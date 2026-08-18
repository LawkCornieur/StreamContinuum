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

def is_series(query):
    if not query:
        return False
    return bool(re.search(r'\b(s\d+\s*e\d+|season\s*\d+|série\s*\d+|serie\s*\d+|s\d+\b|e\d+\b|\d+x\d+)\b', query, re.IGNORECASE))

def get_base_name(query):
    if not query:
        return ""
    q = query
    # Odstranění běžných video přípon
    q = re.sub(r'\.(mkv|avi|mp4|m4v|mov|wmv|ts|flv)$', '', q, flags=re.IGNORECASE)
    # Nahrazení teček, podtržítek a pomlček mezerami
    q = re.sub(r'[._]', ' ', q)
    # Odstranění označení sezón a epizod (S01E01, s1e1, 1x01, Season, Serie apod.)
    q = re.sub(r'\s*(?:s\d+\s*e\d+|\bseason\s*\d+|\bsérie\s*\d+|\bserie\s*\d+|\bs\d+\b|\be\d+\b|\d+x\d+).*$', '', q, flags=re.IGNORECASE).strip()
    # Odstranění kvality a formátů videa/audia/médií
    q = re.sub(r'\b(2160p|1080p|720p|480p|4k|uhd|hd|hdtv|web-?dl|bluray|blu-?ray|bdrip|brrip|dvdrip|dvd|laserdisk|laserdisc|cd|vhs|remux|x264|x265|h264|hevc|aac|ac3|dts)\b.*$', '', q, flags=re.IGNORECASE).strip()
    # Odstranění jazykových tagů a vydání
    q = re.sub(r'\b(cz|sk|en|de|czech|czdab|skdab|dabing|dab|czsub|sksub|sub|titulky|tit|cztit|sktit|repack|proper|extended|unrated)\b.*$', '', q, flags=re.IGNORECASE).strip()
    # Odstranění roku (YYYY) na konci
    q = re.sub(r'\s*\(?\d{4}\)?$', '', q).strip()
    # Odstranění přebytečných znaků na konci a vícenásobných mezer
    q = re.sub(r'[\-\–\—\s]+$', '', q).strip()
    q = re.sub(r'\s+', ' ', q).strip()
    return q if q else query

def get_history():
    if not os.path.exists(PROFILE_DIR):
        os.makedirs(PROFILE_DIR)
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            items = json.load(f)
            if not isinstance(items, list):
                return []
            
            # Deduplicate series keeping only the latest watched episode
            seen_series = set()
            unique_items = []
            for item in items:
                q = item.get('query', '')
                if is_series(q) or item.get('media_type') in ('tvshow', 'tv', 'show'):
                    base = get_base_name(q).lower().strip()
                    if base:
                        if base in seen_series:
                            continue
                        seen_series.add(base)
                unique_items.append(item)
            return unique_items
    except Exception as e:
        xbmc.log(f"StreamContinuum History: Error loading history.json: {e}", xbmc.LOGERROR)
        return []

def get_history_item(query):
    if not query:
        return None
    items = get_history()
    norm_q = query.strip().lower()
    for item in items:
        if item.get('query') == query or item.get('query', '').strip().lower() == norm_q:
            return item
    q_base = get_base_name(query).strip().lower()
    if q_base:
        for item in items:
            item_q = item.get('query', '')
            if (is_series(item_q) or item.get('media_type') in ('tvshow', 'tv', 'show')) and get_base_name(item_q).strip().lower() == q_base:
                return item
    return None

def _save_history(history_list):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_list, f, ensure_ascii=False, indent=4)
    except Exception as e:
        xbmc.log(f"StreamContinuum History: Error saving history.json: {e}", xbmc.LOGERROR)

def add_to_history(query):
    history = get_history()
    now = int(time.time())
    
    # New item template with default values and timestamps
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
        'identified_at': None,
        'is_watched': True,
        'last_played_at': now,
        'added_at': now
    }

    query_is_series = is_series(query)
    query_base = get_base_name(query).lower().strip()

    # Find existing item (either exact query match, or same TV series)
    existing_item = None
    remaining_history = []
    for item in history:
        item_q = item.get('query', '')
        item_is_series = is_series(item_q) or item.get('media_type') in ('tvshow', 'tv', 'show')
        item_base = get_base_name(item_q).lower().strip()
        
        is_same_exact = (item_q == query)
        is_same_series = (query_is_series or item.get('media_type') in ('tvshow', 'tv', 'show')) and item_is_series and (query_base and item_base and query_base == item_base)
        
        if is_same_exact or is_same_series:
            if not existing_item:
                existing_item = item
        else:
            remaining_history.append(item)
    
    history = remaining_history
    
    # If an existing item was found, use its data (to preserve TMDb info if already identified)
    if existing_item:
        existing_item['query'] = query
        existing_item['is_watched'] = True
        existing_item['last_played_at'] = now
        item_to_add = existing_item
    else:
        item_to_add = new_item_template
        
    # Add to top
    history.insert(0, item_to_add)
    
    # Keep only last 50
    history = history[:50]
    
    _save_history(history)

def set_watched_status(query, is_watched):
    history = get_history()
    norm_q = query.strip().lower() if query else ""
    q_base = get_base_name(query).strip().lower() if query else ""
    updated = False
    for item in history:
        item_query = item.get('query', '').strip().lower()
        item_base = get_base_name(item.get('query', '')).strip().lower()
        if item_query == norm_q or (q_base and item_base == q_base):
            item['is_watched'] = bool(is_watched)
            updated = True
            break
    if updated:
        _save_history(history)
    return updated

def delete_from_history(query):
    history = get_history()
    history = [item for item in history if item.get('query') != query]
    _save_history(history)

def update_history_item(old_query, new_query):
    history = get_history()
    for item in history:
        if item.get('query') == old_query:
            item['query'] = new_query
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
    now = int(time.time())
    norm_orig = original_query.strip().lower() if original_query else ""
    orig_base = get_base_name(original_query).strip().lower() if original_query else ""
    
    for i, item in enumerate(history):
        item_query = item.get('query', '').strip().lower()
        item_base = get_base_name(item.get('query', '')).strip().lower()
        if item_query == norm_orig or item.get('query', '').strip() == original_query.strip() or (orig_base and item_base == orig_base):
            item['title'] = tmdb_data.get('title')
            item['year'] = tmdb_data.get('year')
            item['plot'] = tmdb_data.get('plot')
            item['genres'] = tmdb_data.get('genres', [])
            item['rating'] = tmdb_data.get('rating')
            item['runtime'] = tmdb_data.get('runtime')
            item['poster'] = tmdb_data.get('poster')
            item['fanart'] = tmdb_data.get('fanart')
            item['tmdb_id'] = tmdb_data.get('tmdb_id')
            item['media_type'] = tmdb_data.get('media_type')
            item['identified_at'] = now
            updated = True
            break
    if not updated and original_query:
        new_item = {
            'query': original_query,
            'title': tmdb_data.get('title'),
            'year': tmdb_data.get('year'),
            'plot': tmdb_data.get('plot'),
            'genres': tmdb_data.get('genres', []),
            'rating': tmdb_data.get('rating'),
            'runtime': tmdb_data.get('runtime'),
            'poster': tmdb_data.get('poster'),
            'fanart': tmdb_data.get('fanart'),
            'tmdb_id': tmdb_data.get('tmdb_id'),
            'media_type': tmdb_data.get('media_type'),
            'identified_at': now,
            'is_watched': True,
            'last_played_at': now,
            'added_at': now
        }
        history.insert(0, new_item)
        history = history[:50]
        updated = True
    if updated:
        _save_history(history)
    return updated

def clear_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
        xbmc.log(f"StreamContinuum History: Cleared history file: {HISTORY_FILE}", xbmc.LOGINFO)
