import requests
import xbmcaddon
import xbmcgui
import hashlib

ADDON = xbmcaddon.Addon()

def login():
    username = ADDON.getSetting('ws_username')
    password = ADDON.getSetting('ws_password')
    
    if not username or not password:
        return None

    # Webshare API login usually requires SHA1 of password
    password_hash = hashlib.sha1(password.encode('utf-8')).hexdigest()
    
    url = "https://webshare.cz/api/login/"
    data = {
        'username': username,
        'password': password_hash,
        'digest': ''
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        # Webshare returns XML by default, but we can parse it or check status
        # Note: In a real addon, we'd use an XML parser or request JSON if supported
        if 'OK' in response.text:
            # Extract token using simple string manipulation or regex
            import re
            token = re.search(r'<token>(.*?)</token>', response.text)
            if token:
                ADDON.setSetting('ws_token', token.group(1))
                return token.group(1)
    except Exception as e:
        print(f"Webshare login error: {e}")
        
    return None

def get_token():
    token = ADDON.getSetting('ws_token')
    if not token:
        token = login()
    return token
