import requests
import time
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
            root = ElementTree.fromstring(response.content)
            files = []
            for file_elem in root.findall('.//file'):
                ident = file_elem.find('ident')
                name = file_elem.find('name')
                size = file_elem.find('size')
                img = file_elem.find('img')
                description = file_elem.find('description')
                if ident is not None and name is not None:
                    files.append({
                        'ident': ident.text,
                        'name': name.text,
                        'size': int(size.text) if size is not None and size.text else 0,
                        'img': img.text if img is not None else None,
                        'description': description.text if description is not None else ""
                    })
            return files
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

def upload_file(filepath, filename):
    token = get_token()
    if not token:
        return False
        
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
                        xbmc.log(f"StreamContinuum: Uploading {filename} to Webshare (attempt {attempt + 1}/3)...", xbmc.LOGINFO)
                        with open(filepath, 'rb') as f:
                            files = {'file': (filename, f)}
                            upload_data = {
                                'wst': token,
                                'private': 1
                            }
                            up_resp = requests.post(upload_url, data=upload_data, files=files, timeout=60, verify=get_ssl_verify())
                            if up_resp.status_code == 200:
                                try:
                                    root = ElementTree.fromstring(up_resp.content)
                                    status = root.find('status')
                                    if status is not None and status.text == 'OK':
                                        xbmc.log(f"StreamContinuum: Upload of {filename} successful on attempt {attempt + 1}", xbmc.LOGINFO)
                                        return True
                                    else:
                                        xbmc.log(f"StreamContinuum: Upload of {filename} failed XML status: {up_resp.text}", xbmc.LOGWARNING)
                                except Exception as parse_err:
                                    xbmc.log(f"StreamContinuum: Upload of {filename} succeeded with HTTP 200 but failed to parse response XML: {parse_err}. Content: {up_resp.text}", xbmc.LOGWARNING)
                                    return True
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
    data = {'wst': token, 'limit': 100, 'offset': 0}
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
        if response.status_code == 200:
            root = ElementTree.fromstring(response.content)
            files = []
            for file_elem in root.findall('.//file'):
                ident = file_elem.find('ident')
                name = file_elem.find('name')
                if ident is not None and name is not None:
                    files.append({
                        'ident': ident.text,
                        'name': name.text
                    })
            return files
    except Exception as e:
        xbmc.log(f"Webshare get_user_files error: {e}", xbmc.LOGERROR)
    return []

def delete_file(ident):
    if not ident:
        return False
    token = get_token()
    if not token:
        return False
        
    url = BASE_URL + 'remove_file/'
    data = {'wst': token, 'ident': ident}
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
        if response.status_code == 200:
            root = ElementTree.fromstring(response.content)
            status = root.find('status')
            if status is not None and status.text == 'OK':
                xbmc.log(f"Webshare: remove_file {ident} OK", xbmc.LOGINFO)
                return True
    except Exception as e:
        xbmc.log(f"Webshare remove_file error: {e}", xbmc.LOGERROR)
    return False

def get_sync_files():
    token = get_token()
    if not token:
        return []
        
    url = BASE_URL + 'files/'
    data = {'wst': token, 'path': '/StreamContinuum_Sync/', 'private': 1}
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
        if response.status_code == 200:
            root = ElementTree.fromstring(response.content)
            files = []
            for file_elem in root.findall('.//file'):
                ident = file_elem.find('ident')
                name = file_elem.find('name')
                if ident is not None and name is not None:
                    files.append({
                        'ident': ident.text,
                        'name': name.text
                    })
            return files
    except Exception as e:
        xbmc.log(f"Webshare get_sync_files error: {e}", xbmc.LOGERROR)
    return []

def move_to_sync(filename):
    if not filename:
        return False
    token = get_token()
    if not token:
        return False
        
    url = BASE_URL + 'move_file/'
    data = {
        'wst': token,
        'src': f'/{filename}',
        'dest': '/StreamContinuum_Sync/',
        'src_private': 1,
        'dest_private': 1
    }
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10, verify=get_ssl_verify())
        if response.status_code == 200:
            root = ElementTree.fromstring(response.content)
            status = root.find('status')
            if status is not None and status.text == 'OK':
                xbmc.log(f"Webshare: move_to_sync '{filename}' OK", xbmc.LOGINFO)
                return True
    except Exception as e:
        xbmc.log(f"Webshare move_to_sync error: {e}", xbmc.LOGERROR)
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
