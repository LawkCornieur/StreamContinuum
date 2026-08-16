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
    # Odstranění kvality a formátů videa/audia
    q = re.sub(r'\b(2160p|1080p|720p|480p|4k|uhd|hd|hdtv|web-?dl|bluray|bdrip|dvdrip|dvd|x264|x265|h264|hevc|aac|ac3|dts)\b.*$', '', q, flags=re.IGNORECASE).strip()
    # Odstranění jazykových tagů a vydání
    q = re.sub(r'\b(cz|sk|en|dabing|dab|czdab|skdab|titulky|tit|cztit|sktit|repack|proper|extended|unrated)\b.*$', '', q, flags=re.IGNORECASE).strip()
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
                if is_series(q) or item.get('media_type') in ('tvshow', 'tv'):
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

    query_is_series = is_series(query)
    query_base = get_base_name(query).lower().strip()

    # Find existing item (either exact query match, or same TV series)
    existing_item = None
    remaining_history = []
    for item in history:
        item_q = item.get('query', '')
        item_is_series = is_series(item_q) or item.get('media_type') in ('tvshow', 'tv')
        item_base = get_base_name(item_q).lower().strip()
        
        is_same_exact = (item_q == query)
        is_same_series = (query_is_series or item.get('media_type') in ('tvshow', 'tv')) and item_is_series and (query_base and item_base and query_base == item_base)
        
        if is_same_exact or is_same_series:
            if not existing_item:
                existing_item = item
        else:
            remaining_history.append(item)
    
    history = remaining_history
    
    # If an existing item was found, use its data (to preserve TMDb info if already identified)
    if existing_item:
        existing_item['query'] = query
        item_to_add = existing_item
    else:
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
            item['identified_at'] = int(time.time())
            updated = True
            break
    if not updated:
        xbmc.log(f"StreamContinuum History: Failed to find history item to update for query '{original_query}'", xbmc.LOGWARNING)
    if updated:
        _save_history(history)
    return updated

def clear_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
        xbmc.log(f"StreamContinuum History: Cleared history file: {HISTORY_FILE}", xbmc.LOGINFO)
