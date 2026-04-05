import os
import json
import xbmcaddon
import xbmcvfs

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

import re

def add_to_history(query, title):
    history = get_history()
    
    # Try to extract base title from series pattern (e.g., "Show Name S01E01")
    series_pattern = re.compile(r'^(.*)\s+S\d{2}E\d{2}', re.IGNORECASE)
    match = series_pattern.match(title)
    base_title = match.group(1).strip() if match else title
    
    # Remove existing entry with same base title if it's a series, or same title if not
    if match:
        history = [item for item in history if not (series_pattern.match(item.get('title', '')) and series_pattern.match(item.get('title', '')).group(1).strip() == base_title)]
    else:
        history = [item for item in history if not (item.get('title') == title)]
        
    # Add to top
    history.insert(0, {'query': query, 'title': title})
    # Keep only last 50
    history = history[:50]
    
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def clear_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
