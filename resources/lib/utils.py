# -*- coding: utf-8 -*-
import sys
import xbmc

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0'

plugin_id = 'plugin.video.ivysilani.cz'
day_translation = {'1' : 'Pondělí', '2' : 'Úterý', '3' : 'Středa', '4' : 'Čtvrtek', '5' : 'Pátek', '6' : 'Sobota', '0' : 'Neděle'}  
day_translation_short = {'1' : 'Po', '2' : 'Út', '3' : 'St', '4' : 'Čt', '5' : 'Pá', '6' : 'So', '0' : 'Ne'}  
view_modes = {'Seznam' : '50', 'Široký seznam' : '55', 'Posun' : '53', 'Infostěna' : '54', 'Zeď' : '500', 'Fanart' : '502'}
graphql_url = 'https://api.ceskatelevize.cz/graphql/?client=iVysilaniWeb&version=1.124.0&use-new-playability=true&'

_url = sys.argv[0]

def get_url(**kwargs):
    return '{0}?{1}'.format(_url, urlencode(kwargs))

def decode(string_to_decode):
    if PY2:
        return string_to_decode.decode('utf-8')
    else:
        return string_to_decode

def encode(string_to_encode):
    if PY2:
        return string_to_encode.encode('utf-8')
    else:
        return string_to_encode  
    
def get_kodi_version():
    return int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])  
      
