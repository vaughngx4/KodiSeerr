import sys
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import urllib.parse
import api_client
import json
from resources.lib.media_dialog import MediaDialog

addon = xbmcaddon.Addon()
addon_path = addon.getAddonInfo('path')
addon_handle = int(sys.argv[1])
base_url = sys.argv[0]
args = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))

preferred_movie_view = int(addon.getSetting("view_mode_movies") or 0)
preferred_tv_view = int(addon.getSetting("view_mode_tvshows") or 0)

max_search_history = 10
image_base_small = "https://image.tmdb.org/t/p/w500"
image_base_large = "https://image.tmdb.org/t/p/original"
enable_ask_4k = addon.getSettingBool('enable_ask_4k')

def build_url(query):
    return base_url + '?' + urllib.parse.urlencode(query)

def make_art(item):
    art = {}
    for k in ["posterPath", "backdropPath", "logoPath", "bannerPath", "landscapePath", "iconPath", "clearartPath"]:
        if item.get(k):
            if k == "posterPath":
                art["poster"] = image_base_small + item[k]
                art["thumb"] = image_base_small + item[k]
            elif k == "backdropPath":
                art["fanart"] = image_base_large + item[k]
            elif k == "logoPath":
                art["clearlogo"] = image_base_small + item[k]
            elif k == "bannerPath":
                art["banner"] = image_base_small + item[k]
            elif k == "landscapePath":
                art["landscape"] = image_base_small + item[k]
            elif k == "iconPath":
                art["icon"] = image_base_small + item[k]
            elif k == "clearartPath":
                art["clearart"] = image_base_small + item[k]
    return art

def make_info(item, media_type):
    release_date = item.get('releaseDate') or item.get('firstAirDate')
    year = int(release_date.split("-")[0]) if release_date and release_date.split("-")[0].isdigit() else 0
    def join_names(obj_list):
        return ', '.join(
            g['name'] if isinstance(g, dict) and 'name' in g else str(g)
            for g in obj_list
        )
    genres = join_names(item.get('genres', []))
    studio = join_names(item.get('studios', [])) if item.get('studios') else ''
    country = join_names(item.get('productionCountries', [])) if item.get('productionCountries') else ''
    mpaa = item.get('certification', '')
    runtime = item.get('runtime', 0)
    try:
        runtime = int(runtime)
    except Exception:
        runtime = 0
    try:
        rating = float(item.get('voteAverage', 0))
    except Exception:
        rating = 0.0
    votes = item.get('voteCount', 0)
    try:
        votes = int(votes)
    except Exception:
        votes = 0
    director = ', '.join([c['name'] for c in item.get('crew', []) if c.get('job') == 'Director']) if item.get('crew') else ''
    cast = [person['name'] for person in item.get('cast', []) if isinstance(person, dict) and 'name' in person]
    cast_str = ', '.join(cast[:5])
    plot = item.get('overview', '')
    title = item.get('title') or item.get('name')
    # Rich plot for display
    rich_plot = f"{title} ({year})"
    if genres: rich_plot += f"\nGenres: {genres}"
    if studio: rich_plot += f"\nStudio: {studio}"
    if country: rich_plot += f"\nCountry: {country}"
    if mpaa: rich_plot += f"\nCertification: {mpaa}"
    if runtime: rich_plot += f"\nRuntime: {runtime} min"
    if rating: rich_plot += f"\nRating: {rating} ({votes} votes)"
    if director: rich_plot += f"\nDirector: {director}"
    if cast_str: rich_plot += f"\nCast: {cast_str}"
    if plot: rich_plot += f"\n\n{plot}"

    info = {
        'title': title or "",
        'plot': rich_plot or "",
        'year': year,
        'genre': genres or "",
        'rating': rating,
        'votes': votes,
        'premiered': release_date or "",
        'duration': runtime,
        'mpaa': mpaa or "",
        'cast': cast,
        'director': director or "",
        'studio': studio or "",
        'country': country or "",
        'mediatype': media_type
    }
    return info

def set_info_tag(list_item, info):
    info_tag = list_item.getVideoInfoTag()

    # Safe InfoTagVideo setters
    if info.get('title'):
        info_tag.setTitle(info['title'])
    if info.get('plot'):
        info_tag.setPlot(info['plot'])
    if info.get('year'):
        try:
            info_tag.setYear(int(info['year']))
        except Exception:
            pass
    if info.get('rating'):
        try:
            info_tag.setRating(float(info['rating']))
        except Exception:
            pass
    if info.get('votes'):
        try:
            info_tag.setVotes(int(info['votes']))
        except Exception:
            pass
    if info.get('premiered'):
        info_tag.setPremiered(info['premiered'])
    if info.get('duration'):
        try:
            info_tag.setDuration(int(info['duration']))
        except Exception:
            pass
    if info.get('mpaa'):
        info_tag.setMpaa(info['mpaa'])
    if info.get('director'):
        info_tag.setDirector(info['director'])
    if info.get('studio'):
        info_tag.setStudio(info['studio'])

    # Fallback to setInfo for unsupported InfoTagVideo attributes
    fallback_info = {}
    if info.get('genre'):
        fallback_info['genre'] = info['genre']
    if info.get('cast'):
        fallback_info['cast'] = info['cast']
    if info.get('country'):
        fallback_info['country'] = info['country']
    if info.get('mediatype'):
        fallback_info['mediatype'] = info['mediatype']

    if fallback_info:
        list_item.setInfo('video', fallback_info)

def render_media_items(items, current_page=1, total_pages=1, mode=None, genre_id=None, display_type=None):
    # Determine Kodi content type based on mode or display_type
    if mode in ['popular_movies', 'upcoming_movies']:
        content_type = 'movies'
    elif mode in ['popular_tv', 'upcoming_tv']:
        content_type = 'tvshows'
    elif mode == 'genre':
        content_type = 'movies' if display_type == 'movies' else 'tvshows'
    else:
        content_type = 'movies'

    if content_type == 'movies' and preferred_movie_view:
        xbmc.executebuiltin(f'Container.SetViewMode({preferred_movie_view})')
    elif content_type == 'tvshows' and preferred_tv_view:
        xbmc.executebuiltin(f'Container.SetViewMode({preferred_tv_view})')

    xbmcplugin.setContent(addon_handle, content_type)

    # Show page info if pagination exists
    if total_pages > 1:
        page_info = xbmcgui.ListItem(label=f'[I]Page {current_page} of {total_pages}[/I]')
        xbmcplugin.addDirectoryItem(addon_handle, '', page_info, False)

        # Previous Page
        if current_page > 1:
            params = {'mode': mode, 'page': current_page - 1}
            if mode == "genre":
                params['genre_id'] = genre_id
                params['display_type'] = display_type
            prev_page_url = build_url(params)
            prev_item = xbmcgui.ListItem(label=f'[B]<< Previous Page ({current_page - 1})[/B]')
            xbmcplugin.addDirectoryItem(addon_handle, prev_page_url, prev_item, True)

    # Media Items
    for item in items:
        id = item.get('id')
        media_type = item.get('mediaType', 'movie')
        title = item.get('title') or item.get('name') or "Untitled"
        release_date = item.get('releaseDate') or item.get('firstAirDate')
        year = int(release_date.split("-")[0]) if release_date and release_date.split("-")[0].isdigit() else None
        label = f"{title} ({year})" if year else title

        url = build_url({
            'mode': 'media',
            'media_type': media_type,
            'media_id': str(id),
        })

        # url = build_url({'mode': 'list_seasons', 'id': item['id']}) if media_type == 'tv' else \
        #     build_url({'mode': 'request', 'type': 'movie', 'id': item['id']})

        list_item = xbmcgui.ListItem(label=label)
        info = make_info(item, media_type)
        art = make_art(item)
        set_info_tag(list_item, info)
        list_item.setArt(art)
        xbmcplugin.addDirectoryItem(addon_handle, url, list_item, True)

    # Next Page
    if total_pages > 1 and current_page < total_pages:
        params = {'mode': mode, 'page': current_page + 1}
        if mode == "genre":
            params['genre_id'] = genre_id
            params['display_type'] = display_type
        next_page_url = build_url(params)
        next_item = xbmcgui.ListItem(label=f'[B]Next Page ({current_page + 1}) >>[/B]')
        xbmcplugin.addDirectoryItem(addon_handle, next_page_url, next_item, True)

    xbmcplugin.endOfDirectory(addon_handle)

def list_main_menu():
    xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode': 'trending'}), xbmcgui.ListItem('Trending'), True)
    xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode': 'popular_movies'}), xbmcgui.ListItem('Popular Movies'), True)
    xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode': 'popular_tv'}), xbmcgui.ListItem('Popular TV Shows'), True)
    xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode': 'upcoming_movies'}), xbmcgui.ListItem('Upcoming Movies'), True)
    xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode': 'upcoming_tv'}), xbmcgui.ListItem('Upcoming TV Shows'), True)
    xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode': 'genres', 'media_type': 'movie'}), xbmcgui.ListItem('Movies by Genre'), True)
    xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode': 'genres', 'media_type': 'tv'}), xbmcgui.ListItem('TV Shows by Genre'), True)
    xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode': 'requests'}), xbmcgui.ListItem('Request Progress'), True)
    xbmcplugin.addDirectoryItem(addon_handle, build_url({'mode': 'search'}), xbmcgui.ListItem('Search'), True)
    xbmcplugin.endOfDirectory(addon_handle)

def list_genres(media_type):
    data = api_client.client.api_request(f"/genres/{media_type}", params={})
    for item in data:
        name = item.get('name')
        id = item.get('id')
        display_type = "movies" if media_type == "movie" else media_type
        url = build_url({'mode': 'genre', 'display_type': display_type, 'genre_id': id})
        list_item = xbmcgui.ListItem(label=name)
        xbmcplugin.addDirectoryItem(addon_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(addon_handle)

def list_items(data, mode, display_type=None, genre_id=None):
    items = data.get('results', [])
    current_page = data.get('page', 1)
    total_pages = data.get('totalPages', 1)

    render_media_items(
        items=items,
        current_page=current_page,
        total_pages=total_pages,
        mode=mode,
        genre_id=genre_id,
        display_type=display_type
    )

def do_request(media_type, id):
    is4k = False
    if enable_ask_4k:
        if xbmcgui.Dialog().yesno('KodiSeerr', 'Request in 4K quality?'):
            is4k = True
    payload = {
        "mediaType": media_type,
        "mediaId": int(id),
        "is4k": is4k
    }
    if media_type == "tv":
        payload["seasons"] = "all"
    try:
        xbmcgui.Dialog().notification('KodiSeerr', 'Processing Request...', xbmcgui.NOTIFICATION_INFO, 3000)
        api_client.client.api_request("/request", method="POST", data=payload)
        xbmcgui.Dialog().notification('KodiSeerr', 'Request Sent!', xbmcgui.NOTIFICATION_INFO, 3000)
    except Exception as e:
        xbmcgui.Dialog().notification('KodiSeerr', f'Request Failed: {str(e)}', xbmcgui.NOTIFICATION_ERROR, 4000)

def do_request_seasons(tv_id, selected_seasons):
    is4k = False
    if enable_ask_4k:
        if xbmcgui.Dialog().yesno('KodiSeerr', 'Request in 4K quality?'):
            is4k = True

    # Build the payload with all selected seasons
    payload = {
        "mediaType": "tv",
        "mediaId": int(tv_id),
        "seasons": [int(s) for s in selected_seasons],
        "is4k": is4k
    }

    try:
        xbmcgui.Dialog().notification('KodiSeerr', 'Processing Request...', xbmcgui.NOTIFICATION_INFO, 3000)
        api_client.client.api_request("/request", method="POST", data=payload)
        xbmcgui.Dialog().notification(
            'KodiSeerr',
            f'Request sent for seasons: {", ".join(map(str, selected_seasons))}',
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
    except Exception as e:
        xbmcgui.Dialog().notification(
            'KodiSeerr',
            f'Request Failed: {str(e)}',
            xbmcgui.NOTIFICATION_ERROR,
            4000
        )

def show_requests(data, mode):
    items = data.get('results', [])

    status_map = {
        3: "[COLOR blue](Requested)[/COLOR]",
        4: "[COLOR lime](Partially Available)[/COLOR]",
        5: "[COLOR lime](Available)[/COLOR]"
    }

    for item in items:
        media = item.get('media', {})
        if not media or not media.get('tmdbId') or not media.get('mediaType'):
            continue

        id = media.get('tmdbId')
        media_type = media.get('mediaType')

        mediaData = api_client.client.api_request(f"/{media_type}/{id}", params={})

        title = mediaData.get('title') or mediaData.get('name') or f"ID {id}"
        overview = mediaData.get('overview', '')
        release_date = mediaData.get('releaseDate', '')
        vote = mediaData.get('voteAverage')
        runtime = mediaData.get('runtime')
        tagline = mediaData.get('tagline')
        genres = ", ".join(g['name'] for g in mediaData.get('genres', []))

        status = media.get('status')
        label_text = f"{title} {status_map.get(status, '')}"

        url = build_url({
            'mode': 'media',
            'media_type': media_type,
            'media_id': str(id),
        })

        list_item = xbmcgui.ListItem(label=label_text)

        info = {
            'title': title,
            'plot': f"{overview}\n\nGenres: {genres}\nRuntime: {runtime} min\nRating: {vote}\nRelease: {release_date}",
            'tagline': tagline,
            'genre': genres,
            'duration': runtime,
            'rating': vote,
            'year': int(release_date.split('-')[0]) if release_date else None
        }
        set_info_tag(list_item, info)

        art = make_art(mediaData)
        list_item.setArt(art)

        xbmcplugin.addDirectoryItem(addon_handle, url, list_item, isFolder=True)
    xbmcplugin.endOfDirectory(addon_handle)

def launch_media_dialog(mediaData):
    media = mediaData.copy()
    media.update({
        'title': mediaData.get('title') or mediaData.get('name', 'Unknown Title'),
        'poster': image_base_small + mediaData.get('posterPath', ''),
        'fanart': image_base_large + mediaData.get('backdropPath', '')
    })
    dialog = MediaDialog(
        'MediaDetailDialog.xml',
        addon_path,
        'Default',
        '720p',
        media=media,
    )
    dialog.doModal()
    del dialog

def add_request_button(media_type, media_id):
    if media_type == "movie":
        request_url = build_url({'mode': 'request', 'type': media_type, 'id': media_id})
        item = xbmcgui.ListItem(label='[B][COLOR yellow]Request Movie[/COLOR][/B]')
        xbmcplugin.addDirectoryItem(addon_handle, request_url, item, isFolder=False)

    elif media_type == "tv":
        seasons_url = build_url({'mode': 'list_seasons', 'id': media_id})
        item = xbmcgui.ListItem(label='[B][COLOR yellow]Request More Seasons[/COLOR][/B]')
        xbmcplugin.addDirectoryItem(addon_handle, seasons_url, item, isFolder=True)

def add_watch_button(mediaData):
    media_url = mediaData.get('mediaInfo', {}).get('mediaUrl') or mediaData.get('mediaUrl')
    if media_url:
        item = xbmcgui.ListItem(label='[B][COLOR lime]▶ Watch Now[/COLOR][/B]')
        item.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem(addon_handle, media_url, item, isFolder=False)

def list_seasons(tv_id):
    data = api_client.client.api_request(f"/tv/{tv_id}")
    seasons = data.get('seasons', [])
    show_title = data.get('title') or data.get('name')

    if not seasons:
        xbmcgui.Dialog().notification("KodiSeerr", "No seasons found", xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(addon_handle)
        return

    # Build season display names
    season_choices = []
    season_numbers = []

    for season in seasons:
        season_number = season.get('seasonNumber', 0)
        season_name = season.get('name', f"Season {season_number}")
        label = f"{show_title} - {season_name}"
        season_choices.append(label)
        season_numbers.append(season_number)

    # Show multiselect dialog
    selected = xbmcgui.Dialog().multiselect("Select Seasons to Request", season_choices)
    if selected is None:
        xbmcplugin.endOfDirectory(addon_handle)
        return

    season_numbers = [
    seasons[i].get('seasonNumber', 0)
    for i in selected if 0 <= i < len(seasons)
    ]

    url = build_url({'mode': 'request_seasons', 'tv_id': tv_id, 'seasons': json.dumps(season_numbers)})
    xbmc.executebuiltin(f'RunPlugin({url})')

    xbmcplugin.endOfDirectory(addon_handle)

def get_search_history():
    raw = xbmcaddon.Addon().getSetting("search_history") or ""
    try:
        return json.loads(raw) if raw else []
    except Exception:
        return []

def save_search_history(history):
    xbmcaddon.Addon().setSetting("search_history", json.dumps(history))

def add_to_search_history(query):
    history = get_search_history()
    history = [item for item in history if item["query"] != query]
    history.insert(0, {"query": query})
    save_search_history(history[:max_search_history])

def clear_search_history():
    xbmcaddon.Addon().setSetting("search_history", "")

def search(query=None):
    params = args
    query = params.get('query', None)
    filter_media_type = params.get('media_type')
    if query:
        search_query = query
    else:
        history = get_search_history()
        options = ["New Search"] + [item["query"] for item in history]
        if history:
            options.append("Clear Search History")
        choice = xbmcgui.Dialog().select("KodiSeerr Search", options)
        if choice == -1:
            return
        elif choice == 0:
            query = xbmcgui.Dialog().input('Search for Movies or TV Shows')
            if not query:
                return
        elif history and choice == len(options) - 1:
            if xbmcgui.Dialog().yesno("Clear History", "Are you sure you want to clear your search history?"):
                clear_search_history()
            return
        else:
            query = history[choice - 1]["query"]
    add_to_search_history(query)
    data = api_client.client.api_request('/search', params={'query': query})
    if not data or not data.get('results'):
        xbmcgui.Dialog().notification("KodiSeerr", "No results found", xbmcgui.NOTIFICATION_INFO, 3000)
        return
    results = data.get('results', [])
    if filter_media_type in ['movie', 'tv']:
        results = [item for item in results if item.get('mediaType') == filter_media_type]
    if not results:
        xbmcgui.Dialog().notification("KodiSeerr", "No results match your filter", xbmcgui.NOTIFICATION_INFO, 3000)
        return
    render_media_items(results)

mode = args.get('mode')
page = args.get('page')
if not page:
    page = 1
if not mode:
    list_main_menu()
elif mode == "trending":
    data = api_client.client.api_request("/discover/trending", params={"page": page})
    if data:
        list_items(data, mode)
    else:
        xbmcgui.Dialog().notification("Kodiseerr", "API Error", xbmcgui.NOTIFICATION_ERROR)
elif mode == "popular_movies":
    data = api_client.client.api_request("/discover/movies", params={"sortBy": "popularity.desc", "page": page})
    if data:
        list_items(data, mode)
    else:
        xbmcgui.Dialog().notification("Kodiseerr", "API Error", xbmcgui.NOTIFICATION_ERROR)
elif mode == "popular_tv":
    data = api_client.client.api_request("/discover/tv", params={"sortBy": "popularity.desc", "page": page})
    if data:
        list_items(data, mode)
    else:
        xbmcgui.Dialog().notification("Kodiseerr", "API Error", xbmcgui.NOTIFICATION_ERROR)
elif mode == "upcoming_movies":
    data = api_client.client.api_request("/discover/movies/upcoming", params={"page": page})
    if data:
        list_items(data, mode)
    else:
        xbmcgui.Dialog().notification("Kodiseerr", "API Error", xbmcgui.NOTIFICATION_ERROR)
elif mode == "upcoming_tv":
    data = api_client.client.api_request("/discover/tv/upcoming", params={"page": page})
    if data:
        list_items(data, mode)
    else:
        xbmcgui.Dialog().notification("Kodiseerr", "API Error", xbmcgui.NOTIFICATION_ERROR)
elif mode == "search":
    search()
elif mode == "request":
    do_request(args.get('type'), args.get('id'))
elif mode == "requests":
    data = api_client.client.api_request('/request', params={'sort': 'added', 'filter': 'all', 'sortDirection': 'desc', 'take': 25})
    if data:
        show_requests(data, mode)
    else:
        xbmcgui.Dialog().notification("Kodiseerr", "API Error", xbmcgui.NOTIFICATION_ERROR)
elif mode == "list_seasons" and args.get("id"):
    list_seasons(args.get("id"))
elif mode == 'request_seasons' and args.get("tv_id") and args.get("seasons"):
    tv_id = int(args.get("tv_id"))
    selected = json.loads(args.get("seasons"))
    do_request_seasons(tv_id, selected)
elif mode == "genres" and args.get("media_type"):
    list_genres(args.get("media_type"))
elif mode == "genre" and args.get("display_type") and args.get("genre_id"):
    display_type = args.get("display_type")
    genre_id = args.get("genre_id")
    data = api_client.client.api_request(f"/discover/{display_type}/genre/{genre_id}", params={"page": page})
    list_items(data, mode, display_type, genre_id)
elif mode == "media" and args.get("media_type") and args.get("media_id"):
    media_type = args.get("media_type")
    media_id = args.get("media_id")
    mediaData = api_client.client.api_request(f"/{media_type}/{media_id}", params={})
    launch_media_dialog(mediaData)
    sys.exit()
