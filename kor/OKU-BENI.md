# KÖR — 3D Korku Oyunu

Kör bir yaratığın sese göre avlandığı terk edilmiş bir sanatoryumdan kaç.

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
