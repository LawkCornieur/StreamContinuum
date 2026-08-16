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
    tmdb = None # Set tmdb to None if import fails in trakt.py

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
        elif token_res.status_code == 400: # Pending
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

def get_trakt_id_from_tmdb_id(tmdb_id, media_type):
    """
    Přeloží TMDb ID na Trakt ID pomocí Trakt API.
    media_type: 'movie' nebo 'show'
    Vrací Trakt ID (int) nebo None.
    """
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
                # Trakt search by TMDB ID returns a list of results.
                # We expect only one relevant result for an exact TMDB ID.
                first_result = results[0]
                found_media_type = first_result.get('type')
                found_item = first_result.get(found_media_type, {})
                trakt_id = found_item.get('ids', {}).get('trakt')
                if trakt_id:
                    xbmc.log(f"StreamContinuum: Trakt ID {trakt_id} found for TMDb ID {tmdb_id} ({media_type})", xbmc.LOGDEBUG)
                    return trakt_id
            xbmc.log(f"StreamContinuum: No Trakt ID found for TMDb ID {tmdb_id} ({media_type}) via search endpoint.", xbmc.LOGDEBUG)
        else:
            xbmc.log(f"StreamContinuum: Trakt API search by TMDb ID {tmdb_id} failed with status {res.status_code}", xbmc.LOGWARNING)
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error getting Trakt ID for TMDb ID {tmdb_id} ({media_type}): {e}", xbmc.LOGERROR)

    return None

def search_trakt(query):
    """
    Vyhledá filmy a seriály na Trakt.tv pomocí multi-search endpointu.
    Vrací list of dicts, kde každý dict obsahuje 'type' (movie/show) a data položky.
    """
    xbmc.log(f"StreamContinuum: Trakt.tv searching for '{query}'", xbmc.LOGINFO)
    safe_query = urllib.parse.quote(query)
    url = f"https://api.trakt.tv/search?query={safe_query}&type=movie,show"
    headers = get_headers()

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            results = res.json()
            xbmc.log(f"StreamContinuum: Trakt.tv search for '{query}' returned {len(results)} items.", xbmc.LOGDEBUG)
            return results
        else:
            xbmc.log(f"StreamContinuum: Trakt.tv search for '{query}' failed with status {res.status_code}. Response: {res.text[:200]}", xbmc.LOGERROR)
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error searching Trakt.tv for '{query}': {e}", xbmc.LOGERROR)
    return []

def get_localized_metadata(item_id, media_type, season_num=None, episode_num=None, id_type='trakt'):
    """Načte lokalizovaná (česká) metadata a obrázky z TMDb pro daný ID, včetně sezón a epizod.
       item_id: ID of the item (Trakt ID or TMDb ID)
       id_type: 'trakt' or 'tmdb' to specify the type of item_id
    """
    if not item_id:
        return {}

    tmdb_id = None
    trakt_item_data = {} # To store original Trakt data for fallback if TMDb fails

    if id_type == 'trakt':
        # Initial Trakt API call to get TMDb ID for the show/movie.
        trakt_endpoint_type = 'movies' if media_type == 'movie' else 'shows'
        url = f"https://api.trakt.tv/{trakt_endpoint_type}/{item_id}"
        try:
            res = requests.get(url, headers=get_headers(), timeout=10)
            if res.status_code == 200:
                trakt_item_data = res.json()
                tmdb_id = trakt_item_data.get('ids', {}).get('tmdb')
            else:
                xbmc.log(f"StreamContinuum: Trakt API failed to get TMDb ID for {media_type} id={item_id} (S{season_num}E{episode_num}), status={res.status_code}", xbmc.LOGWARNING)
                return {}
        except Exception as e:
            xbmc.log(f"StreamContinuum: Trakt API error getting TMDb ID for {media_type} id={item_id} (S{season_num}E{episode_num}): {e}", xbmc.LOGWARNING)
            return {}
    elif id_type == 'tmdb':
        tmdb_id = item_id # item_id is already tmdb_id
        # If we have tmdb_id, we can attempt to fetch basic Trakt data for fallback if needed.
        # This requires another Trakt API call, but let's keep it simple for now and rely solely on TMDb.
    else:
        xbmc.log(f"StreamContinuum: Invalid id_type '{id_type}' for get_localized_metadata.", xbmc.LOGERROR)
        return {}

    if not tmdb_id:
        xbmc.log(f"StreamContinuum: No TMDb ID found for {media_type} original_id={item_id} id_type={id_type}. Skipping TMDb lookup.", xbmc.LOGWARNING)
        return {} # Return empty to signal no TMDb data

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
        xbmc.log(f"StreamContinuum: Invalid media_type '{media_type}' or missing season/episode numbers for TMDb lookup URL.", xbmc.LOGWARNING)
        return {}

    # Check if tmdb module is actually available *here*
    if tmdb is None:
        xbmc.log(f"StreamContinuum: TMDb module not available in trakt.py for localized data lookup of {media_type} id={tmdb_id}. Falling back to Trakt data (if available).", xbmc.LOGWARNING)
        # Fallback to just Trakt data if tmdb module is missing
        return {
            'title': trakt_item_data.get('title'),
            'overview': trakt_item_data.get('overview'),
            'year': trakt_item_data.get('year'),
            'poster': '', # No TMDb, so no artwork from here
            'fanart': '', # No TMDb, so no artwork from here
            'genres': trakt_item_data.get('genres', []),
            'rating': trakt_item_data.get('rating', 0),
            'runtime': trakt_item_data.get('runtime', 0),
            'status': trakt_item_data.get('status', ''),
            'air_date': trakt_item_data.get('first_aired', '')
        }

    try:
        
        # 1. Fetch data in CS-CZ
        tmdb_data_cs = {}
        tmdb_res_cs = tmdb.make_tmdb_request(tmdb_url_template_cs)
        if tmdb_res_cs and tmdb_res_cs.status_code == 200:
            tmdb_data_cs = tmdb_res_cs.json()
            
        # Determine if CS-CZ data is sufficient. We consider title/name and overview crucial.
        cs_title_or_name = tmdb_data_cs.get('title') if media_type == 'movie' else tmdb_data_cs.get('name')
        cs_overview = tmdb_data_cs.get('overview')
        
        tmdb_data_en = {} # Will hold EN-US data if fetched
        # 2. If CS-CZ title/name OR overview is missing, fetch data in EN-US as fallback
        if (not cs_title_or_name or not cs_overview) and ('language=cs-CZ' in tmdb_url_template_cs):
            xbmc.log(f"StreamContinuum: CS-CZ data insufficient for {media_type} {tmdb_id} (S{season_num}E{episode_num}), fetching EN-US fallback", xbmc.LOGDEBUG)
            tmdb_url_template_en = tmdb_url_template_cs.replace('language=cs-CZ', 'language=en-US')
            try:
                tmdb_res_en = tmdb.make_tmdb_request(tmdb_url_template_en)
                if tmdb_res_en and tmdb_res_en.status_code == 200:
                    tmdb_data_en = tmdb_res_en.json()
            except Exception as e:
                xbmc.log(f"StreamContinuum: Error fetching EN-US fallback for {media_type} {tmdb_id} (S{season_num}E{episode_num}): {e}", xbmc.LOGDEBUG)

        # Helper function to get the best available string, prioritizing CS, then EN, then Trakt (if trakt_key specified and id_type was 'trakt')
        def _get_best_string(cs_key_movie, cs_key_tv, en_key_movie, en_key_tv, trakt_key=None, log_context=""):
            is_title_or_overview = "Title" in log_context or "Overview" in log_context # Check if this is a title or overview field

            cs_value = tmdb_data_cs.get(cs_key_movie if media_type == 'movie' else cs_key_tv)
            if cs_value:
                return cs_value
            
            en_value = tmdb_data_en.get(en_key_movie if media_type == 'movie' else en_key_tv)
            if en_value:
                xbmc.log(f"StreamContinuum: {log_context}: Fallback to EN-US for {media_type} id={item_id} (S{season_num}E{episode_num}) key='{cs_key_movie if media_type=='movie' else cs_key_tv}'", xbmc.LOGDEBUG)
                if is_title_or_overview:
                    return f"[EN] {en_value}" # Prepend [EN] tag for titles/overviews
                return en_value
            
            if id_type == 'trakt' and trakt_key: 
                trakt_value = trakt_item_data.get(trakt_key, '')
                if trakt_value:
                    xbmc.log(f"StreamContinuum: {log_context}: Fallback to Trakt for {media_type} id={item_id} (S{season_num}E{episode_num}) key='{trakt_key}'", xbmc.LOGDEBUG)
                    if is_title_or_overview and not tmdb_data_en.get(en_key_movie if media_type == 'movie' else en_key_tv):
                        # Prepend [TRAKT] tag if it's the raw Trakt English title and no TMDb data (CS or EN) was found
                        return f"[TRAKT] {trakt_value}"
                    return trakt_value
                else:
                    xbmc.log(f"StreamContinuum: {log_context}: Trakt data also missing for {media_type} id={item_id} (S{season_num}E{episode_num}) key='{trakt_key}'", xbmc.LOGDEBUG)
            xbmc.log(f"StreamContinuum: {log_context}: No localized (CS/EN) or Trakt data found for {media_type} id={item_id} (S{season_num}E{episode_num}) key='{cs_key_movie if media_type=='movie' else cs_key_tv}'", xbmc.LOGDEBUG)
            return '' 

        # Helper for year as it's date-based, not just a string key
        def _get_best_year(cs_date_key, en_date_key, trakt_year_key=None, log_context=""):
            cs_year = tmdb_data_cs.get(cs_date_key, '')
            if cs_year:
                return cs_year[:4] # Return only year part
            
            en_year = tmdb_data_en.get(en_date_key, '')
            if en_year:
                xbmc.log(f"StreamContinuum: {log_context}: Fallback to EN-US year for {media_type} id={item_id} (S{season_num}E{episode_num}) key='{cs_date_key}'", xbmc.LOGDEBUG)
                return en_year[:4]
            
            if id_type == 'trakt' and trakt_year_key: 
                trakt_year = trakt_item_data.get(trakt_year_key, '')
                if trakt_year:
                    xbmc.log(f"StreamContinuum: {log_context}: Fallback to Trakt year for {media_type} id={item_id} (S{season_num}E{episode_num}) key='{trakt_year_key}'", xbmc.LOGDEBUG)
                else:
                    xbmc.log(f"StreamContinuum: {log_context}: Trakt year also missing for {media_type} id={item_id} (S{season_num}E{episode_num}) key='{trakt_year_key}'", xbmc.LOGDEBUG)
                return str(trakt_year)[:4]
            xbmc.log(f"StreamContinuum: {log_context}: No localized (CS/EN) or Trakt year found for {media_type} id={item_id} (S{season_num}E{episode_num}) key='{cs_date_key}'", xbmc.LOGDEBUG)
            return ''
            
        result = {}
        if media_type == 'movie':
            result['title'] = _get_best_string('title', '', 'title', '', 'title', log_context='Movie Title')
            result['overview'] = _get_best_string('overview', '', 'overview', '', 'overview', log_context='Movie Overview')
            result['year'] = _get_best_year('release_date', 'release_date', 'year', log_context='Movie Year')
            result['runtime'] = tmdb_data_cs.get('runtime', 0) or tmdb_data_en.get('runtime', 0) or trakt_item_data.get('runtime', 0)
            result['rating'] = tmdb_data_cs.get('vote_average', 0) or tmdb_data_en.get('vote_average', 0) or trakt_item_data.get('rating', 0)
        elif media_type == 'show':
            result['title'] = _get_best_string('', 'name', '', 'name', 'title', log_context='Show Title')
            result['overview'] = _get_best_string('overview', '', 'overview', '', 'overview', log_context='Show Overview')
            result['year'] = _get_best_year('first_air_date', 'first_air_date', 'year', log_context='Show Year')
            result['status'] = (tmdb_data_cs.get('status') or tmdb_data_en.get('status') or 
                                trakt_item_data.get('status', ''))
            result['runtime'] = (tmdb_data_cs.get('episode_run_time', [0])[0] if tmdb_data_cs.get('episode_run_time') else 0) or \
                                (tmdb_data_en.get('episode_run_time', [0])[0] if tmdb_data_en.get('episode_run_time') else 0) or \
                                trakt_item_data.get('runtime', 0)
            result['rating'] = tmdb_data_cs.get('vote_average', 0) or tmdb_data_en.get('vote_average', 0) or trakt_item_data.get('rating', 0)
        elif media_type == 'season':
            # trakt_key=None here so it doesn't fall back to show's title
            result['title'] = _get_best_string('', 'name', '', 'name', None, log_context=f'Season Title S{season_num}') or f"{ADDON.getLocalizedString(30105)} {season_num}"
            result['overview'] = _get_best_string('overview', '', 'overview', '', None, log_context=f'Season Overview S{season_num}')
            result['episode_count'] = tmdb_data_cs.get('episode_count', 0) or tmdb_data_en.get('episode_count', 0)
            result['year'] = _get_best_year('air_date', 'air_date', None, log_context=f'Season Year S{season_num}') # Season air date
            result['rating'] = tmdb_data_cs.get('vote_average', 0) or tmdb_data_en.get('vote_average', 0)
        elif media_type == 'episode':
            # trakt_key=None here so it doesn't fall back to show's title
            result['title'] = _get_best_string('', 'name', '', 'name', None, log_context=f'Episode Title S{season_num}E{episode_num}')
            result['overview'] = _get_best_string('overview', '', 'overview', '', None, log_context=f'Episode Overview S{season_num}E{episode_num}')
            result['runtime'] = tmdb_data_cs.get('runtime', 0) or tmdb_data_en.get('runtime', 0) # Episode runtime from TMDb
            result['year'] = _get_best_year('air_date', 'air_date', None, log_context=f'Episode Year S{season_num}E{episode_num}') # Episode air date
            result['rating'] = tmdb_data_cs.get('vote_average', 0) or tmdb_data_en.get('vote_average', 0)
            result['air_date'] = tmdb_data_cs.get('air_date') or tmdb_data_en.get('air_date') or trakt_item_data.get('first_aired', '')

        # Common fields (artwork, genres)
        # Artwork paths are universal, use the first available one (CS or EN response has them)
        poster_path_cs = tmdb_data_cs.get('poster_path')
        backdrop_path_cs = tmdb_data_cs.get('backdrop_path')
        poster_path_en = tmdb_data_en.get('poster_path')
        backdrop_path_en = tmdb_data_en.get('backdrop_path')
        
        final_poster_path = poster_path_cs or poster_path_en
        final_backdrop_path = backdrop_path_cs or backdrop_path_en

        result['poster'] = f"https://image.tmdb.org/t/p/w500{final_poster_path}" if final_poster_path else ''
        result['fanart'] = f"https://image.tmdb.org/t/p/original{final_backdrop_path}" if final_backdrop_path else ''
        
        # Genres, prefer localized but fall back to English if available
        # Genres are typically at movie/show level. Season/episode TMDb API endpoints do not provide genres directly.
        if media_type in ('movie', 'show'):
            result['genres'] = [g.get('name') for g in tmdb_data_cs.get('genres', []) if g.get('name')] or \
                               [g.get('name') for g in tmdb_data_en.get('genres', []) if g.get('name')] or \
                               trakt_item_data.get('genres', [])
        else: # seasons and episodes don't have genres directly in TMDb response
            result['genres'] = []
            
        return result
    except Exception as e:
        xbmc.log(f"StreamContinuum: TMDb API error getting localized data for {media_type} id={tmdb_id} (S{season_num}E{episode_num}): {e}", xbmc.LOGERROR)
        # Fallback to Trakt data on exception for all fields (if id_type was trakt)
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
