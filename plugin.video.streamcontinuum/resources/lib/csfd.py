import os
import json
import re
import time
import requests
from xml.etree import ElementTree
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
PROFILE_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
CACHE_DIR = os.path.join(PROFILE_DIR, 'csfd_cache')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'cs,sk;q=0.9,en;q=0.8'
}

def fetch_url(url):
    ssl_verify = ADDON.getSettingBool('ssl_verify') if hasattr(ADDON, 'getSettingBool') else (ADDON.getSetting('ssl_verify') != 'false')
    if not ssl_verify:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    response = requests.get(url, headers=HEADERS, timeout=30, verify=ssl_verify)
    return response

def get_cached_or_fetch(url, cache_filename, ttl_seconds=21600):
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        
    cache_path = os.path.join(CACHE_DIR, cache_filename)
    
    # Try reading from cache
    if os.path.exists(cache_path):
        mtime = os.path.getmtime(cache_path)
        if time.time() - mtime < ttl_seconds:
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    if cached_data:
                        xbmc.log(f"StreamContinuum: Loaded ČSFD data from cache: {cache_filename}", xbmc.LOGINFO)
                        return cached_data
                    else:
                        xbmc.log(f"StreamContinuum: Cached data for {cache_filename} is empty, refetching...", xbmc.LOGINFO)
            except Exception as e:
                xbmc.log(f"StreamContinuum: Error reading cache {cache_filename}: {e}", xbmc.LOGWARNING)
                
    # Fetch from web
    xbmc.log(f"StreamContinuum: Fetching ČSFD page: {url}", xbmc.LOGINFO)

    try:
        response = fetch_url(url)
        if response and response.status_code == 200:
            items = parse_articles(response.text)
            if not items:
                xbmc.log(f"StreamContinuum: ČSFD parsing returned no items for {url}", xbmc.LOGWARNING)
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(items, f, ensure_ascii=False, indent=4)
            except Exception as e:
                xbmc.log(f"StreamContinuum: Error writing cache {cache_filename}: {e}", xbmc.LOGWARNING)
            return items
        else:
            xbmc.log(f"StreamContinuum: ČSFD HTTP error {response.status_code if response else 'None'} for {url}", xbmc.LOGERROR)
    except Exception as e:
        xbmc.log(f"StreamContinuum: ČSFD fetch error: {e}", xbmc.LOGERROR)

    return []

def parse_articles(html):
    # Primary pattern – old CSFD markup (any <article> tag)
    article_blocks = re.findall(r'<article.*?>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)

    # Fallback – current CSFD layout (any <div> with class containing "film")
    if not article_blocks:
        article_blocks = re.findall(r'<div[^>]*class="[^">]*film[^">]*"[^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)

    if not article_blocks:
        xbmc.log("StreamContinuum: ČSFD parsing: no article or film blocks found", xbmc.LOGWARNING)
        return []

    items = []
    for block in article_blocks:
        # Title + URL – try the specific class first, then a generic <a> fallback
        title_match = re.search(
            r'<a[^>]*class="[^"]*film-title-name[^"]*"[^>]*href="([^\"]+)"[^>]*>([^<]+)</a>',
            block)
        if not title_match:
            title_match = re.search(r'<a[^>]*href="([^\"]+)"[^>]*>([^<]+)</a>', block, re.DOTALL)
        if not title_match:
            continue
        url = title_match.group(1).strip()
        if url.startswith('/'):
            url = 'https://www.csfd.cz' + url
        title = title_match.group(2).strip()

        # Image
        img_match = re.search(r'<img[^>]*src="([^\"]+)"', block)
        img = img_match.group(1).strip() if img_match else ''
        if img.startswith('//'):
            img = 'https:' + img

        # Year
        year_match = re.search(r'<span class="film-title-info".*?<span class="info">(\d{4})</span>', block, re.DOTALL)
        year = year_match.group(1).strip() if year_match else ''

        # Genres / Country
        genres_match = re.search(r'<p class="film-origins-genres"[^>]*>(.*?)</p>', block, re.DOTALL)
        genres = ''
        if genres_match:
            genres = re.sub(r'<[^>]*>', '', genres_match.group(1)).replace('\n', ' ').strip()
            genres = re.sub(r'\s+', ' ', genres)

        # Description – TV‑tips specific, with fallback
        desc_match = re.search(r'<p class="p-tvtips-2row[^\"]*"(?:[^>]*?)>(.*?)</p>', block, re.DOTALL)
        if not desc_match:
            desc_match = re.search(r'<p class="film-description"(?:[^>]*?)>(.*?)</p>', block, re.DOTALL)
        desc = ''
        if desc_match:
            desc = re.sub(r'<[^>]*>', '', desc_match.group(1)).replace('\n', ' ').strip()
            desc = re.sub(r'\s+', ' ', desc)

        # Creator info
        creators_blocks = re.findall(r'<p class="film-creators"(?:[^>]*?)>(.*?)</p>', block, re.DOTALL)
        creators = ''
        if creators_blocks:
            cleaned = [re.sub(r'<[^>]*>', '', c).strip() for c in creators_blocks]
            creators = ' | '.join(cleaned)

        if not desc and creators:
            desc = creators
        elif creators:
            desc += f'\n\n{creators}'

        # Rating
        rating_match = re.search(r'<span class="rating-average">([^<]+)</span>', block)
        rating = rating_match.group(1).strip() if rating_match else ''
        raw_title = title
        if rating:
            title = f'[{rating}] {title}'

        # Show vs. movie detection
        is_show = False
        if 'seriál' in genres.lower() or 'epizod' in genres.lower() or 'seriál' in block.lower():
            is_show = True

        items.append({
            'title': title,
            'clean_title': raw_title,
            'year': year,
            'url': url,
            'img': img,
            'info': genres,
            'plot': desc,
            'type': 'show' if is_show else 'movie'
        })
    return items

def get_tv_tips(day_offset=0):
    url = f"https://www.csfd.cz/televize/?day={day_offset}"
    cache_name = f"tv_tips_{day_offset}.json"
    return get_cached_or_fetch(url, cache_name)

def get_vod_premieres(page=1):
    url = f"https://www.csfd.cz/vod/?page={page}"
    cache_name = f"vod_premieres_{page}.json"
    return get_cached_or_fetch(url, cache_name)

def get_disk_premieres(month, year):
    url = f"https://www.csfd.cz/disky/?year={year}&month={month}"
    cache_name = f"disky_{year}_{month}.json"
    return get_cached_or_fetch(url, cache_name)
