# -*- coding: utf-8 -*-
import sys
import xbmcgui
import xbmcplugin
import xbmcaddon

from resources.lib.api import call_api
from resources.lib.utils import PY2

if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

def play_channel(channelId):
    data = call_api(url = 'https://api.ceskatelevize.cz/video/v1/playlist-live/v1/stream-data/channel/' + channelId + '?canPlayDrm=false&streamType=dash&quality=web&maxQualityCount=5')
    if 'streamUrls' not in data or 'main' not in data['streamUrls']:
        xbmcgui.Dialog().notification('iVysílání', 'Chyba při přehrání pořadu', xbmcgui.NOTIFICATION_ERROR, 5000)
    else:
        url = data['streamUrls']['main']
        play_url(url, [])

def play_id(id):
    if id == 'N/A':
        xbmcgui.Dialog().notification('iVysílání', 'Pořad není k dispozici!', xbmcgui.NOTIFICATION_ERROR, 5000)
        return    
    data = call_api(url = 'https://api.ceskatelevize.cz/video/v1/playlist-vod/v1/stream-data/media/external/' + str(id) + '?canPlayDrm=true&quality=web&streamType=dash&origin=ivysilani&usePlayability=true')
    if 'streams' not in data or len(data['streams']) < 1 or 'url' not in data['streams'][0]:
        xbmcgui.Dialog().notification('iVysílání', 'Chyba při přehrání pořadu', xbmcgui.NOTIFICATION_ERROR, 5000)
    else:
        url = data['streams'][0]['url']
        subtitles = data['streams'][0].get('subtitles', [])
        play_url(url, subtitles)

def play_url(url, subtitles=[]):
    list_item = xbmcgui.ListItem(path = url)
    if 'drmOnly=true' in url:
        from inputstreamhelper import Helper # type: ignore
        is_helper = Helper('mpd', drm = 'com.widevine.alpha')
        if is_helper.check_inputstream():
            list_item.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
            list_item.setProperty('inputstream.adaptive.license_key', 'https://ivys-wvproxy.o2tv.cz/license?access_token=c3RlcGFuLWEtb25kcmEtanNvdS1wcm9zdGUtbmVqbGVwc2k=||R{SSM}|')
            list_item.setMimeType('application/dash+xml')
    list_item.setProperty('inputstream', 'inputstream.adaptive')
    if PY2:
        list_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
    list_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')        
    list_item.setContentLookup(False)
    if len(subtitles) > 0:
        sub_langs = []
        subs = []
        for sub_lang in subtitles:
            lang = sub_lang['language']
            for sub in sub_lang['files']:
                sub_langs.append(lang)
                subs.append(sub['url'])
                break  # There are multiple formats, but we are only interested in one per language
        list_item.setSubtitles(subs)
        for i in range(len(sub_langs)):
            list_item.setProperty('SubtitleLanguage.%i' % (i + 1,), sub_langs[i])


    xbmcplugin.setResolvedUrl(_handle, True, list_item)                        
