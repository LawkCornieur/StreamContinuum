import sys
import os
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib.parse
import re

# Add addon root and resources/lib to sys.path
ADDON_ROOT = os.path.dirname(__file__)
sys.path.append(ADDON_ROOT)
sys.path.append(os.path.join(ADDON_ROOT, 'resources', 'lib'))

import trakt
import webshare
try:
    import tmdb as tmdb_module
except Exception as _tmdb_e:
    xbmc.log(f"StreamContinuum: TMDb module import failed: {_tmdb_e}", xbmc.LOGWARNING)
    tmdb_module = None

ADDON = xbmcaddon.Addon()
try:
    HANDLE = int(sys.argv[1])
except (IndexError, ValueError):
    HANDLE = -1
ADDON_PATH = ADDON.getAddonInfo('path')
_trakt_cache = {}
_trakt_meta_cache = {}

def get_asset(name):
    if name in ['icon.png', 'fa.png']:
        return os.path.join(ADDON_PATH, 'resources', name)
    return os.path.join(ADDON_PATH, 'resources', 'media', name)

def get_trakt_localized(trakt_id, media_type, season_num=None, episode_num=None):
    global _trakt_meta_cache
    if not trakt_id:
        return {}

    if media_type == 'season' and season_num is not None:
        cache_key = f"{media_type}_{trakt_id}_S{season_num}"
    elif media_type == 'episode' and season_num is not None and episode_num is not None:
        cache_key = f"{media_type}_{trakt_id}_S{season_num}E{episode_num}"
    else:
        cache_key = f"{media_type}_{trakt_id}"

    if cache_key in _trakt_meta_cache:
        return _trakt_meta_cache[cache_key]

    try:
        result = trakt.get_localized_metadata(trakt_id, media_type, season_num, episode_num, id_type='trakt')
        if result:
            _trakt_meta_cache[cache_key] = result
            return result
    except Exception as e:
        xbmc.log(f"StreamContinuum: Trakt localized fetch error: {e}", xbmc.LOGWARNING)

    _trakt_meta_cache[cache_key] = {}
    return {}

def _make_media_list_item(label, year, plot, genres_str, rating, runtime_min, poster, fanart, media_type='movie'):
    list_item = xbmcgui.ListItem(label=label)
    art = {}
    if poster:
        art['poster'] = poster
        art['thumb'] = poster
        art['icon'] = poster
    else:
        art['icon'] = 'DefaultMovies.png' if media_type == 'movie' else 'DefaultTVShows.png'
        art['thumb'] = art['icon']
    art['fanart'] = fanart if fanart else get_asset('fa.png')
    list_item.setArt(art)
    info_tag = list_item.getVideoInfoTag()
    info_tag.setTitle(label)
    info_tag.setMediaType(media_type)
    if plot:
        info_tag.setPlot(str(plot))
    if year:
        try:
            info_tag.setYear(int(str(year)[:4]))
        except (ValueError, TypeError):
            pass
    if genres_str:
        genres_list = [g.strip() for g in str(genres_str).replace('/', ',').split(',') if g.strip()]
        if genres_list:
            info_tag.setGenres(genres_list)
    if rating:
        try:
            info_tag.setRating(float(rating))
        except (ValueError, TypeError):
            pass
    if runtime_min:
        try:
            info_tag.setDuration(int(runtime_min) * 60)
        except (ValueError, TypeError):
            pass
    return list_item

def list_categories():
    xbmc.log(f"StreamContinuum: list_categories started.", xbmc.LOGINFO)
    xbmcplugin.setPluginCategory(HANDLE, 'StreamContinuum')
    xbmcplugin.setContent(HANDLE, 'files')

    trakt_token = ADDON.getSetting('trakt_token')
    enable_trakt_menu = ADDON.getSettingBool('enable_trakt_menu')
    main_fanart = get_asset('fa.png')

    items = [
        (ADDON.getLocalizedString(30052), 'search', 'DefaultAddonsSearch.png', get_asset('fa-ws.png'), '#012a39'),
        (ADDON.getLocalizedString(30053), 'history', 'DefaultHistory.png', get_asset('fa-history.png'), '#cc9900')
    ]

    if trakt_token and enable_trakt_menu:
        items.append((ADDON.getLocalizedString(30119), 'trakt_menu', 'DefaultAddonVideo.png', get_asset('fa-trakt.png'), '#9f42c6'))

    items.append((ADDON.getLocalizedString(30099), 'tmdb_menu', 'DefaultAddonVideo.png', main_fanart, '#01b4e4'))
    items.append((ADDON.getLocalizedString(30054), 'settings', 'DefaultAddonSettings.png', main_fanart, None))
    
    item_count = 0

    for label, action, icon, fanart, color in items:
        try:
            url = f"{sys.argv[0]}?action={action}"
            display_label = f"[COLOR {color}]{label}[/COLOR]" if color else label
            list_item = xbmcgui.ListItem(label=display_label)
            list_item.setArt({'icon': icon, 'thumb': icon, 'fanart': fanart})
            
            success = xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
            if success:
                item_count += 1
            else:
                xbmc.log(f"StreamContinuum: Failed to add directory item '{label}' for action '{action}'. HANDLE={HANDLE}", xbmc.LOGERROR)
        except Exception as e:
            xbmc.log(f"StreamContinuum: Error adding directory item '{label}': {e}", xbmc.LOGERROR)
    
    if item_count == 0:
        xbmcgui.Dialog().notification("StreamContinuum", ADDON.getLocalizedString(30129), xbmcgui.NOTIFICATION_WARNING, 5000)
    
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True if item_count > 0 else False)
    xbmc.log(f"StreamContinuum: list_categories finished with {item_count} items.", xbmc.LOGINFO)

def trakt_menu():
    xbmcplugin.setPluginCategory(HANDLE, ADDON.getLocalizedString(30119))
    fanart = get_asset('fa-trakt.png')
    items = [
        (ADDON.getLocalizedString(30050), 'trakt_playback&offset=0', 'DefaultRecentlyAddedEpisodes.png'),
        (ADDON.getLocalizedString(30051), 'trakt_watchlist', 'DefaultWatchlist.png'),
        ('Katalog', 'trakt_discover_menu', 'DefaultAddonVideo.png'),
        (ADDON.getLocalizedString(30067), 'trakt_search_menu', 'DefaultAddonsSearch.png'),
    ]
    for label, action, icon in items:
        url = f"{sys.argv[0]}?action={action}"
        list_item = xbmcgui.ListItem(label=f"[COLOR #9f42c6]{label}[/COLOR]")
        list_item.setArt({'icon': icon, 'thumb': icon, 'fanart': fanart})
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)

def search(query=None):
    if not query:
        keyboard = xbmc.Keyboard('', ADDON.getLocalizedString(30057))
        keyboard.doModal()
        if keyboard.isConfirmed():
            query = keyboard.getText()
        else:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return

    if query:
        xbmcplugin.setPluginCategory(HANDLE, f"{ADDON.getLocalizedString(30052)}: {query}")
        results = webshare.search(query)
        if not results:
            xbmcgui.Dialog().notification("StreamContinuum", ADDON.getLocalizedString(30058), xbmcgui.NOTIFICATION_INFO, 3000)
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return
        
        optimize_results = ADDON.getSetting('optimize_results') == 'true'
        
        for item in results:
            url = f"{sys.argv[0]}?action=play&ident={item['ident']}&query={urllib.parse.quote(query)}&title={urllib.parse.quote(item['name'])}"
            size_mb = item['size'] / (1024 * 1024)
            size_str = f"{round(size_mb / 1024, 2)} GB" if size_mb > 1000 else f"{round(size_mb, 2)} MB"
            
            name = item['name']
            ext = ""
            if optimize_results:
                if '.' in name:
                    parts = name.rsplit('.', 1)
                    name = parts[0]
                    ext = parts[1]
                name = re.sub(r'[.,_\-]', ' ', name)
                name = re.sub(r'\s+', ' ', name).strip()
            
            list_item = xbmcgui.ListItem(label=name)
            info = {'title': name, 'plot': item['description'], 'size': item['size'], 'mediatype': 'video'}
            name_lower = item['name'].lower()
            res = '480'
            if '2160p' in name_lower or '4k' in name_lower:
                res = '2160'
            elif '1080p' in name_lower:
                res = '1080'
            elif '720p' in name_lower or 'hd' in name_lower:
                res = '720'
            elif '480p' in name_lower:
                res = '480'
            
            audio_info = []
            if 'cz' in name_lower or 'dabing' in name_lower:
                audio_info.append('CZ')
            if 'en' in name_lower or 'english' in name_lower:
                audio_info.append('EN')
            if 'sk' in name_lower or 'slovensky' in name_lower:
                audio_info.append('SK')
            
            if audio_info:
                info['plot'] = f"[COLOR orange][{', '.join(audio_info)}][/COLOR] " + info['plot']
            
            info['plot'] += f"\n\n[B]{ADDON.getLocalizedString(30059)}:[/B] {size_str}"
            if ext:
                info['plot'] += f"\n[B]{ADDON.getLocalizedString(30089)}:[/B] {ext.upper()}"
            info['plot'] += f"\n[B]{ADDON.getLocalizedString(30060)}:[/B] {res}p"
            
            info_tag = list_item.getVideoInfoTag()
            info_tag.setTitle(name)
            info_tag.setPlot(info['plot'])
            info_tag.setMediaType('video')
            
            video_stream = xbmc.VideoStreamDetail()
            video_stream.setWidth(int(res) * 16 // 9)
            video_stream.setHeight(int(res))
            if 'h265' in name_lower or 'hevc' in name_lower or 'x265' in name_lower:
                video_stream.setCodec('hevc')
            elif 'h264' in name_lower or 'x264' in name_lower:
                video_stream.setCodec('h264')
            info_tag.addVideoStream(video_stream)
            
            if item.get('img'):
                list_item.setArt({'thumb': item['img'], 'icon': item['img'], 'poster': item['img']})
            
            list_item.setProperty('IsPlayable', 'true')
            xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=False)
        
        xbmcplugin.endOfDirectory(HANDLE)

def play(ident, query=None):
    link = webshare.get_link(ident)
    if link:
        list_item = xbmcgui.ListItem(path=link)
        xbmcplugin.setResolvedUrl(HANDLE, True, list_item)
        if query:
            import history
            history.add_to_history(query)
            
        monitor = xbmc.Monitor()
        xbmc.sleep(2000)
        while not monitor.abortRequested() and (xbmc.getCondVisibility('Player.HasMedia') or xbmc.Player().isPlaying()):
            xbmc.sleep(1000)

        timeout = 50
        while timeout > 0 and xbmc.getCondVisibility('Window.IsActive(10025)'):
            xbmc.sleep(100)
            timeout -= 1
            
        xbmc.executebuiltin('Dialog.Close(all)')
        after = ADDON.getSetting('after_playback')
        safe_query = urllib.parse.quote(query) if query else ""
        xbmc.sleep(2000)

        if after == '0' and query:
            xbmc.executebuiltin(f'Container.Update({sys.argv[0]}?action=search&query={safe_query},replace)')
        elif after == '1':
            xbmc.executebuiltin(f'Container.Update({sys.argv[0]}?action=search,replace)')
        elif after == '3':
            xbmc.executebuiltin(f'Container.Update({sys.argv[0]}?action=history,replace)')
        elif after == '4' and query:
            xbmc.executebuiltin(f'Container.Update({sys.argv[0]}?action=search_prefill&query={safe_query},replace)')
    else:
        xbmcgui.Dialog().notification("StreamContinuum", ADDON.getLocalizedString(30061), xbmcgui.NOTIFICATION_ERROR, 3000)

def show_history():
    import history
    items = history.get_history()
    xbmcplugin.setPluginCategory(HANDLE, ADDON.getLocalizedString(30053))
    
    if not items:
        xbmcgui.Dialog().notification("StreamContinuum", ADDON.getLocalizedString(30062), xbmcgui.NOTIFICATION_INFO, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
        
    for item in items:
        query = item.get('query', '')
        title = item.get('title') or query
        year = item.get('year')
        plot = item.get('plot')
        genres = item.get('genres', [])
        rating = item.get('rating')
        runtime = item.get('runtime')
        poster = item.get('poster')
        fanart = item.get('fanart')
        media_type = item.get('media_type') or ('movie' if 'S00E00' not in query and re.search(r'\b(S\d{2}E\d{2}|\d{1}x\d{2})\b', query, re.IGNORECASE) is None else 'tvshow')
        
        label = f"{title} ({year})" if year else title
        if item.get('tmdb_id') and poster:
            list_item = _make_media_list_item(
                label=label, year=year, plot=plot, genres_str=', '.join(genres),
                rating=rating, runtime_min=runtime, poster=poster, fanart=fanart, media_type=media_type
            )
        else:
            list_item = xbmcgui.ListItem(label=label)
            list_item.setArt({'icon': 'DefaultHistory.png', 'thumb': 'DefaultHistory.png', 'fanart': get_asset('fa-history.png')})
        
        url = f"{sys.argv[0]}?action=history_menu&query={urllib.parse.quote(query)}"
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
        
    xbmcplugin.endOfDirectory(HANDLE)

def history_menu(query, title=None):
    xbmcplugin.setPluginCategory(HANDLE, f"{ADDON.getLocalizedString(30064)}: {query}")
    items = [
        (ADDON.getLocalizedString(30057), f'search&query={urllib.parse.quote(query)}', 'DefaultAddonsSearch.png'),
        (ADDON.getLocalizedString(30120), f'history_tmdb_identify_search&original_query={urllib.parse.quote(query)}', 'DefaultAddonVideo.png'),
        (ADDON.getLocalizedString(30065), f'history_edit&query={urllib.parse.quote(query)}', 'DefaultEdit.png'),
        (ADDON.getLocalizedString(30066), f'history_delete&query={urllib.parse.quote(query)}', 'DefaultDelete.png'),
        (ADDON.getLocalizedString(30067), f'trakt_search&query={urllib.parse.quote(query)}', 'DefaultAddonVideo.png'),
    ]
    
    series_pattern = re.compile(r'^(.*)\s+S(\d{2})E(\d{2})', re.IGNORECASE)
    match = series_pattern.match(query)
    if match:
        base_title = match.group(1).strip()
        season = int(match.group(2))
        episode = int(match.group(3))
        items.extend([
            (f'{ADDON.getLocalizedString(30068)} (E+{episode+1:02d})', f'search&query={urllib.parse.quote(f"{base_title} S{season:02d}E{episode+1:02d}")}', 'DefaultVideoEpisodes.png'),
            (f'{ADDON.getLocalizedString(30069)} (E-{episode-1:02d})', f'search&query={urllib.parse.quote(f"{base_title} S{season:02d}E{episode-1:02d}")}', 'DefaultVideoEpisodes.png') if episode > 1 else None,
            (f'{ADDON.getLocalizedString(30070)} (S{season+1:02d}E01)', f'search&query={urllib.parse.quote(f"{base_title} S{season+1:02d}E01")}', 'DefaultVideoEpisodes.png'),
            (f'{ADDON.getLocalizedString(30071)} (S{season-1:02d}E01)', f'search&query={urllib.parse.quote(f"{base_title} S{season-1:02d}E01")}', 'DefaultVideoEpisodes.png') if season > 1 else None,
        ])
    
    for label, action_params, icon in [i for i in items if i]:
        url = f"{sys.argv[0]}?action={action_params}"
        list_item = xbmcgui.ListItem(label=label)
        list_item.setArt({'icon': icon, 'thumb': icon})
        is_folder = 'search&query=' in action_params or 'trakt_search&query=' in action_params or 'history_tmdb_identify_search' in action_params
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=is_folder)
        
    xbmcplugin.endOfDirectory(HANDLE)

def trakt_search(query=None):
    if not query:
        keyboard = xbmc.Keyboard('', ADDON.getLocalizedString(30057))
        keyboard.doModal()
        if keyboard.isConfirmed():
            query = keyboard.getText()
        else:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return

    if query:
        xbmcplugin.setPluginCategory(HANDLE, f"Trakt.tv: {query}")
        results = trakt.search_trakt(query)
        if not results:
            xbmcgui.Dialog().notification("Trakt.tv", ADDON.getLocalizedString(30058), xbmcgui.NOTIFICATION_INFO, 3000)
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return

        for item in results:
            media_type = item.get('type')
            data = item.get(media_type, {})
            trakt_id = data.get('ids', {}).get('trakt')
            meta = get_trakt_localized(trakt_id, media_type) if trakt_id else {}
            
            title = meta.get('title') or data.get('title', '')
            year = meta.get('year') or data.get('year', '')
            overview = meta.get('overview') or data.get('overview', '')
            genres = meta.get('genres', []) or data.get('genres', [])
            rating = meta.get('rating') or data.get('rating', 0)
            runtime = meta.get('runtime') or data.get('runtime', 0)
            status = meta.get('status') or data.get('status', '')
            poster = meta.get('poster') or ('DefaultMovies.png' if media_type == 'movie' else 'DefaultTVShows.png')
            fanart = meta.get('fanart') or ''
            label = f"{title} ({year})" if year else title
            kodi_media_type = 'movie' if media_type == 'movie' else 'tvshow'
            genres_str = ', '.join(genres[:3]) if genres else ''

            plot_parts = []
            if overview:
                plot_parts.append(overview)
            if genres_str:
                plot_parts.append(f"[B]{ADDON.getLocalizedString(30114)}:[/B] {genres_str}")
            if runtime:
                unit = 'min/ep' if media_type == 'show' else 'min'
                plot_parts.append(f"[B]{ADDON.getLocalizedString(30115)}:[/B] {runtime} {unit}")
            if status:
                plot_parts.append(f"[B]{ADDON.getLocalizedString(30116)}:[/B] {status}")
            combined_plot = '\n'.join(plot_parts)

            list_item = _make_media_list_item(label, year, combined_plot, genres_str, rating, runtime, poster, fanart, kodi_media_type)
            cm = []
            if trakt_id:
                cm.append((ADDON.getLocalizedString(30072), f'RunPlugin({sys.argv[0]}?action=trakt_mark&type={media_type}&id={trakt_id}&watched=1)'))
                cm.append((ADDON.getLocalizedString(30073), f'RunPlugin({sys.argv[0]}?action=trakt_mark&type={media_type}&id={trakt_id}&watched=0)'))
            list_item.addContextMenuItems(cm)

            if media_type == 'movie':
                ws_query = f"{title} {year}".strip()
                url = f"{sys.argv[0]}?action=search&query={urllib.parse.quote(ws_query)}"
                xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
            else:
                url = (f"{sys.argv[0]}?action=show_seasons"
                       f"&show_title={urllib.parse.quote(title)}"
                       f"&trakt_id={trakt_id}"
                       f"&poster={urllib.parse.quote(poster)}"
                       f"&fanart={urllib.parse.quote(fanart)}")
                xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)

        xbmcplugin.endOfDirectory(HANDLE)

def show_changelog():
    changelog_path = os.path.join(ADDON_PATH, "changelog.txt")
    try:
        with open(changelog_path, 'r', encoding='utf-8') as f:
            changelog = f.read()
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error reading changelog: {e}", xbmc.LOGWARNING)
        changelog = "Changelog momentálně není k dispozici."
    xbmcgui.Dialog().textviewer(ADDON.getAddonInfo('name') + ' - Changelog', changelog)

def show_trakt_watchlist():
    xbmcplugin.setPluginCategory(HANDLE, ADDON.getLocalizedString(30051))
    items = trakt.get_watchlist()
    if not items:
        xbmcgui.Dialog().notification("StreamContinuum", ADDON.getLocalizedString(30074), xbmcgui.NOTIFICATION_INFO, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
        
    for item in items:
        media_type = item.get('type')
        meta_type = media_type 
        rating = 0
        runtime = 0
        genres_str = ''
        plot = ''
        poster = ''
        fanart = ''
        year = ''
        query = ''

        if media_type == 'movie':
            movie = item.get('movie')
            trakt_id = movie.get('ids', {}).get('trakt')
            meta = get_trakt_localized(trakt_id, 'movie') if trakt_id else {}
            title = meta.get('title') or movie.get('title')
            year = meta.get('year') or movie.get('year')
            query = f"{title} {year}" if year else title
            label = f"{title} ({year})" if year else title
            poster = meta.get('poster') or 'DefaultMovies.png'
            fanart = meta.get('fanart') or ''
            plot = meta.get('overview') or ''
            genres_str = ', '.join(meta.get('genres', [])) if meta.get('genres') else ''
            rating = meta.get('rating') or 0
            runtime = meta.get('runtime') or 0
        elif media_type == 'show':
            show = item.get('show')
            trakt_id = show.get('ids', {}).get('trakt')
            meta = get_trakt_localized(trakt_id, 'show') if trakt_id else {}
            title = meta.get('title') or show.get('title')
            year = meta.get('year') or show.get('year')
            query = title
            label = f"{title} ({year})" if year else title
            poster = meta.get('poster') or 'DefaultTVShows.png'
            fanart = meta.get('fanart') or ''
            plot = meta.get('overview') or ''
            genres_str = ', '.join(meta.get('genres', [])) if meta.get('genres') else ''
            rating = meta.get('rating') or 0
            runtime = meta.get('runtime') or 0
            meta_type = 'tvshow'
        elif media_type == 'episode':
            show = item.get('show')
            episode = item.get('episode')
            show_trakt_id = show.get('ids', {}).get('trakt')
            show_meta = get_trakt_localized(show_trakt_id, 'show') if show_trakt_id else {}
            episode_meta = get_trakt_localized(show_trakt_id, 'episode', season_num=episode.get('season'), episode_num=episode.get('number')) if show_trakt_id and episode.get('season') and episode.get('number') else {}
            show_title = show_meta.get('title') or show.get('title')
            show_year = show_meta.get('year') or show.get('year', '')
            ep_title_localized = episode_meta.get('title') or episode.get('title', ADDON.getLocalizedString(30108).format(episode.get('number', 0)))
            ep_overview_localized = episode_meta.get('overview') or episode.get('overview') or show_meta.get('overview') or ''
            label = f"{show_title} S{episode.get('season', 0):02d}E{episode.get('number', 0):02d} - {ep_title_localized}"
            query = f"{show_title} S{episode.get('season', 0):02d}E{episode.get('number', 0):02d}"
            year = show_year
            poster = show_meta.get('poster') or 'DefaultRecentlyAddedEpisodes.png'
            fanart = show_meta.get('fanart') or ''
            plot = ep_overview_localized
            genres_str = ', '.join(show_meta.get('genres', [])) if show_meta.get('genres') else ''
            rating = episode_meta.get('rating') or episode.get('rating') or show_meta.get('rating') or 0
            runtime = episode_meta.get('runtime') or episode.get('runtime') or show_meta.get('runtime') or 0
            meta_type = 'tvshow'
        else:
            continue
            
        url = f"{sys.argv[0]}?action=search_prefill&query={urllib.parse.quote(query)}"
        list_item = _make_media_list_item(label=label, year=year, plot=plot, genres_str=genres_str, rating=rating, runtime_min=runtime, poster=poster, fanart=fanart, media_type='movie' if meta_type == 'movie' else 'tvshow')
        cm = []
        trakt_item_id = item.get('movie', {}).get('ids', {}).get('trakt') if media_type == 'movie' else (item.get('episode', {}).get('ids', {}).get('trakt') if media_type == 'episode' else None)
        if trakt_item_id:
            cm.append((ADDON.getLocalizedString(30072), f'RunPlugin({sys.argv[0]}?action=trakt_mark&type={media_type}&id={trakt_item_id}&watched=1)'))
            cm.append((ADDON.getLocalizedString(30073), f'RunPlugin({sys.argv[0]}?action=trakt_mark&type={media_type}&id={trakt_item_id}&watched=0)'))
        list_item.addContextMenuItems(cm)
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
        
    xbmcplugin.endOfDirectory(HANDLE)

def show_trakt_playback(offset=0):
    offset = int(offset)
    PAGE_SIZE = 20
    xbmcplugin.setPluginCategory(HANDLE, ADDON.getLocalizedString(30050))
    playback_items = trakt.get_playback()
    progress_items = trakt.get_progress()
    combined_items = []
    seen_ids = set()
    
    for item in playback_items:
        media_type = item.get('type')
        trakt_id = item.get('movie', {}).get('ids', {}).get('trakt') if media_type == 'movie' else (item.get('episode', {}).get('ids', {}).get('trakt') if media_type == 'episode' else None)
        id_key = f"{media_type}_{trakt_id}"
        if trakt_id and id_key not in seen_ids:
            combined_items.append(item)
            seen_ids.add(id_key)
            
    for item in progress_items:
        episode = item.get('episode')
        trakt_id = episode.get('ids', {}).get('trakt')
        id_key = f"episode_{trakt_id}"
        if trakt_id and id_key not in seen_ids:
            combined_items.append(item)
            seen_ids.add(id_key)

    if not combined_items:
        xbmcgui.Dialog().notification("StreamContinuum", ADDON.getLocalizedString(30075), xbmcgui.NOTIFICATION_INFO, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
        
    page_items = combined_items[offset:offset + PAGE_SIZE]
    for item in page_items:
        media_type = item.get('type')
        meta_type = media_type
        rating = 0
        runtime = 0
        genres_str = ''
        plot = ''
        poster = ''
        fanart = ''
        year = ''
        query = ''
        
        if media_type == 'movie':
            movie = item.get('movie')
            trakt_id = movie.get('ids', {}).get('trakt')
            meta = get_trakt_localized(trakt_id, 'movie') if trakt_id else {}
            title = meta.get('title') or movie.get('title')
            year = meta.get('year') or movie.get('year')
            query = f"{title} {year}" if year else title
            label = f"{title} ({year})" if year else title
            poster = meta.get('poster') or 'DefaultMovies.png'
            fanart = meta.get('fanart') or ''
            plot = meta.get('overview') or ''
            genres_str = ', '.join(meta.get('genres', [])) if meta.get('genres') else ''
            rating = meta.get('rating') or 0
            runtime = meta.get('runtime') or 0
        elif media_type == 'episode':
            show = item.get('show')
            episode = item.get('episode')
            show_trakt_id = show.get('ids', {}).get('trakt')
            show_meta = get_trakt_localized(show_trakt_id, 'show') if show_trakt_id else {}
            episode_meta = get_trakt_localized(show_trakt_id, 'episode', season_num=episode.get('season'), episode_num=episode.get('number')) if show_trakt_id and episode.get('season') and episode.get('number') else {}
            show_title = show_meta.get('title') or show.get('title')
            show_year = show_meta.get('year') or show.get('year', '')
            ep_title_localized = episode_meta.get('title') or episode.get('title', ADDON.getLocalizedString(30108).format(episode.get('number', 0)))
            ep_overview_localized = episode_meta.get('overview') or episode.get('overview') or show_meta.get('overview') or ''
            label = f"{show_title} S{episode.get('season', 0):02d}E{episode.get('number', 0):02d} - {ep_title_localized}"
            query = f"{show_title} S{episode.get('season', 0):02d}E{episode.get('number', 0):02d}"
            year = show_year
            poster = show_meta.get('poster') or 'DefaultRecentlyAddedEpisodes.png'
            fanart = show_meta.get('fanart') or ''
            plot = ep_overview_localized
            genres_str = ', '.join(show_meta.get('genres', [])) if show_meta.get('genres') else ''
            rating = episode_meta.get('rating') or episode.get('rating') or show_meta.get('rating') or 0
            runtime = episode_meta.get('runtime') or episode.get('runtime') or show_meta.get('runtime') or 0
            meta_type = 'tvshow'
        else:
            continue
            
        url = f"{sys.argv[0]}?action=search_prefill&query={urllib.parse.quote(query)}"
        list_item = _make_media_list_item(label=label, year=year, plot=plot, genres_str=genres_str, rating=rating, runtime_min=runtime, poster=poster, fanart=fanart, media_type='movie' if meta_type == 'movie' else 'tvshow')
        cm = []
        trakt_item_id = item.get('movie', {}).get('ids', {}).get('trakt') if media_type == 'movie' else (item.get('episode', {}).get('ids', {}).get('trakt') if media_type == 'episode' else None)
        if trakt_item_id:
            cm.append((ADDON.getLocalizedString(30072), f'RunPlugin({sys.argv[0]}?action=trakt_mark&type={media_type}&id={trakt_item_id}&watched=1)'))
            cm.append((ADDON.getLocalizedString(30073), f'RunPlugin({sys.argv[0]}?action=trakt_mark&type={media_type}&id={trakt_item_id}&watched=0)'))
        list_item.addContextMenuItems(cm)
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
        
    if len(combined_items) > offset + PAGE_SIZE:
        next_offset = offset + PAGE_SIZE
        next_url = f"{sys.argv[0]}?action=trakt_playback&offset={next_offset}"
        next_label = ADDON.getLocalizedString(30117)
        li_next = xbmcgui.ListItem(label=f"[COLOR gray]>> {next_label} ({next_offset + 1}-{min(len(combined_items), next_offset + PAGE_SIZE)})[/COLOR]")
        li_next.setArt({'icon': 'DefaultFolder.png', 'thumb': 'DefaultFolder.png'})
        xbmcplugin.addDirectoryItem(HANDLE, next_url, li_next, isFolder=True)

    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def search_prefill(query):
    keyboard = xbmc.Keyboard(query, ADDON.getLocalizedString(30076))
    keyboard.doModal()
    if keyboard.isConfirmed():
        new_query = keyboard.getText()
        if new_query:
            search(new_query)
        else:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return
    else:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

def show_tmdb_menu():
    xbmcplugin.setPluginCategory(HANDLE, 'TMDb')
    fanart = get_asset('fa.png')
    items = [
        (ADDON.getLocalizedString(30096), 'tmdb_category&category=tv_tips&offset=0', 'DefaultTVShows.png'),
        (ADDON.getLocalizedString(30097), 'tmdb_category&category=vod&offset=0', 'DefaultMovies.png'),
        (ADDON.getLocalizedString(30098), 'tmdb_category&category=disks&offset=0', 'DefaultMovies.png'),
        (ADDON.getLocalizedString(30052), 'tmdb_search', 'DefaultAddonsSearch.png'),
    ]
    for label, action, icon in items:
        url = f"{sys.argv[0]}?action={action}"
        li = xbmcgui.ListItem(label=f"[COLOR #01b4e4]{label}[/COLOR]")
        li.setArt({'icon': icon, 'thumb': icon, 'fanart': fanart})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True if action != 'tmdb_search' else False)
    xbmcplugin.setContent(HANDLE, 'addons')
    xbmcplugin.endOfDirectory(HANDLE)

def show_tmdb_category(category, offset=0):
    if tmdb_module is None:
        xbmcgui.Dialog().notification('TMDb', ADDON.getLocalizedString(30103), xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    offset = int(offset)
    PAGE_SIZE = 10
    import datetime
    if category == 'tv_tips':
        all_items = tmdb_module.get_tv_tips(0)
        cat_label = ADDON.getLocalizedString(30100)
        content_type = 'episodes'
    elif category == 'vod':
        page = (offset // PAGE_SIZE) + 1
        all_items = tmdb_module.get_vod_premieres(page)
        cat_label = ADDON.getLocalizedString(30101)
        content_type = 'movies'
    elif category == 'disks':
        now = datetime.datetime.now()
        all_items = tmdb_module.get_disk_premieres(now.month, now.year)
        cat_label = ADDON.getLocalizedString(30102)
        content_type = 'movies'
    else:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    xbmcplugin.setPluginCategory(HANDLE, cat_label)
    if not all_items:
        xbmcgui.Dialog().notification('TMDb', ADDON.getLocalizedString(30104), xbmcgui.NOTIFICATION_WARNING, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    page_items = all_items[offset:offset + PAGE_SIZE]
    for item in page_items:
        raw_title = item.get('clean_title', item.get('title', ''))
        display_title = item.get('title', raw_title)
        year = item.get('year', '')
        plot = item.get('plot', '')
        info = item.get('info', '')
        poster = item.get('img', '')
        is_show = item.get('type') == 'show'
        tmdb_item_id = item.get('id')

        combined_plot = plot or ''
        if info and info not in combined_plot:
            combined_plot = f"[B]{info}[/B]\n\n{combined_plot}" if combined_plot else f"[B]{info}[/B]"

        label = f"{display_title} ({year})" if year else display_title
        kodi_type = 'tvshow' if is_show else 'movie'
        li = _make_media_list_item(label, year, combined_plot, info, None, None, poster, '', kodi_type)

        if is_show:
            url = (f"{sys.argv[0]}?action=tmdb_show_seasons"
                   f"&title={urllib.parse.quote(raw_title)}&year={year}"
                   f"&tmdb_id={tmdb_item_id if tmdb_item_id is not None else ''}")
        else:
            ws_query = f"{raw_title} {year}".strip()
            url = f"{sys.argv[0]}?action=search&query={urllib.parse.quote(ws_query)}"

        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    if len(all_items) > offset + PAGE_SIZE:
        next_offset = offset + PAGE_SIZE
        next_url = f"{sys.argv[0]}?action=tmdb_category&category={category}&offset={next_offset}"
        li_next = xbmcgui.ListItem(label=f"[COLOR gray]>> {ADDON.getLocalizedString(30117)} ({next_offset + 1}-{next_offset + PAGE_SIZE})[/COLOR]")
        li_next.setArt({'icon': 'DefaultFolder.png', 'thumb': 'DefaultFolder.png'})
        xbmcplugin.addDirectoryItem(HANDLE, next_url, li_next, isFolder=True)

    xbmcplugin.setContent(HANDLE, content_type)
    xbmcplugin.endOfDirectory(HANDLE)

def show_tmdb_show_seasons(title, year='', tmdb_id=None):
    xbmcplugin.setPluginCategory(HANDLE, f"{title} - {ADDON.getLocalizedString(30105)}")
    xbmc.log(f"StreamContinuum: show_tmdb_show_seasons called for title='{title}', year='{year}', tmdb_id='{tmdb_id}'", xbmc.LOGINFO)

    trakt_id = None
    poster = ''
    fanart = ''
    show_meta = {}

    clean_tmdb_id = tmdb_id if (tmdb_id and str(tmdb_id).strip().lower() != 'none') else None

    if clean_tmdb_id:
        try:
            trakt_id = trakt.get_trakt_id_from_tmdb_id(clean_tmdb_id, 'show')
        except Exception as e:
            xbmc.log(f"StreamContinuum: Error getting Trakt ID from TMDb ID '{clean_tmdb_id}': {e}", xbmc.LOGERROR)

    # Fallback to search_trakt by title if TMDb ID lookup failed or wasn't available
    if not trakt_id and title:
        try:
            search_results = trakt.search_trakt(title)
            for res_item in search_results:
                if res_item.get('type') == 'show':
                    found_show = res_item.get('show', {})
                    candidate_id = found_show.get('ids', {}).get('trakt')
                    if candidate_id:
                        trakt_id = candidate_id
                        xbmc.log(f"StreamContinuum: Fallback match found for show '{title}' -> Trakt ID {trakt_id}", xbmc.LOGINFO)
                        break
        except Exception as e:
            xbmc.log(f"StreamContinuum: Error searching Trakt by show title '{title}': {e}", xbmc.LOGERROR)

    if trakt_id:
        try:
            show_meta = trakt.get_localized_metadata(trakt_id, 'show')
            poster = show_meta.get('poster', '')
            fanart = show_meta.get('fanart', '')
        except Exception as e:
            xbmc.log(f"StreamContinuum: Error fetching localized metadata for Trakt ID '{trakt_id}': {e}", xbmc.LOGERROR)
        final_show_title = show_meta.get('title') or title
        show_seasons(final_show_title, str(trakt_id), poster, fanart)
    else:
        ws_query = f"{title} {year}".strip()
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        xbmc.executebuiltin(f'Container.Update({sys.argv[0]}?action=search&query={urllib.parse.quote(ws_query)},replace)')

def show_tmdb_search(query=None):
    if tmdb_module is None:
        xbmcgui.Dialog().notification('TMDb', ADDON.getLocalizedString(30103), xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    if not query:
        keyboard = xbmc.Keyboard('', ADDON.getLocalizedString(30057))
        keyboard.doModal()
        if keyboard.isConfirmed():
            query = keyboard.getText()
        else:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return

    if query:
        xbmcplugin.setPluginCategory(HANDLE, f"TMDb: {query}")
        all_items = tmdb_module.search_tmdb(query)
        if not all_items:
            xbmcgui.Dialog().notification('TMDb', ADDON.getLocalizedString(30058), xbmcgui.NOTIFICATION_WARNING, 3000)
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return

        for item in all_items:
            raw_title = item.get('clean_title', item.get('title', ''))
            display_title = item.get('title', raw_title)
            year = item.get('year', '')
            plot = item.get('plot', '')
            info = item.get('info', '')
            poster = item.get('img', '')
            is_show = item.get('type') == 'show'
            tmdb_item_id = item.get('id')

            combined_plot = plot or ''
            if info and info not in combined_plot:
                combined_plot = f"[B]{info}[/B]\n\n{combined_plot}" if combined_plot else f"[B]{info}[/B]"

            label = f"{display_title} ({year})" if year else display_title
            kodi_type = 'tvshow' if is_show else 'movie'
            li = _make_media_list_item(label, year, combined_plot, info, None, None, poster, '', kodi_type)

            if is_show:
                url = (f"{sys.argv[0]}?action=tmdb_show_seasons"
                       f"&title={urllib.parse.quote(raw_title)}"
                       f"&year={year}"
                       f"&tmdb_id={tmdb_item_id if tmdb_item_id is not None else ''}")
            else:
                ws_query = f"{raw_title} {year}".strip()
                url = f"{sys.argv[0]}?action=search&query={urllib.parse.quote(ws_query)}"

            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

        xbmcplugin.setContent(HANDLE, 'movies')
        xbmcplugin.endOfDirectory(HANDLE)

def show_seasons(show_title, trakt_id, poster='', fanart=''):
    xbmcplugin.setPluginCategory(HANDLE, f"{show_title} - {ADDON.getLocalizedString(30105)}")
    seasons = trakt.get_seasons(trakt_id)
    if not seasons:
        xbmcgui.Dialog().notification('StreamContinuum', ADDON.getLocalizedString(30106), xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    for season in seasons:
        season_num = season.get('number', 0)
        if season_num == 0:
            continue
        
        season_meta = get_trakt_localized(trakt_id, 'season', season_num=season_num)
        ep_count = season_meta.get('episode_count') or season.get('episode_count', 0)
        rating = season_meta.get('rating') or season.get('rating', 0)
        overview = season_meta.get('overview') or season.get('overview', '')
        season_title = season_meta.get('title') or f"{ADDON.getLocalizedString(30105)} {season_num}"

        label = season_title if not ep_count else f"{season_title}  ({ep_count})"
        li = xbmcgui.ListItem(label=label)
        art = {}
        if poster:
            art['poster'] = poster
            art['thumb'] = poster
            art['icon'] = poster
        art['fanart'] = fanart if fanart else get_asset('fa.png')
        li.setArt(art)

        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(season_title)
        info_tag.setMediaType('season')
        info_tag.setSeason(season_num)
        if overview:
            info_tag.setPlot(overview)
        if rating:
            try:
                info_tag.setRating(float(rating))
            except (ValueError, TypeError):
                pass
        if ep_count:
            info_tag.setEpisodeCount(ep_count)

        url = (f"{sys.argv[0]}?action=show_episodes"
               f"&show_title={urllib.parse.quote(show_title)}"
               f"&trakt_id={trakt_id}"
               f"&season={season_num}"
               f"&poster={urllib.parse.quote(poster)}"
               f"&fanart={urllib.parse.quote(fanart)}")
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    xbmcplugin.setContent(HANDLE, 'seasons')
    xbmcplugin.endOfDirectory(HANDLE)

def show_episodes(show_title, trakt_id, season_num, poster='', fanart=''):
    season_num = int(season_num)
    xbmcplugin.setPluginCategory(HANDLE, f"{show_title} - {ADDON.getLocalizedString(30105)} {season_num}")
    episodes = trakt.get_episodes(trakt_id, season_num)
    if not episodes:
        xbmcgui.Dialog().notification('StreamContinuum', ADDON.getLocalizedString(30107), xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    for episode in episodes:
        ep_num = episode.get('number', 0)
        episode_meta = get_trakt_localized(trakt_id, 'episode', season_num=season_num, episode_num=ep_num)
        ep_title = episode_meta.get('title') or episode.get('title', ADDON.getLocalizedString(30108).format(ep_num))
        overview = episode_meta.get('overview') or episode.get('overview', '')
        rating = episode_meta.get('rating') or episode.get('rating', 0)
        runtime = episode_meta.get('runtime') or episode.get('runtime', 0)

        ws_query = f"{show_title} S{season_num:02d}E{ep_num:02d}"
        label = f"S{season_num:02d}E{ep_num:02d} - {ep_title}"

        li = xbmcgui.ListItem(label=label)
        art = {}
        if poster:
            art['poster'] = poster
            art['thumb'] = poster
            art['icon'] = poster
        art['fanart'] = fanart if fanart else get_asset('fa.png')
        li.setArt(art)

        info_tag = li.getVideoInfoTag()
        info_tag.setTitle(ep_title)
        info_tag.setMediaType('episode')
        info_tag.setSeason(season_num)
        info_tag.setEpisode(ep_num)
        if overview:
            info_tag.setPlot(overview)
        if rating:
            try:
                info_tag.setRating(float(rating))
            except (ValueError, TypeError):
                pass
        if runtime:
            try:
                info_tag.setDuration(int(runtime) * 60)
            except (ValueError, TypeError):
                pass

        url = f"{sys.argv[0]}?action=search&query={urllib.parse.quote(ws_query)}"
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    xbmcplugin.setContent(HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(HANDLE)

def show_trakt_discover_menu():
    xbmcplugin.setPluginCategory(HANDLE, ADDON.getLocalizedString(30109))
    fanart = get_asset('fa-trakt.png')
    items = [
        (ADDON.getLocalizedString(30055),       'trakt_discover&list_type=trending&media_type=movies&offset=0',     'DefaultMovies.png'),
        (ADDON.getLocalizedString(30110),       'trakt_discover&list_type=popular&media_type=movies&offset=0',      'DefaultMovies.png'),
        (ADDON.getLocalizedString(30111),       'trakt_discover&list_type=recommended&media_type=movies&offset=0',  'DefaultMovies.png'),
        (ADDON.getLocalizedString(30056),       'trakt_discover&list_type=trending&media_type=shows&offset=0',      'DefaultTVShows.png'),
        (ADDON.getLocalizedString(30112),       'trakt_discover&list_type=popular&media_type=shows&offset=0',       'DefaultTVShows.png'),
        (ADDON.getLocalizedString(30113),       'trakt_discover&list_type=recommended&media_type=shows&offset=0',   'DefaultTVShows.png'),
    ]
    for label, action, icon in items:
        url = f"{sys.argv[0]}?action={action}"
        li = xbmcgui.ListItem(label=f"[COLOR #9f42c6]{label}[/COLOR]")
        li.setArt({'icon': icon, 'thumb': icon, 'fanart': fanart})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    xbmcplugin.setContent(HANDLE, 'addons')
    xbmcplugin.endOfDirectory(HANDLE)

def show_trakt_discover(list_type, media_type, offset=0):
    offset = int(offset)
    PAGE_SIZE = 10
    discover_titles = {
        ('trending', 'movies'): 30055,
        ('popular', 'movies'): 30110,
        ('recommended', 'movies'): 30111,
        ('trending', 'shows'): 30056,
        ('popular', 'shows'): 30112,
        ('recommended', 'shows'): 30113,
    }
    list_label = ADDON.getLocalizedString(discover_titles.get((list_type, media_type), 30055))
    xbmcplugin.setPluginCategory(HANDLE, f"Trakt.tv - {list_label}")

    if list_type == 'trending':
        raw = trakt.get_trending(media_type)
        item_key = 'movie' if media_type == 'movies' else 'show'
        items = [r.get(item_key, {}) for r in raw if r.get(item_key)]
    elif list_type == 'popular':
        items = trakt.get_popular(media_type)
    elif list_type == 'recommended':
        items = trakt.get_recommended(media_type)
    else:
        items = []

    if not items:
        xbmcgui.Dialog().notification('Trakt.tv', ADDON.getLocalizedString(30118), xbmcgui.NOTIFICATION_WARNING, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    page_items = items[offset:offset + PAGE_SIZE]
    item_type_single = 'movie' if media_type == 'movies' else 'show'
    kodi_content = 'movies' if media_type == 'movies' else 'tvshows'
    kodi_media_type = 'movie' if media_type == 'movies' else 'tvshow'

    for item in page_items:
        trakt_id = item.get('ids', {}).get('trakt')
        meta = get_trakt_localized(trakt_id, item_type_single) if trakt_id else {}
        title = meta.get('title') or item.get('title', '')
        year = meta.get('year') or item.get('year', '')
        overview = meta.get('overview') or item.get('overview', '')
        genres = meta.get('genres', []) or item.get('genres', [])
        rating = meta.get('rating') or item.get('rating', 0)
        runtime = meta.get('runtime') or item.get('runtime', 0)
        status = meta.get('status') or item.get('status', '')
        poster = meta.get('poster') or ('DefaultMovies.png' if item_type_single == 'movie' else 'DefaultTVShows.png')
        fanart = meta.get('fanart') or ''
        label = f"{title} ({year})" if year else title
        genres_str = ', '.join(genres[:3]) if genres else ''

        plot_parts = []
        if overview:
            plot_parts.append(overview)
        if genres_str:
            plot_parts.append(f"[B]{ADDON.getLocalizedString(30114)}:[/B] {genres_str}")
        if runtime:
            unit = 'min/ep' if media_type == 'shows' else 'min'
            plot_parts.append(f"[B]{ADDON.getLocalizedString(30115)}:[/B] {runtime} {unit}")
        if status:
            plot_parts.append(f"[B]{ADDON.getLocalizedString(30116)}:[/B] {status}")
        combined_plot = '\n'.join(plot_parts)

        li = _make_media_list_item(label, year, combined_plot, genres_str, rating, runtime, poster, fanart, kodi_media_type)
        cm = []
        if trakt_id:
            cm.append((ADDON.getLocalizedString(30072), f'RunPlugin({sys.argv[0]}?action=trakt_mark&type={item_type_single}&id={trakt_id}&watched=1)'))
            cm.append((ADDON.getLocalizedString(30073), f'RunPlugin({sys.argv[0]}?action=trakt_mark&type={item_type_single}&id={trakt_id}&watched=0)'))
        li.addContextMenuItems(cm)

        if item_type_single == 'movie':
            ws_query = f"{title} {year}".strip()
            url = f"{sys.argv[0]}?action=search&query={urllib.parse.quote(ws_query)}"
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
        else:
            url = (f"{sys.argv[0]}?action=show_seasons"
                   f"&show_title={urllib.parse.quote(title)}"
                   f"&trakt_id={trakt_id}"
                   f"&poster={urllib.parse.quote(poster)}"
                   f"&fanart={urllib.parse.quote(fanart)}")
            xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    if len(items) > offset + PAGE_SIZE:
        next_offset = offset + PAGE_SIZE
        next_url = (f"{sys.argv[0]}?action=trakt_discover"
                    f"&list_type={list_type}&media_type={media_type}&offset={next_offset}")
        next_label = ADDON.getLocalizedString(30117)
        li_next = xbmcgui.ListItem(label=f"[COLOR gray]>> {next_label} ({next_offset + 1}-{next_offset + PAGE_SIZE})[/COLOR]")
        li_next.setArt({'icon': 'DefaultFolder.png', 'thumb': 'DefaultFolder.png'})
        xbmcplugin.addDirectoryItem(HANDLE, next_url, li_next, isFolder=True)

    xbmcplugin.setContent(HANDLE, kodi_content)
    xbmcplugin.endOfDirectory(HANDLE)

def history_tmdb_identify_search(original_query):
    if tmdb_module is None:
        xbmcgui.Dialog().notification('TMDb', ADDON.getLocalizedString(30103), xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    import history
    cleaned_query = history.get_base_name(original_query)
    xbmcplugin.setPluginCategory(HANDLE, f"{ADDON.getLocalizedString(30120)}: {original_query}")
    xbmc.log(f"StreamContinuum: Searching TMDb for '{original_query}', cleaned to '{cleaned_query}'", xbmc.LOGINFO)
    all_items = tmdb_module.search_tmdb(cleaned_query)
    if not all_items:
        xbmcgui.Dialog().notification('TMDb', ADDON.getLocalizedString(30128), xbmcgui.NOTIFICATION_WARNING, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    for item in all_items:
        raw_title = item.get('clean_title', item.get('title', ''))
        display_title = item.get('title', raw_title)
        year = item.get('year', '')
        plot = item.get('plot', '')
        poster_from_search = item.get('img', '')
        backdrop_from_search = item.get('backdrop_path', '')
        is_show = item.get('type') == 'show'
        kodi_type = 'tvshow' if is_show else 'movie'

        full_tmdb_meta = {}
        if item.get('id'):
            trakt_media_type_param = item.get('media_type', 'movie').replace('tv', 'show')
            full_tmdb_meta = trakt.get_localized_metadata(
                item_id=item.get('id'), 
                media_type=trakt_media_type_param, 
                id_type='tmdb'
            )
        
        final_title = full_tmdb_meta.get('title') or raw_title
        final_year = full_tmdb_meta.get('year') or year
        final_plot = full_tmdb_meta.get('overview') or plot
        final_genres = full_tmdb_meta.get('genres', [])
        final_rating = full_tmdb_meta.get('rating') or item.get('vote_average')
        final_runtime = full_tmdb_meta.get('runtime')
        final_poster = full_tmdb_meta.get('poster') or poster_from_search
        final_fanart = full_tmdb_meta.get('fanart') or backdrop_from_search

        li = _make_media_list_item(
            label=f"{final_title} ({final_year})" if final_year else final_title,
            year=final_year,
            plot=final_plot,
            genres_str=', '.join(final_genres),
            rating=final_rating,
            runtime_min=final_runtime,
            poster=final_poster,
            fanart=final_fanart,
            media_type=kodi_type
        )

        assign_params = {
            'action': 'assign_tmdb_data_to_history',
            'original_query': original_query,
            'tmdb_id': item.get('id'),
            'media_type': kodi_type,
            'title': final_title,
            'year': final_year,
            'plot': final_plot,
            'genres': '|'.join(final_genres),
            'rating': final_rating,
            'runtime': final_runtime,
            'poster': final_poster,
            'fanart': final_fanart
        }
        
        encoded_params = '&'.join(f"{key}={urllib.parse.quote_plus(str(value) if value is not None else '')}" for key, value in assign_params.items())
        url = f"{sys.argv[0]}?{encoded_params}"
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)

    xbmcplugin.setContent(HANDLE, 'movies' if 'movie' in [i.get('media_type') for i in all_items] else 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)

def _safe_int_conversion(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def _safe_float_conversion(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def assign_tmdb_data_to_history(original_query, tmdb_id, media_type, title, year, plot, genres, rating, runtime, poster, fanart):
    import history
    tmdb_data = {
        'tmdb_id': _safe_int_conversion(tmdb_id),
        'media_type': media_type if media_type else None,
        'title': title if title else None,
        'year': _safe_int_conversion(year),
        'plot': plot if plot else None,
        'genres': genres.split('|') if genres else [],
        'rating': _safe_float_conversion(rating),
        'runtime': _safe_int_conversion(runtime),
        'poster': poster if poster else None,
        'fanart': fanart if fanart else None
    }
    
    success = history.update_history_with_tmdb_data(original_query, tmdb_data)
    if success:
        xbmcgui.Dialog().notification("StreamContinuum", ADDON.getLocalizedString(30126), xbmcgui.NOTIFICATION_INFO, 2000)
        xbmc.executebuiltin(f'Container.Update({sys.argv[0]}?action=history,replace)')
    else:
        xbmcgui.Dialog().notification("StreamContinuum", ADDON.getLocalizedString(30127), xbmcgui.NOTIFICATION_ERROR, 3000)

def run():
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 else {}
    action = params.get('action')

    # Actions that do not require an active directory handle
    if action == 'show_changelog':
        show_changelog()
        return
    elif action == 'trakt_auth':
        trakt.authenticate()
        return
    elif action == 'trakt_refresh':
        user_info = trakt.get_user_info()
        if user_info:
            username = user_info.get('username', ADDON.getLocalizedString(30077))
            ADDON.setSetting('trakt_username', username)
            xbmcgui.Dialog().notification("Trakt.tv", f"{ADDON.getLocalizedString(30078)}: {username}", xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification("Trakt.tv", ADDON.getLocalizedString(30079), xbmcgui.NOTIFICATION_ERROR)
        return
    elif action == 'trakt_logout':
        ADDON.setSetting('trakt_token', '')
        ADDON.setSetting('trakt_username', ADDON.getLocalizedString(30048))
        xbmcgui.Dialog().notification("Trakt.tv", ADDON.getLocalizedString(30080), xbmcgui.NOTIFICATION_INFO)
        return
    elif action == 'paste_from_clipboard':
        target = params.get('target')
        try:
            clipboard = xbmc.getClipboard()
            if clipboard:
                ADDON.setSetting(target, clipboard)
                xbmcgui.Dialog().notification("StreamContinuum", f"{ADDON.getLocalizedString(30081)} {target}", xbmcgui.NOTIFICATION_INFO)
            else:
                xbmcgui.Dialog().ok(ADDON.getLocalizedString(30082), ADDON.getLocalizedString(30083))
        except AttributeError:
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(30082), ADDON.getLocalizedString(30084))
        return
    elif action == 'sync_history':
        import sync
        if sync.sync_history():
            xbmcgui.Dialog().notification("StreamContinuum", "Historie synchronizována", xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification("StreamContinuum", "Chyba synchronizace", xbmcgui.NOTIFICATION_ERROR)
        return
    elif action == 'export_settings':
        keyboard = xbmc.Keyboard('', 'Zadejte PIN pro šifrování')
        keyboard.doModal()
        if keyboard.isConfirmed() and keyboard.getText():
            import sync
            success, msg = sync.export_settings(keyboard.getText())
            if success:
                xbmcgui.Dialog().notification("StreamContinuum", "Nastavení exportováno", xbmcgui.NOTIFICATION_INFO)
            else:
                xbmcgui.Dialog().notification("StreamContinuum", msg or "Chyba exportu", xbmc.NOTIFICATION_ERROR)
        return
    elif action == 'import_settings':
        keyboard = xbmc.Keyboard('', 'Zadejte PIN pro dešifrování')
        keyboard.doModal()
        if keyboard.isConfirmed() and keyboard.getText():
            import sync
            success, msg = sync.import_settings(keyboard.getText())
            if success:
                xbmcgui.Dialog().notification("StreamContinuum", "Nastavení importováno", xbmcgui.NOTIFICATION_INFO)
            else:
                xbmcgui.Dialog().notification("StreamContinuum", msg or "Chyba importu", xbmc.NOTIFICATION_ERROR)
        return
    elif action == 'trakt_mark':
        media_type = params.get('type')
        trakt_id = params.get('id')
        watched = params.get('watched') == '1'
        if watched:
            success = trakt.mark_watched(media_type, trakt_id)
        else:
            success = trakt.mark_unwatched(media_type, trakt_id)
        if success:
            xbmcgui.Dialog().notification("Trakt.tv", ADDON.getLocalizedString(30085), xbmcgui.NOTIFICATION_INFO, 2000)
        else:
            xbmcgui.Dialog().notification("Trakt.tv", ADDON.getLocalizedString(30086), xbmcgui.NOTIFICATION_ERROR, 2000)
        return
    elif action == 'history_delete':
        import history
        history.delete_from_history(params.get('query'))
        xbmc.executebuiltin('Container.Refresh')
        return
    elif action == 'history_edit':
        old_query = params.get('query')
        keyboard = xbmc.Keyboard(old_query, ADDON.getLocalizedString(30087))
        keyboard.doModal()
        if keyboard.isConfirmed():
            new_query = keyboard.getText()
            if new_query:
                import history
                history.update_history_item(old_query, new_query)
                xbmc.executebuiltin('Container.Refresh')
        return
    elif action == 'assign_tmdb_data_to_history':
        assign_tmdb_data_to_history(
            original_query=params.get('original_query'),
            tmdb_id=params.get('tmdb_id'),
            media_type=params.get('media_type'),
            title=params.get('title'),
            year=params.get('year'),
            plot=params.get('plot'),
            genres=params.get('genres'),
            rating=params.get('rating'),
            runtime=params.get('runtime'),
            poster=params.get('poster'),
            fanart=params.get('fanart')
        )
        return

    # If the action requires directory handle but handle is invalid, redirect to window
    if HANDLE < 0:
        addon_id = ADDON.getAddonInfo('id')
        target_url = f"plugin://{addon_id}/"
        if len(sys.argv) > 2 and sys.argv[2]:
            target_url += sys.argv[2]
        xbmc.log(f"StreamContinuum: Invalid handle (< 0) for action '{action}'. Redirecting to ActivateWindow.", xbmc.LOGWARNING)
        xbmc.executebuiltin(f'ActivateWindow(Videos, {target_url}, return)')
        return

    if action:
        trakt_token = ADDON.getSetting('trakt_token')
        trakt_user = ADDON.getSetting('trakt_username')
        if trakt_token and (not trakt_user or trakt_user == ADDON.getLocalizedString(30048)):
            user_info = trakt.get_user_info()
            if user_info:
                ADDON.setSetting('trakt_username', user_info.get('username', ADDON.getLocalizedString(30077)))

    if not action:
        list_categories()
    elif action == 'trakt_menu':
        trakt_menu()
    elif action == 'trakt_search_menu':
        trakt_search()
    elif action == 'settings':
        ADDON.openSettings()
    elif action == 'search':
        search(params.get('query'))
    elif action == 'search_prefill':
        search_prefill(params.get('query', ''))
    elif action == 'play':
        play(params.get('ident'), params.get('query'))
    elif action == 'trending_movies':
        xbmcgui.Dialog().ok("StreamContinuum", f"{ADDON.getLocalizedString(30055)} (WIP)")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    elif action == 'trending_shows':
        xbmcgui.Dialog().ok("StreamContinuum", f"{ADDON.getLocalizedString(30056)} (WIP)")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    elif action == 'trakt_watchlist':
        show_trakt_watchlist()
    elif action == 'trakt_playback':
        show_trakt_playback(params.get('offset', 0))
    elif action == 'trakt_search':
        trakt_search(params.get('query', ''))
    elif action == 'history':
        show_history()
    elif action == 'history_menu':
        history_menu(params.get('query'))
    elif action == 'history_tmdb_identify_search':
        history_tmdb_identify_search(params.get('original_query', ''))
    elif action == 'tmdb_menu':
        show_tmdb_menu()
    elif action == 'tmdb_category':
        show_tmdb_category(params.get('category'), params.get('offset', 0))
    elif action == 'tmdb_show_seasons':
        show_tmdb_show_seasons(params.get('title', ''), params.get('year', ''), params.get('tmdb_id'))
    elif action == 'tmdb_search':
        show_tmdb_search(params.get('query'))
    elif action == 'show_seasons':
        show_seasons(params.get('show_title', ''), params.get('trakt_id', ''), params.get('poster', ''), params.get('fanart', ''))
    elif action == 'show_episodes':
        show_episodes(params.get('show_title', ''), params.get('trakt_id', ''), params.get('season', 1), params.get('poster', ''), params.get('fanart', ''))
    elif action == 'trakt_discover_menu':
        show_trakt_discover_menu()
    elif action == 'trakt_discover':
        show_trakt_discover(params.get('list_type', 'trending'), params.get('media_type', 'movies'), params.get('offset', 0))
    else:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

if __name__ == '__main__':
    run()
