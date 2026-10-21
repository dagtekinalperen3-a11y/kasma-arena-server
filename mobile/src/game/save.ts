/**
 * Kalıcı kayıt: elmas, skinler, istatistikler, başarımlar, açılan
 * silah/kitaplar, ustalık, ayarlar, yerel rekorlar.
 */
import { storeGet, storeSet } from "../core/native";
import { stackBonus } from "../core/util";
import { GD, WEAPONS, BOOKS, ACHIEVEMENTS, ACH_BY_ID, SKIN_BY_ID, MASTERY, Req, WEAPON_BY_KEY, BOOK_BY_KEY, SkinDef } from "./data";
import type { RunMeta } from "./run";

const C = GD;
const KEY = "evolvearena_save_v1";
export const MAP_THEMES = ["stone", "frost", "jungle", "desert"];
const MAP_UNLOCK_PREV: Record<string, string> = { frost: "stone", jungle: "frost", desert: "jungle" };

export interface Settings {
  lang: string;
  sfx: number;
  music: number;
  haptics: boolean;
  shake: boolean;
  dmgNumbers: boolean;
  autoAim: boolean;
  zoom: number; // görüş alanı (kısa kenar, dünya birimi)
  quality: number; // 1 yüksek, 0 düşük
  leftHanded: boolean;
  fpsCounter: boolean;
  diff: "normal" | "hard" | "nightmare";
  lastMap: string;
  controlsHint: boolean;
}

export interface RecordRow {
  score: number;
  wave: number;
  kills: number;
  time: number;
  skin: string;
  map: string;
  diff: string;
  level: number;
  date: number;
}

export interface SaveData {
  v: number;
  gems: number;
  gemsEarned: number;
  skins: string[];
  skin: string;
  stats: Record<string, any>;
  ach: Record<string, number>;
  achSeen: string[];
  weaponsOwned: string[];
  booksOwned: string[];
  mastery: Record<string, number>;
  mutedWeapons: string[];
  mutedBooks: string[];
  records: RecordRow[];
  daily: { last: string; streak: number };
  settings: Settings;
  tutorialDone: boolean;
  installId: string;
}

function defaults(): SaveData {
  return {
    v: 1,
    gems: 0,
    gemsEarned: 0,
    skins: ["default", "ranger"],
    skin: "default",
    stats: {},
    ach: {},
    achSeen: [],
    weaponsOwned: [],
    booksOwned: BOOKS.filter((b) => b.basic).map((b) => b.key),
    mastery: {},
    mutedWeapons: [],
    mutedBooks: [],
    records: [],
    daily: { last: "", streak: 0 },
    settings: {
      lang: "",
      sfx: 0.8,
      music: 0.5,
      haptics: true,
      shake: true,
      dmgNumbers: true,
      autoAim: true,
      zoom: 440,
      quality: 1,
      leftHanded: false,
      fpsCounter: false,
      diff: "normal",
      lastMap: "stone",
      controlsHint: true,
    },
    tutorialDone: false,
    installId: Math.random().toString(36).slice(2) + Date.now().toString(36),
  };
}

export function masteryCost(m: any, lvl: number) {
  const T = C.MASTERY_TIERS;
  if (lvl < T) return Math.round(m.cost * Math.pow(m.growth, lvl));
  const son = m.cost * Math.pow(m.growth, T - 1);
  return Math.round(son * Math.pow(1.35, lvl - T + 1));
}
export function masteryBonusAt(m: any, lvl: number) {
  const T = C.MASTERY_TIERS;
  const base = m.per * Math.min(lvl, T);
  if (lvl <= T) return base;
  return base + stackBonus(m.soft, lvl - T, m.cap_soft);
}

/** Eski sürümde gerçek parayla satılan özel karakterler artık elmasla açılır
 * (mağaza kuralları: oyun içi satın alma yalnız mağazanın ödeme sistemiyle). */
const PREMIUM_GEMS: Record<string, number> = { web_master: 1500, ash_warrior: 1600, green_titan: 1800, immortal_merc: 2000 };
export function skinCost(sk: SkinDef) {
  return sk.premium ? PREMIUM_GEMS[sk.id] ?? 1800 : sk.cost || 0;
}

export class Save implements RunMeta {
  data: SaveData = defaults();
  onAch: ((id: string) => void) | null = null;
  private dirty = false;
  private timer: any = null;

  async load() {
    try {
      const raw = await storeGet(KEY);
      if (raw) {
        const d = JSON.parse(raw);
        const def = defaults();
        this.data = { ...def, ...d, settings: { ...def.settings, ...(d.settings || {}) }, daily: { ...def.daily, ...(d.daily || {}) } };
        if (!this.data.skins.includes("default")) this.data.skins.push("default");
        if (![360, 440, 540].includes(this.data.settings.zoom)) this.data.settings.zoom = 440;
      }
    } catch (e) {
      console.warn("save load", e);
    }
  }
  persist(now = false) {
    this.dirty = true;
    if (now) return this.flush();
    if (!this.timer) this.timer = setTimeout(() => this.flush(), 800);
  }
  async flush() {
    clearTimeout(this.timer);
    this.timer = null;
    if (!this.dirty) return;
    this.dirty = false;
    await storeSet(KEY, JSON.stringify(this.data));
  }

  get settings() {
    return this.data.settings;
  }

  // ---- RunMeta ----
  stat(key: string) {
    const v = this.data.stats[key];
    return typeof v === "number" ? v : 0;
  }
  addStat(key: string, n: number) {
    this.data.stats[key] = this.stat(key) + n;
    if (key === "stone_cleared") this.data.stats[key] = 1;
    this.persist();
  }
  maxStat(key: string, v: number) {
    if (v > this.stat(key)) this.data.stats[key] = v;
  }
  bestScore() {
    return this.stat("best_score");
  }
  unlockedWeapons() {
    return this.data.weaponsOwned.filter((k) => WEAPON_BY_KEY[k]);
  }
  unlockedBooks() {
    return this.data.booksOwned.filter((k) => BOOK_BY_KEY[k]);
  }
  mutedWeapons() {
    return this.data.mutedWeapons;
  }
  mutedBooks() {
    return this.data.mutedBooks;
  }
  /** Silahı / kitabı seviye kartlarından çıkarır ya da geri koyar. */
  toggleMute(kind: "w" | "b", key: string) {
    const arr = kind === "w" ? this.data.mutedWeapons : this.data.mutedBooks;
    const i = arr.indexOf(key);
    if (i >= 0) arr.splice(i, 1);
    else {
      if (arr.length >= this.muteLimit(kind)) return false;
      arr.push(key);
    }
    this.persist();
    return true;
  }
  ownsBook(k: string) {
    return this.data.booksOwned.includes(k);
  }
  masteryLevel(k: string) {
    return this.data.mastery[k] || 0;
  }
  masteryBonus(k: string) {
    const m = MASTERY.find((x) => x.key === k);
    return m ? masteryBonusAt(m, this.masteryLevel(k)) : 0;
  }
  hasAch(id: string) {
    return !!this.data.ach[id];
  }
  unlockAch(id: string) {
    if (!id || this.data.ach[id] || !ACH_BY_ID[id]) return;
    this.data.ach[id] = Date.now();
    const gems = ACH_BY_ID[id].gems || 0;
    this.addGems(gems);
    this.persist();
    this.onAch?.(id);
  }

  addGems(n: number) {
    this.data.gems = Math.max(0, this.data.gems + n);
    if (n > 0) this.data.gemsEarned += n;
    this.persist();
  }

  // ---- ustalık ----
  masteryNextCost(k: string) {
    const m = MASTERY.find((x) => x.key === k);
    return m ? masteryCost(m, this.masteryLevel(k)) : 0;
  }
  masteryMaxed(k: string) {
    const m = MASTERY.find((x) => x.key === k);
    return !!(m && m.max && this.masteryLevel(k) >= m.max);
  }
  buyMastery(k: string) {
    if (this.masteryMaxed(k)) return false;
    const c = this.masteryNextCost(k);
    if (this.data.gems < c) return false;
    this.data.gems -= c;
    this.data.mastery[k] = this.masteryLevel(k) + 1;
    this.persist(true);
    return true;
  }
  muteLimit(kind: "w" | "b") {
    return kind === "w" ? C.MAX_MUTED_WEAPONS + this.masteryLevel("m_wmute") : C.MAX_MUTED_BOOKS + this.masteryLevel("m_bmute");
  }

  // ---- skinler ----
  ownsSkin(id: string) {
    return this.data.skins.includes(id);
  }
  buySkin(id: string) {
    const sk = SKIN_BY_ID[id];
    if (!sk || this.ownsSkin(id)) return false;
    const cost = skinCost(sk);
    if (this.data.gems < cost) return false;
    this.data.gems -= cost;
    this.data.skins.push(id);
    this.data.skin = id;
    this.unlockAch("fashion");
    this.persist(true);
    return true;
  }
  equipSkin(id: string) {
    if (!this.ownsSkin(id)) return;
    this.data.skin = id;
    this.persist();
  }
  skinId() {
    return this.ownsSkin(this.data.skin) ? this.data.skin : "default";
  }

  // ---- kilitler ----
  reqState(r: Req): [number, number, boolean] {
    const need = r.need || 1;
    switch (r.kind) {
      case "ach": {
        const got = this.hasAch(r.ach!);
        const a = ACH_BY_ID[r.ach!];
        if (!got && a?.track) return [Math.min(this.stat(a.track.stat), a.track.need), a.track.need, false];
        return [got ? 1 : 0, 1, got];
      }
      case "shop": {
        const cur = (this.data.stats.shop_max || {})[r.item!] || 0;
        return [cur, need, cur >= need];
      }
      case "book": {
        const got = this.ownsBook(r.book!);
        return [got ? 1 : 0, 1, got];
      }
      case "weapon": {
        const got = this.data.weaponsOwned.includes(r.weapon!);
        return [got ? 1 : 0, 1, got];
      }
      default: {
        const cur = this.stat(r.stat!);
        return [cur, need, cur >= need];
      }
    }
  }
  reqsDone(reqs: Req[] | undefined) {
    if (!reqs || !reqs.length) return true;
    return reqs.every((r) => this.reqState(r)[2]);
  }
  reqFrac(reqs: Req[] | undefined) {
    if (!reqs || !reqs.length) return 1;
    let t = 0;
    for (const r of reqs) {
      const [cur, need, done] = this.reqState(r);
      t += done ? 1 : Math.min(1, cur / Math.max(1, need));
    }
    return t / reqs.length;
  }
  /** Şartları dolan silah / kitapları açar. Dönüş: yeni açılanlar. */
  refreshUnlocks(): { weapons: string[]; books: string[] } {
    const nw: string[] = [], nb: string[] = [];
    for (let pass = 0; pass < 3; pass++) {
      for (const w of WEAPONS) {
        if (this.data.weaponsOwned.includes(w.key)) continue;
        if (this.reqsDone(w.unlock?.reqs)) {
          this.data.weaponsOwned.push(w.key);
          nw.push(w.key);
        }
      }
      for (const b of BOOKS) {
        if (this.data.booksOwned.includes(b.key)) continue;
        if (this.reqsDone(b.unlock?.reqs)) {
          this.data.booksOwned.push(b.key);
          nb.push(b.key);
        }
      }
    }
    if (nw.length || nb.length) this.persist();
    return { weapons: nw, books: nb };
  }
  /** İstatistik takipli başarımları denetler. */
  checkStatAchs() {
    for (const a of ACHIEVEMENTS) {
      if (this.hasAch(a.id) || !a.track) continue;
      if (this.stat(a.track.stat) >= a.track.need) this.unlockAch(a.id);
    }
  }

  // ---- haritalar ----
  mapCleared(theme: string) {
    const st = this.data.stats;
    if (theme === "stone") return (st.stone_cleared || 0) > 0 || (st.best_stone_wave || 0) > 25 || (st.best_wave || 0) > 25;
    return (st[`best_${theme}_wave`] || 0) >= 25;
  }
  mapUnlocked(theme: string) {
    const prev = MAP_UNLOCK_PREV[theme];
    if (!prev) return true;
    if ((this.data.stats[`${theme}_kills`] || 0) > 0) return true;
    return this.mapCleared(prev);
  }

  // ---- koşu sonu ----
  commitRun(s: ReturnType<import("./run").Run["summary"]>, mapStats: Record<string, number>) {
    const st = this.data.stats;
    const prevBest = { score: this.stat("best_score"), wave: this.stat("best_wave") };
    st.runs = this.stat("runs") + 1;
    this.maxStat("best_score", s.score);
    st.total_kills = this.stat("total_kills") + s.kills;
    st.total_time = this.stat("total_time") + s.time;
    this.maxStat("best_wave", s.wave);
    this.maxStat("best_run_kills", s.kills);
    st.total_healed = this.stat("total_healed") + s.healed;
    this.maxStat("best_run_heal", s.healed);
    st.total_crits = this.stat("total_crits") + s.crits;
    st.total_bonks = this.stat("total_bonks") + s.bonks;
    this.maxStat("best_run_dashes", s.dashes);
    this.maxStat("best_combo", s.combo);
    st.total_shots = this.stat("total_shots") + s.shots;
    this.maxStat("best_run_shots", s.shots);
    st.total_keys = this.stat("total_keys") + s.keys;
    st.legend_chests = this.stat("legend_chests") + s.legend;
    st.total_lifesteal = this.stat("total_lifesteal") + s.lifesteal;
    st.total_gold = this.stat("total_gold") + s.gold;
    this.maxStat("best_run_gold", s.gold);
    st.total_bonk_hits = this.stat("total_bonk_hits") + s.bonkHits;
    st.total_chests = this.stat("total_chests") + s.chests;
    st.total_goblins = this.stat("total_goblins") + s.goblins;
    const sm = (st.shop_max ||= {});
    for (const [k, l] of Object.entries(s.shopLevels)) if ((l as number) > (sm[k] || 0)) sm[k] = l;
    for (const [k, v] of Object.entries(mapStats)) {
      const kind = (C.MAP_ACH_STATS[k] || [])[1];
      if (kind === "sum") st[k] = this.stat(k) + v;
      else this.maxStat(k, v);
    }
    this.maxStat(`best_${s.theme}_wave`, s.wave);
    st[`${s.theme}_kills`] = this.stat(`${s.theme}_kills`) + s.kills;
    if (s.biome === "hell") st.hell_runs = this.stat("hell_runs") + 1;
    // yerel rekorlar
    this.data.records.push({ score: s.score, wave: s.wave, kills: s.kills, time: s.time, skin: s.skin, map: s.theme, diff: s.diff, level: s.level, date: Date.now() });
    this.data.records.sort((a, b) => b.score - a.score);
    this.data.records = this.data.records.slice(0, 20);
    this.addGems(s.gems);
    this.checkStatAchs();
    const unl = this.refreshUnlocks();
    this.checkStatAchs();
    this.persist(true);
    return { prevBest, unl };
  }

  // ---- günlük hediye ----
  dailyStatus(): { can: boolean; day: number; gems: number } {
    const today = new Date().toISOString().slice(0, 10);
    const d = this.data.daily;
    const gifts: number[] = C.DAILY_GIFT_GEMS;
    if (d.last === today) return { can: false, day: d.streak, gems: gifts[Math.max(0, (d.streak - 1) % gifts.length)] };
    const y = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
    const streak = d.last === y ? d.streak + 1 : 1;
    return { can: true, day: streak, gems: gifts[(streak - 1) % gifts.length] };
  }
  claimDaily() {
    const s = this.dailyStatus();
    if (!s.can) return 0;
    this.data.daily = { last: new Date().toISOString().slice(0, 10), streak: s.day };
    this.addGems(s.gems);
    this.persist(true);
    return s.gems;
  }

  resetAll() {
    const keep = this.data.settings;
    this.data = defaults();
    this.data.settings = keep;
    this.persist(true);
  }
}
