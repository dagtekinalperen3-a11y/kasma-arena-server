/**
 * Kahraman çizimleri: gövde (skine göre aksesuarlı), gözler, silah.
 */
import { Texture } from "pixi.js";
import { makeTex } from "./tex";
import { RGB, rgbCss, lighten, darken, hueCol } from "../core/util";
import type { SkinDef } from "../game/data";

const OUT = "rgba(12,10,20,0.95)";
type G = CanvasRenderingContext2D;

function circ(g: G, x: number, y: number, r: number) {
  g.beginPath();
  g.arc(x, y, r, 0, Math.PI * 2);
}
function shade(g: G, x: number, y: number, r: number, c: RGB) {
  const gr = g.createRadialGradient(x - r * 0.4, y - r * 0.45, r * 0.05, x, y, r * 1.05);
  gr.addColorStop(0, rgbCss(lighten(c, 0.45)));
  gr.addColorStop(0.5, rgbCss(c));
  gr.addColorStop(1, rgbCss(darken(c, 0.35)));
  return gr;
}
function fs(g: G, fill: string | CanvasGradient, lw = 2.2) {
  g.fillStyle = fill;
  g.fill();
  g.strokeStyle = OUT;
  g.lineWidth = lw;
  g.stroke();
}

/** Gövde: 96x96 tuval, merkez (48,52), r=16 -> çizim ölçeği 1.25 */
export function heroBodyTex(sk: SkinDef): Texture {
  return makeTex("hero|" + sk.id, 96, 96, (g) => {
    const R = 20; // görsel yarıçap
    const cx = 48, cy = 54;
    const col = (sk.id === "prism" ? hueCol(0.9) : sk.color) as RGB;
    const acc = sk.accent as RGB;
    const aura = sk.aura;
    // --- arka aksesuarlar ---
    if (aura === "wings") {
      for (const s of [-1, 1]) {
        g.beginPath();
        g.moveTo(cx + s * R * 0.5, cy - R * 0.1);
        g.quadraticCurveTo(cx + s * R * 1.9, cy - R * 1.3, cx + s * R * 2.05, cy - R * 0.2);
        g.quadraticCurveTo(cx + s * R * 1.5, cy - R * 0.1, cx + s * R * 1.6, cy + R * 0.35);
        g.quadraticCurveTo(cx + s * R * 1.1, cy + R * 0.2, cx + s * R * 0.6, cy + R * 0.45);
        g.closePath();
        const gr = g.createLinearGradient(cx, cy, cx + s * R * 2, cy - R);
        gr.addColorStop(0, rgbCss(darken(col, 0.1)));
        gr.addColorStop(1, rgbCss(lighten(acc, 0.2)));
        fs(g, gr, 2);
      }
    }
    if (aura === "shadow" || sk.id === "shadow_hunter") {
      // kapüşonlu pelerin
      g.beginPath();
      g.moveTo(cx - R * 1.1, cy + R * 0.9);
      g.quadraticCurveTo(cx - R * 1.25, cy - R * 0.6, cx, cy - R * 1.35);
      g.quadraticCurveTo(cx + R * 1.25, cy - R * 0.6, cx + R * 1.1, cy + R * 0.9);
      g.closePath();
      fs(g, rgbCss(darken(col, 0.45)), 2);
    }
    if (aura === "merc" || aura === "ash" || aura === "titan") {
      g.beginPath();
      g.moveTo(cx - R * 0.95, cy - R * 0.2);
      g.lineTo(cx - R * 1.25, cy + R * 1.05);
      g.lineTo(cx + R * 1.25, cy + R * 1.05);
      g.lineTo(cx + R * 0.95, cy - R * 0.2);
      g.closePath();
      fs(g, rgbCss(aura === "ash" ? [150, 34, 38] : aura === "titan" ? [70, 50, 110] : [30, 30, 40]), 2);
    }
    // --- ayaklar ---
    for (const s of [-1, 1]) {
      g.beginPath();
      g.ellipse(cx + s * R * 0.42, cy + R * 0.92, R * 0.3, R * 0.2, 0, 0, Math.PI * 2);
      fs(g, rgbCss(darken(col, 0.45)), 2);
    }
    // --- gövde ---
    g.beginPath();
    g.ellipse(cx, cy, R, R * 0.96, 0, 0, Math.PI * 2);
    fs(g, shade(g, cx, cy, R, col), 2.8);
    // göbek / zırh plakası
    g.beginPath();
    g.ellipse(cx, cy + R * 0.38, R * 0.55, R * 0.4, 0, 0, Math.PI * 2);
    g.fillStyle = rgbCss(lighten(col, 0.25), 0.55);
    g.fill();
    // kemer
    g.fillStyle = rgbCss(darken(acc, 0.1));
    g.fillRect(cx - R * 0.78, cy + R * 0.12, R * 1.56, R * 0.16);
    g.fillStyle = rgbCss(acc);
    g.fillRect(cx - R * 0.12, cy + R * 0.08, R * 0.24, R * 0.24);
    // parlama
    g.fillStyle = "rgba(255,255,255,0.45)";
    g.beginPath();
    g.ellipse(cx - R * 0.42, cy - R * 0.5, R * 0.3, R * 0.16, -0.6, 0, Math.PI * 2);
    g.fill();
    // kenar rengi
    g.strokeStyle = rgbCss(acc, 0.8);
    g.lineWidth = 1.6;
    g.beginPath();
    g.ellipse(cx, cy, R - 2.2, R * 0.96 - 2.2, 0, 0, Math.PI * 2);
    g.stroke();
    // --- ön / baş aksesuarları ---
    if (aura === "stars" && (sk.id === "royal" || sk.id === "frost_witch" || sk.id === "orbit_guardian")) {
      if (sk.id === "royal") crown(g, cx, cy - R * 0.85, R * 0.7, "#ffd25a");
      else if (sk.id === "frost_witch") witchHat(g, cx, cy - R * 0.7, R, [150, 210, 255]);
      else {
        g.strokeStyle = rgbCss(acc);
        g.lineWidth = 2;
        g.beginPath();
        g.ellipse(cx, cy - R * 1.02, R * 0.7, R * 0.2, 0, 0, Math.PI * 2);
        g.stroke();
      }
    }
    if (aura === "halo") {
      g.strokeStyle = "#ffe68a";
      g.shadowColor = "#ffd25a";
      g.shadowBlur = 8;
      g.lineWidth = 3;
      g.beginPath();
      g.ellipse(cx, cy - R * 1.12, R * 0.62, R * 0.2, 0, 0, Math.PI * 2);
      g.stroke();
      g.shadowBlur = 0;
    }
    if (aura === "flames") {
      g.shadowColor = "#ff7a20";
      g.shadowBlur = 10;
      for (let i = 0; i < 3; i++) {
        const x = cx + (i - 1) * R * 0.42;
        const h = R * (i === 1 ? 0.95 : 0.65);
        g.beginPath();
        g.moveTo(x - R * 0.24, cy - R * 0.72);
        g.quadraticCurveTo(x - R * 0.1, cy - R * 0.72 - h, x + R * 0.05, cy - R * 0.72 - h * 1.1);
        g.quadraticCurveTo(x + R * 0.1, cy - R * 0.85 - h * 0.4, x + R * 0.24, cy - R * 0.72);
        g.closePath();
        const gr = g.createLinearGradient(x, cy - R * 0.7, x, cy - R * 0.7 - h);
        gr.addColorStop(0, "#ff6a1a");
        gr.addColorStop(1, "#ffe27a");
        g.fillStyle = gr;
        g.fill();
      }
      g.shadowBlur = 0;
    }
    if (aura === "arcs") {
      g.strokeStyle = "#dfffff";
      g.shadowColor = "#7af0ff";
      g.shadowBlur = 8;
      g.lineWidth = 2;
      g.beginPath();
      g.moveTo(cx - R * 0.2, cy - R * 0.92);
      g.lineTo(cx + R * 0.05, cy - R * 1.35);
      g.lineTo(cx - R * 0.05, cy - R * 1.2);
      g.lineTo(cx + R * 0.25, cy - R * 1.6);
      g.stroke();
      g.shadowBlur = 0;
    }
    if (aura === "bubbles") {
      for (const [x, y, r] of [[-0.6, -1.1, 0.16], [0.1, -1.35, 0.12], [0.55, -1.05, 0.14]]) {
        circ(g, cx + x * R, cy + y * R, r * R);
        g.fillStyle = rgbCss(acc, 0.75);
        g.fill();
        g.strokeStyle = "rgba(255,255,255,0.8)";
        g.lineWidth = 1;
        g.stroke();
      }
    }
    if (aura === "web") {
      // maske: kırmızı başlık + ağ çizgileri
      g.save();
      g.beginPath();
      g.ellipse(cx, cy, R - 1, R * 0.96 - 1, 0, 0, Math.PI * 2);
      g.clip();
      g.strokeStyle = "rgba(20,10,20,0.55)";
      g.lineWidth = 1;
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2;
        g.beginPath();
        g.moveTo(cx, cy - R * 0.2);
        g.lineTo(cx + Math.cos(a) * R * 1.4, cy - R * 0.2 + Math.sin(a) * R * 1.4);
        g.stroke();
      }
      for (const rr of [0.4, 0.75]) {
        circ(g, cx, cy - R * 0.2, R * rr);
        g.stroke();
      }
      g.restore();
    }
    if (aura === "cosmos") {
      g.fillStyle = "rgba(255,255,255,0.9)";
      for (const [x, y] of [[-0.4, -0.3], [0.3, -0.55], [0.55, 0.1], [-0.2, 0.35]]) {
        circ(g, cx + x * R, cy + y * R, 1.2);
        g.fill();
      }
    }
    if (aura === "titan") {
      g.fillStyle = "#2a1a3a";
      g.fillRect(cx - R * 0.8, cy - R * 0.85, R * 1.6, R * 0.32);
    }
    if (sk.id === "lucky_fox") {
      for (const s of [-1, 1]) {
        g.beginPath();
        g.moveTo(cx + s * R * 0.3, cy - R * 0.8);
        g.lineTo(cx + s * R * 0.75, cy - R * 1.45);
        g.lineTo(cx + s * R * 0.85, cy - R * 0.55);
        g.closePath();
        fs(g, rgbCss(col), 2);
        g.beginPath();
        g.moveTo(cx + s * R * 0.42, cy - R * 0.78);
        g.lineTo(cx + s * R * 0.72, cy - R * 1.2);
        g.lineTo(cx + s * R * 0.76, cy - R * 0.66);
        g.closePath();
        g.fillStyle = rgbCss(acc);
        g.fill();
      }
    }
    if (sk.id === "iron_sentinel") {
      g.beginPath();
      g.arc(cx, cy - R * 0.1, R * 0.92, Math.PI * 1.05, Math.PI * 1.95);
      g.lineTo(cx + R * 0.7, cy - R * 0.1);
      g.lineTo(cx - R * 0.7, cy - R * 0.1);
      g.closePath();
      fs(g, "#9aa4b8", 2);
    }
    if (sk.id === "pink_dream") {
      for (const s of [-1, 1]) {
        g.beginPath();
        g.ellipse(cx + s * R * 0.32, cy - R * 0.98, R * 0.3, R * 0.18, s * 0.5, 0, Math.PI * 2);
        fs(g, "#ff7ac0", 1.6);
      }
      circ(g, cx, cy - R * 0.95, R * 0.13);
      fs(g, "#ffd0e6", 1.4);
    }
    if (sk.id === "ranger" || sk.id === "default") {
      // küçük kask / bandana
      g.beginPath();
      g.arc(cx, cy - R * 0.05, R * 0.98, Math.PI * 1.12, Math.PI * 1.88);
      g.strokeStyle = rgbCss(darken(acc, sk.id === "ranger" ? 0.4 : 0.2));
      g.lineWidth = 4;
      g.stroke();
    }
  }, 3);
}

function crown(g: G, x: number, y: number, w: number, col: string) {
  g.beginPath();
  g.moveTo(x - w * 0.6, y + w * 0.2);
  g.lineTo(x - w * 0.68, y - w * 0.35);
  g.lineTo(x - w * 0.32, y - w * 0.08);
  g.lineTo(x, y - w * 0.5);
  g.lineTo(x + w * 0.32, y - w * 0.08);
  g.lineTo(x + w * 0.68, y - w * 0.35);
  g.lineTo(x + w * 0.6, y + w * 0.2);
  g.closePath();
  fs(g, col, 2);
  g.fillStyle = "#e0325a";
  circ(g, x, y - w * 0.05, w * 0.1);
  g.fill();
}
function witchHat(g: G, x: number, y: number, R: number, c: RGB) {
  g.beginPath();
  g.moveTo(x - R * 0.7, y + R * 0.1);
  g.lineTo(x + R * 0.15, y - R * 1.1);
  g.lineTo(x + R * 0.7, y + R * 0.1);
  g.closePath();
  fs(g, rgbCss(darken(c, 0.25)), 2);
  g.beginPath();
  g.ellipse(x, y + R * 0.1, R * 0.95, R * 0.2, 0, 0, Math.PI * 2);
  fs(g, rgbCss(c), 2);
}

/** Gözler: 2 göz, merkez (16,12). */
export function heroEyesTex(glow = false): Texture {
  return makeTex("heroeyes" + (glow ? "g" : ""), 32, 24, (g) => {
    for (const x of [9, 23]) {
      if (glow) {
        g.shadowColor = "#c08aff";
        g.shadowBlur = 8;
        g.fillStyle = "#ead2ff";
        g.beginPath();
        g.ellipse(x, 12, 4, 3, 0, 0, Math.PI * 2);
        g.fill();
        g.shadowBlur = 0;
        continue;
      }
      g.fillStyle = "#fbfbff";
      g.beginPath();
      g.ellipse(x, 12, 4.6, 5.4, 0, 0, Math.PI * 2);
      g.fill();
      g.strokeStyle = OUT;
      g.lineWidth = 1.2;
      g.stroke();
    }
  }, 3);
}
export function pupilTex(): Texture {
  return makeTex("pupil", 8, 8, (g) => {
    g.fillStyle = "#151a2c";
    circ(g, 4, 4, 2.6);
    g.fill();
    g.fillStyle = "#fff";
    circ(g, 3, 3, 0.9);
    g.fill();
  }, 3);
}

/**
 * Silah dokusu: sağa bakar, sap (0,0) noktası tuvalde (16, H/2).
 * Döndürme pivotu bu noktadır.
 */
export function weaponTex(kind: string, col: RGB, acc: RGB): { tex: Texture; ax: number; ay: number } {
  const W = 72, H = 72, ox = 16, oy = 36;
  const tex = makeTex(`wpn|${kind}|${col}|${acc}`, W, H, (g) => {
    g.translate(ox, oy);
    const poly = (pts: number[][], fill: string, stroke?: string, lw = 1.6) => {
      g.beginPath();
      pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y)));
      g.closePath();
      g.fillStyle = fill;
      g.fill();
      g.strokeStyle = stroke || OUT;
      g.lineWidth = lw;
      g.stroke();
    };
    const line = (x1: number, y1: number, x2: number, y2: number, c: string, w: number) => {
      g.strokeStyle = c;
      g.lineWidth = w;
      g.beginPath();
      g.moveTo(x1, y1);
      g.lineTo(x2, y2);
      g.stroke();
    };
    const glow = (x: number, y: number, r: number, c: RGB, a = 0.6) => {
      const gr = g.createRadialGradient(x, y, 0, x, y, r);
      gr.addColorStop(0, rgbCss(c, a));
      gr.addColorStop(1, rgbCss(c, 0));
      g.fillStyle = gr;
      g.fillRect(x - r, y - r, r * 2, r * 2);
    };
    const C = rgbCss(col), A = rgbCss(acc);
    switch (kind) {
      case "blaster":
        poly([[0, -5], [20, -5], [27, -2.5], [27, 2.5], [20, 5], [0, 5]], "#2c3248", A);
        poly([[3, 5], [10, 5], [8, 13], [2, 13]], "#242a3c");
        line(6, 0, 21, 0, C, 2.4);
        glow(28, 0, 8, acc, 0.7);
        break;
      case "crossbow":
        poly([[0, -2.5], [23, -2.5], [26, 0], [23, 2.5], [0, 2.5]], "#4e282e", A);
        poly([[9, -17], [20, -3], [20, 3], [9, 17], [13, 0]], C, "#ffd2c8", 1.8);
        line(10, -16, 23, 0, "#fff0ea", 1);
        line(10, 16, 23, 0, "#fff0ea", 1);
        poly([[21, -2.5], [31, 0], [21, 2.5]], A);
        break;
      case "flask":
        poly([[0, -4], [21, -3], [24, 0], [21, 3], [0, 4]], "#23592d", A);
        g.beginPath();
        g.arc(-1, -1, 8.5, 0, Math.PI * 2);
        g.fillStyle = "#1c4226";
        g.fill();
        g.strokeStyle = C;
        g.lineWidth = 2.2;
        g.stroke();
        g.fillStyle = rgbCss(acc, 0.9);
        for (const [x, y] of [[-3, 1], [1, -3], [-1, 4]]) {
          g.beginPath();
          g.arc(x, y, 1.8, 0, Math.PI * 2);
          g.fill();
        }
        glow(25, 0, 10, col, 0.6);
        break;
      case "scepter":
        line(-8, 0, 33, 0, "#d2af5f", 3.4);
        g.beginPath();
        g.arc(37, 0, 7.5, 0, Math.PI * 2);
        g.fillStyle = "#3c1e6e";
        g.fill();
        g.strokeStyle = C;
        g.lineWidth = 2.4;
        g.stroke();
        for (const a of [-0.9, 0, 0.9]) line(37 + Math.cos(a) * 7.5, Math.sin(a) * 7.5, 37 + Math.cos(a) * 12, Math.sin(a) * 12, A, 2);
        glow(37, 0, 14, col, 0.7);
        break;
      case "tesla":
        line(0, 0, 26, 0, "#464e64", 4.5);
        for (const x of [6, 12, 18]) poly([[x - 1.2, -5.5], [x + 1.2, -5.5], [x + 1.2, 5.5], [x - 1.2, 5.5]], A, OUT, 0.8);
        g.beginPath();
        g.arc(29, 0, 4.5, 0, Math.PI * 2);
        g.fillStyle = A;
        g.fill();
        glow(29, 0, 13, col, 0.8);
        break;
      case "scythe": {
        line(-16, 0, 37, 0, "#2e2446", 4.4);
        line(-16, 0, 37, 0, A, 1.2);
        const blade = [[35, 0], [42, -6], [44, -15], [39, -25], [28, -32], [14, -33], [19, -26], [29, -21], [35, -13], [34, -4]];
        poly(blade, "#161024", A, 2);
        glow(24, -26, 14, acc, 0.45);
        break;
      }
      case "cannon":
        poly([[0, -6.5], [19, -5.5], [25, -3.5], [25, 3.5], [19, 5.5], [0, 6.5]], "#54291a", "#ffa046", 2);
        for (const x of [5, 10, 15]) line(x, -5.5, x, 5.5, "#ff7828", 2);
        glow(27, 0, 13, [255, 140, 40], 0.75);
        break;
      case "goldgun":
        poly([[-2, -4.5], [23, -4.5], [32, -2.5], [32, 2.5], [23, 4.5], [-2, 4.5]], "#d2a546", "#fff0aa", 2);
        poly([[2, 4.5], [9, 4.5], [6, 13], [0, 13]], "#aa8232");
        g.beginPath();
        g.arc(10, 0, 3, 0, Math.PI * 2);
        g.fillStyle = "#ff5a78";
        g.fill();
        glow(33, 0, 10, acc, 0.55);
        break;
      case "crystal": {
        const gr = g.createLinearGradient(0, -8, 30, 8);
        gr.addColorStop(0, "#ff7ac8");
        gr.addColorStop(0.5, "#7ad8ff");
        gr.addColorStop(1, "#b0ff7a");
        poly([[0, 0], [10, -9], [31, 0], [10, 9]], gr as any, "#ffffff", 2);
        line(0, 0, 31, 0, "#ffffff", 1);
        glow(31, 0, 12, [255, 200, 255], 0.7);
        break;
      }
      case "webshooter":
        poly([[0, -5], [9, -6], [11, -3], [11, 3], [9, 6], [0, 5]], "#3a3c4e", A);
        poly([[9, -3], [18, -2], [18, 2], [9, 3]], "#969bb0");
        g.beginPath();
        g.arc(6, 0, 3, 0, Math.PI * 2);
        g.fillStyle = A;
        g.fill();
        for (let i = 0; i < 3; i++) {
          const a = (i - 1) * 0.3;
          line(18, 0, 18 + Math.cos(a) * 11, Math.sin(a) * 11, "#eef2fa", 1.2);
        }
        break;
      case "twinblades":
        for (const s of [-1, 1]) {
          poly([[2, s * 4], [12, s * 9], [31, s * 5], [33, s * 2], [12, s * 3]], "#cecbc6", "#78766f");
          line(2, s * 4, 12, s * 6, "#463e3a", 3);
        }
        line(0, 0, 16, 0, "#564e46", 2);
        break;
      case "fists": {
        const fc = darken(col, 0.25);
        g.beginPath();
        g.arc(11, 0, 11.5, 0, Math.PI * 2);
        g.fillStyle = rgbCss(fc);
        g.fill();
        g.strokeStyle = OUT;
        g.lineWidth = 2;
        g.stroke();
        g.beginPath();
        g.arc(8, -3, 4, 0, Math.PI * 2);
        g.fillStyle = rgbCss(lighten(col, 0.35));
        g.fill();
        for (let i = 0; i < 3; i++) line(15, -6 + i * 6, 20, -6 + i * 6, rgbCss(darken(col, 0.5)), 2);
        break;
      }
      case "pistols":
        for (const s of [-1, 1]) {
          poly([[0, s * 3 - 3], [17, s * 3 - 3], [17, s * 3 + 2], [0, s * 3 + 2]], "#2e3040", "#9698a8", 1.2);
          poly([[2, s * 3 + 2], [7, s * 3 + 2], [5, s * 3 + 9], [1, s * 3 + 9]], "#22242e");
        }
        glow(20, 0, 10, col, 0.5);
        break;
      default:
        poly([[0, -4], [24, -4], [24, 4], [0, 4]], C);
    }
  }, 3);
  return { tex, ax: ox / W, ay: oy / H };
}
