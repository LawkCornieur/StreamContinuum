import os
import urllib.request
import xbmcaddon
import xbmc

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
RESOURCES_PATH = os.path.join(ADDON_PATH, 'resources')
MEDIA_PATH = os.path.join(RESOURCES_PATH, 'media')

# Source folder: https://drive.google.com/drive/folders/1FGYxC70rMQKAXJLhGKKgSEFmPSdj0iDF
# We use direct download links for the files.
# Note: These IDs must be the actual file IDs from the folder.
# Since I don't have the exact file IDs, I'm using the folder ID as a base 
# and assuming the user will update them or that I can find a way to list them.
# For the sake of the task, I will use placeholder IDs that the user can verify.

ASSETS = {
    'icon.png': ('1FGYxC70rMQKAXJLhGKKgSEFmPSdj0iDF', os.path.join(RESOURCES_PATH, 'icon.png')),
    'fanart.jpg': ('1FGYxC70rMQKAXJLhGKKgSEFmPSdj0iDF', os.path.join(RESOURCES_PATH, 'fanart.jpg')),
    'fanart_tra.jpg': ('1FGYxC70rMQKAXJLhGKKgSEFmPSdj0iDF', os.path.join(MEDIA_PATH, 'fanart_tra.jpg')),
    'fanart_ws.jpg': ('1FGYxC70rMQKAXJLhGKKgSEFmPSdj0iDF', os.path.join(MEDIA_PATH, 'fanart_ws.jpg')),
    'fanart_his.jpg': ('1FGYxC70rMQKAXJLhGKKgSEFmPSdj0iDF', os.path.join(MEDIA_PATH, 'fanart_his.jpg')),
}

def download_file(file_id, dest_path):
    """Download a file from Google Drive."""
    url = f'https://drive.google.com/uc?export=download&id={file_id}'
    try:
        if not os.path.exists(os.path.dirname(dest_path)):
            os.makedirs(os.path.dirname(dest_path))
        
        # Simple download using urllib
        urllib.request.urlretrieve(url, dest_path)
        return True
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error downloading asset {file_id}: {str(e)}", xbmc.LOGERROR)
        return False

def download_assets():
    """Download all missing assets."""
    # In a real scenario, we would need the specific file IDs.
    # For now, we use the folder ID as a placeholder.
    # The user should replace these with the actual IDs of the files in that folder.
    
    # Example IDs (these are fake, folder ID is 1FGYxC70rMQKAXJLhGKKgSEFmPSdj0iDF)
    # I will use the folder ID for all as a placeholder.
    
    for name, (file_id, dest_path) in ASSETS.items():
        if not os.path.exists(dest_path):
            download_file(file_id, dest_path)

if __name__ == '__main__':
    download_assets()
