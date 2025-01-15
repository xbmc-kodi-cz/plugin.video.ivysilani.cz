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
import time
try:
    from StringIO import BytesIO # type: ignore
except ImportError:
    from io import BytesIO # type: ignore

from resources.lib.utils import ua, graphql_url

GRAPHQL = { 'CurrentBroadcast' : '{"persistedQuery":{"version":1,"sha256Hash":"389c87717d866889c7a97c3452448c255c68dd1a78e155e15839e782672154c9"}}',
            'LiveBroadcastFind' : '{"persistedQuery":{"version":1,"sha256Hash":"bb3130f883abe674a50e02962ccce18b14bb7194700c73e8bb2a1474d1292082"}}',
            'Categories' : '{"persistedQuery":{"version":1,"sha256Hash":"9c1f01e5eb56c808d38ad46cd0b2e88e4acc235af9a88ea947fe1a04cbfff329"}}',
#           'CategoryMenu' : '{"persistedQuery":{"version":1,"sha256Hash":"2f75393bd74faae039f60fe26b1248e6819f794e489234573e9c829b4dfa2827"}}',
           'GetCategoryById' : '{"persistedQuery":{"version":1,"sha256Hash":"793f96231cd326e46a3db0c0f6b07aba3c75fae2351b1476119885b2733b7b64"}}',
           'Show' : '{"persistedQuery":{"version":1,"sha256Hash":"60d2f49d4f4213fc11b287d58190f33bc1461bbc740cb79a290fd168781ab913"}}',
           'SearchShows' : '{"persistedQuery":{"version":1,"sha256Hash":"b5275e0a1c0320064fa11f492469825db0006f94e5f7b1c0fff9e4976c63bf7e"}}',
           'GetEpisodes' : '{"persistedQuery":{"version":1,"sha256Hash":"069bc67c71d69634e6653ac19166e9f94a7db83ec234f35f90fa63ad45caf69d"}}',
           'TVProgramChannelsList' : '{"persistedQuery":{"version":1,"sha256Hash":"bd7ad903729d72514769cca80174d142d1338bdcf353e70b2be8dd8653ffb918"}}',
           'TvProgramDaily' : '{"persistedQuery":{"version":1,"sha256Hash":"661cff054ced91ce2671f85bd398bee5ea5686a2d3f56f46ef5ce19b1ec632a4"}}',
           'TvProgramDailyTablet' : '{"persistedQuery":{"version":1,"sha256Hash":"e661b593b712f0b533a989d75413136bf4459dcf0ee13522538145cd74cad1b3"}}',
           'HomepageBlock' : '{"persistedQuery":{"version":1,"sha256Hash":"2787c318baa800372e53486b85000934ae6603f79b1cdd092966ea881226ceac"}}',
           'HomepageRows' : '{"persistedQuery":{"version":1,"sha256Hash":"d1dcd6054b78bb4e97f986f031e75ecf37f3074eb61e97f588101de866ce5805"}}',
          }

def call_graphql(operationName, variables):
    url = graphql_url + 'operationName=' + operationName + '&variables=' + variables + '&extensions=' + GRAPHQL[operationName]
    ok = False
    err = 0
    while ok == False and err < 10:
        data = call_api(url = url)
        if 'errors' in data and data['errors'] and 'message' in data['errors'][0] and data['errors'][0]['message'] == 'PersistedQueryNotFound':
            err = err + 1
            time.sleep(0.5)
        else:
            ok = True
    time.sleep(0.5)
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

