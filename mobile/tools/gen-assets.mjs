// Simge / açılış / mağaza görsellerini üretir.
// Kullanım: önce `npm run dev`, sonra:
//   PLAYWRIGHT=/yol/playwright/index.mjs node tools/gen-assets.mjs
// (Playwright projeye bağımlılık olarak eklenmedi; bir kez çalıştırılır,
// çıktılar depoya işlenir.)
import fs from "node:fs";
import path from "node:path";
const { chromium } = await import(process.env.PLAYWRIGHT || "playwright");
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const DEV_URL = process.env.DEV_URL || "http://127.0.0.1:5173/?icongen=1";

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(DEV_URL);
await page.waitForFunction(() => window.__genReady === true, null, { timeout: 60000 });

async function save(file, js) {
  const url = await page.evaluate(js);
  const buf = Buffer.from(url.split(",")[1], "base64");
  const out = path.join(ROOT, file);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, buf);
  console.log("✓", file);
}

// web / PWA
await save("public/icon-192.png", "__gen.icon(192)");
await save("public/icon-512.png", "__gen.icon(512)");
// mağaza
await save("store/play-icon-512.png", "__gen.icon(512)");
await save("store/app-store-icon-1024.png", "__gen.icon(1024)");
await save("store/play-feature-graphic-1024x500.png", "__gen.feature()");

// Android başlatıcı simgeleri
const RES = "android/app/src/main/res";
const dens = { mdpi: 1, hdpi: 1.5, xhdpi: 2, xxhdpi: 3, xxxhdpi: 4 };
for (const [d, k] of Object.entries(dens)) {
  const s = Math.round(48 * k), f = Math.round(108 * k);
  await save(`${RES}/mipmap-${d}/ic_launcher.png`, `__gen.icon(${s})`);
  await save(`${RES}/mipmap-${d}/ic_launcher_round.png`, `__gen.icon(${s}, {round: true})`);
  // uyarlanabilir simge: ön plan 108dp, güvenli bölge ortadaki 66dp
  await save(`${RES}/mipmap-${d}/ic_launcher_foreground.png`, `__gen.icon(${f}, {bg: false, scale: 0.62})`);
}
// Android açılış görselleri (Android 11 ve öncesi)
const splashes = {
  "drawable": [480, 320], "drawable-land-mdpi": [480, 320], "drawable-land-hdpi": [800, 480], "drawable-land-xhdpi": [1280, 720],
  "drawable-land-xxhdpi": [1600, 960], "drawable-land-xxxhdpi": [1920, 1280], "drawable-port-mdpi": [320, 480], "drawable-port-hdpi": [480, 800],
  "drawable-port-xhdpi": [720, 1280], "drawable-port-xxhdpi": [960, 1600], "drawable-port-xxxhdpi": [1280, 1920],
};
for (const [d, [w, h]] of Object.entries(splashes)) await save(`${RES}/${d}/splash.png`, `__gen.splash(${w}, ${h})`);

// iOS
const IOS = "ios/App/App/Assets.xcassets";
await save(`${IOS}/AppIcon.appiconset/AppIcon-512@2x.png`, "__gen.icon(1024)");
for (const n of ["splash-2732x2732.png", "splash-2732x2732-1.png", "splash-2732x2732-2.png"]) await save(`${IOS}/Splash.imageset/${n}`, "__gen.splash(2732, 2732)");

await browser.close();
