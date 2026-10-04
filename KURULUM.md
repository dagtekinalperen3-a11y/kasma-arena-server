# HESAP SİSTEMİ — ADIM ADIM KURULUM

Senin Supabase projen: **dagtekinalperen3-a11y's Project**
Şu an içinde tek tablo var: `scores`. Buna 2 tablo daha ekleyeceğiz.

Toplam süre: ~15 dakika. Hiçbir adımda oyunun kodunu değiştirmene gerek yok.

---

## ADIM 1 — Supabase tablolarını aç (3 dakika)

1. Supabase panelinde sol menüden **SQL Editor**'a gir
   (şu an **Table Editor**'dasın, hemen altındaki ikon)
2. **+ New query** de
3. Aşağıdakinin TAMAMINI yapıştır ve **RUN** (sağ altta yeşil düğme)

```sql
-- ============ 1) HESAPLAR ============
create table if not exists accounts (
  id            bigserial primary key,
  email         text unique not null,
  name          text,
  provider      text default 'password',
  password_hash text,
  google_sub    text,
  gems          bigint default 0,
  created_at    double precision
);
create index if not exists accounts_email_idx on accounts (lower(email));

-- ============ 2) OTURUMLAR ============
create table if not exists sessions (
  token_hash  text primary key,
  account_id  bigint references accounts(id) on delete cascade,
  device_hash text,
  created_at  double precision,
  expires_at  double precision
);
create index if not exists sessions_acc_idx on sessions (account_id);

-- ============ 3) MEVCUT scores TABLOSUNA HESAP BAĞI ============
alter table scores add column if not exists account_id bigint;

-- ============ 4) GÜVENLİK: bu iki tablo DIŞARIDAN okunamasın ============
alter table accounts enable row level security;
alter table sessions enable row level security;
-- (hiç policy eklemiyoruz = anon anahtarla kimse okuyamaz.
--  Sunucu service_role anahtarını kullandığı için RLS onu bağlamaz.)
```

4. "Success. No rows returned" yazmalı.
5. Sol menüden **Table Editor**'a dön → artık `accounts`, `scores`, `sessions`
   olmak üzere **3 tablo** görmelisin.

> **ÖNEMLİ:** `accounts` ve `sessions` tablolarına ASLA policy ekleme.
> Şifre özetleri ve oturum jetonları orada duruyor; dışarıdan okunabilir
> olmamalılar. Sunucu zaten service_role anahtarıyla bağlanıyor.

---

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

4. **Save Changes** → Render servisi kendiliğinden yeniden başlatır (~2 dk)

> `SUPABASE_KEY` zaten varsa ve **anon** anahtarıysa, onu **service_role**
> ile DEĞİŞTİR. Anon anahtarla hesap tabloları yazılamaz.

> `KASMA_SUBMIT_SECRET` oyundaki `SUBMIT_SECRET` ile **birebir aynı**
> olmalı. Değiştirmek istersen ikisini birden değiştir, yoksa skor
> gönderimi "imza doğrulanamadı" der.

---

## ADIM 5 — server.py'yi güncelle

Render GitHub'a bağlıysa: `server.py`'nin yeni hâlini repoya push et,
Render kendiliğinden yeniden kurar.

Elle yüklüyorsan: Render'daki `server.py`'yi sana attığım dosyayla
değiştir ve **Manual Deploy → Deploy latest commit** de.

---

## ADIM 6 — Çalışıyor mu? (1 dakika)

Tarayıcıda şu adresi aç:

```
https://kasma-arena-server.onrender.com/auth/status
```

Görmen gereken:

```json
{"accounts": true, "google": true, "client_id": "....apps.googleusercontent.com"}
```

| Ne görüyorsun | Anlamı | Çözüm |
|---|---|---|
| `accounts: true, google: true` | **Her şey hazır** | — |
| `accounts: true, google: false` | Supabase tamam, Google eksik | Adım 3–4'ü kontrol et |
| `accounts: false` | Supabase bağlanamadı | `SUPABASE_URL` / `SUPABASE_KEY` yanlış |
| 404 / sayfa yok | Eski `server.py` yayında | Adım 5 |

---

## ADIM 7 — Oyunda dene

1. Oyunu aç → ana menünün **sağ üstünde** `GİRİŞ YAP` çipi görünmeli
   (görünmüyorsa sunucu `/auth/status`'a cevap vermiyor demektir)
2. Tıkla → **GOOGLE İLE GİRİŞ** → tarayıcı açılır → hesabını seç
3. Tarayıcı "Giriş tamam, oyuna dönebilirsin" der, oyun da adını gösterir
4. Supabase → Table Editor → `accounts` tablosunda satırın belirmiş olmalı
5. Bir koşu oyna, öl → skor `scores` tablosuna **`account_id` dolu** olarak
   düşmeli ve `name` sütununda hesabının adı yazmalı

E-posta/şifre ile kayıt da aynı ekrandan: **Hesabın yok mu? KAYIT OL**.

---

## SIK ÇIKAN HATALAR

**"hesap sistemi kapalı"**
→ `SUPABASE_URL` veya `SUPABASE_KEY` girilmemiş. Adım 4.

**"Google girişi yapılandırılmamış"**
→ `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` girilmemiş. Adım 4.

**"Google doğrulaması başarısız"**
→ En sık sebep: OAuth istemcisini **Web application** olarak açmışsın.
Sil, **Desktop app** olarak yeniden oluştur (Adım 3.4).

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
