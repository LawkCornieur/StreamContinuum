import sys
import os
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib.parse
import re

# Add resources/lib to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'resources', 'lib'))

import trakt
import webshare

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])

def list_categories():
    trakt_token = ADDON.getSetting('trakt_token')
    
    # Set plugin category for breadcrumbs
    xbmcplugin.setPluginCategory(HANDLE, 'StreamContinuum')

    items = [
        (ADDON.getLocalizedString(30052), 'search', 'DefaultAddonsSearch.png'),
        (ADDON.getLocalizedString(30053), 'history', 'DefaultHistory.png')
    ]

    if trakt_token:
        items.append(('Trakt.tv', 'trakt_menu', 'DefaultAddonVideo.png'))
        
    items.append((ADDON.getLocalizedString(30054), 'settings', 'DefaultAddonSettings.png'))
    
    for label, action, icon in items:
        url = f"{sys.argv[0]}?action={action}"
        list_item = xbmcgui.ListItem(label=label)
        list_item.setArt({'icon': icon, 'thumb': icon})
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'addons')
    xbmcplugin.endOfDirectory(HANDLE)

def trakt_menu():
    xbmcplugin.setPluginCategory(HANDLE, 'Trakt.tv')
    
    items = [
        (ADDON.getLocalizedString(30057), 'trakt_search_menu', 'DefaultAddonsSearch.png'),
        (ADDON.getLocalizedString(30055), 'trending_movies', 'DefaultMovies.png'),
        (ADDON.getLocalizedString(30056), 'trending_shows', 'DefaultTVShows.png'),
        (ADDON.getLocalizedString(30050), 'trakt_playback', 'DefaultRecentlyAddedEpisodes.png'),
        (ADDON.getLocalizedString(30051), 'trakt_watchlist', 'DefaultWatchlist.png')
    ]
    
    for label, action, icon in items:
        url = f"{sys.argv[0]}?action={action}"
        list_item = xbmcgui.ListItem(label=label)
        list_item.setArt({'icon': icon, 'thumb': icon})
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
            if size_mb > 1000:
                size_str = f"{round(size_mb / 1024, 2)} GB"
            else:
                size_str = f"{round(size_mb, 2)} MB"
            
            name = item['name']
            ext = ""
            if optimize_results:
                if '.' in name:
                    parts = name.rsplit('.', 1)
                    name = parts[0]
                    ext = parts[1]
                
                # Replace dots, commas, underscores, hyphens with spaces
                name = re.sub(r'[.,_\-]', ' ', name)
                # Remove multiple spaces
                name = re.sub(r'\s+', ' ', name).strip()
            
            label = name
            list_item = xbmcgui.ListItem(label=label)
            
            # Set video info
            info = {
                'title': name,
                'plot': item['description'],
                'size': item['size'],
                'mediatype': 'video'
            }
            
            # Simple parsing of resolution and quality from name
            name_lower = item['name'].lower()
            res = '480'
            if '2160p' in name_lower or '4k' in name_lower:
                res = '2160'
            elif '1080p' in name_lower:
                res = '1080'
            elif '720p' in name_lower:
                res = '720'
            elif '480p' in name_lower:
                res = '480'
            
            info['video_resolution'] = res
            
            # Parse audio tracks
            audio_info = []
            if 'cz' in name_lower or 'dabing' in name_lower:
                audio_info.append('CZ')
            if 'en' in name_lower or 'english' in name_lower:
                audio_info.append('EN')
            if 'sk' in name_lower or 'slovensky' in name_lower:
                audio_info.append('SK')
            
            if audio_info:
                info['plot'] = f"[COLOR orange][{', '.join(audio_info)}][/COLOR] " + info['plot']
            
            # Add file info to plot
            info['plot'] += f"\n\n[B]{ADDON.getLocalizedString(30059)}:[/B] {size_str}"
            if ext:
                info['plot'] += f"\n[B]{ADDON.getLocalizedString(30089)}:[/B] {ext.upper()}"
            info['plot'] += f"\n[B]{ADDON.getLocalizedString(30060)}:[/B] {res}p"
            
            list_item.setInfo('video', info)
            
            # Set stream info for icons
            list_item.addStreamInfo('video', {'width': int(res) * 16 // 9, 'height': int(res)})
            if 'h265' in name_lower or 'hevc' in name_lower or 'x265' in name_lower:
                list_item.addStreamInfo('video', {'codec': 'hevc'})
            elif 'h264' in name_lower or 'x264' in name_lower:
                list_item.addStreamInfo('video', {'codec': 'h264'})
            
            # Set art (thumbnail)
            if item.get('img'):
                list_item.setArt({
                    'thumb': item['img'],
                    'icon': item['img'],
                    'poster': item['img']
                })
            
            list_item.setProperty('IsPlayable', 'true')
            xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=False)
        
        xbmcplugin.endOfDirectory(HANDLE)

class PlayerMonitor(xbmc.Player):
    def __init__(self):
        super(PlayerMonitor, self).__init__()
        self.ended = False
    def onPlayBackEnded(self):
        self.ended = True
    def onPlayBackStopped(self):
        self.ended = True

def play(ident, query=None, title=None):
    link = webshare.get_link(ident)
    if link:
        list_item = xbmcgui.ListItem(path=link)
        xbmcplugin.setResolvedUrl(HANDLE, True, list_item)
        
        if query and title:
            import history
            history.add_to_history(query, title)
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
        title = item.get('title', '')
        
        label = f"{title} [COLOR gray]({ADDON.getLocalizedString(30063)}: {query})[/COLOR]"
        url = f"{sys.argv[0]}?action=history_menu&query={urllib.parse.quote(query)}&title={urllib.parse.quote(title)}"
        
        list_item = xbmcgui.ListItem(label=label)
        list_item.setArt({'icon': 'DefaultHistory.png', 'thumb': 'DefaultHistory.png'})
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
        
    xbmcplugin.endOfDirectory(HANDLE)

def history_menu(query, title):
    xbmcplugin.setPluginCategory(HANDLE, f"{ADDON.getLocalizedString(30064)}: {title}")
    
    items = [
        (ADDON.getLocalizedString(30057), f'search&query={urllib.parse.quote(query)}', 'DefaultAddonsSearch.png'),
        (ADDON.getLocalizedString(30065), f'history_edit&title={urllib.parse.quote(title)}&query={urllib.parse.quote(query)}', 'DefaultEdit.png'),
        (ADDON.getLocalizedString(30066), f'history_delete&title={urllib.parse.quote(title)}', 'DefaultDelete.png'),
        (ADDON.getLocalizedString(30067), f'trakt_search&query={urllib.parse.quote(query)}', 'DefaultAddonVideo.png'),
    ]
    
    # Add episode navigation if it looks like a series
    series_pattern = re.compile(r'^(.*)\s+S(\d{2})E(\d{2})', re.IGNORECASE)
    match = series_pattern.match(title)
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
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True if 'search' in action_params else False)
        
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
            data = item.get(media_type)
            title = data.get('title')
            year = data.get('year')
            trakt_id = data.get('ids', {}).get('trakt')
            
            label = f"{title} ({year})" if year else title
            url = f"{sys.argv[0]}?action=search&query={urllib.parse.quote(title)}"
            
            list_item = xbmcgui.ListItem(label=label)
            icon = 'DefaultMovies.png' if media_type == 'movie' else 'DefaultTVShows.png'
            list_item.setArt({'icon': icon, 'thumb': icon})
            
            # Context menu for marking watched/unwatched
            cm = []
            cm.append((ADDON.getLocalizedString(30072), f'RunPlugin({sys.argv[0]}?action=trakt_mark&type={media_type}&id={trakt_id}&watched=1)'))
            cm.append((ADDON.getLocalizedString(30073), f'RunPlugin({sys.argv[0]}?action=trakt_mark&type={media_type}&id={trakt_id}&watched=0)'))
            list_item.addContextMenuItems(cm)
            
            xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
            
        xbmcplugin.endOfDirectory(HANDLE)

def show_changelog():
    changelog = "[B]Verze 1.1.6[/B]\n"
    changelog += "- Vylepšení zobrazení výsledků hledání z Webshare\n"
    changelog += "- Přidána možnost optimalizace názvů souborů\n"
    changelog += "- Přepočet velikosti nad 1000 MB na GB\n"
    changelog += "- Oprava zobrazení obrázků v doplňku i na webu\n\n"
    
    changelog += "[B]Verze 1.1.5[/B]\n"
    changelog += "- Kompletní lokalizace do angličtiny a češtiny\n"
    changelog += "- Přidána podpora pro tmavý režim na webu repozitáře\n"
    changelog += "- Oprava aktualizačního mechanismu doplňku\n\n"
    
    changelog += "[B]Verze 1.1.4[/B]\n"
    changelog += "- Oprava vyhledávání z historie (automatické spuštění)\n"
    changelog += "- Synchronizace verze s repozitářem\n\n"
    
    changelog += "[B]Verze 1.1.3[/B]\n"
    changelog += "- Oprava hlavního menu (odstranění nefunkční hlavičky)\n"
    changelog += "- Přidány navigační drobky (nadpisy sekcí)\n"
    changelog += "- Vylepšení ikon v menu\n"
    changelog += "- Oprava zobrazení historie změn\n\n"
    
    changelog += "[B]Verze 1.1.2[/B]\n"
    changelog += "- Modernizované hlavní menu\n"
    changelog += "- Rozšířené možnosti v historii (E+1, S+1, Trakt search)\n"
    changelog += "- Možnost označit/odznačit zhlédnuté na Trakt.tv\n"
    changelog += "- Optimalizace historie\n\n"
    
    changelog += "[B]Verze 1.1.1[/B]\n"
    changelog += "- Oprava vyhledávání na Webshare\n"
    changelog += "- Podpora pro Trakt.tv watchlist\n"
    changelog += "- Základní historie hledání\n"
    
    xbmcgui.Dialog().textviewer(f"StreamContinuum - {ADDON.getLocalizedString(30042)}", changelog)

def show_trakt_watchlist():
    xbmcplugin.setPluginCategory(HANDLE, ADDON.getLocalizedString(30051))
    items = trakt.get_watchlist()
    if not items:
        xbmcgui.Dialog().notification("StreamContinuum", ADDON.getLocalizedString(30074), xbmcgui.NOTIFICATION_INFO, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
        
    for item in items:
        media_type = item.get('type')
        if media_type == 'movie':
            movie = item.get('movie')
            title = movie.get('title')
            year = movie.get('year')
            query = f"{title} {year}" if year else title
            label = f"{title} ({year})" if year else title
            icon = 'DefaultMovies.png'
        elif media_type == 'show':
            show = item.get('show')
            title = show.get('title')
            year = show.get('year')
            query = title
            label = f"{title} ({year})" if year else title
            icon = 'DefaultTVShows.png'
        elif media_type == 'episode':
            show = item.get('show')
            episode = item.get('episode')
            title = f"{show.get('title')} S{episode.get('season'):02d}E{episode.get('number'):02d}"
            query = title
            label = title
            icon = 'DefaultRecentlyAddedEpisodes.png'
        else:
            continue
            
        url = f"{sys.argv[0]}?action=search_prefill&query={urllib.parse.quote(query)}"
        list_item = xbmcgui.ListItem(label=label)
        list_item.setArt({'icon': icon})
        
        cm = []
        cm.append((ADDON.getLocalizedString(30052), f'RunPlugin({sys.argv[0]}?action=search&query={urllib.parse.quote(query)})'))
        trakt_id = item.get(media_type, {}).get('ids', {}).get('trakt')
        if trakt_id:
            cm.append((ADDON.getLocalizedString(30072), f'RunPlugin({sys.argv[0]}?action=trakt_mark&type={media_type}&id={trakt_id}&watched=1)'))
            cm.append((ADDON.getLocalizedString(30073), f'RunPlugin({sys.argv[0]}?action=trakt_mark&type={media_type}&id={trakt_id}&watched=0)'))
        list_item.addContextMenuItems(cm)
        
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
        
    xbmcplugin.endOfDirectory(HANDLE)

def show_trakt_playback():
    xbmcplugin.setPluginCategory(HANDLE, ADDON.getLocalizedString(30050))
    # Combine playback (paused) and progress (next episodes)
    playback_items = trakt.get_playback()
    progress_items = trakt.get_progress()
    
    # Use a set to avoid duplicates if something is in both
    seen_ids = set()
    items = []
    
    for item in playback_items:
        media_type = item.get('type')
        if media_type == 'movie':
            movie = item.get('movie')
            trakt_id = movie.get('ids', {}).get('trakt')
            if trakt_id not in seen_ids:
                items.append(item)
                seen_ids.add(trakt_id)
        elif media_type == 'episode':
            episode = item.get('episode')
            trakt_id = episode.get('ids', {}).get('trakt')
            if trakt_id not in seen_ids:
                items.append(item)
                seen_ids.add(trakt_id)
                
    for item in progress_items:
        episode = item.get('episode')
        trakt_id = episode.get('ids', {}).get('trakt')
        if trakt_id not in seen_ids:
            items.append(item)
            seen_ids.add(trakt_id)

    if not items:
        xbmcgui.Dialog().notification("StreamContinuum", ADDON.getLocalizedString(30075), xbmcgui.NOTIFICATION_INFO, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
        
    for item in items:
        media_type = item.get('type')
        if media_type == 'movie':
            movie = item.get('movie')
            title = movie.get('title')
            year = movie.get('year')
            query = f"{title} {year}" if year else title
            label = f"{title} ({year})" if year else title
            icon = 'DefaultMovies.png'
        elif media_type == 'episode':
            show = item.get('show')
            episode = item.get('episode')
            title = f"{show.get('title')} S{episode.get('season'):02d}E{episode.get('number'):02d}"
            query = title
            label = title
            icon = 'DefaultRecentlyAddedEpisodes.png'
        else:
            continue
            
        url = f"{sys.argv[0]}?action=search_prefill&query={urllib.parse.quote(query)}"
        list_item = xbmcgui.ListItem(label=label)
        list_item.setArt({'icon': icon, 'thumb': icon})
        
        cm = []
        cm.append((ADDON.getLocalizedString(30052), f'RunPlugin({sys.argv[0]}?action=search&query={urllib.parse.quote(query)})'))
        trakt_id = item.get(media_type, {}).get('ids', {}).get('trakt')
        if trakt_id:
            cm.append((ADDON.getLocalizedString(30072), f'RunPlugin({sys.argv[0]}?action=trakt_mark&type={media_type}&id={trakt_id}&watched=1)'))
            cm.append((ADDON.getLocalizedString(30073), f'RunPlugin({sys.argv[0]}?action=trakt_mark&type={media_type}&id={trakt_id}&watched=0)'))
        list_item.addContextMenuItems(cm)
        
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
        
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
    else:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

def run():
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
    action = params.get('action')

    # Update Trakt status if token exists but username is not set
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
    elif action == 'trakt_auth':
        trakt.authenticate()
    elif action == 'sync_history':
        import sync
        if sync.sync_history():
            xbmcgui.Dialog().notification("StreamContinuum", "Historie synchronizována", xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification("StreamContinuum", "Chyba synchronizace", xbmcgui.NOTIFICATION_ERROR)
    elif action == 'export_settings':
        keyboard = xbmc.Keyboard('', 'Zadejte PIN pro šifrování')
        keyboard.doModal()
        if keyboard.isConfirmed() and keyboard.getText():
            import sync
            if sync.export_settings(keyboard.getText()):
                xbmcgui.Dialog().notification("StreamContinuum", "Nastavení exportováno", xbmcgui.NOTIFICATION_INFO)
            else:
                xbmcgui.Dialog().notification("StreamContinuum", "Chyba exportu", xbmcgui.NOTIFICATION_ERROR)
    elif action == 'import_settings':
        keyboard = xbmc.Keyboard('', 'Zadejte PIN pro dešifrování')
        keyboard.doModal()
        if keyboard.isConfirmed() and keyboard.getText():
            import sync
            if sync.import_settings(keyboard.getText()):
                xbmcgui.Dialog().notification("StreamContinuum", "Nastavení importováno", xbmcgui.NOTIFICATION_INFO)
            else:
                xbmcgui.Dialog().notification("StreamContinuum", "Chyba importu (špatný PIN?)", xbmcgui.NOTIFICATION_ERROR)
    elif action == 'trakt_refresh':
        user_info = trakt.get_user_info()
        if user_info:
            username = user_info.get('username', ADDON.getLocalizedString(30077))
            ADDON.setSetting('trakt_username', username)
            xbmcgui.Dialog().notification("Trakt.tv", f"{ADDON.getLocalizedString(30078)}: {username}", xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification("Trakt.tv", ADDON.getLocalizedString(30079), xbmcgui.NOTIFICATION_ERROR)
    elif action == 'trakt_logout':
        ADDON.setSetting('trakt_token', '')
        ADDON.setSetting('trakt_username', ADDON.getLocalizedString(30048))
        xbmcgui.Dialog().notification("Trakt.tv", ADDON.getLocalizedString(30080), xbmcgui.NOTIFICATION_INFO)
    elif action == 'paste_from_clipboard':
        target = params.get('target')
        try:
            # Kodi 20+ has xbmc.getClipboard()
            clipboard = xbmc.getClipboard()
            if clipboard:
                ADDON.setSetting(target, clipboard)
                xbmcgui.Dialog().notification("StreamContinuum", f"{ADDON.getLocalizedString(30081)} {target}", xbmcgui.NOTIFICATION_INFO)
            else:
                xbmcgui.Dialog().ok(ADDON.getLocalizedString(30082), ADDON.getLocalizedString(30083))
        except AttributeError:
            # Fallback for older Kodi versions or platforms where getClipboard fails
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(30082), ADDON.getLocalizedString(30084))
    elif action == 'settings':
        ADDON.openSettings()
    elif action == 'search':
        search(params.get('query'))
    elif action == 'search_prefill':
        search_prefill(params.get('query', ''))
    elif action == 'play':
        play(params.get('ident'), params.get('query'), params.get('title'))
    elif action == 'trending_movies':
        xbmcgui.Dialog().ok("StreamContinuum", f"{ADDON.getLocalizedString(30055)} (WIP)")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    elif action == 'trending_shows':
        xbmcgui.Dialog().ok("StreamContinuum", f"{ADDON.getLocalizedString(30056)} (WIP)")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    elif action == 'trakt_watchlist':
        show_trakt_watchlist()
    elif action == 'trakt_playback':
        show_trakt_playback()
    elif action == 'trakt_search':
        trakt_search(params.get('query', ''))
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
    elif action == 'history':
        show_history()
    elif action == 'history_menu':
        history_menu(params.get('query'), params.get('title'))
    elif action == 'history_delete':
        import history
        history.delete_from_history(params.get('title'))
        xbmc.executebuiltin('Container.Refresh')
    elif action == 'history_edit':
        old_title = params.get('title')
        old_query = params.get('query')
        keyboard = xbmc.Keyboard(old_query, ADDON.getLocalizedString(30087))
        keyboard.doModal()
        if keyboard.isConfirmed():
            new_query = keyboard.getText()
            if new_query:
                import history
                history.update_history_item(old_title, new_query, new_query) # Simple update
                xbmc.executebuiltin('Container.Refresh')
    elif action == 'show_changelog':
        show_changelog()
    else:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

if __name__ == '__main__':
    run()
