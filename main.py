# -*- coding: utf-8 -*-
import os
import sys
import xbmcgui
import xbmcplugin
import xbmcaddon

try:
    from urlparse import parse_qsl # type: ignore
except ImportError:
    from urllib.parse import parse_qsl # type: ignore

from resources.lib.live import list_channels
from resources.lib.category import list_categories, list_subcategories, list_category, list_series
from resources.lib.stream import play_channel, play_id
from resources.lib.archive import list_archive, list_archive_days, list_program
from resources.lib.search import list_search, delete_search, program_search
from resources.lib.utils import get_url

if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

def list_settings(label):
    _handle = int(sys.argv[1])
    xbmcplugin.setPluginCategory(_handle, label)

    list_item = xbmcgui.ListItem(label = 'Nastavení doplňku')
    url = get_url(action='addon_settings', label = 'Nastavení doplňku')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def list_menu():
    addon = xbmcaddon.Addon()
    icons_dir = os.path.join(addon.getAddonInfo('path'), 'resources','images')

    list_item = xbmcgui.ListItem(label = 'Živě')
    url = get_url(action='list_channels', label = 'Živě')  
    list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'livetv.png'), 'icon' : os.path.join(icons_dir , 'livetv.png') })
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label = 'Archiv')
    url = get_url(action='list_archive', label = 'Archiv')  
    list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'archive.png'), 'icon' : os.path.join(icons_dir , 'archive.png') })
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label = 'Kategorie')
    url = get_url(action='list_categories', label = 'Kategorie')  
    list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'categories.png'), 'icon' : os.path.join(icons_dir , 'categories.png') })
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label = 'Vyhledávání')
    url = get_url(action='list_search', label = 'Vyhledávání')  
    list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'search.png'), 'icon' : os.path.join(icons_dir , 'search.png') })
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label = 'Nastavení')
    url = get_url(action='addon_settings', label = 'Nastavení')  
    list_item.setArt({ 'thumb' : os.path.join(icons_dir , 'settings.png'), 'icon' : os.path.join(icons_dir , 'settings.png') })
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = True)    

def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params['action'] == 'list_categories':
            list_categories(params['label'])
        elif params['action'] == 'list_subcategories':
            list_subcategories(params['label'], params['categoryId'])            
        elif params['action'] == 'list_category':
            list_category(params['label'], params['categoryId'], params['subcategory'], params['page'])
        elif params['action'] == 'list_series':
            list_series(params['label'], params['id'], params['page'])            
        elif params['action'] == 'play_id':
            play_id(params['id'])

        elif params['action'] == 'list_channels':
            list_channels(params['label'])
        elif params['action'] == 'play_channel':
            play_channel(params['channelId'])

        elif params['action'] == 'list_archive':
            list_archive(params['label'])
        elif params['action'] == 'list_archive_days':
            list_archive_days(params['label'], params['channel'])
        elif params['action'] == 'list_program':
            list_program(params['label'], params['channel'], params['day_min'])

        elif params['action'] == 'list_search':
            list_search(params['label'])
        elif params['action'] == 'program_search':
            program_search(params['query'], params['label'], params['page'])
        elif params['action'] == 'delete_search':
            delete_search(params['query'])

        elif params['action'] == 'list_settings':
            list_settings(params['label'])
        elif params['action'] == 'addon_settings':
            xbmcaddon.Addon().openSettings()
        else:
            raise ValueError('Neznámý parametr: {0}!'.format(paramstring))
    else:
         list_menu()

if __name__ == '__main__':
    router(sys.argv[2][1:])
