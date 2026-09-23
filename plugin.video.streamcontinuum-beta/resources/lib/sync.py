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
    return 'streamcontinuum_history' in str(name).lower().strip()

def _is_settings_sync_filename(name):
    if not name:
        return False
    return 'streamcontinuum_settings' in str(name).lower().strip()

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
            settings[key] = ADDON.getSetting(key)
        
        data = json.dumps(settings)
        encrypted = encrypt_data(data, pin)
        
        if not os.path.exists(PROFILE_DIR):
            os.makedirs(PROFILE_DIR)
            
        filepath = os.path.join(PROFILE_DIR, 'streamcontinuum_settings.enc')
        with open(filepath, 'wb') as f:
            f.write(encrypted)
            
        old_files = webshare.get_sync_files('streamcontinuum_settings')
        for f in old_files:
            ident = f.get('ident')
            if ident:
                xbmc.log(f"StreamContinuum: Cleaning old settings file {f.get('name')} ({ident})", xbmc.LOGINFO)
                webshare.delete_file(ident)
                
        upload_res = webshare.upload_file(filepath, 'streamcontinuum_settings.enc')
        if not upload_res:
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

        candidates = webshare.get_sync_files('streamcontinuum_settings')
        if not candidates:
            return False, "Soubor s nastavením nebyl na Webshare nalezen."
            
        successful_settings = None
        valid_ident = None
        
        for f in candidates:
            ident = f.get('ident')
            if not ident:
                continue
            matched_name = f.get('name')
            xbmc.log(f"StreamContinuum: Attempting to import settings from: {matched_name} ({ident})", xbmc.LOGINFO)
            link = webshare.get_link(ident)
            if not link:
                continue
            try:
                resp = requests.get(link, timeout=10, verify=get_ssl_verify())
                if resp.status_code != 200:
                    continue
                encrypted = resp.content
                data = decrypt_data(encrypted, pin)
                settings = json.loads(data)
                if isinstance(settings, dict) and settings:
                    successful_settings = settings
                    valid_ident = ident
                    break
            except Exception as candidate_err:
                xbmc.log(f"StreamContinuum: Candidate {ident} decryption failed: {candidate_err}", xbmc.LOGWARNING)
                continue
                
        if not successful_settings:
            return False, "Chyba dešifrování nastavení (nesprávný PIN nebo poškozený soubor)."
            
        for key, value in successful_settings.items():
            if isinstance(value, bool):
                ADDON.setSettingBool(key, value)
            elif isinstance(value, int):
                ADDON.setSettingInt(key, value)
            else:
                ADDON.setSetting(key, str(value))
            
        for f in candidates:
            ident = f.get('ident')
            if ident and ident != valid_ident:
                try:
                    webshare.delete_file(ident)
                except Exception:
                    pass
                    
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
                    if not isinstance(local_history, list):
                        local_history = []
                except Exception as e:
                    xbmc.log(f"StreamContinuum: Error loading local history: {e}", xbmc.LOGWARNING)
                    local_history = []
                    
        remote_files = webshare.get_sync_files('streamcontinuum_history')
        xbmc.log(f"StreamContinuum: Found {len(remote_files)} remote history files across Webshare", xbmc.LOGINFO)

        remote_history = []
        for f in remote_files[:5]:
            ident = f.get('ident')
            name = f.get('name', 'streamcontinuum_history.json')
            if not ident:
                continue
            xbmc.log(f"StreamContinuum: Loading remote history from {name} ({ident})", xbmc.LOGINFO)
            link = webshare.get_link(ident)
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
                    xbmc.log(f"StreamContinuum: Error reading remote history from {name}: {read_err}", xbmc.LOGERROR)
                    
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
            
        for f in remote_files:
            ident = f.get('ident')
            if ident:
                xbmc.log(f"StreamContinuum: Cleaning old remote history file {f.get('name')} ({ident})", xbmc.LOGINFO)
                webshare.delete_file(ident)
                
        upload_res = webshare.upload_file(HISTORY_FILE, 'streamcontinuum_history.json')
        if not upload_res:
            xbmc.log("StreamContinuum: Failed to upload history file to Webshare", xbmc.LOGERROR)
            return False
            
        xbmc.log("StreamContinuum: History sync completed successfully", xbmc.LOGINFO)
        return True
    except Exception as e:
        xbmc.log(f"StreamContinuum: sync_history error: {e}", xbmc.LOGERROR)
        return False
