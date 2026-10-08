"""
ARENA BONK — logo / ikon üretici.

assets/source/ altındaki üç orijinal görselden (kare ikon, yuvarlak köşeli
ikon, afiş) oyunun ve mağaza sayfalarının ihtiyaç duyduğu bütün dosyaları
üretir:

  assets/arena_bonk.ico              .exe ikonu (16-256 px, PyInstaller --icon)
  assets/icon_512.png                Google Play uygulama ikonu (512x512)
  assets/icon_1024_rounded.png       genel amaçlı yuvarlak köşeli ikon
  assets/badge_512.png               saydam YUVARLAK amblem (ikonun halkası)
  assets/logo.png                    saydam zeminli birleşik logo
                                     (amblem + ARENA/BONK yazısı + slogan)
  assets/feature_graphic_1024x500.png Google Play öne çıkan görsel
  assets/banner_1600x640.png         afişin kendisi (sosyal medya kapağı)

Ayrıca oyunun içine GÖMÜLEN küçük sürümleri (base64) kasma_arena13.py'deki
EMBED_* sabitlerine yazar; böylece .exe tek dosya olarak dağıtılabilir,
yanında resim klasörü taşımak gerekmez.

Kullanım:  python tools/make_assets.py
"""
import base64
import io
import os
import re

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "source")
OUT = os.path.join(ROOT, "assets")
GAME = os.path.join(ROOT, "kasma_arena13.py")

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/verdanab.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

CREAM = (255, 236, 182)
ORANGE = (224, 122, 74)
OUTLINE = (40, 24, 18)
TAGLINE = (236, 222, 196)


def font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def round_badge(sq, radius_frac=494 / 1024):
    """Kare ikondaki altın halkayı kenar sayıp YUVARLAK bir amblem keser."""
    n = sq.width
    ss = 4
    mask = Image.new("L", (n * ss, n * ss), 0)
    r = radius_frac * n * ss
    c = n * ss / 2
    ImageDraw.Draw(mask).ellipse((c - r, c - r, c + r, c + r), fill=255)
    mask = mask.resize((n, n), Image.LANCZOS)
    out = sq.convert("RGBA")
    out.putalpha(mask)
    return out


def tracked_width(draw, text, fnt, track):
    return int(sum(draw.textlength(ch, font=fnt) for ch in text) + track * (len(text) - 1))


def tracked_text(draw, xy, text, fnt, fill, track):
    """Harf aralığı açılmış yazı (afişteki slogan gibi)."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + track


def outlined_text(draw, xy, text, fnt, fill, stroke, sw, spacing=0):
    draw.text(xy, text, font=fnt, fill=fill, stroke_width=sw, stroke_fill=stroke)


def make_logo(badge, scale=1.0):
    """Amblem + iki satırlık yazı + slogan, saydam zeminde."""
    S = scale
    f_big = font(int(150 * S))
    f_tag = font(int(30 * S))
    sw = int(12 * S)
    # ölçüler
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    a_box = tmp.textbbox((0, 0), "ARENA", font=f_big, stroke_width=sw)
    b_box = tmp.textbbox((0, 0), "BONK", font=f_big, stroke_width=sw)
    tag = "HAYATTA KAL.  VUR.  BONKLA."
    track = int(4 * S)
    t_box = (0, 0, tracked_width(tmp, tag, f_tag, track), f_tag.getbbox("HAY")[3])
    text_w = max(a_box[2] - a_box[0], b_box[2] - b_box[0], t_box[2])
    line_h = a_box[3] - a_box[1]
    badge_d = int(330 * S)
    gap = int(26 * S)
    pad = int(30 * S)
    W = pad * 2 + badge_d + gap + text_w
    text_h = line_h * 2 - int(4 * S) + int(16 * S) + (t_box[3] - t_box[1]) + int(10 * S)
    H = pad * 2 + max(badge_d, text_h)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # yazının arkasında yumuşak koyu hâle: açık renkli zeminlerde de okunur
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    tx = pad + badge_d + gap
    ty = (H - text_h) // 2
    hd.rounded_rectangle((tx + 30 * S, ty + 30 * S, tx + text_w - 30 * S, ty + text_h - 30 * S),
                         radius=int(60 * S), fill=(12, 8, 20, 110))
    halo = halo.filter(ImageFilter.GaussianBlur(int(34 * S)))
    img.alpha_composite(halo)

    # amblem + gölgesi
    b = badge.resize((badge_d, badge_d), Image.LANCZOS)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    by = (H - badge_d) // 2
    shadow = Image.new("RGBA", b.size, (0, 0, 0, 0))
    shadow.putalpha(b.getchannel("A").point(lambda v: int(v * 0.55)))
    sh.paste(shadow, (pad + int(6 * S), by + int(10 * S)), shadow)
    sh = sh.filter(ImageFilter.GaussianBlur(int(10 * S)))
    img.alpha_composite(sh)
    img.alpha_composite(b, (pad, by))

    d = ImageDraw.Draw(img)
    # ARENA (krem) — BONK (turuncu), ortak sol hizalı değil, ortalı
    ax = tx + (text_w - (a_box[2] - a_box[0])) // 2 - a_box[0]
    bx = tx + (text_w - (b_box[2] - b_box[0])) // 2 - b_box[0]
    ay = ty - a_box[1]
    byy = ay + line_h - int(4 * S)
    # alt gölge (koyu, aşağı kaydırılmış)
    for (x, y, s, col) in ((ax, ay, "ARENA", CREAM), (bx, byy, "BONK", ORANGE)):
        d.text((x + int(6 * S), y + int(8 * S)), s, font=f_big, fill=(8, 4, 10, 200),
               stroke_width=sw, stroke_fill=(8, 4, 10, 200))
    for (x, y, s, col) in ((ax, ay, "ARENA", CREAM), (bx, byy, "BONK", ORANGE)):
        outlined_text(d, (x, y), s, f_big, col, OUTLINE, sw)
    # slogan
    tg_y = byy + line_h + int(16 * S)
    tgx = tx + (text_w - (t_box[2] - t_box[0])) // 2
    tracked_text(d, (tgx + 2, tg_y + 3), tag, f_tag, (10, 6, 12, 220), track)
    tracked_text(d, (tgx, tg_y), tag, f_tag, TAGLINE, track)
    return img.crop(img.getbbox())


def png_b64(img, size=None, colors=None):
    if size:
        img = img.resize(size, Image.LANCZOS)
    buf = io.BytesIO()
    if colors:
        img = img.quantize(colors=colors, method=Image.FASTOCTREE, dither=Image.FLOYDSTEINBERG)
    img.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def write_embeds(embeds):
    """kasma_arena13.py içindeki EMBED_... = \"\"\"...\"\"\" bloklarını günceller."""
    with open(GAME, "r", encoding="utf-8") as f:
        src = f.read()
    for name, data in embeds.items():
        lines = "\n".join(data[i:i + 100] for i in range(0, len(data), 100))
        block = '%s = (\n"""%s"""\n)' % (name, lines)
        pat = re.compile(r'^%s = \(\n""".*?"""\n\)' % re.escape(name), re.S | re.M)
        if not pat.search(src):
            raise SystemExit("%s bloğu oyunda bulunamadı" % name)
        src = pat.sub(lambda _m: block, src, count=1)
    with open(GAME, "w", encoding="utf-8") as f:
        f.write(src)


def main():
    sq = Image.open(os.path.join(SRC, "icon_square.png")).convert("RGBA")
    rounded = Image.open(os.path.join(SRC, "icon_rounded.png")).convert("RGBA")
    banner = Image.open(os.path.join(SRC, "banner.png")).convert("RGB")

    badge = round_badge(sq)
    badge.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "badge_512.png"))
    sq.convert("RGB").resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "icon_512.png"))
    rounded.save(os.path.join(OUT, "icon_1024_rounded.png"))
    rounded.save(os.path.join(OUT, "arena_bonk.ico"),
                 sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    banner.save(os.path.join(OUT, "banner_1600x640.png"))

    # Google Play "öne çıkan görsel" 1024x500: afişin ortası, oran korunarak
    bw, bh = banner.size
    tw = int(bh * 1024 / 500)
    x0 = max(0, min(bw - tw, 120 + (1330 - tw) // 2))
    banner.crop((x0, 0, x0 + tw, bh)).resize((1024, 500), Image.LANCZOS).save(
        os.path.join(OUT, "feature_graphic_1024x500.png"))

    logo = make_logo(badge)
    logo.save(os.path.join(OUT, "logo.png"))

    # oyuna gömülenler
    lw = 700
    lh = int(logo.height * lw / logo.width)
    write_embeds({
        "EMBED_LOGO_PNG": png_b64(logo, (lw, lh)),
        "EMBED_ICON_PNG": png_b64(rounded, (128, 128)),
        "EMBED_BADGE_PNG": png_b64(badge, (192, 192)),
    })
    print("logo", logo.size, "->", (lw, lh))


if __name__ == "__main__":
    main()
