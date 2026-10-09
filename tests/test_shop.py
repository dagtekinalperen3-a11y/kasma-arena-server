"""Mağaza (TL ile satın alma) uçtan uca testleri — sahte Supabase ile.

    python -m pytest tests/test_shop.py -q      (ya da: python tests/test_shop.py)

Gerçek ağa çıkmaz: Supabase bellekte taklit edilir, iyzico çağrısı
yerine sahte bir cevap verilir. Denenenler: sipariş açma, deneme (mock)
ödemesiyle teslim, ÇİFT TESLİM olmaması, özel PET tasarımı süzgeci,
başkasının siparişini görememe, iyzico tutar/sepet denetimi, Shopier imzası.
"""
import os
import sys
import types
import json
import copy
import base64
import hmac
import hashlib
import importlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


# ---------------- sahte Supabase ----------------
class _Res:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.op, self.payload, self.filters, self._limit = "select", None, [], None

    def select(self, *_a):
        self.op = "select"
        return self

    def insert(self, row):
        self.op, self.payload = "insert", row
        return self

    def update(self, fields):
        self.op, self.payload = "update", fields
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def limit(self, n):
        self._limit = n
        return self

    def _match(self, row):
        return all(str(row.get(c)) == str(v) for c, v in self.filters)

    def execute(self):
        rows = self.db.setdefault(self.table, [])
        if self.op == "insert":
            row = copy.deepcopy(self.payload)
            if self.table == "accounts" and "id" not in row:
                row["id"] = "acc-%d" % (len(rows) + 1)     # gerçek tabloda varsayılan uuid
            rows.append(row)
            return _Res([copy.deepcopy(row)])
        hit = [r for r in rows if self._match(r)]
        if self.op == "select":
            out = copy.deepcopy(hit[: self._limit] if self._limit else hit)
            return _Res(out)
        if self.op == "update":
            for r in hit:
                r.update(copy.deepcopy(self.payload))
            return _Res(copy.deepcopy(hit))
        if self.op == "delete":
            for r in hit:
                rows.remove(r)
            return _Res(copy.deepcopy(hit))
        raise AssertionError(self.op)


class FakeSupabase:
    def __init__(self):
        self.db = {}

    def table(self, name):
        return _Query(self.db, name)


def load_server(env):
    fake_mod = types.ModuleType("supabase")
    fake_mod.create_client = lambda *a, **k: FakeSupabase()
    fake_mod.Client = object
    sys.modules["supabase"] = fake_mod
    for k in list(os.environ):
        if k.startswith(("PAYMENT_", "IYZICO_", "SHOPIER_", "MOCK_PAY", "PUBLIC_BASE")):
            os.environ.pop(k)
    os.environ.update({"SUPABASE_URL": "http://fake", "SUPABASE_KEY": "fake"})
    os.environ.update(env)
    sys.path.insert(0, ROOT)
    sys.modules.pop("server", None)
    srv = importlib.import_module("server")
    srv.app.config["TESTING"] = True
    return srv


def make_account(srv, username="alp", email="alp@example.com"):
    acc_id = "acc-" + username
    srv.supabase.table("accounts").insert({"id": acc_id, "username": username, "name": username,
                                           "email": email, "provider": "password"}).execute()
    dev = hashlib.sha256(username.encode()).hexdigest()
    tok = srv._new_session(acc_id, dev)
    return acc_id, {"token": tok, "device": dev}


DESIGN = {"body": "chubby", "eyes": "star", "mouth": "fangs", "ears": "fox", "tail": "dragon",
          "wings": "bat", "hat": "crown", "pattern": "spots", "fx": "flames",
          "col": [10, 20, 30], "col2": [200, 210, 220], "eye": [1, 2, 3], "size": 1.15,
          "name": "Bonkçuk<script>"}


def test_mock_flow_gems_skin_custom_pet():
    srv = load_server({"PAYMENT_PROVIDER": "mock", "MOCK_PAY_USERS": "alp",
                       "PUBLIC_BASE_URL": "https://test.local"})
    c = srv.app.test_client()
    assert c.get("/shop/catalog").get_json()["enabled"] is True
    acc_id, auth = make_account(srv)

    def buy(pid, **extra):
        r = c.post("/shop/checkout", json=dict(auth, product_id=pid, **extra)).get_json()
        assert r["success"], r
        oid = r["order_id"]
        k = r["pay_url"].split("k=")[1]
        page = c.get(f"/shop/pay/{oid}?k={k}")
        assert page.status_code == 200 and "DENEME" in page.get_data(as_text=True)
        res = c.post("/shop/mock_result", data={"order": oid, "k": k, "r": "ok"})
        assert "ÖDEME TAMAM" in res.get_data(as_text=True)
        # aynı geri dönüş ikinci kez gelirse ÇİFT teslim olmamalı
        c.post("/shop/mock_result", data={"order": oid, "k": k, "r": "ok"})
        st = c.post("/shop/order_status", json=dict(auth, order_id=oid)).get_json()
        assert st["status"] == "granted", st
        return st["progress"]

    prog = buy("1002")
    assert prog["gems"] == 1320 and prog["gems_earned"] == 1320, prog
    prog = buy("2001")
    assert "web_master" in prog["skins_owned"]
    prog = buy("3100", design=DESIGN)
    cp = prog["custom_pets"]
    assert len(cp) == 1 and cp[0]["id"].startswith("pet_custom_")
    assert cp[0]["id"] in prog["cosmetics_owned"]
    assert cp[0]["design"]["name"] == "Bonkçukscript"       # < > süzüldü
    assert prog["gems"] == 1320                               # elmas tekrar eklenmedi

    # aynı skin ikinci kez satın alınamaz
    r = c.post("/shop/checkout", json=dict(auth, product_id="2001")).get_json()
    assert not r["success"]
    # oyun "bende var" diyerek PARALI içerik ekleyemez, sunucudakini de silemez
    sv = c.post("/player/save", json=dict(auth, progress={
        "skins_owned": ["default", "green_titan"], "cosmetics_owned": ["pet_dragon"],
        "custom_pets": [], "gems_earned": 99999})).get_json()
    pr = sv["progress"]
    assert "green_titan" not in pr["skins_owned"] and "pet_dragon" not in pr["cosmetics_owned"]
    assert len(pr["custom_pets"]) == 1 and pr["gems_earned"] <= 1320 + 4000


def test_bad_design_and_foreign_order():
    srv = load_server({"PAYMENT_PROVIDER": "mock", "MOCK_PAY_USERS": "alp,eve"})
    c = srv.app.test_client()
    _, auth = make_account(srv)
    bad = dict(DESIGN, wings="laser")
    r = c.post("/shop/checkout", json=dict(auth, product_id="3100", design=bad))
    assert r.status_code == 400
    r = c.post("/shop/checkout", json=dict(auth, product_id="9999"))
    assert r.status_code == 400
    r = c.post("/shop/checkout", json=dict(auth, product_id="1001")).get_json()
    _, auth2 = make_account(srv, "eve", "eve@example.com")
    st = c.post("/shop/order_status", json=dict(auth2, order_id=r["order_id"]))
    assert st.status_code == 404
    # anahtarsız ödeme sayfası açılmaz
    assert c.get(f"/shop/pay/{r['order_id']}?k=yanlis").status_code == 404
    # mock: listede olmayan hesap satın alamaz
    _, auth3 = make_account(srv, "mallory", "m@example.com")
    assert c.post("/shop/checkout", json=dict(auth3, product_id="1001")).status_code == 403


def test_shop_closed_without_config():
    srv = load_server({})
    c = srv.app.test_client()
    assert c.get("/shop/catalog").get_json()["enabled"] is False
    _, auth = make_account(srv)
    assert c.post("/shop/checkout", json=dict(auth, product_id="1001")).status_code == 503


def test_iyzico_verification():
    srv = load_server({"PAYMENT_PROVIDER": "iyzico", "IYZICO_API_KEY": "k", "IYZICO_SECRET_KEY": "s",
                       "PUBLIC_BASE_URL": "https://test.local"})
    c = srv.app.test_client()
    assert srv._iyzico_price(15900) == "159.0"
    assert srv._iyzico_price(2990) == "29.9"
    assert srv._iyzico_price(2995) == "29.95"
    acc_id, auth = make_account(srv)
    calls = []

    def fake_call(path, body):
        calls.append((path, body))
        if path.endswith("/initialize/auth/ecom"):
            assert body["price"] == "59.0" and body["basketItems"][0]["price"] == "59.0"
            return {"status": "success", "token": "TOK1", "paymentPageUrl": "https://pay.example/x"}
        return fake_call.detail
    srv._iyzico_call = fake_call
    r = c.post("/shop/checkout", json=dict(auth, product_id="1002")).get_json()
    oid, k = r["order_id"], r["pay_url"].split("k=")[1]
    page = c.get(f"/shop/pay/{oid}?k={k}")
    assert page.status_code == 302 and page.headers["Location"] == "https://pay.example/x"
    # tutar tutmazsa teslim YOK
    fake_call.detail = {"status": "success", "paymentStatus": "SUCCESS", "basketId": oid,
                        "paidPrice": "1.0", "currency": "TRY", "fraudStatus": 1}
    c.post("/shop/callback/iyzico", data={"token": "TOK1"})
    assert srv._order_row(oid)["status"] == "failed"
    # yeni sipariş, doğru tutar -> teslim
    r = c.post("/shop/checkout", json=dict(auth, product_id="1002")).get_json()
    oid = r["order_id"]
    fake_call.detail = {"status": "success", "paymentStatus": "SUCCESS", "basketId": oid,
                        "paidPrice": "59.0", "currency": "TRY", "fraudStatus": 1, "paymentId": "P1"}
    res = c.post("/shop/callback/iyzico", data={"token": "TOK2"})
    assert "ÖDEME TAMAM" in res.get_data(as_text=True)
    assert srv._order_row(oid)["status"] == "granted"
    prog = srv._stored_progress(srv._player_row(acc_id))
    assert prog["gems"] == 1320


def test_iyzico_signature_format():
    srv = load_server({"PAYMENT_PROVIDER": "iyzico", "IYZICO_API_KEY": "apikey", "IYZICO_SECRET_KEY": "secret",
                       "PUBLIC_BASE_URL": "https://test.local"})
    captured = {}

    class _R:
        def __init__(self, req):
            captured["req"] = req

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"status":"success"}'
    srv.urllib.request.urlopen = lambda req, timeout=0: _R(req)
    srv._iyzico_call("/payment/test", {"a": 1})
    req = captured["req"]
    rnd = req.get_header("X-iyzi-rnd")
    auth = req.get_header("Authorization")
    assert auth.startswith("IYZWSv2 ")
    dec = base64.b64decode(auth.split(" ", 1)[1]).decode()
    want_sig = hmac.new(b"secret", (rnd + "/payment/test" + '{"a": 1}').encode(), hashlib.sha256).hexdigest()
    assert dec == f"apiKey:apikey&randomKey:{rnd}&signature:{want_sig}"
    assert req.data == b'{"a": 1}'


def test_shopier_signature():
    srv = load_server({"PAYMENT_PROVIDER": "shopier", "SHOPIER_API_KEY": "k", "SHOPIER_API_SECRET": "sec",
                       "PUBLIC_BASE_URL": "https://test.local"})
    c = srv.app.test_client()
    acc_id, auth = make_account(srv)
    r = c.post("/shop/checkout", json=dict(auth, product_id="3001")).get_json()
    oid, k = r["order_id"], r["pay_url"].split("k=")[1]
    html = c.get(f"/shop/pay/{oid}?k={k}").get_data(as_text=True)
    assert "api_pay4.php" in html and "29.00" in html
    bad = c.post("/shop/callback/shopier", data={"platform_order_id": oid, "random_nr": "123456",
                                                  "status": "success", "signature": "AAAA"})
    assert "doğrulanamadı" in bad.get_data(as_text=True)
    sig = base64.b64encode(hmac.new(b"sec", ("123456" + oid).encode(), hashlib.sha256).digest()).decode()
    ok = c.post("/shop/callback/shopier", data={"platform_order_id": oid, "random_nr": "123456",
                                                 "status": "success", "signature": sig})
    assert "ÖDEME TAMAM" in ok.get_data(as_text=True)
    prog = srv._stored_progress(srv._player_row(acc_id))
    assert "pet_cat" in prog["cosmetics_owned"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK ", name)
