# -*- coding: utf-8 -*-
import sys
import xbmcgui
import xbmcplugin

import time
from datetime import datetime, date

from resources.lib.api import call_graphql, call_graphql_pq, call_api
from resources.lib.items import get_show_listitem
from resources.lib.favourites import get_favourites
from resources.lib.utils import get_url, get_kodi_version

if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

def list_channels_nopq(label):
    channels_list = []
    channels = {}    
    xbmcplugin.setPluginCategory(_handle, label)
    xbmcplugin.setContent(_handle, 'tvshows')
    kodi_version = get_kodi_version()
    data = call_graphql(operationName = 'TVProgramChannelsList', variables = {})
    for item in data:
        if item['channelAsString'] not in channels_list:
            channels_list.append(item['channelAsString'])
        channels.update({item['channelAsString'] : {'id' : item['encoder'], 'name' : item['channelSettings']['channelName']}})

    day = date.today()
    data = call_graphql(operationName = 'CurrentBroadcast', variables = {'channels' : channels_list, 'date' : day.strftime('%m.%d.%Y')})
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
                    if 'platformChannel' in channel_data:
                        channelId = channel_data['platformChannel']
                        title = item['currentBroadcast']['item']['title']
                        image = item['currentBroadcast']['item']['imageUrl']                    
                        list_item = xbmcgui.ListItem(label = channels[item['channel']]['name'] + ' | ' + title + ' | ' + title_time)
                        url = get_url(action='play_channel', channelId = channelId)  
                        if kodi_version >= 20:
                            infotag = list_item.getVideoInfoTag()
                            infotag.setMediaType('tvhow')
                        else:
                            list_item.setInfo('video', {'mediatype' : 'tvhow'})        
                        if kodi_version >= 20:
                            infotag.setTitle(title)
                        else:
                            list_item.setInfo('video', {'title' : title})
                        list_item.setArt({'thumb' : image, 'icon' : image})
                        list_item.setProperty('IsPlayable', 'true')       
                        list_item.setContentLookup(False)          
                        if 'description' in item['currentBroadcast']['item'] and item['currentBroadcast']['item']['description'] is not None:
                            if kodi_version >= 20:
                                infotag.setPlot(item['currentBroadcast']['item']['description'])
                            else:
                                list_item.setInfo('video', {'plot': item['currentBroadcast']['item']['description']})  
                        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
        xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)  

def list_channels(label):
    xbmcplugin.setPluginCategory(_handle, label)
    xbmcplugin.setContent(_handle, 'tvshows')
    kodi_version = get_kodi_version()
    data = call_graphql_pq(operationName = 'LiveBroadcastFind', variables = '{}')
    print(data)
    if data is None:
        xbmcgui.Dialog().notification('iVysíláni', 'Chyba načtení kanálů', xbmcgui.NOTIFICATION_ERROR, 5000)
    else:
        tz_offset = int(time.mktime(datetime.now().timetuple())-time.mktime(datetime.utcnow().timetuple()))
        favourites = get_favourites()
        for item in data:
            if item['current'] is not None:
                startTime = time.mktime(time.strptime(item['current']['startsAt'][:-5], '%Y-%m-%dT%H:%M:%S')) + tz_offset
                endTime = time.mktime(time.strptime(item['current']['endsAt'][:-5], '%Y-%m-%dT%H:%M:%S')) + tz_offset
                title_time = datetime.fromtimestamp(startTime).strftime('%H:%M') + ' - ' + datetime.fromtimestamp(endTime).strftime('%H:%M')
                url = get_url(action='play_channel', channelId = item['current']['encoder'])  
                if 'sidp' in item['current'] and item['current']['sidp'] is not None and len(item['current']['sidp']) > 1:
                    if int(item['current']['sidp']) in favourites:
                        favourite = True
                    else:
                        favourite = False
                    get_show_listitem(label, item['current']['sidp'], favourite, item['current']['assignedToChannel']['channelName'] + ' | ' + item['current']['title'] + ' | ' + title_time, url)
                else:
                    channelId = item['current']['encoder']
                    channelLogo = item['current']['channelSettings']['channelLogo']
                    title = item['current']['title']
                    previewImage = item['current']['previewImage']
                    list_item = xbmcgui.ListItem(label = item['current']['assignedToChannel']['channelName'] + ' | ' + title + ' | ' + title_time)
                    url = get_url(action='play_channel', channelId = channelId)  
                    if kodi_version >= 20:
                        infotag = list_item.getVideoInfoTag()
                        infotag.setMediaType('tvhow')
                    else:
                        list_item.setInfo('video', {'mediatype' : 'tvhow'})        
                    if kodi_version >= 20:
                        infotag.setTitle(title)
                    else:
                        list_item.setInfo('video', {'title' : title})
                    list_item.setArt({'thumb' : previewImage, 'icon' : channelLogo})
                    list_item.setProperty('IsPlayable', 'true')       
                    list_item.setContentLookup(False)          
                    if 'description' in item['current'] and item['current']['description'] is not None:
                        if kodi_version >= 20:
                            infotag.setPlot(item['current']['description'])
                        else:
                            list_item.setInfo('video', {'plot': item['current']['description']})  
                    xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
        xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)  