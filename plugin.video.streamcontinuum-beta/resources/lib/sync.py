import os
import json
import hashlib
import time
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
    import xbmc
    try:
        xbmc.log("StreamContinuum: Starting export_settings", xbmc.LOGINFO)
        
        # Check credentials
        if not ADDON.getSetting('ws_username') or not ADDON.getSetting('ws_password'):
            return False, "Není vyplněno uživatelské jméno nebo heslo pro Webshare."

        settings = {}
        for key in ['ws_username', 'ws_password', 'trakt_token', 'trakt_username', 'trakt_client_id', 'trakt_client_secret']:
            settings[key] = ADDON.getSetting(key)
        
        data = json.dumps(settings)
        encrypted = encrypt_data(data, pin)
        
        if not os.path.exists(PROFILE_DIR):
            os.makedirs(PROFILE_DIR)
            
        filepath = os.path.join(PROFILE_DIR, 'streamcontinuum_settings.enc')
        with open(filepath, 'wb') as f:
            f.write(encrypted)
            
        xbmc.log(f"StreamContinuum: Settings encrypted and saved to {filepath}", xbmc.LOGINFO)
            
        # Clean up sync folder
        files = webshare.get_sync_files()
        for f in files:
            name = f['name']
            if name.startswith('streamcontinuum_settings') and name.endswith('.enc'):
                xbmc.log(f"StreamContinuum: Found old settings file {name} ({f['ident']}), deleting...", xbmc.LOGINFO)
                webshare.delete_file(f['ident'])
                time.sleep(0.5)
                
        # Clean up public root
        public_files = webshare.get_user_files()
        for f in public_files:
            name = f['name']
            if name.startswith('streamcontinuum_settings') and name.endswith('.enc'):
                xbmc.log(f"StreamContinuum: Found old settings in root {name} ({f['ident']}), deleting...", xbmc.LOGINFO)
                webshare.delete_file(f['ident'])
                time.sleep(0.5)
                
        # Pauza, aby Webshare stačil zpracovat smazání před nahráváním nového souboru
        time.sleep(3)
        
        success = webshare.upload_file(filepath, 'streamcontinuum_settings.enc')
        if success:
            # Sleep 2 seconds to allow Webshare backend indexing to complete
            time.sleep(2)
            moved = webshare.move_to_sync('streamcontinuum_settings.enc')
            if not moved:
                return False, "Chyba při přesunu nastavení do složky StreamContinuum_Sync."
        else:
            return False, "Nahrávání nastavení na Webshare selhalo. Zkontrolujte přihlášení."
            
        xbmc.log("StreamContinuum: Export settings successful", xbmc.LOGINFO)
        return True, None
    except Exception as e:
        xbmc.log(f"StreamContinuum: export_settings error: {e}", xbmc.LOGERROR)
        return False, f"Chyba při exportu: {str(e)}"

def import_settings(pin):
    import xbmc
    try:
        # Check credentials
        if not ADDON.getSetting('ws_username') or not ADDON.getSetting('ws_password'):
            return False, "Není vyplněno uživatelské jméno nebo heslo pro Webshare."

        files = webshare.get_sync_files()
        ident = None
        matched_name = None
        
        # First try to find exact name match
        for f in files:
            if f['name'] == 'streamcontinuum_settings.enc':
                ident = f['ident']
                matched_name = f['name']
                break
                
        # Fallback to any matching name
        if not ident:
            for f in files:
                name = f['name']
                if name.startswith('streamcontinuum_settings') and name.endswith('.enc'):
                    ident = f['ident']
                    matched_name = name
                    break
                    
        if not ident:
            return False, "Soubor s nastavením nebyl na Webshare nalezen."
            
        xbmc.log(f"StreamContinuum: Importing settings from file: {matched_name} ({ident})", xbmc.LOGINFO)
        
        link = webshare.get_link(ident)
        if not link:
            return False, "Nelze získat odkaz pro stažení souboru z Webshare."
            
        resp = requests.get(link)
        if resp.status_code != 200:
            return False, f"Chyba při stahování souboru z Webshare (HTTP {resp.status_code})."
            
        encrypted = resp.content
        
        try:
            data = decrypt_data(encrypted, pin)
        except Exception as decrypt_err:
            xbmc.log(f"StreamContinuum: Decryption failed: {decrypt_err}", xbmc.LOGERROR)
            return False, "Chyba dešifrování nastavení (nesprávný PIN?)."
            
        try:
            settings = json.loads(data)
        except Exception as json_err:
            xbmc.log(f"StreamContinuum: JSON parsing failed: {json_err}", xbmc.LOGERROR)
            return False, "Soubor obsahuje neplatná data (poškozená záloha)."
            
        for key, value in settings.items():
            ADDON.setSetting(key, value)
            
        xbmc.log("StreamContinuum: Settings imported successfully", xbmc.LOGINFO)
        return True, None
    except Exception as e:
        xbmc.log(f"StreamContinuum: import_settings error: {e}", xbmc.LOGERROR)
        return False, f"Chyba importu nastavení: {str(e)}"

def sync_history():
    import xbmc
    try:
        xbmc.log("StreamContinuum: Starting sync_history", xbmc.LOGINFO)
        
        # Check credentials
        if not ADDON.getSetting('ws_username') or not ADDON.getSetting('ws_password'):
            xbmc.log("StreamContinuum: Missing Webshare credentials for history sync", xbmc.LOGERROR)
            return False

        local_history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                try:
                    local_history = json.load(f)
                except Exception as e:
                    xbmc.log(f"StreamContinuum: Error loading local history: {e}", xbmc.LOGWARNING)
                    
        files = webshare.get_sync_files()
        
        # Find all history files
        remote_history_files = []
        for f in files:
            name = f['name']
            if name.startswith('streamcontinuum_history') and name.endswith('.json'):
                remote_history_files.append(f)
                
        remote_history = []
        for f in remote_history_files:
            xbmc.log(f"StreamContinuum: Loading remote history from {f['name']} ({f['ident']})", xbmc.LOGINFO)
            link = webshare.get_link(f['ident'])
            if link:
                try:
                    resp = requests.get(link, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, list):
                            remote_history.extend(data)
                except Exception as read_err:
                    xbmc.log(f"StreamContinuum: Error reading remote history from {f['name']}: {read_err}", xbmc.LOGERROR)
                    
        # Merge histories, keeping unique queries or titles
        final_history = []
        seen = set()
        for item in local_history + remote_history:
            title = item.get('query') or item.get('title')
            if title and title not in seen:
                final_history.append(item)
                seen.add(title)
                
        final_history = final_history[:50]
        
        if not os.path.exists(PROFILE_DIR):
            os.makedirs(PROFILE_DIR)
            
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_history, f, ensure_ascii=False, indent=4)
            
        # Delete all remote history files from sync folder
        for f in remote_history_files:
            xbmc.log(f"StreamContinuum: Deleting old remote history file {f['name']} ({f['ident']})", xbmc.LOGINFO)
            webshare.delete_file(f['ident'])
            time.sleep(0.5)
            
        # Also delete all history files from public root just in case
        public_files = webshare.get_user_files()
        for f in public_files:
            name = f['name']
            if name.startswith('streamcontinuum_history') and name.endswith('.json'):
                xbmc.log(f"StreamContinuum: Deleting old remote history in root {name} ({f['ident']})", xbmc.LOGINFO)
                webshare.delete_file(f['ident'])
                time.sleep(0.5)
                
        # Pauza, aby Webshare stačil zpracovat smazání před nahráváním nové historie
        time.sleep(3)
        
        success = webshare.upload_file(HISTORY_FILE, 'streamcontinuum_history.json')
        if success:
            # Sleep 2 seconds to allow Webshare backend indexing to complete
            time.sleep(2)
            moved = webshare.move_to_sync('streamcontinuum_history.json')
            if not moved:
                xbmc.log("StreamContinuum: Failed to move history file to StreamContinuum_Sync", xbmc.LOGERROR)
                return False
        else:
            xbmc.log("StreamContinuum: Failed to upload history file to Webshare", xbmc.LOGERROR)
            return False
            
        xbmc.log("StreamContinuum: History sync completed successfully", xbmc.LOGINFO)
        return True
    except Exception as e:
        xbmc.log(f"StreamContinuum: sync_history error: {e}", xbmc.LOGERROR)
        return False
