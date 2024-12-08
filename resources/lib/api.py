# -*- coding: utf-8 -*-
import xbmcaddon
import xbmc

try:
    from urllib.request import urlopen, Request # type: ignore
    from urllib.error import HTTPError # type: ignore
except ImportError:
    from urllib2 import urlopen, Request, HTTPError # type: ignore

import json
import gzip 
try:
    from StringIO import BytesIO # type: ignore
except ImportError:
    from io import BytesIO # type: ignore

from resources.lib.utils import ua, graphql_url

GRAPHQL = {'LiveBroadcastFind' : '{"persistedQuery":{"version":1,"sha256Hash":"bb3130f883abe674a50e02962ccce18b14bb7194700c73e8bb2a1474d1292082"}}',
           'CategoryMenu' : '{"persistedQuery":{"version":1,"sha256Hash":"2f75393bd74faae039f60fe26b1248e6819f794e489234573e9c829b4dfa2827"}}',
           'GetCategoryById' : '{"persistedQuery":{"version":1,"sha256Hash":"793f96231cd326e46a3db0c0f6b07aba3c75fae2351b1476119885b2733b7b64"}}',
           'Show' : '{"persistedQuery":{"version":1,"sha256Hash":"60d2f49d4f4213fc11b287d58190f33bc1461bbc740cb79a290fd168781ab913"}}',
           'SearchShows' : '{"persistedQuery":{"version":1,"sha256Hash":"b5275e0a1c0320064fa11f492469825db0006f94e5f7b1c0fff9e4976c63bf7e"}}',
           'GetEpisodes' : '{"persistedQuery":{"version":1,"sha256Hash":"069bc67c71d69634e6653ac19166e9f94a7db83ec234f35f90fa63ad45caf69d"}}',
           'TVProgramChannelsList' : '{"persistedQuery":{"version":1,"sha256Hash":"bd7ad903729d72514769cca80174d142d1338bdcf353e70b2be8dd8653ffb918"}}',
           'TvProgramDaily' : '{"persistedQuery":{"version":1,"sha256Hash":"661cff054ced91ce2671f85bd398bee5ea5686a2d3f56f46ef5ce19b1ec632a4"}}',
           'TvProgramDailyTablet' : '{"persistedQuery":{"version":1,"sha256Hash":"e661b593b712f0b533a989d75413136bf4459dcf0ee13522538145cd74cad1b3"}}'
          }
#https://api.ceskatelevize.cz/graphql/?client=iVysilaniWeb&version=1.124.1&use-new-playability=true&operationName=HomepageConfigQuery&variables={}&extensions={"persistedQuery":{"version":1,"sha256Hash":"3baa90011284bfaaa256cfcca1366b41166684873c42ee66851740f7060935d8"}}
#https://api.ceskatelevize.cz/graphql/?client=iVysilaniWeb&version=1.124.1&use-new-playability=true&operationName=HomepageBlockQuery&variables={"id":"100100","limit":12,"offset":0}&extensions={"persistedQuery":{"version":1,"sha256Hash":"0d1334d988371c8b3bbeea4ad0eb66b3c31abb0760f6b79efc2f78051a31f75d"}}

#https://api.ceskatelevize.cz/graphql/?client=iVysilaniWeb&version=1.124.1&use-new-playability=true&operationName=GetRelatedProgrammes&variables={"id":"15349949706","limit":4,"source":"AVRO_B"}&extensions={"persistedQuery":{"version":1,"sha256Hash":"bb7797151cf99e3157d206299cc212616ec198d0d653a67fa261c7735bd3a941"}}
#https://api.ceskatelevize.cz/graphql/?client=iVysilaniWeb&version=1.124.0&use-new-playability=true&operationName=NextEpisode&variables={"currentEpisodeIdec":"22054416016"}&extensions={"persistedQuery":{"version":1,"sha256Hash":"ffd1efa0e54a8904b041378eb63173bbde321b14e153e04632e1c4b309836408"}}
#https://api.ceskatelevize.cz/graphql/?client=iVysilaniWeb&version=1.124.0&use-new-playability=true&operationName=Medium&variables={"id":"22054416016","includeLiveEncoder":false}&extensions={"persistedQuery":{"version":1,"sha256Hash":"9db47789e7af5c226984188c2a2fe4479d11b2be4e1f33de5989548b436a61cd"}}
#https://api.ceskatelevize.cz/graphql/?client=iVysilaniWeb&version=1.124.0&use-new-playability=true&operationName=SearchEpisodes&variables={"limit":5,"offset":0,"search":"test","onlyPlayable":false}&extensions={"persistedQuery":{"version":1,"sha256Hash":"2d1f7dfd3a5d043891fd7a761fa592ef776923572bbf440e25dde6c29b4f0ad1"}}

def call_graphql(operationName, variables):
    url = graphql_url + 'operationName=' + operationName + '&variables=' + variables + '&extensions=' + GRAPHQL[operationName]
    data = call_api(url = url)
    if 'data' not in data or data['data'] is None:
        return None
    for result in data['data']:
        return data['data'][result]
    return None

def call_api(url, data = None, method = None):
    addon = xbmcaddon.Addon()
    headers = {'User-Agent': ua, 'Accept-language' : 'cs', 'Accept-Encoding' : 'gzip', 'Accept': 'application/json; charset=utf-8', 'Content-type' : 'application/json;charset=UTF-8'}
    if data != None:
        data = json.dumps(data).encode("utf-8")
    if addon.getSetting('log_requests') == 'true':
        xbmc.log(url)
    if method is not None:
        request = Request(url = url, data = data, method = method, headers = headers)
    else:
        request = Request(url = url, data = data, headers = headers)
    try:
        response = urlopen(request)
        if 'Content-Encoding' in response.headers and response.headers['Content-Encoding'] == 'gzip':
            gzipFile = gzip.GzipFile(fileobj = BytesIO(response.read()))
            html = gzipFile.read()
        else:
            html = response.read()        
        if addon.getSetting('log_requests') == 'true':
            xbmc.log(str(html))
        if html and len(html) > 0:
            data = json.loads(html)
            return data
        else:
            return []
    except HTTPError as e:
        return { 'err' : e.reason }      

