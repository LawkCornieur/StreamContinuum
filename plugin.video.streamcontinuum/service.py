import xbmc
import xbmcaddon
import xbmcvfs
import os

ADDON = xbmcaddon.Addon()

if __name__ == '__main__':
    monitor = xbmc.Monitor()
    if not monitor.waitForAbort(1):
        if ADDON.getSettingBool('enable_welcome_melody'):
            melody_path = os.path.join(ADDON.getAddonInfo('path'), 'resources', 'media', 'welcome.mp3')
            profile_dir = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
            profile_melody = os.path.join(profile_dir, 'welcome.mp3')
            
            if os.path.exists(melody_path):
                if not os.path.exists(profile_dir):
                    os.makedirs(profile_dir)
                try:
                    xbmcvfs.copy(melody_path, profile_melody)
                    xbmc.log("StreamContinuum: Playing welcome melody.", xbmc.LOGINFO)
                    xbmc.executebuiltin('PlayMedia("{}")'.format(profile_melody))
                except Exception as e:
                    xbmc.log(f"StreamContinuum: Failed to copy/play welcome melody - {e}", xbmc.LOGERROR)
        
        if ADDON.getSettingBool('auto_start'):
            addon_id = ADDON.getAddonInfo('id')
            xbmc.log("StreamContinuum: Auto-starting main addon window.", xbmc.LOGINFO)
            xbmc.executebuiltin(f'ActivateWindow(Videos, plugin://{addon_id}/, return)')
