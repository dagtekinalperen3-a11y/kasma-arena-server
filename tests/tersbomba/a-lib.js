'use strict';
// PKG-A sonrası kurallara uyan modül çözücüler: oyuncu önce modülün yanına gider (erişim denetimi),
// aksiyonlar hız sınırının altında yollanır (≤ 12/sn), lazer kilidi lazer noktası tutularak açılır,
// düğmenin süresi oda sahibinin saatine göre gerçekten beklenir.
// require edildiğinde harness'in SOLVERS tablosunu bu sürümlerle değiştirir → H.solveModule aynı arayüzle çalışır.
// P her zaman bulmacanın TAMAMI olmalı: `await A.full(host)` (istemcilerdeki game.puzzle yalnızca o rolün görünümüdür).
const H = require('./harness');

const PACE = 95;   // ms; aksiyonlar arası bekleme
const SPOT = {     // her modül için uygulayan rolün duracağı yer
  wires: [-4, 0, -8.3], keypad: [10.3, 0, -2], button: [1.5, 0.22, 0], password: [-10.3, 0, 3], fuse: [10.2, 4.2, 6.3],
  mouse: [0, 0, 0.9], keyA: [-10.5, 0, -5.5], keyB: [10.5, 0, 6.4], phone: [-6.8, 0, 0.6], far: [0, 0, 8.5],
};
const MZ = { cols: 5, rows: 4, s: 1.2, x0: 3.2, z0: -4.2 };
const tilePos = i => [MZ.x0 + (i % MZ.cols + 0.5) * MZ.s, 0, MZ.z0 - (Math.floor(i / MZ.cols) + 0.5) * MZ.s];

const full = host => host.tb('JSON.parse(JSON.stringify(T.hostPuzzle()))');
// ışınlan ve konumun oda sahibine ulaşmasını bekle
async function go(c, pos) { await c.moveTo(pos, { pin: true }); await H.sleep(170); }
async function act(c, a, extra) { await c.act(a, extra); await H.sleep(PACE); }
const live = c => c.tb('({ pwIdx: T.game.pwIdx, fuse: T.game.fuse, mouseDial: T.game.mouseDial })');

const SOLVERS = {
  async wires(R, P) { await go(R.defuser, SPOT.wires); await act(R.defuser, 'cut', { i: P.wireAns }); },
  async button(R, P) {
    const c = R.defuser; await go(c, SPOT.button);
    await c.tb(T => { if (T.net.solo && T.myRole() !== 'defuser') T.setRole('defuser'); });
    // basma, bekleme ve bırakma tek evaluate içinde: Node ↔ sayfa gecikmesi (yüklü makinede saniyeler) zamanlamayı bozmasın
    await c.eval(([mode, d]) => new Promise(res => {
      const T = window.__tb, t0 = performance.now(); T.act({ t: 'act', a: 'btnDown' });
      const shown = () => { const t = Math.max(0, Math.ceil(T.game.timeLeft)); return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`.includes(String(d)); };
      const iv = setInterval(() => { const el = performance.now() - t0; if (mode === 'tap' ? el > 120 : (el > 900 && shown()) || el > 25000) { clearInterval(iv); T.act({ t: 'act', a: 'btnUp' }); res(); } }, 25);
    }), [P.btnAns.mode, P.btnAns.digit]);
    await H.sleep(PACE);
  },
  async keypad(R, P) { await go(R.defuser, SPOT.keypad); for (const s of P.order) await act(R.defuser, 'key', { i: P.layout.indexOf(s) }); },
  async password(R, P) {
    const c = R.defuser; await go(c, SPOT.password);
    const { pwIdx } = await live(c);
    for (let k = 0; k < 5; k++) for (let n = (P.pw.cols[k].indexOf([...P.pw.word][k]) - pwIdx[k] + 5) % 5; n > 0; n--) await act(c, 'pw', { c: k, d: 1 });
    await act(c, 'pwOk');
  },
  async fuse(R, P) {
    const c = R.floater; await go(c, SPOT.fuse);
    const { fuse } = await live(c);
    for (let i = 0; i < 5; i++) if (fuse[i] !== P.fuseTarget[i]) await act(c, 'fuse', { i });
    await act(c, 'fuseOk');
  },
  async ducks(R, P) { for (const i of P.ducks.gold) { const s = P.ducks.spots[i]; await go(R.floater, [s[0], 5.0, Math.max(-9.5, s[2])]); await act(R.floater, 'duck', { i }); } },
  async mouse(R, P) {
    const c = R.tiny; await go(c, SPOT.mouse);
    const { mouseDial } = await live(c);
    for (let i = 0; i < 3; i++) for (let n = (P.mouseCode[i] - mouseDial[i] + 10) % 10; n > 0; n--) await act(c, 'dial', { i });
    await act(c, 'dialOk');
  },
  async maze(R, P) { for (const i of P.maze.safe) { await go(R.defuser, tilePos(i)); await act(R.defuser, 'maze', { i }); } },
  async laser(R, P) {
    const c = R.pointer;
    await c.tb(T => { if (T.net.solo && T.myRole() !== 'pointer') T.setRole('pointer'); });
    for (const i of P.laserSeq.slice(await c.tb('T.game.laserProg'))) {
      const before = await c.tb('T.game.laserProg');
      await c.tb((T, i) => T.laser(T.LSR[i].p.slice()), i);
      await c.waitFor(n => window.__tb.game.laserProg > n || window.__tb.game.solved.laser, 8000, before);
      await c.tb(T => T.laser(false)); await H.sleep(250);
    }
  },
  // iki FARKLI oyuncu (tek başına oyunda aynı kişi yeter)
  async keys(R) {
    const [a, b = a] = [...new Set([R.reader, R.pointer, R.defuser, R.floater, R.tiny].filter(Boolean))];
    if (a === b || a.page === b.page) { await go(a, SPOT.keyA); await act(a, 'turnKey', { i: 0 }); await go(a, SPOT.keyB); await act(a, 'turnKey', { i: 1 }); return; }
    await go(a, SPOT.keyA); await go(b, SPOT.keyB); await act(a, 'turnKey', { i: 0 }); await act(b, 'turnKey', { i: 1 });
  },
};
Object.assign(H.SOLVERS, SOLVERS);

module.exports = { PACE, SPOT, MZ, tilePos, full, go, act, SOLVERS, solve: (R, mod, P) => SOLVERS[mod](R, P) };
