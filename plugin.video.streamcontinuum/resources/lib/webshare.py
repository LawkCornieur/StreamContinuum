import requests
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
        print(f"Webshare get_salt error: {e}")
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
        print(f"Webshare login error: {e}")
        
    return None

def get_token():
    token = ADDON.getSetting('ws_token')
    if not token:
        token = login()
    return token

def search(query):
    url = BASE_URL + 'search/'
    data = {
        'what': query.encode('utf-8'),
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
                if ident is not None and name is not None:
                    files.append({
                        'ident': ident.text,
                        'name': name.text,
                        'size': int(size.text) if size is not None and size.text else 0
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
