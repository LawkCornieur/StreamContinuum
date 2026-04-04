import xbmcgui
import xbmcaddon
import requests
import time

ADDON = xbmcaddon.Addon()
CLIENT_ID = "YOUR_TRAKT_CLIENT_ID" # Hardcoded for the addon
CLIENT_SECRET = "YOUR_TRAKT_CLIENT_SECRET"

def authenticate():
    # 1. Generate Device Code
    url = "https://api.trakt.tv/oauth/device/code"
    payload = {"client_id": CLIENT_ID}
    response = requests.post(url, json=payload).json()
    
    user_code = response['user_code']
    device_code = response['device_code']
    interval = response['interval']
    expires_in = response['expires_in']
    
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
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
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
