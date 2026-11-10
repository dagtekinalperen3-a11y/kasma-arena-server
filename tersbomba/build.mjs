// TERS BOMBA — derleme betiği
// Repo kökündeki tersbomba.html (tarayıcı sürümü; Three.js, PeerJS ve yazı tiplerini
// internetten çeker) dosyasını alır, hepsini içine gömer:
//   dist-web/index.html -> EXE (Electron) ve Steam paketi bunu açar; CDN gerekmez.
// Oyunun kaynağı tek yerdedir: ../tersbomba.html. Bu betik onu değiştirmez.
import { build } from 'esbuild';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const nm = (...p) => join(here, 'node_modules', ...p);
const LATIN = 'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2190-21FF,U+2212,U+2215';
const LATIN_EXT = 'U+0100-02AF,U+0304,U+0308,U+0329,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF';
const face = (family, pkg, slug, weight) => [['latin', LATIN], ['latin-ext', LATIN_EXT]].map(([sub, range]) =>
  `@font-face{font-family:"${family}";font-style:normal;font-weight:${weight};font-display:block;` +
  `src:url(data:font/woff2;base64,${readFileSync(nm(pkg, 'files', `${slug}-${sub}-${weight}-normal.woff2`)).toString('base64')}) format("woff2");unicode-range:${range}}`).join('\n');
const fonts = [
  face('Anton', '@fontsource/anton', 'anton', 400),
  ...[500, 600, 700].map(w => face('Barlow Condensed', '@fontsource/barlow-condensed', 'barlow-condensed', w)),
  face('Special Elite', '@fontsource/special-elite', 'special-elite', 400),
].join('\n');

let html = readFileSync(join(here, '..', 'tersbomba.html'), 'utf8');
const must = (ok, what) => { if (!ok) throw new Error('tersbomba.html içinde bulunamadı: ' + what); };

// 1) yazı tipleri
must(/fonts\.googleapis\.com/.test(html), 'Google Fonts bağlantısı');
html = html.replace(/<link[^>]+fonts\.(?:googleapis|gstatic)\.com[^>]*>\s*/g, '');
html = html.replace('<style>', () => '<style>\n' + fonts + '\n');

// 2) import haritası ve PeerJS
must(/<script type="importmap">/.test(html), 'importmap');
html = html.replace(/<script type="importmap">[\s\S]*?<\/script>\s*/, '');
const peer = readFileSync(nm('peerjs', 'dist', 'peerjs.min.js'), 'utf8').replace(/<\/script/gi, '<\\/script');
must(/<script src="[^"]*peerjs[^"]*"><\/script>/.test(html), 'PeerJS script etiketi');
html = html.replace(/<script src="[^"]*peerjs[^"]*"><\/script>/, () => `<script>${peer}</script>`);

// 3) oyun kodu + Three.js tek parça
const m = html.match(/<script type="module">([\s\S]*?)<\/script>/);
must(m, 'oyun modülü');
const out = await build({
  stdin: { contents: m[1], resolveDir: here, loader: 'js' },
  bundle: true, minify: true, format: 'esm', target: 'es2022', write: false, legalComments: 'none',
});
const js = out.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');
html = html.replace(m[0], () => `<script type="module">${js}</script>`);

must(!/cdn\.jsdelivr\.net|fonts\.googleapis\.com/.test(html), 'tüm dış bağlantıların temizlenmesi');
mkdirSync(join(here, 'dist-web'), { recursive: true });
writeFileSync(join(here, 'dist-web', 'index.html'), html);
console.log(`dist-web/index.html hazır (${(html.length / 1024 / 1024).toFixed(2)} MB)`);
