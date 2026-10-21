/**
 * Koşu içi MARKET eşyalarının etkileri (Python apply_shop_item).
 */
import { clamp, stackBonus } from "../core/util";
import { GD } from "./data";
import { shopSoft } from "./balance";
import type { Player } from "./player";

const C = GD;

export function applyShopItem(p: Player, key: string) {
  const luck0 = p.run_luck_bonus, xp0 = p.run_xp_mult;
  applyRaw(p, key);
  const dl = p.run_luck_bonus - luck0, dx = p.run_xp_mult - xp0;
  if (dl > 0) {
    const raw = p.shop_luck_raw || 0;
    p.shop_luck_raw = raw + dl;
    p.run_luck_bonus = luck0 + (shopSoft(raw + dl, C.SHOP_LUCK_SOFT) - shopSoft(raw, C.SHOP_LUCK_SOFT));
  }
  if (dx > 0) {
    const raw = p.shop_xp_raw || 0;
    p.shop_xp_raw = raw + dx;
    p.run_xp_mult = xp0 + (shopSoft(raw + dx, C.SHOP_XP_SOFT) - shopSoft(raw, C.SHOP_XP_SOFT));
  }
}

function addHp(p: Player, n: number) {
  p.base_max_hp += n;
  p.max_hp += n;
  p.hp = Math.min(p.max_hp, p.hp + n);
}

function applyRaw(p: Player, key: string) {
  const lv = Math.max(1, p.shop_levels[key] || 1);
  switch (key) {
    case "core_power": p.run_dmg_mult += 0.08; break;
    case "core_speed": p.run_aspd_mult += 0.06; break;
    case "core_vitality": addHp(p, 30); break;
    case "core_crit":
      p.crit_chance = clamp(p.crit_chance + 0.03, 0, 0.9);
      p.crit_dmg_mult += 0.06;
      break;
    case "core_guard": p.base_armor = clamp(p.base_armor + 0.02, 0, 0.5); break;
    case "core_greed":
      p.run_coin_mult += stackBonus(0.12, lv, 4) - stackBonus(0.12, lv - 1, 4);
      p.run_xp_mult += stackBonus(0.08, lv, 4) - stackBonus(0.08, lv - 1, 4);
      break;
    case "core_reach":
      p.run_pickup_mult += 0.14;
      p.run_xp_mult += stackBonus(0.06, lv, 4) - stackBonus(0.06, lv - 1, 4);
      break;
    case "fire": p.fire_level++; break;
    case "ice": p.ice_level++; break;
    case "multishot": p.multishot_level++; break;
    case "pierce": p.pierce_bonus++; break;
    case "shield": p.shield_charges++; break;
    case "heal": p.heal(40); break;
    case "haste":
      p.run_aspd_mult += 0.09;
      p.run_spd_mult += 0.05;
      break;
    case "explosive": p.explosive_level++; break;
    case "vampiric": p.vamp_level++; break;
    case "thorns": p.thorns_level++; break;
    case "quickdraw":
      p.run_aspd_mult += 0.07;
      p.run_crit_bonus += 0.02;
      break;
    case "bandage":
      p.run_regen_bonus += 0.6;
      addHp(p, 12);
      break;
    case "lucky_coin":
      p.run_coin_mult += 0.15;
      p.run_crit_bonus += 0.02;
      p.run_luck_bonus += C.LUCKY_COIN_LUCK;
      break;
    case "core_luck":
      p.run_luck_bonus += stackBonus(C.CORE_LUCK_PER_LEVEL, lv, C.CORE_LUCK_SOFT) - stackBonus(C.CORE_LUCK_PER_LEVEL, lv - 1, C.CORE_LUCK_SOFT);
      break;
    case "gambler_dice":
      p.run_luck_bonus += C.GAMBLER_DICE_LUCK;
      p.run_spd_mult = Math.max(0.5, p.run_spd_mult - 0.05);
      break;
    case "gale_boots":
      p.run_spd_mult += 0.08;
      p.dash_dist_mult += 0.04;
      break;
    case "war_drum":
      p.bonk_mult += 0.2;
      p.bonk_radius_mult += 0.08;
      p.run_spd_mult += 0.04;
      break;
    case "iron_will":
      p.dmg_taken_mult = Math.max(0.25, p.dmg_taken_mult - 0.05);
      addHp(p, 20);
      break;
    case "frost_core":
      p.ice_level++;
      p.run_dmg_mult += 0.05;
      break;
    case "hunters_mark": p.boss_hunter++; break;
    case "sunder":
      p.execute_threshold = Math.min(C.EXECUTE_MAX, p.execute_threshold + C.EXECUTE_SUNDER);
      p.run_dmg_mult += 0.08;
      break;
    case "soul_jar":
      p.kill_heal += 2;
      p.run_xp_mult += 0.1;
      break;
    case "bulwark":
      p.shield_charges++;
      p.thorns_level++;
      break;
    case "phoenix_ash":
      p.second_wind_charges++;
      p.run_regen_bonus += 1.5;
      break;
    case "kings_ransom":
      p.run_coin_mult += 0.45;
      p.run_xp_mult += 0.2;
      break;
    case "brimstone": p.run_dmg_mult += 0.25; break;
    case "hell_ward":
      p.base_armor += 0.06;
      addHp(p, 40);
      break;
    case "holy_flame": p.holy_flame++; break;
    case "soul_harvest": p.soul_harvest++; break;
    case "angel_wing":
      p.dash_cd_mult = Math.max(0.3, p.dash_cd_mult - 0.2);
      p.angel_wing++;
      break;
    case "purgatory":
      p.purgatory_level++;
      p.purgatory_timer = 0;
      break;
    case "infernal_core":
      p.run_dmg_mult += 0.1;
      p.run_aspd_mult += 0.07;
      break;
    case "cursed_dagger":
      p.run_crit_bonus += 0.08;
      p.run_critdmg_bonus += 0.3;
      break;
    case "dragon_heart":
      addHp(p, 80);
      p.run_regen_bonus += 2;
      break;
    case "flame_orbit":
      p.orbit_level++;
      p.fire_level++;
      break;
    case "soul_lantern":
      p.run_coin_mult += 0.35;
      p.run_xp_mult += 0.25;
      p.run_pickup_mult += 0.3;
      break;
    case "doom_sigil": p.boss_hunter++; break;
    case "ember_step":
      p.run_spd_mult += 0.14;
      p.dash_cd_mult = Math.max(0.3, p.dash_cd_mult - 0.15);
      break;
    case "demon_pact":
      p.run_dmg_mult += 0.6;
      p.dmg_taken_mult += 0.2;
      break;
    case "dash_cd":
      p.dash_cd_mult = Math.max(0.35, p.dash_cd_mult - 0.18);
      p.dash_dist_mult += 0.03;
      break;
    case "blood_pact":
      p.run_dmg_mult += 0.4;
      p.max_hp = Math.max(30, Math.floor(p.max_hp * 0.75));
      p.hp = Math.min(p.hp, p.max_hp);
      break;
    case "glass":
      p.run_aspd_mult += 0.3;
      p.dmg_taken_mult += 0.25;
      break;
    case "devil":
      p.run_coin_mult += 0.2;
      p.run_xp_mult += 0.15;
      p.enemy_hp_curse += 0.12;
      break;
    case "chain": p.chain_level++; break;
    case "frenzy": p.frenzy_level++; break;
    case "second_wind": p.second_wind_charges++; break;
    case "storm": p.storm_level++; break;
    case "overcharge":
      p.bonk_mult += 0.35;
      p.bonk_radius_mult += 0.15;
      break;
    case "execute_edge": p.execute_threshold = Math.min(C.EXECUTE_MAX, p.execute_threshold + C.EXECUTE_EDGE); break;
    case "titan_shield":
      p.shield_charges += 2;
      p.base_armor = clamp(p.base_armor + 0.06, 0, 0.5);
      break;
  }
}
