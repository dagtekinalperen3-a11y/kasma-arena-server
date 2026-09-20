"""
=====================================================================
 KASMA ARENA — ONLINE SKOR SUNUCUSU
 ---------------------------------------------------------------------
 Bu, kasma_arena.py'deki "DÜNYA SIRALAMASI" özelliğinin bağlandığı
 gerçek, çalışan bir sunucudur. SQLite kullanır (ekstra veritabanı
 kurmana gerek yok), Flask ile yazılmıştır.

 UÇ NOKTALAR:
   GET  /health        -> sunucu ayakta mı kontrolü
   GET  /scores         -> en iyi 50 skoru JSON olarak döner
   POST /submit         -> yeni bir skor gönderir

 YEREL ÇALIŞTIRMA:
   pip install flask flask-cors
   python server.py
   (varsayılan olarak http://localhost:5000 üzerinde çalışır)

 SONRA kasma_arena.py içindeki ONLINE_API_URL'i doldur:
   ONLINE_API_URL = "http://localhost:5000"          (yerel test)
   ONLINE_API_URL = "https://senin-adresin.onrender.com"  (gerçek/canlı)

 ÜCRETSİZ CANLI YAYINA ALMA (özet — SERVER_README.md'de detaylı anlatım var):
   1) Bu server.py, requirements.txt dosyalarını bir GitHub reposuna koy.
   2) Render.com'da (ücretsiz plan) "New Web Service" ile bu repoyu bağla.
      Start command: gunicorn server:app
   3) Render sana https://....onrender.com şeklinde bir adres verir.
   4) O adresi ONLINE_API_URL'e yapıştır, oyunu Steam'e onunla paketle.
      Artık her oyuncunun skoru gerçekten aynı ortak tabloya düşer.
=====================================================================
"""

import os
import sqlite3
import time
from flask import Flask, request, jsonify

try:
    from flask_cors import CORS
    HAS_CORS = True
except Exception:
    HAS_CORS = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "kasma_arena_scores.db")

app = Flask(__name__)
if HAS_CORS:
    CORS(app)

MAX_NAME_LEN = 14
MAX_SCORE = 50_000_000   # mantık dışı / hileli gönderimlere karşı üst sınır


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            score INTEGER NOT NULL,
            kills INTEGER NOT NULL DEFAULT 0,
            wave INTEGER NOT NULL DEFAULT 0,
            run_time REAL NOT NULL DEFAULT 0,
            created_at REAL NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_score ON scores(score DESC)")
    conn.commit()
    conn.close()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "kasma-arena-server", "time": time.time()})


@app.route("/scores", methods=["GET"])
def get_scores():
    limit = request.args.get("limit", default=50, type=int)
    limit = max(1, min(limit, 100))
    conn = get_db()
    rows = conn.execute(
        "SELECT name, score, kills, wave, run_time, created_at "
        "FROM scores ORDER BY score DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    result = [dict(r) for r in rows]
    return jsonify(result)


@app.route("/submit", methods=["POST"])
def submit_score():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "İsimsiz")).strip()[:MAX_NAME_LEN] or "İsimsiz"
    try:
        score = int(data.get("score", 0))
        kills = int(data.get("kills", 0))
        wave = int(data.get("wave", 0))
        run_time = float(data.get("time", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Geçersiz veri türü"}), 400

    if score < 0 or score > MAX_SCORE:
        return jsonify({"ok": False, "error": "Skor sınırlar dışında"}), 400
    if kills < 0 or wave < 0 or run_time < 0:
        return jsonify({"ok": False, "error": "Negatif değerler kabul edilmiyor"}), 400

    conn = get_db()
    conn.execute(
        "INSERT INTO scores (name, score, kills, wave, run_time, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, score, kills, wave, run_time, time.time())
    )
    # Tabloyu şişirmemek için sadece en iyi 500 skoru tut
    conn.execute("""
        DELETE FROM scores WHERE id NOT IN (
            SELECT id FROM scores ORDER BY score DESC LIMIT 500
        )
    """)
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
