'use strict';
// Etkileşim hissi: vurgu çerçevesi (izinli sarı / izinsiz kırmızı), tıklama "pop"u, büyütülmüş dokunma alanı (hitPad).
const H = require('../harness');
const FAKE_LOCK = () => Object.defineProperty(document, 'pointerLockElement', { configurable: true, get: () => (window.__lock ? document.querySelector('canvas') : null) });
const frames = (c, n = 4) => c.eval(n => new Promise(r => { const f = () => (n-- > 0 ? requestAnimationFrame(f) : r()); f(); }), n);
// i. etkileşimli parçaya dist metre öteden, (dx, dy) metre kaydırarak nişan al
const aim = async (c, kind, i, off = [0, 0], dist = 1.4) => {
  await c.tb((T, [kind, i, off, dist]) => {
    const o = T.interactables().find(o => o.userData.kind === kind && !o.userData.pad && (i == null || o.userData.i === i)), w = new T.THREE.Vector3(); o.getWorldPosition(w);
    const eye = T.myRole() === 'tiny' ? 0.42 : 1.6, put = () => { T.me.pos.set(w.x - dist, w.y - eye + off[1], w.z + off[0]); T.me.vel.set(0, 0, 0); T.me.yaw = -Math.PI / 2; T.me.pitch = 0; };
    put(); window.__aimPut = put;
  }, [kind, i, off, dist]);
  await frames(c, 5);
};
const click = c => c.eval(() => { document.dispatchEvent(new MouseEvent('mousedown', { button: 0 })); document.dispatchEvent(new MouseEvent('mouseup', { button: 0 })); });

H.run('interact', async t => {
  const infra = await H.startInfra(), browser = await H.launchBrowser();
  const c = await H.newClient(browser, infra, { name: 'Dokun', initScripts: [FAKE_LOCK] });
  await H.soloRoom(c); await H.startGame(c, { diff: 'normal' });
  await c.tb(T => { T.game.chaosIn = 9999; T.setRole('floater'); });
  await c.eval(() => { window.__lock = true; document.dispatchEvent(new Event('pointerlockchange')); });
  // norender modunda çizim yok, dolayısıyla dünya matrisleri güncellenmez; ışın testi için her karede elle güncelle
  await c.eval(() => { const f = () => { if (window.__aimPut) window.__aimPut(); window.__tb.scene.updateMatrixWorld(); requestAnimationFrame(f); }; f(); });

  t.step('vurgu: izinli hedef');
  await aim(c, 'fuse', 2);
  let h = await c.tb(T => ({ ...T.hover(), cross: document.querySelector('#cross').className, hint: document.querySelector('#hint').textContent, hintOn: !document.querySelector('#hint').classList.contains('hidden') }));
  t.check('şaltere bakınca: sarı köşe çerçevesi, parça parlıyor, nişan halkası ve ipucu', h.kind === 'fuse' && h.mark && h.color === 0xf5b800 && h.em === 0x80680f && h.size > 0.2 && /on/.test(h.cross) && !/no/.test(h.cross) && h.hintOn && /Şalter/i.test(h.hint), h);

  t.step('tıklama: parça "pop" yapar, hamle gider, ölçek eski haline döner');
  const before = await c.tb(T => { const o = T.interactables().find(o => o.userData.kind === 'fuse' && o.userData.i === 2); return { fuse: T.game.fuse[2], s: o.scale.toArray() }; });
  const mid = await c.eval(() => { const T = window.__tb; document.dispatchEvent(new MouseEvent('mousedown', { button: 0 })); document.dispatchEvent(new MouseEvent('mouseup', { button: 0 })); return { pops: T.pops.length, fuse: T.game.fuse[2] }; });
  t.check('pop başladı ve şalter durumu değişti', mid.pops === 1 && mid.fuse === !before.fuse, mid);
  await t.sleep(400); await frames(c, 3);
  const after = await c.tb(T => { const o = T.interactables().find(o => o.userData.kind === 'fuse' && o.userData.i === 2); return { pops: T.pops.length, s: o.scale.toArray() }; });
  t.check('pop bitti, ölçek birebir aynı', after.pops === 0 && after.s.every((v, i) => Math.abs(v - before.s[i]) < 1e-9), { before: before.s, after });

  t.step('büyütülmüş dokunma alanı (hitPad)');
  await aim(c, 'fuse', 2, [0.2, 0.05]);   // hedefin 20 cm yanı: boşluk
  h = await c.tb(T => T.hover());
  t.check('hedefin 20 cm yanına bakınca hiçbir şey seçilmiyor', h.kind === null && !h.mark, h);
  await c.tb(T => { const o = T.interactables().find(o => o.userData.kind === 'fuse' && o.userData.i === 2 && o.geometry.type === 'SphereGeometry'); window.__pad = T.hitPad(o, 0.3); });
  await frames(c, 4);
  h = await c.tb(T => T.hover());
  t.check('dokunma alanı eklenince aynı bakış şalteri seçiyor (vurgu asıl parçada)', h.kind === 'fuse' && h.pad && h.mark && h.em === 0x80680f, h);
  const f0 = await c.tb(T => T.game.fuse[2]);
  await click(c); await frames(c, 2);
  t.check('alana tıklamak şalteri çeviriyor', (await c.tb(T => T.game.fuse[2])) === !f0);
  await aim(c, 'fuse', 2);
  h = await c.tb(T => T.hover());
  t.check('doğrudan parçaya bakınca gerçek parça seçiliyor (alan değil)', h.kind === 'fuse' && !h.pad, h);
  await aim(c, 'fuse', 3);  // komşu şalter, alanın içinde kalsa bile
  h = await c.tb(T => ({ ...T.hover(), i: T.interactables().includes(window.__pad) }));
  t.check('komşu şalterin üstünde komşu seçiliyor (alan onu örtmüyor)', h.kind === 'fuse' && !h.pad, h);
  t.check('lazer dokunma alanına takılmıyor (laserSkip)', await c.tb(() => window.__pad.userData.laserSkip === true && window.__pad.material.opacity === 0));

  t.step('vurgu: izinsiz hedef kırmızı');
  await c.tb(T => T.setRole('reader'));
  await aim(c, 'fuse', 1);
  h = await c.tb(T => ({ ...T.hover(), cross: document.querySelector('#cross').className, hint: document.querySelector('#hint').textContent }));
  t.check('TERS SES şaltere bakınca: kırmızı çerçeve, kırmızı halka, "Sadece YERÇEKİMSİZ" ipucu', h.kind === 'fuse' && h.color === 0xe5382b && h.em === 0x5a0a0a && /no/.test(h.cross) && /YERÇEKİMSİZ/.test(h.hint), h);
  const f1 = await c.tb(T => T.game.fuse[1]);
  await click(c); await frames(c, 2);
  t.check('izinsiz tıklama hiçbir şeyi değiştirmiyor, pop yok', (await c.tb(T => T.game.fuse[1])) === f1 && (await c.tb(T => T.pops.length)) === 0);

  t.step('vurgu bitince temizlenir');
  await c.tb(T => { window.__aimPut = null; T.me.pos.set(0, 0, 8); T.me.yaw = Math.PI; });
  await frames(c, 4);
  h = await c.tb(T => ({ ...T.hover(), em: T.interactables().filter(o => o.userData.kind === 'fuse' && o.material.emissive).map(o => o.material.emissive.getHex()) }));
  t.check('çerçeve gizlendi, parçaların ışıması eski haline döndü', !h.mark && h.kind === null && h.em.every(v => v === 0), h);

  t.step('ördek: görünmez dokunma küresine tıklayınca görünen gövde zıplar');
  await c.tb(T => T.setRole('floater'));
  const gold = (await c.puzzle()).ducks.gold[0];
  await aim(c, 'duck', gold, [0, 0], 1.2);
  h = await c.tb(T => T.hover());
  t.check('ördek seçildi (çerçeve var)', h.kind === 'duck' && h.mark, h);
  await click(c);
  t.check('zıplayan nesne ördeğin gövdesi (grup), altın ördek toplandı', await c.tb((T, g) => T.pops.length === 1 && T.pops[0].o === T.M.ducks[g].g && T.game.ducksGot.includes(g), gold));
  t.noErrors();
});
