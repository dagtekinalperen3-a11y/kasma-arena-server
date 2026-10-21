/**
 * Silahlar: sandıktan / seviye kartından gelen 20 silahın mantığı.
 * Python: _fire_weapon, update_passive_weapons ve silah nesnesi sınıfları.
 */
import { clamp, dist, normDir, TAU, lighten, scaleCol, RGB } from "../core/util";
import * as B from "./balance";
import { GD, WEAPON_BY_KEY } from "./data";
import { sfx } from "../core/audio";
import { t } from "../core/i18n";
import { zigzag } from "./fx";
import { DMG } from "./enemy";
import type { Run, Target } from "./run";

const C = GD;
export const COL = {
  ZEMZEM: [96, 198, 255] as RGB, ZEMZEM2: [208, 246, 255] as RGB,
  SHOE: [255, 142, 52] as RGB, SHOE2: [255, 226, 140] as RGB,
  FROST: [124, 208, 255] as RGB, FROST2: [226, 246, 255] as RGB,
  TORNADO: [186, 218, 240] as RGB, TORNADO2: [240, 250, 255] as RGB,
  AXE: [235, 140, 74] as RGB,
  WHIP: [238, 152, 84] as RGB, WHIP2: [255, 226, 176] as RGB,
  PENTA: [238, 78, 122] as RGB, PENTA2: [255, 182, 208] as RGB,
  SHIELD: [150, 176, 214] as RGB, SHIELD2: [236, 246, 255] as RGB,
  EMANET: [214, 226, 246] as RGB, EMANET2: [255, 252, 226] as RGB,
  CLOAK: [132, 120, 214] as RGB, CLOAK2: [214, 206, 255] as RGB,
  GHOST: [130, 222, 255] as RGB, GHOST2: [226, 250, 255] as RGB,
  WOLF: [158, 168, 255] as RGB, WOLF2: [232, 236, 255] as RGB,
  TESLA: [255, 232, 110] as RGB, TESLA2: [255, 252, 214] as RGB,
  METEOR: [255, 118, 52] as RGB, METEOR2: [255, 214, 140] as RGB,
  BEAM: [255, 206, 104] as RGB, BEAM2: [255, 248, 214] as RGB,
  HAWK: [226, 168, 96] as RGB, HAWK2: [255, 236, 196] as RGB,
  BAT: [186, 104, 238] as RGB, BAT2: [240, 212, 255] as RGB,
  NOVA: [150, 228, 255] as RGB, NOVA2: [236, 250, 255] as RGB,
  KNIFE: [214, 226, 246] as RGB, KNIFE2: [255, 255, 255] as RGB,
  QUAKE: [226, 146, 70] as RGB, QUAKE2: [255, 228, 168] as RGB, QUAKE_ROCK: [122, 96, 74] as RGB,
};

export function segDist(px: number, py: number, ax: number, ay: number, bx: number, by: number) {
  const vx = bx - ax, vy = by - ay;
  const ll = vx * vx + vy * vy;
  if (ll <= 1e-9) return Math.hypot(px - ax, py - ay);
  const k = clamp(((px - ax) * vx + (py - ay) * vy) / ll, 0, 1);
  return Math.hypot(px - (ax + vx * k), py - (ay + vy * k));
}

/** Bütün silah nesnelerinin ortak tabanı. */
export abstract class WObj {
  alive = true;
  src = "other";
  view: any = null;
  x = 0;
  y = 0;
  abstract kind: string;
  abstract update(dt: number, run: Run): void;
}

export class WaterZone extends WObj {
  kind = "water";
  max: number;
  slow = 0.52;
  tick = 0;
  t = 0;
  splash = 0.28;
  constructor(x: number, y: number, public r: number, public dps: number, public life: number, public lvl: number, W: number, H: number) {
    super();
    this.x = clamp(x, 20, W - 20);
    this.y = clamp(y, 20, H - 20);
    this.max = life;
    this.src = "zemzem";
  }
  curR() {
    return this.r * clamp(this.t / 0.18, 0, 1) * clamp(this.life / 0.5, 0.55, 1);
  }
  update(dt: number, run: Run) {
    this.t += dt;
    this.life -= dt;
    this.splash = Math.max(0, this.splash - dt);
    if (this.life <= 0) {
      this.alive = false;
      return;
    }
    this.tick -= dt;
    if (this.tick > 0) return;
    this.tick = 0.18;
    const rad = this.curR();
    let sl = 3;
    for (const e of run.targets) {
      if (!e.alive) continue;
      if (dist(this.x, this.y, e.x, e.y) <= rad + e.radius * 0.6) {
        run.fieldDamage(e, this.dps * 0.18, 0, this.lvl);
        e.applySlow(this.slow, 0.55);
        if (sl > 0 && Math.random() < 0.5) {
          sl--;
          run.fx.spark(e.x, e.y, COL.ZEMZEM2, Math.random() * 40 - 20, -30 - Math.random() * 40, 0.35, 2);
        }
      }
    }
  }
}

export class FireRing extends WObj {
  kind = "firering";
  max: number;
  tick = 0;
  t = 0;
  seed = Math.random() * TAU;
  constructor(x: number, y: number, public r0: number, public dps: number, public life: number, public lvl: number, public burn = 0, public ice = false, public slow = 0.55) {
    super();
    this.x = x;
    this.y = y;
    this.max = Math.max(0.05, life);
    this.src = ice ? "frost" : "shoe";
  }
  curR() {
    const k = clamp(this.life / this.max, 0, 1);
    return this.r0 * clamp(this.t / 0.12, 0, 1) * (0.12 + 0.88 * k);
  }
  update(dt: number, run: Run) {
    this.t += dt;
    this.life -= dt;
    if (this.life <= 0) {
      this.alive = false;
      return;
    }
    this.tick -= dt;
    if (this.tick > 0) return;
    this.tick = 0.16;
    const rad = this.curR();
    for (const e of run.targets) {
      if (!e.alive) continue;
      if (dist(this.x, this.y, e.x, e.y) <= rad + e.radius * 0.5) {
        run.fieldDamage(e, this.dps * 0.16, 0, this.lvl);
        if (this.ice) e.applySlow(this.slow, 0.8);
        else if (this.burn > 0) e.applyBurn(this.burn, 1.4);
      }
    }
  }
}

export class Tornado extends WObj {
  kind = "tornado";
  life = 2.6;
  t = 0;
  pullR: number;
  hpCut: number;
  grindT = 0;
  cut = new Set<number>();
  constructor(x: number, y: number, public lvl: number, public dps: number, W: number, H: number) {
    super();
    this.x = clamp(x, 80, W - 80);
    this.y = clamp(y, 80, H - 80);
    this.pullR = 200 + 4 * B.weaponGrowth(lvl);
    this.hpCut = B.tornadoHpCut(lvl);
    this.src = "tornado";
  }
  update(dt: number, run: Run) {
    this.t += dt;
    this.life -= dt;
    if (this.life <= 0) {
      this.alive = false;
      return;
    }
    let grind = 0;
    this.grindT -= dt;
    if (this.dps > 0 && this.grindT <= 0) {
      this.grindT = 0.2;
      grind = this.dps;
    }
    for (const e of run.targets) {
      if (!e.alive) continue;
      const d = dist(this.x, this.y, e.x, e.y);
      if (d > this.pullR) continue;
      const boss = e.isBoss;
      if (!this.cut.has(e.id)) {
        this.cut.add(e.id);
        if (!boss && e.hp > 1) {
          let cut = this.hpCut;
          if (B.enemyWeightClass(e) === "tough") cut = 1 - (1 - cut) * 0.55;
          e.hp = Math.max(1, e.hp * cut);
          e.hitFlash = 0.16;
          run.fx.popup(e.x, e.y - e.radius - 6, `-%${Math.round((1 - cut) * 100)}`, COL.TORNADO2, 14, 0.6, true);
        }
      }
      if (grind > 0 && run.fieldDamage(e, grind, 0, this.lvl)) continue;
      const [dx, dy] = normDir(e.x, e.y, this.x, this.y);
      const spd = (boss ? 150 : 430) * clamp(d / 160, 0.25, 1);
      e.x += (dx * spd + -dy * spd * 0.42) * dt;
      e.y += (dy * spd + dx * spd * 0.42) * dt;
      e.x = clamp(e.x, 16, run.W - 16);
      e.y = clamp(e.y, 16, run.H - 16);
    }
    if (Math.random() < dt * 30) {
      const a = Math.random() * TAU, r = Math.random() * this.pullR * 0.8;
      run.fx.spark(this.x + Math.cos(a) * r, this.y + Math.sin(a) * r, COL.TORNADO2, -Math.sin(a) * 260, Math.cos(a) * 260 - 60, 0.45, 2.6, false, 0, 1);
    }
  }
}

export class FlyingAxe extends WObj {
  kind = "axe";
  phase: "out" | "back" = "out";
  spin = Math.random() * TAU;
  t = 0;
  hitSet = new Set<number>();
  tx: number;
  ty: number;
  constructor(public run: Run, public target: Target, public dmg: number, public k: number, public lvl: number) {
    super();
    this.x = run.player.x;
    this.y = run.player.y;
    this.tx = target.x;
    this.ty = target.y;
    this.src = "axe";
  }
  update(dt: number, run: Run) {
    const p = run.player;
    this.t += dt;
    this.spin += dt * 17;
    if (this.phase === "out") {
      if (this.target && this.target.alive) {
        this.tx = this.target.x;
        this.ty = this.target.y;
      }
      const [dx, dy] = normDir(this.x, this.y, this.tx, this.ty);
      this.x += dx * 620 * dt;
      this.y += dy * 620 * dt;
      if (dist(this.x, this.y, this.tx, this.ty) < 26 || this.t > 1.5) {
        this.phase = "back";
        this.hitSet.clear();
        run.fx.ring(this.x, this.y, COL.AXE, 10, 200, 0.28, 2.6 * this.k);
      }
    } else {
      const [dx, dy] = normDir(this.x, this.y, p.x, p.y);
      this.x += dx * 760 * dt;
      this.y += dy * 760 * dt;
      if (dist(this.x, this.y, p.x, p.y) < 26 || this.t > 4.7) {
        this.alive = false;
        return;
      }
    }
    const hr = 19 * this.k;
    for (const e of run.targets) {
      if (!e.alive || this.hitSet.has(e.id)) continue;
      if (dist(this.x, this.y, e.x, e.y) < hr + e.radius) {
        this.hitSet.add(e.id);
        run.weaponHit(e, this.dmg, 180, null, this.lvl);
        if (Math.random() < 0.5) run.fx.burst(this.x, this.y, lighten(COL.AXE, 0.3), 3, 150, 0.28, 2.6);
      }
    }
  }
}

export class WhipLash extends WObj {
  kind = "whip";
  life = 0.32;
  constructor(public run: Run, public ang: number, public length: number, public width: number, public spinDir: number) {
    super();
    this.x = run.player.x;
    this.y = run.player.y;
    this.src = "whip";
  }
  update(dt: number, run: Run) {
    this.x = run.player.x;
    this.y = run.player.y;
    this.life -= dt;
    if (this.life <= 0) this.alive = false;
  }
}

export class SwordSlash extends WObj {
  kind = "slash";
  life = 0.26;
  constructor(public run: Run, public ang: number, public radius: number, public half: number) {
    super();
    this.x = run.player.x;
    this.y = run.player.y;
    this.src = "emanet";
  }
  update(dt: number, run: Run) {
    this.x = run.player.x;
    this.y = run.player.y;
    this.life -= dt;
    if (this.life <= 0) this.alive = false;
  }
}

export class GhostBlade extends WObj {
  kind = "ghost";
  ang = -Math.PI / 2;
  state: "idle" | "out" | "back" = "idle";
  cd = 0.25 + Math.random() * 0.85;
  target: Target | null = null;
  tx = 0;
  ty = 0;
  hitSet = new Set<number>();
  t = 0;
  constructor(public idx: number, run: Run) {
    super();
    this.x = run.player.x;
    this.y = run.player.y - 30;
    this.src = "ghost_swords";
  }
  static slot(p: { x: number; y: number }, idx: number, n: number, tm: number): [number, number, number] {
    const a = tm * 1.5 + (idx * TAU) / Math.max(1, n);
    return [p.x + Math.cos(a) * C.GHOST_ORBIT_R, p.y - 10 + Math.sin(a) * C.GHOST_ORBIT_R * 0.55, a];
  }
  private hitAlong(run: Run, dmg: number, lvl: number, ox: number, oy: number) {
    for (const e of run.targets) {
      if (!e.alive || this.hitSet.has(e.id)) continue;
      if (segDist(e.x, e.y, ox, oy, this.x, this.y) < C.GHOST_HIT_R + e.radius) {
        this.hitSet.add(e.id);
        run.weaponHit(e, dmg, 70, null, lvl);
        if (Math.random() < 0.5) run.fx.burst(e.x, e.y, COL.GHOST2, 3, 150, 0.25, 2.2);
      }
    }
  }
  update(_dt: number, _run: Run) {}
  step(dt: number, run: Run, n: number, lvl: number, dmg: number, tm: number) {
    const p = run.player;
    this.t += dt;
    const [sx, sy] = GhostBlade.slot(p, this.idx, n, tm);
    if (this.state === "idle") {
      const k = Math.min(1, dt * 10);
      this.x += (sx - this.x) * k;
      this.y += (sy - this.y) * k;
      const want = Math.atan2(sy - (p.y - 10), sx - p.x) - 0.9;
      this.ang += Math.atan2(Math.sin(want - this.ang), Math.cos(want - this.ang)) * k;
      this.cd -= dt;
      if (this.cd <= 0) {
        const c = run.weaponTargets(B.ghostRange(lvl));
        if (c.length) {
          c.sort((a, b) => dist(p.x, p.y, a.x, a.y) - dist(p.x, p.y, b.x, b.y));
          this.target = c[Math.floor(Math.random() * Math.min(3, c.length))];
          this.tx = this.target.x;
          this.ty = this.target.y;
          this.state = "out";
          this.hitSet.clear();
          this.t = 0;
        } else this.cd = 0.2;
      }
    } else if (this.state === "out") {
      if (this.target && this.target.alive) {
        this.tx = this.target.x;
        this.ty = this.target.y;
      }
      const [dx, dy] = normDir(this.x, this.y, this.tx, this.ty);
      this.ang = Math.atan2(dy, dx);
      const ox = this.x, oy = this.y;
      this.x += dx * C.GHOST_SPEED * dt;
      this.y += dy * C.GHOST_SPEED * dt;
      this.hitAlong(run, dmg, lvl, ox, oy);
      if (dist(this.x, this.y, this.tx, this.ty) < 16 || this.t > 0.7) {
        this.state = "back";
        this.hitSet.clear();
        run.fx.ring(this.x, this.y, COL.GHOST, 8, 160, 0.25, 2.2);
      }
    } else {
      const [dx, dy] = normDir(this.x, this.y, sx, sy);
      this.ang = Math.atan2(dy, dx) + Math.PI;
      const ox = this.x, oy = this.y;
      this.x += dx * C.GHOST_SPEED * 0.85 * dt;
      this.y += dy * C.GHOST_SPEED * 0.85 * dt;
      this.hitAlong(run, dmg, lvl, ox, oy);
      if (dist(this.x, this.y, sx, sy) < 18 || this.t > 2.2) {
        this.state = "idle";
        this.cd = B.ghostCd(lvl);
      }
    }
  }
}

export class SpectralWolf extends WObj {
  kind = "wolf";
  vx = 0;
  vy = 0;
  face = 1;
  biteCd = 0.2 + Math.random() * 0.5;
  biteT = 0;
  runPh = Math.random() * TAU;
  target: Target | null = null;
  howlT = 0;
  frenzyT = 0;
  constructor(public idx: number, run: Run) {
    super();
    const a = Math.random() * TAU;
    this.x = run.player.x + Math.cos(a) * 40;
    this.y = run.player.y + Math.sin(a) * 40;
    this.src = "wolves";
  }
  update(_dt: number, _run: Run) {}
  step(dt: number, run: Run, pack: SpectralWolf[], lvl: number, dmg: number) {
    const p = run.player;
    this.biteCd -= dt;
    this.biteT = Math.max(0, this.biteT - dt);
    this.frenzyT = Math.max(0, this.frenzyT - dt);
    if (this.howlT > 0) {
      this.howlT -= dt;
      this.vx *= Math.max(0, 1 - dt * 12);
      this.vy *= Math.max(0, 1 - dt * 12);
      this.x += this.vx * dt;
      this.y += this.vy * dt;
      return;
    }
    if (!this.target || !this.target.alive || dist(p.x, p.y, this.target.x, this.target.y) > C.WOLF_LEASH + 60) {
      const taken = new Set(pack.filter((w) => w !== this && w.target).map((w) => w.target!.id));
      const c = run.weaponTargets(C.WOLF_LEASH);
      let best: Target | null = null, bs = 1e9;
      for (const e of c) {
        const s = dist(this.x, this.y, e.x, e.y) + (taken.has(e.id) ? 160 : 0);
        if (s < bs) {
          bs = s;
          best = e;
        }
      }
      this.target = best;
    }
    let spd = B.wolfSpeed(lvl) * (this.frenzyT > 0 ? 1 + C.WOLF_FRENZY_SPD : 1);
    let tx: number, ty: number;
    if (this.target) {
      tx = this.target.x;
      ty = this.target.y;
      const reach = this.target.radius + C.WOLF_BITE_R;
      if (dist(this.x, this.y, tx, ty) <= reach + 4) {
        if (this.biteCd <= 0) {
          this.biteCd = B.wolfBiteCd(lvl) * (this.frenzyT > 0 ? C.WOLF_FRENZY_BITE : 1);
          this.biteT = 0.18;
          run.weaponHit(this.target, dmg, 40, null, lvl);
          if (!this.target.isBoss) this.target.applySlow(0.75, 0.4);
          for (const o of run.targets) {
            if (o !== this.target && o.alive && dist(o.x, o.y, tx, ty) < C.WOLF_CLEAVE_R + o.radius) run.weaponHit(o, dmg * C.WOLF_CLEAVE_K, 30, null, lvl);
          }
          run.fx.burst(tx, ty, COL.WOLF2, 4, 140, 0.25, 2.4);
        }
        spd *= 0.15;
      }
    } else {
      const [ax, ay] = p.aim_dir;
      const side = (this.idx - (pack.length - 1) / 2) * 34;
      tx = p.x - ax * 60 - ay * side;
      ty = p.y - ay * 60 + ax * side;
      if (dist(this.x, this.y, tx, ty) < 20) spd = 0;
    }
    if (spd > 0) {
      const [dx, dy] = normDir(this.x, this.y, tx, ty);
      this.vx += (dx * spd - this.vx) * Math.min(1, dt * 8);
      this.vy += (dy * spd - this.vy) * Math.min(1, dt * 8);
    } else {
      this.vx *= Math.max(0, 1 - dt * 10);
      this.vy *= Math.max(0, 1 - dt * 10);
    }
    this.x += this.vx * dt;
    this.y += this.vy * dt;
    if (dist(this.x, this.y, p.x, p.y) > C.WOLF_LEASH * 1.8) {
      this.x = p.x + Math.random() * 80 - 40;
      this.y = p.y + Math.random() * 80 - 40;
    }
    this.x = clamp(this.x, 10, run.W - 10);
    this.y = clamp(this.y, 10, run.H - 10);
    if (Math.abs(this.vx) > 8) this.face = this.vx > 0 ? 1 : -1;
    this.runPh += dt * (4 + Math.hypot(this.vx, this.vy) * 0.03);
  }
}

export class MeteorStrike extends WObj {
  kind = "meteor";
  t = 0;
  boomT = -1;
  maxDelay: number;
  constructor(x: number, y: number, public radius: number, public dmg: number, public lvl: number, public delay: number) {
    super();
    this.x = x;
    this.y = y;
    this.maxDelay = Math.max(0.05, delay);
    this.src = "meteor";
  }
  update(dt: number, run: Run) {
    if (this.boomT >= 0) {
      this.boomT += dt;
      if (this.boomT > 0.45) this.alive = false;
      return;
    }
    this.t += dt;
    if (this.t < this.delay) return;
    this.boomT = 0;
    let hit = 0;
    for (const e of run.targets) {
      if (!e.alive) continue;
      const d = dist(this.x, this.y, e.x, e.y);
      if (d <= this.radius + e.radius * 0.6) {
        const k = 1 + 0.25 * (1 - clamp(d / Math.max(1, this.radius), 0, 1));
        run.weaponHit(e, this.dmg * k, 170, null, this.lvl);
        hit++;
      }
    }
    const fr = new FireRing(this.x, this.y, this.radius * 0.75, this.dmg * 0.22, 1.5, this.lvl, this.dmg * 0.1);
    fr.src = "meteor";
    run.addWObj(fr);
    run.fx.shockwave(this.x, this.y, this.radius * 1.15, COL.METEOR, 0.4, 6);
    run.fx.burst(this.x, this.y, COL.METEOR2, 14, 260, 0.5, 3.6);
    run.fx.burst(this.x, this.y, [90, 70, 60], 8, 140, 0.6, 4, 200, false);
    run.fx.shake(hit ? 4 : 2, 0.14);
    sfx("explosion", 0.38);
  }
}

export class SunBeam extends WObj {
  kind = "beam";
  t = 0;
  hitSets: Set<number>[];
  constructor(public run: Run, public ang: number, public n: number, public length: number, public dmg: number, public lvl: number) {
    super();
    this.hitSets = Array.from({ length: Math.max(1, n) }, () => new Set<number>());
    this.x = run.player.x;
    this.y = run.player.y;
    this.src = "beam";
  }
  update(dt: number, run: Run) {
    this.t += dt;
    this.x = run.player.x;
    this.y = run.player.y;
    if (this.t >= C.BEAM_SWEEP_T) {
      this.alive = false;
      return;
    }
    this.ang += (TAU / C.BEAM_SWEEP_T) * dt;
    let fxl = 3;
    for (let i = 0; i < this.n; i++) {
      const a = this.ang + (i * TAU) / this.n;
      const ex = this.x + Math.cos(a) * this.length, ey = this.y + Math.sin(a) * this.length;
      const hs = this.hitSets[i];
      for (const e of run.targets) {
        if (!e.alive || hs.has(e.id)) continue;
        if (segDist(e.x, e.y, this.x, this.y, ex, ey) < C.BEAM_WIDTH + e.radius) {
          hs.add(e.id);
          run.weaponHit(e, this.dmg, 45, null, this.lvl);
          if (fxl-- > 0) run.fx.spark(e.x, e.y, COL.BEAM2, Math.random() * 100 - 50, -30 - Math.random() * 50, 0.3, 2.4);
        }
      }
    }
  }
}

export class Hawk extends WObj {
  kind = "hawk";
  ang = 0;
  state: "circle" | "dive" | "climb" = "circle";
  cd = 0.6 + Math.random() * 0.8;
  target: Target | null = null;
  tx = 0;
  ty = 0;
  t = 0;
  flap = 0;
  alt = C.HAWK_ALT;
  constructor(public idx: number, run: Run) {
    super();
    this.x = run.player.x;
    this.y = run.player.y - 60;
    this.src = "hawk";
  }
  update(_dt: number, _run: Run) {}
  step(dt: number, run: Run, n: number, lvl: number, dmg: number, clock: number) {
    const p = run.player;
    this.t += dt;
    this.flap = Math.sin(clock * 9 + this.idx * 1.7);
    const a = clock * 1.1 + (this.idx * TAU) / Math.max(1, n);
    const ox = p.x + Math.cos(a) * C.HAWK_ORBIT_R, oy = p.y + Math.sin(a) * C.HAWK_ORBIT_R * 0.6;
    if (this.state === "circle") {
      const k = Math.min(1, dt * 4);
      this.x += (ox - this.x) * k;
      this.y += (oy - this.y) * k;
      this.ang = a + Math.PI / 2;
      this.alt += (C.HAWK_ALT - this.alt) * Math.min(1, dt * 4);
      this.cd -= dt;
      if (this.cd <= 0) {
        const c = run.weaponTargets(C.HAWK_RANGE);
        if (c.length) {
          let best = c[0];
          for (const e of c) if (e.hp > best.hp || (e.hp === best.hp && dist(p.x, p.y, e.x, e.y) < dist(p.x, p.y, best.x, best.y))) best = e;
          this.target = best;
          this.state = "dive";
          this.t = 0;
        } else this.cd = 0.3;
      }
    } else if (this.state === "dive") {
      if (this.target && this.target.alive) {
        this.tx = this.target.x;
        this.ty = this.target.y;
      }
      const [dx, dy] = normDir(this.x, this.y, this.tx, this.ty);
      this.ang = Math.atan2(dy, dx);
      this.x += dx * C.HAWK_SPEED * dt;
      this.y += dy * C.HAWK_SPEED * dt;
      this.alt = Math.max(0, this.alt - dt * 120);
      if (dist(this.x, this.y, this.tx, this.ty) < 14 || this.t > 0.9) {
        if (this.target && this.target.alive) run.weaponHit(this.target, dmg, 220, null, lvl);
        for (const o of run.targets) {
          if (o !== this.target && o.alive && dist(o.x, o.y, this.tx, this.ty) < C.HAWK_SPLASH_R + o.radius) run.weaponHit(o, dmg * C.HAWK_SPLASH_K, 120, null, lvl);
        }
        run.fx.burst(this.tx, this.ty, COL.HAWK2, 12, 220, 0.35, 3);
        run.fx.burst(this.tx, this.ty, scaleCol(COL.HAWK, 0.6), 6, 120, 0.6, 2.4, 140, false);
        run.fx.ring(this.tx, this.ty, COL.HAWK, 14, 200, 0.3, 2.6);
        sfx("whip", 0.28);
        this.state = "climb";
        this.t = 0;
      }
    } else {
      const [dx, dy] = normDir(this.x, this.y, ox, oy);
      this.ang = Math.atan2(dy, dx);
      this.x += dx * C.HAWK_SPEED * 0.6 * dt;
      this.y += dy * C.HAWK_SPEED * 0.6 * dt;
      this.alt = Math.min(C.HAWK_ALT, this.alt + dt * 90);
      if (dist(this.x, this.y, ox, oy) < 20 || this.t > 1.6) {
        this.state = "circle";
        this.cd = B.hawkCd(lvl);
      }
    }
    if (dist(this.x, this.y, p.x, p.y) > 900) {
      this.x = p.x;
      this.y = p.y - 60;
      this.state = "circle";
    }
  }
}

export class BatSwarmBat extends WObj {
  kind = "bat";
  t = 0;
  hits = 0;
  hitSet = new Set<number>();
  constructor(public run: Run, public a0: number, public spinDir: number, public dmg: number, public lvl: number) {
    super();
    this.x = run.player.x;
    this.y = run.player.y;
    this.src = "bats";
  }
  update(dt: number, run: Run) {
    this.t += dt;
    if (this.t >= C.BAT_LIFE || this.hits >= C.BAT_PIERCE) {
      this.alive = false;
      return;
    }
    const k = this.t / C.BAT_LIFE;
    const a = this.a0 + this.spinDir * k * 4.2;
    const rr = 24 + C.BAT_REACH * Math.sin(k * Math.PI * 0.5);
    const p = run.player;
    this.x = p.x + Math.cos(a) * rr;
    this.y = p.y + Math.sin(a) * rr * 0.85;
    for (const e of run.targets) {
      if (!e.alive || this.hitSet.has(e.id)) continue;
      if (dist(this.x, this.y, e.x, e.y) < 12 + e.radius) {
        this.hitSet.add(e.id);
        this.hits++;
        run.weaponHit(e, this.dmg, 50, null, this.lvl);
        run.batHeal(this.x, this.y);
        if (this.hits >= C.BAT_PIERCE) break;
      }
    }
  }
}

export class FrostNova extends WObj {
  kind = "nova";
  t = 0;
  constructor(x: number, y: number, public radius: number) {
    super();
    this.x = x;
    this.y = y;
    this.src = "nova";
  }
  update(dt: number) {
    this.t += dt;
    if (this.t > 0.55) this.alive = false;
  }
}

export class ThrownKnife extends WObj {
  kind = "knife";
  vx: number;
  vy: number;
  travel = 0;
  hitSet = new Set<number>();
  constructor(x: number, y: number, public ang: number, public dmg: number, public left: number, public lvl: number) {
    super();
    this.x = x;
    this.y = y;
    this.vx = Math.cos(ang) * C.KNIFE_SPEED;
    this.vy = Math.sin(ang) * C.KNIFE_SPEED;
    this.src = "knives";
  }
  update(dt: number, run: Run) {
    const ox = this.x, oy = this.y;
    this.x += this.vx * dt;
    this.y += this.vy * dt;
    this.travel += C.KNIFE_SPEED * dt;
    if (this.travel > C.KNIFE_RANGE || this.x < 0 || this.y < 0 || this.x > run.W || this.y > run.H) {
      this.alive = false;
      return;
    }
    for (const e of run.targets) {
      if (!e.alive || this.hitSet.has(e.id)) continue;
      if (segDist(e.x, e.y, ox, oy, this.x, this.y) < 9 + e.radius) {
        this.hitSet.add(e.id);
        run.weaponHit(e, this.dmg, 60, null, this.lvl);
        run.fx.spark(e.x, e.y, COL.KNIFE2, this.vx * 0.05, this.vy * 0.05, 0.2, 2);
        if (--this.left <= 0) {
          this.alive = false;
          return;
        }
      }
    }
  }
}

export class QuakeCharge extends WObj {
  kind = "quake";
  t = 0;
  boomT = -1;
  constructor(public run: Run, public radius: number, public dmg: number, public lvl: number) {
    super();
    this.x = run.player.x;
    this.y = run.player.y;
    this.src = "quake";
  }
  explode(run: Run) {
    this.boomT = 0;
    const stun = B.quakeStun(this.lvl);
    for (const e of run.targets) {
      if (!e.alive) continue;
      const d = dist(this.x, this.y, e.x, e.y);
      if (d <= this.radius + e.radius * 0.5) {
        const k = 1 + 0.25 * (1 - clamp(d / Math.max(1, this.radius), 0, 1));
        run.weaponHit(e, this.dmg * k, C.QUAKE_KB, null, this.lvl);
        if (!e.isBoss) e.applySlow(0.25, stun);
      }
    }
    run.fx.shockwave(this.x, this.y, this.radius, COL.QUAKE, 0.4, 7);
    run.fx.shockwave(this.x, this.y, this.radius * 0.6, COL.QUAKE2, 0.3, 4);
    run.fx.burst(this.x, this.y, COL.QUAKE_ROCK, 18, 260, 0.6, 4.2, 320, false);
    run.fx.burst(this.x, this.y, COL.QUAKE2, 10, 200, 0.35, 3);
    run.fx.shake(4, 0.16);
    sfx("bonk", 0.45);
  }
  update(dt: number, run: Run) {
    if (this.boomT >= 0) {
      this.boomT += dt;
      if (this.boomT > 0.45) this.alive = false;
      return;
    }
    this.t += dt;
    this.x = run.player.x;
    this.y = run.player.y;
    if (this.t >= C.QUAKE_CHARGE_T) this.explode(run);
    else if (Math.random() < dt * 14) {
      const a = Math.random() * TAU, rr = this.radius * (this.t / C.QUAKE_CHARGE_T) * (0.5 + Math.random() * 0.5);
      run.fx.spark(this.x + Math.cos(a) * rr, this.y + Math.sin(a) * rr, COL.QUAKE_ROCK, 0, -60, 0.4, 2.6, false);
    }
  }
}

// ------------------------------------------------------------------------
// ATEŞLEME
// ------------------------------------------------------------------------
export function fireWeapon(run: Run, key: string, lvl: number, targets: Target[]) {
  const p = run.player;
  const w = WEAPON_BY_KEY[key];
  const dmg = p.weaponDamage(key, lvl);
  let nearest = targets[0], nd = 1e18;
  for (const e of targets) {
    const d = (e.x - p.x) ** 2 + (e.y - p.y) ** 2;
    if (d < nd) {
      nd = d;
      nearest = e;
    }
  }
  const ang = Math.atan2(nearest.y - p.y, nearest.x - p.x);
  switch (key) {
    case "axe": {
      const n = B.weaponCount(lvl);
      const k = 0.92 + 0.021 * B.weaponGrowth(lvl);
      for (let i = 0; i < n; i++) {
        const tg = targets[Math.floor(Math.random() * targets.length)];
        const ax = new FlyingAxe(run, tg, dmg, k, lvl);
        const a0 = Math.random() * TAU;
        ax.x += Math.cos(a0) * 16;
        ax.y += Math.sin(a0) * 16;
        run.addWObj(ax);
      }
      run.fx.ring(p.x, p.y, w.color, 12, 220, 0.3, 3 * k);
      sfx("shoot_c", 0.42, 0);
      break;
    }
    case "whip": {
      const base = Math.atan2(p.aim_dir[1], p.aim_dir[0]);
      const n = B.weaponCount(lvl, "whip");
      const reach = B.whipReach(lvl), half = B.whipArc(lvl);
      const width = 7 + 0.5 * n;
      let hit = 0, fxl = 6;
      const cosH = Math.cos(half);
      for (let i = 0; i < n; i++) {
        const a = base + (i * TAU) / n;
        const ca = Math.cos(a), sa = Math.sin(a);
        run.addWObj(new WhipLash(run, a, reach, width, i % 2 === 0 ? 1 : -1));
        for (const e of run.targets) {
          if (!e.alive) continue;
          const d = dist(p.x, p.y, e.x, e.y);
          if (d > reach + e.radius || d < 1) continue;
          if (ca * ((e.x - p.x) / d) + sa * ((e.y - p.y) / d) < cosH) continue;
          run.weaponHit(e, dmg, C.WHIP_KB, null, lvl);
          if (fxl-- > 0) run.fx.burst(e.x, e.y, COL.WHIP2, 5, 190, 0.3, 2.6);
          hit++;
        }
      }
      if (hit) run.fx.shake(2.5, 0.1);
      sfx("whip", 0.42, 0);
      break;
    }
    case "emanet": {
      const rad = B.emanetRadius(lvl), half = B.emanetArc(lvl);
      const ca = Math.cos(ang), sa = Math.sin(ang), cosH = Math.cos(half);
      let hit = 0, fxl = 5;
      for (const e of run.targets) {
        if (!e.alive) continue;
        const d = dist(p.x, p.y, e.x, e.y);
        if (d > rad + e.radius) continue;
        if (d >= 1 && ca * ((e.x - p.x) / d) + sa * ((e.y - p.y) / d) < cosH) continue;
        let ed = dmg;
        if (isArmored(e)) {
          ed *= 1 + C.EMANET_ARMOR_BONUS;
          if ((e.armor || 0) > 0.005) ed /= Math.max(0.25, 1 - e.armor);
        }
        run.weaponHit(e, ed, C.EMANET_KB, null, lvl);
        if (fxl-- > 0) run.fx.spark(e.x, e.y, COL.EMANET2, Math.random() * 80 - 40, -20 - Math.random() * 40, 0.3, 2.4);
        hit++;
      }
      run.addWObj(new SwordSlash(run, ang, rad, half));
      if (hit) run.fx.shake(1.6, 0.07);
      sfx("whip", 0.3, 0);
      break;
    }
    case "zemzem": {
      const n = 1 + +(lvl >= 6) + +(lvl >= 13) + +(lvl >= 20);
      const rad = C.ZEMZEM_BASE_R + C.ZEMZEM_R_PER_LEVEL * B.weaponGrowth(lvl);
      const cam = run.camRect(-60);
      const spots: [number, number][] = [];
      const pool = targets.filter((e) => e.x > cam.l && e.x < cam.r && e.y > cam.t && e.y < cam.b);
      const keyd = new Map<Target, number>();
      for (const e of pool) keyd.set(e, dist(p.x, p.y, e.x, e.y) * (0.7 + Math.random() * 0.6));
      pool.sort((a, b) => keyd.get(a)! - keyd.get(b)!);
      for (const e of pool) {
        if (spots.every(([sx, sy]) => dist(e.x, e.y, sx, sy) > rad * 1.15)) spots.push([e.x, e.y]);
        if (spots.length >= n) break;
      }
      let tries = 0;
      while (spots.length < n && tries < 40) {
        tries++;
        const a = Math.random() * TAU, r2 = C.ZEMZEM_THROW * (0.35 + Math.random() * 0.65);
        const sx = clamp(p.x + Math.cos(a) * r2, cam.l, cam.r), sy = clamp(p.y + Math.sin(a) * r2, cam.t, cam.b);
        if (spots.every(([ox, oy]) => dist(sx, sy, ox, oy) > rad * 0.9) || tries > 30) spots.push([sx, sy]);
      }
      for (const [sx, sy] of spots) {
        run.addWObj(new WaterZone(sx, sy, rad, dmg, C.ZEMZEM_LIFE, lvl, run.W, run.H));
        run.fx.burst(sx, sy, COL.ZEMZEM2, 16, 210, 0.45, 3);
        run.fx.shockwave(sx, sy, rad, COL.ZEMZEM, 0.35, 4);
      }
      sfx("splash", 0.5, 0);
      break;
    }
    case "tornado": {
      let bx = 0, by = 0;
      for (const e of targets) {
        bx += e.x;
        by += e.y;
      }
      bx /= targets.length;
      by /= targets.length;
      const d0 = dist(bx, by, p.x, p.y);
      if (d0 < 240) {
        const a0 = d0 > 1 ? Math.atan2(by - p.y, bx - p.x) : ang;
        bx = p.x + Math.cos(a0) * 260;
        by = p.y + Math.sin(a0) * 260;
      }
      const tor = new Tornado(bx, by, lvl, dmg, run.W, run.H);
      run.addWObj(tor);
      run.fx.flash(COL.TORNADO, 0.18);
      run.fx.shockwave(tor.x, tor.y, tor.pullR * 0.5, COL.TORNADO, 0.6, 6);
      run.fx.shake(7, 0.35);
      run.fx.popup(tor.x, tor.y - 170, t("fx.tornado"), COL.TORNADO2, 26, 1.2, true);
      sfx("vortex", 0.7, 0);
      break;
    }
    case "tesla": {
      const n = B.teslaTargets(lvl);
      let cur: Target | null = nearest;
      const pts: number[][] = [[p.x, p.y - 8]];
      const done = new Set<number>();
      let hd = dmg;
      for (let i = 0; i < n && cur; i++) {
        done.add(cur.id);
        pts.push([cur.x, cur.y]);
        run.weaponHit(cur, hd, 30, null, lvl);
        if (!cur.isBoss) cur.applySlow(0.45, 0.3);
        run.fx.burst(cur.x, cur.y, COL.TESLA2, 4, 160, 0.22, 2.2);
        hd *= C.TESLA_FALLOFF;
        let nxt: Target | null = null, best = C.TESLA_JUMP_R;
        for (const e of run.targets) {
          if (!e.alive || done.has(e.id)) continue;
          const d = dist(cur.x, cur.y, e.x, e.y);
          if (d < best) {
            nxt = e;
            best = d;
          }
        }
        cur = nxt;
      }
      for (let i = 0; i < pts.length - 1; i++) {
        run.fx.bolt(zigzag(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], 6, 14), COL.TESLA, 0.22, 3);
      }
      sfx("lightning", 0.36, 0.06);
      break;
    }
    case "meteor": {
      const rad = B.meteorRadius(lvl);
      const cam = run.camRect(-40);
      let pool = targets.filter((e) => e.x > cam.l && e.x < cam.r && e.y > cam.t && e.y < cam.b);
      if (!pool.length) pool = targets.slice();
      const sample = pool.length <= 40 ? pool : pool.sort(() => Math.random() - 0.5).slice(0, 40);
      const crowd = new Map<Target, number>();
      for (const e of sample) {
        let c = 0;
        for (const o of sample) if (dist(o.x, o.y, e.x, e.y) < rad) c++;
        crowd.set(e, -c + Math.random() * 0.8);
      }
      sample.sort((a, b) => crowd.get(a)! - crowd.get(b)!);
      const spots: [number, number][] = [];
      for (const e of sample) {
        if (spots.every(([sx, sy]) => dist(e.x, e.y, sx, sy) > rad)) spots.push([e.x, e.y]);
        if (spots.length >= B.meteorCount(lvl)) break;
      }
      spots.forEach(([sx, sy], i) => run.addWObj(new MeteorStrike(sx, sy, rad, dmg, lvl, C.METEOR_DELAY + 0.16 * i)));
      sfx("blaze", 0.3, 0.05);
      break;
    }
    case "bats": {
      const n = B.batCount(lvl);
      const a0 = Math.random() * TAU;
      for (let i = 0; i < n; i++) run.addWObj(new BatSwarmBat(run, a0 + (i * TAU) / n, i % 2 === 0 ? 1 : -1, dmg, lvl));
      sfx("dash", 0.22, 0.05);
      break;
    }
    case "nova": {
      const rad = B.novaRadius(lvl), frz = B.novaFreeze(lvl);
      for (const e of run.targets) {
        if (!e.alive) continue;
        if (dist(p.x, p.y, e.x, e.y) <= rad + e.radius) {
          run.weaponHit(e, dmg, 120, null, lvl);
          e.applySlow(e.isBoss ? 0.6 : 0.02, frz);
        }
      }
      run.addWObj(new FrostNova(p.x, p.y, rad));
      sfx("ice_step", 0.6, 0);
      break;
    }
    case "knives": {
      const base = Math.atan2(p.aim_dir[1], p.aim_dir[0]);
      const n = B.knifeCount(lvl);
      const fan = 0.7 + 0.04 * n;
      for (let i = 0; i < n; i++) {
        const a = base + (i - (n - 1) / 2) * (fan / Math.max(1, n - 1));
        run.addWObj(new ThrownKnife(p.x + Math.cos(a) * 12, p.y + Math.sin(a) * 12, a, dmg, B.knifePierce(lvl), lvl));
      }
      sfx("whip", 0.22, 0.04);
      break;
    }
    case "quake":
      run.addWObj(new QuakeCharge(run, B.quakeRadius(lvl), dmg, lvl));
      sfx("ice_step", 0.3, 0.08);
      break;
    case "beam":
      run.addWObj(new SunBeam(run, Math.atan2(p.aim_dir[1], p.aim_dir[0]), B.beamCount(lvl), B.beamLen(lvl), dmg, lvl));
      run.fx.ring(p.x, p.y, COL.BEAM, 14, 200, 0.35, 3);
      sfx("blaze", 0.4, 0);
      break;
  }
}

export function isArmored(e: Target) {
  if ((e.armor || 0) > 0.005) return true;
  if ((e as any).guardOf) return true;
  if ((e as any).isMini || e.isBoss) return true;
  return ["tank", "brute", "elite", "shieldman"].includes(e.kind);
}

export function bookSlotPos(p: { x: number; y: number; book_angle: number }, i: number, n: number): [number, number, number] {
  const a = p.book_angle + (i * TAU) / Math.max(1, n);
  return [p.x + Math.cos(a) * C.BOOK_ORBIT_R, p.y + Math.sin(a) * C.BOOK_ORBIT_R * 0.72, a];
}

/** Bekleme süreli silahları ateşler. */
export function updateTimedWeapons(run: Run, dt: number) {
  const p = run.player;
  if (!p.alive) return;
  let targets: Target[] | null = null;
  for (const key of Object.keys(p.weapons)) {
    const w = WEAPON_BY_KEY[key];
    if (!w || w.passive) continue;
    const lvl = p.weapons[key];
    p.weapon_timers[key] = (p.weapon_timers[key] || 0) - dt;
    if (p.weapon_timers[key] > 0) continue;
    if (!targets) targets = run.weaponTargets(C.WEAPON_RANGE);
    if (!targets.length) {
      p.weapon_timers[key] = 0;
      continue;
    }
    DMG.src = key;
    fireWeapon(run, key, lvl, targets);
    p.weapon_timers[key] = B.weaponCooldown(w, lvl) / (1 + p.weapon_speed_bonus);
  }
  DMG.src = "other";
}

/** Sürekli (pasif) silahlar: kalkan, pentagram, papuç, buz izi, pelerin, minyonlar. */
export function updatePassiveWeapons(run: Run, dt: number) {
  const p = run.player;
  if (!p.alive) return;
  const blvl = p.weapons.book || 0;
  if (blvl > 0) {
    DMG.src = "book";
    const n = B.weaponCount(blvl);
    p.book_angle += dt * C.BOOK_SPIN;
    while (p.book_charges.length < n) p.book_charges.push(0);
    if (p.book_charges.length > n) p.book_charges.length = n;
    for (let i = 0; i < n; i++) {
      if (p.book_charges[i] > 0) {
        p.book_charges[i] = Math.max(0, p.book_charges[i] - dt);
        if (p.book_charges[i] <= 0) {
          const [bx, by] = bookSlotPos(p, i, n);
          run.fx.ring(bx, by, COL.SHIELD, 8, 120, 0.3, 2.2);
        }
      }
    }
    const bdmg = p.weaponDamage("book", blvl) * dt;
    for (let i = 0; i < n; i++) {
      if (p.book_charges[i] > 0) continue;
      const [bx, by] = bookSlotPos(p, i, n);
      for (const e of run.targets) {
        if (e.alive && dist(bx, by, e.x, e.y) < e.radius + 15) run.fieldDamage(e, bdmg * 6, 0, blvl);
      }
    }
  }
  const plvl = p.weapons.pentagram || 0;
  if (plvl > 0) {
    DMG.src = "pentagram";
    p.penta_angle += dt * 0.65;
    p.penta_tick -= dt;
    if (p.penta_tick <= 0) {
      p.penta_tick = C.PENTA_TICK;
      const rad = B.pentaRadius(plvl);
      const dps = p.weaponDamage("pentagram", plvl);
      const tick = dps * C.PENTA_TICK, searFlat = dps * C.PENTA_SEAR_K;
      const searFrac = B.pentaSearHpFrac(plvl), searCap = B.pentaSearCap(plvl), batTick = B.pentaBatTickMult(plvl);
      let hit = 0, seared = 0, sparks = 3;
      const inside = new Set<number>();
      for (const e of run.targets) {
        if (!e.alive) continue;
        if (dist(p.x, p.y, e.x, e.y) > rad + e.radius * 0.5) continue;
        inside.add(e.id);
        const isBat = (e as any).shape === "blue";
        let batCapped = false;
        if (!run.pentaInside.has(e.id)) {
          let sear = searFlat;
          if (!e.isBoss) sear += Math.max(0, e.hp) * searFrac;
          let cap = searCap;
          if (isBat) cap = Math.min(cap, B.pentaBatSearCap(plvl));
          if (cap < 1 && !e.isBoss) {
            const ehp = Math.max(0, e.hp);
            if (sear > ehp * cap) {
              sear = ehp * cap;
              batCapped = isBat;
            }
          }
          if (seared < 4) {
            seared++;
            run.fx.spark(e.x, e.y - 6, COL.PENTA2, Math.random() * 80 - 40, -40 - Math.random() * 50, 0.35, 2.8);
          }
          if (run.fieldDamage(e, sear, 0, null)) continue;
          if (batCapped) {
            hit++;
            continue;
          }
        }
        run.fieldDamage(e, tick * (isBat ? batTick : 1), 0, null);
        hit++;
        if (sparks > 0 && Math.random() < 0.4) {
          sparks--;
          run.fx.spark(e.x, e.y, COL.PENTA2, Math.random() * 28 - 14, -34 - Math.random() * 36, 0.4, 2.2);
        }
      }
      run.pentaInside = inside;
      if (seared) sfx("blaze", 0.22, 0.05);
      void hit;
    }
  }
  const slvl = p.weapons.shoe || 0;
  if (slvl > 0) {
    if (!p.shoe_last) p.shoe_last = [p.x, p.y];
    p.shoe_idle += dt;
    if (dist(p.x, p.y, p.shoe_last[0], p.shoe_last[1]) >= C.SHOE_STEP || p.shoe_idle >= C.SHOE_IDLE_EVERY) {
      p.shoe_last = [p.x, p.y];
      p.shoe_idle = 0;
      const dps = p.weaponDamage("shoe", slvl);
      run.addWObj(new FireRing(p.x, p.y, B.shoeRadius(slvl), dps, B.shoeLife(slvl), slvl, dps * 0.3));
      sfx("blaze", 0.16, 0.06);
    }
  }
  const flvl = p.weapons.frost || 0;
  if (flvl > 0) {
    if (!p.frost_last) p.frost_last = [p.x, p.y];
    p.frost_idle += dt;
    if (dist(p.x, p.y, p.frost_last[0], p.frost_last[1]) >= C.SHOE_STEP || p.frost_idle >= C.SHOE_IDLE_EVERY) {
      p.frost_last = [p.x, p.y];
      p.frost_idle = 0;
      const dps = p.weaponDamage("frost", flvl);
      run.addWObj(new FireRing(p.x, p.y, B.shoeRadius(flvl), dps, B.shoeLife(flvl), flvl, 0, true, Math.max(0.3, 0.62 - 0.013 * B.weaponGrowth(flvl))));
      sfx("ice_step", 0.16, 0.06);
    }
  }
  const clvl = p.weapons.cloak || 0;
  if (clvl > 0) {
    if (p.invis_t > 0) {
      p.invis_t = Math.max(0, p.invis_t - dt);
      if (p.invis_t <= 0) {
        p.cloak_timer = B.cloakCooldown(clvl);
        run.fx.ring(p.x, p.y, COL.CLOAK2, 18, 260, 0.45, 3);
        run.fx.popup(p.x, p.y - 46, t("fx.visible"), COL.CLOAK2, 16, 0.8, true);
        sfx("guard", 0.35);
      }
    } else {
      p.cloak_timer -= dt;
      if (p.cloak_timer <= 0) {
        p.invis_t = B.cloakDuration(clvl);
        p.cloak_timer = B.cloakCooldown(clvl);
        run.fx.popup(p.x, p.y - 64, t("fx.invisible"), COL.CLOAK2, 26, 1.4, true);
        run.fx.ring(p.x, p.y, COL.CLOAK, 26, 320, 0.6, 3.4);
        run.fx.shockwave(p.x, p.y, 150, COL.CLOAK2, 0.45, 4);
        sfx("dash", 0.55);
      }
    }
  }
  run.minionT += dt;
  const glvl = p.weapons.ghost_swords || 0;
  if (glvl > 0) {
    DMG.src = "ghost_swords";
    const n = B.ghostCount(glvl);
    while (run.ghostBlades.length < n) run.ghostBlades.push(run.trackObj(new GhostBlade(run.ghostBlades.length, run)));
    while (run.ghostBlades.length > n) run.dropObj(run.ghostBlades.pop()!);
    const gd = p.weaponDamage("ghost_swords", glvl);
    for (const gb of run.ghostBlades) gb.step(dt, run, n, glvl, gd, run.minionT);
  }
  const hlvl = p.weapons.hawk || 0;
  if (hlvl > 0) {
    DMG.src = "hawk";
    const n = B.hawkCount(hlvl);
    while (run.hawks.length < n) run.hawks.push(run.trackObj(new Hawk(run.hawks.length, run)));
    while (run.hawks.length > n) run.dropObj(run.hawks.pop()!);
    const hd = p.weaponDamage("hawk", hlvl);
    for (const hk of run.hawks) hk.step(dt, run, n, hlvl, hd, run.minionT);
  }
  run.batHealBudget = Math.min(p.max_hp * C.BAT_HEAL_RATE * 2, run.batHealBudget + p.max_hp * C.BAT_HEAL_RATE * dt);
  const wlvl = p.weapons.wolves || 0;
  if (wlvl > 0) {
    DMG.src = "wolves";
    const n = B.wolfCount(wlvl);
    while (run.wolves.length < n) {
      run.wolves.push(run.trackObj(new SpectralWolf(run.wolves.length, run)));
      if (run.wolves.length > 1) run.fx.popup(p.x, p.y - 58, t("fx.wolf_join"), COL.WOLF2, 16, 1, true);
    }
    while (run.wolves.length > n) run.dropObj(run.wolves.pop()!);
    const wd = p.weaponDamage("wolves", wlvl);
    run.wolfHowlCd -= dt;
    if (run.wolfHowlCd <= 0 && run.weaponTargets(C.WOLF_LEASH).length) {
      run.wolfHowlCd = C.WOLF_HOWL_CD;
      for (const wf of run.wolves) {
        wf.howlT = C.WOLF_HOWL_T;
        wf.frenzyT = C.WOLF_HOWL_T + C.WOLF_FRENZY_T;
        run.fx.shockwave(wf.x, wf.y, 90, COL.WOLF2, 0.45, 3);
      }
      const lead = run.wolves[0];
      run.fx.popup(lead.x, lead.y - 46, t("fx.howl"), COL.WOLF2, 22, 1.2, true);
      sfx("roar", 0.45, 0.05);
    }
    for (const wf of run.wolves) wf.step(dt, run, run.wolves, wlvl, wd);
  }
  DMG.src = "other";
}

/** Gelen düşman mermisi bir kalkana değdi mi? */
export function blockWithBook(run: Run, proj: { x: number; y: number; r: number; alive: boolean }) {
  const p = run.player;
  const lvl = p.weapons.book || 0;
  if (lvl <= 0 || !p.book_charges.length) return false;
  const n = B.weaponCount(lvl);
  const rech = Math.max(1.4, C.BOOK_RECHARGE - C.BOOK_RECHARGE_PER_LEVEL * B.weaponGrowth(lvl));
  for (let i = 0; i < Math.min(n, p.book_charges.length); i++) {
    if (p.book_charges[i] > 0) continue;
    const [bx, by] = bookSlotPos(p, i, n);
    if (dist(proj.x, proj.y, bx, by) < proj.r + 17) {
      p.book_charges[i] = rech;
      proj.alive = false;
      run.fx.ring(bx, by, COL.SHIELD, 14, 210, 0.35, 3);
      run.fx.burst(bx, by, COL.SHIELD2, 8, 140, 0.3, 2.4);
      sfx("guard", 0.34, 0.02);
      return true;
    }
  }
  return false;
}
