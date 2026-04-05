import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import AdmZip from 'adm-zip';

const addonsDir = '.';
const addonsXmlPath = 'addons.xml';
const addonsXmlMd5Path = 'addons.xml.md5';

async function generateRepo() {
    let addonsXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n';
    
    // Extract changelog from addon.py
    let changelog = '';
    const addonPyPath = path.join('plugin.video.streamcontinuum', 'addon.py');
    if (fs.existsSync(addonPyPath)) {
        const addonPy = fs.readFileSync(addonPyPath, 'utf-8');
        const changelogMatch = addonPy.match(/def show_changelog\(\):[\s\S]*?changelog = "([\s\S]*?)"/);
        if (changelogMatch) {
            changelog = changelogMatch[1].replace(/\[B\]/g, '**').replace(/\[\/B\]/g, '**').replace(/\\n/g, '\n');
            // Extract the rest of the changelog lines
            const lines = addonPy.split('\n');
            let inChangelog = false;
            for (const line of lines) {
                if (line.includes('def show_changelog():')) inChangelog = true;
                if (inChangelog && line.includes('changelog += "')) {
                    changelog += line.match(/changelog \+= "([\s\S]*?)"/)[1].replace(/\[B\]/g, '**').replace(/\[\/B\]/g, '**').replace(/\\n/g, '\n');
                }
                if (inChangelog && line.includes('xbmcgui.Dialog().textviewer')) break;
            }
        }
    }

    const dirs = fs.readdirSync(addonsDir).filter(f => {
        const fullPath = path.join(addonsDir, f);
        return fs.statSync(fullPath).isDirectory() && !f.startsWith('.') && f !== 'node_modules' && f !== 'src' && f !== 'public';
    });
    
    // Ensure public directory exists for Vite
    if (!fs.existsSync('public')) fs.mkdirSync('public');

    let latestPluginVersion = '1.0.0';
    let latestRepoVersion = '1.0.0';

    for (const addonId of dirs) {
        const addonXmlPath = path.join(addonId, 'addon.xml');
        if (fs.existsSync(addonXmlPath)) {
            try {
                console.log(`Processing ${addonId}...`);
                
                // Sync images from root to addon directory and public
                if (fs.existsSync('icon.png')) {
                    fs.copyFileSync('icon.png', path.join(addonId, 'icon.png'));
                    fs.copyFileSync('icon.png', 'public/icon.png');
                }
                if (fs.existsSync('fanart.jpg')) {
                    fs.copyFileSync('fanart.jpg', path.join(addonId, 'fanart.jpg'));
                    fs.copyFileSync('fanart.jpg', 'public/fanart.jpg');
                }

                // Also ensure they are in root if we're processing the main plugin
                if (addonId === 'plugin.video.streamcontinuum') {
                    if (fs.existsSync(path.join(addonId, 'icon.png')) && !fs.existsSync('icon.png')) {
                        fs.copyFileSync(path.join(addonId, 'icon.png'), 'icon.png');
                    }
                    if (fs.existsSync(path.join(addonId, 'fanart.jpg')) && !fs.existsSync('fanart.jpg')) {
                        fs.copyFileSync(path.join(addonId, 'fanart.jpg'), 'fanart.jpg');
                    }
                }

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
                
                if (addonId === 'plugin.video.streamcontinuum') latestPluginVersion = version;
                if (addonId === 'repository.streamcontinuum') latestRepoVersion = version;

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

    // Update README.md
    const readmePath = 'README.md';
    if (fs.existsSync(readmePath)) {
        let readmeContent = fs.readFileSync(readmePath, 'utf-8');
        
        // Update version in installation steps
        readmeContent = readmeContent.replace(/repository\.streamcontinuum-[\d.]+\.zip/g, `repository.streamcontinuum-${latestRepoVersion}.zip`);
        
        // Update changelog section
        const changelogSection = `## Seznam změn\n\n${changelog}`;
        if (readmeContent.includes('## Seznam změn')) {
            readmeContent = readmeContent.replace(/## Seznam změn[\s\S]*/, changelogSection);
        } else {
            readmeContent += `\n\n${changelogSection}`;
        }
        
        fs.writeFileSync(readmePath, readmeContent);
        console.log('Updated README.md with latest version and changelog.');
    }

    // Update repo_data.json for the React app
    const repoDataPath = 'src/repo_data.json';
    const repoData = {
        latestPluginVersion,
        latestRepoVersion,
        changelog,
        updatedAt: new Date().toISOString()
    };
    fs.writeFileSync(repoDataPath, JSON.stringify(repoData, null, 2));
    console.log('Updated src/repo_data.json');

    // Update index.html kodi-listing section ONLY
    const indexPath = 'index.html';
    if (fs.existsSync(indexPath)) {
        let indexContent = fs.readFileSync(indexPath, 'utf-8');
        
        const listingStart = '<div id="kodi-listing" style="display:none">';
        const listingEnd = '</div>';
        const newListing = `${listingStart}
      <a href="addons.xml">addons.xml</a>
      <a href="addons.xml.md5">addons.xml.md5</a>
      <a href="plugin.video.streamcontinuum-${latestPluginVersion}.zip">plugin.video.streamcontinuum-${latestPluginVersion}.zip</a>
      <a href="repository.streamcontinuum-${latestRepoVersion}.zip">repository.streamcontinuum-${latestRepoVersion}.zip</a>
    ${listingEnd}`;

        const regex = new RegExp(`${listingStart}[\\s\\S]*?${listingEnd}`);
        if (indexContent.match(regex)) {
            indexContent = indexContent.replace(regex, newListing);
            fs.writeFileSync(indexPath, indexContent);
            console.log('Updated index.html kodi-listing section.');
        }
    }
}

generateRepo();
