'use strict';
// Fare paneli: rakam ileri (+1) ve geri (−1) çevrilir; kararı oda sahibi verir.
const H = require('../harness'), A = require('../a-lib');
H.run('b-dial', async t => {
  const infra = await H.startInfra(), browser = await H.launchBrowser();
  const c = await H.newClient(browser, infra, { name: 'Dial' });
  await H.soloRoom(c); await H.startGame(c, { diff: 'normal' });
  await c.tb(T => T.setRole('tiny')); await A.go(c, A.SPOT.mouse);
  t.step('geri ve ileri');
  await A.act(c, 'dial', { i: 0, d: -1 });
  t.eq('0 → geri → 9', await c.tb('T.game.mouseDial[0]'), 9);
  await A.act(c, 'dial', { i: 0, d: -1 });
  t.eq('9 → geri → 8', await c.tb('T.game.mouseDial[0]'), 8);
  await A.act(c, 'dial', { i: 0 });
  t.eq('8 → ileri → 9', await c.tb('T.game.mouseDial[0]'), 9);
  await A.act(c, 'dial', { i: 1, d: 5 });
  t.eq('geçersiz yön ileri sayılır', await c.tb('T.game.mouseDial[1]'), 1);
  t.noErrors([c]);
});
