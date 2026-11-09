# KÖR tanıtım videosu

Oyunu kare kare oynatıp 1080p / 24 fps bir dakikalık tanıtım videosu üretir.

```bash
cd kor/trailer
node trailer.js 0 13          # 14 çekimin hepsini frames/ klasörüne çizer (paralel için aralıklara bölünebilir)
python3 synth.py trailer.wav  # müzik ve efektler (numpy + scipy gerekir)
ffmpeg -framerate 24 -i frames/%05d.jpg -i trailer.wav -c:v libx264 -b:v 7M -pix_fmt yuv420p \
  -af loudnorm=I=-14:TP=-1:LRA=11 -c:a aac -b:a 192k -shortest KOR_Tanitim_1080p.mp4
```

Ekran kartı olmayan bir makinede her kare birkaç saniye sürer. Çekim listesi ve zamanları
`trailer.js` içindeki `SHOTS` dizisinde, ses olaylarının zamanları `synth.py` içinde.
