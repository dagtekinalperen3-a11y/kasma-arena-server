/**
 * Dalga yöneticisi — Python `WaveManager` (süreli dalgalar, v3.47).
 */
import * as B from "./balance";
import { GD } from "./data";
import { Enemy, makeMapEnemy } from "./enemy";
import { t } from "../core/i18n";
import { weightedPick } from "../core/util";

const C = GD;
export const CURSE_KINDS: string[] = C.CURSE_KINDS;

export function curseSpawnChance(curses: Record<string, number>) {
  let n = 0;
  for (const k of CURSE_KINDS) n += curses[k] || 0;
  if (n <= 0) return 0;
  return Math.min(C.CURSE_SPAWN_MAX, C.CURSE_SPAWN_BASE + C.CURSE_SPAWN_PER * (n - 1));
}
export function pickCurseKind(curses: Record<string, number>) {
  const kinds = CURSE_KINDS.filter((k) => (curses[k] || 0) > 0);
  if (!kinds.length) return null;
  return weightedPick(kinds, kinds.map((k) => curses[k]));
}
export function hellPickKind(wave: number) {
  const w = Math.max(1, Math.floor(wave));
  const ks = ["h_imp", "h_hound", "h_reaver", "h_seer", "h_golem", "h_butcher"];
  const ws = [10, 4 + Math.min(w, 9), 6 + Math.min(w, 8), Math.max(0, Math.min(w, 7)), Math.max(0, Math.min(w - 1, 8)), Math.max(0, Math.min(w - 2, 8))];
  return weightedPick(ks, ws);
}

export class WaveManager {
  wave = 1;
  waveTime = 0;
  pace: number;
  enemySpeedMult = 1;
  spawnRateMult = 1;
  theme = "stone";
  doom = false;
  spawnTimer = 0;
  announceTimer = 2.4;
  announceText: string;
  bossIdx = 0;
  bossActive = false;
  bossPending = false;
  waveLen: number;
  surgeTimer = 0;
  surgeDelay = 0;
  bossClock = 0;
  curses: Record<string, number> = {};
  dmgMult = 1;
  mutantCounter = 0;
  spawnPosFn: () => [number, number];

  constructor(public diff: B.Diff = "normal", public biome: B.Biome = "arena", spawnPos: () => [number, number]) {
    this.pace = C.DIFF_PACE[diff] ?? 1;
    this.announceText = biome === "hell" ? t("ui.ann_hell", 1) : t("ui.wave", 1);
    this.waveLen = B.waveLength(1, diff, biome);
    this.spawnPosFn = spawnPos;
  }

  isBossWave(w: number) {
    if (this.biome === "hell") return w >= C.HELL_BOSS_FIRST_WAVE && (w - C.HELL_BOSS_FIRST_WAVE) % C.HELL_BOSS_STEP === 0;
    if (w > C.HELL_PORTAL_WAVE) return false;
    return w >= C.BOSS_FIRST_WAVE && (w - C.BOSS_FIRST_WAVE) % C.BOSS_WAVE_STEP === 0;
  }
  surgeActive() {
    return this.surgeTimer > 0 && this.surgeDelay <= 0;
  }
  progress() {
    return this.waveLen <= 0 ? 1 : Math.min(1, Math.max(0, this.waveTime / this.waveLen));
  }
  timeLeft() {
    return Math.max(0, this.waveLen - this.waveTime);
  }
  private beginWave(nw: number) {
    this.wave = nw;
    this.waveTime = 0;
    this.waveLen = B.waveLength(nw, this.diff, this.biome);
    this.surgeDelay = this.isBossWave(nw) ? C.SURGE_CALM_BOSS : C.SURGE_CALM;
    this.surgeTimer = C.SURGE_DURATION;
    this.announceTimer = 2.2;
  }
  pickBaseKind(): string {
    if (this.biome === "hell") return hellPickKind(this.wave);
    const w = this.wave;
    const ks = ["red", "blue", "tank", "yellow", "sprinter", "brute", "bomber", "healer", "wizard", "stinger", "kamikaze"];
    const ws = [
      10,
      6 + Math.min(w, 10),
      Math.max(0, Math.min(w - 2, 8)),
      Math.max(0, Math.min(w - 1, 8)),
      Math.max(0, Math.min(w - 3, 7)),
      Math.max(0, Math.min(w - 5, 6)),
      Math.max(0, Math.min(w - 6, 5)),
      Math.max(0, Math.min(Math.floor((w - 8) / 2), 3)),
      w >= 15 ? Math.max(0, Math.min(w - 14, 3)) : 0,
      w >= 25 ? Math.max(0, Math.min((w - 24) * 2, 10)) : 0,
      w >= C.KAMIKAZE_WAVE ? Math.max(0, Math.min(w - 19, 5)) : 0,
    ];
    let kind = weightedPick(ks, ws);
    if (kind === "blue" && w <= C.EARLY_BAT_WAVES && Math.random() < C.EARLY_BAT_NERF) {
      const rk: string[] = [], rw: number[] = [];
      ks.forEach((k, i) => {
        if (k !== "blue" && ws[i] > 0) {
          rk.push(k);
          rw.push(ws[i]);
        }
      });
      if (rk.length) kind = weightedPick(rk, rw);
    }
    return kind;
  }
  pickKind() {
    if (Object.keys(this.curses).length && Math.random() < curseSpawnChance(this.curses)) {
      const ck = pickCurseKind(this.curses);
      if (ck) return ck;
    }
    return this.pickBaseKind();
  }

  /** Dönüş: dalga değişti mi. Yeni yaratıklar `out`a eklenir. */
  update(dt: number, enemies: Enemy[], waveMult: (w: number) => number, bossActive: boolean): boolean {
    this.waveTime += dt;
    if (this.announceTimer > 0) this.announceTimer -= dt;
    if (this.surgeDelay > 0) this.surgeDelay = Math.max(0, this.surgeDelay - dt);
    else if (this.surgeTimer > 0) this.surgeTimer = Math.max(0, this.surgeTimer - dt);
    let changed = false;
    if (bossActive && !this.bossPending) this.bossClock += dt;
    else this.bossClock = 0;
    if (this.waveTime >= this.waveLen) {
      this.beginWave(this.wave + 1);
      changed = true;
      if (this.isBossWave(this.wave)) {
        this.bossPending = true;
        this.surgeTimer = 0;
        this.announceText = t("ui.boss_coming");
      } else if (this.biome === "hell") this.announceText = t("ui.ann_hell", this.wave);
      else if (this.wave > C.HELL_PORTAL_WAVE) this.announceText = t("ui.ann_rage", this.wave);
      else this.announceText = t("ui.ann_surge", this.wave);
    }
    const bossTime = this.bossPending || (bossActive && this.bossClock < C.BOSS_WAVE_TIMEOUT);
    const tw = B.spawnTempoWave(this.wave, this.biome);
    let interval = Math.max(0.2, 1.15 - tw * 0.035) / (this.pace * C.SPAWN_RATE_TUNE * this.spawnRateMult);
    if (bossTime) interval /= C.BOSS_SPAWN_RATE;
    else {
      interval /= 1 + Math.min(C.WAVE_ACCEL_MAX, this.waveTime * C.WAVE_ACCEL_RATE);
      if (this.surgeActive()) interval *= C.SURGE_RATE;
    }
    this.spawnTimer -= dt;
    if (this.spawnTimer <= 0) {
      this.spawnTimer = interval;
      let cap = B.maxAliveEnemies(tw);
      if (bossTime) cap = Math.max(6, Math.floor(cap * C.BOSS_CROWD_SHARE));
      const sw = this.curses.swarm || 0;
      if (sw) cap = Math.floor(cap * (1 + C.CURSE_SWARM_CAP * sw));
      if (enemies.length >= cap) return changed;
      let count = tw < 3 ? 1 : tw < 6 ? 2 : tw < 10 ? 3 : tw < 16 ? 4 : 5;
      if (bossTime) count = Math.max(1, Math.round(count * C.BOSS_SPAWN_RATE));
      else {
        count += Math.min(C.WAVE_ACCEL_EXTRA_MAX, Math.floor(this.waveTime / C.WAVE_ACCEL_EXTRA_AFTER));
        if (this.surgeActive()) count += C.SURGE_EXTRA;
      }
      const hell = this.biome === "hell";
      count += sw;
      count += B.lateWaveBoost(this.wave, this.biome)[2];
      const frenzy = this.curses.frenzy || 0;
      for (let i = 0; i < count; i++) {
        const kind = this.pickKind();
        const [x, y] = this.spawnPosFn();
        let e: Enemy;
        if (CURSE_KINDS.includes(kind)) e = new Enemy(kind, x, y, waveMult(this.wave), 1, this.wave, null, this.biome);
        else if (hell) e = new Enemy(null, x, y, waveMult(this.wave), 1, this.wave, kind, "hell");
        else e = makeMapEnemy(this.theme, kind, x, y, waveMult(this.wave), 1, this.wave);
        if (frenzy) e.speed *= 1 + C.CURSE_FRENZY_SPD * frenzy;
        if (this.enemySpeedMult !== 1) e.speed *= this.enemySpeedMult;
        if (this.doom) this.doomify(e);
        this.lateBoost(e);
        if (!CURSE_KINDS.includes(kind)) this.mutateRoll(e);
        enemies.push(e);
      }
      let eliteChance = 0.12 + Math.min(0.28, this.wave * 0.008);
      if (this.surgeActive()) eliteChance += 0.1;
      if (!bossTime && this.wave % 5 === 0 && Math.random() < eliteChance) {
        const [x, y] = this.spawnPosFn();
        let el: Enemy;
        if (hell) el = new Enemy(null, x, y, waveMult(this.wave) * 1.1, 1, this.wave, "h_warden", "hell");
        else {
          el = makeMapEnemy(this.theme, "elite", x, y, waveMult(this.wave) * 1.1, 1, this.wave);
          if (this.doom) this.doomify(el);
        }
        this.lateBoost(el);
        enemies.push(el);
      }
    }
    return changed;
  }

  mutateRoll(e: Enemy) {
    const w = this.wave + (this.biome === "hell" ? C.HELL_WAVE_OFFSET : 0);
    if (w < C.MUTANT_FROM) return;
    this.mutantCounter++;
    if (this.mutantCounter % C.MUTANT_EVERY === 0) e.mutate();
  }
  lateBoost(e: Enemy) {
    const [hk, dk0] = B.lateWaveBoost(this.wave, this.biome);
    const dk = dk0 * this.dmgMult;
    if (hk === 1 && dk === 1) return;
    e.max_hp *= hk;
    e.hp *= hk;
    e.dmg *= dk;
    e.contact_dps *= dk;
  }
  doomify(e: Enemy) {
    const [hk, dk] = B.doomMult(this.wave);
    if (hk === 1 && dk === 1) return;
    e.max_hp *= hk;
    e.hp *= hk;
    e.dmg *= dk;
    e.contact_dps *= dk;
  }
}
