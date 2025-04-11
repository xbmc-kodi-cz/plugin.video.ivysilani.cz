# -*- coding: utf-8 -*-
import xbmcaddon
import xbmc

try:
    from urllib.error import HTTPError # type: ignore
except ImportError:
    from urllib2 import HTTPError # type: ignore

import json
from resources.lib.utils import ua, graphql_url, params

GRAPHQL = { 
            'TVProgramChannelsList' : "query TVProgramChannelsList($date: Date) {\n  TVProgramChannelsList(date: $date) {\n    __typename\n    channelAsString\n    encoder\n    channelSettings {\n      __typename\n      channelColor\n      channelLogo\n      channelName\n    }\n  }\n}",
            'CurrentBroadcast' : "query CurrentBroadcast($channels: [String!]!, $date: Date!) {\n  TVProgramDailyChannelsPlanV2(channels: $channels, date: $date) {\n    __typename\n    channel\n    currentBroadcast {\n      __typename\n      item {\n        __typename\n        ...CommonTvProgramFragment\n      }\n    }\n  }\n}\nfragment CommonTvProgramFragment on DailyChannelPlan {\n  __typename\n  idec\n  sidp\n  startTime\n  title\n  show\n  episodeTitle\n  part\n  description\n  imageUrl\n  length\n  ivysilani\n  programSource\n  isPlayableNow\n  playableFrom\n  liveOnly\n  start\n  end\n}",
            'SearchShows' : "query SearchShows($keyword: String!, $limit: PaginationAmount!, $offset: Int!, $onlyPlayable: Boolean!) {\n  searchShowsAsYouType(keyword: $keyword, limit: $limit, offset: $offset, onlyPlayable: $onlyPlayable) {\n    __typename\n    items {\n      __typename\n      id\n      sidp\n      genres {\n        __typename\n        ...GenreFragment\n      }\n      title\n      previewImage\n      playable\n      cardLabels {\n        __typename\n        ...CardLabelFragment\n      }\n    }\n    totalCount\n  }\n}\nfragment GenreFragment on CardGenre {\n  __typename\n  id\n  title\n}\nfragment CardLabelFragment on CardLabels {\n  __typename\n  topLeft\n  topRight\n  center\n  bottomLeft\n  bottomRight\n}",
            'Show' : "query Show($id: String!, $shortText: Boolean) {\n  show(id: $id) {\n    __typename\n    id\n    idec\n    actionButton {\n      __typename\n      action\n      icon\n      idec\n      text(short: $shortText)\n      type\n    }\n    isPlayable\n    playableIdec\n    seasons {\n      __typename\n      id\n      title\n    }\n    title\n    showType\n    shortDescription\n    creators\n    images {\n      __typename\n      ...HeroShowImagesFragment\n    }\n    colorConfig {\n      __typename\n      theme\n    }\n    year\n    countriesOfOrigin {\n      __typename\n      title\n    }\n    labeling\n    genres {\n      __typename\n      title\n      children {\n        __typename\n        title\n      }\n    }\n    flatGenres {\n      __typename\n      title\n    }\n    defaultSort\n    supportsOrdering\n    playabilityError\n    slug\n  }\n}\nfragment HeroShowImagesFragment on ShowImages {\n  __typename\n  logo\n  logoInverted\n  card\n  hero {\n    __typename\n    desktop\n    mobile\n    tablet\n  }\n  placeholder\n}",
            'Categories' : "query Categories($deviceType: String!) {\n  menuOnlyCategories(deviceType: $deviceType) {\n    __typename\n    categoryId\n    title\n    children {\n      __typename\n      categoryId\n      title\n    }\n  }\n}",
            'TvProgramDailyTablet' : "query TvProgramDailyTablet($channels: [String!]!, $date: Date!) {\n  TVProgramDailyChannelsPlanV2(channels: $channels, date: $date) {\n    __typename\n    channel\n    currentBroadcast {\n      __typename\n      item {\n        __typename\n        ...CommonTvProgramFragment\n      }\n    }\n    encoder\n    program {\n      __typename\n      ...CommonTvProgramFragment\n    }\n  }\n  liveBroadcastFind(type: all) {\n    __typename\n    current {\n      __typename\n      channelAsString\n      cardLabels {\n        __typename\n        ...CardLabelFragment\n      }\n      encoder\n      previewImage\n    }\n  }\n}\nfragment CommonTvProgramFragment on DailyChannelPlan {\n  __typename\n  idec\n  sidp\n  startTime\n  title\n  show\n  episodeTitle\n  part\n  description\n  imageUrl\n  length\n  ivysilani\n  programSource\n  isPlayableNow\n  playableFrom\n  liveOnly\n  start\n  end\n}\nfragment CardLabelFragment on CardLabels {\n  __typename\n  topLeft\n  topRight\n  center\n  bottomLeft\n  bottomRight\n}",
            'GetEpisodes' : "query GetEpisodes($idec: String!, $seasonId: String, $limit: PaginationAmount!, $offset: Int!, $orderBy: EpisodeOrderByType!, $keyword: String, $onlyPlayable: Boolean)		{\n			episodesPreviewFind(idec: $idec, seasonId: $seasonId, limit: $limit, offset: $offset, orderBy: $orderBy, keyword: $keyword, onlyPlayable: $onlyPlayable)\n			{\n				totalCount\n				items\n				{\n					id\n					title\n					description\n					duration\n					playable\n					season\n					{\n						id\n						title\n					}\n					images\n					{\n						card\n					}\n					showId\n					showTitle\n					lastBroadcast\n					{\n						datetime\n						channel\n					}\n				}\n			}\n		}",
            'GetCategoryById' : "query GetCategoryById($limit: PaginationAmount!, $offset: Int!, $categoryId: String!, $order: OrderByDirection, $orderBy: CategoryOrderByType)\n		{\n			category(categoryId: $categoryId)\n			{\n				programmeFind(limit: $limit, offset:$offset, order:$order, orderBy:$orderBy)\n				{\n					totalCount\n					items\n					{\n						id\n						idec\n						flatGenres(exceptCategoryId: $categoryId)\n						{\n							id\n							title\n						}\n						title\n						showType\n						description\n						duration\n						shortDescription\n						year\n						images\n						{\n							card\n							hero\n							{\n								mobile\n							}\n						}\n						isPlayable\n					}\n				}\n			}\n		}",
            'HomepageRows' : "query HomepageRows($deviceType: String!, $limit: PaginationAmount!, $offset: Int!) {\n  homepageConfig(deviceType: $deviceType) {\n    __typename\n    rows(limit: $limit, offset: $offset) {\n      __typename\n      id\n      title\n      subtitle\n      type\n      cardFormat\n      disabled\n      hidden\n      assets {\n        __typename\n        ...AssetsFragment\n      }\n    }\n  }\n}\nfragment AssetsFragment on HomepageBlockAssets {\n  __typename\n  totalCount\n  items {\n    __typename\n    ... on ShowCard {\n      id\n      sidp\n      genres {\n        __typename\n        ...GenreFragment\n      }\n      title\n      previewImage\n      playable\n      cardLabels {\n        __typename\n        ...CardLabelFragment\n      }\n    }\n    ... on EpisodeCard {\n      id\n      sidp\n      idec\n      genres {\n        __typename\n        ...GenreFragment\n      }\n      programmeType\n      title\n      showTitle\n      previewImage\n      playable\n      cardLabels {\n        __typename\n        ...CardLabelFragment\n      }\n    }\n  }\n}\nfragment GenreFragment on CardGenre {\n  __typename\n  id\n  title\n}\nfragment CardLabelFragment on CardLabels {\n  __typename\n  topLeft\n  topRight\n  center\n  bottomLeft\n  bottomRight\n}",
            'HomepageBlock' : "query HomepageBlock($id: String!, $limit: Int!, $offset: Int!, $deviceType: String!) {\n  homepageBlock(id: $id, deviceType: $deviceType) {\n    __typename\n    assets(limit: $limit, offset: $offset) {\n      __typename\n      ...AssetsFragment\n    }\n  }\n}\nfragment AssetsFragment on HomepageBlockAssets {\n  __typename\n  totalCount\n  items {\n    __typename\n    ... on ShowCard {\n      id\n      sidp\n      genres {\n        __typename\n        ...GenreFragment\n      }\n      title\n      previewImage\n      playable\n      cardLabels {\n        __typename\n        ...CardLabelFragment\n      }\n    }\n    ... on EpisodeCard {\n      id\n      sidp\n      idec\n      genres {\n        __typename\n        ...GenreFragment\n      }\n      programmeType\n      title\n      showTitle\n      previewImage\n      playable\n      cardLabels {\n        __typename\n        ...CardLabelFragment\n      }\n    }\n  }\n}\nfragment GenreFragment on CardGenre {\n  __typename\n  id\n  title\n}\nfragment CardLabelFragment on CardLabels {\n  __typename\n  topLeft\n  topRight\n  center\n  bottomLeft\n  bottomRight\n}"
          }

def call_graphql(operationName, variables):
    post = {'operationName' : operationName, 'variables' : variables, 'query': GRAPHQL[operationName].replace('\t', '').replace('\n', ' ')}
    data = call_api(url = graphql_url, data = post, method = 'POST')
    if 'data' not in data or data['data'] is None:
        return None
    for result in data['data']:
        return data['data'][result]
    return None

def call_api(url, data = None, method = None):
    import requests
    addon = xbmcaddon.Addon()
    headers = {'User-Agent': ua, 'Accept-language' : 'cs', 'Accept-Encoding' : 'gzip', 'Accept': 'application/json; charset=utf-8', 'Content-type' : 'application/json;charset=UTF-8'}
    if addon.getSetting('log_requests') == 'true':
        xbmc.log(url)
    if method == 'POST':
        request = requests.post(url = url, params = params, json = data, headers = headers )
    else:
        request = requests.get(url = url, params = params, headers = headers )
    try:
        response = request.content
        if addon.getSetting('log_requests') == 'true':
            xbmc.log(str(response))
        if response and len(response) > 0:
            data = json.loads(response)
            return data
        else:
            return []
    except HTTPError as e:
        return { 'err' : e.reason }      

