/**
 * Oyunun veri tabloları — Python sürümünden (tools/export_gamedata.py)
 * birebir aktarılır. Sayılar ve isimler aynı kalsın diye burada elle
 * yazılmaz, JSON'dan okunur.
 */
import G from "../data/gamedata.json";

export const GD: any = G;

export type Col = [number, number, number];

export interface WeaponDef {
  key: string;
  name: string;
  icon: string;
  color: Col;
  cd: number;
  dmg: number;
  dpl?: number;
  cdl?: number;
  passive?: boolean;
  timed?: boolean;
  max?: number;
  up: string;
  desc: string;
  how: string;
  unlock?: { text: string; reqs: Req[] };
}
export interface Req {
  kind: "stat" | "ach" | "shop" | "book" | "weapon";
  stat?: string;
  ach?: string;
  item?: string;
  book?: string;
  weapon?: string;
  need: number;
  text?: string;
  tkey?: string;
}
export interface BookDef {
  key: string;
  name: string;
  desc: string;
  color: Col;
  icon: string;
  rare: boolean;
  basic?: boolean;
  max?: number;
  unlock?: { text: string; reqs: Req[] };
}
export interface ShopItem {
  key: string;
  name: string;
  desc: string;
  cost: number;
  cost_mult: number;
  max: number;
  endless?: boolean;
  icon: string;
  color: Col;
  tier: number;
  cat: string;
  cursed?: boolean;
  legendary?: boolean;
  hell_only?: boolean;
  instant?: boolean;
}
export interface SkinDef {
  id: string;
  name: string;
  color: Col;
  accent: Col;
  cost: number | null;
  premium?: boolean;
  weapon: string;
  proj: string;
  aura: string;
  sfx: string;
  wlen: number;
  desc: string;
  perks: string[];
  perk_add?: Record<string, number>;
  perk_set?: Record<string, number>;
  perk_every?: Record<string, [number, number]>;
  perk_level?: Record<string, [number, number]>;
}
export interface UltDef {
  name: string;
  icon: string;
  color: Col;
  cd: number;
  kind: string;
  mode: string;
  n?: number;
  mult?: number;
  pierce?: number;
  radius?: number;
  duration?: number;
  freeze?: number;
  desc: string;
}
export interface EnemyDef {
  hp: number;
  speed: number;
  dmg: number;
  radius: number;
  coin: number;
  xp: number;
  score: number;
  contact_dps: number;
}
export interface VariantDef {
  name: string;
  base: string;
  shape: string;
  color: Col;
  shot?: string;
  hp?: number;
  dmg?: number;
  radius?: number;
}
export interface AchDef {
  id: string;
  name: string;
  desc: string;
  how?: string;
  tier: string;
  gems: number;
  icon?: string;
  map?: string;
  track?: { stat: string; need: number };
  [k: string]: any;
}

export const WEAPONS: WeaponDef[] = GD.BOSS_WEAPONS;
export const WEAPON_BY_KEY: Record<string, WeaponDef> = Object.fromEntries(WEAPONS.map((w) => [w.key, w]));
export const BOOKS: BookDef[] = GD.BOOKS.filter((b: BookDef) => !(GD.REMOVED_BOOKS || []).includes(b.key));
export const BOOK_BY_KEY: Record<string, BookDef> = Object.fromEntries(BOOKS.map((b) => [b.key, b]));
export const SHOP_ITEMS: ShopItem[] = GD.SHOP_ITEMS;
export const SHOP_BY_KEY: Record<string, ShopItem> = Object.fromEntries(SHOP_ITEMS.map((s) => [s.key, s]));
export const SHOP_CATS: Record<string, string> = GD.SHOP_CATS;
export const SKINS: SkinDef[] = GD.SKINS;
export const SKIN_BY_ID: Record<string, SkinDef> = Object.fromEntries(SKINS.map((s) => [s.id, s]));
export const SKIN_ULTS: Record<string, UltDef> = GD.SKIN_ULTS;
export const ENEMY_DEFS: Record<string, EnemyDef> = GD.ENEMY_DEFS;
export const ENEMY_COLORS: Record<string, Col> = GD.ENEMY_COLORS;
export const MAP_ENEMIES: Record<string, VariantDef> = GD.MAP_ENEMIES;
export const HELL_ENEMIES: Record<string, VariantDef> = GD.HELL_ENEMIES;
export const MAP_ROSTER: Record<string, Record<string, string>> = GD.MAP_ROSTER;
export const ACHIEVEMENTS: AchDef[] = [...GD.ACHIEVEMENTS, ...(GD.MAP_ACHS || []).filter((m: AchDef) => !GD.ACHIEVEMENTS.some((a: AchDef) => a.id === m.id))];
export const ACH_BY_ID: Record<string, AchDef> = Object.fromEntries(ACHIEVEMENTS.map((a) => [a.id, a]));
export const BOSS_DEFS: Record<string, { name: string; hp: number; speed: number; dmg: number; radius: number; color: Col }> =
  GD.BOSS_DEFS;
export const MASTERY: any[] = GD.MASTERY;
export const BIOME_STYLE: Record<string, any> = GD.BIOME_STYLE;

export function getSkin(id: string): SkinDef {
  return SKIN_BY_ID[id] || SKIN_BY_ID["default"];
}
