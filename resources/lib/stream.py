# -*- coding: utf-8 -*-
import sys
import os
import xbmcgui
import xbmcplugin
import xbmcaddon
import re
import xbmc

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

try:
    from urllib.request import urlopen # type: ignore
except ImportError:
    from urllib2 import urlopen # type: ignore

from resources.lib.api import call_api, call_graphql
from resources.lib.items import get_item_data
from resources.lib.utils import PY2, iso639map, ua, get_isa_version

if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

def play_channel(channelId):
    endpoint = 'https://api.ceskatelevize.cz/video/v1/playlist-live/v1/stream-data/channel/' + channelId
    options = '?canPlayDrm=fale&quality=web&maxQualityCount=5'
    data = call_api(url = endpoint + options + '&streamType=hls')
    manifest_type = 'hls'
    isa = get_isa_version()
    if isa >= 21.5:
        from resources.lib.drm import is_drm_stream
    if isinstance(data, dict) and data.get('streamUrls', {}).get('main') and isa >= 21.5 and is_drm_stream(data['streamUrls']['main']):
        data = call_api(url = endpoint + options + '&streamType=dash&encryption=wv')
        manifest_type = 'mpd'
    if 'streamUrls' not in data or 'main' not in data['streamUrls']:
        xbmcgui.Dialog().notification('iVysílání', 'Chyba při přehrání pořadu', xbmcgui.NOTIFICATION_ERROR, 3000)
    else:
        urls = data['streamUrls']
        source = urls.get('timeshift') if manifest_type == 'mpd' else None
        play_url(source or urls['main'], manifest_type=manifest_type)

def play_id(id):
    if id == 'N/A':
        xbmcgui.Dialog().notification('iVysílání', 'Pořad není k dispozici!', xbmcgui.NOTIFICATION_ERROR, 3000)
        return   
    item_data = get_item_data(id)
    play_idec(item_data['idec'])

def play_idec(idec):
    if idec == 'N/A':
        xbmcgui.Dialog().notification('iVysílání', 'Pořad není k dispozici!', xbmcgui.NOTIFICATION_ERROR, 3000)
        return   
    data = call_api(url = 'https://api.ceskatelevize.cz/video/v1/playlist-vod/v1/stream-data/media/external/' + str(idec) + '?canPlayDrm=true&quality=web&streamType=dash&origin=ivysilani&usePlayability=true')
    if isinstance(data, dict) and data.get('platformChannel'):
        play_channel(data['platformChannel'])
        return
    if 'streams' not in data or len(data['streams']) < 1 or 'url' not in data['streams'][0]:
        if 'error' in data and 'message' in data and 'labels' in  data['message'] and 'textShort' in data['message']['labels']:
            xbmcgui.Dialog().notification('iVysílání', data['message']['labels']['textShort'], xbmcgui.NOTIFICATION_ERROR, 3000)
        else:
            xbmcgui.Dialog().notification('iVysílání', 'Chyba při přehrání pořadu', xbmcgui.NOTIFICATION_ERROR, 3000)
    else:
        url = data['streams'][0]['url']
        subtitles = data['streams'][0].get('subtitles', [])
        play_url(url, subtitles)

def play_from_url(url):
    #see https://regex101.com/r/Ay3RyM/1
    m = re.search(r"/(?P<show_id>\d+)-([^/]+/(?P<episode_idec>\d+)/?)?", url)
    show_id = m.group("show_id") if m else None
    if not show_id:
        xbmcgui.Dialog().notification('iVysílání', 'Nepodařilo se zjistit ID pořadu', xbmcgui.NOTIFICATION_ERROR, 3000)
        return
    idec = m.group("episode_idec") if m else None #series has idec in url
    if not idec: #movies must be resolved by calling graphql
        data = call_graphql(operationName = 'Show', variables = {'id' : str(show_id)})
        if not data or 'idec' not in data:
            xbmcgui.Dialog().notification('iVysílání', 'Pořad %s není k dispozici' % str(show_id), xbmcgui.NOTIFICATION_ERROR, 3000)
            return
        idec = data['idec']
    play_idec(idec)

def play_url(url, subtitles=None, manifest_type='mpd'):
    list_item = xbmcgui.ListItem(path = url)
    isa = get_isa_version()
    if isa >= 21.5:
        from resources.lib.drm import is_drm_stream
        from resources.lib.drm_proxy import start_drm_proxy
    if isa >= 21.5 and is_drm_stream(url):
        from inputstreamhelper import Helper # type: ignore
        is_helper = Helper(manifest_type, drm = 'com.widevine.alpha')
        if not is_helper.check_inputstream():
            xbmcplugin.setResolvedUrl(_handle, False, list_item)
            return
        list_item.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
        list_item.setProperty('inputstream.adaptive.license_key', 'https://ivys-wvproxy.o2tv.cz/license?access_token=public|Origin=https%3A%2F%2Fwww.ceskatelevize.cz&Referer=https%3A%2F%2Fwww.ceskatelevize.cz%2F|R{SSM}|')
        if manifest_type == 'mpd':
            try:
                proxy_url = start_drm_proxy(url, ua)
            except (OSError, ValueError, KeyError) as exc:
                # Network exceptions may contain signed URLs: log the type only.
                xbmc.log('[iVysilani] DRM initialization failed ({})'.format(type(exc).__name__), xbmc.LOGERROR)
                xbmcgui.Dialog().notification('iVysílání', 'Nepodařilo se načíst inicializační data DRM', xbmcgui.NOTIFICATION_ERROR, 5000)
                xbmcplugin.setResolvedUrl(_handle, False, list_item)
                return
            list_item.setPath(proxy_url)
            xbmc.log('[iVysilani] DRM: local manifest/init adapter enabled', xbmc.LOGINFO)
    list_item.setMimeType('application/dash+xml' if manifest_type == 'mpd' else 'application/vnd.apple.mpegurl')
    list_item.setProperty('inputstream', 'inputstream.adaptive')
    if PY2:
        list_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
    list_item.setProperty('inputstream.adaptive.manifest_type', manifest_type)
    list_item.setContentLookup(False)
    if subtitles:
        addon = xbmcaddon.Addon()
        addon_userdata_dir = translatePath(addon.getAddonInfo('profile'))
        if not os.path.exists(addon_userdata_dir):
            os.makedirs(addon_userdata_dir)    
        filelist = os.listdir(addon_userdata_dir)
        for filename in filelist:
            if filename.endswith((".sub", ".vtt", ".srt")):
                os.remove(os.path.join(addon_userdata_dir, filename))
        subs = []
        for sub_lang in subtitles:
            lang = sub_lang['language']
            files = {sub['format']: sub['url'] for sub in sub_lang['files']}
            fmt = next((f for f in ('vtt', 'srt') if f in files), None)
            if fmt is None:
                continue
            response = urlopen(files[fmt])
            filename = os.path.join(addon_userdata_dir, iso639map[lang] + '.' + fmt)
            subs.append(filename)
            with open(filename, 'wb') as f:
                f.write(response.read())
        list_item.setSubtitles(subs)
    xbmcplugin.setResolvedUrl(_handle, True, list_item)                        
