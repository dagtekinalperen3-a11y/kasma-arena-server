/**
 * Küçük DOM yardımcıları (çerçeve yok — hızlı ve hafif).
 */
import { sfx } from "../core/audio";
import { haptic } from "../core/native";
import { RGB, rgbCss } from "../core/util";

export function h<K extends keyof HTMLElementTagNameMap>(tag: K, cls = "", html = ""): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html) e.innerHTML = html;
  return e;
}

export function esc(s: string) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}

export const css = (c: RGB | number[], a = 1) => rgbCss(c as RGB, a);

/** Dokunmatik düğme: anında tepki (pointerdown), ses ve titreşim. */
export function tap(el: HTMLElement, fn: (e: Event) => void, snd: string | null = "click") {
  let downAt = 0;
  let sx = 0, sy = 0;
  el.addEventListener("pointerdown", (e) => {
    downAt = performance.now();
    sx = e.clientX;
    sy = e.clientY;
    el.classList.add("down");
  });
  const clear = () => el.classList.remove("down");
  el.addEventListener("pointerleave", clear);
  el.addEventListener("pointercancel", clear);
  el.addEventListener("pointerup", (e) => {
    clear();
    if (!downAt) return;
    downAt = 0;
    // kaydırma hareketiyse tıklama sayma
    if (Math.hypot(e.clientX - sx, e.clientY - sy) > 14) return;
    if (el.classList.contains("disabled")) {
      sfx("error", 0.5);
      haptic("warning");
      return;
    }
    if (snd) sfx(snd, 0.7, 0.02);
    haptic("light");
    fn(e);
  });
  return el;
}

export function btn(label: string, cls = "", fn?: (e: Event) => void, snd: string | null = "click") {
  const b = h("button", "btn " + cls, label);
  b.type = "button";
  if (fn) tap(b, fn, snd);
  return b;
}

/** Sayıyı kısa yaz: 12.4K, 3.1M */
export function short(n: number) {
  n = Math.floor(n);
  if (n < 10000) return String(n);
  if (n < 1e6) return (n / 1000).toFixed(n < 1e5 ? 1 : 0).replace(/\.0$/, "") + "K";
  return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
}

/** Değer değiştiyse yazar (gereksiz yeniden düzenlemeyi önler). */
export function setText(el: HTMLElement, s: string) {
  if ((el as any)._t !== s) {
    (el as any)._t = s;
    el.textContent = s;
  }
}
export function setStyle(el: HTMLElement, prop: string, v: string) {
  const k = "_s_" + prop;
  if ((el as any)[k] !== v) {
    (el as any)[k] = v;
    el.style.setProperty(prop, v);
  }
}
export function setClass(el: HTMLElement, cls: string, on: boolean) {
  if (el.classList.contains(cls) !== on) el.classList.toggle(cls, on);
}
