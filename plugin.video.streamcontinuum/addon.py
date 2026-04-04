import sys
import os
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
    # Main Menu in Czech
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

def run():
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
    action = params.get('action')

    if not action:
        list_categories()
    elif action == 'trakt_auth':
        trakt.authenticate()
    elif action == 'settings':
        ADDON.openSettings()
    elif action == 'trending_movies':
        # Placeholder for trending movies
        xbmcgui.Dialog().ok("StreamContinuum", "Zde budou populární filmy (připravujeme)")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    elif action == 'trending_shows':
        # Placeholder for trending shows
        xbmcgui.Dialog().ok("StreamContinuum", "Zde budou populární seriály (připravujeme)")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    elif action == 'search':
        # Placeholder for search
        xbmcgui.Dialog().ok("StreamContinuum", "Vyhledávání bude brzy dostupné")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    elif action == 'history':
        # Placeholder for history
        xbmcgui.Dialog().ok("StreamContinuum", "Historie bude brzy dostupná")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    else:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

if __name__ == '__main__':
    run()
