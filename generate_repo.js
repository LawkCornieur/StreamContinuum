import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import AdmZip from 'adm-zip';

const addonsDir = '.';
const addonsXmlPath = 'addons.xml';
const addonsXmlMd5Path = 'addons.xml.md5';

async function generateRepo() {
    let addonsXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n';
    
    const dirs = fs.readdirSync(addonsDir).filter(f => {
        const fullPath = path.join(addonsDir, f);
        return fs.statSync(fullPath).isDirectory() && !f.startsWith('.') && f !== 'node_modules';
    });
    
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
                
                // Clean up old ZIPs in the addon directory
                const existingZips = fs.readdirSync(addonId).filter(f => f.endsWith('.zip'));
                for (const oldZip of existingZips) {
                    fs.unlinkSync(path.join(addonId, oldZip));
                }
                
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
                
                // Copy current version to root and clean up old root versions for this addon
                const rootZipName = zipName;
                const oldRootZips = fs.readdirSync('.').filter(f => f.startsWith(addonId) && f.endsWith('.zip') && f !== rootZipName);
                for (const oldRootZip of oldRootZips) {
                    fs.unlinkSync(oldRootZip);
                }
                fs.copyFileSync(zipPath, rootZipName);
                console.log(`Copied ${rootZipName} to root.`);
                
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

    // Update index.html kodi-listing section
    const indexPath = 'index.html';
    if (fs.existsSync(indexPath)) {
        let indexContent = fs.readFileSync(indexPath, 'utf-8');
        const listingRegex = /<div id="kodi-listing" style="display:none">([\s\S]*?)<\/div>/;
        
        let newListing = '\n        <a href="addons.xml">addons.xml</a>\n';
        newListing += '        <a href="addons.xml.md5">addons.xml.md5</a>\n';
        
        // ONLY add ZIPs found in root directory for a clean view in Kodi
        const rootZips = fs.readdirSync('.').filter(f => f.endsWith('.zip')).sort();
        for (const zip of rootZips) {
            newListing += `        <a href="${zip}">${zip}</a>\n`;
        }
        
        indexContent = indexContent.replace(listingRegex, `<div id="kodi-listing" style="display:none">${newListing}      </div>`);
        
        // Update human-visible version strings in index.html
        const repoZip = rootZips.find(z => z.startsWith('repository.streamcontinuum'));
        const pluginZip = rootZips.find(z => z.startsWith('plugin.video.streamcontinuum'));
        
        if (repoZip) {
            // Update the specific line in the instructions
            indexContent = indexContent.replace(/repository\.streamcontinuum-[\d.]+\.zip/g, repoZip);
        }
        
        fs.writeFileSync(indexPath, indexContent);
        console.log('Updated index.html kodi-listing section and version strings.');
    }
}

generateRepo();
