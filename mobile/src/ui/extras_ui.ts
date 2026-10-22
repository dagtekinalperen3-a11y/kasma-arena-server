/**
 * Gezgin tüccar (yeminler) ve lanetli sandık pencereleri.
 */
import { t, fmtPct } from "../core/i18n";
import { rgbCss, RGB } from "../core/util";
import { sfx } from "../core/audio";
import { haptic } from "../core/native";
import * as B from "../game/balance";
import { GD } from "../game/data";
import type { Run } from "../game/run";
import { OATHS, oathUpText, CURSE_COLOR, CURSE_RED } from "../game/extras";
import { merchantTex } from "../render/art_misc";
import { h, btn, tap, esc, short } from "./dom";
import { icon } from "./icons";
import { Layer } from "./overlays";

const C = GD;
let merchantImg = "";
function merchantPic() {
  if (!merchantImg) merchantImg = ((merchantTex().source as any).resource as HTMLCanvasElement).toDataURL();
  return merchantImg;
}
const rarCol = (tier: number) => rgbCss(B.RARITY_COLORS[tier] as RGB);

// ------------------------------------------------------------------
// TÜCCAR
// ------------------------------------------------------------------
export function showMerchant(host: HTMLElement, run: Run, done: () => void) {
  const L = new Layer(host, "merchant");
  const ex = run.ex;
  const close = () => {
    ex.merchantOpen = false;
    L.close(done);
  };
  const greet = () => {
    L.el.innerHTML = "";
    const box = h("div", "m-greet");
    const sworn = ex.oath;
    const txt = sworn ? t("m.sworn", t(`oath.${sworn}.name`), t("rar." + ex.oathTier)) : t("m.greet");
    box.innerHTML = `<img class="m-pic" src="${merchantPic()}" alt="">
      <div class="m-talk"><div class="m-name">${esc(t("m.name"))}</div><div class="m-text">${esc(txt)}</div>
      ${sworn ? "" : `<div class="m-luck">${icon("clover", 14, "#7ef0b0")} ${esc(t("m.luck", fmtPct(ex.merchantLuck(), 1)))}</div>`}</div>`;
    const row = h("div", "row");
    if (sworn) row.append(btn(esc(t("m.ok")), "primary", close));
    else
      row.append(
        btn(`${icon("star", 22)}<span>${esc(t("m.see_oaths"))}</span><small>${esc(t("m.see_oaths_sub"))}</small>`, "merchant-btn xl", cards),
        btn(`<span>${esc(t("m.later"))}</span><small>${esc(t("m.later_sub"))}</small>`, "ghost", close),
      );
    box.append(row);
    L.el.append(box);
  };
  const cards = () => {
    L.el.innerHTML = "";
    const head = h("div", "lu-head");
    head.innerHTML = `<div class="lu-title m-title">${esc(t("dr.title_oath"))}</div><div class="lu-sub">${esc(t("dr.sub_oath"))}</div>`;
    head.append(h("div", "chip gold big", icon("coin", 20, "#ffd34d") + `<span>${short(run.gold)}</span>`));
    const wrap = h("div", "cards");
    ex.merchantOffers().forEach(([key, tier], i) => {
      const def = OATHS.find((o) => o[0] === key)!;
      const c = h("div", "card oath");
      c.style.setProperty("--rc", rarCol(tier));
      c.style.setProperty("--ic", rgbCss(def[2]));
      c.style.animationDelay = i * 70 + "ms";
      c.innerHTML = `<div class="c-top"><span class="c-tag">${esc(t("dr.title_oath"))}</span><div class="rar">${esc(t("rar." + tier))}</div></div>
        <div class="c-ico">${icon(def[1], 44, rgbCss(def[2]))}</div>
        <div class="c-name">${esc(t(`oath.${key}.name`))}</div>
        <div class="c-gains">
          <div class="gain pow"><span>${esc(t("dr.power"))}</span><b>${esc(oathUpText(key, tier))}</b></div>
          <div class="gain price"><span>${esc(t("dr.price"))}</span><b>${esc(t(`oath.${key}.down`))}</b></div>
        </div>
        <div class="c-act">${esc(t("dr.swear"))}</div>`;
      tap(c, () => {
        ex.chooseOath(key, tier);
        haptic("success");
        L.close(done);
      }, null);
      wrap.append(c);
    });
    const foot = h("div", "lu-foot");
    const left = ex.rerollLeft();
    const price = ex.rerollPrice();
    const sub = left <= 0 ? t("m.reroll_none") : run.gold < price ? t("m.reroll_poor", price) : t("m.reroll_sub", price, left);
    const rr = btn(`${icon("refresh", 20)}<span>${esc(t("m.reroll"))}</span><small>${esc(sub)}</small>`, "ghost", () => {
      const [ok] = ex.merchantReroll();
      if (ok) {
        sfx("swoosh", 0.8);
        cards();
      }
    }, null);
    if (left <= 0 || run.gold < price) rr.classList.add("disabled");
    foot.append(rr, btn(esc(t("m.later")), "ghost", close));
    L.el.append(head, wrap, foot);
  };
  greet();
  return { close };
}

// ------------------------------------------------------------------
// LANETLİ SANDIK
// ------------------------------------------------------------------
export function showCurse(host: HTMLElement, run: Run, done: () => void) {
  const L = new Layer(host, "curse");
  const ex = run.ex;
  const offers = ex.curseOffers || [];
  const p = run.player;
  const caveLuck = p.effLuck() * C.CAVE_LUCK_MULT + C.CAVE_LUCK_BASE;
  const head = h("div", "lu-head col");
  head.innerHTML = `<div class="lu-title cu-title">${esc(t("cu.title"))}</div><div class="lu-sub">${esc(t("cu.sub"))}</div>
    <div class="cu-line">${esc(t("cu.score_now", fmtPct(run.curseScoreBonus, 1)))} · ${esc(t("cu.luck_line", fmtPct(caveLuck, 1)))}</div>`;
  const wrap = h("div", "cards");
  const kindCol: Record<string, string> = { pair: rgbCss(CURSE_COLOR), gamble: "#ffc460", blood: rgbCss(CURSE_RED) };
  offers.forEach((o, i) => {
    const c = h("div", "card curse k-" + o.kind);
    c.style.setProperty("--rc", rarCol(o.tier));
    c.style.setProperty("--kc", kindCol[o.kind]);
    c.style.animationDelay = i * 70 + "ms";
    let extra = "";
    if (o.kind === "gamble") extra += `<div class="cu-note gold">${icon("star", 14, "#ffc460")} ${esc(t("cu.gamble_win", fmtPct(o.win || 0, 0), 2))}</div>`;
    if (o.kind === "blood") extra += `<div class="cu-note red">${esc(t("cu.blood_cost", fmtPct(C.BLOOD_PRICE, 0)))}</div><div class="cu-note">${esc(t("cu.no_curse"))}</div>`;
    if (o.curse)
      extra += `<div class="cu-curse"><b>${icon("skull", 14, rgbCss(CURSE_RED))} ${esc(t("cu.c_" + o.curse))}</b><span>${esc(t("cu.cd_" + o.curse))}</span><em>${esc(t("cu.score_plus", fmtPct(C.CURSE_SCORE_PER, 0)))}</em></div>`;
    c.innerHTML = `<div class="cu-band">${esc(t("cu.k_" + o.kind))}</div>
      <div class="c-top"><span class="c-tag"></span><div class="rar">${esc(t("rar." + o.tier))}</div></div>
      <div class="c-name">${esc(t("cu.rw_" + o.reward))}</div>
      <ul class="cu-lines">${o.lines.map((l) => `<li>${icon("check", 13, "#7ef0b0")}${esc(l)}</li>`).join("")}</ul>
      ${extra}
      <div class="c-act">${esc(t("cu.accept"))}</div>`;
    tap(c, () => {
      ex.acceptCurse(i);
      L.close(done);
    }, null);
    wrap.append(c);
  });
  const foot = h("div", "lu-foot col");
  foot.append(
    btn(esc(t("cu.leave")), "ghost", () => {
      ex.declineCurse();
      L.close(done);
    }),
    h("div", "cu-once", esc(t("cu.once"))),
  );
  L.el.append(head, wrap, foot);
  return {
    close() {
      ex.declineCurse();
      L.close(done);
    },
  };
}
