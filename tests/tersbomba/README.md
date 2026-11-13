# Ters Bomba — otomatik çok oyunculu testler

`tersbomba.html` için Playwright tabanlı test düzeneği. Her oyuncu ayrı bir tarayıcı bağlamıdır (ayrı `localStorage`),
aynı odaya **gerçek PeerJS / WebRTC veri kanallarıyla** bağlanır. İnternet gerekmez:

- three.js ve PeerJS istekleri (`cdn.jsdelivr.net`) `node_modules`'tan karşılanır, Google Fonts boş cevaplanır.
- Sinyalleşme için yerel bir PeerServer, oyun dosyası için küçük bir HTTP sunucusu açılır (ikisi de boş bir porta; aynı anda birden çok koşu çakışmaz).
- Oyun `?norender=1` ile açılır: mantık çalışır, WebGL çizimi atlanır (hızlı).

## Çalıştırma

```bash
cd tests/tersbomba
npm install                      # peer, peerjs, three
npx playwright install chromium  # bir kez
node run.js                      # tüm senaryolar + özet tablo
node run.js smoke-5p             # yalnızca adı verilenler
node scenarios/smoke-solo.js     # tek senaryo, doğrudan
```

Playwright `package.json`'da yok; `require('playwright')` çözülebilmeli (global kurulum + `NODE_PATH`, ya da `npm i --no-save playwright`).
Başarısızlıkta çıkış kodu sıfırdan farklıdır; her istemcinin `state()` dökümü, sayfa hataları ve ekran görüntüsü (`out/`) basılır.

| Ortam değişkeni | Anlamı |
|---|---|
| `TB_NM` | `peer`, `peerjs`, `three` paketlerini içeren `node_modules` klasörü (varsayılan: `tests/tersbomba/node_modules`) |
| `TB_HTML` | Test edilecek oyun dosyası (varsayılan: `../../tersbomba.html`) |
| `TB_OUT` | Ekran görüntülerinin yazılacağı klasör (varsayılan: `out/`) |
| `TB_SLOW` | Tüm bekleme sürelerini çarpar (yavaş makine: `TB_SLOW=3`) |
| `TB_ALLOW_KNOWN` | `1` ise `t.bug(...)` ile işaretli bilinen oyun hataları FAIL yerine uyarı sayılır |
| `TB_HEADED` | `1` ise tarayıcı pencereli açılır |

## Senaryolar

- `scenarios/smoke-solo.js` — Antrenman: başlat, 10 modülü çöz, final plakası, `won` + bitiş ekranı.
- `scenarios/smoke-5p.js` — 5 istemci / 5 rol: rol tutarlılığı, durum yakınsaması, her modülü yetkili rolün çözmesi,
  yanlış rolün reddi, final (4/5 plakada kazanılmaz, 5/5'te kazanılır), herkeste bitiş ekranı.

## Yeni senaryo yazmak

`scenarios/` altına bir dosya ekle; `run.js` onu kendiliğinden bulur.

```js
const H = require('../harness');

H.run('ornek', async t => {
  const { clients, host, byRole: R } = await H.party(3);        // reader(oda sahibi), defuser, floater
  const P = await H.startGame(host, { diff: 'kolay', muts: ['hiz'] });
  await R.defuser.act('cut', { i: (P.wireAns + 1) % P.wires.length });   // bilerek yanlış kablo
  await H.waitAll(clients, () => __tb.game.strikes === 1);
  t.eq('herkes 1 hata görüyor', (await H.converge(clients)).strikes, 1);
  await H.solveModule(R, 'keypad', P);                           // doğru aksiyonları yetkili rolden yollar
  t.noErrors();
});
```

Kısa başvuru (`harness.js`):

- Kurulum: `startInfra()`, `launchBrowser()`, `newClient(browser, infra, { name, norender, quality, viewport, mic, initScripts, params })`,
  `hostRoom(c)` → kod, `soloRoom(c)`, `joinRoom(c, kod)`, `setRole(c, rol)`, `startGame(host, { diff, muts })` → bulmaca,
  `party(n, roller)` → `{ clients, host, code, byRole, infra, browser }`, `closeAll()`.
- İstemci: `c.state()`, `c.act(msg)` / `c.act('cut', { i })`, `c.tb('T.game.strikes')` (`T` = `window.__tb`), `c.eval(fn, arg)`,
  `c.waitFor(fn, ms, arg)`, `c.puzzle()`, `c.moveTo([x, y, z], { pin })`, `c.plate()`, `c.shot('dosya.png')`, `c.errors`.
- Toplu: `waitAll(clients, fn, ms, arg)`, `converge(clients, { tol })`, `solveModule(R, mod, P)`, `soloRoles(c)`, `toPlates(clients)`.
- `H.run(ad, async t => …)`: `t.step`, `t.log`, `t.check(etiket, koşul, ayrıntı)`, `t.eq(etiket, gelen, beklenen)`, `t.noErrors()`, `t.sleep(ms)`.
  Kontroller "yumuşak"tır: biri başarısız olsa da senaryo sürer, sonunda FAIL basılır; bekleme zaman aşımları istisna fırlatır.

Notlar: başsız tarayıcıda fare kilitlenemediği için `#pause` katmanı açık kalır (oyun mantığını engellemez); hareket
`c.moveTo` ile verilir. Sayfa içinde çalışan işlevler (`waitFor`, `eval`, `tb`) Node tarafındaki değişkenleri göremez, `arg` ile geçir.
