import xbmc
import xbmcgui
import xbmcaddon
import requests
import time
import urllib.parse

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

def get_localized_metadata(trakt_id, media_type, season_num=None, episode_num=None):
    """Načte lokalizovaná (česká) metadata a obrázky z TMDb pro daný Trakt ID, včetně sezón a epizod."""
    if not trakt_id:
        return {}

    # Initial Trakt API call to get TMDb ID for the show/movie.
    # For episodes/seasons, trakt_id is the show's trakt_id.
    trakt_endpoint_type = 'movies' if media_type == 'movie' else 'shows'
    url = f"https://api.trakt.tv/{trakt_endpoint_type}/{trakt_id}"
    
    tmdb_id = None
    trakt_item_data = {} # To store original Trakt data for fallback if TMDb fails
    try:
        res = requests.get(url, headers=get_headers(), timeout=10)
        if res.status_code == 200:
            trakt_item_data = res.json()
            tmdb_id = trakt_item_data.get('ids', {}).get('tmdb')
        else:
            xbmc.log(f"StreamContinuum: Trakt API failed to get TMDb ID for {media_type} id={trakt_id} (S{season_num}E{episode_num}), status={res.status_code}", xbmc.LOGWARNING)
            return {}
    except Exception as e:
        xbmc.log(f"StreamContinuum: Trakt API error getting TMDb ID for {media_type} id={trakt_id} (S{season_num}E{episode_num}): {e}", xbmc.LOGWARNING)
        return {}

    if not tmdb_id:
        return {}

    tmdb_url_template = None
    if media_type == 'movie':
        tmdb_url_template = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={{api_key}}&language=cs-CZ"
    elif media_type == 'show':
        tmdb_url_template = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={{api_key}}&language=cs-CZ"
    elif media_type == 'season' and season_num is not None:
        tmdb_url_template = f"https://themoviedb.org/3/tv/{tmdb_id}/season/{season_num}?api_key={{api_key}}&language=cs-CZ"
    elif media_type == 'episode' and season_num is not None and episode_num is not None:
        tmdb_url_template = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_num}/episode/{episode_num}?api_key={{api_key}}&language=cs-CZ"
    
    if not tmdb_url_template:
        xbmc.log(f"StreamContinuum: Invalid media_type '{media_type}' or missing season/episode numbers for TMDb lookup.", xbmc.LOGWARNING)
        return {}

    try:
        import tmdb
        tmdb_res = tmdb.make_tmdb_request(tmdb_url_template)
        
        if tmdb_res and tmdb_res.status_code == 200:
            tmdb_data = tmdb_res.json()
            
            result = {}
            # Generic fields, localized from TMDb, falling back to Trakt if TMDb CS is empty
            if media_type == 'movie':
                result['title'] = tmdb_data.get('title') or trakt_item_data.get('title')
                result['overview'] = tmdb_data.get('overview') or trakt_item_data.get('overview')
                result['year'] = tmdb_data.get('release_date', '')[:4] or trakt_item_data.get('year', '')
            elif media_type == 'show':
                result['title'] = tmdb_data.get('name') or trakt_item_data.get('title')
                result['overview'] = tmdb_data.get('overview') or trakt_item_data.get('overview')
                result['year'] = tmdb_data.get('first_air_date', '')[:4] or trakt_item_data.get('year', '')
                result['status'] = tmdb_data.get('status') or trakt_item_data.get('status', '') # Add status for shows
            elif media_type == 'season':
                # For season, name is e.g. "Season 1", overview is plot
                result['title'] = tmdb_data.get('name') or f"Season {season_num}" # Fallback to generic name
                result['overview'] = tmdb_data.get('overview') or trakt_item_data.get('overview')
                result['episode_count'] = tmdb_data.get('episode_count', 0)
            elif media_type == 'episode':
                result['title'] = tmdb_data.get('name') or trakt_item_data.get('title')
                result['overview'] = tmdb_data.get('overview') or trakt_item_data.get('overview')
                result['runtime'] = tmdb_data.get('runtime', 0) # Episode runtime from TMDb
            
            # Common fields (artwork, genres, rating)
            if media_type in ('movie', 'show'): # Poster/Fanart are typically at movie/show level
                poster_path = tmdb_data.get('poster_path')
                backdrop_path = tmdb_data.get('backdrop_path')
                result['poster'] = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ''
                result['fanart'] = f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else ''
                result['genres'] = [g.get('name') for g in tmdb_data.get('genres', []) if g.get('name')]
                result['rating'] = tmdb_data.get('vote_average', 0) # TMDb rating
                if media_type == 'movie':
                    result['runtime'] = tmdb_data.get('runtime', 0)
                else:
                    result['runtime'] = tmdb_data.get('episode_run_time', [0])[0] if tmdb_data.get('episode_run_time') else 0

            elif media_type in ('season', 'episode'):
                 result['rating'] = tmdb_data.get('vote_average', 0)
            
            return result
        else:
            xbmc.log(f"StreamContinuum: TMDb API failed to get localized data for {media_type} id={tmdb_id} (S{season_num}E{episode_num}), status={tmdb_res.status_code}", xbmc.LOGWARNING)
            # Fallback to just Trakt data if TMDb fails completely, still useful
            return {
                'title': trakt_item_data.get('title'),
                'overview': trakt_item_data.get('overview'),
                'year': trakt_item_data.get('year'),
                'poster': '', # No TMDb poster on error
                'fanart': '', # No TMDb fanart on error
                'genres': trakt_item_data.get('genres', []),
                'rating': trakt_item_data.get('rating', 0),
                'runtime': trakt_item_data.get('runtime', 0),
                'status': trakt_item_data.get('status', '')
            }
    except Exception as e:
        xbmc.log(f"StreamContinuum: TMDb API error getting localized data for {media_type} id={tmdb_id} (S{season_num}E{episode_num}): {e}", xbmc.LOGERROR)
        # Fallback to Trakt data on exception
        return {
            'title': trakt_item_data.get('title'),
            'overview': trakt_item_data.get('overview'),
            'year': trakt_item_data.get('year'),
            'poster': '',
            'fanart': '',
            'genres': trakt_item_data.get('genres', []),
            'rating': trakt_item_data.get('rating', 0),
            'runtime': trakt_item_data.get('runtime', 0),
            'status': trakt_item_data.get('status', '')
        }

def get_images(trakt_id, media_type):
    """Zpětně kompatibilní získání plakátu a fanartu."""
    meta = get_localized_metadata(trakt_id, media_type)
    if meta:
        return meta.get('poster', ''), meta.get('fanart', '')
    return '', ''


def get_user_info():
    url = "https://api.trakt.tv/users/me"
    try:
        res = requests.get(url, headers=get_headers())
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return None

def get_watchlist():
    url = "https://api.trakt.tv/sync/watchlist"
    try:
        res = requests.get(url, headers=get_headers())
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return []

def get_playback():
    url = "https://api.trakt.tv/sync/playback"
    try:
        res = requests.get(url, headers=get_headers())
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return []

def get_progress():
    # Get all watched shows
    url = "https://api.trakt.tv/sync/watched/shows?extended=noseasons"
    try:
        res = requests.get(url, headers=get_headers())
        if res.status_code != 200:
            return []
        watched_shows = res.json()
        
        # Sort by recently watched first
        watched_shows.sort(key=lambda x: str(x.get('last_watched_at') or ''), reverse=True)
        
        progress_list = []
        # For each show, get the next episode
        # To avoid too many requests, we take up to 20 recently watched shows for progress calculation
        for item in watched_shows[:20]: # Changed from [:100] to [:20] for performance
            show = item.get('show')
            show_id = show.get('ids', {}).get('trakt')
            if not show_id:
                continue
                
            prog_url = f"https://api.trakt.tv/shows/{show_id}/progress/watched"
            prog_res = requests.get(prog_url, headers=get_headers())
            if prog_res.status_code == 200:
                prog_data = prog_res.json()
                next_ep = prog_data.get('next_episode')
                if next_ep:
                    progress_list.append({
                        'type': 'episode',
                        'show': show,
                        'episode': next_ep
                    })
        return progress_list
    except:
        pass
    return []

def search_trakt(query):
    url = f"https://api.trakt.tv/search/movie,show?query={urllib.parse.quote(query)}"
    try:
        res = requests.get(url, headers=get_headers())
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return []

def mark_watched(media_type, trakt_id):
    url = "https://api.trakt.tv/sync/history"
    payload = {
        media_type + "s": [{"ids": {"trakt": trakt_id}}]
    }
    try:
        res = requests.post(url, json=payload, headers=get_headers())
        return res.status_code == 201
    except:
        return False

def mark_unwatched(media_type, trakt_id):
    url = "https://api.trakt.tv/sync/history/remove"
    payload = {
        media_type + "s": [{"ids": {"trakt": trakt_id}}]
    }
    try:
        res = requests.post(url, json=payload, headers=get_headers())
        return res.status_code == 200
    except:
        return False

def get_trending(media_type):
    # media_type can be 'movies' or 'shows'
    url = f"https://api.trakt.tv/{media_type}/trending?extended=full"
    try:
        res = requests.get(url, headers=get_headers(), timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: get_trending error: {e}", xbmc.LOGERROR)
    return []

def get_popular(media_type):
    # media_type can be 'movies' or 'shows'
    url = f"https://api.trakt.tv/{media_type}/popular?extended=full"
    try:
        res = requests.get(url, headers=get_headers(), timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: get_popular error: {e}", xbmc.LOGERROR)
    return []

def get_recommended(media_type):
    # media_type can be 'movies' or 'shows'
    url = f"https://api.trakt.tv/recommendations/{media_type}?extended=full&limit=30"
    try:
        res = requests.get(url, headers=get_headers(), timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: get_recommended error: {e}", xbmc.LOGERROR)
    return []

def get_seasons(show_id):
    url = f"https://api.trakt.tv/shows/{show_id}/seasons?extended=full"
    try:
        res = requests.get(url, headers=get_headers(), timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: get_seasons error: {e}", xbmc.LOGERROR)
    return []

def get_episodes(show_id, season):
    url = f"https://api.trakt.tv/shows/{show_id}/seasons/{season}?extended=full"
    try:
        res = requests.get(url, headers=get_headers(), timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        xbmc.log(f"StreamContinuum: get_episodes error: {e}", xbmc.LOGERROR)
    return []
