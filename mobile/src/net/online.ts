/**
 * Çevrim içi: hesap (giriş / kayıt) ve dünya sıralaması.
 * Sunucu: kasma-arena-server (server.py). Skor gönderisi oradaki imza ve
 * makullük denetimiyle BİREBİR uyumludur (bkz. _expected_sig, _build_hash).
 * Ağ yoksa oyun hiçbir şey kaybetmeden çevrim dışı devam eder.
 */
import type { Save } from "../game/save";
import type { Run } from "../game/run";

export const API = "https://kasma-arena-server.onrender.com";
// Python sürümündeki SUBMIT_SECRET ile aynı (sunucu KASMA_SUBMIT_SECRET).
const SUBMIT_SECRET = "kasma-arena-submit-v1:3d7f90ac41be6528";
const SIG_FIELDS = ["name", "score", "kills", "wave", "run_time", "created_at", "diff"];

export interface WorldRow {
  name: string;
  score: number;
  kills: number;
  wave: number;
  run_time: number;
  diff: string;
  created_at: number;
  skin?: string;
}

type Summary = ReturnType<Run["summary"]>;

/** Python'un str(float) çıktısı: tam sayı değerli float'ta ".0" ekler. */
function pyFloat(x: number) {
  if (Number.isInteger(x)) return x.toFixed(1);
  const s = String(x);
  // Python 1e16 üstünü üstel yazar; oyunda o büyüklükte süre/tarih yok.
  return s;
}

/** Python json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=True) */
function canonJson(v: any): string {
  if (v === null || v === undefined) return "null";
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : pyFloat(v);
  if (typeof v === "string")
    return JSON.stringify(v).replace(/[\u007f-￿]/g, (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));
  if (Array.isArray(v)) return "[" + v.map(canonJson).join(",") + "]";
  const keys = Object.keys(v).sort();
  return "{" + keys.map((k) => canonJson(k) + ":" + canonJson(v[k])).join(",") + "}";
}

async function sha256Hex(s: string) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
async function hmacHex(key: string, msg: string) {
  const k = await crypto.subtle.importKey("raw", new TextEncoder().encode(key), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", k, new TextEncoder().encode(msg));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function req(path: string, body?: any, timeoutMs = 45000): Promise<any> {
  const ctl = new AbortController();
  const tm = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await fetch(API + path, {
      method: body ? "POST" : "GET",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctl.signal,
    });
    let j: any = null;
    try {
      j = await r.json();
    } catch {}
    if (!r.ok) {
      const e = new Error((j && j.error) || `HTTP ${r.status}`);
      (e as any).status = r.status;
      throw e;
    }
    return j;
  } finally {
    clearTimeout(tm);
  }
}

class Online {
  save: Save | null = null;
  lastSubmit: "" | "sending" | "ok" | "fail" | "skip_login" | "skip_map" = "";
  lastError = "";
  private cache: { t: number; rows: WorldRow[] } | null = null;

  init(save: Save) {
    this.save = save;
    // sunucuyu erkenden uyandır (ücretsiz barındırma uykudan geç kalkar)
    setTimeout(() => req("/auth/status", undefined, 60000).catch(() => {}), 1500);
  }

  get account() {
    return this.save?.data.account || null;
  }
  get loggedIn() {
    return !!this.account?.token;
  }

  private device() {
    return this.save!.data.installId;
  }

  async login(who: string, password: string) {
    const j = await req("/auth/login", { username: who.trim(), password, device: this.device() });
    this.setAccount(j);
    return j;
  }

  async register(username: string, password: string, email: string) {
    const j = await req("/auth/register", { username: username.trim(), password, email: email.trim(), device: this.device() });
    this.setAccount(j);
    return j;
  }

  private setAccount(j: any) {
    if (!j?.success || !j.token) throw new Error(j?.error || "?");
    this.save!.data.account = { token: j.token, username: j.account?.username || j.account?.name || "" };
    this.save!.persist(true);
  }

  async logout() {
    const tok = this.account?.token;
    if (this.save) {
      this.save.data.account = null;
      this.save.persist(true);
    }
    if (tok) req("/auth/logout", { token: tok, device: this.device() }, 15000).catch(() => {});
  }

  /** Hesabı ve sunucudaki bütün verisini kalıcı siler (mağaza kuralı). */
  async deleteAccount(password: string) {
    const acc = this.account;
    if (!acc) return;
    await req("/auth/delete", { token: acc.token, device: this.device(), password }, 60000);
    this.save!.data.account = null;
    this.save!.persist(true);
    this.cache = null;
  }

  async scores(force = false): Promise<WorldRow[]> {
    if (!force && this.cache && performance.now() - this.cache.t < 60000) return this.cache.rows;
    const rows = (await req("/scores?platform=mobile")) as WorldRow[];
    this.cache = { t: performance.now(), rows: Array.isArray(rows) ? rows : [] };
    return this.cache.rows;
  }

  /** Koşu bitince: yalnız TAŞ MEYDAN ve giriş yapılmışsa dünya sıralamasına. */
  submitRun(s: Summary) {
    if (s.theme !== "stone") {
      this.lastSubmit = "skip_map";
      return;
    }
    if (!this.loggedIn || !this.account?.username) {
      this.lastSubmit = "skip_login";
      return;
    }
    if (s.score <= 0 || s.time < 6) return;
    this.lastSubmit = "sending";
    this.doSubmit(s).then(
      () => {
        this.lastSubmit = "ok";
        this.cache = null;
      },
      (e) => {
        this.lastSubmit = "fail";
        this.lastError = String(e?.message || e);
        // oturum düşmüşse (başka cihazdan giriş) çıkış yap
        if ((e as any)?.status === 401 && this.save) {
          this.save.data.account = null;
          this.save.persist();
        }
      },
    );
  }

  private async doSubmit(s: Summary) {
    const acc = this.account!;
    const details = {
      b: Object.entries(s.books).filter(([, l]) => l >= 1).map(([k, l]) => [k, Math.floor(l)]),
      d: Object.entries(s.dmgLog)
        .filter(([, v]) => v > 0)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 24)
        .map(([k, v]) => [k, Math.floor(v)]),
      hell: s.biome === "hell",
      map: s.theme,
      skin: s.skin,
      w: Object.entries(s.weapons).filter(([, l]) => l >= 1).map(([k, l]) => [k, Math.floor(l)]),
    };
    const build = (await sha256Hex(canonJson(details))).slice(0, 32);
    const payload: Record<string, any> = {
      name: acc.username.slice(0, 14),
      score: Math.floor(s.score),
      kills: Math.floor(s.kills),
      wave: Math.floor(s.wave),
      run_time: Math.round(s.time * 1000) / 1000,
      created_at: Math.round(Date.now()) / 1000,
      diff: s.diff,
      details,
      build,
      platform: "mobile",
      wmode: "time",
    };
    const fields = [...SIG_FIELDS, "build", "platform", "wmode"];
    const msg = fields
      .map((k) => {
        const v = payload[k];
        if (k === "run_time" || k === "created_at") return pyFloat(v);
        return String(v ?? "");
      })
      .join("|");
    payload.sig = await hmacHex(SUBMIT_SECRET, msg);
    payload.token = acc.token;
    payload.device = this.device();
    return req("/submit", payload, 60000);
  }

  achievement(_id: string) {}
}

export const online = new Online();

/** Birim testi için (imza uyumu). */
export const _test = { canonJson, pyFloat, sha256Hex, hmacHex };
