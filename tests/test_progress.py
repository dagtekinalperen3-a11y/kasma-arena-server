"""Sunucu İLERLEME ve SKOR DENETİMİ testleri (v3.30) — sahte Supabase ile.

    python tests/test_progress.py      (ya da: python -m pytest tests/test_progress.py -q)

Denenenler:
  * Yeni istatistikler (total_chests, total_cursed, best_curse) kayda girip
    geri gitmiyor; sonsuz/bozuk değer kaydı çökertmiyor.
  * Yeni silahlar (hayalet kılıçlar, kurtlar...) weapons_owned'a ekleniyor.
  * UĞUR ustalığı (m_luck) ödenmişse kalıyor, ödenmemişse kırpılıyor;
    oyunun ve sunucunun ustalık bedeli birebir aynı.
  * Lanetli (x2,5 skor) DÜRÜST bir koşu "imkânsız skor" sayılmıyor; uydurma
    skor hâlâ reddediliyor.
"""
import os
import sys
import tempfile

# Oyuncunun GERÇEK kaydına asla dokunma (Windows'ta %APPDATA% dahil): oyun bu
# klasörü kullanır (bkz. kasma_arena13.ARENA_SAVE_DIR). Oyun modülü içe
# aktarılmadan ÖNCE ayarlanmalı.
os.environ["ARENA_SAVE_DIR"] = tempfile.mkdtemp(prefix="arena_prog_")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from test_shop import load_server  # noqa: E402


def _srv():
    return load_server({})


def test_new_stats_merge():
    srv = _srv()
    old = srv._blank_progress()
    old["stats"] = {"total_chests": 4, "total_cursed": 1}
    new = srv._blank_progress()
    new["stats"] = {"total_chests": 9, "total_cursed": 3, "best_curse": 2, "runs": 5,
                    "total_goblins": 7}
    out = srv._merge_progress(old, new)
    st = out["stats"]
    assert st["total_chests"] == 9 and st["total_cursed"] == 3 and st["best_curse"] == 2
    assert st["total_goblins"] == 7                     # v3.31
    # geri gitmez
    back = srv._blank_progress()
    back["stats"] = {"total_chests": 1}
    out2 = srv._merge_progress(out, back)
    assert out2["stats"]["total_chests"] == 9
    # sonsuz değer kaydı çökertmez
    bad = srv._blank_progress()
    bad["stats"] = {"total_cursed": float("inf"), "best_curse": "abc"}
    out3 = srv._merge_progress(out, bad)
    assert out3["stats"]["total_cursed"] == 3


def test_new_weapons_owned():
    srv = _srv()
    old = srv._blank_progress()
    old["weapons_owned"] = ["axe"]
    new = srv._blank_progress()
    new["weapons_owned"] = ["axe", "ghost_swords", "wolves", "tesla", "meteor", "beam",
                            "hawk", "bats", "nova", "knives", "quake"]
    out = srv._merge_progress(old, new)
    for k in ("ghost_swords", "wolves", "tesla", "meteor", "beam",
              "hawk", "bats", "nova", "knives", "quake"):
        assert k in out["weapons_owned"]


def test_mastery_luck_paid_and_clipped():
    srv = _srv()
    import kasma_arena13 as K
    # oyunun bedeli == sunucunun bedeli
    m = K.MASTERY_BY_KEY["m_luck"]
    for lvl in range(0, 12):
        assert K.mastery_cost(m, lvl) == srv._mastery_cost("m_luck", lvl), lvl
    cost5 = srv._mastery_total("m_luck", 5)
    ok = srv._merge_mastery({}, {"m_luck": 5}, cost5)
    assert ok["m_luck"] == 5
    clipped = srv._merge_mastery({}, {"m_luck": 5}, cost5 - 1)
    assert clipped["m_luck"] < 5


def test_cursed_run_is_plausible():
    srv = _srv()
    import kasma_arena13 as K
    # Bottan ölçülen en uç lanetli koşu (kabus, 30 dk, bütün lanetler):
    wave, rt, kills, score = 55, 1800.0, 33098, 2352618
    ok, why = srv.score_is_plausible("x", score, kills, wave, rt)
    assert ok, why
    # aynı koşunun bir buçuk katı bile geçmeli (pay)
    ok, why = srv.score_is_plausible("x", int(score * 1.5), int(kills * 1.5), wave, rt)
    assert ok, why
    # ama uydurma bir skor hâlâ reddedilir
    ok, why = srv.score_is_plausible("x", 50_000_000, 200, 10, 300.0)
    assert not ok
    ok, why = srv.score_is_plausible("x", 400_000, 400_000, 12, 600.0)
    assert not ok                      # saniyede 666 öldürme (v3.33 sınırı 200)

    # oyunun kendi denetimi de lanet payını tanır
    class _R:
        pass
    r = _R()
    w_ = _R()
    w_.wave = wave
    r.score, r.kills, r.run_time, r.waves = score, kills, rt, w_
    r.curse_score_bonus = K.CURSE_SCORE_MAX
    r.total_wave = lambda: wave
    assert K.run_score_plausible(r)
    r.curse_score_bonus = 0.0
    r.score = 10 ** 9
    assert not K.run_score_plausible(r)


def test_v333_mutes_and_limits():
    srv = _srv()
    import kasma_arena13 as K
    # yeni ustalık dalları: oyunun ve sunucunun bedeli birebir aynı
    for key in ("m_wmute", "m_bmute"):
        m = K.MASTERY_BY_KEY[key]
        for lvl in range(0, 4):
            assert K.mastery_cost(m, lvl) == srv._mastery_cost(key, lvl), (key, lvl)
    # sunucu bu dalları silmez ve 4'te kırpar
    paid = srv._mastery_total("m_wmute", 4) + srv._mastery_total("m_bmute", 2)
    out = srv._merge_mastery({}, {"m_wmute": 9, "m_bmute": 2}, paid + 10 ** 6)
    assert out["m_wmute"] == 4 and out["m_bmute"] == 2
    # reklam ödülü ve süre: oyun ile sunucu aynı, film süresine uygun
    assert srv.AD_REWARD_GEMS == K.AD_REWARD_GEMS == 300
    assert srv.AD_MIN_WATCH < K.GameTour.LENGTH
    # ÇOK GÜÇLÜ dürüst oyuncu (lanetli cehennem, saniyede ~80 öldürme) BANLANMAZ
    rt = 1800.0
    kills = int(80 * rt)
    wave = 70
    score = int(kills * 60)
    ok, why = srv.score_is_plausible("x", score, kills, wave, rt)
    assert ok, why
    # ama uydurma bir skor hâlâ reddedilir
    assert not srv.score_is_plausible("x", 50_000_000, 200, 10, 300.0)[0]
    assert not srv.score_is_plausible("x", 400_000, 1_000_000, 12, 600.0)[0]


def test_v335_cheat_ban_survives_relogin_and_reinstall():
    """HİLE AÇIĞI (v3.35): hile kodu + çıkış/giriş, kaydı silme, başka hesap,
    çevrimdışı hile. Yasak her durumda KALICI kalmalı, hile içeriği hesaba
    yazılmamalı ve temiz hesaplar hiç etkilenmemeli."""
    import threading
    import time as _time
    srv = _srv()
    C = srv.app.test_client()
    import kasma_arena13 as K
    import pygame
    pygame.init()
    pygame.display.set_mode((K.VIRTUAL_W, K.VIRTUAL_H))

    class SyncThread:
        def __init__(self, target=None, args=(), kwargs=None, daemon=None):
            self.t, self.a, self.k = target, args, kwargs or {}

        def start(self):
            if self.t:
                self.t(*self.a, **self.k)

    saved = (threading.Thread, _time.sleep, K.ONLINE_API_URL, K.AccountClient._post,
             K.OnlineClient.submit_score_async, K.SaveManager.on_ban, K.SaveManager.on_progress_change,
             K.SAVE_FILE, K.LEGACY_SAVE)
    # Bu testin KENDİ boş kaydı: sahte sunucu hesap kimliklerini her seferinde
    # acc-1'den verir; başka bir testin (ya da önceki çalıştırmanın) kaydında
    # kalmış "acc:acc-1" profili buraya karışmasın.
    _own = tempfile.mkdtemp(prefix="arena_cheat_")
    K.SAVE_FILE = os.path.join(_own, "kasma_arena_save.json")
    K.LEGACY_SAVE = os.path.join(_own, "legacy_kasma_arena_save.json")
    sent = []

    def _post(self, path, payload, timeout=20):
        return C.post(path, json=payload).get_json() or {}

    def _submit(self, payload, on_done=None):
        j = C.post("/submit", json=payload).get_json() or {}
        sent.append(bool(j.get("success")))
        if on_done:
            on_done(bool(j.get("success")), str(j.get("error") or ""))

    def server_state(acc_id):
        prog = srv._stored_progress(srv._player_row(acc_id))
        sc = [r for r in srv.supabase.table("scores").select("*").execute().data
              if r.get("account_id") == acc_id]
        return bool(prog.get("board_banned")), int(prog.get("gems") or 0), len(prog.get("skins_owned") or []), len(sc)

    def submit(app):
        r = K.RunState(app.save, "default", "normal", ach=None)
        r.score, r.kills, r.run_time, r.game_over = 20000, 400, 400.0, True
        r.waves.wave = 8
        app.run = r
        app.online_submit_status = None
        app._maybe_submit_online()
        return app.online_submit_status

    threading.Thread = SyncThread
    _time.sleep = lambda s: None
    K.ONLINE_API_URL = "http://fake"
    K.AccountClient._post = _post
    K.OnlineClient.submit_score_async = _submit
    try:
        app = K.App()
        app.online.enabled = True
        app.account.register("alp", "sifre12345", "alp@example.com")
        acc = app.account.account["id"]
        assert submit(app) == "gönderildi" and server_state(acc)[3] == 1
        # HİLE: hesap sunucuda da yasaklanır, skorları silinir, içerik hesaba gitmez
        app._apply_cheat()
        banned, gems, skins, scores = server_state(acc)
        assert banned and gems == 0 and skins == 1 and scores == 0
        assert app.save.is_board_banned()
        assert submit(app) == "reddedildi"
        # ÇIKIŞ + GİRİŞ (asıl açık buradaydı: yasak siliniyordu)
        app.account.logout()
        app.account.login("alp", "sifre12345")
        assert app.save.is_board_banned()
        assert submit(app) == "reddedildi"
        # KAYDI SİL, YENİDEN KUR, GİRİŞ YAP: yasak sunucudan geri gelir
        for f in (K.SAVE_FILE, K.LEGACY_SAVE):
            if os.path.exists(f):
                os.remove(f)
        app2 = K.App()
        app2.online.enabled = True
        app2.account.login("alp", "sifre12345")
        assert app2.save.is_board_banned()
        assert submit(app2) == "reddedildi"
        # yerel bayrak elle silinse bile: oyun yasağı sunucudan geri alır...
        app2.save.data["board_banned"] = False
        app2.save.data["tainted"] = False
        assert submit(app2) == "reddedildi" and app2.save.is_board_banned()
        # ...ve oyun kapısı tamamen aşılsa bile SUNUCU kabul etmez
        pay = {"name": "alp", "score": 20000, "kills": 400, "wave": 8, "run_time": 400.0,
               "created_at": _time.time(), "diff": "normal"}
        pay["sig"] = K.sign_submit(pay)
        pay.update(token=app2.account.token, device=K.device_id(), device_legacy=K.device_id_legacy())
        r = C.post("/submit", json=pay)
        assert r.status_code == 403 and server_state(acc)[3] == 0
        # ÇEVRİMDIŞI HİLE: ağ gelince yasak sunucuya taşınır
        app2.account.logout()
        app2.account.register("veli", "sifre12345", "veli@example.com")
        acc2 = app2.account.account["id"]
        K.AccountClient._post = lambda self, path, payload, timeout=20: (_ for _ in ()).throw(OSError("off"))
        app2._apply_cheat()
        assert not server_state(acc2)[0]
        K.AccountClient._post = _post
        app2.account.pull_progress()
        banned2, gems2, skins2, _sc = server_state(acc2)
        assert banned2 and gems2 == 0 and skins2 == 1
        # TEMİZ HESAP etkilenmez
        app2.account.logout()
        app2.account.register("ayse", "sifre12345", "ayse@example.com")
        acc3 = app2.account.account["id"]
        assert not app2.save.is_board_banned()
        assert submit(app2) == "gönderildi" and not server_state(acc3)[0]
        # başkasının adına itiraf edilemez (jeton zorunlu)
        r = C.post("/player/report_cheat", json={"token": "uydurma", "reason": "cheat_code"})
        assert r.status_code == 401
    finally:
        (threading.Thread, _time.sleep, K.ONLINE_API_URL, K.AccountClient._post,
         K.OnlineClient.submit_score_async, K.SaveManager.on_ban, K.SaveManager.on_progress_change,
         K.SAVE_FILE, K.LEGACY_SAVE) = saved


if __name__ == "__main__":
    for n in sorted(k for k in list(globals()) if k.startswith("test_")):
        globals()[n]()
        print("OK ", n)
