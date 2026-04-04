import os
import hashlib

def generate_addons_xml():
    addons_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
    
    # List of directories that are addons
    addon_dirs = ['plugin.video.streamcontinuum', 'repository.streamcontinuum']
    
    for addon_id in addon_dirs:
        addon_xml_path = os.path.join(addon_id, 'addon.xml')
        if os.path.exists(addon_xml_path):
            with open(addon_xml_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Remove the XML declaration if it exists
                content = content.replace('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '')
                content = content.replace('<?xml version="1.0" encoding="utf-8" standalone="yes"?>', '')
                addons_xml += content.strip() + '\n'
    
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
