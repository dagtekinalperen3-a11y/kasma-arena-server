'use strict';
// 5 oyuncu, 5 farklı rol, tek oda (yerel PeerServer + gerçek WebRTC veri kanalları):
// roller tutarlı mı → her modülü yetkili rol çözer → yanlış rol reddedilir → final → herkes "won" görür.
const H = require('../harness'), A = require('../a-lib');   // a-lib: erişim/hız kurallarına uyan çözücüler

H.run('smoke-5p', async t => {
  t.step('5 istemci, oda kur + katıl, rolleri dağıt');
  const { clients, host, code, byRole: R } = await H.party(5);   // reader(oda sahibi), defuser, floater, pointer, tiny
  t.log(`oda ${code} · ${clients.map(c => c.name).join(', ')}`);
  const wantRoles = Object.fromEntries(clients.map((c, i) => [c.name, H.ROLES[i]]));
  for (const c of clients) {
    const s = await c.state();
    t.check(`${c.name}: lobide, kendi rolü doğru, 5 oyuncunun rolünü aynı görüyor`, s.screen === 'lobby' && s.role === wantRoles[c.name] && JSON.stringify(Object.entries(s.players).sort()) === JSON.stringify(Object.entries(wantRoles).sort()), s);
  }
  const net = await Promise.all(clients.map(c => c.tb('({ host: T.net.isHost, up: !!(T.net.hostConn && T.net.hostConn.open), peers: T.net.conns.filter(c => c.open).map(c => c.peer) })')));
  t.check('oda sahibi 4 ayrı istemciye açık veri kanalıyla bağlı, diğerleri oda sahibine bağlı', net[0].host && new Set(net[0].peers).size === 4 && net.slice(1).every(n => !n.host && n.up), net);
  // OYUN HATASI: PeerJS/Chromium bazen aynı bağlantı için 'open' olayını iki kez verir; hostRoom() bağlantıyı net.conns'a
  // iki kez ekler ve o istemci her yayını (state, start, emote, voice...) iki kez alır. Düzeltme: push'tan önce includes() kontrolü.
  t.bug('oda sahibinin net.conns listesinde aynı bağlantı iki kez yok', net[0].peers.length === new Set(net[0].peers).size, `net.conns: ${net[0].peers.length} kayıt, ${new Set(net[0].peers).size} ayrı istemci`);

  t.step('Normal zorlukta başlat');
  await H.startGame(host, { diff: 'normal' });
  const P = await A.full(host);   // bulmacanın tamamı yalnızca oda sahibinde
  t.log(`modüller: ${P.mods.join(', ')} · süre ${P.time} sn`);
  t.eq('5 rol varken 10 modülün hepsi açık', P.mods.length, 10);
  const puzzles = await Promise.all(clients.map(c => c.puzzle()));
  t.check('bulmaca 5 istemcide birebir aynı', puzzles.every(p => JSON.stringify(p) === JSON.stringify(P)));
  const checkpoint = async label => {
    const s = await H.converge(clients).catch(e => (t.check(`yakınsama @ ${label}`, false, e.message), null));
    if (s) t.check(`yakınsama @ ${label}: status=${s.status} strikes=${s.strikes} çözülen=${Object.values(s.solved).filter(Boolean).length}/${P.mods.length} timeLeft=${s.timeLeft} (fark ${s.spread} sn)`, true);
    return s;
  };
  let s = await checkpoint('başlangıç');
  t.check('başlangıç: playing, 0 hata, hiçbir modül çözülmemiş', s && s.status === 'playing' && s.strikes === 0 && Object.values(s.solved).every(v => v === false), s);
  for (const c of clients) t.eq(`${c.name}: oyun içinde rolü aynı`, (await c.state()).role, wantRoles[c.name]);

  t.step('yanlış rolden gelen aksiyon reddedilir');
  const snap = () => host.tb('({ strikes: T.game.strikes, solved: T.game.solved, wireCut: T.game.wireCut, fuse: T.game.fuse, ducksGot: T.game.ducksGot, laserProg: T.game.laserProg, keyProg: T.game.keyProg })');
  const before = await snap(), wrongWire = (P.wireAns + 1) % P.wires.length;
  // herkes ilgili modülün yanında: reddin sebebi uzaklık değil ROL olsun
  await A.go(R.tiny, A.SPOT.wires); await A.go(R.pointer, [P.ducks.spots[P.ducks.gold[0]][0], 5, P.ducks.spots[P.ducks.gold[0]][2]]); await A.go(host, A.SPOT.keypad); await A.go(R.defuser, A.SPOT.fuse);
  await R.tiny.act('cut', { i: wrongWire });         // MİNİK kablo kesemez (kabul edilse: hata + kesik kablo)
  await R.defuser.act('fuse', { i: 0 });             // sigorta YERÇEKİMSİZ'in
  await R.pointer.act('duck', { i: P.ducks.gold[0] });
  await R.defuser.act('laser', { i: P.laserSeq[0] });// eski "laser" aksiyonu artık yok: lazer kilidini oda sahibi lazer noktasından algılar
  await R.defuser.tb((T, p) => T.laser(p), [-9, 3.7, -9.92]);   // İŞARETÇİ olmayanın lazeri sayılmaz (yanlış sensör olsa −6 sn cezası gelirdi)
  await host.act('key', { i: P.layout.indexOf(P.order[0]) });   // oda sahibi (TERS SES) de sembole basamaz
  await t.sleep(1000); await R.defuser.tb(T => T.laser(false));
  // sıra garantisi: aynı kanallardan SONRA yollanan geçerli aksiyonlar işlendiyse öncekiler de işlenmiştir
  await A.go(R.tiny, A.SPOT.mouse); await A.go(R.defuser, A.SPOT.password);
  await R.tiny.act('dial', { i: 0 }); await R.defuser.act('pw', { c: 0, d: 1 });
  await R.pointer.tb((T, i) => T.laser(T.LSR[i].p.slice()), P.laserSeq[0]);
  await H.waitAll(clients, st => { const g = window.__tb.game; return g.mouseDial[0] === 1 && g.laserProg === 1 && g.pwIdx[0] === (st + 1) % 5; }, 10000, P.pw.start[0]);
  await R.pointer.tb(T => T.laser(false));
  t.eq('yetkisiz aksiyonlar durumu değiştirmedi (hata yok, kablo/sigorta/ördek/sembol aynı)', { ...(await snap()), laserProg: 0 }, before);
  await checkpoint('yanlış rol sonrası');

  t.step('her modülü yetkili rol çözer; 5 istemci de çözüldüğünü görür');
  for (const mod of P.mods) {
    await H.solveModule(R, mod, P);
    const ok = await H.waitAll(clients, m => window.__tb.game.solved[m] === true, 10000, mod).then(() => true, e => e.message);
    t.check(`${mod} çözüldü → 5/5 istemci gördü`, ok === true, ok);
    if (mod === 'password' || mod === 'maze') await checkpoint(`${mod} sonrası`);
  }
  s = await checkpoint('tüm modüller sonrası');
  t.check('tüm modüller çözük, 0 hata, final başladı, oyun sürüyor', s && s.status === 'playing' && s.strikes === 0 && Object.values(s.solved).every(Boolean) && !!s.final, s);

  t.step('final: 4 kişi plakada → bomba beklemeli');
  const four = clients.filter(c => c !== R.tiny);
  await R.tiny.moveTo([0, 0, 8.5], { pin: true });   // MİNİK kendi plakasından uzakta
  await H.toPlates(four);
  await H.waitAll(clients, () => window.__tb.game.final.on.length === 4, 10000);
  await t.sleep(2200);                               // 1.5 sn'lik bekleme süresinden uzun
  s = await checkpoint('4/5 plakada');
  t.check('biri eksikken kazanılmıyor', s && s.status === 'playing' && s.final.on.length === 4 && !s.final.on.includes('tiny'), s);

  t.step('final: 5. kişi de plakada → kazanıldı');
  await H.toPlates([R.tiny]);
  const won = await H.waitAll(clients, () => window.__tb.game.status === 'won', 15000).then(() => true, e => e.message);
  t.check('5/5 istemci status === won', won === true, won);
  const end = await H.waitAll(clients, () => !document.querySelector('#endScreen').classList.contains('hidden'), 15000).then(() => true, e => e.message);
  t.check('5/5 istemcide bitiş ekranı açık', end === true, end);
  for (const c of clients) t.eq(`${c.name}: bitiş başlığı`, await c.page.textContent('#endTitle'), 'İMHA EDİLDİ');
  t.check('"Yeni Bomba" düğmeleri yalnızca oda sahibinde', await host.page.isVisible('#endHostBtns') && !(await R.tiny.page.isVisible('#endHostBtns')) && await R.tiny.page.isVisible('#endWait'));
  s = await checkpoint('bitiş');
  t.check('bitiş: won, 0 hata', s && s.status === 'won' && s.strikes === 0 && s.screen === 'end', s);
  await host.shot('smoke-5p-end-host.png'); await R.tiny.shot('smoke-5p-end-tiny.png');
  t.noErrors(clients);
}, { timeout: 360000 });
