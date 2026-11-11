'use strict';
// Antrenman (tek kişi): başlat → her modülü çöz → final plakası → kazan.
const H = require('../harness'), A = require('../a-lib');   // a-lib: erişim/hız kurallarına uyan çözücüler

H.run('smoke-solo', async t => {
  t.step('altyapı + tek istemci');
  const infra = await H.startInfra(), browser = await H.launchBrowser();
  const c = await H.newClient(browser, infra, { name: 'Solo' });

  t.step('Antrenman odası → Normal zorlukta başlat');
  t.eq('oda kodu TEST', await H.soloRoom(c), 'TEST');
  await H.startGame(c, { diff: 'normal' });
  const P = await A.full(c);   // bulmacanın tamamı yalnızca oda sahibinde (antrenmanda: kendisi)
  t.log(`modüller: ${P.mods.join(', ')} · süre ${P.time} sn`);
  t.eq('Normal: 10 modülün hepsi var', P.mods.length, 10);
  let s = await c.state();
  t.check('oyun başladı (playing, hata yok)', s.status === 'playing' && s.strikes === 0 && s.screen === 'game', s);

  t.step('modülleri çöz (her biri kendi rolüyle)');
  const R = H.soloRoles(c);
  for (const mod of P.mods) {
    await H.solveModule(R, mod, P);
    const ok = await c.waitFor(m => window.__tb.game.solved[m] === true, 5000, mod).catch(() => false);
    t.check(`${mod} çözüldü`, ok, await c.state());
  }
  s = await c.state();
  t.eq('hiç hata yapılmadı', s.strikes, 0);

  t.step('final: plakaya bas, 1.5 sn bekle');
  t.check('final başladı', await c.waitFor(() => !!window.__tb.game.final, 5000).catch(() => false), s);
  t.check('henüz kazanılmadı (plakada kimse yok)', (await c.state()).status === 'playing');
  await H.toPlates([c]);
  t.check('status === won', await c.waitFor(() => window.__tb.game.status === 'won', 15000).catch(() => false), await c.state());
  t.check('bitiş ekranı açıldı', await c.waitFor(() => !document.querySelector('#endScreen').classList.contains('hidden'), 15000).catch(() => false));
  t.eq('başlık', await c.page.textContent('#endTitle'), 'İMHA EDİLDİ');
  await c.shot('smoke-solo-end.png');
  t.noErrors();
});
