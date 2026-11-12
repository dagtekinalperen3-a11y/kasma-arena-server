'use strict';
// Ses sırası (5 istemci): aynı anda 3 kayıt → herkes tek tek ve aynı sırada duyar; ACİL öne geçer; konuşan başına tek bekleyen;
// bayat klip düşer; söz (İŞARETÇİ) önceliği + kendiliğinden bitiş + İŞARETÇİ ayrılınca silinme; Telsiz işareti; yeni turda temizlik.
const H = require('../harness');

// sayfada WAV üretip gerçek gönderme yolundan (sendClip → oda sahibi) yollar
const send = (c, dur, o = {}) => c.page.evaluate(([dur, o]) => {
  const sr = 8000, n = Math.round(sr * dur), b = new ArrayBuffer(44 + n * 2), v = new DataView(b), W = (p, s) => [...s].forEach((ch, i) => v.setUint8(p + i, ch.charCodeAt(0)));
  W(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); W(8, 'WAVEfmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, sr, true); v.setUint32(28, sr * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); W(36, 'data'); v.setUint32(40, n * 2, true);
  for (let i = 0; i < n; i++) v.setInt16(44 + i * 2, Math.sin(i / sr * 2 * Math.PI * (o.hz || 330)) * 32767 * (o.amp || 0.2), true);
  return window.__tb.voice.send(b, { urgent: !!o.urgent });
}, [dur, o]);
const vs = c => c.tb(T => { const s = T.voice.state(); return { floor: s.floor ? s.floor.id : null, q: s.q.map(e => e.from), rec: Object.keys(s.rec), hands: Object.keys(s.hands), playing: s.playing ? s.playing.id : null, ducked: s.ducked, noMic: Object.keys(s.noMic) }; });
const log = c => c.tb(T => T.voiceLog.map(L => ({ id: L.id, sp: L.speaker, start: L.start, end: L.end, f: L.flags })));
const hostLog = c => c.tb(T => T.voice.hv.log.slice());

H.run('voice-queue', async t => {
  t.step('5 kişilik oda, Telsiz Disiplini açık');
  const room = await H.party(5), { clients, host, byRole: R } = room;
  await H.startGame(host, { diff: 'kolay', muts: ['telsiz'] });
  const id = {}; for (const r of H.ROLES) id[r] = await R[r].tb(T => T.net.peer.id);
  const nm = x => Object.keys(id).find(r => id[r] === x) || x;
  const waitLogs = (n, ms = 30000) => H.waitAll(clients, n => window.__tb.voiceLog.length >= n && window.__tb.voiceLog.every(L => L.end > 0), ms, n);
  let base = 0;
  const since = async c => (await log(c)).slice(base);

  t.step('1) üç kişi aynı anda V ile kaydediyor (sahte mikrofon)');
  const speakers = [R.reader, R.defuser, R.tiny];
  await Promise.all(speakers.map(c => c.page.keyboard.down('KeyV')));
  await t.sleep(700);
  const mid = await vs(R.floater);
  t.eq('kayıt sırasında 3 kırmızı mikrofon işareti (YERÇEKİMSİZ ekranı)', mid.rec.slice().sort(), [id.reader, id.defuser, id.tiny].sort());
  t.check('oyuncu listesinde .vm.rec işareti', await R.floater.page.locator('#players .vm.rec').count() === 3);
  await t.sleep(600);
  await Promise.all(speakers.map(c => c.page.keyboard.up('KeyV')));
  await waitLogs(3);
  const L0 = await Promise.all(clients.map(c => since(c)));
  const order = L0[0].map(e => e.id).join();
  t.check('5 istemcinin hepsi aynı 3 klibi aynı sırada çaldı', L0.every(L => L.length === 3 && L.map(e => e.id).join() === order), L0.map(L => L.map(e => e.id)));
  let overlap = 0, minGap = 1e9, maxGap = 0;
  for (const L of L0) for (let i = 1; i < L.length; i++) { const g = L[i].start - L[i - 1].end; if (g < 0) overlap++; minGap = Math.min(minGap, g); maxGap = Math.max(maxGap, g); }
  t.check('hiçbir istemcide klipler üst üste binmedi', overlap === 0, { minGap });
  t.log(`klipler arası boşluk: en az ${minGap} ms, en çok ${maxGap} ms · süreler(ms): ${L0[2].map(e => e.end - e.start).join(', ')} · kazançlar: ${L0[2].map(e => e.f.gain).join(', ')}`);
  const fl = L0[2]; // YERÇEKİMSİZ hepsini duyar
  t.check('TERS SES klibi ters, diğerleri düz', fl.every(e => e.f.rev === (e.sp === id.reader)), fl);
  t.check('MİNİK klibi ×1.35, diğerleri ×1', fl.every(e => e.f.rate === (e.sp === id.tiny ? 1.35 : 1)), fl.map(e => e.f.rate));
  t.check('konuşan kendi klibini "self" olarak görür (ses geri yollanmaz)', L0[0].find(e => e.sp === id.reader).f.self === true && fl.every(e => !e.f.self));
  t.check('kazanç tavanı: her klip ≤ 8', fl.every(e => e.f.gain > 0 && e.f.gain <= 8));
  t.check('sıra boşalınca kısma kalktı', await R.floater.waitFor(() => !window.__tb.voice.state().ducked, 3000).catch(() => false));
  base += 3;

  t.step('2) ACİL öne geçer, ikinci ACİL bekleme süresine takılır');
  await send(R.floater, 2.5); await t.sleep(350);
  await send(R.defuser, 0.6); await t.sleep(150);
  await send(R.tiny, 0.6, { urgent: true });
  await t.sleep(250);
  t.eq('bekleyenler: önce ACİL (MİNİK), sonra TERS TUŞ', (await vs(R.pointer)).q.map(nm), ['tiny', 'defuser']);
  t.check('klip çalarken müzik/efekt kısıldı', await R.pointer.tb(T => { const m = T.voice.mix(); return m.ducked && Math.abs(m.sfx - 0.6) < 0.02 && Math.abs(m.music - m.baseMusic * 0.35) < 0.01; }), await R.pointer.tb(T => T.voice.mix()));
  await waitLogs(base + 3);
  let L = await since(R.pointer);
  t.eq('çalma sırası: YERÇEKİMSİZ, MİNİK(ACİL), TERS TUŞ', L.map(e => nm(e.sp)), ['floater', 'tiny', 'defuser']);
  t.check('ACİL işareti yalnızca MİNİK klibinde', L.map(e => e.f.urgent).join() === 'false,true,false');
  base += 3;
  await send(R.tiny, 0.4, { urgent: true });
  await waitLogs(base + 1);
  t.check('25 sn dolmadan ikinci ACİL normal klibe düşer', (await since(R.pointer))[0].f.urgent === false && await R.tiny.tb(T => { const a = T.voice.vc.stats.acks; return a[a.length - 1].urgent === false && T.voice.vc.urgentAt > performance.now() + 15000; }));
  t.check('kısma tam eski değerine döndü', await R.pointer.waitFor(() => { const m = window.__tb.voice.mix(); return !m.ducked && m.sfx === 1 && Math.abs(m.music - m.baseMusic) < 1e-6; }, 3000).catch(() => false), await R.pointer.tb(T => T.voice.mix()));
  base += 1;

  t.step('3) konuşan başına tek bekleyen + 6 sn bekleyen düşer');
  await send(R.floater, 7.0); await t.sleep(120);
  const t0 = Date.now();
  await send(R.reader, 0.5);                       // 6 sn'den fazla bekleyecek → bayat
  await send(R.defuser, 0.5); await t.sleep(1500);
  await send(R.defuser, 0.5);                      // öncekinin yerini alır, bekleme süresi yeniden başlar
  await R.reader.waitFor(() => window.__tb.voice.vc.stats.drops.some(d => d.why === 'bayat'), 12000).catch(() => {});
  const staleMs = Date.now() - t0;
  t.check('TERS SES\'e "bayat" bildirimi geldi', await R.reader.tb(T => T.voice.vc.stats.drops.filter(d => d.why === 'bayat').length === 1));
  t.log(`bayat klip ${staleMs} ms bekledikten sonra düştü (sınır 6000)`);
  t.check('bayatlama 6–7 sn arasında', staleMs >= 5900 && staleMs < 7200, staleMs);
  t.check('TERS TUŞ\'a "yenisi" bildirimi geldi', await R.defuser.tb(T => T.voice.vc.stats.drops.filter(d => d.why === 'yenisi').length === 1));
  t.check('bildirim sağ altta göründü', await R.reader.page.locator('#vNotes .note.bad').count() >= 1);
  await waitLogs(base + 2);
  L = await since(R.pointer);
  t.eq('yalnızca 2 klip çaldı: YERÇEKİMSİZ ve TERS TUŞ\'un son kaydı', L.map(e => nm(e.sp)), ['floater', 'defuser']);
  base += 2;

  t.step('4) söz: İŞARETÇİ verir, öncelik sağlar, 8 sn sonra biter');
  await R.defuser.tb((T, id) => T.act({ t: 'voice', k: 'floor', id }), id.tiny);
  await t.sleep(400);
  t.eq('İŞARETÇİ olmayan söz veremez', (await vs(host)).floor, null);
  t.check('nişan hesabı: lazer MİNİK\'in üstünde → MİNİK', await R.pointer.tb((T, id) => { const p = T.players()[id].p; return !!p && T.voice.aimPlayer([p[0] + 0.1, p[1] + 0.3, p[2]]) === id && T.voice.aimPlayer([p[0] + 3, 5, p[2]]) === null; }, id.tiny));
  const f0 = Date.now();
  await R.pointer.tb((T, id) => T.voice.giveFloor(id), id.tiny);
  await H.waitAll(clients, id => { const f = window.__tb.voice.state().floor; return !!f && f.id === id; }, 3000, id.tiny);
  t.check('söz çipi herkesin ekranında', (await Promise.all(clients.map(c => c.page.locator('#vFloor:not(.hidden)').count()))).every(n => n === 1));
  t.check('MİNİK ekranında "SENDE", listede söz işareti', await R.tiny.page.locator('#vFloor.me').count() === 1 && await R.reader.page.locator('#players .vm.flr').count() === 1);
  await send(R.floater, 2.0); await t.sleep(300);
  await send(R.defuser, 0.5); await t.sleep(150);
  await send(R.tiny, 0.5);
  await waitLogs(base + 3);
  L = await since(R.pointer);
  t.eq('söz sahibi (MİNİK) sırada öne geçti', L.map(e => nm(e.sp)), ['floater', 'tiny', 'defuser']);
  t.check('işaretler: söz yalnızca MİNİK\'te, telsiz yalnızca araya girenlerde', L.map(e => `${e.f.floor}/${e.f.telsiz}`).join() === 'false/true,true/false,false/true', L.map(e => e.f));
  base += 3;
  await host.waitFor(() => !window.__tb.voice.state().floor, 12000);
  const floorMs = Date.now() - f0;
  t.log(`söz ${floorMs} ms sonra kendiliğinden bitti (ayar 8000)`);
  t.check('söz 8 sn civarında bitti', floorMs > 7400 && floorMs < 9500, floorMs);
  await send(R.defuser, 0.4); await waitLogs(base + 1);
  t.check('söz yokken telsiz efekti yok', (await since(R.pointer))[0].f.telsiz === false);
  base += 1;

  t.step('5) söz iste (9)');
  await R.defuser.page.keyboard.press('Digit9');
  await H.waitAll(clients, id => window.__tb.voice.state().hands[id] > performance.now(), 3000, id.defuser);
  t.check('listede ✋ işareti', await R.reader.page.locator('#players .vm.hand').count() === 1);
  t.check('avatarda baloncuk', await R.reader.tb((T, id) => T.avatars[id].bubble.visible || T.avatars[id].bubbleUntil > performance.now(), id.defuser));

  t.step('6) İŞARETÇİ konuşamaz; bozuk paketler yok sayılır');
  await send(R.pointer, 0.5);
  await R.pointer.waitFor(() => window.__tb.voice.vc.stats.drops.some(d => d.why === 'isaretci'), 3000).catch(() => {});
  t.check('İŞARETÇİ\'nin klibi reddedildi', await R.pointer.tb(T => T.voice.vc.stats.drops.some(d => d.why === 'isaretci')));
  await R.defuser.tb(T => { for (const m of [{ t: 'voice' }, { t: 'voice', k: 'clip', data: 5 }, { t: 'voice', k: 'clip', data: '<script>'.repeat(60) }, { t: 'voice', k: 'floor', id: '__proto__' }, { t: 'voice', k: 'part', n: 7, i: 0, data: 'A'.repeat(12001) }, { t: 'voice', k: 'part', n: 1, i: 5, data: 'AAAA' }, { t: 'voice', k: 42 }]) T.act(m); });
  await t.sleep(500);
  t.check('bozuk paketlerden sonra sıra boş, kimse çalmıyor', await host.tb(T => T.voice.hv.q.length === 0 && !T.voice.hv.cur));

  t.step('7) İŞARETÇİ ayrılınca söz silinir');
  await R.pointer.tb((T, id) => T.voice.giveFloor(id), id.reader);
  await host.waitFor(() => !!window.__tb.voice.state().floor, 3000);
  const g0 = Date.now();
  await R.pointer.tb(T => T.net.hostConn.close());
  await H.waitAll([host, R.defuser, R.floater, R.tiny], () => !window.__tb.voice.state().floor, 6000);
  t.log(`İŞARETÇİ koptuktan ${Date.now() - g0} ms sonra söz silindi`);
  t.check('söz 8 sn dolmadan silindi (ayrılma nedeniyle)', Date.now() - g0 < 5000);

  t.step('8) lobiye dönüş / yeni tur: çalan klip durur, sıra boşalır');
  const rest = [host, R.defuser, R.floater, R.tiny];
  const b2 = (await log(R.tiny)).length;
  await send(R.floater, 6.0); await t.sleep(600);
  await send(R.defuser, 1.0); await t.sleep(400);
  t.check('bir klip çalıyor, biri bekliyor', await R.tiny.tb(T => !!T.voice.state().playing && T.voice.state().q.length === 1));
  const s0 = Date.now();
  await host.tb(T => T.toLobby());
  await H.waitAll(rest, () => { const s = window.__tb.voice.state(); return !s.playing && !s.q.length && !s.ducked; }, 4000);
  const stopMs = Date.now() - s0;
  L = (await log(R.tiny)).slice(b2);
  t.log(`lobiye dönüşten ${stopMs} ms sonra tüm istemcilerde ses durdu; klip ${L[0].end - L[0].start} ms çalmıştı (tam süre 6000)`);
  t.check('çalan klip yarıda kesildi (stopped işareti)', L.length === 1 && !!L[0].f.stopped && L[0].end - L[0].start < 3000, L);
  t.check('oda sahibinde sıra, çalan klip ve söz boş', await host.tb(T => T.voice.hv.q.length === 0 && !T.voice.hv.cur && !T.voice.hv.floor));
  await t.sleep(1500);
  t.eq('bekleyen klip sonradan da çalmadı', (await log(R.tiny)).length, b2 + 1);
  const HL = await hostLog(host);
  t.log(`oda sahibi kaydı: ${HL.filter(e => !e.drop).length} klip çaldırıldı, ${HL.filter(e => e.drop).length} klip düşürüldü; en uzun bekleme ${Math.max(...HL.filter(e => !e.drop).map(e => e.waited))} ms`);
  t.noErrors(rest);
});
