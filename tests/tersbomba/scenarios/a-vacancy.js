'use strict';
// PKG-A / A6: tur ortasında rol boşalması.
//  1) şart rol (YERÇEKİMSİZ) kopar → sayaç donar, herkes bandı görür → aynı jetonla dönünce rolünü geri alır, sayaç yürür
//  2) İŞARETÇİ dönmez → bekleme dolunca Lazer Kilidi otomatik kapanır (−15 sn), bildiği bilgiler zincirdeki role geçer
//  3) TERS TUŞ dönmez → 5 modülü otomatik kapanır, sigorta renkleri YERÇEKİMSİZ'e geçer → kalan 3 kişi turu KAZANIR
const H = require('../harness'), A = require('../a-lib');

H.run('a-vacancy', async t => {
  const { clients, host, byRole: R, infra, code } = await H.party(5);
  await H.startGame(host, { diff: 'normal' });
  const P = await A.full(host);
  const g = expr => host.tb(expr);
  const leave = async c => { await c.close(); host.room.members = host.room.members.filter(x => x !== c); };
  const alive = () => clients.filter(c => host.room.members.includes(c));

  t.step('1) YERÇEKİMSİZ sayfayı yeniler (bağlantı kopar)');
  const fl = R.floater, tok = await fl.eval(() => localStorage.getItem('tb-token'));
  t.check('istemcide kalıcı jeton var', /^[\w-]{8,64}$/.test(tok || ''), tok);
  const others = clients.filter(c => c !== fl);
  await fl.page.goto(infra.url({ norender: true }), { waitUntil: 'domcontentloaded' });
  await fl.page.waitForFunction(() => window.__tb && !document.querySelector('#menu').classList.contains('hidden'), null, { timeout: 90000 });
  const t0 = Date.now();
  await H.waitAll(others, () => window.__tb.game.frozen === true && (window.__tb.game.vac || []).some(v => v.role === 'floater'), 20000);
  t.log(`kopma ${Date.now() - t0} ms içinde fark edildi`);
  const a = await Promise.all(others.map(c => c.tb('T.game.timeLeft'))); await t.sleep(2500);
  const b = await Promise.all(others.map(c => c.tb('T.game.timeLeft')));
  t.check('sayaç 2.5 sn boyunca 4 istemcide de durdu', a.every((v, i) => Math.abs(v - b[i]) < 0.05), { a, b });
  const banner = await R.tiny.eval(() => { const el = document.querySelector('#vacBanner'); return el.classList.contains('hidden') ? '' : el.textContent; });
  t.check('bant: "3-floater (YERÇEKİMSİZ) koptu — bekleniyor NN sn" + sayaç durdu', /3-floater.*YERÇEKİMSİZ.*koptu — bekleniyor \d+ sn.*Sayaç durdu/.test(banner), banner);
  t.eq('oyuncu listesinde yok, tur sürüyor', [Object.keys((await host.state()).players).length, (await host.state()).status], [4, 'playing']);
  // donukken diğerleri oynamaya devam eder
  await A.solve(R, 'keypad', P);
  await H.waitAll(others, () => window.__tb.game.solved.keypad === true, 8000);
  t.check('sayaç donukken modül çözülebiliyor', true);

  t.step('1b) aynı jetonla yeniden katılır → rolünü geri alır');
  await fl.page.fill('#nameIn', fl.name); await fl.page.fill('#codeIn', code); await fl.page.click('#btnJoin');   // (H.joinRoom lobiyi bekler; tur ortasında doğrudan oyuna girilir)
  await fl.waitFor(() => { const T = window.__tb; return T.game && T.myRole() === 'floater' && !document.querySelector('#hud').classList.contains('hidden'); }, 20000);
  await H.waitAll(clients, () => window.__tb.game.frozen === false && !(window.__tb.game.vac || []).length, 10000);
  const c1 = await host.tb('T.game.timeLeft'); await t.sleep(1500);
  t.check('sayaç yeniden işliyor', c1 - await host.tb('T.game.timeLeft') > 1);
  let s = await H.converge(clients);
  t.check('dönen oyuncu güncel durumu aldı (keypad çözük, 5 oyuncu)', s.solved.keypad === true && Object.keys(s.players).length === 5 && s.players['3-floater'] === 'floater', s);
  t.check('bant kapandı', await R.tiny.eval(() => document.querySelector('#vacBanner').classList.contains('hidden')));
  t.eq('donma süresi sayıldı (0 < sn < 30)', await g('T.hostR().frozeFor > 0 && T.hostR().frozeFor < 30'), true);

  t.step('2) İŞARETÇİ çıkar ve dönmez (şart rol değil: sayaç donmaz)');
  await leave(R.pointer);
  await H.waitAll(alive(), () => (window.__tb.game.vac || []).some(v => v.role === 'pointer'), 20000);
  t.eq('sayaç donmadı', await g('T.game.frozen'), false);
  const tl0 = await g('T.game.timeLeft');
  await g('T.hostR().vac.pointer.left = 1.5');      // 30 sn'lik beklemeyi kısalt
  await H.waitAll(alive(), () => window.__tb.game.solved.laser === true && window.__tb.game.auto.includes('laser'), 10000);
  const lost = tl0 - await g('T.game.timeLeft');
  t.check(`lazer kilidi otomatik kapandı, ceza −15 sn (ölçülen kayıp ${lost.toFixed(1)} sn)`, lost > 15 && lost < 20, lost);
  await t.sleep(400);
  const hp = await A.full(host);
  t.eq('bilgi devri: sembol→YERÇEKİMSİZ, ördek→MİNİK, fare kodu→TERS SES', [hp.keypadInfo, hp.duckInfo, hp.mouseInfo], ['floater', 'tiny', 'reader']);
  t.check('YERÇEKİMSİZ sembol sırasını gizli notunda görüyor', (await fl.page.textContent('#secret')).includes(P.order[0]) && !(await fl.eval(() => document.querySelector('#secret').classList.contains('hidden'))));
  t.check('MİNİK artık altın ördekleri görüyor (not)', /Altın ördekler/.test(await R.tiny.page.textContent('#secret')));
  t.check('TERS SES fare kodunu görüyor', (await host.page.textContent('#secret')).replace(/\s/g, '').includes(P.mouseCode.join('')));

  t.step('3) TERS TUŞ çıkar ve dönmez → modülleri otomatik kapanır');
  await leave(R.defuser);
  await H.waitAll(alive(), () => window.__tb.game.frozen === true, 20000);
  await g('T.hostR().vac.defuser.left = 1.5');
  await H.waitAll(alive(), () => ['wires', 'button'].every(m => window.__tb.game.solved[m] && window.__tb.game.auto.includes(m)) && window.__tb.game.frozen === false, 10000);
  s = await H.converge(alive());
  t.check('oyun sürüyor, hata yok', s.status === 'playing' && s.strikes === 0, s);
  t.eq('otomatik kapananlar', (await g('T.game.auto')).slice().sort(), ['button', 'laser', 'wires']);
  await t.sleep(400);
  t.check('sigortada yanan renkler YERÇEKİMSİZ\'in notunda', /yanan renkler/.test(await fl.page.textContent('#secret')));

  t.step('3b) kalan 3 kişi kalan modülleri çözer ve kazanır');
  const R3 = { reader: host, floater: fl, tiny: R.tiny };
  t.check('şifre ipucu TERS SES\'in notuna geçti', /Şifre ipucu/.test(await host.page.textContent('#secret')));
  for (const mod of ['password', 'maze', 'fuse', 'ducks', 'mouse', 'keys']) {
    await A.solve(R3, mod, P);
    const ok = await H.waitAll(alive(), m => window.__tb.game.solved[m] === true, 10000, mod).then(() => true, e => e.message);
    t.check(`${mod} çözüldü`, ok === true, ok);
  }
  await H.waitAll(alive(), () => !!window.__tb.game.final, 8000);
  await H.toPlates(alive());
  const won = await H.waitAll(alive(), () => window.__tb.game.status === 'won', 15000).then(() => true, e => e.message);
  t.check('kalan 3 kişi turu kazandı', won === true, won);
  const sc = await host.tb(T => ({ solved: Object.values(T.game.solved).filter(Boolean).length, auto: T.game.auto.length }));
  t.eq('10 modül kapalı, 4\'ü otomatik', sc, { solved: 10, auto: 3 });
  t.eq('oda sahibinde yakalanan istisna yok', (await g('T.hostDiag')).caught, 0);
  t.noErrors(alive());
}, { timeout: 480000 });
