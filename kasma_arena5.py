"""
=====================================================================
 KASMA ARENA  —  v3.3
 2D Top-Down Hayatta Kalma / Skor-Rekor Oyunu
 ---------------------------------------------------------------------
 Dalgalar halinde gelen düşmanlara karşı hayatta kal, nişan al, ateş et,
 dash at, BONK'la, dalga aralarında MARKET'ten güç satın al, seviye atla,
 patronları yen, rekorunu kır. Kaybedersen o koşuda aldıkların silinir.
 Elmasla kalıcı SKIN'ler al (her skinin kendi silahı, mermisi, efekti ve
 ÖZEL YETENEĞİ var).

 v3.3 ile gelenler:
   * HARİTA BÜYÜDÜ: dünya artık oyun penceresinin 3x3'ü (üst/alt/sağ/sol ve
     dört çapraz). Kamera oyuncuyu takip eder, dışı çıkılmaz duvardır ve
     sağ üstte küçük harita vardır.
   * CEHENNEM (2. harita): 25. dalga patronu devrilince MOR portal açılır,
     E ile girilir. Cehennemde yaratıklar bambaşkadır; arenanın 25. dalgası
     kadar güçlü ama 1. dalga kadar yavaştır. Markette yalnızca cehennemde
     açılan yeni bir kademe vardır.
   * 25'ten sonra arenaya YENİ PATRON GELMEZ; onun yerine her dalga üstel
     olarak sertleşir ve oyuncuyu portala girmeye zorlar.

 v3.2 ile gelenler:
   * Ana menüdeki GÜNLÜK MARKET kaldırıldı.
   * BAŞARIMLAR yeniden yazıldı: kademe (bronz/gümüş/altın/efsane),
     ilerleme çubuğu, elmas ödülü ve "nasıl kazanılır" penceresi.
   * KİTAPLAR artık hepsi kilitli ve her kitabın BİRDEN FAZLA şartı var;
     güçlü (nadir) kitapların şartları çok daha ağır.
   * Her SKİN'in otomatik çalışan bir ÖZEL YETENEĞİ var. Yetenek
     çalıştığında düşmanlar 0.5 saniye donar; kalan süre ekranın altındaki
     yetenek çubuğunda görünür.

 Kontroller:
   WASD / Ok tuşları   : Hareket
   FARE                 : Nişan al
   SOL TIK (basılı tut) : Ateş et
   SPACE                : BONK! (yakın alan hasarı + geri itme)
   SHIFT / SAĞ TIK      : DASH (kısa süre hasar almazsın)
   B                    : Oyun-içi MARKET (oyunu duraklatır)
   E                    : CEHENNEM KAPISI'ndan geç (portalın yanındayken)
   ESC                  : Duraklat / Geri          F11: Tam ekran
   F3                   : FPS göstergesi

 Çalıştırmak için:
   pip install pygame
   python kasma_arena2.py
=====================================================================
"""

import pygame
import random
import math
import json
import os
import sys
import time
import threading
import colorsys
import urllib.request
import urllib.error
from array import array

# =====================================================================
# ÇEVRİMİÇİ SUNUCU AYARI
# =====================================================================
ONLINE_API_URL = "https://kasma-arena-server.onrender.com"

# =====================================================================
# TEMEL AYARLAR
# =====================================================================
VIRTUAL_W, VIRTUAL_H = 1280, 720
FPS = 60
GAME_TITLE = "ARENA SAVAŞI"
GAME_VERSION = "3.3"


def _base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = _base_dir()
LEGACY_SAVE = os.path.join(BASE_DIR, "kasma_arena_save.json")


def get_save_dir():
    """Kayıt dosyası kullanıcı klasörüne yazılır (PyInstaller/Steam ile uyumlu)."""
    try:
        if os.name == "nt":
            base = os.environ.get("APPDATA") or os.path.expanduser("~")
            d = os.path.join(base, "KasmaArena")
        elif sys.platform == "darwin":
            d = os.path.expanduser("~/Library/Application Support/KasmaArena")
        else:
            root = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
            d = os.path.join(root, "KasmaArena")
        os.makedirs(d, exist_ok=True)
        return d
    except Exception:
        return BASE_DIR


SAVE_FILE = os.path.join(get_save_dir(), "kasma_arena_save.json")

# ---- Renk paleti ---------------------------------------------------
BG_TOP      = (10, 12, 22)
BG_BOTTOM   = (18, 20, 36)
PANEL_BG    = (20, 23, 38)
PANEL_EDGE  = (60, 70, 110)
TEXT        = (232, 234, 244)
TEXT_DIM    = (150, 155, 178)
GOLD        = (232, 186, 90)
GOLD_DIM    = (150, 120, 65)
RED         = (232, 90, 100)
GREEN       = (110, 220, 140)
BLUE        = (100, 160, 240)
PURPLE      = (170, 120, 230)
CYAN        = (100, 220, 220)
ORANGE      = (240, 150, 80)
WHITE       = (255, 255, 255)
BLACK       = (0, 0, 0)
GEM_COLOR   = (120, 210, 255)
OUTLINE     = (10, 10, 16)

# Çalışma zamanı ayarları (SaveManager'dan güncellenir)
# plain_skin: "SADE GÖRÜNÜM". Açıkken oyuncu; kanat, şapka, gözlük, pelerin
# ve tüm skin efektleri olmadan yalnızca skininin renginde sade bir top olarak
# çizilir. Skin'in verdiği bonuslar aynen devam eder — yalnızca görünüm kapanır.
CFG = {"shake": True, "dmg": True, "fps": False, "plain_skin": False}

random.seed()


# =====================================================================
# YARDIMCI FONKSİYONLAR
# =====================================================================

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def dist(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def norm_dir(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy)
    if d < 1e-6:
        return 0.0, 0.0
    return dx / d, dy / d


def ease_out_cubic(t):
    t = clamp(t, 0.0, 1.0)
    return 1 - (1 - t) ** 3


def fmt_time(seconds):
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


def fmt_num(n):
    n = int(n)
    return f"{n:,}".replace(",", ".")


def scale_col(c, k):
    return (int(clamp(c[0] * k, 0, 255)), int(clamp(c[1] * k, 0, 255)), int(clamp(c[2] * k, 0, 255)))


def mix_col(a, b, t):
    return (int(clamp(lerp(a[0], b[0], t), 0, 255)),
            int(clamp(lerp(a[1], b[1], t), 0, 255)),
            int(clamp(lerp(a[2], b[2], t), 0, 255)))


def lighten(c, t):
    return mix_col(c, (255, 255, 255), t)


def hue_col(h, s=0.72, v=1.0, steps=24):
    """Renk döngüsü (önbellek dostu olması için adımlara bölünür)."""
    h = (int(h * steps) % steps) / steps
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def rot(px, py, ang, ox, oy):
    c, s = math.cos(ang), math.sin(ang)
    return (ox + px * c - py * s, oy + px * s + py * c)


def rot_pts(pts, ang, ox, oy):
    return [rot(x, y, ang, ox, oy) for x, y in pts]


def zigzag(x1, y1, x2, y2, segs, amp, rnd=random):
    pts = [(x1, y1)]
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    for i in range(1, segs):
        f = i / segs
        off = rnd.uniform(-amp, amp)
        pts.append((x1 + dx * f + nx * off, y1 + dy * f + ny * off))
    pts.append((x2, y2))
    return pts


# =====================================================================
# FONT / METİN
# =====================================================================
_font_cache = {}
_text_cache = {}


def get_font(size, bold=False):
    size = int(size)
    key = (size, bold)
    f = _font_cache.get(key)
    if f is None:
        try:
            f = pygame.font.SysFont("segoeui,arial,helvetica,sans", size, bold=bold)
        except Exception:
            f = pygame.font.Font(None, size)
        _font_cache[key] = f
    return f


def _render(text, size, bold, color):
    key = (text, size, bold, color)
    img = _text_cache.get(key)
    if img is None:
        if len(_text_cache) > 900:
            _text_cache.clear()
        img = get_font(size, bold).render(text, True, color)
        _text_cache[key] = img
    return img


def draw_text(surf, text, pos, size=20, color=TEXT, bold=False,
              center=False, shadow=True, alpha=255, right=False):
    size = int(size)
    color = (int(color[0]), int(color[1]), int(color[2]))
    alpha = int(clamp(alpha, 0, 255))
    img = _render(text, size, bold, color)
    img.set_alpha(alpha)
    r = img.get_rect()
    px, py = int(pos[0]), int(pos[1])
    if center:
        r.center = (px, py)
    elif right:
        r.topright = (px, py)
    else:
        r.topleft = (px, py)
    if shadow:
        sh = _render(text, size, bold, (0, 0, 0))
        sh.set_alpha(alpha)
        surf.blit(sh, (r.x + 2, r.y + 2))
    surf.blit(img, r)
    return r


def text_width(text, size=20, bold=False):
    return get_font(size, bold).size(text)[0]


def wrap_text(text, size, max_w, bold=False):
    words = text.split(" ")
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if text_width(test, size, bold) > max_w and line:
            lines.append(line)
            line = w
        else:
            line = test
    if line:
        lines.append(line)
    return lines


# =====================================================================
# GLOW / DISK / GÖLGE ÖNBELLEKLERİ  (performans için sprite kullanılır)
# =====================================================================
_glow_cache = {}
_disc_cache = {}
_shadow_cache = {}


def glow_sprite(r, color, level):
    key = (r, color, level)
    s = _glow_cache.get(key)
    if s is None:
        if len(_glow_cache) > 1400:
            _glow_cache.clear()
        s = pygame.Surface((r * 2, r * 2))
        s.fill((0, 0, 0))
        steps = int(min(26, max(5, r // 2 + 3)))
        k = level / 8.0
        for i in range(steps):
            f = i / (steps - 1)
            rad = max(1, int(r * (1 - f * 0.94)))
            inten = (f ** 2.3) * k
            pygame.draw.circle(s, scale_col(color, inten), (r, r), rad)
        _glow_cache[key] = s
    return s


def add_glow(surf, x, y, r, color, k=1.0):
    """Toplamalı (additive) parlama. Yalnızca opak yüzeylere çizilir."""
    level = int(clamp(k, 0.0, 1.0) * 8 + 0.5)
    if level <= 0:
        return
    r = max(2, int(r) // 2 * 2)
    sp = glow_sprite(r, (int(color[0]), int(color[1]), int(color[2])), level)
    surf.blit(sp, (int(x - r), int(y - r)), special_flags=pygame.BLEND_RGB_ADD)


def disc_sprite(r, color, alpha):
    a = int(clamp(alpha, 0, 255)) // 16 * 16
    key = (r, color, a)
    s = _disc_cache.get(key)
    if s is None:
        if len(_disc_cache) > 1400:
            _disc_cache.clear()
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (color[0], color[1], color[2], a), (r, r), r)
        _disc_cache[key] = s
    return s


def blit_disc(surf, x, y, r, color, alpha):
    r = max(1, int(r))
    if r > 14:
        r = r // 4 * 4
    if alpha < 8:
        return
    sp = disc_sprite(r, (int(color[0]), int(color[1]), int(color[2])), alpha)
    surf.blit(sp, (int(x - r), int(y - r)))


def shadow_sprite(w):
    w = max(6, int(w) // 2 * 2)
    s = _shadow_cache.get(w)
    if s is None:
        s = pygame.Surface((w, max(4, w // 3)), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, 95), s.get_rect())
        _shadow_cache[w] = s
    return s


def draw_bar(surf, rect, frac, color, bg=(28, 30, 44), border=PANEL_EDGE, radius=7):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, bg, rect, border_radius=radius)
    frac = clamp(frac, 0.0, 1.0)
    w = int((rect.w - 4) * frac)
    if w > 2:
        inner = pygame.Rect(rect.x + 2, rect.y + 2, w, rect.h - 4)
        pygame.draw.rect(surf, color, inner, border_radius=max(2, radius - 2))
        hl = pygame.Rect(inner.x + 2, inner.y + 1, max(1, inner.w - 4), max(1, inner.h // 3))
        pygame.draw.rect(surf, lighten(color, 0.4), hl, border_radius=3)
    pygame.draw.rect(surf, border, rect, width=2, border_radius=radius)


# =====================================================================
# SES  (tamamen kod ile sentezlenir — dış dosya gerekmez)
# =====================================================================
_SR = 22050


def _env_tone(freq, dur, vol=0.4, shape="sine", f_end=None, attack=0.004,
              power=1.6, noise=0.0, vib=0.0):
    n = max(1, int(dur * _SR))
    out = [0.0] * n
    phase = 0.0
    two_pi = math.pi * 2
    att_n = max(1, int(attack * _SR))
    for i in range(n):
        t = i / n
        f = freq if f_end is None else freq + (f_end - freq) * t
        if vib:
            f *= 1 + vib * math.sin(i / _SR * 30)
        phase += f / _SR
        p = phase - int(phase)
        if shape == "sine":
            s = math.sin(two_pi * phase)
        elif shape == "square":
            s = 1.0 if p < 0.5 else -1.0
        elif shape == "saw":
            s = 2 * p - 1
        elif shape == "tri":
            s = 4 * abs(p - 0.5) - 1
        else:
            s = random.uniform(-1, 1)
        if noise:
            s = s * (1 - noise) + random.uniform(-1, 1) * noise
        a = i / att_n if i < att_n else 1.0
        out[i] = s * a * ((1 - t) ** power) * vol
    return out


def _mix(parts, total=None):
    if total is None:
        total = max(int(off * _SR) + len(s) for s, off in parts)
    out = [0.0] * total
    for s, off in parts:
        o = int(off * _SR)
        for i, v in enumerate(s):
            j = o + i
            if j >= total:
                break
            out[j] += v
    return out


def _to_bytes(samples, channels=1):
    arr = array('h')
    for v in samples:
        iv = int(clamp(v, -1.0, 1.0) * 30000)
        arr.append(iv)
        if channels == 2:
            arr.append(iv)
    return arr.tobytes()


def _arp(notes, step, dur, vol, shape="tri"):
    return [(_env_tone(f, dur, vol, shape), i * step) for i, f in enumerate(notes)]


SFX_BUILDERS = {
    "shoot_a":  lambda: _env_tone(900, 0.09, .13, "square", f_end=380),
    "shoot_b":  lambda: _mix([(_env_tone(260, .18, .2, "saw", f_end=80), 0), (_env_tone(0, .18, .1, "noise"), 0)]),
    "shoot_c":  lambda: _env_tone(1400, .10, .12, "saw", f_end=300, noise=.5),
    "shoot_d":  lambda: _mix([(_env_tone(0, .14, .15, "noise", power=2.0), 0), (_env_tone(220, .14, .12, "sine", f_end=100), 0)]),
    "hit":      lambda: _env_tone(320, .05, .11, "square", f_end=140, noise=.35),
    "crit":     lambda: _mix([(_env_tone(900, .08, .18, "tri", f_end=1500), 0), (_env_tone(300, .06, .1, "square", f_end=120), 0)]),
    "kill":     lambda: _env_tone(480, .16, .2, "saw", f_end=70, noise=.3),
    "bonk":     lambda: _mix([(_env_tone(150, .28, .5, "sine", f_end=45), 0), (_env_tone(0, .2, .22, "noise", power=2.4), 0)]),
    "dash":     lambda: _mix([(_env_tone(0, .16, .18, "noise", power=2.2), 0), (_env_tone(300, .14, .06, "sine", f_end=900), 0)]),
    "coin":     lambda: _mix([(_env_tone(1250, .05, .13, "sine"), 0), (_env_tone(1700, .08, .13, "sine"), .05)]),
    "xp":       lambda: _env_tone(700, .05, .07, "sine", f_end=1100),
    "heart":    lambda: _env_tone(600, .14, .2, "tri", f_end=950),
    "levelup":  lambda: _mix(_arp([523, 659, 784, 1047], .09, .2, .22)),
    "hurt":     lambda: _env_tone(210, .2, .28, "saw", f_end=70, noise=.45),
    "shield":   lambda: _mix([(_env_tone(900, .15, .22, "sine", f_end=1600), 0), (_env_tone(450, .15, .12, "tri"), 0)]),
    "buy":      lambda: _mix([(_env_tone(880, .07, .2, "sine"), 0), (_env_tone(1320, .12, .2, "sine"), .07)]),
    "error":    lambda: _mix([(_env_tone(160, .1, .16, "square"), 0), (_env_tone(140, .12, .16, "square"), .13)]),
    "boss":     lambda: _mix([(_env_tone(80, .9, .45, "saw", f_end=40, vib=.05), 0), (_env_tone(0, .9, .07, "noise", power=1.2), 0)]),
    "wave":     lambda: _env_tone(220, .35, .22, "tri", f_end=440),
    "explosion": lambda: _mix([(_env_tone(0, .5, .45, "noise", power=2.5), 0), (_env_tone(90, .5, .4, "sine", f_end=30), 0)]),
    "lightning": lambda: _mix([(_env_tone(0, .22, .28, "noise", power=3.0), 0), (_env_tone(2200, .22, .13, "saw", f_end=150), 0)]),
    "click":    lambda: _env_tone(700, .03, .1, "sine"),
    "hover":    lambda: _env_tone(500, .015, .04, "sine"),
    "ach":      lambda: _mix(_arp([659, 784, 988, 1319], .1, .24, .18)),
    "gameover": lambda: _env_tone(420, .9, .28, "saw", f_end=60, vib=.02),
    "second":   lambda: _mix([(_env_tone(400, .5, .26, "sine", f_end=1200), 0), (_env_tone(300, .5, .12, "tri", f_end=900), 0)]),
    "warn":     lambda: _mix([(_env_tone(460, .07, .12, "square"), 0), (_env_tone(460, .07, .12, "square"), .11)]),
}


def _midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def _gen_music(kind):
    bpm = 132 if kind == "battle" else 84
    beat = 60.0 / bpm
    bars = 4
    total = int(bars * 4 * beat * _SR)
    roots = [45, 41, 36, 43]
    chords = [[69, 72, 76], [65, 69, 72], [72, 76, 79], [67, 71, 74]]
    parts = []
    step = beat / 2
    for b in range(bars):
        t0 = b * 4 * beat
        ch = chords[b]
        if kind == "battle":
            for i in range(8):
                nn = roots[b] + (12 if i % 4 == 3 else 0)
                parts.append((_env_tone(_midi(nn), step * 0.92, .15, "saw", power=1.1), t0 + i * step))
            for i in range(16):
                nn = ch[[0, 1, 2, 1][i % 4]] + (12 if i % 8 >= 6 else 0)
                parts.append((_env_tone(_midi(nn), step * 0.5, .055, "tri"), t0 + i * step / 2))
            for i in range(4):
                parts.append((_env_tone(130, .16, .45, "sine", f_end=45, power=2.0), t0 + i * beat))
            for i in (1, 3):
                parts.append((_env_tone(0, .11, .15, "noise", power=2.0), t0 + i * beat))
            for i in range(8):
                parts.append((_env_tone(0, .03, .05, "noise", power=1.0), t0 + i * step + step * 0.5))
        else:
            for n in ch:
                parts.append((_env_tone(_midi(n - 12), 4 * beat * 0.98, .05, "tri", power=.6, attack=.3), t0))
            parts.append((_env_tone(_midi(roots[b]), 4 * beat * 0.9, .09, "sine", power=.8, attack=.05), t0))
            for i in range(8):
                parts.append((_env_tone(_midi(ch[i % 3] + 12), step * 0.9, .045, "sine"), t0 + i * step))
    return _mix(parts, total)


class _NullAudio:
    ok = False

    def play(self, *a, **k):
        pass

    def update(self):
        pass

    def set_music(self, *a, **k):
        pass


audio = _NullAudio()


def sfx(name, vol=1.0, gap=0.03):
    audio.play(name, vol, gap)


class AudioManager:
    def __init__(self, settings):
        global _SR
        self.settings = settings
        self.ok = False
        self.sounds = {}
        self.music_snd = {}
        self._raw = {}
        self._lock = threading.Lock()
        self.want_music = None
        self.cur_music = None
        self.music_ch = None
        self._last = {}
        self.channels = 1
        try:
            try:
                pygame.mixer.init(22050, -16, 1, 512, allowedchanges=0)
            except TypeError:
                pygame.mixer.init(22050, -16, 1, 512)
            info = pygame.mixer.get_init()
            if info:
                _SR = int(info[0])
                self.channels = int(info[2]) if info[2] in (1, 2) else 1
                pygame.mixer.set_num_channels(24)
                pygame.mixer.set_reserved(1)
                self.music_ch = pygame.mixer.Channel(0)
                self.ok = True
                threading.Thread(target=self._generate, daemon=True).start()
        except Exception:
            self.ok = False

    def _generate(self):
        try:
            for name, fn in SFX_BUILDERS.items():
                raw = _to_bytes(fn(), self.channels)
                with self._lock:
                    self._raw[("sfx", name)] = raw
            for kind in ("menu", "battle"):
                raw = _to_bytes(_gen_music(kind), self.channels)
                with self._lock:
                    self._raw[("music", kind)] = raw
        except Exception:
            pass

    def update(self):
        if not self.ok:
            return
        with self._lock:
            items = list(self._raw.items())
            self._raw.clear()
        for (kind, name), raw in items:
            try:
                snd = pygame.mixer.Sound(buffer=raw)
            except Exception:
                continue
            if kind == "sfx":
                self.sounds[name] = snd
            else:
                self.music_snd[name] = snd
        try:
            if self.want_music != self.cur_music:
                if self.want_music is None:
                    self.music_ch.fadeout(500)
                    self.cur_music = None
                elif self.want_music in self.music_snd:
                    self.music_ch.play(self.music_snd[self.want_music], loops=-1, fade_ms=700)
                    self.cur_music = self.want_music
            self.music_ch.set_volume(clamp(self.settings.get("music_vol", 0.5), 0.0, 1.0))
        except Exception:
            pass

    def set_music(self, name):
        self.want_music = name

    def play(self, name, vol=1.0, gap=0.03):
        if not self.ok:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        now = time.time()
        if now - self._last.get(name, 0.0) < gap:
            return
        self._last[name] = now
        try:
            snd.set_volume(clamp(vol * self.settings.get("sfx_vol", 0.7), 0.0, 1.0))
            snd.play()
        except Exception:
            pass


# =====================================================================
# KAYIT SİSTEMİ
# =====================================================================

class SaveManager:
    DEFAULT = {
        "gems": 0,
        "skins_owned": ["default"],
        "equipped_skin": "default",
        "cosmetics_owned": [],
        "books_owned": [],          # görevi tamamlanıp kalıcı açılmış kitaplar
        "save_version": 0,
        "equipped_cosmetics": {"hat": None, "eyewear": None, "cape": None},
        "leaderboard": [],
        "achievements": {},
        "settings": {"fullscreen": False, "player_name": "", "music_vol": 0.5, "sfx_vol": 0.7,
                     "shake": True, "dmg": True, "fps": False, "difficulty": "normal",
                     "skill_scale": 0.85, "plain_skin": False},
        "stats": {"runs": 0, "best_score": 0, "total_kills": 0, "total_time": 0.0,
                  "bosses": 0, "best_wave": 0, "total_shots": 0, "total_lifesteal": 0.0,
                  "total_gold": 0, "best_run_gold": 0, "best_run_dashes": 0,
                  "best_run_shots": 0, "total_bonk_hits": 0, "shop_max": {}},
    }

    def __init__(self):
        self.data = self._load()
        self.apply_cfg()

    def _load(self):
        merged = json.loads(json.dumps(SaveManager.DEFAULT))
        for path in (SAVE_FILE, LEGACY_SAVE):
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                    for k, v in loaded.items():
                        if isinstance(v, dict) and isinstance(merged.get(k), dict):
                            merged[k].update(v)
                        else:
                            merged[k] = v
                    break
                except Exception:
                    continue
        if "default" not in merged.get("skins_owned", []):
            merged.setdefault("skins_owned", []).append("default")
        merged = self._migrate(merged)
        return merged

    # Kayıt biçimi değiştiğinde eski kayıtları düzelten tek yer.
    SAVE_VERSION = 3

    def _migrate(self, data):
        ver = int(data.get("save_version", 0) or 0)
        if ver < 2:
            # v2: Kitaplar artık ELMASLA satın alınmıyor, GÖREVLE açılıyor.
            # Eski kayıttaki satın alınmış kitap listesi temizlenir; kitaplar
            # bundan sonra yalnızca görevleri tamamlandıkça açılır.
            data["books_owned"] = []
            data["save_version"] = 2
        if ver < 3:
            # v3: Artık BAŞLANGIÇ kitabı yok — temel kitaplar dâhil bütün
            # kitaplar kilitli ve her kitabın birden fazla şartı olabiliyor.
            # Eski açık kitap listesi temizlenir ki yeni şartlar baştan işlesin.
            data["books_owned"] = []
            data["save_version"] = 3
        return data

    def save(self):
        try:
            tmp = SAVE_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, SAVE_FILE)
        except Exception as e:
            print("Kayit yazilamadi:", e)

    def apply_cfg(self):
        st = self.data.get("settings", {})
        CFG["shake"] = bool(st.get("shake", True))
        CFG["dmg"] = bool(st.get("dmg", True))
        CFG["fps"] = bool(st.get("fps", False))
        CFG["skill_scale"] = float(st.get("skill_scale", 0.85))
        CFG["plain_skin"] = bool(st.get("plain_skin", False))

    # ---- elmas ----
    def add_gems(self, amount):
        self.data["gems"] = max(0, self.data.get("gems", 0) + int(amount))

    def get_gems(self):
        return self.data.get("gems", 0)

    # ---- skinler ----
    def owns_skin(self, skin_id):
        return skin_id in self.data.get("skins_owned", ["default"])

    def buy_skin(self, skin_id, cost):
        # Premium skinler yalnızca gerçek parayla alınır; elmasla satılmaz.
        if get_skin(skin_id).get("premium"):
            return False
        if self.owns_skin(skin_id) or self.get_gems() < cost:
            return False
        self.add_gems(-cost)
        self.data.setdefault("skins_owned", ["default"]).append(skin_id)
        self.equip_skin(skin_id)
        self.save()
        return True

    def grant_skin(self, skin_id):
        """Bir skini kalıcı olarak hesaba ekler (premium satın alma sonrası)."""
        owned = self.data.setdefault("skins_owned", ["default"])
        if skin_id not in owned:
            owned.append(skin_id)
        self.save()
        return True

    def equip_skin(self, skin_id):
        self.data["equipped_skin"] = skin_id
        self.save()

    def equipped_skin_id(self):
        sid = self.data.get("equipped_skin", "default")
        return sid if self.owns_skin(sid) else "default"

    # ---- kıyafetler (kozmetik: şapka / gözlük / pelerin) ----
    def owns_cosmetic(self, cid):
        return cid in self.data.get("cosmetics_owned", [])

    def buy_cosmetic(self, cid, cost):
        if self.owns_cosmetic(cid) or self.get_gems() < cost:
            return False
        self.add_gems(-cost)
        self.data.setdefault("cosmetics_owned", []).append(cid)
        self.save()
        return True

    # ---- kitaplar ----
    def owns_book(self, key):
        """Kitap AÇIK mı?

        Kitaplar elmasla satın alınmaz; GÖREVLE açılır ve ARTIK HEPSİ
        kilitlidir. Bir kitap şu iki durumdan biriyle açıktır:
          1) Bütün açılış şartları tamamlanmış,
          2) Daha önce açılıp kalıcı olarak kaydedilmiş.
        """
        if key in self.data.get("books_owned", []):
            return True
        bk = BOOK_BY_KEY.get(key)
        if not bk:
            return False
        return book_progress(self, bk)[2]

    def refresh_book_unlocks(self):
        """Görevi yeni tamamlanan kitapları kalıcı olarak işaretler.

        Koşu bittikten sonra çağrılır; yeni açılan kitapların anahtar
        listesini döndürür (bildirim göstermek için).
        """
        owned = self.data.setdefault("books_owned", [])
        newly = []
        for bk in BOOKS:
            key = bk["key"]
            if key in owned:
                continue
            if book_progress(self, bk)[2]:
                owned.append(key)
                newly.append(key)
        if newly:
            self.save()
        return newly

    def unlocked_books(self):
        """Seviye atlamada çıkabilecek kitapların listesi."""
        return [b for b in BOOKS if self.owns_book(b["key"])]

    def equip_cosmetic(self, slot, cid):
        eq = self.data.setdefault("equipped_cosmetics", {"hat": None, "eyewear": None, "cape": None})
        eq[slot] = cid
        self.save()

    def unequip_cosmetic(self, slot):
        eq = self.data.setdefault("equipped_cosmetics", {"hat": None, "eyewear": None, "cape": None})
        eq[slot] = None
        self.save()

    def equipped_cosmetic_id(self, slot):
        eq = self.data.get("equipped_cosmetics", {})
        cid = eq.get(slot)
        return cid if cid and self.owns_cosmetic(cid) else None

    def cosmetics_locked(self):
        """Kuşanılmış skin kendi kostümüyle mi geliyor?

        PREMİUM skinler (Ağ Ustası, Kül Savaşçısı ...) maskesi ve pelerini
        dahil tek parça gelir; bunlar kuşanıldığında şapka/gözlük/pelerin
        slotları kilitlenir.
        """
        return bool(get_skin(self.equipped_skin_id()).get("locks_cosmetics"))

    def equipped_cosmetics(self):
        # Premium skin kuşanıldığında oyuncunun daha önce taktığı kıyafetler
        # otomatik olarak devre dışı kalır. Seçim kayıttan SİLİNMEZ — premium
        # skinden çıkınca eski kıyafetler geri gelir.
        if self.cosmetics_locked():
            return {"hat": None, "eyewear": None, "cape": None}
        return {slot: self.equipped_cosmetic_id(slot) for slot in ("hat", "eyewear", "cape")}

    # ---- yerel skor tablosu ----
    def submit_score(self, name, score, kills, run_time, wave, diff="normal"):
        board = self.data.setdefault("leaderboard", [])
        entry = {
            "name": (name[:14] if name else "İsimsiz"),
            "score": int(score), "kills": int(kills), "time": run_time,
            "wave": wave, "diff": diff, "date": time.strftime("%d.%m.%Y"),
        }
        board.append(entry)
        board.sort(key=lambda e: e["score"], reverse=True)
        rank = -1
        for i, e in enumerate(board):
            if e is entry:
                rank = i
        del board[10:]
        if rank >= 10:
            rank = -1
        self.save()
        return rank

    def qualifies_for_board(self, score):
        board = self.data.get("leaderboard", [])
        if len(board) < 10:
            return True
        return score > board[-1]["score"]


# =====================================================================
# STEAM KÖPRÜSÜ (opsiyonel — SteamworksPy yoksa sessizce devre dışı)
# =====================================================================

class SteamBridge:
    def __init__(self):
        self.ok = False
        self.sw = None
        try:
            from steamworks import STEAMWORKS  # SteamworksPy
            self.sw = STEAMWORKS()
            self.sw.initialize()
            self.ok = True
        except Exception:
            self.ok = False

    def set_achievement(self, ach_id):
        if not self.ok:
            return
        try:
            try:
                self.sw.UserStats.SetAchievement(ach_id)
            except Exception:
                self.sw.UserStats.SetAchievement(ach_id.encode())
            self.sw.UserStats.StoreStats()
        except Exception:
            pass

    def run_callbacks(self):
        if self.ok:
            try:
                self.sw.run_callbacks()
            except Exception:
                pass


# =====================================================================
# ELMAS PAKETLERİ VE SATIN ALMA
# =====================================================================

# Paketlerin GERÇEK fiyatı Steam Partner panelinde tanımlanır ve bölgeye göre
# değişir; buradaki `price_hint` yalnızca ekranda gösterilen bir tahmindir.
# `id` değeri Steam'deki öğe kimliğiyle (itemid) BİREBİR aynı olmalıdır.
GEM_PACKS = [
    dict(id=1001, gems=500,   bonus=0,  price_hint="₺29",   tag="",             color=(120, 200, 255)),
    dict(id=1002, gems=1200,  bonus=10, price_hint="₺59",   tag="POPÜLER",      color=(140, 215, 255)),
    dict(id=1003, gems=2600,  bonus=20, price_hint="₺119",  tag="",             color=(170, 190, 255)),
    dict(id=1004, gems=7000,  bonus=35, price_hint="₺279",  tag="EN AVANTAJLI", color=(255, 205, 110)),
]


def gem_pack_total(pack):
    """Paketin bonus dahil toplam elmas miktarı."""
    return int(pack["gems"] * (1 + pack["bonus"] / 100.0))


# Satın alma uç noktası. Sunucu tarafı hazır olduğunda doldurulur
# (bkz. server.py -> /begin_purchase). BOŞ bırakıldığı sürece elmas marketi
# "yakında" olarak görünür ve hiçbir satın alma başlatılmaz.
PURCHASE_API_URL = ""

# Geliştirici test kipi. AÇIKSA hiçbir ödeme alınmaz, elmaslar yalnızca yerel
# olarak eklenir ve ekranda büyük harflerle "TEST" yazar. Oyuncuya dağıtılan
# yapıda ASLA açık bırakılmamalıdır.
FAKE_PURCHASE = os.environ.get("KASMA_FAKE_PURCHASE") == "1"


class PurchaseBridge:
    """Elmas paketi satın alma köprüsü.

    GERÇEK PARA AKIŞI OYUNUN İÇİNDE DEĞİL, SUNUCUDA KURULUR.
    Steam'de oyun-içi satın alma şu sırayla işler:

      1) Oyun, KENDİ sunucusuna "şu oyuncu şu paketi almak istiyor" der.
      2) Sunucu, Steam'in ISteamMicroTxn/InitTxn ucunu GİZLİ publisher
         anahtarıyla çağırır. (Bu anahtar asla oyunun içinde bulunmamalıdır;
         oyun dosyası açılabilir ve anahtar çalınabilir.)
      3) Steam istemcisinde ödeme penceresi açılır, oyuncu onaylar.
      4) Steam sunucuya bildirir, sunucu FinalizeTxn çağırır ve elmasları
         oyuncunun hesabına yazar.
      5) Oyun /get_player ile güncel elmas sayısını çeker.

    Bu sınıf 1. ve 5. adımları yapar. Sunucu tarafı kurulmadan satın alma
    AÇILMAZ; aksi hâlde ya parasını alıp elmas vermemiş ya da para almadan
    elmas vermiş oluruz.
    """

    def __init__(self, steam, api_url=PURCHASE_API_URL):
        self.steam = steam
        self.api_url = (api_url or "").rstrip("/")
        self.status = None        # ekranda gösterilen son durum metni
        self.busy = False
        self.last_error = None

    def available(self):
        """Satın alma şu an gerçekten yapılabilir mi?"""
        if FAKE_PURCHASE:
            return True
        return bool(self.api_url) and bool(self.steam and self.steam.ok)

    def unavailable_reason(self):
        if not self.api_url:
            return "Satın alma sunucusu henüz bağlı değil."
        if not (self.steam and self.steam.ok):
            return "Steam istemcisi çalışmıyor — oyunu Steam üzerinden başlat."
        return ""

    def steam_id(self):
        if not (self.steam and self.steam.ok):
            return None
        try:
            return str(self.steam.sw.Users.GetSteamID())
        except Exception:
            return None

    def begin_purchase(self, pack, on_done=None):
        """Satın almayı başlatır. Sonuç ASENKRON gelir.

        on_done(ok, mesaj) geri çağrısı ile bildirilir.
        """
        if self.busy:
            return False
        if FAKE_PURCHASE:
            # TEST KİPİ — para akışı yok, yalnızca geliştirme içindir.
            self.status = "TEST KİPİ: ödeme alınmadı"
            if on_done:
                on_done(True, "TEST: %s elmas eklendi" % fmt_num(gem_pack_total(pack)))
            return True
        if not self.available():
            self.last_error = self.unavailable_reason()
            if on_done:
                on_done(False, self.last_error)
            return False

        # EKSİK ADIM (bilerek boş bırakıldı):
        # Oyuncu Steam penceresinde onayladığında Steam,
        # MicroTxnAuthorizationResponse_t geri çağrısını gönderir. O anda
        # sunucudaki /finalize_purchase çağrılmalı ve elmaslar orada yazılır.
        # SteamworksPy bu geri çağrıyı her sürümde sunmadığı için burada
        # bağlanmadı; Steam entegrasyonunu kurarken bu kancayı eklemek
        # ZORUNLUDUR, aksi hâlde ödeme alınır ama elmas yazılmaz.
        self.busy = True
        self.status = "Steam ödeme penceresi açılıyor..."

        def work():
            ok, msg = False, "Satın alma başlatılamadı."
            try:
                payload = json.dumps({
                    "steam_id": self.steam_id(),
                    "item_id": pack["id"],
                    "quantity": 1,
                }).encode("utf-8")
                req = urllib.request.Request(
                    self.api_url + "/begin_purchase", data=payload,
                    headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=12) as r:
                    data = json.loads(r.read().decode("utf-8"))
                ok = bool(data.get("success"))
                msg = data.get("message") or ("Steam penceresini onayla." if ok
                                              else "Satın alma reddedildi.")
            except Exception as e:
                msg = "Sunucuya ulaşılamadı: %s" % e
            self.busy = False
            self.status = msg
            if on_done:
                on_done(ok, msg)

        threading.Thread(target=work, daemon=True).start()
        return True


# =====================================================================
# BAŞARIMLAR
# ---------------------------------------------------------------------
# Her başarım tek bir sözlükle tarif edilir; böylece BAŞARIMLAR ekranı
# kartları, ilerleme çubuklarını ve "nasıl kazanılır" metnini tek bir
# yerden okur.
#
#   id    : benzersiz anahtar (Steam başarım adı da budur)
#   name  : ekranda görünen ad
#   desc  : tek satırlık kısa tarif
#   how   : başarımın NASIL kazanılacağını anlatan uzun metin
#   icon  : draw_icon() simge adı
#   tier  : "bronz" | "gumus" | "altin" | "efsane"  (rozet rengi + sıralama)
#   gems  : açıldığında verilen elmas ödülü
#   track : dict(stat=<istatistik>, need=<hedef>) — ilerleme çubuğu ve
#           otomatik açılma için. Yoksa başarım oyun içinde tetiklenir.
#
# İzlenen istatistikler için ach_stat_value() bakınız; bazı anahtarlar
# (books_unlocked, skins_owned, ach_count) kayıttan türetilir.
# =====================================================================

ACH_TIERS = {
    "bronz":  {"label": "BRONZ",  "color": (196, 138, 86)},
    "gumus":  {"label": "GÜMÜŞ",  "color": (198, 208, 226)},
    "altin":  {"label": "ALTIN",  "color": (232, 186, 90)},
    "efsane": {"label": "EFSANE", "color": (196, 122, 255)},
}
ACH_TIER_ORDER = ["bronz", "gumus", "altin", "efsane"]

ACHIEVEMENTS = [
    dict(id="first_kill", name="İlk Kan", desc="İlk düşmanını öldür.",
         how="Arenaya gir ve tek bir düşman öldür. Sol tıkla ateş etmen yeterli — "
             "bu başarım ilk koşunun ilk saniyelerinde açılır.",
         icon="sword", tier="bronz", gems=10, track=dict(stat="total_kills", need=1)),
    dict(id="wave5", name="Isınma Turu", desc="5. dalgaya ulaş.",
         how="Dalga çubuğu ekranın üstünde. Düşman öldürdükçe dolar; 5. dalgayı "
             "gördüğünde başarım açılır.",
         icon="target", tier="bronz", gems=10, track=dict(stat="best_wave", need=5)),
    dict(id="combo30", name="Kombo Kralı", desc="30'luk kombo yap.",
         how="Düşmanları arka arkaya, ara vermeden öldür. Kombo sayacı sağ üstte; "
             "birkaç saniye vurmazsan sıfırlanır. Kalabalık dalgalarda BONK ile "
             "peş peşe öldürmek en kolay yol.",
         icon="flame", tier="bronz", gems=15, track=dict(stat="best_combo", need=30)),
    dict(id="fashion", name="Modacı", desc="Bir skin satın al.",
         how="Ana menüden SKIN MARKET'e gir ve elmasla herhangi bir skin al. "
             "Elmas, koşu sonunda kazandığın altının bir kısmından gelir.",
         icon="star", tier="bronz", gems=15),
    dict(id="lvl10", name="Tecrübeli", desc="Bir koşuda 10. seviyeye ulaş.",
         how="Düşmanlardan düşen mavi tecrübe küreciklerini topla. Her seviyede "
             "bir kitap seçersin; 10. seviyeye tek bir koşuda ulaşman gerekir.",
         icon="clover", tier="bronz", gems=15),
    dict(id="cursed", name="Şeytanla Dans", desc="Lanetli bir eşya satın al.",
         how="Koşu içi MARKET'i (B tuşu) aç ve kırmızı kurukafa simgeli LANETLİ "
             "eşyalardan birini al: Kan Sözleşmesi, Cam Top veya Şeytan Pazarlığı.",
         icon="skull", tier="bronz", gems=15),
    dict(id="bonk8", name="Yumruk Fırtınası", desc="Tek BONK ile 8 düşmana vur.",
         how="SPACE ile BONK at. Kalabalığın tam ortasına dalıp 8 düşmanı aynı anda "
             "vurman gerekir — BONK yarıçapını büyüten eşyalar işini kolaylaştırır.",
         icon="fist", tier="gumus", gems=25),
    dict(id="wave10", name="Hayatta Kalan", desc="10. dalgaya ulaş.",
         how="10. dalga ilk patronun geldiği dalgadır. Markete uğramayı ve "
             "seviye atlarken savunma kitaplarını almayı ihmal etme.",
         icon="shield", tier="gumus", gems=25, track=dict(stat="best_wave", need=10)),
    dict(id="massacre", name="Katliam", desc="Tek koşuda 250 düşman öldür.",
         how="Tek bir koşuda 250 öldürme. Uzun yaşamak şart: can, zırh ve can "
             "yenileme veren kitapları topla, dalga aralarında marketi kullan.",
         icon="skull", tier="gumus", gems=30, track=dict(stat="best_run_kills", need=250)),
    dict(id="rich", name="Altın Avcısı", desc="Tek koşuda 1500 altın kazan.",
         how="Düşmanlar öldüğünde altın düşürür — yerden TOPLAMAN gerekir. "
             "Toplama menzilini artıran kıyafetler ve Talan Çekirdeği bu işi hızlandırır.",
         icon="coin", tier="gumus", gems=25, track=dict(stat="best_run_gold", need=1500)),
    dict(id="dasher", name="Gölge Adım", desc="Tek koşuda 40 kez dash at.",
         how="SHIFT ya da SAĞ TIK ile dash at. Dash sırasında kısa süre hasar almazsın; "
             "bekleme süresini kısaltan Sis Adımı ile 40 dash kolayca dolar.",
         icon="dash", tier="gumus", gems=25, track=dict(stat="best_run_dashes", need=40)),
    dict(id="boss", name="Dev Avcısı", desc="Bir patronu yen.",
         how="Patronlar 10., 15., 20. ... dalgalarda gelir. Dövüş uzun sürer; "
             "hasar kitaplarını ve markette Patron Avcısı etkilerini önceden hazırla.",
         icon="skull", tier="gumus", gems=30, track=dict(stat="bosses", need=1)),
    dict(id="marathon", name="Maratoncu", desc="Toplamda 2 saat arenada kal.",
         how="Bu sayaç bütün koşularının süresini toplar — oynadıkça kendiliğinden dolar.",
         icon="orbit", tier="gumus", gems=40, track=dict(stat="total_time", need=7200)),
    dict(id="hunter", name="Usta Avcı", desc="Toplamda 2000 düşman öldür.",
         how="Bütün koşuların toplamı sayılır. Sabırla oynadıkça dolar; "
             "yüksek dalgalarda düşman sayısı arttığı için çok daha hızlı ilerler.",
         icon="sword", tier="altin", gems=50, track=dict(stat="total_kills", need=2000)),
    dict(id="wave15", name="Arena Ustası", desc="15. dalgaya ulaş.",
         how="15. dalgada aynı anda birden fazla patron gelebilir. Kaçmayı öğren: "
             "dash bekleme süresi ve hareket hızı bu dalgalarda hasardan değerlidir.",
         icon="shield", tier="altin", gems=50, track=dict(stat="best_wave", need=15)),
    dict(id="nightmare", name="Kabus Avcısı", desc="Kabus zorluğunda 5. dalgaya ulaş.",
         how="Ana menüden ZORLUK'u KABUS yap. Düşmanlar çok daha sık gelir; "
             "5. dalgaya ulaşman yeterli.",
         icon="flame", tier="altin", gems=60),
    dict(id="shots50k", name="Mermi Fabrikası", desc="Toplamda 50.000 mermi at.",
         how="Her atışın saydırır; çoklu atış aldığında tek tıkla birden fazla mermi "
             "sayılır. Atış hızı ve Çoklu Atış veren her şey bu sayacı hızlandırır.",
         icon="target", tier="altin", gems=60, track=dict(stat="total_shots", need=50000)),
    dict(id="leech10k", name="Sülük", desc="Kan Emici ile toplam 10.000 can çal.",
         how="Koşu içi MARKET'ten KAN EMİCİ al ve seviyesini yükselt. Verdiğin hasarın "
             "bir kısmı cana döner — çalınan her can bu sayaca eklenir.",
         icon="heart", tier="altin", gems=60, track=dict(stat="total_lifesteal", need=10000)),
    dict(id="boss10", name="Patron Kâbusu", desc="Toplamda 10 patron devir.",
         how="Her koşuda devirdiğin patronlar toplanır. Patron dalgalarına "
             "hazırlıklı gir: kalkan, ikinci nefes ve patron hasarı artıran etkiler.",
         icon="skull", tier="altin", gems=70, track=dict(stat="bosses", need=10)),
    dict(id="gold100k", name="Hazine Sandığı", desc="Toplamda 100.000 altın topla.",
         how="Yerden topladığın altınların tamamı sayılır. Talan Çekirdeği ve altın "
             "kazancını artıran skinler bu sayacı katlar.",
         icon="coin", tier="altin", gems=60, track=dict(stat="total_gold", need=100000)),
    dict(id="bookworm", name="Kitap Kurdu", desc="10 kitabın kilidini aç.",
         how="KİTAPLIK ekranındaki görevleri tamamla. Her kitabın kendi görevi var; "
             "10 kitap açtığında bu başarım gelir.",
         icon="book", tier="altin", gems=80, track=dict(stat="books_unlocked", need=10)),
    dict(id="wave20", name="Efsane", desc="20. dalgaya ulaş.",
         how="20. dalga ciddi bir duvardır. Buraya gelmek için kitap seçimlerinin "
             "birbirini tamamlaması gerekir: hasar + hayatta kalma dengesi.",
         icon="star", tier="altin", gems=75, track=dict(stat="best_wave", need=20)),
    dict(id="hell_gate", name="Cehennem Kapısı", desc="Mor portaldan geçip CEHENNEM'e in.",
         how="25. dalganın patronunu devir; arenada mor bir portal açılır. "
             "Portalın yanına git ve E tuşuna bas.",
         icon="gem", tier="altin", gems=100),
    dict(id="hell_boss", name="Cehennem Fatihi", desc="Cehennemde bir patron devir.",
         how="CEHENNEM'e indikten sonra 5. dalgada ilk cehennem patronu gelir. "
             "Cehennem yaratıkları arenanın 25. dalgası kadar güçlüdür — markette "
             "yalnızca cehennemde açılan CEHENNEM kademesindeki eşyaları al.",
         icon="flame", tier="efsane", gems=150),
    dict(id="wave25", name="Ölümsüz", desc="25. dalgaya ulaş.",
         how="Oyunun en zor hedeflerinden biri. Nadir kitaplar, efsanevi market "
             "eşyaları ve kusursuz kaçınma olmadan neredeyse imkânsız.",
         icon="shield", tier="efsane", gems=120, track=dict(stat="best_wave", need=25)),
    dict(id="legend", name="Arena Efsanesi", desc="Diğer bütün başarımları aç.",
         how="Listedeki diğer başarımların hepsini tamamla. Sonuncusunu açtığın anda "
             "bu başarım da kendiliğinden gelir.",
         icon="gem", tier="efsane", gems=250,
         track=dict(stat="ach_count", need=22)),
]
ACH_BY_ID = {a["id"]: a for a in ACHIEVEMENTS}
# "Arena Efsanesi" kendisi hariç bütün başarımları ister; sayı listeden türetilir
# ki yeni başarım eklendiğinde hedef elle güncellenmek zorunda kalmasın.
ACH_BY_ID["legend"]["track"]["need"] = len(ACHIEVEMENTS) - 1


def ach_stat_value(save, stat):
    """Bir başarım sayacının güncel değeri.

    Çoğu sayaç kayıttaki 'stats' sözlüğünden okunur; birkaçı (açılan kitap,
    sahip olunan skin, açılan başarım sayısı) kayıttan türetilir.
    """
    if stat == "books_unlocked":
        return sum(1 for b in BOOKS if save.owns_book(b["key"]))
    if stat == "skins_owned":
        return len(save.data.get("skins_owned", []))
    if stat == "ach_count":
        return len([k for k in save.data.get("achievements", {}) if k != "legend"])
    return save.data.get("stats", {}).get(stat, 0) or 0


def ach_progress(save, ach):
    """(şu an, hedef, tamamlandı mı) — izlenmeyen başarımlarda (0, 0, False)."""
    tr = ach.get("track")
    if not tr:
        got = ach["id"] in save.data.get("achievements", {})
        return (1 if got else 0), 0, got
    cur = ach_stat_value(save, tr["stat"])
    need = tr["need"]
    return cur, need, cur >= need


def ach_tier_color(ach):
    return ACH_TIERS.get(ach.get("tier", "bronz"), ACH_TIERS["bronz"])["color"]


class AchievementManager:
    def __init__(self, save, steam):
        self.save = save
        self.steam = steam
        self.toasts = []  # [id, süre]

    def has(self, ach_id):
        return ach_id in self.save.data.get("achievements", {})

    def unlock(self, ach_id):
        if ach_id not in ACH_BY_ID or self.has(ach_id):
            return False
        self.save.data.setdefault("achievements", {})[ach_id] = time.strftime("%d.%m.%Y")
        # Başarımlar artık elmas ödülü de verir.
        gems = int(ACH_BY_ID[ach_id].get("gems", 0) or 0)
        if gems:
            self.save.add_gems(gems)
        self.save.save()
        self.toasts.append([ach_id, 4.0])
        sfx("ach", 1.0, 0.0)
        self.steam.set_achievement(ach_id)
        # Bir başarım açılınca "hepsini aç" başarımı da dolmuş olabilir.
        self.check_stats(_depth=1)
        return True

    def check_stats(self, _depth=0):
        """İstatistiğe bağlı başarımları otomatik açar.

        Koşu bitiminde ve oyun açılışında çağrılır; 'Usta Avcı' gibi toplam
        sayaçlara bağlı başarımlar eskiden hiçbir yerden tetiklenmiyordu.
        """
        opened = []
        for a in ACHIEVEMENTS:
            if not a.get("track") or self.has(a["id"]):
                continue
            if _depth and a["id"] != "legend":
                continue
            cur, need, done = ach_progress(self.save, a)
            if done:
                opened.append(a["id"])
        for aid in opened:
            self.unlock(aid)
        return opened

    def update(self, dt):
        for t in self.toasts:
            t[1] -= dt
        self.toasts = [t for t in self.toasts if t[1] > 0]

    def draw(self, surf):
        # Sağ üstte artık KÜÇÜK HARİTA var; bildirimler onun altından başlar.
        y = 210
        for ach_id, life in self.toasts[:3]:
            a = ACH_BY_ID[ach_id]
            k = clamp(min(life, 4.0 - life) * 3, 0, 1)
            w, h = 340, 66
            x = VIRTUAL_W - (w + 20) * ease_out_cubic(k) + 0
            r = pygame.Rect(int(x), y, w, h)
            tcol = ach_tier_color(a)
            panel(surf, r, bg=(30, 26, 14), edge=tcol, alpha=245, radius=12)
            add_glow(surf, r.x + 32, r.centery, 46, tcol, 0.16)
            draw_icon(surf, r.x + 32, r.centery, a.get("icon", "star"), tcol, 18)
            draw_text(surf, "BAŞARIM AÇILDI", (r.x + 62, r.y + 8), 12, GOLD_DIM, bold=True, shadow=False)
            draw_text(surf, a["name"], (r.x + 62, r.y + 24), 19, TEXT, bold=True)
            gems = int(a.get("gems", 0) or 0)
            if gems:
                draw_icon(surf, r.x + 68, r.y + 52, "gem", GEM_COLOR, 6)
                draw_text(surf, f"+{gems} elmas", (r.x + 78, r.y + 45), 12, GEM_COLOR,
                          bold=True, shadow=False)
            y += h + 8


# =====================================================================
# ÇEVRİMİÇİ İSTEMCİ (opsiyonel dünya skor tablosu)
# =====================================================================

class OnlineClient:
    def __init__(self, base_url):
        self.base_url = (base_url or "").rstrip("/")
        self.enabled = bool(self.base_url)
        self.world_scores = None
        self.world_error = None
        self.loading = False

    def fetch_world_scores_async(self):
        if not self.enabled:
            self.world_scores = []
            self.world_error = "Çevrimiçi sunucu ayarlanmamış (yerel modda)."
            return
        self.loading = True
        self.world_error = None
        self.world_scores = None
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self):
        try:
            req = urllib.request.Request(self.base_url + "/scores",
                                         headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict):
                    data = data.get("scores", [])
                if not isinstance(data, list):
                    data = []
                data.sort(key=lambda e: e.get("score", 0), reverse=True)
                self.world_scores = data[:50]
        except Exception:
            self.world_error = "Sunucuya ulaşılamadı. İnternet bağlantını kontrol et."
            self.world_scores = []
        finally:
            self.loading = False

    def submit_score_async(self, payload, on_done=None):
        if not self.enabled:
            return
        threading.Thread(target=self._submit_worker, args=(payload, on_done), daemon=True).start()

    def _submit_worker(self, payload, on_done):
        ok = False
        try:
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.base_url + "/submit", data=body,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=8) as resp:
                resp.read()
                ok = True
        except Exception:
            ok = False
        if on_done:
            on_done(ok)


# =====================================================================
# PARÇACIK / EFEKT SİSTEMİ
# =====================================================================

class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "r", "gravity", "add", "drag", "grow")

    def __init__(self, x, y, vx, vy, life, color, r, gravity=0.0, add=True, drag=2.0, grow=0.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = max(0.01, life)
        self.color = (int(color[0]), int(color[1]), int(color[2]))
        self.r = r
        self.gravity = gravity
        self.add = add
        self.drag = drag
        self.grow = grow

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        d = max(0.0, 1.0 - self.drag * dt)
        self.vx *= d
        self.vy *= d
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        k = clamp(self.life / self.max_life, 0.0, 1.0)
        r = max(1.0, (self.r + self.grow * (1 - k)) * (0.35 + 0.65 * k))
        if self.add:
            add_glow(surf, self.x, self.y, max(2, r * 2.6), self.color, k * 0.95)
        else:
            blit_disc(surf, self.x, self.y, r, self.color, 215 * k)


class Ring:
    __slots__ = ("x", "y", "r0", "r1", "life", "max_life", "color", "width")

    def __init__(self, x, y, r0, r1, life, color, width):
        self.x, self.y, self.r0, self.r1 = x, y, r0, r1
        self.life = life
        self.max_life = life
        self.color = color
        self.width = width

    def update(self, dt):
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        k = clamp(self.life / self.max_life, 0.0, 1.0)
        rad = lerp(self.r1, self.r0, k ** 1.6)
        col = scale_col(self.color, 0.25 + 0.75 * k)
        w = max(1, int(self.width * k + 0.5))
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), max(2, int(rad)), w)


class BoltFx:
    __slots__ = ("pts", "color", "life", "max_life")

    def __init__(self, pts, color, life):
        self.pts = pts
        self.color = color
        self.life = life
        self.max_life = life

    def update(self, dt):
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        k = clamp(self.life / self.max_life, 0.0, 1.0)
        pts = [(int(x), int(y)) for x, y in self.pts]
        if len(pts) >= 2:
            pygame.draw.lines(surf, scale_col(self.color, 0.6 + 0.4 * k), False, pts, max(2, int(5 * k)))
            pygame.draw.lines(surf, WHITE, False, pts, max(1, int(2 * k)))
        add_glow(surf, pts[-1][0], pts[-1][1], 34, self.color, k)


class FloatingText:
    __slots__ = ("x", "y", "vy", "life", "max_life", "text", "color", "size")

    def __init__(self, x, y, text, color=TEXT, size=18, vy=-46, life=0.8):
        self.x, self.y = x, y
        self.vy = vy
        self.life = life
        self.max_life = life
        self.text = text
        self.color = color
        self.size = size

    def update(self, dt):
        self.y += self.vy * dt
        self.vy *= (1 - min(1, dt * 1.5))
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        t = clamp(self.life / self.max_life, 0, 1)
        sz = int(self.size * (1.15 - 0.15 * t))
        draw_text(surf, self.text, (self.x, self.y), sz, self.color, bold=True, center=True,
                  alpha=int(255 * min(1.0, t * 2.2)))


class EffectSystem:
    MAX_PARTICLES = 650

    def __init__(self):
        self.particles = []
        self.texts = []
        self.rings = []
        self.bolts = []
        self.shake_time = 0.0
        self.shake_mag = 0.0
        self.flash = 0.0
        self.flash_col = WHITE

    def spark(self, x, y, color, vx=0.0, vy=0.0, life=0.5, r=2.5, add=True, gravity=0.0, drag=2.0, grow=0.0):
        if len(self.particles) < self.MAX_PARTICLES:
            self.particles.append(Particle(x, y, vx, vy, life, color, r, gravity, add, drag, grow))

    def burst(self, x, y, color, n=10, speed=140, life=0.5, r=3.0, gravity=0.0, add=True):
        for _ in range(n):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(speed * 0.3, speed)
            self.spark(x, y, color, math.cos(ang) * spd, math.sin(ang) * spd,
                       random.uniform(life * 0.6, life), random.uniform(r * 0.6, r), gravity, add)

    def ring(self, x, y, color, n=16, speed=180, life=0.4, r=2.5):
        for i in range(n):
            ang = (i / n) * math.tau
            self.spark(x, y, color, math.cos(ang) * speed, math.sin(ang) * speed, life, r)

    def shockwave(self, x, y, radius, color, life=0.35, width=5):
        self.rings.append(Ring(x, y, 4, radius, life, color, width))

    def bolt(self, pts, color=(200, 230, 255), life=0.25):
        self.bolts.append(BoltFx(pts, color, life))

    def popup(self, x, y, text, color=TEXT, size=18, life=0.8):
        if len(self.texts) < 60:
            self.texts.append(FloatingText(x, y, text, color, size, life=life))

    def shake(self, amount=8, duration=0.18):
        self.shake_time = max(self.shake_time, duration)
        self.shake_mag = max(self.shake_mag, amount)

    def do_flash(self, color=WHITE, amount=0.5):
        self.flash = max(self.flash, amount)
        self.flash_col = color

    def get_shake_offset(self):
        if self.shake_time <= 0 or not CFG["shake"]:
            return (0, 0)
        m = self.shake_mag * clamp(self.shake_time / 0.25, 0.0, 1.0)
        return (int(random.uniform(-m, m)), int(random.uniform(-m, m)))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]
        self.texts = [t for t in self.texts if t.update(dt)]
        self.rings = [r for r in self.rings if r.update(dt)]
        self.bolts = [b for b in self.bolts if b.update(dt)]
        if self.shake_time > 0:
            self.shake_time = max(0.0, self.shake_time - dt)
            if self.shake_time <= 0:
                self.shake_mag = 0.0
        if self.flash > 0:
            self.flash = max(0.0, self.flash - dt * 2.2)

    def draw(self, surf):
        for r in self.rings:
            r.draw(surf)
        for p in self.particles:
            p.draw(surf)
        for b in self.bolts:
            b.draw(surf)

    def draw_texts(self, surf):
        for t in self.texts:
            t.draw(surf)


# =====================================================================
# İKON ÇİZİMİ
# =====================================================================

def draw_icon(surf, cx, cy, kind, color, r=13):
    kind = kind or "star"
    color = (int(color[0]), int(color[1]), int(color[2]))
    cx, cy = float(cx), float(cy)
    if kind == "sword":
        pygame.draw.line(surf, color, (cx - r*0.5, cy + r*0.6), (cx + r*0.6, cy - r*0.6), 4)
        pygame.draw.line(surf, color, (cx - r*0.7, cy + r*0.1), (cx - r*0.2, cy + r*0.6), 3)
    elif kind == "boot":
        pts = [(cx - r*0.5, cy - r*0.6), (cx - r*0.1, cy - r*0.6), (cx - r*0.1, cy + r*0.15),
               (cx + r*0.6, cy + r*0.15), (cx + r*0.6, cy + r*0.55), (cx - r*0.5, cy + r*0.55)]
        pygame.draw.polygon(surf, color, pts, 0)
    elif kind == "heart":
        pygame.draw.circle(surf, color, (cx - r*0.32, cy - r*0.15), r*0.42)
        pygame.draw.circle(surf, color, (cx + r*0.32, cy - r*0.15), r*0.42)
        pygame.draw.polygon(surf, color, [(cx - r*0.7, cy - r*0.05), (cx + r*0.7, cy - r*0.05), (cx, cy + r*0.7)])
    elif kind == "bolt":
        pts = [(cx + r*0.15, cy - r*0.7), (cx - r*0.35, cy + r*0.05), (cx, cy + r*0.05),
               (cx - r*0.15, cy + r*0.7), (cx + r*0.4, cy - r*0.1), (cx + r*0.05, cy - r*0.1)]
        pygame.draw.polygon(surf, color, pts)
    elif kind == "target":
        pygame.draw.circle(surf, color, (cx, cy), r*0.7, 2)
        pygame.draw.circle(surf, color, (cx, cy), r*0.35, 2)
        pygame.draw.circle(surf, color, (cx, cy), 2)
    elif kind == "magnet":
        rect = pygame.Rect(0, 0, int(r*1.1), int(r*1.1))
        rect.center = (int(cx), int(cy))
        pygame.draw.arc(surf, color, rect, math.pi*0.15, math.pi*0.85, 4)
        pygame.draw.line(surf, color, (cx - r*0.55, cy), (cx - r*0.55, cy + r*0.5), 4)
        pygame.draw.line(surf, color, (cx + r*0.55, cy), (cx + r*0.55, cy + r*0.5), 4)
    elif kind == "coin":
        pygame.draw.circle(surf, color, (cx, cy), r*0.75, 2)
        draw_text(surf, "$", (cx, cy), int(r*1.1), color, bold=True, center=True, shadow=False)
    elif kind == "star":
        pts = []
        for i in range(10):
            ang = -math.pi/2 + i * math.pi/5
            rad = r*0.75 if i % 2 == 0 else r*0.32
            pts.append((cx + math.cos(ang)*rad, cy + math.sin(ang)*rad))
        pygame.draw.polygon(surf, color, pts)
    elif kind == "cross":
        pygame.draw.line(surf, color, (cx, cy - r*0.6), (cx, cy + r*0.6), 4)
        pygame.draw.line(surf, color, (cx - r*0.6, cy), (cx + r*0.6, cy), 4)
    elif kind == "shield":
        pts = [(cx, cy - r*0.75), (cx + r*0.65, cy - r*0.35), (cx + r*0.65, cy + r*0.15),
               (cx, cy + r*0.75), (cx - r*0.65, cy + r*0.15), (cx - r*0.65, cy - r*0.35)]
        pygame.draw.polygon(surf, color, pts, 2)
    elif kind == "fist":
        pygame.draw.circle(surf, color, (cx, cy), r*0.55, 3)
        pygame.draw.line(surf, color, (cx - r*0.2, cy - r*0.8), (cx - r*0.2, cy - r*0.3), 3)
        pygame.draw.line(surf, color, (cx + r*0.15, cy - r*0.85), (cx + r*0.15, cy - r*0.3), 3)
    elif kind == "clover":
        for ang in (0, math.pi/2, math.pi, math.pi*1.5):
            ox, oy = math.cos(ang)*r*0.35, math.sin(ang)*r*0.35
            pygame.draw.circle(surf, color, (cx + ox, cy + oy), r*0.38)
    elif kind == "gem":
        pts = [(cx, cy - r*0.8), (cx + r*0.7, cy - r*0.15), (cx + r*0.4, cy + r*0.75),
               (cx - r*0.4, cy + r*0.75), (cx - r*0.7, cy - r*0.15)]
        pygame.draw.polygon(surf, color, pts, 0)
        pygame.draw.polygon(surf, WHITE, pts, 1)
    elif kind == "skull":
        pygame.draw.circle(surf, color, (cx, cy - r*0.1), r*0.62)
        pygame.draw.rect(surf, color, (cx - r*0.32, cy + r*0.2, r*0.64, r*0.5))
        pygame.draw.circle(surf, (14, 14, 22), (cx - r*0.25, cy - r*0.1), r*0.16)
        pygame.draw.circle(surf, (14, 14, 22), (cx + r*0.25, cy - r*0.1), r*0.16)
    elif kind == "orbit":
        pygame.draw.circle(surf, color, (cx, cy), r*0.7, 1)
        pygame.draw.circle(surf, color, (cx + r*0.5, cy - r*0.5), r*0.22)
        pygame.draw.circle(surf, color, (cx - r*0.5, cy + r*0.5), r*0.22)
        pygame.draw.circle(surf, color, (cx, cy), r*0.18)
    elif kind == "dash":
        for off in (-0.5, 0.1):
            pygame.draw.lines(surf, color, False, [(cx + r*off, cy - r*0.55), (cx + r*(off+0.5), cy),
                                                    (cx + r*off, cy + r*0.55)], 3)
    elif kind == "drop":
        # zehir damlası
        pts = [(cx, cy - r*0.75), (cx + r*0.52, cy + r*0.18), (cx + r*0.30, cy + r*0.62),
               (cx - r*0.30, cy + r*0.62), (cx - r*0.52, cy + r*0.18)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.circle(surf, (14, 14, 22), (cx - r*0.14, cy + r*0.18), max(1, r*0.13))
    elif kind == "flame":
        pts = [(cx, cy - r*0.80), (cx + r*0.48, cy - r*0.05), (cx + r*0.34, cy + r*0.62),
               (cx - r*0.34, cy + r*0.62), (cx - r*0.48, cy - r*0.05)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, (14, 14, 22),
                            [(cx, cy - r*0.10), (cx + r*0.22, cy + r*0.30), (cx - r*0.22, cy + r*0.30)])
    elif kind == "snow":
        for k in range(3):
            a = k * math.pi / 3
            dx, dy = math.cos(a) * r*0.72, math.sin(a) * r*0.72
            pygame.draw.line(surf, color, (cx - dx, cy - dy), (cx + dx, cy + dy), 2)
        pygame.draw.circle(surf, color, (cx, cy), max(1, r*0.16))
    elif kind == "book":
        pygame.draw.rect(surf, color, (cx - r*0.62, cy - r*0.72, r*1.24, r*1.44), border_radius=2)
        pygame.draw.line(surf, (14, 14, 22), (cx, cy - r*0.62), (cx, cy + r*0.62), 2)
    else:
        pygame.draw.circle(surf, color, (cx, cy), r*0.6, 2)


# =====================================================================
# SKİNLER  (kozmetik — güç vermez, ama her biri farklı silah/mermi/efekt taşır)
# =====================================================================

SKINS = [
    dict(id="default", name="Klasik Mavi",     color=(110, 200, 255), accent=(210, 240, 255), cost=0,
         weapon="blaster",  proj="bolt",      aura="motes",   sfx="a", wlen=26,
         desc="Dengeli devriye tüfeği. Parlak mavi enerji atışları.",
         perks=["Hasar Alma -%4 (yeni başlayan dostu)"],
         perk_add=dict(dmg_taken_mult=-0.04)),
    dict(id="ranger", name="Yeşil Öncü",       color=(120, 210, 140), accent=(225, 255, 210), cost=0,
         weapon="crossbow", proj="feather",   aura="motes",   sfx="a", wlen=27,
         desc="İkinci ücretsiz karakter. Hafif ekipmanlı, çevik bir öncü.",
         perks=["Toplama Menzili +20", "Hareket Hızı +10"],
         perk_add=dict(base_pickup=20, base_speed=10)),
    dict(id="crimson", name="Kızıl Şahin",     color=(225, 70, 85),   accent=(255, 190, 160), cost=150,
         weapon="crossbow", proj="feather",   aura="wings",   sfx="a", wlen=26,
         desc="Kanatlarını çırpar, tüy gibi keskin oklar yağdırır.",
         perks=["Mermi Hızı +%12"],
         perk_add=dict(proj_speed_mult=0.12)),
    dict(id="toxic",   name="Zehir Yeşili",    color=(110, 215, 85),  accent=(200, 255, 150), cost=220,
         weapon="flask",    proj="toxic",     aura="bubbles", sfx="d", wlen=25,
         desc="Kabarcıklar saçan zehir tankı, damlayan asit mermileri.",
         perks=["Can Yenilenmesi +0.4/sn", "Altın Kazancı +%6"],
         perk_add=dict(base_regen=0.4, coin_mult=0.06)),
    dict(id="royal",   name="Kraliyet Moru",   color=(175, 120, 235), accent=(255, 220, 120), cost=320,
         weapon="scepter",  proj="star",      aura="stars",   sfx="a", wlen=38,
         desc="Tacını takar, asasıyla dönen yıldızlar fırlatır.",
         perks=["Deneyim Kazancı +%10", "Kritik Hasar +%10"],
         perk_add=dict(xp_mult=0.10, crit_dmg_mult=0.10)),
    dict(id="cyan",    name="Elektrik Cyan",   color=(100, 225, 225), accent=(230, 255, 255), cost=480,
         weapon="tesla",    proj="lightning", aura="arcs",    sfx="c", wlen=30,
         desc="Tesla bobini. Bedeninde her an bir zincir yıldırım hazır bekler.",
         perks=["Zincir Yıldırım Lv.2 ile başlar"],
         perk_set=dict(chain_level=2)),
    dict(id="shadow",  name="Gölge Suikastçı", color=(58, 52, 82),    accent=(175, 100, 255), cost=400,
         weapon="scythe",   proj="blackfire", aura="shadow",  sfx="b", wlen=38,
         desc="Elinde tırpan, ardında gölge izi. Siyah ateş fırlatır.",
         perks=["Dash Mesafesi +%20", "Mermi Delme +1"],
         perk_add=dict(dash_dist_mult=0.20, pierce_bonus=1)),
    dict(id="inferno", name="İnferno",         color=(245, 125, 40),  accent=(255, 225, 110), cost=480,
         weapon="cannon",   proj="fireball",  aura="flames",  sfx="d", wlen=28,
         desc="Tepesinde alev, elinde alev topu atan top. Yaktıkça yanar.",
         perks=["BONK Yarıçapı +%15", "BONK Hasarı +%10"],
         perk_add=dict(bonk_radius_mult=0.15, bonk_mult=0.10)),
    dict(id="gold",    name="Altın Efsane",    color=(232, 186, 90),  accent=(255, 245, 190), cost=700,
         weapon="goldgun",  proj="gold",      aura="halo",    sfx="a", wlen=33,
         desc="Halesi ve işlemeli altın tüfeğiyle gerçek bir efsane.",
         perks=["Altın Kazancı +%20", "Toplama Menzili +20"],
         perk_add=dict(coin_mult=0.20, base_pickup=20)),
    dict(id="prism",   name="Prizma",          color=(255, 120, 200), accent=(255, 255, 255), cost=1000,
         weapon="crystal",  proj="prism",     aura="prism",   sfx="c", wlen=30,
         desc="Sürekli renk değiştiren kristal silah ve mermiler.",
         perks=["Çoklu Atış Lv. +1", "Mermi Hızı +%10"],
         perk_add=dict(multishot_level=1, proj_speed_mult=0.10)),

    # ---- YENİ: ÖZEL YETENEKLİ SKINLER (elmasla alınan kalıcı avantajlar) ----
    dict(id="shadow_hunter", name="Gölge Avcı", color=(52, 44, 78), accent=(200, 150, 255), cost=650,
         weapon="crossbow", proj="blackfire", aura="shadow", sfx="b", wlen=27,
         desc="Karanlıkta pusuya yatan bir avcı. Ayak sesi yok, ok sesi yok.",
         perks=["Hareket Hızı +30", "Dash Bekleme Süresi -%15"],
         perk_add=dict(base_speed=30, dash_cd_mult=-0.15)),
    dict(id="frost_witch", name="Buz Büyücüsü", color=(160, 225, 255), accent=(255, 255, 255), cost=850,
         weapon="scepter", proj="star", aura="stars", sfx="a", wlen=36,
         desc="Asasının ucu buz gibi soğuk. Düşmanları donduran kristaller fırlatır.",
         perks=["Buz Lv.2 ile başlar (yavaşlatma)", "Kritik Vuruş Şansı +%8"],
         perk_set=dict(ice_level=2),
         perk_add=dict(crit_chance=0.08)),
    dict(id="blood_countess", name="Kan Kontesi", color=(200, 30, 55), accent=(255, 120, 130), cost=850,
         weapon="flask", proj="toxic", aura="bubbles", sfx="d", wlen=24,
         desc="Şişesinde kendi kanını taşır. Her vuruşta biraz can çalar.",
         perks=["Kan Emme Lv.2 ile başlar", "Can Yenilenmesi +0.8/sn"],
         perk_set=dict(vamp_level=2),
         perk_add=dict(base_regen=0.8)),
    dict(id="iron_sentinel", name="Zırhlı Devriye", color=(120, 128, 145), accent=(230, 235, 245), cost=750,
         weapon="goldgun", proj="gold", aura="halo", sfx="a", wlen=30,
         desc="Ağır zırh giyer, yavaş ama sağlam. Bir tank gibi öne dalar.",
         perks=["Zırh +%8 (hasar azaltma)", "Can +40", "Hareket Hızı -15 (ağır zırh)"],
         perk_add=dict(base_armor=0.08, base_max_hp=40, base_speed=-15)),
    dict(id="storm_bringer", name="Fırtına Getirici", color=(90, 150, 245), accent=(230, 245, 255), cost=1200,
         weapon="cannon", proj="fireball", aura="flames", sfx="c", wlen=29,
         desc="Gökyüzünü kendine bağlamış. Etrafına düzenli yıldırım fırtınası çağırır.",
         perks=["Fırtına Lv.1 ile başlar (periyodik alan hasarı)", "Mermi Hızı +%18"],
         perk_set=dict(storm_level=1),
         perk_add=dict(proj_speed_mult=0.18)),

    # ---- YENİ +5 SKIN ----
    dict(id="venom_striker", name="Zehir Vuruşçu", color=(90, 205, 115), accent=(220, 255, 210), cost=600,
         weapon="flask", proj="toxic", aura="bubbles", sfx="d", wlen=25,
         desc="Zehirli şişesiyle yakın dövüşe girer, teması bile acıtır.",
         perks=["Dikenler Lv.1 ile başlar (temas hasarına karşılık verir)", "Can Yenilenmesi +0.5/sn"],
         perk_set=dict(thorns_level=1),
         perk_add=dict(base_regen=0.5)),
    dict(id="homing_falcon", name="Yönelmeli Şahin", color=(90, 160, 245), accent=(220, 240, 255), cost=700,
         weapon="crossbow", proj="feather", aura="wings", sfx="a", wlen=27,
         desc="Okları hedefi asla şaşırmaz; havada bile yön değiştirir.",
         perks=["Yönelme Lv.1 ile başlar (mermiler hedefe yönelir)", "Dash Bekleme Süresi -%10"],
         perk_set=dict(homing_level=1),
         perk_add=dict(dash_cd_mult=-0.10)),
    dict(id="frenzy_beast", name="Çılgın Canavar", color=(220, 60, 40), accent=(255, 180, 90), cost=800,
         weapon="cannon", proj="fireball", aura="flames", sfx="d", wlen=28,
         desc="Ne kadar çok vurursa o kadar çılgınlaşır, durmak bilmez.",
         perks=["Çılgınlık Lv.1 ile başlar (ardışık vuruşta güçlenir)", "Can +20"],
         perk_set=dict(frenzy_level=1),
         perk_add=dict(base_max_hp=20)),
    dict(id="orbit_guardian", name="Yörünge Bekçisi", color=(70, 200, 190), accent=(220, 255, 250), cost=900,
         weapon="scepter", proj="star", aura="stars", sfx="a", wlen=37,
         desc="Etrafında dönen bir yıldız kalkanı ile korunur.",
         perks=["Yörünge Lv.1 ile başlar (etrafında dönen mermi)", "Zırh +%5"],
         perk_set=dict(orbit_level=1),
         perk_add=dict(base_armor=0.05)),
    # =================================================================
    # PREMİUM SKİNLER — elmasla DEĞİL, gerçek parayla alınır.
    # Her biri kendi kostümüyle (maske / pelerin / miğfer) gelir; kuşanıldığında
    # şapka-gözlük-pelerin slotları KİLİTLENİR ve oyuncunun daha önce taktığı
    # kıyafetler otomatik olarak devre dışı kalır (locks_cosmetics).
    # `item_id` Steamworks'teki öğe kimliğiyle birebir aynı olmalıdır.
    # =================================================================
    dict(id="web_master", name="Ağ Ustası", color=(205, 45, 58), accent=(60, 105, 215),
         cost=None, premium=True, item_id=2001, price_hint="₺79", locks_cosmetics=True,
         weapon="webshooter", proj="web", aura="web", sfx="a", wlen=22,
         desc="Bileklerinden ağ fırlatan maskeli akrobat. Vurduğu düşman ağa dolanıp "
              "neredeyse yerinde çakılır.",
         perks=["Buz Oku Lv.6 ile başlar (markette en fazla Lv.5 alınabilir)",
                "Kendi maskesi ve kostümüyle gelir"],
         perk_set=dict(ice_level=6)),
    dict(id="ash_warrior", name="Kül Savaşçısı", color=(226, 222, 214), accent=(190, 40, 45),
         cost=None, premium=True, item_id=2002, price_hint="₺79", locks_cosmetics=True,
         weapon="twinblades", proj="ash", aura="ash", sfx="b", wlen=30,
         desc="Külle kaplı, kızıl dövmeli bir savaş tanrısı. Her vuruşunda "
              "düşmanın canını kendine çeker.",
         perks=["Kan Emici Lv.6 ile başlar (markette en fazla Lv.5 alınabilir)",
                "Kendi kostümü ve omuz pelerini ile gelir"],
         perk_set=dict(vamp_level=6)),
    dict(id="green_titan", name="Yeşil Dev", color=(96, 190, 70), accent=(210, 255, 170),
         cost=None, premium=True, item_id=2003, price_hint="₺99", locks_cosmetics=True,
         weapon="fists", proj="rock", aura="titan", sfx="d", wlen=20,
         desc="Yumruğunu yere vurduğunda bütün arena sarsılır. Sarsıntı, patronlar "
              "dışındaki her düşmanın canını yarıya indirir.",
         perks=["EZİCİ DARBE: 10 sn'de bir tüm arenayı kaplar",
                "Ezici darbe patron dışı düşmanların canını yarıya indirir",
                "Normal BONK 5 sn'de bir  ·  150 can ile başlar"],
         perk_set=dict(titan_smash=1, bonk_cd=5.0),
         perk_add=dict(base_max_hp=50)),
    dict(id="immortal_merc", name="Ölümsüz Kiralık", color=(190, 35, 48), accent=(28, 30, 38),
         cost=None, premium=True, item_id=2004, price_hint="₺89", locks_cosmetics=True,
         weapon="pistols", proj="bullet", aura="merc", sfx="c", wlen=24,
         desc="Ölmeyi beceremeyen, çenesi düşük bir kiralık katil. Öldüğü darbede "
              "ayağa kalkar ve dövüşe devam eder.",
         perks=["İkinci Nefes ile başlar (öleceğin darbede yarı canla dirilirsin)",
                "Hasar +%45",
                "Kendi maskesi ve kostümüyle gelir"],
         perk_add=dict(second_wind_charges=1, run_dmg_mult=0.45)),

    dict(id="pink_dream", name="Pembe Rüya", color=(255, 105, 190), accent=(255, 222, 236), cost=1100,
         weapon="scepter", proj="star", aura="halo", sfx="a", wlen=36,
         desc="Tepeden tırnağa pembe — stiliyle olduğu kadar gücüyle de göz doldurur. "
              "Pembe şapka, gözlük ve pelerinle tamamla.",
         perks=["Can Yenilenmesi +0.6/sn", "Kritik Şans +%10", "Toplama Menzili +25"],
         perk_add=dict(base_regen=0.6, crit_chance=0.10, base_pickup=25)),
]
SKIN_BY_ID = {s["id"]: s for s in SKINS}


def get_skin(skin_id):
    return SKIN_BY_ID.get(skin_id, SKINS[0])


def skin_gem_cost(sk):
    """Skinin elmas fiyatı. Premium skinler elmasla SATILMAZ; bu yüzden
    fiyatları None'dur ve karşılaştırmalarda sonsuz sayılırlar."""
    c = sk.get("cost")
    return float("inf") if c is None else int(c)


# =====================================================================
# SKİN YETENEKLERİ  (her skinin kendi özel gücü)
# ---------------------------------------------------------------------
# Her skinin bir ÖZEL YETENEĞİ vardır. Yetenekler OTOMATİKTİR: bekleme
# süresi dolduğunda kendiliğinden çalışır, oyuncunun tuşa basması gerekmez.
# Kalan süre, ekranın altındaki yetenek çubuğunda ayrı bir yuvada görünür.
#
# ORTAK KURAL: Hangi yetenek çalışırsa çalışsın, düşmanlar 0.5 saniye
# DONAR (zaman durur), sonra hareketlerine devam eder. Böylece yetenek
# her zaman hissedilir ve oyuncuya küçük bir nefes payı verir.
#
#   name : yuvada ve mağazada görünen ad
#   desc : ne yaptığını anlatan tek cümle
#   icon : draw_icon() simge adı            color: yuva rengi
#   cd   : bekleme süresi (saniye)
#   kind : RunState.fire_skin_ult() içindeki davranış anahtarı
#   mode : "auto"   -> süre dolunca kendiliğinden çalışır
#          "trigger"-> süre dolduğunda HAZIR bekler, şartı oluşunca çalışır
#
# Güç dengesi: hiçbiri tek başına oyunu bitirmemeli; hepsi "orta" seviye.
# =====================================================================

SKIN_ULTS = {
    "default": dict(name="KALKAN PROTOKOLÜ", icon="shield", color=(120, 200, 255), cd=26.0,
                    kind="guard", mode="auto",
                    desc="2 kalkan yükü verir ve azami canının %15'ini yeniler."),
    "ranger": dict(name="ÖNCÜ ATILIMI", icon="boot", color=(150, 230, 170), cd=22.0,
                   kind="sprint", mode="auto",
                   desc="6 saniye boyunca %35 daha hızlı koşar, %25 daha hızlı ateş edersin."),
    "crimson": dict(name="ŞAHİN YAĞMURU", icon="target", color=(255, 130, 140), cd=18.0,
                    kind="nova", mode="auto", n=14, mult=0.85,
                    desc="Çevrene 14 delici tüy oku yağdırır."),
    "toxic": dict(name="ZEHİR BULUTU", icon="drop", color=(150, 235, 120), cd=17.0,
                  kind="poison_cloud", mode="auto", radius=280,
                  desc="Çevrendeki düşmanları zehirler ve yavaşlatır."),
    "royal": dict(name="KRALİYET FERMANI", icon="star", color=(215, 170, 255), cd=21.0,
                  kind="star_fall", mode="auto", n=7, mult=1.35,
                  desc="Rastgele 7 düşmanın tepesine yıldız düşer."),
    "cyan": dict(name="YILDIRIM FIRTINASI", icon="bolt", color=(120, 235, 235), cd=15.0,
                 kind="chain_storm", mode="auto",
                 desc="Haritadaki HERKESE yıldırım düşer: düşmanların canının %20'si gider "
                      "(patronlara Lv.3 yıldırım hasarı)."),
    "shadow": dict(name="GÖLGE DURUŞU", icon="skull", color=(190, 120, 255), cd=60.0,
                   kind="death_defy", mode="trigger", duration=5.0,
                   desc="Ölümcül darbede canını 1'e sabitler ve 5 saniye ZAMANI DURDURUR — "
                        "sen serbestçe hareket edersin."),
    "inferno": dict(name="ALEV HALKASI", icon="flame", color=(255, 150, 60), cd=19.0,
                    kind="fire_ring", mode="auto", radius=330,
                    desc="Çevrene genişleyen bir alev halkası salar; değdiği düşman yanar."),
    "gold": dict(name="ALTIN DOKUNUŞ", icon="coin", color=(240, 200, 100), cd=24.0,
                 kind="midas", mode="auto", radius=340,
                 desc="Çevredeki düşmanlara hasar verir ve her birinden fazladan altın düşürür."),
    "prism": dict(name="PRİZMA PATLAMASI", icon="gem", color=(255, 150, 220), cd=20.0,
                  kind="nova", mode="auto", n=18, mult=0.75, pierce=2,
                  desc="18 delici prizma ışınını her yöne saçar."),
    "shadow_hunter": dict(name="SESSİZ PUSU", icon="dash", color=(190, 150, 255), cd=23.0,
                          kind="ambush", mode="auto", duration=4.0,
                          desc="4 saniye dokunulmaz olursun ve bu sürede her vuruşun kritik gelir."),
    "frost_witch": dict(name="BUZ ÇAĞI", icon="snow", color=(180, 235, 255), cd=21.0,
                        kind="ice_age", mode="auto", freeze=2.5,
                        desc="Bütün düşmanları 2.5 saniye dondurur, sonrasında 5 saniye yavaşlatır."),
    "blood_countess": dict(name="KAN AYİNİ", icon="heart", color=(230, 70, 100), cd=20.0,
                           kind="blood_rite", mode="auto", radius=320,
                           desc="Çevredeki düşmanların canını emer; emilen canın yarısı sana geçer."),
    "iron_sentinel": dict(name="ZIRH KİLİDİ", icon="shield", color=(180, 190, 210), cd=25.0,
                          kind="bulwark", mode="auto", duration=6.0,
                          desc="6 saniye aldığın hasar %55 azalır ve çevrendeki düşmanları savurursun."),
    "storm_bringer": dict(name="GÖK GÜRÜLTÜSÜ", icon="bolt", color=(130, 180, 255), cd=18.0,
                          kind="thunder", mode="auto", n=6, mult=1.6,
                          desc="Arka arkaya 6 yıldırım, rastgele düşmanların tepesine iner."),
    "venom_striker": dict(name="DİKEN TARLASI", icon="drop", color=(120, 220, 140), cd=18.0,
                          kind="thorn_field", mode="auto", duration=6.0, radius=240,
                          desc="6 saniye boyunca çevrendeki düşmanlar sürekli zehir hasarı alır."),
    "homing_falcon": dict(name="GÜDÜMLÜ SALVO", icon="target", color=(130, 190, 255), cd=16.0,
                          kind="salvo", mode="auto", n=9, mult=0.95,
                          desc="Hedefi şaşmayan 9 güdümlü ok fırlatır."),
    "frenzy_beast": dict(name="KAN ÇILGINLIĞI", icon="flame", color=(255, 120, 70), cd=20.0,
                         kind="frenzy_rush", mode="auto", duration=7.0,
                         desc="7 saniye hasarın %40, atış hızın %30 artar."),
    "orbit_guardian": dict(name="YÖRÜNGE KALKANI", icon="orbit", color=(120, 230, 220), cd=20.0,
                           kind="orbit_shield", mode="auto", duration=8.0,
                           desc="8 saniye 3 ek yörünge bıçağı döner ve 1 kalkan yükü alırsın."),
    "web_master": dict(name="AĞ TUZAĞI", icon="orbit", color=(230, 80, 90), cd=16.0,
                       kind="web_trap", mode="auto", radius=360,
                       desc="Geniş bir ağ atar: yakalanan düşmanlar 4 saniye neredeyse yerinde çakılır."),
    "ash_warrior": dict(name="KÜL KASIRGASI", icon="sword", color=(235, 225, 210), cd=20.0,
                        kind="ash_spin", mode="auto", radius=230, mult=2.0,
                        desc="Çevrene savurarak vurur; verdiğin hasarın %25'i cana döner."),
    "green_titan": dict(name="YER SARSINTISI", icon="fist", color=(150, 255, 130), cd=22.0,
                        kind="quake", mode="auto", mult=1.3,
                        desc="Bütün arenayı sarsar: her düşmanı savurur ve hasar verir."),
    "immortal_merc": dict(name="KURŞUN YAĞMURU", icon="target", color=(230, 90, 100), cd=18.0,
                          kind="nova", mode="auto", n=22, mult=0.7,
                          desc="İki namludan 22 kurşunu her yöne boşaltır."),
    "pink_dream": dict(name="RÜYA PATLAMASI", icon="heart", color=(255, 140, 210), cd=20.0,
                       kind="dream", mode="auto", radius=300, duration=6.0,
                       desc="Azami canının %25'ini yeniler, 6 saniye kritik şansın %25 artar ve "
                            "çevredeki düşmanlar korkup kaçar."),
}

# Ortak kural: her yetenek düşmanları bu kadar süre dondurur.
ULT_FREEZE_ON_CAST = 0.5


def get_skin_ult(skin_id):
    return SKIN_ULTS.get(skin_id)


# =====================================================================
# KIYAFETLER  (kozmetik giysi — şapka / gözlük / pelerin, herhangi bir
# skin ile birlikte giyilebilir, elmasla alınır)
# =====================================================================

COSMETICS = [
    # ---- ŞAPKA (12) ----
    dict(id="cap_red", slot="hat", name="Kırmızı Şapka", cost=80,
         color=(210, 60, 60), accent=(255, 210, 90),
         desc="Basit ama şık, siperlikli bir spor şapka.",
         perk_text="Hareket Hızı +5", perk_add=dict(base_speed=5)),
    dict(id="wizard_hat", slot="hat", name="Büyücü Şapkası", cost=260,
         color=(90, 60, 150), accent=(230, 200, 255),
         desc="Sivri uçlu, ucu parıldayan gizemli bir büyücü şapkası.",
         perk_text="Deneyim Kazancı +%6", perk_add=dict(xp_mult=0.06)),
    dict(id="crown_gold", slot="hat", name="Altın Taç", cost=420,
         color=(232, 186, 90), accent=(255, 250, 210),
         desc="Gerçek bir hükümdar gibi parla, tacınla göz doldur.",
         perk_text="Altın Kazancı +%8", perk_add=dict(coin_mult=0.08)),
    dict(id="halo_ring", slot="hat", name="Melek Halesi", cost=520,
         color=(255, 245, 190), accent=(255, 255, 255),
         desc="Başının üstünde yumuşak, nabız gibi atan bir ışık halesi.",
         perk_text="Can Yenilenmesi +0.3/sn", perk_add=dict(base_regen=0.3)),
    dict(id="beanie_gray", slot="hat", name="Gri Bere", cost=70,
         color=(110, 112, 128), accent=(210, 212, 226),
         desc="Sade, rahat, sokak stili gri bir bere.",
         perk_text="Altın Kazancı +%3", perk_add=dict(coin_mult=0.03)),
    dict(id="viking_helm", slot="hat", name="Viking Miğferi", cost=340,
         color=(140, 100, 60), accent=(220, 225, 235),
         desc="Boynuzlu, ağır ve sağlam bir savaşçı miğferi.",
         perk_text="Can +15", perk_add=dict(base_max_hp=15)),
    dict(id="ninja_hood", slot="hat", name="Ninja Kukuletası", cost=300,
         color=(35, 36, 48), accent=(150, 60, 70),
         desc="Sessiz adımlar için sıkı sarılmış bir kukuleta.",
         perk_text="Dash Mesafesi +%8", perk_add=dict(dash_dist_mult=0.08)),
    dict(id="flower_crown", slot="hat", name="Çiçek Tacı", cost=260,
         color=(240, 170, 200), accent=(255, 240, 200),
         desc="Rengarenk küçük çiçeklerden örülmüş bir taç.",
         perk_text="Can Yenilenmesi +0.2/sn", perk_add=dict(base_regen=0.2)),
    dict(id="top_hat", slot="hat", name="Silindir Şapka", cost=380,
         color=(24, 24, 30), accent=(232, 186, 90),
         desc="Şık, kurdeleli klasik bir silindir şapka.",
         perk_text="Deneyim Kazancı +%5", perk_add=dict(xp_mult=0.05)),
    dict(id="dragon_horns", slot="hat", name="Ejderha Boynuzu", cost=560,
         color=(200, 50, 40), accent=(255, 170, 60),
         desc="Pullu, kavisli bir çift ejderha boynuzu.",
         perk_text="BONK Hasarı +%6", perk_add=dict(bonk_mult=0.06)),
    dict(id="space_helmet", slot="hat", name="Uzay Kaskı", cost=640,
         color=(200, 210, 225), accent=(120, 200, 255),
         desc="Camı yıldızları yansıtan bir astronot kaskı.",
         perk_text="Zırh +%3", perk_add=dict(base_armor=0.03)),
    dict(id="pink_bow", slot="hat", name="Pembe Fiyonk", cost=300,
         color=(255, 110, 190), accent=(255, 210, 235),
         desc="Baştan tırnağa pembe görünüm için tatlı bir fiyonk.",
         perk_text="Kritik Şans +%3", perk_add=dict(crit_chance=0.03)),

    # ---- GÖZLÜK (12) ----
    dict(id="shades", slot="eyewear", name="Güneş Gözlüğü", cost=90,
         color=(20, 22, 30), accent=(120, 180, 255),
         desc="Havalı, koyu camlı klasik bir gözlük.",
         perk_text="Kritik Şans +%3", perk_add=dict(crit_chance=0.03)),
    dict(id="goggles", slot="eyewear", name="Pilot Gözlüğü", cost=150,
         color=(120, 90, 60), accent=(255, 210, 120),
         desc="Kalın çerçeveli, sağlam koruyucu gözlük.",
         perk_text="Zırh +%2", perk_add=dict(base_armor=0.02)),
    dict(id="monocle", slot="eyewear", name="Tekgöz Monokl", cost=220,
         color=(200, 170, 90), accent=(255, 250, 220),
         desc="Zarif, biraz da kibirli görünen tek camlı monokl.",
         perk_text="Deneyim Kazancı +%4", perk_add=dict(xp_mult=0.04)),
    dict(id="visor", slot="eyewear", name="Siber Vizör", cost=340,
         color=(20, 200, 220), accent=(180, 255, 255),
         desc="Tek parça, sürekli parıldayan neon bir vizör.",
         perk_text="Mermi Hızı +%8", perk_add=dict(proj_speed_mult=0.08)),
    dict(id="round_glasses", slot="eyewear", name="Yuvarlak Gözlük", cost=60,
         color=(60, 50, 40), accent=(255, 240, 210),
         desc="Küçük, yuvarlak, sakin görünen bir gözlük.",
         perk_text="Toplama Menzili +8", perk_add=dict(base_pickup=8)),
    dict(id="heart_glasses", slot="eyewear", name="Kalp Gözlük", cost=200,
         color=(230, 60, 110), accent=(255, 200, 215),
         desc="Camları kalp şeklinde, sevimli bir gözlük.",
         perk_text="Altın Kazancı +%3", perk_add=dict(coin_mult=0.03)),
    dict(id="steampunk_goggles", slot="eyewear", name="Steampunk Gözlük", cost=310,
         color=(150, 110, 55), accent=(255, 200, 110),
         desc="Pirinç detaylı, dişlilerle süslü bir gözlük.",
         perk_text="Mermi Hızı +%5", perk_add=dict(proj_speed_mult=0.05)),
    dict(id="ski_mask", slot="eyewear", name="Kayak Gözlüğü", cost=250,
         color=(40, 130, 200), accent=(220, 245, 255),
         desc="Geniş camlı, sağlam bir kayak gözlüğü.",
         perk_text="Hasar Alma -%2", perk_add=dict(dmg_taken_mult=-0.02)),
    dict(id="laser_visor", slot="eyewear", name="Lazer Vizör", cost=420,
         color=(180, 20, 30), accent=(255, 90, 90),
         desc="Kızıl bir çizgi halinde parlayan taktik vizör.",
         perk_text="Kritik Hasar +%5", perk_add=dict(crit_dmg_mult=0.05)),
    dict(id="blindfold", slot="eyewear", name="Kör Bandı", cost=480,
         color=(30, 28, 26), accent=(120, 30, 40),
         desc="Görmeden savaşan bir dövüşçünün bandı.",
         perk_text="Kritik Şans +%5", perk_add=dict(crit_chance=0.05)),
    dict(id="star_glasses", slot="eyewear", name="Yıldız Gözlük", cost=360,
         color=(90, 70, 180), accent=(255, 235, 150),
         desc="Yıldız şeklinde çerçeveli parlak bir gözlük.",
         perk_text="BONK Yarıçapı +%5", perk_add=dict(bonk_radius_mult=0.05)),
    dict(id="pink_shades", slot="eyewear", name="Pembe Güneş Gözlüğü", cost=260,
         color=(255, 120, 190), accent=(255, 220, 235),
         desc="Tam pembe görünüm setini tamamlayan gözlük.",
         perk_text="Hareket Hızı +8", perk_add=dict(base_speed=8)),

    # ---- PELERİN (12) ----
    dict(id="cape_red", slot="cape", name="Kızıl Pelerin", cost=180,
         color=(190, 40, 50), accent=(255, 150, 130),
         desc="Rüzgârda dalgalanan klasik bir kahraman pelerini.",
         perk_text="BONK Hasarı +%4", perk_add=dict(bonk_mult=0.04)),
    dict(id="cape_royal", slot="cape", name="Asil Pelerin", cost=460,
         color=(120, 70, 190), accent=(255, 215, 110),
         desc="Altın işlemeli, ağır ve gösterişli bir asalet pelerini.",
         perk_text="Altın Kazancı +%5", perk_add=dict(coin_mult=0.05)),
    dict(id="cape_shadow", slot="cape", name="Gölge Pelerini", cost=520,
         color=(30, 26, 46), accent=(170, 110, 255),
         desc="Kenarları karanlık dumana dönüşen esrarengiz bir pelerin.",
         perk_text="Dash Mesafesi +%10", perk_add=dict(dash_dist_mult=0.10)),
    dict(id="wings_angelic", slot="cape", name="Melek Kanatları", cost=900,
         color=(255, 250, 240), accent=(255, 225, 140),
         desc="Sırtından açılan, ışıltılı gerçek bir çift melek kanadı.",
         perk_text="Can +25, Can Yenilenmesi +0.3/sn", perk_add=dict(base_max_hp=25, base_regen=0.3)),
    dict(id="cape_forest", slot="cape", name="Orman Pelerini", cost=150,
         color=(60, 130, 75), accent=(200, 240, 190),
         desc="Yapraklarla işlenmiş doğal, sessiz bir pelerin.",
         perk_text="Can Yenilenmesi +0.2/sn", perk_add=dict(base_regen=0.2)),
    dict(id="cape_ice", slot="cape", name="Buz Pelerini", cost=300,
         color=(150, 210, 245), accent=(255, 255, 255),
         desc="Kenarları donmuş, soğuk buhar saçan bir pelerin.",
         perk_text="Dash Bekleme Süresi -%5", perk_add=dict(dash_cd_mult=-0.05)),
    dict(id="cape_flame", slot="cape", name="Alev Pelerini", cost=400,
         color=(230, 100, 40), accent=(255, 210, 100),
         desc="Uçları sürekli tütüp közleşen ateşten bir pelerin.",
         perk_text="BONK Hasarı +%5", perk_add=dict(bonk_mult=0.05)),
    dict(id="cape_storm", slot="cape", name="Fırtına Pelerini", cost=520,
         color=(80, 100, 200), accent=(220, 230, 255),
         desc="İçinde küçük şimşekler çakan bir fırtına pelerini.",
         perk_text="Mermi Hızı +%6", perk_add=dict(proj_speed_mult=0.06)),
    dict(id="cape_starlight", slot="cape", name="Yıldız Işığı Pelerini", cost=600,
         color=(120, 90, 200), accent=(255, 245, 200),
         desc="Üzerinde küçük yıldızların kaydığı gece rengi bir pelerin.",
         perk_text="Deneyim Kazancı +%6", perk_add=dict(xp_mult=0.06)),
    dict(id="cape_bat", slot="cape", name="Yarasa Pelerini", cost=340,
         color=(45, 40, 55), accent=(150, 60, 200),
         desc="Kenarları yarasa kanadı gibi kesilmiş bir pelerin.",
         perk_text="Dash Mesafesi +%6", perk_add=dict(dash_dist_mult=0.06)),
    dict(id="cape_gold_trim", slot="cape", name="Altın Kenarlı Pelerin", cost=700,
         color=(40, 42, 60), accent=(232, 186, 90),
         desc="Kenarları altın işlemeli, gösterişli bir pelerin.",
         perk_text="Altın Kazancı +%6", perk_add=dict(coin_mult=0.06)),
    dict(id="cape_pink", slot="cape", name="Pembe Pelerin", cost=320,
         color=(255, 120, 190), accent=(255, 220, 235),
         desc="Tam pembe görünüm setini tamamlayan pelerin.",
         perk_text="Can +10", perk_add=dict(base_max_hp=10)),

    # ---- EK RENK SEÇENEKLERİ -------------------------------------------
    # Her slotta daha geniş bir renk yelpazesi olsun diye eklenen parçalar.
    dict(id="cap_blue", slot="hat", name="Mavi Kasket", cost=90,
         color=(60, 120, 230), accent=(190, 220, 255),
         desc="Derin mavi, dikişleri belirgin sade bir kasket.",
         perk_text="Mermi Hızı +%4", perk_add=dict(proj_speed_mult=0.04)),
    dict(id="leaf_crown", slot="hat", name="Yaprak Tacı", cost=120,
         color=(70, 160, 85), accent=(205, 245, 195),
         desc="Taze yapraklardan örülmüş, ormanın kendi tacı.",
         perk_text="Toplama Menzili +10", perk_add=dict(base_pickup=10)),
    dict(id="neon_headband", slot="hat", name="Neon Bandana", cost=220,
         color=(60, 220, 215), accent=(225, 255, 255),
         desc="Karanlıkta parlayan turkuaz bir koşu bandanası.",
         perk_text="Dash Bekleme Süresi -%4", perk_add=dict(dash_cd_mult=-0.04)),
    dict(id="ember_horns", slot="hat", name="Köz Boynuzu", cost=280,
         color=(240, 130, 50), accent=(255, 220, 130),
         desc="Uçları hâlâ közlenen, sıcak turuncu boynuzlar.",
         perk_text="BONK Yarıçapı +%6", perk_add=dict(bonk_radius_mult=0.06)),

    # ---- AĞIR KASKLAR -------------------------------------------------
    # Bu dört parça "kafalık" sınıfının üst segmenti: hepsi canlı, yani
    # üzerlerinde sürekli hareket eden bir efekt taşır (alev yelesi, dönen
    # runeler, kayan renkler, uçuşan ruhlar).
    dict(id="dragon_helm", slot="hat", name="Ejderha Kaskı", cost=520,
         color=(196, 62, 48), accent=(255, 186, 74),
         desc="Sırtında yanan bir alev yelesi taşıyan, gözleri kor gibi parlayan ejderha kaskı.",
         perk_text="Hasar +%6", perk_add=dict(run_dmg_mult=0.06)),
    dict(id="immortal_helm", slot="hat", name="Ölümsüz Miğfer", cost=760,
         color=(214, 176, 86), accent=(255, 246, 198),
         desc="Çevresinde ölümsüzlük runeleri döner. Hiç paslanmaz, hiç kırılmaz.",
         perk_text="Zırh +%6, Can +20", perk_add=dict(base_armor=0.06, base_max_hp=20)),
    dict(id="nightmare_helm", slot="hat", name="Kâbus Miğferi", cost=620,
         color=(74, 48, 104), accent=(190, 120, 255),
         desc="Mor alevler saçar, ardında kaybolan ruhlar bırakır.",
         perk_text="Hareket Hızı +12", perk_add=dict(base_speed=12)),
    dict(id="crystal_helm", slot="hat", name="Kristal Kask", cost=680,
         color=(120, 210, 235), accent=(255, 255, 255),
         desc="Işığı kırarak sürekli renk değiştiren, saydam kristal kask.",
         perk_text="Kritik Şans +%5", perk_add=dict(crit_chance=0.05)),

    dict(id="leaf_visor", slot="eyewear", name="Yaprak Vizör", cost=140,
         color=(80, 180, 100), accent=(215, 250, 205),
         desc="Yaprak damarlarını andıran ince yeşil bir vizör.",
         perk_text="Can Yenilenmesi +0.2/sn", perk_add=dict(base_regen=0.2)),
    dict(id="frost_lens", slot="eyewear", name="Buz Lensi", cost=260,
         color=(225, 240, 255), accent=(255, 255, 255),
         desc="Buzdan yontulmuş, kenarları kırağı tutan berrak bir lens.",
         perk_text="Hasar Alma -%2", perk_add=dict(dmg_taken_mult=-0.02)),
    dict(id="ember_shades", slot="eyewear", name="Köz Gözlüğü", cost=230,
         color=(245, 140, 60), accent=(255, 225, 150),
         desc="Camları için için yanan turuncu bir gözlük.",
         perk_text="Kritik Hasar +%4", perk_add=dict(crit_dmg_mult=0.04)),

    dict(id="cape_steel", slot="cape", name="Çelik Pelerin", cost=290,
         color=(120, 128, 145), accent=(235, 240, 250),
         desc="Dövülmüş çelik plakalardan örülmüş ağır bir pelerin.",
         perk_text="Zırh +%3", perk_add=dict(base_armor=0.03)),
]
COSMETIC_BY_ID = {c["id"]: c for c in COSMETICS}
COSMETIC_SLOTS = ["hat", "eyewear", "cape"]
SLOT_LABELS = {"hat": "ŞAPKA", "eyewear": "GÖZLÜK", "cape": "PELERİN"}


def cosmetics_by_slot(slot):
    return [c for c in COSMETICS if c["slot"] == slot]


def _player_cosmetic(p, slot):
    cm = getattr(p, "cosmetics", None)
    if not cm:
        return None
    return COSMETIC_BY_ID.get(cm.get(slot))


def draw_cosmetic_cape(surf, p, px, py, t):
    """Pelerin — gövdenin ARKASINDA çizilir, harekete göre dalgalanır."""
    item = _player_cosmetic(p, "cape")
    if not item:
        return
    r = p.radius
    ax, ay = p.aim_dir
    bx, by = -ax, -ay
    if abs(bx) < 1e-3 and abs(by) < 1e-3:
        bx, by = 0.0, 1.0
    nx, ny = -by, bx
    col, acc = item["color"], item["accent"]
    if item["id"] == "wings_angelic":
        # MELEK KANADI: her kanat üç sıra tüyden oluşur (uzun uçuş tüyleri,
        # orta sıra, omuzdaki kısa örtü tüyleri). Kanatlar birlikte çırpar,
        # arkalarında yumuşak bir hale ve süzülen tüy parçacıkları bırakır.
        flap = math.sin(t * 5.0)
        open_amt = 0.92 + flap * 0.22          # çırpma: açılıp kapanma
        base_ang = math.atan2(by, bx)
        sx, sy = px + bx * r * 0.28, py + by * r * 0.28
        add_glow(surf, sx + bx * r * 0.5, sy + by * r * 0.5, r * 2.2, acc,
                 .26 + .08 * math.sin(t * 3))

        def feather(cx0, cy0, ang_, length, width, fill, edge):
            """Tek bir tüy: uçta sivrilen, dipte yuvarlak bir yaprak."""
            dxf, dyf = math.cos(ang_), math.sin(ang_)
            nxf, nyf = -dyf, dxf
            pts = [
                (cx0, cy0),
                (cx0 + dxf * length * 0.35 + nxf * width, cy0 + dyf * length * 0.35 + nyf * width),
                (cx0 + dxf * length * 0.78 + nxf * width * 0.72,
                 cy0 + dyf * length * 0.78 + nyf * width * 0.72),
                (cx0 + dxf * length, cy0 + dyf * length),
                (cx0 + dxf * length * 0.78 - nxf * width * 0.52,
                 cy0 + dyf * length * 0.78 - nyf * width * 0.52),
                (cx0 + dxf * length * 0.35 - nxf * width * 0.62,
                 cy0 + dyf * length * 0.35 - nyf * width * 0.62),
            ]
            pygame.draw.polygon(surf, OUTLINE, [(a + bx, b + by) for a, b in pts])
            pygame.draw.polygon(surf, fill, pts)
            pygame.draw.polygon(surf, edge, pts, 1)
            # tüy sapı
            pygame.draw.line(surf, edge, (cx0 + dxf * length * 0.12, cy0 + dyf * length * 0.12),
                             (cx0 + dxf * length * 0.92, cy0 + dyf * length * 0.92), 1)

        base_white = lighten(col, 0.42)
        for side in (-1, 1):
            # --- 1. sıra: uzun uçuş tüyleri (en arkada) ---
            for i in range(5):
                f = i / 4.0
                a = base_ang + side * (0.42 + open_amt * (0.26 + f * 0.62))
                L = r * (2.55 - f * 0.55)
                feather(sx, sy, a, L, r * 0.26, base_white, scale_col(acc, 0.85))
            # --- 2. sıra: orta tüyler ---
            for i in range(4):
                f = i / 3.0
                a = base_ang + side * (0.50 + open_amt * (0.22 + f * 0.52))
                L = r * (1.62 - f * 0.34)
                feather(sx, sy, a, L, r * 0.24, lighten(col, 0.62), scale_col(acc, 0.7))
            # --- 3. sıra: omuzdaki kısa örtü tüyleri ---
            for i in range(3):
                f = i / 2.0
                a = base_ang + side * (0.58 + open_amt * (0.18 + f * 0.40))
                L = r * (0.92 - f * 0.18)
                feather(sx, sy, a, L, r * 0.22, WHITE, acc)
            # omuz eklemi
            jx, jy = sx + math.cos(base_ang + side * 0.55) * r * 0.30,                      sy + math.sin(base_ang + side * 0.55) * r * 0.30
            pygame.draw.circle(surf, OUTLINE, (int(jx), int(jy)), max(3, int(r * 0.20)))
            pygame.draw.circle(surf, WHITE, (int(jx), int(jy)), max(2, int(r * 0.16)))
            pygame.draw.circle(surf, acc, (int(jx), int(jy)), max(2, int(r * 0.16)), 1)

        # süzülen tüy parçacıkları
        for i in range(3):
            ph = (t * 0.5 + i * 0.33) % 1.0
            fxp = sx + bx * r * (0.7 + ph * 1.5) + nx * math.sin(t * 1.6 + i * 2.1) * r * 1.1
            fyp = sy + by * r * (0.7 + ph * 1.5) + ny * math.sin(t * 1.6 + i * 2.1) * r * 1.1
            pygame.draw.circle(surf, lighten(acc, 0.5), (int(fxp), int(fyp)),
                               max(1, int(2.4 * (1.0 - ph))))
    else:
        sway = math.sin(t * 4.5 + px * 0.02) * 7
        base_x, base_y = px + bx * r * 0.25, py + by * r * 0.25
        top_l = (base_x + nx * r * 0.85, base_y + ny * r * 0.85)
        top_r = (base_x - nx * r * 0.85, base_y - ny * r * 0.85)
        tip_l = (top_l[0] + bx * (30 + sway), top_l[1] + by * (30 + sway))
        tip_r = (top_r[0] + bx * (30 - sway), top_r[1] + by * (30 - sway))
        mid = (base_x + bx * (34 + sway * 0.5), base_y + by * (34 + sway * 0.5))
        pts = [top_l, tip_l, mid, tip_r, top_r]
        pygame.draw.polygon(surf, OUTLINE, [(x_, y_ + 2) for x_, y_ in pts])
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.polygon(surf, acc, pts, 2)
        if item["id"] == "cape_shadow":
            add_glow(surf, mid[0], mid[1], r * 1.5, acc, .3)
        elif item["id"] == "cape_royal":
            pygame.draw.line(surf, acc, top_l, mid, 1)
            pygame.draw.line(surf, acc, top_r, mid, 1)


def draw_cosmetic_hat(surf, p, px, py, t):
    """Şapka — kafanın ÜSTÜNDE, gövdeden sonra çizilir.

    Her şapkanın kendine ait bir silueti var; hiçbiri "genel görünüm"e
    düşmüyor. Ortak görsel dil: koyu bir taban gölgesi (OUTLINE), ana renk,
    sol üstten gelen ışık için lighten() ile bir parlama ve accent rengiyle
    küçük bir detay (taş, düğme, kor, pırıltı).
    """
    item = _player_cosmetic(p, "hat")
    if not item:
        return
    r = p.radius
    col, acc = item["color"], item["accent"]
    dark = scale_col(col, 0.62)
    lite = lighten(col, 0.34)

    if item["id"] == "cap_red":
        # Klasik beyzbol şapkası: siperlik tacın ön kenarından çıkar ve
        # nişan yönüne döner (kopuk bir yuvarlak değil, gerçek bir siperlik).
        cy = py - r * 0.58
        ax, ay = p.aim_dir
        ang = math.atan2(ay, ax)
        ca, sa = math.cos(ang), math.sin(ang)
        visor_local = [(r * 0.05, -r * 0.52), (r * 0.78, -r * 0.42), (r * 1.20, -r * 0.15),
                       (r * 1.20, r * 0.15), (r * 0.78, r * 0.42), (r * 0.05, r * 0.52)]
        vpts = [(px + lx * ca - ly * sa, cy + r * 0.26 + lx * sa + ly * ca) for lx, ly in visor_local]
        pygame.draw.polygon(surf, OUTLINE, [(x_, y_ + 2) for x_, y_ in vpts])
        pygame.draw.polygon(surf, dark, vpts)
        pygame.draw.line(surf, scale_col(col, 0.88), vpts[1], vpts[2], 2)
        pygame.draw.circle(surf, OUTLINE, (int(px), int(cy)), int(r * 0.77))
        pygame.draw.circle(surf, col, (int(px), int(cy)), int(r * 0.72))
        seam = pygame.Rect(int(px - r * 0.72), int(cy - r * 0.72), int(r * 1.44), int(r * 1.44))
        pygame.draw.arc(surf, dark, seam, 0.55, 2.60, 2)
        pygame.draw.circle(surf, lite, (int(px - r * 0.26), int(cy - r * 0.32)), max(2, int(r * 0.22)))
        pygame.draw.circle(surf, OUTLINE, (int(px), int(cy - r * 0.68)), max(3, int(r * 0.13)))
        pygame.draw.circle(surf, acc, (int(px), int(cy - r * 0.68)), max(2, int(r * 0.10)))

    elif item["id"] == "cap_blue":
        # Düz siperlikli "snapback": kırmızı şapkadan belirgin biçimde farklı,
        # köşeli bir taç ve geniş düz siperlik.
        cy = py - r * 0.60
        ax, ay = p.aim_dir
        ang = math.atan2(ay, ax)
        ca, sa = math.cos(ang), math.sin(ang)
        # düz, geniş ve köşeli siperlik — tacın ön alt kenarına yapışık
        visor_local = [(0.0, -r * 0.56), (r * 1.26, -r * 0.44), (r * 1.28, r * 0.44),
                       (0.0, r * 0.56)]
        vpts = [(px + lx * ca - ly * sa, cy + r * 0.40 + lx * sa + ly * ca) for lx, ly in visor_local]
        pygame.draw.polygon(surf, OUTLINE, [(x_, y_ + 2) for x_, y_ in vpts])
        pygame.draw.polygon(surf, dark, vpts)
        pygame.draw.line(surf, lighten(col, 0.18), vpts[0], vpts[1], 2)
        crown = pygame.Rect(int(px - r * 0.62), int(cy - r * 0.64), int(r * 1.24), int(r * 1.10))
        pygame.draw.rect(surf, OUTLINE, crown.inflate(4, 4), border_radius=max(4, int(r * 0.34)))
        pygame.draw.rect(surf, col, crown, border_radius=max(4, int(r * 0.34)))
        pygame.draw.line(surf, dark, (int(px), crown.y + 4), (int(px), crown.bottom - 4), 2)
        pygame.draw.rect(surf, lite, (crown.x + 4, crown.y + 4, max(3, int(r * 0.40)), max(3, int(r * 0.28))),
                         border_radius=3)
        pygame.draw.circle(surf, acc, (int(px), int(crown.y + 1)), max(2, int(r * 0.10)))

    elif item["id"] == "wizard_hat":
        # Ucu hafif kıvrık külah + yıldızlı bant.
        by = py - r - 2
        tip_sway = math.sin(t * 1.6) * 3.0
        tip = (px + 4 + tip_sway, by - 32)
        mid = (px + 1, by - 14)
        left, right = (px - 15, by + 6), (px + 15, by + 6)
        pts = [left, right, tip, mid]
        pygame.draw.polygon(surf, OUTLINE, [(x_, y_ + 2) for x_, y_ in pts])
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.polygon(surf, dark, [mid, tip, (tip[0] - 4, tip[1] + 4)])
        pygame.draw.line(surf, lite, left, (tip[0] - 2, tip[1] + 3), 2)
        band = pygame.Rect(int(px - 16), int(by - 2), 32, max(4, int(r * 0.22)))
        pygame.draw.rect(surf, OUTLINE, band.inflate(2, 2), border_radius=3)
        pygame.draw.rect(surf, dark, band, border_radius=3)
        pygame.draw.ellipse(surf, OUTLINE, (int(px - 18), int(by + 1), 36, 10))
        pygame.draw.ellipse(surf, col, (int(px - 17), int(by + 2), 34, 8))
        pygame.draw.ellipse(surf, lite, (int(px - 15), int(by + 3), 30, 3))
        add_glow(surf, tip[0], tip[1] + 2, 12, acc, .55 + .18 * math.sin(t * 5))
        pygame.draw.circle(surf, acc, (int(tip[0]), int(tip[1] + 2)), 3)
        for i in range(3):
            sx = px - 10 + i * 10
            sy = by - 1 + (i % 2) * 3
            tw = 1 + max(0.0, math.sin(t * 4 + i * 2.1)) * 1.6
            pygame.draw.circle(surf, acc, (int(sx), int(sy)), int(tw))

    elif item["id"] == "crown_gold":
        # Beş uçlu taç: uçlarda taşlar, altta kalın bant.
        by = py - r - 3
        pts = [(px - 13, by + 9), (px - 13, by - 1), (px - 6, by + 6), (px, by - 9),
               (px + 6, by + 6), (px + 13, by - 1), (px + 13, by + 9)]
        pygame.draw.polygon(surf, OUTLINE, [(x_, y_ + 2) for x_, y_ in pts])
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.polygon(surf, acc, pts, 1)
        band = pygame.Rect(int(px - 14), int(by + 7), 28, max(4, int(r * 0.24)))
        pygame.draw.rect(surf, OUTLINE, band.inflate(2, 2), border_radius=2)
        pygame.draw.rect(surf, dark, band, border_radius=2)
        pygame.draw.line(surf, lite, (band.x + 2, band.y + 1), (band.right - 2, band.y + 1), 1)
        gems = ((px, by - 6, (230, 60, 90)), (px - 13, by - 1, (90, 190, 255)), (px + 13, by - 1, (120, 235, 150)))
        for gx, gy, gc in gems:
            pygame.draw.circle(surf, OUTLINE, (int(gx), int(gy)), 3)
            pygame.draw.circle(surf, gc, (int(gx), int(gy)), 2)
        add_glow(surf, px, by, 18, col, .40 + .18 * math.sin(t * 3.4))

    elif item["id"] == "halo_ring":
        # Çift halka + yumuşak nabız; hafifçe süzülür.
        bob = math.sin(t * 2.0) * 1.8
        hy = py - r - 16 + bob
        add_glow(surf, px, hy, 22, col, .5 + .14 * math.sin(t * 4))
        pygame.draw.ellipse(surf, scale_col(acc, 0.55), (int(px - 18), int(hy - 5), 36, 11), 3)
        pygame.draw.ellipse(surf, acc, (int(px - 16), int(hy - 4), 32, 9), 2)
        pygame.draw.ellipse(surf, lighten(acc, 0.5), (int(px - 12), int(hy - 3), 24, 4), 1)
        for i in range(3):
            a = t * 1.4 + i * math.tau / 3
            sx = px + math.cos(a) * 17
            sy = hy + math.sin(a) * 4.5
            pygame.draw.circle(surf, acc, (int(sx), int(sy)), 1 + int(max(0.0, math.sin(t * 5 + i)) * 1.5))

    elif item["id"] == "beanie_gray":
        # Örgü bere: dokulu gövde, katlı bant ve ponpon.
        cy = py - r * 0.64
        pygame.draw.circle(surf, OUTLINE, (int(px), int(cy)), int(r * 0.74))
        pygame.draw.circle(surf, col, (int(px), int(cy)), int(r * 0.69))
        for i in range(-2, 3):
            kx = px + i * r * 0.24
            pygame.draw.line(surf, dark, (int(kx), int(cy - r * 0.55)), (int(kx), int(cy + r * 0.34)), 1)
        pygame.draw.circle(surf, lite, (int(px - r * 0.26), int(cy - r * 0.30)), max(2, int(r * 0.20)))
        band = pygame.Rect(0, 0, int(r * 1.48), int(r * 0.34))
        band.center = (int(px), int(cy + r * 0.44))
        pygame.draw.ellipse(surf, OUTLINE, band.inflate(3, 3))
        pygame.draw.ellipse(surf, dark, band)
        pygame.draw.ellipse(surf, lighten(col, 0.18), (band.x + 2, band.y + 1, band.w - 4, max(2, band.h // 2)))
        pom = (int(px), int(cy - r * 0.78 + math.sin(t * 2.4) * 1.2))
        pygame.draw.circle(surf, OUTLINE, pom, max(4, int(r * 0.20)))
        pygame.draw.circle(surf, acc, pom, max(3, int(r * 0.17)))
        pygame.draw.circle(surf, lighten(acc, 0.4), (pom[0] - 1, pom[1] - 1), max(1, int(r * 0.07)))

    elif item["id"] == "viking_helm":
        # Miğfer + burun koruması + kıvrık boynuzlar + perçinler.
        cy = py - r * 0.60
        pygame.draw.circle(surf, OUTLINE, (int(px), int(cy)), int(r * 0.70))
        pygame.draw.circle(surf, col, (int(px), int(cy)), int(r * 0.64))
        pygame.draw.circle(surf, lite, (int(px - r * 0.24), int(cy - r * 0.28)), max(2, int(r * 0.18)))
        rim = pygame.Rect(0, 0, int(r * 1.32), int(r * 0.26))
        rim.center = (int(px), int(cy + r * 0.40))
        pygame.draw.ellipse(surf, OUTLINE, rim.inflate(3, 3))
        pygame.draw.ellipse(surf, dark, rim)
        pygame.draw.rect(surf, OUTLINE, (int(px - 4), int(cy - r * 0.08), 8, int(r * 0.72)))
        pygame.draw.rect(surf, dark, (int(px - 3), int(cy - r * 0.08), 6, int(r * 0.70)))
        for s in (-1, 1):
            pygame.draw.circle(surf, dark, (int(px + s * r * 0.40), int(cy + r * 0.20)), max(2, int(r * 0.08)))
            hx0 = px + s * r * 0.52
            hy0 = cy - r * 0.16
            pts = [(hx0, hy0 + 4),
                   (hx0 + s * 7, hy0 - 12),
                   (hx0 + s * 19, hy0 - 19),
                   (hx0 + s * 15, hy0 - 8),
                   (hx0 + s * 17, hy0 + 2),
                   (hx0 + s * 7, hy0 + 6)]
            pygame.draw.polygon(surf, OUTLINE, [(x_ + s, y_ + 1) for x_, y_ in pts])
            pygame.draw.polygon(surf, acc, pts)
            pygame.draw.polygon(surf, scale_col(acc, 0.7), pts, 1)
            pygame.draw.line(surf, scale_col(acc, 0.72), (hx0 + s * 8, hy0 - 10), (hx0 + s * 15, hy0 - 14), 1)

    elif item["id"] == "ninja_hood":
        # Kukuleta + göz açıklığı bandı + arkada uçuşan kuşak.
        cy = py - r * 0.55
        tail = math.sin(t * 2.6) * r * 0.18
        pts = [(px - r * 0.78, cy + r * 0.38), (px - r * 0.62, cy - r * 0.58),
               (px, cy - r * 0.90), (px + r * 0.62, cy - r * 0.58), (px + r * 0.78, cy + r * 0.38)]
        pygame.draw.polygon(surf, OUTLINE, [(x_, y_ + 2) for x_, y_ in pts])
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.polygon(surf, lighten(col, 0.22),
                            [(px - r * 0.52, cy - r * 0.40), (px, cy - r * 0.82), (px + r * 0.06, cy - r * 0.46)])
        band = pygame.Rect(0, 0, int(r * 1.54), int(r * 0.30))
        band.center = (int(px), int(cy + r * 0.16))
        pygame.draw.ellipse(surf, OUTLINE, band.inflate(3, 3), 3)
        pygame.draw.ellipse(surf, acc, band, 2)
        kx, ky = px + r * 0.70, cy + r * 0.10
        pygame.draw.lines(surf, OUTLINE, False,
                          [(kx, ky), (kx + r * 0.30, ky + r * 0.22), (kx + r * 0.56, ky + r * 0.10 + tail)], 5)
        pygame.draw.lines(surf, acc, False,
                          [(kx, ky), (kx + r * 0.30, ky + r * 0.22), (kx + r * 0.56, ky + r * 0.10 + tail)], 2)

    elif item["id"] == "flower_crown":
        # Gerçek taç yapraklı çiçekler + aralarında küçük yeşil yapraklar.
        ring_y = py - r * 0.38
        rx, ry = r * 0.80, r * 0.38
        n = 6
        for i in range(n):
            ang = i * math.tau / n - math.pi / 2
            cxf = px + math.cos(ang) * rx
            cyf = ring_y + math.sin(ang) * ry
            if i % 2 == 1:
                lp = [(cxf, cyf + 3), (cxf + 5, cyf - 3), (cxf, cyf - 8), (cxf - 5, cyf - 3)]
                pygame.draw.polygon(surf, OUTLINE, [(x_, y_ + 1) for x_, y_ in lp])
                pygame.draw.polygon(surf, (110, 180, 110), lp)
                continue
            fc = acc if (i // 2) % 2 == 0 else lighten(col, 0.28)
            sway = math.sin(t * 2.2 + i) * 0.10
            for k in range(5):
                pa = k * math.tau / 5 + sway
                pygame.draw.circle(surf, OUTLINE,
                                   (int(cxf + math.cos(pa) * 4.2), int(cyf + math.sin(pa) * 4.2)), 4)
            for k in range(5):
                pa = k * math.tau / 5 + sway
                pygame.draw.circle(surf, fc,
                                   (int(cxf + math.cos(pa) * 4.2), int(cyf + math.sin(pa) * 4.2)), 3)
            pygame.draw.circle(surf, (255, 235, 120), (int(cxf), int(cyf)), 2)

    elif item["id"] == "top_hat":
        # Silindir şapka: hafif konik gövde, saten bant ve parlama.
        by = py - r - 4
        brim = pygame.Rect(0, 0, int(r * 1.78), int(r * 0.28))
        brim.center = (int(px), int(by))
        pygame.draw.ellipse(surf, OUTLINE, brim.inflate(4, 4))
        pygame.draw.ellipse(surf, col, brim)
        pygame.draw.ellipse(surf, lighten(col, 0.20), (brim.x + 3, brim.y + 1, brim.w - 6, max(2, brim.h // 2)))
        top_w, bot_w = r * 1.02, r * 0.94
        top_y = by - r * 1.22
        body = [(px - bot_w / 2, by), (px - top_w / 2, top_y),
                (px + top_w / 2, top_y), (px + bot_w / 2, by)]
        pygame.draw.polygon(surf, OUTLINE, [(x_, y_ + 1) for x_, y_ in body])
        pygame.draw.polygon(surf, col, body)
        pygame.draw.line(surf, lighten(col, 0.30), (px - bot_w / 2 + 3, by - 3), (px - top_w / 2 + 3, top_y + 3), 2)
        pygame.draw.ellipse(surf, OUTLINE, (int(px - top_w / 2), int(top_y - r * 0.13), int(top_w), int(r * 0.26)))
        pygame.draw.ellipse(surf, lighten(col, 0.12),
                            (int(px - top_w / 2 + 1), int(top_y - r * 0.11), int(top_w - 2), int(r * 0.22)))
        pygame.draw.rect(surf, acc, (int(px - bot_w / 2), int(by - r * 0.30), int(bot_w), max(3, int(r * 0.22))))
        pygame.draw.rect(surf, scale_col(acc, 0.7), (int(px - bot_w / 2), int(by - r * 0.30), int(bot_w), 1))

    elif item["id"] == "dragon_horns":
        # Boğumlu, sivrilen ejderha boynuzları.
        cy = py - r * 0.50
        for s in (-1, 1):
            hx0 = px + s * r * 0.36
            pts = [(hx0, cy + 2), (hx0 + s * 8, cy - 22), (hx0 + s * 21, cy - 31),
                   (hx0 + s * 14, cy - 15), (hx0 + s * 19, cy - 3)]
            pygame.draw.polygon(surf, OUTLINE, [(x_ + s, y_ + 1) for x_, y_ in pts])
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.polygon(surf, acc, pts, 1)
            for k in range(3):
                f = 0.22 + k * 0.22
                rx0 = hx0 + s * (8 * f + 4)
                ry0 = cy - 22 * f - 2
                pygame.draw.line(surf, scale_col(col, 0.65),
                                 (int(rx0), int(ry0)), (int(rx0 + s * 6), int(ry0 - 2)), 1)
            pygame.draw.circle(surf, lighten(acc, 0.35), (int(hx0 + s * 20), int(cy - 30)), 2)

    elif item["id"] == "ember_horns":
        # Kor boynuz: koyu gövde, içinde yanan çatlaklar ve yükselen kıvılcımlar.
        cy = py - r * 0.52
        pulse = .42 + .20 * math.sin(t * 4.2)
        for s in (-1, 1):
            bx0 = px + s * r * 0.40
            pts = [(bx0 - s * r * 0.16, cy + r * 0.12),
                   (bx0 + s * r * 0.08, cy - r * 0.50),
                   (bx0 + s * r * 0.46, cy - r * 0.94),
                   (bx0 + s * r * 0.30, cy - r * 0.42),
                   (bx0 + s * r * 0.24, cy + r * 0.08)]
            pygame.draw.polygon(surf, OUTLINE, [(x_ + s, y_ + 1) for x_, y_ in pts])
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.line(surf, acc, (int(bx0 + s * r * 0.02), int(cy - r * 0.08)),
                             (int(bx0 + s * r * 0.26), int(cy - r * 0.58)), 2)
            pygame.draw.line(surf, lighten(acc, 0.4), (int(bx0 + s * r * 0.14), int(cy - r * 0.34)),
                             (int(bx0 + s * r * 0.30), int(cy - r * 0.52)), 1)
            tipx, tipy = bx0 + s * r * 0.44, cy - r * 0.90
            add_glow(surf, tipx, tipy, r * 0.44, acc, pulse)
            pygame.draw.circle(surf, lighten(acc, 0.45), (int(tipx), int(tipy)), max(2, int(r * 0.09)))
        for i in range(3):
            exx = px + math.sin(t * 1.8 + i * 2.1) * r * 0.5
            eyy = cy - r * 0.95 - ((t * 22 + i * 13) % 18) * 0.5
            pygame.draw.circle(surf, acc, (int(exx), int(eyy)), 1)

    elif item["id"] == "space_helmet":
        # Cam küre + yansıma yayı + yanıp sönen anten.
        cy = py - r * 0.15
        pygame.draw.circle(surf, OUTLINE, (int(px), int(cy)), int(r * 1.06))
        pygame.draw.circle(surf, (30, 34, 46), (int(px), int(cy)), int(r * 0.99))
        glass = pygame.Rect(int(px - r * 0.99), int(cy - r * 0.99), int(r * 1.98), int(r * 1.98))
        pygame.draw.arc(surf, lighten(acc, 0.2), glass, 0.9, 2.2, 3)
        pygame.draw.circle(surf, col, (int(px), int(cy)), int(r * 0.99), 3)
        pygame.draw.circle(surf, acc, (int(px - r * 0.32), int(cy - r * 0.36)), max(2, int(r * 0.26)))
        pygame.draw.circle(surf, lighten(acc, 0.5), (int(px - r * 0.38), int(cy - r * 0.42)), max(1, int(r * 0.11)))
        neck = pygame.Rect(0, 0, int(r * 1.10), int(r * 0.26))
        neck.center = (int(px), int(cy + r * 0.96))
        pygame.draw.ellipse(surf, OUTLINE, neck.inflate(3, 3))
        pygame.draw.ellipse(surf, col, neck)
        ax0, ay0 = px + r * 0.62, cy - r * 0.72
        pygame.draw.line(surf, col, (int(ax0), int(ay0)), (int(ax0 + r * 0.22), int(ay0 - r * 0.40)), 2)
        blink = .35 + .45 * (0.5 + 0.5 * math.sin(t * 6))
        add_glow(surf, ax0 + r * 0.22, ay0 - r * 0.40, r * 0.30, (255, 90, 90), blink)
        pygame.draw.circle(surf, (255, 120, 120), (int(ax0 + r * 0.22), int(ay0 - r * 0.40)), max(2, int(r * 0.08)))
        add_glow(surf, px, cy, r * 1.32, acc, .16)

    elif item["id"] == "pink_bow":
        # Fiyonk: iki dolgun ilmek, ortada düğüm, aşağı sarkan iki kurdele.
        cy = py - r - 6
        sway = math.sin(t * 2.4) * 1.5
        for s in (-1, 1):
            loop = [(px + s * 3, cy),
                    (px + s * 12, cy - 11),
                    (px + s * 19, cy - 3),
                    (px + s * 14, cy + 8),
                    (px + s * 4, cy + 4)]
            pygame.draw.polygon(surf, OUTLINE, [(x_ + s, y_ + 1) for x_, y_ in loop])
            pygame.draw.polygon(surf, col, loop)
            pygame.draw.polygon(surf, lighten(col, 0.28),
                                [(px + s * 5, cy - 1), (px + s * 12, cy - 8), (px + s * 13, cy - 2)])
            rib = [(px + s * 4, cy + 3),
                   (px + s * 8, cy + 12 + sway * s),
                   (px + s * 13, cy + 18 + sway * s)]
            pygame.draw.lines(surf, OUTLINE, False, rib, 5)
            pygame.draw.lines(surf, dark, False, rib, 3)
        pygame.draw.circle(surf, OUTLINE, (int(px), int(cy)), 7)
        pygame.draw.circle(surf, acc, (int(px), int(cy)), 5)
        pygame.draw.circle(surf, lighten(acc, 0.45), (int(px - 2), int(cy - 2)), 2)

    elif item["id"] == "leaf_crown":
        # Sarmaşık tacı: halka boyunca dizilmiş, rüzgârda hafif sallanan yapraklar.
        ring_y = py - r * 0.42
        rx, ry = r * 0.86, r * 0.36
        vine = pygame.Rect(int(px - rx), int(ring_y - ry), int(rx * 2), int(ry * 2))
        pygame.draw.ellipse(surf, OUTLINE, vine.inflate(3, 3), 3)
        pygame.draw.ellipse(surf, scale_col(col, 0.55), vine, 2)
        n = 7
        for i in range(n):
            ang = i * math.tau / n - math.pi / 2
            lx = px + math.cos(ang) * rx
            ly = ring_y + math.sin(ang) * ry
            lean = (-0.6 if math.cos(ang) < 0 else 0.6) + math.sin(t * 2.2 + i) * 0.12
            ca, sa = math.cos(lean), math.sin(lean)
            leaf = [(0, 2), (5, -6), (0, -15), (-5, -6)]
            pts = [(lx + dx * ca - dy * sa, ly + dx * sa + dy * ca) for dx, dy in leaf]
            pygame.draw.polygon(surf, OUTLINE, [(x_, y_ + 1) for x_, y_ in pts])
            pygame.draw.polygon(surf, col if i % 2 == 0 else lighten(col, 0.26), pts)
            pygame.draw.line(surf, scale_col(col, 0.58), pts[0], pts[2], 1)
        for i in range(3):
            a = i * math.tau / 3 - math.pi / 2
            bxp = px + math.cos(a) * rx * 0.72
            byp = ring_y + math.sin(a) * ry * 0.72
            pygame.draw.circle(surf, OUTLINE, (int(bxp), int(byp)), 3)
            pygame.draw.circle(surf, acc, (int(bxp), int(byp)), 2)

    elif item["id"] == "neon_headband":
        # Alın bandı: içinde akan neon şerit ve arkada uçuşan iki uç.
        by = py - r * 0.52
        pulse = .50 + .28 * math.sin(t * 5.0)
        add_glow(surf, px, by, r * 0.98, acc, pulse * 0.55)
        band = pygame.Rect(0, 0, int(r * 1.64), int(r * 0.36))
        band.center = (int(px), int(by))
        pygame.draw.rect(surf, OUTLINE, band.inflate(4, 4), border_radius=max(3, int(r * 0.18)))
        pygame.draw.rect(surf, dark, band, border_radius=max(3, int(r * 0.18)))
        sh = max(2, int(r * 0.12))
        stripe = pygame.Rect(band.x + 3, band.centery - sh // 2, band.w - 6, sh)
        pygame.draw.rect(surf, acc, stripe, border_radius=2)
        pygame.draw.rect(surf, lighten(acc, 0.55), (stripe.x, stripe.y, stripe.w, 1))
        for i in range(4):
            nx = stripe.x + ((t * 28 + i * 16) % (stripe.w + 12)) - 6
            if stripe.x <= nx <= stripe.right:
                pygame.draw.circle(surf, lighten(acc, 0.6), (int(nx), int(stripe.centery)), 2)
        kx, ky = px + r * 0.82, by + r * 0.04
        pygame.draw.circle(surf, OUTLINE, (int(kx), int(ky)), max(3, int(r * 0.16)))
        pygame.draw.circle(surf, col, (int(kx), int(ky)), max(2, int(r * 0.12)))
        for k in (0.0, 0.55):
            wob = math.sin(t * 3.0 + k * 5.0) * r * 0.13
            mid = (kx + r * 0.26, ky + r * 0.12 + k * r * 0.16)
            tip = (kx + r * 0.54, ky + r * 0.28 + k * r * 0.26 + wob)
            pygame.draw.lines(surf, OUTLINE, False, [(kx, ky), mid, tip], 5)
            pygame.draw.lines(surf, col, False, [(kx, ky), mid, tip], 2)

    elif item["id"] == "dragon_helm":
        # Ejderha kaskı: kafaya oturan kapalı miğfer, arkasında yanan alev
        # yelesi, önünde iki kavisli boynuz ve kor gibi parlayan göz yarıkları.
        cy = py - r * 0.34
        # --- alev yelesi (arkada, gövdeden önce) ---
        for i in range(7):
            f = i / 6.0
            fl = math.sin(t * 6 + i * 0.9) * 0.5 + 0.5
            hx = px - r * (0.10 + f * 0.30)
            hy = cy - r * (0.55 + f * 0.62) - fl * r * 0.16
            fr = max(2, int(r * (0.24 - f * 0.13) * (0.75 + fl * 0.5)))
            fc = mix_col(acc, (255, 90, 40), f)
            add_glow(surf, hx, hy, fr * 2.4, fc, .30 + .18 * fl)
            pygame.draw.circle(surf, fc, (int(hx), int(hy)), fr)
        # --- boynuzlar ---
        for s in (-1, 1):
            hx0 = px + s * r * 0.54
            hy0 = cy - r * 0.26
            pts = [(hx0, hy0 + r * 0.16),
                   (hx0 + s * r * 0.16, hy0 - r * 0.46),
                   (hx0 + s * r * 0.62, hy0 - r * 0.74),
                   (hx0 + s * r * 0.40, hy0 - r * 0.30),
                   (hx0 + s * r * 0.34, hy0 + r * 0.10)]
            pygame.draw.polygon(surf, OUTLINE, [(x_ + s, y_ + 1) for x_, y_ in pts])
            pygame.draw.polygon(surf, acc, pts)
            pygame.draw.polygon(surf, scale_col(acc, 0.65), pts, 1)
        # --- miğfer gövdesi ---
        pygame.draw.circle(surf, OUTLINE, (int(px), int(cy)), int(r * 0.86))
        pygame.draw.circle(surf, col, (int(px), int(cy)), int(r * 0.80))
        pygame.draw.circle(surf, lighten(col, 0.30), (int(px - r * 0.28), int(cy - r * 0.32)),
                           max(2, int(r * 0.24)))
        # sırt kreti
        crest = [(px, cy - r * 0.84), (px + r * 0.10, cy - r * 0.20),
                 (px, cy + r * 0.30), (px - r * 0.10, cy - r * 0.20)]
        pygame.draw.polygon(surf, scale_col(col, 0.72), crest)
        # --- göz yarıkları (nabız gibi parlar) ---
        eg = .55 + .30 * math.sin(t * 3.6)
        for s in (-1, 1):
            exx, eyy = px + s * r * 0.30, cy + r * 0.20
            add_glow(surf, exx, eyy, r * 0.40, acc, eg)
            pygame.draw.polygon(surf, (255, 240, 190),
                                [(exx - s * r * 0.16, eyy - r * 0.06),
                                 (exx + s * r * 0.12, eyy - r * 0.12),
                                 (exx + s * r * 0.14, eyy + r * 0.06),
                                 (exx - s * r * 0.14, eyy + r * 0.08)])
        # çene/ağız hattı
        pygame.draw.arc(surf, scale_col(col, 0.5),
                        pygame.Rect(int(px - r * 0.52), int(cy + r * 0.16), int(r * 1.04), int(r * 0.72)),
                        3.5, 5.9, 2)

    elif item["id"] == "immortal_helm":
        # Ölümsüz miğfer: altın kapalı kask, çevresinde dönen runeler ve
        # yukarıdan aşağı süzülen bir ışık parıltısı.
        cy = py - r * 0.36
        # dönen rune halkası (arkada)
        for i in range(6):
            a = t * 0.9 + i * math.tau / 6
            rx = px + math.cos(a) * r * 1.12
            ry = cy + math.sin(a) * r * 0.42 - r * 0.10
            depth = 0.5 + 0.5 * math.sin(a)          # önde/arkada hissi
            rr = max(2, int(r * (0.09 + depth * 0.07)))
            rc = mix_col(scale_col(acc, 0.55), acc, depth)
            add_glow(surf, rx, ry, rr * 3.0, acc, .16 + depth * 0.20)
            pygame.draw.circle(surf, rc, (int(rx), int(ry)), rr)
            pygame.draw.circle(surf, lighten(acc, 0.5), (int(rx), int(ry)), max(1, rr // 2))
        # miğfer
        pygame.draw.circle(surf, OUTLINE, (int(px), int(cy)), int(r * 0.84))
        pygame.draw.circle(surf, col, (int(px), int(cy)), int(r * 0.78))
        # kayan parıltı bandı
        sh = (math.sin(t * 1.8) * 0.5 + 0.5)
        band_y = cy - r * 0.70 + sh * r * 1.30
        clip_prev = surf.get_clip()
        surf.set_clip(pygame.Rect(int(px - r * 0.78), int(cy - r * 0.78), int(r * 1.56), int(r * 1.56)))
        pygame.draw.line(surf, lighten(col, 0.55), (px - r * 0.80, band_y + r * 0.18),
                         (px + r * 0.80, band_y - r * 0.18), max(2, int(r * 0.14)))
        surf.set_clip(clip_prev)
        pygame.draw.circle(surf, lighten(col, 0.34), (int(px - r * 0.26), int(cy - r * 0.30)),
                           max(2, int(r * 0.22)))
        # taç dişleri
        for s in (-1, 0, 1):
            tx = px + s * r * 0.40
            pts = [(tx - r * 0.13, cy - r * 0.66), (tx, cy - r * 1.02), (tx + r * 0.13, cy - r * 0.66)]
            pygame.draw.polygon(surf, OUTLINE, [(x_, y_ + 1) for x_, y_ in pts])
            pygame.draw.polygon(surf, acc, pts)
        # T biçimli vizör
        pygame.draw.rect(surf, (36, 30, 18), (int(px - r * 0.09), int(cy - r * 0.30), int(r * 0.18), int(r * 0.92)))
        pygame.draw.rect(surf, (36, 30, 18), (int(px - r * 0.52), int(cy - r * 0.02), int(r * 1.04), int(r * 0.26)))
        pygame.draw.rect(surf, acc, (int(px - r * 0.52), int(cy - r * 0.02), int(r * 1.04), int(r * 0.26)), 1)
        pygame.draw.circle(surf, OUTLINE, (int(px), int(cy + r * 0.82)), max(2, int(r * 0.10)))
        pygame.draw.circle(surf, acc, (int(px), int(cy + r * 0.82)), max(2, int(r * 0.08)))

    elif item["id"] == "nightmare_helm":
        # Kâbus miğferi: mor alev saçan, ardında kaybolan ruhlar bırakan kask.
        cy = py - r * 0.34
        # uçuşan ruhlar
        for i in range(4):
            ph = (t * 0.7 + i * 0.25) % 1.0
            sx_ = px + math.sin(t * 1.6 + i * 2.0) * r * 0.72
            sy_ = cy - r * 0.55 - ph * r * 1.5
            al = (1.0 - ph)
            sr = max(1, int(r * 0.16 * al))
            add_glow(surf, sx_, sy_, sr * 3.4, acc, 0.30 * al)
            pygame.draw.circle(surf, mix_col(acc, (255, 255, 255), 0.3), (int(sx_), int(sy_)), sr)
        # yan alevler
        for s in (-1, 1):
            for i in range(3):
                fl = math.sin(t * 5 + i * 1.3 + s) * 0.5 + 0.5
                fxp = px + s * r * (0.66 + i * 0.10)
                fyp = cy - r * (0.20 + i * 0.34) - fl * r * 0.18
                fr = max(2, int(r * (0.20 - i * 0.045) * (0.7 + fl * 0.6)))
                add_glow(surf, fxp, fyp, fr * 2.6, acc, .26 + .16 * fl)
                pygame.draw.circle(surf, mix_col(acc, (120, 60, 200), i / 2.0), (int(fxp), int(fyp)), fr)
        # miğfer
        pygame.draw.circle(surf, OUTLINE, (int(px), int(cy)), int(r * 0.84))
        pygame.draw.circle(surf, col, (int(px), int(cy)), int(r * 0.78))
        pygame.draw.circle(surf, lighten(col, 0.28), (int(px - r * 0.26), int(cy - r * 0.30)),
                           max(2, int(r * 0.22)))
        # sivri tepe
        pts = [(px - r * 0.22, cy - r * 0.62), (px, cy - r * 1.14), (px + r * 0.22, cy - r * 0.62)]
        pygame.draw.polygon(surf, OUTLINE, [(x_, y_ + 1) for x_, y_ in pts])
        pygame.draw.polygon(surf, scale_col(col, 0.8), pts)
        # yarık göz bandı
        vis = pygame.Rect(int(px - r * 0.56), int(cy + r * 0.04), int(r * 1.12), int(r * 0.30))
        pygame.draw.rect(surf, (18, 12, 26), vis, border_radius=3)
        gl = .50 + .28 * math.sin(t * 4.2)
        add_glow(surf, px, vis.centery, r * 0.80, acc, gl)
        pygame.draw.line(surf, acc, (vis.x + 3, vis.centery), (vis.right - 3, vis.centery), 2)
        pygame.draw.line(surf, lighten(acc, 0.5), (vis.x + 5, vis.centery), (vis.right - 5, vis.centery), 1)

    elif item["id"] == "crystal_helm":
        # Kristal kask: saydam, ışığı kırarak sürekli renk değiştiren yüzeyler.
        cy = py - r * 0.34
        hue = (t * 0.10) % 1.0
        c1 = hue_col(hue)
        c2 = hue_col((hue + 0.33) % 1.0)
        c3 = hue_col((hue + 0.66) % 1.0)
        add_glow(surf, px, cy, r * 1.30, c1, .30 + .10 * math.sin(t * 3))
        pygame.draw.circle(surf, OUTLINE, (int(px), int(cy)), int(r * 0.84))
        pygame.draw.circle(surf, mix_col(col, c1, 0.45), (int(px), int(cy)), int(r * 0.78))
        # kristal yüzeyler (her biri farklı renkte kırılma)
        facets = [
            ([(px - r * 0.78, cy), (px - r * 0.22, cy - r * 0.74), (px - r * 0.06, cy + r * 0.10)], c2),
            ([(px + r * 0.78, cy), (px + r * 0.24, cy - r * 0.72), (px + r * 0.06, cy + r * 0.14)], c3),
            ([(px - r * 0.34, cy + r * 0.24), (px, cy - r * 0.10), (px + r * 0.34, cy + r * 0.26),
              (px, cy + r * 0.78)], mix_col(c1, (255, 255, 255), 0.35)),
        ]
        for pts, fc in facets:
            pygame.draw.polygon(surf, mix_col(fc, col, 0.45), pts)
            pygame.draw.polygon(surf, lighten(fc, 0.35), pts, 1)
        # tepe kristali
        spire = [(px - r * 0.18, cy - r * 0.66), (px, cy - r * 1.18), (px + r * 0.18, cy - r * 0.66)]
        pygame.draw.polygon(surf, OUTLINE, [(x_, y_ + 1) for x_, y_ in spire])
        pygame.draw.polygon(surf, mix_col(c2, (255, 255, 255), 0.4), spire)
        add_glow(surf, px, cy - r * 1.02, r * 0.46, c2, .42 + .18 * math.sin(t * 4.5))
        pygame.draw.circle(surf, WHITE, (int(px), int(cy - r * 1.04)), max(1, int(r * 0.08)))
        # kenar parlaması
        pygame.draw.circle(surf, lighten(acc, 0.2), (int(px), int(cy)), int(r * 0.78), 2)
        for i in range(3):
            a = t * 1.6 + i * math.tau / 3
            sxp = px + math.cos(a) * r * 0.60
            syp = cy + math.sin(a) * r * 0.60
            tw = 0.5 + 0.5 * math.sin(t * 6 + i * 2)
            pygame.draw.circle(surf, WHITE, (int(sxp), int(syp)), max(1, int(1 + tw * 1.8)))

    else:
        # Güvenlik ağı: ileride tanımsız yeni bir şapka eklenirse yine de
        # düzgün bir silueti olsun (kubbe + kenarlık + accent düğme).
        top_y = py - r - 8
        dome_r = max(6, int(r * 0.62))
        dome_c = (int(px), int(top_y))
        pygame.draw.circle(surf, OUTLINE, dome_c, dome_r + 3)
        pygame.draw.circle(surf, col, dome_c, dome_r)
        pygame.draw.circle(surf, lite, (int(px - dome_r * 0.32), int(top_y - dome_r * 0.32)),
                           max(2, int(dome_r * 0.32)))
        brim = pygame.Rect(0, 0, int(r * 1.52), int(r * 0.32))
        brim.center = (int(px), int(top_y + dome_r * 0.72))
        pygame.draw.ellipse(surf, OUTLINE, brim.inflate(4, 4))
        pygame.draw.ellipse(surf, dark, brim)
        pygame.draw.ellipse(surf, lighten(col, 0.18), (brim.x + 2, brim.y + 1, brim.w - 4, max(2, brim.h // 2)))
        pygame.draw.circle(surf, acc, (int(px), int(top_y - dome_r * 0.44)), 3)
        add_glow(surf, px, top_y, 13, acc, .40 + .12 * math.sin(t * 4))


def _face_frame(p, px, py):
    """Yüz için yerel koordinat sistemi döndürür.

    (fx, fy) = bakış yönü (ileri), (sx, sy) = yüze paralel yan eksen.
    Yerel bir (ileri, yan) noktası şu şekilde dünyaya çevrilir:
        X = px + ileri * fx + yan * sx
        Y = py + ileri * fy + yan * sy
    aim_dir birim vektör olmayabildiği için burada normalize edilir; böylece
    gözlükler hem oyunda hem de market önizlemesinde aynı oranda görünür.
    """
    ax, ay = getattr(p, "aim_dir", (1.0, 0.0))
    L = math.hypot(ax, ay)
    if L < 1e-6:
        ax, ay, L = 1.0, 0.0, 1.0
    ax, ay = ax / L, ay / L
    return ax, ay, -ay, ax


def _fpts(px, py, fx, fy, sx, sy, local):
    """Yerel (ileri, yan) noktalarını dünya koordinatlarına çevirir."""
    return [(px + lf * fx + ls * sx, py + lf * fy + ls * sy) for lf, ls in local]


def draw_cosmetic_eyewear(surf, p, px, py, t):
    """Gözlük — gözlerin üstüne, gövdeden sonra çizilir.

    Her gözlüğün gerçek bir çerçevesi, köprüsü ve cam parlaması var; artık
    hiçbiri "iki küçük daire" değil. Çizim yüzün baktığı yöne göre döner.
    """
    item = _player_cosmetic(p, "eyewear")
    if not item:
        return
    r = p.radius
    col, acc = item["color"], item["accent"]
    dark = scale_col(col, 0.55)
    fx_, fy_, sx_, sy_ = _face_frame(p, px, py)
    iid = item["id"]

    # gözlerin yerel konumu: biraz ileri, iki yana ayrık
    EF, ES = r * 0.40, r * 0.34

    def W(lf, ls):
        return (px + lf * fx_ + ls * sx_, py + lf * fy_ + ls * sy_)

    def poly(local, color, width=0):
        pygame.draw.polygon(surf, color, _fpts(px, py, fx_, fy_, sx_, sy_, local), width)

    def line(a, b, color, w=2):
        pygame.draw.line(surf, color, W(*a), W(*b), w)

    def lens_poly(side, hw, hh, tilt=0.0):
        """Tek bir cam için dörtgen: hw=ileri yarıçap, hh=yan yarıçap."""
        c = ES * side
        return [(EF - hw, c - hh * (1 - tilt * side)),
                (EF + hw, c - hh),
                (EF + hw, c + hh),
                (EF - hw, c + hh * (1 - tilt * side))]

    # ---------------- tek parça (wraparound) gözlükler ----------------
    if iid == "visor":
        band = [(EF - r * 0.20, -r * 0.62), (EF + r * 0.26, -r * 0.50),
                (EF + r * 0.26, r * 0.50), (EF - r * 0.20, r * 0.62)]
        poly([(a + 0.6, b) for a, b in band], OUTLINE)
        poly(band, dark)
        inner = [(EF - r * 0.10, -r * 0.52), (EF + r * 0.20, -r * 0.42),
                 (EF + r * 0.20, r * 0.42), (EF - r * 0.10, r * 0.52)]
        poly(inner, col)
        # tarama çizgisi yukarı aşağı gezer
        scan = math.sin(t * 2.6)
        line((EF + r * 0.06, -r * 0.40 * scan), (EF + r * 0.18, -r * 0.40 * scan), lighten(acc, .5), 2)
        line((EF - r * 0.16, -r * 0.55), (EF + r * 0.22, -r * 0.45), lighten(col, .45), 2)
        add_glow(surf, *W(EF, 0), r * 0.85, acc, .45 + .14 * math.sin(t * 4))

    elif iid == "laser_visor":
        bar = [(EF - r * 0.10, -r * 0.66), (EF + r * 0.20, -r * 0.60),
               (EF + r * 0.20, r * 0.60), (EF - r * 0.10, r * 0.66)]
        poly([(a + 0.6, b) for a, b in bar], OUTLINE)
        poly(bar, (24, 20, 28))
        pulse = .55 + .30 * math.sin(t * 7)
        add_glow(surf, *W(EF + r * 0.10, 0), r * 1.05, col, pulse)
        line((EF + r * 0.10, -r * 0.52), (EF + r * 0.10, r * 0.52), col, 4)
        line((EF + r * 0.10, -r * 0.52), (EF + r * 0.10, r * 0.52), lighten(acc, .6), 2)
        for s in (-1, 1):
            pygame.draw.circle(surf, acc, (int(W(EF + r * 0.10, s * r * 0.56)[0]),
                                           int(W(EF + r * 0.10, s * r * 0.56)[1])), max(2, int(r * 0.09)))

    elif iid == "ski_mask":
        mask = [(EF - r * 0.26, -r * 0.74), (EF + r * 0.28, -r * 0.58),
                (EF + r * 0.28, r * 0.58), (EF - r * 0.26, r * 0.74)]
        poly([(a + 0.8, b) for a, b in mask], OUTLINE)
        poly(mask, dark)
        glass = [(EF - r * 0.12, -r * 0.62), (EF + r * 0.22, -r * 0.48),
                 (EF + r * 0.22, r * 0.48), (EF - r * 0.12, r * 0.62)]
        poly(glass, col)
        poly([(EF + r * 0.02, -r * 0.54), (EF + r * 0.20, -r * 0.44),
              (EF + r * 0.20, -r * 0.16), (EF + r * 0.02, -r * 0.26)], lighten(col, .42))
        # kafa bandı
        for s in (-1, 1):
            line((EF - r * 0.26, s * r * 0.72), (EF - r * 0.95, s * r * 0.62), OUTLINE, 6)
            line((EF - r * 0.26, s * r * 0.72), (EF - r * 0.95, s * r * 0.62), acc, 3)

    elif iid == "blindfold":
        band = [(EF - r * 0.16, -r * 0.82), (EF + r * 0.22, -r * 0.66),
                (EF + r * 0.22, r * 0.66), (EF - r * 0.16, r * 0.82)]
        poly([(a + 0.8, b) for a, b in band], OUTLINE)
        poly(band, col)
        poly([(EF + r * 0.04, -r * 0.70), (EF + r * 0.18, -r * 0.62),
              (EF + r * 0.18, -r * 0.24), (EF + r * 0.04, -r * 0.34)], lighten(col, .22))
        # yan düğüm + uçuşan uçlar
        kx, ky = EF - r * 0.30, r * 0.80
        pygame.draw.circle(surf, OUTLINE, (int(W(kx, ky)[0]), int(W(kx, ky)[1])), max(3, int(r * 0.15)))
        pygame.draw.circle(surf, acc, (int(W(kx, ky)[0]), int(W(kx, ky)[1])), max(2, int(r * 0.11)))
        for k in (0.0, 0.5):
            wob = math.sin(t * 3 + k * 5) * r * 0.16
            pygame.draw.lines(surf, OUTLINE, False,
                              [W(kx, ky), W(kx - r * 0.30, ky + r * 0.22 + k * r * 0.2),
                               W(kx - r * 0.55, ky + r * 0.34 + k * r * 0.3 + wob)], 5)
            pygame.draw.lines(surf, col, False,
                              [W(kx, ky), W(kx - r * 0.30, ky + r * 0.22 + k * r * 0.2),
                               W(kx - r * 0.55, ky + r * 0.34 + k * r * 0.3 + wob)], 2)

    else:
        # ---------------- iki camlı gözlükler ----------------
        # köprü (iki cam arası)
        bridge_col = acc if iid not in ("shades", "round_glasses") else col

        for s in (-1, 1):
            if iid == "monocle" and s == -1:
                continue
            c = ES * s
            ex, ey = W(EF, c)

            if iid == "shades":
                lp = [(EF - r * 0.14, c - r * 0.30), (EF + r * 0.20, c - r * 0.30),
                      (EF + r * 0.20, c + r * 0.30), (EF - r * 0.14, c + r * 0.30)]
                poly([(a + 0.6, b) for a, b in lp], OUTLINE)
                poly(lp, (20, 20, 28))
                poly(lp, col, 1)
                poly([(EF - r * 0.06, c - r * 0.24), (EF + r * 0.12, c - r * 0.24),
                      (EF + r * 0.12, c - r * 0.06), (EF - r * 0.06, c - r * 0.06)], (118, 128, 155))
                # sap: kafayı sıyırarak geriye gider, dışarı fırlamaz
                line((EF - r * 0.12, c + r * 0.28 * s), (EF - r * 0.46, c + r * 0.40 * s), OUTLINE, 2)

            elif iid == "pink_shades":
                # kedi gözü: dış köşesi yukarı kalkık oval
                lp = [(EF - r * 0.16, c - r * 0.24), (EF + r * 0.10, c - r * 0.34),
                      (EF + r * 0.22, c - r * 0.06), (EF + r * 0.14, c + r * 0.26),
                      (EF - r * 0.12, c + r * 0.22)]
                poly([(a + 0.6, b) for a, b in lp], OUTLINE)
                poly(lp, col)
                poly(lp, acc, 1)
                poly([(EF - r * 0.04, c - r * 0.20), (EF + r * 0.10, c - r * 0.24),
                      (EF + r * 0.14, c - r * 0.04), (EF - r * 0.02, c - r * 0.02)], lighten(col, .55))
                line((EF - r * 0.14, c + r * 0.22 * s), (EF - r * 0.46, c + r * 0.36 * s), acc, 2)

            elif iid == "round_glasses":
                pygame.draw.circle(surf, OUTLINE, (int(ex), int(ey)), max(4, int(r * 0.32)))
                pygame.draw.circle(surf, (44, 48, 62), (int(ex), int(ey)), max(3, int(r * 0.29)))
                pygame.draw.circle(surf, col, (int(ex), int(ey)), max(3, int(r * 0.30)), 2)
                pygame.draw.circle(surf, lighten(acc, .45),
                                   (int(ex - fx_ * r * 0.09 + sx_ * r * 0.09),
                                    int(ey - fy_ * r * 0.09 + sy_ * r * 0.09)), max(1, int(r * 0.09)))
                line((EF - r * 0.06, c + r * 0.30 * s), (EF - r * 0.44, c + r * 0.40 * s), col, 2)

            elif iid == "goggles":
                pygame.draw.circle(surf, OUTLINE, (int(ex), int(ey)), max(4, int(r * 0.36)))
                pygame.draw.circle(surf, dark, (int(ex), int(ey)), max(4, int(r * 0.34)))
                pygame.draw.circle(surf, col, (int(ex), int(ey)), max(4, int(r * 0.34)), 3)
                pygame.draw.circle(surf, acc, (int(ex), int(ey)), max(2, int(r * 0.18)))
                pygame.draw.circle(surf, lighten(acc, .55),
                                   (int(ex - fx_ * r * 0.08 + sx_ * r * 0.07),
                                    int(ey - fy_ * r * 0.08 + sy_ * r * 0.07)), max(1, int(r * 0.07)))

            elif iid == "steampunk_goggles":
                pygame.draw.circle(surf, OUTLINE, (int(ex), int(ey)), max(4, int(r * 0.38)))
                pygame.draw.circle(surf, (28, 24, 22), (int(ex), int(ey)), max(4, int(r * 0.34)))
                pygame.draw.circle(surf, col, (int(ex), int(ey)), max(4, int(r * 0.34)), 3)
                pygame.draw.circle(surf, acc, (int(ex), int(ey)), max(2, int(r * 0.14)))
                for gi in range(8):
                    ga = gi * math.tau / 8 + t * 0.4 * s
                    gx = ex + math.cos(ga) * r * 0.40
                    gy = ey + math.sin(ga) * r * 0.40
                    pygame.draw.circle(surf, scale_col(col, .9), (int(gx), int(gy)), max(1, int(r * 0.05)))
                if s == 1:   # yan boru
                    line((EF - r * 0.10, c + r * 0.42), (EF - r * 0.60, c + r * 0.66), scale_col(col, .8), 4)

            elif iid == "monocle":
                pygame.draw.circle(surf, OUTLINE, (int(ex), int(ey)), max(4, int(r * 0.35)))
                pygame.draw.circle(surf, (54, 52, 44), (int(ex), int(ey)), max(3, int(r * 0.31)))
                pygame.draw.circle(surf, acc, (int(ex), int(ey)), max(4, int(r * 0.32)), 2)
                pygame.draw.circle(surf, lighten(acc, .6),
                                   (int(ex - fx_ * r * 0.10 + sx_ * r * 0.09),
                                    int(ey - fy_ * r * 0.10 + sy_ * r * 0.09)), max(1, int(r * 0.09)))
                # sarkan zincir: yüzün yanından geriye doğru iner
                sw = math.sin(t * 2.2) * r * 0.08
                pygame.draw.lines(surf, acc, False,
                                  [W(EF - r * 0.06, c + r * 0.34),
                                   W(EF - r * 0.34, c + r * 0.52 + sw),
                                   W(EF - r * 0.62, c + r * 0.60 + sw)], 1)

            elif iid == "heart_glasses":
                hr = r * 0.30
                hp = [(EF - hr * 0.9, c), (EF + hr * 0.2, c - hr * 1.0),
                      (EF + hr * 0.9, c - hr * 0.35), (EF + hr * 0.35, c + hr * 0.15),
                      (EF + hr * 0.9, c + hr * 0.35), (EF + hr * 0.2, c + hr * 1.0)]
                poly([(a + 0.6, b) for a, b in hp], OUTLINE)
                poly(hp, col)
                poly(hp, acc, 1)
                pygame.draw.circle(surf, lighten(acc, .6),
                                   (int(ex + sx_ * r * 0.08), int(ey + sy_ * r * 0.08)), max(1, int(r * 0.07)))

            elif iid == "star_glasses":
                spts = []
                for si in range(5):
                    oa = -math.pi / 2 + si * math.tau / 5
                    spts.append((EF + math.cos(oa) * r * 0.34, c + math.sin(oa) * r * 0.34))
                    ia = oa + math.pi / 5
                    spts.append((EF + math.cos(ia) * r * 0.15, c + math.sin(ia) * r * 0.15))
                poly([(a + 0.6, b) for a, b in spts], OUTLINE)
                poly(spts, col)
                poly(spts, acc, 1)
                tw = 0.5 + 0.5 * math.sin(t * 5 + s)
                pygame.draw.circle(surf, lighten(acc, .6), (int(ex), int(ey)), max(1, int(1 + tw * r * 0.10)))

            elif iid == "leaf_visor":
                # yaprak biçimli camlar + orta damar
                lp = [(EF - r * 0.22, c), (EF + r * 0.06, c - r * 0.34),
                      (EF + r * 0.26, c), (EF + r * 0.06, c + r * 0.34)]
                poly([(a + 0.6, b) for a, b in lp], OUTLINE)
                poly(lp, col)
                poly(lp, acc, 1)
                line((EF - r * 0.20, c), (EF + r * 0.24, c), scale_col(col, .6), 1)
                for k in (-1, 1):
                    line((EF - r * 0.02, c), (EF + r * 0.10, c + k * r * 0.16), scale_col(col, .6), 1)

            elif iid == "frost_lens":
                pygame.draw.circle(surf, OUTLINE, (int(ex), int(ey)), max(4, int(r * 0.34)))
                pygame.draw.circle(surf, col, (int(ex), int(ey)), max(3, int(r * 0.31)))
                pygame.draw.circle(surf, lighten(col, .5), (int(ex), int(ey)), max(3, int(r * 0.31)), 1)
                # buz kristali
                for k in range(3):
                    ka = k * math.pi / 3 + t * 0.6
                    dx, dy = math.cos(ka) * r * 0.24, math.sin(ka) * r * 0.24
                    pygame.draw.line(surf, lighten(acc, .4), (ex - dx, ey - dy), (ex + dx, ey + dy), 1)
                add_glow(surf, ex, ey, r * 0.52, acc, .34 + .12 * math.sin(t * 3 + s))

            elif iid == "ember_shades":
                lp = [(EF - r * 0.16, c - r * 0.30 * s), (EF + r * 0.20, c - r * 0.32),
                      (EF + r * 0.20, c + r * 0.28), (EF - r * 0.16, c + r * 0.24)]
                poly([(a + 0.6, b) for a, b in lp], OUTLINE)
                poly(lp, (26, 18, 16))
                poly(lp, col, 1)
                glow = .45 + .22 * math.sin(t * 4.5 + s * 1.2)
                add_glow(surf, ex, ey, r * 0.50, acc, glow)
                line((EF - r * 0.10, c - r * 0.18), (EF + r * 0.16, c + r * 0.10), acc, 2)
                line((EF + r * 0.02, c - r * 0.24), (EF + r * 0.10, c + r * 0.04), lighten(acc, .4), 1)

            else:
                # Güvenlik ağı: tanımsız yeni bir gözlük eklenirse düzgün görünsün.
                pygame.draw.circle(surf, OUTLINE, (int(ex), int(ey)), max(3, int(r * 0.31)))
                pygame.draw.circle(surf, col, (int(ex), int(ey)), max(3, int(r * 0.28)))
                pygame.draw.circle(surf, acc, (int(ex), int(ey)), max(3, int(r * 0.28)), 1)

        # köprü: monocle dışındaki bütün iki camlı gözlüklerde
        if iid != "monocle":
            line((EF + r * 0.04, -ES * 0.42), (EF + r * 0.04, ES * 0.42), bridge_col, 2)


AURA_INTERVAL = {"motes": .045, "wings": .08, "bubbles": .055, "stars": .09, "arcs": .07,
                 "shadow": .04, "flames": .022, "halo": .05, "prism": .04,
                 # premium skinler
                 "web": .07, "ash": .035, "titan": .05, "merc": .06}


def skin_update_fx(p, dt, fx):
    """Skin'e özel parçacık imzası.

    Eskiden "motes" ve "bubbles" aileleri yalnızca birkaç soluk toz zerresi
    üretiyor, o skinler ekranda renkli bir toptan ibaret kalıyordu. Artık her
    aile kendi karakterini taşıyan yoğun bir parçacık imzasına sahip.
    """
    if CFG.get("plain_skin"):
        return
    sk = p.skin
    a = sk["aura"]
    iv = AURA_INTERVAL.get(a, .2)
    p.aura_acc += dt
    n = int(p.aura_acc / iv)
    if n <= 0:
        return
    p.aura_acc -= n * iv
    n = min(n, 3)
    r = p.radius
    x, y = p.x, p.y
    col, acc = sk["color"], sk["accent"]
    for _ in range(n):
        if a == "motes":
            # Çekirdekten kopan enerji zerreleri: içeri doğru çekilen kıvılcımlar
            ang = random.uniform(0, math.tau)
            rad = r * random.uniform(1.4, 2.2)
            fx.spark(x + math.cos(ang) * rad, y + math.sin(ang) * rad, acc,
                     -math.cos(ang) * 46, -math.sin(ang) * 46 - 10, .55, 2.4)
            if random.random() < .45:
                fx.spark(x + random.uniform(-r, r), y + random.uniform(-r * .6, r),
                         col, random.uniform(-14, 14), -34, .7, 2.0)
        elif a == "wings":
            fx.spark(x + random.uniform(-r * 1.6, r * 1.6), y + random.uniform(-6, 10),
                     random.choice(((235, 85, 95), (255, 170, 140), (150, 40, 60))),
                     random.uniform(-22, 22), 22, 1.1, 3.0, add=False, gravity=12, drag=0.8)
            if random.random() < .35:
                fx.spark(x + random.uniform(-r * 2.0, r * 2.0), y - r * 0.4, acc,
                         random.uniform(-8, 8), 34, .9, 1.8, gravity=40, drag=0.6)
        elif a == "bubbles":
            # Kaynayan iksir: yükselen kabarcıklar + aşağı damlayan asit
            fx.spark(x + random.uniform(-r * .9, r * .9), y + random.uniform(-r * .2, r * .8),
                     lighten(col, 0.35), random.uniform(-10, 10), -40, 1.0, 3.0,
                     gravity=-16, drag=.45)
            if random.random() < .55:
                fx.spark(x + random.uniform(-r, r), y + r * .8, scale_col(col, 0.8),
                         random.uniform(-6, 6), 40, .7, 2.6, gravity=240, drag=.1)
            if random.random() < .30:
                fx.spark(x + random.uniform(-r * 1.4, r * 1.4), y + random.uniform(-r, r),
                         acc, random.uniform(-18, 18), -18, .5, 1.6)
        elif a == "stars":
            fx.spark(x + random.uniform(-r * 1.6, r * 1.6), y + random.uniform(-r * 1.6, r * 1.6),
                     random.choice((acc, col)), 0, -12, .7, 2.2)
        elif a == "shadow":
            fx.spark(x + random.uniform(-r * .9, r * .9), y + random.uniform(-r * .6, r * .9),
                     (36, 26, 56), random.uniform(-14, 14), -28, .85, 6, add=False, drag=1.5, grow=4)
            if random.random() < .5:
                fx.spark(x + random.uniform(-r, r), y + random.uniform(-r * .4, r), acc,
                         random.uniform(-10, 10), -40, .5, 2.4)
        elif a == "flames":
            fx.spark(x + random.uniform(-r * .8, r * .8), y + random.uniform(-r * .2, r * .7),
                     random.choice(((255, 140, 40), (255, 200, 80), (255, 90, 30))),
                     random.uniform(-14, 14), -55, .5, 4, drag=1.0)
        elif a == "halo":
            fx.spark(x + random.uniform(-r * 1.4, r * 1.4), y + random.uniform(-r * 1.4, r * 1.2),
                     acc, random.uniform(-10, 10), 20, .9, 2.4, gravity=20)
            if random.random() < .35:
                fx.spark(x + random.uniform(-r * .6, r * .6), y - r - 12, (255, 240, 180),
                         random.uniform(-6, 6), -14, .8, 1.8)
        elif a == "arcs":
            fx.spark(x + random.uniform(-r * 1.3, r * 1.3), y + random.uniform(-r * 1.3, r * 1.3),
                     acc, random.uniform(-30, 30), random.uniform(-30, 30), .35, 2.0)
        elif a == "prism":
            fx.spark(x + random.uniform(-r * 1.2, r * 1.2), y + random.uniform(-r * 1.2, r * 1.2),
                     hue_col(random.random()), random.uniform(-12, 12), -14, .7, 2.4)
        elif a == "web":
            # kopan ağ iplikleri
            fx.spark(x + random.uniform(-r * 1.3, r * 1.3), y + random.uniform(-r, r),
                     (232, 238, 250), random.uniform(-16, 16), random.uniform(10, 34),
                     .7, 1.8, add=False, gravity=60, drag=1.2)
        elif a == "ash":
            # savrulan kül + kızıl kor
            fx.spark(x + random.uniform(-r, r), y + random.uniform(-r * .4, r),
                     (188, 184, 178), random.uniform(-22, 22), -30, .8, 3.4,
                     add=False, drag=1.8, grow=2)
            if random.random() < .45:
                fx.spark(x + random.uniform(-r, r), y + random.uniform(-r * .4, r * .6),
                         (210, 60, 52), random.uniform(-14, 14), -42, .5, 2.2)
        elif a == "titan":
            # ayak altından fırlayan toprak/çim parçaları
            fx.spark(x + random.uniform(-r * 1.2, r * 1.2), y + r * .8,
                     random.choice(((96, 150, 72), (120, 96, 60))),
                     random.uniform(-40, 40), random.uniform(-70, -20), .7, 3.2,
                     add=False, gravity=260)
        elif a == "merc":
            # boş kovanlar + barut dumanı
            if random.random() < .5:
                fx.spark(x + random.uniform(-r, r), y,
                         (235, 200, 110), random.uniform(-45, 45), -30, .6, 2.0,
                         gravity=240, drag=.4)
            fx.spark(x + random.uniform(-r, r), y - r * .2,
                     (92, 92, 104), random.uniform(-10, 10), -26, .8, 3.4,
                     add=False, drag=1.6, grow=3)


def skin_draw_back(surf, p, px, py, t):
    """Oyuncunun ARKASINA çizilen skin efektleri (gövdenin altında kalır).

    Her aura ailesinin kendine ait bir arka imzası vardır; böylece hiçbir
    skin yalnızca renkli bir daire olarak kalmaz.
    """
    r = p.radius
    col = p.body_color(t)
    # Dash hayaletleri sade görünümde de kalır — oynanış bilgisi taşır.
    for g in p.ghosts:
        k = clamp(g[2] / 0.35, 0.0, 1.0)
        blit_disc(surf, g[0], g[1], r * (0.65 + 0.35 * k), g[3], 130 * k)
    if CFG.get("plain_skin"):
        # SADE GÖRÜNÜM: yalnızca hafif bir renk parıltısı kalır.
        add_glow(surf, px, py, r * 2.1, col, 0.26)
        return

    sk = p.skin
    a = sk["aura"]
    acc = sk["accent"]
    pulse = 0.5 + 0.5 * math.sin(t * 3)
    base_k = {"flames": .5, "halo": .5, "shadow": .4}.get(a, .32)
    gcol = acc if a == "shadow" else col
    add_glow(surf, px, py, r * (2.5 + 0.25 * pulse), gcol, base_k * (0.85 + 0.15 * pulse))

    if a == "wings":
        flap = math.sin(t * (9 if p.speed_now > 30 else 3.5)) * 0.32
        aim_ang = math.atan2(p.aim_dir[1], p.aim_dir[0])
        for side in (-1, 1):
            for i in range(4):
                ang = aim_ang + side * (1.15 + 0.32 * i + flap)
                dx, dy = math.cos(ang), math.sin(ang)
                nx, ny = -dy, dx
                sx, sy = px + dx * r * 0.5, py + dy * r * 0.5
                L = 40 - i * 4
                tx, ty = sx + dx * L, sy + dy * L
                pts = [(sx + nx * 4.5, sy + ny * 4.5), (tx, ty), (sx - nx * 4.5, sy - ny * 4.5)]
                pygame.draw.polygon(surf, scale_col(col, 0.58 + 0.13 * i), pts)
                pygame.draw.line(surf, acc, (sx, sy), (tx, ty), 1)

    elif a == "motes":
        # ENERJİ ÇEKİRDEĞİ: ters yönde dönen iki altıgen enerji halkası
        for k, (spd, rad_k, wid) in enumerate(((1.1, 1.9, 2), (-0.8, 2.35, 1))):
            ang0 = t * spd + k * 0.5
            rad = r * rad_k * (1.0 + 0.04 * math.sin(t * 2.6 + k))
            pts = [(px + math.cos(ang0 + i * math.tau / 6) * rad,
                    py + math.sin(ang0 + i * math.tau / 6) * rad * 0.82) for i in range(6)]
            pygame.draw.polygon(surf, scale_col(acc, 0.55 + 0.2 * k), pts, wid)
        # halkalar üzerinde koşan enerji düğümleri
        for i in range(3):
            a2 = t * 1.1 + i * math.tau / 3
            nx = px + math.cos(a2) * r * 1.9
            ny = py + math.sin(a2) * r * 1.9 * 0.82
            add_glow(surf, nx, ny, 11, acc, .55)

    elif a == "bubbles":
        # KAYNAYAN İKSİR: arkada yükselen büyük kabarcık kümesi
        for i in range(6):
            ph = (t * 0.5 + i * 0.167) % 1.0
            bx = px + math.sin(t * 1.5 + i * 2.1) * r * 1.6
            by = py + r * 1.0 - ph * r * 3.4
            br = (3.4 + i * 1.0) * (1.0 - ph * 0.40)
            if br < 1.5:
                continue
            alpha = int(190 * (1.0 - ph * 0.8))
            blit_disc(surf, bx, by, br * 1.6, col, alpha // 3)
            pygame.draw.circle(surf, lighten(col, 0.5), (int(bx), int(by)), int(br), 2)
            pygame.draw.circle(surf, (255, 255, 255),
                               (int(bx - br * 0.32), int(by - br * 0.32)), max(1, int(br * 0.22)))
        # tabanda kaynayan sıvı yüzeyi: dolu leke yerine iç içe ince halkalar
        for k in range(3):
            rw = r * (1.15 + k * 0.42) * (1.0 + 0.05 * math.sin(t * 5 + k * 1.4))
            ring = pygame.Rect(0, 0, int(rw * 2), int(max(4, rw * 0.52)))
            ring.center = (int(px), int(py + r * 0.82))
            pygame.draw.ellipse(surf, scale_col(lighten(col, 0.2), 0.9 - k * 0.2), ring, 1)
        add_glow(surf, px, py + r * 0.7, r * 1.5, lighten(col, 0.15),
                 .22 + .10 * math.sin(t * 6))

    elif a == "stars":
        # TAKIMYILDIZ: gövdeyi saran ince yıldız halkası
        ring = pygame.Rect(0, 0, int(r * 5.0), int(r * 3.4))
        ring.center = (int(px), int(py))
        pygame.draw.ellipse(surf, scale_col(acc, 0.5), ring, 1)
        for i in range(6):
            a2 = -t * 0.9 + i * math.tau / 6
            sx = px + math.cos(a2) * r * 2.5
            sy = py + math.sin(a2) * r * 1.7
            pygame.draw.circle(surf, acc, (int(sx), int(sy)), 2)

    elif a == "arcs":
        # TESLA BOBİNİ: gövdeyi çevreleyen iki bakır bobin halkası
        for k, rk in enumerate((1.7, 2.3)):
            ring = pygame.Rect(0, 0, int(r * rk * 2), int(r * rk * 1.15))
            ring.center = (int(px), int(py + r * (0.25 + k * 0.35)))
            pygame.draw.ellipse(surf, scale_col(acc, 0.45 + 0.15 * k), ring, 2)
        add_glow(surf, px, py, r * 2.0, acc, 0.22 + 0.16 * abs(math.sin(t * 7)))

    elif a == "shadow":
        # GÖLGE PELERİNİ: arkada dalgalanan karanlık şeritler
        for i in range(5):
            base_a = math.pi / 2 + (i - 2) * 0.34
            wob = math.sin(t * 2.4 + i * 1.3) * 0.22
            ang = base_a + wob
            L = r * (2.2 + 0.4 * math.sin(t * 1.7 + i))
            tipx, tipy = px + math.cos(ang) * L, py + math.sin(ang) * L
            midx = px + math.cos(ang + 0.25) * L * 0.55
            midy = py + math.sin(ang + 0.25) * L * 0.55
            pygame.draw.polygon(surf, (28, 20, 44),
                                [(px, py), (midx, midy), (tipx, tipy)])

    elif a == "flames":
        # KOR HALKASI: ayakların çevresinde yanan kor
        for i in range(8):
            a2 = t * 1.6 + i * math.tau / 8
            ex = px + math.cos(a2) * r * 1.9
            ey = py + math.sin(a2) * r * 0.95 + r * 0.4
            k = 0.5 + 0.5 * math.sin(t * 8 + i)
            add_glow(surf, ex, ey, 9 + 5 * k, (255, 120 + int(70 * k), 40), .5)

    elif a == "halo":
        # MELEK HALKALARI: eğik dönen iki altın halka
        for k, (rk, tilt) in enumerate(((2.4, 0.32), (2.0, 0.58))):
            w_ = r * rk * 2
            h_ = w_ * (tilt + 0.14 * math.sin(t * 1.3 + k * 2))
            ring = pygame.Rect(0, 0, int(w_), int(max(4, h_)))
            ring.center = (int(px), int(py + r * 0.15))
            pygame.draw.ellipse(surf, (255, 228, 150) if k == 0 else (232, 196, 110), ring, 2)

    elif a == "web":
        # AĞ USTASI: arkada gerilmiş ağ perdesi
        for k in range(3):
            rad = r * (1.9 + k * 0.5)
            pts = [(px + math.cos(t * 0.5 + i * math.tau / 8) * rad,
                    py + math.sin(t * 0.5 + i * math.tau / 8) * rad * 0.8) for i in range(8)]
            pygame.draw.polygon(surf, (86, 96, 122), pts, 1)
        for i in range(8):
            a2 = t * 0.5 + i * math.tau / 8
            pygame.draw.line(surf, (74, 84, 110), (px, py),
                             (px + math.cos(a2) * r * 2.9, py + math.sin(a2) * r * 2.3), 1)

    elif a == "ash":
        # KÜL SAVAŞÇISI: tek omuzdan sarkan kızıl pelerin
        sway = math.sin(t * 2.2) * r * 0.22
        pts = [(px - r * 0.2, py - r * 0.7), (px + r * 1.5, py - r * 0.3),
               (px + r * 1.9 + sway, py + r * 2.2), (px - r * 0.9 + sway, py + r * 2.0),
               (px - r * 0.9, py - r * 0.2)]
        pygame.draw.polygon(surf, (126, 26, 30), pts)
        pygame.draw.polygon(surf, (78, 14, 18), pts, 2)
        # omuz zırhı
        for s in (-1, 1):
            pygame.draw.circle(surf, (168, 164, 156),
                               (int(px + s * r * 0.95), int(py - r * 0.15)), int(r * 0.42))
            pygame.draw.circle(surf, (96, 92, 86),
                               (int(px + s * r * 0.95), int(py - r * 0.15)), int(r * 0.42), 2)

    elif a == "titan":
        # YEŞİL DEV: devasa omuz kütleleri + yerdeki çatlaklar
        for s in (-1, 1):
            pygame.draw.circle(surf, scale_col(col, 0.78),
                               (int(px + s * r * 1.05), int(py - r * 0.25)), int(r * 0.62))
            pygame.draw.circle(surf, OUTLINE,
                               (int(px + s * r * 1.05), int(py - r * 0.25)), int(r * 0.62), 2)
        rnd = random.Random(7)
        for i in range(6):
            a2 = rnd.uniform(0, math.tau)
            x0 = px + math.cos(a2) * r * 1.3
            y0 = py + r * 0.8 + math.sin(a2) * r * 0.3
            x1 = px + math.cos(a2) * r * 2.6
            y1 = py + r * 0.9 + math.sin(a2) * r * 0.6
            pygame.draw.line(surf, (58, 44, 30), (x0, y0), (x1, y1), 2)

    elif a == "merc":
        # ÖLÜMSÜZ KİRALIK: sırtta çapraz iki katana
        for s in (-1, 1):
            ang2 = -math.pi / 2 + s * 0.55
            hx = px - math.cos(ang2) * r * 1.5
            hy = py - math.sin(ang2) * r * 1.5
            tx = px + math.cos(ang2) * r * 1.9
            ty = py + math.sin(ang2) * r * 1.9
            pygame.draw.line(surf, (206, 210, 222), (hx, hy), (tx, ty), 4)
            pygame.draw.line(surf, (40, 42, 52), (hx, hy),
                             (hx - math.cos(ang2) * r * 0.55, hy - math.sin(ang2) * r * 0.55), 5)
        pygame.draw.circle(surf, (32, 34, 44), (int(px), int(py + r * 0.15)), int(r * 1.25), 3)

    elif a == "prism":
        # PRİZMA HALKASI: gökkuşağı renklerinde dönen altıgen
        ang0 = t * 0.9
        for i in range(6):
            a1 = ang0 + i * math.tau / 6
            a2 = ang0 + (i + 1) * math.tau / 6
            p1 = (px + math.cos(a1) * r * 2.1, py + math.sin(a1) * r * 2.1 * 0.85)
            p2 = (px + math.cos(a2) * r * 2.1, py + math.sin(a2) * r * 2.1 * 0.85)
            pygame.draw.line(surf, hue_col(t * 0.4 + i / 6.0), p1, p2, 2)


def skin_draw_front(surf, p, px, py, t):
    """Oyuncunun ÖNÜNE çizilen skin efektleri (gövdenin üstünde kalır)."""
    if CFG.get("plain_skin"):
        return
    sk = p.skin
    a = sk["aura"]
    r = p.radius
    acc = sk["accent"]
    col = sk["color"]

    if a == "stars":
        for i in range(3):
            ang = t * 2.2 + i * math.tau / 3
            sx, sy = px + math.cos(ang) * (r + 16), py + math.sin(ang) * (r + 16) * 0.9
            sz = 5 + math.sin(t * 6 + i) * 1.5
            add_glow(surf, sx, sy, 12, acc, .6)
            pygame.draw.line(surf, acc, (sx - sz, sy), (sx + sz, sy), 2)
            pygame.draw.line(surf, acc, (sx, sy - sz), (sx, sy + sz), 2)
        cy = py - r - 3
        pts = [(px - 9, cy), (px - 9, cy - 8), (px - 4.5, cy - 3), (px, cy - 10),
               (px + 4.5, cy - 3), (px + 9, cy - 8), (px + 9, cy)]
        pygame.draw.polygon(surf, (235, 190, 80), pts)
        pygame.draw.polygon(surf, (255, 240, 170), pts, 1)
        pygame.draw.circle(surf, (255, 90, 140), (int(px), int(cy - 4)), 2)

    elif a == "arcs":
        for k in range(3):
            rnd = random.Random(int(t * 16) * 7 + k * 131)
            ang = rnd.uniform(0, math.tau)
            x0, y0 = px + math.cos(ang) * (r + 1), py + math.sin(ang) * (r + 1)
            ang2 = ang + rnd.uniform(-.4, .4)
            ln = r + rnd.uniform(12, 24)
            x1, y1 = px + math.cos(ang2) * ln, py + math.sin(ang2) * ln
            pts = [(int(x), int(y)) for x, y in zigzag(x0, y0, x1, y1, 4, 4, rnd)]
            pygame.draw.lines(surf, acc, False, pts, 2)
            add_glow(surf, x1, y1, 10, col, .6)
        # tepede çatallanan bobin ucu
        tipy = py - r - 9
        pygame.draw.line(surf, acc, (px, py - r + 2), (px, tipy), 2)
        pygame.draw.circle(surf, (235, 255, 255), (int(px), int(tipy)), 3)
        add_glow(surf, px, tipy, 13, acc, .5 + .3 * abs(math.sin(t * 9)))

    elif a == "halo":
        hy = py - r - 12
        add_glow(surf, px, hy, 22, acc, .35)
        pygame.draw.ellipse(surf, (255, 235, 150), pygame.Rect(int(px - 15), int(hy - 4), 30, 9), 3)
        # halenin çevresinde dolanan altın zerreler
        for i in range(3):
            ang = t * 2.0 + i * math.tau / 3
            gx = px + math.cos(ang) * 17
            gy = hy + math.sin(ang) * 5
            pygame.draw.circle(surf, (255, 246, 200), (int(gx), int(gy)), 2)

    elif a == "shadow":
        for s in (-1, 1):
            pts = [(px + s * 10, py - r + 3), (px + s * 15, py - r - 10), (px + s * 4, py - r + 1)]
            pygame.draw.polygon(surf, (36, 26, 56), pts)
            pygame.draw.polygon(surf, acc, pts, 1)
        # boynuzlar arasında süzülen mor kıvılcım
        sx = px + math.sin(t * 3.1) * 6
        add_glow(surf, sx, py - r - 14, 9, acc, .45 + .25 * math.sin(t * 5))

    elif a == "flames":
        for i, ox in enumerate((-7, 0, 7)):
            h = 11 + 5 * math.sin(t * 14 + i * 2)
            pts = [(px + ox - 4.5, py - r + 2), (px + ox, py - r - h), (px + ox + 4.5, py - r + 2)]
            pygame.draw.polygon(surf, (255, 140, 40), pts)
            pts2 = [(px + ox - 2.5, py - r + 2), (px + ox, py - r - h * 0.6), (px + ox + 2.5, py - r + 2)]
            pygame.draw.polygon(surf, (255, 225, 120), pts2)

    elif a == "prism":
        for i in range(3):
            ang = t * 1.6 + i * math.tau / 3
            sx, sy = px + math.cos(ang) * (r + 15), py + math.sin(ang) * (r + 15)
            hc = hue_col(t * .5 + i * .33)
            add_glow(surf, sx, sy, 13, hc, .7)
            pygame.draw.polygon(surf, hc, [(sx, sy - 5), (sx + 3.5, sy), (sx, sy + 5), (sx - 3.5, sy)])

    elif a == "motes":
        # ENERJİ ÇEKİRDEĞİ: yörüngede koşan üç zerre + tepede enerji kıvılcımı
        for i in range(3):
            ang = t * 2.6 + i * math.tau / 3
            ox = px + math.cos(ang) * (r + 13)
            oy = py + math.sin(ang) * (r + 13) * 0.85
            add_glow(surf, ox, oy, 11, acc, .55)
            pygame.draw.circle(surf, acc, (int(ox), int(oy)), 3)
            # kısa kuyruk
            tang = ang - 0.35
            tx = px + math.cos(tang) * (r + 13)
            ty = py + math.sin(tang) * (r + 13) * 0.85
            pygame.draw.line(surf, scale_col(acc, 0.7), (tx, ty), (ox, oy), 2)
        # tepede duran enerji kıvılcımı
        sy = py - r - 8 + math.sin(t * 4) * 1.5
        add_glow(surf, px, sy, 12, col, .5)
        pygame.draw.circle(surf, (250, 252, 255), (int(px), int(sy)), 2)
        for k in range(4):
            ka = t * 3 + k * math.tau / 4
            pygame.draw.line(surf, acc, (px + math.cos(ka) * 3, sy + math.sin(ka) * 3),
                             (px + math.cos(ka) * 7, sy + math.sin(ka) * 7), 1)

    elif a == "bubbles":
        # İKSİR KABARCIKLARI: gövdenin önünde yükselen parlak kabarcıklar
        for i in range(4):
            ph = (t * 0.8 + i * 0.25) % 1.0
            bx = px + math.sin(t * 2.2 + i * 1.9) * (r * 0.9)
            by = py + r * 0.5 - ph * (r * 2.6)
            br = (4.2 - i * 0.5) * (1.0 - ph * 0.35)
            if br < 1.2:
                continue
            pygame.draw.circle(surf, lighten(col, 0.25), (int(bx), int(by)), int(br), 1)
            pygame.draw.circle(surf, (255, 255, 255),
                               (int(bx - br * 0.35), int(by - br * 0.35)), max(1, int(br * 0.3)))
        # omuz hizasında iki asit damlası
        for s in (-1, 1):
            dy = (t * 60 * (1 + 0.3 * s)) % 26
            dx = px + s * (r + 6)
            pygame.draw.circle(surf, acc, (int(dx), int(py - 6 + dy)), 2)
        add_glow(surf, px, py - r * 0.2, r * 1.2, lighten(col, 0.2), .28 + .12 * math.sin(t * 5))

    elif a == "web":
        # AĞ MASKESİ: kırmızı maske, ağ deseni ve beyaz badem gözler
        # (gövdenin sade gözlerinin üzerine çizilir, onları örter)
        for i in range(5):
            a2 = -math.pi * 0.5 + (i - 2) * 0.42
            pygame.draw.line(surf, (128, 24, 32), (px, py),
                             (px + math.cos(a2) * r * 0.95, py + math.sin(a2) * r * 0.95), 1)
        for rr in (0.42, 0.72):
            pygame.draw.arc(surf, (128, 24, 32),
                            pygame.Rect(int(px - r * rr), int(py - r * rr),
                                        int(r * rr * 2), int(r * rr * 2)),
                            math.pi * 0.08, math.pi * 0.92, 1)
        for s in (-1, 1):
            ex = px + s * r * 0.40
            ey = py - r * 0.08
            pts = [(ex - s * r * 0.30, ey + r * 0.16), (ex + s * r * 0.30, ey + r * 0.04),
                   (ex + s * r * 0.26, ey - r * 0.26), (ex - s * r * 0.22, ey - r * 0.18)]
            pygame.draw.polygon(surf, (245, 248, 255), pts)
            pygame.draw.polygon(surf, (20, 22, 34), pts, 2)

    elif a == "ash":
        # KÜL BOYASI: yüzü çaprazlayan kızıl dövme + sert bakış
        pygame.draw.line(surf, (176, 32, 36),
                         (px - r * 0.62, py - r * 0.55), (px - r * 0.18, py + r * 0.62), 3)
        pygame.draw.line(surf, (176, 32, 36),
                         (px + r * 0.22, py - r * 0.62), (px + r * 0.30, py + r * 0.58), 3)
        for s in (-1, 1):
            pygame.draw.line(surf, (62, 58, 54),
                             (px + s * r * 0.20, py - r * 0.36),
                             (px + s * r * 0.52, py - r * 0.46), 2)
        # sakal gölgesi
        pygame.draw.arc(surf, (120, 116, 110),
                        pygame.Rect(int(px - r * 0.55), int(py - r * 0.1),
                                    int(r * 1.1), int(r * 1.0)),
                        math.pi * 1.05, math.pi * 1.95, 3)

    elif a == "titan":
        # ÖFKELİ SURAT: çatık kaşlar + sıkılı çene
        for s in (-1, 1):
            pygame.draw.line(surf, (34, 62, 26),
                             (px + s * r * 0.16, py - r * 0.44),
                             (px + s * r * 0.60, py - r * 0.22), 4)
        pygame.draw.line(surf, (34, 62, 26),
                         (px - r * 0.36, py + r * 0.40), (px + r * 0.36, py + r * 0.40), 3)
        for i in range(3):
            tx = px - r * 0.22 + i * r * 0.22
            pygame.draw.line(surf, (215, 240, 200),
                             (tx, py + r * 0.40), (tx, py + r * 0.58), 2)
        add_glow(surf, px, py, r * 1.6, (150, 255, 130), .18 + .08 * math.sin(t * 3))

    elif a == "merc":
        # KİRALIK MASKESİ: kırmızı maske, siyah göz bölgeleri
        for s in (-1, 1):
            ex = px + s * r * 0.40
            ey = py - r * 0.08
            pts = [(ex - s * r * 0.34, ey + r * 0.20), (ex + s * r * 0.32, ey + r * 0.06),
                   (ex + s * r * 0.28, ey - r * 0.30), (ex - s * r * 0.26, ey - r * 0.20)]
            pygame.draw.polygon(surf, (26, 28, 36), pts)
            pygame.draw.polygon(surf, (236, 240, 248), pts, 2)
        pygame.draw.line(surf, (120, 20, 28),
                         (px - r * 0.72, py + r * 0.30), (px + r * 0.72, py + r * 0.30), 2)

    elif a == "wings":
        # TÜY TACI: başın üstünde titreşen üç tüy
        for i, ox in enumerate((-8, 0, 8)):
            h = 10 + 3 * math.sin(t * 6 + i * 1.7)
            tip = (px + ox * 1.25, py - r - h)
            pygame.draw.line(surf, scale_col(col, 0.85), (px + ox, py - r + 2), tip, 3)
            pygame.draw.line(surf, acc, (px + ox, py - r + 2), tip, 1)
        add_glow(surf, px, py - r - 6, 14, acc, .30)

class _SkinPreviewActor:
    """skin_draw_back / skin_draw_front için hafif bir sahte oyuncu.

    Skin market kartlarında ve detay ekranında skinin GERÇEK görünümünü
    (kanat, hale, yıldırım, kabarcık, enerji halkası...) canlandırmak için
    kullanılır.
    """
    __slots__ = ("skin", "radius", "ghosts", "speed_now", "aim_dir", "recoil", "flash_t")

    def __init__(self, sk, radius, aim_dir):
        self.skin = sk
        self.radius = radius
        self.ghosts = []
        self.speed_now = 0.0
        self.aim_dir = aim_dir
        self.recoil = 0.0
        self.flash_t = 0.0

    def body_color(self, t):
        if self.skin["id"] == "prism":
            return hue_col(t * 0.35)
        return self.skin["color"]


def draw_skin_preview(surf, sk, cx, cy, t, r=22, weapon=True):
    """Bir skini TÜM efektleriyle birlikte önizler.

    DÜZELTME: skin market'teki kartlar ve detay ekranı eskiden yalnızca düz
    renkli bir daire + silah çiziyordu. Bu yüzden kanatlı, haleli, yıldırımlı
    bütün skinler markette birbirinin aynı "renkli top" gibi görünüyor,
    oyuncu aldığı skinin neye benzediğini ancak oyuna girince görebiliyordu.
    """
    actor = _SkinPreviewActor(sk, r, (math.cos(t * 0.6), math.sin(t * 0.6) * 0.3))
    prev_plain = CFG.get("plain_skin")
    CFG["plain_skin"] = False          # markette skin her zaman tam hâliyle görünür
    try:
        skin_draw_back(surf, actor, cx, cy, t)
        body = actor.body_color(t)
        acc = sk["accent"]
        ix, iy = int(cx), int(cy)
        pygame.draw.circle(surf, OUTLINE, (ix, iy), int(r + 2))
        pygame.draw.circle(surf, scale_col(body, 0.6), (ix, iy), int(r))
        pygame.draw.circle(surf, body, (int(cx - r * 0.10), int(cy - r * 0.14)), int(r * 0.86))
        pygame.draw.circle(surf, lighten(body, 0.5),
                           (int(cx - r * 0.36), int(cy - r * 0.42)), max(2, int(r * 0.22)))
        pygame.draw.circle(surf, acc, (ix, iy), int(r), 2)
        ax, ay = actor.aim_dir
        for s in (-1, 1):
            ex = cx + ax * r * 0.42 + (-ay) * s * r * 0.34
            ey = cy + ay * r * 0.42 + ax * s * r * 0.34
            pygame.draw.circle(surf, (250, 250, 255), (int(ex), int(ey)), max(2, int(r * 0.24)))
            pygame.draw.circle(surf, (20, 24, 40),
                               (int(ex + ax * 1.8), int(ey + ay * 1.8)), max(1, int(r * 0.12)))
        if weapon:
            draw_weapon(surf, actor, cx, cy, t)
        skin_draw_front(surf, actor, cx, cy, t)
    finally:
        CFG["plain_skin"] = prev_plain


def draw_weapon(surf, p, px, py, t):
    sk = p.skin
    w = sk["weapon"]
    ax, ay = p.aim_dir
    ang = math.atan2(ay, ax)
    flip = -1 if ax < 0 else 1
    rec = p.recoil * 5
    ox = px + ax * (p.radius * 0.55 - rec)
    oy = py + ay * (p.radius * 0.55 - rec)
    col = p.body_color(t) if sk["id"] == "prism" else sk["color"]
    acc = sk["accent"]

    def P(x, y):
        return rot(x, y * flip, ang, ox, oy)

    def poly(pts, fill, edge=None, ew=2):
        rp = [P(x, y) for x, y in pts]
        pygame.draw.polygon(surf, fill, rp)
        if edge:
            pygame.draw.polygon(surf, edge, rp, ew)

    def line(a_, b_, c, wd):
        pygame.draw.line(surf, c, P(*a_), P(*b_), wd)

    def circ(x, y, rr, c, wd=0):
        pygame.draw.circle(surf, c, P(x, y), rr, wd)

    def glow(x, y, rr, c, k):
        gx, gy = P(x, y)
        add_glow(surf, gx, gy, rr, c, k)

    if w == "blaster":
        poly([(0, -4), (19, -4), (25, -2), (25, 2), (19, 4), (0, 4)], (44, 50, 72), acc, 2)
        poly([(3, 4), (9, 4), (7, 12), (2, 12)], (36, 40, 58))
        line((6, 0), (20, 0), col, 2)
        circ(26, 0, 3, acc)
    elif w == "crossbow":
        poly([(0, -2), (22, -2), (25, 0), (22, 2), (0, 2)], (78, 40, 46), acc, 1)
        poly([(9, -16), (19, -3), (19, 3), (9, 16), (13, 0)], col, (255, 200, 190), 2)
        line((10, -15), (22, 0), (255, 235, 225), 1)
        line((10, 15), (22, 0), (255, 235, 225), 1)
        poly([(20, -2), (30, 0), (20, 2)], acc)
    elif w == "flask":
        poly([(0, -4), (20, -3), (23, 0), (20, 3), (0, 4)], (35, 90, 45), acc, 1)
        circ(-1, -1, 8, (28, 66, 38))
        circ(-1, -1, 8, col, 2)
        for i in range(3):
            bx = -1 + math.sin(t * 3 + i * 2) * 3
            by = 5 - ((t * 14 + i * 7) % 12)
            circ(bx, by, 2, acc)
        glow(24, 0, 12, col, .55)
    elif w == "scepter":
        line((-8, 0), (32, 0), (210, 175, 95), 3)
        circ(36, 0, 7, (60, 30, 110))
        circ(36, 0, 7, col, 2)
        for aa in (-0.9, 0.0, 0.9):
            line((36 + math.cos(aa) * 7, math.sin(aa) * 7), (36 + math.cos(aa) * 11, math.sin(aa) * 11), acc, 2)
        glow(36, 0, 18, col, .6 + .2 * math.sin(t * 5))
    elif w == "tesla":
        line((0, 0), (25, 0), (70, 78, 100), 4)
        for x in (6, 12, 18):
            poly([(x - 1, -5), (x + 1, -5), (x + 1, 5), (x - 1, 5)], acc)
        circ(28, 0, 4, acc)
        rnd = random.Random(int(t * 25) + 7)
        for _ in range(2):
            aa = rnd.uniform(-1.2, 1.2)
            ln = rnd.uniform(8, 15)
            line((28, 0), (28 + math.cos(aa) * ln, math.sin(aa) * ln), (230, 255, 255), 1)
        glow(28, 0, 14, col, .7)
    elif w == "scythe":
        sw = math.sin(t * 2.5) * 0.05
        ang2 = ang + sw

        def P2(x, y):
            return rot(x, y * flip, ang2, ox, oy)
        pygame.draw.line(surf, (46, 36, 70), P2(-16, 0), P2(36, 0), 4)
        pygame.draw.line(surf, acc, P2(-16, 0), P2(36, 0), 1)
        blade = [(34, 0), (41, -6), (43, -15), (38, -25), (27, -32), (13, -33),
                 (18, -26), (28, -21), (34, -13), (33, -4)]
        bp = [P2(x, y) for x, y in blade]
        pygame.draw.polygon(surf, (22, 16, 36), bp)
        pygame.draw.polygon(surf, acc, bp, 2)
        gx, gy = P2(22, -29)
        add_glow(surf, gx, gy, 18, acc, .55)
        gx, gy = P2(40, -12)
        add_glow(surf, gx, gy, 12, acc, .4)
    elif w == "cannon":
        poly([(0, -6), (18, -5), (24, -3), (24, 3), (18, 5), (0, 6)], (84, 42, 26), (255, 160, 70), 2)
        for x in (5, 10, 15):
            line((x, -5), (x, 5), (255, 120, 40), 2)
        fl = 5 + 4 * abs(math.sin(t * 20))
        poly([(24, -4), (24 + fl, 0), (24, 4)], (255, 150, 40))
        poly([(24, -2), (24 + fl * 0.6, 0), (24, 2)], (255, 230, 120))
        glow(27, 0, 16, (255, 140, 40), .7)
    elif w == "goldgun":
        poly([(-2, -4), (22, -4), (31, -2), (31, 2), (22, 4), (-2, 4)], (210, 165, 70), (255, 240, 170), 2)
        poly([(2, 4), (9, 4), (6, 13), (0, 13)], (170, 130, 50))
        circ(10, 0, 3, (255, 90, 120))
        glow(10, 0, 8, (255, 90, 120), .5)
        circ(19, -6, 3, (255, 240, 170))
        glow(32, 0, 12, acc, .5)
    elif w == "crystal":
        hc = hue_col(t * 0.4)
        poly([(0, 0), (10, -8), (30, 0), (10, 8)], hc, (255, 255, 255), 2)
        line((0, 0), (30, 0), (255, 255, 255), 1)
        glow(30, 0, 14, hc, .7)
    # ---------------- PREMİUM SKİN SİLAHLARI ----------------
    elif w == "webshooter":
        # AĞ USTASI: bilek ağ fırlatıcısı — bileklik + çıkan ağ hüzmesi
        poly([(0, -5), (9, -6), (11, -3), (11, 3), (9, 6), (0, 5)], (58, 60, 78), acc, 1)
        poly([(9, -3), (18, -2), (18, 2), (9, 3)], (150, 155, 175))
        circ(6, 0, 3, acc)
        circ(6, 0, 3, (255, 255, 255), 1)
        for i in range(3):
            a_ = (i - 1) * 0.30
            tx, ty = 18 + math.cos(a_) * 10, math.sin(a_) * 10
            line((18, 0), (tx, ty), (238, 242, 250), 1)
        glow(20, 0, 10, (235, 240, 255), .45)
    elif w == "twinblades":
        # KÜL SAVAŞÇISI: zincire bağlı ikiz kılıçlar
        for s in (-1, 1):
            poly([(2, s * 4), (12, s * 9), (30, s * 5), (32, s * 2), (12, s * 3)],
                 (206, 204, 198), (120, 118, 112), 1)
            line((2, s * 4), (12, s * 6), (70, 62, 58), 3)
        line((0, 0), (16, 0), (86, 78, 70), 2)
        for i in range(3):
            circ(6 + i * 5, 0, 2, (150, 40, 42))
        glow(30, 0, 12, acc, .40)
    elif w == "fists":
        # YEŞİL DEV: silah yok — dev bir yumruk
        circ(10, 0, 11, scale_col(col, 0.75))
        circ(10, 0, 11, OUTLINE, 2)
        circ(8, -3, 4, lighten(col, 0.35))
        for i in range(3):
            line((14, -6 + i * 6), (19, -6 + i * 6), scale_col(col, 0.5), 2)
        glow(12, 0, 16, acc, .35)
    elif w == "pistols":
        # ÖLÜMSÜZ KİRALIK: çift tabanca
        for s in (-1, 1):
            poly([(0, s * 2 - 3), (16, s * 2 - 3), (16, s * 2 + 2), (0, s * 2 + 2)],
                 (46, 48, 60), (150, 152, 168), 1)
            poly([(2, s * 2 + 2), (7, s * 2 + 2), (5, s * 2 + 9), (1, s * 2 + 9)], (34, 36, 46))
            circ(17, s * 2, 2, (200, 200, 210))
        glow(20, 0, 12, col, .45)
    if p.flash_t > 0:
        gx, gy = P(sk["wlen"], 0)
        add_glow(surf, gx, gy, 24, acc, min(1.0, p.flash_t * 16))


# =====================================================================
# OYUN-İÇİ MARKET (geçici, oyun-içi altınla alınır, ölünce silinir)
# =====================================================================
# Kademe 5 = CEHENNEM: yalnızca CEHENNEM haritasında açılır (dalga şartı yok).
TIER_UNLOCK_WAVE = {1: 0, 2: 3, 3: 6, 4: 10, 5: 0}

SHOP_CATS = {
    "core":      "ÇEKİRDEK",
    "weapon":    "SİLAH",
    "defense":   "SAVUNMA",
    "elemental": "ELEMENT",
    "utility":   "YAŞAM",
    "cursed":    "LANETLİ",
    "legendary": "EFSANE",
    "hell":      "CEHENNEM",
}

SHOP_ITEMS = [
    # ---- ÇEKİRDEK: TAVANI OLMAYAN yükseltmeler --------------------------
    # Market eskiden birkaç dalga sonra tamamen "MAX" oluyor, biriken altının
    # harcanacak yeri kalmıyordu. Çekirdekler sonsuz yükseltilebilir; her
    # seviye biraz daha pahalı olur, böylece altın her zaman bir işe yarar
    # ve oyuncu kendini sürekli güçlenirken hisseder.
    {"key": "core_power",    "name": "Güç Çekirdeği",       "desc": "Hasar +%8 (tavanı yok)",
     "cost": 70,  "cost_mult": 1.28, "max": 999, "endless": True, "icon": "sword",  "color": (240, 110, 110), "tier": 1, "cat": "core"},
    {"key": "core_speed",    "name": "Hız Çekirdeği",       "desc": "Atış hızı +%6 (tavanı yok)",
     "cost": 80,  "cost_mult": 1.30, "max": 999, "endless": True, "icon": "boot",   "color": (130, 230, 170), "tier": 1, "cat": "core"},
    {"key": "core_vitality", "name": "Can Çekirdeği",       "desc": "Azami can +30 ve anında dolar (tavanı yok)",
     "cost": 60,  "cost_mult": 1.26, "max": 999, "endless": True, "icon": "heart",  "color": (235, 120, 150), "tier": 1, "cat": "core"},
    {"key": "core_crit",     "name": "Keskinlik Çekirdeği", "desc": "Kritik şans +%3, kritik hasar +%6 (tavanı yok)",
     "cost": 85,  "cost_mult": 1.29, "max": 999, "endless": True, "icon": "clover", "color": (230, 220, 120), "tier": 1, "cat": "core"},
    {"key": "core_guard",    "name": "Koruma Çekirdeği",    "desc": "Zırh +%2 (tavanı yok — zırh üst sınırına kadar)",
     "cost": 90,  "cost_mult": 1.32, "max": 999, "endless": True, "icon": "shield", "color": (160, 180, 220), "tier": 1, "cat": "core"},
    {"key": "core_greed",    "name": "Talan Çekirdeği",     "desc": "Altın +%12, deneyim +%8 (tavanı yok)",
     "cost": 65,  "cost_mult": 1.25, "max": 999, "endless": True, "icon": "coin",   "color": (235, 195, 95),  "tier": 1, "cat": "core"},

    # ---- Tier 1 (baştan açık) ----
    {"key": "fire",      "name": "Ateş Oku",        "desc": "Vuruşların yanık bırakır (zamanla hasar)", "cost": 40, "cost_mult": 1.55, "max": 5, "icon": "bolt", "color": ORANGE, "tier": 1, "cat": "elemental"},
    {"key": "ice",       "name": "Buz Oku",         "desc": "Vuruşların düşmanı yavaşlatır", "cost": 40, "cost_mult": 1.55, "max": 5, "icon": "target", "color": CYAN, "tier": 1, "cat": "elemental"},
    {"key": "multishot", "name": "Çoklu Atış",      "desc": "+1 ek mermi (yelpaze)", "cost": 75, "cost_mult": 1.8, "max": 5, "icon": "star", "color": PURPLE, "tier": 1, "cat": "weapon"},
    {"key": "pierce",    "name": "Delici Mermi",    "desc": "Mermi 1 düşman daha delsin", "cost": 55, "cost_mult": 1.65, "max": 5, "icon": "sword", "color": RED, "tier": 1, "cat": "weapon"},
    {"key": "shield",    "name": "Kalkan",          "desc": "Bir sonraki darbeyi engeller (yığılır)", "cost": 50, "cost_mult": 1.5, "max": 8, "icon": "shield", "color": (160, 170, 200), "tier": 1, "cat": "defense"},
    {"key": "heal",      "name": "İksir",           "desc": "Anında +40 can (10 sn'de bir alınabilir)", "cost": 30, "cost_mult": 1.2, "max": 40, "icon": "heart", "color": GREEN, "tier": 1, "cat": "utility", "instant": True},
    # ---- Tier 2 (Dalga 3+) ----
    {"key": "haste",     "name": "Çevik Refleks",   "desc": "+%9 atış hızı, +%5 hareket hızı", "cost": 65, "cost_mult": 1.6, "max": 8, "icon": "boot", "color": GREEN, "tier": 2, "cat": "weapon"},
    {"key": "explosive", "name": "Patlayıcı Mermi", "desc": "Öldürdüğün düşman çevresine sıçrama hasarı verir", "cost": 90, "cost_mult": 1.75, "max": 5, "icon": "star", "color": (240, 110, 60), "tier": 2, "cat": "weapon"},
    {"key": "vampiric",  "name": "Kan Emici",       "desc": "Verdiğin hasarın %2'si cana döner (seviye başı)", "cost": 85, "cost_mult": 1.7, "max": 5, "icon": "heart", "color": (220, 60, 90), "tier": 2, "cat": "utility"},
    {"key": "thorns",    "name": "Dikenli Zırh",    "desc": "Sana vuran düşman geri hasar alır", "cost": 60, "cost_mult": 1.55, "max": 6, "icon": "shield", "color": (170, 125, 90), "tier": 2, "cat": "defense"},
    {"key": "orbit",     "name": "Dönen Bıçaklar",  "desc": "Etrafında dönen bıçaklar (+1 bıçak)", "cost": 100, "cost_mult": 1.75, "max": 6, "icon": "orbit", "color": (150, 220, 255), "tier": 2, "cat": "weapon"},
    {"key": "dash_cd",   "name": "Sis Adımı",       "desc": "Dash bekleme -%18, mesafe +%10", "cost": 60, "cost_mult": 1.55, "max": 5, "icon": "dash", "color": (140, 230, 190), "tier": 2, "cat": "utility"},
    {"key": "blood_pact", "name": "Kan Sözleşmesi", "desc": "Hasar +%40 ama azami can -%25", "cost": 60, "cost_mult": 1.5, "max": 2, "icon": "skull", "color": (215, 50, 70), "tier": 2, "cat": "cursed", "cursed": True},
    {"key": "glass",     "name": "Cam Top",         "desc": "Atış hızı +%30 ama gelen hasar +%25", "cost": 70, "cost_mult": 1.5, "max": 2, "icon": "skull", "color": (200, 90, 220), "tier": 2, "cat": "cursed", "cursed": True},
    {"key": "devil",     "name": "Şeytan Pazarlığı", "desc": "Altın ve XP +%50 ama düşmanlar +%12 dayanıklı", "cost": 80, "cost_mult": 1.5, "max": 3, "icon": "skull", "color": (255, 120, 60), "tier": 2, "cat": "cursed", "cursed": True},
    # ---- Tier 3 (Dalga 6+) ----
    {"key": "chain",     "name": "Zincir Şok",      "desc": "BONK yakındaki ekstra düşmanlara sıçrar", "cost": 110, "cost_mult": 1.85, "max": 4, "icon": "bolt", "color": (120, 200, 255), "tier": 3, "cat": "elemental"},
    # NOT: "Güdümlü Mermi" MARKETTEN KALDIRILDI. Güdüm yeteneği yalnızca
    # YÖNELMELİ ŞAHİN skini ve onun özel yeteneğiyle gelir; markette satılmaz.
    {"key": "frenzy",    "name": "Çılgınlık Çekirdeği", "desc": "Ardışık öldürmeler hız ve hasarı artırır", "cost": 100, "cost_mult": 1.8, "max": 5, "icon": "clover", "color": (200, 230, 100), "tier": 3, "cat": "elemental"},
    {"key": "second_wind", "name": "İkinci Nefes",  "desc": "Öleceğin darbede %50 canla dirilirsin", "cost": 170, "cost_mult": 2.1, "max": 3, "icon": "heart", "color": (255, 215, 120), "tier": 3, "cat": "defense"},
    {"key": "storm",     "name": "Fırtına",         "desc": "Rastgele düşmanlara yıldırım düşer", "cost": 140, "cost_mult": 1.95, "max": 5, "icon": "bolt", "color": (190, 215, 255), "tier": 3, "cat": "elemental"},
    # ---- Tier 4 — EFSANEVİ (Dalga 10+) ----
    {"key": "overcharge", "name": "Aşırı Yük",      "desc": "BONK hasarı ve alanı çok büyük ölçüde artar", "cost": 240, "cost_mult": 2.2, "max": 4, "icon": "fist", "color": GOLD, "tier": 4, "cat": "legendary", "legendary": True},
    {"key": "execute_edge", "name": "İnfaz Kenarı", "desc": "Canı çok azalan düşmanları anında infaz eder", "cost": 240, "cost_mult": 2.2, "max": 3, "icon": "sword", "color": GOLD, "tier": 4, "cat": "legendary", "legendary": True},
    {"key": "titan_shield", "name": "Titan Kalkanı", "desc": "+2 kalkan yükü ve kalıcı zırh (bu koşu)", "cost": 240, "cost_mult": 2.2, "max": 4, "icon": "shield", "color": GOLD, "tier": 4, "cat": "legendary", "legendary": True},

    # ---- KADEME 5 · CEHENNEM (yalnızca 2. haritada açılır) --------------
    # Cehennem yaratıkları arenanın 25. dalgası kadar canlı ve vurucu geldiği
    # için oyuncunun ilerlemeye devam edebilmesi gerekiyor: bu eşyalar
    # yalnızca CEHENNEM'de satılır ve cehennem dövüşüne göre tasarlandı.
    {"key": "brimstone", "name": "Kükürt Mermisi",
     "desc": "Hasar +%25 (cehennem çeliğiyle dövülmüş mermi)",
     "cost": 300, "cost_mult": 1.85, "max": 5, "icon": "flame", "color": (255, 120, 60),
     "tier": 5, "cat": "hell", "hell_only": True},
    {"key": "hell_ward", "name": "Kor Muskası",
     "desc": "Zırh +%6 ve +40 azami can — cehennem ateşine karşı",
     "cost": 280, "cost_mult": 1.80, "max": 5, "icon": "shield", "color": (255, 170, 90),
     "tier": 5, "cat": "hell", "hell_only": True},
    {"key": "holy_flame", "name": "Kutsal Alev",
     "desc": "Vuruşların düşmanı kutsal ateşle yakar (çok güçlü yanık)",
     "cost": 340, "cost_mult": 1.90, "max": 4, "icon": "cross", "color": (255, 235, 150),
     "tier": 5, "cat": "hell", "hell_only": True},
    {"key": "soul_harvest", "name": "Ruh Hasadı",
     "desc": "Her öldürme can verir ve 5 sn boyunca hasarını yığarak artırır",
     "cost": 360, "cost_mult": 1.95, "max": 3, "icon": "skull", "color": (200, 120, 255),
     "tier": 5, "cat": "hell", "hell_only": True},
    {"key": "angel_wing", "name": "Melek Kanadı",
     "desc": "Dash bekleme -%20 ve dash sonrası uzun dokunulmazlık",
     "cost": 320, "cost_mult": 1.85, "max": 3, "icon": "boot", "color": (220, 240, 255),
     "tier": 5, "cat": "hell", "hell_only": True},
    {"key": "purgatory", "name": "Araf Kalkanı",
     "desc": "Ölümcül darbeyi engeller — 25 sn'de bir kendini yeniler",
     "cost": 420, "cost_mult": 2.1, "max": 2, "icon": "heart", "color": (255, 215, 120),
     "tier": 5, "cat": "hell", "hell_only": True},
    {"key": "infernal_core", "name": "Cehennem Çekirdeği",
     "desc": "Hasar +%10 ve atış hızı +%7 (tavanı yok)",
     "cost": 260, "cost_mult": 1.32, "max": 999, "endless": True, "icon": "gem",
     "color": (255, 90, 120), "tier": 5, "cat": "hell", "hell_only": True},
]
SHOP_BY_KEY = {it["key"]: it for it in SHOP_ITEMS}


def shop_item_cost(item, level):
    return int(math.ceil(item["cost"] * (item["cost_mult"] ** level)))


def shop_item_unlocked(item, current_wave, biome="arena"):
    """Eşya markette alınabilir mi?

    CEHENNEM eşyaları (hell_only) yalnızca 2. haritada görünür; arena
    eşyaları cehennemde de alınmaya devam eder.
    """
    if item.get("hell_only"):
        return biome == "hell"
    return current_wave >= TIER_UNLOCK_WAVE.get(item["tier"], 0)


def apply_shop_item(player, key):
    # --- ÇEKİRDEKLER: tavanı yok, her alımda birikir ---
    if key == "core_power":
        player.run_dmg_mult += 0.08
        return
    if key == "core_speed":
        player.run_aspd_mult += 0.06
        return
    if key == "core_vitality":
        player.base_max_hp += 30
        player.max_hp += 30
        player.hp = min(player.max_hp, player.hp + 30)   # eklenen can anında dolar
        return
    if key == "core_crit":
        player.crit_chance = clamp(player.crit_chance + 0.03, 0, 0.9)
        player.crit_dmg_mult += 0.06
        return
    if key == "core_guard":
        player.base_armor = clamp(player.base_armor + 0.02, 0, 0.5)
        return
    if key == "core_greed":
        player.run_coin_mult += 0.12
        player.run_xp_mult += 0.08
        return
    if key == "fire":
        player.fire_level += 1
    elif key == "ice":
        player.ice_level += 1
    elif key == "multishot":
        player.multishot_level += 1
    elif key == "pierce":
        player.pierce_bonus += 1
    elif key == "shield":
        player.shield_charges += 1
    elif key == "heal":
        player.heal(40)
    elif key == "haste":
        player.run_aspd_mult += 0.09
        player.run_spd_mult += 0.05
    elif key == "explosive":
        player.explosive_level += 1
    elif key == "vampiric":
        player.vamp_level += 1
    elif key == "thorns":
        player.thorns_level += 1
    # ---- CEHENNEM eşyaları ----
    elif key == "brimstone":
        player.run_dmg_mult += 0.25
    elif key == "hell_ward":
        player.base_armor += 0.06
        player.base_max_hp += 40
        player.max_hp += 40
        player.hp = min(player.max_hp, player.hp + 40)
    elif key == "holy_flame":
        player.holy_flame += 1
    elif key == "soul_harvest":
        player.soul_harvest += 1
    elif key == "angel_wing":
        player.dash_cd_mult = max(0.30, player.dash_cd_mult - 0.20)
        player.angel_wing += 1
    elif key == "purgatory":
        player.purgatory_level += 1
        player.purgatory_timer = 0.0
    elif key == "infernal_core":
        player.run_dmg_mult += 0.10
        player.run_aspd_mult += 0.07
    elif key == "orbit":
        player.orbit_level += 1
    elif key == "dash_cd":
        player.dash_cd_mult = max(0.35, player.dash_cd_mult - 0.18)
        player.dash_dist_mult += 0.10
    elif key == "blood_pact":
        player.run_dmg_mult += 0.40
        player.max_hp = max(30, int(player.max_hp * 0.75))
        player.hp = min(player.hp, player.max_hp)
    elif key == "glass":
        player.run_aspd_mult += 0.30
        player.dmg_taken_mult += 0.25
    elif key == "devil":
        player.run_coin_mult += 0.50
        player.run_xp_mult += 0.50
        player.enemy_hp_curse += 0.12
    elif key == "chain":
        player.chain_level += 1
    elif key == "frenzy":
        player.frenzy_level += 1
    elif key == "second_wind":
        player.second_wind_charges += 1
    elif key == "storm":
        player.storm_level += 1
    elif key == "overcharge":
        player.bonk_mult += 0.35
        player.bonk_radius_mult += 0.15
    elif key == "execute_edge":
        player.execute_threshold = min(0.35, player.execute_threshold + 0.12)
    elif key == "titan_shield":
        player.shield_charges += 2
        player.base_armor = clamp(player.base_armor + 0.06, 0, 0.5)


# =====================================================================
# SEVİYE ATLAMA YÜKSELTMELERİ  ("rare" olanlar seyrek çıkar ama çok güçlüdür)
# =====================================================================
# =====================================================================
# KİTAPLAR  (seviye atlayınca gelen yükseltmeler)
# ---------------------------------------------------------------------
# Her yükseltme bir KİTAP. Kapağı, amblemi ve rengi var; seviye atlayınca
# üç kitap arasından biri seçilir.
#
# TASARIM KURALI: Kitaplar, oyun-içi MARKET'in sattığı şeyleri SATMAZ ve
# ekonomi (altın / tecrübe) bonusu VERMEZ. Market ateş/buz/çoklu atış/
# kalkan/dikenler gibi şeyleri zaten veriyor; kitaplar ise ham savaş ve
# hayatta kalma gücü verir: hasar, can, zırh, kritik, menzil, BONK, zehir
# ve markette hiç bulunmayan özel etkiler.
#
# KİLİT: Kitaplar elmasla DEĞİL, GÖREVLE açılır ve ARTIK HEPSİ KİLİTLİDİR.
# Her kitabın BİRDEN FAZLA şartı olabilir; kitap ancak şartların TAMAMI
# tamamlanınca açılır. Kitap ne kadar güçlüyse şartı o kadar ağırdır:
#   - temel kitaplar  : birkaç koşuda dolan küçük hedefler
#   - orta kitaplar   : belli bir oynanış tarzını gerektiren iki hedef
#   - NADİR kitaplar  : uzun soluklu sayaçlar + başarım / market şartı
#
#   unlock = dict(text=<özet>, reqs=[<şart>, <şart>, ...])
#   şart türleri:
#     rq_stat(stat, need, text) : kayıttaki bir sayaç hedefe ulaşsın
#     rq_ach(ach_id)            : bir BAŞARIM açılmış olsun
#     rq_shop(item, need, text) : koşu içi markette bir eşya şu seviyeye çıksın
#     rq_book(book_key)         : başka bir kitap açılmış olsun
#
# İzlenen istatistikler (SaveManager.data["stats"]):
#   total_kills, best_run_kills, bosses, best_wave, best_score, runs,
#   total_healed, best_run_heal, total_crits, total_bonks, total_bonk_hits,
#   total_dashes, best_run_dashes, best_combo, total_shots, best_run_shots,
#   total_lifesteal, total_gold, best_run_gold, total_time, shop_max{}
# =====================================================================


def rq_stat(stat, need, text):
    return dict(kind="stat", stat=stat, need=need, text=text)


def rq_ach(ach_id, text=None):
    return dict(kind="ach", ach=ach_id, need=1, text=text)


def rq_shop(item, need, text):
    return dict(kind="shop", item=item, need=need, text=text)


def rq_book(book_key, text=None):
    return dict(kind="book", book=book_key, need=1, text=text)


BOOKS = [
    # ---- TEMEL KİTAPLAR (en kolay görevler — ilk koşularda açılır) ----
    {"key": "r_dmg", "name": "Hasar Kitabı", "desc": "Hasarını %18 artırır",
     "color": RED, "icon": "sword", "rare": False, "basic": True,
     "unlock": dict(text="Arenaya alış: 60 düşman öldür",
                    reqs=[rq_stat("total_kills", 60, "Toplam 60 düşman öldür")])},
    {"key": "r_hp", "name": "Can Kitabı", "desc": "Azami canını %25 artırır (anında dolar)",
     "color": (230, 110, 130), "icon": "heart", "rare": False, "basic": True,
     "unlock": dict(text="3 koşu tamamla ve 4. dalgayı gör",
                    reqs=[rq_stat("runs", 3, "3 koşu tamamla"),
                          rq_stat("best_wave", 4, "4. dalgaya ulaş")])},
    {"key": "r_armor", "name": "Zırh Kitabı", "desc": "Aldığın hasarı %5 azaltır ve +15 can verir",
     "color": (160, 170, 200), "icon": "shield", "rare": False, "basic": True,
     "unlock": dict(text="500 altın topla ve 5. dalgaya ulaş",
                    reqs=[rq_stat("total_gold", 500, "Toplam 500 altın topla"),
                          rq_stat("best_wave", 5, "5. dalgaya ulaş")])},

    # ---- ORTA KİTAPLAR (belli bir oynanışı gerektirir) ----
    {"key": "r_spd", "name": "Rüzgâr Kitabı",
     "desc": "Hareket hızın %12, dash mesafen %20 artar",
     "color": GREEN, "icon": "boot", "rare": False,
     "unlock": dict(text="Dash ustası ol",
                    reqs=[rq_stat("total_dashes", 400, "Toplam 400 kez dash at"),
                          rq_stat("best_run_dashes", 40, "Tek koşuda 40 kez dash at")])},
    {"key": "r_crit", "name": "Kritik Kitabı", "desc": "Kritik vuruş şansını %8 artırır",
     "color": (140, 230, 120), "icon": "clover", "rare": False,
     "unlock": dict(text="Kritik vuruşla tanış",
                    reqs=[rq_stat("total_crits", 600, "Toplam 600 kritik vuruş yap"),
                          rq_stat("best_wave", 7, "7. dalgaya ulaş")])},
    {"key": "r_critd", "name": "Kritik Güç Kitabı", "desc": "Kritik hasarını %40 artırır",
     "color": (240, 90, 90), "icon": "fist", "rare": False,
     "unlock": dict(text="Kritik hasarda uzmanlaş",
                    reqs=[rq_stat("total_crits", 3000, "Toplam 3.000 kritik vuruş yap"),
                          rq_ach("combo30", "«Kombo Kralı» başarımını aç")])},
    {"key": "r_regen", "name": "Şifa Kitabı", "desc": "Saniyede 0.8 can yeniler",
     "color": (120, 220, 170), "icon": "cross", "rare": False,
     "unlock": dict(text="Yaralarını sar",
                    reqs=[rq_stat("best_run_heal", 1200, "Tek koşuda 1.200 can yenile"),
                          rq_stat("total_healed", 6000, "Toplam 6.000 can yenile")])},
    {"key": "r_bonk", "name": "BONK Kitabı",
     "desc": "BONK hasarın %35, vuruş alanın %20 büyür",
     "color": (240, 120, 60), "icon": "fist", "rare": False,
     "unlock": dict(text="Yumruğunla konuş",
                    reqs=[rq_stat("total_bonks", 500, "Toplam 500 kez BONK at"),
                          rq_stat("total_bonk_hits", 2500, "BONK ile toplam 2.500 düşmana vur")])},
    {"key": "r_swarm", "name": "Sürü Kitabı",
     "desc": "Çevrende 3+ düşman varken hasarın %30 artar",
     "color": (210, 160, 70), "icon": "orbit", "rare": False,
     "unlock": dict(text="Kalabalığın ortasında yaşa",
                    reqs=[rq_stat("best_run_kills", 250, "Tek koşuda 250 düşman öldür"),
                          rq_ach("massacre", "«Katliam» başarımını aç")])},
    {"key": "r_bosshunter", "name": "Patron Avcısı Kitabı",
     "desc": "Patronlara ve elit düşmanlara %30 fazla hasar vurursun",
     "color": (200, 90, 220), "icon": "target", "rare": False,
     "unlock": dict(text="Patron avına çık",
                    reqs=[rq_stat("bosses", 6, "6 patron devir"),
                          rq_ach("boss", "«Dev Avcısı» başarımını aç")])},

    # ---- NADİR KİTAPLAR: markette hiç olmayan güçlü etkiler ----
    # Bunlar oyunun en güçlü etkileri; şartları da buna göre ağırdır.
    {"key": "r_poison", "name": "Zehir Kitabı",
     "desc": "Vurduğun düşmanı ÖLENE KADAR zehirler — zehir üst üste birikir",
     "color": (120, 225, 90), "icon": "drop", "rare": True,
     "unlock": dict(text="Binlerce düşmanı devir, birini bile kaçırma",
                    reqs=[rq_stat("total_kills", 5000, "Toplam 5.000 düşman öldür"),
                          rq_stat("best_run_kills", 300, "Tek koşuda 300 düşman öldür"),
                          rq_ach("hunter", "«Usta Avcı» başarımını aç")])},
    {"key": "r_echo", "name": "Yankı Kitabı",
     "desc": "Her 4. atışın ÇİFT hasar vurur",
     "color": (255, 225, 140), "icon": "bolt", "rare": True,
     "unlock": dict(text="Tetiği bırakma: yarım milyon mermi",
                    reqs=[rq_stat("total_shots", 500000, "Toplam 500.000 mermi at"),
                          rq_ach("shots50k", "«Mermi Fabrikası» başarımını aç")])},
    {"key": "r_killheal", "name": "Kan Kitabı",
     "desc": "Öldürdüğün her düşman sana 3 can verir",
     "color": (220, 60, 90), "icon": "heart", "rare": True,
     "unlock": dict(text="Kan Emici'yi tavana çıkar ve 30.000 can çal",
                    reqs=[rq_shop("vampiric", 5, "Kan Emici'yi markette Lv.5'e (tavan) çıkar"),
                          rq_stat("total_lifesteal", 30000, "Kan Emici ile toplam 30.000 can çal")])},
    {"key": "r_rage", "name": "Öfke Kitabı",
     "desc": "Canın yarısının altındayken hasarın %35 artar",
     "color": (250, 70, 50), "icon": "flame", "rare": True,
     "unlock": dict(text="Patronların kâbusu ol",
                    reqs=[rq_stat("bosses", 12, "12 patron devir"),
                          rq_stat("best_run_kills", 400, "Tek koşuda 400 düşman öldür")])},
    {"key": "r_roar", "name": "Kükreme Kitabı",
     "desc": "BONK'ladığın düşmanlar korkup senden kaçar",
     "color": (235, 140, 60), "icon": "skull", "rare": True,
     "unlock": dict(text="Arena senin kükremeni tanısın",
                    reqs=[rq_stat("total_bonks", 1500, "Toplam 1.500 kez BONK at"),
                          rq_stat("total_bonk_hits", 9000, "BONK ile toplam 9.000 düşmana vur"),
                          rq_book("r_bonk", "Önce BONK Kitabı'nı aç")])},
    {"key": "r_dashslow", "name": "Zaman Kitabı",
     "desc": "Dash attığında çevrendeki düşmanlar yavaşlar",
     "color": (150, 200, 255), "icon": "snow", "rare": True,
     "unlock": dict(text="Zamanla yarış",
                    reqs=[rq_stat("best_wave", 14, "14. dalgaya ulaş"),
                          rq_stat("total_dashes", 1500, "Toplam 1.500 kez dash at"),
                          rq_book("r_spd", "Önce Rüzgâr Kitabı'nı aç")])},
    {"key": "r_lasthope", "name": "Son Umut Kitabı",
     "desc": "Canın %30'unun altındayken aldığın hasar %20 azalır",
     "color": (255, 215, 120), "icon": "shield", "rare": True,
     "unlock": dict(text="Ölümün kıyısında ayakta kal",
                    reqs=[rq_stat("best_wave", 18, "18. dalgaya ulaş"),
                          rq_ach("wave15", "«Arena Ustası» başarımını aç"),
                          rq_shop("shield", 6, "Kalkan'ı markette Lv.6'ya çıkar")])},
    {"key": "r_hp_big", "name": "Dev Kitabı",
     "desc": "Azami canın %40 artar ama biraz yavaşlarsın",
     "color": (200, 140, 90), "icon": "skull", "rare": True,
     "unlock": dict(text="Devleşecek kadar dayan",
                    reqs=[rq_stat("best_combo", 45, "45'lik bir kombo yap"),
                          rq_stat("total_healed", 25000, "Toplam 25.000 can yenile"),
                          rq_ach("wave10", "«Hayatta Kalan» başarımını aç")])},
]
BOOK_BY_KEY = {b["key"]: b for b in BOOKS}
# Artık "şartsız" kitap yok. TEMEL kitaplar yalnızca bir EMNİYET LİSTESİDİR:
# oyuncunun hiç kitabı yoksa seviye atlama ekranı boş kalmasın diye
# start_levelup_choice() bu listeye düşer.
STARTER_BOOKS = [b["key"] for b in BOOKS if b.get("basic")]


def book_reqs(book):
    unl = book.get("unlock")
    return list(unl.get("reqs", [])) if unl else []


def book_req_state(save, req):
    """Tek bir şartın durumu: (şu an, hedef, tamam mı, açıklama)."""
    kind = req.get("kind", "stat")
    if kind == "ach":
        a = ACH_BY_ID.get(req["ach"])
        got = req["ach"] in save.data.get("achievements", {})
        text = req.get("text") or (f"«{a['name']}» başarımını aç" if a else "Bir başarım aç")
        return (1 if got else 0), 1, got, text
    if kind == "shop":
        item = SHOP_BY_KEY.get(req["item"]) if "SHOP_BY_KEY" in globals() else None
        cur = int((save.data.get("stats", {}).get("shop_max", {}) or {}).get(req["item"], 0))
        need = int(req["need"])
        name = item["name"] if item else req["item"]
        text = req.get("text") or f"{name} eşyasını Lv.{need}'e çıkar"
        return cur, need, cur >= need, text
    if kind == "book":
        other = BOOK_BY_KEY.get(req["book"])
        got = req["book"] in save.data.get("books_owned", [])
        text = req.get("text") or (f"Önce {other['name']}'nı aç" if other else "Başka bir kitabı aç")
        return (1 if got else 0), 1, got, text
    cur = save.data.get("stats", {}).get(req["stat"], 0) or 0
    need = req["need"]
    return cur, need, cur >= need, req.get("text", "")


def book_progress(save, book):
    """Kitabın görev ilerlemesi: (tamamlanan şart, toplam şart, hepsi tamam mı).

    Şartı olmayan kitaplar için (1, 1, True) döner — artık böyle bir kitap
    yok ama eski kayıt/rozet kodları bu biçimi bekliyor.
    """
    reqs = book_reqs(book)
    if not reqs:
        return 1, 1, True
    done = 0
    for r in reqs:
        if book_req_state(save, r)[2]:
            done += 1
    return done, len(reqs), done >= len(reqs)


def book_frac(save, book):
    """Kitabın görevlerindeki ORTALAMA ilerleme (0..1) — sıralama ve çubuk için."""
    reqs = book_reqs(book)
    if not reqs:
        return 1.0
    tot = 0.0
    for r in reqs:
        cur, need, done, _ = book_req_state(save, r)
        tot += 1.0 if done else clamp(cur / max(1, need), 0.0, 1.0)
    return tot / len(reqs)


# Geriye dönük uyumluluk: kodun eski adı beklediği yerler için.
RUN_UPGRADES = BOOKS


def draw_book(surf, cx, cy, h, book, t=0.0, locked=False, glow=True):
    """Kapalı bir kitabı çizer.

    Kitap artık düz bir dikdörtgen değil: arka kapak (kalınlık hissi), tek
    tek görünen sayfa kenarları, yaldızlı kesim, kabartmalı deri kapak,
    madalyon içine oturtulmuş amblem, cilt bantları ve aşağı sarkan bir
    ayraç kurdelesi var.

    h = kitabın yüksekliği (piksel). Genişlik orantılı hesaplanır, böylece
    aynı fonksiyon hem küçük kartlarda hem de büyük önizlemede kullanılabilir.
    """
    base = book["color"]
    col = mix_col(base, (88, 92, 110), 0.74) if locked else base
    w = h * 0.74
    x0, y0 = cx - w / 2, cy - h / 2
    # Kilitli kitap sallanmaz — raftaki ölü ağırlık gibi durur.
    sway = 0.0 if locked else math.sin(t * 1.8 + cx * 0.01) * (h * 0.018)
    y0 += sway
    ccy = y0 + h / 2

    rare = bool(book.get("rare")) and not locked
    gild = (245, 210, 122) if rare else ((200, 194, 172) if not locked else (120, 122, 134))
    spine_w = max(3.0, w * 0.17)

    if glow and not locked:
        k = .30 + .12 * math.sin(t * 3 + cx * 0.02)
        add_glow(surf, cx, ccy, h * 0.74, col, k)
        if rare:
            add_glow(surf, cx, ccy, h * 0.52, (255, 226, 150), .18 + .10 * math.sin(t * 4.4 + cx * 0.02))

    # ---- arka kapak: kitaba kalınlık kazandırır ----
    back = pygame.Rect(int(x0 + w * 0.06), int(y0 + h * 0.026), int(w * 0.92), int(h))
    pygame.draw.rect(surf, OUTLINE, back.inflate(4, 4), border_radius=5)
    pygame.draw.rect(surf, scale_col(col, 0.42), back, border_radius=5)

    # ---- sayfa bloğu ----
    pages = pygame.Rect(int(x0 + spine_w), int(y0 + h * 0.035), int(w - spine_w * 0.4), int(h * 0.93))
    pygame.draw.rect(surf, OUTLINE, pages.inflate(4, 4), border_radius=3)
    pygame.draw.rect(surf, (240, 235, 216) if not locked else (128, 130, 142), pages, border_radius=3)
    # yaldızlı kesim (nadir kitapta altın, normalde kirli beyaz)
    gw = max(2, int(w * 0.055))
    pygame.draw.rect(surf, gild, (pages.right - gw, pages.y + 1, gw, pages.h - 2), border_radius=2)
    # tek tek sayfa kenarları
    n_lines = int(clamp(h * 0.10, 3, 14))
    for i in range(n_lines):
        ly = int(pages.y + 4 + (pages.h - 8) * i / max(1, n_lines - 1))
        pygame.draw.line(surf, (198, 192, 172) if not locked else (106, 108, 120),
                         (pages.right - int(w * 0.13), ly), (pages.right - gw - 1, ly), 1)

    # ---- ön kapak ----
    cover = pygame.Rect(int(x0), int(y0), int(w * 0.92), int(h))
    pygame.draw.rect(surf, OUTLINE, cover.inflate(4, 4), border_radius=5)
    pygame.draw.rect(surf, col, cover, border_radius=5)
    # deri dokusu: üstte açık, altta koyu iki bant
    pygame.draw.rect(surf, lighten(col, 0.30),
                     (cover.x + 2, cover.y + 2, cover.w - 4, max(2, int(h * 0.10))), border_radius=3)
    pygame.draw.rect(surf, scale_col(col, 0.74),
                     (cover.x + 2, cover.bottom - max(2, int(h * 0.09)) - 2,
                      cover.w - 4, max(2, int(h * 0.09))), border_radius=3)

    # ---- cilt (sırt) + kabartma bantlar ----
    spine = pygame.Rect(int(x0), int(y0), int(spine_w), int(h))
    pygame.draw.rect(surf, scale_col(col, 0.55), spine, border_radius=4)
    for fy in (0.22, 0.52, 0.80):
        by = int(y0 + h * fy)
        pygame.draw.line(surf, lighten(col, 0.22), (spine.x + 1, by), (spine.right - 1, by), max(1, int(h * 0.016)))
    pygame.draw.line(surf, scale_col(col, 0.36), (spine.right, spine.y + 2), (spine.right, spine.bottom - 2), 1)

    # ---- kapak çerçevesi + köşe perçinleri ----
    inner = cover.inflate(int(-w * 0.22), int(-h * 0.16))
    inner.x += int(spine_w * 0.45)
    frame_col = scale_col(col, 0.48) if locked else gild
    pygame.draw.rect(surf, frame_col, inner, width=max(1, int(h * 0.012)), border_radius=3)
    stud_r = max(1, int(h * 0.022))
    if stud_r >= 2:
        for sx, sy in ((inner.x, inner.y), (inner.right, inner.y),
                       (inner.x, inner.bottom), (inner.right, inner.bottom)):
            pygame.draw.circle(surf, frame_col, (int(sx), int(sy)), stud_r)

    # ---- madalyon + amblem ----
    med_r = max(4, int(h * 0.15))
    mx, my = inner.centerx, inner.centery
    pygame.draw.circle(surf, scale_col(col, 0.62), (int(mx), int(my)), med_r)
    pygame.draw.circle(surf, frame_col, (int(mx), int(my)), med_r, 1)
    em_col = (158, 162, 178) if locked else lighten(col, 0.62)
    draw_icon(surf, mx, my, book.get("icon", "star"), em_col, max(4, h * 0.155))

    # ---- ayraç kurdelesi ----
    # Sayfaların arasına konmuş bir ayraç gibi kitabın ÜSTÜNDEN çıkar.
    # (Aşağı sarktığında kartlarda ve okuma ekranında kitabın hemen altındaki
    #  başlık yazısının üstüne biniyordu.)
    rb_w = max(2, int(w * 0.09))
    rb_x = int(cover.right - w * 0.30)
    rb_len = h * (0.13 + 0.02 * math.sin(t * 2.2 + cx * 0.02))
    rb_col = (226, 78, 92) if not locked else (96, 88, 100)
    rb_top = cover.y - rb_len
    pygame.draw.rect(surf, scale_col(rb_col, 0.7), (rb_x, int(rb_top), rb_w, int(rb_len + h * 0.05)))
    pygame.draw.polygon(surf, rb_col, [
        (rb_x, rb_top), (rb_x + rb_w, rb_top), (rb_x + rb_w / 2, rb_top + rb_w * 0.8)])

    if locked:
        # ---- zincir + asma kilit ----
        cyy = int(y0 + h * 0.62)
        pygame.draw.rect(surf, (52, 55, 70), (int(x0 - 2), cyy - max(2, int(h * 0.035)),
                                              int(w + 4), max(4, int(h * 0.07))), border_radius=3)
        pygame.draw.rect(surf, (96, 102, 124), (int(x0 - 2), cyy - max(2, int(h * 0.035)),
                                                int(w + 4), max(4, int(h * 0.07))), width=1, border_radius=3)
        lx, ly = cx + w * 0.02, cyy + h * 0.02
        arc_r = pygame.Rect(int(lx - h * 0.095), int(ly - h * 0.175), int(h * 0.19), int(h * 0.19))
        pygame.draw.arc(surf, (214, 220, 236), arc_r, 0.2, math.pi - 0.2, max(2, int(h * 0.022)))
        body = pygame.Rect(int(lx - h * 0.105), int(ly - h * 0.065), int(h * 0.21), int(h * 0.16))
        pygame.draw.rect(surf, OUTLINE, body.inflate(2, 2), border_radius=3)
        pygame.draw.rect(surf, (222, 226, 240), body, border_radius=3)
        pygame.draw.circle(surf, (70, 74, 92), body.center, max(1, int(h * 0.024)))
    elif rare:
        # ---- nadir kitap: kapakta dönen parıltılar ----
        for i in range(3):
            a = t * 1.8 + i * math.tau / 3
            sx = cover.centerx + math.cos(a) * w * 0.32
            sy = cover.centery + math.sin(a) * h * 0.34
            sp = 0.5 + 0.5 * math.sin(t * 5 + i * 2.1)
            sz = max(1, int(1 + sp * 2.2))
            pygame.draw.circle(surf, (255, 242, 196), (int(sx), int(sy)), sz)
            if sz >= 2:
                pygame.draw.line(surf, (255, 248, 220), (sx - sz * 2, sy), (sx + sz * 2, sy), 1)
                pygame.draw.line(surf, (255, 248, 220), (sx, sy - sz * 2), (sx, sy + sz * 2), 1)


def draw_book_open(surf, rect, book, t=0.0, locked=False):
    """Açık kitabı (iki sayfalık yayılım) çizer ve metin yazılabilecek
    SOL ve SAĞ sayfa dikdörtgenlerini döndürür.

    Kitaplık'ta bir kitaba tıklandığında kitap gerçekten "açılır"; okuma
    penceresi bu fonksiyonun döndürdüğü sayfalara yazılır.
    """
    base = book["color"]
    col = mix_col(base, (88, 92, 110), 0.74) if locked else base
    rare = bool(book.get("rare")) and not locked
    gild = (245, 210, 122) if rare else (206, 200, 178)
    paper = (243, 238, 220) if not locked else (228, 226, 226)
    ink_line = (214, 206, 184) if not locked else (200, 198, 200)

    # ---- kapak tabakası (sayfaların altından taşar) ----
    pygame.draw.rect(surf, OUTLINE, rect.inflate(8, 8), border_radius=12)
    pygame.draw.rect(surf, scale_col(col, 0.58), rect, border_radius=11)
    pygame.draw.rect(surf, col, rect.inflate(-4, -4), border_radius=10)
    pygame.draw.rect(surf, gild, rect.inflate(-10, -10), width=1, border_radius=9)

    # ---- ayraç kurdelesi: sayfaların ALTINA çizilir, sadece ucu görünür ----
    if not locked:
        rb_w = max(3, int(rect.w * 0.014))
        rb_x = int(rect.right - rect.w * 0.26)
        pygame.draw.rect(surf, (168, 52, 64), (rb_x, rect.y - 16, rb_w, 40))
        pygame.draw.polygon(surf, (226, 78, 92), [
            (rb_x, rect.y - 16), (rb_x + rb_w, rect.y - 16), (rb_x + rb_w / 2, rect.y - 16 + rb_w * 1.6)])

    # ---- iki sayfa ----
    pad = max(8, int(rect.h * 0.035))
    gutter = max(10, int(rect.w * 0.022))
    page_w = (rect.w - pad * 2 - gutter) / 2
    left = pygame.Rect(int(rect.x + pad), int(rect.y + pad), int(page_w), int(rect.h - pad * 2))
    right = pygame.Rect(int(left.right + gutter), left.y, int(page_w), left.h)
    for pg in (left, right):
        pygame.draw.rect(surf, (188, 182, 160), pg.inflate(3, 3), border_radius=4)
        pygame.draw.rect(surf, paper, pg, border_radius=4)

    # ---- cilt (orta) gölgesi: sayfaların içe kıvrıldığı his ----
    sh = pygame.Surface((gutter + 34, left.h), pygame.SRCALPHA)
    for i in range(sh.get_width()):
        k = abs(i - sh.get_width() / 2) / (sh.get_width() / 2)
        a = int(96 * (1.0 - k) ** 1.6)
        if a > 0:
            pygame.draw.line(sh, (40, 32, 22, a), (i, 0), (i, left.h))
    surf.blit(sh, (int(left.right - 17), left.y))
    pygame.draw.line(surf, scale_col(col, 0.45),
                     (int(left.right + gutter / 2), left.y), (int(left.right + gutter / 2), left.bottom), 2)

    # ---- satır çizgileri (kağıt hissi) ----
    for pg in (left, right):
        yy = pg.y + int(pg.h * 0.30)
        while yy < pg.bottom - 14:
            pygame.draw.line(surf, ink_line, (pg.x + 16, yy), (pg.right - 16, yy), 1)
            yy += 22

    return left, right


# =====================================================================
# ARENA SINIRLARI  ·  DÜNYA ve KAMERA
# ---------------------------------------------------------------------
# v3.3'e kadar arena ekranla aynı boyuttaydı: tek ekran, kamera yok.
# Artık DÜNYA, ekrandaki oyun penceresinin 3x3'ü kadar: eski dikdörtgenin
# üstüne, altına, sağına, soluna ve dört çaprazına birer dikdörtgen daha
# eklendi (toplam 9 hücre). Dünyanın dışı hâlâ çıkılmaz duvardır.
#
#   VIEW_RECT  : dünyanın EKRANDA göründüğü pencere (eski arena dikdörtgeni)
#   ARENA_RECT : DÜNYA sınırları (oyun mantığı hep bunu kullanır)
#   kamera     : RunState.cam_x / cam_y — oyuncuyu yumuşak takip eder ve
#                dünyanın dışını göstermeyecek şekilde sınırlanır.
#
# Çizim düzeni: bütün dünya nesneleri tek bir BÜYÜK "dünya yüzeyine" kendi
# dünya koordinatlarıyla çizilir (yani hiçbir çizim kodu değişmek zorunda
# kalmaz), sonra yalnızca kameranın gördüğü dikdörtgen ekrana kopyalanır.
# =====================================================================
ARENA_MARGIN_TOP = 76
ARENA_MARGIN_BOTTOM = 10
ARENA_MARGIN_SIDE = 8

# Dünyanın ekranda göründüğü pencere (eski arena ile birebir aynı yer).
VIEW_RECT = pygame.Rect(
    ARENA_MARGIN_SIDE, ARENA_MARGIN_TOP,
    VIRTUAL_W - ARENA_MARGIN_SIDE * 2,
    VIRTUAL_H - ARENA_MARGIN_TOP - ARENA_MARGIN_BOTTOM)

# Dünya kaç "ekran" büyüklüğünde: 3x3 (orta hücre + 4 yön + 4 çapraz).
WORLD_TILES_X = 3
WORLD_TILES_Y = 3
ARENA_RECT = pygame.Rect(0, 0, VIEW_RECT.w * WORLD_TILES_X, VIEW_RECT.h * WORLD_TILES_Y)

# Dünya yüzeyi bir kez ayrılır (her karede yeniden ayırmak çok pahalı olurdu).
_WORLD_SURFACE = None


def world_surface():
    global _WORLD_SURFACE
    if _WORLD_SURFACE is None:
        _WORLD_SURFACE = pygame.Surface((ARENA_RECT.w, ARENA_RECT.h)).convert()
    return _WORLD_SURFACE


def world_to_screen(x, y, cam):
    """Dünya koordinatını ekran koordinatına çevirir."""
    return (VIEW_RECT.x + (x - cam.x), VIEW_RECT.y + (y - cam.y))


def screen_to_world(x, y, cam):
    """Ekran koordinatını (fare) dünya koordinatına çevirir."""
    return (cam.x + (x - VIEW_RECT.x), cam.y + (y - VIEW_RECT.y))


# =====================================================================
# OYUNCU
# =====================================================================

# Oyuncunun TABAN istatistikleri tek bir yerde durur. Hem Player.__init__
# hem de İSTATİSTİK paneli (yüzdeleri buna göre hesaplar) aynı değerleri
# kullansın diye sabit olarak çıkarıldı.
BASE_SPEED = 215
BASE_MAX_HP = 100
BASE_DMG = 17
BASE_ATK_CD = 0.34
BASE_PICKUP = 60
BASE_DASH_CD = 2.4
BASE_BONK_CD = 1.35


class Player:
    def __init__(self, skin_id="default"):
        self.skin = get_skin(skin_id)
        self.color = self.skin["color"]
        self.cosmetics = {"hat": None, "eyewear": None, "cape": None}
        self.x = ARENA_RECT.centerx
        self.y = ARENA_RECT.centery
        self.radius = 16
        self.vx = self.vy = 0.0
        self.kbx = self.kby = 0.0

        # --- taban istatistikler (herkes eşit başlar) ---
        self.base_speed = BASE_SPEED
        self.base_max_hp = BASE_MAX_HP
        self.base_dmg = BASE_DMG
        self.base_atk_cd = BASE_ATK_CD
        self.base_pickup = BASE_PICKUP
        self.base_armor = 0.0
        self.base_regen = 0.0
        self.coin_mult = 1.0
        self.xp_mult = 1.0
        self.crit_chance = 0.05
        self.crit_dmg_mult = 1.6
        self.bonk_mult = 1.0
        self.bonk_radius_mult = 1.0

        # --- run-içi (geçici) ---
        self.run_dmg_mult = 1.0
        self.run_spd_mult = 1.0
        self.run_aspd_mult = 1.0
        self.run_pickup_mult = 1.0
        self.run_armor_bonus = 0.0
        self.run_coin_mult = 1.0
        self.run_xp_mult = 1.0
        self.run_regen_bonus = 0.0
        self.run_crit_bonus = 0.0
        self.run_critdmg_bonus = 0.0
        self.dmg_taken_mult = 1.0
        self.enemy_hp_curse = 0.0
        self.dash_cd_mult = 1.0
        self.dash_dist_mult = 1.0
        self.bonk_cd_mult = 1.0
        self.proj_speed_mult = 1.0

        self.fire_level = 0
        self.ice_level = 0
        self.poison_level = 0
        # --- kitaplara özel (markette SATILMAYAN) etkiler ---
        self.kill_heal = 0.0        # düşman öldürünce kazanılan can
        self.rage_level = 0         # canın yarısı altındayken hasar bonusu
        self.lowhp_armor = 0.0      # canın %30'u altındayken ek hasar azaltma
        self.dash_slow_level = 0    # dash atınca çevredekileri yavaşlatır
        self.boss_hunter = 0        # patron/elit hedeflere ek hasar
        self.swarm_level = 0        # kalabalıkta hasar bonusu
        self.echo_level = 0         # her 4. atış çift hasar
        self.echo_count = 0         # atış sayacı (Yankı Kitabı)
        self.roar_level = 0         # BONK düşmanları korkutup kaçırır
        self.run_healed = 0.0       # bu koşuda toplam yenilenen can (görevler için)
        self.run_crits = 0          # bu koşuda atılan kritik sayısı
        self.run_bonks = 0          # bu koşuda kullanılan BONK sayısı
        self.run_shots = 0          # bu koşuda ateşlenen mermi sayısı
        self.run_lifesteal = 0.0    # bu koşuda KAN EMİCİ ile çalınan can
        self.multishot_level = 0
        self.pierce_bonus = 0
        self.shield_charges = 0
        self.explosive_level = 0
        self.vamp_level = 0
        self.thorns_level = 0
        self.chain_level = 0
        self.homing_level = 0
        self.frenzy_level = 0
        self.frenzy_stacks = 0
        self.frenzy_timer = 0.0
        self.second_wind_charges = 0
        # --- CEHENNEM eşyaları ---
        self.holy_flame = 0         # vuruşlarda kutsal yanık
        self.soul_harvest = 0       # öldürmede can + yığılan hasar
        self.soul_stacks = 0
        self.soul_timer = 0.0
        self.angel_wing = 0         # dash sonrası uzun dokunulmazlık
        self.purgatory_level = 0    # ölümcül darbeyi engelleyen kalkan
        self.purgatory_timer = 0.0  # yeniden dolma sayacı
        self.execute_threshold = 0.0
        self.orbit_level = 0
        self.orbit_angle = 0.0
        self.storm_level = 0
        self.storm_timer = 2.0
        self.shop_levels = {}
        # --- PATRON SANDIĞINDAN ÇIKAN SİLAHLAR ---
        # {silah_anahtarı: seviye} ve {silah_anahtarı: kalan bekleme}.
        # Silahlar otomatik ateşlenir; bkz. RunState.update_boss_weapons().
        self.weapons = {}
        self.weapon_timers = {}

        # --- SKİN ÖZEL YETENEĞİ (ULTİ) ---
        # Her skinin bir özel yeteneği var; otomatik çalışır ve bekleme süresi
        # ekranın altındaki yetenek çubuğunda görünür.
        self.ult = get_skin_ult(self.skin["id"])
        self.ult_cd = float(self.ult["cd"]) if self.ult else 0.0
        self.ult_timer = self.ult_cd          # kalan bekleme süresi
        self.ult_trigger = None               # bu karede tetiklenen yetenek anahtarı
        self.ult_fx_t = 0.0                   # yetenek çalıştığında kısa parlama
        self.temp_buffs = []                  # [kalan süre, {alan: değişim}]
        self.crit_forced = 0.0                # > 0 iken her vuruş kritik
        self.extra_orbit = 0                  # geçici ek yörünge bıçağı
        self.thorn_field_t = 0.0              # DİKEN TARLASI kalan süresi
        self.thorn_field_r = 0.0
        self.thorn_field_tick = 0.0

        self.bonk_cd = BASE_BONK_CD
        # YEŞİL DEV: "EZİCİ DARBE" — periyodik, tüm arenayı kaplayan BONK.
        self.titan_smash = 0        # 1 ise ezici darbe açık
        self.smash_timer = 0.0      # ezici darbenin bekleme sayacı

        # --- SKIN BAŞLANGIÇ BONUSLARI (perk) ---
        # DİKKAT: perk'ler buradan SONRA hiçbir alanı yeniden atamamalı;
        # aksi hâlde skinin verdiği değer varsayılanla ezilir.
        # Bazı skinler kalıcı elmasla alınan özel yeteneklerle gelir; bu bonuslar
        # taban istatistikler belirlendikten hemen sonra, türetilmiş değerler
        # (max_hp, hp vb.) hesaplanmadan ÖNCE uygulanır.
        for attr, delta in self.skin.get("perk_add", {}).items():
            setattr(self, attr, getattr(self, attr, 0) + delta)
        for attr, val in self.skin.get("perk_set", {}).items():
            setattr(self, attr, val)

        self._cosmetic_perks_applied = False

        self.max_hp = self.base_max_hp
        self.hp = float(self.max_hp)
        self.level = 1
        self.xp = 0.0
        self.xp_to_next = 22

        self.atk_timer = 0.0
        # NOT: bonk_cd yukarıda, skin perk'lerinden ÖNCE tanımlanır — burada
        # yeniden atanırsa Yeşil Dev'in 5 saniyelik BONK perk'i ezilir.
        self.bonk_timer = 0.0
        self.dash_cd_timer = 0.0
        self.dash_time = 0.0
        self.dash_dx = self.dash_dy = 0.0
        self.dash_speed = 0.0
        self.dash_count = 0
        self.invuln = 0.0
        self.shield_icd = 0.0
        self.hit_flash = 0.0
        self.hurt_vig = 0.0
        self.recoil = 0.0
        self.flash_t = 0.0
        self.move_in = (0.0, 0.0)
        self.aim_dir = (0.0, -1.0)
        self.move_anim = 0.0
        self.speed_now = 0.0
        self.alive = True
        self.regen_acc = 0.0
        self.aura_acc = 0.0
        # --- PATRON DURUM ETKİLERİ ---
        # Patronlar artık hepsi aynı biçimde vurmuyor: kimi seni YAKIYOR,
        # kimi ZEHİRLİYOR, kimi YAVAŞLATIYOR. Üçü de burada tutulur ve
        # Player.update() içinde işlenir.
        self.burn_t = 0.0        # yanık kalan süre
        self.burn_dps = 0.0      # yanığın saniyelik hasarı
        self.burn_acc = 0.0
        self.poison_t = 0.0      # zehir kalan süre
        self.poison_dps = 0.0
        self.poison_acc = 0.0
        self.slow_t = 0.0        # yavaşlatma kalan süre
        self.slow_mult = 1.0     # hareket hızı çarpanı (1.0 = etkisiz)
        self.ghosts = []
        self.ghost_t = 0.0
        self.last_hit_by = ""

    def apply_cosmetic_perks(self):
        """Kuşanılmış kıyafetlerin (şapka / gözlük / pelerin) verdiği küçük kalıcı
        bonusları uygular. RunState, self.cosmetics atandıktan hemen sonra çağırır."""
        if self._cosmetic_perks_applied:
            return
        self._cosmetic_perks_applied = True
        for slot in ("hat", "eyewear", "cape"):
            cid = (self.cosmetics or {}).get(slot)
            item = COSMETIC_BY_ID.get(cid) if cid else None
            if not item:
                continue
            for attr, delta in item.get("perk_add", {}).items():
                setattr(self, attr, getattr(self, attr, 0) + delta)
            for attr, val in item.get("perk_set", {}).items():
                setattr(self, attr, val)

        self.max_hp = self.base_max_hp
        self.hp = float(self.max_hp)

    # ---- türetilmiş istatistikler ----
    def body_color(self, t):
        if self.skin["id"] == "prism":
            return hue_col(t * 0.35)
        return self.skin["color"]

    def eff_speed(self):
        sp = self.base_speed * self.run_spd_mult * (1 + 0.05 * self.frenzy_stacks)
        # Patron yavaşlatması (KOLOS'un sarsıntısı gibi) hızı doğrudan keser.
        if self.slow_t > 0:
            sp *= self.slow_mult
        return sp

    def eff_dmg(self):
        d = self.base_dmg * self.run_dmg_mult * (1 + 0.07 * self.frenzy_stacks)
        # RUH HASADI: art arda öldürdükçe hasar yığılır.
        if self.soul_stacks > 0:
            d *= (1.0 + 0.04 * self.soul_stacks)
        # ÖFKE KİTABI: canın yarısının altındayken hasar belirgin artar.
        if self.rage_level > 0 and self.max_hp > 0 and self.hp < self.max_hp * 0.5:
            d *= (1.0 + 0.35 * self.rage_level)
        return d

    def eff_atk_cd(self):
        return max(0.07, self.base_atk_cd / self.run_aspd_mult)

    def eff_pickup(self):
        return self.base_pickup * self.run_pickup_mult

    def eff_armor(self):
        a = self.base_armor + self.run_armor_bonus
        # SON UMUT KİTABI: canın %30'unun altındayken ek hasar azaltma.
        if self.lowhp_armor > 0 and self.max_hp > 0 and self.hp < self.max_hp * 0.3:
            a += self.lowhp_armor
        return clamp(a, 0, 0.6)

    def eff_regen(self):
        return self.base_regen + self.run_regen_bonus

    def eff_coin_mult(self):
        return self.coin_mult * self.run_coin_mult

    def eff_xp_mult(self):
        return self.xp_mult * self.run_xp_mult

    def estimated_dps(self):
        """Oyuncunun patrona karşı kabaca saniyede verebileceği hasar.

        Patron canını oyuncunun GÜCÜNE göre ölçeklemek için kullanılır;
        böylece patron dövüşü hem yeni başlayan hem de eşyalarını doldurmuş
        bir oyuncuda yaklaşık aynı süre kadar sürer. Kesin olması gerekmez,
        büyüklük sırası yeterlidir.
        """
        shots = 1 + self.multishot_level
        cd = max(0.05, self.eff_atk_cd())
        crit = 1.0 + self.eff_crit_chance() * (self.eff_crit_dmg() - 1.0)
        dmg = self.eff_dmg()
        dps = dmg * shots * crit / cd
        # Tek hedefe (patrona) vururken delme fazladan hasar getirmez; buna
        # karşılık yan etkiler (zincir, fırtına, yörünge, ateş, zehir, yankı)
        # kaba bir pay olarak eklenir.
        extra = 1.0
        extra += 0.25 * self.echo_level     # doğrudan hasar katlar
        extra += 0.03 * self.chain_level    # asıl işi kalabalıkta
        extra += 0.04 * self.storm_level
        extra += 0.03 * self.orbit_level
        extra += 0.04 * self.fire_level     # yanık patronda da işler
        extra += 0.05 * self.poison_level
        dps *= extra
        # BONK: bekleme süresine bölünmüş alan hasarı
        dps += (dmg * 2.0 * self.bonk_mult) / max(1.0, self.eff_bonk_cd())
        return max(1.0, dps)

    def eff_crit_chance(self):
        # SESSİZ PUSU gibi yetenekler kısa süre "her vuruş kritik" verir.
        if self.crit_forced > 0:
            return 1.0
        return clamp(self.crit_chance + self.run_crit_bonus, 0, 0.9)

    def eff_crit_dmg(self):
        return self.crit_dmg_mult + self.run_critdmg_bonus

    def eff_pierce_hits(self):
        return 1 + self.pierce_bonus

    def eff_bonk_radius(self):
        return 138 * self.bonk_radius_mult

    def eff_bonk_cd(self):
        return max(0.45, self.bonk_cd * self.bonk_cd_mult)

    def eff_dash_cd(self):
        return max(0.7, BASE_DASH_CD * self.dash_cd_mult)

    def vamp_cap(self):
        return 2.0

    # Bazı "seviye atlama" yükseltmeleri, oyun-içi MARKET'teki aynı gücün bir
    # kopyasıdır (örn. "Yıldırım" ödülü == MARKET'teki "Fırtına"). İkisi aynı
    # sayaçları paylaşsın diye eşleştirme burada tutulur.
    RUN_TO_SHOP_KEY = {
        "r_fireshot": "fire", "r_iceshot": "ice", "r_multi": "multishot",
        "r_pierce": "pierce", "r_vamp": "vampiric", "r_second_wind": "second_wind",
        "r_orbit": "orbit", "r_storm": "storm",
    }

    def apply_run_upgrade(self, key):
        if key == "r_dmg": self.run_dmg_mult += 0.15
        elif key == "r_spd": self.run_spd_mult += 0.10
        elif key == "r_aspd": self.run_aspd_mult += 0.12
        elif key == "r_hp":
            gain = max(20, int(self.max_hp * 0.25))
            self.max_hp += gain
            self.hp = min(self.max_hp, self.hp + gain)
        elif key == "r_mag": self.run_pickup_mult += 0.25
        elif key == "r_armor": self.run_armor_bonus += 0.04
        elif key == "r_coin": self.run_coin_mult += 0.18
        elif key == "r_xp": self.run_xp_mult += 0.18
        elif key == "r_regen": self.run_regen_bonus += 0.5
        elif key == "r_crit": self.run_crit_bonus += 0.06
        elif key == "r_critd": self.run_critdmg_bonus += 0.30
        elif key == "r_bonk":
            self.bonk_mult += 0.22
            self.bonk_radius_mult += 0.12
        elif key == "r_dashcd": self.dash_cd_mult = max(0.35, self.dash_cd_mult - 0.15)
        elif key == "r_bonkcd": self.bonk_cd_mult = max(0.35, self.bonk_cd_mult - 0.15)
        elif key == "r_pspeed": self.proj_speed_mult += 0.18
        elif key == "r_fireshot": self.fire_level += 1
        elif key == "r_iceshot": self.ice_level += 1
        elif key == "r_poison": self.poison_level += 1
        elif key == "r_killheal": self.kill_heal += 3.0
        elif key == "r_rage": self.rage_level += 1
        elif key == "r_lasthope": self.lowhp_armor += 0.20
        elif key == "r_dashslow": self.dash_slow_level += 1
        elif key == "r_bosshunter": self.boss_hunter += 1
        elif key == "r_swarm": self.swarm_level += 1
        elif key == "r_echo": self.echo_level += 1
        elif key == "r_roar": self.roar_level += 1
        elif key == "r_hp_big":
            self.max_hp = int(self.max_hp * 1.40)
            self.hp = min(self.max_hp, self.hp + self.max_hp * 0.40)
            self.base_speed = max(60, self.base_speed - 18)
        elif key == "r_multi": self.multishot_level += 1
        elif key == "r_pierce": self.pierce_bonus += 1
        elif key == "r_vamp": self.vamp_level += 1
        elif key == "r_execute": self.execute_threshold = min(0.35, self.execute_threshold + 0.10)
        elif key == "r_second_wind": self.second_wind_charges += 1
        elif key == "r_orbit": self.orbit_level += 1
        elif key == "r_storm": self.storm_level += 1
        # MARKET'teki karşılığı varsa (örn. Yıldırım -> Fırtına), o sayaç da
        # birlikte artsın; market ekranı gerçek seviyeyi doğru göstersin.
        shop_key = self.RUN_TO_SHOP_KEY.get(key)
        if shop_key:
            self.shop_levels[shop_key] = self.shop_levels.get(shop_key, 0) + 1

    def gain_xp(self, amount):
        amount *= self.eff_xp_mult()
        self.xp += amount
        leveled = 0
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.24 + 8)
            leveled += 1
        return leveled

    def take_damage(self, amount, fx, sx=None, sy=None, src=""):
        """Artık genel 'hasar aldıktan sonra dokunulmazlık' YOK: aynı anda
        birden fazla düşman/mermi hasar verebilir. Yalnızca dash ve
        diriliş dokunulmazlık verir."""
        if not self.alive or self.invuln > 0:
            return 0
        if self.shield_charges > 0:
            if self.shield_icd > 0:
                return 0
            self.shield_charges -= 1
            self.shield_icd = 0.35
            fx.ring(self.x, self.y, (160, 200, 255), n=14, speed=160, life=0.3, r=2.5)
            fx.shockwave(self.x, self.y, 46, (160, 200, 255), 0.25, 3)
            fx.popup(self.x, self.y - 34, "KALKAN!", (160, 200, 255), 18, life=0.6)
            sfx("shield", 1.0, 0.05)
            return 0
        dmg = amount * (1 - self.eff_armor()) * self.dmg_taken_mult
        self.hp -= dmg
        self.hit_flash = 0.3
        self.hurt_vig = min(1.0, self.hurt_vig + dmg / 45.0)
        if src:
            self.last_hit_by = src
        if sx is not None:
            kx, ky = norm_dir(sx, sy, self.x, self.y)
            self.kbx += kx * 170
            self.kby += ky * 170
        fx.shake(5 + min(7, dmg * 0.18), 0.2)
        fx.burst(self.x, self.y, RED, n=6, speed=120, life=0.35, r=3)
        fx.popup(self.x + random.uniform(-10, 10), self.y - 26, f"-{int(dmg)}", (255, 110, 120), 20, life=0.7)
        sfx("hurt", 0.9, 0.08)
        self._resolve_lethal(fx)
        return dmg

    def _resolve_lethal(self, fx):
        """Can sıfırın altına düştüyse ölümü engelleyen güçleri sırayla dener.

        Hem doğrudan darbeler (take_damage) hem de YANIK / ZEHİR gibi süreli
        etkiler buradan geçer; böylece "ikinci nefes" bir alev hasarıyla
        ölürken de çalışır.
        """
        if self.hp > 0 or not self.alive:
            return
        if self.ult and self.ult.get("kind") == "death_defy" and self.ult_ready():
            # GÖLGE DURUŞU: ölümcül darbede can 1'e sabitlenir ve zaman durur.
            # Canın 10 iken 15'lik hasar yesen bile ölmezsin.
            self.hp = 1.0
            self.ult_trigger = "death_defy"
            self.start_ult_cooldown()
            self.invuln = max(self.invuln, float(self.ult.get("duration", 5.0)) + 0.4)
            fx.do_flash((170, 110, 255), 0.5)
            fx.ring(self.x, self.y, (190, 120, 255), n=30, speed=300, life=0.6, r=4)
            fx.popup(self.x, self.y - 48, "GÖLGE DURUŞU!", (200, 140, 255), 28, life=1.3)
            sfx("second", 1.0, 0.0)
            return
        if self.purgatory_level > 0 and self.purgatory_timer <= 0:
            # ARAF KALKANI: ölümcül darbeyi tamamen yutar, sonra yeniden dolar.
            self.hp = max(1.0, self.max_hp * 0.12)
            self.purgatory_timer = max(8.0, 25.0 - 5.0 * (self.purgatory_level - 1))
            self.invuln = max(self.invuln, 1.2)
            fx.ring(self.x, self.y, (255, 215, 120), n=24, speed=240, life=0.5, r=3.5)
            fx.shockwave(self.x, self.y, 170, (255, 215, 120), 0.45, 6)
            fx.popup(self.x, self.y - 44, "ARAF KALKANI!", (255, 225, 150), 24, life=1.1)
            sfx("shield", 1.0, 0.0)
            return
        if self.second_wind_charges > 0:
            self.second_wind_charges -= 1
            self.hp = self.max_hp * 0.5
            self.invuln = 1.6
            fx.ring(self.x, self.y, GOLD, n=26, speed=260, life=0.55, r=4)
            fx.shockwave(self.x, self.y, 220, GOLD, 0.5, 7)
            fx.popup(self.x, self.y - 46, "İKİNCİ NEFES!", GOLD, 26, life=1.2)
            fx.do_flash(GOLD, 0.6)
            sfx("second", 1.0, 0.0)
            return
        self.hp = 0
        self.alive = False

    # ---------------- DURUM ETKİLERİ (patronlar uygular) ----------------
    def apply_burn(self, dps, dur, src="alev"):
        """YANIK: süreli, saniyede hasar veren ateş. En güçlüsü geçerlidir."""
        if not self.alive:
            return
        fresh = self.burn_t <= 0
        self.burn_dps = max(self.burn_dps, dps)
        self.burn_t = max(self.burn_t, dur)
        self.last_hit_by = src
        if fresh:
            sfx("hurt", 0.4, 0.05)

    def apply_poison(self, dps, dur, src="zehir"):
        """ZEHİR: yanıktan daha uzun süren, daha az vuran sızı."""
        if not self.alive:
            return
        self.poison_dps = max(self.poison_dps, dps)
        self.poison_t = max(self.poison_t, dur)
        self.last_hit_by = src

    def apply_slow(self, mult, dur):
        """YAVAŞLATMA: hareket hızını kısar. En sert olanı geçerlidir."""
        if not self.alive:
            return
        if self.slow_t <= 0 or mult < self.slow_mult:
            self.slow_mult = clamp(mult, 0.25, 1.0)
        self.slow_t = max(self.slow_t, dur)

    def clear_status(self):
        self.burn_t = self.poison_t = self.slow_t = 0.0
        self.burn_dps = self.poison_dps = 0.0
        self.slow_mult = 1.0

    def _status_tick(self, amount, fx, src, col):
        """Süreli etkilerin (yanık/zehir) tek bir vuruşu.

        Doğrudan darbelerden farkı: KALKAN yükü harcamaz ve geri tepme
        uygulamaz — yoksa yanık, kalkanları saniyeler içinde eritirdi.
        Dokunulmazlık (dash) ise etkiyi durdurur.
        """
        if not self.alive or amount <= 0 or self.invuln > 0:
            return
        dmg = amount * (1 - self.eff_armor()) * self.dmg_taken_mult
        self.hp -= dmg
        self.last_hit_by = src
        self.hurt_vig = min(1.0, self.hurt_vig + dmg / 90.0)
        fx.popup(self.x + random.uniform(-12, 12), self.y - 20, f"-{max(1, int(dmg))}",
                 col, 14, life=0.5)
        self._resolve_lethal(fx)

    def update_status(self, dt, fx):
        """Yanık / zehir / yavaşlatma sayaçlarını işler."""
        if self.burn_t > 0:
            self.burn_t = max(0.0, self.burn_t - dt)
            self.burn_acc += dt
            while self.burn_acc >= 0.5 and self.alive:
                self.burn_acc -= 0.5
                self._status_tick(self.burn_dps * 0.5, fx, "alev", (255, 150, 70))
            if self.burn_t <= 0:
                self.burn_dps = 0.0
        if self.poison_t > 0:
            self.poison_t = max(0.0, self.poison_t - dt)
            self.poison_acc += dt
            while self.poison_acc >= 0.5 and self.alive:
                self.poison_acc -= 0.5
                self._status_tick(self.poison_dps * 0.5, fx, "zehir", (150, 240, 120))
            if self.poison_t <= 0:
                self.poison_dps = 0.0
        if self.slow_t > 0:
            self.slow_t = max(0.0, self.slow_t - dt)
            if self.slow_t <= 0:
                self.slow_mult = 1.0

    def update(self, dt, keys, fx):
        if not self.alive:
            return
        for name in ("atk_timer", "bonk_timer", "hit_flash", "invuln", "shield_icd",
                     "dash_cd_timer", "flash_t", "hurt_vig", "smash_timer"):
            v = getattr(self, name)
            if v > 0:
                setattr(self, name, max(0.0, v - dt))
        self.recoil = max(0.0, self.recoil - dt * 7)
        self.update_status(dt, fx)
        if not self.alive:
            return
        mx = keys.get("right", 0) - keys.get("left", 0)
        my = keys.get("down", 0) - keys.get("up", 0)
        mlen = math.hypot(mx, my)
        if mlen > 0:
            mx, my = mx / mlen, my / mlen
            self.move_anim += dt * 10
        self.move_in = (mx, my)

        if self.dash_time > 0:
            self.dash_time -= dt
            self.x += self.dash_dx * self.dash_speed * dt
            self.y += self.dash_dy * self.dash_speed * dt
            self.speed_now = self.dash_speed
            self.ghost_t -= dt
            if self.ghost_t <= 0:
                self.ghost_t = 0.025
                self.ghosts.append([self.x, self.y, 0.35, self.body_color(0)])
            fx.spark(self.x, self.y, self.skin["accent"], random.uniform(-40, 40), random.uniform(-40, 40), 0.3, 3)
        else:
            sp = self.eff_speed()
            k = min(1.0, dt * 16)
            self.vx += (mx * sp - self.vx) * k
            self.vy += (my * sp - self.vy) * k
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.speed_now = math.hypot(self.vx, self.vy)
            if self.skin["aura"] == "shadow" and self.speed_now > 60:
                self.ghost_t -= dt
                if self.ghost_t <= 0:
                    self.ghost_t = 0.05
                    self.ghosts.append([self.x, self.y, 0.35, (60, 40, 100)])

        self.x += self.kbx * dt
        self.y += self.kby * dt
        d = max(0.0, 1 - dt * 9)
        self.kbx *= d
        self.kby *= d
        self.x = clamp(self.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
        self.y = clamp(self.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)

        for g in self.ghosts:
            g[2] -= dt
        self.ghosts = [g for g in self.ghosts if g[2] > 0]

        # --- SKİN YETENEĞİ: bekleme sayacı ---
        if self.ult:
            if self.ult_timer > 0:
                self.ult_timer = max(0.0, self.ult_timer - dt)
            self.ult_fx_t = max(0.0, self.ult_fx_t - dt)
        # --- geçici (süreli) bonuslar ---
        if self.temp_buffs:
            still = []
            for buf in self.temp_buffs:
                buf[0] -= dt
                if buf[0] > 0:
                    still.append(buf)
                else:
                    for attr, delta in buf[1].items():
                        setattr(self, attr, getattr(self, attr, 0) - delta)
            self.temp_buffs = still
        if self.crit_forced > 0:
            self.crit_forced = max(0.0, self.crit_forced - dt)
        # --- ARAF KALKANI yeniden dolar ---
        if self.purgatory_timer > 0:
            self.purgatory_timer = max(0.0, self.purgatory_timer - dt)
        # --- RUH HASADI yığınları zamanla söner ---
        if self.soul_timer > 0:
            self.soul_timer -= dt
            if self.soul_timer <= 0:
                self.soul_stacks = 0

        if self.frenzy_timer > 0:
            self.frenzy_timer -= dt
            if self.frenzy_timer <= 0:
                self.frenzy_stacks = 0

        if self.eff_regen() > 0 and self.hp < self.max_hp:
            self.regen_acc += self.eff_regen() * dt
            heal = int(self.regen_acc)
            if heal > 0:
                self.hp = min(self.max_hp, self.hp + heal)
                self.regen_acc -= heal

        skin_update_fx(self, dt, fx)

    def try_dash(self, fx):
        if not self.alive or self.dash_cd_timer > 0 or self.dash_time > 0:
            return False
        mx, my = self.move_in
        if abs(mx) + abs(my) < 0.1:
            mx, my = self.aim_dir
        l = math.hypot(mx, my) or 1.0
        self.dash_dx, self.dash_dy = mx / l, my / l
        dur = 0.17
        self.dash_time = dur
        self.dash_speed = 205.0 * self.dash_dist_mult / dur
        self.dash_cd_timer = self.eff_dash_cd()
        # MELEK KANADI: dash sonrası dokunulmazlık belirgin biçimde uzar.
        self.invuln = max(self.invuln, 0.26 + 0.45 * self.angel_wing)
        self.dash_count += 1
        fx.burst(self.x, self.y, self.skin["accent"], n=10, speed=150, life=0.3, r=3)
        sfx("dash", 1.0, 0.05)
        return True

    def heal(self, amount):
        if amount <= 0 or not self.alive:
            return
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        # Gerçekten yenilenen miktarı say (taşan kısım sayılmaz) — kitap
        # görevlerinde "bir koşuda X can yenile" bunun üzerinden ölçülür.
        self.run_healed += max(0.0, self.hp - before)

    def add_temp_buff(self, duration, **attrs):
        """Süreli bonus: değerler hemen eklenir, süre dolunca aynen geri alınır."""
        if duration <= 0 or not attrs:
            return
        for attr, delta in attrs.items():
            setattr(self, attr, getattr(self, attr, 0) + delta)
        self.temp_buffs.append([float(duration), dict(attrs)])

    def ult_ready(self):
        return bool(self.ult) and self.ult_timer <= 0.0

    def start_ult_cooldown(self):
        self.ult_timer = self.ult_cd
        self.ult_fx_t = 0.5

    def lifesteal(self, amount):
        """KAN EMİCİ ile can çalar ve çalınan miktarı ayrıca sayar.

        'Toplam X can çal' türü görevler/başarımlar bu sayacı kullanır; bu
        yüzden can yenileme (regen) ya da iksirle karışmaması gerekir."""
        if amount <= 0 or not self.alive:
            return
        before = self.hp
        self.heal(amount)
        self.run_lifesteal += max(0.0, self.hp - before)

    def register_kill_for_frenzy(self):
        if self.frenzy_level > 0:
            self.frenzy_stacks = min(self.frenzy_stacks + 1, 2 + self.frenzy_level * 2)
            self.frenzy_timer = 3.0

    def set_aim(self, dx, dy):
        if abs(dx) > 1e-4 or abs(dy) > 1e-4:
            self.aim_dir = (dx, dy)

    def try_attack(self):
        if self.atk_timer <= 0:
            self.atk_timer = self.eff_atk_cd()
            return True
        return False

    def try_bonk(self):
        if self.bonk_timer <= 0:
            self.bonk_timer = self.eff_bonk_cd()
            self.run_bonks += 1
            return True
        return False

    def draw(self, surf, t):
        r = self.radius
        moving = self.speed_now > 20
        bob = math.sin(self.move_anim) * 2.0 if moving else math.sin(t * 2) * 1.2
        px, py = self.x, self.y + bob
        flash = self.hit_flash > 0 and int(self.hit_flash * 40) % 2 == 0
        body = self.body_color(t)
        acc = self.skin["accent"]
        plain = bool(CFG.get("plain_skin"))
        surf.blit(shadow_sprite(r * 2 + 10), (int(px - r - 5), int(self.y + r * 0.55)))
        if not plain:
            draw_cosmetic_cape(surf, self, px, py, t)
        skin_draw_back(surf, self, px, py, t)
        if self.frenzy_stacks > 0:
            add_glow(surf, px, py, r * 3, (255, 200, 80), 0.25 + 0.08 * self.frenzy_stacks)
        ix, iy = int(px), int(py)
        pygame.draw.circle(surf, OUTLINE, (ix, iy), r + 2)
        if flash:
            pygame.draw.circle(surf, WHITE, (ix, iy), r)
        else:
            pygame.draw.circle(surf, scale_col(body, 0.6), (ix, iy), r)
            pygame.draw.circle(surf, body, (int(px - r * 0.10), int(py - r * 0.14)), int(r * 0.86))
            pygame.draw.circle(surf, lighten(body, 0.5), (int(px - r * 0.36), int(py - r * 0.42)), max(2, int(r * 0.22)))
            pygame.draw.circle(surf, acc, (ix, iy), r, 2)
        ax, ay = self.aim_dir
        for s in (-1, 1):
            ex = px + ax * r * 0.42 + (-ay) * s * r * 0.34
            ey = py + ay * r * 0.42 + ax * s * r * 0.34
            if self.skin["id"] == "shadow" and not plain:
                add_glow(surf, ex, ey, 10, acc, 0.85)
                pygame.draw.circle(surf, (235, 200, 255), (int(ex), int(ey)), 3)
            else:
                pygame.draw.circle(surf, (250, 250, 255), (int(ex), int(ey)), 4)
                pygame.draw.circle(surf, (20, 24, 40), (int(ex + ax * 1.6), int(ey + ay * 1.6)), 2)
        if plain:
            # SADE GÖRÜNÜM: süslü silah yerine nişan yönünü gösteren kısa bir namlu.
            bx0, by0 = px + ax * r * 0.7, py + ay * r * 0.7
            bx1, by1 = px + ax * (r + 11), py + ay * (r + 11)
            pygame.draw.line(surf, OUTLINE, (bx0, by0), (bx1, by1), 7)
            pygame.draw.line(surf, scale_col(body, 0.55), (bx0, by0), (bx1, by1), 5)
        else:
            draw_cosmetic_eyewear(surf, self, px, py, t)
            draw_weapon(surf, self, px, py, t)
            skin_draw_front(surf, self, px, py, t)
            draw_cosmetic_hat(surf, self, px, py, t)

        if self.shield_charges > 0:
            add_glow(surf, px, py, r * 2.4, (120, 170, 255), 0.3)
            pygame.draw.circle(surf, (160, 200, 255), (ix, iy), r + 8, 2)
        if self.invuln > 0 and self.dash_time <= 0:
            pygame.draw.circle(surf, (255, 255, 255), (ix, iy), r + 5, 1)
        if self.bonk_timer > 0:
            frac = 1 - clamp(self.bonk_timer / self.eff_bonk_cd(), 0, 1)
            rect = pygame.Rect(0, 0, r * 2 + 14, r * 2 + 14)
            rect.center = (ix, iy)
            if frac > 0.02:
                pygame.draw.arc(surf, ORANGE, rect, -math.pi / 2, -math.pi / 2 + math.tau * frac, 3)

        # ---- PATRON DURUM ETKİLERİ (yanık / zehir / yavaşlatma) ----
        # Oyuncu neden can kaybettiğini gözünün ucuyla görebilsin diye
        # etkiler doğrudan karakterin üstünde canlandırılır.
        if self.burn_t > 0:
            add_glow(surf, px, py, r * 2.3, (255, 130, 50), 0.28 + 0.10 * math.sin(t * 9))
            for i in range(4):
                ph = (t * 1.9 + i * 0.27) % 1.0
                fxp = px + math.sin(t * 5 + i * 2.3) * r * 0.8
                fyp = py - r * 0.4 - ph * r * 2.1
                blit_disc(surf, fxp, fyp, max(1.2, 4.2 * (1 - ph)),
                          (255, 190 - int(70 * ph), 80), int(215 * (1 - ph)))
        if self.poison_t > 0:
            pygame.draw.circle(surf, (130, 230, 100), (ix, iy), r + 7, 1)
            for i in range(3):
                ph = (t * 1.3 + i * 0.37) % 1.0
                bxp = px + math.sin(t * 2.6 + i * 2.1) * r * 0.7
                byp = py - r * 0.3 - ph * r * 1.7
                pygame.draw.circle(surf, (160, 245, 130), (int(bxp), int(byp)),
                                   max(1, int(3.4 * (1 - ph))))
        if self.slow_t > 0:
            pygame.draw.circle(surf, (140, 200, 255), (ix, iy), r + 10, 1)
            for i in range(6):
                a = t * 0.8 + i * math.tau / 6
                blit_disc(surf, px + math.cos(a) * (r + 12), py + math.sin(a) * (r + 12) * 0.7,
                          2.4, (170, 220, 255), 170)


# =====================================================================
# MERMİLER
# =====================================================================

class EnemyProjectile:
    def __init__(self, x, y, vx, vy, dmg, color=(235, 210, 70), r=6, life=4.0,
                 target=None, turn=0.0, accel=0.0, owner=None):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.dmg = dmg
        self.color = color
        self.r = r
        self.life = life
        self.alive = True
        # Yönelmeli mermiler: patronların "lanet mermisi" / "spor oku" gibi
        # saldırıları oyuncuyu bir süre takip eder. turn = saniyedeki dönüş
        # hızı (radyan); 0 ise mermi düz gider.
        self.target = target
        self.turn = turn
        self.accel = accel
        # Mermiyi atan (patron): isabet edince can çalabilmesi için.
        self.owner = owner

    def update(self, dt):
        if self.target is not None and self.turn > 0 and getattr(self.target, "alive", False):
            sp = math.hypot(self.vx, self.vy)
            if sp > 1:
                cur = math.atan2(self.vy, self.vx)
                want = math.atan2(self.target.y - self.y, self.target.x - self.x)
                diff = (want - cur + math.pi) % math.tau - math.pi
                cur += clamp(diff, -self.turn * dt, self.turn * dt)
                sp += self.accel * dt
                self.vx, self.vy = math.cos(cur) * sp, math.sin(cur) * sp
            # yönelme sonsuza kadar sürmez, yoksa kaçmak imkânsız olur
            self.turn = max(0.0, self.turn - dt * 1.45)
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        if (self.life <= 0 or self.x < ARENA_RECT.left - 30 or self.x > ARENA_RECT.right + 30
                or self.y < ARENA_RECT.top - 30 or self.y > ARENA_RECT.bottom + 30):
            self.alive = False

    def draw(self, surf, t):
        x, y = int(self.x), int(self.y)
        add_glow(surf, x, y, self.r * 3.2, self.color, 0.75)
        pygame.draw.circle(surf, OUTLINE, (x, y), self.r + 2)
        pygame.draw.circle(surf, self.color, (x, y), self.r)
        pygame.draw.circle(surf, lighten(self.color, 0.7), (x - 1, y - 1), max(1, self.r // 2))


STYLE_IV = {"bolt": .03, "feather": .035, "toxic": .03, "star": .04, "lightning": .035,
            "blackfire": .03, "fireball": .025, "gold": .03, "prism": .03,
            # premium skin mermileri
            "web": .035, "ash": .03, "rock": .04, "bullet": .02,
            # patron sandığı silahları
            "w_axe": .03, "w_arrow": .035}


class PlayerProjectile:
    def __init__(self, x, y, vx, vy, dmg, hits_left, crit_chance, crit_mult, homing=0,
                 style="bolt", color=(150, 210, 255), accent=WHITE):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.dmg = dmg
        self.hits_left = hits_left
        self.crit_chance = crit_chance
        self.crit_mult = crit_mult
        self.homing = homing
        self.style = style
        self.color = color
        self.accent = accent
        self.r = 6
        self.life = 1.15
        self.alive = True
        self.hit_set = set()
        self.spin = random.uniform(0, math.tau)
        self.trail_acc = 0.0

    def steer_toward(self, tx, ty, dt):
        if self.homing <= 0:
            return
        speed = math.hypot(self.vx, self.vy)
        if speed < 1e-4:
            return
        dx, dy = norm_dir(self.x, self.y, tx, ty)
        cur_x, cur_y = self.vx / speed, self.vy / speed
        turn = min(1.0, (3.0 + self.homing * 2.0) * dt)
        nx = lerp(cur_x, dx, turn)
        ny = lerp(cur_y, dy, turn)
        nl = math.hypot(nx, ny)
        if nl > 1e-4:
            self.vx = nx / nl * speed
            self.vy = ny / nl * speed

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        if (self.life <= 0 or self.x < ARENA_RECT.left - 30 or self.x > ARENA_RECT.right + 30
                or self.y < ARENA_RECT.top - 30 or self.y > ARENA_RECT.bottom + 30):
            self.alive = False

    def emit(self, fx, dt):
        iv = STYLE_IV.get(self.style, .03)
        self.trail_acc += dt
        n = int(self.trail_acc / iv)
        if n <= 0:
            return
        self.trail_acc -= n * iv
        n = min(n, 2)
        rv = random.uniform
        st, x, y = self.style, self.x, self.y
        for _ in range(n):
            if st == "bolt":
                fx.spark(x, y, self.color, 0, 0, .22, 2.4)
            elif st == "feather":
                fx.spark(x, y, random.choice(((235, 85, 95), (255, 170, 140))), rv(-15, 15), rv(-15, 15),
                         .5, 2.6, add=False, gravity=40)
            elif st == "toxic":
                fx.spark(x, y, (120, 225, 95), rv(-20, 20), rv(-20, 20), .5, 2.4, gravity=140)
            elif st == "star":
                fx.spark(x, y, random.choice((self.color, self.accent)), rv(-30, 30), rv(-30, 30), .4, 2.0)
            elif st == "lightning":
                fx.spark(x + rv(-5, 5), y + rv(-5, 5), self.color, rv(-40, 40), rv(-40, 40), .16, 2.0)
            elif st == "blackfire":
                fx.spark(x, y, (34, 22, 52), rv(-20, 20), rv(-30, 10), .55, 5, add=False, drag=3, grow=3)
                fx.spark(x, y, (150, 70, 230), rv(-30, 30), rv(-30, 30), .3, 2.4)
            elif st == "fireball":
                fx.spark(x, y, random.choice(((255, 140, 40), (255, 200, 80))), rv(-20, 20), rv(-50, -10), .4, 3.2)
            elif st == "gold":
                fx.spark(x, y, self.accent if random.random() < .5 else self.color, rv(-25, 25), rv(-25, 25), .4, 2.2)
            elif st == "prism":
                fx.spark(x, y, hue_col(random.random()), rv(-25, 25), rv(-25, 25), .4, 2.4)
            elif st == "web":
                fx.spark(x, y, (238, 242, 250), rv(-14, 14), rv(-14, 14), .45, 2.0, add=False)
            elif st == "ash":
                fx.spark(x, y, random.choice(((196, 192, 186), (120, 40, 42))),
                         rv(-22, 22), rv(-30, 6), .55, 3.0, add=False, drag=2.4, grow=2)
            elif st == "rock":
                fx.spark(x, y, random.choice(((120, 170, 90), (86, 120, 66))),
                         rv(-30, 30), rv(-20, 30), .5, 3.2, add=False, gravity=180)
            elif st == "bullet":
                fx.spark(x, y, (255, 214, 120), rv(-10, 10), rv(-10, 10), .18, 1.8)
            elif st == "w_axe":
                fx.spark(x, y, self.color, rv(-18, 18), rv(-18, 18), .3, 2.6)
            elif st == "w_arrow":
                fx.spark(x, y, self.color, rv(-8, 8), rv(-8, 8), .25, 1.8)

    def draw(self, surf, t):
        x, y = int(self.x), int(self.y)
        sp = math.hypot(self.vx, self.vy) or 1.0
        dx, dy = self.vx / sp, self.vy / sp
        ang = math.atan2(dy, dx)
        st, c, a = self.style, self.color, self.accent
        if st == "bolt":
            add_glow(surf, x, y, 16, c, .8)
            pygame.draw.line(surf, c, (x - dx * 12, y - dy * 12), (x + dx * 4, y + dy * 4), 5)
            pygame.draw.line(surf, WHITE, (x - dx * 8, y - dy * 8), (x + dx * 4, y + dy * 4), 2)
        elif st == "feather":
            add_glow(surf, x, y, 12, c, .4)
            pts = rot_pts([(11, 0), (-2, -3.4), (-12, 0), (-2, 3.4)], ang, x, y)
            pygame.draw.polygon(surf, c, pts)
            pygame.draw.line(surf, (255, 235, 225), pts[2], pts[0], 1)
        elif st == "toxic":
            rr = 6 + math.sin(t * 20 + self.spin) * 1.3
            add_glow(surf, x, y, 20, c, .7)
            pygame.draw.circle(surf, (60, 140, 50), (x, y), int(rr + 1.5))
            pygame.draw.circle(surf, c, (x, y), int(rr))
            pygame.draw.circle(surf, a, (x - 2, y - 2), 2)
        elif st == "star":
            add_glow(surf, x, y, 16, c, .7)
            pts = []
            for i in range(8):
                ai = t * 6 + self.spin + i * math.pi / 4
                rad = 9 if i % 2 == 0 else 3.4
                pts.append((x + math.cos(ai) * rad, y + math.sin(ai) * rad))
            pygame.draw.polygon(surf, a, pts)
            pygame.draw.polygon(surf, c, pts, 1)
        elif st == "lightning":
            add_glow(surf, x, y, 18, c, .8)
            rnd = random.Random(int(t * 30) + int(self.spin * 100))
            pts = [(int(px), int(py)) for px, py in zigzag(x - dx * 26, y - dy * 26, x, y, 5, 4, rnd)]
            pygame.draw.lines(surf, c, False, pts, 3)
            pygame.draw.lines(surf, WHITE, False, pts, 1)
        elif st == "blackfire":
            add_glow(surf, x, y, 26, (120, 50, 200), .55)
            for i in range(3):
                fa = ang + math.pi + (i - 1) * 0.5
                ln = 17 + math.sin(t * 25 + i * 2 + self.spin) * 5
                tip = (x + math.cos(fa) * ln, y + math.sin(fa) * ln)
                nx, ny = -math.sin(fa), math.cos(fa)
                poly = [(x + nx * 5, y + ny * 5), tip, (x - nx * 5, y - ny * 5)]
                pygame.draw.polygon(surf, (28, 16, 44), poly)
                pygame.draw.polygon(surf, (140, 70, 220), poly, 1)
            pygame.draw.circle(surf, (12, 8, 20), (x, y), 7)
            pygame.draw.circle(surf, (175, 100, 255), (x, y), 7, 2)
            pygame.draw.circle(surf, (95, 45, 155), (x, y), 3)
        elif st == "fireball":
            add_glow(surf, x, y, 30, (255, 120, 30), .8)
            for i in range(3):
                fa = ang + math.pi + (i - 1) * 0.45
                ln = 15 + math.sin(t * 22 + i * 2) * 4
                tip = (x + math.cos(fa) * ln, y + math.sin(fa) * ln)
                nx, ny = -math.sin(fa), math.cos(fa)
                pygame.draw.polygon(surf, (255, 110, 30), [(x + nx * 5, y + ny * 5), tip, (x - nx * 5, y - ny * 5)])
            pygame.draw.circle(surf, (255, 110, 30), (x, y), 7)
            pygame.draw.circle(surf, (255, 205, 80), (x, y), 5)
            pygame.draw.circle(surf, (255, 250, 210), (x, y), 2)
        elif st == "gold":
            add_glow(surf, x, y, 18, c, .7)
            pygame.draw.circle(surf, (180, 130, 40), (x, y), 6)
            pygame.draw.circle(surf, c, (x, y), 5)
            pygame.draw.circle(surf, WHITE, (x - 1, y - 1), 2)
            sz = 4 + math.sin(t * 12 + self.spin) * 2
            pygame.draw.line(surf, a, (x - sz - 3, y), (x + sz + 3, y), 1)
            pygame.draw.line(surf, a, (x, y - sz - 3), (x, y + sz + 3), 1)
        elif st == "prism":
            hc = hue_col(t * 0.6 + self.spin)
            add_glow(surf, x, y, 18, hc, .8)
            pts = rot_pts([(10, 0), (0, -5), (-10, 0), (0, 5)], ang, x, y)
            pygame.draw.polygon(surf, hc, pts)
            pygame.draw.polygon(surf, WHITE, pts, 1)
        elif st == "web":
            # AĞ TOPU: dönen bir ağ yumağı + arkasında uzayan iplik
            add_glow(surf, x, y, 16, (225, 235, 255), .55)
            pygame.draw.line(surf, (215, 222, 238), (x - dx * 22, y - dy * 22), (x, y), 2)
            pygame.draw.circle(surf, (245, 248, 255), (x, y), 7)
            pygame.draw.circle(surf, (170, 180, 205), (x, y), 7, 1)
            sp2 = self.spin + t * 6
            for i in range(6):
                a2 = sp2 + i * math.tau / 6
                pygame.draw.line(surf, (150, 162, 190),
                                 (x, y), (x + math.cos(a2) * 7, y + math.sin(a2) * 7), 1)
            for rr in (3, 6):
                pygame.draw.circle(surf, (150, 162, 190), (x, y), rr, 1)
        elif st == "ash":
            # KÜL KESİĞİ: kızıl çekirdekli, külden bir hilal
            add_glow(surf, x, y, 18, (215, 60, 58), .7)
            pts = rot_pts([(11, 0), (1, -7), (-7, 0), (1, 7)], ang, x, y)
            pygame.draw.polygon(surf, (214, 210, 202), pts)
            pygame.draw.polygon(surf, (150, 36, 40), pts, 2)
            pygame.draw.circle(surf, (255, 120, 90), (x, y), 3)
        elif st == "rock":
            # KAYA PARÇASI: köşeli, ağır
            add_glow(surf, x, y, 16, c, .5)
            rnd = random.Random(int(self.spin * 1000))
            pts = []
            for i in range(6):
                a2 = ang + i * math.tau / 6 + self.spin
                rr = 7 + rnd.uniform(-1.6, 2.2)
                pts.append((x + math.cos(a2) * rr, y + math.sin(a2) * rr))
            pygame.draw.polygon(surf, scale_col(c, 0.8), pts)
            pygame.draw.polygon(surf, OUTLINE, pts, 2)
            pygame.draw.circle(surf, lighten(c, 0.35), (int(x - 2), int(y - 2)), 2)
        elif st == "bullet":
            # KURŞUN: kısa, hızlı, sarı izli
            add_glow(surf, x, y, 12, (255, 200, 110), .75)
            pygame.draw.line(surf, (255, 222, 150),
                             (x - dx * 14, y - dy * 14), (x + dx * 3, y + dy * 3), 3)
            pygame.draw.line(surf, (255, 255, 235),
                             (x - dx * 6, y - dy * 6), (x + dx * 3, y + dy * 3), 1)
        elif st == "w_axe":
            # BALTA: kendi ekseninde dönen, iki ağızlı savaş baltası
            spin = t * 16 + self.spin
            add_glow(surf, x, y, 20, c, .55)
            hx0, hy0 = math.cos(spin), math.sin(spin)
            pygame.draw.line(surf, (92, 62, 40),
                             (x - hx0 * 13, y - hy0 * 13), (x + hx0 * 13, y + hy0 * 13), 4)
            for sgn in (-1, 1):
                bx0, by0 = x + hx0 * 12 * sgn, y + hy0 * 12 * sgn
                nx0, ny0 = -hy0, hx0
                blade = [(bx0 + hx0 * 7 * sgn, by0 + hy0 * 7 * sgn),
                         (bx0 + nx0 * 9, by0 + ny0 * 9),
                         (bx0 - hx0 * 5 * sgn, by0 - hy0 * 5 * sgn),
                         (bx0 - nx0 * 9, by0 - ny0 * 9)]
                pygame.draw.polygon(surf, OUTLINE, blade)
                pygame.draw.polygon(surf, (222, 228, 240), blade, 0)
                pygame.draw.polygon(surf, scale_col(c, 0.8), blade, 1)
        elif st == "w_arrow":
            # OK: uzun gövde, tüylü arka, sivri uç
            add_glow(surf, x, y, 14, c, .5)
            pygame.draw.line(surf, (150, 112, 70),
                             (x - dx * 17, y - dy * 17), (x + dx * 9, y + dy * 9), 3)
            tip = rot_pts([(15, 0), (5, -5), (5, 5)], ang, x, y)
            pygame.draw.polygon(surf, OUTLINE, tip)
            pygame.draw.polygon(surf, (236, 244, 252), tip)
            nx0, ny0 = -dy, dx
            for k in (-1, 1):
                pygame.draw.line(surf, c, (x - dx * 17, y - dy * 17),
                                 (x - dx * 10 + nx0 * 5 * k, y - dy * 10 + ny0 * 5 * k), 2)
        else:
            pygame.draw.circle(surf, c, (x, y), self.r)
        if self.homing:
            pygame.draw.circle(surf, (255, 225, 170), (x, y), 10, 1)


# =====================================================================
# EŞYALAR (altın / tecrübe / can)
# =====================================================================

class Pickup:
    __slots__ = ("x", "y", "kind", "value", "vx", "vy", "bob", "collected", "spawn_t", "dead")

    def __init__(self, x, y, kind, value):
        self.x, self.y = x, y
        self.kind = kind  # "coin" | "xp" | "heart"
        self.value = value
        self.vx, self.vy = random.uniform(-50, 50), random.uniform(-50, 50)
        self.bob = random.uniform(0, math.tau)
        self.collected = False
        self.dead = False
        self.spawn_t = 0.0

    def update(self, dt, player):
        self.spawn_t += dt
        k = 1 - min(1, dt * 3)
        self.vx *= k
        self.vy *= k
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.kind == "heart" and self.spawn_t > 14:
            self.dead = True
            return
        if self.spawn_t > 0.15 and player.alive:
            d = dist(self.x, self.y, player.x, player.y)
            pr = player.eff_pickup() * (0.7 if self.kind == "heart" else 1.0)
            if d < pr:
                pull = clamp(1 - d / pr, 0, 1) ** 0.6
                spd = lerp(70, 620, pull)
                dx, dy = norm_dir(self.x, self.y, player.x, player.y)
                self.x += dx * spd * dt
                self.y += dy * spd * dt
            if d < 16:
                self.collected = True

    def draw(self, surf, t):
        bob = math.sin(t * 4 + self.bob) * 2.5
        x, y = int(self.x), int(self.y + bob)
        if self.kind == "coin":
            add_glow(surf, x, y, 12, GOLD, .5)
            pygame.draw.circle(surf, (150, 105, 30), (x, y), 6)
            pygame.draw.circle(surf, GOLD, (x, y), 5)
            pygame.draw.circle(surf, (255, 240, 170), (x - 1, y - 1), 2)
        elif self.kind == "xp":
            add_glow(surf, x, y, 12, PURPLE, .55)
            pts = [(x, y - 6), (x + 4, y), (x, y + 6), (x - 4, y)]
            pygame.draw.polygon(surf, PURPLE, pts)
            pygame.draw.polygon(surf, (225, 200, 255), pts, 1)
        else:
            add_glow(surf, x, y, 18, RED, .6 + 0.2 * math.sin(t * 6))
            draw_icon(surf, x, y, "heart", (255, 110, 130), 13)


# =====================================================================
# SAHADAKİ MARKET PORTALI
# =====================================================================

# =====================================================================
# CEHENNEM  (2. HARİTA)
# ---------------------------------------------------------------------
# 25. dalganın patronu devrildiğinde arenanın ortasında MOR bir portal
# açılır ve oyuncu ölene ya da portala girene kadar orada kalır.
#
# NEDEN VAR: 25. dalgadan sonra oyuncu artık tam donanımlıdır ve oyun
# "bitmiş" hissi verir. Bu yüzden 25'ten sonra arena kasten acımasızlaşır
# (can / zırh / hasar / hız üstel artar, YENİ PATRON GELMEZ) ve oyuncuyu
# portala girmeye zorlar: 32. dalgaya kadar hayatta kalmak imkânsıza yakındır.
#
# CEHENNEM'de her şey aynı kalır (seviye, kitaplar, market eşyaları, altın,
# skor); tek fark yaratıkların BAŞKA olması. Cehennem yaratıkları arenanın
# 25. dalgası kadar CANLI ve VURUCUDUR ama HIZLARI 1. dalga temposuna döner —
# yani dövüş yeniden yönetilebilir hâle gelir ve dalga düzeni baştan başlar.
# Oyuncunun ilerlemeye devam edebilmesi için markete yalnızca cehennemde
# açılan yeni bir kademe (CEHENNEM) eklenir.
# =====================================================================

HELL_PORTAL_WAVE = 25          # portalı açan patron dalgası
HELL_PORTAL_COLOR = (178, 86, 255)
HELL_PORTAL_COLOR2 = (232, 170, 255)

# 25. dalgadan sonra arena her dalgada üstel olarak sertleşir.
ARENA_PRESSURE_FROM = HELL_PORTAL_WAVE
ARENA_PRESSURE_HP = 1.35       # dalga başına can çarpanı
ARENA_PRESSURE_DMG = 1.30      # dalga başına hasar çarpanı
ARENA_PRESSURE_SPD = 0.06      # dalga başına hız artışı
ARENA_PRESSURE_ARMOR = 0.06    # dalga başına zırh (üst sınır %60)


def arena_pressure(wave):
    """25. dalgadan sonraki 'seni portala sokan' baskı çarpanları.

    (can, hasar, hız, zırh) — 25 ve öncesinde hepsi nötrdür.
    """
    over = max(0, int(wave) - ARENA_PRESSURE_FROM)
    if over <= 0:
        return 1.0, 1.0, 1.0, 0.0
    return (ARENA_PRESSURE_HP ** over,
            ARENA_PRESSURE_DMG ** over,
            1.0 + ARENA_PRESSURE_SPD * over,
            clamp(ARENA_PRESSURE_ARMOR * over, 0.0, 0.60))


# ---------------------------------------------------------------------
# CEHENNEM YARATIKLARI
# ---------------------------------------------------------------------
# Her cehennem yaratığının kendi adı, rengi ve GÖRÜNÜMÜ (shape) var; davranışı
# ise kanıtlanmış arena yapay zekâlarından birini (base) kullanır.
#   base  : davranış (red / blue / yellow / tank / sprinter / brute / elite)
#   shape : çizim biçimi — kasten base'den farklı seçildi ki cehennem
#           yaratıkları arenadakilere benzemesin
# ---------------------------------------------------------------------

HELL_ENEMIES = {
    "h_imp":     dict(name="İmp",            base="blue",     shape="yellow",
                      color=(255, 140, 60),  hp=1.00, dmg=1.00, radius=1.05),
    "h_hound":   dict(name="Tazı",           base="sprinter", shape="red",
                      color=(226, 58, 40),   hp=1.05, dmg=1.05, radius=1.05),
    "h_reaver":  dict(name="Yağmacı",        base="red",      shape="brute",
                      color=(178, 40, 52),   hp=1.10, dmg=1.05, radius=1.00),
    "h_seer":    dict(name="Kör Kâhin",      base="yellow",   shape="blue",
                      color=(246, 196, 70),  hp=1.00, dmg=1.10, radius=1.05),
    "h_golem":   dict(name="Lav Golemi",     base="tank",     shape="tank",
                      color=(120, 56, 44),   hp=1.20, dmg=1.10, radius=1.05),
    "h_butcher": dict(name="Kasap",          base="brute",    shape="sprinter",
                      color=(150, 30, 60),   hp=1.15, dmg=1.15, radius=1.05),
    "h_warden":  dict(name="Cehennem Muhafızı", base="elite", shape="elite",
                      color=(255, 96, 40),   hp=1.15, dmg=1.15, radius=1.05),
}

HELL_ENEMY_COLORS = {k: v["color"] for k, v in HELL_ENEMIES.items()}

# Cehennem dalgalarında hangi yaratıktan ne sıklıkla geleceği.
def hell_pick_kind(wave):
    w = max(1, int(wave))
    weights = {
        "h_imp": 10,
        "h_hound": 4 + min(w, 9),
        "h_reaver": 6 + min(w, 8),
        "h_seer": max(0, min(w, 7)),
        "h_golem": max(0, min(w - 1, 8)),
        "h_butcher": max(0, min(w - 2, 8)),
    }
    return random.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]


# Cehennem yaratıkları arenanın 25. dalgası kadar CANLI ve VURUCU başlar.
HELL_BASE_WAVE = 25


def hell_hp_mult(wave):
    """Cehennem dalgasının can çarpanı: 25. dalga seviyesinden başlar ve
    arenadaki gibi dalga başına artar."""
    base = 1.0 + (HELL_BASE_WAVE - 1) * 0.22
    return base * (1.0 + (max(1, wave) - 1) * 0.20)


def hell_dmg_wave(wave):
    """Hasar hesabında kullanılan 'sanal' dalga: cehennem 1 = arena 25.

    Artış arenadakinden daha YUMUŞAK (dalga başına 0.75 arena dalgası):
    cehennem yaratıkları zaten yavaş olduğu için hasar eğrisi de üstel
    biçimde patlamasın, dövüş yönetilebilir kalsın.
    """
    return HELL_BASE_WAVE + (max(1, wave) - 1) * 0.75


def hell_speed_wave(wave):
    """Hız hesabında kullanılan 'sanal' dalga.

    Kullanıcının istediği ana fikir: cehennemde yaratıklar aynı derecede
    güçlü ama HIZLARI 1. dalga temposuna döner; sonra yine kademeli artar.
    """
    return max(1, wave)


# ---------------------------------------------------------------------
# CEHENNEM PATRONLARI
# ---------------------------------------------------------------------
# Davranışları arena patronlarıyla aynı (dengesi oturmuş), kimlikleri başka:
# yeni ad, yeni renk ve cehennem görselliği.
HELL_BOSS_NAMES = {
    "warlord":  "CEHENNEM LORDU",
    "witch":    "KÜL CADISI",
    "colossus": "LAV KOLOSU",
    "reaper":   "RUH TOPLAYICI",
    "hive":     "AZAP ANASI",
    "dragon":   "KOR EJDERHA",
}
HELL_BOSS_COLORS = {
    "warlord":  (236, 74, 44),
    "witch":    (196, 60, 190),
    "colossus": (168, 78, 46),
    "reaper":   (226, 120, 40),
    "hive":     (246, 158, 48),
    "dragon":   (228, 58, 30),
}
# CEHENNEM'in ilk patronu EJDERHA: girer girmez oyuncuyu karşılayan,
# alev püskürten uçan dev. Sonra sırayla diğerleri gelir.
HELL_BOSS_ORDER = ["dragon", "warlord", "colossus", "reaper", "hive", "witch"]
HELL_BOSS_FIRST_WAVE = 5       # cehennemde patron: 5, 10, 15 ...
HELL_BOSS_STEP = 5
# Cehennem patronu, arenanın son patronundan (25. dalga = 4. patron) daha
# güçsüz olmasın diye güç dizini buradan başlar.
HELL_BOSS_INDEX_BASE = 4


def hell_boss_index(wave):
    return HELL_BOSS_INDEX_BASE + max(0, (int(wave) - HELL_BOSS_FIRST_WAVE) // HELL_BOSS_STEP)


class HellPortal:
    """25. dalga patronundan sonra açılan MOR portal.

    Oyuncu ölene ya da içine girene kadar haritada durur; yaklaşınca
    "E" tuşuyla girilir.
    """

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.r = 46
        self.t = 0.0
        self.motes = []
        for _ in range(26):
            self.motes.append([random.uniform(0, math.tau), random.uniform(0.35, 1.25),
                               random.uniform(0.5, 1.6), random.uniform(1.5, 3.4)])

    def update(self, dt):
        self.t += dt
        for mo in self.motes:
            mo[0] += dt * mo[2] * 1.4
            mo[1] -= dt * 0.22
            if mo[1] < 0.18:
                mo[1] = 1.25
                mo[0] = random.uniform(0, math.tau)

    def in_range(self, player):
        return dist(self.x, self.y, player.x, player.y) < self.r + 70

    def draw(self, surf, t):
        pulse = 0.5 + 0.5 * math.sin(self.t * 2.4)
        # dış hale
        add_glow(surf, self.x, self.y, self.r * 4.2, HELL_PORTAL_COLOR, 0.30 + 0.16 * pulse)
        add_glow(surf, self.x, self.y, self.r * 2.0, HELL_PORTAL_COLOR2, 0.26 + 0.12 * pulse)
        # girdap: içe doğru daralan dönen halkalar
        for i in range(7):
            k = i / 6.0
            rr = self.r * (1.06 - k * 0.82)
            ang = self.t * (1.1 + i * 0.35) * (1 if i % 2 == 0 else -1)
            rect = pygame.Rect(0, 0, int(rr * 2), int(rr * 2))
            rect.center = (int(self.x), int(self.y))
            col = mix_col(HELL_PORTAL_COLOR, HELL_PORTAL_COLOR2, k)
            pygame.draw.arc(surf, col, rect, ang, ang + math.pi * 1.35, max(2, int(4 - k * 2)))
        # merkez
        pygame.draw.circle(surf, (26, 10, 42), (int(self.x), int(self.y)), int(self.r * 0.34))
        pygame.draw.circle(surf, HELL_PORTAL_COLOR2, (int(self.x), int(self.y)),
                           int(self.r * 0.34), 2)
        # içe çekilen parçacıklar
        for (a, d, spd, sz) in self.motes:
            px = self.x + math.cos(a) * self.r * d
            py = self.y + math.sin(a) * self.r * d * 0.92
            blit_disc(surf, px, py, sz, HELL_PORTAL_COLOR2, int(120 + 120 * (1.25 - d)))
        # taban halkası
        rect = pygame.Rect(0, 0, int(self.r * 2.2), int(self.r * 2.2))
        rect.center = (int(self.x), int(self.y))
        pygame.draw.ellipse(surf, (*HELL_PORTAL_COLOR, 255), rect, 3)

        # etiket
        draw_text(surf, "CEHENNEM KAPISI", (self.x, self.y - self.r - 42), 16,
                  HELL_PORTAL_COLOR2, bold=True, center=True)
        lab = pygame.Rect(0, 0, 150, 26)
        lab.center = (int(self.x), int(self.y + self.r + 26))
        ls = pygame.Surface(lab.size, pygame.SRCALPHA)
        pygame.draw.rect(ls, (30, 12, 48, 235), ls.get_rect(), border_radius=13)
        pygame.draw.rect(ls, (*HELL_PORTAL_COLOR, 255), ls.get_rect(), width=2, border_radius=13)
        surf.blit(ls, lab.topleft)
        draw_text(surf, "GİRMEK İÇİN  E", lab.center, 13, (245, 225, 255), bold=True,
                  center=True, shadow=False)


class MarketPortal:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.r = 32
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def draw(self, surf, player):
        pulse = 0.5 + 0.5 * math.sin(self.t * 3)
        add_glow(surf, self.x, self.y, self.r * 2.6, GOLD, 0.45 + 0.2 * pulse)
        rect = pygame.Rect(0, 0, self.r * 2, self.r * 2)
        rect.center = (int(self.x), int(self.y))
        pygame.draw.circle(surf, (24, 20, 12), (int(self.x), int(self.y)), self.r)
        pygame.draw.arc(surf, GOLD, rect, self.t * 1.5, self.t * 1.5 + math.pi * 1.4, 3)
        pygame.draw.arc(surf, GOLD_DIM, rect, self.t * -1.2, self.t * -1.2 + math.pi * 1.1, 2)
        draw_icon(surf, self.x, self.y, "coin", GOLD, 16)
        if dist(self.x, self.y, player.x, player.y) < self.r + 110:
            draw_text(surf, "MARKET: ÜSTÜNE YÜRÜ (veya B)", (self.x, self.y - self.r - 18),
                      14, GOLD, bold=True, center=True)


# =====================================================================
# TUZAK / BÖLGE HASARI (yerde kırmızı uyarı, sonra patlar)
# =====================================================================

class Hazard:
    def __init__(self, x, y, r, delay, dmg, owner=None):
        self.x, self.y = x, y
        self.r = r
        self.delay = delay
        self.dmg = dmg
        # Tuzağı kuran (patron): isabet edince can çalabilmesi için.
        self.owner = owner
        self.t = 0.0
        self.exploded = False
        self.linger = 0.0
        self.alive = True

    def update(self, dt, run):
        if not self.exploded:
            self.t += dt
            if self.t >= self.delay:
                self.exploded = True
                self.linger = 0.3
                p = run.player
                if p.alive and dist(self.x, self.y, p.x, p.y) < self.r + p.radius - 2:
                    if self.owner is not None and hasattr(self.owner, "hit_player"):
                        # Patron tuzağı: hasarla birlikte patronun imza etkisini
                        # de taşır (yakar / zehirler / yavaşlatır).
                        self.owner.hit_player(p, self.dmg, run.fx, self.x, self.y)
                    else:
                        p.take_damage(self.dmg, run.fx, self.x, self.y, "Tuzak")
                run.fx.shockwave(self.x, self.y, self.r * 1.15, (255, 90, 70), 0.4, 6)
                run.fx.burst(self.x, self.y, (255, 140, 70), n=18, speed=200, life=0.5, r=3.5)
                run.fx.shake(6, 0.2)
                sfx("explosion", 0.55, 0.05)
        else:
            self.linger -= dt
            if self.linger <= 0:
                self.alive = False

    def draw(self, surf, t):
        x, y = int(self.x), int(self.y)
        if not self.exploded:
            frac = clamp(self.t / self.delay, 0, 1)
            blit_disc(surf, x, y, self.r * frac, (255, 60, 50), 70)
            pulse = 0.6 + 0.4 * math.sin(t * 16)
            pygame.draw.circle(surf, scale_col((255, 70, 60), pulse), (x, y), int(self.r), 2)
            pygame.draw.line(surf, (255, 120, 100), (x - 7, y - 7), (x + 7, y + 7), 2)
            pygame.draw.line(surf, (255, 120, 100), (x - 7, y + 7), (x + 7, y - 7), 2)
        else:
            add_glow(surf, x, y, self.r * 1.4, (255, 120, 60), clamp(self.linger / 0.3, 0, 1))



# =====================================================================
# PATRON SANDIĞI ve OTOMATİK SİLAHLAR
# ---------------------------------------------------------------------
# Bir patron devrildiğinde yere bir SANDIK düşer. Sandığa dokunan oyuncu
# içinden bir SİLAH alır. Silahlar yetenekler gibi çalışır: oyuncu hiçbir
# tuşa basmaz, silah kendi kendine en uygun düşmana ateş eder. Kalan
# bekleme süresi ekranın altındaki yetenek çubuğunda saniye saniye görünür.
#
# HASAR DENGESİ: silah hasarı sabit bir sayı DEĞİLDİR; oyuncunun o anki
# vuruş hasarının (eff_dmg) katı olarak hesaplanır. Yani market, kitap ve
# seviye bonuslarıyla oyuncu güçlendikçe silahlar da birlikte güçlenir ve
# 30. dalgada da işe yaramaya devam eder.
#
# AYNI SİLAH tekrar çıkarsa seviyesi artar: hasarı yükselir, bekleme
# süresi kısalır.
#
# YENİ SİLAH EKLEMEK: BOSS_WEAPONS'a bir satır ekle ve
# RunState._fire_weapon() içine davranışını yaz.
# =====================================================================

BOSS_WEAPONS = [
    dict(key="axe", name="BALTA", icon="sword", color=(235, 140, 74),
         cd=2.4, dmg=2.40, style="w_axe",
         desc="Dönerek uçan balta — önüne gelen herkesi biçer."),
    dict(key="pistol", name="TABANCA", icon="target", color=(240, 216, 142),
         cd=0.75, dmg=0.80, style="bullet",
         desc="En yakın düşmana seri atış yapar."),
    dict(key="katana", name="KATANA", icon="sword", color=(176, 232, 255),
         cd=1.9, dmg=1.95, style=None,
         desc="Çevrene yarım ay kesik atar, yakındaki herkesi biçer."),
    dict(key="bow", name="OK", icon="bolt", color=(150, 232, 170),
         cd=1.5, dmg=1.70, style="w_arrow",
         desc="Uzun menzilli, birçok düşmanı delen ok."),
    dict(key="hammer", name="ÇEKİÇ", icon="fist", color=(206, 196, 238),
         cd=3.6, dmg=3.40, style=None,
         desc="Gökten inen çekiç — düştüğü yeri sarsar."),
]
WEAPON_BY_KEY = {w["key"]: w for w in BOSS_WEAPONS}
# Yetenek çubuğunda silahların hep aynı sırada görünmesi için.
BOSS_WEAPONS_ORDER = [w["key"] for w in BOSS_WEAPONS]

WEAPON_MAX_LEVEL = 8
WEAPON_CD_PER_LEVEL = 0.90      # her seviyede bekleme süresi bu oranla çarpılır
WEAPON_DMG_PER_LEVEL = 0.38     # her seviyede hasara eklenen oran
WEAPON_RANGE = 620.0            # silahların hedef arama menzili


def weapon_cooldown(w, level):
    """Silahın iki atışı arasındaki süre (seviye arttıkça kısalır)."""
    return max(0.22, w["cd"] * (WEAPON_CD_PER_LEVEL ** max(0, level - 1)))


def weapon_damage(player, w, level):
    """Silahın vuruş hasarı — OYUNCUNUN o anki hasarına göre ölçeklenir.

    Böylece silah, alındığı dalgada güçlü olup 10 dalga sonra çöpe dönmez;
    oyuncunun güç eğrisini takip eder.
    """
    return player.eff_dmg() * w["dmg"] * (1.0 + WEAPON_DMG_PER_LEVEL * max(0, level - 1))


class BossChest:
    """Patron ölünce düşen sandık. Oyuncu dokununca açılır ve silah verir."""

    def __init__(self, x, y, boss_name=""):
        self.x, self.y = x, y
        self.r = 26
        self.t = 0.0
        self.open_t = 0.0          # açılma canlandırması
        self.opened = False
        self.taken = False         # ödül verildi mi (RunState işler)
        self.alive = True
        self.boss_name = boss_name
        self.bob = random.uniform(0, math.tau)

    def in_range(self, p):
        return dist(self.x, self.y, p.x, p.y) < self.r + p.radius + 10

    def update(self, dt, player):
        self.t += dt
        if self.opened:
            self.open_t += dt
            if self.open_t > 1.1:
                self.alive = False
            return
        if player.alive and self.in_range(player):
            self.opened = True
            self.open_t = 0.0

    def draw(self, surf, t):
        bob = math.sin(t * 2.4 + self.bob) * 3.0
        x, y = self.x, self.y + bob
        k = clamp(self.open_t / 0.4, 0.0, 1.0) if self.opened else 0.0
        surf.blit(shadow_sprite(int(self.r * 2)), (int(x - self.r), int(self.y + self.r * 0.5)))
        add_glow(surf, x, y, self.r * (2.0 + 1.6 * k), GOLD, 0.35 + 0.18 * math.sin(t * 3) + 0.4 * k)

        w, h = self.r * 1.7, self.r * 1.05
        # --- gövde ---
        base = pygame.Rect(int(x - w), int(y - h * 0.25), int(w * 2), int(h * 1.35))
        pygame.draw.rect(surf, OUTLINE, base.inflate(6, 6), border_radius=6)
        pygame.draw.rect(surf, (126, 78, 42), base, border_radius=6)
        pygame.draw.rect(surf, (86, 52, 28), base, width=2, border_radius=6)
        for i in (-1, 1):
            pygame.draw.line(surf, (92, 58, 32), (x + i * w * 0.45, base.top + 3),
                             (x + i * w * 0.45, base.bottom - 3), 3)
        # --- kapak (açılınca arkaya devrilir) ---
        lid_lift = h * 1.5 * k
        lid = pygame.Rect(int(x - w), int(y - h * 0.95 - lid_lift), int(w * 2), int(h * 0.85))
        pygame.draw.rect(surf, OUTLINE, lid.inflate(6, 6), border_radius=7)
        pygame.draw.rect(surf, (150, 96, 52), lid, border_radius=7)
        pygame.draw.rect(surf, GOLD, lid, width=2, border_radius=7)
        # --- altın kilit ---
        pygame.draw.rect(surf, GOLD, (int(x - 7), int(y - h * 0.28 - lid_lift * 0.4), 14, 16),
                         border_radius=3)
        pygame.draw.circle(surf, (120, 80, 20), (int(x), int(y - h * 0.20 - lid_lift * 0.4)), 3)
        # --- altın bantlar ---
        pygame.draw.line(surf, GOLD, (base.left + 2, base.top + 2), (base.right - 2, base.top + 2), 3)

        if self.opened:
            # açılırken içinden ışık sütunu ve kıvılcımlar fışkırır
            beam = pygame.Surface((int(w * 2), int(h * 6)), pygame.SRCALPHA)
            pygame.draw.polygon(beam, (255, 225, 140, int(150 * (1 - k * 0.4))),
                                [(w * 0.65, beam.get_height()), (w * 1.35, beam.get_height()),
                                 (w * 2.0, 0), (0, 0)])
            surf.blit(beam, (int(x - w), int(y - h * 6)))
            for i in range(8):
                a = t * 3 + i * math.tau / 8
                rr = self.r * (0.5 + 1.8 * k)
                blit_disc(surf, x + math.cos(a) * rr, y + math.sin(a) * rr * 0.6,
                          3.2 * (1 - k * 0.6), (255, 230, 150), int(220 * (1 - k)))
        else:
            # kapalıyken: yukarı süzülen altın zerreler + "YAKLAŞ" ipucu
            for i in range(4):
                ph = (t * 0.8 + i * 0.25 + self.bob) % 1.0
                sx_ = x + math.sin(t * 2 + i * 2.1) * self.r * 0.8
                sy_ = y - self.r * 0.4 - ph * self.r * 2.2
                blit_disc(surf, sx_, sy_, max(1.0, 3.0 * (1 - ph)), (255, 225, 140),
                          int(210 * (1 - ph)))
            draw_text(surf, "PATRON SANDIĞI", (x, y - self.r * 2.4), 13, GOLD,
                      bold=True, center=True)
            draw_text(surf, "yaklaş ve aç", (x, y - self.r * 1.75), 10, TEXT_DIM,
                      center=True, shadow=False)


# =====================================================================
# DÜŞMAN TÜRLERİ
# =====================================================================

ENEMY_COLORS = {
    "red":    (222, 70, 78),
    "blue":   (78, 150, 232),
    "yellow": (235, 210, 70),
    "tank":   (150, 100, 210),
    "sprinter": (235, 130, 235),
    "brute":  (200, 90, 60),
    "elite":  (232, 186, 90),
}

ENEMY_DEFS = {
    "red":      {"hp": 30,  "speed": 100, "dmg": 10, "radius": 14, "coin": 5,  "xp": 4,  "score": 12,  "contact_dps": 17},
    "blue":     {"hp": 14,  "speed": 194, "dmg": 6,  "radius": 10, "coin": 1,  "xp": 2,  "score": 6,   "contact_dps": 10},
    "yellow":   {"hp": 23,  "speed": 78,  "dmg": 9,  "radius": 13, "coin": 3,  "xp": 6,  "score": 16,  "contact_dps": 12},
    "tank":     {"hp": 118, "speed": 58,  "dmg": 21, "radius": 22, "coin": 8,  "xp": 10, "score": 28,  "contact_dps": 27},
    "sprinter": {"hp": 18,  "speed": 270, "dmg": 8,  "radius": 11, "coin": 3,  "xp": 4,  "score": 14,  "contact_dps": 14},
    "brute":    {"hp": 70,  "speed": 84,  "dmg": 16, "radius": 18, "coin": 6,  "xp": 8,  "score": 22,  "contact_dps": 23},
    "elite":    {"hp": 340, "speed": 70,  "dmg": 29, "radius": 28, "coin": 32, "xp": 36, "score": 150, "contact_dps": 36},
}

# Zorluk seviyeleri artık düşman istatistiklerini (can/hasar) DEĞİL, yalnızca
# oyunun TEMPOSUNU değiştirir: aynı skorda aynı dalgaya ulaşılır, aynı xp/altın/
# elmas kazanılır — tek fark düşmanların ne kadar hızlı geldiği ve dalgaların
# ne kadar hızlı ilerlediğidir. Normal daha sakin/yavaş, Kabus deneyimli
# oyuncular için oyunu gerçek anlamda HIZLANDIRIR.
DIFF_MULT = {"normal": 1.0, "hard": 1.0, "nightmare": 1.0}
DIFF_PACE = {"normal": 0.72, "hard": 1.0, "nightmare": 1.55}

# Düşmanın GÖRÜNEN şekliyle ÇARPIŞMA kutusu birebir örtüşsün diye, her tür için
# çizilen görselin gerçek kapladığı alana göre bir çarpışma yarıçapı çarpanı.
# (Örn. üçgen/baklava gibi şekiller, onları çevreleyen daireden daha küçüktür.)
ENEMY_HITBOX_FACTOR = {
    "red": 1.0, "blue": 0.72, "yellow": 0.8, "tank": 0.95,
    "sprinter": 0.8, "brute": 0.92, "elite": 1.0,
}


def wave_speed_mult(wave):
    """Yeni başlayanlar ilk dalgalarda telaşlanmasın diye düşman hızını kısar,
    7. dalgadan sonra ise tecrübeli oyuncular için kademeli olarak hızlandırır."""
    if wave <= 7:
        t = clamp((wave - 1) / 6.0, 0.0, 1.0)
        return lerp(0.66, 0.94, t)
    t = clamp((wave - 7) / 18.0, 0.0, 1.0)
    return lerp(0.94, 1.55, t)


def late_wave_dmg_mult(wave):
    """Düşman HASARININ dalgaya göre artışı. Eskiden hasar, canın (wave_mult)
    yalnızca küçük bir kesri kadar artıyordu; bu yüzden oyuncu eşyalarını
    doldurunca düşmanlar sonsuza kadar 'kum torbası'na dönüşüyor, oyuncu asla
    ciddi hasar almıyordu (ör. 25. dalgada bile ölmeden hayatta kalınabiliyordu).
    Artık ilk dalgalarda (öğrenme eğrisi) yumuşak, 12. dalgadan sonra ÜSSEL
    (exponansiyel) olarak artan bir hasar çarpanı var: eşyalar maksimuma
    ulaşsa bile geç dalgalarda (25-35 civarı) zırh tavanını (%60) delip
    oyuncuyu eritecek kadar büyüyor. Böylece sonsuza kadar hayatta kalmak
    artık mümkün değil — bir yerden sonra oyuncu kaçınılmaz olarak ölür."""
    if wave <= 12:
        return 1.0 + (wave - 1) * 0.055
    base = 1.0 + 11 * 0.055
    extra = ((wave - 12) ** 1.6) * 0.05
    return base + extra


class Enemy:
    def __init__(self, kind, x, y, wave_mult, diff_mult=1.0, wave=1,
                 variant=None, biome="arena"):
        """Bir yaratık üretir.

        kind    : davranış türü (red / blue / yellow / tank / sprinter / brute / elite)
        variant : CEHENNEM yaratığı anahtarı (HELL_ENEMIES). Verilirse davranış
                  variant'ın base'inden, GÖRÜNÜM ise variant'tan gelir; böylece
                  cehennem yaratıkları arenadakilere hiç benzemez.
        biome   : "arena" | "hell" — hız/hasar eğrileri buna göre seçilir.
        """
        var = HELL_ENEMIES.get(variant) if variant else None
        if var:
            kind = var["base"]
        d = ENEMY_DEFS[kind]
        self.kind = kind                 # davranış
        self.variant = variant
        self.hellish = bool(var)
        self.shape = var["shape"] if var else kind      # çizim biçimi
        self.disp_name = var["name"] if var else kind   # ölüm nedeni / arayüz
        self.x, self.y = x, y

        # --- cehennemde hız 1. dalga temposuna döner, can/hasar 25. dalga seviyesinde ---
        spd_wave = hell_speed_wave(wave) if biome == "hell" else wave
        dmg_wave = hell_dmg_wave(wave) if biome == "hell" else wave
        # --- 25. dalgadan sonra arena kasten acımasızlaşır (portala zorlar) ---
        pr_hp, pr_dmg, pr_spd, pr_armor = (1.0, 1.0, 1.0, 0.0) if biome == "hell" else arena_pressure(wave)

        hp_var = var["hp"] if var else 1.0
        dmg_var = var["dmg"] if var else 1.0

        self.max_hp = d["hp"] * wave_mult * hp_var * pr_hp
        self.hp = self.max_hp
        self.speed = d["speed"] * wave_speed_mult(spd_wave) * pr_spd
        dmg_mult = late_wave_dmg_mult(dmg_wave)
        self.dmg = d["dmg"] * dmg_mult * diff_mult * dmg_var * pr_dmg
        # Zırh: gelen hasarın sabit bir yüzdesini keser. 25. dalgadan sonra
        # arena yaratıkları zırhlanır; cehennemde zırh yoktur (canları zaten çok).
        self.armor = pr_armor
        self.radius = d["radius"] * (var["radius"] if var else 1.0)
        self.coin = d["coin"]
        self.xp = d["xp"]
        self.score = d["score"]
        self.contact_dps = d["contact_dps"] * dmg_mult * diff_mult * dmg_var * pr_dmg
        # Kırmızı toplar (temel düşman) ne kadar güçlüyse görsel olarak o kadar
        # doygun/canlı kırmızı olsun — oyuncu tehlikeyi bir bakışta anlasın.
        if self.shape == "red":
            base_dmg = ENEMY_DEFS["red"]["dmg"]
            self.red_intensity = clamp((self.dmg / base_dmg - 1.0) / 3.2, 0.0, 1.0)
        else:
            self.red_intensity = 0.0
        # Çarpışma (hitbox) yarıçapı — görünen şekle göre ayarlanır, gözle görünenden
        # daha büyük bir alanda "hayalet" hasar/isabet olmasın.
        self.hit_r = self.radius * ENEMY_HITBOX_FACTOR.get(self.shape, 1.0)
        self.color = var["color"] if var else ENEMY_COLORS[kind]
        self.alive = True
        self.hit_flash = 0.0
        self.spawn_t = 0.0
        self.shoot_cd = random.uniform(0.6, 1.4)
        self.dash_cd = random.uniform(1.2, 2.4)
        self.dash_t = 0.0
        self.dash_dx = self.dash_dy = 0.0
        self.knock_x = 0.0
        self.knock_y = 0.0
        self.wobble = random.uniform(0, math.tau)
        self.burn_timer = 0.0
        self.burn_dps = 0.0
        self.burn_tick_acc = 0.0
        self.slow_timer = 0.0
        self.slow_mult = 1.0
        self.touch_cd = 0.0
        # ZEHİR: yanıktan farkı süresinin OLMAMASI — bir kez bulaştı mı düşman
        # ölene kadar devam eder ve her yeni vuruşta üst üste birikir.
        self.poison_dps = 0.0
        self.poison_tick_acc = 0.0
        # Yaratık görünümü için: baktığı yön (yumuşatılmış) ve yürüyüş fazı.
        # Gözler ve bacaklar bu ikisine göre çizilir.
        self.face_x, self.face_y = 0.0, 1.0
        self.walk = random.uniform(0, math.tau)
        # KÜKREME KİTABI: korkan düşman bir süre oyuncudan kaçar.
        self.fear_timer = 0.0

    def apply_poison(self, dps):
        self.poison_dps += dps

    def apply_burn(self, dps, duration):
        self.burn_timer = max(self.burn_timer, duration)
        self.burn_dps = max(self.burn_dps, dps)

    def apply_slow(self, mult, duration):
        if self.slow_timer <= 0 or mult < self.slow_mult:
            self.slow_mult = mult
        self.slow_timer = max(self.slow_timer, duration)

    def update(self, dt, player, fx, projectiles, kill_cb=None):
        if not self.alive:
            return
        self.spawn_t += dt
        self.wobble += dt * 6
        if self.touch_cd > 0:
            self.touch_cd -= dt
        scale_in = ease_out_cubic(self.spawn_t / 0.3)

        speed_mult = 1.0
        if self.slow_timer > 0:
            self.slow_timer -= dt
            speed_mult = self.slow_mult
            if self.slow_timer <= 0:
                self.slow_mult = 1.0

        if self.burn_timer > 0:
            self.burn_timer -= dt
            self.burn_tick_acc += dt
            while self.burn_tick_acc >= 0.5 and self.alive:
                self.burn_tick_acc -= 0.5
                died = self.take_damage(self.burn_dps * 0.5, False, fx)
                if died and kill_cb:
                    kill_cb(self)
            if self.burn_timer <= 0:
                self.burn_dps = 0.0
            if not self.alive:
                return

        # ZEHİR: süresi yok, düşman ölene kadar her yarım saniyede bir vurur.
        if self.poison_dps > 0:
            self.poison_tick_acc += dt
            while self.poison_tick_acc >= 0.5 and self.alive:
                self.poison_tick_acc -= 0.5
                died = self.take_damage(self.poison_dps * 0.5, False, fx)
                if died and kill_cb:
                    kill_cb(self)
            if not self.alive:
                return

        eff_speed = self.speed * speed_mult

        # Baktığı yönü oyuncuya doğru yumuşakça çevir + yürüyüş fazını ilerlet.
        if player.alive:
            tfx, tfy = norm_dir(self.x, self.y, player.x, player.y)
            k = min(1.0, dt * 7.0)
            self.face_x += (tfx - self.face_x) * k
            self.face_y += (tfy - self.face_y) * k
            fl = math.hypot(self.face_x, self.face_y)
            if fl > 1e-5:
                self.face_x /= fl
                self.face_y /= fl
        self.walk += dt * (2.0 + eff_speed * 0.030)

        if abs(self.knock_x) > 0.5 or abs(self.knock_y) > 0.5:
            self.x += self.knock_x * dt
            self.y += self.knock_y * dt
            self.knock_x *= max(0.0, 1 - dt * 8)
            self.knock_y *= max(0.0, 1 - dt * 8)
        elif self.dash_t > 0:
            self.dash_t -= dt
            self.x += self.dash_dx * eff_speed * 2.6 * dt
            self.y += self.dash_dy * eff_speed * 2.6 * dt
        else:
            dx, dy = norm_dir(self.x, self.y, player.x, player.y)
            if self.fear_timer > 0:
                # korkmuş düşman ters yöne kaçar
                self.fear_timer -= dt
                dx, dy = -dx, -dy
                self.x += dx * eff_speed * 1.15 * dt * scale_in
                self.y += dy * eff_speed * 1.15 * dt * scale_in
                self.x = clamp(self.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
                self.y = clamp(self.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
                return
            if self.kind == "yellow":
                d = dist(self.x, self.y, player.x, player.y)
                if d < 230:
                    dx, dy = -dx, -dy
                elif d < 280:
                    dx, dy = 0, 0
                self.shoot_cd -= dt
                if self.shoot_cd <= 0 and self.spawn_t > 0.4:
                    self.shoot_cd = random.uniform(1.5, 2.3)
                    pdx, pdy = norm_dir(self.x, self.y, player.x, player.y)
                    projectiles.append(EnemyProjectile(self.x, self.y, pdx * 230, pdy * 230, self.dmg * 0.85))
                    sfx("shoot_c", 0.3, 0.08)
            elif self.kind == "sprinter":
                self.dash_cd -= dt
                if self.dash_cd <= 0 and self.spawn_t > 0.3:
                    self.dash_cd = random.uniform(1.6, 2.6)
                    self.dash_t = 0.22
                    self.dash_dx, self.dash_dy = dx, dy
            # düz ve öngörülebilir bir hareket — gereksiz sallanma/titreme olmasın
            self.x += dx * eff_speed * dt * scale_in
            self.y += dy * eff_speed * dt * scale_in

        self.x = clamp(self.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
        self.y = clamp(self.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)

        if self.hit_flash > 0:
            self.hit_flash -= dt

        if player.alive:
            d = dist(self.x, self.y, player.x, player.y)
            if d < self.hit_r + player.radius - 2 and self.touch_cd <= 0:
                self.touch_cd = 0.12
                dealt = player.take_damage(self.contact_dps * 0.12 * 6, fx, self.x, self.y, self.disp_name)
                if dealt > 0 and player.thorns_level > 0:
                    reflect = dealt * 0.35 * player.thorns_level
                    died = self.take_damage(reflect, False, fx)
                    if died and kill_cb:
                        kill_cb(self)

    def take_damage(self, amount, crit, fx, kx=0.0, ky=0.0):
        # 25. dalgadan sonraki arena yaratıklarının zırhı gelen hasarı keser.
        if self.armor > 0:
            amount *= (1.0 - self.armor)
        self.hp -= amount
        self.hit_flash = 0.14
        self.knock_x += kx
        self.knock_y += ky
        col = (255, 230, 120) if crit else WHITE
        fx.popup(self.x, self.y - self.radius - 4, f"{int(amount)}" + ("!" if crit else ""),
                 col, 22 if crit else 15, life=0.5)
        if crit:
            sfx("crit", 0.7, 0.03)
        if self.hp <= 0 and self.alive:
            self.alive = False
            fx.burst(self.x, self.y, self.color, n=14, speed=170, life=0.5, r=3.5)
            sfx("kill", 0.5, 0.02)
            return True
        return False

    def _eyes(self, surf, x, y, r, fx_, fy_, n=2, spread=0.42, fwd=0.44,
              sz=0.20, eye_col=(255, 255, 255), pupil=(18, 16, 26), glow_col=None, t=0.0):
        """Yaratığın gözlerini baktığı yöne göre çizer.

        Göz, bir karakteri "şekil" olmaktan çıkarıp canlı gösteren tek şeydir;
        bu yüzden bütün düşman türleri bunu kullanır.
        """
        sx_, sy_ = -fy_, fx_
        blink = 1.0
        # ~4 saniyede bir kısa göz kırpma (her düşman farklı fazda)
        ph = (t * 0.9 + self.wobble) % 4.0
        if ph < 0.13:
            blink = max(0.12, abs(ph - 0.065) / 0.065)
        for i in range(n):
            off = 0.0 if n == 1 else (i - (n - 1) / 2.0) * spread * 2.0
            ex = x + fx_ * r * fwd + sx_ * r * off
            ey = y + fy_ * r * fwd + sy_ * r * off
            er = max(1.5, r * sz)
            if glow_col:
                add_glow(surf, ex, ey, er * 3.2, glow_col, .45)
            pygame.draw.circle(surf, OUTLINE, (int(ex), int(ey)), int(er + 1))
            pygame.draw.ellipse(surf, eye_col,
                                (int(ex - er), int(ey - er * blink), int(er * 2), max(1, int(er * 2 * blink))))
            if blink > 0.5:
                px_ = ex + fx_ * er * 0.34
                py_ = ey + fy_ * er * 0.34
                pygame.draw.circle(surf, pupil, (int(px_), int(py_)), max(1, int(er * 0.52)))

    def _legs(self, surf, x, y, r, fx_, fy_, col, pairs=2, length=0.55, width=3, spread=0.62):
        """Yürüyüşle birlikte ileri geri sallanan bacaklar."""
        sx_, sy_ = -fy_, fx_
        for i in range(pairs):
            for s in (-1, 1):
                ph = self.walk + i * 1.7 + (0 if s > 0 else math.pi)
                swing = math.sin(ph) * r * 0.30
                bx = x - fx_ * r * (0.10 + i * 0.34) + sx_ * r * spread * s
                by = y - fy_ * r * (0.10 + i * 0.34) + sy_ * r * spread * s
                tx = bx + sx_ * r * 0.34 * s + fx_ * swing
                ty = by + sy_ * r * 0.34 * s + fy_ * swing
                pygame.draw.line(surf, OUTLINE, (bx, by), (tx, ty), width + 2)
                pygame.draw.line(surf, col, (bx, by), (tx, ty), width)

    def draw(self, surf, t):
        scale = ease_out_cubic(self.spawn_t / 0.3) if self.spawn_t < 0.3 else 1.0
        flash = self.hit_flash > 0
        col = WHITE if flash else self.color
        r = self.radius * scale
        x, y = self.x, self.y
        fx_, fy_ = self.face_x, self.face_y
        sx_, sy_ = -fy_, fx_
        dark = scale_col(col, 0.58)
        lite = lighten(col, 0.34)
        # nefes alma: gövde hafifçe şişip iner
        breathe = 1.0 + math.sin(self.walk * 0.9) * 0.045
        surf.blit(shadow_sprite(int(r * 2 + 6)), (int(x - r - 3), int(y + r - 3)))

        if self.shape == "red":
            # ---- ETLİ SÜRÜNGEN: çenesi olan, tek gözlü, sıçrayarak yürüyen yaratık
            vivid = col if flash else mix_col(self.color, (255, 20, 15), self.red_intensity * 0.85)
            if self.red_intensity > 0.04:
                ga = 0.22 + 0.4 * self.red_intensity + 0.08 * math.sin(t * 5 + self.wobble)
                add_glow(surf, x, y, r * (1.5 + 0.6 * self.red_intensity), vivid, clamp(ga, 0, 0.8))
            hop = abs(math.sin(self.walk * 0.9)) * r * 0.10
            by_ = y - hop
            self._legs(surf, x, by_, r, fx_, fy_, scale_col(vivid, 0.55), pairs=2, width=3)
            pr = r * breathe
            pygame.draw.circle(surf, OUTLINE, (int(x), int(by_)), int(pr + 2))
            pygame.draw.circle(surf, vivid, (int(x), int(by_)), int(pr))
            # sırt dikenleri
            for k in (-1, 0, 1):
                bxp = x - fx_ * pr * 0.55 + sx_ * pr * 0.42 * k
                byp = by_ - fy_ * pr * 0.55 + sy_ * pr * 0.42 * k
                pygame.draw.polygon(surf, scale_col(vivid, 0.6),
                                    [(bxp - sx_ * 3, byp - sy_ * 3),
                                     (bxp - fx_ * pr * 0.34, byp - fy_ * pr * 0.34),
                                     (bxp + sx_ * 3, byp + sy_ * 3)])
            pygame.draw.circle(surf, lighten(vivid, .3),
                               (int(x - pr * .3), int(by_ - pr * .3)), max(2, int(pr * .35)))
            # ağız (yürürken açılıp kapanır)
            mo = 0.5 + 0.5 * math.sin(self.walk * 1.6)
            mx = x + fx_ * pr * 0.66
            my = by_ + fy_ * pr * 0.66
            pygame.draw.polygon(surf, (40, 12, 16),
                                [(mx - sx_ * pr * 0.30, my - sy_ * pr * 0.30),
                                 (mx + fx_ * pr * 0.20, my + fy_ * pr * 0.20),
                                 (mx + sx_ * pr * 0.30, my + sy_ * pr * 0.30),
                                 (mx - fx_ * pr * (0.04 + mo * 0.16), my - fy_ * pr * (0.04 + mo * 0.16))])
            self._eyes(surf, x, by_, pr, fx_, fy_, n=2, spread=0.30, fwd=0.30, sz=0.19, t=t)

        elif self.shape == "blue":
            # ---- YARASA/ÇEVİK: kanat çırpan, dar gövdeli hızlı yaratık
            flap = math.sin(self.walk * 2.6)
            for s in (-1, 1):
                wtip = (x + sx_ * r * (1.5 + flap * 0.30) * s - fx_ * r * 0.20,
                        y + sy_ * r * (1.5 + flap * 0.30) * s - fy_ * r * 0.20)
                wing = [(x + sx_ * r * 0.30 * s, y + sy_ * r * 0.30 * s),
                        wtip,
                        (x + sx_ * r * 0.62 * s - fx_ * r * 0.80,
                         y + sy_ * r * 0.62 * s - fy_ * r * 0.80)]
                pygame.draw.polygon(surf, OUTLINE, [(a + s, b + 1) for a, b in wing])
                pygame.draw.polygon(surf, dark if not flash else col, wing)
                pygame.draw.polygon(surf, col, wing, 1)
            body = [(x + fx_ * r * 1.05, y + fy_ * r * 1.05),
                    (x + sx_ * r * 0.52, y + sy_ * r * 0.52),
                    (x - fx_ * r * 0.86, y - fy_ * r * 0.86),
                    (x - sx_ * r * 0.52, y - sy_ * r * 0.52)]
            pygame.draw.polygon(surf, OUTLINE, [(a, b + 1) for a, b in body])
            pygame.draw.polygon(surf, col, body)
            pygame.draw.polygon(surf, lite, [(x + fx_ * r * 0.7, y + fy_ * r * 0.7),
                                             (x + sx_ * r * 0.22, y + sy_ * r * 0.22),
                                             (x - fx_ * r * 0.2, y - fy_ * r * 0.2)])
            self._eyes(surf, x, y, r, fx_, fy_, n=2, spread=0.26, fwd=0.46, sz=0.17,
                       eye_col=(255, 240, 190), t=t)

        elif self.shape == "yellow":
            # ---- BÜYÜCÜ GÖZ: çevresinde şarj olan kristaller dönen tek gözlü varlık
            charging = self.shoot_cd < 0.6
            spin = t * 1.6
            for i in range(3):
                a = spin + i * math.tau / 3
                orb = r * (1.25 + (0.18 if charging else 0.0))
                ox_, oy_ = x + math.cos(a) * orb, y + math.sin(a) * orb
                oc = (255, 240, 160) if charging else col
                pygame.draw.polygon(surf, OUTLINE,
                                    [(ox_, oy_ - 5), (ox_ + 4, oy_), (ox_, oy_ + 5), (ox_ - 4, oy_)])
                pygame.draw.polygon(surf, oc,
                                    [(ox_, oy_ - 4), (ox_ + 3, oy_), (ox_, oy_ + 4), (ox_ - 3, oy_)])
            if charging:
                add_glow(surf, x, y, r * 1.9, (255, 240, 160), 0.55)
            pr = r * breathe
            pts = [(x, y - pr), (x + pr, y), (x, y + pr), (x - pr, y)]
            pygame.draw.polygon(surf, OUTLINE, [(x, y - pr - 3), (x + pr + 3, y), (x, y + pr + 3), (x - pr - 3, y)])
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.polygon(surf, lite, [(x, y - pr * 0.55), (x + pr * 0.55, y), (x, y)])
            self._eyes(surf, x, y, pr, fx_, fy_, n=1, fwd=0.26, sz=0.34,
                       eye_col=(255, 252, 226), glow_col=(255, 230, 120) if charging else None, t=t)

        elif self.shape == "tank":
            # ---- ZIRHLI YÜRÜYÜŞÇÜ: plakalı, perçinli, vizörlü ağır yaratık
            self._legs(surf, x, y, r, fx_, fy_, (70, 60, 92), pairs=2, length=0.5, width=4, spread=0.66)
            rect = pygame.Rect(0, 0, int(r * 1.86 * breathe), int(r * 1.86 * breathe))
            rect.center = (int(x), int(y))
            pygame.draw.rect(surf, OUTLINE, rect.inflate(5, 5), border_radius=7)
            pygame.draw.rect(surf, col, rect, border_radius=7)
            # omuz plakaları
            for s in (-1, 1):
                pl = [(x + sx_ * r * 0.94 * s - fx_ * r * 0.40, y + sy_ * r * 0.94 * s - fy_ * r * 0.40),
                      (x + sx_ * r * 1.16 * s + fx_ * r * 0.10, y + sy_ * r * 1.16 * s + fy_ * r * 0.10),
                      (x + sx_ * r * 0.80 * s + fx_ * r * 0.46, y + sy_ * r * 0.80 * s + fy_ * r * 0.46)]
                pygame.draw.polygon(surf, OUTLINE, [(a + s, b + 1) for a, b in pl])
                pygame.draw.polygon(surf, dark, pl)
            pygame.draw.rect(surf, lite, rect.inflate(-r * 0.9, -r * 0.9), border_radius=4)
            # perçinler
            for cx_, cy_ in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                rx = x + sx_ * r * 0.62 * cx_ + fx_ * r * 0.62 * cy_
                ry = y + sy_ * r * 0.62 * cx_ + fy_ * r * 0.62 * cy_
                pygame.draw.circle(surf, dark, (int(rx), int(ry)), max(1, int(r * 0.10)))
            # vizör
            vx = x + fx_ * r * 0.72
            vy = y + fy_ * r * 0.72
            pygame.draw.line(surf, (22, 20, 30),
                             (vx - sx_ * r * 0.56, vy - sy_ * r * 0.56),
                             (vx + sx_ * r * 0.56, vy + sy_ * r * 0.56), max(3, int(r * 0.26)))
            self._eyes(surf, x, y, r, fx_, fy_, n=2, spread=0.30, fwd=0.72, sz=0.13,
                       eye_col=(255, 120, 120), glow_col=(255, 80, 80), t=t)

        elif self.shape == "sprinter":
            # ---- AV KÖPEĞİ: ileri atılan, kuyruklu, hız izi bırakan yaratık
            mv = math.atan2(fy_, fx_)
            if self.dash_t > 0:
                for k in range(3):
                    ta = 0.34 - k * 0.10
                    add_glow(surf, x - fx_ * (14 + k * 12), y - fy_ * (14 + k * 12), r * 1.5, col, ta)
            self._legs(surf, x, y, r, fx_, fy_, dark, pairs=2, width=2, spread=0.52)
            # kuyruk (gövdeyi bastırmayacak kadar kısa)
            tw = math.sin(self.walk * 2.2) * r * 0.38
            tail = [(x - fx_ * r * 0.72, y - fy_ * r * 0.72),
                    (x - fx_ * r * 1.10 + sx_ * tw * 0.5, y - fy_ * r * 1.10 + sy_ * tw * 0.5),
                    (x - fx_ * r * 1.42 + sx_ * tw, y - fy_ * r * 1.42 + sy_ * tw)]
            pygame.draw.lines(surf, OUTLINE, False, tail, 6)
            pygame.draw.lines(surf, col, False, tail, 3)
            # gövde: daha dolgun, kalçası geniş bir dört ayaklı silueti
            pts = rot_pts([(r * 1.34, 0), (r * 0.52, -r * 0.74), (-r * 0.46, -r * 0.86),
                           (-r * 0.92, 0), (-r * 0.46, r * 0.86), (r * 0.52, r * 0.74)], mv, x, y)
            pygame.draw.polygon(surf, OUTLINE, [(a + (a - x) * .10, b + (b - y) * .10) for a, b in pts])
            pygame.draw.polygon(surf, col, pts)
            # sırt çizgisi
            pygame.draw.line(surf, lite, (x - fx_ * r * 0.5, y - fy_ * r * 0.5),
                             (x + fx_ * r * 0.9, y + fy_ * r * 0.9), 2)
            # kulaklar
            for s in (-1, 1):
                exx = x + fx_ * r * 0.34 + sx_ * r * 0.56 * s
                eyy = y + fy_ * r * 0.34 + sy_ * r * 0.56 * s
                ear = [(exx, eyy),
                       (exx - fx_ * r * 0.48 + sx_ * r * 0.30 * s,
                        eyy - fy_ * r * 0.48 + sy_ * r * 0.30 * s),
                       (exx + sx_ * r * 0.34 * s, eyy + sy_ * r * 0.34 * s)]
                pygame.draw.polygon(surf, OUTLINE, [(a + s, b + 1) for a, b in ear])
                pygame.draw.polygon(surf, dark, ear)
            self._eyes(surf, x, y, r, fx_, fy_, n=2, spread=0.24, fwd=0.62, sz=0.15,
                       eye_col=(255, 235, 255), t=t)

        elif self.shape == "brute":
            # ---- DEV: geniş omuzlu, iki yumruklu, ağır adımlı yaratık
            step = math.sin(self.walk * 1.1) * r * 0.16
            pts = []
            for i in range(6):
                ang = i * math.tau / 6 + math.pi / 6
                rr = r * breathe * (1.0 + (0.10 if i % 2 == 0 else 0.0))
                pts.append((x + math.cos(ang) * rr, y + math.sin(ang) * rr))
            outer = [(x + (a - x) * 1.14, y + (b - y) * 1.14) for a, b in pts]
            # yumruklar (sırayla öne savrulur)
            for s in (-1, 1):
                sw = step * s
                hx = x + fx_ * (r * 0.72 + sw) + sx_ * r * 1.02 * s
                hy = y + fy_ * (r * 0.72 + sw) + sy_ * r * 1.02 * s
                pygame.draw.circle(surf, OUTLINE, (int(hx), int(hy)), int(r * 0.46))
                pygame.draw.circle(surf, dark, (int(hx), int(hy)), int(r * 0.40))
                pygame.draw.circle(surf, lighten(dark, .3),
                                   (int(hx - fx_ * r * 0.1), int(hy - fy_ * r * 0.1)), max(1, int(r * 0.14)))
            pygame.draw.polygon(surf, OUTLINE, outer)
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.polygon(surf, lite,
                                [(x - fx_ * r * 0.34 - sx_ * r * 0.34, y - fy_ * r * 0.34 - sy_ * r * 0.34),
                                 (x + fx_ * r * 0.10 - sx_ * r * 0.44, y + fy_ * r * 0.10 - sy_ * r * 0.44),
                                 (x + fx_ * r * 0.20, y + fy_ * r * 0.20)])
            self._eyes(surf, x, y, r, fx_, fy_, n=2, spread=0.28, fwd=0.50, sz=0.17,
                       eye_col=(255, 225, 190), t=t)

        elif self.shape == "elite":
            # ---- ELİT: taçlı, yörüngesinde kılıçlar dönen altın şampiyon
            add_glow(surf, x, y, r * 2.0, self.color, .55 + .10 * math.sin(t * 3))
            spin = t * 2
            for i in range(6):
                ang = spin + i * math.tau / 6
                ox_ = x + math.cos(ang) * r * 1.42
                oy_ = y + math.sin(ang) * r * 1.42
                bl = rot_pts([(6, 0), (0, -3), (-6, 0), (0, 3)], ang, ox_, oy_)
                pygame.draw.polygon(surf, OUTLINE, bl)
                pygame.draw.polygon(surf, GOLD, bl)
            self._legs(surf, x, y, r, fx_, fy_, (120, 96, 40), pairs=2, width=4, spread=0.60)
            pr = r * breathe
            pygame.draw.circle(surf, OUTLINE, (int(x), int(y)), int(pr + 3))
            pygame.draw.circle(surf, col, (int(x), int(y)), int(pr))
            pygame.draw.circle(surf, GOLD, (int(x), int(y)), int(pr), 3)
            pygame.draw.circle(surf, lighten(col, .3),
                               (int(x - pr * .32), int(y - pr * .32)), max(2, int(pr * .28)))
            # taç
            for k in (-1, 0, 1):
                bxp = x - fx_ * pr * 0.72 + sx_ * pr * 0.40 * k
                byp = y - fy_ * pr * 0.72 + sy_ * pr * 0.40 * k
                tip = (bxp - fx_ * pr * 0.42, byp - fy_ * pr * 0.42)
                pygame.draw.polygon(surf, OUTLINE,
                                    [(bxp - sx_ * 4, byp - sy_ * 4), tip, (bxp + sx_ * 4, byp + sy_ * 4)])
                pygame.draw.polygon(surf, GOLD,
                                    [(bxp - sx_ * 3, byp - sy_ * 3), tip, (bxp + sx_ * 3, byp + sy_ * 3)])
            self._eyes(surf, x, y, pr, fx_, fy_, n=2, spread=0.28, fwd=0.44, sz=0.18,
                       eye_col=(255, 250, 220), glow_col=(255, 220, 120), t=t)

        else:
            # Güvenlik ağı: tanımsız yeni bir tür eklenirse yine de canlı görünsün.
            pr = r * breathe
            pygame.draw.circle(surf, OUTLINE, (int(x), int(y)), int(pr + 2))
            pygame.draw.circle(surf, col, (int(x), int(y)), int(pr))
            self._eyes(surf, x, y, pr, fx_, fy_, n=2, spread=0.30, fwd=0.40, sz=0.18, t=t)

        # ---- CEHENNEM GÖRSELLİĞİ ----
        # Cehennem yaratıkları aynı iskeleti kullansa bile bambaşka okunsun:
        # boynuzlar, gövdede akkor çatlaklar ve yukarı süzülen kor zerreleri.
        if self.hellish:
            ember = (255, 150, 60)
            add_glow(surf, x, y, r * 2.1, ember, 0.16 + 0.06 * math.sin(t * 4 + self.wobble))
            # boynuzlar
            for sgn in (-1, 1):
                bx0 = x - fx_ * r * 0.55 + sx_ * r * 0.55 * sgn
                by0 = y - fy_ * r * 0.55 + sy_ * r * 0.55 * sgn
                tipx = bx0 - fx_ * r * 0.70 + sx_ * r * 0.42 * sgn
                tipy = by0 - fy_ * r * 0.70 + sy_ * r * 0.42 * sgn
                pygame.draw.polygon(surf, OUTLINE,
                                    [(bx0 - sx_ * 4, by0 - sy_ * 4), (tipx, tipy),
                                     (bx0 + sx_ * 4, by0 + sy_ * 4)])
                pygame.draw.polygon(surf, (236, 226, 214),
                                    [(bx0 - sx_ * 3, by0 - sy_ * 3), (tipx, tipy),
                                     (bx0 + sx_ * 3, by0 + sy_ * 3)])
            # akkor çatlaklar
            for i in range(3):
                a = self.wobble + i * 2.1
                cx0 = x + math.cos(a) * r * 0.30
                cy0 = y + math.sin(a) * r * 0.30
                cx1 = x + math.cos(a + 0.9) * r * 0.80
                cy1 = y + math.sin(a + 0.9) * r * 0.80
                pygame.draw.line(surf, ember, (cx0, cy0), (cx1, cy1), 2)
            # kor zerreleri
            for i in range(3):
                ph = (t * 0.9 + i * 0.33 + self.wobble * 0.2) % 1.0
                ex = x + math.sin(t * 2.0 + i * 2.4 + self.wobble) * r * 0.75
                ey = y - r * 0.5 - ph * r * 1.6
                blit_disc(surf, ex, ey, max(1.0, 2.6 * (1.0 - ph)), (255, 190, 90),
                          int(200 * (1.0 - ph)))

        # ---- durum halkaları ----
        if self.slow_timer > 0:
            pygame.draw.circle(surf, CYAN, (int(x), int(y)), int(r + 4), 1)
        if self.burn_timer > 0:
            pygame.draw.circle(surf, ORANGE, (int(x), int(y)), int(r + 6), 1)
        if self.poison_dps > 0:
            # zehir: yukarı süzülen kabarcıklar + yeşil halka
            pygame.draw.circle(surf, (120, 225, 90), (int(x), int(y)), int(r + 8), 1)
            for i in range(3):
                bph = (t * 1.3 + i * 0.37 + self.wobble) % 1.0
                bxp = x + math.sin(t * 2.4 + i * 2.1) * r * 0.6
                byp = y - r * 0.4 - bph * r * 1.5
                pygame.draw.circle(surf, (150, 240, 120), (int(bxp), int(byp)),
                                   max(1, int(3 * (1.0 - bph))))

        if self.hp < self.max_hp:
            w = r * 2
            bx, by = x - w / 2, y - r - 12
            pygame.draw.rect(surf, (30, 30, 40), (bx, by, w, 4), border_radius=2)
            frac = clamp(self.hp / self.max_hp, 0, 1)
            hc = GREEN if frac > 0.5 else (ORANGE if frac > 0.25 else RED)
            pygame.draw.rect(surf, hc, (bx, by, w * frac, 4), border_radius=2)

# =====================================================================
# PATRON (BOSS)
# =====================================================================

BOSS_DEFS = {
    "warlord":  {"name": "SAVAŞ LORDU",   "hp": 4900, "speed": 80,  "dmg": 33, "radius": 46, "color": (210, 80, 70)},
    "witch":    {"name": "GÖLGE CADISI",  "hp": 4150, "speed": 92,  "dmg": 29, "radius": 42, "color": (140, 90, 210)},
    "colossus": {"name": "KOLOS",         "hp": 6600, "speed": 62,  "dmg": 41, "radius": 54, "color": (110, 130, 160)},
    "reaper":   {"name": "ORAK",          "hp": 3650, "speed": 112, "dmg": 31, "radius": 40, "color": (70, 200, 170)},
    "hive":     {"name": "KOVAN ANA",     "hp": 5750, "speed": 66,  "dmg": 27, "radius": 50, "color": (225, 170, 60)},
    # EJDERHA: yalnızca CEHENNEM'de çıkan, ateş püskürten uçan patron.
    "dragon":   {"name": "EJDERHA",       "hp": 7400, "speed": 96,  "dmg": 36, "radius": 58, "color": (206, 66, 40)},
}
# Patron sırası: aynı patronla üst üste karşılaşılmasın diye 5 tür dönüşümlü gelir.
# (EJDERHA arenada çıkmaz — cehenneme özeldir.)
BOSS_ORDER = ["warlord", "witch", "colossus", "reaper", "hive"]

# ---------------------------------------------------------------------
# PATRON ÖZELLİKLERİ
# ---------------------------------------------------------------------
# Eskiden bütün patronlar aynı şeyi yapıyordu: mermi at, alan hasarı bırak.
# Artık her patronun KENDİNE ÖZGÜ bir imza mekaniği var ve bu mekanik hem
# saldırılarına hem de görünümüne yansıyor.
#
#   burn    : vuruşları seni YAKAR (süreli ateş hasarı)
#   venom   : vuruşları seni ZEHİRLER (daha uzun süren, daha yumuşak sızı)
#   chill   : vuruşları seni YAVAŞLATIR (kaçmak zorlaşır)
#   vanish  : düzenli aralıklarla GÖRÜNMEZ olur, saldırınca ortaya çıkar
#   blink   : oyuncunun dibine IŞINLANIR ve anında vurur
#   inferno : ejderha — hem yakar hem uçar hem alev koridoru bırakır
#
# YENİ PATRON EKLEMEK: BOSS_DEFS'e bir satır, buraya bir özellik ve
# Boss.draw() içine bir çizim dalı eklemek yeterli.
# ---------------------------------------------------------------------
BOSS_TRAITS = {
    "warlord":  {"kind": "burn",    "label": "ATEŞLİ ÇELİK",  "color": (255, 146, 62)},
    "witch":    {"kind": "vanish",  "label": "GÖLGE PERDESİ", "color": (196, 126, 246)},
    "colossus": {"kind": "chill",   "label": "SARSINTI",      "color": (150, 200, 240)},
    "reaper":   {"kind": "blink",   "label": "RUH SIÇRAMASI", "color": (120, 240, 210)},
    "hive":     {"kind": "venom",   "label": "ZEHİRLİ SPOR",  "color": (186, 232, 92)},
    "dragon":   {"kind": "inferno", "label": "EJDER ATEŞİ",   "color": (255, 120, 44)},
}


def boss_trait(kind, hellish=False):
    """Patronun imza özelliği. Cehennem patronları ayrıca ATEŞ de taşır."""
    tr = dict(BOSS_TRAITS.get(kind, BOSS_TRAITS["warlord"]))
    tr["hellfire"] = bool(hellish) or tr["kind"] in ("burn", "inferno")
    return tr

# Patronlar artık 8. dalgada bir kez değil, 10. dalgadan itibaren HER 5 DALGADA
# bir gelir: 10, 15, 20, 25, 30 ...
BOSS_FIRST_WAVE = 10
BOSS_WAVE_STEP = 5

# Patron dengelemesi: patronlar zorlu kalsın ama haksız hissettirmesin.
#   HP     -> %15 daha az can (dövüş "ölümsüz" hissi vermesin)
#   DMG    -> %15 daha az hasar (hem temas hem de tüm saldırılar için)
#   EXTRA  -> her saldırının hazırlık (telegraph) süresine eklenen ek bekleme.
#             Patron eskiden nişan alır almaz ateşliyordu ve oyuncu kaçamadan
#             kilitleniyordu; bu ek süre kaçmak için gerçek bir pencere açar.
# GÖLGE CADISI'nın "lanet çemberi" tuzakları. Tuzak merkezleri arasındaki
# uzaklık, oyuncunun (yarıçap 16) iki tuzağın arasından geçebilmesi için
# 2*(46+16) = 124 pikselden büyük olmalıdır; aşağıdaki değer pay bırakır.
BOSS_RING_HAZARD_R = 46
BOSS_RING_GAP_MIN = 126

# --- PATRON DÖVÜŞÜ SÜRESİ ---------------------------------------------
# Patron canı artık sabit değil: oyuncunun gücüne göre ölçekleniyor.
# Amaç, patron dövüşünün oyuncu ne kadar güçlenirse güçlensin yaklaşık
# BOSS_FIGHT_TARGET saniye sürmesi. Eskiden eşyalarını dolduran bir oyuncu
# patronu birkaç saniyede eritiyordu.
#   UPTIME  : oyuncu dövüş boyunca hasarının ancak bu kadarını basabiliyor
#             (kaçma, konumlanma, bekleme süreleri yüzünden)
#   CAP     : taban canın en fazla kaç katına çıkılabileceği (emniyet tavanı)
BOSS_FIGHT_TARGET = 90.0
BOSS_FIGHT_UPTIME = 0.50
BOSS_HP_SCALE_MAX = 60.0
BOSS_HP_SCALE_MIN = 0.30
# Patronun can çalmasının ÜST SINIRI.
# Sınır OYUNCUNUN saniyelik hasarına göre konur: patron, oyuncunun saniyede
# vurduğu hasarın en fazla bu oranı kadarını geri kazanabilir. Böylece can
# çalma dövüşü yalnızca bir miktar UZATIR, asla kazanılamaz hâle getirmez.
# (Eskiden tavan patronun azami canının yüzdesiydi; azami can oyuncunun
#  gücüyle ölçeklendiği için can çalma da birlikte büyüyor ve patron kendini
#  oyuncudan daha hızlı iyileştirebiliyordu.)
BOSS_LIFESTEAL_VS_DPS = 0.12
# Oyuncunun gücü hiç ölçülemezse kullanılan yedek tavan (azami canın oranı).
BOSS_LIFESTEAL_CAP = 0.004

# Patronun kaçabileceği AZAMİ mesafe.
# "Çaresiz" faza geçen patron, kısa kaçışlarını üst üste bindirerek arenanın
# öbür ucuna kadar gidiyor ve orada takılıyordu; ölçümde 10. dalga dövüşü
# 300 saniyeyi aşıyor, patron pratikte ulaşılamaz hâle geliyordu. Bu mesafeye
# ulaşınca kaçış iptal edilir ve patron tekrar oyuncuya döner.
BOSS_FLEE_MAX_DIST = 380.0

BOSS_HP_NERF = 0.85
BOSS_DMG_NERF = 0.85
BOSS_TELEGRAPH_EXTRA = 0.40


def boss_index_for_wave(wave):
    """Kaçıncı patron olduğunu döndürür (10. dalga -> 1, 15 -> 2, 20 -> 3 ...)."""
    if wave < BOSS_FIRST_WAVE:
        return 1
    return (wave - BOSS_FIRST_WAVE) // BOSS_WAVE_STEP + 1


def boss_power(wave, index=None):
    """Patronun dalgaya göre güç çarpanları: (can, hasar, zırh).

    `index` verilirse dalga yerine o patron dizini kullanılır — cehennem
    patronları arenanın son patronundan zayıf başlamasın diye gerekli.

    Patronlar artık sıradan bir düşman değil: her yeni patron hem belirgin
    biçimde daha etli hem de ZIRHLI gelir. Zırh, gelen hasarın sabit bir
    yüzdesini keser; böylece oyuncu ne kadar güçlenirse güçlensin patron
    birkaç saniyede eriyip gitmez.
    """
    idx = int(index) if index is not None else boss_index_for_wave(wave)
    hp = 1.12 + (idx - 1) * 0.62 + ((idx - 1) ** 1.6) * 0.055
    # DENGE: hasar artışı çok zayıftı (patron başına yalnızca +%16). Oyuncu
    # 10. dalgadan 20. dalgaya kadar kat kat güçlenirken patronlar yerinde
    # sayıyor, 15. ve 20. dalga patronları 10. dalgadakinden kolay geliyordu.
    dmg = 1.0 + (idx - 1) * 0.26 + ((idx - 1) ** 1.5) * 0.02
    armor = clamp(0.12 + (idx - 1) * 0.035, 0.0, 0.45)
    return hp, dmg, armor


def boss_hp_share(n_boss):
    """Birden fazla patron varken her birinin can payı.

    Toplam can, tek patronlu bir dalganın 1.7 katı olur: yani iki patron,
    tek patronun iki katı kadar dayanıklı DEĞİLDİR. Amaç dövüşü uzatmak
    değil, aynı anda iki ayrı tehdidi yönetmeyi zorunlu kılmak.

    DENGE: pay eskiden 1.35 idi; 20. dalgadaki iki patron tek tek çok çabuk
    eriyor, dalga tek patronlu 15. dalgadan bile kolay geçiyordu.
    """
    return 1.0 if n_boss <= 1 else 1.7 / n_boss


def boss_count_for_wave(wave):
    """Geç dalgalarda aynı anda birden fazla patron gelir."""
    if wave >= 35:
        return 3
    if wave >= 20:
        return 2
    return 1


class Boss:
    def __init__(self, kind, x, y, hp_mult, diff_mult=1.0, wave=10, hellish=False):
        d = BOSS_DEFS[kind]
        self.kind = kind
        # CEHENNEM PATRONU: davranışı arena patronuyla aynı (dengesi oturmuş),
        # kimliği bambaşka — yeni ad, yeni renk, alev görselliği ve daha yüksek
        # güç dizini (arenanın son patronundan zayıf olamaz).
        self.hellish = bool(hellish)
        self.name = HELL_BOSS_NAMES.get(kind, d["name"]) if hellish else d["name"]
        self.x, self.y = x, y
        self.wave = wave
        # Patronlar dalgaya göre üç eksende birden güçlenir: can, hasar ve ZIRH.
        # Zırh en kritik olanı — oyuncu eşyalarını doldurup saniyede binlerce
        # hasar vursa bile patron artık anında erimiyor, gerçek bir dövüş oluyor.
        dmgm = late_wave_dmg_mult(hell_dmg_wave(wave) if hellish else wave)
        self.boss_index = hell_boss_index(wave) if hellish else boss_index_for_wave(wave)
        pw_hp, pw_dmg, pw_armor = boss_power(wave, index=self.boss_index)
        self.armor = pw_armor
        self.max_hp = d["hp"] * hp_mult * diff_mult * pw_hp * BOSS_HP_NERF
        self.hp = self.max_hp
        # Cehennemde patron da yavaşlar (yaratıklarla aynı kural), ama canı
        # ve hasarı tam güçtedir.
        self.speed = d["speed"] * (0.82 if hellish else 1.0)
        self.dmg = d["dmg"] * diff_mult * pw_dmg * (0.55 + 0.45 * dmgm) * BOSS_DMG_NERF
        self.radius = d["radius"]
        self.hit_r = self.radius * 0.92
        self.color = HELL_BOSS_COLORS.get(kind, d["color"]) if hellish else d["color"]
        self.alive = True
        self.spawn_t = 0.0
        self.hit_flash = 0.0
        self.phase = 1
        self.atk_timer = 1.4
        self.telegraph = None  # ("kind", x, y, r, timer, total)
        self.wobble = 0.0
        self.touch_cd = 0.0
        self.enraged = False
        self.desperate = False  # 3. faz: çok düşük canda kaçıp yaratık çağırır
        self.is_boss = True
        # Zorlaştıkça ödül de büyür — geç dalgadaki patronu yenmek gerçekten değsin.
        self.score = int(800 * (1.0 + (self.boss_index - 1) * 0.45))
        self.coin = int(260 * (1.0 + (self.boss_index - 1) * 0.35))
        self.xp = int(220 * (1.0 + (self.boss_index - 1) * 0.30))
        # Yaratık çağırma / kaçış mekaniği
        self.summon_cd = random.uniform(5.0, 7.0)
        self.flee_timer = 0.0
        self.summoned_enemies = []
        self.teleport_cd = random.uniform(4.0, 6.0)   # yalnızca "reaper" kullanır
        # --- İMZA ÖZELLİĞİ (bkz. BOSS_TRAITS) ---
        # Her patron farklı vurur: kimi yakar, kimi zehirler, kimi yavaşlatır,
        # kimi görünmez olur, kimi dibine ışınlanır.
        self.trait = boss_trait(kind, hellish)
        self.vanish_t = 0.0                            # görünmezlik kalan süresi
        self.vanish_cd = random.uniform(5.5, 8.0)      # bir sonraki görünmezliğe kalan
        self.fly_t = 0.0                               # EJDERHA: havada geçen süre
        self.fly_dir = (0.0, 0.0)
        self.fly_cd = random.uniform(6.0, 9.0)
        self.trail_acc = 0.0                           # alev/iz bırakma sayacı
        # Çizim için: patronun baktığı yön (yumuşatılmış) ve yürüyüş fazı.
        # Gövde, kanatlar, silahlar ve gözler bu yöne göre çizilir; patronlar
        # artık ekranda dönen soyut şekiller değil, oyuncuya BAKAN yaratıklar.
        self.face_x, self.face_y = 0.0, 1.0
        self.gait = random.uniform(0, math.tau)
        # --- YAYLIM ATEŞ -------------------------------------------------
        # Eskiden yalnızca SAVAŞ LORDU ve ORAK mermi atıyordu; GÖLGE CADISI,
        # KOLOS ve KOVAN ANA'nın tek saldırısı yere telgraflanan alan hasarıydı
        # ve kaçan bir oyuncuya asla dokunamıyorlardı. Artık HER patronun
        # düzenli bir menzilli tehdidi var.
        self.volley_cd = random.uniform(2.2, 3.4)
        # --- HÜCUM (yalnızca KOLOS) --------------------------------------
        self.charge_t = 0.0
        self.charge_dir = (0.0, 0.0)
        # Her patron farklı mesafede savaşır: KOLOS üstüne gelir, CADI uzak durur.
        self.want_dist = {"warlord": 190, "witch": 215, "colossus": 110,
                          "reaper": 160, "hive": 205, "dragon": 245}.get(kind, 190)
        # Zehir patronlarda da işler (süresi yoktur, ölene kadar sürer).
        self.poison_dps = 0.0
        self.poison_tick_acc = 0.0
        # --- CAN ÇALMA ---------------------------------------------------
        # Oyuncu kan emme eşyalarıyla sürekli can çalıyor ve patronu tek
        # taraflı olarak eritiyordu. Artık patron da verdiği hasarın bir
        # kısmını canına ekliyor; dövüş gerçek bir düelloya dönüşüyor.
        self.lifesteal = clamp(0.20 + 0.05 * (self.boss_index - 1), 0.0, 0.45)
        self.heal_budget = 0.0         # saniyede yenilenen can çalma bütçesi
        self.heal_rate = None          # saniyelik can çalma tavanı (spawn'da ayarlanır)
        self.heal_flash = 0.0
        self.healed_total = 0.0
        self.fight_time = 0.0          # dövüşün başından beri geçen süre

    # ---------------- İMZA ÖZELLİĞİ ----------------
    def afflict(self, player, k=1.0):
        """Patronun imza etkisini oyuncuya uygular.

        Patronun HER hasar kaynağı (temas, mermi, tuzak) buradan geçer;
        böylece "ateşli patron yakar, zehirli patron zehirler" kuralı tek
        yerde tanımlı kalır.
        """
        if player is None or not player.alive:
            return
        tk = self.trait["kind"]
        base = max(1.0, self.dmg)
        if tk in ("burn", "inferno"):
            player.apply_burn(base * (0.34 if tk == "inferno" else 0.28) * k,
                              3.2, self.name)
        elif tk == "venom":
            player.apply_poison(base * 0.22 * k, 5.5, self.name)
        elif tk == "chill":
            player.apply_slow(0.58, 1.8)
        elif tk == "vanish":
            player.apply_slow(0.74, 1.4)
            player.apply_poison(base * 0.10 * k, 3.0, self.name)
        elif tk == "blink":
            player.apply_poison(base * 0.16 * k, 4.0, self.name)
        # CEHENNEM patronları ayrıca yakar — cehennemde her darbe ateş taşır.
        if self.trait.get("hellfire") and tk not in ("burn", "inferno"):
            player.apply_burn(base * 0.15 * k, 2.4, self.name)

    def hit_player(self, player, amount, fx, src_x=None, src_y=None):
        """Oyuncuya hasar verir + imza etkisini uygular + can çalar.

        Patronun hasar verdiği her yer bu tek kapıdan geçsin diye var:
        yeni bir saldırı eklerken etkiyi ayrıca yazmak gerekmez.
        """
        if not player.alive:
            return 0.0
        dealt = player.take_damage(amount, fx,
                                   self.x if src_x is None else src_x,
                                   self.y if src_y is None else src_y, self.name)
        if dealt > 0:
            self.afflict(player)
            self.on_damage_dealt(amount)
        return dealt

    def is_hidden(self):
        """GÖLGE PERDESİ açıkken patron neredeyse görünmezdir."""
        return self.vanish_t > 0

    def _update_trait(self, dt, player, fx, projectiles, hazards):
        """İmza özelliğinin kare kare işleyişi (görünmezlik, uçuş, alev izi)."""
        tk = self.trait["kind"]

        # --- GÖLGE PERDESİ: kaybolur, sonra dibinde belirir ---
        if tk == "vanish" and self.spawn_t > 2.0:
            if self.vanish_t > 0:
                self.vanish_t -= dt
                # görünmezken hızla konum değiştirir
                dx, dy = norm_dir(self.x, self.y, player.x, player.y)
                self.x += dx * self.speed * 1.35 * dt
                self.y += dy * self.speed * 1.35 * dt
                if random.random() < dt * 6:
                    fx.spark(self.x + random.uniform(-20, 20), self.y + random.uniform(-20, 20),
                             self.color, 0, -30, 0.4, 3)
                if self.vanish_t <= 0:
                    fx.shockwave(self.x, self.y, 170, self.color, 0.4, 6)
                    fx.popup(self.x, self.y - self.radius - 28, "BELİRDİ!", self.color, 22, life=0.8)
                    sfx("warn", 0.7, 0.0)
                    self.atk_timer = 0.05      # belirir belirmez vurur
            else:
                self.vanish_cd -= dt
                if self.vanish_cd <= 0:
                    self.vanish_cd = random.uniform(7.0, 10.5) * (0.65 if self.enraged else 1.0)
                    self.vanish_t = 3.0 if self.enraged else 2.4
                    fx.ring(self.x, self.y, self.color, n=22, speed=210, life=0.45, r=3)
                    fx.popup(self.x, self.y - self.radius - 28, "GÖLGE PERDESİ!",
                             self.color, 20, life=0.9)
                    sfx("dash", 0.7, 0.0)

        # --- EJDERHA: havalanıp oyuncunun üstüne dalar, ardında alev bırakır ---
        if tk == "inferno":
            if self.fly_t > 0:
                self.fly_t -= dt
                self.x += self.fly_dir[0] * self.speed * 3.6 * dt
                self.y += self.fly_dir[1] * self.speed * 3.6 * dt
                self.trail_acc += dt
                if self.trail_acc >= 0.14:
                    self.trail_acc = 0.0
                    hazards.append(Hazard(self.x, self.y, 52, 0.35, self.dmg * 0.65, owner=self))
                fx.spark(self.x + random.uniform(-30, 30), self.y + random.uniform(-30, 30),
                         (255, 170, 70), random.uniform(-40, 40), random.uniform(-40, 40), 0.4, 5)
                if self.fly_t <= 0:
                    # yere iniş: çevresine halka biçiminde alev saçar
                    fx.shockwave(self.x, self.y, 230, (255, 140, 60), 0.5, 8)
                    fx.shake(12, 0.35)
                    sfx("explosion", 0.8, 0.0)
                    for i in range(8):
                        a = i * math.tau / 8 + random.uniform(-0.2, 0.2)
                        hx = clamp(self.x + math.cos(a) * 130, ARENA_RECT.left + 20, ARENA_RECT.right - 20)
                        hy = clamp(self.y + math.sin(a) * 130, ARENA_RECT.top + 20, ARENA_RECT.bottom - 20)
                        hazards.append(Hazard(hx, hy, 58, 0.25 + i * 0.05, self.dmg * 0.8, owner=self))
            else:
                self.fly_cd -= dt
                if self.fly_cd <= 0 and self.spawn_t > 2.0:
                    self.fly_cd = random.uniform(8.0, 12.0) * (0.7 if self.enraged else 1.0)
                    px, py = self._lead_point(player, 0.5)
                    self.fly_dir = norm_dir(self.x, self.y, px, py)
                    self.fly_t = 0.85
                    self.trail_acc = 0.0
                    fx.popup(self.x, self.y - self.radius - 30, "EJDERHA DALIYOR!",
                             (255, 170, 80), 24, life=1.0)
                    fx.ring(self.x, self.y, (255, 160, 70), n=20, speed=240, life=0.45, r=4)
                    sfx("warn", 0.9, 0.0)

        # --- ATEŞLİ ÇELİK / EJDER ATEŞİ: yürüdüğü yerde kor bırakır ---
        if self.trait.get("hellfire") and self.fly_t <= 0 and self.spawn_t > 1.0:
            if random.random() < dt * 4.5:
                fx.spark(self.x + random.uniform(-self.radius, self.radius),
                         self.y + self.radius * 0.5,
                         (255, 170, 80), random.uniform(-14, 14), -40, 0.5, 4)

    def on_damage_dealt(self, amount):
        """Patron verdiği hasarın bir kısmını canına ekler (can çalma)."""
        if not self.alive or self.lifesteal <= 0 or amount <= 0:
            return
        heal = min(amount * self.lifesteal, self.heal_budget)
        if heal <= 0:
            return
        self.heal_budget -= heal
        before = self.hp
        self.hp = min(self.max_hp, self.hp + heal)
        gained = self.hp - before
        if gained > 0.5:
            self.heal_flash = 0.45
            self.healed_total += gained

    def apply_poison(self, dps):
        self.poison_dps += dps

    def apply_burn(self, dps, duration):
        """Patronlar da yanabilsin diye: yanık, zehirden farklı olarak süreli."""
        self.burn_timer = max(getattr(self, "burn_timer", 0.0), duration)
        self.burn_dps = max(getattr(self, "burn_dps", 0.0), dps)

    def apply_slow(self, mult, duration):
        cur = getattr(self, "slow_mult", 1.0)
        if getattr(self, "slow_timer", 0.0) <= 0 or mult < cur:
            self.slow_mult = mult
        self.slow_timer = max(getattr(self, "slow_timer", 0.0), duration)

    def update(self, dt, player, fx, projectiles, hazards, kill_cb=None):
        if not self.alive:
            return
        self.spawn_t += dt
        self.fight_time += dt
        self.wobble += dt * 3
        # can çalma bütçesi saniyede yenilenir (en fazla 1 saniyelik birikir)
        cap = self.heal_rate if self.heal_rate is not None else self.max_hp * BOSS_LIFESTEAL_CAP
        self.heal_budget = min(cap, self.heal_budget + cap * dt)
        if self.heal_flash > 0:
            self.heal_flash -= dt
        if self.touch_cd > 0:
            self.touch_cd -= dt

        # --- ZEHİR / YANIK: patron da bu etkilerden hasar alır ---
        if self.poison_dps > 0:
            self.poison_tick_acc += dt
            while self.poison_tick_acc >= 0.5 and self.alive:
                self.poison_tick_acc -= 0.5
                if self.take_damage(self.poison_dps * 0.5, False, fx) and kill_cb:
                    kill_cb(self)
            if not self.alive:
                return
        if getattr(self, "burn_timer", 0.0) > 0:
            self.burn_timer -= dt
            self.burn_tick_acc = getattr(self, "burn_tick_acc", 0.0) + dt
            while self.burn_tick_acc >= 0.5 and self.alive:
                self.burn_tick_acc -= 0.5
                if self.take_damage(self.burn_dps * 0.5, False, fx) and kill_cb:
                    kill_cb(self)
            if self.burn_timer <= 0:
                self.burn_dps = 0.0
            if not self.alive:
                return
        scale_in = ease_out_cubic(self.spawn_t / 0.6)
        # Baktığı yön oyuncuya doğru yumuşakça döner + yürüyüş fazı ilerler.
        if player.alive:
            tfx, tfy = norm_dir(self.x, self.y, player.x, player.y)
            k = min(1.0, dt * 5.0)
            self.face_x += (tfx - self.face_x) * k
            self.face_y += (tfy - self.face_y) * k
            fl = math.hypot(self.face_x, self.face_y) or 1.0
            self.face_x /= fl
            self.face_y /= fl
        self.gait += dt * (7.0 if self.fly_t > 0 else 3.4)
        # Fazlar artık daha erken tetikleniyor: patron dövüşünün büyük bölümü
        # öfkeli geçiyor, yani daha hızlı ve daha agresif.
        if not self.enraged and self.hp < self.max_hp * 0.62:
            self.enraged = True
            fx.popup(self.x, self.y - self.radius - 30, "ÖFKELENDİ!", (255, 90, 70), 26, life=1.2)
            fx.do_flash((255, 60, 40), 0.35)
        if not self.desperate and self.hp < self.max_hp * 0.26:
            self.desperate = True
            self.summon_cd = min(self.summon_cd, 1.0)
            fx.popup(self.x, self.y - self.radius - 30, "ÇARESİZ!", (255, 190, 60), 28, life=1.3)
            fx.do_flash((255, 210, 80), 0.3)
            sfx("warn", 0.9, 0.0)

        # Öfkelendikten sonra periyodik olarak yanına yeni yaratıklar çağırır
        # ve kısa bir süre oyuncudan kaçarak mesafe açar — boss artık pasif bir
        # hedef değil, savaş alanını yöneten bir tehdit.
        # KOVAN ANA bunu daha da ileri götürür: öfkelenmeyi beklemeden çağırır.
        if self.enraged or self.kind == "hive":
            self.summon_cd -= dt
            if self.summon_cd <= 0 and self.spawn_t > 1.0:
                base_cd = 4.2 if self.kind == "hive" else random.uniform(5.0, 7.0)
                self.summon_cd = base_cd * (0.55 if self.desperate else 1.0)
                self._summon_minions(fx)
                self.flee_timer = max(self.flee_timer, 2.4 if self.desperate else 1.6)

        # --- İMZA ÖZELLİĞİ: görünmezlik / uçuş / alev izi ---
        self._update_trait(dt, player, fx, projectiles, hazards)

        # ORAK: RUH SIÇRAMASI — oyuncunun DİBİNE ışınlanır ve anında vurur.
        # Eskiden 150 px uzağa, rastgele bir açıya ışınlanıyordu ve oyuncu
        # çoğu zaman bunu fark bile etmiyordu. Artık sıçrama gerçek bir tehdit:
        # arkanda beliriyor ve bekleme süresini sıfırlayıp saldırıya geçiyor.
        if self.kind == "reaper" and self.spawn_t > 1.2:
            self.teleport_cd -= dt
            if self.teleport_cd <= 0:
                self.teleport_cd = random.uniform(2.8, 4.4) * (0.55 if self.enraged else 1.0)
                fx.ring(self.x, self.y, self.color, n=16, speed=180, life=0.3, r=2.5)
                # oyuncunun GİTTİĞİ yönün tersine, yani tam arkasına
                mvx, mvy = getattr(player, "vx", 0.0), getattr(player, "vy", 0.0)
                ml = math.hypot(mvx, mvy)
                if ml > 40:
                    ang = math.atan2(-mvy / ml, -mvx / ml) + random.uniform(-0.5, 0.5)
                else:
                    ang = random.uniform(0, math.tau)
                rad = self.want_dist * 0.62
                self.x = clamp(player.x + math.cos(ang) * rad,
                               ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
                self.y = clamp(player.y + math.sin(ang) * rad,
                               ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)
                fx.ring(self.x, self.y, self.color, n=22, speed=240, life=0.38, r=3)
                fx.spark(self.x, self.y, self.color, 0, -60, 0.5, 6)
                sfx("warn", 0.5, 0.0)
                self.flee_timer = 0.0
                self.atk_timer = min(self.atk_timer, 0.18)   # belirince hemen vurur

        d = dist(self.x, self.y, player.x, player.y)
        dx, dy = norm_dir(self.x, self.y, player.x, player.y)
        if self.fly_t > 0:
            # EJDERHA havada: yönünü _update_trait belirliyor, burada durulur.
            pass
        elif self.charge_t > 0:
            # KOLOS HÜCUMU: telgraflanan yönde hızla ilerler, yolundakini ezer.
            self.charge_t -= dt
            cs = self.speed * 5.4
            self.x += self.charge_dir[0] * cs * dt
            self.y += self.charge_dir[1] * cs * dt
            fx.spark(self.x + random.uniform(-self.radius, self.radius),
                     self.y + random.uniform(-self.radius, self.radius),
                     self.color, random.uniform(-40, 40), random.uniform(-40, 40), .35, 5)
            if (self.x <= ARENA_RECT.left + self.radius or self.x >= ARENA_RECT.right - self.radius
                    or self.y <= ARENA_RECT.top + self.radius or self.y >= ARENA_RECT.bottom - self.radius):
                # duvara toslar: sersemler ve yer sarsılır
                self.charge_t = 0.0
                fx.shockwave(self.x, self.y, 190, self.color, 0.5, 7)
                fx.shake(12, 0.35)
                sfx("bonk", 0.8, 0.0)
        elif self.flee_timer > 0:
            self.flee_timer -= dt
            if d >= BOSS_FLEE_MAX_DIST:
                # Yeterince uzaklaştı: kaçışı kes, dövüşe geri dön.
                self.flee_timer = 0.0
            else:
                flee_k = 1.9 if self.desperate else 1.5
                self.x -= dx * self.speed * flee_k * dt * scale_in
                self.y -= dy * self.speed * flee_k * dt * scale_in
        else:
            want_d = self.want_dist
            speed_k = 1.7 if self.enraged else 1.2
            if d > want_d + 20:
                self.x += dx * self.speed * speed_k * dt * scale_in
                self.y += dy * self.speed * speed_k * dt * scale_in
            elif d < want_d - 20:
                self.x -= dx * self.speed * 0.6 * dt * scale_in
                self.y -= dy * self.speed * 0.6 * dt * scale_in
        self.x = clamp(self.x, ARENA_RECT.left + self.radius, ARENA_RECT.right - self.radius)
        self.y = clamp(self.y, ARENA_RECT.top + self.radius, ARENA_RECT.bottom - self.radius)

        if self.hit_flash > 0:
            self.hit_flash -= dt

        # --- YAYLIM ATEŞ: her patronun düzenli menzilli tehdidi ---
        if self.spawn_t > 1.5 and self.charge_t <= 0 and self.fly_t <= 0 and not self.is_hidden():
            self.volley_cd -= dt
            if self.volley_cd <= 0:
                self.volley_cd = self._volley_interval()
                self._fire_volley(player, fx, projectiles)

        if self.telegraph:
            kind, tx, ty, r, timer, total = self.telegraph
            timer -= dt
            if timer <= 0:
                self._unleash(kind, tx, ty, r, player, fx, projectiles, hazards)
                self.telegraph = None
            else:
                self.telegraph = (kind, tx, ty, r, timer, total)
        else:
            self.atk_timer -= dt
            if (self.atk_timer <= 0 and self.spawn_t > 1.0
                    and self.fly_t <= 0 and not self.is_hidden()):
                # Saldırı temposu hem faza hem de kaçıncı patron olduğuna bağlı:
                # geç dalgalardaki patronlar gözle görülür biçimde daha sık vurur.
                cadence = 0.32 if self.desperate else (0.46 if self.enraged else 0.85)
                cadence *= max(0.45, 1.0 - (self.boss_index - 1) * 0.11)
                self.atk_timer = random.uniform(0.9, 1.45) * cadence
                self._start_attack(player, fx)

        if player.alive and self.touch_cd <= 0:
            if dist(self.x, self.y, player.x, player.y) < self.hit_r + player.radius - 3:
                self.touch_cd = 0.42
                # Hücum eden KOLOS'a ya da dalışa geçen EJDERHA'ya çarpmak
                # sıradan temastan çok daha acıtır.
                touch_dmg = self.dmg * (1.7 if (self.charge_t > 0 or self.fly_t > 0) else 1.0)
                self.hit_player(player, touch_dmg, fx)

    def _summon_minions(self, fx):
        """Boss'un yanına yeni, daha küçük yaratıklar doğurur ve oyuncudan
        kaçmaya başlar — böylece oyuncu hem patronla hem de çağrılan
        yaratıklarla aynı anda uğraşmak zorunda kalır."""
        if self.kind == "hive":
            n = 5 if self.desperate else 4
            kinds = ["red", "sprinter", "blue", "yellow"]
        else:
            n = 4 if self.desperate else 3
            kinds = ["red", "sprinter", "blue"]
        # Çağrılan yaratıklar patronun dalgasıyla ölçeklenir; 30. dalgadaki
        # patronun yaratıkları da 30. dalga gücündedir.
        mult = 1.0 + max(0, self.wave - 1) * 0.20
        for _ in range(n):
            ang = random.uniform(0, math.tau)
            mx = clamp(self.x + math.cos(ang) * 100, ARENA_RECT.left + 20, ARENA_RECT.right - 20)
            my = clamp(self.y + math.sin(ang) * 100, ARENA_RECT.top + 20, ARENA_RECT.bottom - 20)
            kind = random.choice(kinds)
            if self.hellish:
                self.summoned_enemies.append(
                    Enemy(kind, mx, my, mult, 1.0, wave=self.wave,
                          variant=hell_pick_kind(self.wave), biome="hell"))
            else:
                self.summoned_enemies.append(Enemy(kind, mx, my, mult, 1.0, wave=self.wave))
        fx.ring(self.x, self.y, self.color, n=18, speed=190, life=0.4, r=3)
        fx.popup(self.x, self.y - self.radius - 10, "YARATIKLAR ÇAĞIRIYOR!", self.color, 16, life=0.9)
        sfx("warn", 0.6, 0.0)

    def _set_telegraph(self, kind, a, b, c, dur):
        """Patronun TÜM saldırıları bu kapıdan geçer.

        BOSS_TELEGRAPH_EXTRA her saldırının hazırlık süresine sabit olarak
        eklenir; böylece hiçbir saldırı tipi yanlışlıkla "anında ateş eden"
        hâlde kalmaz ve oyuncu her zaman kaçacak zamanı bulur.
        """
        total = dur + BOSS_TELEGRAPH_EXTRA
        self.telegraph = (kind, a, b, c, total, total)

    def _lead_point(self, player, lead=0.34):
        """Oyuncunun BULUNDUĞU yere değil, GİDECEĞİ yere nişan alır.

        Alan saldırıları eskiden oyuncunun o anki konumuna telgraflanıyordu;
        oyuncu bir saniyelik hazırlık süresi boyunca yürüyüp gittiği için
        KOLOS ve KOVAN ANA gibi yalnızca alan saldırısı olan patronlar hiçbir
        zaman isabet ettiremiyordu.
        """
        lx = player.x + getattr(player, "vx", 0.0) * lead
        ly = player.y + getattr(player, "vy", 0.0) * lead
        return (clamp(lx, ARENA_RECT.left + 20, ARENA_RECT.right - 20),
                clamp(ly, ARENA_RECT.top + 20, ARENA_RECT.bottom - 20))

    def _ring_count(self):
        """Lanet çemberindeki tuzak sayısı.

        Tuzaklar arasında MUTLAKA geçilebilir boşluk kalmalı; aksi hâlde
        oyuncu çemberin içine kapanır ve saldırıdan kaçmanın yolu kalmaz.
        Sayı bu yüzden sınırlı tutulur, halkanın yarıçapı ise patron
        seviyesiyle büyür.
        """
        want = 7 + min(3, self.boss_index - 1) + (1 if self.enraged else 0)
        # Halkanın çevresi, istenen tuzak sayısını geçilebilir aralıklarla
        # taşıyamıyorsa tuzak sayısı kırpılır — çember asla tamamen kapanmaz.
        max_n = int((math.tau * self._ring_radius()) // BOSS_RING_GAP_MIN)
        return max(5, min(want, max_n))

    def _ring_radius(self):
        # Yarıçap tuzak sayısından daha hızlı büyür; böylece tuzak merkezleri
        # arasındaki uzaklık her zaman 2*(tuzak_yarıçapı + oyuncu_yarıçapı)
        # değerinin üstünde kalır ve aradan geçilebilir.
        return 160 + self.boss_index * 12

    def _volley_interval(self):
        """İki yaylım ateş arasındaki süre — geç patronlarda belirgin kısalır."""
        base = max(1.5, 5.0 - (self.boss_index - 1) * 0.80)
        if self.desperate:
            base *= 0.55
        elif self.enraged:
            base *= 0.72
        return base * random.uniform(0.85, 1.15)

    def _ranged_dmg_k(self):
        """Menzilli saldırıların hasar katsayısı.

        Vuruş başına hasar zaten dalgayla üssel büyüdüğü için, geç
        patronlarda mermi hasarı biraz kısılır; aksi hâlde tek bir yaylım
        ateş oyuncuyu bir anda siliyor ve dövüş adaletsiz hâle geliyor.
        """
        return max(0.45, 1.0 - (self.boss_index - 1) * 0.09)

    def _shoot(self, projectiles, ang, speed, dmg_k, r=8, color=None,
               target=None, turn=0.0, accel=0.0):
        projectiles.append(EnemyProjectile(
            self.x, self.y, math.cos(ang) * speed, math.sin(ang) * speed,
            self.dmg * dmg_k * self._ranged_dmg_k(), color=color or self.color, r=r,
            target=target, turn=turn, accel=accel, owner=self))

    def _fire_volley(self, player, fx, projectiles):
        """Her patronun kendine özgü MENZİLLİ saldırısı.

        Bu, patronların "kaçan oyuncuya dokunamama" sorununu çözen ana
        eklemedir: artık GÖLGE CADISI lanet mermileri, KOLOS yerden yayılan
        şok dalgası, KOVAN ANA takip eden spor okları atar.
        """
        bi = self.boss_index
        px, py = self._lead_point(player, 0.20)
        base = math.atan2(py - self.y, px - self.x)
        eng = self.enraged or self.desperate

        if self.kind == "warlord":
            # Üç mermilik kısa seri — SAVAŞ LORDU zaten ışın yağdırıyor.
            n = 3 + min(3, (bi - 1) // 2)
            for i in range(n):
                self._shoot(projectiles, base + (i - (n - 1) / 2) * 0.16,
                            420 + bi * 14, 0.50, r=7)
            sfx("shoot_c", 0.5, 0.0)

        elif self.kind == "witch":
            # LANET MERMİLERİ: yay biçiminde çıkar, bir süre oyuncuyu takip eder.
            n = 4 + min(3, bi) + (2 if eng else 0)
            spread = 1.05
            for i in range(n):
                ang = base + (i - (n - 1) / 2) * (spread / max(1, n - 1))
                self._shoot(projectiles, ang, 290 + bi * 14, 0.46, r=8,
                            color=(175, 110, 235), target=player,
                            turn=1.9 + 0.12 * bi, accel=40)
            fx.ring(self.x, self.y, (175, 110, 235), n=14, speed=150, life=0.35, r=3)
            sfx("shoot_c", 0.55, 0.0)

        elif self.kind == "colossus":
            # ŞOK DALGASI: yerden her yöne yayılan ağır taş parçaları.
            n = 10 + bi * 2 + (4 if eng else 0)
            off = random.uniform(0, math.tau)
            for i in range(n):
                self._shoot(projectiles, off + i * math.tau / n, 205 + bi * 8, 0.42,
                            r=11, color=(150, 165, 195))
            fx.shockwave(self.x, self.y, 150, self.color, 0.4, 6)
            fx.shake(7, 0.22)
            sfx("explosion", 0.5, 0.0)

        elif self.kind == "reaper":
            # ÇAPRAZ KESİK: iki hızlı, dar mermi dalgası.
            for wave_i in range(2):
                for o in (-0.22, 0.0, 0.22):
                    self._shoot(projectiles, base + o + wave_i * 0.11,
                                470 + bi * 16, 0.40, r=6, color=(120, 240, 210))
            sfx("shoot_c", 0.5, 0.0)

        elif self.kind == "dragon":
            # ALEV TOPLARI: ağır, yavaş ama peşini bırakmayan kor yumakları
            # + aralarına serpiştirilen küçük kıvılcımlar.
            n = 3 + min(3, bi // 2) + (2 if eng else 0)
            for i in range(n):
                ang = base + (i - (n - 1) / 2) * 0.22
                self._shoot(projectiles, ang, 275 + bi * 12, 0.52, r=13,
                            color=(255, 130, 50), target=player,
                            turn=1.1 + 0.08 * bi, accel=70)
            for i in range(4 + bi):
                self._shoot(projectiles, base + random.uniform(-0.8, 0.8),
                            360 + bi * 16, 0.26, r=6, color=(255, 205, 110))
            fx.ring(self.x, self.y, (255, 150, 60), n=16, speed=180, life=0.4, r=3.5)
            sfx("shoot_c", 0.6, 0.0)

        else:  # hive
            # SPOR OKLARI: yavaş ama ısrarla takip eden mermiler.
            n = 5 + min(3, bi) + (3 if eng else 0)
            for i in range(n):
                ang = base + random.uniform(-0.9, 0.9)
                self._shoot(projectiles, ang, 225 + bi * 12, 0.40, r=9,
                            color=(230, 190, 70), target=player,
                            turn=1.5 + 0.10 * bi, accel=55)
            fx.ring(self.x, self.y, (230, 190, 70), n=12, speed=130, life=0.35, r=3)
            sfx("shoot_c", 0.5, 0.0)

    def _start_attack(self, player, fx):
        bi = self.boss_index
        if self.kind == "warlord":
            n = 9 if self.enraged else 5
            n += min(4, bi - 1)          # geç patron daha geniş yelpaze açar
            spread = 0.30 if self.enraged else 0.38
            px, py = self._lead_point(player, 0.22)
            base = math.atan2(py - self.y, px - self.x)
            angs = [base + (i - (n - 1) / 2) * spread for i in range(n)]
            self._telegraph_beams(angs)
        elif self.kind == "witch":
            # LANET ÇEMBERİ: halka artık patronun değil OYUNCUNUN çevresine kurulur.
            # Eskiden patron ~190 px uzakta durup kendi çevresine 150 px yarıçaplı
            # halka açıyordu; halka oyuncuya hiç ulaşmıyor, saldırı boşa gidiyordu.
            # CADI artık iki saldırı arasında geçiş yapar: lanet çemberi ve
            # telgraflanan lanet yağmuru. Tek saldırılı patron tahmin
            # edilebilir ve sıkıcı oluyordu.
            if random.random() < (0.50 if bi >= 2 else 0.30):
                px, py = self._lead_point(player, 0.25)
                ang = math.atan2(py - self.y, px - self.x)
                self._set_telegraph("barrage", ang, 0, 0, 0.45)
            else:
                px, py = self._lead_point(player, 0.25)
                r = self._ring_radius()
                self._set_telegraph("ring_player", px, py, r, 0.62 if self.enraged else 0.80)
                fx.ring(px, py, self.color, n=24 if self.enraged else 20, speed=150, life=0.5, r=3)
        elif self.kind == "reaper":
            px, py = self._lead_point(player, 0.35)
            if random.random() < 0.5:
                # biçme darbesi: hedefin üstüne inen geniş alan
                self._set_telegraph("scythe", px, py, 120 if self.enraged else 100,
                                    0.5 if self.enraged else 0.62)
            else:
                # çapraz kesik: 2-3 hızlı ışın
                ang = math.atan2(py - self.y, px - self.x)
                offs = (-0.26, 0.0, 0.26) if self.enraged else (-0.2, 0.2)
                self._telegraph_beams([ang + o for o in offs])
        elif self.kind == "hive":
            px, py = self._lead_point(player, 0.35)
            if bi >= 2 and random.random() < 0.40:
                # SPOR YAĞMURU: telgraflanan, hızlı ve yoğun bir mermi yelpazesi.
                ang = math.atan2(py - self.y, px - self.x)
                self._set_telegraph("barrage", ang, 0, 0, 0.50)
            else:
                # Etrafına dağılan, birbirini takip eden çoklu zehir havuzları.
                self._set_telegraph("spore", px, py, 90, 0.7 if self.enraged else 0.85)
                fx.ring(self.x, self.y, self.color, n=16, speed=140, life=0.45, r=3)
        elif self.kind == "dragon":
            px, py = self._lead_point(player, 0.40)
            ang = math.atan2(py - self.y, px - self.x)
            roll = random.random()
            if roll < 0.50:
                # ALEV PÜSKÜRTME: önüne uzanan, yere kor döşeyen alev koridoru
                self._set_telegraph("breath", ang, 0, 0, 0.62 if self.enraged else 0.80)
                fx.popup(self.x, self.y - self.radius - 28, "ALEV PÜSKÜRTÜYOR!",
                         (255, 170, 80), 22, life=0.9)
            elif roll < 0.78:
                # ALEV DUVARI: oyuncunun yoluna dikine bir ateş perdesi çeker
                self._set_telegraph("firewall", px, py, ang, 0.58)
            else:
                # KANAT DARBESİ: çevresine halka biçiminde kor saçar
                self._set_telegraph("wingburst", self.x, self.y, 200, 0.55)

        else:  # colossus
            px, py = self._lead_point(player, 0.45)
            if bi >= 2 and random.random() < 0.45:
                # HÜCUM: yavaş olan KOLOS artık aradaki mesafeyi kapatabiliyor.
                self._set_telegraph("charge", px, py, 0, 0.62)
                fx.popup(self.x, self.y - self.radius - 26, "HÜCUM!", (255, 150, 60), 22, life=0.8)
            else:
                r = 165 if self.enraged else 140
                self._set_telegraph("slam", px, py, r, 0.52 if self.enraged else 0.68)
                fx.popup(px, py - 40, "!", (255, 90, 70), 30, life=0.7)
        sfx("warn", 0.7, 0.0)

    def _telegraph_beams(self, angles):
        """Aynı anda birden fazla ışını hedefler.

        DÜZELTME: eskiden her ışın için _telegraph_line çağrılıyor ve her çağrı
        bir öncekini eziyordu — bu yüzden SAVAŞ LORDU 4-7 ışınlık yelpaze
        açması gerekirken aslında tek bir ışın atıyordu. Artık açıların tamamı
        tek bir telegraph içinde tutuluyor ve hepsi birden ateşleniyor.
        """
        self._set_telegraph("beam", list(angles), 0, 0, 0.48)

    def _unleash(self, kind, a, b, c, player, fx, projectiles, hazards):
        if kind == "beam":
            speed = 430 if self.enraged else 375
            angs = a if isinstance(a, (list, tuple)) else [a]
            for ang in angs:
                projectiles.append(EnemyProjectile(self.x, self.y, math.cos(ang) * speed, math.sin(ang) * speed,
                                                    self.dmg * 0.9, color=self.color, r=8, owner=self))
                fx.bolt([(self.x, self.y), (self.x + math.cos(ang) * 60, self.y + math.sin(ang) * 60)],
                        self.color, 0.2)
            sfx("shoot_c", 0.6, 0.0)
        elif kind == "hazard_ring":
            n = 11 if self.enraged else 8
            for i in range(n):
                ang = i * math.tau / n
                hx = self.x + math.cos(ang) * 150
                hy = self.y + math.sin(ang) * 150
                hx = clamp(hx, ARENA_RECT.left + 20, ARENA_RECT.right - 20)
                hy = clamp(hy, ARENA_RECT.top + 20, ARENA_RECT.bottom - 20)
                hazards.append(Hazard(hx, hy, 56, 0.9, self.dmg * 1.0, owner=self))
        elif kind == "ring_player":
            # LANET ÇEMBERİ: oyuncunun çevresine kapanan halka. Oyuncu ya
            # ortada kalır ya da halkadaki boşluktan kaçar — ama artık
            # saldırıyı görmezden gelip ateş etmeye devam edemez.
            n = self._ring_count()
            for i in range(n):
                ang = i * math.tau / n + random.uniform(-0.05, 0.05)
                hx = clamp(a + math.cos(ang) * c, ARENA_RECT.left + 20, ARENA_RECT.right - 20)
                hy = clamp(b + math.sin(ang) * c, ARENA_RECT.top + 20, ARENA_RECT.bottom - 20)
                hazards.append(Hazard(hx, hy, BOSS_RING_HAZARD_R, 0.45, self.dmg * 0.80, owner=self))
            fx.shockwave(a, b, c, self.color, 0.45, 6)
        elif kind == "barrage":
            # YAĞMUR: telgraflanan yöne doğru sıkı ve hızlı bir mermi yelpazesi.
            # (CADI'nın lanet yağmuru / KOVAN ANA'nın spor yağmuru.)
            n = 7 + self.boss_index * 2 + (3 if self.enraged else 0)
            spread = 0.62
            speed = 330 + self.boss_index * 20
            col = (210, 120, 250) if self.kind == "witch" else (245, 205, 90)
            for i in range(n):
                ang = a + (i - (n - 1) / 2) * (spread / max(1, n - 1))
                self._shoot(projectiles, ang, speed, 0.48, r=7, color=col)
            fx.bolt([(self.x, self.y),
                     (self.x + math.cos(a) * 90, self.y + math.sin(a) * 90)], col, 0.22)
            sfx("shoot_c", 0.7, 0.0)
        elif kind == "charge":
            # KOLOS HÜCUMU: telgraflanan yöne doğru fırlar.
            self.charge_dir = norm_dir(self.x, self.y, a, b)
            self.charge_t = 0.62
            fx.shockwave(self.x, self.y, 140, self.color, 0.35, 5)
            fx.shake(9, 0.25)
            sfx("bonk", 0.6, 0.0)
        elif kind == "scythe":
            # ORAK: hedefin üstüne geniş, hızlı inen bir biçme darbesi.
            hazards.append(Hazard(a, b, c, 0.04, self.dmg * 1.25, owner=self))
            fx.shockwave(a, b, c, self.color, 0.3, 5)
            fx.shake(8, 0.22)
            sfx("bonk", 0.7, 0.0)
        elif kind == "spore":
            # KOVAN ANA: hedefin çevresine saçılan zehir havuzları.
            n = 6 if self.enraged else 4
            for i in range(n):
                ang = i * math.tau / n + random.uniform(-0.3, 0.3)
                rad = random.uniform(40, 130)
                hx = clamp(a + math.cos(ang) * rad, ARENA_RECT.left + 20, ARENA_RECT.right - 20)
                hy = clamp(b + math.sin(ang) * rad, ARENA_RECT.top + 20, ARENA_RECT.bottom - 20)
                hazards.append(Hazard(hx, hy, 50, 0.2 + i * 0.12, self.dmg * 0.85, owner=self))
        elif kind == "breath":
            # ALEV PÜSKÜRTME: patronun önünden uzanan, yere kor döşeyen koridor.
            # Hem hızlı alev mermileri hem de gecikmeli yanma havuzları bırakır.
            steps = 7 + self.boss_index
            for i in range(steps):
                d = 90 + i * 74
                hx = clamp(self.x + math.cos(a) * d, ARENA_RECT.left + 20, ARENA_RECT.right - 20)
                hy = clamp(self.y + math.sin(a) * d, ARENA_RECT.top + 20, ARENA_RECT.bottom - 20)
                hazards.append(Hazard(hx, hy, 60, 0.06 * i, self.dmg * 0.75, owner=self))
            n = 9 + self.boss_index * 2
            for i in range(n):
                self._shoot(projectiles, a + random.uniform(-0.26, 0.26),
                            330 + random.uniform(-40, 90), 0.34, r=9,
                            color=(255, 150 + random.randint(0, 60), 60))
            fx.shockwave(self.x, self.y, 130, (255, 150, 60), 0.35, 5)
            fx.shake(7, 0.25)
            sfx("explosion", 0.6, 0.0)

        elif kind == "firewall":
            # ALEV DUVARI: hedefin üstünden geçen, yola dik bir ateş perdesi.
            nx, ny = -math.sin(c), math.cos(c)
            n = 7 + self.boss_index
            for i in range(n):
                off = (i - (n - 1) / 2) * 88
                hx = clamp(a + nx * off, ARENA_RECT.left + 20, ARENA_RECT.right - 20)
                hy = clamp(b + ny * off, ARENA_RECT.top + 20, ARENA_RECT.bottom - 20)
                hazards.append(Hazard(hx, hy, 54, 0.05 + abs(i - (n - 1) / 2) * 0.05,
                                      self.dmg * 0.85, owner=self))
            sfx("explosion", 0.5, 0.0)

        elif kind == "wingburst":
            # KANAT DARBESİ: çevresine halka hâlinde kor saçar + geri iter.
            n = 14 + self.boss_index * 2
            for i in range(n):
                self._shoot(projectiles, i * math.tau / n + random.uniform(-0.08, 0.08),
                            250 + self.boss_index * 10, 0.38, r=8, color=(255, 170, 70))
            fx.shockwave(self.x, self.y, c, (255, 160, 70), 0.45, 7)
            fx.shake(9, 0.28)
            sfx("bonk", 0.7, 0.0)

        elif kind == "slam":
            hazards.append(Hazard(a, b, c, 0.05, self.dmg * 1.5, owner=self))
            fx.shake(10, 0.3)
            if self.enraged:
                # öfkeliyken iki gecikmeli darbe daha gelir
                for k in range(2):
                    hazards.append(Hazard(a + random.uniform(-80, 80), b + random.uniform(-80, 80),
                                           c * 0.8, 0.3 + k * 0.28, self.dmg * 1.15, owner=self))

    def take_damage(self, amount, crit, fx, kx=0.0, ky=0.0):
        # Patron zırhı gelen hasarın sabit bir yüzdesini keser.
        amount = amount * (1.0 - self.armor)
        self.hp -= amount
        self.hit_flash = 0.12
        col = (255, 230, 120) if crit else WHITE
        fx.popup(self.x + random.uniform(-20, 20), self.y - self.radius, f"{int(amount)}" + ("!" if crit else ""),
                 col, 20 if crit else 15, life=0.45)
        if self.hp <= 0 and self.alive:
            self.alive = False
            fx.burst(self.x, self.y, self.color, n=40, speed=260, life=0.8, r=5)
            fx.shockwave(self.x, self.y, 260, self.color, 0.6, 8)
            fx.do_flash(self.color, 0.5)
            fx.shake(14, 0.4)
            sfx("explosion", 1.0, 0.0)
            return True
        return False

    # =================================================================
    # PATRON ÇİZİMLERİ
    # -----------------------------------------------------------------
    # Her patronun kendine ait bir gövdesi var. Ortak kurallar:
    #   * Çizimler, patronun BAKTIĞI yöne göre yapılır. Koordinat üretmek
    #     için her metodun başındaki P(ileri, yan) yardımcısı kullanılır:
    #     P(1, 0) patronun bir yarıçap ÖNÜ, P(0, 1) sağı, P(-1, 0) arkasıdır.
    #     Böylece patron döndükçe kanatları, silahları ve bacakları da döner.
    #   * Önce OUTLINE ile biraz büyük bir kopya, sonra asıl renk çizilir:
    #     her parçaya koyu bir dış hat kazandırır (okunurluk).
    #   * `col` hasar alınca beyaza döner (vuruş geri bildirimi).
    #
    # YENİ PATRON EKLEMEK: buraya bir _draw_<tür> metodu yaz ve Boss.draw()
    # içindeki sözlüğe ekle.
    # =================================================================

    def _facing(self):
        """(ileri_x, ileri_y, sağ_x, sağ_y) — çizim için yön vektörleri."""
        fx_, fy_ = self.face_x, self.face_y
        l = math.hypot(fx_, fy_) or 1.0
        fx_, fy_ = fx_ / l, fy_ / l
        return fx_, fy_, -fy_, fx_

    def _mapper(self, x, y, r):
        """P(ileri, yan) -> dünya koordinatı. Bütün gövde çizimleri bunu kullanır."""
        fx_, fy_, sx_, sy_ = self._facing()

        def P(f, s):
            return (x + fx_ * r * f + sx_ * r * s,
                    y + fy_ * r * f + sy_ * r * s)
        return P, fx_, fy_, sx_, sy_

    def _poly(self, surf, pts, col, x, y, grow=0.09, outline=True, width=0):
        """Koyu dış hatlı çokgen."""
        if outline and grow > 0:
            pygame.draw.polygon(surf, OUTLINE,
                                [(px + (px - x) * grow, py + (py - y) * grow) for px, py in pts])
        pygame.draw.polygon(surf, col, pts, width)

    def _limb(self, surf, pts, col, w, outline=True):
        """Kalın, dış hatlı uzuv çizgisi (bacak, boyun, kuyruk)."""
        if outline:
            pygame.draw.lines(surf, OUTLINE, False, pts, int(w + 4))
        pygame.draw.lines(surf, col, False, pts, int(w))

    def _boss_eyes(self, surf, P, r, t, n=2, spread=0.30, fwd=0.50, sz=0.15,
                   col=(255, 248, 230), glow=(255, 70, 50)):
        """Patronun gözleri: dışı açık, içi parlayan bir renk + hafif ışıma."""
        offs = [0.0] if n == 1 else [(i - (n - 1) / 2) * 2 * spread for i in range(n)]
        for o in offs:
            ex, ey = P(fwd, o)
            if glow:
                add_glow(surf, ex, ey, r * sz * 3.2, glow, 0.42 + 0.16 * math.sin(t * 5))
            pygame.draw.circle(surf, col, (int(ex), int(ey)), max(2, int(r * sz)))
            pygame.draw.circle(surf, glow or RED, (int(ex), int(ey)), max(1, int(r * sz * 0.52)))

    def _draw_vanished(self, surf, x, y, r, t):
        """GÖLGE PERDESİ: gövde yok, yalnız havadaki titreşim ve puslu gözler."""
        P, fx_, fy_, sx_, sy_ = self._mapper(x, y, r)
        k = 0.35 + 0.25 * math.sin(t * 7)
        add_glow(surf, x, y, r * 1.7, self.color, 0.10 + 0.05 * k)
        for i in range(14):
            a0 = i * math.tau / 14
            a1 = a0 + math.tau / 26
            jit = 1.0 + 0.10 * math.sin(t * 9 + i)
            pygame.draw.line(surf, scale_col(self.color, 0.75 + 0.25 * k),
                             (x + math.cos(a0) * r * jit, y + math.sin(a0) * r * jit),
                             (x + math.cos(a1) * r * jit, y + math.sin(a1) * r * jit), 2)
        for i in range(5):
            a = t * 2.0 + i * math.tau / 5
            blit_disc(surf, x + math.cos(a) * r * 1.1, y + math.sin(a) * r * 1.1,
                      2.4, lighten(self.color, 0.5), 120)
        self._boss_eyes(surf, P, r, t, n=2, spread=0.20, fwd=0.32, sz=0.11,
                        col=(240, 220, 255), glow=(190, 110, 245))

    # ---------------- SAVAŞ LORDU ----------------
    def _draw_warlord(self, surf, x, y, r, col, t):
        """Zırhlı savaş lordu: dalgalanan pelerin, omuzluklar, boynuzlu miğfer,
        iki elinde savaş baltası. ATEŞLİ ÇELİK taşıyorsa baltaları kor gibi yanar."""
        P, fx_, fy_, sx_, sy_ = self._mapper(x, y, r)
        step = math.sin(self.gait) * 0.13
        dark = scale_col(col, 0.58)
        lite = lighten(col, 0.30)
        steel = (198, 205, 224)
        # Pelerin kasten gövdeden ÇOK daha koyu: aksi hâlde ikisi tek bir
        # kırmızı lekeye dönüşüyor ve zırh okunmuyordu.
        cape_col = (74, 18, 18) if not self.hellish else (84, 24, 12)

        # --- pelerin: arkaya doğru genişleyen, kenarları dalgalanan kumaş ---
        cape = [P(0.06, 0.62), P(-0.28, 0.94)]
        for i in range(5):
            k = i / 4.0
            wob = math.sin(t * 2.4 + i * 1.1) * 0.16
            cape.append(P(-1.12 - 0.30 * math.sin(k * math.pi), (0.5 - k) * 1.72 + wob))
        cape += [P(-0.28, -0.94), P(0.06, -0.62)]
        self._poly(surf, cape, cape_col, x, y, grow=0.04)
        pygame.draw.polygon(surf, (66, 14, 14), cape, 2)

        # --- baltalar: omuz hizasından öne uzanan sap + geniş ağız ---
        for sgn in (-1, 1):
            sw = step * sgn
            grip = P(0.10 + sw, 1.00 * sgn)
            tip = P(1.05 + sw, 1.12 * sgn)
            pygame.draw.line(surf, OUTLINE, grip, tip, max(5, int(r * 0.15)))
            pygame.draw.line(surf, (96, 66, 42), grip, tip, max(3, int(r * 0.10)))
            blade = [(tip[0] + (fx_ * 0.34 + sx_ * 0.02 * sgn) * r,
                      tip[1] + (fy_ * 0.34 + sy_ * 0.02 * sgn) * r),
                     (tip[0] + (fx_ * 0.16 + sx_ * 0.52 * sgn) * r,
                      tip[1] + (fy_ * 0.16 + sy_ * 0.52 * sgn) * r),
                     (tip[0] + (-fx_ * 0.30 + sx_ * 0.44 * sgn) * r,
                      tip[1] + (-fy_ * 0.30 + sy_ * 0.44 * sgn) * r),
                     (tip[0] - fx_ * 0.16 * r, tip[1] - fy_ * 0.16 * r)]
            self._poly(surf, blade, steel, x, y, grow=0.03)
            pygame.draw.polygon(surf, (110, 118, 140), blade, 2)
            if self.trait.get("hellfire"):
                add_glow(surf, tip[0], tip[1], r * 0.55, (255, 150, 60), 0.5)

        # --- gövde: omuzları geniş, beli dar bir zırh ---
        body = [P(0.62, 0.36), P(0.30, 0.82), P(-0.46, 0.92),
                P(-0.86, 0.46), P(-0.86, -0.46), P(-0.46, -0.92),
                P(0.30, -0.82), P(0.62, -0.36)]
        self._poly(surf, body, col, x, y, grow=0.09)
        pygame.draw.polygon(surf, dark, body, 2)
        # göğüs plakası + orta kuşak
        chest = [P(0.46, 0.0), P(0.05, 0.46), P(-0.44, 0.0), P(0.05, -0.46)]
        self._poly(surf, chest, lite, x, y, grow=0.0, outline=False)
        pygame.draw.polygon(surf, dark, chest, 2)
        pygame.draw.line(surf, dark, P(0.30, 0.0), P(-0.50, 0.0), 2)

        # --- omuzluklar ---
        for sgn in (-1, 1):
            pl = [P(-0.34, 0.66 * sgn), P(-0.18, 1.14 * sgn),
                  P(0.34, 1.06 * sgn), P(0.40, 0.62 * sgn)]
            self._poly(surf, pl, dark, x, y, grow=0.04)
            pygame.draw.polygon(surf, steel, pl, 2)
            for i in range(3):
                pygame.draw.circle(surf, steel,
                                   [int(v) for v in P(-0.12 + i * 0.22, (0.86 + i * 0.02) * sgn)],
                                   max(1, int(r * 0.055)))

        # --- miğfer: boynuzlu, vizörlü ---
        hx, hy = P(0.46, 0.0)
        pygame.draw.circle(surf, OUTLINE, (int(hx), int(hy)), int(r * 0.42))
        pygame.draw.circle(surf, dark, (int(hx), int(hy)), int(r * 0.36))
        pygame.draw.circle(surf, steel, (int(hx), int(hy)), int(r * 0.36), 2)
        for sgn in (-1, 1):
            b0 = P(0.40, 0.30 * sgn)
            b1 = P(0.02, 0.86 * sgn)
            b2 = P(-0.28, 0.74 * sgn)
            pygame.draw.lines(surf, OUTLINE, False, [b0, b1, b2], max(5, int(r * 0.15)))
            pygame.draw.lines(surf, (240, 232, 214), False, [b0, b1, b2], max(3, int(r * 0.09)))
        pygame.draw.line(surf, (24, 18, 22), P(0.62, -0.22), P(0.62, 0.22), max(3, int(r * 0.13)))
        eye_glow = (255, 140, 60) if self.trait.get("hellfire") else (255, 90, 66)
        self._boss_eyes(surf, P, r, t, n=2, spread=0.11, fwd=0.62, sz=0.075, glow=eye_glow)

    # ---------------- GÖLGE CADISI ----------------
    def _draw_witch(self, surf, x, y, r, col, t):
        """Kukuletalı cadı: yerden yükselen yırtık cübbe, kollarında asa,
        çevresinde dönen mühürler. Süzülerek hareket eder (yere basmaz)."""
        P, fx_, fy_, sx_, sy_ = self._mapper(x, y, r)
        dark = scale_col(col, 0.52)
        lite = lighten(col, 0.38)
        y = y + math.sin(t * 1.8) * r * 0.10
        P, fx_, fy_, sx_, sy_ = self._mapper(x, y, r)

        # --- dönen mühürler (elips yörünge: yere yatık dursun) ---
        for i in range(5):
            a = t * 1.1 + i * math.tau / 5
            gx = x + math.cos(a) * r * 1.62
            gy = y + math.sin(a) * r * 1.62 * 0.55 + r * 0.30
            add_glow(surf, gx, gy, r * 0.30, lite, 0.35)
            rune = rot_pts([(0, -r * 0.16), (r * 0.12, 0), (0, r * 0.16), (-r * 0.12, 0)],
                           a * 2.0, gx, gy)
            pygame.draw.polygon(surf, lite, rune)
            pygame.draw.polygon(surf, (250, 238, 255), rune, 1)

        # --- cübbe: omuzdan arkaya doğru açılan, etekleri yırtık ---
        robe = [P(0.46, 0.30), P(0.30, 0.62)]
        for i in range(7):
            k = i / 6.0
            wob = math.sin(t * 3.4 + i * 1.2) * 0.14
            jag = 0.16 if i % 2 else 0.0
            robe.append(P(-1.05 - 0.28 * math.sin(k * math.pi) - jag,
                          (0.5 - k) * 2.20 + wob))
        robe += [P(0.30, -0.62), P(0.46, -0.30)]
        self._poly(surf, robe, col, x, y, grow=0.05)
        pygame.draw.polygon(surf, dark, robe, 2)
        # cübbenin ön yarığı
        pygame.draw.line(surf, dark, P(0.30, 0.0), P(-0.95, 0.0), 2)

        # --- kollar (iki yana uzanan geniş yenler) ---
        for sgn in (-1, 1):
            sleeve = [P(0.16, 0.42 * sgn), P(0.34, 0.96 * sgn),
                      P(-0.10, 1.12 * sgn), P(-0.30, 0.52 * sgn)]
            self._poly(surf, sleeve, dark, x, y, grow=0.04)

        # --- asa: sağ elde, ucunda büyü küresi ---
        grip = P(0.20, 1.02)
        top = (grip[0] + fx_ * r * 0.30 - abs(r) * 0.0, grip[1] - r * 1.35)
        pygame.draw.line(surf, OUTLINE, (grip[0], grip[1] + r * 0.30), top, max(5, int(r * 0.13)))
        pygame.draw.line(surf, (86, 60, 46), (grip[0], grip[1] + r * 0.30), top, max(3, int(r * 0.08)))
        orb_k = 0.55 + 0.25 * math.sin(t * 4)
        add_glow(surf, top[0], top[1], r * 0.80, lite, 0.45 + 0.30 * orb_k)
        pygame.draw.circle(surf, OUTLINE, (int(top[0]), int(top[1])), int(r * 0.27))
        pygame.draw.circle(surf, lite, (int(top[0]), int(top[1])), int(r * 0.22))
        pygame.draw.circle(surf, (252, 242, 255),
                           (int(top[0] - r * 0.07), int(top[1] - r * 0.07)), max(1, int(r * 0.08)))
        for i in range(3):
            a = t * 3.0 + i * math.tau / 3
            blit_disc(surf, top[0] + math.cos(a) * r * 0.36, top[1] + math.sin(a) * r * 0.36,
                      2.4, (250, 230, 255), 170)

        # --- kukuleta: sivri tepeli, içi kapkaranlık ---
        hood = [P(0.74, 0.0), P(0.44, 0.50), P(-0.26, 0.60),
                P(-0.62, 0.0), P(-0.26, -0.60), P(0.44, -0.50)]
        self._poly(surf, hood, dark, x, y, grow=0.05)
        pygame.draw.polygon(surf, scale_col(dark, 0.7), hood, 2)
        inner = [P(0.56, 0.0), P(0.30, 0.30), P(-0.12, 0.34),
                 P(-0.26, 0.0), P(-0.12, -0.34), P(0.30, -0.30)]
        pygame.draw.polygon(surf, (13, 9, 20), inner)
        self._boss_eyes(surf, P, r, t, n=2, spread=0.13, fwd=0.26, sz=0.085,
                        col=(246, 228, 255), glow=(208, 124, 255))

    # ---------------- KOLOS ----------------
    def _draw_colossus(self, surf, x, y, r, col, t):
        """Taş kolos: düzensiz kaya plakalardan örülü dev gövde, iki ağır yumruk,
        göğsünde nabız gibi atan akkor çekirdek."""
        P, fx_, fy_, sx_, sy_ = self._mapper(x, y, r)
        dark = scale_col(col, 0.55)
        lite = lighten(col, 0.26)
        core = (255, 140, 60) if self.hellish else (120, 200, 255)
        step = math.sin(self.gait) * 0.14
        pulse = 0.55 + 0.45 * math.sin(t * 3.4)

        # --- bacaklar: kısa, kalın taş sütunlar ---
        for sgn in (-1, 1):
            fo = step * sgn
            self._limb(surf, [P(-0.50, 0.46 * sgn), P(-0.95 + fo, 0.56 * sgn),
                              P(-1.15 + fo, 0.50 * sgn)], dark, max(8, int(r * 0.30)))
            foot = [P(-1.02 + fo, 0.24 * sgn), P(-1.36 + fo, 0.34 * sgn),
                    P(-1.30 + fo, 0.78 * sgn), P(-0.98 + fo, 0.70 * sgn)]
            self._poly(surf, foot, dark, x, y, grow=0.04)

        # --- kollar + yumruklar (öne uzanmış) ---
        for sgn in (-1, 1):
            fo = -step * sgn
            self._limb(surf, [P(0.20, 0.90 * sgn), P(0.55 + fo, 1.14 * sgn)],
                       dark, max(7, int(r * 0.26)))
            fist_c = P(0.78 + fo, 1.22 * sgn)
            pygame.draw.circle(surf, OUTLINE, (int(fist_c[0]), int(fist_c[1])), int(r * 0.46))
            pygame.draw.circle(surf, col, (int(fist_c[0]), int(fist_c[1])), int(r * 0.40))
            pygame.draw.circle(surf, lite,
                               (int(fist_c[0] - fx_ * r * 0.10), int(fist_c[1] - fy_ * r * 0.10)),
                               max(2, int(r * 0.15)))
            for i in range(3):
                pygame.draw.line(surf, dark,
                                 P(0.90 + fo, (1.02 + i * 0.14) * sgn),
                                 P(1.06 + fo, (1.00 + i * 0.14) * sgn), 2)

        # --- gövde: üst üste binmiş düzensiz kaya plakalar ---
        plates = (
            (-0.62, 1.02, 0.42),   # kalça
            (0.02, 1.14, 0.46),    # gövde
            (0.52, 0.92, 0.34),    # göğüs
        )
        for i, (fwd, half_w, half_h) in enumerate(plates):
            pts = []
            n = 7
            for j in range(n):
                a = j * math.tau / n + 0.35 + i * 0.4
                jitter = 1.0 + 0.16 * math.sin(j * 2.7 + i)
                pts.append(P(fwd + math.cos(a) * half_h * jitter,
                             math.sin(a) * half_w * jitter))
            self._poly(surf, pts, col if i != 1 else lighten(col, 0.08), x, y, grow=0.05)
            pygame.draw.polygon(surf, dark, pts, 2)

        # --- akkor çekirdek ---
        cx, cy = P(0.18, 0.0)
        add_glow(surf, cx, cy, r * (0.85 + 0.28 * pulse), core, 0.50 + 0.28 * pulse)
        pygame.draw.circle(surf, (20, 16, 20), (int(cx), int(cy)), int(r * 0.30))
        pygame.draw.circle(surf, core, (int(cx), int(cy)), int(r * (0.15 + 0.07 * pulse)))
        for i in range(6):
            a = i * math.tau / 6 + 0.3
            pygame.draw.line(surf, scale_col(core, 0.55 + 0.45 * pulse),
                             (cx + math.cos(a) * r * 0.26, cy + math.sin(a) * r * 0.26),
                             (cx + math.cos(a) * r * (0.70 + 0.25 * math.sin(i * 1.7)),
                              cy + math.sin(a) * r * (0.70 + 0.25 * math.sin(i * 1.7))), 2)

        # --- kafa: omuzların arasına gömülü küçük taş blok ---
        hd = [P(1.10, 0.0), P(0.86, 0.38), P(0.50, 0.30), P(0.50, -0.30), P(0.86, -0.38)]
        self._poly(surf, hd, dark, x, y, grow=0.05)
        pygame.draw.polygon(surf, scale_col(dark, 0.75), hd, 2)
        self._boss_eyes(surf, P, r, t, n=2, spread=0.13, fwd=0.82, sz=0.085,
                        col=(255, 250, 240), glow=core)

    # ---------------- ORAK ----------------
    def _draw_reaper(self, surf, x, y, r, col, t):
        """Ruh toplayıcı: ayağı yere değmeyen paçavra pelerin, boş kukuleta,
        iki eliyle savurduğu dev tırpan. Ardında ruh izi bırakır."""
        P, fx_, fy_, sx_, sy_ = self._mapper(x, y, r)
        dark = scale_col(col, 0.46)
        lite = lighten(col, 0.42)
        y = y + math.sin(t * 2.4) * r * 0.13
        P, fx_, fy_, sx_, sy_ = self._mapper(x, y, r)

        # --- ruh izi ---
        for i in range(4):
            k = 1.0 - i / 4.0
            gx, gy = P(-0.55 - i * 0.45, 0.0)
            blit_disc(surf, gx, gy, r * 0.40 * k, col, int(64 * k))

        # --- tırpan: uzun sap + kavisli ağız (yavaşça salınır) ---
        ang0 = math.sin(t * 0.9) * 0.7 + self.wobble * 0.10
        base = P(0.10, 0.62)
        sh_end = (base[0] + math.cos(ang0) * r * 2.05, base[1] + math.sin(ang0) * r * 2.05)
        sh_start = (base[0] - math.cos(ang0) * r * 0.85, base[1] - math.sin(ang0) * r * 0.85)
        pygame.draw.line(surf, OUTLINE, sh_start, sh_end, max(6, int(r * 0.15)))
        pygame.draw.line(surf, (62, 50, 46), sh_start, sh_end, max(4, int(r * 0.10)))
        blade = pygame.Rect(0, 0, int(r * 1.9), int(r * 1.9))
        blade.center = (int(sh_end[0] - math.cos(ang0) * r * 0.66),
                        int(sh_end[1] - math.sin(ang0) * r * 0.66))
        pygame.draw.arc(surf, OUTLINE, blade.inflate(8, 8), ang0 - 0.25, ang0 + math.pi * 0.70, 8)
        pygame.draw.arc(surf, (228, 238, 246), blade, ang0 - 0.25, ang0 + math.pi * 0.70, 4)
        add_glow(surf, sh_end[0], sh_end[1], r * 0.55, lite, 0.45)

        # --- pelerin: omuzdan aşağı açılan, etekleri şerit şerit yırtık ---
        cloak = [P(0.34, 0.54), P(0.10, 0.92)]
        for i in range(9):
            k = i / 8.0
            wob = math.sin(t * 4.2 + i * 1.35) * 0.16
            depth = -1.10 - 0.45 * math.sin(k * math.pi) - (0.22 if i % 2 else 0.0)
            cloak.append(P(depth, (0.5 - k) * 2.05 + wob))
        cloak += [P(0.10, -0.92), P(0.34, -0.54)]
        self._poly(surf, cloak, col, x, y, grow=0.05)
        pygame.draw.polygon(surf, dark, cloak, 2)

        # --- iskelet eller (tırpanı kavrar) ---
        for grip_f, grip_s in ((0.16, 0.62), (-0.10, 0.34)):
            gx, gy = P(grip_f, grip_s)
            pygame.draw.circle(surf, OUTLINE, (int(gx), int(gy)), max(3, int(r * 0.16)))
            pygame.draw.circle(surf, (228, 232, 226), (int(gx), int(gy)), max(2, int(r * 0.12)))

        # --- kukuleta: derin, içi boş ---
        hood = [P(0.86, 0.0), P(0.58, 0.46), P(-0.06, 0.54),
                P(-0.30, 0.0), P(-0.06, -0.54), P(0.58, -0.46)]
        self._poly(surf, hood, dark, x, y, grow=0.05)
        pygame.draw.polygon(surf, scale_col(dark, 0.7), hood, 2)
        inner = [P(0.64, 0.0), P(0.42, 0.28), P(0.02, 0.30),
                 P(-0.08, 0.0), P(0.02, -0.30), P(0.42, -0.28)]
        pygame.draw.polygon(surf, (9, 13, 15), inner)
        self._boss_eyes(surf, P, r, t, n=2, spread=0.12, fwd=0.34, sz=0.08,
                        col=(226, 255, 250), glow=lite)

    # ---------------- KOVAN ANA ----------------
    def _draw_hive(self, surf, x, y, r, col, t):
        """Kovan anası: titreyen dört kanat, bölmeli karın, zehir iğnesi,
        altı eklemli bacak ve çeneli kafa. Çevresinde yavruları dolanır."""
        P, fx_, fy_, sx_, sy_ = self._mapper(x, y, r)
        dark = scale_col(col, 0.58)
        lite = lighten(col, 0.30)
        venom = (172, 232, 92)

        # --- bacaklar (altı adet, iki eklemli) ---
        for sgn in (-1, 1):
            for i in range(3):
                root_f = 0.34 - i * 0.34
                sw = math.sin(self.gait * 1.7 + i * 1.2 + (0 if sgn > 0 else 1.7)) * 0.16
                a = P(root_f, 0.52 * sgn)
                b = P(root_f + 0.24 + sw, 1.12 * sgn)
                c = P(root_f - 0.18 + sw, 1.60 * sgn)
                self._limb(surf, [a, b, c], dark, max(3, int(r * 0.09)))

        # --- kanatlar: ince, uzun, yarı saydam (çırpınca bulanıklaşır) ---
        flap = 0.16 * math.sin(t * 18)
        pad = int(r * 3.2)
        wsurf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        wcx, wcy = pad, pad

        def W(f, s):
            return (wcx + fx_ * r * f + sx_ * r * s, wcy + fy_ * r * f + sy_ * r * s)

        for sgn in (-1, 1):
            for j, (reach, back, alpha) in enumerate(((1.95, -1.35, 78), (1.55, -2.05, 62))):
                tipo = flap * (1 if j == 0 else -1)
                wing = [W(-0.15, 0.30 * sgn),
                        W(0.25 + tipo, (reach * 0.55) * sgn),
                        W(back * 0.42 + tipo, reach * sgn),
                        W(back, (reach * 0.42) * sgn)]
                pygame.draw.polygon(wsurf, (226, 240, 255, alpha), wing)
                pygame.draw.polygon(wsurf, (255, 255, 255, alpha + 50), wing, 1)
                pygame.draw.line(wsurf, (255, 255, 255, alpha + 40),
                                 W(-0.10, 0.30 * sgn), W(back * 0.42 + tipo, reach * sgn), 1)
        surf.blit(wsurf, (int(x - pad), int(y - pad)))

        # --- karın: arkaya doğru küçülen bölmeler + zehir iğnesi ---
        for i in range(3):
            k = 1.0 - i * 0.20
            ax, ay = P(-0.78 - i * 0.56, 0.0)
            pygame.draw.circle(surf, OUTLINE, (int(ax), int(ay)), int(r * 0.62 * k + 2))
            pygame.draw.circle(surf, dark if i % 2 else col, (int(ax), int(ay)), int(r * 0.62 * k))
            pygame.draw.circle(surf, scale_col(col, 0.75), (int(ax), int(ay)), int(r * 0.62 * k), 2)
        sting = [P(-1.92, 0.20), P(-2.52, 0.0), P(-1.92, -0.20)]
        self._poly(surf, sting, venom, x, y, grow=0.03)
        add_glow(surf, *P(-2.45, 0.0), r * 0.40, venom, 0.5)

        # --- göğüs ---
        pygame.draw.circle(surf, OUTLINE, (int(x), int(y)), int(r * 0.80))
        pygame.draw.circle(surf, col, (int(x), int(y)), int(r * 0.74))
        pygame.draw.circle(surf, lite, [int(v) for v in P(-0.16, 0.0)], int(r * 0.34))

        # --- kafa + çeneler ---
        hx, hy = P(0.94, 0.0)
        pygame.draw.circle(surf, OUTLINE, (int(hx), int(hy)), int(r * 0.44))
        pygame.draw.circle(surf, dark, (int(hx), int(hy)), int(r * 0.38))
        chomp = 0.5 + 0.5 * math.sin(t * 6)
        for sgn in (-1, 1):
            m0 = P(1.18, 0.24 * sgn)
            m1 = P(1.62, (0.10 + 0.26 * chomp) * sgn)
            pygame.draw.line(surf, OUTLINE, m0, m1, max(4, int(r * 0.13)))
            pygame.draw.line(surf, (240, 230, 204), m0, m1, max(2, int(r * 0.08)))
        # duyargalar
        for sgn in (-1, 1):
            self._limb(surf, [P(1.10, 0.20 * sgn), P(1.50, 0.62 * sgn), P(1.40, 1.02 * sgn)],
                       (60, 48, 30), 3, outline=False)
        self._boss_eyes(surf, P, r, t, n=2, spread=0.15, fwd=1.02, sz=0.10,
                        col=(255, 252, 220), glow=venom)

        # --- çevresinde dolanan yavrular ---
        for i in range(4):
            a = t * 2.0 + i * math.tau / 4
            lx = x + math.cos(a) * r * 1.80
            ly = y + math.sin(a) * r * 1.80 * 0.72
            pygame.draw.circle(surf, OUTLINE, (int(lx), int(ly)), 6)
            pygame.draw.circle(surf, lite, (int(lx), int(ly)), 4)

    # ---------------- EJDERHA ----------------
    def _draw_dragon(self, surf, x, y, r, col, t):
        """Cehennem ejderhası: kıvrılan dikenli kuyruk, zarlı iki kanat,
        uzun boyun, dişli çene ve ağzında biriken alev.

        Uçarken (fly_t) gövde yukarı kalkar ve kanatlar tamamen açılır —
        dalışa geçtiği bir bakışta anlaşılır.
        """
        flying = self.fly_t > 0
        lift = (r * 0.55 if flying else 0.0) + math.sin(t * 2.6) * r * (0.16 if flying else 0.07)
        y = y - lift
        P, fx_, fy_, sx_, sy_ = self._mapper(x, y, r)
        dark = scale_col(col, 0.55)
        lite = lighten(col, 0.28)
        belly = (240, 192, 122)
        fire = (255, 150, 55)

        # --- kuyruk: arkaya kıvrılan, ucunda ok başı ---
        tail = []
        for i in range(6):
            k = i / 5.0
            curl = math.sin(t * 2.0 + i * 0.85) * 0.34 * k
            tail.append(P(-0.70 - k * 2.20, curl))
        self._limb(surf, tail, col, max(5, int(r * 0.20)))
        td = (tail[-1][0] - tail[-2][0], tail[-1][1] - tail[-2][1])
        tl = math.hypot(*td) or 1.0
        td = (td[0] / tl, td[1] / tl)
        self._poly(surf, [(tail[-1][0] + td[0] * r * 0.50, tail[-1][1] + td[1] * r * 0.50),
                          (tail[-1][0] - td[1] * r * 0.30, tail[-1][1] + td[0] * r * 0.30),
                          (tail[-1][0] + td[1] * r * 0.30, tail[-1][1] - td[0] * r * 0.30)],
                   dark, x, y, grow=0.03)

        # --- kanatlar: kemikli, tırtıklı zar ---
        flap = (0.86 if flying else 0.58) + 0.22 * math.sin(t * (7.0 if flying else 3.2))
        for sgn in (-1, 1):
            sh = P(-0.10, 0.36 * sgn)
            elbow = P(0.46, (1.06 * flap + 0.30) * sgn)
            tip = P(-0.20, (2.30 * flap + 0.45) * sgn)
            n1 = P(-0.72, (1.78 * flap + 0.32) * sgn)
            n2 = P(-1.02, (1.20 * flap + 0.26) * sgn)
            n3 = P(-1.14, (0.56 * flap + 0.20) * sgn)
            memb = [sh, elbow, tip,
                    P(-0.52, (2.00 * flap + 0.36) * sgn), n1,
                    P(-0.92, (1.46 * flap + 0.28) * sgn), n2,
                    P(-1.18, (0.86 * flap + 0.22) * sgn), n3]
            self._poly(surf, memb, scale_col(col, 0.70), x, y, grow=0.035)
            pygame.draw.polygon(surf, dark, memb, 2)
            for f in (elbow, tip, n1, n2, n3):
                pygame.draw.line(surf, lighten(dark, 0.30), sh, f, max(2, int(r * 0.06)))

        # --- gövde ---
        body = [P(0.90, 0.0), P(0.60, 0.56), P(-0.10, 0.74),
                P(-0.84, 0.44), P(-0.84, -0.44), P(-0.10, -0.74), P(0.60, -0.56)]
        self._poly(surf, body, col, x, y, grow=0.08)
        pygame.draw.polygon(surf, dark, body, 2)
        # karın pulları
        for i in range(4):
            f = 0.50 - i * 0.32
            w = 0.46 - i * 0.05
            pygame.draw.line(surf, belly, P(f, -w), P(f, w), max(2, int(r * 0.08)))
        # sırt dikenleri
        for i in range(4):
            b_f = -0.15 - i * 0.40
            self._poly(surf, [P(b_f, 0.16), P(b_f - 0.38, 0.0), P(b_f, -0.16)],
                       (250, 228, 192), x, y, grow=0.03)

        # --- arka pençeler ---
        for sgn in (-1, 1):
            self._limb(surf, [P(-0.40, 0.60 * sgn), P(-0.78, 0.96 * sgn)],
                       dark, max(3, int(r * 0.12)))
            for k in (-1, 0, 1):
                pygame.draw.line(surf, (248, 240, 224), P(-0.78, 0.96 * sgn),
                                 P(-1.02 + k * 0.10, (1.16 + abs(k) * 0.04) * sgn), 2)

        # --- boyun + kafa ---
        neck = [P(0.60, 0.0), P(1.05, 0.0), P(1.45, 0.0)]
        self._limb(surf, neck, col, max(6, int(r * 0.28)))
        hx, hy = P(1.72, 0.0)
        head = [P(2.22, 0.0), P(1.86, 0.30), P(1.40, 0.34), P(1.30, 0.0),
                P(1.40, -0.34), P(1.86, -0.30)]
        self._poly(surf, head, lighten(col, 0.08), x, y, grow=0.05)
        pygame.draw.polygon(surf, dark, head, 2)
        # boynuzlar
        for sgn in (-1, 1):
            self._limb(surf, [P(1.42, 0.26 * sgn), P(1.02, 0.56 * sgn), P(0.72, 0.52 * sgn)],
                       (242, 230, 208), max(3, int(r * 0.10)))
        # çene + dişler
        jaw = 0.12 + 0.12 * (0.5 + 0.5 * math.sin(t * 3.2))
        self._poly(surf, [P(2.20, 0.0), P(1.82, 0.22), P(1.76, 0.0), P(1.82, -0.22)],
                   (42, 14, 12), x, y, grow=0.0, outline=False)
        for k in (-1, 1):
            pygame.draw.line(surf, (255, 250, 240), P(1.92, 0.16 * k), P(2.16, 0.06 * k), 2)
        pygame.draw.line(surf, (255, 250, 240), P(1.90, 0.0), P(2.14 + jaw, 0.0), 2)
        # ağızda biriken alev
        glow_k = 0.45 + 0.35 * math.sin(t * 5)
        if self.telegraph and self.telegraph[0] == "breath":
            glow_k = 1.0
        mx_, my_ = P(2.20, 0.0)
        add_glow(surf, mx_, my_, r * (0.45 + 0.50 * glow_k), fire, 0.30 + 0.50 * glow_k)
        for i in range(3):
            ph = (t * 1.6 + i * 0.33) % 1.0
            ex_, ey_ = P(2.20 + ph * 0.55, random.uniform(-0.10, 0.10))
            blit_disc(surf, ex_, ey_ - ph * r * 0.45, max(1.0, 4.0 * (1 - ph)),
                      (255, 205, 110), int(200 * (1 - ph)))
        self._boss_eyes(surf, P, r, t, n=2, spread=0.14, fwd=1.66, sz=0.09,
                        col=(255, 248, 214), glow=(255, 170, 60))

    def draw(self, surf, t):
        scale = ease_out_cubic(self.spawn_t / 0.6) if self.spawn_t < 0.6 else 1.0
        r = self.radius * scale
        x, y = self.x, self.y
        col = WHITE if self.hit_flash > 0 else self.color
        hidden = self.is_hidden()
        # GÖLGE PERDESİ açıkken gölge, ışıma ve alev çemberi de kaybolur —
        # yoksa "görünmez" patron ışıldayan bir hedef tahtası olurdu.
        if not hidden:
            surf.blit(shadow_sprite(int(r * 2.4)), (int(x - r * 1.2), int(y + r * 0.6)))
            add_glow(surf, x, y, r * 2.2, self.color, 0.4 + 0.15 * math.sin(t * 3))
        if self.enraged and not hidden:
            add_glow(surf, x, y, r * 1.6, (255, 70, 50), 0.35)
        if getattr(self, "hellish", False) and not hidden:
            # ayağının dibinde dönen alev çemberi + yukarı süzülen korlar
            add_glow(surf, x, y, r * 3.0, (255, 130, 50), 0.22 + 0.08 * math.sin(t * 2.4))
            ring = pygame.Rect(0, 0, int(r * 2.9), int(r * 1.5))
            ring.center = (int(x), int(y + r * 0.55))
            pygame.draw.ellipse(surf, (255, 140, 60), ring, 3)
            for i in range(9):
                a = t * 1.3 + i * math.tau / 9
                fx0 = x + math.cos(a) * r * 1.45
                fy0 = y + r * 0.55 + math.sin(a) * r * 0.75
                blit_disc(surf, fx0, fy0, 3.4, (255, 190, 90), 190)
            for i in range(6):
                ph = (t * 0.7 + i * 0.17) % 1.0
                ex = x + math.sin(t * 1.6 + i * 2.1) * r * 1.0
                ey = y - r * 0.4 - ph * r * 2.2
                blit_disc(surf, ex, ey, max(1.0, 3.6 * (1.0 - ph)), (255, 170, 70),
                          int(210 * (1.0 - ph)))

        # --- GÖVDE ---
        # Her patronun kendi çizimi var. GÖLGE PERDESİ açıkken gövde hiç
        # çizilmez; yalnızca havadaki titreşim ve puslu gözler görünür.
        if hidden:
            self._draw_vanished(surf, x, y, r, t)
        else:
            drawer = {
                "warlord": self._draw_warlord,
                "witch": self._draw_witch,
                "colossus": self._draw_colossus,
                "reaper": self._draw_reaper,
                "hive": self._draw_hive,
                "dragon": self._draw_dragon,
            }.get(self.kind, self._draw_warlord)
            drawer(surf, x, y, r, col, t)

        if self.telegraph:
            kind, a, b, c, timer, total = self.telegraph
            k = 1 - clamp(timer / total, 0, 1)
            if kind == "beam":
                angs = a if isinstance(a, (list, tuple)) else [a]
                alpha = int(120 + 100 * math.sin(k * 20))
                s = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
                for ang in angs:
                    ex, ey = x + math.cos(ang) * 900, y + math.sin(ang) * 900
                    pygame.draw.line(s, (255, 80, 70, alpha), (x, y), (ex, ey), 5)
                surf.blit(s, (0, 0))
            elif kind == "hazard_ring":
                n = 11 if self.enraged else 8
                for i in range(n):
                    ang = i * math.tau / n
                    hx, hy = x + math.cos(ang) * 150, y + math.sin(ang) * 150
                    hx = clamp(hx, ARENA_RECT.left + 20, ARENA_RECT.right - 20)
                    hy = clamp(hy, ARENA_RECT.top + 20, ARENA_RECT.bottom - 20)
                    blit_disc(surf, hx, hy, 30 * k, (255, 70, 60), 90)
            elif kind in ("slam", "scythe"):
                blit_disc(surf, a, b, c * k, (255, 70, 60), 80)
                pygame.draw.circle(surf, (255, 120, 90), (int(a), int(b)), int(c * k), 2)
            elif kind == "spore":
                for i in range(6 if self.enraged else 4):
                    ang = i * math.tau / (6 if self.enraged else 4)
                    hx = clamp(a + math.cos(ang) * 90, ARENA_RECT.left + 20, ARENA_RECT.right - 20)
                    hy = clamp(b + math.sin(ang) * 90, ARENA_RECT.top + 20, ARENA_RECT.bottom - 20)
                    blit_disc(surf, hx, hy, 28 * k, (230, 190, 70), 85)
            elif kind == "barrage":
                # YAĞMUR: mermilerin çıkacağı yelpaze koridoru önceden gösterilir
                n = 7 + self.boss_index * 2 + (3 if self.enraged else 0)
                col = (210, 120, 250) if self.kind == "witch" else (245, 205, 90)
                s = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
                for i in range(n):
                    ang = a + (i - (n - 1) / 2) * (0.62 / max(1, n - 1))
                    ex, ey = x + math.cos(ang) * 900, y + math.sin(ang) * 900
                    pygame.draw.line(s, (*col, int(45 + 95 * k)), (x, y), (ex, ey), 3)
                surf.blit(s, (0, 0))
                add_glow(surf, x, y, 40 + 34 * k, col, 0.35 + 0.35 * k)
            elif kind == "ring_player":
                # oyuncunun çevresine kapanan lanet çemberi
                n = self._ring_count()
                pygame.draw.circle(surf, (210, 120, 250), (int(a), int(b)), int(c), 2)
                for i in range(n):
                    ang = i * math.tau / n
                    hx = clamp(a + math.cos(ang) * c, ARENA_RECT.left + 20, ARENA_RECT.right - 20)
                    hy = clamp(b + math.sin(ang) * c, ARENA_RECT.top + 20, ARENA_RECT.bottom - 20)
                    blit_disc(surf, hx, hy, BOSS_RING_HAZARD_R * 0.56 * k, (230, 90, 220), 92)
                pygame.draw.circle(surf, (255, 170, 255), (int(a), int(b)), max(2, int(6 * k)))
            elif kind == "breath":
                # alev koridoru: patrondan ileri uzanan turuncu huni
                s = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
                spread = 0.30
                for sgn in (-1, 1):
                    ang = a + spread * sgn
                    ex, ey = x + math.cos(ang) * 900, y + math.sin(ang) * 900
                    pygame.draw.line(s, (255, 150, 60, int(70 + 110 * k)), (x, y), (ex, ey), 4)
                ex, ey = x + math.cos(a) * 900, y + math.sin(a) * 900
                pygame.draw.polygon(s, (255, 110, 40, int(30 + 60 * k)), [
                    (x, y),
                    (x + math.cos(a - spread) * 900, y + math.sin(a - spread) * 900),
                    (x + math.cos(a + spread) * 900, y + math.sin(a + spread) * 900)])
                surf.blit(s, (0, 0))
                add_glow(surf, x + math.cos(a) * r * 0.9, y + math.sin(a) * r * 0.9,
                         26 + 34 * k, (255, 180, 80), 0.4 + 0.4 * k)
            elif kind == "firewall":
                # alev duvarı: hedefin üstünden geçen dik perde
                nx, ny = -math.sin(c), math.cos(c)
                n = 7 + self.boss_index
                for i in range(n):
                    off = (i - (n - 1) / 2) * 88
                    hx = clamp(a + nx * off, ARENA_RECT.left + 20, ARENA_RECT.right - 20)
                    hy = clamp(b + ny * off, ARENA_RECT.top + 20, ARENA_RECT.bottom - 20)
                    blit_disc(surf, hx, hy, 30 * k, (255, 130, 50), 95)
            elif kind == "wingburst":
                pygame.draw.circle(surf, (255, 170, 70), (int(a), int(b)), int(c * k), 3)
                for i in range(12):
                    ang = i * math.tau / 12
                    blit_disc(surf, a + math.cos(ang) * c * k, b + math.sin(ang) * c * k,
                              7, (255, 190, 90), 130)
            elif kind == "charge":
                # hücum hattı: patrondan hedefe uzanan geniş kırmızı koridor
                ang = math.atan2(b - y, a - x)
                ex, ey = x + math.cos(ang) * 900, y + math.sin(ang) * 900
                nx, ny = -math.sin(ang), math.cos(ang)
                w2 = self.radius * 1.05
                s = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
                pygame.draw.polygon(s, (255, 90, 60, int(60 + 70 * k)), [
                    (x + nx * w2, y + ny * w2), (ex + nx * w2, ey + ny * w2),
                    (ex - nx * w2, ey - ny * w2), (x - nx * w2, y - ny * w2)])
                surf.blit(s, (0, 0))
                for i in range(3):
                    fx_ = x + math.cos(ang) * (60 + i * 46) * (0.5 + k)
                    fy_ = y + math.sin(ang) * (60 + i * 46) * (0.5 + k)
                    pygame.draw.circle(surf, (255, 150, 90), (int(fx_), int(fy_)), max(2, int(5 * k)), 2)

        # HP bar (üst, isim + imza özelliği + zırh + dövüş süresi ile)
        w = 340
        bx, by = x - w / 2, y - r - 30
        if self.is_hidden():
            # GÖLGE PERDESİ: can çubuğu da kaybolur, yalnızca soluk bir iz kalır.
            hint = pygame.Surface((int(w), 10), pygame.SRCALPHA)
            pygame.draw.rect(hint, (120, 90, 160, 60), hint.get_rect(), border_radius=5)
            surf.blit(hint, (int(bx), int(by)))
            draw_text(surf, "GÖRÜNMEZ", (x, by - 13), 14, (200, 150, 255), bold=True,
                      center=True)
            return
        draw_bar(surf, (bx, by, w, 10), self.hp / self.max_hp, (220, 70, 70))
        # can çaldığında çubuğun üstünde yeşil bir parıltı belirir
        if self.heal_flash > 0:
            k = clamp(self.heal_flash / 0.45, 0, 1)
            gs = pygame.Surface((int(w), 10), pygame.SRCALPHA)
            pygame.draw.rect(gs, (90, 230, 140, int(120 * k)), gs.get_rect(), border_radius=5)
            surf.blit(gs, (int(bx), int(by)))
            draw_text(surf, "CAN ÇALDI", (bx + w + 6, by + 12), 10, (120, 230, 160),
                      bold=True, shadow=False)
        label = self.name
        if self.desperate:
            label += "  ·  ÇARESİZ"
        elif self.enraged:
            label += "  ·  ÖFKELİ"
        draw_text(surf, label, (x, by - 13), 14, GOLD, bold=True, center=True)
        # İmza özelliği rozeti: oyuncu neyle karşı karşıya olduğunu bilsin.
        tr = self.trait
        draw_text(surf, tr["label"], (x, by - 28), 11, tr["color"], bold=True,
                  center=True, shadow=False)
        draw_text(surf, fmt_time(self.fight_time), (bx - 6, by - 4), 11, TEXT_DIM,
                  bold=True, shadow=False, right=True)
        if self.armor > 0.005:
            draw_text(surf, f"ZIRH %{int(self.armor * 100)}", (bx + w + 6, by - 2), 11,
                      (170, 190, 220), bold=True, shadow=False)


def scale_bosses_to_player(bosses, player):
    """Dalgadaki TÜM patronların TOPLAM canını oyuncunun gücüne göre ölçekler.

    Amaç: patron dövüşü, oyuncunun eşya durumundan bağımsız olarak yaklaşık
    BOSS_FIGHT_TARGET saniye sürsün. Eşyalarını dolduran bir oyuncu patronu
    birkaç saniyede eritiyor, yeni başlayan ise dakikalarca uğraşıyordu.

    Ölçek TOPLAM üzerinden hesaplanır: iki patronlu bir dalgada her patrona
    ayrı ayrı tam hedef verilseydi dövüş iki katı sürerdi.
    """
    if not bosses:
        return 1.0
    try:
        est = player.estimated_dps()
    except Exception:
        return 1.0
    base_total = sum(b.max_hp for b in bosses)
    want = est * BOSS_FIGHT_UPTIME * BOSS_FIGHT_TARGET
    scale = clamp(want / max(1.0, base_total), BOSS_HP_SCALE_MIN, BOSS_HP_SCALE_MAX)
    # Can çalma tavanı oyuncunun hasarına göre paylaştırılır: dalgadaki tüm
    # patronların toplam iyileşmesi, oyuncunun saniyelik hasarının belirli bir
    # oranını aşamaz.
    heal_rate = est * BOSS_LIFESTEAL_VS_DPS / max(1, len(bosses))
    for b in bosses:
        b.max_hp *= scale
        b.hp = b.max_hp
        b.heal_rate = heal_rate
    return scale


# =====================================================================
# DALGA / SPAWN YÖNETİCİSİ
# =====================================================================

# 10. dalgadan itibaren her dalgaya eklenen sabit "nefes payı" skoru.
# Oyuncu 10 saniyelik yoğunluk penceresinde zaten bolca skor topluyor;
# bu ek olmadan dalgalar art arda atlıyor. Tek yerden ayarlanabilsin diye sabit.
WAVE_BREATHER_FROM = 10     # bu dalgadan itibaren uygulanır
WAVE_BREATHER_BASE = 380    # 10. dalgada eklenen skor
WAVE_BREATHER_STEP = 150    # her sonraki dalgada üstüne eklenen skor

# Dalga hedeflerinin GENEL çarpanı — dalgaların ne kadar süreceğini belirleyen
# tek düğme. Dalga atlayınca gelen 10 saniyelik yoğunluk penceresinde oyuncu
# çok fazla skor topluyordu ve 2-3-4. dalgalar peş peşe saniyeler içinde
# geçiyordu. Bu çarpan hepsini birden uzatır.
#   Büyütürsen  -> dalgalar daha uzun sürer
#   Küçültürsen -> dalgalar daha hızlı geçer
WAVE_GOAL_SCALE = 2.8
# İlk dalgalar öğretici olduğu için çarpan orada kademeli devreye girer:
# 1. dalga tam çarpanı yemez, 5. dalgadan itibaren tamamı uygulanır.
WAVE_SCALE_RAMP = {1: 0.62, 2: 0.74, 3: 0.84, 4: 0.93}


# İlk dalgaların skor hedefleri elle belirlenir: oyunun açılışı burada
# şekillendiği için formüle bırakılmaz. Kabus temposunda her biri kabaca
# 25-35 saniye sürecek biçimde seçildi.
WAVE_GOAL_TABLE = {1: 600, 2: 2300, 3: 2900, 4: 3500, 5: 4100}
# 5. dalgadan sonrası formülle devam eder; bu çarpan, formülü tablodaki
# son değerle sürekli (kesintisiz) hâle getirir.
WAVE_GOAL_SCALE = 5.9


def wave_score_goal(wave, pace=1.0):
    """Bir sonraki dalgaya geçmek için o dalga içinde toplanması gereken SKOR.

    ÖNEMLİ — ZORLUK HEDEFİ DEĞİŞTİRMEZ.
    Normal, Zor ve Kabus'ta aynı dalgaya aynı skorla ulaşılır. Zorluk yalnızca
    düşmanların ne kadar hızlı ve kalabalık geldiğini belirler; Kabus'ta aynı
    sürede çok daha fazla düşman geldiği için aynı dalgaya kendiliğinden daha
    çabuk ulaşılır. (`pace` yalnızca geriye dönük uyumluluk için duruyor,
    hesaba KATILMAZ.)

    İlk 5 dalga WAVE_GOAL_TABLE'dan gelir, sonrası formülle büyür.
    """
    w = max(1, int(wave))
    if w in WAVE_GOAL_TABLE:
        return WAVE_GOAL_TABLE[w]
    # Spawn modeliyle aynı kademeler: aynı anda kaç düşman geliyorsa o dalgada
    # toplanabilecek skor da o oranda artar.
    burst = 1 if w < 3 else 2 if w < 6 else 3 if w < 10 else 4 if w < 16 else 5
    goal = (95 + 22 * w) * burst * WAVE_GOAL_SCALE
    # 10. dalgadan sonra ayrıca sabit bir "nefes payı" eklenir.
    if w >= WAVE_BREATHER_FROM:
        goal += WAVE_BREATHER_BASE + (w - WAVE_BREATHER_FROM) * WAVE_BREATHER_STEP
    return int(goal)


# Dalga atlandıktan sonraki "yoğunluk" penceresi: bu süre boyunca düşmanlar
# belirgin biçimde daha sık ve daha kalabalık gelir, sonra tempo normale döner.
SURGE_DURATION = 8.0
SURGE_RATE = 0.62      # spawn aralığı çarpanı (küçük = daha sık)
SURGE_EXTRA = 1        # her spawn'da kaç ek düşman

# --- DALGA İÇİ HIZLANMA ---------------------------------------------
# Oyun artık yalnızca dalga atlayınca hızlanmıyor. AYNI dalga içinde de
# zaman geçtikçe düşmanlar kademeli olarak daha sık geliyor; böylece bir
# dalga asla "durgunlaşmıyor", baskı sürekli ve hissedilir biçimde artıyor.
#   spawn_aralığı /= 1 + min(WAVE_ACCEL_MAX, dalga_süresi * WAVE_ACCEL_RATE)
WAVE_ACCEL_RATE = 0.030   # saniye başına hızlanma
WAVE_ACCEL_MAX = 1.10     # en fazla 2.1 kat hızlanır
# Dalga uzadıkça her dalgada gelen düşman sayısı da artar (kaç saniyede bir
# ek düşman eklendiği).
WAVE_ACCEL_EXTRA_AFTER = 26.0

# Arenada aynı anda yaşayabilecek AZAMİ düşman sayısı.
# Dalga içi hızlanma, oyuncu düşmanları temizleyemediğinde sınırsız birikime
# yol açabilirdi; bu da kare hızını (FPS) yere serer. Sınır dolduğunda yeni
# düşman doğmaz — oyuncu biraz temizleyince spawn kendiliğinden devam eder.
def max_alive_enemies(wave):
    return int(min(210, 70 + wave * 4))


class WaveManager:
    def __init__(self, diff="normal", biome="arena"):
        # biome: "arena" (1. harita) | "hell" (CEHENNEM)
        self.biome = biome
        self.wave = 1
        self.wave_time = 0.0
        self.pace = DIFF_PACE.get(diff, 1.0)
        # normal: yavaş/sakin tempo (uzun dalgalar) — kabus: hızlı/yoğun tempo (kısa dalgalar)
        self.wave_duration = 24.0 / self.pace
        self.spawn_timer = 0.0
        self.announce_timer = 2.4
        self.announce_text = ("CEHENNEM — DALGA 1" if biome == "hell" else "DALGA 1")
        self.diff = diff
        self.boss_idx = 0
        self.boss_active = False
        self.boss_pending = False
        # --- skor tabanlı ilerleme ---
        self.wave_start_score = 0      # bu dalgaya girerken oyuncunun skoru
        self.wave_score = 0            # bu dalgada toplanan skor
        self.wave_goal = wave_score_goal(1)
        # --- yoğunluk (surge) penceresi ---
        self.surge_timer = 0.0

    # Dünya ekrandan büyük olduğu için doğum noktasını RunState belirler
    # (kameranın hemen dışı). Atanmazsa eski davranışa (dünya kenarı) düşer.
    spawn_pos_fn = None

    def spawn_pos(self):
        if self.spawn_pos_fn is not None:
            return self.spawn_pos_fn()
        side = random.randint(0, 3)
        if side == 0:
            return (random.uniform(ARENA_RECT.left, ARENA_RECT.right), ARENA_RECT.top - 30)
        elif side == 1:
            return (random.uniform(ARENA_RECT.left, ARENA_RECT.right), ARENA_RECT.bottom + 30)
        elif side == 2:
            return (ARENA_RECT.left - 30, random.uniform(ARENA_RECT.top, ARENA_RECT.bottom))
        else:
            return (ARENA_RECT.right + 30, random.uniform(ARENA_RECT.top, ARENA_RECT.bottom))

    def is_boss_wave(self, w):
        """Patron dalgaları.

        ARENA : 10, 15, 20, 25 — ve ARTIK BU KADAR. 25. dalga patronu oyunun
                1. haritasının finalidir; ondan sonra yeni patron GELMEZ,
                bunun yerine arena her dalgada acımasızlaşarak oyuncuyu
                CEHENNEM KAPISI'na girmeye zorlar.
        CEHENNEM : 5, 10, 15 ...
        """
        if self.biome == "hell":
            return w >= HELL_BOSS_FIRST_WAVE and (w - HELL_BOSS_FIRST_WAVE) % HELL_BOSS_STEP == 0
        if w > HELL_PORTAL_WAVE:
            return False
        return w >= BOSS_FIRST_WAVE and (w - BOSS_FIRST_WAVE) % BOSS_WAVE_STEP == 0

    def surge_active(self):
        return self.surge_timer > 0

    def goal_progress(self):
        """0..1 arası — dalganın skor hedefine ne kadar yaklaşıldığı."""
        if self.wave_goal <= 0:
            return 1.0
        return clamp(self.wave_score / self.wave_goal, 0.0, 1.0)

    def _begin_wave(self, new_wave, total_score):
        """Yeni dalgaya geçerken sayaçları sıfırlar ve yoğunluk penceresini açar."""
        self.wave = new_wave
        self.wave_time = 0.0
        self.wave_start_score = total_score
        self.wave_score = 0
        self.wave_goal = wave_score_goal(new_wave)
        self.wave_duration = min(42 / self.pace, self.wave_duration + 1.1 / self.pace)
        self.surge_timer = SURGE_DURATION
        self.announce_timer = 2.2

    def pick_kind(self):
        if self.biome == "hell":
            return hell_pick_kind(self.wave)
        w = self.wave
        weights = {
            "red": 10,
            "blue": 6 + min(w, 10),
            "tank": max(0, min(w - 2, 8)),
            "yellow": max(0, min(w - 1, 8)),
            "sprinter": max(0, min(w - 3, 7)),
            "brute": max(0, min(w - 5, 6)),
        }
        kinds = list(weights.keys())
        wts = list(weights.values())
        return random.choices(kinds, weights=wts, k=1)[0]

    def update(self, dt, enemies, wave_mult_fn, boss_active=False, total_score=0):
        self.wave_time += dt
        if self.announce_timer > 0:
            self.announce_timer -= dt
        if self.surge_timer > 0:
            self.surge_timer = max(0.0, self.surge_timer - dt)

        # O dalgada toplanan skor = güncel toplam - dalga başındaki toplam
        self.wave_score = max(0, int(total_score) - int(self.wave_start_score))

        wave_changed = False
        if not boss_active and not self.boss_pending:
            # Dalga iki koşuldan biriyle ilerler:
            #   1) SKOR HEDEFİ tutturulduysa (asıl koşul, oyuncuyu ödüllendirir)
            #   2) Emniyet süresi dolduysa (oyuncu skor toplayamıyorsa oyun
            #      kilitlenmesin diye — normal dalga süresinin 2.8 katı)
            goal_met = self.wave_score >= self.wave_goal
            time_out = self.wave_time >= self.wave_duration * 2.8
            if goal_met or time_out:
                self._begin_wave(self.wave + 1, total_score)
                wave_changed = True
                if self.is_boss_wave(self.wave):
                    self.boss_pending = True
                    self.surge_timer = 0.0     # patron dalgasında yoğunluk olmaz
                    self.announce_text = "PATRON YAKLAŞIYOR!"
                elif self.biome == "hell":
                    self.announce_text = f"CEHENNEM — DALGA {self.wave}"
                elif self.wave > HELL_PORTAL_WAVE:
                    # Portal açıldıktan sonra arena her dalgada daha da azgınlaşır.
                    self.announce_text = f"DALGA {self.wave} — ARENA AZIYOR!"
                else:
                    self.announce_text = f"DALGA {self.wave} — YOĞUNLUK!"

        if boss_active or self.boss_pending:
            return wave_changed

        # Zorluk artık düşman istatistiklerini değil yalnızca TEMPOyu (pace)
        # etkiler — spawn hızı tamamen self.pace üzerinden belirlenir.
        # Taban aralık kısaltıldı: ilk dalgalarda oyun "boş" hissettiriyordu.
        base_interval = max(0.28, 1.15 - self.wave * 0.035) / self.pace
        # DALGA İÇİ HIZLANMA: aynı dalgada bile tempo sürekli artar.
        base_interval /= (1.0 + min(WAVE_ACCEL_MAX, self.wave_time * WAVE_ACCEL_RATE))
        if self.surge_active():
            base_interval *= SURGE_RATE
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_timer = base_interval
            # Kalabalık tavanı: arena tıkanmışsa bu turda yeni düşman doğmaz.
            if len(enemies) >= max_alive_enemies(self.wave):
                return wave_changed
            # Geç dalgalarda yalnızca hasar değil, düşman YOĞUNLUĞU da artar —
            # maksimum eşyalı bir oyuncu bile kalabalığa yenik düşebilsin.
            if self.wave < 3:
                count = 1
            elif self.wave < 6:
                count = 2
            elif self.wave < 10:
                count = 3
            elif self.wave < 16:
                count = 4
            else:
                count = 5
            # Dalga uzadıkça kalabalık da büyür (dalga içi hızlanmanın
            # ikinci ayağı) — oyuncu oyalanırsa baskı gerçekten artar.
            count += int(self.wave_time // WAVE_ACCEL_EXTRA_AFTER)
            if self.surge_active():
                count += SURGE_EXTRA
            hell = self.biome == "hell"
            for _ in range(count):
                kind = self.pick_kind()
                x, y = self.spawn_pos()
                if hell:
                    enemies.append(Enemy(None, x, y, wave_mult_fn(self.wave), 1.0,
                                         wave=self.wave, variant=kind, biome="hell"))
                else:
                    enemies.append(Enemy(kind, x, y, wave_mult_fn(self.wave), 1.0, wave=self.wave))
            elite_chance = 0.12 + min(0.28, self.wave * 0.008)
            if self.surge_active():
                elite_chance += 0.10
            if self.wave % 5 == 0 and random.random() < elite_chance:
                x, y = self.spawn_pos()
                if hell:
                    enemies.append(Enemy(None, x, y, wave_mult_fn(self.wave) * 1.1, 1.0,
                                         wave=self.wave, variant="h_warden", biome="hell"))
                else:
                    enemies.append(Enemy("elite", x, y, wave_mult_fn(self.wave) * 1.1, 1.0,
                                         wave=self.wave))

        return wave_changed


# =====================================================================
# COMBO SAYACI
# =====================================================================

class ComboMeter:
    def __init__(self):
        self.count = 0
        self.best = 0
        self.timer = 0.0
        self.window = 2.1
        self.pulse = 0.0

    def add_kill(self):
        self.count += 1
        self.best = max(self.best, self.count)
        self.timer = self.window
        self.pulse = 1.0

    def multiplier(self):
        return 1.0 + min(self.count * 0.04, 2.0)

    def update(self, dt):
        if self.timer > 0:
            self.timer -= dt
            if self.timer <= 0:
                self.count = 0
        if self.pulse > 0:
            self.pulse = max(0.0, self.pulse - dt * 3)


# =====================================================================
# BUTON / PANEL
# =====================================================================

class Button:
    def __init__(self, rect, text, callback=None, color=(52, 60, 96),
                 hover_color=(78, 92, 150), text_size=24, enabled=True,
                 subtitle=None, text_color=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.color = color
        self.hover_color = hover_color
        self.text_size = text_size
        self.enabled = enabled
        self.subtitle = subtitle
        self.text_color = text_color
        self.hover = False
        self.anim = 0.0

    def update(self, mouse_pos, dt):
        was = self.hover
        self.hover = self.enabled and self.rect.collidepoint(mouse_pos)
        if self.hover and not was:
            sfx("hover", 0.4, 0.05)
        target = 1.0 if self.hover else 0.0
        self.anim += (target - self.anim) * min(1, dt * 12)

    def draw(self, surf):
        col = self.hover_color if self.hover else self.color
        if not self.enabled:
            col = (38, 40, 52)
        grow = self.anim * 4
        r = self.rect.inflate(grow, grow)
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (*col, 235), s.get_rect(), border_radius=12)
        edge_a = 60 + int(self.anim * 120)
        pygame.draw.rect(s, (255, 255, 255, edge_a), s.get_rect(), width=2, border_radius=12)
        surf.blit(s, r.topleft)
        tc = self.text_color or ((235, 236, 245) if self.enabled else (110, 110, 122))
        draw_text(surf, self.text, r.center, self.text_size, tc, bold=True, center=True)
        if self.subtitle:
            draw_text(surf, self.subtitle, (r.centerx, r.bottom + 13), 13, TEXT_DIM, center=True, shadow=False)

    def click(self, mouse_pos):
        if self.enabled and self.rect.collidepoint(mouse_pos):
            sfx("click", 0.6, 0.0)
            if self.callback:
                self.callback()
            return True
        return False


def panel(surf, rect, bg=PANEL_BG, edge=PANEL_EDGE, alpha=235, radius=16, edge_w=2):
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (*bg, alpha), s.get_rect(), border_radius=radius)
    pygame.draw.rect(s, (*edge, 220), s.get_rect(), width=edge_w, border_radius=radius)
    surf.blit(s, rect.topleft)


def draw_scrollbar(surf, track_x, list_top, list_h, content_h, scroll):
    """Kaydırılabilir bir liste için sağ kenara ince bir scrollbar çizer."""
    track = pygame.Rect(track_x, list_top, 5, list_h)
    s = pygame.Surface(track.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (255, 255, 255, 30), s.get_rect(), border_radius=3)
    surf.blit(s, track.topleft)
    max_scroll = max(1, content_h - list_h)
    thumb_h = max(24, int(list_h * clamp(list_h / content_h, 0.08, 1.0)))
    thumb_y = list_top + int((list_h - thumb_h) * clamp(scroll / max_scroll, 0.0, 1.0))
    thumb = pygame.Rect(track_x, thumb_y, 5, thumb_h)
    ts = pygame.Surface(thumb.size, pygame.SRCALPHA)
    pygame.draw.rect(ts, (*GOLD, 220), ts.get_rect(), border_radius=3)
    surf.blit(ts, thumb.topleft)


# =====================================================================
# RUN STATE
# =====================================================================

class RunState:
    def __init__(self, save, skin_id, diff="normal", ach=None):
        self.save = save
        self.diff = diff
        self.player = Player(skin_id)
        self.player.cosmetics = save.equipped_cosmetics()
        self.player.apply_cosmetic_perks()
        self.enemies = []
        # Geç dalgalarda aynı anda birden fazla patron gelebildiği için artık
        # tek bir boss değil, yaşayan patronların listesi tutuluyor.
        self.bosses = []
        self.hazards = []
        self.pickups = []
        self.enemy_projectiles = []
        self.player_projectiles = []
        self.fx = EffectSystem()
        self.waves = WaveManager(diff)
        # Düşmanlar dünyanın kenarından değil, kameranın hemen dışından gelir.
        self.waves.spawn_pos_fn = self.near_camera_point
        self.combo = ComboMeter()
        self.ach = ach
        # Arkada kalan yaratıkları önüne ışınlama sayacı (bkz. reposition_stragglers)
        self.straggler_timer = 0.0

        # --- KAMERA ---
        # Dünya ekrandan büyük olduğu için kamera oyuncuyu yumuşak takip eder.
        self.cam_x = clamp(self.player.x - VIEW_RECT.w / 2,
                           ARENA_RECT.left, ARENA_RECT.right - VIEW_RECT.w)
        self.cam_y = clamp(self.player.y - VIEW_RECT.h / 2,
                           ARENA_RECT.top, ARENA_RECT.bottom - VIEW_RECT.h)
        # --- BÖLGE ---
        self.biome = "arena"          # "arena" | "hell"
        self.hell_portal = None       # 25. dalga patronundan sonra açılan mor portal

        self.kills = 0
        # ZAMAN DURDU sayacı: skin yetenekleri düşmanları bu süre boyunca dondurur.
        self.time_stop = 0.0
        self.bonk_hits = 0          # bu koşuda BONK ile vurulan düşman sayısı
        self.coins_earned = 0
        self.gold_wallet = 0
        self.run_time = 0.0
        self.score = 0
        self.game_over = False
        self.submitted_online = False
        self.pending_levelups = 0
        self.levelup_choices = []
        self.shop_offers = []
        self.market_portal = None
        self.want_open_shop = False
        self.bonk8_check = False
        self.gems_earned = 0
        self.death_cause = ""
        # Sağ üstteki "⋮" istatistik paneli açık mı?
        self.show_stats = False
        # Patron sandıkları (devrilen patronun yerine düşer)
        self.chests = []

    # ---------------- KAMERA ----------------
    def cam_rect(self):
        return pygame.Rect(int(self.cam_x), int(self.cam_y), VIEW_RECT.w, VIEW_RECT.h)

    def update_camera(self, dt, snap=False):
        p = self.player
        tx = clamp(p.x - VIEW_RECT.w / 2, ARENA_RECT.left, ARENA_RECT.right - VIEW_RECT.w)
        ty = clamp(p.y - VIEW_RECT.h / 2, ARENA_RECT.top, ARENA_RECT.bottom - VIEW_RECT.h)
        k = 1.0 if snap else min(1.0, dt * 7.0)
        self.cam_x += (tx - self.cam_x) * k
        self.cam_y += (ty - self.cam_y) * k

    def screen_to_world(self, sx, sy):
        return screen_to_world(sx, sy, self.cam_rect())

    def near_camera_point(self, margin=60):
        """Kameranın hemen dışında, dünyanın içinde kalan bir doğum noktası.

        Dünya 3x3 ekran büyüklüğünde olduğu için düşmanlar artık dünyanın
        kenarından değil, oyuncunun gördüğü alanın hemen dışından gelir.
        """
        cam = self.cam_rect()
        for _ in range(12):
            side = random.randint(0, 3)
            if side == 0:
                x, y = random.uniform(cam.left, cam.right), cam.top - margin
            elif side == 1:
                x, y = random.uniform(cam.left, cam.right), cam.bottom + margin
            elif side == 2:
                x, y = cam.left - margin, random.uniform(cam.top, cam.bottom)
            else:
                x, y = cam.right + margin, random.uniform(cam.top, cam.bottom)
            if ARENA_RECT.collidepoint(x, y):
                return x, y
        # Kamera dünyanın köşesindeyse: görüş alanının dışında bir nokta bul.
        for _ in range(30):
            x = random.uniform(ARENA_RECT.left + 40, ARENA_RECT.right - 40)
            y = random.uniform(ARENA_RECT.top + 40, ARENA_RECT.bottom - 40)
            if not cam.inflate(-80, -80).collidepoint(x, y):
                return x, y
        return ARENA_RECT.centerx, ARENA_RECT.centery

    # ---------------- KAÇANIN ÖNÜNE IŞINLANMA ----------------
    # Dünya 3x3 ekran büyüklüğüne çıktığından beri düşmanlardan kaçmak fazla
    # kolaylaştı: oyuncu bir yöne koşunca sürü geride kalıyor ve dalga
    # "boşluğa" dönüşüyordu. Artık ARKADA KALAN yaratıklar, oyuncunun KAÇTIĞI
    # yöne — yani önüne — ışınlanıyor. Kaçmak hâlâ mümkün ama artık bedava değil.
    STRAGGLER_CHECK = 0.45      # kaç saniyede bir bakılır
    STRAGGLER_MIN_SPEED = 95.0  # bu hızın altında "kaçıyor" sayılmaz
    STRAGGLER_BEHIND = 0.25     # arkada sayılması için gereken yön farkı (-1..1)
    STRAGGLER_FAR = 560.0       # bu mesafeden uzaktakiler ışınlanabilir
    STRAGGLER_MAX = 4           # tek seferde en fazla kaç yaratık ışınlanır
    STRAGGLER_COOLDOWN = 3.2    # aynı yaratık tekrar ışınlanana kadar geçen süre
    # Kaçış yönünde ne kadar ileriye bırakılacağı — kameranın hemen dışı.
    STRAGGLER_AHEAD_MIN = VIEW_RECT.w * 0.60
    STRAGGLER_AHEAD_MAX = VIEW_RECT.w * 0.85

    def reposition_stragglers(self, dt):
        """Oyuncunun arkasında kalan yaratıkları kaçış yönünün ÖNÜNE ışınlar.

        Yeni konum kameranın hemen DIŞINDA seçilir: yaratık gözünün önünde
        birden belirmez, oyuncu koşmaya devam edince karşısına çıkar. Her iki
        uçta da kısa bir halka efekti bırakılır ki "ışınlandı" hissi okunsun.
        """
        p = self.player
        if not p.alive:
            return
        self.straggler_timer -= dt
        if self.straggler_timer > 0:
            return
        self.straggler_timer = self.STRAGGLER_CHECK

        # Kaçış yönü: oyuncunun gerçek hızı (dash sırasında dash yönü).
        if p.dash_time > 0:
            mvx, mvy = p.dash_dx, p.dash_dy
            speed = p.dash_speed
        else:
            speed = math.hypot(p.vx, p.vy)
            if speed < 1e-3:
                return
            mvx, mvy = p.vx / speed, p.vy / speed
        if speed < self.STRAGGLER_MIN_SPEED:
            return

        # Bekleme süreleri önce topluca işlenir; aksi hâlde kontenjan dolunca
        # listenin sonundaki yaratıkların sayacı hiç azalmaz ve sonsuza kadar
        # "beklemede" kalırlardı.
        ready = []
        for e in self.enemies:
            if not e.alive or getattr(e, "is_boss", False):
                continue
            cd = getattr(e, "warp_cd", 0.0)
            if cd > 0:
                e.warp_cd = max(0.0, cd - self.STRAGGLER_CHECK)
            else:
                ready.append(e)

        cam = self.cam_rect()
        moved = 0
        for e in ready:
            if moved >= self.STRAGGLER_MAX:
                break
            dx, dy = e.x - p.x, e.y - p.y
            d = math.hypot(dx, dy)
            if d < self.STRAGGLER_FAR:
                continue
            # Oyuncunun gittiği yöne göre ARKADA mı? (nokta çarpımı negatifse arkada)
            if (dx * mvx + dy * mvy) / max(1e-3, d) > -self.STRAGGLER_BEHIND:
                continue
            spot = self._ahead_spawn_point(p, mvx, mvy, cam)
            if spot is None:
                continue
            self.fx.ring(e.x, e.y, e.color, n=10, speed=150, life=0.28, r=2.5)
            e.x, e.y = spot
            e.warp_cd = self.STRAGGLER_COOLDOWN
            e.spawn_t = min(e.spawn_t, 0.12)   # küçülüp büyüyerek "doğsun"
            self.fx.ring(e.x, e.y, e.color, n=14, speed=200, life=0.34, r=3)
            moved += 1

    def _ahead_spawn_point(self, p, mvx, mvy, cam):
        """Kaçış yönünde, kameranın hemen dışında kalan bir doğum noktası."""
        for _ in range(14):
            spread = random.uniform(-0.75, 0.75)
            ca, sa = math.cos(spread), math.sin(spread)
            ax = mvx * ca - mvy * sa
            ay = mvx * sa + mvy * ca
            d = random.uniform(self.STRAGGLER_AHEAD_MIN, self.STRAGGLER_AHEAD_MAX)
            x, y = p.x + ax * d, p.y + ay * d
            if not ARENA_RECT.inflate(-60, -60).collidepoint(x, y):
                continue
            if cam.inflate(60, 60).collidepoint(x, y):
                continue     # görüş alanının içinde belirmesin
            return x, y
        return None

    def wave_hp_mult(self, wave):
        if self.biome == "hell":
            # Cehennem yaratıkları arenanın 25. dalgası kadar canlı başlar.
            base = hell_hp_mult(wave)
        else:
            base = 1.0 + (wave - 1) * 0.22
        return base * (1.0 + self.player.enemy_hp_curse)

    def open_shop(self):
        self.shop_offers = SHOP_ITEMS

    def spawn_market_portal(self):
        # Dünya büyüdüğü için portal artık oyuncunun görüş alanına yakın açılır;
        # küçük haritada ve ekran kenarındaki okla yeri ayrıca gösterilir.
        p = self.player
        for _ in range(20):
            ang = random.uniform(0, math.tau)
            d = random.uniform(220, 420)
            x = clamp(p.x + math.cos(ang) * d, ARENA_RECT.left + 70, ARENA_RECT.right - 70)
            y = clamp(p.y + math.sin(ang) * d, ARENA_RECT.top + 70, ARENA_RECT.bottom - 70)
            if dist(x, y, p.x, p.y) > 180:
                break
        self.market_portal = MarketPortal(x, y)

    # ================= CEHENNEM KAPISI =================
    def open_hell_portal(self):
        """25. dalga patronu devrildiğinde MOR portalı açar.

        Portal oyuncu ölene ya da içine girene kadar yerinde durur.
        """
        p = self.player
        for _ in range(24):
            ang = random.uniform(0, math.tau)
            d = random.uniform(150, 300)
            x = clamp(p.x + math.cos(ang) * d, ARENA_RECT.left + 90, ARENA_RECT.right - 90)
            y = clamp(p.y + math.sin(ang) * d, ARENA_RECT.top + 90, ARENA_RECT.bottom - 90)
            if dist(x, y, p.x, p.y) > 120:
                break
        self.hell_portal = HellPortal(x, y)
        self.fx.do_flash(HELL_PORTAL_COLOR, 0.65)
        self.fx.shake(14, 0.5)
        for k in range(4):
            self.fx.shockwave(x, y, 120 + k * 150, HELL_PORTAL_COLOR, 0.7, 7 - k)
        self.fx.burst(x, y, HELL_PORTAL_COLOR2, n=40, speed=300, life=0.9, r=4)
        self.fx.popup(p.x, p.y - 70, "CEHENNEM KAPISI AÇILDI!", HELL_PORTAL_COLOR2, 30, life=2.4)
        self.waves.announce_timer = 3.2
        self.waves.announce_text = "CEHENNEM KAPISI AÇILDI — E İLE GİR"
        sfx("boss", 1.0, 0.0)

    def enter_hell(self):
        """Portala girildiğinde 2. haritaya (CEHENNEM) geçer.

        Oyuncuya ait hiçbir şey sıfırlanmaz: seviye, kitaplar, market eşyaları,
        altın, skor, öldürme sayısı aynen devam eder. Değişen tek şey HARİTA
        ve YARATIKLAR: cehennem yaratıkları arenanın 25. dalgası kadar canlı
        ve vurucudur ama hızları 1. dalga temposuna döner.
        """
        if self.biome == "hell":
            return
        p = self.player
        self.biome = "hell"
        self.hell_portal = None
        self.market_portal = None
        self.enemies.clear()
        self.bosses = []
        self.hazards.clear()
        self.enemy_projectiles.clear()
        self.player_projectiles.clear()
        self.pickups.clear()
        self.time_stop = 0.0
        # Arenadan kalan yanık/zehir/yavaşlatma cehenneme taşınmasın.
        p.clear_status()

        # Dalga düzeni baştan başlar (1. haritadaki gibi).
        self.waves = WaveManager(self.diff, biome="hell")
        self.waves.spawn_pos_fn = self.near_camera_point
        self.waves.wave_start_score = self.score
        self.waves.announce_timer = 3.4
        self.waves.announce_text = "CEHENNEM — DALGA 1"

        # Oyuncu cehenneme dinlenmiş girer (kapıdan geçiş ödülü).
        p.x, p.y = ARENA_RECT.centerx, ARENA_RECT.centery
        p.hp = p.max_hp
        p.invuln = max(p.invuln, 2.0)
        self.update_camera(0.0, snap=True)

        # Bellek: aynı anda tek zemin tutulur. Arena zemini bırakılır,
        # cehennem zemini burada (geçiş parlamasının altında) hazırlanır.
        _FLOOR_CACHE.pop("arena", None)
        floor_surface("hell")

        self.fx.do_flash(HELL_PORTAL_COLOR, 0.9)
        self.fx.shake(18, 0.7)
        self.fx.popup(p.x, p.y - 80, "CEHENNEME HOŞ GELDİN", (255, 140, 90), 34, life=2.6)
        # Cehenneme girer girmez market açılır: yeni CEHENNEM kademesini gör.
        self.spawn_market_portal()
        if self.ach:
            self.ach.unlock("hell_gate")
        sfx("boss", 1.0, 0.0)

    def buy_shop_item(self, key):
        item = SHOP_BY_KEY.get(key)
        if not item:
            return False
        if not shop_item_unlocked(item, self.waves.wave, self.biome):
            return False
        lvl = self.player.shop_levels.get(key, 0)
        if lvl >= item.get("max", 999):
            return False
        cost = shop_item_cost(item, lvl)
        if self.gold_wallet < cost:
            sfx("error", 0.6, 0.0)
            return False
        self.gold_wallet -= cost
        self.player.shop_levels[key] = lvl + 1
        apply_shop_item(self.player, key)
        self.fx.ring(self.player.x, self.player.y, item["color"], n=14, speed=160, life=0.35, r=3)
        sfx("buy", 1.0, 0.0)
        if item.get("cursed") and self.ach:
            self.ach.unlock("cursed")
        return True

    def do_player_attack(self, aim_dx, aim_dy):
        p = self.player
        # --- kitap çarpanları (atış anında hesaplanır) ---
        atk_mult = 1.0
        echo_shot = False
        if p.echo_level > 0:
            p.echo_count += 1
            if p.echo_count % 4 == 0:
                # YANKI KİTABI: her 4. atış çift hasar vurur
                atk_mult *= (1.0 + 1.0 * p.echo_level)
                echo_shot = True
        if p.swarm_level > 0:
            # SÜRÜ KİTABI: çevrende 3+ düşman varsa hasarın artar
            near = 0
            for e in self.enemies:
                if e.alive and dist(e.x, e.y, p.x, p.y) < 240:
                    near += 1
                    if near >= 3:
                        break
            if near >= 3:
                atk_mult *= (1.0 + 0.30 * p.swarm_level)
        n = 1 + p.multishot_level
        spread_deg = 9
        base_ang = math.atan2(aim_dy, aim_dx)
        speed = 660 * p.proj_speed_mult
        sk = p.skin
        for i in range(n):
            offset = (i - (n - 1) / 2) * math.radians(spread_deg)
            ang = base_ang + offset
            vx, vy = math.cos(ang) * speed, math.sin(ang) * speed
            hits = p.eff_pierce_hits()
            self.player_projectiles.append(PlayerProjectile(
                p.x + aim_dx * (p.radius + sk["wlen"] * 0.55), p.y + aim_dy * (p.radius + sk["wlen"] * 0.55),
                vx, vy, p.eff_dmg() * atk_mult, hits, p.eff_crit_chance(), p.eff_crit_dmg(),
                homing=p.homing_level, style=sk["proj"], color=sk["color"], accent=sk["accent"]))
        p.run_shots += n
        p.recoil = 1.0
        p.flash_t = 0.08
        if echo_shot:
            self.fx.ring(p.x, p.y, (255, 235, 150), n=10, speed=190, life=0.28, r=2.5)
        self.fx.spark(p.x + aim_dx * p.radius, p.y + aim_dy * p.radius, sk["accent"], aim_dx * 40, aim_dy * 40, .15, 2)
        sfx("shoot_" + sk["sfx"], 0.5, 0.035)

    def _titan_smash_fx(self, p):
        """EZİCİ DARBE'nin görsel/işitsel gösterisi."""
        self.fx.popup(p.x, p.y - 56, "EZİCİ DARBE!", (150, 255, 120), 30, life=1.1)
        self.fx.do_flash((150, 255, 130), 0.4)
        self.fx.shake(16, 0.45)
        for k in range(4):
            self.fx.shockwave(p.x, p.y, 260 + k * 260, (150, 255, 130), 0.55, 8 - k)
        self.fx.burst(p.x, p.y, (150, 255, 130), n=42, speed=320, life=0.7, r=5)
        sfx("explosion", 1.0, 0.0)

    def _apply_execute(self, p, e, dmg):
        if p.execute_threshold > 0 and not getattr(e, "is_boss", False) and e.kind != "elite" and e.hp > 0:
            if (e.hp - dmg) / e.max_hp <= p.execute_threshold and e.hp > dmg:
                return e.hp + 1
        return dmg

    def _explosion_splash(self, cx, cy, base_dmg, exclude_id=None):
        p = self.player
        if p.explosive_level <= 0:
            return
        radius = 74
        for e2 in self.enemies:
            if not e2.alive or id(e2) == exclude_id:
                continue
            if dist(cx, cy, e2.x, e2.y) <= radius:
                sdmg = base_dmg * 0.35 * p.explosive_level
                died2 = e2.take_damage(sdmg, False, self.fx)
                if died2:
                    self.on_enemy_killed(e2)
        self.fx.ring(cx, cy, (240, 130, 60), n=10, speed=140, life=0.25, r=2.5)

    def _all_targets(self):
        t = list(self.enemies)
        t.extend(b for b in self.bosses if b.alive)
        return t

    TITAN_SMASH_CD = 10.0          # ezici darbe bekleme süresi (saniye)
    TITAN_SMASH_HP_CUT = 0.5       # patron dışı düşmanların canı bu orana iner

    # ================= PATRON SANDIĞI / OTOMATİK SİLAHLAR =================
    def spawn_boss_chest(self, boss):
        """Devrilen patronun yerine sandık bırakır."""
        x = clamp(boss.x, ARENA_RECT.left + 60, ARENA_RECT.right - 60)
        y = clamp(boss.y, ARENA_RECT.top + 60, ARENA_RECT.bottom - 60)
        self.chests.append(BossChest(x, y, boss.name))
        self.fx.ring(x, y, GOLD, n=24, speed=230, life=0.6, r=4)
        self.fx.popup(x, y - 70, "SANDIK DÜŞTÜ!", GOLD, 26, life=1.6)
        sfx("coin", 0.9, 0.0)

    def grant_weapon(self, chest):
        """Sandıktan bir silah verir (yoksa yenisini, varsa seviye yükseltir)."""
        p = self.player
        missing = [w for w in BOSS_WEAPONS if w["key"] not in p.weapons]
        if missing:
            w = random.choice(missing)
            p.weapons[w["key"]] = 1
            p.weapon_timers[w["key"]] = weapon_cooldown(w, 1) * 0.35
            head, sub = f"{w['name']} BULDUN!", w["desc"]
        else:
            # Hepsi zaten var: en düşük seviyeli silahlardan biri yükselir.
            low = min(p.weapons.values())
            key = random.choice([k for k, v in p.weapons.items() if v == low])
            w = WEAPON_BY_KEY[key]
            if p.weapons[key] >= WEAPON_MAX_LEVEL:
                # Tavana ulaşıldıysa sandık altına dönüşür — boşa gitmesin.
                gold = 400 + self.waves.wave * 45
                self.gold_wallet += gold
                self.coins_earned += gold
                self.fx.popup(chest.x, chest.y - 60, f"+{gold} ALTIN", GOLD, 26, life=1.6)
                return
            p.weapons[key] += 1
            head = f"{w['name']} SEVİYE {p.weapons[key]}"
            sub = "daha sert vurur, daha sık ateşler"
        self.fx.popup(chest.x, chest.y - 74, head, w["color"], 28, life=1.8)
        self.fx.popup(chest.x, chest.y - 46, sub, TEXT, 14, life=1.8)
        self.fx.do_flash(w["color"], 0.35)
        self.fx.ring(chest.x, chest.y, w["color"], n=26, speed=280, life=0.6, r=4)
        sfx("levelup", 1.0, 0.0)

    def update_chests(self, dt):
        for ch in list(self.chests):
            ch.update(dt, self.player)
            if ch.opened and not ch.taken:
                ch.taken = True
                self.grant_weapon(ch)
        self.chests = [c for c in self.chests if c.alive]

    def _weapon_targets(self, max_d=WEAPON_RANGE):
        """Silahların vurabileceği, menzildeki canlı hedefler."""
        p = self.player
        out = []
        for e in self.enemies:
            if e.alive and dist(p.x, p.y, e.x, e.y) <= max_d:
                out.append(e)
        for b in self.bosses:
            # Görünmez patrona silahlar da kilitlenemez.
            if b.alive and not b.is_hidden() and dist(p.x, p.y, b.x, b.y) <= max_d:
                out.append(b)
        return out

    def update_boss_weapons(self, dt):
        """Sandıktan çıkan silahları otomatik ateşler.

        Oyuncu hiçbir tuşa basmaz: her silahın kendi bekleme süresi dolduğunda
        menzildeki en uygun hedefe kendiliğinden vurur.
        """
        p = self.player
        if not p.weapons or not p.alive:
            return
        targets = None
        for key in list(p.weapons.keys()):
            w = WEAPON_BY_KEY.get(key)
            if w is None:
                continue
            lvl = p.weapons[key]
            p.weapon_timers[key] = p.weapon_timers.get(key, 0.0) - dt
            if p.weapon_timers[key] > 0:
                continue
            if targets is None:
                targets = self._weapon_targets()
            if not targets:
                # Hedef yokken sayaç eksiye kaymasın; silah "hazır" bekler.
                p.weapon_timers[key] = 0.0
                continue
            self._fire_weapon(w, lvl, targets)
            p.weapon_timers[key] = weapon_cooldown(w, lvl)

    def _weapon_hit(self, e, dmg, kb=90, crit=None):
        """Silah vuruşunun ortak kapısı: kritik, infaz, kan emme, ölüm."""
        p = self.player
        if crit is None:
            crit = random.random() < p.eff_crit_chance()
        if crit:
            p.run_crits += 1
            dmg *= p.eff_crit_dmg()
        if p.boss_hunter > 0 and (getattr(e, "is_boss", False) or getattr(e, "kind", "") == "elite"):
            dmg *= (1.0 + 0.30 * p.boss_hunter)
        dmg = self._apply_execute(p, e, dmg)
        kx, ky = norm_dir(p.x, p.y, e.x, e.y)
        real_kb = 12 if getattr(e, "is_boss", False) else kb
        died = e.take_damage(dmg, crit, self.fx, kx * real_kb, ky * real_kb)
        if p.vamp_level > 0:
            p.lifesteal(dmg * 0.02 * p.vamp_level)
        if died:
            self.on_enemy_killed(e)
        return died

    def _weapon_projectile(self, w, dmg, ang, speed, hits, life):
        p = self.player
        # Silah mermileri de oyuncunun kritik şansını ve kritik hasarını
        # kullanır; çarpışma çözümü normal mermilerle aynı yerden geçer.
        pr = PlayerProjectile(p.x, p.y, math.cos(ang) * speed, math.sin(ang) * speed,
                              dmg, hits, p.eff_crit_chance(), p.eff_crit_dmg(),
                              style=w["style"] or "bolt", color=w["color"], accent=WHITE)
        pr.life = life
        self.player_projectiles.append(pr)
        return pr

    def _fire_weapon(self, w, lvl, targets):
        p = self.player
        dmg = weapon_damage(p, w, lvl)
        key = w["key"]
        nearest = min(targets, key=lambda e: dist(p.x, p.y, e.x, e.y))
        ang = math.atan2(nearest.y - p.y, nearest.x - p.x)

        if key == "pistol":
            # TABANCA: tek hedefe hızlı kurşun.
            self._weapon_projectile(w, dmg, ang, 980, 1, 1.0)
            self.fx.bolt([(p.x, p.y), (p.x + math.cos(ang) * 26, p.y + math.sin(ang) * 26)],
                         (255, 230, 160), 0.10)
            sfx("shoot_a", 0.35, 0.0)

        elif key == "bow":
            # OK: uzun menzilli, birçok düşmanı delen ok.
            self._weapon_projectile(w, dmg, ang, 760, 3 + lvl // 2, 1.7)
            sfx("shoot_b", 0.35, 0.0)

        elif key == "axe":
            # BALTA: dönerek uçar, yoluna çıkan herkesi biçer (çok delici).
            n = 1 + (1 if lvl >= 4 else 0) + (1 if lvl >= 7 else 0)
            for i in range(n):
                off = (i - (n - 1) / 2) * 0.34
                self._weapon_projectile(w, dmg, ang + off, 430, 4 + lvl, 1.6)
            sfx("shoot_c", 0.4, 0.0)

        elif key == "katana":
            # KATANA: oyuncunun çevresine yarım ay kesik — yakındaki herkese vurur.
            rad = 168 + lvl * 9
            hit = 0
            for e in list(self._all_targets()):
                if e.alive and dist(p.x, p.y, e.x, e.y) <= rad:
                    self._weapon_hit(e, dmg, kb=150)
                    hit += 1
            arc = [(p.x + math.cos(ang + a) * rad * 0.9, p.y + math.sin(ang + a) * rad * 0.9)
                   for a in (-0.95, -0.5, 0.0, 0.5, 0.95)]
            self.fx.bolt(arc, w["color"], 0.22)
            self.fx.shockwave(p.x, p.y, rad, w["color"], 0.22, 3)
            if hit:
                self.fx.shake(4, 0.12)
            sfx("bonk", 0.45, 0.0)

        else:  # hammer
            # ÇEKİÇ: hedefin üstüne iner, düştüğü yeri sarsar.
            rad = 132 + lvl * 8
            tx, ty = nearest.x, nearest.y
            for e in list(self._all_targets()):
                if e.alive and dist(tx, ty, e.x, e.y) <= rad:
                    self._weapon_hit(e, dmg, kb=210)
            self.fx.shockwave(tx, ty, rad, w["color"], 0.35, 6)
            self.fx.burst(tx, ty, w["color"], n=18, speed=220, life=0.5, r=3.5)
            self.fx.bolt([(tx, ty - 260), (tx, ty)], w["color"], 0.18)
            self.fx.shake(8, 0.22)
            sfx("explosion", 0.5, 0.0)

    def do_bonk(self):
        p = self.player
        # YEŞİL DEV — EZİCİ DARBE: 10 saniyede bir, BONK tüm arenayı kaplar ve
        # patronlar dışındaki her düşmanın canını yarıya indirir. Aradaki
        # BONK'lar normal (5 saniyede bir) çalışır.
        smash = bool(p.titan_smash) and p.smash_timer <= 0
        if smash:
            p.smash_timer = self.TITAN_SMASH_CD
            radius = math.hypot(ARENA_RECT.width, ARENA_RECT.height)
            self._titan_smash_fx(p)
        else:
            radius = p.eff_bonk_radius()
        dmg = p.eff_dmg() * 1.9 * p.bonk_mult
        hit_any = 0
        hit_ids = set()
        for e in self._all_targets():
            if not e.alive:
                continue
            d = dist(p.x, p.y, e.x, e.y)
            if d <= radius:
                hit_any += 1
                hit_ids.add(id(e))
                crit = random.random() < p.eff_crit_chance()
                final_dmg = dmg * (p.eff_crit_dmg() if crit else 1.0)
                final_dmg = self._apply_execute(p, e, final_dmg)
                kx, ky = norm_dir(p.x, p.y, e.x, e.y)
                if p.boss_hunter > 0 and (getattr(e, "is_boss", False) or e.kind == "elite"):
                    final_dmg *= (1.0 + 0.30 * p.boss_hunter)
                died = e.take_damage(final_dmg, crit, self.fx, kx * 260, ky * 260)
                # KÜKREME KİTABI: BONK yiyen sıradan düşmanlar korkup kaçar
                if p.roar_level > 0 and not getattr(e, "is_boss", False) and hasattr(e, "fear_timer"):
                    e.fear_timer = max(e.fear_timer, 1.0 + 0.6 * p.roar_level)
                if p.vamp_level > 0:
                    p.lifesteal(final_dmg * 0.02 * p.vamp_level)
                if died:
                    self.on_enemy_killed(e)
        if smash:
            # Canı yarıya indirme: hasardan AYRI bir etkidir, patronlara işlemez.
            for e in self.enemies:
                if e.alive and not getattr(e, "is_boss", False) and e.hp > 1:
                    e.hp = max(1.0, e.hp * self.TITAN_SMASH_HP_CUT)
                    self.fx.spark(e.x, e.y, (170, 255, 140), 0, -40, .5, 3)
        self.bonk_hits += hit_any
        if hit_any >= 8 and self.ach:
            self.ach.unlock("bonk8")
        if p.chain_level > 0:
            candidates = [e for e in self.enemies if e.alive and id(e) not in hit_ids
                          and dist(p.x, p.y, e.x, e.y) <= radius * 2.2]
            candidates.sort(key=lambda e: dist(p.x, p.y, e.x, e.y))
            for e in candidates[:1 + p.chain_level]:
                cdmg = dmg * 0.5
                died = e.take_damage(cdmg, False, self.fx)
                self.fx.ring(e.x, e.y, (120, 200, 255), n=8, speed=120, life=0.25, r=2)
                if died:
                    self.on_enemy_killed(e)
        self.fx.ring(p.x, p.y, ORANGE, n=20, speed=260, life=0.35, r=3)
        self.fx.shockwave(p.x, p.y, radius, ORANGE, 0.3, 4)
        self.fx.shake(6 if hit_any else 3, 0.15)
        sfx("bonk", 1.0, 0.0)

    def do_storm_strike(self):
        p = self.player
        targets = [e for e in self.enemies if e.alive]
        targets.extend(b for b in self.bosses if b.alive)
        if not targets:
            return
        e = random.choice(targets)
        dmg = p.eff_dmg() * (0.9 + 0.35 * p.storm_level)
        died = e.take_damage(dmg, False, self.fx)
        self.fx.bolt(zigzag(e.x, e.y - 320, e.x, e.y, 6, 22), (190, 215, 255), 0.3)
        self.fx.shockwave(e.x, e.y, 40, (190, 215, 255), 0.25, 3)
        sfx("lightning", 0.7, 0.0)
        if died:
            self.on_enemy_killed(e)

    # =================================================================
    # SKİN ÖZEL YETENEKLERİ
    # -----------------------------------------------------------------
    # Yetenekler otomatik çalışır. ORTAK KURAL: hangi yetenek tetiklenirse
    # tetiklensin düşmanlar ULT_FREEZE_ON_CAST kadar (0.5 sn) DONAR, sonra
    # hareketlerine kaldıkları yerden devam eder.
    # =================================================================

    def _ult_targets(self, radius=None):
        """Yeteneğin vuracağı canlı hedefler (patronlar dâhil)."""
        p = self.player
        out = []
        for e in self._all_targets():
            if not e.alive:
                continue
            if radius is None or dist(p.x, p.y, e.x, e.y) <= radius:
                out.append(e)
        return out

    def _ult_hit(self, e, dmg, crit=False, kb=0.0):
        """Yetenek hasarı uygular; ölürse ödülleri işler."""
        p = self.player
        if p.boss_hunter > 0 and (getattr(e, "is_boss", False) or getattr(e, "kind", "") == "elite"):
            dmg *= (1.0 + 0.30 * p.boss_hunter)
        kx, ky = norm_dir(p.x, p.y, e.x, e.y)
        died = e.take_damage(dmg, crit, self.fx, kx * kb, ky * kb)
        if died:
            self.on_enemy_killed(e)
        return died

    def freeze_enemies(self, duration):
        """Zamanı durdurur: düşmanlar, patronlar, mermileri ve tuzakları donar.
        Oyuncu bu sırada serbestçe hareket eder ve ateş edebilir."""
        self.time_stop = max(self.time_stop, float(duration))

    def _ult_spawn_nova(self, n, mult, pierce=1, homing=0, style=None, spread=math.tau,
                        base_ang=None, speed=640):
        """Oyuncunun çevresine halka biçiminde mermi saçar."""
        p = self.player
        sk = p.skin
        if base_ang is None:
            base_ang = math.atan2(p.aim_dir[1], p.aim_dir[0])
        for i in range(n):
            ang = base_ang + (spread * i / n if spread >= math.tau else
                              (spread * (i / max(1, n - 1) - 0.5)))
            vx, vy = math.cos(ang) * speed, math.sin(ang) * speed
            self.player_projectiles.append(PlayerProjectile(
                p.x + math.cos(ang) * (p.radius + 6), p.y + math.sin(ang) * (p.radius + 6),
                vx, vy, p.eff_dmg() * mult, p.eff_pierce_hits() + pierce,
                p.eff_crit_chance(), p.eff_crit_dmg(), homing=homing,
                style=style or sk["proj"], color=sk["color"], accent=sk["accent"]))
        p.run_shots += n

    def _ult_lightning_fx(self, x, y, color=(190, 215, 255)):
        self.fx.bolt(zigzag(x, y - 320, x, y, 6, 22), color, 0.3)
        self.fx.shockwave(x, y, 46, color, 0.25, 3)

    def _ult_banner(self, text, color):
        p = self.player
        self.fx.popup(p.x, p.y - 58, text, color, 26, life=1.0)

    def update_skin_ult(self, dt):
        """Skin yeteneğinin bekleme süresini işler ve zamanı gelince çalıştırır."""
        p = self.player
        if not p.ult or not p.alive:
            return
        # Şarta bağlı (trigger) yetenekler Player içinde işaretlenir.
        if p.ult_trigger:
            kind = p.ult_trigger
            p.ult_trigger = None
            self.fire_skin_ult(kind)
        elif p.ult.get("mode", "auto") == "auto" and p.ult_ready():
            p.start_ult_cooldown()
            self.fire_skin_ult(p.ult["kind"])

        # --- DİKEN TARLASI: süresi boyunca çevreyi zehirlemeye devam eder ---
        if p.thorn_field_t > 0:
            p.thorn_field_t -= dt
            p.thorn_field_tick -= dt
            if p.thorn_field_tick <= 0:
                p.thorn_field_tick = 0.5
                for e in self._ult_targets(p.thorn_field_r):
                    self._ult_hit(e, p.eff_dmg() * 0.35)
                    if hasattr(e, "apply_slow"):
                        e.apply_slow(0.7, 0.8)
                self.fx.shockwave(p.x, p.y, p.thorn_field_r, (120, 220, 140), 0.3, 3)

    def fire_skin_ult(self, kind):
        """Bir skin yeteneğini çalıştırır."""
        p = self.player
        ult = p.ult or {}
        col = tuple(ult.get("color", (255, 255, 255)))
        # ORTAK KURAL: her yetenek düşmanları kısa süre dondurur.
        self.freeze_enemies(ULT_FREEZE_ON_CAST)
        self.fx.ring(p.x, p.y, col, n=22, speed=260, life=0.45, r=3.5)
        self.fx.shake(6, 0.2)
        p.ult_fx_t = 0.5
        name = ult.get("name", "YETENEK")

        # ---------------- KLASİK MAVİ: KALKAN PROTOKOLÜ ----------------
        if kind == "guard":
            p.shield_charges += 2
            p.heal(p.max_hp * 0.15)
            self.fx.shockwave(p.x, p.y, 120, col, 0.4, 5)
            self._ult_banner(name, col)
            sfx("shield", 1.0, 0.0)

        # ---------------- YEŞİL ÖNCÜ: ÖNCÜ ATILIMI ----------------
        elif kind == "sprint":
            p.add_temp_buff(6.0, run_spd_mult=0.35, run_aspd_mult=0.25)
            p.dash_cd_timer = 0.0
            self._ult_banner(name, col)
            sfx("dash", 1.0, 0.0)

        # ---------------- ÇOK YÖNLÜ MERMİ YAĞMURU ----------------
        elif kind == "nova":
            self._ult_spawn_nova(int(ult.get("n", 14)), float(ult.get("mult", 0.85)),
                                 pierce=int(ult.get("pierce", 1)))
            self._ult_banner(name, col)
            sfx("shoot_" + p.skin["sfx"], 0.7, 0.0)

        # ---------------- GÜDÜMLÜ SALVO ----------------
        elif kind == "salvo":
            self._ult_spawn_nova(int(ult.get("n", 9)), float(ult.get("mult", 0.95)),
                                 pierce=1, homing=2)
            self._ult_banner(name, col)
            sfx("shoot_" + p.skin["sfx"], 0.7, 0.0)

        # ---------------- ZEHİR BULUTU ----------------
        elif kind == "poison_cloud":
            rad = float(ult.get("radius", 280))
            for e in self._ult_targets(rad):
                if hasattr(e, "apply_poison"):
                    e.apply_poison(6.0)
                if hasattr(e, "apply_slow"):
                    e.apply_slow(0.6, 3.0)
                self._ult_hit(e, p.eff_dmg() * 0.5)
            self.fx.shockwave(p.x, p.y, rad, col, 0.5, 6)
            self._ult_banner(name, col)
            sfx("explosion", 0.7, 0.0)

        # ---------------- KRALİYET FERMANI ----------------
        elif kind == "star_fall":
            targets = self._ult_targets()
            random.shuffle(targets)
            for e in targets[:int(ult.get("n", 7))]:
                self._ult_hit(e, p.eff_dmg() * float(ult.get("mult", 1.35)), kb=90)
                self.fx.burst(e.x, e.y, col, n=10, speed=150, life=0.4, r=3)
                self.fx.shockwave(e.x, e.y, 54, col, 0.3, 3)
            self._ult_banner(name, col)
            sfx("levelup", 0.8, 0.0)

        # ---------------- ELEKTRİK CYAN: YILDIRIM FIRTINASI ----------------
        elif kind == "chain_storm":
            # Haritadaki HERKESE yıldırım düşer.
            #  - sıradan düşman / elit : azami canının %20'si gider
            #  - PATRON               : Lv.3 fırtına hasarı (yüzde DEĞİL)
            boss_dmg = p.eff_dmg() * (0.9 + 0.35 * 3)
            for e in self._ult_targets():
                if getattr(e, "is_boss", False):
                    self._ult_hit(e, boss_dmg)
                else:
                    self._ult_hit(e, max(1.0, e.max_hp * 0.20))
                self._ult_lightning_fx(e.x, e.y, col)
            self.fx.do_flash(col, 0.35)
            self._ult_banner(name, col)
            sfx("lightning", 1.0, 0.0)

        # ---------------- GÖLGE SUİKASTÇI: GÖLGE DURUŞU ----------------
        elif kind == "death_defy":
            dur = float(ult.get("duration", 5.0))
            # Zaman durur: düşmanlar, mermileri ve tuzaklar donar; oyuncu serbest.
            self.freeze_enemies(dur)
            p.hp = max(1.0, p.hp)
            p.invuln = max(p.invuln, dur + 0.4)
            self.fx.do_flash(col, 0.5)
            for k in range(3):
                self.fx.shockwave(p.x, p.y, 200 + k * 180, col, 0.6, 6 - k)
            self._ult_banner(name + "  —  ZAMAN DURDU", col)
            sfx("second", 1.0, 0.0)

        # ---------------- İNFERNO: ALEV HALKASI ----------------
        elif kind == "fire_ring":
            rad = float(ult.get("radius", 330))
            for e in self._ult_targets(rad):
                self._ult_hit(e, p.eff_dmg() * 1.1, kb=140)
                if hasattr(e, "apply_burn"):
                    e.apply_burn(10.0, 4.0)
            for k in range(3):
                self.fx.shockwave(p.x, p.y, rad * (0.5 + k * 0.28), col, 0.45, 6 - k)
            self.fx.burst(p.x, p.y, col, n=26, speed=280, life=0.6, r=4)
            self._ult_banner(name, col)
            sfx("explosion", 1.0, 0.0)

        # ---------------- ALTIN EFSANE: ALTIN DOKUNUŞ ----------------
        elif kind == "midas":
            rad = float(ult.get("radius", 340))
            for e in self._ult_targets(rad):
                self._ult_hit(e, p.eff_dmg() * 0.9)
                if e.alive:
                    self.pickups.append(Pickup(e.x + random.uniform(-10, 10),
                                               e.y + random.uniform(-10, 10), "coin",
                                               max(2, int(e.coin * 0.6))))
                self.fx.spark(e.x, e.y, GOLD, 0, -40, 0.5, 3)
            self.fx.shockwave(p.x, p.y, rad, GOLD, 0.45, 5)
            self._ult_banner(name, GOLD)
            sfx("coin", 1.0, 0.0)

        # ---------------- GÖLGE AVCI: SESSİZ PUSU ----------------
        elif kind == "ambush":
            dur = float(ult.get("duration", 4.0))
            p.invuln = max(p.invuln, dur)
            p.crit_forced = max(p.crit_forced, dur)
            p.add_temp_buff(dur, run_spd_mult=0.2)
            for k in range(6):
                p.ghosts.append([p.x, p.y, 0.5, (90, 60, 150)])
            self._ult_banner(name, col)
            sfx("dash", 1.0, 0.0)

        # ---------------- BUZ BÜYÜCÜSÜ: BUZ ÇAĞI ----------------
        elif kind == "ice_age":
            freeze = float(ult.get("freeze", 2.5))
            self.freeze_enemies(freeze)
            for e in self._ult_targets():
                self._ult_hit(e, p.eff_dmg() * 0.7)
                if hasattr(e, "apply_slow"):
                    e.apply_slow(0.45, freeze + 5.0)
            self.fx.do_flash(col, 0.3)
            self.fx.shockwave(p.x, p.y, 520, col, 0.6, 6)
            self._ult_banner(name, col)
            sfx("shield", 1.0, 0.0)

        # ---------------- KAN KONTESİ: KAN AYİNİ ----------------
        elif kind == "blood_rite":
            rad = float(ult.get("radius", 320))
            drained = 0.0
            for e in self._ult_targets(rad):
                dmg = e.max_hp * 0.10 + p.eff_dmg() * 0.5
                before = e.hp
                self._ult_hit(e, dmg)
                drained += max(0.0, before - max(0.0, e.hp))
                self.fx.bolt([(e.x, e.y), (p.x, p.y)], (235, 70, 100), 0.25)
            if drained > 0:
                p.lifesteal(drained * 0.5)
            self.fx.shockwave(p.x, p.y, rad, col, 0.45, 5)
            self._ult_banner(name, col)
            sfx("hurt", 0.8, 0.0)

        # ---------------- ZIRHLI DEVRİYE: ZIRH KİLİDİ ----------------
        elif kind == "bulwark":
            dur = float(ult.get("duration", 6.0))
            p.add_temp_buff(dur, dmg_taken_mult=-0.55)
            p.shield_charges += 1
            for e in self._ult_targets(260):
                self._ult_hit(e, p.eff_dmg() * 0.6, kb=420)
            self.fx.shockwave(p.x, p.y, 260, col, 0.45, 6)
            self._ult_banner(name, col)
            sfx("shield", 1.0, 0.0)

        # ---------------- FIRTINA GETİRİCİ: GÖK GÜRÜLTÜSÜ ----------------
        elif kind == "thunder":
            targets = self._ult_targets()
            random.shuffle(targets)
            n = int(ult.get("n", 6))
            for e in targets[:n] if targets else []:
                self._ult_hit(e, p.eff_dmg() * float(ult.get("mult", 1.6)))
                self._ult_lightning_fx(e.x, e.y, col)
            self.fx.do_flash(col, 0.3)
            self._ult_banner(name, col)
            sfx("lightning", 1.0, 0.0)

        # ---------------- ZEHİR VURUŞÇU: DİKEN TARLASI ----------------
        elif kind == "thorn_field":
            p.thorn_field_t = float(ult.get("duration", 6.0))
            p.thorn_field_r = float(ult.get("radius", 240))
            p.thorn_field_tick = 0.0
            self.fx.shockwave(p.x, p.y, p.thorn_field_r, col, 0.45, 5)
            self._ult_banner(name, col)
            sfx("buy", 0.8, 0.0)

        # ---------------- ÇILGIN CANAVAR: KAN ÇILGINLIĞI ----------------
        elif kind == "frenzy_rush":
            dur = float(ult.get("duration", 7.0))
            p.add_temp_buff(dur, run_dmg_mult=0.40, run_aspd_mult=0.30)
            p.frenzy_stacks = max(p.frenzy_stacks, 4)
            p.frenzy_timer = max(p.frenzy_timer, dur)
            self.fx.do_flash(col, 0.25)
            self._ult_banner(name, col)
            sfx("bonk", 0.9, 0.0)

        # ---------------- YÖRÜNGE BEKÇİSİ: YÖRÜNGE KALKANI ----------------
        elif kind == "orbit_shield":
            dur = float(ult.get("duration", 8.0))
            p.add_temp_buff(dur, orbit_level=3)
            p.shield_charges += 1
            self.fx.shockwave(p.x, p.y, 120, col, 0.4, 5)
            self._ult_banner(name, col)
            sfx("shield", 1.0, 0.0)

        # ---------------- AĞ USTASI: AĞ TUZAĞI ----------------
        elif kind == "web_trap":
            rad = float(ult.get("radius", 360))
            for e in self._ult_targets(rad):
                if hasattr(e, "apply_slow"):
                    e.apply_slow(0.12, 4.0)
                self._ult_hit(e, p.eff_dmg() * 0.6)
                self.fx.bolt([(p.x, p.y), (e.x, e.y)], (240, 240, 255), 0.3)
            self.fx.shockwave(p.x, p.y, rad, col, 0.45, 5)
            self._ult_banner(name, col)
            sfx("shoot_a", 0.8, 0.0)

        # ---------------- KÜL SAVAŞÇISI: KÜL KASIRGASI ----------------
        elif kind == "ash_spin":
            rad = float(ult.get("radius", 230))
            total = 0.0
            for e in self._ult_targets(rad):
                dmg = p.eff_dmg() * float(ult.get("mult", 2.0))
                before = e.hp
                self._ult_hit(e, dmg, kb=260)
                total += max(0.0, before - max(0.0, e.hp))
            if total > 0:
                p.lifesteal(total * 0.25)
            for k in range(3):
                self.fx.shockwave(p.x, p.y, rad * (0.55 + k * 0.25), col, 0.4, 5 - k)
            self._ult_banner(name, col)
            sfx("bonk", 1.0, 0.0)

        # ---------------- YEŞİL DEV: YER SARSINTISI ----------------
        elif kind == "quake":
            for e in self._ult_targets():
                self._ult_hit(e, p.eff_dmg() * float(ult.get("mult", 1.3)), kb=360)
                self.fx.spark(e.x, e.y, col, 0, -50, 0.5, 3)
            self.fx.shake(18, 0.5)
            for k in range(4):
                self.fx.shockwave(p.x, p.y, 240 + k * 260, col, 0.55, 8 - k)
            self._ult_banner(name, col)
            sfx("explosion", 1.0, 0.0)

        # ---------------- PEMBE RÜYA: RÜYA PATLAMASI ----------------
        elif kind == "dream":
            rad = float(ult.get("radius", 300))
            dur = float(ult.get("duration", 6.0))
            p.heal(p.max_hp * 0.25)
            p.add_temp_buff(dur, run_crit_bonus=0.25)
            for e in self._ult_targets(rad):
                self._ult_hit(e, p.eff_dmg() * 0.7)
                if hasattr(e, "fear_timer"):
                    e.fear_timer = max(e.fear_timer, 3.0)
            self.fx.shockwave(p.x, p.y, rad, col, 0.5, 6)
            self.fx.burst(p.x, p.y, col, n=24, speed=220, life=0.6, r=4)
            self._ult_banner(name, col)
            sfx("levelup", 0.9, 0.0)

    def on_enemy_killed(self, e):
        p = self.player
        self.kills += 1
        self.combo.add_kill()
        # KAN KİTABI: her öldürmede bir miktar can geri kazanılır.
        if p.kill_heal > 0:
            p.heal(p.kill_heal)
        # RUH HASADI (cehennem eşyası): can + yığılan hasar bonusu
        if p.soul_harvest > 0:
            p.heal(2.0 * p.soul_harvest)
            p.soul_stacks = min(p.soul_stacks + 1, 4 + 4 * p.soul_harvest)
            p.soul_timer = 5.0
        p.register_kill_for_frenzy()
        combo_mult = self.combo.multiplier()
        coin_gain = int(round(e.coin * p.eff_coin_mult()))
        xp_gain = e.xp
        # Altın ARTIK ölüm anında verilmiyor: yere düşen parayı toplaman gerek.
        # (Kazanç, Pickup "coin" toplandığında işleniyor.)
        self.score += int(e.score * combo_mult)
        self.pickups.append(Pickup(e.x + random.uniform(-8, 8), e.y + random.uniform(-8, 8), "coin", coin_gain))
        self.pickups.append(Pickup(e.x + random.uniform(-8, 8), e.y + random.uniform(-8, 8), "xp", xp_gain))
        if random.random() < 0.04 and p.hp < p.max_hp * 0.9:
            self.pickups.append(Pickup(e.x, e.y, "heart", 26))
        if self.combo.count > 0 and self.combo.count % 10 == 0:
            self.fx.popup(p.x, p.y - 50, f"COMBO x{self.combo.count}!", CYAN, 24, life=1.0)
        if self.combo.count >= 30 and self.ach:
            self.ach.unlock("combo30")
        if self.kills == 1 and self.ach:
            self.ach.unlock("first_kill")
        if self.kills >= 250 and self.ach:
            self.ach.unlock("massacre")
        if getattr(e, "is_boss", False):
            self.save.data["stats"]["bosses"] = self.save.data["stats"].get("bosses", 0) + 1
            if self.ach:
                self.ach.unlock("boss")

    def update(self, dt, input_state):
        if self.game_over or self.pending_levelups > 0:
            self.fx.update(dt)
            return

        p = self.player
        self.run_time += dt
        if self.time_stop > 0:
            self.time_stop = max(0.0, self.time_stop - dt)
        p.update(dt, input_state, self.fx)
        self.update_camera(dt)
        # Skin yeteneği: süresi dolduysa kendiliğinden çalışır (ve zamanı durdurabilir).
        self.update_skin_ult(dt)
        # DİKKAT: 'frozen' yetenek çalıştıktan SONRA hesaplanır; yoksa yeteneğin
        # başlattığı donma bir kare geç işlerdi.
        frozen = self.time_stop > 0

        aim_dx, aim_dy = norm_dir(p.x, p.y, input_state.get("aim_x", p.x), input_state.get("aim_y", p.y - 1))
        p.set_aim(aim_dx, aim_dy)

        if input_state.get("mouse_down") and p.try_attack():
            self.do_player_attack(*p.aim_dir)
        if input_state.get("bonk_pressed") and p.try_bonk():
            self.do_bonk()
        if input_state.get("dash_pressed"):
            if p.try_dash(self.fx) and p.dash_slow_level > 0:
                # ZAMAN KİTABI: dash çevredeki düşmanları kısa süre yavaşlatır.
                rad = 150 + 30 * p.dash_slow_level
                dur = 1.4 + 0.6 * p.dash_slow_level
                mult = max(0.35, 1.0 - 0.25 * p.dash_slow_level)
                for e in self.enemies:
                    if e.alive and dist(e.x, e.y, p.x, p.y) < rad and hasattr(e, "apply_slow"):
                        e.apply_slow(mult, dur)
                for b in self.bosses:
                    if b.alive and dist(b.x, b.y, p.x, p.y) < rad and hasattr(b, "apply_slow"):
                        b.apply_slow(mult, dur)
                self.fx.shockwave(p.x, p.y, rad, (150, 210, 255), 0.30, 3)

        if p.orbit_level > 0:
            p.orbit_angle += dt * 3.2
            n = p.orbit_level
            orad = 58
            for i in range(n):
                ang = p.orbit_angle + i * math.tau / n
                ox = p.x + math.cos(ang) * orad
                oy = p.y + math.sin(ang) * orad
                for e in self._all_targets():
                    if not e.alive:
                        continue
                    if dist(ox, oy, e.x, e.y) < e.radius + 10:
                        dmg = p.eff_dmg() * 0.45 * dt * 6
                        died = e.take_damage(dmg, False, self.fx)
                        if died:
                            self.on_enemy_killed(e)

        if p.storm_level > 0:
            p.storm_timer -= dt
            if p.storm_timer <= 0:
                p.storm_timer = max(1.0, 2.6 - p.storm_level * 0.4)
                self.do_storm_strike()

        # ---- patron mantığı ----
        if self.waves.boss_pending and not self.waves.boss_active:
            self.waves.boss_pending = False
            self.waves.boss_active = True
            wave = self.waves.wave
            n_boss = boss_count_for_wave(wave)
            hp_mult = boss_hp_share(n_boss)
            self.enemies.clear()
            self.bosses = []
            hell = self.biome == "hell"
            order = HELL_BOSS_ORDER if hell else BOSS_ORDER
            for i in range(n_boss):
                kind = order[self.waves.boss_idx % len(order)]
                self.waves.boss_idx += 1
                # Birden fazla patron varsa arenanın üst kısmına yatayda yayılırlar.
                cam = self.cam_rect()
                if n_boss == 1:
                    bx = cam.centerx
                else:
                    span = min(cam.width - 220, 220 * (n_boss - 1))
                    bx = cam.centerx - span / 2 + span * i / max(1, n_boss - 1)
                by = cam.top + 110
                bx = clamp(bx, ARENA_RECT.left + 90, ARENA_RECT.right - 90)
                by = clamp(by, ARENA_RECT.top + 90, ARENA_RECT.bottom - 90)
                self.bosses.append(Boss(kind, bx, by, hp_mult, 1.0, wave, hellish=hell))
            # Patron canı oyuncunun gücüne göre ölçeklenir: dövüş, oyuncu ne
            # kadar güçlenirse güçlensin benzer uzunlukta sürsün.
            scale_bosses_to_player(self.bosses, p)
            self.fx.do_flash((255, 60, 50), 0.4)
            if n_boss > 1:
                self.fx.popup(self.cam_rect().centerx, self.cam_rect().top + 60,
                              f"{n_boss} PATRON!", (255, 90, 70), 34, life=1.6)
            sfx("boss", 1.0, 0.0)

        if self.bosses:
            for b in list(self.bosses):
                if b.alive:
                    if not frozen:
                        b.update(dt, p, self.fx, self.enemy_projectiles, self.hazards, self.on_enemy_killed)
                    if b.summoned_enemies:
                        self.enemies.extend(b.summoned_enemies)
                        b.summoned_enemies = []
                else:
                    self.on_enemy_killed(b)
                    # Devrilen her patron yerine bir SANDIK bırakır.
                    self.spawn_boss_chest(b)
                    self.bosses.remove(b)
            if not self.bosses:
                # Tüm patronlar devrildi — dalga normal akışına döner ve
                # zaferin ardından kısa bir yoğunluk penceresi açılır.
                beaten_wave = self.waves.wave
                self.waves.boss_active = False
                self.waves._begin_wave(self.waves.wave + 1, self.score)
                self.waves.announce_timer = 2.5
                self.waves.announce_text = (f"CEHENNEM — DALGA {self.waves.wave}"
                                            if self.biome == "hell"
                                            else f"DALGA {self.waves.wave} — YOĞUNLUK!")
                sfx("wave", 0.6, 0.0)
                if self.ach and self.biome != "hell":
                    self.ach.unlock({5: "wave5", 10: "wave10", 15: "wave15",
                                     20: "wave20"}.get(beaten_wave, ""))
                if self.ach and self.biome == "hell":
                    self.ach.unlock("hell_boss")
                # Patron ödülü: bir sonraki dalgaya girerken market portalı açılır.
                if self.market_portal is None:
                    self.spawn_market_portal()
                # 1. HARİTANIN FİNALİ: 25. dalga patronu devrildiğinde
                # CEHENNEM KAPISI açılır ve oyuncu ölene ya da girene kadar
                # haritada kalır.
                if (self.biome != "hell" and beaten_wave >= HELL_PORTAL_WAVE
                        and self.hell_portal is None):
                    self.open_hell_portal()

        if not frozen:
            for hz in list(self.hazards):
                hz.update(dt, self)
        self.hazards = [h for h in self.hazards if h.alive]

        if not frozen:
            for e in list(self.enemies):
                e.update(dt, p, self.fx, self.enemy_projectiles, self.on_enemy_killed)
        self.enemies = [e for e in self.enemies if e.alive]
        if not frozen:
            # Kaçan oyuncunun arkasında kalan yaratıklar önüne ışınlanır.
            self.reposition_stragglers(dt)
        # Patron sandıkları ve sandıktan çıkan otomatik silahlar
        self.update_chests(dt)
        if not frozen:
            self.update_boss_weapons(dt)

        for proj in list(self.enemy_projectiles):
            if not frozen:
                proj.update(dt)
            if proj.alive and p.alive and not frozen:
                if dist(proj.x, proj.y, p.x, p.y) < proj.r + p.radius:
                    owner = getattr(proj, "owner", None)
                    if owner is not None and hasattr(owner, "hit_player"):
                        # Patron mermisi: hasarın yanında imza etkisini de taşır.
                        owner.hit_player(p, proj.dmg, self.fx, proj.x, proj.y)
                    else:
                        p.take_damage(proj.dmg, self.fx, proj.x, proj.y, "mermi")
                    proj.alive = False
        self.enemy_projectiles = [pr for pr in self.enemy_projectiles if pr.alive]

        for proj in list(self.player_projectiles):
            if proj.homing > 0 and proj.alive:
                nearest, nd = None, 1e9
                for e in self.enemies:
                    if not e.alive:
                        continue
                    dd = dist(proj.x, proj.y, e.x, e.y)
                    if dd < nd:
                        nd = dd
                        nearest = e
                if nearest is not None:
                    proj.steer_toward(nearest.x, nearest.y, dt)
            proj.update(dt)
            proj.emit(self.fx, dt)
            if proj.alive:
                for e in self._all_targets():
                    if not e.alive or id(e) in proj.hit_set:
                        continue
                    e_hit_r = getattr(e, "hit_r", e.radius)
                    # Merminin ucu hedefin görünen alanına biraz bile değse isabet sayılsın;
                    # kıl payı ıskalar/es geçmeler olmasın diye küçük bir tolerans payı var.
                    forgive = max(3.0, proj.r * 0.35)
                    if dist(proj.x, proj.y, e.x, e.y) < proj.r + e_hit_r + forgive:
                        proj.hit_set.add(id(e))
                        crit = random.random() < proj.crit_chance
                        if crit:
                            p.run_crits += 1
                        dmg = proj.dmg * (proj.crit_mult if crit else 1.0)
                        # PATRON AVCISI KİTABI: patron ve elitlere ek hasar
                        if p.boss_hunter > 0 and (getattr(e, "is_boss", False) or e.kind == "elite"):
                            dmg *= (1.0 + 0.30 * p.boss_hunter)
                        dmg = self._apply_execute(p, e, dmg)
                        kx, ky = norm_dir(p.x, p.y, e.x, e.y)
                        kb = 12 if getattr(e, "is_boss", False) else 90
                        died = e.take_damage(dmg, crit, self.fx, kx * kb, ky * kb)
                        if p.fire_level > 0 and hasattr(e, "apply_burn"):
                            e.apply_burn(4 * p.fire_level, 2.2 + p.fire_level * 0.5)
                        # KUTSAL ALEV (cehennem eşyası): çok daha ağır bir yanık
                        if p.holy_flame > 0 and hasattr(e, "apply_burn"):
                            e.apply_burn(18 * p.holy_flame, 3.0 + p.holy_flame * 0.6)
                        if p.ice_level > 0 and hasattr(e, "apply_slow"):
                            e.apply_slow(max(0.3, 1 - 0.18 * p.ice_level), 1.4 + p.ice_level * 0.3)
                        # ZEHİR KİTABI: bulaştığı düşman ölene kadar sürer ve her
                        # isabette üstüne biner. Seviye başına saniyede 3 hasar.
                        if p.poison_level > 0 and hasattr(e, "apply_poison"):
                            e.apply_poison(3.0 * p.poison_level)
                        if p.vamp_level > 0:
                            p.lifesteal(dmg * 0.02 * p.vamp_level)
                        self.fx.burst((proj.x + e.x) / 2, (proj.y + e.y) / 2,
                                      (255, 230, 150) if crit else proj.color, n=4, speed=90, life=0.25, r=2.2)
                        if died:
                            self.on_enemy_killed(e)
                            self._explosion_splash(e.x, e.y, proj.dmg, exclude_id=id(e))
                        proj.hits_left -= 1
                        if proj.hits_left <= 0:
                            proj.alive = False
                            break
        self.player_projectiles = [pr for pr in self.player_projectiles if pr.alive]

        for pu in list(self.pickups):
            pu.update(dt, p)
            if pu.collected:
                if pu.kind == "xp":
                    lv = p.gain_xp(pu.value)
                    if lv > 0:
                        self.pending_levelups += lv
                        self.fx.popup(p.x, p.y - 40, "SEVİYE ATLADI!", GOLD, 20, life=1.0)
                        self.fx.ring(p.x, p.y, GOLD, n=18, speed=200, life=0.5, r=3)
                        sfx("levelup", 1.0, 0.0)
                        if p.level >= 10 and self.ach:
                            self.ach.unlock("lvl10")
                elif pu.kind == "heart":
                    p.heal(pu.value)
                    self.fx.popup(pu.x, pu.y - 10, f"+{pu.value}", (255, 120, 140), 15, life=0.5)
                    sfx("heart", 0.7, 0.05)
                else:
                    # Altın yalnızca burada, yani parayı gerçekten TOPLAYINCA kazanılır.
                    self.coins_earned += pu.value
                    self.gold_wallet += pu.value
                    self.fx.popup(pu.x, pu.y - 10, f"+{pu.value}", GOLD, 14, life=0.5)
                    sfx("coin", 0.4, 0.02)
        self.pickups = [pu for pu in self.pickups if not (pu.collected or pu.dead)]

        wave_changed = self.waves.update(0.0 if frozen else dt, self.enemies, self.wave_hp_mult,
                                         self.waves.boss_active, total_score=self.score)
        if wave_changed:
            sfx("wave", 0.6, 0.0)
            if self.waves.wave % 5 == 0 and self.ach:
                self.ach.unlock({5: "wave5", 10: "wave10", 15: "wave15", 20: "wave20"}.get(self.waves.wave, ""))
            if self.diff == "nightmare" and self.waves.wave >= 5 and self.ach:
                self.ach.unlock("nightmare")
        if wave_changed and self.waves.wave % 2 == 0 and self.market_portal is None and not self.waves.boss_pending:
            self.spawn_market_portal()

        if self.coins_earned >= 1500 and self.ach:
            self.ach.unlock("rich")
        if p.dash_count >= 40 and self.ach:
            self.ach.unlock("dasher")

        # --- CEHENNEM KAPISI: ölene ya da girene kadar yerinde durur ---
        if self.hell_portal is not None:
            self.hell_portal.update(dt)
            if (p.alive and input_state.get("use_pressed")
                    and self.hell_portal.in_range(p)):
                self.enter_hell()

        if self.market_portal is not None and p.alive:
            if dist(p.x, p.y, self.market_portal.x, self.market_portal.y) < p.radius + self.market_portal.r:
                self.want_open_shop = True
                self.market_portal = None
            else:
                self.market_portal.update(dt)

        self.combo.update(dt)
        self.fx.update(dt)
        if self.ach:
            self.ach.update(dt)

        if not p.alive and not self.game_over:
            self.death_cause = p.last_hit_by
            self.finish_run()

    def start_levelup_choice(self):
        # Yalnızca KİTAP MARKETİ'nden açılmış kitaplar çıkabilir. Kilitli bir
        # kitap seviye atlama ekranında asla görünmez.
        pool = self.save.unlocked_books()
        if not pool:
            # EMNİYET: Bütün kitaplar kilitli olduğu için ilk koşularda hiç açık
            # kitap olmayabilir. Seviye atlama ekranı boş kalırsa oyun kilitlenir;
            # bu yüzden hiç kitabı olmayan oyuncuya TEMEL kitaplar gösterilir.
            pool = [b for b in BOOKS if b["key"] in STARTER_BOOKS] or list(BOOKS)
        weights = [3 if u.get("rare") else 10 for u in pool]
        chosen, chosen_keys, attempts = [], set(), 0
        want = min(3, len(pool))
        while len(chosen) < want and attempts < 80:
            attempts += 1
            pick = random.choices(pool, weights=weights, k=1)[0]
            if pick["key"] not in chosen_keys:
                chosen.append(pick)
                chosen_keys.add(pick["key"])
        self.levelup_choices = chosen

    def choose_levelup(self, key):
        self.player.apply_run_upgrade(key)
        self.pending_levelups -= 1
        self.fx.ring(self.player.x, self.player.y, GREEN, n=14, speed=180, life=0.4, r=3)
        sfx("buy", 0.8, 0.0)
        if self.pending_levelups > 0:
            self.start_levelup_choice()
        else:
            self.levelup_choices = []

    def finish_run(self):
        self.game_over = True
        gems = int(self.coins_earned * 0.12)
        self.save.add_gems(gems)
        st = self.save.data["stats"]
        st["runs"] = st.get("runs", 0) + 1
        st["best_score"] = max(st.get("best_score", 0), int(self.score))
        st["total_kills"] = st.get("total_kills", 0) + int(self.kills)
        st["total_time"] = st.get("total_time", 0.0) + self.run_time
        st["best_wave"] = max(st.get("best_wave", 0), self.waves.wave)
        # --- kitap görevleri için izlenen istatistikler ---
        p = self.player
        st["best_run_kills"] = max(st.get("best_run_kills", 0), int(self.kills))
        st["total_healed"] = st.get("total_healed", 0.0) + float(p.run_healed)
        st["best_run_heal"] = max(st.get("best_run_heal", 0.0), float(p.run_healed))
        st["total_crits"] = st.get("total_crits", 0) + int(p.run_crits)
        st["total_bonks"] = st.get("total_bonks", 0) + int(p.run_bonks)
        st["total_dashes"] = st.get("total_dashes", 0) + int(p.dash_count)
        st["best_combo"] = max(st.get("best_combo", 0), int(self.combo.best))
        st["best_run_dashes"] = max(st.get("best_run_dashes", 0), int(p.dash_count))
        st["total_shots"] = st.get("total_shots", 0) + int(p.run_shots)
        st["best_run_shots"] = max(st.get("best_run_shots", 0), int(p.run_shots))
        st["total_lifesteal"] = st.get("total_lifesteal", 0.0) + float(p.run_lifesteal)
        st["total_gold"] = st.get("total_gold", 0) + int(self.coins_earned)
        st["best_run_gold"] = max(st.get("best_run_gold", 0), int(self.coins_earned))
        st["total_bonk_hits"] = st.get("total_bonk_hits", 0) + int(self.bonk_hits)
        # Koşu içi markette hangi eşyanın kaç seviyeye kadar çıkarıldığı: bazı
        # kitaplar "şu eşyayı tavana kadar yükselt" görevini bunun üzerinden ölçer.
        shop_max = st.setdefault("shop_max", {})
        for key, lvl in (p.shop_levels or {}).items():
            if int(lvl) > int(shop_max.get(key, 0)):
                shop_max[key] = int(lvl)
        # Görevi bu koşuda tamamlanan kitapları kalıcı olarak aç.
        self.new_books = self.save.refresh_book_unlocks()
        # Toplam sayaçlara bağlı başarımları tara (Usta Avcı, Sülük, ...).
        if self.ach:
            self.ach.check_stats()
        self.save.save()
        self.gems_earned = gems
        sfx("gameover", 1.0, 0.0)


# =====================================================================
# ARKA PLAN
# =====================================================================

class Background:
    def __init__(self):
        self.gradient = self._build_gradient()
        self.dust = []
        for _ in range(70):
            self.dust.append({
                "x": random.uniform(0, VIRTUAL_W), "y": random.uniform(0, VIRTUAL_H),
                "r": random.uniform(1, 2.6), "spd": random.uniform(6, 22),
                "a": random.uniform(30, 90), "phase": random.uniform(0, math.tau),
            })
        self.t = 0.0

    def _build_gradient(self):
        surf = pygame.Surface((VIRTUAL_W, VIRTUAL_H))
        for y in range(VIRTUAL_H):
            t = y / VIRTUAL_H
            col = (int(lerp(BG_TOP[0], BG_BOTTOM[0], t)), int(lerp(BG_TOP[1], BG_BOTTOM[1], t)),
                   int(lerp(BG_TOP[2], BG_BOTTOM[2], t)))
            pygame.draw.line(surf, col, (0, y), (VIRTUAL_W, y))
        return surf

    def update(self, dt):
        self.t += dt
        for d in self.dust:
            d["y"] -= d["spd"] * dt
            d["x"] += math.sin(self.t * 0.5 + d["phase"]) * 6 * dt
            if d["y"] < -10:
                d["y"] = VIRTUAL_H + 10
                d["x"] = random.uniform(0, VIRTUAL_W)

    def draw(self, surf):
        surf.blit(self.gradient, (0, 0))
        step = 64
        grid_surf = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        for x in range(0, VIRTUAL_W, step):
            pygame.draw.line(grid_surf, (255, 255, 255, 6), (x, 0), (x, VIRTUAL_H))
        for y in range(0, VIRTUAL_H, step):
            pygame.draw.line(grid_surf, (255, 255, 255, 6), (0, y), (VIRTUAL_W, y))
        surf.blit(grid_surf, (0, 0))
        for d in self.dust:
            a = int(d["a"] * (0.6 + 0.4 * math.sin(self.t * 2 + d["phase"])))
            blit_disc(surf, d["x"], d["y"], d["r"], (150, 180, 255), max(0, a))
        vg = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        pygame.draw.rect(vg, (0, 0, 0, 90), vg.get_rect())
        pygame.draw.rect(vg, (0, 0, 0, 0), vg.get_rect().inflate(-220, -160), border_radius=140)
        surf.blit(vg, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)


# =====================================================================
# EKRAN / ÖLÇEKLEME
# =====================================================================

class Display:
    def __init__(self, save):
        self.save = save
        self.fullscreen = bool(save.data.get("settings", {}).get("fullscreen", False))
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((VIRTUAL_W, VIRTUAL_H), pygame.RESIZABLE)
        pygame.display.set_caption(f"{GAME_TITLE}  v{GAME_VERSION}")
        self.canvas = pygame.Surface((VIRTUAL_W, VIRTUAL_H)).convert()
        self.scale = 1.0
        self.offset = (0, 0)
        self.out_size = (VIRTUAL_W, VIRTUAL_H)
        self._compute_scale()

    def _compute_scale(self):
        sw, sh = self.screen.get_size()
        sw, sh = max(sw, 1), max(sh, 1)
        scale = max(min(sw / VIRTUAL_W, sh / VIRTUAL_H), 0.1)
        self.scale = scale
        out_w, out_h = int(VIRTUAL_W * scale), int(VIRTUAL_H * scale)
        self.offset = ((sw - out_w) // 2, (sh - out_h) // 2)
        self.out_size = (out_w, out_h)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        try:
            if self.fullscreen:
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                self.screen = pygame.display.set_mode((VIRTUAL_W, VIRTUAL_H), pygame.RESIZABLE)
        except Exception:
            self.fullscreen = not self.fullscreen
        self.save.data.setdefault("settings", {})["fullscreen"] = self.fullscreen
        self.save.save()
        self._compute_scale()

    def handle_resize(self, size):
        if not self.fullscreen:
            try:
                self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
            except Exception:
                pass
        self._compute_scale()

    def present(self):
        if abs(self.scale - 1.0) < 1e-3 and self.offset == (0, 0):
            self.screen.blit(self.canvas, (0, 0))
        else:
            self.screen.fill((0, 0, 0))
            scaled = pygame.transform.smoothscale(self.canvas, self.out_size)
            self.screen.blit(scaled, self.offset)
        pygame.display.flip()

    def virtual_mouse(self):
        mx, my = pygame.mouse.get_pos()
        vx = (mx - self.offset[0]) / self.scale if self.scale else 0
        vy = (my - self.offset[1]) / self.scale if self.scale else 0
        return (vx, vy)


# =====================================================================
# DÜNYA ZEMİNİ  ·  KÜÇÜK HARİTA
# ---------------------------------------------------------------------
# Zemin, kameranın gördüğü dikdörtgen kadar çizilir. Dünya 3x3 hücreden
# oluştuğu için hücre sınırları daha kalın çizgiyle belirtilir; oyuncu
# haritanın neresinde olduğunu bir bakışta anlar.
# =====================================================================

# Her bölgenin (normal arena / cehennem) kendi zemin paleti var.
BIOME_STYLE = {
    "arena": {
        "top": (18, 20, 34), "bottom": (10, 11, 20),
        "grid": (255, 255, 255, 7), "cell": (120, 150, 255, 26),
        "decal": (90, 120, 200), "wall": (92, 104, 150),
        "name": "ARENA",
    },
    "hell": {
        "top": (48, 14, 16), "bottom": (16, 6, 10),
        "grid": (255, 140, 90, 9), "cell": (255, 110, 70, 34),
        "decal": (190, 70, 45), "wall": (210, 90, 60),
        "name": "CEHENNEM",
    },
}

_FLOOR_CACHE = {}


def _build_floor(biome):
    """Bütün dünyanın zeminini BİR KEZ çizip saklar.

    Zemin (degrade + lekeler + ızgara + 3x3 hücre sınırları + duvar) her
    karede yeniden çizilirse pahalıya patlıyor. Bölge başına tek sefer
    hazırlanıp her karede yalnızca kameranın gördüğü parça kopyalanıyor.
    """
    st = BIOME_STYLE.get(biome, BIOME_STYLE["arena"])
    surf = pygame.Surface((ARENA_RECT.w, ARENA_RECT.h)).convert()

    # --- dikey degrade ---
    for y in range(ARENA_RECT.h):
        k = y / max(1, ARENA_RECT.h - 1)
        col = (int(lerp(st["top"][0], st["bottom"][0], k)),
               int(lerp(st["top"][1], st["bottom"][1], k)),
               int(lerp(st["top"][2], st["bottom"][2], k)))
        pygame.draw.line(surf, col, (0, y), (ARENA_RECT.w, y))

    # --- zemin lekeleri ---
    rnd = random.Random(sum(ord(c) for c in biome) * 7919)
    for _ in range(420):
        dx = rnd.uniform(0, ARENA_RECT.w)
        dy = rnd.uniform(0, ARENA_RECT.h)
        dr = rnd.uniform(8, 44)
        blit_disc(surf, dx, dy, dr, st["decal"], int(rnd.uniform(10, 30)))

    # --- ince ızgara + 3x3 hücre sınırları ---
    ov = pygame.Surface((ARENA_RECT.w, ARENA_RECT.h), pygame.SRCALPHA)
    step = 64
    for x in range(0, ARENA_RECT.w + 1, step):
        pygame.draw.line(ov, st["grid"], (x, 0), (x, ARENA_RECT.h))
    for y in range(0, ARENA_RECT.h + 1, step):
        pygame.draw.line(ov, st["grid"], (0, y), (ARENA_RECT.w, y))
    for i in range(1, WORLD_TILES_X):
        x = VIEW_RECT.w * i
        pygame.draw.line(ov, st["cell"], (x, 0), (x, ARENA_RECT.h), 3)
    for j in range(1, WORLD_TILES_Y):
        y = VIEW_RECT.h * j
        pygame.draw.line(ov, st["cell"], (0, y), (ARENA_RECT.w, y), 3)
    surf.blit(ov, (0, 0))

    # --- ÇIKILMAZ DÜNYA DUVARI ---
    # İçeriye doğru bir bant: koyu dolgu + eğik uyarı şeritleri + parlak kenar.
    # Oyuncu dünyanın bittiği yeri bir bakışta görsün.
    band = 20
    wcol = st["wall"]
    wall = pygame.Surface((ARENA_RECT.w, ARENA_RECT.h), pygame.SRCALPHA)
    edges = [pygame.Rect(0, 0, ARENA_RECT.w, band),
             pygame.Rect(0, ARENA_RECT.h - band, ARENA_RECT.w, band),
             pygame.Rect(0, 0, band, ARENA_RECT.h),
             pygame.Rect(ARENA_RECT.w - band, 0, band, ARENA_RECT.h)]
    for r in edges:
        pygame.draw.rect(wall, (*scale_col(wcol, 0.22), 235), r)
    # eğik şeritler
    stripe = (*scale_col(wcol, 0.55), 90)
    for r in edges:
        cl = wall.get_clip()
        wall.set_clip(r)
        x = r.left - r.height
        while x < r.right + r.height:
            pygame.draw.line(wall, stripe, (x, r.bottom), (x + r.height, r.top), 6)
            x += 26
        wall.set_clip(cl)
    # parlak iç kenar + en dış çizgi
    pygame.draw.rect(wall, (*wcol, 255), pygame.Rect(0, 0, ARENA_RECT.w, ARENA_RECT.h), width=3)
    pygame.draw.rect(wall, (*lighten(wcol, 0.25), 200),
                     pygame.Rect(band, band, ARENA_RECT.w - band * 2, ARENA_RECT.h - band * 2),
                     width=2)
    # köşe köşebentleri
    L = 90
    for (cx, cy, dx, dy) in ((0, 0, 1, 1), (ARENA_RECT.w, 0, -1, 1),
                             (0, ARENA_RECT.h, 1, -1), (ARENA_RECT.w, ARENA_RECT.h, -1, -1)):
        pygame.draw.line(wall, (*lighten(wcol, 0.5), 230), (cx, cy + dy * 2),
                         (cx + dx * L, cy + dy * 2), 5)
        pygame.draw.line(wall, (*lighten(wcol, 0.5), 230), (cx + dx * 2, cy),
                         (cx + dx * 2, cy + dy * L), 5)
    surf.blit(wall, (0, 0))
    return surf


def floor_surface(biome):
    surf = _FLOOR_CACHE.get(biome)
    if surf is None:
        surf = _build_floor(biome)
        _FLOOR_CACHE[biome] = surf
    return surf


def draw_world_floor(world, cam, biome, t):
    """Kameranın gördüğü zemin parçasını dünya yüzeyine kopyalar."""
    world.blit(floor_surface(biome), cam.topleft, cam)


_VIGNETTE = None


def view_vignette():
    global _VIGNETTE
    if _VIGNETTE is None:
        vg = pygame.Surface(VIEW_RECT.size, pygame.SRCALPHA)
        pygame.draw.rect(vg, (0, 0, 0, 80), vg.get_rect())
        pygame.draw.rect(vg, (0, 0, 0, 0), vg.get_rect().inflate(-240, -180), border_radius=150)
        _VIGNETTE = vg
    return _VIGNETTE


def draw_minimap(surf, run, t):
    """Sağ üstteki küçük harita.

    Dünyanın tamamını, kameranın gördüğü çerçeveyi, düşmanları, patronları,
    portalları ve oyuncuyu gösterir.
    """
    st = BIOME_STYLE.get(run.biome, BIOME_STYLE["arena"])
    mw, mh = 196, int(196 * ARENA_RECT.h / ARENA_RECT.w)
    rect = pygame.Rect(VIRTUAL_W - mw - 16, ARENA_MARGIN_TOP + 10, mw, mh)

    bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(bg, (8, 9, 16, 210), bg.get_rect(), border_radius=8)
    surf.blit(bg, rect.topleft)

    sx = rect.w / ARENA_RECT.w
    sy = rect.h / ARENA_RECT.h

    def mp(x, y):
        return (rect.x + (x - ARENA_RECT.left) * sx, rect.y + (y - ARENA_RECT.top) * sy)

    # 3x3 hücre çizgileri
    for i in range(1, WORLD_TILES_X):
        x = rect.x + VIEW_RECT.w * i * sx
        pygame.draw.line(surf, (*st["wall"], 90), (x, rect.y + 2), (x, rect.bottom - 2), 1)
    for j in range(1, WORLD_TILES_Y):
        y = rect.y + VIEW_RECT.h * j * sy
        pygame.draw.line(surf, (*st["wall"], 90), (rect.x + 2, y), (rect.right - 2, y), 1)

    # toplanabilirler (çok soluk)
    for pu in run.pickups:
        if pu.kind == "coin":
            px, py = mp(pu.x, pu.y)
            surf.set_at((int(px), int(py)), (150, 130, 60))

    # düşmanlar
    for e in run.enemies:
        if not e.alive:
            continue
        px, py = mp(e.x, e.y)
        # Cehennem yaratıklarının kendi renkleri var — küçük haritada da onları göster.
        col = getattr(e, "color", None) or ENEMY_COLORS.get(e.kind, RED)
        pygame.draw.circle(surf, col, (int(px), int(py)), 2 if e.kind != "elite" else 3)

    # patronlar
    for b in run.bosses:
        if b.alive and not b.is_hidden():
            px, py = mp(b.x, b.y)
            pulse = 3 + math.sin(t * 6) * 1.2
            pygame.draw.circle(surf, (255, 90, 80), (int(px), int(py)), int(4 + pulse * 0.4))
            pygame.draw.circle(surf, WHITE, (int(px), int(py)), 2)

    # market portalı
    if run.market_portal is not None:
        px, py = mp(run.market_portal.x, run.market_portal.y)
        pygame.draw.circle(surf, GOLD, (int(px), int(py)), 4, 1)
        draw_icon(surf, px, py, "coin", GOLD, 3)

    # cehennem portalı
    if run.hell_portal is not None:
        px, py = mp(run.hell_portal.x, run.hell_portal.y)
        pulse = 0.5 + 0.5 * math.sin(t * 4)
        add_glow(surf, px, py, 22, HELL_PORTAL_COLOR, 0.25 + pulse * 0.25)
        pygame.draw.circle(surf, HELL_PORTAL_COLOR, (int(px), int(py)), 5, 2)

    # kameranın gördüğü alan
    cam = run.cam_rect()
    vr = pygame.Rect(mp(cam.left, cam.top), (cam.w * sx, cam.h * sy))
    pygame.draw.rect(surf, (235, 240, 255), vr, width=1)

    # oyuncu
    p = run.player
    px, py = mp(p.x, p.y)
    pygame.draw.circle(surf, WHITE, (int(px), int(py)), 3)
    pygame.draw.circle(surf, p.skin["color"], (int(px), int(py)), 2)
    ax, ay = p.aim_dir
    pygame.draw.line(surf, WHITE, (px, py), (px + ax * 7, py + ay * 7), 1)

    # çerçeve + etiket
    pygame.draw.rect(surf, st["wall"], rect, width=2, border_radius=8)
    lab = st["name"]
    lw = text_width(lab, 10, True) + 12
    lr = pygame.Rect(rect.x + 6, rect.y - 9, int(lw), 16)
    ls = pygame.Surface(lr.size, pygame.SRCALPHA)
    pygame.draw.rect(ls, (10, 11, 20, 235), ls.get_rect(), border_radius=6)
    surf.blit(ls, lr.topleft)
    draw_text(surf, lab, (lr.centerx, lr.y + 2), 10, st["wall"], bold=True, center=True,
              shadow=False)


def draw_offscreen_markers(surf, run, cam, t):
    """Ekran dışındaki önemli hedefler için kenar okları (patron / portallar)."""
    marks = []
    for b in run.bosses:
        # GÖLGE PERDESİ açıkken patron küçük haritada da, kenar okunda da yoktur.
        if b.alive and not b.is_hidden():
            marks.append((b.x, b.y, (255, 90, 80), "skull"))
    if run.market_portal is not None:
        marks.append((run.market_portal.x, run.market_portal.y, GOLD, "coin"))
    if run.hell_portal is not None:
        marks.append((run.hell_portal.x, run.hell_portal.y, HELL_PORTAL_COLOR, "gem"))
    for (wx, wy, col, icon) in marks:
        if cam.collidepoint(wx, wy):
            continue
        cx, cy = cam.centerx, cam.centery
        dx, dy = wx - cx, wy - cy
        l = math.hypot(dx, dy) or 1.0
        dx, dy = dx / l, dy / l
        ex = clamp(cx + dx * cam.w, cam.left + 30, cam.right - 30)
        ey = clamp(cy + dy * cam.h, cam.top + 30, cam.bottom - 30)
        sx, sy = world_to_screen(ex, ey, cam)
        add_glow(surf, sx, sy, 34, col, 0.28)
        pygame.draw.circle(surf, (12, 13, 22), (int(sx), int(sy)), 13)
        pygame.draw.circle(surf, col, (int(sx), int(sy)), 13, 2)
        draw_icon(surf, sx, sy, icon, col, 7)
        pygame.draw.polygon(surf, col, [(sx + dx * 20, sy + dy * 20),
                                        (sx + dx * 13 - dy * 6, sy + dy * 13 + dx * 6),
                                        (sx + dx * 13 + dy * 6, sy + dy * 13 - dx * 6)])


# =====================================================================
# RUN GÖRSEL ÇİZİMİ
# =====================================================================



# =====================================================================
# YETENEK ÇUBUĞU
# ---------------------------------------------------------------------
# Ekranın altındaki yetenek yuvaları. Her yuva bir tuşu, bir simgeyi ve
# (varsa) canlı bekleme süresini gösterir.
#
# YENİ YETENEK EKLEMEK: aşağıdaki listeye bir sözlük eklemek yeterli.
#   key   : ekranda görünen tuş etiketi
#   name  : yuvanın altındaki kısa ad
#   icon  : draw_icon() simge adı
#   color : yuva rengi
#   cd    : (kalan, toplam) döndüren fonksiyon — bekleme süresi yoksa None
#   lock  : True dönerse yuva kilitli (gri) çizilir — henüz açılmamış yetenekler
# Çubuk genişliği yuva sayısına göre kendiliğinden ortalanır.
# =====================================================================

SKILL_SLOTS = [
    {"key": "SOL TIK", "name": "ATEŞ", "icon": "target", "color": (150, 210, 255),
     "cd": lambda p: (p.atk_timer, p.eff_atk_cd())},
    {"key": "SPACE", "name": "BONK", "icon": "fist", "color": (245, 150, 80),
     "cd": lambda p: (p.bonk_timer, p.eff_bonk_cd())},
    {"key": "SHIFT", "name": "DASH", "icon": "dash", "color": (130, 225, 210),
     "cd": lambda p: (p.dash_cd_timer, p.eff_dash_cd())},
    {"key": "B", "name": "MARKET", "icon": "coin", "color": GOLD, "cd": None},
]

# Yalnızca belirli skinlerde görünen ek yuvalar.
SKILL_SLOT_SMASH = {"key": "SPACE", "name": "EZİCİ", "icon": "skull", "color": (150, 255, 130),
                    "cd": lambda p: (p.smash_timer, RunState.TITAN_SMASH_CD)}


def skill_slots_for(p):
    """Oyuncunun skinine göre gösterilecek yetenek yuvaları."""
    slots = list(SKILL_SLOTS)
    if getattr(p, "titan_smash", 0):
        slots.insert(2, SKILL_SLOT_SMASH)
    # SKİN ÖZEL YETENEĞİ: her skinin kendi yuvası. Tuş etiketi yerine yeteneğin
    # TOPLAM bekleme süresi yazar (örn. "60sn"); yuvanın içindeki sayı ise
    # yeteneğin gelmesine kaç saniye kaldığını gösterir.
    ult = getattr(p, "ult", None)
    if ult:
        slots.append({"key": f"{int(round(ult['cd']))}sn",
                      "name": ult.get("short") or ult["name"].split()[0],
                      "icon": ult.get("icon", "star"),
                      "color": tuple(ult.get("color", GOLD)),
                      "cd": lambda pp: (pp.ult_timer, pp.ult_cd)})
    # PATRON SANDIĞINDAN çıkan otomatik silahlar: her biri kendi yuvasını alır.
    # Tuş etiketi yerine "OTO" yazar — oyuncu bu silahları elle kullanmaz.
    for key in BOSS_WEAPONS_ORDER:
        lvl = p.weapons.get(key, 0)
        if lvl <= 0:
            continue
        w = WEAPON_BY_KEY[key]
        slots.append({
            "key": "OTO",
            "name": w["name"] + (f" {lvl}" if lvl > 1 else ""),
            "icon": w["icon"],
            "color": w["color"],
            "cd": (lambda k, ww, lv: lambda pp: (max(0.0, pp.weapon_timers.get(k, 0.0)),
                                                 weapon_cooldown(ww, lv)))(key, w, lvl),
        })
    return slots


# Yetenek çubuğu boyut kademeleri — duraklatma menüsünden değiştirilir.
SKILL_SCALES = [(0.65, "ÇOK KÜÇÜK"), (0.75, "KÜÇÜK"), (0.85, "NORMAL"),
                (1.0, "BÜYÜK"), (1.15, "ÇOK BÜYÜK")]


def skill_scale_label():
    cur = float(CFG.get("skill_scale", 0.85))
    best = min(SKILL_SCALES, key=lambda it: abs(it[0] - cur))
    return best[1]


def cycle_skill_scale():
    """Bir sonraki boyut kademesine geçer ve seçilen değeri döndürür."""
    cur = float(CFG.get("skill_scale", 0.85))
    idx = min(range(len(SKILL_SCALES)), key=lambda i: abs(SKILL_SCALES[i][0] - cur))
    nxt = SKILL_SCALES[(idx + 1) % len(SKILL_SCALES)][0]
    CFG["skill_scale"] = nxt
    return nxt


def draw_skill_bar(surf, run, t):
    """Ekranın alt ortasında yetenek yuvalarını çizer.

    Yuva boyutu CFG["skill_scale"] ile ölçeklenir; oyuncu duraklatma
    menüsünden küçültüp büyütebilir.
    """
    p = run.player
    slots = skill_slots_for(p)
    n = len(slots)
    k = clamp(float(CFG.get("skill_scale", 0.85)), 0.5, 1.4)
    sw, sh, gap = int(62 * k), int(62 * k), max(5, int(10 * k))
    total = n * sw + (n - 1) * gap
    x0 = VIRTUAL_W / 2 - total / 2
    y0 = VIRTUAL_H - sh - int(30 * k)

    # arka panel
    back = pygame.Rect(int(x0 - 12 * k), int(y0 - 10 * k), int(total + 24 * k), int(sh + 32 * k))
    bs = pygame.Surface(back.size, pygame.SRCALPHA)
    pygame.draw.rect(bs, (10, 11, 20, 188), bs.get_rect(), border_radius=14)
    pygame.draw.rect(bs, (58, 62, 88, 220), bs.get_rect(), width=2, border_radius=14)
    surf.blit(bs, back.topleft)

    for i, sk in enumerate(slots):
        r = pygame.Rect(int(x0 + i * (sw + gap)), int(y0), sw, sh)
        locked = bool(sk.get("lock") and sk["lock"](p))
        col = (86, 90, 112) if locked else sk["color"]

        remain, total_cd = 0.0, 0.0
        if sk.get("cd") and not locked:
            try:
                remain, total_cd = sk["cd"](p)
            except Exception:
                remain, total_cd = 0.0, 0.0
        ready = remain <= 0.001 or total_cd <= 0
        frac = 0.0 if ready else clamp(remain / max(0.0001, total_cd), 0.0, 1.0)

        # yuva zemini
        pygame.draw.rect(surf, (18, 19, 30), r, border_radius=10)
        # bekleme süresi: aşağıdan yukarı dolan karartma
        if frac > 0:
            fill_h = int(r.h * frac)
            cs = pygame.Surface((r.w, fill_h), pygame.SRCALPHA)
            pygame.draw.rect(cs, (6, 7, 14, 200), cs.get_rect())
            surf.blit(cs, (r.x, r.y + r.h - fill_h))
        elif not locked:
            # hazır: hafif nabız
            pulse = 0.18 + 0.10 * math.sin(t * 4 + i)
            gs = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*col, int(255 * pulse)), gs.get_rect(), border_radius=10)
            surf.blit(gs, r.topleft)

        pygame.draw.rect(surf, col if (ready and not locked) else (52, 56, 76), r,
                         width=2, border_radius=10)

        # simge
        icon_col = col if (ready and not locked) else scale_col(col, 0.55)
        draw_icon(surf, r.centerx, r.centery - 4 * k, sk["icon"], icon_col, max(7, int(15 * k)))

        # kalan süre yazısı
        if frac > 0:
            draw_text(surf, f"{remain:.1f}", (r.centerx, r.centery - 8 * k), max(9, int(15 * k)), WHITE,
                      bold=True, center=True)

        # tuş etiketi
        kb = pygame.Rect(r.x + 3, int(r.bottom - 17 * k), r.w - 6, max(9, int(14 * k)))
        pygame.draw.rect(surf, (30, 33, 50) if not locked else (26, 27, 38), kb, border_radius=4)
        draw_text(surf, sk["key"], kb.center, max(6, int(9 * k)), TEXT if not locked else (110, 114, 136),
                  bold=True, center=True, shadow=False)

        # yuva adı
        draw_text(surf, sk["name"], (r.centerx, r.bottom + 4 * k), max(7, int(10 * k)),
                  TEXT_DIM if not locked else (92, 96, 118), center=True, shadow=False)

        if locked:
            pygame.draw.line(surf, (140, 100, 110), (r.x + 8, r.y + 8), (r.right - 8, r.bottom - 8), 2)


# =====================================================================
# İSTATİSTİK PANELİ  (sağ üstteki "⋮" düğmesi)
# ---------------------------------------------------------------------
# Oyuncunun o anki gücünü YÜZDE olarak gösterir. Ölçü birimi "taban oyuncu
# = %100"; yani hasarın iki katına çıkmışsa %200, üç katına çıkmışsa %300
# yazar. Böylece market, kitap, seviye ve skin bonuslarının toplam etkisi
# tek bakışta görülür.
#
# YENİ SATIR EKLEMEK: player_stat_rows() içindeki listeye bir demet eklemek
# yeterli — (simge, etiket, metin, renk, oran).
# =====================================================================

STATS_BTN_W, STATS_BTN_H = 30, 26
STATS_PANEL_W = 336


def stats_button_rect():
    """Sağ üst köşedeki üç nokta düğmesi."""
    return pygame.Rect(VIRTUAL_W - STATS_BTN_W - 10, 8, STATS_BTN_W, STATS_BTN_H)


def stats_panel_rect(n_rows):
    b = stats_button_rect()
    h = 54 + n_rows * 21 + 30
    return pygame.Rect(VIRTUAL_W - STATS_PANEL_W - 10, b.bottom + 6, STATS_PANEL_W, h)


def _pct(v):
    """Oranı yüzdeye çevirir: 1.0 -> "%100", 2.03 -> "%203"."""
    return f"%{int(round(v * 100))}"


def player_stat_rows(p, run):
    """(simge, etiket, değer metni, renk, çubuk oranı) listesi döndürür.

    Çubuk oranı yalnızca görsel: %100 çubuğun yarısını doldurur, %300 ve
    üstü çubuğu tamamen doldurur — böylece tavanı olmayan değerler de
    okunabilir kalır.
    """
    dmg_r = p.eff_dmg() / max(1e-6, BASE_DMG)
    aspd_r = BASE_ATK_CD / max(1e-6, p.eff_atk_cd())
    spd_r = p.eff_speed() / max(1e-6, BASE_SPEED)
    hp_r = p.max_hp / max(1e-6, BASE_MAX_HP)
    pick_r = p.eff_pickup() / max(1e-6, BASE_PICKUP)
    dash_r = BASE_DASH_CD / max(1e-6, p.eff_dash_cd())
    bonk_r = BASE_BONK_CD / max(1e-6, p.eff_bonk_cd())
    shots = 1 + p.multishot_level
    # Taban oyuncunun saniyelik hasarı: yüzdeyi buna göre veriyoruz.
    base_dps = BASE_DMG * (1.0 + 0.05 * (1.6 - 1.0)) / BASE_ATK_CD
    dps = p.estimated_dps()

    rows = [
        ("sword",  "HASAR",           _pct(dmg_r),   (245, 120, 110), dmg_r),
        ("target", "ATIŞ HIZI",       _pct(aspd_r),  (150, 210, 255), aspd_r),
        ("bolt",   "SANİYELİK HASAR", _pct(dps / max(1e-6, base_dps)), (255, 190, 90),
         dps / max(1e-6, base_dps)),
        ("boot",   "HAREKET HIZI",    _pct(spd_r),   (130, 230, 170), spd_r),
        ("heart",  "AZAMİ CAN",       _pct(hp_r),    (235, 120, 150), hp_r),
        ("shield", "ZIRH",            _pct(p.eff_armor()), (160, 180, 220), p.eff_armor() * 3.0),
        ("clover", "KRİTİK ŞANS",     _pct(p.eff_crit_chance()), (230, 220, 120),
         p.eff_crit_chance() * 2.2),
        ("star",   "KRİTİK HASAR",    _pct(p.eff_crit_dmg()), (255, 210, 130),
         p.eff_crit_dmg() / 2.0),
        ("heart",  "CAN ÇALMA",       _pct(0.02 * p.vamp_level), (220, 60, 90),
         0.02 * p.vamp_level * 5.0),
        ("coin",   "ALTIN KAZANCI",   _pct(p.eff_coin_mult()), GOLD, p.eff_coin_mult()),
        ("gem",    "DENEYİM (XP)",    _pct(p.eff_xp_mult()), PURPLE, p.eff_xp_mult()),
        ("magnet", "TOPLAMA MENZİLİ", _pct(pick_r), (150, 220, 255), pick_r),
        ("fist",   "BONK TEMPOSU",    _pct(bonk_r),  (245, 150, 80), bonk_r),
        ("dash",   "DASH TEMPOSU",    _pct(dash_r),  (130, 225, 210), dash_r),
        ("star",   "MERMİ SAYISI",    f"{shots}",    PURPLE, shots / 4.0),
        ("sword",  "DELME",           f"{p.eff_pierce_hits()}", RED,
         p.eff_pierce_hits() / 4.0),
    ]
    if p.eff_regen() > 0:
        rows.append(("heart", "CAN YENİLENME", f"{p.eff_regen():.1f}/sn", GREEN,
                     p.eff_regen() / 10.0))
    if p.frenzy_stacks > 0:
        rows.append(("clover", "ÇILGINLIK", f"x{p.frenzy_stacks}", (255, 200, 80),
                     p.frenzy_stacks / 10.0))
    if p.soul_stacks > 0:
        rows.append(("skull", "RUH YIĞINI", f"x{p.soul_stacks}", (200, 120, 255),
                     p.soul_stacks / 12.0))
    return rows


def draw_stats_panel(surf, run, t):
    """İstatistik panelini çizer ve kapladığı dikdörtgeni döndürür."""
    p = run.player
    rows = player_stat_rows(p, run)
    rect = stats_panel_rect(len(rows))
    panel(surf, rect, bg=(14, 15, 26), edge=(90, 100, 150), alpha=242, radius=14, edge_w=2)

    draw_text(surf, "İSTATİSTİKLER", (rect.centerx, rect.y + 10), 16, GOLD, bold=True, center=True)
    draw_text(surf, "taban oyuncu = %100", (rect.centerx, rect.y + 30), 10, TEXT_DIM,
              center=True, shadow=False)

    y = rect.y + 50
    for (icon, label, value, col, frac) in rows:
        # arka plan çubuğu: %100'ü ortada olacak biçimde ölçeklenir
        bar = pygame.Rect(rect.x + 12, y + 3, rect.w - 24, 15)
        bs = pygame.Surface(bar.size, pygame.SRCALPHA)
        pygame.draw.rect(bs, (255, 255, 255, 12), bs.get_rect(), border_radius=4)
        fill = int(bar.w * clamp(frac / 3.0, 0.0, 1.0))
        if fill > 2:
            pygame.draw.rect(bs, (*col, 62), pygame.Rect(0, 0, fill, bar.h), border_radius=4)
        surf.blit(bs, bar.topleft)
        draw_icon(surf, rect.x + 22, y + 10, icon, col, 7)
        draw_text(surf, label, (rect.x + 34, y + 3), 12, TEXT, shadow=False)
        draw_text(surf, value, (rect.right - 14, y + 2), 13, col, bold=True, right=True,
                  shadow=False)
        y += 21

    draw_text(surf, "TAB / ⋮ ile kapat", (rect.centerx, rect.bottom - 20), 10, TEXT_DIM,
              center=True, shadow=False)
    return rect


def draw_stats_button(surf, run, mouse_pos, t):
    """Sağ üstteki üç nokta düğmesi (açıkken altın renginde yanar)."""
    r = stats_button_rect()
    open_ = getattr(run, "show_stats", False)
    hover = r.collidepoint(mouse_pos) if mouse_pos else False
    bg = (58, 50, 26) if open_ else ((40, 44, 64) if hover else (24, 26, 42))
    pygame.draw.rect(surf, bg, r, border_radius=7)
    pygame.draw.rect(surf, GOLD if (open_ or hover) else PANEL_EDGE, r, width=2, border_radius=7)
    dot = GOLD if (open_ or hover) else (170, 178, 205)
    for i in (-1, 0, 1):
        pygame.draw.circle(surf, dot, (r.centerx, int(r.centery + i * 7)), 2)


def draw_hud(surf, run, t):
    p = run.player
    top = pygame.Rect(0, 0, VIRTUAL_W, ARENA_MARGIN_TOP - 6)
    s = pygame.Surface(top.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (12, 13, 22, 230), top)
    surf.blit(s, (0, 0))
    pygame.draw.line(surf, PANEL_EDGE, (0, top.height), (VIRTUAL_W, top.height), 2)

    hp_rect = pygame.Rect(20, 16, 260, 22)
    frac = clamp(p.hp / p.max_hp, 0, 1)
    hp_col = GREEN if frac > 0.5 else (ORANGE if frac > 0.25 else RED)
    draw_bar(surf, hp_rect, frac, hp_col)
    draw_text(surf, f"{int(p.hp)}/{int(p.max_hp)}", hp_rect.center, 14, WHITE, bold=True, center=True)
    draw_icon(surf, hp_rect.x - 12, hp_rect.centery, "heart", RED, 12)

    xp_rect = pygame.Rect(20, 44, 260, 12)
    draw_bar(surf, xp_rect, p.xp / p.xp_to_next, PURPLE, radius=5)
    draw_text(surf, f"LV {p.level}", (xp_rect.right + 10, xp_rect.centery), 15, PURPLE, bold=True)

    draw_text(surf, f"Altın: {fmt_num(run.gold_wallet)}", (20, 62), 15, GOLD, bold=True)

    # --- PATRON DURUM ETKİLERİ: altının sağında küçük sayaçlar ---
    st_x = 140
    for (act, icon, scol, label) in ((p.burn_t, "flame", (255, 150, 70), "YANIK"),
                                     (p.poison_t, "drop", (150, 240, 120), "ZEHİR"),
                                     (p.slow_t, "snow", (150, 210, 255), "YAVAŞ")):
        if act <= 0:
            continue
        chip = pygame.Rect(st_x, 56, 74, 18)
        cs = pygame.Surface(chip.size, pygame.SRCALPHA)
        pygame.draw.rect(cs, (*scol, 52), cs.get_rect(), border_radius=6)
        pygame.draw.rect(cs, (*scol, 190), cs.get_rect(), width=1, border_radius=6)
        surf.blit(cs, chip.topleft)
        draw_icon(surf, chip.x + 11, chip.centery, icon, scol, 6)
        draw_text(surf, f"{label} {act:0.1f}", (chip.x + 20, chip.y + 3), 10, scol,
                  bold=True, shadow=False)
        st_x += 80

    draw_text(surf, fmt_time(run.run_time), (VIRTUAL_W / 2, 18), 26, TEXT, bold=True, center=True)

    w = run.waves
    if run.bosses:
        n = len([b for b in run.bosses if b.alive])
        label = "PATRON DALGASI" if n <= 1 else f"PATRON DALGASI  ×{n}"
        draw_text(surf, label, (VIRTUAL_W / 2, 41), 15, RED, bold=True, center=True)
        draw_text(surf, "Hepsini devirmeden dalga ilerlemez",
                  (VIRTUAL_W / 2, 61), 11, TEXT_DIM, center=True, shadow=False)
    else:
        # Dalga artık süreyle değil SKORLA ilerliyor; oyuncu hedefe ne kadar
        # kaldığını buradan görür. Yoğunluk penceresi açıkken şerit turuncuya döner.
        surge = w.surge_active()
        next_is_boss = w.is_boss_wave(w.wave + 1)
        hellish = run.biome == "hell"
        wave_col = ORANGE if surge else (GOLD if next_is_boss else
                                         ((255, 130, 80) if hellish else CYAN))
        head = ("CEHENNEM · DALGA " + str(w.wave)) if hellish else f"DALGA {w.wave}"
        if run.hell_portal is not None and not hellish:
            head += "   » CEHENNEM KAPISI AÇIK (E)"
        if next_is_boss:
            head += "   » SONRAKİ: PATRON"
        draw_text(surf, head, (VIRTUAL_W / 2, 40), 14, wave_col, bold=True, center=True)

        gbar = pygame.Rect(VIRTUAL_W / 2 - 120, 52, 240, 7)
        draw_bar(surf, gbar, w.goal_progress(), wave_col,
                 bg=(16, 17, 26), border=(52, 56, 76), radius=4)
        draw_text(surf, f"{fmt_num(min(w.wave_score, w.wave_goal))} / {fmt_num(w.wave_goal)}",
                  (VIRTUAL_W / 2, 64), 10, TEXT_DIM, center=True, shadow=False)

        if surge:
            draw_text(surf, f"YOĞUNLUK {w.surge_timer:0.1f}sn", (gbar.right + 10, 49), 12,
                      ORANGE, bold=True, shadow=False)

    # Sağ üstteki "⋮" istatistik düğmesine yer açmak için biraz sola kaydırıldı.
    rx = VIRTUAL_W - 48
    draw_text(surf, f"Skor  {fmt_num(run.score)}", (rx, 14), 18, TEXT, bold=True, right=True)
    draw_text(surf, f"Öldürme {run.kills}", (rx, 38), 14, TEXT_DIM, right=True)

    icon_x = rx
    badges = []
    if p.fire_level: badges.append(("bolt", ORANGE, p.fire_level))
    if p.ice_level: badges.append(("target", CYAN, p.ice_level))
    if p.shield_charges: badges.append(("shield", (160, 170, 200), p.shield_charges))
    if p.pierce_bonus: badges.append(("sword", RED, p.pierce_bonus))
    if p.multishot_level: badges.append(("star", PURPLE, p.multishot_level))
    if p.explosive_level: badges.append(("star", (240, 110, 60), p.explosive_level))
    if p.vamp_level: badges.append(("heart", (220, 60, 90), p.vamp_level))
    if p.thorns_level: badges.append(("shield", (170, 125, 90), p.thorns_level))
    if p.chain_level: badges.append(("bolt", (120, 200, 255), p.chain_level))
    if p.homing_level: badges.append(("target", (140, 220, 200), p.homing_level))
    if p.orbit_level: badges.append(("orbit", (150, 220, 255), p.orbit_level))
    if p.storm_level: badges.append(("bolt", (190, 215, 255), p.storm_level))
    if p.second_wind_charges: badges.append(("heart", GOLD, p.second_wind_charges))
    if p.holy_flame: badges.append(("cross", (255, 235, 150), p.holy_flame))
    if p.soul_harvest: badges.append(("skull", (200, 120, 255), p.soul_harvest))
    if p.angel_wing: badges.append(("boot", (220, 240, 255), p.angel_wing))
    if p.purgatory_level: badges.append(("shield", (255, 215, 120), p.purgatory_level))
    if p.execute_threshold > 0: badges.append(("sword", GOLD, round(p.execute_threshold * 100)))
    by = 62
    for kind, col, lvl in badges[:14]:
        icon_x -= 26
        draw_icon(surf, icon_x, by, kind, col, 11)
        draw_text(surf, f"x{lvl}", (icon_x + 12, by + 6), 11, col, shadow=False)

    if p.frenzy_stacks > 0:
        draw_text(surf, f"ÇILGINLIK x{p.frenzy_stacks}", (VIRTUAL_W / 2, 96), 14, (255, 200, 80), bold=True, center=True)

    if run.combo.count >= 3:
        pulse = 1 + run.combo.pulse * 0.4
        size = int(20 * pulse)
        col = GOLD if run.combo.count >= 20 else (ORANGE if run.combo.count >= 10 else CYAN)
        draw_text(surf, f"COMBO x{run.combo.count}", (VIRTUAL_W / 2, 76), size, col, bold=True, center=True)
        br = pygame.Rect(VIRTUAL_W / 2 - 80, 94, 160, 5)
        draw_bar(surf, br, run.combo.timer / run.combo.window, col, radius=3)

    if run.waves.announce_timer > 0 and run.waves.announce_text:
        a = clamp(run.waves.announce_timer / 2.2, 0, 1)
        alpha = int(255 * min(1, a * 2))
        scale_t = ease_out_cubic(1 - a)
        size = int(lerp(64, 44, scale_t))
        if "PATRON" in run.waves.announce_text:
            col = RED
        elif "YOĞUNLUK" in run.waves.announce_text:
            col = ORANGE
        else:
            col = CYAN
        draw_text(surf, run.waves.announce_text, (VIRTUAL_W / 2, VIRTUAL_H / 2 - 40), size, col,
                  bold=True, center=True, alpha=alpha)

    if frac < 0.3 and p.alive:
        pulse = (math.sin(t * 8) + 1) / 2
        vg = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        pygame.draw.rect(vg, (180, 0, 0, int(40 * pulse * (1 - frac / 0.3 + 0.3))), vg.get_rect())
        surf.blit(vg, (0, 0))

    if run.fx.flash > 0:
        s = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        s.fill((*run.fx.flash_col, int(run.fx.flash * 130)))
        surf.blit(s, (0, 0))

    if run.ach:
        run.ach.draw(surf)


def draw_run(surf, run, t, aim_pos=None):
    """Koşuyu çizer.

    Bütün dünya nesneleri DÜNYA yüzeyine kendi dünya koordinatlarıyla çizilir;
    sonra yalnızca kameranın gördüğü dikdörtgen ekrana kopyalanır. Böylece
    varlıkların çizim kodu kameradan habersiz kalabiliyor.
    """
    world = world_surface()
    cam = run.cam_rect()
    prev_clip = world.get_clip()
    world.set_clip(cam)

    draw_world_floor(world, cam, run.biome, t)

    if run.hell_portal is not None:
        run.hell_portal.draw(world, t)
    if run.market_portal is not None:
        run.market_portal.draw(world, run.player)
    for hz in run.hazards:
        hz.draw(world, t)
    for pu in run.pickups:
        pu.draw(world, t)
    for ch in run.chests:
        ch.draw(world, t)
    for e in sorted(run.enemies, key=lambda e: e.y):
        e.draw(world, t)
    for b in sorted(run.bosses, key=lambda b: b.y):
        if b.alive:
            b.draw(world, t)
    for proj in run.enemy_projectiles:
        proj.draw(world, t)
    for proj in run.player_projectiles:
        proj.draw(world, t)
    if run.player.alive:
        run.player.draw(world, t)
    run.fx.draw(world)
    run.fx.draw_texts(world)          # hasar sayıları da dünya koordinatında
    world.set_clip(prev_clip)

    surf.blit(world, VIEW_RECT.topleft, cam)

    # kenar karartması (ekran uzayı) — her karede yeniden üretmek pahalı
    # olduğu için tek sefer hazırlanıp saklanıyor.
    surf.blit(view_vignette(), VIEW_RECT.topleft, special_flags=pygame.BLEND_RGBA_SUB)

    draw_offscreen_markers(surf, run, cam, t)
    draw_hud(surf, run, t)
    draw_minimap(surf, run, t)
    draw_skill_bar(surf, run, t)
    # İSTATİSTİK paneli en üstte çizilir: açıkken küçük haritayı örter.
    draw_stats_button(surf, run, aim_pos, t)
    if getattr(run, "show_stats", False):
        draw_stats_panel(surf, run, t)

    if aim_pos and run.player.alive:
        ax, ay = aim_pos
        col = (255, 255, 255, 200)
        s = pygame.Surface((26, 26), pygame.SRCALPHA)
        pygame.draw.circle(s, col, (13, 13), 10, 2)
        pygame.draw.line(s, col, (13, 2), (13, 8), 2)
        pygame.draw.line(s, col, (13, 18), (13, 24), 2)
        pygame.draw.line(s, col, (2, 13), (8, 13), 2)
        pygame.draw.line(s, col, (18, 13), (24, 13), 2)
        surf.blit(s, (ax - 13, ay - 13))


# =====================================================================
# SEVİYE ATLAMA KART SEÇİMİ
# =====================================================================

class LevelUpOverlay:
    def __init__(self):
        self.cards = []

    def rebuild(self, choices):
        self.cards = []
        n = len(choices)
        card_w, card_h = 260, 330
        gap = 30
        total_w = n * card_w + (n - 1) * gap
        start_x = VIRTUAL_W / 2 - total_w / 2
        for i, ch in enumerate(choices):
            rect = pygame.Rect(start_x + i * (card_w + gap), VIRTUAL_H / 2 - card_h / 2, card_w, card_h)
            self.cards.append((rect, ch))

    def draw_and_handle(self, surf, run, mouse_pos, clicked, t):
        overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (5, 6, 12, 190), overlay.get_rect())
        surf.blit(overlay, (0, 0))
        draw_text(surf, "SEVİYE ATLADIN!", (VIRTUAL_W / 2, VIRTUAL_H / 2 - 220), 40, GOLD, bold=True, center=True)
        draw_text(surf, "Kütüphanenden bir kitap seç", (VIRTUAL_W / 2, VIRTUAL_H / 2 - 180), 18, TEXT_DIM, center=True)

        chosen_key = None
        for rect, ch in self.cards:
            hover = rect.collidepoint(mouse_pos)
            bob = math.sin(t * 3 + rect.x * 0.01) * 3
            r2 = rect.move(0, bob)
            rare = ch.get("rare")
            bg = (40, 34, 20) if (hover and rare) else ((34, 38, 60) if hover else (22, 24, 40))
            panel(surf, r2, bg=bg, edge=(ch["color"] if hover else (GOLD_DIM if rare else PANEL_EDGE)),
                  alpha=245, radius=18, edge_w=3)

            if rare:
                lbl = "NADİR KİTAP"
                lw = text_width(lbl, 13, True)
                draw_icon(surf, r2.centerx - lw / 2 - 10, r2.y + 24, "star", GOLD, 6)
                draw_text(surf, lbl, (r2.centerx + 6, r2.y + 18), 13, GOLD, bold=True, center=True, shadow=False)

            draw_book(surf, r2.centerx, r2.y + 86, 96 if hover else 90, ch, t)

            draw_text(surf, ch["name"], (r2.centerx, r2.y + 146), 20, TEXT, bold=True, center=True)
            for i, ln in enumerate(wrap_text(ch["desc"], 14, r2.w - 40)):
                draw_text(surf, ln, (r2.centerx, r2.y + 182 + i * 19), 14, TEXT_DIM, center=True, shadow=False)

            if hover:
                pygame.draw.rect(surf, ch["color"], (r2.x + 16, r2.bottom - 46, r2.w - 32, 32), border_radius=10)
                draw_text(surf, "SEÇ", (r2.centerx, r2.bottom - 30), 16, (10, 10, 16), bold=True, center=True)
            if hover and clicked:
                chosen_key = ch["key"]
        return chosen_key


# =====================================================================
# OYUN-İÇİ MARKET EKRANI
# =====================================================================

class RunShopOverlay:
    def __init__(self):
        self.tab = next(iter(SHOP_CATS))

    def draw_and_handle(self, surf, run, mouse_pos, clicked, t):
        overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (5, 6, 12, 205), overlay.get_rect())
        surf.blit(overlay, (0, 0))
        draw_text(surf, "MARKET", (VIRTUAL_W / 2, 40), 32, GOLD, bold=True, center=True)
        draw_text(surf, f"Altın: {fmt_num(run.gold_wallet)}", (VIRTUAL_W / 2, 70), 17, GOLD, center=True)
        draw_text(surf, "Sadece bu koşu için geçerli — kaybedersen silinir.", (VIRTUAL_W / 2, 89), 12, TEXT_DIM, center=True)

        tabs = list(SHOP_CATS.items())
        tab_w, tab_h, tab_gap = 118, 30, 7
        total_tw = len(tabs) * tab_w + (len(tabs) - 1) * tab_gap
        tx0 = VIRTUAL_W / 2 - total_tw / 2
        ty = 106
        for key, label in tabs:
            i = [k for k, _ in tabs].index(key)
            r = pygame.Rect(tx0 + i * (tab_w + tab_gap), ty, tab_w, tab_h)
            active = (self.tab == key)
            hover = r.collidepoint(mouse_pos)
            bg = (90, 70, 30) if active else ((40, 44, 64) if hover else (24, 26, 42))
            pygame.draw.rect(surf, bg, r, border_radius=8)
            pygame.draw.rect(surf, GOLD if active else PANEL_EDGE, r, width=2, border_radius=8)
            draw_text(surf, label, r.center, 12, TEXT if active else TEXT_DIM, bold=active, center=True, shadow=False)
            if clicked and hover:
                self.tab = key
                sfx("click", 0.5, 0.0)

        offers = [it for it in run.shop_offers if it["cat"] == self.tab]
        cols = 5
        card_w, card_h = 216, 224
        gap_x, gap_y = 12, 12
        total_w = cols * card_w + (cols - 1) * gap_x
        start_x = VIRTUAL_W / 2 - total_w / 2
        start_y = 148
        max_rows_visible = 2

        for i, item in enumerate(offers[:cols * max_rows_visible]):
            col_i, row = i % cols, i // cols
            rect = pygame.Rect(start_x + col_i * (card_w + gap_x), start_y + row * (card_h + gap_y), card_w, card_h)
            unlocked = shop_item_unlocked(item, run.waves.wave, run.biome)
            hover = rect.collidepoint(mouse_pos) and unlocked
            lvl = run.player.shop_levels.get(item["key"], 0)
            maxed = lvl >= item.get("max", 999)
            cost = shop_item_cost(item, lvl)
            affordable = unlocked and not maxed and run.gold_wallet >= cost

            bg = (34, 38, 60) if hover else (20, 22, 36)
            if not unlocked:
                bg = (16, 17, 26)
            edge_col = item["color"] if (hover and affordable) else (GOLD if item.get("legendary") and unlocked else PANEL_EDGE)
            panel(surf, rect, bg=bg, edge=edge_col, alpha=245 if unlocked else 200, radius=16, edge_w=3)

            icon_col = item["color"] if unlocked else (70, 72, 86)
            icon_c = (rect.centerx, rect.y + 46)
            if unlocked and not maxed:
                add_glow(surf, icon_c[0], icon_c[1], 30, icon_col, 0.28 + 0.12 * math.sin(t * 3 + i))
            pygame.draw.circle(surf, OUTLINE, icon_c, 25)
            pygame.draw.circle(surf, icon_col, icon_c, 25, 2)
            draw_icon(surf, icon_c[0], icon_c[1], item["icon"] if unlocked else "shield", icon_col, 19 if unlocked else 15)

            name_col = TEXT if unlocked else TEXT_DIM
            draw_text(surf, item["name"], (rect.centerx, rect.y + 84), 15, name_col, bold=True, center=True)

            if not unlocked:
                if item.get("hell_only"):
                    draw_text(surf, "CEHENNEM'de açılır", (rect.centerx, rect.y + 112), 12,
                              HELL_PORTAL_COLOR2, center=True, shadow=False)
                else:
                    need_wave = TIER_UNLOCK_WAVE.get(item["tier"], 0)
                    draw_text(surf, f"DALGA {need_wave}'te açılır", (rect.centerx, rect.y + 112), 12, GOLD_DIM, center=True, shadow=False)
            else:
                lines = wrap_text(item["desc"], 11, rect.w - 26)
                for j, ln in enumerate(lines[:3]):
                    draw_text(surf, ln, (rect.centerx, rect.y + 108 + j * 14), 11, TEXT_DIM, center=True, shadow=False)
                if not item.get("instant"):
                    if item.get("endless"):
                        draw_text(surf, f"Seviye {lvl}  ·  tavanı yok", (rect.centerx, rect.y + 166),
                                  11, (198, 180, 120), bold=True, center=True, shadow=False)
                    else:
                        draw_text(surf, f"Seviye {lvl}/{item['max']}", (rect.centerx, rect.y + 166), 11, TEXT_DIM, center=True, shadow=False)
                if maxed:
                    draw_text(surf, "MAKSİMUM", (rect.centerx, rect.bottom - 18), 13, GREEN, bold=True, center=True)
                else:
                    pcol = GOLD if affordable else (120, 95, 60)
                    cost_txt = f"{cost}"
                    tw = text_width(cost_txt, 17, True)
                    draw_icon(surf, rect.centerx - tw / 2 - 12, rect.bottom - 24, "coin", pcol, 10)
                    draw_text(surf, cost_txt, (rect.centerx - tw / 2, rect.bottom - 32), 17, pcol, bold=True)
                    if hover and affordable:
                        pygame.draw.rect(surf, item["color"], (rect.x + 12, rect.bottom - 12, rect.w - 24, 3), border_radius=2)
                    if hover and clicked and affordable:
                        run.buy_shop_item(item["key"])

        if not offers:
            draw_text(surf, "Bu kategoride henüz bir şey yok.", (VIRTUAL_W / 2, start_y + 90), 18, TEXT_DIM, center=True)

        btn = Button((VIRTUAL_W / 2 - 130, VIRTUAL_H - 50, 260, 38), "KAPAT (B)", None,
                     color=(70, 76, 100), hover_color=(95, 105, 140))
        btn.update(mouse_pos, 1 / 60)
        btn.draw(surf)
        return btn.rect.collidepoint(mouse_pos) and clicked


# =====================================================================
# UYGULAMA DURUMLARI
# =====================================================================

STATE_MENU = "menu"
STATE_PLAY = "play"
STATE_PAUSE = "pause"
STATE_LEVELUP = "levelup"
STATE_RUN_SHOP = "run_shop"
STATE_GAMEOVER = "gameover"
STATE_SKIN_MARKET = "skin_market"
STATE_SKIN_DETAIL = "skin_detail"
STATE_COSMETIC_MARKET = "cosmetic_market"
STATE_BOOK_MARKET = "book_market"
STATE_LEADERBOARD = "leaderboard"
STATE_WORLD_LB = "world_lb"
STATE_NAME_ENTRY = "name_entry"
STATE_HOW_TO = "howto"
STATE_SETTINGS = "settings"
STATE_ACHIEVEMENTS = "achievements"
STATE_GEM_STORE = "gem_store"

DIFF_ORDER = ["normal", "hard", "nightmare"]
DIFF_LABEL = {"normal": "NORMAL", "hard": "ZOR", "nightmare": "KABUS"}
# Zorluk yalnızca TEMPOyu değiştirir. Dalga hedefleri, düşman canı/hasarı ve
# ödüller her zorlukta AYNIDIR; Kabus'ta düşmanlar çok daha sık geldiği için
# aynı dalgaya daha çabuk ulaşılır.
DIFF_DESC = {"normal": "Sakin tempo. Düşmanlar daha seyrek gelir — dalgalar aynı.",
             "hard": "Standart tempo. Düşmanlar normal sıklıkta gelir.",
             "nightmare": "Yoğun tempo. Aynı dalgalar, çok daha hızlı gelen düşmanlar!"}


class App:
    def __init__(self):
        pygame.init()
        self.save = SaveManager()
        global audio
        audio = AudioManager(self.save.data["settings"])
        self.steam = SteamBridge()
        self.ach = AchievementManager(self.save, self.steam)
        # Eski kayıtlarda hak edilmiş ama hiç açılmamış başarımları aç.
        self.ach.check_stats()
        self.display = Display(self.save)
        self.clock = pygame.time.Clock()
        self.bg = Background()
        self.t = 0.0
        self.state = STATE_MENU
        self.prev_state = STATE_MENU
        self.run = None
        self.levelup_ui = LevelUpOverlay()
        self.shop_ui = RunShopOverlay()
        self.online = OnlineClient(ONLINE_API_URL)
        self.running = True
        self.name_input = self.save.data.get("settings", {}).get("player_name", "")
        self.pending_board_rank = -1
        self.online_submit_status = None
        self.selected_skin = self.save.equipped_skin_id()
        self.diff = self.save.data.get("settings", {}).get("difficulty", "normal")
        self.show_fps = CFG["fps"]
        self.fps_smpl = 60.0
        self.ach_scroll = 0.0
        self.ach_filter = "all"       # all | got | locked | near
        self.ach_detail = None        # tıklanan başarımın anahtarı (detay penceresi)
        self.ach_detail_t = 0.0       # detay penceresi açılma animasyonu (0..1)
        self.skin_scroll = 0.0
        self.detail_skin_id = None
        self.cosmetic_scroll = 0.0
        self.cosmetic_tab = "hat"
        self.book_scroll = 0.0
        self.book_filter = "all"      # all | owned | locked
        self.book_detail = None       # tıklanan kitabın anahtarı (okuma penceresi)
        self.book_detail_t = 0.0      # okuma penceresi açılma animasyonu (0..1)
        self.gem_card_anim = 0.0      # ELMAS MARKETİ kartı hover animasyonu
        self.gem_card_was_hover = False
        self.purchase = PurchaseBridge(self.steam)
        self.gem_msg = None           # satın alma sonucu bildirimi
        self.gem_msg_timer = 0.0
        self.gem_msg_ok = True
        self.store_tab = "gems"       # MAĞAZA sekmesi: gems | skins
        self.menu_buttons = []
        self.build_menu_buttons()
        audio.set_music("menu")

    def build_menu_buttons(self):
        cx = VIRTUAL_W / 2
        # ---- ORTA SÜTUN: OYNA / SKOR TABLOSU / DÜNYA SIRALAMASI (ana akış) ----
        cw, gap = 300, 16
        oyna_h, alt_h = 68, 54
        y0 = 306
        y_oyna = y0
        y_skor = y_oyna + oyna_h + gap
        y_dunya = y_skor + alt_h + gap
        center_bottom = y_dunya + alt_h  # = 306+68+16+54+16+54 = 514

        # ---- SOL SÜTUN (en aşağıda): NASIL OYNANIR (üstte) + BAŞARIMLAR (altta) ----
        side_w, side_h, side_gap = 236, 58, 14
        # Yan sütunlar orta sütunla aynı hizada biter; sağ alttaki GÜNLÜK MARKET
        # kartı 530..702 bandını kullandığı için aralarında 20 px boşluk kalır.
        side_bottom = center_bottom - 4
        y_side2 = side_bottom - side_h        # BAŞARIMLAR (alt)
        y_side1 = y_side2 - side_gap - side_h  # NASIL OYNANIR (üst)
        left_x = cx - cw / 2 - 30 - side_w

        # ---- SAĞ SÜTUN (en aşağıda): SKIN MARKET + KIYAFET MARKET ----
        right_w = side_w
        right_h = side_h
        right_x = cx + cw / 2 + 30
        y_right2 = side_bottom - right_h        # KIYAFET MARKET (alt)
        y_right1 = y_right2 - side_gap - right_h  # SKIN MARKET (orta)
        y_right0 = y_right1 - side_gap - right_h  # KİTAP MARKETİ (üst)

        self.menu_buttons = [
            Button((cx - cw / 2, y_oyna, cw, oyna_h), "OYNA", self.start_run,
                   color=(60, 130, 90), hover_color=(80, 170, 115), text_size=30),
            Button((cx - cw / 2, y_skor, cw, alt_h), "SKOR TABLOSU", lambda: self.goto(STATE_LEADERBOARD),
                   text_size=19),
            Button((cx - cw / 2, y_dunya, cw, alt_h), "DÜNYA SIRALAMASI", lambda: self.goto(STATE_WORLD_LB),
                   color=(50, 80, 120), hover_color=(70, 110, 160), text_size=19),

            Button((left_x, y_side1, side_w, side_h), "NASIL OYNANIR", lambda: self.goto(STATE_HOW_TO),
                   text_size=16),
            Button((left_x, y_side2, side_w, side_h), "BAŞARIMLAR", lambda: self.goto(STATE_ACHIEVEMENTS),
                   color=(90, 70, 110), hover_color=(120, 95, 145), text_size=16),

            Button((right_x, y_right0, right_w, right_h), "KİTAPLIK", lambda: self.goto(STATE_BOOK_MARKET),
                   color=(88, 62, 128), hover_color=(120, 88, 168), text_size=16),
            Button((right_x, y_right1, right_w, right_h), "SKIN MARKET", lambda: self.goto(STATE_SKIN_MARKET),
                   color=(120, 95, 40), hover_color=(160, 125, 55), text_size=16),
            Button((right_x, y_right2, right_w, right_h), "KIYAFET MARKET", lambda: self.goto(STATE_COSMETIC_MARKET),
                   color=(60, 110, 130), hover_color=(80, 145, 170), text_size=16),
        ]

    def goto(self, state):
        self.prev_state = self.state
        self.state = state
        if state == STATE_WORLD_LB:
            self.online.fetch_world_scores_async()
        elif state == STATE_SKIN_MARKET:
            self.skin_scroll = 0.0
        elif state == STATE_COSMETIC_MARKET:
            self.cosmetic_scroll = 0.0
        elif state == STATE_BOOK_MARKET:
            self.book_scroll = 0.0
        elif state == STATE_ACHIEVEMENTS:
            self.ach_scroll = 0.0
            self.ach_detail = None
            # Ekrana girerken toplam sayaçlara bağlı başarımları tara.
            self.ach.check_stats()

    def cycle_diff(self):
        i = DIFF_ORDER.index(self.diff)
        self.diff = DIFF_ORDER[(i + 1) % len(DIFF_ORDER)]
        self.save.data.setdefault("settings", {})["difficulty"] = self.diff
        self.save.save()
        sfx("click", 0.6, 0.0)

    def start_run(self):
        # Kuşanılan skin her zaman KAYITTAN okunur: mağaza, skin market ve
        # menü farklı yerlerden kuşandırabiliyor; tek doğru kaynak kayıttır.
        self.selected_skin = self.save.equipped_skin_id()
        self.run = RunState(self.save, self.selected_skin, self.diff, self.ach)
        self.state = STATE_PLAY
        audio.set_music("battle")

    def gather_input(self, keys_pressed):
        return {
            "left": 1 if (keys_pressed[pygame.K_a] or keys_pressed[pygame.K_LEFT]) else 0,
            "right": 1 if (keys_pressed[pygame.K_d] or keys_pressed[pygame.K_RIGHT]) else 0,
            "up": 1 if (keys_pressed[pygame.K_w] or keys_pressed[pygame.K_UP]) else 0,
            "down": 1 if (keys_pressed[pygame.K_s] or keys_pressed[pygame.K_DOWN]) else 0,
        }

    def run_loop(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 1 / 20)
            self.t += dt
            self.fps_smpl += (self.clock.get_fps() - self.fps_smpl) * 0.05
            mouse_pos = self.display.virtual_mouse()
            clicked = False
            bonk_pressed = False
            dash_pressed = False
            use_pressed = False      # E — portala gir
            stats_pressed = False    # TAB — istatistik paneli
            wheel_y = 0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.display.handle_resize(event.size)
                elif event.type == pygame.MOUSEWHEEL:
                    wheel_y += event.y
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        self.display.toggle_fullscreen()
                    elif event.key == pygame.K_F3:
                        CFG["fps"] = not CFG["fps"]
                    elif event.key == pygame.K_ESCAPE:
                        self.handle_escape()
                    elif event.key == pygame.K_SPACE and self.state == STATE_PLAY:
                        bonk_pressed = True
                    elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT) and self.state == STATE_PLAY:
                        dash_pressed = True
                    elif event.key == pygame.K_e and self.state == STATE_PLAY:
                        use_pressed = True
                    elif event.key == pygame.K_TAB and self.state == STATE_PLAY:
                        stats_pressed = True
                    elif event.key == pygame.K_b and self.state == STATE_PLAY:
                        self.run.open_shop()
                        self.state = STATE_RUN_SHOP
                    elif event.key == pygame.K_b and self.state == STATE_RUN_SHOP:
                        self.state = STATE_PLAY
                    elif self.state == STATE_NAME_ENTRY:
                        self.handle_name_entry_key(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        clicked = True
                    elif event.button == 3 and self.state == STATE_PLAY:
                        dash_pressed = True

            keys = pygame.key.get_pressed()
            mouse_down = pygame.mouse.get_pressed()[0]

            # yön tuşlarıyla (ok tuşları) liste kaydırma — market ekranlarında mouse şart değil
            if self.state in (STATE_SKIN_MARKET, STATE_COSMETIC_MARKET, STATE_BOOK_MARKET,
                              STATE_ACHIEVEMENTS):
                if keys[pygame.K_UP]:
                    wheel_y += 13.0 * dt
                if keys[pygame.K_DOWN]:
                    wheel_y -= 13.0 * dt

            if self.state == STATE_MENU: self.update_menu(dt, mouse_pos, clicked)
            elif self.state == STATE_PLAY: self.update_play(dt, keys, mouse_pos, mouse_down, bonk_pressed,
                                                            dash_pressed, use_pressed, clicked, stats_pressed)
            elif self.state == STATE_PAUSE: self.update_pause(dt, mouse_pos, clicked)
            elif self.state == STATE_LEVELUP: self.update_levelup(dt, mouse_pos, clicked)
            elif self.state == STATE_RUN_SHOP: self.update_run_shop(dt, mouse_pos, clicked)
            elif self.state == STATE_GAMEOVER: self.update_gameover(dt, mouse_pos, clicked)
            elif self.state == STATE_SKIN_MARKET: self.update_skin_market(dt, mouse_pos, clicked, wheel_y)
            elif self.state == STATE_SKIN_DETAIL: self.update_skin_detail(dt, mouse_pos, clicked)
            elif self.state == STATE_COSMETIC_MARKET: self.update_cosmetic_market(dt, mouse_pos, clicked, wheel_y)
            elif self.state == STATE_BOOK_MARKET: self.update_book_market(dt, mouse_pos, clicked, wheel_y)
            elif self.state == STATE_LEADERBOARD: self.update_leaderboard(dt, mouse_pos, clicked)
            elif self.state == STATE_WORLD_LB: self.update_world_leaderboard(dt, mouse_pos, clicked)
            elif self.state == STATE_NAME_ENTRY: self.update_name_entry(dt, mouse_pos, clicked)
            elif self.state == STATE_HOW_TO: self.update_howto(dt, mouse_pos, clicked)
            elif self.state == STATE_ACHIEVEMENTS: self.update_achievements(dt, mouse_pos, clicked, wheel_y)
            elif self.state == STATE_GEM_STORE: self.update_gem_store(dt, mouse_pos, clicked)

            if CFG["fps"]:
                draw_text(self.display.canvas, f"{self.fps_smpl:0.0f} FPS", (VIRTUAL_W - 10, VIRTUAL_H - 10),
                          13, (120, 255, 150), bold=True, right=True, shadow=True)

            audio.update()
            self.steam.run_callbacks()
            self.display.present()

        self.save.save()
        pygame.quit()

    def handle_escape(self):
        if self.state == STATE_PLAY: self.state = STATE_PAUSE
        elif self.state == STATE_PAUSE: self.state = STATE_PLAY
        elif self.state == STATE_RUN_SHOP: self.state = STATE_PLAY
        elif self.state == STATE_SKIN_DETAIL: self.state = STATE_SKIN_MARKET
        elif self.state == STATE_BOOK_MARKET and self.book_detail:
            self.book_detail = None
        elif self.state == STATE_ACHIEVEMENTS and self.ach_detail:
            self.ach_detail = None
        elif self.state in (STATE_SKIN_MARKET, STATE_COSMETIC_MARKET, STATE_BOOK_MARKET,
                            STATE_LEADERBOARD, STATE_WORLD_LB, STATE_GEM_STORE,
                            STATE_HOW_TO, STATE_ACHIEVEMENTS):
            self.state = STATE_MENU
        elif self.state == STATE_GAMEOVER:
            pass

    # ---------------- OYNANIŞ ----------------
    def update_play(self, dt, keys, mouse_pos, mouse_down, bonk_pressed, dash_pressed,
                    use_pressed=False, clicked=False, stats_pressed=False):
        # --- İSTATİSTİK paneli (sağ üstteki "⋮") ---
        # Panelin üstündeyken SOL TIK ateş etmemeli; yoksa düğmeye basarken
        # oyuncu boşluğa ateş ediyor ve panel de açılıp kapanıp duruyordu.
        btn = stats_button_rect()
        over_ui = btn.collidepoint(mouse_pos)
        if self.run.show_stats:
            rows = len(player_stat_rows(self.run.player, self.run))
            over_ui = over_ui or stats_panel_rect(rows).collidepoint(mouse_pos)
        if stats_pressed or (clicked and btn.collidepoint(mouse_pos)):
            self.run.show_stats = not self.run.show_stats
            sfx("click", 0.5, 0.0)
        if over_ui:
            mouse_down = False

        input_state = self.gather_input(keys)
        input_state["mouse_down"] = mouse_down
        input_state["bonk_pressed"] = bonk_pressed
        input_state["dash_pressed"] = dash_pressed
        input_state["use_pressed"] = use_pressed
        # Fare EKRAN koordinatında gelir; nişan DÜNYA koordinatına çevrilir.
        aim_wx, aim_wy = self.run.screen_to_world(mouse_pos[0], mouse_pos[1])
        input_state["aim_x"] = aim_wx
        input_state["aim_y"] = aim_wy
        self.run.update(dt, input_state)
        self.bg.update(dt * 0.4)

        offset = self.run.fx.get_shake_offset()
        canvas = self.display.canvas
        self.bg.draw(canvas)
        tmp = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        draw_run(tmp, self.run, self.t, aim_pos=mouse_pos)
        canvas.blit(tmp, offset)

        if self.run.want_open_shop:
            self.run.want_open_shop = False
            self.run.open_shop()
            self.state = STATE_RUN_SHOP
            return

        if self.run.pending_levelups > 0 and not self.run.levelup_choices:
            self.run.start_levelup_choice()
            self.state = STATE_LEVELUP

        if self.run.game_over:
            self.pending_board_rank = -1
            self.online_submit_status = None
            if self.save.qualifies_for_board(self.run.score):
                self.state = STATE_NAME_ENTRY
            else:
                self._maybe_submit_online()
                self.state = STATE_GAMEOVER
            audio.set_music("menu")

    def update_levelup(self, dt, mouse_pos, clicked):
        canvas = self.display.canvas
        self.bg.draw(canvas)
        tmp = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        draw_run(tmp, self.run, self.t)
        canvas.blit(tmp, (0, 0))
        self.levelup_ui.rebuild(self.run.levelup_choices)
        chosen = self.levelup_ui.draw_and_handle(canvas, self.run, mouse_pos, clicked, self.t)
        if chosen:
            self.run.choose_levelup(chosen)
            if self.run.pending_levelups <= 0:
                self.state = STATE_PLAY

    def update_run_shop(self, dt, mouse_pos, clicked):
        canvas = self.display.canvas
        self.bg.draw(canvas)
        tmp = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        draw_run(tmp, self.run, self.t)
        canvas.blit(tmp, (0, 0))
        close = self.shop_ui.draw_and_handle(canvas, self.run, mouse_pos, clicked, self.t)
        if close:
            self.state = STATE_PLAY

    def update_pause(self, dt, mouse_pos, clicked):
        canvas = self.display.canvas
        tmp = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        draw_run(tmp, self.run, self.t)
        canvas.blit(tmp, (0, 0))
        overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (5, 6, 12, 200), overlay.get_rect())
        canvas.blit(overlay, (0, 0))
        draw_text(canvas, "DURAKLATILDI", (VIRTUAL_W / 2, 200), 48, TEXT, bold=True, center=True)
        draw_text(canvas, f"Dalga {self.run.waves.wave}  •  Skor {fmt_num(self.run.score)}",
                  (VIRTUAL_W / 2, 250), 16, TEXT_DIM, center=True)

        cx = VIRTUAL_W / 2
        w, h, gap = 300, 46, 10
        y0 = 286
        buttons = [
            Button((cx - w / 2, y0, w, h), "DEVAM ET", lambda: self.set_state(STATE_PLAY), color=(60, 130, 90), hover_color=(80, 170, 115)),
            Button((cx - w / 2, y0 + (h + gap), w, h), "TAM EKRAN AÇ/KAPA", self.display.toggle_fullscreen),
            Button((cx - w / 2, y0 + 4 * (h + gap), w, h), "BAŞTAN BAŞLA", self.start_run, color=(130, 90, 60), hover_color=(170, 115, 80)),
            Button((cx - w / 2, y0 + 5 * (h + gap), w, h), "ANA MENÜ", lambda: self.set_state(STATE_MENU)),
        ]
        for b in buttons:
            b.update(mouse_pos, dt)
            b.draw(canvas)
            if clicked:
                b.click(mouse_pos)

        # --- SKİN GÖRÜNÜMÜ (oyun içinden açılıp kapatılabilir) ---
        # Kapatıldığında oyuncu; kanat, şapka, gözlük, pelerin ve skin efektleri
        # olmadan yalnızca skininin renginde sade bir top olarak çizilir.
        self._plain_skin_row(canvas, pygame.Rect(cx - w / 2, y0 + 3 * (h + gap), w, h),
                             mouse_pos, clicked)

        # --- yetenek çubuğu boyutu (oyuncu buradan küçültüp büyütebilir) ---
        sr = pygame.Rect(cx - w / 2, y0 + 2 * (h + gap), w, h)
        hov = sr.collidepoint(mouse_pos)
        panel(canvas, sr, bg=(36, 34, 56) if hov else (26, 26, 42),
              edge=CYAN if hov else PANEL_EDGE, alpha=240, radius=10, edge_w=2)
        draw_text(canvas, "YETENEK ÇUBUĞU", (sr.x + 16, sr.y + 7), 12, TEXT_DIM, shadow=False)
        draw_text(canvas, f"{skill_scale_label()}  »", (sr.x + 16, sr.y + 23), 17,
                  CYAN if hov else TEXT, bold=True, shadow=False)
        # sağda canlı küçük önizleme
        k = clamp(float(CFG.get("skill_scale", 0.85)), 0.5, 1.4)
        pw = int(26 * k)
        for i in range(3):
            prv = pygame.Rect(int(sr.right - 22 - (3 - i) * (pw + 4)), int(sr.centery - pw / 2), pw, pw)
            pygame.draw.rect(canvas, (18, 19, 30), prv, border_radius=4)
            pygame.draw.rect(canvas, (90, 200, 210), prv, width=1, border_radius=4)
        if clicked and hov:
            CFG["skill_scale"] = cycle_skill_scale()
            self.save.data.setdefault("settings", {})["skill_scale"] = CFG["skill_scale"]
            self.save.save()
            sfx("click", 0.6, 0.0)

    def _plain_skin_row(self, canvas, rect, mouse_pos, clicked, compact=False):
        """"SKİN GÖRÜNÜMÜ" anahtarı: sağında canlı bir önizleme topu taşır.

        Kapalıyken oyuncu yalnızca skininin renginde sade bir yuvarlak olur;
        skinin verdiği bonuslar etkilenmez, sadece görünüm sadeleşir.
        """
        on = not CFG.get("plain_skin")
        hov = rect.collidepoint(mouse_pos)
        panel(canvas, rect, bg=(30, 50, 34) if on else (44, 34, 28),
              edge=(GREEN if on else ORANGE) if not hov else lighten(GREEN if on else ORANGE, .3),
              alpha=240, radius=10, edge_w=2)
        if compact:
            draw_text(canvas, f"Skin Görünümü: {'AÇIK' if on else 'KAPALI'}",
                      (rect.centerx - 16, rect.centery - 7), 12, TEXT, bold=True,
                      center=True, shadow=False)
        else:
            draw_text(canvas, "SKİN GÖRÜNÜMÜ", (rect.x + 16, rect.y + 7), 12, TEXT_DIM, shadow=False)
            draw_text(canvas, f"{'AÇIK' if on else 'KAPALI — sade top'}  »",
                      (rect.x + 16, rect.y + 23), 17, (GREEN if on else ORANGE), bold=True,
                      shadow=False)

        # --- canlı önizleme: seçili skinin rengiyle küçük bir karakter ---
        sk = get_skin(self.save.equipped_skin_id())
        pr_ = 9 if compact else 12
        pcx, pcy = rect.right - pr_ - 10, rect.centery
        pygame.draw.circle(canvas, OUTLINE, (int(pcx), int(pcy)), pr_ + 2)
        pygame.draw.circle(canvas, scale_col(sk["color"], 0.6), (int(pcx), int(pcy)), pr_)
        pygame.draw.circle(canvas, sk["color"], (int(pcx - 1), int(pcy - 1)), pr_ - 1)
        if on:
            # görünüm açıkken önizlemede de küçük bir kanat/parıltı görünsün
            add_glow(canvas, pcx, pcy, pr_ * 1.8, sk["accent"], .45)
            for s in (-1, 1):
                pygame.draw.polygon(canvas, sk["accent"],
                                    [(pcx + s * pr_ * 0.75, pcy - 2),
                                     (pcx + s * pr_ * 1.45, pcy - pr_ * 0.65),
                                     (pcx + s * pr_ * 0.85, pcy + pr_ * 0.35)])
        pygame.draw.circle(canvas, (250, 250, 255), (int(pcx - 3), int(pcy - 2)), 2)
        pygame.draw.circle(canvas, (250, 250, 255), (int(pcx + 3), int(pcy - 2)), 2)

        if clicked and hov:
            CFG["plain_skin"] = on          # "on" açık demekti -> kapat
            self.save.data.setdefault("settings", {})["plain_skin"] = CFG["plain_skin"]
            self.save.save()
            sfx("click", 0.6, 0.0)
            return True
        return False

    def set_state(self, s):
        if s == STATE_MENU:
            audio.set_music("menu")
        self.state = s

    def _maybe_submit_online(self):
        if self.run.submitted_online:
            return
        self.run.submitted_online = True
        name = self.name_input.strip() or "İsimsiz"

        def on_done(ok):
            self.online_submit_status = "gönderildi" if ok else "başarısız"

        if self.online.enabled:
            self.online_submit_status = "gönderiliyor"
        # DÜZELTME: sunucu (server.py) "run_time" ve "created_at" bekliyordu,
        # oyun ise "time"/"diff" gönderiyordu. Bu yüzden dünya sıralamasındaki
        # süre alanı her zaman 0 kaydediliyordu.
        self.online.submit_score_async({
            "name": name[:14],
            "score": int(self.run.score),
            "kills": int(self.run.kills),
            "wave": int(self.run.waves.wave),
            "run_time": float(self.run.run_time),
            "created_at": time.time(),
            "diff": self.run.diff,
        }, on_done=on_done)

    def update_gameover(self, dt, mouse_pos, clicked):
        canvas = self.display.canvas
        self.bg.update(dt * 0.2)
        self.bg.draw(canvas)
        r = self.run
        panel_rect = pygame.Rect(0, 0, 560, 540)
        panel_rect.center = (VIRTUAL_W / 2, VIRTUAL_H / 2 - 6)
        panel(canvas, panel_rect, alpha=245)
        draw_text(canvas, "OYUN BİTTİ", (panel_rect.centerx, panel_rect.y + 38), 36, RED, bold=True, center=True)
        if r.death_cause:
            draw_text(canvas, f"Seni öldüren: {r.death_cause}", (panel_rect.centerx, panel_rect.y + 68), 13, TEXT_DIM, center=True, shadow=False)
        rows = [
            ("Skor", fmt_num(r.score), GOLD), ("Dalga", str(r.waves.wave), CYAN),
            ("Zorluk", DIFF_LABEL.get(r.diff, r.diff), TEXT), ("Öldürme", str(r.kills), TEXT),
            ("Harita", "CEHENNEM" if r.biome == "hell" else "ARENA",
             (255, 130, 80) if r.biome == "hell" else CYAN),
            ("Süre", fmt_time(r.run_time), TEXT), ("Kazanılan Altın (bu koşu)", fmt_num(r.coins_earned), GOLD),
            ("Kazanılan Elmas", fmt_num(r.gems_earned), GEM_COLOR),
        ]
        y = panel_rect.y + 96
        for label, val, col in rows:
            draw_text(canvas, label, (panel_rect.x + 40, y), 16, TEXT_DIM)
            draw_text(canvas, val, (panel_rect.right - 40, y), 18, col, bold=True, right=True)
            y += 33
        draw_text(canvas, "Bu koşuda market'ten aldıkların silindi.", (panel_rect.centerx, y + 4), 12, TEXT_DIM, center=True, shadow=False)
        y += 26
        if self.pending_board_rank >= 0:
            draw_text(canvas, f"YEREL SIRALAMADA #{self.pending_board_rank + 1}!", (panel_rect.centerx, y), 18, GOLD, bold=True, center=True)
            y += 24
        if self.online.enabled and self.online_submit_status:
            status_col = {"gönderiliyor": TEXT_DIM, "gönderildi": GREEN, "başarısız": RED}.get(self.online_submit_status, TEXT_DIM)
            draw_text(canvas, f"Dünya sıralamasına {self.online_submit_status}", (panel_rect.centerx, y), 13, status_col, center=True, shadow=False)

        w, h = 220, 52
        by = panel_rect.bottom - 72
        b1 = Button((panel_rect.centerx - w - 10, by, w, h), "TEKRAR OYNA", self.start_run, color=(60, 130, 90), hover_color=(80, 170, 115))
        b2 = Button((panel_rect.centerx + 10, by, w, h), "ANA MENÜ", lambda: self.set_state(STATE_MENU))
        for b in (b1, b2):
            b.update(mouse_pos, dt)
            b.draw(canvas)
            if clicked:
                b.click(mouse_pos)

    # ---------------- İSİM GİRİŞİ ----------------
    def handle_name_entry_key(self, event):
        if event.key == pygame.K_RETURN:
            self.confirm_name_entry()
        elif event.key == pygame.K_BACKSPACE:
            self.name_input = self.name_input[:-1]
        else:
            ch = event.unicode
            if ch and ch.isprintable() and len(self.name_input) < 14:
                self.name_input += ch

    def confirm_name_entry(self):
        r = self.run
        name = self.name_input.strip() or "İsimsiz"
        self.save.data.setdefault("settings", {})["player_name"] = name
        rank = self.save.submit_score(name, r.score, r.kills, r.run_time, r.waves.wave, r.diff)
        self.pending_board_rank = rank
        self._maybe_submit_online()
        self.state = STATE_GAMEOVER

    def update_name_entry(self, dt, mouse_pos, clicked):
        canvas = self.display.canvas
        self.bg.draw(canvas)
        panel_rect = pygame.Rect(0, 0, 520, 260)
        panel_rect.center = (VIRTUAL_W / 2, VIRTUAL_H / 2)
        panel(canvas, panel_rect, alpha=250)
        draw_text(canvas, "YENİ REKOR!", (panel_rect.centerx, panel_rect.y + 40), 32, GOLD, bold=True, center=True)
        draw_text(canvas, f"Skor: {fmt_num(self.run.score)}", (panel_rect.centerx, panel_rect.y + 78), 20, TEXT, center=True)
        draw_text(canvas, "İsmini yaz:", (panel_rect.centerx, panel_rect.y + 120), 16, TEXT_DIM, center=True)
        box = pygame.Rect(0, 0, 320, 46)
        box.center = (panel_rect.centerx, panel_rect.y + 156)
        pygame.draw.rect(canvas, (12, 13, 22), box, border_radius=8)
        pygame.draw.rect(canvas, GOLD, box, width=2, border_radius=8)
        cursor = "|" if int(self.t * 2) % 2 == 0 else ""
        draw_text(canvas, self.name_input + cursor, box.center, 22, TEXT, center=True, shadow=False)
        btn = Button((panel_rect.centerx - 110, panel_rect.bottom - 56, 220, 44), "KAYDET (ENTER)",
                     self.confirm_name_entry, color=(60, 130, 90), hover_color=(80, 170, 115))
        btn.update(mouse_pos, dt)
        btn.draw(canvas)
        if clicked:
            btn.click(mouse_pos)

    # ---------------- ANA MENÜ ----------------
    def _draw_loadout_panel(self, canvas, dt, mouse_pos, clicked):
        """Ana menüdeki sol panel: kuşanılmış karakterin canlı önizlemesi.

        Oyuncu menüden çıkmadan hangi skini, şapkayı, gözlüğü ve pelerini
        taktığını görür; panele tıklayınca doğrudan SKIN MARKET'e gider.
        """
        t = self.t
        rect = pygame.Rect(26, 302, 184, 212)
        hover = rect.collidepoint(mouse_pos)
        sk = get_skin(self.save.equipped_skin_id())
        panel(canvas, rect, bg=(26, 28, 46) if hover else (18, 20, 32),
              edge=sk["color"] if hover else (58, 62, 88), alpha=238, radius=14, edge_w=2)

        draw_text(canvas, "KARAKTERİN", (rect.centerx, rect.y + 10), 12, TEXT_DIM,
                  bold=True, center=True, shadow=False)

        # --- canlı karakter ---
        cx, cy = rect.centerx, rect.y + 84
        bob = math.sin(t * 1.8) * 3
        cy += bob
        fake = type("FP", (), {})()
        fake.radius = 27
        fake.aim_dir = (math.sin(t * 0.6) * 0.30, 1.0)
        fake.cosmetics = self.save.equipped_cosmetics()
        fake.skin = sk

        add_glow(canvas, cx, cy, 58, sk["color"], .38 + .10 * math.sin(t * 2.4))
        if not self.save.cosmetics_locked():
            draw_cosmetic_cape(canvas, fake, cx, cy, t)
        # Skinin kendi görünümü (aura, maske, kanat, pelerin...) tam hâliyle
        draw_skin_preview(canvas, sk, cx, cy, t, r=27, weapon=False)
        if not self.save.cosmetics_locked():
            draw_cosmetic_eyewear(canvas, fake, cx, cy, t)
            draw_cosmetic_hat(canvas, fake, cx, cy, t)

        draw_text(canvas, sk["name"], (rect.centerx, rect.y + 126), 15, sk["color"],
                  bold=True, center=True)

        # --- kuşanılmış parçalar: 3 küçük yuva ---
        eq = self.save.equipped_cosmetics()
        slots = [("hat", "ŞAPKA"), ("eyewear", "GÖZLÜK"), ("cape", "PELERİN")]
        sw = 56
        sx0 = rect.centerx - (len(slots) * sw) / 2
        for i, (slot, label) in enumerate(slots):
            sr = pygame.Rect(int(sx0 + i * sw + 3), rect.y + 150, sw - 6, 32)
            cid = eq.get(slot)
            item = COSMETIC_BY_ID.get(cid) if cid else None
            pygame.draw.rect(canvas, (13, 14, 24), sr, border_radius=7)
            pygame.draw.rect(canvas, item["color"] if item else (46, 50, 70), sr,
                             width=1, border_radius=7)
            if item:
                pygame.draw.circle(canvas, item["color"], (sr.centerx, sr.y + 11), 6)
                pygame.draw.circle(canvas, lighten(item["color"], .45),
                                   (sr.centerx - 2, sr.y + 9), 2)
            else:
                draw_text(canvas, "—", (sr.centerx, sr.y + 3), 13, (70, 74, 96),
                          center=True, shadow=False)
            draw_text(canvas, label, (sr.centerx, sr.bottom - 12), 8,
                      TEXT_DIM if item else (74, 78, 100), center=True, shadow=False)

        if self.save.cosmetics_locked():
            # Premium skin kendi kostümüyle gelir: slotların üstüne kilit şeridi.
            lr = pygame.Rect(int(sx0 + 3), rect.y + 150, int(len(slots) * sw - 6), 32)
            ls = pygame.Surface(lr.size, pygame.SRCALPHA)
            pygame.draw.rect(ls, (18, 14, 28, 225), ls.get_rect(), border_radius=7)
            canvas.blit(ls, lr.topleft)
            pygame.draw.rect(canvas, PURPLE, lr, width=1, border_radius=7)
            draw_text(canvas, "KOSTÜM SABİT", lr.center, 11, PURPLE, bold=True,
                      center=True, shadow=False)

        draw_text(canvas, "Değiştirmek için tıkla", (rect.centerx, rect.bottom - 18), 10,
                  GOLD if hover else TEXT_DIM, center=True, shadow=False)

        if clicked and hover:
            self.goto(STATE_SKIN_MARKET)
            sfx("click", 0.6, 0.0)

    def update_menu(self, dt, mouse_pos, clicked):
        self.bg.update(dt)
        canvas = self.display.canvas
        self.bg.draw(canvas)
        title_bob = math.sin(self.t * 1.4) * 6
        draw_text(canvas, GAME_TITLE, (VIRTUAL_W / 2, 108 + title_bob), 60, GOLD, bold=True, center=True)
        draw_text(canvas, "Kas, nişan al, rekor kır.", (VIRTUAL_W / 2, 158 + title_bob), 17, TEXT_DIM, center=True)

        gem_txt = f"Elmas: {fmt_num(self.save.get_gems())}"
        tw = text_width(gem_txt, 19, True)
        draw_icon(canvas, VIRTUAL_W / 2 - tw / 2 - 16, 198, "gem", GEM_COLOR, 11)
        draw_text(canvas, gem_txt, (VIRTUAL_W / 2, 198), 19, GEM_COLOR, bold=True, center=True)
        best = self.save.data.get("stats", {}).get("best_score", 0)
        best_wave = self.save.data.get("stats", {}).get("best_wave", 0)
        draw_text(canvas, f"En iyi skor: {fmt_num(best)}   En yüksek dalga: {best_wave}", (VIRTUAL_W / 2, 222), 14, TEXT_DIM, center=True)

        # zorluk seçici
        dr = pygame.Rect(0, 0, 260, 34)
        dr.center = (VIRTUAL_W / 2, 254)
        hover = dr.collidepoint(mouse_pos)
        panel(canvas, dr, bg=(30, 26, 44) if hover else (22, 20, 34), edge=PURPLE, alpha=235, radius=9, edge_w=2)
        draw_text(canvas, f"ZORLUK: {DIFF_LABEL[self.diff]}  »", dr.center, 15, PURPLE, bold=True, center=True, shadow=False)
        if clicked and hover:
            self.cycle_diff()
        draw_text(canvas, DIFF_DESC[self.diff], (VIRTUAL_W / 2, 274), 11, TEXT_DIM, center=True, shadow=False)

        self._draw_loadout_panel(canvas, dt, mouse_pos, clicked)

        for b in self.menu_buttons:
            b.update(mouse_pos, dt)
            b.draw(canvas)
            if clicked:
                b.click(mouse_pos)

        online_txt = "ÇEVRİMİÇİ: AÇIK" if self.online.enabled else "ÇEVRİMİÇİ: KAPALI"
        draw_text(canvas, online_txt, (VIRTUAL_W / 2, VIRTUAL_H - 44), 12,
                  GREEN if self.online.enabled else TEXT_DIM, center=True, shadow=False)
        draw_text(canvas, f"v{GAME_VERSION}   F11: Tam Ekran   F3: FPS   ESC: Geri", (VIRTUAL_W / 2, VIRTUAL_H - 24), 12, TEXT_DIM, center=True, shadow=False)

        # ---- alt şerit: sağda MAĞAZA kartı ----
        self.draw_gem_store_card(canvas, dt, mouse_pos, clicked)

    # Ana menünün alt şeridindeki KARE kart (sağ altta MAĞAZA). Boyut, üstteki
    # menü sütunlarına değmeyecek şekilde seçildi (sütunlar 514'te bitiyor).
    # Eski GÜNLÜK MARKET kartı kaldırıldı.
    MENU_CARD = 178
    MENU_CARD_Y = 524
    MENU_CARD_MARGIN = 26

    def _menu_card_rect(self, side):
        s, y, m = self.MENU_CARD, self.MENU_CARD_Y, self.MENU_CARD_MARGIN
        x = m if side == "left" else VIRTUAL_W - m - s
        return pygame.Rect(x, y, s, s)

    # ---------------- MAĞAZA KARTI (ana menü, sağ alt) ----------------
    def draw_gem_store_card(self, canvas, dt, mouse_pos, clicked):
        """Ana menünün SAĞ ALT köşesindeki KARE MAĞAZA kartı.

        Mağaza hem elmas paketlerini hem de gerçek parayla alınan PREMİUM
        skinleri satar.
        """
        # GÜNLÜK MARKET kaldırıldığı için MAĞAZA kartı sağ alta taşındı:
        # solda KARAKTERİN paneli var, böylece alt şerit dengeli duruyor.
        rect = self._menu_card_rect("right")
        hover = rect.collidepoint(mouse_pos)
        if hover and not self.gem_card_was_hover:
            sfx("hover", 0.4, 0.05)
        self.gem_card_was_hover = hover
        self.gem_card_anim += ((1.0 if hover else 0.0) - self.gem_card_anim) * min(1.0, dt * 12)
        rect = rect.move(0, -self.gem_card_anim * 4)

        accent = GEM_COLOR
        pulse = math.sin(self.t * 2.4) * 0.5 + 0.5

        shadow = pygame.Surface((rect.w + 20, rect.h + 20), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=22)
        canvas.blit(shadow, (rect.x - 10, rect.y - 2))
        add_glow(canvas, rect.centerx, rect.centery, 112, accent,
                 0.07 + pulse * 0.04 + self.gem_card_anim * 0.06)

        panel(canvas, rect, bg=(22, 30, 44) if hover else (18, 24, 36),
              edge=accent, alpha=250, radius=18, edge_w=2)
        strip = pygame.Surface((rect.w - 24, 3), pygame.SRCALPHA)
        pygame.draw.rect(strip, (*accent, 150 + int(pulse * 60)), strip.get_rect(), border_radius=2)
        canvas.blit(strip, (rect.x + 12, rect.y + 7))

        pl, pr_ = rect.x + 14, rect.right - 14

        bx, by = rect.x + 27, rect.y + 32
        add_glow(canvas, bx, by, 24, accent, 0.30 + pulse * 0.20)
        pygame.draw.circle(canvas, (13, 14, 22), (int(bx), int(by)), 14)
        pygame.draw.circle(canvas, accent, (int(bx), int(by)), 14, 2)
        draw_icon(canvas, bx, by, "gem", accent, 9)
        draw_text(canvas, "MAĞAZA", (rect.x + 46, rect.y + 14), 12, accent, bold=True, shadow=False)
        draw_text(canvas, "elmas + premium", (rect.x + 46, rect.y + 28), 10, TEXT_DIM, shadow=False)
        draw_text(canvas, f"{sum(1 for s in SKINS if s.get('premium'))} premium skin",
                  (rect.x + 46, rect.y + 41), 9, PURPLE, bold=True, shadow=False)

        pygame.draw.line(canvas, (52, 56, 78), (pl, rect.y + 56), (pr_, rect.y + 56), 1)

        # ---- mevcut elmas ----
        draw_text(canvas, "ELMASIN", (pl, rect.y + 60), 9, TEXT_DIM, bold=True, shadow=False)
        gtxt = fmt_num(self.save.get_gems())
        draw_icon(canvas, pl + 9, rect.y + 82, "gem", GEM_COLOR, 9)
        draw_text(canvas, gtxt, (pl + 24, rect.y + 71), 22, GEM_COLOR, bold=True)

        # ---- en avantajlı paket tanıtımı ----
        best = max(GEM_PACKS, key=lambda p: p["bonus"])
        pygame.draw.line(canvas, (52, 56, 78), (pl, rect.y + 100), (pr_, rect.y + 100), 1)
        draw_text(canvas, f"+%{best['bonus']} BONUS", (pl, rect.y + 108), 10, GOLD,
                  bold=True, shadow=False)
        draw_text(canvas, f"{fmt_num(gem_pack_total(best))} elmas", (pr_, rect.y + 108), 10,
                  TEXT_DIM, bold=True, shadow=False, right=True)
        draw_text(canvas, "en büyük pakette", (pl, rect.y + 121), 9, TEXT_DIM, shadow=False)

        cta = pygame.Rect(pl, rect.y + 136, pr_ - pl, 28)
        cs = pygame.Surface(cta.size, pygame.SRCALPHA)
        base = (48, 120, 170) if hover else (34, 88, 128)
        pygame.draw.rect(cs, (*base, 250), cs.get_rect(), border_radius=14)
        pygame.draw.rect(cs, (255, 255, 255, 55 + int(self.gem_card_anim * 90)),
                         cs.get_rect(), width=2, border_radius=14)
        canvas.blit(cs, cta.topleft)
        draw_text(canvas, "MAĞAZAYA GİT  »", cta.center, 13, (235, 248, 255),
                  bold=True, center=True, shadow=False)

        if clicked and hover:
            self.goto(STATE_GEM_STORE)
            sfx("click", 0.6, 0.0)

    # ---------------- ELMAS MARKETİ (satın alma ekranı) ----------------
    def _buy_gem_pack(self, pack):
        """Bir elmas paketi satın almayı başlatır."""
        def done(ok, msg):
            self.gem_msg = msg
            self.gem_msg_ok = ok
            self.gem_msg_timer = 3.2
            if ok and FAKE_PURCHASE:
                # Yalnızca TEST kipinde elmas yerel olarak eklenir.
                self.save.add_gems(gem_pack_total(pack))
                self.save.save()
            elif ok:
                # Gerçek satın almada elmaslar SUNUCUDA yazılır; oyun yalnızca
                # güncel değeri çeker (çift ekleme olmasın diye).
                self._refresh_gems_from_server()
            if ok:
                sfx("buy", 1.0, 0.0)
        self.purchase.begin_purchase(pack, on_done=done)

    def _refresh_gems_from_server(self):
        """Satın alma sonrası elmas sayısını sunucudan tazeler."""
        sid = self.purchase.steam_id()
        if not (sid and self.online.enabled):
            return
        def work():
            try:
                payload = json.dumps({"steam_id": sid}).encode("utf-8")
                req = urllib.request.Request(
                    ONLINE_API_URL.rstrip("/") + "/get_player", data=payload,
                    headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = json.loads(r.read().decode("utf-8"))
                if data.get("success"):
                    gems = int(data["data"].get("gems", self.save.get_gems()))
                    self.save.data["gems"] = max(0, gems)
                    self.save.save()
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    def _buy_premium_skin(self, sk):
        """Premium skini gerçek parayla satın almayı başlatır."""
        pack = dict(id=sk["item_id"], gems=0, bonus=0,
                    price_hint=sk.get("price_hint", ""), tag="", color=sk["color"])

        def done(ok, msg):
            self.gem_msg = msg
            self.gem_msg_ok = ok
            self.gem_msg_timer = 3.2
            if ok and FAKE_PURCHASE:
                # Yalnızca TEST kipinde skin yerel olarak açılır.
                self.save.grant_skin(sk["id"])
                self.save.equip_skin(sk["id"])
                self.gem_msg = f"TEST: {sk['name']} açıldı ve kuşanıldı"
            elif ok:
                # Gerçek satın almada sahiplik SUNUCUDA yazılır.
                self._refresh_gems_from_server()
            if ok:
                sfx("buy", 1.0, 0.0)

        self.purchase.begin_purchase(pack, on_done=done)

    def _store_tabs(self, canvas, mouse_pos, clicked):
        tabs = [("gems", "ELMAS PAKETLERİ"), ("skins", "PREMİUM SKİNLER")]
        tw, th, gap = 230, 34, 12
        x0 = (VIRTUAL_W - (len(tabs) * tw + (len(tabs) - 1) * gap)) / 2
        for i, (key, label) in enumerate(tabs):
            r = pygame.Rect(x0 + i * (tw + gap), 86, tw, th)
            active = self.store_tab == key
            hov = r.collidepoint(mouse_pos)
            bg = (36, 74, 104) if active else ((30, 34, 50) if hov else (20, 23, 36))
            pygame.draw.rect(canvas, bg, r, border_radius=9)
            pygame.draw.rect(canvas, GEM_COLOR if active else PANEL_EDGE, r, width=2, border_radius=9)
            draw_text(canvas, label, r.center, 14, TEXT if active else TEXT_DIM,
                      bold=True, center=True)
            if clicked and hov and not active:
                self.store_tab = key
                sfx("click", 0.5, 0.0)

    def _draw_gem_packs(self, canvas, dt, mouse_pos, clicked, can_buy):
        cols = len(GEM_PACKS)
        card_w, card_h, gap = 246, 300, 18
        start_x = (VIRTUAL_W - (cols * card_w + (cols - 1) * gap)) / 2
        y0 = 130
        for i, pack in enumerate(GEM_PACKS):
            rect = pygame.Rect(int(start_x + i * (card_w + gap)), y0, card_w, card_h)
            hover = rect.collidepoint(mouse_pos) and can_buy
            featured = pack["tag"] == "EN AVANTAJLI"
            accent = pack["color"]
            if featured:
                add_glow(canvas, rect.centerx, rect.centery, 150, GOLD, 0.10)
            panel(canvas, rect, bg=(26, 34, 50) if hover else (18, 22, 34),
                  edge=accent, alpha=246, radius=16, edge_w=3 if featured else 2)

            if pack["tag"]:
                tw2 = text_width(pack["tag"], 11, True) + 20
                br = pygame.Rect(0, 0, int(tw2), 22)
                br.center = (rect.centerx, rect.y + 2)
                bs = pygame.Surface(br.size, pygame.SRCALPHA)
                pygame.draw.rect(bs, (*(GOLD if featured else PURPLE), 240),
                                 bs.get_rect(), border_radius=11)
                canvas.blit(bs, br.topleft)
                draw_text(canvas, pack["tag"], br.center, 11,
                          (20, 18, 12) if featured else WHITE, bold=True, center=True, shadow=False)

            n_gem = 1 + i
            cy = rect.y + 74
            for k in range(n_gem):
                ang = -math.pi / 2 + (k - (n_gem - 1) / 2) * 0.55
                gx = rect.centerx + math.cos(ang) * (0 if n_gem == 1 else 26)
                gy = cy + math.sin(ang) * 10 + (0 if n_gem == 1 else 8)
                sz = 15 + i * 2
                add_glow(canvas, gx, gy, sz * 2.0, accent, .35)
                draw_icon(canvas, gx, gy, "gem", accent, sz)

            total = gem_pack_total(pack)
            draw_text(canvas, fmt_num(total), (rect.centerx, rect.y + 126), 34,
                      GEM_COLOR, bold=True, center=True)
            draw_text(canvas, "ELMAS", (rect.centerx, rect.y + 166), 12, TEXT_DIM,
                      bold=True, center=True, shadow=False)
            if pack["bonus"]:
                draw_text(canvas, f"{fmt_num(pack['gems'])} + %{pack['bonus']} bonus",
                          (rect.centerx, rect.y + 186), 11, GOLD, bold=True,
                          center=True, shadow=False)
            else:
                draw_text(canvas, "başlangıç paketi", (rect.centerx, rect.y + 186), 11,
                          TEXT_DIM, center=True, shadow=False)

            pygame.draw.line(canvas, (52, 56, 78), (rect.x + 22, rect.y + 208),
                             (rect.right - 22, rect.y + 208), 1)
            draw_text(canvas, pack["price_hint"], (rect.centerx, rect.y + 220), 22,
                      TEXT, bold=True, center=True)
            draw_text(canvas, "fiyat Steam'de bölgene göre belirlenir",
                      (rect.centerx, rect.y + 250), 9, TEXT_DIM, center=True, shadow=False)

            btn = Button((rect.x + 18, rect.bottom - 46, rect.w - 36, 34),
                         "SATIN AL" if can_buy else "YAKINDA",
                         lambda p=pack: self._buy_gem_pack(p),
                         color=(40, 110, 155) if can_buy else (38, 40, 54),
                         hover_color=(58, 145, 195), enabled=can_buy, text_size=14)
            btn.update(mouse_pos, dt)
            btn.draw(canvas)
            if clicked:
                btn.click(mouse_pos)

    def _draw_premium_skins(self, canvas, dt, mouse_pos, clicked, can_buy):
        prem = [s for s in SKINS if s.get("premium")]
        cols = max(1, len(prem))
        card_w, card_h, gap = 246, 300, 18
        start_x = (VIRTUAL_W - (cols * card_w + (cols - 1) * gap)) / 2
        y0 = 130
        equipped = self.save.equipped_skin_id()
        for i, sk in enumerate(prem):
            rect = pygame.Rect(int(start_x + i * (card_w + gap)), y0, card_w, card_h)
            owned = self.save.owns_skin(sk["id"])
            is_eq = equipped == sk["id"]
            hover = rect.collidepoint(mouse_pos)
            accent = GOLD if is_eq else sk["color"]
            add_glow(canvas, rect.centerx, rect.centery, 140, accent, 0.07)
            panel(canvas, rect, bg=(30, 26, 40) if hover else (18, 22, 34),
                  edge=accent, alpha=246, radius=16, edge_w=3)

            tag = "KUŞANILDI" if is_eq else ("SAHİPSİN" if owned else "PREMİUM")
            tcol = GOLD if is_eq else (GREEN if owned else PURPLE)
            tw2 = text_width(tag, 11, True) + 20
            br = pygame.Rect(0, 0, int(tw2), 22)
            br.center = (rect.centerx, rect.y + 2)
            bs = pygame.Surface(br.size, pygame.SRCALPHA)
            pygame.draw.rect(bs, (*tcol, 240), bs.get_rect(), border_radius=11)
            canvas.blit(bs, br.topleft)
            draw_text(canvas, tag, br.center, 11, (20, 18, 12) if is_eq else WHITE,
                      bold=True, center=True, shadow=False)

            draw_skin_preview(canvas, sk, rect.centerx, rect.y + 72, self.t, r=20)

            draw_text(canvas, sk["name"], (rect.centerx, rect.y + 116), 18, TEXT,
                      bold=True, center=True)
            # Özellik listesi kart yüksekliğini AŞMAMALI: ayrılan bandı
            # doldurduğunda kesilir (eskiden fiyatın üstüne biniyordu).
            yy = rect.y + 142
            perk_limit = rect.bottom - 86
            for perk in sk.get("perks", []):
                if yy >= perk_limit:
                    break
                for j, ln in enumerate(wrap_text(perk, 10, rect.w - 34)[:2]):
                    if yy >= perk_limit:
                        break
                    draw_text(canvas, ("• " if j == 0 else "   ") + ln,
                              (rect.x + 18, yy), 10, (200, 205, 225), shadow=False)
                    yy += 11
                yy += 3

            pygame.draw.line(canvas, (52, 56, 78), (rect.x + 22, rect.bottom - 80),
                             (rect.right - 22, rect.bottom - 80), 1)
            if owned:
                draw_text(canvas, "Kendi kostümüyle gelir", (rect.centerx, rect.bottom - 72),
                          10, TEXT_DIM, center=True, shadow=False)
            else:
                draw_text(canvas, sk.get("price_hint", ""), (rect.centerx, rect.bottom - 74),
                          19, TEXT, bold=True, center=True)

            if owned:
                btn = Button((rect.x + 18, rect.bottom - 46, rect.w - 36, 34),
                             "KUŞANILDI" if is_eq else "KUŞAN",
                             lambda s=sk: self._equip_premium(s),
                             color=(60, 130, 90) if not is_eq else (38, 40, 54),
                             hover_color=(80, 170, 115), enabled=not is_eq, text_size=14)
            else:
                btn = Button((rect.x + 18, rect.bottom - 46, rect.w - 36, 34),
                             "SATIN AL" if can_buy else "YAKINDA",
                             lambda s=sk: self._buy_premium_skin(s),
                             color=(120, 60, 150) if can_buy else (38, 40, 54),
                             hover_color=(160, 90, 200), enabled=can_buy, text_size=14)
            btn.update(mouse_pos, dt)
            btn.draw(canvas)
            if clicked:
                btn.click(mouse_pos)

    def _equip_premium(self, sk):
        self.save.equip_skin(sk["id"])
        self.selected_skin = sk["id"]
        sfx("click", 0.6, 0.0)

    def update_gem_store(self, dt, mouse_pos, clicked):
        canvas = self.display.canvas
        self.bg.draw(canvas)
        can_buy = self.purchase.available() and not self.purchase.busy
        ui_click = clicked

        # ================= ÜST ŞERİT =================
        top = pygame.Rect(0, 0, VIRTUAL_W, 76)
        s = pygame.Surface(top.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (12, 13, 22, 238), top)
        canvas.blit(s, (0, 0))
        pygame.draw.line(canvas, (48, 108, 150), (0, 76), (VIRTUAL_W, 76), 2)
        draw_icon(canvas, 34, 30, "gem", GEM_COLOR, 13)
        draw_text(canvas, "MAĞAZA", (56, 16), 26, GEM_COLOR, bold=True)
        draw_text(canvas, "Elmas paketleri ve premium skinler — oyunun gücünü değil, görünümünü ve tarzını değiştirir.",
                  (56, 48), 11, TEXT_DIM, shadow=False)
        gem_txt = fmt_num(self.save.get_gems())
        tw = text_width(gem_txt, 20, True)
        draw_icon(canvas, VIRTUAL_W - 40 - tw - 20, 26, "gem", GEM_COLOR, 11)
        draw_text(canvas, gem_txt, (VIRTUAL_W - 40, 16), 20, GEM_COLOR, bold=True, right=True)
        draw_text(canvas, "mevcut elmasın", (VIRTUAL_W - 40, 46), 11, TEXT_DIM,
                  shadow=False, right=True)

        self._store_tabs(canvas, mouse_pos, ui_click)
        if self.store_tab == "skins":
            self._draw_premium_skins(canvas, dt, mouse_pos, ui_click, can_buy)
        else:
            self._draw_gem_packs(canvas, dt, mouse_pos, ui_click, can_buy)

        # ================= ALT BİLGİ =================
        info = pygame.Rect(120, 440, VIRTUAL_W - 240, 90)
        panel(canvas, info, bg=(18, 19, 30), edge=(64, 70, 96), alpha=235, radius=12, edge_w=1)
        if FAKE_PURCHASE:
            draw_text(canvas, "TEST KİPİ — GERÇEK ÖDEME ALINMIYOR",
                      (info.centerx, info.y + 12), 16, (255, 140, 90), bold=True, center=True)
            draw_text(canvas, "KASMA_FAKE_PURCHASE ortam değişkeni açık. Dağıtım yapısında kapatılmalı.",
                      (info.centerx, info.y + 38), 11, TEXT_DIM, center=True, shadow=False)
        elif can_buy:
            draw_icon(canvas, info.centerx - 120, info.y + 22, "shield", GREEN, 9)
            draw_text(canvas, "Ödeme Steam üzerinden alınır", (info.centerx + 10, info.y + 12),
                      15, GREEN, bold=True, center=True)
            draw_text(canvas, "Satın alma penceresi Steam istemcisinde açılır; ürün hesabına anında tanımlanır.",
                      (info.centerx, info.y + 40), 11, TEXT_DIM, center=True, shadow=False)
        else:
            draw_text(canvas, "SATIN ALMA HENÜZ AÇIK DEĞİL", (info.centerx, info.y + 10), 15,
                      (225, 190, 110), bold=True, center=True)
            draw_text(canvas, self.purchase.unavailable_reason(),
                      (info.centerx, info.y + 34), 12, TEXT_DIM, center=True, shadow=False)
            draw_text(canvas, "Başarımları açtıkça da elmas kazanırsın.",
                      (info.centerx, info.y + 54), 11, GOLD, center=True, shadow=False)

        back = Button((VIRTUAL_W / 2 - 120, VIRTUAL_H - 62, 240, 42), "ANA MENÜYE DÖN",
                      lambda: self.set_state(STATE_MENU), text_size=14)
        for b in (back,):
            b.update(mouse_pos, dt)
            b.draw(canvas)
            if ui_click:
                b.click(mouse_pos)

        if self.purchase.busy:
            draw_text(canvas, self.purchase.status or "İşleniyor...",
                      (VIRTUAL_W / 2, 424), 13, CYAN, bold=True, center=True)
        if self.gem_msg_timer > 0:
            self.gem_msg_timer -= dt
            box = pygame.Rect(0, 0, 460, 110)
            box.center = (VIRTUAL_W / 2, VIRTUAL_H / 2)
            col = GREEN if self.gem_msg_ok else RED
            add_glow(canvas, box.centerx, box.centery, 200, col, 0.14)
            panel(canvas, box, alpha=250, edge=col, edge_w=2)
            draw_text(canvas, "İŞLEM TAMAM" if self.gem_msg_ok else "İŞLEM BAŞARISIZ",
                      (box.centerx, box.y + 24), 18, col, bold=True, center=True)
            for j, ln in enumerate(wrap_text(str(self.gem_msg or ""), 12, box.w - 50)[:2]):
                draw_text(canvas, ln, (box.centerx, box.y + 56 + j * 16), 12, TEXT,
                          center=True, shadow=False)

    # ---------------- NASIL OYNANIR + AYARLAR ----------------
    def update_howto(self, dt, mouse_pos, clicked):
        canvas = self.display.canvas
        self.bg.draw(canvas)
        panel_rect = pygame.Rect(0, 0, 800, 600)
        panel_rect.center = (VIRTUAL_W / 2, VIRTUAL_H / 2)
        panel(canvas, panel_rect, alpha=245)
        draw_text(canvas, "NASIL OYNANIR", (panel_rect.centerx, panel_rect.y + 32), 27, CYAN, bold=True, center=True)
        lines = [
            ("WASD / OK TUŞLARI", "Hareket et, düşmanlardan kaç"),
            ("FARE", "Nişan al — namlu her zaman imleci gösterir"),
            ("SOL TIK (basılı tut)", "Ateş et — nişan aldığın yöne mermi gider"),
            ("SPACE", "BONK! — çevrene alan hasarı veren yakın vuruş"),
            ("SHIFT / SAĞ TIK", "DASH — kısa süre hasar almazsın"),
            ("B", "Büyük MARKET'i aç — dalga ilerledikçe yeni katmanlar açılır"),
            ("DALGALAR SKORLA İLERLER", "Her dalganın skor hedefi var — hedef her zorlukta AYNI"),
            ("ZORLUK = TEMPO", "Kabus dalgaları zorlaştırmaz, düşmanları daha hızlı getirir"),
            ("DALGA İÇİNDE HIZLANIR", "Aynı dalgada bile oyalandıkça düşmanlar sıklaşır ve kalabalıklaşır"),
            ("MARKET ÇEKİRDEKLERİ", "ÇEKİRDEK sekmesindeki yükseltmelerin tavanı yok — altın hep işe yarar"),
            ("10., 15., 20. DALGA...", "10'dan itibaren her 5 dalgada PATRON — canları gücüne göre ölçeklenir"),
            ("PATRONLAR CAN ÇALAR", "Patron da vurdukça iyileşir; dövüş yaklaşık 1,5 dakika sürer"),
            ("KIYAFET MARKET", "Şapka, gözlük ve pelerinlerin her biri küçük kalıcı bonus verir"),
            ("ÖLÜRSEN", "O koşuda market'ten aldıkların silinir — baştan başlarsın"),
            ("SKIN MARKET", "Elmasla kalıcı görünümler al — her skinin kendi silahı var"),
            ("HARİTA 3x3 EKRAN", "Dünya ekrandan büyük — kamera seni takip eder, sağ üstte küçük harita var"),
            ("E  ·  CEHENNEM KAPISI", "25. dalga patronunu devirince açılan MOR portala E ile gir"),
            ("CEHENNEM (2. HARİTA)", "Yaratıklar bambaşka: 25. dalga kadar güçlü ama 1. dalga kadar yavaş"),
            ("25'TEN SONRA ARENA", "Yeni patron gelmez; arena her dalgada azar — 32'ye kadar dayanamazsın"),
            ("CEHENNEM MARKETİ", "Markette yalnızca cehennemde açılan yeni bir kademe var"),
            ("SKİN ÖZEL YETENEĞİ", "Her skinin OTOMATİK bir yeteneği var; süresi ekranın altında yazar"),
            ("YETENEK = 0.5 SN DONMA", "Yetenek çalıştığında düşmanlar yarım saniye donar, sonra devam eder"),
            ("KİTAPLIK", "Kitapların hepsi kilitli — her birinin kendi görevleri var"),
            ("BAŞARIMLAR", "Başarıma tıkla: nasıl kazanılacağını, ilerlemeni ve elmas ödülünü gösterir"),
        ]
        # Satır aralığı listenin uzunluğuna göre hesaplanır; böylece yeni
        # madde eklendiğinde yazılar panelin dışına taşmaz.
        list_top = panel_rect.y + 66
        list_bottom = panel_rect.bottom - 64      # GERİ düğmesine yer bırak
        step = clamp((list_bottom - list_top) / max(1, len(lines)), 22, 38)
        y = list_top
        for title, desc in lines:
            draw_text(canvas, title, (panel_rect.x + 36, y), 13, GOLD, bold=True)
            draw_text(canvas, desc, (panel_rect.x + 36, y + 15), 11, TEXT_DIM, shadow=False)
            y += step

        # ---- ayarlar ----
        ax = panel_rect.x + 420
        draw_text(canvas, "AYARLAR", (ax, panel_rect.y + 70), 18, GOLD, bold=True)
        st = self.save.data.setdefault("settings", {})
        yy = panel_rect.y + 104
        for label, key, is_bool in (("Müzik Sesi", "music_vol", False), ("Efekt Sesi", "sfx_vol", False)):
            draw_text(canvas, label, (ax, yy), 13, TEXT_DIM, shadow=False)
            br = pygame.Rect(ax, yy + 18, 220, 14)
            val = st.get(key, 0.5)
            draw_bar(canvas, br, val, CYAN, radius=6)
            if clicked and br.inflate(0, 10).collidepoint(mouse_pos):
                st[key] = clamp((mouse_pos[0] - br.x) / br.w, 0.0, 1.0)
                self.save.save()
            yy += 44
        for label, key in (("Ekran Sarsıntısı", "shake"), ("Hasar Sayıları", "dmg")):
            r = pygame.Rect(ax, yy, 220, 28)
            on = st.get(key, True)
            hover = r.collidepoint(mouse_pos)
            panel(canvas, r, bg=(30, 50, 34) if on else (40, 26, 26), edge=(GREEN if on else RED), alpha=230, radius=8, edge_w=2)
            draw_text(canvas, f"{label}: {'AÇIK' if on else 'KAPALI'}", r.center, 12, TEXT, bold=True, center=True, shadow=False)
            if clicked and hover:
                st[key] = not on
                self.save.apply_cfg()
                self.save.save()
                sfx("click", 0.5, 0.0)
            yy += 36

        # --- SKİN GÖRÜNÜMÜ anahtarı (oyun içinde ESC > menüden de değiştirilebilir) ---
        self._plain_skin_row(canvas, pygame.Rect(ax, yy, 220, 34), mouse_pos, clicked, compact=True)
        yy += 42
        draw_text(canvas, "Kapalıyken karakterin sadece skin renginde", (ax, yy), 10,
                  TEXT_DIM, shadow=False)
        draw_text(canvas, "sade bir top olur (bonuslar aynen kalır).", (ax, yy + 13), 10,
                  TEXT_DIM, shadow=False)

        btn = Button((panel_rect.centerx - 100, panel_rect.bottom - 52, 200, 40), "GERİ", lambda: self.set_state(STATE_MENU))
        btn.update(mouse_pos, dt)
        btn.draw(canvas)
        if clicked:
            btn.click(mouse_pos)

    # ---------------- BAŞARIMLAR ----------------
    # Başarım ekranı artık küçük bir liste değil, tam ekran bir galeri:
    # her kart madalyonu, kademesini, ilerlemesini ve elmas ödülünü gösterir.
    # Bir karta tıklanınca "NASIL KAZANILIR" penceresi açılır.
    def _ach_sort_key(self, a):
        """Sıralama: önce kilitli ve tamamlanmaya en yakın olanlar."""
        got = self.ach.has(a["id"])
        cur, need, _ = ach_progress(self.save, a)
        frac = (cur / need) if need else 0.0
        return (1 if got else 0, -frac, ACH_TIER_ORDER.index(a.get("tier", "bronz")))

    def _ach_medallion(self, canvas, cx, cy, r, ach, got, pulse=0.0):
        """Başarım madalyonu: kademe rengiyle halka + ortada simge."""
        col = ach_tier_color(ach)
        if got:
            add_glow(canvas, cx, cy, r * 2.6, col, 0.18 + pulse * 0.10)
        pygame.draw.circle(canvas, (14, 15, 24), (int(cx), int(cy)), int(r))
        pygame.draw.circle(canvas, col if got else (62, 66, 84), (int(cx), int(cy)), int(r), 2)
        if got:
            pygame.draw.circle(canvas, scale_col(col, 0.35), (int(cx), int(cy)), int(r - 4))
        draw_icon(canvas, cx, cy, ach.get("icon", "star"),
                  col if got else (78, 82, 100), max(5, int(r * 0.62)))
        if not got:
            # kilit çizgisi — kilitli madalyon soluk ve çapraz çizgili
            pygame.draw.line(canvas, (92, 78, 86), (cx - r * 0.6, cy + r * 0.6),
                             (cx + r * 0.6, cy - r * 0.6), 2)

    def update_achievements(self, dt, mouse_pos, clicked, wheel_y=0):
        canvas = self.display.canvas
        self.bg.draw(canvas)

        unlocked = self.save.data.get("achievements", {})
        got_n = sum(1 for a in ACHIEVEMENTS if a["id"] in unlocked)
        total_n = len(ACHIEVEMENTS)
        earned_gems = sum(int(a.get("gems", 0) or 0) for a in ACHIEVEMENTS if a["id"] in unlocked)
        left_gems = sum(int(a.get("gems", 0) or 0) for a in ACHIEVEMENTS if a["id"] not in unlocked)

        if self.ach_filter == "got":
            items = [a for a in ACHIEVEMENTS if a["id"] in unlocked]
        elif self.ach_filter == "locked":
            items = [a for a in ACHIEVEMENTS if a["id"] not in unlocked]
            items.sort(key=self._ach_sort_key)
        elif self.ach_filter == "near":
            items = []
            for a in ACHIEVEMENTS:
                if a["id"] in unlocked:
                    continue
                cur, need, _ = ach_progress(self.save, a)
                if need and cur / need >= 0.4:
                    items.append(a)
            items.sort(key=self._ach_sort_key)
        else:
            items = list(ACHIEVEMENTS)

        cols = 3
        card_w, card_h = 400, 134
        gap_x, gap_y = 18, 16
        start_x = (VIRTUAL_W - (cols * card_w + (cols - 1) * gap_x)) / 2
        list_top, list_bottom = 158, VIRTUAL_H - 70
        list_h = list_bottom - list_top

        rows = math.ceil(len(items) / cols) if items else 1
        content_h = rows * card_h + max(0, rows - 1) * gap_y
        max_scroll = max(0, content_h - list_h)

        list_rect = pygame.Rect(0, list_top, VIRTUAL_W, list_h)
        if max_scroll > 0 and list_rect.collidepoint(mouse_pos) and not self.ach_detail:
            self.ach_scroll -= wheel_y * 46
        self.ach_scroll = clamp(self.ach_scroll, 0, max_scroll)

        list_click = clicked and not self.ach_detail
        opened_now = False
        pulse = 0.5 + 0.5 * math.sin(self.t * 3.0)

        prev_clip = canvas.get_clip()
        canvas.set_clip(list_rect)
        for i, a in enumerate(items):
            col_i, row = i % cols, i // cols
            y = list_top + row * (card_h + gap_y) - self.ach_scroll
            if y + card_h < list_top or y > list_bottom:
                continue
            rect = pygame.Rect(int(start_x + col_i * (card_w + gap_x)), int(y), card_w, card_h)
            got = a["id"] in unlocked
            cur, need, done = ach_progress(self.save, a)
            tcol = ach_tier_color(a)
            hover = (rect.collidepoint(mouse_pos) and list_rect.collidepoint(mouse_pos)
                     and not self.ach_detail)
            if hover:
                rect = rect.move(0, -3)

            edge = tcol if got else (56, 60, 78)
            if hover:
                add_glow(canvas, rect.centerx, rect.centery, 180, edge, 0.11)
            panel(canvas, rect, bg=(34, 30, 20) if got else ((28, 30, 46) if hover else (19, 21, 33)),
                  edge=lighten(edge, 0.25) if hover else edge, alpha=242, radius=13, edge_w=2)

            # üst şerit: kademe rengi
            strip = pygame.Surface((rect.w - 26, 3), pygame.SRCALPHA)
            pygame.draw.rect(strip, (*tcol, 210 if got else 90), strip.get_rect(), border_radius=2)
            canvas.blit(strip, (rect.x + 13, rect.y + 7))

            self._ach_medallion(canvas, rect.x + 48, rect.y + 52, 28, a, got, pulse)

            tx = rect.x + 88
            draw_text(canvas, a["name"], (tx, rect.y + 16), 18, TEXT if got else (168, 172, 190),
                      bold=True)
            # kademe rozeti (sağ üst)
            tier = ACH_TIERS.get(a.get("tier", "bronz"), ACH_TIERS["bronz"])
            draw_text(canvas, tier["label"], (rect.right - 16, rect.y + 17), 10,
                      tcol if got else scale_col(tcol, 0.55), bold=True, right=True, shadow=False)

            for j, ln in enumerate(wrap_text(a["desc"], 11, rect.w - 108)[:2]):
                draw_text(canvas, ln, (tx, rect.y + 40 + j * 14), 11, TEXT_DIM,
                          shadow=False)

            # ---- alt bölüm: ilerleme / durum ----
            gems = int(a.get("gems", 0) or 0)
            if got:
                draw_icon(canvas, tx + 6, rect.bottom - 30, "star", GREEN, 6)
                draw_text(canvas, f"AÇILDI  ·  {unlocked.get(a['id'], '')}",
                          (tx + 18, rect.bottom - 38), 12, GREEN, bold=True, shadow=False)
            elif need:
                frac = clamp(cur / max(1, need), 0.0, 1.0)
                pb = pygame.Rect(tx, rect.bottom - 40, rect.w - 108 - 82, 8)
                draw_bar(canvas, pb, frac, tcol, radius=4)
                draw_text(canvas, f"{fmt_num(int(cur))} / {fmt_num(int(need))}   (%{int(frac * 100)})",
                          (tx, rect.bottom - 28), 11, TEXT_DIM, shadow=False)
            else:
                draw_text(canvas, "Oyun içinde tetiklenir", (tx, rect.bottom - 30), 11,
                          (150, 140, 110), shadow=False)

            if gems:
                draw_icon(canvas, rect.right - 62, rect.bottom - 26, "gem",
                          GEM_COLOR if not got else (110, 170, 140), 7)
                draw_text(canvas, f"+{gems}", (rect.right - 16, rect.bottom - 34), 13,
                          GEM_COLOR if not got else (110, 170, 140), bold=True, right=True,
                          shadow=False)

            if hover:
                draw_text(canvas, "DETAY  »", (rect.right - 16, rect.y + 40), 10,
                          lighten(edge, 0.35), bold=True, right=True, shadow=False)

            if list_click and hover:
                self.ach_detail = a["id"]
                self.ach_detail_t = 0.0
                opened_now = True
                sfx("click", 0.5, 0.0)
        canvas.set_clip(prev_clip)

        if max_scroll > 0:
            draw_scrollbar(canvas, VIRTUAL_W - 16, list_top, list_h, content_h, self.ach_scroll)

        # ================= ÜST ŞERİT =================
        top = pygame.Rect(0, 0, VIRTUAL_W, 96)
        s = pygame.Surface(top.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (12, 13, 22, 235), top)
        canvas.blit(s, (0, 0))
        pygame.draw.line(canvas, (140, 110, 50), (0, 96), (VIRTUAL_W, 96), 2)
        draw_icon(canvas, 30, 30, "star", GOLD, 13)
        draw_text(canvas, "BAŞARIMLAR", (52, 18), 26, GOLD, bold=True)
        draw_text(canvas, "Bir başarıma tıkla: nasıl kazanılacağını, ilerlemeni ve ödülünü gösterir.",
                  (52, 50), 11, TEXT_DIM, shadow=False)
        draw_icon(canvas, 58, 74, "gem", GEM_COLOR, 6)
        draw_text(canvas, f"Kazanılan: {fmt_num(earned_gems)} elmas   ·   Bekleyen: {fmt_num(left_gems)} elmas",
                  (70, 67), 11, GEM_COLOR, bold=True, shadow=False)

        pbw = 250
        pbx = VIRTUAL_W - pbw - 40
        all_done = got_n >= total_n
        draw_text(canvas, f"{got_n}/{total_n} BAŞARIM", (pbx, 20), 12,
                  GOLD if all_done else TEXT, bold=True, shadow=False)
        draw_bar(canvas, pygame.Rect(pbx, 40, pbw, 10), got_n / max(1, total_n),
                 GOLD if all_done else (230, 180, 90), radius=5)
        draw_text(canvas, f"%{int(got_n / max(1, total_n) * 100)}", (pbx + pbw + 8, 38), 11,
                  TEXT_DIM, bold=True, shadow=False)
        # kademe dağılımı
        lx = pbx
        for tkey in ACH_TIER_ORDER:
            tier = ACH_TIERS[tkey]
            tot = sum(1 for a in ACHIEVEMENTS if a.get("tier") == tkey)
            if not tot:
                continue
            g = sum(1 for a in ACHIEVEMENTS if a.get("tier") == tkey and a["id"] in unlocked)
            pygame.draw.circle(canvas, tier["color"], (int(lx + 5), 66), 5)
            draw_text(canvas, f"{g}/{tot}", (lx + 14, 59), 11, tier["color"], bold=True, shadow=False)
            lx += 62

        # ---- filtre sekmeleri ----
        near_n = 0
        for a in ACHIEVEMENTS:
            if a["id"] in unlocked:
                continue
            c, n2, _ = ach_progress(self.save, a)
            if n2 and c / n2 >= 0.4:
                near_n += 1
        tabs = [("all", f"TÜMÜ ({total_n})"),
                ("got", f"AÇILDI ({got_n})"),
                ("locked", f"KİLİTLİ ({total_n - got_n})"),
                ("near", f"YAKIN ({near_n})")]
        tab_w, tab_h, tab_gap = 168, 34, 10
        tabs_x = (VIRTUAL_W - (tab_w * len(tabs) + tab_gap * (len(tabs) - 1))) / 2
        for i, (key, label) in enumerate(tabs):
            r = pygame.Rect(int(tabs_x + i * (tab_w + tab_gap)), 106, tab_w, tab_h)
            active = self.ach_filter == key
            hov = r.collidepoint(mouse_pos) and not self.ach_detail
            bg = (126, 96, 36) if active else ((36, 34, 46) if hov else (22, 24, 38))
            pygame.draw.rect(canvas, bg, r, border_radius=9)
            pygame.draw.rect(canvas, GOLD if active else PANEL_EDGE, r, width=2, border_radius=9)
            draw_text(canvas, label, r.center, 14, TEXT if active else TEXT_DIM,
                      bold=True, center=True)
            if list_click and hov and not active:
                self.ach_filter = key
                self.ach_scroll = 0.0
                sfx("click", 0.5, 0.0)

        if not items:
            draw_text(canvas, "Bu listede başarım yok.", (VIRTUAL_W / 2, list_top + 70), 16,
                      TEXT_DIM, center=True)

        btn = Button((VIRTUAL_W / 2 - 110, VIRTUAL_H - 58, 220, 44), "ANA MENÜYE DÖN",
                     lambda: self.set_state(STATE_MENU))
        btn.update(mouse_pos, dt)
        btn.draw(canvas)
        if list_click:
            btn.click(mouse_pos)

        if self.ach_detail:
            self._draw_ach_detail(canvas, dt, mouse_pos, clicked and not opened_now)

    def _draw_ach_detail(self, canvas, dt, mouse_pos, clicked):
        """Bir başarıma tıklayınca açılan DETAY penceresi.

        Oyuncu burada başarımı NASIL kazanacağını, nerede olduğunu (ilerleme
        çubuğu + kalan miktar) ve açtığında ne kazanacağını görür.
        """
        a = ACH_BY_ID.get(self.ach_detail)
        if not a:
            self.ach_detail = None
            return
        unlocked = self.save.data.get("achievements", {})
        got = a["id"] in unlocked
        cur, need, done = ach_progress(self.save, a)
        tcol = ach_tier_color(a)
        tier = ACH_TIERS.get(a.get("tier", "bronz"), ACH_TIERS["bronz"])

        self.ach_detail_t = min(1.0, self.ach_detail_t + dt / 0.18)
        k = ease_out_cubic(self.ach_detail_t)

        ov = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        pygame.draw.rect(ov, (5, 6, 12, int(214 * k)), ov.get_rect())
        canvas.blit(ov, (0, 0))

        PW, PH = 640, 442
        r = pygame.Rect(0, 0, int(PW * (0.7 + 0.3 * k)), int(PH * (0.7 + 0.3 * k)))
        r.center = (VIRTUAL_W // 2, VIRTUAL_H // 2 - 6)
        add_glow(canvas, r.centerx, r.centery, 380, tcol, 0.09)
        panel(canvas, r, bg=(24, 22, 16) if got else (18, 20, 30), edge=tcol, alpha=252,
              radius=18, edge_w=3)
        if k < 0.6:
            return

        pulse = 0.5 + 0.5 * math.sin(self.t * 3.0)
        self._ach_medallion(canvas, r.centerx, r.y + 78, 44, a, got, pulse)

        draw_text(canvas, a["name"], (r.centerx, r.y + 132), 28, TEXT if got else (188, 192, 208),
                  bold=True, center=True)
        # kademe rozeti
        blab = f"{tier['label']} BAŞARIM"
        bw = text_width(blab, 12, True) + 26
        br = pygame.Rect(0, 0, int(bw), 22)
        br.center = (r.centerx, r.y + 170)
        pygame.draw.rect(canvas, tcol, br, width=1, border_radius=11)
        draw_text(canvas, blab, (br.centerx, br.centery - 7), 12, tcol, bold=True,
                  center=True, shadow=False)

        y = r.y + 194
        for ln in wrap_text(a["desc"], 15, r.w - 90):
            draw_text(canvas, ln, (r.centerx, y), 15, TEXT, center=True, shadow=False)
            y += 21

        y += 10
        pygame.draw.line(canvas, PANEL_EDGE, (r.x + 40, y), (r.right - 40, y), 1)
        y += 14
        draw_text(canvas, "NASIL KAZANILIR", (r.centerx, y), 13, tcol, bold=True,
                  center=True, shadow=False)
        y += 22
        for ln in wrap_text(a.get("how", a["desc"]), 12, r.w - 90)[:5]:
            draw_text(canvas, ln, (r.centerx, y), 12, (196, 200, 216), center=True, shadow=False)
            y += 17

        y += 12
        # ---- ilerleme ----
        if got:
            draw_text(canvas, f"AÇILDI  ·  {unlocked.get(a['id'], '')}", (r.centerx, y), 16,
                      GREEN, bold=True, center=True)
            y += 26
        elif need:
            frac = clamp(cur / max(1, need), 0.0, 1.0)
            pb = pygame.Rect(r.x + 60, int(y), r.w - 120, 14)
            draw_bar(canvas, pb, frac, tcol, radius=7)
            y += 20
            kalan = max(0, int(need) - int(cur))
            draw_text(canvas,
                      f"{fmt_num(int(cur))} / {fmt_num(int(need))}   —   {fmt_num(kalan)} kaldı  (%{int(frac * 100)})",
                      (r.centerx, y), 13, TEXT_DIM, center=True, shadow=False)
            y += 24
        else:
            draw_text(canvas, "KİLİTLİ", (r.centerx, y), 16, (190, 140, 70), bold=True,
                      center=True)
            y += 22
            draw_text(canvas, "Bu başarımın ilerleme sayacı yok — şartı sağladığın anda açılır.",
                      (r.centerx, y), 11, TEXT_DIM, center=True, shadow=False)
            y += 22

        # ---- ödül ----
        gems = int(a.get("gems", 0) or 0)
        if gems:
            rw = pygame.Rect(0, 0, 250, 34)
            rw.center = (r.centerx, int(y + 14))
            pygame.draw.rect(canvas, (20, 34, 48), rw, border_radius=10)
            pygame.draw.rect(canvas, GEM_COLOR if not got else (80, 140, 110), rw,
                             width=2, border_radius=10)
            draw_icon(canvas, rw.x + 24, rw.centery, "gem",
                      GEM_COLOR if not got else (110, 170, 140), 8)
            draw_text(canvas, ("KAZANILDI: " if got else "ÖDÜL: ") + f"{gems} ELMAS",
                      (rw.centerx + 12, rw.centery - 8), 14,
                      GEM_COLOR if not got else (110, 170, 140), bold=True, center=True,
                      shadow=False)

        # ---- kapat ----
        cb = pygame.Rect(0, 0, 190, 40)
        cb.center = (r.centerx, r.bottom + 32)
        hov = cb.collidepoint(mouse_pos)
        pygame.draw.rect(canvas, (60, 56, 44) if hov else (34, 34, 46), cb, border_radius=10)
        pygame.draw.rect(canvas, tcol if hov else PANEL_EDGE, cb, width=2, border_radius=10)
        draw_text(canvas, "KAPAT", cb.center, 15, TEXT if hov else TEXT_DIM, bold=True,
                  center=True)
        if clicked and (hov or not r.collidepoint(mouse_pos)):
            self.ach_detail = None
            sfx("click", 0.5, 0.0)

    # ---------------- YEREL SKOR TABLOSU ----------------
    def update_leaderboard(self, dt, mouse_pos, clicked):
        canvas = self.display.canvas
        self.bg.draw(canvas)
        panel_rect = pygame.Rect(0, 0, 640, 560)
        panel_rect.center = (VIRTUAL_W / 2, VIRTUAL_H / 2)
        panel(canvas, panel_rect, alpha=245)
        draw_text(canvas, "YEREL SKOR TABLOSU", (panel_rect.centerx, panel_rect.y + 40), 30, GOLD, bold=True, center=True)
        board = self.save.data.get("leaderboard", [])
        headers = ["#", "İsim", "Skor", "Dalga", "Öldürme", "Süre"]
        col_x = [panel_rect.x + 30, panel_rect.x + 70, panel_rect.x + 250, panel_rect.x + 360, panel_rect.x + 450, panel_rect.x + 550]
        hy = panel_rect.y + 90
        for i, h in enumerate(headers):
            draw_text(canvas, h, (col_x[i], hy), 14, TEXT_DIM, bold=True, shadow=False)
        pygame.draw.line(canvas, PANEL_EDGE, (panel_rect.x + 24, hy + 22), (panel_rect.right - 24, hy + 22), 1)
        if not board:
            draw_text(canvas, "Henüz skor yok. İlk rekoru sen kır!", (panel_rect.centerx, panel_rect.centery), 18, TEXT_DIM, center=True)
        else:
            y = hy + 40
            for i, e in enumerate(board[:10]):
                col = GOLD if i == 0 else (TEXT_DIM if i > 2 else TEXT)
                draw_text(canvas, f"{i+1}", (col_x[0], y), 15, col, bold=(i == 0))
                draw_text(canvas, e["name"], (col_x[1], y), 15, col, bold=(i == 0))
                draw_text(canvas, fmt_num(e["score"]), (col_x[2], y), 15, col, bold=(i == 0))
                draw_text(canvas, str(e.get("wave", "-")), (col_x[3], y), 15, col)
                draw_text(canvas, str(e["kills"]), (col_x[4], y), 15, col)
                draw_text(canvas, fmt_time(e["time"]), (col_x[5], y), 15, col)
                y += 36
        btn = Button((panel_rect.centerx - 100, panel_rect.bottom - 60, 200, 44), "GERİ", lambda: self.set_state(STATE_MENU))
        btn.update(mouse_pos, dt)
        btn.draw(canvas)
        if clicked:
            btn.click(mouse_pos)

    # ---------------- DÜNYA SIRALAMASI ----------------
    # ---- sıralama yardımcıları -------------------------------------
    @staticmethod
    def _rank_style(i):
        """Sıraya göre (madalya rengi, parlaklık) döndürür."""
        if i == 0:
            return (255, 205, 80), 1.0
        if i == 1:
            return (206, 214, 232), 0.82
        if i == 2:
            return (214, 148, 88), 0.72
        return (96, 104, 130), 0.0

    def _draw_medal(self, canvas, cx, cy, i, r, t):
        """İlk üç için madalya, diğerleri için sade sıra rozeti."""
        col, shine = self._rank_style(i)
        if shine > 0:
            add_glow(canvas, cx, cy, r * 2.1, col, .30 * shine + .08 * math.sin(t * 3 + i))
        pygame.draw.circle(canvas, OUTLINE, (int(cx), int(cy)), int(r + 2))
        pygame.draw.circle(canvas, scale_col(col, 0.55), (int(cx), int(cy)), int(r))
        pygame.draw.circle(canvas, col, (int(cx), int(cy)), int(r), 2)
        if shine > 0:
            pygame.draw.circle(canvas, lighten(col, 0.55),
                               (int(cx - r * 0.3), int(cy - r * 0.3)), max(1, int(r * 0.24)))
        draw_text(canvas, str(i + 1), (cx, cy), int(r * 1.1),
                  (18, 18, 26) if shine > 0 else TEXT, bold=True, center=True, shadow=False)

    def update_world_leaderboard(self, dt, mouse_pos, clicked):
        canvas = self.display.canvas
        self.bg.draw(canvas)
        t = self.t
        my_name = (self.save.data.get("settings", {}).get("player_name") or "").strip().lower()

        panel_rect = pygame.Rect(0, 0, 760, 600)
        panel_rect.center = (VIRTUAL_W / 2, VIRTUAL_H / 2)
        panel(canvas, panel_rect, alpha=246, edge=(70, 120, 190), edge_w=3, radius=18)

        # ---- başlık şeridi ----
        head = pygame.Rect(panel_rect.x + 2, panel_rect.y + 2, panel_rect.w - 4, 74)
        hs = pygame.Surface(head.size, pygame.SRCALPHA)
        for i in range(head.h):
            a = int(150 * (1 - i / head.h))
            pygame.draw.line(hs, (40, 80, 150, a), (0, i), (head.w, i))
        canvas.blit(hs, head.topleft)
        draw_icon(canvas, panel_rect.centerx - 168, panel_rect.y + 40, "star", (255, 210, 110), 15)
        draw_icon(canvas, panel_rect.centerx + 168, panel_rect.y + 40, "star", (255, 210, 110), 15)
        draw_text(canvas, "DÜNYA SIRALAMASI", (panel_rect.centerx, panel_rect.y + 26), 30,
                  (150, 205, 255), bold=True, center=True)
        draw_text(canvas, "En yüksek skorlar — her koşudan sonra otomatik gönderilir",
                  (panel_rect.centerx, panel_rect.y + 54), 11, (150, 165, 195), center=True, shadow=False)
        pygame.draw.line(canvas, (70, 120, 190), (head.x, head.bottom), (head.right, head.bottom), 2)

        body_top = panel_rect.y + 86

        if self.online.loading:
            # dönen yükleme halkası
            for k in range(8):
                a = t * 3.4 + k * math.tau / 8
                al = 0.15 + 0.85 * ((k / 8.0 + t * 0.5) % 1.0)
                rr = max(2, int(3 * al))
                pygame.draw.circle(canvas, (120, 180, 255),
                                   (int(panel_rect.centerx + math.cos(a) * 26),
                                    int(panel_rect.centery - 20 + math.sin(a) * 26)), rr)
            draw_text(canvas, "Sıralama yükleniyor", (panel_rect.centerx, panel_rect.centery + 22),
                      18, TEXT_DIM, center=True)

        elif self.online.world_error and not self.online.world_scores:
            draw_icon(canvas, panel_rect.centerx, panel_rect.centery - 56, "shield", (110, 118, 148), 26)
            draw_text(canvas, self.online.world_error, (panel_rect.centerx, panel_rect.centery - 16),
                      17, TEXT, center=True)
            if not self.online.enabled:
                draw_text(canvas, "Geliştirici: ONLINE_API_URL değerini doldurup",
                          (panel_rect.centerx, panel_rect.centery + 14), 13, TEXT_DIM, center=True, shadow=False)
                draw_text(canvas, "server.py'yi barındırınca burası canlanır.",
                          (panel_rect.centerx, panel_rect.centery + 32), 13, TEXT_DIM, center=True, shadow=False)

        else:
            board = self.online.world_scores or []
            if not board:
                draw_icon(canvas, panel_rect.centerx, panel_rect.centery - 40, "star", (110, 118, 148), 26)
                draw_text(canvas, "Henüz çevrimiçi skor yok.",
                          (panel_rect.centerx, panel_rect.centery), 19, TEXT_DIM, center=True)
                draw_text(canvas, "İlk sırayı sen al!", (panel_rect.centerx, panel_rect.centery + 26),
                          14, TEXT_DIM, center=True, shadow=False)
            else:
                # ---- PODYUM (ilk üç) ----
                pod_h = 132
                pod = pygame.Rect(panel_rect.x + 24, body_top, panel_rect.w - 48, pod_h)
                order = [1, 0, 2]          # 2. - 1. - 3. sırayla yan yana
                slot_w = pod.w / 3
                for slot, idx in enumerate(order):
                    if idx >= len(board):
                        continue
                    e = board[idx]
                    col, shine = self._rank_style(idx)
                    cx = pod.x + slot_w * slot + slot_w / 2
                    lift = 0 if idx == 0 else 16
                    base_y = pod.bottom - 6
                    bh = pod_h - 44 - lift
                    step = pygame.Rect(int(cx - slot_w * 0.34), int(base_y - bh),
                                       int(slot_w * 0.68), int(bh))
                    pygame.draw.rect(canvas, (24, 28, 44), step, border_radius=8)
                    pygame.draw.rect(canvas, col, step, width=2, border_radius=8)
                    bob = math.sin(t * 2 + idx) * 2
                    self._draw_medal(canvas, cx, step.y - 16 + bob, idx, 17, t)
                    nm = str(e.get("name", "?"))[:12]
                    is_me = my_name and nm.strip().lower() == my_name
                    draw_text(canvas, nm, (cx, step.y + 12), 15,
                              GREEN if is_me else TEXT, bold=True, center=True)
                    draw_text(canvas, fmt_num(e.get("score", 0)), (cx, step.y + 34), 19, col,
                              bold=True, center=True)
                    draw_text(canvas, f"Dalga {e.get('wave', '-')}", (cx, step.bottom - 20), 11,
                              TEXT_DIM, center=True, shadow=False)

                # ---- 4. sıradan itibaren liste ----
                hy = pod.bottom + 14
                draw_text(canvas, "#", (panel_rect.x + 44, hy), 11, TEXT_DIM, bold=True, center=True, shadow=False)
                draw_text(canvas, "OYUNCU", (panel_rect.x + 86, hy), 11, TEXT_DIM, bold=True, shadow=False)
                draw_text(canvas, "SKOR", (panel_rect.x + 470, hy), 11, TEXT_DIM, bold=True, right=True, shadow=False)
                draw_text(canvas, "DALGA", (panel_rect.x + 580, hy), 11, TEXT_DIM, bold=True, right=True, shadow=False)
                draw_text(canvas, "ÖLDÜRME", (panel_rect.right - 40, hy), 11, TEXT_DIM, bold=True, right=True, shadow=False)
                pygame.draw.line(canvas, PANEL_EDGE, (panel_rect.x + 30, hy + 18),
                                 (panel_rect.right - 30, hy + 18), 1)

                y = hy + 26
                row_h = 30
                for i, e in enumerate(board[3:11], start=3):
                    nm = str(e.get("name", "?"))[:14]
                    is_me = my_name and nm.strip().lower() == my_name
                    row = pygame.Rect(panel_rect.x + 30, int(y), panel_rect.w - 60, row_h - 4)
                    if is_me:
                        rs = pygame.Surface(row.size, pygame.SRCALPHA)
                        pygame.draw.rect(rs, (60, 150, 100, 120), rs.get_rect(), border_radius=7)
                        canvas.blit(rs, row.topleft)
                        pygame.draw.rect(canvas, GREEN, row, width=1, border_radius=7)
                    elif i % 2 == 1:
                        rs = pygame.Surface(row.size, pygame.SRCALPHA)
                        pygame.draw.rect(rs, (255, 255, 255, 12), rs.get_rect(), border_radius=7)
                        canvas.blit(rs, row.topleft)
                    tc = GREEN if is_me else TEXT_DIM
                    draw_text(canvas, str(i + 1), (panel_rect.x + 44, y + 4), 13, (120, 128, 156),
                              bold=True, center=True, shadow=False)
                    draw_text(canvas, nm, (panel_rect.x + 86, y + 4), 14, tc, bold=is_me, shadow=False)
                    draw_text(canvas, fmt_num(e.get("score", 0)), (panel_rect.x + 470, y + 4), 14,
                              TEXT if not is_me else GREEN, bold=True, right=True, shadow=False)
                    draw_text(canvas, str(e.get("wave", "-")), (panel_rect.x + 580, y + 4), 14, tc,
                              right=True, shadow=False)
                    draw_text(canvas, fmt_num(e.get("kills", 0)), (panel_rect.right - 40, y + 4), 14, tc,
                              right=True, shadow=False)
                    y += row_h

        w, h = 200, 44
        btn = Button((panel_rect.centerx - w - 8, panel_rect.bottom - 58, w, h), "YENİLE",
                     lambda: self.online.fetch_world_scores_async())
        btn2 = Button((panel_rect.centerx + 8, panel_rect.bottom - 58, w, h), "GERİ",
                      lambda: self.set_state(STATE_MENU))
        for b in (btn, btn2):
            b.update(mouse_pos, dt)
            b.draw(canvas)
            if clicked:
                b.click(mouse_pos)

    # ---------------- KİTAPLIK (görevle açılan kitaplar) ----------------
    # Görev istatistiklerinin nasıl ilerletileceğini anlatan ipuçları —
    # kilitli bir kitabı açan oyuncu ne yapması gerektiğini net görsün.
    UNLOCK_HINTS = {
        "total_dashes":  "İpucu: SHIFT veya SAĞ TIK ile dash at. Her koşuda onlarca kez kullanırsın.",
        "best_run_dashes": "İpucu: Tek koşuda bol bol dash at; Sis Adımı bekleme süresini kısaltır.",
        "total_crits":   "İpucu: Markette kritik şansı veren eşyaları al, kritik sayın hızla artar.",
        "total_bonks":   "İpucu: SPACE ile BONK at. Bekleme süresi kısa — kalabalıkta sürekli kullan.",
        "total_bonk_hits": "İpucu: BONK'u kalabalığın ortasında kullan; her düşman ayrı sayılır.",
        "best_run_heal": "İpucu: Kan emme / can yenileme al ve uzun bir koşuda hasar alıp iyileş.",
        "total_healed":  "İpucu: Şifa veren her şey sayılır: iksir, can yenileme, kan emme.",
        "best_run_kills":"İpucu: Tek bir koşuda mümkün olduğunca uzun hayatta kal.",
        "total_kills":   "İpucu: Bu sayaç tüm koşuların toplamıdır — oynadıkça kendiliğinden dolar.",
        "bosses":        "İpucu: Patronlar 10., 15., 20. ... dalgalarda gelir. Her devirdiğin sayılır.",
        "best_wave":     "İpucu: Dalga hedefini hızlı doldur — dalgalar skorla ilerler.",
        "best_combo":    "İpucu: Düşmanları arka arkaya, ara vermeden öldür; kombo sayacı sağ üstte.",
        "total_shots":   "İpucu: Çoklu Atış her tıkta birden fazla mermi sayar — sayaç çok daha hızlı dolar.",
        "total_lifesteal": "İpucu: Kan Emici'nin seviyesi arttıkça çalınan can katlanır.",
        "total_gold":    "İpucu: Altını yerden TOPLAMAN gerekir; toplama menzilini artır.",
        "runs":          "İpucu: Koşuyu bitirmen yeterli — ölmek de sayılır.",
        "total_time":    "İpucu: Arenada geçirdiğin toplam süre; uzun koşular hızlı doldurur.",
    }

    def _book_sort_key(self, bk):
        """Listeleme sırası: önce açık olanlar, sonra göreve en yakın olanlar."""
        owned = self.save.owns_book(bk["key"])
        return (0 if owned else 1, -book_frac(self.save, bk) if not owned else 0)

    def update_book_market(self, dt, mouse_pos, clicked, wheel_y=0):
        canvas = self.display.canvas
        self.bg.draw(canvas)

        owned_n = sum(1 for b in BOOKS if self.save.owns_book(b["key"]))
        rare_n = sum(1 for b in BOOKS if b.get("rare"))

        if self.book_filter == "owned":
            items = [b for b in BOOKS if self.save.owns_book(b["key"])]
        elif self.book_filter == "locked":
            items = [b for b in BOOKS if not self.save.owns_book(b["key"])]
        elif self.book_filter == "rare":
            items = [b for b in BOOKS if b.get("rare")]
        else:
            items = list(BOOKS)
        # Kilitli sekmesinde göreve en yakın kitap en üste gelir.
        if self.book_filter == "locked":
            items.sort(key=self._book_sort_key)

        cols = 4
        card_w, card_h = 268, 244
        gap_x, gap_y = 18, 18
        start_x = (VIRTUAL_W - (cols * card_w + (cols - 1) * gap_x)) / 2
        list_top = 158
        list_bottom = VIRTUAL_H - 70
        list_h = list_bottom - list_top

        rows = math.ceil(len(items) / cols) if items else 1
        content_h = rows * card_h + max(0, rows - 1) * gap_y
        max_scroll = max(0, content_h - list_h)

        list_rect = pygame.Rect(0, list_top, VIRTUAL_W, list_h)
        if max_scroll > 0 and list_rect.collidepoint(mouse_pos) and not self.book_detail:
            self.book_scroll -= wheel_y * 46
        self.book_scroll = clamp(self.book_scroll, 0, max_scroll)

        # Detay penceresi açıkken arkadaki liste tıklamaları yutulmalı.
        list_click = clicked and not self.book_detail
        opened_now = False

        prev_clip = canvas.get_clip()
        canvas.set_clip(list_rect)
        for i, bk in enumerate(items):
            col_i, row = i % cols, i // cols
            y = list_top + row * (card_h + gap_y) - self.book_scroll
            if y + card_h < list_top or y > list_bottom:
                continue
            rect = pygame.Rect(start_x + col_i * (card_w + gap_x), y, card_w, card_h)
            owned = self.save.owns_book(bk["key"])
            cur, need, done = book_progress(self.save, bk)
            hover = (rect.collidepoint(mouse_pos) and list_rect.collidepoint(mouse_pos)
                     and not self.book_detail)
            # Hover'da kart hafifçe yukarı kalkar.
            if hover:
                rect = rect.move(0, -3)

            rare = bool(bk.get("rare"))
            edge = (GOLD if rare else GREEN) if owned else (58, 60, 78)
            if hover:
                add_glow(canvas, rect.centerx, rect.centery, 128, edge, 0.13)
            panel(canvas, rect, bg=(34, 31, 54) if hover else (20, 22, 36),
                  edge=lighten(edge, 0.25) if hover else edge, alpha=242, radius=14, edge_w=2)

            # ---- üst şerit: nadirlik / durum ----
            strip_col = GOLD if (rare and owned) else (edge if owned else (72, 66, 96))
            strip = pygame.Surface((rect.w - 26, 3), pygame.SRCALPHA)
            pygame.draw.rect(strip, (*strip_col, 200), strip.get_rect(), border_radius=2)
            canvas.blit(strip, (rect.x + 13, rect.y + 7))

            if rare:
                draw_icon(canvas, rect.x + 19, rect.y + 22, "star", GOLD if owned else (128, 112, 70), 6)
                draw_text(canvas, "NADİR", (rect.x + 27, rect.y + 16), 10,
                          GOLD if owned else (128, 112, 70), bold=True, shadow=False)
            if owned and not rare:
                draw_text(canvas, "AÇIK", (rect.x + 17, rect.y + 16), 10, GREEN, bold=True, shadow=False)

            draw_book(canvas, rect.centerx, rect.y + 84, 92 if hover else 86,
                      bk, self.t, locked=not owned)

            draw_text(canvas, bk["name"], (rect.centerx, rect.y + 138), 15, TEXT,
                      bold=True, center=True)
            for j, ln in enumerate(wrap_text(bk["desc"], 10, rect.w - 26)[:2]):
                draw_text(canvas, ln, (rect.centerx, rect.y + 159 + j * 13), 10,
                          TEXT_DIM, center=True, shadow=False)

            # ---- alt bölüm: görev durumu (çok şartlı) ----
            unl = bk.get("unlock")
            if owned:
                draw_icon(canvas, rect.centerx - 36, rect.bottom - 34, "star", GREEN, 6)
                draw_text(canvas, "AÇILDI", (rect.centerx + 6, rect.bottom - 40), 13, GREEN,
                          bold=True, center=True)
            else:
                for j, ln in enumerate(wrap_text(unl.get("text", ""), 10, rect.w - 26)[:1]):
                    draw_text(canvas, ln, (rect.centerx, rect.bottom - 58 + j * 12), 10,
                              (200, 180, 120), center=True, shadow=False)
                # Şart rozetleri: tamamlanan şartlar yeşil, kalanlar soluk.
                reqs = book_reqs(bk)
                bxw = 12
                bx0 = rect.centerx - (len(reqs) * bxw) / 2
                for j, rq in enumerate(reqs):
                    _c, _n, rdone, _t = book_req_state(self.save, rq)
                    pygame.draw.circle(canvas, GREEN if rdone else (86, 80, 104),
                                       (int(bx0 + j * bxw + 5), rect.bottom - 44), 4)
                pb = pygame.Rect(rect.x + 22, rect.bottom - 32, rect.w - 44, 9)
                frac = book_frac(self.save, bk)
                draw_bar(canvas, pb, frac, (215, 175, 90), radius=4)
                draw_text(canvas, f"{cur} / {need} GÖREV  (%{int(frac * 100)})",
                          (rect.centerx, rect.bottom - 20), 10, TEXT_DIM,
                          center=True, shadow=False)

            # Hover'da "oku" ipucu — kitabın tıklanabilir olduğu belli olsun.
            if hover:
                draw_text(canvas, "OKUMAK İÇİN TIKLA  »", (rect.centerx, rect.bottom - 11), 9,
                          lighten(edge, 0.3), bold=True, center=True, shadow=False)

            if list_click and hover:
                # DÜZELTME: kitap açılırken bu karenin tıklaması BURADA tüketilir.
                # Eskiden aynı tıklama alttaki _draw_book_detail'e de geçiyor ve
                # pencere "panel dışına tıklandı" sayılıp anında kapanıyordu; bu
                # yüzden sadece ekranın ortasındaki kitaplar açılabiliyordu.
                self.book_detail = bk["key"]
                self.book_detail_t = 0.0
                opened_now = True
                sfx("click", 0.5, 0.0)
        canvas.set_clip(prev_clip)

        if max_scroll > 0:
            draw_scrollbar(canvas, VIRTUAL_W - 16, list_top, list_h, content_h, self.book_scroll)

        # ---- üst şerit ----
        top = pygame.Rect(0, 0, VIRTUAL_W, 96)
        s = pygame.Surface(top.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (12, 13, 22, 235), top)
        canvas.blit(s, (0, 0))
        pygame.draw.line(canvas, (92, 70, 140), (0, 96), (VIRTUAL_W, 96), 2)
        draw_icon(canvas, 30, 30, "book", (186, 150, 255), 13)
        draw_text(canvas, "KİTAPLIK", (52, 18), 26, (186, 150, 255), bold=True)
        draw_text(canvas,
                  "Kitaplar görevle açılır — açtığın kitaplar seviye atlayınca karşına çıkar.",
                  (52, 50), 11, TEXT_DIM, shadow=False)

        # sağ üst: genel ilerleme çubuğu
        pbw = 250
        pbx = VIRTUAL_W - pbw - 40
        draw_text(canvas, f"{owned_n}/{len(BOOKS)} KİTAP AÇIK", (pbx, 20), 12,
                  GOLD if owned_n >= len(BOOKS) else TEXT, bold=True, shadow=False)
        draw_bar(canvas, pygame.Rect(pbx, 40, pbw, 10), owned_n / max(1, len(BOOKS)),
                 GOLD if owned_n >= len(BOOKS) else (168, 132, 245), radius=5)
        draw_text(canvas, f"%{int(owned_n / max(1, len(BOOKS)) * 100)}", (pbx + pbw + 8, 38), 11,
                  TEXT_DIM, bold=True, shadow=False)

        # ---- filtre sekmeleri ----
        tabs = [("all", f"TÜMÜ ({len(BOOKS)})"),
                ("owned", f"AÇIK ({owned_n})"),
                ("locked", f"KİLİTLİ ({len(BOOKS) - owned_n})"),
                ("rare", f"NADİR ({rare_n})")]
        tab_w, tab_h, tab_gap = 168, 34, 10
        tabs_x = (VIRTUAL_W - (tab_w * len(tabs) + tab_gap * (len(tabs) - 1))) / 2
        for i, (key, label) in enumerate(tabs):
            r = pygame.Rect(tabs_x + i * (tab_w + tab_gap), 106, tab_w, tab_h)
            active = self.book_filter == key
            hov = r.collidepoint(mouse_pos) and not self.book_detail
            bg = (78, 56, 118) if active else ((34, 32, 52) if hov else (22, 24, 38))
            pygame.draw.rect(canvas, bg, r, border_radius=9)
            pygame.draw.rect(canvas, (168, 132, 245) if active else PANEL_EDGE, r,
                             width=2, border_radius=9)
            draw_text(canvas, label, r.center, 14, TEXT if active else TEXT_DIM,
                      bold=True, center=True)
            if list_click and hov and not active:
                self.book_filter = key
                self.book_scroll = 0.0
                sfx("click", 0.5, 0.0)

        if not items:
            draw_text(canvas, "Bu listede kitap yok.", (VIRTUAL_W / 2, list_top + 70), 16,
                      TEXT_DIM, center=True)

        btn = Button((VIRTUAL_W / 2 - 110, VIRTUAL_H - 58, 220, 44), "ANA MENÜYE DÖN",
                     lambda: self.set_state(STATE_MENU))
        btn.update(mouse_pos, dt)
        btn.draw(canvas)
        if list_click:
            btn.click(mouse_pos)

        if self.book_detail:
            # Kitabı açan tıklama yukarıda tüketildi; pencereye geçirilmez.
            self._draw_book_detail(canvas, dt, mouse_pos, clicked and not opened_now)

    def _draw_book_detail(self, canvas, dt, mouse_pos, clicked):
        """Kitaba tıklayınca açılan OKUMA penceresi.

        Kitap gerçekten açılır: iki sayfalık bir yayılım çizilir; sol sayfada
        kitabın kendisi ve künyesi, sağ sayfada etkisi ile (kilitliyse) açılış
        görevi, ilerleme çubuğu ve nasıl ilerletileceğine dair ipucu bulunur.
        """
        bk = BOOK_BY_KEY.get(self.book_detail)
        if not bk:
            self.book_detail = None
            return
        owned = self.save.owns_book(bk["key"])
        cur, need, done = book_progress(self.save, bk)
        unl = bk.get("unlock")
        rare = bool(bk.get("rare"))
        edge = (GOLD if rare else GREEN) if owned else (198, 160, 96)

        self.book_detail_t = min(1.0, self.book_detail_t + dt / 0.22)
        k = ease_out_cubic(self.book_detail_t)

        ov = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
        pygame.draw.rect(ov, (5, 6, 12, int(212 * k)), ov.get_rect())
        canvas.blit(ov, (0, 0))

        BW, BH = 900, 516
        book_rect = pygame.Rect(0, 0, int(BW * (0.55 + 0.45 * k)), int(BH * (0.55 + 0.45 * k)))
        book_rect.center = (VIRTUAL_W // 2, VIRTUAL_H // 2 - 10)

        if k < 0.45:
            # --- açılma anı: kapalı kitap büyüyerek gelir ---
            draw_book(canvas, book_rect.centerx, book_rect.centery,
                      int(200 * (0.5 + k)), bk, self.t, locked=not owned)
            return

        add_glow(canvas, book_rect.centerx, book_rect.centery, 320, edge, 0.10)
        left, right = draw_book_open(canvas, book_rect, bk, self.t, locked=not owned)

        # ================= SOL SAYFA: künye =================
        draw_book(canvas, left.centerx, left.y + 112, 150, bk, self.t, locked=not owned, glow=False)

        ny = left.y + 208
        for ln in wrap_text(bk["name"], 25, left.w - 40)[:2]:
            draw_text(canvas, ln, (left.centerx, ny), 25, (46, 38, 26), bold=True,
                      center=True, shadow=False)
            ny += 28

        # nadirlik rozeti
        badge_txt = "NADİR KİTAP" if rare else "KİTAP"
        badge_col = (168, 122, 30) if rare else (96, 88, 74)
        bw = text_width(badge_txt, 12, True) + (34 if rare else 24)
        br = pygame.Rect(0, 0, int(bw), 22)
        br.center = (left.centerx, int(ny + 12))
        pygame.draw.rect(canvas, badge_col, br, width=1, border_radius=11)
        if rare:
            draw_icon(canvas, br.x + 13, br.centery, "star", badge_col, 6)
            draw_text(canvas, badge_txt, (br.centerx + 7, br.centery - 7), 12, badge_col,
                      bold=True, center=True, shadow=False)
        else:
            draw_text(canvas, badge_txt, (br.centerx, br.centery - 7), 12, badge_col,
                      bold=True, center=True, shadow=False)

        # durum satırı
        sy = ny + 46
        if owned:
            draw_icon(canvas, left.centerx - 44, sy + 7, "star", (44, 116, 72), 7)
            draw_text(canvas, "AÇILDI", (left.centerx + 10, sy), 15, (44, 116, 72),
                      bold=True, center=True, shadow=False)
            draw_text(canvas, "Seviye atladığında karşına çıkabilir.", (left.centerx, sy + 22), 11,
                      (108, 100, 84), center=True, shadow=False)
        else:
            draw_icon(canvas, left.centerx - 46, sy + 7, "shield", (150, 92, 40), 7)
            draw_text(canvas, "KİLİTLİ", (left.centerx + 10, sy), 15, (150, 92, 40),
                      bold=True, center=True, shadow=False)
            draw_text(canvas, "Görevi tamamla, kalıcı olarak açılsın.", (left.centerx, sy + 22), 11,
                      (108, 100, 84), center=True, shadow=False)

        # ---- sol sayfa alt künyesi ----
        iy = sy + 56
        pygame.draw.line(canvas, (206, 196, 172), (left.x + 40, iy), (left.right - 40, iy), 1)
        iy += 14
        rows = [("TÜRÜ", "Nadir Kitap" if rare else
                 ("Temel Kitap" if bk.get("basic") else "Standart Kitap")),
                ("NEREDE ÇIKAR", "Seviye atlama ekranı"),
                ("GÖREV SAYISI", f"{cur} / {need} tamam")]
        for lab, val in rows:
            draw_text(canvas, lab, (left.x + 42, iy), 10, (140, 128, 104), bold=True, shadow=False)
            draw_text(canvas, val, (left.right - 42, iy), 11, (66, 58, 44), bold=True,
                      shadow=False, right=True)
            iy += 20

        # sayfa numarası / künye satırı
        idx = BOOKS.index(bk) + 1 if bk in BOOKS else 0
        draw_text(canvas, f"— {idx} —", (left.centerx, left.bottom - 26), 11, (158, 148, 126),
                  center=True, shadow=False)

        # ================= SAĞ SAYFA: etki + görev =================
        y = right.y + 26
        draw_text(canvas, "ETKİSİ", (right.centerx, y), 13, (150, 96, 30), bold=True,
                  center=True, shadow=False)
        y += 24
        for ln in wrap_text(bk["desc"], 16, right.w - 52):
            draw_text(canvas, ln, (right.centerx, y), 16, (44, 36, 26), center=True, shadow=False)
            y += 23

        y += 12
        pygame.draw.line(canvas, (206, 196, 172), (right.x + 26, y), (right.right - 26, y), 1)
        y += 16

        draw_text(canvas, "AÇILIŞ GÖREVLERİ", (right.centerx, y), 13, (150, 96, 30),
                  bold=True, center=True, shadow=False)
        y += 20
        for ln in wrap_text(unl.get("text", ""), 13, right.w - 52)[:2]:
            draw_text(canvas, ln, (right.centerx, y), 13, (108, 100, 84),
                      center=True, shadow=False)
            y += 17
        y += 6

        # ---- şart listesi: her şart ayrı satır + kendi çubuğu ----
        reqs = book_reqs(bk)
        for rq in reqs:
            rcur, rneed, rdone, rtext = book_req_state(self.save, rq)
            mark_col = (44, 140, 84) if rdone else (176, 128, 52)
            pygame.draw.circle(canvas, mark_col, (int(right.x + 34), int(y + 8)), 6,
                               0 if rdone else 2)
            if rdone:
                pygame.draw.lines(canvas, (245, 242, 232), False,
                                  [(right.x + 31, y + 8), (right.x + 33, y + 11),
                                   (right.x + 37, y + 5)], 2)
            tx = right.x + 48
            lines = wrap_text(rtext, 12, right.w - 96)[:2]
            for ln in lines:
                draw_text(canvas, ln, (tx, y), 12,
                          (52, 92, 66) if rdone else (52, 44, 32), bold=True, shadow=False)
                y += 16
            if rq.get("kind", "stat") in ("stat", "shop") and not rdone:
                frac = clamp(rcur / max(1, rneed), 0.0, 1.0)
                pb = pygame.Rect(int(tx), int(y + 1), right.w - 96, 8)
                draw_bar(canvas, pb, frac, (208, 158, 60),
                         bg=(214, 206, 184), border=(176, 166, 142), radius=4)
                draw_text(canvas,
                          f"{fmt_num(int(rcur))} / {fmt_num(int(rneed))}  "
                          f"(%{int(frac * 100)}  ·  {fmt_num(max(0, int(rneed) - int(rcur)))} kaldı)",
                          (tx, y + 11), 10, (110, 100, 82), shadow=False)
                y += 24
            elif not rdone:
                draw_text(canvas, "henüz tamamlanmadı", (tx, y), 10, (150, 118, 70), shadow=False)
                y += 15
            y += 5

        # ---- genel durum ----
        y += 2
        pygame.draw.line(canvas, (206, 196, 172), (right.x + 26, y), (right.right - 26, y), 1)
        y += 12
        frac_all = book_frac(self.save, bk)
        pb = pygame.Rect(right.x + 40, int(y), right.w - 80, 13)
        draw_bar(canvas, pb, frac_all, (44, 140, 84) if done else (208, 158, 60),
                 bg=(214, 206, 184), border=(176, 166, 142), radius=6)
        y += 20
        if owned:
            draw_text(canvas, f"AÇILDI — {need}/{need} görev tamam", (right.centerx, y), 13,
                      (44, 116, 72), bold=True, center=True, shadow=False)
        elif done:
            draw_text(canvas, "GÖREVLER TAMAM — kitap açıldı!", (right.centerx, y), 13,
                      (44, 116, 72), bold=True, center=True, shadow=False)
        else:
            draw_text(canvas, f"{cur}/{need} görev tamamlandı  (%{int(frac_all * 100)})",
                      (right.centerx, y), 13, (96, 88, 74), center=True, shadow=False)
        y += 22
        if not owned:
            # İlk tamamlanmamış şartın ipucu
            for rq in reqs:
                if book_req_state(self.save, rq)[2]:
                    continue
                hint = self.UNLOCK_HINTS.get(rq.get("stat", ""))
                if rq.get("kind") == "ach":
                    hint = "İpucu: BAŞARIMLAR ekranından bu başarımın nasıl açıldığını okuyabilirsin."
                elif rq.get("kind") == "shop":
                    hint = "İpucu: Koşu içi MARKET'i B tuşuyla aç; altın biriktirip seviyesini yükselt."
                elif rq.get("kind") == "book":
                    hint = "İpucu: Önce bu kitabın şartı olan diğer kitabı açman gerekiyor."
                if hint:
                    for ln in wrap_text(hint, 11, right.w - 52)[:3]:
                        draw_text(canvas, ln, (right.centerx, y), 11, (126, 110, 78),
                                  center=True, shadow=False)
                        y += 15
                break

        draw_text(canvas, f"— {(BOOKS.index(bk) + 1 if bk in BOOKS else 0)} —",
                  (right.centerx, right.bottom - 26), 11, (158, 148, 126),
                  center=True, shadow=False)

        # ================= KAPAT =================
        cb = pygame.Rect(0, 0, 190, 40)
        cb.center = (book_rect.centerx, book_rect.bottom + 34)
        hov = cb.collidepoint(mouse_pos)
        pygame.draw.rect(canvas, (56, 60, 88) if hov else (32, 34, 52), cb, border_radius=10)
        pygame.draw.rect(canvas, edge if hov else PANEL_EDGE, cb, width=2, border_radius=10)
        draw_text(canvas, "KAPAT  (ESC)", cb.center, 15, TEXT, bold=True, center=True)

        if clicked and (hov or not book_rect.collidepoint(mouse_pos)):
            self.book_detail = None
            sfx("click", 0.5, 0.0)

    # ---------------- SKIN MARKET ----------------
    def update_skin_market(self, dt, mouse_pos, clicked, wheel_y=0):
        canvas = self.display.canvas
        self.bg.draw(canvas)

        cols = 4

        card_w, card_h = 270, 208
        gap_x, gap_y = 20, 18
        start_x = (VIRTUAL_W - (cols * card_w + (cols - 1) * gap_x)) / 2
        list_top = 100
        list_bottom = VIRTUAL_H - 72  # alt buton için yer bırak
        list_h = list_bottom - list_top
        equipped = self.save.equipped_skin_id()

        rows = math.ceil(len(SKINS) / cols)
        content_h = rows * card_h + max(0, rows - 1) * gap_y
        max_scroll = max(0, content_h - list_h)

        list_rect = pygame.Rect(0, list_top, VIRTUAL_W, list_h)
        if max_scroll > 0 and list_rect.collidepoint(mouse_pos):
            self.skin_scroll -= wheel_y * 46
        self.skin_scroll = clamp(self.skin_scroll, 0, max_scroll)

        prev_clip = canvas.get_clip()
        canvas.set_clip(list_rect)
        for i, sk in enumerate(SKINS):
            col_i, row = i % cols, i // cols
            y = list_top + row * (card_h + gap_y) - self.skin_scroll
            if y + card_h < list_top or y > list_bottom:
                continue
            rect = pygame.Rect(start_x + col_i * (card_w + gap_x), y, card_w, card_h)
            owned = self.save.owns_skin(sk["id"])
            is_equipped = equipped == sk["id"]
            hover = rect.collidepoint(mouse_pos) and list_rect.collidepoint(mouse_pos)
            premium = bool(sk.get("premium"))
            affordable = (not premium) and self.save.get_gems() >= skin_gem_cost(sk)
            edge = GOLD if is_equipped else (sk["color"] if (owned or affordable or premium) else (60, 62, 82))
            panel(canvas, rect, bg=(30, 34, 54) if hover else (20, 22, 36), edge=edge, alpha=240, radius=14, edge_w=2)

            cc = (rect.centerx, rect.y + 60)
            draw_skin_preview(canvas, sk, cc[0], cc[1], self.t, r=19)
            if premium:
                bw = text_width("PREMİUM", 10, True) + 18
                br = pygame.Rect(0, 0, int(bw), 20)
                br.center = (rect.centerx, rect.y + 2)
                bs = pygame.Surface(br.size, pygame.SRCALPHA)
                pygame.draw.rect(bs, (*PURPLE, 240), bs.get_rect(), border_radius=10)
                canvas.blit(bs, br.topleft)
                draw_text(canvas, "PREMİUM", br.center, 10, WHITE, bold=True,
                          center=True, shadow=False)

            draw_text(canvas, sk["name"], (rect.centerx, rect.y + 104), 15, TEXT, bold=True, center=True)
            for j, ln in enumerate(wrap_text(sk["desc"], 10, rect.w - 24)[:2]):
                draw_text(canvas, ln, (rect.centerx, rect.y + 124 + j * 13), 10, TEXT_DIM, center=True, shadow=False)
            # ---- özel yetenek rozeti ----
            ult = get_skin_ult(sk["id"])
            if ult:
                ucol = tuple(ult.get("color", GOLD))
                uy = rect.y + 152
                draw_icon(canvas, rect.x + 16, uy + 6, ult.get("icon", "star"), ucol, 6)
                draw_text(canvas, ult["name"], (rect.x + 28, uy), 10, ucol, bold=True, shadow=False)
                draw_text(canvas, f"{int(round(ult['cd']))} sn", (rect.right - 14, uy), 10,
                          TEXT_DIM, bold=True, right=True, shadow=False)

            if is_equipped:
                draw_text(canvas, "KUŞANILDI", (rect.centerx, rect.bottom - 20), 13, GOLD, bold=True, center=True)
            elif owned:
                draw_text(canvas, "SAHİPSİN — detaylar için tıkla", (rect.centerx, rect.bottom - 18), 10, TEXT_DIM, center=True, shadow=False)
            elif premium:
                # Premium skin: elmasla değil, MAĞAZA'dan gerçek parayla alınır.
                draw_text(canvas, f"PREMİUM  ·  {sk.get('price_hint', '')}",
                          (rect.centerx, rect.bottom - 27), 14, PURPLE, bold=True, center=True)
                draw_text(canvas, "MAĞAZA'dan alınır", (rect.centerx, rect.bottom - 12), 10,
                          TEXT_DIM, center=True, shadow=False)
            else:
                pcol = GEM_COLOR if affordable else (100, 105, 130)
                cost_txt = str(skin_gem_cost(sk))
                tw = text_width(cost_txt, 15, True)
                draw_icon(canvas, rect.centerx - tw / 2 - 11, rect.bottom - 20, "gem", pcol, 8)
                draw_text(canvas, cost_txt, (rect.centerx - tw / 2 + 4, rect.bottom - 27), 15, pcol, bold=True)

            if clicked and hover:
                self.detail_skin_id = sk["id"]
                self.set_state(STATE_SKIN_DETAIL)
                sfx("click", 0.6, 0.0)
        canvas.set_clip(prev_clip)

        if max_scroll > 0:
            draw_scrollbar(canvas, VIRTUAL_W - 16, list_top, list_h, content_h, self.skin_scroll)

        top = pygame.Rect(0, 0, VIRTUAL_W, 80)
        s = pygame.Surface(top.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (12, 13, 22, 235), top)
        canvas.blit(s, (0, 0))
        draw_text(canvas, "SKIN MARKET", (40, 24), 28, GEM_COLOR, bold=True)
        gem_txt = f"Elmas: {fmt_num(self.save.get_gems())}"
        tw = text_width(gem_txt, 21, True)
        draw_icon(canvas, VIRTUAL_W - 40 - tw - 22, 40, "gem", GEM_COLOR, 11)
        draw_text(canvas, gem_txt, (VIRTUAL_W - 40 - tw, 28), 21, GEM_COLOR, bold=True)

        btn = Button((VIRTUAL_W / 2 - 110, VIRTUAL_H - 58, 220, 44), "ANA MENÜYE DÖN", lambda: self.set_state(STATE_MENU))
        btn.update(mouse_pos, dt)
        btn.draw(canvas)
        if clicked:
            btn.click(mouse_pos)

    # ---------------- SKIN DETAY (ÖZELLİKLER) ----------------
    def _equip_detail_skin(self):
        sk_id = self.detail_skin_id
        if sk_id and self.save.owns_skin(sk_id):
            self.save.equip_skin(sk_id)
            self.selected_skin = sk_id
            sfx("click", 0.6, 0.0)

    def _play_with_detail_skin(self):
        sk_id = self.detail_skin_id
        if sk_id and self.save.owns_skin(sk_id):
            self.save.equip_skin(sk_id)
            self.selected_skin = sk_id
            self.start_run()

    def _buy_detail_skin(self):
        sk_id = self.detail_skin_id
        sk = SKIN_BY_ID.get(sk_id)
        if not sk:
            return
        if sk.get("premium"):
            # Premium skin elmasla alınmaz: oyuncuyu MAĞAZA'ya yönlendir.
            self.store_tab = "skins"
            self.goto(STATE_GEM_STORE)
            return
        if self.save.get_gems() >= skin_gem_cost(sk):
            if self.save.buy_skin(sk_id, skin_gem_cost(sk)):
                self.save.equip_skin(sk_id)
                self.selected_skin = sk_id
                self.ach.unlock("fashion")
                sfx("buy", 1.0, 0.0)
                self.set_state(STATE_SKIN_MARKET)
        else:
            sfx("error", 0.6, 0.0)

    def update_skin_detail(self, dt, mouse_pos, clicked):
        canvas = self.display.canvas
        self.bg.draw(canvas)
        sk = SKIN_BY_ID.get(self.detail_skin_id) or SKINS[0]

        panel_rect = pygame.Rect(0, 0, 540, 618)
        panel_rect.center = (VIRTUAL_W / 2, VIRTUAL_H / 2)
        panel(canvas, panel_rect, alpha=250, edge=sk["color"], edge_w=3)

        back_rect = pygame.Rect(panel_rect.x + 14, panel_rect.y + 14, 90, 28)
        hover_back = back_rect.collidepoint(mouse_pos)
        draw_text(canvas, "‹ GERİ", (back_rect.x, back_rect.y + 5), 14, GOLD if hover_back else TEXT_DIM, bold=hover_back, shadow=False)
        if clicked and hover_back:
            self.set_state(STATE_SKIN_MARKET)

        # önizleme dairesi + canlı silah animasyonu
        cc = (panel_rect.centerx, panel_rect.y + 96)
        draw_skin_preview(canvas, sk, cc[0], cc[1], self.t, r=26)

        draw_text(canvas, sk["name"], (panel_rect.centerx, panel_rect.y + 166), 26, TEXT, bold=True, center=True)

        owned = self.save.owns_skin(sk["id"])
        is_equipped = self.save.equipped_skin_id() == sk["id"]
        affordable = (not sk.get("premium")) and self.save.get_gems() >= skin_gem_cost(sk)

        status_y = panel_rect.y + 208
        if is_equipped:
            draw_text(canvas, "KUŞANILMIŞ DURUMDA", (panel_rect.centerx, status_y), 13, GOLD, bold=True, center=True)
        elif owned:
            draw_text(canvas, "SAHİPSİN", (panel_rect.centerx, status_y), 13, GREEN, bold=True, center=True)
        elif sk.get("premium"):
            draw_text(canvas, f"PREMİUM SKİN  ·  {sk.get('price_hint', '')}",
                      (panel_rect.centerx, status_y), 15, PURPLE, bold=True, center=True)
        else:
            cost_txt = f"{skin_gem_cost(sk)} Elmas"
            draw_text(canvas, cost_txt, (panel_rect.centerx, status_y), 15,
                      GEM_COLOR if affordable else (150, 90, 90), bold=True, center=True)

        y = panel_rect.y + 234
        for ln in wrap_text(sk["desc"], 13, panel_rect.w - 70):
            draw_text(canvas, ln, (panel_rect.centerx, y), 13, TEXT_DIM, center=True, shadow=False)
            y += 18

        y += 12
        pygame.draw.line(canvas, PANEL_EDGE, (panel_rect.x + 30, y), (panel_rect.right - 30, y), 1)
        y += 16

        # ---- ÖZEL YETENEK kutusu ----
        ult = get_skin_ult(sk["id"])
        if ult:
            ucol = tuple(ult.get("color", GOLD))
            ulines = wrap_text(ult["desc"], 11, panel_rect.w - 80)[:3]
            ub = pygame.Rect(panel_rect.x + 26, int(y), panel_rect.w - 52,
                             40 + len(ulines) * 15)
            add_glow(canvas, ub.centerx, ub.centery, 190, ucol, 0.08)
            pygame.draw.rect(canvas, (22, 24, 36), ub, border_radius=10)
            pygame.draw.rect(canvas, ucol, ub, width=2, border_radius=10)
            draw_icon(canvas, ub.x + 22, ub.y + 20, ult.get("icon", "star"), ucol, 9)
            draw_text(canvas, ult["name"], (ub.x + 38, ub.y + 11), 15, ucol, bold=True)
            auto_txt = ("otomatik  ·  " if ult.get("mode", "auto") == "auto" else "şartı oluşunca  ·  ")
            draw_text(canvas, auto_txt + f"{int(round(ult['cd']))} saniyede bir",
                      (ub.right - 12, ub.y + 13), 10, TEXT_DIM, right=True, shadow=False)
            uy = ub.y + 34
            for ln in ulines:
                draw_text(canvas, ln, (ub.x + 14, uy), 11, TEXT, shadow=False)
                uy += 15
            y = ub.bottom + 24

        draw_text(canvas, "ÖZELLİKLER", (panel_rect.centerx, y), 15, sk["color"], bold=True, center=True)
        y += 30
        perks = sk.get("perks") or []
        if perks:
            for perk in perks:
                draw_icon(canvas, panel_rect.x + 50, y + 7, "star", sk["color"], 8)
                draw_text(canvas, perk, (panel_rect.x + 68, y), 14, TEXT, shadow=False)
                y += 27
        else:
            draw_text(canvas, "Bu skin özel bir yetenek içermez — yalnızca görünüm değiştirir.",
                      (panel_rect.centerx, y), 12, TEXT_DIM, center=True, shadow=False)
            y += 27

        btn_w, btn_h, gap = 150, 46, 14
        by = panel_rect.bottom - 66
        if owned:
            play_btn = Button((panel_rect.centerx - btn_w - gap / 2, by, btn_w, btn_h), "OYNA",
                               self._play_with_detail_skin, color=(60, 130, 90), hover_color=(80, 170, 115))
            equip_label = "KUŞANILDI" if is_equipped else "KUŞAN"
            equip_btn = Button((panel_rect.centerx + gap / 2, by, btn_w, btn_h), equip_label,
                                self._equip_detail_skin, enabled=not is_equipped)
            for b in (play_btn, equip_btn):
                b.update(mouse_pos, dt)
                b.draw(canvas)
                if clicked:
                    b.click(mouse_pos)
        elif sk.get("premium"):
            buy_btn = Button((panel_rect.centerx - btn_w - gap / 2, by, btn_w, btn_h),
                              "MAĞAZA  »", self._buy_detail_skin,
                              color=(120, 60, 150), hover_color=(160, 90, 200))
            cancel_btn = Button((panel_rect.centerx + gap / 2, by, btn_w, btn_h), "GERİ",
                                 lambda: self.set_state(STATE_SKIN_MARKET))
            for b in (buy_btn, cancel_btn):
                b.update(mouse_pos, dt)
                b.draw(canvas)
                if clicked:
                    b.click(mouse_pos)
            return
        else:
            buy_btn = Button((panel_rect.centerx - btn_w - gap / 2, by, btn_w, btn_h),
                              "SATIN AL", self._buy_detail_skin, color=(150, 120, 40), hover_color=(190, 155, 60),
                              enabled=affordable)
            cancel_btn = Button((panel_rect.centerx + gap / 2, by, btn_w, btn_h), "GERİ",
                                 lambda: self.set_state(STATE_SKIN_MARKET))
            for b in (buy_btn, cancel_btn):
                b.update(mouse_pos, dt)
                b.draw(canvas)
                if clicked:
                    b.click(mouse_pos)

    # ---------------- KIYAFET MARKET ----------------
    def _cosmetic_preview(self, canvas, cx, cy, radius, slot, item_id, t):
        """Bir kıyafet öğesinin küçük önizlemesini basit bir avatar üstünde çizer."""
        fake = type("FP", (), {})()
        fake.radius = radius
        # Önizlemede karakter EKRANA DOĞRU bakar (aşağı). Böylece gözlüğün iki
        # camı yan yana, şapkanın siperliği öne doğru görünür — kıyafet tepeden
        # bakışta bir çizgiye dönüşmek yerine gerçekten "yüz" gibi okunur.
        # Küçük salınım, parçalara canlılık katar.
        fake.aim_dir = (math.sin(t * 0.6) * 0.25, 1.0)
        fake.cosmetics = {"hat": None, "eyewear": None, "cape": None}
        fake.cosmetics[slot] = item_id
        body = (92, 100, 132)
        draw_cosmetic_cape(canvas, fake, cx, cy, t)
        pygame.draw.circle(canvas, OUTLINE, (int(cx), int(cy)), radius + 2)
        pygame.draw.circle(canvas, body, (int(cx), int(cy)), radius)
        pygame.draw.circle(canvas, lighten(body, .35), (int(cx - radius * .3), int(cy - radius * .3)), max(2, int(radius * .25)))
        draw_cosmetic_eyewear(canvas, fake, cx, cy, t)
        draw_cosmetic_hat(canvas, fake, cx, cy, t)

    def _buy_or_equip_cosmetic(self, item):
        slot = item["slot"]
        if self.save.owns_cosmetic(item["id"]):
            cur = self.save.equipped_cosmetic_id(slot)
            if cur == item["id"]:
                self.save.unequip_cosmetic(slot)
            else:
                self.save.equip_cosmetic(slot, item["id"])
            sfx("click", 0.6, 0.0)
        elif self.save.get_gems() >= item["cost"]:
            if self.save.buy_cosmetic(item["id"], item["cost"]):
                self.save.equip_cosmetic(slot, item["id"])
                sfx("buy", 1.0, 0.0)
        else:
            sfx("error", 0.6, 0.0)

    def update_cosmetic_market(self, dt, mouse_pos, clicked, wheel_y=0):
        canvas = self.display.canvas
        self.bg.draw(canvas)

        # ---- üst şerit ----
        top = pygame.Rect(0, 0, VIRTUAL_W, 96)
        s = pygame.Surface(top.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (12, 13, 22, 235), top)
        canvas.blit(s, (0, 0))
        draw_text(canvas, "KIYAFET MARKET", (40, 18), 26, CYAN, bold=True)
        if self.save.cosmetics_locked():
            # Premium skin kendi kostümüyle gelir; kıyafet slotları kilitlidir.
            sk_name = get_skin(self.save.equipped_skin_id())["name"]
            draw_text(canvas, f"{sk_name} kendi kostümüyle gelir — kıyafetler bu skinde kapalıdır.",
                      (40, 50), 11, PURPLE, bold=True, shadow=False)
        else:
            draw_text(canvas, "Şapka, gözlük ve pelerinle karakterini kişiselleştir.",
                      (40, 50), 11, TEXT_DIM, shadow=False)
        gem_txt = f"Elmas: {fmt_num(self.save.get_gems())}"
        tw = text_width(gem_txt, 20, True)
        draw_icon(canvas, VIRTUAL_W - 40 - tw - 21, 34, "gem", GEM_COLOR, 11)
        draw_text(canvas, gem_txt, (VIRTUAL_W - 40 - tw, 23), 20, GEM_COLOR, bold=True)

        # ---- sekmeler (şapka / gözlük / pelerin) ----
        tab_w, tab_h, tab_gap = 160, 36, 10
        tabs_x = (VIRTUAL_W - (tab_w * 3 + tab_gap * 2)) / 2
        tab_y = 104
        for i, slot in enumerate(COSMETIC_SLOTS):
            r = pygame.Rect(tabs_x + i * (tab_w + tab_gap), tab_y, tab_w, tab_h)
            active = self.cosmetic_tab == slot
            hover = r.collidepoint(mouse_pos)
            bg = (46, 96, 110) if active else ((32, 36, 54) if hover else (22, 24, 38))
            pygame.draw.rect(canvas, bg, r, border_radius=9)
            pygame.draw.rect(canvas, CYAN if active else PANEL_EDGE, r, width=2, border_radius=9)
            draw_text(canvas, SLOT_LABELS[slot], r.center, 15, TEXT if active else TEXT_DIM, bold=True, center=True)
            if clicked and hover and not active:
                self.cosmetic_tab = slot
                self.cosmetic_scroll = 0.0
                sfx("click", 0.5, 0.0)

        # ---- kart ızgarası ----
        list_top = 158
        items = cosmetics_by_slot(self.cosmetic_tab)
        cols = 4
        card_w, card_h = 270, 200
        gap_x, gap_y = 20, 18
        start_x = (VIRTUAL_W - (cols * card_w + (cols - 1) * gap_x)) / 2
        list_bottom = VIRTUAL_H - 70
        list_h = list_bottom - list_top

        rows = math.ceil(len(items) / cols) if items else 1
        content_h = rows * card_h + max(0, rows - 1) * gap_y
        max_scroll = max(0, content_h - list_h)

        list_rect = pygame.Rect(0, list_top, VIRTUAL_W, list_h)
        if max_scroll > 0 and list_rect.collidepoint(mouse_pos):
            self.cosmetic_scroll -= wheel_y * 46
        self.cosmetic_scroll = clamp(self.cosmetic_scroll, 0, max_scroll)

        if not items:
            draw_text(canvas, "Bu slot için parça yok.",
                      (VIRTUAL_W / 2, list_top + 60), 16, TEXT_DIM, center=True)

        prev_clip = canvas.get_clip()
        canvas.set_clip(list_rect)
        equipped_id = self.save.equipped_cosmetic_id(self.cosmetic_tab)
        for i, item in enumerate(items):
            col_i, row = i % cols, i // cols
            y = list_top + row * (card_h + gap_y) - self.cosmetic_scroll
            if y + card_h < list_top or y > list_bottom:
                continue
            rect = pygame.Rect(start_x + col_i * (card_w + gap_x), y, card_w, card_h)
            owned = self.save.owns_cosmetic(item["id"])
            is_equipped = equipped_id == item["id"]
            hover = rect.collidepoint(mouse_pos) and list_rect.collidepoint(mouse_pos)
            affordable = self.save.get_gems() >= item["cost"]
            edge = CYAN if is_equipped else (item["color"] if (owned or affordable) else (60, 62, 82))
            panel(canvas, rect, bg=(30, 34, 54) if hover else (20, 22, 36), edge=edge, alpha=240, radius=14, edge_w=2)

            cc = (rect.centerx, rect.y + 62)
            add_glow(canvas, cc[0], cc[1], 42, item["color"], .4)
            self._cosmetic_preview(canvas, cc[0], cc[1], 26, item["slot"], item["id"], self.t)

            draw_text(canvas, item["name"], (rect.centerx, rect.y + 100), 15, TEXT, bold=True, center=True)
            desc_lines = wrap_text(item["desc"], 10, rect.w - 24)[:1]
            for j, ln in enumerate(desc_lines):
                draw_text(canvas, ln, (rect.centerx, rect.y + 120 + j * 13), 10, TEXT_DIM, center=True, shadow=False)
            perk_txt = item.get("perk_text")
            if perk_txt:
                draw_icon(canvas, rect.centerx - text_width(perk_txt, 11, True) / 2 - 12, rect.y + 137, "star", item["color"], 6)
                draw_text(canvas, perk_txt, (rect.centerx, rect.y + 137), 11, item["color"], bold=True, center=True)

            if is_equipped:
                draw_text(canvas, "KUŞANILDI (çıkar için tıkla)", (rect.centerx, rect.bottom - 18), 10, CYAN, bold=True, center=True)
            elif owned:
                draw_text(canvas, "SAHİPSİN — kuşanmak için tıkla", (rect.centerx, rect.bottom - 18), 10, TEXT_DIM, center=True, shadow=False)
            else:
                pcol = GEM_COLOR if affordable else (100, 105, 130)
                cost_txt = str(item["cost"])
                tw = text_width(cost_txt, 15, True)
                draw_icon(canvas, rect.centerx - tw / 2 - 11, rect.bottom - 20, "gem", pcol, 8)
                draw_text(canvas, cost_txt, (rect.centerx - tw / 2 + 4, rect.bottom - 27), 15, pcol, bold=True)

            if clicked and hover:
                self._buy_or_equip_cosmetic(item)
        canvas.set_clip(prev_clip)

        if max_scroll > 0:
            draw_scrollbar(canvas, VIRTUAL_W - 16, list_top, list_h, content_h, self.cosmetic_scroll)

        btn = Button((VIRTUAL_W / 2 - 110, VIRTUAL_H - 58, 220, 44), "ANA MENÜYE DÖN", lambda: self.set_state(STATE_MENU))
        btn.update(mouse_pos, dt)
        btn.draw(canvas)
        if clicked:
            btn.click(mouse_pos)


# =====================================================================
# GİRİŞ NOKTASI
# =====================================================================

def main():
    app = App()
    try:
        app.run_loop()
    except Exception as e:
        try:
            app.save.save()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
