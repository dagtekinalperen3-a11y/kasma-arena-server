/**
 * Bir koşunun bütün durumu — Python `RunState` karşılığı.
 */
import { clamp, dist, normDir, rand, TAU, RGB, lighten } from "../core/util";
import * as B from "./balance";
import { GD, WEAPON_BY_KEY, SHOP_BY_KEY, ENEMY_COLORS, BOOK_BY_KEY } from "./data";
import { Player } from "./player";
import { Enemy, EnemyProjectile, DMG } from "./enemy";
import { Boss, scaleBossesToPlayer } from "./boss";
import { WaveManager } from "./waves";
import { FX, zigzag } from "./fx";
import { PlayerProjectile, Pickup, BigDrop, Hazard, BossChest, MapKey, HellPortal, PickupKind } from "./objects";
import { WObj, GhostBlade, Hawk, SpectralWolf, updateTimedWeapons, updatePassiveWeapons, blockWithBook } from "./weapons";
import { updateSkinUlt, BlackHole } from "./ults";
import { LevelUp } from "./levelup";
import { applyShopItem } from "./shop";
import { sfx, audio } from "../core/audio";
import { haptic } from "../core/native";
import { t } from "../core/i18n";

const C = GD;
const GOLD: RGB = [232, 186, 90];
const LEVEL_COLOR: RGB = C.LEVEL_COLOR, LEVEL_COLOR2: RGB = C.LEVEL_COLOR2;
const MAGNET_COLOR: RGB = C.MAGNET_COLOR, MAGNET_COLOR2: RGB = C.MAGNET_COLOR2;
const KEY_COLOR: RGB = C.KEY_COLOR;
const LEGEND_COLOR: RGB = C.LEGEND_COLOR, LEGEND_COLOR2: RGB = C.LEGEND_COLOR2;
const PORTAL_COLOR: RGB = C.HELL_PORTAL_COLOR, PORTAL_COLOR2: RGB = C.HELL_PORTAL_COLOR2;

export type Target = (Enemy | Boss) & { [k: string]: any };

/** Koşunun meta (kalıcı kayıt) ile konuştuğu arayüz. */
export interface RunMeta {
  unlockedWeapons(): string[];
  unlockedBooks(): string[];
  mutedWeapons(): string[];
  mutedBooks(): string[];
  ownsBook(key: string): boolean;
  masteryBonus(key: string): number;
  stat(key: string): number;
  addStat(key: string, n: number): void;
  unlockAch(id: string): void;
  bestScore(): number;
}

export interface RunInput {
  mx: number;
  my: number;
  aimX: number;
  aimY: number;
  aimManual: boolean;
  fire: boolean;
  dash: boolean;
  bonk: boolean;
  use: boolean;
}

export class ComboMeter {
  count = 0;
  best = 0;
  timer = 0;
  window = 2.1;
  pulse = 0;
  addKill() {
    this.count++;
    this.best = Math.max(this.best, this.count);
    this.timer = this.window;
    this.pulse = 1;
  }
  multiplier() {
    return 1 + Math.min(this.count * 0.04, 2);
  }
  update(dt: number) {
    if (this.timer > 0) {
      this.timer -= dt;
      if (this.timer <= 0) this.count = 0;
    }
    if (this.pulse > 0) this.pulse = Math.max(0, this.pulse - dt * 3);
  }
}

export class Run {
  W = B.WORLD_W;
  H = B.WORLD_H;
  fx: FX;
  player: Player;
  enemies: Enemy[] = [];
  bosses: Boss[] = [];
  hazards: Hazard[] = [];
  pickups: Pickup[] = [];
  enemyProjectiles: EnemyProjectile[] = [];
  playerProjectiles: PlayerProjectile[] = [];
  wobjs: WObj[] = [];
  ghostBlades: GhostBlade[] = [];
  hawks: Hawk[] = [];
  wolves: SpectralWolf[] = [];
  blackHoles: BlackHole[] = [];
  bigDrops: BigDrop[] = [];
  chests: BossChest[] = [];
  mapKeys: MapKey[] = [];
  legendChest: BossChest | null = null;
  hellPortal: HellPortal | null = null;
  targets: Target[] = [];
  waves: WaveManager;
  combo = new ComboMeter();
  levelup: LevelUp;
  dmgLog: Record<string, number> = {};
  biome: B.Biome = "arena";
  theme: string;
  diff: B.Diff;
  // kamera (dünya birimi)
  camX = 0;
  camY = 0;
  viewW = 1100;
  viewH = 560;
  kills = 0;
  timeStop = 0;
  bonkHits = 0;
  coinsEarned = 0;
  gemCoins = 0;
  scoreFrac = 0;
  gold = 0;
  runTime = 0;
  score = 0;
  gameOver = false;
  arenaWaves = 0;
  pendingLevelups = 0;
  bestAtStart: number;
  recordBeaten = false;
  recordFlash = -1;
  deathCause = "";
  keysGot = 0;
  keysPlaced = false;
  keyRespawnT = 0;
  legendOpened = 0;
  legendHands = 0;
  runKeys = 0;
  pentaInside = new Set<number>();
  minionT = 0;
  wolfHowlCd = 6;
  batHealBudget = 0;
  levelKills = 0;
  magnetKills = 0;
  magnetsTaken = 0;
  magnetsDropped = 0;
  levelDropsTotal = 0;
  chestsOpened = 0;
  bossesKilled = 0;
  goblinsCaught = 0;
  snakesKilled = 0;
  curses: Record<string, number> = {};
  curseScoreBonus = 0;
  doomWarned = false;
  milestones = new Set<string>();
  stragglerTimer = 0;
  campAnchor: [number, number] | null = null;
  campStill = 0;
  campFactor = 0;
  campWarned = false;
  beatenBossWave = 0;
  storedEvents: string[] = [];
  onEvent: (ev: string, data?: any) => void = () => {};
  goblinTimer = 0;

  constructor(public meta: RunMeta, skinId: string, diff: B.Diff, theme: string, cosmeticPerks: Record<string, number>[] = []) {
    this.fx = new FX();
    this.diff = diff;
    this.theme = theme;
    this.player = new Player(skinId, meta, cosmeticPerks);
    this.player.x = this.W / 2;
    this.player.y = this.H / 2;
    this.player.onDash = () => meta.addStat("total_dashes", 1);
    this.waves = new WaveManager(diff, "arena", () => this.nearCameraPoint());
    this.setMapTheme(theme);
    this.levelup = new LevelUp(this);
    this.bestAtStart = meta.bestScore();
    DMG.log = this.dmgLog;
  }

  themeHp = 0;
  themeSpeed = 1;
  themeSpawn = 1;
  setMapTheme(theme: string) {
    const rules: Record<string, Record<string, number>> = C.MAP_RULES;
    if (!rules[theme]) theme = "stone";
    const p = this.player;
    this.theme = theme;
    const r = rules[theme];
    this.themeHp = r.enemy_hp || 0;
    this.themeSpeed = r.enemy_speed || 1;
    this.themeSpawn = r.spawn_rate || 1;
    p.run_xp_mult += r.xp || 0;
    p.run_coin_mult += r.gold || 0;
    this.applyWaveMods();
  }
  applyWaveMods() {
    const arena = this.biome !== "hell";
    this.waves.enemySpeedMult = arena ? this.themeSpeed : 1;
    this.waves.spawnRateMult = arena ? this.themeSpawn : 1;
    this.waves.theme = arena ? this.theme : "stone";
    this.waves.doom = arena && this.theme !== "stone";
  }
  /** Harita başarım sayaçlarına bu koşunun katkısı. */
  mapStatValues(): Record<string, number> {
    const th = this.theme;
    if (th === "stone") return {};
    const p = this.player;
    const src: Record<string, number> = {
      kills: this.kills, bosses: this.bossesKilled, shots: p.run_shots, dashes: p.dash_count, bonk_hits: this.bonkHits,
      wave: this.totalWave(), wind: p.books.r_spd || 0, time: Math.floor(this.runTime), snakes: this.snakesKilled,
    };
    const out: Record<string, number> = {};
    for (const [st, [mp]] of Object.entries(C.MAP_ACH_STATS as Record<string, [string, string]>)) if (mp === th) out[st] = src[C.MAP_STAT_SRC[st]] || 0;
    return out;
  }

  // ------------------------------------------------------------------
  // Kamera & doğum noktaları
  // ------------------------------------------------------------------
  updateCamera(dt: number, snap = false) {
    const p = this.player;
    const tx = clamp(p.x - this.viewW / 2, 0, Math.max(0, this.W - this.viewW));
    const ty = clamp(p.y - this.viewH / 2, 0, Math.max(0, this.H - this.viewH));
    const k = snap ? 1 : Math.min(1, dt * 7);
    this.camX += (tx - this.camX) * k;
    this.camY += (ty - this.camY) * k;
  }
  camRect(inflate = 0) {
    return { l: this.camX - inflate, t: this.camY - inflate, r: this.camX + this.viewW + inflate, b: this.camY + this.viewH + inflate };
  }
  inWorld(x: number, y: number, m = 0) {
    return x >= m && y >= m && x <= this.W - m && y <= this.H - m;
  }

  private campSpawnPoint(): [number, number] | null {
    const p = this.player;
    for (let i = 0; i < 14; i++) {
      const a = Math.random() * TAU, r = rand(230, 430);
      const x = p.x + Math.cos(a) * r, y = p.y + Math.sin(a) * r;
      if (this.inWorld(x, y, 40)) return [x, y];
    }
    return null;
  }
  private aheadChance() {
    let w = this.waves.wave;
    if (this.biome === "hell") w += 25;
    if (w < 10) return 0;
    return Math.min(0.65, 0.2 + (w - 10) * 0.025);
  }
  aheadSpawnPoint(mvx: number, mvy: number): [number, number] | null {
    const p = this.player;
    const cam = this.camRect(60);
    for (let i = 0; i < 14; i++) {
      const s = rand(-0.75, 0.75), ca = Math.cos(s), sa = Math.sin(s);
      const ax = mvx * ca - mvy * sa, ay = mvx * sa + mvy * ca;
      const d = rand(this.viewW * 0.6, this.viewW * 0.85);
      const x = p.x + ax * d, y = p.y + ay * d;
      if (!this.inWorld(x, y, 60)) continue;
      if (x > cam.l && x < cam.r && y > cam.t && y < cam.b) continue;
      return [x, y];
    }
    return null;
  }
  nearCameraPoint(margin = 60): [number, number] {
    const cam = this.camRect();
    if (this.campFactor > 0 && this.player.alive && Math.random() < this.campFactor) {
      const pt = this.campSpawnPoint();
      if (pt) return pt;
    }
    const ah = this.aheadChance();
    if (ah > 0 && Math.random() < ah) {
      const p = this.player;
      const sp = Math.hypot(p.vx, p.vy);
      if (p.alive && sp > 60) {
        const pt = this.aheadSpawnPoint(p.vx / sp, p.vy / sp);
        if (pt) return pt;
      }
    }
    for (let i = 0; i < 12; i++) {
      const side = Math.floor(Math.random() * 4);
      let x: number, y: number;
      if (side === 0) [x, y] = [rand(cam.l, cam.r), cam.t - margin];
      else if (side === 1) [x, y] = [rand(cam.l, cam.r), cam.b + margin];
      else if (side === 2) [x, y] = [cam.l - margin, rand(cam.t, cam.b)];
      else [x, y] = [cam.r + margin, rand(cam.t, cam.b)];
      if (this.inWorld(x, y)) return [x, y];
    }
    const cx = (cam.l + cam.r) / 2, cy = (cam.t + cam.b) / 2;
    for (let i = 0; i < 30; i++) {
      const a = Math.random() * TAU, rr = Math.max(this.viewW, this.viewH) * rand(0.55, 0.75);
      const x = cx + Math.cos(a) * rr, y = cy + Math.sin(a) * rr;
      if (this.inWorld(x, y, 40) && !(x > cam.l + 80 && x < cam.r - 80 && y > cam.t + 80 && y < cam.b - 80)) return [x, y];
    }
    return this.campSpawnPoint() || [this.W / 2, this.H / 2];
  }

  private updateCamping(dt: number) {
    const p = this.player;
    const a = this.campAnchor;
    if (!a || Math.hypot(p.x - a[0], p.y - a[1]) > 170) {
      this.campAnchor = [p.x, p.y];
      this.campStill = 0;
    } else this.campStill += dt;
    const edge = Math.min(p.x, this.W - p.x, p.y, this.H - p.y);
    const corner = Math.min(p.x, this.W - p.x) < 460 && Math.min(p.y, this.H - p.y) < 460;
    let f = 0;
    if (edge < 460) f = 0.35;
    if (corner) f = 0.6;
    if (this.campStill >= 7) f = Math.min(0.85, f + 0.45);
    this.campFactor = f;
    if (f >= 0.6 && p.alive && !this.campWarned) {
      this.campWarned = true;
      this.fx.popup(p.x, p.y - 100, t("fx.no_camping"), [255, 150, 120], 18, 2.4, true);
    }
  }

  private repositionStragglers(dt: number) {
    const p = this.player;
    if (!p.alive) return;
    this.stragglerTimer -= dt;
    if (this.stragglerTimer > 0) return;
    this.stragglerTimer = 0.45;
    let mvx: number, mvy: number, speed: number;
    if (p.dash_time > 0) {
      mvx = p.dash_dx;
      mvy = p.dash_dy;
      speed = p.dash_speed;
    } else {
      speed = Math.hypot(p.vx, p.vy);
      if (speed < 1e-3) return;
      mvx = p.vx / speed;
      mvy = p.vy / speed;
    }
    if (speed < 95) return;
    let moved = 0;
    for (const e of this.enemies) {
      if (moved >= 4) break;
      if (!e.alive || e.isMini || e.guardOf) continue;
      if (e.warpCd > 0) {
        e.warpCd = Math.max(0, e.warpCd - 0.45);
        continue;
      }
      const dx = e.x - p.x, dy = e.y - p.y;
      const d = Math.hypot(dx, dy);
      if (d < 680) continue;
      if ((dx * mvx + dy * mvy) / Math.max(1e-3, d) > -0.25) continue;
      const spot = this.aheadSpawnPoint(mvx, mvy);
      if (!spot) continue;
      e.x = spot[0];
      e.y = spot[1];
      e.warpCd = 3.2;
      e.spawnT = Math.min(e.spawnT, 0.12);
      moved++;
    }
  }

  waveHpMult(wave: number) {
    const base = this.biome === "hell" ? B.hellHpMult(wave) : B.arenaHpMult(wave) * (1 + this.themeHp);
    return base * (1 + this.player.enemy_hp_curse);
  }

  totalWave() {
    return this.biome === "hell" ? this.waves.wave + this.arenaWaves : this.waves.wave;
  }

  // ------------------------------------------------------------------
  // Hedefler, vuruş kapıları
  // ------------------------------------------------------------------
  rebuildTargets() {
    const tg = this.targets;
    tg.length = 0;
    for (const e of this.enemies) if (e.alive) tg.push(e as Target);
    for (const b of this.bosses) if (b.alive) tg.push(b as Target);
  }
  weaponTargets(maxD: number): Target[] {
    const p = this.player;
    const out: Target[] = [];
    const m2 = maxD * maxD;
    for (const e of this.targets) {
      if (!e.alive) continue;
      if (e.isBoss && (e as Boss).isHidden()) continue;
      const dx = e.x - p.x, dy = e.y - p.y;
      if (dx * dx + dy * dy <= m2) out.push(e);
    }
    return out;
  }
  applyExecute(e: Target, dmg: number) {
    const p = this.player;
    if (p.execute_threshold > 0 && !e.isBoss && e.kind !== "elite" && e.hp > 0 && !e.phased) {
      let thr = p.execute_threshold;
      if (B.enemyWeightClass(e) === "tough") thr *= C.EXECUTE_TOUGH_K;
      if ((e.hp - dmg) / Math.max(1e-6, e.max_hp) <= thr && e.hp > dmg) {
        const arm = clamp(e.armor || 0, 0, 0.95);
        this.fx.popup(e.x, e.y - e.radius - 18, t("fx.execute"), [255, 170, 80], 14, 0.5, true);
        return (e.hp + 1) / (1 - arm);
      }
    }
    return dmg;
  }
  weaponHit(e: Target, dmg: number, kb = 90, crit: boolean | null = null, wlvl: number | null = null) {
    const p = this.player;
    if (crit === null) crit = Math.random() < p.effCritChance();
    if (crit) {
      p.run_crits++;
      dmg *= p.effCritDmg();
    }
    if (p.boss_hunter > 0 && (e.isBoss || e.kind === "elite")) dmg *= 1 + p.bossHunterBonus();
    dmg = B.capOneshot(e, dmg, wlvl);
    dmg = this.applyExecute(e, dmg);
    const [kx, ky] = normDir(p.x, p.y, e.x, e.y);
    const rk = e.isBoss ? 12 : kb;
    const died = e.takeDamage(dmg, crit, this.fx, kx * rk, ky * rk);
    if (p.vamp_level > 0) p.lifesteal(dmg * 0.02 * p.vamp_level);
    if (died) this.onEnemyKilled(e);
    return died;
  }
  fieldDamage(e: Target, dmg: number, burn = 0, wlvl: number | null = null) {
    const p = this.player;
    if (p.boss_hunter > 0 && (e.isBoss || e.kind === "elite")) dmg *= 1 + p.bossHunterBonus();
    dmg = B.capOneshot(e, dmg, wlvl);
    dmg = this.applyExecute(e, dmg);
    const died = e.takeDamage(dmg, false, this.fx, 0, 0, true);
    if (burn > 0) e.applyBurn(burn, 1.4);
    if (p.vamp_level > 0) p.lifesteal(dmg * 0.02 * p.vamp_level);
    if (died) this.onEnemyKilled(e);
    return died;
  }
  ultHit(e: Target, dmg: number, crit = false, kb = 0) {
    const p = this.player;
    if (p.boss_hunter > 0 && (e.isBoss || e.kind === "elite")) dmg *= 1 + p.bossHunterBonus();
    const [kx, ky] = normDir(p.x, p.y, e.x, e.y);
    const died = e.takeDamage(dmg, crit, this.fx, kx * kb, ky * kb);
    if (died) this.onEnemyKilled(e);
    return died;
  }
  private explosionSplash(cx: number, cy: number, base: number, excludeId: number) {
    const p = this.player;
    if (p.explosive_level <= 0) return;
    for (const e2 of this.enemies) {
      if (!e2.alive || e2.id === excludeId) continue;
      if (dist(cx, cy, e2.x, e2.y) <= 74) {
        if (e2.takeDamage(base * 0.35 * p.explosive_level, false, this.fx)) this.onEnemyKilled(e2 as Target);
      }
    }
    this.fx.ring(cx, cy, [240, 130, 60], 10, 140, 0.25, 2.5);
  }
  batHeal(_x: number, _y: number) {
    const p = this.player;
    if (!p.alive || this.batHealBudget <= 0) return;
    const amt = Math.min(this.batHealBudget, p.max_hp * C.BAT_HEAL_FRAC);
    this.batHealBudget -= amt;
    p.heal(amt);
  }
  addWObj<T extends WObj>(o: T): T {
    this.wobjs.push(o);
    return o;
  }
  trackObj<T extends WObj>(o: T): T {
    return o;
  }
  dropObj(o: WObj) {
    o.alive = false;
  }

  // ------------------------------------------------------------------
  // Oyuncu saldırıları
  // ------------------------------------------------------------------
  doPlayerAttack(adx: number, ady: number) {
    const p = this.player;
    let mult = 1;
    let echo = false;
    if (p.echo_level > 0) {
      p.echo_count++;
      if (p.echo_count % 4 === 0) {
        mult *= 1 + p.echo_level;
        echo = true;
      }
    }
    if (p.swarm_level > 0) {
      let near = 0;
      for (const e of this.enemies) {
        if (e.alive && dist(e.x, e.y, p.x, p.y) < 240 && ++near >= 3) break;
      }
      if (near >= 3) mult *= 1 + p.swarmBonus();
    }
    const n = 1 + p.multishot_level;
    const base = Math.atan2(ady, adx);
    const speed = 660 * p.proj_speed_mult;
    const sk = p.skin;
    const off = p.radius + sk.wlen * 0.55;
    for (let i = 0; i < n; i++) {
      const ang = base + ((i - (n - 1) / 2) * 9 * Math.PI) / 180;
      const pr = new PlayerProjectile(p.x + adx * off, p.y + ady * off, Math.cos(ang) * speed, Math.sin(ang) * speed, p.effDmg() * mult, p.effPierceHits(), p.effCritChance(), p.effCritDmg(), p.homing_level, sk.proj, sk.color, sk.accent);
      pr.wsrc = "gun";
      this.playerProjectiles.push(pr);
    }
    p.run_shots += n;
    p.recoil = 1;
    p.flash_t = 0.08;
    if (echo) this.fx.ring(p.x, p.y, [255, 235, 150], 10, 190, 0.28, 2.5);
    this.fx.spark(p.x + adx * off, p.y + ady * off, sk.accent, adx * 60, ady * 60, 0.12, 3);
    sfx("shoot_" + sk.sfx, 0.42, 0.06);
  }

  doBonk() {
    DMG.src = "bonk";
    const p = this.player;
    const smash = !!p.titan_smash && p.smash_timer <= 0;
    let radius: number;
    if (smash) {
      p.smash_timer = 10;
      radius = Math.hypot(this.W, this.H);
      this.fx.popup(p.x, p.y - 56, t("fx.titan_smash"), [150, 255, 120], 30, 1.1, true);
      this.fx.flash([150, 255, 130], 0.4);
      this.fx.shake(14, 0.45);
      for (let k = 0; k < 4; k++) this.fx.shockwave(p.x, p.y, 260 + k * 260, [150, 255, 130], 0.55, 8 - k);
      sfx("explosion", 1);
    } else radius = p.effBonkRadius();
    const dmg = p.effDmg() * 1.9 * p.bonk_mult;
    let hit = 0;
    const hitIds = new Set<number>();
    for (const e of this.targets) {
      if (!e.alive) continue;
      if (dist(p.x, p.y, e.x, e.y) > radius) continue;
      hit++;
      hitIds.add(e.id);
      const crit = Math.random() < p.effCritChance();
      let fd = dmg * (crit ? p.effCritDmg() : 1);
      fd = this.applyExecute(e, fd);
      const [kx, ky] = normDir(p.x, p.y, e.x, e.y);
      if (p.boss_hunter > 0 && (e.isBoss || e.kind === "elite")) fd *= 1 + p.bossHunterBonus();
      const died = e.takeDamage(fd, crit, this.fx, kx * 260, ky * 260);
      if (p.roar_level > 0 && !e.isBoss) {
        e.fearTimer = Math.max(e.fearTimer, 1 + 0.6 * p.roar_level);
        e.fearVuln = Math.max(e.fearVuln, Math.min(0.6, 0.25 + 0.05 * p.roar_level));
      }
      if (p.vamp_level > 0) p.lifesteal(fd * 0.02 * p.vamp_level);
      if (died) this.onEnemyKilled(e);
    }
    if (smash) {
      for (const e of this.enemies) if (e.alive && e.hp > 1) e.hp = Math.max(1, e.hp * 0.5);
    }
    this.bonkHits += hit;
    if (hit >= 8) this.meta.unlockAch("bonk8");
    if (p.chain_level > 0) {
      const cands = this.enemies.filter((e) => e.alive && !hitIds.has(e.id) && dist(p.x, p.y, e.x, e.y) <= radius * 2.2);
      cands.sort((a, b) => dist(p.x, p.y, a.x, a.y) - dist(p.x, p.y, b.x, b.y));
      for (const e of cands.slice(0, 1 + p.chain_level)) {
        const died = e.takeDamage(dmg * 0.5, false, this.fx);
        this.fx.bolt(zigzag(p.x, p.y, e.x, e.y, 5, 10), [120, 200, 255], 0.2, 2);
        if (died) this.onEnemyKilled(e as Target);
      }
    }
    this.fx.ring(p.x, p.y, [240, 150, 80], 20, 260, 0.35, 3);
    this.fx.shockwave(p.x, p.y, radius, [255, 170, 90], 0.3, 4);
    this.fx.shake(hit ? 5 : 2.5, 0.15);
    sfx("bonk", 1);
    haptic("medium");
    DMG.src = "other";
  }

  doStormStrike() {
    DMG.src = "storm";
    const p = this.player;
    const tg = this.targets.filter((e) => e.alive);
    if (!tg.length) return;
    const e = tg[Math.floor(Math.random() * tg.length)];
    const died = e.takeDamage(p.effDmg() * (0.9 + 0.35 * p.storm_level), false, this.fx);
    this.fx.bolt(zigzag(e.x, e.y - 320, e.x, e.y, 6, 22), [190, 215, 255], 0.3, 3);
    this.fx.shockwave(e.x, e.y, 40, [190, 215, 255], 0.25, 3);
    sfx("lightning", 0.6);
    if (died) this.onEnemyKilled(e);
    DMG.src = "other";
  }

  // ------------------------------------------------------------------
  // Öldürme / ganimet
  // ------------------------------------------------------------------
  dropPickup(x: number, y: number, kind: PickupKind, value: number) {
    if (value <= 0) return;
    const busy = this.pickups.length > 160;
    const mr = busy ? 95 : 30;
    let best: Pickup | null = null, bd = mr;
    for (const pu of this.pickups) {
      if (pu.kind !== kind || pu.collected || pu.magnet) continue;
      const d = Math.abs(x - pu.x) + Math.abs(y - pu.y);
      if (d < bd) {
        best = pu;
        bd = d;
      }
    }
    if (!best && this.pickups.length >= 240) {
      bd = 1e9;
      for (const pu of this.pickups) {
        if (pu.kind !== kind || pu.collected || pu.magnet) continue;
        const d = Math.abs(x - pu.x) + Math.abs(y - pu.y);
        if (d < bd) {
          best = pu;
          bd = d;
        }
      }
    }
    if (best) {
      best.value += value;
      return;
    }
    this.pickups.push(new Pickup(x + rand(-8, 8), y + rand(-8, 8), kind, value));
  }

  onEnemyKilled(e: Target) {
    if (e.deathCounted) return;
    e.deathCounted = true;
    const p = this.player;
    if (e.kind === "bomber") {
      this.hazards.push(new Hazard(e.x, e.y, C.BOMBER_RADIUS, C.BOMBER_DELAY, e.dmg * C.BOMBER_DMG_MULT, null, ENEMY_COLORS.bomber, "bomber"));
      this.fx.ring(e.x, e.y, ENEMY_COLORS.bomber, 16, 180, 0.4, 3);
    }
    this.kills++;
    if (e.variant === "j_snake") this.snakesKilled++;
    this.combo.addKill();
    const heal = p.kill_heal + p.killHealAmount();
    if (heal > 0) p.heal(heal);
    if (p.soul_harvest > 0) {
      p.heal(2 * p.soul_harvest);
      p.soul_stacks = Math.min(p.soul_stacks + 1, 4 + 4 * p.soul_harvest);
      p.soul_timer = 5;
    }
    p.registerKillForFrenzy();
    const cm = this.combo.multiplier();
    const coin = B.scaledCoinGain(e.coin, p.effCoinMult() * B.econWaveFactor(this.waves.wave, this.biome, "gold", this.diff), this.biome);
    const xp = e.xp * B.econWaveFactor(this.waves.wave, this.biome, "xp", this.diff) * B.xpLevelSoftcap(p.level, this.totalWave());
    if (e.kind === "goblin") this.goblinLoot(e);
    const gain = e.score * cm * (1 + this.curseScoreBonus) * C.SCORE_GAIN + this.scoreFrac;
    this.score += Math.floor(gain);
    this.scoreFrac = gain - Math.floor(gain);
    if (!e.raised) {
      this.dropPickup(e.x, e.y, "coin", coin);
      this.dropPickup(e.x, e.y, "xp", xp);
    }
    if (e.kind === "splitter" && (e.splitGen || 0) < 2) this.splitEnemy(e);
    if (Math.random() < C.HEART_DROP_CHANCE && p.hp < p.max_hp * 0.9) this.pickups.push(new Pickup(e.x, e.y, "heart", 26));
    const canStone = this.levelDropsTotal < this.magnetsDropped;
    if (canStone) this.levelKills++;
    if (canStone && !this.bigDrops.some((d) => d.kind === "level") && Math.random() < B.magnetDropChance(this.levelKills) * C.LEVEL_STONE_RATE) {
      this.levelKills = 0;
      this.levelDropsTotal++;
      this.bigDrops.push(new BigDrop("level", e.x, e.y, this.W, this.H));
      this.fx.popup(e.x, e.y - 58, t("fx.level_stone"), LEVEL_COLOR, 24, 2.2, true);
      this.fx.ring(e.x, e.y, LEVEL_COLOR, 30, 300, 0.8, 4);
      this.fx.shockwave(e.x, e.y, 160, LEVEL_COLOR2, 0.5, 5);
      sfx("levelup", 0.8);
    }
    this.magnetKills++;
    if (!this.bigDrops.some((d) => d.kind === "magnet") && Math.random() < B.magnetDropChance(this.magnetKills, p.effLuck())) {
      this.magnetKills = 0;
      this.magnetsDropped++;
      this.bigDrops.push(new BigDrop("magnet", e.x, e.y, this.W, this.H));
      this.fx.popup(e.x, e.y - 58, t("fx.magnet_drop"), MAGNET_COLOR, 24, 2.2, true);
      this.fx.ring(e.x, e.y, MAGNET_COLOR, 30, 300, 0.8, 4);
      sfx("magnet", 0.85);
    }
    if (this.combo.count > 0 && this.combo.count % 25 === 0) this.fx.popup(p.x, p.y - 54, `COMBO x${this.combo.count}!`, [100, 220, 220], 22, 1, true);
    if (this.combo.count >= 30) this.meta.unlockAch("combo30");
    if (this.kills === 1) this.meta.unlockAch("first_kill");
    if (this.kills >= 250) this.meta.unlockAch("massacre");
    if (e.isBoss) {
      const nb = Math.max(1, (e as Boss).champion);
      this.meta.addStat("bosses", nb);
      this.bossesKilled += nb;
      this.meta.unlockAch("boss");
    }
    if (e.isMini) {
      this.spawnBossChest(e);
      for (const g of e.guards || []) if (g.alive) g.guardOf = null;
    }
  }

  private splitEnemy(e: Target) {
    for (let i = 0; i < 2; i++) {
      const a = Math.random() * TAU;
      const ne = new Enemy("splitter", e.x + Math.cos(a) * 16, e.y + Math.sin(a) * 16, this.waveHpMult(this.waves.wave) * 0.45, 1, this.waves.wave, null, this.biome);
      ne.splitGen = (e.splitGen || 0) + 1;
      ne.radius *= 0.75;
      ne.hit_r *= 0.75;
      ne.coin = Math.floor(ne.coin * 0.5);
      ne.xp = Math.floor(ne.xp * 0.5);
      this.enemies.push(ne);
    }
  }

  private goblinLoot(e: Target) {
    const p = this.player;
    this.goblinsCaught++;
    const g = Math.floor((120 + 30 * this.waves.wave) * C.GOLD_TRIM);
    this.gold += g;
    this.coinsEarned += g;
    this.gemCoins += g;
    this.fx.popup(e.x, e.y - 50, `+${g}`, GOLD, 26, 1.6, true);
    const roll = Math.random() * (1 + p.effLuck());
    if (roll > 1.05) {
      this.levelup.rerollBonus++;
      this.fx.popup(e.x, e.y - 76, t("fx.free_reroll"), [110, 220, 140], 18, 1.6, true);
    }
    sfx("coin", 1);
  }

  spawnBossChest(b: Target, dx = 0) {
    const x = clamp(b.x + dx, 60, this.W - 60), y = clamp(b.y, 60, this.H - 60);
    this.chests.push(new BossChest(x, y, b.name));
    this.fx.ring(x, y, GOLD, 24, 230, 0.6, 4);
    this.fx.popup(x, y - 70, t("fx.chest_drop"), GOLD, 24, 1.6, true);
    sfx("coin", 0.9);
  }

  private grantWeapon(ch: BossChest) {
    const p = this.player;
    this.chestsOpened++;
    const canUp = Object.keys(p.weapons).filter((k) => WEAPON_BY_KEY[k] && p.weapons[k] < (WEAPON_BY_KEY[k].max ?? B.WEAPON_MAX_LEVEL));
    if (!canUp.length) {
      const gem = 400 + this.waves.wave * 45;
      const gold = Math.floor(gem * C.GOLD_TRIM);
      this.gold += gold;
      this.coinsEarned += gold;
      this.gemCoins += gem;
      this.fx.popup(ch.x, ch.y - 60, `+${gold}`, GOLD, 26, 1.6, true);
      this.fx.popup(ch.x, ch.y - 34, t(Object.keys(p.weapons).length ? "fx.chest_all_max" : "fx.chest_no_weapon"), [232, 234, 244], 14, 1.8, true);
      sfx("coin", 0.9);
      return;
    }
    const low = Math.min(...canUp.map((k) => p.weapons[k]));
    const lows = canUp.filter((k) => p.weapons[k] === low);
    const key = lows[Math.floor(Math.random() * lows.length)];
    const w = WEAPON_BY_KEY[key];
    p.weapons[key]++;
    const tier = B.rollRarity(p.effLuck());
    const gained = p.addWeaponBoost(key, B.rarityBoost(tier));
    let extra = false;
    if (tier >= B.RARITY_COUNT - 1 && p.weapons[key] < (w.max ?? B.WEAPON_MAX_LEVEL)) {
      p.weapons[key]++;
      extra = true;
    }
    const rc = B.RARITY_COLORS[tier];
    const wn = t(`w.${key}.name`);
    this.fx.popup(ch.x, ch.y - 80, gained > 0 ? `${t("rar." + tier)} • ${wn} +${Math.round(gained * 100)}%` : `${t("rar." + tier)} • ${wn}`, rc, 22 + 2 * tier, 1.9 + 0.25 * tier, true);
    this.fx.popup(ch.x, ch.y - 50, `${wn}  Lv.${p.weapons[key]}`, w.color, 15, 1.9, true);
    if (extra) this.fx.popup(ch.x, ch.y - 28, t("fx.chest_extra"), GOLD, 16, 2.2, true);
    this.fx.flash(rc, 0.25 + 0.06 * tier);
    for (let k = 0; k <= tier; k++) this.fx.ring(ch.x, ch.y, rc, 22 + 8 * tier, 240 + 60 * k, 0.55 + 0.08 * k, 3 + 0.5 * tier);
    if (tier >= 2) this.fx.shockwave(ch.x, ch.y, 140 + 70 * tier, rc, 0.45, 4 + tier);
    if (tier >= 3) {
      this.fx.burst(ch.x, ch.y, rc, 20 + 14 * tier, 300, 0.8, 4);
      this.fx.shake(4 + 3 * (tier - 2), 0.25);
    }
    sfx("chest", 1);
    haptic(tier >= 3 ? "heavy" : "medium");
    this.onEvent("chest", { key, tier });
  }

  private farPoint(minPlayer: number, avoid: [number, number][] = [], spacing = 0, maxPlayer?: number): [number, number] {
    const p = this.player;
    let best: [number, number] | null = null, bd = -1;
    for (let i = 0; i < 120; i++) {
      const x = rand(180, this.W - 180), y = rand(180, this.H - 180);
      const dp = dist(x, y, p.x, p.y);
      if (dp < minPlayer || (maxPlayer !== undefined && dp > maxPlayer)) continue;
      const dm = avoid.length ? Math.min(...avoid.map(([ax, ay]) => dist(x, y, ax, ay))) : 1e9;
      if (dm >= spacing) return [x, y];
      if (dm > bd) {
        best = [x, y];
        bd = dm;
      }
    }
    return best || [380, 380];
  }
  private placeKeys() {
    const pts: [number, number][] = [];
    for (let i = 0; i < C.KEY_COUNT; i++) pts.push(this.farPoint(C.KEY_PLAYER_MIN, pts, C.KEY_SPACING, C.KEY_PLAYER_MAX));
    this.mapKeys = pts.map(([x, y]) => new MapKey(x, y));
    this.keysGot = 0;
    this.keysPlaced = true;
  }
  nearestKey() {
    const p = this.player;
    let best: MapKey | null = null, bd = 1e18;
    for (const k of this.mapKeys) {
      if (k.taken) continue;
      const d = dist(k.x, k.y, p.x, p.y);
      if (d < bd) {
        bd = d;
        best = k;
      }
    }
    return best;
  }
  private updateKeys(dt: number) {
    const p = this.player;
    if (!this.keysPlaced) this.placeKeys();
    if (!this.mapKeys.length && !this.legendChest && this.keysGot <= 0 && this.legendOpened < C.LEGEND_CHEST_MAX) {
      this.keyRespawnT -= dt;
      if (this.keyRespawnT <= 0) {
        this.placeKeys();
        if (p.alive) this.fx.popup(p.x, p.y - 96, t("fx.keys_new"), KEY_COLOR, 20, 2.2, true);
      }
    }
    for (const k of this.mapKeys) {
      k.update(dt);
      if (!k.taken && p.alive && dist(k.x, k.y, p.x, p.y) < C.KEY_PICK_R + p.radius) {
        k.taken = true;
        this.keysGot++;
        this.runKeys++;
        this.fx.popup(k.x, k.y - 50, t("fx.key", this.keysGot, C.KEY_COUNT), KEY_COLOR, 22, 1.6, true);
        this.fx.ring(k.x, k.y, KEY_COLOR, 22, 220, 0.5, 3);
        sfx("coin", 1);
        haptic("light");
      }
    }
    this.mapKeys = this.mapKeys.filter((k) => !k.gone);
    if (this.keysGot >= C.KEY_COUNT && !this.legendChest && !this.mapKeys.some((k) => !k.taken)) {
      const [x, y] = this.farPoint(1100, this.hellPortal ? [[this.hellPortal.x, this.hellPortal.y]] : [], 300);
      const ch = new BossChest(x, y);
      ch.r = 34;
      ch.legend = true;
      this.legendChest = ch;
      this.keysGot = 0;
      if (p.alive) {
        this.fx.popup(p.x, p.y - 110, t("fx.keys_done"), LEGEND_COLOR, 22, 3, true);
        this.fx.flash(LEGEND_COLOR, 0.3);
      }
      sfx("levelup", 0.9);
    }
    const ch = this.legendChest;
    if (ch) {
      ch.update(dt, p);
      if (ch.opened && !ch.taken) {
        ch.taken = true;
        this.openLegendChest(ch);
      }
      if (!ch.alive) this.legendChest = null;
    }
  }
  private openLegendChest(ch: BossChest) {
    const p = this.player;
    this.legendOpened++;
    this.keyRespawnT = C.KEY_RESPAWN;
    const n = C.LEGEND_CHEST_LEVELS;
    for (let i = 0; i < n; i++) {
      p.level++;
      p.xp_to_next = B.xpNextNeed(p.xp_to_next, p.level);
    }
    p.onLevelUp(n);
    this.legendHands++;
    this.pendingLevelups += n + 1;
    this.fx.popup(ch.x, ch.y - 90, t("fx.legend_open", n), LEGEND_COLOR, 28, 2.6, true);
    this.fx.flash(LEGEND_COLOR, 0.5);
    this.fx.shake(9, 0.4);
    this.fx.burst(ch.x, ch.y, LEGEND_COLOR, 70, 420, 1, 5);
    this.fx.burst(ch.x, ch.y, LEGEND_COLOR2, 40, 320, 0.9, 4);
    for (let k = 0; k < 3; k++) this.fx.shockwave(ch.x, ch.y, 260 + 170 * k, k % 2 ? LEGEND_COLOR2 : LEGEND_COLOR, 0.6, 7 - k);
    sfx("chest", 1);
    sfx("second", 0.9);
    haptic("success");
    this.meta.unlockAch("legend");
  }

  spawnMiniBoss() {
    const p = this.player;
    const mult = this.waveHpMult(this.waves.wave);
    const hell = this.biome === "hell";
    let [hx, hy] = this.nearCameraPoint(140);
    hx = clamp(hx, 70, this.W - 70);
    hy = clamp(hy, 70, this.H - 70);
    const herald = new Enemy("herald", hx, hy, mult, 1, this.waves.wave, null, this.biome);
    const tier = B.miniBossTier(this.waves.wave, hell);
    herald.max_hp *= 1 + C.MINI_BOSS_HP_PER_TIER * tier;
    herald.hp = herald.max_hp;
    herald.heraldLeak = Math.max(C.MINI_BOSS_LEAK_MIN, Enemy.HERALD_LEAK - C.MINI_BOSS_LEAK_PER_TIER * tier);
    this.enemies.push(herald);
    const n = B.miniBossGuardCount(this.waves.wave, hell);
    for (let i = 0; i < n; i++) {
      const a = (TAU * i) / n;
      const g = new Enemy("shieldman", clamp(hx + Math.cos(a) * 60, 30, this.W - 30), clamp(hy + Math.sin(a) * 60, 30, this.H - 30), mult, 1, this.waves.wave, null, this.biome);
      g.max_hp *= 1 + C.MINI_BOSS_GUARD_HP_PER_TIER * tier;
      g.hp = g.max_hp;
      g.armor = Math.max(g.armor, Math.min(C.MINI_BOSS_GUARD_ARMOR_MAX, C.MINI_BOSS_GUARD_ARMOR_PER_TIER * tier));
      g.guardOf = herald;
      g.guardSlot = i;
      herald.guards!.push(g);
      this.enemies.push(g);
    }
    this.fx.popup(p.x, p.y - 110, t("fx.herald"), [246, 214, 120], 28, 2.4, true);
    this.fx.popup(p.x, p.y - 80, t("fx.herald_tip"), [178, 184, 206], 15, 2.4, true);
    this.fx.flash([246, 214, 120], 0.2);
    sfx("boss", 0.45);
  }

  private spawnBosses() {
    const w = this.waves;
    w.bossPending = false;
    w.bossActive = true;
    w.bossClock = 0;
    const wave = w.wave;
    const champ = B.bossCountForWave(wave);
    this.enemies.length = 0;
    this.bosses = this.bosses.filter((b) => b.alive);
    const hell = this.biome === "hell";
    const order: string[] = hell ? C.HELL_BOSS_ORDER : C.BOSS_ORDER;
    const kind = order[w.bossIdx % order.length];
    w.bossIdx++;
    const cam = this.camRect();
    const bx = clamp((cam.l + cam.r) / 2, 90, this.W - 90), by = clamp(cam.t + 110, 90, this.H - 90);
    const nb = new Boss(kind, bx, by, 1, 1, wave, hell, hell ? null : this.theme, champ);
    nb.bossWave = wave;
    this.bosses.push(nb);
    scaleBossesToPlayer([nb], estimatedDps(this.player));
    this.fx.flash([255, 60, 50], 0.35);
    if (champ > 1) this.fx.popup(this.camX + this.viewW / 2, this.camY + 70, t("ui.champ_boss"), [255, 90, 70], 30, 1.8, true);
    sfx("boss", 1);
    haptic("heavy");
    audio.playMusic("boss");
    this.onEvent("boss", nb);
  }

  openHellPortal() {
    this.meta.addStat("stone_cleared", 0);
    this.meta.unlockAch("stone_cleared");
    const p = this.player;
    let x = p.x, y = p.y;
    for (let i = 0; i < 24; i++) {
      const a = Math.random() * TAU, d = rand(150, 300);
      x = clamp(p.x + Math.cos(a) * d, 90, this.W - 90);
      y = clamp(p.y + Math.sin(a) * d, 90, this.H - 90);
      if (dist(x, y, p.x, p.y) > 120) break;
    }
    this.hellPortal = new HellPortal(x, y);
    this.fx.flash(PORTAL_COLOR, 0.6);
    this.fx.shake(12, 0.5);
    for (let k = 0; k < 4; k++) this.fx.shockwave(x, y, 120 + k * 150, PORTAL_COLOR, 0.7, 7 - k);
    this.fx.burst(x, y, PORTAL_COLOR2, 40, 300, 0.9, 4);
    this.waves.announceTimer = 3.2;
    this.waves.announceText = t("fx.portal_open");
    sfx("portal", 1);
    haptic("heavy");
  }

  enterHell() {
    if (this.biome === "hell") return;
    const p = this.player;
    this.collectAllPickups();
    this.biome = "hell";
    this.hellPortal = null;
    this.enemies.length = 0;
    this.bosses.length = 0;
    this.hazards.length = 0;
    this.enemyProjectiles.length = 0;
    this.playerProjectiles.length = 0;
    this.pickups.length = 0;
    for (const o of this.wobjs) o.alive = false;
    this.wobjs.length = 0;
    this.blackHoles.length = 0;
    this.pentaInside.clear();
    this.timeStop = 0;
    p.clearStatus();
    this.arenaWaves = this.waves.wave;
    this.waves = new WaveManager(this.diff, "hell", () => this.nearCameraPoint());
    this.waves.curses = this.curses;
    this.applyWaveMods();
    this.waves.announceTimer = 3.4;
    this.waves.announceText = t("ui.ann_hell", 1);
    p.x = this.W / 2;
    p.y = this.H / 2;
    p.hp = p.max_hp;
    p.invuln = Math.max(p.invuln, 2);
    for (const m of [...this.ghostBlades, ...this.hawks, ...this.wolves]) {
      m.x = p.x;
      m.y = p.y;
    }
    for (const d of this.bigDrops) {
      d.x = p.x + rand(-70, 70);
      d.y = p.y + rand(60, 120);
    }
    this.updateCamera(0, true);
    this.fx.flash(PORTAL_COLOR, 0.8);
    this.fx.shake(14, 0.7);
    this.fx.popup(p.x, p.y - 80, t("fx.welcome_hell"), [255, 140, 90], 30, 2.6, true);
    this.meta.unlockAch("hell_gate");
    sfx("portal", 1);
    audio.playMusic("hell");
    this.onEvent("biome", "hell");
  }

  collectAllPickups() {
    const p = this.player;
    for (const pu of this.pickups) {
      if (pu.collected || pu.dead) continue;
      if (pu.kind === "xp") {
        const lv = p.gainXp(pu.value);
        if (lv > 0) this.pendingLevelups += lv;
      } else if (pu.kind === "coin") this.addGold(pu.value);
      pu.collected = true;
    }
  }

  private addGold(v: number) {
    this.coinsEarned += v;
    this.gemCoins += v / (B.coinDropScale(this.biome) * B.econWaveFactor(this.waves.wave, this.biome, "gold", this.diff));
    this.gold += v;
  }

  buyShopItem(key: string) {
    const item = SHOP_BY_KEY[key];
    if (!item) return false;
    if (!B.shopItemUnlocked(item, this.waves.wave, this.biome)) return false;
    const p = this.player;
    const lvl = p.shop_levels[key] || 0;
    if (lvl >= item.max) return false;
    const cost = B.shopItemCost(item, lvl);
    if (this.gold < cost) {
      sfx("error", 0.6);
      return false;
    }
    this.gold -= cost;
    p.shop_levels[key] = lvl + 1;
    applyShopItem(p, key);
    this.fx.ring(p.x, p.y, item.color, 14, 160, 0.35, 3);
    sfx("buy", 1);
    haptic("light");
    if (item.cursed) this.meta.unlockAch("cursed");
    return true;
  }

  // ------------------------------------------------------------------
  // Kare güncellemesi
  // ------------------------------------------------------------------
  update(dt: number, inp: RunInput) {
    if (this.gameOver) {
      this.fx.update(dt);
      return;
    }
    const p = this.player;
    DMG.log = this.dmgLog;
    DMG.src = "other";
    this.runTime += dt;
    if (this.timeStop > 0) this.timeStop = Math.max(0, this.timeStop - dt);
    p.update(dt, inp.mx, inp.my, this.fx, { w: this.W, h: this.H });
    this.updateCamera(dt);
    this.rebuildTargets();
    updateSkinUlt(this, dt);
    const frozen = this.timeStop > 0;

    // nişan: elle (sağ başparmak / fare) ya da otomatik en yakın / en tehlikeli
    let adx = p.aim_dir[0], ady = p.aim_dir[1];
    if (inp.aimManual) {
      adx = inp.aimX;
      ady = inp.aimY;
    } else {
      const tg = this.autoAimTarget();
      if (tg) [adx, ady] = normDir(p.x, p.y, tg.x, tg.y);
      else if (Math.hypot(p.vx, p.vy) > 30) [adx, ady] = normDir(0, 0, p.vx, p.vy);
    }
    p.setAim(adx, ady);
    if (inp.fire && p.alive && p.tryAttack()) {
      DMG.src = "gun";
      this.doPlayerAttack(p.aim_dir[0], p.aim_dir[1]);
    }
    if (inp.bonk && p.tryBonk()) this.doBonk();
    if (inp.dash && p.tryDash(this.fx) && p.dash_slow_level > 0) {
      const rad = 200 + 30 * p.dash_slow_level, dur = 2 + 0.8 * p.dash_slow_level, mult = Math.max(0.3, 0.7 - 0.15 * p.dash_slow_level);
      for (const e of this.targets) if (e.alive && dist(e.x, e.y, p.x, p.y) < rad) e.applySlow(mult, dur);
      this.fx.shockwave(p.x, p.y, rad, [150, 210, 255], 0.3, 3);
    }
    if (p.orbit_level > 0) {
      DMG.src = "orbit";
      p.orbit_angle += dt * 3.2;
      const n = p.orbit_level;
      for (let i = 0; i < n; i++) {
        const a = p.orbit_angle + (i * TAU) / n;
        const ox = p.x + Math.cos(a) * 58, oy = p.y + Math.sin(a) * 58;
        for (const e of this.targets) {
          if (!e.alive) continue;
          if (dist(ox, oy, e.x, e.y) < e.radius + 10) {
            if (e.takeDamage(p.effDmg() * 0.45 * dt * 6, false, this.fx, 0, 0, true)) this.onEnemyKilled(e);
          }
        }
      }
    }
    if (p.storm_level > 0) {
      p.storm_timer -= dt;
      if (p.storm_timer <= 0) {
        p.storm_timer = Math.max(1, 2.6 - p.storm_level * 0.4);
        this.doStormStrike();
      }
    }
    // patron yarası
    let wd = 0;
    for (const b of this.bosses) if (b.alive) wd = Math.max(wd, b.wound);
    p.wound = wd;
    if (this.waves.bossPending) this.spawnBosses();

    const bctx = { fx: this.fx, player: p, projectiles: this.enemyProjectiles, hazards: this.hazards, W: this.W, H: this.H, kill: (b: any) => this.onEnemyKilled(b) };
    if (this.bosses.length) {
      DMG.src = "other";
      for (const b of [...this.bosses]) {
        if (b.alive) {
          if (!frozen) b.update(dt, bctx);
          if (b.summoned.length) {
            this.enemies.push(...b.summoned);
            b.summoned.length = 0;
          }
        }
        if (!b.alive) {
          this.onEnemyKilled(b as Target);
          this.beatenBossWave = Math.max(this.beatenBossWave, b.bossWave || this.waves.wave);
          const nb = Math.max(1, b.champion);
          for (let i = 0; i < nb; i++) this.spawnBossChest(b as Target, (i - (nb - 1) / 2) * 90);
          this.bosses.splice(this.bosses.indexOf(b), 1);
        }
      }
      if (!this.bosses.length) {
        const beaten = this.beatenBossWave || this.waves.wave;
        this.beatenBossWave = 0;
        if (this.waves.bossActive) {
          this.waves.bossActive = false;
          this.waves.announceTimer = 2.5;
          this.waves.announceText = t("ui.boss_down");
        }
        sfx("wave", 0.6);
        haptic("success");
        audio.playMusic(this.biome === "hell" ? "hell" : this.musicName());
        if (this.biome !== "hell") {
          const a = ({ 5: "wave5", 10: "wave10", 15: "wave15", 20: "wave20", 25: "wave25" } as Record<number, string>)[beaten];
          if (a) this.meta.unlockAch(a);
        } else this.meta.unlockAch("hell_boss");
        if (this.biome !== "hell" && beaten >= C.HELL_PORTAL_WAVE && !this.hellPortal) {
          if (this.theme === "stone") this.openHellPortal();
          else if (!this.doomWarned) {
            this.doomWarned = true;
            this.meta.addStat(`${this.theme}_cleared`, 0);
            this.onEvent("map_cleared", this.theme);
            this.waves.announceTimer = 3.4;
            this.waves.announceText = t("map.doom");
            this.fx.flash([200, 40, 40], 0.35);
          }
        }
      }
    }
    this.waveMilestones();
    if (!frozen) for (const hz of this.hazards) this.updateHazard(hz, dt);
    this.hazards = this.hazards.filter((h) => h.alive);

    if (!frozen) {
      DMG.src = "other";
      const ectx = { fx: this.fx, player: p, projectiles: this.enemyProjectiles, enemies: this.enemies, W: this.W, H: this.H, kill: (e: Enemy) => this.onEnemyKilled(e as Target) };
      for (let i = 0; i < this.enemies.length; i++) this.enemies[i].update(dt, ectx);
      this.separateEnemies();
    }
    this.enemies = this.enemies.filter((e) => e.alive);
    if (!frozen) {
      this.repositionStragglers(dt);
      this.updateCamping(dt);
    }
    this.rebuildTargets();
    this.updateChests(dt);
    this.updateKeys(dt);
    updateTimedWeapons(this, dt);
    updatePassiveWeapons(this, dt);
    for (const o of this.wobjs) {
      DMG.src = o.src;
      o.update(dt, this);
    }
    DMG.src = "other";
    this.wobjs = this.wobjs.filter((o) => o.alive);
    this.updateBigDrops(dt);
    this.updateEnemyProjectiles(dt, frozen);
    this.updatePlayerProjectiles(dt);
    this.updatePickups(dt);

    if (this.recordFlash >= 0) {
      this.recordFlash += dt;
      if (this.recordFlash > 2.6) this.recordFlash = -1;
    }
    if (!this.recordBeaten && this.bestAtStart > 0 && this.score > this.bestAtStart) {
      this.recordBeaten = true;
      this.recordFlash = 0;
      this.fx.flash(GOLD, 0.25);
      this.fx.ring(p.x, p.y, GOLD, 30, 320, 0.8, 4);
      sfx("levelup", 1);
      this.onEvent("record");
    }
    const changed = this.waves.update(frozen ? 0 : dt, this.enemies, (w) => this.waveHpMult(w), this.waves.bossActive);
    if (changed) {
      sfx("wave", 0.6);
      this.onEvent("wave", this.waves.wave);
      if (this.waves.wave % 5 === 0) {
        const a = ({ 5: "wave5", 10: "wave10", 15: "wave15", 20: "wave20", 25: "wave25" } as Record<number, string>)[this.waves.wave];
        if (a && this.biome !== "hell") this.meta.unlockAch(a);
      }
      if (this.diff === "nightmare" && this.totalWave() >= 10) this.meta.unlockAch("nightmare");
      if (!this.waves.bossPending && !this.waves.bossActive && B.miniBossWave(this.waves.wave)) this.spawnMiniBoss();
      this.rollGoblin();
    }
    if (this.coinsEarned >= 1500) this.meta.unlockAch("rich");
    if (p.dash_count >= 40) this.meta.unlockAch("dasher");

    if (this.hellPortal) {
      this.hellPortal.update(dt);
      if (p.alive && this.hellPortal.inRange(p) && inp.use) this.enterHell();
    }
    this.combo.update(dt);
    this.fx.update(dt);
    if (!p.alive && !this.gameOver) {
      this.deathCause = p.last_hit_by;
      this.gameOver = true;
      sfx("gameover", 1);
      haptic("error");
      this.onEvent("death");
    }
  }

  musicName() {
    if (this.biome === "hell") return "hell";
    return ({ stone: "arena", frost: "frost", jungle: "jungle", desert: "desert" } as Record<string, string>)[this.theme] || "arena";
  }

  private rollGoblin() {
    if (this.waves.wave < C.GOBLIN_MIN_WAVE || this.biome === "hell") return;
    if (Math.random() >= C.GOBLIN_CHANCE) return;
    const [x, y] = this.nearCameraPoint(80);
    const g = new Enemy("goblin", x, y, this.waveHpMult(this.waves.wave), 1, this.waves.wave, null, this.biome);
    (g as any).goblinLife = C.GOBLIN_LIFE;
    this.enemies.push(g);
    this.fx.popup(this.player.x, this.player.y - 100, t("fx.goblin"), C.GOBLIN_COLOR, 22, 2.2, true);
    sfx("coin", 0.8);
  }

  /** Yaratıkların birbirinin içine girmesini hafifçe engeller (kalabalık okunsun). */
  private separateEnemies() {
    const es = this.enemies;
    const n = es.length;
    if (n < 2) return;
    // kaba ızgara
    const cell = 48;
    const grid = new Map<number, number[]>();
    for (let i = 0; i < n; i++) {
      const e = es[i];
      const k = ((e.x / cell) | 0) * 4096 + ((e.y / cell) | 0);
      let arr = grid.get(k);
      if (!arr) grid.set(k, (arr = []));
      arr.push(i);
    }
    for (let i = 0; i < n; i++) {
      const e = es[i];
      if (!e.alive || e.guardOf) continue;
      const cx = (e.x / cell) | 0, cy = (e.y / cell) | 0;
      for (let gx = cx - 1; gx <= cx + 1; gx++)
        for (let gy = cy - 1; gy <= cy + 1; gy++) {
          const arr = grid.get(gx * 4096 + gy);
          if (!arr) continue;
          for (const j of arr) {
            if (j <= i) continue;
            const o = es[j];
            const dx = o.x - e.x, dy = o.y - e.y;
            const rr = (e.hit_r + o.hit_r) * 0.82;
            const d2 = dx * dx + dy * dy;
            if (d2 >= rr * rr || d2 < 1e-4) continue;
            const d = Math.sqrt(d2);
            const push = (rr - d) * 0.35;
            const ux = dx / d, uy = dy / d;
            e.x -= ux * push;
            e.y -= uy * push;
            o.x += ux * push;
            o.y += uy * push;
          }
        }
    }
  }

  autoAimTarget(): Target | null {
    const p = this.player;
    let best: Target | null = null, bs = 1e18;
    const maxD = 520;
    for (const e of this.targets) {
      if (!e.alive || e.phased) continue;
      if (e.isBoss && (e as Boss).isHidden()) continue;
      const dx = e.x - p.x, dy = e.y - p.y;
      const d2 = dx * dx + dy * dy;
      if (d2 > maxD * maxD) continue;
      // yakın olan + tehlikeli olan (patron, elit) önce
      let s = d2;
      if (e.isBoss) s *= 0.6;
      if (e.kind === "kamikaze" || e.kind === "healer" || e.kind === "wizard") s *= 0.7;
      if (s < bs) {
        bs = s;
        best = e;
      }
    }
    return best;
  }

  private updateHazard(hz: Hazard, dt: number) {
    if (!hz.exploded) {
      hz.t += dt;
      if (hz.t >= hz.delay) {
        hz.exploded = true;
        hz.linger = 0.3;
        const p = this.player;
        if (p.alive && dist(hz.x, hz.y, p.x, p.y) < hz.r + p.radius - 2) {
          if (hz.owner && hz.owner.hitPlayer) hz.owner.hitPlayer(p, hz.dmg, this.fx, hz.x, hz.y);
          else p.takeDamage(hz.dmg, this.fx, hz.x, hz.y, t("src.trap"));
        }
        this.fx.shockwave(hz.x, hz.y, hz.r * 1.15, hz.color, 0.4, 6);
        this.fx.burst(hz.x, hz.y, lighten(hz.color, 0.25), 14, 200, 0.5, 3.5);
        this.fx.shake(3, 0.15);
        sfx("explosion", 0.4);
      }
    } else {
      hz.linger -= dt;
      if (hz.linger <= 0) hz.alive = false;
    }
  }

  private waveMilestones() {
    const p = this.player;
    const w = this.waves.wave;
    p.armor_pierce = B.enemyArmorPierce(w, this.biome);
    const seen = this.milestones;
    let msg: [string, RGB] | null = null;
    if (this.biome !== "hell") {
      if (w > C.PIERCE_FROM && !seen.has("pierce")) {
        seen.add("pierce");
        msg = ["th.pierce", [255, 170, 120]];
      } else if (w >= C.KAMIKAZE_WAVE && !seen.has("kamikaze")) {
        seen.add("kamikaze");
        msg = ["th.kamikaze", ENEMY_COLORS.kamikaze];
      } else if (w > C.RAGE_FROM && !seen.has("rage")) {
        seen.add("rage");
        msg = ["th.rage", C.RAGE_FIRE];
      } else if (w >= C.MUTANT_FROM && !seen.has("mutant")) {
        seen.add("mutant");
        msg = ["th.mutant", [200, 255, 190]];
      }
    } else if (!seen.has("hell_pierce")) {
      seen.add("hell_pierce");
      msg = ["th.hell_pierce", [255, 120, 90]];
    } else if (w + C.HELL_WAVE_OFFSET >= C.MUTANT_FROM && !seen.has("mutant")) {
      seen.add("mutant");
      msg = ["th.mutant", [200, 255, 190]];
    }
    if (msg && p.alive) {
      this.onEvent("toast", { text: t(msg[0]), color: msg[1] });
      sfx("warn", 0.5);
    }
  }

  private updateChests(dt: number) {
    for (const ch of this.chests) {
      ch.update(dt, this.player);
      if (ch.opened && !ch.taken) {
        ch.taken = true;
        this.grantWeapon(ch);
      }
    }
    this.chests = this.chests.filter((c) => c.alive);
  }

  private updateBigDrops(dt: number) {
    const p = this.player;
    for (const d of this.bigDrops) {
      d.update(dt, p);
      if (!d.collected) continue;
      if (d.kind === "magnet") {
        let n = 0;
        for (const pu of this.pickups) {
          if ((pu.kind === "coin" || pu.kind === "xp") && !pu.magnet) {
            pu.magnet = true;
            pu.spawnT = Math.max(pu.spawnT, 0.2);
            n++;
          }
        }
        this.magnetsTaken++;
        this.fx.popup(p.x, p.y - 74, t("fx.magnet"), MAGNET_COLOR, 30, 1.8, true);
        this.fx.flash(MAGNET_COLOR, 0.35);
        for (let i = 0; i < 3; i++) this.fx.shockwave(p.x, p.y, 240 + i * 220, i % 2 ? MAGNET_COLOR2 : MAGNET_COLOR, 0.55 + i * 0.15, 5);
        sfx("magnet", 1);
        haptic("medium");
        void n;
      } else {
        p.level++;
        p.xp_to_next = B.xpNextNeed(p.xp_to_next, p.level);
        p.onLevelUp(1);
        this.pendingLevelups++;
        this.fx.popup(p.x, p.y - 74, t("fx.level_stone"), LEVEL_COLOR, 30, 1.8, true);
        this.fx.flash(LEVEL_COLOR, 0.35);
        for (let i = 0; i < 2; i++) this.fx.shockwave(p.x, p.y, 240 + i * 220, i % 2 ? LEVEL_COLOR2 : LEVEL_COLOR, 0.55 + i * 0.15, 5);
        sfx("levelup", 1);
        haptic("medium");
        if (p.level >= 10) this.meta.unlockAch("lvl10");
      }
    }
    this.bigDrops = this.bigDrops.filter((d) => d.alive);
  }

  private updateEnemyProjectiles(dt: number, frozen: boolean) {
    const p = this.player;
    for (const pr of this.enemyProjectiles) {
      if (!frozen) pr.update(dt, this.W, this.H);
      if (!pr.alive || !p.alive || frozen) continue;
      if (blockWithBook(this, pr)) continue;
      const rr = pr.r + p.radius;
      const dx = pr.x - p.x, dy = pr.y - p.y;
      if (dx * dx + dy * dy < rr * rr) {
        if (pr.owner && pr.owner.hitPlayer) pr.owner.hitPlayer(p, pr.dmg, this.fx, pr.x, pr.y);
        else {
          p.takeDamage(pr.dmg, this.fx, pr.x, pr.y, t("src.projectile"));
          if (pr.poison > 0) p.applyPoison(pr.poison, C.WIZARD_POISON_TIME, t("en.wizard"));
        }
        pr.alive = false;
      }
    }
    this.enemyProjectiles = this.enemyProjectiles.filter((pr) => pr.alive);
  }

  private updatePlayerProjectiles(dt: number) {
    const p = this.player;
    for (const pr of this.playerProjectiles) {
      if (pr.homing > 0 && pr.alive) {
        let nearest: Target | null = null, nd = 1e18;
        for (const e of this.targets) {
          if (!e.alive) continue;
          const d = (pr.x - e.x) ** 2 + (pr.y - e.y) ** 2;
          if (d < nd) {
            nd = d;
            nearest = e;
          }
        }
        if (nearest) pr.steerToward(nearest.x, nearest.y, dt);
      }
      pr.update(dt, this.W, this.H);
      if (!pr.alive) continue;
      DMG.src = pr.wsrc || "gun";
      for (const e of this.targets) {
        if (!e.alive || pr.hitSet.has(e.id) || e.phased) continue;
        const rr = pr.r + e.hit_r + Math.max(3, pr.r * 0.35);
        const dx = pr.x - e.x, dy = pr.y - e.y;
        if (dx * dx + dy * dy >= rr * rr) continue;
        pr.hitSet.add(e.id);
        const crit = Math.random() < pr.critChance;
        if (crit) p.run_crits++;
        let dmg = pr.dmg * (crit ? pr.critMult : 1);
        if (p.boss_hunter > 0 && (e.isBoss || e.kind === "elite")) dmg *= 1 + p.bossHunterBonus();
        dmg = this.applyExecute(e, dmg);
        const [kx, ky] = normDir(p.x, p.y, e.x, e.y);
        const kb = e.isBoss ? 12 : 90;
        const died = e.takeDamage(dmg, crit, this.fx, kx * kb, ky * kb);
        if (p.fire_level > 0) e.applyBurn(4 * p.fire_level, 2.2 + p.fire_level * 0.5);
        if (p.holy_flame > 0) e.applyBurn(18 * p.holy_flame, 3 + p.holy_flame * 0.6);
        if (p.ice_level > 0) e.applySlow(Math.max(0.3, 1 - 0.18 * p.ice_level), 1.4 + p.ice_level * 0.3);
        if (p.poison_level > 0) e.applyPoison(3 * p.poison_level);
        if (p.vamp_level > 0) p.lifesteal(dmg * 0.02 * p.vamp_level);
        this.fx.burst((pr.x + e.x) / 2, (pr.y + e.y) / 2, crit ? [255, 230, 150] : pr.color, 3, 90, 0.22, 2.2);
        if (died) {
          this.onEnemyKilled(e);
          this.explosionSplash(e.x, e.y, pr.dmg, e.id);
        }
        if (--pr.hitsLeft <= 0) {
          pr.alive = false;
          break;
        }
      }
    }
    DMG.src = "other";
    this.playerProjectiles = this.playerProjectiles.filter((pr) => pr.alive);
  }

  private updatePickups(dt: number) {
    const p = this.player;
    let coinSnd = false;
    for (const pu of this.pickups) {
      pu.update(dt, p);
      if (!pu.collected) continue;
      if (pu.kind === "xp") {
        const lv = p.gainXp(pu.value);
        if (lv > 0) {
          this.pendingLevelups += lv;
          this.fx.ring(p.x, p.y, GOLD, 18, 200, 0.5, 3);
          sfx("levelup", 1);
          haptic("success");
          if (p.level >= 10) this.meta.unlockAch("lvl10");
        } else sfx("xp", 0.3);
      } else if (pu.kind === "heart") {
        p.heal(pu.value);
        this.fx.popup(pu.x, pu.y - 10, `+${pu.value}`, [255, 120, 140], 15, 0.5, true);
        sfx("heart", 0.7);
      } else {
        this.addGold(pu.value);
        coinSnd = true;
      }
    }
    if (coinSnd) sfx("coin", 0.35, 0.08);
    this.pickups = this.pickups.filter((pu) => !(pu.collected || pu.dead));
  }

  /** Koşu bitince kalıcı istatistiklere yazılacak özet. */
  summary() {
    const p = this.player;
    const gems = Math.floor(this.gemCoins * C.RUN_GEM_RATE * p.gem_mult);
    return {
      score: this.score,
      kills: this.kills,
      wave: this.totalWave(),
      time: this.runTime,
      level: p.level,
      gold: this.coinsEarned,
      gems,
      combo: this.combo.best,
      bosses: this.bossesKilled,
      chests: this.chestsOpened,
      biome: this.biome,
      theme: this.theme,
      diff: this.diff,
      skin: p.skin.id,
      weapons: { ...p.weapons },
      books: { ...p.books },
      dmgLog: { ...this.dmgLog },
      shots: p.run_shots,
      crits: p.run_crits,
      bonks: p.run_bonks,
      bonkHits: this.bonkHits,
      dashes: p.dash_count,
      healed: p.run_healed,
      lifesteal: p.run_lifesteal,
      keys: this.runKeys,
      legend: this.legendOpened,
      goblins: this.goblinsCaught,
      snakes: this.snakesKilled,
      shopLevels: { ...p.shop_levels },
      deathCause: this.deathCause,
      record: this.recordBeaten,
    };
  }
}

/** Oyuncunun patrona karşı kaba DPS tahmini (Python estimated_dps). */
export function estimatedDps(p: Player) {
  const shots = 1 + p.multishot_level;
  const cd = Math.max(0.05, p.effAtkCd());
  const crit = 1 + p.effCritChance() * (p.effCritDmg() - 1);
  const dmg = p.effDmg();
  let dps = (dmg * shots * crit) / cd;
  let extra = 1 + 0.25 * p.echo_level + 0.03 * p.chain_level + 0.04 * p.storm_level + 0.03 * p.orbit_level + 0.04 * p.fire_level + 0.05 * p.poison_level;
  dps *= extra;
  dps += (dmg * 2 * p.bonk_mult) / Math.max(1, p.effBonkCd());
  const SHARE: Record<string, number> = {
    axe: 0.85, whip: 0.55, emanet: 0.8, book: 0.3, pentagram: 0.45, zemzem: 0.3, shoe: 0.3, frost: 0.2, tornado: 0.25, cloak: 0,
    ghost_swords: 0.7, wolves: 0.8, tesla: 0.55, meteor: 0.45, beam: 0.4, hawk: 0.85, bats: 0.45, nova: 0.35, knives: 0.55, quake: 0.4,
  };
  const PIECES: Record<string, number> = { axe: 999, whip: 2, book: 1 };
  for (const [key, lvl] of Object.entries(p.weapons)) {
    const w = WEAPON_BY_KEY[key];
    if (!w || lvl <= 0 || w.dmg <= 0) continue;
    const hit = p.weaponDamage(key, lvl);
    let n = ["axe", "whip", "book"].includes(key) ? B.weaponCount(lvl, key) : 1;
    if (PIECES[key]) n = Math.min(n, PIECES[key]);
    let per: number;
    if (key === "ghost_swords") per = (hit * 2 * B.ghostCount(lvl)) / (B.ghostCd(lvl) + 0.5);
    else if (key === "wolves") per = (hit * B.wolfCount(lvl)) / B.wolfBiteCd(lvl);
    else if (key === "hawk") per = (hit * B.hawkCount(lvl)) / (B.hawkCd(lvl) + 0.6);
    else if (key === "knives") per = (hit * Math.min(2, B.knifeCount(lvl))) / Math.max(0.2, B.weaponCooldown(w, lvl));
    else if (key === "beam") per = (hit * B.beamCount(lvl)) / Math.max(0.2, B.weaponCooldown(w, lvl));
    else if (w.passive) per = hit * (key === "book" ? 6 : 1) * n;
    else per = (hit * n) / Math.max(0.2, B.weaponCooldown(w, lvl));
    dps += per * (SHARE[key] ?? 0.4);
  }
  return Math.max(1, dps);
}

export { BOOK_BY_KEY };
