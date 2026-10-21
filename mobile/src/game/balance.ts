/**
 * Denge formülleri — Python sürümündeki fonksiyonların birebir karşılığı.
 * (arena_hp_mult, wave_length, xp_next_need, weapon_growth, ...)
 * Sabitler gamedata.json'dan okunur; böylece iki sürüm aynı sayıları kullanır.
 */
import { GD } from "./data";
import { clamp, lerp, stackBonus } from "../core/util";

const C = GD;

export const BASE_SPEED: number = C.BASE_SPEED;
export const BASE_MAX_HP: number = C.BASE_MAX_HP;
export const BASE_DMG: number = C.BASE_DMG;
export const BASE_ATK_CD: number = C.BASE_ATK_CD;
export const BASE_PICKUP: number = C.BASE_PICKUP;
export const BASE_DASH_CD: number = C.BASE_DASH_CD;
export const BASE_BONK_CD: number = C.BASE_BONK_CD;

// --- Dünya ---------------------------------------------------------------
// Python: 1264 x 634 görüş alanı, dünya 5 x 5 ekran.
export const BASE_VIEW_W = 1264;
export const BASE_VIEW_H = 634;
export const WORLD_W = BASE_VIEW_W * 5;
export const WORLD_H = BASE_VIEW_H * 5;

// --- Hız tavanı ----------------------------------------------------------
export function softSpeedMult(m: number) {
  const from = C.SPEED_SOFT_FROM, k = C.SPEED_SOFT_K, max = C.SPEED_RUN_MAX;
  if (m <= from) return m;
  return Math.min(max, from + (m - from) * k);
}

// --- Seviye eğrisi -------------------------------------------------------
export const XP_BASE_NEED: number = C.XP_BASE_NEED;
export const XP_GAIN_SCALE: number = C.XP_GAIN_SCALE;
export function xpNextNeed(need: number, level: number) {
  const bands: [number | null, number, number][] = C.XP_CURVE_BANDS;
  for (const [cap, growth, flat] of bands) {
    if (cap === null || level <= cap) return Math.max(1, Math.floor(need * growth + flat));
  }
  const last = bands[bands.length - 1];
  return Math.max(1, Math.floor(need * last[1] + last[2]));
}

export function xpLevelSoftcap(level: number, totalWave: number) {
  const w = Math.max(1, Math.floor(totalWave));
  const tbl: [number, number][] = C.XP_SOFTCAP_REF;
  let ref: number;
  if (w >= tbl[tbl.length - 1][0]) ref = tbl[tbl.length - 1][1] + (w - tbl[tbl.length - 1][0]) * C.XP_SOFTCAP_SLOPE;
  else {
    ref = tbl[0][1];
    for (let i = 0; i < tbl.length - 1; i++) {
      const [w0, l0] = tbl[i], [w1, l1] = tbl[i + 1];
      if (w0 <= w && w <= w1) {
        ref = l0 + ((l1 - l0) * (w - w0)) / (w1 - w0);
        break;
      }
    }
  }
  const over = level - ref * C.XP_SOFTCAP_EDGE;
  if (over <= 0) return 1;
  return 1 / (1 + C.XP_SOFTCAP_K * over);
}

// --- Dalga takvimi -------------------------------------------------------
export type Diff = "normal" | "hard" | "nightmare";
export type Biome = "arena" | "hell";

const WAVE_PLAN_COUNT: number = C.WAVE_PLAN_COUNT;
const WAVE_PLAN_GROW: number = C.WAVE_PLAN_GROW;
let planW = 0;
for (let i = 1; i <= WAVE_PLAN_COUNT; i++) planW += 1 + WAVE_PLAN_GROW * (i - 1);

export function wavePlanTotal(diff: Diff = "normal", biome: Biome = "arena") {
  const tbl = C.WAVE_PLAN_TOTAL[biome === "hell" ? "hell" : "arena"];
  return tbl[diff] ?? tbl.normal;
}
export function waveLength(wave: number, diff: Diff = "normal", biome: Biome = "arena") {
  const w = Math.min(WAVE_PLAN_COUNT, Math.max(1, Math.floor(wave)));
  return (wavePlanTotal(diff, biome) * (1 + WAVE_PLAN_GROW * (w - 1))) / planW;
}
export function waveStartTime(wave: number, diff: Diff = "normal", biome: Biome = "arena") {
  const w = Math.max(1, Math.floor(wave));
  let t = 0;
  for (let i = 1; i < Math.min(w, WAVE_PLAN_COUNT + 1); i++) t += waveLength(i, diff, biome);
  if (w > WAVE_PLAN_COUNT + 1) t += (w - WAVE_PLAN_COUNT - 1) * waveLength(WAVE_PLAN_COUNT, diff, biome);
  return t;
}

// --- Ekonomi -------------------------------------------------------------
const HELL_BASE_WAVE: number = C.HELL_BASE_WAVE;
function econRefMinutes(w: number, diff: Diff) {
  const tbl: [number, number][] = C.ECON_TIME_REF[diff] || C.ECON_TIME_REF.normal;
  if (w >= tbl[tbl.length - 1][0]) return tbl[tbl.length - 1][1] + (w - tbl[tbl.length - 1][0]) * C.ECON_TIME_REF_SLOPE;
  for (let i = 0; i < tbl.length - 1; i++) {
    const [w0, m0] = tbl[i], [w1, m1] = tbl[i + 1];
    if (w0 <= w && w <= w1) return m0 + ((m1 - m0) * (w - w0)) / (w1 - w0);
  }
  return tbl[0][1];
}
const econCache = new Map<string, number>();
export function econTimeFactor(wave: number, diff: Diff = "normal", biome: Biome = "arena") {
  const key = `${wave}|${diff}|${biome}`;
  let k = econCache.get(key);
  if (k === undefined) {
    const w = Math.max(1, Math.floor(wave));
    const newMin = (waveStartTime(w, diff, biome) + 0.5 * waveLength(w, diff, biome)) / 60;
    let ref = econRefMinutes(w + (biome === "hell" ? HELL_BASE_WAVE : 0), diff);
    if (biome === "hell") ref -= econRefMinutes(HELL_BASE_WAVE, diff);
    let edge: number = C.ECON_TIME_EDGE[diff] ?? 0.72;
    const tw = w + (biome === "hell" ? HELL_BASE_WAVE : 0);
    edge = 1 + (edge - 1) * clamp((tw - 5) / 10, 0, 1);
    k = clamp((edge * ref) / Math.max(0.2, newMin), C.ECON_TIME_FLOOR, 1);
    econCache.set(key, k);
  }
  return k;
}
export function econWaveFactor(wave: number, biome: Biome, kind: "xp" | "gold", diff: Diff) {
  const tk = econTimeFactor(wave, diff, biome);
  if (biome === "hell") return (kind === "xp" ? C.ECON_HELL_XP : 1) * tk;
  const early = kind === "xp" ? C.ECON_XP_EARLY : C.ECON_GOLD_EARLY;
  const w = Math.floor(wave);
  if (w <= C.ECON_EARLY_UNTIL) return early * tk;
  const k = clamp((w - C.ECON_EARLY_UNTIL) / C.ECON_RAMP_WAVES, 0, 1);
  return (early + (C.ECON_LATE - early) * k) * tk;
}

export function coinDropScale(biome: Biome) {
  return (biome === "hell" ? C.COIN_DROP_SCALE_HELL : C.COIN_DROP_SCALE) * C.GOLD_TRIM;
}
export function scaledCoinGain(base: number, mult: number, biome: Biome) {
  const x = Math.max(0, base * mult * coinDropScale(biome));
  let n = Math.floor(x);
  if (Math.random() < x - n) n++;
  return n;
}

// --- Nadirlik ------------------------------------------------------------
export const RARITY_COUNT = 5;
export const RARITY_MULTS: number[] = C.RARITY_MULTS;
export const RARITY_COLORS: number[][] = C.RARITY_COLORS;
export function rarityWeights(luck: number) {
  const f = 1 + Math.max(0, luck);
  const base: number[] = C.RARITY_BASE_WEIGHTS;
  const w = base.map((b, i) => b * Math.pow(f, C.RARITY_LUCK_EXP * i));
  let rest = 0;
  for (let i = 0; i < w.length - 1; i++) rest += w[i];
  const top = (rest * C.RARITY_LEGEND_CAP) / (1 - C.RARITY_LEGEND_CAP);
  if (w[w.length - 1] > top) w[w.length - 1] = top;
  return w;
}
export function rollRarity(luck: number, rnd: () => number = Math.random) {
  const w = rarityWeights(luck);
  let tot = 0;
  for (const x of w) tot += x;
  let r = rnd() * tot;
  for (let i = 0; i < w.length; i++) {
    r -= w[i];
    if (r <= 0) return i;
  }
  return 0;
}
export function rarityBoost(tier: number, source: "chest" | "card" = "chest") {
  const i = clamp(Math.floor(tier), 0, RARITY_COUNT - 1);
  return (source === "card" ? C.CARD_RARITY_BONUS : C.CHEST_RARITY_BONUS)[i];
}

// --- Yaratık eğrileri ----------------------------------------------------
export function arenaHpMult(wave: number) {
  const w = Math.max(1, Math.floor(wave));
  return 1 + (w - 1) * 0.22 + 0.004 * Math.pow(Math.min(w, 25) - 1, 2);
}
export function waveSpeedMult(wave: number) {
  if (wave <= 7) return lerp(0.66, 0.94, clamp((wave - 1) / 6, 0, 1));
  return lerp(0.94, 1.55, clamp((wave - 7) / 18, 0, 1));
}
export function lateWaveDmgMult(wave: number, coef?: number) {
  if (wave <= 12) return 1 + (wave - 1) * 0.055;
  const base = 1 + 11 * 0.055;
  return base + Math.pow(wave - 12, 1.6) * (coef ?? C.LATE_DMG_COEF);
}
export function arenaPressure(wave: number): [number, number, number, number] {
  const over = Math.max(0, Math.floor(wave) - C.ARENA_PRESSURE_FROM);
  if (over <= 0) return [1, 1, 1, 0];
  return [
    Math.pow(C.ARENA_PRESSURE_HP, over),
    Math.pow(C.ARENA_PRESSURE_DMG, over),
    1 + C.ARENA_PRESSURE_SPD * over,
    clamp(C.ARENA_PRESSURE_ARMOR * over, 0, 0.6),
  ];
}
export function doomMult(wave: number): [number, number] {
  const over = Math.max(0, Math.floor(wave) - C.HELL_PORTAL_WAVE);
  return [Math.pow(C.DOOM_HP, over), Math.pow(C.DOOM_DMG, over)];
}
export function hellPressure(wave: number): [number, number, number] {
  const over = Math.max(0, Math.floor(wave) - C.HELL_PRESSURE_FROM);
  if (over <= 0) return [1, 1, 1];
  return [Math.pow(C.HELL_PRESSURE_HP, over), Math.pow(C.HELL_PRESSURE_DMG, over), 1 + C.HELL_PRESSURE_SPD * over];
}
export function hellArmor(wave: number) {
  return clamp(C.HELL_ARMOR_BASE + C.HELL_ARMOR_PER_WAVE * (Math.max(1, wave) - 1), 0, C.HELL_ARMOR_MAX);
}
export function hellHpMult(wave: number) {
  const w = Math.max(1, Math.floor(wave));
  const base = arenaHpMult(HELL_BASE_WAVE) * C.HELL_HP_BOOST;
  return base * (1 + (w - 1) * 0.32 + 0.008 * Math.pow(w - 1, 2));
}
export const hellDmgWave = (wave: number) => HELL_BASE_WAVE + (Math.max(1, wave) - 1);
export const hellSpeedWave = (wave: number) => C.HELL_SPEED_BASE_WAVE + (Math.max(1, wave) - 1) * 1.5;
export function enemyArmorPierce(wave: number, biome: Biome) {
  const w = Math.max(1, Math.floor(wave));
  if (biome === "hell") return clamp(C.PIERCE_HELL_BASE + C.PIERCE_HELL_PER * (w - 1), 0, C.PIERCE_HELL_MAX);
  return clamp(C.PIERCE_PER_WAVE * (w - C.PIERCE_FROM), 0, C.PIERCE_MAX);
}
export function rageLevel(wave: number, biome: Biome) {
  if (biome === "hell") return 0;
  return clamp((Math.floor(wave) - C.RAGE_FROM) / C.RAGE_FULL, 0, 1);
}
export function lateWaveBoost(wave: number, biome: Biome): [number, number, number] {
  const w = Math.floor(wave) + (biome === "hell" ? HELL_BASE_WAVE : 0);
  const over = Math.max(0, w - C.LATE_BOOST_FROM);
  if (over <= 0) return [1, 1, 0];
  return [
    1 + C.LATE_BOOST_HP * over,
    1 + C.LATE_BOOST_DMG * over,
    Math.min(C.LATE_BOOST_COUNT_MAX, Math.floor(over / C.LATE_BOOST_COUNT_EVERY)),
  ];
}
export const spawnTempoWave = (wave: number, biome: Biome) => Math.floor(wave) + (biome === "hell" ? C.HELL_TEMPO_OFFSET : 0);
export const MOBILE_MAX_ALIVE = 140;
export function maxAliveEnemies(wave: number) {
  return Math.floor(Math.min(MOBILE_MAX_ALIVE, 70 + wave * 4));
}

export function magnetDropChance(killsSince: number, luck = 0) {
  if (killsSince >= C.MAGNET_PITY_TO) return 1;
  if (killsSince <= C.MAGNET_PITY_FROM) return C.MAGNET_DROP_CHANCE * (1 + C.LUCK_MAGNET_K * Math.max(0, luck));
  const k = (killsSince - C.MAGNET_PITY_FROM) / (C.MAGNET_PITY_TO - C.MAGNET_PITY_FROM);
  return C.MAGNET_DROP_CHANCE + (1 - C.MAGNET_DROP_CHANCE) * k;
}

// --- Silah büyümesi ------------------------------------------------------
export const WEAPON_MAX_LEVEL: number = C.WEAPON_MAX_LEVEL;
export function weaponGrowth(lvl: number) {
  const top = WEAPON_MAX_LEVEL - 1;
  const x = clamp((lvl - 1) / top, 0, 1);
  const ic = 1 - Math.pow(1 - x, C.WEAPON_GROWTH_EXP);
  return top * (C.WEAPON_GROWTH_FLOOR * x + (1 - C.WEAPON_GROWTH_FLOOR) * ic);
}
export function weaponCount(lvl: number, key?: string) {
  if (key === "whip") {
    const steps: number[] = C.WHIP_COUNT_STEPS;
    return Math.min(steps[clamp(lvl - 1, 0, steps.length - 1)], C.WHIP_COUNT_MAX);
  }
  const steps: number[] = C.WEAPON_COUNT_STEPS;
  return steps[clamp(lvl - 1, 0, steps.length - 1)];
}
export function weaponCooldown(w: { cd: number; cdl?: number }, lvl: number) {
  const k = w.cdl ?? C.WEAPON_CD_PER_LEVEL;
  return Math.max(0.22, w.cd * Math.pow(k, weaponGrowth(lvl)));
}

export function whipGrowth(lvl: number) {
  const top = WEAPON_MAX_LEVEL - 1;
  const x = clamp((lvl - 1) / top, 0, 1);
  return top * Math.pow(x, C.WHIP_GROWTH_EXP);
}
export const whipArc = (lvl: number) => Math.min(C.WHIP_ARC_MAX, C.WHIP_ARC + C.WHIP_ARC_PER_LEVEL * whipGrowth(lvl));
export const whipReach = (lvl: number) => C.WHIP_LEN + C.WHIP_LEN_PER_LEVEL * whipGrowth(lvl);
export const emanetRadius = (lvl: number) => C.EMANET_BASE_R + C.EMANET_R_PER_LEVEL * weaponGrowth(lvl);
export const emanetArc = (lvl: number) => Math.min(C.EMANET_ARC_MAX, C.EMANET_BASE_ARC + C.EMANET_ARC_PER_LEVEL * weaponGrowth(lvl));
export const cloakCooldown = (lvl: number) => Math.max(C.CLOAK_MIN_CD, C.CLOAK_BASE_CD - C.CLOAK_CD_PER_LEVEL * weaponGrowth(lvl));
export const cloakDuration = (lvl: number) => C.CLOAK_DUR + C.CLOAK_DUR_PER_LEVEL * weaponGrowth(lvl);
export const cloakAmbushBonus = (lvl: number) => (lvl <= 0 ? 0 : C.CLOAK_AMBUSH_BASE + C.CLOAK_AMBUSH_PER_LEVEL * weaponGrowth(lvl));
export const pentaRadius = (lvl: number) => C.PENTA_BASE_R + C.PENTA_R_PER_LEVEL * weaponGrowth(lvl);
export const pentaSearHpFrac = (lvl: number) => Math.min(C.PENTA_SEAR_HP_MAX, C.PENTA_SEAR_HP + C.PENTA_SEAR_HP_PER_LEVEL * weaponGrowth(lvl));
export const pentaSearCap = (lvl: number) => Math.min(1, C.PENTA_SEAR_CAP + C.PENTA_SEAR_CAP_PER_LEVEL * weaponGrowth(lvl));
const step = (t: number[], lvl: number) => t[clamp(Math.floor(lvl) - 1, 0, t.length - 1)];
export const pentaBatSearCap = (lvl: number) => step(C.PENTA_BAT_SEAR_CAP, lvl);
export const pentaBatTickMult = (lvl: number) => step(C.PENTA_BAT_TICK, lvl);
export const shoeRadius = (lvl: number) => C.SHOE_BASE_R + C.SHOE_R_PER_LEVEL * weaponGrowth(lvl);
export function shoeLife(lvl: number) {
  const g = weaponGrowth(lvl);
  const steps: number[] = C.SHOE_LIFE_STEPS;
  if (g <= steps.length - 1) {
    const i = Math.floor(g), f = g - i;
    return lerp(steps[i], steps[Math.min(i + 1, steps.length - 1)], f);
  }
  return steps[steps.length - 1] + C.SHOE_LIFE_PER_LEVEL * (g - (steps.length - 1));
}
export const ghostCount = (lvl: number) => step(C.GHOST_COUNT_STEPS, lvl);
export const ghostRange = (lvl: number) => C.GHOST_RANGE + C.GHOST_RANGE_PER * weaponGrowth(lvl);
export const ghostCd = (lvl: number) => Math.max(0.9, C.GHOST_CD * Math.pow(0.982, weaponGrowth(lvl)));
export const wolfCount = (lvl: number) => 1 + +(lvl >= 4) + +(lvl >= 9) + +(lvl >= 15) + +(lvl >= 21);
export const wolfBiteCd = (lvl: number) => Math.max(0.45, C.WOLF_BITE_CD * Math.pow(0.984, weaponGrowth(lvl)));
export const wolfSpeed = (lvl: number) => C.WOLF_SPEED + 3 * weaponGrowth(lvl);
export const teslaTargets = (lvl: number) => 5 + Math.floor(weaponGrowth(lvl) / 4);
export const meteorCount = (lvl: number) => 1 + +(lvl >= 7) + +(lvl >= 14) + +(lvl >= 21);
export const meteorRadius = (lvl: number) => C.METEOR_BASE_R + C.METEOR_R_PER * weaponGrowth(lvl);
export const beamCount = (lvl: number) => 1 + +(lvl >= 9) + +(lvl >= 20);
export const beamLen = (lvl: number) => C.BEAM_BASE_LEN + C.BEAM_LEN_PER * weaponGrowth(lvl);
export const hawkCount = (lvl: number) => 1 + +(lvl >= 6) + +(lvl >= 13) + +(lvl >= 20);
export const hawkCd = (lvl: number) => Math.max(0.7, 1.45 * Math.pow(0.982, weaponGrowth(lvl)));
export const batCount = (lvl: number) => 4 + Math.floor(weaponGrowth(lvl) / 4);
export const novaRadius = (lvl: number) => C.NOVA_BASE_R + C.NOVA_R_PER * weaponGrowth(lvl);
export const novaFreeze = (lvl: number) => 0.55 + 0.025 * weaponGrowth(lvl);
export const knifeCount = (lvl: number) => 3 + Math.floor(weaponGrowth(lvl) / 6);
export const knifePierce = (lvl: number) => 3 + +(lvl >= 10) + +(lvl >= 20);
export const quakeRadius = (lvl: number) => C.QUAKE_BASE_R + C.QUAKE_R_PER * weaponGrowth(lvl);
export const quakeStun = (lvl: number) => 0.35 + 0.012 * weaponGrowth(lvl);
export function tornadoHpCut(lvl: number) {
  const over = Math.max(0, weaponGrowth(lvl) - 1);
  return Math.max(C.TORNADO_HP_CUT_MIN, C.TORNADO_HP_CUT_BASE - C.TORNADO_HP_CUT_PER_LEVEL * over);
}

// --- Tek-atma freni ------------------------------------------------------
const WEIGHT_CLASS: Record<string, string> = C.ENEMY_WEIGHT_CLASS;
const ONESHOT: Record<string, [number, number | null, number]> = C.ONESHOT_CAP_TABLE;
export function enemyWeightClass(e: any): string {
  if ((e.armor || 0) > 0.005) return "tough";
  if (e.guardOf) return "tough";
  if (e.isMini) return "tough";
  return WEIGHT_CLASS[e.kind] || "normal";
}
export function oneshotCap(e: any, lvl: number) {
  if (e.isBoss) return 1;
  const [base, gate, top] = ONESHOT[enemyWeightClass(e)];
  lvl = Math.max(1, Math.floor(lvl));
  if (gate === null) {
    const f = clamp(weaponGrowth(lvl) / Math.max(1, WEAPON_MAX_LEVEL - 1), 0, 1);
    return clamp(lerp(base, top, f), 0, 0.999);
  }
  if (lvl >= gate) return 1;
  return clamp(lerp(base, 1, (lvl - 1) / (gate - 1)), 0, 1);
}
export function capOneshot(e: any, dmg: number, lvl: number | null) {
  if (lvl == null || dmg <= 0) return dmg;
  if (e.oneshotUsed) return dmg;
  const cap = oneshotCap(e, lvl);
  if (cap >= 1) return dmg;
  const hp = Math.max(0, e.hp);
  const capped = hp * cap;
  if (dmg <= capped) return dmg;
  if (hp - capped <= hp * C.ONESHOT_MERCY) return dmg;
  e.oneshotUsed = true;
  return capped;
}

// --- Kitaplar -------------------------------------------------------------
export const MAX_RUN_WEAPONS: number = C.MAX_RUN_WEAPONS;
export const MAX_RUN_BOOKS: number = C.MAX_RUN_BOOKS;
export const MAX_RUN_RARE_BOOKS: number = C.MAX_RUN_RARE_BOOKS;
export const BOOK_MAX_LEVEL: number = C.BOOK_MAX_LEVEL;
export const BOOK_GAINS: Record<string, [string, number][]> = C.BOOK_GAINS;
export function bookLateK(key: string, lvl: number) {
  if (key === "r_xp") return lvl <= C.BOOK_SOFT_FROM ? 1 : C.BOOK_LATE_K_XP;
  if (key === "r_luck") return lvl <= C.LUCK_BOOK_FULL ? 1 : C.LUCK_BOOK_LATE_K;
  return lvl <= C.BOOK_SOFT_FROM ? 1 : C.BOOK_LATE_K;
}
export function bookGain(key: string, tier: number, lvl: number): [string, number][] {
  tier = clamp(Math.floor(tier || 0), 0, C.BOOK_RARITY_MULT.length - 1);
  const m = C.BOOK_RARITY_MULT[tier] * bookLateK(key, lvl);
  const out: [string, number][] = [];
  for (const [stat, base] of BOOK_GAINS[key] || []) {
    if (stat === "pierce") out.push([stat, C.BOOK_PIERCE_BY_TIER[tier]]);
    else if (stat === "hp") out.push([stat, Math.max(1, Math.round(base * m))]);
    else out.push([stat, base * m]);
  }
  return out;
}

// --- Market ---------------------------------------------------------------
export function shopItemCost(item: { cost: number; cost_mult: number; hell_only?: boolean; instant?: boolean }, level: number) {
  const k = item.hell_only || item.instant ? 1 : C.SHOP_COST_SCALE;
  return Math.ceil(item.cost * k * Math.pow(item.cost_mult, level));
}
export const tierUnlockWave = (tier: number): number => C.TIER_UNLOCK_WAVE[String(tier)] ?? 0;
export function shopItemUnlocked(item: { tier: number; hell_only?: boolean }, wave: number, biome: Biome) {
  if (item.hell_only) return biome === "hell";
  return wave >= (C.TIER_UNLOCK_WAVE[String(item.tier)] ?? 0);
}
export const shopSoft = (raw: number, soft: number) => {
  raw = Math.max(0, raw);
  return raw <= soft ? raw : soft + (raw - soft) * C.SHOP_SOFT_K;
};

// --- Patronlar ------------------------------------------------------------
export function bossIndexForWave(wave: number) {
  if (wave < C.BOSS_FIRST_WAVE) return 1;
  return Math.floor((wave - C.BOSS_FIRST_WAVE) / C.BOSS_WAVE_STEP) + 1;
}
export function hellBossIndex(wave: number) {
  return C.HELL_BOSS_INDEX_BASE + Math.max(0, Math.floor((wave - C.HELL_BOSS_FIRST_WAVE) / C.HELL_BOSS_STEP));
}
export function bossPower(index: number): [number, number, number] {
  const i = index;
  return [
    1.12 + (i - 1) * 0.62 + Math.pow(i - 1, 1.6) * 0.055,
    1 + (i - 1) * 0.26 + Math.pow(i - 1, 1.5) * 0.02,
    clamp(0.12 + (i - 1) * 0.035, 0, 0.45),
  ];
}
export function bossHitFloor(wave: number, hellish: boolean) {
  if (hellish) return Math.min(C.BOSS_FLOOR_MAX, 0.21 + 0.004 * Math.max(0, wave - 1));
  if (wave < C.BOSS_THREAT_FROM) return 0;
  return Math.min(C.BOSS_FLOOR_MAX, 0.06 + 0.0056 * wave);
}
export function bossWound(wave: number, hellish: boolean) {
  if (hellish) return Math.min(C.BOSS_WOUND_MAX, 0.55 + 0.01 * Math.max(0, wave - 1));
  if (wave < C.BOSS_THREAT_FROM) return 0;
  return Math.min(0.6, 0.3 + 0.015 * (wave - C.BOSS_THREAT_FROM));
}
export const bossCountForWave = (wave: number) => (wave >= 35 ? 3 : wave >= 20 ? 2 : 1);
export const miniBossWave = (w: number) => w >= C.MINI_BOSS_FIRST_WAVE && (w - C.MINI_BOSS_FIRST_WAVE) % C.MINI_BOSS_STEP === 0;
export const miniBossTier = (w: number, hell: boolean) =>
  Math.max(0, Math.floor((w - C.MINI_BOSS_FIRST_WAVE) / C.MINI_BOSS_STEP)) + (hell ? C.MINI_BOSS_HELL_TIER : 0);
export const miniBossGuardCount = (w: number, hell: boolean) =>
  Math.min(C.MINI_BOSS_GUARDS_MAX, C.MINI_BOSS_GUARDS + Math.floor(miniBossTier(w, hell) / 2));

export { stackBonus };
export { C as CONST };
