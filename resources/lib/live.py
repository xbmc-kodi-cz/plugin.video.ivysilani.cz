# -*- coding: utf-8 -*-
import sys
import xbmcgui
import xbmcplugin

import time
from datetime import datetime

from resources.lib.api import call_graphql
from resources.lib.category import get_show_listitem
from resources.lib.favourites import get_favourites
from resources.lib.utils import get_url

if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

def list_channels(label):
    xbmcplugin.setPluginCategory(_handle, label)
    xbmcplugin.setContent(_handle, 'movies')
    
    data = call_graphql(operationName = 'LiveBroadcastFind', variables = '{}')
    if data is None:
        xbmcgui.Dialog().notification('iVysíláni', 'Chyba načtení kanálů', xbmcgui.NOTIFICATION_ERROR, 5000)
    else:
        tz_offset = int(time.mktime(datetime.now().timetuple())-time.mktime(datetime.utcnow().timetuple()))
        favourites = get_favourites()
        for item in data:
            if item['current'] is not None and item['current']['channel'] not in ['ctSportExtra', 'iVysilani']:
                startTime = time.mktime(time.strptime(item['current']['startsAt'][:-5], '%Y-%m-%dT%H:%M:%S')) + tz_offset
                print(tz_offset)
                endTime = time.mktime(time.strptime(item['current']['endsAt'][:-5], '%Y-%m-%dT%H:%M:%S')) + tz_offset
                title_time = datetime.fromtimestamp(startTime).strftime('%H:%M') + ' - ' + datetime.fromtimestamp(endTime).strftime('%H:%M')
                if int(item['current']['sidp']) in favourites:
                    favourite = True
                else:
                    favourite = False
                url = get_url(action='play_channel', channelId = item['current']['encoder'])  
                get_show_listitem(label, item['current']['sidp'], favourite, item['current']['assignedToChannel']['channelName'] + ' | ' + item['current']['title'] + ' | ' + title_time, url)
        xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)  
