"""ARENA BONK — başsız tempo/denge botu (v3.28).

Oyunun GERÇEK motoruyla (RunState) ekran açmadan bir koşu oynatır ve
şunları ölçer: her dalgaya kaçıncı saniyede girildi, o anki seviye, can,
silah/kitap takımı. Dalga temposu ve seviye eğrisi bu çıktıyla ayarlandı.

Kullanım:
    python tools/pace_sim.py                # 1 koşu, 16 dakika ya da ölüm
    python tools/pace_sim.py --runs 3 --minutes 18 --god
      --god : oyuncu ölmez (tempo ölçümü için; hasar yine sayılır)
      --dt  : simülasyon adımı (varsayılan 1/30 sn)
"""
import os
import sys
import math
import random
import argparse
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import kasma_arena13 as K  # noqa: E402

import pygame  # noqa: E402


def make_save():
    """Orta seviye bir oyuncunun kaydı: silahların ve kitapların çoğu açık."""
    data = K.json.loads(K.json.dumps(K.SaveManager.DEFAULT))
    data["books_owned"] = [b["key"] for b in K.BOOKS]
    data["weapons_owned"] = [w["key"] for w in K.BOSS_WEAPONS]
    return K._AdSave(data)


# Seviye kartı seçimi: önce silah takımını kur, sonra hasar/can kitapları.
BOOK_PREF = ["r_dmg", "r_aspd", "r_hp", "r_xp", "r_crit", "r_critd", "r_armor", "r_regen",
             "r_spd", "r_vamp", "r_mag", "r_coin"]


def pick_card(run):
    """Ortalama bir oyuncu gibi seçer: silah takımını ve kitap yuvalarını
    doldurur, sonra en düşük seviyeli parçayı büyütür."""
    best, best_s = 0, -1e9
    p = run.player
    for i, ch in enumerate(run.levelup_choices):
        s = random.random() * 4
        if ch["kind"] == "weapon":
            s += 30 if ch["new"] else 22 - 0.5 * p.weapons.get(ch["key"], 0)
        elif ch.get("rare"):
            s += 40
        else:
            k = ch["key"]
            pref = BOOK_PREF.index(k) if k in BOOK_PREF else 12
            s += (28 if ch["new"] else 22 - 0.5 * p.books.get(k, 0)) - pref * 0.6
        if s > best_s:
            best, best_s = i, s
    return best


SHOP_PREF = ["core_power", "core_speed", "core_vitality", "core_crit", "core_guard",
             "haste", "multishot", "vampiric", "heal", "shield", "pierce"]


def shop(run):
    for _ in range(6):
        bought = False
        for key in SHOP_PREF:
            if key in K.SHOP_BY_KEY and run.buy_shop_item(key):
                bought = True
        if not bought:
            break


class Bot:
    """İnsan gibi kaçan, en yakına nişan alan, kalabalıkta BONK/dash atan bot."""

    def __init__(self, run):
        self.run = run
        self.ang = random.uniform(0, math.tau)
        self.bonk = 0.5
        self.dash = 1.5

    def step(self, dt):
        run = self.run
        p = run.player
        self.ang += dt * 0.5
        cx, cy = K.ARENA_RECT.centerx, K.ARENA_RECT.centery
        tx = cx + math.cos(self.ang) * 520
        ty = cy + math.sin(self.ang) * 340
        mx, my = (tx - p.x) * 0.004, (ty - p.y) * 0.004
        near, nd, close = None, 1e18, 0
        for e in [e for e in run.enemies if e.alive] + [b for b in run.bosses if b.alive]:
            d = (e.x - p.x) ** 2 + (e.y - p.y) ** 2
            if d < nd:
                near, nd = e, d
            if d < 170 * 170:
                close += 1
                k = 1.0 / max(20.0, math.sqrt(d))
                mx -= (e.x - p.x) * k * k * 90
                my -= (e.y - p.y) * k * k * 90
        for pr in run.enemy_projectiles:
            d = (pr.x - p.x) ** 2 + (pr.y - p.y) ** 2
            if d < 120 * 120:
                k = 1.0 / max(20.0, math.sqrt(d))
                mx -= (pr.x - p.x) * k * k * 60
                my -= (pr.y - p.y) * k * k * 60
        # yerdeki eşyaya hafif çekim
        best = None
        for pu in run.pickups[:80]:
            d = (pu.x - p.x) ** 2 + (pu.y - p.y) ** 2
            if d < 260 * 260 and (best is None or d < best[0]):
                best = (d, pu)
        if best is not None and close < 3:
            mx += (best[1].x - p.x) * 0.006
            my += (best[1].y - p.y) * 0.006
        for mg in run.magnets + run.level_drops + run.chests:
            mx += (mg.x - p.x) * 0.01
            my += (mg.y - p.y) * 0.01
        ln = math.hypot(mx, my) or 1.0
        mx, my = mx / ln, my / ln
        inp = {"left": max(0.0, -mx), "right": max(0.0, mx), "up": max(0.0, -my),
               "down": max(0.0, my), "mouse_down": near is not None, "use_pressed": False}
        if near is not None:
            inp["aim_x"], inp["aim_y"] = near.x, near.y
        self.bonk -= dt
        self.dash -= dt
        inp["bonk_pressed"] = close >= 4 and self.bonk <= 0
        if inp["bonk_pressed"]:
            self.bonk = 1.4
        inp["dash_pressed"] = close >= 6 and self.dash <= 0
        if inp["dash_pressed"]:
            self.dash = 2.0
        run.update(dt, inp)


def play(minutes, dt, god, seed, diff="normal", verbose=True, strong=0.0):
    random.seed(seed)
    run = K.RunState(make_save(), "default", diff, ach=K._AdAch())
    run.player.no_stats = True
    if strong:
        # "güçlü oyuncu": ustalık + premium skin + iyi oynayış yerine kaba bir hasar/can payı
        run.player.run_dmg_mult += strong
        run.player.max_hp += int(100 * strong)
        run.player.hp = run.player.max_hp
    rare_lv = []
    bot = Bot(run)
    wave_at = {1: (0.0, 1, run.player.hp)}
    t = 0.0
    dmg_by_wave = {}
    last_wave = 1
    shop_t = 0.0
    while t < minutes * 60:
        if run.pending_levelups > 0:
            if not run.levelup_choices:
                run.start_levelup_choice()
            if run.levelup_choices:
                if any(c.get("rare") for c in run.levelup_choices):
                    rare_lv.append(run.levelup_hand_level())
                run.choose_levelup(pick_card(run))
            else:
                run.pending_levelups = 0
            continue
        hp0 = run.player.hp
        bot.step(dt)
        t += dt
        w = run.total_wave()
        lost = max(0.0, hp0 - run.player.hp)
        dmg_by_wave[w] = dmg_by_wave.get(w, 0.0) + lost
        if god and run.player.hp < run.player.max_hp * 0.35:
            run.player.hp = run.player.max_hp
            run.player.alive = True
            run.game_over = False
        if w != last_wave:
            wave_at[w] = (t, run.player.level, run.player.hp)
            last_wave = w
            shop(run)
        shop_t += dt
        if shop_t > 20:
            shop_t = 0
            shop(run)
        if run.game_over:
            break
        if run.hell_portal is not None and run.biome == "arena":
            run.enter_hell()
    p = run.player
    if verbose:
        print(f"seed={seed} t={t/60:.1f}dk  dalga={run.total_wave()}  sv={p.level}  "
              f"ölü={run.game_over}  kill={run.kills}  silah={p.weapons}  kitap={p.books}")
        goal_sum = sum(K.wave_score_goal(w) for w in range(1, run.total_wave() + 2))
        print(f"  skor={run.score}  skor/hedef_toplamı={run.score / goal_sum:.2f}  "
              f"skor/sn={run.score / max(1, run.run_time):.0f}  nadir kart seviyeleri={rare_lv[:12]}")
        for w in sorted(wave_at):
            ts, lv, hp = wave_at[w]
            print(f"  dalga {w:2d}: {ts/60:5.2f} dk  ({ts:6.0f} sn)  sv {lv:3d}  "
                  f"hasar alınan(önceki dalga) {dmg_by_wave.get(w-1, 0):7.0f}  maxhp {p.max_hp}")
    return run, wave_at


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--minutes", type=float, default=16)
    ap.add_argument("--dt", type=float, default=1 / 30.0)
    ap.add_argument("--god", action="store_true")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--diff", default="normal")
    ap.add_argument("--strong", type=float, default=0.0)
    a = ap.parse_args()
    pygame.init()
    pygame.display.set_mode((K.VIRTUAL_W, K.VIRTUAL_H))
    for i in range(a.runs):
        t0 = time.time()
        play(a.minutes, a.dt, a.god, a.seed + i, a.diff, strong=a.strong)
        print(f"  (gerçek süre {time.time() - t0:.0f} sn)")
