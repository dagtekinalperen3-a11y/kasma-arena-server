'use strict';
// İfade: TEKRAR emojisi (8), İŞARETÇİ pankartı, emoji sesi spam sınırı, tek seferlik avatar şakaları (avatarFx / {t:'fx'}).
const H = require('../harness');
const frames = (c, n = 3) => c.eval(n => new Promise(r => { const f = () => (n-- > 0 ? requestAnimationFrame(f) : r()); f(); }), n);
const idOf = c => c.tb(T => T.net.peer.id);
const fxOf = (c, id, kind) => c.tb((T, [id, kind]) => T.fxLog.filter(f => f.id === id && (!kind || f.kind === kind)), [id, kind]);

H.run('express', async t => {
  const pt = await H.party(5), { byRole, clients, host } = pt;
  const P = await H.startGame(host, { diff: 'normal' });
  await host.tb(T => { T.game.chaosIn = 9999; });
  const ids = {}; for (const r of H.ROLES) ids[r] = await idOf(byRole[r]);
  const others = r => clients.filter(c => c !== byRole[r]);
  await H.waitAll(clients, () => Object.keys(window.__tb.avatars).length === 4 && Object.values(window.__tb.players()).every(p => p.p || p.name === window.__tb.players()[window.__tb.net.peer.id].name), 15000);

  t.step('TEKRAR emojisi (8 tuşu)');
  t.eq('emoji listesinde 8. sırada Tekrar var', await host.tb(T => [T.EMOTES.length, T.EMOTES[7].name, T.EMOTES[7].anim]), [8, 'Tekrar', 'again']);
  await byRole.defuser.page.keyboard.press('Digit8');
  await H.waitAll(others('defuser'), id => window.__tb.emoteLog.some(e => e.id === id && e.i === 7), 5000, ids.defuser);
  const seen = await byRole.reader.tb((T, id) => { const a = T.avatars[id]; return { anim: a.emote && a.emote.anim, bubble: a.bubble.visible, placard: !!a.placard }; }, ids.defuser);
  t.check('diğerleri TERS TUŞ\'ta "again" hareketini ve balonu görüyor (pankart yok)', seen.anim === 'again' && seen.bubble && !seen.placard, seen);
  t.check('gönderende bildirim: "Tekrar!"', await byRole.defuser.eval(() => [...document.querySelectorAll('#toasts .toast')].some(d => /Tekrar!/.test(d.textContent))));

  t.step('İŞARETÇİ pankartı');
  for (const [key, sign] of [[6, 'EVET'], [7, 'HAYIR'], [8, 'TEKRAR'], [5, 'DUR'], [3, 'ACELE'], [1, 'BURAYA']]) {
    await byRole.pointer.page.keyboard.press('Digit' + key);
    const ok = await H.waitAll(others('pointer'), ([id, s]) => { const a = window.__tb.avatars[id]; return a.placard && a.placard.visible && a.sign === s && a.placard.material.map; }, 5000, [ids.pointer, sign]).then(() => true, () => false);
    t.check(`${key} → herkes "${sign}" pankartını görüyor`, ok);
    await t.sleep(750);   // gönderme aralığı (700 ms)
  }
  await frames(byRole.tiny, 3);
  const pl = await byRole.tiny.tb((T, id) => { const a = T.avatars[id]; return { w: a.placard.scale.x, y: a.placard.position.y, bubble: a.bubble.visible, armL: a.arms[0].rotation.x }; }, ids.pointer);
  t.check('pankart büyük (≥1.5 m), başın üstünde, emoji balonu yerine geçiyor, köpük el havada', pl.w >= 1.5 && pl.y > 2.2 && !pl.bubble && pl.armL > 2.5, pl);
  t.check('İŞARETÇİ\'de bildirim "Pankart: …" ve tuş çubuğunda pankart yazıları', await byRole.pointer.eval(() => [...document.querySelectorAll('#toasts .toast')].some(d => /Pankart: /.test(d.textContent)) && document.querySelector('#emotes').classList.contains('signs') && /EVET/.test(document.querySelector('#emotes').textContent)));
  t.check('pankart süresi dolunca kayboluyor', await byRole.tiny.waitFor(id => !window.__tb.avatars[id].placard.visible, 6000, ids.pointer).catch(() => false));

  t.step('emoji sesi spam sınırı');
  const spam = await byRole.reader.eval(async id => { const T = window.__tb, w = ms => new Promise(r => setTimeout(r, ms)); T.emoteLog.length = 0; T.playEmote(id, 3); await w(300); T.playEmote(id, 3); await w(300); T.playEmote(id, 6); await w(900); T.playEmote(id, 3); return T.emoteLog.map(e => e.i + ':' + e.muted); }, ids.tiny);
  t.eq('aynı oyuncunun aynı sesi 1.2 sn içinde susturulur; başka ses ve süre dolunca çalar', spam, ['3:false', '3:true', '6:false', '3:false']);
  await t.sleep(800);
  const n0 = await byRole.reader.tb((T, id) => T.emoteLog.filter(e => e.id === id && e.i === 4).length, ids.tiny);
  await byRole.tiny.tb(T => T.emote(4)); await t.sleep(900); await byRole.tiny.tb(T => T.emote(4)); await t.sleep(600);
  const n1 = await byRole.reader.tb((T, id) => T.emoteLog.filter(e => e.id === id && e.i === 4).length, ids.tiny);
  t.eq('korna: 4 sn içinde ikinci kez gönderilmiyor', n1 - n0, 1);

  t.step('bonk: YERÇEKİMSİZ tavana hızlı çarpar');
  t.check('tüm şakalar 1.2 saniyeden kısa', await host.tb(T => Object.values(T.FX_MS).every(ms => ms <= 1200)));
  const fl = byRole.floater;
  await fl.tb(T => { T.me.pos.set(0, 5.0, 4); T.me.vel.set(0, 4, 0); });
  t.check('diğerleri bonk şakasını aldı', await H.waitAll(others('floater'), id => window.__tb.fxLog.some(f => f.id === id && f.kind === 'bonk'), 6000, ids.floater).then(() => true, () => false));
  const b = await byRole.reader.tb((T, id) => { const a = T.avatars[id]; return { fx: a.fx && a.fx.kind, stars: T.fxObjs.length }; }, ids.floater);
  t.check('avatar ezilme animasyonunda ve yıldızlar dönüyor', b.fx === 'bonk' && b.stars >= 1, b);
  const mv = await fl.eval(async () => { const T = window.__tb, y0 = T.me.pos.y, vy = T.me.vel.y; await new Promise(r => setTimeout(r, 250)); return { y0, vy, y1: T.me.pos.y, self: T.fxLog.some(f => f.kind === 'bonk') }; });
  t.check('kontrol kilitlenmedi: YERÇEKİMSİZ sekip aşağı süzülmeye devam ediyor', mv.self && mv.y1 < 5.21 && mv.y1 !== mv.y0, mv);
  await t.sleep(1300);
  t.eq('şaka bitti: avatar normale döndü, yıldızlar silindi', await byRole.reader.tb((T, id) => [T.avatars[id].fx, T.fxObjs.length], ids.floater), [null, 0]);
  await fl.moveTo([0, 2, 6]);

  t.step('oda sahibi: hız sınırı, rol ve tür denetimi');
  const cnt = async () => (await fxOf(byRole.tiny, ids.floater, 'bonk')).length;
  const c0 = await cnt();
  await fl.eval(() => { for (let i = 0; i < 5; i++) window.__tb.act({ t: 'fx', k: 'bonk' }); });
  await t.sleep(500);
  t.eq('art arda 5 istekten yalnızca 1\'i aktarıldı', (await cnt()) - c0, 1);
  await byRole.defuser.eval(() => { const T = window.__tb; T.act({ t: 'fx', k: 'bonk' }); T.act({ t: 'fx', k: 'cheer' }); T.act({ t: 'fx', k: '__proto__' }); T.act({ t: 'fx', k: 7 }); T.act({ t: 'fx' }); });
  await t.sleep(500);
  t.eq('yanlış rol / aktarılamayan tür / bozuk paket yok sayıldı', (await byRole.tiny.tb((T, id) => T.fxLog.filter(f => f.id === id).length, ids.defuser)), 0);
  await byRole.tiny.tb(T => T.sendFx('tumble'));
  t.check('MİNİK\'in taklası diğerlerine ulaştı', await H.waitAll(others('tiny'), id => window.__tb.fxLog.some(f => f.id === id && f.kind === 'tumble'), 5000, ids.tiny).then(() => true, () => false));

  t.step('çeşitlilik: aynı şaka üst üste aynı oynamaz');
  const vs = await byRole.reader.eval(async id => { const T = window.__tb, out = []; for (let i = 0; i < 4; i++) { T.avatarFx(id, 'tumble', 12345); out.push(T.avatars[id].fx.v); await new Promise(r => setTimeout(r, 60)); } return out; }, ids.tiny);
  t.check('aynı tohumla 4 kez: ardışık çeşitler farklı', vs.every((v, i) => i === 0 || v !== vs[i - 1]), vs);

  t.step('cheer: modül çözülünce herkes aynı anda zıplar');
  await clients[0].eval(() => { window.__tb.fxLog.length = 0; }); for (const c of clients) await c.tb(T => { T.fxLog.length = 0; });
  await H.solveModule(byRole, 'wires', P);
  await H.waitAll(clients, () => window.__tb.game.solved.wires === true, 6000);
  await t.sleep(200);
  const cheers = await Promise.all(clients.map(c => c.tb(T => T.fxLog.filter(f => f.kind === 'cheer').map(f => f.v))));
  t.check('her istemcide 5 sevinç (4 avatar + kendisi), hepsinde aynı çeşit', cheers.every(a => a.length === 5 && a.every(v => v === cheers[0][0])), cheers);

  t.step('hata tepkisi ve sahte ördek');
  await t.sleep(1000); for (const c of clients) await c.tb(T => { T.fxLog.length = 0; });
  const badDuck = [0, 1, 2, 3, 4, 5, 6].find(i => !P.ducks.gold.includes(i));
  const spot = P.ducks.spots[badDuck];
  await fl.moveTo([spot[0], spot[1] - 1.9, spot[2] + 1.2], { pin: true }); await t.sleep(400);
  await fl.act('duck', { i: badDuck });
  await H.waitAll(clients, () => window.__tb.game.strikes === 1, 6000);
  await t.sleep(150);
  const q = await byRole.reader.tb((T, ids) => ({ floater: T.fxLog.filter(f => f.id === ids.floater).map(f => f.kind), tiny: T.fxLog.filter(f => f.id === ids.tiny).map(f => f.kind), objs: T.fxObjs.length, ducksInScene: T.M.ducks[0] ? 1 : 0 }), ids);
  t.check('sahte ördek: ördek şişip fırlıyor, kapan irkiliyor (quack), diğerleri irkiliyor (flinch)', q.floater.includes('quack') && q.tiny.includes('flinch') && q.objs >= 1, q);
  await t.sleep(1300);
  t.eq('ördek şakası 1.2 sn içinde temizlendi', await byRole.reader.tb(T => T.fxObjs.length), 0);
  await fl.unpin();
  for (const c of clients) await c.tb(T => { T.fxLog.length = 0; });
  await byRole.defuser.act('key', { i: P.layout.indexOf(P.order[1]) });   // yanlış sembol → hata
  await H.waitAll(clients, () => window.__tb.game.strikes === 2, 6000);
  await t.sleep(150);
  const o = await byRole.reader.tb((T, ids) => ({ defuser: T.fxLog.filter(f => f.id === ids.defuser).map(f => f.kind), floater: T.fxLog.filter(f => f.id === ids.floater).map(f => f.kind) }), ids);
  t.check('hatayı yapan "oops", diğerleri "flinch" tepkisi veriyor', o.defuser.includes('oops') && o.floater.includes('flinch'), o);

  t.step('konuşma tepkisi'); await t.sleep(700);
  const talk = await byRole.reader.eval(async id => { const T = window.__tb, a = T.avatars[id]; const fr = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(r)))); a.talkUntil = performance.now() + 60000; await fr(); const on = a.arms[1].rotation.x; a.talkUntil = 0; await fr(); return { on, off: a.arms[1].rotation.x }; }, ids.tiny);
  t.check('kaydı çalarken el kol hareketi, bitince normal', talk.on > 0.7 && Math.abs(talk.off) < 0.5, talk);
  t.noErrors();
});
