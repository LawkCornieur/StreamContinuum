import xbmc
import xbmcaddon
import xbmcvfs
import os

ADDON = xbmcaddon.Addon()

if __name__ == '__main__':
    monitor = xbmc.Monitor()
    if not monitor.waitForAbort(3):
        melody_played_or_auto_start_enabled = False

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
                    xbmc.executebuiltin('PlayMedia(\"{}\")'.format(profile_melody))
                    melody_played_or_auto_start_enabled = True

                    xbmc.sleep(1000)
                    timeout = 30
                    while timeout > 0 and xbmc.getCondVisibility('Player.HasMedia') and xbmc.Player().isPlaying():
                        xbmc.sleep(100)
                        timeout -= 1
                    
                    if xbmc.getCondVisibility('Player.HasMedia'):
                         xbmc.executebuiltin('PlayerControl(Stop)')
                         xbmc.sleep(500)
                    
                except Exception as e:
                    xbmc.log(f"StreamContinuum: Failed to copy/play welcome melody - {e}", xbmc.LOGERROR)
        
        if ADDON.getSettingBool('auto_start') or melody_played_or_auto_start_enabled:
            xbmc.log("StreamContinuum: Applying post-startup/melody delay before running main addon.", xbmc.LOGINFO)
            xbmc.sleep(2000)
            
        if ADDON.getSettingBool('auto_start'):
            xbmc.executebuiltin('ActivateWindow(Videos, plugin://plugin.video.streamcontinuum/, return)')
