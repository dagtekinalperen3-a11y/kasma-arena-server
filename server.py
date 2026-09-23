import os
import requests
from flask import Flask, jsonify, request
from supabase import Client, create_client

app = Flask(__name__)

# Supabase Bilgilerin (Kendi bilgilerini buraya koyarsın)
SUPABASE_URL = "SENIN_SUPABASE_URL"
SUPABASE_KEY = "SENIN_SUPABASE_KEY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# AYARLAR (Yayın günü sadece burayı değiştireceksin)
# ==========================================
DEV_MODE = True  # Şu an test için True. Yayın günü False yapacaksın!
STEAM_API_KEY = "BURAYA_VALVE_API_KEY_GELECEK"
STEAM_APP_ID = "480"  # Test için 480, kendi oyunun çıkınca gerçek App ID


def steam_biletini_dogrula(steam_id, ticket):
  """Valve Web API kullanarak biletin gerçek olup olmadığını doğrular."""
  if DEV_MODE:
    return True  # Test modundaysak Valve'a sormadan direkt onay ver

  url = "https://partner.steam-api.com/ISteamUserAuth/AuthenticateUserTicket/v1/"
  params = {
      "key": STEAM_API_KEY,
      "appid": STEAM_APP_ID,
      "ticket": ticket,
  }

  try:
    response = requests.get(url, params=params)
    data = response.json()
    # Valve'dan gelen yanıtta kullanıcı ID'si eşleşiyor mu kontrol et
    if "response" in data and "params" in data["response"]:
      gercek_id = data["response"]["params"].get("steamid")
      if str(gercek_id) == str(steam_id):
        return True
  except Exception as e:
    print(f"Steam API Bağlantı Hatası: {e}")

  return False


@app.route("/get_player", methods=["POST"])
def get_player():
  data = request.json
  steam_id = data.get("steam_id")
  ticket = data.get("ticket", "")

  if not steam_id:
    return jsonify({"error": "Steam ID bulunamadı!"}), 400

  # Güvenlik Kontrolü (DEV_MODE kapalıysa bilet kontrolü yapılır)
  if not DEV_MODE:
    if not steam_biletini_dogrula(steam_id, ticket):
      return jsonify({"error": "Steam kimlik doğrulaması başarısız! Hile engellendi."}), 403

  # Supabase'den oyuncuyu sorgula
  response = supabase.table("players").select("*").eq("steam_id", steam_id).execute()

  if response.data and len(response.data) > 0:
    # Oyuncu zaten var, verilerini döndür
    return jsonify(response.data[0]), 200
  else:
    # Oyuncu ilk defa giriyor, yeni kayıt aç (100 Elmas + Default Skin)
    yeni_oyuncu = {
        "steam_id": steam_id,
        "gems": 100,
        "selected_skin": "default",
        "skins": ["default"],
    }
    insert_res = supabase.table("players").insert(yeni_oyuncu).execute()
    return jsonify(insert_res.data[0]), 200


@app.route("/update_player", methods=["POST"])
def update_player():
  data = request.json
  steam_id = data.get("steam_id")
  gems = data.get("gems")
  selected_skin = data.get("selected_skin")
  skins = data.get("skins")

  if not steam_id:
    return jsonify({"error": "Steam ID eksik!"}), 400

  # Güncellenecek veriler
  guncelleme = {}
  if gems is not None:
    guncelleme["gems"] = gems
  if selected_skin is not None:
    guncelleme["selected_skin"] = selected_skin
  if skins is not None:
    guncelleme["skins"] = skins

  # Supabase'de güncelle
  supabase.table("players").update(guncelleme).eq("steam_id", steam_id).execute()

  return jsonify({"status": "success", "message": "Veriler güncellendi!"}), 200


if __name__ == "__main__":
  app.run(port=5000, debug=True)
