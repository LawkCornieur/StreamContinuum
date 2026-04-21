import os
import json
import hashlib
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad
# This is a virtual module provided by Kodi, it must be imported for the addon to function.
import xbmc
import xbmcaddon
import xbmcvfs
import webshare
import requests

ADDON = xbmcaddon.Addon()
PROFILE_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
HISTORY_FILE = os.path.join(PROFILE_DIR, 'history.json')

def get_key(pin):
    return hashlib.sha256(pin.encode('utf-8')).digest()

def encrypt_data(data, pin):
    key = get_key(pin)
    cipher = AES.new(key, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
    return cipher.iv + ct_bytes

def decrypt_data(data, pin):
    key = get_key(pin)
    iv = data[:16]
    ct = data[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    pt = unpad(cipher.decrypt(ct), AES.block_size)
    return pt.decode('utf-8')

def export_settings(pin):
    try:
        xbmc.log("StreamContinuum: Starting export_settings", xbmc.LOGINFO)
        settings = {}
        for key in ['ws_username', 'ws_password', 'trakt_token', 'trakt_username']:
            settings[key] = ADDON.getSetting(key)
        
        data = json.dumps(settings)
        encrypted = encrypt_data(data, pin)
        
        if not os.path.exists(PROFILE_DIR):
            os.makedirs(PROFILE_DIR)
            
        filepath = os.path.join(PROFILE_DIR, 'streamcontinuum_settings.enc')
        with open(filepath, 'wb') as f:
            f.write(encrypted)
            
        xbmc.log(f"StreamContinuum: Settings encrypted and saved to {filepath}", xbmc.LOGINFO)
            
        files = webshare.get_user_files()
        for f in files:
            if f['name'] == 'streamcontinuum_settings.enc':
                xbmc.log(f"StreamContinuum: Found old settings file {f['ident']}, deleting...", xbmc.LOGINFO)
                webshare.delete_file(f['ident'])
                
        success = webshare.upload_file(filepath, 'streamcontinuum_settings.enc')
        xbmc.log(f"StreamContinuum: Upload success={success}", xbmc.LOGINFO)
        return success
    except Exception as e:
        xbmc.log(f"StreamContinuum: export_settings error: {e}", xbmc.LOGERROR)
        return False

def import_settings(pin):
    files = webshare.get_user_files()
    ident = None
    for f in files:
        if f['name'] == 'streamcontinuum_settings.enc':
            ident = f['ident']
            break
            
    if not ident:
        return False
        
    link = webshare.get_link(ident)
    if not link:
        return False
        
    try:
        resp = requests.get(link)
        if resp.status_code == 200:
            encrypted = resp.content
            data = decrypt_data(encrypted, pin)
            settings = json.loads(data)
            for key, value in settings.items():
                ADDON.setSetting(key, value)
            return True
    except Exception as e:
        print(f"Import settings error: {e}")
    return False

def sync_history():
    local_history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            try:
                local_history = json.load(f)
            except:
                pass
                
    files = webshare.get_user_files()
    ident = None
    for f in files:
        if f['name'] == 'streamcontinuum_history.json':
            ident = f['ident']
            break
            
    remote_history = []
    if ident:
        link = webshare.get_link(ident)
        if link:
            try:
                resp = requests.get(link)
                if resp.status_code == 200:
                    remote_history = resp.json()
            except:
                pass
                
    final_history = []
    seen = set()
    for item in local_history + remote_history:
        if item['title'] not in seen:
            final_history.append(item)
            seen.add(item['title'])
            
    final_history = final_history[:50]
    
    if not os.path.exists(PROFILE_DIR):
        os.makedirs(PROFILE_DIR)
        
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_history, f, ensure_ascii=False, indent=4)
        
    if ident:
        webshare.delete_file(ident)
    webshare.upload_file(HISTORY_FILE, 'streamcontinuum_history.json')
    return True
