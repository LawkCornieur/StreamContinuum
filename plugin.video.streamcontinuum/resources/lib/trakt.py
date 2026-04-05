import xbmcgui
import xbmcaddon
import requests
import time

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
    return {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": client_id,
        "Authorization": f"Bearer {token}"
    }

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
