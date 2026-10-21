/**
 * Harita zemini (dikişsiz tekrar eden doku) ve dekorlar.
 */
import { Container, Sprite, Texture, TilingSprite } from "pixi.js";
import { makeTex } from "./tex";
import { RGB, rgbCss, lighten, darken, mixCol, mulberry32, TAU } from "../core/util";

type G = CanvasRenderingContext2D;
const T = 512;

function wrap(g: G, x: number, y: number, r: number, fn: (x: number, y: number) => void) {
  for (const ox of [-T, 0, T]) for (const oy of [-T, 0, T]) {
    const xx = x + ox, yy = y + oy;
    if (xx + r < 0 || yy + r < 0 || xx - r > T || yy - r > T) continue;
    fn(xx, yy);
  }
}
function noise(g: G, rnd: () => number, n: number, cols: string[], rmin: number, rmax: number, alpha = 1) {
  for (let i = 0; i < n; i++) {
    const x = rnd() * T, y = rnd() * T, r = rmin + rnd() * (rmax - rmin);
    g.fillStyle = cols[Math.floor(rnd() * cols.length)];
    g.globalAlpha = alpha * (0.4 + rnd() * 0.6);
    wrap(g, x, y, r, (xx, yy) => {
      g.beginPath();
      g.ellipse(xx, yy, r, r * (0.6 + rnd() * 0.4), rnd() * 3, 0, TAU);
      g.fill();
    });
  }
  g.globalAlpha = 1;
}

export function floorTex(biome: string): Texture {
  return makeTex("floor|" + biome, T, T, (g) => {
    const rnd = mulberry32(biome.length * 977 + 13);
    if (biome === "stone") {
      g.fillStyle = "#2a2f48";
      g.fillRect(0, 0, T, T);
      // taş döşemeler
      const rows = 8, h = T / rows;
      for (let r = 0; r < rows; r++) {
        let x = r % 2 ? -h * 0.5 : 0;
        while (x < T) {
          const w = h * (0.9 + rnd() * 0.9);
          const base = mixCol([46, 52, 80], [58, 64, 96], rnd());
          const gr = g.createLinearGradient(x, r * h, x + w, r * h + h);
          gr.addColorStop(0, rgbCss(lighten(base, 0.06)));
          gr.addColorStop(1, rgbCss(darken(base, 0.1)));
          g.fillStyle = gr;
          const pad = 2.5;
          wrap(g, x + w / 2, r * h + h / 2, w, (xx, yy) => {
            g.beginPath();
            g.roundRect(xx - w / 2 + pad, yy - h / 2 + pad, w - pad * 2, h - pad * 2, 5);
            g.fill();
          });
          x += w;
        }
      }
      noise(g, rnd, 260, ["#3c4468", "#252a42", "#4a5480"], 2, 8, 0.35);
      noise(g, rnd, 40, ["#3a6a56", "#2e5646"], 6, 18, 0.25); // yosun
      // çatlaklar
      g.strokeStyle = "rgba(15,18,30,0.45)";
      g.lineWidth = 1.4;
      for (let i = 0; i < 14; i++) {
        let x = rnd() * T, y = rnd() * T;
        g.beginPath();
        g.moveTo(x, y);
        for (let k = 0; k < 4; k++) {
          x += rnd() * 26 - 13;
          y += rnd() * 26 - 13;
          g.lineTo(x, y);
        }
        g.stroke();
      }
    } else if (biome === "frost") {
      const gr = g.createLinearGradient(0, 0, T, T);
      gr.addColorStop(0, "#c8d8ec");
      gr.addColorStop(1, "#b2c6e0");
      g.fillStyle = gr;
      g.fillRect(0, 0, T, T);
      noise(g, rnd, 220, ["#d8e6f6", "#a8bcd8", "#e8f2fc"], 6, 26, 0.45);
      noise(g, rnd, 30, ["#9ec6ee", "#b6dcff"], 18, 46, 0.35); // buz parçaları
      g.fillStyle = "#ffffff";
      for (let i = 0; i < 160; i++) {
        g.globalAlpha = 0.4 + rnd() * 0.6;
        g.fillRect(rnd() * T, rnd() * T, 1.6, 1.6);
      }
      g.globalAlpha = 1;
    } else if (biome === "jungle") {
      g.fillStyle = "#2c4a26";
      g.fillRect(0, 0, T, T);
      noise(g, rnd, 300, ["#355a2c", "#244020", "#3e6832", "#2a4a22"], 6, 22, 0.6);
      // ot öbekleri
      for (let i = 0; i < 360; i++) {
        const x = rnd() * T, y = rnd() * T;
        g.strokeStyle = rnd() < 0.5 ? "#4f8a3a" : "#3c7030";
        g.lineWidth = 1.4;
        wrap(g, x, y, 8, (xx, yy) => {
          g.beginPath();
          g.moveTo(xx, yy);
          g.lineTo(xx + rnd() * 4 - 2, yy - 5 - rnd() * 4);
          g.stroke();
        });
      }
      noise(g, rnd, 24, ["#e8d24a", "#ff8ab0", "#ffffff"], 1.5, 2.6, 0.9); // çiçek
    } else if (biome === "desert") {
      const gr = g.createLinearGradient(0, 0, 0, T);
      gr.addColorStop(0, "#d8a868");
      gr.addColorStop(1, "#c8955a");
      g.fillStyle = gr;
      g.fillRect(0, 0, T, T);
      noise(g, rnd, 200, ["#e2b878", "#bf8a50", "#d09c62"], 8, 30, 0.4);
      // kum dalgaları
      g.strokeStyle = "rgba(150,100,55,0.35)";
      g.lineWidth = 2;
      for (let i = 0; i < 26; i++) {
        const y0 = rnd() * T, x0 = rnd() * T, w = 60 + rnd() * 90;
        wrap(g, x0, y0, w, (xx, yy) => {
          g.beginPath();
          g.moveTo(xx - w / 2, yy);
          g.quadraticCurveTo(xx, yy - 8, xx + w / 2, yy);
          g.stroke();
        });
      }
      noise(g, rnd, 90, ["#8a6440", "#a07850"], 1.5, 3.5, 0.8); // çakıl
    } else {
      // cehennem
      g.fillStyle = "#1e1214";
      g.fillRect(0, 0, T, T);
      noise(g, rnd, 260, ["#2a1a1c", "#160c0e", "#34201e"], 6, 26, 0.7);
      // lav çatlakları
      for (let i = 0; i < 18; i++) {
        let x = rnd() * T, y = rnd() * T;
        const pts: [number, number][] = [[x, y]];
        for (let k = 0; k < 6; k++) {
          x += rnd() * 40 - 20;
          y += rnd() * 40 - 20;
          pts.push([x, y]);
        }
        for (const [lw, col] of [[7, "rgba(255,90,20,0.25)"], [3, "rgba(255,120,40,0.85)"], [1.2, "rgba(255,220,140,0.95)"]] as [number, string][]) {
          g.strokeStyle = col;
          g.lineWidth = lw;
          for (const [ox, oy] of [[-T, 0], [0, 0], [T, 0], [0, -T], [0, T]]) {
            g.beginPath();
            pts.forEach(([px, py], j) => (j ? g.lineTo(px + ox, py + oy) : g.moveTo(px + ox, py + oy)));
            g.stroke();
          }
        }
      }
      noise(g, rnd, 50, ["#ff7a2a"], 1, 2, 0.6);
    }
  }, 1);
}

// ------------------------------------------------------------------------
// DEKORLAR
// ------------------------------------------------------------------------
const OUT = "rgba(12,10,20,0.9)";
function fs(g: G, fill: string | CanvasGradient, lw = 2) {
  g.fillStyle = fill;
  g.fill();
  g.strokeStyle = OUT;
  g.lineWidth = lw;
  g.stroke();
}
function shadow(g: G, cx: number, cy: number, rx: number) {
  const gr = g.createRadialGradient(cx, cy, 0, cx, cy, rx);
  gr.addColorStop(0, "rgba(0,0,0,0.4)");
  gr.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = gr;
  g.beginPath();
  g.ellipse(cx, cy, rx, rx * 0.35, 0, 0, TAU);
  g.fill();
}

interface DecoDef {
  w: number;
  h: number;
  flat?: boolean;
  draw: (g: G, w: number, h: number) => void;
}

const DECOS: Record<string, DecoDef> = {
  pillar: { w: 60, h: 120, draw: (g, w, h) => {
    shadow(g, w / 2, h - 8, 28);
    g.beginPath();
    g.roundRect(w / 2 - 16, 24, 32, h - 34, 3);
    const gr = g.createLinearGradient(w / 2 - 16, 0, w / 2 + 16, 0);
    gr.addColorStop(0, "#8c92ac");
    gr.addColorStop(0.5, "#c6cadc");
    gr.addColorStop(1, "#6a7090");
    fs(g, gr);
    g.strokeStyle = "rgba(40,44,70,0.5)";
    for (let i = 0; i < 3; i++) {
      g.beginPath();
      g.moveTo(w / 2 - 8 + i * 8, 30);
      g.lineTo(w / 2 - 8 + i * 8, h - 14);
      g.stroke();
    }
    g.beginPath();
    g.roundRect(w / 2 - 22, h - 16, 44, 12, 3);
    fs(g, "#7a809a");
    g.beginPath();
    g.moveTo(w / 2 - 20, 26);
    g.lineTo(w / 2 - 12, 12);
    g.lineTo(w / 2 + 2, 20);
    g.lineTo(w / 2 + 10, 10);
    g.lineTo(w / 2 + 20, 26);
    g.closePath();
    fs(g, "#9aa0b8");
  } },
  brazier: { w: 48, h: 72, draw: (g, w, h) => {
    shadow(g, w / 2, h - 6, 18);
    const gr = g.createRadialGradient(w / 2, 22, 2, w / 2, 22, 24);
    gr.addColorStop(0, "rgba(255,200,90,0.9)");
    gr.addColorStop(1, "rgba(255,120,40,0)");
    g.fillStyle = gr;
    g.fillRect(0, 0, w, 48);
    g.beginPath();
    g.moveTo(w / 2 - 12, 26);
    g.quadraticCurveTo(w / 2 - 6, 4, w / 2, 8);
    g.quadraticCurveTo(w / 2 + 8, 2, w / 2 + 12, 26);
    g.fillStyle = "#ffb43a";
    g.fill();
    g.beginPath();
    g.moveTo(w / 2 - 16, 26);
    g.lineTo(w / 2 + 16, 26);
    g.lineTo(w / 2 + 10, 38);
    g.lineTo(w / 2 - 10, 38);
    g.closePath();
    fs(g, "#5a4a3e");
    g.strokeStyle = OUT;
    g.lineWidth = 5;
    g.beginPath();
    g.moveTo(w / 2, 38);
    g.lineTo(w / 2, h - 8);
    g.stroke();
    g.strokeStyle = "#7a6a5a";
    g.lineWidth = 3;
    g.stroke();
  } },
  obelisk: { w: 50, h: 140, draw: (g, w, h) => {
    shadow(g, w / 2, h - 6, 24);
    g.beginPath();
    g.moveTo(w / 2 - 14, h - 10);
    g.lineTo(w / 2 - 9, 22);
    g.lineTo(w / 2, 8);
    g.lineTo(w / 2 + 9, 22);
    g.lineTo(w / 2 + 14, h - 10);
    g.closePath();
    const gr = g.createLinearGradient(w / 2 - 14, 0, w / 2 + 14, 0);
    gr.addColorStop(0, "#4a4e6a");
    gr.addColorStop(0.5, "#6e7494");
    gr.addColorStop(1, "#353850");
    fs(g, gr);
    g.fillStyle = "rgba(120,170,255,0.85)";
    for (let i = 0; i < 4; i++) g.fillRect(w / 2 - 3, 36 + i * 20, 6, 8);
  } },
  rubble: { w: 70, h: 40, flat: true, draw: (g, w, h) => {
    for (let i = 0; i < 6; i++) {
      const x = 10 + i * 9 + (i % 2) * 4, y = h / 2 + (i % 3) * 5 - 4;
      g.beginPath();
      g.ellipse(x, y, 8 + (i % 3), 5, i, 0, TAU);
      fs(g, i % 2 ? "#5a6080" : "#4a5070", 1.5);
    }
  } },
  rune: { w: 160, h: 160, flat: true, draw: (g, w) => {
    const c = w / 2;
    g.strokeStyle = "rgba(118,158,255,0.35)";
    g.lineWidth = 3;
    g.beginPath();
    g.arc(c, c, 70, 0, TAU);
    g.stroke();
    g.beginPath();
    g.arc(c, c, 56, 0, TAU);
    g.stroke();
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * TAU;
      g.beginPath();
      g.moveTo(c + Math.cos(a) * 56, c + Math.sin(a) * 56);
      g.lineTo(c + Math.cos(a + 0.4) * 70, c + Math.sin(a + 0.4) * 70);
      g.stroke();
    }
  } },
  pine: { w: 90, h: 150, draw: (g, w, h) => {
    shadow(g, w / 2, h - 8, 34);
    g.fillStyle = "#5a3a22";
    g.fillRect(w / 2 - 6, h - 34, 12, 26);
    for (let i = 0; i < 4; i++) {
      const y = h - 34 - i * 26, ww = 40 - i * 7;
      g.beginPath();
      g.moveTo(w / 2 - ww, y);
      g.lineTo(w / 2, y - 42);
      g.lineTo(w / 2 + ww, y);
      g.closePath();
      fs(g, i % 2 ? "#2e5a46" : "#356a52");
      g.beginPath();
      g.moveTo(w / 2 - ww * 0.7, y - 6);
      g.lineTo(w / 2, y - 40);
      g.lineTo(w / 2 + ww * 0.5, y - 12);
      g.closePath();
      g.fillStyle = "rgba(240,248,255,0.85)";
      g.fill();
    }
  } },
  icecrystal: { w: 70, h: 90, draw: (g, w, h) => {
    shadow(g, w / 2, h - 6, 24);
    const sp = [[-14, 60, 0.3], [0, 80, 0], [14, 56, -0.3], [-6, 44, 0.5], [9, 40, -0.5]];
    for (const [ox, len, a] of sp) {
      g.save();
      g.translate(w / 2 + ox, h - 10);
      g.rotate(a);
      g.beginPath();
      g.moveTo(-7, 0);
      g.lineTo(-5, -len * 0.8);
      g.lineTo(0, -len);
      g.lineTo(5, -len * 0.8);
      g.lineTo(7, 0);
      g.closePath();
      const gr = g.createLinearGradient(-7, 0, 7, -len);
      gr.addColorStop(0, "#7ab8f0");
      gr.addColorStop(1, "#e8f8ff");
      fs(g, gr, 1.6);
      g.restore();
    }
  } },
  snowrock: { w: 80, h: 60, draw: (g, w, h) => {
    shadow(g, w / 2, h - 6, 34);
    g.beginPath();
    g.ellipse(w / 2, h - 22, 32, 20, 0, 0, TAU);
    fs(g, "#6a7690");
    g.beginPath();
    g.ellipse(w / 2 - 2, h - 32, 26, 10, 0, 0, TAU);
    g.fillStyle = "#f2f8ff";
    g.fill();
  } },
  frozenlake: { w: 260, h: 160, flat: true, draw: (g, w, h) => {
    g.beginPath();
    g.ellipse(w / 2, h / 2, w / 2 - 6, h / 2 - 6, 0, 0, TAU);
    const gr = g.createRadialGradient(w / 2 - 30, h / 2 - 20, 10, w / 2, h / 2, w / 2);
    gr.addColorStop(0, "rgba(220,244,255,0.9)");
    gr.addColorStop(1, "rgba(120,180,230,0.85)");
    g.fillStyle = gr;
    g.fill();
    g.strokeStyle = "rgba(255,255,255,0.9)";
    g.lineWidth = 3;
    g.stroke();
    g.strokeStyle = "rgba(255,255,255,0.6)";
    g.lineWidth = 1.5;
    for (let i = 0; i < 5; i++) {
      g.beginPath();
      g.moveTo(w / 2 - 80 + i * 30, h / 2 - 30 + (i % 2) * 20);
      g.lineTo(w / 2 - 50 + i * 30, h / 2 + (i % 3) * 10);
      g.stroke();
    }
  } },
  tree: { w: 150, h: 170, draw: (g, w, h) => {
    shadow(g, w / 2, h - 10, 52);
    g.beginPath();
    g.moveTo(w / 2 - 10, h - 10);
    g.lineTo(w / 2 - 7, h - 70);
    g.lineTo(w / 2 + 7, h - 70);
    g.lineTo(w / 2 + 10, h - 10);
    g.closePath();
    fs(g, "#6a4426");
    for (const [x, y, r, c] of [[-34, -96, 34, "#2e5a28"], [32, -98, 34, "#2e5a28"], [0, -120, 40, "#3a7032"], [-18, -76, 30, "#3e7a34"], [22, -78, 28, "#346a2e"]] as [number, number, number, string][]) {
      g.beginPath();
      g.arc(w / 2 + x, h + y, r, 0, TAU);
      fs(g, c, 2);
    }
    g.fillStyle = "rgba(180,255,140,0.25)";
    g.beginPath();
    g.arc(w / 2 - 12, h - 132, 16, 0, TAU);
    g.fill();
  } },
  bush: { w: 80, h: 56, draw: (g, w, h) => {
    shadow(g, w / 2, h - 6, 32);
    for (const [x, y, r] of [[-16, -20, 16], [14, -20, 16], [0, -30, 18]]) {
      g.beginPath();
      g.arc(w / 2 + x, h + y, r, 0, TAU);
      fs(g, "#3a7a30", 2);
    }
    g.fillStyle = "#ff6a8a";
    for (const [x, y] of [[-14, -28], [10, -34], [2, -18]]) {
      g.beginPath();
      g.arc(w / 2 + x, h + y, 3, 0, TAU);
      g.fill();
    }
  } },
  pond: { w: 220, h: 140, flat: true, draw: (g, w, h) => {
    g.beginPath();
    g.ellipse(w / 2, h / 2, w / 2 - 6, h / 2 - 6, 0, 0, TAU);
    const gr = g.createRadialGradient(w / 2, h / 2, 10, w / 2, h / 2, w / 2);
    gr.addColorStop(0, "rgba(40,110,120,0.95)");
    gr.addColorStop(1, "rgba(30,80,70,0.9)");
    g.fillStyle = gr;
    g.fill();
    g.strokeStyle = "#5a8a3a";
    g.lineWidth = 6;
    g.stroke();
    g.fillStyle = "#3e8a3a";
    for (const [x, y] of [[-40, -10], [30, 20], [10, -25]]) {
      g.beginPath();
      g.ellipse(w / 2 + x, h / 2 + y, 12, 8, 0, 0.3, TAU);
      g.fill();
    }
  } },
  cactus: { w: 60, h: 100, draw: (g, w, h) => {
    shadow(g, w / 2, h - 6, 22);
    const body = (x: number, y: number, ww: number, hh: number) => {
      g.beginPath();
      g.roundRect(x, y, ww, hh, ww / 2);
      fs(g, "#4e9a4a");
    };
    body(w / 2 - 22, h - 70, 12, 30);
    body(w / 2 + 10, h - 80, 12, 34);
    body(w / 2 - 10, h - 92, 20, 86);
    g.strokeStyle = "rgba(30,70,30,0.6)";
    g.lineWidth = 1.5;
    g.beginPath();
    g.moveTo(w / 2, h - 86);
    g.lineTo(w / 2, h - 10);
    g.stroke();
  } },
  sandrock: { w: 100, h: 70, draw: (g, w, h) => {
    shadow(g, w / 2, h - 6, 42);
    g.beginPath();
    g.moveTo(10, h - 10);
    g.lineTo(18, h - 40);
    g.lineTo(44, h - 56);
    g.lineTo(76, h - 46);
    g.lineTo(92, h - 10);
    g.closePath();
    const gr = g.createLinearGradient(0, h - 56, 0, h);
    gr.addColorStop(0, "#c88a52");
    gr.addColorStop(1, "#8a5a32");
    fs(g, gr);
    g.strokeStyle = "rgba(90,50,20,0.4)";
    g.beginPath();
    g.moveTo(20, h - 32);
    g.lineTo(80, h - 30);
    g.stroke();
  } },
  bones: { w: 70, h: 40, flat: true, draw: (g, w, h) => {
    g.strokeStyle = "#e8dcc8";
    g.lineWidth = 4;
    g.beginPath();
    g.moveTo(10, h - 10);
    g.lineTo(54, 12);
    g.moveTo(16, 10);
    g.lineTo(58, h - 12);
    g.stroke();
    g.fillStyle = "#e8dcc8";
    g.beginPath();
    g.arc(w - 14, h / 2, 9, 0, TAU);
    g.fill();
    g.fillStyle = "#2a1a10";
    g.beginPath();
    g.arc(w - 17, h / 2 - 1, 2.2, 0, TAU);
    g.arc(w - 11, h / 2 - 1, 2.2, 0, TAU);
    g.fill();
  } },
  oasis: { w: 240, h: 150, flat: true, draw: (g, w, h) => {
    g.beginPath();
    g.ellipse(w / 2, h / 2, w / 2 - 8, h / 2 - 8, 0, 0, TAU);
    g.fillStyle = "rgba(90,170,90,0.6)";
    g.fill();
    g.beginPath();
    g.ellipse(w / 2, h / 2, w / 2 - 34, h / 2 - 30, 0, 0, TAU);
    g.fillStyle = "rgba(60,150,200,0.9)";
    g.fill();
    g.strokeStyle = "rgba(220,250,255,0.7)";
    g.lineWidth = 2;
    g.stroke();
  } },
  lavapool: { w: 200, h: 130, flat: true, draw: (g, w, h) => {
    g.beginPath();
    g.ellipse(w / 2, h / 2, w / 2 - 6, h / 2 - 6, 0, 0, TAU);
    const gr = g.createRadialGradient(w / 2, h / 2, 6, w / 2, h / 2, w / 2);
    gr.addColorStop(0, "#ffe08a");
    gr.addColorStop(0.4, "#ff8a2a");
    gr.addColorStop(1, "#a0280e");
    g.fillStyle = gr;
    g.fill();
    g.strokeStyle = "#2a1414";
    g.lineWidth = 7;
    g.stroke();
  } },
  basalt: { w: 70, h: 110, draw: (g, w, h) => {
    shadow(g, w / 2, h - 6, 28);
    for (const [ox, hh] of [[-14, 70], [0, 96], [14, 60]]) {
      g.beginPath();
      g.moveTo(w / 2 + ox - 9, h - 8);
      g.lineTo(w / 2 + ox - 6, h - hh);
      g.lineTo(w / 2 + ox + 6, h - hh - 6);
      g.lineTo(w / 2 + ox + 9, h - 8);
      g.closePath();
      fs(g, "#3a2a2c");
      g.strokeStyle = "rgba(255,120,40,0.75)";
      g.lineWidth = 1.5;
      g.beginPath();
      g.moveTo(w / 2 + ox, h - 14);
      g.lineTo(w / 2 + ox + 2, h - hh * 0.6);
      g.stroke();
    }
  } },
};

const BIOME_DECOS: Record<string, [string, number][]> = {
  stone: [["pillar", 30], ["brazier", 26], ["obelisk", 14], ["rubble", 50], ["rune", 18]],
  frost: [["pine", 60], ["icecrystal", 34], ["snowrock", 30], ["frozenlake", 10]],
  jungle: [["tree", 56], ["bush", 60], ["pond", 12], ["rubble", 20]],
  desert: [["cactus", 48], ["sandrock", 36], ["bones", 30], ["oasis", 8], ["obelisk", 10]],
  hell: [["lavapool", 18], ["basalt", 44], ["bones", 40], ["rubble", 30]],
};

export interface Deco {
  s: Sprite;
  x: number;
  y: number;
  flat: boolean;
}

export function decoTex(name: string) {
  const d = DECOS[name];
  return makeTex("deco|" + name, d.w, d.h, (g) => d.draw(g, d.w, d.h), 1.5);
}

/** Dünyaya dekor dağıtır (oyuncunun başlangıç noktasının çevresi boş kalır). */
export function scatterDecos(biome: string, W: number, H: number, seed: number): Deco[] {
  const rnd = mulberry32(seed);
  const out: Deco[] = [];
  const list = BIOME_DECOS[biome] || BIOME_DECOS.stone;
  const placed: [number, number, number][] = [];
  for (const [name, count] of list) {
    const d = DECOS[name];
    const tex = decoTex(name);
    for (let i = 0; i < count; i++) {
      for (let tries = 0; tries < 12; tries++) {
        const x = 120 + rnd() * (W - 240), y = 120 + rnd() * (H - 240);
        if (Math.hypot(x - W / 2, y - H / 2) < 380) continue;
        const r = Math.max(d.w, d.h * 0.5) * 0.6;
        if (placed.some(([px, py, pr]) => Math.hypot(px - x, py - y) < pr + r)) continue;
        placed.push([x, y, r]);
        const s = new Sprite(tex);
        s.anchor.set(0.5, d.flat ? 0.5 : 0.92);
        s.position.set(x, y);
        const sc = 0.85 + rnd() * 0.35;
        s.scale.set(rnd() < 0.5 ? -sc : sc, sc);
        out.push({ s, x, y, flat: !!d.flat });
        break;
      }
    }
  }
  return out;
}

export function wallTex(biome: string): Texture {
  return makeTex("wall|" + biome, 128, 64, (g) => {
    const col: RGB = biome === "frost" ? [150, 180, 220] : biome === "jungle" ? [70, 110, 60] : biome === "desert" ? [180, 130, 80] : biome === "hell" ? [70, 30, 30] : [80, 88, 128];
    g.fillStyle = rgbCss(darken(col, 0.5));
    g.fillRect(0, 0, 128, 64);
    for (let r = 0; r < 4; r++) {
      for (let c = -1; c < 5; c++) {
        const x = c * 32 + (r % 2) * 16, y = r * 16;
        g.fillStyle = rgbCss(mixCol(darken(col, 0.2), col, ((c * 7 + r * 3) % 5) / 5));
        g.fillRect(x + 1, y + 1, 30, 14);
      }
    }
  }, 1);
}

export function makeFloor(biome: string): TilingSprite {
  const ts = new TilingSprite({ texture: floorTex(biome), width: 100, height: 100 });
  return ts;
}

export { Container };
