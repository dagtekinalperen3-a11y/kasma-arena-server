#!/usr/bin/env python3
"""
EVOLVE ARENA — YouTube kapak resmi (1280x720 JPG, < 2 MB).

Arka plan oyunun GERÇEK motorundan bir karedir (cehennem, Kor Ejderha ve
evrimleşmiş silahlarla bir savaş); üstüne oyunun logosu, evrimleşmiş silah
amblemi ve büyük kapak yazıları basılır. Fragman aracının (make_evolve_trailer)
altyapısını kullanır.

Kullanım:
    python3 tools/make_thumbnail.py --game yol/kasma_arena13.py
    python3 tools/make_thumbnail.py --game ... -o trailer/youtube_kapak.jpg
"""
import argparse
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import make_evolve_trailer as T     # noqa: E402  (--game'i sys.argv'dan okur)
import pygame                       # noqa: E402

K = T.K
W, H = T.W, T.H


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", default=T.GAME)
    ap.add_argument("-o", "--out", default=os.path.join(T.ROOT, "trailer", "youtube_kapak.jpg"))
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    random.seed(args.seed)
    K.sfx = lambda *a, **k: None

    tr = T.Trailer(K.App())
    sh = tr.sh
    # ---- arka plan: cehennemde evrimleşmiş silahlar + Kor Ejderha ----
    run = tr.make_run(K.HELL_PORTAL_WAVE + 3, {"axe": 25, "tesla": 20, "beam": 20, "pentagram": 18},
                      60, 46, books={"r_critd": (10, 1), "r_echo": (1, 1), "r_xp": (5, 1)},
                      hell=True, ring=40, prewarm=0.3)
    for key, tier in (("axe", 3), ("tesla", 2), ("beam", 2)):
        while K.evo_tier(run.player, key) < tier:
            run.evolve_weapon(key)
    run.evo_banner = None
    cam = run.cam_rect()
    dg = K.Boss("dragon", cam.centerx + 200, cam.centery - 90, 1.0, 1.0, run.waves.wave, hellish=True)
    run.bosses.append(dg)
    K.scale_bosses_to_player(run.bosses, run.player)
    run.waves.boss_active = True
    for _ in range(48):                       # 1,6 sn savaş
        tr.t += 1 / 30.0
        sh.t += 1 / 30.0
        tr.pilot.step(1 / 30.0)
    run.fx.texts.clear()
    run.evo_banner = None
    run.waves.announce_timer = 0.0            # "HEPSİ MOR!" gibi dalga duyuruları çıkmasın
    c = sh.display.canvas
    sh._draw_run_frame(c, aim_pos=tr.pilot.aim)

    out = pygame.Surface((W, H))
    # yakın plan: oyuncu ile ejderhanın ortası, HUD dışarıda kalsın
    px, py = run.world_to_screen(run.player.x, run.player.y)
    qx, qy = run.world_to_screen(dg.x, dg.y)
    z = 1.45
    w, h = K.VIRTUAL_W / z, K.VIRTUAL_H / z
    fx, fy = (px * 0.6 + qx * 0.4) - 120, (py * 0.6 + qy * 0.4)
    x = K.clamp(fx - w / 2, 0, K.VIRTUAL_W - w)
    y = K.clamp(fy - h / 2, 90, K.VIRTUAL_H - h - 60)   # üst ve alt HUD kadraj dışında
    pygame.transform.smoothscale(c.subsurface(pygame.Rect(int(x), int(y), int(w), int(h))), (W, H), out)
    out.fill((255, 190, 170), special_flags=pygame.BLEND_MULT)
    out.fill((18, 0, 6), special_flags=pygame.BLEND_ADD)

    # sol tarafı yazı için karart
    lay = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(W):
        a = int(235 * max(0.0, 1.0 - i / (W * 0.62)) ** 1.3)
        pygame.draw.line(lay, (8, 4, 14, a), (i, 0), (i, H))
    out.blit(lay, (0, 0))
    out.blit(tr.vignette, (0, 0))

    # ---- sağ: evrimleşmiş silah (ZİNCİRLİ TIRPAN, III) ----
    ecol = tuple(K.evo_color("axe", 3))
    ex, ey = 1480, 560
    rays = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(24):
        a = i * math.tau / 24
        pygame.draw.polygon(rays, (255, 210, 120, 34),
                            [(ex, ey), (ex + math.cos(a - .06) * 900, ey + math.sin(a - .06) * 900),
                             (ex + math.cos(a + .06) * 900, ey + math.sin(a + .06) * 900)])
    out.blit(rays, (0, 0))
    K.add_glow(out, ex, ey, 420, ecol, 0.75)
    K.add_glow(out, ex, ey, 260, (255, 230, 170), 0.45)
    evw = dict(K.WEAPON_BY_KEY["axe"])
    evw["color"] = ecol
    K.draw_weapon_emblem(out, ex, ey, 520, evw, 1.3, locked=False, glow=True)
    badge = tr.T.render("EVRİM III", 64, ecol, "black", 7, grad=((255, 255, 235), ecol), glow=ecol)
    out.blit(badge, (ex - badge.get_width() / 2, ey + 270))
    name = tr.T.render(K.evo_name("axe", 3), 46, (255, 236, 220), "black", 6)
    out.blit(name, (ex - name.get_width() / 2, ey + 360))

    # ---- sol: logo + kapak yazıları ----
    logo = K.brand_scaled("logo", w=760)
    if logo is not None:
        out.blit(logo, (70, 46))
    big = tr.T.render("EVRİM!", 300, T.GOLD, "black", 14, scol=(40, 10, 0),
                      grad=((255, 255, 225), (255, 150, 20)), glow=(255, 120, 0))
    out.blit(big, (40, 330))
    sub = tr.T.render("20 SİLAH · 60 EVRİM", 92, T.WHITE, "black", 9, grad=(T.WHITE, (255, 214, 170)))
    out.blit(sub, (70, 690))
    tag = tr.T.render("CEHENNEMDE HAYATTA KALABİLECEK MİSİN?", 50, (255, 120, 90), "black", 6,
                      grad=((255, 220, 200), (255, 70, 40)))
    out.blit(tag, (74, 830))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    final = pygame.transform.smoothscale(out, (1280, 720))
    tmp = os.path.splitext(args.out)[0] + "_tmp.png"
    pygame.image.save(final, tmp)
    try:
        from PIL import Image
        Image.open(tmp).convert("RGB").save(args.out, "JPEG", quality=92, optimize=True)
        os.remove(tmp)
    except Exception:
        os.replace(tmp, os.path.splitext(args.out)[0] + ".png")
    print("kapak:", args.out)


if __name__ == "__main__":
    main()
