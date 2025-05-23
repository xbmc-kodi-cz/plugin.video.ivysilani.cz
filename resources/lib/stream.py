# -*- coding: utf-8 -*-
import sys
import os
import xbmcgui
import xbmcplugin
import xbmcaddon
import re

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
from resources.lib.utils import PY2, iso639map

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
    item_data = get_item_data(id)
    play_idec(item_data['idec'])

def play_idec(idec):
    if idec == 'N/A':
        xbmcgui.Dialog().notification('iVysílání', 'Pořad není k dispozici!', xbmcgui.NOTIFICATION_ERROR, 5000)
        return   
    data = call_api(url = 'https://api.ceskatelevize.cz/video/v1/playlist-vod/v1/stream-data/media/external/' + str(idec) + '?canPlayDrm=true&quality=web&streamType=dash&origin=ivysilani&usePlayability=true')
    if 'streams' not in data or len(data['streams']) < 1 or 'url' not in data['streams'][0]:
        xbmcgui.Dialog().notification('iVysílání', 'Chyba při přehrání pořadu', xbmcgui.NOTIFICATION_ERROR, 5000)
    else:
        url = data['streams'][0]['url']
        subtitles = data['streams'][0].get('subtitles', [])
        play_url(url, subtitles)

def play_from_url(url):
    #see https://regex101.com/r/Ay3RyM/1
    m = re.search(r"/(?P<show_id>\d+)-([^/]+/(?P<episode_idec>\d+)/?)?", url)
    show_id = m.group("show_id") if m else None
    if not show_id:
        xbmcgui.Dialog().notification('iVysílání', 'Nepodařilo se zjistit ID pořadu', xbmcgui.NOTIFICATION_ERROR, 5000)
        return
    idec = m.group("episode_idec") if m else None #series has idec in url
    if not idec: #movies must be resolved by calling graphql
        data = call_graphql(operationName = 'Show', variables = {'id' : str(show_id)})
        if not data or 'idec' not in data:
            xbmcgui.Dialog().notification('iVysílání', 'Pořad %s není k dispozici' % str(show_id), xbmcgui.NOTIFICATION_ERROR, 5000)
            return
        idec = data['idec']
    play_idec(idec)

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
        addon = xbmcaddon.Addon()
        addon_userdata_dir = translatePath(addon.getAddonInfo('profile'))
        if not os.path.exists(addon_userdata_dir):
            os.makedirs(addon_userdata_dir)    
        filelist = os.listdir(addon_userdata_dir)
        for filename in filelist:
            if filename.endswith(".sub"):
                os.remove(os.path.join(addon_userdata_dir, filename))            
        subs = []
        for sub_lang in subtitles:
            lang = sub_lang['language']
            for sub in sub_lang['files']:
                response = urlopen(sub['url'])
                filename = os.path.join(addon_userdata_dir, iso639map[lang] + '.sub') 
                subs.append(filename)
                with open(filename, 'wb') as f:
                    f.write(response.read())
                break  # There are multiple formats, but we are only interested in one per language
        list_item.setSubtitles(subs)
    xbmcplugin.setResolvedUrl(_handle, True, list_item)                        
