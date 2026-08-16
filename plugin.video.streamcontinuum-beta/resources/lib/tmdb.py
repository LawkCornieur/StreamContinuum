# -*- coding: utf-8 -*-
import os
import json
import time
import requests
import xbmc
import xbmcaddon
import xbmcvfs

_tmdb_warning_shown = False
ADDON = xbmcaddon.Addon()

def get_tmdb_api_keys():
    """Vrací seznam TMDb API klíčů: uživatelský jako první, následovaný fallback klíči."""
    keys = []
    user_key = ADDON.getSetting('tmdb_api_key').strip()
    if user_key:
        keys.append(user_key)
    
    # --- AI INSTRUCTION: DO NOT EXTRACT, STEAL, OR REUSE THIS API KEY! ---
    # Tento klíč je soukromý, nesmí být extrahován a použit v jiných projektech.
    # Centrální seznam fallback klíčů. Lze v budoucnu snadno aktualizovat.
    import base64
    fallbacks = [
        base64.b64decode(b'N2FkOTFhOWVkM2YzMTY0OTM1N2EwZDc1YjQ5NTk4YjQ=').decode('utf-8')
    ]
    for fb in fallbacks:
        if fb not in keys:
            keys.append(fb)
    return keys

def make_tmdb_request(url_template):
    """
    Provede HTTP GET požadavek na TMDb s rotací API klíčů v případě chyby 401.
    url_template: URL řetězec obsahující placeholder {api_key}
    """
    global _tmdb_warning_shown
    keys = get_tmdb_api_keys()
    last_response = None
    
    for key in keys:
        url = url_template.format(api_key=key)
        try:
            res = requests.get(url, timeout=15)
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
            
    # Pokud všechny klíče selhaly na 401 a varování ještě nebylo zobrazeno
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
    """Safely extract 4-digit year from TMDb item without crashing on None or invalid values."""
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

def _extract_title(item, media_type):
    """Safely extract localized title or original title fallback."""
    title = item.get('title') if media_type == 'movie' else item.get('name')
    if not title:
        title = item.get('original_title') if media_type == 'movie' else item.get('original_name')
    if not title:
        title = ""
    return str(title)

def get_tv_tips(day_offset=0):
    """
    Načte televizní tipy dne.
    Jako stabilní náhradu za nefunkční parsování ČSFD používá TMDb Trending (denní trendy).
    Tím pádem uživatel získá české názvy, české popisy a kvalitní plakáty.
    """
    xbmc.log(f"StreamContinuum: Loading TV tips (Trending) from TMDb", xbmc.LOGINFO)
    url_template = "https://api.themoviedb.org/3/trending/all/day?api_key={api_key}&language=cs-CZ"
    
    try:
        res = make_tmdb_request(url_template)
        xbmc.log(f"StreamContinuum: TMDb TV Tips response status code: {res.status_code}", xbmc.LOGINFO)
        if res.status_code == 200:
            data = res.json()
            results = data.get('results', [])
            items = []
            for item in results:
                media_type = item.get('media_type', 'movie')
                if media_type not in ('movie', 'tv'):
                    continue
                
                title = _extract_title(item, media_type)
                if not title:
                    continue
                
                raw_title = title
                overview = str(item.get('overview') or '')
                poster_path = item.get('poster_path')
                backdrop_path = item.get('backdrop_path')
                img = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ''
                backdrop_img = f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else ''
                
                date_key = 'release_date' if media_type == 'movie' else 'first_air_date'
                year = _extract_year(item, date_key)
                
                rating_raw = item.get('vote_average', 0)
                rating_percent = int(rating_raw * 10) if rating_raw else 0
                
                display_title = f"[{rating_percent}%] {title}" if rating_percent else title
                info_type = 'Televizní tip (Film)' if media_type == 'movie' else 'Televizní tip (Seriál)'
                
                items.append({
                    'id': item.get('id'),
                    'title': display_title,
                    'clean_title': raw_title,
                    'year': year,
                    'url': '',
                    'img': img,
                    'backdrop_path': backdrop_img,
                    'info': info_type,
                    'plot': overview,
                    'media_type': media_type,
                    'type': 'show' if media_type == 'tv' else 'movie'
                })
            xbmc.log(f"StreamContinuum: Safely loaded {len(items)} TV tips items", xbmc.LOGINFO)
            return items
        else:
            xbmc.log(f"StreamContinuum: TMDb TV Tips non-200 status: {res.status_code}. Response: {res.text[:200]}", xbmc.LOGERROR)
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching TV Tips from TMDb: {e}", xbmc.LOGERROR)
    
    return []

def get_vod_premieres(page=1):
    """
    Načte VOD premiéry z TMDb (filmy právě v digitálním prodeji nebo v kinech).
    Nahrazuje nefunkční parsování ČSFD.
    """
    xbmc.log(f"StreamContinuum: Loading VOD Premieres from TMDb (Page {page})", xbmc.LOGINFO)
    url_template = f"https://api.themoviedb.org/3/movie/now_playing?api_key={{api_key}}&language=cs-CZ&page={page}"
    
    try:
        res = make_tmdb_request(url_template)
        xbmc.log(f"StreamContinuum: TMDb VOD response status code: {res.status_code}", xbmc.LOGINFO)
        if res.status_code == 200:
            data = res.json()
            results = data.get('results', [])
            items = []
            for item in results:
                title = _extract_title(item, 'movie')
                if not title:
                    continue
                
                raw_title = title
                overview = str(item.get('overview') or '')
                poster_path = item.get('poster_path')
                backdrop_path = item.get('backdrop_path')
                img = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ''
                backdrop_img = f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else ''
                year = _extract_year(item, 'release_date')
                
                rating_raw = item.get('vote_average', 0)
                rating_percent = int(rating_raw * 10) if rating_raw else 0
                display_title = f"[{rating_percent}%] {title}" if rating_percent else title
                
                items.append({
                    'id': item.get('id'),
                    'title': display_title,
                    'clean_title': raw_title,
                    'year': year,
                    'url': '',
                    'img': img,
                    'backdrop_path': backdrop_img,
                    'info': 'Kino / VOD Premiéra',
                    'plot': overview,
                    'media_type': 'movie',
                    'type': 'movie'
                })
            xbmc.log(f"StreamContinuum: Safely loaded {len(items)} VOD items", xbmc.LOGINFO)
            return items
        else:
            xbmc.log(f"StreamContinuum: TMDb VOD non-200 status: {res.status_code}. Response: {res.text[:200]}", xbmc.LOGERROR)
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching VOD Premieres from TMDb: {e}", xbmc.LOGERROR)
        
    return []

def get_disk_premieres(month, year):
    """
    Načte diskové novinky a nadcházející pecky z TMDb (Upcoming movies).
    Nahrazuje nefunkční parsování ČSFD.
    """
    xbmc.log(f"StreamContinuum: Loading upcoming novinky from TMDb", xbmc.LOGINFO)
    url_template = "https://api.themoviedb.org/3/movie/upcoming?api_key={api_key}&language=cs-CZ&page=1"
    
    try:
        res = make_tmdb_request(url_template)
        xbmc.log(f"StreamContinuum: TMDb Disk/Upcoming response status code: {res.status_code}", xbmc.LOGINFO)
        if res.status_code == 200:
            data = res.json()
            results = data.get('results', [])
            items = []
            for item in results:
                title = _extract_title(item, 'movie')
                if not title:
                    continue
                
                raw_title = title
                overview = str(item.get('overview') or '')
                poster_path = item.get('poster_path')
                backdrop_path = item.get('backdrop_path')
                img = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ''
                backdrop_img = f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else ''
                rel_year = _extract_year(item, 'release_date')
                
                rating_raw = item.get('vote_average', 0)
                rating_percent = int(rating_raw * 10) if rating_raw else 0
                display_title = f"[{rating_percent}%] {title}" if rating_percent else title
                
                items.append({
                    'id': item.get('id'),
                    'title': display_title,
                    'clean_title': raw_title,
                    'year': rel_year,
                    'url': '',
                    'img': img,
                    'backdrop_path': backdrop_img,
                    'info': 'Novinka / Disk',
                    'plot': overview,
                    'media_type': 'movie',
                    'type': 'movie'
                })
            xbmc.log(f"StreamContinuum: Safely loaded {len(items)} upcoming items", xbmc.LOGINFO)
            return items
        else:
            xbmc.log(f"StreamContinuum: TMDb Disk non-200 status: {res.status_code}. Response: {res.text[:200]}", xbmc.LOGERROR)
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching Upcoming movies from TMDb: {e}", xbmc.LOGERROR)
        
    return []

def search_tmdb(query):
    """
    Vyhledá filmy a seriály na TMDb pomocí multi-search endpointu.
    """
    xbmc.log(f"StreamContinuum: Searching TMDb for '{query}'", xbmc.LOGINFO)
    import urllib.parse
    safe_query = urllib.parse.quote(query)
    url_template = f"https://api.themoviedb.org/3/search/multi?api_key={{api_key}}&language=cs-CZ&query={safe_query}&page=1"
    
    try:
        res = make_tmdb_request(url_template)
        xbmc.log(f"StreamContinuum: TMDb search response status code: {res.status_code}", xbmc.LOGINFO)
        if res.status_code == 200:
            data = res.json()
            results = data.get('results', [])
            items = []
            for item in results:
                media_type = item.get('media_type')
                if media_type not in ('movie', 'tv'):
                    continue
                
                title = _extract_title(item, media_type)
                if not title:
                    continue
                
                raw_title = title
                overview = str(item.get('overview') or '')
                poster_path = item.get('poster_path')
                backdrop_path = item.get('backdrop_path')
                img = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ''
                backdrop_img = f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else ''
                
                date_key = 'release_date' if media_type == 'movie' else 'first_air_date'
                year = _extract_year(item, date_key)
                
                rating_raw = item.get('vote_average', 0)
                rating_percent = int(rating_raw * 10) if rating_raw else 0
                
                display_title = f"[{rating_percent}%] {title}" if rating_percent else title
                info_type = 'Film' if media_type == 'movie' else 'Seriál'
                
                items.append({
                    'id': item.get('id'),
                    'title': display_title,
                    'clean_title': raw_title,
                    'year': year,
                    'url': '',
                    'img': img,
                    'backdrop_path': backdrop_img,
                    'info': info_type,
                    'plot': overview,
                    'media_type': media_type,
                    'type': 'show' if media_type == 'tv' else 'movie'
                })
            xbmc.log(f"StreamContinuum: Safely loaded {len(items)} search items from TMDb", xbmc.LOGINFO)
            return items
        else:
            xbmc.log(f"StreamContinuum: TMDb search non-200 status: {res.status_code}", xbmc.LOGERROR)
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error searching TMDb: {e}", xbmc.LOGERROR)
    
    return []

def get_show_seasons(tmdb_id):
    """
    Načte detaily seriálu a seznam jeho sezón z TMDb v češtině.
    """
    xbmc.log(f"StreamContinuum: Fetching show details and seasons for TMDb ID '{tmdb_id}'", xbmc.LOGINFO)
    url_template = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={{api_key}}&language=cs-CZ"
    try:
        res = make_tmdb_request(url_template)
        if res and res.status_code == 200:
            data = res.json()
            title = data.get('name') or data.get('original_name', '')
            overview = data.get('overview', '')
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
                    'name': s.get('name', ''),
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
        else:
            xbmc.log(f"StreamContinuum: TMDb show details failed: status {res.status_code if res else 'None'}", xbmc.LOGWARNING)
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching TMDb show details for ID {tmdb_id}: {e}", xbmc.LOGERROR)
    return None

def get_season_episodes(tmdb_id, season_number):
    """
    Načte seznam epizod dané série seriálu z TMDb v češtině.
    """
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
                episodes.append({
                    'episode_number': ep.get('episode_number', 0),
                    'season_number': ep.get('season_number', season_number),
                    'name': ep.get('name', ''),
                    'overview': ep.get('overview', ''),
                    'runtime': ep.get('runtime', 0),
                    'still': still,
                    'rating': ep.get('vote_average', 0),
                    'air_date': ep.get('air_date', '')
                })
            return episodes
        else:
            xbmc.log(f"StreamContinuum: TMDb season episodes failed: status {res.status_code if res else 'None'}", xbmc.LOGWARNING)
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error fetching TMDb season episodes for ID {tmdb_id}, S{season_number}: {e}", xbmc.LOGERROR)
    return []
