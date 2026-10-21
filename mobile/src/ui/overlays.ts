/**
 * Koşu içi pencereler: seviye kartları, market, duraklatma, koşu sonu.
 */
import { t, has, fmtPct } from "../core/i18n";
import { rgbCss, fmtTime, RGB } from "../core/util";
import { sfx, audio } from "../core/audio";
import { haptic } from "../core/native";
import * as B from "../game/balance";
import { SHOP_ITEMS, SHOP_CATS, WEAPON_BY_KEY, BOOK_BY_KEY, SKIN_BY_ID, ShopItem } from "../game/data";
import type { Run } from "../game/run";
import type { Offer } from "../game/levelup";
import type { Save } from "../game/save";
import { h, btn, tap, esc, short } from "./dom";
import { online } from "../net/online";
import { icon } from "./icons";

export class Layer {
  el: HTMLElement;
  private closing = false;
  constructor(public host: HTMLElement, cls: string) {
    this.el = h("div", "layer " + cls);
    host.append(this.el);
    requestAnimationFrame(() => this.el.classList.add("in"));
  }
  close(after?: () => void) {
    if (this.closing) return;
    this.closing = true;
    this.el.classList.remove("in");
    this.el.classList.add("out");
    this.el.style.pointerEvents = "none";
    setTimeout(() => {
      this.el.remove();
      after?.();
    }, 180);
  }
}

const RAR = (tier: number | undefined) => B.RARITY_COLORS[tier || 0] as RGB;

function offerName(o: Offer) {
  return o.kind === "weapon" ? t(`w.${o.key}.name`) : t(`b.${o.key}.name`);
}

function fmtGain(run: Run, stat: string, v: number) {
  const p = run.player;
  const [cur, kind] = p.bookStatView(stat, 0);
  const [nxt] = p.bookStatView(stat, v);
  const f = (x: number) => (kind === "int" ? String(Math.round(x)) : kind === "rate" ? x.toFixed(1) + "/s" : fmtPct(x, Math.abs(x) < 0.1 ? 1 : 0));
  return `<div class="gain"><span>${esc(t("bs." + stat))}</span><b>${f(cur)} <em>→</em> ${f(nxt)}</b></div>`;
}

// ------------------------------------------------------------------
// SEVİYE ATLAMA
// ------------------------------------------------------------------
export function showLevelUp(host: HTMLElement, run: Run, done: () => void) {
  const L = new Layer(host, "levelup");
  const lu = run.levelup;
  if (!lu.choices.length) lu.start();
  sfx("levelup", 0.6);
  audio.duck(0.5, 0.2);
  let busy = false;
  const render = () => {
    const p = run.player;
    if (!lu.choices.length) {
      L.close(done);
      return;
    }
    L.el.innerHTML = "";
    const head = h("div", "lu-head");
    head.innerHTML = `<div class="lu-title">${esc(t("lu.title", p.level - Math.max(0, run.pendingLevelups - 1)))}</div><div class="lu-sub">${esc(t("lu.pick"))}${run.pendingLevelups > 1 ? ` · <b>${esc(t("lu.pending", run.pendingLevelups - 1))}</b>` : ""}</div>`;
    const gold = h("div", "chip gold big", icon("coin", 20, "#ffd34d") + `<span>${short(run.gold)}</span>`);
    head.append(gold);
    const cards = h("div", "cards");
    lu.choices.forEach((o, i) => {
      const rc = o.rare ? ([200, 120, 255] as RGB) : RAR(o.rarity);
      const c = h("div", "card" + (o.legend ? " legend" : "") + (o.rare ? " rare" : ""));
      c.style.setProperty("--rc", rgbCss(rc));
      c.style.setProperty("--ic", rgbCss(o.color));
      c.style.animationDelay = i * 70 + "ms";
      const tag = o.kind === "weapon" ? t("lu.weapon") : o.rare ? t("lu.rare2") : t("lu.book2");
      let lvl: string;
      if (o.kind === "weapon") lvl = o.isNew ? t("c.new") : t("lu.levels", o.lvl - 1, o.lvl);
      else lvl = o.isNew ? t("c.new") : t("lu.levels", o.lvl - 1, o.lvl);
      let desc = "";
      if (o.kind === "weapon") desc = esc(o.isNew ? t(`w.${o.key}.desc`) : t(`w.${o.key}.up`));
      else desc = esc(t(`b.${o.key}.desc`));
      let gains = "";
      if (o.gains?.length) gains = o.gains.map(([s, v]) => fmtGain(run, s, v)).join("");
      let boost = "";
      if (o.kind === "weapon" && o.boost) boost = `<div class="gain"><span>${esc(t("lu.dmg_up", ""))}</span><b>+${Math.round(o.boost * 100)}%</b></div>`;
      const rar = o.rarity !== undefined && !o.rare ? `<div class="rar">${esc(t("rar." + (o.rarity || 0)))}</div>` : "";
      c.innerHTML = `
        <div class="c-top"><span class="c-tag">${esc(tag)}</span>${rar}</div>
        <div class="c-ico">${icon(o.icon, 46, rgbCss(o.color))}</div>
        <div class="c-name">${esc(offerName(o))}</div>
        <div class="c-lvl${o.isNew ? " new" : ""}">${esc(lvl)}${o.trial ? ` · ${esc(t("lu.trial"))}` : ""}</div>
        <div class="c-desc">${desc}</div>
        <div class="c-gains">${gains}${boost}</div>`;
      tap(c, () => {
        if (busy) return;
        busy = true;
        c.classList.add("picked");
        haptic("medium");
        setTimeout(() => {
          lu.choose(i);
          busy = false;
          render();
        }, 160);
      }, null);
      cards.append(c);
    });
    const foot = h("div", "lu-foot");
    const rc = lu.rerollCost(), sc = lu.skipCost();
    const rr = btn(`${icon("refresh", 20)}<span>${esc(t("lu.reroll"))}</span><small>${rc ? icon("coin", 14, "#ffd34d") + rc : esc(t("lu.free2", lu.rerollsFree()))}</small>`, "ghost", () => {
      const [ok, msg] = lu.reroll();
      if (!ok) flash(foot, msg);
      render();
    }, null);
    if (rc > run.gold) rr.classList.add("disabled");
    const sk = btn(`${icon("skip", 20)}<span>${esc(t("lu.skip"))}</span><small>${sc ? icon("coin", 14, "#ffd34d") + sc : esc(t("lu.free2", lu.skipsFree()))}</small>`, "ghost", () => {
      const [ok, msg] = lu.skip();
      if (!ok) flash(foot, msg);
      render();
    }, null);
    if (sc > run.gold) sk.classList.add("disabled");
    foot.append(rr, sk);
    L.el.append(head, cards, foot);
  };
  render();
  return {
    pick(i: number) {
      if (busy || !lu.choices[i]) return;
      lu.choose(i);
      render();
    },
    reroll() {
      lu.reroll();
      render();
    },
  };
}

function flash(parent: HTMLElement, msg: string) {
  if (!msg) return;
  const m = h("div", "flash-msg", esc(msg));
  parent.append(m);
  setTimeout(() => m.remove(), 1400);
}

// ------------------------------------------------------------------
// MARKET
// ------------------------------------------------------------------
let lastShopCat = "core";
export function showShop(host: HTMLElement, run: Run, close: () => void) {
  const L = new Layer(host, "shop");
  const cats = Object.keys(SHOP_CATS).filter((c) => run.biome === "hell" || c !== "hell");
  if (!cats.includes(lastShopCat)) lastShopCat = cats[0];
  const head = h("div", "panel-head");
  const title = h("div", "ph-title", icon("cart", 30, "#ffd34d") + `<span>${esc(t("shop.title"))}</span>`);
  const gold = h("div", "chip gold big");
  const x = h("button", "round close", icon("close", 26));
  tap(x, () => L.close(close));
  head.append(title, gold, x);
  const tabs = h("div", "tabs");
  const grid = h("div", "shop-grid scroll");
  const note = h("div", "panel-note", esc(t("shop.paused")));
  L.el.append(head, tabs, grid, note);
  const renderTabs = () => {
    tabs.innerHTML = "";
    for (const c of cats) {
      const b = h("button", "tab" + (c === lastShopCat ? " on" : ""), esc(t("cat." + c)));
      if (c === "cursed") b.classList.add("cursed");
      if (c === "legendary") b.classList.add("legend");
      tap(b, () => {
        lastShopCat = c;
        renderTabs();
        renderGrid();
        grid.scrollTop = 0;
      });
      tabs.append(b);
    }
  };
  const renderGrid = () => {
    gold.innerHTML = icon("coin", 20, "#ffd34d") + `<span>${short(run.gold)}</span>`;
    grid.innerHTML = "";
    const items = SHOP_ITEMS.filter((s) => s.cat === lastShopCat);
    for (const it of items) grid.append(shopCard(run, it, () => renderGrid()));
  };
  renderTabs();
  renderGrid();
  return { close: () => L.close(close) };
}

function shopCard(run: Run, it: ShopItem, refresh: () => void) {
  const p = run.player;
  const lvl = p.shop_levels[it.key] || 0;
  const unlocked = B.shopItemUnlocked(it, run.waves.wave, run.biome);
  const maxed = lvl >= it.max;
  const cost = B.shopItemCost(it, lvl);
  const afford = run.gold >= cost;
  const c = h("div", "sitem" + (maxed ? " maxed" : "") + (!unlocked ? " locked" : "") + (it.cursed ? " cursed" : "") + (it.legendary ? " legend" : ""));
  c.style.setProperty("--ic", rgbCss(it.color));
  const lvTxt = it.endless || it.max >= 99 ? t("shop.owned_inf", lvl) : t("shop.owned", lvl, it.max);
  let action: string;
  if (!unlocked) action = `<div class="s-lock">${icon("lock", 16)} ${esc(it.hell_only ? t("shop.hell_only") : t("shop.locked", B.tierUnlockWave(it.tier)))}</div>`;
  else if (maxed) action = `<div class="s-max">${esc(t("shop.max"))}</div>`;
  else action = `<div class="s-buy${afford ? "" : " poor"}">${icon("coin", 16, "#ffd34d")}<b>${short(cost)}</b></div>`;
  c.innerHTML = `
    <div class="s-ico">${icon(it.icon, 30, rgbCss(it.color))}</div>
    <div class="s-body"><div class="s-name">${esc(t(`s.${it.key}.name`))}</div><div class="s-desc">${esc(t(`s.${it.key}.desc`))}</div><div class="s-lv">${esc(lvTxt)}</div></div>
    ${action}`;
  if (unlocked && !maxed) {
    if (!afford) c.classList.add("disabled");
    tap(c, () => {
      if (run.buyShopItem(it.key)) {
        c.classList.add("bought");
        setTimeout(refresh, 120);
      } else refresh();
    }, null);
  }
  return c;
}

// ------------------------------------------------------------------
// DURAKLATMA
// ------------------------------------------------------------------
export function statRows(run: Run) {
  const p = run.player;
  const rows: [string, string][] = [
    [t("st.max_hp"), `${Math.ceil(p.hp)} / ${Math.round(p.max_hp)}`],
    [t("st.dmg"), p.effDmg().toFixed(1)],
    [t("st.aspd"), (1 / Math.max(0.05, p.effAtkCd())).toFixed(2) + "/s"],
    [t("st.crit"), fmtPct(p.effCritChance())],
    [t("st.critd"), "×" + p.effCritDmg().toFixed(2)],
    [t("st.armor"), fmtPct(p.effArmor())],
    [t("st.regen"), p.effRegen().toFixed(1) + "/s"],
    [t("st.speed"), Math.round(p.effSpeed()).toString()],
    [t("st.pickup"), Math.round(p.effPickup()).toString()],
    [t("st.luck"), fmtPct(p.effLuck())],
    [t("st.gold"), "×" + p.effCoinMult().toFixed(2)],
    [t("st.xp"), "×" + p.effXpMult().toFixed(2)],
  ];
  return rows;
}

export function buildList(run: Run) {
  const p = run.player;
  const items: string[] = [];
  for (const [k, l] of Object.entries(p.weapons)) {
    const w = WEAPON_BY_KEY[k];
    if (!w) continue;
    items.push(`<div class="bitem" style="--ic:${rgbCss(w.color)}">${icon(w.icon, 26, rgbCss(w.color))}<span>${esc(t(`w.${k}.name`))}</span><b>${l}</b></div>`);
  }
  for (const [k, l] of Object.entries(p.books)) {
    const b = BOOK_BY_KEY[k];
    if (!b) continue;
    items.push(`<div class="bitem book${b.rare ? " rare" : ""}" style="--ic:${rgbCss(b.color)}">${icon(b.icon || "book", 26, rgbCss(b.color))}<span>${esc(t(`b.${k}.name`))}</span><b>${l}</b></div>`);
  }
  return items.join("");
}

export function showPause(host: HTMLElement, run: Run, h2: { resume(): void; restart(): void; quit(): void; settings(): void }) {
  const L = new Layer(host, "pause");
  const wrap = h("div", "pause-wrap");
  const left = h("div", "pause-left");
  left.innerHTML = `<div class="big-title">${esc(t("p.title"))}</div>
    <div class="pause-meta">${esc(t("map." + run.theme + ".name"))} · ${esc(t("diff." + run.diff))} · ${esc(t("hud.wave", run.totalWave()))} · ${fmtTime(run.runTime)}</div>`;
  const col = h("div", "menu-col");
  col.append(
    btn(icon("play", 24) + `<span>${esc(t("p.resume"))}</span>`, "primary xl", () => L.close(h2.resume)),
    btn(icon("gear", 22) + `<span>${esc(t("m.settings"))}</span>`, "", () => h2.settings()),
    btn(icon("refresh", 22) + `<span>${esc(t("p.restart"))}</span>`, "", () =>
      confirmBox(host, t("p.quit_q"), () => L.close(h2.restart)),
    ),
    btn(icon("close", 22) + `<span>${esc(t("p.quit"))}</span>`, "danger", () => confirmBox(host, t("p.quit_q"), () => L.close(h2.quit))),
  );
  left.append(col);
  const right = h("div", "pause-right scroll");
  right.innerHTML = `<div class="sec-t">${esc(t("p.build"))}</div><div class="build">${buildList(run) || "—"}</div>
    <div class="sec-t">${esc(t("p.stats"))}</div><div class="stats">${statRows(run)
      .map(([k, v]) => `<div class="srow"><span>${esc(k)}</span><b>${esc(v)}</b></div>`)
      .join("")}</div>`;
  wrap.append(left, right);
  L.el.append(wrap);
  return L;
}

export function confirmBox(host: HTMLElement, text: string, yes: () => void, no?: () => void) {
  const L = new Layer(host, "confirm");
  const box = h("div", "confirm-box");
  box.innerHTML = `<div class="cb-text">${esc(text)}</div>`;
  const row = h("div", "row");
  row.append(
    btn(esc(t("c.no")), "", () => L.close(no)),
    btn(esc(t("c.yes")), "danger", () => L.close(yes)),
  );
  box.append(row);
  L.el.append(box);
  return L;
}

// ------------------------------------------------------------------
// KOŞU SONU
// ------------------------------------------------------------------
export function showGameOver(
  host: HTMLElement,
  run: Run,
  s: ReturnType<Run["summary"]>,
  res: { prevBest: { score: number; wave: number }; unl: { weapons: string[]; books: string[] } },
  save: Save,
  h2: { retry(): void; menu(): void },
) {
  const L = new Layer(host, "gameover");
  const rec = res.prevBest.score > 0 && s.score > res.prevBest.score;
  const killer = s.deathCause ? t("go.killed_by", deathName(s.deathCause)) : "";
  const top = h("div", "go-top");
  top.innerHTML = `<div class="big-title ${rec ? "gold" : ""}">${esc(rec ? t("go.record") : t("go.title"))}</div>${killer ? `<div class="go-killer">${esc(killer)}</div>` : ""}`;
  const main = h("div", "go-main");
  const left = h("div", "go-left");
  const stat = (ic: string, col: string, label: string, val: string, cls = "") =>
    `<div class="go-stat ${cls}">${icon(ic, 22, col)}<span>${esc(label)}</span><b>${esc(val)}</b></div>`;
  left.innerHTML = `
    <div class="go-score"><span>${esc(t("go.score"))}</span><b class="count" data-v="${s.score}">0</b></div>
    <div class="go-stats">
      ${stat("map", "#9fd8ff", t("go.wave"), String(s.wave))}
      ${stat("skull", "#e8e8f2", t("go.kills"), short(s.kills))}
      ${stat("refresh", "#c7b6ff", t("go.time"), fmtTime(s.time))}
      ${stat("star", "#ffd34d", t("go.level"), String(s.level))}
      ${stat("coin", "#ffd34d", t("go.gold"), short(s.gold))}
    </div>
    <div class="go-gems">${icon("gem", 28, "#6ef0ff")}<b>${esc(t("go.gems", s.gems))}</b><small>${icon("gem", 14, "#6ef0ff")} ${short(save.data.gems)}</small></div>
    <div class="go-world"></div>`;
  const gw = left.querySelector(".go-world") as HTMLElement;
  const worldLine = () => {
    const st = online.lastSubmit;
    const txt =
      st === "sending" ? t("go.world_send") : st === "ok" ? t("go.world_ok") : st === "fail" ? t("go.world_fail", online.lastError) : st === "skip_login" ? t("go.world_login") : "";
    gw.innerHTML = txt ? `${icon("globe", 16, st === "ok" ? "#7ef0b0" : st === "fail" ? "#ff8a8a" : "#9fb3e8")}<span>${esc(txt)}</span>` : "";
    if (st === "sending" && gw.isConnected) setTimeout(worldLine, 500);
  };
  worldLine();
  const right = h("div", "go-right scroll");
  const dmg = Object.entries(s.dmgLog).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const tot = dmg.reduce((a, [, v]) => a + v, 0) || 1;
  let html = `<div class="sec-t">${esc(t("go.dmg"))}</div><div class="dmgs">`;
  for (const [k, v] of dmg) {
    const w = WEAPON_BY_KEY[k];
    const name = has("dmg." + k) ? t("dmg." + k) : w ? t(`w.${k}.name`) : has(`b.${k}.name`) ? t(`b.${k}.name`) : k;
    const col = w ? rgbCss(w.color) : k === "gun" ? rgbCss(SKIN_BY_ID[s.skin]?.color || [120, 200, 255]) : "#b8c0e0";
    html += `<div class="dmg-row"><span>${esc(name)}</span><div class="dbar"><i style="width:${((v / tot) * 100).toFixed(1)}%;background:${col}"></i></div><b>${short(v)}</b></div>`;
  }
  html += "</div>";
  const unl = [...res.unl.weapons.map((k) => t("un.weapon", t(`w.${k}.name`))), ...res.unl.books.map((k) => t("un.book", t(`b.${k}.name`)))];
  if (unl.length) html += `<div class="sec-t">${esc(t("go.unlocked"))}</div><div class="unl">${unl.map((u) => `<div class="unl-row">${icon("star", 16, "#ffd34d")}${esc(u)}</div>`).join("")}</div>`;
  right.innerHTML = html;
  main.append(left, right);
  const foot = h("div", "row go-foot");
  foot.append(
    btn(icon("map", 22) + `<span>${esc(t("go.menu"))}</span>`, "", () => L.close(h2.menu)),
    btn(icon("refresh", 22) + `<span>${esc(t("go.retry"))}</span>`, "primary xl", () => L.close(h2.retry)),
  );
  L.el.append(top, main, foot);
  // skor sayacı
  const cEl = left.querySelector(".count") as HTMLElement;
  const target = s.score;
  const t0 = performance.now();
  const step = () => {
    const f = Math.min(1, (performance.now() - t0) / 1100);
    const e = 1 - Math.pow(1 - f, 3);
    cEl.textContent = short(Math.round(target * e));
    if (f < 1) requestAnimationFrame(step);
    else if (rec) sfx("ach", 0.8);
  };
  requestAnimationFrame(step);
  return L;
}

function deathName(c: string) {
  if (has(c)) return t(c);
  if (has("en." + c)) return t("en." + c);
  if (has("bn." + c)) return t("bn." + c);
  return c;
}
