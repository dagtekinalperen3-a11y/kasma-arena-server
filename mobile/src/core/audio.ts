/**
 * Ses motoru (Web Audio).
 *
 * Eski sürümde sesler 22 kHz'de ham kare / testere dalgasıyla üretiliyor ve
 * hiçbir sınır olmadan üst üste çalınıyordu: kalabalıkta onlarca "kill" sesi
 * aynı anda patlayıp cızırtıya dönüşüyordu. Burada:
 *   - her efekt açılışta OfflineAudioContext ile 44.1 kHz'de, filtreli ve
 *     zarflı olarak bir kez üretilir (oyun sırasında sentez yok -> takılma yok),
 *   - her sesin aynı anda çalabileceği kopya sayısı ve iki çalma arasındaki en
 *     kısa süre sınırlıdır, toplam ses sayısı da tavanlıdır,
 *   - ana çıkışta yumuşak bir sıkıştırıcı (compressor) vardır,
 *   - müzik birkaç bölümlü, filtreli synth + davul olarak arka planda üretilir.
 */

type Ctx = BaseAudioContext;
const SR = 44100;

let noiseBuf: AudioBuffer | null = null;
function getNoise(ctx: Ctx): AudioBuffer {
  if (noiseBuf && noiseBuf.sampleRate === ctx.sampleRate) return noiseBuf;
  const len = ctx.sampleRate * 2;
  const b = ctx.createBuffer(1, len, ctx.sampleRate);
  const d = b.getChannelData(0);
  let seed = 1234567;
  for (let i = 0; i < len; i++) {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    d[i] = (seed / 0x7fffffff) * 2 - 1;
  }
  noiseBuf = b;
  return b;
}

interface ToneOpt {
  type?: OscillatorType;
  f0: number;
  f1?: number;
  dur: number;
  vol?: number;
  attack?: number;
  release?: number;
  curve?: "exp" | "lin";
  filter?: BiquadFilterType;
  ff0?: number;
  ff1?: number;
  q?: number;
  detune?: number; // cents, ikinci osilatör
  vib?: number; // vibrato derinliği (oran)
  vibRate?: number;
  pan?: number;
}

function env(ctx: Ctx, g: GainNode, t0: number, dur: number, vol: number, attack: number, release: number) {
  const gp = g.gain;
  gp.setValueAtTime(0.0001, t0);
  gp.linearRampToValueAtTime(vol, t0 + Math.max(0.001, attack));
  const sustainEnd = t0 + Math.max(attack + 0.001, dur - release);
  gp.setValueAtTime(vol, sustainEnd);
  gp.exponentialRampToValueAtTime(0.0001, t0 + dur);
}

function tone(ctx: Ctx, out: AudioNode, t0: number, o: ToneOpt) {
  const vol = o.vol ?? 0.3;
  const g = ctx.createGain();
  const attack = o.attack ?? 0.004;
  const release = o.release ?? o.dur * 0.85;
  env(ctx, g, t0, o.dur, vol, attack, release);
  let node: AudioNode = g;
  if (o.filter) {
    const f = ctx.createBiquadFilter();
    f.type = o.filter;
    f.Q.value = o.q ?? 0.8;
    f.frequency.setValueAtTime(o.ff0 ?? 2000, t0);
    if (o.ff1) f.frequency.exponentialRampToValueAtTime(Math.max(20, o.ff1), t0 + o.dur);
    g.connect(f);
    node = f;
  }
  if (o.pan) {
    const p = ctx.createStereoPanner();
    p.pan.value = o.pan;
    node.connect(p);
    node = p;
  }
  node.connect(out);
  const oscs: OscillatorNode[] = [];
  const mk = (det: number) => {
    const osc = ctx.createOscillator();
    osc.type = o.type ?? "sine";
    osc.frequency.setValueAtTime(o.f0, t0);
    if (o.f1 && o.f1 !== o.f0) {
      if (o.curve === "lin") osc.frequency.linearRampToValueAtTime(o.f1, t0 + o.dur);
      else osc.frequency.exponentialRampToValueAtTime(Math.max(1, o.f1), t0 + o.dur);
    }
    osc.detune.value = det;
    osc.connect(g);
    oscs.push(osc);
  };
  mk(0);
  if (o.detune) mk(o.detune);
  if (o.vib) {
    const lfo = ctx.createOscillator();
    const lg = ctx.createGain();
    lfo.frequency.value = o.vibRate ?? 6;
    lg.gain.value = o.f0 * o.vib;
    lfo.connect(lg);
    for (const osc of oscs) lg.connect(osc.frequency);
    lfo.start(t0);
    lfo.stop(t0 + o.dur + 0.05);
  }
  for (const osc of oscs) {
    osc.start(t0);
    osc.stop(t0 + o.dur + 0.05);
  }
}

interface NoiseOpt {
  dur: number;
  vol?: number;
  attack?: number;
  filter?: BiquadFilterType;
  ff0?: number;
  ff1?: number;
  q?: number;
  pan?: number;
  rate?: number;
}

function noise(ctx: Ctx, out: AudioNode, t0: number, o: NoiseOpt) {
  const src = ctx.createBufferSource();
  src.buffer = getNoise(ctx);
  src.playbackRate.value = o.rate ?? 1;
  const g = ctx.createGain();
  env(ctx, g, t0, o.dur, o.vol ?? 0.3, o.attack ?? 0.002, o.dur * 0.9);
  src.connect(g);
  let node: AudioNode = g;
  if (o.filter) {
    const f = ctx.createBiquadFilter();
    f.type = o.filter;
    f.Q.value = o.q ?? 0.8;
    f.frequency.setValueAtTime(o.ff0 ?? 2000, t0);
    if (o.ff1) f.frequency.exponentialRampToValueAtTime(Math.max(20, o.ff1), t0 + o.dur);
    g.connect(f);
    node = f;
  }
  if (o.pan) {
    const p = ctx.createStereoPanner();
    p.pan.value = o.pan;
    node.connect(p);
    node = p;
  }
  node.connect(out);
  src.start(t0, Math.random() * 1.5);
  src.stop(t0 + o.dur + 0.05);
}

/** Basit geri besleme gecikmesi (yankı). */
function echo(ctx: Ctx, out: AudioNode, time = 0.12, fb = 0.35, wet = 0.3): AudioNode {
  const inp = ctx.createGain();
  const d = ctx.createDelay(1.0);
  d.delayTime.value = time;
  const f = ctx.createGain();
  f.gain.value = fb;
  const w = ctx.createGain();
  w.gain.value = wet;
  const lp = ctx.createBiquadFilter();
  lp.type = "lowpass";
  lp.frequency.value = 3500;
  inp.connect(out);
  inp.connect(d);
  d.connect(lp);
  lp.connect(f);
  f.connect(d);
  lp.connect(w);
  w.connect(out);
  return inp;
}

const midi = (n: number) => 440 * Math.pow(2, (n - 69) / 12);

// ---------------------------------------------------------------------------
// EFEKT TARİFLERİ — her biri (ctx, out) alır, t=0'dan çizer. [süre, tarif]
// ---------------------------------------------------------------------------
type Recipe = [number, (ctx: Ctx, out: AudioNode) => void];

const SFX: Record<string, Recipe> = {
  shoot_a: [0.12, (c, o) => {
    tone(c, o, 0, { type: "square", f0: 1150, f1: 420, dur: 0.09, vol: 0.10, filter: "lowpass", ff0: 3800, ff1: 900 });
    tone(c, o, 0, { type: "sine", f0: 600, f1: 200, dur: 0.07, vol: 0.12 });
    noise(c, o, 0, { dur: 0.03, vol: 0.06, filter: "highpass", ff0: 3000 });
  }],
  shoot_b: [0.2, (c, o) => {
    tone(c, o, 0, { type: "sawtooth", f0: 300, f1: 90, dur: 0.17, vol: 0.12, filter: "lowpass", ff0: 1600, ff1: 300 });
    noise(c, o, 0, { dur: 0.15, vol: 0.12, filter: "bandpass", ff0: 1800, ff1: 500, q: 1.2 });
  }],
  shoot_c: [0.14, (c, o) => {
    tone(c, o, 0, { type: "sawtooth", f0: 1700, f1: 380, dur: 0.11, vol: 0.08, filter: "bandpass", ff0: 2600, ff1: 900, q: 2.5 });
    tone(c, o, 0, { type: "sine", f0: 2400, f1: 900, dur: 0.06, vol: 0.06 });
    noise(c, o, 0, { dur: 0.05, vol: 0.05, filter: "highpass", ff0: 5000 });
  }],
  shoot_d: [0.18, (c, o) => {
    tone(c, o, 0, { type: "sine", f0: 230, f1: 70, dur: 0.15, vol: 0.32 });
    noise(c, o, 0, { dur: 0.12, vol: 0.14, filter: "lowpass", ff0: 2200, ff1: 400 });
  }],
  hit: [0.07, (c, o) => {
    tone(c, o, 0, { type: "triangle", f0: 520, f1: 210, dur: 0.05, vol: 0.14 });
    noise(c, o, 0, { dur: 0.035, vol: 0.06, filter: "highpass", ff0: 2500 });
  }],
  crit: [0.16, (c, o) => {
    tone(c, o, 0, { type: "triangle", f0: 1100, f1: 1900, dur: 0.1, vol: 0.12 });
    tone(c, o, 0.015, { type: "sine", f0: 2600, f1: 3200, dur: 0.08, vol: 0.06 });
    noise(c, o, 0, { dur: 0.05, vol: 0.08, filter: "bandpass", ff0: 4000, q: 2 });
  }],
  kill: [0.16, (c, o) => {
    tone(c, o, 0, { type: "sine", f0: 520, f1: 110, dur: 0.12, vol: 0.18 });
    noise(c, o, 0, { dur: 0.1, vol: 0.10, filter: "bandpass", ff0: 1400, ff1: 400, q: 1.4 });
  }],
  bonk: [0.42, (c, o) => {
    tone(c, o, 0, { type: "sine", f0: 160, f1: 38, dur: 0.34, vol: 0.55 });
    tone(c, o, 0, { type: "triangle", f0: 420, f1: 90, dur: 0.12, vol: 0.18 });
    noise(c, o, 0, { dur: 0.22, vol: 0.22, filter: "lowpass", ff0: 2600, ff1: 200 });
    noise(c, o, 0, { dur: 0.02, vol: 0.18, filter: "highpass", ff0: 3000 });
  }],
  dash: [0.22, (c, o) => {
    noise(c, o, 0, { dur: 0.2, vol: 0.22, filter: "bandpass", ff0: 500, ff1: 3200, q: 1.6, attack: 0.03 });
    tone(c, o, 0, { type: "sine", f0: 300, f1: 900, dur: 0.15, vol: 0.05 });
  }],
  coin: [0.22, (c, o) => {
    tone(c, o, 0, { type: "sine", f0: 1318, dur: 0.07, vol: 0.12 });
    tone(c, o, 0.05, { type: "sine", f0: 1760, dur: 0.15, vol: 0.12 });
    tone(c, o, 0.05, { type: "triangle", f0: 3520, dur: 0.08, vol: 0.02 });
  }],
  xp: [0.07, (c, o) => {
    tone(c, o, 0, { type: "sine", f0: 880, f1: 1320, dur: 0.06, vol: 0.06 });
  }],
  heart: [0.3, (c, o) => {
    tone(c, o, 0, { type: "triangle", f0: 523, f1: 784, dur: 0.12, vol: 0.18 });
    tone(c, o, 0.1, { type: "sine", f0: 1047, dur: 0.18, vol: 0.12 });
  }],
  levelup: [1.1, (c, o) => {
    const e = echo(c, o, 0.11, 0.35, 0.35);
    [523, 659, 784, 1047, 1319].forEach((f, i) =>
      tone(c, e, i * 0.075, { type: "triangle", f0: f, dur: 0.28, vol: 0.16, filter: "lowpass", ff0: 5000 }));
    tone(c, e, 0.3, { type: "sine", f0: 2093, dur: 0.5, vol: 0.06 });
    tone(c, o, 0, { type: "sawtooth", f0: 262, dur: 0.6, vol: 0.05, filter: "lowpass", ff0: 900, detune: 9, attack: 0.05 });
  }],
  hurt: [0.26, (c, o) => {
    tone(c, o, 0, { type: "sawtooth", f0: 220, f1: 70, dur: 0.2, vol: 0.18, filter: "lowpass", ff0: 1400, ff1: 250 });
    tone(c, o, 0, { type: "sine", f0: 140, f1: 60, dur: 0.18, vol: 0.3 });
    noise(c, o, 0, { dur: 0.08, vol: 0.12, filter: "lowpass", ff0: 2000 });
  }],
  shield: [0.4, (c, o) => {
    const e = echo(c, o, 0.08, 0.3, 0.25);
    tone(c, e, 0, { type: "sine", f0: 900, f1: 1650, dur: 0.18, vol: 0.18 });
    tone(c, e, 0, { type: "triangle", f0: 1340, dur: 0.25, vol: 0.06 });
    tone(c, e, 0, { type: "sine", f0: 2210, dur: 0.2, vol: 0.04 });
  }],
  guard: [0.16, (c, o) => {
    tone(c, o, 0, { type: "triangle", f0: 760, f1: 1300, dur: 0.09, vol: 0.14 });
    tone(c, o, 0, { type: "square", f0: 240, f1: 120, dur: 0.08, vol: 0.05, filter: "lowpass", ff0: 1500 });
  }],
  buy: [0.4, (c, o) => {
    tone(c, o, 0, { type: "triangle", f0: 880, dur: 0.1, vol: 0.18 });
    tone(c, o, 0.08, { type: "triangle", f0: 1320, dur: 0.22, vol: 0.18 });
    tone(c, o, 0.08, { type: "sine", f0: 2640, dur: 0.16, vol: 0.05 });
    noise(c, o, 0.08, { dur: 0.06, vol: 0.05, filter: "highpass", ff0: 6000 });
  }],
  error: [0.3, (c, o) => {
    tone(c, o, 0, { type: "square", f0: 180, dur: 0.1, vol: 0.08, filter: "lowpass", ff0: 900 });
    tone(c, o, 0.13, { type: "square", f0: 150, dur: 0.12, vol: 0.08, filter: "lowpass", ff0: 900 });
  }],
  boss: [1.8, (c, o) => {
    tone(c, o, 0, { type: "sawtooth", f0: 55, dur: 1.6, vol: 0.25, filter: "lowpass", ff0: 300, ff1: 900, detune: 12, attack: 0.2, vib: 0.02, vibRate: 5 });
    tone(c, o, 0, { type: "sawtooth", f0: 82.4, dur: 1.6, vol: 0.18, filter: "lowpass", ff0: 300, ff1: 1200, detune: -10, attack: 0.25 });
    tone(c, o, 0, { type: "sine", f0: 70, f1: 30, dur: 1.2, vol: 0.45 });
    noise(c, o, 0, { dur: 1.4, vol: 0.12, filter: "lowpass", ff0: 400, ff1: 120, attack: 0.3 });
  }],
  wave: [0.9, (c, o) => {
    const e = echo(c, o, 0.14, 0.3, 0.3);
    tone(c, e, 0, { type: "sawtooth", f0: 220, dur: 0.7, vol: 0.10, filter: "lowpass", ff0: 400, ff1: 2200, detune: 8, attack: 0.15 });
    tone(c, e, 0, { type: "sawtooth", f0: 330, dur: 0.7, vol: 0.07, filter: "lowpass", ff0: 400, ff1: 2200, detune: -8, attack: 0.18 });
    tone(c, e, 0.05, { type: "sine", f0: 440, dur: 0.6, vol: 0.06, attack: 0.1 });
  }],
  explosion: [0.8, (c, o) => {
    noise(c, o, 0, { dur: 0.65, vol: 0.45, filter: "lowpass", ff0: 3500, ff1: 150 });
    tone(c, o, 0, { type: "sine", f0: 110, f1: 28, dur: 0.6, vol: 0.5 });
    noise(c, o, 0, { dur: 0.03, vol: 0.25, filter: "highpass", ff0: 2000 });
  }],
  lightning: [0.4, (c, o) => {
    noise(c, o, 0, { dur: 0.3, vol: 0.32, filter: "highpass", ff0: 1800, ff1: 600 });
    tone(c, o, 0, { type: "sawtooth", f0: 2400, f1: 140, dur: 0.22, vol: 0.08, filter: "bandpass", ff0: 2000, q: 1.5 });
    tone(c, o, 0.02, { type: "sine", f0: 90, f1: 40, dur: 0.3, vol: 0.25 });
  }],
  click: [0.05, (c, o) => {
    tone(c, o, 0, { type: "sine", f0: 900, f1: 600, dur: 0.035, vol: 0.12 });
  }],
  ach: [1.2, (c, o) => {
    const e = echo(c, o, 0.13, 0.4, 0.35);
    [659, 784, 988, 1319, 1568].forEach((f, i) =>
      tone(c, e, i * 0.09, { type: "triangle", f0: f, dur: 0.35, vol: 0.13 }));
    tone(c, e, 0.4, { type: "sine", f0: 2637, dur: 0.5, vol: 0.05 });
  }],
  gameover: [1.6, (c, o) => {
    const e = echo(c, o, 0.18, 0.35, 0.3);
    [392, 311, 262, 196].forEach((f, i) =>
      tone(c, e, i * 0.22, { type: "sawtooth", f0: f, dur: 0.5, vol: 0.08, filter: "lowpass", ff0: 1400, ff1: 400, detune: 8 }));
    tone(c, o, 0.66, { type: "sine", f0: 98, f1: 60, dur: 0.9, vol: 0.3 });
  }],
  second: [0.9, (c, o) => {
    const e = echo(c, o, 0.1, 0.4, 0.3);
    tone(c, e, 0, { type: "sine", f0: 400, f1: 1200, dur: 0.5, vol: 0.2 });
    tone(c, e, 0, { type: "triangle", f0: 600, f1: 1800, dur: 0.5, vol: 0.08 });
    noise(c, e, 0, { dur: 0.5, vol: 0.06, filter: "highpass", ff0: 4000, attack: 0.2 });
  }],
  warn: [0.3, (c, o) => {
    tone(c, o, 0, { type: "square", f0: 620, dur: 0.08, vol: 0.06, filter: "lowpass", ff0: 2000 });
    tone(c, o, 0.12, { type: "square", f0: 620, dur: 0.08, vol: 0.06, filter: "lowpass", ff0: 2000 });
  }],
  whip: [0.16, (c, o) => {
    noise(c, o, 0, { dur: 0.1, vol: 0.3, filter: "bandpass", ff0: 5000, ff1: 1200, q: 2 });
    tone(c, o, 0, { type: "sawtooth", f0: 1900, f1: 260, dur: 0.08, vol: 0.05, filter: "lowpass", ff0: 4000 });
  }],
  splash: [0.4, (c, o) => {
    noise(c, o, 0, { dur: 0.32, vol: 0.22, filter: "bandpass", ff0: 1800, ff1: 500, q: 0.9 });
    tone(c, o, 0, { type: "sine", f0: 620, f1: 180, dur: 0.22, vol: 0.12 });
    tone(c, o, 0.05, { type: "sine", f0: 900, f1: 400, dur: 0.12, vol: 0.06 });
  }],
  vortex: [0.9, (c, o) => {
    tone(c, o, 0, { type: "sawtooth", f0: 70, f1: 300, dur: 0.8, vol: 0.12, filter: "lowpass", ff0: 300, ff1: 1500, vib: 0.08, vibRate: 9, attack: 0.1 });
    noise(c, o, 0, { dur: 0.8, vol: 0.14, filter: "bandpass", ff0: 400, ff1: 1600, q: 1.2, attack: 0.2 });
  }],
  magnet: [0.8, (c, o) => {
    const e = echo(c, o, 0.09, 0.35, 0.3);
    [784, 1047, 1319, 1568, 2093].forEach((f, i) =>
      tone(c, e, i * 0.06, { type: "sine", f0: f, dur: 0.2, vol: 0.12 }));
  }],
  blaze: [0.36, (c, o) => {
    noise(c, o, 0, { dur: 0.3, vol: 0.16, filter: "lowpass", ff0: 1500, ff1: 600, attack: 0.03 });
    tone(c, o, 0, { type: "triangle", f0: 180, f1: 70, dur: 0.28, vol: 0.12 });
  }],
  ice_step: [0.22, (c, o) => {
    noise(c, o, 0, { dur: 0.16, vol: 0.12, filter: "highpass", ff0: 4000 });
    tone(c, o, 0, { type: "triangle", f0: 1500, f1: 600, dur: 0.14, vol: 0.06 });
  }],
  roar: [0.9, (c, o) => {
    tone(c, o, 0, { type: "sawtooth", f0: 110, f1: 70, dur: 0.8, vol: 0.2, filter: "lowpass", ff0: 900, ff1: 300, vib: 0.06, vibRate: 22, attack: 0.05 });
    noise(c, o, 0, { dur: 0.8, vol: 0.18, filter: "bandpass", ff0: 600, q: 0.8, attack: 0.05 });
  }],
  chest: [1.0, (c, o) => {
    const e = echo(c, o, 0.12, 0.35, 0.35);
    tone(c, o, 0, { type: "sine", f0: 120, f1: 60, dur: 0.25, vol: 0.4 });
    [523, 659, 784, 1047, 1319, 1568].forEach((f, i) =>
      tone(c, e, 0.12 + i * 0.06, { type: "triangle", f0: f, dur: 0.3, vol: 0.12 }));
  }],
  portal: [1.4, (c, o) => {
    const e = echo(c, o, 0.2, 0.45, 0.4);
    tone(c, e, 0, { type: "sawtooth", f0: 110, f1: 440, dur: 1.2, vol: 0.12, filter: "lowpass", ff0: 300, ff1: 3000, vib: 0.04, vibRate: 6, detune: 14, attack: 0.3 });
    noise(c, e, 0, { dur: 1.2, vol: 0.1, filter: "bandpass", ff0: 300, ff1: 3000, q: 2, attack: 0.4 });
  }],
  ult: [0.6, (c, o) => {
    const e = echo(c, o, 0.1, 0.3, 0.3);
    tone(c, e, 0, { type: "sawtooth", f0: 330, f1: 990, dur: 0.3, vol: 0.12, filter: "lowpass", ff0: 800, ff1: 5000, detune: 10 });
    tone(c, e, 0.12, { type: "triangle", f0: 1320, dur: 0.4, vol: 0.1 });
    noise(c, o, 0, { dur: 0.25, vol: 0.1, filter: "highpass", ff0: 2500, attack: 0.08 });
  }],
  tap: [0.06, (c, o) => {
    tone(c, o, 0, { type: "triangle", f0: 660, f1: 520, dur: 0.045, vol: 0.10 });
  }],
  swoosh: [0.3, (c, o) => {
    noise(c, o, 0, { dur: 0.26, vol: 0.12, filter: "bandpass", ff0: 400, ff1: 2400, q: 1.2, attack: 0.08 });
  }],
};

/** Aynı anda en çok kaç kopya çalabilir, iki çalma arası en az kaç ms. */
const LIMITS: Record<string, [number, number]> = {
  shoot_a: [3, 45], shoot_b: [3, 60], shoot_c: [3, 45], shoot_d: [3, 60],
  hit: [4, 30], crit: [3, 50], kill: [4, 35], coin: [3, 40], xp: [2, 40],
  hurt: [2, 120], explosion: [3, 80], lightning: [3, 70], whip: [3, 60],
  blaze: [2, 120], ice_step: [2, 120], splash: [2, 90], guard: [2, 80],
  warn: [2, 200], bonk: [2, 60], dash: [2, 60], click: [3, 30], tap: [3, 30],
};

// ---------------------------------------------------------------------------
// MÜZİK
// ---------------------------------------------------------------------------
interface Track {
  bpm: number;
  bars: number;
  root: number; // midi
  prog: number[][]; // her bar için akor (kök ofsetleri, minör/majör)
  bass: number[]; // her bar kök notası ofseti
  mood: "calm" | "battle" | "boss" | "hell" | "frost" | "jungle" | "desert";
}

const TRACKS: Record<string, Track> = {
  menu: { bpm: 92, bars: 16, root: 57, mood: "calm",
    prog: [[0, 3, 7], [-4, 0, 3], [-9, -5, -2], [-2, 2, 5]], bass: [0, -4, -9, -2] },
  arena: { bpm: 126, bars: 16, root: 45, mood: "battle",
    prog: [[0, 3, 7], [-4, 0, 3], [3, 7, 10], [-2, 2, 5]], bass: [0, -4, 3, -2] },
  frost: { bpm: 118, bars: 16, root: 50, mood: "frost",
    prog: [[0, 3, 7], [5, 8, 12], [-2, 2, 5], [3, 7, 10]], bass: [0, 5, -2, 3] },
  jungle: { bpm: 122, bars: 16, root: 47, mood: "jungle",
    prog: [[0, 3, 7], [0, 3, 8], [-2, 2, 5], [-4, 0, 3]], bass: [0, 0, -2, -4] },
  desert: { bpm: 120, bars: 16, root: 48, mood: "desert",
    prog: [[0, 4, 7], [1, 4, 8], [0, 4, 7], [-2, 1, 5]], bass: [0, 1, 0, -2] },
  hell: { bpm: 138, bars: 16, root: 40, mood: "hell",
    prog: [[0, 3, 7], [1, 4, 8], [-2, 1, 5], [0, 3, 6]], bass: [0, 1, -2, 0] },
  boss: { bpm: 142, bars: 16, root: 42, mood: "boss",
    prog: [[0, 3, 7], [-1, 3, 6], [0, 3, 7], [1, 5, 8]], bass: [0, -1, 0, 1] },
};

function kick(c: Ctx, o: AudioNode, t: number, v = 0.7) {
  tone(c, o, t, { type: "sine", f0: 150, f1: 42, dur: 0.32, vol: v, release: 0.28 });
  noise(c, o, t, { dur: 0.012, vol: v * 0.25, filter: "highpass", ff0: 2500 });
}
function snare(c: Ctx, o: AudioNode, t: number, v = 0.35) {
  noise(c, o, t, { dur: 0.18, vol: v, filter: "bandpass", ff0: 2200, q: 0.7 });
  tone(c, o, t, { type: "triangle", f0: 220, f1: 160, dur: 0.1, vol: v * 0.6 });
}
function hat(c: Ctx, o: AudioNode, t: number, v = 0.09, open = false) {
  noise(c, o, t, { dur: open ? 0.16 : 0.035, vol: v, filter: "highpass", ff0: 7500 });
}

function renderTrack(c: OfflineAudioContext, tr: Track) {
  const master = c.createGain();
  master.gain.value = 0.85;
  const comp = c.createDynamicsCompressor();
  comp.threshold.value = -16;
  comp.ratio.value = 3;
  master.connect(comp);
  comp.connect(c.destination);
  const drums = c.createGain();
  drums.gain.value = 0.9;
  drums.connect(master);
  const music = c.createGain();
  music.gain.value = 1;
  music.connect(master);
  const delayed = echo(c, music, (60 / tr.bpm) * 0.75, 0.38, 0.32);

  const beat = 60 / tr.bpm;
  const bar = beat * 4;
  const R = tr.root;
  const intense = tr.mood !== "calm";
  for (let b = 0; b < tr.bars; b++) {
    const t0 = b * bar;
    const ch = tr.prog[b % tr.prog.length];
    const bn = tr.bass[b % tr.bass.length];
    const section = Math.floor(b / 4); // 0: giriş, 1: A, 2: B, 3: doruk
    // --- PAD ---
    for (const n of ch) {
      tone(c, music, t0, {
        type: "sawtooth", f0: midi(R + 12 + n), dur: bar * 0.98, vol: intense ? 0.028 : 0.04,
        filter: "lowpass", ff0: intense ? 900 : 700, ff1: intense ? 1800 : 1100, detune: 11, attack: 0.25,
        release: 0.5, pan: (n % 2 ? -0.25 : 0.25),
      });
    }
    if (tr.mood === "calm") {
      // yumuşak bas + arpej
      tone(c, music, t0, { type: "triangle", f0: midi(R - 12 + bn), dur: bar * 0.95, vol: 0.12, attack: 0.05, release: 0.6 });
      for (let i = 0; i < 8; i++) {
        const n = ch[[0, 1, 2, 1][i % 4]] + ((i >> 2) % 2 ? 12 : 0);
        tone(c, delayed, t0 + i * beat / 2, {
          type: "sine", f0: midi(R + 24 + n), dur: beat * 0.45, vol: 0.05, release: beat * 0.4,
          pan: i % 2 ? 0.3 : -0.3,
        });
      }
      if (section >= 1) {
        for (let i = 0; i < 4; i++) hat(c, drums, t0 + i * beat + beat / 2, 0.025);
        kick(c, drums, t0, 0.25);
        kick(c, drums, t0 + 2 * beat, 0.2);
      }
      continue;
    }
    // --- BAS (8'lik) ---
    for (let i = 0; i < 8; i++) {
      const up = tr.mood === "hell" || tr.mood === "boss" ? (i % 4 === 3 ? 12 : i % 2 ? 7 : 0) : (i % 4 === 3 ? 12 : 0);
      tone(c, music, t0 + i * beat / 2, {
        type: "sawtooth", f0: midi(R - 12 + bn + up), dur: beat * 0.46, vol: 0.13,
        filter: "lowpass", ff0: 1400, ff1: 220, q: 3, release: beat * 0.35,
      });
    }
    // --- ARPEJ / MELODİ ---
    if (section >= 1) {
      const pat = tr.mood === "desert" ? [0, 1, 2, 1, 0, 2, 1, 2] : [0, 1, 2, 1, 2, 1, 0, 1];
      const oct = section === 3 ? 24 : 12;
      for (let i = 0; i < 16; i++) {
        if (tr.mood === "jungle" && i % 3 === 2) continue;
        const n = ch[pat[i % 8] % ch.length] + (i % 8 >= 6 ? 12 : 0);
        tone(c, delayed, t0 + i * beat / 4, {
          type: tr.mood === "frost" ? "sine" : "triangle", f0: midi(R + oct + n), dur: beat * 0.22,
          vol: tr.mood === "frost" ? 0.06 : 0.045, release: beat * 0.18, pan: i % 2 ? 0.35 : -0.35,
        });
      }
    }
    if (section === 2 || section === 3) {
      // uzun lead notası (bar başına iki)
      for (let k = 0; k < 2; k++) {
        const n = ch[(b + k) % ch.length] + 24;
        tone(c, delayed, t0 + k * 2 * beat, {
          type: "square", f0: midi(R + n), dur: beat * 1.8, vol: 0.022, filter: "lowpass", ff0: 1800, ff1: 2600,
          detune: 6, attack: 0.04, release: beat * 0.8, vib: 0.006, vibRate: 5,
        });
      }
    }
    // --- DAVUL ---
    const kv = section === 0 ? 0.45 : 0.7;
    for (let i = 0; i < 4; i++) kick(c, drums, t0 + i * beat, kv);
    if (tr.mood === "boss" || tr.mood === "hell") kick(c, drums, t0 + 3.5 * beat, kv * 0.7);
    if (section >= 1) {
      snare(c, drums, t0 + beat, 0.3);
      snare(c, drums, t0 + 3 * beat, 0.3);
      if (b % 4 === 3) {
        snare(c, drums, t0 + 3.5 * beat, 0.2);
        snare(c, drums, t0 + 3.75 * beat, 0.24);
      }
    }
    for (let i = 0; i < 8; i++) hat(c, drums, t0 + i * beat / 2 + (i % 2 ? 0 : 0), i % 2 ? 0.07 : 0.04, i === 7 && b % 2 === 1);
    if (tr.mood === "jungle") {
      for (let i = 0; i < 8; i++)
        tone(c, drums, t0 + (i * 1.5 % 4) * beat, { type: "sine", f0: 330 + (i % 3) * 110, f1: 200, dur: 0.12, vol: 0.12 });
    }
    if (tr.mood === "desert") {
      for (let i = 0; i < 4; i++)
        noise(c, drums, t0 + i * beat + beat * 0.75, { dur: 0.08, vol: 0.06, filter: "bandpass", ff0: 3500, q: 3 });
    }
  }
}

// ---------------------------------------------------------------------------

export class AudioEngine {
  ctx: AudioContext | null = null;
  master!: GainNode;
  sfxBus!: GainNode;
  musicBus!: GainNode;
  buffers = new Map<string, AudioBuffer>();
  music = new Map<string, AudioBuffer>();
  private musicRendering = new Set<string>();
  private active = new Map<string, number>();
  private lastPlay = new Map<string, number>();
  private totalVoices = 0;
  private curMusic: { name: string; src: AudioBufferSourceNode; gain: GainNode } | null = null;
  private wantMusic: string | null = null;
  sfxVol = 0.8;
  musicVol = 0.55;
  private unlocked = false;
  private suspendedByApp = false;

  init() {
    if (this.ctx) return;
    const AC: typeof AudioContext = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (!AC) return;
    this.ctx = new AC({ latencyHint: "interactive" });
    const comp = this.ctx.createDynamicsCompressor();
    comp.threshold.value = -12;
    comp.knee.value = 10;
    comp.ratio.value = 4;
    comp.attack.value = 0.003;
    comp.release.value = 0.2;
    comp.connect(this.ctx.destination);
    this.master = this.ctx.createGain();
    this.master.gain.value = 1;
    this.master.connect(comp);
    this.sfxBus = this.ctx.createGain();
    this.sfxBus.gain.value = this.sfxVol;
    this.sfxBus.connect(this.master);
    this.musicBus = this.ctx.createGain();
    this.musicBus.gain.value = this.musicVol;
    this.musicBus.connect(this.master);
    const unlock = () => {
      if (!this.ctx) return;
      if (this.ctx.state !== "running" && !this.suspendedByApp) this.ctx.resume().catch(() => {});
      if (!this.unlocked) {
        // iOS: sessiz bir tampon çalarak kilidi aç
        const b = this.ctx.createBuffer(1, 1, 22050);
        const s = this.ctx.createBufferSource();
        s.buffer = b;
        s.connect(this.ctx.destination);
        s.start(0);
        this.unlocked = true;
      }
    };
    for (const ev of ["pointerdown", "touchend", "keydown"]) window.addEventListener(ev, unlock, { passive: true });
  }

  /** Bütün efektleri arka planda üretir. */
  async renderAll(onProgress?: (f: number) => void) {
    const names = Object.keys(SFX);
    let i = 0;
    for (const name of names) {
      const [dur, fn] = SFX[name];
      try {
        const c = new OfflineAudioContext(2, Math.ceil((dur + 0.05) * SR), SR);
        const g = c.createGain();
        g.connect(c.destination);
        fn(c, g);
        const buf = await c.startRendering();
        this.buffers.set(name, buf);
      } catch (e) {
        console.warn("sfx", name, e);
      }
      i++;
      onProgress?.(i / names.length);
    }
  }

  async renderMusic(name: string): Promise<AudioBuffer | null> {
    if (this.music.has(name)) return this.music.get(name)!;
    const tr = TRACKS[name];
    if (!tr || this.musicRendering.has(name)) return null;
    this.musicRendering.add(name);
    try {
      const len = (60 / tr.bpm) * 4 * tr.bars;
      const c = new OfflineAudioContext(2, Math.ceil(len * SR), SR);
      renderTrack(c, tr);
      const buf = await c.startRendering();
      this.music.set(name, buf);
      return buf;
    } catch (e) {
      console.warn("music", name, e);
      return null;
    } finally {
      this.musicRendering.delete(name);
    }
  }

  setVolumes(sfx: number, music: number) {
    this.sfxVol = sfx;
    this.musicVol = music;
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    this.sfxBus.gain.setTargetAtTime(sfx, t, 0.05);
    this.musicBus.gain.setTargetAtTime(music, t, 0.05);
  }

  play(name: string, vol = 1, pitchVar = 0.04, pan = 0) {
    const ctx = this.ctx;
    if (!ctx || ctx.state !== "running" || this.sfxVol <= 0.001) return;
    const buf = this.buffers.get(name);
    if (!buf) return;
    const now = performance.now();
    const lim = LIMITS[name] || [4, 25];
    if ((this.active.get(name) || 0) >= lim[0]) return;
    const last = this.lastPlay.get(name) || 0;
    if (now - last < lim[1]) return;
    if (this.totalVoices >= 28) return;
    this.lastPlay.set(name, now);
    const src = ctx.createBufferSource();
    src.buffer = buf;
    if (pitchVar) src.playbackRate.value = 1 + (Math.random() * 2 - 1) * pitchVar;
    const g = ctx.createGain();
    g.gain.value = vol;
    src.connect(g);
    if (pan) {
      const p = ctx.createStereoPanner();
      p.pan.value = Math.max(-1, Math.min(1, pan));
      g.connect(p);
      p.connect(this.sfxBus);
    } else g.connect(this.sfxBus);
    this.active.set(name, (this.active.get(name) || 0) + 1);
    this.totalVoices++;
    src.onended = () => {
      this.active.set(name, Math.max(0, (this.active.get(name) || 1) - 1));
      this.totalVoices = Math.max(0, this.totalVoices - 1);
      g.disconnect();
    };
    src.start();
  }

  async playMusic(name: string | null, fade = 1.2) {
    this.wantMusic = name;
    if (!this.ctx) return;
    if (this.curMusic && this.curMusic.name === name) return;
    const old = this.curMusic;
    if (old) {
      const t = this.ctx.currentTime;
      old.gain.gain.cancelScheduledValues(t);
      old.gain.gain.setValueAtTime(old.gain.gain.value, t);
      old.gain.gain.linearRampToValueAtTime(0, t + fade);
      old.src.stop(t + fade + 0.05);
      this.curMusic = null;
    }
    if (!name) return;
    const buf = await this.renderMusic(name);
    if (!buf || this.wantMusic !== name || !this.ctx) return;
    if (this.curMusic && (this.curMusic as any).name === name) return;
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    src.loop = true;
    const g = this.ctx.createGain();
    const t = this.ctx.currentTime;
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(1, t + fade);
    src.connect(g);
    g.connect(this.musicBus);
    src.start();
    this.curMusic = { name, src, gain: g };
  }

  /** Müziği geçici olarak kıs (menü açıkken / ölüm anında). */
  duck(amount: number, time = 0.3) {
    if (!this.ctx || !this.curMusic) return;
    const t = this.ctx.currentTime;
    this.curMusic.gain.gain.cancelScheduledValues(t);
    this.curMusic.gain.gain.setTargetAtTime(amount, t, time / 3);
  }

  preloadMusic(names: string[]) {
    // sırayla, oyunu boğmadan
    (async () => {
      for (const n of names) await this.renderMusic(n);
    })();
  }

  appPause() {
    this.suspendedByApp = true;
    this.ctx?.suspend().catch(() => {});
  }
  appResume() {
    this.suspendedByApp = false;
    this.ctx?.resume().catch(() => {});
  }
}

export const audio = new AudioEngine();
export const sfx = (name: string, vol = 1, pitchVar = 0.04) => audio.play(name, vol, pitchVar);
