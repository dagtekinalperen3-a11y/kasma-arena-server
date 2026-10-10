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
import math

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
                            "hawk", "bats", "nova", "knives", "mines"]
    out = srv._merge_progress(old, new)
    for k in ("ghost_swords", "wolves", "tesla", "meteor", "beam",
              "hawk", "bats", "nova", "knives", "mines"):
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
    ok, why = srv.score_is_plausible("x", 400_000, 100_000, 12, 600.0)
    assert not ok                      # saniyede 166 öldürme

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


if __name__ == "__main__":
    for n in sorted(k for k in list(globals()) if k.startswith("test_")):
        globals()[n]()
        print("OK ", n)
