"""Satış akışı testleri (PHP sunucusuna HTTP ile).

    cd reklam-veriyor && python -m pytest -q tests

PHP'nin yerleşik sunucusunu 8 işçiyle başlatır; eş zamanlı rezervasyon testi
gerçekten paralel istek gönderir.
"""
import io
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import threading
import time

import pytest
import requests

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FATURA = {"name": "Ayşe Yılmaz", "phone": "0532 000 00 00", "city": "İstanbul", "address": "Örnek Mah. 1. Sok. No 2"}


def _bos_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture(scope="session")
def sunucu():
    # Hazır bir sunucuya karşı çalıştırmak için (ör. Apache):
    #   RV_TEST_ADRES=http://127.0.0.1:8089 RV_TEST_VERI=/yol/public_html/veri python -m pytest tests
    if os.environ.get("RV_TEST_ADRES"):
        yield os.environ["RV_TEST_ADRES"], os.environ["RV_TEST_VERI"]
        return
    veri = tempfile.mkdtemp(prefix="rv-veri-")
    port = _bos_port()
    env = dict(os.environ, RV_VERI_DIZINI=veri, RV_ODEME="test", RV_YONETICI_EPOSTA="yonetici@example.com",
               RV_YONETICI_SIFRE="yonetici-sifre", PHP_CLI_SERVER_WORKERS="8")
    proc = subprocess.Popen(["php", "-S", "127.0.0.1:%d" % port, "index.php"], cwd=KOK, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    adres = "http://127.0.0.1:%d" % port
    for _ in range(50):
        try:
            requests.get(adres + "/api/me", timeout=1)
            break
        except requests.ConnectionError:
            time.sleep(0.1)
    yield adres, veri
    log = os.path.join(veri, "hata.log")
    if os.path.exists(log):
        print("\n--- hata.log ---\n" + open(log).read())
    proc.terminate()
    proc.wait()
    shutil.rmtree(veri, ignore_errors=True)


def vt(veri):
    ad = re.search(r"'([^']+\.sqlite)'", open(os.path.join(veri, "veritabani-adi.php")).read()).group(1)
    c = sqlite3.connect(os.path.join(veri, ad), timeout=20, isolation_level=None)
    return c


@pytest.fixture()
def temiz(sunucu):
    adres, veri = sunucu
    requests.get(adres + "/api/me")      # şemayı oluştur
    c = vt(veri)
    for t in ("cell_locks", "orders", "slots", "stats_daily", "seen", "uploads", "rate_log"):
        c.execute("DELETE FROM " + t)
    c.execute("DELETE FROM users WHERE is_admin = 0")
    c.execute("UPDATE settings SET value = '50' WHERE key = 'price_per_pixel'")
    c.execute("UPDATE settings SET value = '30' WHERE key = 'duration_days'")
    c.close()
    zaman_ileri(veri)
    return sunucu


def zaman_ileri(veri):
    """Temizlik kısıtını sıfırla (15 sn bekleme yerine)."""
    try:
        os.remove(os.path.join(veri, ".temizlik"))
    except FileNotFoundError:
        pass


class Istemci:
    def __init__(self, adres):
        self.a = adres
        self.s = requests.Session()
        self.csrf = self.s.get(adres + "/api/me").json()["csrf"]

    def istek(self, yontem, yol, json=None, **kw):
        r = self.s.request(yontem, self.a + yol, json=json, headers={"X-CSRF-Token": self.csrf},
                           allow_redirects=False, **kw)
        try:
            d = r.json()
        except ValueError:
            d = {}
        if isinstance(d, dict) and "csrf" in d:
            self.csrf = d["csrf"]
        return r.status_code, d

    def kayit(self, eposta):
        return self.istek("POST", "/api/auth/register", {"email": eposta, "password": "gizli-sifre-1", "name": "Test"})

    def siparis(self, x, y, w, h):
        return self.istek("POST", "/api/orders", {"x": x, "y": y, "w": w, "h": h, "billing": FATURA, "accept_terms": True})

    def ode(self, ref, sonuc="success"):
        sayfa = self.s.get(self.a + "/odeme/test/" + ref).text
        token = sayfa.split('name="token" value="')[1].split('"')[0]
        return self.s.post(self.a + "/odeme/test/" + ref, data={"token": token, "result": sonuc}, allow_redirects=False)


def test_fiyat_sunucuda_hesaplanir(temiz):
    a = Istemci(temiz[0])
    a.kayit("a@example.com")
    kod, q = a.istek("POST", "/api/quote", {"x": 0, "y": 0, "w": 8, "h": 4})
    assert kod == 200, q
    assert q["width_px"] == 120 and q["height_px"] == 60
    assert q["pixels"] == 7200
    assert q["amount"] == 7200 * 50          # varsayılan 0,50 TL/piksel
    assert q["duration_days"] == 30


def test_ayni_alan_iki_kisiye_satilmaz(temiz):
    a, b = Istemci(temiz[0]), Istemci(temiz[0])
    a.kayit("a@example.com")
    b.kayit("b@example.com")
    kod, o = a.siparis(10, 10, 4, 4)
    assert kod == 200, o
    kod, hata = b.siparis(12, 12, 4, 4)      # çakışan alan
    assert kod == 409, hata
    assert b.siparis(14, 10, 2, 2)[0] == 200  # bitişik ama çakışmayan alan
    pano = Istemci(temiz[0]).istek("GET", "/api/board")[1]
    assert any(t["state"] == "reserved" and t["x"] == 10 for t in pano["taken"])


def test_es_zamanli_istekler_tek_kazanan(temiz):
    istemciler = [Istemci(temiz[0]) for _ in range(8)]
    for i, cl in enumerate(istemciler):
        assert cl.kayit("p%d@example.com" % i)[0] == 200
    sonuclar = []
    engel = threading.Barrier(len(istemciler))

    def calis(cl):
        engel.wait()
        sonuclar.append(cl.siparis(40, 20, 5, 5)[0])
    ipler = [threading.Thread(target=calis, args=(cl,)) for cl in istemciler]
    for t in ipler:
        t.start()
    for t in ipler:
        t.join()
    assert sorted(sonuclar) == [200] + [409] * 7, sonuclar
    c = vt(temiz[1])
    assert c.execute("SELECT COUNT(*) FROM cell_locks").fetchone()[0] == 25


def test_odeme_onayi_alani_hesaba_baglar(temiz):
    a = Istemci(temiz[0])
    a.kayit("a@example.com")
    kod, o = a.siparis(0, 0, 6, 4)
    assert o["redirect_url"].startswith("/odeme/test/")
    r = a.ode(o["ref"])
    assert r.status_code == 303 and "sonuc=success" in r.headers["Location"]
    my = a.istek("GET", "/api/my")[1]
    assert len(my["slots"]) == 1
    s = my["slots"][0]
    assert (s["x"], s["y"], s["w"], s["h"]) == (0, 0, 6, 4)
    assert my["orders"][0]["status"] == "paid"
    b = Istemci(temiz[0])
    b.kayit("b@example.com")
    assert b.siparis(5, 3, 2, 2)[0] == 409


def test_odeme_tamamlanmazsa_rezervasyon_biter(temiz):
    adres, veri = temiz
    a, b = Istemci(adres), Istemci(adres)
    a.kayit("a@example.com")
    b.kayit("b@example.com")
    kod, o = a.siparis(20, 20, 3, 3)
    assert kod == 200
    c = vt(veri)
    token = c.execute("SELECT provider_token FROM orders WHERE ref = ?", (o["ref"],)).fetchone()[0]
    c.execute("UPDATE orders SET expires_at = expires_at - 3600 WHERE ref = ?", (o["ref"],))
    c.execute("UPDATE cell_locks SET expires_at = expires_at - 3600")
    zaman_ileri(veri)
    pano = b.istek("GET", "/api/board")[1]
    assert not any(t["state"] == "reserved" for t in pano["taken"])
    assert c.execute("SELECT status FROM orders WHERE ref = ?", (o["ref"],)).fetchone()[0] == "expired"
    assert b.siparis(20, 20, 3, 3)[0] == 200
    # süre dolunca test ödeme sayfası formu göstermez
    assert 'name="token"' not in a.s.get(adres + "/odeme/test/" + o["ref"]).text
    # ödeme yine de geç gelirse alan A'ya verilmez, para iade edilir
    r = a.s.post(adres + "/odeme/test/" + o["ref"], data={"token": token, "result": "success"}, allow_redirects=False)
    assert r.status_code == 303, (r.status_code, r.text[:300])
    assert c.execute("SELECT status FROM orders WHERE ref = ?", (o["ref"],)).fetchone()[0] == "refunded"
    assert c.execute("SELECT COUNT(*) FROM slots").fetchone()[0] == 0


def test_gec_odeme_alan_bossa_tamamlanir(temiz):
    adres, veri = temiz
    a = Istemci(adres)
    a.kayit("a@example.com")
    kod, o = a.siparis(30, 30, 2, 2)
    c = vt(veri)
    token = c.execute("SELECT provider_token FROM orders WHERE ref = ?", (o["ref"],)).fetchone()[0]
    c.execute("UPDATE cell_locks SET expires_at = 1")
    c.execute("UPDATE orders SET expires_at = 1")
    a.s.post(adres + "/odeme/test/" + o["ref"], data={"token": token, "result": "success"}, allow_redirects=False)
    my = a.istek("GET", "/api/my")[1]
    assert my["orders"][0]["status"] == "paid" and len(my["slots"]) == 1


def test_basarisiz_odeme_alani_birakir(temiz):
    a = Istemci(temiz[0])
    a.kayit("a@example.com")
    kod, o = a.siparis(60, 20, 3, 3)
    r = a.ode(o["ref"], "failure")
    assert "sonuc=failure" in r.headers["Location"]
    assert a.istek("GET", "/api/orders/" + o["ref"])[1]["order"]["status"] == "failed"
    b = Istemci(temiz[0])
    b.kayit("b@example.com")
    assert b.siparis(60, 20, 3, 3)[0] == 200


def test_yayinla_gosterim_tiklama(temiz):
    adres, veri = temiz
    a = Istemci(adres)
    a.kayit("a@example.com")
    kod, o = a.siparis(0, 0, 10, 6)
    a.ode(o["ref"])
    slot = a.istek("GET", "/api/my")[1]["slots"][0]
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (300, 180), "#3366ff").save(buf, "PNG")
    buf.seek(0)
    r = a.s.post(adres + "/api/upload", files={"file": ("a.png", buf, "image/png")}, headers={"X-CSRF-Token": a.csrf})
    assert r.status_code == 200, r.text
    img = r.json()["image"]
    assert a.s.get(adres + "/u/" + img).headers["Content-Type"].startswith("image/")
    # görsel olmayan dosya reddedilir
    r = a.s.post(adres + "/api/upload", files={"file": ("x.png", io.BytesIO(b"<?php echo 1; ?>"), "image/png")},
                 headers={"X-CSRF-Token": a.csrf})
    assert r.status_code == 400
    kod, hata = a.istek("POST", "/api/slots/%d/publish" % slot["id"],
                        {"image": img, "button_text": "Ürünü İncele", "url": "javascript:alert(1)"})
    assert kod == 400
    kod, res = a.istek("POST", "/api/slots/%d/publish" % slot["id"],
                       {"image": img, "button_text": "Ürünü İncele", "url": "ornek.com.tr/urun", "title": "Ürün"})
    assert kod == 200, res
    pano = Istemci(adres).istek("GET", "/api/board")[1]
    ad = [x for x in pano["ads"] if x["id"] == slot["id"]][0]
    assert ad["button_text"] == "Ürünü İncele" and ad["display_url"] == "ornek.com.tr/urun"
    v = Istemci(adres)
    v.s.post(adres + "/api/track", json={"ids": [slot["id"]], "v": "ziyaretci1"})
    v.s.post(adres + "/api/track", json={"ids": [slot["id"]], "v": "ziyaretci1"})   # tekrar sayılmaz
    r = v.s.get(adres + "/r/%d" % slot["id"], allow_redirects=False)
    assert r.status_code == 302 and r.headers["Location"] == "https://ornek.com.tr/urun"
    st = a.istek("GET", "/api/slots/%d/stats" % slot["id"])[1]
    assert st["impressions"] == 1 and st["clicks"] == 1


def test_baskasinin_alanini_duzenleyemez(temiz):
    a, b = Istemci(temiz[0]), Istemci(temiz[0])
    a.kayit("a@example.com")
    b.kayit("b@example.com")
    kod, o = a.siparis(0, 0, 2, 2)
    a.ode(o["ref"])
    sid = a.istek("GET", "/api/my")[1]["slots"][0]["id"]
    assert b.istek("POST", "/api/slots/%d/publish" % sid, {"url": "x.com"})[0] == 404


def test_yonetici_fiyat_ve_sure_ayarlar(temiz):
    y = Istemci(temiz[0])
    assert y.istek("POST", "/api/auth/login", {"email": "yonetici@example.com", "password": "yonetici-sifre"})[0] == 200
    kod, res = y.istek("POST", "/api/admin/settings", {"price_per_pixel": 125, "duration_days": 90})
    assert kod == 200, res
    q = y.istek("POST", "/api/quote", {"x": 0, "y": 0, "w": 1, "h": 1})[1]
    assert q["amount"] == 225 * 125 and q["duration_days"] == 90
    u = Istemci(temiz[0])
    u.kayit("u@example.com")
    assert u.istek("POST", "/api/admin/settings", {"price_per_pixel": 1})[0] == 403
    assert y.istek("GET", "/api/admin/overview")[0] == 200


def test_sure_uzatma(temiz):
    a = Istemci(temiz[0])
    a.kayit("a@example.com")
    kod, o = a.siparis(70, 40, 2, 2)
    a.ode(o["ref"])
    s = a.istek("GET", "/api/my")[1]["slots"][0]
    kod, r = a.istek("POST", "/api/slots/%d/renew" % s["id"], {"billing": FATURA, "accept_terms": True})
    assert kod == 200, r
    a.ode(r["ref"])
    s2 = a.istek("GET", "/api/my")[1]["slots"][0]
    assert s2["ends_at"] - s["ends_at"] == 30 * 86400


def test_csrf_olmadan_islem_yapilamaz(temiz):
    a = Istemci(temiz[0])
    a.kayit("a@example.com")
    r = a.s.post(temiz[0] + "/api/orders", json={"x": 0, "y": 0, "w": 1, "h": 1})
    assert r.status_code == 403


def test_demo_yukle_ve_kaldir(temiz):
    y = Istemci(temiz[0])
    y.istek("POST", "/api/auth/login", {"email": "yonetici@example.com", "password": "yonetici-sifre"})
    kod, r = y.istek("POST", "/api/admin/demo/load")
    assert kod == 200 and r["added"] == 34, r
    assert len(Istemci(temiz[0]).istek("GET", "/api/board")[1]["ads"]) == 34
    kod, r = y.istek("POST", "/api/admin/demo/remove")
    assert r["removed"] == 34
    assert Istemci(temiz[0]).istek("GET", "/api/board")[1]["ads"] == []
