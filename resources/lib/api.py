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

GRAPHQL = { 
           'CurrentBroadcast' : '{"persistedQuery":{"version":1,"sha256Hash":"389c87717d866889c7a97c3452448c255c68dd1a78e155e15839e782672154c9"}}',
           'LiveBroadcastFind' : '{"persistedQuery":{"version":1,"sha256Hash":"dbe5f832b7fb5830bda984155f49b4b8c055c1f3f5de8561bfda05ed5658ae61"}}',
           'Categories' : '{"persistedQuery":{"version":1,"sha256Hash":"9c1f01e5eb56c808d38ad46cd0b2e88e4acc235af9a88ea947fe1a04cbfff329"}}',
#           'CategoryMenu' : '{"persistedQuery":{"version":1,"sha256Hash":"2f75393bd74faae039f60fe26b1248e6819f794e489234573e9c829b4dfa2827"}}',
           'GetCategoryById' : '{"persistedQuery":{"version":1,"sha256Hash":"e8f138451a02b5310cc46626961ed75441d50e875aa99eef74cd3ebd76fe1674"}}',
           'Show' : '{"persistedQuery":{"version":1,"sha256Hash":"a0b8c34187b57b539d3705347d53e1af91977eb70696781995bfd542022f0468"}}',
           'MediumMeta' : '{"persistedQuery":{"version":1,"sha256Hash":"b6ac484229e4ed1a3226eb2bc589c10d5ef2c90ca6bea29508725f59472ed8cb"}}',
           'SearchShows' : '{"persistedQuery":{"version":1,"sha256Hash":"0ed5566c9b2d37d6fc0b3f76a1b6f06e8633dae9de5d90a3dcdb10bbaf0388a9"}}',
           'GetEpisodes' : '{"persistedQuery":{"version":1,"sha256Hash":"163c22c6f604628f0cbfbfec54eb145a2e31388c2222093a283541a861b17181"}}',
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
    while ok == False and err < 4:
        data = call_api(url = url)
        if 'errors' in data and data['errors'] and 'message' in data['errors'][0] and data['errors'][0]['message'] == 'PersistedQueryNotFound':
            err = err + 1
            time.sleep(1)
        else:
            ok = True
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

