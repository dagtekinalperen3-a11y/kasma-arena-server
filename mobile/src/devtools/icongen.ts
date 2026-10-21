/**
 * Geliştirme aracı (?icongen=1): uygulama simgesi, açılış ekranı ve mağaza
 * görsellerini oyunun kendi çizimlerinden üretir. tools/gen-assets.mjs
 * bu sayfayı açıp PNG'leri dosyaya yazar. Oyuna dahil edilmez.
 */
import "@fontsource/lilita-one/400.css";
import "@fontsource/rubik/800.css";
import type { Texture } from "pixi.js";
import { getSkin, ENEMY_COLORS } from "../game/data";
import { heroBodyTex, heroEyesTex, pupilTex, weaponTex } from "../render/art_player";
import { enemyTextures } from "../render/sprites";
import { RGB } from "../core/util";

const src = (t: Texture) => (t.source as any).resource as HTMLCanvasElement;
const BG0 = "#0b0d18";

function hero(g: CanvasRenderingContext2D, cx: number, cy: number, size: number, skinId = "default", glow = true) {
  const sk = getSkin(skinId);
  const res = Math.min(24, Math.max(3, Math.ceil((size / 96) * 1.3)));
  const s = size / 96;
  g.save();
  g.translate(cx - 48 * s, cy - 54 * s);
  g.scale(s, s);
  if (glow) {
    const gr = g.createRadialGradient(48, 54, 4, 48, 54, 46);
    gr.addColorStop(0, `rgba(${sk.color.join(",")},0.55)`);
    gr.addColorStop(1, `rgba(${sk.color.join(",")},0)`);
    g.fillStyle = gr;
    g.beginPath();
    g.arc(48, 54, 46, 0, Math.PI * 2);
    g.fill();
  }
  g.fillStyle = "rgba(0,0,0,0.3)";
  g.beginPath();
  g.ellipse(48, 76, 17, 5, 0, 0, Math.PI * 2);
  g.fill();
  g.drawImage(src(heroBodyTex(sk, res)), 0, 0, 96, 96);
  const ew = 32 * 0.9, eh = 24 * 0.9;
  g.drawImage(src(heroEyesTex(false, res)), 48 - ew / 2 + 1.5, 51 - eh / 2, ew, eh);
  const pw = 8 * 0.9;
  for (const dx of [-6.2, 6.2]) g.drawImage(src(pupilTex(res)), 48 + dx * 0.9 + 3 - pw / 2, 51 - pw / 2 + 0.5, pw, pw);
  const wt = weaponTex(sk.weapon, sk.color as RGB, sk.accent as RGB, res);
  const ww = 72 * 0.85, wh = 72 * 0.85;
  g.drawImage(src(wt.tex), 48 + 11 - ww * wt.ax, 57 - wh * wt.ay, ww, wh);
  g.restore();
}

function enemy(g: CanvasRenderingContext2D, kind: string, x: number, y: number, r: number, alpha = 1) {
  const col = (ENEMY_COLORS as any)[kind] || [200, 80, 90];
  const R = Math.max(9, Math.round(r));
  const t = enemyTextures(kind, col, R)[0];
  g.save();
  g.globalAlpha = alpha;
  g.drawImage(src(t), x - R * 1.5, y - R * 1.5, R * 3, R * 3);
  g.restore();
}

function bgArena(g: CanvasRenderingContext2D, w: number, h: number, cx = w / 2, cy = h / 2) {
  const R = Math.hypot(w, h) / 2;
  const gr = g.createRadialGradient(cx, cy, 0, cx, cy, R);
  gr.addColorStop(0, "#3a2f86");
  gr.addColorStop(0.45, "#1d2156");
  gr.addColorStop(1, "#0b0d18");
  g.fillStyle = gr;
  g.fillRect(0, 0, w, h);
  // ışık hüzmeleri
  g.save();
  g.translate(cx, cy);
  for (let i = 0; i < 14; i++) {
    g.rotate((Math.PI * 2) / 14);
    const lg = g.createLinearGradient(0, 0, R, 0);
    lg.addColorStop(0, "rgba(140,170,255,0.10)");
    lg.addColorStop(1, "rgba(140,170,255,0)");
    g.fillStyle = lg;
    g.beginPath();
    g.moveTo(0, 0);
    g.lineTo(R, -R * 0.09);
    g.lineTo(R, R * 0.09);
    g.closePath();
    g.fill();
  }
  g.restore();
}

function ring(g: CanvasRenderingContext2D, cx: number, cy: number, r: number, w: number) {
  g.save();
  g.lineWidth = w;
  const lg = g.createLinearGradient(cx - r, cy - r, cx + r, cy + r);
  lg.addColorStop(0, "#ffe680");
  lg.addColorStop(0.5, "#ffb52e");
  lg.addColorStop(1, "#ff7a1a");
  g.strokeStyle = lg;
  g.shadowColor = "rgba(255,170,40,0.7)";
  g.shadowBlur = w * 1.5;
  g.beginPath();
  g.arc(cx, cy, r, 0, Math.PI * 2);
  g.stroke();
  g.restore();
}

function logo(g: CanvasRenderingContext2D, x: number, y: number, size: number, align: CanvasTextAlign = "center") {
  g.save();
  g.textAlign = align;
  g.textBaseline = "alphabetic";
  const draw = (txt: string, yy: number, fs: number, c0: string, c1: string, c2: string, shadow: string) => {
    g.font = `${fs}px "Lilita One"`;
    g.lineJoin = "round";
    g.lineWidth = fs * 0.14;
    g.strokeStyle = shadow;
    g.strokeText(txt, x, yy + fs * 0.06);
    g.strokeText(txt, x, yy);
    const gr = g.createLinearGradient(0, yy - fs * 0.8, 0, yy);
    gr.addColorStop(0, c0);
    gr.addColorStop(0.55, c1);
    gr.addColorStop(1, c2);
    g.fillStyle = gr;
    g.fillText(txt, x, yy);
  };
  draw("EVOLVE", y, size * 0.84, "#ffffff", "#a9d4ff", "#6aa8ff", "#13205a");
  draw("ARENA", y + size * 0.95, size, "#ffe680", "#ffb52e", "#ff7a1a", "#5a2600");
  g.restore();
}

function canvas(w: number, h: number) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return [c, c.getContext("2d")!] as const;
}

const api = {
  /** Uygulama simgesi. bg=false → uyarlanabilir ön plan (saydam). */
  icon(size: number, opts: { bg?: boolean; scale?: number; round?: boolean } = {}) {
    const [c, g] = canvas(size, size);
    const bg = opts.bg !== false;
    if (bg) {
      bgArena(g, size, size);
      ring(g, size / 2, size * 0.52, size * 0.36, size * 0.035);
    }
    const sc = opts.scale ?? 1;
    hero(g, size / 2 - size * 0.02 * sc, size * 0.53, size * 0.92 * sc, "default", bg);
    if (opts.round) {
      const [c2, g2] = canvas(size, size);
      g2.beginPath();
      g2.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
      g2.clip();
      g2.drawImage(c, 0, 0);
      return c2.toDataURL("image/png");
    }
    return c.toDataURL("image/png");
  },
  /** Açılış ekranı: koyu zemin, ortada logo + kahraman (kenarlar kırpılabilir). */
  splash(w: number, h: number) {
    const [c, g] = canvas(w, h);
    g.fillStyle = BG0;
    g.fillRect(0, 0, w, h);
    const s = Math.min(w, h);
    const cx = w / 2, cy = h / 2;
    const gr = g.createRadialGradient(cx, cy, 0, cx, cy, s * 0.6);
    gr.addColorStop(0, "#26286a");
    gr.addColorStop(1, "rgba(11,13,24,0)");
    g.fillStyle = gr;
    g.fillRect(0, 0, w, h);
    hero(g, cx, cy - s * 0.07, s * 0.34, "default");
    logo(g, cx, cy + s * 0.2, s * 0.11);
    return c.toDataURL("image/png");
  },
  /** Google Play öne çıkan görsel (1024x500). */
  feature() {
    const [c, g] = canvas(1024, 500);
    bgArena(g, 1024, 500, 700, 260);
    const kinds = ["red", "blue", "yellow", "tank", "sprinter", "brute", "wizard", "kamikaze"];
    const spots = [[560, 90, 24], [930, 120, 22], [980, 330, 26], [860, 430, 20], [600, 420, 28], [470, 250, 18], [790, 70, 16], [520, 330, 16]];
    spots.forEach(([x, y, r], i) => enemy(g, kinds[i % kinds.length], x, y, r, 0.95));
    ring(g, 740, 270, 150, 8);
    hero(g, 740, 275, 310, "default");
    logo(g, 250, 220, 120);
    g.font = '800 30px "Rubik"';
    g.fillStyle = "#dfe6ff";
    g.textAlign = "center";
    g.fillText("Survive · Evolve · Break records", 250, 400);
    return c.toDataURL("image/png");
  },
};

export async function icongen() {
  await Promise.all([document.fonts.load('400 100px "Lilita One"'), document.fonts.load('800 30px "Rubik"')]);
  (window as any).__gen = api;
  document.getElementById("boot")?.remove();
  const prev = document.createElement("img");
  prev.src = api.feature();
  prev.style.cssText = "position:fixed;left:0;top:0;width:512px";
  document.body.append(prev);
  const ic = document.createElement("img");
  ic.src = api.icon(256);
  ic.style.cssText = "position:fixed;left:520px;top:0;width:256px";
  document.body.append(ic);
  (window as any).__genReady = true;
}
