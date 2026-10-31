# Hile koruması

İlke: **dürüst oyuncu asla yakalanmaz.** "Çok hasar", "çok skor", "çok hızlı" gibi
tahmine dayalı eşiklerle yasak yok; güçlü ama dürüst koşular (mezarlık, cehennem, yemin,
evrim, ustalık) hiç sorun olmaz. Yasak yalnızca **kesin kanıt** bulununca konur.

## Oyunda (kasma_arena13.py)

### 1. Mühürlü değerler (bellek düzenleyici / Cheat Engine)
`Player`, `RunState`, `ComboMeter`, `WaveManager` sınıflarının bütün sayısal alanları
(can, maks can, hasar çarpanları, hız, zırh, kritik, bekleme süreleri, skor, öldürme,
altın, koşu elmas parası, seviye, tecrübe, dalga, koşu süresi, kombo...) oyunun kendi
kodu yazdığı anda gizli bir mühür alır. Mühür, değerin ikili gösterimi ile oturuma özel
rastgele bir anahtardan üretilir.
Silah ve kitap seviyeleri de mühürlü sözlükte durur.

- Değer bellekte dışarıdan değişirse oyunun kodu çalışmadığı için mühür tutmaz.
- Her yazmadan önce eski değerin mührü de kontrol edilir: her kare artan alanlarda
  (koşu süresi, can yenilenmesi) yapılan değişiklik bir sonraki karede "aklanamaz".
- Yarım saniyede bir bütün mühürler taranır, koşu biterken bir kez daha.
- Konum alanları (x, y, hız vektörü) mühürsüz: 2 kişilik eşitleme onları doğrudan kaydırır.

### 2. Hız hilesi (speedhack)
Oyun saati (QueryPerformanceCounter) ile duvar saati (`time.time`) karşılaştırılır.
5 saniyelik **üç ardışık** pencerede oyun saati %40'tan fazla hızlı akarsa hız hilesi.
Takılma, düşük FPS ve pencere küçültme oyun saatini yalnızca yavaşlatır. Sistem saatinin
tek seferlik ayarı da üç pencere boyunca sürmez.

### 3. Kod enjeksiyonu (DLL enjektörü / Extreme Injector / araya kod sokma)
Bellek mühürleri *dışarıdan* bellek düzenlemesini yakalar. Ama oyunun içine DLL sokup
oyunun **kendi Python yorumlayıcısında** kod çalıştıran biri (Extreme Injector + Python
yükü) değerleri oyunun yazma yolundan değiştirebilir; mühür de "oyun yazdı" sanır. Buna
karşı dört katman daha var:

1. **Kod kimliği.** Oyunun bütün kod nesneleri ve fonksiyon/sınıf tablosu açılışta
   kaydedilir. Mühürlü bir alana oyunun kendi kodu dışından ya da **ana iş parçacığı
   dışından** (DLL kendi thread'inde çalışır) yazılırsa = enjeksiyon.
2. **Denetim kancası** (`sys.addaudithook` — kaldırılamaz). Oyun hiçbir yerde
   `exec`/`compile`/`gc.get_objects`/`settrace` kullanmaz. Yerel koddan (çerçeve yok) ya
   da enjekte bir dizge çerçevesinden (`"<string>"`) böyle bir çağrı gelirse = enjeksiyon.
   Tembel modül yüklemeleri gerçek `.py` dosyasından geldiği için elenir: **dürüst oyunda
   yanlış alarm olmaz** (namedtuple, json, tembel import... hepsi denendi, temiz).
3. **Bütünlük.** Oyunun fonksiyonu ya da sınıf metodu başka bir şeyle değiştirilirse
   (korumayı kapatma yaması) = yama. Mühürlü nesnenin sınıfı/metodu gölgelenirse de yakalanır.
4. **Modül/işlem taraması (yalnız Windows).** İndirilenler / Masaüstü / Belgeler / Temp'ten
   yüklenmiş **imzasız DLL** = enjeksiyon → yasak. Ayrıca açık hile programı (Cheat Engine,
   Extreme Injector, Xenos, WeMod, x64dbg...) görülürse o koşu sıralamaya **gönderilmez**
   (sarı uyarı bandı; yasak değil, sadece geçersiz).

Enjeksiyon bulgusu *kalıcıdır*: o oyun açık olduğu sürece hiçbir koşu sıralamaya gitmez
(enjekte kod ilk satırda bulgu listesini silse bile gizli kopya kancada durur).

### 4. Eski/değiştirilmiş exe (sürüm kapısı)
Skor imzası **v2**: anahtar gizli anahtardan türetilir ve oyunun sürümü imzaya girer.
Hile korumasız eski sürümler (**3.49 ve öncesi**) artık dünya sıralamasına skor
gönderemez — sunucu `426 "oyunu güncelle"` döner. Yeni exe çıkınca sürüm yükseltilir.

### 5. Tespit olunca
- Koşu geçersiz olur: sıralamaya gitmez, elmas vermez.
- Ekranın üstünde kırmızı bant çıkar: "HİLE TESPİT EDİLDİ" (hile programı açıksa sarı bant).
- Hesap kalıcı yasaklanır. Kanıt (tür, alan, değer, dalga, seviye, süre, sürüm) sunucuya
  gönderilir. İnternet yoksa bir sonraki girişte gönderilir (`ban_pending`).
- 2 kişilik modda da çalışır: ev sahibi iki oyuncuyu da tarar. Konuğun bütün değerleri
  ev sahibinden geldiği için konukta bellek taraması yok; saat, kod ve DLL denetimi var.

## Sunucuda (server.py)
- **Sürüm kapısı:** `/submit` ve `/coop/submit`, `KASMA_MIN_VERSION`'ın (3.50) altındaki
  oyunları reddeder. İmza v2 olmayan (eski) gönderiler de reddedilir.
- `/player/report_cheat`: yalnızca `reason="ac"` ve kanıt türü `bellek`, `hiz`, `kod`
  (enjeksiyon/yama) ya da `dll` (yüklenen hile DLL'i) ise yasaklar.
  - Kanıt `geri_bildirim` tablosuna `tur = "hile"` olarak düşer. Mesajda kim, ne, hangi
    dalga ve sürüm yazar.
  - Hesabın sıralamadaki eski skorları gizlenir (`ranked = false`).
  - Eski oyun sürümlerinin "hile kodu" bildirimi yasaklamaz.
- Yasak yalnızca sunucuda değişir. Oyun dosyasından `board_banned=false` gönderilse de
  geri gelir. `/submit` yasaklı hesabın skorunu almaz.
- **Kayıt dosyası kurcalama:** gönderimde yeni görünen elmaslı skin ya da kıyafetin
  bedeli harcanmamışsa eşya reddedilir.
  - Eski ucuz fiyat için bedelin dörtte biri yeter.
  - Reddedilenler `rewards.ac_items`'a yazılır.
  - Şans çarkı ödülleri ve premium eşyalar zaten sunucuda yazıldığı için etkilenmez.
- Elmas zaten sunucu defterinde (`gems_earned` / `gems_spent`, gönderim başına üst sınır).

## Yönetici
- Hile kayıtları: Supabase › `geri_bildirim` tablosu, `tur = hile`.
- Yasağı kaldırmak: oyunda yönetici hesabıyla sohbete `unban kullanıcıadı`
  (ya da `banac kullanıcıadı`). Kaldırılınca oyuncunun oyunundaki yasak da kendiliğinden
  kalkar. Gizlenen eski skorlar gizli kalır, yeni skorlar sıralamaya girer.

## Yeni sürüm çıkarırken (ÖNEMLİ)
Hile koruması oyunun içinde. Koruma güncellemesi oyuncuya ancak **yeni exe** ile ulaşır:
1. `kasma_arena13.py` ile `EvolveArena.exe`'yi yeniden derle (PyInstaller) ve siteye koy.
2. `server.py`'yi Render'a yükle (sürüm kapısı + yeni imza orada çalışmalı).
3. `GAME_VERSION` (oyun) ile `KASMA_MIN_VERSION` (sunucu) birbirini tutmalı. Eski exe
   oynayanlar "oyunu güncelle" uyarısı alır ve skor gönderemez — bu kasıtlı.

## Sınırlar (dürüstçe)
- Oyun bilgisayarda çalışıyor. Yeterince uğraşan biri exe'yi tersine çevirip korumayı
  tamamen sökebilir; ama bunu yapan **eski/değiştirilmiş** bir exe artık sürüm+imza
  kapısından geçemez, enjeksiyon/DLL/yama katmanları da ayağa kalkar. Sunucu tarafı
  (elmas defteri, eşya bedeli, yasak, imza) her hâlükârda geçerli kalır.
- Hile programını (Cheat Engine vb.) açık tutan oyuncu yasaklanmasa bile o koşusu
  sıralamaya giremez.
- Düşman nesneleri (canları) performans için mühürsüz.
- Modül/işlem taraması yalnız Windows'ta; Linux/Mac derlemelerinde bu katman atlanır
  (öbür dört katman çalışır).
