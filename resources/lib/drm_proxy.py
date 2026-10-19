"""Adapt ČT's rotating seig KIDs to Kodi 21's per-initialization KID.

Only manifests and small initialization files are served locally. Encrypted
media segments and Widevine licenses continue directly to their original CDN.
"""
import base64
import copy
import hashlib
import json
import math
import os
import struct
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET

from resources.lib import drm


NS = drm.DASH['d']
CENC = 'urn:mpeg:cenc:2013'
ET.register_namespace('', NS)
ET.register_namespace('cenc', CENC)


def _boxes(data, start=0, end=None):
    end = len(data) if end is None else min(end, len(data))
    while start + 8 <= end:
        size, kind = struct.unpack_from('>I4s', data, start)
        header = 8
        if size == 1:
            if start + 16 > end:
                return
            size = struct.unpack_from('>Q', data, start + 8)[0]
            header = 16
        elif size == 0:
            size = end - start
        if size < header:
            raise ValueError('Invalid MP4 box size')
        if start + size > end:
            return  # Prefix reads can end inside the encrypted mdat.
        yield kind, start, start + header, start + size
        start += size


def segment_metadata(data):
    """Read a single seig KID and decode timestamp, without touching mdat."""
    found = []
    decode_time = None
    for kind, _, payload, end in _boxes(data):
        if kind != b'moof':
            continue
        for child, _, body, child_end in _boxes(data, payload, end):
            if child != b'traf':
                continue
            for atom, _, value, atom_end in _boxes(data, body, child_end):
                if atom == b'tfdt':
                    version = data[value]
                    size = 8 if version == 1 else 4
                    if version not in (0, 1) or value + 4 + size != atom_end:
                        raise ValueError('Unsupported tfdt')
                    decode_time = int.from_bytes(data[value + 4:atom_end], 'big')
                if atom != b'sgpd' or data[value + 4:value + 8] != b'seig':
                    continue
                if data[value] != 1 or value + 16 > atom_end:
                    raise ValueError('Unsupported seig group version')
                length, count = struct.unpack_from('>II', data, value + 8)
                if length != 20 or count != 1 or value + 16 + length != atom_end:
                    raise ValueError('Expected one fixed-size seig entry per fragment')
                entry = data[value + 16:atom_end]
                if entry[2] != 1 or entry[3] not in (8, 16) or not any(entry[4:20]):
                    raise ValueError('Unsupported seig encryption parameters')
                found.append(entry[4:20])
    pssh = drm.find_widevine_pssh(data)
    if len(found) != 1 or decode_time is None or not pssh:
        raise ValueError('Missing rotating KID, timestamp or Widevine PSSH')
    return {'kid': found[0], 'time': decode_time, 'pssh': pssh}


def _init_kid_offset(data):
    """Locate the one encrypted track's tenc.default_KID."""
    offsets = []

    def visit(start, end, depth=0):
        if depth > 12:
            raise ValueError('MP4 initialization nesting limit exceeded')
        for kind, _, payload, stop in _boxes(data, start, end):
            child_start = None
            if kind == b'tenc':
                if stop - payload < 24 or data[payload] not in (0, 1):
                    raise ValueError('Unsupported tenc layout')
                offsets.append(payload + 8)
            elif kind in (b'moov', b'trak', b'mdia', b'minf', b'stbl', b'sinf', b'schi'):
                child_start = payload
            elif kind == b'stsd':
                child_start = payload + 8
            elif kind == b'encv':
                child_start = payload + 78
            elif kind == b'enca':
                if payload + 10 > stop or data[payload + 8:payload + 10] != b'\0\0':
                    raise ValueError('Unsupported audio sample entry')
                child_start = payload + 28
            if child_start is not None:
                visit(child_start, stop, depth + 1)
    visit(0, len(data))
    if len(offsets) != 1:
        raise ValueError('Expected one encrypted track in initialization')
    return offsets[0]


def patch_init_kid(data, kid):
    """Replace tenc.default_KID only; file size and all media bytes are unchanged."""
    if len(kid) != 16 or not any(kid):
        raise ValueError('Invalid initialization KID')
    offset = _init_kid_offset(data)
    result = bytearray(data)
    result[offset:offset + 16] = kid
    return bytes(result)


def _tag(name):
    return '{{{}}}{}'.format(NS, name)


def crypto_period_index(pssh):
    """Read the public Widevine rotation index (protobuf field 7), not keys."""
    offset = 28
    if pssh[8] == 1:
        offset += 4 + 16 * struct.unpack_from('>I', pssh, offset)[0]
    length = struct.unpack_from('>I', pssh, offset)[0]
    data = pssh[offset + 4:offset + 4 + length]
    pos = 0

    def integer():
        nonlocal pos
        value = 0
        for shift in range(0, 70, 7):
            if pos >= len(data):
                break
            byte = data[pos]
            pos += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value
        raise ValueError('Invalid Widevine rotation metadata')

    while pos < len(data):
        tag = integer()
        field, wire = tag >> 3, tag & 7
        if wire == 0:
            value = integer()
            if field == 7:
                return value
        elif wire == 2:
            size = integer()
            pos += size
        elif wire in (1, 5):
            pos += 8 if wire == 1 else 4
        else:
            raise ValueError('Unsupported Widevine rotation metadata')
        if pos > len(data):
            raise ValueError('Truncated Widevine rotation metadata')
    raise ValueError('Timeshift requires a Widevine crypto-period index')


def _timeline(template, static=False):
    timeline = template.find('d:SegmentTimeline', drm.DASH)
    if timeline is None:
        return None
    if static:
        # Only the first fragment is needed to repair a VOD initialization.
        # Leave all original runs (including variable durations) in the MPD.
        entry = timeline.find('d:S', drm.DASH)
        if entry is None:
            raise ValueError('Empty VOD timeline')
        return {'time': int(entry.get('t', '0')), 'duration': int(entry.attrib['d'])}
    first, end, duration, count = None, 0, None, 0
    runs = []
    for entry in timeline.findall('d:S', drm.DASH):
        own_duration = int(entry.attrib['d'])
        start = int(entry.get('t', str(end)))
        repeat = int(entry.get('r', '0'))
        if own_duration <= 0 or repeat < 0 or (count and (start < end or own_duration != duration)):
            raise ValueError('Timeshift requires non-overlapping constant-duration segments')
        if not count or start != end:
            runs.append((count, start))
        if first is None:
            first, duration = start, own_duration
        count += repeat + 1
        end = start + (repeat + 1) * own_duration
    if first is None or count > 12000:
        raise ValueError('Unsupported timeshift timeline size')
    return {'time': first, 'duration': duration, 'count': count, 'runs': runs}


def _segment_time(spec, number):
    template, timeline = spec['template'], spec['timeline']
    index = number - int(template.get('startNumber', '1'))
    runs = timeline.get('runs', [(0, timeline['time'])]) if timeline else [(0, int(template.get('presentationTimeOffset', '0')))]
    offset, origin = next((run for run in reversed(runs) if run[0] <= index), runs[0])
    return origin + (index - offset) * int(template.get('duration', '0'))


def _segment_number(spec, timestamp):
    """Find the preceding segment; extend the pinned final run at the live edge."""
    template, timeline = spec['template'], spec['timeline']
    runs = timeline['runs'] if timeline else [(0, int(template.get('presentationTimeOffset', '0')))]
    duration = int(template['duration'])
    index = math.floor((timestamp - runs[0][1]) / duration)
    for offset, origin in runs[1:]:
        if timestamp < origin:
            index = min(index, offset - 1)  # A timestamp in a gap precedes the next run.
            break
        index = offset + math.floor((timestamp - origin) / duration)
    return int(template.get('startNumber', '1')) + index


def _specs(root, period, manifest_url):
    specs = []
    for adaptation in period.findall('d:AdaptationSet', drm.DASH):
        for representation in adaptation.findall('d:Representation', drm.DASH):
            base, attributes, timeline = manifest_url, {}, None
            nodes = (root, period, adaptation, representation)
            for node in nodes:
                location = node.find('d:BaseURL', drm.DASH)
                if location is not None and location.text:
                    base = urljoin(base, location.text.strip())
                template = node.find('d:SegmentTemplate', drm.DASH)
                if template is not None:
                    own_timeline = _timeline(template, root.get('type', 'static') == 'static')
                    if own_timeline is not None:
                        timeline = own_timeline
                    attributes.update(template.attrib)
            if timeline:
                attributes['duration'] = str(timeline['duration'])
            protected = any(cp.get('schemeIdUri', '').lower() == drm.WIDEVINE_SCHEME
                            for node in nodes for cp in node.findall('d:ContentProtection', drm.DASH))
            specs.append({'id': representation.attrib['id'],
                          'base': base, 'template': attributes, 'representation': representation,
                          'protected': protected, 'timeline': timeline,
                          'mime': representation.get('mimeType', adaptation.get('mimeType', '')),
                          'bandwidth': int(representation.get('bandwidth', '0'))})
    return specs


class ManifestAdapter:
    def __init__(self, source, user_agent, local_url):
        self.source, self.user_agent, self.local_url = source, user_agent, local_url
        self.metadata = {}
        self.groups = []
        self.initializations = {}
        self.init_cache = {}
        self.source_document = None
        self.source_effective_url = None
        self.clock_offset = 0
        self.first_available_number = None
        self.lock = threading.RLock()
        self.cached_manifest = None
        self.is_static = False
        self.refreshed_at = 0

    def _metadata(self, spec, number):
        template = spec['template']
        name = drm._media_name(template['media'], spec['representation'], number,
                               _segment_time(spec, number))
        url = urljoin(spec['base'], name)
        key = (url, number)
        if key not in self.metadata:
            data, _, _ = drm._download(url, self.user_agent, prefix=True, prefix_bytes=8192)
            try:
                info = segment_metadata(data)
            except ValueError:
                # Some video moofs contain large sample-encryption tables.
                data, _, _ = drm._download(url, self.user_agent, prefix=True)
                info = segment_metadata(data)
            self.metadata[key] = info
        return self.metadata[key]

    def _history_groups(self, reference, first, last):
        """Locate monotonic crypto-period boundaries by bisection, not a media scan."""
        probes = 0

        def metadata(number):
            nonlocal probes
            probes += 1
            if probes > 512:
                raise ValueError('Too many timeshift key boundaries')
            info = self._metadata(reference, number)
            info['rotation'] = crypto_period_index(info['pssh'])
            return info

        # Leave a small margin for expiration/publication at the CDN edges.
        for _ in range(5):
            try:
                left = metadata(first)
                break
            except OSError:
                first += 1
        else:
            raise ValueError('Timeshift history is unavailable')
        for _ in range(5):
            try:
                right = metadata(last)
                break
            except OSError:
                last -= 1
        else:
            raise ValueError('Timeshift live edge is unavailable')
        intervals = [(first, last, left, right)]
        boundaries = {first: left}
        with ThreadPoolExecutor(max_workers=4) as executor:
            while intervals:
                split = []
                for low, high, a, b in intervals:
                    if a['rotation'] > b['rotation']:
                        raise ValueError('Non-monotonic timeshift key rotation')
                    if a['rotation'] == b['rotation']:
                        if a['kid'] != b['kid']:
                            raise ValueError('Multiple KIDs in one crypto-period')
                        continue
                    if low + 1 == high:
                        boundaries[high] = b
                    else:
                        split.append((low, high, a, b, (low + high) // 2))
                middles = list(executor.map(metadata, [item[4] for item in split]))
                intervals = []
                for (low, high, a, b, middle), info in zip(split, middles):
                    intervals.extend(((low, middle, a, info), (middle, high, info, b)))
        starts = sorted(boundaries)
        groups = [dict(boundaries[number], first=number,
                       last=starts[index + 1] - 1 if index + 1 < len(starts) else last)
                  for index, number in enumerate(starts)]
        return first, last, groups

    def _static_manifest(self, root, periods):
        # Preserve source periods, protection data and complete timelines.
        # A representation-level init override inherits the rest in ISA.
        for index, period in enumerate(periods):
            for spec in _specs(root, period, self.source_effective_url):
                if not spec['protected']:
                    continue
                attributes = spec['template']
                first = int(attributes.get('startNumber', '1'))
                name = drm._media_name(attributes['initialization'], spec['representation'], first, 0)
                init_id = hashlib.sha256(('{}:{}'.format(index, spec['id'])).encode()).hexdigest()[:32]
                self.initializations[init_id] = (urljoin(spec['base'], name), None, spec, first, None)
                template = spec['representation'].find('d:SegmentTemplate', drm.DASH)
                if template is None:
                    template = ET.SubElement(spec['representation'], _tag('SegmentTemplate'))
                template.set('initialization', self.local_url + '/init/' + init_id + '.mp4')
        if not self.initializations:
            raise ValueError('No protected representations')
        base = root.find('d:BaseURL', drm.DASH)
        if base is None:
            base = ET.Element(_tag('BaseURL'))
            root.insert(0, base)
        base.text = urljoin(self.source_effective_url, (base.text or '').strip())
        self.cached_manifest = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        return self.cached_manifest

    def manifest(self):
        with self.lock:
            if self.cached_manifest and (self.is_static or time.monotonic() - self.refreshed_at < 1):
                return self.cached_manifest
            # ČT can alternate packager timelines between identical MPD requests
            # (AST, Period id/start and startNumber all change). Pin one template
            # for this playback; its duration-based media URLs keep advancing.
            if self.source_document is None:
                document, effective, date = drm._download(self.source, self.user_agent)
                self.source_document = document
                self.source_effective_url = effective
                if date:
                    self.clock_offset = parsedate_to_datetime(date).timestamp() - time.time()
            root = ET.fromstring(self.source_document)
            periods = root.findall('d:Period', drm.DASH)
            self.is_static = root.get('type', 'static') == 'static'
            if self.is_static:
                return self._static_manifest(root, periods)
            if root.get('type') != 'dynamic' or len(periods) != 1:
                raise ValueError('Expected one source live DASH period')
            original = periods[0]
            specs = _specs(root, original, self.source_effective_url)
            protected = [spec for spec in specs if spec['protected']]
            if not protected:
                raise ValueError('No protected representations')
            reference = min(protected, key=lambda spec: (not spec['mime'].startswith('audio/'), spec['bandwidth']))
            template = reference['template']
            timeline = reference['timeline']
            scale, duration = int(template.get('timescale', '1')), int(template['duration'])
            start = int(template.get('startNumber', '1'))
            if scale <= 0 or duration <= 0:
                raise ValueError('Invalid live time scale')
            for spec in specs:
                own = spec['template']
                if (int(own.get('duration', '0')) * scale != duration * int(own.get('timescale', '1'))
                        or int(own.get('startNumber', '1')) != start
                        or bool(spec['timeline']) != bool(timeline)):
                    raise ValueError('Unaligned live tracks')
                if timeline and ([(offset, (tick - int(own.get('presentationTimeOffset', '0'))) * scale)
                                  for offset, tick in spec['timeline']['runs']]
                                 != [(offset, (tick - int(template.get('presentationTimeOffset', '0'))) * int(own.get('timescale', '1')))
                                     for offset, tick in timeline['runs']]):
                    raise ValueError('Unaligned timeshift timestamps')
            now = time.time() + self.clock_offset
            period_start = drm._duration(original.get('start', 'PT0S'))
            elapsed = now - drm._timestamp(root.attrib['availabilityStartTime']) - period_start
            presentation_offset = int(template.get('presentationTimeOffset', '0'))
            last = _segment_number(reference, elapsed * scale + presentation_offset) - 1
            window = drm._duration(root.get('timeShiftBufferDepth', 'PT76S'))
            window_count = math.ceil(window * scale / duration)
            if timeline and window_count > 12000:
                raise ValueError('Timeshift window exceeds supported size')
            # Boundary discovery takes a few seconds. Do not advertise the
            # oldest CDN fragments that can expire before Kodi requests them.
            if timeline:
                cutoff = (elapsed - max(0, window - 30)) * scale + presentation_offset
                first = max(start, _segment_number(reference, cutoff))
                if _segment_time(reference, first) < cutoff:
                    first += 1
            else:
                first = max(start, last - min(32, window_count) + 1)
            if first > last:
                raise ValueError('No complete live segments')

            def probe(number):
                try:
                    return number, self._metadata(reference, number)
                except OSError:
                    return number, None  # Expired/unpublished edge segments are not advertised.
            if self.groups and first > self.groups[-1]['last'] + 1:
                self.groups.clear()
            if timeline and not self.groups:
                first, last, self.groups = self._history_groups(reference, first, last)
            else:
                scan_first = max(first, self.groups[-1]['last'] + 1) if timeline and self.groups else first
                with ThreadPoolExecutor(max_workers=4) as executor:
                    available = dict((n, info) for n, info in executor.map(probe, range(scan_first, last + 1)) if info)
                if not available and not self.groups:
                    raise ValueError('No complete live segment metadata')
                if available:
                    last = max(available)
                    if not timeline:
                        first = last
                        while first - 1 in available:
                            first -= 1
                for number in range(max(scan_first, first), last + 1):
                    if self.groups and number <= self.groups[-1]['last']:
                        continue
                    info = available.get(number)
                    if not info:
                        break  # Retry unpublished edges on the next refresh.
                    if not self.groups or self.groups[-1]['kid'] != info['kid']:
                        self.groups.append(dict(info, first=number, last=number))
                    else:
                        self.groups[-1]['last'] = number
            self.groups = [group for group in self.groups if group['last'] >= first]
            self.first_available_number = first
            utc_timing = root.findall('d:UTCTiming', drm.DASH)
            for child in list(root):
                if child.tag in (_tag('Period'), _tag('BaseURL'), _tag('Location')):
                    root.remove(child)
            for child in utc_timing:
                root.remove(child)
            root.set('minimumUpdatePeriod', 'PT2S')
            root.set('suggestedPresentationDelay', 'PT12S')
            if timeline:
                root.set('timeShiftBufferDepth', 'PT{:.6f}S'.format(max(0, window - 30)))
            root.set('publishTime', datetime.fromtimestamp(now, timezone.utc).isoformat())
            ET.SubElement(root, _tag('Location')).text = self.local_url + '/manifest.mpd'
            active_inits = set()
            for group in self.groups:
                period = copy.deepcopy(original)
                group_time = _segment_time(reference, group['first'])
                period.set('id', '{}-{}'.format(original.get('id', 'ct'), group['first']))
                period.set('start', 'PT{:.6f}S'.format(period_start + (group_time - presentation_offset) / scale))
                period.set('duration', 'PT{:.6f}S'.format((_segment_time(reference, group['last']) + duration - group_time) / scale))
                for node in period.iter():
                    for child in list(node):
                        if child.tag == _tag('BaseURL'):
                            node.remove(child)
                by_id = {spec['id']: spec for spec in specs}
                for adaptation in period.findall('d:AdaptationSet', drm.DASH):
                    reps = adaptation.findall('d:Representation', drm.DASH)
                    if any(by_id[rep.attrib['id']]['protected'] for rep in reps):
                        for cp in adaptation.findall('d:ContentProtection', drm.DASH):
                            adaptation.remove(cp)
                        protection = ET.Element(_tag('ContentProtection'), {
                            'schemeIdUri': 'urn:mpeg:dash:mp4protection:2011', 'value': 'cenc',
                            '{{{}}}default_KID'.format(CENC): str(uuid.UUID(bytes=group['kid']))})
                        adaptation.insert(0, protection)
                        cp = ET.Element(_tag('ContentProtection'), {'schemeIdUri': drm.WIDEVINE_SCHEME})
                        adaptation.insert(1, cp)
                        ET.SubElement(cp, '{{{}}}pssh'.format(CENC)).text = base64.b64encode(group['pssh']).decode('ascii')
                    for representation in reps:
                        spec = by_id[representation.attrib['id']]
                        attributes = dict(spec['template'])
                        selected_first = max(first, group['first']) if timeline else group['first']
                        attributes['startNumber'] = str(selected_first)
                        own_duration = int(attributes['duration'])
                        attributes['presentationTimeOffset'] = str(_segment_time(spec, group['first']))
                        attributes['media'] = urljoin(spec['base'], attributes['media'])
                        init_name = drm._media_name(attributes['initialization'], spec['representation'], group['first'], 0)
                        init_url = urljoin(spec['base'], init_name)
                        if spec['protected']:
                            init_id = hashlib.sha256((period.get('id') + ':' + spec['id']).encode()).hexdigest()[:32]
                            # Keep enough context to validate this track only
                            # if Kodi requests its initialization (e.g. on seek).
                            self.initializations[init_id] = (init_url, group['kid'], spec,
                                                             group['first'], group['last'])
                            active_inits.add(init_id)
                            attributes['initialization'] = self.local_url + '/init/' + init_id + '.mp4'
                        else:
                            attributes['initialization'] = init_url
                        for child in list(representation):
                            if child.tag in (_tag('SegmentTemplate'), _tag('ContentProtection')):
                                representation.remove(child)
                        if timeline:
                            attributes.pop('duration')
                        output_template = ET.SubElement(representation, _tag('SegmentTemplate'), attributes)
                        if timeline:
                            output_timeline = ET.SubElement(output_template, _tag('SegmentTimeline'))
                            boundaries = [selected_first] + [start + offset for offset, _ in spec['timeline']['runs'][1:]
                                                             if selected_first < start + offset <= group['last']] + [group['last'] + 1]
                            for begin, end in zip(boundaries, boundaries[1:]):
                                ET.SubElement(output_timeline, _tag('S'), {
                                    't': str(_segment_time(spec, begin)),
                                    'd': str(own_duration), 'r': str(end - begin - 1)})
                root.append(period)
            root.extend(utc_timing)
            # A reader can still request an init from an older MPD snapshot.
            # Keep a bounded history instead of removing it at the live edge.
            retained = active_inits | set(list(self.initializations)[-256:])
            self.initializations = {key: value for key, value in self.initializations.items() if key in retained}
            self.init_cache = {key: value for key, value in self.init_cache.items() if key in active_inits}
            self.metadata = {key: info for key, info in self.metadata.items() if key[1] >= first - 32}
            self.cached_manifest = ET.tostring(root, encoding='utf-8', xml_declaration=True)
            self.refreshed_at = time.monotonic()
            return self.cached_manifest

    def initialization(self, init_id):
        with self.lock:
            if init_id not in self.initializations:
                raise KeyError('Unknown initialization')
            if init_id not in self.init_cache:
                url, kid, spec, first, last = self.initializations[init_id]
                if kid is not None:
                    number = max(first, self.first_available_number)
                    if number > last:
                        raise KeyError('Initialization period has expired')
                    info = self._metadata(spec, number)
                    if info['kid'] != kid:
                        raise ValueError('Independent track key rotation is not supported')
                data, _, _ = drm._download(url, self.user_agent)
                if kid is None:
                    offset = _init_kid_offset(data)
                    if not any(data[offset:offset + 16]):
                        kid = self._metadata(spec, first)['kid']
                self.init_cache[init_id] = patch_init_kid(data, kid) if kid is not None else data
            return self.init_cache[init_id]


class ProxyServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, source, user_agent, token=None):
        self.token = token or uuid.uuid4().hex
        super().__init__(('127.0.0.1', 0), ProxyHandler)
        self.local_url = 'http://127.0.0.1:{}/{}'.format(self.server_port, self.token)
        self.manifest_state = ManifestAdapter(source, user_agent, self.local_url)
        self.last_request = time.monotonic()


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Never log upstream signed URLs or local session tokens.

    def do_GET(self):
        self.server.last_request = time.monotonic()
        path = urlsplit(self.path).path
        prefix = '/' + self.server.token + '/'
        if not path.startswith(prefix):
            self.send_error(404)
            return
        route = path[len(prefix):]
        try:
            if route == 'manifest.mpd':
                content = self.server.manifest_state.manifest()
                mime = 'application/dash+xml'
            elif route.startswith('init/') and route.endswith('.mp4'):
                content = self.server.manifest_state.initialization(route[5:-4])
                mime = 'video/mp4'
            else:
                self.send_error(404)
                return
        except KeyError:
            self.send_error(404)
            return
        except (OSError, ValueError, ET.ParseError):
            self.send_error(502, 'Cannot prepare DRM metadata')
            return
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass


def start_drm_proxy(source, user_agent):
    """Launch a separate Kodi script when the user starts protected DASH playback."""
    import xbmc
    import xbmcaddon
    import xbmcvfs
    addon = xbmcaddon.Addon()
    directory = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    os.makedirs(directory, exist_ok=True)
    config_path = os.path.join(directory, 'drm-proxy-' + uuid.uuid4().hex + '.json')
    ready_path = config_path + '.ready'
    with open(config_path, 'w') as output:
        json.dump({'source': source, 'user_agent': user_agent}, output)
    script = os.path.join(addon.getAddonInfo('path'), 'proxy_service.py')
    xbmc.executebuiltin('RunScript("{}","{}")'.format(script, config_path))
    monitor = xbmc.Monitor()
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if os.path.exists(ready_path):
            try:
                with open(ready_path) as source_file:
                    ready = json.load(source_file)
            finally:
                os.remove(ready_path)
            if ready.get('error'):
                raise ValueError('DRM proxy failed to initialize')
            return ready['url']
        if monitor.waitForAbort(0.1):
            break
    raise ValueError('DRM proxy startup timed out')
