# -*- coding: utf-8 -*-
import sys
import xbmcgui
import xbmcplugin
from resources.lib.api import call_graphql
from resources.lib.favourites import get_favourites
from resources.lib.items import get_show_listitem
from resources.lib.utils import get_url, encode

if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

def list_recommended(label):
    xbmcplugin.setPluginCategory(_handle, label)
    data = call_graphql(operationName = 'HomepageRows', variables = '{"deviceType":"website","limit":40,"offset":0}')
    if data is not None and 'rows' in data and len(data['rows']) > 0:
        for item in data['rows']:
            if item['assets']['totalCount'] > 0:
                list_item = xbmcgui.ListItem(label = item['title'])
                url = get_url(action='list_block', label = encode(item['title']), blockId = item['id'])  
                xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
        xbmcplugin.endOfDirectory(_handle, cacheToDisc = True)    

def list_block(label, blockId):
    xbmcplugin.setPluginCategory(_handle, label)
    xbmcplugin.setContent(_handle, 'tvshows')
    data = call_graphql(operationName = 'HomepageBlock', variables = '{"id":"' + str(blockId) + '","limit":40,"offset":0,"deviceType":"website"}')
    if data is not None and 'assets' in data and 'items' in data['assets'] and len(data['assets']['items']) > 0:
        favourites = get_favourites()
        for item in data['assets']['items']:
            if int(item['id']) in favourites:
                favourite = True
            else:
                favourite = False
            get_show_listitem(label, item['id'], favourite)
        xbmcplugin.endOfDirectory(_handle, cacheToDisc = True)  

