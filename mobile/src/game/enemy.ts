/**
 * Yaratık — Python `Enemy` sınıfının karşılığı (davranış birebir).
 */
import { clamp, dist, normDir, mixCol, RGB } from "../core/util";
import * as B from "./balance";
import { GD, ENEMY_DEFS, ENEMY_COLORS, MAP_ENEMIES, HELL_ENEMIES, VariantDef } from "./data";
import type { FX } from "./fx";
import type { Player } from "./player";
import { sfx } from "../core/audio";
import { t, tx } from "../core/i18n";

const C = GD;
const SHAPE_ALIAS: Record<string, string> = { bomber: "bomber", healer: "healer", wizard: "wizard", stinger: "stinger" };
const HITBOX: Record<string, number> = C.ENEMY_HITBOX_FACTOR;
const MAP_SHOT_COLORS: Record<string, RGB> = C.MAP_SHOT_COLORS;

export class EnemyProjectile {
  alive = true;
  view: any = null;
  constructor(
    public x: number,
    public y: number,
    public vx: number,
    public vy: number,
    public dmg: number,
    public color: RGB | number[] = [235, 210, 70],
    public r = 6,
    public life = 4,
    public target: any = null,
    public turn = 0,
    public accel = 0,
    public owner: any = null,
    public poison = 0,
    public style = "orb",
  ) {}
  update(dt: number, W: number, H: number) {
    if (this.target && this.turn > 0 && this.target.alive) {
      let sp = Math.hypot(this.vx, this.vy);
      if (sp > 1) {
        let cur = Math.atan2(this.vy, this.vx);
        const want = Math.atan2(this.target.y - this.y, this.target.x - this.x);
        let diff = want - cur;
        diff = ((diff + Math.PI) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) - Math.PI;
        cur += clamp(diff, -this.turn * dt, this.turn * dt);
        sp += this.accel * dt;
        this.vx = Math.cos(cur) * sp;
        this.vy = Math.sin(cur) * sp;
      }
      this.turn = Math.max(0, this.turn - dt * 1.45);
    }
    this.x += this.vx * dt;
    this.y += this.vy * dt;
    this.life -= dt;
    if (this.life <= 0 || this.x < -30 || this.x > W + 30 || this.y < -30 || this.y > H + 30) this.alive = false;
  }
}

export interface EnemyCtx {
  fx: FX;
  player: Player;
  projectiles: EnemyProjectile[];
  enemies: Enemy[];
  W: number;
  H: number;
  kill: (e: Enemy) => void;
}

let ENEMY_ID = 1;

export class Enemy {
  id = ENEMY_ID++;
  kind: string;
  variant: string | null;
  hellish: boolean;
  mapVar: boolean;
  shotStyle: string;
  shape: string;
  name: string;
  x: number;
  y: number;
  max_hp: number;
  hp: number;
  speed: number;
  dmg: number;
  armor: number;
  radius: number;
  coin: number;
  xp: number;
  score: number;
  contact_dps: number;
  hit_r: number;
  color: RGB;
  rage: number;
  mutant = false;
  fuse_t = 0;
  exploded = false;
  isMini: boolean;
  isBoss = false;
  guards: Enemy[] | null;
  guardOf: Enemy | null = null;
  guardSlot = 0;
  blockFlash = 0;
  alive = true;
  hitFlash = 0;
  spawnT = 0;
  shootCd = 0.6 + Math.random() * 0.8;
  healCd = 0.3 + Math.random() * 0.7;
  healFlash = 0;
  dashCd = 1.2 + Math.random() * 1.2;
  dashT = 0;
  dashDx = 0;
  dashDy = 0;
  knockX = 0;
  knockY = 0;
  wobble = Math.random() * 6.28;
  burnTimer = 0;
  burnDps = 0;
  burnAcc = 0;
  slowTimer = 0;
  slowMult = 1;
  touchCd = 0;
  poisonDps = 0;
  poisonAcc = 0;
  faceX = 0;
  faceY = 1;
  walk = Math.random() * 6.28;
  fearTimer = 0;
  fearVuln = 0;
  splitGen = 0;
  raised = false;
  necroCd = 2 + Math.random() * 1.5;
  phased = false;
  phaseT: number;
  warpCd = 0;
  oneshotUsed = false;
  deathCounted = false;
  view: any = null;
  // görsel
  scaleK = 1;

  constructor(kind: string | null, x: number, y: number, waveMult: number, diffMult = 1, wave = 1, variant: string | null = null, biome: B.Biome = "arena") {
    const v: VariantDef | undefined = variant ? HELL_ENEMIES[variant] || MAP_ENEMIES[variant] : undefined;
    if (v) kind = v.base;
    const k = kind as string;
    const d = ENEMY_DEFS[k];
    this.kind = k;
    this.variant = variant;
    this.hellish = !!(variant && HELL_ENEMIES[variant]);
    this.mapVar = !!(variant && MAP_ENEMIES[variant]);
    this.shotStyle = v?.shot ?? "orb";
    this.shape = v ? v.shape : SHAPE_ALIAS[k] || k;
    this.name = v ? tx("en." + variant, v.name) : tx("en." + k, k);
    this.x = x;
    this.y = y;
    const spdWave = biome === "hell" ? B.hellSpeedWave(wave) : wave;
    const dmgWave = biome === "hell" ? B.hellDmgWave(wave) : wave;
    let prHp: number, prDmg: number, prSpd: number, prArm: number;
    if (biome === "hell") {
      const [h, dm, s] = B.hellPressure(wave);
      prHp = h;
      prDmg = dm * C.HELL_DMG_BOOST;
      prSpd = s;
      prArm = 0;
    } else [prHp, prDmg, prSpd, prArm] = B.arenaPressure(wave);
    const hpVar = v?.hp ?? 1, dmgVar = v?.dmg ?? 1;
    this.max_hp = d.hp * waveMult * hpVar * prHp * C.ENEMY_HP_TUNE;
    this.hp = this.max_hp;
    this.speed = d.speed * B.waveSpeedMult(spdWave) * prSpd;
    const dmgMult = B.lateWaveDmgMult(dmgWave, biome === "hell" ? C.LATE_DMG_COEF_HELL : undefined);
    this.dmg = d.dmg * dmgMult * diffMult * dmgVar * prDmg * C.ENEMY_DMG_TUNE;
    this.armor = biome === "hell" ? B.hellArmor(wave) : prArm;
    this.radius = d.radius * (v?.radius ?? 1);
    this.coin = d.coin;
    this.xp = d.xp;
    this.score = d.score;
    this.contact_dps = d.contact_dps * dmgMult * diffMult * dmgVar * prDmg * C.ENEMY_DMG_TUNE;
    if (k === "stinger") {
      this.speed = Math.min(this.speed, B.BASE_SPEED * C.STINGER_SPEED_CAP);
      this.dmg = Math.min(this.dmg, d.dmg * C.STINGER_DMG_CAP);
      this.contact_dps = Math.min(this.contact_dps, d.contact_dps * C.STINGER_DMG_CAP);
    }
    const hbShape = this.mapVar ? k : this.shape;
    this.hit_r = this.radius * (HITBOX[hbShape] ?? 1);
    this.color = (v ? v.color : ENEMY_COLORS[k]) as RGB;
    if (this.shape === "red" && !v) {
      const ri = clamp((this.dmg / ENEMY_DEFS.red.dmg - 1) / 3.2, 0, 1);
      this.color = mixCol(this.color, [255, 20, 15], ri * 0.6);
    }
    this.rage = B.rageLevel(wave, biome);
    if (this.rage > 0) {
      const rc: RGB = k === "blue" || k === "stinger" ? (C.RAGE_BAT as RGB) : (C.RAGE_FIRE as RGB);
      this.color = mixCol(this.color, rc, 0.25 + 0.4 * this.rage);
    }
    this.isMini = k === "herald";
    this.guards = k === "herald" ? [] : null;
    this.phaseT = 0.8 + Math.random() * (C.GHOST_SOLID_T - 0.8);
  }

  mutate() {
    if (this.mutant) return;
    this.mutant = true;
    this.max_hp *= C.MUTANT_HP;
    this.hp = this.max_hp;
    this.dmg *= C.MUTANT_DMG;
    this.contact_dps *= C.MUTANT_DMG;
    this.speed *= C.MUTANT_SPEED;
    this.armor = Math.min(0.6, this.armor + C.MUTANT_ARMOR);
    this.score = Math.floor(this.score * C.MUTANT_REWARD);
    this.xp = Math.floor(this.xp * C.MUTANT_REWARD);
    this.coin = Math.floor(this.coin * C.MUTANT_REWARD);
    this.rage = 0;
    this.color = mixCol(this.color, this.hellish ? C.MUTANT_SKIN_HELL : C.MUTANT_SKIN, 0.8);
  }

  applyPoison(dps: number) {
    this.poisonDps += dps;
  }
  applyBurn(dps: number, dur: number) {
    this.burnTimer = Math.max(this.burnTimer, dur);
    this.burnDps = Math.max(this.burnDps, dps);
  }
  applySlow(mult: number, dur: number) {
    if (this.slowTimer <= 0 || mult < this.slowMult) this.slowMult = mult;
    this.slowTimer = Math.max(this.slowTimer, dur);
  }

  private kamikazeBlast(c: EnemyCtx) {
    this.alive = false;
    this.exploded = true;
    const col = ENEMY_COLORS.kamikaze;
    c.fx.shockwave(this.x, this.y, C.KAMIKAZE_RADIUS, [255, 170, 80], 0.35, 7);
    c.fx.ring(this.x, this.y, col, 26, 320, 0.5, 4);
    c.fx.burst(this.x, this.y, [255, 220, 120], 18, 260, 0.45, 4);
    c.fx.shake(6, 0.22);
    sfx("explosion", 0.8);
    const p = c.player;
    if (p.alive && dist(this.x, this.y, p.x, p.y) <= C.KAMIKAZE_RADIUS + p.radius) {
      p.takeDamage(this.dmg * C.KAMIKAZE_DMG_MULT, c.fx, this.x, this.y, this.name);
    }
  }

  private clampWorld(c: EnemyCtx) {
    this.x = clamp(this.x, this.radius, c.W - this.radius);
    this.y = clamp(this.y, this.radius, c.H - this.radius);
  }

  liveGuards() {
    if (!this.guards) return 0;
    let n = 0;
    for (const g of this.guards) if (g.alive) n++;
    return n;
  }

  update(dt: number, c: EnemyCtx) {
    if (!this.alive) return;
    const p = c.player;
    const fx = c.fx;
    this.spawnT += dt;
    if (this.kind === "ghost") {
      this.phaseT -= dt;
      if (this.phaseT <= 0) {
        this.phased = !this.phased;
        this.phaseT = this.phased ? C.GHOST_PHASE_T : C.GHOST_SOLID_T;
        fx.ring(this.x, this.y, ENEMY_COLORS.ghost, 8, 110, 0.3, 2.2);
      }
    }
    this.wobble += dt * 6;
    if (this.touchCd > 0) this.touchCd -= dt;
    const scaleIn = 1 - Math.pow(1 - clamp(this.spawnT / 0.3, 0, 1), 3);
    let speedMult = 1;
    if (this.slowTimer > 0) {
      this.slowTimer -= dt;
      speedMult = this.slowMult;
      if (this.slowTimer <= 0) this.slowMult = 1;
    }
    if (this.burnTimer > 0) {
      this.burnTimer -= dt;
      this.burnAcc += dt;
      while (this.burnAcc >= 0.5 && this.alive) {
        this.burnAcc -= 0.5;
        if (this.takeDamage(this.burnDps * 0.5, false, fx, 0, 0, true)) c.kill(this);
      }
      if (this.burnTimer <= 0) this.burnDps = 0;
      if (!this.alive) return;
    }
    if (this.poisonDps > 0) {
      this.poisonAcc += dt;
      while (this.poisonAcc >= 0.5 && this.alive) {
        this.poisonAcc -= 0.5;
        if (this.takeDamage(this.poisonDps * 0.5, false, fx, 0, 0, true)) c.kill(this);
      }
      if (!this.alive) return;
    }
    if (this.hitFlash > 0) this.hitFlash -= dt;
    if (this.healFlash > 0) this.healFlash -= dt;
    if (this.blockFlash > 0) this.blockFlash = Math.max(0, this.blockFlash - dt);

    if (p.invis_t > 0) {
      if (Math.abs(this.knockX) > 0.5 || Math.abs(this.knockY) > 0.5) {
        this.x += this.knockX * dt;
        this.y += this.knockY * dt;
        this.knockX *= Math.max(0, 1 - dt * 8);
        this.knockY *= Math.max(0, 1 - dt * 8);
        this.clampWorld(c);
      }
      return;
    }
    let eff = this.speed * speedMult;
    if (this.kind === "kamikaze" && p.alive) {
      if (this.fuse_t > 0) {
        this.fuse_t -= dt;
        eff *= C.KAMIKAZE_FUSE_SLOW;
        if (this.fuse_t <= 0) {
          this.kamikazeBlast(c);
          return;
        }
      } else if (this.spawnT > 0.3 && dist(this.x, this.y, p.x, p.y) < C.KAMIKAZE_TRIGGER + p.radius) {
        this.fuse_t = C.KAMIKAZE_FUSE;
        fx.popup(this.x, this.y - this.radius - 18, "!", [255, 220, 120], 26, 0.5, true);
        sfx("warn", 0.6);
      }
    }
    if (p.alive) {
      const [tfx, tfy] = normDir(this.x, this.y, p.x, p.y);
      const k = Math.min(1, dt * 7);
      this.faceX += (tfx - this.faceX) * k;
      this.faceY += (tfy - this.faceY) * k;
    }
    this.walk += dt * (2 + eff * 0.03);

    if (Math.abs(this.knockX) > 0.5 || Math.abs(this.knockY) > 0.5) {
      this.x += this.knockX * dt;
      this.y += this.knockY * dt;
      this.knockX *= Math.max(0, 1 - dt * 8);
      this.knockY *= Math.max(0, 1 - dt * 8);
    } else if (this.dashT > 0) {
      this.dashT -= dt;
      this.x += this.dashDx * eff * 2.6 * dt;
      this.y += this.dashDy * eff * 2.6 * dt;
    } else if (this.guardOf && this.guardOf.alive) {
      const g = this.guardOf;
      const n = Math.max(1, g.guards!.length);
      const base = Math.atan2(p.y - g.y, p.x - g.x);
      const spread = Math.min(Math.PI * 0.92, 0.62 * (n - 1));
      const off = n === 1 ? 0 : (this.guardSlot / (n - 1) - 0.5) * spread;
      const a = base + off;
      const ring = g.radius + this.radius + 44;
      const tx_ = g.x + Math.cos(a) * ring, ty = g.y + Math.sin(a) * ring;
      const [gdx, gdy] = normDir(this.x, this.y, tx_, ty);
      const gd = dist(this.x, this.y, tx_, ty);
      if (gd > 4) {
        const st = Math.min(gd, eff * 1.55 * dt * scaleIn);
        this.x += gdx * st;
        this.y += gdy * st;
      }
      this.clampWorld(c);
      if (p.alive) {
        const pd = dist(this.x, this.y, p.x, p.y);
        const need = this.hit_r + p.radius;
        if (pd > 0.001 && pd < need) {
          p.x = clamp(this.x + ((p.x - this.x) / pd) * need, p.radius, c.W - p.radius);
          p.y = clamp(this.y + ((p.y - this.y) / pd) * need, p.radius, c.H - p.radius);
        }
      }
      return;
    } else {
      let [dx, dy] = normDir(this.x, this.y, p.x, p.y);
      if (this.fearTimer > 0) {
        this.fearTimer -= dt;
        this.x -= dx * eff * 1.15 * dt * scaleIn;
        this.y -= dy * eff * 1.15 * dt * scaleIn;
        this.clampWorld(c);
        return;
      }
      if (this.isMini) {
        const d = dist(this.x, this.y, p.x, p.y);
        if (d < 250) {
          dx = -dx;
          dy = -dy;
        } else if (d < 340) {
          const t0 = dx;
          dx = -dy;
          dy = t0;
        }
        this.x += dx * eff * dt * scaleIn;
        this.y += dy * eff * dt * scaleIn;
        this.clampWorld(c);
        if (p.alive && dist(this.x, this.y, p.x, p.y) < this.hit_r + p.radius - 2 && this.touchCd <= 0) {
          this.touchCd = 0.12;
          p.takeDamage(this.contact_dps * 0.12 * 6, fx, this.x, this.y, this.name);
        }
        return;
      }
      if (this.kind === "wizard") {
        const d = dist(this.x, this.y, p.x, p.y);
        if (d < C.WIZARD_KEEP) {
          dx = -dx;
          dy = -dy;
        } else if (d < C.WIZARD_KEEP + 110) {
          const t0 = dx;
          dx = -dy;
          dy = t0;
        }
        this.shootCd -= dt;
        if (this.shootCd <= 0 && this.spawnT > 0.6) {
          this.shootCd = C.WIZARD_SHOOT_CD[0] + Math.random() * (C.WIZARD_SHOOT_CD[1] - C.WIZARD_SHOOT_CD[0]);
          const [pdx, pdy] = normDir(this.x, this.y, p.x, p.y);
          const wcol = this.mapVar ? this.color : ENEMY_COLORS.wizard;
          c.projectiles.push(new EnemyProjectile(this.x, this.y, pdx * C.WIZARD_SHOT_SPEED, pdy * C.WIZARD_SHOT_SPEED, this.dmg, wcol, 7, 4, null, 0, 0, null, this.dmg * C.WIZARD_POISON_MULT, this.shotStyle === "orb" ? "poison" : this.shotStyle));
          fx.ring(this.x, this.y, wcol, 10, 130, 0.3, 2.5);
          sfx("shoot_c", 0.3);
        }
      } else if (this.kind === "goblin") {
        const d = dist(this.x, this.y, p.x, p.y);
        const zz = Math.sin(this.spawnT * 2.3 + this.wobble);
        if (d < 520) {
          const ndx = -dx + -dy * zz * 0.6, ndy = -dy + dx * zz * 0.6;
          dx = ndx;
          dy = ndy;
        } else {
          const s = zz > 0 ? 1 : -1;
          const ndx = -dy * s, ndy = dx * s;
          dx = ndx;
          dy = ndy;
        }
        if (this.x < 80 || this.x > c.W - 80) {
          dx *= 0.2;
          if (Math.abs(dy) <= 0.3) dy = this.y < c.H / 2 ? 1 : -1;
        }
        if (this.y < 80 || this.y > c.H - 80) {
          dy *= 0.2;
          if (Math.abs(dx) <= 0.3) dx = this.x < c.W / 2 ? 1 : -1;
        }
        const ln = Math.hypot(dx, dy) || 1;
        dx /= ln;
        dy /= ln;
      } else if (this.kind === "necro") {
        const d = dist(this.x, this.y, p.x, p.y);
        if (d < C.NECRO_KEEP) {
          dx = -dx;
          dy = -dy;
        } else if (d < C.NECRO_KEEP + 100) {
          const t0 = dx;
          dx = -dy;
          dy = t0;
        }
      } else if (this.kind === "healer") {
        const d = dist(this.x, this.y, p.x, p.y);
        if (d < C.HEALER_KEEP) {
          dx = -dx;
          dy = -dy;
        } else if (d < C.HEALER_KEEP + 90) {
          const t0 = dx;
          dx = -dy;
          dy = t0;
        }
        this.healCd -= dt;
        if (this.healCd <= 0 && this.spawnT > 0.5) {
          this.healCd = C.HEALER_TICK;
          let n = 0;
          for (const o of c.enemies) {
            if (o === this || !o.alive || o.hp >= o.max_hp) continue;
            if (dist(this.x, this.y, o.x, o.y) > C.HEALER_RADIUS) continue;
            o.hp = Math.min(o.max_hp, o.hp + o.max_hp * C.HEALER_FRAC);
            o.healFlash = 0.25;
            if (++n >= C.HEALER_MAX_TARGETS) break;
          }
          if (n) fx.ring(this.x, this.y, ENEMY_COLORS.healer, 12, 120, 0.35, 2.5);
        }
      } else if (this.kind === "yellow") {
        const d = dist(this.x, this.y, p.x, p.y);
        if (d < 230) {
          dx = -dx;
          dy = -dy;
        } else if (d < 280) {
          dx = 0;
          dy = 0;
        }
        this.shootCd -= dt;
        if (this.shootCd <= 0 && this.spawnT > 0.4) {
          this.shootCd = 1.5 + Math.random() * 0.8;
          const [pdx, pdy] = normDir(this.x, this.y, p.x, p.y);
          const col = this.mapVar ? MAP_SHOT_COLORS[this.shotStyle] || [235, 210, 70] : this.hellish ? [255, 140, 60] : [235, 210, 70];
          c.projectiles.push(new EnemyProjectile(this.x, this.y, pdx * 230, pdy * 230, this.dmg * 0.85, col, 6, 4, null, 0, 0, null, 0, this.shotStyle));
          sfx("shoot_c", 0.25);
        }
      } else if (this.kind === "sprinter") {
        this.dashCd -= dt;
        if (this.dashCd <= 0 && this.spawnT > 0.3) {
          this.dashCd = 1.6 + Math.random();
          this.dashT = 0.22;
          this.dashDx = dx;
          this.dashDy = dy;
        }
      }
      this.x += dx * eff * dt * scaleIn;
      this.y += dy * eff * dt * scaleIn;
    }
    this.clampWorld(c);

    if (p.alive && this.contact_dps > 0) {
      const d = dist(this.x, this.y, p.x, p.y);
      if (d < this.hit_r + p.radius - 2 && this.touchCd <= 0) {
        this.touchCd = 0.12;
        let tmp = this.contact_dps * 0.12 * 6;
        if (this.slowTimer > 0 && p.dash_slow_level > 0) tmp *= 1 - Math.min(0.5, 0.3 + 0.05 * p.dash_slow_level);
        const dealt = p.takeDamage(tmp, fx, this.x, this.y, this.name);
        if (dealt > 0 && p.thorns_level > 0) {
          if (this.takeDamage(dealt * 0.35 * p.thorns_level, false, fx)) c.kill(this);
        }
      }
    }
  }

  static HERALD_LEAK = 0.12;
  heraldLeak = Enemy.HERALD_LEAK;

  takeDamage(amount: number, crit: boolean, fx: FX, kx = 0, ky = 0, quiet = false, log?: (a: number) => void): boolean {
    if (this.phased) return false;
    if (this.isMini) {
      const n = this.liveGuards();
      if (n > 0) {
        const soaked = amount * (1 - this.heraldLeak);
        amount *= this.heraldLeak;
        this.blockFlash = 0.22;
        const alive = this.guards!.filter((g) => g.alive);
        if (alive.length) {
          const gg = alive[Math.floor(Math.random() * alive.length)];
          gg.blockFlash = 0.22;
          if (!quiet && soaked > 0) fx.popup(gg.x, gg.y - gg.radius - 6, t("fx.absorbed"), [150, 200, 250], 13, 0.45, true);
        }
      }
    }
    if (this.fearTimer > 0 && this.fearVuln > 0) amount *= 1 + this.fearVuln;
    if (this.armor > 0) amount *= 1 - this.armor;
    if (this.alive) DMG.note(Math.min(amount, Math.max(0, this.hp)));
    void log;
    this.hp -= amount;
    this.hitFlash = 0.12;
    this.knockX += kx;
    this.knockY += ky;
    if (!quiet) {
      fx.popup(this.x, this.y - this.radius - 4, `${Math.floor(amount)}${crit ? "!" : ""}`, crit ? [255, 230, 120] : [255, 255, 255], crit ? 22 : 15, 0.5);
    }
    if (crit) sfx("crit", 0.5);
    else if (!quiet) sfx("hit", 0.35, 0.1);
    if (this.hp <= 0 && this.alive) {
      this.alive = false;
      fx.burst(this.x, this.y, this.color, 12, 170, 0.5, 3.5);
      sfx("kill", 0.45);
      return true;
    }
    return false;
  }
}

/** Hasar dökümü (ölüm ekranı): kaynak -> toplam. */
export const DMG = {
  src: "other",
  log: null as Record<string, number> | null,
  note(a: number) {
    if (!this.log || a <= 0) return;
    this.log[this.src] = (this.log[this.src] || 0) + a;
  },
};

export function makeMapEnemy(theme: string, kind: string, x: number, y: number, waveMult: number, diffMult: number, wave: number) {
  const roster = (GD.MAP_ROSTER as Record<string, Record<string, string>>)[theme];
  const mv = roster ? roster[kind] : undefined;
  if (mv) return new Enemy(null, x, y, waveMult, diffMult, wave, mv);
  return new Enemy(kind, x, y, waveMult, diffMult, wave);
}
