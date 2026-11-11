'use strict';
// PKG-A / A1: şart roller (TERS SES, TERS TUŞ, YERÇEKİMSİZ) dolmadan tur başlatılamaz; lobi hangi rolün eksik olduğunu söyler.
const H = require('../harness');

H.run('a-start-gate', async t => {
  t.step('2 kişi: oda sahibi reader, diğeri defuser → YERÇEKİMSİZ boş');
  const { clients, host, infra, browser, code } = await H.party(2, ['reader', 'defuser']);
  const st = () => host.eval(() => ({ dis: document.querySelector('#btnStart').disabled, txt: document.querySelector('#lobbyStatus').textContent, miss: window.__tb.missingRoles() }));
  let s = await st();
  t.eq('eksik rol listesi', s.miss, ['floater']);
  t.check('Başlat düğmesi kapalı', s.dis === true, s);
  t.check('lobi metni eksik rolü adıyla söylüyor', /YERÇEKİMSİZ/.test(s.txt) && !/TERS TUŞ/.test(s.txt), s.txt);
  t.check('misafir de eksik rolü görüyor', /YERÇEKİMSİZ/.test(await clients[1].page.textContent('#lobbyStatus')));
  t.eq('hostStart() reddediyor', await host.tb('T.hostStart()'), false);
  await t.sleep(400);
  t.check('oyun başlamadı (iki istemcide de)', (await host.state()).screen === 'lobby' && (await clients[1].state()).screen === 'lobby');
  t.check('onay penceresi çıkmadı', host.dialogs.length === 0, host.dialogs);

  t.step('misafir izleyici olursa iki şart rol eksik');
  await H.setRole(clients[1], 'none');
  await host.waitFor(() => window.__tb.missingRoles().length === 2, 5000);
  s = await st();
  t.eq('eksik: defuser + floater', s.miss.slice().sort(), ['defuser', 'floater']);
  t.check('düğme hâlâ kapalı', s.dis === true);

  t.step('3. kişi gelir, roller dolar → başlatılabilir');
  await H.setRole(clients[1], 'defuser');
  const c3 = await H.newClient(browser, infra, { name: '3-floater' });
  await H.joinRoom(c3, code);
  await H.setRole(c3, 'floater');
  await host.waitFor(() => window.__tb.missingRoles().length === 0, 5000);
  s = await st();
  t.check('düğme açıldı', s.dis === false, s);
  const P = await H.startGame(host, { diff: 'normal' });
  t.check('3 kişilik tur başladı', (await host.state()).status === 'playing');
  t.check('3 rolde fare paneli ve lazer yok, labirent var', !P.mods.includes('mouse') && !P.mods.includes('laser') && P.mods.includes('maze'), P.mods);
  t.eq('3 rolde bilgi sahipleri (sembol: floater, ördek: reader)', [P.keypadInfo, P.duckInfo], ['floater', 'reader']);

  t.step('antrenman (tek kişi) muaf');
  const solo = await H.newClient(browser, infra, { name: 'Solo' });
  await H.soloRoom(solo);
  t.eq('antrenmanda eksik rol yok', await solo.tb('T.missingRoles()'), []);
  t.check('antrenmanda düğme açık', !(await solo.eval(() => document.querySelector('#btnStart').disabled)));
  t.noErrors();
});
