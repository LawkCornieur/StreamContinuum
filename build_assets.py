import os
import shutil

# Asset restoration script - Copies original assets from media-src to addon resources
# This replaces the previous Google Drive dependency.

def sync_assets():
    media_src = "media-src"
    addon_dir = "plugin.video.streamcontinuum"
    res_dir = os.path.join(addon_dir, "resources")
    media_dir = os.path.join(res_dir, "media")

    # Map of source files in media-src to their destinations
    MAPPINGS = {
        "icon.png": os.path.join(res_dir, "icon.png"),
        "fa.png": os.path.join(res_dir, "fa.png"),
        "fa-trakt.png": os.path.join(media_dir, "fa-trakt.png"),
        "fa-ws.png": os.path.join(media_dir, "fa-ws.png"),
        "fa-history.png": os.path.join(media_dir, "fa-history.png"),
        "StreamContinuum.mp3": os.path.join(media_dir, "welcome.mp3")
    }

    print("Starting asset restoration from media-src...")
    
    if not os.path.exists(media_src):
        print(f"ERROR: Source directory '{media_src}' not found!")
        return

    # Ensure target directories exist
    os.makedirs(res_dir, exist_ok=True)
    os.makedirs(media_dir, exist_ok=True)

    success_count = 0
    for src_name, dest_path in MAPPINGS.items():
        src_path = os.path.join(media_src, src_name)
        
        if os.path.exists(src_path):
            try:
                # Use shutil.copy2 to preserve metadata and overwrite corrupted files
                shutil.copy2(src_path, dest_path)
                print(f"  [OK] Restored: {src_name} -> {dest_path}")
                success_count += 1
            except Exception as e:
                print(f"  [ERROR] Failed to copy {src_name}: {e}")
        else:
            print(f"  [SKIP] {src_name} not found in media-src.")

    print(f"\nAsset restoration complete. Successfully updated {success_count} files.")

if __name__ == "__main__":
    sync_assets()
