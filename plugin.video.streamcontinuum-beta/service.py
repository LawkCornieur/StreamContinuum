import xbmc
import xbmcaddon
import xbmcvfs
import os

ADDON = xbmcaddon.Addon()

if __name__ == '__main__':
    # Wait for the system to be ready
    monitor = xbmc.Monitor()
    if not monitor.waitForAbort(3): # Slightly longer delay to let Kodi finish startup
        melody_played_or_auto_start_enabled = False # Flag to decide if we need a post-startup delay

        # 1. Welcome Melody
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
                    melody_played_or_auto_start_enabled = True # Mark that we've affected UI state

                    # Add a short delay to allow the player to start and stabilize.
                    xbmc.sleep(1000) # Give it 1 second

                    # Wait for the player to stop or for a reasonable timeout.
                    # The 'Control 55 in window 10025' error suggests the player window is active.
                    timeout = 30 # Max 3 seconds (30 * 100ms)
                    while timeout > 0 and xbmc.getCondVisibility('Player.HasMedia') and xbmc.Player().isPlaying():
                        xbmc.sleep(100)
                        timeout -= 1
                    
                    if xbmc.getCondVisibility('Player.HasMedia'):
                         xbmc.executebuiltin('PlayerControl(Stop)') # Explicitly stop if still playing
                         xbmc.sleep(500) # Give Kodi a moment to process stop and close window
                    
                except Exception as e:
                    xbmc.log(f"StreamContinuum: Failed to copy/play welcome melody - {e}", xbmc.LOGERROR)
        
        # If auto-start is enabled OR melody was played (which also impacts UI context),
        # add a substantial delay BEFORE launching the addon to allow Kodi's UI to fully settle.
        if ADDON.getSettingBool('auto_start') or melody_played_or_auto_start_enabled:
            xbmc.log("StreamContinuum: Applying post-startup/melody delay before running main addon.", xbmc.LOGINFO)
            # This sleep replaces the one in addon.py's run() at the very start
            xbmc.sleep(3000) # 3 seconds delay should be robust enough
            
        # 2. Auto Start Addon
        if ADDON.getSettingBool('auto_start'):
            xbmc.executebuiltin('RunAddon(plugin.video.streamcontinuum)')
