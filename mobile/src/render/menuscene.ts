/**
 * Menü arka planı: seçili haritanın zemini üzerinde dolaşan yaratıklar
 * ve ortada bekleyen kahraman. Ucuz — birkaç sprite.
 */
import { Container, Sprite, TilingSprite, Graphics, Texture } from "pixi.js";
import { rand, pick, TAU } from "../core/util";
import { ENEMY_COLORS, MAP_ROSTER, MAP_ENEMIES, getSkin } from "../game/data";
import { enemyTextures } from "./sprites";
import { floorTex, scatterDecos, Deco } from "./world";
import { heroBodyTex, heroEyesTex } from "./art_player";
import { shadowTex } from "./tex";

interface Mob {
  s: Sprite;
  sh: Sprite;
  tex: Texture[];
  x: number;
  y: number;
  vx: number;
  vy: number;
  t: number;
  r: number;
}

export class MenuScene {
  root = new Container();
  private floor: TilingSprite;
  private world = new Container();
  private decoLayer = new Container();
  private mobs: Mob[] = [];
  private dim = new Graphics();
  private theme = "";
  private time = 0;
  private hero = new Container();
  private heroBody = new Sprite();
  private heroEyes = new Sprite();
  private w = 1;
  private h = 1;
  private scale = 1;

  constructor() {
    this.floor = new TilingSprite({ texture: Texture.WHITE, width: 10, height: 10 });
    const sh = new Sprite(shadowTex());
    sh.anchor.set(0.5);
    sh.scale.set(1.3, 1.1);
    sh.y = 16;
    this.heroBody.anchor.set(0.5, 54 / 96);
    this.heroEyes.anchor.set(0.5);
    this.heroEyes.texture = heroEyesTex();
    this.heroEyes.scale.set(0.9);
    this.heroEyes.position.set(2, -3);
    this.hero.addChild(sh, this.heroBody, this.heroEyes);
    this.world.addChild(this.decoLayer);
    this.world.sortableChildren = true;
    this.root.addChild(this.floor, this.world, this.dim);
  }

  setTheme(theme: string) {
    if (theme === this.theme) return;
    this.theme = theme;
    const biome = theme;
    this.floor.texture = floorTex(biome);
    for (const m of this.mobs) {
      m.s.destroy();
      m.sh.destroy();
    }
    this.mobs = [];
    this.decoLayer.removeChildren().forEach((c) => c.destroy());
    const decos: Deco[] = scatterDecos(biome, 1800, 1100, 99 + theme.length);
    for (const d of decos.slice(0, 26)) {
      d.s.x -= 900;
      d.s.y -= 550;
      d.s.zIndex = d.flat ? -1000 : d.s.y;
      this.decoLayer.addChild(d.s);
    }
    const roster = theme === "stone" ? null : MAP_ROSTER[theme];
    const kinds = ["red", "blue", "yellow", "tank", "sprinter", "brute", "wizard"];
    for (let i = 0; i < 16; i++) {
      const k = pick(kinds);
      let shape = k, col = ENEMY_COLORS[k] || [200, 100, 100];
      if (roster && roster[k] && MAP_ENEMIES[roster[k]]) {
        const v = MAP_ENEMIES[roster[k]];
        shape = v.shape;
        col = v.color;
      }
      const r = k === "tank" || k === "brute" ? 22 : 15;
      const tex = enemyTextures(shape, col, r);
      const s = new Sprite(tex[0]);
      s.anchor.set(0.5);
      s.scale.set(1 / 1);
      const sh = new Sprite(shadowTex());
      sh.anchor.set(0.5);
      sh.scale.set(r / 16, r / 22);
      sh.alpha = 0.7;
      const ang = rand(0, TAU), d = rand(220, 700);
      const m: Mob = { s, sh, tex, x: Math.cos(ang) * d, y: Math.sin(ang) * d * 0.6, vx: 0, vy: 0, t: rand(0, 5), r };
      this.mobs.push(m);
      this.world.addChild(sh, s);
    }
  }

  setHero(skinId: string) {
    this.heroBody.texture = heroBodyTex(getSkin(skinId));
  }

  resize(w: number, h: number) {
    this.w = w;
    this.h = h;
    this.floor.width = w;
    this.floor.height = h;
    this.scale = Math.min(w, h) / 520;
    this.floor.tileScale.set(this.scale * 0.9);
    this.world.scale.set(this.scale);
    this.world.position.set(w * 0.66, h * 0.58);
    this.dim.clear();
    // okunurluk için sol tarafı ve kenarları karart
    const steps = 24;
    for (let i = 0; i < steps; i++) {
      const f = i / steps;
      this.dim.rect((w * i) / steps, 0, w / steps + 1, h).fill({ color: 0x080a14, alpha: 0.72 * Math.pow(1 - f, 1.4) + 0.12 });
    }
    this.dim.rect(0, 0, w, h * 0.14).fill({ color: 0x080a14, alpha: 0.25 });
    this.dim.rect(0, h * 0.86, w, h * 0.14).fill({ color: 0x080a14, alpha: 0.3 });
  }

  update(dt: number) {
    this.time += dt;
    this.floor.tilePosition.x -= dt * 14 * this.scale;
    this.floor.tilePosition.y -= dt * 6 * this.scale;
    const bob = Math.sin(this.time * 2.2);
    this.heroBody.scale.set(1 / (1 + bob * 0.015) * 1.6, (1 + bob * 0.015) * 1.6);
    this.hero.scale.set(1);
    this.heroEyes.scale.set(0.9 * 1.6);
    this.heroEyes.position.set(2 * 1.6 + Math.sin(this.time * 0.7) * 3, -5 + bob * 0.8);
    this.hero.y = bob * 1.5;
    this.hero.zIndex = 0;
    for (const m of this.mobs) {
      m.t += dt;
      // kahramanın etrafında yavaşça dolaş
      const dx = -m.x, dy = -m.y;
      const d = Math.hypot(dx, dy) || 1;
      const tang = d < 260 ? -1 : 0.35;
      const ax = (dx / d) * tang * 30 + (-dy / d) * 26;
      const ay = (dy / d) * tang * 30 + (dx / d) * 26;
      m.vx += (ax - m.vx) * dt * 0.8;
      m.vy += (ay - m.vy) * dt * 0.8;
      m.x += m.vx * dt;
      m.y += m.vy * dt * 0.7;
      const f = Math.floor(m.t * 4) % 2;
      m.s.texture = m.tex[f];
      m.s.position.set(m.x, m.y + Math.sin(m.t * 6) * 1.5);
      m.sh.position.set(m.x, m.y + m.r * 0.85);
      m.s.zIndex = m.y;
      m.sh.zIndex = -500;
    }
  }
}
