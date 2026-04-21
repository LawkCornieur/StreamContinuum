import xbmc
import xbmcaddon
import os

ADDON = xbmcaddon.Addon()

if __name__ == '__main__':
    # Wait for the system to be ready
    monitor = xbmc.Monitor()
    if not monitor.waitForAbort(2): # Short delay to let Kodi finish startup
        if ADDON.getSettingBool('enable_welcome_melody'):
            melody_path = os.path.join(ADDON.getAddonInfo('path'), 'resources', 'media', 'welcome.mp3')
            if os.path.exists(melody_path):
                # play the melody
                xbmc.executebuiltin('PlayMedia("{}")'.format(melody_path))
