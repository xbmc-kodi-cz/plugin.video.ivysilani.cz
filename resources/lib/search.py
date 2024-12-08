# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

import math 

from resources.lib.api import call_graphql
from resources.lib.category import get_show_listitem
from resources.lib.utils import get_url, plugin_id

_handle = int(sys.argv[1])

def list_search(label):
    xbmcplugin.setPluginCategory(_handle, label)
    list_item = xbmcgui.ListItem(label='Nové hledání')
    url = get_url(action='program_search', query = '-----', label = label + ' / ' + 'Nové hledání', page = 1)  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    history = load_search_history()
    for item in history:
        list_item = xbmcgui.ListItem(label=item)
        url = get_url(action='program_search', query = item, label = label + ' / ' + item, page = 1)  
        list_item.addContextMenuItems([('Smazat', 'RunPlugin(plugin://' + plugin_id + '?action=delete_search&query=' + quote(item) + ')')])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle,cacheToDisc = False)

def program_search(query, label, page):
    addon = xbmcaddon.Addon()
    icons_dir = os.path.join(addon.getAddonInfo('path'), 'resources','images')
    xbmcplugin.setPluginCategory(_handle, label)
    if query == '-----':
        input = xbmc.Keyboard('', 'Hledat')
        input.doModal()
        if not input.isConfirmed(): 
            return
        query = input.getText()
        if len(query) == 0:
            xbmcgui.Dialog().notification('iVysíláni', 'Je potřeba zadat vyhledávaný řetězec', xbmcgui.NOTIFICATION_ERROR, 5000)
            return   
        else:
            save_search_history(query)
            
    pagesize = int(addon.getSetting('pagesize'))
    offset = (int(page) - 1) * pagesize
    data = call_graphql(operationName = 'SearchShows', variables = '{"limit":' + str(pagesize) + ',"offset":' + str(offset) + ',"search":"' + quote(query) + '","onlyPlayable":true}')            
    if data is None:
        xbmcgui.Dialog().notification('iVysíláni', 'Chyba načtení pořadů', xbmcgui.NOTIFICATION_ERROR, 5000)
    else:
        if 'items' in data and len(data['items']) > 0:
            totalCount = int(data['totalCount'])

            if int(offset) > 0:
                list_item = xbmcgui.ListItem(label='Předchozí strana (' + str(int(page) - 1) + '/' + str(math.ceil(totalCount/pagesize)) + ')')
                url = get_url(action='program_search', query = query, label = label, page = int(page) - 1)  
                list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'previous_arrow.png'), 'icon' : os.path.join(icons_dir , 'previous_arrow.png') })
                xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

            for item in data['items']:
                get_show_listitem(label, item['id'])

            if  totalCount > int(offset) + pagesize:
                list_item = xbmcgui.ListItem(label='Následující strana (' + str(int(page) + 1) + '/' + str(math.ceil(totalCount/pagesize)) + ')')
                url = get_url(action='program_search', query = query, label = label, page = int(page) + 1)  
                list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'next_arrow.png'), 'icon' : os.path.join(icons_dir , 'next_arrow.png') })
                xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

            xbmcplugin.endOfDirectory(_handle, cacheToDisc = False)                  

        else:
            xbmcgui.Dialog().notification('iVysíláni','Nic nenalezeno', xbmcgui.NOTIFICATION_INFO, 3000)

def save_search_history(query):
    addon = xbmcaddon.Addon()
    addon_userdata_dir = translatePath(addon.getAddonInfo('profile')) 
    max_history = 10
    cnt = 0
    history = []
    filename = addon_userdata_dir + 'search_history.txt'
    if not os.path.exists(addon_userdata_dir):
        os.makedirs(addon_userdata_dir)

    try:
        with open(filename, 'r') as file:
            for line in file:
                item = line[:-1]
                history.append(item)
    except IOError:
        history = []
    history.insert(0,query)
    with open(filename, 'w') as file:
        for item  in history:
            cnt = cnt + 1
            if cnt <= max_history:
                file.write('%s\n' % item)

def load_search_history():
    history = []
    addon = xbmcaddon.Addon()
    addon_userdata_dir = translatePath(addon.getAddonInfo('profile')) 
    filename = addon_userdata_dir + 'search_history.txt'
    try:
        with open(filename, 'r') as file:
            for line in file:
                item = line[:-1]
                history.append(item)
    except IOError:
        history = []
    return history

def delete_search(query):
    addon = xbmcaddon.Addon()
    addon_userdata_dir = translatePath(addon.getAddonInfo('profile')) 
    filename = addon_userdata_dir + 'search_history.txt'
    history = load_search_history()
    for item in history:
        if item == query:
            history.remove(item)
    try:
        with open(filename, 'w') as file:
            for item in history:
                file.write('%s\n' % item)
    except IOError:
        pass
    xbmc.executebuiltin('Container.Refresh')