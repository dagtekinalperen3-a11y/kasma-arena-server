// Geliştirme: bütün çizimleri bir sayfada gösterir (?gallery=1).
import { Application, Container, Sprite, Text } from "pixi.js";
import { ENEMY_ART } from "./render/art_enemies";
import { enemyTextures } from "./render/sprites";
import { ENEMY_COLORS, MAP_ENEMIES, HELL_ENEMIES } from "./game/data";

export async function gallery() {
  const app = new Application();
  await app.init({ resizeTo: window, background: "#20263a", resolution: Math.min(2, devicePixelRatio), autoDensity: true });
  document.getElementById("game")!.appendChild(app.canvas);
  document.getElementById("boot")?.remove();
  const root = new Container();
  app.stage.addChild(root);
  const items: [string, number[]][] = [];
  for (const k of Object.keys(ENEMY_ART)) {
    const v = (MAP_ENEMIES as any)[Object.keys(MAP_ENEMIES).find((m) => MAP_ENEMIES[m].shape === k) || ""];
    const h = Object.values(HELL_ENEMIES).find((m) => m.shape === k);
    const col = (ENEMY_COLORS as any)[k] || v?.color || h?.color || [200, 120, 120];
    items.push([k, col]);
  }
  const cols = 10;
  items.forEach(([k, col], i) => {
    const [t0, t1, tf] = enemyTextures(k, col, 18);
    const x = 40 + (i % cols) * 120, y = 50 + Math.floor(i / cols) * 120;
    [t0, t1].forEach((t, j) => {
      const s = new Sprite(t);
      s.anchor.set(0.5);
      s.x = x + j * 55;
      s.y = y;
      root.addChild(s);
    });
    const tx = new Text({ text: k, style: { fill: "#fff", fontSize: 11 } });
    tx.x = x - 20;
    tx.y = y + 30;
    root.addChild(tx);
    void tf;
  });
}
