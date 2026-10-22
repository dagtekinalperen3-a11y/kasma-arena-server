# EvolveArena — Google Play ve App Store'a Yükleme Rehberi

Oyun artık Python/pygame değil: **TypeScript + PixiJS (WebGL)** ile yeniden yazıldı ve
**Capacitor** ile gerçek bir Android / iOS uygulaması olarak paketleniyor. Bütün oyun
mantığı, denge sayıları ve içerik (silahlar, kitaplar, karakterler, patronlar, haritalar,
cehennem, market, başarımlar, ustalık) Python sürümünden birebir aktarıldı.

```
mobile/
  src/            oyunun kaynak kodu (TypeScript)
  public/         simgeler, gizlilik politikası
  android/        Android Studio projesi (Capacitor)
  ios/            Xcode projesi (Capacitor, Swift Package Manager)
  store/          mağaza görselleri (simge, Play tanıtım görseli, ekran görüntüleri)
  tools/          görsel üretme aracı
.github/workflows/android.yml   → APK + AAB otomatik derleme
.github/workflows/ios.yml       → iOS derleme / TestFlight yükleme
```

---

## 1. Bilgisayarında çalıştırmak (isteğe bağlı)

Node.js 22 kur, sonra:

```bash
cd mobile
npm install
npm run dev          # tarayıcıda http://localhost:5173 — fare/klavye ile oynanır
npm run build        # dist/ klasörüne üretim derlemesi
```

Telefonda denemek için en kolay yol: GitHub → **Actions → Android** → son çalışmanın
**Artifacts** bölümünden `evolvearena-debug.apk` indir, telefona kur
(“bilinmeyen kaynaklara izin ver” gerekir).

---

## 2. Google Play

### 2.1 Hesap
1. <https://play.google.com/console> → geliştirici hesabı aç (tek seferlik 25 $).
   Kişisel hesaplarda Google, ilk yayından önce **12 test kullanıcısıyla 14 gün kapalı test**
   ister — “Kapalı test” kanalını bunun için kullan.
2. **Uygulama oluştur** → Ad: *EvolveArena*, Tür: Oyun, Ücretsiz.

### 2.2 Yükleme anahtarı (bir kez)
Bilgisayarında (Java yüklüyse) ya da Android Studio ile:

```bash
keytool -genkeypair -v -keystore upload.jks -alias upload -keyalg RSA -keysize 2048 -validity 10000
base64 -w0 upload.jks > upload.jks.b64      # macOS: base64 -i upload.jks -o upload.jks.b64
```

> `upload.jks` dosyasını ve şifresini **kaybetme ve depoya koyma**. Play App Signing
> açık olduğu için kaybedersen Play Console'dan yeni yükleme anahtarı istenebilir, ama
> uğraştırır.

GitHub deposu → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Değer |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | `upload.jks.b64` dosyasının içeriği |
| `ANDROID_KEYSTORE_PASSWORD` | keystore şifresi |
| `ANDROID_KEY_ALIAS` | `upload` |
| `ANDROID_KEY_PASSWORD` | anahtar şifresi |

### 2.3 Derleme
GitHub → **Actions → Android → Run workflow**. Bitince Artifacts'tan
`evolvearena-release.aab` dosyasını indir. (Sürüm kodu her çalışmada otomatik artar;
sürüm adı `mobile/package.json` içindeki `version`.)

### 2.4 Play Console'da doldurulacaklar
- **Uygulama paketi**: Test ve yayın → Kapalı test (ya da Üretim) → Yeni sürüm → AAB'yi yükle.
- **Mağaza girişi**: metinler `store/listing.md` dosyasında hazır (TR + EN).
  - Simge: `store/play-icon-512.png`
  - Öne çıkan görsel: `store/play-feature-graphic-1024x500.png`
  - Ekran görüntüleri: `store/screenshots/phone/*.jpg` (en az 2; `tr-` Türkçe, `en-` İngilizce) ve
    `store/screenshots/ipad-13/*.jpg` (tablet)
- **Gizlilik politikası URL'si**: `https://kasma-arena-server.onrender.com/privacy.html`
  (dosya depodaki `privacy.html`; sunucu yeniden dağıtıldığında yayında olur).
  **Önce** dosyadaki `ILETISIM@ORNEK.COM` yazan iki yeri kendi iletişim e-postanla değiştir
  (`privacy.html` ve `mobile/public/privacy.html`).
- **Uygulama içeriği** formları — önerilen cevaplar:
  - Reklam içeriyor mu: **Hayır**
  - Hedef kitle: 13+ (ya da “her yaş” istiyorsan Aileler politikasına uyum gerekir; 13+ seç)
  - İçerik derecelendirmesi (IARC anketi): çizgi film tarzı fantastik şiddet → genelde PEGI 7 / Everyone 10+
  - **Veri güvenliği**:
    - Veri toplanıyor mu: **Evet** (yalnızca isteğe bağlı hesap açılırsa)
    - Kişisel bilgiler → *E-posta adresi* ve *Kullanıcı kimlikleri (kullanıcı adı)*:
      toplanıyor, paylaşılmıyor, amaç: *Hesap yönetimi*; isteğe bağlı
    - Uygulama etkinliği → *Diğer uygulama içi etkinlik (oyun skorları)*: amaç *Uygulama işlevselliği*
    - Aktarım şifreli (HTTPS): **Evet**; Kullanıcı silme isteyebilir: **Evet**
  - **Hesap silme URL'si**: `https://kasma-arena-server.onrender.com/privacy.html`
    (sayfada oyun içi silme yolu ve e-posta ile silme anlatılıyor)
  - Oyun içi satın alma: **Yok** (eski sürümdeki gerçek parayla satılan özel karakterler
    artık oyun içi elmasla açılıyor — mağazalar dış ödeme sistemine izin vermez)

### 2.5 Otomatik yükleme (isteğe bağlı)
İlk AAB elle yüklendikten sonra: Play Console → Kurulum → API erişimi → hizmet hesabı
oluştur, “Yayınlar” iznini ver, JSON anahtarını `PLAY_SERVICE_ACCOUNT_JSON` secret'ı
olarak ekle. Sonra **Run workflow** ekranındaki `play_track` kutusuna `internal`
(ya da `beta` / `production`) yazınca derlenen paket doğrudan Play'e gider.

---

## 3. App Store (iOS)

### 3.1 Hesap
1. <https://developer.apple.com/programs/> → Apple Developer Program (yıllık 99 $).
2. <https://appstoreconnect.apple.com> → **Uygulamalar → +** → Bundle ID olarak
   `com.evolvearena.game` (önce developer.apple.com → Identifiers'da oluştur), Ad: EvolveArena.

### 3.2 Mac olmadan derleme (GitHub Actions)
App Store Connect → **Kullanıcılar ve Erişim → Entegrasyonlar → App Store Connect API**
→ anahtar oluştur (rol: *App Manager*), `.p8` dosyasını indir.

```bash
base64 -i AuthKey_XXXXXXXXXX.p8 -o key.b64      # Linux: base64 -w0 AuthKey_XXXX.p8 > key.b64
```

GitHub secret'ları:

| Secret | Değer |
|---|---|
| `APPLE_TEAM_ID` | developer.apple.com → Membership → Team ID |
| `ASC_KEY_ID` | API anahtarının Key ID'si |
| `ASC_ISSUER_ID` | API sayfasındaki Issuer ID |
| `ASC_KEY_P8_BASE64` | `key.b64` içeriği |

GitHub → **Actions → iOS → Run workflow**. İş bitince sürüm App Store Connect →
**TestFlight**'ta görünür (işlenmesi 5-30 dk). Sertifika / profil dosyası gerekmez:
Xcode bulut imzalaması API anahtarıyla bunları kendisi oluşturur.

### 3.3 App Store Connect'te doldurulacaklar
- Ekran görüntüleri: `store/screenshots/iphone-6.9/*.jpg` ve `store/screenshots/ipad-13/*.jpg`
- Metinler: `store/listing.md`
- Gizlilik politikası URL'si: yukarıdaki ile aynı
- **App Privacy** (Gizlilik etiketi): *Contact Info → Email Address* ve *Identifiers → User ID*
  ve *Usage Data → Other (gameplay scores)* — hepsi “App Functionality”, kimliğe bağlı,
  izleme (tracking) **yok**.
- Yaş derecelendirmesi: Cartoon or Fantasy Violence → *Infrequent/Mild* → 9+
- Şifreleme sorusu: Info.plist'te `ITSAppUsesNonExemptEncryption = NO` olduğu için sorulmaz.
- İnceleme notu (Review Notes): “Hesap isteğe bağlıdır, yalnızca dünya sıralaması için
  kullanılır. Hesap silme: RECORDS → WORLD → DELETE ACCOUNT.” Gerekirse bir deneme hesabı yaz.

---

## 4. Sunucu (Render)

`server.py` iki küçük değişiklik aldı, yeniden dağıtınca etkin olur:
- Mobil uygulamanın kökenleri (`https://localhost`, `capacitor://localhost`) CORS listesine eklendi.
- `/auth/delete` — hesabı ve bütün verisini silen uç (iki mağaza da zorunlu tutuyor).

Mobil skorlar `scores` tablosunda `platform = 'mobile'` ile ayrı tutulur (sunucunun mevcut
v3.45 mobil desteği). Yalnızca **Taş Meydan** koşuları ve giriş yapmış oyuncular sıralamaya
girer; skor imzası ve koşu kartı özeti Python sürümüyle birebir aynı yöntemle hesaplanır.

> Render'ın ücretsiz planı uykuya geçer; ilk istek 30-50 sn sürebilir. Oyun açılışta
> sunucuyu arka planda uyandırır, sıralama ekranı bunu bekler.

---

## 5. Yeni sürüm çıkarmak

1. Kodu değiştir, `mobile/package.json` → `version` alanını artır (ör. `4.0.1`).
2. Commit + push. Actions → Android ve iOS iş akışlarını çalıştır.
3. AAB'yi Play'e, iOS derlemesini TestFlight'tan incelemeye gönder.

## 6. Simge / görselleri yeniden üretmek

```bash
cd mobile && npm run dev   # ayrı terminalde
npx playwright install chromium
PLAYWRIGHT=playwright node tools/gen-assets.mjs
```

## 7. Paket adını değiştirmek istersen
Mağazaya ilk yüklemeden ÖNCE değiştirilebilir (sonra değiştirilemez): `capacitor.config.ts`
(`appId`), `android/app/build.gradle` (`applicationId`, `namespace`), Java paket klasörü,
`ios/App/App.xcodeproj/project.pbxproj` (`PRODUCT_BUNDLE_IDENTIFIER`) ve
`.github/workflows/android.yml` (`packageName`).
