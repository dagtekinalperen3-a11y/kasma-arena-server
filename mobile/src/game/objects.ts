/**
 * Oyuncu mermisi, yerdeki eşyalar, tuzaklar, sandıklar, portal.
 */
import { clamp, dist, normDir, lerp, RGB } from "../core/util";
import { GD } from "./data";
import type { Player } from "./player";

const C = GD;

export class PlayerProjectile {
  alive = true;
  view: any = null;
  r = 6;
  life = 1.15;
  hitSet = new Set<number>();
  spin = Math.random() * 6.28;
  trailAcc = 0;
  wsrc: string | null = null;
  constructor(
    public x: number,
    public y: number,
    public vx: number,
    public vy: number,
    public dmg: number,
    public hitsLeft: number,
    public critChance: number,
    public critMult: number,
    public homing = 0,
    public style = "bolt",
    public color: RGB | number[] = [150, 210, 255],
    public accent: RGB | number[] = [255, 255, 255],
  ) {}
  steerToward(tx: number, ty: number, dt: number) {
    if (this.homing <= 0) return;
    const sp = Math.hypot(this.vx, this.vy);
    if (sp < 1e-4) return;
    const [dx, dy] = normDir(this.x, this.y, tx, ty);
    const turn = Math.min(1, (3 + this.homing * 2) * dt);
    const nx = lerp(this.vx / sp, dx, turn), ny = lerp(this.vy / sp, dy, turn);
    const nl = Math.hypot(nx, ny);
    if (nl > 1e-4) {
      this.vx = (nx / nl) * sp;
      this.vy = (ny / nl) * sp;
    }
  }
  update(dt: number, W: number, H: number) {
    this.x += this.vx * dt;
    this.y += this.vy * dt;
    this.life -= dt;
    this.spin += dt * 10;
    if (this.life <= 0 || this.x < -30 || this.x > W + 30 || this.y < -30 || this.y > H + 30) this.alive = false;
  }
}

export type PickupKind = "coin" | "xp" | "heart";

export class Pickup {
  vx = (Math.random() - 0.5) * 100;
  vy = (Math.random() - 0.5) * 100;
  bob = Math.random() * 6.28;
  collected = false;
  dead = false;
  spawnT = 0;
  magnet = false;
  view: any = null;
  constructor(public x: number, public y: number, public kind: PickupKind, public value: number) {}
  update(dt: number, p: Player) {
    this.spawnT += dt;
    if (this.magnet && p.alive) {
      const d = dist(this.x, this.y, p.x, p.y);
      const [dx, dy] = normDir(this.x, this.y, p.x, p.y);
      const spd = lerp(760, 1500, clamp(this.spawnT * 0.8, 0, 1));
      this.x += dx * spd * dt;
      this.y += dy * spd * dt;
      this.vx = this.vy = 0;
      if (d < 38 || d < spd * dt) this.collected = true;
      return;
    }
    const k = 1 - Math.min(1, dt * 3);
    this.vx *= k;
    this.vy *= k;
    this.x += this.vx * dt;
    this.y += this.vy * dt;
    if (this.kind === "heart" && this.spawnT > 14) {
      this.dead = true;
      return;
    }
    if (this.spawnT > 0.15 && p.alive) {
      let d = dist(this.x, this.y, p.x, p.y);
      let pr: number;
      if (this.kind === "coin") pr = Math.max(p.radius + 18, p.effPickup() * C.COIN_PICKUP_FACTOR);
      else if (this.kind === "heart") pr = p.effPickup() * 0.8;
      else pr = p.effPickup();
      if (d < pr) {
        const pull = Math.pow(clamp(1 - d / pr, 0, 1), 0.6);
        const spd = lerp(70, 620, pull);
        const [dx, dy] = normDir(this.x, this.y, p.x, p.y);
        this.x += dx * spd * dt;
        this.y += dy * spd * dt;
        d = dist(this.x, this.y, p.x, p.y);
      }
      if (d < C.PICKUP_GRAB_R) this.collected = true;
    }
  }
}

/** Mıknatıs / seviye taşı: aynı toplama davranışı. */
export class BigDrop {
  t = Math.random() * 6.28;
  collected = false;
  alive = true;
  view: any = null;
  constructor(public kind: "magnet" | "level", public x: number, public y: number, W: number, H: number) {
    this.x = clamp(x, 30, W - 30);
    this.y = clamp(y, 30, H - 30);
  }
  update(dt: number, p: Player) {
    this.t += dt;
    if (!p.alive) return;
    const pr = Math.max(46, p.effPickup() * 1.3);
    const d = dist(this.x, this.y, p.x, p.y);
    if (d < pr) {
      const pull = Math.pow(clamp(1 - d / pr, 0, 1), 0.5);
      const [dx, dy] = normDir(this.x, this.y, p.x, p.y);
      const spd = lerp(120, 900, pull);
      this.x += dx * spd * dt;
      this.y += dy * spd * dt;
    }
    if (d < 26) {
      this.collected = true;
      this.alive = false;
    }
  }
}

export class Hazard {
  t = 0;
  exploded = false;
  linger = 0;
  alive = true;
  view: any = null;
  constructor(
    public x: number,
    public y: number,
    public r: number,
    public delay: number,
    public dmg: number,
    public owner: any = null,
    public color: RGB | number[] = [255, 70, 60],
    public kind: string = "blast",
  ) {}
}

export class BossChest {
  r = 26;
  t = 0;
  openT = 0;
  opened = false;
  taken = false;
  alive = true;
  bob = Math.random() * 6.28;
  view: any = null;
  legend = false;
  constructor(public x: number, public y: number, public bossName = "") {}
  inRange(p: Player) {
    return dist(this.x, this.y, p.x, p.y) < this.r + p.radius + 10;
  }
  update(dt: number, p: Player) {
    this.t += dt;
    if (this.opened) {
      this.openT += dt;
      if (this.openT > 1.1) this.alive = false;
      return;
    }
    if (p.alive && this.inRange(p)) {
      this.opened = true;
      this.openT = 0;
    }
  }
}

export class MapKey {
  t = Math.random() * 5;
  taken = false;
  gone = false;
  takeT = 0;
  view: any = null;
  constructor(public x: number, public y: number) {}
  update(dt: number) {
    this.t += dt;
    if (this.taken) {
      this.takeT += dt;
      if (this.takeT > 0.6) this.gone = true;
    }
  }
}

export class HellPortal {
  r = 46;
  t = 0;
  view: any = null;
  constructor(public x: number, public y: number) {}
  update(dt: number) {
    this.t += dt;
  }
  inRange(p: Player) {
    return dist(this.x, this.y, p.x, p.y) < this.r + 70;
  }
}
