# -*- coding: utf-8 -*-
import sys
import xbmcgui
import xbmcplugin

from resources.lib.api import call_graphql
from resources.lib.utils import get_url, get_kodi_version

if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

def list_channels(label):
    kodi_version = get_kodi_version()
    xbmcplugin.setPluginCategory(_handle, label)
    data = call_graphql(operationName = 'LiveBroadcastFind', variables = '{}')
    if data is None:
        xbmcgui.Dialog().notification('iVysíláni', 'Chyba načtení kanálů', xbmcgui.NOTIFICATION_ERROR, 5000)
    else:
        for item in data:
            if item['current'] is not None:
                channelId = item['current']['encoder']
                channelName = item['current']['assignedToChannel']['channelName']
                channelLogo = item['current']['channelSettings']['channelLogo']
                title = item['current']['title']
                previewImage = item['current']['previewImage']

                list_item = xbmcgui.ListItem(label = channelName + ' | ' + title )
                url = get_url(action='play_channel', channelId = channelId)  
                list_item.setInfo('video', {'mediatype':'movie', 'title': title})                  
                list_item.setArt({'thumb' : previewImage, 'icon' : channelLogo})
                list_item.setProperty('IsPlayable', 'true')       
                list_item.setContentLookup(False)          
                if kodi_version >= 20:
                    infotag = list_item.getVideoInfoTag()
                    infotag.setMediaType('movie')
                else:
                    list_item.setInfo('video', {'mediatype' : 'movie'})        
                if 'description' in item['current'] and item['current']['description'] is not None:
                    if kodi_version >= 20:
                        infotag.setPlot(item['current']['description'])
                    else:
                        list_item.setInfo('video', {'plot': item['current']['description']})  

                xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
        xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)  


