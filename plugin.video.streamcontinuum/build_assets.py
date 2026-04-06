import os
import xbmc
import xbmcaddon
import xbmcgui

# Try to import requests, fallback to urllib if not available
try:
    import requests
except ImportError:
    requests = None
    import urllib.request

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
RESOURCES_PATH = os.path.join(ADDON_PATH, 'resources')
MEDIA_PATH = os.path.join(RESOURCES_PATH, 'media')

# Source folder: https://drive.google.com/drive/folders/1FGYxC70rMQKAXJLhGKKgSEFmPSdj0iDF
ASSETS = {
    'icon.png': ('15MGgy1fzAgoWwGM7j9c7VbwSLfv3jK1Y', os.path.join(RESOURCES_PATH, 'icon.png')),
    'fanart.png': ('1Jcdx1xAU--gJ70MYwaMdIZc4CsviGMBo', os.path.join(RESOURCES_PATH, 'fanart.png')),
    'fanart_tra.png': ('1w_CUSUI3y9Oer54e2OG7UYismpYP7hAs', os.path.join(MEDIA_PATH, 'fanart_tra.png')),
    'fanart_ws.png': ('1aUCb2QUQZKwRRlpbzQJsdIuevoaJt-x1', os.path.join(MEDIA_PATH, 'fanart_ws.png')),
    'fanart_his.png': ('1NKIQ2izUw5gN3fP1mCe0GoWi-fv4LynY', os.path.join(MEDIA_PATH, 'fanart_his.png')),
}

def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value
    return None

def download_file(file_id, dest_path):
    """Download a file from Google Drive with robust handling."""
    url = "https://docs.google.com/uc?export=download"
    
    try:
        if not os.path.exists(os.path.dirname(dest_path)):
            os.makedirs(os.path.dirname(dest_path))

        if requests:
            session = requests.Session()
            response = session.get(url, params={'id': file_id}, stream=True)
            token = get_confirm_token(response)

            if token:
                params = {'id': file_id, 'confirm': token}
                response = session.get(url, params=params, stream=True)

            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(32768):
                    if chunk:
                        f.write(chunk)
        else:
            # Fallback to urllib
            download_url = f"{url}&id={file_id}"
            urllib.request.urlretrieve(download_url, dest_path)
            
        return True
    except Exception as e:
        xbmc.log(f"StreamContinuum: Error downloading asset {file_id} to {dest_path}: {str(e)}", xbmc.LOGERROR)
        return False

def download_assets():
    """Download all missing assets."""
    progress = None
    missing_assets = [name for name, (file_id, dest_path) in ASSETS.items() if not os.path.exists(dest_path)]
    
    if missing_assets:
        progress = xbmcgui.DialogProgress()
        progress.create("StreamContinuum", "Stahování grafických podkladů...")
        
        for i, name in enumerate(missing_assets):
            file_id, dest_path = ASSETS[name]
            progress.update(int((i / len(missing_assets)) * 100), f"Stahuji: {name}")
            if progress.iscanceled():
                break
            download_file(file_id, dest_path)
            
        progress.close()

if __name__ == '__main__':
    download_assets()
