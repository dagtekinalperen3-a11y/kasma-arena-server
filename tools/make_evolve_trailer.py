#!/usr/bin/env python3
"""
EVOLVE ARENA — 90 SANİYELİK TANITIM FRAGMANI (1920x1080, 30 fps, MP4)
=====================================================================

Her oyun karesi oyunun GERÇEK motorudur: kasma_arena13.py içe aktarılır,
oyunun kendi "gölge oyun" altyapısı (GameTour / App(shadow_of=...)) ekransız
çalıştırılır ve savaşları insan gibi nişan alan otomatik pilot oynar.
Bunun üstüne fragman katmanı eklenir (oyunda olmayan ama senaryonun
istediği her şey):

  * flaş / glitch / zoom-punch / ekran sarsıntısı / hız çizgileri,
    renk ayrışması (chromatic aberration), hareket bulanıklığı,
  * dünyaya göre renk paleti (buzul mavi, orman yeşil, çöl turuncu,
    cehennem kızıl) + kar / yaprak / kum / kor parçacıkları,
  * 1080p'de keskin, büyük trailer yazıları (Inter Black Italic),
  * EVRİM sahnesi, dünya sıralaması tırmanışı, highlight reel, logo,
  * tools/trailer_audio.py ile sentezlenen müzik + SFX (telifsiz),
    120 BPM ızgarasına oturtulmuş kesimlerle senkron.

Gerçek oyuncu kaydına dokunmaz (ARENA_SAVE_DIR geçici klasöre yönlenir),
ağa bağlanmaz, pencere açmaz.

Kullanım:
    python3 tools/make_evolve_trailer.py                       # tam film
    python3 tools/make_evolve_trailer.py -o fragman.mp4
    python3 tools/make_evolve_trailer.py --stills 4.6,21,46    # yalnız PNG kareler
    python3 tools/make_evolve_trailer.py --from 52 --to 65 -o dunyalar.mp4

Gerekenler: pygame, numpy, scipy ve PATH'te ffmpeg.
"""
import argparse
import math
import os
import random
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
_TMP = tempfile.mkdtemp(prefix="evolve_trailer_")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["ARENA_SAVE_DIR"] = os.path.join(_TMP, "save")   # gerçek kayda dokunma
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import numpy as np          # noqa: E402
import pygame               # noqa: E402

import kasma_arena13 as K   # noqa: E402
import trailer_audio as A   # noqa: E402

W, H = 1920, 1080
VW, VH = K.VIRTUAL_W, K.VIRTUAL_H
S = W / VW                   # kanvas -> 1080p ölçeği (1.5)
FPS = 30
LENGTH = 90.0
GOLD = (255, 204, 92)
WHITE = (255, 255, 255)
RED = (255, 60, 50)

# (başlangıç, bitiş, sahne) — kesimler 120 BPM vuruş ızgarasında (0,5 sn)
SCENES = (
    (0.0, 3.5, "dark"),       # KANCA: kapkaranlık + "CEHENNEM KAPISI AÇILIYOR..."
    (3.5, 8.0, "hook"),       # flaş — oyuncu yaratık dalgasının ortasında
    (8.0, 11.0, "dash"),      # MEKANİK: koş + DASH
    (11.0, 14.5, "bonk"),     # BONK + sarsıntı
    (14.5, 17.0, "market"),   # market yanıp sönerek açılır
    (17.0, 20.0, "gold"),     # altın yağmuru + KOŞ. VUR. HAYATTA KAL.
    (20.0, 36.5, "weapons"),  # 11 silah × 1,5 sn
    (36.5, 38.0, "combo"),    # SONSUZ KOMBİNASYON
    (38.0, 42.5, "books"),    # kitaplar parlıyor
    (42.5, 45.0, "charge"),   # silah 10, kitap 3 — yavaş çekim yükseliş
    (45.0, 47.0, "evolve"),   # BEYAZ PATLAMA — EVRİM
    (47.0, 52.0, "power"),    # evrimleşmiş güçle savaş
    (52.0, 56.5, "frost"),    # Buzul Vadisi
    (56.5, 61.0, "jungle"),   # Zümrüt Orman
    (61.0, 65.0, "desert"),   # Kızıl Çöl
    (65.0, 67.5, "gate"),     # cehennem kapısı açılır — gerilim nefesi
    (67.5, 71.5, "hellord"),  # CEHENNEM LORDU
    (71.5, 75.0, "dragon"),   # KOR EJDERHA
    (75.0, 78.5, "crit"),     # KRİTİK! + şans simgeleri
    (78.5, 82.5, "ranking"),  # dünya sıralaması tırmanışı
    (82.5, 84.0, "badges"),   # başarımlar
    (84.0, 86.5, "reel"),     # 0,2 sn'lik highlight reel
    (86.5, 90.0, "logo"),     # EVOLVE ARENA + ŞİMDİ İNDİR
)
# highlight reel için yakalanacak anlar
SNAP_TIMES = (4.7, 9.6, 12.6, 21.2, 27.4, 33.8, 45.6, 49.6, 54.2, 58.8, 63.0, 69.2, 73.2,
              76.6, 81.6)

# market eşyaları (senaryodaki "silahlar") — (anahtar, ekstra market, başlık, ek ayar)
ARMORY = (
    ("fire", {"fire": 5, "haste": 5, "multishot": 1}, None, {}),
    ("ice", {"ice": 5, "haste": 5, "multishot": 1}, None, {}),
    ("multishot", {"multishot": 5, "haste": 3}, None, {}),
    ("pierce", {"pierce": 5, "multishot": 2, "haste": 3}, None, {}),
    ("shield", {"shield": 8}, None, {"hurt": True, "rmin": 50, "rmax": 160}),
    ("explosive", {"explosive": 5, "haste": 5, "multishot": 2}, None, {}),
    ("chain", {"chain": 4, "storm": 5, "haste": 3}, "ZİNCİR ŞOK + FIRTINA", {"bonk": 0.35}),
    ("vampiric", {"vampiric": 5, "haste": 4, "multishot": 2}, None, {"lowhp": True}),
    ("overcharge", {"overcharge": 4}, None, {"bonk": 0.3, "rmin": 70, "rmax": 220}),
    ("execute_edge", {"execute_edge": 3, "multishot": 2, "haste": 3}, None, {}),
    ("titan_shield", {"titan_shield": 4, "shield": 3, "multishot": 1}, None,
     {"hurt": True, "rmin": 60, "rmax": 200}),
)
ITEM_DUR = 1.5

WORLDS = {
    "frost": dict(name="BUZUL VADİSİ", col=(150, 210, 255), bosses=("warlord", "witch"),
                  mobs="YETİLER · KURTLAR · BUZ GOLEMLERİ",
                  grade=((196, 222, 255), (12, 24, 44))),
    "jungle": dict(name="ZÜMRÜT ORMAN", col=(120, 235, 130), bosses=("witch", "colossus"),
                   mobs="YILANLAR · GORİLLER · PANTERLER",
                   grade=((200, 238, 190), (2, 20, 8))),
    "desert": dict(name="KIZIL ÇÖL", col=(255, 176, 80), bosses=("warlord", "colossus"),
                   mobs="AKREPLER · MUMYALAR · ÇAKALLAR",
                   grade=((255, 222, 176), (34, 14, 0))),
}


# =====================================================================
# yardımcılar
# =====================================================================
def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def fmt_int(n):
    return f"{int(n):,}".replace(",", ".")


def _find_font(names):
    dirs = ["/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/inter",
            "/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
            "C:/Windows/Fonts", "/Library/Fonts", "/System/Library/Fonts"]
    for nm in names:
        for d in dirs:
            p = os.path.join(d, nm)
            if os.path.isfile(p):
                return p
    for d in dirs:                       # alt klasörlerde ara
        if not os.path.isdir(d):
            continue
        for r, _ds, fs in os.walk(d):
            for nm in names:
                if nm in fs:
                    return os.path.join(r, nm)
    return None


class Type:
    """1080p trailer yazıları: kontur, gölge, parıltı, altın gradyan."""

    def __init__(self):
        self.paths = {
            "black": _find_font(["Inter-BlackItalic.otf", "InterDisplay-BlackItalic.otf",
                                 "ariblk.ttf", "Arial Black.ttf", "impact.ttf",
                                 "DejaVuSans-BoldOblique.ttf"]),
            "heavy": _find_font(["InterDisplay-Black.otf", "Inter-Black.otf", "ariblk.ttf",
                                 "DejaVuSans-Bold.ttf"]),
            "bold": _find_font(["Inter-ExtraBold.otf", "Inter-Bold.otf", "arialbd.ttf",
                                "DejaVuSans-Bold.ttf"]),
        }
        self.fonts = {}
        self.cache = {}

    def font(self, style, size):
        key = (style, size)
        f = self.fonts.get(key)
        if f is None:
            p = self.paths.get(style)
            try:
                f = pygame.font.Font(p, size) if p else pygame.font.Font(None, int(size * 1.3))
            except Exception:
                f = pygame.font.Font(None, int(size * 1.3))
            self.fonts[key] = f
        return f

    def render(self, text, size, color=WHITE, style="black", stroke=0, scol=(10, 6, 14),
               grad=None, glow=None, shadow=True):
        key = (text, size, color, style, stroke, scol, grad, glow, shadow)
        img = self.cache.get(key)
        if img is not None:
            return img
        if len(self.cache) > 600:
            self.cache.clear()
        f = self.font(style, size)
        base = f.render(text, True, WHITE).convert_alpha()
        bw, bh = base.get_size()
        if grad:
            top, bot = grad
            col = pygame.Surface((bw, bh), pygame.SRCALPHA)
            for y in range(bh):
                k = y / max(1, bh - 1)
                c = tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3))
                pygame.draw.line(col, c + (255,), (0, y), (bw, y))
            col.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        else:
            col = base.copy()
            col.fill(tuple(color) + (255,), special_flags=pygame.BLEND_RGBA_MULT)
        gr = int(size * 0.3) if glow else 0
        pad = stroke + gr + (stroke + 4 if shadow else 0)
        out = pygame.Surface((bw + pad * 2, bh + pad * 2), pygame.SRCALPHA)
        if glow:
            gimg = base.copy()
            gimg.fill(tuple(glow) + (255,), special_flags=pygame.BLEND_RGBA_MULT)
            sw, sh = max(1, (bw + gr * 2) // 6), max(1, (bh + gr * 2) // 6)
            tmp = pygame.Surface((bw + gr * 2, bh + gr * 2), pygame.SRCALPHA)
            tmp.blit(gimg, (gr, gr))
            small = pygame.transform.smoothscale(tmp, (sw, sh))
            small = pygame.transform.smoothscale(small, (max(1, sw // 2), max(1, sh // 2)))
            big = pygame.transform.smoothscale(small, (bw + gr * 2, bh + gr * 2))
            big.set_alpha(150)
            out.blit(big, (pad - gr, pad - gr))
        if stroke or shadow:
            s = base.copy()
            s.fill(tuple(scol) + (255,), special_flags=pygame.BLEND_RGBA_MULT)
            if shadow:
                d = stroke + 4
                for a in range(0, 360, 45):
                    out.blit(s, (pad + d * 0.5 + math.cos(math.radians(a)) * stroke,
                                 pad + d + math.sin(math.radians(a)) * stroke))
            for a in range(0, 360, 22):
                out.blit(s, (pad + math.cos(math.radians(a)) * stroke,
                             pad + math.sin(math.radians(a)) * stroke))
        out.blit(col, (pad, pad))
        self.cache[key] = out
        return out


# =====================================================================
# otomatik pilot (oyunun kendi pilotu + fragman komutları)
# =====================================================================
class Pilot(K._TourPilot):
    KINDS = ("red", "red", "blue", "yellow", "tank", "sprinter", "brute")

    def __init__(self, run, crowd=0):
        super().__init__(run, crowd=crowd)
        self.force_dash = False

    def spawn(self):
        run = self.run
        x, y = run.near_camera_point()
        w = run.waves.wave
        if run.biome == "hell":
            run.enemies.append(K.Enemy(None, x, y, run.wave_hp_mult(w), 1.0, wave=w,
                                       variant=K.hell_pick_kind(w), biome="hell"))
        else:
            run.enemies.append(run._make_enemy(random.choice(self.KINDS), x, y))

    def step(self, dt):
        run = self.run
        orig = run.update

        def upd(dt_, inp):
            if self.force_dash:
                self.force_dash = False
                run.player.dash_cd_timer = 0.0
                inp["dash_pressed"] = True
            return orig(dt_, inp)
        run.update = upd
        try:
            super().step(dt)
        finally:
            try:
                del run.update
            except AttributeError:
                pass


# =====================================================================
# yönetmen
# =====================================================================
class Trailer(K.GameTour):
    def __init__(self, real_app):
        super().__init__(real_app)
        self.T = Type()
        self.events = []            # ses: (t, ad, kazanç)
        self.punches = []           # (t, güç)
        self.shakes = []            # (t, genlik, süre)
        self.flashes = []           # (t, süre, renk, güç)
        self.glitches = []          # (t, süre)
        self.speeds = []            # (t, süre, güç)
        self.snaps = []
        self.cur_scene = None
        self.wipe_from = None
        self.last_pre = None
        self.overlays = []
        self.item_i = -1
        self.rank_y = {}
        self.vignette = self._make_vignette()
        self.layer = pygame.Surface((W, H), pygame.SRCALPHA)
        self.skin = next((s for s in K.SKINS if s.get("id") == self.sh.selected_skin), K.SKINS[0])
        self.rng = random.Random(11)
        for theme in ("frost", "jungle", "desert"):          # zeminleri önceden çiz
            try:
                K.floor_surface(theme)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # efekt kayıtları
    def sfx(self, name, gain=0.8, at=None):
        self.events.append((self.t if at is None else at, name, gain))

    def punch(self, s=0.12):
        self.punches.append((self.t, s))

    def shake(self, amp=14, dur=0.35):
        self.shakes.append((self.t, amp, dur))

    def flash(self, dur=0.25, col=(255, 250, 240), power=1.0):
        self.flashes.append((self.t, dur, col, power))

    def glitch(self, dur=0.2):
        self.glitches.append((self.t, dur))

    def speed(self, dur=0.4, power=1.0):
        self.speeds.append((self.t, dur, power))

    def ov(self, fn):
        self.overlays.append(fn)

    # ------------------------------------------------------------------
    def make_run(self, wave=8, weapons=None, level=20, crowd=30, books=None, theme="stone",
                 hell=False, shop=None, ring=0, rmin=140, rmax=380, prewarm=0.0, hurt=False):
        sh = self.sh
        sh.start_run()
        run = sh.run
        run.set_map_theme(theme)
        run.merchant = None
        run.quests = []
        run.ach = None
        run.cursed_next_wave = 999          # filmde lanetli mağara bildirimi çıkmasın
        p = run.player
        p.no_stats = True
        if not hurt:
            p.take_damage = lambda *a, **k: 0
        p.weapons = dict(weapons or {})
        for k in p.weapons:
            p.weapon_timers[k] = 0.0
        for bk, (lv, tier) in (books or {}).items():
            for _ in range(lv):
                p.take_book(bk, tier)
        p.level = level
        for key, lv in (shop or {}).items():
            for _ in range(lv):
                p.shop_levels[key] = p.shop_levels.get(key, 0) + 1
                K.apply_shop_item(p, key)
        if hell:
            run.waves.wave = K.HELL_PORTAL_WAVE
            run.enter_hell()
        if wave > 1:
            run.waves._begin_wave(wave, run.score)
        run.waves.announce_timer = 0.0
        self.pilot = Pilot(run, crowd=crowd)
        sh.state = K.STATE_PLAY
        if ring:
            self.ring(run, ring, rmin, rmax)
        for _ in range(int(prewarm * 60)):
            self.pilot.step(1 / 60.0)
        run.fx.texts.clear()
        return run

    def ring(self, run, n, rmin=140, rmax=380):
        p = run.player
        w = run.waves.wave
        for _ in range(n):
            a = random.uniform(0, math.tau)
            d = random.uniform(rmin, rmax)
            x = K.clamp(p.x + math.cos(a) * d, K.ARENA_RECT.left + 40, K.ARENA_RECT.right - 40)
            y = K.clamp(p.y + math.sin(a) * d * 0.75, K.ARENA_RECT.top + 40, K.ARENA_RECT.bottom - 40)
            if run.biome == "hell":
                run.enemies.append(K.Enemy(None, x, y, run.wave_hp_mult(w), 1.0, wave=w,
                                           variant=K.hell_pick_kind(w), biome="hell"))
            else:
                run.enemies.append(run._make_enemy(random.choice(Pilot.KINDS), x, y))

    def add_boss(self, run, kind, dx, dy, hellish=False, theme=None):
        cam = run.cam_rect()
        bx = K.clamp(cam.centerx + dx, K.ARENA_RECT.left + 90, K.ARENA_RECT.right - 90)
        by = K.clamp(cam.centery + dy, K.ARENA_RECT.top + 90, K.ARENA_RECT.bottom - 90)
        b = K.Boss(kind, bx, by, 1.0, 1.0, run.waves.wave, hellish=hellish,
                   theme=None if (hellish or theme in (None, "stone")) else theme)
        run.bosses.append(b)
        K.scale_bosses_to_player(run.bosses, run.player)
        run.waves.boss_active = True
        return b

    def bonk(self, power=1.0):
        run = self.sh.run
        run.player.bonk_cd = 0.0
        try:
            run.do_bonk()
        except Exception:
            pass
        run.fx.shake(12, 0.35)
        self.shake(16 * power, 0.4)
        self.punch(0.10 * power)
        self.glitch(0.12)
        self.sfx("bonk", 0.9)

    def play(self, dt):
        self._play(dt)

    def player_screen(self):
        run = self.sh.run
        if run is None:
            return VW / 2, VH / 2
        return run.world_to_screen(run.player.x, run.player.y)

    def bg(self, c, top=(54, 30, 80), bot=(10, 6, 20), key="g"):
        cache = getattr(self, "_bgs", None)
        if cache is None:
            cache = self._bgs = {}
        img = cache.get((key, top, bot))
        if img is None:
            img = pygame.Surface((VW, VH)).convert()
            for y in range(VH):
                pygame.draw.line(img, K.mix_col(top, bot, y / VH), (0, y), (VW, y))
            cache[(key, top, bot)] = img
        c.blit(img, (0, 0))

    def rays(self, c, cx, cy, st, col=(236, 186, 92), alpha=30, n=22):
        lay = pygame.Surface((VW, VH), pygame.SRCALPHA)
        for i in range(n):
            a = st * 0.22 + i * math.tau / n
            pygame.draw.polygon(lay, col + (alpha,),
                                [(cx, cy), (cx + math.cos(a - .05) * 1100, cy + math.sin(a - .05) * 1100),
                                 (cx + math.cos(a + .05) * 1100, cy + math.sin(a + .05) * 1100)])
        c.blit(lay, (0, 0))

    # ------------------------------------------------------------------
    # 1080p yazı
    def title(self, out, text, cx, cy, size, t0, t1=None, color=WHITE, grad=None, stroke=7,
              scol=(10, 6, 14), glow=None, slam=0.55, chroma=False, flicker=False, style="black",
              align="center"):
        lt = self.t - t0
        if lt < 0 or (t1 is not None and self.t >= t1):
            return
        img = self.T.render(text, size, color, style, stroke, scol, grad, glow)
        k = ease_out(lt / 0.16)
        sc = 1.0 + slam * (1 - k)
        a = min(1.0, lt / 0.07)
        if t1 is not None:
            a = min(a, max(0.0, (t1 - self.t) / 0.12))
        if flicker:
            a *= 0.35 + 0.65 * (self.rng.random() > 0.25)
        if sc != 1.0:
            img = pygame.transform.smoothscale(img, (int(img.get_width() * sc),
                                                     int(img.get_height() * sc)))
        iw, ih = img.get_size()
        x = cx - iw / 2 if align == "center" else (cx if align == "left" else cx - iw)
        y = cy - ih / 2
        if chroma or lt < 0.12:
            d = 10 if chroma else int(14 * (1 - lt / 0.12))
            if d > 0:
                for tint, dx in (((255, 40, 60), -d), ((40, 220, 255), d)):
                    g = img.copy()
                    g.fill(tint + (255,), special_flags=pygame.BLEND_RGBA_MULT)
                    g.set_alpha(int(150 * a))
                    out.blit(g, (x + dx, y), special_flags=pygame.BLEND_ADD)
        if a < 1.0:
            img = img.copy()
            img.set_alpha(int(255 * a))
        out.blit(img, (x, y))

    def keycap(self, out, label, sub, x, y, t0, t1, col=(255, 214, 120)):
        lt = self.t - t0
        if lt < 0 or self.t >= t1:
            return
        k = ease_out(lt / 0.25)
        f = self.T.render(label, 40, WHITE, "heavy", 0, shadow=False)
        w = f.get_width() + 44
        r = pygame.Rect(0, 0, w, 74)
        r.topleft = (int(x), int(y + (1 - k) * 60))
        box = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(box, (14, 10, 24, 220), box.get_rect(), border_radius=14)
        pygame.draw.rect(box, col + (255,), box.get_rect(), width=4, border_radius=14)
        pygame.draw.rect(box, col + (255,), pygame.Rect(0, r.h - 10, r.w, 10),
                         border_bottom_left_radius=14, border_bottom_right_radius=14)
        box.set_alpha(int(255 * k))
        out.blit(box, r.topleft)
        out.blit(f, (r.x + 22, r.y + 9))
        s = self.T.render(sub, 34, col, "black", 4)
        out.blit(s, (r.right + 10, r.y + 37 - s.get_height() / 2))

    # ------------------------------------------------------------------
    # 1080p parçacıklar
    def particles(self, out, kind, n=120, alpha=1.0):
        t = self.t
        rnd = random.Random(99)
        if kind == "snow":
            for i in range(n):
                x0, y0, sp, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(140, 420), rnd.choice((2, 3, 3, 4, 6))
                x = (x0 - t * sp * 0.55 + math.sin(t * 2 + i) * 20) % W
                y = (y0 + t * sp) % H
                pygame.draw.circle(out, (235, 245, 255), (int(x), int(y)), r)
        elif kind == "leaves":
            for i in range(n // 2):
                x0, y0, sp = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(60, 160)
                x = (x0 + t * sp * 0.6 + math.sin(t * 1.4 + i) * 60) % W
                y = (y0 + t * sp) % H
                a = t * 3 + i
                col = rnd.choice(((90, 200, 90), (150, 220, 80), (60, 150, 70)))
                pts = [(x + math.cos(a) * 9, y + math.sin(a) * 4), (x - math.sin(a) * 4, y + math.cos(a) * 9),
                       (x - math.cos(a) * 9, y - math.sin(a) * 4), (x + math.sin(a) * 4, y - math.cos(a) * 9)]
                pygame.draw.polygon(out, col, pts)
            for i in range(n // 2):                      # ateş böcekleri
                x0, y0 = rnd.uniform(0, W), rnd.uniform(0, H)
                x = x0 + math.sin(t * 0.8 + i) * 40
                y = y0 + math.cos(t * 0.6 + i * 2) * 30
                if math.sin(t * 4 + i * 1.7) > 0.2:
                    pygame.draw.circle(out, (230, 255, 150), (int(x), int(y)), 3)
        elif kind == "dust":
            lay = self.layer
            lay.fill((0, 0, 0, 0))
            for i in range(n):
                x0, y0, sp, ln = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(500, 1100), rnd.uniform(40, 160)
                x = (x0 + t * sp) % (W + 200) - 100
                y = y0 + math.sin(t * 2 + i) * 10
                pygame.draw.line(lay, (255, 214, 150, int(90 * alpha)), (x, y), (x + ln, y + 4), 2)
            out.blit(lay, (0, 0))
        elif kind == "embers":
            for i in range(n):
                x0, y0, sp, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(60, 260), rnd.choice((2, 2, 3, 4))
                x = (x0 + math.sin(t * 1.5 + i) * 40) % W
                y = (y0 - t * sp) % H
                col = rnd.choice(((255, 120, 40), (255, 180, 70), (255, 70, 30)))
                if alpha >= 1 or rnd.random() < alpha:
                    pygame.draw.circle(out, col, (int(x), int(y)), r)

    # ------------------------------------------------------------------
    @staticmethod
    def _make_vignette():
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        a = np.clip((d - 0.62) / 0.75, 0, 1) ** 1.6 * 215
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        px = pygame.surfarray.pixels_alpha(surf)
        px[:, :] = a.T.astype(np.uint8)
        del px
        return surf

    # ------------------------------------------------------------------
    def scene_at(self, t):
        for st, en, nm in SCENES:
            if t < en:
                return st, en, nm
        return SCENES[-1]

    def frame(self, t, out):
        """t anındaki kareyi out'a (1920x1080) çizer."""
        dt = 1.0 / FPS
        self.t = t
        self.sh.t += dt
        st0, en, name = self.scene_at(t)
        st = t - st0
        first = name != self.cur_scene
        if first:
            self.wipe_from = self.last_pre
            self.cur_scene = name
            self.prev = -1.0
        # sahne başına varsayılanlar
        self.zoom, self.focus, self.grade = 1.06, "player", None
        self.blur, self.vig = 0.0, 1.0
        self.wipe = None
        self.overlays = []
        canvas_scene = getattr(self, "_s_" + name)(st, dt, first, en - st0)
        self.prev = st
        self.compose(out, canvas_scene is not False)
        self.post(out)
        pre = out.copy()
        for fn in self.overlays:
            fn(out)
        self.after(out)
        # highlight reel ve geçişler için
        for sn in SNAP_TIMES:
            if abs(t - sn) < 0.5 / FPS:
                self.snaps.append(pre)
        self.last_pre = pre

    # ------------------------------------------------------------------
    def compose(self, out, use_canvas):
        if not use_canvas:
            out.fill((0, 0, 0))
            return
        c = self.sh.display.canvas
        t = self.t
        z = self.zoom
        for t0, s in self.punches:
            if t >= t0:
                z += s * math.exp(-(t - t0) * 9.0)
        z = max(1.0, z)
        if self.focus == "player":
            fx, fy = self.player_screen()
        elif self.focus is None:
            fx, fy = VW / 2, VH / 2
        else:
            fx, fy = self.focus
        w, h = VW / z, VH / z
        sx = sy = 0.0
        for t0, amp, dur in self.shakes:
            if t0 <= t < t0 + dur:
                k = 1 - (t - t0) / dur
                sx += self.rng.uniform(-1, 1) * amp * k / S
                sy += self.rng.uniform(-1, 1) * amp * k / S
        x = K.clamp(fx - w / 2 + sx, 0, VW - w)
        y = K.clamp(fy - h / 2 + sy, 0, VH - h)
        sub = c.subsurface(pygame.Rect(int(x), int(y), int(w), int(h)))
        pygame.transform.smoothscale(sub, (W, H), out)

    def post(self, out):
        t = self.t
        if self.blur > 0 and self.last_pre is not None:          # hareket bulanıklığı
            g = self.last_pre.copy()
            g.set_alpha(int(170 * self.blur))
            out.blit(g, (0, 0))
        if self.grade:
            mul, add = self.grade
            out.fill(mul, special_flags=pygame.BLEND_MULT)
            out.fill(add, special_flags=pygame.BLEND_ADD)
        # hız çizgileri
        pw = 0.0
        for t0, dur, power in self.speeds:
            if t0 <= t < t0 + dur:
                pw = max(pw, power * (1 - (t - t0) / dur) ** 0.7)
        if pw > 0.02:
            lay = self.layer
            lay.fill((0, 0, 0, 0))
            cx, cy = W / 2, H / 2
            for i in range(90):
                a = self.rng.uniform(0, math.tau)
                r0 = self.rng.uniform(330, 700)
                r1 = r0 + self.rng.uniform(250, 900)
                wd = self.rng.uniform(0.004, 0.012)
                pygame.draw.polygon(lay, (255, 255, 255, int(150 * pw)),
                                    [(cx + math.cos(a) * r0, cy + math.sin(a) * r0),
                                     (cx + math.cos(a - wd) * r1, cy + math.sin(a - wd) * r1),
                                     (cx + math.cos(a + wd) * r1, cy + math.sin(a + wd) * r1)])
            out.blit(lay, (0, 0))
        if self.vig > 0:
            if self.vig >= 1.0:
                out.blit(self.vignette, (0, 0))
            else:
                v = self.vignette.copy()
                v.set_alpha(int(255 * self.vig))
                out.blit(v, (0, 0))
        # sahne geçişi: eğik wipe (önceki sahne sağdan kayarak açılır)
        if self.wipe and self.wipe_from is not None:
            k, col = self.wipe
            if k < 1.0:
                x0 = int(-200 + (W + 400) * ease_in_out(k))
                if x0 < W:
                    out.blit(self.wipe_from, (max(0, x0), 0),
                             pygame.Rect(max(0, x0), 0, W - max(0, x0), H))
                    pygame.draw.polygon(out, col, [(x0 - 140, 0), (x0 + 60, 0), (x0 + 200, H),
                                                   (x0, H)])
                    pygame.draw.polygon(out, WHITE, [(x0 + 30, 0), (x0 + 60, 0), (x0 + 200, H),
                                                     (x0 + 170, H)])

    def after(self, out):
        """Yazılardan SONRA: glitch, renk ayrışması, flaş."""
        t = self.t
        gl = 0.0
        for t0, dur in self.glitches:
            if t0 <= t < t0 + dur:
                gl = max(gl, 1 - (t - t0) / dur)
        ca = 0
        for t0, s in self.punches:
            if t0 <= t < t0 + 0.2:
                ca = max(ca, int(s * 60 * (1 - (t - t0) / 0.2)))
        if gl > 0:
            ca = max(ca, int(12 * gl))
            for _ in range(int(3 + 6 * gl)):
                y = self.rng.randrange(0, H - 40)
                hh = min(self.rng.randrange(8, 70), H - y)
                dx = self.rng.randrange(-60, 60)
                band = out.subsurface(pygame.Rect(0, y, W, hh)).copy()
                out.blit(band, (dx, y))
        if ca > 0:
            arr = pygame.surfarray.pixels3d(out)
            arr[ca:, :, 0] = arr[:-ca, :, 0].copy()
            arr[:-ca, :, 2] = arr[ca:, :, 2].copy()
            del arr
        for t0, dur, col, power in self.flashes:
            if t0 <= t < t0 + dur:
                k = (1 - (t - t0) / dur) ** 1.5 * power
                fl = pygame.Surface((W, H))
                fl.fill(col)
                fl.set_alpha(int(255 * min(1.0, k)))
                out.blit(fl, (0, 0))

    # ==================================================================
    # SAHNELER — kanvasa (1280x720) oyun çizer; 1080p katmanı self.ov ile
    # ==================================================================
    def _s_dark(self, st, dt, first, dur):
        c = self.sh.display.canvas
        c.fill((0, 0, 0))
        self.vig = 0.0
        if first:
            self.sfx("growl", 0.9, 0.2)
            self.sfx("growl", 0.75, 1.5)
            self.sfx("glitch", 0.5, 0.8)
            self.sfx("growl", 1.0, 2.6)
            self.sfx("glitch", 0.6, 3.15)
            self.sfx("whoosh", 0.6, 3.2)

        def draw(out):
            t = self.t
            # aşağıdan gelen kızıl kapı ışığı
            k = 0.25 + 0.75 * ease_in_out(st / dur)
            pul = 0.7 + 0.3 * math.sin(t * 9) * math.sin(t * 2.3)
            glow = pygame.Surface((W // 8, H // 8), pygame.SRCALPHA)
            for r in range(60, 0, -4):
                a = int(10 * k * pul * (1 - r / 60) * 3)
                pygame.draw.ellipse(glow, (255, 50, 20, a),
                                    pygame.Rect(W // 16 - r * 2, H // 8 - r, r * 4, r * 2))
            out.blit(pygame.transform.smoothscale(glow, (W, H)), (0, 0))
            self.particles(out, "embers", n=int(30 + 70 * k), alpha=k)
            # karanlıkta beliren göz çiftleri
            rnd = random.Random(5)
            for i in range(14):
                t_on = 0.3 + i * 0.2
                ex, ey = rnd.uniform(160, W - 160), rnd.uniform(140, H - 260)
                if t < t_on:
                    continue
                blink = (math.sin((t - t_on) * 3 + i) > -0.85)
                if not blink:
                    continue
                a = min(1.0, (t - t_on) / 0.25)
                sz = rnd.uniform(5, 11)
                for sx in (-1, 1):
                    pygame.draw.ellipse(out, (int(255 * a), int(40 * a), int(20 * a)),
                                        pygame.Rect(ex + sx * sz * 2.2 - sz, ey - sz * 0.45, sz * 2, sz * 0.9))
            if st >= 0.8:
                fl = st > 3.0 or (0.8 < st < 1.3)
                self.title(out, "CEHENNEM KAPISI AÇILIYOR...", W / 2, H / 2 - 20, 104, 0.8, 3.45,
                           grad=((255, 236, 220), (255, 70, 50)), stroke=6, glow=(200, 20, 10),
                           slam=0.08, flicker=fl, chroma=st > 3.0)
        self.ov(draw)
        if self.at(st, 0.8) or self.at(st, 3.15):
            self.glitch(0.25)
        return False

    def _s_hook(self, st, dt, first, dur):
        if first:
            self.make_run(16, {"tesla": 12, "tornado": 10, "beam": 12, "pentagram": 12}, 42, 70,
                          books={"r_dmg": (8, 3), "r_aspd": (6, 2)}, ring=60, rmin=110, rmax=420,
                          prewarm=0.25)
            self.flash(0.45, power=1.0)
            self.punch(0.25)
            self.speed(0.5, 1.0)
            self.pilot.force_dash = True
            self.sfx("impact_big", 0.9)
            self.sfx("whoosh", 0.7)
        if self.at(st, 1.0):
            self.bonk(1.3)
        if self.at(st, 2.5):
            self.bonk(1.0)
        self.play(dt)
        self.zoom = 1.06 + 0.5 * (1 - ease_out(st / 0.5)) + 0.08 * (st / dur)
        self.grade = ((215, 190, 190), (14, 0, 0))

        def draw(out):
            self.title(out, "HAYATTA KALABİLECEK", W / 2, H / 2 - 70, 118, self.t - st + 1.0, None,
                       grad=(WHITE, (255, 200, 170)), stroke=8, glow=(160, 20, 10))
            self.title(out, "MİSİN?", W / 2, H / 2 + 70, 150, self.t - st + 1.5, None,
                       grad=((255, 120, 90), (220, 20, 20)), stroke=8, glow=(200, 20, 10))
        self.ov(draw)
        if self.at(st, 1.5):
            self.punch(0.08)
            self.sfx("impact", 0.5)

    def _s_dash(self, st, dt, first, dur):
        if first:
            self.make_run(6, {}, 8, 46, shop={"haste": 3, "multishot": 1}, ring=34, rmin=120,
                          rmax=360, prewarm=0.4)
            self.sfx("whoosh", 0.5)
        for x in (0.45, 1.45, 2.45):
            if self.at(st, x):
                self.pilot.force_dash = True
                self.speed(0.45, 1.0)
                self.punch(0.07)
                self.sfx("whoosh", 0.8)
        self.play(dt)
        self.zoom = 1.12
        for x in (0.45, 1.45, 2.45):
            if x <= st < x + 0.35:
                self.blur = 0.75
        self.ov(lambda out: (self.keycap(out, "W A S D", "KOŞ", 80, 880, self.t - st + 0.1, self.t + 1),
                             self.keycap(out, "SHIFT", "DASH", 80, 970, self.t - st + 0.45, self.t + 1)))

    def _s_bonk(self, st, dt, first, dur):
        if first:
            self.make_run(9, {"pentagram": 4}, 14, 64, shop={"overcharge": 1, "haste": 2},
                          ring=50, rmin=70, rmax=300, prewarm=0.3)
            self.flash(0.15, power=0.6)
            self.sfx("whoosh", 0.6)
        for x in (0.5, 1.5, 2.5):
            if self.at(st, x):
                self.bonk(1.4)
                self.ring(self.sh.run, 18, 80, 260)
        self.play(dt)
        self.zoom = 1.14
        self.ov(lambda out: self.keycap(out, "SPACE", "BONK!", 80, 970, self.t - st + 0.5,
                                        self.t + 1, col=(255, 150, 90)))

    def _s_market(self, st, dt, first, dur):
        sh = self.sh
        if first:
            run = self.make_run(8, {"tesla": 6, "tornado": 4, "beam": 6, "pentagram": 6}, 16, 12)
            run.gold_wallet = max(run.gold_wallet, 1600)
            run.open_shop()
            sh.state = K.STATE_RUN_SHOP
            self.flash(0.18, col=(255, 220, 140), power=0.9)
            self.glitch(0.3)
            self.sfx("glitch", 0.5)
            self.sfx("shing", 0.6)
        m = self.path([(0.0, (640, 600)), (0.5, (183, 250)), (1.1, (183, 250)), (1.5, (420, 250)),
                       (2.5, (420, 250))], st)
        clicked = False
        for x in (0.6, 1.0, 1.6, 2.0):
            if self.at(st, x):
                clicked = True
                self.clicks.append((m, self.t))
                self.punch(0.04)
                self.sfx("coin", 0.9)
        if sh.state == K.STATE_RUN_SHOP:
            sh.update_run_shop(dt, m, clicked)
            self.cursor(m)
        else:
            self.play(dt)
        self.zoom, self.focus = 1.0, None
        on = st > 0.28 or int(st * 30) % 3 != 1          # açılışta yanıp sönme
        if not on:
            sh.display.canvas.fill((255, 236, 180))
        self.ov(lambda out: self.keycap(out, "B", "MARKET", 80, 970, self.t - st + 0.3,
                                        self.t + 1, col=GOLD))

    def _s_gold(self, st, dt, first, dur):
        if first:
            self.make_run(10, {"tesla": 6, "pentagram": 6, "beam": 6}, 20, 34,
                          shop={"haste": 3, "multishot": 2}, ring=26, prewarm=0.3)
            self.flash(0.12, power=0.6)
            self.sfx("whoosh", 0.6)
        run = self.sh.run
        p = run.player
        if int(st * 30) % 4 == 0:                          # altın yağmuru
            for _ in range(7):
                a = random.uniform(0, math.tau)
                d = random.uniform(160, 420)
                pk = K.Pickup(p.x + math.cos(a) * d, p.y + math.sin(a) * d * 0.7, "coin",
                              random.choice((3, 5, 8)))
                pk.magnet = True
                run.pickups.append(pk)
        if int(st * 30) % 3 == 0:
            self.sfx("coin", 0.35)
        self.play(dt)
        self.zoom = 1.1
        self.grade = ((255, 240, 205), (14, 8, 0))
        words = (("KOŞ.", 0.0, -230, (WHITE, (200, 230, 255))), ("VUR.", 0.5, -40, (WHITE, (255, 190, 150))),
                 ("HAYATTA KAL.", 1.0, 170, ((255, 240, 180), (255, 160, 40))))
        for _w, x, _y, _g in words:
            if self.at(st, x):
                self.punch(0.09)
                self.sfx("impact", 0.55)
                self.glitch(0.1)

        def draw(out):
            dim = pygame.Surface((W, H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, int(110 * min(1.0, st / 0.2))))
            out.blit(dim, (0, 0))
            for wd, x, y, g in words:
                self.title(out, wd, W / 2, H / 2 + y, 190 if wd != "HAYATTA KAL." else 170,
                           self.t - st + x, None, grad=g, stroke=9, glow=(255, 140, 40), slam=0.8)
        self.ov(draw)

    # ------------------------------------------------------------------
    def _s_weapons(self, st, dt, first, dur):
        i = min(len(ARMORY) - 1, int(st / ITEM_DUR))
        lt = st - i * ITEM_DUR
        key, shop, label, extra = ARMORY[i]
        item = K.SHOP_BY_KEY[key]
        legendary = bool(item.get("legendary"))
        if i != self.item_i:
            self.item_i = i
            run = self.make_run(11, {}, 24, 44, shop=shop, ring=36, rmin=extra.get("rmin", 120),
                                rmax=extra.get("rmax", 330), prewarm=0.45, hurt=extra.get("hurt", False))
            if extra.get("lowhp"):
                self.pilot.keep_hp = False
                run.player.hp = run.player.max_hp * 0.3
            if extra.get("hurt"):
                self.pilot.target = (run.player.x, run.player.y)
            self.flash(0.16, col=(255, 236, 190) if legendary else (255, 250, 245), power=0.85)
            self.punch(0.1)
            self.sfx("whoosh", 0.7)
            if legendary:
                self.sfx("shing", 0.7)
            if i == 0:
                self.sfx("impact", 0.7)
        if extra.get("bonk") and self.at(st, i * ITEM_DUR + extra["bonk"]):
            self.bonk(1.3 if key == "overcharge" else 0.9)
        self.play(dt)
        self.zoom = 1.16 - 0.06 * (lt / ITEM_DUR)
        if legendary:
            self.grade = ((255, 238, 200), (22, 14, 0))
        name = label or item["name"].upper()
        col = tuple(item.get("color", GOLD))

        def draw(out):
            k = ease_out(lt / 0.2)
            x0 = int(-760 + 820 * k)
            y0 = 800
            box = pygame.Surface((900, 190), pygame.SRCALPHA)
            box.fill((10, 8, 18, 215))
            pygame.draw.rect(box, (GOLD if legendary else col) + (255,), pygame.Rect(0, 0, 12, 190))
            out.blit(box, (x0, y0))
            cxi, cyi = x0 + 110, y0 + 95
            pygame.draw.circle(out, (24, 18, 36), (cxi, cyi), 70)
            pygame.draw.circle(out, GOLD if legendary else col, (cxi, cyi), 70, 6)
            K.draw_icon(out, cxi, cyi, item.get("icon", "star"), col if not legendary else GOLD, r=42)
            if legendary:
                tag = self.T.render("★ EFSANEVİ ★", 34, GOLD, "black", 4)
                out.blit(tag, (x0 + 200, y0 + 6))
                img = self.T.render(name, 80, GOLD, "black", 6, grad=((255, 250, 210), (255, 170, 40)),
                                    glow=(255, 170, 40))
                out.blit(img, (x0 + 190 - 40, y0 + 30 - 40))
            else:
                img = self.T.render(name, 80, col, "black", 6, grad=(WHITE, col))
                out.blit(img, (x0 + 190, y0 + 22))
            d = self.T.render(item["desc"], 30, (236, 232, 244), "bold", 3)
            out.blit(d, (x0 + 196, y0 + 128))
            # sayaç
            ctr = self.T.render(f"{i + 1:02d}/{len(ARMORY):02d}", 36, (200, 190, 220), "heavy", 3)
            out.blit(ctr, (W - ctr.get_width() - 60, 50))
            if legendary:                     # altın parıltı süpürmesi
                sx = int(-300 + (W + 600) * (lt / ITEM_DUR))
                lay = self.layer
                lay.fill((0, 0, 0, 0))
                pygame.draw.polygon(lay, (255, 220, 120, 46), [(sx, 0), (sx + 140, 0), (sx - 160, H), (sx - 300, H)])
                out.blit(lay, (0, 0))
            if st < 1.4:
                self.title(out, "ONLARCA SİLAH.", W / 2, 230, 150, self.t - st + 0.05, self.t - st + 1.45,
                           grad=(WHITE, (255, 190, 120)), stroke=9, glow=(255, 120, 40))
        self.ov(draw)

    def _s_combo(self, st, dt, first, dur):
        c = self.sh.display.canvas
        self.bg(c, (40, 22, 60), (8, 4, 16))
        self.rays(c, VW / 2, VH / 2, self.t, alpha=26)
        K.add_glow(c, VW / 2, VH / 2, 460, (210, 150, 60), 0.3)
        self.zoom, self.focus = 1.0 + 0.04 * st, None
        if first:
            self.flash(0.2, power=0.9)
            self.sfx("impact", 0.7)
            self.punch(0.1)

        def draw(out):
            n = len(ARMORY)
            for j, (key, _s, _l, _e) in enumerate(ARMORY):
                it = K.SHOP_BY_KEY[key]
                a = j * math.tau / n + self.t * 0.6
                k = ease_out((st - j * 0.04) / 0.35)
                rr = 420 * k + 900 * (1 - k)
                x, y = W / 2 + math.cos(a) * rr * 1.25, H / 2 + math.sin(a) * rr * 0.78
                leg = it.get("legendary")
                pygame.draw.circle(out, (24, 18, 36), (int(x), int(y)), 58)
                pygame.draw.circle(out, GOLD if leg else tuple(it["color"]), (int(x), int(y)), 58, 5)
                K.draw_icon(out, x, y, it.get("icon", "star"), GOLD if leg else tuple(it["color"]), r=34)
            self.title(out, "SONSUZ", W / 2, H / 2 - 70, 150, self.t - st + 0.1, None,
                       grad=(WHITE, (255, 200, 120)), stroke=9, glow=(255, 140, 40))
            self.title(out, "KOMBİNASYON.", W / 2, H / 2 + 80, 150, self.t - st + 0.45, None,
                       grad=((255, 236, 170), (255, 150, 40)), stroke=9, glow=(255, 140, 40))
        if self.at(st, 0.45):
            self.punch(0.08)
            self.sfx("impact", 0.5)
        self.ov(draw)

    # ------------------------------------------------------------------
    BOOK_KEYS = (("r_dmg", (255, 110, 90)), ("r_luck", (120, 235, 130)), ("r_crit", (255, 214, 90)))

    def _s_books(self, st, dt, first, dur):
        c = self.sh.display.canvas
        self.bg(c, (44, 28, 22), (12, 8, 10), "books")
        self.zoom, self.focus = 1.0 + 0.05 * st / dur, None
        if first:
            self.flash(0.2, col=(200, 160, 255), power=0.7)
            self.sfx("whoosh_down", 0.6)
        # arkada raf
        for sy in (210, 560):
            pygame.draw.rect(c, (92, 60, 36), pygame.Rect(0, sy, VW, 18))
            pygame.draw.rect(c, (128, 86, 52), pygame.Rect(0, sy, VW, 4))
        others = [b for b in K.BOOKS if b["key"] not in dict(self.BOOK_KEYS)][:24]
        for j, bk in enumerate(others):
            row, col = divmod(j, 12)
            x = 60 + col * 105 + (st * 30 if row == 0 else -st * 30)
            y = 150 if row == 0 else 500
            K.draw_book(c, x, y, 90, bk, self.t, locked=False, glow=False)
        dim = pygame.Surface((VW, VH), pygame.SRCALPHA)
        dim.fill((6, 4, 10, 150))
        c.blit(dim, (0, 0))
        for j, (key, colr) in enumerate(self.BOOK_KEYS):
            t_in = j * 1.0
            if st < t_in:
                continue
            bk = K.BOOK_BY_KEY[key]
            k = ease_out((st - t_in) / 0.35)
            cx = VW / 2 + (j - 1) * 330
            cy = 330 + (1 - k) * 300
            pul = 0.5 + 0.5 * math.sin(self.t * 6 + j)
            K.add_glow(c, cx, cy, 190, colr, 0.25 + 0.2 * pul)
            K.draw_book(c, cx, cy, 200, bk, self.t, locked=False, glow=True)
            if self.at(st, t_in):
                self.sfx("shing", 0.6)
                self.sfx("levelup", 0.4)
                self.punch(0.05)

        def draw(out):
            for j, (key, colr) in enumerate(self.BOOK_KEYS):
                t_in = j * 1.0
                if st < t_in + 0.15:
                    continue
                cx = W / 2 + (j - 1) * 330 * S
                nm = K.bk_name(K.BOOK_BY_KEY[key]).upper()
                self.title(out, nm, cx, 790, 54, self.t - st + t_in + 0.15, None, color=colr,
                           grad=(WHITE, colr), stroke=5, slam=0.3)
            self.title(out, "KİTAPLAR", W / 2, 110, 96, self.t - st + 0.1, None,
                       grad=((230, 210, 255), (170, 120, 255)), stroke=8, glow=(140, 80, 255))
            if st > 3.0:
                self.title(out, "HER KİTAP SİLAHINI BAŞKA BİR YÖNE BÜYÜTÜR", W / 2, 960, 48,
                           self.t - st + 3.0, None, color=(236, 232, 244), stroke=4, slam=0.2,
                           style="heavy")
        self.ov(draw)

    def _s_charge(self, st, dt, first, dur):
        c = self.sh.display.canvas
        self.bg(c, (30, 18, 46), (6, 4, 12), "charge")
        q = st / dur
        self.zoom, self.focus = 1.0 + 0.22 * ease_in_out(q), None
        cx, cy = VW / 2, VH / 2 - 10
        self.rays(c, cx, cy, self.t * (1 + 3 * q), col=(255, 230, 170), alpha=int(18 + 40 * q))
        merge = ease_in_out((st - 1.9) / 0.6)
        wx = cx - 300 * (1 - merge)
        bx = cx + 300 * (1 - merge)
        w = K.WEAPON_BY_KEY["tesla"]
        bk = K.BOOK_BY_KEY["r_dmg"]
        K.add_glow(c, wx, cy, 200, (150, 200, 255), 0.25 + 0.4 * q)
        K.add_glow(c, bx, cy, 200, (255, 110, 90), 0.25 + 0.4 * q)
        K.draw_weapon_emblem(c, wx, cy, 190, w, self.t, locked=False, glow=True)
        K.draw_book(c, bx, cy, 190, bk, self.t, locked=False, glow=True)
        # birleşen enerji parçacıkları
        rnd = random.Random(3)
        for i in range(60):
            a = rnd.uniform(0, math.tau)
            ph = (self.t * (0.6 + q * 1.8) + rnd.random()) % 1.0
            r = 520 * (1 - ph)
            x, y = cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7
            K.blit_disc(c, x, y, 2 + 2 * ph, (255, 240, 200), int(255 * ph))
        K.add_glow(c, cx, cy, 120 + 380 * q, (255, 245, 220), 0.1 + 0.5 * q * q)
        wl = 1 + int(min(1.0, st / 1.6) * 9)
        bl = 1 + int(min(1.0, st / 1.4) * 2)
        if int(st * FPS) % 5 == 0 and st < 1.7:
            self.sfx("crit", 0.18)
        if self.at(st, 1.6):
            self.sfx("levelup", 0.8)
            self.punch(0.06)
        self.shakes.append((self.t, 3 + 9 * q, 1.0 / FPS + 0.001))
        self.vig = 1.0

        def draw(out):
            if merge < 0.5:
                a = 1 - merge * 2
                for x, txt, sub, colr in ((wx * S, f"SEVİYE {wl}", "YILDIRIM ZİNCİRİ", (150, 200, 255)),
                                          (bx * S, f"SEVİYE {bl}", "HASAR KİTABI", (255, 120, 100))):
                    img = self.T.render(txt, 72, colr, "black", 6,
                                        grad=(WHITE, colr) if not txt.endswith(("10", " 3")) else ((255, 250, 210), GOLD),
                                        glow=GOLD if txt.endswith(("10", " 3")) else None).copy()
                    img.set_alpha(int(255 * a))
                    out.blit(img, (x - img.get_width() / 2, (cy + 150) * S))
                    s2 = self.T.render(sub, 36, (236, 232, 244), "heavy", 4).copy()
                    s2.set_alpha(int(255 * a))
                    out.blit(s2, (x - s2.get_width() / 2, (cy + 150) * S + 100))
                plus = self.T.render("+", 140, GOLD, "black", 8, glow=(255, 160, 40)).copy()
                plus.set_alpha(int(255 * a))
                out.blit(plus, (W / 2 - plus.get_width() / 2, cy * S - plus.get_height() / 2))
            # yükselen beyazlık
            wh = pygame.Surface((W, H))
            wh.fill((255, 250, 236))
            wh.set_alpha(int(200 * ease_in_out((st - 1.8) / 0.7) ** 2))
            out.blit(wh, (0, 0))
        self.ov(draw)

    def _s_evolve(self, st, dt, first, dur):
        c = self.sh.display.canvas
        if first:
            self.flash(0.9, col=(255, 255, 255), power=1.6)
            self.punch(0.3)
            self.shake(26, 0.6)
            self.speed(0.9, 1.2)
            self.sfx("shing", 1.0)
        self.bg(c, (255, 214, 120), (90, 40, 10), "evo")
        self.rays(c, VW / 2, VH / 2 - 20, self.t * 3, col=(255, 255, 230), alpha=70, n=28)
        cx, cy = VW / 2, VH / 2 - 20
        K.add_glow(c, cx, cy, 420, (255, 255, 240), 0.8)
        # altın, evrimleşmiş silah amblemi
        w = dict(K.WEAPON_BY_KEY["tesla"])
        w["color"] = GOLD
        sc = 1.0 + 0.08 * math.sin(self.t * 10)
        for r in range(3):
            K.ring_aa(c, cx, cy, (150 + r * 40 + st * 220) % 520, (255, 240, 190), 3)
        K.draw_weapon_emblem(c, cx + 230, cy, 220 * sc, w, self.t, locked=False, glow=True)
        K.draw_skin_preview(c, self.skin, cx - 210, cy + 10, self.t, r=78)
        K.add_glow(c, cx - 210, cy + 10, 160, (255, 255, 255), 0.55 + 0.25 * math.sin(self.t * 14))
        self.zoom, self.focus = 1.0 + 0.1 * (1 - ease_out(st / 0.8)), None
        self.grade = ((255, 245, 225), (12, 8, 0))

        def draw(out):
            self.title(out, "EVRİM!", W / 2, 180, 210, self.t - st + 0.15, None,
                       grad=((255, 255, 230), (255, 160, 30)), stroke=10, scol=(70, 30, 0),
                       glow=(255, 200, 80), slam=1.0)
            self.title(out, "YILDIRIM ZİNCİRİ  ★  EVRİMLEŞTİ", W / 2, 930, 60, self.t - st + 0.6, None,
                       color=WHITE, stroke=6, scol=(70, 30, 0), slam=0.3)
        self.ov(draw)
        if self.at(st, 0.15):
            self.sfx("impact", 0.6)

    def _s_power(self, st, dt, first, dur):
        if first:
            self.make_run(20, {"tesla": 22, "tornado": 20, "beam": 22, "pentagram": 22,
                               "meteor": 14}, 74, 80,
                          books={"r_dmg": (16, 4), "r_aspd": (12, 3), "r_crit": (10, 3)},
                          ring=60, prewarm=0.4)
            self.flash(0.3, col=(255, 240, 200), power=1.0)
        for x in (0.5, 2.5, 4.0):
            if self.at(st, x):
                self.bonk(1.2)
                self.ring(self.sh.run, 26)
        for x in (1.0, 2.0, 3.0):
            if self.at(st, x):
                self.punch(0.06)
        self.play(dt)
        self.zoom = 1.08 + 0.1 * math.sin(st * 0.6)
        self.grade = ((255, 240, 210), (16, 10, 0))

        def draw(out):
            self.title(out, "SİLAHINI EVRİMLEŞTİR.", W / 2, 170, 120, self.t - st + 0.2, None,
                       grad=(WHITE, (255, 210, 130)), stroke=9, glow=(255, 130, 30))
            self.title(out, "GÜCÜNÜ KATLA.", W / 2, 930, 150, self.t - st + 1.5, None,
                       grad=((255, 236, 160), (255, 120, 20)), stroke=10, glow=(255, 110, 20))
        if self.at(st, 1.5):
            self.sfx("impact", 0.6)
        self.ov(draw)

    # ------------------------------------------------------------------
    def _world(self, theme, st, dt, first, dur):
        wd = WORLDS[theme]
        if first:
            run = self.make_run(12, {"tesla": 8, "tornado": 6, "beam": 8, "pentagram": 8}, 30, 46,
                                theme=theme, books={"r_dmg": (6, 2)}, ring=34, prewarm=0.2)
            self.add_boss(run, wd["bosses"][0], -260, -150, theme=theme)
            self.add_boss(run, wd["bosses"][1], 260, -130, theme=theme)
            self.sfx("whoosh", 0.8)
            self.sfx("growl", 0.45, self.t + 0.3)
            self.punch(0.1)
        self.wipe = (st / 0.32, wd["col"])
        self.play(dt)
        run = self.sh.run
        if run.bosses:
            bx = sum(b.x for b in run.bosses) / len(run.bosses)
            by = sum(b.y for b in run.bosses) / len(run.bosses)
            px, py = run.world_to_screen(run.player.x, run.player.y)
            qx, qy = run.world_to_screen(bx, by)
            self.focus = ((px + qx) / 2, (py + qy) / 2)
        self.zoom = 1.12 + 0.06 * st / dur
        self.grade = wd["grade"]
        part = {"frost": "snow", "jungle": "leaves", "desert": "dust"}[theme]
        names = [K.MAP_BOSS_NAMES[theme][b] for b in wd["bosses"]]

        def draw(out):
            self.particles(out, part, n=140 if part != "dust" else 70)
            self.title(out, wd["name"], 70, 150, 120, self.t - st + 0.25, None, align="left",
                       grad=(WHITE, wd["col"]), stroke=9, glow=tuple(int(v * 0.7) for v in wd["col"]))
            self.title(out, wd["mobs"], 76, 250, 40, self.t - st + 0.55, None, align="left",
                        color=(236, 236, 244), stroke=4, style="heavy", slam=0.2)
            self.title(out, "PATRON: " + "  /  ".join(names), 76, 310, 46, self.t - st + 0.85, None,
                       align="left", color=(255, 120, 100), grad=((255, 210, 190), (255, 80, 60)),
                       stroke=5, slam=0.3)
            box = pygame.Surface((W, 92), pygame.SRCALPHA)
            box.fill((8, 6, 14, 190))
            out.blit(box, (0, H - 120))
            tl = self.T.render("3 FARKLI DÜNYA. HER BİRİ KENDİ CANAVARLARIYLA.", 54, WHITE, "black", 5)
            out.blit(tl, (W / 2 - tl.get_width() / 2, H - 74 - tl.get_height() / 2))
        self.ov(draw)

    def _s_frost(self, st, dt, first, dur):
        self._world("frost", st, dt, first, dur)

    def _s_jungle(self, st, dt, first, dur):
        self._world("jungle", st, dt, first, dur)

    def _s_desert(self, st, dt, first, dur):
        self._world("desert", st, dt, first, dur)

    # ------------------------------------------------------------------
    def _s_gate(self, st, dt, first, dur):
        if first:
            run = self.make_run(K.HELL_PORTAL_WAVE, {"tesla": 12, "tornado": 10, "beam": 12,
                                                     "pentagram": 12}, 34, 4)
            run.enemies[:] = run.enemies[:4]
            run.open_hell_portal()
            run.waves.announce_timer = 0.0
            run.fx.texts.clear()
            self.pilot.crowd = 0
            self.flash(0.3, col=(255, 60, 40), power=0.9)
            self.sfx("glitch", 0.5)
            self.sfx("growl", 0.9, self.t + 0.4)
        run = self.sh.run
        hp = run.hell_portal
        if hp is not None:
            self.pilot.target = (hp.x, hp.y)
            px, py = self.player_screen()
            qx, qy = run.world_to_screen(hp.x, hp.y)
            self.focus = (px * 0.35 + qx * 0.65, py * 0.35 + qy * 0.65)
        self.play(dt)
        self.zoom = 1.15 + 0.35 * ease_in_out(st / dur)
        self.grade = ((190, 120, 120), (18, 0, 0))
        self.vig = 1.0
        blink = int(self.t * 6) % 2 == 0

        def draw(out):
            # uyarı şeritleri
            for yy in (0, H - 56):
                band = pygame.Surface((W, 56), pygame.SRCALPHA)
                band.fill((0, 0, 0, 220))
                off = int(self.t * 160) % 80
                for x in range(-80, W + 80, 80):
                    pygame.draw.polygon(band, (220, 30, 20, 230), [(x + off, 0), (x + off + 40, 0),
                                                                   (x + off + 10, 56), (x + off - 30, 56)])
                out.blit(band, (0, yy))
            if blink or st < 0.4:
                self.title(out, "⚠ UYARI ⚠", W / 2, 200, 70, self.t - st + 0.05, None,
                           color=(255, 70, 50), stroke=6, slam=0.2)
            self.title(out, "25. DALGADA", W / 2, H / 2 + 120, 96, self.t - st + 0.2, None,
                       grad=(WHITE, (255, 170, 150)), stroke=8, glow=(160, 10, 0), slam=0.3)
            self.title(out, "CEHENNEM KAPISI AÇILIR...", W / 2, H / 2 + 240, 104, self.t - st + 0.7,
                       None, grad=((255, 200, 180), (255, 40, 20)), stroke=8, glow=(200, 20, 0),
                       slam=0.3, flicker=st > 2.0, chroma=st > 2.2)
        self.ov(draw)
        if self.at(st, 2.2):
            self.glitch(0.3)
            self.sfx("glitch", 0.7)

    def _hell_common(self, st, out_fn=None):
        self.grade = ((255, 150, 120), (26, 0, 0))
        self.vig = 1.0

    def _s_hellord(self, st, dt, first, dur):
        if first:
            run = self.make_run(K.HELL_PORTAL_WAVE + 3, {"tesla": 14, "tornado": 12, "beam": 14,
                                                         "pentagram": 14, "meteor": 10}, 50, 40,
                                books={"r_dmg": (10, 3)}, hell=True, ring=30, prewarm=0.2)
            self.add_boss(run, "warlord", 0, -170, hellish=True)
            self.flash(0.5, col=(255, 90, 40), power=1.2)
            self.punch(0.25)
            self.shake(24, 0.7)
            self.sfx("growl", 1.0)
        run = self.sh.run
        if self.at(st, 2.0):
            self.bonk(1.2)
        self.play(dt)
        if run.bosses and st < 1.3:
            b = run.bosses[0]
            qx, qy = run.world_to_screen(b.x, b.y)
            k = ease_in_out(st / 1.3)
            px, py = self.player_screen()
            self.focus = (qx + (px - qx) * k, qy + (py - qy) * k)
            self.zoom = 1.55 - 0.45 * k
        else:
            self.zoom = 1.1
        self._hell_common(st)

        def draw(out):
            self.particles(out, "embers", n=150)
            self.title(out, "CEHENNEM LORDU", W / 2, 170, 140, self.t - st + 0.1, None,
                       grad=((255, 220, 180), (255, 50, 20)), stroke=10, scol=(30, 0, 0),
                       glow=(220, 30, 0), slam=0.6)
            if st > 1.8:
                self.title(out, "EVRİMSİZ GİRME.", W / 2, 930, 130, self.t - st + 1.8, None,
                           grad=(WHITE, (255, 80, 50)), stroke=10, scol=(30, 0, 0),
                           glow=(220, 30, 0), chroma=int(self.t * 8) % 4 == 0)
        if self.at(st, 1.8):
            self.punch(0.12)
            self.sfx("impact", 0.8)
            self.glitch(0.2)
        self.ov(draw)

    def _s_dragon(self, st, dt, first, dur):
        run = self.sh.run
        if first:
            run.chests.clear()
            self.sfx("whoosh_down", 0.9)
            self.sfx("growl", 1.0, self.t + 0.5)
        if self.at(st, 0.8):
            cam = run.cam_rect()
            dg = K.Boss("dragon", cam.centerx + 240, cam.centery - 110, 1.0, 1.0, run.waves.wave,
                        hellish=True)
            run.bosses.append(dg)
            K.scale_bosses_to_player(run.bosses, run.player)
            run.waves.boss_active = True
            self.flash(0.4, col=(255, 120, 40), power=1.2)
            self.punch(0.2)
            self.shake(28, 0.8)
            self.sfx("impact_big", 0.9)
        if self.at(st, 2.4):
            self.bonk(1.2)
        self.play(dt)
        self.zoom = 1.12 if st > 0.8 else 1.25
        self._hell_common(st)

        def draw(out):
            if st < 1.0:                    # başın üstünden geçen ejderha gölgesi
                k = st / 1.0
                x = -700 + (W + 1400) * k
                y = H * 0.45 + math.sin(k * 3) * 40
                lay = self.layer
                lay.fill((0, 0, 0, 0))
                wing = math.sin(self.t * 9) * 140
                body = [(x - 320, y), (x - 80, y - 60), (x + 260, y - 30), (x + 380, y), (x + 260, y + 30),
                        (x - 80, y + 60)]
                pygame.draw.polygon(lay, (0, 0, 0, 175), body)
                pygame.draw.polygon(lay, (0, 0, 0, 160), [(x - 40, y - 20), (x + 120, y - 330 - wing),
                                                          (x + 200, y - 20)])
                pygame.draw.polygon(lay, (0, 0, 0, 160), [(x - 40, y + 20), (x + 120, y + 330 + wing),
                                                          (x + 200, y + 20)])
                pygame.draw.polygon(lay, (0, 0, 0, 170), [(x - 320, y), (x - 560, y - 40), (x - 520, y + 10)])
                out.blit(lay, (0, 0))
            self.particles(out, "embers", n=170)
            if st > 0.8:
                self.title(out, "KOR EJDERHA", W / 2, 170, 150, self.t - st + 0.85, None,
                           grad=((255, 230, 160), (255, 90, 20)), stroke=10, scol=(30, 0, 0),
                           glow=(255, 80, 0), slam=0.7)
            if st > 2.2:
                self.title(out, "EVRİMSİZ GİRME.", W / 2, 930, 130, self.t - st + 2.2, None,
                           grad=(WHITE, (255, 80, 50)), stroke=10, scol=(30, 0, 0),
                           glow=(220, 30, 0), flicker=st > 3.0)
        self.ov(draw)

    # ------------------------------------------------------------------
    def _s_crit(self, st, dt, first, dur):
        if first:
            self.make_run(14, {"knives": 10, "tesla": 8}, 30, 50,
                          books={"r_crit": (12, 4), "r_critd": (10, 4), "r_luck": (8, 3)},
                          shop={"gambler_dice": 2, "multishot": 3, "haste": 4}, ring=40, prewarm=0.3)
            self.flash(0.35, col=(255, 240, 160), power=1.0)
            self.punch(0.1)
        self.play(dt)
        self.zoom = 1.12
        self.grade = ((255, 246, 215), (10, 8, 0))
        pops = [0.25, 0.75, 1.25, 1.5, 1.75, 2.25, 2.5, 2.75, 3.0, 3.25]
        for x in pops:
            if self.at(st, x):
                self.sfx("crit", 0.55)
                self.punch(0.05)
        icons = (("horseshoe", 1.0, -560), ("dice", 1.5, 0), ("clover", 2.0, 560))
        for _n, x, _dx in icons:
            if self.at(st, x):
                self.sfx("shing", 0.5)

        def draw(out):
            rnd = random.Random(21)
            for j, x in enumerate(pops):
                px, py = rnd.uniform(330, W - 330), rnd.uniform(330, H - 300)
                lt = st - x
                if 0 <= lt < 0.6:
                    sz = 92 if j % 3 else 120
                    self.title(out, "KRİTİK!", px, py - lt * 80, sz, self.t - lt, self.t - lt + 0.6,
                               grad=((255, 255, 200), (255, 190, 20)), stroke=7, scol=(80, 30, 0),
                               glow=(255, 180, 0), slam=0.9)
            for kind, x, dx in icons:
                lt = st - x
                if lt < 0:
                    continue
                k = ease_out(lt / 0.3)
                cx, cy = W / 2 + dx, 190
                rr = int(80 * (0.4 + 0.6 * k))
                K.add_glow(out, cx, cy, 170, (120, 255, 140) if kind == "clover" else GOLD, 0.35)
                pygame.draw.circle(out, (24, 18, 36), (int(cx), int(cy)), rr)
                pygame.draw.circle(out, GOLD, (int(cx), int(cy)), rr, 6)
                if kind == "dice":
                    a = (1 - k) * 3 + math.sin(self.t * 3) * 0.1
                    sq = 70 * k
                    pts = [(cx + math.cos(a + i * math.pi / 2 + math.pi / 4) * sq * 0.7,
                            cy + math.sin(a + i * math.pi / 2 + math.pi / 4) * sq * 0.7) for i in range(4)]
                    pygame.draw.polygon(out, (245, 240, 230), pts)
                    for ox, oy in ((-1, -1), (1, 1), (0, 0), (1, -1), (-1, 1)):
                        rx = ox * math.cos(a) - oy * math.sin(a)
                        ry = ox * math.sin(a) + oy * math.cos(a)
                        pygame.draw.circle(out, (200, 30, 40), (int(cx + rx * sq * 0.25), int(cy + ry * sq * 0.25)), 6)
                else:
                    K.draw_icon(out, cx, cy, kind, (120, 255, 140) if kind == "clover" else GOLD, r=int(48 * k) + 1)
            self.title(out, "ŞANSINI DENE.", W / 2, 930, 140, self.t - st + 0.3, None,
                       grad=((200, 255, 200), (90, 220, 110)), stroke=9, scol=(0, 30, 10),
                       glow=(60, 200, 90))
        self.ov(draw)

    RIVALS = (("ZeyNo", 148200, 41), ("BonkUstası", 131900, 38), ("Ayaz_41", 120450, 36),
              ("KralMert", 98700, 33), ("Efe_TR", 91200, 31), ("Duru", 84330, 29),
              ("Selin07", 77010, 27), ("Ozi", 65800, 24), ("Kuzey", 52400, 22))

    def _s_ranking(self, st, dt, first, dur):
        c = self.sh.display.canvas
        self.bg(c, (22, 30, 64), (8, 8, 20), "rank")
        self.rays(c, VW / 2, -80, self.t, col=(120, 160, 255), alpha=16)
        self.zoom, self.focus = 1.0, None
        if first:
            self.flash(0.2, col=(160, 200, 255), power=0.8)
            self.sfx("whoosh", 0.8)
        q = ease_in_out((st - 0.3) / 2.5)
        mine = 40500 + (152340 - 40500) * q
        rows = [(n, s, w, False) for n, s, w in self.RIVALS] + [("SEN", mine, 44, True)]
        rows.sort(key=lambda r: -r[1])
        rank_now = [r[0] for r in rows].index("SEN")
        prev_rank = getattr(self, "_prev_rank", rank_now)
        if rank_now < prev_rank:
            self.sfx("coin", 0.7)
            self.sfx("whoosh", 0.25)
        if rank_now == 0 and prev_rank != 0:
            self._rank1_t = self.t
            self.sfx("impact", 0.8)
            self.punch(0.12)
            self.flash(0.25, col=(255, 230, 150), power=0.7)
        self._prev_rank = rank_now
        top = 150
        rh = 47
        for i, (nm, sc, wv, me) in enumerate(rows):
            ty = top + i * rh
            y = self.rank_y.get(nm, ty)
            y += (ty - y) * min(1.0, dt * 14)
            self.rank_y[nm] = y
        for i, (nm, sc, wv, me) in sorted(enumerate(rows), key=lambda r: r[1][3]):
            y = self.rank_y[nm]
            r = pygame.Rect(240, int(y), 800, rh - 8)
            if me:
                K.add_glow(c, r.centerx, r.centery, 420, GOLD, 0.25)
                K.panel(c, r, bg=(70, 52, 20), edge=GOLD, alpha=250, radius=12, edge_w=3)
            else:
                K.panel(c, r, bg=(26, 26, 46), edge=(70, 80, 130), alpha=235, radius=12, edge_w=1)
            medal = {0: (255, 214, 90), 1: (210, 214, 230), 2: (214, 150, 90)}.get(i)
            if medal:
                pygame.draw.circle(c, medal, (r.x + 34, r.centery), 17)
                K.draw_text(c, str(i + 1), (r.x + 34, r.centery), 18, (30, 20, 10), bold=True, center=True)
            else:
                K.draw_text(c, str(i + 1), (r.x + 34, r.centery), 20, (200, 205, 230), bold=True, center=True)
            K.draw_text(c, nm, (r.x + 72, r.centery - 12), 22, GOLD if me else (236, 236, 250), bold=True)
            K.draw_text(c, f"Dalga {wv}", (r.x + 470, r.centery - 10), 18, (170, 176, 210), bold=True)
            K.draw_text(c, fmt_int(sc), (r.right - 24, r.centery - 12), 22, GOLD if me else WHITE,
                        bold=True, right=True)
            if me and rank_now > 0:
                K.draw_text(c, "▲", (r.x + 130, r.centery - 12), 20, (120, 255, 140), bold=True)
        if rank_now == 0:                      # konfeti
            lt = st - 2.8
            for i in range(80):
                x = (i * 97.7 + math.sin(st * 2 + i) * 30) % VW
                y = (max(0, lt) * (200 + (i % 7) * 40) + i * 23) % (VH + 40) - 20
                colr = ((255, 214, 110), (255, 120, 140), (120, 210, 255), (150, 240, 160))[i % 4]
                pygame.draw.rect(c, colr, pygame.Rect(int(x), int(y), 6, 10))

        def draw(out):
            self.title(out, "DÜNYA SIRALAMASI", W / 2, 95, 96, self.t - st + 0.1, None,
                       grad=(WHITE, (140, 190, 255)), stroke=8, glow=(60, 110, 255))
            self.title(out, "DÜNYAYLA YARIŞ.", W / 2, 1000, 104, self.t - st + 0.5, None,
                       grad=((200, 230, 255), (90, 160, 255)), stroke=9, glow=(50, 100, 255))
            if rank_now == 0:
                self.title(out, "1.", 1740, 330, 190, getattr(self, "_rank1_t", self.t), None,
                           grad=((255, 250, 200), (255, 180, 40)), stroke=9, glow=(255, 170, 30),
                           slam=1.0)
                self.title(out, "SENSİN!", 1740, 470, 64, getattr(self, "_rank1_t", self.t) + 0.1, None,
                           grad=((255, 250, 200), (255, 180, 40)), stroke=8, glow=(255, 170, 30),
                           slam=0.9)
        self.ov(draw)

    def _s_badges(self, st, dt, first, dur):
        c = self.sh.display.canvas
        self.bg(c, (40, 28, 64), (10, 6, 20), "badge")
        self.rays(c, VW / 2, VH / 2, self.t, alpha=22)
        self.zoom, self.focus = 1.02, None
        achs = [a for a in K.ACHIEVEMENTS if a.get("icon")][::max(1, len(K.ACHIEVEMENTS) // 8)][:6]
        tiers = {"bronz": (214, 150, 90), "gümüş": (210, 214, 230), "altın": GOLD}
        for j, a in enumerate(achs):
            t_in = j * 0.16
            if st < t_in:
                continue
            if self.at(st, t_in):
                self.sfx("crit", 0.45)
                self.punch(0.03)
            k = ease_out((st - t_in) / 0.25)
            cx = VW / 2 + (j - 2.5) * 185
            cy = 330
            col = tiers.get(a.get("tier"), GOLD)
            rr = 64 * (0.3 + 0.7 * k) * (1 + 0.15 * (1 - k))
            K.add_glow(c, cx, cy, 130, col, 0.3)
            pygame.draw.circle(c, (30, 22, 44), (int(cx), int(cy)), int(rr))
            pygame.draw.circle(c, col, (int(cx), int(cy)), int(rr), 6)
            K.draw_icon(c, cx, cy, a["icon"], col, r=int(30 * k) + 1)
            K.draw_text(c, K.ach_name(a) if hasattr(K, "ach_name") else a["name"], (cx, cy + 92), 18,
                        (236, 232, 244), bold=True, center=True)

        def draw(out):
            self.title(out, "BAŞARIM AÇILDI!", W / 2, 130, 72, self.t - st + 0.05, None,
                       color=GOLD, grad=((255, 250, 210), GOLD), stroke=6, slam=0.3)
            self.title(out, "ZİRVEYE ÇIK.", W / 2, 880, 170, self.t - st + 0.35, None,
                       grad=((255, 250, 200), (255, 170, 30)), stroke=10, glow=(255, 150, 20))
        if self.at(st, 0.35):
            self.sfx("impact", 0.7)
            self.punch(0.1)
        self.ov(draw)

    # ------------------------------------------------------------------
    def _s_reel(self, st, dt, first, dur):
        n = 12
        i = int(st / 0.2)
        self.vig = 0.0

        def draw(out):
            if self.snaps and i < n:
                snap = self.snaps[int(i * len(self.snaps) / n)]
                lt = st - i * 0.2
                z = 1.12 - 0.12 * ease_out(lt / 0.2)
                img = pygame.transform.smoothscale(snap, (int(W * z), int(H * z)))
                out.blit(img, (-(img.get_width() - W) / 2, -(img.get_height() - H) / 2))
            else:
                out.fill((255, 255, 255))
        if int(st / 0.2) != int((st - 1.0 / FPS) / 0.2) or first:
            if i < n:
                self.flash(0.09, power=0.8)
                self.sfx("impact" if i % 4 == 0 else "whoosh", 0.35)
                self.glitch(0.06)
        self.ov(draw)
        self.sh.display.canvas.fill((0, 0, 0))

    def _s_logo(self, st, dt, first, dur):
        c = self.sh.display.canvas
        c.fill((0, 0, 0))
        self.zoom, self.focus = 1.0, None
        self.vig = 1.0
        if first:
            self.sfx("whoosh_down", 0.7)
        if self.at(st, 0.3):
            self.punch(0.15)
            self.shake(18, 0.4)
            self.sfx("impact", 0.7)
            self.flash(0.2, col=(255, 220, 160), power=0.8)
        if self.at(st, 2.5):                     # 89,0 — final vuruş
            self.punch(0.22)
            self.shake(30, 0.6)
            self.flash(0.3, power=1.0)
            self.glitch(0.25)
        if st > 0.3:
            k = ease_out((st - 0.3) / 0.6)
            self.rays(c, VW / 2, VH / 2 - 70, self.t, alpha=int(34 * k))
            K.add_glow(c, VW / 2, VH / 2 - 70, 520, (230, 140, 50), 0.35 * k)
            badge = K.brand_scaled("badge", h=150)
            if badge is not None:
                img = badge.copy()
                img.set_alpha(int(255 * k))
                c.blit(img, (VW / 2 - img.get_width() / 2, 40 + (1 - k) * -60))

        def draw(out):
            self.particles(out, "embers", n=90)
            if st >= 0.3:
                self.title(out, "EVOLVE", W / 2, 440, 230, self.t - st + 0.3, None,
                           grad=((255, 252, 230), (255, 196, 80)), stroke=12, scol=(40, 16, 0),
                           glow=(255, 150, 30), slam=0.9)
                self.title(out, "ARENA", W / 2, 640, 230, self.t - st + 0.45, None,
                           grad=((255, 160, 90), (210, 50, 20)), stroke=12, scol=(40, 8, 0),
                           glow=(255, 70, 20), slam=0.9)
            if st >= 1.1:
                self.title(out, "ŞİMDİ İNDİR.", W / 2, 850, 110, self.t - st + 1.1, None,
                           color=WHITE, stroke=8, glow=(255, 255, 255), slam=0.4)
            if st >= 1.6:
                self.title(out, "HAYATTA KALABİLECEK MİSİN?", W / 2, 965, 64, self.t - st + 1.6, None,
                           grad=((255, 220, 200), (255, 90, 60)), stroke=6, slam=0.3,
                           chroma=st > 2.5 and st < 2.8)
            fade = max(0.0, (st - 3.2) / 0.3)
            if fade > 0:
                blk = pygame.Surface((W, H))
                blk.fill((0, 0, 0))
                blk.set_alpha(int(255 * min(1.0, fade)))
                out.blit(blk, (0, 0))
        self.ov(draw)


# =====================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default=os.path.join(ROOT, "evolve_arena_trailer.mp4"))
    ap.add_argument("--stills", default="", help="virgülle saniyeler: yalnız PNG kareler yaz")
    ap.add_argument("--from", dest="t_from", type=float, default=0.0)
    ap.add_argument("--to", dest="t_to", type=float, default=LENGTH)
    ap.add_argument("--crf", type=int, default=19)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed % (2 ** 32))
    K.sfx = lambda *a, **k: None                   # oyunun kendi sesi kapalı
    app = K.App()
    tr = Trailer(app)
    out = pygame.Surface((W, H))

    stills = sorted(float(x) for x in args.stills.split(",") if x.strip())
    t_end = min(LENGTH, args.t_to)
    if stills:
        t_end = min(t_end, stills[-1] + 1.0 / FPS)
    n0 = int(round(args.t_from * FPS))
    n1 = int(round(t_end * FPS))

    proc = None
    silent = os.path.join(_TMP, "video.mp4")
    if not stills:
        proc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
             "-crf", str(args.crf), "-pix_fmt", "yuv420p", silent],
            stdin=subprocess.PIPE)
    t0 = time.time()
    still_dir = os.path.splitext(args.out)[0] + "_stills"
    for i in range(n0, n1):
        t = i / FPS
        tr.frame(t, out)
        if proc:
            proc.stdin.write(pygame.image.tobytes(out, "RGB"))
        for s in stills:
            if abs(t - s) < 0.5 / FPS:
                os.makedirs(still_dir, exist_ok=True)
                p = os.path.join(still_dir, f"t{s:05.1f}_{tr.cur_scene}.png")
                pygame.image.save(out, p)
                print("kare:", p)
        if i % (FPS * 5) == 0:
            print(f"  {t:5.1f} sn  [{tr.cur_scene}]  ({time.time() - t0:.0f} sn geçti)", flush=True)
    if not proc:
        return
    proc.stdin.close()
    proc.wait()
    print("görüntü bitti, ses sentezleniyor...", flush=True)
    wav = os.path.join(_TMP, "audio.wav")
    # ses her zaman tam film zaman çizelgesinde üretilir; parça render'da
    # ilgili aralık -ss ile kesilir (müzik ve kesimler senkron kalsın)
    A.render(list(tr.events), LENGTH, wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-ss", str(args.t_from),
           "-t", str(t_end - args.t_from), "-i", wav, "-map", "0:v", "-map", "1:a",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
           args.out]
    subprocess.run(cmd, check=True)
    print(f"tamam: {args.out}  ({time.time() - t0:.0f} sn)")


if __name__ == "__main__":
    main()
