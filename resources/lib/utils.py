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
iso639map = {'aar': 'aa', 'ave': 'ae', 'afr': 'af', 'aka': 'ak', 'amh': 'am', 'arg': 'an', 'ara': 'ar', 'asm': 'as', 'ava': 'av', 'aym': 'ay', 'aze': 'az', 'bak': 'ba', 'bel': 'be', 'bul': 'bg', 'bis': 'bi', 'bam': 'bm', 'ben': 'bn', 'bod': 'bo', 'bre': 'br', 'bos': 'bs', 'cat': 'ca', 'che': 'ce', 'cos': 'co', 'cre': 'cr', 'ces': 'cs', 'chu': 'cu', 'chv': 'cv', 'cym': 'cy', 'dan': 'da', 'deu': 'de', 'div': 'dv', 'dzo': 'dz', 'ewe': 'ee', 'ell': 'el', 'eng': 'en', 'epo': 'eo', 'spa': 'es', 'est': 'et', 'eus': 'eu', 'fas': 'fa', 'ful': 'ff', 'fin': 'fi', 'fij': 'fj', 'fao': 'fo', 'fra': 'fr', 'fry': 'fy', 'gle': 'ga', 'gla': 'gd', 'glg': 'gl', 'grn': 'gn', 'guj': 'gu', 'glv': 'gv', 'hau': 'ha', 'heb': 'he', 'hin': 'hi', 'hmo': 'ho', 'hrv': 'hr', 'hat': 'ht', 'hun': 'hu', 'hye': 'hy', 'her': 'hz', 'cha': 'ch', 'ina': 'ia', 'ind': 'id', 'ile': 'ie', 'ibo': 'ig', 'iii': 'ii', 'ipk': 'ik', 'ido': 'io', 'isl': 'is', 'ita': 'it', 'iku': 'iu', 'jpn': 'ja', 'jav': 'jv', 'kat': 'ka', 'kon': 'kg', 'kik': 'ki', 'kua': 'kj', 'kaz': 'kk', 'kal': 'kl', 'khm': 'km', 'kan': 'kn', 'kor': 'ko', 'kau': 'kr', 'kas': 'ks', 'kur': 'ku', 'kom': 'kv', 'cor': 'kw', 'kir': 'ky', 'lat': 'la', 'ltz': 'lb', 'lug': 'lg', 'lim': 'li', 'lin': 'ln', 'lao': 'lo', 'lit': 'lt', 'lub': 'lu', 'lav': 'lv', 'mlg': 'mg', 'mah': 'mh', 'mri': 'mi', 'mkd': 'mk', 'mal': 'ml', 'mon': 'mn', 'mar': 'mr', 'msa': 'ms', 'mlt': 'mt', 'mya': 'my', 'nau': 'na', 'nob': 'nb', 'nde': 'nd', 'nep': 'ne', 'ndo': 'ng', 'nld': 'nl', 'nno': 'nn', 'nor': 'no', 'nbl': 'nr', 'nav': 'nv', 'nya': 'ny', 'oci': 'oc', 'oji': 'oj', 'orm': 'om', 'ori': 'or', 'oss': 'os', 'pan': 'pa', 'pli': 'pi', 'pol': 'pl', 'pus': 'ps', 'por': 'pt', 'que': 'qu', 'roh': 'rm', 'run': 'rn', 'ron': 'ro', 'rus': 'ru', 'kin': 'rw', 'san': 'sa', 'srd': 'sc', 'snd': 'sd', 'sme': 'se', 'sag': 'sg', 'sin': 'si', 'slk': 'sk', 'slv': 'sl', 'smo': 'sm', 'sna': 'sn', 'som': 'so', 'sqi': 'sq', 'srp': 'sr', 'ssw': 'ss', 'sot': 'st', 'sun': 'su', 'swe': 'sv', 'swa': 'sw', 'tam': 'ta', 'tel': 'te', 'tgk': 'tg', 'tha': 'th', 'tir': 'ti', 'tuk': 'tk', 'tgl': 'tl', 'tsn': 'tn', 'ton': 'to', 'tur': 'tr', 'tso': 'ts', 'tat': 'tt', 'twi': 'tw', 'tah': 'ty', 'uig': 'ug', 'ukr': 'uk', 'urd': 'ur', 'uzb': 'uz', 'ven': 've', 'vie': 'vi', 'vol': 'vo', 'wln': 'wa', 'wol': 'wo', 'xho': 'xh', 'yid': 'yi', 'yor': 'yo', 'zha': 'za', 'zho': 'zh', 'zul': 'zu'}
ordering = {'od nejsledovanějších' : {'orderBy' : 'popular_previous_seven_days'}, 'od nejnovějších' : {'order' : 'desc' , 'orderBy' : 'premiere'}, 'abecedně' : {'order' : 'asc', 'orderBy' : 'alphabet'}}
graphql_url = 'https://api.ceskatelevize.cz/graphql/'
params = {'client' : 'iVysilaniWeb', 'version' : '1.131.1', 'use-new-playability' : True}
channels = {'CH_1' : 'ČT1', 'CH_2' : 'ČT2', 'CH_4' : 'ČT Sport', 'CH_24' : 'ČT24', 'CH_5' : 'ČT :D', 'CH_6' : 'ČT art', 'CH_25' : "ČT Sport Plus 1", 'CH_25' : "ČT Sport Plus 1", 'CH_26' : "ČT Sport Plus 2", 'CH_27' : "ČT Sport Plus 3", 'CH_28' : "ČT Sport Plus 4", 'CH_29' : "ČT Sport Plus 5", 'CH_30' : "ČT Sport Plus 6", 'CH_31' : "ČT Sport Plus 7", 'CH_32' : "ČT Sport Plus 8"}

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
      
