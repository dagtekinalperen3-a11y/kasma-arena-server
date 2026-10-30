import os
import sys
import json
import math
import functools
import time
import uuid
import hmac
import hashlib
import threading
import urllib.parse
import urllib.request
import datetime
import re as _re
from collections import defaultdict, deque
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from supabase import create_client, Client

app = Flask(__name__, static_folder=".")

# CORS: masaüstü oyunun buna ihtiyacı yok, ama telefon sürümü GitHub Pages'ta
# çalışan bir web sayfası. İzin sadece oyunun kendi sayfasına ve oyunun
# kullandığı uçlara veriliyor (/diag, eski steam uçları kapalı). Çerez yok,
# jeton gövdede gidiyor.
#   Render > Environment: PLAY_ORIGINS = https://KULLANICIADIN.github.io
#   (virgülle birden fazla yazılabilir; boşsa sadece *.github.io)
PLAY_ORIGINS = [o.strip().rstrip("/").lower()
                for o in (os.environ.get("PLAY_ORIGINS") or "").split(",") if o.strip()]
CORS_PATHS = ("/auth/", "/player/", "/shop/", "/reward", "/rewards", "/ad/", "/gift",
              "/scores", "/submit", "/contact", "/snow", "/event")
CORS_BLOCKED = ("/diag", "/get_player", "/update_player", "/admin")
# Web sitesi (volvearena.shop): yalnızca /site/ uçlarına ve yalnızca bu
# kökenlerden. Render > Environment: SITE_ORIGINS = https://alanadin.com
# (virgülle birden fazla). Boşsa aşağıdaki varsayılanlar.
SITE_ORIGINS = [o.strip().rstrip("/").lower()
                for o in (os.environ.get("SITE_ORIGINS")
                          or "https://volvearena.shop,https://www.volvearena.shop").split(",") if o.strip()]


def _origin_ok(origin):
    o = (origin or "").strip().rstrip("/").lower()
    if PLAY_ORIGINS:
        return o in PLAY_ORIGINS          # yalnızca elle yazılmış kökenler
    if not o.startswith("https://") or len(o) > 200:
        return False
    host = o[len("https://"):]
    return (host.endswith(".github.io") and "/" not in host and ":" not in host
            and host.count(".") == 2)


def _cors_path_ok(path):
    p = path or ""
    if any(p.startswith(b) for b in CORS_BLOCKED):
        return False
    return any(p.startswith(a) for a in CORS_PATHS)


def _site_origin_ok(origin):
    return (origin or "").strip().rstrip("/").lower() in SITE_ORIGINS


@app.after_request
def _cors(resp):
    origin = request.headers.get("Origin")
    site = (request.path or "").startswith("/site/")
    if origin and site and _site_origin_ok(origin):
        resp.headers["Access-Control-Allow-Origin"] = origin.strip().rstrip("/")
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Max-Age"] = "600"
    elif origin and not site and _origin_ok(origin) and _cors_path_ok(request.path):
        resp.headers["Access-Control-Allow-Origin"] = origin.strip().rstrip("/")
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Max-Age"] = "600"
    if origin:
        resp.headers["Vary"] = "Origin"
    # güvenlik başlıkları (her yanıtta)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if site or (request.path or "").startswith(("/auth/", "/player/", "/rewards", "/admin")):
        # hesap verisi önbelleğe, vekillere düşmesin
        resp.headers["Cache-Control"] = "no-store"
    return resp

# Oyunun en büyük isteği (/player/save, bütün ilerleme) birkaç on kilobayt; 256
# KB bol bol yeter.
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024

# Hız sınırı gerçek IP'ye bakmalı. X-Forwarded-For'un ilk değerini istemci
# yazabiliyor; ProxyFix(x_for=1) Render'ın eklediği son değeri alıyor.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


def _client_ip():
    """Hız sınırı anahtarı: vekilin doğruladığı gerçek istemci adresi."""
    return request.remote_addr or "?"


# Dünya sıralamasının tutulduğu Supabase tablosu.
WORLD_TABLE = "scores"          # veritabanında: skorlar


def _oops(e, msg="sunucu hatası", code=500):
    """Hatayı sunucu günlüğüne yazar, oyuncuya sabit bir metin + iz kimliği döner."""
    ref = uuid.uuid4().hex[:8]
    try:
        app.logger.exception("[%s] %s", ref, msg)
    except Exception:
        pass
    return jsonify({"success": False, "error": msg, "ref": ref}), code


@app.errorhandler(Exception)
def _any_error(e):
    """Yakalanmamış her istisna da aynı süzgeçten geçer."""
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        # 404/405/413 gibi normal HTTP yanıtları olduğu gibi kalsın.
        return e
    return _oops(e)

# Supabase bağlantı bilgileri (Render Environment değişkenlerinden alınır)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---- veritabanı katmanı ----
# Kod İngilizce alan adlarıyla çalışır; veritabanında tablolar ve sütunlar
# Türkçe ve okunaklı (VERITABANI.sql). db("accounts") gibi çağrılar adları
# çevirir. Zamanlar kodda epoch saniye (float), veritabanında gerçek tarih
# (timestamptz): yazarken ve okurken o da çevrilir.
#   kod adı: (tablo, {kod sütunu: veritabanı sütunu}, {zaman sütunları})
DB_TABLES = {
    "accounts": ("oyuncular", {
        "username": "kullanici_adi", "email": "eposta", "provider": "giris_yontemi",
        "password_hash": "sifre_ozeti", "google_sub": "google_kimligi", "name": "google_adi",
        "created_at": "kayit_tarihi", "last_login": "son_giris", "last_seen": "son_gorulme",
        "last_logout": "son_cikis", "play_seconds": "toplam_oynama_sn",
        "play_sessions": "oturum_sayisi", "version": "surum"},
        {"created_at", "last_login", "last_seen", "last_logout"}),
    "sessions": ("oturumlar", {
        "token_hash": "token_ozeti", "account_id": "oyuncu_id", "device_hash": "cihaz_ozeti",
        "created_at": "olusturma", "expires_at": "bitis"},
        {"created_at", "expires_at"}),
    "player_data": ("ilerleme", {
        "account_id": "oyuncu_id", "gems": "elmas", "gems_earned": "kazanilan_elmas",
        "gems_spent": "harcanan_elmas", "best_score": "en_iyi_skor", "best_wave": "en_iyi_dalga",
        "total_kills": "toplam_oldurme", "runs": "kosu_sayisi", "skin_count": "skin_sayisi",
        "pet_count": "pet_sayisi", "data": "veri", "updated_at": "guncelleme"},
        {"updated_at"}),
    "player_events": ("olay_gunlugu", {
        "account_id": "oyuncu_id", "at": "zaman", "kind": "tur", "delta": "degisim",
        "total": "toplam", "note": "aciklama"},
        {"at"}),
    "scores": ("skorlar", {
        "account_id": "oyuncu_id", "name": "kullanici_adi", "score": "skor", "kills": "oldurme",
        "wave": "dalga", "run_time": "sure_sn", "diff": "zorluk", "map": "harita",
        "ranked": "dunya_siralamasi", "details": "kosu_karti", "created_at": "tarih",
        "sig": "imza"},
        {"created_at"}),
    "play_sessions": ("oyun_oturumlari", {
        "account_id": "oyuncu_id", "started_at": "giris", "ended_at": "cikis",
        "seconds": "sure_sn", "open": "acik", "version": "surum"},
        {"started_at", "ended_at"}),
    "friends": ("arkadaslar", {
        "a": "isteyen_id", "b": "istenen_id", "status": "durum", "created_at": "tarih"},
        {"created_at"}),
    "messages": ("mesajlar", {
        "sender": "gonderen_id", "receiver": "alici_id", "kind": "tur", "body": "metin",
        "created_at": "tarih", "read_at": "okunma"},
        {"created_at", "read_at"}),
    "coop_scores": ("ikili_skorlar", {
        "pair_key": "ikili_anahtari", "account_a": "oyuncu_a_id", "account_b": "oyuncu_b_id",
        "name_a": "oyuncu_a", "name_b": "oyuncu_b", "score": "skor", "kills": "oldurme",
        "wave": "dalga", "run_time": "sure_sn", "diff": "zorluk", "details": "kosu_karti",
        "created_at": "tarih"},
        {"created_at"}),
    "feedback": ("geri_bildirim", {
        "created_at": "tarih", "kind": "tur", "message": "mesaj", "email": "eposta",
        "account_id": "oyuncu_id", "username": "kullanici_adi", "ip_hash": "ip_ozeti",
        "version": "surum", "status": "durum"},
        {"created_at"}),
    "shop_orders": ("siparisler", {
        "account_id": "oyuncu_id", "product_id": "urun_id", "kind": "tur",
        "amount": "tutar_kurus", "currency": "para_birimi", "status": "durum",
        "provider": "saglayici", "provider_ref": "saglayici_ref", "payload": "ek_veri",
        "created_at": "olusturma", "paid_at": "odeme", "granted_at": "teslim", "error": "hata"},
        {"created_at", "paid_at", "granted_at"}),
}
_DB_REV = {k: {v: c for c, v in cols.items()} for k, (_t, cols, _z) in DB_TABLES.items()}


def _to_ts(v):
    """epoch saniye -> ISO tarih (0 / boş -> NULL)."""
    if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
        return v
    if not math.isfinite(v) or v <= 0:
        return None
    return datetime.datetime.fromtimestamp(float(v), datetime.timezone.utc).isoformat()


def _from_ts(v):
    """ISO tarih -> epoch saniye (boş -> 0)."""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).strip().replace(" ", "T")
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    # Python 3.10 ve öncesi yalnızca 3 ya da 6 haneli kesir okur
    m = _re.match(r"^(.*T\d\d:\d\d:\d\d)(?:\.(\d+))?(.*)$", t)
    if m:
        frac = (m.group(2) or "")[:6].ljust(6, "0")
        tz = m.group(3) or "+00:00"
        if _re.match(r"^[+-]\d\d$", tz):
            tz += ":00"
        t = m.group(1) + "." + frac + tz
    try:
        return datetime.datetime.fromisoformat(t).timestamp()
    except ValueError:
        return 0.0


class _DbResult:
    __slots__ = ("data", "count")

    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _DbQuery:
    """Supabase sorgusunu saran ince katman: sütun adlarını ve zamanları çevirir."""
    __slots__ = ("_q", "_key")

    def __init__(self, q, key):
        self._q = q
        self._key = key

    def _col(self, c):
        spec = DB_TABLES.get(self._key)
        return spec[1].get(c, c) if spec else c

    def _val(self, c, v):
        spec = DB_TABLES.get(self._key)
        return _to_ts(v) if spec and c in spec[2] else v

    def _row_in(self, d):
        return {self._col(k): self._val(k, v) for k, v in d.items()}

    def _row_out(self, d):
        if not isinstance(d, dict):
            return d
        rev = _DB_REV.get(self._key)
        if not rev:
            return d
        zc = DB_TABLES[self._key][2]
        out = {}
        for k, v in d.items():
            c = rev.get(k, k)
            out[c] = _from_ts(v) if c in zc else v
        return out

    def _wrap(self, q):
        return _DbQuery(q, self._key)

    # ---- okuma / yazma ----
    def select(self, cols="*", **kw):
        if str(cols).strip() != "*":
            cols = ",".join(self._col(c.strip()) for c in str(cols).split(",") if c.strip())
        return self._wrap(self._q.select(cols, **kw))

    def insert(self, rows, **kw):
        rows = [self._row_in(r) for r in rows] if isinstance(rows, list) else self._row_in(rows)
        return self._wrap(self._q.insert(rows, **kw))

    def update(self, d, **kw):
        return self._wrap(self._q.update(self._row_in(d), **kw))

    def delete(self, **kw):
        return self._wrap(self._q.delete(**kw))

    # ---- süzgeçler ----
    def _f(self, name, col, val):
        return self._wrap(getattr(self._q, name)(self._col(col), self._val(col, val)))

    def eq(self, c, v):
        return self._f("eq", c, v)

    def neq(self, c, v):
        return self._f("neq", c, v)

    def gt(self, c, v):
        return self._f("gt", c, v)

    def gte(self, c, v):
        return self._f("gte", c, v)

    def lt(self, c, v):
        return self._f("lt", c, v)

    def lte(self, c, v):
        return self._f("lte", c, v)

    def ilike(self, c, v):
        return self._wrap(self._q.ilike(self._col(c), v))

    def is_(self, c, v):
        return self._wrap(self._q.is_(self._col(c), v))

    def in_(self, c, vals):
        return self._wrap(self._q.in_(self._col(c), [self._val(c, v) for v in vals]))

    def order(self, c, **kw):
        return self._wrap(self._q.order(self._col(c), **kw))

    def limit(self, n, **kw):
        return self._wrap(self._q.limit(n, **kw))

    def execute(self):
        res = self._q.execute()
        data = getattr(res, "data", None)
        if isinstance(data, list):
            data = [self._row_out(r) for r in data]
        elif isinstance(data, dict):
            data = self._row_out(data)
        return _DbResult(data, getattr(res, "count", None))


def db(key):
    """db("accounts") -> oyuncular tablosu (adlar çevrilir)."""
    spec = DB_TABLES.get(key)
    return _DbQuery(supabase.table(spec[0] if spec else key), key)


def _body():
    """İstek gövdesi - her zaman sözlük."""
    d = request.get_json(silent=True)
    return d if isinstance(d, dict) else {}


def _int(v, default=0):
    """Güvenli tamsayı: "abc", None, 1e400, NaN -> default (500 yerine)."""
    try:
        f = float(v)
        return int(f) if math.isfinite(f) else default
    except (TypeError, ValueError, OverflowError):
        return default


def _num(v, default=0.0):
    try:
        f = float(v)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError, OverflowError):
        return default


# Yalnız web sayfası türleri, gizli (.) dosyalar hariç.
STATIC_EXT = (".html", ".htm", ".css", ".js", ".png", ".jpg", ".jpeg", ".gif",
              ".svg", ".ico", ".webp", ".txt", ".woff", ".woff2")


@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def static_files(path):
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    if (not path.lower().endswith(STATIC_EXT) or name.startswith(".")
            or any(part.startswith(".") for part in path.split("/"))):
        return jsonify({"error": "bulunamadı"}), 404
    return send_from_directory(".", path)

# ---- hesaplar: kullanıcı adı/şifre + Google ile giriş ----
# - şifreler scrypt + hesaba özel tuzla saklanıyor, karşılaştırma sabit zamanlı
# - Google client secret sadece sunucuda; oyun yalnız yetki kodunu yolluyor
#   (RFC 8252 loopback + PKCE)
# - oturum jetonunun veritabanında sadece SHA-256 özeti duruyor, süresi var
# - giriş denemeleri IP ve hesap başına sınırlı; "kullanıcı yok" ile "şifre
#   yanlış" aynı cevabı veriyor
# Gerekenler: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET (yoksa Google girişi
# kapalı, gerisi çalışır). Tablolar için README_ACCOUNTS.md.

import base64
import re as _re
import secrets

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

SESSION_TTL = 60 * 60 * 24 * 60          # oturum ömrü: 60 gün
PW_MIN_LEN = 8
NAME_MAX = 14
# scrypt parametreleri. N bellek maliyeti; 2**15 masaüstü/sunucu için makul
# (yaklaşık 32 MB) ve kaba kuvveti ciddi biçimde pahalılaştırır.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 15, 8, 1
EMAIL_RE = _re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,24}$")

# kullanıcı adı: sıralamada görünen ad. Bir kez seçilir, bir daha değişmez.
USERNAME_RE = _re.compile(r"^[A-Za-z0-9ÇĞİÖŞÜçğıöşü_]{3,14}$")

# Oyuncunun adını çalmaya çalışan "admin / moderator" gibi adlar kapalı.
USERNAME_BLOCK = {"admin", "administrator", "moderator", "mod", "sistem", "system",
                  "kasma", "kasmaarena", "evolve", "evolvearena", "arenabonk", "root", "null", "undefined", "anonim",
                  "isimsiz", "server", "sunucu", "support", "destek"}


def _accounts_enabled():
    return bool(supabase)


def _google_enabled():
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and supabase)


def _hash_password(password, salt=None):
    """Şifreyi scrypt ile karar."""
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt,
                        n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32,
                        maxmem=64 * 1024 * 1024)
    return "scrypt$%d$%d$%d$%s$%s" % (
        SCRYPT_N, SCRYPT_R, SCRYPT_P,
        base64.b64encode(salt).decode(), base64.b64encode(dk).decode())


def _verify_password(password, stored):
    """Şifre doğru mu?"""
    try:
        algo, n, r, pp, salt_b64, dk_b64 = str(stored).split("$")
        if algo != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        want = base64.b64decode(dk_b64)
        got = hashlib.scrypt(password.encode("utf-8"), salt=salt,
                             n=int(n), r=int(r), p=int(pp), dklen=len(want),
                             maxmem=64 * 1024 * 1024)
        return hmac.compare_digest(got, want)
    except Exception:
        return False


# kukla özet: giriş denemesinde hesap bulunamasa da aynı scrypt maliyetini
# harcamak için.
_DUMMY_HASH = _hash_password(secrets.token_hex(16))


def _token_hash(tok):
    return hashlib.sha256(tok.encode("utf-8")).hexdigest()


def _clean_device(d):
    """İstemciden gelen cihaz kimliği: yalnızca 64 karaktere kadar hex."""
    d = str(d or "")[:64].strip().lower()
    return d if all(c in "0123456789abcdef" for c in d) and len(d) >= 16 else ""


def _new_session(account_id, device=""):
    """Yeni oturum jetonu (veritabanına özeti yazılır). Hesabın eski oturumları kapanır."""
    _sess_cache_drop(account_id=account_id)
    try:
        db("sessions").delete().eq("account_id", account_id).execute()
    except Exception:
        pass        # silinemezse bile yeni oturum açılsın; en kötü ihtimalle eski kalır
    tok = secrets.token_urlsafe(32)
    db("sessions").insert({
        "token_hash": _token_hash(tok),
        "account_id": account_id,
        "device_hash": _clean_device(device),
        "created_at": time.time(),
        "expires_at": time.time() + SESSION_TTL,
    }).execute()
    return tok


def _acct(data, check_device=True):
    """İstek gövdesinden hesabı çözer (cihaz denetimi dahil)."""
    data = data or {}
    if not check_device:
        return _account_by_session(str(data.get("token", "")))
    return _account_by_session(str(data.get("token", "")),
                               data.get("device", ""),
                               data.get("device_legacy", ""))


# oturum önbelleği: arkadaş yoklaması, mesaj, ping gibi sık istekler her
# seferinde iki veritabanı okuması yapmasın (mesajlar bu yüzden geç gidiyordu).
# Çıkış, şifre değişimi ve ad seçimi önbelleği hemen temizler.
SESSION_CACHE_TTL = 30.0
_SESS_CACHE = {}
_sess_cache_lock = threading.Lock()


def _sess_cache_drop(token_hash=None, account_id=None):
    with _sess_cache_lock:
        if token_hash is not None:
            _SESS_CACHE.pop(token_hash, None)
        if account_id is not None:
            for k in [k for k, v in _SESS_CACHE.items()
                      if str(v[1].get("account_id")) == str(account_id)]:
                _SESS_CACHE.pop(k, None)


def _account_by_session(tok, device=None, device_legacy=None):
    """Jetondan hesabı bulur; süresi geçmişse ya da cihaz tutmuyorsa None."""
    if not tok or not supabase:
        return None
    th = _token_hash(tok)
    now = time.time()
    with _sess_cache_lock:
        hit = _SESS_CACHE.get(th)
    if hit and now - hit[0] < SESSION_CACHE_TTL:
        sess, acc_row = hit[1], hit[2]
    else:
        rows = db("sessions").select("*").eq("token_hash", th).execute()
        if not rows.data:
            _sess_cache_drop(th)
            return None
        sess = rows.data[0]
        acc_row = None
    if float(sess.get("expires_at", 0)) < time.time():
        _sess_cache_drop(sess.get("token_hash"))
        try:
            db("sessions").delete().eq(
                "token_hash", sess["token_hash"]).execute()
        except Exception:
            pass
        return None
    if device is not None:
        want = str(sess.get("device_hash") or "")
        # boş device_hash artık kabul edilmiyor.
        if not want:
            return None
        ok_dev = _clean_device(device) == want
        if not ok_dev and device_legacy:
            ok_dev = _clean_device(device_legacy) == want
        if not ok_dev:
            return None
    if acc_row is None:
        # select("*") bilerek: tek tek sayınca yeni sütun unutuluyor. Dışarı
        # giden alanları zaten _public_account süzüyor.
        acc = db("accounts").select("*").eq("id", sess["account_id"]).execute()
        if not acc.data:
            return None
        acc_row = acc.data[0]
        with _sess_cache_lock:
            if len(_SESS_CACHE) > 20000:
                _SESS_CACHE.clear()
            _SESS_CACHE[th] = (now, sess, acc_row)
    return dict(acc_row)


def _public_account(acc):
    """Oyuncuya döndürülebilir alanlar."""
    return {
        "id": acc.get("id"),
        "email": acc.get("email") or "",
        "username": acc.get("username") or "",
        # name = sıralamada görünen ad. Kullanıcı adı seçilmişse odur.
        "name": acc.get("username") or acc.get("name") or "",
        "provider": acc.get("provider", "password"),
        # Kullanıcı adı henüz seçilmemişse oyun bir kereye mahsus seçtirir.
        "needs_username": not bool(acc.get("username")),
        # şifre özeti değil, yalnızca "var mı?": Google ile gelen hesapta şifre
        # olmayabilir, oyun o zaman "mevcut şifre" kutusunu hiç göstermez ve
        # ekranda "ŞİFRE BELİRLE" yazar.
        "has_password": bool(acc.get("password_hash")),
    }


def _clean_username(u):
    """Kullanıcı adını denetler."""
    u = str(u or "").strip()
    if not USERNAME_RE.match(u):
        return False, "kullanıcı adı 3-14 karakter olmalı (harf, rakam, _)"
    if u.lower() in USERNAME_BLOCK:
        return False, "bu kullanıcı adı kullanılamaz"
    return True, u


def _accounts_by_username(u, cols="*"):
    """Kullanıcı adına (büyük/küçük harf duyarsız) uyan hesaplar."""
    low = str(u or "").strip().lower()
    if not low:
        return []
    pat = low.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    q = db("accounts").select(cols)
    try:
        rows = q.ilike("username", pat).execute().data or []
    except AttributeError:          # ilike'ı olmayan (eski / sahte) istemci
        rows = db("accounts").select(cols).execute().data or []
    return [r for r in rows if str(r.get("username") or "").lower() == low]


def _username_taken(u, except_id=None):
    return any(r.get("id") != except_id for r in _accounts_by_username(u, "id,username"))


def _b64url_json(part):
    pad = "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(part + pad).decode("utf-8"))


def _verify_google_id_token(id_token):
    """Google kimlik jetonunun alanlarını denetler. İmzaya bakılmıyor: jeton TLS üstünden doğrudan Google'dan geldi."""
    try:
        payload = _b64url_json(id_token.split(".")[1])
    except Exception:
        return None, "kimlik jetonu okunamadı"
    if payload.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        return None, "kimlik jetonu Google'dan değil"
    aud = payload.get("aud")
    if aud != GOOGLE_CLIENT_ID:
        return None, "kimlik jetonu bu oyun için değil"
    if float(payload.get("exp", 0)) < time.time():
        return None, "kimlik jetonunun süresi dolmuş"
    if not payload.get("email"):
        return None, "hesapta e-posta yok"
    if payload.get("email_verified") not in (True, "true"):
        return None, "Google hesabının e-postası doğrulanmamış"
    return payload, ""


def _find_or_create_account(email, name, provider, password_hash=None, google_sub=None):
    email = email.strip().lower()
    rows = db("accounts").select("*").eq("email", email).execute()
    if rows.data:
        acc = rows.data[0]
        # Kayıtta yazılan e-posta doğrulanmadığı için Google girişi sadece aynı
        # Google kimliğine, Google ile açılmış ya da şifresiz bir hesaba
        # bağlanır. Yoksa biri başkasının Gmail'iyle önceden hesap açıp
        # bekleyebilirdi.
        if google_sub:
            same = str(acc.get("google_sub") or "") == str(google_sub)
            if not same:
                if acc.get("google_sub") or acc.get("password_hash"):
                    raise _LinkRefused()
        patch = {}
        if google_sub and not acc.get("google_sub"):
            patch["google_sub"] = google_sub
        if name and not acc.get("name"):
            patch["name"] = name[:NAME_MAX]
        if patch:
            db("accounts").update(patch).eq("id", acc["id"]).execute()
            acc.update(patch)
        return acc, False
    new = {
        "email": email,
        # Google'dan gelen ad yalnızca bilgi. Sıralamada görünecek kullanıcı
        # adını oyuncu bir kez kendisi seçer ve bir daha değiştiremez.
        "name": (name or "")[:NAME_MAX],
        "provider": provider,
        "created_at": time.time(),
    }
    if password_hash:
        new["password_hash"] = password_hash
    if google_sub:
        new["google_sub"] = google_sub
    res = db("accounts").insert(new).execute()
    return res.data[0], True


@app.route("/diag", methods=["GET"])
def diag():
    """Kurulum kontrolü: hangi tablo/sütun eksik. DIAG_TOKEN gerekir (?key= ya da X-Diag-Key)."""
    want = os.environ.get("DIAG_TOKEN", "")
    got = request.args.get("key") or request.headers.get("X-Diag-Key") or ""
    if not want or not hmac.compare_digest(want, got):
        if not _rate_ok("diag:" + _client_ip()):
            return jsonify({"error": "cok fazla istek"}), 429
        return jsonify({"error": "DIAG_TOKEN gerekli"}), 404
    out = {"supabase": bool(supabase), "google": _google_enabled(),
           "tables": {}, "ok": True, "yapilacak": []}
    if not supabase:
        out["ok"] = False
        out["yapilacak"].append("SUPABASE_URL ve SUPABASE_KEY girilmemiş "
                                "(service_role anahtarı olmalı)")
        return jsonify(out)
    # Her tablodan tek satır okumayı dene; hata metni eksik olanı söyler.
    # kod adları (db() veritabanındaki Türkçe adlara çevirir)
    need = {
        "accounts": ["id", "username", "email", "provider", "password_hash",
                     "google_sub", "created_at", "last_seen", "play_seconds"],
        "sessions": ["token_hash", "account_id", "device_hash", "expires_at"],
        "player_data": ["account_id", "gems", "gems_earned", "gems_spent",
                        "best_score", "best_wave", "total_kills", "runs",
                        "skin_count", "pet_count", "data", "updated_at"],
        "player_events": ["account_id", "at", "kind", "delta", "total", "note"],
        "scores": ["name", "score", "kills", "wave", "run_time", "created_at",
                   "account_id", "skin", "details", "platform", "ranked", "sig"],
        "play_sessions": ["account_id", "started_at", "ended_at", "seconds", "open"],
        "friends": ["id", "a", "b", "status", "created_at"],
        "messages": ["id", "sender", "receiver", "kind", "body", "created_at", "read_at"],
        "coop_scores": ["id", "pair_key", "account_a", "account_b", "name_a", "name_b", "score",
                        "kills", "wave", "run_time", "diff", "details", "created_at"],
        "feedback": ["id", "created_at", "kind", "message"],
        # gerçek para (TL) siparişleri - bkz. README_ODEME.md
        "shop_orders": ["id", "account_id", "product_id", "kind", "amount", "currency",
                        "status", "provider", "provider_ref", "payload", "created_at",
                        "paid_at", "granted_at", "error"],
    }
    for tbl, cols in need.items():
        info = {"var": False, "eksik_sutunlar": []}
        try:
            db(tbl).select("*").limit(1).execute()
            info["var"] = True
        except Exception:
            # Ham Supabase metni değil: yalnızca "yok" bilgisi. Ayrıntı Render
            # günlüğünde.
            try:
                app.logger.exception("diag %s", tbl)
            except Exception:
                pass
            info["var"] = False
            out["ok"] = False
            real = DB_TABLES.get(tbl, (tbl,))[0]
            out["yapilacak"].append(f"'{real}' tablosu yok, VERITABANI.sql'i çalıştır")
            out["tables"][tbl] = info
            continue
        for c in cols:
            try:
                db(tbl).select(c).limit(1).execute()
            except Exception:
                info["eksik_sutunlar"].append(c)
        if info["eksik_sutunlar"]:
            out["ok"] = False
            spec = DB_TABLES.get(tbl, (tbl, {}))
            out["yapilacak"].append(
                f"'{spec[0]}' tablosunda eksik sütun: "
                + ", ".join(spec[1].get(c, c) for c in info["eksik_sutunlar"]))
        out["tables"][tbl] = info
    if not _google_enabled():
        out["yapilacak"].append("Google girişi kapalı (GOOGLE_CLIENT_ID / "
                                "GOOGLE_CLIENT_SECRET yok), zorunlu değil")
    shop_problem = _shop_config_problem()
    out["magaza"] = {"saglayici": SHOP_PROVIDER or "(kapalı)",
                     "acik": shop_problem == ""}
    if shop_problem:
        out["yapilacak"].append("Mağaza (TL ile satın alma) kapalı: " + shop_problem)
    if out["ok"] and not out["yapilacak"]:
        out["yapilacak"].append("her şey yerinde")
    return jsonify(out)


@app.route("/auth/status", methods=["GET"])
def auth_status():
    """Oyun açılışta buraya bakar: hangi giriş yolları açık?"""
    return jsonify({
        "accounts": _accounts_enabled(),
        "google": _google_enabled(),
        "client_id": GOOGLE_CLIENT_ID if _google_enabled() else "",
    })


@app.route("/auth/register", methods=["POST"])
def auth_register():
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    src = _client_ip()
    if not _rate_ok("auth:" + src):
        return jsonify({"success": False, "error": "çok fazla deneme"}), 429
    data = _body()
    # kullanıcı adı ile kayıt. kurtarma e-postası zorunlu - şifresini unutan
    # oyuncuya /auth/forgot ile kod gönderebilmek için.
    ok, uname = _clean_username(data.get("username"))
    if not ok:
        return jsonify({"success": False, "error": uname}), 400
    password = str(data.get("password", ""))
    email = str(data.get("email", "")).strip().lower()
    if not email:
        return jsonify({"success": False,
                        "error": "kurtarma e-postası gerekli"}), 400
    if len(email) > 254 or not EMAIL_RE.match(email):
        return jsonify({"success": False, "error": "e-posta geçersiz"}), 400
    if len(password) < PW_MIN_LEN:
        return jsonify({"success": False,
                        "error": f"şifre en az {PW_MIN_LEN} karakter olmalı"}), 400
    try:
        if _username_taken(uname):
            return jsonify({"success": False,
                            "error": "bu kullanıcı adı alınmış"}), 409
        if email:
            rows = db("accounts").select("id").eq("email", email).execute()
            if rows.data:
                return jsonify({"success": False,
                                "error": "bu e-posta zaten kayıtlı"}), 409
        new_acc = {
            "email": email or None,
            "username": uname,
            "name": uname,
            "provider": "password",
            "password_hash": _hash_password(password),
            "created_at": time.time(),
        }
        acc = db("accounts").insert(new_acc).execute().data[0]
        tok = _new_session(acc["id"], data.get("device"))
        return jsonify({"success": True, "token": tok, "account": _public_account(acc)})
    except Exception as e:
        return _oops(e)


@app.route("/auth/login", methods=["POST"])
def auth_login():
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    src = _client_ip()
    if not _rate_ok("auth:" + src):
        return jsonify({"success": False, "error": "çok fazla deneme"}), 429
    data = _body()
    # Oyuncu kullanıcı adını da e-postasını da yazabilir; ikisi de aynı kutudan
    # gelir.
    who = str(data.get("username") or data.get("email") or "").strip()
    password = str(data.get("password", ""))
    # hesap bazlı kilit: belirli bir hesabı deneme yanılma ile kırmaya çalışan
    # biri IP değiştirerek IP sınırını atlatabilir; bu sayaç kullanıcı adına
    # baktığı için atlatılamaz.
    if _login_locked(who.lower()):
        return jsonify({"success": False,
                        "error": "çok fazla hatalı deneme, biraz bekle"}), 429
    try:
        acc = None
        if "@" in who:
            rows = db("accounts").select("*").eq(
                "email", who.lower()).execute()
            acc = rows.data[0] if rows.data else None
        else:
            found = _accounts_by_username(who)
            acc = found[0] if found else None
        # Hesap yoksa da scrypt çalışsın: cevap süresinden hangi adların
        # kayıtlı olduğu anlaşılmasın.
        if not acc or not acc.get("password_hash"):
            _verify_password(password, _DUMMY_HASH)
            _login_failed(who.lower())
            return jsonify({"success": False,
                            "error": "kullanıcı adı ya da şifre hatalı"}), 401
        if not _verify_password(password, acc["password_hash"]):
            _login_failed(who.lower())
            return jsonify({"success": False,
                            "error": "kullanıcı adı ya da şifre hatalı"}), 401
        _login_ok(who.lower())
        tok = _new_session(acc["id"], data.get("device"))
        return jsonify({"success": True, "token": tok, "account": _public_account(acc)})
    except Exception as e:
        return _oops(e)


# ---- şifremi unuttum ----
# POST /auth/forgot {who, lang}: kayıtlı e-postaya 15 dakikalık 6 haneli kod.
#   Cevap hep success (hesap var mı yok mu belli olmasın).
# POST /auth/reset {who, code, password, device}: şifre değişir, bütün
#   oturumlar kapanır, bu cihaza yeni oturum verilir.
# Kodlar bellekte, özet olarak duruyor; sunucu yeniden başlarsa düşer.
# E-posta için biri yeter: BREVO_API_KEY veya RESEND_API_KEY (+ MAIL_FROM),
# ya da SMTP_HOST/PORT/USER/PASS + MAIL_FROM. MAIL_FROM_NAME isteğe bağlı.
RESET_CODE_TTL = 15 * 60
RESET_MAX_TRIES = 5
RESET_RESEND_GAP = 60
RESET_DAY = 24 * 3600
RESET_DAY_SENDS = 6             # hesap başına günde en çok kod
RESET_DAY_TRIES = 10            # hesap başına günde en çok yanlış deneme
_reset_codes = {}               # account_id -> {"h", "exp", "tries", "sent"}
_reset_lock = threading.Lock()
_RESET_KEY = secrets.token_bytes(32)

RESET_MAIL = {
    "tr": ("EvolveArena şifre sıfırlama kodun",
           "Merhaba {name},\n\nŞifre sıfırlama kodun: {code}\n\n"
           "Kod 15 dakika geçerli. Bu isteği sen yapmadıysan bu e-postayı yok say; "
           "şifren değişmez."),
    "en": ("Your EvolveArena password reset code",
           "Hi {name},\n\nYour password reset code: {code}\n\n"
           "It is valid for 15 minutes. If you didn't ask for this, ignore this "
           "email; your password stays the same."),
}


def _mail_configured():
    return bool(os.environ.get("MAIL_FROM") and (
        os.environ.get("BREVO_API_KEY") or os.environ.get("RESEND_API_KEY")
        or os.environ.get("SMTP_HOST")))


def _send_mail(to, subject, text):
    """Düz metin e-posta."""
    sender = os.environ.get("MAIL_FROM", "")
    sender_name = os.environ.get("MAIL_FROM_NAME", "EvolveArena")
    brevo = os.environ.get("BREVO_API_KEY", "")
    resend_key = os.environ.get("RESEND_API_KEY", "")
    if brevo:
        req = urllib.request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=json.dumps({"sender": {"email": sender, "name": sender_name},
                             "to": [{"email": to}], "subject": subject,
                             "textContent": text}).encode("utf-8"),
            headers={"api-key": brevo, "Content-Type": "application/json",
                     "Accept": "application/json"})
        urllib.request.urlopen(req, timeout=20).read()
        return
    if resend_key:
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps({"from": f"{sender_name} <{sender}>", "to": [to],
                             "subject": subject, "text": text}).encode("utf-8"),
            headers={"Authorization": f"Bearer {resend_key}",
                     "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=20).read()
        return
    import smtplib
    import ssl
    from email.message import EmailMessage
    msg = EmailMessage()
    msg["From"] = f"{sender_name} <{sender}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    host = os.environ.get("SMTP_HOST", "")
    port = int(os.environ.get("SMTP_PORT", "587") or 587)
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as s:
            s.login(os.environ.get("SMTP_USER", ""), os.environ.get("SMTP_PASS", ""))
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls(context=ctx)
            s.login(os.environ.get("SMTP_USER", ""), os.environ.get("SMTP_PASS", ""))
            s.send_message(msg)


def _reset_hash(account_id, code):
    return hmac.new(_RESET_KEY, f"{account_id}:{code}".encode("utf-8"),
                    hashlib.sha256).hexdigest()


def _find_account_by_who(who):
    """Kullanıcı adı ya da e-postadan hesap."""
    who = str(who or "").strip()
    if not who:
        return None
    if "@" in who:
        rows = db("accounts").select("*").eq("email", who.lower()).execute()
        return rows.data[0] if rows.data else None
    found = _accounts_by_username(who)
    return found[0] if found else None


@app.route("/auth/forgot", methods=["POST"])
def auth_forgot():
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    if not _rate_ok("fp:" + _client_ip(), max_n=6):
        return jsonify({"success": False, "error": "çok fazla deneme, biraz bekle"}), 429
    data = _body()
    who = str(data.get("who") or "").strip()[:96]
    lang = "tr" if str(data.get("lang") or "tr") == "tr" else "en"
    ok = jsonify({"success": True})
    if not who:
        return ok
    if not _mail_configured():
        app.logger.warning("[sifre] /auth/forgot geldi ama e-posta ayarı yok "
                           "(BREVO_API_KEY / RESEND_API_KEY / SMTP_HOST + MAIL_FROM)")
        return ok
    try:
        acc = _find_account_by_who(who)
    except Exception as e:
        return _oops(e)
    email = str((acc or {}).get("email") or "").strip()
    if not acc or not EMAIL_RE.match(email):
        return ok                       # dışarıdan ayırt edilemesin
    aid = str(acc["id"])
    now = time.time()
    with _reset_lock:
        cur = _reset_codes.get(aid)
        if cur and now - cur["sent"] < RESET_RESEND_GAP:
            return ok
        # yeniden gönderim deneme sayacını sıfırlamaz. Hesap başına 24 saatlik
        # kota.
        day0 = cur.get("day0", now) if cur and now - cur.get("day0", now) < RESET_DAY else now
        sends = (cur.get("sends", 1) + 1) if cur and day0 != now else 1
        day_tries = cur.get("day_tries", 0) if cur and day0 != now else 0
        if sends > RESET_DAY_SENDS or day_tries >= RESET_DAY_TRIES:
            return ok
        code = f"{secrets.randbelow(10 ** 6):06d}"
        _reset_codes[aid] = {"h": _reset_hash(aid, code), "exp": now + RESET_CODE_TTL,
                             "tries": 0, "sent": now, "day0": day0, "sends": sends,
                             "day_tries": day_tries}
        if len(_reset_codes) > 4096:
            for k in [k for k, v in _reset_codes.items() if v["exp"] < now]:
                _reset_codes.pop(k, None)
    subject, body = RESET_MAIL[lang]
    text = body.format(name=acc.get("username") or acc.get("name") or "", code=code)

    def worker():
        try:
            _send_mail(email, subject, text)
        except Exception:
            app.logger.exception("[sifre] e-posta gönderilemedi (hesap %s)", aid)
    threading.Thread(target=worker, daemon=True).start()
    return ok


@app.route("/auth/reset", methods=["POST"])
def auth_reset():
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    if not _rate_ok("fpr:" + _client_ip()):
        return jsonify({"success": False, "error": "çok fazla deneme, biraz bekle"}), 429
    data = _body()
    who = str(data.get("who") or "").strip()[:96]
    code = str(data.get("code") or "").strip()
    new_pw = str(data.get("password") or "")
    bad = (jsonify({"success": False, "error": "kod yanlış ya da süresi dolmuş"}), 400)
    if len(new_pw) < PW_MIN_LEN:
        return jsonify({"success": False,
                        "error": f"şifre en az {PW_MIN_LEN} karakter olmalı"}), 400
    if not (len(code) == 6 and code.isdigit()):
        return bad
    try:
        acc = _find_account_by_who(who)
    except Exception as e:
        return _oops(e)
    if not acc:
        return bad
    aid = str(acc["id"])
    with _reset_lock:
        cur = _reset_codes.get(aid)
        if (not cur or not cur.get("h") or time.time() > cur["exp"]
                or cur["tries"] >= RESET_MAX_TRIES
                or cur.get("day_tries", 0) >= RESET_DAY_TRIES):
            if cur:
                cur["h"] = ""           # kod öldü; günlük sayaç durur (silinmez)
            return bad
        if not hmac.compare_digest(cur["h"], _reset_hash(aid, code)):
            cur["tries"] += 1
            cur["day_tries"] = cur.get("day_tries", 0) + 1
            return bad
        _reset_codes.pop(aid, None)     # kod tek kullanımlık
    try:
        db("accounts").update(
            {"password_hash": _hash_password(new_pw)}).eq("id", acc["id"]).execute()
        # Şifre neden sıfırlanıyorsa (unutuldu / çalındı) eski oturumlar gider.
        db("sessions").delete().eq("account_id", acc["id"]).execute()
        _sess_cache_drop(account_id=acc["id"])
        tok = _new_session(acc["id"], data.get("device"))
    except Exception as e:
        return _oops(e)
    _login_ok(str(acc.get("username") or "").lower())
    _login_ok(str(acc.get("email") or "").lower())
    # artık şifresi var (Google hesabı da şifre kazanmış olur)
    pub = _public_account(dict(acc, password_hash="x"))
    return jsonify({"success": True, "token": tok, "account": pub})


class _GoogleError(Exception):
    """Google tarafında bir şey tutmadı."""


class _LinkRefused(Exception):
    """Google girişi şifreyle açılmış başka bir hesaba bağlanamaz."""


def _exchange_google_code(code, verifier, redirect_uri):
    """Yetkilendirme kodunu Google'da jetona çevirir ve kimlik iddialarını döndürür."""
    try:
        body = urllib.parse.urlencode({
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        }).encode()
        req = urllib.request.Request(GOOGLE_TOKEN_URL, data=body)
        with urllib.request.urlopen(req, timeout=15) as r:
            tok_res = json.loads(r.read().decode("utf-8"))
    except Exception:
        raise _GoogleError("Google doğrulaması başarısız")
    payload, why = _verify_google_id_token(tok_res.get("id_token", ""))
    if not payload:
        raise _GoogleError(why)
    return payload


@app.route("/auth/google", methods=["POST"])
def auth_google():
    """Oyundan gelen yetkilendirme kodunu jetona çevirir (PKCE)."""
    if not _google_enabled():
        return jsonify({"success": False,
                        "error": "Google girişi yapılandırılmamış"}), 503
    src = _client_ip()
    if not _rate_ok("auth:" + src):
        return jsonify({"success": False, "error": "çok fazla deneme"}), 429
    data = _body()
    code = str(data.get("code", ""))
    verifier = str(data.get("code_verifier", ""))
    redirect_uri = str(data.get("redirect_uri", ""))
    if not code or not verifier or not redirect_uri:
        return jsonify({"success": False, "error": "eksik bilgi"}), 400
    # Geri dönüş adresi yalnızca yerel olabilir (RFC 8252 loopback).
    if not _re.match(r"^http://(127\.0\.0\.1|\[::1\]|localhost):\d{1,5}/?$", redirect_uri):
        return jsonify({"success": False, "error": "geri dönüş adresi geçersiz"}), 400
    try:
        payload = _exchange_google_code(code, verifier, redirect_uri)
    except _GoogleError as e:
        # Google'ın hata gövdesini oyuncuya aynen yansıtmıyoruz.
        return _oops(e, "giriş doğrulanamadı", 401)
    try:
        acc, created = _find_or_create_account(
            payload["email"], payload.get("name") or payload.get("given_name", ""),
            "google", google_sub=payload.get("sub"))
        tok = _new_session(acc["id"], data.get("device"))
        return jsonify({"success": True, "token": tok, "new": created,
                        "account": _public_account(acc)})
    except _LinkRefused:
        return jsonify({"success": False,
                        "error": "bu e-posta kullanıcı adı + şifreyle açılmış bir hesapta kayıtlı; "
                                 "kullanıcı adın ve şifrenle giriş yap"}), 409
    except Exception as e:
        return _oops(e)


@app.route("/auth/me", methods=["POST"])
def auth_me():
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    data = _body()
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    return jsonify({"success": True, "account": _public_account(acc)})


@app.route("/auth/username", methods=["POST"])
def auth_set_username():
    """Kullanıcı adını bir kez belirler."""
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    data = _body()
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    if acc.get("username"):
        return jsonify({"success": False,
                        "error": "kullanıcı adı bir kez seçilir, değiştirilemez"}), 409
    ok, uname = _clean_username(data.get("username"))
    if not ok:
        return jsonify({"success": False, "error": uname}), 400
    if _username_taken(uname, except_id=acc["id"]):
        return jsonify({"success": False, "error": "bu kullanıcı adı alınmış"}), 409
    db("accounts").update(
        {"username": uname, "name": uname}).eq("id", acc["id"]).execute()
    _sess_cache_drop(account_id=acc["id"])
    acc["username"] = uname
    acc["name"] = uname
    return jsonify({"success": True, "account": _public_account(acc)})


# ---- oyuncu ilerlemesi ----
# Elmas, skinler, petler, kostümler, açılmış kitap/silahlar ve istatistikler
# hesaba ait: yeni hesap sıfırdan başlar, başka bilgisayarda da aynıdır, kayıt
# dosyasını kurcalayan sunucudaki hesabı şişiremez.

# Bir koşudan kazanılabilecek elmas için cömert bir üst sınır. Amaç oyunu
# kısıtlamak değil, "tek istekle 1.000.000 elmas" yolunu kapatmak.
GEM_GAIN_CAP_PER_PUSH = 5_000_000
# zamana bağlı elmas bütçesi. Hesabın bir "elmas kovası" var: en fazla
# GEM_BURST dolar, saatte GEM_RATE_PER_HOUR kadar yeniden dolar.
# (oyunda iyi bir cehennem koşusu yüz binlerce elmas getiriyor; eski 4.000'lik
# sınır oyuncunun elmasını sunucuda eksik gösteriyordu)
GEM_BURST = 5_000_000
GEM_RATE_PER_HOUR = 5_000_000
PROGRESS_LISTS = ("skins_owned", "cosmetics_owned", "books_owned", "weapons_owned", "profile_owned")
# profil kartı süsleri (oyundaki PROFILE_ITEMS ile aynı anahtarlar)
PROFILE_ITEM_KIND = {
    **{k: "bg" for k in ("bg_skull", "bg_rainbow", "bg_galaxy", "bg_inferno", "bg_frost", "bg_neon",
                         "bg_royal", "bg_matrix", "bg_sakura", "bg_storm",
                         "bg_ocean", "bg_aurora", "bg_sunset", "bg_fireflies", "bg_hearts", "bg_lava",
                         "bg_goldrain", "bg_void")},
    **{k: "frame" for k in ("fr_bronze", "fr_silver", "fr_gold", "fr_fire", "fr_diamond", "fr_rainbow",
                            "fr_emerald", "fr_ruby", "fr_amethyst", "fr_neon", "fr_electric", "fr_vine")},
    **{k: "glow" for k in ("gl_white", "gl_gold", "gl_red", "gl_cyan", "gl_purple", "gl_rainbow",
                           "gl_green", "gl_pink", "gl_orange", "gl_fire", "gl_shadow", "gl_ice")},
    **{k: "badge" for k in ("bd_crown", "bd_skull", "bd_flame", "bd_star", "bd_heart", "bd_bolt",
                            "bd_sword", "bd_gem", "bd_shield", "bd_clover", "bd_snow", "bd_ghost")},
    **{k: "title" for k in ("tt_legend", "tt_bosshunter", "tt_hellord", "tt_shadow", "tt_king",
                            "tt_immortal", "tt_lucky", "tt_sniper", "tt_champion", "tt_grinder")},
    "motto": "motto",
}
PROFILE_STYLE_SLOTS = ("bg", "frame", "glow", "badge", "title")
PROFILE_MOTTO_MAX = 40


def _clean_profile_style(st, owned):
    """Profil biçimi: yalnız sahip olunan süsler, söz kısa ve düz metin."""
    out = {"bg": "", "frame": "", "glow": "", "badge": "", "title": "", "motto": ""}
    if not isinstance(st, dict):
        return out
    own = set(owned or [])
    for k in PROFILE_STYLE_SLOTS:
        v = str(st.get(k) or "")
        if v in own and PROFILE_ITEM_KIND.get(v) == k:
            out[k] = v
    if "motto" in own:
        m = _clean_text(st.get("motto"), PROFILE_MOTTO_MAX * 2).replace("\n", " ")
        out["motto"] = " ".join(m.split())[:PROFILE_MOTTO_MAX]
    return out
# gerçek parayla satılan içerik: oyunun gönderdiği listeye yeni eklenmişse
# kabul edilmez.
PAID_SKINS = {"web_master", "ash_warrior", "green_titan", "immortal_merc"}
# yalnızca şans çarkından (sunucu) çıkan kozmetikler
WHEEL_ONLY_COSMETICS = {"crown_god"}
# yalnızca yöneticinin verebildiği kozmetikler (oyun kendi kendine ekleyemez)
ADMIN_ONLY_COSMETICS = {"crown_50m"}


def _is_paid(list_key, item):
    if list_key == "skins_owned":
        return item in PAID_SKINS
    if list_key == "cosmetics_owned":
        return str(item).startswith("pet_") or item in WHEEL_ONLY_COSMETICS or item in ADMIN_ONLY_COSMETICS
    return False

# ---- arena ustalığı (koşular arası kalıcı yükseltme) ----
# Oyundaki mastery tablosuyla birebir aynı olmalı: sunucu, iddia edilen
# ustalığın gerçekten ödenmiş olup olmadığını buradan hesaplıyor.
MASTERY_TIERS = 5
MASTERY_COSTS = {
    "m_dmg": (120, 1.60), "m_hp": (110, 1.60), "m_armor": (140, 1.65),
    "m_speed": (120, 1.60), "m_gem": (150, 1.70), "m_xp": (130, 1.65),
    "m_luck": (130, 1.65),      # uğur (kalıcı şans)
    # kapatma hakkı: elmasla +1 silah / +1 kitap kapatma (en çok 4)
    "m_wmute": (250, 1.50), "m_bmute": (250, 1.50),
}
# Kademesi sınırlı dallar (oyundaki mastery satırındaki "max").
MASTERY_MAX = {"m_wmute": 4, "m_bmute": 4}
# Kurcalanmış bir istemcinin "kademe 10^9" yazıp sayıyla oynamasını engeller;
# gerçek oyuncu bu sayıya hiçbir zaman yaklaşamaz (prestij bedeli üstel).
MASTERY_LEVEL_CAP = 60


def _mastery_cost(key, lvl):
    """lvl -> lvl+1 bedeli (oyundaki mastery_cost ile birebir)."""
    base, growth = MASTERY_COSTS[key]
    if lvl < MASTERY_TIERS:
        return int(round(base * (growth ** lvl)))
    son = base * (growth ** (MASTERY_TIERS - 1))
    return int(round(son * (1.35 ** (lvl - MASTERY_TIERS + 1))))


def _mastery_total(key, lvl):
    """0'dan lvl'e toplam bedel."""
    if key not in MASTERY_COSTS:
        return 0
    return sum(_mastery_cost(key, i) for i in range(max(0, int(lvl))))


def _merge_mastery(old, new, gems_spent):
    """Ustalığı birleştirir; toplam bedeli harcanan elması geçemez."""
    out = {}
    for key in MASTERY_COSTS:
        try:
            a = int((old or {}).get(key, 0) or 0)
        except (TypeError, ValueError):
            a = 0
        try:
            b = int((new or {}).get(key, 0) or 0)
        except (TypeError, ValueError):
            b = 0
        out[key] = max(0, min(MASTERY_MAX.get(key, MASTERY_LEVEL_CAP), max(a, b)))
    # Ödenebilirlik: en pahalı daldan başlayarak kırp.
    butce = max(0, int(gems_spent or 0))
    while sum(_mastery_total(k, v) for k, v in out.items()) > butce:
        k = max(out, key=lambda k: out[k] and _mastery_cost(k, out[k] - 1) or 0)
        if out[k] <= 0:
            break
        out[k] -= 1
    return out
PROGRESS_STATS = ("runs", "best_score", "total_kills", "total_time", "bosses",
                  "best_wave", "total_shots", "total_gold", "total_lifesteal",
                  "best_run_gold", "best_run_dashes", "best_run_shots",
                  "total_bonk_hits", "total_chests", "total_cursed", "best_curse",
                  "total_goblins",
                  # harita başarımı sayaçları (Buzul / Çöl / Orman)
                  "frost_kills", "frost_bosses", "best_frost_wave", "frost_shots",
                  "desert_dashes", "best_desert_wind", "best_desert_wave", "desert_kills",
                  "desert_bonk_hits", "jungle_snakes", "jungle_bosses", "best_jungle_time",
                  "jungle_kills",
                  # harita kilidi: haritaların en iyi dalgası, Taş Meydan bitti
                  # mi
                  "best_stone_wave", "best_jungle_wave", "stone_cleared",
                  # oyunun büyüyen sayaçlarıyla eşitlendi.
                  "best_combo", "best_run_heal", "best_run_kills", "total_bonks",
                  "total_crits", "total_dashes", "total_healed",
                  # anahtarlar / efsanevi sandık
                  "total_keys", "legend_chests")
# oyundan kaldırılan kitaplar (Çoğalma Kitabı). Eski istemciler göndermeye
# devam edebilir; sunucu bunları saklamaz.
REMOVED_BOOKS = frozenset({"r_multi"})


def _player_row(account_id):
    rows = db("player_data").select("*").eq(
        "account_id", account_id).execute()
    return rows.data[0] if rows.data else None


def _blank_progress():
    return {
        "gems": 0, "gems_earned": 0, "gems_spent": 0,
        "skins_owned": ["default"], "equipped_skin": "default",
        "cosmetics_owned": [], "equipped_cosmetics": {},
        "books_owned": [], "weapons_owned": [],
        "achievements": {}, "stats": {}, "mastery": {},
        # kalıcı dünya sıralaması yasağı. Bir kez True olunca hiçbir yerde
        # False'a dönmez; oyun da sunucu da aynı bayrağı taşır.
        "board_banned": False, "ban_reasons": [],
    }


def _stored_progress(row):
    if not row:
        return _blank_progress()
    out = _blank_progress()
    try:
        out.update(json.loads(row.get("data") or "{}")
                   if isinstance(row.get("data"), str) else (row.get("data") or {}))
    except Exception:
        pass
    out["gems"] = int(row.get("gems", 0) or 0)
    out["gems_earned"] = int(row.get("gems_earned", 0) or 0)
    out["gems_spent"] = int(row.get("gems_spent", 0) or 0)
    return out


# Dünya sıralaması yasakları kaldırıldı: hiçbir skor "imkânsız" diye
# reddedilmez, hiçbir hesap sıralamadan atılmaz. Bu iki işlev eski çağrılar
# kırılmasın diye duruyor.
def _is_banned(account_id):
    return False


def _ban_account(account_id, reason):
    return None


# hesap kilidi: aynı hesaba aynı anda gelen iki istek (ör. otomatik kayıt +
# hediye) birbirinin yazdığını ezmesin diye okuma-birleştirme-yazma tek seferde
# yapılır. Kilit süreç içi; gunicorn -w 1 ile çalıştır.
_ACCT_LOCKS = [threading.Lock() for _ in range(64)]


def _acct_lock(account_id):
    return _ACCT_LOCKS[int(hashlib.sha1(str(account_id).encode()).hexdigest()[:8], 16) % 64]


def _gem_allowance(prog, now=None):
    """Hesabın elmas kovasında şu an kaç elmaslık yer var?"""
    now = time.time() if now is None else now
    clk = prog.get("_gem_clock") or {}
    try:
        t = float(clk.get("t") or 0)
        left = float(clk.get("left", GEM_BURST))
    except (TypeError, ValueError):
        t, left = 0.0, float(GEM_BURST)
    if t <= 0 or not math.isfinite(t) or not math.isfinite(left):
        return float(GEM_BURST)
    return max(0.0, min(float(GEM_BURST), left + max(0.0, now - t) * GEM_RATE_PER_HOUR / 3600.0))


def _merge_progress(old, new, gem_cap=GEM_GAIN_CAP_PER_PUSH):
    """İlerlemeyi birleştirir: hiçbir şey geri gitmez, elmas bir seferde en çok GEM_GAIN_CAP_PER_PUSH artar."""
    out = dict(old)
    for k in PROGRESS_LISTS:
        merged = list(old.get(k) or [])
        nv = new.get(k)
        for v in (nv if isinstance(nv, list) else []):
            if isinstance(v, str) and v not in merged and not _is_paid(k, v):
                merged.append(v)
        if k == "books_owned":
            merged = [v for v in merged if v not in REMOVED_BOOKS]
        if k == "profile_owned":
            merged = [v for v in merged if v in PROFILE_ITEM_KIND]
        out[k] = merged[:400]
    if isinstance(new.get("profile_style"), dict):
        out["profile_style"] = _clean_profile_style(new["profile_style"], out.get("profile_owned"))
    for k in ("equipped_skin",):
        if new.get(k):
            out[k] = str(new[k])[:40]
    if isinstance(new.get("equipped_cosmetics"), dict):
        out["equipped_cosmetics"] = {str(a)[:20]: (str(b)[:40] if b else None)
                                     for a, b in list(new["equipped_cosmetics"].items())[:12]}
    # istatistikler: her alan yalnızca büyüyebilir
    st_old = dict(old.get("stats") or {})
    st_new = new.get("stats") or {}
    for k in PROGRESS_STATS:
        try:
            cur = float(st_old.get(k, 0) or 0)
            inc = float(st_new.get(k, 0) or 0)
            # sonlu olmayan değeri reddet.
            if not math.isfinite(inc):
                inc = 0.0
            if not math.isfinite(cur):
                cur = 0.0
            st_old[k] = min(max(cur, inc), STAT_CAP.get(k, STAT_CAP_DEFAULT))
        except Exception:
            pass
    out["stats"] = st_old
    # ---- kalıcı sıralama yasağı (başka hesaba sızan yasak) ----
    # Var olan yasak (old) aynen korunur - hileci dosyasını temizleyip geri
    # dönemez - ama yeni bir yasak yalnızca sunucunun kendi doğruladığı yoldan
    # gelir: /submit'teki imzalı skor-makullük denetimi ya da elle (admin)
    # müdahale.
    out["board_banned"] = False         # yasak yok
    out["ban_reasons"] = []
    # ücretsiz elmas sayaçları: reklam ve günlük hediye hesaplarda yalnızca
    # sunucuda işler.
    out["rewards"] = dict(old.get("rewards") or {})
    out["_gem_clock"] = dict(old.get("_gem_clock") or {})
    ach = dict(old.get("achievements") or {})
    for k, v in list((new.get("achievements") or {}).items())[:400]:
        ach.setdefault(str(k)[:40], v)
    out["achievements"] = ach
    # ---- elmas defteri ----
    earned_old = _int(old.get("gems_earned", 0))
    spent_old = _int(old.get("gems_spent", 0))
    earned_new = max(0, _int(new.get("gems_earned", 0)))
    spent_new = max(0, _int(new.get("gems_spent", 0)))
    # Sunucu tarafında (sitede: çark, kazı kazan; yönetici) işlenen elmas,
    # oyun henüz görmeden eski bir kayıt gönderirse "büyük olan kazanır"
    # birleştirmesinde kaybolmasın: oyunun gördüğü sayaçla (rewards.srv_*)
    # aradaki fark oyunun değerine eklenir. Böylece ne sitede kazanılan silinir
    # ne de sitede harcanan elmas oyunda ikinci kez harcanabilir.
    rw_old = old.get("rewards") if isinstance(old.get("rewards"), dict) else {}
    rw_new = new.get("rewards") if isinstance(new.get("rewards"), dict) else {}
    if spent_new > 0:
        spent_new += max(0, _int(rw_old.get("srv_spent"), 0) - max(0, _int(rw_new.get("srv_spent"), 0)))
    if earned_new > 0:
        earned_new += max(0, _int(rw_old.get("srv_earned"), 0) - max(0, _int(rw_new.get("srv_earned"), 0)))
    cap = int(max(0, min(GEM_GAIN_CAP_PER_PUSH, gem_cap)))
    earned = max(earned_old, min(earned_new, earned_old + cap))
    spent = max(spent_old, spent_new)
    out["gems_earned"] = earned
    out["gems_spent"] = min(spent, earned)
    out["gems"] = max(0, out["gems_earned"] - out["gems_spent"])
    # ustalık: kademe geri gitmez, tavanı var ve ödenmiş olmalı. bütçe defterin
    # sonucu (kazanılanla sınırlı harcama).
    out["mastery"] = _merge_mastery(old.get("mastery"), new.get("mastery"),
                                    out["gems_spent"])
    # kapatılan silah/kitaplar: en çok alınmış hak kadar (bedava 4 / 6 + ustalık)
    for k, m, free in (("weapons_muted", "m_wmute", 4), ("books_muted", "m_bmute", 6)):
        lst = new.get(k)
        if isinstance(lst, list):
            room = free + _int((out["mastery"] or {}).get(m, 0))
            out[k] = [str(x)[:40] for x in lst if isinstance(x, str)][:room]
        elif isinstance(old.get(k), list):
            out[k] = list(old[k])
    if isinstance(out.get("books_muted"), list):
        out["books_muted"] = [b for b in out["books_muted"] if b not in REMOVED_BOOKS]
    return out


@app.route("/player/load", methods=["POST"])
def player_load():
    """Hesabın ilerlemesini döndürür."""
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    data = _body()
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    return jsonify({"success": True, "progress": _public_progress(_stored_progress(_player_row(acc["id"])))})


def _log_event(account_id, kind, delta, total, note=""):
    """Oyuncunun ilerlemesindeki her değişikliği zamanıyla kaydeder."""
    try:
        db("player_events").insert({
            "account_id": account_id,
            "at": time.time(),
            "kind": str(kind)[:16],
            "delta": int(delta),
            "total": int(total),
            "note": str(note)[:120],
        }).execute()
    except Exception:
        pass


def _public_progress(prog):
    """Oyuna giden ilerleme: sunucunun iç alanları (elmas kovası, reklam bileti) çıkarılır."""
    out = dict(prog)
    out.pop("_gem_clock", None)
    rw = dict(out.get("rewards") or {})
    rw.pop("ad_nonce", None)
    rw.pop("ad_started", None)
    rw.pop("snow_nonce", None)          # kartopu bileti de gizli
    rw.pop("snow_started", None)
    rw.pop("wheel_nonce", None)         # çark bileti de
    rw.pop("wheel_started", None)
    rw.pop("swheel_nonce", None)        # sitedeki çarkın bileti de
    rw.pop("swheel_at", None)
    out["rewards"] = rw
    return out


def _store_progress(account_id, row, before, merged):
    """Birleştirilmiş ilerlemeyi yazar ve olay günlüğünü tutar."""
    merged["board_banned"] = False
    merged["ban_reasons"] = []
    st = merged.get("stats") or {}
    st_before = before.get("stats") or {}
    payload = {
        "account_id": account_id,
        "gems": int(merged["gems"]),
        "gems_earned": int(merged["gems_earned"]),
        "gems_spent": int(merged["gems_spent"]),
        # Aşağıdaki sütunlar veritabanında tek bakışta okunabilsin diye ayrı
        # duruyor.
        "best_score": int(st.get("best_score", 0) or 0),
        "best_wave": int(st.get("best_wave", 0) or 0),
        "total_kills": int(st.get("total_kills", 0) or 0),
        "runs": int(st.get("runs", 0) or 0),
        "skin_count": len(merged.get("skins_owned") or []),
        "pet_count": len([c for c in (merged.get("cosmetics_owned") or [])
                          if str(c).startswith("pet_")]),
        "data": {k: v for k, v in merged.items()
                 if k not in ("gems", "gems_earned", "gems_spent")},
        "updated_at": time.time(),
    }
    try:
        if row:
            db("player_data").update(payload).eq(
                "account_id", account_id).execute()
        else:
            db("player_data").insert(payload).execute()
    except Exception as e:
        # Ayrıntı Render günlüğünde, oyuncuda bildirebileceği bir iz kimliği
        # var; eksik sütunu /diag söyler.
        return _oops(e, "ilerleme yazılamadı")

    # ---- olay günlüğü ----
    d_gem = int(merged["gems_earned"]) - int(before.get("gems_earned", 0) or 0)
    if d_gem:
        _log_event(account_id, "gem", d_gem, merged["gems"], "kazanıldı")
    d_spent = int(merged["gems_spent"]) - int(before.get("gems_spent", 0) or 0)
    if d_spent:
        _log_event(account_id, "gem", -d_spent, merged["gems"], "harcandı")
    new_skins = [x for x in (merged.get("skins_owned") or [])
                 if x not in (before.get("skins_owned") or [])]
    for sk in new_skins[:20]:
        _log_event(account_id, "skin", 1, len(merged.get("skins_owned") or []), sk)
    new_cos = [x for x in (merged.get("cosmetics_owned") or [])
               if x not in (before.get("cosmetics_owned") or [])]
    for cs in new_cos[:20]:
        _log_event(account_id, "kostum", 1, len(merged.get("cosmetics_owned") or []), cs)
    d_runs = int(st.get("runs", 0) or 0) - int(st_before.get("runs", 0) or 0)
    if d_runs > 0:
        _log_event(account_id, "kosu", d_runs, int(st.get("runs", 0) or 0),
                   "en iyi skor %d" % int(st.get("best_score", 0) or 0))
    return None


@app.route("/player/save", methods=["POST"])
def player_save():
    """Oyundaki ilerlemeyi hesaba yazar (birleştirerek)."""
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    data = _body()
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    incoming = data.get("progress")
    if not isinstance(incoming, dict):
        return jsonify({"success": False, "error": "ilerleme verisi yok"}), 400
    _touch_play(acc, data)
    with _acct_lock(acc["id"]):
        row = _player_row(acc["id"])
        before = _stored_progress(row)
        now = time.time()
        allow = _gem_allowance(before, now)
        merged = _merge_progress(before, incoming, gem_cap=allow)
        gained = int(merged["gems_earned"]) - int(before.get("gems_earned", 0) or 0)
        merged["_gem_clock"] = {"t": now, "left": max(0.0, allow - max(0, gained))}
        err = _store_progress(acc["id"], row, before, merged)
    if err is not None:
        return err
    return jsonify({"success": True, "progress": _public_progress(merged)})


# ---- oynama süresi: ne zaman girdi, ne zaman çıktı, ne kadar oynadı ----
# Oyun açıkken dakikada bir /player/ping gelir (arkadaş yoklaması, skor ve
# kayıt da sayılır). PLAY_GAP'ten uzun sessizlik = oyun kapanmış; sonraki ping
# yeni bir oyun oturumu açar. Oyun kapanırken /player/bye çıkışı hemen yazar.
# Durum bellekte tutulur, veritabanına en çok PLAY_WRITE_EVERY saniyede bir
# yazılır (tek süreç: gunicorn -w 1).
PLAY_GAP = 240.0
PLAY_WRITE_EVERY = 55.0
_PLAY = {}
_PLAY_LOCKS = [threading.Lock() for _ in range(32)]


def _play_lock(aid):
    return _PLAY_LOCKS[int(hashlib.sha1(str(aid).encode()).hexdigest()[:8], 16) % 32]


def _client_meta(data):
    data = data or {}
    ver = _clean_text(data.get("version"), 16) if data.get("version") else ""
    plat = "mobile" if data.get("platform") == "mobile" else "pc"
    return ver, plat


def _touch_play(acc, data=None, closing=False):
    """Oyuncu şu an oyunda: oynama süresini ve giriş/çıkış zamanlarını işler."""
    if not acc or not supabase:
        return
    aid = acc.get("id")
    if aid is None:
        return
    now = time.time()
    ver, plat = _client_meta(data)
    try:
        with _play_lock(aid):
            st = _PLAY.get(aid)
            if st is None:
                # sunucu yeni açıldı: hesabın kayıtlı toplamından devam et
                st = {"sid": None, "start": now, "last": 0.0, "written": 0.0,
                      "total": float(_num(acc.get("play_seconds"), 0)),
                      "count": int(_num(acc.get("play_sessions"), 0))}
                seen = _num(acc.get("last_seen"), 0)
                if seen and now - seen < PLAY_GAP and _num(acc.get("last_logout"), 0) < seen:
                    rows = (db("play_sessions").select("id,started_at,open").eq("account_id", aid)
                            .order("id", desc=True).limit(1).execute().data or [])
                    if rows and rows[0].get("open"):
                        st.update(sid=rows[0]["id"], start=_num(rows[0].get("started_at"), now),
                                  last=seen, written=seen)
                _PLAY[aid] = st
            if st["sid"] is None or now - st["last"] > PLAY_GAP:
                if closing:
                    return
                # yeni oyun oturumu
                row = {"account_id": aid, "started_at": now, "ended_at": now, "seconds": 0,
                       "open": True, "platform": plat}
                if ver:
                    row["version"] = ver
                res = db("play_sessions").insert(row).execute()
                st.update(sid=(res.data or [{}])[0].get("id"), start=now, last=now, written=now)
                st["count"] += 1
                patch = {"last_login": now, "last_seen": now, "play_sessions": st["count"],
                         "platform": plat}
                if ver:
                    patch["version"] = ver
                db("accounts").update(patch).eq("id", aid).execute()
                return
            st["total"] += max(0.0, now - st["last"])
            st["last"] = now
            if closing or now - st["written"] >= PLAY_WRITE_EVERY:
                st["written"] = now
                patch = {"last_seen": now, "play_seconds": int(st["total"])}
                if closing:
                    patch["last_logout"] = now
                db("accounts").update(patch).eq("id", aid).execute()
                if st["sid"] is not None:
                    db("play_sessions").update({
                        "ended_at": now, "seconds": int(now - st["start"]),
                        "open": not closing}).eq("id", st["sid"]).execute()
            if closing:
                st["sid"] = None
                st["last"] = 0.0
    except Exception:
        # süre tutulamadı diye oyuncunun isteği bozulmasın
        app.logger.exception("oynama süresi yazılamadı")


@app.route("/player/ping", methods=["POST"])
def player_ping():
    """Oyun açık: dakikada bir gelir."""
    if not _accounts_enabled():
        return jsonify({"success": False}), 503
    data = _body()
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    _touch_play(acc, data)
    return jsonify({"success": True})


@app.route("/player/bye", methods=["POST"])
def player_bye():
    """Oyun kapanıyor: çıkış saatini yaz."""
    if not _accounts_enabled():
        return jsonify({"success": True})
    data = _body()
    acc = _acct(data)
    if acc:
        _touch_play(acc, data, closing=True)
    return jsonify({"success": True})


# ---- oyunun kendi hile itirafı ----
# Hesap, isteğin kendi geçerli oturum jetonundan (ve cihazından) çözülür: biri
# yalnızca kendi hesabını itiraf edebilir, başkasınınkini asla.
CHEAT_REPORT_REASONS = ("cheat_code", "gems", "stats", "run")


@app.route("/player/report_cheat", methods=["POST"])
def player_report_cheat():
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    data = _body()
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    # yasak yok: eski oyun sürümleri bu ucu çağırabilir, sessizce geçilir
    prog = _stored_progress(_player_row(acc["id"]))
    return jsonify({"success": True, "banned": False, "progress": _public_progress(prog)})


# ---- ücretsiz elmas: günlük hediye + reklam ----
# Hesaplı oyuncuda sunucunun saatiyle sayılır (bilgisayarın saatini geri alan
# aynı hakkı iki kez alamaz). Reklam ödülü /rewards/ad_start biletiyle ve
# AD_MIN_WATCH dolunca verilir. Değerler oyundakilerle aynı olmalı.
REWARD_TZ_OFFSET = 3 * 3600          # Türkiye (UTC+3)
AD_REWARD_GEMS = 240           # -%20
AD_DAILY_LIMIT = 5
AD_COOLDOWN = 90.0
AD_MIN_WATCH = 80.0                  # reklam = 90 sn tanıtım filmi (yedek oyun turu 120 sn)
DAILY_GIFT_GEMS = (120, 200, 280, 360, 440, 520, 600)   # (oyunla aynı) -%20
# kartopu savaşı (kardan adam etkinliği): günde 3 oyun, 30 sn; vurulan her
# düşman 1 elmas (altın goblin 3).
SNOW_DAILY = 3
SNOW_TIME = 30.0
SNOW_MAX_GEMS = 130             # tek oyunda en çok (iyi bir oyun ~100)
SNOW_MAX_ELAPSED = 15 * 60


def _server_day(offset_days=0):
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() + REWARD_TZ_OFFSET
                                                 + offset_days * 86400))


def _reward_ctx():
    """Ortak giriş denetimi: (hesap, istek verisi) ya da hata."""
    if not _accounts_enabled():
        return None, (jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503)
    data = _body()
    acc = _acct(data)
    if not acc:
        return None, (jsonify({"success": False, "error": "oturum geçersiz"}), 401)
    if not _rate_ok("rw:" + str(acc["id"])):
        return None, (jsonify({"success": False, "error": "çok sık deneme, biraz bekle"}), 429)
    return (acc, data), None


def _reward_row(account_id):
    """(satır, ilerleme, ödül sözlüğü) - _acct_lock içinde çağrılmalı."""
    row = _player_row(account_id)
    before = _stored_progress(row)
    return row, before, dict(before.get("rewards") or {})


def _ads_used_today(rw):
    return int(rw.get("ad_count", 0) or 0) if rw.get("ad_day") == _server_day() else 0


def _snow_used_today(rw):
    return int(rw.get("snow_count", 0) or 0) if rw.get("snow_day") == _server_day() else 0


# ---- iletişim / destek ----
# Oyundaki giriş ekranından "İLETİŞİM" ile gelen sorun / öneri mesajları
# Supabase'deki "feedback" tablosuna yazılır.
CONTACT_KINDS = ("sorun", "oneri", "diger")
CONTACT_MIN = 10
CONTACT_MAX = 1500
CONTACT_SHORT = (3, 600.0)          # 10 dakikada en çok 3 mesaj (IP)
CONTACT_DAY = (12, 86400.0)         # günde en çok 12 mesaj (IP)
CONTACT_ACC_DAY = (8, 86400.0)      # günde en çok 8 mesaj (hesap)
_CONTACT_SALT = os.environ.get("CONTACT_SALT", "evolve-contact-v1")


def _clean_text(txt, limit):
    out = []
    for ch in str(txt or "")[:limit * 2]:
        if ch == "\n" or ch == "\t" or (ch.isprintable() and ch not in "\u200b\u200e\u200f\u202e"):
            out.append(" " if ch == "\t" else ch)
    t = "".join(out).strip()
    while "\n\n\n" in t:
        t = t.replace("\n\n\n", "\n\n")
    return t[:limit]


@app.route("/contact", methods=["POST"])
def contact_message():
    if not supabase:
        return jsonify({"success": False, "error": "sunucu hazır değil"}), 500
    try:
        data = _body()
        kind = str(data.get("kind") or "diger")
        if kind not in CONTACT_KINDS:
            kind = "diger"
        msg = _clean_text(data.get("message"), CONTACT_MAX)
        if len(msg) < CONTACT_MIN:
            return jsonify({"success": False,
                            "error": "mesaj çok kısa (en az %d harf)" % CONTACT_MIN}), 400
        email = str(data.get("email") or "").strip().lower()[:254]
        if email and not EMAIL_RE.match(email):
            return jsonify({"success": False, "error": "e-posta adresi geçersiz"}), 400
        ip = (_client_ip() or "").split(",")[0].strip()
        if not (_rate_ok("contact:s:" + ip, *CONTACT_SHORT) and _rate_ok("contact:d:" + ip, *CONTACT_DAY)):
            return jsonify({"success": False,
                            "error": "çok sık mesaj gönderdin, biraz sonra tekrar dene"}), 429
        acc = _acct(data) if data.get("token") else None
        if acc and not _rate_ok("contact:a:%s" % acc.get("id"), *CONTACT_ACC_DAY):
            return jsonify({"success": False, "error": "bugünlük mesaj sınırına ulaştın"}), 429
        row = {
            "created_at": time.time(),
            "kind": kind,
            "message": msg,
            "email": email or ((acc or {}).get("email") or ""),
            "account_id": (acc or {}).get("id"),
            "username": str((acc or {}).get("username") or "")[:32],
            "ip_hash": hashlib.sha256((_CONTACT_SALT + ip).encode()).hexdigest()[:16],
            "version": _clean_text(data.get("version"), 16),
            "status": "yeni",
        }
        try:
            db("feedback").insert(row).execute()
        except Exception as e:
            return _oops(e, "mesaj kaydedilemedi")
        return jsonify({"success": True})
    except Exception as e:
        return _oops(e)


@app.route("/rewards/snow_start", methods=["POST"])
def rewards_snow_start():
    """Kartopu savaşı başlıyor: tek kullanımlık bilet + sunucu saati."""
    ctx, err = _reward_ctx()
    if err:
        return err
    acc, _data = ctx
    with _acct_lock(acc["id"]):
        row, before, rw = _reward_row(acc["id"])
        used = _snow_used_today(rw)
        if used >= SNOW_DAILY:
            return jsonify({"success": False, "error": "bugünkü kartopu hakkın bitti",
                            "left": 0}), 429
        nonce = secrets.token_hex(12)
        rw["snow_nonce"] = nonce
        rw["snow_started"] = time.time()
        merged = dict(before)
        merged["rewards"] = rw
        e = _store_progress(acc["id"], row, before, merged)
        if e is not None:
            return e
    return jsonify({"success": True, "ticket": nonce, "left": SNOW_DAILY - used})


@app.route("/rewards/ad_start", methods=["POST"])
def rewards_ad_start():
    ctx, err = _reward_ctx()
    if err:
        return err
    acc, _data = ctx
    with _acct_lock(acc["id"]):
        return _ad_start_locked(acc)


def _ad_start_locked(acc):
    row, before, rw = _reward_row(acc["id"])
    if _ads_used_today(rw) >= AD_DAILY_LIMIT:
        return jsonify({"success": False, "error": "bugünkü reklam hakkın bitti"}), 429
    if time.time() - float(rw.get("ad_last", 0) or 0) < AD_COOLDOWN - 2:
        return jsonify({"success": False, "error": "bir sonraki reklam için biraz bekle"}), 429
    nonce = secrets.token_hex(12)
    rw["ad_nonce"] = nonce
    rw["ad_started"] = time.time()
    merged = dict(before)
    merged["rewards"] = rw
    e = _store_progress(acc["id"], row, before, merged)
    if e is not None:
        return e
    return jsonify({"success": True, "ticket": nonce})


# ---- şans çarkı ----
# Oyuncu ÇEVİR'e basar -> /rewards/wheel_start bilet verir ve oyun siteyi açar.
# Sitede en az WHEEL_MIN_AWAY saniye kalıp dönünce /rewards/wheel_spin çarkı
# çevirir: sonucu SUNUCU seçer (oyun yalnızca çarkı o dilime döndürür), ödül
# hesaba burada yazılır. Günde WHEEL_DAILY hak. Oyundaki WHEEL_PRIZES ile aynı
# olmalı (oyun oranları ekranda gösteriyor).
WHEEL_DAILY = 5
WHEEL_COOLDOWN = 60.0
WHEEL_MIN_AWAY = 30.0
WHEEL_MAX_AWAY = 30 * 60.0
WHEEL_PRIZES = (            # (ödül, yüzde olasılık)
    ("g200", 25.0), ("g300", 22.0), ("g500", 18.0), ("g1000", 14.5), ("g2500", 10.0),
    ("g5000", 7.1), ("g10000", 1.0), ("crown_god", 2.0),
    ("ash_warrior", 0.1), ("green_titan", 0.1), ("immortal_merc", 0.1), ("web_master", 0.1),
)
WHEEL_DUPE_GEMS = 5000       # zaten sahip olunan taç / skin çıkarsa yerine elmas
_wheel_rng = secrets.SystemRandom()


def _wheel_pick():
    total = sum(w for _p, w in WHEEL_PRIZES)
    x = _wheel_rng.uniform(0.0, total)
    for prize, w in WHEEL_PRIZES:
        x -= w
        if x <= 0:
            return prize
    return WHEEL_PRIZES[0][0]


def _wheel_apply(before, prize, site=False):
    """Çark ödülünü ilerlemeye işler: (yeni ilerleme, elmas, zaten vardı mı)."""
    merged = json.loads(json.dumps(before))
    gems = 0
    dupe = False
    if prize[:1] == "g" and prize[1:].isdigit():        # "g200" (green_titan değil)
        gems = int(prize[1:])
    elif prize in WHEEL_ONLY_COSMETICS:
        lst = list(merged.get("cosmetics_owned") or [])
        if prize in lst:
            dupe, gems = True, WHEEL_DUPE_GEMS
        else:
            lst.append(prize)
            merged["cosmetics_owned"] = lst
    else:
        lst = list(merged.get("skins_owned") or ["default"])
        if prize in lst:
            dupe, gems = True, WHEEL_DUPE_GEMS
        else:
            lst.append(prize)
            merged["skins_owned"] = lst
    if gems:
        merged["gems_earned"] = min(GEM_TOTAL_MAX, int(before.get("gems_earned", 0) or 0) + gems)
        merged["gems"] = max(0, merged["gems_earned"] - int(before.get("gems_spent", 0) or 0))
    return merged, gems, dupe


def _wheel_used_today(rw):
    return int(rw.get("wheel_count", 0) or 0) if rw.get("wheel_day") == _server_day() else 0


@app.route("/rewards/wheel_start", methods=["POST"])
def rewards_wheel_start():
    ctx, err = _reward_ctx()
    if err:
        return err
    acc, _data = ctx
    with _acct_lock(acc["id"]):
        row, before, rw = _reward_row(acc["id"])
        used = _wheel_used_today(rw)
        if used >= WHEEL_DAILY:
            return jsonify({"success": False, "error": "bugünkü çark hakkın bitti", "left": 0}), 429
        if time.time() - _num(rw.get("wheel_last"), 0) < WHEEL_COOLDOWN - 2:
            return jsonify({"success": False, "error": "bir sonraki çevirme için biraz bekle"}), 429
        nonce = secrets.token_hex(12)
        rw["wheel_nonce"] = nonce
        rw["wheel_started"] = time.time()
        merged = dict(before)
        merged["rewards"] = rw
        e = _store_progress(acc["id"], row, before, merged)
        if e is not None:
            return e
    return jsonify({"success": True, "ticket": nonce, "left": WHEEL_DAILY - used,
                    "wait": WHEEL_MIN_AWAY})


@app.route("/rewards/wheel_spin", methods=["POST"])
def rewards_wheel_spin():
    ctx, err = _reward_ctx()
    if err:
        return err
    acc, data = ctx
    with _acct_lock(acc["id"]):
        row, before, rw = _reward_row(acc["id"])
        ticket = str(data.get("ticket") or "")
        if not ticket or not hmac.compare_digest(ticket, str(rw.get("wheel_nonce") or "")):
            return jsonify({"success": False, "error": "çark bileti geçersiz"}), 403
        el = time.time() - _num(rw.get("wheel_started"), 0)
        if el < WHEEL_MIN_AWAY - 1.0:
            return jsonify({"success": False, "error": "sitede %d saniye kalmalısın" % int(WHEEL_MIN_AWAY),
                            "wait": max(0.0, WHEEL_MIN_AWAY - el)}), 403
        if el > WHEEL_MAX_AWAY:
            rw.pop("wheel_nonce", None)
            return jsonify({"success": False, "error": "çark biletinin süresi doldu"}), 403
        if _wheel_used_today(rw) >= WHEEL_DAILY:
            return jsonify({"success": False, "error": "bugünkü çark hakkın bitti"}), 429
        prize = _wheel_pick()
        merged, gems, dupe = _wheel_apply(before, prize)
        rw["wheel_count"] = _wheel_used_today(rw) + 1
        rw["wheel_day"] = _server_day()
        rw["wheel_last"] = time.time()
        rw["wheel_total"] = int(rw.get("wheel_total", 0) or 0) + 1
        rw.pop("wheel_nonce", None)          # bilet bir kez kullanılır
        rw.pop("wheel_started", None)
        merged["rewards"] = rw
        e = _store_progress(acc["id"], row, before, merged)
        if e is not None:
            return e
        _log_event(acc["id"], "cark", gems, int(merged.get("gems", 0) or 0),
                   ("şans çarkı: " + prize + (" (zaten vardı)" if dupe else ""))[:120])
    return jsonify({"success": True, "prize": prize, "gems": gems, "dupe": dupe,
                    "left": WHEEL_DAILY - int(rw["wheel_count"]),
                    "progress": _public_progress(merged)})


@app.route("/rewards/claim", methods=["POST"])
def rewards_claim():
    ctx, err = _reward_ctx()
    if err:
        return err
    acc, data = ctx
    with _acct_lock(acc["id"]):
        return _claim_locked(acc, data)


def _claim_locked(acc, data):
    row, before, rw = _reward_row(acc["id"])
    kind = str(data.get("kind") or "")
    now = time.time()
    today = _server_day()
    if kind == "gift":
        if rw.get("gift_day") == today:
            return jsonify({"success": False, "error": "bugünün hediyesini zaten aldın"}), 409
        streak = int(rw.get("gift_streak", 0) or 0)
        idx = (streak % len(DAILY_GIFT_GEMS)) if rw.get("gift_day") == _server_day(-1) else 0
        amount = DAILY_GIFT_GEMS[idx]
        rw["gift_day"] = today
        rw["gift_streak"] = idx + 1
        note = "günlük hediye"
    elif kind == "ad":
        ticket = str(data.get("ticket") or "")
        if not ticket or not hmac.compare_digest(ticket, str(rw.get("ad_nonce") or "")):
            return jsonify({"success": False, "error": "reklam bileti geçersiz"}), 403
        if now - float(rw.get("ad_started", 0) or 0) < AD_MIN_WATCH:
            return jsonify({"success": False, "error": "reklam sonuna kadar izlenmedi"}), 403
        if _ads_used_today(rw) >= AD_DAILY_LIMIT:
            return jsonify({"success": False, "error": "bugünkü reklam hakkın bitti"}), 429
        rw["ad_count"] = _ads_used_today(rw) + 1
        rw["ad_day"] = today
        rw["ad_last"] = now
        rw["ad_total"] = int(rw.get("ad_total", 0) or 0) + 1
        rw.pop("ad_nonce", None)        # bilet bir kez kullanılır
        rw.pop("ad_started", None)
        amount = AD_REWARD_GEMS
        note = "reklam"
    elif kind == "snow":
        ticket = str(data.get("ticket") or "")
        if not ticket or not hmac.compare_digest(ticket, str(rw.get("snow_nonce") or "")):
            return jsonify({"success": False, "error": "oyun bileti geçersiz"}), 403
        el = now - _num(rw.get("snow_started"), 0)
        if el < SNOW_TIME - 1.0:
            return jsonify({"success": False, "error": "oyun süresi dolmadan bozdurulamaz"}), 403
        if el > SNOW_MAX_ELAPSED:
            rw.pop("snow_nonce", None)
            return jsonify({"success": False, "error": "oyun biletinin süresi doldu"}), 403
        if _snow_used_today(rw) >= SNOW_DAILY:
            return jsonify({"success": False, "error": "bugünkü kartopu hakkın bitti"}), 429
        amount = max(0, min(SNOW_MAX_GEMS, _int(data.get("hits"), 0)))
        rw["snow_count"] = _snow_used_today(rw) + 1
        rw["snow_day"] = today
        rw["snow_best"] = max(_int(rw.get("snow_best"), 0), amount)
        rw.pop("snow_nonce", None)      # bilet bir kez kullanılır
        rw.pop("snow_started", None)
        note = "kartopu"
    else:
        return jsonify({"success": False, "error": "bilinmeyen ödül"}), 400
    merged = dict(before)
    merged["rewards"] = rw
    merged["gems_earned"] = int(before.get("gems_earned", 0) or 0) + amount
    merged["gems"] = max(0, merged["gems_earned"] - int(before.get("gems_spent", 0) or 0))
    e = _store_progress(acc["id"], row, before, merged)
    if e is not None:
        return e
    # (elmas artışı _store_progress'te "gem / kazanıldı" olarak zaten günlüğe
    # yazıldı)
    return jsonify({"success": True, "amount": amount, "note": note,
                    "progress": _public_progress(merged)})


@app.route("/auth/logout", methods=["POST"])
def auth_logout():
    if not _accounts_enabled():
        return jsonify({"success": True})
    data = _body()
    tok = str(data.get("token", ""))
    if tok:
        try:
            acc = _account_by_session(tok)
            if acc:
                _touch_play(acc, data, closing=True)
        except Exception:
            pass
        _sess_cache_drop(_token_hash(tok))
        try:
            db("sessions").delete().eq(
                "token_hash", _token_hash(tok)).execute()
        except Exception:
            pass
    return jsonify({"success": True})


@app.route("/auth/logout_all", methods=["POST"])
def auth_logout_all():
    """Bütün cihazlardan çıkış."""
    if not _accounts_enabled():
        return jsonify({"success": True})
    data = _body()
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    try:
        db("sessions").delete().eq("account_id", acc["id"]).execute()
        _sess_cache_drop(account_id=acc["id"])
    except Exception as e:
        return _oops(e)
    return jsonify({"success": True})


@app.route("/auth/email", methods=["POST"])
def auth_email():
    """Kurtarma e-postası ekle/değiştir. Şifreli hesapta mevcut şifre istenir."""
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    if not _rate_ok("email:" + _client_ip()):
        return jsonify({"success": False, "error": "çok fazla deneme"}), 429
    data = _body()
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    if acc.get("provider") == "google":
        return jsonify({"success": False,
                        "error": "Google hesabının e-postası değiştirilemez"}), 400
    email = str(data.get("email", "")).strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        return jsonify({"success": False, "error": "e-posta geçersiz"}), 400
    cur_hash = str(acc.get("password_hash") or "")
    if cur_hash and not _verify_password(str(data.get("password", "")), cur_hash):
        _login_failed(str(acc.get("username") or "").lower())
        return jsonify({"success": False, "error": "mevcut şifre hatalı"}), 403
    try:
        rows = db("accounts").select("id").eq("email", email).execute()
        if any(str(r.get("id")) != str(acc["id"]) for r in (rows.data or [])):
            return jsonify({"success": False,
                            "error": "bu e-posta zaten kayıtlı"}), 409
        db("accounts").update({"email": email}).eq("id", acc["id"]).execute()
        _sess_cache_drop(account_id=acc["id"])
        acc = dict(acc, email=email)
    except Exception as e:
        return _oops(e)
    return jsonify({"success": True, "account": _public_account(acc)})


@app.route("/auth/password", methods=["POST"])
def auth_password():
    """Şifre değiştirme: oturum + cihaz + mevcut şifre ister, bütün oturumları kapatır."""
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    if not _rate_ok("pw:" + _client_ip()):
        return jsonify({"success": False, "error": "çok fazla deneme"}), 429
    data = _body()
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    new_pw = str(data.get("new_password", ""))
    if len(new_pw) < PW_MIN_LEN:
        return jsonify({"success": False,
                        "error": f"şifre en az {PW_MIN_LEN} karakter olmalı"}), 400
    cur_hash = str(acc.get("password_hash") or "")
    if cur_hash:
        if not _verify_password(str(data.get("password", "")), cur_hash):
            _login_failed(str(acc.get("username") or "").lower())
            return jsonify({"success": False, "error": "mevcut şifre hatalı"}), 403
    try:
        db("accounts").update(
            {"password_hash": _hash_password(new_pw)}).eq("id", acc["id"]).execute()
        # Bütün oturumları kes, sonra çağırana yeni bir tane ver.
        db("sessions").delete().eq("account_id", acc["id"]).execute()
        _sess_cache_drop(account_id=acc["id"])
        tok = _new_session(acc["id"], data.get("device"))
    except Exception as e:
        return _oops(e)
    return jsonify({"success": True, "token": tok})


# ---- hile koruması ----
# İstemcideki koruma her zaman aşılabilir, asıl karar burada. Üç süzgeç:
# imza (SUBMIT_SECRET), makullük (skor; öldürme, dalga ve süreyle tutarlı mı)
# ve hız sınırı.
# KASMA_SUBMIT_SECRET Render'da ayarlı olmalı ve oyundaki SUBMIT_SECRET ile
# aynı olmalı. Buradaki varsayılan sadece geliştirme için.

SUBMIT_SECRET = os.environ.get("KASMA_SUBMIT_SECRET",
                               "kasma-arena-submit-v1:3d7f90ac41be6528")
# İmza zorunlu mu? Eski istemcilerin bir süre çalışabilmesi için kapatılabilir.
REQUIRE_SIGNATURE = os.environ.get("KASMA_REQUIRE_SIG", "1") == "1"

# ---- sınırlar ----
# "İmkânsız skor" denetimi yok: dürüst ama çok güçlü koşular da reddediliyordu.
# Yalnızca veritabanını bozacak uç değerler (negatif, taşan sayı) kırpılır.
MAX_RUN_TIME = 24 * 3600.0
MAX_WAVE = 100_000
MAX_SCORE = 9_000_000_000_000
MAX_KILLS = 9_000_000_000
# istatistik tavanları: kurcalanmış istemci "10^18 öldürme" yazıp tabloları
# bozamasın. Gerçek oyuncu bunlara yaklaşamaz.
STAT_CAP_DEFAULT = 10 ** 9
STAT_CAP = {
    "runs": 1_000_000,
    "best_score": MAX_SCORE,
    "best_wave": MAX_WAVE,
    "total_kills": 100_000_000,
    "total_time": 10 * 365 * 24 * 3600,     # on yıllık oynanış
    "bosses": 1_000_000,
    "total_shots": 1_000_000_000,
}
# ---- hız sınırı ----
RATE_WINDOW = 300.0            # saniye
RATE_MAX = 40                  # bu pencerede aynı kaynaktan en çok kaç gönderi
_rate_hits = defaultdict(deque)
_rate_lock = threading.Lock()


# hesap bazlı giriş kilidi.
LOGIN_FAIL_MAX = 10            # bu kadar yanlış denemeden sonra
LOGIN_LOCK_SECS = 60.0         # bu kadar saniye kilitli
_login_fails = defaultdict(deque)
_login_lock = threading.Lock()


def _login_locked(who):
    """Bu hesap şu an kilitli mi?"""
    if not who:
        return False
    now = time.time()
    with _login_lock:
        dq = _login_fails[who]
        while dq and now - dq[0] > LOGIN_LOCK_SECS:
            dq.popleft()
        return len(dq) >= LOGIN_FAIL_MAX


def _login_failed(who):
    """Yanlış denemeyi kaydet."""
    if not who:
        return
    now = time.time()
    with _login_lock:
        _login_fails[who].append(now)
        if len(_login_fails) > 4096:
            for k in [k for k, v in _login_fails.items()
                      if not v or now - v[-1] > LOGIN_LOCK_SECS]:
                _login_fails.pop(k, None)


def _login_ok(who):
    """Doğru girişte sayaç sıfırlanır."""
    if who:
        with _login_lock:
            _login_fails.pop(who, None)


def _rate_ok(key, max_n=RATE_MAX, window=RATE_WINDOW):
    now = time.time()
    with _rate_lock:
        dq = _rate_hits[key]
        while dq and now - dq[0] > window:
            dq.popleft()
        if len(dq) >= max_n:
            return False
        dq.append(now)
        # süresi geçmiş anahtarları at, sözlük sınırsız büyümesin
        if len(_rate_hits) > 4096:
            for k in [k for k, v in _rate_hits.items()
                      if not v or now - v[-1] > RATE_WINDOW]:
                _rate_hits.pop(k, None)
            # Hâlâ büyükse en eski dokunulanları at: bellek her şeyden önce.
            if len(_rate_hits) > 8192:
                for k in sorted(_rate_hits,
                                key=lambda k: _rate_hits[k][-1]
                                )[:len(_rate_hits) - 4096]:
                    _rate_hits.pop(k, None)
        return True


# Oyundaki SUBMIT_SIG_FIELDS ile birebir aynı olmalı.
SUBMIT_SIG_FIELDS = ("name", "score", "kills", "wave", "run_time", "created_at", "diff")

SCORE_PUBLIC_FIELDS = ("name", "score", "kills", "wave", "run_time", "diff",
                       "created_at", "skin", "build", "style")

# ---- koşu kartı ----
# Sıralamada bir skora tıklayınca açılan ayrıntı (skin, silahlar, kitaplar,
# hasar, istatistikler). Kart oyuncudan geldiği için özeti imzaya giriyor ve
# burada alan alan süzülüyor: sadece bilinen anahtarlar, tavanlı sayılar,
# serbest metin yok; skin hesapta yoksa "default" yazılıyor.
BUILD_WEAPONS = frozenset((
    "axe", "book", "pentagram", "whip", "zemzem", "shoe", "frost", "emanet", "cloak",
    "tornado", "ghost_swords", "wolves", "tesla", "meteor", "beam", "hawk", "bats",
    "nova", "knives", "quake"))
BUILD_BOOKS = frozenset((
    "r_armor", "r_aspd", "r_bonk", "r_bosshunter", "r_clover", "r_coin", "r_crit",
    "r_critd", "r_dashslow", "r_dmg", "r_echo", "r_evade", "r_execute", "r_hp",
    "r_hp_big", "r_killheal", "r_lasthope", "r_luck", "r_mag", "r_pierce", "r_poison",
    "r_rage", "r_regen", "r_roar", "r_spd", "r_swarm", "r_vamp", "r_wspd", "r_xp",
    "r_ice"))
BUILD_DMG_EXTRA = frozenset(("gun", "bonk", "storm", "ult", "orbit", "other"))
BUILD_MAPS = frozenset(("stone", "frost", "jungle", "desert"))
BUILD_WEAPON_MAX = 6            # oyunda 4 yuva (+ pay)
BUILD_BOOK_MAX = 8              # 4 normal + 1 nadir (+ pay)
BUILD_LEVEL_CAP = 40            # silah tavanı 25, kitap tavanı 30
# istatistik: (alt, üst) - üst sınırlar dürüst oyunun çok üstünde, saçmalığı
# keser
BUILD_STATS = {
    "hp": (1, 100000), "regen": (0, 5000), "armor": (0, 1.0), "vamp": (0, 5.0),
    "dmg": (0, 1000), "crit": (0, 1.0), "critd": (0, 100), "aspd": (0, 100),
    "dps": (0, 1e6), "multi": (1, 50), "pierce": (0, 200), "speed": (0, 20),
    "dash": (0, 50), "bonk": (0, 50), "pickup": (0, 5000), "gold": (0, 100),
    "xp": (0, 100), "luck": (0, 50), "lvl": (1, 999), "bosses": (0, 500),
}
BUILD_RAW_MAX = 6000            # karta ayrılan en büyük JSON boyu (bayt)
_KEY_RE = _re.compile(r"^[a-z0-9_]{1,40}$")


def _build_hash(details):
    """İstemcideki build_hash ile birebir aynı kanonik JSON özeti."""
    raw = json.dumps(details, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32], len(raw)


def _clean_build(d, owned_skins):
    """Koşu kartını süzer."""
    if not isinstance(d, dict):
        return None, "default"
    out = {"v": 1}
    sk = str(d.get("skin") or "default")
    skin = sk if (_KEY_RE.match(sk) and (sk == "default" or sk in owned_skins)) else "default"
    out["skin"] = skin
    mp = str(d.get("map") or "stone")
    out["map"] = mp if mp in BUILD_MAPS else "stone"
    out["hell"] = bool(d.get("hell"))

    def pairs(lst, allowed, cap_n, cap_v, as_int=True):
        res, seen = [], set()
        if not isinstance(lst, list):
            return res
        for it in lst[:cap_n * 3]:
            if not (isinstance(it, (list, tuple)) and len(it) == 2):
                continue
            k = str(it[0])
            if k not in allowed or k in seen:
                continue
            v = _num(it[1], -1)
            if v < 0:
                continue
            v = min(v, cap_v)
            res.append([k, int(v) if as_int else round(v, 3)])
            seen.add(k)
            if len(res) >= cap_n:
                break
        return res

    out["w"] = [p_ for p_ in pairs(d.get("w"), BUILD_WEAPONS, BUILD_WEAPON_MAX, BUILD_LEVEL_CAP) if p_[1] >= 1]
    out["b"] = [p_ for p_ in pairs(d.get("b"), BUILD_BOOKS, BUILD_BOOK_MAX, BUILD_LEVEL_CAP) if p_[1] >= 1]
    out["d"] = pairs(d.get("d"), BUILD_WEAPONS | BUILD_DMG_EXTRA, 24, 1e13)
    out["d"].sort(key=lambda x: -x[1])
    st_in = d.get("st") if isinstance(d.get("st"), dict) else {}
    st = {}
    for k, (lo, hi) in BUILD_STATS.items():
        if k in st_in:
            v = _num(st_in.get(k), None)
            if v is not None:
                st[k] = round(max(lo, min(hi, v)), 3)
    out["st"] = st
    return out, skin


def _public_score(row):
    """Sıralama satırının dışarı çıkabilen alanları."""
    return {k: row.get(k) for k in SCORE_PUBLIC_FIELDS if k in row}


def _expected_sig(payload):
    """İmza, istemcideki sign_submit ile birebir aynı sırayı kullanır."""
    fields = SUBMIT_SIG_FIELDS + (("build",) if payload.get("build") else ())
    # mobil gönderide "platform" alanı da imzalı (skor tablo değiştiremez)
    if payload.get("platform"):
        fields = fields + ("platform",)
    # süreli dalga kipi de imzalı (eski istemciler bu alanı göndermez)
    if payload.get("wmode"):
        fields = fields + ("wmode",)
    msg = "|".join(str(payload.get(k, "")) for k in fields)
    return hmac.new(SUBMIT_SECRET.encode("utf-8"), msg.encode("utf-8"),
                    hashlib.sha256).hexdigest()


# ---- skor tablosu ----

WORLD_LB_ROWS = 50              # sıralamada gösterilen koşu sayısı


@app.route("/scores", methods=["GET"])
def get_scores():
    if not supabase:
        return jsonify({"error": "Supabase bağlantısı yapılandırılmamış!"}), 500
    try:
        # Bir oyuncu tabloda birden çok kez yer alabilir, her koşu ayrı satır.
        # ?platform=mobile telefon tablosunu verir.
        plat = "mobile" if request.args.get("platform") == "mobile" else "pc"
        rows = (db(WORLD_TABLE).select("name,score,kills,wave,run_time,diff,created_at,skin,details,account_id")
                .eq("platform", plat).eq("ranked", True)
                .order("score", desc=True).limit(WORLD_LB_ROWS).execute().data or [])
        styles = {}
        ids = sorted({str(r.get("account_id")) for r in rows if r.get("account_id") is not None})
        if ids:
            try:
                for pr in db("player_data").select("account_id,data").in_("account_id", ids).execute().data or []:
                    d = pr.get("data") if isinstance(pr.get("data"), dict) else {}
                    styles[str(pr.get("account_id"))] = _clean_profile_style(d.get("profile_style"),
                                                                             d.get("profile_owned"))
            except Exception:
                app.logger.exception("profil biçimleri okunamadı")
        out = []
        for r in rows:
            r = dict(r)
            r["style"] = styles.get(str(r.pop("account_id", None)))
            row = dict(r)
            row["build"] = row.pop("details", None)
            row["skin"] = str(row.get("skin") or (row["build"] or {}).get("skin") or "default")[:40]
            out.append(_public_score(row))
        return jsonify(out)
    except Exception as e:
        return _oops(e)


def _is_duplicate_error(e):
    t = str(e).lower()
    return "23505" in t or "duplicate key" in t or "already exists" in t


@app.route("/submit", methods=["POST"])
def add_score():
    """Biten koşuyu kaydeder. Taş Meydan koşuları dünya sıralamasına girer,
    öbür haritalar yalnızca oyuncunun geçmişine yazılır.

    Aynı gönderi (aynı imza) ikinci kez gelirse - oyun cevabı alamayıp yeniden
    denediğinde - hata değil "kaydedildi" döner."""
    if not supabase:
        return jsonify({"success": False, "error": "sunucu hazır değil"}), 500
    try:
        data = _body()
        name = str(data.get("name", "Anonim"))[:14]
        score = _int(data.get("score"), 0)
        kills = _int(data.get("kills"), 0)
        wave = _int(data.get("wave"), 0)
        run_time = _num(data.get("run_time"), 0.0)
        diff = str(data.get("diff", "normal"))
        if diff not in ("normal", "hard", "nightmare"):
            diff = "normal"

        if not _rate_ok("sub:" + _client_ip()):
            return jsonify({"success": False, "error": "çok sık gönderim, biraz bekle"}), 429

        # ---- imza: sıralamaya elle (curl ile) skor yazılamasın ----
        sig = str(data.get("sig") or "")[:128]
        if REQUIRE_SIGNATURE:
            build_h = ""
            if data.get("details") is not None:
                build_h, _raw_len = _build_hash(data.get("details"))
            want = _expected_sig({
                "name": name, "score": data.get("score", 0), "kills": data.get("kills", 0),
                "wave": data.get("wave", 0), "run_time": data.get("run_time", 0),
                "created_at": data.get("created_at", 0),
                "diff": str(data.get("diff", "normal")), "build": build_h,
                "platform": "mobile" if data.get("platform") == "mobile" else "",
                "wmode": "time" if data.get("wmode") == "time" else "",
            })
            if not sig or not hmac.compare_digest(sig, want):
                return jsonify({"success": False,
                                "error": "oyun sürümün eski, oyunu güncelle"}), 403

        if str(data.get("mode") or "") == "coop":
            return jsonify({"success": False, "error": "2 kişilik koşular buradan gönderilmez"}), 422

        acc = _acct(data)
        if not acc:
            return jsonify({"success": False,
                            "error": "dünya sıralaması için giriş gerekli"}), 401
        if not acc.get("username"):
            return jsonify({"success": False,
                            "error": "önce kullanıcı adı seçmelisin"}), 409
        account_id = acc.get("id")
        _touch_play(acc, data)

        # aynı koşu ikinci kez geldiyse: zaten yazılı
        if sig:
            seen = db(WORLD_TABLE).select("id").eq("sig", sig).limit(1).execute().data
            if seen:
                return jsonify({"success": True, "again": True})

        platform = "mobile" if data.get("platform") == "mobile" else "pc"
        payload = {
            "account_id": account_id,
            # ad sunucudan gelir: kimse başkasının adıyla skor gönderemez
            "name": str(acc.get("username"))[:14],
            "score": max(0, min(score, MAX_SCORE)),
            "kills": max(0, min(kills, MAX_KILLS)),
            "wave": max(0, min(wave, MAX_WAVE)),
            "run_time": max(0.0, min(run_time, MAX_RUN_TIME)),
            "diff": diff,
            "platform": platform,
            "created_at": time.time(),
            "sig": sig or None,
        }
        mp = "stone"
        if data.get("details") is not None:
            owned = set(_stored_progress(_player_row(account_id)).get("skins_owned") or [])
            build, skin = _clean_build(data.get("details"), owned)
            if build is not None:
                payload["details"] = build
                payload["skin"] = skin
                mp = build.get("map") or "stone"
        payload["map"] = mp
        # dünya sıralaması yalnızca Taş Meydan'da (öbür haritaların kuralları
        # skoru kolaylaştırıyor); öbür koşular oyuncunun geçmişinde durur
        payload["ranked"] = (mp == "stone")
        try:
            db(WORLD_TABLE).insert(payload).execute()
        except Exception as e:
            if sig and _is_duplicate_error(e):
                return jsonify({"success": True, "again": True})
            raise
        rank = None
        if payload["ranked"]:
            try:
                res = (db(WORLD_TABLE).select("id", count="exact").eq("platform", platform)
                       .eq("ranked", True).gt("score", payload["score"]).limit(1).execute())
                if res.count is not None:
                    rank = int(res.count) + 1
            except Exception:
                rank = None
        return jsonify({"success": True, "ranked": payload["ranked"], "rank": rank})
    except Exception as e:
        return _oops(e, "skor kaydedilemedi")


# ---- eski steam uçları (oyun artık kullanmıyor, varsayılan kapalı) ----

# Gerekirse Render'da LEGACY_STEAM_API=1.
LEGACY_STEAM_API = os.environ.get("LEGACY_STEAM_API") == "1"


def _legacy_off():
    return jsonify({"success": False, "error": "bu uç kapalı"}), 404


@app.route("/get_player", methods=["POST"])
def get_player():
    if not LEGACY_STEAM_API:
        return _legacy_off()
    if not supabase:
        return jsonify({"error": "Supabase bağlantısı yok!"}), 500
    try:
        data = _body()
        steam_id = data.get("steam_id")
        name = data.get("name", "Steam Oyuncusu")
        
        if not steam_id:
            return jsonify({"error": "steam_id gereklidir!"}), 400

        # Oyuncuyu benzersiz steam_id'si ile veritabanında arıyoruz
        response = db("players").select("*").eq("steam_id", steam_id).execute()
        
        if response.data and len(response.data) > 0:
            return jsonify({"success": True, "data": response.data[0]})
        else:
            # Oyuncu ilk defa giriyorsa sıfır elmas ve default skinle kayıt
            # açıyoruz
            new_player = {
                "steam_id": steam_id,
                "name": name,
                "gems": 0,
                "skins": "default",
                "selected_skin": "default"
            }
            ins_res = db("players").insert(new_player).execute()
            return jsonify({"success": True, "data": ins_res.data[0]})
    except Exception as e:
        return _oops(e)

@app.route("/update_player", methods=["POST"])
def update_player():
    if not LEGACY_STEAM_API:
        return _legacy_off()
    if not supabase:
        return jsonify({"error": "Supabase bağlantısı yok!"}), 500
    try:
        data = _body()
        steam_id = data.get("steam_id")
        selected_skin = data.get("selected_skin")

        if not steam_id:
            return jsonify({"error": "steam_id gereklidir!"}), 400

        # hile koruması: bu uç nokta artık "gems" ve "skins" kabul etmiyor.
        payload = {}
        if selected_skin is not None:
            row = db("players").select("skins").eq(
                "steam_id", steam_id).execute()
            owned = (row.data[0].get("skins") if row.data else "") or "default"
            owned_list = [x.strip() for x in str(owned).split(",") if x.strip()]
            if selected_skin not in owned_list:
                return jsonify({"success": False,
                                "error": "bu skine sahip değilsin"}), 403
            payload["selected_skin"] = selected_skin
        if not payload:
            return jsonify({"success": True, "data": []})

        # Steam ID'ye göre oyuncunun verilerini güvenle güncelliyoruz
        response = db("players").update(payload).eq("steam_id", steam_id).execute()
        return jsonify({"success": True, "data": response.data})
    except Exception as e:
        return _oops(e)


# ---- steam ile elmas satın alma (ISteamMicroTxn) ----

STEAM_PUBLISHER_KEY = os.environ.get("STEAM_PUBLISHER_KEY")
STEAM_APP_ID = os.environ.get("STEAM_APP_ID")
STEAM_SANDBOX = os.environ.get("STEAM_MICROTXN_SANDBOX") == "1"

_MICROTXN_BASE = ("https://partner.steam-api.com/ISteamMicroTxnSandbox"
                 if STEAM_SANDBOX else
                 "https://partner.steam-api.com/ISteamMicroTxn")

GEM_PACKS = {
    1001: (500,  "500 Elmas",   2900,  "TRY"),
    1002: (1320, "1.320 Elmas", 5900,  "TRY"),
    1003: (3120, "3.120 Elmas", 11900, "TRY"),
    1004: (9450, "9.450 Elmas", 27900, "TRY"),
}

def _purchases_enabled():
    return bool(STEAM_PUBLISHER_KEY and STEAM_APP_ID and supabase)

def _steam_post(endpoint, fields):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(_MICROTXN_BASE + endpoint, data=data)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

@app.route("/begin_purchase", methods=["POST"])
def begin_purchase():
    if not LEGACY_STEAM_API:
        return _legacy_off()
    if not _purchases_enabled():
        return jsonify({
            "success": False,
            "message": "Satın alma yapılandırılmamış (STEAM_PUBLISHER_KEY / STEAM_APP_ID eksik).",
        }), 503
    try:
        data = _body()
        steam_id = str(data.get("steam_id") or "").strip()
        item_id = int(data.get("item_id") or 0)
        if not steam_id.isdigit():
            return jsonify({"success": False, "message": "Geçersiz steam_id"}), 400
        if item_id not in GEM_PACKS:
            return jsonify({"success": False, "message": "Bilinmeyen paket"}), 400

        gems, desc, amount, currency = GEM_PACKS[item_id]
        orderid = uuid.uuid4().int >> 76        # 52 bitlik benzersiz sipariş no

        db("purchases").insert({
            "orderid": str(orderid),
            "steam_id": steam_id,
            "item_id": item_id,
            "gems": gems,
            "status": "pending",
            "created_at": time.time(),
        }).execute()

        res = _steam_post("/InitTxn/v3/", {
            "key": STEAM_PUBLISHER_KEY,
            "orderid": orderid,
            "steamid": steam_id,
            "appid": STEAM_APP_ID,
            "itemcount": 1,
            "language": "tr",
            "currency": currency,
            "itemid[0]": item_id,
            "qty[0]": 1,
            "amount[0]": amount,
            "description[0]": desc,
        })
        ok = res.get("response", {}).get("result") == "OK"
        return jsonify({
            "success": ok,
            "orderid": str(orderid),
            "message": ("Steam penceresini onayla." if ok
                        else res.get("response", {}).get("error", {}).get("errordesc",
                                                                  "Steam işlemi reddetti.")),
        })
    except Exception as e:
        return _oops(e)

@app.route("/finalize_purchase", methods=["POST"])
def finalize_purchase():
    if not LEGACY_STEAM_API:
        return _legacy_off()
    if not _purchases_enabled():
        return jsonify({"success": False, "message": "Satın alma yapılandırılmamış."}), 503
    try:
        data = _body()
        orderid = str(data.get("orderid") or "").strip()
        if not orderid.isdigit():
            return jsonify({"success": False, "message": "Geçersiz orderid"}), 400

        rows = db("purchases").select("*").eq("orderid", orderid).execute()
        if not rows.data:
            return jsonify({"success": False, "message": "Sipariş bulunamadı"}), 404
        order = rows.data[0]
        if order.get("status") == "completed":
            return jsonify({"success": True, "message": "Sipariş zaten tamamlanmış."})

        res = _steam_post("/FinalizeTxn/v2/", {
            "key": STEAM_PUBLISHER_KEY,
            "orderid": orderid,
            "appid": STEAM_APP_ID,
        })
        if res.get("response", {}).get("result") != "OK":
            db("purchases").update({"status": "failed"}).eq("orderid", orderid).execute()
            return jsonify({"success": False, "message": "Steam ödemeyi onaylamadı."}), 402

        steam_id = order["steam_id"]
        gems = int(order["gems"])
        pl = db("players").select("gems").eq("steam_id", steam_id).execute()
        cur = int(pl.data[0]["gems"]) if pl.data else 0
        db("players").update({"gems": cur + gems}).eq("steam_id", steam_id).execute()
        db("purchases").update({"status": "completed"}).eq("orderid", orderid).execute()
        return jsonify({"success": True, "gems": cur + gems,
                        "message": f"{gems} elmas hesabına eklendi."})
    except Exception as e:
        return _oops(e)

@app.route("/purchase_status", methods=["GET"])
def purchase_status():
    return jsonify({
        "enabled": _purchases_enabled(),
        "sandbox": STEAM_SANDBOX,
        "packs": {str(k): {"gems": v[0], "desc": v[1]} for k, v in GEM_PACKS.items()},
    })

# ---- mağaza: TL ile satın alma ----
# 1) oyun /shop/checkout ile sipariş açar; fiyat sunucunun kataloğundan gelir
# 2) oyun /shop/pay/<sipariş> sayfasını tarayıcıda açar -> iyzico / Shopier
#    (kart bilgisi ne oyuna ne bu sunucuya gelir)
# 3) sağlayıcı /shop/callback/<sağlayıcı>'ya döner, ödeme doğrulanır ve ürün
#    hesaba yazılır (her sipariş bir kez: pending -> paid -> granted)
# 4) oyun /shop/order_status ile bekler
# Anahtarlar ortam değişkeninde, kurulum README_ODEME.md'de.
SHOP_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "").strip().lower()
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
SHOP_FALLBACK_EMAIL = os.environ.get("SHOP_FALLBACK_EMAIL", "").strip()

IYZICO_API_KEY = os.environ.get("IYZICO_API_KEY", "").strip()
IYZICO_SECRET_KEY = os.environ.get("IYZICO_SECRET_KEY", "").strip()
# Canlı: https://api.iyzipay.com Deneme: https://sandbox-api.iyzipay.com
IYZICO_BASE_URL = os.environ.get("IYZICO_BASE_URL", "https://api.iyzipay.com").strip().rstrip("/")

SHOPIER_API_KEY = os.environ.get("SHOPIER_API_KEY", "").strip()
SHOPIER_API_SECRET = os.environ.get("SHOPIER_API_SECRET", "").strip()
SHOPIER_WEBSITE_INDEX = os.environ.get("SHOPIER_WEBSITE_INDEX", "1").strip() or "1"
SHOPIER_PAY_URL = "https://www.shopier.com/ShowProduct/api_pay4.php"

# deneme sağlayıcısı: gerçek para yok, "ÖDE" düğmesiyle sipariş tamamlanır.
# Sadece PAYMENT_PROVIDER=mock iken ve MOCK_PAY_USERS'taki hesaplar için.
# Canlıda kullanma.
MOCK_PAY_USERS = {u.strip().lower() for u in
                  os.environ.get("MOCK_PAY_USERS", "").split(",") if u.strip()}

ORDER_TTL = 6 * 3600              # bu kadar eski "pending" sipariş ödenemez
CUSTOM_PET_PRODUCT = "3100"
CUSTOM_PET_MAX = 24               # bir hesapta en çok kaç özel pet

# katalog - fiyat kuruş cinsinden. Oyundaki item_id'lerle birebir aynı.
SHOP_PRODUCTS = {
    "1001": {"kind": "gems", "gems": 500, "price": 2900, "name": "500 Elmas"},
    "1002": {"kind": "gems", "gems": 1320, "price": 5900, "name": "1.320 Elmas"},
    "1003": {"kind": "gems", "gems": 3120, "price": 11900, "name": "3.120 Elmas"},
    "1004": {"kind": "gems", "gems": 9450, "price": 27900, "name": "9.450 Elmas"},
    # 4 yeni paket (oyundaki GEM_PACKS ile aynı; gems = bonus dahil toplam)
    "1005": {"kind": "gems", "gems": 120, "price": 900, "name": "120 Elmas"},
    "1006": {"kind": "gems", "gems": 6250, "price": 18900, "name": "6.250 Elmas"},
    "1007": {"kind": "gems", "gems": 18200, "price": 49900, "name": "18.200 Elmas"},
    "1008": {"kind": "gems", "gems": 37500, "price": 89900, "name": "37.500 Elmas"},
    "2001": {"kind": "skin", "item": "web_master", "price": 7900, "name": "Ağ Ustası (skin)"},
    "2002": {"kind": "skin", "item": "ash_warrior", "price": 7900, "name": "Kül Savaşçısı (skin)"},
    "2003": {"kind": "skin", "item": "green_titan", "price": 9900, "name": "Yeşil Dev (skin)"},
    "2004": {"kind": "skin", "item": "immortal_merc", "price": 8900, "name": "Ölümsüz Kiralık (skin)"},
    "3001": {"kind": "pet", "item": "pet_cat", "price": 2900, "name": "Yavru Kedi (PET)"},
    "3002": {"kind": "pet", "item": "pet_dog", "price": 2900, "name": "Minik Köpek (PET)"},
    "3003": {"kind": "pet", "item": "pet_bunny", "price": 3900, "name": "Tavşan (PET)"},
    "3004": {"kind": "pet", "item": "pet_slime", "price": 3900, "name": "Slime (PET)"},
    "3005": {"kind": "pet", "item": "pet_ghost", "price": 4900, "name": "Sevimli Hayalet (PET)"},
    "3006": {"kind": "pet", "item": "pet_owl", "price": 4900, "name": "Baykuş (PET)"},
    "3007": {"kind": "pet", "item": "pet_drone", "price": 5900, "name": "Mini Drone (PET)"},
    "3008": {"kind": "pet", "item": "pet_dragon", "price": 7900, "name": "Yavru Ejderha (PET)"},
    # adda kesme işareti yok (ödeme sağlayıcısının ürün adı alanı için)
    CUSTOM_PET_PRODUCT: {"kind": "custom_pet", "price": 15900, "name": "Ozel Tasarim PET"},
}

# özel pet parçaları - oyundaki CUSTOM_PET_PARTS ile birebir aynı olmalı.
# Tasarım veritabanına girmeden önce bu listeyle süzülür.
CUSTOM_PET_PARTS = {
    "body": ("round", "chubby", "tall", "bean", "blob"),
    "eyes": ("round", "big", "sleepy", "happy", "angry", "star", "cyclops", "heart"),
    "mouth": ("smile", "cat", "fangs", "tongue", "o", "none"),
    "ears": ("none", "cat", "dog", "bunny", "bear", "fox", "horns", "antenna"),
    "tail": ("none", "cat", "fox", "puff", "dragon", "devil", "fish"),
    "wings": ("none", "bat", "angel", "fairy", "dragon"),
    "hat": ("none", "crown", "bow", "unicorn", "halo", "tophat", "leaf", "flower"),
    "pattern": ("plain", "belly", "spots", "stripes", "cheeks"),
    "fx": ("none", "sparkle", "hearts", "flames", "snow", "bubbles", "rainbow"),
}
CUSTOM_PET_COLORS = ("col", "col2", "eye")
CUSTOM_PET_NAME_RE = _re.compile(r"[^0-9A-Za-zÇĞİÖŞÜçğıöşü _\-]")


def _clean_pet_design(d):
    """Oyundan gelen pet tasarımını süzer."""
    if not isinstance(d, dict):
        return None
    out = {}
    # tanınmayan parça siparişi düşürmez, o parça varsayılana döner.
    for key, allowed in CUSTOM_PET_PARTS.items():
        v = str(d.get(key, allowed[0]))
        out[key] = v if v in allowed else allowed[0]
    for key, fallback in zip(CUSTOM_PET_COLORS, ([255, 168, 92], [255, 236, 212], [64, 150, 255])):
        c = d.get(key)
        try:
            if not (isinstance(c, (list, tuple)) and len(c) == 3):
                raise ValueError
            out[key] = [max(0, min(255, int(x))) for x in c]
        except (TypeError, ValueError, OverflowError):
            out[key] = list(fallback)
    try:
        size = float(d.get("size", 1.0))
    except (TypeError, ValueError):
        size = 1.0
    if not math.isfinite(size):
        size = 1.0
    out["size"] = round(max(0.8, min(1.3, size)), 2)
    name = CUSTOM_PET_NAME_RE.sub("", str(d.get("name", "") or ""))[:14].strip()
    out["name"] = name or "Petim"
    return out


def _shop_config_problem():
    """Mağaza açılabilir mi?"""
    if not supabase:
        return "Supabase bağlı değil"
    if not SHOP_PROVIDER:
        return "PAYMENT_PROVIDER ayarlanmamış (iyzico / shopier / mock)"
    if not PUBLIC_BASE_URL.startswith("https://") and SHOP_PROVIDER != "mock":
        return "PUBLIC_BASE_URL https:// ile başlamalı (ör. https://kasma-arena-server.onrender.com)"
    if SHOP_PROVIDER == "iyzico":
        if not (IYZICO_API_KEY and IYZICO_SECRET_KEY):
            return "IYZICO_API_KEY / IYZICO_SECRET_KEY eksik"
    elif SHOP_PROVIDER == "shopier":
        if not (SHOPIER_API_KEY and SHOPIER_API_SECRET):
            return "SHOPIER_API_KEY / SHOPIER_API_SECRET eksik"
    elif SHOP_PROVIDER == "mock":
        if not MOCK_PAY_USERS:
            return "mock sağlayıcı için MOCK_PAY_USERS (deneme hesap adları) gerekli"
    else:
        return "bilinmeyen PAYMENT_PROVIDER: " + SHOP_PROVIDER
    return ""


def _shop_enabled():
    return _shop_config_problem() == ""


def _base_url():
    return PUBLIC_BASE_URL or request.host_url.rstrip("/")


def _tl(kurus):
    """15900 -> '159', 2990 -> '29,90' (ekranda gösterim)."""
    k = int(kurus)
    return f"{k // 100}" if k % 100 == 0 else f"{k // 100},{k % 100:02d}"


def _order_row(order_id):
    rows = db("shop_orders").select("*").eq("id", str(order_id)).execute()
    return rows.data[0] if rows.data else None


def _order_payload(order):
    p = order.get("payload")
    if isinstance(p, str):
        try:
            p = json.loads(p)
        except Exception:
            p = {}
    return p if isinstance(p, dict) else {}


@app.route("/shop/catalog", methods=["GET"])
def shop_catalog():
    """Oyun mağazası fiyatları ve mağazanın açık olup olmadığı."""
    return jsonify({
        "enabled": _shop_enabled(),
        "provider": SHOP_PROVIDER if _shop_enabled() else "",
        "currency": "TRY",
        "products": {pid: {"kind": p["kind"], "price": p["price"], "name": p["name"],
                           "price_text": "₺" + _tl(p["price"])}
                     for pid, p in SHOP_PRODUCTS.items()},
        "custom_pet_parts": {k: list(v) for k, v in CUSTOM_PET_PARTS.items()},
    })


@app.route("/shop/checkout", methods=["POST"])
def shop_checkout():
    """Sipariş açar ve ödeme sayfasının adresini döndürür."""
    if not _shop_enabled():
        return jsonify({"success": False, "error": "satın alma şu an kapalı"}), 503
    data = _body()
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "satın almak için giriş yap"}), 401
    if not _rate_ok("shop:" + str(acc["id"])):
        return jsonify({"success": False, "error": "çok sık deneme, biraz bekle"}), 429
    pid = str(data.get("product_id") or "")
    prod = SHOP_PRODUCTS.get(pid)
    if not prod:
        return jsonify({"success": False, "error": "bilinmeyen ürün"}), 400
    if SHOP_PROVIDER == "mock" and str(acc.get("username") or "").lower() not in MOCK_PAY_USERS:
        return jsonify({"success": False, "error": "deneme mağazası bu hesaba kapalı"}), 403
    payload = {"k": secrets.token_urlsafe(18), "ip": _client_ip()}
    prog = _stored_progress(_player_row(acc["id"]))
    # aynı ürün için açık sipariş varsa yenisi açılmaz, aynı ödeme sayfası döner
    # (iki sekmede iki kez ödenmesin)
    try:
        open_rows = (db("shop_orders").select("*")
                     .eq("account_id", acc["id"]).execute().data or [])
    except Exception:
        open_rows = []
    now_ = time.time()
    open_rows = [o for o in open_rows if o.get("status") in ("pending", "paid")
                 and now_ - _num(o.get("created_at"), 0) < ORDER_TTL]
    if prod["kind"] in ("skin", "pet"):
        for o in open_rows:
            if str(o.get("product_id")) == pid and o.get("status") == "pending":
                k_ = _order_payload(o).get("k", "")
                return jsonify({"success": True, "order_id": o["id"], "reused": True,
                                "pay_url": f"{_base_url()}/shop/pay/{o['id']}?k={k_}",
                                "price_text": "₺" + _tl(prod["price"]), "name": prod["name"]})
            if str(o.get("product_id")) == pid and o.get("status") == "paid":
                return jsonify({"success": False, "error": "bu ürünün ödemesi alındı, teslim ediliyor"}), 409
    if prod["kind"] == "skin" and prod["item"] in (prog.get("skins_owned") or []):
        return jsonify({"success": False, "error": "bu skin zaten sende"}), 409
    if prod["kind"] == "pet" and prod["item"] in (prog.get("cosmetics_owned") or []):
        return jsonify({"success": False, "error": "bu PET zaten sende"}), 409
    if prod["kind"] == "custom_pet":
        design = _clean_pet_design(data.get("design"))
        if design is None:
            return jsonify({"success": False, "error": "PET tasarımı geçersiz"}), 400
        waiting = sum(1 for o in open_rows if o.get("kind") == "custom_pet")
        if len(prog.get("custom_pets") or []) + waiting >= CUSTOM_PET_MAX:
            return jsonify({"success": False, "error": "özel PET sınırına ulaştın"}), 409
        payload["design"] = design
    oid = "AB" + time.strftime("%y%m%d") + secrets.token_hex(6).upper()
    try:
        db("shop_orders").insert({
            "id": oid, "account_id": acc["id"], "product_id": pid, "kind": prod["kind"],
            "amount": int(prod["price"]), "currency": "TRY", "status": "pending",
            "provider": SHOP_PROVIDER, "provider_ref": "", "payload": payload,
            "created_at": time.time(), "paid_at": 0, "granted_at": 0, "error": "",
        }).execute()
    except Exception as e:
        return _oops(e, "sipariş açılamadı")
    return jsonify({"success": True, "order_id": oid,
                    "pay_url": f"{_base_url()}/shop/pay/{oid}?k={payload['k']}",
                    "price_text": "₺" + _tl(prod["price"]), "name": prod["name"]})


@app.route("/shop/order_status", methods=["POST"])
def shop_order_status():
    """Oyun siparişi buradan izler."""
    data = _body()
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    if not _rate_ok("shopst:" + str(acc["id"]), max_n=150):
        return jsonify({"success": False, "error": "çok sık soruldu"}), 429
    order = _order_row(str(data.get("order_id") or ""))
    if not order or str(order.get("account_id")) != str(acc["id"]):
        return jsonify({"success": False, "error": "sipariş bulunamadı"}), 404
    st = order.get("status")
    if st == "paid":
        # ödeme doğrulanmış ama teslim yarım kalmış: şimdi tamamla
        _grant_order(order["id"])
        order = _order_row(order["id"]) or order
        st = order.get("status")
    out = {"success": True, "status": st, "order_id": order["id"]}
    if st == "granted":
        out["progress"] = _public_progress(_stored_progress(_player_row(acc["id"])))
    elif st in ("failed", "cancelled"):
        out["reason"] = str(order.get("error") or "")[:120]
    return jsonify(out)


# ---- özel PET'i elmasla almak (hesap başına yalnızca 1 kez) ----
GEM_PET_PRICE = 200_000


@app.route("/shop/custom_pet_gems", methods=["POST"])
def shop_custom_pet_gems():
    """Özel PET'i 200.000 elmasla verir. Her hesap bu hakkı bir kez kullanır;
    elmas sunucudaki defterden düşülür."""
    ctx, err = _reward_ctx()
    if err:
        return err
    acc, data = ctx
    design = _clean_pet_design(data.get("design"))
    if design is None:
        return jsonify({"success": False, "error": "PET tasarımı geçersiz"}), 400
    with _acct_lock(acc["id"]):
        row = _player_row(acc["id"])
        before = _stored_progress(row)
        # oyun güncel ilerlemesini de yolluyor: son koşudan gelen elmas henüz
        # kaydedilmediyse burada sayılsın ("elmasım var ama yetmiyor" diyordu)
        cur = before
        if isinstance(data.get("progress"), dict):
            now_ = time.time()
            allow = _gem_allowance(before, now_)
            cur = _merge_progress(before, data["progress"], gem_cap=allow)
            gained = int(cur["gems_earned"]) - int(before.get("gems_earned", 0) or 0)
            cur["_gem_clock"] = {"t": now_, "left": max(0.0, allow - max(0, gained))}
        if cur.get("gem_pet_bought"):
            return jsonify({"success": False, "error": "elmasla PET hakkını zaten kullandın"}), 409
        if len(cur.get("custom_pets") or []) >= CUSTOM_PET_MAX:
            return jsonify({"success": False, "error": "özel PET sınırına ulaştın"}), 409
        earned = int(cur.get("gems_earned", 0) or 0)
        spent = int(cur.get("gems_spent", 0) or 0)
        if earned - spent < GEM_PET_PRICE:
            return jsonify({"success": False,
                            "error": f"yeterli elmas yok ({max(0, earned - spent)} / {GEM_PET_PRICE})"}), 402
        merged = json.loads(json.dumps(cur))
        merged["gems_spent"] = spent + GEM_PET_PRICE
        merged["gems"] = max(0, earned - merged["gems_spent"])
        pet_id = "pet_custom_g" + secrets.token_hex(4)
        pets = list(cur.get("custom_pets") or [])
        pets.append({"id": pet_id, "design": design, "gems": GEM_PET_PRICE, "at": time.time()})
        merged["custom_pets"] = pets
        lst = list(cur.get("cosmetics_owned") or [])
        if pet_id not in lst:
            lst.append(pet_id)
        merged["cosmetics_owned"] = lst
        merged["gem_pet_bought"] = True
        e = _store_progress(acc["id"], row, before, merged)
        if e is not None:
            return e
        _log_event(acc["id"], "gempet", -GEM_PET_PRICE, int(merged["gems"]), "elmasla özel PET")
    return jsonify({"success": True, "pet_id": pet_id, "progress": _public_progress(merged)})


def _mark_order(order_id, fields, only_status=None):
    """Siparişi koşullu günceller; değişen satır varsa True."""
    q = db("shop_orders").update(fields).eq("id", order_id)
    if only_status is not None:
        q = q.eq("status", only_status)
    res = q.execute()
    return bool(res.data)


def _grant_order(order_id, provider_ref=None):
    """Ödemesi doğrulanmış siparişi hesaba yazar. Her sipariş bir kez (paid -> granted)."""
    order = _order_row(order_id)
    if not order:
        return False, "sipariş yok"
    if order.get("status") == "granted":
        return True, "zaten teslim edildi"
    st0 = order.get("status")
    if st0 in ("pending", "failed", "cancelled"):
        # aynı siparişin başka sekmede reddedilen denemesi siparişi "failed"
        # yapmış olabilir; sonra doğrulanmış başarılı bir ödeme gelirse para
        # çekilmiş demektir - ürün yine teslim edilir.
        f = {"status": "paid", "paid_at": time.time()}
        if provider_ref:
            f["provider_ref"] = str(provider_ref)[:120]
        _mark_order(order_id, f, only_status=st0)
        order = _order_row(order_id) or order
    if order.get("status") != "paid":
        return order.get("status") == "granted", str(order.get("status"))
    if not _mark_order(order_id, {"status": "granted", "granted_at": time.time()},
                       only_status="paid"):
        return True, "başka bir istek teslim etti"
    prod = SHOP_PRODUCTS.get(str(order.get("product_id")))
    acc_id = order["account_id"]
    try:
        with _acct_lock(acc_id):
            row = _player_row(acc_id)
            before = _stored_progress(row)
            merged = json.loads(json.dumps(before))
            kind = prod["kind"]
            note = f"satın alma {order_id} {prod['name']}"
            if kind == "gems":
                merged["gems_earned"] = int(before.get("gems_earned", 0) or 0) + int(prod["gems"])
                merged["gems"] = max(0, merged["gems_earned"] - int(before.get("gems_spent", 0) or 0))
                merged["gems_bought"] = int(before.get("gems_bought", 0) or 0) + int(prod["gems"])
            elif kind == "skin":
                lst = list(before.get("skins_owned") or ["default"])
                if prod["item"] not in lst:
                    lst.append(prod["item"])
                merged["skins_owned"] = lst
            elif kind == "pet":
                lst = list(before.get("cosmetics_owned") or [])
                if prod["item"] not in lst:
                    lst.append(prod["item"])
                merged["cosmetics_owned"] = lst
            elif kind == "custom_pet":
                design = _clean_pet_design(_order_payload(order).get("design"))
                if design is None:
                    raise ValueError("siparişteki PET tasarımı bozuk")
                pet_id = "pet_custom_" + order_id[-8:].lower()
                pets = list(before.get("custom_pets") or [])
                if not any(isinstance(x, dict) and x.get("id") == pet_id for x in pets):
                    pets.append({"id": pet_id, "design": design, "order": order_id,
                                 "at": time.time()})
                # kırpma yok - ödenmiş bir tasarım asla silinmez (sınır
                # siparişte, bekleyen siparişler dahil denetlenir).
                merged["custom_pets"] = pets
                lst = list(before.get("cosmetics_owned") or [])
                if pet_id not in lst:
                    lst.append(pet_id)
                merged["cosmetics_owned"] = lst
            purchases = list(before.get("purchases") or [])
            purchases.append({"order": order_id, "product": order.get("product_id"),
                              "amount": int(order.get("amount") or 0), "at": time.time()})
            merged["purchases"] = purchases[-200:]
            err = _store_progress(acc_id, row, before, merged)
            if err is not None:
                raise RuntimeError("ilerleme yazılamadı")
            _log_event(acc_id, "satin", int(order.get("amount") or 0),
                       int(merged.get("gems", 0) or 0), note)
        return True, "teslim edildi"
    except Exception as e:
        try:
            app.logger.exception("teslim hatası %s", order_id)
        except Exception:
            pass
        _mark_order(order_id, {"status": "paid", "error": str(e)[:200]}, only_status="granted")
        return False, "teslim yarım kaldı, yeniden denenecek"


def _fail_order(order_id, reason):
    _mark_order(order_id, {"status": "failed", "error": str(reason)[:200]}, only_status="pending")


# ---- ödeme sayfası (tarayıcıda açılır) ----
_PAGE_CSS = ("body{font-family:system-ui,Segoe UI,Arial;background:#14121f;color:#eee;"
             "display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}"
             ".k{background:#1f1c30;border:2px solid #6a5cff;border-radius:18px;padding:32px 40px;"
             "max-width:460px;text-align:center}h1{color:#ffd66e;margin:0 0 8px}"
             ".p{font-size:30px;font-weight:700;color:#7fe0ff;margin:14px 0}"
             "button{font-size:18px;font-weight:700;border:0;border-radius:12px;padding:14px 26px;"
             "margin:6px;cursor:pointer}.ok{background:#3fbf6f;color:#fff}.no{background:#444;color:#ddd}"
             "small{color:#9a96b0}")


def _html_page(title, body, code=200):
    html = (f"<!doctype html><html lang='tr'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{title}</title><style>{_PAGE_CSS}</style></head><body><div class='k'>"
            f"{body}</div></body></html>")
    return html, code, {"Content-Type": "text/html; charset=utf-8",
                        "Cache-Control": "no-store", "X-Frame-Options": "DENY"}


def _esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def _result_page(ok, msg):
    if ok:
        return _html_page("Ödeme tamam", "<h1>ÖDEME TAMAM!</h1>"
                          f"<p>{_esc(msg)}</p><p>Oyuna dönebilirsin, ürün hesabına geldi.</p>"
                          "<small>Bu sekmeyi kapatabilirsin.</small>")
    return _html_page("Ödeme tamamlanmadı", "<h1>ÖDEME TAMAMLANMADI</h1>"
                      f"<p>{_esc(msg)}</p><p>Hesabından para çekilmediyse oyundan yeniden "
                      "deneyebilirsin.</p><small>Bu sekmeyi kapatabilirsin.</small>", 200)


@app.route("/shop/pay/<order_id>", methods=["GET"])
def shop_pay(order_id):
    """Oyunun tarayıcıda açtığı sayfa: siparişi sağlayıcıya yönlendirir."""
    if not _rate_ok("pay:" + _client_ip(), max_n=40):
        return _html_page("Bekle", "<h1>Biraz bekle</h1><p>Çok sık deneme.</p>", 429)
    order = _order_row(order_id)
    k = request.args.get("k", "")
    if (not order or not hmac.compare_digest(str(_order_payload(order).get("k", "")), str(k))):
        return _html_page("Bulunamadı", "<h1>Sipariş bulunamadı</h1>", 404)
    if order.get("status") == "granted":
        return _result_page(True, "Bu sipariş zaten tamamlandı.")
    if order.get("status") != "pending":
        return _result_page(False, "Bu sipariş artık ödenemez. Oyundan yeniden başlat.")
    if time.time() - float(order.get("created_at") or 0) > ORDER_TTL:
        _fail_order(order_id, "süresi doldu")
        return _result_page(False, "Siparişin süresi doldu. Oyundan yeniden başlat.")
    prod = SHOP_PRODUCTS.get(str(order.get("product_id")))
    if not prod:
        return _result_page(False, "Ürün artık satılmıyor.")
    acc_rows = db("accounts").select("*").eq("id", order["account_id"]).execute()
    acc = acc_rows.data[0] if acc_rows.data else {}
    try:
        if SHOP_PROVIDER == "iyzico":
            # sayfa yeniden açılınca yeni form açılmaz (iki sekmede iki kez
            # ödeme olmasın); 25 dk içindeki form aynen kullanılır.
            pl = _order_payload(order)
            if pl.get("pay_page") and time.time() - _num(pl.get("pay_page_at"), 0) < 25 * 60:
                return "", 302, {"Location": pl["pay_page"], "Cache-Control": "no-store"}
            return _iyzico_start(order, prod, acc)
        if SHOP_PROVIDER == "shopier":
            return _shopier_start(order, prod, acc)
        if SHOP_PROVIDER == "mock":
            return _mock_start(order, prod, acc)
    except Exception:
        try:
            app.logger.exception("ödeme başlatılamadı %s", order_id)
        except Exception:
            pass
        return _result_page(False, "Ödeme sayfası açılamadı. Biraz sonra yeniden dene.")
    return _result_page(False, "Satın alma şu an kapalı.")


def _buyer_fields(acc):
    uname = str(acc.get("username") or acc.get("name") or "Oyuncu")
    email = str(acc.get("email") or "") or SHOP_FALLBACK_EMAIL or "odeme@example.com"
    return uname, email


# ---- iyzico (Checkout Form) ----
def _iyzico_price(kurus):
    """iyzico fiyat biçimi: 15900 -> '159.0', 2990 -> '29.9', 2995 -> '29.95'."""
    k = int(kurus)
    whole, frac = k // 100, k % 100
    if frac == 0:
        return f"{whole}.0"
    return f"{whole}.{frac:02d}".rstrip("0")


def _iyzico_call(path, body):
    """iyzico IYZWSv2 imzalı istek."""
    rnd = str(int(time.time() * 1000)) + secrets.token_hex(4)
    body_str = json.dumps(body)
    sig = hmac.new(IYZICO_SECRET_KEY.encode("utf-8"), (rnd + path + body_str).encode("utf-8"),
                   hashlib.sha256).hexdigest()
    auth = base64.b64encode(f"apiKey:{IYZICO_API_KEY}&randomKey:{rnd}&signature:{sig}"
                            .encode("utf-8")).decode("ascii")
    req = urllib.request.Request(
        IYZICO_BASE_URL + path, data=body_str.encode("utf-8"),
        headers={"Authorization": "IYZWSv2 " + auth, "x-iyzi-rnd": rnd,
                 "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def _iyzico_start(order, prod, acc):
    uname, email = _buyer_fields(acc)
    price = _iyzico_price(order["amount"])
    ip = _client_ip()
    now_s = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    addr = {"contactName": uname, "city": "Istanbul", "country": "Turkey",
            "address": "Dijital teslimat (oyun içi ürün)", "zipCode": "34000"}
    body = {
        "locale": "tr",
        "conversationId": order["id"],
        "price": price,
        "paidPrice": price,
        "currency": "TRY",
        "basketId": order["id"],
        "paymentGroup": "PRODUCT",
        "callbackUrl": _base_url() + "/shop/callback/iyzico",
        "enabledInstallments": [1],
        "buyer": {
            "id": str(acc.get("id", "")), "name": uname, "surname": "Oyuncu",
            "gsmNumber": "+905000000000", "email": email,
            "identityNumber": "11111111111", "lastLoginDate": now_s,
            "registrationDate": now_s, "registrationAddress": addr["address"],
            "ip": ip, "city": addr["city"], "country": addr["country"],
            "zipCode": addr["zipCode"]},
        "shippingAddress": addr,
        "billingAddress": addr,
        "basketItems": [{"id": str(order["product_id"]), "name": prod["name"],
                         "category1": "Oyun", "category2": "Dijital",
                         "itemType": "VIRTUAL", "price": price}],
    }
    res = _iyzico_call("/payment/iyzipos/checkoutform/initialize/auth/ecom", body)
    if res.get("status") != "success" or not res.get("paymentPageUrl"):
        app.logger.warning("iyzico başlatma reddi %s: %s", order["id"],
                           res.get("errorMessage"))
        return _result_page(False, "Ödeme sağlayıcısı siparişi kabul etmedi.")
    pl = dict(_order_payload(order))
    pl["pay_page"] = str(res["paymentPageUrl"])[:400]
    pl["pay_page_at"] = time.time()
    _mark_order(order["id"], {"provider_ref": str(res.get("token", ""))[:120], "payload": pl},
                only_status="pending")
    return "", 302, {"Location": res["paymentPageUrl"], "Cache-Control": "no-store"}


@app.route("/shop/callback/iyzico", methods=["POST"])
def shop_callback_iyzico():
    """iyzico dönüşü. Gelen veriye güvenmiyoruz, sonucu iyzico'ya soruyoruz."""
    if SHOP_PROVIDER != "iyzico":
        return _result_page(False, "Sağlayıcı kapalı.")
    token = str(request.form.get("token") or request.args.get("token") or "")[:200]
    if not token:
        return _result_page(False, "Eksik ödeme bilgisi.")
    try:
        res = _iyzico_call("/payment/iyzipos/checkoutform/auth/ecom/detail",
                           {"locale": "tr", "token": token})
    except Exception:
        app.logger.exception("iyzico detail")
        return _result_page(False, "Ödeme doğrulanamadı; para çekildiyse ürün birkaç "
                                   "dakika içinde hesabına gelir ya da destekle görüş.")
    oid = str(res.get("basketId") or "")
    order = _order_row(oid) if oid else None
    if not order:
        return _result_page(False, "Sipariş bulunamadı.")
    paid_ok = (res.get("status") == "success" and res.get("paymentStatus") == "SUCCESS"
               and str(res.get("currency", "TRY")) == "TRY"
               and int(res.get("fraudStatus", 1) or 0) == 1)
    try:
        amount_ok = abs(float(res.get("paidPrice") or 0) * 100 - int(order["amount"])) < 1
    except (TypeError, ValueError):
        amount_ok = False
    if not (paid_ok and amount_ok):
        if order.get("status") == "pending":
            _fail_order(oid, res.get("errorMessage") or res.get("paymentStatus") or "ödeme olmadı")
        return _result_page(False, "Ödeme tamamlanmadı.")
    ok, msg = _grant_order(oid, provider_ref=res.get("paymentId") or token)
    return _result_page(ok, SHOP_PRODUCTS.get(str(order["product_id"]), {}).get("name", "") +
                        (" hesabına eklendi." if ok else " - " + msg))


# ---- Shopier ----
def _shopier_start(order, prod, acc):
    uname, email = _buyer_fields(acc)
    total = f"{int(order['amount']) // 100}.{int(order['amount']) % 100:02d}"
    rnd = str(secrets.randbelow(900000) + 100000)
    # verilen random_nr siparişe yazılır; geri dönüşte aynısı olmalı.
    pl = dict(_order_payload(order))
    pl["rnd"] = rnd
    _mark_order(order["id"], {"payload": pl}, only_status="pending")
    currency = "0"                                   # 0 = TL
    data = rnd + order["id"] + total + currency
    sig = base64.b64encode(hmac.new(SHOPIER_API_SECRET.encode("utf-8"), data.encode("utf-8"),
                                    hashlib.sha256).digest()).decode("ascii")
    f = {
        "API_key": SHOPIER_API_KEY, "website_index": SHOPIER_WEBSITE_INDEX,
        "platform_order_id": order["id"], "product_name": prod["name"],
        "product_type": "1",                         # 1 = indirilebilir / sanal ürün
        "buyer_name": uname, "buyer_surname": "Oyuncu", "buyer_email": email,
        "buyer_account_age": "0", "buyer_id_nr": str(acc.get("id", ""))[:40],
        "buyer_phone": "05000000000",
        "billing_address": "Dijital teslimat", "billing_city": "Istanbul",
        "billing_country": "Turkey", "billing_postcode": "34000",
        "shipping_address": "Dijital teslimat", "shipping_city": "Istanbul",
        "shipping_country": "Turkey", "shipping_postcode": "34000",
        "total_order_value": total, "currency": currency, "platform": "0",
        "is_in_frame": "0", "current_language": "0", "modul_version": "1.0.4",
        "random_nr": rnd, "signature": sig,
    }
    inputs = "".join(f"<input type='hidden' name='{_esc(k)}' value='{_esc(v)}'>" for k, v in f.items())
    body = (f"<h1>EvolveArena</h1><p>{_esc(prod['name'])}</p><div class='p'>₺{_tl(order['amount'])}</div>"
            f"<form id='f' method='post' action='{SHOPIER_PAY_URL}'>{inputs}"
            "<button class='ok' type='submit'>GÜVENLİ ÖDEMEYE GEÇ</button></form>"
            "<small>Shopier güvenli ödeme sayfasına yönlendiriliyorsun...</small>"
            "<script>setTimeout(function(){document.getElementById('f').submit()},600)</script>")
    return _html_page("Ödeme", body)


@app.route("/shop/callback/shopier", methods=["POST"])
def shop_callback_shopier():
    """Shopier dönüşü, HMAC-SHA256 imzası kontrol edilir."""
    if SHOP_PROVIDER != "shopier":
        return _result_page(False, "Sağlayıcı kapalı.")
    oid = str(request.form.get("platform_order_id") or "")[:40]
    rnd = str(request.form.get("random_nr") or "")[:20]
    status = str(request.form.get("status") or "").lower()
    sig = str(request.form.get("signature") or "")
    want = base64.b64encode(hmac.new(SHOPIER_API_SECRET.encode("utf-8"), (rnd + oid).encode("utf-8"),
                                     hashlib.sha256).digest()).decode("ascii")
    if not (oid and rnd and sig and hmac.compare_digest(want, sig)):
        return _result_page(False, "Ödeme imzası doğrulanamadı.")
    order = _order_row(oid)
    if not order:
        return _result_page(False, "Sipariş bulunamadı.")
    # Shopier'in imzası sadece random_nr + sipariş no'yu kapsıyor, status'u
    # değil. O yüzden: random_nr bizim verdiğimiz olmalı, başarıda payment_id
    # dolu ve başka siparişte kullanılmamış olmalı, ilk dönüş belirleyici.
    pl = _order_payload(order)
    if not pl.get("rnd") or not hmac.compare_digest(str(pl.get("rnd")), rnd):
        return _result_page(False, "Ödeme imzası doğrulanamadı.")
    if order.get("status") in ("failed", "cancelled"):
        return _result_page(False, "Ödeme tamamlanmadı.")
    if status != "success":
        _fail_order(oid, "shopier: " + status)
        return _result_page(False, "Ödeme tamamlanmadı.")
    pay_id = str(request.form.get("payment_id") or "").strip()[:80]
    if not pay_id:
        _fail_order(oid, "shopier: payment_id yok")
        return _result_page(False, "Ödeme doğrulanamadı.")
    try:
        dup = db("shop_orders").select("id").eq("provider_ref", pay_id).execute().data or []
    except Exception:
        dup = []
    if any(str(d.get("id")) != oid for d in dup):
        return _result_page(False, "Bu ödeme başka bir siparişte kullanıldı.")
    ok, msg = _grant_order(oid, provider_ref=pay_id)
    return _result_page(ok, SHOP_PRODUCTS.get(str(order["product_id"]), {}).get("name", "") +
                        (" hesabına eklendi." if ok else " - " + msg))


# ---- deneme (mock) ----
def _mock_start(order, prod, acc):
    k = _order_payload(order).get("k", "")
    body = (f"<h1>DENEME ÖDEMESİ</h1><p>{_esc(prod['name'])}</p>"
            f"<div class='p'>₺{_tl(order['amount'])}</div>"
            "<p><b>Gerçek para çekilmez.</b> Yalnızca kurulum denemesi içindir.</p>"
            f"<form method='post' action='/shop/mock_result'>"
            f"<input type='hidden' name='order' value='{_esc(order['id'])}'>"
            f"<input type='hidden' name='k' value='{_esc(k)}'>"
            "<button class='ok' name='r' value='ok'>ÖDE (DENEME)</button>"
            "<button class='no' name='r' value='no'>İPTAL</button></form>")
    return _html_page("Deneme ödemesi", body)


@app.route("/shop/mock_result", methods=["POST"])
def shop_mock_result():
    if SHOP_PROVIDER != "mock":
        return _result_page(False, "Deneme sağlayıcısı kapalı.")
    oid = str(request.form.get("order") or "")[:40]
    order = _order_row(oid)
    if not order or not hmac.compare_digest(str(_order_payload(order).get("k", "")),
                                            str(request.form.get("k") or "")):
        return _result_page(False, "Sipariş bulunamadı.")
    if request.form.get("r") != "ok":
        _mark_order(oid, {"status": "cancelled", "error": "deneme: iptal"}, only_status="pending")
        return _result_page(False, "İptal edildi.")
    ok, msg = _grant_order(oid, provider_ref="mock")
    return _result_page(ok, "DENEME: " + SHOP_PRODUCTS.get(str(order["product_id"]), {}).get("name", "") +
                        (" hesabına eklendi." if ok else " - " + msg))


# ---- 2 kişilik (beta): oda + websocket aktarıcı ----
# Oyunu odayı kuranın bilgisayarı yönetir, konuk sadece tuşlarını yollar. Bu
# sunucu ikisinin arasında mesaj taşır, içine bakmaz, hiçbir şey saklamaz.
# Oda kurmak/katılmak giriş ister; websocket oda kodu + uzun biletle açılır;
# mesaj boyu ve hızı sınırlı. Odalar bellekte, 45 sn sessiz kalınca kapanır.
# Render başlatma komutu (tek işçi şart, odalar işçinin belleğinde):
#   gunicorn server:app --worker-class gthread -w 1 --threads 64 --timeout 120
try:
    from flask_sock import Sock as _Sock
    _coop_sock = _Sock(app)
    app.config["SOCK_SERVER_OPTIONS"] = {"ping_interval": 20, "max_message_size": 128 * 1024}
except Exception:            # flask-sock kurulu değil: 2 kişilik kapalı
    _coop_sock = None

COOP_MAX_ROOMS = max(1, min(200, int(os.environ.get("COOP_MAX_ROOMS", "24") or 24)))
COOP_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"     # karışmayan harfler
COOP_CODE_RE = _re.compile(r"^[A-HJ-NP-Z2-9]{6}$")
COOP_KEY_RE = _re.compile(r"^[A-Za-z0-9_\-]{20,64}$")
COOP_IDLE = 45.0              # bu kadar sessizlikte oda kapanır
COOP_RECONNECT = 25.0         # kopan oyuncunun geri dönme payı
COOP_MAX_AGE = 3 * 3600.0
COOP_MSG_MAX = {"host": 96 * 1024, "guest": 4 * 1024}
# konuk saniyede 45-60 girdi yollar (gecikme düşsün diye); sınır buna göre
COOP_BUCKET = {"host": (160.0, 480.0, 768 * 1024.0, 2048 * 1024.0),
               "guest": (150.0, 300.0, 64 * 1024.0, 128 * 1024.0)}
COOP_VER_RE = _re.compile(r"^[0-9][0-9.]{0,9}$")

_COOP_ROOMS = {}
_coop_lock = threading.Lock()
_coop_reaper_started = [False]


class _CoopConn:
    """Bir websocket bağlantısı + gönderme kilidi + jeton kovası."""

    def __init__(self, ws, role):
        self.ws = ws
        self.role = role
        self.lock = threading.Lock()
        r, cap, br, bcap = COOP_BUCKET[role]
        self.rate, self.cap, self.brate, self.bcap = r, cap, br, bcap
        self.tok, self.btok = cap, bcap
        self.t = time.time()
        self.drops = 0
        self.closed = False

    def allow(self, n):
        now = time.time()
        dt = max(0.0, now - self.t)
        self.t = now
        self.tok = min(self.cap, self.tok + dt * self.rate)
        self.btok = min(self.bcap, self.btok + dt * self.brate)
        if self.tok < 1.0 or self.btok < n:
            self.drops += 1
            return False
        self.tok -= 1.0
        self.btok -= n
        self.drops = max(0, self.drops - 1) if self.drops else 0
        return True

    def send(self, data):
        if self.closed:
            return False
        try:
            with self.lock:
                self.ws.send(data)
            return True
        except Exception:
            self.closed = True
            return False

    def close(self):
        self.closed = True
        try:
            self.ws.close()
        except Exception:
            pass


def _coop_name(acc):
    return str(acc.get("username") or acc.get("name") or "Oyuncu")[:14]


def _coop_ctrl(conn, ev, **kw):
    if conn is not None:
        msg = {"t": "srv", "ev": ev}
        msg.update(kw)
        conn.send(json.dumps(msg, ensure_ascii=False))


def _coop_close_room(code, why="closed"):
    """Odayı kapatır (kilit dışında çağrılır)."""
    with _coop_lock:
        room = _COOP_ROOMS.pop(code, None)
    if not room:
        return
    for role in ("host", "guest"):
        c = room.get(role + "_ws")
        if c is not None:
            _coop_ctrl(c, "closed", why=why)
            c.close()


def _coop_reap():
    now = time.time()
    dead = []
    with _coop_lock:
        for code, room in _COOP_ROOMS.items():
            live = room.get("host_ws") is not None or room.get("guest_ws") is not None
            if now - room["created"] > COOP_MAX_AGE:
                dead.append((code, "too_old"))
            elif not live and now - room["last"] > COOP_IDLE:
                dead.append((code, "idle"))
            elif room.get("host_ws") is None and room.get("host_seen") \
                    and now - room.get("host_left", now) > COOP_RECONNECT:
                dead.append((code, "host_left"))
    for code, why in dead:
        _coop_close_room(code, why)


def _coop_reaper():
    while True:
        time.sleep(5.0)
        try:
            _coop_reap()
        except Exception:
            pass


def _coop_start_reaper():
    with _coop_lock:
        if _coop_reaper_started[0]:
            return
        _coop_reaper_started[0] = True
    threading.Thread(target=_coop_reaper, daemon=True).start()


def _coop_ready():
    """2 kişilik bu sunucuda çalışabilir mi?"""
    if _coop_sock is None:
        return "sunucuda 2 kişilik modül (flask-sock) kurulu değil"
    if not request.environ.get("wsgi.multithread"):
        return "sunucu ayarı eksik (gthread başlatma komutu)"
    return ""


def _coop_ver(data):
    v = str(data.get("ver") or "")
    return v if COOP_VER_RE.match(v) else ""


@app.route("/coop/create", methods=["POST"])
def coop_create():
    why = _coop_ready()
    if why:
        return jsonify({"success": False, "error": why}), 503
    data = _body()
    if not _rate_ok("coopci:" + _client_ip(), 30, 300):
        return jsonify({"success": False, "error": "çok sık deneme"}), 429
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "giriş gerekli"}), 401
    aid = str(acc.get("id"))
    if not _rate_ok("coopc:" + aid, 12, 300):
        return jsonify({"success": False, "error": "çok sık oda kuruldu, biraz bekle"}), 429
    ver = _coop_ver(data)
    if not ver:
        return jsonify({"success": False, "error": "geçersiz sürüm"}), 400
    _coop_start_reaper()
    _coop_reap()
    # Hesap başına tek oda: eskisi (kurduğu ya da katıldığı) kapanır.
    with _coop_lock:
        olds = [c for c, r in _COOP_ROOMS.items()
                if r["host_acct"] == aid or r.get("guest_acct") == aid]
    for c in olds:
        _coop_close_room(c, "replaced")
    with _coop_lock:
        if len(_COOP_ROOMS) >= COOP_MAX_ROOMS:
            return jsonify({"success": False, "error": "sunucu dolu, birazdan tekrar dene"}), 503
        for _ in range(50):
            code = "".join(secrets.choice(COOP_CODE_CHARS) for _ in range(6))
            if code not in _COOP_ROOMS:
                break
        else:
            return jsonify({"success": False, "error": "oda kodu üretilemedi"}), 503
        key = secrets.token_urlsafe(24)
        now = time.time()
        _COOP_ROOMS[code] = {
            "code": code, "ver": ver, "created": now, "last": now,
            "host_acct": aid, "host_name": _coop_name(acc), "host_key": key,
            "guest_acct": None, "guest_name": "", "guest_key": None,
            "host_ws": None, "guest_ws": None, "host_seen": False,
        }
    return jsonify({"success": True, "code": code, "key": key, "name": _coop_name(acc)})


@app.route("/coop/join", methods=["POST"])
def coop_join():
    why = _coop_ready()
    if why:
        return jsonify({"success": False, "error": why}), 503
    data = _body()
    if not _rate_ok("coopji:" + _client_ip(), 40, 300):
        return jsonify({"success": False, "error": "çok sık deneme"}), 429
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "giriş gerekli"}), 401
    aid = str(acc.get("id"))
    if not _rate_ok("coopj:" + aid, 20, 300):
        return jsonify({"success": False, "error": "çok sık deneme, biraz bekle"}), 429
    code = str(data.get("code") or "").strip().upper()[:12]
    ver = _coop_ver(data)
    if not COOP_CODE_RE.match(code):
        return jsonify({"success": False, "error": "oda kodu 6 karakter olmalı"}), 400
    _coop_reap()
    with _coop_lock:
        room = _COOP_ROOMS.get(code)
        if room is None:
            return jsonify({"success": False, "error": "oda bulunamadı"}), 404
        if room["host_acct"] == aid:
            return jsonify({"success": False, "error": "kendi odana katılamazsın"}), 400
        if room.get("guest_acct") and room["guest_acct"] != aid:
            return jsonify({"success": False, "error": "oda dolu"}), 409
        if ver != room["ver"]:
            return jsonify({"success": False,
                            "error": "oyun sürümleri farklı (v%s / v%s)" % (room["ver"], ver or "?")}), 409
        if room.get("guest_acct") != aid or not room.get("guest_key"):
            room["guest_key"] = secrets.token_urlsafe(24)
        room["guest_acct"] = aid
        room["guest_name"] = _coop_name(acc)
        room["last"] = time.time()
        key, host_name = room["guest_key"], room["host_name"]
        host_ws = room.get("host_ws")
    _coop_ctrl(host_ws, "joined", name=_coop_name(acc))
    return jsonify({"success": True, "code": code, "key": key, "host": host_name,
                    "name": _coop_name(acc)})


@app.route("/coop/leave", methods=["POST"])
def coop_leave():
    data = _body()
    code = str(data.get("code") or "").strip().upper()[:12]
    key = str(data.get("key") or "")[:80]
    if not (COOP_CODE_RE.match(code) and COOP_KEY_RE.match(key)):
        return jsonify({"success": False}), 400
    with _coop_lock:
        room = _COOP_ROOMS.get(code)
        role = None
        if room:
            if hmac.compare_digest(key, room["host_key"]):
                role = "host"
            elif room.get("guest_key") and hmac.compare_digest(key, room["guest_key"]):
                role = "guest"
        if role == "guest":
            c = room.get("guest_ws")
            room["guest_hist"] = (room.get("guest_acct"), room.get("guest_name") or "", time.time())
            room["guest_ws"] = None
            room["guest_acct"] = None
            room["guest_key"] = None
            room["guest_name"] = ""
            hw = room.get("host_ws")
        else:
            c = hw = None
    if role == "host":
        _coop_close_room(code, "host_left")
    elif role == "guest":
        if c is not None:
            c.close()
        _coop_ctrl(hw, "left")
    return jsonify({"success": bool(role)})


if _coop_sock is not None:
    @_coop_sock.route("/coop/ws")
    def coop_ws(ws):
        origin = request.headers.get("Origin")
        if origin and not _origin_ok(origin):
            return
        code = str(request.args.get("code") or "").strip().upper()[:12]
        key = str(request.args.get("key") or "")[:80]
        if not (COOP_CODE_RE.match(code) and COOP_KEY_RE.match(key)):
            return
        if not _rate_ok("coopw:" + _client_ip(), 60, 300):
            return
        with _coop_lock:
            room = _COOP_ROOMS.get(code)
            role = None
            if room:
                if hmac.compare_digest(key, room["host_key"]):
                    role = "host"
                elif room.get("guest_key") and hmac.compare_digest(key, room["guest_key"]):
                    role = "guest"
            if role is None:
                room = None
            else:
                other = "guest" if role == "host" else "host"
                conn = _CoopConn(ws, role)
                old = room.get(role + "_ws")
                room[role + "_ws"] = conn
                room["last"] = time.time()
                if role == "host":
                    room["host_seen"] = True
                # "you": oyuncunun dış ip'si. İki oyun birbirine doğrudan
                # bağlanmayı denerken (UDP delik açma) yedek aday olur.
                hello = {"role": role, "code": code, "host": room["host_name"],
                         "guest": room.get("guest_name") or "",
                         "peer": room.get(other + "_ws") is not None,
                         "you": _client_ip()}
                peer = room.get(other + "_ws")
        if room is None:
            time.sleep(0.5)                    # bilet deneme hızını keser
            try:
                ws.send(json.dumps({"t": "srv", "ev": "closed", "why": "no_room"}))
            except Exception:
                pass
            return
        if old is not None:
            old.close()
        _coop_ctrl(conn, "hello", **hello)
        _coop_ctrl(peer, "peer_on", role=role)
        try:
            while True:
                data = ws.receive(timeout=COOP_IDLE)
                with _coop_lock:
                    alive = _COOP_ROOMS.get(code) is room and room.get(role + "_ws") is conn
                    if alive:
                        room["last"] = time.time()
                        peer = room.get(other + "_ws")
                if not alive or conn.closed:
                    break
                if data is None:
                    continue                    # sessizlik: odayı bekçi kapatır
                if isinstance(data, str):
                    if data == "ping":
                        _coop_ctrl(conn, "pong")
                    continue                    # oyuncu metin mesajı aktarılmaz
                n = len(data)
                if n > COOP_MSG_MAX[role] or not conn.allow(n):
                    if conn.drops > 400:
                        break                   # sel: bağlantı kapanır
                    continue
                if peer is not None:
                    peer.send(data)
        except Exception:
            pass
        finally:
            with _coop_lock:
                still = _COOP_ROOMS.get(code) is room and room.get(role + "_ws") is conn
                if still:
                    room[role + "_ws"] = None
                    room["last"] = time.time()
                    if role == "host":
                        room["host_left"] = time.time()
                    peer = room.get(other + "_ws")
            conn.closed = True
            if still:
                _coop_ctrl(peer, "peer_off", role=role)


# ---- 2 kişilik dünya sıralaması ----
# Koşu ev sahibinde işlediği için skoru ev sahibi gönderir. Sunucu odanın
# iki hesabını zaten biliyor (kim kurdu, kim katıldı): skor o iki hesaba
# yazılır, istemcinin söylediği adlara bakılmaz. Oda başına aynı koşu bir
# kez yazılır. Skor makullük denetiminden geçmez, gönderildiği gibi yazılır.
COOP_LB_SIZE = 20
COOP_SUBMIT_SLACK = 45.0       # koşu süresi oda ömrüne bu kadar sığmayabilir
COOP_GUEST_GONE = 120.0        # konuk bu kadar önce ayrıldıysa skor yazılmaz
COOP_PUBLIC_FIELDS = ("name_a", "name_b", "score", "kills", "wave", "run_time", "diff",
                      "created_at", "details")


def _coop_pair_key(a, b):
    a, b = str(a), str(b)
    return a + ":" + b if a < b else b + ":" + a


def _clean_coop_player(d, owned):
    """2 kişilik koşudaki bir oyuncunun kartı: tek kişilik kartı + evrimler + kişisel sayılar."""
    if not isinstance(d, dict):
        d = {}
    build, skin = _clean_build(d, owned)
    out = build or {"v": 1, "skin": "default", "w": [], "b": [], "d": [], "st": {}}
    evo = d.get("evo")
    out["evo"] = sorted({str(k) for k in evo if str(k) in BUILD_WEAPONS})[:4] if isinstance(evo, list) else []
    for k, hi in (("score", MAX_SCORE), ("kills", MAX_KILLS), ("lv", 999), ("combo", 100000)):
        out[k] = int(max(0, min(hi, _num(d.get(k), 0))))
    return out


def _owned_skins(account_id):
    try:
        return set(_stored_progress(_player_row(account_id)).get("skins_owned") or [])
    except Exception:
        return set()


@app.route("/coop/submit", methods=["POST"])
def coop_submit():
    if not supabase:
        return jsonify({"success": False, "error": "Supabase bağlantısı yapılandırılmamış!"}), 500
    try:
        data = _body()
        acc = _acct(data)
        if not acc:
            return jsonify({"success": False, "error": "giriş gerekli"}), 401
        aid = str(acc.get("id"))
        if not _rate_ok("coops:" + aid, 10, 600):
            return jsonify({"success": False, "error": "çok sık gönderim"}), 429
        code = str(data.get("code") or "").strip().upper()[:12]
        key = str(data.get("key") or "")[:80]
        run_id = str(data.get("run_id") or "")[:40]
        if not (COOP_CODE_RE.match(code) and COOP_KEY_RE.match(key) and _KEY_RE.match(run_id or "-")):
            return jsonify({"success": False, "error": "geçersiz gönderi"}), 400
        try:
            score = int(data.get("score", 0))
            kills = int(data.get("kills", 0))
            wave = int(data.get("wave", 0))
            run_time = float(data.get("run_time", 0))
        except (TypeError, ValueError, OverflowError):
            return jsonify({"success": False, "error": "geçersiz gönderi"}), 400
        if not math.isfinite(run_time):
            return jsonify({"success": False, "error": "geçersiz gönderi"}), 400
        diff = str(data.get("diff", "normal"))
        if diff not in ("normal", "hard", "nightmare"):
            diff = "normal"
        now = time.time()
        with _coop_lock:
            room = _COOP_ROOMS.get(code)
            if room is None or room["host_acct"] != aid or not hmac.compare_digest(key, room["host_key"]):
                return jsonify({"success": False, "error": "oda bulunamadı"}), 404
            runs = room.setdefault("runs", set())
            if run_id in runs:
                return jsonify({"success": False, "error": "bu koşu zaten gönderildi"}), 409
            gid, gname = room.get("guest_acct"), room.get("guest_name") or ""
            if not gid:
                hist = room.get("guest_hist")
                if hist and now - hist[2] < COOP_GUEST_GONE:
                    gid, gname = hist[0], hist[1]
            # aynı odada art arda koşular: her koşu bir öncekinin gönderisinden
            # sonra başlamış olmalı
            span = now - max(room["created"], room.get("last_submit", 0.0))
            if not gid:
                return jsonify({"success": False, "error": "arkadaşın odada değil"}), 409
            if run_time > now - room["created"] + COOP_SUBMIT_SLACK or run_time > span + COOP_SUBMIT_SLACK:
                return jsonify({"success": False, "error": "koşu süresi tutmuyor"}), 422
            runs.add(run_id)
            room["last_submit"] = now
        # 2 kişilik skorda "en çok şu kadar skor olabilir" makullük denetimi yok:
        # gönderilen skor aynen yazılır. Yalnızca veritabanını bozacak uç
        # değerler (negatif, taşan sayı) sınırlanır; ret yok.
        score = max(0, min(score, MAX_SCORE))
        kills = max(0, min(kills, MAX_KILLS))
        wave = max(1, min(wave, MAX_WAVE))
        run_time = max(0.0, min(run_time, float(MAX_RUN_TIME)))
        gacc = db("accounts").select("id,username").eq("id", gid).execute().data or []
        if not gacc or not acc.get("username") or not gacc[0].get("username"):
            return jsonify({"success": False, "error": "iki oyuncunun da kullanıcı adı olmalı"}), 409
        pls = data.get("players") if isinstance(data.get("players"), list) else []
        pls = (pls + [{}, {}])[:2]
        details = {"v": 1, "a": _clean_coop_player(pls[0], _owned_skins(aid)),
                   "b": _clean_coop_player(pls[1], _owned_skins(gid))}
        if len(json.dumps(details)) > BUILD_RAW_MAX * 2:
            return jsonify({"success": False, "error": "koşu kartı çok büyük"}), 413
        row = {"pair_key": _coop_pair_key(aid, gid), "account_a": aid, "account_b": str(gid),
               "name_a": str(acc.get("username"))[:14], "name_b": str(gacc[0].get("username"))[:14],
               "score": score, "kills": kills, "wave": wave, "run_time": run_time, "diff": diff,
               "details": details, "created_at": now}
        try:
            db("coop_scores").insert(row).execute()
        except Exception as e:
            app.logger.exception("coop_scores insert")
            return jsonify({"success": False, "error": "2 kişilik sıralama henüz kurulmamış "
                                                       "(VERITABANI.sql)"}), 503
        rank = None
        try:
            for i, r in enumerate(_coop_top(COOP_LB_SIZE)):
                if r.get("_pair") == row["pair_key"] and int(r.get("score") or 0) == score:
                    rank = i + 1
                    break
        except Exception:
            pass
        return jsonify({"success": True, "rank": rank})
    except Exception as e:
        return _oops(e)


def _coop_top(n):
    rows = (db("coop_scores").select("*").order("score", desc=True).limit(1000)
            .execute().data or [])
    rows.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
    out, seen = [], set()
    for r in rows:
        pk = r.get("pair_key")
        if pk in seen:
            continue                     # aynı ikili tabloda bir kez (en iyi koşusu)
        seen.add(pk)
        d = r.get("details")
        if isinstance(d, str):
            try:
                d = json.loads(d)
            except Exception:
                d = None
        o = {k: r.get(k) for k in COOP_PUBLIC_FIELDS}
        o["details"] = d
        o["_pair"] = pk
        out.append(o)
        if len(out) >= n:
            break
    return out


@app.route("/coop/scores", methods=["GET"])
def coop_scores():
    if not supabase:
        return jsonify({"error": "Supabase bağlantısı yapılandırılmamış!"}), 500
    try:
        rows = _coop_top(COOP_LB_SIZE)
    except Exception:
        app.logger.exception("coop_scores")
        return jsonify({"scores": [], "setup": False})
    for r in rows:
        r.pop("_pair", None)
    return jsonify({"scores": rows, "setup": True})


# ---- arkadaşlar, mesajlar, davet, profil ----
# Arkadaşlık iki yönlü tek satır: a isteği gönderen, b alan. Kabul edilince
# status = accepted. Mesajlar yalnızca arkadaşlar arasında; davet de bir mesaj
# türü (gövdesi oda kodu). Çevrimiçi bilgisi bellekte (tek süreç), kalıcı
# değil: oyun açıkken her yoklamada tazelenir.
SOCIAL_ONLINE = 75.0           # bu kadar sn içinde yoklayan çevrimiçi sayılır
SOCIAL_MAX_FRIENDS = 100
SOCIAL_MAX_PENDING = 30
SOCIAL_MSG_MAX = 240
SOCIAL_INVITE_TTL = 180.0
SOCIAL_STATUSES = ("menu", "play", "coop", "lobby")
_PRESENCE = {}
_presence_lock = threading.Lock()


def _twice(fn, *a, **k):
    """Geçici bir Supabase/ağ hatasında aynı okumayı bir kez daha dener."""
    try:
        return fn(*a, **k)
    except Exception as e:
        app.logger.warning("tekrar deneniyor %s: %r", getattr(fn, "__name__", "?"), e)
        time.sleep(0.4)
        return fn(*a, **k)


def _social_acc(data):
    acc = _twice(_acct, data)
    if not acc or not acc.get("username"):
        return None
    aid = str(acc.get("id"))
    st = str(data.get("status") or "menu")
    with _presence_lock:
        if len(_PRESENCE) > 50000:
            cut = time.time() - SOCIAL_ONLINE
            for k in [k for k, v in _PRESENCE.items() if v[0] < cut]:
                _PRESENCE.pop(k, None)
        _PRESENCE[aid] = (time.time(), st if st in SOCIAL_STATUSES else "menu")
    _touch_play(acc, data)
    return acc


def _presence(aid):
    with _presence_lock:
        v = _PRESENCE.get(str(aid))
    if not v or time.time() - v[0] > SOCIAL_ONLINE:
        return False, ""
    return True, v[1]


def _social_need_login():
    return jsonify({"success": False, "error": "giriş ve kullanıcı adı gerekli"}), 401


_MISSING_TABLE_HINTS = ("pgrst205", "pgrst200", "42p01", "does not exist",
                        "schema cache", "could not find the table", "could not find a relationship")


def _social_setup_error():
    """Gerçekten tablo eksikse "kurulmamış"; başka her hata geçici sunucu hatasıdır.

    Eskiden her istisna "kurulmamış" diye dönüyor, oyun da arkadaş ekranını
    kapatıyordu. Aktif istisna varsa (except bloğundan çağrılır) ona bakılır.
    """
    e = sys.exc_info()[1]
    if e is not None and not any(h in str(e).lower() for h in _MISSING_TABLE_HINTS):
        ref = uuid.uuid4().hex[:8]
        try:
            app.logger.error("[%s] sosyal geçici hata: %r", ref, e)
        except Exception:
            pass
        return jsonify({"success": False, "ref": ref,
                        "error": "sunucu şu an yanıt vermedi, birazdan tekrar dene"}), 500
    return jsonify({"success": False, "setup": False,
                    "error": "arkadaş sistemi henüz kurulmamış (VERITABANI.sql)"}), 503


def _friend_rows(aid):
    a = db("friends").select("*").eq("a", aid).execute().data or []
    b = db("friends").select("*").eq("b", aid).execute().data or []
    return a + b


def _names_for(ids):
    ids = sorted({str(i) for i in ids if i})
    if not ids:
        return {}
    try:
        rows = db("accounts").select("id,username").in_("id", ids).execute().data or []
    except AttributeError:
        rows = []
        for i in ids:
            rows += db("accounts").select("id,username").eq("id", i).execute().data or []
    return {str(r.get("id")): str(r.get("username") or "") for r in rows}


_NAME_CACHE = {}


def _account_named(name):
    """Kullanıcı adından hesap (kısa önbellekli: ad bir kez seçilir, değişmez)."""
    key = str(name or "").strip().lower()
    hit = _NAME_CACHE.get(key)
    if hit and time.time() - hit[0] < 300.0:
        return dict(hit[1])
    rows = _twice(_accounts_by_username, name, "id,username,created_at")
    if not rows:
        return None
    if len(_NAME_CACHE) > 20000:
        _NAME_CACHE.clear()
    _NAME_CACHE[key] = (time.time(), rows[0])
    return dict(rows[0])


def _are_friends(aid, bid):
    for r in _friend_rows(aid):
        if r.get("status") == "accepted" and {str(r.get("a")), str(r.get("b"))} == {str(aid), str(bid)}:
            return True
    return False


@app.route("/social/sync", methods=["POST"])
def social_sync():
    if not supabase:
        return _social_setup_error()
    data = _body()
    acc = _social_acc(data)
    if not acc:
        return _social_need_login()
    if not _rate_ok("socs:" + str(acc.get("id")), 40, 60):
        return jsonify({"success": False, "error": "çok sık istek"}), 429
    aid = str(acc.get("id"))
    try:
        rows = _friend_rows(aid)
        unread = db("messages").select("id,sender,kind,body,created_at").eq(
            "receiver", aid).is_("read_at", "null").limit(500).execute().data or []
    except Exception:
        app.logger.exception("social_sync")
        return _social_setup_error()
    other = {}
    for r in rows:
        o = str(r.get("b")) if str(r.get("a")) == aid else str(r.get("a"))
        other[o] = r
    names = _names_for(list(other) + [m.get("sender") for m in unread])
    now = time.time()
    friends, incoming, outgoing = [], [], []
    cnt = defaultdict(int)
    invites = []
    for m in unread:
        s = str(m.get("sender"))
        if m.get("kind") == "invite":
            if now - float(m.get("created_at") or 0) < SOCIAL_INVITE_TTL and names.get(s):
                invites.append({"id": m.get("id"), "from": names[s], "code": str(m.get("body") or "")[:6],
                                "at": m.get("created_at")})
        else:
            cnt[s] += 1
    for o, r in other.items():
        nm = names.get(o)
        if not nm:
            continue
        if r.get("status") == "accepted":
            on, st = _presence(o)
            friends.append({"name": nm, "online": on, "status": st, "unread": cnt.get(o, 0)})
        elif str(r.get("a")) == aid:
            outgoing.append(nm)
        else:
            incoming.append(nm)
    friends.sort(key=lambda f: (not f["online"], -f["unread"], f["name"].lower()))
    invites.sort(key=lambda i: -float(i.get("at") or 0))
    return jsonify({"success": True, "friends": friends, "incoming": sorted(incoming),
                    "outgoing": sorted(outgoing), "invites": invites[:3],
                    "unread": sum(f["unread"] for f in friends)})


@app.route("/social/request", methods=["POST"])
def social_request():
    if not supabase:
        return _social_setup_error()
    data = _body()
    acc = _social_acc(data)
    if not acc:
        return _social_need_login()
    aid = str(acc.get("id"))
    if not _rate_ok("socr:" + aid, 20, 3600):
        return jsonify({"success": False, "error": "çok fazla istek gönderdin, biraz bekle"}), 429
    tgt = _account_named(data.get("name"))
    if not tgt:
        return jsonify({"success": False, "error": "bu adda oyuncu yok"}), 404
    tid = str(tgt.get("id"))
    if tid == aid:
        return jsonify({"success": False, "error": "kendini ekleyemezsin"}), 400
    try:
        rows = _friend_rows(aid)
        mine = [r for r in rows if {str(r.get("a")), str(r.get("b"))} == {aid, tid}]
        if mine:
            r = mine[0]
            if r.get("status") == "accepted":
                return jsonify({"success": True, "state": "friends", "name": tgt.get("username")})
            if str(r.get("a")) == tid:
                # o da beni eklemiş: iki taraf da istiyor, arkadaş oldunuz
                db("friends").update({"status": "accepted"}).eq("id", r.get("id")).execute()
                return jsonify({"success": True, "state": "friends", "name": tgt.get("username")})
            return jsonify({"success": True, "state": "pending", "name": tgt.get("username")})
        acc_n = sum(1 for r in rows if r.get("status") == "accepted")
        pend_n = sum(1 for r in rows if r.get("status") != "accepted" and str(r.get("a")) == aid)
        if acc_n >= SOCIAL_MAX_FRIENDS:
            return jsonify({"success": False, "error": "arkadaş listen dolu (%d)" % SOCIAL_MAX_FRIENDS}), 409
        if pend_n >= SOCIAL_MAX_PENDING:
            return jsonify({"success": False, "error": "bekleyen isteğin çok fazla"}), 409
        db("friends").insert({"a": aid, "b": tid, "status": "pending",
                                          "created_at": time.time()}).execute()
    except Exception:
        app.logger.exception("social_request")
        return _social_setup_error()
    return jsonify({"success": True, "state": "pending", "name": tgt.get("username")})


@app.route("/social/respond", methods=["POST"])
def social_respond():
    if not supabase:
        return _social_setup_error()
    data = _body()
    acc = _social_acc(data)
    if not acc:
        return _social_need_login()
    aid = str(acc.get("id"))
    tgt = _account_named(data.get("name"))
    if not tgt:
        return jsonify({"success": False, "error": "bu adda oyuncu yok"}), 404
    tid = str(tgt.get("id"))
    try:
        rows = [r for r in _friend_rows(aid) if str(r.get("a")) == tid and str(r.get("b")) == aid
                and r.get("status") != "accepted"]
        if not rows:
            return jsonify({"success": False, "error": "istek bulunamadı"}), 404
        if data.get("accept"):
            db("friends").update({"status": "accepted"}).eq("id", rows[0].get("id")).execute()
        else:
            db("friends").delete().eq("id", rows[0].get("id")).execute()
    except Exception:
        app.logger.exception("social_respond")
        return _social_setup_error()
    return jsonify({"success": True})


@app.route("/social/remove", methods=["POST"])
def social_remove():
    if not supabase:
        return _social_setup_error()
    data = _body()
    acc = _social_acc(data)
    if not acc:
        return _social_need_login()
    aid = str(acc.get("id"))
    tgt = _account_named(data.get("name"))
    if not tgt:
        return jsonify({"success": False, "error": "bu adda oyuncu yok"}), 404
    tid = str(tgt.get("id"))
    try:
        for r in _friend_rows(aid):
            if {str(r.get("a")), str(r.get("b"))} == {aid, tid}:
                db("friends").delete().eq("id", r.get("id")).execute()
    except Exception:
        app.logger.exception("social_remove")
        return _social_setup_error()
    return jsonify({"success": True})


def _msg_public(m, aid, names):
    return {"id": m.get("id"), "me": str(m.get("sender")) == aid, "text": str(m.get("body") or ""),
            "at": m.get("created_at"), "from": names.get(str(m.get("sender")), "")}


@app.route("/social/messages", methods=["POST"])
def social_messages():
    if not supabase:
        return _social_setup_error()
    data = _body()
    acc = _social_acc(data)
    if not acc:
        return _social_need_login()
    aid = str(acc.get("id"))
    if not _rate_ok("socm:" + aid, 60, 60):
        return jsonify({"success": False, "error": "çok sık istek"}), 429
    tgt = _account_named(data.get("name"))
    if not tgt:
        return jsonify({"success": False, "error": "bu adda oyuncu yok"}), 404
    tid = str(tgt.get("id"))
    after = _int(data.get("after"), 0)
    try:
        if not _are_friends(aid, tid):
            return jsonify({"success": False, "error": "yalnızca arkadaşlarınla yazışabilirsin"}), 403
        q1 = db("messages").select("*").eq("sender", aid).eq("receiver", tid).eq("kind", "text")
        q2 = db("messages").select("*").eq("sender", tid).eq("receiver", aid).eq("kind", "text")
        if after > 0:
            q1, q2 = q1.gt("id", after), q2.gt("id", after)
        rows = (q1.order("id", desc=True).limit(60).execute().data or []) + \
               (q2.order("id", desc=True).limit(60).execute().data or [])
        rows.sort(key=lambda m: int(m.get("id") or 0))
        rows = rows[-60:]
        if any(str(m.get("sender")) == tid and not m.get("read_at") for m in rows):
            db("messages").update({"read_at": time.time()}).eq("receiver", aid).eq(
                "sender", tid).eq("kind", "text").is_("read_at", "null").execute()
    except Exception:
        app.logger.exception("social_messages")
        return _social_setup_error()
    names = {aid: str(acc.get("username")), tid: str(tgt.get("username"))}
    on, st = _presence(tid)
    return jsonify({"success": True, "messages": [_msg_public(m, aid, names) for m in rows],
                    "online": on, "status": st})


@app.route("/social/send", methods=["POST"])
def social_send():
    if not supabase:
        return _social_setup_error()
    data = _body()
    acc = _social_acc(data)
    if not acc:
        return _social_need_login()
    aid = str(acc.get("id"))
    if not _rate_ok("socw:" + aid, 20, 60) or not _rate_ok("socwd:" + aid, 600, 86400):
        return jsonify({"success": False, "error": "çok hızlı yazıyorsun, biraz yavaş"}), 429
    text = " ".join(_clean_text(data.get("text"), SOCIAL_MSG_MAX).split())
    if not text:
        return jsonify({"success": False, "error": "boş mesaj"}), 400
    tgt = _account_named(data.get("name"))
    if not tgt:
        return jsonify({"success": False, "error": "bu adda oyuncu yok"}), 404
    tid = str(tgt.get("id"))
    try:
        if not _are_friends(aid, tid):
            return jsonify({"success": False, "error": "yalnızca arkadaşlarınla yazışabilirsin"}), 403
        res = db("messages").insert({"sender": aid, "receiver": tid, "kind": "text",
                                                 "body": text, "created_at": time.time()}).execute()
    except Exception:
        app.logger.exception("social_send")
        return _social_setup_error()
    m = (res.data or [{}])[0]
    return jsonify({"success": True, "message": _msg_public(m, aid, {aid: str(acc.get("username"))})})


@app.route("/social/invite", methods=["POST"])
def social_invite():
    if not supabase:
        return _social_setup_error()
    data = _body()
    acc = _social_acc(data)
    if not acc:
        return _social_need_login()
    aid = str(acc.get("id"))
    if not _rate_ok("soci:" + aid, 10, 120):
        return jsonify({"success": False, "error": "çok sık davet"}), 429
    code = str(data.get("code") or "").strip().upper()[:12]
    key = str(data.get("key") or "")[:80]
    if not (COOP_CODE_RE.match(code) and COOP_KEY_RE.match(key)):
        return jsonify({"success": False, "error": "önce oda kur"}), 400
    with _coop_lock:
        room = _COOP_ROOMS.get(code)
        ok = room is not None and room["host_acct"] == aid and hmac.compare_digest(key, room["host_key"])
        full = bool(room and room.get("guest_acct"))
    if not ok:
        return jsonify({"success": False, "error": "oda bulunamadı"}), 404
    if full:
        return jsonify({"success": False, "error": "oda dolu"}), 409
    tgt = _account_named(data.get("name"))
    if not tgt:
        return jsonify({"success": False, "error": "bu adda oyuncu yok"}), 404
    tid = str(tgt.get("id"))
    try:
        if not _are_friends(aid, tid):
            return jsonify({"success": False, "error": "yalnızca arkadaşlarını davet edebilirsin"}), 403
        # eski davetleri kapat: aynı kişiye tek geçerli davet
        db("messages").update({"read_at": time.time()}).eq("sender", aid).eq(
            "receiver", tid).eq("kind", "invite").is_("read_at", "null").execute()
        db("messages").insert({"sender": aid, "receiver": tid, "kind": "invite", "body": code,
                                           "created_at": time.time()}).execute()
    except Exception:
        app.logger.exception("social_invite")
        return _social_setup_error()
    on, _st = _presence(tid)
    return jsonify({"success": True, "online": on})


@app.route("/social/invite_seen", methods=["POST"])
def social_invite_seen():
    if not supabase:
        return _social_setup_error()
    data = _body()
    acc = _social_acc(data)
    if not acc:
        return _social_need_login()
    mid = _int(data.get("id"), 0)
    try:
        db("messages").update({"read_at": time.time()}).eq("id", mid).eq(
            "receiver", str(acc.get("id"))).eq("kind", "invite").execute()
    except Exception:
        return _social_setup_error()
    return jsonify({"success": True})


@app.route("/social/profile", methods=["POST"])
def social_profile():
    if not supabase:
        return _social_setup_error()
    data = _body()
    acc = _social_acc(data)
    if not acc:
        return _social_need_login()
    aid = str(acc.get("id"))
    if not _rate_ok("socp:" + aid, 30, 60):
        return jsonify({"success": False, "error": "çok sık istek"}), 429
    tgt = _account_named(data.get("name"))
    if not tgt:
        return jsonify({"success": False, "error": "bu adda oyuncu yok"}), 404
    tid = str(tgt.get("id"))
    row = _player_row(tid) or {}
    prog = _stored_progress(row)
    st = prog.get("stats") if isinstance(prog.get("stats"), dict) else {}

    def _n(v):
        return int(max(0, _num(v, 0)))
    out = {"name": tgt.get("username"), "created_at": tgt.get("created_at"),
           "best_score": _n(row.get("best_score") or st.get("best_score")),
           "best_wave": _n(row.get("best_wave") or st.get("best_wave")),
           "total_kills": _n(row.get("total_kills") or st.get("total_kills")),
           "runs": _n(row.get("runs") or st.get("runs")),
           "bosses": _n(st.get("bosses")), "best_combo": _n(st.get("best_combo")),
           "skins": _n(row.get("skin_count")) or len(prog.get("skins_owned") or []),
           "skin": str(prog.get("equipped_skin") or "default")[:40],
           "style": _clean_profile_style(prog.get("profile_style"), prog.get("profile_owned")),
           "banned": False}
    on, stt = _presence(tid)
    out["online"], out["status"] = on, stt
    rel = "self" if tid == aid else "none"
    try:
        for r in _friend_rows(aid):
            if {str(r.get("a")), str(r.get("b"))} == {aid, tid}:
                rel = "friends" if r.get("status") == "accepted" else (
                    "sent" if str(r.get("a")) == aid else "incoming")
    except Exception:
        pass
    out["rel"] = rel
    top = []
    try:
        rows = (db(WORLD_TABLE).select("score,wave,kills,run_time,diff,created_at").eq(
            "account_id", tgt.get("id")).eq("ranked", True).order("score", desc=True)
            .limit(3).execute().data or [])
        top = [{k: r.get(k) for k in ("score", "wave", "kills", "run_time", "diff")} for r in rows]
    except Exception:
        pass
    out["top"] = top
    coop = []
    try:
        ra = db("coop_scores").select("name_a,name_b,score,wave,account_a").eq(
            "account_a", tid).order("score", desc=True).limit(3).execute().data or []
        rb = db("coop_scores").select("name_a,name_b,score,wave,account_a").eq(
            "account_b", tid).order("score", desc=True).limit(3).execute().data or []
        for r in sorted(ra + rb, key=lambda r: -float(r.get("score") or 0))[:3]:
            mate = r.get("name_b") if str(r.get("account_a")) == tid else r.get("name_a")
            coop.append({"mate": mate, "score": r.get("score"), "wave": r.get("wave")})
    except Exception:
        pass
    out["coop"] = coop
    return jsonify({"success": True, "profile": out})


# ---- sosyal uçlar: yakalanmayan hata "sunucu hatası" yerine düzgün cevap ----
def _social_safe(fn, retry):
    from werkzeug.exceptions import HTTPException

    @functools.wraps(fn)
    def inner(*a, **k):
        for attempt in (0, 1):
            try:
                return fn(*a, **k)
            except HTTPException:
                raise
            except Exception as e:
                if retry and attempt == 0:
                    app.logger.warning("sosyal uç tekrar deneniyor %s: %r", fn.__name__, e)
                    time.sleep(0.4)
                    continue
                app.logger.exception("sosyal uç %s", fn.__name__)
                return _social_setup_error()
    return inner


# yazma uçları (mesaj, istek, davet) çift işlenmesin diye yeniden denenmez
for _name, _retry in (("social_sync", True), ("social_messages", True), ("social_profile", True),
                      ("social_respond", True), ("social_remove", True),
                      ("social_request", False), ("social_send", False),
                      ("social_invite", False), ("social_invite_seen", False)):
    app.view_functions[_name] = _social_safe(app.view_functions[_name], _retry)


# ---- yönetici: dünya sıralaması yasağını kaldır ----
# Yetki, istekteki geçerli oturumun hesabının kullanıcı adından gelir; ad
# Render > Environment > ADMIN_USERNAMES (virgülle) ile değişir.
ADMIN_USERNAMES = {u.strip().lower()
                   for u in (os.environ.get("ADMIN_USERNAMES") or "Yapimci1903").split(",") if u.strip()}


@app.route("/admin/unban", methods=["POST"])
def admin_unban():
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    data = _body()
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    if str(acc.get("username") or "").strip().lower() not in ADMIN_USERNAMES:
        app.logger.warning("yetkisiz /admin/unban denemesi: hesap %s", acc.get("id"))
        return jsonify({"success": False, "error": "bu komut için yetkin yok"}), 403
    if not _rate_ok("adm:" + str(acc.get("id")), 30, 60):
        return jsonify({"success": False, "error": "çok sık istek"}), 429
    tgt = _account_named(data.get("name"))
    if not tgt:
        return jsonify({"success": False, "error": "bu adda oyuncu yok"}), 404
    tid = tgt.get("id")
    try:
        with _acct_lock(tid):
            row = _player_row(tid)
            prog = _stored_progress(row)
            was = bool(prog.get("board_banned"))
            prog["board_banned"] = False
            prog["ban_reasons"] = []
            # Oyuncunun kendi kaydındaki yerel yasak da kalksın diye artan damga:
            # oyun bu damgayı profilinde ilk kez görünce yerel yasağı siler.
            prog["ban_lift"] = max(int(time.time()), _int(prog.get("ban_lift"), 0) + 1)
            payload = {
                "account_id": tid,
                "data": {k: v for k, v in prog.items()
                         if k not in ("gems", "gems_earned", "gems_spent")},
                "updated_at": time.time(),
            }
            if row:
                db("player_data").update(payload).eq("account_id", tid).execute()
            else:
                payload.update(gems=0, gems_earned=0, gems_spent=0)
                db("player_data").insert(payload).execute()
        _log_event(tid, "yasak", 0, 0, ("kaldırıldı: " + str(acc.get("username")))[:120])
    except Exception as e:
        return _oops(e, "ban kaldırılamadı")
    return jsonify({"success": True, "name": tgt.get("username"), "was_banned": was})


# ---- yönetici: bir oyuncuya elmas ver ----
GEM_TOTAL_MAX = 2_000_000_000        # veritabanı sütunu taşmasın (int4 ~2,147 milyar)


@app.route("/admin/give_gems", methods=["POST"])
def admin_give_gems():
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    data = _body()
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    if str(acc.get("username") or "").strip().lower() not in ADMIN_USERNAMES:
        app.logger.warning("yetkisiz /admin/give_gems denemesi: hesap %s", acc.get("id"))
        return jsonify({"success": False, "error": "bu komut için yetkin yok"}), 403
    if not _rate_ok("adm:" + str(acc.get("id")), 30, 60):
        return jsonify({"success": False, "error": "çok sık istek"}), 429
    amount = _int(data.get("amount"), 0)
    if amount < 1:
        return jsonify({"success": False, "error": "miktar 1 ya da daha büyük olmalı"}), 400
    tgt = _account_named(data.get("name"))
    if not tgt:
        return jsonify({"success": False, "error": "bu adda oyuncu yok"}), 404
    tid = tgt.get("id")
    try:
        with _acct_lock(tid):
            row = _player_row(tid)
            prog = _stored_progress(row)
            earned = max(0, _int(prog.get("gems_earned"), 0))
            spent = min(max(0, _int(prog.get("gems_spent"), 0)), earned)
            add = min(amount, GEM_TOTAL_MAX - earned)
            if add < 1:
                return jsonify({"success": False, "error": "bu oyuncunun elmas sınırı dolu"}), 409
            earned += add
            total = earned - spent
            rw_ = dict(prog.get("rewards") or {})
            rw_["srv_earned"] = _int(rw_.get("srv_earned"), 0) + add
            prog["rewards"] = rw_
            payload = {
                "account_id": tid,
                "gems": total, "gems_earned": earned, "gems_spent": spent,
                "data": {k: v for k, v in prog.items()
                         if k not in ("gems", "gems_earned", "gems_spent")},
                "updated_at": time.time(),
            }
            if row:
                db("player_data").update(payload).eq("account_id", tid).execute()
            else:
                db("player_data").insert(payload).execute()
        _log_event(tid, "gem", add, total, ("yönetici: " + str(acc.get("username")))[:120])
    except Exception as e:
        return _oops(e, "elmas verilemedi")
    return jsonify({"success": True, "name": tgt.get("username"), "added": add, "total": total})


# =====================================================================
# ---- web sitesi: şans çarkı + kazı kazan ----
# =====================================================================
# Akış:
#   1) Oyun: /site/link (oyun oturumuyla) -> tek kullanımlık, 10 dakikalık kod.
#      Oyun siteyi https://volvearena.shop/#k=KOD ile açar (# kısmı sunucuya,
#      günlüklere ve reklam ağlarına gitmez).
#   2) Site: /site/exchange {code} -> "site geçişi" (2 saatlik, imzalı jeton).
#      Ya da /site/login {username, password} (oyundaki girişle aynı sınırlar).
#      Site geçişi oyun oturumu DEĞİLDİR: oyunu oturumdan atmaz, şifre/e-posta
#      değiştiremez; yalnızca /site/ uçlarında geçer. Şifre değişince geçersiz.
#   3) Çark: /site/wheel/ad (sponsor bağlantısına tıklandı, sayaç başlar) ->
#      en az SITE_WHEEL_WAIT saniye sonra /site/wheel/spin. Sonucu SUNUCU seçer
#      ve hesaba burada yazar; site yalnızca çarkı o dilime döndürür.
#   4) Kazı kazan: /site/scratch/buy {tier}. Bedel düşülür ve ödül AYNI ANDA,
#      satın alırken sunucuda belirlenip hesaba yazılır. Kartın altında ne
#      olduğu sayfaya ancak satın alma bittikten sonra gelir: sağ tık > incele
#      ile bakan biri yalnızca zaten kesinleşmiş sonucu görür, değiştiremez.
#      Kod yok, kodu tahmin etme / paylaşma / iki kez bozdurma derdi yok.
# Sitede kazanılan / harcanan elmas rewards.srv_earned / srv_spent sayaçlarına
# da yazılır (bkz. _merge_progress): oyun eski bir kayıtla gelse bile ne
# kazanç silinir ne harcama geri gelir.
SITE_SECRET = (os.environ.get("SITE_SECRET")
               or hashlib.sha256(("evolve-site-v1|" + (SUPABASE_KEY or secrets.token_hex(32))
                                  + "|" + (GOOGLE_CLIENT_SECRET or "")).encode()).hexdigest())
SITE_PASS_TTL = 2 * 3600
SITE_CODE_TTL = 10 * 60
SITE_WHEEL_WAIT = 15.0
SITE_WHEEL_MAX_WAIT = 30 * 60.0
SITE_WHEEL_GAP = 8.0                 # iki çevirme arası en az
SITE_AD_URL = "https://ardance.org/4/8eb87fad3ff308b09ec866979c2bcfe7"
_site_codes = {}                     # kod özeti -> (hesap, bitiş)
_site_acc_cache = {}                 # hesap id -> (zaman, satır)
SITE_ACC_CACHE_T = 20.0
_site_lock = threading.Lock()
_site_rng = secrets.SystemRandom()

# kazı kazan: bedel -> (ödül, yüzde) tablosu. Beklenen getiri bedelin %75-80'i
# (elmas ekonomisi şişmesin), 1 milyon "çok zor".
SCRATCH_TIERS = {
    "5k": (5000, ((0, 30.0), (250, 18.0), (1000, 13.0), (2500, 13.0), (5000, 12.5), (10000, 10.0),
                  (25000, 2.6), (100000, 0.88), (1000000, 0.02))),
    "10k": (10000, ((0, 30.3), (500, 17.0), (2500, 14.0), (5000, 13.0), (10000, 12.0), (20000, 9.0),
                    (50000, 3.2), (100000, 1.1), (250000, 0.36), (1000000, 0.04))),
    "50k": (50000, ((0, 30.0), (2500, 17.0), (10000, 14.0), (25000, 13.0), (50000, 12.5), (100000, 9.0),
                    (250000, 3.0), (500000, 1.2), (1000000, 0.3))),
}
SCRATCH_DAILY = 150                  # hesap başına günde en çok kart
SCRATCH_PER_MIN = 20


def _b64u(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _pw_tag(acc):
    """Şifre değişince eski site geçişleri düşsün diye şifre özetinden kısa iz."""
    return hashlib.sha256(("pw|" + str((acc or {}).get("password_hash") or "")).encode()).hexdigest()[:10]


def _site_sign(msg):
    return _b64u(hmac.new(SITE_SECRET.encode(), msg.encode(), hashlib.sha256).digest())


def _site_make_pass(acc):
    exp = int(time.time() + SITE_PASS_TTL)
    msg = "s1.%s.%d.%s.%s" % (int(acc["id"]), exp, _pw_tag(acc), secrets.token_hex(6))
    return msg + "." + _site_sign(msg)


def _site_acc(data):
    """Site geçişinden hesabı çözer (yoksa None)."""
    tok = str((data or {}).get("pass") or "")
    if not tok or len(tok) > 200 or not supabase:
        return None
    parts = tok.split(".")
    if len(parts) != 6 or parts[0] != "s1":
        return None
    msg = ".".join(parts[:5])
    if not hmac.compare_digest(_site_sign(msg), parts[5]):
        return None
    try:
        aid, exp = int(parts[1]), int(parts[2])
    except ValueError:
        return None
    if exp < time.time():
        return None
    # oyun masası saniyede bir sorulur: hesap satırı kısa süre önbellekte
    now = time.time()
    with _site_lock:
        hit = _site_acc_cache.get(aid)
    if hit and now - hit[0] < SITE_ACC_CACHE_T:
        acc = hit[1]
    else:
        rows = db("accounts").select("*").eq("id", aid).execute()
        if not rows.data:
            return None
        acc = rows.data[0]
        with _site_lock:
            if len(_site_acc_cache) > 5000:
                _site_acc_cache.clear()
            _site_acc_cache[aid] = (now, acc)
    if not hmac.compare_digest(_pw_tag(acc), parts[3]):
        return None
    return dict(acc)


def _site_ctx(poll=False):
    if not _accounts_enabled():
        return None, None, (jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503)
    if not _rate_ok(("site:pip:" if poll else "site:ip:") + _client_ip(), 400 if poll else 120, 60):
        return None, None, (jsonify({"success": False, "error": "çok sık istek, biraz bekle"}), 429)
    data = _body()
    acc = _site_acc(data)
    if not acc:
        return None, None, (jsonify({"success": False, "error": "oturum süresi doldu, oyundan yeniden aç ya da giriş yap",
                                     "relogin": True}), 401)
    if not _rate_ok(("site:p:" if poll else "site:a:") + str(acc["id"]), 200 if poll else 90, 60):
        return None, None, (jsonify({"success": False, "error": "çok sık istek, biraz bekle"}), 429)
    return acc, data, None


def _site_name(acc):
    return str(acc.get("username") or acc.get("name") or "oyuncu")[:20]


def _site_state(acc, prog):
    rw = dict(prog.get("rewards") or {})
    now = time.time()
    used = _wheel_used_today(rw)
    ad_at = _num(rw.get("swheel_at"), 0)
    pending = bool(rw.get("swheel_nonce")) and 0 < now - ad_at < SITE_WHEEL_MAX_WAIT
    scr_used = _int(rw.get("scr_count"), 0) if rw.get("scr_day") == _server_day() else 0
    return {
        "name": _site_name(acc),
        "gems": int(prog.get("gems", 0) or 0),
        "wheel": {"left": max(0, WHEEL_DAILY - used), "daily": WHEEL_DAILY, "wait": SITE_WHEEL_WAIT,
                  "pending": pending, "rest": max(0.0, SITE_WHEEL_WAIT - (now - ad_at)) if pending else None,
                  "prizes": [[p_, w_] for p_, w_ in WHEEL_PRIZES], "dupe_gems": WHEEL_DUPE_GEMS},
        "scratch": {"left": max(0, SCRATCH_DAILY - scr_used), "daily": SCRATCH_DAILY,
                    "tiers": {k: {"cost": c, "table": [[a, w] for a, w in t]} for k, (c, t) in SCRATCH_TIERS.items()}},
        "ad_url": SITE_AD_URL,
        "room": _my_room_brief(acc.get("id")),
    }


def _my_room_brief(aid):
    try:
        with _games_lock:
            r = _room_of(aid)
            return {"id": r["id"], "kind": r["kind"]} if r else None
    except NameError:
        return None


@app.route("/site/link", methods=["POST"])
def site_link():
    """Oyun: siteyi bu hesapla açmak için tek kullanımlık kod."""
    ctx, err = _reward_ctx()
    if err:
        return err
    acc, _data = ctx
    code = secrets.token_urlsafe(18)
    now = time.time()
    with _site_lock:
        if len(_site_codes) > 20000:
            for k in [k for k, v in _site_codes.items() if v[1] < now]:
                _site_codes.pop(k, None)
            if len(_site_codes) > 20000:
                _site_codes.clear()
        _site_codes[_token_hash(code)] = (int(acc["id"]), now + SITE_CODE_TTL)
    return jsonify({"success": True, "code": code, "ttl": SITE_CODE_TTL})


@app.route("/site/exchange", methods=["POST"])
def site_exchange():
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    if not _rate_ok("site:x:" + _client_ip(), 20, 300):
        return jsonify({"success": False, "error": "çok fazla deneme"}), 429
    code = str(_body().get("code") or "")[:64]
    if not code:
        return jsonify({"success": False, "error": "kod yok"}), 400
    with _site_lock:
        hit = _site_codes.pop(_token_hash(code), None)      # tek kullanımlık
    if not hit or hit[1] < time.time():
        return jsonify({"success": False, "error": "bağlantının süresi dolmuş, oyundan yeniden aç"}), 401
    rows = db("accounts").select("*").eq("id", hit[0]).execute()
    if not rows.data:
        return jsonify({"success": False, "error": "hesap bulunamadı"}), 404
    acc = rows.data[0]
    prog = _stored_progress(_player_row(acc["id"]))
    return jsonify({"success": True, "pass": _site_make_pass(acc), "ttl": SITE_PASS_TTL,
                    "state": _site_state(acc, prog)})


@app.route("/site/login", methods=["POST"])
def site_login():
    """Sitede kullanıcı adı / e-posta + şifre ile giriş (oyun oturumunu kapatmaz)."""
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    if not _rate_ok("auth:" + _client_ip()):
        return jsonify({"success": False, "error": "çok fazla deneme"}), 429
    data = _body()
    who = str(data.get("username") or "").strip()[:254]
    password = str(data.get("password", ""))[:256]
    if _login_locked(who.lower()):
        return jsonify({"success": False, "error": "çok fazla hatalı deneme, biraz bekle"}), 429
    try:
        if "@" in who:
            rows = db("accounts").select("*").eq("email", who.lower()).execute()
            acc = rows.data[0] if rows.data else None
        else:
            found = _accounts_by_username(who) if who else []
            acc = found[0] if found else None
        if not acc or not acc.get("password_hash"):
            _verify_password(password, _DUMMY_HASH)
            _login_failed(who.lower())
            return jsonify({"success": False, "error": "kullanıcı adı ya da şifre hatalı "
                            "(Google ile giriyorsan siteyi oyundan aç)"}), 401
        if not _verify_password(password, acc["password_hash"]):
            _login_failed(who.lower())
            return jsonify({"success": False, "error": "kullanıcı adı ya da şifre hatalı"}), 401
        _login_ok(who.lower())
        prog = _stored_progress(_player_row(acc["id"]))
        return jsonify({"success": True, "pass": _site_make_pass(acc), "ttl": SITE_PASS_TTL,
                        "state": _site_state(acc, prog)})
    except Exception as e:
        return _oops(e)


@app.route("/site/me", methods=["POST"])
def site_me():
    acc, _data, err = _site_ctx()
    if err:
        return err
    _game_reaper_start()
    try:
        _escrow_reconcile(acc["id"])
    except Exception:
        app.logger.exception("emanet denetlenemedi")
    prog = _stored_progress(_player_row(acc["id"]))
    return jsonify({"success": True, "state": _site_state(acc, prog)})


@app.route("/site/wheel/ad", methods=["POST"])
def site_wheel_ad():
    """Sponsor bağlantısına tıklandı: çark bileti + bekleme sayacı başlar."""
    acc, _data, err = _site_ctx()
    if err:
        return err
    with _acct_lock(acc["id"]):
        row, before, rw = _reward_row(acc["id"])
        if _wheel_used_today(rw) >= WHEEL_DAILY:
            return jsonify({"success": False, "error": "bugünkü çark hakkın bitti, yarın yenilenir"}), 429
        now = time.time()
        if now - _num(rw.get("wheel_last"), 0) < SITE_WHEEL_GAP:
            return jsonify({"success": False, "error": "biraz bekle"}), 429
        nonce = secrets.token_hex(12)
        rw["swheel_nonce"] = nonce
        rw["swheel_at"] = now
        merged = dict(before)
        merged["rewards"] = rw
        e = _store_progress(acc["id"], row, before, merged)
        if e is not None:
            return e
    return jsonify({"success": True, "ticket": nonce, "wait": SITE_WHEEL_WAIT, "ad_url": SITE_AD_URL})


@app.route("/site/wheel/spin", methods=["POST"])
def site_wheel_spin():
    acc, data, err = _site_ctx()
    if err:
        return err
    with _acct_lock(acc["id"]):
        row, before, rw = _reward_row(acc["id"])
        ticket = str(data.get("ticket") or "")[:64]
        if not ticket or not hmac.compare_digest(ticket, str(rw.get("swheel_nonce") or "")):
            return jsonify({"success": False, "error": "önce sponsor bağlantısına tıkla"}), 403
        el = time.time() - _num(rw.get("swheel_at"), 0)
        if el < SITE_WHEEL_WAIT - 0.5:
            return jsonify({"success": False, "error": "%d saniye daha bekle" % int(math.ceil(SITE_WHEEL_WAIT - el)),
                            "rest": max(0.0, SITE_WHEEL_WAIT - el)}), 403
        if el > SITE_WHEEL_MAX_WAIT:
            rw.pop("swheel_nonce", None)
            return jsonify({"success": False, "error": "süre doldu, sponsora yeniden tıkla"}), 403
        if _wheel_used_today(rw) >= WHEEL_DAILY:
            return jsonify({"success": False, "error": "bugünkü çark hakkın bitti"}), 429
        prize = _wheel_pick()
        merged, gems, dupe = _wheel_apply(before, prize)
        rw["wheel_count"] = _wheel_used_today(rw) + 1
        rw["wheel_day"] = _server_day()
        rw["wheel_last"] = time.time()
        rw["wheel_total"] = int(rw.get("wheel_total", 0) or 0) + 1
        rw["wheel_site_last"] = prize
        if gems:
            rw["srv_earned"] = _int(rw.get("srv_earned"), 0) + gems
        rw.pop("swheel_nonce", None)         # bilet bir kez kullanılır
        rw.pop("swheel_at", None)
        merged["rewards"] = rw
        e = _store_progress(acc["id"], row, before, merged)
        if e is not None:
            return e
        _log_event(acc["id"], "cark", gems, int(merged.get("gems", 0) or 0),
                   ("site çarkı: " + prize + (" (zaten vardı)" if dupe else ""))[:120])
    return jsonify({"success": True, "prize": prize, "gems": gems, "dupe": dupe,
                    "state": _site_state(acc, merged)})


def _scratch_pick(table):
    total = sum(w for _a, w in table)
    x = _site_rng.uniform(0.0, total)
    for amt, w in table:
        x -= w
        if x <= 0:
            return amt
    return table[0][0]


def _scratch_cells(prize, table):
    """Kartın 9 hücresi (yalnız görüntü): kazanan miktar 3 kez, gerisi en çok
    2'şer kez. Ödül yoksa hiçbir miktar 3 kez yazmaz."""
    amounts = [a for a, _w in table if a > 0]
    cells = []
    if prize > 0:
        cells = [prize] * 3
        pool = [a for a in amounts if a != prize]
    else:
        pool = list(amounts)
    while len(cells) < 9:
        a = _site_rng.choice(pool)
        if cells.count(a) < 2:
            cells.append(a)
    _site_rng.shuffle(cells)
    return cells


@app.route("/site/scratch/buy", methods=["POST"])
def site_scratch_buy():
    acc, data, err = _site_ctx()
    if err:
        return err
    tier = str(data.get("tier") or "")
    if tier not in SCRATCH_TIERS:
        return jsonify({"success": False, "error": "bilinmeyen kart"}), 400
    if not _rate_ok("scr:" + str(acc["id"]), SCRATCH_PER_MIN, 60):
        return jsonify({"success": False, "error": "çok hızlı, biraz yavaşla"}), 429
    cost, table = SCRATCH_TIERS[tier]
    with _acct_lock(acc["id"]):
        row, before, rw = _reward_row(acc["id"])
        today = _server_day()
        used = _int(rw.get("scr_count"), 0) if rw.get("scr_day") == today else 0
        if used >= SCRATCH_DAILY:
            return jsonify({"success": False, "error": "bugünkü kazı kazan sınırına ulaştın"}), 429
        earned = max(0, _int(before.get("gems_earned"), 0))
        spent = min(max(0, _int(before.get("gems_spent"), 0)), earned)
        if earned - spent < cost:
            return jsonify({"success": False, "error": "yeterli elmasın yok"}), 409
        prize = _scratch_pick(table)
        win = min(prize, max(0, GEM_TOTAL_MAX - earned))
        merged = dict(before)
        merged["gems_spent"] = spent + cost
        merged["gems_earned"] = earned + win
        merged["gems"] = max(0, merged["gems_earned"] - merged["gems_spent"])
        rw["scr_day"] = today
        rw["scr_count"] = used + 1
        rw["scr_total"] = _int(rw.get("scr_total"), 0) + 1
        rw["scr_won"] = _int(rw.get("scr_won"), 0) + win
        rw["scr_best"] = max(_int(rw.get("scr_best"), 0), win)
        rw["srv_spent"] = _int(rw.get("srv_spent"), 0) + cost
        rw["srv_earned"] = _int(rw.get("srv_earned"), 0) + win
        merged["rewards"] = rw
        e = _store_progress(acc["id"], row, before, merged)
        if e is not None:
            return e
        _log_event(acc["id"], "kazi", win - cost, int(merged["gems"]),
                   ("kazı kazan %s: %d" % (tier, win))[:120])
    return jsonify({"success": True, "tier": tier, "cost": cost, "prize": win,
                    "cells": _scratch_cells(win, table), "state": _site_state(acc, merged)})


# =====================================================================
# ---- site oyun salonu: yazı tura, blackjack, pişti (oyuncular arası) + rulet ----
# =====================================================================
# Güvenlik ilkeleri:
#  - Bütün kartlar, desteler ve sonuçlar YALNIZ sunucuda tutulur ve
#    secrets.SystemRandom ile karılır. Tarayıcıya bir oyuncunun görmesi gereken
#    dışında hiçbir şey gitmez (deste, rakibin kapalı kartı, masadaki kapalı
#    kartlar asla gönderilmez). F12 ile bakan biri gelecek kartı göremez.
#  - Yatırılan elmas odaya girerken hesaptan düşülür ve "emanet"e (rewards.
#    escrow) yazılır. Oyun bitince kazanana pot - %5 kesinti ödenir; berabere
#    kalınırsa herkesin yatırdığı aynen geri döner. Emanet ödemesi tek
#    seferliktir (iki kez ödenemez). Sunucu yeniden başlarsa ya da oda
#    kaybolursa emanetteki elmas oyuncuya kendiliğinden geri verilir.
#  - Her hamle sunucuda doğrulanır (sıra, el, geçerli kart). Süresi dolan
#    oyuncu adına sunucu oynar (blackjack: dur, pişti: rastgele kart).
#  - Aynı IP'den iki hesap aynı masaya oturamaz (kendi kendine elmas aktarma).
# Kilit sırası her zaman: _games_lock -> _acct_lock (kilitlenme olmasın).
GAME_STAKES = (1000, 5000, 10000, 25000, 50000, 100000)
GAME_RAKE = 0.05
GAME_KINDS = {"coin": (2, 2), "bj": (2, 2), "pisti": (2, 4)}
GAME_NAMES = {"coin": "yazı tura", "bj": "blackjack", "pisti": "pişti"}
GAME_TURN_T = {"bj": 30.0, "pisti": 25.0}
GAME_WAIT_T = 15 * 60.0          # dolmayan masa bu kadar sonra kapanır (iade)
GAME_DONE_KEEP = 90.0            # biten masa sonucu bu kadar görünür
GAME_LEFT_T = 1.5                # masadan kalkan oyuncunun sırası hemen oynanır
ROULETTE_MAX = 100000            # tek çevirmede en çok toplam bahis
ROULETTE_MIN = 100
ROULETTE_DAILY = 400
_games = {}
_games_lock = threading.RLock()
_game_rng = secrets.SystemRandom()
SUITS = ("S", "H", "D", "C")      # maça, kupa, karo, sinek
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
ROUL_RED = frozenset((1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36))


def _new_deck():
    d = [r + s for s in SUITS for r in RANKS]
    _game_rng.shuffle(d)
    return d


def _ip_tag():
    return hashlib.sha256(("ip|" + _CONTACT_SALT + "|" + (_client_ip() or "")).encode()).hexdigest()[:16]


# ---- emanet (escrow) ----
def _escrow_take(aid, rid, amount, note):
    """Bedeli hesaptan düşüp emanete yazar. Döner: None (tamam) ya da hata metni."""
    with _acct_lock(aid):
        row, before, rw = _reward_row(aid)
        earned = max(0, _int(before.get("gems_earned"), 0))
        spent = min(max(0, _int(before.get("gems_spent"), 0)), earned)
        if earned - spent < amount:
            return "yeterli elmasın yok"
        esc = dict(rw.get("escrow") or {})
        if rid in esc:
            return "zaten bu masadasın"
        esc[rid] = int(amount)
        rw["escrow"] = esc
        rw["srv_spent"] = _int(rw.get("srv_spent"), 0) + int(amount)
        merged = dict(before)
        merged["gems_spent"] = spent + int(amount)
        merged["gems_earned"] = earned
        merged["gems"] = max(0, earned - merged["gems_spent"])
        merged["rewards"] = rw
        if _store_progress(aid, row, before, merged) is not None:
            return "elmas düşülemedi, tekrar dene"
    _log_event(aid, "oyun", -int(amount), int(merged["gems"]), ("%s: masaya oturdu" % note)[:120])
    return None


def _escrow_pay(aid, rid, payout, note):
    """Emaneti kapatır ve payout'u hesaba yazar (0 = kaybetti). Tek seferlik."""
    with _acct_lock(aid):
        row, before, rw = _reward_row(aid)
        esc = dict(rw.get("escrow") or {})
        if rid not in esc:
            return False                 # zaten ödendi / iade edildi
        esc.pop(rid, None)
        rw["escrow"] = esc
        payout = max(0, int(payout))
        earned = max(0, _int(before.get("gems_earned"), 0))
        spent = min(max(0, _int(before.get("gems_spent"), 0)), earned)
        payout = min(payout, max(0, GEM_TOTAL_MAX - earned))
        if payout:
            rw["srv_earned"] = _int(rw.get("srv_earned"), 0) + payout
        merged = dict(before)
        merged["gems_earned"] = earned + payout
        merged["gems_spent"] = spent
        merged["gems"] = max(0, merged["gems_earned"] - spent)
        merged["rewards"] = rw
        if _store_progress(aid, row, before, merged) is not None:
            return False
    _log_event(aid, "oyun", payout, int(merged["gems"]), note[:120])
    return True


def _escrow_reconcile(aid):
    """Sunucuda artık olmayan masaların emanetini iade eder (yeniden başlatma vb.)."""
    with _games_lock:
        row = _player_row(aid)
        prog = _stored_progress(row)
        esc = dict((prog.get("rewards") or {}).get("escrow") or {})
        for rid, amt in esc.items():
            room = _games.get(rid)
            if room is None or aid not in [p_["aid"] for p_ in room["players"]]:
                _escrow_pay(aid, rid, _int(amt, 0), "masa kapandı: elmas iade")


# ---- masa yardımcıları ----
def _room_of(aid):
    for room in _games.values():
        if room["state"] in ("wait", "play") and any(p_["aid"] == aid for p_ in room["players"]):
            return room
    return None


def _room_public(room):
    return {"id": room["id"], "kind": room["kind"], "stake": room["stake"], "cap": room["cap"],
            "players": [p_["name"] for p_ in room["players"]], "state": room["state"],
            "side": room.get("side"), "age": int(time.time() - room["created"])}


def _settle(room, winners_idx, why):
    """Masayı bitirir: kazanan(lar)a pot - %5, beraberlikte herkese iade."""
    if room["state"] == "done":
        return
    room["state"] = "done"
    room["done_at"] = time.time()
    n = len(room["players"])
    pot = room["stake"] * n
    res = {"why": why, "winners": [room["players"][i]["name"] for i in winners_idx], "pot": pot}
    if not winners_idx or len(winners_idx) == n:
        res["refund"] = True
        for p_ in room["players"]:
            _escrow_pay(p_["aid"], room["id"], room["stake"],
                        "%s: berabere, elmas iade" % GAME_NAMES[room["kind"]])
        res["payout"] = room["stake"]
    else:
        share = int(pot * (1.0 - GAME_RAKE)) // len(winners_idx)
        res["payout"] = share
        res["rake"] = pot - share * len(winners_idx)
        for i, p_ in enumerate(room["players"]):
            win = i in winners_idx
            _escrow_pay(p_["aid"], room["id"], share if win else 0,
                        "%s %s: %s" % (GAME_NAMES[room["kind"]], "kazandı" if win else "kaybetti",
                                       ("+%d" % share) if win else ("-%d" % room["stake"])))
    room["result"] = res
    room["seq"] += 1


def _cancel(room, why):
    if room["state"] == "done":
        return
    room["state"] = "done"
    room["done_at"] = time.time()
    for p_ in room["players"]:
        _escrow_pay(p_["aid"], room["id"], room["stake"],
                    "%s masası kapandı: elmas iade" % GAME_NAMES[room["kind"]])
    room["result"] = {"why": why, "refund": True, "winners": [], "payout": room["stake"], "pot": 0}
    room["seq"] += 1


# ---- blackjack ----
def _bj_value(cards):
    v, aces = 0, 0
    for c in cards:
        r = c[:-1]
        if r == "A":
            v += 11
            aces += 1
        elif r in ("J", "Q", "K"):
            v += 10
        else:
            v += int(r)
    while v > 21 and aces:
        v -= 10
        aces -= 1
    return v


def _bj_start(room):
    room["deck"] = _new_deck()
    room["hands"] = [[room["deck"].pop(), room["deck"].pop()] for _ in room["players"]]
    room["done"] = [False] * len(room["players"])
    now = time.time()
    room["deadline"] = [now + GAME_TURN_T["bj"]] * len(room["players"])
    for i, h in enumerate(room["hands"]):
        if _bj_value(h) == 21:
            room["done"][i] = True       # blackjack: kendiliğinden durur


def _bj_act(room, i, action):
    if room["done"][i]:
        return "elin bitti, rakibi bekle"
    if action == "hit":
        room["hands"][i].append(room["deck"].pop())
        if _bj_value(room["hands"][i]) >= 21:
            room["done"][i] = True
    elif action == "stand":
        room["done"][i] = True
    else:
        return "geçersiz hamle"
    room["deadline"][i] = time.time() + GAME_TURN_T["bj"]
    return None


def _bj_finish_if_done(room):
    if room["state"] != "play" or not all(room["done"]):
        return
    vals = [_bj_value(h) for h in room["hands"]]
    nat = [len(h) == 2 and v == 21 for h, v in zip(room["hands"], vals)]
    ok = [i for i, v in enumerate(vals) if v <= 21]
    if not ok:
        return _settle(room, [], "ikisi de battı")
    best = max(vals[i] for i in ok)
    top = [i for i in ok if vals[i] == best]
    if len(top) > 1 and any(nat[i] for i in top) and not all(nat[i] for i in top):
        top = [i for i in top if nat[i]]
    _settle(room, top, "blackjack" if any(nat[i] for i in top) else "en yüksek el")


# ---- pişti ----
def _pisti_card_points(c):
    r, s_ = c[:-1], c[-1]
    if c == "10D":
        return 3
    if c == "2C":
        return 2
    return 1 if r in ("A", "J") else 0


def _pisti_start(room):
    deck = _new_deck()
    table = [deck.pop() for _ in range(4)]
    room["deck"] = deck
    room["table"] = table                 # son eleman açık (üstteki)
    room["hands"] = [[deck.pop() for _ in range(4)] for _ in room["players"]]
    n = len(room["players"])
    room["taken"] = [[] for _ in range(n)]
    room["pisti"] = [0] * n
    room["turn"] = 0
    room["last_taker"] = None
    room["last"] = None
    room["deadline"] = time.time() + GAME_TURN_T["pisti"]


def _pisti_play(room, i, card):
    if room["turn"] != i:
        return "sıra sende değil"
    hand = room["hands"][i]
    if card not in hand:
        return "bu kart elinde yok"
    hand.remove(card)
    table = room["table"]
    top = table[-1] if table else None
    took = False
    pis = 0
    if top is not None and (card[:-1] == top[:-1] or card[:-1] == "J"):
        if len(table) == 1 and card[:-1] == top[:-1]:
            pis = 20 if card[:-1] == "J" else 10
            room["pisti"][i] += pis
        room["taken"][i].extend(table + [card])
        room["table"] = []
        room["last_taker"] = i
        took = True
    else:
        table.append(card)
    room["last"] = {"by": room["players"][i]["name"], "card": card, "took": took, "pisti": pis}
    n = len(room["players"])
    room["turn"] = (i + 1) % n
    if all(not h for h in room["hands"]):
        if len(room["deck"]) >= 4 * n:
            room["hands"] = [[room["deck"].pop() for _ in range(4)] for _ in range(n)]
        else:
            if room["table"] and room["last_taker"] is not None:
                room["taken"][room["last_taker"]].extend(room["table"])
                room["table"] = []
            _pisti_finish(room)
            return None
    room["deadline"] = time.time() + (GAME_LEFT_T if room["players"][room["turn"]].get("left")
                                      else GAME_TURN_T["pisti"])
    return None


def _pisti_scores(room):
    n = len(room["players"])
    sc = [sum(_pisti_card_points(c) for c in room["taken"][i]) + room["pisti"][i] for i in range(n)]
    counts = [len(t) for t in room["taken"]]
    mx = max(counts) if counts else 0
    if mx and counts.count(mx) == 1:
        sc[counts.index(mx)] += 3
    return sc


def _pisti_finish(room):
    sc = _pisti_scores(room)
    room["final_scores"] = sc
    best = max(sc)
    _settle(room, [i for i, v in enumerate(sc) if v == best], "en çok puan")


# ---- zaman aşımı / otomatik hamle ----
def _game_tick(room):
    now = time.time()
    if room["state"] == "wait":
        if now - room["created"] > GAME_WAIT_T:
            _cancel(room, "masa dolmadı")
        return
    if room["state"] != "play":
        return
    if room["kind"] == "bj":
        for i in range(len(room["players"])):
            if not room["done"][i] and (now > room["deadline"][i] or room["players"][i].get("left")):
                room["done"][i] = True
                room["seq"] += 1
        _bj_finish_if_done(room)
    elif room["kind"] == "pisti":
        guard = 0
        while room["state"] == "play" and now > room["deadline"] and guard < 60:
            guard += 1
            i = room["turn"]
            hand = room["hands"][i]
            if not hand:
                break
            top = room["table"][-1] if room["table"] else None
            pick = None
            if top is not None:
                same = [c for c in hand if c[:-1] == top[:-1]]
                jack = [c for c in hand if c[:-1] == "J"]
                pick = (same or jack or [None])[0]
            _pisti_play(room, i, pick or _game_rng.choice(hand))
            room["seq"] += 1


def _game_reaper():
    while True:
        time.sleep(1.0)
        try:
            with _games_lock:
                now = time.time()
                for rid in list(_games):
                    room = _games[rid]
                    try:
                        _game_tick(room)
                    except Exception:
                        app.logger.exception("masa işlenemedi")
                    if room["state"] == "done" and now - room.get("done_at", now) > GAME_DONE_KEEP:
                        _games.pop(rid, None)
        except Exception:
            app.logger.exception("oyun bekçisi")


_game_reaper_started = [False]


def _game_reaper_start():
    if not _game_reaper_started[0]:
        _game_reaper_started[0] = True
        threading.Thread(target=_game_reaper, daemon=True).start()


# ---- oyuncuya giden görünüm (yalnız görmesi gerekenler) ----
def _room_view(room, aid):
    me = next((i for i, p_ in enumerate(room["players"]) if p_["aid"] == aid), None)
    out = _room_public(room)
    out["seq"] = room["seq"]
    out["me"] = me
    out["result"] = room.get("result")
    reveal = room["state"] == "done"
    now = time.time()
    if room["kind"] == "coin" and room.get("flip"):
        out["flip"] = room["flip"]
    if room["kind"] == "bj" and "hands" in room:
        hands = []
        for i, h in enumerate(room["hands"]):
            if reveal or i == me:
                hands.append({"cards": list(h), "value": _bj_value(h), "done": room["done"][i]})
            else:
                # rakip: yalnız ilk kart açık, gerisi kapalı (sayısı bilinir)
                hands.append({"cards": [h[0]] + ["??"] * (len(h) - 1), "value": None, "done": room["done"][i]})
        out["hands"] = hands
        if me is not None and room["state"] == "play":
            out["time_left"] = max(0, int(room["deadline"][me] - now))
    if room["kind"] == "pisti" and "hands" in room:
        out["hand"] = list(room["hands"][me]) if me is not None else []
        out["counts"] = [len(h) for h in room["hands"]]
        out["table_top"] = room["table"][-1] if room["table"] else None
        out["table_n"] = len(room["table"])
        out["deck_n"] = len(room["deck"])
        out["taken_n"] = [len(t) for t in room["taken"]]
        out["pisti"] = list(room["pisti"])
        out["turn"] = room["turn"]
        out["last"] = room.get("last")
        out["time_left"] = max(0, int(room["deadline"] - now)) if room["state"] == "play" else 0
        if reveal and "final_scores" in room:
            out["scores"] = room["final_scores"]
    return out


def _game_resp(acc, extra=None):
    prog = _stored_progress(_player_row(acc["id"]))
    d = {"success": True, "state": _site_state(acc, prog)}
    if extra:
        d.update(extra)
    return jsonify(d)


@app.route("/site/games/list", methods=["POST"])
def site_games_list():
    acc, data, err = _site_ctx(poll=True)
    if err:
        return err
    _game_reaper_start()
    kind = str(data.get("kind") or "")
    with _games_lock:
        rooms = [_room_public(r) for r in _games.values()
                 if r["state"] == "wait" and (not kind or r["kind"] == kind)]
        mine = _room_of(acc["id"])
    rooms.sort(key=lambda r: r["stake"])
    return jsonify({"success": True, "rooms": rooms[:60], "mine": mine["id"] if mine else None,
                    "mine_kind": mine["kind"] if mine else None, "stakes": list(GAME_STAKES)})


@app.route("/site/games/create", methods=["POST"])
def site_games_create():
    acc, data, err = _site_ctx()
    if err:
        return err
    _game_reaper_start()
    kind = str(data.get("kind") or "")
    stake = _int(data.get("stake"), 0)
    if kind not in GAME_KINDS or stake not in GAME_STAKES:
        return jsonify({"success": False, "error": "geçersiz masa"}), 400
    lo, hi = GAME_KINDS[kind]
    cap = max(lo, min(hi, _int(data.get("cap"), lo)))
    side = str(data.get("side") or "yazi")
    if side not in ("yazi", "tura"):
        side = "yazi"
    if not _rate_ok("game:new:" + str(acc["id"]), 12, 60):
        return jsonify({"success": False, "error": "çok sık masa açıyorsun"}), 429
    aid = acc["id"]
    with _games_lock:
        _escrow_reconcile(aid)
        if _room_of(aid):
            return jsonify({"success": False, "error": "zaten bir masadasın"}), 409
        rid = secrets.token_hex(8)
        e = _escrow_take(aid, rid, stake, GAME_NAMES[kind])
        if e:
            return jsonify({"success": False, "error": e}), 409
        _games[rid] = {"id": rid, "kind": kind, "stake": stake, "cap": cap, "state": "wait",
                       "created": time.time(), "seq": 1, "side": side if kind == "coin" else None,
                       "players": [{"aid": aid, "name": _site_name(acc), "ip": _ip_tag()}]}
        view = _room_view(_games[rid], aid)
    return _game_resp(acc, {"room": view})


@app.route("/site/games/join", methods=["POST"])
def site_games_join():
    acc, data, err = _site_ctx()
    if err:
        return err
    rid = str(data.get("room") or "")[:32]
    aid = acc["id"]
    with _games_lock:
        _escrow_reconcile(aid)
        room = _games.get(rid)
        if room is None or room["state"] != "wait":
            return jsonify({"success": False, "error": "bu masa artık yok"}), 404
        if _room_of(aid):
            return jsonify({"success": False, "error": "zaten bir masadasın"}), 409
        ip = _ip_tag()
        if any(p_["ip"] == ip for p_ in room["players"]):
            return jsonify({"success": False, "error": "aynı bağlantıdan iki hesap aynı masaya oturamaz"}), 403
        e = _escrow_take(aid, rid, room["stake"], GAME_NAMES[room["kind"]])
        if e:
            return jsonify({"success": False, "error": e}), 409
        room["players"].append({"aid": aid, "name": _site_name(acc), "ip": ip})
        room["seq"] += 1
        if len(room["players"]) >= room["cap"]:
            room["state"] = "play"
            if room["kind"] == "coin":
                flip = _game_rng.choice(("yazi", "tura"))
                room["flip"] = flip
                _settle(room, [0 if flip == room["side"] else 1], "para: " + flip)
            elif room["kind"] == "bj":
                _bj_start(room)
                _bj_finish_if_done(room)
            else:
                _pisti_start(room)
        view = _room_view(room, aid)
    return _game_resp(acc, {"room": view})


@app.route("/site/games/state", methods=["POST"])
def site_games_state():
    acc, data, err = _site_ctx(poll=True)
    if err:
        return err
    rid = str(data.get("room") or "")[:32]
    with _games_lock:
        room = _games.get(rid)
        if room is None or not any(p_["aid"] == acc["id"] for p_ in room["players"]):
            return jsonify({"success": False, "error": "masa kapandı", "gone": True}), 404
        _game_tick(room)
        if _int(data.get("seq"), -1) == room["seq"] and room["state"] != "play":
            return jsonify({"success": True, "same": True})
        view = _room_view(room, acc["id"])
    return jsonify({"success": True, "room": view})


@app.route("/site/games/act", methods=["POST"])
def site_games_act():
    acc, data, err = _site_ctx()
    if err:
        return err
    rid = str(data.get("room") or "")[:32]
    action = str(data.get("action") or "")
    aid = acc["id"]
    with _games_lock:
        room = _games.get(rid)
        if room is None:
            return jsonify({"success": False, "error": "masa kapandı"}), 404
        idx = next((i for i, p_ in enumerate(room["players"]) if p_["aid"] == aid), None)
        if idx is None:
            return jsonify({"success": False, "error": "bu masada değilsin"}), 403
        _game_tick(room)
        e = None
        if action == "leave":
            if room["state"] == "wait":
                room["players"].pop(idx)
                _escrow_pay(aid, rid, room["stake"], "%s: masadan kalktı, elmas iade" % GAME_NAMES[room["kind"]])
                room["seq"] += 1
                if not room["players"]:
                    _games.pop(rid, None)
                view = None
            elif room["state"] == "play":
                # oyun sürerken kalkan oyuncunun eli kendiliğinden oynanır (kaybeder)
                room["players"][idx]["left"] = True
                if room["kind"] == "bj":
                    room["done"][idx] = True
                    room["hands"][idx].extend([])
                    _bj_finish_if_done(room)
                elif room["kind"] == "pisti" and room["turn"] == idx:
                    room["deadline"] = min(room["deadline"], time.time() + GAME_LEFT_T)
                room["seq"] += 1
                view = _room_view(room, aid)
            else:
                view = _room_view(room, aid)
            return _game_resp(acc, {"room": view})
        if room["state"] != "play":
            return jsonify({"success": False, "error": "oyun başlamadı ya da bitti"}), 409
        if room["kind"] == "bj":
            e = _bj_act(room, idx, action)
            if not e:
                _bj_finish_if_done(room)
        elif room["kind"] == "pisti" and action == "play":
            e = _pisti_play(room, idx, str(data.get("card") or "")[:3])
        else:
            e = "geçersiz hamle"
        if e:
            return jsonify({"success": False, "error": e}), 409
        room["seq"] += 1
        view = _room_view(room, aid)
        done = room["state"] == "done"
    if done:
        return _game_resp(acc, {"room": view})
    return jsonify({"success": True, "room": view})


# ---- rulet (kasaya karşı, Avrupa tipi tek sıfır) ----
def _roul_win(bet, n):
    t, v = bet["type"], bet.get("value")
    if t == "num":
        return 36 if n == v else 0
    if n == 0:
        return 0
    if t == "red":
        return 2 if n in ROUL_RED else 0
    if t == "black":
        return 2 if n not in ROUL_RED else 0
    if t == "even":
        return 2 if n % 2 == 0 else 0
    if t == "odd":
        return 2 if n % 2 == 1 else 0
    if t == "low":
        return 2 if n <= 18 else 0
    if t == "high":
        return 2 if n >= 19 else 0
    if t == "dozen":
        return 3 if (n - 1) // 12 + 1 == v else 0
    if t == "col":
        return 3 if (n - 1) % 3 + 1 == v else 0
    return 0


@app.route("/site/roulette/spin", methods=["POST"])
def site_roulette_spin():
    acc, data, err = _site_ctx()
    if err:
        return err
    raw = data.get("bets")
    if not isinstance(raw, list) or not raw or len(raw) > 40:
        return jsonify({"success": False, "error": "bahis yok"}), 400
    bets = []
    for b in raw:
        if not isinstance(b, dict):
            return jsonify({"success": False, "error": "geçersiz bahis"}), 400
        t = str(b.get("type") or "")
        amt = _int(b.get("amount"), 0)
        v = _int(b.get("value"), -1)
        if t not in ("num", "red", "black", "even", "odd", "low", "high", "dozen", "col") or amt < ROULETTE_MIN:
            return jsonify({"success": False, "error": "geçersiz bahis"}), 400
        if t == "num" and not 0 <= v <= 36:
            return jsonify({"success": False, "error": "geçersiz sayı"}), 400
        if t in ("dozen", "col") and v not in (1, 2, 3):
            return jsonify({"success": False, "error": "geçersiz bahis"}), 400
        bets.append({"type": t, "value": v if t in ("num", "dozen", "col") else None, "amount": amt})
    total = sum(b["amount"] for b in bets)
    if total > ROULETTE_MAX:
        return jsonify({"success": False, "error": "tek çevirmede en çok %d elmas" % ROULETTE_MAX}), 400
    if not _rate_ok("roul:" + str(acc["id"]), 30, 60):
        return jsonify({"success": False, "error": "çok hızlı, biraz yavaşla"}), 429
    aid = acc["id"]
    with _acct_lock(aid):
        row, before, rw = _reward_row(aid)
        today = _server_day()
        used = _int(rw.get("roul_count"), 0) if rw.get("roul_day") == today else 0
        if used >= ROULETTE_DAILY:
            return jsonify({"success": False, "error": "bugünkü rulet sınırına ulaştın"}), 429
        earned = max(0, _int(before.get("gems_earned"), 0))
        spent = min(max(0, _int(before.get("gems_spent"), 0)), earned)
        if earned - spent < total:
            return jsonify({"success": False, "error": "yeterli elmasın yok"}), 409
        n = _game_rng.randrange(37)
        win = sum(b["amount"] * _roul_win(b, n) for b in bets)
        win = min(win, max(0, GEM_TOTAL_MAX - earned))
        merged = dict(before)
        merged["gems_spent"] = spent + total
        merged["gems_earned"] = earned + win
        merged["gems"] = max(0, merged["gems_earned"] - merged["gems_spent"])
        rw["roul_day"] = today
        rw["roul_count"] = used + 1
        rw["srv_spent"] = _int(rw.get("srv_spent"), 0) + total
        rw["srv_earned"] = _int(rw.get("srv_earned"), 0) + win
        merged["rewards"] = rw
        e = _store_progress(aid, row, before, merged)
        if e is not None:
            return e
        _log_event(aid, "rulet", win - total, int(merged["gems"]), ("rulet %d: bahis %d, kazanç %d" % (n, total, win))[:120])
    return jsonify({"success": True, "number": n, "color": "green" if n == 0 else ("red" if n in ROUL_RED else "black"),
                    "bet": total, "win": win, "state": _site_state(acc, merged)})


@app.route("/admin/give_item", methods=["POST"])
def admin_give_item():
    """Yönetici: bir oyuncuya satılmayan kozmetik verir (50M Tacı)."""
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    data = _body()
    acc = _acct(data)
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    if str(acc.get("username") or "").strip().lower() not in ADMIN_USERNAMES:
        app.logger.warning("yetkisiz /admin/give_item denemesi: hesap %s", acc.get("id"))
        return jsonify({"success": False, "error": "bu komut için yetkin yok"}), 403
    if not _rate_ok("adm:" + str(acc.get("id")), 30, 60):
        return jsonify({"success": False, "error": "çok sık istek"}), 429
    item = str(data.get("item") or "")
    if item not in ADMIN_ONLY_COSMETICS:
        return jsonify({"success": False, "error": "bilinmeyen eşya"}), 400
    tgt = _account_named(data.get("name"))
    if not tgt:
        return jsonify({"success": False, "error": "bu adda oyuncu yok"}), 404
    tid = tgt.get("id")
    try:
        with _acct_lock(tid):
            row = _player_row(tid)
            before = _stored_progress(row)
            merged = json.loads(json.dumps(before))
            lst = list(merged.get("cosmetics_owned") or [])
            had = item in lst
            if not had:
                lst.append(item)
                merged["cosmetics_owned"] = lst
                e = _store_progress(tid, row, before, merged)
                if e is not None:
                    return e
        _log_event(tid, "kostum", 1, 0, ("yönetici verdi: %s (%s)" % (item, acc.get("username")))[:120])
    except Exception as e:
        return _oops(e, "eşya verilemedi")
    return jsonify({"success": True, "name": tgt.get("username"), "item": item, "had": had})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
