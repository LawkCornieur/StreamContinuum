import xbmc
import xbmcaddon
import os

ADDON = xbmcaddon.Addon()

if __name__ == '__main__':
    # Wait for the system to be ready
    monitor = xbmc.Monitor()
    if not monitor.waitForAbort(3): # Slightly longer delay to let Kodi finish startup
        # 1. Welcome Melody
        if ADDON.getSettingBool('enable_welcome_melody'):
            melody_path = os.path.join(ADDON.getAddonInfo('path'), 'resources', 'media', 'welcome.mp3')
            if os.path.exists(melody_path):
                xbmc.executebuiltin('PlayMedia("{}")'.format(melody_path))
        
        # 2. Auto Start Addon
        if ADDON.getSettingBool('auto_start'):
            xbmc.executebuiltin('RunAddon(plugin.video.streamcontinuum)')
