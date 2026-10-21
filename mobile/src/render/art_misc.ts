/**
 * Mermiler, toplanabilirler, silah nesneleri, alanlar ve patron çizimleri.
 */
import { Texture } from "pixi.js";
import { makeTex } from "./tex";
import { RGB, rgbCss, lighten, darken, TAU } from "../core/util";
import { eyes } from "./tex";

const OUT = "rgba(12,10,20,0.95)";
type G = CanvasRenderingContext2D;

function circ(g: G, x: number, y: number, r: number) {
  g.beginPath();
  g.arc(x, y, Math.max(0.5, r), 0, TAU);
}
function glow(g: G, x: number, y: number, r: number, c: RGB | number[], a = 0.7) {
  const gr = g.createRadialGradient(x, y, 0, x, y, r);
  gr.addColorStop(0, rgbCss(c, a));
  gr.addColorStop(0.45, rgbCss(c, a * 0.45));
  gr.addColorStop(1, rgbCss(c, 0));
  g.fillStyle = gr;
  g.fillRect(x - r, y - r, r * 2, r * 2);
}
function fs(g: G, fill: string | CanvasGradient, lw = 2) {
  g.fillStyle = fill;
  g.fill();
  g.strokeStyle = OUT;
  g.lineWidth = lw;
  g.stroke();
}

// ------------------------------------------------------------------------
// OYUNCU MERMİLERİ (sağa bakar; 40x24, merkez 24,12)
// ------------------------------------------------------------------------
export function projTex(style: string, col: RGB, acc: RGB): Texture {
  return makeTex(`pp|${style}|${col}|${acc}`, 48, 28, (g) => {
    const cx = 28, cy = 14;
    const C = rgbCss(col), A = rgbCss(acc);
    switch (style) {
      case "feather":
        g.beginPath();
        g.moveTo(cx + 10, cy);
        g.quadraticCurveTo(cx - 2, cy - 7, cx - 14, cy - 2);
        g.lineTo(cx - 10, cy);
        g.lineTo(cx - 14, cy + 2);
        g.quadraticCurveTo(cx - 2, cy + 7, cx + 10, cy);
        fs(g, C, 1.2);
        g.strokeStyle = A;
        g.lineWidth = 1;
        g.beginPath();
        g.moveTo(cx - 12, cy);
        g.lineTo(cx + 9, cy);
        g.stroke();
        break;
      case "star": {
        glow(g, cx, cy, 13, col, 0.6);
        g.beginPath();
        for (let i = 0; i < 10; i++) {
          const a = (i * Math.PI) / 5, r = i % 2 ? 3.2 : 7.5;
          g.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
        }
        g.closePath();
        fs(g, A, 1.2);
        break;
      }
      case "lightning":
        glow(g, cx, cy, 14, col, 0.8);
        g.strokeStyle = "#f0ffff";
        g.lineWidth = 2.4;
        g.beginPath();
        g.moveTo(cx - 14, cy);
        g.lineTo(cx - 6, cy - 4);
        g.lineTo(cx, cy + 3);
        g.lineTo(cx + 6, cy - 3);
        g.lineTo(cx + 12, cy);
        g.stroke();
        break;
      case "blackfire":
        glow(g, cx, cy, 13, [150, 70, 230], 0.75);
        circ(g, cx, cy, 6.5);
        fs(g, "#1e1430", 1.4);
        circ(g, cx + 1, cy - 1, 3);
        g.fillStyle = "#b46aff";
        g.fill();
        break;
      case "fireball":
        glow(g, cx, cy, 14, [255, 140, 40], 0.85);
        g.beginPath();
        g.moveTo(cx + 8, cy);
        g.quadraticCurveTo(cx + 2, cy - 9, cx - 14, cy);
        g.quadraticCurveTo(cx + 2, cy + 9, cx + 8, cy);
        g.fillStyle = "#ff8a28";
        g.fill();
        circ(g, cx + 2, cy, 4.5);
        g.fillStyle = "#fff2a0";
        g.fill();
        break;
      case "gold":
        glow(g, cx, cy, 12, col, 0.6);
        circ(g, cx, cy, 5.5);
        fs(g, "#ffd25a", 1.4);
        circ(g, cx - 1.5, cy - 1.5, 2);
        g.fillStyle = "#fff6c8";
        g.fill();
        break;
      case "prism": {
        glow(g, cx, cy, 13, [255, 180, 255], 0.6);
        const gr = g.createLinearGradient(cx - 10, cy, cx + 10, cy);
        gr.addColorStop(0, "#ff7ac8");
        gr.addColorStop(0.5, "#7ad8ff");
        gr.addColorStop(1, "#b0ff7a");
        g.beginPath();
        g.moveTo(cx + 10, cy);
        g.lineTo(cx, cy - 6);
        g.lineTo(cx - 10, cy);
        g.lineTo(cx, cy + 6);
        g.closePath();
        fs(g, gr, 1.2);
        break;
      }
      case "toxic":
        glow(g, cx, cy, 13, [120, 225, 95], 0.7);
        circ(g, cx, cy, 6);
        fs(g, "#78e15f", 1.4);
        circ(g, cx - 2, cy - 2, 2);
        g.fillStyle = "#e0ffd0";
        g.fill();
        break;
      case "web":
        g.strokeStyle = "#f0f2fa";
        g.lineWidth = 1.4;
        for (let i = 0; i < 6; i++) {
          const a = (i / 6) * TAU;
          g.beginPath();
          g.moveTo(cx, cy);
          g.lineTo(cx + Math.cos(a) * 8, cy + Math.sin(a) * 8);
          g.stroke();
        }
        circ(g, cx, cy, 5);
        g.stroke();
        break;
      case "ash":
        glow(g, cx, cy, 12, [190, 40, 45], 0.6);
        circ(g, cx, cy, 5.5);
        fs(g, "#c4c0ba", 1.2);
        break;
      case "rock":
        g.beginPath();
        for (let i = 0; i < 7; i++) {
          const a = (i / 7) * TAU, r = 6 + (i % 2) * 1.6;
          g.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
        }
        g.closePath();
        fs(g, "#78aa5a", 1.4);
        break;
      case "bullet":
        glow(g, cx, cy, 10, [255, 214, 120], 0.6);
        g.beginPath();
        g.ellipse(cx, cy, 7, 3, 0, 0, TAU);
        fs(g, "#ffd678", 1);
        break;
      default: // bolt
        glow(g, cx - 3, cy, 14, col, 0.75);
        g.beginPath();
        g.ellipse(cx, cy, 10, 4, 0, 0, TAU);
        g.fillStyle = C;
        g.fill();
        g.beginPath();
        g.ellipse(cx + 1, cy, 6, 2, 0, 0, TAU);
        g.fillStyle = "#ffffff";
        g.fill();
    }
  }, 2);
}

// ------------------------------------------------------------------------
// DÜŞMAN MERMİLERİ (32x32, merkez)
// ------------------------------------------------------------------------
export function enemyShotTex(style: string, col: RGB): Texture {
  return makeTex(`es|${style}|${col.map(Math.round)}`, 32, 32, (g) => {
    const cx = 16, cy = 16;
    if (style === "icicle") {
      glow(g, cx, cy, 12, col, 0.5);
      g.beginPath();
      g.moveTo(cx + 11, cy);
      g.lineTo(cx - 6, cy - 4);
      g.lineTo(cx - 9, cy);
      g.lineTo(cx - 6, cy + 4);
      g.closePath();
      fs(g, rgbCss(lighten(col, 0.3)), 1.2);
      return;
    }
    if (style === "arrow") {
      g.strokeStyle = "#6a4a2a";
      g.lineWidth = 2;
      g.beginPath();
      g.moveTo(cx - 11, cy);
      g.lineTo(cx + 6, cy);
      g.stroke();
      g.beginPath();
      g.moveTo(cx + 11, cy);
      g.lineTo(cx + 4, cy - 4);
      g.lineTo(cx + 4, cy + 4);
      g.closePath();
      fs(g, "#d8dce6", 1);
      return;
    }
    // orb / spit / poison / boss
    glow(g, cx, cy, 15, col, 0.65);
    circ(g, cx, cy, 6.5);
    const gr = g.createRadialGradient(cx - 2, cy - 2, 1, cx, cy, 7);
    gr.addColorStop(0, "#ffffff");
    gr.addColorStop(0.4, rgbCss(lighten(col, 0.4)));
    gr.addColorStop(1, rgbCss(col));
    fs(g, gr, 1.4);
  }, 2);
}

// ------------------------------------------------------------------------
// TOPLANABİLİRLER
// ------------------------------------------------------------------------
export function pickupTex(kind: string): Texture {
  return makeTex("pu|" + kind, 32, 32, (g) => {
    const cx = 16, cy = 16;
    if (kind === "coin") {
      glow(g, cx, cy, 14, [232, 186, 90], 0.45);
      g.beginPath();
      g.ellipse(cx, cy, 6.5, 7, 0, 0, TAU);
      fs(g, "#e8b84a", 1.4);
      g.beginPath();
      g.ellipse(cx, cy, 4.2, 4.8, 0, 0, TAU);
      g.strokeStyle = "#fff0b0";
      g.lineWidth = 1.2;
      g.stroke();
      circ(g, cx - 2, cy - 2.5, 1.6);
      g.fillStyle = "#fffbe6";
      g.fill();
    } else if (kind === "xp") {
      glow(g, cx, cy, 13, [140, 120, 255], 0.55);
      g.beginPath();
      g.moveTo(cx, cy - 7.5);
      g.lineTo(cx + 5, cy);
      g.lineTo(cx, cy + 7.5);
      g.lineTo(cx - 5, cy);
      g.closePath();
      const gr = g.createLinearGradient(cx - 5, cy - 7, cx + 5, cy + 7);
      gr.addColorStop(0, "#e0d4ff");
      gr.addColorStop(0.5, "#9a78ff");
      gr.addColorStop(1, "#5a3ad0");
      fs(g, gr, 1.2);
    } else if (kind === "heart") {
      glow(g, cx, cy, 15, [255, 90, 110], 0.55);
      g.beginPath();
      g.moveTo(cx, cy + 7);
      g.bezierCurveTo(cx - 12, cy - 1, cx - 6, cy - 10, cx, cy - 4);
      g.bezierCurveTo(cx + 6, cy - 10, cx + 12, cy - 1, cx, cy + 7);
      fs(g, "#ff5a78", 1.4);
      circ(g, cx - 3.5, cy - 3.5, 1.6);
      g.fillStyle = "#ffe0e6";
      g.fill();
    }
  }, 3);
}

export function bigDropTex(kind: "magnet" | "level"): Texture {
  return makeTex("bd|" + kind, 64, 64, (g) => {
    const cx = 32, cy = 32;
    if (kind === "magnet") {
      glow(g, cx, cy, 30, [255, 84, 96], 0.5);
      g.lineCap = "butt";
      g.strokeStyle = OUT;
      g.lineWidth = 12;
      g.beginPath();
      g.arc(cx, cy - 2, 11, Math.PI, 0, true);
      g.stroke();
      g.strokeStyle = "#ff5460";
      g.lineWidth = 9;
      g.stroke();
      g.fillStyle = "#e8f0ff";
      g.fillRect(cx - 15.5, cy - 4, 9, 10);
      g.fillRect(cx + 6.5, cy - 4, 9, 10);
      g.strokeStyle = OUT;
      g.lineWidth = 1.5;
      g.strokeRect(cx - 15.5, cy - 4, 9, 10);
      g.strokeRect(cx + 6.5, cy - 4, 9, 10);
    } else {
      glow(g, cx, cy, 30, [178, 110, 255], 0.55);
      g.beginPath();
      g.moveTo(cx, cy - 16);
      g.lineTo(cx + 12, cy - 4);
      g.lineTo(cx + 8, cy + 14);
      g.lineTo(cx - 8, cy + 14);
      g.lineTo(cx - 12, cy - 4);
      g.closePath();
      const gr = g.createLinearGradient(cx, cy - 16, cx, cy + 14);
      gr.addColorStop(0, "#f2e4ff");
      gr.addColorStop(1, "#8a4aff");
      fs(g, gr, 2);
      g.fillStyle = "#fff";
      g.font = "bold 14px sans-serif";
      g.textAlign = "center";
      g.textBaseline = "middle";
      g.fillText("▲", cx, cy + 2);
    }
  }, 2);
}

export function chestTex(legend: boolean, open: boolean): Texture {
  return makeTex(`chest|${legend}|${open}`, 80, 80, (g) => {
    const cx = 40, cy = 46;
    const main = legend ? "#7a3ad0" : "#8a5a2a";
    const trim = legend ? "#ffc846" : "#e8b84a";
    glow(g, cx, cy - 6, 38, legend ? [255, 200, 90] : [232, 186, 90], 0.5);
    g.beginPath();
    g.roundRect(cx - 22, cy - 6, 44, 24, 4);
    fs(g, main, 2.4);
    g.fillStyle = trim;
    g.fillRect(cx - 22, cy - 2, 44, 4);
    g.fillRect(cx - 3, cy - 6, 6, 24);
    if (open) {
      g.beginPath();
      g.moveTo(cx - 22, cy - 6);
      g.lineTo(cx - 18, cy - 26);
      g.lineTo(cx + 18, cy - 26);
      g.lineTo(cx + 22, cy - 6);
      g.closePath();
      fs(g, main, 2.2);
      glow(g, cx, cy - 10, 26, [255, 240, 180], 0.9);
    } else {
      g.beginPath();
      g.moveTo(cx - 22, cy - 6);
      g.quadraticCurveTo(cx, cy - 26, cx + 22, cy - 6);
      g.closePath();
      fs(g, main, 2.2);
      g.strokeStyle = trim;
      g.lineWidth = 3;
      g.beginPath();
      g.moveTo(cx - 3, cy - 6);
      g.lineTo(cx - 3, cy - 18);
      g.stroke();
      circ(g, cx, cy - 2, 4);
      fs(g, trim, 1.4);
    }
  }, 2);
}

export function keyTex(): Texture {
  return makeTex("key", 48, 48, (g) => {
    glow(g, 24, 24, 22, [255, 214, 90], 0.55);
    g.strokeStyle = OUT;
    g.lineWidth = 6;
    circ(g, 16, 24, 6.5);
    g.stroke();
    g.beginPath();
    g.moveTo(22, 24);
    g.lineTo(38, 24);
    g.moveTo(32, 24);
    g.lineTo(32, 30);
    g.moveTo(37, 24);
    g.lineTo(37, 29);
    g.stroke();
    g.strokeStyle = "#ffd65a";
    g.lineWidth = 3.6;
    circ(g, 16, 24, 6.5);
    g.stroke();
    g.beginPath();
    g.moveTo(22, 24);
    g.lineTo(38, 24);
    g.moveTo(32, 24);
    g.lineTo(32, 30);
    g.moveTo(37, 24);
    g.lineTo(37, 29);
    g.stroke();
  }, 2);
}

export function portalTex(): Texture {
  return makeTex("portal", 160, 160, (g) => {
    const cx = 80, cy = 80;
    glow(g, cx, cy, 78, [178, 86, 255], 0.65);
    for (let i = 0; i < 5; i++) {
      g.strokeStyle = `rgba(${200 + i * 10},${140 + i * 20},255,${0.9 - i * 0.12})`;
      g.lineWidth = 5 - i * 0.6;
      g.beginPath();
      g.ellipse(cx, cy, 52 - i * 9, 60 - i * 10, 0, 0, TAU);
      g.stroke();
    }
    const gr = g.createRadialGradient(cx, cy, 2, cx, cy, 40);
    gr.addColorStop(0, "#1a0630");
    gr.addColorStop(1, "rgba(80,20,140,0.2)");
    g.fillStyle = gr;
    g.beginPath();
    g.ellipse(cx, cy, 40, 48, 0, 0, TAU);
    g.fill();
  }, 2);
}

// ------------------------------------------------------------------------
// SİLAH NESNELERİ
// ------------------------------------------------------------------------
export function axeTex(): Texture {
  return makeTex("axe", 56, 56, (g) => {
    g.translate(28, 28);
    g.strokeStyle = OUT;
    g.lineWidth = 6;
    g.beginPath();
    g.moveTo(-16, 10);
    g.lineTo(12, -8);
    g.stroke();
    g.strokeStyle = "#845632";
    g.lineWidth = 4;
    g.stroke();
    g.beginPath();
    g.moveTo(4, -14);
    g.quadraticCurveTo(22, -18, 20, 2);
    g.lineTo(8, -4);
    g.closePath();
    const gr = g.createLinearGradient(4, -16, 20, 2);
    gr.addColorStop(0, "#eef2fa");
    gr.addColorStop(1, "#7a8092");
    fs(g, gr, 1.8);
  }, 2);
}
export function knifeTex(): Texture {
  return makeTex("knife", 40, 16, (g) => {
    g.beginPath();
    g.moveTo(38, 8);
    g.lineTo(16, 4);
    g.lineTo(16, 12);
    g.closePath();
    fs(g, "#e6ecf8", 1.2);
    g.fillStyle = "#5a3a22";
    g.fillRect(4, 6, 12, 4);
  }, 2);
}
export function ghostSwordTex(): Texture {
  return makeTex("gsword", 56, 20, (g) => {
    glow(g, 30, 10, 22, [130, 222, 255], 0.5);
    g.beginPath();
    g.moveTo(54, 10);
    g.lineTo(18, 5);
    g.lineTo(18, 15);
    g.closePath();
    fs(g, "rgba(210,246,255,0.95)", 1.2);
    g.fillStyle = "#82deff";
    g.fillRect(12, 3, 5, 14);
    g.fillRect(4, 8, 9, 4);
  }, 2);
}
export function wolfTex(f: number): Texture {
  return makeTex("wolf" + f, 64, 48, (g) => {
    const col: RGB = [158, 168, 255];
    glow(g, 32, 26, 28, col, 0.35);
    g.globalAlpha = 0.92;
    const leg = (x: number, ph: number) => {
      g.strokeStyle = rgbCss(darken(col, 0.3));
      g.lineWidth = 4;
      g.beginPath();
      g.moveTo(x, 28);
      g.lineTo(x + ((ph + f) % 2 ? 4 : -4), 40);
      g.stroke();
    };
    leg(18, 0);
    leg(24, 1);
    leg(38, 1);
    leg(44, 0);
    g.beginPath();
    g.ellipse(30, 24, 17, 8, 0, 0, TAU);
    fs(g, rgbCss(col), 1.6);
    g.beginPath();
    g.moveTo(13, 22);
    g.quadraticCurveTo(4, 14, 2, 10 + f * 3);
    g.strokeStyle = rgbCss(col);
    g.lineWidth = 4;
    g.stroke();
    g.beginPath();
    g.ellipse(48, 16, 9, 7, 0.2, 0, TAU);
    fs(g, rgbCss(lighten(col, 0.2)), 1.6);
    g.beginPath();
    g.moveTo(44, 10);
    g.lineTo(46, 2);
    g.lineTo(50, 10);
    fs(g, rgbCss(col), 1.2);
    g.beginPath();
    g.moveTo(52, 16);
    g.lineTo(61, 19);
    g.lineTo(52, 22);
    fs(g, rgbCss(lighten(col, 0.3)), 1.2);
    circ(g, 50, 14, 1.8);
    g.fillStyle = "#fff";
    g.fill();
  }, 2);
}
export function hawkTex(f: number): Texture {
  return makeTex("hawk" + f, 64, 48, (g) => {
    const col: RGB = [226, 168, 96];
    const up = f === 0;
    for (const s of [-1, 1]) {
      g.beginPath();
      g.moveTo(32, 24);
      g.quadraticCurveTo(32 + s * 14, up ? 4 : 20, 32 + s * 30, up ? 8 : 28);
      g.quadraticCurveTo(32 + s * 16, up ? 18 : 30, 32, 30);
      g.closePath();
      fs(g, rgbCss(darken(col, 0.1)), 1.6);
    }
    g.beginPath();
    g.ellipse(32, 26, 6, 10, 0, 0, TAU);
    fs(g, rgbCss(col), 1.6);
    circ(g, 32, 16, 5);
    fs(g, "#f6ecd8", 1.4);
    g.beginPath();
    g.moveTo(30, 14);
    g.lineTo(32, 10);
    g.lineTo(34, 14);
    g.fillStyle = "#ffc846";
    g.fill();
  }, 2);
}
export function batTex(f: number): Texture {
  return makeTex("wbat" + f, 40, 28, (g) => {
    const col: RGB = [186, 104, 238];
    glow(g, 20, 14, 16, col, 0.4);
    for (const s of [-1, 1]) {
      g.beginPath();
      g.moveTo(20, 14);
      g.quadraticCurveTo(20 + s * 10, f ? 2 : 10, 20 + s * 18, f ? 6 : 18);
      g.quadraticCurveTo(20 + s * 10, 16, 20, 18);
      g.closePath();
      fs(g, rgbCss(col), 1.2);
    }
    circ(g, 20, 15, 4.5);
    fs(g, rgbCss(darken(col, 0.3)), 1.2);
  }, 2);
}
export function shieldBookTex(charged: boolean): Texture {
  return makeTex("shbook" + charged, 40, 44, (g) => {
    const cx = 20, cy = 20;
    if (charged) glow(g, cx, cy, 20, [150, 176, 214], 0.45);
    g.globalAlpha = charged ? 1 : 0.45;
    g.beginPath();
    g.moveTo(cx - 12, cy - 12);
    g.lineTo(cx + 12, cy - 12);
    g.quadraticCurveTo(cx + 13, cy + 8, cx, cy + 18);
    g.quadraticCurveTo(cx - 13, cy + 8, cx - 12, cy - 12);
    g.closePath();
    const gr = g.createLinearGradient(cx - 12, cy - 12, cx + 12, cy + 16);
    gr.addColorStop(0, "#e6f0ff");
    gr.addColorStop(1, "#6a7ea6");
    fs(g, gr, 2);
    g.strokeStyle = "#e2ba62";
    g.lineWidth = 2;
    g.beginPath();
    g.moveTo(cx, cy - 10);
    g.lineTo(cx, cy + 14);
    g.moveTo(cx - 9, cy - 2);
    g.lineTo(cx + 9, cy - 2);
    g.stroke();
  }, 2);
}
export function pentagramTex(): Texture {
  return makeTex("penta", 256, 256, (g) => {
    const cx = 128, cy = 128, R = 120;
    const gr = g.createRadialGradient(cx, cy, 10, cx, cy, R);
    gr.addColorStop(0, "rgba(238,78,122,0.05)");
    gr.addColorStop(0.85, "rgba(238,78,122,0.18)");
    gr.addColorStop(1, "rgba(238,78,122,0.0)");
    g.fillStyle = gr;
    circ(g, cx, cy, R);
    g.fill();
    g.strokeStyle = "rgba(255,150,190,0.85)";
    g.lineWidth = 3;
    circ(g, cx, cy, R - 4);
    g.stroke();
    circ(g, cx, cy, R - 14);
    g.stroke();
    g.lineWidth = 2.5;
    g.beginPath();
    for (let i = 0; i <= 5; i++) {
      const a = -Math.PI / 2 + ((i * 2) % 5) * ((TAU) / 5);
      const x = cx + Math.cos(a) * (R - 14), y = cy + Math.sin(a) * (R - 14);
      i ? g.lineTo(x, y) : g.moveTo(x, y);
    }
    g.stroke();
  }, 1);
}
export function puddleTex(): Texture {
  return makeTex("puddle", 128, 128, (g) => {
    const cx = 64, cy = 64;
    const gr = g.createRadialGradient(cx, cy, 6, cx, cy, 62);
    gr.addColorStop(0, "rgba(150,220,255,0.55)");
    gr.addColorStop(0.8, "rgba(80,170,255,0.45)");
    gr.addColorStop(1, "rgba(200,240,255,0)");
    g.fillStyle = gr;
    g.beginPath();
    for (let i = 0; i < 16; i++) {
      const a = (i / 16) * TAU, r = 58 + Math.sin(i * 2.3) * 4;
      g.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
    }
    g.closePath();
    g.fill();
    g.strokeStyle = "rgba(220,248,255,0.8)";
    g.lineWidth = 2;
    g.stroke();
  }, 1);
}
export function fireRingTex(ice: boolean): Texture {
  return makeTex("fring" + ice, 128, 128, (g) => {
    const cx = 64, cy = 64;
    const c1 = ice ? "rgba(150,220,255," : "rgba(255,140,50,";
    const gr = g.createRadialGradient(cx, cy, 30, cx, cy, 62);
    gr.addColorStop(0, c1 + "0.0)");
    gr.addColorStop(0.75, c1 + "0.35)");
    gr.addColorStop(0.92, c1 + "0.9)");
    gr.addColorStop(1, c1 + "0)");
    g.fillStyle = gr;
    circ(g, cx, cy, 63);
    g.fill();
    g.strokeStyle = ice ? "rgba(235,250,255,0.9)" : "rgba(255,230,140,0.9)";
    g.lineWidth = 2;
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * TAU;
      g.beginPath();
      g.moveTo(cx + Math.cos(a) * 54, cy + Math.sin(a) * 54);
      g.lineTo(cx + Math.cos(a + 0.12) * 62, cy + Math.sin(a + 0.12) * 62);
      g.stroke();
    }
  }, 1);
}
export function dangerTex(): Texture {
  return makeTex("danger", 128, 128, (g) => {
    const cx = 64, cy = 64;
    const gr = g.createRadialGradient(cx, cy, 0, cx, cy, 63);
    gr.addColorStop(0, "rgba(255,255,255,0.08)");
    gr.addColorStop(0.85, "rgba(255,255,255,0.28)");
    gr.addColorStop(1, "rgba(255,255,255,0.0)");
    g.fillStyle = gr;
    circ(g, cx, cy, 63);
    g.fill();
    g.strokeStyle = "rgba(255,255,255,0.95)";
    g.lineWidth = 3;
    circ(g, cx, cy, 60);
    g.stroke();
  }, 1);
}
export function tornadoTex(f: number): Texture {
  return makeTex("tornado" + f, 128, 160, (g) => {
    const cx = 64;
    for (let i = 0; i < 9; i++) {
      const y = 150 - i * 16;
      const w = 10 + i * 6.5;
      g.strokeStyle = `rgba(220,236,250,${0.35 + i * 0.06})`;
      g.lineWidth = 3;
      g.beginPath();
      g.ellipse(cx + Math.sin(i * 0.9 + f * 1.5) * 6, y, w, w * 0.28, 0, 0, TAU);
      g.stroke();
    }
  }, 1);
}
export function rockTex(): Texture {
  return makeTex("meteorrock", 64, 64, (g) => {
    glow(g, 32, 32, 30, [255, 120, 50], 0.6);
    g.beginPath();
    for (let i = 0; i < 9; i++) {
      const a = (i / 9) * TAU, r = 14 + ((i * 7) % 5);
      g.lineTo(32 + Math.cos(a) * r, 32 + Math.sin(a) * r);
    }
    g.closePath();
    fs(g, "#5a3a2a", 2);
    g.fillStyle = "#ff8a3a";
    for (const [x, y] of [[26, 28], [36, 36], [34, 24]]) {
      circ(g, x, y, 2.6);
      g.fill();
    }
  }, 2);
}
export function blackHoleTex(): Texture {
  return makeTex("bhole", 256, 256, (g) => {
    const cx = 128, cy = 128;
    const gr = g.createRadialGradient(cx, cy, 6, cx, cy, 126);
    gr.addColorStop(0, "rgba(0,0,0,1)");
    gr.addColorStop(0.18, "rgba(20,0,40,0.95)");
    gr.addColorStop(0.3, "rgba(170,140,255,0.6)");
    gr.addColorStop(0.55, "rgba(90,60,200,0.25)");
    gr.addColorStop(1, "rgba(60,40,140,0)");
    g.fillStyle = gr;
    circ(g, cx, cy, 126);
    g.fill();
  }, 1);
}

// ------------------------------------------------------------------------
// PATRONLAR (r*3 tuval, merkez)
// ------------------------------------------------------------------------
export function bossTex(kind: string, col: RGB, theme: string | null, hellish: boolean, R: number, flash = false): Texture {
  const key = `boss|${kind}|${col.map(Math.round)}|${theme}|${hellish}|${R}|${flash}`;
  const S = Math.ceil(R * 3.2);
  return makeTex(key, S, S, (g) => {
    const cx = S / 2, cy = S / 2 + R * 0.1;
    const shadeG = (x: number, y: number, r: number, c: RGB) => {
      const gr = g.createRadialGradient(x - r * 0.4, y - r * 0.45, r * 0.05, x, y, r * 1.05);
      gr.addColorStop(0, rgbCss(lighten(c, 0.4)));
      gr.addColorStop(0.55, rgbCss(c));
      gr.addColorStop(1, rgbCss(darken(c, 0.4)));
      return gr;
    };
    const dark = darken(col, 0.45);
    // aura
    glow(g, cx, cy, R * 1.5, hellish ? [255, 90, 40] : col, 0.25);
    switch (kind) {
      case "warlord": {
        for (const s of [-1, 1]) {
          circ(g, cx + s * R * 0.95, cy - R * 0.25, R * 0.42);
          fs(g, shadeG(cx + s * R, cy - R * 0.3, R * 0.4, darken(col, 0.1)), 3);
          for (let k = 0; k < 3; k++) {
            g.beginPath();
            g.moveTo(cx + s * R * (0.8 + k * 0.15), cy - R * 0.6);
            g.lineTo(cx + s * R * (0.9 + k * 0.15), cy - R * 0.95);
            g.lineTo(cx + s * R * (1.0 + k * 0.15), cy - R * 0.58);
            fs(g, "#d8d4c8", 1.6);
          }
        }
        circ(g, cx, cy, R * 0.9);
        fs(g, shadeG(cx, cy, R * 0.9, col), 3.5);
        g.beginPath();
        g.roundRect(cx - R * 0.55, cy - R * 0.55, R * 1.1, R * 0.5, R * 0.15);
        fs(g, rgbCss(dark), 2.5);
        g.fillStyle = "#14101c";
        g.fillRect(cx - R * 0.45, cy - R * 0.38, R * 0.9, R * 0.14);
        eyes(g, cx, cy - R * 0.31, R, { n: 2, spread: 0.24, size: 0.08, col: "#ffe6c8", pupil: "#ff3a1a", glow: "rgba(255,80,40,1)" });
        // kılıç
        g.save();
        g.translate(cx + R * 0.9, cy + R * 0.2);
        g.rotate(-0.6);
        g.beginPath();
        g.moveTo(-R * 0.08, 0);
        g.lineTo(-R * 0.08, -R * 1.3);
        g.lineTo(0, -R * 1.5);
        g.lineTo(R * 0.08, -R * 1.3);
        g.lineTo(R * 0.08, 0);
        g.closePath();
        fs(g, "#e2e6ee", 2);
        g.fillStyle = "#d2a046";
        g.fillRect(-R * 0.25, -R * 0.05, R * 0.5, R * 0.12);
        g.restore();
        break;
      }
      case "witch": {
        g.beginPath();
        g.moveTo(cx - R * 0.95, cy + R * 0.95);
        g.quadraticCurveTo(cx - R * 0.8, cy - R * 0.2, cx, cy - R * 0.4);
        g.quadraticCurveTo(cx + R * 0.8, cy - R * 0.2, cx + R * 0.95, cy + R * 0.95);
        g.closePath();
        fs(g, shadeG(cx, cy, R, col), 3);
        circ(g, cx, cy - R * 0.35, R * 0.45);
        fs(g, "#d8c8e8", 2.4);
        g.beginPath();
        g.moveTo(cx - R * 0.85, cy - R * 0.55);
        g.lineTo(cx + R * 0.25, cy - R * 1.75);
        g.lineTo(cx + R * 0.85, cy - R * 0.55);
        g.closePath();
        fs(g, rgbCss(dark), 2.6);
        g.beginPath();
        g.ellipse(cx, cy - R * 0.55, R * 1.05, R * 0.2, 0, 0, TAU);
        fs(g, rgbCss(darken(col, 0.3)), 2.4);
        eyes(g, cx, cy - R * 0.35, R, { n: 2, spread: 0.2, size: 0.09, col: "#f0d0ff", pupil: "#a020ff", glow: "rgba(200,90,255,1)" });
        glow(g, cx + R * 0.95, cy + R * 0.1, R * 0.4, [200, 120, 255], 0.8);
        break;
      }
      case "colossus": {
        for (const s of [-1, 1]) {
          g.beginPath();
          g.roundRect(cx + s * R * 0.95 - R * 0.35, cy - R * 0.2, R * 0.7, R * 0.9, R * 0.2);
          fs(g, shadeG(cx, cy, R, darken(col, 0.15)), 3);
        }
        g.beginPath();
        const pts = [[-0.85, -0.55], [-0.35, -1.0], [0.35, -1.0], [0.85, -0.55], [0.8, 0.75], [-0.8, 0.75]];
        pts.forEach(([x, y], i) => (i ? g.lineTo(cx + x * R, cy + y * R) : g.moveTo(cx + x * R, cy + y * R)));
        g.closePath();
        fs(g, shadeG(cx, cy, R, col), 3.5);
        g.strokeStyle = rgbCss(darken(col, 0.5));
        g.lineWidth = 2;
        g.beginPath();
        g.moveTo(cx - R * 0.5, cy - R * 0.2);
        g.lineTo(cx - R * 0.1, cy + R * 0.3);
        g.lineTo(cx + R * 0.4, cy);
        g.stroke();
        eyes(g, cx, cy - R * 0.55, R, { n: 2, spread: 0.24, size: 0.09, col: "#d0f0ff", pupil: "#40b0ff", glow: "rgba(120,200,255,1)" });
        break;
      }
      case "reaper": {
        g.beginPath();
        g.moveTo(cx - R * 0.85, cy + R * 0.9);
        for (let i = 0; i < 5; i++) g.lineTo(cx - R * 0.85 + i * R * 0.42 + R * 0.21, cy + R * (i % 2 ? 0.65 : 0.95));
        g.lineTo(cx + R * 0.85, cy + R * 0.9);
        g.quadraticCurveTo(cx + R * 0.9, cy - R * 1.2, cx, cy - R * 1.05);
        g.quadraticCurveTo(cx - R * 0.9, cy - R * 1.2, cx - R * 0.85, cy + R * 0.9);
        g.closePath();
        g.globalAlpha = 0.95;
        fs(g, shadeG(cx, cy, R, darken(col, 0.4)), 3);
        g.globalAlpha = 1;
        g.beginPath();
        g.ellipse(cx, cy - R * 0.3, R * 0.45, R * 0.5, 0, 0, TAU);
        g.fillStyle = "#08060e";
        g.fill();
        eyes(g, cx, cy - R * 0.35, R, { n: 2, spread: 0.18, size: 0.09, col: rgbCss(lighten(col, 0.5)), pupil: rgbCss(col), glow: rgbCss(col) });
        g.save();
        g.translate(cx - R * 0.95, cy);
        g.strokeStyle = "#4a3a2a";
        g.lineWidth = R * 0.08;
        g.beginPath();
        g.moveTo(0, R * 0.9);
        g.lineTo(0, -R * 1.2);
        g.stroke();
        g.beginPath();
        g.moveTo(0, -R * 1.2);
        g.quadraticCurveTo(R * 0.9, -R * 1.4, R * 1.1, -R * 0.7);
        g.quadraticCurveTo(R * 0.7, -R * 1.0, 0, -R * 0.98);
        fs(g, "#d8e0ea", 2);
        g.restore();
        break;
      }
      case "hive": {
        for (const s of [-1, 1]) {
          g.beginPath();
          g.ellipse(cx + s * R * 0.75, cy - R * 0.6, R * 0.55, R * 0.28, s * 0.5, 0, TAU);
          g.fillStyle = "rgba(230,245,255,0.65)";
          g.fill();
          g.strokeStyle = OUT;
          g.lineWidth = 2;
          g.stroke();
        }
        g.beginPath();
        g.ellipse(cx, cy + R * 0.2, R * 0.75, R * 0.85, 0, 0, TAU);
        fs(g, shadeG(cx, cy, R, col), 3.5);
        g.fillStyle = "#2a1c10";
        for (let i = 0; i < 3; i++) g.fillRect(cx - R * 0.75, cy - R * 0.1 + i * R * 0.32, R * 1.5, R * 0.1);
        circ(g, cx, cy - R * 0.65, R * 0.45);
        fs(g, shadeG(cx, cy - R * 0.65, R * 0.45, darken(col, 0.2)), 3);
        eyes(g, cx, cy - R * 0.7, R, { n: 2, spread: 0.26, size: 0.13, col: "#ff4a3a", pupil: "#300" });
        break;
      }
      default: {
        // dragon
        for (const s of [-1, 1]) {
          g.beginPath();
          g.moveTo(cx + s * R * 0.4, cy - R * 0.2);
          g.quadraticCurveTo(cx + s * R * 1.5, cy - R * 1.4, cx + s * R * 1.55, cy - R * 0.1);
          g.quadraticCurveTo(cx + s * R * 1.1, cy - R * 0.25, cx + s * R * 0.9, cy + R * 0.3);
          g.closePath();
          fs(g, rgbCss(darken(col, 0.25)), 3);
        }
        g.beginPath();
        g.ellipse(cx, cy + R * 0.15, R * 0.75, R * 0.8, 0, 0, TAU);
        fs(g, shadeG(cx, cy, R, col), 3.5);
        g.beginPath();
        g.ellipse(cx, cy + R * 0.35, R * 0.45, R * 0.5, 0, 0, TAU);
        g.fillStyle = "rgba(255,210,140,0.6)";
        g.fill();
        circ(g, cx, cy - R * 0.62, R * 0.45);
        fs(g, shadeG(cx, cy - R * 0.6, R * 0.45, col), 3);
        for (const s of [-1, 1]) {
          g.beginPath();
          g.moveTo(cx + s * R * 0.2, cy - R * 0.95);
          g.quadraticCurveTo(cx + s * R * 0.5, cy - R * 1.4, cx + s * R * 0.62, cy - R * 1.45);
          g.lineTo(cx + s * R * 0.4, cy - R * 0.92);
          fs(g, "#e8dcc8", 2);
        }
        eyes(g, cx, cy - R * 0.68, R, { n: 2, spread: 0.24, size: 0.1, col: "#fff2a0", pupil: "#ff3a00", glow: "rgba(255,120,30,1)" });
      }
    }
    // tema / cehennem tacı
    if (hellish) {
      g.fillStyle = "#ff7a2a";
      g.shadowColor = "#ff4a00";
      g.shadowBlur = 10;
      for (let i = 0; i < 5; i++) {
        const x = cx + (i - 2) * R * 0.2;
        g.beginPath();
        g.moveTo(x - R * 0.08, cy - R * 1.0);
        g.quadraticCurveTo(x, cy - R * (1.35 + (i % 2) * 0.15), x + R * 0.08, cy - R * 1.0);
        g.fill();
      }
      g.shadowBlur = 0;
    } else if (theme === "frost") {
      g.fillStyle = "rgba(220,245,255,0.95)";
      for (let i = 0; i < 5; i++) {
        const x = cx + (i - 2) * R * 0.18;
        g.beginPath();
        g.moveTo(x - R * 0.06, cy - R * 1.0);
        g.lineTo(x, cy - R * (1.3 + (i % 2) * 0.12));
        g.lineTo(x + R * 0.06, cy - R * 1.0);
        g.fill();
      }
    } else if (theme === "jungle") {
      g.fillStyle = "#5ab446";
      for (let i = 0; i < 6; i++) {
        const a = Math.PI + (i / 5) * Math.PI;
        g.beginPath();
        g.ellipse(cx + Math.cos(a) * R * 0.55, cy - R * 0.85 + Math.sin(a) * R * 0.2, R * 0.16, R * 0.08, a, 0, TAU);
        g.fill();
      }
    } else if (theme === "desert") {
      g.beginPath();
      g.moveTo(cx - R * 0.55, cy - R * 0.85);
      g.lineTo(cx, cy - R * 1.35);
      g.lineTo(cx + R * 0.55, cy - R * 0.85);
      g.closePath();
      fs(g, "#e8b84a", 2);
      g.fillStyle = "#2a5aa0";
      g.fillRect(cx - R * 0.45, cy - R * 1.0, R * 0.9, R * 0.08);
    }
    if (flash) {
      g.globalCompositeOperation = "source-atop";
      g.fillStyle = "rgba(255,255,255,0.9)";
      g.fillRect(0, 0, S, S);
    }
  }, flash ? 1 : 2);
}
