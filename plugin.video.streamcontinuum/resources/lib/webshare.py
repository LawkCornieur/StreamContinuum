import requests
import xbmcaddon
import xbmcgui
import hashlib
import re

ADDON = xbmcaddon.Addon()

def login():
    username = ADDON.getSetting('ws_username')
    password = ADDON.getSetting('ws_password')
    
    if not username or not password:
        return None

    password_hash = hashlib.sha1(password.encode('utf-8')).hexdigest()
    
    url = "https://webshare.cz/api/login/"
    data = {
        'username': username,
        'password': password_hash,
        'digest': ''
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if 'OK' in response.text:
            token = re.search(r'<token>(.*?)</token>', response.text)
            if token:
                ADDON.setSetting('ws_token', token.group(1))
                return token.group(1)
    except Exception as e:
        print(f"Webshare login error: {e}")
        
    return None

def get_token():
    token = ADDON.getSetting('ws_token')
    if not token:
        token = login()
    return token

def search(query):
    token = get_token()
    if not token:
        return []

    url = "https://webshare.cz/api/search/"
    data = {
        'what': query,
        'token': token,
        'offset': 0,
        'limit': 50,
        'category': 'video',
        'sort': 'rating'
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        # Webshare returns XML. We'll use regex for simplicity as we don't have a full XML parser easily available
        files = []
        # Find all <file> blocks
        file_blocks = re.findall(r'<file>(.*?)</file>', response.text, re.DOTALL)
        for block in file_blocks:
            ident = re.search(r'<ident>(.*?)</ident>', block)
            name = re.search(r'<name>(.*?)</name>', block)
            size = re.search(r'<size>(.*?)</size>', block)
            if ident and name:
                files.append({
                    'ident': ident.group(1),
                    'name': name.group(1),
                    'size': int(size.group(1)) if size else 0
                })
        return files
    except Exception as e:
        print(f"Webshare search error: {e}")
        return []

def get_link(ident):
    token = get_token()
    if not token:
        return None

    url = "https://webshare.cz/api/file_link/"
    data = {
        'ident': ident,
        'token': token
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        link = re.search(r'<link>(.*?)</link>', response.text)
        if link:
            return link.group(1)
    except Exception as e:
        print(f"Webshare get_link error: {e}")
        
    return None
