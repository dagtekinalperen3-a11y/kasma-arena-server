-- EvolveArena: arkadaşlar, mesajlar (sohbet + 2 kişilik davet) ve
-- 2 kişilik dünya sıralaması.
-- Supabase > SQL Editor'de bir kez çalıştır. Tekrar çalıştırmak zararsız.
-- Sunucu service_role anahtarıyla bağlandığı için RLS açık kalsa da çalışır;
-- tarayıcıdan (anon anahtar) bu tablolara erişim olmaz.

create table if not exists friends (
  id bigserial primary key,
  a text not null,                       -- isteği gönderen hesap (accounts.id)
  b text not null,                       -- isteği alan hesap
  status text not null default 'pending',  -- pending | accepted
  created_at double precision not null default extract(epoch from now()),
  unique (a, b)
);
create index if not exists friends_a_idx on friends (a);
create index if not exists friends_b_idx on friends (b);

create table if not exists messages (
  id bigserial primary key,
  sender text not null,
  receiver text not null,
  kind text not null default 'text',     -- text | invite (gövde = oda kodu)
  body text not null default '',
  created_at double precision not null default extract(epoch from now()),
  read_at double precision
);
create index if not exists messages_recv_idx on messages (receiver, read_at);
create index if not exists messages_pair_idx on messages (sender, receiver, id);

create table if not exists coop_scores (
  id bigserial primary key,
  pair_key text not null,                -- iki hesabın sıralı kimlikleri
  account_a text not null,               -- odayı kuran
  account_b text not null,               -- katılan
  name_a text not null,
  name_b text not null,
  score bigint not null,
  kills integer not null default 0,
  wave integer not null default 1,
  run_time double precision not null default 0,
  diff text not null default 'normal',
  details jsonb,                         -- iki oyuncunun kartı (silah, kitap, evrim)
  created_at double precision not null default extract(epoch from now())
);
create index if not exists coop_scores_score_idx on coop_scores (score desc);
create index if not exists coop_scores_a_idx on coop_scores (account_a);
create index if not exists coop_scores_b_idx on coop_scores (account_b);

alter table friends enable row level security;
alter table messages enable row level security;
alter table coop_scores enable row level security;

-- eski mesajlar birikmesin: 60 günden eski okunmuş mesajları arada bir sil
-- delete from messages where read_at is not null and created_at < extract(epoch from now()) - 60*86400;
