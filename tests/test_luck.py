"""ŞANS SİSTEMİ (v3.29) testleri — oyunu açmadan, başsız.

    python tests/test_luck.py          (ya da: python -m pytest tests/test_luck.py -q)

Denenenler: roll_rarity dağılımı, eff_luck toplamı, weapon_boost'un hasara
yansıması ve tavanı, sandık ve seviye atlama akışı, şanslı yenileme, şans
içerikleri (kitap / market / kıyafet / skin / ustalık), kitap ayarları
(İkinci Nefes yok, Dev 250, Son Umut, Zaman), İNFAZ'ın silah freni ve
zırh altında çalışması, eski kaydın yüklenmesi ve skor denetimi payı.
"""
import os
import sys
import json
import math
import random
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# Kayıt dosyası geçici bir klasöre yazılsın (oyuncunun gerçek kaydına dokunma).
_TMP = tempfile.mkdtemp(prefix="arena_luck_")
os.environ["XDG_DATA_HOME"] = _TMP
os.environ["ARENA_SAVE_DIR"] = os.path.join(_TMP, "KasmaArena")   # Windows'ta da geçerli

import pygame  # noqa: E402
import kasma_arena13 as K  # noqa: E402

pygame.init()
pygame.display.set_mode((K.VIRTUAL_W, K.VIRTUAL_H))


def _save(**extra):
    data = json.loads(json.dumps(K.SaveManager.DEFAULT))
    data["books_owned"] = [b["key"] for b in K.BOOKS]
    data["weapons_owned"] = [w["key"] for w in K.BOSS_WEAPONS]
    data.update(extra)
    return K._AdSave(data)


def _run(skin="default", **extra):
    return K.RunState(_save(**extra), skin, "normal", ach=K._AdAch())


def rarity_report():
    """Şans 0/50/100/200 için 20.000 çekilişlik dağılım tablosu."""
    rows = []
    for luck in (0.0, 0.5, 1.0, 2.0, 5.0):
        pct = K.rarity_table(luck, n=20000, seed=7)
        rows.append((luck, pct))
    return rows


def test_rarity_distribution():
    rows = dict(rarity_report())
    assert rows[0.0][4] < 0.5, rows[0.0]                 # %0 şansta Efsanevi ~yok
    assert 65 < rows[0.0][0] < 75
    assert rows[1.0][0] < rows[0.5][0] < rows[0.0][0]    # şans Yaygın'ı azaltır
    assert rows[2.0][3] > rows[1.0][3] > rows[0.5][3]    # ... Epik'i artırır
    for luck, pct in rows.items():
        assert pct[4] <= 10.8, (luck, pct)               # Efsanevi tavanı %10
    w = K.rarity_weights(50.0)
    assert w[4] / sum(w) <= K.RARITY_LEGEND_CAP + 1e-9


def test_eff_luck_sum():
    p = K.Player("default")
    assert p.eff_luck() == 0.0
    p.luck = 0.05
    p.run_luck_bonus = 0.10
    assert abs(p.eff_luck() - 0.15) < 1e-9
    p.run_luck_bonus = -1.0
    assert p.eff_luck() == 0.0                           # eksiye düşmez
    # skin perk'i
    fox = K.Player("lucky_fox")
    assert abs(fox.luck - 0.05) < 1e-9
    fox.gain_xp(10 ** 6)
    assert fox.level > 5 and fox.luck > 0.05 + 0.01 * 3
    # kıyafet perk'i
    q = K.Player("default")
    q.cosmetics = {"hat": "flower_crown", "eyewear": "heart_glasses", "cape": "cape_forest"}
    q.apply_cosmetic_perks()
    assert abs(q.eff_luck() - 0.15) < 1e-9
    # şans kritik şansını değiştirmez
    c0 = K.Player("default").eff_crit_chance()
    assert q.eff_crit_chance() == c0


def test_weapon_boost_damage():
    p = K.Player("default")
    w = K.WEAPON_BY_KEY["axe"]
    d0 = K.weapon_damage(p, w, 3)
    p.add_weapon_boost("axe", K.rarity_boost(3, "card"))  # Epik kart: +%10
    d1 = K.weapon_damage(p, w, 3)
    assert abs(d1 / d0 - (1 + K.CARD_RARITY_BONUS[3])) < 1e-6
    assert K.rarity_boost(0, "card") == 0.0                 # Yaygın kart: yalnızca seviye
    assert K.rarity_boost(4, "chest") > K.rarity_boost(4, "card")
    for _ in range(40):
        p.add_weapon_boost("axe", K.rarity_boost(4))
    assert abs(p.weapon_boost["axe"] - K.WEAPON_BOOST_CAP) < 1e-9
    assert abs(K.weapon_damage(p, w, 3) / d0 - (1 + K.WEAPON_BOOST_CAP)) < 1e-6
    # başka silah etkilenmez
    w2 = K.WEAPON_BY_KEY["whip"]
    assert K.weapon_damage(p, w2, 3) == K.weapon_damage(K.Player("default"), w2, 3)


def test_chest_flow():
    run = _run()
    p = run.player
    ch = K.BossChest(p.x, p.y, "x")
    run.grant_weapon(ch)                                 # silah yok -> altın
    assert run.chests_opened == 1 and run.gold_wallet > 0
    p.weapons = {"axe": 2, "whip": 5}
    random.seed(3)
    for _ in range(30):
        run.grant_weapon(K.BossChest(p.x, p.y, "x"))
    assert run.chests_opened == 31
    assert p.weapon_boost.get("axe", 0) > 0 and p.weapon_boost.get("whip", 0) > 0
    assert all(v <= K.WEAPON_BOOST_CAP + 1e-9 for v in p.weapon_boost.values())
    # tavanı dolu silah sandıkta çökmeden altına döner
    p.weapons = {k: K.weapon_max_level(K.WEAPON_BY_KEY[k]) for k in p.weapons}
    run.grant_weapon(K.BossChest(p.x, p.y, "x"))
    # Efsanevi sandık bir seviye daha verir
    p.weapons = {"axe": 3}
    p.luck = 999.0
    orig = K.roll_rarity
    K.roll_rarity = lambda luck, rnd=random: 4
    try:
        run.grant_weapon(K.BossChest(p.x, p.y, "x"))
    finally:
        K.roll_rarity = orig
    assert p.weapons["axe"] == 5


def test_levelup_flow():
    run = _run()
    p = run.player
    p.weapons = {"axe": 2}
    p.luck = 1.0
    run.pending_levelups = 40
    seen_tiers = set()
    for _ in range(40):
        run.start_levelup_choice()
        assert run.levelup_choices, "el boş"
        for c in run.levelup_choices:
            if c["kind"] == "weapon":
                # v3.30: YENİ silah kartı da kendi kademesini çeker
                assert "rarity" in c and abs(c["boost"] - K.rarity_boost(c["rarity"], "card")) < 1e-9
                seen_tiers.add(c["rarity"])
            else:
                # v3.32: normal kitap kartı nadirlik çeker; kazanç nadirliğe göre
                if c.get("rare"):
                    assert "rarity" not in c and "gains" not in c
                else:
                    r = c["rarity"]
                    assert c["gains"] == K.book_gain(c["key"], r, c["lvl"])
        # varsa yükseltme kartını seç
        idx = next((i for i, c in enumerate(run.levelup_choices)
                    if c["kind"] == "weapon" and not c["new"]), 0)
        run.choose_levelup(idx)
    assert len(seen_tiers) >= 2
    assert sum(p.weapon_boost.values()) > 0
    # çizim çökmesin (rozet + şans göstergesi)
    run.pending_levelups = 1
    run.start_levelup_choice()
    ov = K.LevelUpOverlay()
    ov.rebuild(run.levelup_choices)
    surf = pygame.Surface((K.VIRTUAL_W, K.VIRTUAL_H))
    lx = K.VIRTUAL_W / 2 + 160
    ov.draw_and_handle(surf, run, (int(lx), int(ov.cards[0][0].y - 4)), False, 1.0)
    for rect, _c, _i in ov.cards:
        ov.draw_and_handle(surf, run, rect.center, False, 1.0)
    K.draw_stats_panel(surf, run, 1.0)


def test_lucky_reroll():
    run = _run()
    run.player.run_luck_bonus = 10.0                    # olasılık tavanı %35
    run.pending_levelups = 1
    run.start_levelup_choice()
    run.reroll_used = run.REROLL_FREE + 5
    run.gold_wallet = 10 ** 6
    random.seed(11)
    free = 0
    for _ in range(400):
        run.reroll_used = run.REROLL_FREE + 5           # fiyat sabit kalsın
        run.gold_wallet = 10 ** 9
        used = run.reroll_used
        ok, msg = run.reroll_levelup()
        assert ok
        if run.reroll_used == used:
            free += 1
    assert 0.25 < free / 400.0 < 0.45, free
    # şans 0: hiç bedava yok
    run2 = _run()
    run2.pending_levelups = 1
    run2.start_levelup_choice()
    run2.reroll_used = run2.REROLL_FREE + 5
    run2.gold_wallet = 10 ** 6
    for _ in range(100):
        run2.reroll_used = run2.REROLL_FREE + 5
        run2.gold_wallet = 10 ** 9
        u = run2.reroll_used
        run2.reroll_levelup()
        assert run2.reroll_used == u + 1


def test_rare_book_weight_luck():
    run = _run()
    offers, w0 = run.levelup_pool()
    run.player.run_luck_bonus = 1.0
    offers1, w1 = run.levelup_pool()
    for o, a, b in zip(offers, w0, w1):
        if o["kind"] == "book" and o.get("rare") and a > 0:
            assert abs(b / a - 1.5) < 1e-6
        elif o["kind"] == "book":
            assert a == b


def test_luck_content():
    p = K.Player("default")
    base = dict(K.BOOK_GAINS["r_luck"])["luck"]
    for _ in range(3):
        p.take_book("r_luck")                               # Yaygın kart
    assert abs(p.eff_luck() - 3 * base) < 1e-9
    assert K.book_max_level("r_luck") == 30
    for _ in range(12):
        p.take_book("r_luck")
    # 10'dan sonrası azalan getirili
    assert abs(p.eff_luck() - (10 * base + 5 * base * K.LUCK_BOOK_LATE_K)) < 1e-9
    # Efsanevi kart Yaygın'ın 8 katı verir
    q2 = K.Player("default")
    q2.take_book("r_luck", 4)
    assert abs(q2.eff_luck() - base * K.BOOK_RARITY_MULT[4]) < 1e-9
    q = K.Player("default")
    assert q.take_book("r_clover") == 1
    assert abs(q.eff_luck() - K.CLOVER_LUCK_ON_TAKE) < 1e-9          # v3.31: %60
    q.gain_xp(10 ** 6)
    assert abs(q.eff_luck() - (K.CLOVER_LUCK_ON_TAKE
                               + K.CLOVER_LUCK_PER_LEVEL * (q.level - 1))) < 1e-6
    # market
    s = K.Player("default")
    for key in ("core_luck", "lucky_coin", "gambler_dice"):
        s.shop_levels[key] = s.shop_levels.get(key, 0) + 1
        K.apply_shop_item(s, key)
    assert abs(s.eff_luck() - (0.08 + 0.10 + 0.25)) < 1e-9
    # v3.30: Şans Çekirdeği tavansız ama azalan getirili (toplam +%56'ya yaklaşır)
    assert K.SHOP_BY_KEY["core_luck"]["max"] >= 999
    c = K.Player("default")
    for i in range(60):
        c.shop_levels["core_luck"] = i + 1
        K.apply_shop_item(c, "core_luck")
    assert 0.45 < c.eff_luck() < 0.56
    # ustalık
    sv = _save(mastery={"m_luck": 5})
    K.MASTERY_SAVE[0] = sv
    try:
        m = K.Player("default")
    finally:
        K.MASTERY_SAVE[0] = None
    assert abs(m.luck - 0.15) < 1e-9
    # mıknatıs: şans temel olasılığı büyütür, garanti eğrisi aynı
    assert abs(K.magnet_drop_chance(10, 1.0) / K.magnet_drop_chance(10) - 1.5) < 1e-9
    assert K.magnet_drop_chance(K.MAGNET_PITY_TO, 5.0) == 1.0
    # 5 dilde metinler
    for key in ("rar.0", "rar.4", "st.luck", "b.r_luck.name", "b.r_clover.desc",
                "s.core_luck.name", "s.gambler_dice.desc", "mastery.m_luck.name",
                "ui.luck_tip", "ui.luck_free", "fx.execute", "sk.lucky_fox.name"):
        row = K.STRINGS[key]
        assert len(row) == 5 and all(row), key


def test_book_tweaks():
    assert "r_second_wind" not in K.BOOK_BY_KEY
    p = K.Player("default")
    hp0 = p.max_hp
    p.take_book("r_hp_big")
    assert p.max_hp - hp0 == 250
    # SON UMUT: %40 canın altında -%35 hasar ve +2 can/sn; zırh tavanı aynı
    h = K.Player("default")
    h.take_book("r_lasthope")
    fx = K.EffectSystem()
    h.hp = h.max_hp * 0.39
    before = h.hp
    h.take_damage(10, fx)
    assert abs((before - h.hp) - 10 * (1 - h.eff_armor()) * h.dmg_taken_mult * 0.65) < 1e-6
    assert h.eff_regen() >= 2.0 and h.eff_armor() <= 0.6
    h.hp = h.max_hp
    assert h.lowhp_factor() == 1.0
    # ZAMAN: dash -%10
    z = K.Player("default")
    z.take_book("r_dashslow")
    assert abs(z.dash_cd_mult - 0.90) < 1e-9
    # eski kapatma kaydı hak yemesin
    sv = _save(books_muted=["r_second_wind", "r_dmg"])
    assert sv.effective_muted_books() == ["r_dmg"]


def test_execute_works():
    run = _run()
    p = run.player
    p.execute_threshold = 0.18
    # 1) silah vuruşu: tek-atma freni infazı yememeli
    e = K.Enemy("tank", p.x + 60, p.y, 1.0, wave=5)
    e.hp = e.max_hp * 0.25
    run.enemies.append(e)
    run._weapon_hit(e, e.max_hp * 0.20, crit=False, wlvl=1)   # freni aşan vuruş
    assert not e.alive, "silahla infaz olmadı"
    # 2) zırhlı yaratık (25+ dalga / cehennem)
    e2 = K.Enemy("red", p.x + 60, p.y, 1.0, wave=5)
    e2.armor = 0.5
    e2.hp = e2.max_hp * 0.25
    run.enemies.append(e2)
    run._field_damage(e2, e2.max_hp * 0.10, wlvl=1)
    assert not e2.alive, "zırhlıda infaz olmadı"
    # 3) eşiğin üstünde kalan yaratık ölmez
    e3 = K.Enemy("red", p.x + 60, p.y, 1.0, wave=5)
    e3.hp = e3.max_hp
    run.enemies.append(e3)
    run._weapon_hit(e3, e3.max_hp * 0.10, crit=False)
    assert e3.alive
    # 4) market eşyaları eşiği açıyor
    q = K.Player("default")
    K.apply_shop_item(q, "execute_edge")
    K.apply_shop_item(q, "sunder")
    assert abs(q.execute_threshold - 0.18) < 1e-9


def test_old_save_loads():
    """v3.28 biçiminde (total_chests / m_luck yok, İkinci Nefes açık) imzalı
    bir kayıt yazılır ve yeni sürümle açılır."""
    old = json.loads(json.dumps(K.SaveManager.DEFAULT))
    old["books_owned"] = ["r_dmg", "r_second_wind", "r_hp"]
    old["books_muted"] = ["r_second_wind"]
    old["stats"] = {"runs": 5, "total_kills": 900, "best_wave": 12}
    old["mastery"] = {"m_dmg": 2}
    old.pop("custom_pets", None)
    old["_sig"] = K.sign_save(old)
    with open(K.SAVE_FILE, "wb") as f:
        f.write(K.encrypt_save(json.dumps(old)))
    sv = K.SaveManager()
    assert not sv.data.get("tainted"), sv.data.get("taint_reasons")
    assert sv.owns_book("r_dmg")
    assert all(b["key"] != "r_second_wind" for b in sv.unlocked_books())
    run = K.RunState(sv, "default", "normal", ach=K._AdAch())
    run.save.save = lambda *a, **k: None
    run.save.progress_changed = lambda *a, **k: None
    run.chests_opened = 2
    run.finish_run()
    assert sv.data["stats"]["total_chests"] == 2


def test_score_checks_with_boosts():
    """Efsanevi boost'larla şişen silah hasarı skor denetimini tetiklememeli:
    denetim hasarı oyuncunun eff_dmg'sinden ölçer (boost ona girmez), skor
    denetimi de öldürme/dalga/süreye bakar."""
    run = _run()
    p = run.player
    for k in ("axe", "whip", "tornado", "zemzem"):
        p.weapons[k] = 10
        p.weapon_boost[k] = K.WEAPON_BOOST_CAP
    p.run_luck_bonus = 3.0
    assert K.run_integrity_check(run) is None



def test_v331_reroll_goblin_cave():
    run = _run()
    # yenileme ucuzladı: bedavalardan sonra 40, 50, 70 ...
    run.reroll_used = run.REROLL_FREE
    assert run.reroll_cost() == 40
    run.reroll_used = run.REROLL_FREE + 4
    assert run.reroll_cost() < 150
    # kitap kartından kazanılan bedava hak önce harcanır
    run.pending_levelups = 1
    run.start_levelup_choice()
    run.reroll_bonus = 1
    assert run.reroll_cost() == 0
    used = run.reroll_used
    ok, _msg = run.reroll_levelup()
    assert ok and run.reroll_bonus == 0 and run.reroll_used == used
    # hazine goblini: ganimet her kademede çökmeden
    run.waves.wave = 8
    run.spawn_goblin()
    g = next(e for e in run.enemies if e.kind == "goblin")
    assert g.contact_dps == 0
    orig = K.roll_rarity
    try:
        for t in range(5):
            K.roll_rarity = lambda luck, rnd=random, t=t: t
            run._goblin_loot(g)
    finally:
        K.roll_rarity = orig
    assert run.goblins_caught == 5 and run.reroll_bonus >= 1
    # v3.32: dalga olayları tamamen kaldırıldı
    assert not hasattr(K, "WAVE_EVENTS") and not hasattr(run, "wave_event")
    # mağara sessiz yerleşir, ekranda değildir
    run.spawn_cursed_shrine()
    sh = run.cursed_shrine
    assert not sh.discovered
    assert K.dist(sh.x, sh.y, run.player.x, run.player.y) > 600
    for key in ("cu.found", "cu.found_sub", "cu.map_label", "fx.goblin", "cu.once", "cu.collapsed",
                "w.hawk.name", "w.bats.name", "w.nova.name", "w.knives.name", "w.quake.name",
                "w.quake.desc", "b.r_wspd.name", "b.r_evade.desc", "bs.dmg", "bs.evade", "fx.evade"):
        row = K.STRINGS[key]
        assert len(row) == 5 and all(row), key


def test_v332_books_cave_quake():
    # --- kitap kazancı nadirliğe göre; nadir kitaplar sabit ---
    for key in K.BOOK_GAINS:
        assert key in K.BOOK_BY_KEY and not K.BOOK_BY_KEY[key].get("rare"), key
        g0 = dict(K.book_gain(key, 0, 1))
        g4 = dict(K.book_gain(key, 4, 1))
        for st in g0:
            assert g4[st] > g0[st], (key, st)
    for b in K.BOOKS:
        if not b.get("rare"):
            assert b["key"] in K.BOOK_GAINS, b["key"]
            # kitaplıkta yüzdeli/sayılı açıklama yok
            for lang in K.LANG_CODES:
                K.set_lang(lang)
                d = K.bk_desc(b)
                assert "%" not in d and not any(ch.isdigit() for ch in d.replace("5'e", "").replace("3+", "").replace("3 ", "")), (b["key"], d)
            K.set_lang("tr")
    p = K.Player("default")
    d0 = p.run_dmg_mult
    p.take_book("r_dmg", 0)
    assert abs(p.run_dmg_mult - d0 - 0.05) < 1e-9
    p.take_book("r_dmg", 4)
    assert abs(p.run_dmg_mult - d0 - 0.05 - 0.40) < 1e-9           # Efsanevi +%40
    assert abs(p.book_totals["dmg"] - 0.45) < 1e-9
    # geç seviyeler (16+) yarı güç
    for _ in range(14):
        p.take_book("r_dmg", 0)
    tot = p.book_totals["dmg"]
    p.take_book("r_dmg", 0)                                        # 17. seviye
    assert abs(p.book_totals["dmg"] - tot - 0.05 * K.BOOK_LATE_K) < 1e-9
    # kaçınma: darbeden sıyrılır, tavanı var
    e = K.Player("default")
    for _ in range(30):
        e.take_book("r_evade", 4)
    assert 0.3 < e.eff_evasion() < 0.37
    fx = K.EffectSystem()
    random.seed(3)
    dodged = 0
    for _ in range(400):
        e.hp = e.max_hp
        if e.take_damage(1, fx) == 0:
            dodged += 1
    assert 80 < dodged < 190, dodged
    # soğuma: silah bekleme kısalır
    run = _run()
    run.player.weapons = {"tesla": 3}
    run.player.weapon_speed_bonus = 0.5
    w = K.WEAPON_BY_KEY["tesla"]
    assert K.weapon_cooldown(w, 3) / 1.5 < K.weapon_cooldown(w, 3)
    # kitap kartı çizimi (5 dil) çökmesin
    surf = pygame.Surface((K.VIRTUAL_W, K.VIRTUAL_H))
    run.pending_levelups = 1
    run.start_levelup_choice()
    for lang in K.LANG_CODES:
        K.set_lang(lang)
        for key in ("r_dmg", "r_hp", "r_regen", "r_mag", "r_pierce", "r_swarm"):
            o = run._book_offer(K.BOOK_BY_KEY[key], 1, True)
            K.draw_levelup_card(surf, pygame.Rect(100, 100, 270, 330), o, run, 1.0, True)
    K.set_lang("tr")

    # --- mağara: vazgeçince ÇÖKER, bir daha açılmaz ---
    run = _run()
    run.spawn_cursed_shrine()
    sh = run.cursed_shrine
    run.open_cursed()
    assert run.curse_offers
    run.decline_curse()
    assert run.curse_offers is None and sh.used and not sh.in_range(run.player)

    # --- DEPREM: birikir, sonra patlar ---
    run = _run()
    p = run.player
    p.weapons = {"quake": 5}
    e = K.Enemy("tank", p.x + 60, p.y, 1.0, wave=5)
    run.enemies.append(e)
    hp0 = e.hp
    qk = K.QuakeCharge(p, K.quake_radius(5), 10.0, 5)
    run.quakes.append(qk)
    for _ in range(20):
        qk.update(1 / 60, run)
    assert e.hp == hp0 and qk.boom_t < 0                          # henüz birikiyor
    for _ in range(50):
        qk.update(1 / 60, run)
    assert e.hp < hp0                                             # patladı
    # MAYIN kaldırıldı; eski kayıtta mayını olan DEPREM'i açık bulur
    assert "mines" not in K.WEAPON_BY_KEY
    sv = _save(weapons_owned=["axe", "mines"])
    assert sv.owns_weapon("quake")


def test_v333_crash_trims_mutes():
    # --- ÇÖKME: lanetli koşuda patron gelince HUD 'surge' hatası verip
    # oyunu kapatıyordu. Lanet + patron + yoğunluk birlikte çizilebilmeli.
    run = _run()
    run.curse_score_bonus = 0.5
    run.waves.wave = 10
    run.waves.boss_pending = True
    run.update(1 / 60, {"left": 0, "right": 0, "up": 0, "down": 0, "mouse_down": False})
    surf = pygame.Surface((K.VIRTUAL_W, K.VIRTUAL_H))
    for _ in range(90):
        run.update(1 / 60, {"left": 0, "right": 0, "up": 0, "down": 0, "mouse_down": False})
        if run.bosses:
            break
    assert run.bosses, "patron doğmadı"
    K.draw_hud(surf, run, 1.0)
    run.bosses.clear()
    run.waves.surge_timer = 3.0
    K.draw_hud(surf, run, 1.0)
    # --- güvenlik ağı: tek karelik hata oyunu kapatmaz, kayda yazılır
    app = K.App()
    try:
        raise RuntimeError("deneme")
    except RuntimeError:
        assert app._frame_error()
    # --- %10 XP ve altın kısıntısı (elmas etkilenmez)
    assert abs(K.XP_TRIM - 0.90) < 1e-9 and abs(K.GOLD_TRIM - 0.90) < 1e-9
    assert abs(K.coin_drop_scale("arena") - K.COIN_DROP_SCALE * 0.90) < 1e-9
    p = K.Player("default")
    q = K.Player("default")
    p.gain_xp(10.0)
    assert abs(p.xp - 10.0 * p.eff_xp_mult() * K.XP_GAIN_SCALE) < 1e-6
    assert abs(K.XP_GAIN_SCALE - 1.40 * K.XP_GAIN_BUFFS[0] * K.XP_GAIN_BUFFS[1] * 0.90) < 1e-9
    del q
    # --- elmasla kapatma hakkı (+4 silah, +4 kitap)
    sv = _save(mastery={"m_wmute": 2, "m_bmute": 4}, gems=10 ** 6)
    assert sv.max_muted_weapons() == K.MAX_MUTED_WEAPONS + 2
    assert sv.max_muted_books() == K.MAX_MUTED_BOOKS + 4
    assert sv.mastery_maxed("m_bmute") and not sv.buy_mastery("m_bmute")
    sv.data["weapons_owned"] = [w["key"] for w in K.BOSS_WEAPONS]
    sv.data["weapons_muted"] = []
    for w in K.BOSS_WEAPONS[:9]:
        sv.toggle_weapon_mute(w["key"])
    assert len(sv.data["weapons_muted"]) == K.MAX_MUTED_WEAPONS + 2
    # mute dalları oyuncuya güç vermez
    K.MASTERY_SAVE[0] = sv
    try:
        m = K.Player("default")
    finally:
        K.MASTERY_SAVE[0] = None
    assert m.eff_dmg() == K.Player("default").eff_dmg()
    # --- tanıtım filmi: 2 dakika, ödül 300 elmas
    assert abs(K.GameTour.LENGTH - 120.0) < 1e-6 and K.AD_REWARD_GEMS == 300
    for lang in K.LANG_CODES:
        K.set_lang(lang)
        assert K._tc("a", "b", "c", "d", "e") == {"tr": "a", "en": "b", "es": "c",
                                                  "de": "d", "ru": "e"}[lang]
    K.set_lang("tr")


_NOINP = {"left": 0, "right": 0, "up": 0, "down": 0, "mouse_down": False}


def test_v334_maps_and_oaths():
    # --- HARİTALAR: kural uygulanır, değişince geri alınır, cehennemde biter
    run = _run()
    xp0, coin0 = run.player.run_xp_mult, run.player.run_coin_mult
    run.set_map_theme("jungle")
    assert abs(run.player.run_xp_mult - (xp0 + 0.12)) < 1e-9
    assert abs(run.waves.spawn_rate_mult - 1.12) < 1e-9
    assert run.waves.theme == "jungle" and run.waves.doom
    run.set_map_theme("desert")
    assert abs(run.player.run_xp_mult - xp0) < 1e-9          # orman payı geri alındı
    assert abs(run.player.run_coin_mult - (coin0 + 0.15)) < 1e-9
    assert abs(run.waves.enemy_speed_mult - 1.08) < 1e-9 and run.waves.theme == "desert"
    run.set_map_theme("frost")
    assert abs(run.wave_hp_mult(10) / K.arena_hp_mult(10) - 1.10) < 1e-6
    run.set_map_theme("stone")
    assert not run.waves.doom and run.waves.theme == "stone"
    assert set(K.MAP_THEMES) == set(K.MAP_RULES) == set(K.MAP_FLOOR_KEY)
    # --- YEMİNLER: her biri bir artı bir eksi; dürüst koşu denetime takılmaz
    for key, _ic, _col in K.OATHS:
        for skin in ("default", "immortal_merc", "green_titan", "shadow_hunter"):
            run = _run(skin)
            run.apply_oath(key)
            assert run.oath == key
            assert K.run_integrity_check(run) is None, (key, skin)
            assert run.player.max_hp >= 30 and run.player.hp == run.player.max_hp
    run = _run()
    hp0 = run.player.max_hp
    run.apply_oath("glass")
    assert run.player.max_hp == int(round(hp0 * 0.75))
    run = _run()
    run.apply_oath("blood")
    assert run.player.eff_regen() == 0.0 and run.player.vamp_level >= 1.0
    run = _run()
    run.apply_oath("feast")
    assert abs(run.waves.spawn_rate_mult - 1.15) < 1e-9
    run = _run()
    run.apply_oath("bulwark")
    sc = run.player.shield_charges
    run.player.shield_charges = 0
    run.player.take_damage = lambda *a, **k: 0               # kalkan harcanmasın
    for _ in range(int(K.OATH_BULWARK_EVERY * 30) + 5):
        run.update(1 / 30, _NOINP)
        if run.game_over:
            break
    assert sc >= 3 and run.player.shield_charges >= 1
    run = _run()
    run.apply_oath(None)                                     # yeminsiz
    assert run.oath is None


def test_v336_merchant_stays_all_run():
    run = _run()
    p = run.player
    run.update_camera(0, snap=True)
    run.spawn_merchant()
    m = run.merchant
    assert m is not None and not hasattr(run, "calm")
    # kameranın dışında, oyuncudan uzakta doğar (haritada işaretlenmez)
    assert not run.cam_rect().collidepoint(m.x, m.y)
    assert K.dist(m.x, m.y, p.x, p.y) > 600
    # DALGA 0 YOK: oyun hemen başlar, yaratık doğar, süre işler
    for _ in range(200):
        run.update(1 / 30, _NOINP)
        if run.enemies:
            break
    assert run.enemies and run.run_time > 0
    # uzaktayken E bir şey açmaz; yanına gidince açılır
    run.update(1 / 30, dict(_NOINP, use_pressed=True))
    assert not run.merchant_open
    p.x, p.y = m.x + 20, m.y
    run.enemies.clear()
    run.update(1 / 30, dict(_NOINP, use_pressed=True))
    assert run.merchant_open
    hand = run.merchant_offers()
    assert len(hand) == 3 and len({k for k, _t in hand}) == 3
    assert all(0 <= t_ < K.RARITY_COUNT and k in K.OATH_BY_KEY for k, t_ in hand)
    # aynı seviyede el DEĞİŞMEZ (konuşup durmak kademe çekmez) ...
    for _ in range(30):
        assert run.merchant_offers() == hand
    # ... seviye atlayınca yenilenir ve tüccarın şansı seviyeyle artar
    luck1 = run.merchant_luck()
    p.level += 5
    run.merchant_offers()
    assert run.merchant_hand_lvl == p.level
    assert abs(run.merchant_luck() - luck1 - 5 * K.MERCHANT_LUCK_PER_LEVEL) < 1e-9
    # yemin: kademesiyle uygulanır, koşuda TEK yemin, tüccar yerinde kalır
    run.choose_oath("glass", 3)
    assert run.oath == "glass" and run.oath_tier == 3 and not run.merchant_open
    assert m.done and run.merchant is m
    run.choose_oath("turtle", 4)
    assert run.oath == "glass" and run.oath_tier == 3
    run.update(1 / 30, dict(_NOINP, use_pressed=True))   # yine konuşulabilir
    assert run.merchant_open
    run.choose_oath(None)
    assert not run.merchant_open and run.oath == "glass"
    # kademe aralık dışına taşamaz
    run2 = _run()
    run2.choose_oath("glass", 99)
    assert run2.oath_tier == K.RARITY_COUNT - 1


def test_v336_tiered_oaths_fair():
    """Kademe yalnız GÜÇ tarafını büyütür, bedel aynı kalır; her kademe ve
    her skinle dürüst koşu hile denetimine takılmaz."""
    mult = K.OATH_TIER_MULT
    assert len(mult) == K.RARITY_COUNT and list(mult) == sorted(mult) and mult[0] == 1.0
    for key, _ic, _col in K.OATHS:
        vals = [K.oath_values(key, t) for t in range(K.RARITY_COUNT)]
        for a_, b_ in zip(vals, vals[1:]):
            if key == "bulwark":     # daha çok kalkan, daha KISA dolum süresi
                assert b_[0] >= a_[0] and b_[1] <= a_[1], (key, vals)
            else:
                assert all(y >= x for x, y in zip(a_, b_)), (key, vals)
        texts = [K.oath_up_text(key, t) for t in range(K.RARITY_COUNT)]
        assert all(texts) and len(set(texts)) >= 2, (key, texts)
        downs = set()
        for tier in range(K.RARITY_COUNT):
            for skin in ("default", "immortal_merc", "green_titan", "shadow_hunter"):
                run = _run(skin)
                p = run.player
                base = (p.max_hp, p.run_dmg_mult, p.run_spd_mult, p.run_aspd_mult, p.run_xp_mult,
                        p.run_coin_mult, p.enemy_hp_curse, p.regen_mult)
                run.choose_oath(key, tier)
                assert run.oath == key and run.oath_tier == tier
                assert K.run_integrity_check(run) is None, (key, tier, skin)
                assert p.max_hp >= 30 and p.hp == p.max_hp
                if skin == "default":
                    # bedel (eksi taraf) kademeden bağımsız
                    if key == "glass":
                        downs.add(p.max_hp / float(base[0]))
                    elif key == "gold_fever":
                        downs.add(round(p.enemy_hp_curse - base[6], 6))
                    elif key == "turtle":
                        downs.add(round(p.run_spd_mult - base[2], 6))
                    elif key == "scholar":
                        downs.add(round(p.run_dmg_mult - base[1], 6))
                    elif key in ("bulwark", "hawkeye"):
                        downs.add(round(p.run_aspd_mult - base[3], 6))
                    elif key == "hunter":
                        downs.add(round(p.run_coin_mult - base[5], 6))
                    elif key == "hoard":
                        downs.add(round(p.run_xp_mult - base[4], 6))
                    elif key == "blood":
                        downs.add(p.regen_mult)
                    elif key == "wind":
                        downs.add(run.oath_speed)
                    elif key == "feast":
                        downs.add(run.oath_spawn)
        if downs:
            assert len(downs) == 1, (key, downs)
    # güç tarafı gerçekten büyür
    lo, hi = _run(), _run()
    lo.choose_oath("glass", 0)
    hi.choose_oath("glass", K.RARITY_COUNT - 1)
    assert hi.player.run_dmg_mult > lo.player.run_dmg_mult
    lo, hi = _run(), _run()
    lo.choose_oath("bulwark", 0)
    hi.choose_oath("bulwark", K.RARITY_COUNT - 1)
    assert hi.player.shield_charges > lo.player.shield_charges and hi.oath_period < lo.oath_period


def test_v335_map_achievements_and_weapons():
    # 20 silahın 12'si harita başarımıyla açılır; BUZ İZİ = Buz Kıran + PAPUÇ
    gated = [w for w in K.BOSS_WEAPONS
             if any(r.get("kind") == "ach" and K.ACH_BY_ID.get(r["ach"], {}).get("map")
                    for r in K.weapon_reqs(w))]
    assert len(K.BOSS_WEAPONS) == 20 and len(gated) == 12
    fr = K.WEAPON_BY_KEY["frost"]
    kinds = sorted((r.get("kind"), r.get("ach") or r.get("weapon")) for r in K.weapon_reqs(fr))
    assert kinds == [("ach", "buz_kiran"), ("weapon", "shoe")]
    to = K.WEAPON_BY_KEY["tornado"]
    assert {r.get("ach") for r in K.weapon_reqs(to)} == {"kum_firtinasi", "col_ruzgari"}
    for a in K.MAP_ACHS:
        assert a["track"]["stat"] in K.MAP_ACH_STATS and a["map"] in ("frost", "jungle", "desert")
        for f in ("name", "desc", "how"):
            assert all(K.STRINGS["a.%s.%s" % (a["id"], f)])
    # Taş Meydan'da harita sayacı yok
    run = _run()
    run.kills = 5000
    assert run.map_stat_values() == {}
    # Buzul'da 1.000 öldürme -> başarım koşu içinde açılır, BUZ İZİ (papuç varsa) açılır
    sv = _save()
    sv.data["weapons_owned"] = ["shoe"]
    sv.data["achievements"] = {}
    ach = K.AchievementManager(sv, K._NullSteam())
    run = K.RunState(sv, "default", "normal", ach=ach)
    run.set_map_theme("frost")
    run.kills = 999
    run.check_map_achs()
    assert "buz_kiran" not in sv.data["achievements"]
    run.kills = 1000
    run.check_map_achs()
    assert "buz_kiran" in sv.data["achievements"]
    run.finish_run()
    assert sv.data["stats"]["frost_kills"] == 1000
    assert "frost" in sv.data["weapons_owned"]
    # en iyi değer sayaçları (max) toplanmaz
    run2 = K.RunState(sv, "default", "normal", ach=ach)
    run2.set_map_theme("frost")
    run2.waves.wave = 7
    run2.kills = 10
    run2.finish_run()
    assert sv.data["stats"]["frost_kills"] == 1010
    assert sv.data["stats"]["best_frost_wave"] == 7
    # ORMAN: arenanın "kırmızı" yaratığının yerine YILAN doğar ve sayılır
    run3 = _run()
    run3.set_map_theme("jungle")
    assert run3.waves.theme == "jungle"
    e = K.make_map_enemy("jungle", "red", run3.player.x + 30, run3.player.y, 1.0, 1.0, wave=3)
    assert e.kind == "red" and e.variant == "j_snake"
    surf = pygame.Surface((K.VIRTUAL_W, K.VIRTUAL_H))
    e.draw(surf, 1.0)
    run3.enemies.append(e)
    e.hp = 0
    e.alive = False
    run3.on_enemy_killed(e)
    other = K.make_map_enemy("jungle", "blue", 0, 0, 1.0, 1.0, wave=3)
    other.alive = False
    run3.on_enemy_killed(other)
    assert run3.snakes_killed == 1 and run3.map_stat_values()["jungle_snakes"] == 1
    # Taş Meydan'da yılan yok; eski "snake" türü de kalktı
    run4 = _run()
    assert run4.waves.theme == "stone"
    assert K.make_map_enemy(run4.waves.theme, "red", 0, 0, 1.0).variant is None
    assert "snake" not in K.ENEMY_DEFS


def test_v335_no_hell_and_doom():
    # Taş Meydan dışında 25. dalga patronu cehennem kapısı açmaz
    hp_k, dmg_k = K.doom_mult(K.HELL_PORTAL_WAVE)
    assert hp_k == 1.0 and dmg_k == 1.0
    hp_k, dmg_k = K.doom_mult(K.HELL_PORTAL_WAVE + 6)
    assert hp_k > 3.5 and dmg_k > 4.5
    wm = K.WaveManager("normal")
    wm.doom = True
    wm.wave = K.HELL_PORTAL_WAVE + 4
    e = K.Enemy("red", 0, 0, 1.0, 1.0, wave=wm.wave)
    d0, h0 = e.dmg, e.max_hp
    wm._doomify(e)
    assert abs(e.dmg / d0 - K.DOOM_DMG ** 4) < 1e-6 and abs(e.max_hp / h0 - K.DOOM_HP ** 4) < 1e-6


def test_v335_app_flow_and_world_gate():
    app = K.App()
    app.splash_t = 99
    # OYNA -> harita seçimi; varsayılan TAŞ MEYDAN
    app.open_map_select()
    assert app.state == K.STATE_MAP_SELECT and app.selected_map() == "stone"
    app.update_map_select(1 / 30, (0, 0), False)
    app.set_selected_map("frost")
    assert app.selected_map() == "frost"
    app.start_run()
    run = app.run
    assert app.state == K.STATE_PLAY and run.map_theme == "frost" and run.merchant is not None
    assert run.waves.theme == "frost" and not hasattr(run, "calm")
    # dünya sıralaması yalnız Taş Meydan'da
    run.game_over = True
    assert app.world_block_reason() is not None
    # tüccar akışı: E -> mağara -> yemin
    run.game_over = False
    run.merchant_offers()
    run.merchant_open = True
    app.update_play(1 / 30, K._NoKeys(), (640, 360), False, False, False)
    assert app.state == K.STATE_MERCHANT
    for _ in range(5):
        app.t += 1 / 30
        app.update_merchant(1 / 30, (0, 0), False)
    app.merchant_ui.stage = "oaths"
    app.update_merchant(1 / 30, (0, 0), False)
    app.update_merchant(1 / 30, app.merchant_ui.cards[0][0].center, False)
    for _ in range(20):
        app.t += 1 / 30
        app.update_merchant(1 / 30, (0, 0), False)
    app.update_merchant(1 / 30, app.merchant_ui.cards[0][0].center, True)
    key, tier = run.merchant_hand[0]
    assert app.state == K.STATE_PLAY and run.oath == key and run.oath_tier == tier
    app.handle_escape()
    assert app.state == K.STATE_PAUSE
    app.resume_run()
    assert app.state == K.STATE_PLAY
    # ayar: görev kutusu gizlenebilir
    assert K.CFG.get("show_quests", True)
    # tuş: yeniden başla eylemi var, varsayılanı R
    assert "restart" in K.KEY_ACTIONS and K.DEFAULT_KEYS["restart"] == ["r"]
    # metinler beş dilde
    for k in ["dr.title_oath", "q.title", "key.restart", "st.oath", "m.greet", "m.talk", "ms.title",
              "map.doom", "map.no_world", "ui.show_quests", "m.hint", "m.luck", "m.sworn", "m.ok",
              "m.one_oath", "m.later_sub"] + \
            ["oath.%s.%s" % (o[0], f) for o in K.OATHS for f in ("name", "up", "down")] + \
            ["q." + q for q in K.QUEST_DEFS]:
        assert len(set(K.STRINGS[k])) >= 2 and all(K.STRINGS[k]), k
    # tanıtım filmi hep taş arenada, tüccarsız oynar
    tour = K.GameTour(app)
    for _ in range(30 * 30):
        tour.update(1 / 30)
        if getattr(tour.sh, "run", None) is not None:
            break
    assert tour.sh.run.map_theme == "stone" and tour.sh.run.merchant is None
    assert tour.sh.state == K.STATE_PLAY
    K.set_lang("tr")


def test_v334_quests_pay_only_clean():
    for seed in range(30):
        qs = _run().roll_quests(random.Random(seed))
        assert [q["tier"] for q in qs] == [0, 1, 2]
        assert len({q["key"] for q in qs}) == 3
        assert all(K.QUEST_DEFS[q["key"]][2][q["tier"]] == q["goal"] for q in qs)
    run = _run()
    run.quests = [{"key": "kills", "tier": 0, "goal": 5, "done": False},
                  {"key": "level", "tier": 1, "goal": 1, "done": False},
                  {"key": "wave", "tier": 2, "goal": 99, "done": False}]
    run.kills = 6
    run.update_quests()
    assert [q["done"] for q in run.quests] == [True, True, False]
    run.finish_run()
    assert run.quest_gems == K.QUEST_GEMS[0] + K.QUEST_GEMS[1]
    assert run.gems_earned >= run.quest_gems
    bad = _run()
    bad.quests = [{"key": "kills", "tier": 2, "goal": 1, "done": False}]
    bad.kills = 5
    bad.cheat_flag = "hasar"
    bad.finish_run()
    assert bad.quest_gems == 0 and bad.gems_earned == 0


LANGS = ("tr", "en", "es", "de", "ru")


def test_v336_map_creatures_same_game():
    """Her haritanın 11 kendi yaratığı var; can, hasar, hız, ödül ve isabet
    alanı arenadaki karşılığıyla BİREBİR aynı (oyun mantığı değişmez)."""
    assert set(K.MAP_ROSTER) == {"frost", "jungle", "desert"}
    attrs = ("kind", "max_hp", "speed", "dmg", "contact_dps", "radius", "hit_r", "coin", "xp",
             "score", "armor")
    seen = set()
    for theme, roster in K.MAP_ROSTER.items():
        assert set(roster) == {"red", "blue", "yellow", "tank", "sprinter", "brute", "elite",
                               "bomber", "healer", "wizard", "stinger"}, theme
        for kind, var in roster.items():
            assert var not in seen
            seen.add(var)
            d = K.MAP_ENEMIES[var]
            assert d["base"] == kind and K.HELL_SHAPES.get(d["shape"]) == "_draw_" + d["shape"]
            assert not any(f in d for f in ("hp", "dmg", "radius")), var     # çarpan YOK
            for w in (1, 12, 30):
                a = K.Enemy(kind, 0, 0, 1.7, 1.0, wave=w)
                b = K.Enemy(None, 0, 0, 1.7, 1.0, wave=w, variant=var)
                for at in attrs:
                    assert getattr(a, at) == getattr(b, at), (var, w, at)
            e = K.make_map_enemy(theme, kind, 0, 0, 1.0)
            assert e.variant == var and e.map_var and not e.hellish
            for lg in LANGS:                                  # ad 5 dilde
                K.set_lang(lg)
                assert K.make_map_enemy(theme, kind, 0, 0, 1.0).disp_name
            K.set_lang("tr")
            assert all(K.STRINGS["en." + var]) and len(set(K.STRINGS["en." + var])) >= 2
    assert len(seen) == 33
    # cehennem yaratıkları eskisi gibi
    h = K.Enemy(None, 0, 0, 1.0, wave=3, variant="h_imp", biome="hell")
    assert h.hellish and not h.map_var
    # Taş Meydan / lanet türleri dokunulmadan döner
    assert K.make_map_enemy("stone", "red", 0, 0, 1.0).variant is None
    assert K.make_map_enemy("frost", "goblin", 0, 0, 1.0).variant is None


def test_v336_map_creatures_draw_inside_sprite():
    """Her yaratık her yönde ve her adımda gövde önbelleğinin içine sığar."""
    for var in K.MAP_ENEMIES:
        e = K.Enemy(None, 0, 0, 1.0, wave=5, variant=var)
        e.spawn_t = 9.0
        r = e.radius
        pad = int(r * 2.2) + 6
        for i in range(8):
            ang = i * math.tau / 8
            for walk, t, sc in ((0.0, 0.0, 0.0), (1.7, 1.3, 0.5), (4.1, 2.9, 2.0)):
                e.face_x, e.face_y = math.cos(ang), math.sin(ang)
                e.walk, e.shoot_cd = walk, sc
                spr = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
                K._GLOW_ON_ALPHA = True
                try:
                    e._draw_body(spr, pad, pad, t, r)
                finally:
                    K._GLOW_ON_ALPHA = False
                m = pygame.mask.from_surface(spr, 24)
                bb = m.get_bounding_rects()
                assert bb, var
                u = bb[0].unionall(bb[1:]) if len(bb) > 1 else bb[0]
                assert u.left > 0 and u.top > 0 and u.right < pad * 2 and u.bottom < pad * 2, (var, ang)
        e.hit_flash = 0.2                       # vuruş parlaması da çizilir
        e.draw(pygame.Surface((K.VIRTUAL_W, K.VIRTUAL_H)), 1.0)


def test_v336_map_spawns_and_shots():
    random.seed(11)
    run = _run()
    run.set_map_theme("desert")
    run.player.take_damage = lambda *a, **k: 0
    run.waves.wave = 16
    for _ in range(900):
        run.update(1 / 30, _NOINP)
    arena_kinds = set(K.MAP_ROSTER["desert"])
    mapped = [e for e in run.enemies if e.kind in arena_kinds]
    assert mapped and all(e.variant == K.MAP_ROSTER["desert"][e.kind] for e in mapped)
    # dönüşte haritayı değiştirmek takımı da değiştirir; cehennemde harita takımı yok
    run.set_map_theme("stone")
    assert run.waves.theme == "stone"
    # okçu (sarı) ve büyücü kendi mermi görselini atar; hasar arenanınkiyle aynı
    for kind, style in (("yellow", "arrow"), ("wizard", "arrow")):
        p = K.Player("default")
        p.x, p.y = 900.0, 900.0
        shots = {}
        for var_kind in (None, "desert"):
            e = (K.make_map_enemy(var_kind, kind, 900.0 + 260, 900.0, 1.0, wave=16) if var_kind
                 else K.Enemy(kind, 900.0 + 260, 900.0, 1.0, wave=16))
            e.spawn_t, e.shoot_cd = 2.0, 0.0
            projs = []
            for _ in range(60):
                e.update(1 / 30, p, run.fx, projs, enemies=[])
                if projs:
                    break
            assert projs, (kind, var_kind)
            shots[var_kind] = projs[0]
        assert shots["desert"].style == style and shots[None].style == "orb"
        assert abs(shots["desert"].dmg - shots[None].dmg) < 1e-9
        assert shots["desert"].r == shots[None].r and shots["desert"].poison == shots[None].poison
        surf = pygame.Surface((K.VIRTUAL_W, K.VIRTUAL_H))
        for st in ("orb", "icicle", "spit", "arrow"):
            K.EnemyProjectile(400, 300, 120, -40, 5, style=st).draw(surf, 1.0)


def test_v336_map_bosses():
    run = _run()
    for theme in ("frost", "jungle", "desert"):
        for kind in K.BOSS_ORDER:
            random.seed(3)
            a = K.Boss(kind, 900, 900, 1.0, 1.0, 15)
            random.seed(3)
            b = K.Boss(kind, 900, 900, 1.0, 1.0, 15, theme=theme)
            for at in ("max_hp", "speed", "dmg", "radius", "hit_r", "armor", "score", "coin", "xp",
                       "boss_index"):
                assert getattr(a, at) == getattr(b, at), (theme, kind, at)
            assert a.trait == b.trait and b.theme == theme and b.name != a.name
            assert all(K.STRINGS["bn.%s.%s" % (theme, kind)])
            surf = pygame.Surface((K.VIRTUAL_W, K.VIRTUAL_H))
            b.spawn_t = 9.0
            b.draw(surf, 1.0)
            b.draw(surf, 1.0, hud=False)
            # çağırdığı yaratıklar da haritanın
            b._summon_minions(run.fx)
            assert b.summoned_enemies
            assert all(e.variant == K.MAP_ROSTER[theme][e.kind] for e in b.summoned_enemies)
        for lg in LANGS:
            K.set_lang(lg)
            names = {K.Boss(k, 0, 0, 1.0, 1.0, 10, theme=theme).name for k in K.BOSS_ORDER}
            assert len(names) == 5
        K.set_lang("tr")
    # cehennem patronu harita kimliği almaz
    hb = K.Boss("warlord", 0, 0, 1.0, 1.0, 10, hellish=True, theme="frost")
    assert hb.theme is None and hb.name == K.HELL_BOSS_NAMES["warlord"]
    # oyunda: harita koşusunun patron dalgası haritanın patronunu getirir
    run = _run()
    run.set_map_theme("jungle")
    run.waves.wave = 10
    run.waves.boss_pending = True
    run.update(1 / 30, _NOINP)
    assert run.bosses and all(bb.theme == "jungle" for bb in run.bosses)


def test_v336_map_select_screen():
    app = K.App()
    app.splash_t = 99

    def step(n, mouse=(0, 0), click=False):
        for i in range(n):
            app.t += 1 / 30
            app.update_map_select(1 / 30, mouse, click and i == 0)
    app.open_map_select()
    step(12)                                        # manzaralar hazırlanır
    for th in K.MAP_THEMES:
        assert (th,) + K.MS_CARD_SCENE in K._MAP_SCENES and (th,) + K.MS_BIG_SCENE in K._MAP_SCENES
    # karta tıkla -> kart büyüyüp ayrıntı penceresine dönüşür
    c = K._ms_card_rect(2)
    step(1, c.center, True)
    assert app._ms_zoom == "jungle" and app.selected_map() == "jungle"
    assert 0.0 <= app.ms_zoom_k() < 1.0
    step(12, (700, 160))
    assert app.ms_zoom_k() == 1.0
    # ESC önce pencereyi kapatır, sonra menüye döner
    app.handle_escape()
    step(12)
    assert app.state == K.STATE_MAP_SELECT and app._ms_zoom is None
    # ok tuşu yokken pencere dışına tıklamak da kapatır
    step(1, K._ms_card_rect(3).center, True)
    step(12)
    assert app._ms_zoom == "desert"
    step(1, (5, 5), True)
    step(12)
    assert app._ms_zoom is None
    # ayrıntı penceresinden BAŞLA: o harita başlar
    step(1, K._ms_card_rect(1).center, True)
    step(12)
    bs = pygame.Rect(K.MS_WIN_RECT.x + 20 + 162, K.MS_WIN_RECT.bottom - 62, K.MS_BIG_SCENE[0] - 162, 46)
    step(1, bs.center, True)
    assert app.state == K.STATE_PLAY and app.run.map_theme == "frost"
    # her dilde ve her haritada çizilir (taşan / eksik metin hata vermez)
    app.open_map_select()
    for lg in LANGS:
        K.set_lang(lg)
        step(2)
        for i, th in enumerate(K.MAP_THEMES):
            app.set_selected_map(th)
            app.ms_open_zoom(th, i)
            app._ms_zoom_t0 -= 1.0
            step(2, (640, 160))
            app._ms_zoom = None
    K.set_lang("tr")
    for k in ["ms.tap", "ms.creatures", "ms.creatures_sub", "ms.creatures_stone", "ms.hover_hint",
              "ms.bosses", "ms.boss_waves", "ms.hell_bosses", "ms.weapons", "ms.stone_weapons",
              "ms.rules", "ms.same", "ms.stone_note", "ms.badge_world", "ms.badge_hell",
              "ms.weap_done", "ms.record", "ms.r_score", "ms.r_wave", "ms.r_kills", "ms.r_bosses",
              "ms.r_time", "ms.r_dashes"] + ["ms.tag." + th for th in K.MAP_THEMES] + \
            ["ms.role." + k for k in K.MS_BEST_KINDS]:
        assert len(set(K.STRINGS[k])) >= 2 and all(K.STRINGS[k]), k
    app.handle_escape()
    assert app.state == K.STATE_MENU


def test_v336_pause_quest_toggle_and_backgrounds():
    app = K.App()
    app.splash_t = 99
    app.start_run()
    app.handle_escape()
    assert app.state == K.STATE_PAUSE
    app.update_pause(1 / 30, (0, 0), False)
    was = bool(K.CFG.get("show_quests", True))
    app.update_pause(1 / 30, app.pause_quest_rect.center, True)
    assert bool(K.CFG.get("show_quests", True)) == (not was)
    assert app.save.data["settings"]["show_quests"] == (not was)
    app.update_pause(1 / 30, app.pause_quest_rect.center, True)
    assert bool(K.CFG.get("show_quests", True)) == was
    # KİTAPLIK ve KIYAFET MARKET kendi arka planlarını çizer
    surf = pygame.Surface((K.VIRTUAL_W, K.VIRTUAL_H))
    for t in (0.0, 3.7, 61.2):
        K.draw_library_bg(surf, t)
        K.draw_wardrobe_bg(surf, t)
    for st, fn in ((K.STATE_BOOK_MARKET, app.update_book_market),
                   (K.STATE_COSMETIC_MARKET, app.update_cosmetic_market)):
        app.goto(st)
        for _ in range(3):
            app.t += 1 / 30
            fn(1 / 30, (0, 0), False, 0)


if __name__ == "__main__":
    print("roll_rarity dağılımı (20.000 çekiliş):")
    print("  şans   | Yaygın | Sıradışı | Nadir | Epik  | Efsanevi")
    for luck, pct in rarity_report():
        print("  %%%-5d | %6.1f | %8.1f | %5.1f | %5.1f | %8.2f" % (
            round(luck * 100), pct[0], pct[1], pct[2], pct[3], pct[4]))
    names = [n for n in sorted(globals()) if n.startswith("test_")]
    for n in names:
        globals()[n]()
        print("OK ", n)
