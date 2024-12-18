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

import codecs
import json

if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

def add_favourite(item):  
    item = json.loads(item)
    addon = xbmcaddon.Addon()
    addon_userdata_dir = translatePath(addon.getAddonInfo('profile'))
    if not os.path.exists(addon_userdata_dir):
        os.makedirs(addon_userdata_dir)    
    filename = os.path.join(addon_userdata_dir, 'favourites.txt')
    favourites = get_favourites()
    if item not in favourites:
        favourites.append(item)
        try:
            with codecs.open(filename, 'w', encoding='utf-8') as file:
                file.write('%s\n' % json.dumps(favourites))        
        except IOError as error:
            xbmcgui.Dialog().notification('iVysíláni', 'Chyba při uložení oblíbených pořadů', xbmcgui.NOTIFICATION_ERROR, 5000)            
        xbmcgui.Dialog().notification('iVysíláni', 'Pořad byl přidaný do oblíbených', xbmcgui.NOTIFICATION_INFO, 5000)
    else:
        xbmcgui.Dialog().notification('iVysíláni', 'Pořad je již v oblíbených', xbmcgui.NOTIFICATION_ERROR, 5000)

def remove_favourite(item):
    item = json.loads(item)
    addon = xbmcaddon.Addon()
    addon_userdata_dir = translatePath(addon.getAddonInfo('profile'))
    filename = os.path.join(addon_userdata_dir, 'favourites.txt')
    favourites = get_favourites()
    favourites.remove(item)
    try:
        with codecs.open(filename, 'w', encoding='utf-8') as file:
            file.write('%s\n' % json.dumps(favourites))        
    except IOError:
        xbmcgui.Dialog().notification('iVysíláni', 'Chyba při uložení oblíbených pořadů', xbmcgui.NOTIFICATION_ERROR, 5000)            
    xbmc.executebuiltin('Container.Refresh')

def get_favourites():
    addon = xbmcaddon.Addon()
    addon_userdata_dir = translatePath(addon.getAddonInfo('profile'))
    filename = os.path.join(addon_userdata_dir, 'favourites.txt')
    data = None
    try:
        with codecs.open(filename, 'r', encoding='utf-8') as file:
            for row in file:
                data = row[:-1]
    except IOError as error:
        if error.errno != 2:
            xbmcgui.Dialog().notification('iVysíláni', 'Chyba při načtení oblíbených pořadů', xbmcgui.NOTIFICATION_ERROR, 5000)
            sys.exit()
    if data is not None:
        favourites = json.loads(data)
    else:
        favourites = []
    return favourites

def list_favourites(label):
    from resources.lib.items import get_show_listitem
    xbmcplugin.setPluginCategory(_handle, label)
    xbmcplugin.setContent(_handle, 'movies')
    favourites = get_favourites()
    for id in favourites:
        get_show_listitem(label, id, True)
    xbmcplugin.endOfDirectory(_handle)  