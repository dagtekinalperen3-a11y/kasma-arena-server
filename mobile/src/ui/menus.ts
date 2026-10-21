/**
 * Menü ekranları: ana menü, harita seçimi, karakterler, silahlık, ustalık,
 * başarımlar, rekorlar, ayarlar, nasıl oynanır.
 */
import { t, tx, has, LANGS, lang, setLang, fmtPct } from "../core/i18n";
import { rgbCss, fmtTime, RGB } from "../core/util";
import { sfx } from "../core/audio";
import { haptic, isNative, platform, exitApp } from "../core/native";
import { GD, SKINS, SKIN_ULTS, WEAPONS, BOOKS, ACHIEVEMENTS, MASTERY, getSkin, Req, SkinDef } from "../game/data";
import { Save, MAP_THEMES, skinCost, masteryBonusAt } from "../game/save";
import { heroPortrait } from "../render/portrait";
import { h, btn, tap, esc, short } from "./dom";
import { icon } from "./icons";
import { Layer, confirmBox } from "./overlays";
import { renderWorld } from "./world";
import { online } from "../net/online";

const C = GD;
export const VERSION = "4.0.0";

export interface MenuCallbacks {
  start(theme: string, diff: "normal" | "hard" | "nightmare"): void;
  settingsChanged(): void;
  langChanged(): void;
  previewTheme(theme: string): void;
}

const TIER_COL: Record<string, string> = { bronz: "#d79a62", gumus: "#c9d6e8", altin: "#ffd34d", efsane: "#d48bff" };

export class Menus {
  main: HTMLElement | null = null;
  private stack: Layer[] = [];

  constructor(private host: HTMLElement, private save: Save, private cb: MenuCallbacks) {}

  get open() {
    return this.stack.length > 0;
  }

  /** Android geri tuşu: en üstteki pencereyi kapatır. true = işlendi. */
  back(): boolean {
    const top = this.stack.pop();
    if (top) {
      top.close();
      sfx("click", 0.5);
      return true;
    }
    return false;
  }

  closeAll() {
    while (this.stack.length) this.stack.pop()!.close();
  }

  hideMain() {
    if (this.main) {
      const m = this.main;
      this.main = null;
      m.classList.remove("in");
      m.classList.add("out");
      setTimeout(() => m.remove(), 200);
    }
    this.closeAll();
  }

  private gemsChip() {
    return `<div class="chip gems big">${icon("gem", 20, "#6ef0ff")}<span>${short(this.save.data.gems)}</span></div>`;
  }

  /** Başlıklı tam ekran pencere. */
  private panel(title: string, ic: string, cls = ""): { L: Layer; body: HTMLElement; head: HTMLElement } {
    const L = new Layer(this.host, "panel " + cls);
    const head = h("div", "panel-head");
    const back = h("button", "round back", icon("back", 26));
    tap(back, () => this.closeTop(L));
    head.append(back);
    head.insertAdjacentHTML("beforeend", `<div class="ph-title">${icon(ic, 30)}<span>${esc(title)}</span></div><div class="ph-right">${this.gemsChip()}</div>`);
    const body = h("div", "panel-body");
    L.el.append(head, body);
    this.stack.push(L);
    return { L, body, head };
  }

  private closeTop(L: Layer) {
    const i = this.stack.indexOf(L);
    if (i >= 0) this.stack.splice(i, 1);
    L.close();
    this.refreshMain();
  }

  private refreshGems() {
    this.host.querySelectorAll(".chip.gems span").forEach((e) => (e.textContent = short(this.save.data.gems)));
  }

  // ------------------------------------------------------------------
  // ANA MENÜ
  // ------------------------------------------------------------------
  showMain() {
    this.main?.remove();
    const m = h("div", "mainmenu");
    this.main = m;
    this.host.append(m);
    this.renderMain();
    requestAnimationFrame(() => m.classList.add("in"));
  }

  refreshMain() {
    if (this.main) this.renderMain();
  }

  private renderMain() {
    const m = this.main!;
    const s = this.save;
    const sk = getSkin(s.skinId());
    const daily = s.dailyStatus();
    const achNew = ACHIEVEMENTS.filter((a) => s.hasAch(a.id) && !s.data.achSeen.includes(a.id)).length;
    m.innerHTML = "";
    const top = h("div", "mm-top");
    const dailyBtn = h("button", "chip daily" + (daily.can ? " glow" : ""), icon("gift", 20, daily.can ? "#ffd34d" : "#9aa3c7") + `<span>${esc(t("m.daily"))}</span>`);
    tap(dailyBtn, () => this.showDaily());
    top.innerHTML = this.gemsChip();
    top.prepend(dailyBtn);
    const left = h("div", "mm-left");
    left.innerHTML = `<div class="logo"><span class="l1">EVOLVE</span><span class="l2">ARENA</span></div><div class="tagline">${esc(t("m.tagline"))}</div>`;
    const play = btn(`${icon("play", 34)}<span>${esc(t("m.play"))}</span>`, "play", () => this.showMapSelect(), "tap");
    left.append(play);
    const grid = h("div", "mm-grid");
    const items: [string, string, string, () => void, number?][] = [
      ["user", t("m.skins"), "#7fd0ff", () => this.showSkins()],
      ["sword", t("m.arsenal"), "#ff9e6b", () => this.showArsenal()],
      ["star", t("m.mastery"), "#ffd34d", () => this.showMastery()],
      ["trophy", t("m.ach"), "#c79bff", () => this.showAchievements(), achNew],
      ["medal", t("m.records"), "#7ef0b0", () => this.showRecords()],
      ["gear", t("m.settings"), "#b8c0e0", () => this.showSettings()],
    ];
    for (const [ic, label, col, fn, badge] of items) {
      const b = btn(`${icon(ic, 30, col)}<span>${esc(label)}</span>${badge ? `<i class="badge">${badge}</i>` : ""}`, "tile", fn);
      grid.append(b);
    }
    left.append(grid);
    const right = h("div", "mm-right");
    const ult = SKIN_ULTS[sk.id];
    const best = s.stat("best_score");
    right.innerHTML = `
      <div class="hero-stage" style="--hc:${rgbCss(sk.color as RGB)}">
        <div class="hero-glow"></div>
        <img class="hero-img" src="${heroPortrait(sk, 220)}" alt="">
      </div>
      <div class="hero-name">${esc(t(`sk.${sk.id}.name`))}</div>
      ${ult ? `<div class="hero-ult">${icon(ult.icon, 16, rgbCss(ult.color))}<span>${esc(tx("ult." + sk.id, ult.name))}</span></div>` : ""}
      ${best > 0 ? `<div class="best-line">${icon("trophy", 16, "#ffd34d")}<span>${esc(t("m.best"))}: <b>${short(best)}</b> · ${esc(t("m.best_wave"))}: <b>${s.stat("best_wave")}</b></span></div>` : ""}`;
    tap(right.querySelector(".hero-stage") as HTMLElement, () => this.showSkins());
    const how = btn(`${icon("info", 20)}<span>${esc(t("m.howto"))}</span>`, "ghost small", () => this.showHowTo());
    right.append(how);
    m.append(top, left, right);
  }

  // ------------------------------------------------------------------
  // GÜNLÜK HEDİYE
  // ------------------------------------------------------------------
  showDaily() {
    const s = this.save;
    const st = s.dailyStatus();
    const L = new Layer(this.host, "confirm");
    this.stack.push(L);
    const box = h("div", "confirm-box daily-box");
    const gifts: number[] = C.DAILY_GIFT_GEMS;
    const cur = st.can ? st.day : st.day;
    box.innerHTML = `<div class="big-title small">${esc(t("m.daily"))}</div><div class="days">${gifts
      .map((g, i) => {
        const d = i + 1;
        const idx = ((cur - 1) % gifts.length) + 1;
        const done = st.can ? d < idx : d <= idx;
        const now = st.can && d === idx;
        return `<div class="day${done ? " done" : ""}${now ? " now" : ""}"><small>${esc(t("m.daily_day", d))}</small>${icon("gem", 22, "#6ef0ff")}<b>${g}</b>${done ? `<i>${icon("check", 18, "#7ef0b0")}</i>` : ""}</div>`;
      })
      .join("")}</div>`;
    const row = h("div", "row");
    if (st.can) {
      row.append(
        btn(`${icon("gift", 22)}<span>${esc(t("m.daily_claim", st.gems))}</span>`, "primary xl", () => {
          const g = s.claimDaily();
          if (g) {
            sfx("ach", 1);
            haptic("success");
          }
          this.stack.splice(this.stack.indexOf(L), 1);
          L.close();
          this.refreshMain();
        }, null),
      );
    } else {
      row.append(h("div", "muted-t", esc(t("m.daily_done"))));
      row.append(btn(esc(t("c.ok")), "", () => this.closeTop(L)));
    }
    box.append(row);
    L.el.append(box);
    tap(L.el, (e) => {
      if (e.target === L.el) this.closeTop(L);
    }, null);
  }

  // ------------------------------------------------------------------
  // HARİTA SEÇİMİ
  // ------------------------------------------------------------------
  showMapSelect() {
    const s = this.save;
    const { body } = this.panel(t("ms2.title"), "map", "mapsel");
    let theme = s.mapUnlocked(s.data.settings.lastMap) ? s.data.settings.lastMap : "stone";
    let diff = s.data.settings.diff;
    const maps = h("div", "maps");
    const diffRow = h("div", "diff-row");
    const diffDesc = h("div", "diff-desc");
    const start = btn(`${icon("play", 30)}<span>${esc(t("ms2.start"))}</span>`, "play", () => {
      s.data.settings.lastMap = theme;
      s.data.settings.diff = diff;
      s.persist();
      this.cb.start(theme, diff);
    }, "tap");
    const render = () => {
      maps.innerHTML = "";
      for (const th of MAP_THEMES) {
        const unl = s.mapUnlocked(th);
        const col = rgbCss(C.MAP_THEME_COLOR[th]);
        const best = s.stat(`best_${th}_wave`);
        const pros = (C.MAP_PROS[th] || []).map((k: string) => `<li class="pro">${icon("check", 14, "#7ef0b0")}${esc(t(k, MAP_ACH_COUNT(th)))}</li>`).join("");
        const cons = (C.MAP_CONS[th] || []).map((k: string) => `<li class="con">${icon("close", 12, "#ff7a7a")}${esc(t(k))}</li>`).join("");
        const c = h("div", "mapcard" + (th === theme ? " on" : "") + (unl ? "" : " locked"));
        c.style.setProperty("--mc", col);
        c.innerHTML = `
          <div class="mc-art mc-${th}">${icon(C.MAP_THEME_ICON[th], 44, col)}</div>
          <div class="mc-name">${esc(t(`map.${th}.name`))}</div>
          <div class="mc-rule">${esc(t(`map.${th}.rule`))}</div>
          <ul class="mc-list">${pros}${cons}</ul>
          ${best > 0 ? `<div class="mc-best">${icon("trophy", 14, "#ffd34d")} ${esc(t("ms2.best", best))}</div>` : ""}
          ${unl ? "" : `<div class="mc-lock">${icon("lock", 30)}<span>${esc(t("ms2.locked"))}</span><small>${esc(t("map." + C.MAP_UNLOCK_PREV[th] + ".name"))} · 25</small></div>`}`;
        if (unl)
          tap(c, () => {
            theme = th;
            this.cb.previewTheme(th);
            render();
          });
        else tap(c, () => {}, "error");
        maps.append(c);
      }
      diffRow.innerHTML = "";
      for (const d of C.DIFF_ORDER as ("normal" | "hard" | "nightmare")[]) {
        const [fg, bg] = C.DIFF_BADGE[d];
        const b = h("button", "seg" + (d === diff ? " on" : ""), esc(t("diff." + d)));
        b.style.setProperty("--fg", rgbCss(fg));
        b.style.setProperty("--bg", rgbCss(bg));
        tap(b, () => {
          diff = d;
          render();
        });
        diffRow.append(b);
      }
      diffDesc.textContent = t("diffd." + diff);
    };
    render();
    const foot = h("div", "ms-foot");
    const dl = h("div", "diff-wrap");
    dl.innerHTML = `<div class="sec-t">${esc(t("ms2.diff"))}</div>`;
    dl.append(diffRow, diffDesc);
    foot.append(dl, start);
    body.append(maps, foot);
    this.cb.previewTheme(theme);
  }

  // ------------------------------------------------------------------
  // KARAKTERLER
  // ------------------------------------------------------------------
  showSkins() {
    const s = this.save;
    const { body } = this.panel(t("sk2.title"), "user", "skins");
    let sel = s.skinId();
    const list = h("div", "skin-grid scroll");
    const detail = h("div", "skin-detail scroll");
    body.append(list, detail);
    const order = [...SKINS].sort((a, b) => (s.ownsSkin(b.id) ? 1 : 0) - (s.ownsSkin(a.id) ? 1 : 0) || skinCost(a) - skinCost(b));
    const renderList = () => {
      list.innerHTML = "";
      for (const sk of order) {
        const own = s.ownsSkin(sk.id);
        const eq = s.skinId() === sk.id;
        const c = h("div", "skin-card" + (sk.id === sel ? " on" : "") + (own ? " own" : ""));
        c.style.setProperty("--hc", rgbCss(sk.color as RGB));
        c.innerHTML = `<img src="${heroPortrait(sk, 120)}" alt=""><div class="sc-name">${esc(t(`sk.${sk.id}.name`))}</div>${
          eq ? `<div class="sc-tag eq">${icon("check", 14)}</div>` : own ? "" : `<div class="sc-cost">${icon("gem", 14, "#6ef0ff")}${skinCost(sk)}</div>`
        }`;
        tap(c, () => {
          sel = sk.id;
          renderList();
          renderDetail();
        });
        list.append(c);
      }
    };
    const renderDetail = () => {
      const sk = getSkin(sel);
      const own = s.ownsSkin(sk.id);
      const eq = s.skinId() === sk.id;
      const ult = SKIN_ULTS[sk.id];
      const cost = skinCost(sk);
      detail.innerHTML = `
        <div class="sd-top" style="--hc:${rgbCss(sk.color as RGB)}"><div class="hero-glow"></div><img src="${heroPortrait(sk, 200)}" alt=""></div>
        <div class="sd-name">${esc(t(`sk.${sk.id}.name`))}</div>
        <div class="sd-desc">${esc(t(`sk.${sk.id}.desc`))}</div>
        ${ult ? `<div class="sd-ult" style="--uc:${rgbCss(ult.color)}"><div class="u-ico">${icon(ult.icon, 26, rgbCss(ult.color))}</div><div><div class="u-t">${esc(t("sk2.ult"))} · ${esc(tx("ult." + sk.id, ult.name))}</div><div class="u-d">${esc(tx("ultd." + sk.id, ult.desc))}</div><div class="u-cd">${icon("refresh", 12)} ${esc(t("c.sec", Math.round(ult.cd)))}</div></div></div>` : ""}
        ${perkLines(sk).length ? `<div class="sec-t">${esc(t("sk2.perks"))}</div><ul class="perks">${perkLines(sk).map((p) => `<li>${icon("star", 12, "#ffd34d")}${esc(p)}</li>`).join("")}</ul>` : ""}`;
      const act = h("div", "sd-act");
      if (eq) act.append(btn(`${icon("check", 22)}<span>${esc(t("sk2.equipped"))}</span>`, "ok disabled"));
      else if (own)
        act.append(
          btn(`<span>${esc(t("sk2.equip"))}</span>`, "primary", () => {
            s.equipSkin(sk.id);
            renderList();
            renderDetail();
          }),
        );
      else {
        const b = btn(`${icon("gem", 22, "#6ef0ff")}<span>${esc(t("sk2.buy", cost))}</span>`, "buy", () => {
          if (s.buySkin(sk.id)) {
            sfx("ach", 1);
            haptic("success");
            this.refreshGems();
            renderList();
            renderDetail();
          }
        }, "buy");
        if (s.data.gems < cost) {
          b.classList.add("disabled");
          act.append(b, h("div", "muted-t", esc(t("sk2.no_gems"))));
        } else act.append(b);
      }
      detail.append(act);
    };
    renderList();
    renderDetail();
  }

  // ------------------------------------------------------------------
  // SİLAHLIK
  // ------------------------------------------------------------------
  reqText(r: Req) {
    switch (r.kind) {
      case "ach":
        return t("rq.ach", t(`a.${r.ach}.name`));
      case "book":
        return t("rq.book", t(`b.${r.book}.name`));
      case "weapon":
        return t("rq.weapon", t(`w.${r.weapon}.name`));
      case "shop":
        return t("rq.shop", t(`s.${r.item}.name`), r.need);
      default: {
        const need = r.stat === "total_time" ? Math.round(r.need / 60) : r.need;
        return has("rq." + r.stat) ? t("rq." + r.stat, need.toLocaleString(lang())) : r.text || r.stat || "";
      }
    }
  }

  private reqHtml(reqs: Req[] | undefined) {
    if (!reqs) return "";
    return reqs
      .map((r) => {
        const [cur, need, done] = this.save.reqState(r);
        const isStat = r.kind === "stat" || (r.kind === "ach" && need > 1) || r.kind === "shop";
        const f = Math.min(1, cur / Math.max(1, need));
        const show = (v: number) => short(r.stat === "total_time" ? v / 60 : v);
        return `<div class="req${done ? " done" : ""}"><div class="rq-t">${icon(done ? "check" : "lock", 13, done ? "#7ef0b0" : "#9aa3c7")}<span>${esc(this.reqText(r))}</span></div>${
          isStat && !done ? `<div class="rq-bar"><i style="width:${(f * 100).toFixed(1)}%"></i></div><div class="rq-n">${show(cur)} / ${show(need)}</div>` : ""
        }</div>`;
      })
      .join("");
  }

  showArsenal() {
    const s = this.save;
    const { body } = this.panel(t("ar.title"), "sword", "arsenal");
    let tab: "w" | "b" = "w";
    const tabs = h("div", "tabs");
    const info = h("div", "ar-info");
    const grid = h("div", "ar-grid scroll");
    body.append(tabs, info, grid);
    const render = () => {
      tabs.innerHTML = "";
      for (const [k, label] of [
        ["w", t("ar.weapons")],
        ["b", t("ar.books")],
      ] as ["w" | "b", string][]) {
        const b = h("button", "tab" + (k === tab ? " on" : ""), esc(label));
        tap(b, () => {
          tab = k;
          render();
          grid.scrollTop = 0;
        });
        tabs.append(b);
      }
      const list = tab === "w" ? WEAPONS : BOOKS;
      const owned = tab === "w" ? s.data.weaponsOwned : s.data.booksOwned;
      const muted = tab === "w" ? s.data.mutedWeapons : s.data.mutedBooks;
      const lim = s.muteLimit(tab);
      info.innerHTML = `<span>${esc(t("ar.count", list.filter((x) => owned.includes(x.key)).length, list.length))}</span><span>${icon("muted", 14)} ${esc(t("ar.mute_left", muted.length, lim))}</span>`;
      grid.innerHTML = "";
      const sorted = [...list].sort((a, b) => (owned.includes(b.key) ? 1 : 0) - (owned.includes(a.key) ? 1 : 0));
      for (const it of sorted) {
        const own = owned.includes(it.key);
        const mt = muted.includes(it.key);
        const pre = tab === "w" ? "w" : "b";
        const rare = tab === "b" && (it as any).rare;
        const c = h("div", "ar-card" + (own ? " own" : " locked") + (mt ? " muted" : "") + (rare ? " rare" : ""));
        c.style.setProperty("--ic", rgbCss((it as any).color));
        const how = tab === "w" && has(`w.${it.key}.how`) ? `<div class="ar-how">${esc(t(`w.${it.key}.how`))}</div>` : "";
        c.innerHTML = `
          <div class="ar-head"><div class="ar-ico">${icon((it as any).icon || "book", 30, own ? rgbCss((it as any).color) : "#5d6687")}</div>
          <div><div class="ar-name">${esc(t(`${pre}.${it.key}.name`))}${rare ? ` <em>${esc(t("ar.rare"))}</em>` : ""}</div>
          <div class="ar-desc">${esc(t(`${pre}.${it.key}.desc`))}</div></div></div>
          ${own ? "" : `${how}<div class="reqs">${this.reqHtml(it.unlock?.reqs)}</div>`}`;
        if (own) {
          const mb = btn(mt ? `${icon("muted", 16)}<span>${esc(t("ar.unmute"))}</span>` : `${icon("muted", 16)}<span>${esc(t("ar.mute"))}</span>`, "mini" + (mt ? " on" : ""), () => {
            if (!s.toggleMute(tab, it.key)) {
              sfx("error", 0.6);
              haptic("warning");
            }
            render();
          });
          if (!mt && muted.length >= lim) mb.classList.add("disabled");
          c.append(mb);
          if (mt) c.insertAdjacentHTML("beforeend", `<div class="ar-muted">${esc(t("ar.muted"))}</div>`);
        }
        grid.append(c);
      }
    };
    render();
  }

  // ------------------------------------------------------------------
  // USTALIK
  // ------------------------------------------------------------------
  showMastery() {
    const s = this.save;
    const { body } = this.panel(t("mt.title"), "star", "mastery");
    const sub = h("div", "panel-note top", esc(t("mt.sub")));
    const list = h("div", "mt-list scroll");
    body.append(sub, list);
    const fmtB = (m: any, v: number) => (m.key === "m_hp" ? `+${Math.round(v)}` : m.key === "m_wmute" || m.key === "m_bmute" ? `+${Math.round(v)}` : "+" + fmtPct(v, 1));
    const render = () => {
      list.innerHTML = "";
      for (const m of MASTERY) {
        const lvl = s.masteryLevel(m.key);
        const maxed = s.masteryMaxed(m.key);
        const cost = s.masteryNextCost(m.key);
        const cur = lvl > 0 ? masteryBonusAt(m, lvl) : 0;
        const nxt = masteryBonusAt(m, lvl + 1);
        const r = h("div", "mt-row");
        r.style.setProperty("--ic", rgbCss(m.color));
        const pips = Array.from({ length: C.MASTERY_TIERS }, (_, i) => `<i class="${i < lvl ? "on" : ""}"></i>`).join("");
        r.innerHTML = `<div class="mt-ico">${icon(m.icon, 30, rgbCss(m.color))}</div>
          <div class="mt-body"><div class="mt-name">${esc(t(`mastery.${m.key}.name`))} <span class="mt-lv">${esc(t("c.lv", lvl))}</span></div>
          <div class="mt-desc">${esc(t(`mastery.${m.key}.desc`))}</div>
          <div class="mt-pips">${pips}${lvl > C.MASTERY_TIERS ? `<b>+${lvl - C.MASTERY_TIERS}</b>` : ""}</div></div>
          <div class="mt-val"><b>${fmtB(m, cur)}</b>${maxed ? "" : `<small>→ ${fmtB(m, nxt)}</small>`}</div>`;
        if (maxed) r.append(btn(esc(t("mt.max")), "mini ok disabled"));
        else {
          const b = btn(`${icon("gem", 16, "#6ef0ff")}<span>${short(cost)}</span>`, "buy mini", () => {
            if (s.buyMastery(m.key)) {
              haptic("success");
              this.refreshGems();
              render();
            }
          }, "buy");
          if (s.data.gems < cost) b.classList.add("disabled");
          r.append(b);
        }
        list.append(r);
      }
    };
    render();
  }

  // ------------------------------------------------------------------
  // BAŞARIMLAR
  // ------------------------------------------------------------------
  showAchievements() {
    const s = this.save;
    const { body } = this.panel(t("ac.title"), "trophy", "achs");
    const got = ACHIEVEMENTS.filter((a) => s.hasAch(a.id)).length;
    const info = h("div", "ar-info", `<span>${esc(t("ac.count", got, ACHIEVEMENTS.length))}</span><div class="ac-total"><i style="width:${((got / ACHIEVEMENTS.length) * 100).toFixed(1)}%"></i></div>`);
    const grid = h("div", "ac-grid scroll");
    body.append(info, grid);
    const sorted = [...ACHIEVEMENTS].sort((a, b) => {
      const ga = s.hasAch(a.id) ? 1 : 0, gb = s.hasAch(b.id) ? 1 : 0;
      if (ga !== gb) return ga - gb;
      const fa = a.track ? s.stat(a.track.stat) / a.track.need : 0, fb = b.track ? s.stat(b.track.stat) / b.track.need : 0;
      return fb - fa;
    });
    for (const a of sorted) {
      const done = s.hasAch(a.id);
      const fresh = done && !s.data.achSeen.includes(a.id);
      const col = TIER_COL[a.tier] || "#c9d6e8";
      const c = h("div", "ac-card" + (done ? " done" : "") + (fresh ? " fresh" : ""));
      c.style.setProperty("--tc", col);
      let prog = "";
      if (!done && a.track) {
        const cur = Math.min(s.stat(a.track.stat), a.track.need);
        prog = `<div class="rq-bar"><i style="width:${((cur / a.track.need) * 100).toFixed(1)}%"></i></div><div class="rq-n">${short(cur)} / ${short(a.track.need)}</div>`;
      }
      c.innerHTML = `<div class="ac-ico">${icon(a.icon || "trophy", 28, done ? col : "#59617f")}</div>
        <div class="ac-body"><div class="ac-name">${esc(t(`a.${a.id}.name`))}</div><div class="ac-desc">${esc(t(`a.${a.id}.desc`))}</div>${prog}</div>
        <div class="ac-gem">${done ? icon("check", 20, "#7ef0b0") : `${icon("gem", 14, "#6ef0ff")}<b>${a.gems}</b>`}</div>`;
      if (has(`a.${a.id}.how`)) {
        tap(c, () => {
          c.classList.toggle("open");
          if (!c.querySelector(".ac-how")) c.querySelector(".ac-body")!.insertAdjacentHTML("beforeend", `<div class="ac-how">${esc(t(`a.${a.id}.how`))}</div>`);
        });
      }
      grid.append(c);
    }
    for (const a of ACHIEVEMENTS) if (s.hasAch(a.id) && !s.data.achSeen.includes(a.id)) s.data.achSeen.push(a.id);
    s.persist();
  }

  // ------------------------------------------------------------------
  // REKORLAR
  // ------------------------------------------------------------------
  showRecords(world: (el: HTMLElement) => void = renderWorld) {
    const s = this.save;
    const { body } = this.panel(t("rec.title"), "medal", "records");
    const tabs = h("div", "tabs");
    const content = h("div", "rec-body scroll");
    body.append(tabs, content);
    let tab = "local";
    const render = () => {
      tabs.innerHTML = "";
      const tl: [string, string][] = [
        ["local", t("rec.local")],
        ["life", t("rec.lifetime")],
      ];
      tl.push(["world", t("rec.world")]);
      for (const [k, label] of tl) {
        const b = h("button", "tab" + (k === tab ? " on" : ""), esc(label));
        tap(b, () => {
          tab = k;
          render();
        });
        tabs.append(b);
      }
      content.innerHTML = "";
      if (tab === "local") {
        if (!s.data.records.length) {
          content.innerHTML = `<div class="empty">${icon("trophy", 48, "#4a5274")}<span>${esc(t("rec.empty"))}</span></div>`;
          return;
        }
        content.innerHTML = `<table class="rec-table"><tbody>${s.data.records
          .map((r, i) => {
            const sk = getSkin(r.skin);
            return `<tr class="${i < 3 ? "top" + (i + 1) : ""}"><td class="rk">${i + 1}</td><td class="pf"><img src="${heroPortrait(sk, 64)}" alt=""></td><td class="sc">${short(r.score)}</td><td>${esc(t("hud.wave", r.wave))}</td><td>${icon("skull", 14)} ${short(r.kills)}</td><td>${fmtTime(r.time)}</td><td class="mp">${esc(t("map." + r.map + ".short"))} · ${esc(t("diff." + r.diff))}</td></tr>`;
          })
          .join("")}</tbody></table>`;
      } else if (tab === "life") {
        const rows: [string, string, string][] = [
          ["refresh", t("rec.runs"), short(s.stat("runs"))],
          ["trophy", t("m.best"), short(s.stat("best_score"))],
          ["map", t("m.best_wave"), String(s.stat("best_wave"))],
          ["skull", t("st.kills"), short(s.stat("total_kills"))],
          ["coin", t("go.gold"), short(s.stat("total_gold"))],
          ["star", t("rec.playtime"), fmtTime(s.stat("total_time"))],
          ["gem", t("c.gems"), short(s.data.gemsEarned)],
        ];
        content.innerHTML = `<div class="life-grid">${rows.map(([ic, k, v]) => `<div class="life">${icon(ic, 26, "#9fd8ff")}<span>${esc(k)}</span><b>${esc(v)}</b></div>`).join("")}</div>`;
      } else world(content);
    };
    render();
  }

  // ------------------------------------------------------------------
  // AYARLAR
  // ------------------------------------------------------------------
  showSettings(extra?: (body: HTMLElement) => void) {
    const s = this.save;
    const st = s.data.settings;
    const { L, body } = this.panel(t("set.title"), "gear", "settings");
    const wrap = h("div", "set-wrap scroll");
    body.append(wrap);
    const render = () => {
      wrap.innerHTML = "";
      const row = (label: string, ic: string) => {
        const r = h("div", "set-row");
        r.innerHTML = `<div class="set-l">${icon(ic, 22, "#9fb3e8")}<span>${esc(label)}</span></div>`;
        wrap.append(r);
        return r;
      };
      // dil
      const lr = row(t("set.lang"), "globe");
      const lg = h("div", "seg-group");
      for (const [code, name] of LANGS) {
        const b = h("button", "seg" + (code === lang() ? " on" : ""), esc(name));
        tap(b, () => {
          st.lang = code;
          setLang(code);
          s.persist();
          this.cb.langChanged();
          // başlıkları yeni dile çevir
          this.stack.splice(this.stack.indexOf(L), 1);
          L.close();
          this.refreshMain();
          this.showSettings(extra);
        });
        lg.append(b);
      }
      lr.append(lg);
      // ses
      const slider = (label: string, ic: string, get: () => number, set: (v: number) => void) => {
        const r = row(label, ic);
        const inp = h("input", "slider") as HTMLInputElement;
        inp.type = "range";
        inp.min = "0";
        inp.max = "100";
        inp.value = String(Math.round(get() * 100));
        inp.style.setProperty("--v", inp.value + "%");
        inp.addEventListener("input", () => {
          inp.style.setProperty("--v", inp.value + "%");
          set(+inp.value / 100);
          this.cb.settingsChanged();
        });
        inp.addEventListener("change", () => {
          sfx("click", 0.8);
          s.persist();
        });
        r.append(inp);
      };
      slider(t("set.sfx"), "volume", () => st.sfx, (v) => (st.sfx = v));
      slider(t("set.music"), "volume", () => st.music, (v) => (st.music = v));
      const toggle = (label: string, ic: string, key: keyof typeof st) => {
        const r = row(label, ic);
        const on = !!st[key];
        const b = h("button", "toggle" + (on ? " on" : ""), "<i></i>");
        tap(b, () => {
          (st as any)[key] = !st[key];
          s.persist();
          this.cb.settingsChanged();
          render();
        });
        r.append(b);
      };
      toggle(t("set.haptics"), "hand", "haptics");
      toggle(t("set.shake"), "bolt", "shake");
      toggle(t("set.dmg"), "target", "dmgNumbers");
      toggle(t("set.left"), "hand", "leftHanded");
      // kamera
      const zr = row(t("set.zoom"), "map");
      const zg = h("div", "seg-group");
      for (const [v, label] of [
        [360, t("set.zoom_near")],
        [440, t("set.zoom_mid")],
        [540, t("set.zoom_far")],
      ] as [number, string][]) {
        const b = h("button", "seg" + (st.zoom === v ? " on" : ""), esc(label));
        tap(b, () => {
          st.zoom = v;
          s.persist();
          this.cb.settingsChanged();
          render();
        });
        zg.append(b);
      }
      zr.append(zg);
      const qr = row(t("set.quality"), "star");
      const qg = h("div", "seg-group");
      for (const [v, label] of [
        [1, t("set.q_high")],
        [0, t("set.q_low")],
      ] as [number, string][]) {
        const b = h("button", "seg" + (st.quality === v ? " on" : ""), esc(label));
        tap(b, () => {
          st.quality = v;
          s.persist();
          this.cb.settingsChanged();
          render();
        });
        qg.append(b);
      }
      qr.append(qg);
      toggle(t("set.fps"), "info", "fpsCounter");
      const ar = row(t("acc.account"), "user");
      ar.insertAdjacentHTML("beforeend", `<span class="muted-t">${esc(online.loggedIn ? t("acc.signed", online.account!.username) : t("acc.guest"))}</span>`);
      extra?.(wrap);
      const foot = h("div", "set-foot");
      const reset = btn(`${icon("refresh", 18)}<span>${esc(t("set.reset"))}</span>`, "danger small", () =>
        confirmBox(this.host, t("set.reset_q"), () => {
          s.resetAll();
          this.refreshGems();
          this.refreshMain();
          haptic("heavy");
        }),
      );
      foot.append(reset);
      if (isNative && platform === "android")
        foot.append(
          btn(`${icon("close", 18)}<span>${esc(t("m.quit"))}</span>`, "ghost small", () => confirmBox(this.host, t("m.quit_q"), () => exitApp())),
        );
      foot.append(btn(`${icon("info", 18)}<span>${esc(t("set.privacy"))}</span>`, "ghost small", () => this.showPrivacy()));
      foot.insertAdjacentHTML("beforeend", `<div class="ver">EvolveArena · ${esc(t("set.version", VERSION))}</div>`);
      wrap.append(foot);
    };
    render();
    return L;
  }

  /** Gizlilik politikası (uygulamanın içinde, çevrim dışı da açılır). */
  showPrivacy() {
    const { body } = this.panel(t("set.privacy"), "info", "privacy");
    const fr = h("iframe", "doc-frame") as HTMLIFrameElement;
    fr.src = "privacy.html";
    body.append(fr);
  }

  // ------------------------------------------------------------------
  // NASIL OYNANIR
  // ------------------------------------------------------------------
  showHowTo(onDone?: () => void) {
    const L = new Layer(this.host, "confirm howto");
    this.stack.push(L);
    const box = h("div", "confirm-box how-box");
    const rows: [string, string, string][] = [
      ["hand", "#7fd0ff", t("how.move")],
      ["target", "#ff9e6b", t("how.aim")],
      ["dash", "#9fd8ff", t("how.dash")],
      ["fist", "#ffb36b", t("how.bonk")],
      ["star", "#c79bff", t("how.level")],
      ["cart", "#ffd34d", t("how.shop")],
      ["skull", "#ff7a7a", t("how.boss")],
    ];
    box.innerHTML = `<div class="big-title small">${esc(t("how.title"))}</div><div class="how-list scroll">${rows
      .map(([ic, col, txt]) => `<div class="how-row"><div class="hw-ico" style="--ic:${col}">${icon(ic, 26, col)}</div><span>${esc(txt)}</span></div>`)
      .join("")}</div>`;
    const row = h("div", "row");
    row.append(
      btn(esc(t("how.ok")), "primary xl", () => {
        this.stack.splice(this.stack.indexOf(L), 1);
        L.close(onDone);
      }),
    );
    box.append(row);
    L.el.append(box);
  }
}

/** Karakter özellik satırları — verilerden, seçili dilde üretilir. */
const PCT_ADD: Record<string, [string, number]> = {
  base_armor: ["st.armor", 1], bonk_mult: ["bs.bonk", 1], bonk_radius_mult: ["bs.bonk_r", 1], coin_mult: ["bs.coin", 1],
  crit_chance: ["bs.crit", 1], crit_dmg_mult: ["bs.critd", 1], dash_cd_mult: ["pk.dashcd", 1], dash_dist_mult: ["bs.dash", 1],
  dmg_taken_mult: ["pk.taken", 1], luck: ["bs.luck", 1], proj_speed_mult: ["pk.projspd", 1], run_dmg_mult: ["bs.dmg", 1], xp_mult: ["bs.xp", 1],
  skin_aspd: ["bs.aspd", 1], skin_power: ["bs.dmg", 1], regen_pct: ["pk.regen_pct", 1],
};
const FLAT_ADD: Record<string, string> = { base_max_hp: "pk.hp", _hp: "pk.hp", base_pickup: "st.pickup", base_speed: "st.speed", base_regen: "st.regen", multishot_level: "pk.multishot", pierce_bonus: "bs.pierce" };
function signed(v: number, pct: boolean, digits = 0) {
  const s = v < 0 ? "−" : "+";
  const a = Math.abs(v);
  if (!pct) return s + (Number.isInteger(a) ? a : a.toFixed(1));
  const d = a * 100 < 1 ? (a * 100 < 0.1 ? 3 : 1) : Number.isInteger(Math.round(a * 1000) / 10) ? 0 : 1;
  return s + fmtPct(a, Math.max(d, digits));
}
export function perkLines(sk: SkinDef): string[] {
  const out: string[] = [];
  const label = (k: string) => (PCT_ADD[k] ? t(PCT_ADD[k][0]) : FLAT_ADD[k] ? t(FLAT_ADD[k]) : has("pk." + k) ? t("pk." + k) : k);
  for (const [k, v] of Object.entries(sk.perk_set || {})) {
    if (k === "titan_smash") out.push(t("pk.titan"));
    else if (k === "bonk_cd") out.push(t("pk.bonk_cd", v));
    else out.push(t("pk.start", label(k), v));
  }
  for (const [k, v] of Object.entries(sk.perk_add || {})) {
    if (k === "luck_per_level") out.push(t("pk.luck_lvl"));
    else if (k === "second_wind_charges") out.push(t("pk.second"));
    else if (PCT_ADD[k]) out.push(`${label(k)} ${signed(v, true)}`);
    else if (FLAT_ADD[k]) out.push(`${label(k)} ${signed(v, false)}${k === "base_regen" ? "/s" : ""}`);
  }
  for (const [k, [every, mx]] of Object.entries(sk.perk_every || {})) out.push(t("pk.every", every, label(k), mx));
  for (const [k, [per, cap]] of Object.entries(sk.perk_level || {})) {
    const pct = !!PCT_ADD[k];
    out.push(t("pk.level", label(k), signed(per, pct, k === "regen_pct" ? 3 : 1), signed(cap, pct)));
  }
  return out;
}

function MAP_ACH_COUNT(th: string) {
  return ACHIEVEMENTS.filter((a) => a.map === th).length;
}

export type { SkinDef };
