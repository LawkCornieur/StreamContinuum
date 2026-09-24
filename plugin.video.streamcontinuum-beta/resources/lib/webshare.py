import requests
import time
import json
import os
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

def get_ssl_verify():
    try:
        return ADDON.getSettingBool('ssl_verify')
    except Exception:
        return True

def _is_response_ok(response):
    if not response or response.status_code not in (200, 201):
        return False
    try:
        root = ElementTree.fromstring(response.content)
        status = root.findtext('status')
        if status and status.upper() == 'OK':
            return True
        if root.attrib.get('status', '').upper() == 'OK':
            return True
        for st in root.findall('.//status'):
            if st.text and st.text.upper() == 'OK':
                return True
    except Exception:
        pass
    try:
        js = response.json()
        if js.get('status', '').upper() == 'OK' or js.get('result', '').upper() == 'OK':
            return True
    except Exception:
        pass
    txt = response.text.upper()
    if '<STATUS>OK</STATUS>' in txt or '"STATUS":"OK"' in txt or '"STATUS": "OK"' in txt:
        return True
    return False

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
            tag = elem.tag.lower() if elem.tag else ''
            if tag in ('folder', 'dir', 'directory', 'folders', 'dirs'):
                continue
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

def search_user_files(query):
    token = get_token()
    if not token or not query:
        return []
    url = BASE_URL + 'search/'
    data = {
        'what': str(query).strip(),
        'sort': 'recent',
        'limit': 50,
        'offset': 0,
        'wst': token
    }
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
        if response.status_code == 200:
            return _parse_files_from_content(response.content)
    except Exception as e:
        xbmc.log(f"Webshare search_user_files error: {e}", xbmc.LOGWARNING)
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

def delete_file(ident):
    if not ident:
        return False
    token = get_token()
    if not token:
        return False
        
    data = {
        'ident': str(ident).strip(),
        'file_ident': str(ident).strip(),
        'id': str(ident).strip(),
        'wst': token
    }
    endpoints = ['file_delete/', 'delete_file/', 'user_file_delete/', 'file_remove/', 'user_files_delete/', 'delete/']
    for ep in endpoints:
        try:
            url = BASE_URL + ep
            response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
            if _is_response_ok(response):
                xbmc.log(f"Webshare: delete_file {ident} OK via {ep}", xbmc.LOGINFO)
                return True
        except Exception as e:
            xbmc.log(f"Webshare delete_file error on {ep}: {e}", xbmc.LOGWARNING)
    return False

def get_sync_files(filename_pattern=None):
    try:
        token = get_token()
        if not token:
            return []
            
        search_term = str(filename_pattern or 'streamcontinuum').lower().strip()
        results = search_user_files(search_term)
        if not results:
            return []
            
        found_files = []
        seen_idents = set()
        for f in results:
            ident = f.get('ident')
            name = str(f.get('name', '')).lower()
            if ident and ident not in seen_idents:
                if search_term in name:
                    seen_idents.add(ident)
                    found_files.append(f)
                    
        return found_files
    except Exception as e:
        xbmc.log(f"Webshare get_sync_files error: {e}", xbmc.LOGWARNING)
        return []

def upload_file(filepath, filename, target_folder_name='StreamContinuum_Sync'):
    token = get_token()
    if not token:
        xbmc.log("StreamContinuum: Webshare upload_file failed - missing token", xbmc.LOGERROR)
        return False
        
    if not os.path.exists(filepath):
        xbmc.log(f"StreamContinuum: Webshare upload_file failed - file {filepath} not found", xbmc.LOGERROR)
        return False

    try:
        with open(filepath, 'rb') as f:
            file_content = f.read()
    except Exception as e:
        xbmc.log(f"StreamContinuum: Failed to read local file {filepath}: {e}", xbmc.LOGERROR)
        return False

    folder_name = target_folder_name or 'StreamContinuum_Sync'
    for attempt in range(2):
        try:
            xbmc.log(f"StreamContinuum: Uploading {filename} to Webshare (folder: {folder_name}, attempt {attempt + 1}/2)...", xbmc.LOGINFO)
            url_res = requests.post(BASE_URL + 'upload_url/', data={'wst': token, 'folder': folder_name, 'dir': folder_name, 'directory': folder_name}, headers=HEADERS, timeout=10, verify=get_ssl_verify())
            if url_res.status_code != 200 or not _is_response_ok(url_res):
                xbmc.log(f"StreamContinuum: Failed to obtain upload_url from Webshare", xbmc.LOGWARNING)
                continue

            root = ElementTree.fromstring(url_res.content)
            url_node = root.find('url')
            if url_node is None or not url_node.text:
                xbmc.log("StreamContinuum: upload_url missing in Webshare response", xbmc.LOGWARNING)
                continue

            upload_url = url_node.text.strip()
            mime = 'application/json' if str(filename).endswith('.json') else 'application/octet-stream'
            files = {'file': (filename, file_content, mime)}
            upload_data = {
                'wst': token,
                'private': '1',
                'folder': folder_name,
                'dir': folder_name,
                'directory': folder_name
            }
            
            up_resp = requests.post(upload_url, data=upload_data, files=files, timeout=25, verify=get_ssl_verify())
            if up_resp.status_code in (200, 201):
                uploaded_ident = None
                try:
                    up_root = ElementTree.fromstring(up_resp.content)
                    uploaded_ident = up_root.findtext('ident') or up_root.findtext('file_ident')
                except Exception:
                    pass
                if not uploaded_ident:
                    try:
                        up_js = up_resp.json()
                        uploaded_ident = up_js.get('ident') or up_js.get('file_ident')
                    except Exception:
                        pass
                        
                if uploaded_ident or _is_response_ok(up_resp):
                    xbmc.log(f"StreamContinuum: Upload of {filename} successful on attempt {attempt + 1} (ident: {uploaded_ident})", xbmc.LOGINFO)
                    return uploaded_ident if uploaded_ident else True
                else:
                    xbmc.log(f"StreamContinuum: Upload of {filename} response: {up_resp.text[:120]}", xbmc.LOGWARNING)
            else:
                xbmc.log(f"StreamContinuum: Upload of {filename} failed with HTTP status {up_resp.status_code}", xbmc.LOGWARNING)
        except Exception as e:
            xbmc.log(f"StreamContinuum: Webshare upload_file attempt {attempt + 1} failed: {e}", xbmc.LOGWARNING)
        if attempt < 1:
            time.sleep(1)
            
    return False

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
