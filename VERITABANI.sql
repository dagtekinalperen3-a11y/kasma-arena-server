-- =====================================================================
--  KASMA ARENA — VERİTABANI  (v3.21)
-- ---------------------------------------------------------------------
--  NASIL ÇALIŞTIRILIR
--    Supabase > SQL Editor > + New query > bu dosyanın TAMAMINI yapıştır
--    > RUN. Sonunda "Success. No rows returned" yazmalı.
--
--  GÜVENLE TEKRAR ÇALIŞTIRILABİLİR: her şey "if not exists" ya da
--  "create or replace". Var olan verilerine DOKUNMAZ. Daha önce başka bir
--  SQL çalıştırdıysan da bunu çalıştır — eksikleri tamamlar.
-- =====================================================================


-- =====================================================================
-- 1) HESAPLAR
-- =====================================================================
create table if not exists accounts (
  id            bigserial primary key,
  email         text,
  username      text,
  name          text,
  provider      text default 'password',
  password_hash text,
  google_sub    text,
  gems          bigint default 0,
  created_at    double precision
);

-- Eski kurulumdan geliyorsan eksikleri ekle:
alter table accounts add column if not exists username   text;
alter table accounts add column if not exists email      text;
alter table accounts add column if not exists google_sub text;
alter table accounts add column if not exists gems       bigint default 0;
-- Kullanıcı adıyla kayıt olanın e-postası yoktur: zorunluluğu kaldır.
alter table accounts alter column email drop not null;

create unique index if not exists accounts_username_uidx
  on accounts (lower(username));
create index if not exists accounts_email_idx
  on accounts (lower(email));


-- =====================================================================
-- 2) OTURUMLAR
--    Jetonun kendisi DEĞİL, yalnızca SHA-256 özeti saklanır.
--    device_hash: oturumu o bilgisayara bağlar (kayıt dosyası çalınsa
--    bile başka makinede kullanılamaz).
-- =====================================================================
create table if not exists sessions (
  token_hash  text primary key,
  account_id  bigint references accounts(id) on delete cascade,
  device_hash text,
  created_at  double precision,
  expires_at  double precision
);
alter table sessions add column if not exists device_hash text;
create index if not exists sessions_acc_idx on sessions (account_id);


-- =====================================================================
-- 3) OYUNCU İLERLEMESİ
--    Elmas, skinler, petler, kostümler, açılmış kitap/silahlar ve
--    istatistikler. HESABA aittir: yeni hesap sıfırdan başlar, oyuncu
--    başka bilgisayara girince ilerlemesi onunla gelir.
--
--    Sık bakılan alanlar ayrı SÜTUN (hızlı sıralanır), geri kalanı
--    "data" içinde JSON.
-- =====================================================================
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
-- Eski kurulumdan geliyorsan eksikleri ekle:
alter table player_data add column if not exists gems_earned bigint default 0;
alter table player_data add column if not exists gems_spent  bigint default 0;
alter table player_data add column if not exists best_score  bigint default 0;
alter table player_data add column if not exists best_wave   int    default 0;
alter table player_data add column if not exists total_kills bigint default 0;
alter table player_data add column if not exists runs        int    default 0;
alter table player_data add column if not exists skin_count  int    default 0;
alter table player_data add column if not exists pet_count   int    default 0;
alter table player_data add column if not exists data        jsonb  default '{}'::jsonb;
alter table player_data add column if not exists updated_at  double precision;


-- =====================================================================
-- 4) OLAY GÜNLÜĞÜ  —  "saniyesine kadar ne oldu?"
--    Her elmas artışı/harcaması, her yeni skin, her koşu buraya zamanıyla
--    yazılır. Bir oyuncunun geçmişini satır satır okuyabilirsin.
-- =====================================================================
create table if not exists player_events (
  id         bigserial primary key,
  account_id bigint references accounts(id) on delete cascade,
  at         double precision,     -- unix zamanı (görünümlerde okunur hâle gelir)
  kind       text,                 -- gem | skin | kostum | kosu
  delta      bigint,               -- değişim (elmasta +/-)
  total      bigint,               -- değişimden SONRAKİ toplam
  note       text
);
create index if not exists player_events_acc_idx on player_events (account_id, at desc);


-- =====================================================================
-- 5) SKORLAR  (dünya sıralaması)
-- =====================================================================
alter table scores add column if not exists account_id bigint;
-- v3.22: zorluk sıralamada görünüyor (imzanın içinde, uydurulamaz)
alter table scores add column if not exists diff text default 'normal';
create index if not exists scores_acc_idx   on scores (account_id);
create index if not exists scores_score_idx on scores (score desc);


-- =====================================================================
-- 6) GÜVENLİK
--    Bu tablolar dışarıdan OKUNAMAZ. Sunucu service_role anahtarıyla
--    bağlandığı için RLS onu bağlamaz; anon anahtarla kimse giremez.
--    ASLA bu tablolara policy ekleme.
-- =====================================================================
alter table accounts      enable row level security;
alter table sessions      enable row level security;
alter table player_data   enable row level security;
alter table player_events enable row level security;


-- =====================================================================
-- 7) BAKMAK İÇİN GÖRÜNÜMLER
--    Table Editor'ın sol listesinde görünür, tıklayıp okursun.
--    Görünüm veri tutmaz; her açılışta hesaplanır, silmesi zararsızdır.
-- =====================================================================

-- 7a) OYUNCU ÖZETİ — kim, kaç elması var, en iyi skoru ne
drop view if exists player_overview;
create view player_overview as
select
  a.id                                           as hesap_no,
  a.username                                     as kullanici_adi,
  coalesce(a.email, '-')                         as gmail,
  case when a.provider = 'google' then 'Google'
       else 'Kullanıcı adı' end                  as giris_yolu,
  coalesce(d.gems, 0)                            as elmas,
  coalesce(d.gems_earned, 0)                     as toplam_kazanilan_elmas,
  coalesce(d.gems_spent, 0)                      as toplam_harcanan_elmas,
  coalesce(d.best_score, 0)                      as en_iyi_skor,
  coalesce(d.best_wave, 0)                       as en_yuksek_dalga,
  coalesce(d.total_kills, 0)                     as toplam_oldurme,
  coalesce(d.runs, 0)                            as kosu_sayisi,
  coalesce(d.skin_count, 0)                      as skin_sayisi,
  coalesce(d.pet_count, 0)                       as pet_sayisi,
  d.data -> 'skins_owned'                        as skinler,
  d.data -> 'cosmetics_owned'                    as kostumler_ve_petler,
  d.data -> 'equipped_skin'                      as kusanilan_skin,
  d.data -> 'books_owned'                        as acilan_kitaplar,
  d.data -> 'weapons_owned'                      as acilan_silahlar,
  to_timestamp(a.created_at)                     as kayit_tarihi,
  to_timestamp(d.updated_at)                     as son_guncelleme
from accounts a
left join player_data d on d.account_id = a.id
order by coalesce(d.best_score, 0) desc;

-- 7b) ELMAS / SKİN GEÇMİŞİ — saniyesine kadar
drop view if exists oyuncu_gecmisi;
create view oyuncu_gecmisi as
select
  to_timestamp(e.at)                             as zaman,
  a.username                                     as kullanici_adi,
  case e.kind when 'gem'    then 'ELMAS'
              when 'skin'   then 'SKİN'
              when 'kostum' then 'KOSTÜM/PET'
              when 'kosu'   then 'KOŞU'
              else e.kind end                    as ne_oldu,
  e.delta                                        as degisim,
  e.total                                        as sonraki_toplam,
  e.note                                         as aciklama
from player_events e
join accounts a on a.id = e.account_id
order by e.at desc;

-- 7c) DÜNYA SIRALAMASI — skorlar hesaplarıyla birlikte
drop view if exists dunya_siralamasi;
create view dunya_siralamasi as
select
  row_number() over (order by s.score desc)      as sira,
  coalesce(a.username, s.name)                   as kullanici_adi,
  coalesce(a.email, '-')                         as gmail,
  s.score                                        as skor,
  s.wave                                         as dalga,
  s.kills                                        as oldurme,
  case coalesce(s.diff, 'normal')
       when 'nightmare' then 'KABUS'
       when 'hard'      then 'ZOR'
       else                  'NORMAL' end         as zorluk,
  round(s.run_time::numeric, 1)                  as sure_sn,
  case when s.account_id is null then 'HAYIR' else 'EVET' end as hesapli,
  to_timestamp(s.created_at)                     as zaman
from scores s
left join accounts a on a.id = s.account_id
order by s.score desc;

-- 7d) TEK OYUNCUNUN HER ŞEYİ — kullanıcı adını yazıp çalıştır
--     select * from oyuncu_detay('alperenbaba11');
drop function if exists oyuncu_detay(text);
create function oyuncu_detay(p_kullanici text)
returns table (
  bolum text, anahtar text, deger text
) language sql stable as $$
  select 'HESAP', 'kullanıcı adı', a.username from accounts a
    where lower(a.username) = lower(p_kullanici)
  union all
  select 'HESAP', 'gmail', coalesce(a.email, '-') from accounts a
    where lower(a.username) = lower(p_kullanici)
  union all
  select 'HESAP', 'kayıt tarihi', to_char(to_timestamp(a.created_at),
         'DD.MM.YYYY HH24:MI:SS') from accounts a
    where lower(a.username) = lower(p_kullanici)
  union all
  select 'İLERLEME', 'elmas', coalesce(d.gems, 0)::text
    from accounts a left join player_data d on d.account_id = a.id
    where lower(a.username) = lower(p_kullanici)
  union all
  select 'İLERLEME', 'en iyi skor', coalesce(d.best_score, 0)::text
    from accounts a left join player_data d on d.account_id = a.id
    where lower(a.username) = lower(p_kullanici)
  union all
  select 'İLERLEME', 'koşu sayısı', coalesce(d.runs, 0)::text
    from accounts a left join player_data d on d.account_id = a.id
    where lower(a.username) = lower(p_kullanici)
  union all
  select 'SKİNLER', 'sahip olunan', jsonb_array_elements_text(
           coalesce(d.data -> 'skins_owned', '[]'::jsonb))
    from accounts a left join player_data d on d.account_id = a.id
    where lower(a.username) = lower(p_kullanici)
  union all
  select 'KOSTÜM/PET', 'sahip olunan', jsonb_array_elements_text(
           coalesce(d.data -> 'cosmetics_owned', '[]'::jsonb))
    from accounts a left join player_data d on d.account_id = a.id
    where lower(a.username) = lower(p_kullanici)
  union all
  select 'GEÇMİŞ',
         to_char(to_timestamp(e.at), 'DD.MM HH24:MI:SS'),
         e.kind || ' ' || e.delta::text || ' (toplam ' || e.total::text || ') ' ||
         coalesce(e.note, '')
    from player_events e join accounts a on a.id = e.account_id
    where lower(a.username) = lower(p_kullanici)
    order by 1, 2
$$;
