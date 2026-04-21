import fs from 'fs';
import path from 'path';

const distPath = path.join(process.cwd(), 'dist');
if (fs.existsSync(distPath)) {
    console.log('Copying dist content to root for GitHub Pages...');
    
    // Create index.html from template.html for GitHub Pages
    const templateDist = path.join(distPath, 'template.html');
    if (fs.existsSync(templateDist)) {
        fs.copyFileSync(templateDist, path.join(process.cwd(), 'index.html'));
        console.log('Created index.html from template.html');
    }
    
    const files = fs.readdirSync(distPath);
    files.forEach(file => {
        // Protected files that should never be overwritten by web build
        if (file === 'template.html' || file === 'index.html') {
            return;
        }
        if (file === 'icon.png' || file === 'fa.png' || file.endsWith('.zip') || file.endsWith('.png')) {
             if (fs.existsSync(path.join(process.cwd(), file))) {
                 console.log(`Skipping protected file ${file}`);
                 return;
             }
        }
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
