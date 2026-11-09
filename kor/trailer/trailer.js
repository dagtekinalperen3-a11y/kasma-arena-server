// KÖR — 1 dakikalık tanıtım videosu: oyunu kare kare oynatıp 1080p kaydeder.
// Kullanım: node trailer.js <ilkÇekim> <sonÇekim>   (çekim numaraları 0'dan)
const { chromium } = require('playwright');
const fs = require('fs');
const stepper = require('./stepper.js');
const FPS = 24;
const OUT = __dirname + '/frames';
fs.mkdirSync(OUT, { recursive: true });

// çekim listesi: [ad, başlangıç sn, bitiş sn]
const SHOTS = [
  ['intro', 0, 5], ['approach', 5, 9.5], ['face', 9.5, 13.5], ['charge', 13.5, 17], ['gameplay', 17, 20.5],
  ['ward', 20.5, 24], ['friends', 24, 29], ['revive', 29, 32], ['montage', 32, 38], ['screamer', 38, 39.5],
  ['chase', 39.5, 47.5], ['escape', 47.5, 52], ['title', 52, 57], ['sting', 57, 60],
];
module.exports = { SHOTS, FPS };
if (require.main !== module) return;

const [from, to] = [+process.argv[2], +process.argv[3]];

// sayfa içinde çalışan yönetmen
const DIRECTOR = () => {
  const K = window.__kor, C = 3.2, cc = i => (i + .5) * C;
  const V = (x, y, z) => new (K.camera.position.constructor)(x, y, z);
  const lerp = (a, b, t) => a + (b - a) * t, cl = (v, a, b) => Math.max(a, Math.min(b, v));
  const ease = t => t * t * (3 - 2 * t);
  const $ = id => document.getElementById(id);
  // yazı katmanı
  const tr = document.createElement('div');
  tr.style.cssText = 'position:fixed;inset:0;z-index:40;pointer-events:none;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center';
  tr.innerHTML = '<div id="trBig" style="font-family:Creepster,cursive;color:#e8e0cc;font-size:118px;letter-spacing:6px;text-shadow:0 0 30px #600,0 0 6px #000;line-height:1"></div><div id="trSub" style="font-family:\'Special Elite\',monospace;color:#d8d2c4;font-size:34px;letter-spacing:10px;margin-top:22px;text-shadow:0 0 10px #000"></div>';
  document.body.appendChild(tr);
  const black = document.createElement('div'); black.style.cssText = 'position:fixed;inset:0;z-index:35;background:#000;opacity:0;pointer-events:none'; document.body.appendChild(black);
  const white = document.createElement('div'); white.style.cssText = 'position:fixed;inset:0;z-index:36;background:#fff;opacity:0;pointer-events:none'; document.body.appendChild(white);
  const face = document.createElement('img'); face.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;object-fit:cover;z-index:37;opacity:0;pointer-events:none'; document.body.appendChild(face);
  const lower = document.createElement('div'); lower.style.cssText = 'position:fixed;left:90px;bottom:120px;z-index:40;font-family:Creepster,cursive;font-size:84px;color:#e8e0cc;letter-spacing:4px;text-shadow:0 0 18px #500,0 0 4px #000;opacity:0'; document.body.appendChild(lower);
  $('chapter').style.transition = 'none'; $('banner').style.transition = 'none';
  const text = (big, sub, op, color) => { $('trBig').textContent = big; $('trSub').textContent = sub || ''; tr.style.opacity = op; $('trBig').style.color = color || '#e8e0cc'; };
  const fadeWin = (t, a, b, f = .4) => cl(Math.min((t - a) / f, (b - t) / f), 0, 1);
  const cam = (x, z, yaw, pitch = 0) => { K.player.pos.set(x, 0, z); K.player.yaw = yaw; K.player.pitch = pitch; K.player.vel.set(0, 0, 0); };
  const hideActors = () => { for (const k of ['lunger', 'peekHead', 'shadowRunner', 'child']) if (K[k]) K[k].visible = false; K.grin.visible = false; };
  const avatars = () => [...K.NET.players.values()];
  // ortak: oyunun kendi korkularını kapat
  const calm = () => {
    const S = K.S; S.dirT = 999; S.watchT = 999; S.huntT = 999; S.wxT = 999; S.chapT = .001; S.reading = false;
    Object.keys(K.scares).forEach(n => S.triggered.add(n));
    K.mon.active = false; S.flashForcedOff = 0; S.stalk = null; S.cryArm = null;
    $('chapter').style.opacity = 0;
    if (!window.__guides) window.__guides = K.scene.children.filter(o => o.isMesh && o.material && o.material.blending === 2 && o.material.color && o.material.color.getHex() === 0x7fd4ff);
    window.__guides.forEach(m => m.visible = false);
  };
  const sprintLegs = (m, t, k = 28) => m.userData.legs.forEach(l => { l.hip.rotation.x = Math.sin(t * k + l.s * 1.6) * 1.1 - .5; l.kn.rotation.x = .6 + Math.max(0, Math.sin(t * k + l.s)) * .9; });
  const runAv = (r, x, z, yaw, run) => { r.tpos.set(x, 0, z); r.tyaw = yaw; r.run = run ? 1 : 0; r.hid = 0; };
  let screamImg = null;

  window.TR = {
    init(needAvatars) {
      calm();
      $('hud').style.display = 'none';
      screamImg = K.drawScreamer('maw').toDataURL('image/jpeg', .92);
      if (needAvatars) {
        const SL = K.REMOTE_LIGHTS[0].constructor; const sl = new SL(0xfff1d6, 0, 24, .55, .6, 1.4); K.scene.add(sl); K.scene.add(sl.target); K.REMOTE_LIGHTS.push(sl);
        K.NET.on = true; K.NET.started = true; K.NET.host = true;
        [['Alperen', 0], ['Mehmet', 1], ['Ece', 2]].forEach(([n, role], i) => { const r = K.mkRemote(i + 1, n); r.roles = [role]; r.hid = 1; K.NET.players.set(i + 1, r); K.makeAvatar(r); });
      }
    },
    setup(name) {
      calm(); hideActors(); text('', '', 0); black.style.opacity = 0; white.style.opacity = 0; face.style.opacity = 0; lower.style.opacity = 0;
      K.S.fearKick = 0; K.S.glitch = 0; K.S.hallu = 0; K.S.halluT = 0; K.S.flashOn = true; K.S.crouchToggle = false; K.S.nv = false; $('nvHud').style.display = 'none';
      $('hud').style.display = name === 'gameplay' ? 'block' : 'none';
      avatars().forEach(r => { r.hid = 1; r.down = 0; r.crouch = 0; });
      if (name === 'ward') { K.applyStations(K.STATIONS.map(s => s.type === 'candle')); }
      if (name === 'chase' || name === 'escape' || name === 'sting') { if (K.S.chapter !== 3) K.startChapter(3); calm(); K.S.state = 'play'; K.mon.active = false; }
      if (name === 'gameplay') { K.S.stage = ''; }
      if (!window.__skin0) window.__skin0 = K.M.skin.color.getHex();
      K.M.skin.color.setHex(name === 'face' ? 0x3f3a33 : window.__skin0);
    },
    frame(name, t, dt) {
      const S = K.S, L = K.lunger, u = L.userData;
      calm(); S.fearKick = 0;
      if (name === 'intro') {
        cam(lerp(cc(2), cc(6), t / 5), cc(6), -Math.PI / 2, -.02);
        black.style.opacity = cl(1 - t / 1.2, 0, 1);
        text('', '', 0); $('trSub').textContent = '1987  ·  AZİZ LAZAR SANATORYUMU'; tr.style.opacity = fadeWin(t, .8, 4.6, .7);
      }
      if (name === 'approach') {
        cam(cc(7), cc(6), -Math.PI / 2, .02); S.fearKick = .45;
        L.visible = t < 4.25; L.position.set(lerp(cc(12.2), cc(9.6), t / 4), 0, cc(6)); L.rotation.set(0, -Math.PI / 2, 0);
        K.animateMonster(L, dt, 1.6, false, false); u.head.rotation.z = Math.sin(t * 2.3) * .5;
        if (t > 3.85 && t < 3.9) K.flicker(.6);
      }
      if (name === 'face') {
        cam(cc(10) + t * .12, cc(6), -Math.PI / 2, .12); S.fearKick = .55;
        L.visible = true; L.rotation.set(0, -Math.PI / 2, 0); L.position.set(cc(10) + t * .12 + 2.05, 0, cc(6));
        K.animateMonster(L, dt, 0, false, true);
        u.spine.rotation.x = 1.0; u.neck.rotation.x = -.95; u.body.position.y = -.15;   // öne eğilip yüzünü kameraya uzatır
        u.head.rotation.z = Math.sin(t * 2.1) * .35 + (Math.sin(t * 13) > .93 ? .5 : 0); u.head.rotation.y = Math.sin(t * 1.3) * .3;
        u.jaw.rotation.x = lerp(.15, .55, t / 4) + Math.sin(t * 9) * .03; K.spreadJaw(u);
        text('O SENİ GÖREMEZ...', '', fadeWin(t, .4, 3.7, .5));
      }
      if (name === 'charge') {
        cam(cc(5), cc(6), -Math.PI / 2, .03);
        L.visible = t < 3.45;
        const start = cc(5) + 15;
        let x = start;
        if (t > .9) x = Math.max(cc(5) + 1.1, start - (t - .9) * 7.2);
        L.position.set(x, 0, cc(6)); L.rotation.set(0, -Math.PI / 2, 0);
        if (t < .9) { K.animateMonster(L, dt, 0, false, true); u.jaw.rotation.x = lerp(.2, 1, cl(t / .5, 0, 1)); u.head.rotation.z = Math.sin(t * 40) * .2; }
        else { K.animateMonster(L, dt, 6, true, false); sprintLegs(L, t); u.jaw.rotation.x = .9 + Math.sin(t * 30) * .1; }
        K.spreadJaw(u);
        S.fearKick = cl(.4 + t / 3, 0, 1); S.glitch = t > 3.1 ? 1 : 0; K.player.shake = t > .8 && t < 1.3 ? .6 : (t > 3 ? .9 : 0);
        text('AMA HER ŞEYİ DUYAR', '', fadeWin(t, .15, 1.9, .3), '#ff3a2a');
        white.style.opacity = t > 3.4 ? 1 : 0;
      }
      if (name === 'gameplay') {
        if (t < dt * 1.5) cam(cc(19 + 39), cc(6), -Math.PI / 2, -.05);
        K.S.fearKick = .2;
        lower.textContent = 'TEK BAŞINA...'; lower.style.opacity = fadeWin(t, .4, 3.2, .4);
      }
      if (name === 'ward') {
        cam(cc(6 + 39) + .6, cc(8.6), Math.PI + .25 - t * .14, -.2);
        if (t > 1.6 && !S.nv) { const r = Math.random; Math.random = () => .99; K.setNV(true); Math.random = r; }
        S.nvBatt = 1;
        const g = K.halluFigs && K.halluFigs[0];
        if (!window.__ghost) { window.__ghost = K.humanoid(new (K.M.mouth.constructor)({ color: 0xeeeeee, transparent: true, opacity: .85 }), 1.05); K.scene.add(window.__ghost); }
        const gh = window.__ghost; gh.visible = S.nv && t < 3.45;
        const gz = t < 2.9 ? cc(12.6) : lerp(cc(12.6), cc(9.2), (t - 2.9) / .5);
        gh.position.set(cc(5.6 + 39), 0, gz); gh.rotation.y = Math.PI; gh.userData.head.rotation.z = .7;
        if (t > 2.9) { S.glitch = .8; K.player.shake = .7; }
        white.style.opacity = t > 3.42 ? .9 : 0;
      }
      if (name === 'friends') {
        cam(cc(19), cc(16), Math.PI / 2, -.02); S.fearKick = .15;
        const rs = avatars();
        const base = lerp(cc(13), cc(17.4), t / 5);
        [[0, 0], [-1.6, -.75], [-1.3, .8]].forEach(([dx, dz], i) => runAv(rs[i], base + dx, cc(16) + dz, -Math.PI / 2 + Math.sin(t * 1.3 + i) * .25, false));
        text('YA DA ARKADAŞLARINLA', '3 KİŞİYE KADAR ONLINE', fadeWin(t, .5, 4.6, .5));
      }
      if (name === 'revive') {
        cam(cc(20) + .6, cc(16) + .9, Math.PI / 2 - .22, -.22); S.fearKick = .4;
        const rs = avatars(), bx = cc(19) - .4;
        runAv(rs[1], bx, cc(16), 0, false); rs[1].down = t < 2.1 ? 1 : 0;
        runAv(rs[0], bx + .2, cc(16) - .9, Math.PI, false); rs[0].crouch = t < 2.1 ? 1 : 0;
        runAv(rs[2], bx - 1.4, cc(16) + .5, Math.PI / 2 + .4, false);
        text('BİRBİRİNİZİ KURTARIN', '', fadeWin(t, .3, 2.8, .4));
      }
      if (name === 'montage') {
        const k = Math.floor(t), lt = t - k; S.fearKick = .7; S.flashOn = true; hideActors(); S.hallu = 0;
        black.style.opacity = lt < .06 ? 1 : 0;
        if (k === 0) { // kapının arkasında
          cam(cc(11), cc(6) + .6, 0, .05);
          const d = K.doors.find(d => d.x === 11 && d.z === 5);
          if (lt < .05) { d.open = 0; d.target = 1; d.speed = 7; d.swing = 1; }
          if (lt > .22) { K.standFacing(K.peekHead, V(cc(11), 0, cc(4) + .2)); K.animateMonster(K.peekHead, dt, 0, false, true); K.peekHead.userData.jaw.rotation.x = .95; K.spreadJaw(K.peekHead.userData); K.peekHead.visible = true; K.player.shake = .5; }
        }
        if (k === 1) { // sanrı
          if (lt < .05) { K.hallucinate(3); S.halluMax = 20; }
          cam(cc(24), cc(21), Math.PI * .9 + lt * .2, 0); S.hallu = 1;
        }
        if (k === 2) { // karanlıkta gözler
          cam(cc(2 + 39), cc(6), -Math.PI / 2, 0); S.flashOn = false; S.hallu = 0; S.halluT = 0; (K.halluFigs || []).forEach(f => f.visible = false);
          if (lt < .05) { [[7, 2.1, -.9], [9, 1.7, .8], [11, .35, 0], [13, 2.2, .4], [15, 1.6, -.7], [17, .4, .9], [19, 1.9, -.2], [22, 1.7, .6]].forEach(([dx, y, dz]) => K.spawnEyes(V(cc(2 + 39) + dx, y, cc(6) + dz), 99)); }
        }
        if (k === 3) { // şimşekte siluet
          K.watchers.forEach(w => { w.active = false; w.g.visible = false; });
          cam(cc(11), cc(3.4), 0, .08); S.flashOn = false;
          if (lt < .05) K.lightning(true);
        }
        if (k === 4) { // tavandan baş aşağı
          cam(cc(26 + 39), cc(6), -Math.PI / 2, .05); S.flashOn = true;
          const p = V(cc(26 + 39) + 1.7, 0, cc(6));
          L.visible = true; L.rotation.set(0, -Math.PI / 2, Math.PI);
          const y = lt < .12 ? lerp(3.9, 1.55, lt / .12) : 1.55 + Math.sin(lt * 30) * .02;
          u.jaw.rotation.x = .95; K.spreadJaw(u); u.head.rotation.z = Math.sin(lt * 25) * .3; u.neck.rotation.x = -.2; u.spine.rotation.x = .1;
          u.arms.forEach(a => { a.sh.rotation.x = -1.2 + Math.sin(lt * 18 + a.s) * .3; a.sh.rotation.z = a.s * .6; a.el.rotation.x = -.5; });
          L.position.set(0, 0, 0); K.placeHeadAt(L, V(p.x, y, p.z)); K.player.shake = lt < .3 ? .8 : .2;
        }
        if (k === 5) { // karanlıkta sırıtış
          L.visible = false; cam(cc(9), cc(16), -Math.PI / 2, 0); S.flashOn = false; S.blackT = .5;
          if (lt < .05) { S.grinT = 1.9; S.grinFar = V(cc(9) + 6, 1.7, cc(16)); S.grinNear = V(cc(9) + 1.9, 1.62, cc(16)); }
        }
      }
      if (name === 'screamer') {
        if (t < dt * 1.5) face.src = screamImg;
        const on = t < .95;
        face.style.opacity = on ? 1 : 0;
        const s = 1.05 + t * .45, j = on ? 18 : 0;
        face.style.transform = `scale(${s}) translate(${(Math.random() - .5) * j}px,${(Math.random() - .5) * j}px) rotate(${(Math.random() - .5) * 3}deg)`;
        face.style.filter = (Math.floor(t * 24) % 7 === 3) ? 'invert(1) contrast(1.6)' : 'contrast(1.3) saturate(1.3)';
        white.style.opacity = t < .08 ? .8 : 0; black.style.opacity = t > .95 ? 1 : 0;
      }
      if (name === 'chase') {
        const sp = 4.2, camX = cc(5) + t * sp;
        cam(camX, cc(16), Math.PI / 2, -.02); S.fearKick = 1; S.flashOn = true;
        const rs = avatars();
        [[4.2, 0], [5.6, -.8], [6.3, .75]].forEach(([back, dz], i) => runAv(rs[i], camX - back + Math.sin(t * 9 + i) * .1, cc(16) + dz, -Math.PI / 2, true));
        const mx = camX - (t < 6 ? 10.5 - t * .55 : 7.2 - (t - 6) * 2.4);
        L.visible = true; L.position.set(mx, 0, cc(16)); L.rotation.set(0, Math.PI / 2, 0);
        K.animateMonster(L, dt, 6, true, false); sprintLegs(L, t); u.jaw.rotation.x = .85 + Math.sin(t * 28) * .12; K.spreadJaw(u);
        K.player.shake = .25 + (t > 6.5 ? .5 : 0); S.glitch = t > 7.6 ? 1 : 0;
        text('KAÇIN!', '', fadeWin(t, .3, 2.2, .3), '#ff2a1a');
        black.style.opacity = t > 7.85 ? 1 : 0;
      }
      if (name === 'escape') {
        cam(cc(27) - .5, cc(21.2), Math.PI, .02); S.fearKick = .6; S.flashOn = true;
        const g = K.exitGate, o = cl(t / 1.6, 0, 1); g.l.position.x = -C / 4 - ease(o) * C / 2; g.r.position.x = C / 4 + ease(o) * C / 2;
        const rs = avatars(), gz = cc(26) - C / 2;
        [[1.3, -.6], [1.75, .7], [2.15, 0]].forEach(([t0, dx], i) => { const k = cl((t - t0) / 1.9, 0, 1); runAv(rs[i], cc(27) + dx * (1 - k * .6), lerp(cc(20.6), gz + 3, k), Math.PI, true); rs[i].hid = t < t0 || k >= 1 ? 1 : 0; });
        L.visible = t > 3.3 && t < 4.35;
        if (L.visible) { const k = cl((t - 3.3) / 1, 0, 1); L.position.set(cc(25.3) + k * 1.8, 0, lerp(cc(22.5), cc(24.2), k)); L.rotation.set(0, Math.PI * .75, 0); K.animateMonster(L, dt, 6, true, false); sprintLegs(L, t); u.jaw.rotation.x = 1; K.spreadJaw(u); K.player.shake = .5; }
        white.style.opacity = cl((t - 3.7) / .6, 0, 1);
      }
      if (name === 'title') {
        hideActors(); black.style.opacity = 1; white.style.opacity = cl(1 - t / .5, 0, 1);
        const flick = (t > 1.4 && t < 1.48) || (t > 2.9 && t < 2.95) ? .25 : 1;
        tr.style.opacity = cl(t / .5, 0, 1) * flick * cl((5 - t) / .4, 0, 1);
        $('trBig').innerHTML = '<span style="font-size:260px;color:#b00d0d;text-shadow:0 0 50px #700,0 0 6px #000;letter-spacing:24px">KÖR</span>';
        $('trSub').innerHTML = (t > 1.2 ? 'KÖR BİR YARATIK. ÜÇ ARKADAŞ. TEK ÇIKIŞ.' : '') + (t > 2.6 ? '<div style="font-size:30px;letter-spacing:8px;margin-top:26px;color:#a8a296">TEK BAŞINA YA DA 3 KİŞİ ONLINE</div>' : '');
      }
      if (name === 'sting') {
        const on = t > 1.2 && t < 2.0;
        black.style.opacity = on ? 0 : 1; text('', '', 0);
        cam(cc(15), cc(16), -Math.PI / 2, .03); S.flashOn = true; S.fearKick = 1;
        L.visible = on;
        if (on) {
          const k = cl((t - 1.2) / .35, 0, 1), dist = lerp(3.2, .55, k * k);
          L.rotation.set(0, -Math.PI / 2, 0); L.position.set(0, 0, 0);
          u.spine.rotation.x = .75; u.neck.rotation.x = -.55; u.jaw.rotation.x = .9 + Math.sin(t * 50) * .1; K.spreadJaw(u); u.head.rotation.z = Math.sin(t * 37) * .25;
          u.arms.forEach(a => { a.sh.rotation.x = -1.9; a.sh.rotation.z = a.s * .7; a.el.rotation.x = -.6; });
          K.placeHeadAt(L, V(cc(15) + dist, 1.64, cc(16))); K.player.shake = 1; S.glitch = .5;
        }
        if (t > 2.0) { tr.style.opacity = cl((t - 2.15) / .3, 0, 1); $('trBig').innerHTML = '<span style="font-size:150px;color:#b00d0d">KÖR</span>'; $('trSub').textContent = 'ŞİMDİ OYNA'; }
      }
    },
  };
};

(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--autoplay-policy=no-user-gesture-required', '--mute-audio', '--disable-dev-shm-usage', '--js-flags=--max-old-space-size=4096'] });
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  p.setDefaultTimeout(900000);
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.addInitScript(stepper);
  await p.goto('file://' + require('path').resolve(__dirname, '../../kor.html'));
  await p.waitForFunction(() => window.__kor && __kor.items.length > 0);
  await p.evaluate(() => { document.querySelector('#qRow .btn[data-q="1"]').click(); });
  await p.click('#bStart');
  for (let i = 0; i < 8; i++) await p.click('#intro', { force: true }).catch(() => {});
  await p.evaluate(DIRECTOR);
  const needAv = SHOTS.slice(from, to + 1).some(s => ['friends', 'revive', 'chase', 'escape'].includes(s[0]));
  await p.evaluate(n => TR.init(n), needAv);
  for (let i = 0; i < 4; i++) await p.evaluate(() => __advance(1000 / 24));
  const dt = 1 / FPS;
  for (let si = from; si <= to; si++) {
    const [name, a, bnd] = SHOTS[si];
    await p.evaluate(n => TR.setup(n), name);
    if (name === 'gameplay') await p.keyboard.down('KeyW');
    // ısınma: ışıklar ve gölgeler otursun
    for (let w = 0; w < 3; w++) await p.evaluate(([n]) => { TR.frame(n, 0, 1 / 24); __advance(1000 / 24); }, [name]);
    const n0 = Math.round(a * FPS), n1 = Math.round(bnd * FPS);
    const PREV = process.env.PREVIEW ? process.env.PREVIEW.split(',').map(Number) : null;
    for (let f = n0; f < n1; f++) {
      if (PREV) { const rel = (f - n0) / (n1 - n0); const want = PREV.some(q => Math.abs(rel - q) < .5 / (n1 - n0)); const t = (f - n0) / FPS;
        if (!want) { if ((f - n0) % 6 === 0 || PREV.some(q => rel < q && rel > q - 8 / (n1 - n0))) await p.evaluate(([n, t, dt]) => { TR.frame(n, t, dt); __advance(dt * 1000); }, [name, t, dt]); else await p.evaluate(([n, t, dt]) => { TR.frame(n, t, dt); __advance(1); }, [name, t, dt]); continue; } }
      const t = (f - n0) / FPS;
      await p.evaluate(([n, t, dt]) => { TR.frame(n, t, dt); __advance(dt * 1000); }, [name, t, dt]);
      await p.screenshot({ path: process.env.PREVIEW ? `${__dirname}/prev/${name}_${String(f).padStart(5, '0')}.jpg` : `${OUT}/${String(f).padStart(5, '0')}.jpg`, type: 'jpeg', quality: process.env.PREVIEW ? 70 : 92 });
      if (f % 24 === 0 || process.env.PREVIEW) console.log(name, f, new Date().toISOString().slice(11, 19));
    }
    if (name === 'gameplay') await p.keyboard.up('KeyW');
  }
  await b.close();
  console.log('BİTTİ', from, to);
})();
