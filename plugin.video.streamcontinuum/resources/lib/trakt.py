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

def get_images(trakt_id, media_type):
    if not trakt_id:
        return '', ''
    endpoint = 'movies' if media_type in ('movie', 'Movie') else 'shows'
    url = f"https://api.trakt.tv/{endpoint}/{trakt_id}?extended=images"
    try:
        res = requests.get(url, headers=get_headers(), timeout=10)
        if res.status_code == 200:
            data = res.json()
            images = data.get('images', {}) or {}
            poster = (images.get('poster', {}).get('full') or
                      images.get('poster', {}).get('medium') or
                      images.get('poster', {}).get('thumb') or
                      data.get('image', ''))
            fanart = (images.get('fanart', {}).get('full') or
                      images.get('fanart', {}).get('medium') or
                      images.get('backdrop', {}).get('full') or
                      images.get('banner', {}).get('full') or
                      images.get('clearart', {}).get('full') or
                      '')
            return poster, fanart
    except Exception as e:
        xbmc.log(f"StreamContinuum: Trakt image fetch error: {e}", xbmc.LOGWARNING)
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
        # To avoid too many requests, we only take the top 15 recently watched
        for item in watched_shows[:15]:
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
