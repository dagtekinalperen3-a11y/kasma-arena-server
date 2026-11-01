"""
EVOLVE ARENA — fragman müziği ve ses efektleri (tamamen sentez, telifsiz).

make_evolve_trailer.py tarafından çağrılır. Hiçbir dış ses dosyası
kullanılmaz: davul, bas, pad, arpej, BRAAAM, yükselen (riser), darbe
(impact), whoosh, kalp atışı, canavar homurtusu... hepsi numpy/scipy ile
burada üretilir.

Tempo 120 BPM: 1 vuruş = 0,5 sn, 1 ölçü = 2 sn. Fragmanın bütün kesimleri
vuruş ızgarasına oturur; böylece görüntü ve müzik kendiliğinden senkron.

Dinamik akış (senaryoya göre):
   0 -  8  gergin: drone + nabız + homurtular, sona doğru riser
   8 - 38  tempolu ve agresif: 4/4 kick, clap, hi-hat, bas, arpej
  38 - 45  kitaplar: davul düşer, tik-tak + pad, 42,5'ten itibaren riser
  45       EVRİM: beyaz patlama -> BRAAAM + tam drop
  45 - 65  agresif (dünyalar)
  65 - 67,5 cehennem kapısı: "gerilim nefesi" (sessizlik + kalp atışı)
  67,5- 75 cehennem: yarım tempo, ağır BRAAAM'ler
  75 - 84  zafer: majör renkli dönüş
  84 - 90  highlight + logo, 89'da final bas drop'u
"""
import math
import wave

import numpy as np
from scipy import signal

SR = 44100
BPM = 120.0
BEAT = 60.0 / BPM
BAR = BEAT * 4


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


# --------------------------------------------------------------------------
# temel yardımcılar
# --------------------------------------------------------------------------
_rng = np.random.default_rng(7)


def tvec(dur):
    return np.arange(int(dur * SR)) / SR


def noise(dur):
    return _rng.standard_normal(int(dur * SR))


def sos(kind, f, order=2):
    nyq = SR / 2
    if isinstance(f, (tuple, list)):
        wn = [max(1e-4, min(0.999, x / nyq)) for x in f]
    else:
        wn = max(1e-4, min(0.999, f / nyq))
    return signal.butter(order, wn, btype=kind, output="sos")


def filt(x, kind, f, order=2):
    return signal.sosfilt(sos(kind, f, order), x)


def sweep_filter(x, kind, f0, f1, steps=24, order=2):
    """Zamanla kayan filtre: parçalara bölüp her parçayı başka kesimle süzer,
    parçaları çapraz geçişle birleştirir."""
    n = len(x)
    out = np.zeros(n)
    seg = max(1, n // steps)
    win = np.hanning(seg * 2)
    for i in range(steps + 1):
        c = i * seg
        a, b = max(0, c - seg), min(n, c + seg)
        if a >= b:
            continue
        k = i / steps
        f = f0 * (f1 / f0) ** k
        if kind == "bandpass":
            f = (f / 1.6, f * 1.6)
        y = filt(x[a:b], kind, f, order)
        w = win[(a - (c - seg)):(a - (c - seg)) + (b - a)]
        out[a:b] += y * w
    return out


def env_ad(n, a, d, curve=4.0):
    """Atak + üstel sönüm zarfı (n örnek)."""
    t = np.arange(n) / SR
    e = np.exp(-t / max(1e-4, d / curve) * 1.0)
    if a > 0:
        e *= np.clip(t / a, 0, 1)
    return e


def saw(freq, t, phase=0.0):
    ph = (freq * t + phase) % 1.0
    return 2.0 * ph - 1.0


def square(freq, t, duty=0.5):
    return np.where((freq * t) % 1.0 < duty, 1.0, -1.0)


def band_saw(f0, t, cutoff, harmonics=48):
    """Kesimi zamanla değişebilen (dizi) bant sınırlı testere: BRAAAM ve
    pad için. cutoff skaler ya da t ile aynı boyda dizi olabilir."""
    out = np.zeros_like(t)
    cutoff = np.broadcast_to(np.asarray(cutoff, dtype=float), t.shape)
    for k in range(1, harmonics + 1):
        fk = f0 * k
        if fk > SR / 2 - 500:
            break
        g = 1.0 / (1.0 + np.exp((fk - cutoff) / (0.18 * cutoff + 30)))
        out += np.sin(2 * np.pi * fk * t + k * 0.7) * g / k
    return out


# --------------------------------------------------------------------------
# enstrümanlar ve SFX — her biri mono numpy dizisi döndürür
# --------------------------------------------------------------------------
def kick(power=1.0):
    t = tvec(0.45)
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 7.5)
    click = filt(noise(0.45), "highpass", 2500) * np.exp(-t * 180) * 0.35
    return np.tanh((body + click) * 1.6 * power) * 0.9


def clap():
    t = tvec(0.35)
    n = filt(noise(0.35), "bandpass", (900, 4200))
    e = np.zeros_like(t)
    for o in (0.0, 0.011, 0.022):
        e += np.where(t >= o, np.exp(-(t - o) * 60), 0)
    e += np.exp(-t * 14) * 0.5
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.4
    return (n * e * 0.55 + tone)


def hat(open_=False):
    d = 0.22 if open_ else 0.05
    t = tvec(d)
    n = filt(noise(d), "highpass", 7000)
    return n * np.exp(-t * (14 if open_ else 90)) * 0.35


def tick():
    t = tvec(0.04)
    return np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 160) * 0.35


def impact(size=1.0):
    d = 2.6
    t = tvec(d)
    f = 34 + 70 * np.exp(-t * 9)
    ph = 2 * np.pi * np.cumsum(f) / SR
    boom = np.sin(ph) * np.exp(-t * 1.6)
    crack = filt(noise(d), "lowpass", 3000) * np.exp(-t * 22) * 0.8
    rumble = filt(noise(d), "lowpass", 140) * np.exp(-t * 1.4) * 2.2
    return np.tanh((boom * 1.3 + crack + rumble) * size) * 0.95


def whoosh(dur=0.45, up=True):
    n = noise(dur)
    y = sweep_filter(n, "bandpass", 300 if up else 4000, 4000 if up else 300, steps=10)
    t = tvec(dur)
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.6
    return y * e * 0.9


def shing():
    d = 0.6
    t = tvec(d)
    n = filt(noise(d), "highpass", 5000) * np.exp(-t * 9) * 0.6
    ring = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * 6) for f in (2093, 3136, 4186)) * 0.12
    return n + ring


def riser(dur):
    t = tvec(dur)
    k = t / dur
    n = sweep_filter(noise(dur), "bandpass", 250, 7000, steps=28)
    f = 110 * 2 ** (k * 3.2)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) * 0.25 + np.sin(ph * 1.5) * 0.12
    return (n * 0.8 + tone) * k ** 2.2


def braaam(root_m=26, dur=3.2, bright=1.0):
    t = tvec(dur)
    cut = 120 + (1600 * bright) * (1 - np.exp(-t * 6)) * np.exp(-t * 0.9)
    y = np.zeros_like(t)
    for m, g in ((root_m, 1.0), (root_m + 12, 0.7), (root_m + 7, 0.45), (root_m + 19, 0.3)):
        for det in (-0.12, 0.0, 0.11):
            y += band_saw(midi(m + det), t, cut, harmonics=40) * g
    e = np.clip(t / 0.03, 0, 1) * np.exp(-t * 0.85)
    return np.tanh(y * 0.55) * e


def growl(dur=1.4):
    t = tvec(dur)
    f = 95 * np.exp(-t * 0.6) + 40
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.tanh(saw(1, ph / (2 * np.pi)) * 3 + np.sin(ph * 0.5) * 2)
    rough = filt(noise(dur), "lowpass", 380) * 3
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * (18 + 9 * np.sin(t * 3)) * t)
    y = filt(body * 0.5 + rough, "lowpass", 600) * lfo
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.8
    return y * e * 0.7


def heartbeat():
    t = tvec(0.7)
    y = np.zeros_like(t)
    for o, g in ((0.0, 1.0), (0.2, 0.75)):
        tt = np.clip(t - o, 0, None)
        y += np.where(t >= o, np.sin(2 * np.pi * 52 * tt) * np.exp(-tt * 16), 0) * g
    return np.tanh(y * 2.0) * 0.9


def coin():
    t = tvec(0.25)
    f = np.where(t < 0.06, 1318.5, 1975.5)
    return square(f, t, 0.5) * np.exp(-t * 14) * 0.12


def crit_ding():
    t = tvec(0.7)
    y = sum(np.sin(2 * np.pi * f * t) * g for f, g in ((1568, 1), (2349, .6), (3136, .4)))
    sh = np.zeros_like(t)
    s_ = shing()[:len(t)]
    sh[:len(s_)] = s_
    return y * np.exp(-t * 7) * 0.3 + sh * 0.4


def glitch():
    d = 0.18
    t = tvec(d)
    f = _rng.choice([220, 330, 440, 880, 1760], size=int(d * 40) + 1)
    seg = np.repeat(f, int(SR / 40) + 1)[:len(t)]
    y = square(seg, t, 0.3) * 0.25
    y = np.round(y * 4) / 4                      # bit crush
    return y * (1 - t / d)


def bonk_hit():
    t = tvec(0.5)
    f = 180 * np.exp(-t * 10) + 60
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 9)
    thud = filt(noise(0.5), "lowpass", 1400) * np.exp(-t * 30)
    return np.tanh((body * 1.4 + thud * 0.7) * 1.5) * 0.85


def level_up():
    t = tvec(0.9)
    y = np.zeros_like(t)
    for i, m in enumerate((72, 76, 79, 84)):
        o = i * 0.07
        tt = np.clip(t - o, 0, None)
        y += np.where(t >= o, square(midi(m), tt, 0.25) * np.exp(-tt * 6), 0)
    return filt(y, "lowpass", 5000) * 0.18


# --------------------------------------------------------------------------
# mikser
# --------------------------------------------------------------------------
class Mix:
    def __init__(self, length):
        self.n = int((length + 3.5) * SR)
        self.length = length
        self.buses = {k: np.zeros((self.n, 2)) for k in ("drums", "music", "sfx", "verb")}

    def add(self, bus, t, x, gain=1.0, pan=0.0, verb=0.0):
        i = int(round(t * SR))
        if i >= self.n or len(x) == 0:
            return
        if i < 0:
            x = x[-i:]
            i = 0
        x = x[:self.n - i]
        lg = math.cos((pan + 1) * math.pi / 4) * math.sqrt(2)
        rg = math.sin((pan + 1) * math.pi / 4) * math.sqrt(2)
        b = self.buses[bus]
        b[i:i + len(x), 0] += x * gain * lg
        b[i:i + len(x), 1] += x * gain * rg
        if verb > 0:
            v = self.buses["verb"]
            v[i:i + len(x), 0] += x * gain * verb * lg
            v[i:i + len(x), 1] += x * gain * verb * rg


def _reverb_ir(dur=2.2):
    t = tvec(dur)
    ir = np.stack([noise(dur), noise(dur)], axis=1)
    ir *= np.exp(-t * 3.2)[:, None]
    ir[:, 0] = filt(ir[:, 0], "lowpass", 6000)
    ir[:, 1] = filt(ir[:, 1], "lowpass", 6000)
    return ir / np.sqrt((ir ** 2).sum(axis=0)) * 0.9


# Akor yürüyüşü (Re minör): i - VI - III - VII  /  cehennem: i - bII
PROG_MAIN = [(38, (62, 65, 69)), (34, (58, 62, 65)), (41, (60, 65, 69)), (36, (60, 64, 67))]
PROG_HELL = [(38, (62, 65, 69)), (39, (63, 67, 70))]
PROG_WIN = [(34, (58, 62, 65)), (36, (60, 64, 67)), (38, (62, 66, 69)), (38, (62, 66, 69))]


def chord_at(t):
    bar = int(t // BAR)
    if 65.0 <= t < 75.0:
        return PROG_HELL[bar % 2]
    if t >= 75.0:
        return PROG_WIN[bar % 4]
    return PROG_MAIN[bar % 4]


def _section(t):
    if t < 8.0:
        return "tense"
    if t < 38.0:
        return "drive"
    if t < 45.0:
        return "books"
    if t < 65.0:
        return "drive"
    if t < 67.5:
        return "breath"
    if t < 75.0:
        return "hell"
    if t < 84.0:
        return "win"
    if t < 89.0:
        return "final"
    return "end"


def build_music(m, length):
    """Davul, bas, pad ve arpej katmanları."""
    k1, cl, hh, ho, tk = kick(), clap(), hat(), hat(True), tick()
    kick_times = []
    steps = int(length / (BEAT / 4))
    for s in range(steps):
        t = s * BEAT / 4
        sec = _section(t)
        beat_i, sub = divmod(s, 4)          # vuruş, 16'lık
        in_bar = beat_i % 4
        if sec in ("drive", "win", "final"):
            if sub == 0:
                m.add("drums", t, k1, 0.95)
                kick_times.append(t)
            if sub == 0 and in_bar in (1, 3):
                m.add("drums", t, cl, 0.55, verb=0.25)
            if sub == 2:
                m.add("drums", t, ho if in_bar == 3 else hh, 0.5, pan=0.25)
            elif sec != "win" or sub in (1, 3):
                m.add("drums", t, hh, 0.22, pan=-0.25)
            if sec == "final" and t > 86.5 and sub in (1, 3):
                m.add("drums", t, cl, 0.25)       # snare roll havası
        elif sec == "hell":
            # yarım tempo: kick 1 ve 3'te değil, ölçüde iki kez ağır
            if sub == 0 and in_bar in (0, 2) and t >= 67.5:
                m.add("drums", t, kick(1.4), 1.0)
                kick_times.append(t)
            if sub == 0 and in_bar == 2 and t >= 67.5:
                m.add("drums", t, cl, 0.7, verb=0.5)
            if sub in (0, 2) and t >= 67.5:
                m.add("drums", t, hh, 0.18)
        elif sec == "books":
            if t < 42.5:
                if sub in (0, 2):
                    m.add("drums", t, tk, 0.6 if sub == 0 else 0.35, pan=0.3 if sub else -0.3)
            else:                           # 42,5 - 45: hızlanan tik-tak (yükseliş)
                m.add("drums", t, tk, 0.5 + 0.4 * (t - 42.5) / 2.5)
                if sub == 0:
                    m.add("drums", t, kick(0.7), 0.45 + 0.4 * (t - 42.5) / 2.5)
        elif sec == "tense":
            if sub == 0:                    # boğuk nabız
                g = 0.25 + 0.35 * t / 8.0
                m.add("drums", t, filt(kick(0.8), "lowpass", 180), g)
            if t > 4.0 and sub == 2:
                m.add("drums", t, hh, 0.12)

    # ---- bas + pad + arpej (ölçü ölçü) ----
    nbars = int(length / BAR) + 1
    for b in range(nbars):
        t0 = b * BAR
        sec = _section(t0 + 0.01)
        root, ch = chord_at(t0 + 0.01)
        tt = tvec(BAR)
        # PAD: her bölümde (tense hariç hafif), yavaş atak
        if sec not in ("end",):
            cut = {"tense": 500, "books": 1400, "breath": 400, "hell": 900}.get(sec, 1800)
            pad = np.zeros_like(tt)
            for nm in ch:
                for det in (-0.08, 0.08):
                    pad += band_saw(midi(nm + det - 12), tt, cut, harmonics=24)
            pe = np.clip(tt / 0.35, 0, 1) * np.clip((BAR - tt) / 0.3, 0, 1)
            g = {"tense": 0.05, "books": 0.11, "breath": 0.04, "hell": 0.08, "win": 0.1}.get(sec, 0.07)
            m.add("music", t0, pad * pe, g, verb=0.6)
        # BAS: 8'likler, sidechain zarfıyla kick'e yer açar
        if sec in ("drive", "win", "final", "hell"):
            for e8 in range(8):
                t = t0 + e8 * BEAT / 2
                if sec == "hell" and t < 67.5:
                    continue
                d = BEAT / 2
                tb = tvec(d)
                f = midi(root - (12 if sec == "hell" else 0))
                if sec == "drive" and e8 % 2 == 1:
                    f *= 2
                x = (band_saw(f, tb, 420 + 500 * np.exp(-tb * 18), harmonics=24) * 0.8
                     + np.sin(2 * np.pi * f * tb) * 0.6)
                x *= np.clip(tb / 0.004, 0, 1) * np.clip((d - tb) / 0.01, 0, 1)
                m.add("music", t, np.tanh(x * 1.6), 0.33)
        elif sec == "tense":
            tb = tvec(BAR)
            drone = np.sin(2 * np.pi * midi(26) * tb) + 0.4 * band_saw(midi(26), tb, 220, 12)
            m.add("music", t0, drone * np.clip(tb / 0.2, 0, 1) * np.clip((BAR - tb) / 0.2, 0, 1),
                  0.25 + 0.1 * t0 / 8.0)
        # ARPEJ: 16'lık kare dalga, akor tonlarında
        if sec in ("drive", "win", "final") or (sec == "books" and t0 >= 38.0):
            notes = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 24, ch[2] + 12, ch[0] + 24,
                     ch[1] + 12, ch[2] + 24]
            stepd = BEAT / 4 if sec != "books" else BEAT / 2
            nsteps = int(BAR / stepd)
            for i in range(nsteps):
                t = t0 + i * stepd
                nt = notes[i % len(notes)]
                d = stepd * 0.95
                ta = tvec(d)
                x = square(midi(nt), ta, 0.3) * np.exp(-ta * (14 if sec != "books" else 6))
                x = filt(x, "lowpass", 2600 if sec != "books" else 1600)
                m.add("music", t, x, 0.07 if sec != "win" else 0.085,
                      pan=0.35 if i % 2 else -0.35, verb=0.35)
    return kick_times


def master(m, kick_times):
    n = m.n
    tt = np.arange(n) / SR
    # sidechain (müzik busu kick'e boyun eğer)
    duck = np.ones(n)
    for kt in kick_times:
        i = int(kt * SR)
        j = min(n, i + int(0.3 * SR))
        x = (np.arange(j - i) / SR)
        duck[i:j] = np.minimum(duck[i:j], 1 - 0.55 * np.exp(-x / 0.09))
    music = m.buses["music"] * duck[:, None]
    ir = _reverb_ir()
    verb = np.stack([signal.fftconvolve(m.buses["verb"][:, c], ir[:, c])[:n] for c in (0, 1)], axis=1)
    mix = m.buses["drums"] + music + m.buses["sfx"] + verb * 0.5
    # 89-90: final drop'tan sonra kuyruk; 90'da hafif sönüş
    fade = np.clip((m.length + 0.6 - tt) / 0.6, 0, 1)
    mix *= fade[:, None]
    # yumuşak sınırlayıcı
    peak = np.percentile(np.abs(mix), 99.95) or 1.0
    mix = np.tanh(mix / peak * 1.15) * 0.92
    return mix[:int((m.length + 0.05) * SR)]


SFX = {
    "impact": lambda: impact(1.0), "impact_big": lambda: impact(1.5), "whoosh": whoosh,
    "whoosh_down": lambda: whoosh(0.5, False), "shing": shing, "growl": growl,
    "heartbeat": heartbeat, "coin": coin, "crit": crit_ding, "glitch": glitch,
    "bonk": bonk_hit, "levelup": level_up,
}


def render(events, length, path):
    """events: [(t, ad, kazanç)] — sahnelerin istediği SFX'ler.
    Müzik yapısı yukarıdaki bölümlerden kendiliğinden kurulur."""
    m = Mix(length)
    kick_times = build_music(m, length)
    # ---- yapısal vuruşlar (senaryo) ----
    m.add("sfx", 5.0, riser(3.0), 0.55)
    for t, root, br, g in ((8.0, 26, 1.0, 0.9), (45.0, 26, 1.3, 1.0), (67.5, 25, 1.1, 1.0),
                           (71.5, 25, 1.2, 0.95), (89.0, 26, 1.4, 1.0)):
        m.add("sfx", t, braaam(root, 3.4, br), g * 0.75, verb=0.4)
    for t, g in ((8.0, 0.9), (45.0, 1.0), (67.5, 1.0), (75.0, 0.6), (89.0, 1.0)):
        m.add("sfx", t, impact(1.4), g)
    m.add("sfx", 35.5, riser(2.5), 0.45)
    m.add("sfx", 42.5, riser(2.5), 0.75)
    m.add("sfx", 62.0, riser(3.0), 0.4)
    m.add("sfx", 86.5, riser(2.5), 0.6)
    for i in range(4):                          # cehennem kapısı: kalp atışları
        m.add("sfx", 65.0 + i * 0.62, heartbeat(), 0.85)
    for i in range(8):
        m.add("sfx", 67.5 + i * 0.95, heartbeat(), 0.35)
    for t, name, g in events:
        gen = SFX.get(name)
        if gen is None or t < 0 or t > length:
            continue
        pan = float(_rng.uniform(-0.3, 0.3))
        m.add("sfx", t, gen(), g, pan=pan, verb=0.2 if name not in ("coin",) else 0.05)
    mix = master(m, kick_times)
    data = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    return path
