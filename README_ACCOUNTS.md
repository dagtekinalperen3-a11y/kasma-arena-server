# Hesap Sistemi — Kurulum

Oyun **girişsiz de çalışır**. Hesap yalnızca dünya sıralamasına girmek ve
elmasların hesapta durması için gerekir. Aşağıdakiler yapılmadan oyun
açılır, oynanır; sadece giriş ekranı "kapalı" der.

## 1) Supabase tabloları

Supabase > SQL Editor'da çalıştır:

```sql
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

create table if not exists sessions (
  token_hash  text primary key,
  account_id  bigint references accounts(id) on delete cascade,
  device_hash text,
  created_at  double precision,
  expires_at  double precision
);
create index if not exists sessions_acc_idx on sessions (account_id);

-- daha önce kurduysan (device_hash sonradan eklendi):
alter table sessions add column if not exists device_hash text;

-- skorları hesaba bağlamak için (varsa atla)
alter table scores add column if not exists account_id bigint;
```

**Önemli:** `accounts` ve `sessions` tablolarında Row Level Security'yi
AÇIK bırak ve **anon anahtara erişim verme**. Sunucu `SUPABASE_KEY` olarak
*service role* anahtarını kullanmalı; o anahtar yalnızca sunucuda durur.
Şifre özetleri ve oturum jetonları başka hiçbir yerden okunabilmemeli.

## 2) Google OAuth istemcisi

1. https://console.cloud.google.com → proje seç/oluştur
2. **APIs & Services → OAuth consent screen** → External → uygulama adını
   gir → `email`, `profile`, `openid` kapsamlarını ekle → yayınla
3. **APIs & Services → Credentials → Create credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Oluşunca **Client ID** ve **Client secret** verilir

> Masaüstü istemcisinde yönlendirme adresi girmene gerek yok: Google
> `http://127.0.0.1:<port>` (loopback) adreslerini bu istemci tipinde
> otomatik kabul eder. Oyun her girişte boş bir port seçer.

## 3) Sunucu ortam değişkenleri (Render → Environment)

```
SUPABASE_URL=...
SUPABASE_KEY=...            # service role anahtarı
GOOGLE_CLIENT_ID=....apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=...
KASMA_SUBMIT_SECRET=...     # oyundaki SUBMIT_SECRET ile AYNI olmalı
```

`GOOGLE_CLIENT_SECRET` **yalnızca sunucuda** durur. Oyun dosyasına asla
yazma: oyun .exe'ye çevrilse bile içindeki metinler okunabilir.

## 4) Oyun tarafı

`kasma_arena13.py` içinde `ONLINE_API_URL` zaten sunucunu gösteriyor.
Google giriş düğmesi, sunucu `/auth/status` ucunda `google: true` dönerse
kendiliğinden etkinleşir — oyunda ayrıca bir şey ayarlamana gerek yok.

## Güvenlik özeti

| Konu | Nasıl korunuyor |
|---|---|
| Şifre | scrypt + kullanıcıya özel tuz; düz metin hiçbir yerde yok |
| Şifre karşılaştırma | `hmac.compare_digest` (sabit zamanlı) |
| Google client secret | yalnızca sunucuda; oyun kodu görmez |
| Yetkilendirme kodu çalınması | PKCE (`code_verifier`) olmadan kod işe yaramaz |
| Oturum jetonu | veritabanında yalnızca SHA-256 özeti durur, süresi var |
| Kaba kuvvet | kaynak başına deneme sınırı (`_rate_ok`) |
| Hesap sızdırma | "e-posta yok" ile "şifre yanlış" aynı hatayı döndürür |
| Sıralamada isim | giriş yapan oyuncunun adını SUNUCU yazar, istemci değil |
| Jetonun çalınması | oturum CİHAZA bağlı (`device_hash`): kayıt dosyası başka bilgisayara kopyalanırsa jeton kabul edilmez |
| Kayıt dosyasında jeton | düz metin değil, makineye bağlı biçimde sarılı durur (`seal_token`) |

### Bilinmesi gerekenler
- Oyuncunun bilgisayarındaki oturum jetonu, **o bilgisayara erişebilen**
  biri tarafından yine de ele geçirilebilir. Bu bütün masaüstü oyunlarında
  böyledir. Buna karşı iki katman var: jeton kayıt dosyasında düz metin
  durmaz, ve oturum cihaz kimliğine bağlıdır — dosya başka bir makineye
  taşındığında sunucu jetonu reddeder. Jeton ayrıca süresi dolunca
  geçersizleşir ve "çıkış yap" ile anında iptal edilir.
- Cihaz kimliği, kullanıcı adı + makine adının **SHA-256 özetidir**;
  sunucuya gerçek adlar gitmez. Oyuncu bilgisayarını yeniler ya da kullanıcı
  adını değiştirirse yalnızca bir kez yeniden giriş yapması gerekir.
- Şifre sıfırlama (e-posta ile) **henüz yok**. Eklemek istersen e-posta
  gönderen bir servise (Resend, SendGrid, Supabase Auth) ihtiyacın olur.
