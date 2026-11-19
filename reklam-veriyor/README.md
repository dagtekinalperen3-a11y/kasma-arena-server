# Reklam Veriyor

Türkçe piksel reklam panosu. Site sahibi reklam alanı satar. Reklamveren boş alanı panodan seçer, sabit ücret öder, görselini, butonunu ve bağlantısını yükler, gösterim ve tıklama sayılarını izler.

- **Arayüz:** HTML, CSS ve JavaScript (`static/`)
- **Sunucu:** PHP 8 ve SQLite (`index.php`, `lib/`). MySQL gerekmez, paylaşımlı hostingde `public_html` içinde çalışır.
- **Ödeme:** iyzico Ortak Ödeme Sayfası. Denemek için test sağlayıcısı da var.

Kurulum adımları `KURULUM.txt` dosyasında.

## Geliştirme

```bash
cd reklam-veriyor
php -S 127.0.0.1:8000 index.php        # http://127.0.0.1:8000
python3 -m pytest -q tests             # satış akışı testleri (php -S'i kendisi başlatır)
python3 paketle.py                     # ../reklam-veriyor-public_html.zip
```

Testler şunları kontrol eder: fiyatın sunucuda hesaplanması, aynı alanın iki kişiye satılamaması (8 paralel istek), rezervasyon süresinin dolması, geç gelen ödemede alan boşsa satışın tamamlanması, alan doluysa iade, görsel doğrulama, bağlantı doğrulama, gösterim ve tıklama sayımı, süre uzatma, yönetici ayarları ve CSRF koruması.
