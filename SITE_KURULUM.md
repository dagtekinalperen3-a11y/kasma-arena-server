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
- `assets/` klasörü (`site.css`, `site.js`, `data.js`)
- `default.php` (indirme sayacı) ve `.htaccess` (gizli dosya: dosya yöneticisinde "gizli dosyaları göster")
Kolaylık için aynı içerik `site_dist.zip` olarak da var: public_html'de zip'i yükleyip "Extract" de.

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
- Çark her sayfada sağ alttaki yuvarlak düğmede. ÇEVİR -> sponsor bağlantısı yeni sekmede açılır -> 15 sn (sunucu sayar) -> ÇEVİR!
  Günde 5 hak. Sonucu sunucu seçer, ödül hesaba anında yazılır.
- Kazı kazan: 5K / 10K / 50K. Bedel düşülür ve ödül satın alırken sunucuda belirlenip
  aynı anda hesaba yazılır. Sayfada gizli sonuç ya da kod yoktur.
- Oyun açıkken sitede kazanılan/harcanan elmas, oyun eski bir kayıtla gelse bile kaybolmaz
  (`rewards.srv_earned / srv_spent` sayaçları).

## Oyun Salonu (oyunlar.html)
- Yazı tura (2 kişi), blackjack (2 kişi), pişti (2 ya da 4 kişi): oyuncular arası, bahis
  1K / 5K / 10K / 25K / 50K / 100K. Kazanan pot − %5 alır; berabere kalınırsa herkesin elması
  geri döner. Rulet kasaya karşı (tek sıfırlı Avrupa ruleti, çevirme başına en çok 100K).
- Bütün kartlar ve sonuçlar sunucuda (server.py, `/site/games/*`, `/site/roulette/spin`).
  Tarayıcıya deste, rakibin kapalı kartı ya da masadaki kapalı kartlar hiç gitmez.
- Yatırılan elmas masaya oturunca emanete alınır (`rewards.escrow`). Sunucu yeniden başlarsa
  kaybolan masaların emaneti oyuncunun bir sonraki site isteğinde kendiliğinden iade edilir.
- Aynı IP'den iki hesap aynı masaya oturamaz. Süresi dolan oyuncu adına sunucu oynar.
- Render'da tek süreç (gunicorn -w 1) şart: masalar bellekte tutuluyor.

## 50M Tacı
Yalnızca yönetici verir: oyunda sohbete `tac50m kullanıcıadı` yaz (yönetici hesabıyla girişliyken).
Özelliği: elmas kazancı +%50.
