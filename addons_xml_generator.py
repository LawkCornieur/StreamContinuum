import os
import hashlib
import zipfile
import xml.etree.ElementTree as ET

def generate_addons_xml():
    addons_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
    
    # List of directories to check for addons
    # We'll look for any directory that contains an addon.xml
    for addon_id in os.listdir('.'):
        if not os.path.isdir(addon_id) or addon_id.startswith('.'):
            continue
            
        addon_xml_path = os.path.join(addon_id, 'addon.xml')
        if os.path.exists(addon_xml_path):
            try:
                # Parse addon.xml to get version
                tree = ET.parse(addon_xml_path)
                root = tree.getroot()
                version = root.get('version')
                
                print(f"Processing {addon_id} v{version}...")
                
                # Read content for addons.xml
                with open(addon_xml_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Remove the XML declaration if it exists
                    content = content.replace('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '')
                    content = content.replace('<?xml version="1.0" encoding="utf-8" standalone="yes"?>', '')
                    addons_xml += content.strip() + '\n'
                
                # Create ZIP file: addon_id/addon_id-version.zip
                zip_name = f"{addon_id}-{version}.zip"
                zip_path = os.path.join(addon_id, zip_name)
                
                # Create the zip
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root_dir, dirs, files in os.walk(addon_id):
                        for file in files:
                            # Don't include the zip itself or other zips
                            if file.endswith('.zip'):
                                continue
                            
                            file_path = os.path.join(root_dir, file)
                            # The arcname should start with the addon_id
                            arcname = os.path.relpath(file_path, os.path.join(addon_id, '..'))
                            zf.write(file_path, arcname)
                
                print(f"Created {zip_path}")
                
                # Also copy the repository zip to root for easy initial installation if it's the repo addon
                if addon_id.startswith('repository.'):
                    import shutil
                    shutil.copy2(zip_path, f"{zip_name}")
                    print(f"Copied {zip_name} to root.")

            except Exception as e:
                print(f"Error processing {addon_id}: {e}")
    
    addons_xml += '</addons>\n'
    
    # Write addons.xml
    with open('addons.xml', 'w', encoding='utf-8') as f:
        f.write(addons_xml)
    
    # Generate MD5
    md5_hash = hashlib.md5(addons_xml.encode('utf-8')).hexdigest()
    with open('addons.xml.md5', 'w', encoding='utf-8') as f:
        f.write(md5_hash)
    
    print("Generated addons.xml and addons.xml.md5 successfully.")

if __name__ == "__main__":
    generate_addons_xml()
