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

def search():
    keyboard = xbmcgui.DialogKeyboard()
    keyboard.doModal()
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            results = webshare.search(query)
            if not results:
                xbmcgui.Dialog().notification("StreamContinuum", "Nebyly nalezeny žádné výsledky", xbmcgui.NOTIFICATION_INFO, 3000)
                return
            
            for item in results:
                url = f"{sys.argv[0]}?action=play&ident={item['ident']}"
                size_mb = round(item['size'] / (1024 * 1024), 2)
                label = f"{item['name']} ({size_mb} MB)"
                list_item = xbmcgui.ListItem(label=label)
                list_item.setInfo('video', {'title': item['name']})
                list_item.setProperty('IsPlayable', 'true')
                xbmcplugin.addDirectoryItem(HANDLE, url, list_item, isFolder=False)
            
            xbmcplugin.endOfDirectory(HANDLE)

def play(ident):
    link = webshare.get_link(ident)
    if link:
        list_item = xbmcgui.ListItem(path=link)
        xbmcplugin.setResolvedUrl(HANDLE, True, list_item)
    else:
        xbmcgui.Dialog().notification("StreamContinuum", "Nepodařilo se získat odkaz k přehrání", xbmcgui.NOTIFICATION_ERROR, 3000)

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
    elif action == 'play':
        play(params.get('ident'))
    elif action == 'trending_movies':
        xbmcgui.Dialog().ok("StreamContinuum", "Zde budou populární filmy (připravujeme)")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    elif action == 'trending_shows':
        xbmcgui.Dialog().ok("StreamContinuum", "Zde budou populární seriály (připravujeme)")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    elif action == 'history':
        xbmcgui.Dialog().ok("StreamContinuum", "Historie bude brzy dostupná")
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    else:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

if __name__ == '__main__':
    run()
