import sharp from 'sharp';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const staticDir = resolve(here, '..', 'static');

const src = await readFile(resolve(staticDir, 'icon.svg'));

const sizes = [
  { name: 'apple-touch-icon.png', size: 180 },
  { name: 'icon-512.png', size: 512 },
  { name: 'icon-192.png', size: 192 }
];

for (const { name, size } of sizes) {
  const buf = await sharp(src, { density: 600 })
    .resize(size, size)
    .png({ compressionLevel: 9 })
    .toBuffer();
  await writeFile(resolve(staticDir, name), buf);
  console.log(`wrote static/${name} (${size}x${size})`);
}
