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
        return fs.statSync(fullPath).isDirectory() && !f.startsWith('.') && f !== 'node_modules' && f !== 'src';
    });
    
    let latestPluginVersion = '1.0.0';
    let latestRepoVersion = '1.0.0';

    for (const addonId of dirs) {
        const addonXmlPath = path.join(addonId, 'addon.xml');
        if (fs.existsSync(addonXmlPath)) {
            try {
                console.log(`Processing ${addonId}...`);
                
                // Sync images from root to addon directory
                if (fs.existsSync('icon.png')) fs.copyFileSync('icon.png', path.join(addonId, 'icon.png'));
                if (fs.existsSync('fanart.jpg')) fs.copyFileSync('fanart.jpg', path.join(addonId, 'fanart.jpg'));

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

    // Update index.html kodi-listing section
    const indexPath = 'index.html';
    if (fs.existsSync(indexPath)) {
        let indexContent = `<!doctype html>
<html lang="cs">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>StreamContinuum - Kodi Repository</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/lucide-static@0.321.0/font/lucide.min.css">
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
      body { font-family: 'Inter', sans-serif; }
      .glass { background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }
      .hero-bg { background-image: linear-gradient(to bottom, rgba(15, 23, 42, 0.7), rgba(15, 23, 42, 1)), url('fanart.jpg'); background-size: cover; background-position: center; }
    </style>
  </head>
  <body class="bg-slate-950 text-slate-100 min-h-screen">
    <div class="hero-bg min-h-[400px] flex items-center justify-center text-center px-6 py-20">
      <div class="max-w-3xl">
        <img src="icon.png" alt="StreamContinuum Logo" class="w-32 h-32 mx-auto mb-8 rounded-3xl shadow-2xl border-4 border-blue-500/20">
        <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">StreamContinuum</h1>
        <p class="text-xl text-slate-300 mb-8">Moderní doplněk pro Kodi s integrací Trakt.tv a Webshare.cz</p>
        <div class="flex flex-wrap justify-center gap-4">
          <a href="repository.streamcontinuum-${latestRepoVersion}.zip" class="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-xl font-semibold transition-all shadow-lg shadow-blue-900/20 flex items-center gap-2">
            <i class="lucide-download"></i> Stáhnout Repozitář (v${latestRepoVersion})
          </a>
          <a href="#install" class="bg-slate-800 hover:bg-slate-700 text-white px-8 py-3 rounded-xl font-semibold transition-all border border-slate-700 flex items-center gap-2">
            <i class="lucide-book-open"></i> Návod k instalaci
          </a>
        </div>
      </div>
    </div>

    <main class="max-w-5xl mx-auto px-6 py-16 space-y-20">
      <section id="install" class="grid md:grid-cols-2 gap-12 items-start">
        <div class="glass rounded-3xl p-8">
          <h2 class="text-2xl font-bold mb-6 flex items-center gap-3">
            <i class="lucide-list-ordered text-blue-400"></i> Instalace
          </h2>
          <div class="space-y-6">
            <div class="flex gap-4">
              <div class="w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold flex-shrink-0">1</div>
              <div>
                <h3 class="font-semibold mb-1">Přidat zdroj</h3>
                <p class="text-slate-400 text-sm">V Kodi jděte do <span class="text-slate-200 font-medium">Správce souborů</span> -> <span class="text-slate-200 font-medium">Přidat zdroj</span> a zadejte adresu:</p>
                <code class="block bg-slate-900 p-2 rounded mt-2 text-blue-300 text-xs break-all">https://lawkcornieur.github.io/StreamContinuum/</code>
              </div>
            </div>
            <div class="flex gap-4">
              <div class="w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold flex-shrink-0">2</div>
              <div>
                <h3 class="font-semibold mb-1">Instalovat ze ZIP</h3>
                <p class="text-slate-400 text-sm">Jděte do <span class="text-slate-200 font-medium">Doplňky</span> -> <span class="text-slate-200 font-medium">Instalovat ze souboru zip</span> a vyberte přidaný zdroj.</p>
              </div>
            </div>
            <div class="flex gap-4">
              <div class="w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold flex-shrink-0">3</div>
              <div>
                <h3 class="font-semibold mb-1">Instalovat doplněk</h3>
                <p class="text-slate-400 text-sm">Jděte do <span class="text-slate-200 font-medium">Instalovat z repozitáře</span> -> <span class="text-slate-200 font-medium">StreamContinuum Repo</span> -> <span class="text-slate-200 font-medium">Doplňky videí</span> -> <span class="text-slate-200 font-medium">StreamContinuum</span>.</p>
              </div>
            </div>
          </div>
        </div>

        <div class="glass rounded-3xl p-8">
          <h2 class="text-2xl font-bold mb-6 flex items-center gap-3">
            <i class="lucide-history text-blue-400"></i> Seznam změn
          </h2>
          <div class="prose prose-invert prose-sm max-w-none text-slate-400 whitespace-pre-line">
${changelog.replace(/\*\*(.*?)\*\*/g, '<span class="text-blue-400 font-bold">$1</span>')}
          </div>
        </div>
      </section>

      <section class="glass rounded-3xl p-8">
        <h2 class="text-2xl font-bold mb-8 flex items-center gap-3">
          <i class="lucide-settings-2 text-blue-400"></i> Konfigurace Trakt.tv
        </h2>
        <div class="grid md:grid-cols-3 gap-8">
          <div class="space-y-3">
            <div class="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center"><i class="lucide-plus-circle text-blue-400"></i></div>
            <h3 class="font-semibold">Vytvořit aplikaci</h3>
            <p class="text-slate-400 text-sm">Na Trakt.tv v sekci API Apps vytvořte novou aplikaci.</p>
          </div>
          <div class="space-y-3">
            <div class="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center"><i class="lucide-link text-blue-400"></i></div>
            <h3 class="font-semibold">Redirect URI</h3>
            <p class="text-slate-400 text-sm">Jako Redirect URI použijte: <code class="bg-slate-900 px-1 rounded text-blue-300">urn:ietf:wg:oauth:2.0:oob</code></p>
          </div>
          <div class="space-y-3">
            <div class="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center"><i class="lucide-key text-blue-400"></i></div>
            <h3 class="font-semibold">Client ID & Secret</h3>
            <p class="text-slate-400 text-sm">Zkopírujte údaje do nastavení doplňku a aktivujte zařízení.</p>
          </div>
        </div>
      </section>
    </main>

    <footer class="border-t border-slate-900 py-12 text-center text-slate-500 text-sm">
      <p>&copy; 2026 StreamContinuum Repository. Všechna práva vyhrazena.</p>
      <p class="mt-2 text-slate-700">Aktualizováno: ${new Date().toLocaleDateString('cs-CZ')} ${new Date().toLocaleTimeString('cs-CZ')}</p>
    </footer>

    <div id="kodi-listing" style="display:none">
      <a href="addons.xml">addons.xml</a>
      <a href="addons.xml.md5">addons.xml.md5</a>
      <a href="plugin.video.streamcontinuum-${latestPluginVersion}.zip">plugin.video.streamcontinuum-${latestPluginVersion}.zip</a>
      <a href="repository.streamcontinuum-${latestRepoVersion}.zip">repository.streamcontinuum-${latestRepoVersion}.zip</a>
    </div>
  </body>
</html>`;
        
        fs.writeFileSync(indexPath, indexContent);
        console.log('Updated index.html with modern UI and latest info.');
    }
}

generateRepo();
