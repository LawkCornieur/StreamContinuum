import xbmc
import xbmcgui
import xbmcaddon
import requests
import time
import urllib.parse

try:
    import tmdb
except Exception as _tmdb_e:
    xbmc.log(f"StreamContinuum: Trakt.py: TMDb module import failed: {_tmdb_e}", xbmc.LOGWARNING)
    tmdb = None

ADDON = xbmcaddon.Addon()

def authenticate():
    client_id = ADDON.getSetting('trakt_client_id')
    client_secret = ADDON.getSetting('trakt_client_secret')
    
    if not client_id or not client_secret:
        xbmcgui.Dialog().ok("Trakt.tv Error", "Chybí Client ID nebo Client Secret v nastavení API.")
        return

    # 1. Generate Device Code
    url = "https://api.trakt.tv/oauth/device/code"
    payload = {"client_id": client_id}
    
    try:
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            xbmcgui.Dialog().ok("Trakt.tv Error", f"Chyba při komunikaci s Trakt.tv (Status: {res.status_code})\nZkontrolujte Client ID.")
            return
        response = res.json()
    except Exception as e:
        xbmcgui.Dialog().ok("Trakt.tv Error", f"Nepodařilo se připojit k Trakt.tv: {str(e)}")
        return
    
    user_code = response.get('user_code')
    device_code = response.get('device_code')
    interval = response.get('interval', 5)
    expires_in = response.get('expires_in', 600)
    
    if not user_code or not device_code:
        xbmcgui.Dialog().ok("Trakt.tv Error", "API nevrátilo aktivační kódy.")
        return
    
    # 2. Show Dialog to User
    progress = xbmcgui.DialogProgress()
    progress.create("Trakt.tv Activation", 
                    f"Go to: trakt.tv/activate\nEnter code: {user_code}")
    
    # 3. Poll for Token
    start_time = time.time()
    while time.time() - start_time < expires_in:
        if progress.iscanceled():
            break
            
        token_url = "https://api.trakt.tv/oauth/device/token"
        token_payload = {
            "code": device_code,
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        token_res = requests.post(token_url, json=token_payload)
        
        if token_res.status_code == 200:
            data = token_res.json()
            ADDON.setSetting('trakt_token', data['access_token'])
            
            # Fetch and save username
            user_info = get_user_info()
            if user_info:
                ADDON.setSetting('trakt_username', user_info.get('username', 'Připojeno'))
            
            xbmcgui.Dialog().notification("Trakt.tv", "Successfully connected!", xbmcgui.NOTIFICATION_INFO)
            break
        elif token_res.status_code == 400:
            time.sleep(interval)
        else:
            break
            
    progress.close()

def get_headers():
    client_id = ADDON.getSetting('trakt_client_id')
    token = ADDON.getSetting('trakt_token')
    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": client_id
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def get_user_info():
    url = "https://api.trakt.tv/users/me"
    headers = get_headers()
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error getting Trakt user info: {e}", xbmc.LOGERROR)
    return None

def get_trakt_id_from_tmdb_id(tmdb_id, media_type):
    if not tmdb_id or str(tmdb_id).strip().lower() in ('none', '', '0') or media_type not in ('movie', 'show'):
        return None

    trakt_search_type = 'movie' if media_type == 'movie' else 'show'
    url = f"https://api.trakt.tv/search/tmdb/{tmdb_id}?type={trakt_search_type}"
    headers = get_headers()

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            results = res.json()
            if results:
                first_result = results[0]
                found_media_type = first_result.get('type')
                found_item = first_result.get(found_media_type, {})
                trakt_id = found_item.get('ids', {}).get('trakt')
                if trakt_id:
                    return trakt_id
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error getting Trakt ID for TMDb ID {tmdb_id} ({media_type}): {e}", xbmc.LOGERROR)
    return None

def search_trakt(query):
    xbmc.log(f"StreamContinuum: Trakt.tv searching for '{query}'", xbmc.LOGINFO)
    safe_query = urllib.parse.quote(query)
    url = f"https://api.trakt.tv/search?query={safe_query}&type=movie,show"
    headers = get_headers()

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error searching Trakt.tv for '{query}': {e}", xbmc.LOGERROR)
    return []

def get_watchlist():
    url = "https://api.trakt.tv/sync/watchlist"
    headers = get_headers()
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error getting Trakt watchlist: {e}", xbmc.LOGERROR)
    return []

def add_to_watchlist(media_type, item_id, id_type='trakt'):
    url = "https://api.trakt.tv/sync/watchlist"
    headers = get_headers()
    item_key = 'movies' if media_type == 'movie' else ('episodes' if media_type == 'episode' else 'shows')
    id_field = 'tmdb' if id_type == 'tmdb' else 'trakt'
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        return False
    payload = {item_key: [{"ids": {id_field: item_id}}]}
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code in (200, 201):
            return True
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error adding to watchlist on Trakt: {e}", xbmc.LOGERROR)
    return False

def remove_from_watchlist(media_type, item_id, id_type='trakt'):
    url = "https://api.trakt.tv/sync/watchlist/remove"
    headers = get_headers()
    item_key = 'movies' if media_type == 'movie' else ('episodes' if media_type == 'episode' else 'shows')
    id_field = 'tmdb' if id_type == 'tmdb' else 'trakt'
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        return False
    payload = {item_key: [{"ids": {id_field: item_id}}]}
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code in (200, 201):
            return True
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error removing from watchlist on Trakt: {e}", xbmc.LOGERROR)
    return False

def get_playback():
    url = "https://api.trakt.tv/sync/playback"
    headers = get_headers()
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error getting Trakt playback: {e}", xbmc.LOGERROR)
    return []

def get_progress():
    url = "https://api.trakt.tv/sync/playback/episodes"
    headers = get_headers()
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error getting Trakt progress: {e}", xbmc.LOGERROR)
    return []

def get_trending(media_type):
    url = f"https://api.trakt.tv/{media_type}/trending"
    headers = get_headers()
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error getting Trakt trending {media_type}: {e}", xbmc.LOGERROR)
    return []

def get_popular(media_type):
    url = f"https://api.trakt.tv/{media_type}/popular"
    headers = get_headers()
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error getting Trakt popular {media_type}: {e}", xbmc.LOGERROR)
    return []

def get_recommended(media_type):
    url = f"https://api.trakt.tv/recommendations/{media_type}"
    headers = get_headers()
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error getting Trakt recommended {media_type}: {e}", xbmc.LOGERROR)
    return []

def get_seasons(trakt_id):
    url = f"https://api.trakt.tv/shows/{trakt_id}/seasons?extended=full"
    headers = get_headers()
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error getting Trakt seasons for {trakt_id}: {e}", xbmc.LOGERROR)
    return []

def get_episodes(trakt_id, season_num):
    url = f"https://api.trakt.tv/shows/{trakt_id}/seasons/{season_num}?extended=full"
    headers = get_headers()
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error getting Trakt episodes for {trakt_id} S{season_num}: {e}", xbmc.LOGERROR)
    return []

def mark_watched(media_type, item_id, id_type='trakt'):
    url = "https://api.trakt.tv/sync/history"
    headers = get_headers()
    item_key = 'movies' if media_type == 'movie' else ('episodes' if media_type == 'episode' else 'shows')
    id_field = 'tmdb' if id_type == 'tmdb' else 'trakt'
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        return False
    payload = {item_key: [{"ids": {id_field: item_id}}]}
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code in (200, 201):
            return True
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error marking watched on Trakt: {e}", xbmc.LOGERROR)
    return False

def mark_unwatched(media_type, item_id, id_type='trakt'):
    url = "https://api.trakt.tv/sync/history/remove"
    headers = get_headers()
    item_key = 'movies' if media_type == 'movie' else ('episodes' if media_type == 'episode' else 'shows')
    id_field = 'tmdb' if id_type == 'tmdb' else 'trakt'
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        return False
    payload = {item_key: [{"ids": {id_field: item_id}}]}
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code in (200, 201):
            return True
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error marking unwatched on Trakt: {e}", xbmc.LOGERROR)
    return False

def get_localized_metadata(item_id, media_type, season_num=None, episode_num=None, id_type='trakt'):
    if not item_id:
        return {}

    tmdb_id = None
    trakt_item_data = {}

    if id_type == 'trakt':
        trakt_endpoint_type = 'movies' if media_type == 'movie' else 'shows'
        url = f"https://api.trakt.tv/{trakt_endpoint_type}/{item_id}"
        try:
            res = requests.get(url, headers=get_headers(), timeout=10)
            if res.status_code == 200:
                trakt_item_data = res.json()
                tmdb_id = trakt_item_data.get('ids', {}).get('tmdb')
            else:
                return {}
        except Exception:
            return {}
    elif id_type == 'tmdb':
        tmdb_id = item_id
    else:
        return {}

    if not tmdb_id:
        return {}

    tmdb_url_template_cs = None
    if media_type == 'movie':
        tmdb_url_template_cs = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={{api_key}}&language=cs-CZ"
    elif media_type == 'show':
        tmdb_url_template_cs = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={{api_key}}&language=cs-CZ"
    elif media_type == 'season' and season_num is not None:
        tmdb_url_template_cs = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_num}?api_key={{api_key}}&language=cs-CZ"
    elif media_type == 'episode' and season_num is not None and episode_num is not None:
        tmdb_url_template_cs = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_num}/episode/{episode_num}?api_key={{api_key}}&language=cs-CZ"
    
    if not tmdb_url_template_cs:
        return {}

    if tmdb is None:
        return {
            'title': trakt_item_data.get('title'),
            'overview': trakt_item_data.get('overview'),
            'year': trakt_item_data.get('year'),
            'poster': '',
            'fanart': '',
            'genres': trakt_item_data.get('genres', []),
            'rating': trakt_item_data.get('rating', 0),
            'runtime': trakt_item_data.get('runtime', 0),
            'status': trakt_item_data.get('status', ''),
            'air_date': trakt_item_data.get('first_aired', '')
        }

    try:
        tmdb_data_cs = {}
        tmdb_res_cs = tmdb.make_tmdb_request(tmdb_url_template_cs)
        if tmdb_res_cs and tmdb_res_cs.status_code == 200:
            tmdb_data_cs = tmdb_res_cs.json()
            
        cs_title_or_name = tmdb_data_cs.get('title') if media_type == 'movie' else tmdb_data_cs.get('name')
        cs_overview = tmdb_data_cs.get('overview')
        
        tmdb_data_en = {}
        if (not cs_title_or_name or not cs_overview) and ('language=cs-CZ' in tmdb_url_template_cs):
            tmdb_url_template_en = tmdb_url_template_cs.replace('language=cs-CZ', 'language=en-US')
            try:
                tmdb_res_en = tmdb.make_tmdb_request(tmdb_url_template_en)
                if tmdb_res_en and tmdb_res_en.status_code == 200:
                    tmdb_data_en = tmdb_res_en.json()
            except Exception:
                pass

        def _get_best_string(cs_key_movie, cs_key_tv, en_key_movie, en_key_tv, trakt_key=None, log_context=""):
            cs_value = tmdb_data_cs.get(cs_key_movie if media_type == 'movie' else cs_key_tv)
            if cs_value:
                return cs_value
            en_value = tmdb_data_en.get(en_key_movie if media_type == 'movie' else en_key_tv)
            if en_value:
                if "Title" in log_context:
                    return f"[EN] {en_value}"
                return en_value
            if id_type == 'trakt' and trakt_key: 
                trakt_value = trakt_item_data.get(trakt_key, '')
                if trakt_value:
                    if "Title" in log_context and not tmdb_data_en.get(en_key_movie if media_type == 'movie' else en_key_tv):
                        return f"[TRAKT] {trakt_value}"
                    return trakt_value
            return ''

        def _get_best_year(cs_date_key, en_date_key, trakt_year_key=None, log_context=""):
            cs_year = tmdb_data_cs.get(cs_date_key, '')
            if cs_year:
                return str(cs_year)[:4]
            en_year = tmdb_data_en.get(en_date_key, '')
            if en_year:
                return str(en_year)[:4]
            if id_type == 'trakt' and trakt_year_key: 
                trakt_year = trakt_item_data.get(trakt_year_key, '')
                if trakt_year:
                    return str(trakt_year)[:4]
            return ''
            
        result = {}
        if media_type == 'movie':
            result['title'] = _get_best_string('title', '', 'title', '', 'title', log_context='Movie Title')
            result['overview'] = _get_best_string('overview', 'overview', 'overview', 'overview', 'overview', log_context='Movie Overview')
            result['year'] = _get_best_year('release_date', 'release_date', 'year', log_context='Movie Year')
            result['runtime'] = tmdb_data_cs.get('runtime', 0) or tmdb_data_en.get('runtime', 0) or trakt_item_data.get('runtime', 0)
            result['rating'] = tmdb_data_cs.get('vote_average', 0) or tmdb_data_en.get('vote_average', 0) or trakt_item_data.get('rating', 0)
        elif media_type == 'show':
            result['title'] = _get_best_string('', 'name', '', 'name', 'title', log_context='Show Title')
            result['overview'] = _get_best_string('overview', 'overview', 'overview', 'overview', 'overview', log_context='Show Overview')
            result['year'] = _get_best_year('first_air_date', 'first_air_date', 'year', log_context='Show Year')
            result['status'] = (tmdb_data_cs.get('status') or tmdb_data_en.get('status') or trakt_item_data.get('status', ''))
            result['runtime'] = (tmdb_data_cs.get('episode_run_time', [0])[0] if tmdb_data_cs.get('episode_run_time') else 0) or \
                                (tmdb_data_en.get('episode_run_time', [0])[0] if tmdb_data_en.get('episode_run_time') else 0) or \
                                trakt_item_data.get('runtime', 0)
            result['rating'] = tmdb_data_cs.get('vote_average', 0) or tmdb_data_en.get('vote_average', 0) or trakt_item_data.get('rating', 0)
        elif media_type == 'season':
            result['title'] = _get_best_string('', 'name', '', 'name', None, log_context=f'Season Title S{season_num}') or f"{ADDON.getLocalizedString(30105)} {season_num}"
            result['overview'] = _get_best_string('overview', 'overview', 'overview', 'overview', None, log_context=f'Season Overview S{season_num}')
            result['episode_count'] = tmdb_data_cs.get('episode_count', 0) or tmdb_data_en.get('episode_count', 0)
            result['year'] = _get_best_year('air_date', 'air_date', None, log_context=f'Season Year S{season_num}')
            result['rating'] = tmdb_data_cs.get('vote_average', 0) or tmdb_data_en.get('vote_average', 0)
        elif media_type == 'episode':
            result['title'] = _get_best_string('', 'name', '', 'name', None, log_context=f'Episode Title S{season_num}E{episode_num}')
            result['overview'] = _get_best_string('overview', 'overview', 'overview', 'overview', None, log_context=f'Episode Overview S{season_num}E{episode_num}')
            result['runtime'] = tmdb_data_cs.get('runtime', 0) or tmdb_data_en.get('runtime', 0)
            result['year'] = _get_best_year('air_date', 'air_date', None, log_context=f'Episode Year S{season_num}E{episode_num}')
            result['rating'] = tmdb_data_cs.get('vote_average', 0) or tmdb_data_en.get('vote_average', 0)
            result['air_date'] = tmdb_data_cs.get('air_date') or tmdb_data_en.get('air_date') or trakt_item_data.get('first_aired', '')

        poster_path_cs = tmdb_data_cs.get('poster_path')
        backdrop_path_cs = tmdb_data_cs.get('backdrop_path')
        poster_path_en = tmdb_data_en.get('poster_path')
        backdrop_path_en = tmdb_data_en.get('backdrop_path')
        
        final_poster_path = poster_path_cs or poster_path_en
        final_backdrop_path = backdrop_path_cs or backdrop_path_en

        result['poster'] = f"https://image.tmdb.org/t/p/w500{final_poster_path}" if final_poster_path else ''
        result['fanart'] = f"https://image.tmdb.org/t/p/original{final_backdrop_path}" if final_backdrop_path else ''
        
        if media_type in ('movie', 'show'):
            result['genres'] = [g.get('name') for g in tmdb_data_cs.get('genres', []) if g.get('name')] or \
                               [g.get('name') for g in tmdb_data_en.get('genres', []) if g.get('name')] or \
                               trakt_item_data.get('genres', [])
        else:
            result['genres'] = []
            
        return result
    except Exception as e:
        xbmc.log(f"StreamContinuum: TMDb API error getting localized data: {e}", xbmc.LOGERROR)
        return {}
