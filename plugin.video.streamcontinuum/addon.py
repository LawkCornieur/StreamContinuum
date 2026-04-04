import sys
import os
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib.parse

# Add resources/lib to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'resources', 'lib'))

import trakt
import webshare

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])

def list_categories():
    items = [
        ('Populární filmy', 'trending_movies', 'DefaultMovies.png'),
        ('Populární seriály', 'trending_shows', 'DefaultTVShows.png'),
        ('Hledat', 'search', 'DefaultAddonsSearch.png'),
        ('Historie', 'history', 'DefaultHistory.png'),
        ('Nastavení', 'settings', 'DefaultAddonSettings.png')
    ]
    
    for label, action, icon in items:
        url = f"{sys.argv[0]}?action={action}"
        list_item = xbmcgui.ListItem(label=label)
        list_item.setArt({'icon': icon})
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def search(query=None):
    if not query:
        keyboard = xbmc.Keyboard('', 'Hledat na Webshare')
        keyboard.doModal()
        if keyboard.isConfirmed():
            query = keyboard.getText()
        else:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return

    if query:
        results = webshare.search(query)
        if not results:
            xbmcgui.Dialog().notification("StreamContinuum", "Nebyly nalezeny žádné výsledky", xbmcgui.NOTIFICATION_INFO, 3000)
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return
        
        for item in results:
            url = f"{sys.argv[0]}?action=play&ident={item['ident']}&query={urllib.parse.quote(query)}&title={urllib.parse.quote(item['name'])}"
            size_mb = round(item['size'] / (1024 * 1024), 2)
            label = f"{item['name']} ({size_mb} MB)"
            list_item = xbmcgui.ListItem(label=label)
            
            # Set video info
            info = {
                'title': item['name'],
                'plot': item['description'],
                'size': item['size']
            }
            
            # Simple parsing of resolution and quality from name
            name_lower = item['name'].lower()
            if '2160p' in name_lower or '4k' in name_lower:
                info['video_resolution'] = '2160'
            elif '1080p' in name_lower:
                info['video_resolution'] = '1080'
            elif '720p' in name_lower:
                info['video_resolution'] = '720'
            elif '480p' in name_lower:
                info['video_resolution'] = '480'
            
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
            
            list_item.setInfo('video', info)
            
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
            
            monitor = PlayerMonitor()
            # Wait for playback to start
            for _ in range(20):
                if monitor.isPlaying():
                    break
                xbmc.sleep(500)
            
            if monitor.isPlaying():
                while monitor.isPlaying() and not monitor.ended:
                    xbmc.sleep(1000)
                
                # Playback finished, move to history
                xbmc.executebuiltin('Container.Update(plugin://plugin.video.streamcontinuum/?action=history)')
    else:
        xbmcgui.Dialog().notification("StreamContinuum", "Nepodařilo se získat odkaz k přehrání", xbmcgui.NOTIFICATION_ERROR, 3000)

def show_history():
    import history
    items = history.get_history()
    
    if not items:
        xbmcgui.Dialog().notification("StreamContinuum", "Historie je prázdná", xbmcgui.NOTIFICATION_INFO, 3000)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
        
    for item in items:
        query = item.get('query', '')
        title = item.get('title', '')
        
        label = f"{title} [COLOR gray](Hledáno: {query})[/COLOR]"
        url = f"{sys.argv[0]}?action=search_prefill&query={urllib.parse.quote(query)}"
        
        list_item = xbmcgui.ListItem(label=label)
        list_item.setArt({'icon': 'DefaultHistory.png'})
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=True)
        
    xbmcplugin.endOfDirectory(HANDLE)

def search_prefill(query):
    keyboard = xbmc.Keyboard(query, 'Hledat další díl')
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

    if not action:
        list_categories()
    elif action == 'trakt_auth':
        trakt.authenticate()
    elif action == 'settings':
        ADDON.openSettings()
    elif action == 'search':
        search()
    elif action == 'search_prefill':
        search_prefill(params.get('query', ''))
    elif action == 'play':
        play(params.get('ident'), params.get('query'), params.get('title'))
    elif action == 'trending_movies':
        xbmcgui.Dialog().ok("StreamContinuum", "Zde budou populární filmy (připravujeme)")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    elif action == 'trending_shows':
        xbmcgui.Dialog().ok("StreamContinuum", "Zde budou populární seriály (připravujeme)")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    elif action == 'history':
        show_history()
    else:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

if __name__ == '__main__':
    run()
