/**
 * Varlık dokuları: yaratık, oyuncu, mermi, toplanabilir ... hepsi burada
 * önbelleğe alınır.
 */
import { Texture } from "pixi.js";
import { makeTex } from "./tex";
import { enemyArt } from "./art_enemies";
import { RGB } from "../core/util";

const ENEMY_RES = 3;

/** Yaratık dokusu: [kare0, kare1, beyaz-parlama]. */
export function enemyTextures(shape: string, col: RGB | number[], r: number): Texture[] {
  const R = Math.round(r);
  const ck = `${shape}|${col.map((v) => Math.round(v)).join(",")}|${R}`;
  const art = enemyArt(shape);
  const c = col as RGB;
  const size = R * 3;
  const t0 = makeTex("e0|" + ck, size, size, (g) => art(g, R, c, 0), ENEMY_RES);
  const t1 = makeTex("e1|" + ck, size, size, (g) => art(g, R, c, 1), ENEMY_RES);
  const tf = makeTex("ef|" + ck, size, size, (g) => {
    art(g, R, c, 0);
    g.globalCompositeOperation = "source-atop";
    g.fillStyle = "rgba(255,255,255,0.62)";
    g.fillRect(0, 0, size, size);
  }, 2);
  return [t0, t1, tf];
}
