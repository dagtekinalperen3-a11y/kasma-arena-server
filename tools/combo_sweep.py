"""Kombo taraması: tools/combo_sim.run_combo'yu çok çekirdekte çalıştırır.

    python tools/combo_sweep.py jobs.json results.jsonl [işçi]

jobs.json: [{"weapons": [...], "books": [...], "rare": "...", "seed": 1}, ...]
Sonuçlar satır satır results.jsonl'a eklenir; yarıda kalırsa tekrar
çalıştırınca bitmiş işleri atlar.
"""
import json
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def key_of(j):
    return "|".join([",".join(j["weapons"]), ",".join(j["books"]), j["rare"], str(j["seed"])])


def work(j):
    import combo_sim as C
    try:
        res = C.run_combo(j["weapons"], j["books"], j["rare"], seed=j["seed"],
                          max_time=j.get("max_time", 3600.0))
    except Exception as e:  # bir koşu çökerse tarama durmasın
        res = {"weapons": j["weapons"], "books": j["books"], "rare": j["rare"],
               "seed": j["seed"], "error": repr(e)}
    res["key"] = key_of(j)
    return res


def main():
    jobs = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else os.cpu_count()
    done = set()
    if os.path.exists(out):
        for ln in open(out):
            try:
                done.add(json.loads(ln)["key"])
            except Exception:
                pass
    todo = [j for j in jobs if key_of(j) not in done]
    print(f"{len(todo)} iş ({len(done)} bitmiş)", flush=True)
    with Pool(workers, maxtasksperchild=4) as pl, open(out, "a") as f:
        for i, res in enumerate(pl.imap_unordered(work, todo)):
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
            f.flush()
            print(i + 1, res.get("wave"), res.get("score"), res.get("weapons"),
                  res.get("wall"), flush=True)


if __name__ == "__main__":
    main()
