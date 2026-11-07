// KÖR — derleme betiği
// Oyunu (Three.js + efektler + yazı tipleri dahil) internetsiz çalışan TEK bir
// HTML dosyasına paketler:
//   dist-web/kor.html  -> EXE (Electron) bunu açar
//   ../kor.html        -> sunucunun /kor.html adresi ve arkadaşa atılacak dosya
import { build } from 'esbuild';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const font = (pkg, file) => readFileSync(join(here, 'node_modules', pkg, 'files', file)).toString('base64');

const fonts = `
@font-face{font-family:"Creepster";font-style:normal;font-weight:400;font-display:block;
  src:url(data:font/woff2;base64,${font('@fontsource/creepster', 'creepster-latin-400-normal.woff2')}) format("woff2")}
@font-face{font-family:"Special Elite";font-style:normal;font-weight:400;font-display:block;
  src:url(data:font/woff2;base64,${font('@fontsource/special-elite', 'special-elite-latin-400-normal.woff2')}) format("woff2");
  unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2190-21FF,U+2212,U+2215}
@font-face{font-family:"Special Elite";font-style:normal;font-weight:400;font-display:block;
  src:url(data:font/woff2;base64,${font('@fontsource/special-elite', 'special-elite-latin-ext-400-normal.woff2')}) format("woff2");
  unicode-range:U+0100-02AF,U+0304,U+0308,U+0329,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF}
`;

const out = await build({
  entryPoints: [join(here, 'src', 'game.js')],
  bundle: true, minify: true, format: 'iife', target: 'es2020', write: false,
  legalComments: 'none',
});
const js = out.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');

let html = readFileSync(join(here, 'template.html'), 'utf8');
html = html.replace('/*__FONTS__*/', () => fonts).replace('/*__GAME__*/', () => js);

mkdirSync(join(here, 'dist-web'), { recursive: true });
writeFileSync(join(here, 'dist-web', 'kor.html'), html);
writeFileSync(join(here, '..', 'kor.html'), html);
console.log(`kor.html hazır (${(html.length / 1024 / 1024).toFixed(2)} MB)`);
