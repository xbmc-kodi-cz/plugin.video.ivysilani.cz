# -*- coding: utf-8 -*-
import sys
import os
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc

try:
    from xbmcvfs import translatePath
except ImportError:
    from xbmc import translatePath

import sqlite3
import json

from resources.lib.api import call_graphql
from resources.lib.utils import get_url, get_kodi_version, encode, plugin_id

if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

current_version = 1

def open_db():
    global db, version
    addon = xbmcaddon.Addon()
    addon_userdata_dir = translatePath(addon.getAddonInfo('profile')) 
    if not os.path.isdir(addon_userdata_dir):
        os.mkdir(addon_userdata_dir)
    db = sqlite3.connect(addon_userdata_dir + 'items_data.db', timeout = 10)
    db.execute('CREATE TABLE IF NOT EXISTS version (version INTEGER PRIMARY KEY)')
    db.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, idec INTEGER, showType VARCHAR(255), title VARCHAR(255), description VARCHAR(255), image VARCHAR(255), cast VARCHAR(255), directors VARCHAR(255), year VARCHAR(255), country VARCHAR(255), genres VARCHAR(255))')
    row = None
    for row in db.execute('SELECT version FROM version'):
        version = row[0]
    if not row:
        db.execute('INSERT INTO version VALUES (?)', [current_version])
        db.commit()     
        version = current_version
    if version != current_version:
        version = migrate_db(version)

def close_db():
    global db
    db.close()    

def migrate_db(version):
    global db
    return version

def remove_db():
    addon = xbmcaddon.Addon()
    addon_userdata_dir = translatePath(addon.getAddonInfo('profile'))
    filename = os.path.join(addon_userdata_dir, 'items_data.db')
    if os.path.exists(filename):
        try:
            os.remove(filename) 
            xbmcgui.Dialog().notification('iVysílání', 'Keš byla vymazána', xbmcgui.NOTIFICATION_INFO, 5000)    
        except IOError:
            xbmcgui.Dialog().notification('iVysílání', 'Chyba při mazání keše!', xbmcgui.NOTIFICATION_ERROR, 5000)    

def get_data_from_api(id, cache):
    global db
    item_data = {}
    data = call_graphql(operationName = 'Show', variables = '{"id":"' + str(id) + '"}')
    if data is not None:
        idec = int(data['idec'])
        showType = data['showType']
        title = data['title']
        description = ''
        image = data['images']['card']
        cast = []
        directors = []
        year = ''
        country = ''
        genres = []

        if 'shortDescription' in data and data['shortDescription'] is not None:
            description = data['shortDescription']

        if 'year' in data and data['year'] is not None and len(str(data['year'])) > 0:
                year = str(data['year'])

        if 'flatGenres' in data and data['flatGenres'] is not None and len(data['flatGenres']) > 0:
            for genre in data['flatGenres']:      
                genres.append(genre['title'])

        if 'countriesOfOrigin' in data and data['countriesOfOrigin'] is not None and len(data['countriesOfOrigin']) > 0:
            country = data['countriesOfOrigin'][0]['title']

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
                if ':' in part and 'Hrají' in part:
                    cast = []
                    if len(part.split(':')) > 0:
                        cast_data = part.split(':')[1].split(',')
                        for person in cast_data: 
                            cast.append(person)
        if cache == True:
            db.execute('INSERT INTO items VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (id, idec, showType, title, description, image, json.dumps(cast), json.dumps(directors), year, country, json.dumps(genres)))      
            db.commit()
        item_data = { 'id' : id, 'idec' : idec, 'showType' : showType, 'title' : title, 'description' : description, 'image' : image, 'cast' : cast, 'directors' : directors, 'year' : year, 'country' : country, 'genres' : genres }
    return item_data        

def get_item_data(id, cache = True):
    global db
    item_data = {}
    addon = xbmcaddon.Addon()
    if addon.getSetting('use_cache') == 'true' and cache == True:
        open_db()
        row = None
        for row in db.execute('SELECT idec, showType, title, description, image, "cast", directors, year, country, genres FROM items WHERE id = ?', [id]):
            idec = row[0]
            showType = row[1]
            title = row[2]
            description = row[3]
            image = row[4]
            cast = json.loads(row[5])
            directors = json.loads(row[6])
            year = row[7]
            country = row[8]
            genres = json.loads(row[9])
        if not row:
            item_data = get_data_from_api(id, cache)
        else:
            item_data = { 'id' : id, 'idec' : idec, 'showType' : showType, 'title' : title, 'description' : description, 'image' : image, 'cast' : cast, 'directors' : directors, 'year' : year, 'country' : country, 'genres' : genres }                
        close_db()            
    else:
        cache = False
        item_data = get_data_from_api(id, cache)
    return item_data

def get_show_listitem(label, id, favourite = False, title = None, url = None):
    if url is None:
        expand_series = True
        cache = True
    else:
        expand_series = False
        cache = False
    kodi_version = get_kodi_version()
    item_data = get_item_data(int(id), cache)
    if len(item_data) > 0:
        menus = []
        idec = item_data['idec']
        if title is not None:
            list_item = xbmcgui.ListItem(label = title)
        else:
            list_item = xbmcgui.ListItem(label = item_data['title'])
        if item_data['showType'] in ['series', 'magazine'] and expand_series == True:
            url = get_url(action='list_series', label = label + '/' + encode(item_data['title']), id = idec, page = 1)  
        else:
            if url is None:
                url = get_url(action='play_id', id = idec)  
            list_item.setProperty('IsPlayable', 'true')       
            list_item.setContentLookup(False)          
        if item_data['showType'] in ['series', 'magazine']:
            menus.append(('Přejít na pořad...', 'Container.Update(' + get_url(action = 'list_series', label = encode(item_data['title']), id = str(idec), page = 1) + ')'))
        if kodi_version >= 20:
            infotag = list_item.getVideoInfoTag()
            infotag.setMediaType('movie')
        else:
            list_item.setInfo('video', {'mediatype' : 'movie'})     
        list_item.setArt({'thumb': item_data['image'], 'poster' : item_data['image']})
        if kodi_version >= 20:
            infotag.setPlot(item_data['description'])
        else:
            list_item.setInfo('video', {'plot': item_data['description']})  
        if len(item_data['year']) > 0:
            if kodi_version >= 20:
                infotag.setYear(int(item_data['year']))
            else:
                list_item.setInfo('video', {'year': int(item_data['year'])})    

        if len(item_data['genres']) > 0:
            if kodi_version >= 20:
                infotag.setGenres(item_data['genres'])
            else:
                list_item.setInfo('video', {'genre' : item_data['genres']}) 
        if len(item_data['country']) > 0:
            if kodi_version >= 20:
                infotag.setCountries([item_data['country']])
            else:
                list_item.setInfo('video', {'country': item_data['country']})


        if len(item_data['directors']) > 0:
            if kodi_version >= 20:
                infotag.setDirectors(item_data['directors'])
            else:
                list_item.setInfo('video', {'director' : item_data['directors']})  
    
        if len(item_data['cast']) > 0:
            cast = []
            for person in item_data['cast']: 
                if kodi_version >= 20:
                    cast.append(xbmc.Actor(person.strip()))
                else:
                    cast.append(person)              
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

        if item_data['showType'] in ['series', 'magazine'] and expand_series == True:
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)              
        else:
            xbmcplugin.addDirectoryItem(_handle, url, list_item, False)        
