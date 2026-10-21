/**
 * Yaratık çizimleri (Canvas2D -> doku). Her yaratık önden/yandan görünen bir
 * çizgi-film gövdesi olarak çizilir; sağa bakar, sola giderken sprite
 * aynalanır. İki kare: 0 = adım / kanat yukarı, 1 = adım / kanat aşağı.
 * Tuval boyutu: 3r x 3r, merkez (1.5r, 1.5r).
 */
import { RGB, rgbCss, lighten, darken, mixCol } from "../core/util";
import { eyes } from "./tex";

type G = CanvasRenderingContext2D;
type DrawFn = (g: G, r: number, c: RGB, f: number) => void;

const OUT = "rgba(14,12,22,0.95)";

function fillStroke(g: G, fill: string | CanvasGradient, lw: number) {
  g.fillStyle = fill;
  g.fill();
  g.strokeStyle = OUT;
  g.lineWidth = lw;
  g.stroke();
}
function shade(g: G, x: number, y: number, r: number, c: RGB, k = 0.38) {
  const gr = g.createRadialGradient(x - r * 0.4, y - r * 0.45, r * 0.05, x, y, r * 1.05);
  gr.addColorStop(0, rgbCss(lighten(c, k)));
  gr.addColorStop(0.55, rgbCss(c));
  gr.addColorStop(1, rgbCss(darken(c, 0.32)));
  return gr;
}
function ellipse(g: G, x: number, y: number, rx: number, ry: number, rot = 0) {
  g.beginPath();
  g.ellipse(x, y, Math.max(0.5, rx), Math.max(0.5, ry), rot, 0, Math.PI * 2);
}
function circle(g: G, x: number, y: number, r: number) {
  g.beginPath();
  g.arc(x, y, Math.max(0.5, r), 0, Math.PI * 2);
}
function legs(g: G, x: number, y: number, r: number, col: string, f: number, n = 2, len = 0.45, w = 0.2) {
  g.lineWidth = r * w;
  g.lineCap = "round";
  for (let i = 0; i < n; i++) {
    const off = (i - (n - 1) / 2) * r * 0.6;
    const ph = (i + f) % 2 ? 1 : -1;
    g.strokeStyle = OUT;
    g.lineWidth = r * w + 2.5;
    g.beginPath();
    g.moveTo(x + off, y);
    g.lineTo(x + off + ph * r * 0.14, y + r * len);
    g.stroke();
    g.strokeStyle = col;
    g.lineWidth = r * w;
    g.beginPath();
    g.moveTo(x + off, y);
    g.lineTo(x + off + ph * r * 0.14, y + r * len);
    g.stroke();
  }
}
function highlight(g: G, x: number, y: number, rx: number, ry: number, a = 0.35) {
  g.fillStyle = `rgba(255,255,255,${a})`;
  ellipse(g, x, y, rx, ry, -0.5);
  g.fill();
}
function mouth(g: G, x: number, y: number, w: number, open: number, teeth = true) {
  g.fillStyle = "#2a0d14";
  ellipse(g, x, y, w, Math.max(1, w * open));
  g.fill();
  if (teeth) {
    g.fillStyle = "#fff6e6";
    const n = 3;
    for (let i = 0; i < n; i++) {
      const tx = x - w * 0.7 + (i * w * 1.4) / (n - 1);
      g.beginPath();
      g.moveTo(tx - w * 0.18, y - w * open * 0.85);
      g.lineTo(tx + w * 0.18, y - w * open * 0.85);
      g.lineTo(tx, y - w * open * 0.2);
      g.closePath();
      g.fill();
    }
  }
}
function wing(g: G, x: number, y: number, r: number, dir: number, up: boolean, col: RGB, membrane = true) {
  const tipY = up ? y - r * 1.15 : y + r * 0.2;
  g.beginPath();
  g.moveTo(x, y - r * 0.15);
  g.quadraticCurveTo(x + dir * r * 0.9, tipY - r * 0.3, x + dir * r * 1.45, tipY);
  if (membrane) {
    g.quadraticCurveTo(x + dir * r * 1.1, tipY + r * 0.35, x + dir * r * 0.95, tipY + r * 0.25);
    g.quadraticCurveTo(x + dir * r * 0.75, tipY + r * 0.6, x + dir * r * 0.5, tipY + r * 0.45);
    g.quadraticCurveTo(x + dir * r * 0.3, y + r * 0.3, x, y + r * 0.2);
  } else {
    g.quadraticCurveTo(x + dir * r * 0.8, y + r * 0.3, x, y + r * 0.2);
  }
  g.closePath();
  const gr = g.createLinearGradient(x, y, x + dir * r * 1.4, tipY);
  gr.addColorStop(0, rgbCss(darken(col, 0.15)));
  gr.addColorStop(1, rgbCss(lighten(col, 0.15)));
  fillStroke(g, gr, 2);
}
function spikesTop(g: G, x: number, y: number, r: number, col: RGB, n = 3, h = 0.35) {
  for (let i = 0; i < n; i++) {
    const a = -Math.PI / 2 + (i - (n - 1) / 2) * 0.55;
    const bx = x + Math.cos(a) * r * 0.85, by = y + Math.sin(a) * r * 0.85;
    const tx = x + Math.cos(a) * r * (1 + h), ty = y + Math.sin(a) * r * (1 + h);
    g.beginPath();
    g.moveTo(bx - Math.sin(a) * r * 0.16, by + Math.cos(a) * r * 0.16);
    g.lineTo(tx, ty);
    g.lineTo(bx + Math.sin(a) * r * 0.16, by - Math.cos(a) * r * 0.16);
    g.closePath();
    fillStroke(g, rgbCss(darken(col, 0.25)), 1.8);
  }
}
function horns(g: G, x: number, y: number, r: number, col = "#efe4d0", curl = 1) {
  for (const s of [-1, 1]) {
    g.beginPath();
    g.moveTo(x + s * r * 0.35, y - r * 0.7);
    g.quadraticCurveTo(x + s * r * 0.95, y - r * 1.05, x + s * r * (0.75 + 0.3 * curl), y - r * 1.5);
    g.quadraticCurveTo(x + s * r * 0.7, y - r * 1.0, x + s * r * 0.12, y - r * 0.82);
    g.closePath();
    fillStroke(g, col, 1.8);
  }
}

// ------------------------------------------------------------------------
// ARENA (TAŞ MEYDAN) YARATIKLARI
// ------------------------------------------------------------------------
const red: DrawFn = (g, r, c, f) => {
  // SÜRÜNGEN: dikenli sırtlı, iri ağızlı yuvarlak yaratık
  const cx = 1.5 * r, cy = 1.5 * r - (f ? r * 0.06 : 0);
  legs(g, cx, cy + r * 0.55, r, rgbCss(darken(c, 0.45)), f, 2, 0.42, 0.24);
  spikesTop(g, cx, cy, r, c, 3, 0.32);
  circle(g, cx, cy, r);
  fillStroke(g, shade(g, cx, cy, r, c), 2.5);
  highlight(g, cx - r * 0.35, cy - r * 0.42, r * 0.28, r * 0.16);
  eyes(g, cx + r * 0.12, cy - r * 0.18, r, { n: 2, spread: 0.3, size: 0.2, angry: true });
  mouth(g, cx + r * 0.15, cy + r * 0.38, r * 0.38, f ? 0.45 : 0.25);
};

const blue: DrawFn = (g, r, c, f) => {
  // YAVRU (yarasa): kanat çırpan küçük gövde
  const cx = 1.5 * r, cy = 1.45 * r;
  const wc = darken(c, 0.25);
  wing(g, cx - r * 0.2, cy, r, -1, f === 0, wc);
  wing(g, cx + r * 0.2, cy, r, 1, f === 0, wc);
  ellipse(g, cx, cy, r * 0.62, r * 0.75);
  fillStroke(g, shade(g, cx, cy, r * 0.7, c), 2.2);
  // kulaklar
  for (const s of [-1, 1]) {
    g.beginPath();
    g.moveTo(cx + s * r * 0.15, cy - r * 0.6);
    g.lineTo(cx + s * r * 0.45, cy - r * 1.05);
    g.lineTo(cx + s * r * 0.5, cy - r * 0.45);
    g.closePath();
    fillStroke(g, rgbCss(c), 1.6);
  }
  eyes(g, cx, cy - r * 0.12, r, { n: 2, spread: 0.26, size: 0.17, col: "#fff2bf", pupil: "#3a1008" });
  g.fillStyle = "#fff";
  for (const s of [-1, 1]) {
    g.beginPath();
    g.moveTo(cx + s * r * 0.12, cy + r * 0.2);
    g.lineTo(cx + s * r * 0.06, cy + r * 0.4);
    g.lineTo(cx + s * r * 0.0, cy + r * 0.2);
    g.fill();
  }
};

const yellow: DrawFn = (g, r, c, f) => {
  // BÜYÜCÜ GÖZ: çevresinde kristaller dönen baklava gövde, tek dev göz
  const cx = 1.5 * r, cy = 1.5 * r;
  for (let i = 0; i < 3; i++) {
    const a = i * 2.094 + (f ? 0.5 : 0);
    const ox = cx + Math.cos(a) * r * 1.22, oy = cy + Math.sin(a) * r * 1.22;
    g.beginPath();
    g.moveTo(ox, oy - 5);
    g.lineTo(ox + 4, oy);
    g.lineTo(ox, oy + 5);
    g.lineTo(ox - 4, oy);
    g.closePath();
    fillStroke(g, rgbCss(lighten(c, 0.3)), 1.4);
  }
  g.beginPath();
  g.moveTo(cx, cy - r);
  g.lineTo(cx + r * 0.95, cy);
  g.lineTo(cx, cy + r);
  g.lineTo(cx - r * 0.95, cy);
  g.closePath();
  fillStroke(g, shade(g, cx, cy, r, c), 2.5);
  g.beginPath();
  g.moveTo(cx, cy - r * 0.6);
  g.lineTo(cx + r * 0.5, cy);
  g.lineTo(cx, cy);
  g.closePath();
  g.fillStyle = "rgba(255,255,255,0.25)";
  g.fill();
  eyes(g, cx, cy, r, { n: 1, size: 0.34, col: "#fffbe2", glow: "rgba(255,230,120,1)" });
};

const tank: DrawFn = (g, r, c, f) => {
  // ZIRHLI YÜRÜYÜŞÇÜ: plakalı kutu gövde, vizör
  const cx = 1.5 * r, cy = 1.45 * r;
  legs(g, cx, cy + r * 0.7, r, "#463c5c", f, 2, 0.32, 0.3);
  const w = r * 1.8, h = r * 1.65;
  g.beginPath();
  g.roundRect(cx - w / 2, cy - h / 2, w, h, r * 0.3);
  fillStroke(g, shade(g, cx, cy, r, c), 3);
  // omuz plakaları
  for (const s of [-1, 1]) {
    g.beginPath();
    g.roundRect(cx + s * r * 0.95 - r * 0.28, cy - r * 0.75, r * 0.56, r * 0.7, r * 0.15);
    fillStroke(g, rgbCss(darken(c, 0.2)), 2);
  }
  g.beginPath();
  g.roundRect(cx - w * 0.3, cy - h * 0.12, w * 0.6, h * 0.5, r * 0.12);
  g.fillStyle = rgbCss(lighten(c, 0.2));
  g.fill();
  // perçinler
  g.fillStyle = rgbCss(darken(c, 0.4));
  for (const [px, py] of [[-0.62, -0.55], [0.62, -0.55], [-0.62, 0.6], [0.62, 0.6]]) {
    circle(g, cx + px * r, cy + py * r, r * 0.09);
    g.fill();
  }
  // vizör
  g.beginPath();
  g.roundRect(cx - r * 0.6, cy - r * 0.42, r * 1.2, r * 0.3, r * 0.15);
  g.fillStyle = "#16141e";
  g.fill();
  g.fillStyle = "#ff6a6a";
  g.shadowColor = "#ff4040";
  g.shadowBlur = 6;
  circle(g, cx - r * 0.25, cy - r * 0.27, r * 0.09);
  g.fill();
  circle(g, cx + r * 0.25, cy - r * 0.27, r * 0.09);
  g.fill();
  g.shadowBlur = 0;
};

const sprinter: DrawFn = (g, r, c, f) => {
  // AV KÖPEĞİ: uzun gövde, kuyruk, sivri kulak
  const cx = 1.45 * r, cy = 1.55 * r;
  // bacaklar
  g.lineCap = "round";
  for (const [lx, ph] of [[-0.55, 0], [-0.25, 1], [0.35, 1], [0.62, 0]]) {
    const sw = (ph + f) % 2 ? 0.18 : -0.18;
    g.strokeStyle = OUT;
    g.lineWidth = r * 0.22 + 2.5;
    g.beginPath();
    g.moveTo(cx + lx * r, cy + r * 0.2);
    g.lineTo(cx + (lx + sw) * r, cy + r * 0.75);
    g.stroke();
    g.strokeStyle = rgbCss(darken(c, 0.35));
    g.lineWidth = r * 0.22;
    g.stroke();
  }
  // kuyruk
  g.beginPath();
  g.moveTo(cx - r * 0.8, cy - r * 0.05);
  g.quadraticCurveTo(cx - r * 1.3, cy - r * (f ? 0.7 : 0.45), cx - r * 1.35, cy - r * (f ? 0.95 : 0.75));
  g.strokeStyle = OUT;
  g.lineWidth = r * 0.24 + 2;
  g.stroke();
  g.strokeStyle = rgbCss(c);
  g.lineWidth = r * 0.24;
  g.stroke();
  ellipse(g, cx, cy, r * 0.95, r * 0.5);
  fillStroke(g, shade(g, cx, cy, r * 0.8, c), 2.4);
  // kafa
  const hx = cx + r * 0.85, hy = cy - r * 0.35;
  ellipse(g, hx, hy, r * 0.52, r * 0.45);
  fillStroke(g, shade(g, hx, hy, r * 0.5, c), 2.2);
  for (const s of [0, 1]) {
    g.beginPath();
    g.moveTo(hx - r * 0.25 + s * r * 0.22, hy - r * 0.3);
    g.lineTo(hx - r * 0.18 + s * r * 0.22, hy - r * 0.85);
    g.lineTo(hx + r * 0.05 + s * r * 0.22, hy - r * 0.35);
    g.closePath();
    fillStroke(g, rgbCss(darken(c, 0.1)), 1.6);
  }
  ellipse(g, hx + r * 0.45, hy + r * 0.1, r * 0.28, r * 0.2);
  fillStroke(g, rgbCss(lighten(c, 0.15)), 1.8);
  eyes(g, hx + r * 0.1, hy - r * 0.08, r, { n: 1, size: 0.15, col: "#ffeaa0", pupil: "#300", angry: true });
  g.fillStyle = "#1a1018";
  circle(g, hx + r * 0.72, hy + r * 0.05, r * 0.07);
  g.fill();
};

const brute: DrawFn = (g, r, c, f) => {
  // KABA: geniş omuzlu, iri yumruklu, boynuzlu dev
  const cx = 1.5 * r, cy = 1.5 * r;
  legs(g, cx, cy + r * 0.55, r, rgbCss(darken(c, 0.45)), f, 2, 0.4, 0.32);
  horns(g, cx, cy + r * 0.05, r * 0.9);
  // gövde
  g.beginPath();
  g.moveTo(cx - r * 0.95, cy - r * 0.35);
  g.quadraticCurveTo(cx, cy - r * 1.05, cx + r * 0.95, cy - r * 0.35);
  g.quadraticCurveTo(cx + r * 0.85, cy + r * 0.75, cx, cy + r * 0.8);
  g.quadraticCurveTo(cx - r * 0.85, cy + r * 0.75, cx - r * 0.95, cy - r * 0.35);
  g.closePath();
  fillStroke(g, shade(g, cx, cy, r, c), 2.8);
  // yumruklar
  for (const s of [-1, 1]) {
    circle(g, cx + s * r * 1.05, cy + r * (f && s > 0 ? 0.15 : 0.35), r * 0.36);
    fillStroke(g, shade(g, cx + s * r, cy + r * 0.3, r * 0.36, darken(c, 0.1)), 2.2);
  }
  highlight(g, cx - r * 0.35, cy - r * 0.35, r * 0.3, r * 0.14);
  eyes(g, cx, cy - r * 0.15, r, { n: 2, spread: 0.3, size: 0.15, col: "#ffd7a0", pupil: "#3a0a00", angry: true });
  mouth(g, cx, cy + r * 0.32, r * 0.35, f ? 0.3 : 0.18);
};

const elite: DrawFn = (g, r, c, f) => {
  // ELİT: taçlı, pelerinli şampiyon
  const cx = 1.5 * r, cy = 1.55 * r;
  // pelerin
  g.beginPath();
  g.moveTo(cx - r * 0.7, cy - r * 0.4);
  g.lineTo(cx - r * (f ? 1.05 : 0.95), cy + r * 0.95);
  g.lineTo(cx + r * (f ? 0.95 : 1.05), cy + r * 0.95);
  g.lineTo(cx + r * 0.7, cy - r * 0.4);
  g.closePath();
  fillStroke(g, "#5a1f2e", 2.2);
  circle(g, cx, cy, r * 0.85);
  fillStroke(g, shade(g, cx, cy, r * 0.85, c), 3);
  // taç
  g.beginPath();
  const ty = cy - r * 0.75;
  g.moveTo(cx - r * 0.55, ty + r * 0.15);
  g.lineTo(cx - r * 0.6, ty - r * 0.4);
  g.lineTo(cx - r * 0.3, ty - r * 0.15);
  g.lineTo(cx, ty - r * 0.55);
  g.lineTo(cx + r * 0.3, ty - r * 0.15);
  g.lineTo(cx + r * 0.6, ty - r * 0.4);
  g.lineTo(cx + r * 0.55, ty + r * 0.15);
  g.closePath();
  fillStroke(g, "#ffd25a", 2);
  g.fillStyle = "#e0325a";
  circle(g, cx, ty - r * 0.1, r * 0.09);
  g.fill();
  eyes(g, cx, cy - r * 0.05, r * 0.85, { n: 2, spread: 0.32, size: 0.2, angry: true, glow: "rgba(255,200,80,1)" });
  mouth(g, cx, cy + r * 0.38, r * 0.28, 0.25);
};

const kamikaze: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.55 * r;
  legs(g, cx, cy + r * 0.6, r, "#46322e", f, 2, 0.35, 0.22);
  circle(g, cx, cy, r);
  fillStroke(g, shade(g, cx, cy, r, [58, 44, 44]), 2.6);
  g.strokeStyle = "#ff7a32";
  g.lineWidth = 2.2;
  g.shadowColor = "#ff5a20";
  g.shadowBlur = 6;
  for (let k = 0; k < 3; k++) {
    const a = k * 2.1 + 0.4;
    g.beginPath();
    g.moveTo(cx + Math.cos(a) * r * 0.12, cy + Math.sin(a) * r * 0.12);
    g.lineTo(cx + Math.cos(a + 0.35) * r * 0.55, cy + Math.sin(a + 0.35) * r * 0.55);
    g.lineTo(cx + Math.cos(a - 0.1) * r * 0.92, cy + Math.sin(a - 0.1) * r * 0.92);
    g.stroke();
  }
  g.shadowBlur = 0;
  // fitil
  g.strokeStyle = "#d6b882";
  g.lineWidth = 2.5;
  g.beginPath();
  g.moveTo(cx + r * 0.2, cy - r * 0.95);
  g.quadraticCurveTo(cx + r * 0.5, cy - r * 1.3, cx + r * 0.35, cy - r * 1.45);
  g.stroke();
  g.fillStyle = f ? "#fff2a0" : "#ff9a3a";
  circle(g, cx + r * 0.35, cy - r * 1.45, r * 0.13);
  g.fill();
  eyes(g, cx, cy - r * 0.05, r, { n: 2, spread: 0.3, size: 0.18, col: "#ffe678", pupil: "#3a0a00", angry: true });
};

const healer: DrawFn = (g, r, c, f) => {
  // ŞİFACI: yapraklı, haleli yumuşak ruh
  const cx = 1.5 * r, cy = 1.5 * r;
  g.strokeStyle = "rgba(160,255,190,0.8)";
  g.lineWidth = 2.4;
  ellipse(g, cx, cy - r * 1.05, r * 0.5, r * 0.15);
  g.stroke();
  for (const s of [-1, 1]) {
    g.beginPath();
    g.ellipse(cx + s * r * 0.8, cy - r * 0.1 + (f ? -2 : 2), r * 0.5, r * 0.22, s * 0.6, 0, Math.PI * 2);
    fillStroke(g, rgbCss(darken(c, 0.15)), 1.8);
  }
  g.beginPath();
  g.moveTo(cx, cy - r * 0.95);
  g.quadraticCurveTo(cx + r * 0.95, cy - r * 0.5, cx + r * 0.7, cy + r * 0.85);
  g.quadraticCurveTo(cx, cy + r * 0.6, cx - r * 0.7, cy + r * 0.85);
  g.quadraticCurveTo(cx - r * 0.95, cy - r * 0.5, cx, cy - r * 0.95);
  fillStroke(g, shade(g, cx, cy, r, c), 2.4);
  g.fillStyle = "#fff";
  g.fillRect(cx - r * 0.08, cy + r * 0.05, r * 0.16, r * 0.5);
  g.fillRect(cx - r * 0.25, cy + r * 0.22, r * 0.5, r * 0.16);
  eyes(g, cx, cy - r * 0.3, r, { n: 2, spread: 0.26, size: 0.15 });
};

const wizard: DrawFn = (g, r, c, f) => {
  // BÜYÜCÜ: sivri şapkalı, asalı cüce
  const cx = 1.45 * r, cy = 1.6 * r;
  // asa
  g.strokeStyle = "#5a3a22";
  g.lineWidth = r * 0.14;
  g.beginPath();
  g.moveTo(cx + r * 0.8, cy + r * 0.8);
  g.lineTo(cx + r * 0.95, cy - r * 0.9);
  g.stroke();
  g.fillStyle = "#a6f07a";
  g.shadowColor = "#7cff5a";
  g.shadowBlur = f ? 10 : 5;
  circle(g, cx + r * 0.97, cy - r * 1.0, r * 0.2);
  g.fill();
  g.shadowBlur = 0;
  // cüppe
  g.beginPath();
  g.moveTo(cx - r * 0.75, cy + r * 0.85);
  g.quadraticCurveTo(cx - r * 0.65, cy - r * 0.3, cx, cy - r * 0.45);
  g.quadraticCurveTo(cx + r * 0.65, cy - r * 0.3, cx + r * 0.75, cy + r * 0.85);
  g.closePath();
  fillStroke(g, shade(g, cx, cy, r, c), 2.4);
  // şapka
  g.beginPath();
  g.moveTo(cx - r * 0.7, cy - r * 0.35);
  g.lineTo(cx + r * 0.1, cy - r * 1.55);
  g.lineTo(cx + r * 0.7, cy - r * 0.35);
  g.closePath();
  fillStroke(g, rgbCss(darken(c, 0.35)), 2.2);
  ellipse(g, cx, cy - r * 0.35, r * 0.85, r * 0.16);
  fillStroke(g, rgbCss(darken(c, 0.45)), 2);
  eyes(g, cx, cy - r * 0.1, r, { n: 2, spread: 0.24, size: 0.13, col: "#e0ffb0", pupil: "#0a2a00", glow: "rgba(150,255,120,1)" });
};

const stinger: DrawFn = (g, r, c, f) => {
  // ARI: çizgili gövde, iğne, hızlı kanat
  const cx = 1.45 * r, cy = 1.5 * r;
  for (const s of [-1, 1]) {
    ellipse(g, cx - r * 0.1 + s * r * 0.15, cy - r * (f ? 0.75 : 0.55), r * 0.5, r * 0.25, s * (f ? 0.5 : 0.2));
    g.fillStyle = "rgba(220,240,255,0.65)";
    g.fill();
    g.strokeStyle = "rgba(20,20,30,0.8)";
    g.lineWidth = 1.4;
    g.stroke();
  }
  // iğne
  g.beginPath();
  g.moveTo(cx - r * 0.95, cy + r * 0.1);
  g.lineTo(cx - r * 1.35, cy + r * 0.25);
  g.lineTo(cx - r * 0.9, cy + r * 0.3);
  g.closePath();
  fillStroke(g, "#2a2230", 1.5);
  ellipse(g, cx - r * 0.25, cy + r * 0.15, r * 0.75, r * 0.5);
  fillStroke(g, shade(g, cx, cy, r * 0.7, c), 2.2);
  g.fillStyle = "#231c24";
  for (let i = 0; i < 2; i++) {
    g.fillRect(cx - r * 0.55 + i * r * 0.45, cy - r * 0.3, r * 0.17, r * 0.9);
  }
  circle(g, cx + r * 0.55, cy - r * 0.05, r * 0.42);
  fillStroke(g, shade(g, cx + r * 0.5, cy, r * 0.4, c), 2);
  eyes(g, cx + r * 0.65, cy - r * 0.12, r * 0.6, { n: 2, spread: 0.35, size: 0.28, col: "#ff4040", pupil: "#200" });
};

const herald: DrawFn = (g, r, c, f) => {
  // SANCAKTAR: sırtında sandık + sancak
  const cx = 1.5 * r, cy = 1.55 * r;
  // sancak direği
  g.strokeStyle = "#6a4a2a";
  g.lineWidth = r * 0.1;
  g.beginPath();
  g.moveTo(cx - r * 0.55, cy + r * 0.4);
  g.lineTo(cx - r * 0.55, cy - r * 1.4);
  g.stroke();
  g.beginPath();
  g.moveTo(cx - r * 0.55, cy - r * 1.4);
  g.lineTo(cx + r * (f ? 0.45 : 0.4), cy - r * 1.22);
  g.lineTo(cx - r * 0.55, cy - r * 0.95);
  g.closePath();
  fillStroke(g, "#e04848", 1.6);
  // sandık
  g.beginPath();
  g.roundRect(cx - r * 0.4, cy - r * 1.05, r * 0.95, r * 0.6, r * 0.1);
  fillStroke(g, "#8a5a2a", 2);
  g.fillStyle = "#ffd25a";
  g.fillRect(cx - r * 0.4, cy - r * 0.82, r * 0.95, r * 0.1);
  circle(g, cx, cy + r * 0.05, r * 0.82);
  fillStroke(g, shade(g, cx, cy, r * 0.82, c), 2.6);
  legs(g, cx, cy + r * 0.7, r, rgbCss(darken(c, 0.4)), f, 2, 0.3, 0.22);
  eyes(g, cx + r * 0.1, cy, r * 0.82, { n: 2, spread: 0.3, size: 0.18 });
};

const shieldman: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.5 * r;
  legs(g, cx, cy + r * 0.55, r, "#3a4458", f, 2, 0.38, 0.25);
  circle(g, cx - r * 0.2, cy, r * 0.75);
  fillStroke(g, shade(g, cx, cy, r * 0.75, [110, 118, 140]), 2.4);
  // kask
  g.beginPath();
  g.arc(cx - r * 0.2, cy - r * 0.15, r * 0.72, Math.PI, 0);
  g.closePath();
  fillStroke(g, "#8a94aa", 2);
  g.fillStyle = "#14141c";
  g.fillRect(cx - r * 0.55, cy - r * 0.25, r * 0.7, r * 0.14);
  // büyük kalkan
  g.beginPath();
  g.moveTo(cx + r * 0.25, cy - r * 0.95);
  g.lineTo(cx + r * 1.05, cy - r * 0.8);
  g.quadraticCurveTo(cx + r * 1.15, cy + r * 0.5, cx + r * 0.65, cy + r * 1.05);
  g.quadraticCurveTo(cx + r * 0.25, cy + r * 0.5, cx + r * 0.25, cy - r * 0.95);
  g.closePath();
  fillStroke(g, shade(g, cx + r * 0.65, cy, r * 0.8, c), 2.6);
  g.strokeStyle = "#e2ba62";
  g.lineWidth = 2;
  g.beginPath();
  g.moveTo(cx + r * 0.65, cy - r * 0.75);
  g.lineTo(cx + r * 0.65, cy + r * 0.8);
  g.stroke();
};

const goblin: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.55 * r;
  // çuval
  ellipse(g, cx - r * 0.65, cy - r * 0.1, r * 0.55, r * 0.6);
  fillStroke(g, "#a07a46", 2);
  g.fillStyle = "#ffd25a";
  g.font = `bold ${r * 0.6}px sans-serif`;
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.fillText("$", cx - r * 0.65, cy - r * 0.05);
  legs(g, cx, cy + r * 0.55, r, rgbCss(darken(c, 0.4)), f, 2, 0.4, 0.2);
  circle(g, cx + r * 0.1, cy, r * 0.7);
  fillStroke(g, shade(g, cx, cy, r * 0.7, c), 2.4);
  for (const s of [-1, 1]) {
    g.beginPath();
    g.moveTo(cx + r * 0.1 + s * r * 0.5, cy - r * 0.25);
    g.lineTo(cx + r * 0.1 + s * r * 1.15, cy - r * 0.6);
    g.lineTo(cx + r * 0.1 + s * r * 0.55, cy + r * 0.05);
    g.closePath();
    fillStroke(g, rgbCss(c), 1.8);
  }
  eyes(g, cx + r * 0.15, cy - r * 0.1, r * 0.7, { n: 2, spread: 0.3, size: 0.2, col: "#fff59a" });
  g.strokeStyle = "#2a1010";
  g.lineWidth = 2;
  g.beginPath();
  g.arc(cx + r * 0.15, cy + r * 0.2, r * 0.25, 0.2, Math.PI - 0.2);
  g.stroke();
};

const splitter: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.55 * r;
  g.beginPath();
  g.moveTo(cx - r, cy + r * 0.6);
  g.quadraticCurveTo(cx - r * 1.05, cy - r * (f ? 0.9 : 0.8), cx, cy - r * 0.95);
  g.quadraticCurveTo(cx + r * 1.05, cy - r * (f ? 0.8 : 0.9), cx + r, cy + r * 0.6);
  g.quadraticCurveTo(cx, cy + r * 0.9, cx - r, cy + r * 0.6);
  fillStroke(g, shade(g, cx, cy, r, c), 2.6);
  g.strokeStyle = rgbCss(darken(c, 0.45));
  g.lineWidth = 2.2;
  g.beginPath();
  g.moveTo(cx, cy - r * 0.9);
  g.lineTo(cx + r * 0.1, cy - r * 0.4);
  g.lineTo(cx - r * 0.08, cy);
  g.lineTo(cx + r * 0.05, cy + r * 0.5);
  g.stroke();
  highlight(g, cx - r * 0.45, cy - r * 0.4, r * 0.25, r * 0.12, 0.45);
  eyes(g, cx - r * 0.35, cy - r * 0.15, r, { n: 1, size: 0.18 });
  eyes(g, cx + r * 0.38, cy - r * 0.15, r, { n: 1, size: 0.18 });
};

const necro: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.55 * r;
  g.beginPath();
  g.moveTo(cx - r * 0.85, cy + r * 0.85);
  g.lineTo(cx - r * 0.6, cy - r * 0.55);
  g.quadraticCurveTo(cx, cy - r * 1.35, cx + r * 0.6, cy - r * 0.55);
  g.lineTo(cx + r * 0.85, cy + r * 0.85);
  g.closePath();
  fillStroke(g, "#2a2236", 2.4);
  ellipse(g, cx, cy - r * 0.35, r * 0.45, r * 0.42);
  fillStroke(g, "#d8d4c6", 2);
  g.fillStyle = rgbCss(c);
  g.shadowColor = rgbCss(c);
  g.shadowBlur = 8;
  circle(g, cx - r * 0.16, cy - r * 0.38, r * 0.1);
  g.fill();
  circle(g, cx + r * 0.16, cy - r * 0.38, r * 0.1);
  g.fill();
  circle(g, cx + r * 0.95, cy - r * (f ? 0.2 : 0.3), r * 0.22);
  g.fill();
  g.shadowBlur = 0;
};

const ghost: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.45 * r;
  g.beginPath();
  g.moveTo(cx - r * 0.85, cy + r * 0.9);
  g.lineTo(cx - r * 0.85, cy - r * 0.1);
  g.arc(cx, cy - r * 0.1, r * 0.85, Math.PI, 0);
  g.lineTo(cx + r * 0.85, cy + r * 0.9);
  for (let i = 0; i < 4; i++) {
    const x0 = cx + r * 0.85 - (i + 0.5) * (r * 1.7) / 4;
    g.quadraticCurveTo(x0 + r * 0.2, cy + r * (f ? 0.6 : 0.75), x0 - r * 0.21, cy + r * 0.9);
  }
  g.closePath();
  g.globalAlpha = 0.85;
  fillStroke(g, shade(g, cx, cy, r, c), 2.2);
  g.globalAlpha = 1;
  g.fillStyle = "#1c1c34";
  ellipse(g, cx - r * 0.3, cy - r * 0.15, r * 0.14, r * 0.22);
  g.fill();
  ellipse(g, cx + r * 0.3, cy - r * 0.15, r * 0.14, r * 0.22);
  g.fill();
  ellipse(g, cx, cy + r * 0.3, r * 0.16, r * 0.2);
  g.fill();
};

// ------------------------------------------------------------------------
// CEHENNEM
// ------------------------------------------------------------------------
const imp: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.5 * r;
  wing(g, cx - r * 0.2, cy - r * 0.1, r * 0.85, -1, f === 0, [120, 30, 30]);
  wing(g, cx + r * 0.2, cy - r * 0.1, r * 0.85, 1, f === 0, [120, 30, 30]);
  horns(g, cx, cy + r * 0.1, r * 0.7, "#2a1414");
  circle(g, cx, cy, r * 0.7);
  fillStroke(g, shade(g, cx, cy, r * 0.7, c), 2.4);
  eyes(g, cx, cy - r * 0.1, r * 0.7, { n: 2, spread: 0.3, size: 0.2, col: "#ffef7a", pupil: "#400", angry: true });
  mouth(g, cx, cy + r * 0.28, r * 0.25, 0.3);
  // kuyruk
  g.strokeStyle = OUT;
  g.lineWidth = 3;
  g.beginPath();
  g.moveTo(cx, cy + r * 0.65);
  g.quadraticCurveTo(cx - r * 0.6, cy + r * 1.1, cx - r * 0.9, cy + r * 0.8);
  g.stroke();
};
const hound: DrawFn = (g, r, c, f) => {
  sprinter(g, r, c, f);
  // alevli sırt
  g.fillStyle = "rgba(255,170,60,0.9)";
  g.shadowColor = "#ff6a10";
  g.shadowBlur = 8;
  for (let i = 0; i < 4; i++) {
    const x = 1.45 * r - r * 0.6 + i * r * 0.35, y = 1.55 * r - r * 0.45;
    g.beginPath();
    g.moveTo(x - r * 0.12, y);
    g.quadraticCurveTo(x, y - r * (0.5 + (i + f) % 2 * 0.2), x + r * 0.12, y);
    g.fill();
  }
  g.shadowBlur = 0;
};
const reaver: DrawFn = (g, r, c, f) => {
  red(g, r, c, f);
  horns(g, 1.5 * r, 1.5 * r + r * 0.15, r * 0.85, "#1e1012");
};
const seer: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.5 * r;
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2 + (f ? 0.3 : 0);
    g.strokeStyle = rgbCss(darken(c, 0.4));
    g.lineWidth = r * 0.16;
    g.beginPath();
    g.moveTo(cx, cy);
    g.quadraticCurveTo(cx + Math.cos(a + 0.4) * r * 0.9, cy + Math.sin(a + 0.4) * r * 0.9, cx + Math.cos(a) * r * 1.3, cy + Math.sin(a) * r * 1.3);
    g.stroke();
  }
  circle(g, cx, cy, r * 0.85);
  fillStroke(g, shade(g, cx, cy, r * 0.85, c), 2.6);
  g.fillStyle = "#2a0c08";
  ellipse(g, cx, cy, r * 0.55, r * 0.35);
  g.fill();
  eyes(g, cx, cy, r * 0.85, { n: 1, size: 0.3, col: "#ffefb0", pupil: "#b00", glow: "rgba(255,120,40,1)" });
};
const golem: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.5 * r;
  legs(g, cx, cy + r * 0.6, r, "#2a1a16", f, 2, 0.35, 0.36);
  const pts = [[-0.9, -0.4], [-0.5, -0.95], [0.4, -0.9], [0.95, -0.3], [0.85, 0.6], [0.2, 0.85], [-0.7, 0.7]];
  g.beginPath();
  pts.forEach(([x, y], i) => (i ? g.lineTo(cx + x * r, cy + y * r) : g.moveTo(cx + x * r, cy + y * r)));
  g.closePath();
  fillStroke(g, shade(g, cx, cy, r, c), 3);
  g.strokeStyle = "#ffae42";
  g.shadowColor = "#ff6a00";
  g.shadowBlur = 8;
  g.lineWidth = 2.4;
  g.beginPath();
  g.moveTo(cx - r * 0.5, cy - r * 0.5);
  g.lineTo(cx - r * 0.1, cy - r * 0.1);
  g.lineTo(cx + r * 0.4, cy - r * 0.2);
  g.moveTo(cx - r * 0.1, cy - r * 0.1);
  g.lineTo(cx, cy + r * 0.55);
  g.stroke();
  g.shadowBlur = 0;
  eyes(g, cx, cy - r * 0.35, r, { n: 2, spread: 0.3, size: 0.13, col: "#ffcf5a", pupil: "#ff6a00", glow: "rgba(255,140,40,1)" });
};
const butcher: DrawFn = (g, r, c, f) => {
  brute(g, r, c, f);
  const cx = 1.5 * r, cy = 1.5 * r;
  // satır
  g.save();
  g.translate(cx + r * 1.05, cy + r * 0.1);
  g.rotate(f ? -0.5 : -0.2);
  g.beginPath();
  g.roundRect(-r * 0.08, -r * 1.0, r * 0.16, r * 0.6, 2);
  fillStroke(g, "#5a3a22", 1.6);
  g.beginPath();
  g.roundRect(-r * 0.05, -r * 1.55, r * 0.6, r * 0.6, 3);
  fillStroke(g, "#c8ccd6", 1.8);
  g.restore();
};
const warden: DrawFn = (g, r, c, f) => {
  elite(g, r, c, f);
  const cx = 1.5 * r, cy = 1.55 * r;
  g.strokeStyle = "rgba(255,120,40,0.85)";
  g.shadowColor = "#ff4a00";
  g.shadowBlur = 10;
  g.lineWidth = 2.5;
  circle(g, cx, cy, r * 1.05);
  g.stroke();
  g.shadowBlur = 0;
};

// ------------------------------------------------------------------------
// BUZUL VADİSİ
// ------------------------------------------------------------------------
const f_beetle: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.55 * r;
  for (let i = 0; i < 3; i++) {
    const ly = cy - r * 0.2 + i * r * 0.35;
    for (const s of [-1, 1]) {
      g.strokeStyle = OUT;
      g.lineWidth = 2.6;
      g.beginPath();
      g.moveTo(cx + s * r * 0.6, ly);
      g.lineTo(cx + s * r * 1.1, ly + ((i + f) % 2 ? -r * 0.15 : r * 0.15));
      g.stroke();
    }
  }
  ellipse(g, cx, cy, r * 0.85, r * 0.9);
  fillStroke(g, shade(g, cx, cy, r, c), 2.6);
  g.strokeStyle = rgbCss(darken(c, 0.4));
  g.lineWidth = 2;
  g.beginPath();
  g.moveTo(cx, cy - r * 0.55);
  g.lineTo(cx, cy + r * 0.85);
  g.stroke();
  // buz kristalleri
  g.fillStyle = "rgba(235,250,255,0.9)";
  for (const [x, y] of [[-0.4, 0.1], [0.4, 0.3], [-0.25, 0.5]]) {
    g.beginPath();
    g.moveTo(cx + x * r, cy + y * r - r * 0.18);
    g.lineTo(cx + x * r + r * 0.1, cy + y * r);
    g.lineTo(cx + x * r, cy + y * r + r * 0.18);
    g.lineTo(cx + x * r - r * 0.1, cy + y * r);
    g.fill();
  }
  circle(g, cx, cy - r * 0.75, r * 0.4);
  fillStroke(g, shade(g, cx, cy - r * 0.75, r * 0.4, darken(c, 0.2)), 2);
  eyes(g, cx, cy - r * 0.78, r * 0.5, { n: 2, spread: 0.45, size: 0.25, col: "#dff6ff", pupil: "#0a2a44" });
};
const f_bat: DrawFn = (g, r, c, f) => {
  blue(g, r, c, f);
  g.fillStyle = "rgba(240,252,255,0.85)";
  const cx = 1.5 * r, cy = 1.45 * r;
  for (const s of [-1, 1]) {
    g.beginPath();
    g.moveTo(cx + s * r * 0.5, cy + r * 0.2);
    g.lineTo(cx + s * r * 0.58, cy + r * 0.5);
    g.lineTo(cx + s * r * 0.66, cy + r * 0.2);
    g.fill();
  }
};
const f_wisp: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.45 * r;
  g.globalAlpha = 0.35;
  circle(g, cx, cy, r * 1.15);
  g.fillStyle = rgbCss(c);
  g.fill();
  g.globalAlpha = 1;
  g.beginPath();
  g.moveTo(cx, cy - r * 1.0);
  g.bezierCurveTo(cx + r * 1.1, cy - r * 0.6, cx + r * 0.7, cy + r * 0.6, cx + r * 0.2, cy + r * (f ? 1.05 : 0.9));
  g.quadraticCurveTo(cx, cy + r * 0.6, cx - r * 0.25, cy + r * (f ? 0.9 : 1.05));
  g.bezierCurveTo(cx - r * 0.7, cy + r * 0.6, cx - r * 1.1, cy - r * 0.6, cx, cy - r * 1.0);
  fillStroke(g, shade(g, cx, cy, r, c, 0.5), 2.2);
  eyes(g, cx, cy - r * 0.2, r, { n: 2, spread: 0.3, size: 0.16, col: "#ffffff", pupil: "#1a3a5a" });
};
const f_golem: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.5 * r;
  legs(g, cx, cy + r * 0.6, r, rgbCss(darken(c, 0.5)), f, 2, 0.35, 0.36);
  const pts = [[-0.85, -0.3], [-0.45, -1.0], [0.1, -0.75], [0.55, -1.05], [0.95, -0.25], [0.8, 0.7], [-0.75, 0.7]];
  g.beginPath();
  pts.forEach(([x, y], i) => (i ? g.lineTo(cx + x * r, cy + y * r) : g.moveTo(cx + x * r, cy + y * r)));
  g.closePath();
  fillStroke(g, shade(g, cx, cy, r, c, 0.5), 3);
  g.strokeStyle = "rgba(255,255,255,0.6)";
  g.lineWidth = 1.6;
  g.beginPath();
  g.moveTo(cx - r * 0.4, cy - r * 0.6);
  g.lineTo(cx - r * 0.1, cy);
  g.moveTo(cx + r * 0.35, cy - r * 0.6);
  g.lineTo(cx + r * 0.5, cy + r * 0.2);
  g.stroke();
  eyes(g, cx, cy - r * 0.2, r, { n: 2, spread: 0.32, size: 0.13, col: "#bff4ff", pupil: "#2aa0ff", glow: "rgba(120,220,255,1)" });
};
const f_wolf: DrawFn = (g, r, c, f) => {
  sprinter(g, r, c, f);
};
const f_yeti: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.5 * r;
  legs(g, cx, cy + r * 0.6, r, rgbCss(darken(c, 0.35)), f, 2, 0.38, 0.34);
  g.beginPath();
  for (let i = 0; i <= 16; i++) {
    const a = (i / 16) * Math.PI * 2;
    const rr = r * (0.95 + (i % 2 ? 0.08 : 0));
    const x = cx + Math.cos(a) * rr, y = cy + Math.sin(a) * rr * 0.95;
    i ? g.lineTo(x, y) : g.moveTo(x, y);
  }
  g.closePath();
  fillStroke(g, shade(g, cx, cy, r, c, 0.2), 2.8);
  for (const s of [-1, 1]) {
    circle(g, cx + s * r * 1.0, cy + r * (f && s > 0 ? 0.05 : 0.3), r * 0.34);
    fillStroke(g, rgbCss(c), 2);
  }
  ellipse(g, cx, cy - r * 0.15, r * 0.55, r * 0.45);
  g.fillStyle = "#8aa0c0";
  g.fill();
  eyes(g, cx, cy - r * 0.25, r, { n: 2, spread: 0.28, size: 0.14, angry: true });
  mouth(g, cx, cy + r * 0.08, r * 0.28, f ? 0.35 : 0.2);
};
const f_snowball: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.5 * r;
  circle(g, cx, cy, r * 0.95);
  fillStroke(g, shade(g, cx, cy, r, c, 0.1), 2.4);
  g.fillStyle = "rgba(170,200,230,0.55)";
  for (const [x, y, s] of [[-0.4, 0.2, 0.18], [0.35, -0.35, 0.12], [0.3, 0.5, 0.15]]) {
    circle(g, cx + x * r, cy + y * r, s * r);
    g.fill();
  }
  // havuç burun + kızgın gözler
  g.beginPath();
  g.moveTo(cx + r * 0.1, cy);
  g.lineTo(cx + r * 0.75, cy + r * 0.1);
  g.lineTo(cx + r * 0.1, cy + r * 0.18);
  fillStroke(g, "#ff8a2a", 1.5);
  eyes(g, cx - r * 0.05, cy - r * 0.3, r, { n: 2, spread: 0.3, size: 0.12, col: "#222", pupil: "#000", angry: true });
  g.fillStyle = "#ff3a1a";
  circle(g, cx - r * 0.1, cy - r * 1.0, r * (f ? 0.14 : 0.1));
  g.fill();
};

// ------------------------------------------------------------------------
// ZÜMRÜT ORMAN
// ------------------------------------------------------------------------
const j_snake: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.6 * r;
  g.lineCap = "round";
  const path = () => {
    g.beginPath();
    g.moveTo(cx - r * 1.2, cy + r * 0.3);
    g.bezierCurveTo(cx - r * 0.8, cy - r * (f ? 0.4 : 0.1), cx - r * 0.3, cy + r * (f ? 0.6 : 0.8), cx + r * 0.2, cy + r * 0.1);
  };
  path();
  g.strokeStyle = OUT;
  g.lineWidth = r * 0.55 + 3;
  g.stroke();
  path();
  g.strokeStyle = rgbCss(c);
  g.lineWidth = r * 0.55;
  g.stroke();
  path();
  g.strokeStyle = rgbCss(lighten(c, 0.35));
  g.setLineDash([r * 0.18, r * 0.22]);
  g.lineWidth = r * 0.2;
  g.stroke();
  g.setLineDash([]);
  ellipse(g, cx + r * 0.45, cy - r * 0.15, r * 0.55, r * 0.42, -0.3);
  fillStroke(g, shade(g, cx + r * 0.45, cy - r * 0.15, r * 0.5, c), 2.4);
  eyes(g, cx + r * 0.55, cy - r * 0.32, r * 0.55, { n: 2, spread: 0.4, size: 0.22, col: "#ffe86a", pupil: "#000" });
  g.strokeStyle = "#e0324a";
  g.lineWidth = 2;
  g.beginPath();
  g.moveTo(cx + r * 0.95, cy - r * 0.05);
  g.lineTo(cx + r * 1.25, cy + (f ? -r * 0.1 : r * 0.05));
  g.stroke();
};
const j_fly: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.5 * r;
  g.globalAlpha = 0.35;
  g.fillStyle = rgbCss(c);
  circle(g, cx - r * 0.3, cy + r * 0.2, r * 1.0);
  g.fill();
  g.globalAlpha = 1;
  for (const s of [-1, 1]) {
    ellipse(g, cx + s * r * 0.15, cy - r * (f ? 0.7 : 0.5), r * 0.45, r * 0.22, s * (f ? 0.6 : 0.2));
    g.fillStyle = "rgba(230,255,230,0.6)";
    g.fill();
  }
  ellipse(g, cx - r * 0.35, cy + r * 0.2, r * 0.55, r * 0.4);
  g.fillStyle = "#fff9a0";
  g.shadowColor = rgbCss(c);
  g.shadowBlur = 12;
  g.fill();
  g.shadowBlur = 0;
  circle(g, cx + r * 0.35, cy, r * 0.42);
  fillStroke(g, shade(g, cx + r * 0.35, cy, r * 0.4, [60, 70, 40]), 2);
  eyes(g, cx + r * 0.45, cy - r * 0.05, r * 0.5, { n: 2, spread: 0.45, size: 0.25 });
};
const j_frog: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.6 * r;
  for (const s of [-1, 1]) {
    ellipse(g, cx + s * r * 0.75, cy + r * 0.55, r * 0.35, r * (f ? 0.2 : 0.25));
    fillStroke(g, rgbCss(darken(c, 0.15)), 2);
  }
  ellipse(g, cx, cy + r * 0.1, r * 0.95, r * 0.72);
  fillStroke(g, shade(g, cx, cy, r, c), 2.6);
  ellipse(g, cx, cy + r * 0.35, r * 0.6, r * 0.35);
  g.fillStyle = rgbCss(lighten(c, 0.45));
  g.fill();
  for (const s of [-1, 1]) {
    circle(g, cx + s * r * 0.42, cy - r * 0.5, r * 0.3);
    fillStroke(g, rgbCss(c), 2);
  }
  eyes(g, cx, cy - r * 0.52, r, { n: 2, spread: 0.42, size: 0.2, col: "#fff59a", pupil: "#000" });
  g.strokeStyle = "#1a2a10";
  g.lineWidth = 2;
  g.beginPath();
  g.arc(cx, cy - r * 0.05, r * 0.45, 0.3, Math.PI - 0.3);
  g.stroke();
  g.fillStyle = "rgba(255,90,60,0.85)";
  for (const [x, y] of [[-0.5, 0.1], [0.55, 0.0], [0.1, -0.2]]) {
    circle(g, cx + x * r, cy + y * r, r * 0.08);
    g.fill();
  }
};
const j_treant: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.5 * r;
  legs(g, cx, cy + r * 0.6, r, "#4a3020", f, 2, 0.35, 0.34);
  // taç (yapraklar)
  for (const [x, y, s] of [[-0.6, -0.8, 0.5], [0.0, -1.05, 0.55], [0.6, -0.8, 0.5], [-0.25, -1.2, 0.4], [0.35, -1.2, 0.4]]) {
    circle(g, cx + x * r, cy + y * r, s * r);
    fillStroke(g, shade(g, cx + x * r, cy + y * r, s * r, [70, 150, 60], 0.3), 2);
  }
  g.beginPath();
  g.roundRect(cx - r * 0.7, cy - r * 0.6, r * 1.4, r * 1.35, r * 0.3);
  fillStroke(g, shade(g, cx, cy, r, c), 2.8);
  g.strokeStyle = rgbCss(darken(c, 0.4));
  g.lineWidth = 1.6;
  for (let i = 0; i < 3; i++) {
    g.beginPath();
    g.moveTo(cx - r * 0.45 + i * r * 0.45, cy - r * 0.45);
    g.lineTo(cx - r * 0.4 + i * r * 0.42, cy + r * 0.6);
    g.stroke();
  }
  for (const s of [-1, 1]) {
    g.strokeStyle = OUT;
    g.lineWidth = r * 0.2 + 2;
    g.beginPath();
    g.moveTo(cx + s * r * 0.65, cy - r * 0.2);
    g.lineTo(cx + s * r * 1.2, cy + r * (f ? -0.1 : 0.2));
    g.stroke();
    g.strokeStyle = rgbCss(c);
    g.lineWidth = r * 0.2;
    g.stroke();
  }
  eyes(g, cx, cy - r * 0.1, r, { n: 2, spread: 0.3, size: 0.14, col: "#d6ff7a", pupil: "#2a3a00", glow: "rgba(190,255,90,1)" });
};
const j_panther: DrawFn = (g, r, c, f) => {
  sprinter(g, r, c, f);
};
const j_gorilla: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.5 * r;
  legs(g, cx, cy + r * 0.6, r, rgbCss(darken(c, 0.4)), f, 2, 0.32, 0.34);
  for (const s of [-1, 1]) {
    g.strokeStyle = OUT;
    g.lineWidth = r * 0.42 + 2;
    g.beginPath();
    g.moveTo(cx + s * r * 0.7, cy - r * 0.3);
    g.lineTo(cx + s * r * 1.1, cy + r * (f && s > 0 ? 0.3 : 0.7));
    g.stroke();
    g.strokeStyle = rgbCss(c);
    g.lineWidth = r * 0.42;
    g.stroke();
  }
  ellipse(g, cx, cy, r * 0.95, r * 0.85);
  fillStroke(g, shade(g, cx, cy, r, c, 0.25), 2.8);
  ellipse(g, cx, cy - r * 0.15, r * 0.5, r * 0.42);
  g.fillStyle = "#c8b8a8";
  g.fill();
  eyes(g, cx, cy - r * 0.3, r, { n: 2, spread: 0.24, size: 0.12, angry: true });
  g.fillStyle = "#2a1a1a";
  circle(g, cx - r * 0.08, cy - r * 0.08, r * 0.05);
  g.fill();
  circle(g, cx + r * 0.08, cy - r * 0.08, r * 0.05);
  g.fill();
  mouth(g, cx, cy + r * 0.1, r * 0.22, f ? 0.4 : 0.2);
};
const j_shroom: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.55 * r;
  g.beginPath();
  g.roundRect(cx - r * 0.4, cy - r * 0.1, r * 0.8, r * 0.85, r * 0.2);
  fillStroke(g, "#efe4cc", 2.2);
  g.beginPath();
  g.moveTo(cx - r * 1.05, cy);
  g.quadraticCurveTo(cx - r * 1.0, cy - r * (f ? 1.15 : 1.05), cx, cy - r * 1.1);
  g.quadraticCurveTo(cx + r * 1.0, cy - r * (f ? 1.05 : 1.15), cx + r * 1.05, cy);
  g.closePath();
  fillStroke(g, shade(g, cx, cy - r * 0.5, r, c), 2.6);
  g.fillStyle = "#fff4ee";
  for (const [x, y, s] of [[-0.55, -0.35, 0.18], [0.1, -0.7, 0.2], [0.6, -0.3, 0.15]]) {
    circle(g, cx + x * r, cy + y * r, s * r);
    g.fill();
  }
  eyes(g, cx, cy + r * 0.25, r, { n: 2, spread: 0.2, size: 0.12, angry: true });
};

// ------------------------------------------------------------------------
// KIZIL ÇÖL
// ------------------------------------------------------------------------
const d_scorpion: DrawFn = (g, r, c, f) => {
  const cx = 1.45 * r, cy = 1.7 * r;
  for (let i = 0; i < 3; i++) {
    for (const s of [-1, 1]) {
      g.strokeStyle = OUT;
      g.lineWidth = 2.6;
      g.beginPath();
      g.moveTo(cx - r * 0.3 + i * r * 0.3, cy + s * r * 0.1);
      g.lineTo(cx - r * 0.45 + i * r * 0.3 + ((i + f) % 2 ? 0.1 : -0.1) * r, cy + r * 0.55);
      g.stroke();
    }
  }
  // kuyruk
  g.lineCap = "round";
  const tail = () => {
    g.beginPath();
    g.moveTo(cx - r * 0.6, cy);
    g.quadraticCurveTo(cx - r * 1.35, cy - r * 0.6, cx - r * 0.85, cy - r * (f ? 1.35 : 1.25));
    g.quadraticCurveTo(cx - r * 0.4, cy - r * 1.55, cx - r * 0.05, cy - r * 1.15);
  };
  tail();
  g.strokeStyle = OUT;
  g.lineWidth = r * 0.32 + 3;
  g.stroke();
  tail();
  g.strokeStyle = rgbCss(c);
  g.lineWidth = r * 0.32;
  g.stroke();
  g.beginPath();
  g.moveTo(cx - r * 0.1, cy - r * 1.25);
  g.lineTo(cx + r * 0.2, cy - r * 1.0);
  g.lineTo(cx - r * 0.12, cy - r * 1.02);
  g.closePath();
  fillStroke(g, "#2a1410", 1.5);
  ellipse(g, cx, cy, r * 0.8, r * 0.45);
  fillStroke(g, shade(g, cx, cy, r * 0.8, c), 2.4);
  // kıskaçlar
  for (const s of [-1, 1]) {
    g.beginPath();
    g.ellipse(cx + r * 0.95, cy + s * r * 0.35, r * 0.3, r * 0.18, s * (f ? 0.4 : 0.2), 0, Math.PI * 2);
    fillStroke(g, rgbCss(darken(c, 0.1)), 2);
  }
  eyes(g, cx + r * 0.5, cy - r * 0.15, r * 0.6, { n: 2, spread: 0.35, size: 0.18, col: "#ff4a3a", pupil: "#200" });
};
const d_vulture: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.5 * r;
  wing(g, cx - r * 0.2, cy, r * 1.05, -1, f === 0, darken(c, 0.15), false);
  wing(g, cx + r * 0.2, cy, r * 1.05, 1, f === 0, darken(c, 0.15), false);
  ellipse(g, cx, cy + r * 0.05, r * 0.55, r * 0.7);
  fillStroke(g, shade(g, cx, cy, r * 0.6, c), 2.2);
  circle(g, cx, cy - r * 0.65, r * 0.32);
  fillStroke(g, "#e8b0a0", 2);
  g.beginPath();
  g.moveTo(cx + r * 0.15, cy - r * 0.62);
  g.quadraticCurveTo(cx + r * 0.55, cy - r * 0.55, cx + r * 0.32, cy - r * 0.35);
  g.closePath();
  fillStroke(g, "#f0c860", 1.6);
  eyes(g, cx - r * 0.05, cy - r * 0.7, r * 0.5, { n: 1, size: 0.25, col: "#ffefb0", pupil: "#200" });
};
const d_archer: DrawFn = (g, r, c, f) => {
  const cx = 1.45 * r, cy = 1.55 * r;
  // yay
  g.strokeStyle = "#7a4a22";
  g.lineWidth = r * 0.12;
  g.beginPath();
  g.arc(cx + r * 0.6, cy - r * 0.05, r * 0.85, -1.2, 1.2);
  g.stroke();
  g.strokeStyle = "#eee";
  g.lineWidth = 1.2;
  g.beginPath();
  g.moveTo(cx + r * 0.6 + Math.cos(-1.2) * r * 0.85, cy - r * 0.05 + Math.sin(-1.2) * r * 0.85);
  g.lineTo(cx + r * (f ? 0.35 : 0.55), cy - r * 0.05);
  g.lineTo(cx + r * 0.6 + Math.cos(1.2) * r * 0.85, cy - r * 0.05 + Math.sin(1.2) * r * 0.85);
  g.stroke();
  // cüppe gövde
  g.beginPath();
  g.moveTo(cx - r * 0.7, cy + r * 0.85);
  g.quadraticCurveTo(cx - r * 0.6, cy - r * 0.4, cx, cy - r * 0.55);
  g.quadraticCurveTo(cx + r * 0.6, cy - r * 0.4, cx + r * 0.7, cy + r * 0.85);
  g.closePath();
  fillStroke(g, shade(g, cx, cy, r, c), 2.4);
  // sarık
  circle(g, cx, cy - r * 0.6, r * 0.45);
  fillStroke(g, "#f0e6d0", 2);
  g.fillStyle = "#2a1a10";
  g.fillRect(cx - r * 0.35, cy - r * 0.6, r * 0.7, r * 0.18);
  eyes(g, cx + r * 0.05, cy - r * 0.52, r * 0.45, { n: 2, spread: 0.4, size: 0.18, col: "#ffefb0", pupil: "#200" });
};
const d_mummy: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.5 * r;
  legs(g, cx, cy + r * 0.65, r, rgbCss(darken(c, 0.25)), f, 2, 0.32, 0.34);
  for (const s of [-1, 1]) {
    g.strokeStyle = OUT;
    g.lineWidth = r * 0.3 + 2;
    g.beginPath();
    g.moveTo(cx + s * r * 0.6, cy - r * 0.3);
    g.lineTo(cx + s * r * 1.15, cy - r * (f ? 0.25 : 0.4));
    g.stroke();
    g.strokeStyle = rgbCss(c);
    g.lineWidth = r * 0.3;
    g.stroke();
  }
  g.beginPath();
  g.roundRect(cx - r * 0.75, cy - r * 0.95, r * 1.5, r * 1.75, r * 0.5);
  fillStroke(g, shade(g, cx, cy, r, c, 0.2), 2.8);
  g.strokeStyle = rgbCss(darken(c, 0.3));
  g.lineWidth = 1.6;
  for (let i = 0; i < 6; i++) {
    g.beginPath();
    g.moveTo(cx - r * 0.7, cy - r * 0.7 + i * r * 0.28);
    g.lineTo(cx + r * 0.7, cy - r * 0.6 + i * r * 0.28 + (i % 2 ? 2 : -2));
    g.stroke();
  }
  g.fillStyle = "#1a1010";
  g.fillRect(cx - r * 0.5, cy - r * 0.5, r * 1.0, r * 0.22);
  eyes(g, cx, cy - r * 0.39, r, { n: 2, spread: 0.24, size: 0.09, col: "#7affb0", pupil: "#0a4", glow: "rgba(90,255,150,1)" });
};
const d_jackal: DrawFn = (g, r, c, f) => {
  sprinter(g, r, c, f);
};
const d_bandit: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.5 * r;
  legs(g, cx, cy + r * 0.6, r, "#3a2a20", f, 2, 0.38, 0.28);
  // kılıç
  g.save();
  g.translate(cx + r * 0.95, cy + r * 0.1);
  g.rotate(f ? -0.9 : -0.5);
  g.beginPath();
  g.moveTo(0, 0);
  g.quadraticCurveTo(r * 0.3, -r * 0.8, r * 0.05, -r * 1.35);
  g.lineTo(-r * 0.1, -r * 0.1);
  g.closePath();
  fillStroke(g, "#d8dce6", 1.6);
  g.restore();
  circle(g, cx, cy, r * 0.88);
  fillStroke(g, shade(g, cx, cy, r * 0.88, c), 2.8);
  // peçe + sarık
  g.beginPath();
  g.arc(cx, cy - r * 0.15, r * 0.85, Math.PI, 0);
  g.closePath();
  fillStroke(g, "#3a2e2a", 2);
  g.fillStyle = "#2a1c18";
  g.fillRect(cx - r * 0.75, cy + r * 0.05, r * 1.5, r * 0.4);
  eyes(g, cx, cy - r * 0.08, r, { n: 2, spread: 0.3, size: 0.13, angry: true });
};
const d_cactus: DrawFn = (g, r, c, f) => {
  const cx = 1.5 * r, cy = 1.55 * r;
  for (const s of [-1, 1]) {
    g.beginPath();
    g.roundRect(cx + s * r * 0.55 - r * 0.2, cy - r * (s > 0 ? 0.8 : 0.5) - (f ? 3 : 0), r * 0.4, r * 0.75, r * 0.2);
    fillStroke(g, shade(g, cx, cy, r * 0.5, c), 2);
  }
  g.beginPath();
  g.roundRect(cx - r * 0.45, cy - r * 1.05, r * 0.9, r * 1.9, r * 0.45);
  fillStroke(g, shade(g, cx, cy, r, c), 2.6);
  g.strokeStyle = "rgba(255,255,230,0.9)";
  g.lineWidth = 1.2;
  for (let i = 0; i < 9; i++) {
    const x = cx + ((i * 37) % 7 - 3) * r * 0.12, y = cy - r * 0.8 + i * r * 0.18;
    g.beginPath();
    g.moveTo(x, y);
    g.lineTo(x + (i % 2 ? 4 : -4), y - 3);
    g.stroke();
  }
  g.fillStyle = "#ff5a8a";
  circle(g, cx, cy - r * 1.05, r * 0.16);
  g.fill();
  eyes(g, cx, cy - r * 0.3, r, { n: 2, spread: 0.22, size: 0.12, angry: true });
};

export const ENEMY_ART: Record<string, DrawFn> = {
  red, blue, yellow, tank, sprinter, brute, elite, kamikaze, healer, wizard, stinger,
  bomber: (g, r, c, f) => {
    brute(g, r, c, f);
    // sırtta bomba fitili
    g.fillStyle = "#2a2a30";
    circle(g, 1.5 * r + r * 0.55, 1.5 * r - r * 0.85, r * 0.28);
    g.fill();
    g.fillStyle = f ? "#fff2a0" : "#ff8a2a";
    circle(g, 1.5 * r + r * 0.75, 1.5 * r - r * 1.15, r * 0.1);
    g.fill();
  },
  herald, shieldman, goblin, splitter, necro, ghost, raised: necro,
  imp, hound, reaver, seer, golem, butcher, warden,
  f_beetle, f_bat, f_wisp, f_golem, f_wolf, f_yeti, f_snowball,
  j_snake, j_fly, j_frog, j_treant, j_panther, j_gorilla, j_shroom,
  d_scorpion, d_vulture, d_archer, d_mummy, d_jackal, d_bandit, d_cactus,
};

/** Bir şekil için çizim (yoksa kırmızı sürüngen). */
export function enemyArt(shape: string): DrawFn {
  return ENEMY_ART[shape] || red;
}

export function mutantCol(c: RGB, hell: boolean): RGB {
  return mixCol(c, hell ? [236, 226, 214] : [236, 242, 230], 0.75);
}
