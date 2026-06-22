import os
import json
import re
import time
import requests
from xml.etree import ElementTree
import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
PROFILE_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
CACHE_DIR = os.path.join(PROFILE_DIR, 'csfd_cache')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'cs,sk;q=0.9,en;q=0.8'
}

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
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        if response.status_code == 200:
            items = parse_articles(response.text)
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(items, f, ensure_ascii=False, indent=4)
            except Exception as e:
                xbmc.log(f"StreamContinuum: Error writing cache {cache_filename}: {e}", xbmc.LOGWARNING)
            return items
        else:
            xbmc.log(f"StreamContinuum: ČSFD HTTP error {response.status_code} for {url}", xbmc.LOGERROR)
    except Exception as e:
        xbmc.log(f"StreamContinuum: ČSFD fetch error: {e}", xbmc.LOGERROR)
        
    return []

def parse_articles(html):
    # Find all articles
    article_blocks = re.findall(r'<article\b[^>]*>(.*?)</article>', html, re.DOTALL)
    items = []
    for block in article_blocks:
        # Title and URL
        title_match = re.search(r'<a href="([^"]+)"[^>]*class="[^"]*film-title-name[^"]*">([^<]+)</a>', block)
        if not title_match:
            title_match = re.search(r'<h3>.*?<a href="([^"]+)"[^>]*>([^<]+)</a>', block, re.DOTALL)
            
        if not title_match:
            continue
            
        url = title_match.group(1).strip()
        title = title_match.group(2).strip()
        
        # Image
        img_match = re.search(r'<img [^>]*src="([^"]+)"', block)
        img = img_match.group(1).strip() if img_match else ""
        if img.startswith('//'):
            img = 'https:' + img
            
        # Year
        year_match = re.search(r'<span class="film-title-info">.*?<span class="info">(\d{4})</span>', block)
        year = year_match.group(1).strip() if year_match else ""
        
        # Genres / Country
        genres_match = re.search(r'<p class="film-origins-genres">(.*?)</p>', block, re.DOTALL)
        genres = ""
        if genres_match:
            genres = re.sub(r'<[^>]*>', '', genres_match.group(1)).replace('\n', ' ').strip()
            genres = re.sub(r'\s+', ' ', genres)
            
        # Description
        desc_match = re.search(r'<p class="p-tvtips-2row[^"]*">(.*?)</p>', block, re.DOTALL)
        desc = ""
        if desc_match:
            desc = re.sub(r'<[^>]*>', '', desc_match.group(1)).replace('\n', ' ').strip()
            desc = re.sub(r'\s+', ' ', desc)
            
        # Creator info
        creators_blocks = re.findall(r'<p class="film-creators">(.*?)</p>', block, re.DOTALL)
        creators = ""
        if creators_blocks:
            cleaned_blocks = [re.sub(r'<[^>]*>', '', cb).strip() for cb in creators_blocks]
            creators = " | ".join(cleaned_blocks)
            
        # Combine creators into description
        if not desc and creators:
            desc = creators
        elif creators:
            desc += f"\n\n{creators}"
            
        # Rating
        rating_match = re.search(r'<span class="rating-average">([^<]+)</span>', block)
        rating = rating_match.group(1).strip() if rating_match else ""
        raw_title = title
        if rating:
            title = f"[{rating}] {title}"
            
        # Differentiate Movie vs Show
        is_show = False
        if "seriál" in genres.lower() or "epizod" in genres.lower() or "seriál" in block.lower():
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
