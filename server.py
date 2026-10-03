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


def _expected_sig(payload):
    """İmza, istemcideki sign_submit() ile BİREBİR aynı sırayı kullanır."""
    msg = "|".join(str(payload.get(k, "")) for k in
                   ("name", "score", "kills", "wave", "run_time", "created_at"))
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
            })
            if not sig or not hmac.compare_digest(sig, want):
                return jsonify({"success": False, "error": "imza doğrulanamadı"}), 403

        # ---- SÜZGEÇ 2: MAKULLÜK ----
        ok, why = score_is_plausible(name, score, kills, wave, run_time)
        if not ok:
            return jsonify({"success": False, "error": f"skor reddedildi: {why}"}), 422

        payload = {
            "name": name,
            "score": score,
            "kills": kills,
            "wave": wave,
            "run_time": run_time,
            "created_at": created_at
        }
        
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
