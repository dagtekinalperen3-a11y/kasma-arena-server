/**
 * Oyun dünyasının çizimi. Simülasyon (game/*) Pixi'den habersizdir; bu sınıf
 * her karede koşunun listelerini dolaşıp havuzdan alınmış sprite'ları
 * günceller. Kullanılmayan sprite'lar havuza döner (nesne yaratılmaz).
 */
import { Application, Container, Graphics, Sprite, Texture, TilingSprite } from "pixi.js";
import { Run, Target } from "../game/run";
import { Enemy } from "../game/enemy";
import { Boss } from "../game/boss";
import { enemyTextures } from "./sprites";
import { heroBodyTex, heroEyesTex, pupilTex, weaponTex } from "./art_player";
import * as A from "./art_misc";
import { floorTex, scatterDecos, Deco, wallTex } from "./world";
import { shadowTex, softCircle, squareTex } from "./tex";
import { RGB, rgbToHex, clamp, TAU, lighten, hueCol, mixCol } from "../core/util";
import { GD } from "../game/data";
import { bookSlotPos } from "../game/weapons";
import * as Bal from "../game/balance";

const C = GD;

class Pool<T extends Container> {
  free: T[] = [];
  used = new Set<T>();
  constructor(private make: () => T, private parent: Container) {}
  get(): T {
    const o = this.free.pop() || this.make();
    if (!o.parent) this.parent.addChild(o);
    o.visible = true;
    this.used.add(o);
    return o;
  }
  release(o: T) {
    if (!this.used.has(o)) return;
    this.used.delete(o);
    o.visible = false;
    this.free.push(o);
  }
}

interface View {
  pool: Pool<any>;
  obj: any;
  mark: number;
  extra?: any;
}

export class WorldRenderer {
  root = new Container();
  world = new Container();
  floor: TilingSprite;
  decalLayer = new Container();
  shadowLayer = new Container();
  pickupLayer = new Container();
  entityLayer = new Container();
  projLayer = new Container();
  dynBelow = new Graphics();
  dynAbove = new Graphics();
  screenLayer = new Container();
  indicators = new Graphics();
  flash: Sprite;
  vignette: Sprite;
  zoom = 1;
  viewShort = 560;
  frame = 0;
  private views = new Map<any, View>();
  private pools: Record<string, Pool<any>> = {};
  private decos: Deco[] = [];
  private biome = "";
  private walls = new Container();
  // oyuncu
  private pc = new Container();
  private pShadow: Sprite;
  private pBody: Sprite;
  private pEyes: Sprite;
  private pPupils: Sprite[];
  private pWeapon: Sprite;
  private pWeaponKey = "";
  private ghosts: Sprite[] = [];
  private penta: Sprite;
  private books: Sprite[] = [];
  private orbits: Sprite[] = [];
  private t = 0;
  quality = 1;

  constructor(public app: Application) {
    this.floor = new TilingSprite({ texture: Texture.WHITE, width: 10, height: 10 });
    this.world.addChild(this.floor, this.walls, this.decalLayer, this.dynBelow, this.shadowLayer, this.pickupLayer, this.entityLayer, this.projLayer);
    this.entityLayer.sortableChildren = true;
    this.root.addChild(this.world, this.screenLayer);
    this.flash = new Sprite(Texture.WHITE);
    this.flash.alpha = 0;
    this.vignette = new Sprite(this.vignetteTex());
    this.vignette.alpha = 0;
    this.screenLayer.addChild(this.indicators, this.vignette, this.flash);
    this.pShadow = new Sprite(shadowTex());
    this.pShadow.anchor.set(0.5);
    this.pBody = new Sprite(Texture.EMPTY);
    this.pBody.anchor.set(0.5, 54 / 96);
    this.pEyes = new Sprite(heroEyesTex());
    this.pEyes.anchor.set(0.5);
    this.pPupils = [new Sprite(pupilTex()), new Sprite(pupilTex())];
    for (const s of this.pPupils) s.anchor.set(0.5);
    this.pWeapon = new Sprite(Texture.EMPTY);
    this.pc.addChild(this.pBody, this.pEyes, ...this.pPupils, this.pWeapon);
    this.penta = new Sprite(A.pentagramTex());
    this.penta.anchor.set(0.5);
    this.penta.visible = false;
    this.decalLayer.addChild(this.penta);
    this.shadowLayer.addChild(this.pShadow);
  }

  private vignetteTex() {
    const cv = document.createElement("canvas");
    cv.width = cv.height = 256;
    const g = cv.getContext("2d")!;
    const gr = g.createRadialGradient(128, 128, 60, 128, 128, 180);
    gr.addColorStop(0, "rgba(255,0,0,0)");
    gr.addColorStop(1, "rgba(255,30,40,0.85)");
    g.fillStyle = gr;
    g.fillRect(0, 0, 256, 256);
    return Texture.from(cv);
  }

  private pool(kind: string, make: () => any, parent: Container) {
    return (this.pools[kind] ||= new Pool(make, parent));
  }

  private view(obj: any, kind: string, make: () => any, parent: Container): View {
    let v = this.views.get(obj);
    if (!v) {
      const pool = this.pool(kind, make, parent);
      v = { pool, obj: pool.get(), mark: this.frame };
      this.views.set(obj, v);
    }
    v.mark = this.frame;
    return v;
  }

  setBiome(biome: string, W: number, H: number) {
    if (biome === this.biome) return;
    this.biome = biome;
    this.floor.texture = floorTex(biome);
    for (const d of this.decos) d.s.destroy();
    this.decos = scatterDecos(biome, W, H, 1234 + biome.length * 7);
    for (const d of this.decos) {
      if (d.flat) this.decalLayer.addChildAt(d.s, 0);
      else {
        d.s.zIndex = d.y;
        this.entityLayer.addChild(d.s);
      }
    }
    // dünya sınırı duvarları
    this.walls.removeChildren();
    const wt = wallTex(biome);
    const th = 64;
    for (const [x, y, w, h] of [[-th, -th, W + th * 2, th], [-th, H, W + th * 2, th], [-th, 0, th, H], [W, 0, th, H]]) {
      const ts = new TilingSprite({ texture: wt, width: w, height: h });
      ts.position.set(x, y);
      this.walls.addChild(ts);
    }
    const edge = new Graphics();
    edge.rect(0, 0, W, H).stroke({ width: 6, color: 0x000000, alpha: 0.35 });
    this.walls.addChild(edge);
  }

  /** Ekran boyutuna göre yakınlaştırma ve koşunun görüş alanı. */
  layout(run: Run | null) {
    const w = this.app.screen.width, h = this.app.screen.height;
    const short = Math.min(w, h);
    this.zoom = short / this.viewShort;
    if (run) {
      run.viewW = w / this.zoom;
      run.viewH = h / this.zoom;
    }
    this.flash.width = w;
    this.flash.height = h;
    this.vignette.width = w;
    this.vignette.height = h;
  }

  render(run: Run, dt: number) {
    this.t += dt;
    this.frame++;
    const fx = run.fx;
    if (!fx.addLayer.parent) {
      this.world.addChild(fx.waveLayer, fx.normLayer, fx.addLayer, fx.boltLayer, this.dynAbove, fx.textLayer);
    }
    this.setBiome(run.biome === "hell" ? "hell" : run.theme, run.W, run.H);
    this.layout(run);
    const z = this.zoom;
    let sx = 0, sy = 0;
    if (fx.shakeT > 0 && fx.shakeAmt > 0) {
      const a = fx.shakeAmt * Math.min(1, fx.shakeT * 4);
      sx = (Math.random() * 2 - 1) * a;
      sy = (Math.random() * 2 - 1) * a;
    }
    const camX = run.camX + sx, camY = run.camY + sy;
    this.world.scale.set(z);
    this.world.position.set(Math.round(-camX * z), Math.round(-camY * z));
    // zemin: yalnızca görüş alanı kadar
    this.floor.position.set(camX - 64, camY - 64);
    this.floor.width = run.viewW + 128;
    this.floor.height = run.viewH + 128;
    this.floor.tilePosition.set(-(camX - 64), -(camY - 64));
    // dekor görünürlüğü (kırpma)
    const cl = camX - 200, ct = camY - 200, cr = camX + run.viewW + 200, cb = camY + run.viewH + 260;
    for (const d of this.decos) d.s.visible = d.x > cl && d.x < cr && d.y > ct && d.y < cb;

    const gb = this.dynBelow, ga = this.dynAbove;
    gb.clear();
    ga.clear();

    this.drawPlayer(run);
    this.drawEnemies(run, cl, ct, cr, cb);
    this.drawBosses(run);
    this.drawProjectiles(run, cl, ct, cr, cb);
    this.drawPickups(run, cl, ct, cr, cb);
    this.drawWeaponObjects(run);
    this.drawHazards(run);
    this.drawMisc(run);
    this.sweep();
    this.drawIndicators(run);
    // ekran parlaması
    if (fx.flashA > 0) {
      this.flash.tint = fx.flashCol;
      this.flash.alpha = Math.min(0.55, fx.flashA);
    } else this.flash.alpha = 0;
    const p = run.player;
    const low = p.alive ? clamp(1 - p.hp / p.max_hp, 0, 1) : 1;
    this.vignette.alpha = Math.max(p.hurt_vig * 0.5, low > 0.65 ? (low - 0.65) * 1.2 * (0.7 + 0.3 * Math.sin(this.t * 6)) : 0);
  }

  private sweep() {
    for (const [obj, v] of this.views) {
      if (v.mark !== this.frame) {
        v.pool.release(v.obj);
        const sp = (v as any).shPool as Pool<any> | undefined;
        if (v.extra) for (const e of v.extra) sp ? sp.release(e) : (e.visible = false);
        this.views.delete(obj);
      }
    }
  }

  // ------------------------------------------------------------------
  private drawPlayer(run: Run) {
    const p = run.player;
    if (!this.pc.parent) this.entityLayer.addChild(this.pc);
    const sk = p.skin;
    this.pBody.texture = heroBodyTex(sk);
    const moving = p.speed_now > 20;
    const bob = moving ? Math.sin(p.move_anim) * 1.8 : Math.sin(this.t * 2.2) * 1.0;
    const squash = moving ? 1 + Math.sin(p.move_anim * 2) * 0.03 : 1 + Math.sin(this.t * 2.2) * 0.015;
    this.pc.position.set(p.x, p.y + bob);
    this.pc.zIndex = p.y;
    this.pc.visible = p.alive || run.gameOver;
    const flash = p.hit_flash > 0 && Math.floor(p.hit_flash * 30) % 2 === 0;
    const sc = 16 / 20 / 3; // tuval 3x çözünürlükte, görsel r=20 -> dünya r=16
    void sc;
    const k = p.radius / 20;
    this.pBody.scale.set(k * (1 / squash), k * squash);
    this.pBody.tint = flash ? 0xff8080 : sk.id === "prism" ? rgbToHex(lighten(hueCol(this.t * 0.35), 0.1)) : 0xffffff;
    let alpha = 1;
    if (p.invis_t > 0) alpha = 0.35;
    else if (p.invuln > 0 && p.dash_time <= 0) alpha = 0.6 + 0.4 * Math.sin(this.t * 30);
    this.pc.alpha = alpha;
    const [ax, ay] = p.aim_dir;
    const shadowEyes = sk.id === "shadow" || sk.id === "shadow_hunter";
    this.pEyes.texture = heroEyesTex(shadowEyes);
    this.pEyes.scale.set(k * 0.9);
    this.pEyes.position.set(ax * 3.5, -3 + ay * 2.5);
    for (let i = 0; i < 2; i++) {
      const pp = this.pPupils[i];
      pp.visible = !shadowEyes;
      pp.scale.set(k * 0.9);
      pp.position.set(this.pEyes.x + (i ? 6.2 : -6.2) * k * 0.9 + ax * 2, this.pEyes.y + ay * 2);
    }
    // silah
    const wk = sk.weapon + sk.id;
    if (wk !== this.pWeaponKey) {
      this.pWeaponKey = wk;
      const wt = weaponTex(sk.weapon, sk.color as RGB, sk.accent as RGB);
      this.pWeapon.texture = wt.tex;
      this.pWeapon.anchor.set(wt.ax, wt.ay);
    }
    const ang = Math.atan2(ay, ax);
    const rec = p.recoil * 4;
    this.pWeapon.position.set(ax * (p.radius * 0.55 - rec), ay * (p.radius * 0.55 - rec) + 3);
    this.pWeapon.rotation = ang;
    this.pWeapon.scale.set(0.85, ax < 0 ? -0.85 : 0.85);
    // silah arkada mı önde mi
    const behind = ay < -0.35;
    const wi = this.pc.getChildIndex(this.pWeapon);
    if (behind && wi !== 0) this.pc.setChildIndex(this.pWeapon, 0);
    else if (!behind && wi !== this.pc.children.length - 1) this.pc.setChildIndex(this.pWeapon, this.pc.children.length - 1);
    // gölge
    this.pShadow.position.set(p.x, p.y + p.radius * 0.85);
    this.pShadow.scale.set((p.radius * 2.4) / 64, (p.radius * 2.4) / 64);
    this.pShadow.visible = this.pc.visible;
    // dash izleri
    while (this.ghosts.length < p.ghosts.length) {
      const s = new Sprite(Texture.EMPTY);
      s.anchor.set(0.5, 54 / 96);
      s.blendMode = "add";
      this.entityLayer.addChild(s);
      this.ghosts.push(s);
    }
    for (let i = 0; i < this.ghosts.length; i++) {
      const s = this.ghosts[i];
      const g = p.ghosts[i];
      if (!g) {
        s.visible = false;
        continue;
      }
      s.visible = true;
      s.texture = this.pBody.texture;
      s.position.set(g[0], g[1]);
      s.zIndex = g[1] - 1;
      s.scale.set(k);
      s.tint = rgbToHex(sk.accent);
      s.alpha = clamp(g[2] / 0.3, 0, 1) * 0.45;
    }
    // durum halkaları (dyn)
    const ga = this.dynAbove;
    if (p.shield_charges > 0) ga.circle(p.x, p.y, p.radius + 9).stroke({ width: 2, color: 0xa0c8ff, alpha: 0.85 });
    if (p.burn_t > 0) ga.circle(p.x, p.y, p.radius + 6).stroke({ width: 2, color: 0xff8232, alpha: 0.6 + 0.3 * Math.sin(this.t * 9) });
    if (p.poison_t > 0) ga.circle(p.x, p.y, p.radius + 12).stroke({ width: 1.5, color: 0x82e664, alpha: 0.8 });
    if (p.slow_t > 0) ga.circle(p.x, p.y, p.radius + 15).stroke({ width: 1.5, color: 0x8cc8ff, alpha: 0.8 });
    if (p.bonk_timer > 0) {
      const f = 1 - clamp(p.bonk_timer / p.effBonkCd(), 0, 1);
      if (f > 0.02) ga.arc(p.x, p.y, p.radius + 11, -Math.PI / 2, -Math.PI / 2 + TAU * f).stroke({ width: 3, color: 0xf09650, alpha: 0.9 });
    }
    // pentagram
    const plvl = p.weapons.pentagram || 0;
    this.penta.visible = plvl > 0 && p.alive;
    if (plvl > 0) {
      const r = Bal.pentaRadius(plvl);
      this.penta.position.set(p.x, p.y);
      this.penta.scale.set(r / 120);
      this.penta.rotation = p.penta_angle;
    }
    // kalkan kitapları
    const blvl = p.weapons.book || 0;
    const nb = blvl > 0 ? Bal.weaponCount(blvl) : 0;
    while (this.books.length < nb) {
      const s = new Sprite(A.shieldBookTex(true));
      s.anchor.set(0.5);
      this.entityLayer.addChild(s);
      this.books.push(s);
    }
    for (let i = 0; i < this.books.length; i++) {
      const s = this.books[i];
      if (i >= nb || !p.alive) {
        s.visible = false;
        continue;
      }
      const [bx, by, a] = bookSlotPos(p, i, nb);
      s.visible = true;
      s.position.set(bx, by);
      s.zIndex = by;
      const charged = !(p.book_charges[i] > 0);
      s.texture = A.shieldBookTex(charged);
      const depth = (Math.sin(a) + 1) * 0.5;
      s.scale.set(0.55 + 0.2 * depth);
    }
    // yörünge topları
    const no = p.orbit_level + p.extra_orbit;
    while (this.orbits.length < no) {
      const s = new Sprite(A.projTex("fireball", [255, 140, 40], [255, 220, 120]));
      s.anchor.set(0.58, 0.5);
      this.entityLayer.addChild(s);
      this.orbits.push(s);
    }
    for (let i = 0; i < this.orbits.length; i++) {
      const s = this.orbits[i];
      if (i >= no || !p.alive) {
        s.visible = false;
        continue;
      }
      const a = p.orbit_angle + (i * TAU) / no;
      s.visible = true;
      s.position.set(p.x + Math.cos(a) * 58, p.y + Math.sin(a) * 58);
      s.rotation = a + Math.PI / 2;
      s.zIndex = s.y;
    }
  }

  private drawEnemies(run: Run, cl: number, ct: number, cr: number, cb: number) {
    const shadowT = shadowTex();
    for (const e of run.enemies) {
      if (!e.alive) continue;
      if (e.x < cl || e.x > cr || e.y < ct || e.y > cb) continue;
      const v = this.view(e, "enemy", () => {
        const s = new Sprite(Texture.EMPTY);
        s.anchor.set(0.5);
        return s;
      }, this.entityLayer);
      if (!v.extra) {
        const sh = this.pool("eshadow", () => {
          const s = new Sprite(shadowT);
          s.anchor.set(0.5);
          return s;
        }, this.shadowLayer).get();
        v.extra = [sh];
        (v as any).shPool = this.pools.eshadow;
      }
      const s = v.obj as Sprite;
      const r = e.radius;
      const key = (e as any)._tk;
      if (!key || (e as any)._tc !== e.color) {
        (e as any)._tex = enemyTextures(e.shape, e.color, Math.max(9, Math.round(r)));
        (e as any)._tc = e.color;
        (e as any)._tk = 1;
      }
      const tx = (e as any)._tex as Texture[];
      const flash = e.hitFlash > 0.055;
      s.texture = flash ? tx[2] : tx[Math.floor(e.walk * 1.3) % 2];
      const R = Math.max(9, Math.round(r));
      const base = r / R;
      const spawn = clamp(e.spawnT / 0.3, 0, 1);
      const breathe = 1 + Math.sin(e.walk * 2) * 0.04;
      const face = e.faceX < -0.05 ? -1 : 1;
      s.scale.set(base * spawn * face * (1 / breathe), base * spawn * breathe);
      s.position.set(e.x, e.y - r * 0.15);
      s.zIndex = e.y;
      s.rotation = Math.sin(e.walk) * 0.06;
      let a = 1;
      if (e.phased) a = 0.3;
      s.alpha = a;
      s.tint = e.healFlash > 0 ? 0xa0ffb0 : e.fuse_t > 0 && Math.floor(e.fuse_t * 12) % 2 ? 0xff9a6a : 0xffffff;
      const sh = v.extra[0] as Sprite;
      sh.visible = true;
      sh.position.set(e.x, e.y + r * 0.75);
      sh.scale.set((r * 2.2) / 64, (r * 2.2) / 64);
      // can çubuğu: ağır yaratıklar
      if ((e.kind === "elite" || e.isMini || e.kind === "goblin" || e.kind === "shieldman" || e.kind === "tank") && e.hp < e.max_hp) {
        const w = r * 2, y = e.y - r * 1.55;
        const f = clamp(e.hp / e.max_hp, 0, 1);
        this.dynAbove.rect(e.x - w / 2, y, w, 4).fill({ color: 0x14101c, alpha: 0.85 });
        this.dynAbove.rect(e.x - w / 2, y, w * f, 4).fill({ color: e.isMini ? 0xf6d678 : 0xff5a5a });
      }
      if (e.isMini && e.liveGuards() > 0) this.dynBelow.circle(e.x, e.y, r + 12).stroke({ width: 3, color: 0x96c8fa, alpha: 0.4 + (e.blockFlash > 0 ? 0.5 : 0) });
      if (e.guardOf && e.blockFlash > 0) this.dynAbove.circle(e.x, e.y, r + 6).stroke({ width: 3, color: 0x96c8fa, alpha: 0.9 });
      if (e.fuse_t > 0) this.dynBelow.circle(e.x, e.y, C.KAMIKAZE_RADIUS).fill({ color: 0xff6a2a, alpha: 0.12 + 0.1 * Math.sin(this.t * 20) }).stroke({ width: 2, color: 0xff8a3a, alpha: 0.7 });
      if (e.mutant) this.dynBelow.circle(e.x, e.y + r * 0.5, r * 0.9).fill({ color: 0x78d278, alpha: 0.12 });
    }
  }

  private drawBosses(run: Run) {
    for (const b of run.bosses) {
      if (!b.alive) continue;
      const v = this.view(b, "boss", () => {
        const s = new Sprite(Texture.EMPTY);
        s.anchor.set(0.5);
        return s;
      }, this.entityLayer);
      const s = v.obj as Sprite;
      const R = Math.round(b.radius);
      // yalnız ilk anda kısa bir parlama (sürekli vurulan patron bembeyaz kalmasın)
      const tex = A.bossTex(b.kind, b.color, b.theme, b.hellish, R, b.hitFlash > 0.07 && this.frame % 2 === 0);
      s.texture = tex;
      const spawn = clamp(b.spawnT / 0.6, 0, 1);
      const breathe = 1 + Math.sin(b.gait * 2) * 0.03;
      const face = b.faceX < -0.05 ? -1 : 1;
      s.scale.set(spawn * face / breathe, spawn * breathe);
      s.position.set(b.x, b.y - (b.flyT > 0 ? 30 : 0));
      s.zIndex = b.y;
      s.rotation = Math.sin(b.gait) * 0.04;
      s.alpha = b.isHidden() ? 0.12 : 1;
      s.tint = b.healFlash > 0 ? 0xa0ffb0 : b.enraged ? 0xffd0c8 : 0xffffff;
      const gb = this.dynBelow, ga = this.dynAbove;
      gb.ellipse(b.x, b.y + b.radius * 0.8, b.radius * 1.1, b.radius * 0.35).fill({ color: 0x000000, alpha: 0.35 });
      if (b.aegisHp > 0) ga.circle(b.x, b.y, b.radius + 14).fill({ color: 0x82dcff, alpha: 0.12 }).stroke({ width: 3, color: 0x82dcff, alpha: 0.4 + 0.5 * (b.aegisHp / b.aegisMax) });
      if (b.wardT > 0) ga.circle(b.x, b.y, b.radius + 10).stroke({ width: 4, color: 0xffdc6e, alpha: 0.6 + 0.3 * Math.sin(this.t * 10) });
      if (b.drainT > 0) {
        const p = run.player;
        ga.moveTo(b.x, b.y).lineTo(p.x, p.y).stroke({ width: 4, color: 0xe62846, alpha: 0.7 });
      }
      if (b.pullT > 0) ga.circle(b.x, b.y, 420 * (b.pullT / 0.85)).stroke({ width: 3, color: 0xc882ff, alpha: 0.5 });
      for (const sn of b.snares) {
        const f = 1 - sn[2] / C.SNARE_DELAY;
        gb.circle(sn[0], sn[1], C.SNARE_R).fill({ color: 0x78c850, alpha: 0.12 + 0.2 * f }).stroke({ width: 2, color: 0x96dc5a, alpha: 0.8 });
      }
      // telgraflar
      const tg = b.telegraph;
      if (tg) {
        const [kind, a, bb, c, timer, total] = tg;
        const f = 1 - timer / total;
        const col = rgbToHex(b.trait.color);
        if (kind === "beam") {
          const angs: number[] = Array.isArray(a) ? a : [a];
          for (const an of angs) {
            ga.moveTo(b.x, b.y).lineTo(b.x + Math.cos(an) * 700, b.y + Math.sin(an) * 700).stroke({ width: 2 + 6 * f, color: 0xff5040, alpha: 0.25 + 0.45 * f });
          }
        } else if (kind === "lunge" || kind === "charge") {
          ga.moveTo(b.x, b.y).lineTo(a, bb).stroke({ width: b.radius * 1.6, color: 0xff6040, alpha: 0.12 + 0.2 * f });
        } else if (kind === "breath") {
          const an = a as number;
          ga.moveTo(b.x, b.y).lineTo(b.x + Math.cos(an) * (90 + (7 + b.bossIndex) * 74), b.y + Math.sin(an) * (90 + (7 + b.bossIndex) * 74)).stroke({ width: 110, color: 0xff8a30, alpha: 0.1 + 0.2 * f });
        } else if (kind === "barrage") {
          const an = a as number;
          for (const o of [-0.31, 0.31]) ga.moveTo(b.x, b.y).lineTo(b.x + Math.cos(an + o) * 600, b.y + Math.sin(an + o) * 600).stroke({ width: 2, color: col, alpha: 0.5 * f + 0.2 });
        } else if (kind === "wall" || kind === "firewall") {
          const nx = -Math.sin(c), ny = Math.cos(c);
          const L = kind === "wall" ? (9 + b.bossIndex) * 76 : (7 + b.bossIndex) * 88;
          ga.moveTo(a - nx * L / 2, bb - ny * L / 2).lineTo(a + nx * L / 2, bb + ny * L / 2).stroke({ width: 60, color: col, alpha: 0.12 + 0.2 * f });
        } else if (kind === "slam" || kind === "scythe" || kind === "spore") {
          gb.circle(a, bb, c || 90).fill({ color: 0xff4030, alpha: 0.1 + 0.25 * f }).stroke({ width: 3, color: 0xff6a50, alpha: 0.8 });
          gb.circle(a, bb, (c || 90) * f).fill({ color: 0xff4030, alpha: 0.18 });
        } else if (kind === "cage" || kind === "ring_player") {
          gb.circle(a, bb, c).stroke({ width: 10, color: col, alpha: 0.2 + 0.4 * f });
        } else if (kind === "meteor") {
          gb.circle(a, bb, 210).fill({ color: 0xff8a40, alpha: 0.08 + 0.12 * f }).stroke({ width: 2, color: 0xffa050, alpha: 0.6 });
        } else if (kind === "pull") {
          gb.circle(b.x, b.y, 420 * (1 - f * 0.5)).stroke({ width: 4, color: 0xc882ff, alpha: 0.6 });
        } else if (kind === "hazard_ring") {
          gb.circle(b.x, b.y, 150).stroke({ width: 12, color: col, alpha: 0.15 + 0.3 * f });
        } else if (kind === "wingburst") {
          gb.circle(b.x, b.y, c * f).stroke({ width: 4, color: 0xffa046, alpha: 0.7 });
        }
      }
    }
  }

  private drawProjectiles(run: Run, cl: number, ct: number, cr: number, cb: number) {
    for (const pr of run.playerProjectiles) {
      if (pr.x < cl || pr.x > cr || pr.y < ct || pr.y > cb) continue;
      const v = this.view(pr, "pproj", () => {
        const s = new Sprite(Texture.EMPTY);
        s.anchor.set(28 / 48, 0.5);
        return s;
      }, this.projLayer);
      const s = v.obj as Sprite;
      s.texture = A.projTex(pr.style, pr.color as RGB, pr.accent as RGB);
      s.position.set(pr.x, pr.y);
      s.rotation = pr.style === "star" || pr.style === "web" ? pr.spin : Math.atan2(pr.vy, pr.vx);
      s.scale.set(1.05);
      if (pr.style === "prism") s.tint = rgbToHex(hueCol(pr.spin * 0.1));
      else s.tint = 0xffffff;
    }
    for (const pr of run.enemyProjectiles) {
      if (pr.x < cl || pr.x > cr || pr.y < ct || pr.y > cb) continue;
      const v = this.view(pr, "eproj", () => {
        const s = new Sprite(Texture.EMPTY);
        s.anchor.set(0.5);
        return s;
      }, this.projLayer);
      const s = v.obj as Sprite;
      s.texture = A.enemyShotTex(pr.style === "boss" ? "orb" : pr.style, pr.color as RGB);
      s.position.set(pr.x, pr.y);
      s.rotation = Math.atan2(pr.vy, pr.vx);
      s.scale.set(Math.max(0.8, pr.r / 6.5));
    }
  }

  private drawPickups(run: Run, cl: number, ct: number, cr: number, cb: number) {
    for (const pu of run.pickups) {
      if (pu.x < cl || pu.x > cr || pu.y < ct || pu.y > cb) continue;
      const v = this.view(pu, "pickup", () => {
        const s = new Sprite(Texture.EMPTY);
        s.anchor.set(0.5);
        return s;
      }, this.pickupLayer);
      const s = v.obj as Sprite;
      s.texture = A.pickupTex(pu.kind);
      const bob = Math.sin(this.t * 4 + pu.bob) * 2;
      s.position.set(pu.x, pu.y + bob);
      let sc = 0.8;
      if (pu.kind !== "heart") sc = Math.min(1.7, 0.75 + Math.log10(1 + pu.value) * 0.35);
      else sc = 1;
      s.scale.set(sc);
      s.alpha = pu.kind === "heart" && pu.spawnT > 11 ? 0.5 + 0.5 * Math.sin(this.t * 14) : 1;
    }
    for (const d of run.bigDrops) {
      const v = this.view(d, "bigdrop", () => {
        const s = new Sprite(Texture.EMPTY);
        s.anchor.set(0.5);
        return s;
      }, this.pickupLayer);
      const s = v.obj as Sprite;
      s.texture = A.bigDropTex(d.kind);
      s.position.set(d.x, d.y + Math.sin(d.t * 3) * 4);
      s.scale.set(0.75 + 0.05 * Math.sin(d.t * 5));
    }
  }

  private spriteFor(obj: any, kind: string, parent: Container, anchorX = 0.5, anchorY = 0.5): Sprite {
    const v = this.view(obj, kind, () => {
      const s = new Sprite(Texture.EMPTY);
      s.anchor.set(anchorX, anchorY);
      return s;
    }, parent);
    return v.obj as Sprite;
  }

  private drawWeaponObjects(run: Run) {
    const gb = this.dynBelow, ga = this.dynAbove;
    for (const o of run.wobjs as any[]) {
      switch (o.kind) {
        case "water": {
          const s = this.spriteFor(o, "water", this.decalLayer);
          s.texture = A.puddleTex();
          const r = o.curR();
          s.position.set(o.x, o.y);
          s.scale.set(r / 60);
          s.alpha = clamp(o.life / 0.5, 0, 1);
          break;
        }
        case "firering": {
          const s = this.spriteFor(o, "firering", this.decalLayer);
          s.texture = A.fireRingTex(o.ice);
          const r = o.curR();
          s.position.set(o.x, o.y);
          s.scale.set(r / 62);
          s.alpha = clamp(o.life / 0.3, 0, 1);
          s.blendMode = o.ice ? "normal" : "add";
          break;
        }
        case "tornado": {
          const s = this.spriteFor(o, "tornado", this.entityLayer, 0.5, 0.95);
          s.texture = A.tornadoTex(Math.floor(o.t * 12) % 2);
          s.position.set(o.x, o.y + 30);
          s.zIndex = o.y + 30;
          const sc = (o.pullR / 200) * clamp(o.t / 0.2, 0, 1) * clamp(o.life / 0.3, 0, 1);
          s.scale.set(sc * 1.4, sc * 1.6);
          gb.circle(o.x, o.y, o.pullR).stroke({ width: 2, color: 0xbadaf0, alpha: 0.25 });
          break;
        }
        case "axe": {
          const s = this.spriteFor(o, "axe", this.projLayer);
          s.texture = A.axeTex();
          s.position.set(o.x, o.y);
          s.rotation = o.spin;
          s.scale.set(0.9 * o.k);
          break;
        }
        case "knife": {
          const s = this.spriteFor(o, "knife", this.projLayer, 0.7, 0.5);
          s.texture = A.knifeTex();
          s.position.set(o.x, o.y);
          s.rotation = o.ang;
          break;
        }
        case "ghost": {
          const s = this.spriteFor(o, "ghost", this.projLayer, 0.4, 0.5);
          s.texture = A.ghostSwordTex();
          s.position.set(o.x, o.y);
          s.rotation = o.ang;
          s.scale.set(0.8);
          break;
        }
        case "wolf": {
          const s = this.spriteFor(o, "wolf", this.entityLayer);
          s.texture = A.wolfTex(Math.floor(o.runPh) % 2);
          s.position.set(o.x, o.y);
          s.zIndex = o.y;
          s.scale.set(0.95 * o.face, 0.95);
          s.alpha = 0.92;
          break;
        }
        case "hawk": {
          const s = this.spriteFor(o, "hawk", this.projLayer);
          s.texture = A.hawkTex(o.flap > 0 ? 0 : 1);
          s.position.set(o.x, o.y - o.alt);
          s.rotation = o.ang + Math.PI / 2;
          s.scale.set(0.75);
          gb.ellipse(o.x, o.y + 8, 12, 4).fill({ color: 0x000000, alpha: 0.25 });
          break;
        }
        case "bat": {
          const s = this.spriteFor(o, "bat", this.projLayer);
          s.texture = A.batTex(Math.floor(o.t * 14) % 2);
          s.position.set(o.x, o.y);
          s.scale.set(0.9);
          break;
        }
        case "meteor": {
          if (o.boomT < 0) {
            const f = clamp(o.t / o.delay, 0, 1);
            gb.circle(o.x, o.y, o.radius).fill({ color: 0xff7634, alpha: 0.08 + 0.15 * f }).stroke({ width: 2, color: 0xffa050, alpha: 0.85 });
            gb.circle(o.x, o.y, o.radius * f).fill({ color: 0xff7634, alpha: 0.15 });
            const s = this.spriteFor(o, "meteor", this.projLayer);
            s.texture = A.rockTex();
            s.position.set(o.x + (1 - f) * 120, o.y - (1 - f) * 380);
            s.scale.set(0.9 + 0.3 * f);
            s.rotation = f * 6;
          } else {
            const v = this.views.get(o);
            if (v) (v.obj as Sprite).visible = false;
            this.views.get(o) && (this.views.get(o)!.mark = this.frame);
          }
          break;
        }
        case "whip": {
          const f = 1 - o.life / 0.32;
          const e = 1 - Math.pow(1 - f, 3);
          const swing = o.spinDir * 0.4 * (2 * e - 1);
          const reach = o.length * (0.46 + 0.54 * Math.min(1, f * 1.35));
          const a0 = o.ang + swing * 0.3, a1 = o.ang + swing;
          const gx = o.x + Math.cos(a0) * 17, gy = o.y + Math.sin(a0) * 17;
          const pts: number[] = [];
          const N = 14;
          for (let i = 0; i <= N; i++) {
            const fr = i / N;
            let a = a0 + (a1 - a0) * Math.pow(fr, 0.55);
            a -= o.spinDir * 0.55 * Math.sin(fr * Math.PI) * (1 - e * 0.6);
            pts.push(gx + Math.cos(a) * (reach - 17) * fr, gy + Math.sin(a) * (reach - 17) * fr);
          }
          const alpha = clamp(o.life / 0.1, 0, 1);
          ga.poly(pts, false).stroke({ width: o.width + 3, color: 0x281810, alpha: 0.85 * alpha, cap: "round", join: "round" });
          ga.poly(pts, false).stroke({ width: o.width, color: 0xb06a3a, alpha, cap: "round", join: "round" });
          ga.poly(pts, false).stroke({ width: 2, color: 0xffe2b0, alpha: 0.8 * alpha, cap: "round", join: "round" });
          break;
        }
        case "slash": {
          const f = 1 - o.life / 0.26;
          const r = o.radius;
          const sweep = o.half * 2 * Math.min(1, f * 1.6);
          const a0 = o.ang - o.half, a1 = a0 + sweep;
          ga.arc(o.x, o.y, r * 0.85, a0, a1).stroke({ width: r * 0.28, color: 0xf0f4ff, alpha: 0.35 * (1 - f) });
          ga.arc(o.x, o.y, r * 0.95, a0, a1).stroke({ width: 3, color: 0xffffff, alpha: 0.9 * (1 - f) });
          break;
        }
        case "beam": {
          for (let i = 0; i < o.n; i++) {
            const a = o.ang + (i * TAU) / o.n;
            const ex = o.x + Math.cos(a) * o.length, ey = o.y + Math.sin(a) * o.length;
            ga.moveTo(o.x, o.y).lineTo(ex, ey).stroke({ width: C.BEAM_WIDTH * 2.2, color: 0xffc860, alpha: 0.35 });
            ga.moveTo(o.x, o.y).lineTo(ex, ey).stroke({ width: C.BEAM_WIDTH * 0.8, color: 0xfff8d8, alpha: 0.95 });
          }
          break;
        }
        case "nova": {
          const f = o.t / 0.55;
          ga.circle(o.x, o.y, o.radius * Math.min(1, f * 1.8)).fill({ color: 0x96e4ff, alpha: 0.18 * (1 - f) }).stroke({ width: 5, color: 0xecfaff, alpha: 0.9 * (1 - f) });
          break;
        }
        case "quake": {
          if (o.boomT < 0) {
            const f = o.t / C.QUAKE_CHARGE_T;
            gb.circle(o.x, o.y, o.radius).stroke({ width: 2, color: 0xe29246, alpha: 0.5 });
            gb.circle(o.x, o.y, o.radius * f).fill({ color: 0xe29246, alpha: 0.12 + 0.1 * f });
          }
          break;
        }
      }
    }
    // minyonlar (ayrı listelerde)
    for (const o of run.ghostBlades as any[]) {
      const s = this.spriteFor(o, "ghost", this.projLayer, 0.4, 0.5);
      s.texture = A.ghostSwordTex();
      s.position.set(o.x, o.y);
      s.rotation = o.ang;
      s.scale.set(0.8);
    }
    for (const o of run.hawks as any[]) {
      const s = this.spriteFor(o, "hawk", this.projLayer);
      s.texture = A.hawkTex(o.flap > 0 ? 0 : 1);
      s.position.set(o.x, o.y - o.alt);
      s.rotation = o.ang + Math.PI / 2;
      s.scale.set(0.75);
    }
    for (const o of run.wolves as any[]) {
      const s = this.spriteFor(o, "wolf", this.entityLayer);
      s.texture = A.wolfTex(Math.floor(o.runPh) % 2);
      s.position.set(o.x, o.y);
      s.zIndex = o.y;
      s.scale.set(0.95 * o.face, 0.95);
      s.alpha = 0.9;
    }
    for (const bh of run.blackHoles) {
      const s = this.spriteFor(bh, "bhole", this.decalLayer);
      s.texture = A.blackHoleTex();
      s.position.set(bh.x, bh.y);
      s.rotation = bh.t * 3;
      s.scale.set((bh.r / 126) * (0.6 + 0.4 * Math.min(1, bh.t * 3)));
    }
  }

  private drawHazards(run: Run) {
    const dt = A.dangerTex();
    for (const h of run.hazards) {
      const s = this.spriteFor(h, "hazard", this.decalLayer);
      s.texture = dt;
      s.position.set(h.x, h.y);
      s.tint = rgbToHex(h.color);
      if (!h.exploded) {
        const f = clamp(h.t / h.delay, 0, 1);
        s.scale.set(h.r / 60);
        s.alpha = 0.45 + 0.45 * f;
        this.dynBelow.circle(h.x, h.y, h.r * f).fill({ color: rgbToHex(h.color), alpha: 0.22 });
      } else {
        s.scale.set((h.r / 60) * 1.1);
        s.alpha = clamp(h.linger / 0.3, 0, 1) * 0.6;
      }
    }
  }

  private drawMisc(run: Run) {
    for (const ch of run.chests) {
      const s = this.spriteFor(ch, "chest", this.entityLayer, 0.5, 0.65);
      s.texture = A.chestTex(false, ch.opened);
      s.position.set(ch.x, ch.y + Math.sin(ch.t * 3 + ch.bob) * 3);
      s.zIndex = ch.y;
      s.scale.set(ch.opened ? 1 + ch.openT * 0.4 : 0.9);
      s.alpha = ch.opened ? clamp(1.1 - ch.openT, 0, 1) : 1;
    }
    if (run.legendChest) {
      const ch = run.legendChest;
      const s = this.spriteFor(ch, "chest", this.entityLayer, 0.5, 0.65);
      s.texture = A.chestTex(true, ch.opened);
      s.position.set(ch.x, ch.y + Math.sin(ch.t * 3) * 3);
      s.zIndex = ch.y;
      s.scale.set(1.25);
    }
    for (const k of run.mapKeys) {
      if (k.gone) continue;
      const s = this.spriteFor(k, "key", this.entityLayer);
      s.texture = A.keyTex();
      s.position.set(k.x, k.y - 10 + Math.sin(k.t * 3) * 5 - (k.taken ? k.takeT * 60 : 0));
      s.zIndex = k.y;
      s.alpha = k.taken ? clamp(1 - k.takeT / 0.6, 0, 1) : 1;
      s.rotation = Math.sin(k.t * 2) * 0.2;
    }
    // gezgin tüccar ve lanetli mağara
    const ex = run.ex;
    if (ex?.merchant) {
      const m = ex.merchant;
      const s = this.spriteFor(m, "merchant", this.entityLayer, 62 / 220, 150 / 180);
      s.texture = A.merchantTex();
      s.position.set(m.x, m.y);
      s.zIndex = m.y;
      if (!m.done) {
        const by = m.y - 150 + Math.sin(m.t * 4) * 5;
        this.dynAbove.circle(m.x, by, 15).fill({ color: 0x0c0a14 }).circle(m.x, by, 12.5).fill({ color: 0xffc46e });
        this.dynAbove.roundRect(m.x - 2, by - 7.5, 4, 9, 2).fill({ color: 0x3c220a }).circle(m.x, by + 5, 2.2).fill({ color: 0x3c220a });
      }
    }
    if (ex?.shrine) {
      const sh = ex.shrine;
      const s = this.spriteFor(sh, "shrine", this.entityLayer, 0.5, 138 / 170);
      s.texture = A.shrineTex(sh.lid > 0.5);
      const fade = sh.used ? clamp(1 - sh.dieT / 1.6, 0, 1) : 1;
      s.position.set(sh.x + (sh.used ? Math.sin(sh.t * 50) * 3 * fade : 0), sh.y + (1 - fade) * 20);
      s.alpha = fade;
      s.zIndex = sh.y;
      if (!sh.used) this.dynBelow.circle(sh.x, sh.y + 30, 104).stroke({ width: 3, color: 0xb25cff, alpha: 0.18 + 0.12 * Math.sin(sh.t * 3) });
    }
    if (run.hellPortal) {
      const hp = run.hellPortal;
      const s = this.spriteFor(hp, "portal", this.decalLayer);
      s.texture = A.portalTex();
      s.position.set(hp.x, hp.y);
      s.scale.set(0.9 + 0.06 * Math.sin(hp.t * 3));
      s.rotation = hp.t * 0.5;
    }
  }

  // ------------------------------------------------------------------
  // Ekran kenarı göstergeleri: patron, sandık, anahtar, portal
  // ------------------------------------------------------------------
  private drawIndicators(run: Run) {
    const g = this.indicators;
    g.clear();
    const w = this.app.screen.width, h = this.app.screen.height;
    const z = this.zoom;
    const items: [number, number, number][] = [];
    for (const b of run.bosses) if (b.alive && !b.isHidden()) items.push([b.x, b.y, 0xff4a3a]);
    for (const c of run.chests) if (!c.opened) items.push([c.x, c.y, 0xe8b84a]);
    if (run.legendChest) items.push([run.legendChest.x, run.legendChest.y, 0xc878ff]);
    const k = run.nearestKey();
    if (k) items.push([k.x, k.y, 0xffd65a]);
    if (run.hellPortal) items.push([run.hellPortal.x, run.hellPortal.y, 0xb256ff]);
    // mağara: bulunduktan sonra; tüccar: mobilde harita olmadığı için hep (yemin edilene dek)
    if (run.ex?.shrine?.discovered && !run.ex.shrine.used) items.push([run.ex.shrine.x, run.ex.shrine.y, 0xb25cff]);
    if (run.ex?.merchant && !run.ex.merchant.done) items.push([run.ex.merchant.x, run.ex.merchant.y, 0xffc46e]);
    for (const d of run.bigDrops) items.push([d.x, d.y, d.kind === "magnet" ? 0xff5460 : 0xb26eff]);
    const m = 34;
    for (const [x, y, col] of items) {
      const sx = (x - run.camX) * z, sy = (y - run.camY) * z;
      if (sx > 0 && sx < w && sy > 0 && sy < h) continue;
      const cx = w / 2, cy = h / 2;
      const dx = sx - cx, dy = sy - cy;
      const ang = Math.atan2(dy, dx);
      const kx = (w / 2 - m) / Math.max(1e-3, Math.abs(dx)), ky = (h / 2 - m) / Math.max(1e-3, Math.abs(dy));
      const kk = Math.min(kx, ky);
      const px = cx + dx * kk, py = cy + dy * kk;
      const s = 13;
      const p1 = [px + Math.cos(ang) * s, py + Math.sin(ang) * s];
      const p2 = [px + Math.cos(ang + 2.5) * s, py + Math.sin(ang + 2.5) * s];
      const p3 = [px + Math.cos(ang - 2.5) * s, py + Math.sin(ang - 2.5) * s];
      g.circle(px, py, 15).fill({ color: 0x0b0d18, alpha: 0.55 });
      g.poly([...p1, ...p2, ...p3]).fill({ color: col, alpha: 0.95 }).stroke({ width: 2, color: 0x0b0d18, alpha: 0.8 });
    }
  }

  worldToScreen(run: Run, x: number, y: number): [number, number] {
    return [(x - run.camX) * this.zoom, (y - run.camY) * this.zoom];
  }

  reset() {
    for (const [, v] of this.views) {
      v.pool.release(v.obj);
      const sp = (v as any).shPool as Pool<any> | undefined;
      if (v.extra) for (const e of v.extra) sp ? sp.release(e) : (e.visible = false);
    }
    this.views.clear();
    for (const s of [...this.books, ...this.orbits, ...this.ghosts]) s.visible = false;
    this.penta.visible = false;
  }
}

export { softCircle, squareTex, mixCol };
export type { Target, Enemy, Boss };
