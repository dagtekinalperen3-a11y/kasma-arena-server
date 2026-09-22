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

# Oyunun skorları çektiği adres (/scores)
@app.route("/scores", methods=["GET"])
def get_scores():
    if not supabase:
        return jsonify({"error": "Supabase bağlantısı yapılandırılmamış!"}), 500
    try:
        response = supabase.table("scores").select("*").order("score", desc=True).limit(10).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Oyunun skoru kaydettiği adres (/submit)
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
