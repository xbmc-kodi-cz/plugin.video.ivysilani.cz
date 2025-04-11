# -*- coding: utf-8 -*-
import sys
import xbmcgui
import xbmcplugin

from datetime import date, datetime, timedelta
import time

from resources.lib.api import call_graphql
from resources.lib.items import get_show_listitem
from resources.lib.favourites import get_favourites
from resources.lib.utils import get_url, day_translation, day_translation_short, encode

if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

def list_archive(label):
    xbmcplugin.setPluginCategory(_handle, label)
    data = call_graphql(operationName = 'TVProgramChannelsList', variables = {})
    if data is None:
        xbmcgui.Dialog().notification('iVysíláni', 'Chyba načtení kanálů', xbmcgui.NOTIFICATION_ERROR, 5000)
    else:
        for item in data:
            if item['channelAsString'] not in ['ctSportExtra', 'iVysilani']:
                list_item = xbmcgui.ListItem(label = item['channelSettings']['channelName'])
                url = get_url(action='list_archive_days', channel = item['channelAsString'], label = label + ' / ' + encode(item['channelSettings']['channelName']))  
                xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = True)

def list_archive_days(label, channel):
    xbmcplugin.setPluginCategory(_handle, label)
    for i in range (15):
        day = date.today() - timedelta(days = i)
        if i == 0:
            den_label = 'Dnes'
            den = 'Dnes'
        elif i == 1:
            den_label = 'Včera'
            den = 'Včera'
        else:
            den_label = day_translation_short[day.strftime('%w')] + ' ' + day.strftime('%d.%m')
            den = day_translation[day.strftime('%w')] + ' ' + day.strftime('%d.%m.%Y')
        list_item = xbmcgui.ListItem(label = den)
        url = get_url(action='list_program', channel = channel, day_min = i, label = label + ' / ' + den_label)  
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)

def list_program(label, channel, day_min):
    label = label.replace('Archiv /','')
    xbmcplugin.setPluginCategory(_handle, label)
    xbmcplugin.setContent(_handle, 'tvshows')

    day = date.today() - timedelta(days = int(day_min))
    data = call_graphql(operationName = 'TvProgramDailyTablet', variables = {'channels' : channel, 'date' : day.strftime('%m.%d.%Y')})
    if data is None:
        xbmcgui.Dialog().notification('iVysíláni', 'Chyba při načtení pořadů', xbmcgui.NOTIFICATION_ERROR, 5000)        
    else:
        favourites = get_favourites()
        tz_offset = int(time.mktime(datetime.now().timetuple())-time.mktime(datetime.utcnow().timetuple()))
        for item in data[0]['program']:
            startTime = time.mktime(time.strptime(item['start'][:-5], '%Y-%m-%dT%H:%M:%S')) + tz_offset
            endTime = time.mktime(time.strptime(item['end'][:-5], '%Y-%m-%dT%H:%M:%S')) + tz_offset
            if 'idec' in item and item['idec'] is not None and 'isPlayableNow' in item and item['isPlayableNow'] == True:
                title = day_translation_short[(datetime.fromtimestamp(startTime)).strftime('%w')] + ' ' + datetime.fromtimestamp(startTime).strftime('%d.%m %H:%M') + ' - ' + datetime.fromtimestamp(endTime).strftime('%H:%M') + ' | ' + encode(item['title'])
                if int(item['sidp']) in favourites:
                    favourite = True
                else:
                    favourite = False
                item_data = { 'idec' : int(item['idec']), 'showType' : 'show', 'title' : item['title'], 'description' : item['description'], 'image' :item['imageUrl'], 'cast' : [], 'directors' : [], 'year' : '', 'country' : '', 'genres' : []}
                get_show_listitem(label, item['sidp'], favourite, title, item_data = item_data)
            else:
                list_item = xbmcgui.ListItem(label = '[COLOR = grey]' + day_translation_short[datetime.fromtimestamp(startTime).strftime('%w')] + ' ' + datetime.fromtimestamp(startTime).strftime('%d.%m %H:%M') + ' - ' + datetime.fromtimestamp(endTime).strftime('%H:%M') + ' | ' + encode(item['title']) + '[/COLOR]')
                url = get_url(action='play_idec', idec = 'N/A') 
                xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    xbmcplugin.endOfDirectory(_handle, updateListing = True, cacheToDisc = True)    