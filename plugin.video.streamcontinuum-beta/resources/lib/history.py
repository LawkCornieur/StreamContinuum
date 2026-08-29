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

def _safe_timestamp(val):
    if not val:
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0

def has_non_latin(s):
    if not s:
        return False
    for ch in str(s):
        o = ord(ch)
        if o > 0x024F and not (0x1E00 <= o <= 0x1EFF or 0x2000 <= o <= 0x206F):
            return True
    return False

def sanitize_title(s):
    if not s:
        return ""
    cleaned = []
    for ch in str(s):
        o = ord(ch)
        if o < 32 or (0x007F <= o <= 0x009F) or (0xD800 <= o <= 0xDFFF) or (0xFFF0 <= o <= 0xFFFF) or o >= 0x10000:
            continue
        cleaned.append(ch)
    return "".join(cleaned).strip()

def is_series(query):
    if not query:
        return False
    return bool(re.search(r'\b(s\d+\s*e\d+|season\s*\d+|série\s*\d+|serie\s*\d+|s\d+\b|e\d+\b|\d+x\d+)\b', str(query), re.IGNORECASE))

def get_base_name(query):
    if not query:
        return ""
    q = str(query)
    q = re.sub(r'\.(mkv|avi|mp4|m4v|mov|wmv|ts|flv)$', '', q, flags=re.IGNORECASE)
    q = re.sub(r'[._]', ' ', q)
    q = re.sub(r'\s*(?:s\d+\s*e\d+|\bseason\s*\d+|\bsérie\s*\d+|\bserie\s*\d+|\bs\d+\b|\be\d+\b|\d+x\d+).*$', '', q, flags=re.IGNORECASE).strip()
    q = re.sub(r'\b(2160p|1080p|720p|480p|4k|uhd|hd|hdtv|web-?dl|bluray|blu-?ray|bdrip|brrip|dvdrip|dvd|laserdisk|laserdisc|cd|vhs|remux|x264|x265|h264|hevc|aac|ac3|dts)\b.*$', '', q, flags=re.IGNORECASE).strip()
    q = re.sub(r'\b(cz|sk|en|de|czech|czdab|skdab|dabing|dab|czsub|sksub|sub|titulky|tit|cztit|sktit|repack|proper|extended|unrated)\b.*$', '', q, flags=re.IGNORECASE).strip()
    q = re.sub(r'\s*\(?\d{4}\)?$', '', q).strip()
    q = re.sub(r'[\-\–\—\s]+$', '', q).strip()
    q = re.sub(r'\s+', ' ', q).strip()
    return sanitize_title(q) if q else sanitize_title(str(query))

def get_history(deduplicate=True):
    if not os.path.exists(PROFILE_DIR):
        try:
            os.makedirs(PROFILE_DIR)
        except Exception:
            pass
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            items = json.load(f)
            if not isinstance(items, list):
                return []
            
            now = int(time.time())
            for item in items:
                if 'is_watched' not in item:
                    item['is_watched'] = True
                if 'added_at' not in item:
                    item['added_at'] = now
                if 'last_played_at' not in item:
                    item['last_played_at'] = now
                if item.get('title'):
                    item['title'] = sanitize_title(item['title'])
            
            items.sort(key=lambda x: max(_safe_timestamp(x.get('last_played_at')), _safe_timestamp(x.get('added_at'))), reverse=True)
            
            if not deduplicate:
                return items

            seen_series_keys = set()
            unique_items = []
            for item in items:
                q = item.get('query', '')
                tmdb_id = item.get('tmdb_id')
                title = item.get('title')
                is_tv = item.get('media_type') in ('tvshow', 'tv', 'show') or is_series(q)
                if is_tv:
                    keys = []
                    if tmdb_id and str(tmdb_id).strip().lower() not in ('none', '', '0'):
                        keys.append(f"tmdb_{tmdb_id}")
                    if title and not has_non_latin(title):
                        t_base = get_base_name(title).lower().strip()
                        if t_base:
                            keys.append(f"title_{t_base}")
                    q_base = get_base_name(q).lower().strip()
                    if q_base:
                        keys.append(f"query_{q_base}")
                    
                    if keys and any(k in seen_series_keys for k in keys):
                        continue
                    
                    for k in keys:
                        seen_series_keys.add(k)
                unique_items.append(item)
            return unique_items
    except Exception as e:
        xbmc.log(f"StreamContinuum History: Error loading history.json: {e}", xbmc.LOGERROR)
        return []

def get_history_item(query):
    if not query:
        return None
    items = get_history(deduplicate=False)
    norm_q = str(query).strip().lower()
    for item in items:
        if item.get('query') == query or str(item.get('query', '')).strip().lower() == norm_q:
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
        if not os.path.exists(PROFILE_DIR):
            os.makedirs(PROFILE_DIR)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_list, f, ensure_ascii=False, indent=4)
    except Exception as e:
        xbmc.log(f"StreamContinuum History: Error saving history.json: {e}", xbmc.LOGERROR)

def add_to_history(query):
    if not query:
        return
    history = get_history(deduplicate=False)
    now = int(time.time())
    
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

    existing_item = None
    remaining_history = []
    for item in history:
        item_q = item.get('query', '')
        item_is_series = is_series(item_q) or item.get('media_type') in ('tvshow', 'tv', 'show')
        item_base = get_base_name(item_q).lower().strip()
        
        is_same_exact = (item_q == query)
        is_same_series = (query_is_series or item.get('media_type') in ('tvshow', 'tv', 'show')) and item_is_series and (
            (query_base and item_base and query_base == item_base) or
            (item.get('title') and not has_non_latin(item.get('title')) and get_base_name(item.get('title')).lower().strip() == query_base)
        )
        
        if is_same_exact or is_same_series:
            if not existing_item:
                existing_item = item
        else:
            remaining_history.append(item)
    
    history = remaining_history
    
    if existing_item:
        existing_item['query'] = query
        existing_item['is_watched'] = True
        existing_item['last_played_at'] = now
        if 'added_at' not in existing_item or not existing_item['added_at']:
            existing_item['added_at'] = now
        item_to_add = existing_item
    else:
        item_to_add = new_item_template
        
    history.insert(0, item_to_add)
    history = history[:50]
    _save_history(history)

def add_to_watchlist_local(query, tmdb_data=None):
    if not query:
        return
    history = get_history(deduplicate=False)
    now = int(time.time())
    
    query_is_series = is_series(query) or (tmdb_data and tmdb_data.get('media_type') in ('tvshow', 'tv', 'show'))
    query_base = get_base_name(query).lower().strip()
    
    existing_item = None
    remaining_history = []
    for item in history:
        item_q = item.get('query', '')
        item_is_series = is_series(item_q) or item.get('media_type') in ('tvshow', 'tv', 'show')
        item_base = get_base_name(item_q).lower().strip()
        
        is_same_exact = (item_q == query)
        is_same_series = query_is_series and item_is_series and (
            (query_base and item_base and query_base == item_base) or
            (item.get('title') and not has_non_latin(item.get('title')) and get_base_name(item.get('title')).lower().strip() == query_base)
        )
        
        if is_same_exact or is_same_series:
            if not existing_item:
                existing_item = item
        else:
            remaining_history.append(item)
            
    history = remaining_history
    
    if existing_item:
        existing_item['query'] = query
        existing_item['is_watched'] = False
        existing_item['last_played_at'] = now
        if tmdb_data:
            for k in ['title', 'year', 'plot', 'genres', 'rating', 'runtime', 'poster', 'fanart', 'tmdb_id', 'media_type']:
                if k in tmdb_data and tmdb_data[k] is not None:
                    val = tmdb_data[k]
                    if k == 'title':
                        val = sanitize_title(val)
                    existing_item[k] = val
        item_to_add = existing_item
    else:
        item_to_add = {
            'query': query,
            'title': sanitize_title(tmdb_data.get('title')) if tmdb_data else None,
            'year': tmdb_data.get('year') if tmdb_data else None,
            'plot': tmdb_data.get('plot', '') if tmdb_data else '',
            'genres': tmdb_data.get('genres', []) if tmdb_data else [],
            'rating': tmdb_data.get('rating') if tmdb_data else None,
            'runtime': tmdb_data.get('runtime') if tmdb_data else None,
            'poster': tmdb_data.get('poster') if tmdb_data else None,
            'fanart': tmdb_data.get('fanart') if tmdb_data else None,
            'tmdb_id': tmdb_data.get('tmdb_id') if tmdb_data else None,
            'media_type': tmdb_data.get('media_type') if tmdb_data else ('tvshow' if query_is_series else 'movie'),
            'identified_at': now if (tmdb_data and tmdb_data.get('tmdb_id')) else None,
            'is_watched': False,
            'last_played_at': now,
            'added_at': now
        }
        
    history.insert(0, item_to_add)
    history = history[:50]
    _save_history(history)

def set_watched_status(query, is_watched):
    if not query:
        return False
    history = get_history(deduplicate=False)
    norm_q = str(query).strip().lower()
    q_base = get_base_name(query).strip().lower()
    updated = False
    for item in history:
        item_query = str(item.get('query', '')).strip().lower()
        item_base = get_base_name(item.get('query', '')).strip().lower()
        if item_query == norm_q or (q_base and item_base == q_base):
            item['is_watched'] = bool(is_watched)
            updated = True
            break
    if updated:
        _save_history(history)
    return updated

def delete_from_history(query):
    if not query:
        return
    history = get_history(deduplicate=False)
    history = [item for item in history if item.get('query') != query]
    _save_history(history)

def update_history_item(old_query, new_query):
    if not old_query or not new_query:
        return
    history = get_history(deduplicate=False)
    now = int(time.time())
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
            item['last_played_at'] = now
            break
    _save_history(history)
    
def update_history_with_tmdb_data(original_query, tmdb_data):
    if not original_query:
        return False
    history = get_history(deduplicate=False)
    updated = False
    now = int(time.time())
    norm_orig = str(original_query).strip().lower()
    orig_base = get_base_name(original_query).strip().lower()
    
    clean_title = sanitize_title(tmdb_data.get('title'))
    if has_non_latin(clean_title) or not clean_title:
        clean_title = orig_base or original_query

    for i, item in enumerate(history):
        item_query = str(item.get('query', '')).strip().lower()
        item_base = get_base_name(item.get('query', '')).strip().lower()
        if item_query == norm_orig or str(item.get('query', '')).strip() == str(original_query).strip() or (orig_base and item_base == orig_base):
            item['title'] = clean_title
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
            'title': clean_title,
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
        try:
            os.remove(HISTORY_FILE)
            xbmc.log(f"StreamContinuum History: Cleared history file: {HISTORY_FILE}", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"StreamContinuum History: Error clearing history file: {e}", xbmc.LOGERROR)
