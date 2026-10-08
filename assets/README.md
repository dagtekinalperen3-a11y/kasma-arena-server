# ARENA BONK — logo ve ikonlar

`source/` içindeki üç orijinal görselden `python tools/make_assets.py` ile üretilir.

| Dosya | Ne için |
|---|---|
| `arena_bonk.ico` | Windows `.exe` ikonu (16–256 px). `build_exe.bat` bunu kullanır. |
| `icon_512.png` | Google Play uygulama ikonu (512×512, tam kare — köşeleri mağaza yuvarlar). |
| `icon_1024_rounded.png` | Yuvarlak köşeli ikon (Discord, web sitesi, sosyal medya profil resmi). |
| `badge_512.png` | Saydam zeminli yuvarlak amblem. |
| `logo.png` | Saydam zeminli birleşik logo: amblem + ARENA/BONK + slogan. |
| `feature_graphic_1024x500.png` | Google Play "öne çıkan görsel". |
| `banner_1600x640.png` | Afiş / kapak görseli. |

Oyunun içindeki logo, pencere ikonu ve amblem `kasma_arena13.py` sonundaki
`EMBED_*` sabitlerine gömülüdür (betik onları da günceller), bu yüzden `.exe`
tek başına dağıtılabilir.
