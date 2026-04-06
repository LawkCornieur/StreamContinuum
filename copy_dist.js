import fs from 'fs';
import path from 'path';

const distPath = path.join(process.cwd(), 'dist');
if (fs.existsSync(distPath)) {
    console.log('Copying dist content to root for GitHub Pages...');
    
    // No need to rename template.html anymore
    const files = fs.readdirSync(distPath);
    files.forEach(file => {
        if (file === 'icon-v0.0.1.png' || file === 'fa-v0.0.1.png' || file.endsWith('.zip')) return; // Skip overwriting root images and zips
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
