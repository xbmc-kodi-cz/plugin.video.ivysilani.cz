# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

import math

from resources.lib.api import call_graphql
from resources.lib.favourites import get_favourites
from resources.lib.utils import get_url, encode, get_kodi_version, plugin_id, encode, ordering

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
    xbmcplugin.setContent(_handle, 'episodes')

    pagesize = int(addon.getSetting('pagesize'))
    offset = (int(page) - 1) * pagesize

    data = call_graphql(operationName = 'GetEpisodes', variables = '{"limit":' + str(pagesize) + ',"offset":' + str(offset) + ',"idec":"' + str(id) + '","orderBy":"newest","onlyPlayable":true}')
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

def get_show_listitem(label, id, favourite = False, title = None, url = None):
    if url is None:
        expand_series = True
    else:
        expand_series = False
    kodi_version = get_kodi_version()
    data = call_graphql(operationName = 'Show', variables = '{"id":"' + str(id) + '"}')
    if data is not None:
        menus = []
        idec = data['idec']
        if title is not None:
            list_item = xbmcgui.ListItem(label = title)
        else:
            list_item = xbmcgui.ListItem(label = data['title'])
        if data['showType'] in ['series', 'magazine'] and expand_series == True:
            url = get_url(action='list_series', label = label + '/' + encode(data['title']), id = idec, page = 1)  
        else:
            if url is None:
                url = get_url(action='play_id', id = idec)  
            list_item.setProperty('IsPlayable', 'true')       
            list_item.setContentLookup(False)          
        if data['showType'] in ['series', 'magazine']:
            menus.append(('Přejít na pořad...', 'Container.Update(' + get_url(action = 'list_series', label = data['title'], id = str(idec), page = 1) + ')'))
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
        if 'year' in data and data['year'] is not None and len(str(data['year'])) > 0:
            if kodi_version >= 20:
                infotag.setYear(int(data['year']))
            else:
                list_item.setInfo('video', {'year': int(data['year'])})    

        if 'flatGenres' in data and data['flatGenres'] is not None and len(data['flatGenres']) > 0:
            genres = []
            for genre in data['flatGenres']:      
              genres.append(genre['title'])
            if kodi_version >= 20:
                infotag.setGenres(genres)
            else:
                list_item.setInfo('video', {'genre' : genres}) 
        if 'countriesOfOrigin' in data and data['countriesOfOrigin'] is not None and len(data['countriesOfOrigin']) > 0:
            if kodi_version >= 20:
                infotag.setCountries([data['countriesOfOrigin'][0]['title']])
            else:
                list_item.setInfo('video', {'countriesOfOrigin': data['countriesOfOrigin'][0]['title']})

        if 'creators' in data and data['creators'] is not None and len(data['creators']) > 0:
            parts = data['creators'].split('.')
            for part in parts:
                part = encode(part).strip().replace(' a další','')
                if ':' in part and 'Režie' in part:
                    directors = []
                    if len(part.split(':')) > 0:
                        directors_data = part.split(':')[1].split(',')
                        for person in directors_data:
                            directors.append(person.strip())
                        if len(directors) > 0:
                            if kodi_version >= 20:
                                infotag.setDirectors(directors)
                            else:
                                list_item.setInfo('video', {'director' : directors})  
                if ':' in part and 'Hrají' in part:
                    cast = []
                    if len(part.split(':')) > 0:
                        cast_data = part.split(':')[1].split(',')
                        for person in cast_data: 
                            if kodi_version >= 20:
                                cast.append(xbmc.Actor(person.strip()))
                            else:
                                cast.append(person)                    
                        if len(cast) > 0:
                            if kodi_version >= 20:
                                infotag.setCast(cast)
                            else:
                                list_item.setInfo('video', {'castandrole' : cast})  

        if favourite == True:
            menus.append(('Odstranit z oblíbených iVysíláni', 'RunPlugin(plugin://' + plugin_id + '?action=remove_favourite&item=' + str(id) + ')'))
        else:
            menus.append(('Přidat do oblíbených iVysíláni', 'RunPlugin(plugin://' + plugin_id + '?action=add_favourite&item=' + str(id) + ')'))
        if len(menus) > 0:
            list_item.addContextMenuItems(menus, replaceItems = True)        

        if data['showType'] in ['series', 'magazine'] and expand_series == True:
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)              
        else:
            xbmcplugin.addDirectoryItem(_handle, url, list_item, False)        

def list_category(label, categoryId, subcategory, page):
    addon = xbmcaddon.Addon()
    icons_dir = os.path.join(addon.getAddonInfo('path'), 'resources','images')
    pagesize = int(addon.getSetting('pagesize'))
    offset = (int(page) - 1) * pagesize
    xbmcplugin.setPluginCategory(_handle, label)
    xbmcplugin.setContent(_handle, 'movies')
    if int(subcategory) == 0:
        list_item = xbmcgui.ListItem(label = 'Podkategorie')
        url = get_url(action='list_subcategories', label = label, categoryId = categoryId)  
        list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'categories.png'), 'icon' : os.path.join(icons_dir , 'categories.png') })
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)    

    data = call_graphql(operationName = 'GetCategoryById', variables = '{"categoryId":"' + categoryId + '","limit":' + str(pagesize) + ',"offset":' + str(offset) + ',' + ordering[addon.getSetting('categories_order')] + '}')
    if data is None:
        xbmcgui.Dialog().notification('iVysíláni', 'Chyba při načtení kategorie', xbmcgui.NOTIFICATION_ERROR, 5000)        
    else:
        totalCount = int(data['programmeFind']['totalCount'])
        if int(offset) > 0:
            list_item = xbmcgui.ListItem(label='Předchozí strana (' + str(int(page) - 1) + '/' + str(math.ceil(totalCount/pagesize)) + ')')
            url = get_url(action='list_category', label = label, categoryId = categoryId, subcategory = subcategory, page = int(page) - 1)  
            list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'previous_arrow.png'), 'icon' : os.path.join(icons_dir , 'previous_arrow.png') })
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

        favourites = get_favourites()
        for item in data['programmeFind']['items']:
            if int(item['id']) in favourites:
                favourite = True
            else:
                favourite = False
            get_show_listitem(label, item['id'], favourite)
           
        if  totalCount > int(offset) + pagesize:
            list_item = xbmcgui.ListItem(label='Následující strana (' + str(int(page) + 1) + '/' + str(math.ceil(totalCount/pagesize)) + ')')
            url = get_url(action='list_category', label = label, categoryId = categoryId, subcategory = subcategory, page = int(page) + 1)  
            list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'next_arrow.png'), 'icon' : os.path.join(icons_dir , 'next_arrow.png') })
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
        xbmcplugin.endOfDirectory(_handle, cacheToDisc = True)  
