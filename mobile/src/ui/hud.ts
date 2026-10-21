/**
 * Oyun içi gösterge (DOM). Saniyede ~20 kez ve yalnız değişen değerler
 * yazılır; kare hızını etkilemez. Dokunmatik düğmelerin isabet testi
 * Input'ta koordinatla yapılır, buradaki öğeler yalnız görünüştür.
 */
import { Input, TouchButton } from "../core/input";
import { t } from "../core/i18n";
import { fmtTime, rgbCss } from "../core/util";
import { getSkin } from "../game/data";
import type { Run } from "../game/run";
import { h, setText, setStyle, setClass, short, tap } from "./dom";
import { icon } from "./icons";

export interface HudCallbacks {
  pause(): void;
  shop(): void;
}

interface Toast {
  el: HTMLElement;
  t: number;
}

export class Hud {
  root = h("div", "hud");
  private hpFill = h("i");
  private hpLag = h("b");
  private hpText = h("span");
  private shieldRow = h("div", "shields");
  private xpFill = h("i");
  private lvText = h("span", "lv");
  private ultBox = h("div", "ult");
  private ultIco = h("div", "ult-ico");
  private waveText = h("div", "wave-t");
  private waveSub = h("div", "wave-s");
  private waveBar = h("i");
  private goldText = h("span");
  private killText = h("span");
  private scoreText = h("span");
  private bossWrap = h("div", "bossbar");
  private bossName = h("div", "bn");
  private bossFill = h("i");
  private bossLag = h("b");
  private ann = h("div", "announce");
  private toasts = h("div", "toasts");
  private combo = h("div", "combo");
  private fps = h("div", "fps");
  private status = h("div", "status");
  private joyBase = h("div", "joy");
  private joyKnob = h("div", "joy-knob");
  private aimBase = h("div", "joy aim");
  private aimKnob = h("div", "joy-knob aim");
  private joyHint = h("div", "joy-hint");
  private record = h("div", "rec-flash");
  private btnEls: Record<string, HTMLElement> = {};
  private tlist: Toast[] = [];
  private lastHp = -1;
  private lagHp = 1;
  private bossLagV = 1;
  private acc = 0;
  private fpsAcc = 0;
  private fpsN = 0;
  private lastAnn = "";
  safe = { l: 0, r: 0, t: 0, b: 0 };
  showFps = false;
  leftHanded = false;
  hintTime = 0;

  constructor(private input: Input, private cb: HudCallbacks) {
    const r = this.root;
    // sol üst: can + tecrübe + ülti
    const tl = h("div", "hud-tl");
    const hp = h("div", "hpbar");
    hp.append(this.hpLag, this.hpFill, this.hpText);
    hp.insertAdjacentHTML("afterbegin", `<div class="hp-ico">${icon("heart", 22, "#ff5a6e")}</div>`);
    const xp = h("div", "xpbar");
    xp.append(this.xpFill, this.lvText);
    this.ultBox.append(this.ultIco);
    const col = h("div", "hud-col");
    col.append(hp, xp, this.shieldRow, this.status);
    tl.append(this.ultBox, col);
    // orta üst: dalga
    const tc = h("div", "hud-tc");
    const wb = h("div", "wavebar");
    wb.append(this.waveBar);
    tc.append(this.waveText, wb, this.waveSub, this.bossWrap, this.toasts);
    this.bossWrap.append(this.bossName);
    const bb = h("div", "bb");
    bb.append(this.bossLag, this.bossFill);
    this.bossWrap.append(bb);
    // sağ üst: kaynaklar + duraklat
    const tr = h("div", "hud-tr");
    const res = h("div", "res");
    const g = h("div", "chip gold", icon("coin", 18, "#ffd34d"));
    g.append(this.goldText);
    const k = h("div", "chip", icon("skull", 18, "#e8e8f2"));
    k.append(this.killText);
    const s = h("div", "chip score", icon("star", 18, "#9fd8ff"));
    s.append(this.scoreText);
    res.append(g, k, s);
    const pause = h("button", "round pause", icon("pause", 26));
    tap(pause, () => this.cb.pause());
    const shop = h("button", "round shop", icon("cart", 26));
    tap(shop, () => this.cb.shop());
    const btnRow = h("div", "hud-btns");
    btnRow.append(shop, pause);
    tr.append(btnRow, res, this.combo);
    // sağ alt: eylem düğmeleri (yalnız görüntü)
    for (const [id, ic, label] of [
      ["dash", "dash", t("btn.dash")],
      ["bonk", "fist", t("btn.bonk")],
      ["use", "play", t("btn.use")],
    ]) {
      const b = h("div", "abtn " + id, `<div class="cd"></div><div class="ab-ico">${icon(ic, 34)}</div><div class="ab-l">${label}</div>`);
      this.btnEls[id] = b;
      r.append(b);
    }
    this.joyBase.append(this.joyKnob);
    this.aimBase.append(this.aimKnob);
    this.joyHint.innerHTML = `<div class="jh-ring"></div><div class="jh-dot"></div><div class="jh-t">${t("how.move")}</div>`;
    r.append(tl, tc, tr, this.joyHint, this.joyBase, this.aimBase, this.ann, this.record, this.fps);
    this.measureSafe();
    this.layout();
  }

  measureSafe() {
    const probe = h("div", "safe-probe");
    document.body.append(probe);
    const cs = getComputedStyle(probe);
    this.safe = { l: parseFloat(cs.paddingLeft) || 0, r: parseFloat(cs.paddingRight) || 0, t: parseFloat(cs.paddingTop) || 0, b: parseFloat(cs.paddingBottom) || 0 };
    probe.remove();
  }

  /** Düğme yerlerini ekran boyutuna göre hesaplar ve Input'a verir. */
  layout() {
    this.measureSafe();
    const W = window.innerWidth, H = window.innerHeight;
    const s = Math.min(W, H);
    const big = Math.round(Math.max(44, Math.min(70, s * 0.105)));
    const small = Math.round(big * 0.8);
    const pad = 22;
    const right = W - Math.max(this.safe.r, 8) - pad;
    const bottom = H - Math.max(this.safe.b, 6) - pad;
    const mirror = this.leftHanded;
    const X = (x: number) => (mirror ? W - x : x);
    const dash: TouchButton = { id: "dash", x: X(right - big), y: bottom - big, r: big, visible: true, pressed: false };
    const bonk: TouchButton = { id: "bonk", x: X(right - big * 2 - small * 1.25), y: bottom - small * 0.55, r: small, visible: true, pressed: false };
    const use: TouchButton = { id: "use", x: X(right - big * 0.9), y: bottom - big * 2 - small * 1.2, r: small, visible: false, pressed: false };
    this.input.setButtons([dash, bonk, use]);
    this.input.mirror = mirror;
    for (const b of [dash, bonk, use]) {
      const el = this.btnEls[b.id];
      el.style.width = el.style.height = b.r * 2 + "px";
      el.style.left = b.x - b.r + "px";
      el.style.top = b.y - b.r + "px";
    }
    this.root.style.setProperty("--sl", Math.max(this.safe.l, 10) + "px");
    this.root.style.setProperty("--sr", Math.max(this.safe.r, 10) + "px");
    this.root.style.setProperty("--st", Math.max(this.safe.t, 8) + "px");
    this.root.style.setProperty("--sb", Math.max(this.safe.b, 8) + "px");
    setClass(this.root, "mirror", mirror);
    const hx = mirror ? W * 0.78 : W * 0.2;
    this.joyHint.style.left = hx + "px";
    this.joyHint.style.top = H * 0.68 + "px";
  }

  reset(run: Run) {
    this.lastHp = -1;
    this.lagHp = 1;
    this.bossLagV = 1;
    this.lastAnn = "";
    for (const ts of this.tlist) ts.el.remove();
    this.tlist = [];
    const sk = getSkin(run.player.skin.id);
    const u = run.player.ult;
    this.ultBox.style.display = u ? "" : "none";
    if (u) {
      this.ultIco.innerHTML = icon(u.icon || "star", 26, rgbCss(u.color));
      this.ultBox.style.setProperty("--uc", rgbCss(u.color));
    }
    this.root.style.setProperty("--skin", rgbCss(sk.color));
    this.ann.className = "announce";
    this.record.className = "rec-flash";
    this.update(run, 1, true);
  }

  toast(text: string, color = "#fff", dur = 3) {
    const el = h("div", "toast");
    el.textContent = text;
    el.style.setProperty("--c", color);
    this.toasts.prepend(el);
    this.tlist.push({ el, t: dur });
    while (this.tlist.length > 3) this.tlist.shift()!.el.remove();
  }

  /** Her kare çağrılır; DOM'a ~20 Hz yazar. Joystick her kare. */
  update(run: Run, dt: number, force = false) {
    const inp = this.input;
    // joystick görselleri (her kare, yalnız transform)
    if (inp.joyActive) {
      setStyle(this.joyBase, "display", "block");
      this.joyBase.style.transform = `translate(${inp.joyBaseX}px,${inp.joyBaseY}px)`;
      const kx = Math.max(-1, Math.min(1, (inp.joyX - inp.joyBaseX) / inp.joyR)) * inp.joyR;
      const ky = Math.max(-1, Math.min(1, (inp.joyY - inp.joyBaseY) / inp.joyR)) * inp.joyR;
      const l = Math.hypot(kx, ky), m = l > inp.joyR ? inp.joyR / l : 1;
      this.joyKnob.style.transform = `translate(${kx * m}px,${ky * m}px)`;
    } else setStyle(this.joyBase, "display", "none");
    if (inp.aimStickActive && inp.aimActive) {
      setStyle(this.aimBase, "display", "block");
      this.aimBase.style.transform = `translate(${inp.aimBaseX}px,${inp.aimBaseY}px)`;
      this.aimKnob.style.transform = `translate(${inp.ax * 40}px,${inp.ay * 40}px)`;
    } else setStyle(this.aimBase, "display", "none");
    this.hintTime = Math.max(0, this.hintTime - dt);
    setClass(this.joyHint, "show", this.hintTime > 0 && !inp.joyActive);

    // ekran uyarı / kayıt
    const p = run.player;
    for (const ts of this.tlist) {
      ts.t -= dt;
      if (ts.t <= 0.35) ts.el.classList.add("out");
    }
    while (this.tlist.length && this.tlist[0].t <= 0) this.tlist.shift()!.el.remove();

    this.fpsAcc += dt;
    this.fpsN++;
    if (this.showFps && this.fpsAcc >= 0.5) {
      setText(this.fps, Math.round(this.fpsN / this.fpsAcc) + " FPS");
      this.fpsAcc = 0;
      this.fpsN = 0;
    }
    setStyle(this.fps, "display", this.showFps ? "block" : "none");

    this.acc += dt;
    // can çubuğu gecikmeli iz (her kare yumuşak)
    const hpF = Math.max(0, Math.min(1, p.hp / Math.max(1, p.max_hp)));
    this.lagHp = this.lagHp > hpF ? Math.max(hpF, this.lagHp - dt * 0.6) : hpF;
    if (this.acc < 0.05 && !force) return;
    this.acc = 0;

    setStyle(this.hpFill, "transform", `scaleX(${hpF})`);
    setStyle(this.hpLag, "transform", `scaleX(${this.lagHp})`);
    setText(this.hpText, `${Math.ceil(Math.max(0, p.hp))} / ${Math.round(p.max_hp)}`);
    setClass(this.root, "lowhp", hpF < 0.3 && p.alive);
    if (this.lastHp >= 0 && p.hp < this.lastHp - 0.5) {
      this.hpFill.parentElement!.classList.remove("hit");
      void this.hpFill.offsetWidth;
      this.hpFill.parentElement!.classList.add("hit");
    }
    this.lastHp = p.hp;
    const xpF = Math.max(0, Math.min(1, p.xp / Math.max(1, p.xp_to_next)));
    setStyle(this.xpFill, "transform", `scaleX(${xpF})`);
    setText(this.lvText, t("c.lv", p.level));
    // kalkan yükleri
    const sc = Math.min(8, p.shield_charges | 0);
    if ((this.shieldRow as any)._n !== sc) {
      (this.shieldRow as any)._n = sc;
      this.shieldRow.innerHTML = sc > 0 ? icon("shield", 16, "#8fd0ff").repeat(sc) : "";
    }
    // durumlar
    let st = "";
    if (p.burn_t > 0) st += icon("flame", 16, "#ff8a3c");
    if (p.poison_t > 0) st += icon("drop", 16, "#9be25a");
    if (p.slow_t > 0) st += icon("snow", 16, "#9fd8ff");
    if (p.wound > 0) st += `<span class="wound">${t("hud.wound", Math.round(p.wound * 100))}</span>`;
    if ((this.status as any)._v !== st) {
      (this.status as any)._v = st;
      this.status.innerHTML = st;
    }
    // ülti bekleme halkası
    if (p.ult) {
      const f = p.ult_cd > 0 ? 1 - p.ult_timer / p.ult_cd : 1;
      setStyle(this.ultBox, "--p", (f * 100).toFixed(1) + "%");
      setClass(this.ultBox, "ready", f >= 1);
    }

    // dalga
    const w = run.waves;
    const hell = run.biome === "hell";
    setText(this.waveText, hell ? t("hud.hell_wave", w.wave) : t("hud.wave", w.wave));
    if (run.bosses.length) {
      setText(this.waveSub, t("hud.boss_fight"));
      setStyle(this.waveBar, "transform", "scaleX(1)");
      setClass(this.waveText.parentElement!, "boss", true);
    } else {
      setClass(this.waveText.parentElement!, "boss", false);
      setText(this.waveSub, fmtTime(run.runTime));
      setStyle(this.waveBar, "transform", `scaleX(${Math.max(0, Math.min(1, w.progress()))})`);
    }
    // patron çubuğu
    if (run.bosses.length) {
      let hp = 0, mx = 0;
      for (const b of run.bosses) {
        hp += Math.max(0, b.hp);
        mx += b.max_hp;
      }
      const f = mx > 0 ? hp / mx : 0;
      this.bossLagV = this.bossLagV > f ? Math.max(f, this.bossLagV - 0.02) : f;
      const b0 = run.bosses[0];
      setText(this.bossName, run.bosses.length > 1 ? `${b0.name} ×${run.bosses.length}` : b0.name);
      setStyle(this.bossWrap, "display", "block");
      setStyle(this.bossFill, "transform", `scaleX(${f})`);
      setStyle(this.bossLag, "transform", `scaleX(${this.bossLagV})`);
      setStyle(this.bossWrap, "--bc", rgbCss(b0.color));
    } else {
      setStyle(this.bossWrap, "display", "none");
      this.bossLagV = 1;
    }
    // kaynaklar
    setText(this.goldText, short(run.gold));
    setText(this.killText, short(run.kills));
    setText(this.scoreText, short(run.score));
    const cm = run.combo.multiplier();
    if (run.combo.count >= 10) {
      setStyle(this.combo, "display", "block");
      setText(this.combo, `${t("hud.combo")} ${run.combo.count}  ×${cm.toFixed(1)}`);
    } else setStyle(this.combo, "display", "none");

    // duyuru
    if (w.announceTimer > 0 && w.announceText) {
      if (w.announceText !== this.lastAnn) {
        this.lastAnn = w.announceText;
        this.ann.textContent = w.announceText;
        this.ann.className = "announce";
        void this.ann.offsetWidth;
        this.ann.className = "announce show" + (run.bosses.length || /BOSS|PATRON|JEFE|БОСС/i.test(w.announceText) ? " danger" : "");
      }
    } else if (this.lastAnn) {
      this.lastAnn = "";
      this.ann.className = "announce";
    }
    // rekor
    const rec = run.recordFlash >= 0;
    if (rec && !this.record.classList.contains("show")) {
      this.record.textContent = t("hud.record");
      this.record.classList.add("show");
    } else if (!rec) this.record.classList.remove("show");

    // düğmeler
    const dcd = p.dash_cd_timer > 0 ? p.dash_cd_timer / Math.max(0.1, p.effDashCd()) : 0;
    const bcd = p.bonk_timer > 0 ? p.bonk_timer / Math.max(0.1, p.effBonkCd()) : 0;
    this.setBtn("dash", dcd);
    this.setBtn("bonk", bcd);
    const portal = !!(run.hellPortal && p.alive && run.hellPortal.inRange(p));
    const ub = inp.btn("use");
    if (ub) ub.visible = portal;
    setStyle(this.btnEls.use, "display", portal ? "flex" : "none");
  }

  private setBtn(id: string, cd: number) {
    const el = this.btnEls[id];
    const b = this.input.btn(id);
    setStyle(el, "--cd", (Math.max(0, Math.min(1, cd)) * 100).toFixed(1) + "%");
    setClass(el, "cooling", cd > 0);
    setClass(el, "pressed", !!b?.pressed);
  }
}
