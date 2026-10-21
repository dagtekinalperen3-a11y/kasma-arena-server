/**
 * Seviye atlama kartları — Python levelup_pool / start_levelup_choice /
 * choose_levelup / reroll / skip (nadirlik, şans, kader kilidi, kombo ısısı).
 */
import { mulberry32, shuffle, weightedPick, RGB } from "../core/util";
import * as B from "./balance";
import { GD, WEAPON_BY_KEY, BOOK_BY_KEY, BOOKS, WeaponDef, BookDef } from "./data";
import { sfx } from "../core/audio";
import { haptic } from "../core/native";
import { t } from "../core/i18n";
import type { Run } from "./run";

const C = GD;
const REROLL_FREE = 3, SKIP_FREE = 3, REROLL_BASE = 40, REROLL_GROWTH = 1.3, SKIP_BASE = 90, SKIP_GROWTH = 1.55;
const COMBO_SETS: [string[], number][] = [
  [["tornado", "zemzem", "r_vamp"], 0.8],
  [["tornado", "zemzem", "r_killheal"], 0.8],
  [["pentagram", "shoe", "frost"], 0.7],
  [["whip", "emanet", "r_swarm"], 0.6],
  [["axe", "r_critd", "r_crit"], 0.6],
  [["book", "cloak", "r_lasthope"], 0.65],
  [["r_rage", "r_lasthope", "r_killheal"], 0.75],
];

export interface Offer {
  kind: "weapon" | "book";
  key: string;
  lvl: number;
  isNew: boolean;
  color: RGB;
  icon: string;
  rarity?: number;
  boost?: number;
  gains?: [string, number][];
  rare?: boolean;
  max?: number;
  legend?: boolean;
  trial?: boolean;
}

const stepCost = (used: number, free: number, base: number, growth: number) => (used < free ? 0 : Math.round((base * Math.pow(growth, used - free)) / 10) * 10);

export class LevelUp {
  choices: Offer[] = [];
  rerollUsed = 0;
  skipUsed = 0;
  rerollBonus = 0;
  offerSeen: Record<string, number> = {};
  destinyLocked = new Set<string>();

  constructor(public run: Run) {
    this.rollDestiny();
  }

  private rollDestiny() {
    const rnd = mulberry32((Math.random() * 1e9) | 0);
    const sh = <T>(a: T[]) => {
      for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(rnd() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
      }
      return a;
    };
    const ri = (a: number, b: number) => a + Math.floor(rnd() * (b - a + 1));
    const m = this.run.meta;
    const wk = m.unlockedWeapons();
    if (wk.length >= 6) sh(wk).slice(0, ri(1, 2)).forEach((k) => this.destinyLocked.add(k));
    const bk = m.unlockedBooks().filter((k) => !BOOK_BY_KEY[k]?.rare);
    if (bk.length >= 8) sh(bk).slice(0, ri(1, 2)).forEach((k) => this.destinyLocked.add(k));
    const rb = m.unlockedBooks().filter((k) => BOOK_BY_KEY[k]?.rare);
    if (rb.length >= 4) sh(rb).slice(0, ri(1, 2)).forEach((k) => this.destinyLocked.add(k));
  }

  rerollCost() {
    if (this.rerollBonus > 0) return 0;
    return stepCost(this.rerollUsed, REROLL_FREE, REROLL_BASE, REROLL_GROWTH);
  }
  skipCost() {
    return stepCost(this.skipUsed, SKIP_FREE, SKIP_BASE, SKIP_GROWTH);
  }
  rerollsFree() {
    return Math.max(0, REROLL_FREE - this.rerollUsed) + this.rerollBonus;
  }
  skipsFree() {
    return Math.max(0, SKIP_FREE - this.skipUsed);
  }

  private weaponOffer(w: WeaponDef, lvl: number, isNew: boolean): Offer {
    const tier = B.rollRarity(this.run.player.effLuck());
    return { kind: "weapon", key: w.key, lvl, isNew, color: w.color, icon: w.icon, rarity: tier, boost: B.rarityBoost(tier, "card") };
  }
  private bookOffer(bk: BookDef, lvl: number, isNew: boolean): Offer {
    const rare = !!bk.rare;
    const o: Offer = { kind: "book", key: bk.key, lvl, isNew, color: bk.color, icon: bk.icon || "star", rare, max: this.run.player.bookMaxLevel(bk.key) };
    if (!rare && B.BOOK_GAINS[bk.key]) {
      const tier = B.rollRarity(this.run.player.effLuck());
      o.rarity = tier;
      o.gains = B.bookGain(bk.key, tier, lvl);
    }
    return o;
  }
  private comboDamp(key: string) {
    const p = this.run.player;
    const owned = new Set([...Object.keys(p.weapons), ...Object.keys(p.books)]);
    let damp = 1;
    for (const [parts, str] of COMBO_SETS) {
      if (!parts.includes(key) || owned.has(key)) continue;
      const have = parts.filter((k) => owned.has(k)).length;
      if (have <= 0) continue;
      const f = parts.length > 1 ? have / (parts.length - 1) : 1;
      damp *= Math.max(0.18, 1 - str * Math.min(1, f));
    }
    return damp;
  }
  private metaWeight(key: string, base: number) {
    if (this.destinyLocked.has(key)) return 0;
    let w = base * this.comboDamp(key);
    const seen = this.offerSeen[key] || 0;
    if (seen > 2) w *= Math.max(0.45, 1 - 0.12 * (seen - 2));
    return Math.max(0, w);
  }

  pool(): [Offer[], number[]] {
    const p = this.run.player;
    const m = this.run.meta;
    const offers: Offer[] = [], weights: number[] = [];
    const muted = new Set([...m.mutedWeapons(), ...m.mutedBooks()]);
    const have = new Set(Object.keys(p.weapons));
    const room = have.size < p.max_weapons;
    for (const key of m.unlockedWeapons()) {
      const w = WEAPON_BY_KEY[key];
      if (!w || muted.has(key)) continue;
      if (have.has(key)) {
        if (p.weapons[key] < (w.max ?? B.WEAPON_MAX_LEVEL)) {
          offers.push(this.weaponOffer(w, p.weapons[key] + 1, false));
          weights.push(this.metaWeight(key, 11));
        }
      } else if (room) {
        offers.push(this.weaponOffer(w, 1, true));
        weights.push(this.metaWeight(key, 18));
      }
    }
    let books = m.unlockedBooks().map((k) => BOOK_BY_KEY[k]).filter(Boolean);
    if (!books.length) books = BOOKS.filter((b) => b.basic);
    const bookRoom = p.normalBookCount() < p.max_books;
    const rareRoom = p.rareBookCount() < p.max_rare;
    for (const bk of books) {
      const key = bk.key;
      if (muted.has(key)) continue;
      const cur = p.books[key] || 0;
      if (bk.rare) {
        if (cur > 0 || !rareRoom) continue;
        offers.push(this.bookOffer(bk, 1, true));
        weights.push(this.metaWeight(key, 8) * (1 + C.LUCK_RARE_BOOK_K * p.effLuck()));
        continue;
      }
      if (cur <= 0) {
        if (!bookRoom) continue;
        offers.push(this.bookOffer(bk, 1, true));
        weights.push(this.metaWeight(key, 17));
      } else if (cur < p.bookMaxLevel(key)) {
        offers.push(this.bookOffer(bk, cur + 1, false));
        weights.push(this.metaWeight(key, 12));
      }
    }
    return [offers, weights];
  }

  handLevel() {
    return Math.max(1, this.run.player.level - Math.max(0, this.run.pendingLevelups) + 1);
  }

  private legendHand(): Offer[] {
    const [offers, weights] = this.pool();
    const top = B.RARITY_COUNT - 1;
    const pool: [Offer, number][] = [];
    offers.forEach((o, i) => {
      if (o.kind === "weapon") {
        o.rarity = top;
        o.boost = B.rarityBoost(top, "card");
      } else if (o.kind === "book" && !o.rare && B.BOOK_GAINS[o.key]) {
        o.rarity = top;
        o.gains = B.bookGain(o.key, top, o.lvl);
      } else return;
      o.legend = true;
      pool.push([o, Math.max(1, weights[i])]);
    });
    if (!pool.length) return [];
    const chosen: Offer[] = [];
    const seen = new Set<string>();
    for (const kind of ["weapon", "book"]) {
      const c = pool.filter(([o]) => o.kind === kind);
      if (c.length) {
        const o = weightedPick(c.map((x) => x[0]), c.map((x) => x[1]));
        chosen.push(o);
        seen.add(o.kind + o.key);
      }
    }
    let rest = pool.filter(([o]) => !seen.has(o.kind + o.key));
    while (chosen.length < 3 && rest.length) {
      const o = weightedPick(rest.map((x) => x[0]), rest.map((x) => x[1]));
      chosen.push(o);
      rest = rest.filter(([a]) => a !== o);
    }
    return shuffle(chosen);
  }

  private guaranteedRare(chosen: Offer[]): Offer | null {
    if (chosen.some((c) => c.rare)) return null;
    if (this.handLevel() % C.RARE_BOOK_EVERY !== 0) return null;
    const p = this.run.player;
    if (p.rareBookCount() >= p.max_rare) return null;
    const m = this.run.meta;
    const muted = new Set(m.mutedBooks());
    let cands = m.unlockedBooks().map((k) => BOOK_BY_KEY[k]).filter((b) => b && b.rare && !p.books[b.key]);
    let trial = false;
    if (!cands.length) {
      cands = BOOKS.filter((b) => b.rare && !p.books[b.key] && !muted.has(b.key));
      trial = true;
    }
    if (!cands.length) return null;
    const bk = cands[Math.floor(Math.random() * cands.length)];
    const o = this.bookOffer(bk, 1, true);
    o.trial = trial && !m.ownsBook(bk.key);
    return o;
  }

  start() {
    if (this.run.legendHands > 0) {
      const h = this.legendHand();
      if (h.length) {
        this.choices = h;
        return;
      }
      this.run.legendHands = 0;
    }
    const [o0, w0] = this.pool();
    let pairs = o0.map((o, i) => [o, w0[i]] as [Offer, number]).filter(([, w]) => w > 0);
    if (!pairs.length) pairs = o0.map((o, i) => [o, Math.max(1, w0[i])] as [Offer, number]);
    if (!pairs.length) {
      this.choices = [];
      return;
    }
    const offers = pairs.map((p) => p[0]), weights = pairs.map((p) => p[1]);
    const want = Math.min(3, offers.length);
    const chosen: Offer[] = [];
    const seen = new Set<string>();
    const draw = (cands: Offer[], cw: number[]) => {
      for (let i = 0; i < 60; i++) {
        const pk = weightedPick(cands, cw);
        if (!seen.has(pk.kind + pk.key)) return pk;
      }
      return cands.find((c) => !seen.has(c.kind + c.key)) || null;
    };
    for (const kind of ["weapon", "book"]) {
      if (chosen.length >= want) break;
      const cands = offers.filter((o) => o.kind === kind);
      if (!cands.length) continue;
      const pk = draw(cands, cands.map((o) => weights[offers.indexOf(o)]));
      if (pk) {
        seen.add(pk.kind + pk.key);
        chosen.push(pk);
      }
    }
    while (chosen.length < want) {
      const pk = draw(offers, weights);
      if (!pk) break;
      seen.add(pk.kind + pk.key);
      chosen.push(pk);
    }
    const rare = this.guaranteedRare(chosen);
    if (rare) {
      if (chosen.length < 3) chosen.push(rare);
      else {
        const kinds = chosen.map((c) => c.kind);
        let victim = chosen.length - 1;
        chosen.forEach((c, i) => {
          if (kinds.filter((k) => k === c.kind).length > 1) victim = i;
        });
        chosen[victim] = rare;
      }
    }
    shuffle(chosen);
    for (const c of chosen) this.offerSeen[c.key] = (this.offerSeen[c.key] || 0) + 1;
    this.choices = chosen;
  }

  choose(idx: number) {
    const ch = this.choices[idx];
    if (!ch) return;
    const run = this.run;
    const p = run.player;
    const fx = run.fx;
    if (ch.kind === "book") {
      const lvl = p.takeBook(ch.key, ch.rarity || 0);
      if (lvl <= 0) {
        this.start();
        return;
      }
      const nm = t(`b.${ch.key}.name`);
      fx.popup(p.x, p.y - 64, lvl <= 1 ? nm : `${nm}  Lv.${lvl}`, ch.color, 22, 1.3, true);
      if (ch.rarity) fx.popup(p.x, p.y - 40, t("rar." + ch.rarity), B.RARITY_COLORS[ch.rarity], 15 + ch.rarity, 1.3, true);
      if (ch.key === "r_luck" || ch.key === "r_clover") run.meta.addStat("best_luck_book", 0);
    } else {
      const key = ch.key;
      const w = WEAPON_BY_KEY[key];
      const first = !p.weapons[key];
      p.weapons[key] = (p.weapons[key] || 0) + 1;
      if (first) p.weapon_timers[key] = B.weaponCooldown(w, 1) * 0.35;
      const nm = t(`w.${key}.name`);
      fx.popup(p.x, p.y - 64, first ? nm : `${nm}  Lv.${p.weapons[key]}`, ch.color, 22, 1.4, true);
      if (ch.boost) {
        const g = p.addWeaponBoost(key, ch.boost);
        const tier = ch.rarity || 0;
        if (g > 0) {
          const rc = B.RARITY_COLORS[tier];
          fx.popup(p.x, p.y - 40, `${t("rar." + tier)}  +${Math.round(g * 100)}%`, rc, 15 + tier, 1.4, true);
          if (tier >= 3) {
            fx.ring(p.x, p.y, rc, 24 + 6 * tier, 260, 0.55, 3.5);
            fx.flash(rc, 0.18 + 0.05 * tier);
          }
        }
      }
    }
    if (ch.legend) run.legendHands = Math.max(0, run.legendHands - 1);
    run.pendingLevelups--;
    fx.ring(p.x, p.y, ch.color, 16, 190, 0.45, 3);
    sfx("buy", 0.8);
    haptic("light");
    this.next();
  }

  private next() {
    if (this.run.pendingLevelups > 0) this.start();
    else this.choices = [];
  }

  reroll(): [boolean, string] {
    let cost = this.rerollCost();
    let lucky = false, bonus = false;
    if (this.rerollUsed >= REROLL_FREE && this.rerollBonus > 0) {
      bonus = true;
      cost = 0;
    } else if (cost > 0 && Math.random() < Math.min(C.LUCK_FREE_REROLL_MAX, this.run.player.effLuck() * C.LUCK_FREE_REROLL_K)) {
      lucky = true;
      cost = 0;
    }
    if (cost > this.run.gold) {
      sfx("error", 0.6);
      return [false, t("lu.need_gold", cost)];
    }
    if (cost) this.run.gold -= cost;
    if (bonus) this.rerollBonus--;
    else if (!lucky) this.rerollUsed++;
    const prev = this.choices.map((c) => c.kind + c.key).join();
    for (let i = 0; i < 6; i++) {
      this.start();
      if (this.choices.map((c) => c.kind + c.key).join() !== prev) break;
    }
    sfx("click", 0.7);
    if (lucky) return [true, t("ui.luck_free")];
    return [true, cost ? `-${cost}` : ""];
  }

  skip(): [boolean, string] {
    const cost = this.skipCost();
    if (cost > this.run.gold) {
      sfx("error", 0.6);
      return [false, t("lu.need_gold", cost)];
    }
    if (cost) this.run.gold -= cost;
    this.skipUsed++;
    if (this.choices.some((c) => c.legend)) this.run.legendHands = Math.max(0, this.run.legendHands - 1);
    this.run.pendingLevelups--;
    sfx("swoosh", 0.8);
    this.next();
    return [true, cost ? `-${cost}` : ""];
  }
}
