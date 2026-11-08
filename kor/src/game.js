import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';

/* =====================================================================
   KÖR — Sessiz Koğuş
   Tek dosya 3D korku oyunu. Kör bir yaratık, ses tabanlı yapay zekâ,
   prosedürel dokular ve prosedürel ses (WebAudio). Harici dosya yok.
   ===================================================================== */

const $ = id => document.getElementById(id);
let RNG = Math.random;
const rand = (a, b) => a + RNG() * (b - a);
const mulberry32 = a => () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
const shuffle = arr => { const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { const j = (RNG() * (i + 1)) | 0; [a[i], a[j]] = [a[j], a[i]]; } return a; };
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const pick = arr => arr[(RNG() * arr.length) | 0];
const store = {
  get(k, d) { try { const v = localStorage.getItem('kor_' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('kor_' + k, JSON.stringify(v)); } catch (e) {} }
};

/* ------------------------------ HARİTA ------------------------------ */
// 1. kat (x 0-36) | 2. kat (x 39-75). Y = merdiven (iki kat arasında eşleşir)
const MAP = [
"############################################################################",
"#.....#L........#L......F.#........L####.........#.........#.......#.......#",
"#.....D.........#.........#.........####.........#.........#.......#.......#",
"#..S..#.........#.........#.......F.####.........#.........#.......#.......#",
"#.....#.......F.#.........#.........####.........#.........#.......#.......#",
"###D#######D#########D#########D############D#########D########D#######D####",
"#.......L...............L..........Y####..................................Y#",
"#####D#####.#############D#####.#############D######.##D########.#####D#####",
"#L........#.#...B...#........L#.#...####L..........#.#..#.#.#..#.#........L#",
"#.........#.D.......#.........#.#.K.####...........#.#..#.#.#..#.#.........#",
"#.........#.#.......#.........D.#...####...........#.D..#.#.#..#.#.........#",
"#.........D.#.......#.........#.X...####...........D.#..#.#.#..#.D.........#",
"#.........#.#.......D.........#.#...####...........#.#.........D.#.........#",
"#.F.......#.#.......#.........#.#...####...........#.#.........#.#.........#",
"#.........#.#.......#.F.......#.#...####...........#.#........L#.#.........#",
"###########.####D########D#####.####################.###########.###########",
"#Y............L..................L..####Y..................................#",
"#####D########D#######D####D#################D###########D###########D######",
"#.........#.......#.................####...........#...........#...........#",
"#.......F.#.......#................L####L..........#...........#...........#",
"#.........#.......#.................####...........#...........#...........#",
"#.........#.......D.................####...........D...........D...........#",
"#.........D.......#.................####...........#...........#...........#",
"#.........#.......#.........M.......####...........#...........#..........L#",
"#.........#.F.....#.................####...........#...........#...........#",
"#L........#.......#L................####...........#...........#...........#",
"###########################E################################################",
];
const GW = MAP[0].length, GH = MAP.length;
const C = 3.2;           // hücre boyu (metre)
const WALL_H = 3.0;
const cellAt = (x, z) => (x < 0 || z < 0 || x >= GW || z >= GH) ? '#' : MAP[z][x];
const toCell = v => Math.floor(v / C);
const cc = i => (i + 0.5) * C;  // hücre merkezi
const F2X = 39;                                   // 2. katın ızgaradaki x kayması
const floorOfX = x => (x >= F2X * C ? 1 : 0);     // dünya x -> kat
const STAIRS = [[35, 6], [1, 16]];                // her iki katta aynı yerel konum
const stairPair = (x, z) => { const f = x >= F2X ? 1 : 0, lx = x - f * F2X; return [lx + (1 - f) * F2X, z]; };

const ROOMS = [
  { n: 'Hasta Odası 13', x0: 1, z0: 1, x1: 5, z1: 4 },
  { n: 'Koğuş', x0: 7, z0: 1, x1: 15, z1: 4 },
  { n: 'Banyolar', x0: 17, z0: 1, x1: 25, z1: 4 },
  { n: 'Depo', x0: 27, z0: 1, x1: 35, z1: 4 },
  { n: 'Ameliyathane', x0: 1, z0: 8, x1: 9, z1: 14 },
  { n: 'Jeneratör', x0: 13, z0: 8, x1: 19, z1: 14 },
  { n: 'Yemekhane', x0: 21, z0: 8, x1: 29, z1: 14 },
  { n: 'Başhekim', x0: 33, z0: 8, x1: 35, z1: 14 },
  { n: 'Morg', x0: 1, z0: 18, x1: 9, z1: 25 },
  { n: 'Şapel', x0: 11, z0: 18, x1: 17, z1: 25 },
  { n: 'Lobi', x0: 19, z0: 18, x1: 35, z1: 25 },
  { n: 'Arşiv', x0: 40, z0: 1, x1: 48, z1: 4, f: 1 },
  { n: 'Kütüphane', x0: 50, z0: 1, x1: 58, z1: 4, f: 1 },
  { n: 'Elektroşok', x0: 60, z0: 1, x1: 66, z1: 4, f: 1 },
  { n: 'Kazan Dairesi', x0: 68, z0: 1, x1: 74, z1: 4, f: 1 },
  { n: 'Çocuk Koğuşu', x0: 40, z0: 8, x1: 50, z1: 14, f: 1 },
  { n: 'Hücreler', x0: 54, z0: 8, x1: 62, z1: 14, f: 1 },
  { n: 'Laboratuvar', x0: 66, z0: 8, x1: 74, z1: 14, f: 1 },
  { n: 'Duşlar', x0: 40, z0: 18, x1: 50, z1: 25, f: 1 },
  { n: 'Gözlem Odası', x0: 52, z0: 18, x1: 62, z1: 25, f: 1 },
  { n: 'Yatakhane', x0: 64, z0: 18, x1: 74, z1: 25, f: 1 },
];
const roomOf = (x, z) => ROOMS.find(r => x >= r.x0 && x <= r.x1 && z >= r.z0 && z <= r.z1);

/* ------------------------------ AYARLAR ----------------------------- */
const DIFF = [
  { name: 'KOLAY', hear: 0.7, speed: 0.85, chaseSpeed: 3.9, track: 2.2 },
  { name: 'NORMAL', hear: 1.0, speed: 1.0, chaseSpeed: 4.55, track: 3.0 },
  { name: 'KÂBUS', hear: 1.35, speed: 1.15, chaseSpeed: 5.15, track: 4.2 },
];
let diff = store.get('diff', 1);
let sens = store.get('sens', 1);
let volume = store.get('vol', 1);

/* ---------------------------- RENDERER ------------------------------ */
const canvas = $('game');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
const isTouch = matchMedia('(pointer: coarse)').matches || 'ontouchstart' in window;
// GRAFİK KALİTESİ: 0 düşük, 1 orta, 2 yüksek
let quality = store.get('quality', isTouch ? 0 : 2);
const QUAL = [
  { res: .6, shadow: 512, bloom: false, post: true },
  { res: .85, shadow: 1024, bloom: true, post: true },
  { res: 1.0, shadow: 2048, bloom: true, post: true },
];
renderer.setSize(innerWidth, innerHeight, false);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.2;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000000);
scene.fog = new THREE.FogExp2(0x03040a, 0.068);
const camera = new THREE.PerspectiveCamera(72, innerWidth / innerHeight, 0.05, 80);
scene.add(camera);

/* ---- son işleme: bloom + film (gren, vinyet, renk sapması, korku nabzı) ---- */
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), .55, .6, .82);
composer.addPass(bloom);
composer.addPass(new OutputPass());
const filmPass = new ShaderPass({
  uniforms: {
    tDiffuse: { value: null }, uTime: { value: 0 }, uFear: { value: 0 }, uGrain: { value: .09 },
    uCA: { value: .0015 }, uHit: { value: 0 }, uGlitch: { value: 0 }, uHallu: { value: 0 }, uNV: { value: 0 }, uRes: { value: new THREE.Vector2(innerWidth, innerHeight) },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform float uTime, uFear, uGrain, uCA, uHit, uGlitch, uHallu, uNV; uniform vec2 uRes; varying vec2 vUv;
    float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233))) * 43758.5453); }
    void main(){
      vec2 uv = vUv; vec2 c = uv - .5; float r = length(c);
      // korku: ekran kenarları dalgalanır
      uv += c * sin(uTime * 7. + r * 20.) * .004 * uFear;
      uv += vec2(sin(uv.y * 14. + uTime * 3.), cos(uv.x * 11. + uTime * 2.3)) * .006 * uHallu;
      // bozulma: yatay bant kaymaları
      float fr = floor(uTime * 24.);
      float band = floor(vUv.y * 18.);
      float gOn = step(.62, h(vec2(band, fr))) * uGlitch;
      uv.x += (h(vec2(band * 1.7, fr + 3.)) - .5) * .16 * gOn;
      uv.y += (h(vec2(fr, 9.)) - .5) * .03 * uGlitch;
      float ca = uCA * (1. + uFear * 4. + uHit * 10. + uGlitch * 30.) * r * 2. + uGlitch * .012;
      vec3 col;
      col.r = texture2D(tDiffuse, uv + c * ca).r;
      col.g = texture2D(tDiffuse, uv).g;
      col.b = texture2D(tDiffuse, uv - c * ca).b;
      // renk düzenleme: soğuk gölgeler, hafif solgun
      float l = dot(col, vec3(.299,.587,.114));
      col = mix(vec3(l), col, .78);
      col *= mix(vec3(.86,.95,1.04), vec3(1.05,1.,.9), smoothstep(.0,.6,l));
      // korku: kırmızı kenar nabzı
      float beat = pow(abs(sin(uTime * (2.2 + uFear * 3.))), 6.);
      col = mix(col, col * vec3(1.35,.45,.4), smoothstep(.25,.75,r) * uFear * (.55 + beat * .45));
      // sanrı: kan kırmızısı dünya
      float lh = dot(col, vec3(.299,.587,.114));
      col = mix(col, vec3(lh * 1.5, lh * .3, lh * .25) + vec3(.05,0.,0.), uHallu * .8);
      // gece görüşü: yeşil, parlak, karıncalı
      float ln = dot(col, vec3(.299,.587,.114));
      vec3 nv = vec3(.18, 1., .28) * (pow(ln, .55) * 1.9 + .03) + (h(vUv * uRes * .5 + uTime) - .5) * .22;
      nv *= .92 + .08 * sin(vUv.y * uRes.y * .9 - uTime * 40.);
      col = mix(col, nv, uNV);
      // vinyet
      col *= smoothstep(.95, .28, r * (1. + uFear * .25 + uHallu * .35));
      // film greni + tarama
      float g = h(vUv * uRes + fract(uTime * 37.)) - .5;
      col += g * uGrain * (.6 + l);
      col *= .965 + .035 * sin(vUv.y * uRes.y * 1.4 + uTime * 30.);
      col += vec3(1.,.1,.05) * uHit * .35;
      col = mix(col, 1. - col, step(.93, h(vec2(fr, 2.))) * step(.5, uGlitch));
      gl_FragColor = vec4(col, 1.);
    }`,
});
composer.addPass(filmPass);
function applyQuality() {
  const Q = QUAL[quality];
  const pr = Math.min(devicePixelRatio, 1.5) * Q.res;
  renderer.setPixelRatio(pr); composer.setPixelRatio(pr);
  renderer.setSize(innerWidth, innerHeight, false); composer.setSize(innerWidth, innerHeight);
  bloom.enabled = Q.bloom;
  filmPass.uniforms.uRes.value.set(innerWidth * pr, innerHeight * pr);
  if (typeof flashlight !== 'undefined' && flashlight.shadow.mapSize.x !== Q.shadow) {
    flashlight.shadow.mapSize.set(Q.shadow, Q.shadow);
    if (flashlight.shadow.map) { flashlight.shadow.map.dispose(); flashlight.shadow.map = null; }
  }
}
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  applyQuality();
});

const ambient = new THREE.AmbientLight(0x1a1d2a, 0.75);
scene.add(ambient);
const hemi = new THREE.HemisphereLight(0x22283a, 0x0a0505, 0.25);
scene.add(hemi);

// El feneri
const flashlight = new THREE.SpotLight(0xfff1d6, 60, 30, 0.6, 0.55, 1.4);
flashlight.castShadow = true;
flashlight.shadow.mapSize.set(QUAL[quality].shadow, QUAL[quality].shadow);
flashlight.shadow.camera.near = 0.2;
flashlight.shadow.camera.far = 26;
flashlight.shadow.bias = -0.0015;
flashlight.position.set(0.18, -0.12, 0.05);
camera.add(flashlight);
camera.add(flashlight.target);
flashlight.target.position.set(0, -0.2, -5);
const fillLight = new THREE.PointLight(0xffe6c0, 0.9, 4, 2);  // fenerin yansıması
camera.add(fillLight);

/* ------------------------- PROSEDÜREL DOKULAR ------------------------ */
function makeCanvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
function grime(ctx, w, h, n, col, rmin, rmax, a) {
  for (let i = 0; i < n; i++) {
    const x = Math.random() * w, y = Math.random() * h, r = rand(rmin, rmax);
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, col.replace('A', a * rand(.4, 1)));
    g.addColorStop(1, col.replace('A', 0));
    ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2);
  }
}
function drips(ctx, w, h, y0, n, col) {
  ctx.fillStyle = col;
  for (let i = 0; i < n; i++) {
    const x = Math.random() * w, len = rand(10, h * 0.5), wd = rand(1, 3.5);
    ctx.globalAlpha = rand(.15, .45);
    ctx.fillRect(x, y0, wd, len);
    ctx.beginPath(); ctx.arc(x + wd / 2, y0 + len, wd * 0.9, 0, 7); ctx.fill();
  }
  ctx.globalAlpha = 1;
}
function crack(ctx, x, y, len, ang, depth) {
  ctx.beginPath(); ctx.moveTo(x, y);
  for (let i = 0; i < 8; i++) {
    ang += rand(-.6, .6); x += Math.cos(ang) * len / 8; y += Math.sin(ang) * len / 8; ctx.lineTo(x, y);
    if (depth > 0 && Math.random() < .2) crack(ctx, x, y, len * .4, ang + rand(-1, 1), depth - 1);
  }
  ctx.stroke();
}
// renk dokusundan kabartma (normal) haritası üret: parlaklık = yükseklik
function normalFrom(src, strength = 2.5, invert = false) {
  const w = src.width, h = src.height;
  const d = src.getContext('2d').getImageData(0, 0, w, h).data;
  const H = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) { const v = (d[i * 4] * .3 + d[i * 4 + 1] * .59 + d[i * 4 + 2] * .11) / 255; H[i] = invert ? 1 - v : v; }
  const c = makeCanvas(w, h), x = c.getContext('2d'), img = x.createImageData(w, h), o = img.data;
  for (let y = 0; y < h; y++) for (let X = 0; X < w; X++) {
    const l = H[y * w + ((X - 1 + w) % w)], r = H[y * w + ((X + 1) % w)], u = H[((y - 1 + h) % h) * w + X], dn = H[((y + 1) % h) * w + X];
    let nx = (l - r) * strength, ny = (dn - u) * strength, nz = 1; const len = Math.hypot(nx, ny, nz);
    const i = (y * w + X) * 4; o[i] = (nx / len * .5 + .5) * 255; o[i + 1] = (ny / len * .5 + .5) * 255; o[i + 2] = (nz / len * .5 + .5) * 255; o[i + 3] = 255;
  }
  x.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; return t;
}
function wallTexture(variant) {
  const w = 512, h = 512, c = makeCanvas(w, h), x = c.getContext('2d');
  const top = variant === 2 ? '#6d6a5c' : variant === 1 ? '#5d6b62' : '#77786a';
  x.fillStyle = top; x.fillRect(0, 0, w, h);
  // alt yarı fayans
  const tileY = h * 0.55;
  const tc = variant === 2 ? '#7a776b' : '#8c9488';
  for (let ty = tileY; ty < h; ty += 32) for (let tx = 0; tx < w; tx += 32) {
    x.fillStyle = tc; x.fillRect(tx + 1, ty + 1, 30, 30);
    x.fillStyle = `rgba(0,0,0,${rand(0, .18)})`; x.fillRect(tx + 1, ty + 1, 30, 30);
  }
  x.fillStyle = '#2b2b25'; x.fillRect(0, tileY - 8, w, 8);   // bordür
  for (let i = 0; i < 9000; i++) { x.fillStyle = `rgba(${Math.random() < .5 ? 0 : 255},${Math.random() < .5 ? 0 : 255},0,${rand(0, .04)})`; x.fillRect(Math.random() * w, Math.random() * h, 2, 2); }
  grime(x, w, h, 40, 'rgba(25,20,10,A)', 20, 120, .55);
  grime(x, w, h, 12, 'rgba(40,50,20,A)', 30, 90, .35); // küf
  x.fillStyle = 'rgba(20,15,5,.55)'; x.fillRect(0, h - 40, w, 40);
  drips(x, w, h, 0, 30, '#1a1408');
  x.strokeStyle = 'rgba(10,8,5,.7)'; x.lineWidth = 1.2;
  for (let i = 0; i < 4; i++) crack(x, Math.random() * w, Math.random() * h * .5, rand(60, 200), rand(0, 6), 2);
  if (variant === 2 || Math.random() < .5) { // kan
    grime(x, w, h, 3, 'rgba(90,0,0,A)', 10, 50, .7);
    drips(x, w, h, rand(100, 250), 6, '#4a0303');
  }
  // soyulan boya
  for (let i = 0; i < 14; i++) {
    x.fillStyle = 'rgba(45,40,30,.6)';
    x.beginPath(); const px = Math.random() * w, py = Math.random() * tileY;
    x.moveTo(px, py); for (let k = 0; k < 7; k++) x.lineTo(px + rand(-25, 25), py + rand(-18, 18)); x.fill();
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t;
}
function floorTexture() {
  const w = 512, h = 512, c = makeCanvas(w, h), x = c.getContext('2d');
  const s = 64;
  for (let ty = 0; ty < h; ty += s) for (let tx = 0; tx < w; tx += s) {
    const dark = ((tx + ty) / s) % 2 === 0;
    x.fillStyle = dark ? '#3a3a35' : '#8a8676'; x.fillRect(tx, ty, s, s);
    x.fillStyle = `rgba(0,0,0,${rand(0, .25)})`; x.fillRect(tx, ty, s, s);
    x.strokeStyle = 'rgba(0,0,0,.6)'; x.strokeRect(tx + .5, ty + .5, s - 1, s - 1);
  }
  for (let i = 0; i < 12000; i++) { x.fillStyle = `rgba(0,0,0,${rand(0, .08)})`; x.fillRect(Math.random() * w, Math.random() * h, 2, 2); }
  grime(x, w, h, 60, 'rgba(20,15,8,A)', 20, 110, .6);
  if (Math.random() < .7) grime(x, w, h, 2, 'rgba(70,0,0,A)', 15, 45, .8);
  x.strokeStyle = 'rgba(0,0,0,.6)'; for (let i = 0; i < 6; i++) crack(x, Math.random() * w, Math.random() * h, rand(40, 160), rand(0, 6), 1);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 4; return t;
}
function ceilTexture() {
  const w = 256, h = 256, c = makeCanvas(w, h), x = c.getContext('2d');
  x.fillStyle = '#5a584e'; x.fillRect(0, 0, w, h);
  x.strokeStyle = '#2a2925'; x.lineWidth = 3;
  for (let i = 0; i <= w; i += 64) { x.beginPath(); x.moveTo(i, 0); x.lineTo(i, h); x.stroke(); x.beginPath(); x.moveTo(0, i); x.lineTo(w, i); x.stroke(); }
  grime(x, w, h, 30, 'rgba(50,35,10,A)', 10, 60, .55);
  for (let i = 0; i < 3; i++) { x.fillStyle = '#111'; x.fillRect(((Math.random() * 4) | 0) * 64 + 2, ((Math.random() * 4) | 0) * 64 + 2, 60, 60); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; return t;
}
function doorTexture(electric) {
  const w = 256, h = 512, c = makeCanvas(w, h), x = c.getContext('2d');
  x.fillStyle = electric ? '#3b4148' : '#5b4a36'; x.fillRect(0, 0, w, h);
  for (let i = 0; i < 4000; i++) { x.fillStyle = `rgba(0,0,0,${rand(0, .12)})`; x.fillRect(Math.random() * w, Math.random() * h, 1, rand(2, 20)); }
  x.strokeStyle = 'rgba(0,0,0,.6)'; x.lineWidth = 6; x.strokeRect(24, 30, w - 48, h - 60);
  if (!electric) { x.fillStyle = '#0c0d0e'; x.fillRect(70, 70, 116, 120); x.strokeStyle = '#333'; x.strokeRect(70, 70, 116, 120); }
  else { x.fillStyle = '#ffcc00'; for (let i = 0; i < 8; i++) { x.save(); x.translate(0, 420 + (i % 2) * 0); x.restore(); } x.fillStyle = 'rgba(255,200,0,.8)'; x.font = 'bold 28px monospace'; x.fillText('YETKİLİ', 60, 250); }
  grime(x, w, h, 20, 'rgba(10,5,0,A)', 20, 90, .6);
  drips(x, w, h, 200, 5, '#3a0202');
  x.fillStyle = '#a89a70'; x.beginPath(); x.arc(w - 40, h / 2 + 20, 10, 0, 7); x.fill();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function textDecal(text, size, color, w = 1024, h = 256) {
  const c = makeCanvas(w, h), x = c.getContext('2d');
  x.font = `${size}px Creepster, "Special Elite", cursive`;
  x.textAlign = 'center'; x.textBaseline = 'middle';
  x.fillStyle = color; x.shadowColor = color; x.shadowBlur = 6;
  x.fillText(text, w / 2, h / 2 - 20);
  // akıntılar
  x.shadowBlur = 0;
  const m = x.measureText(text).width;
  for (let i = 0; i < 26; i++) {
    const dx = w / 2 - m / 2 + Math.random() * m, len = rand(10, 90), wd = rand(2, 5);
    x.globalAlpha = rand(.5, .9); x.fillRect(dx, h / 2, wd, len);
    x.beginPath(); x.arc(dx + wd / 2, h / 2 + len, wd, 0, 7); x.fill();
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function skinTexture() {
  const w = 256, h = 256, c = makeCanvas(w, h), x = c.getContext('2d');
  x.fillStyle = '#8f877a'; x.fillRect(0, 0, w, h);
  grime(x, w, h, 50, 'rgba(60,50,45,A)', 8, 40, .6);
  grime(x, w, h, 20, 'rgba(110,60,70,A)', 6, 30, .35);
  grime(x, w, h, 12, 'rgba(160,150,130,A)', 10, 40, .4);
  x.strokeStyle = 'rgba(70,20,50,.55)'; x.lineWidth = 1.3;
  for (let i = 0; i < 26; i++) crack(x, Math.random() * w, Math.random() * h, rand(30, 90), rand(0, 6), 2);
  for (let i = 0; i < 3000; i++) { x.fillStyle = `rgba(30,20,20,${rand(0, .15)})`; x.fillRect(Math.random() * w, Math.random() * h, 1, 1); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; return t;
}
function noteTexture() {
  const c = makeCanvas(64, 80), x = c.getContext('2d');
  x.fillStyle = '#cdbf9c'; x.fillRect(0, 0, 64, 80);
  x.fillStyle = '#332'; for (let i = 0; i < 9; i++) x.fillRect(8, 10 + i * 7, rand(30, 48), 1.5);
  x.fillStyle = 'rgba(120,0,0,.5)'; x.beginPath(); x.arc(50, 62, 8, 0, 7); x.fill();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

/* ------------------------------ DÜNYA ------------------------------- */
const world = new THREE.Group(); scene.add(world);
const wallMats = [0, 1, 2].map(v => { const map = wallTexture(v); return new THREE.MeshStandardMaterial({ map, normalMap: normalFrom(map.image, 3), normalScale: new THREE.Vector2(.9, .9), roughness: .88, metalness: 0 }); });
const floorTex = floorTexture(); floorTex.repeat.set(GW * C / 3.2, GH * C / 3.2);
const floorNorm = normalFrom(floorTex.image, 2.2); floorNorm.repeat.copy(floorTex.repeat);
const floorRough = (() => { // ıslak su birikintileri: fenerde parlar
  const w = 256, c = makeCanvas(w, w), x = c.getContext('2d');
  x.fillStyle = 'rgb(200,200,200)'; x.fillRect(0, 0, w, w);
  for (let i = 0; i < 7; i++) {
    const px = Math.random() * w, py = Math.random() * w, r = rand(14, 46);
    const g = x.createRadialGradient(px, py, 0, px, py, r); g.addColorStop(0, 'rgb(20,20,20)'); g.addColorStop(.7, 'rgb(40,40,40)'); g.addColorStop(1, 'rgba(200,200,200,0)');
    x.fillStyle = g; x.beginPath(); x.ellipse(px, py, r, r * rand(.5, 1), rand(0, 3), 0, 7); x.fill();
  }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(GW * C / 7, GH * C / 7); return t;
})();
const ceilTex = ceilTexture(); ceilTex.repeat.set(GW * C / 2.4, GH * C / 2.4);
const ceilNorm = normalFrom(ceilTex.image, 3); ceilNorm.repeat.copy(ceilTex.repeat);
const floorMat = new THREE.MeshStandardMaterial({ map: floorTex, normalMap: floorNorm, roughnessMap: floorRough, roughness: 1, metalness: .08 });
const ceilMat = new THREE.MeshStandardMaterial({ map: ceilTex, normalMap: ceilNorm, roughness: 1 });

{ // zemin ve tavan
  const fg = new THREE.PlaneGeometry(GW * C, GH * C);
  const floor = new THREE.Mesh(fg, floorMat); floor.rotation.x = -Math.PI / 2; floor.position.set(GW * C / 2, 0, GH * C / 2); floor.receiveShadow = true; world.add(floor);
  const ceil = new THREE.Mesh(fg, ceilMat); ceil.rotation.x = Math.PI / 2; ceil.position.set(GW * C / 2, WALL_H, GH * C / 2); world.add(ceil);
}
{ // duvarlar: 3 varyantlı instanced kutular (yalnızca boşluğa bakan duvarlar)
  const walls = [[], [], []];
  for (let z = 0; z < GH; z++) for (let x = 0; x < GW; x++) {
    const ch = cellAt(x, z);
    if (ch !== '#') continue;
    let exposed = false;
    for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const n = cellAt(x + dx, z + dz); if (n !== '#' && n !== 'E') exposed = true; }
    if (!exposed) continue;
    const r = roomOf(x, z);
    let v = (x * 7 + z * 13) % 5 === 0 ? 2 : ((x + z) % 3 === 0 ? 1 : 0);
    if (r && (r.n === 'Morg' || r.n === 'Ameliyathane')) v = 2;
    walls[v].push([x, z]);
  }
  const bg = new THREE.BoxGeometry(C, WALL_H, C);
  const m4 = new THREE.Matrix4();
  walls.forEach((list, v) => {
    const im = new THREE.InstancedMesh(bg, wallMats[v], list.length);
    list.forEach(([x, z], i) => { m4.makeTranslation(cc(x), WALL_H / 2, cc(z)); im.setMatrixAt(i, m4); });
    im.castShadow = true; im.receiveShadow = true; world.add(im);
  });
}

/* --------------------------- MALZEMELER ----------------------------- */
const M = {
  metal: new THREE.MeshStandardMaterial({ color: 0x7c8086, roughness: .55, metalness: .7 }),
  rust: new THREE.MeshStandardMaterial({ color: 0x5a3b26, roughness: .9, metalness: .4 }),
  sheet: new THREE.MeshStandardMaterial({ color: 0xb8b2a0, roughness: 1 }),
  bloodSheet: new THREE.MeshStandardMaterial({ color: 0x9a8a7a, roughness: 1 }),
  wood: new THREE.MeshStandardMaterial({ color: 0x4a3524, roughness: .85 }),
  dark: new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 1 }),
  locker: new THREE.MeshStandardMaterial({ color: 0x48585a, roughness: .6, metalness: .5 }),
  hair: new THREE.MeshStandardMaterial({ color: 0x050505, roughness: .3, metalness: .2, side: THREE.DoubleSide }),
  bone: new THREE.MeshStandardMaterial({ color: 0xcdbf9e, roughness: .55 }),
  skin: new THREE.MeshStandardMaterial({ map: skinTexture(), color: 0x6f675e, roughness: .38, metalness: .05 }),
  skinDark: new THREE.MeshStandardMaterial({ color: 0x3a302a, roughness: .7 }),
  maw: new THREE.MeshBasicMaterial({ color: 0x200303 }),
  gum: new THREE.MeshStandardMaterial({ color: 0x3a0608, roughness: .25 }),
  teeth: new THREE.MeshStandardMaterial({ color: 0xd8d0b0, roughness: .4 }),
  mouth: new THREE.MeshBasicMaterial({ color: 0x080000 }),
  blood: new THREE.MeshStandardMaterial({ color: 0x3a0000, roughness: .3, metalness: .1 }),
  mannequin: new THREE.MeshStandardMaterial({ color: 0xc8bba4, roughness: .5 }),
  fuse: new THREE.MeshStandardMaterial({ color: 0xd8c040, roughness: .4, metalness: .6, emissive: 0x3a2a00 }),
  card: new THREE.MeshStandardMaterial({ color: 0xd0d8e0, roughness: .3, emissive: 0x102030 }),
  batt: new THREE.MeshStandardMaterial({ color: 0x206030, roughness: .4, metalness: .5, emissive: 0x041a08 }),
  glass: new THREE.MeshStandardMaterial({ color: 0x2c5a3a, roughness: .1, metalness: .2, transparent: true, opacity: .8 }),
  paper: new THREE.MeshStandardMaterial({ map: noteTexture(), roughness: 1, side: THREE.DoubleSide, emissive: 0x2a2418 }),
  lampOn: new THREE.MeshBasicMaterial({ color: 0xfff0c8 }),
  lampOff: new THREE.MeshStandardMaterial({ color: 0x333028 }),
  red: new THREE.MeshBasicMaterial({ color: 0xff2010 }),
  green: new THREE.MeshBasicMaterial({ color: 0x20ff40 }),
};
const box = (w, h, d, mat) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat); m.castShadow = true; m.receiveShadow = true; return m; };
const cyl = (rt, rb, h, mat, s = 10) => { const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, s), mat); m.castShadow = true; return m; };

// çarpışma kutuları (oyuncu için) — XZ düzleminde AABB
const solids = [];
function addSolid(x, z, hw, hd, tag) { const s = { x0: x - hw, x1: x + hw, z0: z - hd, z1: z + hd, tag }; solids.push(s); return s; }

/* -------- duvara yaslı nesne yerleşimi: en yakın duvarın yönünü bul ---- */
function wallDir(x, z) {
  // önce duvar olan yönler
  const dirs = [[0, -1], [1, 0], [0, 1], [-1, 0]];
  for (const [dx, dz] of dirs) if (cellAt(x + dx, z + dz) === '#') return [dx, dz];
  return [0, -1];
}

/* -------------------------- KAPILAR -------------------------------- */
const doors = [];
const doorTex = doorTexture(false), elecTex = doorTexture(true);
function buildDoor(x, z, electric) {
  const ew = cellAt(x - 1, z) === '#' && cellAt(x + 1, z) === '#'; // kapı x ekseninde uzanıyor
  const pivot = new THREE.Group();
  const dw = C * 0.62, dh = 2.45;
  const mat = new THREE.MeshStandardMaterial({ map: electric ? elecTex : doorTex, roughness: .8, metalness: electric ? .6 : .1 });
  const panel = box(dw, dh, 0.09, mat);
  panel.position.set(dw / 2, dh / 2, 0);
  pivot.add(panel);
  // kapı çerçevesi + üst duvar
  const frame = new THREE.Group();
  const side = (C - dw) / 2;
  const left = box(side, WALL_H, 0.5, wallMats[0]); left.position.set(-C / 2 + side / 2, WALL_H / 2, 0);
  const right = box(side, WALL_H, 0.5, wallMats[0]); right.position.set(C / 2 - side / 2, WALL_H / 2, 0);
  const top = box(dw, WALL_H - dh, 0.5, wallMats[0]); top.position.set(0, dh + (WALL_H - dh) / 2, 0);
  frame.add(left, right, top);
  frame.position.set(cc(x), 0, cc(z));
  if (!ew) frame.rotation.y = Math.PI / 2;
  world.add(frame);
  pivot.position.set(cc(x), 0, cc(z));
  if (ew) pivot.position.x -= dw / 2; else { pivot.rotation.y = Math.PI / 2; pivot.position.z += dw / 2; }
  world.add(pivot);
  const baseRot = pivot.rotation.y;
  let light = null;
  if (electric) {
    light = box(0.12, 0.12, 0.05, M.red);
    light.position.set(dw + 0.18, 1.35, 0.3); pivot.add(light);
  }
  // yan duvar parçaları için çarpışma
  if (ew) { addSolid(cc(x) - C / 2 + side / 2, cc(z), side / 2, 0.25); addSolid(cc(x) + C / 2 - side / 2, cc(z), side / 2, 0.25); }
  else { addSolid(cc(x), cc(z) - C / 2 + side / 2, 0.25, side / 2); addSolid(cc(x), cc(z) + C / 2 - side / 2, 0.25, side / 2); }
  const d = { x, z, ew, pivot, baseRot, open: 0, target: 0, electric, locked: electric, light, swing: 1, id: doors.length, slamT: 0 };
  doors.push(d);
  return d;
}
const doorAt = (x, z) => doors.find(d => d.x === x && d.z === z);

/* --------------------------- DOLAPLAR ------------------------------- */
const lockers = [];
function buildLocker(x, z, hideable = true) {
  const [dx, dz] = wallDir(x, z);
  const g = new THREE.Group();
  const body = box(1.0, 2.2, 0.75, M.locker); body.position.y = 1.1; g.add(body);
  const doorPivot = new THREE.Group(); doorPivot.position.set(-0.5, 0, 0.38); g.add(doorPivot);
  const dpanel = box(1.0, 2.15, 0.05, M.locker); dpanel.position.set(0.5, 1.1, 0); doorPivot.add(dpanel);
  for (let i = 0; i < 6; i++) { const s = box(0.6, 0.03, 0.02, M.dark); s.position.set(0.5, 1.75 + i * 0.07 - 0.0, 0.03); doorPivot.add(s); }
  const k = box(0.05, 0.15, 0.04, M.metal); k.position.set(0.88, 1.1, 0.04); doorPivot.add(k);
  // duvara yasla
  const px = cc(x) + dx * (C / 2 - 0.42), pz = cc(z) + dz * (C / 2 - 0.42);
  g.position.set(px, 0, pz);
  g.rotation.y = Math.atan2(-dx, -dz);
  world.add(g);
  const solid = addSolid(px, pz, Math.abs(dx) ? 0.4 : 0.52, Math.abs(dz) ? 0.4 : 0.52, 'locker');
  const facing = new THREE.Vector3(-dx, 0, -dz);
  const L = { x, z, g, doorPivot, hideable, pos: new THREE.Vector3(px, 0, pz), facing, solid, open: 0, target: 0 };
  lockers.push(L);
  return L;
}

/* ----------------------------- DEKOR -------------------------------- */
function bed(x, z, rot, bloody) {
  const g = new THREE.Group();
  const frame = box(1.0, 0.08, 2.1, M.rust); frame.position.y = 0.55; g.add(frame);
  const mat = box(0.92, 0.16, 1.95, bloody ? M.bloodSheet : M.sheet); mat.position.y = 0.67; g.add(mat);
  for (const [lx, lz] of [[-.45, -1], [.45, -1], [-.45, 1], [.45, 1]]) { const l = cyl(.025, .025, .55, M.rust, 6); l.position.set(lx, .27, lz); g.add(l); }
  const head = box(1.0, 0.7, 0.05, M.rust); head.position.set(0, 0.85, -1.05); g.add(head);
  if (bloody) { const b = new THREE.Mesh(new THREE.CircleGeometry(.35, 12), M.blood); b.rotation.x = -Math.PI / 2; b.position.set(.1, .76, .2); g.add(b); }
  g.position.set(x, 0, z); g.rotation.y = rot; world.add(g);
  const s = Math.abs(Math.sin(rot)) > .5;
  addSolid(x, z, s ? 1.05 : .5, s ? .5 : 1.05);
  return g;
}
function wheelchair() {
  const g = new THREE.Group();
  const seat = box(.5, .05, .5, M.dark); seat.position.y = .5; g.add(seat);
  const back = box(.5, .55, .05, M.dark); back.position.set(0, .8, -.25); g.add(back);
  for (const sx of [-.3, .3]) {
    const w = new THREE.Mesh(new THREE.TorusGeometry(.3, .025, 6, 18), M.metal); w.rotation.y = Math.PI / 2; w.position.set(sx, .3, -.05); g.add(w);
    const h = cyl(.015, .015, .5, M.metal, 5); h.rotation.x = Math.PI / 2; h.position.set(sx * .8, .9, -.45); g.add(h);
  }
  for (const sx of [-.2, .2]) { const w = cyl(.07, .07, .03, M.dark, 8); w.rotation.z = Math.PI / 2; w.position.set(sx, .07, .3); g.add(w); }
  world.add(g); return g;
}
function table(x, z, w, d) {
  const g = new THREE.Group();
  const top = box(w, .06, d, M.wood); top.position.y = .76; g.add(top);
  for (const [lx, lz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) { const l = box(.06, .76, .06, M.rust); l.position.set(lx * (w / 2 - .06), .38, lz * (d / 2 - .06)); g.add(l); }
  g.position.set(x, 0, z); world.add(g); addSolid(x, z, w / 2, d / 2); return g;
}
function chair(x, z, rot, fallen) {
  const g = new THREE.Group();
  const s = box(.42, .04, .42, M.wood); s.position.y = .45; g.add(s);
  const b = box(.42, .45, .04, M.wood); b.position.set(0, .7, -.2); g.add(b);
  for (const [lx, lz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) { const l = box(.03, .45, .03, M.rust); l.position.set(lx * .18, .22, lz * .18); g.add(l); }
  g.position.set(x, 0, z); g.rotation.y = rot;
  if (fallen) { g.rotation.z = Math.PI / 2; g.position.y = .22; }
  world.add(g); return g;
}
function cabinet(x, z, w = 1.2, h = 1.8) {
  const [dx, dz] = wallDir(toCell(x), toCell(z));
  const g = box(Math.abs(dz) ? w : .5, h, Math.abs(dz) ? .5 : w, M.rust);
  const px = x + dx * (C / 2 - .3), pz = z + dz * (C / 2 - .3);
  g.position.set(px, h / 2, pz); world.add(g);
  addSolid(px, pz, Math.abs(dz) ? w / 2 : .25, Math.abs(dz) ? .25 : w / 2);
  return g;
}
function bloodPool(x, z, r) { const b = new THREE.Mesh(new THREE.CircleGeometry(r, 16), M.blood); b.rotation.x = -Math.PI / 2; b.position.set(x, .012 + Math.random() * .004, z); b.scale.set(1, rand(.6, 1.2), 1); world.add(b); return b; }
function bloodTrail(x0, z0, x1, z1) { const n = Math.ceil(Math.hypot(x1 - x0, z1 - z0) / .45); for (let i = 0; i < n; i++) { const t = i / n; bloodPool(lerp(x0, x1, t) + rand(-.15, .15), lerp(z0, z1, t) + rand(-.15, .15), rand(.08, .22)); } }
function wallText(text, x, z, dirx, dirz, h = 1.7, w = 2.6) {
  const tex = textDecal(text, 150, '#7a0606');
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, w / 4), new THREE.MeshStandardMaterial({ map: tex, transparent: true, roughness: .5, depthWrite: false }));
  m.position.set(x - dirx * (C / 2 - .02) , h, z - dirz * (C / 2 - .02));
  m.lookAt(m.position.x + dirx, h, m.position.z + dirz);
  world.add(m); return m;
}

/* ------------------------- MANKEN / CESET --------------------------- */
function humanoid(mat, scale = 1) {
  const g = new THREE.Group();
  const torso = box(.42, .62, .24, mat); torso.position.y = 1.18; g.add(torso);
  const hips = box(.38, .2, .22, mat); hips.position.y = .82; g.add(hips);
  const head = new THREE.Mesh(new THREE.SphereGeometry(.14, 12, 10), mat); head.scale.set(1, 1.25, 1.05); head.position.y = 1.68; head.castShadow = true; g.add(head);
  const neck = cyl(.05, .06, .12, mat, 6); neck.position.y = 1.53; g.add(neck);
  const limbs = {};
  for (const s of [-1, 1]) {
    const arm = new THREE.Group(); arm.position.set(s * .27, 1.45, 0);
    const ua = cyl(.05, .045, .32, mat, 6); ua.position.y = -.16; arm.add(ua);
    const fa = new THREE.Group(); fa.position.y = -.32; arm.add(fa);
    const lo = cyl(.045, .035, .3, mat, 6); lo.position.y = -.15; fa.add(lo);
    g.add(arm);
    const leg = new THREE.Group(); leg.position.set(s * .11, .78, 0);
    const ul = cyl(.07, .06, .4, mat, 6); ul.position.y = -.2; leg.add(ul);
    const ll = cyl(.055, .045, .38, mat, 6); ll.position.y = -.58; leg.add(ll);
    g.add(leg);
    limbs[s < 0 ? 'la' : 'ra'] = arm; limbs[s < 0 ? 'll' : 'rl'] = leg; limbs[s < 0 ? 'lfa' : 'rfa'] = fa;
  }
  g.userData = { head, torso, limbs };
  g.scale.setScalar(scale);
  return g;
}

/* ---------------------------- YARATIK ------------------------------- */
// Uzun, sıska, kambur, gözsüz; yüzünün yarısı ağız.
function buildMonster(silhouette = false) {
  const skin = silhouette ? new THREE.MeshBasicMaterial({ color: 0x000000 }) : M.skin;
  const dark = silhouette ? skin : M.skinDark;
  const g = new THREE.Group();
  const body = new THREE.Group(); g.add(body);
  // gövde: kaburgalı
  const spine = new THREE.Group(); spine.position.y = 1.35; body.add(spine);
  const chest = new THREE.Mesh(new THREE.SphereGeometry(.2, 14, 12), skin); chest.scale.set(1, 1.55, .62); chest.position.y = .56; chest.castShadow = true; spine.add(chest);
  const belly = new THREE.Mesh(new THREE.SphereGeometry(.12, 12, 10), skin); belly.scale.set(1, 1.6, .7); belly.position.set(0, .16, -.02); spine.add(belly);
  for (const s of [-1, 1]) { const sc = new THREE.Mesh(new THREE.SphereGeometry(.07, 8, 6), skin); sc.position.set(s * .2, .76, -.03); sc.scale.set(1.2, .8, 1); spine.add(sc); }
  for (let i = 0; i < 6; i++) { const r = new THREE.Mesh(new THREE.TorusGeometry(.19 - i * .014, .011, 5, 14, Math.PI), skin); r.position.set(0, .78 - i * .085, .045); r.rotation.set(Math.PI / 2 + .25, 0, 0); r.scale.y = .62; spine.add(r); }
  const pelvis = new THREE.Mesh(new THREE.CylinderGeometry(.15, .18, .3, 8), skin); pelvis.position.y = 1.25; pelvis.scale.z = .7; body.add(pelvis);
  // boyun + kafa
  const neck = new THREE.Group(); neck.position.y = .9; spine.add(neck);
  const neckM = cyl(.05, .075, .44, skin, 7); neckM.position.y = .2; neck.add(neckM);
  for (const s of [-1, 1]) { const tn = cyl(.012, .016, .42, skin, 4); tn.position.set(s * .04, .2, .035); tn.rotation.z = s * .12; neck.add(tn); }
  const head = new THREE.Group(); head.position.y = .44; neck.add(head);
  for (let i = 0; i < 9; i++) { const v = new THREE.Mesh(new THREE.ConeGeometry(.03, .09, 5), silhouette ? skin : M.bone); v.position.set(0, .05 + i * .1, -.13 + Math.sin(i * .4) * .01); v.rotation.x = -Math.PI / 2 - .3; spine.add(v); }
  const bone = silhouette ? skin : M.bone;
  const skull = new THREE.Mesh(new THREE.SphereGeometry(.2, 20, 16), skin); skull.scale.set(.78, 1.32, 1.05); skull.position.y = .3; skull.castShadow = true; head.add(skull);
  // kafatası dışarı çıkmış: yırtık deri altından kemik
  const bonePatch = new THREE.Mesh(new THREE.SphereGeometry(.172, 12, 10, 0, 1.6, .2, 1.1), bone); bonePatch.scale.set(.82, 1.3, 1.06); bonePatch.position.set(.008, .31, -.004); bonePatch.rotation.y = -.4; head.add(bonePatch);
  for (let i = 0; i < 5; i++) { const sh = box(.006, rand(.03, .07), .006, M.blood); sh.position.set(rand(.03, .12), rand(.36, .52), rand(.06, .14)); sh.rotation.z = rand(-.8, .8); head.add(sh); }
  const hole = silhouette ? skin : M.mouth;
  // gözler: biri dikilmiş, diğeri dipsiz bir oyuk
  const sockR = new THREE.Mesh(new THREE.CircleGeometry(.042, 9), hole); sockR.position.set(.07, .33, .196); sockR.rotation.set(-.12, .4, .35); sockR.scale.set(1.15, 1.45, 1); head.add(sockR);
  for (let k = 0; k < 4; k++) { const tear = box(.008, rand(.08, .2), .004, hole); tear.position.set(.07 + rand(-.02, .02), .25 - k * .01, .2); tear.rotation.z = rand(-.15, .15); head.add(tear); }
  const lid = box(.075, .012, .01, M.skinDark); lid.position.set(-.07, .33, .2); lid.rotation.set(0, -.4, -.3); head.add(lid);
  for (let k = 0; k < 5; k++) { const st = box(.004, .04, .012, M.dark); st.position.set(-.1 + k * .015, .33 - k * .006, .203); st.rotation.set(0, -.4, -.3); head.add(st); }
  const split = box(.012, .2, .012, hole); split.position.set(0, .47, .16); split.rotation.x = -.5; head.add(split);
  // ıslak, uzun, seyrek saç (arkada ve yanlarda)
  const hairMat = silhouette ? skin : M.hair;
  for (let i = 0; i < 46; i++) {
    const a = rand(-Math.PI, Math.PI), front = Math.cos(a) > .5;
    if (front && Math.random() < .75) continue;
    const L = rand(.4, front ? .6 : 1.0);
    const h = box(rand(.006, .016), L, .004, hairMat);
    h.position.set(Math.sin(a) * .15, .5 - L / 2, Math.cos(a) * .16 + (front ? .04 : 0));
    h.rotation.set(front ? -.12 : rand(-.12, .12), a, rand(-.08, .08)); head.add(h);
  }
  const scalp = new THREE.Mesh(new THREE.SphereGeometry(.165, 12, 8, Math.PI * .1, Math.PI * 1.3, 0, Math.PI / 2.4), hairMat); scalp.scale.set(.85, 1.2, 1.05); scalp.position.y = .36; scalp.rotation.y = Math.PI * .55; head.add(scalp);
  for (let i = 0; i < 10; i++) { // damarlar
    const v = box(.006, rand(.06, .16), .006, M.blood); const a = rand(-1, 1), y = rand(.18, .48);
    v.position.set(Math.sin(a) * .15, y, Math.cos(a) * .175); v.rotation.set(rand(-.5, .5), a, rand(-.9, .9)); head.add(v);
  }
  // kulaklara kadar yırtılmış ağız kenarları
  for (const s of [-1, 1]) { const cut = box(.1, .012, .012, hole); cut.position.set(s * .13, .13, .1); cut.rotation.set(0, s * -.9, s * .45); head.add(cut); }
  // üst çene ve iğne dişler (iki sıra)
  const maxilla = new THREE.Mesh(new THREE.CylinderGeometry(.11, .145, .1, 18), skin); maxilla.position.set(0, .085, .04); maxilla.castShadow = true; head.add(maxilla);
  const palate = new THREE.Mesh(new THREE.CircleGeometry(.132, 18), silhouette ? skin : M.gum); palate.rotation.x = Math.PI / 2; palate.position.set(0, .034, .04); head.add(palate);
  for (let row = 0; row < 2; row++) for (let i = 0; i < 17; i++) {
    const a = (i / 16 - .5) * 2.7, L = rand(.05, .12) * (row ? .7 : 1), r = row ? .1 : .128;
    const t = new THREE.Mesh(new THREE.ConeGeometry(row ? .008 : .011, L, 4), M.teeth);
    t.position.set(Math.sin(a) * r, .036 - L / 2, .04 + Math.cos(a) * r); t.rotation.set(Math.PI + rand(-.2, .2), 0, rand(-.2, .2)); head.add(t);
  }
  const maw = new THREE.Mesh(new THREE.SphereGeometry(.1, 12, 10), silhouette ? skin : M.maw); maw.position.set(0, -.01, .03); head.add(maw);
  // boğazda halka diş
  for (let i = 0; i < 10; i++) { const a = i / 10 * Math.PI * 2; const t = new THREE.Mesh(new THREE.ConeGeometry(.008, .05, 4), M.teeth); t.position.set(Math.cos(a) * .05, -.02 + Math.sin(a) * .04, -.01); t.rotation.set(Math.PI / 2, 0, a); head.add(t); }
  // alt çene ikiye ayrılır: iki yarım, yana ve aşağı açılır
  const jaw = new THREE.Group(); jaw.position.set(0, .05, -.06); head.add(jaw);
  const halves = [];
  for (const s of [-1, 1]) {
    const hv = new THREE.Group(); hv.position.set(s * .02, 0, 0); jaw.add(hv);
    const m = new THREE.Mesh(new THREE.SphereGeometry(.14, 12, 8, s < 0 ? -Math.PI / 2 : Math.PI / 2, Math.PI, Math.PI / 2, Math.PI / 2), skin);
    m.scale.set(.95, .9, 1.02); m.position.set(-s * .02, 0, .1); hv.add(m);
    const gum = new THREE.Mesh(new THREE.CircleGeometry(.12, 12, s < 0 ? Math.PI / 2 : -Math.PI / 2, Math.PI), silhouette ? skin : M.gum); gum.rotation.x = -Math.PI / 2; gum.position.set(-s * .02, -.004, .1); hv.add(gum);
    for (let i = 0; i < 9; i++) {
      const a = s * (i / 8) * 1.3, L = rand(.045, .1);
      const b = new THREE.Mesh(new THREE.ConeGeometry(.01, L, 4), M.teeth);
      b.position.set(Math.sin(a) * .118 - s * .02, L / 2 - .005, .1 + Math.cos(a) * .118); b.rotation.set(rand(-.2, .2), 0, rand(-.2, .2)); hv.add(b);
    }
    halves.push(hv);
  }
  const tongue = new THREE.Mesh(new THREE.SphereGeometry(.05, 8, 6), silhouette ? skin : M.gum); tongue.position.set(0, -.02, .12); tongue.scale.set(1, .45, 2.4); jaw.add(tongue);
  const mouth = maw;
  // kollar: çok uzun, pençeli
  const arms = [];
  for (const s of [-1, 1]) {
    const sh = new THREE.Group(); sh.position.set(s * .27, .78, 0); spine.add(sh);
    const ua = cyl(.05, .034, .7, skin, 9); ua.position.y = -.35; sh.add(ua);
    const el = new THREE.Group(); el.position.y = -.7; sh.add(el);
    const knob = new THREE.Mesh(new THREE.SphereGeometry(.042, 8, 6), skin); el.add(knob);
    const fa = cyl(.036, .022, .75, skin, 9); fa.position.y = -.37; el.add(fa);
    const hand = new THREE.Group(); hand.position.y = -.75; el.add(hand);
    for (let f = 0; f < 4; f++) {
      const fg = new THREE.Mesh(new THREE.ConeGeometry(.011, .34, 4), dark);
      fg.position.set((f - 1.5) * .025, -.12, .02); fg.rotation.x = .25; fg.rotation.z = (f - 1.5) * .12; hand.add(fg);
    }
    arms.push({ sh, el, hand, s });
  }
  // bacaklar: ters dizli
  const legs = [];
  for (const s of [-1, 1]) {
    const hip = new THREE.Group(); hip.position.set(s * .13, 1.2, 0); body.add(hip);
    const th = cyl(.065, .04, .62, skin, 9); th.position.y = -.31; hip.add(th);
    const kn = new THREE.Group(); kn.position.y = -.62; hip.add(kn);
    const kb = new THREE.Mesh(new THREE.SphereGeometry(.05, 8, 6), skin); kn.add(kb);
    const sh = cyl(.04, .025, .6, skin, 9); sh.position.y = -.3; kn.add(sh);
    const ft = box(.08, .04, .22, dark); ft.position.set(0, -.6, .06); kn.add(ft);
    legs.push({ hip, kn, s });
  }
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  body.scale.setScalar(.8);
  g.userData = { body, spine, neck, head, jaw, halves, arms, legs, mouth };
  return g;
}

/* ===================================================================
   SES MOTORU — her şey WebAudio ile sentezleniyor
   =================================================================== */
const A = {
  ctx: null, master: null, comp: null, noise: null, rev: null, revSend: null,
  init() {
    if (this.ctx) return;
    const ctx = this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.comp = ctx.createDynamicsCompressor(); this.comp.threshold.value = -14; this.comp.ratio.value = 6;
    this.master = ctx.createGain(); this.master.gain.value = volume;
    this.master.connect(this.comp); this.comp.connect(ctx.destination);
    // beyaz gürültü
    const len = ctx.sampleRate * 2, buf = ctx.createBuffer(1, len, ctx.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    this.noise = buf;
    // kahverengi gürültü
    const bb = ctx.createBuffer(1, len, ctx.sampleRate), bd = bb.getChannelData(0); let last = 0;
    for (let i = 0; i < len; i++) { last = (last + .02 * (Math.random() * 2 - 1)) / 1.02; bd[i] = last * 3.5; }
    this.brown = bb;
    // yankı (koridor)
    const rl = ctx.sampleRate * 2.6, rb = ctx.createBuffer(2, rl, ctx.sampleRate);
    for (let ch = 0; ch < 2; ch++) { const rd = rb.getChannelData(ch); for (let i = 0; i < rl; i++) rd[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / rl, 2.6); }
    this.rev = ctx.createConvolver(); this.rev.buffer = rb;
    this.revSend = ctx.createGain(); this.revSend.gain.value = .45;
    this.revSend.connect(this.rev); this.rev.connect(this.master);
    // distorsiyon eğrisi
    const curve = new Float32Array(1024); for (let i = 0; i < 1024; i++) { const x = i / 512 - 1; curve[i] = Math.tanh(x * 6); }
    this.curve = curve;
  },
  get t() { return this.ctx.currentTime; },
  out(dest, wet = .3) { // kuru + yankı
    const g = this.ctx.createGain(); g.connect(dest || this.master);
    if (wet > 0) { const s = this.ctx.createGain(); s.gain.value = wet; g.connect(s); s.connect(this.revSend); }
    return g;
  },
  panner(pos) {
    const p = this.ctx.createPanner();
    p.panningModel = 'HRTF'; p.distanceModel = 'inverse'; p.refDistance = 1.6; p.maxDistance = 60; p.rolloffFactor = 1.4;
    if (pos) this.setPos(p, pos);
    p.connect(this.master);
    const s = this.ctx.createGain(); s.gain.value = .35; p.connect(s); s.connect(this.revSend);
    return p;
  },
  setPos(p, v) {
    if (p.positionX) { p.positionX.value = v.x; p.positionY.value = v.y; p.positionZ.value = v.z; } else p.setPosition(v.x, v.y, v.z);
  },
  dest(pos, wet) { return pos ? this.panner(pos) : this.out(null, wet ?? .25); },
  src(buf = this.noise, loop = false) { const s = this.ctx.createBufferSource(); s.buffer = buf; s.loop = loop; s.playbackRate.value = 1; return s; },
  env(g, t, a, peak, d, sustain = 0) { g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(peak, t + a); g.gain.exponentialRampToValueAtTime(Math.max(sustain, .0001), t + a + d); },
  updateListener(cam) {
    if (!this.ctx) return;
    const l = this.ctx.listener, p = cam.getWorldPosition(_v1), f = cam.getWorldDirection(_v2);
    if (l.positionX) {
      l.positionX.value = p.x; l.positionY.value = p.y; l.positionZ.value = p.z;
      l.forwardX.value = f.x; l.forwardY.value = f.y; l.forwardZ.value = f.z; l.upX.value = 0; l.upY.value = 1; l.upZ.value = 0;
    } else { l.setPosition(p.x, p.y, p.z); l.setOrientation(f.x, f.y, f.z, 0, 1, 0); }
  },

  /* ---- tekil sesler ---- */
  step(vol, pos, heavy = false, rate = 1) {
    const t = this.t, d = this.dest(pos, .2);
    const n = this.src(); n.playbackRate.value = rand(.7, 1.1) * rate;
    const f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = heavy ? rand(180, 320) : rand(500, 900); f.Q.value = .9;
    const g = this.ctx.createGain(); this.env(g, t, .004, vol, heavy ? .16 : .09);
    n.connect(f); f.connect(g); g.connect(d); n.start(t, Math.random()); n.stop(t + .3);
    const o = this.ctx.createOscillator(); o.frequency.setValueAtTime(heavy ? 70 : 110, t); o.frequency.exponentialRampToValueAtTime(40, t + .12);
    const og = this.ctx.createGain(); this.env(og, t, .003, vol * (heavy ? 1.3 : .5), .12);
    o.connect(og); og.connect(d); o.start(t); o.stop(t + .2);
    if (heavy && Math.random() < .35) { // pençe tırmalaması
      const s = this.src(), sf = this.ctx.createBiquadFilter(); sf.type = 'highpass'; sf.frequency.value = 2500;
      const sg = this.ctx.createGain(); this.env(sg, t + .05, .02, vol * .35, .25);
      s.connect(sf); sf.connect(sg); sg.connect(d); s.start(t + .05, Math.random()); s.stop(t + .4);
    }
  },
  click(pos, n = 4, vol = .5) { // ekolokasyon tıkırtısı
    const t = this.t, d = this.dest(pos);
    for (let i = 0; i < n; i++) {
      const tt = t + i * rand(.045, .09);
      const s = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = rand(1800, 3600); f.Q.value = 8;
      const g = this.ctx.createGain(); this.env(g, tt, .001, vol * rand(.6, 1.2), .03);
      s.connect(f); f.connect(g); g.connect(d); s.start(tt, Math.random()); s.stop(tt + .06);
    }
  },
  growl(pos, dur = 1.6, vol = .7, pitch = 1) {
    const t = this.t, d = this.dest(pos);
    const o = this.ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.setValueAtTime(rand(55, 75) * pitch, t); o.frequency.linearRampToValueAtTime(rand(40, 55) * pitch, t + dur);
    const o2 = this.ctx.createOscillator(); o2.type = 'square'; o2.frequency.value = o.frequency.value * 1.49;
    const lfo = this.ctx.createOscillator(); lfo.frequency.value = rand(9, 16); const lg = this.ctx.createGain(); lg.gain.value = 18 * pitch; lfo.connect(lg); lg.connect(o.frequency);
    const n = this.src(); const nf = this.ctx.createBiquadFilter(); nf.type = 'bandpass'; nf.frequency.value = 500 * pitch; nf.Q.value = 2;
    const f = this.ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 700 * pitch; f.Q.value = 4;
    const ws = this.ctx.createWaveShaper(); ws.curve = this.curve;
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + .25); g.gain.setValueAtTime(vol, t + dur * .6); g.gain.exponentialRampToValueAtTime(.0001, t + dur);
    const o2g = this.ctx.createGain(); o2g.gain.value = .3;
    o.connect(ws); o2.connect(o2g); o2g.connect(ws); ws.connect(f); n.connect(nf); nf.connect(f); f.connect(g); g.connect(d);
    [o, o2, lfo].forEach(x => { x.start(t); x.stop(t + dur + .05); }); n.start(t, Math.random()); n.stop(t + dur + .05);
  },
  screech(pos, dur = 1.4, vol = 1) { // insanı zıplatan çığlık
    const t = this.t, d = pos ? this.panner(pos) : this.out(null, .5);
    const ws = this.ctx.createWaveShaper(); ws.curve = this.curve;
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + .02); g.gain.setValueAtTime(vol, t + dur * .55); g.gain.exponentialRampToValueAtTime(.0001, t + dur);
    const hp = this.ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 180;
    ws.connect(hp); hp.connect(g); g.connect(d);
    for (let i = 0; i < 5; i++) {
      const o = this.ctx.createOscillator(); o.type = i % 2 ? 'sawtooth' : 'square';
      const base = rand(380, 1300);
      o.frequency.setValueAtTime(base * .6, t); o.frequency.exponentialRampToValueAtTime(base, t + .08); o.frequency.exponentialRampToValueAtTime(base * rand(.45, .7), t + dur);
      const lfo = this.ctx.createOscillator(); lfo.frequency.value = rand(25, 60); const lg = this.ctx.createGain(); lg.gain.value = base * .08; lfo.connect(lg); lg.connect(o.frequency);
      const og = this.ctx.createGain(); og.gain.value = .22;
      o.connect(og); og.connect(ws); o.start(t); o.stop(t + dur); lfo.start(t); lfo.stop(t + dur);
    }
    const n = this.src(), nf = this.ctx.createBiquadFilter(); nf.type = 'bandpass'; nf.frequency.setValueAtTime(3000, t); nf.frequency.exponentialRampToValueAtTime(900, t + dur); nf.Q.value = 1.5;
    const ng = this.ctx.createGain(); ng.gain.value = .7; n.connect(nf); nf.connect(ng); ng.connect(ws); n.start(t); n.stop(t + dur);
  },
  sting(vol = 1) { // "korku vuruşu": uyumsuz yaylı akoru + darbe
    const t = this.t, d = this.out(null, .6);
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol * .5, t + .015); g.gain.exponentialRampToValueAtTime(.0001, t + 3.2);
    const f = this.ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.setValueAtTime(7000, t); f.frequency.exponentialRampToValueAtTime(600, t + 2.5);
    g.connect(f); f.connect(d);
    const root = rand(180, 240);
    [1, 1.059, 1.414, 1.5, 1.888, 2.12, 2.83, 3.0].forEach(r => {
      const o = this.ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = root * r * rand(.995, 1.005);
      const lfo = this.ctx.createOscillator(); lfo.frequency.value = rand(5, 8); const lg = this.ctx.createGain(); lg.gain.value = 3; lfo.connect(lg); lg.connect(o.frequency);
      const og = this.ctx.createGain(); og.gain.value = .12; o.connect(og); og.connect(g); o.start(t); o.stop(t + 3.3); lfo.start(t); lfo.stop(t + 3.3);
    });
    this.boom(vol);
    const n = this.src(), ng = this.ctx.createGain(); this.env(ng, t, .005, vol * .8, .4); n.connect(ng); ng.connect(d); n.start(t); n.stop(t + .6);
  },
  boom(vol = 1, pos) {
    const t = this.t, d = this.dest(pos, .5);
    const o = this.ctx.createOscillator(); o.frequency.setValueAtTime(110, t); o.frequency.exponentialRampToValueAtTime(28, t + 1.2);
    const g = this.ctx.createGain(); this.env(g, t, .005, vol * 1.2, 1.4);
    o.connect(g); g.connect(d); o.start(t); o.stop(t + 1.6);
  },
  slam(pos, vol = 1) {
    const t = this.t, d = this.dest(pos, .5);
    const n = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 900;
    const g = this.ctx.createGain(); this.env(g, t, .002, vol, .35);
    n.connect(f); f.connect(g); g.connect(d); n.start(t, Math.random()); n.stop(t + .5);
    const o = this.ctx.createOscillator(); o.frequency.setValueAtTime(90, t); o.frequency.exponentialRampToValueAtTime(35, t + .3);
    const og = this.ctx.createGain(); this.env(og, t, .002, vol * 1.2, .4); o.connect(og); og.connect(d); o.start(t); o.stop(t + .5);
    // metal çınlaması
    const m = this.ctx.createOscillator(); m.type = 'triangle'; m.frequency.value = rand(300, 520);
    const mg = this.ctx.createGain(); this.env(mg, t, .002, vol * .12, .9); m.connect(mg); mg.connect(d); m.start(t); m.stop(t + 1);
  },
  creak(pos, dur = .9, vol = .35, base = 1) { // kapı gıcırtısı (yapış-kay)
    const t = this.t, d = this.dest(pos, .4);
    const o = this.ctx.createOscillator(); o.type = 'sawtooth';
    const f0 = rand(380, 600) * base;
    o.frequency.setValueAtTime(f0, t);
    for (let i = 1; i < 14; i++) o.frequency.linearRampToValueAtTime(f0 * rand(.65, 1.35), t + dur * i / 14);
    const am = this.ctx.createOscillator(); am.type = 'square'; am.frequency.value = rand(25, 45);
    const amg = this.ctx.createGain(); amg.gain.value = .5; am.connect(amg);
    const f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 1200 * base; f.Q.value = 3;
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + .08); g.gain.setValueAtTime(vol, t + dur * .7); g.gain.exponentialRampToValueAtTime(.0001, t + dur);
    const g2 = this.ctx.createGain(); g2.gain.value = .5; amg.connect(g2.gain);
    o.connect(f); f.connect(g2); g2.connect(g); g.connect(d);
    o.start(t); o.stop(t + dur + .05); am.start(t); am.stop(t + dur + .05);
  },
  glass(pos, vol = 1) {
    const t = this.t, d = this.dest(pos, .5);
    for (let i = 0; i < 26; i++) {
      const tt = t + Math.pow(Math.random(), 2) * .5;
      const o = this.ctx.createOscillator(); o.type = 'sine'; o.frequency.value = rand(2500, 7500);
      const g = this.ctx.createGain(); this.env(g, tt, .001, vol * rand(.05, .2), rand(.05, .25));
      o.connect(g); g.connect(d); o.start(tt); o.stop(tt + .35);
    }
    const n = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'highpass'; f.frequency.value = 2000;
    const g = this.ctx.createGain(); this.env(g, t, .001, vol * .9, .3); n.connect(f); f.connect(g); g.connect(d); n.start(t, Math.random()); n.stop(t + .4);
  },
  pickup() {
    const t = this.t, d = this.out(null, .1);
    [660, 990].forEach((fr, i) => { const o = this.ctx.createOscillator(); o.type = 'triangle'; o.frequency.value = fr; const g = this.ctx.createGain(); this.env(g, t + i * .07, .005, .12, .25); o.connect(g); g.connect(d); o.start(t + i * .07); o.stop(t + i * .07 + .3); });
  },
  flashClick() {
    const t = this.t, d = this.out(null, 0), n = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'highpass'; f.frequency.value = 3000;
    const g = this.ctx.createGain(); this.env(g, t, .001, .25, .03); n.connect(f); f.connect(g); g.connect(d); n.start(t, Math.random()); n.stop(t + .05);
  },
  whisper(pan = 0, dur = 2.4, vol = .25, pos) {
    const t = this.t;
    let d;
    if (pos) d = this.panner(pos); else { const p = this.ctx.createStereoPanner(); p.pan.value = pan; p.connect(this.master); d = p; }
    const n = this.src();
    const f1 = this.ctx.createBiquadFilter(); f1.type = 'bandpass'; f1.Q.value = 6;
    const f2 = this.ctx.createBiquadFilter(); f2.type = 'bandpass'; f2.Q.value = 9;
    const g = this.ctx.createGain(); g.gain.value = 0;
    let tt = t;
    while (tt < t + dur) { // heceler
      const syl = rand(.08, .22);
      f1.frequency.setValueAtTime(rand(600, 1100), tt); f2.frequency.setValueAtTime(rand(1800, 3200), tt);
      g.gain.setValueAtTime(0, tt); g.gain.linearRampToValueAtTime(vol * rand(.4, 1), tt + syl * .3); g.gain.linearRampToValueAtTime(0, tt + syl);
      tt += syl + rand(0, .12);
    }
    const mix = this.ctx.createGain(); mix.gain.value = 1;
    n.connect(f1); n.connect(f2); f1.connect(g); f2.connect(g); g.connect(d);
    n.start(t, Math.random()); n.stop(t + dur + .1);
  },
  gasp(vol = .5) {
    const t = this.t, d = this.out(null, .1), n = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.Q.value = 2;
    f.frequency.setValueAtTime(600, t); f.frequency.linearRampToValueAtTime(1600, t + .5);
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + .12); g.gain.exponentialRampToValueAtTime(.0001, t + .7);
    n.connect(f); f.connect(g); g.connect(d); n.start(t, Math.random()); n.stop(t + .8);
  },
  breath(vol, inhale) {
    const t = this.t, d = this.out(null, 0), n = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.Q.value = 1.2;
    f.frequency.value = inhale ? 1400 : 900;
    const dur = inhale ? .8 : 1.0;
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + dur * .4); g.gain.exponentialRampToValueAtTime(.0001, t + dur);
    n.connect(f); f.connect(g); g.connect(d); n.start(t, Math.random()); n.stop(t + dur + .05);
  },
  heart(vol) {
    const t = this.t, d = this.out(null, 0);
    [0, .16].forEach((o, i) => {
      const s = this.ctx.createOscillator(); s.frequency.setValueAtTime(62, t + o); s.frequency.exponentialRampToValueAtTime(36, t + o + .12);
      const g = this.ctx.createGain(); this.env(g, t + o, .01, vol * (i ? .7 : 1), .16);
      s.connect(g); g.connect(d); s.start(t + o); s.stop(t + o + .25);
    });
  },
  musicBox(pos, notes, onEnd) {
    const t0 = this.t, d = this.panner(pos);
    const g = this.ctx.createGain(); g.connect(d);
    let tt = t0;
    notes.forEach(([f, l], i) => {
      const slow = 1 + i * .025;
      [1, 2.01, 3.98].forEach((h, k) => {
        const o = this.ctx.createOscillator(); o.type = 'sine'; o.frequency.value = f * h * (1 - i * .0015);
        const og = this.ctx.createGain(); this.env(og, tt, .004, [.22, .06, .02][k], 1.2);
        o.connect(og); og.connect(g); o.start(tt); o.stop(tt + 1.4);
      });
      tt += l * slow;
    });
    return { node: g, end: tt };
  },
  staticNoise(pos, dur = 3, vol = .35) {
    const t = this.t, d = this.panner(pos), n = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 1800; f.Q.value = .7;
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + .05);
    for (let i = 0; i < 40; i++) g.gain.setValueAtTime(vol * rand(.3, 1.3), t + i * dur / 40);
    g.gain.exponentialRampToValueAtTime(.0001, t + dur);
    n.connect(f); f.connect(g); g.connect(d); n.start(t, Math.random()); n.stop(t + dur + .1);
  },
  siren(dur = 6) {
    const t = this.t, d = this.out(null, .7);
    const o = this.ctx.createOscillator(); o.type = 'square';
    for (let i = 0; i < dur; i += .9) { o.frequency.setValueAtTime(520, t + i); o.frequency.linearRampToValueAtTime(820, t + i + .45); o.frequency.linearRampToValueAtTime(520, t + i + .9); }
    const f = this.ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 2200;
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(.09, t + .1); g.gain.setValueAtTime(.09, t + dur - .3); g.gain.exponentialRampToValueAtTime(.0001, t + dur);
    o.connect(f); f.connect(g); g.connect(d); o.start(t); o.stop(t + dur);
  },
  hum(pos, vol = .05) { // floresan vızıltısı, sürekli
    const o = this.ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = 100;
    const f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 200; f.Q.value = 4;
    const g = this.ctx.createGain(); g.gain.value = vol;
    const p = this.panner(pos); p.refDistance = .8; p.rolloffFactor = 2.2;
    o.connect(f); f.connect(g); g.connect(p); o.start();
    return g;
  },
  speak(text, rate = .55, pitch = .05) {
    try {
      if (!('speechSynthesis' in window)) return;
      const u = new SpeechSynthesisUtterance(text); u.lang = 'tr-TR'; u.rate = rate; u.pitch = pitch; u.volume = Math.min(1, volume);
      const v = speechSynthesis.getVoices().find(v => /tr/i.test(v.lang)); if (v) u.voice = v;
      speechSynthesis.cancel(); speechSynthesis.speak(u);
    } catch (e) {}
  },
  rumble() { // uzaktan gelen gümbürtü
    const t = this.t, d = this.out(null, .8), n = this.src(this.brown), f = this.ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 160;
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(.9, t + .6); g.gain.exponentialRampToValueAtTime(.0001, t + 3);
    n.connect(f); f.connect(g); g.connect(d); n.start(t); n.stop(t + 3.1);
  },
  distantScream() {
    const t = this.t, p = this.ctx.createStereoPanner(); p.pan.value = rand(-1, 1); p.connect(this.revSend);
    const o = this.ctx.createOscillator(); o.type = 'sawtooth'; const b = rand(500, 800);
    o.frequency.setValueAtTime(b, t); o.frequency.linearRampToValueAtTime(b * 1.3, t + .4); o.frequency.exponentialRampToValueAtTime(b * .5, t + 2.2);
    const lfo = this.ctx.createOscillator(); lfo.frequency.value = 6; const lg = this.ctx.createGain(); lg.gain.value = 18; lfo.connect(lg); lg.connect(o.frequency);
    const f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 1100; f.Q.value = 3;
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(.12, t + .3); g.gain.exponentialRampToValueAtTime(.0001, t + 2.3);
    o.connect(f); f.connect(g); g.connect(p); o.start(t); o.stop(t + 2.4); lfo.start(t); lfo.stop(t + 2.4);
  },
  laugh(pos) { // çocuk kıkırtısı (bozuk)
    const t = this.t, d = this.panner(pos);
    for (let i = 0; i < 6; i++) {
      const tt = t + i * .14;
      const o = this.ctx.createOscillator(); o.type = 'triangle'; o.frequency.setValueAtTime(rand(520, 640) * (1 - i * .04), tt); o.frequency.exponentialRampToValueAtTime(rand(380, 450), tt + .1);
      const f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 1400; f.Q.value = 2;
      const g = this.ctx.createGain(); this.env(g, tt, .01, .25, .1);
      o.connect(f); f.connect(g); g.connect(d); o.start(tt); o.stop(tt + .14);
    }
  }
};
const _v1 = new THREE.Vector3(), _v2 = new THREE.Vector3(), _v3 = new THREE.Vector3();

/* --- sürekli ambiyans (dron + rüzgâr) --- */
/* --- ek sesler: yağmur, gök gürültüsü, kapı vurma, telefon, gerilim kemanı --- */
Object.assign(A, {
  riser(dur = 1.8, vol = .5) { // gerilim yükselişi -> sonra vuruş gelir
    const t = this.t, d = this.out(null, .4);
    const n = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.Q.value = 4;
    f.frequency.setValueAtTime(200, t); f.frequency.exponentialRampToValueAtTime(5000, t + dur);
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + dur); g.gain.setValueAtTime(.0001, t + dur + .02);
    n.connect(f); f.connect(g); g.connect(d); n.start(t, Math.random()); n.stop(t + dur + .05);
    const o = this.ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.setValueAtTime(110, t); o.frequency.exponentialRampToValueAtTime(880, t + dur);
    const og = this.ctx.createGain(); og.gain.setValueAtTime(.0001, t); og.gain.exponentialRampToValueAtTime(vol * .25, t + dur); og.gain.setValueAtTime(.0001, t + dur + .02);
    o.connect(og); og.connect(d); o.start(t); o.stop(t + dur + .05);
  },
  hit(vol = 1) { // "bir anda" gelen sert korku vuruşu
    this.sting(vol); this.boom(vol * 1.1);
    const t = this.t, d = this.out(null, .7);
    const n = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 2500;
    const g = this.ctx.createGain(); this.env(g, t, .002, vol * 1.1, .6); n.connect(f); f.connect(g); g.connect(d); n.start(t, Math.random()); n.stop(t + .8);
    // yaylı çığlık (psikopat kemanı)
    for (let i = 0; i < 3; i++) {
      const o = this.ctx.createOscillator(); o.type = 'sawtooth'; const b = rand(1400, 2200);
      o.frequency.setValueAtTime(b, t); o.frequency.linearRampToValueAtTime(b * rand(.9, 1.1), t + .5);
      const lfo = this.ctx.createOscillator(); lfo.frequency.value = rand(6, 9); const lg = this.ctx.createGain(); lg.gain.value = 25; lfo.connect(lg); lg.connect(o.frequency);
      const bp = this.ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = b; bp.Q.value = 2;
      const og = this.ctx.createGain(); og.gain.setValueAtTime(.0001, t); og.gain.exponentialRampToValueAtTime(vol * .09, t + .01);
      for (let k = 0; k < 6; k++) og.gain.setValueAtTime(vol * .09 * (k % 2 ? .3 : 1), t + .09 + k * .09);
      og.gain.exponentialRampToValueAtTime(.0001, t + 1.1);
      o.connect(bp); bp.connect(og); og.connect(d); o.start(t); o.stop(t + 1.2); lfo.start(t); lfo.stop(t + 1.2);
    }
  },
  gliss(vol = .07) { // yükselen tiz yaylı kayma
    const t = this.t, d = this.out(null, .6);
    for (let i = 0; i < 2; i++) {
      const o = this.ctx.createOscillator(); o.type = 'sawtooth'; const b = rand(500, 700) * (i ? 1.06 : 1);
      o.frequency.setValueAtTime(b, t); o.frequency.exponentialRampToValueAtTime(b * 3, t + 3);
      const bp = this.ctx.createBiquadFilter(); bp.type = 'lowpass'; bp.frequency.value = 3000;
      const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + 2.4); g.gain.exponentialRampToValueAtTime(.0001, t + 3.1);
      o.connect(bp); bp.connect(g); g.connect(d); o.start(t); o.stop(t + 3.2);
    }
  },
  thunder(delay = 0, vol = 1) {
    const t = this.t + delay, d = this.out(null, .9);
    const n = this.src(this.brown), f = this.ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.setValueAtTime(900, t); f.frequency.exponentialRampToValueAtTime(120, t + 3);
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol * 1.4, t + .06);
    for (let i = 1; i < 10; i++) g.gain.setValueAtTime(vol * rand(.4, 1.3), t + i * .25);
    g.gain.exponentialRampToValueAtTime(.0001, t + 5);
    n.connect(f); f.connect(g); g.connect(d); n.start(t); n.stop(t + 5.1);
    const c = this.src(), cf = this.ctx.createBiquadFilter(); cf.type = 'highpass'; cf.frequency.value = 1500;
    const cg = this.ctx.createGain(); this.env(cg, t, .002, vol * .5, .25); c.connect(cf); cf.connect(cg); cg.connect(d); c.start(t, Math.random()); c.stop(t + .4);
  },
  knock(pos, n = 3, vol = 1) {
    for (let i = 0; i < n; i++) {
      const t = this.t + i * rand(.32, .42), d = this.dest(pos, .5);
      const s = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 500;
      const g = this.ctx.createGain(); this.env(g, t, .002, vol, .18); s.connect(f); f.connect(g); g.connect(d); s.start(t, Math.random()); s.stop(t + .3);
      const o = this.ctx.createOscillator(); o.frequency.setValueAtTime(130, t); o.frequency.exponentialRampToValueAtTime(50, t + .15);
      const og = this.ctx.createGain(); this.env(og, t, .002, vol * 1.3, .2); o.connect(og); og.connect(d); o.start(t); o.stop(t + .3);
    }
  },
  phone(pos, rings = 3) {
    const d = this.panner(pos);
    for (let r = 0; r < rings; r++) {
      const t = this.t + r * 3;
      [440, 480].forEach(fr => {
        const o = this.ctx.createOscillator(); o.frequency.value = fr;
        const am = this.ctx.createOscillator(); am.type = 'square'; am.frequency.value = 20; const ag = this.ctx.createGain(); ag.gain.value = .5; am.connect(ag);
        const g = this.ctx.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(.12, t + .02); g.gain.setValueAtTime(.12, t + 1.6); g.gain.linearRampToValueAtTime(0, t + 1.65);
        const g2 = this.ctx.createGain(); g2.gain.value = .5; ag.connect(g2.gain);
        o.connect(g2); g2.connect(g); g.connect(d); o.start(t); o.stop(t + 1.7); am.start(t); am.stop(t + 1.7);
      });
    }
  },
  spark(pos) {
    const t = this.t, d = this.dest(pos, .3);
    for (let i = 0; i < 18; i++) {
      const tt = t + Math.random() * .7, s = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'highpass'; f.frequency.value = 3000;
      const g = this.ctx.createGain(); this.env(g, tt, .001, rand(.1, .4), .02); s.connect(f); f.connect(g); g.connect(d); s.start(tt, Math.random()); s.stop(tt + .04);
    }
    const o = this.ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = 120; const g = this.ctx.createGain(); this.env(g, t, .01, .12, .7); o.connect(g); g.connect(d); o.start(t); o.stop(t + .8);
    this.glass(pos, .6);
  },
  drip(pos) {
    const t = this.t, d = this.dest(pos, .9), o = this.ctx.createOscillator();
    o.frequency.setValueAtTime(rand(1400, 2000), t); o.frequency.exponentialRampToValueAtTime(rand(500, 700), t + .05);
    const g = this.ctx.createGain(); this.env(g, t, .002, .12, .06); o.connect(g); g.connect(d); o.start(t); o.stop(t + .1);
  },
  metal(pos, vol = .5) {
    const t = this.t, d = this.dest(pos, .7);
    [1, 2.76, 5.4, 8.9].forEach((h, i) => { const o = this.ctx.createOscillator(); o.type = 'sine'; o.frequency.value = 180 * h * rand(.98, 1.02); const g = this.ctx.createGain(); this.env(g, t, .002, vol * [.5, .3, .2, .1][i], rand(1, 2.5)); o.connect(g); g.connect(d); o.start(t); o.stop(t + 2.6); });
    this.slam(pos, vol * .5);
  },
  whoosh(vol = .5) {
    const t = this.t, d = this.out(null, .3), n = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.Q.value = 1.5;
    f.frequency.setValueAtTime(300, t); f.frequency.exponentialRampToValueAtTime(2500, t + .25); f.frequency.exponentialRampToValueAtTime(400, t + .6);
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + .2); g.gain.exponentialRampToValueAtTime(.0001, t + .65);
    n.connect(f); f.connect(g); g.connect(d); n.start(t, Math.random()); n.stop(t + .7);
  },
  gong() { // yeni görev
    const t = this.t, d = this.out(null, .8);
    [55, 110.5, 166, 221].forEach((f, i) => { const o = this.ctx.createOscillator(); o.frequency.value = f; const g = this.ctx.createGain(); this.env(g, t, .01, [.5, .25, .12, .08][i], 3.5); o.connect(g); g.connect(d); o.start(t); o.stop(t + 3.6); });
  },
  chime() { // yol gösterme
    const t = this.t, d = this.out(null, .7);
    [784, 988, 1175].forEach((f, i) => { const o = this.ctx.createOscillator(); o.type = 'sine'; o.frequency.value = f; const g = this.ctx.createGain(); this.env(g, t + i * .09, .005, .06, 1.2); o.connect(g); g.connect(d); o.start(t + i * .09); o.stop(t + i * .09 + 1.3); });
  },
});
let rainGain = null, stringsGain = null;
function startWeather() {
  const ctx = A.ctx;
  rainGain = ctx.createGain(); rainGain.gain.value = 0; rainGain.connect(A.master);
  const r = A.src(A.noise, true), hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 900;
  const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2600;
  const rg = ctx.createGain(); rg.gain.value = .028; r.connect(hp); hp.connect(lp); lp.connect(rg); rg.connect(rainGain); r.start();
  const r2 = A.src(A.brown, true), lp2 = ctx.createBiquadFilter(); lp2.type = 'lowpass'; lp2.frequency.value = 300; const rg2 = ctx.createGain(); rg2.gain.value = .12;
  r2.connect(lp2); lp2.connect(rg2); rg2.connect(rainGain); r2.start();
  rainGain.gain.linearRampToValueAtTime(1, A.t + 5);
  // gerilim kemanları: yaratık yaklaştıkça açılır
  stringsGain = ctx.createGain(); stringsGain.gain.value = 0; stringsGain.connect(A.master);
  const sl = ctx.createBiquadFilter(); sl.type = 'lowpass'; sl.frequency.value = 2400; sl.connect(stringsGain);
  [311, 329.6, 466, 493.9, 622].forEach(f => {
    const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = f;
    const v = ctx.createOscillator(); v.frequency.value = rand(5, 7); const vg = ctx.createGain(); vg.gain.value = f * .006; v.connect(vg); vg.connect(o.frequency);
    const trem = ctx.createOscillator(); trem.frequency.value = rand(9, 13); const tg = ctx.createGain(); tg.gain.value = .5; trem.connect(tg);
    const g = ctx.createGain(); g.gain.value = .5; tg.connect(g.gain);
    const og = ctx.createGain(); og.gain.value = .045; o.connect(g); g.connect(og); og.connect(sl);
    o.start(); v.start(); trem.start();
  });
}

let droneGain = null, chaseGain = null, monsterVoice = null;
function startAmbience() {
  const ctx = A.ctx, t = A.t;
  droneGain = ctx.createGain(); droneGain.gain.value = 0; droneGain.connect(A.master);
  droneGain.gain.linearRampToValueAtTime(.16, t + 4);
  [41.2, 43.6, 61.7, 82.4 * 1.06].forEach((f, i) => {
    const o = ctx.createOscillator(); o.type = i === 3 ? 'triangle' : 'sine'; o.frequency.value = f;
    const lfo = ctx.createOscillator(); lfo.frequency.value = rand(.03, .12); const lg = ctx.createGain(); lg.gain.value = rand(.5, 2); lfo.connect(lg); lg.connect(o.frequency);
    const g = ctx.createGain(); g.gain.value = i === 3 ? .08 : .3; o.connect(g); g.connect(droneGain); o.start(); lfo.start();
  });
  const wind = A.src(A.noise, true), wf = ctx.createBiquadFilter(); wf.type = 'bandpass'; wf.frequency.value = 400; wf.Q.value = .6;
  const wlfo = ctx.createOscillator(); wlfo.frequency.value = .07; const wlg = ctx.createGain(); wlg.gain.value = 250; wlfo.connect(wlg); wlg.connect(wf.frequency);
  const wg = ctx.createGain(); wg.gain.value = .018; wind.connect(wf); wf.connect(wg); wg.connect(droneGain); wind.start(); wlfo.start();
  // kovalama müziği: hızlı nabız + gerilim
  chaseGain = ctx.createGain(); chaseGain.gain.value = 0; chaseGain.connect(A.master);
  const cs = ctx.createOscillator(); cs.type = 'sawtooth'; cs.frequency.value = 55;
  const cs2 = ctx.createOscillator(); cs2.type = 'sawtooth'; cs2.frequency.value = 58.3;
  const cf = ctx.createBiquadFilter(); cf.type = 'lowpass'; cf.frequency.value = 400; cf.Q.value = 6;
  const pulse = ctx.createOscillator(); pulse.type = 'square'; pulse.frequency.value = 4.6; const pg = ctx.createGain(); pg.gain.value = 300; pulse.connect(pg); pg.connect(cf.frequency);
  const hi = ctx.createOscillator(); hi.type = 'sawtooth'; hi.frequency.value = 880 * 1.06; const hig = ctx.createGain(); hig.gain.value = .03;
  const hilfo = ctx.createOscillator(); hilfo.frequency.value = 7; const hilg = ctx.createGain(); hilg.gain.value = 12; hilfo.connect(hilg); hilg.connect(hi.frequency);
  cs.connect(cf); cs2.connect(cf); cf.connect(chaseGain); hi.connect(hig); hig.connect(chaseGain);
  [cs, cs2, pulse, hi, hilfo].forEach(o => o.start());
  // yaratığın sürekli hırıltılı nefesi (konumsal)
  const mp = A.panner(new THREE.Vector3()); mp.refDistance = 1.2; mp.rolloffFactor = 1.8;
  const mn = A.src(A.noise, true), mf = ctx.createBiquadFilter(); mf.type = 'bandpass'; mf.frequency.value = 350; mf.Q.value = 3;
  const mo = ctx.createOscillator(); mo.type = 'sawtooth'; mo.frequency.value = 48; const mog = ctx.createGain(); mog.gain.value = .25;
  const mg = ctx.createGain(); mg.gain.value = 0;
  const blfo = ctx.createOscillator(); blfo.frequency.value = .45; const blg = ctx.createGain(); blg.gain.value = .5; blfo.connect(blg); blg.connect(mg.gain);
  const mlp = ctx.createBiquadFilter(); mlp.type = 'lowpass'; mlp.frequency.value = 900;
  mn.connect(mf); mf.connect(mg); mo.connect(mog); mog.connect(mlp); mlp.connect(mg); mg.connect(mp);
  const mvol = ctx.createGain(); mvol.gain.value = 0; mg.disconnect(); mg.connect(mvol); mvol.connect(mp);
  mn.start(); mo.start(); blfo.start();
  monsterVoice = { panner: mp, vol: mvol, rate: blfo, osc: mo };
}

/* ===================================================================
   OYUN DURUMU
   =================================================================== */
const S = {
  state: 'title', // title, intro, play, pause, dead, win, jumpscare
  time: 0, deaths: 0, startTime: 0,
  power: false, keycard: false, escaped: false,
  bottles: 1, battery: 1, stamina: 1, breath: 1, holdingBreath: false,
  flashOn: true, flashForcedOff: 0,
  crouch: false, running: false,
  hidden: null, // dolap
  noiseLevel: 0, fear: 0,
  visited: new Set(),
  triggered: new Set(),
  checkpoint: null,
  notesRead: new Set(),
};
const player = { pos: new THREE.Vector3(cc(3), 0, cc(3)), yaw: Math.PI, pitch: 0, vel: new THREE.Vector3(), bob: 0, stepAcc: 0, h: 1.62, shake: 0 };

/* ------------------------- NESNELERİ KUR ----------------------------- */
const items = []; // {type, mesh, pos, taken, cell}
let it_glow = null;
const pageTex = (() => { const c = makeCanvas(64, 86), x = c.getContext('2d'); x.fillStyle = '#b8a888'; x.fillRect(0, 0, 64, 86); x.strokeStyle = '#5a0000'; x.lineWidth = 2; x.beginPath(); x.arc(32, 40, 18, 0, 7); x.stroke();
  for (let i = 0; i < 5; i++) { const a = i / 5 * 6.28 - 1.57, b = (i + 2) / 5 * 6.28 - 1.57; x.moveTo(32 + Math.cos(a) * 18, 40 + Math.sin(a) * 18); x.lineTo(32 + Math.cos(b) * 18, 40 + Math.sin(b) * 18); } x.stroke();
  x.fillStyle = '#3a2a1a'; for (let i = 0; i < 6; i++) x.fillRect(8, 64 + i * 3, rand(30, 48), 1); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; })();
const glowTex = (() => { const c = makeCanvas(64, 64), x = c.getContext('2d'); const g = x.createRadialGradient(32, 32, 0, 32, 32, 32); g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(.25, 'rgba(255,255,255,.35)'); g.addColorStop(1, 'rgba(255,255,255,0)'); x.fillStyle = g; x.fillRect(0, 0, 64, 64); return new THREE.CanvasTexture(c); })();
function addItem(type, x, z, opts = {}) {
  const g = new THREE.Group();
  let y = .02;
  if (type === 'fuse') {
    const b = cyl(.06, .06, .28, M.fuse, 10); b.rotation.z = Math.PI / 2; g.add(b);
    const e1 = cyl(.07, .07, .04, M.metal, 10); e1.rotation.z = Math.PI / 2; e1.position.x = .15; g.add(e1);
    const e2 = e1.clone(); e2.position.x = -.15; g.add(e2);
    y = .82;
  } else if (type === 'battery') {
    const b = cyl(.04, .04, .16, M.batt, 8); b.rotation.z = Math.PI / 2; g.add(b); y = .05;
  } else if (type === 'bottle') {
    const b = cyl(.045, .05, .22, M.glass, 8); b.position.y = .11; g.add(b);
    const n = cyl(.018, .025, .1, M.glass, 6); n.position.y = .27; g.add(n); y = 0;
  } else if (type === 'card') {
    const b = box(.16, .01, .1, M.card); g.add(b); const s = box(.05, .012, .03, M.red); s.position.set(.04, 0, 0); g.add(s); y = .8;
  } else if (type === 'file') {
    const f = box(.32, .04, .24, new THREE.MeshStandardMaterial({ color: 0xc8a860, roughness: .9 })); f.rotation.y = rand(0, 3); g.add(f);
    const tab = box(.1, .045, .03, M.red); tab.position.set(.1, .005, -.12); f.add(tab); y = .03;
  } else if (type === 'page') {
    const pg = new THREE.Mesh(new THREE.PlaneGeometry(.24, .32), new THREE.MeshStandardMaterial({ map: pageTex, roughness: 1, side: THREE.DoubleSide, emissive: 0x401010 }));
    pg.rotation.x = -Math.PI / 2; pg.rotation.z = rand(-1, 1); g.add(pg); y = .015;
  } else if (type === 'note') {
    const p = new THREE.Mesh(new THREE.PlaneGeometry(.22, .28), M.paper); p.rotation.x = -Math.PI / 2; p.rotation.z = rand(-.5, .5); g.add(p); y = opts.y ?? .015;
  }
  const px = opts.px ?? cc(x) + rand(-.6, .6), pz = opts.pz ?? cc(z) + rand(-.6, .6);
  g.position.set(px, y, pz);
  if (type === 'fuse' || type === 'card') { // masaya/sehpaya koy
    const st = box(.6, y - .03, .5, M.rust); st.position.set(px, (y - .03) / 2, pz); world.add(st);
    addSolid(px, pz, .3, .25);
  }
  if (type === 'fuse' || type === 'card' || type === 'battery' || type === 'file' || type === 'page') { // hafif parıltı
    const gl = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: { fuse: 0xffcc44, card: 0x66aaff, file: 0xffe0a0, page: 0xff4040 }[type] || 0x44ff66, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: .55 }));
    gl.scale.setScalar(.7); g.add(gl); it_glow = gl;
  }
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  world.add(g);
  const it = { type, mesh: g, pos: g.position, taken: false, id: items.length, glow: (type === 'fuse' || type === 'card' || type === 'battery' || type === 'file' || type === 'page') ? it_glow : null, ...opts };
  if (it.glow && type !== 'battery') it.glow.scale.setScalar(1.3);
  items.push(it); return it;
}

// lambalar
const lamps = [];
const LIGHT_POOL = [];
for (let i = 0; i < 7; i++) { const pl = new THREE.PointLight(0xffffff, 0, 9, 1.8); scene.add(pl); LIGHT_POOL.push(pl); }
function addLamp(x, z, opts = {}) {
  const g = new THREE.Group();
  const tube = box(1.2, .06, .18, M.lampOff); g.add(tube);
  g.position.set(cc(x) + (opts.ox || 0), WALL_H - .05, cc(z) + (opts.oz || 0));
  world.add(g);
  // sanal ışık: gerçek ışığı her karede en yakın lambalara dağıtılan havuz verir
  const light = { position: new THREE.Vector3(g.position.x, WALL_H - .4, g.position.z), color: new THREE.Color(opts.color || 0xd8e8ff), intensity: 0, distance: opts.dist || 9 };
  const L = { g, tube, light, base: opts.intensity ?? 7, mode: opts.mode || 'flicker', on: opts.mode !== 'off', t: rand(0, 10), hum: null, cell: [x, z], power: !!opts.power };
  L.mode0 = L.mode; L.base0 = L.base; L.c0 = light.color.clone();
  lamps.push(L); return L;
}

const notesText = [
  'Gece hemşiresi Selma\'nın defterinden:\n\n"Hastalar artık bağırmıyor. Bağıranları önce o buluyor. Kimse gözlerini görmedi, çünkü gözü yok. Sadece dinliyor. Koridorda ayakkabımı çıkardım. Yine de nefesimi duydu sanırım."',
  'Bakım notu — Jeneratör odası:\n\n"Ana sigorta kutusu 3 sigorta istiyor. Biri ameliyathanede, biri morgda kaldı galiba, diğerlerini o şey bir yerlere sürükledi. Güç gelmeden başhekimin elektronik kapısı açılmaz. Kart onun masasında."',
  '(Kanla yazılmış)\n\n"KOŞMA\nKOŞMA\nKOŞMA\nO DUYUYOR\nDOLAPLAR GÜVENLİ... AMA NEFESİNİ TUT"',
  'Dr. Aydemir, kişisel kayıt — 14 Kasım 1987:\n\n"Denek 9\'un görme siniri tamamen köreldi; karşılığında işitmesi akıl almaz. 30 metreden kalp atışını duyduğuna yemin ederim. Bu gece kayışlarını kopardı. Şişe kırıldığında dönüp oraya koştu. Bunu bir yere yazmalıyım: SES ONU ÇEKER."',
  'Kapıya kazınmış:\n\n"Ana kapı kartla açılıyor ama okuyucu yavaş. Kartı okuttuğunda alarm bütün binayı uyandırıyor. O geldiğinde hâlâ orada olma."',
];

let monster, silhouette, crawler, hangBody, lockerCorpse, wchair, faceScare, radioMesh, mannequins = [];
let fuseBox, exitGate, exitLight, fuseLights = [], candleLight; const candles = [];
const fuseSpots = [];
function buildWorld() {
  // kapılar, dolaplar, işaretler
  for (let z = 0; z < GH; z++) for (let x = 0; x < GW; x++) {
    const ch = cellAt(x, z);
    if (ch === 'D') buildDoor(x, z, false);
    if (ch === 'X') buildDoor(x, z, true);
    if (ch === 'L') buildLocker(x, z, true);
    if (ch === 'F') fuseSpots.push([x, z]);
  }
  // çıkış kapısı (büyük metal kapı)
  {
    const g = new THREE.Group();
    const mat = new THREE.MeshStandardMaterial({ color: 0x3a3f44, roughness: .5, metalness: .8 });
    const l = box(C / 2, 2.8, .2, mat); l.position.set(-C / 4, 1.4, 0); g.add(l);
    const r = box(C / 2, 2.8, .2, mat); r.position.set(C / 4, 1.4, 0); g.add(r);
    const bar = box(C, .12, .3, M.rust); bar.position.y = 1.2; g.add(bar);
    const reader = box(.2, .3, .1, M.dark); reader.position.set(C / 2 - .25, 1.3, -.2); g.add(reader);
    exitLight = box(.12, .06, .05, M.red); exitLight.position.set(C / 2 - .25, 1.42, -.26); g.add(exitLight);
    const sign = new THREE.Mesh(new THREE.PlaneGeometry(1.2, .35), new THREE.MeshBasicMaterial({ map: textDecal('ÇIKIŞ', 200, '#30ff60', 512, 160), transparent: true }));
    sign.position.set(0, 2.85, -.3); sign.rotation.y = Math.PI; g.add(sign);
    const lintel = box(C, WALL_H - 2.8, .4, wallMats[0]); lintel.position.set(0, 2.8 + (WALL_H - 2.8) / 2, 0); g.add(lintel);
    const outside = new THREE.Mesh(new THREE.PlaneGeometry(C, WALL_H), new THREE.MeshBasicMaterial({ color: 0xc8d4ff, fog: false }));
    outside.position.set(0, WALL_H / 2, 1.4); outside.rotation.y = Math.PI; g.add(outside);
    for (const sx of [-1, 1]) { const side = box(.1, WALL_H, 1.6, wallMats[0]); side.position.set(sx * C / 2, WALL_H / 2, .8); g.add(side); }
    g.position.set(cc(27), 0, cc(26) - C / 2 + .15);
    world.add(g);
    exitGate = { g, l, r, open: 0 };
    const sl = new THREE.PointLight(0x30ff60, 1.2, 4, 2); sl.position.set(cc(27), 2.6, cc(26) - C / 2 - .5); world.add(sl);
  }
  // sigorta kutusu
  {
    const g = new THREE.Group();
    const b = box(1.0, 1.2, .3, M.metal); b.position.y = 1.4; g.add(b);
    for (let i = 0; i < 3; i++) {
      const slot = box(.18, .3, .05, M.dark); slot.position.set(-.3 + i * .3, 1.45, .16); g.add(slot);
      const lt = box(.08, .05, .04, M.red); lt.position.set(-.3 + i * .3, 1.75, .16); g.add(lt);
      const fz = cyl(.05, .05, .24, M.fuse, 8); fz.position.set(-.3 + i * .3, 1.45, .2); fz.visible = false; g.add(fz);
      fuseLights.push({ lt, fz });
    }
    const lever = box(.06, .3, .06, M.red); lever.position.set(.55, 1.4, .1); g.add(lever);
    const [dx, dz] = wallDir(16, 8);
    g.position.set(cc(16) + dx * (C / 2 - .16), 0, cc(8) + dz * (C / 2 - .16)); g.rotation.y = Math.atan2(-dx, -dz);
    world.add(g);
    fuseBox = { g, pos: g.position.clone(), lever };
    const warn = new THREE.PointLight(0xff3020, .6, 3, 2); warn.position.set(g.position.x, 2.1, g.position.z + .5); world.add(warn);
    fuseBox.warn = warn;
  }
  // yataklar (koğuş)
  for (let i = 0; i < 4; i++) { bed(cc(8) + i * C * 1.9, cc(1) + .2, 0, i === 2); bed(cc(9) + i * C * 1.9 - .5, cc(4) - .2, Math.PI, i === 0); }
  bed(cc(1) + .5, cc(1) + .3, 0, true); // başlangıç odası
  bed(cc(5) - .2, cc(1) + .3, 0, false);
  // ameliyathane
  table(cc(5), cc(11), 1.0, 2.2); bloodPool(cc(5), cc(11) + .6, .9); bloodTrail(cc(5), cc(11), cc(10), cc(11));
  cabinet(cc(9), cc(8)); cabinet(cc(1), cc(10)); cabinet(cc(9), cc(14));
  { const l = new THREE.Mesh(new THREE.CylinderGeometry(.5, .3, .25, 12, 1, true), M.metal); l.position.set(cc(5), 2.5, cc(11)); world.add(l); }
  // yemekhane masaları
  for (let i = 0; i < 3; i++) for (let j = 0; j < 2; j++) {
    table(cc(22.5) + i * C * 2.3, cc(9.6) + j * C * 2.6, 2.6, .9);
    chair(cc(22.5) + i * C * 2.3 - .7, cc(9.6) + j * C * 2.6 + .7, Math.PI, Math.random() < .3);
    chair(cc(22.5) + i * C * 2.3 + .6, cc(9.6) + j * C * 2.6 - .7, 0, Math.random() < .3);
  }
  // morg çekmeceleri (duvar)
  for (let i = 0; i < 6; i++) {
    const g = box(.95, .55, .3, M.metal); g.position.set(cc(2) + i * 1.05, .5 + (i % 2) * .62, cc(18) - C / 2 + .17); world.add(g);
    const g2 = box(.95, .55, .3, M.metal); g2.position.set(cc(2) + i * 1.05, 1.74, cc(18) - C / 2 + .17); world.add(g2);
  }
  addSolid(cc(4.5), cc(18) - C / 2 + .2, 3.4, .25);
  for (let i = 0; i < 3; i++) { // otopsi masaları + örtülü cesetler
    table(cc(3) + i * C * 1.2, cc(22), .9, 2.0);
    const body = humanoid(M.sheet, 1); body.rotation.x = -Math.PI / 2; body.position.set(cc(3) + i * C * 1.2, .82, cc(22) + .85); world.add(body);
  }
  bloodTrail(cc(5), cc(16), cc(5), cc(20));
  // şapel sıraları
  for (let i = 0; i < 4; i++) for (const sx of [-1, 1]) {
    const p = box(2.0, .5, .5, M.wood); p.position.set(cc(14) + sx * 2.0, .45, cc(19.5) + i * 1.6); world.add(p);
    const pb = box(2.0, .6, .08, M.wood); pb.position.set(cc(14) + sx * 2.0, .85, cc(19.5) + i * 1.6 + .25); world.add(pb);
    addSolid(cc(14) + sx * 2.0, cc(19.5) + i * 1.6 + .1, 1.0, .35);
  }
  { // haç (ters)
    const v = box(.12, 1.4, .08, M.wood); v.position.set(cc(14), 1.6, cc(25) + C / 2 - .2); world.add(v);
    const h = box(.7, .12, .08, M.wood); h.position.set(cc(14), 1.1, cc(25) + C / 2 - .2); world.add(h);
    for (let i = 0; i < 9; i++) { const c = cyl(.03, .03, .2, M.sheet, 6); c.position.set(cc(14) + rand(-1.2, 1.2), .1, cc(24.5) + rand(-.5, .5)); world.add(c); const fl = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xff9940, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true })); fl.scale.setScalar(.25); fl.position.copy(c.position); fl.position.y = .24; world.add(fl); candles.push(fl); }
    candleLight = new THREE.PointLight(0xff8830, 1.4, 6, 2); candleLight.position.set(cc(14), .5, cc(24.5)); world.add(candleLight);
  }
  // lobi: resepsiyon, banklar
  { const d = box(4, 1.1, .8, M.wood); d.position.set(cc(24), .55, cc(20)); world.add(d); addSolid(cc(24), cc(20), 2, .4); }
  for (let i = 0; i < 3; i++) { const b = box(2.2, .45, .6, M.wood); b.position.set(cc(31) , .22, cc(19.5) + i * 2.2); world.add(b); addSolid(cc(31), cc(19.5) + i * 2.2, 1.1, .3); }
  cabinet(cc(35), cc(23)); cabinet(cc(19), cc(19));
  // depo
  for (let i = 0; i < 4; i++) { const sh = box(.6, 2.2, 2.2, M.rust); sh.position.set(cc(28) + i * 2.2, 1.1, cc(2.5)); world.add(sh); addSolid(cc(28) + i * 2.2, cc(2.5), .3, 1.1); }
  table(cc(33), cc(1.2), 1.4, .7);
  radioMesh = box(.4, .25, .18, M.dark); radioMesh.position.set(cc(33), .92, cc(1.2)); world.add(radioMesh);
  { const dial = box(.08, .08, .02, M.lampOn); dial.position.set(.1, .02, .1); radioMesh.add(dial); dial.visible = false; radioMesh.userData.dial = dial; }
  // banyo bölmeleri
  for (let i = 0; i < 4; i++) { const p = box(.06, 2.0, 1.6, M.metal); p.position.set(cc(18.5) + i * 1.6, 1.0, cc(1) + .1); world.add(p); addSolid(cc(18.5) + i * 1.6, cc(1) + .1, .05, .8); }
  for (let i = 0; i < 4; i++) { const s = box(.5, .2, .4, M.sheet); s.position.set(cc(18) + i * 2, .9, cc(4) + C / 2 - .3); world.add(s); }
  // başhekim odası
  table(cc(34), cc(10), 1.6, .8); chair(cc(34), cc(10.6), Math.PI, false); cabinet(cc(35), cc(13)); cabinet(cc(33), cc(8));
  // jeneratör
  { const gen = box(1.6, 1.3, 2.6, M.rust); gen.position.set(cc(17), .65, cc(12)); world.add(gen); addSolid(cc(17), cc(12), .8, 1.3);
    for (let i = 0; i < 3; i++) { const p = cyl(.08, .08, 3, M.rust, 6); p.position.set(cc(14) + i * .3, 1.5, cc(14) + C / 2 - .2); world.add(p); } }
  // koridorlar: devrik sandalyeler, kağıtlar, kan
  chair(cc(14), cc(6), .5, true); chair(cc(28), cc(16), 2, true);
  bloodPool(cc(19), cc(6), .5); bloodTrail(cc(16), cc(6), cc(16), cc(15)); bloodPool(cc(31), cc(12), .4);
  // duvar yazıları
  wallText('O DUYUYOR', cc(18), cc(6), 0, 1);
  wallText('KOŞMA', cc(31), cc(10), -1, 0, 1.6, 2.2);
  wallText('SESSİZ OL', cc(8), cc(16), 0, 1);
  wallText('NEFESİNİ TUT', cc(26), cc(25), 0, -1);
  wallText('GÖZÜ YOK', cc(4), cc(25), 0, -1, 1.5, 2.4);
  wallText('ARKANA BAKMA', cc(3), cc(1), 0, 1, 1.9, 2.4);

  // lambalar (yalnızca birkaçı, titrek)
  addLamp(3, 2, { mode: 'flicker', intensity: 3.5 });
  addLamp(9, 6, { mode: 'flicker' });
  addLamp(22, 6, { mode: 'flicker', intensity: 6 });
  addLamp(11, 11, { mode: 'dead', power: true });
  addLamp(16, 10, { mode: 'off', power: true, color: 0xff3020, intensity: 9 });
  addLamp(25, 11, { mode: 'flicker', intensity: 5 });
  addLamp(20, 16, { mode: 'flicker' });
  addLamp(31, 13, { mode: 'off', power: true, color: 0xff3020 });
  addLamp(5, 21, { mode: 'flicker', intensity: 4, color: 0xc8ffd8 });
  addLamp(27, 21, { mode: 'off', power: true, color: 0xff3020, intensity: 10, dist: 14 });
  addLamp(34, 11, { mode: 'off', power: true, color: 0xffd8a0 });

  buildFloor2();
  buildStairs();
  // yaratık + korkutma aktörleri
  monster = buildMonster(); scene.add(monster);
  silhouette = buildMonster(true); silhouette.visible = false; scene.add(silhouette);
  crawler = buildMonster(); crawler.visible = false; scene.add(crawler);
  faceScare = buildMonster(); faceScare.visible = false; faceScare.scale.setScalar(1); camera.add(faceScare);
  hangBody = humanoid(M.bloodSheet, 1); hangBody.visible = false; scene.add(hangBody);
  { const rope = cyl(.012, .012, 3, M.wood, 4); rope.position.y = 3.25; hangBody.add(rope); hangBody.userData.rope = rope; }
  wchair = wheelchair(); wchair.position.set(cc(28.4), 0, cc(13.4)); wchair.rotation.y = Math.PI * 1.25;
  // banyoda dolap cesedi (saklanılamaz)
  const lc = buildLocker(25, 4, false); lockerCorpse = { L: lc, body: humanoid(M.skinDark, .95), fired: false };
  lockerCorpse.body.position.set(0, 0, 0); lc.g.add(lockerCorpse.body); lockerCorpse.body.visible = false;
  // mankenler (bakmadığında dönüyorlar)
  [[22, 23], [33, 22], [10, 3], [26, 18]].forEach(([x, z]) => {
    const m = humanoid(M.mannequin, 1.02); m.position.set(cc(x), 0, cc(z)); m.rotation.y = rand(0, 6); scene.add(m);
    m.userData.limbs.la.rotation.x = -.3; m.userData.limbs.ra.rotation.z = .2;
    mannequins.push({ m, home: m.position.clone(), seen: true });
  });
}

/* ------------------- EK DÜNYA: pencere, tabela, dekor ------------------- */
const windowMats = [];
let lightningLight, shadowRunner, child, peekHead, sparks;
function windowTexture() {
  const w = 256, h = 320, c = makeCanvas(w, h), x = c.getContext('2d');
  const g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#1b2740'); g.addColorStop(1, '#0a0f1c');
  x.fillStyle = g; x.fillRect(0, 0, w, h);
  // ağaç dalları silüeti
  x.strokeStyle = '#020306'; x.lineCap = 'round';
  for (let i = 0; i < 5; i++) { x.lineWidth = rand(3, 8); crack(x, rand(0, w), h, rand(120, 260), -Math.PI / 2 + rand(-.6, .6), 3); }
  // yağmur damlaları
  for (let i = 0; i < 160; i++) { x.fillStyle = `rgba(160,190,230,${rand(.05, .3)})`; x.fillRect(rand(0, w), rand(0, h), 1.5, rand(3, 12)); }
  grime(x, w, h, 14, 'rgba(30,25,15,A)', 20, 80, .6);
  // çerçeve ve parmaklık
  x.fillStyle = '#2a2620'; x.fillRect(0, 0, w, 14); x.fillRect(0, h - 14, w, 14); x.fillRect(0, 0, 14, h); x.fillRect(w - 14, 0, 14, h);
  x.fillRect(w / 2 - 5, 0, 10, h); x.fillRect(0, h / 2 - 5, w, 10);
  x.fillStyle = '#121212'; for (let i = 1; i < 6; i++) x.fillRect(i * w / 6 - 3, 0, 6, h);
  // kanlı el izi
  if (Math.random() < .35) { x.fillStyle = 'rgba(110,0,0,.75)'; handprint(x, rand(50, 200), rand(80, 240), rand(.8, 1.2)); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function handprint(x, px, py, sc) {
  x.save(); x.translate(px, py); x.scale(sc, sc); x.rotate(rand(-.4, .4));
  x.beginPath(); x.ellipse(0, 0, 16, 20, 0, 0, 7); x.fill();
  [[-14, -26, 5, 15], [-5, -34, 5, 18], [5, -33, 5, 18], [14, -27, 4.5, 15], [22, -2, 4.5, 12]].forEach(([a, b, rw, rh], i) => { x.beginPath(); x.ellipse(a, b, rw, rh, i === 4 ? 1 : 0, 0, 7); x.fill(); });
  for (let i = 0; i < 4; i++) x.fillRect(rand(-14, 14), 10, 2.5, rand(15, 45));
  x.restore();
}
function plateTexture(text, bg = '#1d4f3a', fg = '#e8efe6') {
  const c = makeCanvas(512, 128), x = c.getContext('2d');
  x.fillStyle = bg; x.fillRect(0, 0, 512, 128);
  x.strokeStyle = fg; x.lineWidth = 5; x.strokeRect(10, 10, 492, 108);
  x.fillStyle = fg; x.font = 'bold 58px "Special Elite", monospace'; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.fillText(text.toLocaleUpperCase('tr-TR'), 256, 68);
  grime(x, 512, 128, 10, 'rgba(0,0,0,A)', 10, 60, .55);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function buildExtras() {
  // pencereler: dış duvarlarda, şimşekte parlar
  const winGeo = new THREE.PlaneGeometry(1.5, 1.85);
  const texes = [windowTexture(), windowTexture(), windowTexture()];
  for (let z = 0; z < GH; z++) for (let x = 0; x < GW; x++) {
    if (cellAt(x, z) !== '#') continue;
    const edge = x === 0 || z === 0 || x === GW - 1 || z === GH - 1 || x === 36 || x === F2X;
    if (!edge || (x + z) % 3 !== 0) continue;
    for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const n = cellAt(x + dx, z + dz);
      if (!'.FSMBK'.includes(n) || n === 'L') continue;
      if (!roomOf(x + dx, z + dz)) continue;
      const mat = new THREE.MeshStandardMaterial({ map: pick(texes), emissive: 0x6688cc, emissiveMap: null, emissiveIntensity: .08, roughness: .2, metalness: .3 });
      mat.emissiveMap = mat.map;
      windowMats.push(mat);
      const m = new THREE.Mesh(winGeo, mat);
      m.position.set(cc(x) + dx * (C / 2 + .02), 1.65, cc(z) + dz * (C / 2 + .02));
      m.lookAt(m.position.x + dx, 1.65, m.position.z + dz);
      world.add(m);
      const sill = box(1.7, .08, .2, M.wood); sill.position.set(m.position.x + dx * .08, .72, m.position.z + dz * .08); sill.rotation.y = m.rotation.y; world.add(sill);
    }
  }
  lightningLight = new THREE.HemisphereLight(0xaac4ff, 0x101830, 0); scene.add(lightningLight);

  // kapı üstü oda tabelaları (koridor tarafında)
  for (const d of doors) {
    const sides = d.ew ? [[0, -1], [0, 1]] : [[-1, 0], [1, 0]];
    for (const [sx, sz] of sides) {
      const here = roomOf(d.x + sx, d.z + sz), there = roomOf(d.x - sx, d.z - sz);
      if (!there || here === there) continue;
      const name = there.n === 'Başhekim' ? 'Başhekim Odası' : there.n;
      const m = new THREE.Mesh(new THREE.PlaneGeometry(1.5, .38), new THREE.MeshStandardMaterial({ map: plateTexture(name, d.electric ? '#5a1414' : '#1d4f3a'), roughness: .5, emissive: 0xffffff, emissiveIntensity: .05 }));
      m.material.emissiveMap = m.material.map;
      m.position.set(cc(d.x) + sx * .27, 2.72, cc(d.z) + sz * .27);
      m.lookAt(m.position.x + sx, 2.72, m.position.z + sz);
      world.add(m);
    }
  }
  // duvarlarda kanlı el izleri
  const hpTex = (() => { const c = makeCanvas(256, 256), x = c.getContext('2d'); x.fillStyle = 'rgba(95,0,0,.85)'; for (let i = 0; i < 4; i++) handprint(x, 40 + i * 55, 90 + Math.sin(i) * 40, .9); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; })();
  [[2, 6, 0, 1], [15, 6, 0, -1], [11, 9, -1, 0], [31, 8, 1, 0], [21, 16, 0, -1], [6, 20, 0, 1], [30, 16, 0, 1], [16, 2, 1, 0]].forEach(([x, z, dx, dz]) => {
    if (cellAt(x + dx, z + dz) !== '#') return;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(1.3, 1.3), new THREE.MeshStandardMaterial({ map: hpTex, transparent: true, depthWrite: false, roughness: .3 }));
    m.position.set(cc(x) + dx * (C / 2 - .015), rand(.9, 1.6), cc(z) + dz * (C / 2 - .015)); m.lookAt(m.position.x - dx, m.position.y, m.position.z - dz); m.rotation.z += rand(-.5, .5);
    world.add(m);
  });
  // sedyeler, serum askıları, kağıtlar, sarkan kablolar
  const gurney = (x, z, rot) => {
    const g = new THREE.Group();
    const top = box(.7, .06, 1.9, M.metal); top.position.y = .8; g.add(top);
    const pad = box(.62, .08, 1.8, M.bloodSheet); pad.position.y = .87; g.add(pad);
    for (const [lx, lz] of [[-.3, -.85], [.3, -.85], [-.3, .85], [.3, .85]]) { const l = cyl(.02, .02, .78, M.metal, 5); l.position.set(lx, .39, lz); g.add(l); }
    g.position.set(x, 0, z); g.rotation.y = rot; world.add(g);
    const s = Math.abs(Math.sin(rot)) > .5; addSolid(x, z, s ? .95 : .35, s ? .35 : .95);
  };
  gurney(cc(27) , cc(6) - .7, Math.PI / 2 + .15); gurney(cc(3), cc(16) - .7, Math.PI / 2 - .1); gurney(cc(31) - .6, cc(13), .08); gurney(cc(3), cc(12), .3);
  const iv = (x, z) => { const g = new THREE.Group(); const p = cyl(.015, .015, 1.9, M.metal, 5); p.position.y = .95; g.add(p); const b = box(.14, .22, .05, M.glass); b.position.set(.1, 1.75, 0); g.add(b); const base = cyl(.25, .25, .03, M.metal, 5); base.position.y = .02; g.add(base); g.position.set(x, 0, z); world.add(g); };
  iv(cc(6), cc(10)); iv(cc(2), cc(2) + .8); iv(cc(13), cc(2)); iv(cc(4), cc(20));
  const paperGeo = new THREE.PlaneGeometry(.22, .3);
  for (let i = 0; i < 70; i++) {
    const c = pick(floorCells); const m = new THREE.Mesh(paperGeo, M.sheet);
    m.rotation.set(-Math.PI / 2, 0, rand(0, 6)); m.position.set(cc(c[0]) + rand(-1.4, 1.4), .006 + i * .00005, cc(c[1]) + rand(-1.4, 1.4)); m.receiveShadow = true; world.add(m);
  }
  for (let i = 0; i < 18; i++) {
    const c = pick(floorCells), L = rand(.4, 1.3);
    const w = cyl(.012, .012, L, M.dark, 4); w.position.set(cc(c[0]) + rand(-1, 1), WALL_H - L / 2, cc(c[1]) + rand(-1, 1)); w.rotation.z = rand(-.2, .2); world.add(w);
  }
  // korku aktörleri
  shadowRunner = buildMonster(true); shadowRunner.visible = false; scene.add(shadowRunner);
  child = humanoid(new THREE.MeshBasicMaterial({ color: 0x050505 }), .62); child.visible = false; scene.add(child);
  peekHead = buildMonster(); peekHead.visible = false; scene.add(peekHead);
  // kıvılcım parçacıkları
  const sg = new THREE.BufferGeometry(); const sp = new Float32Array(60 * 3); sg.setAttribute('position', new THREE.BufferAttribute(sp, 3));
  sparks = new THREE.Points(sg, new THREE.PointsMaterial({ color: 0xffcc66, size: .06, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
  sparks.visible = false; sparks.userData.v = new Float32Array(60 * 3); scene.add(sparks);
}


/* ============================ 2. KAT ============================ */
const STATIONS = [];   // görev istasyonları: vana, mum, arşiv
const O2 = F2X;        // 2. kat x kayması (hücre)
function station(type, x, z, mesh, extra = {}) {
  const st = { type, id: STATIONS.length, pos: mesh.position.clone(), mesh, done: false, ...extra };
  STATIONS.push(st); return st;
}
function buildFloor2() {
  const X = x => cc(x + O2);
  // ARŞİV: raflar ve arşiv dolabı (dosya teslim)
  for (let i = 0; i < 3; i++) { const sh = box(.5, 2.3, 2.6, M.rust); sh.position.set(X(3) + i * 2.4, 1.15, cc(3)); world.add(sh); addSolid(X(3) + i * 2.4, cc(3), .25, 1.3); for (let k = 0; k < 4; k++) { const bx = box(.45, .3, .4, M.sheet); bx.position.set(X(3) + i * 2.4, .35 + k * .55, cc(3) + rand(-1, 1)); world.add(bx); } }
  { const g = new THREE.Group(); const b = box(1.4, 1.6, .7, M.metal); b.position.y = .8; g.add(b);
    for (let k = 0; k < 4; k++) { const d = box(1.3, .32, .05, M.rust); d.position.set(0, .3 + k * .38, .36); g.add(d); const h = box(.3, .05, .05, M.dark); h.position.set(0, .3 + k * .38, .4); g.add(h); }
    g.position.set(X(8), 0, cc(1) - C / 2 + .4); world.add(g); addSolid(X(8), cc(1) - C / 2 + .4, .7, .35);
    station('archive', X(8), cc(1), g, { label: 'Arşiv dolabı' }); }
  // KÜTÜPHANE
  for (let i = 0; i < 4; i++) { const sh = box(2.2, 2.4, .45, M.wood); sh.position.set(X(12) + i * 2.3, 1.2, cc(1) - C / 2 + .25); world.add(sh); }
  table(X(15), cc(3), 2.2, 1); chair(X(14), cc(3.5), 0, true); chair(X(16), cc(2.6), Math.PI, false);
  // ELEKTROŞOK
  { const ch = box(.7, .1, .7, M.wood); ch.position.set(X(24), .5, cc(2.5)); world.add(ch); const bk = box(.7, 1.1, .1, M.wood); bk.position.set(X(24), 1.05, cc(2.5) - .35); world.add(bk);
    const cap = new THREE.Mesh(new THREE.SphereGeometry(.2, 10, 6, 0, 6.3, 0, 1.4), M.metal); cap.position.set(X(24), 1.65, cc(2.5) - .2); world.add(cap);
    const mac = box(1.2, 1.3, .6, M.metal); mac.position.set(X(26), .65, cc(1)); world.add(mac); addSolid(X(26), cc(1), .6, .3); addSolid(X(24), cc(2.5), .4, .4);
    for (let k = 0; k < 5; k++) { const dl = box(.08, .08, .02, k % 2 ? M.red : M.green); dl.position.set(X(26) - .4 + k * .2, 1.1, cc(1) + .31); world.add(dl); } }
  wallText('İTİRAF ET', X(24), cc(4), 0, -1, 1.7, 2.4);
  // KAZAN DAİRESİ: kazanlar, borular, 3 vana
  for (let i = 0; i < 2; i++) { const k = cyl(.9, .9, 2.6, M.rust, 16); k.position.set(X(31) + i * 2.6, 1.3, cc(2.6)); world.add(k); addSolid(X(31) + i * 2.6, cc(2.6), .9, .9); }
  for (let i = 0; i < 5; i++) { const pp = cyl(.08, .08, C * 7, M.rust, 6); pp.rotation.z = Math.PI / 2; pp.position.set(X(32), 2.6 - i * .12, cc(1) - 1 + i * .5); world.add(pp); }
  [[30, 1, 0, -1], [35, 3, 1, 0], [34, 4, 0, 1]].forEach(([x, z, dx, dz]) => {
    const g = new THREE.Group(); const pipe = cyl(.07, .07, .5, M.rust, 6); pipe.rotation.x = Math.PI / 2; pipe.position.z = -.25; g.add(pipe);
    const wheel = new THREE.Mesh(new THREE.TorusGeometry(.2, .03, 6, 16), M.red); g.add(wheel);
    for (let k = 0; k < 4; k++) { const sp = box(.4, .025, .025, M.red); sp.rotation.z = k * Math.PI / 4; wheel.add(sp); }
    g.position.set(X(x) + dx * (C / 2 - .5), 1.3, cc(z) + dz * (C / 2 - .5)); g.lookAt(g.position.x - dx, 1.3, g.position.z - dz); world.add(g);
    station('valve', 0, 0, g, { wheel, label: 'Vana' });
  });
  // ÇOCUK KOĞUŞU: küçük yataklar, oyuncaklar, mum sunağı (4 mum)
  for (let i = 0; i < 4; i++) { const b = bed(X(2) + i * 2.8, cc(8) + .3, 0, i === 1); b.scale.setScalar(.7); }
  for (let i = 0; i < 3; i++) { const b = bed(X(2.5) + i * 3.2, cc(14) - .3, Math.PI, false); b.scale.setScalar(.7); }
  { const horse = new THREE.Group(); const bd = box(.7, .25, .2, M.wood); bd.position.y = .55; horse.add(bd); const hd = box(.15, .35, .18, M.wood); hd.position.set(.35, .75, 0); horse.add(hd); const rk = new THREE.Mesh(new THREE.TorusGeometry(.5, .03, 4, 12, Math.PI), M.wood); rk.rotation.x = Math.PI; rk.position.y = .5; horse.add(rk); horse.position.set(X(9), 0, cc(10)); world.add(horse); }
  for (let i = 0; i < 4; i++) {
    const a = i / 4 * Math.PI * 2 + .4, cx = X(6) + Math.cos(a) * 1.4, cz = cc(11) + Math.sin(a) * 1.4;
    const g = new THREE.Group(); const c = cyl(.05, .06, .3, M.sheet, 8); c.position.y = .15; g.add(c);
    const fl = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xffa040, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true })); fl.scale.setScalar(.35); fl.position.y = .38; fl.visible = false; g.add(fl);
    g.position.set(cx, 0, cz); world.add(g);
    station('candle', 0, 0, g, { flame: fl, label: 'Mum' });
  }
  { const shr = box(.6, .5, .6, M.wood); shr.position.set(X(6), .25, cc(11)); world.add(shr); const pic = box(.4, .5, .04, M.bloodSheet); pic.position.set(X(6), .75, cc(11)); world.add(pic); }
  candleRoomLight = new THREE.PointLight(0xff8830, 0, 7, 2); candleRoomLight.position.set(X(6), 1, cc(11)); world.add(candleRoomLight);
  wallText('OYNA BENİMLE', X(6), cc(14), 0, -1, 1.5, 2.6);
  // HÜCRELER: yere atılmış şilteler, zincirler
  [16, 18, 20, 22].forEach(x => { const m = box(.9, .12, 1.9, M.bloodSheet); m.position.set(X(x), .06, cc(9)); world.add(m); });
  wallText('ÇIKAR BENİ', X(19), cc(13), 0, -1, 1.6, 2.4);
  // LABORATUVAR: masalar ve yeşil sıvılı kavanozlar
  const jarMat = new THREE.MeshStandardMaterial({ color: 0x4a8a3a, emissive: 0x1a4a10, transparent: true, opacity: .75, roughness: .1 });
  for (let i = 0; i < 2; i++) { table(X(30) + i * 3.2, cc(11), 2.4, .9); for (let k = 0; k < 4; k++) { const j = cyl(.1, .1, .35, jarMat, 10); j.position.set(X(30) + i * 3.2 - .9 + k * .6, .96, cc(11)); world.add(j); } }
  cabinet(X(35), cc(9)); cabinet(X(27), cc(13));
  // DUŞLAR
  for (let i = 0; i < 5; i++) { const sh = cyl(.06, .06, .3, M.metal, 6); sh.rotation.x = Math.PI / 2; sh.position.set(X(2) + i * 2, 2.2, cc(18) - C / 2 + .2); world.add(sh); }
  bloodPool(X(6), cc(22), 1.1); bloodTrail(X(6), cc(22), X(6), cc(17));
  // GÖZLEM ODASI: ortada masa, etrafında sandalye sıraları
  table(X(18), cc(21.5), 1, 2.2); for (let r = 0; r < 2; r++) for (let i = 0; i < 5; i++) chair(X(14.5) + i * 1.6, cc(19) - r * .9 + (r ? 0 : 0), 0, Math.random() < .2);
  // YATAKHANE
  for (let i = 0; i < 4; i++) { bed(X(26) + i * 2.6, cc(18) + .3, 0, i === 2); bed(X(26.5) + i * 2.6, cc(25) - .3, Math.PI, i === 0); }
  // koridor dekoru
  chair(X(20), cc(6), 1, true); bloodPool(X(28), cc(16), .5); bloodTrail(X(13), cc(9), X(13), cc(15));
  wallText('YUKARIDA DA DUYAR', X(20), cc(16), 0, -1, 1.6, 2.8);
  // 2. kat lambaları
  addLamp(9 + O2, 6, { mode: 'flicker' }); addLamp(25 + O2, 6, { mode: 'flicker', intensity: 5 }); addLamp(13 + O2, 11, { mode: 'flicker' });
  addLamp(20 + O2, 16, { mode: 'flicker' }); addLamp(32 + O2, 16, { mode: 'dead' }); addLamp(5 + O2, 3, { mode: 'flicker', intensity: 4 });
  addLamp(32 + O2, 2, { mode: 'flicker', color: 0xffb070, intensity: 5 }); addLamp(31 + O2, 11, { mode: 'flicker', color: 0xb0ffb0, intensity: 4 });
  addLamp(18 + O2, 21, { mode: 'flicker', intensity: 6 }); addLamp(30 + O2, 21, { mode: 'dead' }); addLamp(6 + O2, 21, { mode: 'flicker', intensity: 3.5 });
}
let candleRoomLight;
// merdivenler: zeminde yukarı çıkan basamaklar, 2. katta aşağı inen boşluk
function buildStairs() {
  for (let z = 0; z < GH; z++) for (let x = 0; x < GW; x++) {
    if (cellAt(x, z) !== 'Y') continue;
    const [dx, dz] = wallDir(x, z), up = x < F2X;
    const g = new THREE.Group(); g.position.set(cc(x), 0, cc(z)); g.rotation.y = Math.atan2(dx, dz); world.add(g);
    if (up) {
      for (let i = 0; i < 9; i++) { const st = box(C * .8, .32, .36, M.wood); st.position.set(0, .16 + i * .32, -C / 2 + .2 + i * .33); g.add(st); }
    } else {
      const hole = new THREE.Mesh(new THREE.PlaneGeometry(C * .8, C * .9), new THREE.MeshBasicMaterial({ color: 0x000000 })); hole.rotation.x = -Math.PI / 2; hole.position.set(0, .02, .1); g.add(hole);
      for (let i = 0; i < 3; i++) { const st = box(C * .8, .05, .3, M.wood); st.position.set(0, .03, -1.2 + i * .35); g.add(st); }
    }
    for (const sx of [-1, 1]) { const r = box(.05, .9, C * .9, M.rust); r.position.set(sx * C * .42, .9, 0); g.add(r); }
    const sign = new THREE.Mesh(new THREE.PlaneGeometry(1.4, .36), new THREE.MeshStandardMaterial({ map: plateTexture(up ? '↑ 2. KAT' : '↓ ZEMİN KAT', '#1d3a5a'), emissive: 0xffffff, emissiveIntensity: .06 }));
    sign.material.emissiveMap = sign.material.map;
    sign.position.set(cc(x) + dx * (C / 2 - .03), 2.4, cc(z) + dz * (C / 2 - .03)); sign.lookAt(sign.position.x - dx, 2.4, sign.position.z - dz); world.add(sign);
  }
}

/* ------------------------------ YOL BULMA ---------------------------- */
const passable = (x, z, forMonster) => {
  const ch = cellAt(x, z);
  if (ch === '#' || ch === 'E') return false;
  if (ch === 'X') { const d = doorAt(x, z); return !d.locked; }
  return true;
};
function bfs(sx, sz, tx, tz) {
  if (sx === tx && sz === tz) return [[tx, tz]];
  const prev = new Map(), key = (x, z) => z * GW + x;
  const q = [[sx, sz]]; prev.set(key(sx, sz), null);
  while (q.length) {
    const [x, z] = q.shift();
    const nbs = [[x + 1, z], [x - 1, z], [x, z + 1], [x, z - 1]];
    if (cellAt(x, z) === 'Y') nbs.push(stairPair(x, z));   // merdiven: diğer kat
    for (const [nx, nz] of nbs) {
      const k = key(nx, nz);
      if (prev.has(k) || !passable(nx, nz, true)) continue;
      prev.set(k, key(x, z));
      if (nx === tx && nz === tz) {
        const path = []; let c = k;
        while (c != null) { path.unshift([c % GW, (c / GW) | 0]); c = prev.get(c); }
        return path;
      }
      q.push([nx, nz]);
    }
  }
  return null;
}
function lineClear(x0, z0, x1, z1) { // ızgarada görüş/ses hattı
  const d = Math.hypot(x1 - x0, z1 - z0), n = Math.ceil(d / (C * .25));
  for (let i = 1; i < n; i++) {
    const t = i / n, cx = toCell(lerp(x0, x1, t)), cz = toCell(lerp(z0, z1, t)), ch = cellAt(cx, cz);
    if (ch === '#' || ch === 'E') return false;
    if (ch === 'D' || ch === 'X') { const dd = doorAt(cx, cz); if (dd && dd.open < .5) return false; }
  }
  return true;
}
const floorCells = [];
for (let z = 0; z < GH; z++) for (let x = 0; x < GW; x++) if ('.LFSMBK'.includes(cellAt(x, z))) floorCells.push([x, z]);

/* ------------------------------ YARATIK AI --------------------------- */
const mon = {
  pos: new THREE.Vector3(cc(28), 0, cc(23)), dir: 0, state: 'wander', target: null, path: [], pathI: 0,
  speed: 1.5, stateT: 0, lastHeard: null, trackT: 0, stepT: 0, clickT: 3, growlT: 8, anim: 0, alert: 0,
  stuckT: 0, lastPos: new THREE.Vector3(), headTwitch: 0, twitchT: 0, rage: false, searchN: 0, lockerTarget: null, active: true, frozenT: 0,
};
function monSetTarget(x, z, state) {
  const sx = toCell(mon.pos.x), sz = toCell(mon.pos.z);
  const tx = clamp(toCell(x), 0, GW - 1), tz = clamp(toCell(z), 0, GH - 1);
  let p = bfs(sx, sz, tx, tz);
  if (!p) { // ulaşılamayan hedef: en yakın geçilebilir komşu
    for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { p = bfs(sx, sz, tx + dx, tz + dz); if (p) break; }
  }
  if (!p) return false;
  mon.path = p.map(([cx, cz]) => new THREE.Vector3(cc(cx), 0, cc(cz)));
  mon.path[mon.path.length - 1] = new THREE.Vector3(x, 0, z);
  if (!passable(tx, tz)) mon.path[mon.path.length - 1] = new THREE.Vector3(cc(p[p.length - 1][0]), 0, cc(p[p.length - 1][1]));
  mon.pathI = Math.min(1, mon.path.length - 1);
  if (state) { mon.state = state; mon.stateT = 0; }
  return true;
}
function monWander() {
  // oyuncunun bulunduğu bölgeye hafif yönelimli rastgele dolaşma (oyunu canlı tutar)
  let c;
  if (Math.random() < .72) {
    const px = toCell(player.pos.x), pz = toCell(player.pos.z);
    const near = floorCells.filter(([x, z]) => Math.abs(x - px) + Math.abs(z - pz) < 9 && Math.abs(x - px) + Math.abs(z - pz) > 3);
    c = near.length ? pick(near) : pick(floorCells);
  } else c = pick(floorCells);
  monSetTarget(cc(c[0]) + rand(-.8, .8), cc(c[1]) + rand(-.8, .8), 'wander');
}

/* gürültü olayı: yaratık duyar mı? */
function emitNoise(pos, loud, fromPlayer = true, label = '') {
  if (fromPlayer && label !== 'net') S.noiseLevel = Math.max(S.noiseLevel, loud);
  if (isMP() && !NET.host && label !== 'net') { NET.send({ k: 'noise', x: +pos.x.toFixed(2), z: +pos.z.toFixed(2), l: loud, p: fromPlayer ? 1 : 0 }); return; }
  if (!mon.active || (S.state !== 'play' && label !== 'net')) return;
  const pf = floorOfX(pos.x), mf = floorOfX(mon.pos.x);
  let dist = Math.hypot(pos.x - mon.pos.x, pos.z - mon.pos.z);
  if (pf !== mf) dist = Math.hypot(pos.x - pf * F2X * C - (mon.pos.x - mf * F2X * C), pos.z - mon.pos.z) * 1.6 + 9; // kat arası: üstten/alttan zor duyar
  let range = loud * DIFF[diff].hear * (mon.rage ? 1.4 : 1) * (1 + .12 * ((S.chapter || 1) - 1));
  if (pf === mf && !lineClear(pos.x, pos.z, mon.pos.x, mon.pos.z)) range *= .62;
  if (dist > range) return;
  if (!fromPlayer && loud >= 20) { // şişe / radyo: kovalamayı bile böler
    mon.lastHeard = pos.clone(); mon.trackT = 0;
    A.click(mon.pos.clone().setY(2), 6, .8); mon.frozenT = .25;
    monSetTarget(pos.x, pos.z, 'investigate');
    return;
  }
  const strong = dist < range * .55 || mon.state === 'chase';
  mon.lastHeard = pos.clone();
  mon.alert = Math.min(1, mon.alert + .5);
  if (fromPlayer && strong) {
    if (mon.state !== 'chase') {
      A.screech(mon.pos.clone().setY(2), .9, .6); A.gliss(.06); mon.frozenT = .35;
      if (!S.chaseTip) { S.chaseTip = true; tutor(K('SENİ DUYDU! Köşeyi dön, <kbd>C</kbd> ile eğil ya da dolaba saklan (<kbd>E</kbd>)', 'SENİ DUYDU! Kaç, sonra <b>EĞİL</b> ya da dolaba saklan'), 5); }
    }
    mon.state = 'chase'; mon.stateT = 0; mon.trackT = DIFF[diff].track + 1.2;
    monSetTarget(pos.x, pos.z);
  } else if (mon.state !== 'chase') {
    if (mon.state !== 'investigate') { A.click(mon.pos.clone().setY(2), 6, .7); mon.frozenT = .6; }
    monSetTarget(pos.x, pos.z, 'investigate');
  }
}

function updateMonster(dt) {
  if (!mon.active) { monster.visible = false; return; }
  if (isMP() && !NET.host) { monsterPuppet(dt); return; }
  monster.visible = true;
  const D = DIFF[diff];
  mon.stateT += dt;
  if (mon.frozenT > 0) { mon.frozenT -= dt; }
  // durum makinesi
  let spd = 1.4 * D.speed;
  const pDist = Math.hypot(player.pos.x - mon.pos.x, player.pos.z - mon.pos.z);
  if (mon.state === 'wander') {
    spd = (S.hunting > 0 ? 2.6 : 1.85) * D.speed;
    if (mon.pathI >= mon.path.length) { mon.state = 'idle'; mon.stateT = 0; }
  } else if (mon.state === 'idle') {
    spd = 0;
    if (mon.stateT > rand(.5, 1.6)) monWander();
  } else if (mon.state === 'investigate') {
    spd = (S.hunting > 0 ? 3.7 : 3.1) * D.speed;
    if (mon.pathI >= mon.path.length) { mon.state = 'search'; mon.stateT = 0; mon.searchN = 0; A.click(mon.pos.clone().setY(2), 8, .6); }
  } else if (mon.state === 'search') {
    spd = 1.6 * D.speed;
    if (mon.pathI >= mon.path.length) {
      mon.searchN++;
      if (mon.searchN > 4 || mon.stateT > 12) { mon.rage ? monSetTarget(player.pos.x + rand(-4, 4), player.pos.z + rand(-4, 4), 'investigate') : monWander(); }
      else { const a = rand(0, 6.28), r = rand(1.5, 4.5); const tx = mon.lastHeard ? mon.lastHeard.x : mon.pos.x, tz = mon.lastHeard ? mon.lastHeard.z : mon.pos.z; monSetTarget(tx + Math.cos(a) * r, tz + Math.sin(a) * r); mon.frozenT = rand(.6, 1.6); if (Math.random() < .5) A.click(mon.pos.clone().setY(2), 5, .5); }
    }
  } else if (mon.state === 'chase') {
    spd = D.chaseSpeed * (mon.rage ? 1.04 : 1) + .12 * ((S.chapter || 1) - 1);
    mon.trackT -= dt;
    if (mon.trackT <= 0 && mon.pathI >= mon.path.length) {
      mon.state = 'search'; mon.stateT = 0; mon.searchN = 0; A.growl(mon.pos.clone().setY(2), 1.4, .5, .9);
    } else if (mon.pathI >= mon.path.length && mon.lastHeard) {
      // vardı, oyuncu sessizse koklar
      mon.state = 'search'; mon.stateT = 0; mon.searchN = 0;
    }
  } else if (mon.state === 'locker') { // dolabı parçalıyor
    spd = 0;
    if (S.hidden) S.hidden.target = 1.6;
    if (mon.stateT > .9) { killPlayer(isTouch ? 'Dolapta nefesini duydu. Yaklaşınca NEFES TUT düğmesine bas.' : 'Dolapta nefesini duydu. Yaklaşınca Q ile nefesini tut.'); }
  }
  // saklanan oyuncuyu kokla (dolabın yanında nefes)
  // hareket
  if (mon.frozenT > 0) spd = 0;
  if (spd > 0 && mon.pathI < mon.path.length) {
    const tgt = mon.path[mon.pathI];
    // merdivenden diğer kata geç
    if (tgt.distanceTo(mon.pos) > C * 4 && cellAt(toCell(mon.pos.x), toCell(mon.pos.z)) === 'Y') {
      A.step(.9, mon.pos.clone().setY(.1), true, .7); mon.pos.copy(tgt); mon.pathI++; A.step(.9, mon.pos.clone().setY(.1), true, .7); A.creak(mon.pos.clone().setY(1), .8, .2, .5);
      return;
    }
    // ileri görülebilen noktaya kısayol
    while (mon.pathI + 1 < mon.path.length && lineClear(mon.pos.x, mon.pos.z, mon.path[mon.pathI + 1].x, mon.path[mon.pathI + 1].z) && mon.pos.distanceTo(mon.path[mon.pathI + 1]) < 7) mon.pathI++;
    const t2 = mon.path[mon.pathI];
    const dx = t2.x - mon.pos.x, dz = t2.z - mon.pos.z, d = Math.hypot(dx, dz);
    // kapı açma
    const ncx = toCell(mon.pos.x + dx / (d || 1) * .9), ncz = toCell(mon.pos.z + dz / (d || 1) * .9);
    const door = doorAt(ncx, ncz);
    if (door && door.open < .9 && !door.locked) {
      if (door.target < 1) { door.target = 1; door.swing = Math.sign(Math.random() - .5) || 1; if (isMP()) sendDoor(door); A.slam(new THREE.Vector3(cc(door.x), 1.2, cc(door.z)), mon.state === 'chase' ? 1 : .6); if (mon.state !== 'chase') A.creak(new THREE.Vector3(cc(door.x), 1.2, cc(door.z)), .6, .3, .7); }
      spd *= .3;
    }
    if (d < .25) mon.pathI++;
    else {
      const step = Math.min(d, spd * dt);
      mon.pos.x += dx / d * step; mon.pos.z += dz / d * step;
      const want = Math.atan2(dx, dz);
      let diffA = want - mon.dir; while (diffA > Math.PI) diffA -= Math.PI * 2; while (diffA < -Math.PI) diffA += Math.PI * 2;
      mon.dir += diffA * Math.min(1, dt * 6);
    }
  }
  // takılma kontrolü
  if (mon.lastPos.distanceTo(mon.pos) < .01 && spd > 0) { mon.stuckT += dt; if (mon.stuckT > 2.5) { mon.stuckT = 0; monWander(); } } else mon.stuckT = 0;
  mon.lastPos.copy(mon.pos);

  const moving = spd > 0 && mon.pathI < mon.path.length;
  monsterFx(dt, moving ? spd : 0);
  // yakalama
  if (S.state === 'play' && !S.hidden && !S.down && !(S.invT > 0) && pDist < 1.05 && mon.state !== 'locker') killPlayer(deathTip());
  if (isMP()) for (const r of NET.remotes()) if (!r.down && !r.hid && !(r.inv > 0) && Math.hypot(r.pos.x - mon.pos.x, r.pos.z - mon.pos.z) < 1.05) {
    r.down = 1; r.inv = 5; NET.send({ k: 'caught', to: r.id, id: r.id }); mon.state = 'search'; mon.stateT = 0; mon.searchN = 3;
  }
  // dolaptaki oyuncu: nefes sesi duyulursa
  if (S.hidden && mon.state === 'search' && pDist < 2.2 && !S.holdingBreath && Math.random() < dt * .9) {
    mon.state = 'locker'; mon.stateT = 0; A.screech(mon.pos.clone().setY(2), 1, .9);
  }


}
function monsterFx(dt, spd) { // ses ve animasyon (ev sahibinde de, diğer oyuncularda da çalışır)
  const moving = spd > 0;
  if (moving) {
    mon.anim += dt * spd * 2.3;
    mon.stepT -= dt * spd;
    if (mon.stepT <= 0) { mon.stepT = 1.25; const mp = mon.pos.clone().setY(.05); A.step(mon.state === 'chase' ? 1.1 : .75, mp, true, mon.state === 'chase' ? 1.2 : .8); A.tick(mp, mon.state === 'chase' ? .8 : .45); later(.07, () => A.tick(mp, .4)); }
  }
  mon.clickT -= dt;
  if (mon.clickT <= 0) { mon.clickT = mon.state === 'chase' ? rand(.8, 1.6) : rand(2.5, 5.5); A.click(mon.pos.clone().setY(2.1), (3 + Math.random() * 4) | 0, mon.state === 'wander' ? .4 : .65); }
  mon.growlT -= dt;
  if (mon.growlT <= 0) { mon.growlT = mon.state === 'chase' ? rand(1.8, 3) : rand(7, 15); A.growl(mon.pos.clone().setY(2), rand(1, 2), mon.state === 'chase' ? .9 : .45, mon.state === 'chase' ? 1.15 : 1); }
  if (monsterVoice) {
    A.setPos(monsterVoice.panner, _v1.set(mon.pos.x, 2.1, mon.pos.z));
    monsterVoice.vol.gain.setTargetAtTime(mon.state === 'chase' ? .55 : .3, A.t, .3);
    monsterVoice.rate.frequency.setTargetAtTime(mon.state === 'chase' ? 1.6 : .45, A.t, .5);
  }

  // animasyon
  animateMonster(monster, dt, spd, mon.state === 'chase', mon.state === 'search' || mon.state === 'idle');
  monster.position.copy(mon.pos);
  monster.rotation.y = mon.dir;
}
function animateMonster(m, dt, spd, chase, sniff) {
  const u = m.userData, t = performance.now() / 1000;
  const ph = (m === monster ? mon.anim : t * 9);
  const sw = Math.sin(ph), sw2 = Math.cos(ph);
  const amp = spd > 0 ? Math.min(1, spd / 3) : 0;
  u.body.position.y = Math.abs(sw) * .06 * amp - (chase ? .25 : 0);
  u.spine.rotation.x = chase ? .85 : (sniff ? .55 : .45);
  u.spine.rotation.z = sw * .06 * amp;
  u.neck.rotation.x = chase ? -.7 : (sniff ? -.2 : -.35);
  u.legs.forEach(l => { const s = l.s * sw; l.hip.rotation.x = s * .7 * amp - (chase ? .5 : .1); l.kn.rotation.x = Math.max(0, -s) * 1.1 * amp + (chase ? .6 : .15); });
  u.arms.forEach(a => {
    if (chase) { a.sh.rotation.x = -1.3 + a.s * sw * .5; a.el.rotation.x = -.4; a.sh.rotation.z = a.s * .25; }
    else { a.sh.rotation.x = -a.s * sw * .35 * amp + .15; a.el.rotation.x = -.35 - Math.max(0, a.s * sw2) * .3; a.sh.rotation.z = a.s * .12; }
  });
  // ürkütücü kafa seğirmeleri
  if (m === monster) {
    mon.twitchT -= dt;
    if (mon.twitchT <= 0) { mon.twitchT = rand(.15, sniff ? .6 : 1.8); mon.headTwitch = rand(-.9, .9); }
    u.head.rotation.y = lerp(u.head.rotation.y, mon.headTwitch * (sniff ? 1 : .5), Math.min(1, dt * 22));
    u.head.rotation.z = lerp(u.head.rotation.z, mon.headTwitch * .5, Math.min(1, dt * 18));
    u.jaw.rotation.x = chase ? .6 + Math.sin(t * 20) * .15 : .22 + Math.max(0, Math.sin(t * 2.3)) * .2;
    // ara sıra kafasını yan yatırıp neredeyse ters çevirir
    mon.rollT = (mon.rollT ?? 6) - dt;
    if (mon.rollT <= 0) { mon.rollT = rand(5, 11); mon.rollHold = rand(1, 2); mon.rollDir = Math.random() < .5 ? -1 : 1; }
    if (mon.rollHold > 0) { mon.rollHold -= dt; u.head.rotation.z = lerp(u.head.rotation.z, mon.rollDir * 1.7, Math.min(1, dt * 9)); }
  }
  spreadJaw(u);
}
function spreadJaw(u) { const o = u.jaw.rotation.x; if (u.halves) { u.halves[0].rotation.y = -o * .75; u.halves[1].rotation.y = o * .75; } }
function placeHeadAt(m, target) {
  m.updateMatrixWorld(true);
  const hp = m.userData.head.getWorldPosition(new THREE.Vector3());
  m.position.add(target.clone().sub(hp));
}
function deathTip() {
  return pick([
    'Koşmak onu çağırır. Eğilerek yürü (C).',
    'Tıkırtıları dinle: yaklaşıyorsa kıpırdama ve nefesini tut (Q).',
    'Şişeyi uzağa fırlat (sağ tık / G) — sesin peşinden gider.',
    'Eğilerek açılan kapılar ses çıkarmaz.',
    'Dolaplara saklan (E). Ama yanına gelirse nefesini tut.',
    'Seni göremez. Durursan kaybolursun.',
  ]);
}

/* ============================ KORKU OLAYLARI ========================= */
const events = [];   // zamanlanmış küçük işler
function later(sec, fn) { events.push({ t: S.time + sec, fn }); }
const scares = {
  // 1) koridor sonunda siluet, ışıklar titreyince kaybolur
  silhouette: { cell: [[6, 6], [7, 6], [5, 6]], look: [cc(30), cc(6)], fire() {
    silhouette.position.set(cc(30), 0, cc(6)); silhouette.rotation.y = -Math.PI / 2; silhouette.visible = true;
    animateMonster(silhouette, 0, 0, false, false);
    A.whisper(0, 1.4, .18);
    later(1.4, () => { flicker(1.2); A.sting(.55); });
    later(1.9, () => { silhouette.visible = false; });
  } },
  // 2) kavşaktan geçen sürünen şey
  crawler: { cell: [[11, 12], [11, 13]], look: [cc(11), cc(16)], fire() {
    crawler.visible = true; crawler.userData.run = { t: 0, x0: cc(1), x1: cc(24), z: cc(16) };
    A.screech(new THREE.Vector3(cc(11), 1, cc(16)), 1.1, .9);
    A.sting(.8); shake(.5);
  } },
  // 3) dolaptan düşen ceset
  lockerCorpse: { cell: [[23, 3], [23, 4], [24, 3], [22, 4]], fire() {
    const L = lockerCorpse.L; L.target = 1.9; lockerCorpse.body.visible = true; lockerCorpse.fall = 0;
    A.slam(L.pos.clone().setY(1.2), 1.2); A.sting(.9); shake(.6); flash(.25);
  } },
  // 4) tavandan düşen ceset — tam önüne
  hang: { cell: [[11, 6], [12, 6], [13, 6]], look: [cc(16), cc(6)], fire() {
    const f = _v1.set(Math.sin(player.yaw) * -1, 0, Math.cos(player.yaw) * -1);
    hangBody.position.set(player.pos.x + f.x * 1.8, WALL_H + 1.4, player.pos.z + f.z * 1.8);
    hangBody.visible = true; hangBody.userData.drop = { t: 0 };
    A.slam(hangBody.position.clone().setY(2.6), .7); A.sting(1); later(.3, () => A.creak(hangBody.position, 2.5, .25, .5)); shake(.6);
  } },
  // 5) kendi kendine gelen tekerlekli sandalye
  wheelchair: { cell: [[22, 11], [22, 12], [23, 11], [24, 8], [25, 8], [26, 8], [29, 10], [25, 14]], fire() { wchair.userData.roll = { t: 0 }; A.creak(wchair.position.clone().setY(.5), 3, .22, 1.6); } },
  // 6) radyo konuşuyor
  radio: { cell: [[30, 2], [30, 3], [29, 3], [30, 4]], fire() {
    radioMesh.userData.dial.visible = true;
    A.staticNoise(radioMesh.position, 6, .4);
    later(1.2, () => A.speak('seni... duyuyorum', .45, .01));
    later(4.5, () => A.speak('kaç', .35, .01));
    later(6.5, () => { radioMesh.userData.dial.visible = false; });
    later(5.5, () => emitNoise(radioMesh.position, 22, false));
  } },
  // 7) yukarıda koşan ayak sesleri
  overhead: { cell: [[20, 16], [21, 16], [19, 16]], fire() {
    for (let i = 0; i < 14; i++) later(i * .21, () => { const p = new THREE.Vector3(player.pos.x - 8 + i * 1.2, WALL_H + .4, player.pos.z); A.step(1, p, true, .6); });
    later(3.2, () => A.slam(new THREE.Vector3(player.pos.x + 9, WALL_H + .4, player.pos.z), .8));
    dust(2.5);
  } },
  // 8) müzik kutusu ve kıkırtı
  musicbox: { cell: [[4, 16], [3, 16], [6, 16]], fire() {
    const notes = [[659, .45], [622, .45], [659, .45], [494, .9], [523, .45], [440, .9], [330, .45], [392, .45], [440, 1.2], [330, .45], [415, .45], [494, 1.2]];
    const r = A.musicBox(new THREE.Vector3(cc(5), 1, cc(23)), notes);
    scares.musicbox.node = r.node;
    later(9, () => A.laugh(new THREE.Vector3(cc(7), 1, cc(24))));
  } },
  morgue: { cell: [[5, 18], [5, 19]], fire() {
    if (scares.musicbox.node) { scares.musicbox.node.gain.setValueAtTime(0, A.t); }
    later(.5, () => { A.slam(new THREE.Vector3(cc(7), 1, cc(18)), 1); A.sting(.7); flicker(.6); });
  } },
  // 9) şapel: mumlar sönüyor + fısıltı
  chapel: { cell: [[12, 18], [13, 18], [14, 18]], fire() {
    A.whisper(-1, 2.5, .3); later(1.2, () => A.whisper(1, 2.5, .3));
    later(2.4, () => { S.candlesOut = true; candles.forEach(c => c.visible = false); A.gasp(.15); });
    later(3.4, () => { A.laugh(new THREE.Vector3(cc(14), 1, cc(24))); });
    later(6, () => { S.candlesOut = false; candles.forEach(c => c.visible = true); A.sting(.4); });
  } },
  // 10) lobi: kapılar arkandan kapanır
  lobby: { cell: [[22, 18], [27, 18], [22, 19], [27, 19]], fire() {
    [doorAt(22, 17), doorAt(27, 17)].forEach(d => { if (d.open > .2) { d.target = 0; } });
    A.slam(new THREE.Vector3(cc(24), 1.2, cc(17)), 1.1); blackout(1.5);
    later(.4, () => A.whisper(0, 1.4, .4, camera.localToWorld(new THREE.Vector3(0, 0, .6))));
    later(1.6, () => A.sting(.6));
  } },
};

function flicker(dur) { S.flickerT = Math.max(S.flickerT || 0, dur); }
function blackout(dur) { S.blackT = Math.max(S.blackT || 0, dur); }
function shake(a) { player.shake = Math.max(player.shake, a); }
function flash(a) { const f = $('flash'); f.style.transition = 'none'; f.style.opacity = a; requestAnimationFrame(() => { f.style.transition = 'opacity .5s'; f.style.opacity = 0; }); }
function redFlash(a) { const f = $('redflash'); f.style.transition = 'none'; f.style.opacity = a; requestAnimationFrame(() => { f.style.transition = 'opacity 1.2s'; f.style.opacity = 0; }); }

// toz parçacıkları (fener ışığında)
const dustGeo = new THREE.BufferGeometry(); const DN = 260; const dpos = new Float32Array(DN * 3);
for (let i = 0; i < DN; i++) { dpos[i * 3] = rand(-4, 4); dpos[i * 3 + 1] = rand(0, 3); dpos[i * 3 + 2] = rand(-4, 4); }
dustGeo.setAttribute('position', new THREE.BufferAttribute(dpos, 3));
const dustPts = new THREE.Points(dustGeo, new THREE.PointsMaterial({ color: 0xbbb4a0, size: .018, transparent: true, opacity: .55, depthWrite: false }));
scene.add(dustPts);
let dustFall = 0;
function dust(t) { dustFall = t; }

// yüz korkusu (2. sigortada)
function faceJumpscare() {
  S.flashForcedOff = 1.1;
  A.flashClick();
  later(1.1, () => {
    faceScare.visible = true; faceScare.rotation.set(0, 0, 0); faceScare.position.set(0, 0, 0);
    const u = faceScare.userData; u.spine.rotation.x = .9; u.neck.rotation.x = -.9; u.jaw.rotation.x = .75; u.head.rotation.z = .35; spreadJaw(u);
    u.arms.forEach(a => { a.sh.rotation.x = -1.7; a.sh.rotation.z = a.s * .8; });
    faceScare.updateMatrixWorld(true);
    const hl = camera.worldToLocal(u.head.getWorldPosition(new THREE.Vector3()));
    faceScare.position.set(-hl.x, -hl.y - .1, -hl.z - .62);
    A.screech(null, 1.0, 1.1); A.sting(1); shake(1); flash(.12);
    later(.42, () => { faceScare.visible = false; S.flashForcedOff = .3; });
    // gerçek yaratık yakına gelir
    later(1, () => {
      const c = floorCells.filter(([x, z]) => { const d = Math.hypot(cc(x) - player.pos.x, cc(z) - player.pos.z); return d > 12 && d < 20; });
      if (c.length && !mon.rage) { const p = pick(c); mon.pos.set(cc(p[0]), 0, cc(p[1])); monSetTarget(player.pos.x, player.pos.z, 'investigate'); }
    });
  });
}

/* ======================= OYUNCU ETKİLEŞİMLERİ ======================== */
let focus = null; // {kind, obj, text}
function findFocus() {
  if (S.down) return null;
  if (S.hidden) return { kind: 'unhide', text: 'Dolaptan çık' };
  const eye = _v1.set(player.pos.x, player.h, player.pos.z);
  const fwd = camera.getWorldDirection(_v2);
  let best = null, bd = 2.3;
  const consider = (p, maxD, o) => {
    const to = _v3.set(p.x - eye.x, (p.y ?? eye.y) - eye.y, p.z - eye.z);
    const d = to.length(); if (d > maxD) return;
    to.normalize(); const dot = to.dot(fwd);
    if (dot < .82 - (1 / (d + .5)) * .25) return;
    const score = d * (1.6 - dot);
    if (score < bd) { bd = score; best = o; }
  };
  for (const it of items) if (!it.taken && it.mesh.visible) {
    const txt = { fuse: 'Sigortayı al', battery: 'Pili al', bottle: 'Şişeyi al', card: 'Kartı al', note: 'Notu oku', doll: 'Bebeği al', codenote: 'Kanlı notu oku' }[it.type];
    consider(it.mesh.position, 2.2, { kind: 'item', obj: it, text: txt });
  }
  for (const d of doors) {
    const p = new THREE.Vector3(cc(d.x), 1.2, cc(d.z));
    let txt = d.open > .5 ? 'Kapıyı kapat' : 'Kapıyı aç';
    if (d.locked) txt = 'Kilitli';
    consider(p, 2.6, { kind: 'door', obj: d, text: txt + (d.locked ? '' : (S.crouch ? '  (sessiz)' : '')) });
  }
  for (const L of lockers) if (L.hideable) consider(L.pos.clone().setY(1.2).addScaledVector(L.facing, .4), 2.0, { kind: 'locker', obj: L, text: 'Dolaba saklan' });
  // teslim noktaları ve istasyonlar
  for (const t of chTasks()) {
    const st = S.tasks[t.id]; if (st.done) continue;
    if (t.deliver) {
      const ok = st.got >= needOf(t) && canDoTask(t);
      consider(deliverPos(t.deliver), 2.6, { kind: ok ? 'deliver' : 'none', obj: t, text: ok ? t.dlabel : `${t.dmk} — ${st.got}/${needOf(t)} ${t.mk.toLocaleLowerCase('tr-TR')}` });
    } else for (const stn of STATIONS) if (stn.type === t.station && !stn.done)
      consider(stn.pos, 2.4, canDoTask(t) ? { kind: 'station', obj: stn, text: stn.type === 'valve' ? 'Vanayı aç (GÜRÜLTÜLÜ!)' : 'Mumu yak' } : { kind: 'none', text: `${ROLES[t.role].name} görevi — önce kendi görevlerini bitir` });
  }
  if (S.chapter === 2 && !S.ritual && chTasks().every(taskDone)) consider(ALTAR.clone().setY(1), 2.6, { kind: 'ritual', text: 'AYİNİ BAŞLAT' });
  // yerdeki arkadaş
  if (isMP()) for (const r of NET.remotes()) if (r.down) consider(r.pos.clone().setY(.4), 2.4, { kind: 'revive', obj: r, text: `${r.name} adlı arkadaşını kaldır (basılı tut)` });
  // merdivenler
  for (const [x, z] of STAIRS) for (const f of [0, 1]) { const p = new THREE.Vector3(cc(x + f * F2X), 1.2, cc(z)); consider(p, 2.6, { kind: 'stairs', obj: [x + f * F2X, z], text: f ? 'Aşağı in (zemin kat)' : 'Yukarı çık (2. kat)' }); }
  if (S.chapter === 3 && !S.safeOpen) consider(SAFE_POS.clone().add(new THREE.Vector3(0, .25, .25)), 2.4, { kind: 'safe', text: S.codeKnown ? `Kasaya şifreyi gir (${S.code})` : 'Kasa — şifre gerekli' });
  const gp = new THREE.Vector3(cc(27), 1.3, cc(26) - C / 2);
  consider(gp, 2.8, { kind: 'gate', text: S.keycard ? 'Kartı okut (basılı tut)' : 'Kart okuyucu — çıkış kartı gerekli' });
  return best;
}
let holdT = 0;
function interact(dt, pressed, held) {
  if (!focus) { holdT = 0; return; }
  if (focus.kind === 'revive') {
    if (held) { holdT += dt; S.holdMax = 2.5; if (holdT >= 2.5) { const r = focus.obj; NET.send({ k: 'revive', to: r.id, id: r.id }); r.down = 0; r.inv = 4; holdT = 0; sub(`${r.name} ayağa kalktı!`, 2); A.gasp(.3); } }
    else holdT = Math.max(0, holdT - dt * 2);
    return;
  }
  S.holdMax = 3;
  if (focus.kind === 'gate' && S.keycard) {
    if (held) {
      if (holdT === 0) { A.siren(12); emitNoise(new THREE.Vector3(cc(27), 1, cc(25)), 60, true); mon.rage = true; sub('OKUYUCU YAVAŞ... BEKLE!', 2.5); }
      holdT += dt;
      if (holdT >= 3) win();
      // okuyucu bip
      if (((holdT * 3) | 0) !== (((holdT - dt) * 3) | 0)) { const t = A.t, o = A.ctx.createOscillator(); o.frequency.value = 1200; const g = A.ctx.createGain(); A.env(g, t, .003, .1, .08); o.connect(g); g.connect(A.master); o.start(t); o.stop(t + .1); }
    } else holdT = Math.max(0, holdT - dt * 2);
    return;
  }
  holdT = 0;
  if (!pressed) return;
  const f = focus;
  if (f.kind === 'item') takeItem(f.obj);
  else if (f.kind === 'door') {
    const d = f.obj;
    if (d.locked) {
      A.slam(new THREE.Vector3(cc(d.x), 1.2, cc(d.z)), .2); emitNoise(player.pos, 3);
      sub(S.chapter < 3 ? 'Kilitli. İçeriden bir şey nefes alıyor...' : 'Kilitli.');
      if (S.chapter < 3 && Math.random() < .5) later(.6, () => A.knock(new THREE.Vector3(cc(d.x), 1.3, cc(d.z)), 3, 1.3));
      return;
    }
    d.target = d.target > .5 ? 0 : 1;
    // açılış yönü: oyuncudan uzağa
    const p = new THREE.Vector3(cc(d.x), 0, cc(d.z));
    d.swing = d.ew ? (player.pos.z < p.z ? -1 : 1) : (player.pos.x < p.x ? 1 : -1);
    const quiet = S.crouch;
    d.speed = quiet ? .7 : 2.6;
    A.creak(p.clone().setY(1.2), quiet ? 1.4 : .7, quiet ? .05 : .32, quiet ? .8 : 1);
    if (d.target === 0 && !quiet) later(.35, () => A.slam(p.clone().setY(1.2), .5));
    emitNoise(player.pos, quiet ? 1.5 : 8.5);
    sendDoor(d);
    if (d.target === 1) doorSurprise(d);
  }
  else if (f.kind === 'locker') hide(f.obj);
  else if (f.kind === 'safe') openKeypad();
  else if (f.kind === 'deliver') doDeliver(f.obj);
  else if (f.kind === 'station') doStation(f.obj);
  else if (f.kind === 'ritual') { ritual(); NET.send({ k: 'ritual' }); }
  else if (f.kind === 'stairs') useStairs(f.obj);
  else if (f.kind === 'unhide') unhide();
}
function takeItem(it) {
  it.taken = true; it.mesh.visible = false;
  emitNoise(player.pos, 2.5);
  if (it.type === 'note') { A.pickup(); showNote(it.text, it.noteId); it.taken = false; it.mesh.visible = true; return; }
  A.pickup();
  NET.send({ k: 'take', i: it.id });
  if (it.task) { takeTaskItem(it, false); }
  else if (it.type === 'battery') { S.battery = Math.min(1, S.battery + .55); sub('Pil (+%55)'); }
  else if (it.type === 'bottle') { S.bottles++; sub('Şişe. Fırlat: sağ tık / G'); }
  else if (it.type === 'codenote') readCode(it);
  else if (it.type === 'card') {
    S.keycard = true; sub('KARTI ALDIN. ÇIKIŞA KOŞ!', 3);
    mon.rage = true; duck(1);
    later(1, () => { screamer(true); });
    if (!isMP() || NET.host) cardChase();
    saveCheckpoint();
  }
  updateTasks();
}
function powerOn() {
  S.power = true;
  fuseBox.lever.rotation.x = -1; fuseBox.warn.color.set(0x30ff40);
  A.boom(1); A.siren(5);
  lamps.forEach(L => { if (L.power) { L.on = true; L.mode = L.mode === 'dead' ? 'flicker' : 'alarm'; } });
  later(.4, () => { blackout(.3); });
  sub('ELEKTRİK GELDİ...', 3);
  if (!isMP() || NET.host) later(3.2, () => { startChapter(2); NET.send({ k: 'chapter', n: 2 }); });
  // güç gelince her yer gürültü — yaratık öfkelenir
  emitNoise(fuseBox.pos, 40, true);
  later(2, () => A.screech(mon.pos.clone().setY(2), 1.6, 1));
  saveCheckpoint();
  updateTasks();
}
function hide(L) {
  S.hidden = L; L.target = 1;
  A.creak(L.pos.clone().setY(1.2), .4, .15, 1.6);
  emitNoise(player.pos, 3);
  later(.35, () => { L.target = 0; A.slam(L.pos.clone().setY(1.2), .25); });
  player.prevPos = player.pos.clone();
  player.pos.copy(L.pos);
  player.yaw = Math.atan2(-L.facing.x, -L.facing.z);
  player.pitch = 0;
  $('lockerView').style.opacity = 1;
}
function unhide() {
  const L = S.hidden; S.hidden = null; L.target = 1;
  A.creak(L.pos.clone().setY(1.2), .4, .15, 1.6);
  emitNoise(L.pos, 3);
  later(.5, () => { L.target = 0; });
  player.pos.copy(L.pos).addScaledVector(L.facing, .95);
  $('lockerView').style.opacity = 0;
}
// fırlatılan şişeler
const thrown = [];
function throwBottle() {
  if (S.bottles <= 0) { sub('Şişen yok.'); return; }
  if (S.hidden) return;
  S.bottles--; updateTasks();
  const m = new THREE.Group(); const b = cyl(.045, .05, .22, M.glass, 8); m.add(b);
  const dir = camera.getWorldDirection(new THREE.Vector3());
  m.position.set(player.pos.x, player.h - .1, player.pos.z).addScaledVector(dir, .4);
  scene.add(m);
  thrown.push({ m, v: dir.multiplyScalar(13).add(new THREE.Vector3(0, 3.2, 0)), life: 0 });
  A.gasp(.08);
}
function updateThrown(dt) {
  for (let i = thrown.length - 1; i >= 0; i--) {
    const t = thrown[i]; t.life += dt;
    t.v.y -= 14 * dt;
    const np = t.m.position.clone().addScaledVector(t.v, dt);
    const hitWall = !passable(toCell(np.x), toCell(np.z)) || ((cellAt(toCell(np.x), toCell(np.z)) === 'D') && (doorAt(toCell(np.x), toCell(np.z)).open < .5));
    t.m.rotation.x += dt * 12; t.m.rotation.z += dt * 7;
    if (hitWall || np.y < .05 || np.y > WALL_H - .05 || t.life > 4) {
      const p = t.m.position.clone();
      A.glass(p, 1); emitNoise(p, 24, false, 'bottle');
      // cam kırıkları
      for (let k = 0; k < 7; k++) { const s = box(.04, .01, .03, M.glass); s.position.set(p.x + rand(-.4, .4), .01, p.z + rand(-.4, .4)); s.rotation.y = rand(0, 6); world.add(s); }
      scene.remove(t.m); thrown.splice(i, 1);
    } else t.m.position.copy(np);
  }
}

/* ============================ HUD / UI =============================== */
function updateTasks() {
  const ch = S.chapter || 1, t = [`<div class="h">— BÖLÜM ${ch} · ${CHAPTERS[ch].t} —</div>`];
  if (ch <= 2) {
    for (const k of chTasks()) {
      const st = S.tasks[k.id], need = needOf(k), mine = myRoles().includes(k.role);
      const who = isMP() ? `<span style="color:${ROLES[k.role].css}">${NET.nameOfRole(k.role)}</span> · ` : '';
      const prog = st.done ? '✔' : k.item ? (st.got >= need ? 'TESLİM ET' : `${st.got}/${need}`) : `${st.got}/${need}`;
      t.push(`<div class="${st.done ? 'done' : mine || myTasksDone() ? 'cur' : ''}" style="${!mine && isMP() && !st.done ? 'opacity:.6' : ''}">${who}${k.label} <b>${prog}</b></div>`);
    }
    if (isMP() && myTasksDone() && !chTasks().every(taskDone)) t.push('<div style="color:#7fd4ff">» Görevlerin bitti: arkadaşlarına yardım et!</div>');
    if (ch === 2 && chTasks().every(taskDone)) t.push(`<div class="${S.ritual ? 'done' : 'cur'}">Şapelde ayini başlat</div>`);
  }
  if (ch === 3) {
    const line = (done, cur, txt) => t.push(`<div class="${done ? 'done' : cur ? 'cur' : ''}">${txt}</div>`);
    line(S.codeKnown, !S.codeKnown, 'Kasanın şifresini bul'); line(S.keycard, S.codeKnown && !S.keycard, 'Başhekimin kasasını aç'); line(false, S.keycard, 'Lobideki ÇIKIŞTAN kaç');
  }
  $('tasks').innerHTML = t.join('');
  const carry = chTasks().filter(k => k.item && !S.tasks[k.id].done && S.tasks[k.id].got).map(k => `${k.mk} × ${S.tasks[k.id].got}`).join('<br>');
  $('inv').innerHTML = `🍾 Şişe × ${S.bottles}<br>${carry ? carry + '<br>' : ''}${S.codeKnown && !S.keycard ? '🔢 Şifre: ' + S.code + '<br>' : ''}${S.keycard ? '💳 Çıkış kartı' : ''}<br><span style="color:#8f8">📷 Kamera ${Math.round((S.nvBatt ?? 1) * 100)}%</span>`;
}
let subT = 0, msgT = 0;
function sub(text, dur = 2.2) { $('sub').textContent = text; $('sub').style.opacity = 1; subT = dur; }
function msg(html, dur = 3) { $('msg').innerHTML = html; $('msg').style.opacity = 1; msgT = dur; }
function showNote(text, id) {
  S.notesRead.add(id);
  $('noteText').innerHTML = text.replace(/</g, '&lt;') + '<i>[E / tıkla] kapat</i>';
  $('note').style.display = 'flex'; S.reading = true;
}
function closeNote() { $('note').style.display = 'none'; S.reading = false; }
for (let i = 0; i < 22; i++) $('noiseMeter').appendChild(document.createElement('i'));
const meterBars = [...$('noiseMeter').children];

function drawMap() {
  const f = floorOfX(player.pos.x), X0 = f * F2X, LW = 37;
  const cv = $('mapCanvas'), x = cv.getContext('2d'), s = 18, ox = (cv.width - LW * s) / 2 - X0 * s, oz = (cv.height - GH * s) / 2 + 10;
  x.fillStyle = '#c9bc98'; x.fillRect(0, 0, cv.width, cv.height);
  x.font = '20px "Special Elite", monospace'; x.fillStyle = '#3a2a1a'; x.textAlign = 'center';
  x.fillText(f ? 'AZİZ LAZAR SANATORYUMU — 2. KAT' : 'AZİZ LAZAR SANATORYUMU — ZEMİN KAT', cv.width / 2, 26);
  for (let z = 0; z < GH; z++) for (let cx = X0; cx < X0 + LW; cx++) {
    const ch = cellAt(cx, z); if (ch === '#') continue;
    const seen = S.visited.has(z * GW + cx);
    x.fillStyle = seen ? 'rgba(60,40,20,.25)' : 'rgba(60,40,20,.06)';
    x.fillRect(ox + cx * s, oz + z * s, s, s);
    if (ch === 'D' || ch === 'X') { x.fillStyle = ch === 'X' ? '#802' : '#654'; x.fillRect(ox + cx * s + 4, oz + z * s + 4, s - 8, s - 8); }
    if (ch === 'Y') { x.fillStyle = '#1a3a6a'; x.font = 'bold 14px monospace'; x.fillText('⇅', ox + cx * s + s / 2, oz + z * s + s - 4); }
  }
  x.strokeStyle = '#2a1a0a'; x.lineWidth = 2;
  for (let z = 0; z < GH; z++) for (let cx = X0; cx < X0 + LW; cx++) {
    if (cellAt(cx, z) === '#') continue;
    const px = ox + cx * s, pz = oz + z * s;
    if (cellAt(cx, z - 1) === '#') { x.beginPath(); x.moveTo(px, pz); x.lineTo(px + s, pz); x.stroke(); }
    if (cellAt(cx, z + 1) === '#' || cellAt(cx, z + 1) === 'E') { x.beginPath(); x.moveTo(px, pz + s); x.lineTo(px + s, pz + s); x.stroke(); }
    if (cellAt(cx - 1, z) === '#') { x.beginPath(); x.moveTo(px, pz); x.lineTo(px, pz + s); x.stroke(); }
    if (cellAt(cx + 1, z) === '#') { x.beginPath(); x.moveTo(px + s, pz); x.lineTo(px + s, pz + s); x.stroke(); }
  }
  x.font = '11px "Special Elite", monospace'; x.fillStyle = '#3a2a1a';
  ROOMS.filter(r => (r.f || 0) === f).forEach(r => x.fillText(r.n.toLocaleUpperCase('tr-TR'), ox + (r.x0 + r.x1 + 1) / 2 * s, oz + (r.z0 + r.z1 + 1) / 2 * s));
  if (!f) { x.fillStyle = '#106020'; x.fillText('ÇIKIŞ', ox + 27.5 * s, oz + 26.9 * s); }
  // takım arkadaşları
  if (typeof NET !== 'undefined' && NET.on) for (const r of NET.remotes()) {
    if (floorOfX(r.pos.x) !== f) continue;
    x.fillStyle = ROLES[r.role]?.css || '#fff'; x.beginPath(); x.arc(ox + r.pos.x / C * s, oz + r.pos.z / C * s, 5, 0, 7); x.fill();
    x.font = '10px monospace'; x.fillText(r.name, ox + r.pos.x / C * s, oz + r.pos.z / C * s - 8);
  }
  // oyuncu
  const px = ox + player.pos.x / C * s, pz = oz + player.pos.z / C * s;
  x.save(); x.translate(px, pz); x.rotate(-player.yaw + Math.PI);
  x.fillStyle = '#a00'; x.beginPath(); x.moveTo(0, -8); x.lineTo(5, 6); x.lineTo(-5, 6); x.fill(); x.restore();
  x.font = '13px "Special Elite", monospace'; x.fillStyle = '#5a1a0a';
  x.fillText('"O" kroki üzerinde değil. Hiçbir zaman değil.', cv.width / 2, cv.height - 10);
}

/* ============================== GİRDİ ================================ */
const keys = {};
let mouseLocked = false, ePressed = false, eHeld = false;
addEventListener('keydown', e => {
  if (e.repeat && e.code !== 'KeyE') { keys[e.code] = true; return; }
  keys[e.code] = true;
  if (S.state !== 'play') { if (e.code === 'Escape' && S.state === 'pause') resume(); return; }
  if (S.keypad) { e.preventDefault(); if (/^Digit\d$|^Numpad\d$/.test(e.code)) kpPress(e.code.slice(-1)); else if (e.code === 'Backspace') kpPress('del'); else if (e.code === 'Enter' || e.code === 'NumpadEnter') kpPress('ok'); else if (e.code === 'Escape' || e.code === 'KeyE') closeKeypad(); return; }
  if (S.reading) { if (e.code === 'KeyE' || e.code === 'Escape' || e.code === 'Space') closeNote(); return; }
  if (e.code === 'KeyE' && !e.repeat) ePressed = true;
  if (e.code === 'KeyF') toggleFlash();
  if (e.code === 'KeyG') throwBottle();
  if (e.code === 'KeyH') showGuide();
  if (e.code === 'KeyV') toggleNV();
  if (e.code === 'KeyT') pingForward();
  if (isMP() && /^Digit[1-4]$/.test(e.code)) sendChat(+e.code.slice(5) - 1);
  if (e.code === 'KeyM' || e.code === 'Tab') { e.preventDefault(); $('mapView').style.display = 'flex'; drawMap(); }
  if (e.code === 'KeyC') { S.crouchToggle = !S.crouchToggle; }
  if (e.code === 'Escape') pause();
});
addEventListener('keyup', e => {
  keys[e.code] = false;
  if (e.code === 'KeyM' || e.code === 'Tab') $('mapView').style.display = 'none';
});
canvas.addEventListener('mousedown', e => {
  if (S.state !== 'play') return;
  if (!mouseLocked && !isTouch) { canvas.requestPointerLock?.(); return; }
  if (S.reading) { closeNote(); return; }
  if (e.button === 2) throwBottle();
  if (e.button === 0) ePressed = true, eHeld = true;
});
addEventListener('mouseup', e => { if (e.button === 0) eHeld = false; });
$('note').addEventListener('click', closeNote);
addEventListener('contextmenu', e => e.preventDefault());
document.addEventListener('pointerlockchange', () => {
  mouseLocked = document.pointerLockElement === canvas;
  if (!mouseLocked && S.state === 'play' && !isTouch && !S.keypad) pause();
});
addEventListener('mousemove', e => {
  if (!mouseLocked || S.state !== 'play') return;
  look(e.movementX, e.movementY, .0022);
});
function look(dx, dy, k) {
  player.yaw -= dx * k * sens;
  player.pitch = clamp(player.pitch - dy * k * sens, -1.35, 1.35);
}
function toggleFlash() {
  if (S.battery <= 0) { A.flashClick(); return; }
  S.flashOn = !S.flashOn; A.flashClick(); emitNoise(player.pos, 1.2);
}
addEventListener('blur', () => { if (S.state === 'play') pause(); });
document.addEventListener('visibilitychange', () => { if (document.hidden && S.state === 'play') pause(); });

/* ---- dokunmatik ---- */
const touch = { mx: 0, mz: 0, stickId: null, lookId: null, lx: 0, ly: 0, run: false, breath: false, use: false };
if (isTouch) {
  document.body.classList.add('touch');
  const stick = $('stick'), knob = $('knob');
  stick.addEventListener('touchstart', e => { e.preventDefault(); const t = e.changedTouches[0]; touch.stickId = t.identifier; stickMove(t); }, { passive: false });
  const stickMove = t => {
    const r = stick.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    let dx = t.clientX - cx, dy = t.clientY - cy; const d = Math.hypot(dx, dy), max = r.width / 2;
    if (d > max) { dx *= max / d; dy *= max / d; }
    knob.style.transform = `translate(${dx}px,${dy}px)`;
    touch.mx = dx / max; touch.mz = dy / max;
  };
  addEventListener('touchmove', e => {
    for (const t of e.changedTouches) {
      if (t.identifier === touch.stickId) stickMove(t);
      else if (t.identifier === touch.lookId) { look(t.clientX - touch.lx, t.clientY - touch.ly, .0048); touch.lx = t.clientX; touch.ly = t.clientY; }
    }
  }, { passive: false });
  addEventListener('touchend', e => {
    for (const t of e.changedTouches) {
      if (t.identifier === touch.stickId) { touch.stickId = null; touch.mx = touch.mz = 0; knob.style.transform = ''; }
      if (t.identifier === touch.lookId) touch.lookId = null;
    }
  });
  canvas.addEventListener('touchstart', e => {
    if (S.state !== 'play') return;
    if (S.reading) { closeNote(); return; }
    for (const t of e.changedTouches) if (touch.lookId == null) { touch.lookId = t.identifier; touch.lx = t.clientX; touch.ly = t.clientY; }
  }, { passive: true });
  const btn = (id, down, up) => { const el = $(id); el.addEventListener('touchstart', e => { e.preventDefault(); e.stopPropagation(); down(el); }, { passive: false }); el.addEventListener('touchend', e => { e.preventDefault(); up && up(el); }, { passive: false }); };
  btn('tRun', el => { touch.run = true; el.classList.add('on'); }, el => { touch.run = false; el.classList.remove('on'); });
  btn('tCrouch', el => { S.crouchToggle = !S.crouchToggle; el.classList.toggle('on', S.crouchToggle); });
  btn('tUse', () => { if (S.reading) closeNote(); else { ePressed = true; touch.use = true; } }, () => { touch.use = false; });
  btn('tLight', () => toggleFlash());
  btn('tThrow', () => throwBottle());
  btn('tGuide', () => showGuide());
  btn('tNV', () => toggleNV());
  btn('tPing', () => pingForward());
  btn('tBreath', el => { touch.breath = true; el.classList.add('on'); }, el => { touch.breath = false; el.classList.remove('on'); });
  btn('tPause', () => pause());
  btn('tMap', () => { const mv = $('mapView'); if (mv.style.display === 'flex') mv.style.display = 'none'; else { mv.style.display = 'flex'; drawMap(); } });
  $('mapView').addEventListener('touchstart', () => { $('mapView').style.display = 'none'; });
}

/* =========================== OYUN AKIŞI ============================== */
function saveCheckpoint() {
  S.checkpoint = {
    pos: player.pos.clone(), yaw: player.yaw,
    tasks: JSON.parse(JSON.stringify(S.tasks)), stations: STATIONS.map(x => x.done), power: S.power, keycard: S.keycard, bottles: Math.max(1, S.bottles), battery: Math.max(.5, S.battery),
    taken: items.map(i => i.taken), triggered: new Set(S.triggered), rage: mon.rage,
    doors: doors.map(d => ({ locked: d.locked })),
    chapter: S.chapter, ritual: S.ritual, codeKnown: S.codeKnown, safeOpen: S.safeOpen,
  };
}
function loadCheckpoint() {
  const c = S.checkpoint;
  player.pos.copy(c.pos); player.yaw = c.yaw; player.pitch = 0;
  S.tasks = JSON.parse(JSON.stringify(c.tasks)); S.power = c.power; S.keycard = c.keycard; S.bottles = c.bottles; S.battery = c.battery;
  S.stamina = 1; S.breath = 1; S.hidden = null; S.flashOn = true; S.triggered = new Set(c.triggered);
  S.chapter = c.chapter; S.ritual = c.ritual; applyStations(c.stations); S.stalk = null; S.cryArm = null; S.grinT = 0; grin.visible = false; crumbs.length = 0;
  $('lockerView').style.opacity = 0;
  S.codeKnown = c.codeKnown; S.safeOpen = c.safeOpen; safeDoor.rotation.y = S.safeOpen ? -1.7 : 0; safeDoor.userData.led.material = S.safeOpen ? M.green : M.red;
  items.forEach((it, i) => { it.taken = c.taken[i]; });
  refreshItemVisibility();
  S.hunting = 0; S.huntT = 45; S.halluT = 0; S.hallu = 0; halluFigs.forEach(f => f.visible = false); watchers.forEach(w => { w.active = false; w.g.visible = false; }); S.fall = null; hangBody.visible = false; closeKeypad();
  doors.forEach((d, i) => { d.locked = c.doors[i].locked; if (d.light) d.light.material = d.locked ? M.red : M.green; });
  fuseLights.forEach((f, i) => { const on = S.tasks.fuse.done && i < needOf(TASK_BY_ID.fuse); f.fz.visible = on; f.lt.material = on ? M.green : M.red; });
  if (!S.power) { lamps.forEach(L => { if (L.power) { L.on = false; L.mode = L.cell[0] === 11 && L.cell[1] === 11 ? 'dead' : 'off'; } }); fuseBox.lever.rotation.x = 0; fuseBox.warn.color.set(0xff3020); }
  mon.rage = c.rage;
  // yaratığı uzağa koy
  const far = floorCells.filter(([x, z]) => Math.hypot(cc(x) - player.pos.x, cc(z) - player.pos.z) > 22);
  const p = pick(far.length ? far : floorCells); mon.pos.set(cc(p[0]), 0, cc(p[1])); mon.state = 'idle'; mon.stateT = 0; mon.path = []; mon.pathI = 0; mon.trackT = 0;
  events.length = 0; holdT = 0;
  silhouette.visible = crawler.visible = faceScare.visible = peekHead.visible = shadowRunner.visible = child.visible = false;
  actorRuns.length = 0; S.behindArm = null; S.dirT = 20; S.duckT = 0; guideT = 0; guideDots.forEach(d => d.visible = false);
  if (!S.ritual) { resetAltar(); if (S.tasks.doll.done) altarDolls.forEach(d => d.visible = true); if (S.tasks.page.done) altarPages.forEach(d => d.visible = true); }
  scare3d.ceil = scare3d.sprint = null; if (lunger) lunger.visible = false;
  if (S.power && S.chapter === 1) later(1, () => startChapter(2));
  updateTasks();
}
function newGame(seed = (Math.random() * 1e9) | 0) {
  // nesneleri tohumla yerleştir (çok oyunculuda herkes aynı dünyayı görür)
  RNG = mulberry32(seed); S.seed = seed;
  items.forEach(it => { world.remove(it.mesh); }); items.length = 0;
  const N = id => needOf(TASK_BY_ID[id]), tag = (it, task, ch) => { it.task = task; it.ch = ch; return it; };
  shuffle(fuseSpots).slice(0, N('fuse')).forEach(([x, z]) => tag(addItem('fuse', x, z), 'fuse', 1));
  shuffle(FILE_SPOTS).slice(0, N('file')).forEach(([x, z]) => tag(addItem('file', x, z), 'file', 1));
  shuffle(DOLL_SPOTS).slice(0, N('doll')).forEach(([x, z]) => tag(addDoll(x, z), 'doll', 2));
  shuffle(PAGE_SPOTS).slice(0, N('page')).forEach(([x, z]) => tag(addItem('page', x, z), 'page', 2));
  addItem('card', 34, 9, { px: cc(34), pz: cc(10) - .1 });
  const bottleSpots = [[2, 2], [12, 3], [20, 2], [32, 4], [3, 9], [16, 13], [27, 12], [8, 24], [15, 22], [30, 24], [24, 16], [33, 6], [11, 9], [5 + F2X, 6], [20 + F2X, 9], [30 + F2X, 23], [8 + F2X, 12], [17 + F2X, 2]];
  shuffle(bottleSpots).slice(0, 10).forEach(([x, z]) => addItem('bottle', x, z));
  const battSpots = [[4, 4], [14, 2], [28, 4], [7, 13], [18, 9], [28, 9], [2, 20], [16, 24], [21, 24], [35, 12], [9, 6], [12 + F2X, 6], [24 + F2X, 2], [6 + F2X, 22], [32 + F2X, 12]];
  shuffle(battSpots).slice(0, 7).forEach(([x, z]) => addItem('battery', x, z));
  const noteSpots = [[2, 4, 0], [14, 9, 1], [9, 16, 2], [4 + F2X, 2, 3], [29, 23, 4]];
  noteSpots.forEach(([x, z, n]) => addItem('note', x, z, { text: notesText[n], noteId: n }));
  addCodeNote().ch = 3; newSafe();
  RNG = Math.random;
  newTasks(); applyStations([]); S.safeOpen = false; S.chapter = 1; refreshItemVisibility();
  Object.assign(S, { nv: false, nvBatt: 1, down: false, invT: 0, mpPause: false, chapter: 1, dolls: 0, ritual: false, stalk: null, cryArm: null, grinT: 0, glitch: 0, stage: 0, dirT: 25, wxT: 10, recentScares: [], behindArm: null, duckT: 0, bannerT: 0, fuses: 0, power: false, keycard: false, bottles: 2, battery: 1, stamina: 1, breath: 1, hidden: null, flashOn: true, crouchToggle: false, deaths: 0, time: 0, startTime: 0, triggered: new Set(), visited: new Set(), notesRead: new Set() });
  doors.forEach(d => { d.open = d.target = 0; d.locked = d.electric; if (d.light) d.light.material = M.red; d.pivot.rotation.y = d.baseRot; });
  lockers.forEach(L => { L.open = L.target = 0; });
  lockerCorpse.body.visible = false; lockerCorpse.fall = null; S.candlesOut = false; candles.forEach(c => c.visible = true);
  hangBody.visible = false; wchair.position.set(cc(28.4), 0, cc(13.4)); wchair.userData.roll = null;
  fuseLights.forEach(f => { f.fz.visible = false; f.lt.material = M.red; });
  lamps.forEach(L => { L.broken = false; L.mode = L.mode0; L.on = L.mode0 !== 'off'; L.base = L.base0; L.light.color.copy(L.c0); });
  resetAltar();
  fuseBox.lever.rotation.x = 0; fuseBox.warn.color.set(0xff3020);
  exitGate.open = 0; exitGate.l.position.x = -C / 4; exitGate.r.position.x = C / 4;
  player.pos.set(cc(3), 0, cc(3)); player.yaw = Math.PI; player.pitch = -.1;
  mon.rage = false; mon.pos.set(cc(28), 0, cc(23)); mon.state = 'idle'; mon.stateT = -6; mon.path = []; mon.pathI = 0;
  events.length = 0;
  saveCheckpoint();
  updateTasks();
}

const INTRO = [
  'Kasım, 1987.\nAziz Lazar Sanatoryumu kapatılalı üç gün oldu.',
  'Kardeşin burada gece bekçisiydi.\nSon telefonunda fısıldıyordu:\n"Bağırma. Koşma. O duyar."',
  'Uyandığında 13 numaralı odadaydın.\nKapılar kilitli. Elektrik yok.\nVe koridorda bir şey... tıkırdıyor.',
  'O seni GÖREMEZ.\nAma her sesi DUYAR.\nKoşarsan gelir. Eğilirsen duymaz.',
  'Üç bölüm. Üç gece.\nKARANLIK. AYİN. KAÇIŞ.\n\nArkandan gelen ayak seslerine kulak verme.',
  'Ekrandaki mavi ◆ işaret sana yolu gösterecek.\nKaybolursan H tuşu.\n\nŞimdi... sessizce çık.',
];
let introI = 0;
let introList = INTRO;
function showIntro(list) {
  introList = list || INTRO;
  S.state = 'intro'; show('intro'); introI = 0; nextIntro();
}
function nextIntro() {
  if (introI >= introList.length) { startPlay(); return; }
  const el = $('introText'); el.style.transition = 'none'; el.style.opacity = 0; el.textContent = introList[introI++];
  requestAnimationFrame(() => { el.style.transition = 'opacity 1.2s'; el.style.opacity = 1; });
  if (A.ctx) A.click(new THREE.Vector3(player.pos.x + rand(-6, 6), 2, player.pos.z + rand(-6, 6)), 4, .25);
}
$('intro').addEventListener('click', nextIntro);
$('intro').addEventListener('touchstart', e => { e.preventDefault(); nextIntro(); }, { passive: false });

function show(id) { document.querySelectorAll('.screen').forEach(s => s.classList.toggle('on', s.id === id)); }
function startPlay() {
  show(null); $('hud').style.display = 'block';
  if (isTouch) $('touch').style.display = 'block';
  S.state = 'play'; S.startTime = performance.now();
  if (!isTouch) canvas.requestPointerLock?.();
  later(1, () => tutor(K('<kbd>W A S D</kbd> yürü &nbsp; <kbd>Fare</kbd> etrafına bak', 'Sol çubukla yürü, ekranın sağını kaydırarak bak'), 5));
  later(6.5, () => tutor(K('Mavi ◆ işareti takip et &nbsp; Kaybolursan <kbd>H</kbd>', 'Mavi ◆ işareti takip et &nbsp; Kaybolursan <b>YOL</b>'), 5));
  later(12, () => tutor(K('Kapılara bak ve <kbd>E</kbd> bas &nbsp; <kbd>C</kbd> ile eğilirsen sessiz olursun', 'Kapılara bakıp <b>KULLAN</b> &nbsp; <b>EĞİL</b> = sessiz'), 5));
  later(18, () => { A.click(new THREE.Vector3(cc(14), 2, cc(6)), 6, .7); A.growl(new THREE.Vector3(cc(16), 2, cc(9)), 1.6, .5); sub('...o neydi?', 2); });
  later(19.5, () => tutor(K('<kbd>Shift</kbd> koşar ama <b>O DUYAR</b> &nbsp; <kbd>G</kbd> şişe fırlat, sesin peşinden gider', '<b>KOŞ</b> = gürültü! &nbsp; <b>ŞİŞE AT</b> = onu başka yere çeker'), 5.5));
  chapterCard(1);
}
function pause() {
  if (S.state !== 'play') return;
  if (isMP()) { show('pause'); S.mpPause = true; document.exitPointerLock?.(); return; }
  S.state = 'pause'; show('pause'); if (A.ctx) A.ctx.suspend();
  document.exitPointerLock?.();
}
function resume() {
  show(null); S.mpPause = false; S.state = S.state === 'pause' ? 'play' : S.state; if (A.ctx) A.ctx.resume();
  if (!isTouch) canvas.requestPointerLock?.();
  last = performance.now();
}
function killPlayer(tip) {
  if (S.state !== 'play' || S.down || S.invT > 0) return;
  S.state = 'jumpscare'; S.deaths++; $('chapter').style.opacity = 0; $('hud').style.display = 'none'; $('touch').style.display = 'none';
  S.jumpT = 0; S.deathTip = tip;
  document.exitPointerLock?.();
  $('lockerView').style.opacity = 0;
  A.screech(null, 1.6, 1.25); A.sting(1); A.boom(1.2); S.glitch = .35; setTimeout(() => A.ring(.04), 1500);
  // yaratığı kameraya doğru çevir
  const dx = player.pos.x - mon.pos.x, dz = player.pos.z - mon.pos.z;
  mon.dir = Math.atan2(dx, dz);
  S.jumpFrom = { yaw: player.yaw, pitch: player.pitch };
}
function win(remote) {
  if (S.state === 'win') return;
  if (!remote) NET.send({ k: 'win' });
  S.state = 'win';
  const secs = (performance.now() - S.startTime) / 1000;
  const best = store.get('best_' + diff, null);
  if (!best || secs < best) store.set('best_' + diff, secs);
  const fmt = s => `${(s / 60) | 0}:${String((s % 60) | 0).padStart(2, '0')}`;
  $('winStats').innerHTML = `Zorluk: ${DIFF[diff].name}<br>Süre: ${fmt(secs)}<br>${isMP() ? 'Oyuncular: ' + [...NET.players.values()].map(p => p.name).join(', ') + '<br>' : ''}Ölüm: ${S.deaths}<br>Okunan not: ${S.notesRead.size}/5${best && secs >= best ? '<br>En iyi: ' + fmt(best) : '<br><b style="color:#9f9">YENİ REKOR</b>'}<br><br><span style="color:var(--dim)">Arkanda kapı kapanırken... bir tıkırtı duydun.</span>`;
  document.exitPointerLock?.();
  $('hud').style.display = 'none'; $('touch').style.display = 'none';
  exitGate.opening = true;
  A.boom(.8);
  setTimeout(() => { show('win'); }, 1800);
}
function toMenu() {
  NET.leave(); S.down = false; $('downView').style.display = 'none'; S.nv = false; $('nvHud').style.display = 'none';
  S.state = 'title'; show('title'); $('hud').style.display = 'none'; $('touch').style.display = 'none';
  if (A.ctx) A.ctx.resume();
  refreshBest();
}
function refreshBest() {
  const b = store.get('best_' + diff, null);
  $('best').textContent = b ? `En iyi kaçış (${DIFF[diff].name}): ${(b / 60) | 0}:${String((b % 60) | 0).padStart(2, '0')}` : '';
}

$('bStart').onclick = () => {
  A.init(); if (A.ctx.state === 'suspended') A.ctx.resume();
  if (!droneGain) { startAmbience(); startWeather(); lampBuzz(); }
  newGame(); showIntro();
  try { speechSynthesis.getVoices(); } catch (e) {}
};
$('bHow').onclick = () => show('howto');
$('bHowBack').onclick = () => show('title');
document.querySelectorAll('#diffRow .btn').forEach(b => b.onclick = () => {
  diff = +b.dataset.d; store.set('diff', diff);
  document.querySelectorAll('#diffRow .btn').forEach(x => x.classList.toggle('sel', x === b)); refreshBest();
});
document.querySelectorAll('#diffRow .btn').forEach(x => x.classList.toggle('sel', +x.dataset.d === diff));
$('bResume').onclick = resume;
$('bRestartCp').onclick = () => { loadCheckpoint(); resume(); };
$('bQuit').onclick = toMenu;
$('bRetry').onclick = () => { loadCheckpoint(); show(null); $('hud').style.display = 'block'; if (isTouch) $('touch').style.display = 'block'; S.state = 'play'; if (!isTouch) canvas.requestPointerLock?.(); last = performance.now(); };
$('bMenu2').onclick = toMenu;
$('bMenu3').onclick = toMenu;
$('sens').value = sens; $('sens').oninput = e => { sens = +e.target.value; store.set('sens', sens); };
$('vol').value = volume; $('vol').oninput = e => { volume = +e.target.value; store.set('vol', volume); if (A.master) A.master.gain.value = volume; };
refreshBest();

/* ========================== FİZİK / HAREKET ========================== */
const PR = .32; // oyuncu yarıçapı
function blocked(x, z) {
  const minx = toCell(x - PR), maxx = toCell(x + PR), minz = toCell(z - PR), maxz = toCell(z + PR);
  for (let cz = minz; cz <= maxz; cz++) for (let cx = minx; cx <= maxx; cx++) {
    const ch = cellAt(cx, cz);
    if (ch === '#' || ch === 'E') return true;
    if (ch === 'D' || ch === 'X') {
      const d = doorAt(cx, cz);
      if (d.open < .75) { // kapalı kapı: kapı düzlemine dik ince kutu
        const px = cc(cx), pz = cc(cz);
        if (d.ew ? Math.abs(z - pz) < PR + .08 : Math.abs(x - px) < PR + .08) return true;
      }
    }
  }
  for (const s of solids) if (x + PR > s.x0 && x - PR < s.x1 && z + PR > s.z0 && z - PR < s.z1) return true;
  return false;
}
function movePlayer(dt) {
  if (S.hidden || S.reading || S.keypad || S.down) { S.running = false; return 0; }
  let fx = 0, fz = 0;
  if (keys.KeyW || keys.ArrowUp) fz -= 1; if (keys.KeyS || keys.ArrowDown) fz += 1;
  if (keys.KeyA || keys.ArrowLeft) fx -= 1; if (keys.KeyD || keys.ArrowRight) fx += 1;
  fx += touch.mx; fz += touch.mz;
  const len = Math.hypot(fx, fz); if (len > 1) { fx /= len; fz /= len; }
  S.crouch = !!S.crouchToggle;
  const wantRun = (keys.ShiftLeft || keys.ShiftRight || touch.run) && fz < 0 && S.stamina > .02 && !S.crouch;
  S.running = wantRun && len > .1;
  let spd = S.crouch ? 1.35 : (S.running ? 5.1 : 2.6);
  if (touch.mx || touch.mz) spd *= Math.min(1, Math.hypot(touch.mx, touch.mz) * 1.25);
  const sy = Math.sin(player.yaw), cy = Math.cos(player.yaw);
  const wx = (fx * cy + fz * sy) * spd, wz = (-fx * sy + fz * cy) * spd;
  player.vel.x = lerp(player.vel.x, wx, Math.min(1, dt * 10)); player.vel.z = lerp(player.vel.z, wz, Math.min(1, dt * 10));
  const nx = player.pos.x + player.vel.x * dt, nz = player.pos.z + player.vel.z * dt;
  if (!blocked(nx, player.pos.z)) player.pos.x = nx; else player.vel.x = 0;
  if (!blocked(player.pos.x, nz)) player.pos.z = nz; else player.vel.z = 0;
  const sp = Math.hypot(player.vel.x, player.vel.z);
  // dayanıklılık
  if (S.running) S.stamina = Math.max(0, S.stamina - dt / 5.5);
  else S.stamina = Math.min(1, S.stamina + dt / (sp > .1 ? 9 : 5));
  if (S.stamina <= 0.02 && !S.exhausted) { S.exhausted = true; A.gasp(.3); emitNoise(player.pos, 7); }
  if (S.stamina > .35) S.exhausted = false;
  // ayak sesleri
  if (sp > .3) {
    player.stepAcc += sp * dt;
    const stride = S.running ? 2.1 : S.crouch ? .9 : 1.5;
    if (player.stepAcc > stride) {
      player.stepAcc = 0;
      const vol = S.running ? .55 : S.crouch ? .05 : .2;
      A.step(vol, null, false, S.running ? 1.1 : .9);
      emitNoise(player.pos, S.running ? 15 : S.crouch ? 1.0 : 5.5);
      onPlayerStep();
    }
  }
  return sp;
}

/* =========================== GÖREV & YOL REHBERİ ======================= */
const nearestItem = type => { let best = null, bd = 1e9; for (const it of items) if (it.type === type && !it.taken) { const d = it.pos.distanceTo(player.pos); if (d < bd) { bd = d; best = it; } } return best; };
// yere düşen parlayan iz
const guideDots = [];
const guideMat = new THREE.MeshBasicMaterial({ map: glowTex, color: 0x7fd4ff, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0, fog: false });
const guideGeo = new THREE.PlaneGeometry(.55, .55);
for (let i = 0; i < 140; i++) { const m = new THREE.Mesh(guideGeo, guideMat.clone()); m.rotation.x = -Math.PI / 2; m.visible = false; scene.add(m); guideDots.push(m); }
let guideT = 0, guideCd = 0;
function showGuide(auto = false) {
  if (guideCd > 0 && !auto) return;
  const o = objective();
  const path = bfs(toCell(player.pos.x), toCell(player.pos.z), toCell(o.pos.x), toCell(o.pos.z))
    || bfs(toCell(player.pos.x), toCell(player.pos.z), toCell(o.pos.x), toCell(o.pos.z) - 1);
  if (!path) return;
  const pts = [player.pos.clone(), ...path.slice(1).map(([x, z]) => new THREE.Vector3(cc(x), 0, cc(z)))];
  pts[pts.length - 1] = o.pos.clone().setY(0);
  let n = 0;
  for (let i = 0; i < pts.length - 1 && n < guideDots.length; i++) {
    const a = pts[i], b = pts[i + 1], L = a.distanceTo(b);
    for (let d = (i === 0 ? 1 : 0); d < L && n < guideDots.length; d += .9) {
      const p = a.clone().lerp(b, d / L); const dot = guideDots[n++];
      dot.position.set(p.x, .03, p.z); dot.visible = true; dot.userData.i = n;
    }
  }
  for (let i = n; i < guideDots.length; i++) guideDots[i].visible = false;
  guideT = 8; guideCd = auto ? 0 : 5;
  if (!auto) A.chime(); else A.chime();
}
function updateGuide(dt) {
  const pulse = 1 + Math.sin(S.time * 4) * .25;
  for (const it of items) if (it.glow && !it.taken) it.glow.material.opacity = .45 * pulse;
  guideCd -= dt;
  if (guideT <= 0) return;
  guideT -= dt;
  const t = 8 - guideT;
  for (const d of guideDots) {
    if (!d.visible) continue;
    const i = d.userData.i, appear = clamp((t * 14 - i) / 3, 0, 1);
    const wave = .55 + .45 * Math.sin(t * 6 - i * .45);
    d.material.opacity = appear * wave * clamp(guideT / 2, 0, 1) * .9;
    d.scale.setScalar(.8 + wave * .35);
    if (guideT <= 0) d.visible = false;
  }
}

/* ============================ ÖĞRETİCİ ============================= */
let tutorT = 0;
function tutor(html, dur = 4.5) { const el = $('tutor'); el.innerHTML = html; el.style.opacity = 1; tutorT = dur; }
const K = (desk, tch) => isTouch ? tch : desk;

/* ======================= KORKU YÖNETMENİ ========================== */
// Oyuncunun çevresinde rastgele ama yerinde korkular üretir.
function spotAhead(minD, maxD) {
  const fx = -Math.sin(player.yaw), fz = -Math.cos(player.yaw), out = [];
  for (let d = minD; d <= maxD; d += .5) {
    const x = player.pos.x + fx * d, z = player.pos.z + fz * d;
    if (!passable(toCell(x), toCell(z)) || !lineClear(player.pos.x, player.pos.z, x, z)) break;
    const ch = cellAt(toCell(x), toCell(z)); if (ch === 'D' || ch === 'X') continue;
    out.push(new THREE.Vector3(x, 0, z));
  }
  return out.length ? out[(out.length * rand(.5, 1)) | 0] : null;
}
function spotBehind() {
  const fx = -Math.sin(player.yaw), fz = -Math.cos(player.yaw);
  for (const d of [2.2, 1.6, 1.1]) { const x = player.pos.x - fx * d, z = player.pos.z - fz * d; if (passable(toCell(x), toCell(z)) && lineClear(player.pos.x, player.pos.z, x, z)) return new THREE.Vector3(x, 0, z); }
  return null;
}
function standFacing(m, p) { m.position.copy(p); m.rotation.y = Math.atan2(player.pos.x - p.x, player.pos.z - p.z); }
function duck(sec) { S.duckT = Math.max(S.duckT || 0, sec); }
const actorRuns = [];   // {m, a, b, t, dur, kind}
let lightT = 0;
function lightning(withFigure = false) {
  lightT = 1.1;
  A.thunder(rand(.4, 1.6), rand(.7, 1));
  if (withFigure) {
    const p = spotAhead(4, 10);
    if (p) { standFacing(shadowRunner, p); animateMonster(shadowRunner, 0, 0, false, false); S.lightFigure = true; later(.1, () => { A.hit(.9); shake(.5); }); }
  }
}
const DIRECTOR = {
  peek() { // ileride bir an görünen yaratık
    const p = spotAhead(6, 13); if (!p) return false;
    duck(1.4);
    later(1.4, () => {
      standFacing(peekHead, p); animateMonster(peekHead, 0, 0, false, true); peekHead.visible = true;
      A.hit(.85); flicker(.7); shake(.4);
      later(.7, () => { peekHead.visible = false; });
    });
    return true;
  },
  behind() { // arkandan nefes... dönersen orada
    const p = spotBehind(); if (!p) return false;
    A.whisper(0, 1.8, .45, p.clone().setY(1.6)); A.breath(.2, false);
    S.behindArm = { p, t: 5 };
    return true;
  },
  runner() { // önünden koşup geçen gölge
    const p = spotAhead(5, 10); if (!p) return false;
    const rx = Math.cos(player.yaw), rz = -Math.sin(player.yaw), sg = Math.random() < .5 ? 1 : -1;
    const a = p.clone().add(new THREE.Vector3(rx * 4 * sg, 0, rz * 4 * sg)), b = p.clone().add(new THREE.Vector3(-rx * 4 * sg, 0, -rz * 4 * sg));
    actorRuns.push({ m: shadowRunner, a, b, t: 0, dur: .75, kind: 'run' });
    A.whoosh(.7); A.screech(p.clone().setY(1.5), .6, .5);
    for (let i = 0; i < 4; i++) later(i * .17, () => A.step(.9, a.clone().lerp(b, i / 4).setY(.1), true, 1.4));
    return true;
  },
  child() { // kıkırdayan küçük gölge
    const p = spotAhead(6, 12); if (!p) return false;
    const rx = Math.cos(player.yaw), rz = -Math.sin(player.yaw), sg = Math.random() < .5 ? 1 : -1;
    actorRuns.push({ m: child, a: p.clone().add(new THREE.Vector3(rx * 3 * sg, 0, rz * 3 * sg)), b: p.clone().add(new THREE.Vector3(-rx * 3 * sg, 0, -rz * 3 * sg)), t: 0, dur: 1.2, kind: 'child' });
    A.laugh(p.clone().setY(1)); later(.6, () => A.sting(.4));
    return true;
  },
  knock() { // kapıya vuruluyor
    const d = doors.filter(d => d.open < .3 && Math.hypot(cc(d.x) - player.pos.x, cc(d.z) - player.pos.z) < 11).sort((a, b) => Math.hypot(cc(a.x) - player.pos.x, cc(a.z) - player.pos.z) - Math.hypot(cc(b.x) - player.pos.x, cc(b.z) - player.pos.z))[0];
    if (!d) return false;
    const p = new THREE.Vector3(cc(d.x), 1.3, cc(d.z));
    duck(1.2);
    later(1.2, () => { A.knock(p, 3, 1.2); d.rattle = 1.2; later(1.4, () => { A.knock(p, 5, 1.5); d.rattle = 2; shake(.3); }); later(3.6, () => A.whisper(0, 1.5, .25, p)); });
    return true;
  },
  lamp() { // lamba patlar
    const L = lamps.filter(L => !L.broken && Math.hypot(L.light.position.x - player.pos.x, L.light.position.z - player.pos.z) < 13)[0];
    if (!L) return false;
    L.broken = true; A.spark(L.light.position); burstSparks(L.light.position); flash(.15); later(.1, () => A.sting(.5));
    return true;
  },
  lightning() { lightning(Math.random() < .7); return true; },
  rush() { // arkandan koşarak gelen ayak sesleri... sonra sessizlik
    const fx = -Math.sin(player.yaw), fz = -Math.cos(player.yaw);
    duck(3);
    for (let i = 0; i < 9; i++) later(i * .2, () => { const d = 9 - i; A.step(1.2, new THREE.Vector3(player.pos.x - fx * d, .1, player.pos.z - fz * d), true, 1.3); });
    later(1.85, () => { A.whisper(0, 1.2, .5, camera.localToWorld(new THREE.Vector3(.3, 0, .4))); shake(.4); });
    return true;
  },
  phone() {
    const c = floorCells.filter(([x, z]) => { const d = Math.hypot(cc(x) - player.pos.x, cc(z) - player.pos.z); return d > 6 && d < 14 && roomOf(x, z); });
    if (!c.length) return false; const p = pick(c);
    A.phone(new THREE.Vector3(cc(p[0]), 1, cc(p[1])), 3);
    later(9, () => A.laugh(new THREE.Vector3(cc(p[0]), 1, cc(p[1]))));
    return true;
  },
  slam() {
    const d = doors.filter(d => d.open > .6 && !d.locked && Math.hypot(cc(d.x) - player.pos.x, cc(d.z) - player.pos.z) < 12)[0];
    if (!d) return false;
    duck(1); later(1, () => { d.target = 0; d.speed = 9; A.slam(new THREE.Vector3(cc(d.x), 1.2, cc(d.z)), 1.4); A.sting(.6); shake(.5); });
    return true;
  },
  ceiling() {
    const fx = -Math.sin(player.yaw), fz = -Math.cos(player.yaw);
    for (let i = 0; i < 10; i++) later(i * .28, () => { const p = new THREE.Vector3(player.pos.x + fx * (5 - i), WALL_H + .3, player.pos.z + fz * (5 - i)); A.step(.7, p, true, .7); if (i % 3 === 0) A.creak(p, .4, .12, .5); });
    dust(3); later(3, () => A.growl(new THREE.Vector3(player.pos.x, WALL_H + .4, player.pos.z), 1.5, .6, 1.2));
    return true;
  },
  bottle() {
    const a = Math.random() * 6.28, p = new THREE.Vector3(player.pos.x + Math.cos(a) * 3, 1, player.pos.z + Math.sin(a) * 3);
    if (!passable(toCell(p.x), toCell(p.z))) return false;
    A.glass(p, 1.2); A.sting(.45); shake(.2); return true;
  },
  flashDie() {
    S.flashForcedOff = 2.2; A.flashClick(); duck(2.2);
    later(.6, () => A.breath(.3, true)); later(1.5, () => A.whisper(rand(-1, 1), 1, .35));
    if (Math.random() < .6) later(2.2, () => { const p = spotAhead(3, 6); if (p) { standFacing(peekHead, p); animateMonster(peekHead, 0, 0, false, true); peekHead.visible = true; A.hit(1); shake(.6); later(.35, () => { peekHead.visible = false; flicker(.4); }); } });
    return true;
  },
};
function burstSparks(p) {
  const pos = sparks.geometry.attributes.position, v = sparks.userData.v;
  for (let i = 0; i < 60; i++) { pos.setXYZ(i, p.x, p.y, p.z); v[i * 3] = rand(-2.5, 2.5); v[i * 3 + 1] = rand(-1, 2); v[i * 3 + 2] = rand(-2.5, 2.5); }
  pos.needsUpdate = true; sparks.visible = true; sparks.userData.t = 1.2;
}
function updateDirector(dt) {
  // ileri koşan aktörler
  for (let i = actorRuns.length - 1; i >= 0; i--) {
    const r = actorRuns[i]; r.t += dt; const k = r.t / r.dur;
    r.m.visible = k < 1; r.m.position.copy(r.a).lerp(r.b, Math.min(1, k));
    r.m.rotation.y = Math.atan2(r.b.x - r.a.x, r.b.z - r.a.z);
    if (r.kind === 'run') { const ph = r.t * 26; animateMonster(r.m, 0, 0, true, false); r.m.userData.legs.forEach(l => { l.hip.rotation.x = Math.sin(ph + l.s * 1.5) - .5; }); }
    else { const L = r.m.userData.limbs, ph = r.t * 18; L.ll.rotation.x = Math.sin(ph); L.rl.rotation.x = -Math.sin(ph); L.la.rotation.x = -Math.sin(ph); L.ra.rotation.x = Math.sin(ph); }
    if (k >= 1) actorRuns.splice(i, 1);
  }
  // arkanda
  if (S.behindArm) {
    const b = S.behindArm; b.t -= dt;
    const fx = -Math.sin(player.yaw), fz = -Math.cos(player.yaw), dx = b.p.x - player.pos.x, dz = b.p.z - player.pos.z, l = Math.hypot(dx, dz) || 1;
    if ((dx * fx + dz * fz) / l > .55) { standFacing(peekHead, b.p); animateMonster(peekHead, 0, 0, false, true); peekHead.visible = true; A.hit(1.1); A.screech(null, .8, .9); shake(.8); flash(.1); redFlash(.4); S.behindArm = null; later(.4, () => { peekHead.visible = false; }); }
    else if (b.t <= 0) S.behindArm = null;
  }
  // kıvılcımlar
  if (sparks.visible) {
    const pos = sparks.geometry.attributes.position, v = sparks.userData.v;
    for (let i = 0; i < 60; i++) { v[i * 3 + 1] -= 9 * dt; pos.setXYZ(i, pos.getX(i) + v[i * 3] * dt, Math.max(.02, pos.getY(i) + v[i * 3 + 1] * dt), pos.getZ(i) + v[i * 3 + 2] * dt); }
    pos.needsUpdate = true; sparks.userData.t -= dt; sparks.material.opacity = Math.max(0, sparks.userData.t); if (sparks.userData.t <= 0) sparks.visible = false;
  }
  // kapı sarsıntısı
  for (const d of doors) if (d.rattle > 0) { d.rattle -= dt; d.pivot.rotation.y += Math.sin(S.time * 60) * .02 * Math.min(1, d.rattle); }
  // şimşek
  if (lightT > 0) {
    lightT -= dt;
    const k = 1.1 - lightT, I = (k < .08 ? 1 : k < .16 ? .1 : k < .26 ? .8 : k < .5 ? .3 * (1 - (k - .26) / .24) : 0) * (Math.random() * .3 + .85);
    lightningLight.intensity = I * 2.4;
    for (const m of windowMats) m.emissiveIntensity = .08 + I * 7;
    shadowRunner.visible = !!S.lightFigure && I > .5;
    if (lightT <= 0) { lightningLight.intensity = 0; for (const m of windowMats) m.emissiveIntensity = .08; S.lightFigure = false; shadowRunner.visible = false; }
  }
  // ortam: yağmurda damlalar, metal sesleri
  S.dripT = (S.dripT || 2) - dt;
  if (S.dripT <= 0) { S.dripT = rand(.6, 3); A.drip(player.pos.clone().add(new THREE.Vector3(rand(-6, 6), rand(.5, 2.8), rand(-6, 6)))); }
  S.wxT = (S.wxT ?? 14) - dt;
  if (S.wxT <= 0) { S.wxT = rand(22, 50); lightning(false); }
  // yönetmen
  if (S.state !== 'play') return;
  S.dirT = (S.dirT ?? 22) - dt;
  if (S.dirT > 0 || mon.state === 'chase' || S.down) return;
  const pool = S.hidden ? ['knock', 'rush', 'ceiling', 'phone', 'cry', 'drag'] : Object.keys(DIRECTOR);
  const recent = S.recentScares || (S.recentScares = []);
  const order = pool.filter(n => !recent.includes(n)).sort(() => Math.random() - .5);
  for (const n of order) if (DIRECTOR[n]()) { recent.push(n); if (recent.length > 9) recent.shift(); break; }
  S.dirT = (diff === 0 ? rand(18, 30) : diff === 2 ? rand(9, 17) : rand(12, 22)) * [1, 1, .8, .6][S.chapter || 1];
}

/* ============================== BÖLÜMLER ============================== */
const CHAPTERS = [null,
  { n: 'BÖLÜM 1', t: 'KARANLIK', d: 'Elektrik yok. Hastanede saklı 3 sigortayı bul ve jeneratörü çalıştır.' },
  { n: 'BÖLÜM 2', t: 'AYİN', d: 'Işıklar geldi... ve bir şey uyandı. 4 lanetli bebeği bul, şapeldeki mumlarda yak. Müzik kutusu sesini dinle.' },
  { n: 'BÖLÜM 3', t: 'KAÇIŞ', d: 'Ayin bozuldu. Işıklar kızıla döndü ve O artık çok öfkeli. Kartı başhekimin kasasında: kanlı bir notta yazan şifreyi bul, kasayı aç ve ÇIK.' },
];
function chapterCard(n) {
  const c = CHAPTERS[n];
  $('chN').textContent = c.n; $('chT').textContent = c.t; $('chD').textContent = c.d;
  $('chapter').style.opacity = 1; S.state = 'chapter'; S.chapT = 4.5;
  A.gong(); A.boom(.8); later(0, () => {});
  updateTasks();
}
function startChapter(n) {
  S.chapter = n; S.stage = 0; S.stalk = null; S.cryArm = null; S.helpNotified = false;
  refreshItemVisibility();
  if (n === 2) {
    if (isMP()) later(5, () => tutor('Yeni görevlerin: ' + TASKDEF[2].filter(t => NET.myRoles.includes(t.role)).map(t => t.label).join(' · '), 6));
    S.dirT = 14;
  }
  if (n === 3) {
    // her yer kırmızı acil durum ışığı
    lamps.forEach(L => { L.broken = false; L.on = true; L.mode = 'alarm'; L.base = 3.5; L.light.color.set(0xff1808); });
    S.candlesOut = true; candles.forEach(c => c.visible = false);
    doors.forEach(d => { if (d.electric) { d.locked = false; d.light.material = M.green; d.target = 1; d.swing = 1; d.speed = 6; } });
    mon.rage = true;
    const c = floorCells.filter(([x, z]) => { const d = Math.hypot(cc(x) - player.pos.x, cc(z) - player.pos.z); return d > 16 && d < 24; });
    if (c.length) { const q = pick(c); mon.pos.set(cc(q[0]), 0, cc(q[1])); monSetTarget(player.pos.x, player.pos.z, 'investigate'); }
    S.dirT = 10;
    later(.5, () => { A.slam(new THREE.Vector3(cc(32), 1.2, cc(11)), 1.4); A.siren(4); });
  }
  saveCheckpoint();
  chapterCard(n);
}

/* ============================ AYİN: BEBEKLER =========================== */
const DOLL_SPOTS = [[13, 2], [20, 4], [28, 12], [2, 9], [8, 23], [33, 24], [34, 2], [14, 13], [24, 9], [6, 13], [21, 23], [1, 19]];
Object.assign(M, {
  porcelain: new THREE.MeshStandardMaterial({ color: 0xe6ddcc, roughness: .25, metalness: .05 }),
  dollDress: new THREE.MeshStandardMaterial({ color: 0x6a3f48, roughness: .95 }),
  dollEye: new THREE.MeshBasicMaterial({ color: 0x000000 }),
});
function dollModel() {
  const g = new THREE.Group();
  const dress = new THREE.Mesh(new THREE.ConeGeometry(.13, .27, 10), M.dollDress); dress.position.y = .135; g.add(dress);
  const head = new THREE.Mesh(new THREE.SphereGeometry(.085, 14, 10), M.porcelain); head.position.y = .33; head.rotation.z = .35; g.add(head);
  const hair = new THREE.Mesh(new THREE.SphereGeometry(.092, 12, 8, 0, Math.PI * 2, 0, Math.PI / 1.8), M.hair); hair.position.y = .34; hair.rotation.set(-.3, 0, .35); g.add(hair);
  for (const s of [-1, 1]) {
    const e = new THREE.Mesh(new THREE.SphereGeometry(.017, 8, 6), M.dollEye); e.position.set(s * .032 + .012, .345, .072); g.add(e);
    const tear = box(.007, .07, .004, M.blood); tear.position.set(s * .032 + .014, .3, .078); g.add(tear);
    const arm = cyl(.016, .013, .14, M.porcelain, 5); arm.position.set(s * .11, .2, 0); arm.rotation.z = s * .7; g.add(arm);
  }
  const mouth = box(.03, .008, .005, M.blood); mouth.position.set(.008, .3, .082); g.add(mouth);
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  return g;
}
function addDoll(x, z) {
  const g = dollModel();
  g.position.set(cc(x) + rand(-.5, .5), 0, cc(z) + rand(-.5, .5)); g.rotation.y = rand(0, 6.28); g.scale.setScalar(1.8);
  const gl = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xff3020, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: .4 }));
  gl.scale.setScalar(.8); gl.position.y = .25; g.add(gl);
  g.visible = false; world.add(g);
  const it = { type: 'doll', mesh: g, pos: g.position, taken: false, id: items.length, glow: gl, beacon: rand(0, 4) };
  items.push(it); return it;
}
const ALTAR = new THREE.Vector3(cc(14), 0, cc(24) + .3);
let altarFire, altarDolls = [], altarPages = [];
function buildAltar() {
  const a = box(1.8, .95, .8, M.wood); a.position.set(ALTAR.x, .475, ALTAR.z + .35); world.add(a); addSolid(ALTAR.x, ALTAR.z + .35, .9, .4);
  const cloth = box(1.85, .02, .85, M.bloodSheet); cloth.position.set(ALTAR.x, .96, ALTAR.z + .35); world.add(cloth);
  for (let i = 0; i < 4; i++) { const d = dollModel(); d.position.set(ALTAR.x - .6 + i * .4, .97, ALTAR.z + .35); d.visible = false; world.add(d); altarDolls.push(d); }
  for (let i = 0; i < 3; i++) { const pg = new THREE.Mesh(new THREE.PlaneGeometry(.24, .32), new THREE.MeshStandardMaterial({ map: pageTex, side: THREE.DoubleSide })); pg.rotation.set(-Math.PI / 2, 0, rand(-.4, .4)); pg.position.set(ALTAR.x - .4 + i * .4, .975, ALTAR.z + .1); pg.visible = false; world.add(pg); altarPages.push(pg); }
  altarFire = new THREE.PointLight(0xff6a20, 0, 9, 2); altarFire.position.set(ALTAR.x, 1.4, ALTAR.z); world.add(altarFire);
}
function resetAltar() { S.fireT = 0; if (altarFire) altarFire.intensity = 0; altarDolls.forEach(d => { d.visible = false; d.scale.setScalar(1); }); altarPages.forEach(d => { d.visible = false; d.scale.setScalar(1); }); }
function ritual() {
  if (S.ritual) return;
  S.ritual = true; updateTasks();
  altarDolls.forEach(d => d.visible = true); altarPages.forEach(d => d.visible = true);
  sub('Yanın...', 2);
  duck(1.5);
  later(1.5, () => {
    S.fireT = 5; A.boom(1.3); A.hit(1); burstSparks(ALTAR.clone().setY(1.1)); shake(.8); flash(.35);
    S.candlesOut = false; candles.forEach(c => c.visible = true);
    for (let i = 0; i < 6; i++) later(i * .4, () => A.cry(ALTAR.clone().setY(1), .8));
  });
  later(3.4, () => screamer(true));
  later(5, () => { A.distantScream(); blackout(1.2); });
  if (!isMP() || NET.host) later(6.4, () => { startChapter(3); NET.send({ k: 'chapter', n: 3 }); });
}

/* ========================= ANİ KORKU YÜZLERİ ========================= */
function drawScreamer(style = 'maw') {
  if (style === 'woman') return drawWoman();
  if (style === 'child') return drawChild();
  const W = 640, H = 640, c = makeCanvas(W, H), x = c.getContext('2d');
  const bg = x.createRadialGradient(W / 2, H / 2, 40, W / 2, H / 2, W * .72); bg.addColorStop(0, '#3a0303'); bg.addColorStop(1, '#000');
  x.fillStyle = bg; x.fillRect(0, 0, W, H);
  x.save(); x.translate(W / 2 + rand(-20, 20), H * .5); x.rotate(rand(-.15, .15)); x.scale(1, rand(1.12, 1.3));
  const fg = x.createRadialGradient(-30, -70, 20, 0, 0, 240); fg.addColorStop(0, '#d8cfbd'); fg.addColorStop(.55, '#8a8070'); fg.addColorStop(1, '#1c1813');
  x.fillStyle = fg; x.beginPath(); x.ellipse(0, 0, 178, 232, 0, 0, 7); x.fill();
  for (const sx of [-1, 1]) { const g = x.createRadialGradient(sx * 100, 50, 5, sx * 100, 50, 90); g.addColorStop(0, 'rgba(20,10,5,.75)'); g.addColorStop(1, 'rgba(20,10,5,0)'); x.fillStyle = g; x.fillRect(-200, -100, 400, 300); }
  // damarlar ve çatlaklar
  x.strokeStyle = 'rgba(80,10,30,.7)'; x.lineWidth = 1.6; for (let i = 0; i < 14; i++) crack(x, rand(-140, 140), rand(-200, 160), rand(40, 120), rand(0, 6), 2);
  x.strokeStyle = 'rgba(0,0,0,.8)'; x.lineWidth = 2.5; for (let i = 0; i < 4; i++) crack(x, rand(-120, 120), rand(-200, -60), rand(60, 140), rand(0, 6), 2);
  // göz çukurları: dipsiz, kanlı
  for (const sx of [-1, 1]) {
    x.save(); x.translate(sx * 72, -58); x.rotate(sx * .28);
    const g = x.createRadialGradient(0, 0, 10, 0, 0, 78); g.addColorStop(0, 'rgba(0,0,0,1)'); g.addColorStop(.55, 'rgba(0,0,0,.95)'); g.addColorStop(1, 'rgba(0,0,0,0)');
    x.fillStyle = g; x.beginPath(); x.ellipse(0, 0, 66, 78, 0, 0, 7); x.fill();
    if (Math.random() < .6) { x.fillStyle = '#fff'; x.beginPath(); x.arc(rand(-6, 6), rand(-4, 6), rand(2, 4), 0, 7); x.fill(); }
    x.restore();
    x.fillStyle = '#5a0000'; for (let k = 0; k < 4; k++) { const tx = sx * 72 + rand(-26, 26), L = rand(60, 180); x.fillRect(tx, -10, rand(3, 7), L); x.beginPath(); x.arc(tx + 3, -10 + L, 5, 0, 7); x.fill(); }
  }
  // burun yarıkları
  x.fillStyle = '#000'; for (const sx of [-1, 1]) { x.beginPath(); x.ellipse(sx * 12, 20, 6, 16, sx * .3, 0, 7); x.fill(); }
  // dev ağız
  const mw = rand(90, 115), mh = rand(110, 140), my = 125;
  const mg = x.createRadialGradient(0, my, 10, 0, my, mh); mg.addColorStop(0, '#000'); mg.addColorStop(.7, '#140000'); mg.addColorStop(1, '#4a0505');
  x.fillStyle = mg; x.beginPath(); x.ellipse(0, my, mw, mh, 0, 0, 7); x.fill();
  x.fillStyle = '#e4d6a8'; x.strokeStyle = '#3a2a10'; x.lineWidth = 1.5;
  const tooth = (a, up) => { const tx = Math.sin(a) * mw * .96, ty = my + (up ? -1 : 1) * Math.cos(a) * mh * .96, L = rand(22, 46) * (1 - Math.abs(a) * .3), w = rand(7, 12);
    x.beginPath(); x.moveTo(tx - w, ty); x.lineTo(tx + w, ty); x.lineTo(tx + rand(-3, 3), ty + (up ? L : -L)); x.closePath(); x.fill(); x.stroke(); };
  for (let i = 0; i < 15; i++) { const a = (i / 14 - .5) * 2.4; tooth(a, true); tooth(a + rand(-.05, .05), false); }
  x.restore();
  // saç
  x.lineCap = 'round';
  for (let i = 0; i < 170; i++) {
    let sx = W / 2 + rand(-230, 230); if (Math.abs(sx - W / 2) < 120 && Math.random() < .85) sx += Math.sign(sx - W / 2 || 1) * 120;
    x.strokeStyle = `rgba(0,0,0,${rand(.6, .95)})`; x.lineWidth = rand(1, 4);
    x.beginPath(); x.moveTo(sx, -10); x.bezierCurveTo(sx + rand(-40, 40), H * .25, sx + rand(-70, 70), H * .55, sx + rand(-80, 80), rand(H * .45, H * 1.05)); x.stroke();
  }
  // kan sıçraması
  x.fillStyle = 'rgba(120,0,0,.85)'; for (let i = 0; i < 40; i++) { x.beginPath(); x.arc(rand(0, W), rand(0, H), rand(1, 9), 0, 7); x.fill(); }
  // bozulma dilimleri
  for (let i = 0; i < 9; i++) { const y = rand(0, H), h = rand(6, 40), dx = rand(-50, 50); const d = x.getImageData(0, y, W, h); x.putImageData(d, dx, y); }
  const img = x.getImageData(0, 0, W, H), d = img.data;
  for (let i = 0; i < d.length; i += 4) { const n = (Math.random() - .5) * 60; d[i] += n + 10; d[i + 1] += n; d[i + 2] += n; }
  x.putImageData(img, 0, 0);
  const v = x.createRadialGradient(W / 2, H / 2, W * .3, W / 2, H / 2, W * .75); v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,.9)'); x.fillStyle = v; x.fillRect(0, 0, W, H);
  return c;
}
function faceFinish(x, W, H) { // ortak: kan, bozulma, gren, vinyet
  x.fillStyle = 'rgba(120,0,0,.85)'; for (let i = 0; i < 30; i++) { x.beginPath(); x.arc(rand(0, W), rand(0, H), rand(1, 8), 0, 7); x.fill(); }
  for (let i = 0; i < 7; i++) { const y = rand(0, H), h = rand(6, 34), dx = rand(-45, 45); const d = x.getImageData(0, y, W, h); x.putImageData(d, dx, y); }
  const img = x.getImageData(0, 0, W, H), d = img.data;
  for (let i = 0; i < d.length; i += 4) { const n = (Math.random() - .5) * 55; d[i] += n + 8; d[i + 1] += n; d[i + 2] += n; }
  x.putImageData(img, 0, 0);
  const v = x.createRadialGradient(W / 2, H / 2, W * .28, W / 2, H / 2, W * .75); v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,.92)'); x.fillStyle = v; x.fillRect(0, 0, W, H);
}
function hairCurtain(x, W, H, n, gap, alpha = .9) {
  x.lineCap = 'round';
  for (let i = 0; i < n; i++) {
    let sx = W / 2 + rand(-260, 260); if (Math.abs(sx - W / 2) < gap && Math.random() < .9) sx += Math.sign(sx - W / 2 || 1) * gap;
    x.strokeStyle = `rgba(0,0,0,${rand(.55, alpha)})`; x.lineWidth = rand(1, 5);
    x.beginPath(); x.moveTo(sx, -10); x.bezierCurveTo(sx + rand(-30, 30), H * .3, sx + rand(-50, 50), H * .6, sx + rand(-60, 60), rand(H * .7, H * 1.1)); x.stroke();
  }
}
function drawWoman() { // ıslak siyah saçlar, tek dev göz, dikey uzamış ağız
  const W = 640, H = 640, c = makeCanvas(W, H), x = c.getContext('2d');
  x.fillStyle = '#020306'; x.fillRect(0, 0, W, H);
  x.save(); x.translate(W / 2, H * .55); x.rotate(rand(-.25, .25)); x.scale(1, 1.3);
  const fg = x.createRadialGradient(-20, -60, 10, 0, 0, 230); fg.addColorStop(0, '#e9e6e2'); fg.addColorStop(.6, '#9aa0a6'); fg.addColorStop(1, '#202428');
  x.fillStyle = fg; x.beginPath(); x.ellipse(0, 0, 150, 215, 0, 0, 7); x.fill();
  x.strokeStyle = 'rgba(40,40,90,.5)'; x.lineWidth = 1.4; for (let i = 0; i < 16; i++) crack(x, rand(-120, 120), rand(-180, 150), rand(30, 110), rand(0, 6), 2);
  const eye = (ex, ey, r) => { const g = x.createRadialGradient(ex, ey, 2, ex, ey, r * 1.6); g.addColorStop(0, '#000'); g.addColorStop(.6, 'rgba(0,0,0,.95)'); g.addColorStop(1, 'rgba(0,0,0,0)'); x.fillStyle = g; x.beginPath(); x.ellipse(ex, ey, r * 1.6, r * 1.3, 0, 0, 7); x.fill();
    x.fillStyle = '#d9d2c0'; x.beginPath(); x.ellipse(ex, ey, r, r * .8, 0, 0, 7); x.fill(); x.fillStyle = '#000'; x.beginPath(); x.arc(ex + rand(-3, 3), ey, r * .22, 0, 7); x.fill(); };
  eye(55, -70, 30);
  x.fillStyle = '#000'; x.beginPath(); x.ellipse(-60, -70, 40, 32, 0, 0, 7); x.fill();
  x.fillStyle = '#3a0000'; for (let k = 0; k < 4; k++) x.fillRect(-60 + rand(-20, 20), -50, rand(3, 6), rand(80, 200));
  const mg = x.createLinearGradient(0, 30, 0, 200); mg.addColorStop(0, '#000'); mg.addColorStop(1, '#2a0000');
  x.fillStyle = mg; x.beginPath(); x.ellipse(0, 115, 42, 95, 0, 0, 7); x.fill();
  x.restore();
  hairCurtain(x, W, H, 320, 60, .97);
  faceFinish(x, W, H); return c;
}
function drawChild() { // kapkara gözler, kulaklara yırtılmış dikişli gülüş
  const W = 640, H = 640, c = makeCanvas(W, H), x = c.getContext('2d');
  const bg = x.createRadialGradient(W / 2, H / 2, 30, W / 2, H / 2, W * .7); bg.addColorStop(0, '#201010'); bg.addColorStop(1, '#000'); x.fillStyle = bg; x.fillRect(0, 0, W, H);
  x.save(); x.translate(W / 2, H * .52); x.rotate(rand(-.3, .3));
  const fg = x.createRadialGradient(-30, -50, 10, 0, 0, 220); fg.addColorStop(0, '#f1e3d3'); fg.addColorStop(.6, '#b49c8a'); fg.addColorStop(1, '#2a1c16');
  x.fillStyle = fg; x.beginPath(); x.ellipse(0, 0, 190, 205, 0, 0, 7); x.fill();
  for (const sx of [-1, 1]) {
    const g = x.createRadialGradient(sx * 70, -40, 4, sx * 70, -40, 70); g.addColorStop(0, '#000'); g.addColorStop(.75, '#000'); g.addColorStop(1, 'rgba(0,0,0,0)');
    x.fillStyle = g; x.beginPath(); x.ellipse(sx * 70, -40, 58, 64, 0, 0, 7); x.fill();
    x.fillStyle = 'rgba(255,255,255,.85)'; x.beginPath(); x.arc(sx * 70 - 12, -56, 5, 0, 7); x.fill();
    x.fillStyle = '#4a0000'; for (let k = 0; k < 3; k++) x.fillRect(sx * 70 + rand(-25, 25), -5, rand(3, 6), rand(60, 160));
  }
  // kulaktan kulağa gülüş
  x.strokeStyle = '#0a0000'; x.lineWidth = 16; x.lineCap = 'round';
  x.beginPath(); x.moveTo(-175, 10); x.quadraticCurveTo(0, 190, 175, 10); x.stroke();
  x.fillStyle = '#e8dcb8'; for (let i = 0; i < 26; i++) { const t = i / 25, px = -165 + t * 330, py = 10 + Math.sin(t * Math.PI) * 88; x.beginPath(); x.moveTo(px - 6, py - 6); x.lineTo(px + 6, py - 6); x.lineTo(px, py + 10); x.fill(); }
  x.strokeStyle = '#2a0a00'; x.lineWidth = 2.5; for (let i = 0; i < 16; i++) { const t = i / 15, px = -160 + t * 320, py = 10 + Math.sin(t * Math.PI) * 88; x.beginPath(); x.moveTo(px - 4, py - 16); x.lineTo(px + 4, py + 16); x.stroke(); }
  x.fillStyle = 'rgba(110,0,0,.8)'; for (let i = 0; i < 10; i++) x.fillRect(rand(-150, 150), rand(40, 100), rand(3, 6), rand(40, 130));
  x.restore();
  hairCurtain(x, W, H, 110, 160, .8);
  faceFinish(x, W, H); return c;
}
const screamFaces = [];
let screamCd = 0, lastFace = null, lastAnim = null;
function showFace(cls, ms) {
  if (!screamFaces.length) ['maw', 'woman', 'child', 'maw', 'woman', 'child'].forEach(st => screamFaces.push(drawScreamer(st)));
  let f; do { f = pick(screamFaces); } while (f === lastFace && screamFaces.length > 1); lastFace = f;
  const el = $('screamer');
  el.width = f.width; el.height = f.height; el.getContext('2d').drawImage(f, 0, 0);
  el.classList.remove('on', 'sub', 'rush', 'strobe', 'slide'); void el.offsetWidth; el.classList.add(cls);
  setTimeout(() => el.classList.remove(cls), ms);
}
function screamer(force = false) {
  if (!force && screamCd > 0) return false;
  screamCd = 40;
  let cls; do { cls = pick(['on', 'rush', 'strobe', 'slide']); } while (cls === lastAnim); lastAnim = cls;
  showFace(cls, 800);
  A.screech(null, 1.2, 1.3); A.hit(1.1); setTimeout(() => A.ring(), 750);
  if (cls === 'strobe') { setTimeout(() => A.screech(null, .5, .9), 300); }
  S.glitch = 1.3; shake(1.2); redFlash(.7);
  return true;
}
function subliminal() {
  showFace('sub', 60 + Math.random() * 50);
  A.boom(.35); S.glitch = Math.max(S.glitch || 0, .7);
}

/* ======================= YENİ ÜRPERTİCİ SESLER ======================= */
Object.assign(A, {
  cry(pos, dur = 3) { // uzaktan kadın ağlaması
    const d = pos ? this.panner(pos) : this.out(null, .5);
    let t = this.t;
    while (t < this.t + dur) {
      const L = rand(.25, .6), f0 = rand(300, 420);
      const o = this.ctx.createOscillator(); o.type = 'sawtooth';
      o.frequency.setValueAtTime(f0, t); o.frequency.linearRampToValueAtTime(f0 * rand(.7, .85), t + L);
      const v = this.ctx.createOscillator(); v.frequency.value = rand(6, 9); const vg = this.ctx.createGain(); vg.gain.value = 9; v.connect(vg); vg.connect(o.frequency);
      const f1 = this.ctx.createBiquadFilter(); f1.type = 'bandpass'; f1.frequency.value = 850; f1.Q.value = 5;
      const f2 = this.ctx.createBiquadFilter(); f2.type = 'bandpass'; f2.frequency.value = 1250; f2.Q.value = 6;
      const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(.22, t + .05); g.gain.exponentialRampToValueAtTime(.0001, t + L);
      o.connect(f1); o.connect(f2); f1.connect(g); f2.connect(g); g.connect(d);
      o.start(t); o.stop(t + L + .02); v.start(t); v.stop(t + L + .02);
      t += L + rand(.08, .35);
      if (Math.random() < .3) { // hıçkırık nefesi
        const n = this.src(), nf = this.ctx.createBiquadFilter(); nf.type = 'bandpass'; nf.frequency.value = 1600; nf.Q.value = 2;
        const ng = this.ctx.createGain(); ng.gain.setValueAtTime(.0001, t); ng.gain.exponentialRampToValueAtTime(.12, t + .15); ng.gain.exponentialRampToValueAtTime(.0001, t + .3);
        n.connect(nf); nf.connect(ng); ng.connect(d); n.start(t, Math.random()); n.stop(t + .32); t += .35;
      }
    }
  },
  ring(vol = .035) { // kulak çınlaması
    const t = this.t, d = this.out(null, 0);
    [6200, 6260].forEach(f => { const o = this.ctx.createOscillator(); o.frequency.value = f; const g = this.ctx.createGain(); g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(.0001, t + 3.5); o.connect(g); g.connect(d); o.start(t); o.stop(t + 3.6); });
  },
  scrape(pos, dur = 1.2, vol = .4) { // yerde sürüklenen metal
    const t = this.t, d = this.dest(pos, .5);
    const n = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.Q.value = 14;
    for (let i = 0; i < dur * 20; i++) f.frequency.setValueAtTime(rand(1200, 2600), t + i * .05);
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + .1); g.gain.setValueAtTime(vol, t + dur - .2); g.gain.exponentialRampToValueAtTime(.0001, t + dur);
    n.connect(f); f.connect(g); g.connect(d); n.start(t, Math.random()); n.stop(t + dur + .05);
    const o = this.ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = rand(70, 95); const lp = this.ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 300;
    const og = this.ctx.createGain(); og.gain.setValueAtTime(.0001, t); og.gain.exponentialRampToValueAtTime(vol * .5, t + .1); og.gain.exponentialRampToValueAtTime(.0001, t + dur);
    o.connect(lp); lp.connect(og); og.connect(d); o.start(t); o.stop(t + dur + .05);
  },
});

/* ==================== KARANLIKTA SIRITAN DİŞLER ===================== */
const grin = new THREE.Group();
{
  const tm = new THREE.MeshBasicMaterial({ color: 0xfff2d8 });
  for (let i = 0; i < 14; i++) {
    const a = (i / 13 - .5) * 2.6;
    const u = new THREE.Mesh(new THREE.ConeGeometry(.013, rand(.05, .09), 4), tm); u.position.set(Math.sin(a) * .2, .02 - Math.cos(a) * .03, Math.cos(a) * .04); u.rotation.x = Math.PI; grin.add(u);
    const l = new THREE.Mesh(new THREE.ConeGeometry(.012, rand(.04, .08), 4), tm); l.position.set(Math.sin(a) * .18, -.06 + Math.cos(a) * .02, Math.cos(a) * .04); grin.add(l);
  }
  grin.visible = false; scene.add(grin);
}

/* ================= ARKANDAN GELEN AYAK SESLERİ (TAKİPÇİ) ================= */
const crumbs = []; let crumbT = 0;
function stalkerPos() { return crumbs.length ? crumbs[Math.max(0, crumbs.length - 1 - 22)] : player.pos; }
function startStalker(dur = 14) { if (!S.stalk) S.stalk = { t: dur, extra: false, lastStep: S.time }; }
function onPlayerStep() {
  if (!S.stalk) return;
  S.stalk.extra = false; S.stalk.lastStep = S.time;
  later(rand(.28, .42), () => {
    if (!S.stalk) return;
    const p = stalkerPos(); if (p.distanceTo(player.pos) < 1.6) return;
    A.step(S.running ? .7 : .45, p.clone().setY(.1), Math.random() < .35, .85);
  });
}
function updateStalker(dt) {
  crumbT -= dt;
  if (crumbT <= 0) { crumbT = .1; crumbs.push(player.pos.clone()); if (crumbs.length > 40) crumbs.shift(); }
  const st = S.stalk; if (!st) return;
  st.t -= dt;
  const p = stalkerPos(), dx = p.x - player.pos.x, dz = p.z - player.pos.z, d = Math.hypot(dx, dz);
  // sen durunca... o da durur. Ama bir adım geç.
  if (S.time - st.lastStep > .8 && !st.extra && d > 1.6) {
    st.extra = true;
    later(.45, () => { if (S.stalk) A.step(.55, p.clone().setY(.1), false, .8); });
    later(1.5, () => { if (S.stalk) A.breath(.12, false); });
  }
  // dönüp bakarsan...
  const fx = -Math.sin(player.yaw), fz = -Math.cos(player.yaw);
  if (d > 2 && (dx * fx + dz * fz) / d > .8 && lineClear(player.pos.x, player.pos.z, p.x, p.z)) {
    S.stalk = null;
    if (Math.random() < .45) { standFacing(shadowRunner, p); animateMonster(shadowRunner, 0, 0, false, true); shadowRunner.visible = true; A.hit(.9); shake(.6); S.glitch = .8; setTimeout(() => { shadowRunner.visible = false; }, 180); }
    else { duck(2); A.ring(.02); }
    return;
  }
  if (st.t <= 0) { S.stalk = null; A.whisper(0, 1.4, .45, camera.localToWorld(new THREE.Vector3(-.25, 0, .35))); }
}

/* =========================== YENİ KORKULAR =========================== */
Object.assign(DIRECTOR, {
  screamer() { return screamer(); },
  subliminal() { if (S.flashOn === false) return false; subliminal(); return true; },
  stalker() { if (S.hidden || S.stalk) return false; startStalker(rand(12, 20)); return true; },
  stalker2() { if (S.hidden || S.stalk) return false; startStalker(rand(10, 16)); return true; },
  cry() {
    const c = floorCells.filter(([x, z]) => { const d = Math.hypot(cc(x) - player.pos.x, cc(z) - player.pos.z); return d > 9 && d < 16 && roomOf(x, z); });
    if (!c.length) return false; const q = pick(c);
    S.cryArm = { pos: new THREE.Vector3(cc(q[0]), 1, cc(q[1])), t: 22, k: 0 };
    return true;
  },
  grin() {
    const p = spotAhead(5, 9); if (!p) return false;
    const fx = -Math.sin(player.yaw), fz = -Math.cos(player.yaw);
    blackout(2.8); S.flashForcedOff = 2.8; A.flashClick(); duck(2.8);
    S.grinT = 2.8; S.grinFar = p.clone().setY(1.75); S.grinNear = new THREE.Vector3(player.pos.x + fx * 2.2, 1.7, player.pos.z + fz * 2.2);
    later(.6, () => A.growl(S.grinFar, 1.2, .35, 1.3));
    later(1.6, () => { A.whisper(0, .9, .5, S.grinNear); });
    later(2.8, () => { A.hit(1); shake(.7); S.glitch = 1; });
    return true;
  },
  doorBehind() {
    const fx = -Math.sin(player.yaw), fz = -Math.cos(player.yaw);
    const d = doors.find(d => { const dx = cc(d.x) - player.pos.x, dz = cc(d.z) - player.pos.z, l = Math.hypot(dx, dz); return !d.locked && d.open < .3 && l < 9 && l > 1.5 && (dx * fx + dz * fz) / l < -.3; });
    if (!d) return false;
    d.target = 1; d.speed = .3; d.swing = 1; A.creak(new THREE.Vector3(cc(d.x), 1.2, cc(d.z)), 3.2, .3, .6);
    return true;
  },
  drag() {
    const a = Math.random() * 6.28, r = rand(7, 11);
    for (let i = 0; i < 5; i++) later(i * .7, () => A.scrape(new THREE.Vector3(player.pos.x + Math.cos(a + i * .2) * r, .2, player.pos.z + Math.sin(a + i * .2) * r), .9, .45));
    later(3.8, () => A.growl(new THREE.Vector3(player.pos.x + Math.cos(a + 1) * r, 2, player.pos.z + Math.sin(a + 1) * r), 1.6, .6));
    return true;
  },
});
// karanlıkta görünmesi için dişler daha parlak: sis dışı
grin.traverse(o => { if (o.material) o.material.fog = false; });

function updateHorror(dt) {
  screamCd -= dt;
  S.glitch = Math.max(0, (S.glitch || 0) - dt * 1.4);
  updateStalker(dt);
  // ağlayan kadın
  const cr = S.cryArm;
  if (cr) {
    cr.t -= dt; cr.k -= dt;
    if (cr.k <= 0) { cr.k = 3.4; A.cry(cr.pos, 3); }
    if (cr.pos.distanceTo(player.pos.clone().setY(1)) < 4.5) { S.cryArm = null; A.hit(1); A.screech(cr.pos, .9, 1); subliminal(); shake(.6); }
    else if (cr.t <= 0) S.cryArm = null;
  }
  // sırıtan dişler: uzakta belirir, sonra dibine gelir
  if (S.grinT > 0) {
    S.grinT -= dt;
    const near = S.grinT < 1.3;
    grin.visible = S.grinT < 2.5 && S.grinT > .05;
    grin.position.copy(near ? S.grinNear : S.grinFar);
    grin.lookAt(player.pos.x, grin.position.y, player.pos.z);
    grin.scale.setScalar(near ? 1.3 : 1);
    if (S.grinT <= 0) grin.visible = false;
  }
  // ateş
  if (S.fireT > 0) { S.fireT -= dt; altarFire.intensity = (S.fireT > 0 ? 9 : 0) * (.7 + Math.random() * .5); altarDolls.concat(altarPages).forEach(d => d.scale.setScalar(Math.max(.01, S.fireT / 5))); if (S.fireT <= 0) altarDolls.concat(altarPages).forEach(d => d.visible = false); }
  // bebeklerin müzik kutusu fenerleri
  if (S.chapter === 2) for (const it of items) if (it.type === 'doll' && !it.taken) {
    it.beacon -= dt;
    if (it.beacon <= 0) {
      it.beacon = rand(4, 6);
      if (it.pos.distanceTo(player.pos) < 30) A.musicBox(it.pos.clone().setY(.4), [[1319, .22], [1175, .22], [988, .22], [880, .5]].map(([f, l]) => [f * rand(.97, 1.0), l]));
    }
  }
}

/* ====================== v4: SESLER, KAPILAR, YENİ KORKULAR ====================== */
Object.assign(A, {
  tick(pos, vol = .6) { // pençe tıkırtısı (fayansa vuran tırnak)
    const t = this.t, d = this.dest(pos, .35);
    const s = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = rand(3000, 5200); f.Q.value = 6;
    const g = this.ctx.createGain(); this.env(g, t, .001, vol, .025); s.connect(f); f.connect(g); g.connect(d); s.start(t, Math.random()); s.stop(t + .05);
    const o = this.ctx.createOscillator(); o.frequency.value = rand(1800, 2600); const og = this.ctx.createGain(); this.env(og, t, .001, vol * .25, .02); o.connect(og); og.connect(d); o.start(t); o.stop(t + .04);
  },
  clawRun(from, to, dur = 1.6, vol = .8) { // arkandan "tık tık tık" koşarak gelen şey
    let k = 0; const n = Math.round(dur * 11);
    for (let i = 0; i < n; i++) {
      const u = i / n, tt = dur * (1 - Math.pow(1 - u, 1.35)); // hızlanarak
      later(tt, () => { const p = from.clone().lerp(to, u).setY(.05); this.tick(p, vol * (.5 + u * .7)); if (i % 2 === 0) this.step(.35 + u * .5, p, true, 1.5); });
      k++;
    }
  },
  moan(pos, vol = .2) { // uzaktan inleme
    const t = this.t, d = this.dest(pos, .8), o = this.ctx.createOscillator(); o.type = 'triangle';
    const f0 = rand(180, 260); o.frequency.setValueAtTime(f0, t); o.frequency.linearRampToValueAtTime(f0 * 1.15, t + 1); o.frequency.exponentialRampToValueAtTime(f0 * .6, t + 3);
    const v = this.ctx.createOscillator(); v.frequency.value = 5; const vg = this.ctx.createGain(); vg.gain.value = 6; v.connect(vg); vg.connect(o.frequency);
    const f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 700; f.Q.value = 2;
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + .8); g.gain.exponentialRampToValueAtTime(.0001, t + 3.2);
    o.connect(f); f.connect(g); g.connect(d); o.start(t); o.stop(t + 3.3); v.start(t); v.stop(t + 3.3);
  },
  bell(pos, vol = .25) { // şapelde uzak çan
    const t = this.t, d = this.dest(pos, .9);
    [1, 2.4, 3.9, 5.4].forEach((h, i) => { const o = this.ctx.createOscillator(); o.frequency.value = 110 * h; const g = this.ctx.createGain(); this.env(g, t, .005, vol * [.6, .3, .15, .08][i], 5); o.connect(g); g.connect(d); o.start(t); o.stop(t + 5.2); });
  },
  swell(vol = .25) { // tersine yükselen uğultu, aniden kesilir
    const t = this.t, d = this.out(null, .6), n = this.src(), f = this.ctx.createBiquadFilter(); f.type = 'lowpass';
    f.frequency.setValueAtTime(200, t); f.frequency.exponentialRampToValueAtTime(3000, t + 2.5);
    const g = this.ctx.createGain(); g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + 2.5); g.gain.setValueAtTime(.0001, t + 2.52);
    n.connect(f); f.connect(g); g.connect(d); n.start(t, Math.random()); n.stop(t + 2.6);
  },
  pipes(pos) { for (let i = 0; i < 4; i++) later(i * rand(.15, .3), () => this.metal(pos, .18)); },
});
// arka plan: her birkaç saniyede bir uzaktan ürpertici bir ses
const AMBIENT = [
  p => A.moan(p, .14), p => A.pipes(p), p => A.whisper(rand(-1, 1), 2, .08), p => A.creak(p, 2.5, .15, .5),
  p => A.slam(p, .3), p => A.laugh(p), p => A.bell(new THREE.Vector3(cc(14), 3, cc(24)), .16), () => A.swell(.15),
  p => { for (let i = 0; i < 5; i++) later(i * .35, () => A.step(.4, p.clone().setY(WALL_H + .3), true, .7)); },
  p => A.cry(p, 2.5), p => A.scrape(p, 1.6, .2), p => A.staticNoise(p, 1.2, .15), p => A.knock(p, 2, .35), p => A.growl(p, 1.8, .2, .8),
];
let ambT2 = 6, lastAmb = -1;
function ambientScares(dt) {
  ambT2 -= dt; if (ambT2 > 0) return;
  ambT2 = rand(6, 13) * (S.chapter === 3 ? .7 : 1);
  let i; do { i = (Math.random() * AMBIENT.length) | 0; } while (i === lastAmb); lastAmb = i;
  const a = Math.random() * 6.28, r = rand(9, 20);
  AMBIENT[i](new THREE.Vector3(player.pos.x + Math.cos(a) * r, rand(.5, 2.5), player.pos.z + Math.sin(a) * r));
}
// kapılar: yaklaşınca kendiliğinden açılır
function autoDoors() {
  const sp = Math.hypot(player.vel.x, player.vel.z); if (sp < .8 || S.hidden) return;
  const vx = player.vel.x / sp, vz = player.vel.z / sp;
  for (const d of [0.6, 1.2, 1.8]) {
    const cx = toCell(player.pos.x + vx * d), cz = toCell(player.pos.z + vz * d), door = doorAt(cx, cz);
    if (!door || door.locked || door.target > .5 || door.open > .5) continue;
    const p = new THREE.Vector3(cc(door.x), 0, cc(door.z));
    door.target = 1; door.swing = door.ew ? (player.pos.z < p.z ? -1 : 1) : (player.pos.x < p.x ? 1 : -1);
    const quiet = S.crouch; door.speed = quiet ? 1.2 : 3.2;
    A.creak(p.clone().setY(1.2), quiet ? 1 : .6, quiet ? .05 : .25, quiet ? .8 : 1.1);
    emitNoise(player.pos, quiet ? 1.5 : 7);
    return;
  }
}
// hayalet kapılar: bir anda kendiliğinden açılıp kapanır
let ghostDoorT = 45;
function ghostDoors(dt) {
  if (isMP() && !NET.host) return;
  ghostDoorT -= dt; if (ghostDoorT > 0) return;
  ghostDoorT = rand(40, 75) * (S.chapter === 3 ? .7 : 1);
  const near = doors.filter(d => !d.locked && Math.hypot(cc(d.x) - player.pos.x, cc(d.z) - player.pos.z) < 14 && !(toCell(player.pos.x) === d.x && toCell(player.pos.z) === d.z));
  if (!near.length) return;
  const d = pick(near), p = new THREE.Vector3(cc(d.x), 1.2, cc(d.z)), kind = Math.random();
  if (kind < .35) { d.target = d.target > .5 ? 0 : 1; d.speed = 9; d.swing = rand(-1, 1) < 0 ? -1 : 1; A.slam(p, 1.1); shake(.2); }
  else if (kind < .7) { d.target = 1; d.speed = 7; d.swing = 1; A.slam(p, .8); later(.9, () => { d.target = 0; d.speed = 9; A.slam(p, 1.2); }); }
  else { for (let i = 0; i < 4; i++) later(i * .32, () => { d.target = i % 2 ? 0 : 1; d.speed = 10; d.swing = 1; A.slam(p, .7 + i * .12); }); }
}
// 3B korkular için ayrı bir yaratık kopyası
let lunger = null;
const scare3d = { ceil: null, sprint: null };
Object.assign(DIRECTOR, {
  tickRun() { // arkandan tık tık tık koşarak geliyor... ve kayboluyor
    const fx = -Math.sin(player.yaw), fz = -Math.cos(player.yaw);
    const from = new THREE.Vector3(player.pos.x - fx * 14, 0, player.pos.z - fz * 14), to = new THREE.Vector3(player.pos.x - fx * 1.2, 0, player.pos.z - fz * 1.2);
    duck(2.2); A.clawRun(from, to, 1.9, .9);
    later(1.95, () => { A.screech(to.clone().setY(1.5), .5, .8); A.whisper(0, .8, .5, camera.localToWorld(new THREE.Vector3(0, 0, .3))); shake(.5); S.glitch = .6; });
    return true;
  },
  ceilingDrop() { // tavandan baş aşağı sarkar, tam önüne
    if (scare3d.ceil) return false;
    const p = spotAhead(1.3, 1.9); if (!p) return false;
    duck(1.2);
    later(1.2, () => { scare3d.ceil = { t: 0, p, yaw: Math.atan2(player.pos.x - p.x, player.pos.z - p.z) }; lunger.visible = true; A.slam(p.clone().setY(WALL_H), .8); A.hit(1.1); A.screech(p.clone().setY(1.6), 1, 1.1); shake(.9); S.glitch = .7; });
    return true;
  },
  sprint() { // koridorun sonundan üstüne koşar, son anda yok olur
    if (scare3d.sprint) return false;
    const p = spotAhead(10, 15); if (!p) return false;
    scare3d.sprint = { t: 0, from: p, to: new THREE.Vector3(player.pos.x, 0, player.pos.z) };
    lunger.visible = true; A.screech(p.clone().setY(1.8), 1.3, 1); A.riser(.9, .4);
    return true;
  },
  doorWave() { // koridordaki kapılar sırayla çarpar, sana doğru
    const list = doors.filter(d => !d.locked && Math.hypot(cc(d.x) - player.pos.x, cc(d.z) - player.pos.z) < 20 && !(toCell(player.pos.x) === d.x && toCell(player.pos.z) === d.z))
      .sort((a, b) => Math.hypot(cc(b.x) - player.pos.x, cc(b.z) - player.pos.z) - Math.hypot(cc(a.x) - player.pos.x, cc(a.z) - player.pos.z)).slice(0, 5);
    if (list.length < 2) return false;
    duck(1);
    list.forEach((d, i) => later(1 + i * .38, () => { d.target = d.open > .5 ? 0 : 1; d.speed = 11; d.swing = 1; A.slam(new THREE.Vector3(cc(d.x), 1.2, cc(d.z)), 1.2); flicker(.25); }));
    later(1 + list.length * .38 + .3, () => { A.hit(.7); shake(.5); });
    return true;
  },
});
function update3dScares(dt) {
  const c = scare3d.ceil;
  if (c) {
    c.t += dt; const u = lunger.userData;
    lunger.rotation.set(0, c.yaw, Math.PI);
    u.jaw.rotation.x = c.t < .15 ? .2 : .95 + Math.sin(c.t * 40) * .1; spreadJaw(u);
    u.head.rotation.z = Math.sin(c.t * 25) * .3; u.neck.rotation.x = -.2; u.spine.rotation.x = .1;
    u.arms.forEach(a => { a.sh.rotation.x = -1.2 + Math.sin(c.t * 18 + a.s) * .3; a.sh.rotation.z = a.s * .6; a.el.rotation.x = -.5; });
    const y = c.t < .12 ? lerp(WALL_H + .8, 1.55, c.t / .12) : c.t < .9 ? 1.55 + Math.sin(c.t * 30) * .02 : lerp(1.55, WALL_H + 1.2, (c.t - .9) / .18);
    lunger.position.set(0, 0, 0); placeHeadAt(lunger, new THREE.Vector3(c.p.x, y, c.p.z));
    if (c.t > 1.1) { lunger.visible = false; scare3d.ceil = null; }
  }
  const sp = scare3d.sprint;
  if (sp) {
    sp.t += dt; const u = lunger.userData;
    const L = sp.from.distanceTo(sp.to), k = Math.min(1, sp.t * 12 / L);
    lunger.rotation.set(0, Math.atan2(sp.to.x - sp.from.x, sp.to.z - sp.from.z), 0);
    lunger.position.copy(sp.from).lerp(sp.to, k);
    animateMonster(lunger, 0, 6, true, false);
    const ph = sp.t * 28; u.legs.forEach(l => { l.hip.rotation.x = Math.sin(ph + l.s * 1.6) * 1.1 - .5; l.kn.rotation.x = .6 + Math.max(0, Math.sin(ph + l.s)) * .9; });
    if (Math.floor(sp.t * 14) !== Math.floor((sp.t - dt) * 14)) A.tick(lunger.position, .9);
    if (lunger.position.distanceTo(player.pos) < 1.3 || k >= 1) { lunger.visible = false; scare3d.sprint = null; A.hit(1); S.glitch = 1; shake(1); flash(.2); if (Math.random() < .5) subliminal(); }
  }
}
// lamba altı ışık sütunları + floresan vızıltısı
const shafts = [];
function buildShafts() {
  const geo = new THREE.CylinderGeometry(.45, 1.5, WALL_H - .15, 24, 1, true);
  for (const L of lamps) {
    const mat = new THREE.ShaderMaterial({
      uniforms: { uColor: { value: L.light.color.clone() }, uI: { value: 0 } },
      vertexShader: `varying vec2 vUv; varying vec3 vN; varying vec3 vV; void main(){ vUv = uv; vec4 mv = modelViewMatrix * vec4(position,1.); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`,
      fragmentShader: `uniform vec3 uColor; uniform float uI; varying vec2 vUv; varying vec3 vN; varying vec3 vV; void main(){ float f = pow(abs(dot(vN, vV)), 1.6); float a = uI * f * pow(vUv.y, 1.4) * .055; gl_FragColor = vec4(uColor * a, a); }`,
      transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide,
    });
    const m = new THREE.Mesh(geo, mat); m.position.set(L.light.position.x, (WALL_H - .15) / 2, L.light.position.z); world.add(m);
    L.shaft = m; shafts.push(m);
  }
}
function lampBuzz() { // ses motoru açıldıktan sonra
  for (const L of lamps) { L.hum = A.hum(L.light.position, 0); }
}
function updateShafts() {
  for (const L of lamps) {
    if (!L.shaft) continue;
    L.shaft.material.uniforms.uI.value = L.light.intensity / Math.max(1, L.base) * (S.state === 'title' ? 1 : 1);
    L.shaft.material.uniforms.uColor.value.copy(L.light.color);
    if (L.hum) L.hum.gain.setTargetAtTime(L.light.intensity > .5 ? .035 : 0, A.t, .02);
  }
}

/* ===================== v5: GÖZLER, AV, SANRI, KASA ===================== */
// --- uzaktan izleyen gözler
const watchers = [];
function makeEyes() {
  const g = new THREE.Group();
  const mat = new THREE.MeshBasicMaterial({ color: 0xfff1b8, fog: false });
  for (const sx of [-1, 1]) {
    const e = new THREE.Mesh(new THREE.SphereGeometry(.03, 8, 6), mat); e.position.x = sx * .06; e.scale.y = .7; g.add(e);
    const gl = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xffd890, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: .5, fog: false }));
    gl.scale.setScalar(.28); gl.position.x = sx * .06; g.add(gl);
  }
  g.visible = false; scene.add(g);
  return { g, active: false, t: 0, life: 0, seen: false, blink: 2, lit: 0 };
}
for (let i = 0; i < 12; i++) watchers.push(makeEyes());
function spawnEyes(p, life = 30) {
  const w = watchers.find(w => !w.active); if (!w) return null;
  Object.assign(w, { active: true, t: 0, life, seen: false, blink: rand(1.5, 4), lit: 0, closing: 0 });
  w.g.position.copy(p); w.g.scale.set(1, 1, 1); w.g.visible = true; return w;
}
function closeEyes(w, sound = true) {
  if (!w.active || w.closing) return; w.closing = .14;
  if (sound) { const r = Math.random(); if (r < .35) A.whisper(0, 1, .25, w.g.position); else if (r < .6) A.laugh(w.g.position); else { const away = w.g.position.clone().add(w.g.position.clone().sub(player.pos).setY(0).normalize().multiplyScalar(6)); A.clawRun(w.g.position.clone(), away, .8, .5); } }
}
function updateWatchers(dt) {
  S.watchT = (S.watchT ?? 18) - dt;
  if (S.watchT <= 0 && !S.hidden) {
    S.watchT = rand(14, 26);
    let p = spotAhead(11, 22);
    if (!p) { const c = floorCells.filter(([x, z]) => { const d = Math.hypot(cc(x) - player.pos.x, cc(z) - player.pos.z); return d > 11 && d < 20 && lineClear(player.pos.x, player.pos.z, cc(x), cc(z)); }); if (c.length) { const q = pick(c); p = new THREE.Vector3(cc(q[0]) + rand(-1, 1), 0, cc(q[1]) + rand(-1, 1)); } }
    if (p) { p.y = pick([2.15, 1.75, 1.6, .32]); spawnEyes(p, rand(20, 35)); }
  }
  const fwd = camera.getWorldDirection(_v2);
  for (const w of watchers) {
    if (!w.active) continue;
    w.t += dt;
    w.g.lookAt(camera.position);
    if (w.closing) { w.closing -= dt; w.g.scale.y = Math.max(.05, w.closing / .14); if (w.closing <= 0) { w.active = false; w.g.visible = false; } continue; }
    w.blink -= dt; w.g.scale.y = w.blink < 0 ? .08 : 1; if (w.blink < -.13) w.blink = rand(2, 5);
    const to = w.g.position.clone().sub(camera.position), d = to.length(); to.normalize();
    const dot = to.dot(fwd);
    if (dot > .9 && !w.seen && d < 24) { w.seen = true; A.heart(.7); later(.25, () => A.heart(.6)); A.sting(.22); S.fearKick = .6; }
    if (dot > .975 && S.flashOn && d < 15) w.lit += dt; else w.lit = Math.max(0, w.lit - dt);
    if (d < 6.5 || w.lit > .4 || w.t > w.life) closeEyes(w);
  }
}
// --- kapı açınca sürpriz
let doorScareCd = 20, lastDoorScare = '';
function doorSurprise(d) {
  if (doorScareCd > 0 || mon.state === 'chase' || Math.random() > .32) return;
  const c = new THREE.Vector3(cc(d.x), 0, cc(d.z)), dir = c.clone().sub(player.pos).setY(0).normalize();
  let beyond = c.clone().addScaledVector(dir, 1.4);
  if (!passable(toCell(beyond.x), toCell(beyond.z))) beyond = c.clone().addScaledVector(dir, .8);
  let kinds = ['face', 'swarm', 'fall', 'runaway', 'screamer'].filter(k => k !== lastDoorScare);
  if (hangBody.visible) kinds = kinds.filter(k => k !== 'fall');
  const k = pick(kinds); lastDoorScare = k; doorScareCd = rand(30, 50);
  if (k === 'face') later(.3, () => { standFacing(peekHead, beyond); animateMonster(peekHead, 0, 0, false, true); peekHead.userData.jaw.rotation.x = .9; spreadJaw(peekHead.userData); peekHead.visible = true; A.hit(1.1); A.screech(beyond.clone().setY(1.7), .9, 1); shake(.8); S.glitch = .6; later(.75, () => { peekHead.visible = false; }); });
  if (k === 'swarm') { for (let i = 0; i < 9; i++) { const q = beyond.clone().addScaledVector(dir, rand(.5, 4)).add(new THREE.Vector3(-dir.z, 0, dir.x).multiplyScalar(rand(-2.2, 2.2))); q.y = rand(.3, 2.3); spawnEyes(q, 2.6); } A.sting(.6); later(.3, () => { A.whisper(-1, 2, .3); A.whisper(1, 2, .3); }); later(2.4, () => { watchers.forEach(w => closeEyes(w, false)); A.hit(.7); }); }
  if (k === 'fall') { hangBody.userData.rope.visible = false; hangBody.rotation.order = 'YXZ'; hangBody.position.copy(beyond); hangBody.rotation.set(0, Math.atan2(player.pos.x - beyond.x, player.pos.z - beyond.z), 0); hangBody.userData.head.rotation.z = .5; hangBody.visible = true; S.fall = { t: 0 }; A.creak(beyond.clone().setY(1.5), .6, .2, .6); }
  if (k === 'runaway') { actorRuns.push({ m: shadowRunner, a: beyond.clone(), b: beyond.clone().addScaledVector(dir, 6), t: 0, dur: .7, kind: 'run' }); A.clawRun(beyond.clone(), beyond.clone().addScaledVector(dir, 6), .7, .9); later(.2, () => A.laugh(beyond.clone().setY(1))); A.sting(.5); }
  if (k === 'screamer') later(.3, () => screamer(true));
}
function updateFall(dt) {
  if (!S.fall) return;
  S.fall.t += dt; const k = Math.min(1, S.fall.t / .55);
  hangBody.rotation.x = k * k * Math.PI / 2; hangBody.position.y = k * .1;
  if (k >= 1 && !S.fall.hit) { S.fall.hit = true; A.slam(hangBody.position.clone().setY(.3), 1.2); A.hit(.9); shake(.7); }
  if (S.fall.t > 12) { hangBody.visible = false; hangBody.userData.rope.visible = true; hangBody.rotation.set(0, 0, 0); S.fall = null; }
}
// --- AV: yaratık seni aramaya çıkar
function startHunt(dur = 18) {
  if (S.hunting > 0 || mon.state === 'chase' || !mon.active) return false;
  S.hunting = dur; S.huntPing = 0;
  A.screech(mon.pos.clone().setY(2), 1.8, 1.3); A.gliss(.07); flicker(1.6); shake(.3);
  msg('<b style="color:#ff3a3a;letter-spacing:3px">O SENİ ARIYOR</b><br><span style="font-size:15px">Saklan ya da eğilip sessizce uzaklaş</span>', 4);
  return true;
}
function updateHunt(dt) {
  if (isMP() && !NET.host) { if (S.hunting > 0) S.hunting -= dt; return; }
  if (S.hunting > 0) {
    S.hunting -= dt; S.huntPing -= dt;
    if (S.huntPing <= 0 && mon.state !== 'chase' && mon.state !== 'locker') {
      S.huntPing = 3.5; const a = rand(0, 6.28), r = S.hidden ? rand(3, 7) : rand(1.5, 6);
      monSetTarget(player.pos.x + Math.cos(a) * r, player.pos.z + Math.sin(a) * r, 'investigate');
      A.click(mon.pos.clone().setY(2), 6, .8);
    }
    if (S.hunting <= 0) { A.growl(mon.pos.clone().setY(2), 2, .6, .9); sub('...uzaklaştı.', 2.5); }
    return;
  }
  S.huntT = (S.huntT ?? 60) - dt;
  if (S.huntT <= 0) { S.huntT = rand(55, 85) * [1, 1, .8, .6][S.chapter || 1] * (diff === 0 ? 1.4 : diff === 2 ? .7 : 1); const hd = diff === 0 ? 13 : 18; if (startHunt(hd)) NET.send({ k: 'hunt', d: hd }); }
}
// --- SANRI: dünya kızarır, etrafında kıpırdamayan figürler belirir
const halluFigs = [];
function hallucinate(dur = 8) {
  if (S.halluT > 0) return false;
  if (!halluFigs.length) for (let i = 0; i < 7; i++) { const f = humanoid(new THREE.MeshBasicMaterial({ color: 0x030303 }), rand(.95, 1.15)); f.visible = false; scene.add(f); halluFigs.push(f); }
  S.halluT = dur; S.halluMax = dur;
  halluFigs.forEach((f, i) => {
    for (let k = 0; k < 8; k++) {
      const a = i / halluFigs.length * 6.28 + rand(-.4, .4), r = rand(3.5, 8), x = player.pos.x + Math.cos(a) * r, z = player.pos.z + Math.sin(a) * r;
      if (passable(toCell(x), toCell(z)) && lineClear(player.pos.x, player.pos.z, x, z)) { f.position.set(x, 0, z); f.rotation.y = Math.atan2(player.pos.x - x, player.pos.z - z); f.userData.head.rotation.z = rand(-.6, .6); f.visible = true; break; }
    }
  });
  A.swell(.3); A.heart(.8); duck(1);
  for (let i = 0; i < 5; i++) later(.5 + i * 1.2, () => A.whisper(rand(-1, 1), 1.6, .3));
  later(2, () => A.cry(null, 2.5));
  return true;
}
function updateHallu(dt) {
  if (!(S.halluT > 0)) { S.hallu = Math.max(0, (S.hallu || 0) - dt * 2); return; }
  S.halluT -= dt;
  const el = S.halluMax - S.halluT;
  S.hallu = Math.min(1, el / .8, S.halluT / .6);
  S.halluStep = (S.halluStep ?? 2) - dt;
  if (S.halluStep <= 0) { // bakmadığın an bir adım yaklaşırlar
    S.halluStep = 1.8;
    for (const f of halluFigs) if (f.visible) { const d = f.position.clone().sub(player.pos).setY(0); const L = d.length(); if (L > 2) { f.position.addScaledVector(d.normalize(), -.9); f.rotation.y = Math.atan2(player.pos.x - f.position.x, player.pos.z - f.position.z); f.userData.head.rotation.z = rand(-.8, .8); } }
    A.step(.4, player.pos.clone().add(new THREE.Vector3(rand(-3, 3), 0, rand(-3, 3))), false, .8);
  }
  if (S.halluT <= 0) { halluFigs.forEach(f => f.visible = false); A.hit(.9); flash(.35); shake(.6); }
}
// --- KASA ve ŞİFRE
const SAFE_POS = new THREE.Vector3(cc(34), .79, cc(10) - .1);
const CODE_SPOTS = [[6, 24], [16, 19], [34, 24], [2, 12], [28, 14], [8, 20]];
let safeDoor;
function buildSafe() {
  const g = new THREE.Group(); g.position.copy(SAFE_POS); world.add(g);
  const bodyM = new THREE.MeshStandardMaterial({ color: 0x2a2d30, roughness: .35, metalness: .85 });
  const b = box(.6, .5, .45, bodyM); b.position.y = .25; g.add(b);
  safeDoor = new THREE.Group(); safeDoor.position.set(-.29, .25, .235); g.add(safeDoor);
  const dp = box(.56, .46, .04, bodyM); dp.position.x = .28; safeDoor.add(dp);
  const dial = cyl(.06, .06, .03, M.metal, 14); dial.rotation.x = Math.PI / 2; dial.position.set(.28, .03, .03); safeDoor.add(dial);
  const pad = box(.12, .09, .015, M.dark); pad.position.set(.45, -.12, .025); safeDoor.add(pad);
  const led = box(.03, .015, .01, M.red); led.position.set(.45, -.06, .03); safeDoor.add(led); safeDoor.userData.led = led;
}
function newSafe() { S.code = String(1000 + Math.floor(RNG() * 9000)); S.codeKnown = false; S.safeOpen = false; if (safeDoor) { safeDoor.rotation.y = 0; safeDoor.userData.led.material = M.red; } }
function addCodeNote() {
  const [x, z] = pick(CODE_SPOTS);
  const g = new THREE.Group();
  const p = new THREE.Mesh(new THREE.PlaneGeometry(.26, .34), M.paper); p.rotation.x = -Math.PI / 2; p.rotation.z = rand(-.5, .5); g.add(p);
  const pool = new THREE.Mesh(new THREE.CircleGeometry(.45, 14), M.blood); pool.rotation.x = -Math.PI / 2; pool.position.y = -.004; g.add(pool);
  const gl = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xff2a1a, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: .5 })); gl.scale.setScalar(.9); gl.position.y = .15; g.add(gl);
  g.position.set(cc(x) + rand(-.5, .5), .016, cc(z) + rand(-.5, .5)); g.visible = false; world.add(g);
  const it = { type: 'codenote', mesh: g, pos: g.position, taken: false, id: items.length, glow: gl };
  items.push(it); return it;
}
function readCode(it) {
  S.codeKnown = true;
  showNote(`Başhekim Aydemir'in son yazısı (kanla):\n\n"Kasanın şifresini unutmayayım diye buraya yazıyorum. Yüksek sesle söylemedim. O DUYAR.\n\n           ${S.code}\n\nKartı al ve kaç. Benim için çok geç."`, 9);
  sub('ŞİFRE: ' + S.code, 4);
  updateTasks(); saveCheckpoint();
  later(1, () => hallucinate(7));
}
let kpBuf = '';
function openKeypad() {
  S.keypad = true; kpBuf = ''; kpDraw();
  $('keypad').style.display = 'flex'; document.exitPointerLock?.();
}
function closeKeypad() { S.keypad = false; $('keypad').style.display = 'none'; }
function kpDraw(bad) { const el = $('kpScreen'); el.textContent = (kpBuf + '····').slice(0, 4); el.classList.toggle('bad', !!bad); }
function kpPress(k) {
  if (!S.keypad) return;
  const beep = f => { const t = A.t, o = A.ctx.createOscillator(); o.type = 'square'; o.frequency.value = f; const g = A.ctx.createGain(); A.env(g, t, .002, .06, .08); o.connect(g); g.connect(A.master); o.start(t); o.stop(t + .1); };
  if (k === 'del') { kpBuf = kpBuf.slice(0, -1); kpDraw(); beep(600); return; }
  if (k === 'ok' || (k !== 'del' && kpBuf.length >= 4 && k !== 'ok')) { if (k !== 'ok') return; }
  if (k === 'ok') {
    if (kpBuf === S.code) {
      kpDraw(); beep(1400); later(.12, () => beep(1800)); S.safeOpen = true; safeDoor.userData.led.material = M.green; NET.send({ k: 'safe' });
      setTimeout(closeKeypad, 450); A.metal(SAFE_POS, .4); S.safeAnim = 0;
      later(1, () => { const card = items.find(i => i.type === 'card'); card.mesh.visible = true; takeItem(card); });
    } else {
      kpDraw(true); A.buzz(); emitNoise(player.pos, 18); shake(.25); sub('YANLIŞ ŞİFRE — kasa öttü!', 2.5);
      setTimeout(() => { kpBuf = ''; kpDraw(); }, 700);
    }
    return;
  }
  kpBuf += k; kpDraw(); beep(1000);
}
document.querySelectorAll('#keypad button').forEach(b => b.addEventListener('click', e => { e.stopPropagation(); kpPress(b.dataset.k); }));
$('keypad').addEventListener('click', e => { if (e.target.id === 'keypad') closeKeypad(); });
A.buzz = function () { const t = this.t, o = this.ctx.createOscillator(); o.type = 'square'; o.frequency.value = 130; const g = this.ctx.createGain(); this.env(g, t, .005, .25, .7); o.connect(g); g.connect(this.master); o.start(t); o.stop(t + .8); };
// sanrı ve gözler yönetmene de eklenir
Object.assign(DIRECTOR, {
  hallucination() { return hallucinate(rand(6, 9)); },
  eyes() { let n = 0; for (let i = 0; i < 4; i++) { const p = spotAhead(8, 20); if (p) { p.y = rand(.3, 2.2); p.x += rand(-1, 1); p.z += rand(-1, 1); if (spawnEyes(p, 12)) n++; } } if (n) A.whisper(0, 2, .2); return n > 0; },
});

/* ====================== ÇOK OYUNCULU (taslak; aşağıda doldurulur) ====================== */
const NET = { on: false, started: false, host: true, myRoles: [0, 1, 2] };
const FILE_SPOTS = [[12, 3], [27, 3], [8, 12], [23, 10], [3, 22], [30, 20], [17, 24], [3 + F2X, 9], [16 + F2X, 4], [29 + F2X, 12], [20 + F2X, 22], [5 + F2X, 23], [33 + F2X, 20]];
const PAGE_SPOTS = [[15, 10], [33, 2], [6, 19], [25, 24], [10, 6], [13 + F2X, 2], [26 + F2X, 3], [33 + F2X, 9], [9 + F2X, 20], [22 + F2X, 24], [2 + F2X, 6]];
function itemVisible(it) {
  if (it.taken) return false;
  if (it.type === 'card') return !!S.safeOpen;
  if (it.ch) return it.ch === S.chapter;
  return true;
}
function refreshItemVisibility() { items.forEach(it => it.mesh.visible = itemVisible(it)); }
function applyStations(arr) {
  STATIONS.forEach((st, i) => {
    st.done = !!(arr && arr[i]);
    if (st.type === 'valve') st.wheel.rotation.z = st.done ? Math.PI * 3 : 0;
    if (st.type === 'candle') st.flame.visible = st.done;
  });
  if (candleRoomLight) candleRoomLight.intensity = 1.2 * STATIONS.filter(s => s.type === 'candle' && s.done).length;
}
function useStairs([x, z]) {
  if (S.stairT > 0) return;
  const [tx, tz] = stairPair(x, z), [dx, dz] = wallDir(tx, tz);
  S.stairT = 1.2; blackout(.75); emitNoise(player.pos, 5);
  for (let i = 0; i < 7; i++) later(i * .1, () => A.step(.35, null, false, 1.2));
  later(.38, () => { player.pos.set(cc(tx) - dx * 1.1, 0, cc(tz) - dz * 1.1); player.yaw = Math.atan2(dx, dz); player.pitch = 0; A.creak(player.pos.clone().setY(1), .6, .15, .6); });
}

/* ========================= ROLLER VE GÖREVLER ========================= */
const ROLES = [
  { name: 'ELEKTRİKÇİ', css: '#ff7a5c', color: 0xb83a2a },
  { name: 'HEMŞİRE', css: '#7ab8ff', color: 0x2f62b8 },
  { name: 'BEKÇİ', css: '#7fe39a', color: 0x2f8a48 },
];
const TASKDEF = {
  1: [
    { id: 'fuse', role: 0, item: 'fuse', need: [2, 3], label: 'Sigortaları bul', dlabel: 'Sigortaları jeneratördeki kutuya tak', deliver: 'fusebox', mk: 'SİGORTA', dmk: 'SİGORTA KUTUSU' },
    { id: 'file', role: 1, item: 'file', need: [2, 3], label: 'Kayıp hasta dosyalarını topla', dlabel: 'Dosyaları 2. kattaki arşive koy', deliver: 'archive', mk: 'DOSYA', dmk: 'ARŞİV DOLABI' },
    { id: 'valve', role: 2, station: 'valve', need: [2, 3], label: 'Kazan dairesinde vanaları aç (2. kat)', mk: 'VANA' },
  ],
  2: [
    { id: 'doll', role: 0, item: 'doll', need: [2, 3], label: 'Lanetli bebekleri bul', dlabel: 'Bebekleri şapeldeki sunağa koy', deliver: 'altar', mk: 'BEBEK', dmk: 'SUNAK' },
    { id: 'candle', role: 1, station: 'candle', need: [3, 4], label: 'Çocuk koğuşunda mumları yak (2. kat)', mk: 'MUM' },
    { id: 'page', role: 2, item: 'page', need: [2, 3], label: 'Ayin kitabının sayfalarını bul', dlabel: 'Sayfaları şapeldeki sunağa koy', deliver: 'altar', mk: 'SAYFA', dmk: 'SUNAK' },
  ],
};
const TASK_BY_ID = {}; Object.values(TASKDEF).flat().forEach(t => TASK_BY_ID[t.id] = t);
const isMP = () => NET.on && NET.started;
const needOf = t => t.need[isMP() ? 1 : 0];
const chTasks = (ch = S.chapter) => TASKDEF[ch] || [];
const taskDone = t => !!S.tasks[t.id]?.done;
const myRoles = () => isMP() ? NET.myRoles : [0, 1, 2];
const roleFinished = role => chTasks().filter(t => t.role === role).every(taskDone);
const myTasksDone = () => myRoles().every(roleFinished);
const canDoTask = t => !isMP() || myRoles().includes(t.role) || myTasksDone();
function newTasks() { S.tasks = {}; for (const t of Object.values(TASK_BY_ID)) S.tasks[t.id] = { got: 0, done: false }; }
const deliverPos = k => k === 'fusebox' ? fuseBox.pos.clone().setY(1.4) : k === 'archive' ? STATIONS.find(s => s.type === 'archive').pos.clone().setY(1) : ALTAR.clone().setY(1.1);
// diğer kattaki hedef "uzak" sayılır
const goalDist = p => Math.hypot(p.x - player.pos.x, p.z - player.pos.z) + (floorOfX(p.x) !== floorOfX(player.pos.x) ? 35 : 0);
function taskTarget(t) {
  const st = S.tasks[t.id]; if (!st || st.done) return null;
  if (t.item) {
    if (st.got < needOf(t)) {
      let best = null, bd = 1e9; for (const it of items) if (it.task === t.id && !it.taken) { const d = goalDist(it.pos); if (d < bd) { bd = d; best = it; } }
      return best ? { pos: best.pos.clone().setY(.8), mk: t.mk, key: t.id + ':c', t } : null;
    }
    return { pos: deliverPos(t.deliver), mk: t.dmk, key: t.id + ':d', t };
  }
  const sts = STATIONS.filter(s => s.type === t.station && !s.done).sort((a, b) => goalDist(a.pos) - goalDist(b.pos));
  return sts.length ? { pos: sts[0].pos.clone(), mk: t.mk, key: t.id + ':s', t } : null;
}
const nearestOf = list => list.sort((a, b) => goalDist(a.pos) - goalDist(b.pos))[0];
function objective() {
  const ch = S.chapter || 1;
  if (ch <= 2) {
    const mine = chTasks().filter(t => myRoles().includes(t.role)).map(taskTarget).filter(Boolean);
    if (mine.length) return nearestOf(mine);
    const rest = chTasks().map(taskTarget).filter(Boolean);
    if (rest.length) { const o = nearestOf(rest); return { ...o, key: 'help', help: true }; }
    if (ch === 2 && !S.ritual) return { key: 'ritual', pos: ALTAR.clone().setY(1.1), mk: 'SUNAK' };
    return { key: 'wait', pos: fuseBox.pos.clone().setY(1.4), mk: 'JENERATÖR' };
  }
  if (!S.keycard) { const n = !S.codeKnown && nearestItem('codenote'); return n ? { key: 'code', pos: n.pos.clone().setY(.5), mk: 'KANLI NOT' } : { key: 'safe', pos: SAFE_POS.clone().setY(1.1), mk: 'KASA' }; }
  return { key: 'exit', pos: new THREE.Vector3(cc(27), 1.4, cc(26) - C / 2), mk: 'ÇIKIŞ' };
}
const BANNERS = {
  'fuse:c': ['SİGORTALARI BUL', 'Jeneratör için sigortalar lazım. Mavi ◆ işareti takip et.'],
  'fuse:d': ['ELEKTRİĞİ VER', 'Sigortaları jeneratör odasındaki kutuya tak.'],
  'file:c': ['DOSYALARI TOPLA', 'Kayıp hasta dosyaları hastaneye dağılmış.'],
  'file:d': ['ARŞİVE GÖTÜR', 'Dosyaları 2. kattaki arşiv dolabına koy.'],
  'valve:s': ['VANALARI AÇ', '2. kattaki kazan dairesine çık. Vanalar ÇOK gürültülü!'],
  'doll:c': ['BEBEKLERİ BUL', 'Lanetli bebekler... müzik kutusu sesini dinle.'],
  'doll:d': ['SUNAĞA GÖTÜR', 'Bebekleri şapeldeki sunağa koy.'],
  'candle:s': ['MUMLARI YAK', '2. kattaki çocuk koğuşunda mumları yak.'],
  'page:c': ['SAYFALARI BUL', 'Ayin kitabının yırtık sayfaları kanla parlıyor.'],
  'page:d': ['SUNAĞA GÖTÜR', 'Sayfaları şapeldeki sunağa koy.'],
  'help': ['YARDIM ET!', 'Kendi görevlerin bitti. Arkadaşlarının kalan işleri artık senin de görevin.'],
  'ritual': ['AYİNİ BAŞLAT', 'Her şey hazır. Şapeldeki sunakta ayini başlat.'],
  'wait': ['BEKLE...', 'Jeneratör çalışıyor.'],
  'code': ['ŞİFREYİ BUL', 'Kart başhekimin kasasında. Şifre kanlı bir notta yazıyor.'],
  'safe': ['KASAYI AÇ', 'Başhekim odasındaki kasaya şifreyi gir. Yanlış girersen öter!'],
  'exit': ['KAÇ!', 'Lobideki ÇIKIŞ kapısına koş ve kartı okut.'],
};
function banner(key) {
  const b = BANNERS[key]; if (!b) return;
  $('bnT').textContent = b[0]; $('bnD').textContent = b[1];
  $('banner').style.opacity = 1; S.bannerT = 4.5;
  A.gong(); later(1.2, () => showGuide(true));
}
const mk = $('marker'), mkLabel = $('mkLabel');
function nearestStair() {
  const f = floorOfX(player.pos.x); let best = null, bd = 1e9;
  for (const [x, z] of STAIRS) { const p = new THREE.Vector3(cc(x + f * F2X), 1.2, cc(z)); const d = p.distanceTo(player.pos); if (d < bd) { bd = d; best = p; } }
  return best;
}
function updateMarker() {
  const o = objective();
  if (o.key !== S.stage) { S.stage = o.key; banner(o.key); updateTasks(); }
  let target = o.pos, label = o.mk;
  if (floorOfX(o.pos.x) !== floorOfX(player.pos.x)) { target = nearestStair(); label = `${o.mk} · ${floorOfX(o.pos.x) ? '2. KAT' : 'ZEMİN'} → MERDİVEN`; }
  const v = target.clone().project(camera);
  const behind = v.z > 1;
  let x = v.x, y = v.y;
  if (behind) { x = -x; y = -y; }
  const m = .86, edge = behind || Math.abs(x) > m || Math.abs(y) > m;
  if (edge) { const k = m / Math.max(Math.abs(x), Math.abs(y), .0001); x *= k; y *= k; if (behind && Math.abs(y) < m) { y = -m; } }
  const sx = (x * .5 + .5) * innerWidth, sy = (-y * .5 + .5) * innerHeight;
  mk.style.display = S.hidden ? 'none' : 'flex';
  mk.classList.toggle('edge', edge);
  mk.style.transform = `translate(${sx}px,${sy}px) translate(-50%,-50%)`;
  if (edge) mk.querySelector('.arr').style.transform = `rotate(${Math.atan2(x, y)}rad)`;
  const dist = Math.hypot(target.x - player.pos.x, target.z - player.pos.z);
  mkLabel.textContent = `${o.help ? 'YARDIM: ' : ''}${label} · ${Math.round(dist)}m`;
  mk.style.opacity = dist < 2.2 ? .35 : 1;
}
// görev eşyası alındı
function takeTaskItem(it, remote) {
  const t = TASK_BY_ID[it.task], st = S.tasks[t.id];
  st.got = Math.min(needOf(t), st.got + 1);
  if (!remote) {
    sub(`${t.mk} (${st.got}/${needOf(t)})`, 2.2);
    if (t.id === 'fuse') { if (st.got === 1) later(2.5, () => { A.rumble(); sub('...bir şey uyandı.', 2.5); }); if (st.got === 2) faceJumpscare(); }
    if (t.id === 'doll') dollScare(it, st.got, needOf(t));
    if (t.id === 'page') { A.whisper(rand(-1, 1), 2, .35); if (st.got === 2) later(.6, () => hallucinate(6)); }
    if (t.id === 'file' && st.got === needOf(t)) later(.8, () => { duck(1); later(1, () => screamer(true)); });
    if (st.got >= needOf(t)) later(1, () => sub(t.dlabel.toLocaleUpperCase('tr-TR'), 3));
  }
  updateTasks();
}
function dollScare(it, n, need) {
  const p = it.pos.clone().setY(.4);
  if (n === 1) { A.laugh(p); later(.5, subliminal); later(1.6, () => sub('...bebek güldü mü?', 2)); }
  if (n === 2 && n < need) { duck(1.1); later(1.1, () => screamer(true)); }
  if (n === need) { later(1, () => startStalker(16)); later(2, () => { if (!isMP() || NET.host) startHunt(14); }); }
}
// teslim (sigorta kutusu, arşiv, sunak)
function doDeliver(t, remote) {
  const st = S.tasks[t.id]; if (st.done) return;
  st.done = true;
  if (t.deliver === 'fusebox') { for (let i = 0; i < 3; i++) { fuseLights[i].fz.visible = i < needOf(t); fuseLights[i].lt.material = i < needOf(t) ? M.green : M.red; } A.slam(fuseBox.pos.clone().setY(1.4), .4); }
  if (t.deliver === 'archive') { A.slam(deliverPos('archive'), .5); A.metal(deliverPos('archive'), .2); }
  if (t.deliver === 'altar') { (t.id === 'doll' ? altarDolls : altarPages).forEach(d => d.visible = true); A.whisper(0, 2, .3); }
  if (!remote) { sub(`✔ ${t.label} — TAMAM`, 2.5); emitNoise(player.pos, 6); NET.send({ k: 'deliver', id: t.id }); }
  else sub(`✔ ${ROLES[t.role].name}: ${t.label}`, 2.5);
  afterTask();
}
// istasyon (vana, mum)
function doStation(stn, remote) {
  if (stn.done) return;
  stn.done = true;
  const t = chTasks().concat(Object.values(TASK_BY_ID)).find(t => t.station === stn.type), st = S.tasks[t.id];
  st.got++; if (st.got >= needOf(t)) st.done = true;
  if (stn.type === 'valve') { stn.spin = 1.4; A.creak(stn.pos, 1.4, .5, .4); A.metal(stn.pos, .35); if (!remote) emitNoise(player.pos, 13); }
  if (stn.type === 'candle') {
    stn.flame.visible = true; candleRoomLight.intensity = 1.2 * STATIONS.filter(s => s.type === 'candle' && s.done).length;
    if (!remote && st.got === 2) { A.laugh(stn.pos.clone().setY(1)); later(.8, () => { const p = spotAhead(3, 6); if (p) { actorRuns.push({ m: child, a: p.clone().add(new THREE.Vector3(2, 0, 0)), b: p.clone().add(new THREE.Vector3(-2, 0, 0)), t: 0, dur: 1, kind: 'child' }); A.sting(.5); } }); }
  }
  if (!remote) { sub(`${t.mk} (${st.got}/${needOf(t)})`, 2); NET.send({ k: 'station', id: stn.id }); }
  afterTask();
}
function afterTask() {
  updateTasks();
  if (isMP() && myTasksDone() && !chTasks().every(taskDone) && !S.helpNotified) { S.helpNotified = true; }
  if (isMP() && !NET.host) return;
  if (S.chapter === 1 && chTasks().every(taskDone) && !S.power) { later(1.2, () => { powerOn(); NET.send({ k: 'power' }); }); }
  saveCheckpoint();
}

/* ============================ ÇOK OYUNCULU ============================ */
const KOR_WS = (() => { try { const q = new URLSearchParams(location.search).get('server'); if (q && /^wss?:\/\//.test(q)) return q; if (/onrender\.com$/i.test(location.host)) return (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/kor/ws'; } catch (e) {} return 'wss://kasma-arena-server-wir3.onrender.com/kor/ws'; })();  // Render'daki sunucunun asıl adresi
const KOR_HTTP = KOR_WS.replace(/^ws/, 'http').replace('/kor/ws', '');
function mkRemote(id, name) {
  return { id, name, roles: [], pos: new THREE.Vector3(cc(3), 0, cc(3)), tpos: new THREE.Vector3(cc(3), 0, cc(3)), yaw: 0, tyaw: 0, pitch: 0, crouch: 0, flash: 1, down: 0, hid: 0, run: 0, inv: 0, seen: false, avatar: null, light: null, stepT: 0, last: 0 };
}
function assignRoles(ids) {
  ids = ids.slice().sort((a, b) => a - b); const r = {};
  if (ids.length === 1) r[ids[0]] = [0, 1, 2];
  else if (ids.length === 2) { r[ids[0]] = [0, 2]; r[ids[1]] = [1]; }
  else ids.forEach((id, i) => r[id] = [i % 3]);
  return r;
}
Object.assign(NET, {
  id: -1, code: '', players: new Map(), ws: null, sendT: 0, monT: 0, doorT: 0, pingT: 0,
  send(o) { if (this.ws && this.ws.readyState === 1) try { this.ws.send(JSON.stringify(o)); } catch (e) {} },
  remotes() { return [...this.players.values()].filter(p => p.id !== this.id); },
  nameOfRole(r) { for (const p of this.players.values()) if (p.roles.includes(r)) return p.id === this.id ? 'SEN' : p.name; return ROLES[r].name; },
  connect(create, code, name) {
    return new Promise((res, rej) => {
      const url = KOR_WS + '?name=' + encodeURIComponent(name) + (create ? '&create=1' : '&code=' + encodeURIComponent(code));
      let ws, opened = false;
      try { ws = new WebSocket(url); } catch (e) { rej('bağlanılamadı'); return; }
      this.ws = ws;
      const to = setTimeout(() => { if (!opened) { try { ws.close(); } catch (e) {} rej('sunucu cevap vermedi'); } }, 20000);
      ws.onmessage = ev => {
        let m; try { m = JSON.parse(ev.data); } catch (e) { return; }
        if (m.t === 'srv') {
          if (m.ev === 'hello') { opened = true; clearTimeout(to); this.on = true; this.id = m.id; this.code = m.code; this.host = m.host === m.id; this.roster(m.players); res(); }
          else if (m.ev === 'error') { clearTimeout(to); rej(m.why || 'hata'); }
          else if (m.ev === 'join' || m.ev === 'leave') {
            const who = this.players.get(m.id)?.name || '';
            this.roster(m.players);
            if (m.ev === 'leave') { this.host = m.host === this.id; if (this.started) feed(`<i>${who} oyundan ayrıldı</i>`); }
            else if (this.started) feed(`<i>${m.name} katıldı</i>`);
          }
          return;
        }
        if (m.f != null && m.d) this.recv(m.f, m.d);
      };
      ws.onclose = () => { clearTimeout(to); if (!opened) rej('bağlantı kurulamadı'); else this.closed(); };
      ws.onerror = () => {};
    });
  },
  roster(list) {
    const ids = new Set(list.map(p => p.id));
    for (const id of [...this.players.keys()]) if (!ids.has(id)) this.drop(id);
    for (const p of list) if (!this.players.has(p.id)) this.players.set(p.id, mkRemote(p.id, p.name));
    lobbyRender();
  },
  drop(id) { const p = this.players.get(id); if (!p) return; if (p.avatar) scene.remove(p.avatar); if (p.light) { p.light.intensity = 0; p.light.userData.used = false; } this.players.delete(id); },
  closed() {
    const was = this.started; this.on = false; this.started = false; this.ws = null;
    for (const id of [...this.players.keys()]) this.drop(id);
    if (was && (S.state === 'play' || S.state === 'chapter')) msg('<b style="color:#f66">Bağlantı koptu</b> — tek başına devam ediyorsun', 5);
    else { $('lbStatus').textContent = 'Bağlantı kapandı.'; $('lbRoom').style.display = 'none'; $('lbPre').style.display = 'block'; }
  },
  leave() { try { this.ws && this.ws.close(); } catch (e) {} this.ws = null; this.on = false; this.started = false; for (const id of [...this.players.keys()]) this.drop(id); },
  recv(from, d) {
    const p = this.players.get(from); if (!p) return;
    switch (d.k) {
      case 'p':
        p.tpos.set(d.x, 0, d.z); p.tyaw = d.y; p.pitch = d.pi; p.crouch = d.c; p.flash = d.fl; p.run = d.r; p.hid = d.h; p.down = d.dn; p.last = performance.now();
        if (!p.seen || p.tpos.distanceTo(p.pos) > 8) { p.pos.copy(p.tpos); p.yaw = p.tyaw; p.seen = true; }
        break;
      case 'm': if (!this.host) { mon.net = { x: d.x, z: d.z, dir: d.d }; mon.state = d.s; mon.rage = !!d.r; } break;
      case 'noise': if (this.host) emitNoise(new THREE.Vector3(d.x, 0, d.z), d.l, !!d.p, 'net'); break;
      case 'take': {
        const it = items[d.i]; if (!it || it.taken) break;
        it.taken = true; it.mesh.visible = false;
        if (it.task) takeTaskItem(it, true);
        if (it.type === 'card') teamCard(p);
        if (it.type === 'codenote') { S.codeKnown = true; sub(`${p.name} şifreyi buldu: ${S.code}`, 4); updateTasks(); }
        break;
      }
      case 'door': { const dr = doors[d.i]; if (dr) { dr.target = d.t; dr.swing = d.s; dr.speed = d.sp; dr.localT = performance.now(); } break; }
      case 'doors': if (!this.host) d.t.forEach((t, i) => { const dr = doors[i]; if (dr && performance.now() - (dr.localT || 0) > 2500) dr.target = t; }); break;
      case 'deliver': doDeliver(TASK_BY_ID[d.id], true); break;
      case 'station': doStation(STATIONS[d.id], true); break;
      case 'power': if (!S.power) powerOn(); break;
      case 'chapter': if (S.chapter !== d.n) startChapter(d.n); break;
      case 'ritual': ritual(); break;
      case 'safe': if (!S.safeOpen) { S.safeOpen = true; safeDoor.userData.led.material = M.green; A.metal(SAFE_POS, .3); refreshItemVisibility(); sub(`${p.name} kasayı açtı!`, 3); } break;
      case 'hunt': startHunt(d.d || 18); break;
      case 'caught': if (d.id === this.id && !S.down) killPlayer(deathTip()); break;
      case 'revive': if (d.id === this.id && S.down) revived(p.name); break;
      case 'ping': addPing(p, new THREE.Vector3(d.x, d.y, d.z)); break;
      case 'chat': chatShow(p, d.m); break;
      case 'start': beginMP(d); break;
      case 'win': if (S.state !== 'win') win(true); break;
    }
  },
  tick(dt) {
    this.pingT -= dt; if (this.pingT <= 0) { this.pingT = 20; try { this.ws && this.ws.readyState === 1 && this.ws.send('ping'); } catch (e) {} }
    if (!this.started) return;
    this.sendT -= dt;
    if (this.sendT <= 0) {
      this.sendT = 1 / 15;
      this.send({ k: 'p', x: +player.pos.x.toFixed(2), z: +player.pos.z.toFixed(2), y: +player.yaw.toFixed(3), pi: +player.pitch.toFixed(2), c: S.crouch ? 1 : 0, fl: S.flashOn && !(S.flashForcedOff > 0) ? 1 : 0, r: S.running ? 1 : 0, h: S.hidden ? 1 : 0, dn: S.down || S.state === 'jumpscare' ? 1 : 0 });
    }
    if (this.host) {
      this.monT -= dt; if (this.monT <= 0) { this.monT = 1 / 12; this.send({ k: 'm', x: +mon.pos.x.toFixed(2), z: +mon.pos.z.toFixed(2), d: +mon.dir.toFixed(2), s: mon.state, r: mon.rage ? 1 : 0 }); }
      this.doorT -= dt; if (this.doorT <= 0) { this.doorT = 2; this.send({ k: 'doors', t: doors.map(d => d.target > .5 ? 1 : 0) }); }
    }
    updateRemotes(dt);
  },
});
function sendDoor(d) { d.localT = performance.now(); NET.send({ k: 'door', i: doors.indexOf(d), t: d.target, s: d.swing, sp: d.speed }); }

// --- diğer oyuncuların 3B görünüşü
const REMOTE_LIGHTS = [];
for (let i = 0; i < 2; i++) { const sl = new THREE.SpotLight(0xfff1d6, 0, 24, .55, .6, 1.4); scene.add(sl); scene.add(sl.target); REMOTE_LIGHTS.push(sl); }
function nameTag(text, css) {
  const c = makeCanvas(256, 64), x = c.getContext('2d');
  x.font = 'bold 28px "Special Elite", monospace'; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.fillStyle = 'rgba(0,0,0,.55)'; x.fillRect(0, 8, 256, 48); x.fillStyle = css; x.fillText(text, 128, 33);
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false, fog: false }));
  sp.scale.set(1.1, .275, 1); return sp;
}
function makeAvatar(p) {
  const role = p.roles[0] ?? 0;
  const jacket = new THREE.MeshStandardMaterial({ color: ROLES[role].color, roughness: .8 }), skinM = new THREE.MeshStandardMaterial({ color: 0xd2ad92, roughness: .7 }), pants = new THREE.MeshStandardMaterial({ color: 0x23262b, roughness: .9 });
  const g = new THREE.Group(), body = new THREE.Group(); g.add(body);
  const torso = box(.44, .62, .26, jacket); torso.position.y = 1.2; body.add(torso);
  const hips = box(.38, .2, .24, pants); hips.position.y = .84; body.add(hips);
  const head = new THREE.Mesh(new THREE.SphereGeometry(.13, 12, 10), skinM); head.scale.set(1, 1.15, 1.05); head.position.y = 1.7; body.add(head);
  const hair = new THREE.Mesh(new THREE.SphereGeometry(.14, 10, 8, 0, Math.PI * 2, 0, Math.PI / 2), M.dark); hair.position.y = 1.72; body.add(hair);
  const limbs = {};
  for (const s of [-1, 1]) {
    const arm = new THREE.Group(); arm.position.set(s * .29, 1.47, 0); body.add(arm);
    const ua = box(.11, .34, .11, jacket); ua.position.y = -.17; arm.add(ua);
    const fa = box(.09, .3, .09, skinM); fa.position.y = -.48; arm.add(fa);
    const leg = new THREE.Group(); leg.position.set(s * .11, .78, 0); body.add(leg);
    const ul = box(.15, .42, .15, pants); ul.position.y = -.21; leg.add(ul);
    const sh = box(.13, .36, .16, M.dark); sh.position.y = -.58; leg.add(sh);
    limbs[s < 0 ? 'la' : 'ra'] = arm; limbs[s < 0 ? 'll' : 'rl'] = leg;
  }
  const torch = cyl(.025, .03, .2, M.metal, 8); torch.rotation.x = Math.PI / 2; torch.position.set(0, -.62, .08); limbs.ra.add(torch);
  const tag = nameTag(`${p.name} · ${ROLES[role].name}`, ROLES[role].css); tag.position.y = 2.15; g.add(tag);
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  g.userData = { body, limbs, head, tag };
  scene.add(g); p.avatar = g;
  const sl = REMOTE_LIGHTS.find(l => !l.userData.used); if (sl) { sl.userData.used = true; p.light = sl; }
}
function updateRemotes(dt) {
  for (const r of NET.remotes()) {
    if (!r.avatar) continue;
    const before = r.pos.clone();
    r.pos.lerp(r.tpos, Math.min(1, dt * 10));
    let da = r.tyaw - r.yaw; while (da > Math.PI) da -= Math.PI * 2; while (da < -Math.PI) da += Math.PI * 2; r.yaw += da * Math.min(1, dt * 10);
    if (r.inv > 0) r.inv -= dt;
    const sp = before.distanceTo(r.pos) / Math.max(dt, 1e-3);
    const av = r.avatar, u = av.userData;
    av.visible = !r.hid;
    av.position.copy(r.pos); av.rotation.order = 'YXZ'; av.rotation.y = r.yaw + Math.PI;
    if (r.down) { av.rotation.x = -Math.PI / 2; av.position.y = .18; u.tag.position.set(0, .6, -1.6); }
    else { av.rotation.x = 0; av.position.y = 0; u.tag.position.set(0, 2.15, 0); }
    av.scale.y = r.crouch && !r.down ? .72 : 1;
    r.ph = (r.ph || 0) + dt * sp * 3.2;
    const sw = Math.sin(r.ph) * Math.min(1, sp / 2.5);
    u.limbs.ll.rotation.x = sw * .7; u.limbs.rl.rotation.x = -sw * .7; u.limbs.la.rotation.x = -sw * .5; u.limbs.ra.rotation.x = -1.1 + r.pitch * .6;
    // fener
    if (r.light) {
      const fx = -Math.sin(r.yaw), fz = -Math.cos(r.yaw);
      r.light.position.set(r.pos.x + fx * .35, (r.crouch ? 1.05 : 1.5), r.pos.z + fz * .35);
      r.light.target.position.set(r.pos.x + fx * 6, 1.4 + Math.sin(r.pitch) * 6, r.pos.z + fz * 6);
      r.light.intensity = r.flash && !r.hid && !r.down ? 45 : 0;
    }
    // ayak sesleri
    if (sp > .5 && !r.crouch && !r.down) { r.stepT -= dt * sp; if (r.stepT <= 0) { r.stepT = r.run ? 2.1 : 1.5; A.step(r.run ? .5 : .25, r.pos.clone().setY(.1), false, 1); } }
  }
}
// --- diğerlerinde yaratık: ev sahibinden gelen konuma kayar
function monsterPuppet(dt) {
  monster.visible = true;
  if (mon.net) {
    const dx = mon.net.x - mon.pos.x, dz = mon.net.z - mon.pos.z, d = Math.hypot(dx, dz);
    if (d > 6) mon.pos.set(mon.net.x, 0, mon.net.z); else { const k = Math.min(1, dt * 10); mon.pos.x += dx * k; mon.pos.z += dz * k; }
    let da = mon.net.dir - mon.dir; while (da > Math.PI) da -= Math.PI * 2; while (da < -Math.PI) da += Math.PI * 2; mon.dir += da * Math.min(1, dt * 10);
  }
  const spd = mon.lastPos.distanceTo(mon.pos) / Math.max(dt, 1e-3); mon.lastPos.copy(mon.pos);
  monsterFx(dt, spd > .3 ? Math.min(spd, 5.5) : 0);
}
// --- yere düşme ve kaldırma
function goDown() {
  S.down = true; S.downT = 25; S.hidden = null; $('lockerView').style.opacity = 0;
  $('downView').style.display = 'flex'; $('hud').style.display = 'block'; if (isTouch) $('touch').style.display = 'block';
  A.gasp(.5);
}
function updateDown(dt) {
  if (!S.down) return;
  S.downT -= dt;
  const alone = !NET.remotes().some(r => !r.down);
  $('downText').innerHTML = alone ? `Herkes yerde... ${Math.ceil(S.downT)} sn sonra başlangıç odasında uyanacaksın` : `Arkadaşların seni kaldırabilir (yanına gelip <b>E</b> basılı tutsunlar)<br>${Math.ceil(S.downT)} sn sonra başlangıç odasında uyanırsın`;
  player.h = lerp(player.h, .3, dt * 4);
  if (S.downT <= 0) { revived(null); player.pos.set(cc(3) + rand(-.6, .6), 0, cc(3) + rand(-.6, .6)); player.yaw = Math.PI; sub('Başlangıç odasında uyandın...', 3); }
}
function revived(by) {
  S.down = false; S.invT = 4; $('downView').style.display = 'none';
  if (by) { sub(`${by} seni kaldırdı!`, 3); A.gasp(.4); }
}
// --- işaret (ping) ve hızlı mesajlar
const pings = [];
function addPing(p, pos) {
  const el = document.createElement('div'); el.className = 'pg';
  const css = p ? ROLES[p.roles[0] ?? 0].css : '#fff'; el.style.color = css;
  el.innerHTML = `<i></i>${p ? p.name : 'SEN'}`; $('pings').appendChild(el);
  pings.push({ el, pos, t: 7 }); A.chime();
}
function pingForward() {
  const dir = camera.getWorldDirection(new THREE.Vector3()), o = camera.position.clone();
  let p = o.clone();
  for (let d = .5; d < 25; d += .25) {
    p = o.clone().addScaledVector(dir, d);
    if (p.y < .05 || p.y > WALL_H - .05 || !passable(toCell(p.x), toCell(p.z))) { p = o.clone().addScaledVector(dir, d - .3); break; }
  }
  addPing(null, p); NET.send({ k: 'ping', x: +p.x.toFixed(2), y: +p.y.toFixed(2), z: +p.z.toFixed(2) });
}
function updatePings(dt) {
  for (let i = pings.length - 1; i >= 0; i--) {
    const pg = pings[i]; pg.t -= dt;
    if (pg.t <= 0) { pg.el.remove(); pings.splice(i, 1); continue; }
    const v = pg.pos.clone().project(camera), vis = v.z < 1 && Math.abs(v.x) < 1.1 && Math.abs(v.y) < 1.1;
    pg.el.style.display = vis ? 'block' : 'none';
    pg.el.style.left = ((v.x * .5 + .5) * innerWidth) + 'px'; pg.el.style.top = ((-v.y * .5 + .5) * innerHeight) + 'px';
    pg.el.style.opacity = Math.min(1, pg.t);
  }
}
const QUICK = ['Buraya gel!', 'KAÇ! Arkanda!', 'Yardım et!', 'Tamam 👍'];
function feed(html) { const el = document.createElement('div'); el.innerHTML = html; $('feed').appendChild(el); setTimeout(() => { el.style.opacity = 0; setTimeout(() => el.remove(), 1000); }, 6000); while ($('feed').children.length > 6) $('feed').firstChild.remove(); }
function chatShow(p, m) { const txt = QUICK[m] || ''; if (!txt) return; feed(`<b style="color:${p ? ROLES[p.roles[0] ?? 0].css : '#fff'}">${p ? p.name : 'Sen'}:</b> ${txt}`); A.pickup(); }
function sendChat(i) { chatShow(null, i); NET.send({ k: 'chat', m: i }); }
// --- kart takımındır
function teamCard(p) {
  S.keycard = true; mon.rage = true; updateTasks();
  sub(`${p ? p.name : 'Biri'} KARTI ALDI! ÇIKIŞA KOŞUN!`, 4); A.sting(.7);
  if (NET.host) cardChase();
}
function cardChase() {
  later(2.2, () => {
    const c = floorCells.filter(([x, z]) => { const d = Math.hypot(cc(x) - player.pos.x, cc(z) - player.pos.z); return d > 11 && d < 17; });
    if (c.length) { const q = pick(c); mon.pos.set(cc(q[0]), 0, cc(q[1])); }
    A.screech(mon.pos.clone().setY(2), 1.5, 1.2); mon.state = 'chase'; mon.trackT = 6; monSetTarget(player.pos.x, player.pos.z);
  });
}
// --- oyunu başlat (ev sahibi herkese yollar)
function beginMP(d) {
  NET.started = true; diff = d.diff ?? diff;
  for (const p of NET.players.values()) p.roles = (d.roles[p.id] || []).map(Number);
  NET.myRoles = NET.players.get(NET.id).roles;
  A.init(); if (A.ctx.state === 'suspended') A.ctx.resume();
  if (!droneGain) { startAmbience(); startWeather(); lampBuzz(); }
  newGame(d.seed);
  const k = [...NET.players.keys()].sort().indexOf(NET.id);
  player.pos.set(cc(3) + (k - 1) * .8, 0, cc(3) + (k === 1 ? -.6 : .3));
  for (const r of NET.remotes()) { if (!r.avatar) makeAvatar(r); r.pos.set(cc(3), 0, cc(3)); r.tpos.copy(r.pos); r.seen = false; }
  const mine = NET.myRoles.map(r => ROLES[r].name).join(' + ');
  const tasks = TASKDEF[1].filter(t => NET.myRoles.includes(t.role)).map(t => '• ' + t.label).join('\n');
  showIntro([
    `Kasım, 1987. Aziz Lazar Sanatoryumu.\n${NET.players.size} kişisiniz.\nVe içeride bir şey var.`,
    `Senin rolün: ${mine}\n\nİlk görevlerin:\n${tasks}`,
    'Görevlerini bitirince arkadaşlarına yardım et.\nYaratık birini yakalarsa yere düşer:\nyanına gidip E basılı tutarak kaldırın.\n\nT: işaret koy · 1-4: hızlı mesaj · V: kamera',
  ]);
}
// --- lobi ekranı
function lobbyRender() {
  const list = $('lbList'); if (!list) return;
  const ids = [...NET.players.keys()].sort(), roles = assignRoles(ids);
  list.innerHTML = ids.map(id => { const p = NET.players.get(id), r = roles[id] || []; return `<div><span style="color:${ROLES[r[0] ?? 0].css}">●</span> <b>${p.name}</b>${id === NET.id ? ' (sen)' : ''} — ${r.map(x => ROLES[x].name).join(' + ')}</div>`; }).join('') + (ids.length < 3 ? `<div style="opacity:.5">... ${3 - ids.length} kişi daha katılabilir</div>` : '');
  $('lbStartRow').style.display = NET.host ? 'block' : 'none';
  if (!NET.host && NET.on) $('lbStatus').textContent = 'Oda sahibinin oyunu başlatması bekleniyor...';
}
async function lobbyConnect(create) {
  const name = ($('lbName').value || '').trim() || 'Oyuncu'; store.set('name', name);
  const code = ($('lbCode').value || '').trim().toUpperCase();
  if (!create && code.length !== 5) { $('lbStatus').textContent = 'Oda kodu 5 karakter.'; return; }
  A.init(); if (A.ctx.state === 'suspended') A.ctx.resume();
  $('lbStatus').textContent = 'Sunucuya bağlanılıyor... (sunucu uyuyorsa 30-60 sn sürebilir)';
  try { await fetch(KOR_HTTP + '/health', { mode: 'no-cors', cache: 'no-store' }); } catch (e) {}
  let err = '';
  for (let i = 0; i < 3; i++) { try { await NET.connect(create, code, name); err = ''; break; } catch (e) { err = String(e); if (/bulunamadı|dolu|başladı|5 karakter/.test(err)) break; await new Promise(r => setTimeout(r, 2500)); } }
  if (err) { $('lbStatus').textContent = 'Olmadı: ' + err + (location.protocol === 'https:' && /claude/.test(location.host) ? ' (Bu sayfada çok oyunculu çalışmaz; EXE veya kor.html ile oyna.)' : ''); return; }
  $('lbPre').style.display = 'none'; $('lbRoom').style.display = 'block'; $('lbCodeBig').textContent = NET.code;
  $('lbStatus').textContent = NET.host ? 'Arkadaşların katılınca OYUNU BAŞLAT\'a bas (tek başına da başlatabilirsin).' : '';
  lobbyRender();
}
$('bCoop').onclick = () => { show('lobby'); $('lbName').value = store.get('name', ''); $('lbPre').style.display = 'block'; $('lbRoom').style.display = 'none'; $('lbStatus').textContent = ''; };
$('lbCreate').onclick = () => lobbyConnect(true);
$('lbJoin').onclick = () => lobbyConnect(false);
$('lbBack').onclick = () => { NET.leave(); show('title'); };
$('lbStart').onclick = () => {
  if (!NET.host) return;
  const d = { k: 'start', seed: (Math.random() * 1e9) | 0, diff, roles: assignRoles([...NET.players.keys()]) };
  NET.send(d); beginMP(d);
};
// --- gece görüş kamerası
let nvGhost = null, nvGhostCd = 0;
function setNV(on) {
  S.nv = on; $('nvHud').style.display = on ? 'block' : 'none';
  const t = A.t, o = A.ctx.createOscillator(); o.frequency.value = on ? 1800 : 900; const g = A.ctx.createGain(); A.env(g, t, .002, .05, .08); o.connect(g); g.connect(A.master); o.start(t); o.stop(t + .1);
  if (on && nvGhostCd <= 0 && Math.random() < .4) {
    const p = spotAhead(4, 9);
    if (p) { if (!nvGhost) { nvGhost = humanoid(new THREE.MeshBasicMaterial({ color: 0xeeeeee, transparent: true, opacity: .85 }), 1.05); scene.add(nvGhost); } nvGhost.position.copy(p); nvGhost.rotation.y = Math.atan2(player.pos.x - p.x, player.pos.z - p.z); nvGhost.userData.head.rotation.z = .7; nvGhost.userData.look = 0; nvGhost.userData.rush = 0; nvGhost.userData.live = true; nvGhostCd = 30; }
  }
  if (!on && nvGhost) nvGhost.userData.live = false;
}
function toggleNV() { if (S.nv) { setNV(false); return; } if ((S.nvBatt ?? 1) < .2) { sub('Kameranın şarjı az... bekle', 2); A.flashClick(); return; } setNV(true); }
function updateNV(dt) {
  nvGhostCd -= dt;
  if (S.nv) { S.nvBatt = Math.max(0, (S.nvBatt ?? 1) - dt / 5); if (S.nvBatt <= 0) { setNV(false); sub('Kamera kapandı — şarj oluyor (20 sn)', 2.5); } }
  else S.nvBatt = Math.min(1, (S.nvBatt ?? 1) + dt / 20);
  $('nvBar').style.width = (S.nvBatt * 100) + '%';
  ambient.intensity = S.nv ? 6 : .75; hemi.intensity = S.nv ? 2.2 : .25;
  if (nvGhost) {
    const u = nvGhost.userData; nvGhost.visible = !!(S.nv && u.live);
    if (nvGhost.visible) {
      const to = nvGhost.position.clone().setY(1.5).sub(camera.position), d = to.length(); to.normalize();
      if (!u.rush && to.dot(camera.getWorldDirection(_v2)) > .95) { u.look += dt; if (u.look > .5) { u.rush = .3; A.hit(1); A.screech(null, .7, 1); shake(.7); S.glitch = 1; } }
      if (u.rush) { u.rush -= dt; nvGhost.position.lerp(new THREE.Vector3(player.pos.x, 0, player.pos.z), Math.min(1, dt * 9)); if (u.rush <= 0) u.live = false; }
    }
  }
}

/* ============================ ANA DÖNGÜ ============================== */
let last = performance.now(), heartT = 0, breathT = 0, ambT = 20;

function updateLamps(dt) {
  if (candleLight) candleLight.intensity = S.candlesOut ? 0 : 1.2 + Math.sin(performance.now() * .013) * .25 + Math.random() * .2;
  for (const L of lamps) {
    L.t += dt;
    let I = 0;
    if (L.mode === 'flicker') {
      const n = Math.sin(L.t * 23) * Math.sin(L.t * 7.3) + Math.sin(L.t * 1.3);
      I = n > -.2 ? L.base : (Math.random() < .5 ? L.base * .2 : 0);
      if (Math.random() < .01) I = 0;
    } else if (L.mode === 'alarm') I = L.base * (.55 + .45 * Math.sin(L.t * 5));
    else if (L.mode === 'dead') I = Math.random() < .03 ? L.base * .8 : 0;
    if (S.flickerT > 0) I *= Math.random() < .5 ? 0 : 1.2;
    if (S.blackT > 0) I = 0;
    if (!L.on && L.mode !== 'flicker' && L.mode !== 'dead') I = 0;
    if (L.broken) I = 0;
    L.light.intensity = I;
    L.tube.material = I > .5 ? M.lampOn : M.lampOff;
    if (L.mode === 'alarm' && I > .5) L.tube.material = M.red;
    // performans: uzak ışıkları kapat
  }
  // ışık havuzu: oyuncunun katındaki en yakın yanık lambalar
  const pf = floorOfX(camera.position.x);
  const cand = lamps.filter(L => L.light.intensity > .05 && floorOfX(L.light.position.x) === pf)
    .sort((a, b) => a.light.position.distanceToSquared(camera.position) - b.light.position.distanceToSquared(camera.position));
  LIGHT_POOL.forEach((pl, i) => { const L = cand[i]; if (L) { pl.position.copy(L.light.position); pl.color.copy(L.light.color); pl.intensity = L.light.intensity; pl.distance = L.light.distance; } else pl.intensity = 0; });
}
function updateDoors(dt) {
  for (const d of doors) {
    const sp = d.speed || 2.6;
    d.open += clamp(d.target - d.open, -dt * sp, dt * sp);
    d.pivot.rotation.y = d.baseRot + d.open * 1.6 * (d.swing || 1);
  }
  for (const L of lockers) {
    L.open += clamp(L.target - L.open, -dt * 6, dt * 6);
    L.doorPivot.rotation.y = -L.open * 1.4;
  }
}
function updateScares(dt) {
  const pcx = toCell(player.pos.x), pcz = toCell(player.pos.z);
  S.visited.add(pcz * GW + pcx);
  const fwd = camera.getWorldDirection(_v2);
  for (const [name, sc] of Object.entries(scares)) {
    if (S.triggered.has(name) || S.state !== 'play' || S.hidden) continue;
    if (!sc.cell.some(([x, z]) => x === pcx && z === pcz)) continue;
    if (sc.look) {
      const dx = sc.look[0] - player.pos.x, dz = sc.look[1] - player.pos.z, l = Math.hypot(dx, dz);
      if ((dx * fwd.x + dz * fwd.z) / l < .8) continue;
    }
    S.triggered.add(name); sc.fire();
  }
  // sürünen şey koşusu
  const cr = crawler.userData.run;
  if (cr) {
    cr.t += dt;
    const x = lerp(cr.x0, cr.x1, cr.t / 1.6);
    crawler.position.set(x, -.75, cr.z); crawler.rotation.set(0, Math.PI / 2, 0);
    const u = crawler.userData; u.spine.rotation.x = 1.45; u.neck.rotation.x = -1.3;
    u.legs.forEach(l => { l.hip.rotation.x = Math.sin(cr.t * 30 + l.s) * 1 - .8; });
    u.arms.forEach(a => { a.sh.rotation.x = -1.5 + Math.sin(cr.t * 30 + a.s * 2) * .8; });
    u.head.rotation.y = Math.sin(cr.t * 40) * .5;
    if (cr.t > 1.6) { crawler.visible = false; crawler.userData.run = null; }
  }
  // asılı ceset düşüşü
  const hd = hangBody.userData.drop;
  if (hd) {
    hd.t += dt;
    const fall = Math.min(1, hd.t / .22);
    hangBody.position.y = lerp(WALL_H + 1.4, .55, fall * fall);
    hangBody.userData.rope.position.y = (WALL_H - hangBody.position.y) / 2 + 1.75;
    hangBody.userData.rope.scale.y = Math.max(.1, (WALL_H - hangBody.position.y - 1.75) / 3 + .01);
    hangBody.rotation.z = Math.sin(hd.t * 2.2) * .25 * Math.exp(-hd.t * .25);
    hangBody.rotation.y += dt * .3;
    hangBody.userData.limbs.la.rotation.z = -.2; hangBody.userData.limbs.ra.rotation.z = .2;
    hangBody.userData.head.rotation.z = .9;
    if (hd.t > 40) { hangBody.visible = false; hangBody.userData.drop = null; }
  }
  // dolap cesedi düşüşü
  if (lockerCorpse.fall != null) {
    lockerCorpse.fall = Math.min(1, lockerCorpse.fall + dt * 2.4);
    const b = lockerCorpse.body, f = lockerCorpse.fall;
    b.position.set(0, 0, .2 + f * .6); b.rotation.x = f * f * 1.45;
    b.userData.limbs.la.rotation.x = -f * 2; b.userData.limbs.ra.rotation.x = -f * 1.6; b.userData.head.rotation.x = .6;
  }
  // tekerlekli sandalye
  const wr = wchair.userData.roll;
  if (wr) {
    wr.t += dt;
    if (wr.t < 4) { const sp = Math.max(0, 1.1 - wr.t * .25); wchair.position.x -= sp * dt * Math.SQRT1_2; wchair.position.z -= sp * dt * Math.SQRT1_2; }
  }
  // mankenler: bakmıyorken sana döner ve yaklaşır
  for (const mq of mannequins) {
    const m = mq.m;
    const dx = m.position.x - player.pos.x, dz = m.position.z - player.pos.z, d = Math.hypot(dx, dz);
    const inView = (dx * fwd.x + dz * fwd.z) / d > .35 && d < 18 && lineClear(player.pos.x, player.pos.z, m.position.x, m.position.z) && (S.flashOn || d < 4);
    if (!inView && mq.seen && d < 14 && d > 2.6) {
      m.rotation.y = Math.atan2(-dx, -dz);
      // biraz yaklaş
      const step = Math.min(.9, d - 2.4);
      const nx = m.position.x - dx / d * step, nz = m.position.z - dz / d * step;
      if (passable(toCell(nx), toCell(nz)) && cellAt(toCell(nx), toCell(nz)) !== 'D') m.position.set(nx, 0, nz);
      m.userData.head.rotation.y = rand(-.6, .6); m.userData.limbs.ra.rotation.x = rand(-1.6, 0);
      mq.seen = false;
      if (d < 6 && Math.random() < .35) A.creak(m.position.clone().setY(1), .25, .08, 2.2);
    }
    if (inView) {
      if (!mq.seen && d < 5 && !mq.scared) { mq.scared = true; A.sting(.35); }
      mq.seen = true;
    }
  }
  // dolap kapısı / dekor zamanlayıcıları
  for (let i = events.length - 1; i >= 0; i--) if (S.time >= events[i].t) { const e = events[i]; events.splice(i, 1); e.fn(); }
  // rastgele ortam korkuları
  ambT -= dt;
  if (ambT <= 0) {
    ambT = rand(22, 55);
    const r = Math.random();
    if (r < .2) A.whisper(rand(-1, 1), rand(1.5, 3), .14);
    else if (r < .35) A.distantScream();
    else if (r < .5) A.rumble();
    else if (r < .65) { const d = pick(doors.filter(d => !d.locked && Math.hypot(cc(d.x) - player.pos.x, cc(d.z) - player.pos.z) < 16)); if (d) { d.target = d.target > .5 ? 0 : 1; d.swing = 1; A.creak(new THREE.Vector3(cc(d.x), 1.2, cc(d.z)), 2.2, .25, .7); } }
    else if (r < .75) flicker(rand(.5, 1.5));
    else if (r < .85) { const p = player.pos.clone().add(new THREE.Vector3(rand(-6, 6), 0, rand(-6, 6))); A.slam(p.setY(1), .5); }
    else A.laugh(player.pos.clone().add(new THREE.Vector3(rand(-8, 8), 1, rand(-8, 8))));
  }
}

function frame(now) {
  requestAnimationFrame(frame);
  const dt = Math.min(.05, (now - last) / 1000); last = now;
  const playing = S.state === 'play';
  if (NET.on) NET.tick(dt);
  if (S.state === 'chapter') {
    S.chapT -= dt;
    if (S.chapT < 1) $('chapter').style.opacity = 0;
    if (S.chapT <= 0) S.state = 'play';
  }
  if (playing || S.state === 'jumpscare') S.time += dt;

  if (playing) {
    const sp = movePlayer(dt);
    // nefes tutma
    const wantHold = keys.KeyQ || touch.breath;
    if (wantHold && S.breath > 0 && !S.gaspLock) { S.holdingBreath = true; S.breath = Math.max(0, S.breath - dt / 9); }
    else {
      if (S.holdingBreath && S.breath <= 0) { A.gasp(.6); emitNoise(player.pos, 8); S.gaspLock = true; sub('Nefesin kesildi!'); }
      S.holdingBreath = false; S.breath = Math.min(1, S.breath + dt / 5);
      if (S.breath > .4) S.gaspLock = false;
    }
    // nefes: yaratık çok yakınsa duyabilir
    breathT -= dt;
    const mdist = Math.hypot(player.pos.x - mon.pos.x, player.pos.z - mon.pos.z);
    if (breathT <= 0) {
      const heavy = S.stamina < .4 || S.fear > .5;
      breathT = heavy ? .9 : 2.2;
      if (!S.holdingBreath) {
        if (heavy || S.hidden) A.breath(heavy ? .12 : .05, true);
        if (mdist < 3.2 && !S.hidden) emitNoise(player.pos, heavy ? 4.5 : 2.2);
      }
    }
    // yaratık yakında: nefes ipucu
    S.hintCd = (S.hintCd || 0) - dt;
    if (mdist < 6.5 && mon.active && !S.holdingBreath && S.hintCd <= 0) { S.hintCd = 25; msg(isTouch ? 'Çok yakın... <b>NEFES TUT</b>' : 'Çok yakın... <b>[Q]</b> nefesini tut', 2.5); }
    // fener
    const forcedOff = S.flashForcedOff > 0;
    if (S.flashForcedOff > 0) S.flashForcedOff -= dt;
    if (S.flashOn) S.battery = Math.max(0, S.battery - dt / 200);
    if (S.battery <= 0 && S.flashOn) { S.flashOn = false; sub('Pil bitti...'); }
    let fI = S.flashOn && !forcedOff ? 60 : 0;
    if (S.battery < .15 && Math.random() < .08) fI *= Math.random();
    if (forcedOff && Math.random() < .05) fI = 30;
    flashlight.intensity = fI; fillLight.intensity = fI ? .9 : 0;
    // korku
    let fear = 0;
    if (mon.active) {
      fear = clamp(1 - mdist / 16, 0, 1);
      if (mon.state === 'chase') fear = Math.max(fear, .75);
      else if (mon.state === 'investigate') fear = Math.max(fear, .35 * clamp(1 - mdist / 25, 0, 1) + fear);
    }
    if (S.hunting > 0) fear = Math.max(fear, .5);
    if (S.fearKick > 0) { fear = Math.max(fear, S.fearKick); S.fearKick -= dt * .3; }
    if (S.hallu > 0) fear = Math.max(fear, .8 * S.hallu);
    S.fear = lerp(S.fear, clamp(fear, 0, 1), dt * 2);
    heartT -= dt;
    if (heartT <= 0 && S.fear > .15) { heartT = lerp(1.1, .38, S.fear); A.heart(.25 + S.fear * .6); }
    if (chaseGain) chaseGain.gain.setTargetAtTime(mon.state === 'chase' ? .13 : (S.hunting > 0 ? .06 : 0), A.t, mon.state === 'chase' ? .3 : 1.5);
    // ani sessizlik (korkudan hemen önce) -> sonra vuruş
    if (S.duckT > 0) S.duckT -= dt;
    const ducked = S.duckT > 0;
    if (droneGain) droneGain.gain.setTargetAtTime(ducked ? .004 : .12 + S.fear * .12, A.t, ducked ? .15 : 1);
    if (rainGain) rainGain.gain.setTargetAtTime(ducked ? .03 : (S.hidden ? .35 : .6), A.t, ducked ? .15 : 1.2);
    if (stringsGain) stringsGain.gain.setTargetAtTime(ducked ? 0 : clamp((S.fear - .25) * 1.4, 0, 1) * .5, A.t, .8);
    // ses ölçer
    S.noiseLevel = Math.max(0, S.noiseLevel - dt * 25);
    const nl = Math.min(1, S.noiseLevel / 16);
    meterBars.forEach((b, i) => { const on = i / meterBars.length < nl; b.style.height = (6 + i * .7) + 'px'; b.style.background = on ? (i > 14 ? '#ff2a2a' : i > 7 ? '#d8a040' : '#d8d2c4') : 'rgba(255,255,255,.12)'; });
    // etkileşim
    focus = findFocus();
    const held = keys.KeyE || eHeld || touch.use;
    interact(dt, ePressed, held);
    ePressed = false;
    const pr = $('prompt');
    if (focus) { pr.innerHTML = `<b>${isTouch ? 'KULLAN' : 'E'}</b>${focus.text}`; pr.style.opacity = 1; } else pr.style.opacity = 0;
    const hb = $('holdbar'); if (holdT > 0) { hb.style.display = 'block'; hb.firstChild.style.width = (holdT / (S.holdMax || 3) * 100) + '%'; } else hb.style.display = 'none';
    updateMonster(dt);
    updateScares(dt);
    updateThrown(dt);
    updateMarker();
    updateGuide(dt);
    updateHorror(dt);
    updateNV(dt); updateDown(dt); updatePings(dt); if (S.invT > 0) S.invT -= dt;
    ambientScares(dt); ghostDoors(dt); update3dScares(dt); updateWatchers(dt); updateHunt(dt); updateHallu(dt); updateFall(dt);
    doorScareCd -= dt;
    if (S.safeOpen && safeDoor.rotation.y > -1.7) safeDoor.rotation.y -= dt * 2.5;
    if (tutorT > 0) { tutorT -= dt; if (tutorT <= 0) $('tutor').style.opacity = 0; }
    if (S.bannerT > 0) { S.bannerT -= dt; if (S.bannerT <= 0) $('banner').style.opacity = 0; }
    // kamera sallanması
    player.bob += sp * dt * (S.running ? 2.6 : 2.2);
    const targetH = S.hidden ? 1.55 : (S.crouch ? 1.0 : 1.62);
    player.h = lerp(player.h, targetH, dt * 8);
    // HUD
    $('stamI').style.width = (S.stamina * 100) + '%'; $('stamI').style.background = S.exhausted ? '#a33' : '';
    $('battI').style.width = (S.battery * 100) + '%'; $('battI').style.background = S.battery < .2 ? '#a33' : '';
    $('breathI').style.width = (S.breath * 100) + '%'; $('breathBar').style.opacity = (S.holdingBreath || S.breath < 1) ? 1 : 0;
    $('vignette').style.opacity = .45;
    $('fearTint').style.opacity = S.holdingBreath ? .3 : 0;
    if (subT > 0) { subT -= dt; if (subT <= 0) $('sub').style.opacity = 0; }
    if (msgT > 0) { msgT -= dt; if (msgT <= 0) $('msg').style.opacity = 0; }
    if (S.flickerT > 0) S.flickerT -= dt;
    if (S.blackT > 0) S.blackT -= dt;
    if (S.stairT > 0) S.stairT -= dt;
    for (const st of STATIONS) if (st.spin > 0) { st.spin -= dt; st.wheel.rotation.z += dt * 7; }
  }

  // ölüm sahnesi: yaratık yüzüne atılır
  if (S.state === 'jumpscare') {
    S.jumpT += dt;
    const t = S.jumpT;
    const eye = new THREE.Vector3(player.pos.x, player.h, player.pos.z);
    // yaratığı oyuncunun önüne getir
    const toM = Math.atan2(mon.pos.x - player.pos.x, mon.pos.z - player.pos.z);
    if (t < dt * 1.5) player.yaw = toM + Math.PI;
    player.pitch = lerp(player.pitch, .02, Math.min(1, dt * 10));
    const dist = lerp(1.5, .6, Math.min(1, t * 4));
    const u = monster.userData;
    u.body.position.y = 0;
    u.spine.rotation.x = .75; u.neck.rotation.x = -.55; u.jaw.rotation.x = .85 + Math.sin(t * 50) * .12; spreadJaw(u);
    u.head.rotation.z = Math.sin(t * 37) * .25; u.head.rotation.y = Math.sin(t * 23) * .2;
    u.arms.forEach(a => { a.sh.rotation.x = -1.9; a.sh.rotation.z = a.s * .7; a.el.rotation.x = -.6; });
    monster.rotation.y = player.yaw;   // yüzü kameraya dönük
    monster.position.set(0, 0, 0);
    const fx = -Math.sin(player.yaw), fz = -Math.cos(player.yaw);
    placeHeadAt(monster, _v3.set(player.pos.x + fx * dist, player.h + .02, player.pos.z + fz * dist));
    mon.pos.copy(monster.position);
    monster.visible = true;
    flashlight.intensity = Math.random() < .25 ? 0 : 6; fillLight.intensity = .25;
    player.shake = 1;
    if (t < .05) redFlash(.45);
    if (t > 1.5 && isMP()) { S.state = 'play'; monster.visible = true; goDown(); if (!isTouch) canvas.requestPointerLock?.(); }
    else if (t > 1.5) {
      S.state = 'dead'; show('dead'); $('hud').style.display = 'none'; $('touch').style.display = 'none';
      $('deadTip').textContent = S.deathTip;
      $('blackout').style.opacity = 0;
    }
  }

  if (playing || S.state === 'jumpscare' || S.state === 'win' || S.state === 'chapter') {
    updateLamps(dt); updateDoors(dt); updateDirector(dt); updateShafts();
    if (S.state === 'win' && exitGate.opening) { exitGate.open = Math.min(1, exitGate.open + dt * .5); exitGate.l.position.x = -C / 4 - exitGate.open * C / 2; exitGate.r.position.x = C / 4 + exitGate.open * C / 2; }
    // kamera
    player.shake = Math.max(0, player.shake - dt * 1.6);
    const sh = player.shake * player.shake * .08;
    const bobY = Math.sin(player.bob * 2) * (S.running ? .06 : .03), bobX = Math.cos(player.bob) * (S.running ? .04 : .02);
    camera.position.set(player.pos.x + rand(-sh, sh), player.h + bobY + rand(-sh, sh), player.pos.z + rand(-sh, sh));
    camera.rotation.order = 'YXZ';
    const tt = now / 1000, sway = .004 + S.fear * .006;
    camera.rotation.set(player.pitch + rand(-sh, sh) * .5 + Math.sin(tt * .8) * sway, player.yaw + bobX * .1 + Math.sin(tt * .53) * sway * .8, bobX * .15 * (S.running ? 1 : .4) + Math.sin(tt * .37) * sway * .5);
    const targetFov = S.running ? 86 : (S.fear > .6 ? 72 : 78);
    camera.fov = lerp(camera.fov, targetFov, dt * 3); camera.updateProjectionMatrix();
    // toz
    dustPts.position.set(Math.floor(player.pos.x / 8) * 8, 0, Math.floor(player.pos.z / 8) * 8);
    const dp = dustGeo.attributes.position;
    for (let i = 0; i < DN; i++) {
      let y = dp.getY(i) - dt * (dustFall > 0 ? .9 : .03) + Math.sin(now * .001 + i) * .0015;
      if (y < 0) y = WALL_H;
      dp.setY(i, y);
      const wx = dustPts.position.x + dp.getX(i);
      if (Math.abs(wx - player.pos.x) > 8) dp.setX(i, player.pos.x - dustPts.position.x + rand(-4, 4));
      const wz = dustPts.position.z + dp.getZ(i);
      if (Math.abs(wz - player.pos.z) > 8) dp.setZ(i, player.pos.z - dustPts.position.z + rand(-4, 4));
    }
    dp.needsUpdate = true; dustFall = Math.max(0, dustFall - dt);
    $('blackout').style.opacity = S.blackT > 0 ? .97 : 0;
    A.updateListener(camera);
  } else if (S.state === 'title' || S.state === 'intro') {
    // menü arka planı: koridorda yavaş kamera
    const t = now / 1000;
    camera.position.set(cc(11) + Math.sin(t * .1) * .4, 1.6, cc(9) + Math.sin(t * .07) * 2);
    camera.rotation.set(-.05, Math.PI + Math.sin(t * .13) * .5, 0);
    flashlight.intensity = Math.random() < .02 ? 0 : 35;
    updateLamps(dt); updateShafts();
    if (S.state === 'title' && monster) {
      monster.visible = true; mon.anim += dt * 2; monster.position.set(cc(11), 0, cc(15) + Math.sin(t * .2) * 1.5); monster.rotation.y = Math.PI;
      animateMonster(monster, dt, 1.2, false, true);
    }
  }

  // son işleme
  filmPass.uniforms.uTime.value = now / 1000;
  filmPass.uniforms.uFear.value = S.state === 'play' ? S.fear : (S.state === 'jumpscare' ? .45 : 0);
  filmPass.uniforms.uHit.value = S.state === 'jumpscare' ? .12 : Math.max(0, player.shake - .3);
  filmPass.uniforms.uHallu.value = S.hallu || 0;
  filmPass.uniforms.uNV.value = S.nv && (S.state === 'play' || S.state === 'chapter') ? 1 : 0;
  filmPass.uniforms.uGlitch.value = Math.min(1.2, (S.glitch || 0) + (S.state === 'jumpscare' ? .12 : 0));
  composer.render();
}

// yazı tipleri yüklenince dünyayı kur (duvar yazıları ve tabelalar tuvale çiziliyor)
(async () => {
  try { await Promise.race([Promise.all([document.fonts.load('150px Creepster'), document.fonts.load('58px "Special Elite"')]), new Promise(r => setTimeout(r, 2500))]); } catch (e) {}
  buildWorld();
  buildExtras();
  buildAltar();
  lunger = buildMonster(); lunger.visible = false; scene.add(lunger);
  buildSafe();
  buildShafts();
  newGame();
  mon.pos.set(cc(11), 0, cc(15));
  applyQuality();
  requestAnimationFrame(frame);
})();
document.querySelectorAll('#qRow .btn').forEach(b => {
  b.classList.toggle('sel', +b.dataset.q === quality);
  b.onclick = () => { quality = +b.dataset.q; store.set('quality', quality); document.querySelectorAll('#qRow .btn').forEach(x => x.classList.toggle('sel', x === b)); applyQuality(); };
});
window.__kor = { STATIONS, TASK_BY_ID, useStairs, doStation, doDeliver, NET, startHunt, hallucinate, doorSurprise, spawnEyes, watchers, openKeypad, kpPress, scare3d, ghostDoors, autoDoors, startChapter, ritual, screamer, subliminal, startStalker, DIRECTOR, showGuide, objective, lightning, S, mon, player, scares, killPlayer, emitNoise, camera, A, items, doors, lockers, takeItem, powerOn, hide, unhide, interact, throwBottle, loadCheckpoint, faceJumpscare, monster, drawMap, get focus() { return focus; } };
