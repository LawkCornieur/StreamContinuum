import xbmc
import xbmcaddon
import xbmcvfs
import os

ADDON = xbmcaddon.Addon()

if __name__ == '__main__':
    # Wait for the system to be ready
    monitor = xbmc.Monitor()
    if not monitor.waitForAbort(3): # Slightly longer delay to let Kodi finish startup
        # 1. Welcome Melody
        if ADDON.getSettingBool('enable_welcome_melody'):
            melody_path = os.path.join(ADDON.getAddonInfo('path'), 'resources', 'media', 'welcome.mp3')
            profile_dir = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
            profile_melody = os.path.join(profile_dir, 'welcome.mp3')
            
            if os.path.exists(melody_path):
                if not os.path.exists(profile_dir):
                    os.makedirs(profile_dir)
                try:
                    # Zkopírujeme soubor do profile mapy, aby nebyl při přehrávání zamčený původní adresář s doplňkem,
                    # což způsobuje v OS Windows pád aktualizace doplňku s (Error renaming file).
                    xbmcvfs.copy(melody_path, profile_melody)
                    xbmc.executebuiltin('PlayMedia("{}")'.format(profile_melody))
                except Exception as e:
                    xbmc.log("StreamContinuum: failed to copy/play welcome melody - " + str(e), xbmc.LOGERROR)
        
        # 2. Auto Start Addon
        if ADDON.getSettingBool('auto_start'):
            xbmc.executebuiltin('RunAddon(plugin.video.streamcontinuum)')

