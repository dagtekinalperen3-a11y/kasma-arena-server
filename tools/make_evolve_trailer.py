#!/usr/bin/env python3
"""
EVOLVE ARENA — TANITIM FRAGMANI (1920x1080, 30 fps, ~1:52, MP4)
==============================================================

Her oyun karesi oyunun GERÇEK motoru ve GERÇEK ekranlarıdır: oyun dosyası
(kasma_arena13.py) içe aktarılır, oyunun kendi "gölge oyun" altyapısı
(GameTour / App(shadow_of=...)) ekransız çalıştırılır; menülerde sanal bir
imleç gezer, savaşları insan gibi nişan alan otomatik pilot oynar.

Akış:
  karanlık kanca -> yaratık dalgası -> KAYIT OL -> ANA MENÜ -> HARİTA SEÇ ->
  normal oynanış (koş / dash / BONK) -> B MARKET (bir kez) -> SİLAHLIK ->
  silah detayı + EVRİM YOLU -> EVRİMİ İZLE (I / II / III canlı) -> 8 silahın
  oyunda evrimleşmesi -> KİTAP + SİLAH = EVRİM mantığı -> seviye atlayınca
  EVRİM KARTI -> evrimleşmiş güç -> Buzul / Orman / Çöl (patronlar) ->
  cehennem kapısı -> Cehennem Lordu -> Kor Ejderha -> KRİTİK -> gerçek
  DÜNYA SIRALAMASI -> highlight reel -> logo + ŞİMDİ İNDİR

Oyun normal görüş açısıyla izlenir; kamera yalnızca patron gelişlerinde
yaklaşır. Fragman katmanı (oyunda olmayan): flaş, zoom-punch, sarsıntı, hız
çizgileri, dünyaya göre renk paleti, parçacıklar, 1080p trailer yazıları.
Müzik ve SFX tools/trailer_audio.py ile sentezlenir (telifsiz), 120 BPM
ızgarasına oturan kesimlerle senkron.

Gerçek oyuncu kaydına dokunmaz (ARENA_SAVE_DIR geçici klasöre yönlenir),
ağa bağlanmaz, pencere açmaz.

Kullanım:
    python3 tools/make_evolve_trailer.py --game yol/kasma_arena13.py -o fragman.mp4
    python3 tools/make_evolve_trailer.py --stills 10,40,66                # yalnız PNG
    python3 tools/make_evolve_trailer.py --from 72 --to 86 -o dunyalar.mp4

--game verilmezse depodaki kasma_arena13.py kullanılır. Oyun dosyası EVRİM
sistemini (EVOLUTIONS) içermelidir (EvolveArena sürümü).

Gerekenler: pygame, numpy, scipy ve PATH'te ffmpeg.
"""
import argparse
import importlib.util
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
sys.path.insert(0, HERE)


def _game_path():
    for i, a in enumerate(sys.argv):
        if a == "--game" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith("--game="):
            return a.split("=", 1)[1]
    return os.path.join(ROOT, "kasma_arena13.py")


GAME = os.path.abspath(_game_path())
sys.path.insert(0, os.path.dirname(GAME))

import numpy as np          # noqa: E402
import pygame               # noqa: E402

_spec = importlib.util.spec_from_file_location("kasma_arena13", GAME)
K = importlib.util.module_from_spec(_spec)
sys.modules["kasma_arena13"] = K
_spec.loader.exec_module(K)
if not hasattr(K, "EVOLUTIONS"):
    sys.exit("Bu oyun dosyasında EVRİM sistemi yok (EVOLUTIONS). EvolveArena sürümünü "
             "--game ile verin.")

import trailer_audio as A   # noqa: E402

W, H = 1920, 1080
VW, VH = K.VIRTUAL_W, K.VIRTUAL_H
S = W / VW                   # kanvas -> 1080p ölçeği (1.5)
FPS = 30
LENGTH = 112.0
GOLD = (255, 204, 92)
WHITE = (255, 255, 255)
PLAYER = "Kanka"

# (başlangıç, bitiş, sahne) — kesimler 120 BPM vuruş ızgarasında (0,5 sn)
SCENES = (
    (0.0, 3.5, "dark"),        # kapkaranlık + "CEHENNEM KAPISI AÇILIYOR..."
    (3.5, 8.0, "hook"),        # flaş — yaratık dalgasının ortasında
    (8.0, 14.0, "register"),   # KAYIT OL
    (14.0, 18.0, "menu"),      # ANA MENÜ -> OYNA
    (18.0, 21.5, "mapsel"),    # HARİTA SEÇ -> BAŞLA
    (21.5, 30.0, "play"),      # normal oynanış: koş, dash, BONK
    (30.0, 31.5, "market"),    # B — market bir kez
    (31.5, 34.0, "survive"),   # KOŞ. VUR. HAYATTA KAL.
    (34.0, 39.0, "codex"),     # SİLAHLIK
    (39.0, 42.5, "wdetail"),   # silah detayı: evrim yolu
    (42.5, 49.0, "evopv"),     # EVRİMİ İZLE: I / II / III
    (49.0, 61.0, "arsenal"),   # 8 silah oyunda evrimleşir
    (61.0, 64.5, "evologic"),  # SİLAH + EŞ KİTAP = EVRİM
    (64.5, 67.5, "evocard"),   # seviye atla: EVRİM KARTI
    (67.5, 72.0, "power"),     # evrimleşmiş güç
    (72.0, 76.5, "frost"),     # Buzul Vadisi
    (76.5, 81.0, "jungle"),    # Zümrüt Orman
    (81.0, 85.5, "desert"),    # Kızıl Çöl
    (85.5, 88.0, "gate"),      # cehennem kapısı — gerilim nefesi
    (88.0, 92.0, "hellord"),   # CEHENNEM LORDU
    (92.0, 96.0, "dragon"),    # KOR EJDERHA
    (96.0, 99.0, "crit"),      # KRİTİK! + şans
    (99.0, 104.5, "ranking"),  # gerçek DÜNYA SIRALAMASI
    (104.5, 107.0, "reel"),    # highlight reel
    (107.0, 112.0, "logo"),    # logo + ŞİMDİ İNDİR
)
EVO_HIT = 67.0                 # EVRİM kartına tıklama anı (müzikte BRAAAM)
FINAL_HIT = 110.0

# müzik planı (tools/trailer_audio.py) — sahnelerle aynı zaman çizelgesi
AUDIO_PLAN = dict(
    sections=((0.0, "tense"), (8.0, "lite"), (21.5, "drive"), (61.0, "books"),
              (EVO_HIT, "drive"), (85.5, "breath"), (88.0, "hell"), (96.0, "win"),
              (107.0, "final"), (FINAL_HIT, "end")),
    braams=((21.5, 26, 1.0, 0.9), (EVO_HIT, 26, 1.3, 1.0), (88.0, 25, 1.1, 1.0),
            (92.0, 25, 1.2, 0.95), (FINAL_HIT, 26, 1.4, 1.0)),
    impacts=((8.0, 0.45), (21.5, 0.9), (EVO_HIT, 1.0), (88.0, 1.0), (96.0, 0.6),
             (FINAL_HIT, 1.0)),
    risers=((5.0, 3.0, 0.55), (18.5, 3.0, 0.5), (64.5, 2.5, 0.75), (82.5, 3.0, 0.45),
            (107.5, 2.5, 0.6)),
    heart_fast=85.5, heart_slow=88.0,
)
SNAP_TIMES = (4.7, 10.6, 15.6, 25.2, 33.0, 45.6, 50.0, 54.6, 59.6, 67.4, 70.2, 74.6,
              79.2, 83.8, 89.6, 93.6, 97.6, 102.9)

# oyunda evrimleşen silahlar: (silah, kademe)
ARSENAL = (("whip", 1), ("tornado", 2), ("ghost_swords", 3), ("wolves", 1), ("tesla", 2),
           ("meteor", 3), ("beam", 2), ("bats", 3))
ARSENAL_DUR = 1.5
EVO_KEY = "axe"                # evrim mantığı / EVRİM kartı / önizleme bu silahla

WORLDS = {
    "frost": dict(col=(150, 210, 255), bosses=("warlord", "witch"),
                  mobs="YETİLER · KURTLAR · BUZ GOLEMLERİ",
                  grade=((205, 226, 255), (8, 18, 34))),
    "jungle": dict(col=(120, 235, 130), bosses=("witch", "colossus"),
                   mobs="YILANLAR · GORİLLER · PANTERLER",
                   grade=((210, 240, 200), (0, 14, 4))),
    "desert": dict(col=(255, 176, 80), bosses=("warlord", "colossus"),
                   mobs="AKREPLER · MUMYALAR · ÇAKALLAR",
                   grade=((255, 228, 190), (24, 10, 0))),
}
RIVALS = (("ZeyNo", 148200, 41, 4770), ("BonkUstası", 103499, 35, 4340),
          ("Ayaz_41", 89009, 32, 3920), ("KralMert", 76547, 29, 3410),
          ("Efe_TR", 65830, 26, 3020), ("Duru", 56613, 23, 2700),
          ("Selin07", 48687, 20, 2310), ("Ozi", 41870, 17, 1960), ("Kuzey", 36008, 14, 1640))


# =====================================================================
# yardımcılar
# =====================================================================
def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lerp_path(keys, t):
    """[(t, (x, y)), ...] üzerinde yumuşak yol."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            k = ease_in_out((t - t0) / max(1e-6, t1 - t0))
            return (p0[0] + (p1[0] - p0[0]) * k, p0[1] + (p1[1] - p0[1]) * k)
    return keys[-1][1]


def _find_font(names):
    dirs = ["/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/inter",
            "/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
            "C:/Windows/Fonts", "/Library/Fonts", "/System/Library/Fonts"]
    for nm in names:
        for d in dirs:
            p = os.path.join(d, nm)
            if os.path.isfile(p):
                return p
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for r, _ds, fs in os.walk(d):
            for nm in names:
                if nm in fs:
                    return os.path.join(r, nm)
    return None


class Type:
    """1080p trailer yazıları: kontur, gölge, parıltı, gradyan."""

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
        run.find_note = None                # "gezgin tüccar / buluntu" notları filmde çıkmasın
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
        self.vignette = self._make_vignette()
        self.layer = pygame.Surface((W, H), pygame.SRCALPHA)
        self.rng = random.Random(11)
        self._vitrin_save()
        for theme in ("frost", "jungle", "desert"):          # zeminleri önceden çiz
            try:
                K.floor_surface(theme)
            except Exception:
                pass

    def _vitrin_save(self):
        """Fragman kaydı: bütün haritalar ve silahlar açık, hesap kapalı."""
        d = self.sh.save.data
        st = d.setdefault("stats", {})
        st["stone_cleared"] = 1
        for th in ("frost", "jungle", "desert"):
            st[th + "_kills"] = max(int(st.get(th + "_kills", 0) or 0), 120)
        d["weapons_owned"] = list(K.WEAPON_BY_KEY)
        d["weapons_muted"] = []
        self.sh.account.account = None

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

    def tap(self, pos, gain=0.6):
        """Sanal imleç tıklaması: halka + ses (oyunun düğmesine basmaz)."""
        self.clicks.append((pos, self.t))
        self.sfx("click", gain)

    # ------------------------------------------------------------------
    def make_run(self, wave=8, weapons=None, level=20, crowd=30, books=None, theme="stone",
                 hell=False, ring=0, rmin=140, rmax=380, prewarm=0.0, announce=False):
        sh = self.sh
        sh.start_run()
        run = sh.run
        run.set_map_theme(theme)
        run.merchant = None
        run.quests = []
        run.ach = None
        run.cursed_next_wave = 999          # filmde lanetli mağara bildirimi çıkmasın
        run.lectern_done = True             # "gizemli KÜRSÜ belirdi" bildirimi de
        p = run.player
        p.no_stats = True
        p.take_damage = lambda *a, **k: 0
        p.weapons = dict(weapons or {})
        for k in p.weapons:
            p.weapon_timers[k] = 0.0
        for bk, (lv, tier) in (books or {}).items():
            for _ in range(lv):
                p.take_book(bk, tier)
        p.level = level
        if hell:
            run.waves.wave = K.HELL_PORTAL_WAVE
            run.enter_hell()
        if wave > 1:
            run.waves._begin_wave(wave, run.score)
        if not announce:
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
        run.fx.shake(10, 0.3)
        self.shake(10 * power, 0.3)
        self.sfx("bonk", 0.9)

    def evolve(self, run, key, tier):
        """Silahı istenen kademeye taşır; son adım ekranda (flaş + afiş)."""
        p = run.player
        while K.evo_tier(p, key) < tier - 1:
            run.evolve_weapon(key)
        run.evolve_weapon(key)

    def play(self, dt):
        self._play(dt)

    def player_screen(self):
        run = self.sh.run
        if run is None:
            return VW / 2, VH / 2
        return run.world_to_screen(run.player.x, run.player.y)

    def boss_zoom(self, run, lt, t_in=0.0, hold=1.2, z=1.45):
        """Patron gelişi: kamera patrona yaklaşır, sonra normal görüşe döner."""
        bs = [b for b in run.bosses if b.alive]
        if not bs or lt < t_in:
            return
        q = lt - t_in
        if q < 0.35:
            k = ease_out(q / 0.35)
        elif q < 0.35 + hold:
            k = 1.0
        else:
            k = 1.0 - ease_in_out((q - 0.35 - hold) / 0.5)
        if k <= 0:
            return
        bx = sum(b.x for b in bs) / len(bs)
        by = sum(b.y for b in bs) / len(bs)
        qx, qy = run.world_to_screen(bx, by)
        self.zoom = 1.0 + (z - 1.0) * k
        self.focus = (VW / 2 + (qx - VW / 2) * k, VH / 2 + (qy - VH / 2) * k)

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

    def ui_cursor(self, pos):
        self.cursor(pos)
        c = self.sh.display.canvas
        for (p, t0) in self.clicks:
            k = (self.t - t0) / 0.45
            if 0 <= k <= 1:
                K.ring_aa(c, p[0], p[1], 8 + 34 * k, (255, 236, 170), max(1, int(5 * (1 - k))))

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
            a = min(a, max(0.0, (t1 - self.t) / 0.15))
        if flicker:
            a *= 0.35 + 0.65 * (self.rng.random() > 0.25)
        if sc != 1.0:
            img = pygame.transform.smoothscale(img, (int(img.get_width() * sc),
                                                     int(img.get_height() * sc)))
        iw, ih = img.get_size()
        x = cx - iw / 2 if align == "center" else (cx if align == "left" else cx - iw)
        y = cy - ih / 2
        if chroma or lt < 0.1:
            d = 9 if chroma else int(10 * (1 - lt / 0.1))
            if d > 0:
                for tint, dx in (((255, 40, 60), -d), ((40, 220, 255), d)):
                    g = img.copy()
                    g.fill(tint + (255,), special_flags=pygame.BLEND_RGBA_MULT)
                    g.set_alpha(int(130 * a))
                    out.blit(g, (x + dx, y), special_flags=pygame.BLEND_ADD)
        if a < 1.0:
            img = img.copy()
            img.set_alpha(int(255 * a))
        out.blit(img, (x, y))

    def band(self, out, text, t0, t1, col=GOLD, sub=None, y=985, size=66):
        """UI ekranlarında alt yazı şeridi: ekranın altını hafifçe karartır."""
        lt = self.t - t0
        if lt < 0 or self.t >= t1:
            return
        a = min(1.0, lt / 0.15, (t1 - self.t) / 0.15)
        hh = 150 if sub else 118
        strip = pygame.Surface((W, hh), pygame.SRCALPHA)
        for i in range(hh):
            al = int(215 * a * min(1.0, i / 30.0))
            pygame.draw.line(strip, (6, 4, 12, al), (0, i), (W, i))
        out.blit(strip, (0, H - hh))
        self.title(out, text, W / 2, y if not sub else y - 22, size, t0, t1,
                   grad=(WHITE, col), stroke=6, slam=0.25)
        if sub:
            self.title(out, sub, W / 2, y + 40, 34, t0 + 0.1, t1, color=(236, 232, 244),
                       stroke=4, slam=0.1, style="heavy")

    def keycap(self, out, label, sub, x, y, t0, t1, col=(255, 214, 120)):
        lt = self.t - t0
        if lt < 0 or self.t >= t1:
            return
        k = ease_out(lt / 0.25)
        a = min(1.0, (t1 - self.t) / 0.2)
        f = self.T.render(label, 40, WHITE, "heavy", 0, shadow=False)
        w = f.get_width() + 44
        r = pygame.Rect(0, 0, w, 74)
        r.topleft = (int(x), int(y + (1 - k) * 60))
        box = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(box, (14, 10, 24, 220), box.get_rect(), border_radius=14)
        pygame.draw.rect(box, col + (255,), box.get_rect(), width=4, border_radius=14)
        pygame.draw.rect(box, col + (255,), pygame.Rect(0, r.h - 10, r.w, 10),
                         border_bottom_left_radius=14, border_bottom_right_radius=14)
        box.blit(f, (22, 9))
        box.set_alpha(int(255 * k * a))
        out.blit(box, r.topleft)
        s = self.T.render(sub, 34, col, "black", 4).copy()
        s.set_alpha(int(255 * a))
        out.blit(s, (r.right + 10, r.y + 37 - s.get_height() / 2))

    # ------------------------------------------------------------------
    # 1080p parçacıklar
    def particles(self, out, kind, n=120, alpha=1.0):
        t = self.t
        rnd = random.Random(99)
        if kind == "snow":
            for i in range(n):
                x0, y0, sp, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(140, 420), rnd.choice((2, 3, 3, 4, 5))
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
                pygame.draw.line(lay, (255, 214, 150, int(80 * alpha)), (x, y), (x + ln, y + 4), 2)
            out.blit(lay, (0, 0))
        elif kind == "embers":
            for i in range(n):
                x0, y0, sp, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(60, 260), rnd.choice((2, 2, 3, 4))
                x = (x0 + math.sin(t * 1.5 + i) * 40) % W
                y = (y0 - t * sp) % H
                col = rnd.choice(((255, 120, 40), (255, 180, 70), (255, 70, 30)))
                if alpha >= 1 or rnd.random() < alpha:
                    pygame.draw.circle(out, col, (int(x), int(y)), r)

    @staticmethod
    def _make_vignette():
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        a = np.clip((d - 0.7) / 0.75, 0, 1) ** 1.6 * 190
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
        # sahne başına varsayılanlar: NORMAL GÖRÜŞ (yakınlaştırma yok)
        self.zoom, self.focus, self.grade = 1.0, None, None
        self.blur, self.vig = 0.0, 0.6
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
        sx = sy = 0.0
        amp_now = 0.0
        for t0, amp, dur in self.shakes:
            if t0 <= t < t0 + dur:
                k = 1 - (t - t0) / dur
                amp_now += amp * k
                sx += self.rng.uniform(-1, 1) * amp * k / S
                sy += self.rng.uniform(-1, 1) * amp * k / S
        z = max(1.0 + amp_now * 0.0016, z)      # sarsıntıya pay bırak
        if self.focus is None:
            fx, fy = VW / 2, VH / 2
        elif self.focus == "player":
            fx, fy = self.player_screen()
        else:
            fx, fy = self.focus
        w, h = VW / z, VH / z
        x = K.clamp(fx - w / 2 + sx, 0, VW - w)
        y = K.clamp(fy - h / 2 + sy, 0, VH - h)
        if z <= 1.0001:
            pygame.transform.smoothscale(c, (W, H), out)
            return
        sub = c.subsurface(pygame.Rect(int(x), int(y), int(w), int(h)))
        pygame.transform.smoothscale(sub, (W, H), out)

    def post(self, out):
        t = self.t
        if self.blur > 0 and self.last_pre is not None:
            g = self.last_pre.copy()
            g.set_alpha(int(150 * self.blur))
            out.blit(g, (0, 0))
        if self.grade:
            mul, add = self.grade
            out.fill(mul, special_flags=pygame.BLEND_MULT)
            out.fill(add, special_flags=pygame.BLEND_ADD)
        pw = 0.0
        for t0, dur, power in self.speeds:
            if t0 <= t < t0 + dur:
                pw = max(pw, power * (1 - (t - t0) / dur) ** 0.7)
        if pw > 0.02:
            lay = self.layer
            lay.fill((0, 0, 0, 0))
            cx, cy = W / 2, H / 2
            for i in range(80):
                a = self.rng.uniform(0, math.tau)
                r0 = self.rng.uniform(380, 720)
                r1 = r0 + self.rng.uniform(250, 900)
                wd = self.rng.uniform(0.004, 0.011)
                pygame.draw.polygon(lay, (255, 255, 255, int(130 * pw)),
                                    [(cx + math.cos(a) * r0, cy + math.sin(a) * r0),
                                     (cx + math.cos(a - wd) * r1, cy + math.sin(a - wd) * r1),
                                     (cx + math.cos(a + wd) * r1, cy + math.sin(a + wd) * r1)])
            out.blit(lay, (0, 0))
        if self.vig > 0:
            v = self.vignette
            if self.vig < 1.0:
                v = v.copy()
                v.set_alpha(int(255 * self.vig))
            out.blit(v, (0, 0))
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
            if t0 <= t < t0 + 0.15 and s >= 0.1:
                ca = max(ca, int(s * 40 * (1 - (t - t0) / 0.15)))
        if gl > 0:
            ca = max(ca, int(10 * gl))
            for _ in range(int(2 + 5 * gl)):
                y = self.rng.randrange(0, H - 40)
                hh = min(self.rng.randrange(8, 60), H - y)
                dx = self.rng.randrange(-50, 50)
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
    # SAHNELER
    # ==================================================================
    def _s_dark(self, st, dt, first, dur):
        self.sh.display.canvas.fill((0, 0, 0))
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
            k = 0.25 + 0.75 * ease_in_out(st / dur)
            pul = 0.7 + 0.3 * math.sin(t * 9) * math.sin(t * 2.3)
            glow = pygame.Surface((W // 8, H // 8), pygame.SRCALPHA)
            for r in range(60, 0, -4):
                a = int(10 * k * pul * (1 - r / 60) * 3)
                pygame.draw.ellipse(glow, (255, 50, 20, a),
                                    pygame.Rect(W // 16 - r * 2, H // 8 - r, r * 4, r * 2))
            out.blit(pygame.transform.smoothscale(glow, (W, H)), (0, 0))
            self.particles(out, "embers", n=int(30 + 70 * k), alpha=k)
            rnd = random.Random(5)
            for i in range(14):
                t_on = 0.3 + i * 0.2
                ex, ey = rnd.uniform(160, W - 160), rnd.uniform(140, H - 260)
                if t < t_on or math.sin((t - t_on) * 3 + i) <= -0.85:
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
            self.punch(0.18)
            self.speed(0.4, 0.8)
            self.pilot.force_dash = True
            self.sfx("impact_big", 0.9)
            self.sfx("whoosh", 0.7)
        if self.at(st, 1.0):
            self.bonk(1.2)
        if self.at(st, 2.5):
            self.bonk(1.0)
        self.play(dt)
        self.grade = ((225, 200, 200), (10, 0, 0))

        def draw(out):
            self.title(out, "HAYATTA KALABİLECEK", W / 2, H / 2 - 70, 118, self.t - st + 1.0, None,
                       grad=(WHITE, (255, 200, 170)), stroke=8, glow=(160, 20, 10))
            self.title(out, "MİSİN?", W / 2, H / 2 + 70, 150, self.t - st + 1.5, None,
                       grad=((255, 120, 90), (220, 20, 20)), stroke=8, glow=(200, 20, 10))
        self.ov(draw)
        if self.at(st, 1.5):
            self.punch(0.05)
            self.sfx("impact", 0.5)

    # ------------------------------------------------------------------
    # KAYIT OL -> ANA MENÜ -> HARİTA SEÇ
    REG_FIELDS = (("user", PLAYER, (640, 284), 0.6, 1.5),
                  ("password", "evolve2026", (640, 334), 1.9, 2.8),
                  ("email", "kanka@evolvearena.com", (640, 390), 3.1, 4.2))
    REG_BTN = (640, 450)

    def _s_register(self, st, dt, first, dur):
        sh = self.sh
        if first:
            sh.account.account = None
            sh.state = K.STATE_LOGIN
            try:
                sh._login_set_mode("up")
            except Exception:
                sh.login_mode = "up"
            for k in sh.login_fields:
                sh.login_fields[k] = ""
            self.flash(0.3, power=0.8)
            self.sfx("whoosh_down", 0.6)
        keys = [(0.0, (900, 620))]
        for _f, _txt, pos, a, b in self.REG_FIELDS:
            keys += [(a - 0.35, pos), (b, pos)]
        keys += [(4.6, self.REG_BTN), (5.2, self.REG_BTN), (6.0, (980, 300))]
        m = lerp_path(keys, st)
        for fld, txt, pos, a, b in self.REG_FIELDS:
            if self.at(st, a - 0.2):
                self.tap(pos, 0.4)
            if a <= st:
                sh.login_focus = fld if st < b + 0.2 else sh.login_focus
                n = int(len(txt) * min(1.0, (st - a) / (b - a)))
                if len(sh.login_fields[fld]) != n:
                    sh.login_fields[fld] = txt[:n]
                    self.sfx("click", 0.18)
        if self.at(st, 4.7):
            self.tap(self.REG_BTN, 0.8)
        if self.at(st, 5.0):
            sh.account.sign_in(PLAYER, self.REG_FIELDS[2][1])
            sh.state = K.STATE_MENU
            self.flash(0.2, col=(170, 255, 190), power=0.7)
            self.sfx("levelup", 0.6)
            self.sfx("shing", 0.5)
        if sh.state == K.STATE_LOGIN:
            sh.update_login(dt, m, False)
        else:
            sh.update_menu(dt, m, False)
        self.ui_cursor(m)

        def draw(out):
            self.title(out, "HESABINI AÇ.", W / 2, 62, 76, self.t - st + 0.2, self.t - st + 5.0,
                       grad=(WHITE, (150, 230, 255)), stroke=6, glow=(40, 120, 255), slam=0.3)
            if st >= 5.0:
                self.title(out, "HESAP AÇILDI!", W / 2, H / 2, 110, self.t - st + 5.0, None,
                           grad=((220, 255, 220), (90, 220, 120)), stroke=8, glow=(40, 180, 80),
                           slam=0.8)
        self.ov(draw)

    MENU_PLAY = (640, 334)

    def _s_menu(self, st, dt, first, dur):
        sh = self.sh
        if first:
            sh.state = K.STATE_MENU
        m = lerp_path([(0.0, (980, 300)), (0.8, (810, 402)), (1.5, (810, 402)), (2.1, (1108, 402)),
                       (2.6, (1108, 402)), (3.2, self.MENU_PLAY), (4.0, self.MENU_PLAY)], st)
        if self.at(st, 3.45):
            self.tap(self.MENU_PLAY, 0.8)
            self.punch(0.03)
        sh.update_menu(dt, m, False)
        self.ui_cursor(m)
        self.ov(lambda out: self.band(out, "HOŞ GELDİN, KANKA.", self.t - st + 0.2, self.t - st + 3.4,
                                      col=(255, 214, 120)))

    MAP_CARDS = {"stone": (180, 470), "frost": (490, 470), "jungle": (795, 470), "desert": (1105, 470)}
    MAP_START = (820, 660)

    def _s_mapsel(self, st, dt, first, dur):
        sh = self.sh
        if first:
            sh.state = K.STATE_MAP_SELECT
            self.flash(0.12, power=0.5)
            self.sfx("whoosh", 0.5)
        mc = self.MAP_CARDS
        m = lerp_path([(0.0, self.MENU_PLAY), (0.5, mc["stone"]), (0.9, mc["frost"]), (1.3, mc["jungle"]),
                       (1.7, mc["desert"]), (2.2, self.MAP_START), (3.5, self.MAP_START)], st)
        for x in (0.5, 0.9, 1.3, 1.7):
            if self.at(st, x):
                self.sfx("click", 0.25)
        if self.at(st, 2.9):
            self.tap(self.MAP_START, 0.8)
        sh.update_map_select(dt, m, False)
        self.ui_cursor(m)
        self.ov(lambda out: self.title(out, "4 DÜNYA", 1700, 120, 64, self.t - st + 0.5, None,
                                       grad=(WHITE, GOLD), stroke=6, slam=0.3))

    # ------------------------------------------------------------------
    # NORMAL OYNANIŞ
    def _s_play(self, st, dt, first, dur):
        if first:
            self.make_run(3, {"axe": 4, "whip": 3}, 7, 18, ring=14, rmin=200, rmax=420,
                          prewarm=0.1, announce=True)
            self.flash(0.3, power=0.8)
            self.sfx("impact", 0.6)
        self.pilot.crowd = int(18 + st * 4)
        if self.at(st, 3.0):
            self.pilot.force_dash = True
            self.speed(0.3, 0.7)
            self.sfx("whoosh", 0.8)
        for x in (5.0, 7.0):
            if self.at(st, x):
                self.ring(self.sh.run, 10, 90, 200)
                self.bonk(1.0)
        self.play(dt)
        self.ov(lambda out: (
            self.keycap(out, "W A S D", "KOŞ", 70, 760, self.t - st + 0.4, self.t - st + dur),
            self.keycap(out, "SHIFT", "DASH", 70, 850, self.t - st + 2.8, self.t - st + dur),
            self.keycap(out, "SPACE", "BONK!", 70, 940, self.t - st + 4.8, self.t - st + dur,
                        col=(255, 150, 90))))

    def _s_market(self, st, dt, first, dur):
        sh = self.sh
        if first:
            run = sh.run
            run.gold_wallet = max(run.gold_wallet, 900)
            run.open_shop()
            sh.state = K.STATE_RUN_SHOP
            self.flash(0.15, col=(255, 220, 140), power=0.7)
            self.sfx("shing", 0.5)
        m = lerp_path([(0.0, (640, 600)), (0.8, (420, 250)), (1.5, (420, 250))], st)
        if sh.state == K.STATE_RUN_SHOP:
            sh.update_run_shop(dt, m, False)
            self.cursor(m)
        else:
            self.play(dt)
        self.ov(lambda out: self.keycap(out, "B", "MARKET", 70, 940, self.t - st, self.t - st + dur,
                                        col=GOLD))

    def _s_survive(self, st, dt, first, dur):
        if first:
            self.make_run(10, {"axe": 8, "whip": 8, "tornado": 6, "pentagram": 6}, 22, 46,
                          books={"r_dmg": (4, 2)}, ring=30, prewarm=0.3)
            self.flash(0.15, power=0.6)
            self.sfx("whoosh", 0.6)
        self.play(dt)
        words = (("KOŞ.", 0.0, -230, (WHITE, (200, 230, 255))), ("VUR.", 0.5, -40, (WHITE, (255, 190, 150))),
                 ("HAYATTA KAL.", 1.0, 170, ((255, 240, 180), (255, 160, 40))))
        for _w, x, _y, _g in words:
            if self.at(st, x):
                self.punch(0.05)
                self.sfx("impact", 0.55)
        if self.at(st, 1.0):
            self.bonk(1.0)

        def draw(out):
            dim = pygame.Surface((W, H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, int(95 * min(1.0, st / 0.2))))
            out.blit(dim, (0, 0))
            for wd, x, y, g in words:
                self.title(out, wd, W / 2, H / 2 + y, 190 if wd != "HAYATTA KAL." else 170,
                           self.t - st + x, None, grad=g, stroke=9, glow=(255, 140, 40), slam=0.8)
        self.ov(draw)

    # ------------------------------------------------------------------
    # SİLAHLIK -> DETAY -> EVRİMİ İZLE
    CODEX_AXE = (170, 200)
    EVO_WATCH = (620, 616)
    TIER_CARDS = {1: (1043, 263), 2: (1043, 375), 3: (1043, 487)}

    def _s_codex(self, st, dt, first, dur):
        sh = self.sh
        if first:
            sh.state = K.STATE_WEAPON_CODEX
            sh.weapon_detail = None
            sh.weapon_filter = "all"
            sh.weapon_scroll = 0.0
            self.flash(0.25, col=(255, 230, 190), power=0.8)
            self.sfx("whoosh_down", 0.7)
            self.sfx("impact", 0.4)
        # liste aşağı kayıp geri gelir (20 silahın hepsi görünsün)
        if st < 1.2:
            sc = 0.0
        elif st < 2.6:
            sc = 420 * ease_in_out((st - 1.2) / 1.4)
        elif st < 3.6:
            sc = 420 * (1 - ease_in_out((st - 2.6) / 1.0))
        else:
            sc = 0.0
        sh.weapon_scroll = sc
        if hasattr(sh, "weapon_scroll_target"):
            sh.weapon_scroll_target = sc
        m = lerp_path([(0.0, (900, 600)), (1.0, (760, 330)), (2.6, (1060, 480)), (3.6, (560, 230)),
                       (4.4, self.CODEX_AXE), (5.0, self.CODEX_AXE)], st)
        if self.at(st, 4.6):
            self.tap(self.CODEX_AXE, 0.8)
            sh.weapon_detail = EVO_KEY
            sh.weapon_detail_t = 0.0
        sh.update_weapon_codex(dt, m, False, 0)
        self.ui_cursor(m)
        n = len(K.WEAPON_BY_KEY)
        self.ov(lambda out: self.band(out, f"{n} SİLAH. HER BİRİNİN 3 EVRİMİ VAR.",
                                      self.t - st + 0.3, self.t - st + 4.5, col=(255, 190, 120)))

    def _s_wdetail(self, st, dt, first, dur):
        sh = self.sh
        if first:
            sh.weapon_detail = EVO_KEY
        m = lerp_path([(0.0, self.CODEX_AXE), (0.7, (820, 560)), (1.4, (900, 600)), (2.0, (840, 640)),
                       (2.8, self.EVO_WATCH), (3.5, self.EVO_WATCH)], st)
        if self.at(st, 3.1):
            self.tap(self.EVO_WATCH, 0.8)
        sh.update_weapon_codex(dt, m, False, 0)
        self.ui_cursor(m)
        bk = K.BOOK_BY_KEY[K.EVOLUTIONS[EVO_KEY][0]]
        self.ov(lambda out: self.band(out, "SİLAH LV.10 + EŞ KİTAP LV.3 = EVRİM",
                                      self.t - st + 0.3, self.t - st + dur, col=(255, 150, 120),
                                      sub=f"{K.w_name(K.WEAPON_BY_KEY[EVO_KEY])} + {K.bk_name(bk).upper()}"))

    def _s_evopv(self, st, dt, first, dur):
        sh = self.sh
        if first:
            sh.evo_pv = K.EvoPreview(sh, EVO_KEY)
            sh.evo_pv.select(1)
            self.flash(0.2, col=(255, 200, 180), power=0.6)
            self.sfx("shing", 0.7)
        pv = sh.evo_pv
        tiers = ((0.0, 1), (2.1, 2), (4.2, 3))
        m = lerp_path([(0.0, self.EVO_WATCH), (0.4, self.TIER_CARDS[1]), (1.6, self.TIER_CARDS[1]),
                       (2.0, self.TIER_CARDS[2]), (3.7, self.TIER_CARDS[2]), (4.1, self.TIER_CARDS[3]),
                       (6.5, self.TIER_CARDS[3])], st)
        for x, tier in tiers[1:]:
            if self.at(st, x):
                self.tap(self.TIER_CARDS[tier], 0.7)
                pv.select(tier)
                self.punch(0.03)
                self.sfx("levelup", 0.5)
        sh.update_weapon_codex(dt, m, False, 0)
        self.ui_cursor(m)
        cur = pv.tier

        def draw(out):
            roman = K.EVO_ROMAN[cur]
            nm = K.evo_name(EVO_KEY, cur)
            col = tuple(K.evo_color(EVO_KEY, cur))
            t0 = self.t - st + [x for x, tr in tiers if tr == cur][0] + 0.1
            self.band(out, f"EVRİM {roman}: {nm}", t0, self.t - st + dur, col=col,
                      sub=f"SİLAH LV.{K.evo_level_need(EVO_KEY, cur)}  +  KİTAP LV.{K.evo_book_need(EVO_KEY, cur)}")
        self.ov(draw)
        if st > dur - 1.5 / FPS:
            sh.close_evo_viewer()
            sh.weapon_detail = None

    # ------------------------------------------------------------------
    # OYUNDA EVRİMLEŞEN SİLAHLAR
    def _s_arsenal(self, st, dt, first, dur):
        i = min(len(ARSENAL) - 1, int(st / ARSENAL_DUR))
        lt = st - i * ARSENAL_DUR
        key, tier = ARSENAL[i]
        w = K.WEAPON_BY_KEY[key]
        book = K.EVOLUTIONS[key][0]
        if i != self.item_i:
            self.item_i = i
            lvl = K.evo_level_need(key, tier)
            run = self.make_run(12, {key: lvl}, 26, 44, books={book: (K.evo_book_need(key, tier), 1)},
                                ring=34, rmin=110, rmax=340, prewarm=0.3)
            p = run.player
            while K.evo_tier(p, key) < tier - 1:
                run.evolve_weapon(key)
            run.evo_banner = None
            run.fx.texts.clear()
            self.flash(0.12, power=0.6)
            self.sfx("whoosh", 0.7)
        run = self.sh.run
        if self.at(st, i * ARSENAL_DUR + 0.3):
            run.evolve_weapon(key)
            self.punch(0.04)
            self.sfx("shing", 0.6)
        self.play(dt)
        evolved = lt >= 0.3
        col = tuple(K.evo_color(key, tier)) if evolved else tuple(w["color"])

        def draw(out):
            k = ease_out(lt / 0.2)
            x0 = int(-860 + 900 * k)
            y0 = 790
            box = pygame.Surface((960, 170), pygame.SRCALPHA)
            box.fill((10, 8, 18, 215))
            pygame.draw.rect(box, col + (255,), pygame.Rect(0, 0, 12, 170))
            out.blit(box, (x0, y0))
            K.draw_weapon_emblem(out, x0 + 100, y0 + 85, 130, w, self.t, locked=False, glow=True)
            if not evolved:
                img = self.T.render(K.w_name(w), 72, col, "black", 6, grad=(WHITE, col))
                out.blit(img, (x0 + 190, y0 + 30))
            else:
                a = self.T.render(K.w_name(w) + "  →", 34, (220, 214, 232), "heavy", 3)
                out.blit(a, (x0 + 196, y0 + 14))
                img = self.T.render(K.evo_name(key, tier), 70, col, "black", 6,
                                    grad=((255, 255, 240), col), glow=col)
                out.blit(img, (x0 + 150, y0 + 6))
                tag = self.T.render(f"EVRİM {K.EVO_ROMAN[tier]}", 34, col, "black", 4)
                out.blit(tag, (x0 + 196, y0 + 120))
            ctr = self.T.render(f"{i + 1:02d}/{len(ARSENAL):02d}", 36, (200, 190, 220), "heavy", 3)
            out.blit(ctr, (W - ctr.get_width() - 60, H - 90))
            if st < 1.45:
                self.title(out, "EVRİMLER OYUNDA", W / 2, 620, 110, self.t - st + 0.05,
                           self.t - st + 1.45, grad=(WHITE, (255, 190, 120)), stroke=8,
                           glow=(255, 120, 40))
        self.ov(draw)

    # ------------------------------------------------------------------
    # KİTAP + SİLAH = EVRİM
    def _s_evologic(self, st, dt, first, dur):
        c = self.sh.display.canvas
        self.bg(c, (36, 22, 40), (8, 5, 12), "evologic")
        self.rays(c, VW / 2, 150, self.t, col=(255, 200, 150), alpha=16)
        self.vig = 1.0
        if first:
            self.flash(0.25, col=(200, 160, 255), power=0.8)
            self.sfx("whoosh_down", 0.7)
        w = K.WEAPON_BY_KEY[EVO_KEY]
        bk = K.BOOK_BY_KEY[K.EVOLUTIONS[EVO_KEY][0]]
        tier_now = 1 + min(2, int(max(0.0, st - 0.6) / 0.9))
        ecol = tuple(K.evo_color(EVO_KEY, tier_now))
        k1 = ease_out(st / 0.35)
        cy = 190
        K.add_glow(c, 330, cy, 150, tuple(w["color"]), 0.3)
        K.draw_weapon_emblem(c, 330, cy + (1 - k1) * 200, 150, w, self.t, locked=False, glow=True)
        K.add_glow(c, 640, cy, 150, (196, 150, 255), 0.3)
        K.draw_book(c, 640, cy + (1 - k1) * 200, 150, bk, self.t, locked=False, glow=True)
        evw = dict(w)
        evw["color"] = ecol
        K.add_glow(c, 950, cy, 170 + 20 * math.sin(self.t * 6), ecol, 0.45)
        K.draw_weapon_emblem(c, 950, cy + (1 - k1) * 200, 160, evw, self.t, locked=False, glow=True)
        for i in range(1, 4):
            t_in = 0.6 + (i - 1) * 0.9
            if self.at(st, t_in):
                self.sfx("levelup", 0.5)
                self.punch(0.03)

        def draw(out):
            self.title(out, "KİTAPLAR SİLAHINI EVRİMLEŞTİRİR", W / 2, 60, 66, self.t - st + 0.05, None,
                       grad=((235, 220, 255), (170, 120, 255)), stroke=6, glow=(120, 60, 255), slam=0.3)
            for sx, txt in ((485, "+"), (795, "=")):
                img = self.T.render(txt, 120, GOLD, "black", 8, glow=(255, 160, 40))
                out.blit(img, (sx * S - img.get_width() / 2, cy * S - img.get_height() / 2))
            for x, nm in ((330, K.w_name(w)), (640, K.bk_name(bk).upper()),
                          (950, K.evo_name(EVO_KEY, tier_now))):
                img = self.T.render(nm, 34, WHITE if x != 950 else ecol, "heavy", 4)
                out.blit(img, (x * S - img.get_width() / 2, (cy + 110) * S))
            for i in range(1, 4):
                t_in = 0.6 + (i - 1) * 0.9
                lt = st - t_in
                if lt < 0:
                    continue
                k = ease_out(lt / 0.25)
                col = tuple(K.evo_color(EVO_KEY, i))
                y = 560 + (i - 1) * 140
                x0 = int(260 - (1 - k) * 600)
                row = pygame.Surface((1400, 116), pygame.SRCALPHA)
                row.fill((14, 10, 22, 225))
                pygame.draw.rect(row, col + (255,), pygame.Rect(0, 0, 14, 116))
                pygame.draw.rect(row, col + (255,), row.get_rect(), width=3, border_radius=4)
                out.blit(row, (x0, y))
                rn = self.T.render(K.EVO_ROMAN[i], 74, col, "black", 5, grad=(WHITE, col))
                out.blit(rn, (x0 + 40, y + 58 - rn.get_height() / 2))
                req = self.T.render(f"SİLAH LV.{K.evo_level_need(EVO_KEY, i)}  +  KİTAP LV.{K.evo_book_need(EVO_KEY, i)}",
                                    44, WHITE, "heavy", 4)
                out.blit(req, (x0 + 170, y + 58 - req.get_height() / 2))
                nm = self.T.render("→  " + K.evo_name(EVO_KEY, i), 52, col, "black", 5,
                                   grad=((255, 255, 240), col))
                out.blit(nm, (x0 + 1380 - nm.get_width(), y + 58 - nm.get_height() / 2))
        self.ov(draw)

    def _s_evocard(self, st, dt, first, dur):
        sh = self.sh
        if first:
            run = self.make_run(9, {EVO_KEY: K.evo_level_need(EVO_KEY, 1), "whip": 8, "tornado": 7},
                                20, 30, books={K.EVOLUTIONS[EVO_KEY][0]: (K.evo_book_need(EVO_KEY, 1), 1),
                                               "r_dmg": (3, 1)}, ring=20, prewarm=0.3)
            p = run.player
            try:
                o_w = run._weapon_offer(K.WEAPON_BY_KEY["whip"], p.weapons["whip"] + 1, False)
                o_e = run.evo_offer(EVO_KEY)
                o_b = run._book_offer(K.BOOK_BY_KEY["r_aspd"], 1, True)
                run.levelup_choices = [o_w, o_e, o_b]
                run.pending_levelups = 1
                sh.state = K.STATE_LEVELUP
            except Exception:
                sh.state = K.STATE_PLAY
            self.flash(0.15, power=0.6)
            self.sfx("levelup", 0.9)
        run = sh.run
        hit = EVO_HIT - (self.t - st)               # sahne içindeki tıklama anı
        if sh.state == K.STATE_LEVELUP:
            cards = [r.center for (r, _c, _i) in sh.levelup_ui.cards] or [(342, 352), (640, 352), (938, 352)]
            cards = (cards + [cards[-1]] * 3)[:3]
            m = lerp_path([(0.0, (640, 690)), (0.6, cards[0]), (1.1, cards[0]), (1.6, cards[1]),
                           (3.0, cards[1])], st)
            clicked = self.at(st, hit)
            if clicked:
                self.tap(m, 0.9)
            sh.update_levelup(dt, m, clicked)
            self.cursor(m)
        else:
            self.play(dt)
        if self.at(st, hit):
            if EVO_KEY not in run.player.evolved:
                run.evolve_weapon(EVO_KEY)
            sh.state = K.STATE_PLAY
            run.pending_levelups = 0
            self.flash(0.6, power=1.3)
            self.punch(0.12)
            self.shake(18, 0.5)
            self.speed(0.6, 1.0)
        self.ov(lambda out: (self.band(out, "SEVİYE ATLA  →  EVRİM KARTI", self.t - st + 0.3,
                                       self.t - st + hit, col=(255, 120, 90)),
                             self.title(out, "EVRİM!", W / 2, 300, 200, self.t - st + hit + 0.05, None,
                                        grad=((255, 255, 230), (255, 160, 30)), stroke=10,
                                        scol=(70, 30, 0), glow=(255, 200, 80), slam=1.0)))

    def _s_power(self, st, dt, first, dur):
        run = self.sh.run
        if first:
            p = run.player
            p.weapons.update({"tesla": 20, "beam": 20, "pentagram": 18})
            for k in ("tesla", "beam", "pentagram"):
                p.weapon_timers[k] = 0.0
            for bk, lv in (("r_echo", 1), ("r_xp", 5)):
                for _ in range(lv):
                    p.take_book(bk, 1)
            self.pilot.crowd = 60
            self.ring(run, 30)
        for x, key, tier in ((1.0, "tesla", 2), (2.5, "beam", 2)):
            if self.at(st, x):
                self.evolve(run, key, tier)
                self.punch(0.04)
                self.sfx("shing", 0.6)
        if self.at(st, 3.5):
            self.bonk(1.0)
        self.play(dt)

        def draw(out):
            self.title(out, "SİLAHINI EVRİMLEŞTİR.", W / 2, 300, 110, self.t - st + 0.3, None,
                       grad=(WHITE, (255, 210, 130)), stroke=9, glow=(255, 130, 30))
            self.title(out, "GÜCÜNÜ KATLA.", W / 2, 440, 140, self.t - st + 1.5, None,
                       grad=((255, 236, 160), (255, 120, 20)), stroke=10, glow=(255, 110, 20))
        if self.at(st, 1.5):
            self.sfx("impact", 0.6)
        self.ov(draw)

    # ------------------------------------------------------------------
    # DÜNYALAR — kamera yalnız patron gelişinde yaklaşır
    def _world(self, theme, st, dt, first, dur):
        wd = WORLDS[theme]
        if first:
            self.make_run(12, {"tesla": 10, "tornado": 8, "beam": 10, "pentagram": 10}, 30, 46,
                          theme=theme, books={"r_dmg": (6, 2)}, ring=34, prewarm=0.2)
            self.sfx("whoosh", 0.8)
        run = self.sh.run
        if self.at(st, 1.0):
            self.add_boss(run, wd["bosses"][0], -230, -150, theme=theme)
            self.add_boss(run, wd["bosses"][1], 230, -130, theme=theme)
            self.punch(0.06)
            self.shake(14, 0.4)
            self.sfx("growl", 0.7)
            self.sfx("impact", 0.6)
        self.wipe = (st / 0.32, wd["col"])
        self.play(dt)
        self.boss_zoom(run, st, t_in=1.0, hold=1.2)
        self.grade = wd["grade"]
        part = {"frost": "snow", "jungle": "leaves", "desert": "dust"}[theme]
        names = [K.MAP_BOSS_NAMES[theme][b] for b in wd["bosses"]]
        wname = K.L("map.%s.name" % theme)

        def draw(out):
            self.particles(out, part, n=110 if part != "dust" else 60)
            self.title(out, wname, W / 2, 330, 130, self.t - st + 0.15, self.t - st + 1.1,
                       grad=(WHITE, wd["col"]), stroke=9, glow=tuple(int(v * 0.7) for v in wd["col"]))
            self.title(out, wd["mobs"], W / 2, 440, 44, self.t - st + 0.35, self.t - st + 1.1,
                       color=(236, 236, 244), stroke=4, style="heavy", slam=0.2)
            self.title(out, "PATRON: " + "  /  ".join(names), W / 2, 820, 64, self.t - st + 1.1,
                       self.t - st + 2.9, grad=((255, 220, 200), (255, 80, 60)), stroke=6, slam=0.4)
            self.band(out, "3 FARKLI DÜNYA. HER BİRİ KENDİ CANAVARLARIYLA.", self.t - st,
                      self.t - st + dur + 0.01, col=wd["col"], size=54)
        self.ov(draw)

    def _s_frost(self, st, dt, first, dur):
        self._world("frost", st, dt, first, dur)

    def _s_jungle(self, st, dt, first, dur):
        self._world("jungle", st, dt, first, dur)

    def _s_desert(self, st, dt, first, dur):
        self._world("desert", st, dt, first, dur)

    # ------------------------------------------------------------------
    # CEHENNEM
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
        self.play(dt)
        self.grade = ((205, 140, 140), (14, 0, 0))
        self.vig = 1.0
        blink = int(self.t * 6) % 2 == 0

        def draw(out):
            for yy in (0, H - 56):
                band = pygame.Surface((W, 56), pygame.SRCALPHA)
                band.fill((0, 0, 0, 220))
                off = int(self.t * 160) % 80
                for x in range(-80, W + 80, 80):
                    pygame.draw.polygon(band, (220, 30, 20, 230), [(x + off, 0), (x + off + 40, 0),
                                                                   (x + off + 10, 56), (x + off - 30, 56)])
                out.blit(band, (0, yy))
            if blink or st < 0.4:
                self.title(out, "UYARI", W / 2, 200, 70, self.t - st + 0.05, None,
                           color=(255, 70, 50), stroke=6, slam=0.2)
            self.title(out, "25. DALGADA", W / 2, H / 2 + 140, 96, self.t - st + 0.2, None,
                       grad=(WHITE, (255, 170, 150)), stroke=8, glow=(160, 10, 0), slam=0.3)
            self.title(out, "CEHENNEM KAPISI AÇILIR...", W / 2, H / 2 + 260, 104, self.t - st + 0.7,
                       None, grad=((255, 200, 180), (255, 40, 20)), stroke=8, glow=(200, 20, 0),
                       slam=0.3, flicker=st > 2.0)
        self.ov(draw)
        if self.at(st, 2.2):
            self.glitch(0.25)
            self.sfx("glitch", 0.6)

    def _s_hellord(self, st, dt, first, dur):
        if first:
            run = self.make_run(K.HELL_PORTAL_WAVE + 3, {"tesla": 14, "tornado": 12, "beam": 14,
                                                         "pentagram": 14, "meteor": 10}, 50, 40,
                                books={"r_dmg": (10, 3)}, hell=True, ring=30, prewarm=0.2)
            self.add_boss(run, "warlord", 0, -170, hellish=True)
            self.flash(0.5, col=(255, 90, 40), power=1.2)
            self.punch(0.12)
            self.shake(22, 0.6)
            self.sfx("growl", 1.0)
        run = self.sh.run
        if self.at(st, 2.6):
            self.bonk(1.0)
        self.play(dt)
        self.boss_zoom(run, st, t_in=0.0, hold=1.0, z=1.5)
        self.grade = ((255, 165, 135), (20, 0, 0))
        self.vig = 1.0

        def draw(out):
            self.particles(out, "embers", n=130)
            self.title(out, "CEHENNEM LORDU", W / 2, 180, 140, self.t - st + 0.1, None,
                       grad=((255, 220, 180), (255, 50, 20)), stroke=10, scol=(30, 0, 0),
                       glow=(220, 30, 0), slam=0.6)
            if st > 1.9:
                self.title(out, "EVRİMSİZ GİRME.", W / 2, 930, 130, self.t - st + 1.9, None,
                           grad=(WHITE, (255, 80, 50)), stroke=10, scol=(30, 0, 0), glow=(220, 30, 0))
        if self.at(st, 1.9):
            self.punch(0.06)
            self.sfx("impact", 0.8)
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
            self.punch(0.1)
            self.shake(24, 0.7)
            self.sfx("impact_big", 0.9)
        if self.at(st, 2.8):
            self.bonk(1.0)
        self.play(dt)
        if st >= 0.8:
            alive = [b for b in run.bosses if b.alive and b.kind == "dragon"]
            if alive:
                b = alive[0]
                q = st - 0.8
                k = ease_out(q / 0.35) if q < 0.35 else (1.0 if q < 1.5 else
                                                          1.0 - ease_in_out((q - 1.5) / 0.5))
                if k > 0:
                    qx, qy = run.world_to_screen(b.x, b.y)
                    self.zoom = 1.0 + 0.5 * k
                    self.focus = (VW / 2 + (qx - VW / 2) * k, VH / 2 + (qy - VH / 2) * k)
        self.grade = ((255, 165, 135), (20, 0, 0))
        self.vig = 1.0

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
            self.particles(out, "embers", n=150)
            if st > 0.8:
                self.title(out, "KOR EJDERHA", W / 2, 180, 150, self.t - st + 0.85, None,
                           grad=((255, 230, 160), (255, 90, 20)), stroke=10, scol=(30, 0, 0),
                           glow=(255, 80, 0), slam=0.7)
            if st > 2.4:
                self.title(out, "EVRİMSİZ GİRME.", W / 2, 930, 130, self.t - st + 2.4, None,
                           grad=(WHITE, (255, 80, 50)), stroke=10, scol=(30, 0, 0),
                           glow=(220, 30, 0), flicker=st > 3.3)
        self.ov(draw)

    # ------------------------------------------------------------------
    def _s_crit(self, st, dt, first, dur):
        if first:
            self.make_run(14, {"knives": 12, "tesla": 10, "axe": 10}, 34, 50,
                          books={"r_crit": (12, 4), "r_critd": (10, 4), "r_luck": (8, 3)},
                          ring=40, prewarm=0.3)
            self.flash(0.35, col=(255, 240, 160), power=1.0)
        self.play(dt)
        self.grade = ((255, 248, 222), (8, 6, 0))
        pops = [0.25, 0.75, 1.25, 1.5, 1.75, 2.25, 2.5, 2.75]
        for x in pops:
            if self.at(st, x):
                self.sfx("crit", 0.55)
        icons = (("horseshoe", 1.0, -560), ("dice", 1.5, 0), ("clover", 2.0, 560))
        for _n, x, _dx in icons:
            if self.at(st, x):
                self.sfx("shing", 0.5)

        def draw(out):
            rnd = random.Random(21)
            for j, x in enumerate(pops):
                px, py = rnd.uniform(380, W - 380), rnd.uniform(380, H - 360)
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
                cx, cy = W / 2 + dx, 240
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
            self.title(out, "ŞANSINI DENE.", W / 2, 900, 140, self.t - st + 0.3, None,
                       grad=((200, 255, 200), (90, 220, 110)), stroke=9, scol=(0, 30, 10),
                       glow=(60, 200, 90))
        self.ov(draw)

    # ------------------------------------------------------------------
    # GERÇEK DÜNYA SIRALAMASI EKRANI — oyuncu sıralamada yükselir
    def _rank_rows(self, mine):
        rows = [dict(name=n, score=s, wave=w, kills=k, diff="normal", run_time=1200)
                for n, s, w, k in RIVALS]
        rows.append(dict(name=PLAYER, score=int(mine), wave=44, kills=5320, diff="kabus", run_time=1700))
        rows.sort(key=lambda r: -r["score"])
        return rows

    def _s_ranking(self, st, dt, first, dur):
        sh = self.sh
        if first:
            if not sh.account.logged_in():
                sh.account.sign_in(PLAYER, self.REG_FIELDS[2][1])
            sh.state = K.STATE_WORLD_LB
            self.flash(0.2, col=(160, 200, 255), power=0.7)
            self.sfx("whoosh", 0.8)
            self._prev_rank = None
        q = ease_in_out((st - 0.4) / 2.6)
        mine = 30500 + (168420 - 30500) * q
        rows = self._rank_rows(mine)
        sh.online.world_scores = rows
        rank = [r["name"] for r in rows].index(PLAYER)
        if self._prev_rank is not None and rank < self._prev_rank:
            self.sfx("coin", 0.7)
            if rank == 0:
                self._rank1_t = self.t
                self.sfx("impact", 0.8)
                self.punch(0.05)
                self.flash(0.25, col=(255, 230, 150), power=0.6)
        self._prev_rank = rank
        m = (1100 + math.sin(st) * 40, 600)
        sh.update_world_leaderboard(dt, m, False)
        if rank == 0:                          # konfeti
            c = sh.display.canvas
            lt = self.t - getattr(self, "_rank1_t", self.t)
            for i in range(70):
                x = (i * 97.7 + math.sin(st * 2 + i) * 30) % VW
                y = (lt * (200 + (i % 7) * 40) + i * 23) % (VH + 40) - 20
                colr = ((255, 214, 110), (255, 120, 140), (120, 210, 255), (150, 240, 160))[i % 4]
                pygame.draw.rect(c, colr, pygame.Rect(int(x), int(y), 6, 10))

        def draw(out):
            if rank != 0:
                self.band(out, "DÜNYAYLA YARIŞ.", self.t - st + 0.3, self.t + 1, col=(140, 190, 255))
            else:
                t1 = getattr(self, "_rank1_t", self.t)
                self.band(out, "ZİRVEYE ÇIK.", t1, self.t + 1, col=GOLD)
                self.title(out, "1. SENSİN!", W / 2, H / 2 - 40, 150, t1, t1 + 1.3,
                           grad=((255, 250, 200), (255, 180, 40)), stroke=9, glow=(255, 170, 30),
                           slam=1.0)
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
                z = 1.08 - 0.08 * ease_out(lt / 0.2)
                img = pygame.transform.smoothscale(snap, (int(W * z), int(H * z)))
                out.blit(img, (-(img.get_width() - W) / 2, -(img.get_height() - H) / 2))
            else:
                out.fill((255, 255, 255))
        if first or int(st / 0.2) != int((st - 1.0 / FPS) / 0.2):
            if i < n:
                self.flash(0.08, power=0.7)
                self.sfx("impact" if i % 4 == 0 else "whoosh", 0.35)
        self.ov(draw)
        self.sh.display.canvas.fill((0, 0, 0))

    def _s_logo(self, st, dt, first, dur):
        c = self.sh.display.canvas
        c.fill((0, 0, 0))
        self.vig = 1.0
        if first:
            self.sfx("whoosh_down", 0.7)
        if self.at(st, 0.3):
            self.punch(0.08)
            self.shake(14, 0.4)
            self.sfx("impact", 0.7)
            self.flash(0.2, col=(255, 220, 160), power=0.8)
        hit = FINAL_HIT - (self.t - st)
        if self.at(st, hit):
            self.punch(0.12)
            self.shake(24, 0.5)
            self.flash(0.3, power=1.0)
        if st > 0.3:
            k = ease_out((st - 0.3) / 0.6)
            self.rays(c, VW / 2, VH / 2 - 70, self.t, col=(170, 120, 255), alpha=int(30 * k))
            K.add_glow(c, VW / 2, VH / 2 - 70, 520, (150, 90, 230), 0.35 * k)

        def draw(out):
            self.particles(out, "embers", n=80)
            if st >= 0.3:
                k = ease_out((st - 0.3) / 0.25)
                sc = 1.0 + 0.5 * (1 - k)
                logo = K.brand_scaled("logo", w=int(1250 * sc))
                if logo is not None:
                    img = logo.copy()
                    img.set_alpha(int(255 * min(1.0, (st - 0.3) / 0.1)))
                    out.blit(img, (W / 2 - img.get_width() / 2, 430 - img.get_height() / 2))
            if st >= 1.1:
                self.title(out, "ŞİMDİ İNDİR.", W / 2, 820, 110, self.t - st + 1.1, None,
                           color=WHITE, stroke=8, glow=(255, 255, 255), slam=0.4)
            if st >= 1.6:
                self.title(out, "HAYATTA KALABİLECEK MİSİN?", W / 2, 940, 64, self.t - st + 1.6, None,
                           grad=((255, 220, 200), (255, 90, 60)), stroke=6, slam=0.3)
            fade = max(0.0, (st - (dur - 0.4)) / 0.4)
            if fade > 0:
                blk = pygame.Surface((W, H))
                blk.fill((0, 0, 0))
                blk.set_alpha(int(255 * min(1.0, fade)))
                out.blit(blk, (0, 0))
        self.ov(draw)


# =====================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", default=GAME, help="oyun dosyası (kasma_arena13.py, EvolveArena sürümü)")
    ap.add_argument("-o", "--out", default=os.path.join(ROOT, "trailer", "evolve_arena_trailer.mp4"))
    ap.add_argument("--stills", default="", help="virgülle saniyeler: yalnız PNG kareler yaz")
    ap.add_argument("--from", dest="t_from", type=float, default=0.0)
    ap.add_argument("--to", dest="t_to", type=float, default=LENGTH)
    ap.add_argument("--bitrate", default="4200k", help="H.264 hedef bit hızı (dosya < 100 MB kalsın)")
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
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        proc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
             "-b:v", args.bitrate, "-maxrate", "7000k", "-bufsize", "10000k",
             "-pix_fmt", "yuv420p", silent],
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
                print("kare:", p, flush=True)
        if i % (FPS * 5) == 0:
            print(f"  {t:5.1f} sn  [{tr.cur_scene}]  ({time.time() - t0:.0f} sn geçti)", flush=True)
    if not proc:
        return
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg görüntü kodlaması başarısız")
    print("görüntü bitti, ses sentezleniyor...", flush=True)
    wav = os.path.join(_TMP, "audio.wav")
    # ses her zaman tam film zaman çizelgesinde üretilir; parça render'da
    # ilgili aralık -ss ile kesilir (müzik ve kesimler senkron kalsın)
    A.render(list(tr.events), LENGTH, wav, plan=AUDIO_PLAN)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-ss", str(args.t_from),
           "-t", str(t_end - args.t_from), "-i", wav, "-map", "0:v", "-map", "1:a",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
           args.out]
    subprocess.run(cmd, check=True)
    print(f"tamam: {args.out}  ({time.time() - t0:.0f} sn)")


if __name__ == "__main__":
    main()
