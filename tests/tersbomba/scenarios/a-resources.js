'use strict';
// PKG-A / A7: kaynak sızıntısı ölçümü (çizim AÇIK, düşük kalite, küçük pencere — renderer.info.memory yalnızca çizilen şeyleri sayar).
//  A) antrenman, 10 tur: her turda ördek yağmuru + patlama (kaybet) → "Yeni Bomba". Tur başlarındaki GPU sayıları büyümemeli.
//  B) 3 kişi, 5 tur: turlar arasında iki misafir rol değiştirir (avatarlar yeniden kurulur) → oda sahibinde sayılar büyümemeli.
const H = require('../harness');

const settle = (c, ms = 1200) => c.eval(ms => new Promise(r => setTimeout(r, ms)), ms);
H.run('a-resources', async t => {
  const infra = await H.startInfra(), browser = await H.launchBrowser();
  const view = { norender: false, quality: 'low', viewport: { width: 320, height: 200 } };

  t.step('A) antrenman: 10 tur (ördek yağmuru + patlama)');
  const c = await H.newClient(browser, infra, { name: 'Solo', ...view });
  await H.soloRoom(c);
  const rows = [];
  for (let r = 1; r <= 10; r++) {
    if (r === 1) await H.startGame(c, { diff: 'kolay' });
    else { await c.tb('T.hostStart()'); await c.waitFor(() => { const g = window.__tb.game; return g && g.status === 'playing' && g.countdown <= 0; }, 60000); }
    await settle(c);
    rows.push(await c.tb('T.res()'));
    // ördek yağmuru (45 ördek), sonra süreyi bitir → patlama
    await c.tb(T => { T.game.chaos = { type: 'ordek', left: 9, dur: 10, target: T.myId, seed: 1 }; });
    await c.waitFor(() => window.__tb.res().rain >= 20, 15000);
    await c.tb(T => { T.game.timeLeft = 0.2; });
    await c.waitFor(() => !document.querySelector('#endScreen').classList.contains('hidden'), 30000);
  }
  const f = rows[1], l = rows[9];
  t.log('tur başı ölçümleri (geo/tex/prog/sahne nesnesi): ' + rows.map(x => `${x.geo}/${x.tex}/${x.prog}/${x.objs}`).join('  '));
  t.check(`geometri sayısı büyümüyor (2. tur ${f.geo} → 10. tur ${l.geo})`, l.geo - f.geo <= 40, rows.map(x => x.geo));
  t.check(`doku sayısı büyümüyor (2. tur ${f.tex} → 10. tur ${l.tex})`, l.tex - f.tex <= 10, rows.map(x => x.tex));
  t.check(`sahne nesnesi sayısı büyümüyor (2. tur ${f.objs} → 10. tur ${l.objs})`, l.objs - f.objs <= 20, rows.map(x => x.objs));
  t.check('tur başında eski parçacık / yağmur ördeği kalmıyor', rows.slice(1).every(x => x.particles === 0 && x.rain === 0), rows.map(x => [x.particles, x.rain]));
  t.noErrors([c]);
  await c.close();

  t.step('B) 3 kişi: 5 tur, turlar arasında rol değişimi (avatarlar yeniden kurulur)');
  const host = await H.newClient(browser, infra, { name: 'H', ...view }), g1 = await H.newClient(browser, infra, { name: 'G1' }), g2 = await H.newClient(browser, infra, { name: 'G2' });
  const code = await H.hostRoom(host); await H.joinRoom(g1, code); await H.joinRoom(g2, code);
  const rows2 = [];
  for (let r = 1; r <= 5; r++) {
    await H.setRole(g1, r % 2 ? 'defuser' : 'floater'); await H.setRole(g2, r % 2 ? 'floater' : 'defuser');
    await host.waitFor(() => window.__tb.missingRoles().length === 0, 8000);
    await H.startGame(host, { diff: 'kolay' });
    await g1.moveTo([-2, 0, 5], { pin: true }); await g2.moveTo([2, 1, 5], { pin: true });
    await host.tb(T => { T.me.pos.set(0, 0, 8.5); T.me.yaw = 0; T.me.pitch = 0; });   // iki avatar da görüş alanında
    await settle(host, 1500);
    rows2.push(await host.tb('T.res()'));
    await host.tb('T.toLobby()');
    await H.waitAll([host, g1, g2], () => !document.querySelector('#lobby').classList.contains('hidden'), 15000);
  }
  const f2 = rows2[1], l2 = rows2[4];
  t.log('tur başı ölçümleri (geo/tex/prog/sahne nesnesi/lazer): ' + rows2.map(x => `${x.geo}/${x.tex}/${x.prog}/${x.objs}/${x.lasers}`).join('  '));
  t.check(`geometri sayısı büyümüyor (2. tur ${f2.geo} → 5. tur ${l2.geo})`, l2.geo - f2.geo <= 40, rows2.map(x => x.geo));
  t.check(`doku sayısı büyümüyor (2. tur ${f2.tex} → 5. tur ${l2.tex})`, l2.tex - f2.tex <= 8, rows2.map(x => x.tex));
  t.check(`sahne nesnesi sayısı büyümüyor (2. tur ${f2.objs} → 5. tur ${l2.objs})`, l2.objs - f2.objs <= 20, rows2.map(x => x.objs));
  t.noErrors([host, g1, g2]);
}, { timeout: 900000 });
