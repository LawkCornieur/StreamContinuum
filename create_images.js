import fs from 'fs';

const transparentPng = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=', 'base64');

fs.writeFileSync('plugin.video.streamcontinuum/icon.png', transparentPng);
fs.writeFileSync('plugin.video.streamcontinuum/fanart.jpg', transparentPng);
