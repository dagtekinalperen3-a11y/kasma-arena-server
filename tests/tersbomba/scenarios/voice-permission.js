'use strict';
// Mikrofon izni ve yerel ses: izin yok (oyun sürer, işaret görünür), geç gelen izin yarışı (V erken bırakılırsa kayıt başlamaz),
// laboratuvar (lobi), antrenmanda prova yerel kalır, rol değişince ses durur, hız sınırı 1.6, ses yüksekliği eşitleme.
const H = require('../harness');

// getUserMedia'yı test "izin ver" diyene kadar bekletir (izin penceresi açık kalmış gibi)
const gate = () => {
  const md = navigator.mediaDevices, real = md.getUserMedia.bind(md);
  let open; const p = new Promise(r => { open = r; });
  window.__micOpen = open; window.__micCalls = 0;
  md.getUserMedia = c => { window.__micCalls++; return p.then(() => real(c)); };
};
const hold = async (c, key, ms) => { await c.page.keyboard.down(key); await H.sleep(ms); await c.page.keyboard.up(key); };

H.run('voice-permission', async t => {
  t.step('3 kişi: TERS SES (mikrofon var), TERS TUŞ (izin yok), YERÇEKİMSİZ (izin penceresi açık kalıyor)');
  const room = await H.party(3, null, { clients: [{}, { mic: false }, { initScripts: [gate] }] }), { clients, host, byRole: R } = room;
  const id = {}; for (const r of ['reader', 'defuser', 'floater']) id[r] = await R[r].tb(T => T.net.peer.id);

  t.step('lobi: mikrofonsuz oyuncu bildirilir, laboratuvar çalışır');
  await H.waitAll(clients, id => !!window.__tb.voice.state().noMic[id], 5000, id.defuser);
  t.check('izin vermeyen kendi lobisinde açık bir mesaj görür', await R.defuser.page.evaluate(() => { const el = document.querySelector('#micNote'); return !el.classList.contains('hidden') && /Mikrofon izni verilmedi/.test(el.textContent) && /Oyun devam eder/.test(el.textContent); }));
  t.check('diğerleri kimin mikrofonsuz olduğunu görür', await host.page.evaluate(() => /Mikrofonu olmayanlar: 2-defuser/.test(document.querySelector('#micNote').textContent)));
  await host.page.click('#btnLab');
  const box = await host.page.locator('#labRec').boundingBox();
  await host.page.mouse.move(box.x + 20, box.y + 10); await host.page.mouse.down(); await t.sleep(900); await host.page.mouse.up();
  await host.waitFor(() => window.__tb.voiceLog.length === 1 && window.__tb.voiceLog[0].end > 0, 8000);
  await host.page.click('#labFwd');
  await host.waitFor(() => window.__tb.voiceLog.length === 2 && window.__tb.voiceLog[1].end > 0, 8000);
  const lab = await host.tb(T => T.voiceLog.map(L => ({ ...L.flags, ms: L.end - L.start })));
  t.check('laboratuvar: önce ters, sonra tersin tersi (düz) çaldı; ikisi de yerel', lab[0].local === 'lab' && lab[0].rev === true && lab[1].local === 'lab' && lab[1].rev === false, lab);
  t.eq('laboratuvar kaydı oda sahibine gitmedi', await host.tb(T => [T.voice.vc.stats.sent, T.voice.hv.log.length]), [0, 0]);
  await host.page.click('#labModal [data-close]');

  t.step('oyun: izin yok → tek açık mesaj, işaret, oyun sürer');
  await H.startGame(host, { diff: 'kolay' });
  await hold(R.defuser, 'KeyV', 300); await t.sleep(300);
  const n1 = await R.defuser.page.evaluate(() => [...document.querySelectorAll('#vNotes .note')].map(d => d.textContent));
  t.check('ilk V: tam açıklama (bir kez)', n1.length === 1 && /Mikrofon izni verilmedi/.test(n1[0]) && /kilit simgesinden/.test(n1[0]), n1);
  await hold(R.defuser, 'KeyV', 300); await t.sleep(300);
  const n2 = await R.defuser.page.evaluate(() => [...document.querySelectorAll('#vNotes .note')].map(d => d.textContent));
  t.check('ikinci V: uzun mesaj yinelenmez, kısa uyarı gelir', n2.length === 2 && /kayıt alınamadı/.test(n2[1]), n2);
  t.check('herkesin listesinde "mikrofon yok" işareti', (await Promise.all(clients.map(c => c.page.locator('#players .vm.nomic').count()))).every(n => n === 1));
  t.eq('mikrofonsuz istemci kayıt başlatmadı, klip yollamadı', await R.defuser.tb(T => [T.voice.state().recording, T.voice.vc.stats.recs, T.voice.vc.stats.sent]), [false, 0, 0]);

  t.step('izin yarışı: izin penceresi açıkken V bırakılırsa kayıt başlamaz');
  t.eq('YERÇEKİMSİZ: izin isteği hâlâ bekliyor', await R.floater.tb(T => T.voice.state().mic), '');
  await R.floater.page.keyboard.down('KeyV'); await t.sleep(300);
  t.check('beklerken "izin bekleniyor" kutusu', await R.floater.page.evaluate(() => { const r = document.querySelector('#rec'); return !r.classList.contains('hidden') && r.classList.contains('wait') && /izni bekleniyor/.test(r.textContent); }));
  await R.floater.page.keyboard.up('KeyV');
  t.check('bırakınca kutu kapandı', await R.floater.page.evaluate(() => document.querySelector('#rec').classList.contains('hidden')));
  await R.floater.page.evaluate(() => window.__micOpen());
  await R.floater.waitFor(() => window.__tb.voice.state().mic === 'ok', 5000);
  await t.sleep(800);
  t.eq('izin geldi ama kayıt BAŞLAMADI (recording, kayıt sayısı, gönderilen)', await R.floater.tb(T => [T.voice.state().recording, T.voice.state().wanting, T.voice.vc.stats.recs, T.voice.vc.stats.sent]), [false, false, 0, 0]);
  t.eq('tek getUserMedia çağrısı (lobi + V aynı isteği bekledi)', await R.floater.page.evaluate(() => window.__micCalls), 1);
  const b0 = await R.defuser.tb(T => T.voiceLog.length);
  await hold(R.floater, 'KeyV', 900);
  await H.waitAll(clients, n => window.__tb.voiceLog.length > n && window.__tb.voiceLog.every(L => L.end > 0), 10000, b0 + (0));
  t.eq('izin varken V normal çalışır: 1 kayıt, 1 klip', await R.floater.tb(T => [T.voice.vc.stats.recs, T.voice.vc.stats.sent]), [1, 1]);
  t.check('mikrofonsuz oyuncu klibi duydu (oyun onun için de sürüyor)', await R.defuser.tb((T, id) => { const L = T.voiceLog[T.voiceLog.length - 1]; return L.speaker === id && !L.flags.self && !L.flags.error && T.game.status === 'playing'; }, id.floater));
  await R.defuser.page.keyboard.press('Digit6');
  t.check('mikrofonsuz oyuncu hareketle anlatabiliyor', await host.waitFor(id => { const a = window.__tb.avatars[id]; return !!a && !!a.emote; }, 3000, id.defuser).catch(() => false));
  t.noErrors(clients);
  for (const c of clients) await c.close();

  t.step('antrenman: prova yerel, V kendi klibini çaldırır, rol değişince ses durur');
  const c = await H.newClient(room.browser, room.infra, { name: 'Solo' });
  await H.soloRoom(c);
  await H.startGame(c, { diff: 'kolay', muts: ['helyum'] });
  await c.tb(T => T.setRole('reader'));
  await t.sleep(300);
  await hold(c, 'KeyB', 800);
  await c.waitFor(() => window.__tb.voiceLog.length === 1 && window.__tb.voiceLog[0].end > 0, 8000);
  t.check('prova: yerel, ters, helyumlu (×1.45)', await c.tb(T => { const f = T.voiceLog[0].flags; return f.local === 'prova' && f.rev && f.rate === 1.45; }), await c.tb(T => T.voiceLog[0].flags));
  t.eq('prova oda sahibine gitmedi (gönderilen, sıra kaydı)', await c.tb(T => [T.voice.vc.stats.sent, T.voice.hv.log.length]), [0, 0]);
  t.eq('hız: düz 1.45, MİNİK+helyum 1.6 (çarpım 1.96 sınırlandı)', await c.tb(T => [T.voice.rate('reader'), T.voice.rate('tiny')]), [1.45, 1.6]);
  await c.tb(T => T.setRole('tiny')); await t.sleep(300);
  await hold(c, 'KeyV', 2500);
  await c.waitFor(() => window.__tb.voiceLog.length === 2, 8000);
  await t.sleep(400);
  const r0 = Date.now();
  await c.page.keyboard.press('Tab');
  await c.waitFor(() => !window.__tb.voice.state().playing, 3000);
  const L = await c.tb(T => { const L = T.voiceLog[1]; return { ...L.flags, ms: L.end - L.start }; });
  t.log(`rol değişiminden ${Date.now() - r0} ms sonra ses durdu; klip ${L.ms} ms çalmıştı`);
  t.check('antrenmanda kendi klibin çalar (×1.6), rol değişince yarıda kesilir', L.self && L.rate === 1.6 && L.stopped === 'rol' && L.ms < 1400, L);
  await t.sleep(600);
  t.check('kısma kalktı, oda sahibinde çalan yok', await c.tb(T => !T.voice.mix().ducked && T.voice.mix().sfx === 1 && !T.voice.hv.cur));

  t.step('ses yüksekliği eşitleme (sentetik klipler)');
  const G = await c.tb(T => {
    const mk = (amp, sil) => { const b = new AudioBuffer({ length: 16000, sampleRate: 16000 }), d = b.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = (sil && i < 8000) ? 0 : Math.sin(i * 0.2) * amp; return b; };
    return [0.04, 0.2, 0.9, 0.0005].map(a => { const g = T.voice.clipGain(mk(a, true)); return { amp: a, gain: +g.gain.toFixed(3), outRms: +(g.rms * g.gain).toFixed(3), outPeak: +(g.peak * g.gain).toFixed(3) }; });
  });
  t.log('eşitleme: ' + JSON.stringify(G));
  t.check('kısık ve normal klip aynı hedefe gelir (0.16 ± 0.01), tepe ≤ 0.9', G.slice(0, 3).every(g => Math.abs(g.outRms - 0.16) < 0.01 && g.outPeak <= 0.9), G);
  t.check('sessiz klip yükseltilmez; kazanç 0.25–8 arasında', G[3].gain === 1 && G.every(g => g.gain >= 0.25 && g.gain <= 8), G);
  t.noErrors([c]);
});
