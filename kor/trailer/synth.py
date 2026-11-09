"""KÖR tanıtım videosu müziği ve efektleri: tamamen sentezlenir, çekimlerle eşzamanlı."""
import numpy as np
from scipy import signal
import wave, sys

SR = 48000
DUR = 60.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)          # kuru
RL = np.zeros(N); RR = np.zeros(N)        # yankı gönderimi


def tt(d): return np.arange(int(d * SR)) / SR


def place(sig, t0, gain=1.0, pan=0.0, rev=0.25):
    i = int(t0 * SR)
    if i >= N or len(sig) == 0:
        return
    s = sig[: N - i] * gain
    gl, gr = np.sqrt((1 - pan) / 2), np.sqrt((1 + pan) / 2)
    L[i:i + len(s)] += s * gl; R[i:i + len(s)] += s * gr
    RL[i:i + len(s)] += s * gl * rev; RR[i:i + len(s)] += s * gr * rev


def filt(x, kind, f, order=2):
    if kind == 'band':
        sos = signal.butter(order, [max(20, f[0]), min(SR / 2 - 100, f[1])], 'bandpass', fs=SR, output='sos')
    else:
        sos = signal.butter(order, min(SR / 2 - 100, f), kind, fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def noise(d): return rng.uniform(-1, 1, int(d * SR))


def brown(d):
    b = np.cumsum(rng.uniform(-1, 1, int(d * SR))); b -= np.linspace(b[0], b[-1], len(b)) if len(b) > 1 else 0
    return b / (np.abs(b).max() + 1e-9)


def expenv(d, a=.005, decay=.3):
    t = tt(d); e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / decay)
    return e


def saw(freq, d):
    ph = np.cumsum(np.broadcast_to(freq, int(d * SR)) / SR) if np.ndim(freq) else tt(d) * freq
    return 2 * (ph % 1) - 1


def sine(freq, d):
    ph = np.cumsum(np.broadcast_to(freq, int(d * SR)) / SR) if np.ndim(freq) else tt(d) * freq
    return np.sin(2 * np.pi * ph)


# ---------------------------------------------------------------- sesler
def heart(t, v=.8):
    for o, g in ((0, 1), (.17, .7)):
        d = .25; f = 62 * np.exp(-tt(d) * 6) + 30
        place(sine(f, d) * expenv(d, .008, .1), t + o, v * g, 0, .05)


def step(t, v=.5, heavy=False, pan=0):
    d = .3
    n = filt(noise(d), 'band', (180, 340) if heavy else (500, 900)) * expenv(d, .003, .12 if heavy else .07) * 3
    th = sine(np.linspace(80 if heavy else 120, 38, int(d * SR)), d) * expenv(d, .003, .12) * (1.3 if heavy else .5)
    place(n + th, t, v, pan, .2)


def tick(t, v=.4, pan=0):
    d = .05; place(filt(noise(d), 'band', (3000, 5200), 4) * expenv(d, .001, .015) * 5, t, v, pan, .3)


def clicks(t, n=5, v=.4, pan=0):
    for i in range(n): tick(t + i * rng.uniform(.045, .09), v * rng.uniform(.6, 1.2), pan)


def growl(t, d=1.6, v=.6, pitch=1.0, pan=0):
    f = np.linspace(65 * pitch, 45 * pitch, int(d * SR)) + 14 * pitch * np.sin(2 * np.pi * 12 * tt(d))
    x = np.tanh(4 * (saw(f, d) + .3 * saw(f * 1.49, d))) + filt(noise(d), 'band', (300, 700)) * .8
    x = filt(x, 'low', 750) * np.minimum(1, tt(d) / .25) * np.minimum(1, (d - tt(d)) / .4)
    place(x, t, v, pan, .35)


def screech(t, d=1.3, v=1.0, pan=0):
    x = np.zeros(int(d * SR)); T = tt(d)
    for i in range(6):
        b = rng.uniform(380, 1400)
        f = b * (.6 + .4 * np.minimum(1, T / .08)) * np.exp(-T / d * rng.uniform(.4, .8)) + b * .08 * np.sin(2 * np.pi * rng.uniform(25, 60) * T)
        x += saw(f, d) * .25
    x += filt(noise(d), 'band', (900, 3000)) * .8
    x = filt(np.tanh(3 * x), 'high', 180) * np.minimum(1, T / .02) * np.minimum(1, (d - T) / (d * .45))
    place(x, t, v, pan, .45)


def boom(t, v=1.0, d=1.8):
    f = 110 * np.exp(-tt(d) * 3.5) + 26
    place(sine(f, d) * expenv(d, .004, .9) * 1.3 + filt(noise(d), 'low', 200) * expenv(d, .002, .15), t, v, 0, .5)


def braam(t, d=3.0, v=1.0):
    T = tt(d); x = np.zeros(len(T))
    for f in (55, 55.4, 82.4, 110, 110.6, 130.8, 164.8):
        x += saw(f * (1 + .002 * np.sin(2 * np.pi * 4 * T)), d)
    cutoff = 300 + 2200 * np.exp(-T / .6)
    # süpürülen alçak geçiren: bloklar halinde
    y = np.zeros_like(x); blk = 2048
    for i in range(0, len(x), blk):
        sos = signal.butter(2, cutoff[i], 'low', fs=SR, output='sos'); y[i:i + blk] = signal.sosfilt(sos, x[i:i + blk])
    y = np.tanh(1.8 * y / 3) * np.minimum(1, T / .02) * np.exp(-np.maximum(0, T - .3) / (d * .45))
    place(y, t, v, 0, .55); boom(t, v * .9)


def hit(t, v=1.0):
    d = 1.2; T = tt(d); x = np.zeros(len(T))
    for f in (1480, 1568, 1661, 2093):
        x += saw(f * (1 + .006 * np.sin(2 * np.pi * 7 * T)), d) * .12
    x = filt(x, 'band', (900, 4000)) * expenv(d, .004, .35)
    place(x, t, v * .8, 0, .5)
    place(filt(noise(.6), 'low', 2500) * expenv(.6, .002, .12) * 1.5, t, v, 0, .4)
    boom(t, v)


def riser(t, d=2.0, v=.6):
    T = tt(d); f = 200 * (25 ** (T / d))
    n = np.zeros(len(T)); blk = 2048; src = noise(d)
    for i in range(0, len(T), blk):
        sos = signal.butter(2, [f[i] * .8, min(f[i] * 1.3, 20000)], 'bandpass', fs=SR, output='sos'); n[i:i + blk] = signal.sosfilt(sos, src[i:i + blk])
    x = (n * 3 + saw(110 * (8 ** (T / d)), d) * .25) * (T / d) ** 2
    place(x, t, v, 0, .4)


def music_box(t, notes, v=.25, slow=1.0, pan=-.3):
    for i, (f, l) in enumerate(notes):
        d = 1.6; T = tt(d); x = np.zeros(len(T))
        for h, g in ((1, .7), (2.01, .2), (3.98, .08)):
            x += np.sin(2 * np.pi * f * h * (1 - i * .0015) * T) * g
        place(x * expenv(d, .004, .5), t, v, pan, .6)
        t += l * slow * (1 + i * .02)


MB = [(659, .45), (622, .45), (659, .45), (494, .9), (523, .45), (440, .9), (330, .45), (392, .45), (440, 1.2)]


def whisper(t, d=2.0, v=.3, pan=0):
    T = tt(d); src = noise(d); env = np.zeros(len(T)); tt0 = 0
    while tt0 < d:
        syl = rng.uniform(.08, .22); i0, i1 = int(tt0 * SR), int(min(d, tt0 + syl) * SR)
        if i1 > i0: env[i0:i1] = np.sin(np.linspace(0, np.pi, i1 - i0)) * rng.uniform(.4, 1)
        tt0 += syl + rng.uniform(0, .12)
    x = (filt(src, 'band', (700, 1100), 2) + filt(src, 'band', (1900, 3100), 2)) * env * 2
    place(x, t, v, pan, .5)


def thunder(t, v=1.0):
    d = 4.5; x = filt(brown(d), 'low', 500) * np.exp(-tt(d) / 1.6) * (1 + .5 * np.sin(2 * np.pi * 3 * tt(d)))
    place(x * 1.5, t, v, 0, .7); place(filt(noise(.3), 'high', 1500) * expenv(.3, .001, .06) * 2, t, v * .6, 0, .5)


def slam(t, v=1.0, pan=0):
    d = .6; place(filt(noise(d), 'low', 900) * expenv(d, .002, .12) * 2 + sine(np.linspace(90, 35, int(d * SR)), d) * expenv(d, .002, .2) * 1.2, t, v, pan, .5)
    d2 = 1.2; place(sine(rng.uniform(300, 500), d2) * expenv(d2, .002, .4) * .15, t, v, pan, .5)


def laugh(t, v=.3, pan=.4):
    for i in range(6):
        d = .14; f = np.linspace(rng.uniform(520, 640) * (1 - i * .04), 400, int(d * SR))
        x = filt(np.abs(saw(f, d)) * 2 - 1, 'band', (900, 2200)) * expenv(d, .01, .06)
        place(x, t + i * .14, v, pan, .6)


def tinnitus(t, d=2.5, v=.06):
    T = tt(d); place((np.sin(2 * np.pi * 6200 * T) + np.sin(2 * np.pi * 6260 * T)) * np.exp(-T / (d * .5)), t, v, 0, 0)


def beep(t, f=1800, v=.15):
    d = .1; place(sine(f, d) * expenv(d, .002, .05), t, v, 0, .1)


def static(t, d, v=.08):
    x = filt(noise(d), 'band', (1200, 2600)) * (0.6 + .4 * rng.uniform(0, 1, int(d * SR)) ** 4)
    place(x, t, v, 0, .1)


def gasp(t, v=.4):
    d = .7; T = tt(d); n = noise(d); y = np.zeros(len(T)); blk = 2048
    for i in range(0, len(T), blk):
        fc = 600 + 1200 * T[i] / d; sos = signal.butter(2, [fc * .7, fc * 1.4], 'bandpass', fs=SR, output='sos'); y[i:i + blk] = signal.sosfilt(sos, n[i:i + blk])
    place(y * np.sin(np.pi * np.minimum(1, T / d)) * 3, t, v, 0, .2)


def kick(t, v=1.0):
    d = .35; place(sine(np.linspace(110, 42, int(d * SR)) * np.exp(-tt(d) * 0), d) * expenv(d, .002, .12) * 1.4, t, v, 0, .1)


def tom(t, v=.6):
    d = .4; place(sine(np.linspace(160, 80, int(d * SR)), d) * expenv(d, .002, .15) + filt(noise(d), 'low', 400) * expenv(d, .001, .05) * .5, t, v, 0, .3)


def snare(t, v=.5):
    d = .25; place(filt(noise(d), 'band', (1500, 6000)) * expenv(d, .001, .07) * 1.5 + sine(190, d) * expenv(d, .001, .05) * .5, t, v, 0, .3)


def drums(t0, t1, bpm, v=1.0, ramp=False):
    beat = 60 / bpm; t = t0; i = 0
    while t < t1:
        g = v * (.6 + .4 * (t - t0) / max(1e-3, t1 - t0)) if ramp else v
        kick(t, g)
        if i % 2 == 1: snare(t, g * .55)
        tom(t + beat / 2, g * .45)
        t += beat; i += 1


def drone(t0, t1, v=.25):
    d = t1 - t0; T = tt(d); x = np.zeros(len(T))
    for f, g in ((41.2, .35), (43.6, .3), (61.7, .25), (87.3, .08)):
        x += np.sin(2 * np.pi * f * T + 2 * np.sin(2 * np.pi * .07 * T)) * g
    x += filt(noise(d), 'band', (250, 600)) * .05 * (1 + np.sin(2 * np.pi * .09 * T))
    fade = np.minimum(1, T / 2.5) * np.minimum(1, (d - T) / 1.5)
    place(x * fade, t0, v, 0, .3)


def strings(t0, t1, v=.08, rise=False):
    d = t1 - t0; T = tt(d); x = np.zeros(len(T)); k = (1.5 ** (T / d)) if rise else 1
    for f in (311, 329.6, 466, 493.9, 622):
        x += saw(f * k * (1 + .006 * np.sin(2 * np.pi * rng.uniform(5, 7) * T)), d) * (.6 + .4 * np.sin(2 * np.pi * rng.uniform(9, 13) * T))
    x = filt(x, 'low', 2600) * np.minimum(1, T / 1.2) * np.minimum(1, (d - T) / .3)
    place(x, t0, v, 0, .5)


def pad(t0, d, v=.15):
    T = tt(d); x = np.zeros(len(T))
    for f in (220, 277.2, 329.6, 440, 554.4):
        x += np.sin(2 * np.pi * f * T) * (1 + .3 * np.sin(2 * np.pi * .3 * T))
    place(x * np.minimum(1, T / 1.5) * np.minimum(1, (d - T) / .2), t0, v, 0, .7)


# ---------------------------------------------------------------- zaman çizelgesi
# 0-5 giriş
drone(0, 13.6, .32); music_box(.7, MB, .2); thunder(2.3, .45)
# 5-9.5 yaklaşan siluet
for i in range(8): step(5.05 + i * .55, .55, True); tick(5.1 + i * .55, .25)
clicks(6.1, 6, .45); clicks(7.7, 5, .5); growl(7.0, 1.6, .35)
static(8.85, .3, .15); slam(8.9, .35); hit(8.95, .45)
# 9.5-13.5 yüz
hb = 9.7; iv = .85
while hb < 13.4: heart(hb, .7); hb += iv; iv = max(.5, iv * .93)
whisper(10.1, 2.2, .25, -.5); growl(10.4, 1.4, .3, .8); clicks(11.3, 6, .45); growl(12.2, 1.2, .35, .9)
strings(11.0, 13.55, .07)
# 13.5-17 saldırı
screech(13.62, 1.1, 1.0); braam(13.6, 2.4, .9)
t = 14.4
while t < 16.9: step(t, .3 + (t - 14.4) * .35, True); tick(t + .03, .5); t += .17
riser(15.0, 1.9, .6); hit(16.9, 1.0); screech(16.85, .5, .6)
# 17-20.5 oynanış
drone(17, 24.2, .25)
beep(17.15, 220, .25); boom(17.15, .25)
for i in range(6): step(17.2 + i * .56, .22, False, (-.2 if i % 2 else .2))
slam(19.2, .25, .7)
# 20.5-24 çocuk koğuşu + gece görüşü
music_box(20.6, MB[:6], .18, 1.1, .3); laugh(21.3, .25, .5)
for i in range(30): tick(20.6 + rng.uniform(0, 3), .05)
beep(22.1, 1800, .2); static(22.1, 1.85, .06); whisper(22.4, 1.0, .2, .3)
screech(23.4, .7, .9); hit(23.9, .9)
# 24-29 arkadaşlar
drone(24, 32.2, .25); strings(24, 29, .05)
for i in range(20): kick(24.1 + i * .6, .35 if i % 2 == 0 else .2)
for i in range(14): step(24.2 + i * .36, .15, False, rng.uniform(-.4, .4))
riser(27.6, 1.4, .3)
# 29-32 kaldırma
hb = 29.1
while hb < 32: heart(hb, .6); hb += .7
gasp(31.15, .45); whisper(29.5, 1.5, .15, .6)
# 32-38 kurgu
drums(32, 38, 140, .55)
for k in range(6): boom(32 + k, .55); place(filt(noise(.2), 'low', 3000) * expenv(.2, .001, .05), 32 + k, .8)
slam(32.05, .9); screech(32.22, .7, .9)
whisper(33.05, .9, .4, -.6); whisper(33.1, .9, .4, .6); place(filt(brown(1.0), 'low', 300) * np.linspace(0, 1, SR), 33.0, .6)
whisper(34.05, .9, .35, -.3); whisper(34.15, .9, .35, .4); heart(34.4, .7)
thunder(35.08, 1.0)
slam(36.0, .8); screech(36.05, .8, .9)
growl(37.05, .8, .5, 1.3); whisper(37.1, .5, .4); hit(37.55, .8)
# 38-39.5 ekran yüzü
screech(38.0, 1.0, 1.3); hit(38.0, 1.2); braam(38.0, 1.6, .9); tinnitus(38.95, 1.6, .06)
# 39.5-47.5 kovalama
drone(39.5, 52, .22); drums(39.6, 49.5, 150, .9, True); strings(39.6, 47.5, .09, True)
for tg in (40.0, 43.0, 46.0): growl(tg, 1.2, .8, 1.2); screech(tg + .3, .6, .5)
t = 39.6
while t < 47.4: step(t, .35, True, -.3); tick(t + .02, .35); step(t + .09, .18, False, .3); t += .19
place(np.sign(np.sin(2 * np.pi * (520 + 300 * (tt(8) % .9 / .9)) * tt(8))) * .15, 39.6, .25, 0, .6)
riser(46.3, 1.1, .5); hit(47.35, 1.0)
# 47.5-52 kaçış
place(filt(brown(1.6), 'low', 200) * 1.2, 47.6, .7); slam(47.6, .6)
pad(48.6, 2.8, .12); screech(50.8, .8, .9); boom(51.25, 1.3); place(filt(noise(1.5), 'low', 1200) * np.exp(-tt(1.5) / .4), 51.25, .6, 0, .9)
# 52-57 başlık
braam(52.05, 4.2, 1.1); music_box(53.6, MB[:5], .16, 1.25, .25); drone(52.5, 57.2, .18)
# 57-60 son korku
gasp(57.65, .2)
screech(58.2, .8, 1.3); hit(58.2, 1.2); braam(58.2, .8, .8)
boom(59.1, .9)

# ---------------------------------------------------------------- yankı + karıştırma
d = 2.8; ir = rng.uniform(-1, 1, (int(d * SR), 2)) * np.exp(-np.arange(int(d * SR)) / SR / .7)[:, None]
ir = np.stack([filt(ir[:, 0], 'low', 5000), filt(ir[:, 1], 'low', 5000)], 1) * .03
wl = signal.fftconvolve(RL, ir[:, 0])[:N]; wr = signal.fftconvolve(RR, ir[:, 1])[:N]
mix = np.stack([L + wl, R + wr], 1)
# 59.0'da kesik: tam sessizlik, sonra son boom
cut0, cut1 = int(59.0 * SR), int(59.1 * SR)
mix[cut0:cut1] *= np.linspace(1, 0, cut1 - cut0)[:, None] * 0
mix = filt(mix.T, 'high', 25).T if False else mix
# kompresör: sessiz yerleri yükselt, patlamaları bastır
mono = np.abs(mix).max(1)
env = signal.sosfilt(signal.butter(1, 6, 'low', fs=SR, output='sos'), mono)
env = np.maximum.accumulate(np.maximum(env, 1e-6)[::-1])[::-1] * 0 + np.maximum(env, 1e-6)
thr = np.percentile(env, 75)
gain = np.where(env > thr, (env / thr) ** (1 / 4 - 1), 1.0)
mix = mix * gain[:, None]
peak = np.abs(mix).max(); mix = np.tanh(mix / peak * 1.6) / np.tanh(1.6) * .93
fade = np.ones(N); fade[-int(.6 * SR):] = np.linspace(1, 0, int(.6 * SR)); mix *= fade[:, None]
out = (mix * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'trailer.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())
print('ses hazır', peak)
