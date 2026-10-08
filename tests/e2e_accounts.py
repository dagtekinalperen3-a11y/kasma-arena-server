"""
ARENA BONK — UÇTAN UCA HESAP / HİLE KORUMASI TESTİ

Gerçek server.py'yi bellekte çalışan SAHTE bir Supabase ile yerelde ayağa
kaldırır; oyunun GERÇEK hesap istemcisini (AccountClient, RewardCenter,
SaveManager) ona bağlar ve şunları sınar:

  * kayıt / giriş / çıkış, iki farklı hesap + misafir arasında geçiş
  * HER ŞEY HESABA ÖZEL: elmas, skin, günlük hediye, reklam sayaçları
  * hediye/reklam sunucu saatiyle: aynı gün ikinci kez alınamaz, başka
    hesapta alınabilir, saat oynatılsa da sunucu izin vermez
  * reklam bileti olmadan / süre dolmadan ödül yok
  * şişirilmiş elmas gönderen istemci: zaman bütçesiyle sınırlanır
  * gerçek parayla satılan skin/PET'i "bende var" diyen istemci: reddedilir
  * kurcalanmış (şaibeli) yerel kayıt: sunucuya gönderilmez, sunucudaki
    temiz ilerleme aynen alınır
  * skor gönderimi (imzalı) ve dünya sıralaması

Çalıştırma:   pip install flask pygame
              python tests/e2e_accounts.py
"""
import copy
import importlib.util
import os
import sys
import tempfile
import threading
import time
import types
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = tempfile.mkdtemp(prefix="arenabonk_e2e_")
os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", HOME=HOME,
                  APPDATA=HOME, XDG_DATA_HOME=HOME)
os.environ["no_proxy"] = os.environ["NO_PROXY"] = "127.0.0.1,localhost"
for k in ("http_proxy", "HTTP_PROXY"):
    os.environ.pop(k, None)


# =====================================================================
# SAHTE SUPABASE (yalnızca server.py'nin kullandığı çağrılar)
# =====================================================================
class _Res:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.mode, self.payload, self.cols = "select", None, "*"
        self.filters, self._order, self._limit = [], None, None

    def select(self, cols="*", **_k):
        self.mode, self.cols = "select", cols
        return self

    def insert(self, row):
        self.mode, self.payload = "insert", row
        return self

    def update(self, patch):
        self.mode, self.payload = "update", patch
        return self

    def delete(self):
        self.mode = "delete"
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def execute(self):
        if self.db.latency:              # gerçek veritabanı gibi gecikme
            time.sleep(self.db.latency)
        with self.db.lock:
            rows = self.db.tables.setdefault(self.name, [])
            hit = [r for r in rows if all(r.get(c) == v for c, v in self.filters)]
            if self.mode == "insert":
                new = [self.payload] if isinstance(self.payload, dict) else list(self.payload)
                out = []
                for r in new:
                    r = copy.deepcopy(r)
                    r.setdefault("id", str(uuid.uuid4()))
                    rows.append(r)
                    out.append(copy.deepcopy(r))
                return _Res(out)
            if self.mode == "update":
                for r in hit:
                    r.update(copy.deepcopy(self.payload))
                return _Res(copy.deepcopy(hit))
            if self.mode == "delete":
                for r in hit:
                    rows.remove(r)
                return _Res(copy.deepcopy(hit))
            out = copy.deepcopy(hit)
            if self._order:
                c, desc = self._order
                out.sort(key=lambda r: r.get(c) or 0, reverse=desc)
            if self._limit is not None:
                out = out[:self._limit]
            if self.cols != "*":
                keep = [c.strip() for c in self.cols.split(",")]
                out = [{c: r.get(c) for c in keep} for r in out]
            return _Res(out)


class FakeSupabase:
    def __init__(self):
        self.tables = {}
        self.lock = threading.RLock()
        self.latency = 0.0

    def table(self, name):
        return _Query(self, name)


fake_mod = types.ModuleType("supabase")
fake_mod.create_client = lambda *a, **k: FakeSupabase()
fake_mod.Client = FakeSupabase
sys.modules["supabase"] = fake_mod

# ---- sunucuyu yükle ----
spec = importlib.util.spec_from_file_location("server", os.path.join(ROOT, "server.py"))
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
DB = FakeSupabase()
server.supabase = DB

from werkzeug.serving import make_server   # noqa: E402

httpd = make_server("127.0.0.1", 0, server.app, threaded=True)
PORT = httpd.server_port
threading.Thread(target=httpd.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:%d" % PORT

# ---- oyunu yükle ----
spec = importlib.util.spec_from_file_location("ka", os.path.join(ROOT, "kasma_arena13.py"))
ka = importlib.util.module_from_spec(spec)
sys.modules["ka"] = ka
spec.loader.exec_module(ka)
ka.ONLINE_API_URL = URL


# =====================================================================
# küçük test yardımcıları
# =====================================================================
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("  OK   " if cond else "  HATA ") + name + (("  — " + str(detail)) if detail and not cond else ""))


def wait(cond, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.05)
    return False


def call_reward(rc, kind):
    """RewardCenter.claim_gift / grant_ad'ı çağırır, sonucu bekler."""
    box = {}
    fn = rc.claim_gift if kind == "gift" else rc.grant_ad
    fn(lambda amt, err: box.update(amt=amt, err=err))
    wait(lambda: "amt" in box, 10)
    return box.get("amt", 0), box.get("err", "TIMEOUT")


def server_row(acc_id):
    return server._stored_progress(server._player_row(acc_id))


# =====================================================================
def main():
    print("Sunucu:", URL)
    app = ka.App()
    acc, sv, rc = app.account, app.save, app.rewards
    wait(lambda: not acc.booting)
    check("sunucuya bağlanıldı", acc.server_ok is True)

    # ---------- MİSAFİR ----------
    print("\n[1] Misafir")
    check("misafir profili", sv.profile_id() == "guest")
    amt, err = call_reward(rc, "gift")
    check("misafir günlük hediye alır (yerel)", amt == 20, err)
    amt, err = call_reward(rc, "gift")
    check("misafir aynı gün ikinci hediyeyi alamaz", amt == 0)
    guest_gems = sv.get_gems()
    # saat hilesi: kayıt 'gelecekte' görünürse ödül yok
    sv.data["rewards"]["hw"] = time.time() + 5 * 86400
    check("misafirde saat geri alınmışsa hediye/reklam kapalı",
          not rc.gift_ready() and not rc.ad_ready())
    sv.data["rewards"]["hw"] = time.time()

    # ---------- HESAP A ----------
    print("\n[2] Hesap A: kayıt + hediye + reklam")
    acc.register("alpkanka", "sifre12345", "")
    wait(lambda: acc.logged_in() and not acc.busy)
    check("A kayıt oldu ve giriş yaptı", acc.logged_in(), acc.status)
    a_id = (acc.account or {}).get("id")
    wait(lambda: acc.sync_at > 0, 5)
    check("A yeni hesap SIFIRDAN başlar (misafir elması geçmez)", sv.get_gems() == 0, sv.get_gems())
    check("A'da hediye alınabilir görünür", rc.gift_ready())
    amt, err = call_reward(rc, "gift")
    check("A hediye SUNUCUDAN alır", amt == 20 and sv.get_gems() == 20, (amt, err, sv.get_gems()))
    check("sunucuda A'nın elması 20", server_row(a_id)["gems"] == 20)
    amt, err = call_reward(rc, "gift")
    check("A aynı gün ikinci hediye: reddedildi", amt == 0 and err, err)
    # sunucu saatini 'yarın'a almadan, yereldeki sayacı sıfırlayan hileci:
    sv.data["rewards"] = {"pid": sv.profile_id()}
    amt, err = call_reward(rc, "gift")
    check("yerel sayaç sıfırlansa da sunucu ikinci hediyeyi vermez", amt == 0, err)
    # reklam: bilet + süre
    rc.begin_ad()
    wait(lambda: not rc.ticket_pending)
    check("reklam bileti alındı", bool(rc.ticket))
    amt, err = call_reward(rc, "ad")
    check("reklam sonuna kadar izlenmeden ödül yok", amt == 0, err)
    amt, err = call_reward(rc, "ad")
    check("biletsiz reklam ödülü yok", amt == 0)
    server.AD_MIN_WATCH = 0.0
    server.AD_COOLDOWN = 0.0
    rc.begin_ad()
    wait(lambda: not rc.ticket_pending)
    amt, err = call_reward(rc, "ad")
    check("izlenen reklam +50 verir", amt == 50 and sv.get_gems() == 70, (amt, err, sv.get_gems()))
    tk = None
    rc.begin_ad()
    wait(lambda: not rc.ticket_pending)
    tk = rc.ticket
    call_reward(rc, "ad")
    rc.ticket = tk
    amt, err = call_reward(rc, "ad")
    check("aynı reklam bileti ikinci kez kullanılamaz", amt == 0, err)
    a_gems = sv.get_gems()

    # ---------- ÇIKIŞ: misafire dönüş ----------
    print("\n[3] Çıkış -> misafir")
    acc.logout()
    check("çıkınca misafir profiline dönüldü", sv.profile_id() == "guest")
    check("misafirin elması geri geldi, A'nınki karışmadı", sv.get_gems() == guest_gems,
          (sv.get_gems(), guest_gems))
    check("misafirin hediye sayacı kendi sayacı (alınmış)", not rc.gift_ready())

    # ---------- HESAP B ----------
    print("\n[4] Hesap B: aynı bilgisayarda başka hesap")
    acc.register("velikanka", "sifre12345", "")
    wait(lambda: acc.logged_in() and not acc.busy)
    b_id = (acc.account or {}).get("id")
    check("B giriş yaptı", acc.logged_in() and b_id != a_id)
    wait(lambda: acc.sync_at > 0, 5)
    check("B sıfırdan başlar", sv.get_gems() == 0, sv.get_gems())
    check("B'de hediye ALINABİLİR (A almış olsa da)", rc.gift_ready())
    amt, err = call_reward(rc, "gift")
    check("B hediyesini aldı", amt == 20, err)
    # B skin alır (elmasla) — başarım da açılabilir
    sv.add_gems(150)                   # (koşudan kazanılmış gibi)
    ok = sv.buy_skin("crimson", 150)
    check("B elmasla skin aldı", ok)
    acc.push_progress()
    wait(lambda: not acc.sync_busy, 5)
    time.sleep(0.3)
    check("B'nin skini sunucuda", "crimson" in server_row(b_id).get("skins_owned", []))

    # ---------- A'ya geri dön ----------
    print("\n[5] Tekrar A")
    acc.logout()
    acc.login("alpkanka", "sifre12345")
    wait(lambda: acc.logged_in() and not acc.busy)
    wait(lambda: acc.sync_at > 0, 5)
    time.sleep(0.3)
    check("A'nın elması aynen geri geldi", sv.get_gems() == a_gems, (sv.get_gems(), a_gems))
    check("A'da B'nin skini YOK", "crimson" not in sv.data.get("skins_owned", []))
    check("A'nın bugünkü hediyesi 'alındı' (sunucudan)", not rc.gift_ready())

    # ---------- HİLE: şişirilmiş elmas ----------
    print("\n[6] Hile denemeleri")
    before = server_row(a_id)["gems_earned"]
    for _ in range(4):
        sv.data["gems_earned"] = int(sv.data.get("gems_earned", 0)) + 100000
        sv.data["gems"] = int(sv.data.get("gems", 0)) + 100000
        acc.push_progress()
        wait(lambda: not acc.sync_busy, 5)
        time.sleep(0.2)
    after = server_row(a_id)["gems_earned"]
    check("4 x 100.000 elmas gönderen istemci en çok GEM_BURST alır",
          after - before <= server.GEM_BURST, after - before)
    # parayla satılan skin / PET
    sv.data.setdefault("skins_owned", []).append("web_master")
    sv.data.setdefault("cosmetics_owned", []).append("pet_dragon")
    acc.push_progress()
    wait(lambda: not acc.sync_busy, 5)
    time.sleep(0.3)
    row = server_row(a_id)
    check("sunucu premium skini kabul etmedi", "web_master" not in row.get("skins_owned", []))
    check("sunucu parayla satılan PET'i kabul etmedi", "pet_dragon" not in row.get("cosmetics_owned", []))
    check("oyun da sunucuda olmayan premium skini geri aldı",
          "web_master" not in sv.data.get("skins_owned", []))
    # kurcalanmış kayıt
    clean_gems = server_row(a_id)["gems"]
    sv.mark_tainted("signature")
    sv.data["gems_earned"] = 9999999
    sv.data["gems"] = 9999999
    acc.push_progress()               # şaibeli: göndermek yerine indirir
    wait(lambda: not sv.is_tainted(), 6)
    time.sleep(0.3)
    check("şaibeli kayıt sunucuya gitmedi, sunucudaki temiz değer alındı",
          sv.get_gems() == clean_gems and server_row(a_id)["gems"] == clean_gems,
          (sv.get_gems(), clean_gems))

    # ---------- SKOR + DÜNYA SIRALAMASI ----------
    print("\n[7] Skor gönderimi")
    app.start_run()
    run = app.run
    for _ in range(600):
        run.player.hp = run.player.max_hp
        run.pending_levelups = 0
        run.update(1 / 30, {"left": 0, "right": 0, "up": 0, "down": 0, "mouse_down": True,
                            "aim_x": run.player.x + 50, "aim_y": run.player.y})
    run.finish_run()
    app._maybe_submit_online()
    wait(lambda: app.online_submit_status in ("gönderildi", "başarısız", "reddedildi"), 8)
    check("skor dünya sıralamasına gönderildi", app.online_submit_status == "gönderildi",
          (app.online_submit_status, getattr(app, "online_block_text", "")))
    app.online.fetch_world_scores_async()
    wait(lambda: app.online.world_scores is not None and not app.online.loading, 8)
    names = [e.get("name") for e in (app.online.world_scores or [])]
    check("dünya sıralamasında hesabın adı var", "alpkanka" in names, names)

    # ---------- profil sızıntısı: eski sürüm kopyası ----------
    print("\n[8] Eski sürümden kalan profil kopyası")
    sv.data.setdefault("profiles", {})["acc:eski"] = {"gems": 5, "gems_earned": 5,
                                                       "gems_spent": 0}
    sv.data["rewards"] = {"pid": sv.profile_id(), "gift_day": "2999-01-01"}
    sv.switch_profile("acc:eski")
    check("eksik alanlar önceki kullanıcıdan SIZMADI",
          sv.data.get("rewards") == {} and sv.data.get("skins_owned") == ["default"],
          (sv.data.get("rewards"), sv.data.get("skins_owned")))

    # ---------- aynı anda 8 hediye isteği ----------
    print("\n[9] Aynı anda yağdırılan istekler")
    import json as _json
    with DB.lock:
        prow = [r for r in DB.tables["player_data"] if r.get("account_id") == a_id][0]
        d = _json.loads(prow["data"]) if isinstance(prow.get("data"), str) else dict(prow["data"])
        d.setdefault("rewards", {})["gift_day"] = server._server_day(-1)
        prow["data"] = _json.dumps(d) if isinstance(prow.get("data"), str) else d
    server._rate_hits.clear()
    DB.latency = 0.03                    # okuma ile yazma arasında yarış penceresi
    g0 = server_row(a_id)["gems_earned"]
    outs = []
    body = {"token": acc.token, "device": ka.device_id(), "device_legacy": ka.device_id_legacy(),
            "kind": "gift"}
    def one():
        try:
            outs.append(acc._post("/rewards/claim", dict(body)))
        except Exception:               # 409 / 429: reddedildi
            outs.append({})
    th = [threading.Thread(target=one) for _ in range(8)]
    for t in th:
        t.start()
    for t in th:
        t.join()
    DB.latency = 0.0
    wins = [o for o in outs if o.get("success")]
    g1 = server_row(a_id)["gems_earned"]
    check("8 eşzamanlı hediye isteğinden yalnızca 1'i geçer", len(wins) == 1, len(wins))
    check("elmas yalnızca bir kez eklendi", g1 - g0 == (wins[0]["amount"] if wins else 0),
          (g0, g1))

    ok_n = sum(1 for _n, ok in RESULTS if ok)
    print("\nSONUÇ: %d / %d geçti" % (ok_n, len(RESULTS)))
    httpd.shutdown()
    return 0 if ok_n == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
