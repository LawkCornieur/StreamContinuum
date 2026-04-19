import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import archiver from 'archiver';

const addonsDir = '.';
const publicDir = 'public';
const addonsXmlPath = path.join(publicDir, 'addons.xml');
const addonsXmlMd5Path = path.join(publicDir, 'addons.xml.md5');

    async function generateRepo() {
    // Ensure public directory exists for Vite
    if (!fs.existsSync(publicDir)) fs.mkdirSync(publicDir);

    const mediaSrc = 'media-src';
    if (!fs.existsSync(mediaSrc)) fs.mkdirSync(mediaSrc);

    // Helper to find asset with fallbacks
    const findAsset = (name) => {
        const primary = path.join(mediaSrc, name);
        if (fs.existsSync(primary)) return primary;
        
        const fallbacks = [
            path.join('.', name),
            path.join(mediaSrc, name.replace('.png', '.jpg')),
            path.join('.', name.replace('.png', '.jpg')),
        ];
        
        if (name === 'fa.png') {
            fallbacks.push(path.join('.', 'fanart.jpg'));
            fallbacks.push(path.join(mediaSrc, 'fanart.jpg'));
            fallbacks.push(path.join(mediaSrc, 'fa.jpg'));
        }
        
        for (const f of fallbacks) {
            if (fs.existsSync(f)) return f;
        }
        return null;
    };

    let addonsXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n';
    
    // Extract changelog from addon.py
    let changelog = '';
    const addonPyPath = path.join('plugin.video.streamcontinuum', 'addon.py');
    if (fs.existsSync(addonPyPath)) {
        const addonPy = fs.readFileSync(addonPyPath, 'utf-8');
        const changelogMatch = addonPy.match(/def show_changelog\(\):[\s\S]*?changelog\s*=\s*["']([\s\S]*?)["']/);
        if (changelogMatch) {
            changelog = changelogMatch[1].replace(/\[B\]/g, '**').replace(/\[\/B\]/g, '**').replace(/\\n/g, '\n');
            // Extract the rest of the changelog lines
            const lines = addonPy.split('\n');
            let inChangelog = false;
            for (const line of lines) {
                if (line.includes('def show_changelog():')) inChangelog = true;
                if (inChangelog && line.includes('changelog += "')) {
                    const match = line.match(/changelog\s*\+=\s*["']([\s\S]*?)["']/);
                    if (match) {
                        changelog += match[1].replace(/\[B\]/g, '**').replace(/\[\/B\]/g, '**').replace(/\\n/g, '\n');
                    }
                }
                if (inChangelog && line.includes('xbmcgui.Dialog().textviewer')) break;
            }
        }
    }

    const dirs = fs.readdirSync(addonsDir).filter(f => {
        const fullPath = path.join(addonsDir, f);
        return fs.statSync(fullPath).isDirectory() && !f.startsWith('.') && f !== 'node_modules' && f !== 'src' && f !== 'public' && f !== 'dist';
    });
    
    let latestPluginVersion = '1.0.0';
    let latestRepoVersion = '1.0.0';

    for (const addonId of dirs) {
        const addonXmlFile = path.join(addonId, 'addon.xml');
        if (fs.existsSync(addonXmlFile)) {
            try {
                console.log(`Processing ${addonId}...`);
                
                // Sync images from media-src to addon directory and public
                const mediaSrc = 'media-src';
                
                // Main Icon
                const iconPath = findAsset('icon.png');
                if (iconPath) {
                    // Copy to resources for plugin
                    const iconResources = path.join(addonId, 'resources', 'icon.png');
                    if (!fs.existsSync(path.dirname(iconResources))) fs.mkdirSync(path.dirname(iconResources), { recursive: true });
                    fs.copyFileSync(iconPath, iconResources);
                    // Copy to root for repository
                    fs.copyFileSync(iconPath, path.join(addonId, 'icon.png'));
                    // Copy to public for web
                    fs.copyFileSync(iconPath, path.join(publicDir, 'icon.png'));
                }
                
                // Main Fanart
                const fanartPath = findAsset('fa.png');
                if (fanartPath) {
                    // Copy to resources for plugin
                    const fanartResources = path.join(addonId, 'resources', 'fanart.png');
                    if (!fs.existsSync(path.dirname(fanartResources))) fs.mkdirSync(path.dirname(fanartResources), { recursive: true });
                    fs.copyFileSync(fanartPath, fanartResources);
                    // Copy to root for repository
                    fs.copyFileSync(fanartPath, path.join(addonId, 'fanart.png'));
                    // Copy to public for web
                    fs.copyFileSync(fanartPath, path.join(publicDir, 'fa.png'));
                }

                // Section Fanarts (media folder)
                const sectionMedia = {
                    'fa-ws.png': 'fa-ws.png',
                    'fa-trakt.png': 'fa-trakt.png',
                    'fa-history.png': 'fa-history.png'
                };

                for (const [src, dest] of Object.entries(sectionMedia)) {
                    const sectionPath = findAsset(src);
                    if (sectionPath) {
                        const destPath = path.join(addonId, 'resources', 'media', dest);
                        if (!fs.existsSync(path.dirname(destPath))) fs.mkdirSync(path.dirname(destPath), { recursive: true });
                        fs.copyFileSync(sectionPath, destPath);
                        fs.copyFileSync(sectionPath, path.join(publicDir, src));
                    }
                }

                // Sync Favicons
                const faviconSrc = path.join(mediaSrc, 'favicon');
                if (fs.existsSync(faviconSrc)) {
                    const favicons = fs.readdirSync(faviconSrc);
                    for (const fav of favicons) {
                        fs.copyFileSync(path.join(faviconSrc, fav), path.join(publicDir, fav));
                    }
                }

                // Sync Webmanifest
                if (fs.existsSync('site.webmanifest')) {
                    fs.copyFileSync('site.webmanifest', path.join(publicDir, 'site.webmanifest'));
                }

                // Read addon.xml
                let content = fs.readFileSync(addonXmlFile, 'utf-8');
                
                // Extract version from <addon ... version="..."
                const versionMatch = content.match(/<addon[^>]*version="([^"]+)"/);
                if (!versionMatch) {
                    console.error(`Could not find version in ${addonXmlFile}`);
                    continue;
                }
                const version = versionMatch[1];
                console.log(`Found version ${version} for ${addonId}`);
                
                if (addonId === 'plugin.video.streamcontinuum') latestPluginVersion = version;
                if (addonId === 'repository.streamcontinuum') latestRepoVersion = version;

                // Remove XML declaration
                content = content.replace(/<\?xml[^?]*\?>/g, '').trim();
                addonsXml += content + '\n';
                
                // Sync version to settings.xml if it's the main plugin
                if (addonId === 'plugin.video.streamcontinuum') {
                    const settingsPath = path.join(addonId, 'resources', 'settings.xml');
                    if (fs.existsSync(settingsPath)) {
                        let settingsContent = fs.readFileSync(settingsPath, 'utf-8');
                        const updatedSettings = settingsContent.replace(/(<setting id="about_version"[^>]*default=")[^"]+(")/, `$1${version}$2`);
                        if (settingsContent !== updatedSettings) {
                            fs.writeFileSync(settingsPath, updatedSettings);
                            console.log(`Updated version to ${version} in settings.xml`);
                        }
                    }
                }
                
                // Create ZIP file: addon_id/addon_id-version.zip
                const zipName = `${addonId}-${version}.zip`;
                const zipPath = path.join(addonId, zipName);
                
                // Clean up old ZIPs in the addon directory
                const existingZips = fs.readdirSync(addonId).filter(f => f.endsWith('.zip'));
                for (const oldZip of existingZips) {
                    fs.unlinkSync(path.join(addonId, oldZip));
                }
                
                // Use archiver
                await new Promise((resolve, reject) => {
                    const output = fs.createWriteStream(zipPath);
                    const archive = archiver('zip', {
                        zlib: { level: 9 } // Sets the compression level.
                    });

                    output.on('close', function() {
                        console.log(`Created ${zipPath} (${archive.pointer()} total bytes)`);
                        resolve();
                    });

                    archive.on('error', function(err) {
                        reject(err);
                    });

                    archive.pipe(output);

                    // Add everything in the addon directory to the zip, but under a folder named addonId
                    const addonFiles = fs.readdirSync(addonId);
                    for (const file of addonFiles) {
                        if (file.endsWith('.zip')) continue;
                        
                        const filePath = path.join(addonId, file);
                        const stats = fs.statSync(filePath);
                        
                        if (stats.isDirectory()) {
                            archive.directory(filePath, path.join(addonId, file));
                        } else {
                            archive.file(filePath, { name: path.join(addonId, file) });
                        }
                    }

                    archive.finalize();
                });
                
                // Copy current version to public and clean up old public versions for this addon
                const publicZipPath = path.join(publicDir, zipName);
                const oldPublicZips = fs.readdirSync(publicDir).filter(f => f.startsWith(addonId) && f.endsWith('.zip') && f !== zipName);
                for (const oldPublicZip of oldPublicZips) {
                    fs.unlinkSync(path.join(publicDir, oldPublicZip));
                }
                fs.copyFileSync(zipPath, publicZipPath);
                
                // Also copy to root for backward compatibility if needed, but public is primary
                const rootZipPath = zipName;
                const oldRootZips = fs.readdirSync('.').filter(f => f.startsWith(addonId) && f.endsWith('.zip') && f !== zipName);
                for (const oldRootZip of oldRootZips) {
                    fs.unlinkSync(oldRootZip);
                }
                fs.copyFileSync(zipPath, rootZipPath);
                
                console.log(`Copied ${zipName} to public and root.`);
                
            } catch (err) {
                console.error(`Error processing ${addonId}:`, err);
            }
        }
    }
    
    addonsXml += '</addons>\n';
    
    // Write addons.xml to root and public
    fs.writeFileSync('addons.xml', addonsXml);
    fs.writeFileSync(addonsXmlPath, addonsXml);
    
    // Generate MD5 for root and public
    const md5 = crypto.createHash('md5').update(addonsXml).digest('hex');
    fs.writeFileSync('addons.xml.md5', md5);
    fs.writeFileSync(addonsXmlMd5Path, md5);
    
    console.log('Generated addons.xml and addons.xml.md5 successfully in root and public.');

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

    // Update template.html kodi-listing section ONLY
    const templatePath = 'template.html';
    if (fs.existsSync(templatePath)) {
        let templateContent = fs.readFileSync(templatePath, 'utf-8');
        
        const listingStart = '<div id="kodi-listing" style="display:none">';
        const listingEnd = '</div>';
        const newListing = `${listingStart}
      <a href="addons.xml">addons.xml</a>
      <a href="addons.xml.md5">addons.xml.md5</a>
      <a href="plugin.video.streamcontinuum-${latestPluginVersion}.zip">plugin.video.streamcontinuum-${latestPluginVersion}.zip</a>
      <a href="repository.streamcontinuum-${latestRepoVersion}.zip">repository.streamcontinuum-${latestRepoVersion}.zip</a>
    ${listingEnd}`;

        const regex = new RegExp(`${listingStart}[\\s\\S]*?${listingEnd}`);
        if (templateContent.match(regex)) {
            templateContent = templateContent.replace(regex, newListing);
            fs.writeFileSync(templatePath, templateContent);
            console.log('Updated template.html kodi-listing section.');
        }
    }
}

generateRepo();
