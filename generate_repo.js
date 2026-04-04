import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import AdmZip from 'adm-zip';

const addonsDir = '.';
const addonsXmlPath = 'addons.xml';
const addonsXmlMd5Path = 'addons.xml.md5';

async function generateRepo() {
    let addonsXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n';
    
    const dirs = fs.readdirSync(addonsDir).filter(f => fs.statSync(path.join(addonsDir, f)).isDirectory() && !f.startsWith('.'));
    
    for (const addonId of dirs) {
        const addonXmlPath = path.join(addonId, 'addon.xml');
        if (fs.existsSync(addonXmlPath)) {
            try {
                console.log(`Processing ${addonId}...`);
                
                // Read addon.xml
                let content = fs.readFileSync(addonXmlPath, 'utf-8');
                
                // Extract version from <addon ... version="..."
                const versionMatch = content.match(/<addon[^>]*version="([^"]+)"/);
                if (!versionMatch) {
                    console.error(`Could not find version in ${addonXmlPath}`);
                    continue;
                }
                const version = versionMatch[1];
                console.log(`Found version ${version} for ${addonId}`);
                
                // Remove XML declaration
                content = content.replace(/<\?xml[^?]*\?>/g, '').trim();
                addonsXml += content + '\n';
                
                // Create ZIP file: addon_id/addon_id-version.zip
                const zipName = `${addonId}-${version}.zip`;
                const zipPath = path.join(addonId, zipName);
                
                const zip = new AdmZip();
                
                // Add everything in the addon directory to the zip, but under a folder named addonId
                const addonFiles = fs.readdirSync(addonId);
                for (const file of addonFiles) {
                    if (file.endsWith('.zip')) continue;
                    
                    const filePath = path.join(addonId, file);
                    const stats = fs.statSync(filePath);
                    
                    if (stats.isDirectory()) {
                        zip.addLocalFolder(filePath, path.join(addonId, file));
                    } else {
                        zip.addLocalFile(filePath, addonId);
                    }
                }
                
                zip.writeZip(zipPath);
                console.log(`Created ${zipPath}`);
                
                // If it's a repository, copy to root
                if (addonId.startsWith('repository.')) {
                    fs.copyFileSync(zipPath, zipName);
                    console.log(`Copied ${zipName} to root.`);
                }
                
            } catch (err) {
                console.error(`Error processing ${addonId}:`, err);
            }
        }
    }
    
    addonsXml += '</addons>\n';
    
    // Write addons.xml
    fs.writeFileSync(addonsXmlPath, addonsXml);
    
    // Generate MD5
    const md5 = crypto.createHash('md5').update(addonsXml).digest('hex');
    fs.writeFileSync(addonsXmlMd5Path, md5);
    
    console.log('Generated addons.xml and addons.xml.md5 successfully.');
}

generateRepo();
