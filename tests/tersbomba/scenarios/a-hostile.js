'use strict';
// PKG-A / A3: bozuk ve kötü niyetli paketler oda sahibini ve diğer istemcileri düşürmez, durumu değiştirmez;
// hız sınırı, isim temizliği ve oyuncu sınırı (8) çalışır.
const H = require('../harness');

H.run('a-hostile', async t => {
  const { clients, host, byRole: R, infra, browser, code } = await H.party(4, ['reader', 'defuser', 'floater', 'tiny']);
  const bad = R.tiny;

  t.step('lobide: geçersiz rol / tekrar hello / isim temizliği');
  await bad.tb(T => { T.raw({ t: 'role', role: 'admin' }); T.raw({ t: 'role', role: '__proto__' }); T.raw({ t: 'role', role: 7 }); T.raw({ t: 'hello', name: 'Korsan' }); T.raw({ t: 'hello', name: { toString: 1 } }); });
  await t.sleep(500);
  let s = await host.state();
  t.eq('roller ve isimler değişmedi', s.players, { '1-reader': 'reader', '2-defuser': 'defuser', '3-floater': 'floater', '4-tiny': 'tiny' });
  t.eq('isim temizliği', await host.tb(T => [T.cleanName('  <b>Ali\u0000\n  Veli</b>  '), T.cleanName(null), T.cleanName('x'.repeat(500)).length, T.cleanName({}), T.cleanName('‮​ ')]), ['bAli Veli/b', 'Oyuncu', 16, 'Oyuncu', 'Oyuncu']);

  t.step('oyuncu sınırı: 8 kişi dolunca 9. kişi alınmaz');
  const extra = [];
  for (let i = 5; i <= 8; i++) { const c = await H.newClient(browser, infra, { name: 'X' + i }); await H.joinRoom(c, code); extra.push(c); }
  t.eq('8 oyuncu (5. rol + 3 izleyici)', Object.values((await host.state()).players).sort(), ['defuser', 'floater', 'none', 'none', 'none', 'pointer', 'reader', 'tiny']);
  const ninth = await H.newClient(browser, infra, { name: 'X9' });
  await ninth.page.fill('#nameIn', 'X9'); await ninth.page.fill('#codeIn', code); await ninth.page.click('#btnJoin');
  const full = await ninth.waitFor(() => /dolu/.test(document.querySelector('#menuStatus').textContent), 15000).catch(() => false);
  t.check('9. kişi "oda dolu" mesajını gördü ve menüde', full && (await ninth.state()).screen === 'menu');
  t.eq('oda sahibinde hâlâ 8 oyuncu', Object.keys((await host.state()).players).length, 8);
  for (const c of [...extra, ninth]) await c.close();
  host.room.members = host.room.members.filter(c => clients.includes(c));
  await host.waitFor(() => Object.keys(window.__tb.players()).length === 4, 20000);

  t.step('oyunu başlat');
  await H.startGame(host, { diff: 'normal' });
  await bad.moveTo([0, 0, 0.9], { pin: true });
  const snap = () => host.tb(T => { const g = T.game; return JSON.stringify({ st: g.status, strikes: g.strikes, solved: g.solved, wireCut: g.wireCut, keyProg: g.keyProg, pwIdx: g.pwIdx, fuse: g.fuse, ducksGot: g.ducksGot, mouseDial: g.mouseDial, mazeVisited: g.mazeVisited, mazeFails: g.mazeFails, laserProg: g.laserProg, btnHeld: g.btnHeld, players: Object.values(T.players()).map(p => p.name + ':' + p.role).sort() }); });
  const before = await snap(), t0 = (await host.state()).timeLeft;

  t.step('bozuk paket yağmuru');
  await bad.tb(T => {
    // not: çıplak `null` paketi PeerJS 1.5.4'ün kendi _handleDataMessage'ında istisna fırlatır (oyuna ulaşmadan; oda sahibi çalışmaya devam eder) → burada yollanmıyor
    const junk = [0, 'merhaba', [], [1, 2, 3], {}, { t: 5 }, { t: null }, { t: '__proto__' }, { t: 'constructor' }, { t: 'toString' }, { t: 'bilinmeyen', x: 1 },
      { t: 'pos' }, { t: 'pos', p: 'abc' }, { t: 'pos', p: [1, 2] }, { t: 'pos', p: [NaN, 0, 0] }, { t: 'pos', p: [1e99, 'x', 0] }, { t: 'pos', p: { length: 3 } }, { t: 'pos', p: [0, 0, 0], yaw: 'x', l: 'lazer' }, { t: 'pos', p: [0, 0, 0], l: [1, 2] }, { t: 'pos', p: new Array(1000).fill(0) },
      { t: 'act' }, { t: 'act', a: null }, { t: 'act', a: 5 }, { t: 'act', a: '__proto__' }, { t: 'act', a: 'constructor' }, { t: 'act', a: 'hasOwnProperty' }, { t: 'act', a: 'patlat' },
      { t: 'act', a: 'cut', i: 99 }, { t: 'act', a: 'cut', i: -1 }, { t: 'act', a: 'cut', i: 1.5 }, { t: 'act', a: 'cut', i: '0' }, { t: 'act', a: 'cut' },
      { t: 'act', a: 'key', i: 4 }, { t: 'act', a: 'pw', c: 9, d: 1 }, { t: 'act', a: 'pw', c: 0, d: 5 }, { t: 'act', a: 'pw', c: 0 }, { t: 'act', a: 'fuse', i: 77 }, { t: 'act', a: 'duck', i: 7 }, { t: 'act', a: 'duck', i: null },
      { t: 'act', a: 'dial', i: 3 }, { t: 'act', a: 'dial', i: -2 }, { t: 'act', a: 'dial', i: {} }, { t: 'act', a: 'maze', i: 20 }, { t: 'act', a: 'maze', i: 1e9 }, { t: 'act', a: 'turnKey', i: 2 }, { t: 'act', a: 'turnKey', i: 'a' },
      { t: 'act', a: 'btnUp', dur: 'x', timer: {} }, { t: 'act', a: 'laser', i: 0 }, { t: 'role', role: 'defuser' }, { t: 'hello', name: 'x'.repeat(8000) }, { t: 'emote' }, { t: 'emote', e: 'x' }, { t: 'emote', e: 1e9 }, { t: 'voice' }, { t: 'voice', data: 5 }, { t: 'ping', x: [] }];
    for (const j of junk) { try { T.raw(j); } catch (e) {} }
  });
  await t.sleep(2500);   // hız sınırı kovaları dolsun
  // sıra garantisi: aynı kanaldan SONRA yollanan geçerli aksiyon işlendiyse öncekiler de işlenmiştir
  await bad.act('dial', { i: 0 });
  await H.waitAll(clients, () => window.__tb.game.mouseDial[0] === 1, 10000);
  const after = JSON.parse(await snap());
  t.eq('durum değişmedi (yalnızca son geçerli aksiyon işlendi)', { ...after, mouseDial: [0, 0, 0] }, JSON.parse(before));
  const d = await host.tb('T.hostDiag');
  t.log('hostDiag: ' + JSON.stringify(d));
  t.eq('oda sahibinde yakalanan istisna yok (doğrulama yeterli)', d.caught, 0);
  t.check('bozuk paketler sayıldı', d.bad >= 20, d);
  t.check('oda sahibinin saati işliyor', (await host.state()).timeLeft < t0 - 1.5);
  t.check('hostile istemcinin konumu oda içinde kaldı', await host.tb(T => Object.values(T.players()).every(p => !p.p || (Math.abs(p.p[0]) <= 12 && p.p[1] >= 0 && p.p[1] <= 7 && Math.abs(p.p[2]) <= 10))));
  const cs = await H.converge(clients);
  t.check('4 istemci aynı durumda, oyun sürüyor', cs.status === 'playing' && cs.strikes === 0, cs);

  t.step('hız sınırı: 300 aksiyon + 2000 konum paketi tek seferde');
  await t.sleep(1500);
  const lim0 = (await host.tb('T.hostDiag')).limited;
  await bad.tb(T => { for (let i = 0; i < 300; i++) T.raw({ t: 'act', a: 'dial', i: 1 }); });
  await t.sleep(2500);
  await bad.act('dial', { i: 2 });
  await H.waitAll(clients, () => window.__tb.game.mouseDial[2] === 1, 10000);
  const done = 300 - ((await host.tb('T.hostDiag')).limited - lim0);
  t.check(`300 aksiyondan yalnızca bir patlama kadarı işlendi (işlenen: ${done})`, done >= 5 && done <= 30, done);
  const lim1 = (await host.tb('T.hostDiag')).limited;
  await bad.tb(T => { for (let i = 0; i < 2000; i++) T.raw({ t: 'pos', p: [0, 0, 0.9], yaw: i }); });
  await t.sleep(2000);
  const lim = (await host.tb('T.hostDiag')).limited - lim1;
  t.check(`2000 konum paketinden sınıra takılan: ${lim}`, lim >= 1850 && lim < 2000, lim);
  t.check('diğer oyuncular etkilenmedi', (await H.converge(clients)).status === 'playing');
  t.eq('hâlâ istisna yok', (await host.tb('T.hostDiag')).caught, 0);
  t.noErrors(clients);
}, { timeout: 420000 });
