"""ARENA BONK — başsız SİLAH DENGE ölçümü (v3.30).

Her silahı TEK BAŞINA (oyuncunun kendi tüfeği susturulmuş) iki senaryoda
oynatır ve saniyelik hasarı ölçer:

  tek   : 140 px ötede kıpırdamayan, ölmeyen tek hedef (patron dövüşü).
  sürü  : çevrede hep 36 yaratık (8. dalga kırmızıları + tanklar); ölen
          yerine yenisi doğar. Gerçek (canı aşmayan) hasar ve öldürme sayılır.

Sonuçlar oyuncunun vuruş hasarına (eff_dmg) bölünür, yani "oyuncu
tüfeğinin kaç katı" diye okunur. Kullanım:

    python tools/weapon_bench.py                 # bütün silahlar
    python tools/weapon_bench.py --keys wolves tesla --levels 1 8 15 25
"""
import os
import sys
import math
import random
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import kasma_arena13 as K  # noqa: E402
import pygame  # noqa: E402


def _save():
    data = K.json.loads(K.json.dumps(K.SaveManager.DEFAULT))
    data["books_owned"] = [b["key"] for b in K.BOOKS]
    data["weapons_owned"] = [w["key"] for w in K.BOSS_WEAPONS]
    return K._AdSave(data)


def _new_run(seed):
    random.seed(seed)
    run = K.RunState(_save(), "default", "normal", ach=K._AdAch())
    run.waves.update = lambda *a, **k: False       # doğum yok: sahayı biz kurarız
    run.waves.wave = 8
    p = run.player
    p.no_stats = True
    p.invuln = 1e9
    return run


def _spawn(run, kind, r_lo=90, r_hi=380):
    p = run.player
    a = random.uniform(0, math.tau)
    rr = random.uniform(r_lo, r_hi)
    e = K.Enemy(kind, p.x + math.cos(a) * rr, p.y + math.sin(a) * rr,
                run.wave_hp_mult(8), 1.0, wave=8)
    e.contact_dps = 0.0
    e.dmg = 0.0
    run.enemies.append(e)
    return e


def bench(key, lvl, scenario, secs=14.0, seed=3, dt=1 / 30.0):
    run = _new_run(seed)
    p = run.player
    p.weapons = {key: lvl}
    p.weapon_timers = {key: 0.3}
    dealt = [0.0]
    orig = K.Enemy.take_damage

    def td(self, amount, *a, **kw):
        before = max(0.0, self.hp)
        died = orig(self, amount, *a, **kw)
        dealt[0] += min(before, max(0.0, before - max(0.0, self.hp)))
        return died
    K.Enemy.take_damage = td
    try:
        if scenario == "tek":
            dummy = K.Enemy("tank", p.x + 140, p.y, 1.0, 1.0, wave=8)
            dummy.max_hp = dummy.hp = 1e12
            dummy.speed = 0.0
            dummy.contact_dps = 0.0
            dummy.armor = 0.0
            run.enemies.append(dummy)
        else:
            for i in range(36):
                _spawn(run, "tank" if i % 6 == 0 else "red")
        kills0 = run.kills
        t = 0.0
        while t < secs:
            near = min(run.enemies, key=lambda e: K.dist(p.x, p.y, e.x, e.y)) if run.enemies else None
            inp = {"left": 0, "right": 0, "up": 0, "down": 0, "mouse_down": False,
                   "use_pressed": False, "bonk_pressed": False, "dash_pressed": False}
            if near is not None:
                inp["aim_x"], inp["aim_y"] = near.x, near.y
            run.update(dt, inp)
            run.pending_levelups = 0
            run.pickups.clear()
            if scenario == "tek":
                for e in run.enemies:
                    e.hp = e.max_hp
            else:
                alive = [e for e in run.enemies if e.alive]
                for _ in range(36 - len(alive)):
                    _spawn(run, "tank" if random.random() < 0.17 else "red", 300, 420)
            t += dt
        base = max(1e-6, p.eff_dmg())
        return dealt[0] / secs / base, (run.kills - kills0) / secs * 60.0
    finally:
        K.Enemy.take_damage = orig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", nargs="*", default=None)
    ap.add_argument("--levels", nargs="*", type=int, default=[1, 8, 15, 25])
    ap.add_argument("--secs", type=float, default=14.0)
    a = ap.parse_args()
    pygame.init()
    pygame.display.set_mode((K.VIRTUAL_W, K.VIRTUAL_H))
    keys = a.keys or [w["key"] for w in K.BOSS_WEAPONS if w["key"] != "cloak"]
    print("silah         sv | tek hedef (x tüfek) | sürü DPS (x tüfek) | sürü öldürme/dk")
    for key in keys:
        for lvl in a.levels:
            st, _ = bench(key, lvl, "tek", a.secs)
            sw, kpm = bench(key, lvl, "suru", a.secs)
            print(f"{key:13s} {lvl:2d} | {st:19.2f} | {sw:18.2f} | {kpm:8.0f}", flush=True)


if __name__ == "__main__":
    main()
