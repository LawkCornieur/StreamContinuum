import requests
# This is a virtual module provided by Kodi, it must be imported for the addon to function.
import xbmc
import xbmcaddon
import xbmcgui
import hashlib
from xml.etree import ElementTree
from resources.lib.md5crypt import md5crypt

ADDON = xbmcaddon.Addon()
BASE_URL = "https://webshare.cz/api/"
HEADERS = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}

def get_salt(username):
    url = BASE_URL + 'salt/'
    data = {'username_or_email': username}
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10)
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
        response = requests.post(url, data=data, headers=HEADERS, timeout=10)
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
    url = BASE_URL + 'search/'
    data = {
        'what': query,
        'sort': 'rating',
        'limit': 50,
        'offset': 0,
        'category': 'video'
    }
    
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10)
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
        print(f"Webshare search error: {e}")
    return []

def get_link(ident):
    token = get_token()
    if not token:
        return None

    url = BASE_URL + 'file_link/'
    data = {
        'ident': ident,
        'wst': token
    }
    
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            root = ElementTree.fromstring(response.content)
            link = root.find('link')
            if link is not None and link.text:
                return link.text
    except Exception as e:
        print(f"Webshare get_link error: {e}")
        
    return None

def upload_file(filepath, filename):
    token = get_token()
    if not token:
        return None
        
    url = BASE_URL + 'upload_link/'
    data = {'wst': token}
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            root = ElementTree.fromstring(response.content)
            link = root.find('link')
            if link is not None and link.text:
                upload_url = link.text
                
                with open(filepath, 'rb') as f:
                    files = {'file': (filename, f)}
                    upload_data = {'wst': token}
                    up_resp = requests.post(upload_url, data=upload_data, files=files, timeout=30)
                    if up_resp.status_code == 200:
                        return True
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
        response = requests.post(url, data=data, headers=HEADERS, timeout=10)
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
        print(f"Webshare get_user_files error: {e}")
    return []

def delete_file(ident):
    token = get_token()
    if not token:
        return False
        
    url = BASE_URL + 'delete_file/'
    data = {'wst': token, 'ident': ident}
    try:
        response = requests.post(url, data=data, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return True
    except Exception as e:
        print(f"Webshare delete_file error: {e}")
    return False
