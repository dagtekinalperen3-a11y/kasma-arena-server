# OYUNU KORUMA — NE MÜMKÜN, NE DEĞİL

Oyunu herkese açacaksan önce şu gerçeği bilmen gerekiyor, çünkü kurduğun
her şey buna göre şekilleniyor:

> **Oyuncunun bilgisayarına verdiğin hiçbir şey gizli kalmaz.**
> .exe'ye çevirsen de, şifrelesen de, karıştırsan da — yeterince uğraşan
> biri içini görür. Bu Python'a özel bir zayıflık değil; Unity, Unreal,
> C++ ile yazılmış oyunlar için de geçerli.

Arkadaşının "bir program çalıştırıp her şeyi görmesi" bu yüzden. Onu
tamamen engelleyemezsin. **Ama zaten engellemen gerekmiyor** — önemli olan,
gördüğü şeyin işine yaramaması.

---

## 1) GERÇEK KORUMA: SUNUCU HAKEM

Bu sürümde (v3.20) değeri olan her şey oyuncunun bilgisayarından çıkarıldı:

| Ne | Nerede tutuluyor | Hile denenirse |
|---|---|---|
| Elmas | sunucudaki hesapta | `/player/save` elmasın bir seferde en fazla 4000 artmasına izin verir |
| Skinler, petler, kostümler | sunucudaki hesapta | liste yalnızca BÜYÜYEBİLİR, istemci silemez |
| İstatistikler | sunucudaki hesapta | her alan yalnızca büyüyebilir |
| Dünya sıralaması | sunucu | giriş + imza + makullük denetimi; jetonsuz gönderi reddedilir |
| Sıralamadaki ad | sunucu | adı SUNUCU yazar, istemciden geleni değil |
| Google client secret | yalnızca sunucuda | .exe'nin içinde hiç yok |

Oyuncu `kasma_arena13.py`'yi açıp `self.gems = 999999` yazsa ne olur?
Kendi ekranında 999999 elmas görür. Hesabına yazılmaz, mağazadan aldığı
hiçbir şey kalıcı olmaz, dünya sıralamasına giremez. **Kendini kandırmış
olur, başkasını değil.** Hile korumasının amacı tam olarak budur.

---

## 2) OYUNCUNUN BİLGİSAYARINDA YAPILANLAR

Bunlar "kararlı saldırganı durdurma" iddiasında değil; **kolay hile yolunu
kapatma** iddiasındadır. Bir sayıyı Not Defteri'yle değiştirmek 10 saniye
sürüyorsa herkes yapar; 3 saat sürüyorsa kimse yapmaz.

- **Kayıt dosyası şifreli.** `kasma_save.json` artık okunabilir JSON değil.
  Açan biri `KASMA1` başlığı ve anlamsız bir metin görür.
- **Kayıt dosyası imzalı** (HMAC-SHA256) ve imza **bu bilgisayara bağlı**.
  Dosyayı düzenleyen ya da başkasının kaydını kopyalayan yakalanır; o kayıt
  bir daha dünya sıralamasına giremez.
- **Elmas defteri.** `gems` her zaman `kazanılan - harcanan` olmak zorunda.
  Yalnızca elması şişiren biri bu denetime takılır.
- **Koşu içi denetim.** Hasar/can/hız oyunun kendi üretebileceği tavanın
  üstüne çıkarsa (bellek düzenleyici) koşu geçersiz sayılır.
- **Oturum jetonu cihaza bağlı.** Kayıt dosyası çalınıp başka bilgisayara
  taşınsa bile o jetonla hesaba girilemez — sunucu reddeder.

---

## 3) .EXE'YE ÇEVİRME

### En kolay yol: PyInstaller

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name "Kasma Arena" kasma_arena13.py
```

`dist/Kasma Arena.exe` çıkar. **Ama:** PyInstaller .exe'si içindeki Python
kodu `pyinstxtractor` + bir decompiler ile geri çıkarılabilir. Yani
arkadaşının yaptığı şey bundan sonra da mümkün olur.

### Geri çevirmesi ZOR yol: Nuitka

Nuitka, Python'u gerçek makine koduna (C üzerinden) derler. Çıkan .exe'de
geri çevrilebilir Python kodu **yoktur**; elinde kalan şey, herhangi bir
C programı gibi, assembly'dir.

```bash
pip install nuitka
python -m nuitka --standalone --onefile --windows-disable-console ^
  --enable-plugin=no-qt --include-package=pygame ^
  --output-filename="KasmaArena.exe" kasma_arena13.py
```

İlk derleme 10-20 dakika sürer. Oyun tek dosyadan ibaret olduğu için
Nuitka ile sorunsuz derlenir.

> Nuitka bile "kırılamaz" demek değildir — assembly okuyan biri yine
> çalışır. Ama bu, "oyun kodunu merak eden arkadaş" ile "tersine mühendislik
> bilen biri" arasındaki fark kadar büyük bir fark.

### İkisinde de yapman gerekenler
- `-OO` ile derle (docstring'ler ve assert'ler çıkar).
- `ONLINE_API_URL` dışında **hiçbir sır oyuna koyma**. Şu an koymuyorsun.
- `.pyc` ya da kaynak dosyayı .exe'nin yanına **koyma**.

---

## 4) BİLEREK AÇIK BIRAKILAN TEK ŞEY

`SUBMIT_SECRET` oyunun içinde duruyor (skor gönderisini imzalamak için).
Oyunu çözümleyen biri bunu bulabilir. **Zarar veremez**, çünkü skorun
sıralamaya girmesi için imza TEK BAŞINA yetmiyor:

1. geçerli bir oturum jetonu gerekiyor (hesap + giriş),
2. jeton o cihaza bağlı olmalı,
3. skorun makullük denetiminden geçmesi gerekiyor,
4. gönderim hızı sınırlı.

İstersen `KASMA_SUBMIT_SECRET` ortam değişkenini değiştirip hem sunucuda
hem oyunda güncelleyebilirsin; eski sürümlerle imzalanan gönderiler
reddedilir.

---

## 5) SIRADAKİ ADIM (istersen)

Şu an eksik olan tek ciddi şey: **hesabı ele geçirilen oyuncunun kurtarma
yolu** (şifre sıfırlama). Bunun için e-posta gönderen bir servis gerekiyor
(Resend / SendGrid — ikisinin de ücretsiz katmanı var). Eklemek istersen
sunucuya 2 uç, oyuna 1 ekran ekleniyor.
