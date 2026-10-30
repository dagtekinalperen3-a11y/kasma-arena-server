"""Web sitesini (index.html) oyunun kendi verisi ve çizimleriyle derler.

    python tools/build_site.py

site/index.src.html şablonundaki /*GAMEDATA*/ yerine oyundan okunan veri
(skinler, yetenekler, kitaplar, silahlar, kostümler, petler, şans çarkı) ve
oyunun kendi çizim kodundan üretilmiş görseller (PNG, base64) yazılır; sonuç
depo kökündeki index.html'dir (Render da onu sunar, Hostinger'a da o yüklenir).
Oyuna yeni skin / kitap / silah eklenince bu betiği yeniden çalıştırmak yeter.
"""
import base64
import importlib.util
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "offscreen")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# oyun kendi kayıt dosyasını buraya açsın (gerçek kayda dokunmasın)
_tmp_home = os.path.join(ROOT, ".site_build_home")
os.makedirs(_tmp_home, exist_ok=True)
os.environ["HOME"] = _tmp_home
os.environ["APPDATA"] = _tmp_home

spec = importlib.util.spec_from_file_location("ka", os.path.join(ROOT, "kasma_arena13.py"))
ka = importlib.util.module_from_spec(spec)
sys.modules["ka"] = ka
spec.loader.exec_module(ka)
import pygame  # noqa: E402

try:
    from PIL import Image
except Exception:            # PIL yoksa görseller sıkıştırılmadan yazılır
    Image = None

app = ka.App()
ka.set_lang("tr")


def hexc(c):
    return "#%02x%02x%02x" % tuple(int(v) for v in c[:3])


def png(surf, pad=2):
    r = surf.get_bounding_rect(min_alpha=8)
    if r.w <= 0 or r.h <= 0:
        r = surf.get_rect()
    r = r.inflate(pad * 2, pad * 2).clip(surf.get_rect())
    sub = surf.subsurface(r).copy()
    raw = io.BytesIO()
    pygame.image.save(sub, raw, "x.png")
    data = raw.getvalue()
    if Image is not None:
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        q = im.quantize(colors=160, method=Image.Quantize.FASTOCTREE)
        out = io.BytesIO()
        q.save(out, "PNG", optimize=True)
        if len(out.getvalue()) < len(data):
            data = out.getvalue()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def canvas(w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    return s


T = 0.35
data = {"skins": [], "books": [], "weapons": [], "cosmetics": [], "pets": [], "wheel": {}}

# ---- skinler ----
for sk in ka.SKINS:
    s = canvas(190, 150)
    try:
        ka.draw_skin_preview(s, sk, 95, 80, T, r=30)
    except Exception as e:
        print("skin çizilemedi", sk["id"], e)
    u = ka.get_skin_ult(sk["id"]) or {}
    data["skins"].append({
        "id": sk["id"], "name": ka.skin_name(sk), "desc": ka.skin_desc(sk),
        "color": hexc(sk["color"]), "accent": hexc(sk.get("accent", sk["color"])),
        "cost": sk.get("cost"), "premium": bool(sk.get("premium")), "price": sk.get("price_hint", ""),
        "perks": [str(p) for p in (sk.get("perks") or [])],
        "ult": {"name": u.get("name", ""), "desc": u.get("desc", ""), "cd": u.get("cd", 0),
                "color": hexc(u.get("color", sk["color"]))} if u else None,
        "img": png(s),
    })

# ---- kitaplar ----
for bk in ka.BOOKS:
    s = canvas(120, 130)
    ka.draw_book(s, 60, 66, 92, bk, T)
    unl = bk.get("unlock") or {}
    data["books"].append({
        "key": bk["key"], "name": ka.bk_name(bk), "desc": ka.bk_desc(bk), "color": hexc(bk["color"]),
        "rare": bool(bk.get("rare")), "unlock": ka.unlock_text(unl), "img": png(s),
    })

# ---- silahlar ----
book_by = {b["key"]: b for b in ka.BOOKS}
for w in ka.BOSS_WEAPONS:
    s = canvas(130, 130)
    ka.draw_weapon_emblem(s, 65, 65, 92, w, T, locked=False, glow=True)
    ev = ka.EVOLUTIONS.get(w["key"])
    evo = None
    if ev and ev[0] in book_by:
        try:
            evo = {"book": ka.bk_name(book_by[ev[0]]), "name": ka.evo_name(w["key"], 1)}
        except Exception:
            evo = {"book": ka.bk_name(book_by[ev[0]]), "name": ""}
    data["weapons"].append({
        "key": w["key"], "name": ka.w_name(w), "desc": ka.w_desc(w), "color": hexc(w["color"]),
        "unlock": ka.unlock_text(w.get("unlock") or {}), "evo": evo,
        "timed": bool(w.get("timed")), "passive": bool(w.get("passive")), "img": png(s),
    })

# ---- kostümler + petler ----
for c in list(ka.COSMETICS) + list(ka.PETS):
    s = canvas(130, 130)
    try:
        app._cosmetic_preview(s, 65, 68, 30, c["slot"], c["id"], T)
    except Exception as e:
        print("kostüm çizilemedi", c["id"], e)
    row = {"id": c["id"], "slot": c["slot"], "name": ka.cos_name(c), "desc": ka.cos_desc(c),
           "color": hexc(c.get("color", (200, 200, 200))), "perk": c.get("perk_text") or "",
           "cost": c.get("cost"), "wheel": bool(c.get("wheel_only")), "price": c.get("price_hint", ""),
           "img": png(s)}
    (data["pets"] if c["slot"] == "pet" else data["cosmetics"]).append(row)

# ---- şans çarkı (oyundakiyle aynı) ----
crown = canvas(80, 80)
ka.draw_god_crown(crown, 40, 44, 22, T, glow=False)
data["wheel"] = {
    "order": list(ka.WHEEL_ORDER),
    "colors": {k: hexc(v) for k, v in ka.WHEEL_COLORS.items()},
    "names": {k: ka.wheel_prize_name(k) for k in ka.WHEEL_ORDER},
    "short": {k: ka.wheel_short(k) for k in ka.WHEEL_ORDER},
    "odds": {k: v for k, v in ka.WHEEL_PRIZES},
    "crown": png(crown),
    "daily": ka.WHEEL_DAILY, "wait": ka.WHEEL_SITE_WAIT,
}
data["version"] = ka.GAME_VERSION
data["counts"] = {"skins": len(ka.SKINS), "books": len(ka.BOOKS), "weapons": len(ka.BOSS_WEAPONS),
                  "cosmetics": len(ka.COSMETICS), "pets": len(ka.PETS)}

src = open(os.path.join(ROOT, "site", "index.src.html"), encoding="utf-8").read()
blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
out = src.replace("/*GAMEDATA*/null", blob)
for k, v in data["counts"].items():
    out = out.replace("{{%s}}" % k, str(v))
out = out.replace("{{version}}", data["version"])
out = out.replace("{{wheeldaily}}", str(ka.WHEEL_DAILY)).replace("{{wheelwait}}", str(ka.WHEEL_SITE_WAIT))
import re  # noqa: E402
_m = re.search(r"^SCRATCH_DAILY\s*=\s*(\d+)", open(os.path.join(ROOT, "server.py"), encoding="utf-8").read(), re.M)
out = out.replace("{{scrdaily}}", _m.group(1) if _m else "150")
with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
    f.write(out)
print("index.html yazıldı: %.0f KB (%d skin, %d kitap, %d silah, %d kostüm, %d pet)" % (
    len(out.encode()) / 1024, len(data["skins"]), len(data["books"]), len(data["weapons"]),
    len(data["cosmetics"]), len(data["pets"])))
