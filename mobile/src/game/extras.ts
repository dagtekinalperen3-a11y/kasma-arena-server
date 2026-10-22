/**
 * Koşu yan sistemleri — Python sürümünden birebir:
 *  - KOŞU GÖREVLERİ (roll_quests / update_quests)
 *  - GEZGİN TÜCCAR ve YEMİNLER (spawn_merchant / apply_oath ...)
 *  - LANETLİ MAĞARA (spawn_cursed_shrine / accept_curse ...)
 *  - ÖLÜ ÇAĞIRICI cesetleri (_on_cursed_death / _necro_raise)
 */
import { clamp, dist, rand, shuffle, pick, TAU, RGB, lighten, stackBonus } from "../core/util";
import { sfx } from "../core/audio";
import { haptic } from "../core/native";
import { t, fmtPct } from "../core/i18n";
import * as B from "./balance";
import { GD, WEAPON_BY_KEY, ENEMY_COLORS } from "./data";
import { Enemy, makeMapEnemy } from "./enemy";
import { CURSE_KINDS } from "./waves";
import { zigzag } from "./fx";
import type { Run, Target } from "./run";

const C = GD;
const GREEN: RGB = [110, 230, 140];
const MERCHANT_COLOR = C.MERCHANT_COLOR as RGB;
export const CURSE_COLOR = C.CURSE_COLOR as RGB;
export const CURSE_COLOR2 = C.CURSE_COLOR2 as RGB;
export const CURSE_RED = C.CURSE_RED as RGB;
export const OATHS: [string, string, RGB][] = C.OATHS;
export const QUEST_DEFS: Record<string, [string, RGB, (number | null)[]]> = C.QUEST_DEFS;
export const QUEST_GEMS: number[] = C.QUEST_GEMS;
export const QUEST_TIER_COLORS: RGB[] = C.QUEST_TIER_COLORS;

export interface Quest {
  key: string;
  tier: number;
  goal: number;
  done: boolean;
}

export class Merchant {
  t = rand(0, 10);
  done = false;
  constructor(public x: number, public y: number) {}
  inRange(p: { x: number; y: number }) {
    return dist(this.x, this.y, p.x, p.y) < 110;
  }
  update(dt: number) {
    this.t += dt;
  }
}

export class CursedShrine {
  r = 64;
  t = rand(0, 10);
  alive = true;
  opened = false;
  used = false;
  discovered = false;
  dieT = 0;
  lid = 0;
  constructor(public x: number, public y: number) {}
  inRange(p: { x: number; y: number }) {
    return !this.used && dist(this.x, this.y + 30, p.x, p.y) < 104;
  }
  update(dt: number) {
    this.t += dt;
    const target = this.opened ? 1 : 0;
    this.lid += (target - this.lid) * Math.min(1, dt * 6);
    if (this.used) {
      this.dieT += dt;
      if (this.dieT > 1.6) this.alive = false;
    }
  }
}

export interface CurseOffer {
  kind: "pair" | "gamble" | "blood";
  reward: string;
  tier: number;
  vals: Record<string, number>;
  lines: string[];
  curse: string | null;
  win?: number;
}

// ------------------------------------------------------------------
// sayılar
// ------------------------------------------------------------------
export function oathValues(key: string, tier = 0): number[] {
  const ti = clamp(Math.floor(tier), 0, C.OATH_TIER_MULT.length - 1);
  const m = C.OATH_TIER_MULT[ti];
  switch (key) {
    case "glass": return [0.3 * m];
    case "gold_fever": return [0.35 * m];
    case "turtle": return [Math.round(50 * m), 0.08 * m];
    case "scholar": return [0.25 * m];
    case "gambler": return [0.5 * m];
    case "blood": return [0.02 * m];
    case "wind": return [0.12 * m, 0.25 * m];
    case "bulwark": return [3 + ti, Math.round(C.OATH_BULWARK_EVERY / m)];
    case "hunter": return [1 * m];
    case "feast": return [0.25 * m];
    case "hoard": return [Math.round((350 * m) / 10) * 10];
    case "hawkeye": return [0.12 * m, 0.25 * m];
  }
  return [];
}

export function oathUpText(key: string, tier = 0) {
  const v = oathValues(key, tier);
  const pct = (x: number) => "+" + fmtPct(x, 1);
  let args: string[];
  if (key === "turtle") args = [`+${v[0]}`, pct(v[1])];
  else if (key === "bulwark") args = [`+${v[0]}`, `${v[1]}`];
  else if (key === "hoard") args = [String(v[0])];
  else if (key === "hunter") args = [pct(stackBonus(0.385, v[0], 3.5))];
  else args = v.map(pct);
  return t(`oath.${key}.up`, ...args);
}

export function merchantRerollCost(wave: number, used: number) {
  const steps: number[] = C.MERCHANT_REROLL_STEP;
  const k = steps[Math.min(used, steps.length - 1)];
  return Math.floor((C.MERCHANT_REROLL_BASE + C.MERCHANT_REROLL_WAVE * Math.max(1, wave)) * k);
}

export function cursedRewardValues(key: string, tier: number, wave: number): Record<string, number> {
  const m = C.CURSE_TIER_MULT[clamp(Math.floor(tier), 0, C.CURSE_TIER_MULT.length - 1)];
  switch (key) {
    case "power": return { levels: Math.round(5 * m), hp: Math.floor(100 * m), dmg: 0.5 * m };
    case "fortune": return { levels: Math.round(3 * m), luck: 0.12 * m };
    case "arsenal": return { wlevels: Math.round(2 * m), boost: 0.1 * m };
    case "treasure": return { gold: Math.floor((600 + 120 * Math.max(1, wave)) * m * C.GOLD_TRIM), coin: 0.25 * m };
    case "fortress": return { hp: Math.floor(250 * m), armor: 0.08 * m, shields: Math.round(2 * m) };
    case "edge": return { crit: 0.12 * m, critd: 0.5 * m, aspd: 0.15 * m };
  }
  return {};
}

export function cursedRewardLines(vals: Record<string, number>) {
  const out: string[] = [];
  const p1 = (x: number) => fmtPct(x, 1);
  if (vals.levels) out.push(t("cu.r_levels", vals.levels));
  if (vals.wlevels) out.push(t("cu.r_wlevels", vals.wlevels));
  if (vals.hp) out.push(t("cu.r_hp", vals.hp));
  if (vals.dmg) out.push(t("cu.r_dmg", p1(vals.dmg)));
  if (vals.luck) out.push(t("cu.r_luck", p1(vals.luck)));
  if (vals.boost) out.push(t("cu.r_boost", p1(vals.boost)));
  if (vals.gold) out.push(t("cu.r_gold", vals.gold));
  if (vals.coin) out.push(t("cu.r_coin", p1(vals.coin)));
  if (vals.armor) out.push(t("cu.r_armor", p1(vals.armor)));
  if (vals.shields) out.push(t("cu.r_shields", vals.shields));
  if (vals.crit) out.push(t("cu.r_crit", p1(vals.crit)));
  if (vals.critd) out.push(t("cu.r_critd", p1(vals.critd)));
  if (vals.aspd) out.push(t("cu.r_aspd", p1(vals.aspd)));
  return out;
}

// ------------------------------------------------------------------
// Koşu eklentisi
// ------------------------------------------------------------------
export class RunExtras {
  quests: Quest[] = [];
  questT = 0;
  questFlash = 0;
  merchant: Merchant | null = null;
  merchantOpen = false;
  merchantHand: [string, number][] = [];
  merchantRerolls = 0;
  oath: string | null = null;
  oathTier = 0;
  oathSpeed = 1;
  oathSpawn = 1;
  oathPeriod: number = C.OATH_BULWARK_EVERY;
  oathT = 0;
  shrine: CursedShrine | null = null;
  curseOffers: CurseOffer[] | null = null;
  cursedTaken = 0;
  cursedSpawns = 0;
  cursedSpawnT = -999;
  corpses: [number, number, number][] = [];

  constructor(public run: Run) {}

  /** Koşu başında: görevler + tüccar. */
  start() {
    this.rollQuests();
    this.spawnMerchant();
  }

  private makeEnemy(kind: string, x: number, y: number, themed = true): Enemy {
    const r = this.run;
    const w = r.waves.wave;
    x = clamp(x, 30, r.W - 30);
    y = clamp(y, 30, r.H - 30);
    let e: Enemy;
    if (kind in (C.HELL_ENEMIES || {})) e = new Enemy(null, x, y, r.waveHpMult(w), 1, w, kind, "hell");
    else if (themed && r.biome !== "hell" && r.waves.theme !== "stone" && C.MAP_ROSTER[r.waves.theme]?.[kind])
      e = makeMapEnemy(r.waves.theme, kind, x, y, r.waveHpMult(w), 1, w);
    else e = new Enemy(kind, x, y, r.waveHpMult(w), 1, w, null, r.biome);
    const fz = r.curses.frenzy || 0;
    if (fz) e.speed *= 1 + C.CURSE_FRENZY_SPD * fz;
    return e;
  }

  // ---------------- görevler ----------------
  rollQuests() {
    const keys = shuffle(Object.keys(QUEST_DEFS));
    const used = new Set<string>();
    this.quests = [];
    for (let tier = 0; tier < 3; tier++) {
      for (const k of keys) {
        const goal = QUEST_DEFS[k][2][tier];
        if (used.has(k) || goal == null) continue;
        used.add(k);
        this.quests.push({ key: k, tier, goal, done: false });
        break;
      }
    }
  }

  questValue(key: string) {
    const r = this.run;
    switch (key) {
      case "kills": return r.kills;
      case "wave": return r.totalWave();
      case "level": return r.player.level;
      case "gold": return Math.floor(r.coinsEarned);
      case "combo": return r.combo.best;
      case "boss": return r.bossesKilled;
      case "cave": return this.cursedTaken;
    }
    return 0;
  }

  updateQuests() {
    const p = this.run.player, fx = this.run.fx;
    for (const q of this.quests) {
      if (q.done || this.questValue(q.key) < q.goal) continue;
      q.done = true;
      const col = QUEST_TIER_COLORS[q.tier];
      const gems = QUEST_GEMS[q.tier];
      fx.popup(p.x, p.y + 74, t("q.done"), col, 26, 2.2, true);
      fx.popup(p.x, p.y + 100, `${t("q." + q.key, q.goal)}  +${gems}`, [110, 240, 255], 16, 2.2, true);
      fx.ring(p.x, p.y, col, 26, 260, 0.6, 3.5);
      this.questFlash = 2.4;
      sfx("ach", 0.8, 0);
      haptic("success");
      this.run.onEvent("quest", q);
    }
  }

  questGemsDue() {
    return this.quests.filter((q) => q.done).reduce((a, q) => a + QUEST_GEMS[q.tier], 0);
  }

  // ---------------- tüccar ----------------
  spawnMerchant() {
    const r = this.run, p = r.player;
    const cam = r.camRect(120);
    let x = 0, y = 0;
    for (let i = 0; i < 80; i++) {
      x = rand(220, r.W - 220);
      y = rand(240, r.H - 160);
      const d = dist(x, y, p.x, p.y);
      const inCam = x > cam.l && x < cam.r && y > cam.t && y < cam.b;
      if (d > 650 && d < 1150 && !inCam) break;
    }
    this.merchant = new Merchant(x, y);
    this.merchantHand = [];
    this.merchantRerolls = 0;
    r.fx.popup(p.x, p.y - 96, t("m.hint_m"), MERCHANT_COLOR, 18, 4, true);
  }

  merchantLuck() {
    const p = this.run.player;
    return p.effLuck() + C.MERCHANT_LUCK_PER_LEVEL * Math.max(0, p.level - 1);
  }

  private rollHand() {
    const luck = this.merchantLuck();
    const old = new Set(this.merchantHand.map((h) => h[0]));
    const pool = OATHS.map((o) => o[0]);
    const fresh = pool.filter((k) => !old.has(k));
    const keys = shuffle([...(fresh.length >= 3 ? fresh : pool)]).slice(0, 3);
    this.merchantHand = keys.map((k) => [k, B.rollRarity(luck)] as [string, number]);
  }

  merchantOffers() {
    if (!this.merchantHand.length) this.rollHand();
    return [...this.merchantHand];
  }
  rerollLeft() {
    return Math.max(0, C.MERCHANT_REROLLS - this.merchantRerolls);
  }
  rerollPrice() {
    return merchantRerollCost(this.run.waves.wave, this.merchantRerolls);
  }
  merchantReroll(): [boolean, string] {
    if (this.oath) return [false, "sworn"];
    if (this.rerollLeft() <= 0) return [false, "none"];
    const cost = this.rerollPrice();
    if (this.run.gold < cost) return [false, "gold"];
    this.run.gold -= cost;
    this.merchantRerolls++;
    this.rollHand();
    return [true, ""];
  }

  chooseOath(key: string | null, tier = 0) {
    if (key && !this.oath) {
      this.applyOath(key, tier);
      if (this.merchant) this.merchant.done = true;
    }
    this.merchantOpen = false;
  }

  private scaleMaxHp(f: number) {
    const p = this.run.player;
    p.max_hp = Math.max(30, Math.round(p.max_hp * f));
    p.hp = p.max_hp;
  }

  applyOath(key: string, tier = 0) {
    const p = this.run.player;
    if (!OATHS.some((o) => o[0] === key)) return;
    this.oath = key;
    this.oathTier = tier = clamp(Math.floor(tier), 0, B.RARITY_COUNT - 1);
    const v = oathValues(key, tier);
    switch (key) {
      case "glass": p.run_dmg_mult += v[0]; this.scaleMaxHp(0.75); break;
      case "gold_fever": p.run_coin_mult += v[0]; p.enemy_hp_curse += 0.1; break;
      case "turtle": p.max_hp += v[0]; p.hp = p.max_hp; p.run_armor_bonus += v[1]; p.run_spd_mult -= 0.07; break;
      case "scholar": p.run_xp_mult += v[0]; p.run_dmg_mult -= 0.12; break;
      case "gambler": p.run_luck_bonus += v[0]; this.scaleMaxHp(0.85); break;
      case "blood": p.vamp_level += v[0] / 0.02; p.regen_mult = 0; break;
      case "wind": p.run_spd_mult += v[0]; p.dash_dist_mult += v[1]; this.oathSpeed = 1.1; break;
      case "bulwark": p.shield_charges += v[0]; this.oathPeriod = v[1]; p.run_aspd_mult -= 0.1; this.oathT = 0; break;
      case "hunter": p.boss_hunter += v[0]; p.run_coin_mult -= 0.1; break;
      case "feast": p.run_xp_mult += v[0]; p.run_coin_mult += v[0]; this.oathSpawn = 1.15; break;
      case "hoard": this.run.gold += v[0]; p.run_xp_mult -= 0.1; break;
      case "hawkeye": p.run_crit_bonus += v[0]; p.run_critdmg_bonus += v[1]; p.run_aspd_mult -= 0.1; break;
    }
    this.run.applyWaveMods();
    const col = OATHS.find((o) => o[0] === key)![2];
    this.run.fx.ring(p.x, p.y, col, 30, 300, 0.7, 4);
    this.run.fx.flash(col, 0.25);
    sfx("levelup", 0.9);
    haptic("success");
  }

  // ---------------- lanetli mağara ----------------
  private cursedDue() {
    const r = this.run;
    const n = this.cursedSpawns;
    if (n >= C.CURSED_MAX || r.biome === "hell") return false;
    if (n === 0) return true;
    const old = this.shrine;
    if (old && old.alive && !old.used) {
      if (old.discovered || r.runTime - this.cursedSpawnT < C.CURSED_MIN_LIFE) return false;
    }
    if (n === 1) return r.bossesKilled >= 1;
    return !!r.hellPortal || r.doomWarned;
  }

  private spawnShrine() {
    const r = this.run, p = r.player;
    const cam = r.camRect(160);
    let x = 0, y = 0;
    for (let i = 0; i < 80; i++) {
      x = rand(220, r.W - 220);
      y = rand(220, r.H - 220);
      const d = dist(x, y, p.x, p.y);
      const farPortal = !r.hellPortal || dist(x, y, r.hellPortal.x, r.hellPortal.y) > 320;
      const inCam = x > cam.l && x < cam.r && y > cam.t && y < cam.b;
      if (d > 700 && d < 1500 && farPortal && !inCam) break;
    }
    this.shrine = new CursedShrine(x, y);
    this.cursedSpawns++;
    this.cursedSpawnT = r.runTime;
  }

  openCursed() {
    const sh = this.shrine;
    if (!sh) return;
    sh.opened = true;
    this.curseOffers = this.buildOffers();
    this.run.fx.flash(CURSE_COLOR, 0.35);
    sfx("magnet", 0.6, 0);
  }

  private buildOffers(): CurseOffer[] {
    const r = this.run, p = r.player;
    const luck = p.effLuck();
    const rewards = shuffle((C.CURSE_REWARDS as string[]).filter((k) => k !== "arsenal" || Object.keys(p.weapons).length));
    const curses: string[] = shuffle([...CURSE_KINDS]);
    if (Math.random() < 0.45) curses[2] = pick(["frenzy", "swarm"]);
    const caveLuck = luck * C.CAVE_LUCK_MULT + C.CAVE_LUCK_BASE;
    const offers: CurseOffer[] = [];
    for (let i = 0; i < 3; i++) {
      const tier = B.rollRarity(caveLuck);
      const rk = rewards[i % rewards.length];
      const vals = cursedRewardValues(rk, tier, r.waves.wave);
      if (tier >= 3) vals.levels = (vals.levels || 0) + (tier >= 4 ? 2 : 1);
      if (tier >= 4 && Object.keys(p.weapons).length) vals.wlevels = (vals.wlevels || 0) + 1;
      offers.push({ kind: "pair", reward: rk, tier, vals, lines: cursedRewardLines(vals), curse: curses[i] });
    }
    const x = Math.random();
    if (x < 0.35) {
      offers[2].kind = "gamble";
      offers[2].win = Math.min(C.GAMBLE_WIN_MAX, C.GAMBLE_WIN + C.GAMBLE_WIN_LUCK * luck);
    } else if (x < 0.6) {
      offers[2].kind = "blood";
      offers[2].curse = null;
    }
    return offers;
  }

  declineCurse() {
    const sh = this.shrine, fx = this.run.fx;
    if (sh) {
      sh.opened = false;
      sh.used = true;
      fx.popup(sh.x, sh.y - 70, t("cu.collapsed"), [200, 180, 220], 20, 1.8, true);
      fx.burst(sh.x, sh.y, [120, 100, 140], 26, 180, 0.7, 4);
      fx.shake(6, 0.3);
      sfx("bonk", 0.5, 0);
    }
    this.curseOffers = null;
  }

  acceptCurse(idx: number) {
    const offers = this.curseOffers || [];
    const o = offers[idx];
    if (!o) return;
    const r = this.run, p = r.player, fx = r.fx;
    const sh = this.shrine;
    const [sx, sy] = sh ? [sh.x, sh.y + 30] : [p.x, p.y];
    let mult = 1;
    if (o.kind === "gamble") {
      const won = Math.random() < (o.win ?? C.GAMBLE_WIN);
      mult = won ? 2 : 0;
      fx.popup(p.x, p.y - 96, won ? t("cu.won") : t("cu.lost"), won ? GREEN : CURSE_RED, 30, 2, true);
      haptic(won ? "success" : "error");
    }
    if (mult) this.applyReward(o.vals, mult);
    if (o.kind === "blood") {
      const loss = Math.floor(p.max_hp * C.BLOOD_PRICE);
      p.max_hp = Math.max(30, Math.floor(p.max_hp) - loss);
      p.hp = Math.min(p.hp, p.max_hp);
      fx.popup(p.x, p.y - 70, `-${loss} ${t("cu.maxhp")}`, CURSE_RED, 20, 1.6, true);
      fx.flash(CURSE_RED, 0.4);
    } else if (o.curse) {
      r.curses[o.curse] = (r.curses[o.curse] || 0) + 1;
      r.curseScoreBonus = Math.min(C.CURSE_SCORE_MAX, r.curseScoreBonus + C.CURSE_SCORE_PER);
      this.curseTrap(o.curse, sx, sy);
    }
    this.cursedTaken++;
    if (sh) sh.used = true;
    this.curseOffers = null;
    sfx("levelup", 0.9, 0);
  }

  private applyReward(vals: Record<string, number>, mult: number) {
    const r = this.run, p = r.player;
    const n = (vals.levels || 0) * mult;
    if (n > 0) {
      for (let i = 0; i < n; i++) {
        p.level += 1;
        p.xp_to_next = B.xpNextNeed(p.xp_to_next, p.level);
      }
      p.onLevelUp(n);
      r.pendingLevelups += n;
    }
    const wl = (vals.wlevels || 0) * mult;
    if (wl > 0) {
      for (const k of Object.keys(p.weapons)) {
        const w = WEAPON_BY_KEY[k];
        if (!w) continue;
        p.weapons[k] = Math.min(w.max ?? B.WEAPON_MAX_LEVEL, p.weapons[k] + wl);
        p.addWeaponBoost(k, (vals.boost || 0) * mult);
      }
    }
    const hp = (vals.hp || 0) * mult;
    if (hp) {
      p.max_hp += hp;
      p.hp = Math.min(p.max_hp, p.hp + hp);
    }
    p.run_dmg_mult += (vals.dmg || 0) * mult;
    p.run_luck_bonus += (vals.luck || 0) * mult;
    r.gold += Math.floor((vals.gold || 0) * mult);
    p.run_coin_mult += (vals.coin || 0) * mult;
    p.run_armor_bonus += (vals.armor || 0) * mult;
    p.shield_charges += (vals.shields || 0) * mult;
    p.run_crit_bonus += (vals.crit || 0) * mult;
    p.run_critdmg_bonus += (vals.critd || 0) * mult;
    p.run_aspd_mult += (vals.aspd || 0) * mult;
    r.fx.ring(p.x, p.y, GREEN, 24, 260, 0.5, 3.5);
  }

  private curseTrap(curse: string, sx: number, sy: number) {
    const r = this.run, fx = r.fx;
    const n = Math.min(20, C.CURSE_TRAP_BASE + Math.floor(r.waves.wave / 2));
    for (let i = 0; i < n; i++) {
      const a = (i / n) * TAU + rand(-0.2, 0.2);
      const rr = rand(110, 250);
      const kind = CURSE_KINDS.includes(curse) ? curse : r.waves.pickBaseKind();
      r.enemies.push(this.makeEnemy(kind, sx + Math.cos(a) * rr, sy + Math.sin(a) * rr));
    }
    fx.flash(CURSE_COLOR, 0.55);
    fx.shake(12, 0.45);
    for (let k = 0; k < 3; k++) fx.shockwave(sx, sy, 160 + 150 * k, k % 2 === 0 ? CURSE_COLOR : CURSE_RED, 0.5 + 0.12 * k, 6 - k);
    fx.burst(sx, sy, CURSE_COLOR2, 36, 320, 0.7, 4);
    fx.popup(sx, sy - 120, t("cu.trap"), CURSE_RED, 38, 1.8, true);
    sfx("explosion", 0.8, 0);
    haptic("heavy");
  }

  // ---------------- ceset / ölü çağırıcı ----------------
  onDeath(e: Target) {
    const r = this.run;
    if (e.isBoss) return;
    if (r.curses.necro && !(e as any).raised && e.kind !== "necro" && e.kind !== "splitter" && this.corpses.length < 40) this.corpses.push([e.x, e.y, r.runTime]);
  }

  private necroRaise(nec: Enemy) {
    const r = this.run;
    const near = this.corpses.filter((c) => dist(c[0], c[1], nec.x, nec.y) < C.NECRO_RADIUS).slice(0, C.NECRO_MAX_RAISE);
    if (!near.length) return;
    const col = ENEMY_COLORS.necro as RGB;
    for (const c of near) {
      this.corpses.splice(this.corpses.indexOf(c), 1);
      const sk = this.makeEnemy("red", c[0], c[1], false);
      (sk as any).raised = true;
      sk.color = C.RAISED_COLOR;
      sk.max_hp *= 0.55;
      sk.hp = sk.max_hp;
      sk.coin = 0;
      sk.xp = 0;
      sk.score = Math.max(1, Math.floor(sk.score * 0.5));
      sk.name = t("en.raised");
      r.enemies.push(sk);
      r.fx.bolt(zigzag(nec.x, nec.y - 18, c[0], c[1], 5, 10), col, 0.3);
      r.fx.burst(c[0], c[1], C.RAISED_COLOR, 8, 120, 0.4, 3);
    }
    r.fx.popup(nec.x, nec.y - 36, t("fx.raise"), lighten(col, 0.3), 14, 0.8);
    sfx("vortex", 0.25, 0.08);
  }

  // ---------------- kare ----------------
  /** Dönüş: "GİR" basışı burada kullanıldı mı. */
  update(dt: number, use: boolean): boolean {
    const r = this.run, p = r.player;
    let used = false;
    this.questT -= dt;
    if (this.questT <= 0) {
      this.questT = 0.5;
      if (this.quests.length && !r.gameOver) this.updateQuests();
    }
    if (this.questFlash > 0) this.questFlash = Math.max(0, this.questFlash - dt);
    if (this.oath === "bulwark") {
      this.oathT += dt;
      if (this.oathT >= this.oathPeriod) {
        this.oathT = 0;
        if (p.shield_charges < 3) {
          p.shield_charges += 1;
          r.fx.popup(p.x, p.y - 40, "+1", [170, 180, 255], 16, 0.7, true);
        }
      }
    }
    // mağara
    if (this.cursedDue()) this.spawnShrine();
    const sh = this.shrine;
    if (sh) {
      sh.update(dt);
      const cam = r.camRect(-70);
      if (!sh.discovered && sh.x > cam.l && sh.x < cam.r && sh.y > cam.t && sh.y < cam.b) {
        sh.discovered = true;
        r.fx.popup(p.x, p.y - 92, t("cu.found"), CURSE_COLOR2, 24, 2.4, true);
        sfx("magnet", 0.5, 0);
        haptic("medium");
      }
      if (!sh.alive) this.shrine = null;
      else if (use && p.alive && !sh.used && !this.curseOffers && sh.inRange(p)) {
        this.openCursed();
        used = true;
      }
    }
    if (this.corpses.length) this.corpses = this.corpses.filter((c) => r.runTime - c[2] < C.CORPSE_LIFE);
    for (const e of r.enemies) {
      if (e.alive && e.kind === "necro" && e.spawnT > 1) {
        e.necroCd -= dt;
        if (e.necroCd <= 0) {
          e.necroCd = C.NECRO_CD;
          this.necroRaise(e);
        }
      }
    }
    // tüccar
    const m = this.merchant;
    if (m) {
      m.update(dt);
      if (!used && use && !this.merchantOpen && p.alive && !this.curseOffers && !m.done && m.inRange(p)) {
        this.merchantOffers();
        this.merchantOpen = true;
        used = true;
      }
    }
    return used;
  }

  /** Şu an GİR düğmesi gösterilmeli mi (tüccar / mağara yakında). */
  useTarget(): "merchant" | "shrine" | null {
    const p = this.run.player;
    if (this.shrine && !this.shrine.used && this.shrine.inRange(p) && !this.curseOffers) return "shrine";
    if (this.merchant && !this.merchant.done && this.merchant.inRange(p)) return "merchant";
    return null;
  }
}
