# -*- coding: utf-8 -*-
import sys
import xbmcgui
import xbmcplugin

import time
from datetime import date, datetime
import json

from resources.lib.api import call_graphql, call_api
from resources.lib.items import get_show_listitem
from resources.lib.favourites import get_favourites
from resources.lib.utils import get_url, get_kodi_version

if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

def list_channels(label):
    channels_list = []
    channels = {}
    xbmcplugin.setPluginCategory(_handle, label)
    xbmcplugin.setContent(_handle, 'movies')
    kodi_version = get_kodi_version()
    data = call_graphql(operationName = 'TVProgramChannelsList', variables = '{}')
    for item in data:
        if item['channelAsString'] not in channels_list:
            channels_list.append(item['channelAsString'])
        channels.update({item['channelAsString'] : {'id' : item['encoder'], 'name' : item['channelSettings']['channelName']}})

    day = date.today()
    data = call_graphql(operationName = 'CurrentBroadcast', variables = '{"channels":' + json.dumps(channels_list).replace(' ','') + ',"date":"' + day.strftime('%m.%d.%Y') +'"}')
    if data is None:
        xbmcgui.Dialog().notification('iVysíláni', 'Chyba načtení kanálů', xbmcgui.NOTIFICATION_ERROR, 5000)
    else:
        tz_offset = int(time.mktime(datetime.now().timetuple())-time.mktime(datetime.utcnow().timetuple()))
        favourites = get_favourites()
        for item in data:
            if item['currentBroadcast'] is not None and 'item' in item['currentBroadcast']:
                startTime = time.mktime(time.strptime(item['currentBroadcast']['item']['start'][:-5], '%Y-%m-%dT%H:%M:%S')) + tz_offset
                endTime = time.mktime(time.strptime(item['currentBroadcast']['item']['end'][:-5], '%Y-%m-%dT%H:%M:%S')) + tz_offset
                title_time = datetime.fromtimestamp(startTime).strftime('%H:%M') + ' - ' + datetime.fromtimestamp(endTime).strftime('%H:%M')
                url = get_url(action='play_channel', channelId = channels[item['channel']]['id'])  
                if 'sidp' in item['currentBroadcast']['item'] and item['currentBroadcast']['item']['sidp'] is not None and len(item['currentBroadcast']['item']['sidp']) > 1:
                    if int(item['currentBroadcast']['item']['sidp']) in favourites:
                        favourite = True
                    else:
                        favourite = False
                    item_data = { 'idec' : int(item['currentBroadcast']['item']['idec']), 'showType' : 'show', 'title' : item['currentBroadcast']['item']['title'], 'description' : item['currentBroadcast']['item']['description'], 'image' : item['currentBroadcast']['item']['imageUrl'], 'cast' : [], 'directors' : [], 'year' : '', 'country' : '', 'genres' : []}
                    get_show_listitem(label, item['currentBroadcast']['item']['sidp'], favourite, channels[item['channel']]['name'] + ' | ' + item['currentBroadcast']['item']['title'] + ' | ' + title_time, url, item_data)
                else:
                    channel_data = call_api(url = 'https://api.ceskatelevize.cz/video/v1/playlist-vod/v1/stream-data/media/external/' + str(item['currentBroadcast']['item']['idec']) + '?canPlayDrm=true&quality=web&streamType=dash&origin=ivysilani&usePlayability=true')
                    channelId = channel_data['platformChannel']
                    title = item['currentBroadcast']['item']['title']
                    image = item['currentBroadcast']['item']['imageUrl']
                    list_item = xbmcgui.ListItem(label = channels[item['channel']]['name'] + ' | ' + title + ' | ' + title_time)
                    url = get_url(action='play_channel', channelId = channelId)  
                    list_item.setInfo('video', {'mediatype':'movie', 'title': title})                  
                    list_item.setArt({'thumb' : image, 'icon' : image})
                    list_item.setProperty('IsPlayable', 'true')       
                    list_item.setContentLookup(False)          
                    if kodi_version >= 20:
                        infotag = list_item.getVideoInfoTag()
                        infotag.setMediaType('movie')
                    else:
                        list_item.setInfo('video', {'mediatype' : 'movie'})        
                    if 'description' in item['currentBroadcast']['item'] and item['currentBroadcast']['item']['description'] is not None:
                        if kodi_version >= 20:
                            infotag.setPlot(item['currentBroadcast']['item']['description'])
                        else:
                            list_item.setInfo('video', {'plot': item['currentBroadcast']['item']['description']})  
                    xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
        xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)  
