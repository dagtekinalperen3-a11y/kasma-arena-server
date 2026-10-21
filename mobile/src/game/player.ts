/**
 * Oyuncu — Python `Player` sınıfının karşılığı. Alan adları bilerek Python
 * ile aynı (snake_case): skinlerin / eşyaların perk tabloları alanları adla
 * yazıyor (perk_add: {"base_speed": 10} gibi).
 */
import { clamp, normDir, stackBonus, RGB } from "../core/util";
import * as B from "./balance";
import { GD, SkinDef, UltDef, getSkin, SKIN_ULTS, BOOK_BY_KEY, WEAPON_BY_KEY } from "./data";
import type { FX } from "./fx";
import { sfx } from "../core/audio";
import { haptic } from "../core/native";
import { t } from "../core/i18n";

const C = GD;

export interface MasterySource {
  masteryBonus(key: string): number;
}

export class Player {
  [k: string]: any;
  skin: SkinDef;
  color: RGB;
  x = B.WORLD_W / 2;
  y = B.WORLD_H / 2;
  radius = 16;
  vx = 0;
  vy = 0;
  kbx = 0;
  kby = 0;

  base_speed = B.BASE_SPEED;
  base_max_hp = B.BASE_MAX_HP;
  base_dmg = B.BASE_DMG;
  base_atk_cd = B.BASE_ATK_CD;
  base_pickup = B.BASE_PICKUP;
  base_armor = 0;
  base_regen = 0;
  coin_mult = 1;
  xp_mult = 1;
  gem_mult = 1;
  crit_chance = 0.05;
  crit_dmg_mult = 1.6;
  bonk_mult = 1;
  bonk_radius_mult = 1;
  luck = 0;
  luck_per_level = 0;

  run_dmg_mult = 1;
  run_spd_mult = 1;
  run_aspd_mult = 1;
  run_pickup_mult = 1;
  run_armor_bonus = 0;
  run_coin_mult = 1;
  run_xp_mult = 1;
  run_regen_bonus = 0;
  run_crit_bonus = 0;
  run_critdmg_bonus = 0;
  run_luck_bonus = 0;
  book_totals: Record<string, number> = {};
  weapon_speed_bonus = 0;
  regen_mult = 1;
  wound = 0;
  evade_pts = 0;
  clover_level = 0;
  weapon_boost: Record<string, number> = {};
  dmg_taken_mult = 1;
  enemy_hp_curse = 0;
  dash_cd_mult = 1;
  dash_dist_mult = 1;
  bonk_cd_mult = 1;
  proj_speed_mult = 1;
  shop_luck_raw = 0;
  shop_xp_raw = 0;

  fire_level = 0;
  ice_level = 0;
  poison_level = 0;
  kill_heal = 0;
  kill_heal_level = 0;
  rage_level = 0;
  lowhp_armor = 0;
  dash_slow_level = 0;
  boss_hunter = 0;
  swarm_level = 0;
  echo_level = 0;
  echo_count = 0;
  roar_level = 0;
  run_healed = 0;
  run_crits = 0;
  run_bonks = 0;
  run_shots = 0;
  run_lifesteal = 0;
  multishot_level = 0;
  pierce_bonus = 0;
  shield_charges = 0;
  explosive_level = 0;
  vamp_level = 0;
  _vamp_spent = 0;
  thorns_level = 0;
  chain_level = 0;
  homing_level = 0;
  frenzy_level = 0;
  frenzy_stacks = 0;
  frenzy_timer = 0;
  second_wind_charges = 0;
  holy_flame = 0;
  soul_harvest = 0;
  soul_stacks = 0;
  soul_timer = 0;
  angel_wing = 0;
  purgatory_level = 0;
  purgatory_timer = 0;
  execute_threshold = 0;
  orbit_level = 0;
  orbit_angle = 0;
  storm_level = 0;
  storm_timer = 2;
  shop_levels: Record<string, number> = {};
  weapons: Record<string, number> = {};
  weapon_timers: Record<string, number> = {};
  books: Record<string, number> = {};
  book_angle = 0;
  book_charges: number[] = [];
  penta_angle = 0;
  penta_tick = 0;
  shoe_last: [number, number] | null = null;
  shoe_idle = 0;
  frost_last: [number, number] | null = null;
  frost_idle = 0;
  invis_t = 0;
  cloak_timer = 0;

  ult: UltDef | null;
  ult_cd: number;
  ult_timer: number;
  ult_trigger: string | null = null;
  ult_fx_t = 0;
  temp_buffs: [number, Record<string, number>][] = [];
  armor_pierce = 0;
  crit_forced = 0;
  extra_orbit = 0;
  thorn_field_t = 0;
  thorn_field_r = 0;
  thorn_field_tick = 0;
  skin_power = 0;
  skin_aspd = 0;
  regen_pct = 0;
  skin_growth: Record<string, number> = {};
  bonk_cd = B.BASE_BONK_CD;
  titan_smash = 0;
  smash_timer = 0;
  _skin_every_base: Record<string, number> = {};

  max_hp: number;
  hp: number;
  level = 1;
  xp = 0;
  xp_to_next = B.XP_BASE_NEED;
  atk_timer = 0;
  bonk_timer = 0;
  dash_cd_timer = 0;
  dash_time = 0;
  dash_dx = 0;
  dash_dy = 0;
  dash_speed = 0;
  dash_count = 0;
  invuln = 0;
  shield_icd = 0;
  hit_flash = 0;
  hurt_vig = 0;
  recoil = 0;
  flash_t = 0;
  move_in: [number, number] = [0, 0];
  aim_dir: [number, number] = [1, 0];
  move_anim = 0;
  speed_now = 0;
  alive = true;
  regen_acc = 0;
  burn_t = 0;
  burn_dps = 0;
  burn_acc = 0;
  poison_t = 0;
  poison_dps = 0;
  poison_acc = 0;
  slow_t = 0;
  slow_mult = 1;
  ghosts: [number, number, number][] = [];
  ghost_t = 0;
  last_hit_by = "";
  max_weapons = B.MAX_RUN_WEAPONS;
  max_books = B.MAX_RUN_BOOKS;
  max_rare = B.MAX_RUN_RARE_BOOKS;
  onDash: (() => void) | null = null;

  constructor(skinId: string, mastery: MasterySource | null, cosmeticPerks: Record<string, number>[] = []) {
    this.skin = getSkin(skinId);
    this.color = this.skin.color as RGB;
    for (const [a, d] of Object.entries(this.skin.perk_add || {})) this[a] = (this[a] || 0) + d;
    for (const [a, v] of Object.entries(this.skin.perk_set || {})) this[a] = v;
    for (const a of Object.keys(this.skin.perk_every || {})) this._skin_every_base[a] = Math.floor(this[a] || 0);
    if (mastery) {
      this.base_dmg *= 1 + mastery.masteryBonus("m_dmg");
      this.base_max_hp += mastery.masteryBonus("m_hp");
      this.base_armor = Math.min(0.55, this.base_armor + mastery.masteryBonus("m_armor"));
      this.base_speed *= 1 + mastery.masteryBonus("m_speed");
      this.gem_mult = 1 + mastery.masteryBonus("m_gem");
      this.xp_mult *= 1 + mastery.masteryBonus("m_xp");
      this.luck += mastery.masteryBonus("m_luck");
    }
    for (const pa of cosmeticPerks) for (const [a, d] of Object.entries(pa)) this[a] = (this[a] || 0) + d;
    this.ult = SKIN_ULTS[this.skin.id] || null;
    this.ult_cd = this.ult ? this.ult.cd : 0;
    this.ult_timer = this.ult_cd;
    this.max_hp = this.base_max_hp;
    this.hp = this.max_hp;
  }

  // ---- türetilmiş statlar ----
  tempSpeedBonus() {
    let s = 0;
    for (const b of this.temp_buffs) s += b[1].run_spd_mult || 0;
    return s;
  }
  runSpeedMult(add = 0) {
    const tmp = this.tempSpeedBonus();
    const m = (this.run_spd_mult - tmp + add) * (1 + 0.05 * this.frenzy_stacks);
    return B.softSpeedMult(m) + tmp;
  }
  effSpeed() {
    let sp = this.base_speed * this.runSpeedMult();
    if (this.slow_t > 0) sp *= this.slow_mult;
    return sp;
  }
  effDmg() {
    let d = this.base_dmg * this.run_dmg_mult * (1 + 0.07 * this.frenzy_stacks) * (1 + this.skin_power);
    if (this.soul_stacks > 0) d *= 1 + 0.04 * this.soul_stacks;
    if (this.rage_level > 0 && this.max_hp > 0 && this.hp < this.max_hp * 0.5) d *= 1 + this.rageBonus();
    if (this.invis_t > 0) d *= 1 + B.cloakAmbushBonus(this.weapons.cloak || 0);
    return d;
  }
  effAtkCd() {
    return Math.max(0.07, this.base_atk_cd / (this.run_aspd_mult * (1 + this.skin_aspd)));
  }
  effPickup() {
    return this.base_pickup * this.run_pickup_mult;
  }
  effArmor() {
    return clamp(this.base_armor + this.run_armor_bonus, 0, 0.6);
  }
  lowhpActive() {
    return this.lowhp_armor > 0 && this.max_hp > 0 && this.hp < this.max_hp * C.LASTHOPE_HP_FRAC;
  }
  lowhpFactor() {
    return this.lowhpActive() ? Math.max(0.4, 1 - this.lowhp_armor) : 1;
  }
  killHealAmount() {
    return this.kill_heal_level <= 0 ? 0 : Math.max(4, this.max_hp * 0.03);
  }
  effEvasion() {
    return stackBonus(C.EVADE_PER, this.evade_pts, C.EVADE_SOFT);
  }
  magBookBonus(pts?: number) {
    return stackBonus(0.58, pts ?? this.book_totals.mag ?? 0, 2.0);
  }
  bossHunterBonus() {
    return stackBonus(0.385, this.boss_hunter, 3.5);
  }
  swarmBonus() {
    return stackBonus(0.3, this.swarm_level, 3.0);
  }
  rageBonus() {
    return stackBonus(0.47, this.rage_level, 3.0);
  }
  bookLevel(k: string) {
    return this.books[k] || 0;
  }
  normalBookCount() {
    return Object.keys(this.books).filter((k) => !BOOK_BY_KEY[k]?.rare).length;
  }
  rareBookCount() {
    return Object.keys(this.books).filter((k) => BOOK_BY_KEY[k]?.rare).length;
  }
  effRegen() {
    let r = this.base_regen + this.run_regen_bonus + this.max_hp * this.regen_pct;
    if (this.lowhpActive()) r += C.LASTHOPE_REGEN;
    return r * this.regen_mult;
  }
  effCoinMult() {
    return this.coin_mult * this.run_coin_mult;
  }
  effXpMult() {
    return this.xp_mult * this.run_xp_mult;
  }
  effCritChance() {
    if (this.crit_forced > 0) return 1;
    return clamp(this.crit_chance + this.run_crit_bonus, 0, 0.9);
  }
  effCritDmg() {
    return this.crit_dmg_mult + this.run_critdmg_bonus;
  }
  effLuck() {
    return Math.max(0, this.luck + this.run_luck_bonus);
  }
  effPierceHits() {
    return 1 + this.pierce_bonus;
  }
  effBonkRadius() {
    return 138 * this.bonk_radius_mult;
  }
  effBonkCd() {
    return Math.max(0.45, this.bonk_cd * this.bonk_cd_mult);
  }
  effDashCd() {
    return Math.max(0.7, B.BASE_DASH_CD * this.dash_cd_mult);
  }
  vampHitCap() {
    return this.max_hp * 0.25;
  }
  vampRateCap() {
    return this.max_hp * (0.04 + 0.02 * Math.max(1, this.vamp_level));
  }

  /** Kitap kartındaki "önce → sonra" satırı için statın değeri. */
  bookStatView(stat: string, add = 0): [number, "pct" | "int" | "rate"] {
    const tot = (this.book_totals[stat] || 0) + add;
    if (stat === "hp") return [this.max_hp + add, "int"];
    if (stat === "pierce") return [tot, "int"];
    if (stat === "regen") return [tot, "rate"];
    if (stat === "mag") return [this.magBookBonus(tot), "pct"];
    if (stat === "swarm") return [stackBonus(0.3, this.swarm_level + add, 3.0), "pct"];
    if (stat === "hunter") return [stackBonus(0.385, this.boss_hunter + add, 3.5), "pct"];
    if (stat === "evade") return [stackBonus(C.EVADE_PER, this.evade_pts + add, C.EVADE_SOFT), "pct"];
    if (stat === "spd") return [this.runSpeedMult(add) - 1, "pct"];
    return [tot, "pct"];
  }

  applyBookStat(stat: string, a: number) {
    switch (stat) {
      case "dmg": this.run_dmg_mult += a; break;
      case "hp": {
        const gain = Math.floor(a);
        this.max_hp += gain;
        this.hp = Math.min(this.max_hp, this.hp + gain);
        break;
      }
      case "armor": this.run_armor_bonus += a; break;
      case "spd": this.run_spd_mult += a; break;
      case "dash": this.dash_dist_mult += a; break;
      case "aspd": this.run_aspd_mult += a; break;
      case "crit": this.run_crit_bonus += a; break;
      case "critd": this.run_critdmg_bonus += a; break;
      case "regen": this.run_regen_bonus += a; break;
      case "coin": this.run_coin_mult += a; break;
      case "xp": this.run_xp_mult += a; break;
      case "mag": {
        const old = this.magBookBonus();
        this.run_pickup_mult += this.magBookBonus((this.book_totals.mag || 0) + a) - old;
        break;
      }
      case "vamp": this.vamp_level += a / 0.02; break;
      case "pierce": this.pierce_bonus += Math.floor(a); break;
      case "bonk": this.bonk_mult += a; break;
      case "bonk_r": this.bonk_radius_mult += a; break;
      case "swarm": this.swarm_level += a; break;
      case "hunter": this.boss_hunter += a; break;
      case "luck": this.run_luck_bonus += a; break;
      case "wspd": this.weapon_speed_bonus += a; break;
      case "evade": this.evade_pts += a; break;
    }
    this.book_totals[stat] = (this.book_totals[stat] || 0) + a;
  }

  static RUN_TO_SHOP_KEY: Record<string, string> = { r_pierce: "pierce", r_vamp: "vampiric" };

  applyRunUpgrade(key: string, lvl: number, tier = 0) {
    lvl = Math.max(1, lvl);
    if (B.BOOK_GAINS[key]) {
      for (const [stat, amt] of B.bookGain(key, tier, lvl)) this.applyBookStat(stat, amt);
    } else {
      switch (key) {
        case "r_poison": this.poison_level += 1; break;
        case "r_killheal": this.kill_heal_level += 1; break;
        case "r_rage": this.rage_level += 1; break;
        case "r_lasthope": this.lowhp_armor += C.LASTHOPE_DR; break;
        case "r_dashslow":
          this.dash_slow_level += 1;
          this.dash_cd_mult = Math.max(0.35, this.dash_cd_mult - 0.1);
          break;
        case "r_clover":
          this.run_luck_bonus += C.CLOVER_LUCK_ON_TAKE;
          this.clover_level += 1;
          break;
        case "r_echo": this.echo_level += 1; break;
        case "r_roar": this.roar_level += 1; break;
        case "r_hp_big":
          this.max_hp += C.DEV_BOOK_HP;
          this.hp = Math.min(this.max_hp, this.hp + C.DEV_BOOK_HP);
          this.base_speed = Math.max(60, this.base_speed - 18);
          break;
        case "r_execute": this.execute_threshold = Math.min(C.EXECUTE_MAX, this.execute_threshold + C.EXECUTE_BOOK); break;
      }
    }
    const sk = Player.RUN_TO_SHOP_KEY[key];
    if (sk) this.shop_levels[sk] = (this.shop_levels[sk] || 0) + 1;
  }

  bookMaxLevel(key: string) {
    const b = BOOK_BY_KEY[key];
    if (!b) return B.BOOK_MAX_LEVEL;
    if (b.rare) return 1;
    return b.max ?? B.BOOK_MAX_LEVEL;
  }

  takeBook(key: string, tier = 0) {
    const bk = BOOK_BY_KEY[key];
    const rare = !!bk?.rare;
    const cur = this.books[key] || 0;
    let top: number;
    if (rare) {
      if (cur > 0 || this.rareBookCount() >= this.max_rare) return 0;
      top = 1;
    } else {
      top = this.bookMaxLevel(key);
      if (cur === 0 && this.normalBookCount() >= this.max_books) return 0;
    }
    if (cur >= top) return 0;
    const nl = cur + 1;
    this.books[key] = nl;
    this.applyRunUpgrade(key, nl, tier);
    return nl;
  }

  addWeaponBoost(key: string, amount: number) {
    const cur = this.weapon_boost[key] || 0;
    const nv = Math.min(C.WEAPON_BOOST_CAP, cur + Math.max(0, amount));
    this.weapon_boost[key] = nv;
    return nv - cur;
  }

  weaponDamage(key: string, lvl: number) {
    const w = WEAPON_BY_KEY[key];
    const dpl = w.dpl ?? C.WEAPON_DMG_PER_LEVEL;
    const boost = 1 + (this.weapon_boost[key] || 0);
    return this.effDmg() * w.dmg * C.WEAPON_DMG_GLOBAL * (1 + dpl * C.WEAPON_DPL_SCALE * B.weaponGrowth(lvl)) * boost;
  }

  onLevelUp(n = 1) {
    if (n <= 0) return;
    if (this.clover_level > 0) this.run_luck_bonus += C.CLOVER_LUCK_PER_LEVEL * n;
    if (this.luck_per_level > 0) this.luck += this.luck_per_level * n;
    const sk = this.skin;
    for (const [attr, [stp, cap]] of Object.entries(sk.perk_level || {})) {
      const done = this.skin_growth[attr] || 0;
      let want = done + stp * n;
      want = cap < 0 ? Math.max(want, cap) : Math.min(want, cap);
      const delta = want - done;
      if (!delta) continue;
      this.skin_growth[attr] = want;
      if (attr === "_hp") {
        this.max_hp += delta;
        this.hp = Math.min(this.max_hp, this.hp + delta);
      } else this[attr] = (this[attr] || 0) + delta;
    }
    for (const [attr, [every, top]] of Object.entries(sk.perk_every || {})) {
      const base = this._skin_every_base[attr] || 0;
      const target = Math.min(top, base + Math.floor((this.level - 1) / Math.max(1, every)));
      if ((this[attr] || 0) < target) this[attr] = target;
    }
  }

  gainXp(amount: number) {
    amount *= this.effXpMult() * B.XP_GAIN_SCALE;
    this.xp += amount;
    let leveled = 0;
    while (this.xp >= this.xp_to_next) {
      this.xp -= this.xp_to_next;
      this.level += 1;
      this.xp_to_next = B.xpNextNeed(this.xp_to_next, this.level);
      leveled++;
    }
    this.onLevelUp(leveled);
    return leveled;
  }

  takeDamage(amount: number, fx: FX, sx?: number, sy?: number, src = "") {
    if (!this.alive || this.invuln > 0) return 0;
    if (this.shield_charges > 0) {
      if (this.shield_icd > 0) return 0;
      this.shield_charges -= 1;
      this.shield_icd = 0.35;
      fx.ring(this.x, this.y, [160, 200, 255], 14, 160, 0.3, 2.5);
      fx.shockwave(this.x, this.y, 46, [160, 200, 255], 0.25, 3);
      fx.popup(this.x, this.y - 34, t("fx.shield"), [160, 200, 255], 18, 0.6, true);
      sfx("shield", 1);
      haptic("light");
      return 0;
    }
    if (this.evade_pts > 0 && Math.random() < this.effEvasion()) {
      fx.popup(this.x, this.y - 34, t("fx.evade"), [200, 225, 255], 16, 0.5, true);
      fx.ring(this.x, this.y, [200, 225, 255], 10, 140, 0.25, 2.2);
      return 0;
    }
    const arm = this.effArmor() * (1 - clamp(this.armor_pierce, 0, 1));
    const dmg = amount * (1 - arm) * this.dmg_taken_mult * this.lowhpFactor();
    this.hp -= dmg;
    this.hit_flash = 0.3;
    this.hurt_vig = Math.min(1, this.hurt_vig + dmg / 45);
    if (src) this.last_hit_by = src;
    if (sx !== undefined && sy !== undefined) {
      const [kx, ky] = normDir(sx, sy, this.x, this.y);
      this.kbx += kx * 170;
      this.kby += ky * 170;
    }
    fx.shake(4 + Math.min(6, dmg * 0.16), 0.18);
    fx.burst(this.x, this.y, [232, 90, 100], 6, 120, 0.35, 3);
    fx.popup(this.x + (Math.random() * 20 - 10), this.y - 26, `-${Math.floor(dmg)}`, [255, 110, 120], 20, 0.7, true);
    sfx("hurt", 0.9);
    haptic(dmg > this.max_hp * 0.12 ? "medium" : "light");
    this.resolveLethal(fx);
    return dmg;
  }

  resolveLethal(fx: FX) {
    if (this.hp > 0 || !this.alive) return;
    if (this.ult && this.ult.kind === "death_defy" && this.ultReady()) {
      this.hp = 1;
      this.ult_trigger = "death_defy";
      this.startUltCooldown();
      this.invuln = Math.max(this.invuln, (this.ult.duration ?? 5) + 0.4);
      fx.flash([170, 110, 255], 0.5);
      fx.ring(this.x, this.y, [190, 120, 255], 30, 300, 0.6, 4);
      fx.popup(this.x, this.y - 48, t("ult.shadow_stance"), [200, 140, 255], 28, 1.3, true);
      sfx("second", 1);
      haptic("heavy");
      return;
    }
    if (this.purgatory_level > 0 && this.purgatory_timer <= 0) {
      this.hp = Math.max(1, this.max_hp * 0.12);
      this.purgatory_timer = Math.max(8, 25 - 5 * (this.purgatory_level - 1));
      this.invuln = Math.max(this.invuln, 1.2);
      fx.ring(this.x, this.y, [255, 215, 120], 24, 240, 0.5, 3.5);
      fx.shockwave(this.x, this.y, 170, [255, 215, 120], 0.45, 6);
      fx.popup(this.x, this.y - 44, t("fx.purgatory"), [255, 225, 150], 24, 1.1, true);
      sfx("shield", 1);
      haptic("heavy");
      return;
    }
    if (this.second_wind_charges > 0) {
      this.second_wind_charges -= 1;
      this.hp = this.max_hp * 0.5;
      this.invuln = 1.6;
      fx.ring(this.x, this.y, [232, 186, 90], 26, 260, 0.55, 4);
      fx.shockwave(this.x, this.y, 220, [232, 186, 90], 0.5, 7);
      fx.popup(this.x, this.y - 46, t("fx.second_wind"), [232, 186, 90], 26, 1.2, true);
      fx.flash([232, 186, 90], 0.6);
      sfx("second", 1);
      haptic("heavy");
      return;
    }
    this.hp = 0;
    this.alive = false;
  }

  applyBurn(dps: number, dur: number, src = "") {
    if (!this.alive) return;
    const fresh = this.burn_t <= 0;
    this.burn_dps = Math.max(this.burn_dps, dps);
    this.burn_t = Math.max(this.burn_t, dur);
    if (src) this.last_hit_by = src;
    if (fresh) sfx("hurt", 0.4);
  }
  applyPoison(dps: number, dur: number, src = "") {
    if (!this.alive) return;
    this.poison_dps = Math.max(this.poison_dps, dps);
    this.poison_t = Math.max(this.poison_t, dur);
    if (src) this.last_hit_by = src;
  }
  applySlow(mult: number, dur: number) {
    if (!this.alive) return;
    if (this.slow_t <= 0 || mult < this.slow_mult) this.slow_mult = clamp(mult, 0.25, 1);
    this.slow_t = Math.max(this.slow_t, dur);
  }
  clearStatus() {
    this.burn_t = this.poison_t = this.slow_t = 0;
    this.burn_dps = this.poison_dps = 0;
    this.slow_mult = 1;
  }
  private statusTick(amount: number, fx: FX, src: string, col: RGB) {
    if (!this.alive || amount <= 0 || this.invuln > 0) return;
    const arm = this.effArmor() * (1 - clamp(this.armor_pierce, 0, 1));
    const dmg = amount * (1 - arm) * this.dmg_taken_mult * this.lowhpFactor();
    this.hp -= dmg;
    this.last_hit_by = src;
    this.hurt_vig = Math.min(1, this.hurt_vig + dmg / 90);
    fx.popup(this.x + (Math.random() * 24 - 12), this.y - 20, `-${Math.max(1, Math.floor(dmg))}`, col, 14, 0.5, true);
    this.resolveLethal(fx);
  }
  updateStatus(dt: number, fx: FX) {
    if (this.burn_t > 0) {
      this.burn_t = Math.max(0, this.burn_t - dt);
      this.burn_acc += dt;
      while (this.burn_acc >= 0.5 && this.alive) {
        this.burn_acc -= 0.5;
        this.statusTick(this.burn_dps * 0.5, fx, t("src.fire"), [255, 150, 70]);
      }
      if (this.burn_t <= 0) this.burn_dps = 0;
    }
    if (this.poison_t > 0) {
      this.poison_t = Math.max(0, this.poison_t - dt);
      this.poison_acc += dt;
      while (this.poison_acc >= 0.5 && this.alive) {
        this.poison_acc -= 0.5;
        this.statusTick(this.poison_dps * 0.5, fx, t("src.poison"), [150, 240, 120]);
      }
      if (this.poison_t <= 0) this.poison_dps = 0;
    }
    if (this.slow_t > 0) {
      this.slow_t = Math.max(0, this.slow_t - dt);
      if (this.slow_t <= 0) this.slow_mult = 1;
    }
  }

  update(dt: number, mx: number, my: number, fx: FX, world: { w: number; h: number }) {
    if (!this.alive) return;
    for (const n of ["atk_timer", "bonk_timer", "hit_flash", "invuln", "shield_icd", "dash_cd_timer", "flash_t", "hurt_vig", "smash_timer"]) {
      const v = this[n];
      if (v > 0) this[n] = Math.max(0, v - dt);
    }
    this.recoil = Math.max(0, this.recoil - dt * 7);
    if (this._vamp_spent > 0) this._vamp_spent = Math.max(0, this._vamp_spent - this.vampRateCap() * dt);
    this.updateStatus(dt, fx);
    if (!this.alive) return;
    const ml = Math.hypot(mx, my);
    if (ml > 1) {
      mx /= ml;
      my /= ml;
    }
    if (ml > 0.05) this.move_anim += dt * 10 * Math.min(1, ml);
    this.move_in = [mx, my];
    if (this.dash_time > 0) {
      this.dash_time -= dt;
      this.x += this.dash_dx * this.dash_speed * dt;
      this.y += this.dash_dy * this.dash_speed * dt;
      this.speed_now = this.dash_speed;
      this.ghost_t -= dt;
      if (this.ghost_t <= 0) {
        this.ghost_t = 0.03;
        this.ghosts.push([this.x, this.y, 0.3]);
      }
      fx.spark(this.x, this.y, this.skin.accent, Math.random() * 80 - 40, Math.random() * 80 - 40, 0.3, 3);
    } else {
      const sp = this.effSpeed();
      const k = Math.min(1, dt * 16);
      this.vx += (mx * sp - this.vx) * k;
      this.vy += (my * sp - this.vy) * k;
      this.x += this.vx * dt;
      this.y += this.vy * dt;
      this.speed_now = Math.hypot(this.vx, this.vy);
    }
    this.x += this.kbx * dt;
    this.y += this.kby * dt;
    const d = Math.max(0, 1 - dt * 9);
    this.kbx *= d;
    this.kby *= d;
    this.x = clamp(this.x, this.radius, world.w - this.radius);
    this.y = clamp(this.y, this.radius, world.h - this.radius);
    for (const g of this.ghosts) g[2] -= dt;
    if (this.ghosts.length && this.ghosts[0][2] <= 0) this.ghosts = this.ghosts.filter((g) => g[2] > 0);

    if (this.ult) {
      if (this.ult_timer > 0) this.ult_timer = Math.max(0, this.ult_timer - dt);
      this.ult_fx_t = Math.max(0, this.ult_fx_t - dt);
    }
    if (this.temp_buffs.length) {
      const still: [number, Record<string, number>][] = [];
      for (const buf of this.temp_buffs) {
        buf[0] -= dt;
        if (buf[0] > 0) still.push(buf);
        else for (const [a, dl] of Object.entries(buf[1])) this[a] = (this[a] || 0) - dl;
      }
      this.temp_buffs = still;
    }
    if (this.crit_forced > 0) this.crit_forced = Math.max(0, this.crit_forced - dt);
    if (this.purgatory_timer > 0) this.purgatory_timer = Math.max(0, this.purgatory_timer - dt);
    if (this.soul_timer > 0) {
      this.soul_timer -= dt;
      if (this.soul_timer <= 0) this.soul_stacks = 0;
    }
    if (this.frenzy_timer > 0) {
      this.frenzy_timer -= dt;
      if (this.frenzy_timer <= 0) this.frenzy_stacks = 0;
    }
    const rg = this.effRegen();
    if (rg > 0 && this.hp < this.max_hp) {
      this.regen_acc += rg * dt * (1 - this.wound);
      const heal = Math.floor(this.regen_acc);
      if (heal > 0) {
        const before = this.hp;
        this.hp = Math.min(this.max_hp, this.hp + heal);
        this.run_healed += this.hp - before;
        this.regen_acc -= heal;
      }
    }
  }

  tryDash(fx: FX) {
    if (!this.alive || this.dash_cd_timer > 0 || this.dash_time > 0) return false;
    let [mx, my] = this.move_in;
    if (Math.abs(mx) + Math.abs(my) < 0.1) [mx, my] = this.aim_dir;
    const l = Math.hypot(mx, my) || 1;
    this.dash_dx = mx / l;
    this.dash_dy = my / l;
    const dur = 0.17;
    this.dash_time = dur;
    this.dash_speed = (205 * this.dash_dist_mult) / dur;
    this.dash_cd_timer = this.effDashCd();
    this.invuln = Math.max(this.invuln, 0.26 + 0.45 * this.angel_wing);
    this.dash_count += 1;
    this.onDash?.();
    fx.burst(this.x, this.y, this.skin.accent, 10, 150, 0.3, 3);
    sfx("dash", 1);
    haptic("light");
    return true;
  }

  heal(amount: number) {
    if (amount <= 0 || !this.alive) return;
    amount *= 1 - this.wound;
    const before = this.hp;
    this.hp = Math.min(this.max_hp, this.hp + amount);
    this.run_healed += Math.max(0, this.hp - before);
  }

  addTempBuff(duration: number, attrs: Record<string, number>) {
    if (duration <= 0) return;
    for (const [a, d] of Object.entries(attrs)) this[a] = (this[a] || 0) + d;
    this.temp_buffs.push([duration, { ...attrs }]);
  }
  ultReady() {
    return !!this.ult && this.ult_timer <= 0;
  }
  startUltCooldown() {
    this.ult_timer = this.ult_cd;
    this.ult_fx_t = 0.5;
  }
  lifesteal(amount: number, capped = true) {
    if (amount <= 0 || !this.alive) return;
    if (capped) {
      amount = Math.min(amount, this.vampHitCap());
      amount = Math.min(amount, Math.max(0, this.vampRateCap() - this._vamp_spent));
      if (amount <= 0) return;
      this._vamp_spent += amount;
    }
    const before = this.hp;
    this.heal(amount);
    this.run_lifesteal += Math.max(0, this.hp - before);
  }
  registerKillForFrenzy() {
    if (this.frenzy_level > 0) {
      this.frenzy_stacks = Math.min(this.frenzy_stacks + 1, 2 + this.frenzy_level * 2);
      this.frenzy_timer = 3;
    }
  }
  setAim(dx: number, dy: number) {
    if (Math.abs(dx) > 1e-4 || Math.abs(dy) > 1e-4) this.aim_dir = [dx, dy];
  }
  tryAttack() {
    if (this.atk_timer <= 0) {
      this.atk_timer = this.effAtkCd();
      return true;
    }
    return false;
  }
  tryBonk() {
    if (this.bonk_timer <= 0) {
      this.bonk_timer = this.effBonkCd();
      this.run_bonks += 1;
      return true;
    }
    return false;
  }
}
