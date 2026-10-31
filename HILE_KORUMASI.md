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

### 3. Tespit olunca
- Koşu geçersiz olur: sıralamaya gitmez, elmas vermez.
- Ekranın üstünde kırmızı bant çıkar: "HİLE TESPİT EDİLDİ".
- Hesap kalıcı yasaklanır. Kanıt (alan, değer, dalga, seviye, süre, sürüm) sunucuya
  gönderilir. İnternet yoksa bir sonraki girişte gönderilir (`ban_pending`).
- 2 kişilik modda da çalışır: ev sahibi iki oyuncuyu da tarar. Konuğun bütün değerleri
  ev sahibinden geldiği için konukta bellek taraması yok, saat denetimi var.

## Sunucuda (server.py)
- `/player/report_cheat`: yalnızca `reason="ac"` ve kanıt türü `bellek` ya da `hiz` ise
  yasaklar.
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

## Sınırlar (dürüstçe)
- Oyun bilgisayarda çalışıyor. Exe'yi açıp kodu değiştiren ve korumayı söken biri,
  istemci tarafındaki her denetimi atlatabilir. Sunucu tarafı (elmas defteri, eşya
  bedeli, yasak) yine de geçerli kalır.
- Düşman nesneleri (canları) performans için mühürsüz.
