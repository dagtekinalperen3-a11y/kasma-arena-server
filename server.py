import os
import json
import time
import uuid
import hmac
import hashlib
import threading
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__, static_folder=".")
CORS(app)  # CORS sorunlarını önlemek için

# Supabase bağlantı bilgileri (Render Environment değişkenlerinden alınır)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

# =====================================================================
# HESAP SİSTEMİ  (v3.19) — GOOGLE İLE GİRİŞ + E-POSTA/ŞİFRE KAYDI
# ---------------------------------------------------------------------
# GÜVENLİK TASARIMI — neden böyle kuruldu:
#
# 1) ŞİFRE ASLA DÜZ SAKLANMAZ. scrypt ile, kullanıcıya özel rastgele tuzla
#    karılır (bkz. _hash_password). scrypt bellek-zorlu bir fonksiyondur;
#    veritabanı çalınsa bile şifreleri kaba kuvvetle çözmek pahalıdır.
#    Karşılaştırma hmac.compare_digest ile yapılır (zamanlama sızıntısı yok).
#
# 2) GOOGLE GİRİŞİNDE "CLIENT SECRET" OYUNDA DURMAZ. Oyun yalnızca
#    yetkilendirme KODUNU alır ve sunucuya yollar; kodu jetona çeviren ve
#    kimliği doğrulayan taraf SUNUCUDUR. Oyun dosyası açılsa bile gizli
#    anahtar çıkmaz. Akış RFC 8252 (native app) + PKCE'dir: oyun rastgele
#    bir doğrulayıcı üretir, Google'a yalnızca özetini gönderir; kodu
#    çalan biri doğrulayıcıyı bilmediği için kullanamaz.
#
# 3) KİMLİK JETONU GOOGLE'DAN DOĞRUDAN ALINIR. Kod değişimi sunucu ile
#    Google arasında TLS üzerinden yapıldığı için jeton kanalın kendisiyle
#    doğrulanmış olur; yine de iss / aud / exp / email_verified alanları
#    tek tek denetlenir (bkz. _verify_google_id_token).
#
# 4) OTURUM JETONU VERİTABANINDA DÜZ DURMAZ. 32 baytlık rastgele bir jeton
#    üretilir, oyuncuya bir kez verilir, veritabanına yalnızca SHA-256
#    ÖZETİ yazılır. Veritabanı çalınsa bile oturumlar ele geçirilemez.
#    Jetonun son kullanma tarihi vardır (SESSION_TTL).
#
# 5) GİRİŞ DENEMELERİ SINIRLIDIR (bkz. _rate_ok): aynı kaynaktan şifre
#    deneyen bir saldırgan kesilir.
#
# 6) "Kullanıcı var mı yok mu" SIZDIRILMAZ: yanlış e-posta ile yanlış şifre
#    aynı hatayı döndürür.
#
# KURULUM (bu üçü olmadan Google girişi kapalı kalır, oyun yine çalışır):
#   GOOGLE_CLIENT_ID      Google Cloud > Kimlik Bilgileri > OAuth istemcisi
#   GOOGLE_CLIENT_SECRET  (aynı yerden; YALNIZCA sunucuda dursun)
#   Supabase'de iki tablo gerekir — SQL'i README_ACCOUNTS.md dosyasında.
# =====================================================================

import base64
import re as _re
import secrets

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

SESSION_TTL = 60 * 60 * 24 * 60          # oturum ömrü: 60 gün
PW_MIN_LEN = 8
NAME_MAX = 14
# scrypt parametreleri. N bellek maliyeti; 2**15 masaüstü/sunucu için
# makul (yaklaşık 32 MB) ve kaba kuvveti ciddi biçimde pahalılaştırır.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 15, 8, 1
EMAIL_RE = _re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,24}$")

# KULLANICI ADI: sıralamada görünen ad. Bir kez seçilir, BİR DAHA DEĞİŞMEZ.
# Harf/rakam/alt çizgi; boşluk ve noktalama yok ki sıralamada başkasının adını
# taklit eden "KASMACI " gibi varyantlar üretilemesin.
USERNAME_RE = _re.compile(r"^[A-Za-z0-9ÇĞİÖŞÜçğıöşü_]{3,14}$")

# Oyuncunun adını çalmaya çalışan "admin / moderator" gibi adlar kapalı.
USERNAME_BLOCK = {"admin", "administrator", "moderator", "mod", "sistem", "system",
                  "kasma", "kasmaarena", "root", "null", "undefined", "anonim",
                  "isimsiz", "server", "sunucu", "support", "destek"}


def _accounts_enabled():
    return bool(supabase)


def _google_enabled():
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and supabase)


def _hash_password(password, salt=None):
    """Şifreyi scrypt ile karar. Dönüş: saklanabilir tek bir metin."""
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt,
                        n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32,
                        maxmem=64 * 1024 * 1024)
    return "scrypt$%d$%d$%d$%s$%s" % (
        SCRYPT_N, SCRYPT_R, SCRYPT_P,
        base64.b64encode(salt).decode(), base64.b64encode(dk).decode())


def _verify_password(password, stored):
    """Şifre doğru mu? Sabit zamanlı karşılaştırma."""
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


def _token_hash(tok):
    return hashlib.sha256(tok.encode("utf-8")).hexdigest()


def _clean_device(d):
    """İstemciden gelen cihaz kimliği: yalnızca 64 karaktere kadar hex.

    Oyun bunu makine adının SHA-256 özetinden üretir (bkz. device_id);
    sunucuya gerçek kullanıcı/makine adı hiç gelmez. Biçimi burada da
    daraltıyoruz ki bu alan serbest metin deposuna dönüşmesin.
    """
    d = str(d or "")[:64].strip().lower()
    return d if all(c in "0123456789abcdef" for c in d) and len(d) >= 16 else ""


def _new_session(account_id, device=""):
    """Yeni oturum jetonu. Veritabanına yalnızca ÖZETİ yazılır.

    Oturum, girişin yapıldığı CİHAZA bağlanır: jeton bir başkasının eline
    geçse (kayıt dosyası paylaşıldı, dosya çalındı) başka bir makinede
    kabul edilmez.
    """
    tok = secrets.token_urlsafe(32)
    supabase.table("sessions").insert({
        "token_hash": _token_hash(tok),
        "account_id": account_id,
        "device_hash": _clean_device(device),
        "created_at": time.time(),
        "expires_at": time.time() + SESSION_TTL,
    }).execute()
    return tok


def _account_by_session(tok, device=None):
    """Jetondan hesabı bulur. Süresi dolmuşsa ya da CİHAZ tutmuyorsa None.

    device=None geçilirse cihaz denetimi YAPILMAZ; bu yalnızca skor
    gönderimi gibi, jetonun tek işinin "adı sahiplenmek" olduğu yerler
    için. Hesabı okuyan/değiştiren uçlar cihazı mutlaka geçirir.
    """
    if not tok or not supabase:
        return None
    rows = supabase.table("sessions").select("*").eq(
        "token_hash", _token_hash(tok)).execute()
    if not rows.data:
        return None
    sess = rows.data[0]
    if float(sess.get("expires_at", 0)) < time.time():
        try:
            supabase.table("sessions").delete().eq(
                "token_hash", sess["token_hash"]).execute()
        except Exception:
            pass
        return None
    if device is not None:
        want = str(sess.get("device_hash") or "")
        # Eski oturumlarda device_hash boş olabilir: onları kırmıyoruz,
        # yalnızca İKİSİ de doluyken eşitlik arıyoruz.
        if want and _clean_device(device) != want:
            return None
    # DİKKAT: sütunları TEK TEK saymıyoruz. Daha önce burada sabit bir
    # liste vardı ve "username" o listede yoktu; sonucu şuydu: oyun yeniden
    # açıldığında /auth/me kullanıcı adı olmayan bir hesap döndürüyor, oyun
    # "daha ad seçmemişsin" sanıp DÜNYA SIRALAMASINI KAPATIYORDU. Yeni bir
    # sütun eklendiğinde aynı hatanın tekrarlamaması için hepsini alıyoruz;
    # şifre özeti zaten _public_account süzgecinden geçmeden dışarı çıkmıyor.
    acc = supabase.table("accounts").select("*").eq(
        "id", sess["account_id"]).execute()
    return acc.data[0] if acc.data else None


def _public_account(acc):
    """Oyuncuya DÖNDÜRÜLEBİLİR alanlar. Şifre özeti asla buraya girmez."""
    return {
        "id": acc.get("id"),
        "email": acc.get("email") or "",
        "username": acc.get("username") or "",
        # name = sıralamada görünen ad. Kullanıcı adı seçilmişse odur.
        "name": acc.get("username") or acc.get("name") or "",
        "provider": acc.get("provider", "password"),
        # Kullanıcı adı henüz seçilmemişse oyun bir kereye mahsus seçtirir.
        "needs_username": not bool(acc.get("username")),
    }


def _clean_username(u):
    """Kullanıcı adını denetler. (ok, temiz_ad_veya_hata) döner."""
    u = str(u or "").strip()
    if not USERNAME_RE.match(u):
        return False, "kullanıcı adı 3-14 karakter olmalı (harf, rakam, _)"
    if u.lower() in USERNAME_BLOCK:
        return False, "bu kullanıcı adı kullanılamaz"
    return True, u


def _username_taken(u, except_id=None):
    rows = supabase.table("accounts").select("id,username").execute()
    low = u.lower()
    for r in rows.data or []:
        if str(r.get("username") or "").lower() == low and r.get("id") != except_id:
            return True
    return False


def _b64url_json(part):
    pad = "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(part + pad).decode("utf-8"))


def _verify_google_id_token(id_token):
    """Google kimlik jetonunun İÇERİĞİNİ denetler.

    İMZA ayrıca doğrulanmaz çünkü jeton, SUNUCU ile Google arasında TLS
    üzerinden yapılan kod değişiminden DOĞRUDAN geldi — araya kimse
    giremez. (Jeton istemciden gelseydi imza doğrulaması şart olurdu;
    bu akışta istemci jetonu hiç görmüyor.)
    """
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
    rows = supabase.table("accounts").select("*").eq("email", email).execute()
    if rows.data:
        acc = rows.data[0]
        # Google ile giren, daha önce şifreyle açılmış hesabına bağlanabilir.
        patch = {}
        if google_sub and not acc.get("google_sub"):
            patch["google_sub"] = google_sub
        if name and not acc.get("name"):
            patch["name"] = name[:NAME_MAX]
        if patch:
            supabase.table("accounts").update(patch).eq("id", acc["id"]).execute()
            acc.update(patch)
        return acc, False
    new = {
        "email": email,
        # Google'dan gelen ad yalnızca BİLGİ. Sıralamada görünecek
        # KULLANICI ADINI oyuncu bir kez kendisi seçer (bkz.
        # /auth/username) ve bir daha değiştiremez.
        "name": (name or "")[:NAME_MAX],
        "provider": provider,
        "created_at": time.time(),
    }
    if password_hash:
        new["password_hash"] = password_hash
    if google_sub:
        new["google_sub"] = google_sub
    res = supabase.table("accounts").insert(new).execute()
    return res.data[0], True


@app.route("/diag", methods=["GET"])
def diag():
    """KURULUM DOĞRU MU? Tarayıcıda açılıp bakılacak tek adres.

    Eksik bir tablo ya da sütun yüzünden ilerleme sessizce yazılamıyorsa
    burada görünür. Hiçbir oyuncu verisi döndürmez — yalnızca "var / yok".
    """
    out = {"supabase": bool(supabase), "google": _google_enabled(),
           "tables": {}, "ok": True, "yapilacak": []}
    if not supabase:
        out["ok"] = False
        out["yapilacak"].append("SUPABASE_URL ve SUPABASE_KEY girilmemiş "
                                "(service_role anahtarı olmalı)")
        return jsonify(out)
    # Her tablodan tek satır okumayı dene; hata metni eksik olanı söyler.
    need = {
        "accounts": ["id", "username", "email", "provider", "password_hash",
                     "google_sub", "created_at"],
        "sessions": ["token_hash", "account_id", "device_hash", "expires_at"],
        "player_data": ["account_id", "gems", "gems_earned", "gems_spent",
                        "best_score", "best_wave", "total_kills", "runs",
                        "skin_count", "pet_count", "data", "updated_at"],
        "player_events": ["account_id", "at", "kind", "delta", "total", "note"],
        "scores": ["name", "score", "kills", "wave", "run_time", "created_at",
                   "account_id"],
    }
    for tbl, cols in need.items():
        info = {"var": False, "eksik_sutunlar": []}
        try:
            supabase.table(tbl).select("*").limit(1).execute()
            info["var"] = True
        except Exception as e:
            info["hata"] = str(e)[:160]
            out["ok"] = False
            out["yapilacak"].append(f"'{tbl}' tablosu yok — VERITABANI.sql'i çalıştır")
            out["tables"][tbl] = info
            continue
        for c in cols:
            try:
                supabase.table(tbl).select(c).limit(1).execute()
            except Exception:
                info["eksik_sutunlar"].append(c)
        if info["eksik_sutunlar"]:
            out["ok"] = False
            out["yapilacak"].append(
                f"'{tbl}' tablosunda eksik sütun: " + ", ".join(info["eksik_sutunlar"]))
        out["tables"][tbl] = info
    if not _google_enabled():
        out["yapilacak"].append("Google girişi kapalı (GOOGLE_CLIENT_ID / "
                                "GOOGLE_CLIENT_SECRET yok) — zorunlu değil")
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
    src = (request.headers.get("X-Forwarded-For", request.remote_addr or "?")).split(",")[0].strip()
    if not _rate_ok("auth:" + src):
        return jsonify({"success": False, "error": "çok fazla deneme"}), 429
    data = request.json or {}
    # KULLANICI ADI ile kayıt: e-posta İSTEĞE BAĞLI. Oyuncu Gmail'siz de
    # hesap açabilsin diye. (E-posta verilirse şifre kurtarmada işe yarar.)
    ok, uname = _clean_username(data.get("username"))
    if not ok:
        return jsonify({"success": False, "error": uname}), 400
    password = str(data.get("password", ""))
    email = str(data.get("email", "")).strip().lower()
    if email and not EMAIL_RE.match(email):
        return jsonify({"success": False, "error": "e-posta geçersiz"}), 400
    if len(password) < PW_MIN_LEN:
        return jsonify({"success": False,
                        "error": f"şifre en az {PW_MIN_LEN} karakter olmalı"}), 400
    try:
        if _username_taken(uname):
            return jsonify({"success": False,
                            "error": "bu kullanıcı adı alınmış"}), 409
        if email:
            rows = supabase.table("accounts").select("id").eq("email", email).execute()
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
        acc = supabase.table("accounts").insert(new_acc).execute().data[0]
        tok = _new_session(acc["id"], data.get("device"))
        return jsonify({"success": True, "token": tok, "account": _public_account(acc)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/auth/login", methods=["POST"])
def auth_login():
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    src = (request.headers.get("X-Forwarded-For", request.remote_addr or "?")).split(",")[0].strip()
    if not _rate_ok("auth:" + src):
        return jsonify({"success": False, "error": "çok fazla deneme"}), 429
    data = request.json or {}
    # Oyuncu kullanıcı adını DA e-postasını DA yazabilir; ikisi de aynı
    # kutudan gelir (bkz. oyundaki giriş ekranı).
    who = str(data.get("username") or data.get("email") or "").strip()
    password = str(data.get("password", ""))
    try:
        acc = None
        if "@" in who:
            rows = supabase.table("accounts").select("*").eq(
                "email", who.lower()).execute()
            acc = rows.data[0] if rows.data else None
        else:
            rows = supabase.table("accounts").select("*").execute()
            low = who.lower()
            for rrow in rows.data or []:
                if str(rrow.get("username") or "").lower() == low:
                    acc = rrow
                    break
        # "Kullanıcı yok" ile "şifre yanlış" AYNI hatayı döndürür: saldırgan
        # hangi adların kayıtlı olduğunu öğrenemesin.
        if not acc or not acc.get("password_hash") or \
                not _verify_password(password, acc["password_hash"]):
            return jsonify({"success": False,
                            "error": "kullanıcı adı ya da şifre hatalı"}), 401
        tok = _new_session(acc["id"], data.get("device"))
        return jsonify({"success": True, "token": tok, "account": _public_account(acc)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


class _GoogleError(Exception):
    """Google tarafında bir şey tutmadı. Metni oyuncuya gösterilebilir."""


def _exchange_google_code(code, verifier, redirect_uri):
    """Yetkilendirme kodunu Google'da jetona çevirir ve kimlik iddialarını döndürür.

    client_secret YALNIZCA burada kullanılır; oyun onu hiç görmez.
    Ayrı bir işlev olmasının ikinci sebebi: test edilebilmesi.
    """
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
    """Oyundan gelen YETKİLENDİRME KODUNU jetona çevirir (PKCE).

    Oyun hiçbir zaman client secret görmez; kodu jetona çeviren taraf burasıdır.
    """
    if not _google_enabled():
        return jsonify({"success": False,
                        "error": "Google girişi yapılandırılmamış"}), 503
    src = (request.headers.get("X-Forwarded-For", request.remote_addr or "?")).split(",")[0].strip()
    if not _rate_ok("auth:" + src):
        return jsonify({"success": False, "error": "çok fazla deneme"}), 429
    data = request.json or {}
    code = str(data.get("code", ""))
    verifier = str(data.get("code_verifier", ""))
    redirect_uri = str(data.get("redirect_uri", ""))
    if not code or not verifier or not redirect_uri:
        return jsonify({"success": False, "error": "eksik bilgi"}), 400
    # Geri dönüş adresi YALNIZCA yerel olabilir (RFC 8252 loopback).
    if not _re.match(r"^http://(127\.0\.0\.1|\[::1\]|localhost):\d{1,5}/?$", redirect_uri):
        return jsonify({"success": False, "error": "geri dönüş adresi geçersiz"}), 400
    try:
        payload = _exchange_google_code(code, verifier, redirect_uri)
    except _GoogleError as e:
        # Google'ın hata gövdesini oyuncuya aynen yansıtmıyoruz.
        return jsonify({"success": False, "error": str(e)}), 401
    try:
        acc, created = _find_or_create_account(
            payload["email"], payload.get("name") or payload.get("given_name", ""),
            "google", google_sub=payload.get("sub"))
        tok = _new_session(acc["id"], data.get("device"))
        return jsonify({"success": True, "token": tok, "new": created,
                        "account": _public_account(acc)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/auth/me", methods=["POST"])
def auth_me():
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    data = request.json or {}
    acc = _account_by_session(str(data.get("token", "")), data.get("device", ""))
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    return jsonify({"success": True, "account": _public_account(acc)})


@app.route("/auth/username", methods=["POST"])
def auth_set_username():
    """Kullanıcı adını BİR KEZ belirler.

    Google ile gelen oyuncunun sıralamada görünecek adı yoktur; onu burada
    bir kereye mahsus seçer. SEÇİLDİKTEN SONRA DEĞİŞTİRİLEMEZ: dünya
    sıralamasında bir ad kimdeyse onda kalsın, kimse "geçen haftanın
    birincisinin" adını üstüne geçirmesin.
    """
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    data = request.json or {}
    acc = _account_by_session(str(data.get("token", "")), data.get("device", ""))
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
    supabase.table("accounts").update(
        {"username": uname, "name": uname}).eq("id", acc["id"]).execute()
    acc["username"] = uname
    acc["name"] = uname
    return jsonify({"success": True, "account": _public_account(acc)})


# =====================================================================
# OYUNCU İLERLEMESİ  (v3.20)
# ---------------------------------------------------------------------
# Elmas, skinler, petler, kostümler, açılmış kitap/silahlar ve istatistikler
# HESABA ait. Böylece:
#   * Yeni hesap SIFIRDAN başlar (misafir oynarken topladıkların gelmez).
#   * Hesabınla başka bir bilgisayara girdiğinde ilerlemen seninle gelir.
#   * Kayıt dosyasını düzenleyen biri sunucudaki hesabı şişiremez: elmas
#     yalnızca MAKUL bir hızla artabilir (bkz. _merge_progress).
# =====================================================================

# Bir koşudan kazanılabilecek elmas için CÖMERT bir üst sınır. Amaç oyunu
# kısıtlamak değil, "tek istekle 1.000.000 elmas" yolunu kapatmak.
GEM_GAIN_CAP_PER_PUSH = 4000
PROGRESS_LISTS = ("skins_owned", "cosmetics_owned", "books_owned", "weapons_owned")
PROGRESS_STATS = ("runs", "best_score", "total_kills", "total_time", "bosses",
                  "best_wave", "total_shots", "total_gold", "total_lifesteal",
                  "best_run_gold", "best_run_dashes", "best_run_shots",
                  "total_bonk_hits")


def _player_row(account_id):
    rows = supabase.table("player_data").select("*").eq(
        "account_id", account_id).execute()
    return rows.data[0] if rows.data else None


def _blank_progress():
    return {
        "gems": 0, "gems_earned": 0, "gems_spent": 0,
        "skins_owned": ["default"], "equipped_skin": "default",
        "cosmetics_owned": [], "equipped_cosmetics": {},
        "books_owned": [], "weapons_owned": [],
        "achievements": {}, "stats": {},
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


def _merge_progress(old, new):
    """Sunucudaki ilerlemeyi oyundan geleniyle birleştirir.

    KURAL: ilerleme GERİ GİTMEZ, ve elmas defteri bir seferde en fazla
    GEM_GAIN_CAP_PER_PUSH kadar artabilir. İstemciden gelen sayıya olduğu
    gibi güvenilmez — oyun dosyası oyuncunun bilgisayarında duruyor.
    """
    out = dict(old)
    for k in PROGRESS_LISTS:
        merged = list(old.get(k) or [])
        for v in (new.get(k) or []):
            if isinstance(v, str) and v not in merged:
                merged.append(v)
        out[k] = merged[:400]
    for k in ("equipped_skin",):
        if new.get(k):
            out[k] = str(new[k])[:40]
    if isinstance(new.get("equipped_cosmetics"), dict):
        out["equipped_cosmetics"] = {str(a)[:20]: (str(b)[:40] if b else None)
                                     for a, b in list(new["equipped_cosmetics"].items())[:12]}
    # istatistikler: her alan yalnızca BÜYÜYEBİLİR
    st_old = dict(old.get("stats") or {})
    st_new = new.get("stats") or {}
    for k in PROGRESS_STATS:
        try:
            st_old[k] = max(float(st_old.get(k, 0) or 0), float(st_new.get(k, 0) or 0))
        except Exception:
            pass
    out["stats"] = st_old
    ach = dict(old.get("achievements") or {})
    for k, v in list((new.get("achievements") or {}).items())[:400]:
        ach.setdefault(str(k)[:40], v)
    out["achievements"] = ach
    # --- elmas defteri ---
    earned_old = int(old.get("gems_earned", 0) or 0)
    spent_old = int(old.get("gems_spent", 0) or 0)
    earned_new = int(new.get("gems_earned", 0) or 0)
    spent_new = int(new.get("gems_spent", 0) or 0)
    earned = max(earned_old, min(earned_new, earned_old + GEM_GAIN_CAP_PER_PUSH))
    spent = max(spent_old, spent_new)
    out["gems_earned"] = earned
    out["gems_spent"] = min(spent, earned)
    out["gems"] = max(0, out["gems_earned"] - out["gems_spent"])
    return out


@app.route("/player/load", methods=["POST"])
def player_load():
    """Hesabın ilerlemesini döndürür. Yeni hesapta her şey SIFIR."""
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    data = request.json or {}
    acc = _account_by_session(str(data.get("token", "")), data.get("device", ""))
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    return jsonify({"success": True, "progress": _stored_progress(_player_row(acc["id"]))})


def _log_event(account_id, kind, delta, total, note=""):
    """Oyuncunun ilerlemesindeki her değişikliği ZAMANIYLA kaydeder.

    Amaç: "bu oyuncu ne zaman kaç elmas kazandı, hangi skini ne zaman
    aldı" sorularına saniyesi saniyesine cevap verebilmek
    (bkz. player_events tablosu ve gem_history görünümü).

    Günlük yazılamazsa oyun durmaz: kayıt asıl iş değil, iz bırakmaktır.
    """
    try:
        supabase.table("player_events").insert({
            "account_id": account_id,
            "at": time.time(),
            "kind": str(kind)[:16],
            "delta": int(delta),
            "total": int(total),
            "note": str(note)[:120],
        }).execute()
    except Exception:
        pass


@app.route("/player/save", methods=["POST"])
def player_save():
    """Oyundaki ilerlemeyi hesaba yazar (birleştirerek)."""
    if not _accounts_enabled():
        return jsonify({"success": False, "error": "hesap sistemi kapalı"}), 503
    data = request.json or {}
    acc = _account_by_session(str(data.get("token", "")), data.get("device", ""))
    if not acc:
        return jsonify({"success": False, "error": "oturum geçersiz"}), 401
    incoming = data.get("progress")
    if not isinstance(incoming, dict):
        return jsonify({"success": False, "error": "ilerleme verisi yok"}), 400
    row = _player_row(acc["id"])
    before = _stored_progress(row)
    merged = _merge_progress(before, incoming)
    st = merged.get("stats") or {}
    st_before = before.get("stats") or {}
    payload = {
        "account_id": acc["id"],
        "gems": int(merged["gems"]),
        "gems_earned": int(merged["gems_earned"]),
        "gems_spent": int(merged["gems_spent"]),
        # Aşağıdaki sütunlar veritabanında TEK BAKIŞTA okunabilsin diye ayrı
        # duruyor (bkz. player_overview görünümü).
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
            supabase.table("player_data").update(payload).eq(
                "account_id", acc["id"]).execute()
        else:
            supabase.table("player_data").insert(payload).execute()
    except Exception as e:
        # HATAYI YUTMUYORUZ. Eksik bir sütun yüzünden ilerleme sessizce
        # yazılmazsa oyuncu "elmasım artmıyor" diye bakakalır; oyun bu
        # metni hesap ekranında gösteriyor.
        return jsonify({"success": False,
                        "error": "ilerleme yazılamadı: " + str(e)[:200]}), 500

    # ---- OLAY GÜNLÜĞÜ ----
    d_gem = int(merged["gems_earned"]) - int(before.get("gems_earned", 0) or 0)
    if d_gem:
        _log_event(acc["id"], "gem", d_gem, merged["gems"], "kazanıldı")
    d_spent = int(merged["gems_spent"]) - int(before.get("gems_spent", 0) or 0)
    if d_spent:
        _log_event(acc["id"], "gem", -d_spent, merged["gems"], "harcandı")
    new_skins = [x for x in (merged.get("skins_owned") or [])
                 if x not in (before.get("skins_owned") or [])]
    for sk in new_skins[:20]:
        _log_event(acc["id"], "skin", 1, len(merged.get("skins_owned") or []), sk)
    new_cos = [x for x in (merged.get("cosmetics_owned") or [])
               if x not in (before.get("cosmetics_owned") or [])]
    for cs in new_cos[:20]:
        _log_event(acc["id"], "kostum", 1, len(merged.get("cosmetics_owned") or []), cs)
    d_runs = int(st.get("runs", 0) or 0) - int(st_before.get("runs", 0) or 0)
    if d_runs > 0:
        _log_event(acc["id"], "kosu", d_runs, int(st.get("runs", 0) or 0),
                   "en iyi skor %d" % int(st.get("best_score", 0) or 0))
    return jsonify({"success": True, "progress": merged})


@app.route("/auth/logout", methods=["POST"])
def auth_logout():
    if not _accounts_enabled():
        return jsonify({"success": True})
    tok = str((request.json or {}).get("token", ""))
    if tok:
        try:
            supabase.table("sessions").delete().eq(
                "token_hash", _token_hash(tok)).execute()
        except Exception:
            pass
    return jsonify({"success": True})


# =====================================================================
# HİLE KORUMASI  (sunucu tarafı — ASIL koruma burasıdır)
# ---------------------------------------------------------------------
# İstemcide çalışan hiçbir koruma mutlak değildir: oyunun dosyası açılabilir,
# yerleşik anahtar çıkarılabilir. Dünya sıralamasının temizliği bu yüzden
# SUNUCUDA karara bağlanır. Üç süzgeç var:
#
#   1) İMZA       — gönderi, oyunun bildiği gizli anahtarla imzalanmış
#                   olmalı. İmzasız/yanlış imzalı istek (örn. elle atılan
#                   bir curl) hiç değerlendirilmez.
#   2) MAKULLÜK   — skor; öldürme sayısı, dalga ve süreyle TUTARLI olmalı.
#                   Oyunun kendi kuralları içinde üretilemeyecek bir skor
#                   reddedilir. Bu süzgeç anahtarı çalmış birini de yakalar:
#                   imzayı taklit etse bile 10 milyonluk skoru 12 saniyede
#                   üretemez.
#   3) HIZ SINIRI — aynı kaynaktan dakikalar içinde yağdırılan gönderiler
#                   kesilir.
#
# ÖNEMLİ: SUBMIT_SECRET ortam değişkeninden okunur ve oyundaki değerle AYNI
# olmalıdır (kasma_arena13.py / SUBMIT_SECRET). Yayına çıkmadan önce ikisi
# birden değiştirilmelidir; buradaki varsayılan yalnızca geliştirme içindir.
# =====================================================================

SUBMIT_SECRET = os.environ.get("KASMA_SUBMIT_SECRET",
                               "kasma-arena-submit-v1:3d7f90ac41be6528")
# İmza zorunlu mu? Eski istemcilerin bir süre çalışabilmesi için kapatılabilir.
REQUIRE_SIGNATURE = os.environ.get("KASMA_REQUIRE_SIG", "1") == "1"

# --- MAKULLÜK SINIRLARI ---
# Hepsi oyunun kendi eğrilerinden türetildi ve dürüst bir oyuncunun asla
# takılmayacağı kadar geniş bırakıldı.
MAX_SCORE_PER_KILL = 900.0     # bir öldürmeden çıkabilecek en yüksek skor
MAX_SCORE_PER_SEC = 4000.0     # saniyede üretilebilecek en yüksek skor
MAX_KILLS_PER_SEC = 25.0       # saniyede devrilebilecek en çok yaratık
MIN_RUN_TIME = 5.0             # bundan kısa bir koşu skor üretemez
MAX_RUN_TIME = 6 * 3600.0      # 6 saatten uzun koşu kabul edilmez
MAX_WAVE = 400
MAX_SCORE = 500_000_000
SCORE_FLOOR = 6000.0           # bu skorun altında makullük aranmaz

# --- HIZ SINIRI ---
RATE_WINDOW = 300.0            # saniye
RATE_MAX = 12                  # bu pencerede aynı kaynaktan en çok kaç gönderi
_rate_hits = defaultdict(deque)
_rate_lock = threading.Lock()


def _rate_ok(key):
    now = time.time()
    with _rate_lock:
        dq = _rate_hits[key]
        while dq and now - dq[0] > RATE_WINDOW:
            dq.popleft()
        if len(dq) >= RATE_MAX:
            return False
        dq.append(now)
        # Sözlük sonsuza kadar büyümesin: boşalan anahtarları at.
        if len(_rate_hits) > 4096:
            for k in [k for k, v in _rate_hits.items() if not v]:
                _rate_hits.pop(k, None)
        return True


# Oyundaki SUBMIT_SIG_FIELDS ile BİREBİR aynı olmalı.
SUBMIT_SIG_FIELDS = ("name", "score", "kills", "wave", "run_time", "created_at", "diff")


def _expected_sig(payload):
    """İmza, istemcideki sign_submit() ile BİREBİR aynı sırayı kullanır."""
    msg = "|".join(str(payload.get(k, "")) for k in SUBMIT_SIG_FIELDS)
    return hmac.new(SUBMIT_SECRET.encode("utf-8"), msg.encode("utf-8"),
                    hashlib.sha256).hexdigest()


def _wave_goal(wave):
    """Oyundaki dalga skor hedefinin kaba karşılığı (bkz. wave_score_goal).

    Birebir aynı olması gerekmez; burada yalnızca ÜST SINIR için kullanılıyor,
    o yüzden bilerek CÖMERT.
    """
    w = max(1, int(wave))
    table = {1: 600, 2: 2300, 3: 2900, 4: 3500, 5: 4100}
    if w in table:
        return table[w]
    return 4100 + 5.9 * (w - 5) * (900 + 60 * (w - 5))


def score_is_plausible(name, score, kills, wave, run_time):
    """Gönderilen skor oyunun kuralları içinde üretilebilir mi?

    Dönüş: (uygun_mu, sebep)
    """
    if not (0 <= score <= MAX_SCORE):
        return False, "skor aralık dışı"
    if not (0 <= kills <= 2_000_000):
        return False, "öldürme sayısı aralık dışı"
    if not (1 <= wave <= MAX_WAVE):
        return False, "dalga aralık dışı"
    if not (0 < run_time <= MAX_RUN_TIME):
        return False, "süre aralık dışı"
    if score < SCORE_FLOOR:
        return True, ""
    if run_time < MIN_RUN_TIME:
        return False, "koşu süresi skora göre çok kısa"
    if kills > MAX_KILLS_PER_SEC * run_time + 50:
        return False, "öldürme sayısı süreye göre imkânsız"
    if score > MAX_SCORE_PER_KILL * (kills + 10):
        return False, "skor öldürme sayısına göre imkânsız"
    if score / run_time > MAX_SCORE_PER_SEC:
        return False, "saniyelik skor imkânsız"
    goal_sum = sum(_wave_goal(w) for w in range(1, int(wave) + 2))
    if score > goal_sum * 2.5 + SCORE_FLOOR:
        return False, "skor ulaşılan dalgaya göre imkânsız"
    return True, ""


# --- 1. SKOR TABLOSU ENDPOINT'LERİ (Liderlik Tablosu) ---

@app.route("/scores", methods=["GET"])
def get_scores():
    if not supabase:
        return jsonify({"error": "Supabase bağlantısı yapılandırılmamış!"}), 500
    try:
        response = supabase.table("scores").select("*").order("score", desc=True).limit(10).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/submit", methods=["POST"])
def add_score():
    if not supabase:
        return jsonify({"error": "Supabase bağlantısı yapılandırılmamış!"}), 500
    try:
        data = request.json or {}
        name = str(data.get("name", "Anonim"))[:14]
        score = int(data.get("score", 0))
        kills = int(data.get("kills", 0))
        wave = int(data.get("wave", 0))
        run_time = float(data.get("run_time", 0))
        created_at = float(data.get("created_at", 0))
        # ZORLUK: sıralamada görünür, o yüzden imzanın içinde. Bilinmeyen bir
        # değer gelirse "normal" sayılır (uydurma etiket yazılamasın).
        diff = str(data.get("diff", "normal"))
        if diff not in ("normal", "hard", "nightmare"):
            diff = "normal"

        # ---- SÜZGEÇ 3: HIZ SINIRI ----
        src = request.headers.get("X-Forwarded-For", request.remote_addr or "?")
        src = src.split(",")[0].strip()
        if not _rate_ok(src):
            return jsonify({"success": False, "error": "çok sık gönderim"}), 429

        # ---- SÜZGEÇ 1: İMZA ----
        if REQUIRE_SIGNATURE:
            sig = str(data.get("sig") or "")
            want = _expected_sig({
                "name": name, "score": score, "kills": kills, "wave": wave,
                "run_time": run_time, "created_at": created_at,
                "diff": str(data.get("diff", "normal")),
            })
            if not sig or not hmac.compare_digest(sig, want):
                return jsonify({"success": False, "error": "imza doğrulanamadı"}), 403

        # ---- SÜZGEÇ 2: MAKULLÜK ----
        ok, why = score_is_plausible(name, score, kills, wave, run_time)
        if not ok:
            return jsonify({"success": False, "error": f"skor reddedildi: {why}"}), 422

        # ---- HESAP ZORUNLU ----
        # DÜNYA SIRALAMASI yalnızca giriş yapmış oyunculara açık. Sebebi
        # tek cümleyle: sıralamadaki bir ad kime aitse onda kalsın ve
        # hileci bir hesapla birlikte engellenebilsin. Girişsiz oynayan
        # oyuncu oyunun tamamını oynar, skoru yalnızca KENDİ bilgisayarındaki
        # yerel tabloya yazılır (oyun bunu sonuç ekranında söylüyor).
        acc = _account_by_session(str(data.get("token", "")), data.get("device", ""))
        if not acc:
            return jsonify({"success": False,
                            "error": "dünya sıralaması için giriş gerekli"}), 401
        if not acc.get("username"):
            return jsonify({"success": False,
                            "error": "önce kullanıcı adı seçmelisin"}), 409
        account_id = acc.get("id")
        # Ad SUNUCUDAN gelir, istemciden değil: kimse başkasının adıyla
        # skor gönderemez.
        name = str(acc.get("username"))[:14]

        payload = {
            "name": name,
            "score": score,
            "kills": kills,
            "wave": wave,
            "run_time": run_time,
            "created_at": created_at,
            "diff": diff,
        }
        if account_id is not None:
            payload["account_id"] = account_id

        response = supabase.table("scores").insert(payload).execute()
        return jsonify({"success": True, "data": response.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- 2. STEAM OYUNCU & İLERLEME ENDPOINT'LERİ (Gems, Skinler vb.) ---

@app.route("/get_player", methods=["POST"])
def get_player():
    if not supabase:
        return jsonify({"error": "Supabase bağlantısı yok!"}), 500
    try:
        data = request.json
        steam_id = data.get("steam_id")
        name = data.get("name", "Steam Oyuncusu")
        
        if not steam_id:
            return jsonify({"error": "steam_id gereklidir!"}), 400

        # Oyuncuyu benzersiz steam_id'si ile veritabanında arıyoruz
        response = supabase.table("players").select("*").eq("steam_id", steam_id).execute()
        
        if response.data and len(response.data) > 0:
            return jsonify({"success": True, "data": response.data[0]})
        else:
            # Oyuncu ilk defa giriyorsa sıfır elmas ve default skinle kayıt açıyoruz
            new_player = {
                "steam_id": steam_id,
                "name": name,
                "gems": 0,
                "skins": "default",
                "selected_skin": "default"
            }
            ins_res = supabase.table("players").insert(new_player).execute()
            return jsonify({"success": True, "data": ins_res.data[0]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/update_player", methods=["POST"])
def update_player():
    if not supabase:
        return jsonify({"error": "Supabase bağlantısı yok!"}), 500
    try:
        data = request.json or {}
        steam_id = data.get("steam_id")
        selected_skin = data.get("selected_skin")

        if not steam_id:
            return jsonify({"error": "steam_id gereklidir!"}), 400

        # HİLE KORUMASI: bu uç nokta ARTIK "gems" ve "skins" KABUL ETMİYOR.
        # Eskiden istemci kendi elmas sayısını ve sahip olduğu skinleri
        # doğrudan yazabiliyordu; yani oyunu hiç açmadan atılan tek bir
        # istekle sınırsız elmas yazdırmak mümkündü. Elmas yalnızca
        # /finalize_purchase içinde (Steam ödemeyi onayladıktan SONRA)
        # sunucu tarafında artar; skin sahipliği de aynı yoldan yazılır.
        # Burada yalnızca KUŞANILAN skin değişebilir ve o da oyuncunun
        # gerçekten sahip olduğu skinlerden biri olmalıdır.
        payload = {}
        if selected_skin is not None:
            row = supabase.table("players").select("skins").eq(
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
        response = supabase.table("players").update(payload).eq("steam_id", steam_id).execute()
        return jsonify({"success": True, "data": response.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =====================================================================
# 3. ELMAS SATIN ALMA  (Steam Microtransactions / ISteamMicroTxn)
# ---------------------------------------------------------------------

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
    if not _purchases_enabled():
        return jsonify({
            "success": False,
            "message": "Satın alma yapılandırılmamış (STEAM_PUBLISHER_KEY / STEAM_APP_ID eksik).",
        }), 503
    try:
        data = request.json or {}
        steam_id = str(data.get("steam_id") or "").strip()
        item_id = int(data.get("item_id") or 0)
        if not steam_id.isdigit():
            return jsonify({"success": False, "message": "Geçersiz steam_id"}), 400
        if item_id not in GEM_PACKS:
            return jsonify({"success": False, "message": "Bilinmeyen paket"}), 400

        gems, desc, amount, currency = GEM_PACKS[item_id]
        orderid = uuid.uuid4().int >> 76        # 52 bitlik benzersiz sipariş no

        supabase.table("purchases").insert({
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
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/finalize_purchase", methods=["POST"])
def finalize_purchase():
    if not _purchases_enabled():
        return jsonify({"success": False, "message": "Satın alma yapılandırılmamış."}), 503
    try:
        data = request.json or {}
        orderid = str(data.get("orderid") or "").strip()
        if not orderid.isdigit():
            return jsonify({"success": False, "message": "Geçersiz orderid"}), 400

        rows = supabase.table("purchases").select("*").eq("orderid", orderid).execute()
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
            supabase.table("purchases").update({"status": "failed"}).eq("orderid", orderid).execute()
            return jsonify({"success": False, "message": "Steam ödemeyi onaylamadı."}), 402

        steam_id = order["steam_id"]
        gems = int(order["gems"])
        pl = supabase.table("players").select("gems").eq("steam_id", steam_id).execute()
        cur = int(pl.data[0]["gems"]) if pl.data else 0
        supabase.table("players").update({"gems": cur + gems}).eq("steam_id", steam_id).execute()
        supabase.table("purchases").update({"status": "completed"}).eq("orderid", orderid).execute()
        return jsonify({"success": True, "gems": cur + gems,
                        "message": f"{gems} elmas hesabına eklendi."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/purchase_status", methods=["GET"])
def purchase_status():
    return jsonify({
        "enabled": _purchases_enabled(),
        "sandbox": STEAM_SANDBOX,
        "packs": {str(k): {"gems": v[0], "desc": v[1]} for k, v in GEM_PACKS.items()},
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
