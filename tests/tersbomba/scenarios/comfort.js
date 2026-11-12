'use strict';
// Konfor ayarları: her seçenek kamera / efekt değişkenlerini değiştirir, bulmaca durumunu DEĞİŞTİRMEZ.
// 1) Tek istemci: ayarlar gerçek arayüzden (duraklatma penceresi) açılıp kapanır, __tb.cam / __tb.post okunur.
// 2) A/B: aynı tohumla kurulan iki antrenman odası, biri varsayılan biri "her şey sakin" ayarlarla;
//    aynı hamle dizisinden sonra bulmaca durumu birebir aynı olmalı.
const H = require('../harness'); require('../a-lib');

// başsız tarayıcıda gerçek fare kilidi yok: window.__lock ile taklit edilir (kilit kalkınca oyun duraklatma penceresini açar)
const FAKE_LOCK = () => Object.defineProperty(document, 'pointerLockElement', { configurable: true, get: () => (window.__lock ? document.querySelector('canvas') : null) });
const lock = (c, on) => c.eval(on => { window.__lock = on; document.dispatchEvent(new Event('pointerlockchange')); }, on);
// Math.random'ı sabit tohumla değiştirip AYNI görevde başlat düğmesine basar → iki sayfada aynı bulmaca
const SEEDED_START = seed => {
  let a = seed >>> 0;
  Math.random = () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  document.querySelector('#btnStart').click();
};
const LOGIC = T => { const g = T.game; return JSON.stringify({ puzzle: g.puzzle, status: g.status, strikes: g.strikes, solved: g.solved, wireCut: g.wireCut, keyProg: g.keyProg, keyPressed: g.keyPressed, pwIdx: g.pwIdx, fuse: g.fuse, ducksGot: g.ducksGot, mouseDial: g.mouseDial, mazeVisited: g.mazeVisited, mazeFails: g.mazeFails, laserProg: g.laserProg, final: !!g.final }); };
const frames = (c, n = 3) => c.eval(n => new Promise(r => { const f = () => (n-- > 0 ? requestAnimationFrame(f) : r()); f(); }), n);
// hamleyi yollar ve ~20 kare boyunca efekt değerlerinin en büyüğünü toplar
const probe = (c, msg) => c.eval(msg => new Promise(r => { const T = window.__tb; T.act(msg); let n = 20; const m = { vignette: 0, ab: 0, filmAb: 0 }; const f = () => { const p = T.post(); for (const k in m) m[k] = Math.max(m[k], p[k] || 0); n-- > 0 ? requestAnimationFrame(f) : r(m); }; f(); }), msg);
const toggle = async (c, key, want) => {
  const locked = await c.eval(() => !!window.__lock); if (locked) await lock(c, false);   // ESC'ye basılmış gibi: duraklatma penceresi açılır
  if ((await c.tb((T, k) => T.settings[k], key)) !== want) await c.eval(k => { const b = document.querySelector(`#pcSeg button[data-c="${k}"]`); if (document.querySelector("#pause").classList.contains("hidden") || !b.offsetWidth) throw new Error("duraklatma penceresi kapalı"); b.click(); }, key);
  if (locked) await lock(c, true);
  return c.tb((T, k) => T.settings[k], key);
};
const setShake = (c, v) => c.eval(v => { const el = document.querySelector('#pShake'); el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); }, v);
const forceChaos = (c, type) => c.tb((T, type) => { T.game.chaosIn = 9999; T.game.chaos = type ? { type, left: 30, dur: 30, target: 'solo', seed: 1 } : null; }, type);

async function soloGame(browser, infra, name, seed) {
  const c = await H.newClient(browser, infra, { name, quality: 'high', norender: true, initScripts: [FAKE_LOCK] });
  await H.soloRoom(c);
  await c.page.click('#diffSeg button[data-d="normal"]');
  await c.eval(SEEDED_START, seed);
  await c.waitFor(() => { const g = window.__tb.game; return !!g && g.countdown <= 0; }, 60000);
  await c.tb(T => { T.game.chaosIn = 9999; });
  return c;
}

H.run('comfort', async t => {
  const infra = await H.startInfra(), browser = await H.launchBrowser();

  // ------------------------------------------------------------------ 1) tek istemci
  t.step('varsayılanlar ve ayar pencereleri');
  const c = await H.newClient(browser, infra, { name: 'Konfor', quality: 'high', norender: true, initScripts: [FAKE_LOCK] });
  await c.page.click('#btnSet');
  t.eq('Ayarlar: konfor satırları var', await c.eval(() => [!!document.querySelector('#sShake'), [...document.querySelectorAll('#cSeg button')].map(b => b.dataset.c + ':' + b.classList.contains('on'))]), [true, ['motion:true', 'flash:true', 'plain:false']]);
  await c.page.click('#setModal [data-close]');
  t.eq('varsayılan ayarlar', await c.tb(T => [T.settings.shake, T.settings.motion, T.settings.flash, T.settings.plain]), [1, true, true, false]);
  const post0 = await c.tb(T => T.post());
  t.check('varsayılan efektler (parlama .42, kenar .42, kum .035, renk kayması .012)', post0.bloom === 0.42 && post0.vig === 0.42 && post0.grain === 0.035 && post0.ab0 === 0.012 && !post0.nofx && post0.flashShown, post0);

  t.step('antrenman turu (tohumlu bulmaca)');
  const c1 = await soloGame(browser, infra, 'Konfor2', 4242); await c.close();
  const logic0 = await c1.tb(LOGIC);
  await run1(t, c1, logic0);

  // ------------------------------------------------------------------ 2) A/B
  t.step('A/B: aynı tohum, farklı konfor ayarları, aynı hamleler');
  const A = await soloGame(browser, infra, 'A-varsayilan', 777), B = await soloGame(browser, infra, 'B-sakin', 777);
  await toggle(B, 'motion', false); await toggle(B, 'flash', false); await toggle(B, 'plain', true); await setShake(B, 0);
  t.check('başlangıç bulmacası birebir aynı', (await A.tb(LOGIC)) === (await B.tb(LOGIC)));
  const PZ = await A.puzzle();
  const script = async c => {
    const R = H.soloRoles(c);
    await forceChaos(c, 'bascasagi');
    await c.moveTo([-4, 0, -8.3], { pin: true }); await H.sleep(250);   // erişim denetimi: kablo panosunun yanında
    await R.defuser.act('cut', { i: [0, 1, 2, 3].find(i => i !== PZ.wireAns) });      // bilerek hata
    await H.sleep(150);
    for (const mod of PZ.mods) await H.solveModule(R, mod, PZ);
    await c.waitFor(() => !!window.__tb.game.final, 8000);
    await forceChaos(c, null);
  };
  await script(A); await script(B);
  const fa = await A.tb(LOGIC), fb = await B.tb(LOGIC);
  t.check('aynı hamlelerden sonra bulmaca durumu birebir aynı', fa === fb, fa === fb ? '' : { A: fa.slice(-400), B: fb.slice(-400) });
  const st = JSON.parse(fa);
  t.check('ikisinde de: 1 hata, tüm modüller çözüldü, final açıldı', st.strikes === 1 && Object.values(st.solved).every(Boolean) && st.final, st.solved);
  await H.toPlates([A, B]);
  t.check('ikisi de kazandı', await A.waitFor(() => window.__tb.game.status === 'won', 15000).catch(() => false) && await B.waitFor(() => window.__tb.game.status === 'won', 15000).catch(() => false));
  t.noErrors();
});

async function run1(t, c, logic0) {
  t.check('duraklatma penceresinde sarsıntı kaydırıcısı ve 3 anahtar var', await c.eval(() => !document.querySelector('#pause').classList.contains('hidden') && !!document.querySelector('#pShake') && document.querySelectorAll('#pcSeg button').length === 3));

  t.step('kamera hareketi: yürüme sallanması');
  await c.tb(T => T.setRole('reader'));
  await c.moveTo([6, 0, 8.5], { yaw: 0 });
  await lock(c, true);
  await c.page.keyboard.down('KeyW'); await t.sleep(500); await frames(c);
  const walked = await c.tb(T => ({ z: T.me.pos.z, bobPhase: T.me.bob }));
  t.check('W ile yüründü (sahte fare kilidi)', walked.z < 8.3 && walked.bobPhase > 0.5, walked);
  const sample = () => c.eval(() => new Promise(r => { let n = 20, mb = 0, mr = 0; const f = () => { mb = Math.max(mb, Math.abs(__tb.cam.bob)); mr = Math.max(mr, Math.abs(__tb.cam.rollTarget)); n-- > 0 ? requestAnimationFrame(f) : r({ bob: mb, roll: mr }); }; f(); }));
  let s = await sample();
  t.check('açıkken yürürken kamera sallanıyor', s.bob > 0.01, s);
  t.eq('Kamera hareketi kapatıldı', await toggle(c, 'motion', false), false);
  await c.moveTo([6, 0, 8.5], { yaw: 0 }); await frames(c, 2);
  const z1 = await c.tb(T => T.me.pos.z);
  s = await sample();
  const z2 = await c.tb(T => T.me.pos.z);
  t.check('kapalıyken sallanma tam 0', s.bob === 0, s);
  await c.page.keyboard.up('KeyW');
  t.check('kapalıyken de yürünüyor (konum ilerledi)', z2 < z1 - 0.2, { z1, z2 });

  t.step('kamera hareketi: süzülme salınımı');
  await c.tb(T => T.setRole('floater'));
  s = await sample();
  t.check('kapalıyken YERÇEKİMSİZ kamerası yatmıyor', s.roll === 0, s);
  await toggle(c, 'motion', true); await t.sleep(700);
  s = await sample();
  t.check('açıkken YERÇEKİMSİZ kamerası salınıyor', s.roll > 0.003 && s.roll <= 0.07, s);

  t.step('sarsıntı miktarı');
  await c.tb(T => T.setRole('reader'));
  await c.moveTo([6, 0, 8.5], { yaw: 0, pin: true });
  const amp = async v => { await setShake(c, v); await c.tb(T => T.setShake(1)); await frames(c, 2); return c.tb(T => ({ amp: T.cam.shakeAmp, left: T.cam.shake, set: T.settings.shake, dx: Math.abs(T.camera.position.x - T.me.pos.x) })); };
  const a100 = await amp(1), a50 = await amp(0.5), a0 = await amp(0);
  t.check('%100: sarsıntı genliği = kalan × 0.12', Math.abs(a100.amp / a100.left - 0.12) < 1e-6 && a100.dx > 0, a100);
  t.check('%50: genlik yarısı', Math.abs(a50.amp / a50.left - 0.06) < 1e-6 && a50.set === 0.5, a50);
  t.check('%0: genlik 0 ve kamera hiç oynamıyor', a0.amp === 0 && a0.dx < 1e-9, a0);
  await setShake(c, 1); await c.tb(T => T.setShake(0)); await c.unpin();

  t.step('BAŞ AŞAĞI kaosu: kamera dönüşü isteğe bağlı, fare her durumda ters');
  await forceChaos(c, 'bascasagi');
  await c.waitFor(() => window.__tb.cam.flipMe === true, 5000);
  await frames(c, 3);
  let f = await c.tb(T => ({ roll: T.cam.rollTarget, mark: T.post().invMark }));
  t.check('hareket açık: kamera 180° dönüyor, işaret yok', Math.abs(f.roll - Math.PI) < 1e-9 && !f.mark, f);
  const yawStep = () => c.eval(() => { const y0 = __tb.me.yaw; document.dispatchEvent(new MouseEvent('mousemove', { movementX: 100, movementY: 0 })); return __tb.me.yaw - y0; });
  const yawOn = await yawStep();
  await toggle(c, 'motion', false); await frames(c, 3);
  f = await c.tb(T => ({ roll: T.cam.rollTarget, mark: T.post().invMark, text: document.querySelector('#invMark').textContent }));
  t.check('hareket kapalı: kamera dönmüyor, "Baş aşağı / fare ters" işareti görünüyor', f.roll === 0 && f.mark && /ters/i.test(f.text), f);
  const yawOff = await yawStep();
  t.check('fare iki durumda da ters (sağa çekince yaw artıyor)', yawOn > 0 && Math.abs(yawOn - yawOff) < 1e-9, { yawOn, yawOff });
  await forceChaos(c, null);
  await c.waitFor(() => window.__tb.cam.flipMe === false, 5000); await frames(c, 2);
  const yawNormal = await yawStep();
  t.check('kaos bitince fare normal, işaret kayboldu', yawNormal < 0 && !(await c.tb(T => T.post().invMark)), { yawNormal });
  await toggle(c, 'motion', true);

  t.step('kafein kaosu: görüş açısı sıçraması isteğe bağlı');
  await forceChaos(c, 'kafein'); await t.sleep(1200);
  const fovOn = await c.tb(T => T.post().fov);
  await toggle(c, 'motion', false); await t.sleep(1200);
  const fovOff = await c.tb(T => T.post().fov);
  t.check('açıkken FOV +14°, kapalıyken ayardaki değer', fovOn > 80 && Math.abs(fovOff - 72) < 1.5, { fovOn, fovOff });
  await forceChaos(c, null); await toggle(c, 'motion', true);

  t.step('flaş ve ekran efektleri');
  await c.tb(T => T.setRole('defuser'));
  await c.moveTo([-4, 0, -8.3], { pin: true }); await H.sleep(250);   // erişim denetimi
  const wrong = await c.tb(T => { const P = T.game.puzzle; return [0, 1, 2, 3, 4, 5].filter(i => i < P.wires.length && i !== P.wireAns); });
  let p = await probe(c, { t: 'act', a: 'cut', i: wrong[0] });
  t.eq('1. hata sayıldı', (await c.state()).strikes, 1);
  t.check('açıkken hata: kırmızı nabız + renk kayması (gölgelendiriciye de gidiyor)', p.filmAb > 0.3 && p.vignette > 0.8 && p.ab > 0.2, p);
  await t.sleep(900);
  t.eq('Flaş ve ekran efektleri kapatıldı', await toggle(c, 'flash', false), false);
  p = await c.tb(T => T.post());
  t.check('kapalı: body.nofx, beyaz flaş katmanı gizli', p.nofx && !p.flashShown, p);
  p = await probe(c, { t: 'act', a: 'cut', i: wrong[1] });
  t.check('kapalıyken hata: kırmızı nabız yok, gölgelendiricide renk kayması 0', p.vignette < 0.05 && p.ab === 0, p);
  t.check('hata yine sayıldı ve bildirildi (2/3, bildirim var)', (await c.state()).strikes === 2 && await c.eval(() => [...document.querySelectorAll('#toasts .toast')].some(d => /2\/3/.test(d.textContent))));

  t.step('sade görüntü');
  t.eq('Sade görüntü açıldı', await toggle(c, 'plain', true), true);
  p = await c.tb(T => T.post());
  t.check('sade: parlama ≤ .1, kum 0, kenar ≤ .15, sabit renk kayması 0', p.bloom <= 0.1 && p.grain === 0 && p.vig <= 0.15 && p.ab0 === 0, p);
  t.eq('Sade görüntü kapatıldı', await toggle(c, 'plain', false), false);
  p = await c.tb(T => T.post());
  t.check('normal değerler geri geldi', p.bloom === 0.42 && p.grain === 0.035 && p.vig === 0.42 && p.ab0 === 0.012, p);

  t.step('ayarlar bulmacaya dokunmadı + kalıcı');
  const logic1 = JSON.parse(await c.tb(LOGIC)), l0 = JSON.parse(logic0);
  t.check('bulmaca verisi aynı (yalnızca bilerek kesilen 2 yanlış kablo ve 2 hata farkı)', JSON.stringify(logic1.puzzle) === JSON.stringify(l0.puzzle) && logic1.strikes === 2 && logic1.wireCut.filter(Boolean).length === 2 && JSON.stringify(logic1.solved) === JSON.stringify(l0.solved));
  await toggle(c, 'motion', false); await toggle(c, 'plain', true); await setShake(c, 0.25);
  const saved = await c.eval(() => JSON.parse(localStorage.getItem('tb-settings')));
  t.check('localStorage: shake .25, motion/flash kapalı, plain açık', saved.shake === 0.25 && saved.motion === false && saved.flash === false && saved.plain === true, saved);

  t.step('patlama: beyaz flaş yerine yumuşak kararma, takla yok');
  p = await c.eval(i => { const T = window.__tb; T.act({ t: 'act', a: 'cut', i }); return new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => r({ ...T.post(), status: T.game.status, roll: T.cam.rollTarget, amp: T.cam.shakeAmp, shake: T.cam.shake })))); }, wrong[2]);
  t.check('yumuşak kararma açık, beyaz flaş görünmüyor, kamera taklası yok, sarsıntı %25', p.status === 'lost' && p.softFade && !p.flashShown && p.roll === 0 && p.amp > 0 && Math.abs(p.amp / p.shake - 0.03) < 1e-6, p);
  await c.page.reload({ waitUntil: 'domcontentloaded' });
  await c.waitFor(() => window.__tb && !document.querySelector('#menu').classList.contains('hidden'), 90000);
  t.eq('sayfa yenilenince ayarlar korunuyor', await c.tb(T => [T.settings.shake, T.settings.motion, T.settings.flash, T.settings.plain, T.post().nofx, T.post().bloom]), [0.25, false, false, true, true, 0.1]);
  await c.close();
}
