import os
import json
import xbmcaddon
import xbmcvfs
import re

ADDON = xbmcaddon.Addon()
PROFILE_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
HISTORY_FILE = os.path.join(PROFILE_DIR, 'history.json')

def get_history():
    if not os.path.exists(PROFILE_DIR):
        os.makedirs(PROFILE_DIR)
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def get_base_name(query):
    if not query:
        return ""
    # Matches patterns like S01E01, s1e1, 1x01 and everything after it
    pattern = r'(?i)\s*(s\d+\s*e\d+|\d+x\d+).*$'
    base = re.sub(pattern, '', query).strip()
    return base if base else query

def add_to_history(query, title=None):
    history = get_history()
    
    base_name = get_base_name(query).lower()
    
    new_history = []
    for item in history:
        item_q = item.get('query', '')
        # Remove exact match
        if item_q == query:
            continue
        # Remove previous episodes of the same show, if base name matches
        if get_base_name(item_q).lower() == base_name and base_name != item_q.lower() and base_name != "":
            continue
        new_history.append(item)
    
    history = new_history
        
    # Add to top
    history.insert(0, {'query': query})
    # Keep only last 50
    history = history[:50]
    
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def delete_from_history(query):
    history = get_history()
    history = [item for item in history if item.get('query') != query]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def update_history_item(old_query, new_query, new_title=None):
    history = get_history()
    for item in history:
        if item.get('query') == old_query:
            item['query'] = new_query
            break
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def clear_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
