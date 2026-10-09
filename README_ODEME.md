# ARENA BONK — Mağazada TL ile satın alma (v3.28)

Oyunun mağazası artık gerçek parayla (TL) çalışıyor: elmas paketleri, premium
skinler, hazır PET'ler ve **Kendi PET'ini yap (₺159)**. Oyun tarafı ve sunucu
tarafı hazır; senin yapacağın tek şey bir **ödeme sağlayıcısı** hesabı açıp
anahtarlarını Render'a girmek.

## 1. Banka bilgisi nereye girilir? (Koda DEĞİL)

Kart ödemesini doğrudan bir banka hesabına (IBAN) bağlamak mümkün değil; araya
bir **ödeme kuruluşu** girer. Sen o kuruluşa üye olursun, **IBAN'ını onların
paneline** yazarsın, oyuncunun ödediği para oradan senin hesabına aktarılır.
Oyun ve sunucu yalnızca kuruluşun verdiği **API anahtarlarını** bilir; kart
bilgisi ne oyuna ne sunucuya gelir.

İki seçenek hazır (birini seçmen yeterli):

| | **Shopier** | **iyzico** |
|---|---|---|
| Şirket gerekir mi? | Hayır, **bireysel** satıcı olabilir | Evet (şahıs şirketi yeterli, vergi levhası ister) |
| Deneme ortamı | Yok (küçük bir gerçek ödemeyle denenir) | Var (sandbox) |
| Sunucu ayarı | `PAYMENT_PROVIDER=shopier` | `PAYMENT_PROVIDER=iyzico` |

> Şirketin yoksa **Shopier** ile başla. İleride şirket açınca iyzico'ya geçmek
> yalnızca birkaç ortam değişkenini değiştirmek demek; oyunu güncellemen gerekmez.

## 2. Supabase'de sipariş tablosu

Supabase > SQL Editor'da bir kez çalıştır:

```sql
create table if not exists shop_orders (
  id           text primary key,
  account_id   text not null,
  product_id   text not null,
  kind         text not null,
  amount       integer not null,               -- kuruş (15900 = 159 TL)
  currency     text not null default 'TRY',
  status       text not null default 'pending', -- pending | paid | granted | failed | cancelled
  provider     text not null default '',
  provider_ref text not null default '',
  payload      jsonb not null default '{}'::jsonb,
  created_at   double precision not null,
  paid_at      double precision not null default 0,
  granted_at   double precision not null default 0,
  error        text not null default ''
);
create index if not exists shop_orders_account_idx on shop_orders (account_id);
alter table shop_orders enable row level security;   -- sunucu service_role anahtarıyla yazar
```

Kontrol: `https://<sunucu>/diag?key=<DIAG_TOKEN>` adresi `shop_orders` tablosunu
ve "Mağaza ... kapalı" satırını gösterir; her şey tamamsa o satır kaybolur.

## 3. Render > Environment

Her sağlayıcıda ortak:

| Değişken | Örnek | Not |
|---|---|---|
| `PAYMENT_PROVIDER` | `shopier` / `iyzico` / `mock` | Boşsa mağaza kapalı görünür |
| `PUBLIC_BASE_URL` | `https://kasma-arena-server.onrender.com` | Ödeme dönüş adresleri bundan kurulur, **https** olmalı |
| `SHOP_FALLBACK_EMAIL` | `destek@ornek.com` | E-postası olmayan (kullanıcı adıyla açılmış) hesaplar için fatura e-postası |

**Shopier**
- `SHOPIER_API_KEY`, `SHOPIER_API_SECRET` → Shopier panelinde API / modül entegrasyonu bölümü
- `SHOPIER_WEBSITE_INDEX` → genelde `1`
- Shopier panelindeki **Geri dönüş (callback) URL**: `https://<sunucu>/shop/callback/shopier`

**iyzico**
- `IYZICO_API_KEY`, `IYZICO_SECRET_KEY` → iyzico üye işyeri panelindeki API anahtarları
- Deneme için `IYZICO_BASE_URL=https://sandbox-api.iyzipay.com` (sandbox anahtarlarıyla);
  canlıya geçince bu değişkeni sil (varsayılan `https://api.iyzipay.com`).
- Dönüş adresi kodda otomatik: `https://<sunucu>/shop/callback/iyzico`

## 4. Önce DENEME, sonra canlı

1. `PAYMENT_PROVIDER=mock` ve `MOCK_PAY_USERS=senin_kullanici_adin` yap.
   Oyunda kendi hesabınla gir, mağazadan bir şey al: tarayıcıda **"DENEME
   ÖDEMESİ"** sayfası açılır, **ÖDE (DENEME)**'ye bas — ürün birkaç saniyede
   oyuna gelir. Para çekilmez; yalnızca listedeki hesaplar kullanabilir.
2. iyzico ise sandbox anahtarlarıyla, Shopier ise en ucuz ürünle (₺29 PET)
   gerçek bir ödeme yap ve ürünün geldiğini gör.
3. `PAYMENT_PROVIDER`'ı gerçek sağlayıcıya çevir, `MOCK_PAY_USERS`'ı sil.

## 5. Nasıl çalışıyor (güvenlik)

- Fiyat **sunucunun kataloğundan** gelir (`server.py SHOP_PRODUCTS`); oyunun
  gönderdiği fiyata bakılmaz. Fiyat değiştirmek için yalnızca orayı değiştir,
  oyun yeni fiyatı kendisi okur.
- Ürün yalnızca **sunucunun doğruladığı ödemeyle** verilir: iyzico'da sonuç
  iyzico'ya geri sorulur (tutar, sepet, para birimi, dolandırıcılık durumu),
  Shopier'de dönüşün HMAC imzası denetlenir.
- Her sipariş **bir kez** teslim edilir (koşullu durum geçişi). İki dönüş aynı
  anda gelse bile ürün iki kez yazılmaz.
- Oyuncu tarayıcıyı kapatsa ya da oyun kapalıyken ödese bile ürün hesabına
  yazılır; oyunu açınca gelir.
- Satın alma **hesaba** bağlıdır; misafir oyuncuya "GİRİŞ YAP" düğmesi çıkar.
- Bütün satın almalar `player_events` tablosuna `satin` olarak düşer;
  `shop_orders` tablosunda her siparişin durumu görünür.

## 6. Bilmen gerekenler

- **Fatura / vergi:** ödeme kuruluşu parayı tahsil eder ama dijital ürün
  satışının faturası ve vergisi satıcıya (sana) aittir. Satışa başlamadan bir
  mali müşavire danış.
- **Mesafeli satış:** mağaza sayfasında (veya web sitende) satış sözleşmesi,
  iade/cayma koşulları ve iletişim bilgin bulunmalı; ödeme kuruluşları başvuruda
  bunu ister.
- **Google Play / Steam:** oyunu Google Play'e koyarsan oradaki sürümde dijital
  ürünler için **Google Play Billing** zorunludur; Steam'de de Steam'in kendi
  ödeme sistemi kullanılır. Bu web ödemesi, oyunun **kendi sitenden indirilen
  .exe** sürümü içindir.

## 7. Test

```
pip install flask
python tests/test_shop.py
```

Sahte bir Supabase ile şunları dener: sipariş açma, deneme ödemesiyle teslim,
çift teslim olmaması, özel PET tasarımı süzgeci, başkasının siparişini görememe,
iyzico tutar/sepet denetimi ve imza biçimi, Shopier imzası.
