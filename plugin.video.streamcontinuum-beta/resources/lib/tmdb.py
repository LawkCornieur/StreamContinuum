# -*- coding: utf-8 -*-
import os
import json
import time
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
            return items
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching TV Tips from TMDb: {e}", xbmc.LOGERROR)
    
    return []

def get_vod_premieres(page=1):
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
            return items
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching VOD Premieres from TMDb: {e}", xbmc.LOGERROR)
        
    return []

def get_disk_premieres(month, year):
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
            return items
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching Upcoming movies from TMDb: {e}", xbmc.LOGERROR)
        
    return []

def get_top_rated(media_type='movie', page=1):
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
            return items
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error loading top rated {media_type}: {e}", xbmc.LOGERROR)
    return []

def get_discover_by_genre(media_type, genre_id, page=1):
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
            return items
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error searching TMDb: {e}", xbmc.LOGERROR)
    
    return []

def get_show_seasons(tmdb_id):
    if not tmdb_id or str(tmdb_id).strip().lower() in ('none', '', '0'):
        return None
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
            return {
                'id': data.get('id'),
                'title': title,
                'overview': overview,
                'poster': poster,
                'fanart': fanart,
                'seasons': seasons
            }
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching TMDb show details for ID {tmdb_id}: {e}", xbmc.LOGERROR)
    return None

def get_season_episodes(tmdb_id, season_number):
    if not tmdb_id or str(tmdb_id).strip().lower() in ('none', '', '0'):
        return []
    xbmc.log(f"StreamContinuum: Fetching episodes for TMDb ID '{tmdb_id}', season {season_number}", xbmc.LOGINFO)
    url_template = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_number}?api_key={{api_key}}&language=cs-CZ"
    try:
        res = make_tmdb_request(url_template)
        if res and res.status_code == 200:
            data = res.json()
            raw_episodes = data.get('episodes', [])
            episodes = []
            for ep in raw_episodes:
                still_path = ep.get('still_path')
                still = f"https://image.tmdb.org/t/p/w500{still_path}" if still_path else ''
                ep_name = ep.get('name', '')
                if _has_non_latin(ep_name):
                    ep_name = f"Episode {ep.get('episode_number', 0)}"
                ep_name = _sanitize_string(ep_name)
                episodes.append({
                    'episode_number': ep.get('episode_number', 0),
                    'season_number': ep.get('season_number', season_number),
                    'name': ep_name,
                    'overview': ep.get('overview', ''),
                    'runtime': ep.get('runtime', 0),
                    'still': still,
                    'rating': ep.get('vote_average', 0),
                    'air_date': ep.get('air_date', '')
                })
            return episodes
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching TMDb season episodes for ID {tmdb_id}, S{season_number}: {e}", xbmc.LOGERROR)
    return []
