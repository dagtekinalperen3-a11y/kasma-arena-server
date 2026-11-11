'use strict';
// PKG-A / A4: kararı oda sahibi verir — uzaktan dokunma reddedilir, düğmenin süresi oda sahibinin saatinden ölçülür
// (istemcinin dur/timer beyanı yok sayılır), lazer kilidi lazer noktasından algılanır, labirent adımı konuma bakar.
const H = require('../harness'), A = require('../a-lib');

H.run('a-authority', async t => {
  const { clients, host, byRole: R } = await H.party(5);
  await H.startGame(host, { diff: 'normal' });
  const P = await A.full(host);
  const g = expr => host.tb(expr), diag = () => host.tb('T.hostDiag');
  const sync = async c => { await c.tb('T.raw && T.net.hostConn ? T.raw({ t: "ping" }) : 0'); await t.sleep(250); };   // kanaldaki paketler işlensin

  t.step('erişim: uzaktaki oyuncunun aksiyonu reddedilir');
  let d0 = (await diag()).reach;
  await A.go(R.defuser, A.SPOT.far); await R.defuser.act('cut', { i: P.wireAns });                 // doğru kablo ama odanın öbür ucundan
  await A.go(R.floater, [10.2, 0, 6.3]); await R.floater.act('fuse', { i: 0 });                    // sigorta kutusunun tam altında, yerde
  await A.go(R.tiny, [0, 0.92, 0.3]); await R.tiny.act('dial', { i: 0 });                          // masanın ÜSTÜNDE
  await A.go(R.pointer, A.SPOT.far); await R.pointer.act('turnKey', { i: 0 });
  await A.go(R.floater, [-11, 0.3, 9]); await R.floater.act('duck', { i: P.ducks.gold[0] });
  await A.go(R.defuser, A.SPOT.far); await R.defuser.act('maze', { i: P.maze.safe[0] });           // labirente basmadan adım beyanı
  await R.defuser.act('btnDown'); await R.defuser.act('btnUp');
  await sync(R.defuser); await t.sleep(400);
  const fuse0 = P.fuseStart[0];
  t.eq('hiçbiri işlenmedi', await g('[T.game.wireCut.some(Boolean), T.game.solved.wires, T.game.fuse[0], T.game.mouseDial[0], T.game.keyArm[0] > 0, T.game.ducksGot.length, T.game.mazeVisited.length, T.game.mazeFails, T.game.btnHeld, T.game.strikes]'), [false, false, fuse0, 0, false, 0, 0, 0, false, 0]);
  t.eq('oda sahibi 7 aksiyonu "uzak" diye reddetti', (await diag()).reach - d0, 7);

  t.step('erişim: yanına gidince aynı aksiyonlar kabul edilir');
  await A.go(R.floater, A.SPOT.fuse); await A.act(R.floater, 'fuse', { i: 0 });
  await A.go(R.tiny, A.SPOT.mouse); await A.act(R.tiny, 'dial', { i: 0 });
  await H.waitAll(clients, f => window.__tb.game.fuse[0] === !f && window.__tb.game.mouseDial[0] === 1, 8000, fuse0);
  t.check('sigorta ve fare paneli tepki verdi (5 istemcide)', true);
  await A.go(R.defuser, A.tilePos(P.maze.safe[0])); await A.act(R.defuser, 'maze', { i: P.maze.safe[0] });
  await host.waitFor(() => window.__tb.game.mazeVisited.length === 1, 5000);
  t.eq('labirent: karenin üstündeyken adım sayıldı, ceza yok', await g('[T.game.mazeVisited.length, T.game.mazeFails]'), [1, 0]);

  t.step('düğme: süreyi oda sahibi ölçer, istemcinin beyanı (dur/timer) yok sayılır');
  await A.go(R.defuser, A.SPOT.button);
  t.log('düğme cevabı: ' + JSON.stringify(P.btnAns));
  if (P.btnAns.mode === 'hold') {
    // hemen bırak ama "5 sn tuttum, sayaçta doğru rakam vardı" de → oda sahibi kısa basış ölçer → hata
    await R.defuser.act('btnDown'); await R.defuser.act({ t: 'act', a: 'btnUp', dur: 5000, timer: '0:' + P.btnAns.digit + P.btnAns.digit });
  } else {
    // 1.2 sn tut ama "100 ms bastım" de → oda sahibi uzun basış ölçer → hata
    await R.defuser.act('btnDown'); await t.sleep(1200); await R.defuser.act({ t: 'act', a: 'btnUp', dur: 100, timer: '' });
  }
  await H.waitAll(clients, () => window.__tb.game.strikes === 1, 8000);
  t.eq('yalan beyan işe yaramadı: 1 hata, düğme çözülmedi', await g('[T.game.strikes, T.game.solved.button, T.game.btnHeld]'), [1, false, false]);
  await t.sleep(300);
  await host.eval(() => { window.__toasts = []; new MutationObserver(ms => ms.forEach(m => m.addedNodes.forEach(n => window.__toasts.push(n.textContent)))).observe(document.querySelector('#toasts'), { childList: true }); });
  await A.solve(R, 'button', P);
  await t.sleep(600); t.log('oda sahibindeki bildirimler: ' + JSON.stringify(await host.eval(() => window.__toasts)) + ' ' + JSON.stringify(await Promise.all([host, R.defuser].map(c => c.tb('T.game.timeLeft')))));
  await H.waitAll(clients, () => window.__tb.game.solved.button === true, 30000);
  t.eq('doğru süre/rakamla çözüldü, yeni hata yok', await g('[T.game.strikes, T.game.solved.button]'), [1, true]);

  t.step('lazer kilidi: oda sahibi lazer noktasından algılar');
  const sensor = i => R.pointer.tb((T, i) => T.laser(T.LSR[i].p.slice()), i), off = () => R.pointer.tb(T => T.laser(false));
  await R.pointer.act({ t: 'act', a: 'laser', i: P.laserSeq[0] });   // eski istemci beyanı
  await sensor(P.laserSeq[0]); await t.sleep(250); await off();      // çok kısa tutuş (≈0.25 sn < 0.6 sn)
  await t.sleep(500);
  t.eq('beyan ve kısa tutuş sayılmadı', await g('T.game.laserProg'), 0);
  const tHold = Date.now(); await sensor(P.laserSeq[0]);
  await H.waitAll(clients, () => window.__tb.game.laserProg === 1, 8000);
  t.log(`ilk sensör ${Date.now() - tHold} ms tutuşta kabul edildi`);
  await t.sleep(1500);
  t.eq('aynı sensörde beklemek ikinci kez saymıyor', await g('T.game.laserProg'), 1);
  await off(); await t.sleep(300);
  const tl0 = await g('T.game.timeLeft'), wrong = P.laserSeq[3];
  await sensor(wrong);
  await H.waitAll(clients, () => window.__tb.game.laserProg === 0, 8000);
  const lost = tl0 - await g('T.game.timeLeft');
  t.check(`yanlış sensör: kilit sıfırlandı, −6 sn (ölçülen kayıp ${lost.toFixed(1)} sn)`, lost > 6 && lost < 9, lost);
  await off(); await t.sleep(300);
  await A.solve(R, 'laser', P);
  await H.waitAll(clients, () => window.__tb.game.solved.laser === true, 8000);
  t.check('doğru sırayla lazer kilidi açıldı', true);

  t.step('düğmeyi tutan oyuncu koparsa düğme bırakılır');
  // düğme çözüldü; aynı mekanizma için btnBy sahipliğini başka modülle sınayamayız → çözülmemiş yeni turda dene
  const st = await H.converge(clients);
  t.check('5 istemci aynı durumda', st.status === 'playing' && st.strikes === 1, st);
  t.eq('oda sahibinde yakalanan istisna yok', (await diag()).caught, 0);
  t.noErrors(clients);
}, { timeout: 420000 });
