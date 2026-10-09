"""Tarama sonuçlarından (results/*.jsonl) Markdown tablo üretir.

    python tools/combo_report.py results/phaseA.jsonl [...] > rapor.md
"""
import json
import sys
from collections import defaultdict

WN = {"axe": "BALTA", "book": "KALKAN", "pentagram": "PENTAGRAM", "whip": "KIRBAÇ",
      "zemzem": "ZEMZEM", "shoe": "PAPUÇ", "frost": "BUZ İZİ", "emanet": "EMANET",
      "cloak": "PELERİN", "tornado": "HORTUM"}
BN = {"r_dmg": "Hasar", "r_hp": "Can", "r_armor": "Zırh", "r_spd": "Rüzgâr", "r_aspd": "Tempo",
      "r_crit": "Kritik", "r_critd": "Kritik Güç", "r_regen": "Şifa", "r_coin": "Altın",
      "r_xp": "Bilgelik", "r_mag": "Mıknatıs", "r_vamp": "Sülük", "r_pierce": "Delgi",
      "r_bonk": "BONK", "r_swarm": "Sürü", "r_bosshunter": "Patron Avcısı",
      "r_poison": "Zehir", "r_echo": "Yankı", "r_multi": "Çoğalma", "r_killheal": "Kan",
      "r_rage": "Öfke", "r_execute": "İnfaz", "r_roar": "Kükreme", "r_dashslow": "Zaman",
      "r_second_wind": "İkinci Nefes", "r_lasthope": "Son Umut", "r_hp_big": "Dev"}


def load(paths):
    rows = []
    for p in paths:
        for ln in open(p):
            ln = ln.strip()
            if ln:
                d = json.loads(ln)
                if "error" not in d:
                    rows.append(d)
    return rows


def wname(ws):
    return " + ".join(WN.get(w, w) for w in ws)


def bname(bs, rare):
    return ", ".join(BN.get(b, b) for b in bs) + " + nadir: " + BN.get(rare, rare)


def group(rows, by):
    g = defaultdict(list)
    for r in rows:
        g[by(r)].append(r)
    return g


def summarize(rs):
    waves = [r["wave"] for r in rs]
    scores = [r["score"] for r in rs]
    best = max(rs, key=lambda r: (r["wave"], r["score"]))
    return {
        "n": len(rs), "max_wave": max(waves), "avg_wave": sum(waves) / len(waves),
        "max_score": max(scores), "avg_score": sum(scores) / len(scores),
        "arena": best.get("arena_wave"), "hell": best["wave"] - (best.get("arena_wave") or 0)
        if best.get("hell") else 0, "time": best["time"], "level": best["level"],
        "lvl25": (best.get("lvl_at") or {}).get("25"),
    }


def fmt_num(n):
    return f"{int(n):,}".replace(",", ".")


def fmt_time(s):
    s = int(s)
    return f"{s // 60}:{s % 60:02d}"


def main():
    rows = load(sys.argv[1:])
    g = group(rows, lambda r: (tuple(r["weapons"]), tuple(r["books"]), r["rare"]))
    items = [(k, summarize(v)) for k, v in g.items()]
    items.sort(key=lambda kv: (-kv[1]["max_wave"], -kv[1]["max_score"]))
    print("| # | Silahlar | Kitaplar (4 normal / nadir) | En iyi dalga (arena+cehennem) | En iyi skor | Ort. dalga | Koşu | Süre | Seviye (25. dalgada) |")
    print("|---|---|---|---|---|---|---|---|---|")
    for i, (k, s) in enumerate(items, 1):
        ws, bs, rare = k
        print(f"| {i} | {wname(ws)} | {bname(bs, rare)} | **{s['max_wave']}** "
              f"({s['arena']}+{s['hell']}) | {fmt_num(s['max_score'])} | {s['avg_wave']:.1f} | {s['n']} | "
              f"{fmt_time(s['time'])} | {s['level']} ({s['lvl25']}) |")


if __name__ == "__main__":
    main()
