import G from "../data/gamedata.json";
import { UI_STRINGS } from "./strings";

export const LANGS: [string, string][] = [
  ["tr", "Türkçe"],
  ["en", "English"],
  ["es", "Español"],
  ["de", "Deutsch"],
  ["ru", "Русский"],
];
const CODES = LANGS.map((l) => l[0]);
let langIdx = 0;

const SRC = (G as any).STRINGS as Record<string, string[]>;

export function setLang(code: string) {
  const i = CODES.indexOf(code);
  langIdx = i >= 0 ? i : 0;
  document.documentElement.lang = CODES[langIdx];
}
export const lang = () => CODES[langIdx];
export const langIndex = () => langIdx;

export function detectLang(): string {
  const n = (navigator.language || "tr").slice(0, 2).toLowerCase();
  return CODES.includes(n) ? n : "en";
}

function fmt(s: string, args: any[]) {
  if (!args.length) return s;
  let auto = 0;
  return s.replace(/\{(\d*)\}/g, (_, i) => {
    const v = args[i === "" ? auto++ : +i];
    return v === undefined ? "" : String(v);
  });
}

/** Çeviri: önce mobil arayüz sözlüğü, sonra oyunun kendi tablosu. */
export function t(key: string, ...args: any[]): string {
  const row = UI_STRINGS[key] || SRC[key];
  if (!row) return key;
  const s = row[langIdx] || row[1] || row[0] || key;
  return fmt(s, args);
}

/** Anahtar yoksa verilen yedeği döner. */
export function tx(key: string, fallback: string, ...args: any[]): string {
  const row = UI_STRINGS[key] || SRC[key];
  if (!row) return fmt(fallback, args);
  return fmt(row[langIdx] || row[1] || row[0] || fallback, args);
}

export const has = (key: string) => !!(UI_STRINGS[key] || SRC[key]);

export function fmtPct(v: number, digits = 0) {
  const x = (v * 100).toFixed(digits);
  const s = lang() === "tr" ? x.replace(".", ",") : x;
  return lang() === "tr" ? "%" + s : s + "%";
}
