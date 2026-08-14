import os
import json
import xbmcaddon
import xbmcvfs
import re
import time
import xbmc

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
    except Exception as e:
        xbmc.log(f"StreamContinuum History: Error loading history.json: {e}", xbmc.LOGERROR)
        return []

def get_base_name(query):
    if not query:
        return ""
    # Matches patterns like S01E01, s1e1, 1x01 and everything after it
    base = re.sub(r'\s*(?:s\d+\s*e\d+|\d+x\d+).*$', '', query, flags=re.IGNORECASE).strip()
    
    # Also remove common year patterns like "(YYYY)" or "YYYY" at the end
    base = re.sub(r'\s*\(?\d{4}\)?$', '', base).strip()

    return base if base else query

def _save_history(history_list):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_list, f, ensure_ascii=False, indent=4)
    except Exception as e:
        xbmc.log(f"StreamContinuum History: Error saving history.json: {e}", xbmc.LOGERROR)

def add_to_history(query):
    history = get_history()
    
    # New item template with default None/empty values for TMDb data
    new_item_template = {
        'query': query,
        'title': None,
        'year': None,
        'plot': None,
        'genres': [],
        'rating': None,
        'runtime': None,
        'poster': None,
        'fanart': None,
        'tmdb_id': None,
        'media_type': None,
        'identified_at': None # Timestamp for when it was identified with TMDb
    }

    # Check for existing item with the exact same query
    existing_item = None
    for i, item in enumerate(history):
        if item.get('query') == query:
            existing_item = item
            # Remove it temporarily to re-add it at the top
            del history[i]
            break
    
    # If an existing item was found, use its data (to preserve TMDb info if already identified)
    if existing_item:
        # Update query in case of slight changes (e.g. case) and bring to top
        existing_item['query'] = query
        item_to_add = existing_item
    else:
        # If not found, create a new item with template values
        item_to_add = new_item_template
        
    # Add to top
    history.insert(0, item_to_add)
    
    # Keep only last 50
    history = history[:50]
    
    _save_history(history)

def delete_from_history(query):
    history = get_history()
    history = [item for item in history if item.get('query') != query]
    _save_history(history)

def update_history_item(old_query, new_query):
    history = get_history()
    for item in history:
        if item.get('query') == old_query:
            item['query'] = new_query
            # If it was identified, the identification is now potentially invalid
            # or at least the query has changed, so clear identification status
            item['title'] = None
            item['year'] = None
            item['plot'] = None
            item['genres'] = []
            item['rating'] = None
            item['runtime'] = None
            item['poster'] = None
            item['fanart'] = None
            item['tmdb_id'] = None
            item['media_type'] = None
            item['identified_at'] = None
            break
    _save_history(history)
    
def update_history_with_tmdb_data(original_query, tmdb_data):
    history = get_history()
    updated = False
    for i, item in enumerate(history):
        if item.get('query', '').strip() == original_query.strip(): # Robust comparison for Issue #13
            item['title'] = tmdb_data.get('title')
            item['year'] = tmdb_data.get('year')
            item['plot'] = tmdb_data.get('plot') # Use 'plot' from TMDb results dict
            item['genres'] = tmdb_data.get('genres', []) # Assume this is a list of strings
            item['rating'] = tmdb_data.get('rating') # Float
            item['runtime'] = tmdb_data.get('runtime') # Integer (minutes)
            item['poster'] = tmdb_data.get('poster')
            item['fanart'] = tmdb_data.get('fanart')
            item['tmdb_id'] = tmdb_data.get('tmdb_id')
            item['media_type'] = tmdb_data.get('media_type')
            item['identified_at'] = int(time.time()) # Timestamp for identification
            updated = True
            break
    if not updated: # Log if item not found, for Issue #13 debugging
        xbmc.log(f"StreamContinuum History: Failed to find history item to update for query '{original_query}'", xbmc.LOGWARNING)
    if updated:
        _save_history(history)
    return updated

def clear_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
        xbmc.log(f"StreamContinuum History: Cleared history file: {HISTORY_FILE}", xbmc.LOGINFO)
