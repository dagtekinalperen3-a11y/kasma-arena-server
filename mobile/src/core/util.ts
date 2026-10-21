export const TAU = Math.PI * 2;

export const clamp = (v: number, lo: number, hi: number) => (v < lo ? lo : v > hi ? hi : v);
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const dist = (x1: number, y1: number, x2: number, y2: number) => Math.hypot(x2 - x1, y2 - y1);
export const dist2 = (x1: number, y1: number, x2: number, y2: number) => {
  const dx = x2 - x1, dy = y2 - y1;
  return dx * dx + dy * dy;
};
export const easeOutCubic = (t: number) => 1 - Math.pow(1 - clamp(t, 0, 1), 3);
export const easeOutBack = (t: number) => {
  const c1 = 1.70158, c3 = c1 + 1;
  t = clamp(t, 0, 1);
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
};

export function normDir(x1: number, y1: number, x2: number, y2: number): [number, number] {
  const dx = x2 - x1, dy = y2 - y1;
  const l = Math.hypot(dx, dy);
  if (l < 1e-6) return [0, 0];
  return [dx / l, dy / l];
}

export const rand = (a: number, b: number) => a + Math.random() * (b - a);
export const randInt = (a: number, b: number) => a + Math.floor(Math.random() * (b - a + 1));
export const chance = (p: number) => Math.random() < p;
export function pick<T>(arr: readonly T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

export function weightedPick<T>(items: readonly T[], weights: readonly number[]): T {
  let total = 0;
  for (const w of weights) total += Math.max(0, w);
  if (total <= 0) return items[0];
  let r = Math.random() * total;
  for (let i = 0; i < items.length; i++) {
    r -= Math.max(0, weights[i]);
    if (r <= 0) return items[i];
  }
  return items[items.length - 1];
}

export function shuffle<T>(arr: T[]): T[] {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const t = arr[i];
    arr[i] = arr[j];
    arr[j] = t;
  }
  return arr;
}

/** Seeded PRNG (mulberry32). */
export function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export type RGB = [number, number, number];

export const rgbToHex = (c: RGB | number[]) => ((c[0] & 255) << 16) | ((c[1] & 255) << 8) | (c[2] & 255);
export const rgbCss = (c: RGB | number[], a = 1) =>
  a >= 1 ? `rgb(${c[0] | 0},${c[1] | 0},${c[2] | 0})` : `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;
export const mixCol = (a: RGB | number[], b: RGB | number[], t: number): RGB => [
  a[0] + (b[0] - a[0]) * t,
  a[1] + (b[1] - a[1]) * t,
  a[2] + (b[2] - a[2]) * t,
];
export const scaleCol = (c: RGB | number[], k: number): RGB => [
  clamp(c[0] * k, 0, 255),
  clamp(c[1] * k, 0, 255),
  clamp(c[2] * k, 0, 255),
];
export const lighten = (c: RGB | number[], t: number): RGB => mixCol(c, [255, 255, 255], t);
export const darken = (c: RGB | number[], t: number): RGB => mixCol(c, [0, 0, 0], t);

export function hueCol(h: number, s = 0.72, v = 1.0): RGB {
  h = ((h % 1) + 1) % 1;
  const i = Math.floor(h * 6), f = h * 6 - i;
  const p = v * (1 - s), q = v * (1 - f * s), t = v * (1 - (1 - f) * s);
  const m = [
    [v, t, p], [q, v, p], [p, v, t], [p, q, v], [t, p, v], [v, p, q],
  ][i % 6];
  return [m[0] * 255, m[1] * 255, m[2] * 255];
}

export function fmtTime(sec: number) {
  sec = Math.max(0, Math.floor(sec));
  const m = Math.floor(sec / 60), s = sec % 60;
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

export function fmtNum(n: number) {
  n = Math.floor(n);
  return n.toLocaleString("tr-TR");
}

/** Azalan getirili yığın (Python stack_bonus). */
export function stackBonus(per: number, lvl: number, soft = 4.0) {
  lvl = Math.max(0, lvl);
  if (lvl <= 0) return 0;
  return per * soft * (1 - soft / (soft + lvl));
}
