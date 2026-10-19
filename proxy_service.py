"""Per-playback loopback manifest/init adapter, started on demand by the addon."""
import json
import os
import sys
import threading
import time

import xbmc

from resources.lib.drm_proxy import ProxyServer


def serve(config_path):
    ready = config_path + '.ready'
    server = None
    thread = None
    started = time.monotonic()
    try:
        with open(config_path) as source:
            config = json.load(source)
        server = ProxyServer(config['source'], config['user_agent'])
        server.manifest_state.manifest()
        temporary = ready + '.tmp'
        with open(temporary, 'w') as output:
            json.dump({'url': server.local_url + '/manifest.mpd'}, output)
        os.replace(temporary, ready)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        xbmc.log('[iVysilani] DRM proxy: ready in {:.2f}s; track KIDs checked on demand'.format(
            time.monotonic() - started), xbmc.LOGINFO)
        monitor = xbmc.Monitor()
        player = xbmc.Player()
        while not monitor.waitForAbort(1):
            if time.monotonic() - server.last_request > 90:
                # Static VOD does not refresh its MPD. Keep its init routes
                # available for a later seek/quality change in this playback.
                try:
                    if player.getPlayingFile() == server.local_url + '/manifest.mpd':
                        continue
                except RuntimeError:  # Playback stopped while checking it.
                    pass
                break
    except Exception as exc:
        xbmc.log('[iVysilani] DRM proxy failed ({})'.format(type(exc).__name__), xbmc.LOGERROR)
        if not os.path.exists(ready):
            temporary = ready + '.tmp'
            with open(temporary, 'w') as output:
                json.dump({'error': type(exc).__name__}, output)
            os.replace(temporary, ready)
    finally:
        if server:
            if thread:
                server.shutdown()
                thread.join(timeout=2)
            server.server_close()
        if os.path.exists(config_path):
            os.remove(config_path)


if __name__ == '__main__':
    serve(sys.argv[1])
