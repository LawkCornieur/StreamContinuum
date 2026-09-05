import xbmc
import xbmcaddon
import xbmcvfs
import os
import sys

ADDON_ROOT = os.path.dirname(__file__)
sys.path.append(ADDON_ROOT)
sys.path.append(os.path.join(ADDON_ROOT, 'resources', 'lib'))

import history

ADDON = xbmcaddon.Addon()

def check_new_episodes_bg():
    try:
        xbmc.log("StreamContinuum Service: Checking for new aired episodes in history on background...", xbmc.LOGINFO)
        updated = history.check_and_update_next_episodes()
        if updated:
            xbmc.log("StreamContinuum Service: New episodes detected and added to watchlist.", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"StreamContinuum Service: Background episode check failed: {e}", xbmc.LOGWARNING)

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

        if not monitor.waitForAbort(5):
            check_new_episodes_bg()

        while not monitor.abortRequested():
            if monitor.waitForAbort(14400):
                break
            check_new_episodes_bg()
