# TERS BOMBA — Kaotik Co-op Bomba İmha

3-5 arkadaş, 1 bomba, 0 mantık. Biri **tersten konuşur**, birinin **yürüme tuşları sürekli
karışır**, biri **havada süzülür**, biri **konuşamaz**, biri **fare boyundadır**. Herkesin
bilgisi farklıdır; kimse bombayı tek başına çözemez.

## Hemen oyna (kurulum yok)
Repo kökündeki **`tersbomba.html`** dosyasını tarayıcıda aç (internet gerekir) ya da sunucuda
`/tersbomba.html` adresine git. Biri **Oda Kur** der, 5 harfli kodu diğerleri **Katıl** ile girer.
Tek başına denemek için **Antrenman**: oyunda `TAB` ile roller arasında geçilir.

## v2.1 ile gelenler
- **Yeni görsel kimlik:** "Ters Bomba A.Ş. İmha Eğitim Tesisi". Afiş yazı tipi, tehlike şeritleri,
  çelik paneller, daktilo yazılı gizli notlar, çizgi ikon seti, 7 parçalı LED sayaç.
- **Sade ekranlar:** tek sütun ana menü, rol dosyalı ekip odası, küçülen görev kartı (`H` ile açılır).
- **Yeni oda havası:** boyalı beton duvarlar, koyu parlak zemin, lamba huzmeleri, LED şeritler,
  ikaz lambaları, duvar sayacı, canlı ekranlı kontrol masası, dolaplar, sarkan kablolar.
- **Lazer Kilidi (5 kişi):** İŞARETÇİ duvarlardaki 4 sensörü lazerle doğru sırada vurur; sırayı
  sadece MİNİK bilir.
- **Büyük final:** tüm modüller bitince herkes aynı anda kendi renkli plakasına basmalı.

## v2.0 ile gelenler
- **2 yeni modül:** 🧭 Labirent (yolu sadece uçan görür, karışık tuşlu oyuncu yürür) ve
  🔑 Çift Anahtar (iki kişi odanın iki ucunda aynı anda çevirir).
- **4 yeni kaos olayı:** 📞 çalan telefon (açan +12 sn kazandırır), 🌫️ sis, 🫨 deprem, 🥤 kafein.
- **Mutatörler:** Gece Vardiyası, Helyum Partisi, Kaos Yağmuru, Hız Bombası, Ayna Dünya.
- **Puan, 3 yıldız, rütbeler, rekorlar, 13 başarım** ve profil ekranı.
- Laf atan bomba, son 10 saniye kalp atışı, rol tanıtımı, havai fişekli zafer.
- Gündüz / gün batımı / gece temaları, ışık huzmeleri, film efekti, kenar yumuşatma.
- Menü müziği ve zenginleşen gerilim müziği.
- Hata düzeltmeleri: duran oyuncunun görünmez olması, `H` tuşunun yürüme tuşu olarak
  atanması, oda sahibi çıkınca oyunda takılı kalma, tur başına bellek sızıntısı ve daha fazlası.

## EXE yap (Windows)
1. [Node.js](https://nodejs.org) LTS sürümünü kur (bir kere).
2. Bu klasördeki **`EXE-YAP.bat`** dosyasını çift tıkla.
3. Bitince `exe/Ters-Bomba.exe` hazır: tek dosya, kurulum istemez, tam ekran açılır (F11).

GitHub'da: `tersbomba.html` ya da `tersbomba/` değiştiğinde **Actions → Ters Bomba EXE**
iş akışı EXE'yi kendisi derler ve `tersbomba-son` sürümüne yükler.

## Steam için
```bash
npm install
npm run steam     # exe/win-unpacked/ klasörünü üretir
```
`exe/win-unpacked/` klasörünün tamamı Steam deposuna (SteamPipe) yüklenecek içeriktir; başlatma
dosyası `Ters Bomba.exe`. Bu paket Three.js, PeerJS ve yazı tiplerini içinde taşır, CDN'e
ihtiyaç duymaz. Çok oyunculu bağlantı için oyuncuların interneti yine gerekir (PeerJS).

Steam'e çıkmadan önce yapılacaklar (bu repoda yok):
- Steamworks SDK bağlanması (Steam başarımları, arkadaş daveti, overlay). Şu an başarımlar
  ve rekorlar bilgisayarda yerel olarak saklanır.
- Kendi PeerJS / TURN sunucun: herkese açık PeerJS bulutu yoğun kullanımda sınırlıdır ve bazı
  ağlarda (katı NAT) doğrudan bağlantı kurulamaz. Adres `?ph=...&pp=...&sec=1` ile verilebilir.
- İngilizce dil desteği (oyun şu an yalnızca Türkçe).
- EXE'nin kod imzalanması (yoksa Windows SmartScreen uyarı gösterir).

## Geliştirme
Oyunun kaynağı tek dosyadır: repo kökündeki `tersbomba.html`.
```bash
npm install
npm run build     # ../tersbomba.html -> dist-web/index.html (her şey içine gömülü)
npm start         # Electron penceresinde dene
```
