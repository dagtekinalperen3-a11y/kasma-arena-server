# KÖR — 3D Korku Oyunu

Kör bir yaratığın sese göre avlandığı iki katlı, terk edilmiş bir sanatoryumdan kaç.
Tek başına ya da **3 kişiye kadar arkadaşlarınla** oyna.

## Arkadaşlarla oynama
- Ana menü → **ARKADAŞLARLA OYNA** → biri **ODA KUR** der, çıkan 5 harfli kodu
  diğerleri **KATIL** ile girer. Oda sahibi **OYUNU BAŞLAT**'a basar.
- Herkesin rolü ve kendi görevi var (Elektrikçi, Hemşire, Bekçi). Görevini bitiren
  arkadaşlarına yardım eder. 3. bölüm hep birlikte kaçış.
- Yaratık birini yakalarsa yere düşer; yanına gidip **E basılı tutarak** kaldırın.
- **T** işaret koy, **1-4** hızlı mesaj, **V** gece görüş kamerası.
- Çok oyunculu için sunucuda (Render) `server.py`'nin bu sürümü çalışmalı ve başlatma
  komutu şu olmalı: `gunicorn server:app --worker-class gthread -w 1 --threads 64 --timeout 120`

## Hemen oyna (kurulum yok)
Repo kökündeki **`kor.html`** dosyasını çift tıkla. İnternetsiz çalışır, tek dosyadır,
arkadaşına da böyle atabilirsin.

## EXE yap (Windows)
1. [Node.js](https://nodejs.org) LTS sürümünü kur (bir kere).
2. Bu klasördeki **`EXE-YAP.bat`** dosyasını çift tıkla.
3. Bitince `exe/KOR-Korku-Oyunu.exe` açılır. Bu tek dosyayı arkadaşlarına at,
   kurulum istemez, çift tıklayınca oyun tam ekran açılır (F11 pencere/tam ekran).

GitHub'da: `kor/` klasörü her değiştiğinde **Actions → KÖR EXE** iş akışı EXE'yi
kendisi derler. Çalışmanın sayfasındaki **Artifacts** bölümünden indirebilirsin.

## Geliştirme
```bash
npm install
npm run build     # src/game.js + template.html -> ../kor.html ve dist-web/kor.html
npm start         # Electron penceresinde dene
```
