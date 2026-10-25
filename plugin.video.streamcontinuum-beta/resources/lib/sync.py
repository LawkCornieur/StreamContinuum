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
SYNC_LOCK_FILE = os.path.join(PROFILE_DIR, 'sync.lock')

class SyncLock:
    def __init__(self, timeout=60):
        self.lock_file = SYNC_LOCK_FILE
        self.timeout = timeout
        self.acquired = False

    def acquire(self):
        try:
            if not os.path.exists(PROFILE_DIR):
                os.makedirs(PROFILE_DIR)
                
            now = time.time()
            if os.path.exists(self.lock_file):
                try:
                    mtime = os.path.getmtime(self.lock_file)
                    if (now - mtime) > self.timeout:
                        xbmc.log("StreamContinuum: Odstraňuji expirovaný sync.lock", xbmc.LOGWARNING)
                        try:
                            os.remove(self.lock_file)
                        except Exception:
                            pass
                    else:
                        xbmc.log("StreamContinuum: Synchronizace již běží v jiném procesu, přeskakuji.", xbmc.LOGINFO)
                        return False
                except Exception:
                    pass

            with open(self.lock_file, 'w') as f:
                f.write(str(int(now)))
            self.acquired = True
            return True
        except Exception as e:
            xbmc.log(f"StreamContinuum: Chyba při získání sync zámku: {e}", xbmc.LOGWARNING)
            return False

    def release(self):
        if self.acquired:
            try:
                if os.path.exists(self.lock_file):
                    os.remove(self.lock_file)
            except Exception:
                pass
            self.acquired = False

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

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
            'autoplay_next', 'autoplay_countdown', 'autoplay_continue_btn',
            'optimize_results', 'after_playback', 
            'open_last_history', 'enable_welcome_melody', 'auto_start', 
            'ssl_verify', 'enable_trakt_menu', 'ws_auto_sync'
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
            
        # 1. Smazat staré soubory nastavení na Webshare a ověřit jejich smazání
        webshare.purge_sync_files('streamcontinuum_settings')

        upload_res = webshare.upload_file(filepath, 'streamcontinuum_settings.enc', target_folder_name='StreamContinuum_Sync')
        if not upload_res:
            return False, "Nahrávání nastavení na Webshare selhalo. Zkontrolujte přihlášení."

        # 2. Post-upload deduplikace: ponechat pouze nově nahraný soubor
        new_ident = upload_res if isinstance(upload_res, str) else None
        webshare.prune_sync_duplicates('streamcontinuum_settings', keep_ident=new_ident)
            
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
            
        if valid_ident:
            webshare.prune_sync_duplicates('streamcontinuum_settings', keep_ident=valid_ident)
                    
        xbmc.log("StreamContinuum: Settings imported successfully", xbmc.LOGINFO)
        return True, None
    except Exception as e:
        xbmc.log(f"StreamContinuum: import_settings error: {e}", xbmc.LOGERROR)
        return False, f"Chyba importu nastavení: {str(e)}"

def sync_history(silent=False, force=False, reason=""):
    try:
        xbmc.log(f"StreamContinuum: Starting sync_history (silent={silent}, force={force}, reason='{reason}')", xbmc.LOGINFO)
        
        if not ADDON.getSetting('ws_username') or not ADDON.getSetting('ws_password'):
            if not silent:
                xbmc.log("StreamContinuum: Missing Webshare credentials for history sync", xbmc.LOGERROR)
            return False

        with SyncLock() as acquired:
            if not acquired:
                xbmc.log(f"StreamContinuum: sync_history skipped (lock busy, reason='{reason}')", xbmc.LOGINFO)
                return False

            now = time.time()
            if silent and not force:
                try:
                    last_sync = float(ADDON.getSetting('ws_last_sync_ts') or 0)
                    if now - last_sync < 60:
                        xbmc.log(f"StreamContinuum: sync_history throttled (last sync {int(now - last_sync)}s ago, reason='{reason}')", xbmc.LOGDEBUG)
                        return True
                except Exception:
                    pass

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

            # 5. Uložit historii i s platnými náhrobky lokálně
            history._save_history(final_history, tombstones=all_tombstones)

            # 5b. Vyhodnotit a doplnit nově navazující epizody ve watchlistu na základě synchronizovaného stavu před uploadem
            try:
                history.check_and_update_next_episodes(force=True)
            except Exception as ep_err:
                xbmc.log(f"StreamContinuum: check_and_update_next_episodes in sync error: {ep_err}", xbmc.LOGWARNING)

            # 6. Smazat původní soubory historie na Webshare a ověřit jejich smazání před uploadem
            purged = webshare.purge_sync_files('streamcontinuum_history')
            if not purged:
                xbmc.log("StreamContinuum: Varování - staré soubory historie nebylo možné plně ověřit před nahráním", xbmc.LOGWARNING)
                
            upload_res = webshare.upload_file(HISTORY_FILE, 'streamcontinuum_history.json', target_folder_name='StreamContinuum_Sync')
            if not upload_res:
                xbmc.log("StreamContinuum: Failed to upload history file to Webshare", xbmc.LOGERROR)
                return False

            # 7. Post-upload začištění: odstranit jakékoliv vzniklé duplicitní verze
            new_ident = upload_res if isinstance(upload_res, str) else None
            webshare.prune_sync_duplicates('streamcontinuum_history', keep_ident=new_ident)

            try:
                ADDON.setSetting('ws_last_sync_ts', str(int(now)))
            except Exception:
                pass

            xbmc.log(f"StreamContinuum: History sync completed successfully (reason='{reason}')", xbmc.LOGINFO)
            return True
    except Exception as e:
        xbmc.log(f"StreamContinuum: sync_history error: {e}", xbmc.LOGERROR)
        return False

def sync_history_bg(silent=True, force=False, reason=""):
    """
    Spustí synchronizaci historie asynchronně ve vlastním vlákně,
    aby neblokovala uživatelské rozhraní Kodi.
    """
    try:
        if not ADDON.getSettingBool('ws_auto_sync'):
            return
        if not ADDON.getSetting('ws_username') or not ADDON.getSetting('ws_password'):
            return

        import threading
        t = threading.Thread(
            target=sync_history,
            kwargs={'silent': silent, 'force': force, 'reason': reason},
            daemon=True
        )
        t.start()
    except Exception as e:
        xbmc.log(f"StreamContinuum: sync_history_bg launch error: {e}", xbmc.LOGWARNING)
