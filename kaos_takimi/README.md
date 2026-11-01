# KAOS TAKIMI

2D, yukarıdan bakışlı, online co-op parti oyunu. Godot 4 + GDScript.

> **Şu anki durum:** AŞAMA 1 (Temel Oyun) — ana menü, KAOS FABRİKASI haritası,
> WASD ile hareket eden karakter ve onu takip eden kamera hazır.

---

## 1. Kurulum (ikiniz de aynen yapın)

1. **Godot 4.7.2** indirin: <https://godotengine.org/download/archive/4.7.2-stable/>
   - **"Godot Engine" (Standard)** sürümünü indirin, **.NET sürümünü değil.**
   - İkiniz de **aynı sürümü** kullanın. Farklı sürüm kullanırsanız Godot dosyaları
     farklı kaydeder ve git'te gereksiz çakışmalar çıkar.
   - Kurulum yok: zip'i açın, `Godot_v4.7.2-stable_win64.exe` dosyasını çalıştırın.
2. Bu depoyu bilgisayarınıza indirin (git clone / pull).
3. Godot açılınca **"İçe Aktar" (Import)** butonuna basın →
   `kaos_takimi/project.godot` dosyasını seçin → **"İçe Aktar ve Düzenle"**.
4. İlk açılışta Godot fontları ve ikonu içe aktarır (birkaç saniye).
5. Sağ üstteki **▶ (F5)** butonuna basın. Ana menü açılır.

> İlk açılışta "Çıktı" panelinde font ile ilgili kırmızı hata görürseniz
> Godot'u kapatıp tekrar açın. Bu, ilk içe aktarma sırasında bir kez olur.

---

## 2. Kontroller

| Tuş | Ne yapar |
|-----|----------|
| **W A S D** veya **ok tuşları** | Yürü |
| **ESC** | Oyun içi menü (Devam Et / Ana Menü) |
| **F11** | Tam ekran aç/kapat |
| **E** | (Henüz bir şey yapmıyor — AŞAMA 2'de "etkileşim" olacak) |

Tuşlar **fiziksel tuş konumuna** göre ayarlı. Yani Türkçe Q veya F klavyede de
W/A/S/D'nin bulunduğu yerdeki tuşlar çalışır.

---

## 3. Klasör yapısı

```
kaos_takimi/
├── project.godot              → Proje ayarları (pencere boyutu, tuşlar, başlangıç sahnesi)
├── icon.svg                   → Oyun ikonu
├── assets/                    → Resim, ses, font gibi "ham" dosyalar
│   ├── fonts/                 → Baloo 2 fontu (Türkçe karakter destekli) + lisansı
│   ├── ui/main_theme.tres     → Tüm butonların/panellerin görünümü (renk, köşe, font)
│   ├── sprites/               → (boş) İleride karakter/obje çizimleri buraya
│   └── audio/music, audio/sfx → (boş) AŞAMA 6'da müzik ve sesler buraya
├── scenes/                    → Oyunun sahneleri ve onlara ait scriptler
│   ├── main_menu/             → Ana menü
│   ├── maps/kaos_fabrikasi/   → KAOS FABRİKASI haritası
│   ├── player/                → Oyuncu karakteri
│   ├── objects/               → Haritadaki objeler (duvar, kutu, makine, bant...)
│   └── ui/                    → Oyun içi arayüz (HUD, ESC menüsü)
└── scripts/                   → Hiçbir sahneye ait olmayan genel scriptler
    ├── autoload/game_manager.gd → Oyun boyunca yaşayan yönetici (sahne geçişleri)
    └── utils/draw_utils.gd      → Kodla çizim yardımcıları
```

**Kural:** Bir sahne (`.tscn`) ile onun scripti (`.gd`) **aynı klasörde** durur.

---

## 4. Hangi dosya ne işe yarar?

| Dosya | Görevi | Değişirse neyi etkiler? |
|-------|--------|-------------------------|
| `scripts/autoload/game_manager.gd` | Sahne geçişleri (ekran kararıp açılır), oyuncu adı/rengi, F11 | Bütün oyun. Dikkatli değiştirin. |
| `scenes/main_menu/main_menu.tscn/.gd` | Ana menü ve butonları | Sadece menü |
| `scenes/main_menu/menu_background.gd` | Menü arka planı (dişliler, bant) | Sadece menü görüntüsü |
| `scenes/player/player.gd` | Hareket (hız, ivme), kamera sınırı | Karakterin hissi |
| `scenes/player/player_visual.gd` | Karakterin çizimi ve yürüme animasyonu | Menüdeki ve oyundaki karakter görüntüsü |
| `scenes/maps/kaos_fabrikasi/kaos_fabrikasi.tscn` | Haritanın tamamı (odalar, duvarlar, objeler) | Harita |
| `scenes/maps/kaos_fabrikasi/kaos_fabrikasi.gd` | Oyuncuyu doğurur, HUD ve ESC menüsünü bağlar | Harita açılışı |
| `scenes/objects/*.gd` | Her objenin çizimi ve çarpışması | O objenin **haritadaki bütün kopyaları** |
| `scenes/objects/factory_prop.gd` | Çarpışan objelerin ortak temeli | Kutu, varil, masa, makine, raf, duvar |
| `scenes/ui/hud.gd/.tscn` | Sol üst oda adı, sağ üst tuş bilgisi | Oyun içi ekran |
| `scenes/ui/pause_menu.gd/.tscn` | ESC menüsü | Oyun içi menü |
| `assets/ui/main_theme.tres` | Buton/panel stili | Bütün arayüz |

---

## 5. Haritayı düzenlemek

Bütün harita objeleri **`@tool`** scriptlerle çizildiği için Godot editöründe de
görünürler. `kaos_fabrikasi.tscn` dosyasını açın:

- **Taşımak:** Objeyi seçip fareyle sürükleyin.
- **Yeni obje eklemek:** `scenes/objects/` içinden bir `.tscn` dosyasını
  sürükleyip **`World`** düğümünün içine bırakın. (Zemin boyaları → `FloorDecals`,
  duvarlar → `Walls`, bantlar → `Conveyors`.)
- **Ayarlarını değiştirmek:** Objeyi seçin, sağdaki **Inspector** panelinden
  boyut, renk, kutu sayısı (`stack`), makine türü (`kind`) vb. değiştirin.

Harita katmanları (alttan üste çizim sırası):

| Düğüm | İçindekiler |
|-------|-------------|
| `Floors` | Oda zeminleri (`floor_zone`) — her birinin `room_name` değeri sol üstte görünür |
| `FloorDecals` | Yer boyaları, ikaz şeritleri, yağ lekeleri, giderler |
| `Conveyors` | Taşıma bantları |
| `Walls` | Duvarlar |
| `Doors` | Otomatik kapılar (oyuncu yaklaşınca açılır) |
| `World` | Oyuncular + kutular, makineler, masalar... (**Y-Sort** açık: aşağıdaki obje öne çizilir) |
| `SpawnPoints` | 10 oyuncunun doğma noktası |

Objelerin `(0,0)` noktası **yere değdikleri alt kenarın ortasıdır**. Böylece
karakter bir makinenin arkasına geçince makinenin arkasında kalır.

---

## 6. İki kişi birlikte çalışırken kurallar

1. **Çalışmaya başlamadan önce mutlaka `git pull` yapın.**
2. **Aynı anda aynı `.tscn` dosyasını düzenlemeyin.** Özellikle
   `kaos_fabrikasi.tscn` — birleştirmesi zor. Kim haritayla uğraşıyorsa
   diğerine haber versin.
3. Godot'un oluşturduğu **`.uid` ve `.import` dosyalarını commit'leyin.**
   Bunlar dosyaların kimlik bilgisidir; silinirse sahneler bozulabilir.
4. **`.godot/` klasörünü asla commit'lemeyin** (zaten `.gitignore` içinde).
5. Dosya taşırken/adını değiştirirken **Godot'un içindeki "Dosya Sistemi"
   panelini kullanın**, Windows Gezgini'ni değil. Godot bağlantıları otomatik düzeltir.
6. Küçük ve sık commit atın. Commit mesajına ne yaptığınızı yazın:
   `Harita: depoya 3 raf eklendi`.

---

## 7. Yol haritası

- [x] **AŞAMA 1 — Temel oyun:** proje, klasörler, ana menü, harita, karakter, WASD, kamera
- [ ] **AŞAMA 2 — Oyuncu sistemi:** animasyonlar, oyuncu itme, isimler, nesnelerle etkileşim (E), karakter ekranı
- [ ] **AŞAMA 3 — Görev sistemi:** görevler, ilerleme, puan
- [ ] **AŞAMA 4 — Kaos sistemi:** kaygan zemin, elektrik kesintisi, ters kontrol
- [ ] **AŞAMA 5 — Multiplayer:** host/client (ENet), 10 kişilik oda, senkronizasyon
- [ ] **AŞAMA 6 — Tamamlama:** sonuç ekranı, ses, müzik, optimizasyon
- [ ] **AŞAMA 7 — Steam hazırlığı:** Windows build, sunucu altyapısı

### İleriyi düşünerek yapılan seçimler
- `player.gd` içindeki `get_input_direction()` ayrı bir fonksiyon: ters kontrol (AŞAMA 4)
  ve online hareket (AŞAMA 5) sadece burayı değiştirerek eklenecek.
- ESC menüsü oyunu **durdurmuyor**: online oyunda bir kişi menü açınca herkes donmasın diye.
- Harita `spawn_player()` fonksiyonuyla oyuncu doğuruyor: AŞAMA 5'te her bağlanan
  oyuncu için aynı fonksiyon kullanılacak.
- Görev noktaları (`task_point`) şimdiden haritada ve `task_points` grubunda;
  AŞAMA 3'teki görev sistemi bunları otomatik bulacak.

---

## Lisanslar
- Font: **Baloo 2** — SIL Open Font License 1.1 (`assets/fonts/OFL.txt`). Türkçe dışı
  karakterler dosya boyutu için çıkarıldı.
