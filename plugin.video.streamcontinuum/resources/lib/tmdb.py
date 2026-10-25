# -*- coding: utf-8 -*-
import os
import json
import time
import datetime
import random
import requests
import re
import xbmc
import xbmcaddon
import xbmcvfs
import urllib.parse
import urllib3

try:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

_tmdb_warning_shown = False
ADDON = xbmcaddon.Addon()

TMDB_CACHE_FILE = None
_tmdb_cache_data = None
_tmdb_cache_dirty = False

def _get_cache_file():
    global TMDB_CACHE_FILE
    if TMDB_CACHE_FILE is None:
        try:
            profile = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
            if not os.path.exists(profile):
                try:
                    os.makedirs(profile, exist_ok=True)
                except Exception:
                    pass
            TMDB_CACHE_FILE = os.path.join(profile, 'tmdb_cache.json')
        except Exception:
            return None
    return TMDB_CACHE_FILE

def _load_tmdb_cache():
    global _tmdb_cache_data
    if _tmdb_cache_data is not None:
        return _tmdb_cache_data
    cache_path = _get_cache_file()
    if not cache_path or not os.path.exists(cache_path):
        _tmdb_cache_data = {}
        return _tmdb_cache_data
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                _tmdb_cache_data = data
                return _tmdb_cache_data
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error loading TMDb cache: {e}", xbmc.LOGWARNING)
    _tmdb_cache_data = {}
    return _tmdb_cache_data

def _save_tmdb_cache():
    global _tmdb_cache_data, _tmdb_cache_dirty
    if not _tmdb_cache_dirty or _tmdb_cache_data is None:
        return
    cache_path = _get_cache_file()
    if not cache_path:
        return
    try:
        now = int(time.time())
        cleaned = {}
        for k, v in _tmdb_cache_data.items():
            if isinstance(v, dict):
                ts = v.get('ts', 0)
                ttl = v.get('ttl', 0)
                if (ts + ttl) > now:
                    cleaned[k] = v
        if len(cleaned) > 1500:
            sorted_keys = sorted(cleaned.keys(), key=lambda x: cleaned[x].get('ts', 0), reverse=True)
            cleaned = {k: cleaned[k] for k in sorted_keys[:1500]}
        _tmdb_cache_data = cleaned

        temp_file = f"{cache_path}.{os.getpid()}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(_tmdb_cache_data, f, ensure_ascii=False)
        os.replace(temp_file, cache_path)
        _tmdb_cache_dirty = False
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error saving TMDb cache: {e}", xbmc.LOGWARNING)

def get_cached_tmdb(key):
    cache = _load_tmdb_cache()
    entry = cache.get(str(key))
    if entry and isinstance(entry, dict):
        ts = entry.get('ts', 0)
        ttl = entry.get('ttl', 0)
        now = int(time.time())
        if (ts + ttl) > now:
            return entry.get('data')
    return None

def set_cached_tmdb(key, data, ttl):
    global _tmdb_cache_dirty
    if data is None:
        return
    cache = _load_tmdb_cache()
    now = int(time.time())
    cache[str(key)] = {
        'ts': now,
        'ttl': int(ttl),
        'data': data
    }
    _tmdb_cache_dirty = True
    _save_tmdb_cache()

def clear_tmdb_cache():
    global _tmdb_cache_data, _tmdb_cache_dirty
    _tmdb_cache_data = {}
    _tmdb_cache_dirty = False
    cache_path = _get_cache_file()
    if cache_path and os.path.exists(cache_path):
        try:
            os.remove(cache_path)
        except Exception:
            pass


def get_ssl_verify():
    try:
        return ADDON.getSettingBool('ssl_verify')
    except Exception:
        return True

def get_tmdb_api_keys():
    keys = []
    user_key = (ADDON.getSetting('tmdb_api_key') or '').strip()
    if user_key:
        keys.append(user_key)
    
    import base64
    fallbacks = [
        base64.b64decode(b'N2FkOTFhOWVkM2YzMTY0OTM1N2EwZDc1YjQ5NTk4YjQ=').decode('utf-8')
    ]
    for fb in fallbacks:
        if fb not in keys:
            keys.append(fb)
    return keys

def make_tmdb_request(url_template):
    global _tmdb_warning_shown
    keys = get_tmdb_api_keys()
    last_response = None
    
    for key in keys:
        url = url_template.format(api_key=key)
        try:
            res = requests.get(url, timeout=15, verify=get_ssl_verify())
            last_response = res
            if res.status_code == 200:
                return res
            elif res.status_code == 401:
                xbmc.log(f"StreamContinuum: TMDb request failed with 401 using key {key[:6]}..., trying next key", xbmc.LOGWARNING)
                continue
            else:
                return res
        except Exception as e:
            xbmc.log(f"StreamContinuum: TMDb request error with key {key[:6]}: {e}", xbmc.LOGERROR)
            
    if (last_response is None or last_response.status_code == 401) and not _tmdb_warning_shown:
        _tmdb_warning_shown = True
        try:
            import xbmcgui
            xbmcgui.Dialog().ok(
                "TMDb API Error",
                "Všechny veřejné TMDb API klíče selhaly (Chyba 401).\n\n"
                "Pro správné a plynulé načítání TV tipů, novinek a plakátů si prosím "
                "vytvořte vlastní bezplatný API klíč na stránce themoviedb.org a "
                "vložte jej do Nastavení doplňku (sekce API)."
            )
        except Exception as warning_e:
            xbmc.log(f"StreamContinuum: Failed to show TMDb warning dialog: {warning_e}", xbmc.LOGERROR)
            
    return last_response

def _extract_year(item, date_key):
    val = item.get(date_key)
    if not val:
        return ""
    try:
        val_str = str(val).strip()
        if len(val_str) >= 4:
            return val_str[:4]
    except Exception:
        pass
    return ""

def _has_non_latin(s):
    if not s:
        return False
    for ch in str(s):
        o = ord(ch)
        if o > 0x024F and not (0x1E00 <= o <= 0x1EFF or 0x2000 <= o <= 0x206F):
            return True
    return False

def _sanitize_string(s):
    if not s:
        return ""
    cleaned = []
    for ch in str(s):
        o = ord(ch)
        if o < 32 or (0x007F <= o <= 0x009F) or (0xD800 <= o <= 0xDFFF) or (0xFFF0 <= o <= 0xFFFF) or o >= 0x10000:
            continue
        cleaned.append(ch)
    return "".join(cleaned).strip()

def _extract_title(item, media_type):
    title = item.get('title') if media_type == 'movie' else item.get('name')
    orig_title = item.get('original_title') if media_type == 'movie' else item.get('original_name')
    
    title = _sanitize_string(title)
    orig_title = _sanitize_string(orig_title)
    
    if title and not _has_non_latin(title):
        return title
    if orig_title and not _has_non_latin(orig_title):
        return orig_title
        
    for t in (title, orig_title):
        if t:
            latin_part = "".join([c for c in t if ord(c) <= 0x024F or (0x1E00 <= ord(c) <= 0x1EFF)]).strip()
            if len(latin_part) >= 2:
                return _sanitize_string(latin_part)

    return orig_title or title or ""

def _format_item(item, default_media_type=None, default_info=""):
    media_type = item.get('media_type', default_media_type or 'movie')
    if media_type not in ('movie', 'tv', 'show'):
        media_type = default_media_type or 'movie'
    is_show = media_type in ('tv', 'show')
    
    title = _extract_title(item, 'tv' if is_show else 'movie')
    if not title:
        return None
        
    raw_title = title
    overview = str(item.get('overview') or '')
    poster_path = item.get('poster_path')
    backdrop_path = item.get('backdrop_path')
    img = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ''
    backdrop_img = f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else ''
    
    date_key = 'first_air_date' if is_show else 'release_date'
    year = _extract_year(item, date_key)
    
    rating_raw = item.get('vote_average', 0)
    rating_percent = int(rating_raw * 10) if rating_raw else 0
    
    display_title = f"[{rating_percent}%] {title}" if rating_percent else title
    
    return {
        'id': item.get('id'),
        'title': display_title,
        'clean_title': raw_title,
        'year': year,
        'url': '',
        'img': img,
        'backdrop_path': backdrop_img,
        'info': default_info or ('Seriál' if is_show else 'Film'),
        'plot': overview,
        'media_type': 'tv' if is_show else 'movie',
        'type': 'show' if is_show else 'movie',
        'vote_average': rating_raw
    }

def get_tv_tips(day_offset=0):
    cache_key = f"tv_tips_{day_offset}"
    cached = get_cached_tmdb(cache_key)
    if cached is not None:
        return cached

    xbmc.log(f"StreamContinuum: Loading TV tips (Trending) from TMDb", xbmc.LOGINFO)
    url_template = "https://api.themoviedb.org/3/trending/all/day?api_key={api_key}&language=cs-CZ"
    
    try:
        res = make_tmdb_request(url_template)
        if res and res.status_code == 200:
            data = res.json()
            results = data.get('results', [])
            items = []
            for item in results:
                media_type = item.get('media_type', 'movie')
                if media_type not in ('movie', 'tv'):
                    continue
                info_label = 'Televizní tip (Seriál)' if media_type == 'tv' else 'Televizní tip (Film)'
                formatted = _format_item(item, media_type, info_label)
                if formatted:
                    items.append(formatted)
            set_cached_tmdb(cache_key, items, 6 * 3600)
            return items
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching TV Tips from TMDb: {e}", xbmc.LOGERROR)
    
    return []

def get_vod_premieres(page=1):
    cache_key = f"vod_premieres_{page}"
    cached = get_cached_tmdb(cache_key)
    if cached is not None:
        return cached

    xbmc.log(f"StreamContinuum: Loading VOD Premieres from TMDb (Page {page})", xbmc.LOGINFO)
    url_template = f"https://api.themoviedb.org/3/movie/now_playing?api_key={{api_key}}&language=cs-CZ&page={page}"
    
    try:
        res = make_tmdb_request(url_template)
        if res and res.status_code == 200:
            data = res.json()
            results = data.get('results', [])
            items = []
            for item in results:
                formatted = _format_item(item, 'movie', 'Kino / VOD Premiéra')
                if formatted:
                    items.append(formatted)
            set_cached_tmdb(cache_key, items, 6 * 3600)
            return items
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching VOD Premieres from TMDb: {e}", xbmc.LOGERROR)
        
    return []

def get_disk_premieres(month, year):
    cache_key = f"disk_premieres_{month}_{year}"
    cached = get_cached_tmdb(cache_key)
    if cached is not None:
        return cached

    xbmc.log(f"StreamContinuum: Loading upcoming novinky from TMDb", xbmc.LOGINFO)
    url_template = "https://api.themoviedb.org/3/movie/upcoming?api_key={api_key}&language=cs-CZ&page=1"
    
    try:
        res = make_tmdb_request(url_template)
        if res and res.status_code == 200:
            data = res.json()
            results = data.get('results', [])
            items = []
            for item in results:
                formatted = _format_item(item, 'movie', 'Novinka / Disk')
                if formatted:
                    items.append(formatted)
            set_cached_tmdb(cache_key, items, 12 * 3600)
            return items
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching Upcoming movies from TMDb: {e}", xbmc.LOGERROR)
        
    return []

def get_top_rated(media_type='movie', page=1):
    cache_key = f"top_rated_{media_type}_{page}"
    cached = get_cached_tmdb(cache_key)
    if cached is not None:
        return cached

    xbmc.log(f"StreamContinuum: Loading top rated {media_type} from TMDb (page {page})", xbmc.LOGINFO)
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    url_template = f"https://api.themoviedb.org/3/{endpoint}/top_rated?api_key={{api_key}}&language=cs-CZ&page={page}"
    
    try:
        res = make_tmdb_request(url_template)
        if res and res.status_code == 200:
            data = res.json()
            results = data.get('results', [])
            items = []
            for item in results:
                info_label = 'Top Seriál' if media_type == 'tv' else 'Top Film'
                formatted = _format_item(item, media_type, info_label)
                if formatted:
                    items.append(formatted)
            set_cached_tmdb(cache_key, items, 24 * 3600)
            return items
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error loading top rated {media_type}: {e}", xbmc.LOGERROR)
    return []

def get_discover_by_genre(media_type, genre_id, page=1):
    cache_key = f"discover_{media_type}_{genre_id}_{page}"
    cached = get_cached_tmdb(cache_key)
    if cached is not None:
        return cached

    xbmc.log(f"StreamContinuum: Discovering {media_type} for genre {genre_id} (page {page})", xbmc.LOGINFO)
    endpoint = 'movie' if media_type == 'movie' else 'tv'
    url_template = f"https://api.themoviedb.org/3/discover/{endpoint}?api_key={{api_key}}&language=cs-CZ&sort_by=popularity.desc&with_genres={genre_id}&page={page}"
    
    try:
        res = make_tmdb_request(url_template)
        if res and res.status_code == 200:
            data = res.json()
            results = data.get('results', [])
            items = []
            for item in results:
                info_label = 'Seriál' if media_type == 'tv' else 'Film'
                formatted = _format_item(item, media_type, info_label)
                if formatted:
                    items.append(formatted)
            set_cached_tmdb(cache_key, items, 24 * 3600)
            return items
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error discovering genre {genre_id}: {e}", xbmc.LOGERROR)
    return []

def get_random_tips():
    xbmc.log(f"StreamContinuum: Fetching random curated tips from TMDb", xbmc.LOGINFO)
    items = []
    random_pages_movies = random.sample(range(1, 15), 2)
    random_pages_tv = random.sample(range(1, 10), 1)
    
    for p in random_pages_movies:
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={{api_key}}&language=cs-CZ&sort_by=vote_average.desc&vote_count.gte=300&page={p}"
        res = make_tmdb_request(url)
        if res and res.status_code == 200:
            for it in res.json().get('results', []):
                formatted = _format_item(it, 'movie', 'Doporučený film')
                if formatted:
                    items.append(formatted)
                    
    for p in random_pages_tv:
        url = f"https://api.themoviedb.org/3/discover/tv?api_key={{api_key}}&language=cs-CZ&sort_by=vote_average.desc&vote_count.gte=150&page={p}"
        res = make_tmdb_request(url)
        if res and res.status_code == 200:
            for it in res.json().get('results', []):
                formatted = _format_item(it, 'tv', 'Doporučený seriál')
                if formatted:
                    items.append(formatted)
                    
    random.shuffle(items)
    return items[:25]

def search_tmdb(query):
    if not query:
        return []
    clean_q = str(query).strip().lower()
    cache_key = f"search_{clean_q}"
    cached = get_cached_tmdb(cache_key)
    if cached is not None:
        return cached

    xbmc.log(f"StreamContinuum: Searching TMDb for '{query}'", xbmc.LOGINFO)
    safe_query = urllib.parse.quote(str(query))
    url_template = f"https://api.themoviedb.org/3/search/multi?api_key={{api_key}}&language=cs-CZ&query={safe_query}&page=1"
    
    try:
        res = make_tmdb_request(url_template)
        if res and res.status_code == 200:
            data = res.json()
            results = data.get('results', [])
            items = []
            for item in results:
                media_type = item.get('media_type')
                if media_type not in ('movie', 'tv'):
                    continue
                info_label = 'Film' if media_type == 'movie' else 'Seriál'
                formatted = _format_item(item, media_type, info_label)
                if formatted:
                    items.append(formatted)
            set_cached_tmdb(cache_key, items, 7 * 86400)
            return items
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error searching TMDb: {e}", xbmc.LOGERROR)
    
    return []

def get_show_seasons(tmdb_id):
    if not tmdb_id or str(tmdb_id).strip().lower() in ('none', '', '0'):
        return None
    cache_key = f"tv_{tmdb_id}"
    cached = get_cached_tmdb(cache_key)
    if cached is not None:
        return cached

    xbmc.log(f"StreamContinuum: Fetching show details and seasons for TMDb ID '{tmdb_id}'", xbmc.LOGINFO)
    url_template = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={{api_key}}&language=cs-CZ"
    try:
        res = make_tmdb_request(url_template)
        if res and res.status_code == 200:
            data = res.json()
            title = data.get('name') or data.get('original_name', '')
            if _has_non_latin(title) and data.get('original_name') and not _has_non_latin(data.get('original_name')):
                title = data.get('original_name')
            title = _sanitize_string(title)
            overview = data.get('overview', '')
            if not overview:
                try:
                    res_en = make_tmdb_request(f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={{api_key}}&language=en-US")
                    if res_en and res_en.status_code == 200:
                        overview = res_en.json().get('overview', '')
                except Exception:
                    pass
            poster_path = data.get('poster_path')
            backdrop_path = data.get('backdrop_path')
            poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ''
            fanart = f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else ''
            
            ep_runtimes = data.get('episode_run_time', [])
            runtime = ep_runtimes[0] if (ep_runtimes and isinstance(ep_runtimes, list) and ep_runtimes[0]) else 0
            if not runtime:
                last_ep = data.get('last_episode_to_air') or {}
                if isinstance(last_ep, dict) and last_ep.get('runtime'):
                    runtime = last_ep.get('runtime', 0)
            if not runtime:
                next_ep = data.get('next_episode_to_air') or {}
                if isinstance(next_ep, dict) and next_ep.get('runtime'):
                    runtime = next_ep.get('runtime', 0)
            genres = [g.get('name') for g in data.get('genres', []) if g.get('name')]
            rating = data.get('vote_average', 0)
            year_str = _extract_year(data, 'first_air_date')
            try:
                year = int(year_str) if year_str and year_str.isdigit() else None
            except (ValueError, TypeError):
                year = None
            status = data.get('status', '')
            
            raw_seasons = data.get('seasons', [])
            seasons = []
            for s in raw_seasons:
                s_poster = f"https://image.tmdb.org/t/p/w500{s.get('poster_path')}" if s.get('poster_path') else poster
                seasons.append({
                    'season_number': s.get('season_number', 0),
                    'name': _sanitize_string(s.get('name', '')),
                    'overview': s.get('overview', ''),
                    'episode_count': s.get('episode_count', 0),
                    'poster': s_poster,
                    'air_date': s.get('air_date', ''),
                    'rating': s.get('vote_average', 0)
                })
            result = {
                'id': data.get('id'),
                'title': title,
                'year': year,
                'overview': overview,
                'runtime': runtime,
                'genres': genres,
                'rating': rating,
                'poster': poster,
                'fanart': fanart,
                'status': status,
                'first_air_date': data.get('first_air_date', ''),
                'seasons': seasons
            }
            status_lower = str(status or '').strip().lower()
            ttl = (30 * 86400) if status_lower in ('ended', 'canceled', 'ukončeno') else (24 * 86400)
            set_cached_tmdb(cache_key, result, ttl)
            return result
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching TMDb show details for ID {tmdb_id}: {e}", xbmc.LOGERROR)
    return None

def get_movie_details(tmdb_id):
    if not tmdb_id or str(tmdb_id).strip().lower() in ('none', '', '0'):
        return None
    cache_key = f"movie_{tmdb_id}"
    cached = get_cached_tmdb(cache_key)
    if cached is not None:
        return cached

    xbmc.log(f"StreamContinuum: Fetching movie details for TMDb ID '{tmdb_id}'", xbmc.LOGINFO)
    url_template = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={{api_key}}&language=cs-CZ"
    try:
        res = make_tmdb_request(url_template)
        if res and res.status_code == 200:
            data = res.json()
            title = data.get('title') or data.get('original_title', '')
            if _has_non_latin(title) and data.get('original_title') and not _has_non_latin(data.get('original_title')):
                title = data.get('original_title')
            title = _sanitize_string(title)
            overview = data.get('overview', '')
            if not overview:
                try:
                    res_en = make_tmdb_request(f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={{api_key}}&language=en-US")
                    if res_en and res_en.status_code == 200:
                        overview = res_en.json().get('overview', '')
                except Exception:
                    pass
            poster_path = data.get('poster_path')
            backdrop_path = data.get('backdrop_path')
            poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ''
            fanart = f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else ''
            runtime = data.get('runtime', 0) or 0
            genres = [g.get('name') for g in data.get('genres', []) if g.get('name')]
            rating = data.get('vote_average', 0)
            year_str = _extract_year(data, 'release_date')
            try:
                year = int(year_str) if year_str and year_str.isdigit() else None
            except (ValueError, TypeError):
                year = None
            result = {
                'id': data.get('id'),
                'title': title,
                'clean_title': _extract_title(data, 'movie'),
                'year': year,
                'overview': overview,
                'plot': overview,
                'runtime': runtime,
                'genres': genres,
                'rating': rating,
                'poster': poster,
                'fanart': fanart,
                'media_type': 'movie',
                'type': 'movie'
            }
            set_cached_tmdb(cache_key, result, 30 * 86400)
            return result
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching movie details for ID {tmdb_id}: {e}", xbmc.LOGERROR)
    return None

def get_season_episodes(tmdb_id, season_number):
    if not tmdb_id or str(tmdb_id).strip().lower() in ('none', '', '0'):
        return []
    cache_key = f"tv_s_{tmdb_id}_{season_number}"
    cached = get_cached_tmdb(cache_key)
    if cached is not None:
        return cached

    xbmc.log(f"StreamContinuum: Fetching episodes for TMDb ID '{tmdb_id}', season {season_number}", xbmc.LOGINFO)
    url_template = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_number}?api_key={{api_key}}&language=cs-CZ"
    try:
        res = make_tmdb_request(url_template)
        if res and res.status_code == 200:
            data = res.json()
            raw_episodes = data.get('episodes', [])
            
            # Zjistit, zda v této řadě existuje alespoň jedna epizoda s nenulovým runtime
            known_runtime = 0
            for ep in raw_episodes:
                r_val = ep.get('runtime')
                if r_val and isinstance(r_val, (int, float)) and r_val > 0:
                    known_runtime = int(r_val)
                    break
                    
            episodes = []
            today_str = datetime.date.today().isoformat()
            all_aired = True if raw_episodes else False

            for ep in raw_episodes:
                still_path = ep.get('still_path')
                still = f"https://image.tmdb.org/t/p/w500{still_path}" if still_path else ''
                ep_name = ep.get('name', '')
                if _has_non_latin(ep_name):
                    ep_name = f"Episode {ep.get('episode_number', 0)}"
                ep_name = _sanitize_string(ep_name)
                
                ep_rt = ep.get('runtime')
                try:
                    ep_rt = int(ep_rt) if ep_rt is not None else 0
                except (ValueError, TypeError):
                    ep_rt = 0
                if ep_rt <= 0 and known_runtime > 0:
                    ep_rt = known_runtime

                air_date_val = ep.get('air_date', '') or ''
                if not air_date_val or air_date_val > today_str:
                    all_aired = False

                episodes.append({
                    'episode_number': ep.get('episode_number', 0),
                    'season_number': ep.get('season_number', season_number),
                    'name': ep_name,
                    'overview': ep.get('overview', ''),
                    'runtime': ep_rt,
                    'still': still,
                    'rating': ep.get('vote_average', 0),
                    'air_date': air_date_val
                })

            ttl = (30 * 86400) if all_aired else (24 * 86400)
            set_cached_tmdb(cache_key, episodes, ttl)
            return episodes
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching TMDb season episodes for ID {tmdb_id}, S{season_number}: {e}", xbmc.LOGERROR)
    return []
