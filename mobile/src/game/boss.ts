/**
 * Patron — Python `Boss` sınıfının karşılığı: imza özelliği (yanık, zehir,
 * görünmezlik, ışınlanma, ejderha dalışı), 18 yetenek, telgraflı saldırılar,
 * menzilli yaylım, öfke / çaresizlik fazları, bariyer, ölüm sarmalı.
 */
import { clamp, dist, normDir, lighten, TAU, RGB, rand, pick } from "../core/util";
import * as B from "./balance";
import { GD, BOSS_DEFS } from "./data";
import { Enemy, EnemyProjectile, makeMapEnemy, DMG } from "./enemy";
import { Hazard } from "./objects";
import { hellPickKind } from "./waves";
import type { FX } from "./fx";
import type { Player } from "./player";
import { sfx } from "../core/audio";
import { t, tx } from "../core/i18n";

const C = GD;
const AEGIS_COLOR: RGB = C.AEGIS_COLOR;
const WARD_COLOR: RGB = C.WARD_COLOR;
const DRAIN_COLOR: RGB = C.DRAIN_COLOR;

export interface BossCtx {
  fx: FX;
  player: Player;
  projectiles: EnemyProjectile[];
  hazards: Hazard[];
  W: number;
  H: number;
  kill: (b: any) => void;
}

const TRAIT_HAZARD_COLORS: Record<string, RGB> = {
  burn: [255, 132, 46], inferno: [255, 116, 34], venom: [150, 226, 74], chill: [120, 196, 255], vanish: [196, 116, 246], blink: [110, 236, 208],
};

export function bossSkillSet(kind: string, theme: string | null, hellish: boolean): string[] {
  const byMap = C.BOSS_SKILLS_BY_MAP as Record<string, Record<string, string[]>>;
  const mp = hellish ? "hell" : theme && byMap[theme] ? theme : "stone";
  let sk = byMap[mp]?.[kind] || byMap.stone[kind];
  if (!sk) sk = [...(C.BOSS_SKILL_SETS[kind] || ["lunge"]), ...(C.BOSS_POWER_SKILLS[kind] || [])];
  return [...new Set(sk)];
}

let BOSS_ID = 1_000_000;

export class Boss {
  id = BOSS_ID++;
  kind: string;
  hellish: boolean;
  name: string;
  x: number;
  y: number;
  wave: number;
  hitFloor: number;
  wound: number;
  bossIndex: number;
  armor: number;
  max_hp: number;
  hp: number;
  speed: number;
  dmg: number;
  radius: number;
  hit_r: number;
  color: RGB;
  theme: string | null;
  skills: string[];
  element: string | null;
  champion: number;
  alive = true;
  spawnT = 0;
  hitFlash = 0;
  atkTimer = 1.4;
  telegraph: [string, any, number, number, number, number] | null = null;
  touchCd = 0;
  enraged = false;
  desperate = false;
  isBoss = true;
  isMini = false;
  score: number;
  coin: number;
  xp: number;
  summonCd = rand(5, 7);
  fleeTimer = 0;
  summoned: Enemy[] = [];
  teleportCd = rand(4, 6);
  trait: { kind: string; label: string; color: RGB; hellfire: boolean };
  vanishT = 0;
  vanishCd = rand(5.5, 8);
  flyT = 0;
  flyDir: [number, number] = [0, 0];
  flyCd = rand(6, 9);
  trailAcc = 0;
  skillCd = rand(3.5, 6);
  lastSkill = "";
  pullT = 0;
  buffT = 0;
  huntT = 0;
  huntCheck = 0;
  strafeDir = Math.random() < 0.5 ? -1 : 1;
  strafeT = rand(1.4, 2.6);
  faceX = 0;
  faceY = 1;
  gait = Math.random() * TAU;
  volleyCd = rand(2.2, 3.4);
  chargeT = 0;
  chargeDir: [number, number] = [0, 0];
  wantDist: number;
  poisonDps = 0;
  poisonAcc = 0;
  burnTimer = 0;
  burnDps = 0;
  burnAcc = 0;
  slowTimer = 0;
  slowMult = 1;
  lifesteal: number;
  healBudget = 0;
  healRate: number | null = null;
  intakeBudget: number | null = null;
  minFightTime: number = C.BOSS_MIN_FIGHT_TIME;
  healFlash = 0;
  fightTime = 0;
  aegisHp = 0;
  aegisMax = 0;
  aegisT = 0;
  spiralT = 0;
  spiralDelay = 0;
  spiralAcc = 0;
  spiralAng = 0;
  powerPhase = 0;
  veilT = 0;
  wardT = 0;
  wardPop = 0;
  drainT = 0;
  drainAcc = 0;
  novaN = 0;
  novaCd = 0;
  novaAng = 0;
  snares: [number, number, number][] = [];
  fearTimer = 0;
  fearVuln = 0;
  bossWave = 0;
  view: any = null;
  deathCounted = false;
  oneshotUsed = false;
  shape = "boss";

  constructor(kind: string, x: number, y: number, hpMult: number, diffMult = 1, wave = 10, hellish = false, theme: string | null = null, champion = 1) {
    const d = BOSS_DEFS[kind];
    this.kind = kind;
    this.hellish = hellish;
    this.name = hellish ? tx("bn.hell." + kind, C.HELL_BOSS_NAMES[kind] || d.name) : tx("bn." + kind, d.name);
    this.x = x;
    this.y = y;
    this.wave = wave;
    this.hitFloor = B.bossHitFloor(wave, hellish);
    this.wound = B.bossWound(wave, hellish);
    const dmgm = hellish ? B.lateWaveDmgMult(B.hellDmgWave(wave), C.LATE_DMG_COEF_HELL) : B.lateWaveDmgMult(wave);
    this.bossIndex = hellish ? B.hellBossIndex(wave) : B.bossIndexForWave(wave);
    const [pwHp, pwDmg, pwArm] = B.bossPower(this.bossIndex);
    this.armor = pwArm;
    this.max_hp = d.hp * hpMult * diffMult * pwHp * C.BOSS_HP_NERF * C.BOSS_HP_BONUS;
    this.hp = this.max_hp;
    this.speed = d.speed;
    this.dmg = d.dmg * diffMult * pwDmg * (0.55 + 0.45 * dmgm) * C.BOSS_DMG_NERF;
    this.radius = d.radius;
    this.hit_r = this.radius * 0.92;
    this.color = (hellish ? C.HELL_BOSS_COLORS[kind] || d.color : d.color) as RGB;
    this.theme = theme && C.MAP_BOSS_NAMES[theme] && !hellish ? theme : null;
    if (this.theme) {
      this.name = tx(`bn.${this.theme}.${kind}`, C.MAP_BOSS_NAMES[this.theme][kind] || this.name);
      this.color = (C.MAP_BOSS_COLORS[this.theme][kind] || this.color) as RGB;
    }
    this.skills = bossSkillSet(kind, this.theme, hellish);
    this.element = this.theme ? C.MAP_BOSS_ELEMENT[this.theme] || null : null;
    this.champion = Math.max(1, champion);
    if (this.champion > 1) {
      this.name = "★ " + this.name;
      this.dmg *= 1 + C.CHAMPION_DMG_PER * (this.champion - 1);
      this.radius = Math.floor(this.radius * C.CHAMPION_SIZE);
      this.hit_r = this.radius * 0.92;
    }
    this.score = Math.floor(800 * (1 + (this.bossIndex - 1) * 0.45)) * this.champion;
    this.coin = Math.floor(260 * (1 + (this.bossIndex - 1) * 0.35)) * this.champion;
    this.xp = Math.floor(220 * (1 + (this.bossIndex - 1) * 0.3)) * this.champion;
    const tr = C.BOSS_TRAITS[kind] || C.BOSS_TRAITS.warlord;
    this.trait = { ...tr, hellfire: hellish || tr.kind === "burn" || tr.kind === "inferno" };
    this.wantDist = ({ warlord: 190, witch: 215, colossus: 110, reaper: 160, hive: 205, dragon: 245 } as Record<string, number>)[kind] ?? 190;
    this.lifesteal = clamp(0.2 + 0.05 * (this.bossIndex - 1), 0, 0.45);
  }

  traitLabel() {
    return tx("trait." + this.kind, this.trait.label);
  }
  private dotDps(p: Player, want: number, frac: number) {
    return Math.min(want, Math.max(2, p.max_hp * frac));
  }
  private areaK() {
    return Math.max(0.45, 1 - (this.bossIndex - 1) * 0.07);
  }
  private rangedK() {
    return Math.max(0.45, 1 - (this.bossIndex - 1) * 0.09);
  }
  private hz(x: number, y: number, r: number, delay: number, dmg: number, c: BossCtx) {
    const col = TRAIT_HAZARD_COLORS[this.trait.kind] || [255, 70, 60];
    c.hazards.push(new Hazard(clamp(x, 20, c.W - 20), clamp(y, 20, c.H - 20), r, delay, dmg, this, col));
  }
  private say(c: BossCtx, key: string, col: RGB | number[], size = 22, life = 0.9) {
    c.fx.popup(this.x, this.y - this.radius - 30, t(key), col, size, life, true);
  }

  afflict(p: Player, k = 1) {
    if (!p || !p.alive) return;
    const tk = this.trait.kind;
    const base = Math.max(1, this.dmg);
    const BC = 0.05, PC = 0.035;
    if (tk === "burn" || tk === "inferno") p.applyBurn(this.dotDps(p, base * (tk === "inferno" ? 0.34 : 0.28) * k, BC), 3.2, this.name);
    else if (tk === "venom") p.applyPoison(this.dotDps(p, base * 0.22 * k, PC), 5.5, this.name);
    else if (tk === "chill") p.applySlow(0.58, 1.8);
    else if (tk === "vanish") {
      p.applySlow(0.74, 1.4);
      p.applyPoison(this.dotDps(p, base * 0.1 * k, PC * 0.5), 3, this.name);
    } else if (tk === "blink") p.applyPoison(this.dotDps(p, base * 0.16 * k, PC * 0.7), 4, this.name);
    const el = this.element;
    if (el === "chill" && tk !== "chill") p.applySlow(0.78, 1);
    else if (el === "venom" && tk !== "venom") p.applyPoison(this.dotDps(p, base * 0.1 * k, PC * 0.5), 3.5, this.name);
    else if (el === "burn" && tk !== "burn" && tk !== "inferno") p.applyBurn(this.dotDps(p, base * 0.12 * k, BC * 0.5), 2.4, this.name);
    if (this.trait.hellfire && tk !== "burn" && tk !== "inferno") p.applyBurn(this.dotDps(p, base * 0.15 * k, BC * 0.6), 2.4, this.name);
  }

  hitPlayer(p: Player, amount: number, fx: FX, sx?: number, sy?: number) {
    if (!p.alive) return 0;
    if (this.hitFloor > 0 && amount > 0 && this.dmg > 0) amount = Math.max(amount, p.max_hp * this.hitFloor * Math.min(1.7, amount / this.dmg));
    const dealt = p.takeDamage(amount, fx, sx ?? this.x, sy ?? this.y, this.name);
    if (dealt > 0) {
      this.afflict(p);
      this.onDamageDealt(amount);
    }
    return dealt;
  }

  isHidden() {
    return this.vanishT > 0 || this.veilT > 0;
  }

  onDamageDealt(amount: number) {
    if (!this.alive || this.lifesteal <= 0 || amount <= 0) return;
    const heal = Math.min(amount * this.lifesteal, this.healBudget);
    if (heal <= 0) return;
    this.healBudget -= heal;
    const before = this.hp;
    this.hp = Math.min(this.max_hp, this.hp + heal);
    if (this.hp - before > 0.5) this.healFlash = 0.45;
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

  private shoot(c: BossCtx, ang: number, speed: number, dmgK: number, r = 8, color?: RGB | number[], target: any = null, turn = 0, accel = 0) {
    c.projectiles.push(new EnemyProjectile(this.x, this.y, Math.cos(ang) * speed, Math.sin(ang) * speed, this.dmg * dmgK * this.rangedK(), color || this.color, r, 4, target, turn, accel, this, 0, "boss"));
  }
  private leadPoint(p: Player, lead = 0.34, c: BossCtx): [number, number] {
    return [clamp(p.x + p.vx * lead, 20, c.W - 20), clamp(p.y + p.vy * lead, 20, c.H - 20)];
  }
  private aimAngle(p: Player, speed: number, jitter = 0.1, c: BossCtx) {
    speed = Math.max(60, speed);
    let th = dist(this.x, this.y, p.x, p.y) / speed;
    for (let i = 0; i < 2; i++) th = dist(this.x, this.y, p.x + p.vx * th, p.y + p.vy * th) / speed;
    th += rand(-jitter, jitter);
    const tx_ = clamp(p.x + p.vx * th, 20, c.W - 20), ty = clamp(p.y + p.vy * th, 20, c.H - 20);
    return Math.atan2(ty - this.y, tx_ - this.x);
  }
  private escapeAngle(p: Player) {
    if (Math.hypot(p.vx, p.vy) > 60) return Math.atan2(p.vy, p.vx);
    return Math.atan2(p.y - this.y, p.x - this.x);
  }
  private ringRadius() {
    return 160 + this.bossIndex * 12;
  }
  private ringCount() {
    const want = 7 + Math.min(3, this.bossIndex - 1) + (this.enraged ? 1 : 0);
    const maxN = Math.floor((TAU * this.ringRadius()) / C.BOSS_RING_GAP_MIN);
    return Math.max(5, Math.min(want, maxN));
  }
  private setTelegraph(kind: string, a: any, b: number, cc: number, dur: number) {
    const total = dur + C.BOSS_TELEGRAPH_EXTRA;
    this.telegraph = [kind, a, b, cc, total, total];
  }
  private skillInterval() {
    let base = Math.max(3, 7.5 - (this.bossIndex - 1) * 0.8);
    if (this.desperate) base *= 0.55;
    else if (this.enraged) base *= 0.72;
    if (this.buffT > 0) base *= 0.75;
    return base * rand(0.85, 1.15);
  }
  private volleyInterval() {
    let base = Math.max(1.5, 5 - (this.bossIndex - 1) * 0.8);
    if (this.desperate) base *= 0.55;
    else if (this.enraged) base *= 0.72;
    return base * rand(0.85, 1.15);
  }

  private summonMinions(c: BossCtx) {
    let n: number, kinds: string[];
    if (this.kind === "hive") {
      n = this.desperate ? 5 : 4;
      kinds = ["red", "sprinter", "blue", "yellow"];
    } else {
      n = this.desperate ? 4 : 3;
      kinds = ["red", "sprinter", "blue"];
    }
    const mult = 1 + Math.max(0, this.wave - 1) * 0.2;
    for (let i = 0; i < n; i++) {
      const a = Math.random() * TAU;
      const mx = clamp(this.x + Math.cos(a) * 100, 20, c.W - 20), my = clamp(this.y + Math.sin(a) * 100, 20, c.H - 20);
      const kind = pick(kinds);
      if (this.hellish) this.summoned.push(new Enemy(kind, mx, my, mult, 1, this.wave, hellPickKind(this.wave), "hell"));
      else if (this.theme) this.summoned.push(makeMapEnemy(this.theme, kind, mx, my, mult, 1, this.wave));
      else this.summoned.push(new Enemy(kind, mx, my, mult, 1, this.wave));
    }
    c.fx.ring(this.x, this.y, this.color, 18, 190, 0.4, 3);
    c.fx.popup(this.x, this.y - this.radius - 10, t("boss.summon"), this.color, 16, 0.9, true);
    sfx("warn", 0.6);
  }

  private startAegis(c: BossCtx) {
    this.aegisMax = this.max_hp * C.AEGIS_FRAC;
    this.aegisHp = this.aegisMax;
    this.aegisT = C.AEGIS_TIME;
    c.fx.ring(this.x, this.y, AEGIS_COLOR, 28, 240, 0.6, 3.5);
    this.say(c, "boss.aegis", AEGIS_COLOR, 24, 1.2);
    sfx("guard", 0.8);
  }
  private startSpiral(c: BossCtx) {
    this.spiralDelay = 0.65;
    this.spiralT = C.SPIRAL_TIME + (this.desperate ? 0.8 : 0);
    this.spiralAcc = 0;
    this.spiralAng = Math.random() * TAU;
    this.say(c, "boss.spiral", [255, 110, 150], 24, 1.1);
    c.fx.shockwave(this.x, this.y, 160, [255, 110, 150], 0.45, 5);
    sfx("warn", 0.8);
  }

  private castSkill(c: BossCtx) {
    const p = c.player;
    const pool = this.skills.filter((k) => k !== this.lastSkill);
    const name = pick(pool.length ? pool : this.skills);
    this.lastSkill = name;
    const [px, py] = this.leadPoint(p, 0.35, c);
    const fx = c.fx;
    switch (name) {
      case "lunge":
        this.setTelegraph("lunge", px, py, 0, 0.55);
        this.say(c, "boss.lunge", [255, 150, 90]);
        break;
      case "wall": {
        const esc = this.escapeAngle(p);
        this.setTelegraph("wall", clamp(p.x + Math.cos(esc) * 190, 30, c.W - 30), clamp(p.y + Math.sin(esc) * 190, 30, c.H - 30), esc, 0.62);
        this.say(c, "boss.wall", this.trait.color, 20);
        break;
      }
      case "cage":
        this.setTelegraph("cage", px, py, this.ringRadius() * 0.82, this.enraged ? 0.6 : 0.78);
        fx.ring(px, py, this.trait.color, 22, 170, 0.5, 3);
        break;
      case "meteor":
        this.setTelegraph("meteor", px, py, 0, 0.55);
        this.say(c, "boss.meteor", [255, 170, 80]);
        break;
      case "pull":
        this.setTelegraph("pull", this.x, this.y, 0, 0.62);
        this.say(c, "boss.pull", [200, 130, 255]);
        break;
      case "quake": {
        fx.shockwave(this.x, this.y, 300, this.color, 0.55, 8);
        fx.shake(10, 0.4);
        this.say(c, "boss.quake", [170, 200, 240], 22, 1);
        for (let ring = 0; ring < 3; ring++) {
          const n = 8 + ring * 3, rad = 150 + ring * 115;
          for (let i = 0; i < n; i++) {
            const a = (i * TAU) / n + ring * 0.24;
            this.hz(this.x + Math.cos(a) * rad, this.y + Math.sin(a) * rad, 56, 0.25 + ring * 0.3, this.dmg * 0.5 * this.areaK(), c);
          }
        }
        if (dist(this.x, this.y, p.x, p.y) < 520) p.applySlow(0.62, 2.2);
        sfx("explosion", 0.7);
        break;
      }
      case "warcry":
        this.buffT = 6.5;
        fx.shockwave(this.x, this.y, 260, [255, 120, 60], 0.5, 7);
        fx.ring(this.x, this.y, [255, 180, 90], 26, 300, 0.55, 4);
        this.say(c, "boss.warcry", [255, 180, 90], 26, 1.2);
        fx.shake(8, 0.3);
        if (dist(this.x, this.y, p.x, p.y) < 300) {
          const [kx, ky] = normDir(this.x, this.y, p.x, p.y);
          p.kbx += kx * 1500;
          p.kby += ky * 1500;
          p.applyBurn(this.dmg * 0.22, 3, this.name);
        }
        sfx("boss", 0.8);
        break;
      case "harvest": {
        const a = Math.random() * TAU;
        this.x = clamp(p.x + Math.cos(a) * 90, this.radius, c.W - this.radius);
        this.y = clamp(p.y + Math.sin(a) * 90, this.radius, c.H - this.radius);
        fx.ring(this.x, this.y, this.color, 24, 260, 0.4, 3);
        this.hz(this.x, this.y, 165, 0.3, this.dmg * this.areaK(), c);
        this.say(c, "boss.harvest", this.color, 24, 1);
        this.fleeTimer = 0;
        sfx("warn", 0.9);
        break;
      }
      case "blink": {
        const esc = this.escapeAngle(p) + rand(-0.6, 0.6);
        fx.burst(this.x, this.y, this.color, 26, 220, 0.45, 4);
        const rad = rand(210, 280);
        this.x = clamp(p.x + Math.cos(esc) * rad, this.radius, c.W - this.radius);
        this.y = clamp(p.y + Math.sin(esc) * rad, this.radius, c.H - this.radius);
        fx.ring(this.x, this.y, lighten(this.color, 0.3), 24, 260, 0.4, 3);
        this.say(c, "boss.blink", lighten(this.color, 0.3), 24);
        const base = Math.atan2(p.y - this.y, p.x - this.x);
        const n = this.bossIndex < 4 ? 5 : 7;
        for (let i = 0; i < n; i++) this.shoot(c, base + (i - (n - 1) / 2) * 0.17, 330, 0.55, 8);
        this.fleeTimer = 0;
        sfx("dash", 0.9);
        break;
      }
      case "veil":
        if (this.trait.kind === "vanish") this.vanishT = Math.max(this.vanishT, C.VEIL_TIME);
        else this.veilT = C.VEIL_TIME;
        fx.ring(this.x, this.y, this.color, 24, 220, 0.45, 3);
        this.say(c, "boss.veil", [220, 200, 255], 22, 1);
        sfx("dash", 0.7);
        break;
      case "ward":
        this.wardT = C.WARD_TIME;
        fx.ring(this.x, this.y, WARD_COLOR, 30, 230, 0.55, 3.5);
        fx.shockwave(this.x, this.y, 180, WARD_COLOR, 0.45, 6);
        this.say(c, "boss.ward", WARD_COLOR, 24, 1.2);
        sfx("guard", 0.9);
        break;
      case "drain":
        if (dist(this.x, this.y, p.x, p.y) <= C.DRAIN_RANGE * 0.92) {
          this.drainT = C.DRAIN_TIME + (this.enraged ? 0.6 : 0);
          this.drainAcc = 0;
          this.say(c, "boss.drain", DRAIN_COLOR, 22, 1.1);
          sfx("warn", 0.8);
        } else {
          this.setTelegraph("pull", this.x, this.y, 0, 0.62);
          this.say(c, "boss.pull", [200, 130, 255]);
        }
        break;
      case "nova":
        this.novaN = 3 + (this.desperate ? 1 : 0);
        this.novaCd = 0.35;
        this.novaAng = Math.random() * TAU;
        fx.shockwave(this.x, this.y, 150, lighten(this.color, 0.3), 0.4, 5);
        this.say(c, "boss.nova", lighten(this.color, 0.35), 22, 1);
        sfx("warn", 0.7);
        break;
      case "snare": {
        const esc = this.escapeAngle(p);
        const spots: [number, number][] = [[p.x, p.y], [p.x + Math.cos(esc) * 150, p.y + Math.sin(esc) * 150]];
        if (this.enraged) spots.push([p.x - Math.cos(esc) * 150, p.y - Math.sin(esc) * 150]);
        for (const [sx, sy] of spots) this.snares.push([clamp(sx, 30, c.W - 30), clamp(sy, 30, c.H - 30), C.SNARE_DELAY]);
        this.say(c, "boss.snare", [150, 220, 90], 22, 1);
        sfx("warn", 0.7);
        break;
      }
      case "aegis":
        this.startAegis(c);
        break;
      case "spiral":
        this.startSpiral(c);
        break;
      case "mines": {
        const cells: [number, number][] = [];
        for (const i of [-1, 0, 1]) for (const j of [-1, 0, 1]) if (i || j) cells.push([i, j]);
        const safe = pick(cells);
        const n = this.bossIndex < 4 ? 3 : 4;
        for (let i = -n; i <= n; i++)
          for (let j = -n; j <= n; j++) {
            if ((i === safe[0] && j === safe[1]) || (Math.abs(i) + Math.abs(j) > 1 && Math.random() < 0.3)) continue;
            if (i * i + j * j > (n + 0.5) ** 2) continue;
            this.hz(p.x + i * C.MINES_STEP, p.y + j * C.MINES_STEP, C.MINES_R, 1.05 + 0.1 * Math.max(Math.abs(i), Math.abs(j)), this.dmg * 0.75 * this.areaK(), c);
          }
        this.say(c, "boss.mines", [255, 120, 90], 24, 1.1);
        fx.shake(5, 0.25);
        sfx("warn", 0.9);
        break;
      }
      case "swarm":
        this.summonMinions(c);
        for (const [cx, cy] of [[this.x, this.y], [p.x, p.y]]) {
          for (let i = 0; i < 5; i++) {
            const a = (i * TAU) / 5 + rand(-0.3, 0.3);
            this.hz(cx + Math.cos(a) * 110, cy + Math.sin(a) * 110, 54, 0.3 + i * 0.1, this.dmg * 0.5 * this.areaK(), c);
          }
        }
        this.say(c, "boss.swarm", [200, 230, 100], 22, 1);
        break;
    }
  }

  private updateTrait(dt: number, c: BossCtx) {
    const p = c.player, fx = c.fx;
    const tk = this.trait.kind;
    if (tk === "vanish" && this.spawnT > 2) {
      if (this.vanishT > 0) {
        this.vanishT -= dt;
        const [dx, dy] = normDir(this.x, this.y, p.x, p.y);
        this.x += dx * this.speed * 1.35 * dt;
        this.y += dy * this.speed * 1.35 * dt;
        if (Math.random() < dt * 6) fx.spark(this.x + rand(-20, 20), this.y + rand(-20, 20), this.color, 0, -30, 0.4, 3);
        if (this.vanishT <= 0) {
          fx.shockwave(this.x, this.y, 170, this.color, 0.4, 6);
          this.say(c, "boss.appear", this.color, 22, 0.8);
          sfx("warn", 0.7);
          this.atkTimer = 0.05;
        }
      } else {
        this.vanishCd -= dt;
        if (this.vanishCd <= 0) {
          this.vanishCd = rand(7, 10.5) * (this.enraged ? 0.65 : 1);
          this.vanishT = this.enraged ? 3 : 2.4;
          fx.ring(this.x, this.y, this.color, 22, 210, 0.45, 3);
          this.say(c, "boss.vanish", this.color, 20);
          sfx("dash", 0.7);
        }
      }
    }
    if (tk === "inferno") {
      if (this.flyT > 0) {
        this.flyT -= dt;
        this.x += this.flyDir[0] * this.speed * 3.6 * dt;
        this.y += this.flyDir[1] * this.speed * 3.6 * dt;
        this.trailAcc += dt;
        if (this.trailAcc >= 0.19) {
          this.trailAcc = 0;
          this.hz(this.x, this.y, 52, 0.35, this.dmg * 0.48 * this.areaK(), c);
        }
        fx.spark(this.x + rand(-30, 30), this.y + rand(-30, 30), [255, 170, 70], rand(-40, 40), rand(-40, 40), 0.4, 5);
        if (this.flyT <= 0) {
          fx.shockwave(this.x, this.y, 230, [255, 140, 60], 0.5, 8);
          fx.shake(10, 0.35);
          sfx("explosion", 0.8);
          for (let i = 0; i < 8; i++) {
            const a = (i * TAU) / 8 + rand(-0.2, 0.2);
            this.hz(this.x + Math.cos(a) * 130, this.y + Math.sin(a) * 130, 58, 0.25 + i * 0.05, this.dmg * 0.62 * this.areaK(), c);
          }
        }
      } else {
        this.flyCd -= dt;
        if (this.flyCd <= 0 && this.spawnT > 2) {
          this.flyCd = rand(8, 12) * (this.enraged ? 0.7 : 1);
          const [px, py] = this.leadPoint(p, 0.5, c);
          this.flyDir = normDir(this.x, this.y, px, py);
          this.flyT = 0.85;
          this.trailAcc = 0;
          this.say(c, "boss.dragon_dive", [255, 170, 80], 24, 1);
          fx.ring(this.x, this.y, [255, 160, 70], 20, 240, 0.45, 4);
          sfx("warn", 0.9);
        }
      }
    }
    if (this.trait.hellfire && this.flyT <= 0 && this.spawnT > 1 && Math.random() < dt * 4.5) {
      fx.spark(this.x + rand(-this.radius, this.radius), this.y + this.radius * 0.5, [255, 170, 80], rand(-14, 14), -40, 0.5, 4);
    }
  }

  private updatePower(dt: number, c: BossCtx) {
    if (this.enraged && this.powerPhase === 0) {
      this.powerPhase = 1;
      if (this.skills.includes("aegis")) this.startAegis(c);
      else this.startSpiral(c);
    }
    if (this.desperate && this.powerPhase === 1) {
      this.powerPhase = 2;
      this.startSpiral(c);
    }
    if (this.aegisHp > 0) {
      this.aegisT -= dt;
      if (this.aegisT <= 0) {
        const heal = this.aegisHp * C.AEGIS_HEAL_K;
        this.hp = Math.min(this.max_hp, this.hp + heal);
        this.aegisHp = 0;
        if (heal > 0.5) {
          this.healFlash = 0.6;
          c.fx.popup(this.x, this.y - this.radius - 30, t("boss.aegis_pop", Math.floor(heal)), AEGIS_COLOR, 22, 1.1, true);
        }
        const n = 14 + 2 * Math.min(5, this.bossIndex);
        for (let i = 0; i < n; i++) this.shoot(c, (i * TAU) / n, 300, 0.55, 8, AEGIS_COLOR);
        c.fx.shockwave(this.x, this.y, 220, AEGIS_COLOR, 0.5, 6);
      }
    }
    if (this.spiralT > 0) {
      if (this.spiralDelay > 0) {
        this.spiralDelay -= dt;
        return;
      }
      this.spiralT -= dt;
      this.spiralAcc += dt;
      const arms = this.enraged || this.desperate ? 4 : 3;
      while (this.spiralAcc >= C.SPIRAL_EVERY) {
        this.spiralAcc -= C.SPIRAL_EVERY;
        for (let i = 0; i < arms; i++) this.shoot(c, this.spiralAng + (i * TAU) / arms, C.SPIRAL_SPEED, 0.42, 7, [255, 110, 150]);
        this.spiralAng += 0.21 * (this.strafeDir > 0 ? 1 : -1);
      }
    }
  }

  private updateNewSkills(dt: number, c: BossCtx) {
    const p = c.player, fx = c.fx;
    if (this.wardT > 0) {
      this.wardT -= dt;
      if (this.wardPop > 0) this.wardPop -= dt;
      if (this.wardT <= 0) fx.ring(this.x, this.y, WARD_COLOR, 20, 280, 0.4, 3);
    }
    if (this.veilT > 0) {
      this.veilT -= dt;
      const sx = -(p.y - this.y), sy = p.x - this.x;
      const ln = Math.hypot(sx, sy) || 1;
      const [dx, dy] = normDir(this.x, this.y, p.x, p.y);
      this.x += (dx * 1.1 + (sx / ln) * 0.6 * this.strafeDir) * this.speed * 1.4 * dt;
      this.y += (dy * 1.1 + (sy / ln) * 0.6 * this.strafeDir) * this.speed * 1.4 * dt;
      if (Math.random() < dt * 6) fx.spark(this.x + rand(-20, 20), this.y + rand(-20, 20), this.color, 0, -30, 0.4, 3);
      if (this.veilT <= 0) {
        fx.shockwave(this.x, this.y, 190, this.color, 0.45, 7);
        this.say(c, "boss.appear", this.color, 22, 0.8);
        this.hz(this.x, this.y, 150, 0.3, this.dmg * 0.8 * this.areaK(), c);
        this.atkTimer = 0.05;
        sfx("warn", 0.7);
      }
    }
    if (this.drainT > 0) {
      this.drainT -= dt;
      if (!p.alive || dist(this.x, this.y, p.x, p.y) > C.DRAIN_RANGE) {
        this.drainT = 0;
        fx.popup(p.x, p.y - 40, t("boss.drain_break"), [255, 200, 200], 20, 0.8, true);
        sfx("crit", 0.5);
      } else {
        this.drainAcc += dt;
        while (this.drainAcc >= C.DRAIN_TICK && this.drainT > 0) {
          this.drainAcc -= C.DRAIN_TICK;
          const amt = Math.min(Math.max(1, this.dmg * C.DRAIN_DMG_K * this.areaK()), Math.max(2, p.max_hp * 0.022));
          const hp0 = p.hp;
          (p as any).statusTick(amt, fx, this.name, DRAIN_COLOR);
          const dealt = Math.max(0, hp0 - p.hp);
          if (dealt > 0) this.onDamageDealt((dealt * C.DRAIN_HEAL_K) / Math.max(0.05, this.lifesteal));
          fx.spark(p.x, p.y, DRAIN_COLOR, (this.x - p.x) * 1.5, (this.y - p.y) * 1.5, 0.45, 4);
        }
      }
    }
    if (this.novaN > 0) {
      this.novaCd -= dt;
      if (this.novaCd <= 0) {
        this.novaCd = 0.42;
        const n = 16 + 2 * Math.min(4, this.bossIndex);
        const gap = Math.floor(Math.random() * n);
        for (let i = 0; i < n; i++) {
          if (i === gap || i === (gap + 1) % n) continue;
          this.shoot(c, this.novaAng + (i * TAU) / n, 250, 0.45, 7, lighten(this.color, 0.35));
        }
        this.novaAng += TAU / n / 2;
        this.novaN--;
        fx.shockwave(this.x, this.y, 120, lighten(this.color, 0.35), 0.3, 4);
      }
    }
    if (this.snares.length) {
      const keep: [number, number, number][] = [];
      for (const sn of this.snares) {
        sn[2] -= dt;
        if (sn[2] > 0) {
          keep.push(sn);
          continue;
        }
        fx.burst(sn[0], sn[1], [120, 200, 80], 16, 170, 0.45, 3.5);
        if (p.alive && dist(sn[0], sn[1], p.x, p.y) < C.SNARE_R + p.radius - 4) {
          this.hitPlayer(p, this.dmg * 0.45 * this.areaK(), fx, sn[0], sn[1]);
          p.applySlow(0.25, C.SNARE_ROOT);
          fx.popup(p.x, p.y - 42, t("boss.rooted"), [170, 230, 110], 20, 0.9, true);
        }
      }
      this.snares = keep;
    }
  }

  private updateSkills(dt: number, c: BossCtx, d: number) {
    const p = c.player, fx = c.fx;
    this.updateNewSkills(dt, c);
    if (this.pullT > 0) {
      this.pullT -= dt;
      if (p.alive) {
        const [dx, dy] = normDir(p.x, p.y, this.x, this.y);
        const pv = 470 * (this.enraged ? 1.25 : 1);
        p.x = clamp(p.x + dx * pv * dt, p.radius, c.W - p.radius);
        p.y = clamp(p.y + dy * pv * dt, p.radius, c.H - p.radius);
        if (Math.random() < dt * 14) fx.spark(p.x + rand(-24, 24), p.y + rand(-24, 24), [200, 140, 255], dx * 160, dy * 160, 0.35, 2.6);
      }
    }
    if (this.buffT > 0) {
      this.buffT -= dt;
      if (Math.random() < dt * 5) fx.spark(this.x + rand(-this.radius, this.radius), this.y + rand(-this.radius, this.radius), [255, 170, 80], 0, -60, 0.45, 3);
    }
    const canHunt = this.fleeTimer <= 0 && this.chargeT <= 0 && this.flyT <= 0 && this.pullT <= 0 && this.spawnT > 2;
    if (canHunt && d > C.BOSS_HUNT_DIST) {
      this.huntCheck += dt;
      if (this.huntCheck >= C.BOSS_HUNT_DELAY && this.huntT <= 0) {
        this.huntT = C.BOSS_HUNT_TIME;
        this.huntCheck = 0;
        this.say(c, "boss.hunt", [255, 90, 70], 24, 1);
        sfx("warn", 0.8);
      }
    } else this.huntCheck = 0;
    if (this.huntT > 0) {
      this.huntT -= dt;
      if (d < this.wantDist * 1.15) this.huntT = 0;
    }
    this.strafeT -= dt;
    if (this.strafeT <= 0) {
      this.strafeT = rand(1.4, 2.8);
      this.strafeDir = -this.strafeDir;
    }
    if (this.spawnT > 2.5 && this.chargeT <= 0 && this.flyT <= 0 && this.pullT <= 0 && !this.isHidden()) {
      this.skillCd -= dt;
      if (this.skillCd <= 0) {
        if (this.telegraph) this.skillCd = 0.15;
        else {
          this.skillCd = this.skillInterval();
          this.castSkill(c);
        }
      }
    }
  }

  private fireVolley(c: BossCtx) {
    const p = c.player, fx = c.fx;
    const bi = this.bossIndex;
    const eng = this.enraged || this.desperate;
    if (this.kind === "warlord") {
      const spd = 420 + bi * 14;
      const base = this.aimAngle(p, spd, 0.1, c);
      const n = 3 + Math.min(3, Math.floor((bi - 1) / 2));
      for (let i = 0; i < n; i++) this.shoot(c, base + (i - (n - 1) / 2) * 0.16, spd, 0.5, 7);
      sfx("shoot_c", 0.5);
    } else if (this.kind === "witch") {
      const spd = 290 + bi * 14;
      const base = this.aimAngle(p, spd, 0.18, c);
      const n = 4 + Math.min(3, bi) + (eng ? 2 : 0);
      for (let i = 0; i < n; i++) this.shoot(c, base + (i - (n - 1) / 2) * (1.05 / Math.max(1, n - 1)), spd, 0.46, 8, [175, 110, 235], p, 1.9 + 0.12 * bi, 40);
      fx.ring(this.x, this.y, [175, 110, 235], 14, 150, 0.35, 3);
      sfx("shoot_c", 0.55);
    } else if (this.kind === "colossus") {
      const n = 10 + bi * 2 + (eng ? 4 : 0);
      const off = Math.random() * TAU;
      for (let i = 0; i < n; i++) this.shoot(c, off + (i * TAU) / n, 205 + bi * 8, 0.42, 11, [150, 165, 195]);
      fx.shockwave(this.x, this.y, 150, this.color, 0.4, 6);
      fx.shake(5, 0.22);
      sfx("explosion", 0.5);
    } else if (this.kind === "reaper") {
      const spd = 470 + bi * 16;
      const base = this.aimAngle(p, spd, 0.07, c);
      for (let w = 0; w < 2; w++) for (const o of [-0.22, 0, 0.22]) this.shoot(c, base + o + w * 0.11, spd, 0.4, 6, [120, 240, 210]);
      sfx("shoot_c", 0.5);
    } else if (this.kind === "dragon") {
      const spd = 275 + bi * 12;
      const base = this.aimAngle(p, spd, 0.16, c);
      const n = 3 + Math.min(3, Math.floor(bi / 2)) + (eng ? 2 : 0);
      for (let i = 0; i < n; i++) this.shoot(c, base + (i - (n - 1) / 2) * 0.22, spd, 0.52, 13, [255, 130, 50], p, 1.1 + 0.08 * bi, 70);
      const ss = 360 + bi * 16;
      const sb = this.aimAngle(p, ss, 0.14, c);
      for (let i = 0; i < 4 + bi; i++) this.shoot(c, sb + rand(-0.8, 0.8), ss, 0.26, 6, [255, 205, 110]);
      fx.ring(this.x, this.y, [255, 150, 60], 16, 180, 0.4, 3.5);
      sfx("shoot_c", 0.6);
    } else {
      const spd = 225 + bi * 12;
      const base = this.aimAngle(p, spd, 0.2, c);
      const n = 5 + Math.min(3, bi) + (eng ? 3 : 0);
      for (let i = 0; i < n; i++) this.shoot(c, base + rand(-0.9, 0.9), spd, 0.4, 9, [230, 190, 70], p, 1.5 + 0.1 * bi, 55);
      fx.ring(this.x, this.y, [230, 190, 70], 12, 130, 0.35, 3);
      sfx("shoot_c", 0.5);
    }
  }

  private startAttack(c: BossCtx) {
    const p = c.player, fx = c.fx;
    const bi = this.bossIndex;
    if (this.kind === "warlord") {
      if (bi >= 2 && Math.random() < 0.38) {
        this.setTelegraph("hazard_ring", 0, 0, 0, this.enraged ? 0.48 : 0.6);
        fx.ring(this.x, this.y, this.color, 20, 180, 0.45, 3);
        return;
      }
      const n = (this.enraged ? 9 : 5) + Math.min(4, bi - 1);
      const spread = this.enraged ? 0.3 : 0.38;
      const base = this.aimAngle(p, 400, 0.12, c);
      this.setTelegraph("beam", Array.from({ length: n }, (_, i) => base + (i - (n - 1) / 2) * spread), 0, 0, 0.48);
    } else if (this.kind === "witch") {
      if (Math.random() < (bi >= 2 ? 0.5 : 0.3)) this.setTelegraph("barrage", this.aimAngle(p, 330 + bi * 20, 0.16, c), 0, 0, 0.45);
      else {
        const [px, py] = this.leadPoint(p, 0.95, c);
        this.setTelegraph("ring_player", px, py, this.ringRadius(), this.enraged ? 0.62 : 0.8);
        fx.ring(px, py, this.color, this.enraged ? 24 : 20, 150, 0.5, 3);
      }
    } else if (this.kind === "reaper") {
      const [px, py] = this.leadPoint(p, 0.85, c);
      if (Math.random() < 0.5) this.setTelegraph("scythe", px, py, this.enraged ? 120 : 100, this.enraged ? 0.5 : 0.62);
      else {
        const ang = this.aimAngle(p, 400, 0.1, c);
        const offs = this.enraged ? [-0.26, 0, 0.26] : [-0.2, 0.2];
        this.setTelegraph("beam", offs.map((o) => ang + o), 0, 0, 0.48);
      }
    } else if (this.kind === "hive") {
      const [px, py] = this.leadPoint(p, 1, c);
      if (bi >= 2 && Math.random() < 0.4) this.setTelegraph("barrage", this.aimAngle(p, 330 + bi * 20, 0.18, c), 0, 0, 0.5);
      else {
        this.setTelegraph("spore", px, py, 90, this.enraged ? 0.7 : 0.85);
        fx.ring(this.x, this.y, this.color, 16, 140, 0.45, 3);
      }
    } else if (this.kind === "dragon") {
      const [px, py] = this.leadPoint(p, 0.9, c);
      const ang = Math.atan2(py - this.y, px - this.x);
      const roll = Math.random();
      if (roll < 0.5) {
        this.setTelegraph("breath", ang, 0, 0, this.enraged ? 0.62 : 0.8);
        this.say(c, "boss.breath", [255, 170, 80], 22, 0.9);
      } else if (roll < 0.78) this.setTelegraph("firewall", px, py, ang, 0.58);
      else this.setTelegraph("wingburst", this.x, this.y, 200, 0.55);
    } else {
      const [px, py] = this.leadPoint(p, 0.95, c);
      if (bi >= 2 && Math.random() < 0.45) {
        this.setTelegraph("charge", px, py, 0, 0.62);
        this.say(c, "boss.charge", [255, 150, 60], 22, 0.8);
      } else {
        this.setTelegraph("slam", px, py, this.enraged ? 165 : 140, this.enraged ? 0.52 : 0.68);
        fx.popup(px, py - 40, "!", [255, 90, 70], 30, 0.7, true);
      }
    }
    sfx("warn", 0.7);
  }

  private unleash(kind: string, a: any, b: number, cc: number, c: BossCtx) {
    const fx = c.fx;
    switch (kind) {
      case "beam": {
        const speed = this.enraged ? 430 : 375;
        const angs: number[] = Array.isArray(a) ? a : [a];
        for (const ang of angs) {
          c.projectiles.push(new EnemyProjectile(this.x, this.y, Math.cos(ang) * speed, Math.sin(ang) * speed, this.dmg * 0.9, this.color, 8, 4, null, 0, 0, this, 0, "boss"));
        }
        sfx("shoot_c", 0.6);
        break;
      }
      case "hazard_ring": {
        const n = this.enraged ? 11 : 8;
        for (let i = 0; i < n; i++) {
          const ang = (i * TAU) / n;
          this.hz(this.x + Math.cos(ang) * 150, this.y + Math.sin(ang) * 150, 56, 0.9, this.dmg, c);
        }
        break;
      }
      case "ring_player": {
        const n = this.ringCount();
        for (let i = 0; i < n; i++) {
          const ang = (i * TAU) / n + rand(-0.05, 0.05);
          this.hz(a + Math.cos(ang) * cc, b + Math.sin(ang) * cc, C.BOSS_RING_HAZARD_R, 0.45, this.dmg * 0.8, c);
        }
        fx.shockwave(a, b, cc, this.color, 0.45, 6);
        break;
      }
      case "barrage": {
        const n = 7 + this.bossIndex * 2 + (this.enraged ? 3 : 0);
        const speed = 330 + this.bossIndex * 20;
        const col: RGB = this.kind === "witch" ? [210, 120, 250] : [245, 205, 90];
        for (let i = 0; i < n; i++) this.shoot(c, a + (i - (n - 1) / 2) * (0.62 / Math.max(1, n - 1)), speed, 0.48, 7, col);
        sfx("shoot_c", 0.7);
        break;
      }
      case "lunge":
        this.chargeDir = normDir(this.x, this.y, a, b);
        this.chargeT = 0.55;
        this.huntT = 0;
        fx.shockwave(this.x, this.y, 150, this.trait.color, 0.35, 5);
        fx.shake(6, 0.22);
        sfx("dash", 0.8);
        break;
      case "wall": {
        const nx = -Math.sin(cc), ny = Math.cos(cc);
        const n = 9 + this.bossIndex;
        for (let i = 0; i < n; i++) {
          const off = (i - (n - 1) / 2) * 76;
          this.hz(a + nx * off, b + ny * off, 52, 0.05 + Math.abs(i - (n - 1) / 2) * 0.05, this.dmg * 0.55 * this.areaK(), c);
        }
        sfx("explosion", 0.5);
        break;
      }
      case "cage": {
        const n = this.ringCount();
        for (let i = 0; i < n; i++) {
          const ang = (i * TAU) / n + rand(-0.05, 0.05);
          this.hz(a + Math.cos(ang) * cc, b + Math.sin(ang) * cc, C.BOSS_RING_HAZARD_R, 0.4, this.dmg * 0.55 * this.areaK(), c);
        }
        fx.shockwave(a, b, cc, this.trait.color, 0.45, 6);
        break;
      }
      case "meteor": {
        const n = 7 + this.bossIndex * 2 + (this.enraged ? 3 : 0);
        for (let i = 0; i < n; i++) {
          const ang = Math.random() * TAU, rad = Math.random() * 210;
          this.hz(a + Math.cos(ang) * rad, b + Math.sin(ang) * rad, 58, 0.1 + i * 0.13, this.dmg * 0.6 * this.areaK(), c);
        }
        fx.shake(5, 0.3);
        sfx("explosion", 0.55);
        break;
      }
      case "pull":
        this.pullT = 0.85;
        fx.shockwave(this.x, this.y, 420, [200, 130, 255], 0.5, 6);
        for (let i = 0; i < 26; i++) {
          const a2 = (i * TAU) / 26;
          fx.spark(this.x + Math.cos(a2) * 230, this.y + Math.sin(a2) * 230, [200, 130, 255], -Math.cos(a2) * 320, -Math.sin(a2) * 320, 0.6, 3.2);
        }
        if (c.player.alive) c.player.applySlow(0.7, 1.6);
        sfx("warn", 0.9);
        break;
      case "charge":
        this.chargeDir = normDir(this.x, this.y, a, b);
        this.chargeT = 0.62;
        fx.shockwave(this.x, this.y, 140, this.color, 0.35, 5);
        fx.shake(7, 0.25);
        sfx("bonk", 0.6);
        break;
      case "scythe":
        this.hz(a, b, cc, 0.04, this.dmg * 1.25, c);
        fx.shockwave(a, b, cc, this.color, 0.3, 5);
        fx.shake(6, 0.22);
        sfx("bonk", 0.7);
        break;
      case "spore": {
        const n = this.enraged ? 6 : 4;
        for (let i = 0; i < n; i++) {
          const ang = (i * TAU) / n + rand(-0.3, 0.3), rad = rand(40, 130);
          this.hz(a + Math.cos(ang) * rad, b + Math.sin(ang) * rad, 50, 0.2 + i * 0.12, this.dmg * 0.85, c);
        }
        break;
      }
      case "breath": {
        const steps = 7 + this.bossIndex;
        for (let i = 0; i < steps; i++) {
          const d = 90 + i * 74;
          this.hz(this.x + Math.cos(a) * d, this.y + Math.sin(a) * d, 60, 0.06 * i, this.dmg * 0.6 * this.areaK(), c);
        }
        const n = 9 + this.bossIndex * 2;
        for (let i = 0; i < n; i++) this.shoot(c, a + rand(-0.26, 0.26), 330 + rand(-40, 90), 0.34, 9, [255, 150 + Math.floor(Math.random() * 60), 60]);
        fx.shockwave(this.x, this.y, 130, [255, 150, 60], 0.35, 5);
        fx.shake(6, 0.25);
        sfx("explosion", 0.6);
        break;
      }
      case "firewall": {
        const nx = -Math.sin(cc), ny = Math.cos(cc);
        const n = 7 + this.bossIndex;
        for (let i = 0; i < n; i++) {
          const off = (i - (n - 1) / 2) * 88;
          this.hz(a + nx * off, b + ny * off, 54, 0.05 + Math.abs(i - (n - 1) / 2) * 0.05, this.dmg * 0.85 * this.areaK(), c);
        }
        sfx("explosion", 0.5);
        break;
      }
      case "wingburst": {
        const n = 14 + this.bossIndex * 2;
        for (let i = 0; i < n; i++) this.shoot(c, (i * TAU) / n + rand(-0.08, 0.08), 250 + this.bossIndex * 10, 0.38, 8, [255, 170, 70]);
        fx.shockwave(this.x, this.y, cc, [255, 160, 70], 0.45, 7);
        fx.shake(7, 0.28);
        sfx("bonk", 0.7);
        break;
      }
      case "slam":
        this.hz(a, b, cc, 0.05, this.dmg * 1.5, c);
        fx.shake(8, 0.3);
        if (this.enraged) for (let k = 0; k < 2; k++) this.hz(a + rand(-80, 80), b + rand(-80, 80), cc * 0.8, 0.3 + k * 0.28, this.dmg * 1.15, c);
        break;
    }
  }

  update(dt: number, c: BossCtx) {
    if (!this.alive) return;
    const p = c.player, fx = c.fx;
    this.spawnT += dt;
    this.fightTime += dt;
    const cap = this.healRate ?? this.max_hp * C.BOSS_LIFESTEAL_CAP;
    this.healBudget = Math.min(cap, this.healBudget + cap * dt);
    if (this.intakeBudget !== null) this.intakeBudget = Math.min(this.max_hp * C.BOSS_BURST_POOL, this.intakeBudget + (this.max_hp / this.minFightTime) * dt);
    if (this.healFlash > 0) this.healFlash -= dt;
    if (this.touchCd > 0) this.touchCd -= dt;
    if (this.slowTimer > 0) {
      this.slowTimer -= dt;
      if (this.slowTimer <= 0) this.slowMult = 1;
    }
    if (this.poisonDps > 0) {
      this.poisonAcc += dt;
      while (this.poisonAcc >= 0.5 && this.alive) {
        this.poisonAcc -= 0.5;
        if (this.takeDamage(this.poisonDps * 0.5, false, fx, 0, 0, true)) c.kill(this);
      }
      if (!this.alive) return;
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
    const scaleIn = 1 - Math.pow(1 - clamp(this.spawnT / 0.6, 0, 1), 3);
    if (p.alive) {
      const [tfx, tfy] = normDir(this.x, this.y, p.x, p.y);
      const k = Math.min(1, dt * 5);
      this.faceX += (tfx - this.faceX) * k;
      this.faceY += (tfy - this.faceY) * k;
    }
    this.gait += dt * (this.flyT > 0 ? 7 : 3.4);
    if (!this.enraged && this.hp < this.max_hp * 0.62) {
      this.enraged = true;
      this.say(c, "boss.enraged", [255, 90, 70], 26, 1.2);
      fx.flash([255, 60, 40], 0.3);
    }
    if (!this.desperate && this.hp < this.max_hp * 0.26) {
      this.desperate = true;
      this.summonCd = Math.min(this.summonCd, 1);
      this.say(c, "boss.desperate", [255, 190, 60], 28, 1.3);
      fx.flash([255, 210, 80], 0.25);
      sfx("warn", 0.9);
    }
    if (this.enraged || this.kind === "hive") {
      this.summonCd -= dt;
      if (this.summonCd <= 0 && this.spawnT > 1) {
        const base = this.kind === "hive" ? 4.2 : rand(5, 7);
        this.summonCd = base * (this.desperate ? 0.55 : 1);
        this.summonMinions(c);
        this.fleeTimer = Math.max(this.fleeTimer, this.desperate ? 2.4 : 1.6);
      }
    }
    this.updateTrait(dt, c);
    if (this.kind === "reaper" && this.spawnT > 1.2) {
      this.teleportCd -= dt;
      if (this.teleportCd <= 0) {
        this.teleportCd = rand(2.8, 4.4) * (this.enraged ? 0.55 : 1);
        fx.ring(this.x, this.y, this.color, 16, 180, 0.3, 2.5);
        const ml = Math.hypot(p.vx, p.vy);
        const ang = ml > 40 ? Math.atan2(-p.vy / ml, -p.vx / ml) + rand(-0.5, 0.5) : Math.random() * TAU;
        const rad = this.wantDist * 0.62;
        this.x = clamp(p.x + Math.cos(ang) * rad, this.radius, c.W - this.radius);
        this.y = clamp(p.y + Math.sin(ang) * rad, this.radius, c.H - this.radius);
        fx.ring(this.x, this.y, this.color, 22, 240, 0.38, 3);
        sfx("warn", 0.5);
        this.fleeTimer = 0;
        this.atkTimer = Math.min(this.atkTimer, 0.18);
      }
    }
    const d = dist(this.x, this.y, p.x, p.y);
    const [dx, dy] = normDir(this.x, this.y, p.x, p.y);
    this.updateSkills(dt, c, d);
    this.updatePower(dt, c);
    const sm = this.slowTimer > 0 ? this.slowMult : 1;
    const spd = this.speed * sm;
    if (this.flyT > 0) {
      /* uçuş updateTrait'te */
    } else if (this.chargeT > 0) {
      this.chargeT -= dt;
      const cs = this.speed * 5.4;
      this.x += this.chargeDir[0] * cs * dt;
      this.y += this.chargeDir[1] * cs * dt;
      fx.spark(this.x + rand(-this.radius, this.radius), this.y + rand(-this.radius, this.radius), this.color, rand(-40, 40), rand(-40, 40), 0.35, 5);
      if (this.x <= this.radius || this.x >= c.W - this.radius || this.y <= this.radius || this.y >= c.H - this.radius) {
        this.chargeT = 0;
        fx.shockwave(this.x, this.y, 190, this.color, 0.5, 7);
        fx.shake(9, 0.35);
        sfx("bonk", 0.8);
      }
    } else if (this.fleeTimer > 0) {
      this.fleeTimer -= dt;
      if (d >= C.BOSS_FLEE_MAX_DIST) this.fleeTimer = 0;
      else {
        const fk = this.desperate ? 1.9 : 1.5;
        this.x -= dx * spd * fk * dt * scaleIn;
        this.y -= dy * spd * fk * dt * scaleIn;
      }
    } else if (this.huntT > 0) {
      let hs = Math.max(spd * C.BOSS_HUNT_SPEED, p.effSpeed() * C.BOSS_HUNT_MIN_VS_PLAYER);
      if (this.buffT > 0) hs *= C.BOSS_BUFF_SPEED;
      this.x += dx * hs * dt * scaleIn;
      this.y += dy * hs * dt * scaleIn;
      if (Math.random() < dt * 8) fx.spark(this.x - dx * this.radius, this.y - dy * this.radius, this.trait.color, -dx * 90, -dy * 90, 0.35, 3);
    } else {
      let sk = this.enraged ? 1.7 : 1.2;
      if (this.buffT > 0) sk *= C.BOSS_BUFF_SPEED;
      if (d > this.wantDist + 200) sk *= 1.55;
      let stk = this.enraged ? 0.95 : 0.75;
      if (this.buffT > 0) stk *= C.BOSS_BUFF_SPEED;
      this.x += -dy * spd * stk * this.strafeDir * dt * scaleIn;
      this.y += dx * spd * stk * this.strafeDir * dt * scaleIn;
      if (d > this.wantDist + 20) {
        this.x += dx * spd * sk * dt * scaleIn;
        this.y += dy * spd * sk * dt * scaleIn;
      } else if (d < this.wantDist - 20) {
        this.x -= dx * spd * 0.6 * dt * scaleIn;
        this.y -= dy * spd * 0.6 * dt * scaleIn;
      }
    }
    this.x = clamp(this.x, this.radius, c.W - this.radius);
    this.y = clamp(this.y, this.radius, c.H - this.radius);
    if (this.hitFlash > 0) this.hitFlash -= dt;
    if (this.spawnT > 1.5 && this.chargeT <= 0 && this.flyT <= 0 && !this.isHidden()) {
      this.volleyCd -= dt;
      if (this.volleyCd <= 0) {
        this.volleyCd = this.volleyInterval();
        this.fireVolley(c);
      }
    }
    if (this.telegraph) {
      const tg = this.telegraph;
      tg[4] -= dt;
      if (tg[4] <= 0) {
        this.telegraph = null;
        this.unleash(tg[0], tg[1], tg[2], tg[3], c);
      }
    } else {
      this.atkTimer -= dt;
      if (this.atkTimer <= 0 && this.spawnT > 1 && this.flyT <= 0 && !this.isHidden()) {
        let cad = this.desperate ? 0.32 : this.enraged ? 0.46 : 0.85;
        cad *= Math.max(0.45, 1 - (this.bossIndex - 1) * 0.11);
        if (this.buffT > 0) cad *= C.BOSS_BUFF_CADENCE;
        this.atkTimer = rand(0.9, 1.45) * cad;
        this.startAttack(c);
      }
    }
    if (p.alive && this.touchCd <= 0 && dist(this.x, this.y, p.x, p.y) < this.hit_r + p.radius - 3) {
      this.touchCd = 0.42;
      this.hitPlayer(p, this.dmg * (this.chargeT > 0 || this.flyT > 0 ? 1.7 : 1), fx);
    }
  }

  takeDamage(amount: number, crit: boolean, fx: FX, _kx = 0, _ky = 0, quiet = false): boolean {
    if (this.wardT > 0) {
      if (!quiet && this.wardPop <= 0) {
        this.wardPop = 0.35;
        fx.popup(this.x + rand(-24, 24), this.y - this.radius, t("boss.immune"), WARD_COLOR, 15, 0.4, true);
      }
      return false;
    }
    amount *= 1 - this.armor;
    if (this.aegisHp > 0 && amount > 0) {
      const soak = Math.min(this.aegisHp, amount * (1 - C.AEGIS_LEAK));
      this.aegisHp -= soak;
      amount -= soak;
      if (this.aegisHp <= 0.5) {
        this.aegisHp = 0;
        fx.popup(this.x, this.y - this.radius - 34, t("boss.aegis_break"), AEGIS_COLOR, 24, 1, true);
        fx.ring(this.x, this.y, AEGIS_COLOR, 30, 320, 0.55, 4);
        sfx("crit", 0.9);
      }
    }
    if (this.intakeBudget === null) this.intakeBudget = this.max_hp * C.BOSS_BURST_POOL;
    if (amount > this.intakeBudget) amount = Math.max(0, this.intakeBudget);
    this.intakeBudget -= amount;
    if (this.alive) DMG.note(Math.min(amount, Math.max(0, this.hp)));
    this.hp -= amount;
    this.hitFlash = 0.1;
    if (!quiet && amount >= 1) fx.popup(this.x + rand(-20, 20), this.y - this.radius, `${Math.floor(amount)}${crit ? "!" : ""}`, crit ? [255, 230, 120] : [255, 255, 255], crit ? 20 : 15, 0.45);
    if (this.hp <= 0 && this.alive) {
      this.alive = false;
      fx.burst(this.x, this.y, this.color, 40, 260, 0.8, 5);
      fx.shockwave(this.x, this.y, 260, this.color, 0.6, 8);
      fx.flash(this.color, 0.5);
      fx.shake(12, 0.4);
      sfx("explosion", 1);
      return true;
    }
    return false;
  }
}

/** Dalgadaki patronların toplam canını oyuncunun gücüne göre ölçekler. */
export function scaleBossesToPlayer(bosses: Boss[], est: number) {
  if (!bosses.length) return 1;
  const n = bosses.length;
  let baseTotal = 0, arm = 0, champ = 1;
  for (const b of bosses) {
    baseTotal += b.max_hp;
    arm += b.armor;
    champ = Math.max(champ, b.champion);
  }
  arm /= n;
  let want = est * C.BOSS_FIGHT_UPTIME * C.BOSS_FIGHT_TARGET * C.BOSS_HP_BONUS;
  want *= Math.max(0.4, 1 - arm);
  if (n > 1) want *= C.MULTI_BOSS_TOTAL;
  if (n === 1 && champ > 1) want *= C.MULTI_BOSS_TOTAL * (1 + 0.35 * (champ - 2));
  const scale = clamp(want / Math.max(1, baseTotal), C.BOSS_HP_SCALE_MIN, C.BOSS_HP_SCALE_MAX);
  const healRate = (est * C.BOSS_LIFESTEAL_VS_DPS) / n;
  for (const b of bosses) {
    b.max_hp *= scale;
    b.hp = b.max_hp;
    b.healRate = healRate;
    b.minFightTime = C.BOSS_MIN_FIGHT_TIME / n;
  }
  return scale;
}
