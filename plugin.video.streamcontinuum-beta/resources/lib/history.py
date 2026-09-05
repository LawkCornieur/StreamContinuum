import os
import json
import xbmcaddon
import xbmcvfs
import re
import time
import xbmc
import datetime

try:
    import tmdb
except Exception:
    tmdb = None

ADDON = xbmcaddon.Addon()
PROFILE_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
HISTORY_FILE = os.path.join(PROFILE_DIR, 'history.json')

def _safe_timestamp(val):
    if not val:
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        pass
    try:
        val_str = str(val).replace('T', ' ').strip()
        if len(val_str) >= 10:
            dt = datetime.datetime.fromisoformat(val_str[:19])
            return int(dt.timestamp())
    except Exception:
        pass
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
            for idx, item in enumerate(items):
                if 'is_watched' not in item:
                    item['is_watched'] = True
                if not item.get('added_at'):
                    item['added_at'] = now - idx
                if not item.get('last_played_at'):
                    item['last_played_at'] = item['added_at']
                if item.get('title'):
                    item['title'] = sanitize_title(item['title'])
            
            items.sort(key=lambda x: max(_safe_timestamp(x.get('last_played_at')), _safe_timestamp(x.get('added_at'))), reverse=True)
            
            if not deduplicate:
                return items

            series_map = {}
            movie_map = {}
            for item in items:
                q = item.get('query', '')
                tmdb_id = item.get('tmdb_id')
                t_title = item.get('title', '')
                t_base = get_base_name(t_title).lower().strip() if (t_title and not has_non_latin(t_title)) else ''
                q_base = get_base_name(q).lower().strip()
                is_tv = item.get('media_type') in ('tvshow', 'tv', 'show') or is_series(q)

                if is_tv:
                    if tmdb_id and str(tmdb_id).strip().lower() not in ('none', '', '0'):
                        key = f"tmdb_{tmdb_id}"
                        if key not in series_map or (not series_map[key].get('tmdb_id') and tmdb_id):
                            series_map[key] = item
                    if t_base:
                        key = f"title_{t_base}"
                        if key not in series_map or (not series_map[key].get('tmdb_id') and tmdb_id):
                            series_map[key] = item
                    if q_base:
                        key = f"query_{q_base}"
                        if key not in series_map or (not series_map[key].get('tmdb_id') and tmdb_id):
                            series_map[key] = item
                else:
                    if tmdb_id and str(tmdb_id).strip().lower() not in ('none', '', '0'):
                        key = f"movie_tmdb_{tmdb_id}"
                        if key not in movie_map or (not movie_map[key].get('tmdb_id') and tmdb_id):
                            movie_map[key] = item
                    if t_base:
                        key = f"movie_title_{t_base}"
                        if key not in movie_map or (not movie_map[key].get('tmdb_id') and tmdb_id):
                            movie_map[key] = item
                    if q_base:
                        key = f"movie_query_{q_base}"
                        if key not in movie_map or (not movie_map[key].get('tmdb_id') and tmdb_id):
                            movie_map[key] = item

            seen_keys = set()
            unique_items = []
            for item in items:
                q = item.get('query', '')
                tmdb_id = item.get('tmdb_id')
                title = item.get('title')
                is_tv = item.get('media_type') in ('tvshow', 'tv', 'show') or is_series(q)
                
                q_base = get_base_name(q).lower().strip()
                t_base = get_base_name(title).lower().strip() if (title and not has_non_latin(title)) else ''

                if is_tv:
                    matched_source = None
                    if tmdb_id and f"tmdb_{tmdb_id}" in series_map:
                        matched_source = series_map[f"tmdb_{tmdb_id}"]
                    elif t_base and f"title_{t_base}" in series_map:
                        matched_source = series_map[f"title_{t_base}"]
                    elif q_base and f"query_{q_base}" in series_map:
                        matched_source = series_map[f"query_{q_base}"]

                    if matched_source and matched_source is not item:
                        for meta_k in ['tmdb_id', 'title', 'year', 'plot', 'genres', 'rating', 'runtime', 'poster', 'fanart', 'media_type', 'identified_at']:
                            if matched_source.get(meta_k) is not None and item.get(meta_k) is None:
                                item[meta_k] = matched_source[meta_k]
                        tmdb_id = item.get('tmdb_id')
                        title = item.get('title')
                        if title:
                            t_base = get_base_name(title).lower().strip() if not has_non_latin(title) else t_base

                    keys = []
                    if tmdb_id and str(tmdb_id).strip().lower() not in ('none', '', '0'):
                        keys.append(f"tmdb_{tmdb_id}")
                    if title and not has_non_latin(title):
                        tb = get_base_name(title).lower().strip()
                        if tb:
                            keys.append(f"title_{tb}")
                    if q_base:
                        keys.append(f"query_{q_base}")

                    if keys and any(k in seen_keys for k in keys):
                        continue
                    for k in keys:
                        seen_keys.add(k)
                else:
                    matched_source = None
                    if tmdb_id and f"movie_tmdb_{tmdb_id}" in movie_map:
                        matched_source = movie_map[f"movie_tmdb_{tmdb_id}"]
                    elif t_base and f"movie_title_{t_base}" in movie_map:
                        matched_source = movie_map[f"movie_title_{t_base}"]
                    elif q_base and f"movie_query_{q_base}" in movie_map:
                        matched_source = movie_map[f"movie_query_{q_base}"]

                    if matched_source and matched_source is not item:
                        for meta_k in ['tmdb_id', 'title', 'year', 'plot', 'genres', 'rating', 'runtime', 'poster', 'fanart', 'media_type', 'identified_at']:
                            if matched_source.get(meta_k) is not None and item.get(meta_k) is None:
                                item[meta_k] = matched_source[meta_k]
                        tmdb_id = item.get('tmdb_id')
                        title = item.get('title')

                    m_keys = []
                    if tmdb_id and str(tmdb_id).strip().lower() not in ('none', '', '0'):
                        m_keys.append(f"movie_tmdb_{tmdb_id}")
                    if title and not has_non_latin(title):
                        tb = get_base_name(title).lower().strip()
                        if tb:
                            m_keys.append(f"movie_title_{tb}")
                    q_norm = str(q).strip().lower()
                    if q_norm:
                        m_keys.append(f"movie_q_{q_norm}")
                    if q_base:
                        m_keys.append(f"movie_query_{q_base}")

                    if m_keys and any(k in seen_keys for k in m_keys):
                        continue
                    for k in m_keys:
                        seen_keys.add(k)

                unique_items.append(item)
            return unique_items
    except json.JSONDecodeError as jde:
        xbmc.log(f"StreamContinuum History: Corrupted history.json detected: {jde}", xbmc.LOGERROR)
        try:
            bak_file = HISTORY_FILE + '.corrupted'
            if os.path.exists(HISTORY_FILE):
                os.rename(HISTORY_FILE, bak_file)
        except Exception:
            pass
        return []
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
        temp_file = HISTORY_FILE + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(history_list, f, ensure_ascii=False, indent=4)
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        os.rename(temp_file, HISTORY_FILE)
    except Exception as e:
        xbmc.log(f"StreamContinuum History: Error saving history.json: {e}", xbmc.LOGERROR)

def add_to_history(query):
    if not query:
        return
    query_str = str(query).strip()
    history = get_history(deduplicate=False)
    now = int(time.time())
    
    new_item_template = {
        'query': query_str,
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

    query_is_series = is_series(query_str)
    query_base = get_base_name(query_str).lower().strip()

    existing_item = None
    matching_tmdb_item = None
    remaining_history = []
    for item in history:
        item_q = item.get('query', '')
        item_is_series = is_series(item_q) or item.get('media_type') in ('tvshow', 'tv', 'show')
        item_base = get_base_name(item_q).lower().strip()
        
        is_same_exact = (item_q == query_str)
        is_same_series = (query_is_series or item.get('media_type') in ('tvshow', 'tv', 'show')) and item_is_series and (
            (query_base and item_base and query_base == item_base) or
            (item.get('title') and not has_non_latin(item.get('title')) and get_base_name(item.get('title')).lower().strip() == query_base)
        )
        
        if is_same_exact or is_same_series:
            if not existing_item:
                existing_item = item
        else:
            remaining_history.append(item)
            
        if item_is_series and item.get('tmdb_id') and not matching_tmdb_item:
            if query_base and item_base == query_base:
                matching_tmdb_item = item
            elif item.get('title') and not has_non_latin(item.get('title')) and get_base_name(item.get('title')).lower().strip() == query_base:
                matching_tmdb_item = item
    
    history = remaining_history
    
    if existing_item:
        existing_item['query'] = query_str
        existing_item['is_watched'] = True
        existing_item['last_played_at'] = now
        if 'added_at' not in existing_item or not existing_item['added_at']:
            existing_item['added_at'] = now
        if not existing_item.get('tmdb_id') and matching_tmdb_item:
            for k in ['tmdb_id', 'title', 'year', 'plot', 'genres', 'rating', 'runtime', 'poster', 'fanart', 'media_type', 'identified_at']:
                if matching_tmdb_item.get(k) is not None:
                    existing_item[k] = matching_tmdb_item[k]
        item_to_add = existing_item
    else:
        item_to_add = new_item_template
        if matching_tmdb_item:
            for k in ['tmdb_id', 'title', 'year', 'plot', 'genres', 'rating', 'runtime', 'poster', 'fanart', 'media_type', 'identified_at']:
                if matching_tmdb_item.get(k) is not None:
                    item_to_add[k] = matching_tmdb_item[k]
        
    history.insert(0, item_to_add)
    history = history[:50]
    _save_history(history)

def add_to_watchlist_local(query, tmdb_data=None):
    if not query:
        return
    query_str = str(query).strip()
    history = get_history(deduplicate=False)
    now = int(time.time())
    
    query_is_series = is_series(query_str) or (tmdb_data and tmdb_data.get('media_type') in ('tvshow', 'tv', 'show'))
    query_base = get_base_name(query_str).lower().strip()
    
    existing_item = None
    remaining_history = []
    for item in history:
        item_q = item.get('query', '')
        item_is_series = is_series(item_q) or item.get('media_type') in ('tvshow', 'tv', 'show')
        item_base = get_base_name(item_q).lower().strip()
        
        is_same_exact = (item_q == query_str)
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
        existing_item['query'] = query_str
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
            'query': query_str,
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
    norm_old = str(old_query).strip().lower()
    old_base = get_base_name(old_query).strip().lower()
    
    updated = False
    for item in history:
        item_q = str(item.get('query', '')).strip()
        item_q_lower = item_q.lower()
        item_base = get_base_name(item_q).strip().lower()
        if item_q == str(old_query).strip() or item_q_lower == norm_old or (old_base and item_base == old_base):
            item['query'] = new_query
            item['last_played_at'] = now
            updated = True
            break
    if updated:
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

def check_and_update_next_episodes():
    if tmdb is None:
        return False
    try:
        all_items = get_history(deduplicate=False)
        if not all_items:
            return False
        
        watched_series = {}
        for item in all_items:
            q = item.get('query', '')
            is_tv = item.get('media_type') in ('tvshow', 'tv', 'show') or is_series(q)
            if not is_tv:
                continue
                
            ep_match = re.search(r'^(.*?)(?:[\s._-]+)?(?:S(\d+)\s*E(\d+)|\b(\d+)x(\d+)\b)', q, re.IGNORECASE)
            if not ep_match:
                continue
                
            raw_base = ep_match.group(1).strip() if ep_match.group(1) else ""
            cleaned_base = re.sub(r'[\s._-]+$', '', raw_base).strip()
            season = int(ep_match.group(2) or ep_match.group(4))
            episode = int(ep_match.group(3) or ep_match.group(5))
            ws_base = cleaned_base if cleaned_base else get_base_name(q)
            
            key = str(item.get('tmdb_id')) if item.get('tmdb_id') else ws_base.lower()
            is_watched = bool(item.get('is_watched', True))
            
            if key not in watched_series:
                watched_series[key] = {
                    'item': item,
                    'ws_base': ws_base,
                    'max_season': season,
                    'max_episode': episode,
                    'is_watched': is_watched,
                    'tmdb_id': item.get('tmdb_id')
                }
            else:
                curr = watched_series[key]
                if (season > curr['max_season']) or (season == curr['max_season'] and episode > curr['max_episode']):
                    curr['max_season'] = season
                    curr['max_episode'] = episode
                    curr['item'] = item
                    curr['is_watched'] = is_watched
                if item.get('tmdb_id') and not curr.get('tmdb_id'):
                    curr['tmdb_id'] = item.get('tmdb_id')

        today = datetime.date.today()
        updated_any = False
        
        for key, s_info in watched_series.items():
            if not s_info['is_watched']:
                continue
                
            tmdb_id = s_info.get('tmdb_id')
            ws_base = s_info['ws_base']
            last_s = s_info['max_season']
            last_e = s_info['max_episode']
            
            if not tmdb_id:
                search_title = s_info['item'].get('title') or ws_base
                try:
                    res = tmdb.search_tmdb(search_title)
                    for r in res:
                        if r.get('type') == 'show' and r.get('id'):
                            tmdb_id = r.get('id')
                            break
                except Exception:
                    pass
                    
            if not tmdb_id:
                continue
                
            try:
                show_details = tmdb.get_show_seasons(tmdb_id)
                if not show_details or 'seasons' not in show_details:
                    continue
                    
                curr_season_eps = tmdb.get_season_episodes(tmdb_id, last_s) or []
                next_ep_obj = next((e for e in curr_season_eps if e.get('episode_number') == last_e + 1), None)
                target_season = last_s
                target_episode = last_e + 1
                
                if not next_ep_obj:
                    next_season_obj = next((s for s in show_details.get('seasons', []) if s.get('season_number') == last_s + 1), None)
                    if next_season_obj:
                        next_season_eps = tmdb.get_season_episodes(tmdb_id, last_s + 1) or []
                        next_ep_obj = next((e for e in next_season_eps if e.get('episode_number') == 1), None)
                        target_season = last_s + 1
                        target_episode = 1
                        
                if next_ep_obj:
                    air_date_str = next_ep_obj.get('air_date')
                    is_aired = True
                    if air_date_str:
                        try:
                            air_dt = datetime.datetime.strptime(str(air_date_str)[:10], '%Y-%m-%d').date()
                            if air_dt > today:
                                is_aired = False
                        except Exception:
                            pass
                            
                    if is_aired:
                        next_query = f"{ws_base} S{target_season:02d}E{target_episode:02d}"
                        already_in_hist = any(
                            (it.get('query') == next_query or str(it.get('query', '')).strip().lower() == next_query.lower())
                            for it in all_items
                        )
                        if not already_in_hist:
                            ep_title = next_ep_obj.get('name') or f"Epizoda {target_episode}"
                            full_show_title = show_details.get('title') or s_info['item'].get('title') or ws_base
                            plot_text = next_ep_obj.get('overview') or show_details.get('overview') or ''
                            tmdb_data = {
                                'tmdb_id': tmdb_id,
                                'media_type': 'tvshow',
                                'title': full_show_title,
                                'year': int(str(air_date_str)[:4]) if (air_date_str and len(str(air_date_str)) >= 4) else show_details.get('year'),
                                'plot': plot_text,
                                'poster': next_ep_obj.get('still') or show_details.get('poster'),
                                'fanart': show_details.get('fanart'),
                                'rating': next_ep_obj.get('rating') or show_details.get('rating')
                            }
                            add_to_watchlist_local(next_query, tmdb_data)
                            all_items = get_history(deduplicate=False)
                            updated_any = True
            except Exception as check_e:
                xbmc.log(f"StreamContinuum History: Error checking next episode for {ws_base}: {check_e}", xbmc.LOGWARNING)
                
        return updated_any
    except Exception as e:
        xbmc.log(f"StreamContinuum History: check_and_update_next_episodes failed: {e}", xbmc.LOGERROR)
        return False

def clear_history():
    if os.path.exists(HISTORY_FILE):
        try:
            os.remove(HISTORY_FILE)
            xbmc.log(f"StreamContinuum History: Cleared history file: {HISTORY_FILE}", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"StreamContinuum History: Error clearing history file: {e}", xbmc.LOGERROR)
