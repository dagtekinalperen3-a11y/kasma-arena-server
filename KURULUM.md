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

> **v3.20 ile güncellendi.** Daha önce ADIM 1'i çalıştırdıysan aşağıdakini
> yine çalıştır: `create ... if not exists` ve `add column if not exists`
> kullanıldığı için var olanlara dokunmaz, yalnızca eksikleri ekler.

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

-- v3.20: kullanıcı adı (sıralamada görünen ad, BİR KEZ seçilir)
alter table accounts add column if not exists username text;
-- Kullanıcı adıyla kayıt olanda e-posta yok: zorunluluğu kaldır.
alter table accounts alter column email drop not null;
create unique index if not exists accounts_username_uidx
  on accounts (lower(username));

-- ============ 3) OYUNCU İLERLEMESİ (v3.20) ============
-- Elmas, skinler, petler ve istatistikler HESABA ait. Yeni hesap sıfırdan
-- başlar; oyuncu başka bir bilgisayara girince ilerlemesi onunla gelir.
create table if not exists player_data (
  account_id  bigint primary key references accounts(id) on delete cascade,
  gems        bigint default 0,
  gems_earned bigint default 0,
  gems_spent  bigint default 0,
  best_score  bigint default 0,
  best_wave   int    default 0,
  total_kills bigint default 0,
  runs        int    default 0,
  skin_count  int    default 0,
  pet_count   int    default 0,
  data        jsonb  default '{}'::jsonb,
  updated_at  double precision
);
alter table player_data enable row level security;

-- ============ 4) MEVCUT scores TABLOSUNA HESAP BAĞI ============
alter table scores add column if not exists account_id bigint;

-- ============ 5) OYUNCULARA TEK BAKIŞTA BAKMAK İÇİN ============
-- Table Editor'da "player_overview"ı aç: her oyuncunun kullanıcı adı,
-- gmail'i, elması, en iyi skoru, kaç skini ve kaç peti olduğu tek
-- tabloda görünür.
create or replace view player_overview as
select
  a.id,
  a.username                            as kullanici_adi,
  a.email                               as gmail,
  a.provider                            as giris_yolu,
  coalesce(d.gems, 0)                   as elmas,
  coalesce(d.best_score, 0)             as en_iyi_skor,
  coalesce(d.best_wave, 0)              as en_yuksek_dalga,
  coalesce(d.total_kills, 0)            as toplam_oldurme,
  coalesce(d.runs, 0)                   as kosu_sayisi,
  coalesce(d.skin_count, 0)             as skin_sayisi,
  coalesce(d.pet_count, 0)              as pet_sayisi,
  d.data -> 'skins_owned'               as skinler,
  d.data -> 'cosmetics_owned'           as kostumler,
  to_timestamp(a.created_at)            as kayit_tarihi,
  to_timestamp(d.updated_at)            as son_oyun
from accounts a
left join player_data d on d.account_id = a.id
order by coalesce(d.best_score, 0) desc;

-- ============ 4) GÜVENLİK: bu iki tablo DIŞARIDAN okunamasın ============
alter table accounts enable row level security;
alter table sessions enable row level security;
-- (hiç policy eklemiyoruz = anon anahtarla kimse okuyamaz.
--  Sunucu service_role anahtarını kullandığı için RLS onu bağlamaz.)
```

4. "Success. No rows returned" yazmalı.
5. Sol menüden **Table Editor**'a dön → artık `accounts`, `scores`, `sessions`
   olmak üzere **3 tablo** görmelisin.

> **ÖNEMLİ:** `accounts`, `sessions` ve `player_data` tablolarına ASLA
> policy ekleme.
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

## OYUNCULARA BAKMAK

Supabase > **Table Editor** > sol listeden **player_overview**:

| kullanici_adi | gmail | elmas | en_iyi_skor | skin_sayisi | pet_sayisi | son_oyun |
|---|---|---|---|---|---|---|
| KASMACI | leon@gmail.com | 1.240 | 128.400 | 7 | 2 | 4 Eki 14:02 |

`skinler` ve `kostumler` sütunlarına tıklayınca hangi skinlere sahip
olduğunu tek tek görürsün. Liste en iyi skora göre sıralı gelir.

> Bu bir GÖRÜNÜM (view), tablo değil — içinde veri tutulmaz, her
> açılışta `accounts` + `player_data`'dan hesaplanır. Silmesi veya
> yeniden oluşturması zararsızdır.

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
