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
import xbmc
import xbmcaddon
import xbmcvfs
import webshare
import requests
import urllib3
import history

try:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

ADDON = xbmcaddon.Addon()
PROFILE_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
HISTORY_FILE = os.path.join(PROFILE_DIR, 'history.json')

def get_ssl_verify():
    try:
        return ADDON.getSettingBool('ssl_verify')
    except Exception:
        return True

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

def _is_history_sync_filename(name):
    if not name:
        return False
    n = name.lower()
    return n.startswith('streamcontinuum_history')

def _is_settings_sync_filename(name):
    if not name:
        return False
    n = name.lower()
    return n.startswith('streamcontinuum_settings')

def export_settings(pin):
    try:
        xbmc.log("StreamContinuum: Starting export_settings", xbmc.LOGINFO)
        
        if not ADDON.getSetting('ws_username') or not ADDON.getSetting('ws_password'):
            return False, "Není vyplněno uživatelské jméno nebo heslo pro Webshare."

        settings = {}
        settings_keys = [
            'ws_username', 'ws_password', 'trakt_token', 'trakt_username', 
            'trakt_client_id', 'trakt_client_secret', 'tmdb_api_key',
            'autoplay_next', 'optimize_results', 'after_playback', 
            'open_last_history', 'enable_welcome_melody', 'auto_start', 
            'ssl_verify', 'enable_trakt_menu'
        ]
        for key in settings_keys:
            val = ADDON.getSetting(key)
            settings[key] = val
        
        data = json.dumps(settings)
        encrypted = encrypt_data(data, pin)
        
        if not os.path.exists(PROFILE_DIR):
            os.makedirs(PROFILE_DIR)
            
        filepath = os.path.join(PROFILE_DIR, 'streamcontinuum_settings.enc')
        with open(filepath, 'wb') as f:
            f.write(encrypted)
            
        xbmc.log(f"StreamContinuum: Settings encrypted and saved to {filepath}", xbmc.LOGINFO)
            
        files = webshare.get_sync_files()
        for f in files:
            if _is_settings_sync_filename(f.get('name')):
                xbmc.log(f"StreamContinuum: Found old settings file in sync {f.get('name')} ({f['ident']}), deleting...", xbmc.LOGINFO)
                webshare.delete_file(f['ident'])
                time.sleep(0.3)
                
        public_files = webshare.get_user_files()
        for f in public_files:
            if _is_settings_sync_filename(f.get('name')):
                xbmc.log(f"StreamContinuum: Found old settings in root {f.get('name')} ({f['ident']}), deleting...", xbmc.LOGINFO)
                webshare.delete_file(f['ident'])
                time.sleep(0.3)
                
        time.sleep(1.0)
        
        success = webshare.upload_file(filepath, 'streamcontinuum_settings.enc')
        if success:
            time.sleep(1)
            webshare.move_to_sync('streamcontinuum_settings.enc')
        else:
            return False, "Nahrávání nastavení na Webshare selhalo. Zkontrolujte přihlášení."
            
        xbmc.log("StreamContinuum: Export settings successful", xbmc.LOGINFO)
        return True, None
    except Exception as e:
        xbmc.log(f"StreamContinuum: export_settings error: {e}", xbmc.LOGERROR)
        return False, f"Chyba při exportu: {str(e)}"

def import_settings(pin):
    try:
        if not ADDON.getSetting('ws_username') or not ADDON.getSetting('ws_password'):
            return False, "Není vyplněno uživatelské jméno nebo heslo pro Webshare."

        files = webshare.get_sync_files()
        ident = None
        matched_name = None
        
        for f in files:
            if f.get('name') == 'streamcontinuum_settings.enc':
                ident = f['ident']
                matched_name = f['name']
                break
                
        if not ident:
            for f in files:
                if _is_settings_sync_filename(f.get('name')):
                    ident = f['ident']
                    matched_name = f['name']
                    break
                    
        if not ident:
            public_files = webshare.get_user_files()
            for f in public_files:
                if _is_settings_sync_filename(f.get('name')):
                    ident = f['ident']
                    matched_name = f['name']
                    break
                    
        if not ident:
            return False, "Soubor s nastavením nebyl na Webshare nalezen."
            
        xbmc.log(f"StreamContinuum: Importing settings from file: {matched_name} ({ident})", xbmc.LOGINFO)
        
        link = webshare.get_link(ident)
        if not link:
            return False, "Nelze získat odkaz pro stažení souboru z Webshare."
            
        resp = requests.get(link, verify=get_ssl_verify())
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
            if isinstance(value, bool):
                ADDON.setSettingBool(key, value)
            elif isinstance(value, int):
                ADDON.setSettingInt(key, value)
            else:
                ADDON.setSetting(key, str(value))
            
        xbmc.log("StreamContinuum: Settings imported successfully", xbmc.LOGINFO)
        return True, None
    except Exception as e:
        xbmc.log(f"StreamContinuum: import_settings error: {e}", xbmc.LOGERROR)
        return False, f"Chyba importu nastavení: {str(e)}"

def sync_history():
    try:
        xbmc.log("StreamContinuum: Starting sync_history", xbmc.LOGINFO)
        
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
        remote_history_files = []
        for f in files:
            if _is_history_sync_filename(f.get('name')):
                remote_history_files.append(f)
                
        public_files = webshare.get_user_files()
        for f in public_files:
            if _is_history_sync_filename(f.get('name')) and f['ident'] not in [rf['ident'] for rf in remote_history_files]:
                remote_history_files.append(f)
                
        remote_history = []
        for f in remote_history_files:
            xbmc.log(f"StreamContinuum: Loading remote history from {f.get('name')} ({f['ident']})", xbmc.LOGINFO)
            link = webshare.get_link(f['ident'])
            if link:
                try:
                    resp = requests.get(link, timeout=10, verify=get_ssl_verify())
                    if resp.status_code == 200:
                        try:
                            data = resp.json()
                            if isinstance(data, list):
                                remote_history.extend(data)
                        except Exception:
                            try:
                                data = json.loads(resp.text)
                                if isinstance(data, list):
                                    remote_history.extend(data)
                            except Exception:
                                pass
                except Exception as read_err:
                    xbmc.log(f"StreamContinuum: Error reading remote history from {f.get('name')}: {read_err}", xbmc.LOGERROR)
                    
        merged_map = {}
        for item in local_history + remote_history:
            if not isinstance(item, dict):
                continue
            q = item.get('query', '')
            t_title = item.get('title', '')
            tmdb_id = item.get('tmdb_id')
            is_tv = item.get('media_type') in ('tvshow', 'tv', 'show') or history.is_series(q)
            is_watched_flag = bool(item.get('is_watched', True))
            status_suffix = "_w" if is_watched_flag else "_uw"
            
            if is_tv:
                base = history.get_base_name(t_title if (t_title and not history.has_non_latin(t_title)) else q).lower().strip()
                if tmdb_id and str(tmdb_id).strip().lower() not in ('none', '', '0'):
                    key = f"tv_tmdb_{tmdb_id}{status_suffix}"
                elif base:
                    key = f"tv_base_{base}{status_suffix}"
                else:
                    key = f"{q or t_title}{status_suffix}"
            else:
                key = f"{q or t_title}{status_suffix}"
                
            if not key:
                continue
                
            if key not in merged_map:
                merged_map[key] = item
            else:
                existing_time = history._safe_timestamp(merged_map[key].get('last_played_at')) or history._safe_timestamp(merged_map[key].get('added_at'))
                item_time = history._safe_timestamp(item.get('last_played_at')) or history._safe_timestamp(item.get('added_at'))
                if item_time >= existing_time:
                    for meta_k in ['tmdb_id', 'title', 'year', 'plot', 'genres', 'rating', 'runtime', 'poster', 'fanart', 'media_type', 'identified_at']:
                        if item.get(meta_k) is None and merged_map[key].get(meta_k) is not None:
                            item[meta_k] = merged_map[key][meta_k]
                    merged_map[key] = item
                else:
                    for meta_k in ['tmdb_id', 'title', 'year', 'plot', 'genres', 'rating', 'runtime', 'poster', 'fanart', 'media_type', 'identified_at']:
                        if merged_map[key].get(meta_k) is None and item.get(meta_k) is not None:
                            merged_map[key][meta_k] = item[meta_k]
                
        final_history = list(merged_map.values())
        final_history.sort(key=lambda x: (history._safe_timestamp(x.get('last_played_at')) or history._safe_timestamp(x.get('added_at')) or 0), reverse=True)
        final_history = final_history[:60]
        
        if not os.path.exists(PROFILE_DIR):
            os.makedirs(PROFILE_DIR)
            
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_history, f, ensure_ascii=False, indent=4)
            
        for f in remote_history_files:
            xbmc.log(f"StreamContinuum: Deleting old remote history file {f.get('name')} ({f['ident']})", xbmc.LOGINFO)
            webshare.delete_file(f['ident'])
            time.sleep(0.3)
            
        time.sleep(1.0)
        
        success = webshare.upload_file(HISTORY_FILE, 'streamcontinuum_history.json')
        if success:
            time.sleep(1)
            webshare.move_to_sync('streamcontinuum_history.json')
        else:
            xbmc.log("StreamContinuum: Failed to upload history file to Webshare", xbmc.LOGERROR)
            return False
            
        xbmc.log("StreamContinuum: History sync completed successfully", xbmc.LOGINFO)
        return True
    except Exception as e:
        xbmc.log(f"StreamContinuum: sync_history error: {e}", xbmc.LOGERROR)
        return False
