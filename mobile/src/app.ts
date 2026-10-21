/**
 * Uygulama: açılış, menü ⇄ koşu geçişleri, oyun döngüsü, ayarlar,
 * arka plana alma, Android geri tuşu.
 */
import "@fontsource/rubik/400.css";
import "@fontsource/rubik/600.css";
import "@fontsource/rubik/800.css";
import "@fontsource/lilita-one/400.css";
import { Application, Container } from "pixi.js";
import { audio, sfx } from "./core/audio";
import { setLang, detectLang, t } from "./core/i18n";
import { Input } from "./core/input";
import { nativeSetup, hideSplash, setHaptics, haptic, isNative } from "./core/native";
import { rgbCss } from "./core/util";
import { FX, installFonts } from "./game/fx";
import { Run, RunInput } from "./game/run";
import { Save } from "./game/save";
import { ACH_BY_ID, WEAPON_BY_KEY, getSkin } from "./game/data";
import * as B from "./game/balance";
import { WorldRenderer } from "./render/renderer";
import { MenuScene } from "./render/menuscene";
import { Hud } from "./ui/hud";
import { Menus } from "./ui/menus";
import { Layer, showLevelUp, showShop, showPause, showGameOver } from "./ui/overlays";
import { online } from "./net/online";

type Overlay = "none" | "levelup" | "shop" | "pause" | "gameover" | "settings";

class Game {
  app = new Application();
  save = new Save();
  input!: Input;
  renderer!: WorldRenderer;
  menuScene = new MenuScene();
  hud!: Hud;
  menus!: Menus;
  ui = document.getElementById("ui")!;
  layer = document.createElement("div");
  run: Run | null = null;
  state: "boot" | "menu" | "run" = "boot";
  overlay: Overlay = "none";
  overlayLayer: Layer | null = null;
  levelUpCtl: ReturnType<typeof showLevelUp> | null = null;
  deathT = 0;
  gameRoot = new Container();
  private lastTheme = "stone";
  private lastDiff: "normal" | "hard" | "nightmare" = "normal";
  private inp: RunInput = { mx: 0, my: 0, aimX: 0, aimY: 0, aimManual: false, fire: false, dash: false, bonk: false, use: false };
  private bgPaused = false;

  async boot() {
    const bar = document.querySelector("#boot .boot-bar i") as HTMLElement | null;
    const prog = (f: number) => bar && (bar.style.width = Math.round(f * 100) + "%");
    prog(0.05);
    await this.save.load();
    const st = this.save.data.settings;
    if (!st.lang) st.lang = detectLang();
    setLang(st.lang);
    prog(0.1);
    // yazı tipleri hazır olmadan bitmap yazı kurulmasın
    try {
      await Promise.race([
        Promise.all([document.fonts.load("800 40px Rubik"), document.fonts.load("400 40px 'Lilita One'"), document.fonts.load("400 16px Rubik")]),
        new Promise((r) => setTimeout(r, 2500)),
      ]);
    } catch {}
    installFonts();
    prog(0.2);
    const dpr = window.devicePixelRatio || 1;
    await this.app.init({
      resizeTo: window,
      background: "#0b0d18",
      antialias: false,
      autoDensity: true,
      resolution: Math.min(dpr, st.quality ? 2 : 1.5),
      powerPreference: "high-performance",
      preference: "webgl",
      hello: false,
    } as any);
    document.getElementById("game")!.appendChild(this.app.canvas);
    this.app.stage.addChild(this.menuScene.root, this.gameRoot);
    this.renderer = new WorldRenderer(this.app);
    this.gameRoot.addChild(this.renderer.root);
    this.gameRoot.visible = false;
    this.input = new Input(this.app.canvas);
    this.layer.className = "ui-layer";
    this.ui.append(this.layer);
    this.hud = new Hud(this.input, { pause: () => this.openPause(), shop: () => this.openShop() });
    this.hud.root.style.display = "none";
    this.ui.prepend(this.hud.root);
    this.menus = new Menus(this.layer, this.save, {
      start: (th, d) => this.startRun(th, d),
      settingsChanged: () => this.applySettings(),
      langChanged: () => this.onLangChanged(),
      previewTheme: (th) => this.menuScene.setTheme(th),
    });
    this.save.onAch = (id) => this.onAchievement(id);
    prog(0.3);
    // sesler: önceden hazırlanır (oyun sırasında hiç sentez yok)
    audio.init();
    await audio.renderAll((f) => prog(0.3 + f * 0.6));
    audio.preloadMusic(["menu", "arena"]);
    this.applySettings();
    prog(1);
    this.save.refreshUnlocks();
    this.save.checkStatAchs();
    await nativeSetup({
      onPause: () => this.onAppPause(),
      onResume: () => this.onAppResume(),
      onBack: () => this.onBack(),
    });
    window.addEventListener("resize", () => this.onResize());
    window.addEventListener("orientationchange", () => setTimeout(() => this.onResize(), 250));
    window.addEventListener("keydown", (e) => {
      if (e.code === "Escape" && this.state === "menu") this.onBack();
    });
    this.app.ticker.maxFPS = 60;
    this.app.ticker.add((tk) => this.frame(tk.deltaMS / 1000));
    this.toMenu();
    this.onResize();
    online.init(this.save);
    const boot = document.getElementById("boot");
    if (boot) {
      boot.classList.add("hide");
      setTimeout(() => boot.remove(), 450);
    }
    hideSplash();
    if (!this.save.data.tutorialDone) {
      setTimeout(() => {
        if (this.state === "menu")
          this.menus.showHowTo(() => {
            this.save.data.tutorialDone = true;
            this.save.persist();
          });
      }, 500);
    }
  }

  applySettings() {
    const st = this.save.data.settings;
    audio.setVolumes(st.sfx, st.music);
    setHaptics(st.haptics);
    FX.shakeOn = st.shake;
    this.renderer.viewShort = st.zoom;
    this.renderer.quality = st.quality ? 1 : 0.6;
    if (this.run) {
      this.run.fx.showDamage = st.dmgNumbers;
      this.run.fx.quality = st.quality ? 1 : 0.55;
    }
    this.hud.showFps = st.fpsCounter;
    if (this.hud.leftHanded !== st.leftHanded) {
      this.hud.leftHanded = st.leftHanded;
      this.hud.layout();
    }
    this.app.ticker.maxFPS = 60;
  }

  onLangChanged() {
    // HUD metinleri yeniden kurulsun
    const old = this.hud.root;
    this.hud = new Hud(this.input, { pause: () => this.openPause(), shop: () => this.openShop() });
    this.hud.leftHanded = this.save.data.settings.leftHanded;
    this.hud.showFps = this.save.data.settings.fpsCounter;
    this.hud.root.style.display = old.style.display;
    old.replaceWith(this.hud.root);
    this.hud.layout();
  }

  onResize() {
    const w = window.innerWidth, h = window.innerHeight;
    this.menuScene.resize(w, h);
    this.renderer.layout(this.run);
    this.hud.layout();
    document.body.classList.toggle("portrait", h > w);
  }

  // ------------------------------------------------------------------
  toMenu() {
    this.closeOverlay();
    this.state = "menu";
    if (this.run) {
      this.renderer.reset();
      this.run = null;
    }
    this.input.enabled = false;
    this.input.reset();
    this.gameRoot.visible = false;
    this.menuScene.root.visible = true;
    this.menuScene.setTheme(this.save.mapUnlocked(this.save.data.settings.lastMap) ? this.save.data.settings.lastMap : "stone");
    this.menuScene.setHero(this.save.skinId());
    this.hud.root.style.display = "none";
    this.menus.showMain();
    audio.playMusic("menu");
  }

  startRun(theme: string, diff: "normal" | "hard" | "nightmare") {
    this.lastTheme = theme;
    this.lastDiff = diff;
    this.menus.hideMain();
    this.closeOverlay();
    if (this.run) this.renderer.reset();
    const s = this.save;
    const run = new Run(s, s.skinId(), diff, theme, []);
    this.run = run;
    run.fx.showDamage = s.data.settings.dmgNumbers;
    run.fx.quality = s.data.settings.quality ? 1 : 0.55;
    run.onEvent = (ev, data) => this.onRunEvent(ev, data);
    this.renderer.layout(run);
    run.updateCamera(0, true);
    this.gameRoot.visible = true;
    this.menuScene.root.visible = false;
    this.state = "run";
    this.deathT = 0;
    this.input.reset();
    this.input.enabled = true;
    this.hud.root.style.display = "";
    this.hud.reset(run);
    this.hud.hintTime = s.stat("runs") < 3 ? 6 : 0;
    audio.playMusic(run.musicName());
    sfx("portal", 0.7);
    haptic("medium");
  }

  // ------------------------------------------------------------------
  // Pencereler
  // ------------------------------------------------------------------
  closeOverlay() {
    if (this.overlayLayer) this.overlayLayer.close();
    this.overlayLayer = null;
    this.levelUpCtl = null;
    this.overlay = "none";
    this.hud.root.classList.remove("covered");
    if (this.state === "run") {
      this.input.enabled = true;
      this.input.reset();
    }
  }

  private setOverlay(o: Overlay) {
    this.overlay = o;
    this.hud.root.classList.add("covered");
    this.input.enabled = false;
    this.input.reset();
  }

  openPause() {
    if (!this.run || this.overlay !== "none" || this.run.gameOver) return;
    this.setOverlay("pause");
    audio.duck(0.45, 0.2);
    this.overlayLayer = showPause(this.layer, this.run, {
      resume: () => this.resume(),
      restart: () => {
        this.finishRun(false);
        this.startRun(this.lastTheme, this.lastDiff);
      },
      quit: () => {
        this.finishRun(true);
      },
      settings: () => {
        const L = this.menus.showSettings();
        void L;
      },
    });
  }

  resume() {
    this.overlayLayer = null;
    this.overlay = "none";
    this.hud.root.classList.remove("covered");
    this.input.enabled = true;
    this.input.reset();
    audio.duck(1, 0.2);
  }

  openShop() {
    if (!this.run || this.overlay !== "none" || this.run.gameOver) return;
    this.setOverlay("shop");
    audio.duck(0.5, 0.2);
    const ctl = showShop(this.layer, this.run, () => this.resume());
    this.overlayLayer = null;
    (this as any)._shopCtl = ctl;
  }

  openLevelUp() {
    if (!this.run) return;
    this.setOverlay("levelup");
    this.levelUpCtl = showLevelUp(this.layer, this.run, () => {
      this.levelUpCtl = null;
      this.resume();
    });
  }

  /** Koşuyu bitirir: istatistikler yazılır. showResults=true ise sonuç ekranı. */
  finishRun(showResults: boolean) {
    const run = this.run;
    if (!run) return;
    if ((run as any)._committed) return;
    (run as any)._committed = true;
    const s = run.summary();
    const res = this.save.commitRun(s, run.mapStatValues());
    online.submitRun(s);
    if (!showResults) return;
    this.closeOverlay();
    this.setOverlay("gameover");
    this.hud.root.style.display = "none";
    audio.playMusic("menu", 2);
    this.overlayLayer = showGameOver(this.layer, run, s, res, this.save, {
      retry: () => {
        this.overlayLayer = null;
        this.startRun(this.lastTheme, this.lastDiff);
      },
      menu: () => {
        this.overlayLayer = null;
        this.toMenu();
      },
    });
  }

  // ------------------------------------------------------------------
  onRunEvent(ev: string, data?: any) {
    const hud = this.hud;
    switch (ev) {
      case "toast":
        hud.toast(data.text, rgbCss(data.color));
        break;
      case "ult":
        hud.toast(data.name, rgbCss(data.color), 2);
        haptic("medium");
        break;
      case "chest": {
        const w = WEAPON_BY_KEY[data?.key];
        if (w) hud.toast(`${t(`w.${w.key}.name`)} ↑  ${t("rar." + (data.tier || 0))}`, rgbCss(B.RARITY_COLORS[data.tier || 0]), 3);
        break;
      }
      case "map_cleared":
        hud.toast(t("map.doom"), "#ff8080", 4);
        break;
      case "biome":
        hud.toast(t("fx.welcome_hell"), "#ff7050", 4);
        haptic("heavy");
        break;
      case "wave":
        haptic("light");
        break;
      case "boss":
        haptic("heavy");
        break;
      case "death":
        this.deathT = 1.6;
        this.input.enabled = false;
        break;
    }
  }

  onAchievement(id: string) {
    const a = ACH_BY_ID[id];
    if (!a) return;
    const msg = `${t("ac.toast", t(`a.${id}.name`))}  +${a.gems}💎`;
    if (this.state === "run") this.hud.toast(msg, "#ffd34d", 3.5);
    sfx("ach", 0.9);
    online.achievement(id);
  }

  // ------------------------------------------------------------------
  onAppPause() {
    this.bgPaused = true;
    audio.appPause();
    this.save.persist(true);
    if (this.state === "run" && this.overlay === "none" && this.run && !this.run.gameOver) this.openPause();
    this.app.ticker.stop();
  }
  onAppResume() {
    this.bgPaused = false;
    audio.appResume();
    this.app.ticker.start();
    this.input.reset();
  }

  onBack() {
    if (this.menus.back()) return;
    if (this.state === "run") {
      if (this.overlay === "none") this.openPause();
      else if (this.overlay === "pause") {
        this.overlayLayer?.close(() => this.resume());
      } else if (this.overlay === "shop") {
        (this as any)._shopCtl?.close();
      }
      return;
    }
    if (this.state === "menu") {
      // ana menüde: çıkış onayı (Android)
      if (isNative) this.menus.showSettings();
    }
  }

  // ------------------------------------------------------------------
  // Kare
  // ------------------------------------------------------------------
  frame(rawDt: number) {
    if (this.bgPaused) return;
    const dt = Math.min(0.05, Math.max(0, rawDt));
    if (this.state === "menu") {
      this.menuScene.update(dt);
      return;
    }
    const run = this.run;
    if (!run) return;
    const inp = this.input;
    inp.pollKeyboard();
    // klavye kısayolları
    if (inp.take("pause") && this.overlay === "none") this.openPause();
    if (inp.take("shop") && this.overlay === "none") this.openShop();
    if (this.overlay === "levelup" && this.levelUpCtl) {
      for (const [k, i] of [["c1", 0], ["c2", 1], ["c3", 2]] as [string, number][]) if (inp.take(k)) this.levelUpCtl.pick(i);
      if (inp.take("reroll")) this.levelUpCtl.reroll();
    }
    const paused = this.overlay !== "none";
    if (!paused) {
      const ri = this.inp;
      ri.mx = inp.mx;
      ri.my = inp.my;
      const p = run.player;
      if (inp.usingMouse && inp.mouseDown) {
        const [sx, sy] = this.renderer.worldToScreen(run, p.x, p.y);
        const dx = inp.mouseX - sx, dy = inp.mouseY - sy;
        const l = Math.hypot(dx, dy) || 1;
        ri.aimManual = true;
        ri.aimX = dx / l;
        ri.aimY = dy / l;
      } else if (inp.aimActive) {
        ri.aimManual = true;
        ri.aimX = inp.ax;
        ri.aimY = inp.ay;
      } else ri.aimManual = false;
      const auto = this.save.data.settings.autoAim;
      ri.fire = ri.aimManual || (auto && run.autoAimTarget() !== null);
      ri.dash = inp.take("dash");
      ri.bonk = inp.take("bonk");
      ri.use = inp.take("use") || inp.isHeld("use");
      // uzun karede iki adım (çarpışmalar kaçmasın)
      const steps = dt > 1 / 40 ? 2 : 1;
      const sdt = dt / steps;
      for (let i = 0; i < steps; i++) {
        run.update(sdt, ri);
        ri.dash = ri.bonk = ri.use = false;
      }
      if (run.gameOver) {
        this.deathT -= dt;
        if (this.deathT <= 0) this.finishRun(true);
      } else if (run.pendingLevelups > 0 && p.alive) this.openLevelUp();
    } else if (this.overlay !== "gameover") {
      // durakken de efektler hafifçe akmasın; yalnız çiz
    }
    this.renderer.render(run, paused ? 0 : dt);
    if (this.overlay !== "gameover") this.hud.update(run, dt);
  }
}

export async function startGame() {
  const g = new Game();
  (window as any).__game = g;
  try {
    await g.boot();
  } catch (e) {
    console.error(e);
    const b = document.getElementById("boot");
    if (b) b.insertAdjacentHTML("beforeend", `<div class="boot-err">${String(e)}</div>`);
  }
}

void getSkin;
