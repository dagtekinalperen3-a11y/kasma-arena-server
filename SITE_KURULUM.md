# Site + Çark + Kazı Kazan kurulumu

## Render (sunucu)
1. `server.py` bu dalla birlikte yayına girer (yeni uçlar: `/site/link`, `/site/exchange`,
   `/site/login`, `/site/me`, `/site/wheel/ad`, `/site/wheel/spin`, `/site/scratch/buy`).
2. Render > Environment'a ekle:
   - `SITE_SECRET` = uzun, rastgele bir metin (ör. 64 karakter). Site geçişlerini imzalar.
     Boş kalırsa SUPABASE_KEY'den türetilir; yine de ayrı bir değer koy.
   - `SITE_ORIGINS` = `https://volvearena.shop,https://www.volvearena.shop`
     (alan adın farklıysa onu yaz; yalnız bu adresler `/site/` uçlarını çağırabilir).
3. Veritabanında yeni tablo/sütun gerekmez: sayaçlar `ilerleme.veri.rewards` içinde.

## Hostinger (volvearena.shop / public_html)
Site artık çok sayfalı. `site/dist/` klasörünün **içindeki her şeyi** public_html'e yükle
(eski `index.html`'in üzerine yazılır):
- `index.html` (ana sayfa), `karakterler.html`, `silahlar.html`, `evrimler.html`, `kitaplar.html`,
  `kostumler.html`, `rehber.html`, `oyunlar.html` (Oyun Salonu), `kazi.html`, `magaza.html`
- `assets/` klasörü (`site.css`, `site.js`, `data.js`, `config.js`)
- `default.php` (indirme sayacı) ve `.htaccess` (gizli dosya: dosya yöneticisinde "gizli dosyaları göster")
Kolaylık için aynı içerik `site_dist.zip` olarak da var: public_html'de zip'i yükleyip "Extract" de.

## AppLixir ödüllü video (Şans Çarkı)
Sitede başka hiçbir reklam yok (Adsterra / sponsor bağlantıları kaldırıldı). Çark, ÇEVİR'e
basınca AppLixir ödüllü videosunu oynatır; video bitince çark açılır.
1. **API anahtarını yaz:** Hostinger'da `public_html/assets/config.js` dosyasını aç, tek satır:

       window.EA_CFG={applixirKey:"BURAYA-API-ANAHTARIN"};

   Yeniden derlemek gerekmez (dosya hep taze yüklenir). Kalıcı olsun diye aynı anahtarı
   depodaki `site/config.json` içine de yaz (`"applixir_api_key": "..."`); sonraki derlemeler onu kullanır.
2. SDK her sayfada yüklü (`https://cdn.applixir.com/applixir.app.v6.1.0.js`), video çarkın
   panelindeki `<div id="applixir-ad">` çapasına açılır.
3. Akış (`site/src/site.js`, `axPreload` / `axShow`): sayfa açılınca reklam önceden yüklenir
   (`preloadAd`). ÇEVİR'e basınca sunucu bekleme sayacını başlatır (`/site/wheel/ad`), sonra
   `adHandle.show()`. `status.type === "complete"` gelince çark açılır. Önceden yüklenmiş
   reklam yoksa `initializeAndOpenPlayer` ile açılır.
4. Ödülü **sunucu** verir: `/site/wheel/spin` ancak sayaç başladıktan en az 15 sn sonra kabul
   edilir. Reklam engelleyici yüzünden video açılmazsa oyuncu 15 sn bekleyip yine çevirebilir.

## Hız
- Reklam betikleri kaldırıldı, görseller WebP (data.js ~%22 küçük), `.htaccess` sıkıştırma
  (gzip) ve 1 yıllık önbellek açık: ikinci girişte site anında açılır.
- Render ücretsiz planı 15 dakika istek gelmeyince sunucuyu uyutuyordu (ilk giren 30-60 sn
  bekliyordu). Sunucu artık 10 dakikada bir kendi `/health` adresini yokluyor ve uyumuyor
  (Render `RENDER_EXTERNAL_URL` değişkenini kendisi verir). Site de açılır açılmaz sunucuyu dürter.

## Giriş / oturum
- Site oturumu tarayıcıda 7 gün kalır (sayfa yenilense, yeni sekme açılsa da). Site açıkken
  her `/site/me` isteğinde oturum tazelenir. Şifre değişince bütün site oturumları düşer.
- Sayfa açılır açılmaz son bilinen ad ve elmas gösterilir, sunucu cevap verince güncellenir.
  Sunucu uyanırken altta "Sunucuya bağlanılıyor…" bandı çıkar; ağ hatası yüzünden çıkış yapılmaz,
  yalnız sunucu "oturum geçersiz" derse çıkış yapılır.
- `server.py` mutlaka yeni sürümüyle yüklenmeli (yeni uçlar: `/health`, `/site/gemwheel/spin`,
  `/site/me` oturum tazeleme). Render'da `SITE_ORIGINS` boşsa `https://volvearena.shop` ve
  `https://www.volvearena.shop` kabul edilir; başka bir adres kullanıyorsan onu da ekle.
- Mağaza sayfasındaki "Satın al" düğmeleri `odeme.php`'ye gider. Bu dosya sunucunda yoksa
  düğmeler ölü bağlantı yerine "satın alma oyunun içinden" penceresini açar.

## Siteyi yeniden derlemek
Oyuna yeni skin/kitap/silah eklenince:

    pip install pygame-ce pillow
    python tools/build_site.py

Kaynaklar `site/src/` (iskelet, sayfalar, CSS, JS) ve `site/static/`. `site/dist/`'i elle
düzenleme; kaynağı düzenleyip derle.

## Nasıl çalışıyor
- Oyunda Mağaza > Şans Çarkı > ÇEVİR: sunucudan tek kullanımlık 10 dakikalık kod alınır,
  site `https://volvearena.shop/#k=KOD` ile açılır ve hesap otomatik bağlanır.
  (Sitede kullanıcı adı/şifre ile de girilebilir; Google hesapları oyundan açmalı.)
- Çark her sayfada sağ alttaki yuvarlak düğmede. ÇEVİR -> ödüllü video -> (en az 15 sn, sunucu sayar) -> ÇEVİR!
  Günde 5 hak. Sonucu sunucu seçer, ödül hesaba anında yazılır.
- Kazı kazan: 5K / 10K / 50K / 100K (100K'lık kartta en büyük ödül 5.000.000). Bedel düşülür ve ödül satın alırken sunucuda belirlenip
  aynı anda hesaba yazılır. Sayfada gizli sonuç ya da kod yoktur.
- Oyun açıkken sitede kazanılan/harcanan elmas, oyun eski bir kayıtla gelse bile kaybolmaz
  (`rewards.srv_earned / srv_spent` sayaçları).

## Oyun Salonu (oyunlar.html)
- Yazı tura (2 kişi), blackjack (2 kişi), pişti (2 ya da 4 kişi): oyuncular arası, bahis
  1K / 5K / 10K / 25K / 50K / 100K / 150K / 200K / 300K / 500K / 1M. Kazanan pot − %5 alır;
  berabere kalınırsa herkesin elması geri döner. Oyun bitince "Tekrar oyna" aynı ayarla yeni masa açar.
  Rulet kasaya karşı (tek sıfırlı Avrupa ruleti, çevirme başına en çok 1.000.000).
- Elmas Çarkı (kasaya karşı): bahis 1K-250K, 16 dilim, x0 ile x10 arası çarpan; oranlar sayfada
  yazar (beklenen getiri ~%88). Sonucu sunucu seçer (`/site/gemwheel/spin`), günde en çok 300 çevirme.
- Bütün kartlar ve sonuçlar sunucuda (server.py, `/site/games/*`, `/site/roulette/spin`).
  Tarayıcıya deste, rakibin kapalı kartı ya da masadaki kapalı kartlar hiç gitmez.
- Yatırılan elmas masaya oturunca emanete alınır (`rewards.escrow`). Sunucu yeniden başlarsa
  kaybolan masaların emaneti oyuncunun bir sonraki site isteğinde kendiliğinden iade edilir.
- Aynı ağdan (aynı internet) iki hesap aynı masaya oturabilir. Süresi dolan oyuncu adına sunucu oynar.
- Render'da tek süreç (gunicorn -w 1) şart: masalar bellekte tutuluyor.

## 50M Tacı
Yalnızca yönetici verir: oyunda sohbete `tac50m kullanıcıadı` yaz (yönetici hesabıyla girişliyken).
Özelliği: elmas kazancı +%50.
