'use strict';
// Ekran görüntüleri (çizim AÇIK, yazılımsal WebGL yavaştır): TB_SHOTS=ad1,ad2 ile yalnızca seçilenler alınır.
// Kalite: TB_Q=low|high (varsayılan ikisi de), boyut 1280×720. Çıktı: TB_OUT (varsayılan tests/tersbomba/out).
const H = require('../harness');
const ONLY = (process.env.TB_SHOTS || '').split(',').filter(Boolean), QS = (process.env.TB_Q || 'low,high').split(',');
const want = n => !ONLY.length || ONLY.includes(n);
const settle = (c, n = 3) => c.eval(n => new Promise(r => { const f = () => (n-- > 0 ? requestAnimationFrame(f) : r()); f(); }), n);
// kamerayı sabitle: rol, konum, bakış
const view = async (c, role, pos, yaw, pitch = 0) => {
  await c.tb((T, [role, pos, yaw, pitch]) => { if (T.myRole() !== role) T.setRole(role); clearInterval(window.__tbPin); const put = () => { T.me.pos.set(pos[0], pos[1], pos[2]); T.me.vel.set(0, 0, 0); T.me.yaw = yaw; T.me.pitch = pitch; }; put(); window.__tbPin = setInterval(put, 30); document.querySelector('#pause').classList.add('hidden'); document.querySelector('#roleCard').classList.remove('open'); }, [role, pos, yaw, pitch]);
  await settle(c, 4);
};
// sahte oyuncular: silüet ve pankart görüntüleri için (yalnızca yerel; oda sahibi mantığına girmez)
const crowd = (c, list) => c.tb((T, list) => { const P = T.players(); list.forEach(([role, x, z, yaw], i) => { P['f' + i] = { name: role.toUpperCase(), role, p: [x, role === 'floater' ? 1.2 : 0, z], yaw }; }); T.setRole(T.myRole()); }, list);

H.run('shots', async t => {
  const infra = await H.startInfra(), browser = await H.launchBrowser();
  for (const q of QS) {
    t.step(`kalite: ${q}`);
    const c = await H.newClient(browser, infra, { name: 'Foto', quality: q, norender: false, viewport: { width: 1280, height: 720 } });
    const shot = async n => { if (want(n)) { await settle(c, 2); t.log(await c.shot(`e-${q}-${n}.png`)); } };
    await c.tb(T => { T.settings.motion = false; T.settings.shake = 0; T.applyComfort(); });   // sabit kare: sallanma yok
    await shot('menu');
    if (want('settings')) { await c.page.click('#btnSet'); await shot('settings'); await c.page.click('#setModal [data-close]'); }
    await H.soloRoom(c);
    await H.startGame(c, { diff: 'normal' });
    await c.tb(T => { T.game.chaosIn = 9999; T.game.timeLeft = 400; T.applyTheme('gunduz'); });
    if (want('pause')) { await c.tb(T => T.setRole('reader')); await shot('pause'); }
    if (want('centre')) { await view(c, 'defuser', [0, 0, 8.6], 0, 0.05); await shot('centre'); }
    if (want('compass-n')) { await view(c, 'pointer', [0, 0, 7], 0, 0.22); await shot('compass-n'); }
    if (want('compass-e')) { await view(c, 'pointer', [-7, 0, 0], -Math.PI / 2, 0.2); await shot('compass-e'); }
    if (want('compass-s')) { await view(c, 'pointer', [0, 0, -7], Math.PI, 0.25); await shot('compass-s'); }
    if (want('compass-w')) { await view(c, 'pointer', [7, 0, 0], Math.PI / 2, 0.2); await shot('compass-w'); }
    if (want('floor')) { await view(c, 'floater', [0, 5, 0.01], 0, -1.5); await shot('floor'); }
    if (want('tiny-eye')) { await view(c, 'tiny', [-2, 0, 3], 0.25, 0.3); await shot('tiny-eye'); }
    if (want('floater-eye')) { await view(c, 'floater', [-3, 4.6, 5], -0.5, -0.3); await shot('floater-eye'); }
    if (want('avatars') || want('placard')) {
      await crowd(c, [['reader', -4, -1, Math.PI], ['defuser', -2, -1, Math.PI], ['floater', 0, -1, Math.PI], ['pointer', 2, -1, Math.PI], ['tiny', 4, -1, Math.PI]]);
      await c.tb(T => T.setRole('none'));
      await view(c, 'none', [0, 0, 9.4], 0, 0.02); await settle(c, 6); await shot('avatars');
      if (want('placard') && await c.tb(T => typeof T.playEmote === 'function')) { await c.tb(T => { T.playEmote('f3', 5); T.playEmote('f0', 7); }); await settle(c, 12); await shot('placard'); }
    }
    if (want('disco')) { await view(c, 'defuser', [0, 0, 8.6], 0, 0.05); await c.tb(T => { T.game.chaos = { type: 'disko', left: 60, dur: 60, target: 'solo', seed: 1 }; }); await t.sleep(1500); await settle(c, 6); await shot('disco'); }
    t.check(`${q}: sayfa hatası yok`, c.errors.length === 0, c.errors.join(' | '));
    await c.close();
  }
}, { timeout: 1500000 });
