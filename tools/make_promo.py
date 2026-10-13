"""ARENA BONK — 1.5 dakikalık REKLAM FİLMİ (MP4) üretir (v3.38).

make_trailer.py 2 dakikalık ÖĞRETİCİ turu kaydeder; bu araç ise oyuncuyu
ekrana kilitleyen, hızlı kurgulu bir REKLAM çeker: soğuk açılış (dev
kalabalık + BONK), logo, temel oynanış, seviye kartları, 6 silahlık geçit,
kitaplar, harita seçimi ve 3 dünya (Buzul / Orman / Çöl, kendi yaratıkları ve
patronlarıyla), şampiyon patron, 25. dalga sonrası ÖFKE, cehennem kapısı,
40 dalgalık CEHENNEM, şampiyon ejderha, güç gösterisi, dünya sıralaması ve
çağrı. Sahneler arasında 6 çeşit geçiş: altın perde, beyaz çakma, yakınlaşma,
kayma, daire açılımı ve bozulma (glitch).

Her kare oyunun GERÇEK motorudur (GameTour'un gölge oyunu, kaydın kopyası);
gerçek kayda, hesaba ve sunucuya hiçbir şey yazılmaz. Ses: oyunun kendi
efektleri + sahnelere oturan 128 BPM müzik (make_trailer'ın enstrümanları).

Kullanım:
    python tools/make_promo.py                       # trailer/arena_bonk_reklam.mp4
    python tools/make_promo.py --seconds 12 --out deneme.mp4
    python tools/make_promo.py --max-mb 29           # boyutu sınırla (iki geçişli kodlama)
Gerekenler: pygame(-ce), numpy, ffmpeg (PATH'te).
"""
import os
import sys
import math
import time
import random
import argparse
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import make_trailer as MT   # noqa: E402  (ortamı, pygame'i ve oyunu o hazırlar)
import numpy as np          # noqa: E402
import pygame               # noqa: E402

K = MT.K
_tc = K._tc
W, H = K.VIRTUAL_W, K.VIRTUAL_H
ROOT = MT.ROOT

# Silah geçidi: (silah, ekranda kalma süresi)
PARADE = ("tesla", "tornado", "meteor", "wolves", "beam", "ghost_swords")
PARADE_STEP = 1.25

# Dünyalar: harita -> (gösterilecek patron türü, renk)
WORLDS = {
    "frost": ("witch", (170, 220, 255)),
    "jungle": ("colossus", (150, 240, 110)),
    "desert": ("warlord", (255, 206, 110)),
}


class _MapPilot(K._TourPilot):
    """Harita sahnelerinde yeni gelen yaratıklar o haritanın yaratıkları olsun."""

    def spawn(self):
        run = self.run
        x, y = run.near_camera_point()
        w = run.waves.wave
        kind = random.choice(("red", "red", "blue", "yellow", "tank", "sprinter", "brute"))
        run.enemies.append(K.make_map_enemy(run.map_theme, kind, x, y, run.wave_hp_mult(w), 1.0, wave=w))


class _RagePilot(K._TourPilot):
    """Öfke sahnesi: kırmızılar, yarasalar ve dibine sokulan kamikazeler."""

    def spawn(self):
        run = self.run
        x, y = run.near_camera_point()
        w = run.waves.wave
        kind = random.choice(("red", "red", "blue", "blue", "sprinter", "kamikaze", "brute"))
        run.enemies.append(K.Enemy(kind, x, y, run.wave_hp_mult(w), 1.0, wave=w))


class PromoFilm(MT.GameTrailer):
    # (ad, süre, giriş geçişi)
    # geçişler: wipe (altın perde), flash (beyaz çakma), zoom (eski kare
    # büyüyüp söner), slide (yeni sahne sağdan iter), iris (daire açılır),
    # glitch (bozulma), "" (yok)
    SCENES = (
        ("cold", 4.0, ""), ("title", 3.0, "flash"), ("basics", 4.6, "slide"),
        ("levelup", 5.6, "zoom"), ("arsenal", 9.0, "flash"), ("books", 6.0, "wipe"),
        ("worlds", 5.0, "iris"), ("frost", 2.8, "glitch"), ("jungle", 2.8, "slide"),
        ("desert", 2.8, "slide"), ("boss", 5.6, "wipe"), ("rage", 5.6, "flash"),
        ("gate", 5.0, "wipe"), ("hell", 6.6, "zoom"), ("dragon", 5.4, "flash"),
        ("power", 5.0, "flash"), ("worldlb", 6.0, "wipe"), ("outro", 5.2, "iris"),
    )
    LENGTH = sum(d for _n, d, _w in SCENES)
    PLAY_SCENES = ("cold", "basics", "arsenal", "frost", "jungle", "desert", "boss", "rage",
                   "gate", "hell", "dragon", "power")
    CUT_LEN = {"wipe": 0.32, "flash": 0.22, "zoom": 0.38, "slide": 0.34, "iris": 0.42,
               "glitch": 0.26}

    def __init__(self, real_app):
        super().__init__(real_app)
        self._last = None          # bir önceki karenin kopyası (geçişler için)
        self._from = None          # geçişte "eski sahne" karesi
        # Harita zeminleri ve harita seçim ekranının manzaraları/armaları ilk
        # kez çizilirken yavaş: film ortasında boş kare çıkmasın diye şimdi.
        for th in K.MAP_THEMES:
            try:
                K.floor_surface(th)
            except Exception:
                pass
            for size in (K.MS_CARD_SCENE, K.MS_BIG_SCENE):
                try:
                    K.map_scene(th, size[0], size[1])
                except Exception:
                    pass
            for w, _a in K.ms_weapons_for(th):
                if w is not None:
                    try:
                        K.ms_weapon_emblem(None, 0, 0, 24, w, not self.sh.save.owns_weapon(w["key"]))
                    except Exception:
                        pass
            try:
                K._ms_detail_static(self.sh, th)
            except Exception:
                pass
        self._embers = [(random.uniform(0, W), random.uniform(0, H), random.uniform(0.4, 1.0))
                        for _ in range(70)]
        # Reklamda oyunun kendi duyuruları (tüccar ipucu, dalga eşiği, kombo,
        # dalga başlığı) altyazılarla çakışmasın: bunlar filmde gizlenir.
        self._mute_txt = {K.L("m.hint")}
        for key in K.STRINGS:
            if key.startswith("th."):
                self._mute_txt.add(K.L(key))

    # ------------------------------------------------------------------
    # ÇERÇEVE: sahneyi çiz, sonra geçişi eski karenin üstüne kur
    # ------------------------------------------------------------------
    def update(self, dt):
        dt = min(dt, 1 / 20.0)
        self.t = min(self.LENGTH, self.t + dt)
        self.sh.t += dt
        i, name, st, dur, cut = self._scene()
        first = i != self.scene_i
        if first:
            self.scene_i = i
            self.prev = -1.0
            self._from = self._last
        getattr(self, "_s_" + name)(st, dt, first)
        c = self.sh.display.canvas
        for (pos, t0) in self.clicks:
            k = (self.t - t0) / 0.45
            if 0 <= k <= 1:
                K.ring_aa(c, pos[0], pos[1], 8 + 34 * k, (255, 236, 170), max(1, int(5 * (1 - k))))
        if name in self.PLAY_SCENES:
            logo = K.brand_scaled("logo", h=54)
            if logo is not None:
                c.blit(logo, (W - logo.get_width() - 16, H - logo.get_height() - 12))
        self._letterbox(c, name, st, dur)
        self._transition(c, cut, st)
        self.prev = st
        self._last = c.copy()

    def _apply_cam(self, c, z, cx, cy):
        """Kamera itişi: karenin (cx, cy) çevresini z kat büyütür."""
        if z <= 1.001:
            return
        w, h = W / z, H / z
        x = K.clamp(cx - w / 2, 0, W - w)
        y = K.clamp(cy - h / 2, 0, H - h)
        part = c.subsurface(pygame.Rect(int(x), int(y), int(w), int(h))).copy()
        c.blit(pygame.transform.smoothscale(part, (W, H)), (0, 0))

    def _push(self, st, dur, z0, z1, p0, p1):
        """Sahne boyunca yumuşak kamera itişi (Ken Burns). Altyazılardan ÖNCE
        çağrılır: yazılar büyümez, kesilmez."""
        k = K.clamp(st / max(1e-6, dur), 0.0, 1.0)
        k = k * k * (3 - 2 * k)
        self._apply_cam(self.sh.display.canvas, z0 + (z1 - z0) * k,
                        p0[0] + (p1[0] - p0[0]) * k, p0[1] + (p1[1] - p0[1]) * k)

    def _play(self, dt, step=True):
        """Oyunu oynat; oyunun kendi büyük duyurularını reklamda gizle."""
        sh = self.sh
        run = sh.run
        if run is not None:
            run.waves.announce_timer = 0.0
            if run.fx.texts:
                seen = set()
                keep = []
                for ft in run.fx.texts:
                    if self._keep_text(ft) and (ft.size < 20 or ft.text not in seen):
                        seen.add(ft.text)
                        keep.append(ft)
                run.fx.texts[:] = keep
        super()._play(dt, step)

    def _keep_text(self, ft):
        tx = ft.text
        if tx in self._mute_txt:
            return False
        if tx.startswith("COMBO") or tx.startswith("КОМБО"):
            return False
        # büyük yazılı duyurular (seviye atladın, sürüye yeni kurt...) gizlenir;
        # hasar sayıları ve sandık / kapı duyuruları kalır
        if ft.size >= 20 and not tx[:1].isdigit() and tx[:1] not in "+-":
            return any(w in tx for w in ("SANDIK", "CEHENNEM KAPISI"))
        return True

    def _letterbox(self, c, name, st, dur):
        """Sinema şeritleri: oyun sahnelerinde ince siyah bant (film hissi)."""
        if name not in self.PLAY_SCENES:
            return
        h = 18
        pygame.draw.rect(c, (0, 0, 0), pygame.Rect(0, 0, W, h))
        pygame.draw.rect(c, (0, 0, 0), pygame.Rect(0, H - h, W, h))

    def _transition(self, c, cut, st):
        ln = self.CUT_LEN.get(cut, 0.0)
        if not cut or st >= ln or self.t < 0.5:
            return
        k = st / ln
        old = self._from
        if cut == "wipe":
            x0 = -260 + (W + 520) * k
            if old is not None:           # perdenin sağı hâlâ eski sahne
                c.blit(old, (int(x0 + 150), 0), pygame.Rect(int(x0 + 150), 0, W, H))
            pygame.draw.polygon(c, (236, 186, 92), [(x0, 0), (x0 + 300, 0), (x0 + 80, H), (x0 - 220, H)])
            pygame.draw.polygon(c, (255, 242, 205), [(x0 + 230, 0), (x0 + 300, 0), (x0 + 80, H),
                                                     (x0 + 10, H)])
        elif cut == "flash":
            fl = pygame.Surface((W, H))
            fl.fill((255, 250, 235))
            fl.set_alpha(int(235 * (1.0 - k) ** 1.6))
            c.blit(fl, (0, 0))
        elif cut == "zoom" and old is not None:
            e = K.ease_out_cubic(k)
            s = 1.0 + 0.7 * e
            img = pygame.transform.smoothscale(old, (int(W * s), int(H * s)))
            img.set_alpha(int(255 * (1.0 - e)))
            c.blit(img, (int(W / 2 - img.get_width() / 2), int(H / 2 - img.get_height() / 2)))
            fl = pygame.Surface((W, H))
            fl.fill((255, 236, 200))
            fl.set_alpha(int(120 * (1.0 - k) ** 2))
            c.blit(fl, (0, 0))
        elif cut == "slide" and old is not None:
            e = K.ease_out_cubic(k)
            new = c.copy()
            c.fill((0, 0, 0))
            off = int(W * e)
            c.blit(old, (-off, 0))
            c.blit(new, (W - off, 0))
            # hız çizgileri + altın kenar
            pygame.draw.rect(c, (255, 214, 120), pygame.Rect(W - off - 6, 0, 8, H))
            lay = pygame.Surface((W, H), pygame.SRCALPHA)
            rnd = random.Random(int(self.t * 60))
            for _ in range(26):
                y = rnd.randrange(0, H)
                ln_ = rnd.randrange(120, 420)
                x = W - off + rnd.randrange(-60, 200)
                pygame.draw.line(lay, (255, 250, 230, 150), (x, y), (x + ln_, y), 2)
            c.blit(lay, (0, 0))
        elif cut == "iris" and old is not None:
            e = K.ease_out_cubic(k)
            r = int(30 + math.hypot(W, H) * 0.55 * e)
            top = old.copy()
            top.set_colorkey((1, 0, 1))
            pygame.draw.circle(top, (1, 0, 1), (W // 2, H // 2), r)
            c.blit(top, (0, 0))
            K.ring_aa(c, W // 2, H // 2, r, (255, 220, 140), max(2, int(10 * (1 - e))))
        elif cut == "glitch":
            src = c.copy()
            rnd = random.Random(int(self.t * 240))
            band = 0
            while band < H:
                hgt = rnd.randrange(8, 46)
                use_old = old is not None and rnd.random() < 0.55 * (1.0 - k)
                img = old if use_old else src
                dx = int(rnd.uniform(-70, 70) * (1.0 - k))
                c.blit(img, (dx, band), pygame.Rect(0, band, W, hgt))
                band += hgt
            # renk kayması (kırmızı / camgöbeği)
            for col, dx in (((255, 40, 60), 6), ((40, 230, 255), -6)):
                tint = src.copy()
                tint.fill(col, special_flags=pygame.BLEND_RGB_MULT)
                tint.set_alpha(int(70 * (1.0 - k)))
                c.blit(tint, (dx, 0))

    # ------------------------------------------------------------------
    # yardımcılar
    # ------------------------------------------------------------------
    def _map_run(self, theme, wave, weapons, level, crowd, books=None):
        run = self._fresh_run(wave, weapons, level, crowd, books=books)
        run.set_map_theme(theme)
        run.waves.announce_timer = 0.0
        self.pilot = _MapPilot(run, crowd=crowd)
        return run

    def _spawn_map_ring(self, run, theme, n, rmin=150, rmax=380):
        p = run.player
        w = run.waves.wave
        for _ in range(n):
            a = random.uniform(0, math.tau)
            d = random.uniform(rmin, rmax)
            x = K.clamp(p.x + math.cos(a) * d, K.ARENA_RECT.left + 40, K.ARENA_RECT.right - 40)
            y = K.clamp(p.y + math.sin(a) * d * 0.75, K.ARENA_RECT.top + 40, K.ARENA_RECT.bottom - 40)
            kind = random.choice(("red", "red", "blue", "yellow", "tank", "sprinter", "brute"))
            run.enemies.append(K.make_map_enemy(theme, kind, x, y, run.wave_hp_mult(w), 1.0, wave=w))

    def _add_boss(self, run, kind, dx, dy, hellish=False, theme=None, champion=1):
        p = run.player
        b = K.Boss(kind, K.clamp(p.x + dx, K.ARENA_RECT.left + 80, K.ARENA_RECT.right - 80),
                   K.clamp(p.y + dy, K.ARENA_RECT.top + 80, K.ARENA_RECT.bottom - 80),
                   1.0, 1.0, run.waves.wave, hellish=hellish, theme=theme, champion=champion)
        run.bosses.append(b)
        K.scale_bosses_to_player(run.bosses, p)
        run.waves.boss_active = True
        return b

    def _big_text(self, text, st, y, col, size=86, life=9.0, sub=None, sub_col=(240, 236, 250)):
        """Kinetik başlık: hafif büyüyerek iner, gölgeli ve parlak."""
        if st < 0 or st > life:
            return
        c = self.sh.display.canvas
        k = K.ease_out_cubic(min(1.0, st / 0.22))
        a = min(1.0, (life - st) / 0.3)
        sz = int(size * (1.35 - 0.35 * k))
        K.add_glow(c, W / 2, y, 300, col, 0.22 * k * a)
        K.draw_text(c, text, (W / 2 + 4, y + 5), sz, (0, 0, 0), bold=True, center=True,
                    alpha=int(160 * a), shadow=False)
        K.draw_text(c, text, (W / 2, y), sz, col, bold=True, center=True, alpha=int(255 * a))
        if sub and st > 0.25:
            q = min(1.0, (st - 0.25) / 0.3) * a
            K.draw_text(c, sub, (W / 2, y + size * 0.62 + 14), 26, sub_col, bold=True,
                        center=True, alpha=int(255 * q))

    def _corner_tag(self, text, st, col, life):
        """Sol üstte kayarak giren küçük etiket (ör. 'DALGA 28')."""
        if st < 0 or st > life:
            return
        c = self.sh.display.canvas
        k = min(K.ease_out_cubic(st / 0.3), K.ease_out_cubic((life - st) / 0.25))
        tw = K.text_width(text, 26, True) + 40
        x = -tw + (tw + 24) * k
        r = pygame.Rect(int(x), 92, int(tw), 44)
        bar = pygame.Surface(r.size, pygame.SRCALPHA)
        bar.fill((10, 8, 18, 215))
        c.blit(bar, r.topleft)
        pygame.draw.rect(c, col, pygame.Rect(r.x, r.y, 6, r.h))
        K.draw_text(c, text, (r.x + 22, r.y + 8), 26, col, bold=True)

    def _embers_draw(self, c, st, col=(255, 170, 80), up=True):
        for i, (x, y, s) in enumerate(self._embers):
            yy = (y - st * 60 * s) % H if up else (y + st * 40 * s) % H
            xx = (x + math.sin(st * 1.3 + i) * 14) % W
            K.blit_disc(c, xx, yy, 1.2 + 2.2 * s, col, int(120 + 110 * s))

    # ==================================================================
    # SAHNELER
    # ==================================================================
    def _s_cold(self, st, dt, first):
        if first:
            run = self._fresh_run(18, {"tesla": 16, "tornado": 14, "beam": 16, "pentagram": 16,
                                       "meteor": 12},
                                  48, 70, books={"r_dmg": (10, 3), "r_aspd": (8, 3)})
            self._spawn_ring(run, 70, rmin=120, rmax=420)
            K.sfx("boss", 0.8, 0.0)
        run = self.sh.run
        if self.hit(st, 1.55):
            self._big_bonk(run)
        self._play(dt)
        self._big_text(_tc("1 KAHRAMAN.", "1 HERO.", "1 HÉROE.", "1 HELD.", "1 ГЕРОЙ."), st - 0.15, 250,
                       (255, 236, 182), size=78, life=1.35)
        self._big_text(_tc("BİN CANAVAR.", "A THOUSAND MONSTERS.", "MIL MONSTRUOS.", "TAUSEND MONSTER.",
                           "ТЫСЯЧА МОНСТРОВ."), st - 1.55, 250, (255, 110, 80), size=82, life=1.0)
        self._big_text(_tc("HAZIR MISIN?", "ARE YOU READY?", "¿ESTÁS LISTO?", "BIST DU BEREIT?",
                           "ТЫ ГОТОВ?"), st - 2.6, 360, K.GOLD, size=96, life=1.1)

    def _s_title(self, st, dt, first):
        c = self.sh.display.canvas
        c.blit(self._grad_bg(), (0, 0))
        cx, cy = W / 2, H / 2 - 40
        self._rays(c, cx, cy, st * 1.6, alpha=34)
        K.add_glow(c, cx, cy, 520, (230, 150, 60), 0.34)
        self._embers_draw(c, st)
        logo = K.brand_scaled("logo", w=900)
        if logo is not None:
            k = min(1.0, st / 0.28)
            s = 2.4 - 1.4 * K.ease_out_cubic(k)
            if st > 0.28:                          # çarpınca hafif sekme
                s = 1.0 + 0.05 * math.sin((st - 0.28) * 22) * math.exp(-(st - 0.28) * 6)
            img = pygame.transform.smoothscale(logo, (int(logo.get_width() * s), int(logo.get_height() * s)))
            img.set_alpha(int(255 * min(1.0, st / 0.12)))
            c.blit(img, (cx - img.get_width() / 2, cy - img.get_height() / 2))
        if st > 0.28:
            q = min(1.0, (st - 0.28) / 0.6)
            K.ring_aa(c, cx, cy, 160 + 620 * q, (255, 230, 170), max(1, int(14 * (1 - q))))
        if self.hit(st, 0.28):
            K.sfx("bonk", 1.0, 0.0)
        if st > 1.0:
            a = int(255 * min(1.0, (st - 1.0) / 0.35))
            K.draw_text(c, _tc("HAYATTA KAL · GÜÇLEN · ZİRVEYE ÇIK", "SURVIVE · POWER UP · REACH THE TOP",
                               "SOBREVIVE · MEJORA · LLEGA A LA CIMA", "ÜBERLEBE · WERDE STARK · AB NACH OBEN",
                               "ВЫЖИВИ · УСИЛЬСЯ · ПОКОРИ ВЕРШИНУ"),
                        (cx, cy + 200), 34, (255, 236, 182), bold=True, center=True, alpha=a)

    def _s_basics(self, st, dt, first):
        if first:
            run = self._fresh_run(4, {"axe": 4, "whip": 3}, 6, 24)
            self._spawn_ring(run, 22)
        run = self.sh.run
        if self.hit(st, 3.0):
            self._big_bonk(run)
        self._play(dt)
        self.cap(_tc("KOŞ · NİŞAN AL · BONKLA!", "RUN · AIM · BONK!", "CORRE · APUNTA · ¡BONK!",
                     "LAUF · ZIEL · BONK!", "БЕГИ · ЦЕЛЬСЯ · БОНК!"),
                 _tc("WASD koş, fareyle vur, SPACE ile etrafındakileri savur.",
                     "WASD to run, mouse to shoot, SPACE to blast them all away.",
                     "WASD para correr, ratón para disparar, ESPACIO para barrerlos.",
                     "WASD laufen, Maus schießen, LEERTASTE fegt alle weg.",
                     "WASD — бег, мышь — огонь, ПРОБЕЛ раскидывает всех."),
                 st - 0.3, 4.1, col=(140, 230, 170))
        self.stamp("BONK!", st - 3.0, K.GOLD, y=250, life=1.2)

    def _s_levelup(self, st, dt, first):
        sh = self.sh
        if first:
            run = self._fresh_run(9, {"axe": 6, "whip": 5, "tornado": 4}, 14, 10)
            try:
                p = run.player
                o1 = run._weapon_offer(K.WEAPON_BY_KEY["tesla"], 1, True)
                o1["rarity"], o1["boost"] = 4, K.rarity_boost(4, "card")
                lv = p.books.get("r_dmg", 0) + 1
                o2 = run._book_offer(K.BOOK_BY_KEY["r_dmg"], lv, lv == 1)
                o2["rarity"], o2["gains"] = 3, K.book_gain("r_dmg", 3, lv)
                o3 = run._weapon_offer(K.WEAPON_BY_KEY["beam"], 1, True)
                o3["rarity"], o3["boost"] = 1, K.rarity_boost(1, "card")
                run.levelup_choices = [o1, o2, o3]
                run.pending_levelups = 1
                sh.state = K.STATE_LEVELUP
                K.sfx("levelup", 1.0, 0.0)
            except Exception:
                sh.state = K.STATE_PLAY
        run = sh.run
        if sh.state == K.STATE_LEVELUP:
            sh.levelup_ui.rebuild(run.levelup_choices)
            cards = [r.center for (r, _c, _i) in sh.levelup_ui.cards] or [(640, 360)] * 3
            cards = (cards + [cards[-1]] * 3)[:3]
            m = self.path([(0.0, (640, 690)), (0.7, cards[2]), (1.5, cards[2]), (2.1, cards[1]),
                           (2.9, cards[1]), (3.5, cards[0]), (6.0, cards[0])], st)
            clicked = self.at(st, 4.3)
            if clicked:
                self.clicks.append((m, self.t))
                self.hits.append(self.t)
            sh.update_levelup(dt, m, clicked)
            self.cursor(m)
        else:
            self._play(dt)
            self.stamp(_tc("EFSANEVİ!", "LEGENDARY!", "¡LEGENDARIO!", "LEGENDÄR!", "ЛЕГЕНДАРНО!"),
                       st - 4.35, (255, 196, 70), y=250, life=1.25)
        self.cap(_tc("HER SEVİYEDE 3 KART", "3 CARDS EVERY LEVEL", "3 CARTAS CADA NIVEL",
                     "3 KARTEN JEDES LEVEL", "3 КАРТЫ КАЖДЫЙ УРОВЕНЬ"),
                 _tc("Yaygın → Nadir → Epik → EFSANEVİ. Şansın arttıkça kartların parlar!",
                     "Common → Rare → Epic → LEGENDARY. More luck, shinier cards!",
                     "Común → Rara → Épica → LEGENDARIA. ¡Más suerte, cartas más brillantes!",
                     "Gewöhnlich → Selten → Episch → LEGENDÄR. Mehr Glück, bessere Karten!",
                     "Обычная → Редкая → Эпик → ЛЕГЕНДА. Больше удачи — ярче карты!"),
                 st - 0.25, 3.9, y=604, col=(255, 200, 90))

    def _s_arsenal(self, st, dt, first):
        sh = self.sh
        if first:
            run = self._fresh_run(14, {PARADE[0]: 14}, 30, 46, books={"r_dmg": (6, 2), "r_aspd": (5, 2)})
            self._spawn_ring(run, 40)
            self.flags.discard("parade_all")
            self._parade_i = 0
        run = sh.run
        p = run.player
        n = len(PARADE)
        idx = min(n, int(st / PARADE_STEP))
        if idx != self._parade_i:
            self._parade_i = idx
            if idx < n:
                p.weapons = {PARADE[idx]: 14}
            else:
                p.weapons = {k: 12 for k in PARADE}
                p.weapons.update({"pentagram": 12})
            for k in p.weapons:
                p.weapon_timers[k] = 0.0
            self.hits.append(self.t)
            if len(run.enemies) < 30:
                self._spawn_ring(run, 26)
        if idx >= n and self.hit(st, n * PARADE_STEP + 0.6):
            self._big_bonk(run)
        self._play(dt)
        c = sh.display.canvas
        # her silah değişiminde kısa beyaz çakma
        ph = st - min(idx, n) * PARADE_STEP
        if idx > 0 and ph < 0.12:
            fl = pygame.Surface((W, H))
            fl.fill((255, 250, 235))
            fl.set_alpha(int(150 * (1.0 - ph / 0.12)))
            c.blit(fl, (0, 0))
        if idx < n:
            w = K.WEAPON_BY_KEY[PARADE[idx]]
            self._weapon_card(c, w, ph, PARADE_STEP, idx)
        else:
            self._big_text(_tc("HEPSİNİ BİRLEŞTİR!", "COMBINE THEM ALL!", "¡COMBÍNALAS TODAS!",
                               "KOMBINIERE ALLE!", "ОБЪЕДИНИ ВСЁ!"), ph, 250, K.GOLD, size=80,
                           life=1.5, sub=_tc("20 silah · her koşu bambaşka bir takım",
                                             "20 weapons · a brand-new build every run",
                                             "20 armas · una build nueva en cada partida",
                                             "20 Waffen · jeder Lauf ein neuer Build",
                                             "20 видов оружия · новый билд каждый забег"))
        self._corner_tag(_tc("SİLAHLAR", "WEAPONS", "ARMAS", "WAFFEN", "ОРУЖИЕ"), st, (255, 214, 120), 7.4)

    def _weapon_card(self, c, w, ph, life, idx):
        """Silah geçidinin alt şeridi: arma + ad + sayaç."""
        k = min(K.ease_out_cubic(ph / 0.25), K.ease_out_cubic(max(0.0, life - ph) / 0.15))
        col = tuple(w.get("color", (255, 214, 120)))
        r = pygame.Rect(0, 0, 560, 96)
        r.midbottom = (W // 2, int(H - 40 + (1.0 - k) * 140))
        bar = pygame.Surface(r.size, pygame.SRCALPHA)
        bar.fill((10, 8, 18, 225))
        c.blit(bar, r.topleft)
        pygame.draw.rect(c, col, r, width=3, border_radius=4)
        K.add_glow(c, r.x + 56, r.centery, 70, col, 0.35 * k)
        try:
            K.ms_weapon_emblem(c, r.x + 56, r.centery, 64, w, False)
        except Exception:
            K.draw_icon(c, r.x + 56, r.centery, w.get("icon", "star"), col, r=26)
        nm = K.w_name(w).upper()
        sz = 40
        while sz > 22 and K.text_width(nm, sz, True) > r.w - 150:
            sz -= 2
        K.draw_text(c, nm, (r.x + 112, r.y + 14), sz, col, bold=True)
        K.draw_text(c, "%d / %d" % (idx + 1, len(PARADE)), (r.x + 114, r.y + 62), 18,
                    (210, 204, 226), bold=True)

    def _s_books(self, st, dt, first):
        sh = self.sh
        if first:
            sh.goto(K.STATE_BOOK_MARKET)
            sh.book_filter = "all"
            self.music.append((self.t, "menu"))
        if st < 2.9:
            sh.book_scroll = 120 * K.ease_out_cubic(st / 2.6)
        m = self.path([(0.0, (1069, 371)), (1.1, (783, 330)), (2.2, (783, 330)), (2.8, (786, 123)),
                       (3.4, (786, 123)), (4.4, (560, 300)), (6.0, (560, 300))], st)
        clicked = self.at(st, 3.0)
        if clicked:
            self.clicks.append((m, self.t))
            self.hits.append(self.t)
        sh.update_book_market(dt, m, clicked, 0)
        self.cursor(m)
        self._push(st, 6.0, 1.0, 1.18, (640, 330), (640, 300))
        self.cap(_tc("30 KİTAP", "30 BOOKS", "30 LIBROS", "30 BÜCHER", "30 КНИГ"),
                 _tc("Hasar, can, şans, vampir... 4 kitap taşı, her biri 30. seviyeye büyür.",
                     "Damage, health, luck, vampire... carry 4, each grows to level 30.",
                     "Daño, vida, suerte, vampiro... lleva 4, cada uno sube al nivel 30.",
                     "Schaden, Leben, Glück, Vampir... trage 4, jedes bis Stufe 30.",
                     "Урон, здоровье, удача, вампиризм... носи 4, каждая до 30 уровня."),
                 st - 0.2, 2.8, col=(196, 150, 255))
        self.cap(_tc("NADİR KİTAPLAR", "RARE BOOKS", "LIBROS RAROS", "SELTENE BÜCHER", "РЕДКИЕ КНИГИ"),
                 _tc("Zehir, Yankı, Çoklu Atış... tek seçim koşunu baştan yazar.",
                     "Poison, Echo, Multishot... one pick rewrites your run.",
                     "Veneno, Eco, Multidisparo... una elección cambia tu partida.",
                     "Gift, Echo, Mehrfachschuss... eine Wahl schreibt deinen Lauf neu.",
                     "Яд, Эхо, Мультивыстрел... один выбор меняет забег."),
                 st - 3.1, 2.8, col=(255, 200, 90))

    def _s_worlds(self, st, dt, first):
        sh = self.sh
        if first:
            sh.set_selected_map("stone")
            sh.open_map_select()
            sh.state = K.STATE_MAP_SELECT
        cards = [K._ms_card_rect(i).center for i in range(len(K.MAP_THEMES))]
        m = self.path([(0.0, (640, 690)), (0.5, cards[0]), (0.9, cards[0]), (1.25, cards[1]),
                       (1.55, cards[2]), (1.85, cards[3]), (2.2, cards[1]), (5.0, (900, 420))], st)
        clicked = self.at(st, 2.45)
        if clicked:
            self.clicks.append((m, self.t))
            self.hits.append(self.t)
        if sh.state == K.STATE_MAP_SELECT:
            sh.update_map_select(dt, m, clicked)
        self.cursor(m)
        self.cap(_tc("4 DÜNYA", "4 WORLDS", "4 MUNDOS", "4 WELTEN", "4 МИРА"),
                 _tc("Her dünyanın kendi canavarları, kendi patronu, kendi kuralı.",
                     "Every world has its own monsters, its own boss, its own rules.",
                     "Cada mundo tiene sus monstruos, su jefe y sus reglas.",
                     "Jede Welt hat eigene Monster, einen eigenen Boss, eigene Regeln.",
                     "В каждом мире свои монстры, свой босс и свои правила."),
                 st - 0.2, 4.6, y=596, col=(140, 210, 255))

    def _world_clip(self, theme, st, dt, first):
        boss_kind, col = WORLDS[theme]
        if first:
            run = self._map_run(theme, 12, {"tesla": 10, "tornado": 8, "beam": 10, "pentagram": 10},
                                28, 34, books={"r_dmg": (6, 2)})
            self._spawn_map_ring(run, theme, 30)
            self._add_boss(run, boss_kind, 250, -110, theme=theme)
            self.pilot.target = None
            K.sfx("boss", 0.7, 0.0)
        self._play(dt)
        nm = K.L("map.%s.name" % theme)
        boss_nm = K.map_boss_name(theme, boss_kind, "")
        self._big_text(nm.upper(), st - 0.1, 150, col, size=70, life=2.6,
                       sub=_tc("Patron: ", "Boss: ", "Jefe: ", "Boss: ", "Босс: ") + boss_nm)

    def _s_frost(self, st, dt, first):
        self._world_clip("frost", st, dt, first)

    def _s_jungle(self, st, dt, first):
        self._world_clip("jungle", st, dt, first)

    def _s_desert(self, st, dt, first):
        self._world_clip("desert", st, dt, first)

    def _s_boss(self, st, dt, first):
        sh = self.sh
        if first:
            run = self._fresh_run(20, {"tesla": 12, "tornado": 10, "beam": 12, "pentagram": 12}, 40, 10,
                                  books={"r_dmg": (8, 3)})
            run.chests.clear()
            self._add_boss(run, "colossus", 260, -60, champion=2)
            self.pilot.target = None
            K.sfx("boss", 1.0, 0.0)
            self.hits.append(self.t)
        run = sh.run
        if st > 3.9:
            for b in list(run.bosses):
                K.tour_kill_boss(b, run.fx)
            if self.hit(st, 3.95):
                self._big_bonk(run)
        self.pilot.target = None
        self._play(dt)
        self.cap(_tc("★ ŞAMPİYON PATRONLAR", "★ CHAMPION BOSSES", "★ JEFES CAMPEONES", "★ CHAMPION-BOSSE",
                     "★ БОССЫ-ЧЕМПИОНЫ"),
                 _tc("Her haritada başka yetenekler. Devir onu, SANDIĞI kap!",
                     "New skills on every map. Take it down, grab the CHEST!",
                     "Habilidades nuevas en cada mapa. ¡Derríbalo y toma el COFRE!",
                     "Neue Fähigkeiten auf jeder Karte. Besiege ihn, schnapp dir die TRUHE!",
                     "На каждой карте новые умения. Победи и забери СУНДУК!"),
                 st - 0.3, 3.5, col=(255, 110, 90))
        self.stamp(_tc("PATRON DEVRİLDİ!", "BOSS DOWN!", "¡JEFE DERROTADO!", "BOSS BESIEGT!", "БОСС ПОВЕРЖЕН!"),
                   st - 4.0, K.GOLD, y=250, life=1.5)

    def _s_rage(self, st, dt, first):
        sh = self.sh
        if first:
            run = self._fresh_run(K.RAGE_FROM + K.RAGE_FULL, {"tesla": 14, "tornado": 12, "beam": 14, "pentagram": 14,
                                       "wolves": 10},
                                  52, 50, books={"r_dmg": (10, 3), "r_armor": (8, 2)})
            self.pilot = _RagePilot(run, crowd=50)
            p = run.player
            w = run.waves.wave
            for _ in range(44):
                a = random.uniform(0, math.tau)
                d = random.uniform(160, 400)
                x = K.clamp(p.x + math.cos(a) * d, K.ARENA_RECT.left + 40, K.ARENA_RECT.right - 40)
                y = K.clamp(p.y + math.sin(a) * d * 0.75, K.ARENA_RECT.top + 40, K.ARENA_RECT.bottom - 40)
                kind = random.choice(("red", "red", "blue", "blue", "sprinter", "kamikaze", "kamikaze"))
                run.enemies.append(K.Enemy(kind, x, y, run.wave_hp_mult(w), 1.0, wave=w))
        self._play(dt)
        wv = self.sh.run.waves.wave
        self._corner_tag(_tc("DALGA %d", "WAVE %d", "OLEADA %d", "WELLE %d", "ВОЛНА %d") % wv, st, (255, 90, 60), 5.4)
        self._big_text(_tc("ÖFKE MODU", "RAGE MODE", "MODO FURIA", "WUTMODUS", "РЕЖИМ ЯРОСТИ"), st - 0.2,
                       170, (255, 80, 60), size=84, life=2.1,
                       sub=_tc("25. dalgadan sonra canavarlar kızarır, daha sert vurur",
                               "After wave 25 monsters burn red and hit harder",
                               "Tras la oleada 25 los monstruos arden y golpean más fuerte",
                               "Ab Welle 25 glühen Monster rot und schlagen härter zu",
                               "После 25-й волны монстры пылают и бьют сильнее"))
        self.cap(_tc("KAMİKAZELER!", "KAMIKAZES!", "¡KAMIKAZES!", "KAMIKAZES!", "КАМИКАДЗЕ!"),
                 _tc("Dibine sokulup patlarlar. Yarasalar morla parlayarak koşar. KAÇ!",
                     "They rush in and explode. Bats glow purple and charge. RUN!",
                     "Se acercan y explotan. Los murciélagos brillan en púrpura. ¡CORRE!",
                     "Sie stürmen heran und explodieren. Fledermäuse glühen lila. LAUF!",
                     "Подбегают и взрываются. Мыши светятся фиолетом. БЕГИ!"),
                 st - 2.4, 3.0, col=(236, 120, 255))

    def _s_gate(self, st, dt, first):
        sh = self.sh
        if first:
            run = self._fresh_run(K.HELL_PORTAL_WAVE, {"tesla": 14, "tornado": 12, "beam": 14,
                                                       "pentagram": 14}, 50, 4,
                                  books={"r_dmg": (10, 3)})
            run.enemies[:] = run.enemies[:4]
            run.open_hell_portal()
            self.pilot.crowd = 4
            self.hits.append(self.t)
        run = sh.run
        hp = run.hell_portal
        if run.biome != "hell" and hp is not None and st > 0.5:
            self.pilot.target = (hp.x, hp.y)
            self.pilot.use = st > 2.3
        if st > 3.8 and run.biome != "hell":
            run.enter_hell()
        if run.biome == "hell" and "gate_in" not in self.flags:
            self.flags.add("gate_in")
            self.pilot.use = False
            self.pilot.target = None
            self.pilot.crowd = 0
            self.pilot.cx, self.pilot.cy = run.player.x, run.player.y
            self.hits.append(self.t)
        self._play(dt)
        if run.biome == "hell":
            c = sh.display.canvas
            gin = next((float(f[7:]) for f in self.flags if f.startswith("gate_t=")), None)
            if gin is None:
                self.flags.add("gate_t=%.3f" % st)
                gin = st
            q = st - gin
            fl = pygame.Surface((W, H))
            fl.fill((255, 120, 40))
            fl.set_alpha(int(200 * max(0.0, 1.0 - q / 0.5)))
            c.blit(fl, (0, 0))
        self.cap(_tc("CEHENNEM KAPISI", "THE HELL GATE", "LA PUERTA DEL INFIERNO", "DAS HÖLLENTOR",
                     "ВРАТА АДА"),
                 _tc("25. dalga patronunu devir... ve kapıdan geç.",
                     "Beat the wave-25 boss... and step through.",
                     "Vence al jefe de la oleada 25... y cruza.",
                     "Besiege den Boss der Welle 25... und tritt hindurch.",
                     "Победи босса 25-й волны... и шагни внутрь."),
                 st - 0.3, 3.4, col=(200, 120, 255))

    def _s_hell(self, st, dt, first):
        sh = self.sh
        run = sh.run
        if first:
            self.flags.discard("gate_in")
            if run.biome != "hell":
                run.enter_hell()
            p = run.player
            p.weapons = {"tesla": 16, "tornado": 14, "beam": 16, "pentagram": 16, "meteor": 12, "nova": 12}
            for k in p.weapons:
                p.weapon_timers[k] = 0.0
            run.score = max(run.score, 61250)       # geç oyun skoru (HUD'da)
            run.record_beaten = True                 # rekor anı güç sahnesinde gelsin
            run.waves._begin_wave(31, run.score)
            run.waves.announce_timer = 0.0
            run.fx.texts.clear()
            self.pilot.cx, self.pilot.cy = p.x, p.y
            self.pilot.crowd = 48
            self._spawn_ring(run, 40)
        if self.hit(st, 3.3):
            self._big_bonk(run)
        self._play(dt)
        self._big_text(_tc("CEHENNEM", "HELL", "INFIERNO", "HÖLLE", "АД"), st - 0.05, 170, (255, 90, 50),
                       size=110, life=2.0, sub=_tc("40 dalga · lav · ateş · durmak yok",
                                                   "40 waves · lava · fire · no mercy",
                                                   "40 oleadas · lava · fuego · sin piedad",
                                                   "40 Wellen · Lava · Feuer · keine Gnade",
                                                   "40 волн · лава · огонь · без пощады"),
                       sub_col=(255, 214, 170))
        self.cap(_tc("SONUNA KADAR DAYANABİLİR MİSİN?", "CAN YOU LAST TO THE END?",
                     "¿AGUANTARÁS HASTA EL FINAL?", "HÄLTST DU BIS ZUM ENDE DURCH?",
                     "ПРОДЕРЖИШЬСЯ ДО КОНЦА?"),
                 _tc("Her dalga bir öncekinden sert. Sayaç 40'a dayanınca...",
                     "Every wave is harder than the last. When the counter hits 40...",
                     "Cada oleada es más dura. Cuando el contador llegue a 40...",
                     "Jede Welle ist härter. Wenn der Zähler 40 erreicht...",
                     "Каждая волна сильнее. Когда счётчик дойдёт до 40..."),
                 st - 2.6, 3.6, col=(255, 120, 60))

    def _s_dragon(self, st, dt, first):
        sh = self.sh
        run = sh.run
        if first:
            run.chests.clear()
            run.waves._begin_wave(40, run.score)
            run.waves.announce_timer = 0.0
            run.fx.texts.clear()
            cam = run.cam_rect()
            dg = K.Boss("dragon", cam.centerx + 260, cam.centery - 120, 1.0, 1.0, run.waves.wave,
                        hellish=True, champion=3)
            run.bosses.append(dg)
            K.scale_bosses_to_player(run.bosses, run.player)
            run.waves.boss_active = True
            self.pilot.crowd = 16
            self.pilot.target = None
            K.sfx("boss", 1.0, 0.0)
            self.hits.append(self.t)
        if st > 4.3:
            for b in list(run.bosses):
                K.tour_kill_boss(b, run.fx)
        self._play(dt)
        self._corner_tag(_tc("DALGA 40/40", "WAVE 40/40", "OLEADA 40/40", "WELLE 40/40", "ВОЛНА 40/40"),
                         st, (255, 90, 60), 5.2)
        self.cap(_tc("★ KOR EJDERHA UYANDI!", "★ THE EMBER DRAGON AWAKENS!", "★ ¡DESPIERTA EL DRAGÓN DE ASCUAS!",
                     "★ DER GLUTDRACHE ERWACHT!", "★ ПРОБУДИЛСЯ УГОЛЬНЫЙ ДРАКОН!"),
                 _tc("Cehennemde her patron +2 yetenekle gelir.",
                     "In hell every boss brings +2 extra skills.",
                     "En el infierno cada jefe trae +2 habilidades.",
                     "In der Hölle hat jeder Boss +2 Fähigkeiten.",
                     "В аду у каждого босса +2 умения."),
                 st - 0.3, 3.9, col=(255, 90, 60))
        self.stamp(_tc("EJDERHA DEVRİLDİ!", "DRAGON SLAIN!", "¡DRAGÓN ABATIDO!", "DRACHE BESIEGT!",
                       "ДРАКОН ПОВЕРЖЕН!"), st - 4.35, K.GOLD, y=250, life=1.05)

    def _s_power(self, st, dt, first):
        if first:
            run = self._fresh_run(20, {"tesla": 22, "tornado": 20, "beam": 22, "pentagram": 22,
                                       "meteor": 18, "wolves": 16, "ghost_swords": 16},
                                  80, 64, books={"r_dmg": (18, 4), "r_aspd": (14, 3), "r_crit": (12, 3)},
                                  hell=True)
            run.score = 20800                        # rekorun (21.450) hemen altı
            run.waves._begin_wave(36, run.score)
            run.waves.announce_timer = 0.0
            run.fx.texts.clear()
            self._spawn_ring(run, 56)
        run = self.sh.run
        if self.hit(st, 1.9):
            self._big_bonk(run)
        if self.at(st, 2.3):
            # oyunun KENDİ "YENİ REKOR!" anı (altın çakma + damga) tam burada
            run.score = max(run.score, 118400)
            self.hits.append(self.t)
        if self.hit(st, 3.6):
            self._big_bonk(run)
        self._play(dt)
        self.stamp(_tc("DURDURULAMAZ!", "UNSTOPPABLE!", "¡IMPARABLE!", "UNAUFHALTSAM!", "НЕУДЕРЖИМ!"),
                   st - 0.3, (255, 140, 60), y=300, life=1.85)

    def _s_worldlb(self, st, dt, first):
        """Turdaki dünya sıralaması sahnesi + podyuma doğru kamera itişi."""
        sh = self.sh
        if first:
            sh.state = K.STATE_MENU
            sh.online.world_scores = self._world_rows()
        if st < 1.3:
            m = self.path([(0.0, (640, 600)), (0.9, (640, 487)), (1.3, (640, 487))], st)
            if self.at(st, 1.0):
                self.click(m)
            sh.update_menu(dt, m, False)
            self.cursor(m)
            return
        if sh.state != K.STATE_WORLD_LB:
            sh.goto(K.STATE_WORLD_LB)
        m = self.path([(1.3, (640, 487)), (2.2, (760, 230)), (6.0, (760, 230))], st)
        sh.update_world_leaderboard(dt, m, False)
        self.cursor(m)
        self._push(st - 1.3, 4.7, 1.0, 1.3, (640, 330), (640, 250))
        c = sh.display.canvas
        for i in range(70):                    # altın konfeti
            x = (i * 97.7 + math.sin(st * 2 + i) * 30) % W
            y = ((st - 1.4) * (160 + (i % 7) * 30) + i * 23) % (H + 40) - 20
            col = ((255, 214, 110), (255, 120, 140), (120, 210, 255), (150, 240, 160))[i % 4]
            pygame.draw.rect(c, col, pygame.Rect(int(x), int(y), 6, 10))
        if self.hit(st, 1.4):
            K.sfx("buy", 1.0, 0.0)
        self.stamp(_tc("1. SENSİN!", "YOU'RE #1!", "¡ERES EL #1!", "DU BIST #1!", "ТЫ — №1!"),
                   st - 1.4, K.GOLD, y=420, life=2.0)
        self.cap(_tc("DÜNYA SIRALAMASI", "WORLD RANKING", "RANKING MUNDIAL", "WELTRANGLISTE",
                     "МИРОВОЙ РЕЙТИНГ"),
                 _tc("Zirveye kas, adın en üstte parlasın. Arkadaşların seni geçebilecek mi?",
                     "Grind to the top and see your name shine. Can your friends beat you?",
                     "Sube a la cima y haz brillar tu nombre. ¿Te superarán tus amigos?",
                     "Kämpf dich nach oben. Können deine Freunde dich schlagen?",
                     "Пробейся на вершину. Смогут ли друзья тебя обогнать?"),
                 st - 2.0, 3.8, col=(130, 200, 255))

    def _s_outro(self, st, dt, first):
        c = self.sh.display.canvas
        if first:
            self.music.append((self.t, "menu"))
        c.blit(self._grad_bg(), (0, 0))
        cx, cy = W / 2, 230
        self._rays(c, cx, cy, st, alpha=36)
        K.add_glow(c, cx, cy, 520, (220, 150, 60), 0.34)
        self._embers_draw(c, st)
        logo = K.brand_scaled("logo", w=760)
        if logo is not None:
            k = K.ease_out_cubic(min(1.0, st / 0.35))
            s = 0.85 + 0.15 * k + 0.012 * math.sin(st * 3)
            img = pygame.transform.smoothscale(logo, (int(logo.get_width() * s), int(logo.get_height() * s)))
            c.blit(img, (cx - img.get_width() / 2, cy - img.get_height() / 2))
        if st > 0.5:
            q = 0.5 + 0.5 * math.sin(st * 5)
            e = K.ease_out_cubic(min(1.0, (st - 0.5) / 0.35))
            b = pygame.Rect(0, 0, int(470 * (0.6 + 0.4 * e)), int(92 * (0.6 + 0.4 * e)))
            b.center = (int(cx), 470)
            K.add_glow(c, b.centerx, b.centery, 280, K.GREEN, 0.18 + 0.14 * q)
            c.blit(K._button_body(b.w, b.h, (60, 150, 92), q, 22), b.topleft)
            pygame.draw.rect(c, (190, 255, 210), b, width=3, border_radius=22)
            K.draw_text(c, _tc("ŞİMDİ OYNA!", "PLAY NOW!", "¡JUEGA YA!", "JETZT SPIELEN!", "ИГРАЙ СЕЙЧАС!"),
                        b.center, int((38 + 3 * q) * (0.6 + 0.4 * e)), K.WHITE, bold=True, center=True)
            if self.hit(st, 0.5):
                K.sfx("buy", 1.0, 0.0)
            # tıklayan imleç
            m = self.path([(0.5, (900, 640)), (1.6, (b.centerx + 40, b.centery + 14)), (9.0, (b.centerx + 40, b.centery + 14))], st)
            if self.at(st, 1.8):
                self.click(m)
            self.cursor(m)
        if st > 1.0:
            a = int(255 * min(1.0, (st - 1.0) / 0.4))
            K.draw_text(c, _tc("Sen kaçıncı dalgaya dayanırsın?", "How many waves can YOU survive?",
                               "¿Cuántas oleadas aguantarás TÚ?", "Wie viele Wellen überlebst DU?",
                               "Сколько волн продержишься ТЫ?"),
                        (cx, 570), 30, (255, 236, 182), bold=True, center=True, alpha=a)
        if st > 1.6:
            a = int(255 * min(1.0, (st - 1.6) / 0.4))
            K.draw_text(c, _tc("20 silah · 30 kitap · 4 dünya · 40 dalgalık cehennem · dünya sıralaması",
                               "20 weapons · 30 books · 4 worlds · a 40-wave hell · world ranking",
                               "20 armas · 30 libros · 4 mundos · infierno de 40 oleadas · ranking mundial",
                               "20 Waffen · 30 Bücher · 4 Welten · 40-Wellen-Hölle · Weltrangliste",
                               "20 оружий · 30 книг · 4 мира · ад на 40 волн · мировой рейтинг"),
                        (cx, 616), 20, (214, 206, 230), bold=True, center=True, alpha=a)
        if self.hit(st, 0.15):
            K.sfx("bonk", 1.0, 0.0)


# =====================================================================
# MÜZİK — sahnelere oturan 128 BPM reklam müziği
# =====================================================================
SCENE_LEVEL = {
    "cold": 3, "title": 1, "basics": 2, "levelup": 1, "arsenal": 3, "books": 1, "worlds": 1,
    "frost": 2, "jungle": 2, "desert": 2, "boss": 3, "rage": 3, "gate": 1, "hell": 3,
    "dragon": 3, "power": 3, "worldlb": 1, "outro": 0,
}
RISERS = ("arsenal", "boss", "hell", "power")      # öncesinde yükselen ses
DROPS = ("title", "hell", "outro")                  # kesmeden hemen önce kısa sessizlik


def compose(total, scenes, cut_times, hits):
    """make_trailer.compose'un reklam sürümü: aynı enstrümanlar, bu filmin
    sahne yoğunlukları, yükselişleri ve vuruş öncesi sessizlikleri."""
    starts = {}
    acc = 0.0
    for nm, d, _c in scenes:
        starts[nm] = (acc, acc + d)
        acc += d
    return _compose_with_starts(total, cut_times, hits, starts)


def _compose_with_starts(total, cut_times, hits, starts):
    SR, BEAT = MT.SR, MT.BEAT
    out = np.zeros(int(total * SR) + SR * 3)
    side = np.ones_like(out)

    def add(x, at, g=1.0, duck=False):
        i = int(at * SR)
        if i >= len(out) or i < 0:
            return
        j = min(len(out), i + len(x))
        if duck:
            out[i:j] += x[:j - i] * g * side[i:j]
        else:
            out[i:j] += x[:j - i] * g

    sec = [(a, b, SCENE_LEVEL.get(nm, 2)) for nm, (a, b) in starts.items()]

    def level_at(t):
        for a, b, lv in sec:
            if a <= t < b:
                return lv
        return 0

    K_, S_, CL, HC, HO = MT.kick(), MT.snare(), MT.clap(), MT.hat(), MT.hat(True)
    nbeats = int(total / BEAT) + 2
    for bi in range(nbeats):
        t = bi * BEAT
        lv = level_at(t)
        if lv >= 2 or (lv == 1 and bi % 2 == 0):
            i = int(t * SR)
            dn = int(0.22 * SR)
            if i < len(side):
                j = min(len(side), i + dn)
                side[i:j] = np.minimum(side[i:j], 0.35 + 0.65 * np.linspace(0, 1, j - i) ** 0.7)
            add(K_, t, 0.95)
    PROG = MT.PROG
    for bi in range(nbeats):
        t = bi * BEAT
        lv = level_at(t)
        bar, beat_in_bar = divmod(bi, 4)
        root, chord = PROG[bar % 4]
        if lv >= 2 and beat_in_bar in (1, 3):
            add(S_, t, 0.9)
            add(CL, t + 0.004, 0.8)
        if lv == 1 and beat_in_bar == 2:
            add(CL, t, 0.7)
        if lv >= 2:
            for h in range(4 if lv == 3 else 2):
                add(HC, t + h * BEAT / (4 if lv == 3 else 2), 1.0 if h % 2 else 0.6)
            if beat_in_bar % 2 == 1:
                add(HO, t + BEAT / 2, 0.7)
        if lv >= 2:
            for e in range(2):
                f = MT.midi(MT.bass_note(root) + (12 if (e == 1 and beat_in_bar % 2) else 0))
                x = MT._bl_saw(f, BEAT / 2 * 0.92, cutoff=900 if lv == 2 else 1500, detune=(0.0, 7.0))
                x *= MT._env(len(x), 0.004, 0.06)
                add(x, t + e * BEAT / 2, 0.55, duck=True)
        elif lv == 1 and beat_in_bar == 0:
            f = MT.midi(MT.bass_note(root))
            x = MT._bl_saw(f, BEAT * 4 * 0.95, cutoff=500) * MT._env(int(BEAT * 4 * 0.95 * SR), 0.05, 0.6)
            add(x, t, 0.45)
        if beat_in_bar == 0 and lv >= 1:
            for nn in chord:
                x = MT._bl_saw(MT.midi(nn), BEAT * 4 * 0.98, cutoff=2600 if lv >= 2 else 1600,
                               detune=(-11.0, 0.0, 9.0))
                x *= MT._env(len(x), 0.04 if lv >= 2 else 0.4, 0.5)
                add(x, t, 0.10 if lv >= 2 else 0.12, duck=lv >= 2)
        if lv >= 1:
            steps = 4 if lv >= 2 else 2
            for s_ in range(steps):
                ai = (bi * steps + s_)
                nn = chord[ai % 3] + 12 + (12 if (ai // 3) % 4 == 3 else 0)
                d = BEAT / steps * 0.8
                n = int(d * SR)
                tt = MT._t(n)
                x = (np.sign(np.sin(2 * np.pi * MT.midi(nn) * tt)) * 0.5
                     + np.sin(2 * np.pi * MT.midi(nn) * 2 * tt) * 0.3) * np.exp(-tt * 18)
                add(x, t + s_ * BEAT / steps, 0.07 if lv >= 2 else 0.06)
        if lv == 3 and beat_in_bar == 0:
            mel = [chord[2] + 12, chord[1] + 12, chord[2] + 12, chord[0] + 24]
            for q, nn in enumerate(mel):
                x = MT._bl_saw(MT.midi(nn), BEAT * 0.95, cutoff=3200, detune=(-6.0, 6.0))
                vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * MT._t(len(x)))
                x = x * vib * MT._env(len(x), 0.01, 0.12)
                add(x, t + q * BEAT, 0.075, duck=True)

    # kısa sessizlikler (vuruştan önce nefes): müzik o anda çekilir
    for nm in DROPS:
        if nm in starts:
            at = starts[nm][0]
            i0, i1 = int((at - 0.30) * SR), int(at * SR)
            if 0 <= i0 < i1 <= len(out):
                out[i0:i1] *= np.linspace(1.0, 0.05, i1 - i0)
    for ct, kind in cut_times:
        if ct > 0.1:
            if kind == "flash":
                add(MT.impact(), ct, 0.55)
            else:
                add(MT.whoosh() * 1.4, ct - 0.12, 0.9)
    for ht in hits:
        add(MT.impact(), ht, 0.45)
        add(CL, ht, 0.8)
    for nm in RISERS:
        if nm in starts and starts[nm][0] > 2.4:
            add(MT.riser(2.4), starts[nm][0] - 2.4, 0.5)
    if "outro" in starts:
        o0 = starts["outro"][0]
        for nn in (45, 57, 60, 64, 69):
            x = MT._bl_saw(MT.midi(nn), 5.5, cutoff=2400, detune=(-9.0, 0.0, 8.0)) * \
                MT._env(int(5.5 * SR), 0.01, 1.6, hold=0.2)
            add(x, o0, 0.10)
    return out


# =====================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "trailer", "arena_bonk_reklam.mp4"))
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--lang", default="tr")
    ap.add_argument("--seconds", type=float, default=0.0, help="deneme için kısa çıktı")
    ap.add_argument("--start", type=float, default=0.0, help="deneme: bu saniyeden itibaren kaydet")
    ap.add_argument("--max-mb", type=float, default=0.0, help="çıktı boyu sınırı (0 = kalite modu)")
    ap.add_argument("--frames", default="", help="bu saniyelerin karelerini PNG kaydet (virgülle)")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    random.seed(2038)
    np.random.seed(2038)

    K.ONLINE_API_URL = ""
    K.PURCHASE_API_URL = ""
    K.NEW_YEAR_THEME = False        # reklam mevsimsiz: menüde yılbaşı süsü olmasın
    app = K.App()
    app.splash_t = 99.0
    K.CFG["lang"] = a.lang
    rec = MT.SfxRecorder()
    K.audio = rec
    film = PromoFilm(app)
    rec.clock = lambda: film.t
    end = film.LENGTH if not a.seconds else min(film.LENGTH, a.start + a.seconds)
    start = max(0.0, min(a.start, end))
    total = end - start
    ow, oh = (int(v) for v in a.size.lower().split("x"))
    dt = 1.0 / a.fps
    snaps = sorted(float(x) for x in a.frames.split(",") if x.strip())

    # --start: o ana kadar sessizce sar (sahneler gerçek akışla kurulsun)
    t0 = time.time()
    while film.t + 1e-9 < start:
        film.update(dt)
        film.render()

    tmp_video = a.out + ".video.mp4"
    tmp_wav = a.out + ".wav"
    vf = f"scale={ow}:{oh}:flags=lanczos"
    nframes = int(round(total * a.fps))
    # Kare dizisi önce kayıpsıza yakın bir ara dosyaya, sonra (boy sınırı
    # varsa) iki geçişli hedef bit hızıyla son dosyaya kodlanır.
    raw_cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{W}x{H}", "-r", str(a.fps), "-i", "-", "-vf", vf,
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p", tmp_video]
    ff = subprocess.Popen(raw_cmd, stdin=subprocess.PIPE)
    for f in range(nframes):
        film.update(dt)
        frame = film.render()
        ff.stdin.write(pygame.image.tobytes(frame, "RGB"))
        while snaps and film.t >= snaps[0] - 1e-6:
            pygame.image.save(frame, "%s.%05.1f.png" % (a.out, snaps.pop(0)))
        if f % (a.fps * 5) == 0:
            sc = film._scene()
            print(f"  {film.t:6.1f} / {end:.1f} sn   sahne: {sc[1]:10s}   ({time.time() - t0:.0f} sn)",
                  flush=True)
    ff.stdin.close()
    ff.wait()

    print("ses hazırlanıyor...", flush=True)
    cuts = [c for c in film.cut_times if c[0] < end]
    hits = [h for h in film.hits if h < end]
    music = compose(end, film.SCENES, cuts, hits)
    fx = MT.mix_sfx(rec.events, end)
    n0, n1 = int(start * MT.SR), int(end * MT.SR)
    mixd = music[n0:n1] * 0.66 + fx[n0:n1] * 0.30
    peak = np.max(np.abs(mixd)) or 1.0
    mixd = np.tanh(mixd / peak * 1.25) / np.tanh(1.25) * 0.92
    fade = min(len(mixd), int(1.0 * MT.SR))
    if fade:
        mixd[-fade:] *= np.linspace(1, 0, fade)
    MT.write_wav(tmp_wav, mixd)

    abr = 160
    if a.max_mb > 0:
        budget_kbit = a.max_mb * 8 * 1024 * 0.97          # kapsayıcı payı
        vbr = max(400, int(budget_kbit / total - abr))
        passlog = a.out + ".pass"
        common = ["-c:v", "libx264", "-preset", "slow", "-b:v", f"{vbr}k", "-maxrate", f"{int(vbr * 1.6)}k",
                  "-bufsize", f"{int(vbr * 2)}k", "-pix_fmt", "yuv420p", "-passlogfile", passlog]
        subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp_video] + common +
                              ["-pass", "1", "-an", "-f", "mp4", os.devnull])
        subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp_video, "-i", tmp_wav] + common +
                              ["-pass", "2", "-c:a", "aac", "-b:a", f"{abr}k", "-shortest",
                               "-movflags", "+faststart", a.out])
        for ext in ("-0.log", "-0.log.mbtree"):
            if os.path.exists(passlog + ext):
                os.remove(passlog + ext)
    else:
        subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp_video, "-i", tmp_wav,
                               "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                               "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out])
    os.remove(tmp_video)
    os.remove(tmp_wav)
    mb = os.path.getsize(a.out) / (1024 * 1024)
    print(f"hazır: {a.out}  ({total:.1f} sn, {mb:.1f} MB, {time.time() - t0:.0f} sn sürdü)")


if __name__ == "__main__":
    main()
