import fs from 'fs';
import path from 'path';

const distPath = path.join(process.cwd(), 'dist');
if (fs.existsSync(distPath)) {
    console.log('Copying dist content to root for GitHub Pages...');
    
    // Rename template.html to index.html in dist
    if (fs.existsSync(path.join(distPath, 'template.html'))) {
        fs.renameSync(path.join(distPath, 'template.html'), path.join(distPath, 'index.html'));
    }

    const files = fs.readdirSync(distPath);
    files.forEach(file => {
        if (file === 'icon-v0.0.1.png' || file === 'fanart-v0.0.1.jpg' || file.endsWith('.zip')) return; // Skip overwriting root images and zips
        const src = path.join(distPath, file);
        const dest = path.join(process.cwd(), file);
        if (fs.statSync(src).isDirectory()) {
            if (!fs.existsSync(dest)) fs.mkdirSync(dest, { recursive: true });
            const subFiles = fs.readdirSync(src);
            subFiles.forEach(subFile => {
                fs.copyFileSync(path.join(src, subFile), path.join(dest, subFile));
            });
        } else {
            fs.copyFileSync(src, dest);
        }
    });
    console.log('Website files copied to root.');
}
