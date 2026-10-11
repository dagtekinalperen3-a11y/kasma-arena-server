"""ARENA BONK — 2 dakikalık TANITIM FİLMİ (MP4) üretir (v3.33: oyundaki turun aynısı).

Her kare oyunun GERÇEK motorudur: GameTour'un "gölge oyunu" (App(shadow_of=...))
kaydın KOPYASIYLA çalışır, savaşları insan gibi nişan alan otomatik pilot
oynar (bkz. _TourPilot), menülerde sanal imleç gezer. Gerçek kayda, hesaba ve
sunucuya hiçbir şey yazılmaz.

Ses: oyunun kendi efektleri (SFX_BUILDERS; film sırasında çalınan her efekt
zamanıyla kaydedilir) + bu araçta sentezlenen, sahne kesmelerine oturan
128 BPM bir fragman müziği.

Kullanım:
    python tools/make_trailer.py                  # trailer/arena_bonk_tanitim.mp4
    python tools/make_trailer.py --fps 30 --size 1280x720 --out film.mp4
Gerekenler: pygame(-ce), numpy, ffmpeg (PATH'te).
"""
import os
import sys
import math
import time
import wave
import random
import argparse
import subprocess

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import numpy as np          # noqa: E402
import pygame               # noqa: E402
import kasma_arena13 as K   # noqa: E402

_tc = K._tc
W, H = K.VIRTUAL_W, K.VIRTUAL_H


# =====================================================================
# SES KAYDEDİCİ — oyunun sfx() çağrılarını zamanıyla yakalar
# =====================================================================
class SfxRecorder:
    ok = True

    def __init__(self):
        self.events = []
        self.clock = lambda: 0.0
        self._last = {}

    def play(self, name, vol=1.0, gap=0.03):
        t = self.clock()
        if t - self._last.get(name, -9.0) < max(gap, 0.05):
            return
        self._last[name] = t
        self.events.append((t, name, float(vol)))

    def update(self):
        pass

    def set_music(self, *_a, **_k):
        pass


# =====================================================================
# FRAGMAN — oyundaki 2 dakikalık TANITIM TURUNUN aynısı (v3.33)
# ---------------------------------------------------------------------
# Mağazanın sağ altındaki ödüllü reklam K.GameTour'u oynatır; bu araç AYNI
# turu kare kare MP4'e yazar. Sahne listesi, alt yazılar (5 dil) ve pilot
# tek yerde (oyunun içinde) durur: film ile reklam hiç ayrışmaz.
# =====================================================================
class GameTrailer(K.GameTour):
    def __init__(self, real_app):
        super().__init__(real_app)
        sh = self.sh
        # vitrin: hesap girişli görünsün (yalnızca filmde)
        sh.account.sign_in(self.NAME, "kanka@mail.com")


# Sahnelerin müzik yoğunluğu: 0 sessiz, 1 hafif, 2 tam, 3 en yoğun
SCENE_LEVEL = {
    "intro": 1, "hook": 3, "basics": 2, "levelup": 1, "luck": 1, "arsenal": 3,
    "books": 1, "market": 1, "boss": 3, "chest": 2, "cave": 2, "hell": 3,
    "dragon": 3, "power": 3, "record": 1, "worldlb": 1, "mastery": 1,
    "skins": 1, "pets": 1, "outro": 0,
}


# =====================================================================
# MÜZİK — 128 BPM fragman müziği (numpy sentezi)
# =====================================================================
SR = 44100
BPM = 128.0
BEAT = 60.0 / BPM


def _t(n):
    return np.arange(n) / SR


def _bl_saw(freq, dur, cutoff=2400.0, detune=(0.0,)):
    """Bant sınırlı testere (toplamalı sentez): örtüşme yok, filtre yok."""
    n = int(dur * SR)
    t = _t(n)
    out = np.zeros(n)
    for dt_ in detune:
        f = freq * (2 ** (dt_ / 1200.0))
        kmax = max(1, int(cutoff / f))
        for k in range(1, min(kmax, 60) + 1):
            out += np.sin(2 * np.pi * k * f * t) / k
    return out / (len(detune) * 1.6)


def _env(n, a=0.005, r=0.08, hold=None):
    e = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    if hold is None:
        e[-nr:] *= np.linspace(1, 0, nr)
    else:
        nh = int(hold * SR)
        if nh < n:
            tail = n - nh
            e[nh:] *= np.exp(-np.arange(tail) / (r * SR))
    return e


def kick():
    n = int(0.42 * SR)
    t = _t(n)
    f = 44 + 120 * np.exp(-t * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 7.5)
    x[:int(0.004 * SR)] += np.random.uniform(-0.6, 0.6, int(0.004 * SR))
    return np.tanh(x * 1.6) * 0.95


def snare():
    n = int(0.28 * SR)
    t = _t(n)
    nz = np.random.uniform(-1, 1, n)
    nz = np.diff(np.concatenate([[0], nz]))         # parlak gürültü
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 28)
    return (nz * np.exp(-t * 16) * 0.42 + body * 0.5) * 0.8


def clap():
    n = int(0.22 * SR)
    t = _t(n)
    nz = np.diff(np.concatenate([[0], np.random.uniform(-1, 1, n)]))
    env = np.exp(-t * 22) + 0.6 * np.exp(-np.maximum(0, t - 0.012) * 30) * (t > 0.012)
    return nz * env * 0.35


def hat(open_=False):
    n = int((0.22 if open_ else 0.05) * SR)
    t = _t(n)
    nz = np.random.uniform(-1, 1, n)
    nz = np.diff(np.diff(np.concatenate([[0, 0], nz])))
    return nz * np.exp(-t * (14 if open_ else 70)) * (0.10 if open_ else 0.08)


def impact():
    n = int(2.6 * SR)
    t = _t(n)
    f = 32 + 70 * np.exp(-t * 6)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.8)
    nz = np.random.uniform(-1, 1, n)
    nz = np.diff(np.concatenate([[0], nz])) * np.exp(-t * 2.4) * 0.35
    return np.tanh((boom * 1.4 + nz)) * 0.9


def riser(dur):
    n = int(dur * SR)
    t = _t(n)
    k = t / dur
    nz = np.random.uniform(-1, 1, n)
    nz = np.diff(np.concatenate([[0], nz]))
    tone = np.sin(2 * np.pi * np.cumsum(200 + 1400 * k ** 2) / SR)
    return (nz * 0.35 + tone * 0.25) * k ** 2.2


def whoosh():
    n = int(0.5 * SR)
    t = _t(n)
    nz = np.random.uniform(-1, 1, n)
    env = np.sin(np.pi * t / 0.5) ** 2
    return np.diff(np.concatenate([[0], nz])) * env * 0.22


def midi(nn):
    return 440.0 * 2 ** ((nn - 69) / 12.0)


def bass_note(root):
    """Bas notasını duyulur aralığa (A1-G#2, 55-104 Hz) oturtur: C1 gibi
    33 Hz'lik notalar dizüstü hoparlörde hiç duyulmuyor."""
    n = root - 24
    while n < 33:
        n += 12
    while n > 44:
        n -= 12
    return n


# Am - F - C - G (epik minör)
PROG = [(57, (57, 60, 64)), (53, (53, 57, 60)), (48, (55, 60, 64)), (55, (55, 59, 62))]


def compose(total, scenes, cut_times, hits):
    """Sahne zaman çizelgesine oturan fragman müziği."""
    out = np.zeros(int(total * SR) + SR * 3)
    side = np.ones_like(out)           # kick'e göre 'sidechain' sönümü

    def add(x, at, g=1.0, duck=False):
        i = int(at * SR)
        if i >= len(out) or i < 0:
            return
        j = min(len(out), i + len(x))
        if duck:
            out[i:j] += x[:j - i] * g * side[i:j]
        else:
            out[i:j] += x[:j - i] * g

    # bölümler: (başlangıç, bitiş, yoğunluk) — 0 sessiz, 1 hafif, 2 tam, 3 en yoğun
    starts = {}
    acc = 0.0
    for nm, d, _c in scenes:
        starts[nm] = (acc, acc + d)
        acc += d
    sec = [(a, b, SCENE_LEVEL.get(nm, 2)) for nm, (a, b) in starts.items()]

    def level_at(t):
        for a, b, lv in sec:
            if a <= t < b:
                return lv
        return 0

    K_, S_, CL, HC, HO = kick(), snare(), clap(), hat(), hat(True)
    nbeats = int(total / BEAT) + 2
    # önce kick'ler (sidechain zarfı için)
    for bi in range(nbeats):
        t = bi * BEAT
        lv = level_at(t)
        if lv >= 2 or (lv == 1 and bi % 2 == 0):
            i = int(t * SR)
            dn = int(0.22 * SR)
            if i < len(side):
                j = min(len(side), i + dn)
                side[i:j] = np.minimum(side[i:j], 0.35 + 0.65 * np.linspace(0, 1, j - i) ** 0.7)
            add(K_, t, 0.95)
    for bi in range(nbeats):
        t = bi * BEAT
        lv = level_at(t)
        bar, beat_in_bar = divmod(bi, 4)
        root, chord = PROG[bar % 4]
        if lv >= 2 and beat_in_bar in (1, 3):
            add(S_, t, 0.9)
            add(CL, t + 0.004, 0.8)
        if lv == 1 and beat_in_bar == 2:
            add(CL, t, 0.7)
        if lv >= 2:
            for h in range(4 if lv == 3 else 2):
                add(HC, t + h * BEAT / (4 if lv == 3 else 2), 1.0 if h % 2 else 0.6)
            if beat_in_bar % 2 == 1:
                add(HO, t + BEAT / 2, 0.7)
        # bas: 8'likler (oktav zıplamalı)
        if lv >= 2:
            for e in range(2):
                f = midi(bass_note(root) + (12 if (e == 1 and beat_in_bar % 2) else 0))
                x = _bl_saw(f, BEAT / 2 * 0.92, cutoff=900 if lv == 2 else 1500, detune=(0.0, 7.0))
                x *= _env(len(x), 0.004, 0.06)
                add(x, t + e * BEAT / 2, 0.55, duck=True)
        elif lv == 1 and beat_in_bar == 0:
            f = midi(bass_note(root))
            x = _bl_saw(f, BEAT * 4 * 0.95, cutoff=500) * _env(int(BEAT * 4 * 0.95 * SR), 0.05, 0.6)
            add(x, t, 0.45)
        # akor yastığı (her ölçü başında)
        if beat_in_bar == 0 and lv >= 1:
            for nn in chord:
                x = _bl_saw(midi(nn), BEAT * 4 * 0.98, cutoff=2600 if lv >= 2 else 1600,
                            detune=(-11.0, 0.0, 9.0))
                x *= _env(len(x), 0.04 if lv >= 2 else 0.4, 0.5)
                add(x, t, 0.10 if lv >= 2 else 0.12, duck=lv >= 2)
        # arpej (16'lık)
        if lv >= 1:
            steps = 4 if lv >= 2 else 2
            for s_ in range(steps):
                ai = (bi * steps + s_)
                nn = chord[ai % 3] + 12 + (12 if (ai // 3) % 4 == 3 else 0)
                d = BEAT / steps * 0.8
                n = int(d * SR)
                tt = _t(n)
                x = (np.sign(np.sin(2 * np.pi * midi(nn) * tt)) * 0.5
                     + np.sin(2 * np.pi * midi(nn) * 2 * tt) * 0.3) * np.exp(-tt * 18)
                add(x, t + s_ * BEAT / steps, 0.07 if lv >= 2 else 0.06)
        # en yoğun bölümlerde lead (uzun notalar)
        if lv == 3 and beat_in_bar == 0:
            mel = [chord[2] + 12, chord[1] + 12, chord[2] + 12, chord[0] + 24]
            for q, nn in enumerate(mel):
                x = _bl_saw(midi(nn), BEAT * 0.95, cutoff=3200, detune=(-6.0, 6.0))
                vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * _t(len(x)))
                x = x * vib * _env(len(x), 0.01, 0.12)
                add(x, t + q * BEAT, 0.075, duck=True)

    # kesmeler ve vurgular
    for ct, kind in cut_times:
        if ct > 0.1:
            add(impact() if kind == "flash" else whoosh() * 1.4, ct - (0.0 if kind == "flash" else 0.12),
                0.55 if kind == "flash" else 0.9)
    for ht in hits:
        add(impact(), ht, 0.45)
        add(CL, ht, 0.8)
    # yükselişler: başlık öncesi ve final öncesi
    for at in (starts["hook"][0], starts["boss"][0], starts["power"][0]):
        r = riser(2.4)
        add(r, at - 2.4, 0.5)
    # final akoru
    o0 = starts["outro"][0]
    for nn in (45, 57, 60, 64, 69):
        x = _bl_saw(midi(nn), 5.5, cutoff=2400, detune=(-9.0, 0.0, 8.0)) * _env(int(5.5 * SR), 0.01, 1.6, hold=0.2)
        add(x, o0, 0.10)
    return out


def mix_sfx(events, total):
    """Oyunun kendi efektlerini (SFX_BUILDERS) kaydedilen anlara yerleştirir."""
    out = np.zeros(int(total * SR) + SR * 3)
    cache = {}
    window = {}
    for t, name, vol in events:
        if t > total:
            continue
        b = window.setdefault(int(t * 10), [0])
        if b[0] >= 5:              # 0.1 sn'de en çok 5 efekt (kakofoni olmasın)
            continue
        b[0] += 1
        if name not in cache:
            fn = K.SFX_BUILDERS.get(name)
            if fn is None:
                cache[name] = None
            else:
                x = np.array(fn(), dtype=np.float64)
                # oyunun örnekleme hızından 44.1 kHz'e
                src = np.arange(len(x)) / float(K._SR)
                dst = np.arange(int(len(x) * SR / K._SR)) / float(SR)
                cache[name] = np.interp(dst, src, x)
        x = cache[name]
        if x is None:
            continue
        i = int(t * SR)
        j = min(len(out), i + len(x))
        out[i:j] += x[:j - i] * vol
    return out


def write_wav(path, x):
    x = np.clip(x, -1.0, 1.0)
    pcm = (x * 32000).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        st = np.empty(len(pcm) * 2, dtype=np.int16)
        st[0::2] = pcm
        st[1::2] = pcm
        w.writeframes(st.tobytes())


# =====================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "trailer", "arena_bonk_tanitim.mp4"))
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--lang", default="tr")
    ap.add_argument("--seconds", type=float, default=0.0, help="deneme için kısa çıktı")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    random.seed(2028)
    np.random.seed(2028)

    K.ONLINE_API_URL = ""
    K.PURCHASE_API_URL = ""
    app = K.App()
    app.splash_t = 99.0
    K.CFG["lang"] = a.lang
    rec = SfxRecorder()
    K.audio = rec
    trailer = GameTrailer(app)
    rec.clock = lambda: trailer.t
    total = trailer.LENGTH if not a.seconds else min(trailer.LENGTH, a.seconds)
    nframes = int(round(total * a.fps))
    ow, oh = (int(v) for v in a.size.lower().split("x"))

    tmp_video = a.out + ".video.mp4"
    tmp_wav = a.out + ".wav"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(a.fps), "-i", "-",
           "-vf", f"scale={ow}:{oh}:flags=lanczos",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", tmp_video]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    dt = 1.0 / a.fps
    for f in range(nframes):
        trailer.update(dt)
        frame = trailer.render()
        ff.stdin.write(pygame.image.tobytes(frame, "RGB"))
        if f % (a.fps * 5) == 0:
            sc = trailer._scene()
            print(f"  {trailer.t:6.1f} / {total:.1f} sn   sahne: {sc[1]:10s}   "
                  f"({time.time() - t0:.0f} sn)", flush=True)
    ff.stdin.close()
    ff.wait()

    print("ses hazırlanıyor...", flush=True)
    music = compose(total, trailer.SCENES, [c for c in trailer.cut_times if c[0] < total],
                    [h for h in trailer.hits if h < total])
    fx = mix_sfx(rec.events, total)
    n = int(total * SR)
    mixd = music[:n] * 0.66 + fx[:n] * 0.30
    peak = np.max(np.abs(mixd)) or 1.0
    mixd = np.tanh(mixd / peak * 1.25) / np.tanh(1.25) * 0.92
    fade = int(1.0 * SR)
    mixd[-fade:] *= np.linspace(1, 0, fade)
    write_wav(tmp_wav, mixd)

    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp_video, "-i", tmp_wav,
                           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", a.out])
    os.remove(tmp_video)
    os.remove(tmp_wav)
    print(f"hazır: {a.out}  ({total:.1f} sn, {time.time() - t0:.0f} sn sürdü)")


if __name__ == "__main__":
    main()
