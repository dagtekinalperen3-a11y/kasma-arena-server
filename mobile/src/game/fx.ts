/**
 * Görsel efektler. Hepsi önceden ayrılmış havuzlardan gelir; oyun sırasında
 * nesne yaratılmaz (çöp toplayıcı takılması olmasın diye).
 */
import { BitmapFont, BitmapText, Container, Graphics, Particle, ParticleContainer, Sprite, Texture } from "pixi.js";
import { RGB, rgbToHex, lighten } from "../core/util";
import { softCircle, ringTex, dotTex, discTex } from "../render/tex";

interface P {
  p: Particle;
  alive: boolean;
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  max: number;
  r: number;
  grav: number;
  drag: number;
  grow: number;
  a0: number;
}
interface Wave {
  s: Sprite;
  alive: boolean;
  x: number;
  y: number;
  r: number;
  life: number;
  max: number;
  a0: number;
}
interface Pop {
  t: BitmapText;
  alive: boolean;
  x: number;
  y: number;
  vy: number;
  life: number;
  max: number;
  scale: number;
}
interface Bolt {
  g: Graphics;
  alive: boolean;
  life: number;
  max: number;
}

let fontsReady = false;
export function installFonts() {
  if (fontsReady) return;
  fontsReady = true;
  const chars = [["0", "9"], "+-!%xX.,:/ ", ["A", "Z"], "ÇĞİÖŞÜÂ"];
  BitmapFont.install({
    name: "dmg",
    style: { fontFamily: "Rubik, Arial Black, sans-serif", fontSize: 40, fontWeight: "900", fill: "#ffffff", stroke: { color: "#0d0a14", width: 7, join: "round" } },
    chars: chars as any,
    resolution: 1,
    padding: 6,
  });
}

export class FX {
  addLayer: ParticleContainer;
  normLayer: ParticleContainer;
  waveLayer = new Container();
  textLayer = new Container();
  boltLayer = new Container();
  private parts: P[] = [];
  private nparts: P[] = [];
  private waves: Wave[] = [];
  private pops: Pop[] = [];
  private bolts: Bolt[] = [];
  private pi = 0;
  private ni = 0;
  shakeAmt = 0;
  shakeT = 0;
  flashCol: number = 0xffffff;
  flashA = 0;
  private flashMax = 0;
  quality = 1; // 0.5 = düşük (parçacık sayısı yarıya)
  showDamage = true;
  private popBudget = 0;
  enabled = true;

  constructor(maxParts = 700, maxNorm = 260) {
    const soft = softCircle();
    this.addLayer = new ParticleContainer({
      dynamicProperties: { position: true, vertex: true, rotation: false, color: true },
    } as any);
    this.addLayer.blendMode = "add";
    this.normLayer = new ParticleContainer({
      dynamicProperties: { position: true, vertex: true, rotation: false, color: true },
    } as any);
    const dot = dotTex();
    for (let i = 0; i < maxParts; i++) {
      const p = new Particle({ texture: soft, x: -9999, y: -9999, anchorX: 0.5, anchorY: 0.5, alpha: 0 } as any);
      this.addLayer.addParticle(p);
      this.parts.push({ p, alive: false, x: 0, y: 0, vx: 0, vy: 0, life: 0, max: 1, r: 1, grav: 0, drag: 0, grow: 0, a0: 1 });
    }
    for (let i = 0; i < maxNorm; i++) {
      const p = new Particle({ texture: dot, x: -9999, y: -9999, anchorX: 0.5, anchorY: 0.5, alpha: 0 } as any);
      this.normLayer.addParticle(p);
      this.nparts.push({ p, alive: false, x: 0, y: 0, vx: 0, vy: 0, life: 0, max: 1, r: 1, grav: 0, drag: 0, grow: 0, a0: 1 });
    }
    const rt = [ringTex(5), ringTex(10), ringTex(18)];
    for (let i = 0; i < 48; i++) {
      const s = new Sprite(rt[i % 3]);
      s.anchor.set(0.5);
      s.visible = false;
      s.blendMode = "add";
      this.waveLayer.addChild(s);
      this.waves.push({ s, alive: false, x: 0, y: 0, r: 0, life: 0, max: 1, a0: 1 });
    }
    installFonts();
    for (let i = 0; i < 48; i++) {
      const t = new BitmapText({ text: "", style: { fontFamily: "dmg", fontSize: 20 } });
      t.anchor.set(0.5);
      t.visible = false;
      this.textLayer.addChild(t);
      this.pops.push({ t, alive: false, x: 0, y: 0, vy: 0, life: 0, max: 1, scale: 1 });
    }
    for (let i = 0; i < 24; i++) {
      const g = new Graphics();
      g.visible = false;
      g.blendMode = "add";
      this.boltLayer.addChild(g);
      this.bolts.push({ g, alive: false, life: 0, max: 1 });
    }
    void discTex;
  }

  private takePart(add = true): P {
    const arr = add ? this.parts : this.nparts;
    let i = add ? this.pi : this.ni;
    for (let k = 0; k < arr.length; k++) {
      const q = arr[i];
      i = (i + 1) % arr.length;
      if (!q.alive) {
        if (add) this.pi = i;
        else this.ni = i;
        return q;
      }
    }
    // hepsi doluysa en eskisini (sıradakini) ez
    const q = arr[i];
    if (add) this.pi = (i + 1) % arr.length;
    else this.ni = (i + 1) % arr.length;
    return q;
  }

  spark(x: number, y: number, col: RGB | number[], vx: number, vy: number, life: number, r: number, add = true, grav = 0, drag = 0, grow = 0) {
    if (!this.enabled) return;
    const q = this.takePart(add);
    q.alive = true;
    q.x = x;
    q.y = y;
    q.vx = vx;
    q.vy = vy;
    q.life = q.max = Math.max(0.05, life);
    q.r = r;
    q.grav = grav;
    q.drag = drag;
    q.grow = grow;
    q.a0 = 1;
    q.p.tint = rgbToHex(col);
    q.p.alpha = 1;
    const sc = (r * (add ? 3.2 : 2.2)) / (add ? 64 : 16);
    q.p.scaleX = q.p.scaleY = sc;
    q.p.x = x;
    q.p.y = y;
  }

  burst(x: number, y: number, col: RGB | number[], n = 10, speed = 150, life = 0.4, r = 3, grav = 0, add = true) {
    n = Math.max(1, Math.round(n * this.quality));
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2;
      const s = speed * (0.35 + Math.random() * 0.75);
      this.spark(x, y, col, Math.cos(a) * s, Math.sin(a) * s, life * (0.6 + Math.random() * 0.6), r * (0.7 + Math.random() * 0.5), add, grav, 2);
    }
  }

  ring(x: number, y: number, col: RGB | number[], n = 12, speed = 160, life = 0.35, r = 3) {
    n = Math.max(3, Math.round(n * this.quality));
    const off = Math.random() * 6.28;
    for (let i = 0; i < n; i++) {
      const a = off + (i / n) * Math.PI * 2;
      this.spark(x, y, col, Math.cos(a) * speed, Math.sin(a) * speed, life, r, true, 0, 3);
    }
  }

  shockwave(x: number, y: number, radius: number, col: RGB | number[], life = 0.35, width = 4) {
    if (!this.enabled) return;
    let w: Wave | undefined;
    const bucket = width <= 4 ? 0 : width <= 7 ? 1 : 2;
    for (let i = bucket; i < this.waves.length; i += 3) if (!this.waves[i].alive) { w = this.waves[i]; break; }
    if (!w) return;
    w.alive = true;
    w.x = x;
    w.y = y;
    w.r = radius;
    w.life = w.max = life;
    w.a0 = 0.95;
    w.s.visible = true;
    w.s.tint = rgbToHex(lighten(col, 0.1));
    w.s.position.set(x, y);
    w.s.scale.set(0.01);
  }

  popup(x: number, y: number, text: string, col: RGB | number[], size = 16, life = 0.6, force = false) {
    if (!this.enabled) return;
    if (!force && !this.showDamage && /^[0-9]+!?$/.test(text)) return;
    // kalabalıkta küçük sayıları seyrelt
    if (!force && size < 18 && /^[0-9]+!?$/.test(text)) {
      if (this.popBudget <= 0) return;
      this.popBudget -= 1;
    }
    let p: Pop | undefined;
    let oldest: Pop | undefined;
    for (const q of this.pops) {
      if (!q.alive) { p = q; break; }
      if (!oldest || q.life < oldest.life) oldest = q;
    }
    if (!p) p = oldest!;
    p.alive = true;
    p.x = x + (Math.random() - 0.5) * 10;
    p.y = y;
    p.vy = -46 - size * 1.2;
    p.life = p.max = life;
    p.scale = size / 20;
    p.t.text = text;
    p.t.tint = rgbToHex(col);
    p.t.visible = true;
    p.t.alpha = 1;
    p.t.position.set(p.x, p.y);
    p.t.scale.set(p.scale * 1.35);
  }

  bolt(points: number[][], col: RGB | number[], life = 0.25, width = 3) {
    if (!this.enabled || points.length < 2) return;
    const b = this.bolts.find((q) => !q.alive);
    if (!b) return;
    b.alive = true;
    b.life = b.max = life;
    const g = b.g;
    g.clear();
    const draw = () => {
      g.moveTo(points[0][0], points[0][1]);
      for (let i = 1; i < points.length; i++) g.lineTo(points[i][0], points[i][1]);
    };
    draw();
    g.stroke({ width: width * 3, color: rgbToHex(col), alpha: 0.3, join: "round", cap: "round" });
    draw();
    g.stroke({ width, color: rgbToHex(lighten(col, 0.5)), alpha: 1, join: "round", cap: "round" });
    g.visible = true;
    g.alpha = 1;
  }

  static shakeOn = true;
  shake(amount: number, dur = 0.2) {
    if (!FX.shakeOn) return;
    if (amount > this.shakeAmt * (this.shakeT > 0 ? 1 : 0)) {
      this.shakeAmt = amount;
      this.shakeT = dur;
    }
  }

  flash(col: RGB | number[], alpha = 0.4) {
    this.flashCol = rgbToHex(col);
    this.flashA = Math.max(this.flashA, alpha);
    this.flashMax = Math.max(0.2, alpha);
  }

  update(dt: number) {
    this.popBudget = Math.min(10, this.popBudget + dt * 18);
    for (const arr of [this.parts, this.nparts]) {
      for (let i = 0; i < arr.length; i++) {
        const q = arr[i];
        if (!q.alive) continue;
        q.life -= dt;
        if (q.life <= 0) {
          q.alive = false;
          q.p.alpha = 0;
          q.p.x = -9999;
          continue;
        }
        if (q.drag) {
          const k = Math.max(0, 1 - q.drag * dt);
          q.vx *= k;
          q.vy *= k;
        }
        q.vy += q.grav * dt;
        q.x += q.vx * dt;
        q.y += q.vy * dt;
        const f = q.life / q.max;
        q.p.x = q.x;
        q.p.y = q.y;
        q.p.alpha = f * q.a0;
        if (q.grow) {
          const base = arr === this.parts ? (q.r * 3.2) / 64 : (q.r * 2.2) / 16;
          q.p.scaleX = q.p.scaleY = base * (1 + q.grow * (1 - f));
        }
      }
    }
    for (const w of this.waves) {
      if (!w.alive) continue;
      w.life -= dt;
      if (w.life <= 0) {
        w.alive = false;
        w.s.visible = false;
        continue;
      }
      const f = 1 - w.life / w.max;
      const e = 1 - Math.pow(1 - f, 3);
      w.s.scale.set((w.r * e) / 128);
      w.s.alpha = w.a0 * (1 - f);
    }
    for (const p of this.pops) {
      if (!p.alive) continue;
      p.life -= dt;
      if (p.life <= 0) {
        p.alive = false;
        p.t.visible = false;
        continue;
      }
      p.vy *= Math.max(0, 1 - dt * 4);
      p.y += p.vy * dt;
      const f = 1 - p.life / p.max;
      const pop = f < 0.15 ? 1.35 - (f / 0.15) * 0.35 : 1;
      p.t.position.set(p.x, p.y);
      p.t.scale.set(p.scale * pop);
      p.t.alpha = f > 0.6 ? 1 - (f - 0.6) / 0.4 : 1;
    }
    for (const b of this.bolts) {
      if (!b.alive) continue;
      b.life -= dt;
      if (b.life <= 0) {
        b.alive = false;
        b.g.visible = false;
        continue;
      }
      b.g.alpha = b.life / b.max;
    }
    if (this.shakeT > 0) {
      this.shakeT -= dt;
      if (this.shakeT <= 0) this.shakeAmt = 0;
    }
    if (this.flashA > 0) this.flashA = Math.max(0, this.flashA - dt * (this.flashMax / 0.35));
  }

  clear() {
    for (const q of this.parts) { q.alive = false; q.p.alpha = 0; q.p.x = -9999; }
    for (const q of this.nparts) { q.alive = false; q.p.alpha = 0; q.p.x = -9999; }
    for (const w of this.waves) { w.alive = false; w.s.visible = false; }
    for (const p of this.pops) { p.alive = false; p.t.visible = false; }
    for (const b of this.bolts) { b.alive = false; b.g.visible = false; }
    this.shakeAmt = 0;
    this.flashA = 0;
  }
}

export function zigzag(x1: number, y1: number, x2: number, y2: number, segs: number, amp: number): number[][] {
  const pts: number[][] = [[x1, y1]];
  const dx = x2 - x1, dy = y2 - y1;
  const l = Math.hypot(dx, dy) || 1;
  const nx = -dy / l, ny = dx / l;
  for (let i = 1; i < segs; i++) {
    const t = i / segs;
    const o = (Math.random() * 2 - 1) * amp;
    pts.push([x1 + dx * t + nx * o, y1 + dy * t + ny * o]);
  }
  pts.push([x2, y2]);
  return pts;
}

export { Texture };
