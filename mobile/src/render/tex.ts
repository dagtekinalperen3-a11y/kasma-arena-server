/**
 * Prosedürel doku üretimi: Canvas2D'ye bir kez çizilir, GPU dokusu olur.
 * Oyun sırasında hiçbir şey yeniden çizilmez — yalnızca sprite'lar taşınır.
 */
import { Texture, Rectangle } from "pixi.js";
import { RGB, rgbCss, lighten, darken, mixCol } from "../core/util";

export const TEX_RES = 2; // dokular 2x çözünürlükte çizilir (keskin görünsün)
const cache = new Map<string, Texture>();

export function makeTex(key: string, w: number, h: number, draw: (g: CanvasRenderingContext2D, w: number, h: number) => void, res = TEX_RES): Texture {
  const c = cache.get(key);
  if (c) return c;
  const cv = document.createElement("canvas");
  cv.width = Math.max(1, Math.ceil(w * res));
  cv.height = Math.max(1, Math.ceil(h * res));
  const g = cv.getContext("2d")!;
  g.scale(res, res);
  g.lineJoin = "round";
  g.lineCap = "round";
  draw(g, w, h);
  const t = Texture.from({ resource: cv, resolution: res, antialias: true } as any);
  t.source.scaleMode = "linear";
  cache.set(key, t);
  return t;
}

export function hasTex(key: string) {
  return cache.has(key);
}
export function getTex(key: string) {
  return cache.get(key);
}

// ------------------------------------------------------------------------
// Ortak şekiller
// ------------------------------------------------------------------------
export function softCircle(): Texture {
  return makeTex("soft", 64, 64, (g) => {
    const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, "rgba(255,255,255,1)");
    gr.addColorStop(0.35, "rgba(255,255,255,0.75)");
    gr.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = gr;
    g.fillRect(0, 0, 64, 64);
  }, 1);
}
export function dotTex(): Texture {
  return makeTex("dot", 16, 16, (g) => {
    g.fillStyle = "#fff";
    g.beginPath();
    g.arc(8, 8, 7, 0, Math.PI * 2);
    g.fill();
  }, 2);
}
export function ringTex(thick: number): Texture {
  return makeTex("ring" + thick, 256, 256, (g) => {
    g.strokeStyle = "#fff";
    g.lineWidth = thick;
    g.beginPath();
    g.arc(128, 128, 128 - thick / 2 - 1, 0, Math.PI * 2);
    g.stroke();
    // yumuşak iç parıltı
    g.globalAlpha = 0.25;
    g.lineWidth = thick * 3;
    g.beginPath();
    g.arc(128, 128, 128 - thick * 2, 0, Math.PI * 2);
    g.stroke();
  }, 1);
}
export function discTex(): Texture {
  return makeTex("disc", 256, 256, (g) => {
    const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    gr.addColorStop(0, "rgba(255,255,255,0.35)");
    gr.addColorStop(0.75, "rgba(255,255,255,0.55)");
    gr.addColorStop(0.95, "rgba(255,255,255,0.9)");
    gr.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = gr;
    g.beginPath();
    g.arc(128, 128, 128, 0, Math.PI * 2);
    g.fill();
  }, 1);
}
export function shadowTex(): Texture {
  return makeTex("shadow", 64, 32, (g) => {
    const gr = g.createRadialGradient(32, 16, 0, 32, 16, 32);
    gr.addColorStop(0, "rgba(0,0,0,0.55)");
    gr.addColorStop(0.6, "rgba(0,0,0,0.3)");
    gr.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = gr;
    g.save();
    g.scale(1, 0.5);
    g.beginPath();
    g.arc(32, 32, 32, 0, Math.PI * 2);
    g.fill();
    g.restore();
  }, 1);
}
export function squareTex(): Texture {
  return makeTex("sq", 4, 4, (g) => {
    g.fillStyle = "#fff";
    g.fillRect(0, 0, 4, 4);
  }, 1);
}

// ------------------------------------------------------------------------
// Çizim yardımcıları
// ------------------------------------------------------------------------
export function radial(g: CanvasRenderingContext2D, x: number, y: number, r: number, inner: RGB | number[], outer: RGB | number[], a = 1) {
  const gr = g.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r);
  gr.addColorStop(0, rgbCss(inner, a));
  gr.addColorStop(1, rgbCss(outer, a));
  return gr;
}

export function blob(g: CanvasRenderingContext2D, x: number, y: number, r: number, col: RGB | number[], outline = true) {
  g.fillStyle = radial(g, x, y, r, lighten(col, 0.35), darken(col, 0.25));
  g.beginPath();
  g.arc(x, y, r, 0, Math.PI * 2);
  g.fill();
  if (outline) {
    g.strokeStyle = rgbCss(darken(col, 0.6));
    g.lineWidth = Math.max(1.5, r * 0.11);
    g.stroke();
  }
}

export function poly(g: CanvasRenderingContext2D, pts: number[][], fill: string | CanvasGradient, stroke?: string, lw = 2) {
  g.beginPath();
  g.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]);
  g.closePath();
  g.fillStyle = fill;
  g.fill();
  if (stroke) {
    g.strokeStyle = stroke;
    g.lineWidth = lw;
    g.stroke();
  }
}

export function eyes(g: CanvasRenderingContext2D, x: number, y: number, r: number, opts: { n?: number; spread?: number; size?: number; col?: string; pupil?: string; angry?: boolean; glow?: string } = {}) {
  const n = opts.n ?? 2;
  const spread = (opts.spread ?? 0.38) * r;
  const sz = (opts.size ?? 0.22) * r;
  for (let i = 0; i < n; i++) {
    const ex = n === 1 ? x : x + (i - (n - 1) / 2) * spread * (2 / Math.max(1, n - 1));
    if (opts.glow) {
      g.fillStyle = opts.glow;
      g.globalAlpha = 0.35;
      g.beginPath();
      g.arc(ex, y, sz * 1.9, 0, Math.PI * 2);
      g.fill();
      g.globalAlpha = 1;
    }
    g.fillStyle = opts.col ?? "#fff";
    g.beginPath();
    g.ellipse(ex, y, sz, sz * 1.15, 0, 0, Math.PI * 2);
    g.fill();
    g.fillStyle = opts.pupil ?? "#141420";
    g.beginPath();
    g.arc(ex + sz * 0.15, y + sz * 0.15, sz * 0.55, 0, Math.PI * 2);
    g.fill();
    g.fillStyle = "rgba(255,255,255,0.9)";
    g.beginPath();
    g.arc(ex - sz * 0.15, y - sz * 0.3, sz * 0.22, 0, Math.PI * 2);
    g.fill();
    if (opts.angry) {
      g.strokeStyle = "#141420";
      g.lineWidth = Math.max(1.4, sz * 0.4);
      g.beginPath();
      const dir = i === 0 ? 1 : -1;
      g.moveTo(ex - sz * 1.1 * dir, y - sz * 1.5);
      g.lineTo(ex + sz * 0.9 * dir, y - sz * 0.9);
      g.stroke();
    }
  }
}

export { mixCol };

/** Bir doku atlasından alt doku keser. */
export function sub(t: Texture, x: number, y: number, w: number, h: number) {
  return new Texture({ source: t.source, frame: new Rectangle(x, y, w, h) });
}
