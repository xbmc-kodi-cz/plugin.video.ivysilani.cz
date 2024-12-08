# -*- coding: utf-8 -*-
import sys
import os
import xbmcgui
import xbmcplugin
import xbmcaddon

import math

from resources.lib.api import call_graphql
from resources.lib.utils import get_url, encode, get_kodi_version

if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

def list_categories(label):
    xbmcplugin.setPluginCategory(_handle, label)
    data = call_graphql(operationName = 'CategoryMenu', variables = '{}')
    if data is not None:
        for item in data:
            if item['categoryId'] is not None:
                list_item = xbmcgui.ListItem(label = item['title'])
                url = get_url(action='list_category', label = encode(item['title']), categoryId = item['categoryId'][0], subcategory = 0, page = 1)  
                xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
        xbmcplugin.endOfDirectory(_handle, cacheToDisc = True)    

def list_subcategories(label, categoryId):
    xbmcplugin.setPluginCategory(_handle, label)
    data = call_graphql(operationName = 'CategoryMenu', variables = '{}')
    if data is not None:
        for item in data:
            if item['categoryId'] is not None and item['categoryId'][0] == str(categoryId):
                for subitem in item['children']:
                    if subitem['categoryId'] is not None:
                        if str(categoryId) in subitem['categoryId']:
                            subitem['categoryId'].remove(str(categoryId))
                        if len(subitem['categoryId']) > 0:
                            list_item = xbmcgui.ListItem(label = subitem['title'])
                            url = get_url(action='list_category', label = encode(subitem['title']), categoryId = subitem['categoryId'][0], subcategory = 1, page = 1)  
                            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
        xbmcplugin.endOfDirectory(_handle, cacheToDisc = True)    

def list_series(label, id, page):
    addon = xbmcaddon.Addon()
    icons_dir = os.path.join(addon.getAddonInfo('path'), 'resources','images')
    kodi_version = get_kodi_version()
    xbmcplugin.setPluginCategory(_handle, label)    
    pagesize = int(addon.getSetting('pagesize'))
    offset = (int(page) - 1) * pagesize

    data = call_graphql(operationName = 'GetEpisodes', variables = '{"limit":' + str(pagesize) + ',"offset":' + str(offset) + ',"idec":"' + str(id) + '","orderBy":"lastTvBroadcast","onlyPlayable":true}')
    if data is None:
        xbmcgui.Dialog().notification('iVysíláni', 'Chyba při načtení epizod', xbmcgui.NOTIFICATION_ERROR, 5000)        
    else:
        totalCount = int(data['totalCount'])
        if int(offset) > 0:
            list_item = xbmcgui.ListItem(label='Předchozí strana (' + str(int(page) - 1) + '/' + str(math.ceil(totalCount/pagesize)) + ')')
            url = get_url(action='list_series', label = label, id = id, page = int(page) - 1)  

            list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'previous_arrow.png'), 'icon' : os.path.join(icons_dir , 'previous_arrow.png') })
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

        for item in data['items']:
            list_item = xbmcgui.ListItem(label = item['title'])
            url = get_url(action='play_id', id = item['id'])  
            list_item.setProperty('IsPlayable', 'true')       
            list_item.setContentLookup(False)          
            if kodi_version >= 20:
                infotag = list_item.getVideoInfoTag()
                infotag.setMediaType('movie')
            else:
                list_item.setInfo('video', {'mediatype' : 'movie'})        
            list_item.setArt({'thumb': item['images']['card'], 'poster' : item['images']['card']})
            if 'description' in item and item['description'] is not None:
                if kodi_version >= 20:
                    infotag.setPlot(item['description'])
                else:
                    list_item.setInfo('video', {'plot': item['description']})  
            xbmcplugin.addDirectoryItem(_handle, url, list_item, False)        

        if  totalCount > int(offset) + pagesize:
            list_item = xbmcgui.ListItem(label='Následující strana (' + str(int(page) + 1) + '/' + str(math.ceil(totalCount/pagesize)) + ')')
            url = get_url(action='list_series', label = label, id = id, page = int(page) + 1)  
            list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'next_arrow.png'), 'icon' : os.path.join(icons_dir , 'next_arrow.png') })
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)


    xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)              

def get_show_listitem(label, id):
    kodi_version = get_kodi_version()
    data = call_graphql(operationName = 'Show', variables = '{"id":"' + str(id) + '"}')
    idec = data['idec']
    list_item = xbmcgui.ListItem(label = data['title'])
    if data['showType'] in ['series', 'magazine']:
        url = get_url(action='list_series', label = label + '/' + encode(data['title']), id = idec, page = 1)  
    else:
        url = get_url(action='play_id', id = idec)  
        list_item.setProperty('IsPlayable', 'true')       
        list_item.setContentLookup(False)          
    if kodi_version >= 20:
        infotag = list_item.getVideoInfoTag()
        infotag.setMediaType('movie')
    else:
        list_item.setInfo('video', {'mediatype' : 'movie'})        
    list_item.setArt({'thumb': data['images']['card'], 'poster' : data['images']['card']})
    if 'shortDescription' in data and data['shortDescription'] is not None:
        if kodi_version >= 20:
            infotag.setPlot(data['shortDescription'])
        else:
            list_item.setInfo('video', {'plot': data['shortDescription']})  
    if data['showType'] in ['series', 'magazine']:
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)              
    else:
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)        

def list_category(label, categoryId, subcategory, page):
    addon = xbmcaddon.Addon()
    icons_dir = os.path.join(addon.getAddonInfo('path'), 'resources','images')
    pagesize = int(addon.getSetting('pagesize'))
    offset = (int(page) - 1) * pagesize
    xbmcplugin.setPluginCategory(_handle, label)
    if int(subcategory) == 0:
        list_item = xbmcgui.ListItem(label = 'Podkategorie')
        url = get_url(action='list_subcategories', label = label, categoryId = categoryId)  
        list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'categories.png'), 'icon' : os.path.join(icons_dir , 'categories.png') })
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)    

    data = call_graphql(operationName = 'GetCategoryById', variables = '{"categoryId":"' + categoryId + '","limit":' + str(pagesize) + ',"offset":' + str(offset) + '}')
    if data is None:
        xbmcgui.Dialog().notification('iVysíláni', 'Chyba při načtení kategorie', xbmcgui.NOTIFICATION_ERROR, 5000)        
    else:
        totalCount = int(data['programmeFind']['totalCount'])
        if int(offset) > 0:
            list_item = xbmcgui.ListItem(label='Předchozí strana (' + str(int(page) - 1) + '/' + str(math.ceil(totalCount/pagesize)) + ')')
            url = get_url(action='list_category', label = label, categoryId = categoryId, subcategory = subcategory, page = int(page) - 1)  
            list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'previous_arrow.png'), 'icon' : os.path.join(icons_dir , 'previous_arrow.png') })
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
            
        for item in data['programmeFind']['items']:
            get_show_listitem(label, item['id'])
           
        if  totalCount > int(offset) + pagesize:
            list_item = xbmcgui.ListItem(label='Následující strana (' + str(int(page) + 1) + '/' + str(math.ceil(totalCount/pagesize)) + ')')
            url = get_url(action='list_category', label = label, categoryId = categoryId, subcategory = subcategory, page = int(page) + 1)  
            list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'next_arrow.png'), 'icon' : os.path.join(icons_dir , 'next_arrow.png') })
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
        xbmcplugin.endOfDirectory(_handle, cacheToDisc = True)  
