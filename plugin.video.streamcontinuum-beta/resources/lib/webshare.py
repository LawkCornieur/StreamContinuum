import requests
import time
import json
import xbmc
import xbmcaddon
import xbmcgui
import hashlib
from xml.etree import ElementTree
from resources.lib.md5crypt import md5crypt
import urllib3

try:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

ADDON = xbmcaddon.Addon()
BASE_URL = "https://webshare.cz/api/"
HEADERS = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}

_sync_folder_cache = None

def get_ssl_verify():
    try:
        return ADDON.getSettingBool('ssl_verify')
    except Exception:
        return True

def _get_node_text_or_attr(elem, keys):
    for k in keys:
        txt = elem.findtext(k)
        if txt and str(txt).strip():
            return str(txt).strip()
        val = elem.attrib.get(k)
        if val and str(val).strip():
            return str(val).strip()
        for attr_k, attr_v in elem.attrib.items():
            if attr_k.lower() == k.lower() and attr_v and str(attr_v).strip():
                return str(attr_v).strip()
    return None

def _parse_files_from_content(content):
    files = []
    seen_idents = set()
    if not content:
        return files

    try:
        root = ElementTree.fromstring(content)
        for elem in root.iter():
            ident = _get_node_text_or_attr(elem, ['ident', 'file_ident', 'id'])
            name = _get_node_text_or_attr(elem, ['name', 'file_name', 'filename', 'title'])
            if ident and name and ident not in seen_idents:
                seen_idents.add(ident)
                size_val = _get_node_text_or_attr(elem, ['size', 'file_size']) or '0'
                try:
                    size = int(size_val)
                except Exception:
                    size = 0
                img = _get_node_text_or_attr(elem, ['img', 'image', 'preview'])
                desc = _get_node_text_or_attr(elem, ['description', 'desc']) or ""
                files.append({
                    'ident': ident,
                    'name': name,
                    'size': size,
                    'img': img,
                    'description': desc
                })
    except Exception:
        pass

    if not files:
        try:
            data = json.loads(content) if isinstance(content, (str, bytes)) else content
            def _extract_from_json(obj):
                if isinstance(obj, dict):
                    ident = obj.get('ident') or obj.get('file_ident') or obj.get('id')
                    name = obj.get('name') or obj.get('file_name') or obj.get('title')
                    if ident and name and str(ident) not in seen_idents:
                        seen_idents.add(str(ident))
                        try:
                            size = int(obj.get('size', 0))
                        except Exception:
                            size = 0
                        files.append({
                            'ident': str(ident),
                            'name': str(name),
                            'size': size,
                            'img': obj.get('img'),
                            'description': obj.get('description', '')
                        })
                    for v in obj.values():
                        _extract_from_json(v)
                elif isinstance(obj, list):
                    for item in obj:
                        _extract_from_json(item)
            _extract_from_json(data)
        except Exception:
            pass

    return files

def _parse_folder_from_content(content, target_folder_name='StreamContinuum_Sync'):
    if not content:
        return None

    target_clean = target_folder_name.strip().lower()

    try:
        root = ElementTree.fromstring(content)
        for elem in root.iter():
            name_candidates = []
            if elem.text and elem.text.strip():
                name_candidates.append(elem.text.strip())
            for k in ['name', 'folder_name', 'title', 'dirname', 'label', 'dir']:
                v = elem.attrib.get(k) or elem.findtext(k)
                if v and str(v).strip():
                    name_candidates.append(str(v).strip())
            for attr_k, attr_v in elem.attrib.items():
                if attr_k.lower() in ('name', 'folder_name', 'title', 'dirname') and attr_v:
                    name_candidates.append(str(attr_v).strip())

            matches = any(cand.lower() == target_clean for cand in name_candidates)
            if matches:
                for k in ['ident', 'folder_ident', 'id', 'folder_id', 'dir_id']:
                    v = elem.attrib.get(k) or elem.findtext(k)
                    if v and str(v).strip():
                        return str(v).strip()
                for attr_k, attr_v in elem.attrib.items():
                    if attr_k.lower() in ('ident', 'folder_ident', 'id', 'folder_id') and attr_v:
                        return str(attr_v).strip()
                if elem.text and elem.text.strip() and elem.text.strip().lower() != target_clean:
                    return elem.text.strip()

        for parent in root.iter():
            for child in list(parent):
                child_text = (child.text or "").strip().lower()
                child_name = (child.attrib.get('name') or "").strip().lower()
                if child_text == target_clean or child_name == target_clean:
                    for k in ['ident', 'folder_ident', 'id', 'folder_id']:
                        v = parent.attrib.get(k) or parent.findtext(k) or child.attrib.get(k) or child.findtext(k)
                        if v and str(v).strip():
                            return str(v).strip()
    except Exception:
        pass

    try:
        data = json.loads(content) if isinstance(content, (str, bytes)) else content
        def _find_folder_json(obj):
            if isinstance(obj, dict):
                name = obj.get('name') or obj.get('folder_name') or obj.get('title') or obj.get('label')
                ident = obj.get('ident') or obj.get('folder_ident') or obj.get('id') or obj.get('folder_id')
                if name and ident and str(name).strip().lower() == target_clean:
                    return str(ident)
                for v in obj.values():
                    res = _find_folder_json(v)
                    if res:
                        return res
            elif isinstance(obj, list):
                for item in obj:
                    res = _find_folder_json(item)
                    if res:
                        return res
            return None
        found = _find_folder_json(data)
        if found:
            return found
    except Exception:
        pass

    return None

def get_salt(username):
    if not username:
        return None
    url = BASE_URL + 'salt/'
    data = {'username_or_email': username}
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
        if response.status_code == 200:
            root = ElementTree.fromstring(response.content)
            if root.find('status') is not None and root.find('status').text == 'OK':
                return root.find('salt').text
    except Exception as e:
        xbmc.log(f"Webshare get_salt error: {e}", xbmc.LOGERROR)
    return None

def login():
    username = ADDON.getSetting('ws_username')
    password = ADDON.getSetting('ws_password')
    
    if not username or not password:
        return None

    salt = get_salt(username)
    if not salt:
        return None

    password_hash = hashlib.sha1(md5crypt(password, salt).encode('utf-8')).hexdigest()
    
    url = BASE_URL + 'login/'
    data = {
        'username_or_email': username,
        'password': password_hash,
        'keep_logged_in': 1
    }
    
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
        if response.status_code == 200:
            root = ElementTree.fromstring(response.content)
            if root.find('status') is not None and root.find('status').text == 'OK':
                token = root.find('token').text
                if token:
                    ADDON.setSetting('ws_token', token)
                    return token
    except Exception as e:
        xbmc.log(f"Webshare login error: {e}", xbmc.LOGERROR)
        
    return None

def get_token():
    token = ADDON.getSetting('ws_token')
    if not token:
        token = login()
    return token

def search(query):
    if not query:
        return []
    url = BASE_URL + 'search/'
    data = {
        'what': query,
        'sort': 'rating',
        'limit': 50,
        'offset': 0,
        'category': 'video'
    }
    
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
        if response.status_code == 200:
            return _parse_files_from_content(response.content)
    except Exception as e:
        xbmc.log(f"Webshare search error: {e}", xbmc.LOGERROR)
    return []

def get_link(ident):
    if not ident:
        return None
    token = get_token()
    if not token:
        return None

    url = BASE_URL + 'file_link/'
    data = {
        'ident': ident,
        'wst': token
    }
    
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
        if response.status_code == 200:
            root = ElementTree.fromstring(response.content)
            link = root.find('link')
            if link is not None and link.text:
                return link.text
    except Exception as e:
        xbmc.log(f"Webshare get_link error: {e}", xbmc.LOGERROR)
        
    return None

def create_folder(foldername):
    token = get_token()
    if not token:
        return None
    url = BASE_URL + 'mkdir/'
    data = {
        'wst': token,
        'name': foldername,
        'folder_name': foldername,
        'private': 1
    }
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
        if response.status_code == 200:
            ident = _parse_folder_from_content(response.content, foldername)
            if ident:
                xbmc.log(f"Webshare: create_folder '{foldername}' ident: {ident}", xbmc.LOGINFO)
                return str(ident)
            try:
                root = ElementTree.fromstring(response.content)
                for k in ['ident', 'folder_ident', 'id', 'folder_id']:
                    id_node = root.find(k)
                    if id_node is not None and id_node.text and id_node.text.strip():
                        return id_node.text.strip()
                    id_attr = root.attrib.get(k)
                    if id_attr and id_attr.strip():
                        return id_attr.strip()
                status = _get_node_text_or_attr(root, ['status'])
                if status == 'OK':
                    return True
            except Exception:
                pass
            try:
                js = response.json()
                found_id = js.get('ident') or js.get('folder_ident') or js.get('id')
                if found_id:
                    return str(found_id)
            except Exception:
                pass
            if 'OK' in response.text:
                return True
    except Exception as e:
        xbmc.log(f"Webshare create_folder error: {e}", xbmc.LOGERROR)
    return None

def get_sync_folder_ident(force_refresh=False):
    global _sync_folder_cache
    if _sync_folder_cache and not force_refresh:
        return _sync_folder_cache

    token = get_token()
    if not token:
        xbmc.log("Webshare: Cannot get sync folder ident without token", xbmc.LOGWARNING)
        return None
        
    sync_folder_name = 'StreamContinuum_Sync'
    endpoints = [
        ('user_data/', {'wst': token}),
        ('user_folders/', {'wst': token, 'limit': 200, 'offset': 0}),
        ('folders/', {'wst': token, 'limit': 200, 'offset': 0}),
        ('user_files/', {'wst': token, 'limit': 200, 'offset': 0})
    ]

    for ep, data in endpoints:
        try:
            res = requests.post(BASE_URL + ep, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
            if res.status_code == 200:
                found_ident = _parse_folder_from_content(res.content, sync_folder_name)
                if found_ident:
                    xbmc.log(f"Webshare: Found sync folder ident via {ep}: {found_ident}", xbmc.LOGINFO)
                    _sync_folder_cache = str(found_ident)
                    return _sync_folder_cache
        except Exception as e:
            xbmc.log(f"Webshare get_sync_folder_ident error ({ep}): {e}", xbmc.LOGWARNING)
            
    xbmc.log(f"Webshare: Sync folder '{sync_folder_name}' not found, creating new...", xbmc.LOGINFO)
    created = create_folder(sync_folder_name)
    if isinstance(created, str) and created and created != 'True':
        _sync_folder_cache = str(created)
        return _sync_folder_cache
        
    time.sleep(1.0)
    for ep, data in endpoints:
        try:
            res = requests.post(BASE_URL + ep, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
            if res.status_code == 200:
                found_ident = _parse_folder_from_content(res.content, sync_folder_name)
                if found_ident:
                    xbmc.log(f"Webshare: Found newly created sync folder ident via {ep}: {found_ident}", xbmc.LOGINFO)
                    _sync_folder_cache = str(found_ident)
                    return _sync_folder_cache
        except Exception:
            pass

    xbmc.log(f"Webshare: Failed to resolve ident for sync folder '{sync_folder_name}'", xbmc.LOGERROR)
    return None

def upload_file(filepath, filename):
    token = get_token()
    if not token:
        return False
        
    folder_ident = get_sync_folder_ident()
    url = BASE_URL + 'upload_url/'
    data = {'wst': token}
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
        if response.status_code == 200:
            root = ElementTree.fromstring(response.content)
            url_node = root.find('url')
            if url_node is not None and url_node.text:
                upload_url = url_node.text
                
                for attempt in range(3):
                    try:
                        xbmc.log(f"StreamContinuum: Uploading {filename} to Webshare (attempt {attempt + 1}/3, folder: {folder_ident})...", xbmc.LOGINFO)
                        with open(filepath, 'rb') as f:
                            file_content = f.read()
                            
                        files = {'file': (filename, file_content, 'application/json' if filename.endswith('.json') else 'application/octet-stream')}
                        upload_data = {
                            'wst': token,
                            'private': '1'
                        }
                        if folder_ident:
                            upload_data['folder'] = str(folder_ident)
                            upload_data['folder_ident'] = str(folder_ident)
                            upload_data['target_folder'] = str(folder_ident)
                            upload_data['dir'] = str(folder_ident)
                            
                        up_resp = requests.post(upload_url, data=upload_data, files=files, timeout=60, verify=get_ssl_verify())
                        if up_resp.status_code in (200, 201):
                            if 'OK' in up_resp.text or '<status>OK</status>' in up_resp.text or 'ident' in up_resp.text or '"status":"OK"' in up_resp.text:
                                xbmc.log(f"StreamContinuum: Upload of {filename} successful on attempt {attempt + 1}", xbmc.LOGINFO)
                                return True
                            else:
                                xbmc.log(f"StreamContinuum: Upload of {filename} response: {up_resp.text}", xbmc.LOGWARNING)
                        else:
                            xbmc.log(f"StreamContinuum: Upload of {filename} failed with status {up_resp.status_code}", xbmc.LOGWARNING)
                    except Exception as e:
                        xbmc.log(f"StreamContinuum: Webshare upload_file attempt {attempt + 1} failed: {e}", xbmc.LOGWARNING)
                    if attempt < 2:
                        time.sleep(2)
                
    except Exception as e:
        xbmc.log(f"Webshare upload_file error: {e}", xbmc.LOGERROR)
    return False

def get_user_files():
    token = get_token()
    if not token:
        return []
        
    url = BASE_URL + 'user_files/'
    data = {'wst': token, 'limit': 200, 'offset': 0}
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
        if response.status_code == 200:
            return _parse_files_from_content(response.content)
    except Exception as e:
        xbmc.log(f"Webshare get_user_files error: {e}", xbmc.LOGERROR)
    return []

def delete_file(ident):
    if not ident:
        return False
    token = get_token()
    if not token:
        return False
        
    endpoints = ['file_delete/', 'delete_file/', 'remove_file/']
    for ep in endpoints:
        url = BASE_URL + ep
        data = {'wst': token, 'ident': ident}
        try:
            response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
            if response.status_code == 200:
                if 'OK' in response.text or 'status' in response.text:
                    xbmc.log(f"Webshare: delete_file {ident} via {ep} OK", xbmc.LOGINFO)
                    return True
        except Exception as e:
            xbmc.log(f"Webshare delete_file error ({ep}): {e}", xbmc.LOGWARNING)
    return False

def get_sync_files():
    token = get_token()
    if not token:
        return []
        
    folder_ident = get_sync_folder_ident()
    if not folder_ident:
        xbmc.log("Webshare get_sync_files: Cannot fetch sync files because folder ident is None", xbmc.LOGWARNING)
        return []

    files = []
    seen_idents = set()
    
    endpoints = [
        ('folder_files/', {'wst': token, 'folder': folder_ident, 'private': 1}),
        ('folder_files/', {'wst': token, 'ident': folder_ident, 'private': 1}),
        ('user_files/', {'wst': token, 'folder': folder_ident, 'private': 1}),
        ('files/', {'wst': token, 'folder': folder_ident, 'private': 1}),
    ]
    
    for ep, data in endpoints:
        try:
            url = BASE_URL + ep
            response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
            if response.status_code == 200:
                parsed = _parse_files_from_content(response.content)
                for f in parsed:
                    if f['ident'] not in seen_idents:
                        seen_idents.add(f['ident'])
                        files.append(f)
                if files:
                    break
        except Exception as e:
            xbmc.log(f"Webshare get_sync_files error ({ep}): {e}", xbmc.LOGWARNING)
            
    return files

def move_to_sync(filename):
    if not filename:
        return False
    token = get_token()
    if not token:
        return False
        
    folder_ident = get_sync_folder_ident()
    if not folder_ident:
        xbmc.log("Webshare move_to_sync: folder_ident is None, unable to move", xbmc.LOGERROR)
        return False
        
    time.sleep(0.5)

    sync_files = get_sync_files()
    found_in_sync = any(f.get('name') == filename for f in sync_files)

    user_files = get_user_files()
    root_idents = [f.get('ident') for f in user_files if f.get('name') == filename]

    if not found_in_sync and root_idents:
        for root_ident in root_idents:
            candidates = [
                ('file_update/', {'wst': token, 'ident': root_ident, 'folder': folder_ident, 'private': 1}),
                ('file_update/', {'wst': token, 'ident': root_ident, 'folder_ident': folder_ident, 'private': 1}),
                ('file_move/', {'wst': token, 'ident': root_ident, 'folder': folder_ident, 'private': 1}),
                ('file_move/', {'wst': token, 'ident': root_ident, 'target_folder': folder_ident, 'private': 1}),
                ('move_file/', {'wst': token, 'ident': root_ident, 'folder': folder_ident, 'private': 1}),
                ('folder_add_file/', {'wst': token, 'folder': folder_ident, 'ident': root_ident, 'private': 1}),
            ]

            for ep, data in candidates:
                try:
                    response = requests.post(BASE_URL + ep, data=data, headers=HEADERS, timeout=8, verify=get_ssl_verify())
                    if response.status_code == 200 and ('OK' in response.text or 'status' in response.text):
                        xbmc.log(f"Webshare: move_to_sync '{filename}' via {ep} OK", xbmc.LOGINFO)
                        break
                except Exception as e:
                    xbmc.log(f"Webshare move_to_sync attempt ({ep}) error: {e}", xbmc.LOGWARNING)

    time.sleep(0.5)
    sync_files_after = get_sync_files()
    is_in_sync = any(f.get('name') == filename for f in sync_files_after)

    if root_idents:
        sync_idents = [f.get('ident') for f in sync_files_after if f.get('name') == filename]
        for r_ident in root_idents:
            if r_ident not in sync_idents:
                xbmc.log(f"Webshare: Removing duplicate/old root file {filename} ({r_ident})", xbmc.LOGINFO)
                delete_file(r_ident)

    return is_in_sync

def run_speedtest(dialog=None):
    ssl_verify = get_ssl_verify()
    
    if dialog:
        dialog.update(5, "Měření odezvy serveru (Ping)...")
    
    ping_url = BASE_URL + 'salt/'
    pings = []
    for _ in range(3):
        try:
            t0 = time.time()
            requests.post(ping_url, data={'username_or_email': 'speedtest'}, timeout=5, verify=ssl_verify)
            pings.append((time.time() - t0) * 1000)
        except Exception:
            pass
        if dialog and dialog.iscanceled():
            return None
    
    avg_ping = (sum(pings) / len(pings)) if pings else 0.0
    
    test_urls = []
    try:
        results = search('1080p')
        if results:
            for r in results[:3]:
                link = get_link(r.get('ident'))
                if link:
                    test_urls.append(link)
                    break
    except Exception:
        pass
        
    if not test_urls:
        test_urls.append("https://webshare.cz/speedtest/download")
        
    total_bytes = 0
    start_time = None
    peak_mbps = 0.0
    duration_target = 8.0
    
    for test_url in test_urls:
        try:
            if dialog:
                dialog.update(20, f"Měření rychlosti stahování...\nOdezva: {avg_ping:.0f} ms")
            
            with requests.get(test_url, stream=True, timeout=10, verify=ssl_verify) as resp:
                if resp.status_code == 200:
                    start_time = time.time()
                    last_update = start_time
                    chunk_size = 128 * 1024
                    
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if not chunk:
                            break
                        total_bytes += len(chunk)
                        now = time.time()
                        elapsed = now - start_time
                        
                        if elapsed >= duration_target:
                            break
                            
                        if dialog and dialog.iscanceled():
                            return None
                            
                        if now - last_update >= 0.25:
                            last_update = now
                            current_mbps = (total_bytes * 8.0) / (elapsed * 1000000.0) if elapsed > 0 else 0.0
                            current_mbs = (total_bytes / (1024.0 * 1024.0)) / elapsed if elapsed > 0 else 0.0
                            if current_mbps > peak_mbps:
                                peak_mbps = current_mbps
                            
                            pct = int(20 + (elapsed / duration_target) * 75)
                            pct = min(95, max(20, pct))
                            
                            if dialog:
                                dialog.update(
                                    pct,
                                    f"Měření rychlosti stahování...\n"
                                    f"Aktuální rychlost: {current_mbps:.2f} Mbps ({current_mbs:.2f} MB/s)\n"
                                    f"Přeneseno: {total_bytes / (1024*1024):.1f} MB | Odezva: {avg_ping:.0f} ms"
                                )
                    
                    if total_bytes > 0:
                        break
        except Exception as e:
            xbmc.log(f"StreamContinuum: Speedtest chunk download error: {e}", xbmc.LOGWARNING)
            continue
            
    if not start_time or total_bytes == 0:
        return None
        
    total_elapsed = max(0.1, time.time() - start_time)
    avg_mbps = (total_bytes * 8.0) / (total_elapsed * 1000000.0)
    avg_mbs = (total_bytes / (1024.0 * 1024.0)) / total_elapsed
    if avg_mbps > peak_mbps:
        peak_mbps = avg_mbps
        
    return {
        'ping_ms': avg_ping,
        'avg_mbps': avg_mbps,
        'avg_mbs': avg_mbs,
        'peak_mbps': peak_mbps,
        'total_bytes': total_bytes,
        'duration': total_elapsed
    }
