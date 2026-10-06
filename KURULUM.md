# HESAP SİSTEMİ — ADIM ADIM KURULUM

Senin Supabase projen: **dagtekinalperen3-a11y's Project**
Şu an içinde tek tablo var: `scores`. Buna 2 tablo daha ekleyeceğiz.

Toplam süre: ~15 dakika. Hiçbir adımda oyunun kodunu değiştirmene gerek yok.

---

## ADIM 1 — Veritabanını kur (2 dakika)

1. Supabase panelinde sol menüden **SQL Editor** → **+ New query**
2. **`VERITABANI.sql`** dosyasının TAMAMINI yapıştır → **RUN**
3. "Success. No rows returned" yazmalı

Hepsi bu. Dosya şunları yapıyor:

| | Ne |
|---|---|
| `accounts` | hesaplar (kullanıcı adı + gmail birlikte) |
| `sessions` | oturumlar (jetonun yalnızca özeti, cihaza bağlı) |
| `player_data` | elmas, skinler, petler, istatistikler |
| `player_events` | **her değişiklik zamanıyla** — elmas artışı, yeni skin, koşu |
| `scores` | dünya sıralaması (var olana `account_id` eklenir) |
| 4 görünüm | `player_overview`, `oyuncu_gecmisi`, `dunya_siralamasi`, `oyuncu_detay()` |

> **Tekrar tekrar çalıştırabilirsin.** Her şey `if not exists` /
> `create or replace` ile yazıldı; var olan verine dokunmaz, yalnızca
> eksikleri tamamlar. Daha önce başka bir SQL çalıştırdıysan da bunu
> çalıştır.

> **ÖNEMLİ:** `accounts`, `sessions`, `player_data` ve `player_events`
> tablolarına **ASLA policy ekleme**. Şifre özetleri ve oturum jetonları
> orada; dışarıdan okunabilir olmamalılar. Sunucu service_role anahtarıyla
> bağlandığı için RLS onu bağlamaz.

## ADIM 2 — Supabase service_role anahtarını al (1 dakika)

Sunucunun `accounts`/`sessions` tablolarına yazabilmesi için **anon** değil
**service_role** anahtarı lazım.

1. Supabase'de sol altta **Project Settings** (dişli ikonu)
2. **API Keys** (ya da **API**) sekmesi
3. İki anahtar göreceksin:
   - `anon public` → **BUNU KULLANMA**
   - `service_role secret` → **BUNU KOPYALA** (gözü tıklayıp göster)
4. Aynı sayfadaki **Project URL**'i de kopyala
   (`https://mnjcdhllcmfqaejdmquv.supabase.co` gibi)

> service_role anahtarı **tam yetkilidir**. Yalnızca Render'ın
> Environment bölümüne yapıştır — Discord'a, GitHub'a, oyunun içine ASLA.

---

## ADIM 3 — Google OAuth istemcisi oluştur (6 dakika)

1. https://console.cloud.google.com adresine gir (Google hesabınla)
2. Üstteki proje seçiciden **New Project** → ad: `Kasma Arena` → **Create**
3. Sol menü: **APIs & Services → OAuth consent screen**
   - User Type: **External** → **Create**
   - App name: `Kasma Arena`
   - User support email: kendi e-postan
   - Developer contact: kendi e-postan
   - **Save and Continue**
   - **Scopes** ekranında **Add or Remove Scopes** → şu üçünü seç:
     `openid`, `.../auth/userinfo.email`, `.../auth/userinfo.profile`
     → **Update** → **Save and Continue**
   - **Test users** ekranında **+ Add Users** → kendi e-postanı ekle
     → **Save and Continue** → **Back to Dashboard**
4. Sol menü: **APIs & Services → Credentials**
   - **+ Create Credentials** → **OAuth client ID**
   - Application type: **Desktop app**  ← ÇOK ÖNEMLİ, "Web application" DEĞİL
   - Name: `Kasma Arena Oyun`
   - **Create**
5. Açılan kutuda iki değer var, ikisini de kopyala:
   - **Client ID** → `1234...apps.googleusercontent.com`
   - **Client secret** → `GOCSPX-...`

> **Desktop app** tipinde yönlendirme adresi girmene GEREK YOK.
> Google bu tipte `http://127.0.0.1:<port>` adreslerini otomatik kabul eder;
> oyun her girişte boş bir port seçiyor.

### Oyunu herkese açmak istediğinde
Şu an uygulama "Testing" modunda — yalnızca Test users'a eklediğin
e-postalar giriş yapabilir (en fazla 100 kişi). Oyunu yayınlayınca
**OAuth consent screen → Publish App** de. Google basit kapsamlar
(`email`, `profile`, `openid`) için doğrulama istemez, hemen açılır.

---

## ADIM 4 — Render'a ortam değişkenlerini gir (3 dakika)

1. https://dashboard.render.com → `kasma-arena-server` servisine gir
2. Sol menüden **Environment**
3. **Add Environment Variable** ile şunları tek tek ekle:

| Key | Value |
|---|---|
| `SUPABASE_URL` | Adım 2'deki Project URL |
| `SUPABASE_KEY` | Adım 2'deki **service_role** anahtarı |
| `GOOGLE_CLIENT_ID` | Adım 3'teki Client ID |
| `GOOGLE_CLIENT_SECRET` | Adım 3'teki Client secret |
| `KASMA_SUBMIT_SECRET` | `kasma-arena-submit-v1:3d7f90ac41be6528` |
| `DIAG_TOKEN` | Kendi uyduracağın uzun bir parola (örn. `tani-8f3a9c2e71b4`) |

4. **Save Changes** → Render servisi kendiliğinden yeniden başlatır (~2 dk)

> `SUPABASE_KEY` zaten varsa ve **anon** anahtarıysa, onu **service_role**
> ile DEĞİŞTİR. Anon anahtarla hesap tabloları yazılamaz.

> `KASMA_SUBMIT_SECRET` oyundaki `SUBMIT_SECRET` ile **birebir aynı**
> olmalı. Değiştirmek istersen ikisini birden değiştir, yoksa skor
> gönderimi "imza doğrulanamadı" der.

> `DIAG_TOKEN` olmadan `/diag` sayfası **açılmaz** (404 döner). Bu
> bilerek böyle: o sayfa veritabanının bütün tablo ve sütun adlarını
> listeliyor, yani herkese açık olması saldırgana hazır bir harita
> veriyordu. Kendi uydurduğun parolayı yaz ve sayfayı
> `https://...onrender.com/diag?key=PAROLAN` diye aç.

---

## ADIM 5 — server.py'yi güncelle

Render GitHub'a bağlıysa: `server.py`'nin yeni hâlini repoya push et,
Render kendiliğinden yeniden kurar.

Elle yüklüyorsan: Render'daki `server.py`'yi sana attığım dosyayla
değiştir ve **Manual Deploy → Deploy latest commit** de.

---

## ADIM 6 — Çalışıyor mu? (1 dakika)

Tarayıcıda **tanı adresini** aç — kurulumun tamamını tek bakışta söyler:

```
https://kasma-arena-server.onrender.com/diag?key=PAROLAN
```

(`PAROLAN` = Adım 4'te `DIAG_TOKEN` olarak yazdığın değer. Parolasız
açarsan sayfa 404 verir; bu bilerek böyle.)

Görmen gereken:

```json
{"supabase": true, "google": true, "ok": true,
 "yapilacak": ["her şey yerinde"]}
```

`ok: false` ise `yapilacak` listesi tam olarak neyin eksik olduğunu
söyler (hangi tablo yok, hangi sütun eksik). `tables` bölümünde her
tablonun durumu ayrı ayrı yazar.

Giriş yollarını ayrıca görmek istersen:

```
https://kasma-arena-server.onrender.com/auth/status
```

Görmen gereken:

```json
{"accounts": true, "google": true, "client_id": "....apps.googleusercontent.com"}
```

| Ne görüyorsun | Anlamı | Çözüm |
|---|---|---|
| `ok: true` | **Her şey hazır** | — |
| `"'player_data' tablosunda eksik sütun: ..."` | SQL eksik çalışmış | `VERITABANI.sql`'i tekrar çalıştır |
| `"'player_events' tablosu yok"` | eski kurulum | `VERITABANI.sql`'i çalıştır |
| `supabase: false` | Supabase bağlanamadı | `SUPABASE_URL` / `SUPABASE_KEY` yanlış |
| `google: false` | Google girişi kapalı (zorunlu değil) | Adım 3–4'ü kontrol et |
| 404 / sayfa yok | Eski `server.py` yayında | Adım 5 |

---

## OYUNCULARA BAKMAK

Supabase > **Table Editor** > sol listede dört görünüm var.

### `player_overview` — kim ne durumda
| kullanici_adi | gmail | giris_yolu | elmas | en_iyi_skor | skin_sayisi | pet_sayisi |
|---|---|---|---|---|---|---|
| KASMACI | leon@gmail.com | Google | 1240 | 128400 | 3 | 1 |

`skinler`, `kostumler_ve_petler`, `acilan_kitaplar`, `acilan_silahlar`
sütunlarına tıklayınca tek tek görürsün. En iyi skora göre sıralı gelir.

### `oyuncu_gecmisi` — saniyesine kadar ne oldu
| zaman | kullanici_adi | ne_oldu | degisim | sonraki_toplam | aciklama |
|---|---|---|---|---|---|
| 2026-10-05 00:13:54 | KASMACI | KOŞU | 1 | 43 | en iyi skor 128400 |
| 2026-10-05 00:12:30 | KASMACI | SKİN | 1 | 3 | gold |
| 2026-10-05 00:11:40 | KASMACI | ELMAS | -260 | 860 | harcandı |
| 2026-10-05 00:10:00 | KASMACI | ELMAS | +120 | 1120 | kazanıldı |

Her elmas artışı, her harcama, her yeni skin ve her koşu buraya
**zamanıyla** yazılıyor.

### `dunya_siralamasi` — skorlar hesaplarıyla
| sira | kullanici_adi | gmail | skor | dalga | hesapli |
|---|---|---|---|---|---|
| 1 | KASMACI | leon@gmail.com | 128400 | 17 | EVET |

`hesapli` sütunu, skorun bir hesaba bağlı olup olmadığını gösterir.
Yeni skorların hepsi EVET olmalı (girişsiz gönderim artık reddediliyor);
HAYIR olanlar v3.20 öncesinden kalan eski kayıtlardır.

### `oyuncu_detay('kullanıcıadı')` — tek oyuncunun her şeyi
SQL Editor'da:

```sql
select * from oyuncu_detay('alperenbaba11');
```

Hesap bilgisi, ilerleme, sahip olduğu her skin ve kostüm, ve bütün
geçmişi tek listede gelir.

> Bunlar GÖRÜNÜM (view), tablo değil — içlerinde veri tutulmaz, her
> açılışta hesaplanır. Silmek veya yeniden oluşturmak zararsızdır.

---

## ADIM 7 — Oyunda dene

1. Oyunu aç → ana menünün **sağ üstünde** `GİRİŞ YAP` çipi görünmeli
   (görünmüyorsa sunucu `/auth/status`'a cevap vermiyor demektir)
2. Tıkla → iki yol var:
   - üstte **GOOGLE İLE GİRİŞ** (tek tık, tarayıcı açılır)
   - altta **KULLANICI ADI + ŞİFRE** (Gmail gerekmez)
3. Google ile girdiysen oyun bir kez **KULLANICI ADI SEÇ** der. Bu ad
   dünya sıralamasında görünecek ad; **bir kez seçilir, bir daha
   değişmez**.
4. Supabase → Table Editor → `accounts` tablosunda satırın belirmiş olmalı
   (`username` ve `email` birlikte)
5. Bir koşu oyna, öl → skor `scores` tablosuna **`account_id` dolu** olarak
   düşmeli ve `name` sütununda hesabının adı yazmalı
6. `player_data` tablosunda elmasın/skinlerin görünmeli

### Bilmen gereken iki davranış
- **Girişsiz oynayan dünya sıralamasına giremez** — skoru yalnızca kendi
  bilgisayarındaki yerel tabloya yazılır. Oyunun geri kalanı tamamen açık.
- **Yeni hesap SIFIRDAN başlar.** Misafirken topladığın elmas/skin hesaba
  geçmez (geçseydi herkes misafirken oynayıp sonra kayıt olurdu). Misafir
  ilerlemen silinmez; çıkış yapınca aynen geri gelir.

---

## SIK ÇIKAN HATALAR

**"hesap sistemi kapalı"**
→ `SUPABASE_URL` veya `SUPABASE_KEY` girilmemiş. Adım 4.

**"Google girişi yapılandırılmamış"**
→ `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` girilmemiş. Adım 4.

**"Google doğrulaması başarısız"**
→ En sık sebep: OAuth istemcisini **Web application** olarak açmışsın.
Sil, **Desktop app** olarak yeniden oluştur (Adım 3.4).

**Giriş yaptım ama skor dünya sıralamasına düşmüyor**
→ Önce `/diag?key=PAROLAN` adresine bak. Orası temizse sonuç ekranındaki kırmızı satırı oku:
artık sebebi yazıyor ("önce kullanıcı adı seçmelisin", "giriş gerekli"...).
Sunucuyu güncellemediysen bu satır boş kalır — `server.py`'yi yenile.

**Elmasım / skinim veritabanında artmıyor**
→ Oyunda ESC → ANA MENÜ → sağ üstteki hesap çipi → HESAP ekranı. En altta
"ilerleme kaydedildi · 00:13:54" yazıyorsa her şey yolunda. Kırmızı bir
hata yazıyorsa sebebi orada; genelde `VERITABANI.sql` çalıştırılmamıştır.

**"column accounts.username does not exist"**
→ v3.20 SQL'i çalıştırmamışsın. ADIM 1'i tekrar çalıştır (var olanlara
dokunmaz).

**"null value in column email violates not-null constraint"**
→ `alter table accounts alter column email drop not null;` satırını
atlamışsın. Kullanıcı adıyla kayıt olanların e-postası yok.

**"relation player_data does not exist"**
→ ADIM 1'deki 3. bloğu çalıştır.

**"relation accounts does not exist"**
→ Adım 1'deki SQL çalışmamış. SQL Editor'da tekrar çalıştır.

**"new row violates row-level security policy"**
→ Render'da **anon** anahtarı kullanıyorsun. **service_role** ile değiştir.

**Tarayıcı açıldı ama oyun beklemeye devam ediyor**
→ Güvenlik duvarı `127.0.0.1` dinlemesini engelliyor olabilir.
Oyun 3 dakika sonra kendiliğinden "Süre doldu" der, kilitlenmez.
E-posta/şifre ile giriş bu durumda da çalışır.

---

## NE NEREDE DURUYOR

| Veri | Nerede | Nasıl korunuyor |
|---|---|---|
| Şifre | `accounts.password_hash` | scrypt + rastgele tuz; düz şifre hiçbir yerde yok |
| Oturum jetonu | `sessions.token_hash` | yalnızca SHA-256 özeti; 60 gün ömürlü |
| Cihaz bağı | `sessions.device_hash` | kayıt dosyası çalınsa başka bilgisayarda çalışmaz |
| Google secret | Render Environment | oyunun içinde YOK, .exe açılsa bile çıkmaz |
| Oyuncunun jetonu | kayıt dosyası | düz metin değil, makineye bağlı sarılı |

---

## HENÜZ OLMAYAN: ŞİFRE SIFIRLAMA

"Şifremi unuttum" akışı yok. Eklemek istersen e-posta gönderen bir servis
gerekir (Resend ya da SendGrid, ikisinin de ücretsiz katmanı var).
İstersen onu da yazarım — sunucuya 2 uç + oyuna 1 ekran ekleniyor.
