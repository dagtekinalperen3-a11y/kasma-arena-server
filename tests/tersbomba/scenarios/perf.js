'use strict';
// Performans ölçümü (çizim AÇIK). Sabit kamera noktaları: menü, oyun içi merkez, disko sırasında merkez.
// Her nokta için: çizim çağrısı, üçgen, gölgelendirici programı, ışık sayısı ve ortalama kare süresi.
// DİKKAT: bu ortamda WebGL yazılımsaldır (SwiftShader); süreler mutlak değil, yalnızca birbirine göre anlamlıdır.
//   TB_HTML=<başka html>   karşılaştırma için (ör. değişiklik öncesi kopya; __tb.renderer ve __tb.scene gerekir)
//   TB_Q=low,high  TB_W=640 TB_H=360  TB_FRAMES=8  TB_LABEL=ad → TB_OUT/perf-<ad>.json
//   TB_PERF_HIDE=round|hud|decor   darboğaz aramak için bir şeyi gizleyip ölçer
const fs = require('fs'), path = require('path');
const H = require('../harness');
const QS = (process.env.TB_Q || 'low,high').split(','), W = +(process.env.TB_W || 640), HH = +(process.env.TB_H || 360), N = +(process.env.TB_FRAMES || 8);
const LABEL = process.env.TB_LABEL || 'run', HIDE = process.env.TB_PERF_HIDE || '';

const measure = (c, n) => c.eval(n => new Promise(res => {
  const T = window.__tb, r = T.renderer; r.info.autoReset = false; r.info.reset();
  let i = -2, calls = 0, tris = 0, last = 0; const dts = [];
  const f = t => {
    if (i >= 0) { calls += r.info.render.calls; tris += r.info.render.triangles; if (i > 0) dts.push(t - last); }
    last = t; r.info.reset(); i++;
    if (i <= n) return requestAnimationFrame(f);
    dts.sort((a, b) => a - b);
    const L = { point: 0, spot: 0, dir: 0 }; T.scene.traverse(o => { if (o.isPointLight) L.point++; else if (o.isSpotLight) L.spot++; else if (o.isDirectionalLight) L.dir++; });
    res({ calls: Math.round(calls / (n + 1)), tris: Math.round(tris / (n + 1)), programs: r.info.programs.length, lights: `${L.point}n+${L.spot}s+${L.dir}y`, ms: +(dts.reduce((a, b) => a + b, 0) / dts.length).toFixed(1), med: +dts[dts.length >> 1].toFixed(1), geo: r.info.memory.geometries, tex: r.info.memory.textures });
  };
  requestAnimationFrame(f);
}), n);

H.run('perf', async t => {
  const infra = await H.startInfra(), browser = await H.launchBrowser(), out = { label: LABEL, html: H.HTML, size: `${W}x${HH}`, frames: N, hide: HIDE, q: {} };
  for (const q of QS) {
    t.step(`${q} · ${W}×${HH} · ${N} kare`);
    const c = await H.newClient(browser, infra, { name: 'Perf', quality: q, norender: false, viewport: { width: W, height: HH } });
    const R = out.q[q] = {};
    await c.tb(T => { if (T.settings) { T.settings.motion = false; T.settings.shake = 0; } });
    await t.sleep(800);
    R.menu = await measure(c, N); t.log('menü  ', JSON.stringify(R.menu));
    await H.soloRoom(c); await H.startGame(c, { diff: 'normal' });
    await c.tb(T => { T.game.chaosIn = 9999; T.game.timeLeft = 400; T.setRole('defuser'); document.querySelector('#pause').classList.add('hidden'); });
    await c.moveTo([0, 0, 6.5], { yaw: 0, pin: true }); await c.tb(T => { T.me.pitch = 0; });
    if (HIDE === 'round') await c.tb(T => { T.M.bomb.parent.visible = false; });
    if (HIDE === 'hud') await c.eval(() => { document.querySelector('#hud').style.display = 'none'; });
    await t.sleep(600);
    R.game = await measure(c, N); t.log('oyun  ', JSON.stringify(R.game));
    await c.tb(T => { T.game.chaos = { type: 'disko', left: 600, dur: 600, target: 'solo', seed: 1 }; });
    await c.waitFor(() => !document.querySelector('#chaos').classList.contains('hidden'), 60000);
    R.disco = await measure(c, N); t.log('disko ', JSON.stringify(R.disco));
    t.check(`${q}: sayfa hatası yok`, c.errors.length === 0, c.errors.join(' | '));
    await c.close();
  }
  fs.mkdirSync(H.OUT, { recursive: true });
  const f = path.join(H.OUT, `perf-${LABEL}.json`); fs.writeFileSync(f, JSON.stringify(out, null, 1)); t.log('yazıldı:', f);
  console.log('\n| kalite | nokta | çağrı | üçgen | program | ışık | ort. kare ms | ortanca ms |\n|---|---|---|---|---|---|---|---|');
  for (const q in out.q) for (const k in out.q[q]) { const m = out.q[q][k]; console.log(`| ${q} | ${k} | ${m.calls} | ${m.tris} | ${m.programs} | ${m.lights} | ${m.ms} | ${m.med} |`); }
}, { timeout: 3000000 });
