# Kasma Arena (EvolveArena)

Yukarıdan bakışlı, dalga dalga gelen yaratıklara karşı hayatta kalma oyunu.
pygame ile yazıldı, telefon sürümü pygbag ile tarayıcıda çalışıyor.

Bu repoda iki şey var:

- `server.py`: hesaplar, dünya sıralaması, mağaza ve 2 kişilik mod için
  sunucu (Flask + Supabase). Render'da çalışıyor.
- `kasma_arena13.py`: oyunun kendisi.

## Oyunu çalıştırmak

```
pip install pygame
python kasma_arena13.py
```

## Sunucu

```
pip install -r requirements.txt
gunicorn server:app --worker-class gthread -w 1 --threads 64 --timeout 120
```

Render > Environment'a girilmesi gerekenler:

| değişken | ne için |
| --- | --- |
| `SUPABASE_URL`, `SUPABASE_KEY` | veritabanı (service_role anahtarı) |
| `KASMA_SUBMIT_SECRET` | skor imzası, oyundakiyle aynı olmalı |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google ile giriş (isteğe bağlı) |
| `BREVO_API_KEY` / `RESEND_API_KEY` + `MAIL_FROM` | şifre sıfırlama e-postası |
| `PLAY_ORIGINS` | telefon sürümünün GitHub Pages adresi |
| `PAYMENT_PROVIDER` + sağlayıcı anahtarları | TL ile satın alma |
| `DIAG_TOKEN` | `/diag` kurulum kontrolü |

Arayüz yazı tipleri Onest ve Russo One (SIL Open Font License 1.1),
oyunun içine gömülü; lisans metni [FONT_LICENSE.txt](FONT_LICENSE.txt).

Değişiklik notları: [CHANGELOG.md](CHANGELOG.md)
