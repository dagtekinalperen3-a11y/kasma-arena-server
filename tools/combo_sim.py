"""
ARENA BONK — BAŞSIZ KOMBO SİMÜLATÖRÜ
=====================================================================
Oyunun GERÇEK motoruyla (RunState) ekran açmadan koşu oynatır. Otomatik
pilot: düşmanlardan kaçarak daire çizer, en yakına nişan alır, kalabalıkta
BONK, sıkışınca dash atar, altın/tecrübe/sandık toplar, markette alışveriş
yapar, seviye atlarken kendi KOMBOSUNU (4 silah, 4 normal kitap, 1 nadir
kitap) seçer ve 25. dalga patronundan sonra cehenneme girer.

Kullanım (depo kökünden):
    python tools/combo_sim.py one axe,whip,pentagram,tornado r_dmg,r_hp,r_armor,r_vamp r_killheal
    python tools/combo_sim.py xp            # seviye / dalga eğrisi ölçümü

Ayrıntılı tarama scripts'leri bu modülü içe aktarıp run_combo() çağırır.
"""
import os
import sys
import math
import json
import random
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.environ.get("KASMA_GAME_DIR", os.path.dirname(HERE))
sys.path.insert(0, GAME_DIR)

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((8, 8))
import kasma_arena13 as K  # noqa: E402


# ---------------------------------------------------------------------
# hızlandırma: görsel efektler oyunu etkilemez, simülasyonda boşa düşer
# ---------------------------------------------------------------------
def _noop(*_a, **_k):
    return None


for _n in ("spark", "burst", "ring", "shockwave", "bolt", "popup", "shake", "do_flash"):
    setattr(K.EffectSystem, _n, _noop)
K.sfx = _noop


def make_save():
    data = json.loads(json.dumps(K.SaveManager.DEFAULT))
    data["weapons_owned"] = [w["key"] for w in K.BOSS_WEAPONS]
    data["books_owned"] = [b["key"] for b in K.BOOKS]
    sv = K._AdSave(data)
    return sv


# Markette alınan eşyalar: (anahtar, en çok kaç seviye) — sırası öncelik.
SHOP_PLAN = [
    ("multishot", 3), ("core_power", 3), ("core_vitality", 3), ("haste", 2),
    ("bandage", 3), ("vampiric", 2), ("pierce", 2), ("core_speed", 3),
    ("core_guard", 3), ("iron_will", 3), ("quickdraw", 3), ("second_wind", 1),
    ("hunters_mark", 2), ("titan_shield", 2), ("phoenix_ash", 1),
    ("execute_edge", 1), ("storm", 2), ("vampiric", 4), ("multishot", 5),
    ("iron_will", 5), ("bandage", 6), ("haste", 5), ("second_wind", 3),
    # cehennem
    ("hell_ward", 3), ("dragon_heart", 2), ("purgatory", 2), ("brimstone", 3),
    ("infernal_core", 4), ("cursed_dagger", 2), ("hell_ward", 5),
    ("dragon_heart", 4), ("brimstone", 5),
]
# Bütün plan tükenince altın tavansız çekirdeklere akar.
ENDLESS = ["core_power", "core_vitality", "core_speed", "core_guard", "core_crit"]
ENDLESS_HELL = ["infernal_core", "core_vitality", "core_power", "core_guard"]

AURA_WEAPONS = {"pentagram", "shoe", "frost", "emanet", "whip", "book", "zemzem", "tornado"}


class Pilot:
    def __init__(self, run, weapons, books, rare, rnd):
        self.run = run
        self.weapons = list(weapons)
        self.books = list(books)
        self.rare = rare
        self.rnd = rnd
        self.circle = rnd.choice((-1.0, 1.0))
        self.shop_t = 0.0
        self.dash_hold = 0.0
        self.melee = len(AURA_WEAPONS & set(weapons)) >= 2
        self.last_heal_buy = -99.0

    # ------------------------------------------------------------ seviye
    def install_pool_filter(self):
        run = self.run
        allowed = set(self.weapons) | set(self.books) | {self.rare}
        orig = run.levelup_pool

        def pool():
            offers, weights = orig()
            keep = [(o, w) for o, w in zip(offers, weights) if o["key"] in allowed]
            if not keep:
                return offers, weights
            return [o for o, _ in keep], [max(1.0, w) for _, w in keep]
        run.levelup_pool = pool
        run.destiny_locked = set()
        run._combo_damp = lambda key: 1.0

    def offer_score(self, o):
        p = self.run.player
        key = o["key"]
        if o["kind"] == "weapon":
            if key not in self.weapons:
                return -10
            if o["new"]:
                return 100
            return 40 - p.weapons.get(key, 0)          # en düşük seviyeyi yükselt
        if o.get("rare"):
            return 90 if key == self.rare else -10
        if key not in self.books:
            return -10
        if o["new"]:
            return 80
        return 30 - p.books.get(key, 0) * 0.8

    def handle_levelups(self):
        run = self.run
        guard = 0
        while run.pending_levelups > 0 and guard < 50:
            guard += 1
            if not run.levelup_choices:
                run.start_levelup_choice()
            if not run.levelup_choices:
                run.pending_levelups = 0
                break
            sc = [self.offer_score(o) for o in run.levelup_choices]
            best = max(range(len(sc)), key=lambda i: sc[i])
            if sc[best] < 0:
                if run.rerolls_left_free() > 0:
                    run.reroll_levelup()
                    continue
                ok, _ = run.skip_levelup()
                if not ok:
                    run.choose_levelup(best)
                continue
            run.choose_levelup(best)

    # ------------------------------------------------------------ market
    def shop(self):
        run = self.run
        p = run.player
        # iksir: can yarının altındaysa
        hp_frac = p.hp / max(1.0, p.max_hp)
        heal = K.SHOP_BY_KEY["heal"]
        if hp_frac < 0.45 and run.run_time - self.last_heal_buy > 10.5:
            if run.buy_shop_item("heal"):
                self.last_heal_buy = run.run_time
        for _ in range(30):
            bought = False
            for key, cap in SHOP_PLAN:
                it = K.SHOP_BY_KEY[key]
                if not K.shop_item_unlocked(it, run.waves.wave, run.biome):
                    continue
                lvl = p.shop_levels.get(key, 0)
                if lvl >= min(cap, it.get("max", 999)):
                    continue
                cost = K.shop_item_cost(it, lvl)
                if cost <= run.gold_wallet:
                    bought = run.buy_shop_item(key)
                # plan sırasını koru: önceki satır tamamlanmadan ileri
                # yalnızca ucuzsa atlanır
                break
            if not bought:
                # plan bitti ya da sıradaki pahalı: tavansız çekirdekten en ucuzunu al
                pool = ENDLESS_HELL if run.biome == "hell" else ENDLESS
                plan_done = all(
                    p.shop_levels.get(k, 0) >= min(c, K.SHOP_BY_KEY[k].get("max", 999))
                    or not K.shop_item_unlocked(K.SHOP_BY_KEY[k], run.waves.wave, run.biome)
                    for k, c in SHOP_PLAN)
                if not plan_done:
                    break
                best, bc = None, 1e18
                for k in pool:
                    it = K.SHOP_BY_KEY[k]
                    if not K.shop_item_unlocked(it, run.waves.wave, run.biome):
                        continue
                    c = K.shop_item_cost(it, p.shop_levels.get(k, 0))
                    if c < bc:
                        best, bc = k, c
                if best and bc <= run.gold_wallet:
                    bought = run.buy_shop_item(best)
                if not bought:
                    break

    # ------------------------------------------------------------ hareket
    def step(self, dt):
        run = self.run
        p = run.player
        self.handle_levelups()
        self.shop_t -= dt
        if self.shop_t <= 0:
            self.shop_t = 1.0
            self.shop()

        hp_frac = p.hp / max(1.0, p.max_hp)
        rep_r = (150 + 110 * (1 - hp_frac)) if self.melee else 230
        rx = ry = 0.0
        near, nd = None, 1e18
        close = 0
        crowd_x = crowd_y = 0.0
        ncrowd = 0
        for e in run.enemies:
            if not e.alive:
                continue
            dx, dy = p.x - e.x, p.y - e.y
            d2 = dx * dx + dy * dy
            if d2 < nd:
                near, nd = e, d2
            if d2 < 600 * 600:
                crowd_x += e.x
                crowd_y += e.y
                ncrowd += 1
            if d2 < rep_r * rep_r:
                d = math.sqrt(d2) or 1.0
                w = (rep_r - d) / rep_r
                w = w * w * (1.0 + e.dmg / 25.0)
                rx += dx / d * w
                ry += dy / d * w
                if d < 85:
                    close += 1
        boss_t = None
        for b in run.bosses:
            if not b.alive:
                continue
            dx, dy = p.x - b.x, p.y - b.y
            d = math.hypot(dx, dy) or 1.0
            if boss_t is None or d < boss_t[1]:
                boss_t = (b, d)
            keep = 300 + b.radius
            if d < keep:
                w = ((keep - d) / keep) * 3.0
                rx += dx / d * w
                ry += dy / d * w
            if d < b.radius + 60:
                close += 3
        for hz in run.hazards:
            if hz.exploded:
                continue
            dx, dy = p.x - hz.x, p.y - hz.y
            d = math.hypot(dx, dy) or 1.0
            if d < hz.r + 50:
                w = 4.0 * (hz.r + 50 - d) / (hz.r + 50)
                rx += dx / d * w
                ry += dy / d * w
                if d < hz.r + p.radius and hz.delay - hz.t < 0.35:
                    close += 5
        for pr in run.enemy_projectiles:
            if not pr.alive:
                continue
            dx, dy = p.x - pr.x, p.y - pr.y
            d = math.hypot(dx, dy)
            if d > 230 or d < 1:
                continue
            vx, vy = getattr(pr, "vx", 0.0), getattr(pr, "vy", 0.0)
            sp = math.hypot(vx, vy)
            if sp < 1:
                continue
            # bize doğru mu geliyor?
            if (dx * vx + dy * vy) / (d * sp) < 0.6:
                continue
            # merminin yoluna dik kaç
            px_, py_ = -vy / sp, vx / sp
            side = 1.0 if (dx * px_ + dy * py_) >= 0 else -1.0
            w = 2.2 * (230 - d) / 230
            rx += px_ * side * w
            ry += py_ * side * w

        # kalabalığın çevresinde daire çiz (köşeye sıkışmamak için)
        mx, my = rx * 2.4, ry * 2.4
        if ncrowd:
            cx, cy = crowd_x / ncrowd, crowd_y / ncrowd
            dx, dy = p.x - cx, p.y - cy
            d = math.hypot(dx, dy) or 1.0
            tx, ty = -dy / d * self.circle, dx / d * self.circle
            mx += tx * 0.9
            my += ty * 0.9
            if self.melee and hp_frac > 0.55 and d > 200:
                # aura silahları: kalabalığın kenarına yaklaş
                mx -= dx / d * 0.5
                my -= dy / d * 0.5
        # duvar
        A = K.ARENA_RECT
        m = 260
        if p.x < A.left + m:
            mx += (A.left + m - p.x) / m * 3.0
        if p.x > A.right - m:
            mx -= (p.x - (A.right - m)) / m * 3.0
        if p.y < A.top + m:
            my += (A.top + m - p.y) / m * 3.0
        if p.y > A.bottom - m:
            my -= (p.y - (A.bottom - m)) / m * 3.0
        # toplanacaklar: sandık > portal > tecrübe/altın (güvenliyse)
        goal = None
        if run.chests:
            ch = min(run.chests, key=lambda c: (c.x - p.x) ** 2 + (c.y - p.y) ** 2)
            if not ch.opened:
                goal = (ch.x, ch.y, 1.6)
        if goal is None and run.hell_portal is not None and run.biome != "hell":
            goal = (run.hell_portal.x, run.hell_portal.y, 2.5)
        if goal is None and close == 0:
            best, bd = None, 340 * 340
            for pu in run.pickups:
                d2 = (pu.x - p.x) ** 2 + (pu.y - p.y) ** 2
                if d2 < bd:
                    best, bd = pu, d2
            for lv in run.level_drops + run.magnets:
                d2 = (lv.x - p.x) ** 2 + (lv.y - p.y) ** 2
                if d2 < 700 * 700:
                    best, bd = lv, 0
                    break
            if best is not None:
                goal = (best.x, best.y, 0.8)
        if goal is not None:
            gx, gy, gw = goal
            dx, dy = gx - p.x, gy - p.y
            d = math.hypot(dx, dy) or 1.0
            mx += dx / d * gw
            my += dy / d * gw
        ln = math.hypot(mx, my)
        if ln > 1e-6:
            mx, my = mx / ln, my / ln
        else:
            mx, my = 0.0, 0.0
        inp = {"left": max(0.0, -mx), "right": max(0.0, mx),
               "up": max(0.0, -my), "down": max(0.0, my)}
        # nişan: menzildeki patron, yoksa en yakın yaratık
        tgt = None
        if boss_t is not None and boss_t[1] < 560 and not boss_t[0].is_hidden():
            tgt = boss_t[0]
        elif near is not None:
            tgt = near
        if tgt is not None:
            inp["aim_x"], inp["aim_y"] = tgt.x, tgt.y
            inp["mouse_down"] = True
        bonk_r = p.eff_bonk_radius() * 0.8
        nb = 0
        for e in run.enemies:
            if e.alive and abs(e.x - p.x) < bonk_r and abs(e.y - p.y) < bonk_r:
                nb += 1
                if nb >= 3:
                    break
        inp["bonk_pressed"] = nb >= 3 or (boss_t is not None and boss_t[1] < bonk_r)
        inp["dash_pressed"] = close >= 3 or (hp_frac < 0.35 and close >= 1)
        inp["use_pressed"] = run.hell_portal is not None
        run.update(dt, inp)


def run_combo(weapons, books, rare, seed=0, diff="normal", dt=1 / 60.0,
              max_time=3600.0, trace=False, enter_hell=True, stop_wave=None):
    random.seed(seed)
    rnd = random.Random(seed * 7919 + 13)
    sv = make_save()
    K.MASTERY_SAVE[0] = sv
    run = K.RunState(sv, "default", diff, ach=K._AdAch())
    run.player.no_stats = True
    pilot = Pilot(run, weapons, books, rare, rnd)
    pilot.install_pool_filter()
    xp_total = [0.0]
    _gain = run.player.gain_xp

    def gain(amount):
        xp_total[0] += amount * run.player.eff_xp_mult() * K.XP_GAIN_SCALE
        return _gain(amount)
    run.player.gain_xp = gain
    xp_at = {}
    if not enter_hell:
        K.RunState.open_hell_portal  # noqa
        run.open_hell_portal = lambda: None
    t0 = time.time()
    lvl_at = {}
    trace_rows = []
    last_wave = 0
    while not run.game_over and run.run_time < max_time:
        pilot.step(dt)
        tw = run.total_wave()
        if tw != last_wave:
            last_wave = tw
            lvl_at[tw] = run.player.level
            xp_at[tw] = round(xp_total[0])
            if stop_wave and tw >= stop_wave:
                break
            if trace:
                p = run.player
                trace_rows.append((tw, round(run.run_time), p.level, int(run.score),
                                   dict(p.weapons), dict(p.books), int(p.hp), int(p.max_hp)))
    p = run.player
    res = {
        "weapons": weapons, "books": books, "rare": rare, "seed": seed,
        "wave": run.total_wave(), "arena_wave": run.arena_waves or run.waves.wave,
        "hell": run.biome == "hell", "score": int(run.score), "kills": int(run.kills),
        "level": p.level, "time": round(run.run_time, 1), "dead": bool(run.game_over),
        "cause": run.death_cause, "lvl_at": lvl_at, "xp_at": xp_at, "wall": round(time.time() - t0, 1),
        "wlv": dict(p.weapons), "blv": dict(p.books),
    }
    if trace:
        res["trace"] = trace_rows
    return res


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "one"
    if mode == "one":
        w = sys.argv[2].split(",")
        b = sys.argv[3].split(",")
        r = sys.argv[4]
        seed = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        res = run_combo(w, b, r, seed=seed, trace=True)
        for row in res.pop("trace"):
            print(row)
        print(json.dumps(res, ensure_ascii=False))
