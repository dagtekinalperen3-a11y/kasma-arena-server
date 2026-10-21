"""EvolveArena (Python/pygame) oyun dosyasındaki veri tablolarını mobil
sürümün kullandığı JSON'a döker.

Kullanım:
    python tools/export_gamedata.py /yol/arenae.py src/data/gamedata.json

pygame kurulu olmalı (pip install pygame). Oyun penceresi açılmaz; yalnızca
modül içe aktarılır ve büyük harfli sabitler okunur.
"""
import importlib.util
import json
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

SKIP = {
    "_COOP_STATIC", "_WEB_JS", "_SERVER_ROOTS_PEM", "ACCOUNT_RETURN_PAGE_OK",
    "ACCOUNT_RETURN_PAGE_FAIL", "SUBMIT_SECRET", "_SAVE_SECRET", "SAVE_MAGIC",
}


def conv(o, depth=0):
    if depth > 14:
        raise TypeError("deep")
    if isinstance(o, (bool, int, float, str)) or o is None:
        return o
    if isinstance(o, (list, tuple)):
        return [conv(x, depth + 1) for x in o]
    if isinstance(o, (set, frozenset)):
        return sorted((conv(x, depth + 1) for x in o), key=str)
    if isinstance(o, dict):
        return {str(k): conv(v, depth + 1) for k, v in o.items()}
    if callable(o):
        return None
    raise TypeError(type(o))


def main(src, dst):
    save_dir = os.path.join(os.path.dirname(os.path.abspath(dst)), ".export_save")
    os.makedirs(save_dir, exist_ok=True)
    os.environ["ARENA_SAVE_DIR"] = save_dir
    spec = importlib.util.spec_from_file_location("arena_src", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = {}
    for k, v in vars(mod).items():
        if k in SKIP or k.startswith("EMBED") or k.endswith(("_BY_KEY", "_BY_ID")):
            continue
        if not (k.isupper() or (k.startswith("_") and k[1:].isupper())):
            continue
        try:
            out[k] = conv(v)
        except Exception:
            pass
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote", dst, len(out), "tables")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
