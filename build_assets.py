import os
import sys
import requests

# Google Drive file IDs map
# User: Fill in the file IDs from your Google Drive
ASSETS = {
    "icon.png": "YOUR_ICON_PNG_GOOGLE_DRIVE_ID",
    "fa.png": "YOUR_FA_PNG_GOOGLE_DRIVE_ID",
    "fa-trakt.png": "YOUR_FA_TRAKT_PNG_GOOGLE_DRIVE_ID",
    "fa-ws.png": "YOUR_FA_WS_PNG_GOOGLE_DRIVE_ID",
    "fa-history.png": "YOUR_FA_HISTORY_PNG_GOOGLE_DRIVE_ID"
}

def download_file(file_id, dest_path):
    print(f"Downloading {dest_path}...")
    url = f"https://docs.google.com/uc?export=download&id={file_id}"
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Successfully downloaded {dest_path}")
        return True
    except Exception as e:
        print(f"Error downloading {dest_path}: {e}")
        return False

def build():
    addon_dir = "plugin.video.streamcontinuum"
    res_dir = os.path.join(addon_dir, "resources")
    media_dir = os.path.join(res_dir, "media")

    # Ensure directories exist
    os.makedirs(res_dir, exist_ok=True)
    os.makedirs(media_dir, exist_ok=True)

    for filename, file_id in ASSETS.items():
        if not file_id or "YOUR_" in file_id:
            print(f"Skipping {filename}: No Google Drive ID provided.")
            continue

        if filename in ["icon.png", "fa.png"]:
            dest = os.path.join(res_dir, filename)
        else:
            dest = os.path.join(media_dir, filename)
        
        # Download
        download_file(file_id, dest)

    # Also copy to root resources if needed for GitHub Pages or repo
    # This matches the structure of the repository
    print("Asset build complete.")

if __name__ == "__main__":
    build()
