import os
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

@app.route("/get_player", methods=["GET", "POST"])
def get_player():
    if not supabase:
        return jsonify({"error": "Supabase bağlantısı yok!"}), 500
    try:
        # İster GET parametresiyle ister POST json ile gelsin, steam_id ve name'i alalım
        if request.method == "GET":
            steam_id = request.args.get("steam_id")
            name = request.args.get("name", "Steam Oyuncusu")
        else:
            data = request.json or {}
            steam_id = data.get("steam_id")
            name = data.get("name", "Steam Oyuncusu")
        
        if not steam_id:
            return jsonify({"error": "steam_id gereklidir!"}), 400

        # Oyuncuyu benzersiz steam_id'si ile veritabanında arıyoruz
        response = supabase.table("players").select("*").eq("steam_id", steam_id).execute()
        
        if response.data and len(response.data) > 0:
            return jsonify({"success": True, "data": response.data[0]})
        else:
            # Yeni gelen oyuncu (veya test oyuncusu) veritabanında yoksa 100 puan/elmas ile kaydediyoruz[cite: 1]
            new_player = {
                "steam_id": steam_id,
                "name": name,
                "gems": 100,
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

        # Steam ID'ye göre oyuncunun verilerini güvenle güncelliyoruz[cite: 1]
        response = supabase.table("players").update(payload).eq("steam_id", steam_id).execute()
        return jsonify({"success": True, "data": response.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
