"""
ARENA BONK — TANITIM VİDEOSU ÜRETİCİ  (~1.5 dakika, 1280x720, 30 FPS, sesli)

Video çizim taklidi DEĞİL: oyunun kendisi (kasma_arena13.py) ekransız
çalıştırılır, gerçek ekranlar ve gerçek koşular kare kare çekilir. Savaş
sahnelerini bir otomatik pilot oynar; menülerde sanal bir imleç gezinip
tıklar. Sesler ve müzik de oyunun kendi ses sentezinden gelir (SFX_BUILDERS,
_gen_music): oyun içinde hangi an hangi ses çalıyorsa videoda da o çalar.

Kayıt dosyana DOKUNMAZ: oyun geçici bir klasördeki boş bir kayıtla açılır.

Kullanım:
    pip install pygame numpy          (ffmpeg de kurulu olmalı)
    python tools/make_trailer.py                       -> arena_bonk_trailer.mp4
    python tools/make_trailer.py --out video.mp4
    python tools/make_trailer.py --preview 3,20,45     -> o saniyelerin PNG'leri

Sahneler (saniye):
    GİRİŞ · ANA MENÜ · SAVAŞ · SEVİYE ATLAMA · MARKET · PATRON · CEHENNEM
    KAPISI · CEHENNEM + CEHENNEM PATRONU · SİLAHLIK/KİTAPLIK/SKİN/BAŞARIM ·
    MAĞAZA · KAPANIŞ
"""
import argparse
import importlib.util
import math
import os
import random
import subprocess
import sys
import tempfile
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "kasma_arena13.py")
W, H, FPS = 1280, 720, 30
DT = 1.0 / FPS

# ---- oyunu ekransız ve geçici bir kayıtla aç ----
_tmp_home = tempfile.mkdtemp(prefix="arenabonk_trailer_")
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["HOME"] = _tmp_home
os.environ["APPDATA"] = _tmp_home
os.environ["XDG_DATA_HOME"] = _tmp_home

import numpy as np                     # noqa: E402

spec = importlib.util.spec_from_file_location("ka", GAME)
ka = importlib.util.module_from_spec(spec)
sys.modules["ka"] = ka
spec.loader.exec_module(ka)
ka.ONLINE_API_URL = ""
ka.NEW_YEAR_THEME = True
import pygame                          # noqa: E402


# =====================================================================
# SES KAYDI: oyunun çaldığı her ses (zamanıyla) not edilir
# =====================================================================
class Recorder:
    def __init__(self):
        self.events = []        # (zaman, ad, ses)
        self.music = []         # (zaman, ad)
        self.now = 0.0
        self._last = {}
        self.ok = True
        self.settings = {"sfx_vol": 0.7, "music_vol": 0.5}

    def play(self, name, vol=1.0, gap=0.03):
        if self.now - self._last.get(name, -9.0) < max(gap, 0.03):
            return
        self._last[name] = self.now
        self.events.append((self.now, name, float(vol)))

    def set_music(self, name):
        pass

    def update(self):
        pass

    def set_volumes(self, *a, **k):
        pass

    def __getattr__(self, _n):
        return lambda *a, **k: None


REC = Recorder()


# =====================================================================
# YARDIMCILAR
# =====================================================================
def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def lerp2(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def path_pos(keys, t):
    """keys: [(zaman, (x, y)), ...] — yumuşak geçişli imleç yolu."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            k = (t - t0) / max(1e-6, t1 - t0)
            k = k * k * (3 - 2 * k)
            return lerp2(p0, p1, k)
    return keys[-1][1]


class Overlay:
    """Altyazılar, tıklama halkaları, sahne geçişleri."""

    def __init__(self):
        self.clicks = []

    def click(self, pos, t):
        self.clicks.append((pos, t))

    def draw_clicks(self, surf, t):
        for (pos, t0) in self.clicks:
            k = (t - t0) / 0.45
            if 0 <= k <= 1:
                ka.ring_aa(surf, pos[0], pos[1], 8 + 34 * k, (255, 236, 170), max(1, int(5 * (1 - k))))

    @staticmethod
    def caption(surf, text, sub, st, dur, y=600, col=(255, 214, 120), x0=0):
        if st < 0 or st > dur:
            return
        k_in = ease(st / 0.45)
        k_out = ease((dur - st) / 0.35)
        k = min(k_in, k_out)
        tw = max(ka.text_width(text, 40, True), ka.text_width(sub, 22, True) if sub else 0) + 90
        x = x0 - tw + (tw + 50) * k
        h = 98 if sub else 70
        bar = pygame.Surface((int(tw), h), pygame.SRCALPHA)
        bar.fill((10, 8, 18, 220))
        surf.blit(bar, (int(x), y))
        pygame.draw.rect(surf, col, pygame.Rect(int(x + tw - 10), y, 10, h))
        ka.draw_text(surf, text, (int(x) + 30, y + 10), 40, col, bold=True)
        if sub:
            ka.draw_text(surf, sub, (int(x) + 32, y + 60), 22, (236, 232, 244), bold=True)

    @staticmethod
    def wipe(surf, st, dur=0.34):
        if st >= dur:
            return
        k = st / dur
        x0 = -260 + (W + 520) * k
        pygame.draw.polygon(surf, (236, 186, 92), [(x0, 0), (x0 + 300, 0), (x0 + 80, H), (x0 - 220, H)])
        pygame.draw.polygon(surf, (255, 242, 205), [(x0 + 230, 0), (x0 + 300, 0), (x0 + 80, H), (x0 + 10, H)])

    @staticmethod
    def corner_logo(surf):
        logo = ka.brand_scaled("logo", h=58)
        if logo is not None:
            img = logo.copy()
            img.set_alpha(215)
            surf.blit(img, (W - img.get_width() - 18, H - img.get_height() - 14))


OV = Overlay()


# =====================================================================
# OTOMATİK PİLOT
# =====================================================================
class Pilot:
    def __init__(self, run, crowd=30):
        self.run = run
        p = run.player
        self.cx, self.cy = p.x, p.y
        self.ang = random.uniform(0, math.tau)
        self.bonk = 0.5
        self.dash = 1.5
        self.crowd = crowd
        self.target = None          # (x, y): oraya yürü (portal, sandık)
        self.use = False
        self.aim = (W / 2, H / 2)

    def spawn(self):
        run = self.run
        x, y = run.near_camera_point()
        w = run.waves.wave
        if run.biome == "hell":
            run.enemies.append(ka.Enemy(None, x, y, run.wave_hp_mult(w), 1.0, wave=w,
                                        variant=ka.hell_pick_kind(w), biome="hell"))
        else:
            kind = random.choice(("red", "red", "blue", "yellow", "tank", "sprinter", "brute", "bomber"))
            run.enemies.append(ka.Enemy(kind, x, y, run.wave_hp_mult(w), 1.0, wave=w))

    def step(self, dt, keep_levelups=False):
        run = self.run
        p = run.player
        p.hp = p.max_hp
        if not keep_levelups:
            run.pending_levelups = 0
            run.levelup_choices = []
        run.want_open_shop = False
        if self.crowd:
            while len(run.enemies) < self.crowd:
                self.spawn()
        self.ang += dt * 0.55
        if self.target is not None:
            tx, ty = self.target
        else:
            tx = self.cx + math.cos(self.ang) * 230
            ty = self.cy + math.sin(self.ang) * 140
        mx, my = tx - p.x, ty - p.y
        near, nd, close = None, 1e18, 0
        targets = [e for e in run.enemies if e.alive] + [b for b in run.bosses if b.alive]
        for e in targets:
            d = (e.x - p.x) ** 2 + (e.y - p.y) ** 2
            if d < nd:
                near, nd = e, d
            if d < 150 * 150:
                close += 1
                if d < 95 * 95 and self.target is None:
                    k = 1.0 / max(20.0, math.sqrt(d))
                    mx -= (e.x - p.x) * k * 160
                    my -= (e.y - p.y) * k * 160
        ln = math.hypot(mx, my)
        if ln < 12 and self.target is not None:
            mx = my = 0.0
        else:
            ln = ln or 1.0
            mx, my = mx / ln, my / ln
        inp = {"left": max(0.0, -mx), "right": max(0.0, mx), "up": max(0.0, -my),
               "down": max(0.0, my), "mouse_down": near is not None, "use_pressed": self.use}
        if near is not None:
            inp["aim_x"], inp["aim_y"] = near.x, near.y
            self.aim = run.world_to_screen(near.x, near.y)
        self.bonk -= dt
        self.dash -= dt
        inp["bonk_pressed"] = close >= 4 and self.bonk <= 0
        if inp["bonk_pressed"]:
            self.bonk = 1.5
        inp["dash_pressed"] = close >= 7 and self.dash <= 0 and self.target is None
        if inp["dash_pressed"]:
            self.dash = 2.2
        run.update(dt, inp)


# =====================================================================
# YÖNETMEN
# =====================================================================
class Director:
    def __init__(self):
        random.seed(2026)
        self.app = ka.App()
        ka.audio = REC                     # sfx() artık kayda gider
        app = self.app
        app.splash_t = 99
        sv = app.save
        # Vitrin kaydı: zengin ekranlar için kilitler açık, biraz ilerleme var.
        sv.unlock_everything()
        sv.data["tainted"] = False
        sv.data["taint_reasons"] = []
        sv.add_gems(2450)
        st = sv.data.setdefault("stats", {})
        st.update(best_score=48250, best_wave=27, runs=42, total_kills=9120, bosses=14)
        ach = sv.data.setdefault("achievements", {})
        for a in ka.ACHIEVEMENTS[:15]:
            ach[a["id"]] = "24.12.2026"
        sv.data["equipped_skin"] = "prism"
        app.selected_skin = "prism"
        self.ov = OV
        self.t = 0.0
        self.music = []            # (zaman, "menu"/"battle")
        self.pilot = None

    # ------------------------------------------------------------------
    def canvas(self):
        return self.app.display.canvas

    def set_music(self, name):
        if not self.music or self.music[-1][1] != name:
            self.music.append((self.t, name))

    def play_frame(self, aim=None, cursor=True):
        app, run = self.app, self.app.run
        off = run.fx.get_shake_offset()
        aim = aim or self.pilot.aim
        app._draw_run_frame(self.canvas(), aim_pos=aim, offset=off)
        if cursor:
            ka.draw_cursor(self.canvas(), aim, "aim", app.t, hot=True)

    # ------------------------------------------------------------------
    # SAHNELER: her biri (süre, fonksiyon); fonksiyon (st, ilk_kare) alır
    # ------------------------------------------------------------------
    def s_intro(self, st, first):
        c = self.canvas()
        if first:
            self.set_music("menu")
            self._intro_bg = pygame.Surface((W, H)).convert()
            for y in range(H):
                pygame.draw.line(self._intro_bg, ka.mix_col((54, 30, 80), (10, 6, 20), y / H), (0, y), (W, y))
        c.blit(self._intro_bg, (0, 0))
        cx, cy = W / 2, H / 2 - 20
        lay = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(22):
            a = st * 0.22 + i * math.tau / 22
            pygame.draw.polygon(lay, (236, 186, 92, 30), [(cx, cy), (cx + math.cos(a - .05) * 1000, cy + math.sin(a - .05) * 1000),
                                                         (cx + math.cos(a + .05) * 1000, cy + math.sin(a + .05) * 1000)])
        c.blit(lay, (0, 0))
        ka.add_glow(c, cx, cy, 480, (210, 150, 60), 0.30 + 0.1 * min(1, st))
        # önce amblem düşer, sonra yazılı logo
        if st < 1.6:
            badge = ka.brand_scaled("badge", h=260)
            k = ease(st / 0.6)
            s_ = 0.3 + 0.7 * k + 0.08 * math.sin(min(1, st / 0.6) * math.pi)
            img = pygame.transform.smoothscale(badge, (int(260 * s_), int(260 * s_)))
            c.blit(img, (cx - img.get_width() / 2, cy - img.get_height() / 2))
            if st > 0.55:
                q = min(1.0, (st - 0.55) / 0.6)
                ka.ring_aa(c, cx, cy, 140 + 500 * q, (255, 230, 170), max(1, int(12 * (1 - q))))
                if "bonk0" not in getattr(self, "_marks", set()):
                    self._marks = {"bonk0"}
                    REC.play("bonk", 1.0, 0.0)
        else:
            logo = ka.brand_scaled("logo", w=900)
            k = ease((st - 1.6) / 0.5)
            s_ = 0.8 + 0.2 * k
            img = pygame.transform.smoothscale(logo, (int(logo.get_width() * s_), int(logo.get_height() * s_)))
            img.set_alpha(int(255 * k))
            c.blit(img, (cx - img.get_width() / 2, cy - img.get_height() / 2))
            if st > 2.6:
                a = int(255 * min(1.0, (st - 2.6) / 0.4))
                ka.draw_text(c, "Bir BONK, bin yaratık.", (cx, cy + 215), 30, (255, 236, 182), bold=True,
                             center=True, alpha=a)

    def s_menu(self, st, first):
        app = self.app
        if first:
            app.state = ka.STATE_MENU
            if app.xmas:
                app.xmas.santa_t = 0.6
                app.xmas.santa_dir = 1
        keys = [(0.0, (1180, 640)), (1.2, (1160, 520)), (2.4, (1160, 520)), (3.3, (340, 486)),
                (4.0, (640, 340)), (5.5, (640, 340))]
        m = path_pos(keys, st)
        clicked = False
        if st >= 4.6 and not getattr(self, "_menu_clicked", False):
            self._menu_clicked = True
            self.ov.click(m, self.t)
            REC.play("click", 0.6, 0.0)
        # tıklamayı menüye VERMİYORUZ: koşuyu biz başlatacağız
        app.update_menu(DT, m, clicked)
        ka.draw_cursor(self.canvas(), m, "ui", app.t)
        self.ov.caption(self.canvas(), "YILBAŞI GÜNCELLEMESİ", "Noel Baba arenaya uğradı!", st - 0.6, 3.6,
                        y=590, col=(255, 120, 120))

    def s_fight(self, st, first):
        app = self.app
        if first:
            self.set_music("battle")
            app.start_run()
            ka.audio = REC
            run = app.run
            run.waves.wave = 4
            run.player.books = {"r_dmg": 2, "r_aspd": 2}
            self.pilot = Pilot(run, crowd=32)
            for _ in range(60):
                self.pilot.step(1 / 60)
        self.pilot.step(DT)
        self.play_frame()
        self.ov.caption(self.canvas(), "DALGA DALGA YARATIK!", "Her dalga daha kalabalık, daha hızlı.", st - 0.4, 5.6)
        self.ov.caption(self.canvas(), "ATEŞ ET • DASH AT • BONK'LA!", "Kalabalığın ortasına dal, hepsini savur.",
                        st - 6.6, 6.0, col=(140, 230, 170))

    def s_levelup(self, st, first):
        app, run = self.app, self.app.run
        if first:
            run.pending_levelups = 1
            run.start_levelup_choice()
            app.state = ka.STATE_LEVELUP
            REC.play("levelup", 1.0, 0.0)
        if app.state == ka.STATE_LEVELUP:
            cards = [r.center for (r, _c, _i) in app.levelup_ui.cards] or [(640, 360)]
            mid = cards[min(1, len(cards) - 1)]
            keys = [(0.0, (640, 640)), (0.9, cards[0]), (1.8, cards[-1]), (2.7, mid), (3.6, mid)]
            m = path_pos(keys, st)
            clicked = st >= 3.4 and not getattr(self, "_lv_clicked", False)
            if clicked:
                self._lv_clicked = True
                self.ov.click(m, self.t)
            app.t += 0  # (app.t ana döngüde ilerliyor)
            app.update_levelup(DT, m, clicked)
            ka.draw_cursor(self.canvas(), m, "ui", app.t)
        else:
            self.pilot.step(DT)
            self.play_frame()
        self.ov.caption(self.canvas(), "SEVİYE ATLADIN!", "Her seviyede gücünü sen seç: silah ya da kitap.",
                        st - 0.3, 5.0, y=606, col=(232, 186, 90))

    def s_market(self, st, first):
        app, run = self.app, self.app.run
        if first:
            run.gold_wallet = max(run.gold_wallet, 4200)
            run.open_shop()
            app.state = ka.STATE_RUN_SHOP
        keys = [(0.0, (640, 600)), (0.8, (183, 250)), (2.2, (183, 250)), (2.8, (327, 116)),
                (3.4, (327, 116)), (4.1, (412, 250)), (5.0, (412, 250)), (5.6, (952, 116)),
                (6.3, (952, 116)), (6.9, (640, 688)), (8.0, (640, 688))]
        m = path_pos(keys, st)
        clicked = False
        for at in (1.2, 1.8, 3.1, 4.5, 6.0, 7.2):
            if self._t_prev_local < at <= st:
                clicked = True
                self.ov.click(m, self.t)
        if app.state == ka.STATE_RUN_SHOP:
            app.update_run_shop(DT, m, clicked)
            ka.draw_cursor(self.canvas(), m, "ui", app.t)
        else:
            app.state = ka.STATE_PLAY
            self.pilot.step(DT)
            self.play_frame()
        self.ov.caption(self.canvas(), "DALGA ARASI MARKET", "Altınını güce çevir — çekirdek, silah, efsane eşyalar.",
                        st - 0.5, 6.4, y=606, x0=0)

    def s_boss(self, st, first):
        app, run = self.app, self.app.run
        if first:
            app.state = ka.STATE_PLAY
            p = run.player
            p.weapons = {"axe": 5, "pentagram": 5, "whip": 4, "tornado": 4}
            p.level = max(p.level, 18)
            run.waves.wave = 10
            run.waves.boss_pending = True
            self.pilot.crowd = 16
            self._boss_dead_at = None
        if st > 8.2:
            for b in list(run.bosses):
                if b.alive:
                    b.take_damage(b.hp + 50, True, run.fx)
        if not run.bosses and st > 8.2 and self._boss_dead_at is None:
            self._boss_dead_at = st
        # devrilen patronun sandığına yürü
        self.pilot.target = (run.chests[0].x, run.chests[0].y) if run.chests else None
        self.pilot.step(DT)
        self.play_frame()
        self.ov.caption(self.canvas(), "PATRONLARI DEVİR!", "Her 5 dalgada bir dev gelir. Devir, sandığını kap.",
                        st - 0.8, 5.5, col=(255, 110, 90))
        self.ov.caption(self.canvas(), "10 EFSANE SİLAH", "Balta, Pentagram, Kırbaç, Hortum... hepsi aynı anda!",
                        st - 6.6, 5.2, col=(238, 150, 100))

    def s_portal(self, st, first):
        app, run = self.app, self.app.run
        if first:
            self.pilot.target = None
            run.enemies[:] = run.enemies[:6]
            self.pilot.crowd = 0
            run.open_hell_portal()
        hp = run.hell_portal
        if hp is not None and st > 1.4:
            self.pilot.target = (hp.x, hp.y)
            self.pilot.use = st > 3.6
        self.pilot.step(DT)
        if run.biome == "hell":
            self.pilot.use = False
            self.pilot.target = None
        self.play_frame()
        self.ov.caption(self.canvas(), "CEHENNEM KAPISI", "25. dalgada açılır. Cesaretin varsa gir...",
                        st - 0.6, 5.0, col=(200, 110, 255))

    def s_hell(self, st, first):
        app, run = self.app, self.app.run
        if first:
            if run.biome != "hell":
                run.enter_hell()
            self.pilot.use = False
            self.pilot.target = None
            self.pilot.crowd = 34
            self.pilot.cx, self.pilot.cy = run.player.x, run.player.y
        if 6.0 <= st and not getattr(self, "_hboss", False):
            self._hboss = True
            run.waves.wave = 5
            run.waves.boss_pending = True
            self.pilot.crowd = 18
        self.pilot.step(DT)
        self.play_frame()
        self.ov.caption(self.canvas(), "CEHENNEM", "İkinci harita: lav, alev ve çok daha güçlü yaratıklar.",
                        st - 0.5, 5.2, col=(255, 120, 60))
        self.ov.caption(self.canvas(), "CEHENNEM PATRONLARI", "Ejderha, Savaş Lordu, Kolos... sıra sende.",
                        st - 6.6, 5.6, col=(255, 80, 80))

    def s_collection(self, st, first):
        app = self.app
        part = min(3, int(st / 2.0))
        lst = st - part * 2.0
        if first:
            self.set_music("menu")
        wheel = -0.9 if lst > 0.5 else 0.0
        m = (640 + math.sin(st * 1.3) * 300, 330 + math.cos(st * 1.1) * 120)
        if part == 0:
            if lst < DT * 1.5:
                app.state, app.weapon_scroll = ka.STATE_WEAPON_CODEX, 0.0
            app.update_weapon_codex(DT, m, False, wheel)
            cap = ("SİLAHLIK", "10 silah — her biri kendi göreviyle açılır.", (238, 150, 100))
        elif part == 1:
            if lst < DT * 1.5:
                app.state, app.book_scroll = ka.STATE_BOOK_MARKET, 0.0
            app.update_book_market(DT, m, False, wheel)
            cap = ("KİTAPLIK", "27 güç kitabı, nadir kitaplar, gizli görevler.", (196, 150, 255))
        elif part == 2:
            if lst < DT * 1.5:
                app.state, app.skin_scroll = ka.STATE_SKIN_MARKET, 0.0
            app.update_skin_market(DT, m, False, wheel)
            cap = ("24 SKİN", "Her skinin kendi silahı ve özel yeteneği var.", (255, 205, 110))
        else:
            if lst < DT * 1.5:
                app.state, app.ach_scroll = ka.STATE_ACHIEVEMENTS, 0.0
            app.update_achievements(DT, m, False, wheel)
            cap = ("BAŞARIMLAR", "Madalyonları topla, elmas kazan.", (232, 186, 90))
        ka.draw_cursor(self.canvas(), m, "ui", app.t)
        self.ov.wipe(self.canvas(), lst, 0.22) if part > 0 else None
        self.ov.caption(self.canvas(), cap[0], cap[1], lst - 0.1, 1.9, y=596, col=cap[2])

    def s_store(self, st, first):
        app = self.app
        if first:
            app.state = ka.STATE_GEM_STORE
            app.store_tab = "free"
        keys = [(0.0, (640, 600)), (1.0, (640, 388)), (3.0, (640, 388)), (3.6, (288, 388)), (4.0, (288, 388))]
        m = path_pos(keys, st)
        clicked = self._t_prev_local < 1.4 <= st
        if clicked:
            self.ov.click(m, self.t)
        app.update_gem_store(DT, m, clicked)
        ka.draw_cursor(self.canvas(), m, "ui", app.t)
        self.ov.caption(self.canvas(), "HER GÜN HEDİYE", "Günlük hediye, ücretsiz elmas, başarım ödülleri.",
                        st - 0.3, 3.7, y=596, col=(140, 230, 170))

    def s_outro(self, st, first):
        c = self.canvas()
        if first:
            self.set_music("menu")
        c.blit(self._intro_bg, (0, 0))
        cx, cy = W / 2, 250
        lay = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(22):
            a = st * 0.22 + i * math.tau / 22
            pygame.draw.polygon(lay, (236, 186, 92, 34), [(cx, cy), (cx + math.cos(a - .05) * 1000, cy + math.sin(a - .05) * 1000),
                                                         (cx + math.cos(a + .05) * 1000, cy + math.sin(a + .05) * 1000)])
        c.blit(lay, (0, 0))
        ka.add_glow(c, cx, cy, 480, (210, 150, 60), 0.32)
        logo = ka.brand_scaled("logo", w=820)
        k = ease(st / 0.6)
        img = pygame.transform.smoothscale(logo, (int(logo.get_width() * (0.85 + 0.15 * k)),
                                                  int(logo.get_height() * (0.85 + 0.15 * k))))
        c.blit(img, (cx - img.get_width() / 2, cy - img.get_height() / 2))
        if st > 0.7:
            q = 0.5 + 0.5 * math.sin(st * 5)
            b = pygame.Rect(0, 0, 440, 88)
            b.center = (int(cx), 500)
            ka.add_glow(c, b.centerx, b.centery, 260, ka.GREEN, 0.18 + 0.12 * q)
            c.blit(ka._button_body(b.w, b.h, (60, 150, 92), q, 22), b.topleft)
            pygame.draw.rect(c, (190, 255, 210), b, width=3, border_radius=22)
            ka.draw_text(c, "ŞİMDİ OYNA!", b.center, int(40 + 3 * q), ka.WHITE, bold=True, center=True)
        if st > 1.2:
            a = int(255 * min(1.0, (st - 1.2) / 0.5))
            ka.draw_text(c, "Arkadaşlarınla yarış — dünya sıralamasında zirveye çık!", (cx, 588), 24,
                         (236, 222, 196), bold=True, center=True, alpha=a)
            ka.draw_text(c, "Mutlu yıllar!  •  5 dil  •  Google ile giriş  •  Dünya sıralaması", (cx, 628), 18,
                         (190, 176, 210), center=True, alpha=a)
        for i in range(60):
            x = (i * 131.3 + math.sin(st + i) * 20) % W
            y = (st * (40 + i % 5 * 12) + i * 57) % H
            ka.blit_disc(c, x, y, 1.5 + i % 3, (255, 255, 255), 190)
        # sona doğru karar
        if st > 5.0:
            f = pygame.Surface((W, H))
            f.set_alpha(int(255 * min(1.0, (st - 5.0) / 0.5)))
            c.blit(f, (0, 0))

    SCENES = (("intro", 5.0), ("menu", 5.5), ("fight", 13.0), ("levelup", 5.5), ("market", 8.0),
              ("boss", 12.0), ("portal", 6.0), ("hell", 13.0), ("collection", 8.0), ("store", 4.0),
              ("outro", 5.6))

    def frames(self):
        """Her kare için (zaman, tuval) üretir."""
        for name, dur in self.SCENES:
            n = int(round(dur * FPS))
            fn = getattr(self, "s_" + name)
            self._t_prev_local = -1.0
            for i in range(n):
                st = i * DT
                REC.now = self.t
                self.app.t += DT
                fn(st, i == 0)
                c = self.canvas()
                OV.draw_clicks(c, self.t)
                if name in ("fight", "boss", "portal", "hell"):
                    OV.corner_logo(c)
                if name != "intro":
                    OV.wipe(c, st)
                self._t_prev_local = st
                yield self.t, c
                self.t += DT

    @property
    def length(self):
        return sum(d for _n, d in self.SCENES)


# =====================================================================
# SES MİKSİ
# =====================================================================
def build_audio(director, path):
    sr = int(getattr(ka, "_SR", 22050)) or 22050
    total = int((director.length + 0.5) * sr)
    out = np.zeros(total, dtype=np.float32)
    # müzik: sahneye göre menü / savaş, yumuşak geçişli
    loops = {k: np.asarray(ka._gen_music(k), dtype=np.float32) for k in ("menu", "battle")}
    marks = director.music + [(director.length + 1, None)]
    fade = int(0.6 * sr)
    for (t0, name), (t1, _n) in zip(marks, marks[1:]):
        a, b = int(t0 * sr), min(total, int(t1 * sr) + fade)
        if b <= a:
            continue
        loop = loops[name]
        seg = np.resize(loop, b - a).copy()
        env = np.ones(b - a, dtype=np.float32)
        k = min(fade, (b - a) // 2)
        env[:k] = np.linspace(0, 1, k)
        env[-k:] = np.linspace(1, 0, k)
        out[a:b] += seg * env * 0.42
    # sonda müzik söner
    end = int((director.length - 0.8) * sr)
    out[end:] *= np.linspace(1, 0, total - end)
    # efektler
    cache = {}
    for (t, name, vol) in REC.events:
        if name not in ka.SFX_BUILDERS:
            continue
        if name not in cache:
            try:
                cache[name] = np.asarray(ka.SFX_BUILDERS[name](), dtype=np.float32)
            except Exception:
                cache[name] = np.zeros(1, dtype=np.float32)
        s = cache[name]
        a = int(t * sr)
        b = min(total, a + len(s))
        if b > a:
            out[a:b] += s[:b - a] * float(vol) * 0.55
    out = np.tanh(out * 1.15) / np.tanh(1.15)
    pcm = (np.clip(out, -1, 1) * 30000).astype("<i2")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def to_bytes(surf):
    f = getattr(pygame.image, "tobytes", None) or pygame.image.tostring
    return f(surf, "RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "arena_bonk_trailer.mp4"))
    ap.add_argument("--preview", default="")
    ap.add_argument("--crf", default="19")
    args = ap.parse_args()
    d = Director()
    if args.preview:
        want = sorted(float(x) for x in args.preview.split(","))
        outdir = os.path.dirname(os.path.abspath(args.out))
        for t, c in d.frames():
            while want and t >= want[0]:
                p = os.path.join(outdir, "trailer_%05.1f.png" % want.pop(0))
                pygame.image.save(c, p)
                print("kaydedildi:", p)
            if not want:
                break
        return
    silent = args.out + ".video.mp4"
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-preset", "slow", "-crf", args.crf,
                             "-pix_fmt", "yuv420p", "-movflags", "+faststart", silent],
                            stdin=subprocess.PIPE)
    n = 0
    for _t, c in d.frames():
        proc.stdin.write(to_bytes(c))
        n += 1
        if n % 300 == 0:
            print("%d kare (%.0f sn)" % (n, n / FPS), flush=True)
    proc.stdin.close()
    proc.wait()
    wav = args.out + ".wav"
    build_audio(d, wav)
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
                           "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                           "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                           "-shortest", "-movflags", "+faststart", args.out])
    os.remove(silent)
    os.remove(wav)
    print("Bitti:", args.out, "(%d kare, %.1f sn)" % (n, n / FPS))


if __name__ == "__main__":
    main()
