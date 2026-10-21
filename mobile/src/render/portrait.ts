/**
 * Menüler için kahraman resmi: oyundaki dokularla aynı çizim, tek tuvalde
 * birleştirilip resim adresine çevrilir (önbellekli).
 */
import type { Texture } from "pixi.js";
import { RGB } from "../core/util";
import type { SkinDef } from "../game/data";
import { heroBodyTex, heroEyesTex, pupilTex, weaponTex } from "./art_player";

const cache = new Map<string, string>();

function src(t: Texture): HTMLCanvasElement {
  return (t.source as any).resource as HTMLCanvasElement;
}

export function heroPortrait(sk: SkinDef, px = 160): string {
  const key = sk.id + "|" + px;
  const c = cache.get(key);
  if (c) return c;
  const cv = document.createElement("canvas");
  cv.width = cv.height = px;
  const g = cv.getContext("2d")!;
  const s = px / 96;
  g.scale(s, s);
  const shadow = sk.id === "shadow" || sk.id === "shadow_hunter";
  // gölge
  g.fillStyle = "rgba(0,0,0,0.28)";
  g.beginPath();
  g.ellipse(48, 76, 18, 5.5, 0, 0, Math.PI * 2);
  g.fill();
  g.drawImage(src(heroBodyTex(sk)), 0, 0, 96, 96);
  const ew = 32 * 0.9, eh = 24 * 0.9;
  g.drawImage(src(heroEyesTex(shadow)), 48 - ew / 2 + 1.5, 51 - eh / 2, ew, eh);
  if (!shadow) {
    const pw = 8 * 0.9;
    for (const dx of [-6.2, 6.2]) g.drawImage(src(pupilTex()), 48 + dx * 0.9 + 3 - pw / 2, 51 - pw / 2, pw, pw);
  }
  const wt = weaponTex(sk.weapon, sk.color as RGB, sk.accent as RGB);
  const wc = src(wt.tex);
  const res = (wt.tex.source as any).resolution || 1;
  const ww = (wc.width / res) * 0.85, wh = (wc.height / res) * 0.85;
  g.drawImage(wc, 48 + 11 - ww * wt.ax, 57 - wh * wt.ay, ww, wh);
  const url = cv.toDataURL("image/png");
  cache.set(key, url);
  return url;
}
