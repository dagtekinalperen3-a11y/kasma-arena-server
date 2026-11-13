'use strict';
// =====================================================================
//  Ters Bomba — çok oyunculu test düzeneği (Playwright + yerel PeerServer)
//  Her istemci ayrı bir BrowserContext'tir; CDN istekleri node_modules'tan
//  karşılanır, PeerJS sinyalleşmesi yerel PeerServer'a gider (internet gerekmez).
// =====================================================================
const fs = require('fs'), path = require('path'), http = require('http');

const NM = path.resolve(process.env.TB_NM || path.join(__dirname, 'node_modules'));
const HTML = path.resolve(process.env.TB_HTML || path.join(__dirname, '..', '..', 'tersbomba.html'));
const OUT = path.resolve(process.env.TB_OUT || path.join(__dirname, 'out'));
const SLOW = +process.env.TB_SLOW || 1;              // yavaş makinede tüm bekleme sürelerini çarpar
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ROLES = ['reader', 'defuser', 'floater', 'pointer', 'tiny'];   // lobideki sıra; ilk oyuncu (oda sahibi) reader olur
const DIFFS = { easy: 'kolay', hard: 'zor', kolay: 'kolay', normal: 'normal', zor: 'zor' };

function need(pkg, file = '') {
  const p = path.join(NM, pkg, file);
  if (!fs.existsSync(p)) throw new Error(`"${pkg}" bulunamadı: ${p}\n→ tests/tersbomba içinde "npm install" çalıştır ya da TB_NM ile bir node_modules klasörü göster.`);
  return p;
}
function playwright() {
  try { return require('playwright'); } catch (e) { /* aşağıda TB_NM denenir */ }
  try { return require(path.join(NM, 'playwright')); } catch (e) {
    throw new Error('Playwright bulunamadı. "npm i --no-save playwright && npx playwright install chromium" çalıştır (ya da global kurulumu NODE_PATH ile göster).');
  }
}

// ---------------------------------------------------------------------
//  Altyapı: yerel PeerServer + tersbomba.html'i sunan küçük HTTP sunucusu
// ---------------------------------------------------------------------
const open = { infras: new Set(), browsers: new Set(), clients: new Set() };
const rooms = new Map();   // oda kodu → { code, host, members: [client] }

async function startInfra() {
  if (!fs.existsSync(HTML)) throw new Error('Oyun dosyası yok: ' + HTML);
  need('three', 'build/three.module.js'); need('peerjs', 'dist/peerjs.min.js');
  const { PeerServer } = require(need('peer'));
  const peerHttp = await new Promise((res, rej) => { const app = PeerServer({ port: 0, host: '127.0.0.1', path: '/' }, res); app.on('error', rej); });
  const web = http.createServer((req, res) => {
    const p = req.url.split('?')[0];
    if (p !== '/' && p !== '/tersbomba.html') { res.writeHead(404); return res.end(); }
    fs.readFile(HTML, (err, buf) => {   // her istekte yeniden okunur: oyun dosyası değişirse testler güncelini görür
      if (err) { res.writeHead(500); return res.end(String(err)); }
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' }); res.end(buf);
    });
  });
  await new Promise((res, rej) => web.once('error', rej).listen(0, '127.0.0.1', res));
  const peerPort = peerHttp.address().port, webPort = web.address().port;
  const infra = {
    peerPort, webPort, html: HTML,
    url(extra = {}) {
      const q = new URLSearchParams({ ph: '127.0.0.1', pp: String(peerPort), path: '/', sec: '0' });
      for (const [k, v] of Object.entries(extra)) if (v != null && v !== false) q.set(k, v === true ? '1' : String(v));
      return `http://127.0.0.1:${webPort}/tersbomba.html?${q}`;
    },
    async close() {
      open.infras.delete(infra);
      for (const s of [web, peerHttp]) { s.closeAllConnections && s.closeAllConnections(); await new Promise(r => s.close(r)); }
    },
  };
  open.infras.add(infra);
  return infra;
}

// ---------------------------------------------------------------------
//  Tarayıcı ve istemciler
// ---------------------------------------------------------------------
const CHROME_ARGS = [
  '--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist',               // yazılımsal WebGL
  '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',                         // sahte mikrofon
  '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows',
  '--autoplay-policy=no-user-gesture-required',
  '--allow-loopback-in-peer-connection',                                                          // STUN yokken de aynı makinede WebRTC
];
async function launchBrowser(opts = {}) {
  const browser = await playwright().chromium.launch({ headless: !process.env.TB_HEADED, ...opts, args: [...CHROME_ARGS, ...(opts.args || [])] });
  open.browsers.add(browser);
  browser.on('disconnected', () => open.browsers.delete(browser));
  return browser;
}

// CDN → node_modules. Google Fonts boş CSS ile cevaplanır (oyun yedek yazı tipine düşer).
async function installRoutes(context) {
  await context.route(/^https:\/\/cdn\.jsdelivr\.net\//, route => {
    const u = route.request().url().split('?')[0];
    let m = u.match(/\/npm\/three@[^/]+\/(.+)$/), file = null;
    if (m) file = path.join(NM, 'three', m[1]);
    else if ((m = u.match(/\/npm\/peerjs@[^/]+\/(.+)$/))) file = path.join(NM, 'peerjs', m[1]);
    if (!file || !file.startsWith(NM) || !fs.existsSync(file)) return route.fulfill({ status: 404, body: 'harness: yerelde yok: ' + u });
    return route.fulfill({ path: file, contentType: 'text/javascript; charset=utf-8' });
  });
  await context.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, route => route.fulfill({ status: 200, contentType: 'text/css', body: '' }));
}

// PeerJS'in varsayılan STUN/TURN sunucularına internetsiz ortamda ulaşılamaz; yalnızca yerel adaylarla bağlan.
function localIceOnly() {
  let P;
  Object.defineProperty(window, 'Peer', {
    configurable: true, get: () => P,
    set(Real) { P = function (id, o) { if (id && typeof id === 'object') { o = id; id = undefined; } return new Real(id, Object.assign({}, o, { config: { iceServers: [], sdpSemantics: 'unified-plan' } })); }; P.prototype = Real.prototype; },
  });
}
const NOISE = [/GPU stall due to ReadPixels/i, /fonts\.(googleapis|gstatic)\.com/i];
let clientSeq = 0;

async function newClient(browser, infra, { name, norender = true, quality = 'low', viewport = { width: 960, height: 540 }, mic = true, initScripts = [], params = {}, localIce = true } = {}) {
  const idx = ++clientSeq;
  name = name || 'Test' + idx;
  const context = await browser.newContext({ viewport, permissions: mic ? ['microphone'] : [] });
  await installRoutes(context);
  await context.addInitScript(s => { try { if (!localStorage.getItem('tb-settings')) localStorage.setItem('tb-settings', JSON.stringify(s)); } catch (e) {} }, { quality });
  if (localIce) await context.addInitScript(localIceOnly);
  if (!mic) await context.addInitScript(() => { if (navigator.mediaDevices) navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException('test: mikrofon yok', 'NotAllowedError')); });
  for (const s of initScripts) await context.addInitScript(s);
  const page = await context.newPage();
  page.setDefaultTimeout(30000 * SLOW);
  const errors = [], warnings = [], dialogs = [];
  const noisy = (txt, url) => NOISE.some(re => re.test(txt) || re.test(url || ''));
  page.on('console', m => {
    const txt = m.text(), url = (m.location() || {}).url;
    if (noisy(txt, url)) return;
    if (m.type() === 'error') errors.push('console.error: ' + txt.slice(0, 400));
    else if (m.type() === 'warning') warnings.push(txt.slice(0, 400));
  });
  page.on('pageerror', e => errors.push('pageerror: ' + e.message + '\n    ' + String(e.stack || '').split('\n').slice(1, 4).map(s => s.trim()).join('\n    ')));
  page.on('crash', () => errors.push('SAYFA ÇÖKTÜ'));
  page.on('dialog', d => { dialogs.push(`${d.type()}: ${d.message()}`); d.accept().catch(() => {}); });   // confirm() → Tamam

  const client = {
    name, idx, page, context, errors, warnings, dialogs, room: null,
    eval: (fn, arg) => page.evaluate(fn, arg),
    // __tb üstünde çalışır: tb(T => T.game.status) ya da tb('T.game.status') / tb('const g = T.game; return g.strikes')
    tb(fn, arg) {
      const src = typeof fn === 'function' ? fn.toString() : `(T, arg) => { ${/\breturn\b/.test(fn) ? fn : 'return (' + fn + ')'} }`;
      return page.evaluate(([s, a]) => (0, eval)('(' + s + ')')(window.__tb, a), [src, arg]);
    },
    waitFor: (fn, timeout = 15000, arg) => page.waitForFunction(fn, arg, { timeout: timeout * SLOW, polling: 100 }).then(() => true),
    state: () => page.evaluate(() => {
      const T = window.__tb, vis = id => { const el = document.getElementById(id); return !!el && !el.classList.contains('hidden'); };
      const screen = ['loading', 'menu', 'lobby', 'endScreen', 'hud'].find(vis) || '?';
      if (!T) return { screen };
      const g = T.game, r1 = v => Math.round(v * 10) / 10, players = {};
      for (const p of Object.values(T.players())) players[p.name] = p.role;
      const s = { screen: screen === 'endScreen' ? 'end' : screen === 'hud' ? 'game' : screen, role: T.myRole(), players };
      if (g) Object.assign(s, { status: g.status, countdown: r1(Math.max(0, g.countdown)), timeLeft: r1(g.timeLeft), strikes: g.strikes, solved: { ...g.solved }, final: g.final ? { on: g.final.on.slice(), hold: r1(g.final.hold) } : null, chaos: g.chaos ? g.chaos.type : null });
      return s;
    }),
    // act({ t:'act', a:'cut', i:2 }) ya da kısaca act('cut', { i: 2 })
    act: (msg, extra) => page.evaluate(m => window.__tb.act(m), typeof msg === 'string' ? { t: 'act', a: msg, ...extra } : msg),
    puzzle: () => page.evaluate(() => JSON.parse(JSON.stringify(window.__tb.game.puzzle))),
    // ışınla: [x, y, z]. pin=true ise bırakılana kadar orada tutar (YERÇEKİMSİZ kendi kendine süzülür)
    moveTo: (pos, { yaw, pin = false } = {}) => page.evaluate(([p, yaw, pin]) => {
      const me = window.__tb.me, put = () => { me.pos.set(p[0], p[1], p[2]); me.vel.set(0, 0, 0); };
      clearInterval(window.__tbPin); put(); if (yaw != null) me.yaw = yaw;
      if (pin) window.__tbPin = setInterval(put, 30);
    }, [pos, yaw, pin]),
    unpin: () => page.evaluate(() => clearInterval(window.__tbPin)),
    plate: role => page.evaluate(r => { const T = window.__tb, p = T.M.plates[r || T.myRole()].g.position; return [p.x, 0, p.z]; }, role),
    shot(file) { const f = path.resolve(OUT, file); fs.mkdirSync(path.dirname(f), { recursive: true }); return page.screenshot({ path: f }).then(() => f); },
    async close() { open.clients.delete(client); await context.close().catch(() => {}); },
  };
  open.clients.add(client);
  await page.goto(infra.url({ norender, ...params }), { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.__tb && !document.querySelector('#menu').classList.contains('hidden'), null, { timeout: 90000 * SLOW });
  return client;
}

// ---------------------------------------------------------------------
//  Oda yardımcıları (gerçek arayüz üzerinden)
// ---------------------------------------------------------------------
const inLobby = () => !document.querySelector('#lobby').classList.contains('hidden');

async function hostRoom(client, { solo = false } = {}) {
  const { page } = client;
  await page.fill('#nameIn', client.name);
  await page.click(solo ? '#btnSolo' : '#btnHost');
  await client.waitFor(inLobby, 30000).catch(async e => { throw new Error(`${client.name}: oda kurulamadı — "${await page.textContent('#menuStatus')}" (${e.message.split('\n')[0]})`); });
  const code = (await page.textContent('#roomCode')).trim();
  client.room = { code, host: client, members: [client], solo };
  if (!solo) rooms.set(code, client.room);
  return code;
}
const soloRoom = client => hostRoom(client, { solo: true });

async function joinRoom(client, code) {
  const { page } = client;
  await page.fill('#nameIn', client.name);
  await page.fill('#codeIn', code);
  await page.click('#btnJoin');
  // lobi açıldı VE oda sahibinin listesinde varız (ilk 'lobby' yayını geldi)
  await client.waitFor(() => { const T = window.__tb; return !document.querySelector('#lobby').classList.contains('hidden') && T.net.peer && !!T.players()[T.net.peer.id]; }, 30000)
    .catch(async e => { throw new Error(`${client.name}: "${code}" odasına katılamadı — "${await page.textContent('#menuStatus')}" (${e.message.split('\n')[0]})`); });
  const room = rooms.get(code);
  if (room) { room.members.push(client); client.room = room; }
  return client;
}

// Lobide rol kartına tıklar (başkasındaysa oyun yer değiştirir). Antrenman oyununun içindeyken __tb.setRole kullanır.
async function setRole(client, role) {
  const s = await client.state();
  if (s.role === role) return;
  if (s.screen === 'lobby') await client.page.click(role === 'none' ? '#lnkSpec' : `#roleSlots .rcard[data-role="${role}"]`);
  else if (client.room && client.room.solo) await client.tb((T, r) => T.setRole(r), role);
  else throw new Error(`${client.name}: rol yalnızca lobide değişir (ekran: ${s.screen})`);
  await client.waitFor(r => window.__tb.myRole() === r, 10000, role);
}

const waitAll = (clients, fn, timeout, arg) => Promise.all(clients.map(c => c.waitFor(fn, timeout, arg).catch(e => { throw new Error(`${c.name}: ${e.message.split('\n')[0]}`); })));

async function startGame(host, { diff = 'normal', muts = [] } = {}) {
  const { page } = host, members = host.room ? host.room.members : [host], d = DIFFS[diff];
  if (!d) throw new Error('Bilinmeyen zorluk: ' + diff);
  await page.click(`#diffSeg button[data-d="${d}"]`);
  for (const m of muts) if (!(await page.locator(`#mutSeg button[data-m="${m}"]`).evaluate(b => b.classList.contains('on')))) await page.click(`#mutSeg button[data-m="${m}"]`);
  // ayarlar herkese ulaşsın (oda sahibi başlatınca bulmaca bu ayarlarla üretilir)
  await host.waitFor(([d, muts]) => document.querySelector(`#diffSeg button[data-d="${d}"]`).classList.contains('on') && muts.every(m => document.querySelector(`#mutSeg button[data-m="${m}"]`).classList.contains('on')), 10000, [d, muts]);
  await page.click('#btnStart');
  await waitAll(members, () => { const g = window.__tb.game; return !!g && g.countdown <= 0 && !document.querySelector('#hud').classList.contains('hidden'); }, 60000);
  return host.puzzle();
}

// n istemcili hazır oda. roles[i] → i. istemcinin rolü (varsayılan: reader(oda sahibi), defuser, floater, pointer, tiny).
async function party(n = 5, roles, opts = {}) {
  roles = roles || Array.from({ length: n }, (_, i) => ROLES[i] || 'none');
  const infra = await startInfra(), browser = await launchBrowser(opts.launch);
  const clients = [];
  for (let i = 0; i < n; i++) clients.push(await newClient(browser, infra, { name: `${i + 1}-${roles[i]}`, ...opts.client, ...(opts.clients || [])[i] }));
  const host = clients[0], code = await hostRoom(host);
  for (const c of clients.slice(1)) await joinRoom(c, code);
  for (let i = 0; i < n; i++) await setRole(clients[i], roles[i]);
  const want = {}; clients.forEach((c, i) => want[c.name] = roles[i]);
  await waitAll(clients, w => { const P = Object.values(window.__tb.players()); return P.length === Object.keys(w).length && P.every(p => w[p.name] === p.role); }, 15000, want);
  const byRole = {}; clients.forEach((c, i) => { if (roles[i] !== 'none' && !byRole[roles[i]]) byRole[roles[i]] = c; });
  return { infra, browser, clients, host, code, roles, byRole, close: closeAll };
}

async function closeAll() {
  for (const c of [...open.clients]) await c.close();
  for (const b of [...open.browsers]) await b.close().catch(() => {});
  for (const i of [...open.infras]) await i.close().catch(() => {});
  rooms.clear();
}

// ---------------------------------------------------------------------
//  Durum karşılaştırma
// ---------------------------------------------------------------------
const core = s => JSON.stringify({ screen: s.screen, status: s.status, strikes: s.strikes, solved: s.solved, players: Object.entries(s.players || {}).sort(), final: s.final ? s.final.on.slice().sort() : null });
function divergence(clients, states, tol) {
  for (let i = 1; i < states.length; i++) {
    if (core(states[i]) !== core(states[0])) return `${clients[i].name} ≠ ${clients[0].name}\n   ${clients[0].name}: ${core(states[0])}\n   ${clients[i].name}: ${core(states[i])}`;
  }
  const ts = states.map(s => s.timeLeft).filter(v => v != null);
  if (ts.length && Math.max(...ts) - Math.min(...ts) > tol) return `timeLeft farkı > ${tol} sn: ${states.map((s, i) => `${clients[i].name}=${s.timeLeft}`).join(' ')}`;
  return null;
}
// Tüm istemciler aynı çekirdek duruma (ekran, status, strikes, solved, roller, final) gelene dek bekler; ortak durumu döndürür.
async function converge(clients, { tol = 1.5, timeout = 10000 } = {}) {
  const t0 = Date.now(); let why;
  for (;;) {
    const states = await Promise.all(clients.map(c => c.state()));
    if (!(why = divergence(clients, states, tol))) return { ...states[0], spread: Math.round((Math.max(...states.map(s => s.timeLeft || 0)) - Math.min(...states.map(s => s.timeLeft || 0))) * 100) / 100 };
    if (Date.now() - t0 > timeout * SLOW) throw new Error('İstemciler aynı duruma yakınsamadı: ' + why);
    await sleep(150);
  }
}

// ---------------------------------------------------------------------
//  Modül çözücüler: doğru aksiyonu, o modüle dokunabilen ROLDEKİ istemciden yollar
//  (oyundaki MOD_ROLE / ACT_MOD / hostAction ile aynı kurallar). R = { reader, defuser, floater, pointer, tiny } → istemci
// ---------------------------------------------------------------------
const live = c => c.tb('({ pwIdx: T.game.pwIdx, fuse: T.game.fuse, mouseDial: T.game.mouseDial })');
const SOLVERS = {
  wires: (R, P) => R.defuser.act('cut', { i: P.wireAns }),
  async button(R, P) { await R.defuser.act('btnDown'); await R.defuser.act('btnUp', P.btnAns.mode === 'tap' ? { dur: 120, timer: '' } : { dur: 1500, timer: String(P.btnAns.digit) }); },
  async keypad(R, P) { for (const s of P.order) await R.defuser.act('key', { i: P.layout.indexOf(s) }); },
  async password(R, P) {
    const { pwIdx } = await live(R.defuser);
    for (let c = 0; c < 5; c++) for (let n = (P.pw.cols[c].indexOf(P.pw.word[c]) - pwIdx[c] + 5) % 5; n > 0; n--) await R.defuser.act('pw', { c, d: 1 });
    await R.defuser.act('pwOk');
  },
  async fuse(R, P) {
    const { fuse } = await live(R.floater);
    for (let i = 0; i < 5; i++) if (fuse[i] !== P.fuseTarget[i]) await R.floater.act('fuse', { i });
    await R.floater.act('fuseOk');
  },
  async ducks(R, P) { for (const i of P.ducks.gold) await R.floater.act('duck', { i }); },
  async mouse(R, P) {
    const { mouseDial } = await live(R.tiny);
    for (let i = 0; i < 3; i++) for (let n = (P.mouseCode[i] - mouseDial[i] + 10) % 10; n > 0; n--) await R.tiny.act('dial', { i });
    await R.tiny.act('dialOk');
  },
  async maze(R, P) { for (const i of P.maze.safe) await R.defuser.act('maze', { i }); },
  async laser(R, P) { for (const i of P.laserSeq) await R.pointer.act('laser', { i }); },
  // iki FARKLI oyuncu (tek başına oyunda aynı kişi yeter)
  async keys(R) { const [a, b = a] = [...new Set([R.reader, R.pointer, R.defuser, R.floater, R.tiny].filter(Boolean))]; await a.act('turnKey', { i: 0 }); await b.act('turnKey', { i: 1 }); },
};
async function solveModule(R, mod, P) {
  if (!SOLVERS[mod]) throw new Error('Bu modül için çözücü yok: ' + mod + ' (harness.js → SOLVERS)');
  await SOLVERS[mod](R, P || await Object.values(R)[0].puzzle());
}
// Antrenman: tek istemci, aksiyondan önce o role bürünür → solveModule ile aynı arayüz
function soloRoles(client) {
  const R = {};
  for (const r of ROLES) R[r] = Object.assign(Object.create(client), { act: async (m, x) => { await client.tb((T, r) => { if (T.myRole() !== r) T.setRole(r); }, r); return client.act(m, x); } });
  return R;
}
// Final: verilen istemciler kendi rollerinin plakasına geçer ve orada kalır.
const toPlates = clients => Promise.all(clients.map(async c => c.moveTo(await c.plate(), { pin: true })));

// ---------------------------------------------------------------------
//  Senaryo koşucusu: adımlar, kontroller, hata dökümü, PASS/FAIL ve çıkış kodu
// ---------------------------------------------------------------------
async function run(name, fn, { timeout = 300000 } = {}) {
  const t0 = Date.now(), el = () => ((Date.now() - t0) / 1000).toFixed(1).padStart(6) + 's';
  const checks = [], fails = [], known = [];
  const t = {
    name,
    log: (...a) => console.log(`[${el()}]  `, ...a),
    step: s => console.log(`[${el()}] ▶ ${s}`),
    // yumuşak kontrol: başarısız olsa da senaryo sürer, sonunda FAIL sayılır
    check(label, ok, detail) {
      checks.push(label);
      if (ok) console.log(`[${el()}]   ✓ ${label}`);
      else { fails.push(label + (detail !== undefined ? ' — ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) : '')); console.log(`[${el()}]   ✗ ${label}` + (detail !== undefined ? '\n            ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) : '')); }
      return !!ok;
    },
    // bilinen OYUN hatasına bağlı kontrol: varsayılan olarak FAIL sayılır; TB_ALLOW_KNOWN=1 ise yalnızca uyarı basar
    bug(label, ok, detail) {
      if (ok || !process.env.TB_ALLOW_KNOWN) return t.check(label, ok, detail);
      known.push(label); console.log(`[${el()}]   ⚠ BİLİNEN OYUN HATASI (TB_ALLOW_KNOWN): ${label}\n            ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`); return false;
    },
    eq(label, got, want) { return t.check(label, JSON.stringify(got) === JSON.stringify(want), `beklenen ${JSON.stringify(want)}, gelen ${JSON.stringify(got)}`); },
    // tüm istemcilerde konsol/sayfa hatası olmamalı
    noErrors(clients = [...open.clients]) { for (const c of clients) t.check(`${c.name}: sayfa hatası yok`, c.errors.length === 0, c.errors.join(' | ')); },
    sleep: ms => sleep(ms * SLOW),
  };
  console.log(`\n===== ${name} =====`);
  let crash = null, timer;
  try {
    await Promise.race([fn(t), new Promise((_, rej) => { timer = setTimeout(() => rej(new Error(`senaryo zaman aşımı (${timeout * SLOW / 1000} sn)`)), timeout * SLOW); })]);
  } catch (e) { crash = e; fails.push('İSTİSNA: ' + (e && e.message || e)); }
  clearTimeout(timer);
  if (fails.length) {
    console.log(`\n----- ${name}: hata dökümü -----`);
    if (crash) console.log(crash.stack || crash);
    let i = 0;
    for (const c of open.clients) {
      const st = await Promise.race([c.state(), sleep(5000).then(() => 'durum okunamadı (5 sn)')]).catch(e => 'durum okunamadı: ' + e.message);
      console.log(`\n[${c.name}] durum: ${JSON.stringify(st)}`);
      if (c.dialogs.length) console.log(`[${c.name}] diyaloglar: ${c.dialogs.join(' | ')}`);
      console.log(`[${c.name}] hatalar (${c.errors.length}):${c.errors.length ? '\n  ' + c.errors.join('\n  ') : ' yok'}`);
      const f = await Promise.race([c.shot(`${name}-fail-${++i}.png`), sleep(8000)]).catch(() => null);
      if (f) console.log(`[${c.name}] ekran görüntüsü: ${f}`);
    }
  }
  await Promise.race([closeAll(), sleep(15000)]);
  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`\n${fails.length ? 'FAIL' : 'PASS'}  ${name}  (${checks.length} kontrol, ${fails.length} hata, ${secs} sn)`);
  fails.forEach(f => console.log('  ✗ ' + f));
  known.forEach(f => console.log('  ⚠ bilinen oyun hatası (sayılmadı): ' + f));
  process.exit(fails.length ? 1 : 0);
}

module.exports = {
  NM, HTML, OUT, ROLES, CHROME_ARGS, sleep,
  startInfra, launchBrowser, newClient, hostRoom, soloRoom, joinRoom, setRole, startGame, party, closeAll,
  waitAll, converge, solveModule, SOLVERS, soloRoles, toPlates, run,
};
