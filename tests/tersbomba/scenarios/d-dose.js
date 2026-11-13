'use strict';
// Doz: ısınmada düz WASD, zorluğa göre havuz, düğme tutulurken erteleme, finalde donma, kritik anda ağır kaos yok.
const H = require('../harness');
H.run('d-dose', async t => {
  const infra = await H.startInfra(), browser = await H.launchBrowser();
  for (const diff of ['kolay', 'normal', 'zor']) {
    t.step(diff);
    const c = await H.newClient(browser, infra, { name: 'Doz-' + diff });
    await H.soloRoom(c); await H.startGame(c, { diff });
    const a = await c.tb(T => ({ plain: T.kmIsPlain(T.game.keymap), kin: T.game.keymapIn, tune: T.TUNE[T.game.puzzle.diff], chaosIn: T.game.chaosIn, chaos: T.game.chaos }));
    t.check('tur düz WASD ile başlar, ısınma süresi tabloda', a.plain && a.kin <= a.tune.warm && a.kin > a.tune.warm - 6, a);
    t.check('ilk kaos en erken tablodaki saniyede', a.chaosIn >= a.tune.chaosFirst - 6 && !a.chaos, a);
    // düğme tutulurken karışmaz
    await c.tb(T => { T.game.btnHeld = true; T.game.keymapIn = 0.05; });
    await t.sleep(900);
    t.check('düğme tutulurken ertelendi', await c.tb(T => T.kmIsPlain(T.game.keymap)));
    await c.tb(T => { T.game.btnHeld = false; });
    await c.waitFor(() => !window.__tb.kmIsPlain(window.__tb.game.keymap), 4000);
    const seen = new Set();
    for (let i = 0; i < 12; i++) { const km = await c.tb(T => { const k = { ...T.game.keymap }; T.game.keymapIn = 0.01; return k; }); Object.values(km).forEach(k => seen.add(k)); await t.sleep(160); }
    const pool = await c.tb(T => T.KM_POOLS[T.TUNE[T.game.puzzle.diff].pool] || null);
    t.check('tuşlar zorluğun havuzundan', pool ? [...seen].every(k => pool.includes(k)) : seen.size > 8, { seen: [...seen].join(' '), pool });
    t.check('karışmış düzen hiç düz WASD değil', !(await c.tb(T => T.kmIsPlain(T.game.keymap))));
    // kritik anda ağır kaos yok
    const kinds = [];
    for (let i = 0; i < 8; i++) {
      await c.tb(T => { T.game.chaos = null; T.game.timeLeft = 35; T.game.chaosIn = 0.01; });
      await c.waitFor(() => !!window.__tb.game.chaos, 4000);
      kinds.push(await c.tb(T => T.game.chaos.type));
    }
    const hard = await c.tb(T => T.CHAOS_HARD);
    t.check('40 sn altında yalnız görsel/etkileşimli kaos', kinds.every(k => !hard.includes(k) || (diff === 'kolay' && k === 'helyum')), kinds);
    // finalde tuş karışmaz
    await c.tb(T => { T.game.chaos = null; T.game.timeLeft = 200; T.game.final = { hold: 0, on: [] }; T.game.keymapIn = 0.01; });
    const before = await c.tb(T => JSON.stringify(T.game.keymap)); await t.sleep(900);
    t.eq('finalde tuşlar aynı kaldı', await c.tb(T => JSON.stringify(T.game.keymap)), before);
    t.noErrors([c]);
    await c.context.close();
  }
});
