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
Şu dosyaları yükle (eskilerin üzerine):
- `index.html` (depo kökündeki, derlenmiş tek dosya)
- `default.php` (indirme sayacı, artık aynı IP'den dakikada 1 sayım)
- `site/.htaccess` -> public_html/`.htaccess` (HTTPS zorlama + güvenlik başlıkları)

## Siteyi yeniden derlemek
Oyuna yeni skin/kitap/silah eklenince:

    pip install pygame-ce pillow
    python tools/build_site.py

`site/index.src.html` şablondur; `index.html`'i elle düzenleme, şablonu düzenleyip derle.

## Nasıl çalışıyor
- Oyunda Mağaza > Şans Çarkı > ÇEVİR: sunucudan tek kullanımlık 10 dakikalık kod alınır,
  site `https://volvearena.shop/#k=KOD` ile açılır ve hesap otomatik bağlanır.
  (Sitede kullanıcı adı/şifre ile de girilebilir; Google hesapları oyundan açmalı.)
- Çark: ÇEVİR -> sponsor bağlantısı yeni sekmede açılır -> 15 sn (sunucu sayar) -> ÇEVİR!
  Günde 5 hak. Sonucu sunucu seçer, ödül hesaba anında yazılır.
- Kazı kazan: 5K / 10K / 50K. Bedel düşülür ve ödül satın alırken sunucuda belirlenip
  aynı anda hesaba yazılır. Sayfada gizli sonuç ya da kod yoktur.
- Oyun açıkken sitede kazanılan/harcanan elmas, oyun eski bir kayıtla gelse bile kaybolmaz
  (`rewards.srv_earned / srv_spent` sayaçları).
