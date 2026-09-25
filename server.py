import os
import json
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
        data = request.json
        name = data.get("name", "Anonim")
        score = int(data.get("score", 0))
        kills = int(data.get("kills", 0))
        wave = int(data.get("wave", 0))
        run_time = float(data.get("run_time", 0))
        created_at = float(data.get("created_at", 0))

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
        data = request.json
        steam_id = data.get("steam_id")
        gems = data.get("gems")
        selected_skin = data.get("selected_skin")
        skins = data.get("skins")
        
        if not steam_id:
            return jsonify({"error": "steam_id gereklidir!"}), 400

        payload = {}
        if gems is not None:
            payload["gems"] = int(gems)
        if selected_skin is not None:
            payload["selected_skin"] = selected_skin
        if skins is not None:
            payload["skins"] = skins

        # Steam ID'ye göre oyuncunun verilerini güvenle güncelliyoruz
        response = supabase.table("players").update(payload).eq("steam_id", steam_id).execute()
        return jsonify({"success": True, "data": response.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =====================================================================
# 3. ELMAS SATIN ALMA  (Steam Microtransactions / ISteamMicroTxn)
# ---------------------------------------------------------------------
# KURULUM — bu üç ortam değişkeni ayarlanmadan satın alma ÇALIŞMAZ:
#
#   STEAM_PUBLISHER_KEY : Steamworks > Kullanıcılar ve İzinler > Publisher WebAPI Key
#                         !!! Bu anahtar ASLA oyunun içine konmamalıdır. Oyun
#                         dosyası açılabilir ve anahtar çalınabilir; çalan kişi
#                         mağazan üzerinde işlem yapabilir.
#   STEAM_APP_ID        : Oyunun Steam App ID'si
#   STEAM_MICROTXN_SANDBOX : "1" ise Steam'in test (sandbox) ucu kullanılır.
#
# Ayrıca Steamworks panelinde her paket için bir "item id" tanımlaman ve
# aşağıdaki GEM_PACKS tablosunu oyundaki GEM_PACKS ile BİREBİR eşlemen gerekir.
# Fiyat bilgisi Steam'de tanımlıdır; buradaki `amount` (kuruş cinsinden) ile
# Steam'deki fiyat uyuşmazsa Steam işlemi reddeder.
#
# AKIŞ:
#   1) Oyun  -> POST /begin_purchase   {steam_id, item_id}
#   2) Sunucu-> Steam InitTxn          (sipariş oluşur, Steam istemcisinde pencere açılır)
#   3) Oyuncu Steam penceresinde onaylar
#   4) Oyun  -> POST /finalize_purchase {orderid}
#   5) Sunucu-> Steam FinalizeTxn      ve BAŞARILIYSA elmas hesaba yazılır
#
# Elmaslar YALNIZCA 5. adımda, Steam işlemi onayladıktan sonra yazılır.
# =====================================================================

import time
import uuid
import urllib.parse
import urllib.request

STEAM_PUBLISHER_KEY = os.environ.get("STEAM_PUBLISHER_KEY")
STEAM_APP_ID = os.environ.get("STEAM_APP_ID")
STEAM_SANDBOX = os.environ.get("STEAM_MICROTXN_SANDBOX") == "1"

_MICROTXN_BASE = ("https://partner.steam-api.com/ISteamMicroTxnSandbox"
                  if STEAM_SANDBOX else
                  "https://partner.steam-api.com/ISteamMicroTxn")

# item_id -> (elmas, açıklama, kuruş cinsinden fiyat, para birimi)
# Oyundaki GEM_PACKS ile aynı id'leri ve aynı elmas miktarlarını kullanmalı.
GEM_PACKS = {
    1001: (500,  "500 Elmas",   2900,  "TRY"),
    1002: (1320, "1.320 Elmas", 5900,  "TRY"),
    1003: (3120, "3.120 Elmas", 11900, "TRY"),
    1004: (9450, "9.450 Elmas", 27900, "TRY"),
}


def _purchases_enabled():
    return bool(STEAM_PUBLISHER_KEY and STEAM_APP_ID and supabase)


def _steam_post(endpoint, fields):
    """Steam MicroTxn ucuna form-encoded POST atar ve JSON döndürür."""
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(_MICROTXN_BASE + endpoint, data=data)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


@app.route("/begin_purchase", methods=["POST"])
def begin_purchase():
    """Satın almayı başlatır: Steam'de ödeme penceresini açtırır."""
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
        orderid = uuid.uuid4().int >> 76          # 52 bitlik benzersiz sipariş no

        # Siparişi ÖNCE kendi veritabanımıza "beklemede" olarak yazıyoruz;
        # böylece Steam onayladığında hangi hesaba ne yazacağımızı biliyoruz.
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
    """Oyuncu Steam penceresinde onayladıktan sonra çağrılır.

    Elmaslar YALNIZCA burada, Steam FinalizeTxn "OK" dönerse yazılır.
    """
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
            # Aynı sipariş iki kez elmas yazmasın (tekrar gönderime karşı koruma).
            return jsonify({"success": True, "message": "Sipariş zaten tamamlanmış."})

        res = _steam_post("/FinalizeTxn/v2/", {
            "key": STEAM_PUBLISHER_KEY,
            "orderid": orderid,
            "appid": STEAM_APP_ID,
        })
        if res.get("response", {}).get("result") != "OK":
            supabase.table("purchases").update({"status": "failed"}).eq("orderid", orderid).execute()
            return jsonify({"success": False, "message": "Steam ödemeyi onaylamadı."}), 402

        # --- elmasları hesaba yaz ---
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
    """Satın almanın açık olup olmadığını söyler (oyun bunu gösterir)."""
    return jsonify({
        "enabled": _purchases_enabled(),
        "sandbox": STEAM_SANDBOX,
        "packs": {str(k): {"gems": v[0], "desc": v[1]} for k, v in GEM_PACKS.items()},
    })



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
