'use strict';
// PKG-A / A2: her 3/4/5 rollük kombinasyon ve her zorluk için 300 rastgele bulmaca → checkSolvable hepsini geçirmeli;
// şart rolü eksik kombinasyonlar ve bozulmuş bulmacalar reddedilmeli. Tek sayfada, ağ gerekmez.
const H = require('../harness');

H.run('a-solvable', async t => {
  const infra = await H.startInfra(), browser = await H.launchBrowser();
  const c = await H.newClient(browser, infra, { name: 'Solv' });
  const res = await c.tb(T => {
    const combos = [['reader', 'defuser', 'floater'], ['reader', 'defuser', 'floater', 'pointer'], ['reader', 'defuser', 'floater', 'tiny'], ['reader', 'defuser', 'floater', 'pointer', 'tiny']];
    const out = { total: 0, bad: [], mods: {}, holders: {} };
    for (const roles of combos) for (const diff of ['kolay', 'normal', 'zor']) {
      const key = roles.length + ':' + roles.slice(3).join('+') + ':' + diff, R = new Set(roles);
      for (let i = 0; i < 300; i++) {
        const P = T.genPuzzle(diff, new Set(roles), i % 2 ? ['hiz'] : [], roles.length), bad = T.checkSolvable(P, roles);
        out.total++;
        if (bad.length && out.bad.length < 5) out.bad.push({ key, bad });
        // checkSolvable'dan bağımsız denetim: her modülün uygulayıcısı ve bilgi sahibi bu rollerde var mı
        for (const m of P.mods) { const N = T.MOD_NEEDS[m]; if ((N.apply !== 'any' && !R.has(N.apply)) || (N.needs || []).some(r => !R.has(r)) || (N.chain && !R.has(P[N.info]))) out.bad.push({ key, indep: m }); }
        out.mods[key] = P.mods.join(','); out.holders[key] = [P.keypadInfo, P.duckInfo, P.mouseInfo].join(',');
      }
    }
    // şart rolü eksik kombinasyonlar
    out.missing = [['reader', 'defuser'], ['reader', 'floater', 'pointer', 'tiny'], ['defuser', 'floater', 'tiny'], ['pointer', 'tiny']].map(roles => T.checkSolvable(T.genPuzzle('normal', new Set(roles), [], roles.length), roles).length > 0);
    // bozulmuş bulmacalar
    const all = ['reader', 'defuser', 'floater', 'pointer', 'tiny'], mk = f => { const P = T.genPuzzle('normal', new Set(all), [], 5); f(P); return T.checkSolvable(P, all).length > 0; };
    out.broken = {
      wireAns: mk(P => { P.wireAns = (P.wireAns + 1) % P.wires.length; }), wireOut: mk(P => { P.wireAns = 99; }), pwWord: mk(P => { P.pw.word = 'XXXXX'; }), pwStart: mk(P => { P.pw.start = P.pw.cols.map((col, i) => col.indexOf([...P.pw.word][i])); }),
      fuse: mk(P => { P.fuseStart = P.fuseTarget.slice(); }), maze: mk(P => { P.maze.safe = [0, 19]; }), gold: mk(P => { P.ducks.gold = [1, 1, 2]; }), laser: mk(P => { P.laserSeq = [0, 0, 1, 2]; }),
      holder: mk(P => { P.mouseInfo = 'none'; }), modRole: T.checkSolvable(T.genPuzzle('normal', new Set(all), [], 5), ['reader', 'defuser', 'floater']).length > 0, noPw: mk(P => { P.pw = undefined; }),
    };
    return out;
  });
  t.eq('üretilen bulmaca sayısı (4 kombinasyon × 3 zorluk × 300)', res.total, 3600);
  t.check('hepsi çözülebilir', res.bad.length === 0, res.bad);
  t.log('modüller: ' + JSON.stringify(res.mods));
  t.log('bilgi sahipleri (sembol, ördek, fare): ' + JSON.stringify(res.holders));
  t.eq('3 rol normal: fare/lazer yok', res.mods['3::normal'], 'wires,button,keypad,password,fuse,ducks,maze,keys');
  t.eq('3+MİNİK normal: fare var, lazer yok', res.mods['4:tiny:normal'], 'wires,button,keypad,password,fuse,ducks,mouse,maze,keys');
  t.eq('3+İŞARETÇİ normal: fare/lazer yok', res.mods['4:pointer:normal'], 'wires,button,keypad,password,fuse,ducks,maze,keys');
  t.eq('5 rol normal: 10 modül', res.mods['5:pointer+tiny:normal'].split(',').length, 10);
  t.eq('zincir: 3 rol → floater, reader, (fare yok)', res.holders['3::normal'], 'floater,reader,reader');
  t.eq('zincir: +MİNİK → ördek bilgisi MİNİK, fare kodu TERS SES', res.holders['4:tiny:normal'], 'floater,tiny,reader');
  t.eq('zincir: +İŞARETÇİ → hepsi İŞARETÇİ', res.holders['4:pointer:normal'], 'pointer,pointer,pointer');
  t.check('şart rolü eksik 4 kombinasyon da reddedildi', res.missing.every(Boolean), res.missing);
  t.check('bozulmuş 11 bulmaca da reddedildi', Object.values(res.broken).every(Boolean), res.broken);
  t.noErrors();
});
