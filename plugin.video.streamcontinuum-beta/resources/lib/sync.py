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
HISTORY_FILE = history.HISTORY_FILE

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

def validate_history_item(item):
    norm = history.normalize_history_item(item)
    if norm:
        norm.pop('_raw_title_hint', None)
    return norm

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
                xbmc.log(f"StreamContinuum: Cleaning old settings file {f.get('name')} ({ident}) before upload", xbmc.LOGINFO)
                deleted = webshare.delete_file(ident)
                if deleted:
                    xbmc.log(f"StreamContinuum: Deleted old settings file {ident}", xbmc.LOGINFO)
                else:
                    xbmc.log(f"StreamContinuum: Failed to delete old settings file {ident}", xbmc.LOGWARNING)

        upload_res = webshare.upload_file(filepath, 'streamcontinuum_settings.enc', target_folder_name='StreamContinuum_Sync')
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

        raw_local = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                try:
                    loaded = json.load(f)
                    if isinstance(loaded, list):
                        raw_local = loaded
                except Exception as e:
                    xbmc.log(f"StreamContinuum: Error loading local history: {e}", xbmc.LOGWARNING)
                    raw_local = []
                    
        local_active = [it for it in raw_local if isinstance(it, dict) and not it.get('is_deleted') and str(it.get('query', '')).strip()]
        local_tombstones = history.merge_tombstones(
            history.load_tombstones(),
            [it for it in raw_local if isinstance(it, dict) and it.get('is_deleted')]
        )
                    
        remote_files = webshare.get_sync_files('streamcontinuum_history')
        xbmc.log(f"StreamContinuum: Found {len(remote_files)} remote history files across Webshare", xbmc.LOGINFO)

        remote_history = []
        remote_tombstones = []
        for f in remote_files:
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
                        except Exception:
                            data = json.loads(resp.text)
                        if isinstance(data, list):
                            for r_it in data:
                                if isinstance(r_it, dict):
                                    if r_it.get('is_deleted'):
                                        remote_tombstones.append(r_it)
                                    elif str(r_it.get('query', '')).strip():
                                        remote_history.append(r_it)
                except Exception as read_err:
                    xbmc.log(f"StreamContinuum: Error reading remote history from {name}: {read_err}", xbmc.LOGERROR)

        # 1. Sloučit a vyčistit náhrobky ze všech zdrojů
        all_tombstones = history.merge_tombstones(local_tombstones, remote_tombstones)
        xbmc.log(f"StreamContinuum: Active tombstones for sync: {len(all_tombstones)}", xbmc.LOGINFO)

        # 2. Sloučit aktivní položky z lokálního disku i vzdáleného úložiště
        all_active_candidates = local_active + remote_history

        # 3. Vyřadit položky, které odpovídají platným náhrobkům smazání
        filtered_items = history.filter_items_by_tombstones(all_active_candidates, all_tombstones)

        # 4. Konsolidovat a deduplikovat výsledné položky
        final_history = history.consolidate_history_items(filtered_items)

        # 5. Uložit historii i s platnými náhrobky
        history._save_history(final_history, tombstones=all_tombstones)

        # Nejprve smazat staré soubory historie na Webshare, aby při nahrání nového souboru
        # nedocházelo ke kolizi názvu (přejmenování na streamcontinuum_history(ident).json) a selhání move_file
        for f in remote_files:
            ident = f.get('ident')
            if ident:
                xbmc.log(f"StreamContinuum: Cleaning old remote history file {f.get('name')} ({ident})", xbmc.LOGINFO)
                deleted = webshare.delete_file(ident)
                if deleted:
                    xbmc.log(f"StreamContinuum: Deleted old remote history file {ident}", xbmc.LOGINFO)
                else:
                    xbmc.log(f"StreamContinuum: Failed to delete old remote history file {ident}", xbmc.LOGWARNING)
            
        upload_res = webshare.upload_file(HISTORY_FILE, 'streamcontinuum_history.json', target_folder_name='StreamContinuum_Sync')
        if not upload_res:
            xbmc.log("StreamContinuum: Failed to upload history file to Webshare", xbmc.LOGERROR)
            return False

        xbmc.log("StreamContinuum: History sync completed successfully", xbmc.LOGINFO)
        return True
    except Exception as e:
        xbmc.log(f"StreamContinuum: sync_history error: {e}", xbmc.LOGERROR)
        return False
