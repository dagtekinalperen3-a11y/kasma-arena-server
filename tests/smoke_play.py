"""
ARENA BONK — BAŞTAN SONA OYNANIŞ TESTİ (ekransız)

Oyunu gerçek ekran akışından oynatır: menü -> koşu -> seviye kartları ->
koşu marketi -> 10. ve 15. dalga patronları -> 25. dalga cehennem kapısı ->
cehennem -> ölüm -> sonuç ekranı. Sonra bütün menü ekranlarında rastgele
tıklar. Herhangi bir hata (exception) testi düşürür.

Ayrıca bu sürümdeki değişiklikleri ölçer:
  * zemzem yalnızca ekranda görünen yere düşüyor mu
  * patron varken yaratık gelmeye devam ediyor mu (yarı hızda)
  * kişisel rekor geçilince "YENİ REKOR" damgası çıkıyor mu

Çalıştırma:   python tests/smoke_play.py [--fast]
"""
import importlib.util
import math
import os
import random
import sys
import tempfile
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = tempfile.mkdtemp(prefix="arenabonk_smoke_")
os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", HOME=HOME,
                  APPDATA=HOME, XDG_DATA_HOME=HOME)

spec = importlib.util.spec_from_file_location("ka", os.path.join(ROOT, "kasma_arena13.py"))
ka = importlib.util.module_from_spec(spec)
sys.modules["ka"] = ka
spec.loader.exec_module(ka)
ka.ONLINE_API_URL = ""
import pygame  # noqa: E402

FAST = "--fast" in sys.argv
DT = 1 / 20
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("  OK   " if cond else "  HATA ") + name + (("  — " + str(detail)) if detail else ""))


class BotKeys:
    """pygame.key.get_pressed yerine: yalnızca botun bastığı yön tuşları."""

    def __init__(self):
        self.down = set()

    def press(self, **dirs):
        self.down = set()
        for action, on in dirs.items():
            if on:
                self.down.update(ka.key_codes(action))

    def __getitem__(self, k):
        return k in self.down


def play_run(app, until_wave, hell_until=0, god=True, max_frames=60000):
    """Koşuyu gerçek ekran fonksiyonlarıyla oynatır. İstatistik döndürür."""
    keys = BotKeys()
    st = dict(levelups=0, shop_opens=0, boss_frames=0, boss_spawned=0, normal_spawned=0,
              normal_frames=0, zemzem_drops=0, zemzem_off=0, max_enemies=0, frames=0,
              hell=False, gold_by_wave={}, level_by_wave={}, record_seen=False,
              slow=[], waves_seen=set())
    ang = 0.0
    bonk_cd = dash_cd = 0.0
    shop_cd = 20.0
    rng = random.Random(7)
    for frame in range(max_frames):
        run = app.run
        st["frames"] = frame
        s = app.state
        t0 = time.perf_counter()
        if s == ka.STATE_PLAY:
            p = run.player
            if god and p.alive:
                p.hp = max(p.hp, p.max_hp * 0.6)
                p.invuln = max(p.invuln, 0.3)   # hedef dalgaya kadar ölmesin
            ang += DT * 0.6
            near, nd, close = None, 1e18, 0
            mx = math.cos(ang) * 0.5
            my = math.sin(ang) * 0.5
            for e in [e for e in run.enemies if e.alive] + [b for b in run.bosses if b.alive]:
                d = (e.x - p.x) ** 2 + (e.y - p.y) ** 2
                if d < nd:
                    near, nd = e, d
                if d < 160 * 160:
                    close += 1
                    k = 1.0 / max(20.0, math.sqrt(d))
                    mx -= (e.x - p.x) * k
                    my -= (e.y - p.y) * k
            use = False
            portal = getattr(run, "hell_portal", None)
            if portal is not None and run.biome != "hell" and run.waves.wave >= until_wave:
                mx, my = portal.x - p.x, portal.y - p.y
                use = math.hypot(mx, my) < 90
            keys.press(left=mx < -0.15, right=mx > 0.15, up=my < -0.15, down=my > 0.15)
            if near is not None:
                aim = run.world_to_screen(near.x, near.y)
            else:
                aim = (ka.VIRTUAL_W / 2 + 100, ka.VIRTUAL_H / 2)
            bonk_cd -= DT
            dash_cd -= DT
            bonk = close >= 4 and bonk_cd <= 0
            if bonk:
                bonk_cd = 1.5
            dash = close >= 8 and dash_cd <= 0
            if dash:
                dash_cd = 2.5
            n_before = len(run.water_zones)
            boss_up = bool(run.bosses) or run.waves.boss_pending
            ids_before = {id(e) for e in run.enemies}
            app.update_play(DT, keys, aim, True, bonk, dash, use_pressed=use)
            new = [e for e in run.enemies if id(e) not in ids_before]
            if boss_up:
                st["boss_frames"] += 1
                st["boss_spawned"] += len(new)
            else:
                st["normal_frames"] += 1
                st["normal_spawned"] += len(new)
            # zemzem: yeni birikintiler ekranda mı?
            vis = run.cam_rect()
            for wz in run.water_zones[n_before:]:
                st["zemzem_drops"] += 1
                if not vis.collidepoint(wz.x, wz.y):
                    st["zemzem_off"] += 1
            st["max_enemies"] = max(st["max_enemies"], len(run.enemies))
            if getattr(run, "record_flash", -1.0) >= 0:
                st["record_seen"] = True
            w = run.waves.wave
            key = ("H" if run.biome == "hell" else "A") + str(w)
            if key not in st["waves_seen"]:
                st["waves_seen"].add(key)
                st["gold_by_wave"][key] = int(run.gold_wallet)
                st["level_by_wave"][key] = int(p.level)
            if run.biome == "hell":
                st["hell"] = True
                if run.waves.wave >= hell_until:
                    god = False
            elif run.waves.wave >= until_wave and not hell_until:
                god = False
            # marketi ara sıra aç (gerçek oyuncu gibi)
            shop_cd -= DT
            if shop_cd <= 0 and app.state == ka.STATE_PLAY and run.gold_wallet >= 60:
                shop_cd = 45.0
                app.state = ka.STATE_RUN_SHOP
                st["shop_opens"] += 1
        elif s == ka.STATE_LEVELUP:
            app.update_levelup(DT, (-50, -50), False)
            cards = app.levelup_ui.cards
            if cards:
                rect = rng.choice(cards)[0]
                app.update_levelup(DT, rect.center, True)
                st["levelups"] += 1
        elif s == ka.STATE_RUN_SHOP:
            for _ in range(3):
                pos = (rng.randint(180, 1100), rng.randint(150, 560))
                app.update_run_shop(DT, pos, True)
            app.update_run_shop(DT, (ka.VIRTUAL_W // 2, ka.VIRTUAL_H - 31), True)
            if app.state == ka.STATE_RUN_SHOP:
                app.state = ka.STATE_PLAY
        elif s in (ka.STATE_GAMEOVER, ka.STATE_NAME_ENTRY):
            break
        elif s == ka.STATE_PAUSE:
            app.state = ka.STATE_PLAY
        else:
            break
        st["slow"].append(time.perf_counter() - t0)
        if app.run is None:
            break
    return st


def fuzz_screens(app, frames=40):
    rng = random.Random(11)
    errs = []
    states = [ka.STATE_MENU, ka.STATE_SKIN_MARKET, ka.STATE_COSMETIC_MARKET, ka.STATE_BOOK_MARKET,
              ka.STATE_WEAPON_CODEX, ka.STATE_LEADERBOARD, ka.STATE_WORLD_LB, ka.STATE_HOW_TO,
              ka.STATE_SETTINGS, ka.STATE_ACHIEVEMENTS, ka.STATE_GEM_STORE, ka.STATE_LOGIN,
              ka.STATE_MASTERY, ka.STATE_KEYS]
    for stt in states:
        for i in range(frames):
            if app.state not in states or app.state == ka.STATE_PLAY:
                app.state = stt
            if i == 0:
                app.state = stt
            mouse = (rng.randint(0, ka.VIRTUAL_W), rng.randint(0, ka.VIRTUAL_H))
            clicked = rng.random() < 0.25
            # oyundan çıkma / hesap / ödeme düğmeleri test dışı
            app.running = True
            try:
                s = app.state
                app.t += DT
                if s == ka.STATE_MENU:
                    app.update_menu(DT, mouse, clicked)
                elif s == ka.STATE_SKIN_MARKET:
                    app.update_skin_market(DT, mouse, clicked, rng.choice((0, 0, 1, -1)))
                elif s == ka.STATE_SKIN_DETAIL:
                    app.update_skin_detail(DT, mouse, clicked)
                elif s == ka.STATE_COSMETIC_MARKET:
                    app.update_cosmetic_market(DT, mouse, clicked, rng.choice((0, 1, -1)))
                elif s == ka.STATE_BOOK_MARKET:
                    app.update_book_market(DT, mouse, clicked, rng.choice((0, 1, -1)))
                elif s == ka.STATE_WEAPON_CODEX:
                    app.update_weapon_codex(DT, mouse, clicked, rng.choice((0, 1, -1)))
                elif s == ka.STATE_LEADERBOARD:
                    app.update_leaderboard(DT, mouse, clicked)
                elif s == ka.STATE_WORLD_LB:
                    app.update_world_leaderboard(DT, mouse, clicked)
                elif s == ka.STATE_HOW_TO:
                    app.update_howto(DT, mouse, clicked)
                elif s == ka.STATE_SETTINGS:
                    app.update_settings(DT, mouse, clicked)
                elif s == ka.STATE_ACHIEVEMENTS:
                    app.update_achievements(DT, mouse, clicked, rng.choice((0, 1, -1)))
                elif s == ka.STATE_GEM_STORE:
                    app.update_gem_store(DT, mouse, clicked)
                elif s == ka.STATE_LOGIN:
                    app.update_login(DT, mouse, clicked)
                elif s == ka.STATE_MASTERY:
                    app.update_mastery(DT, mouse, clicked)
                elif s == ka.STATE_KEYS:
                    app.key_waiting = None
                    app.update_keys(DT, mouse, clicked)
                elif s == ka.STATE_NAME_ENTRY:
                    app.update_name_entry(DT, mouse, clicked)
                else:
                    app.state = stt
                if app.state == ka.STATE_PLAY and app.run is not None:
                    # menüden oyuna geçti: birkaç kare oyna ve geri dön
                    for _ in range(10):
                        app.update_play(DT, BotKeys(), mouse, True, False, False)
                    app.run = None
                    app.state = ka.STATE_MENU
            except Exception:
                errs.append((stt, app.state, traceback.format_exc()))
                app.state = stt
    return errs


def main():
    print("ARENA BONK baştan sona test")
    app = ka.App()
    sv = app.save
    for _ in range(200):                      # açılış + menü
        app.t += DT
        app.update_menu(DT, (-100, -100), False)
    check("menü açıldı", app.state == ka.STATE_MENU)

    # ---- KOŞU 1: arena 1 -> 25 + cehennem ----
    sv.data["stats"]["best_score"] = 400      # rekor kolayca geçilsin
    app.start_run()
    check("OYNA: koşu başladı", app.state == ka.STATE_PLAY and app.run is not None)
    app.run.player.weapons["zemzem"] = 6       # zemzem testi için (6. sv = 2 birikinti)
    t0 = time.time()
    until = 12 if FAST else ka.HELL_PORTAL_WAVE + 1
    try:
        st = play_run(app, until_wave=until, hell_until=0 if FAST else 3)
        err = None
    except Exception:
        err = traceback.format_exc()
        st = None
    check("koşu boyunca hata yok", err is None, err or "")
    if st is None:
        return 1
    run = app.run
    print("    süre %.0f sn, %d kare, dalga %d (%s), seviye %d, ölüm=%s" % (
        time.time() - t0, st["frames"], run.waves.wave, run.biome, run.player.level,
        not run.player.alive))
    check("seviye kartları seçildi", st["levelups"] >= 10, st["levelups"])
    check("koşu marketi açıldı", st["shop_opens"] >= 1, st["shop_opens"])
    check("patron dövüşü oldu", st["boss_frames"] > 0, st["boss_frames"])
    if st["boss_frames"] and st["normal_frames"]:
        br = st["boss_spawned"] / st["boss_frames"]
        nr = st["normal_spawned"] / st["normal_frames"]
        check("patron varken yaratık GELMEYE DEVAM ediyor", st["boss_spawned"] > 0,
              "patron sırasında %d yaratık" % st["boss_spawned"])
        check("patron varken doğum hızı normalin altında", br < nr,
              "kare başı patronlu %.3f / normal %.3f" % (br, nr))
    check("zemzem ekrandaki yere düşüyor", st["zemzem_drops"] == 0 or st["zemzem_off"] == 0,
          "%d birikinti, %d ekran dışı" % (st["zemzem_drops"], st["zemzem_off"]))
    check("rekor geçilince YENİ REKOR damgası çıktı", st["record_seen"])
    if not FAST:
        check("cehenneme girildi", st["hell"])
    lv = st["level_by_wave"]
    gd = st["gold_by_wave"]
    print("    seviye/altın (dalga başında):",
          ", ".join("%s: lv%d %dG" % (k, lv[k], gd[k]) for k in sorted(lv, key=lambda k: (k[0], int(k[1:])))))
    fr = sorted(st["slow"])
    if fr:
        print("    kare süresi (güncelle+çiz): ort %.1f ms, %%99 %.1f ms" % (
            1000 * sum(fr) / len(fr), 1000 * fr[int(len(fr) * 0.99)]))

    # ---- ÖLÜM + SONUÇ EKRANI ----
    if app.state != ka.STATE_GAMEOVER:
        run.player.hp = 0
        for _ in range(200):
            if app.state in (ka.STATE_GAMEOVER, ka.STATE_NAME_ENTRY):
                break
            run.player.hp = 0
            app.update_play(DT, BotKeys(), (640, 360), False, False, False)
    if app.state == ka.STATE_NAME_ENTRY:          # misafir rekor kırınca isim sorulur
        app.update_name_entry(DT, (-50, -50), False)
        app.name_input = "Bot"
        app.confirm_name_entry()
    check("ölünce sonuç ekranı", app.state == ka.STATE_GAMEOVER, app.state)
    try:
        for _ in range(120):
            app.t += DT
            app.update_gameover(DT, (-50, -50), False)
        shot = os.environ.get("SMOKE_SHOT") or os.path.join(HOME, "gameover.png")
        pygame.image.save(app.display.canvas, shot)
        err = None
    except Exception:
        err = traceback.format_exc()
    check("sonuç ekranı hatasız", err is None, err or "")
    check("kişisel rekor kaydedildi", sv.data["stats"]["best_score"] >= int(run.score),
          (sv.data["stats"]["best_score"], int(run.score)))
    check("koşu sayısı arttı", sv.data["stats"]["runs"] >= 1)
    sst = sv.data["stats"]
    print("    bir koşunun kitap sayaçları:", ", ".join(
        "%s=%s" % (k, int(sst.get(k, 0) or 0)) for k in (
            "total_kills", "total_shots", "total_lifesteal", "total_healed", "total_bonks",
            "total_bonk_hits", "total_dashes", "total_crits", "total_gold", "bosses")))

    # ---- MENÜ EKRANLARI ----
    sv.add_gems(5000)
    app.state = ka.STATE_MENU
    app.run = None
    errs = fuzz_screens(app, 30 if FAST else 60)
    check("bütün menü ekranlarında rastgele tıklama: hata yok", not errs,
          "\n".join("%s/%s:\n%s" % e for e in errs[:3]))
    check("elmas defteri tutarlı (hile damgası yok)", not sv.is_tainted(),
          sv.taint_text() if sv.is_tainted() else "")

    # ---- REKLAM (oyun turu) ----
    try:
        app._ad_start()
        for _ in range(int(20 / DT)):
            app.t += DT
            app.update_menu(DT, (-50, -50), False)
        err = None
    except Exception:
        err = traceback.format_exc()
    check("reklam (oyun turu) oynuyor", err is None, err or "")

    ok_n = sum(1 for _n, ok in RESULTS if ok)
    print("\nSONUÇ: %d / %d geçti" % (ok_n, len(RESULTS)))
    return 0 if ok_n == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
