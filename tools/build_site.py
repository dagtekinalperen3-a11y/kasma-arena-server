"""Web sitesini oyunun kendi verisi ve çizimleriyle derler (çok sayfalı).

    pip install pygame-ce pillow
    python tools/build_site.py

Kaynak:  site/src/_layout.html   ortak iskelet (üst menü, alt bilgi, çark paneli)
         site/src/pages/*.html   sayfaların içeriği (ilk satır: <!--meta ...-->)
         site/src/site.css, site.js
         site/static/*           olduğu gibi kopyalanır (default.php, .htaccess)
Çıktı:   site/dist/              Hostinger'a (public_html) bu klasörün İÇİ yüklenir.
         site/dist/assets/data.js  oyundan üretilen veri + görseller (window.GD)

Oyuna yeni skin / kitap / silah eklenince bu betiği yeniden çalıştırmak yeter.
"""
import base64
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "site", "src")
STATIC = os.path.join(ROOT, "site", "static")
DIST = os.path.join(ROOT, "site", "dist")
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
    kind = "png"
    if Image is not None:
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        q = im.quantize(colors=160, method=Image.Quantize.FASTOCTREE)
        out = io.BytesIO()
        q.save(out, "PNG", optimize=True)
        if len(out.getvalue()) < len(data):
            data = out.getvalue()
        # WebP çok daha küçük: site daha hızlı açılır (bütün güncel tarayıcılar okur)
        try:
            out = io.BytesIO()
            Image.open(io.BytesIO(data)).convert("RGBA").save(out, "WEBP", lossless=True, method=6)
            if len(out.getvalue()) < len(data):
                data, kind = out.getvalue(), "webp"
        except Exception:
            pass
    return "data:image/%s;base64," % kind + base64.b64encode(data).decode()


def canvas(w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    return s


T = 0.35
NEW_SKINS = ["shadow_warrior", "dragon_soul", "chrono_sage"]
data = {"skins": [], "books": [], "weapons": [], "evos": [], "cosmetics": [], "pets": [], "wheel": {},
        "new": NEW_SKINS}

# ---- karakterler ----
for sk in ka.SKINS:
    s = canvas(300, 240)
    try:
        ka.draw_skin_preview(s, sk, 150, 128, T, r=44)
    except Exception as e:
        print("skin çizilemedi", sk["id"], e)
    u = ka.get_skin_ult(sk["id"]) or {}
    try:
        style = [round(v, 3) for v in ka.skin_style_scores(sk)]
    except Exception:
        style = []
    data["skins"].append({
        "id": sk["id"], "name": ka.skin_name(sk), "desc": ka.skin_desc(sk),
        "color": hexc(sk["color"]), "accent": hexc(sk.get("accent", sk["color"])),
        "cost": sk.get("cost"), "premium": bool(sk.get("premium")), "price": sk.get("price_hint", ""),
        "perks": [ka.perk_tr(p) for p in (sk.get("perks") or [])], "style": style,
        "ult": {"name": ka.TRX(u.get("name", "")), "desc": ka.TRX(u.get("desc", "")), "cd": u.get("cd", 0),
                "color": hexc(u.get("color", sk["color"]))} if u else None,
        "img": png(s),
    })

# ---- kitaplar ----
book_by = {b["key"]: b for b in ka.BOOKS}
book_img = {}
evo_of_book = {}
for wk, ev in ka.EVOLUTIONS.items():
    evo_of_book.setdefault(ev[0], []).append(wk)
weapon_by = {w["key"]: w for w in ka.BOSS_WEAPONS}
for bk in ka.BOOKS:
    s = canvas(120, 130)
    ka.draw_book(s, 60, 66, 92, bk, T)
    unl = bk.get("unlock") or {}
    book_img[bk["key"]] = png(s)
    data["books"].append({
        "key": bk["key"], "name": ka.bk_name(bk), "desc": ka.bk_desc(bk), "color": hexc(bk["color"]),
        "rare": bool(bk.get("rare")), "unlock": ka.unlock_text(unl),
        "reqs": [ka.req_text(rq) for rq in ka.book_reqs(bk)],
        "max": ka.book_max_level(bk),
        "pairs": [ka.w_name(weapon_by[k]) for k in evo_of_book.get(bk["key"], []) if k in weapon_by],
        "img": book_img[bk["key"]],
    })

# ---- silahlar ----
weapon_img = {}
for w in ka.BOSS_WEAPONS:
    s = canvas(130, 130)
    ka.draw_weapon_emblem(s, 65, 65, 92, w, T, locked=False, glow=True)
    weapon_img[w["key"]] = png(s)
    ev = ka.EVOLUTIONS.get(w["key"])
    data["weapons"].append({
        "key": w["key"], "name": ka.w_name(w), "desc": ka.w_desc(w), "up": ka.w_up(w), "how": ka.w_how(w),
        "color": hexc(w["color"]), "unlock": ka.unlock_text(w.get("unlock") or {}),
        "reqs": [ka.req_text(rq) for rq in ka.weapon_reqs(w)],
        "max": ka.weapon_max_level(w),
        "evo": ka.evo_name(w["key"], 1) if ev else "", "book": ka.bk_name(book_by[ev[0]]) if ev and ev[0] in book_by else "",
        "timed": bool(w.get("timed")), "passive": bool(w.get("passive")), "img": weapon_img[w["key"]],
    })

# ---- evrimler ----
for w in ka.BOSS_WEAPONS:
    key = w["key"]
    ev = ka.EVOLUTIONS.get(key)
    if not ev or ev[0] not in book_by:
        continue
    tiers = []
    for tier in range(1, ka.EVO_TIERS_MAX + 1):
        tiers.append({
            "tier": tier, "roman": ka.EVO_ROMAN[tier], "name": ka.evo_name(key, tier),
            "perk": ka.L("evo.perk." + ka.evo_tier_perk(key, tier)),
            "color": hexc(ka.evo_color(key, tier)),
            "lvl": ka.evo_level_need(key, tier), "book_lvl": ka.evo_book_need(key, tier),
            "mult": ka.EVO_TIER_MULT[tier - 1],
        })
    bk = book_by[ev[0]]
    data["evos"].append({"key": key, "weapon": ka.w_name(w), "wcolor": hexc(w["color"]), "wimg": weapon_img[key],
                         "book": ka.bk_name(bk), "bimg": book_img[bk["key"]], "brare": bool(bk.get("rare")),
                         "tiers": tiers})

# ---- kostümler + petler ----
for c in list(ka.COSMETICS) + list(ka.PETS):
    s = canvas(130, 130)
    try:
        app._cosmetic_preview(s, 65, 68, 30, c["slot"], c["id"], T)
    except Exception as e:
        print("kostüm çizilemedi", c["id"], e)
    row = {"id": c["id"], "slot": c["slot"], "name": ka.cos_name(c), "desc": ka.cos_desc(c),
           "color": hexc(c.get("color", (200, 200, 200))),
           "perk": ka.perk_tr(c["perk_text"]) if c.get("perk_text") else "",
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
data["evo_rules"] = {"lvl": list(ka.EVO_TIER_LEVEL), "book": list(ka.EVO_TIER_BOOK), "mult": list(ka.EVO_TIER_MULT)}
data["version"] = ka.GAME_VERSION
counts = {"skins": len(ka.SKINS), "books": len(ka.BOOKS), "weapons": len(ka.BOSS_WEAPONS),
          "evos": len(data["evos"]), "cosmetics": len(ka.COSMETICS), "pets": len(ka.PETS)}
data["counts"] = counts

_m = re.search(r"^SCRATCH_DAILY\s*=\s*(\d+)", open(os.path.join(ROOT, "server.py"), encoding="utf-8").read(), re.M)
VARS = dict({k: str(v) for k, v in counts.items()},
            version=data["version"], wheeldaily=str(ka.WHEEL_DAILY), wheelwait=str(ka.WHEEL_SITE_WAIT),
            scrdaily=_m.group(1) if _m else "150")

# ---- çıktı ----
if os.path.isdir(DIST):
    shutil.rmtree(DIST)
os.makedirs(os.path.join(DIST, "assets"))


def write(rel, text):
    path = os.path.join(DIST, rel)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return text


blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
ver = {}
ver["data"] = hashlib.sha1(write("assets/data.js", "window.GD=" + blob + ";\n").encode()).hexdigest()[:8]
for name in ("site.css", "site.js"):
    txt = open(os.path.join(SRC, name), encoding="utf-8").read()
    ver[name.split(".")[1]] = hashlib.sha1(write("assets/" + name, txt).encode()).hexdigest()[:8]

# AppLixir API anahtarı: site/config.json {"applixir_api_key": "..."} ya da
# APPLIXIR_API_KEY ortam değişkeni. Sunucuda assets/config.js düzenlenerek de
# değiştirilebilir (yeniden derleme gerekmez).
_cfg = {}
try:
    _cfg = json.load(open(os.path.join(ROOT, "site", "config.json"), encoding="utf-8"))
except Exception:
    _cfg = {}
_ak = str(_cfg.get("applixir_api_key") or os.environ.get("APPLIXIR_API_KEY") or "")
ver["cfg"] = hashlib.sha1(write("assets/config.js", "/* AppLixir ödüllü video ayarı. API anahtarını tırnakların arasına yaz. */\n"
                                "window.EA_CFG={applixirKey:%s};\n" % json.dumps(_ak)).encode()).hexdigest()[:8]

layout = open(os.path.join(SRC, "_layout.html"), encoding="utf-8").read()
META_RE = re.compile(r"^<!--meta\s+(.*?)-->\s*", re.S)
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')
pages = sorted(f for f in os.listdir(os.path.join(SRC, "pages")) if f.endswith(".html"))
for fn in pages:
    body = open(os.path.join(SRC, "pages", fn), encoding="utf-8").read()
    m = META_RE.match(body)
    meta = dict(ATTR_RE.findall(m.group(1))) if m else {}
    body = body[m.end():] if m else body
    page = meta.get("page", fn[:-5])
    out = (layout.replace("{{content}}", body)
           .replace("{{title}}", meta.get("title", "EvolveArena"))
           .replace("{{desc}}", meta.get("desc", ""))
           .replace("{{page}}", page)
           .replace("{{v_css}}", ver["css"]).replace("{{v_js}}", ver["js"]).replace("{{v_data}}", ver["data"])
           .replace("{{v_cfg}}", ver["cfg"]))
    out = re.sub(r'data-nav="%s"' % re.escape(page), 'data-nav="%s" aria-current="page"' % page, out)
    for k, v in VARS.items():
        out = out.replace("{{%s}}" % k, v)
    left = re.findall(r"\{\{\w+\}\}", out)
    if left:
        print("UYARI: doldurulmamış yer tutucu", fn, set(left))
    write(fn, out)

for fn in os.listdir(STATIC):
    shutil.copy2(os.path.join(STATIC, fn), os.path.join(DIST, fn))

size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _d, fs in os.walk(DIST) for f in fs)
print("site/dist yazıldı: %d sayfa, %.0f KB (%d karakter, %d kitap, %d silah, %d evrim, %d kostüm, %d pet)" % (
    len(pages), size / 1024, counts["skins"], counts["books"], counts["weapons"], counts["evos"],
    counts["cosmetics"], counts["pets"]))
