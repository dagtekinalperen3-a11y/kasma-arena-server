"""ARENA BONK — 2 dakikalık TANITIM FİLMİ (MP4) üretir (v3.28).

Her kare oyunun GERÇEK motorudur: GameTour'un "gölge oyunu" (App(shadow_of=...))
kaydın KOPYASIYLA çalışır, savaşları insan gibi nişan alan otomatik pilot
oynar (bkz. _TourPilot), menülerde sanal imleç gezer. Gerçek kayda, hesaba ve
sunucuya hiçbir şey yazılmaz.

Ses: oyunun kendi efektleri (SFX_BUILDERS; film sırasında çalınan her efekt
zamanıyla kaydedilir) + bu araçta sentezlenen, sahne kesmelerine oturan
128 BPM bir fragman müziği.

Kullanım:
    python tools/make_trailer.py                  # trailer/arena_bonk_tanitim.mp4
    python tools/make_trailer.py --fps 30 --size 1280x720 --out film.mp4
Gerekenler: pygame(-ce), numpy, ffmpeg (PATH'te).
"""
import os
import sys
import math
import time
import wave
import random
import argparse
import subprocess

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import numpy as np          # noqa: E402
import pygame               # noqa: E402
import kasma_arena13 as K   # noqa: E402

_tc = K._tc
W, H = K.VIRTUAL_W, K.VIRTUAL_H


# =====================================================================
# SES KAYDEDİCİ — oyunun sfx() çağrılarını zamanıyla yakalar
# =====================================================================
class SfxRecorder:
    ok = True

    def __init__(self):
        self.events = []
        self.clock = lambda: 0.0
        self._last = {}

    def play(self, name, vol=1.0, gap=0.03):
        t = self.clock()
        if t - self._last.get(name, -9.0) < max(gap, 0.05):
            return
        self._last[name] = t
        self.events.append((t, name, float(vol)))

    def update(self):
        pass

    def set_music(self, *_a, **_k):
        pass


# =====================================================================
# FRAGMAN
# =====================================================================
class GameTrailer(K.GameTour):
    # (sahne, süre, geçiş) — geçiş: "wipe" altın perde, "flash" beyaz çakma, "" yok
    SCENES = (
        ("coldopen", 6.0, ""), ("title", 4.0, "flash"),
        ("wave1", 5.0, "flash"), ("wave5", 4.5, "wipe"),
        ("ars0", 3.5, "flash"), ("ars1", 3.5, "flash"), ("ars2", 3.5, "flash"), ("ars3", 3.5, "flash"),
        ("rarelvl", 4.0, "flash"), ("market", 3.5, ""),
        ("bossa", 5.0, "wipe"), ("bossb", 4.0, "flash"), ("bossc", 4.0, "flash"),
        ("magnet", 4.5, "wipe"), ("portal", 3.0, "wipe"), ("hell1", 3.5, ""),
        ("hellboss", 4.0, "flash"), ("dragon2", 4.5, "flash"),
        ("codex", 5.0, "wipe"), ("books", 4.5, "wipe"), ("skins", 5.5, "wipe"),
        ("petlab", 9.5, "wipe"), ("pets", 3.0, "wipe"), ("worldlb", 5.0, "wipe"),
        ("finale", 8.0, "flash"), ("outro", 6.5, "flash"),
    )
    LENGTH = sum(d for _n, d, _w in SCENES)
    PLAY_SCENES = {"coldopen", "wave1", "wave5", "ars0", "ars1", "ars2", "ars3", "bossa", "bossb",
                   "bossc", "magnet", "portal", "hell1", "hellboss", "dragon2", "finale"}

    ARSENAL = (
        ({"axe": 7, "whip": 6}, 9, 30, ("BALTA + KIRBAÇ", "AXE + WHIP"),
         ("Bumerang baltalar döner, kırbaç önündekini savurur.",
          "Boomerang axes fly back, the whip sweeps the way."), (238, 150, 100)),
        ({"pentagram": 7, "zemzem": 6}, 11, 36, ("PENTAGRAM + ZEMZEM", "PENTAGRAM + HOLY WATER"),
         ("Mühre giren kavrulur, kutsal su yerde eritir.",
          "Step in the sigil and burn; holy water melts the rest."), (200, 110, 255)),
        ({"tornado": 6, "frost": 6, "shoe": 6}, 13, 40, ("HORTUM + BUZ İZİ + PAPUÇ", "TORNADO + FROST + FIRE SHOES"),
         ("Hortum yutar, buz yavaşlatır, ateş izi yakar.",
          "The tornado swallows, frost slows, fire trails burn."), (120, 200, 255)),
        ({"emanet": 7, "book": 6, "cloak": 5, "axe": 6}, 15, 46, ("EMANET + KALKAN + PELERİN", "BLADE + SHIELDS + CLOAK"),
         ("Kılıç zırh deler, kalkanlar mermi savuşturur.",
          "The blade cuts armor, shields deflect bullets."), (255, 214, 120)),
    )

    def __init__(self, real_app):
        super().__init__(real_app)
        sh = self.sh
        # vitrin: mağaza açık, hesap girişli görünsün (yalnızca filmde)
        sh.account.sign_in(self.NAME, "kanka@mail.com")
        sh.purchase.enabled = True
        sh.purchase.api_url = "trailer"
        sh.purchase._catalog_at = time.time() + 10 ** 6
        sh.purchase.catalog = {str(K.CUSTOM_PET_PRODUCT_ID): {"price": 15900}}
        self.cut_times = []          # müzik için: sahne kesmeleri
        self.hits = []               # müzik için: vurgu anları (damga/BONK)
        self.flash_k = 0.0
        acc = 0.0
        for nm, dur, cut in self.SCENES:
            if cut:
                self.cut_times.append((acc, cut))
            acc += dur

    # ------------------------------------------------------------------
    def hit(self, st, x):
        """Tek seferlik vurgu: müziğe 'çarpma' olarak da yazılır."""
        if self.at(st, x):
            self.hits.append(self.t)
            return True
        return False

    def update(self, dt):
        dt = min(dt, 1 / 20.0)
        self.t = min(self.LENGTH, self.t + dt)
        self.sh.t += dt
        i, name, st, dur, cut = self._scene()
        first = i != self.scene_i
        if first:
            self.scene_i = i
            self.prev = -1.0
        run = self.sh.run
        if run is not None and not getattr(run.player, "_trailer_god", False):
            # Filmde kahraman hasar almaz: ekranda "ölen oyuncu" görünmesin.
            run.player._trailer_god = True
            run.player.take_damage = lambda *a, **k: 0
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
        if cut == "wipe" and st < 0.32 and self.t > 0.5:
            k = st / 0.32
            x0 = -260 + (W + 520) * k
            pygame.draw.polygon(c, (236, 186, 92), [(x0, 0), (x0 + 300, 0), (x0 + 80, H), (x0 - 220, H)])
            pygame.draw.polygon(c, (255, 242, 205), [(x0 + 230, 0), (x0 + 300, 0), (x0 + 80, H), (x0 + 10, H)])
        elif cut == "flash" and st < 0.22:
            fl = pygame.Surface((W, H))
            fl.fill((255, 250, 235))
            fl.set_alpha(int(235 * (1.0 - st / 0.22) ** 1.6))
            c.blit(fl, (0, 0))
        self.prev = st

    # ------------------------------------------------------------------
    def _fresh_run(self, wave, weapons, level, crowd, books=None):
        sh = self.sh
        sh.start_run()
        run = sh.run
        p = run.player
        p.no_stats = True
        p.weapons = dict(weapons)
        for k in p.weapons:
            p.weapon_timers[k] = 0.0
        for bk, lv in (books or {}).items():
            for _ in range(lv):
                p.take_book(bk)
        p.level = level
        if wave > 1:
            run.waves._begin_wave(wave, run.score)
            run.waves.announce_timer = 0.0
        self.pilot = K._TourPilot(run, crowd=crowd)
        return run

    def _spawn_ring(self, run, n, rmin=150, rmax=380):
        """Yaratıkları oyuncunun ÇEVRESİNE (ekranın içine) dizer: aksiyon anında başlasın."""
        p = run.player
        w = run.waves.wave
        for _ in range(n):
            a = random.uniform(0, math.tau)
            d = random.uniform(rmin, rmax)
            x = K.clamp(p.x + math.cos(a) * d, K.ARENA_RECT.left + 40, K.ARENA_RECT.right - 40)
            y = K.clamp(p.y + math.sin(a) * d * 0.75, K.ARENA_RECT.top + 40, K.ARENA_RECT.bottom - 40)
            if run.biome == "hell":
                run.enemies.append(K.Enemy(None, x, y, run.wave_hp_mult(w), 1.0, wave=w,
                                           variant=K.hell_pick_kind(w), biome="hell"))
            else:
                kind = random.choice(("red", "red", "blue", "yellow", "tank", "sprinter", "brute"))
                run.enemies.append(K.Enemy(kind, x, y, run.wave_hp_mult(w), 1.0, wave=w))

    def pstamp(self, text, st, col, y=330, life=1.45):
        """Kısa ömürlü büyük damga (art arda gelenler üst üste binmesin)."""
        K.draw_stamp(self.sh.display.canvas, text, st, col, y, life=life)

    def _big_bonk(self, run):
        p = run.player
        p.bonk_cd = 0.0
        try:
            run.do_bonk()
        except Exception:
            pass
        run.fx.shake(12, 0.35)

    # ================== SAHNELER ==================
    def _s_coldopen(self, st, dt, first):
        if first:
            run = self._fresh_run(12, {"axe": 6, "pentagram": 6, "whip": 5, "tornado": 4}, 28, 48,
                                  books={"r_dmg": 4, "r_aspd": 3})
            self.music.append((self.t, "battle"))
            self._spawn_ring(run, 44)
        run = self.sh.run
        for x in (1.85, 3.45):
            if self.hit(st, x):
                self._big_bonk(run)
        self.hit(st, 0.25)
        self._play(dt)
        self.pstamp(_tc("HAYATTA KAL.", "SURVIVE."), st - 0.25, K.WHITE)
        self.pstamp(_tc("VUR.", "SHOOT."), st - 1.85, (255, 214, 120))
        self.pstamp(_tc("BONK'LA!", "BONK!"), st - 3.45, (255, 120, 90), life=2.2)

    def _s_title(self, st, dt, first):
        c = self.sh.display.canvas
        c.blit(self._grad_bg(), (0, 0))
        cx, cy = W / 2, H / 2 - 40
        self._rays(c, cx, cy, st * 2.0, alpha=40)
        K.add_glow(c, cx, cy, 520, (210, 150, 60), 0.34)
        logo = K.brand_scaled("logo", w=900)
        if logo is not None:
            k = K.ease_out_cubic(min(1.0, st / 0.28))
            s_ = 1.7 - 0.7 * k
            img = pygame.transform.smoothscale(logo, (int(logo.get_width() * s_), int(logo.get_height() * s_)))
            jx = math.sin(st * 70) * 6 * max(0.0, 0.4 - st) / 0.4
            c.blit(img, (cx - img.get_width() / 2 + jx, cy - img.get_height() / 2))
        if st < 0.9:
            q = st / 0.9
            K.ring_aa(c, cx, cy, 140 + 640 * q, (255, 230, 170), max(1, int(14 * (1 - q))))
        if self.at(st, 0.02):
            K.sfx("bonk", 1.0, 0.0)
        if st > 0.9:
            a = int(255 * min(1.0, (st - 0.9) / 0.4))
            K.draw_text(c, _tc("Dalga dalga gelen yaratıklara karşı TEK BAŞINA.",
                               "Alone against endless waves of monsters."),
                        (cx, cy + 205), 30, (255, 236, 182), bold=True, center=True, alpha=a)
        if st > 2.0:
            a = int(255 * min(1.0, (st - 2.0) / 0.4))
            n_w, n_b, n_s = len(K.BOSS_WEAPONS), len(K.BOOKS), len(K.SKINS)
            K.draw_text(c, _tc(f"{n_w} SİLAH  ·  {n_b} KİTAP  ·  PATRONLAR  ·  CEHENNEM  ·  {n_s} SKİN",
                               f"{n_w} WEAPONS  ·  {n_b} BOOKS  ·  BOSSES  ·  HELL  ·  {n_s} SKINS"),
                        (cx, cy + 250), 22, (200, 190, 230), bold=True, center=True, alpha=a)

    def _arsenal(self, idx, st, dt, first):
        ws, wave, crowd, title, sub, col = self.ARSENAL[idx]
        run = self.sh.run
        if first:
            p = run.player
            p.weapons = dict(ws)
            for k in p.weapons:
                p.weapon_timers[k] = 0.0
            p.level = max(p.level, 14 + idx * 6)
            run.waves.wave = wave
            run.waves.announce_timer = 0.0
            run.enemies[:] = [e for e in run.enemies if e.alive][:crowd // 3]
            self.pilot.crowd = crowd
            self.pilot.cx, self.pilot.cy = p.x, p.y
            self._spawn_ring(run, crowd, 170, 420)
        if self.hit(st, 1.6):
            self._big_bonk(run)
        self._play(dt)
        self.cap(_tc(*title), _tc(*sub), st - 0.05, 3.3, col=col)

    def _s_ars0(self, st, dt, first):
        self._arsenal(0, st, dt, first)

    def _s_ars1(self, st, dt, first):
        self._arsenal(1, st, dt, first)

    def _s_ars2(self, st, dt, first):
        self._arsenal(2, st, dt, first)

    def _s_ars3(self, st, dt, first):
        self._arsenal(3, st, dt, first)

    def _s_rarelvl(self, st, dt, first):
        sh = self.sh
        run = sh.run
        if first:
            run.player.level = 19      # elde nadir kart: 20. seviye eşiği
            try:
                run.levelup_choices = [
                    run._weapon_offer(K.WEAPON_BY_KEY["tornado"], run.player.weapons.get("tornado", 0) + 1,
                                      "tornado" not in run.player.weapons),
                    run._book_offer(K.BOOK_BY_KEY["r_multi"], 1, True),
                    run._book_offer(K.BOOK_BY_KEY["r_xp"], run.player.books.get("r_xp", 0) + 1,
                                    "r_xp" not in run.player.books),
                ]
                run.pending_levelups = 1
                sh.state = K.STATE_LEVELUP
                K.sfx("levelup", 1.0, 0.0)
            except Exception:
                sh.state = K.STATE_PLAY
        if sh.state == K.STATE_LEVELUP:
            cards = [r.center for (r, _c, _i) in sh.levelup_ui.cards] or [(640, 360)] * 3
            m = self.path([(0.0, (640, 660)), (0.7, cards[0]), (1.3, cards[2]), (2.0, cards[1]),
                           (4.0, cards[1])], st)
            clicked = self.at(st, 2.5)
            if clicked:
                self.clicks.append((m, self.t))
                self.hits.append(self.t)
            sh.update_levelup(dt, m, clicked)
            self.cursor(m)
        else:
            self._play(dt)
        self.stamp(_tc("NADİR KİTAP!", "RARE BOOK!"), st - 2.55, (255, 214, 120), y=120)
        self.cap(_tc("SEVİYE ATLA, KARTINI SEÇ", "LEVEL UP, PICK YOUR CARD"),
                 _tc("Her 5 seviyede bir NADİR kitap kartı garanti!", "A RARE book card every 5 levels!"),
                 st - 0.2, 3.7, y=612, col=(232, 186, 90))

    def _boss(self, st, dt, first, wave, idx, title, sub, col, kill_at):
        sh = self.sh
        run = sh.run
        if first:
            sh.state = K.STATE_PLAY
            p = run.player
            p.weapons = {"axe": 6, "pentagram": 6, "tornado": 5, "emanet": 6}
            for k in p.weapons:
                p.weapon_timers[k] = 0.0
            p.level = max(p.level, 18 + idx * 6)
            run.chests.clear()
            for b in list(run.bosses):
                b.alive = False
            run.bosses = []
            run.waves.wave = wave
            run.waves.boss_idx = idx
            run.waves.boss_active = False      # önceki patronun bayrağı kalmasın
            run.waves.boss_pending = True
            self.pilot.crowd = 12
            self.pilot.target = None
        if st > kill_at:
            for b in list(run.bosses):
                if b.alive:
                    K.tour_kill_boss(b, run.fx)
                    self.hits.append(self.t)
                    run.fx.shake(14, 0.4)
        self.pilot.target = (run.chests[0].x, run.chests[0].y) if run.chests else None
        self._play(dt)
        self.cap(title, sub, st - 0.4, 3.6, col=col)

    def _s_bossa(self, st, dt, first):
        self._boss(st, dt, first, 10, 0, _tc("PATRON GELİYOR!", "BOSS INCOMING!"),
                   _tc("Her 5 dalgada bir dev: kaç, vur, devir!", "A giant every 5 waves: dodge, hit, win!"),
                   (255, 110, 90), 3.7)

    def _s_bossb(self, st, dt, first):
        self._boss(st, dt, first, 15, 1, _tc("CADI", "THE WITCH"),
                   _tc("Zehir yağdırır, kaybolur, arkandan çıkar.", "Rains poison, vanishes, strikes from behind."),
                   (200, 120, 255), 3.0)

    def _s_bossc(self, st, dt, first):
        self._boss(st, dt, first, 20, 2, _tc("KOLOS", "THE COLOSSUS"),
                   _tc("Yer sarsılır. Sandığı kap, silahın güçlensin!", "The ground shakes. Grab the chest, power up!"),
                   (255, 160, 80), 3.0)

    def _s_wave1(self, st, dt, first):
        super()._s_wave1(st, dt, first)
        if first:
            self.pilot.crowd = 14
            self._spawn_ring(self.sh.run, 8, 220, 420)

    def _s_magnet(self, st, dt, first):
        super()._s_magnet(st, dt, first)
        self.stamp(_tc("HİÇBİR ŞEY KAYBOLMAZ!", "NOTHING EVER DESPAWNS!"), st - 0.9, (130, 210, 255), y=150)

    def _s_dragon2(self, st, dt, first):
        sh = self.sh
        run = sh.run
        p = run.player
        if first:
            run.chests.clear()
            cam = run.cam_rect()
            dg = K.Boss("dragon", cam.centerx + 260, cam.centery - 120, 1.0, 1.0, run.waves.wave,
                        hellish=True)
            run.bosses.append(dg)
            K.scale_bosses_to_player(run.bosses, p)
            run.waves.boss_active = True
            self.pilot.crowd = 14
            K.sfx("boss", 1.0, 0.0)
        if self.hit(st, 3.3):
            for b in list(run.bosses):
                K.tour_kill_boss(b, run.fx)
            run.fx.shake(18, 0.5)
            run.fx.do_flash((255, 160, 80), 0.45)
        self._play(dt)
        self.cap(_tc("EJDERHA UYANDI!", "THE DRAGON AWAKENS!"),
                 _tc("Cehennemin ilk patronu ateş kusar...", "Hell's first boss breathes fire..."),
                 st - 0.2, 3.0, col=(255, 90, 60))
        self.stamp(_tc("EJDERHA DEVRİLDİ!", "DRAGON DOWN!"), st - 3.35, (255, 170, 80), y=150)

    def _s_petlab(self, st, dt, first):
        sh = self.sh
        if first:
            sh.state = K.STATE_MENU
            sh.save.data["pet_draft"] = dict(K.CUSTOM_PET_DEFAULT, name="Bonkçuk")
            sh.open_pet_designer()
            self._pl_rnd = random.Random(31)
            self._pl_steps = []
            # (zaman, sekme, seçenek) — imleç kartlara gidip tıklar
            plan = [(0.9, "body", "chubby"), (1.6, "eyes", "star"), (2.3, "ears", "fox"),
                    (3.0, "wings", "dragon"), (3.7, "tail", "dragon"), (4.4, "hat", "crown"),
                    (5.1, "fx", "flames"), (5.8, "colors", None)]
            self._pl_steps = plan
        pd = sh.pd
        area_x, area_y, area_w = 504, 184, 740
        # sekme düğmesi ve seçenek kartının ekrandaki yeri
        def tab_pos(key):
            keys = [k for k, _p in sh.PD_TABS]
            i = keys.index(key)
            row, ci = (0, i) if i < 6 else (1, i - 6)
            n_row = 6 if row == 0 else len(keys) - 6
            x0 = 492 + 764 / 2 - (n_row * 116 + (n_row - 1) * 8) / 2
            return (x0 + ci * 124 + 58, 88 + 14 + row * 38 + 15)

        def chip_pos(key, opt):
            opts = K.CUSTOM_PET_PARTS[key]
            cols = 4 if len(opts) <= 8 else 5
            cw = (area_w - (cols - 1) * 12) // cols
            i = opts.index(opt)
            return (area_x + (i % cols) * (cw + 12) + cw / 2, area_y + (i // cols) * 222 + 104)

        keys = [(0.0, (640, 690))]
        for (tt, tab, opt) in self._pl_steps:
            keys.append((tt - 0.42, tab_pos(tab)))
            keys.append((tt - 0.12, chip_pos(tab, opt) if opt else (900, 270)))
        keys.append((6.6, (900, 270)))
        keys.append((7.4, (1068, 674)))          # TAMAM — SATIN AL
        keys.append((8.3, (785, 501)))           # onay penceresi: ÖDEMEYE GEÇ
        keys.append((9.5, (785, 501)))
        m = self.path(keys, st)
        for (tt, tab, opt) in self._pl_steps:
            if self.at(st, tt - 0.35):
                pd["tab"] = tab
                self.clicks.append((tab_pos(tab), self.t))
                K.sfx("click", 0.6, 0.0)
            if self.at(st, tt):
                if opt:
                    sh._pd_set(tab, opt)
                    self.clicks.append((m, self.t))
                else:
                    sh._pd_set("col", [150, 110, 240])
                    sh._pd_set("col2", [255, 214, 120])
                self.hits.append(self.t)
        if self.at(st, 6.4):
            sh._pd_set("name", "Bonkçuk")
        if self.at(st, 7.5):
            self.clicks.append((m, self.t))
            pd["confirm"] = True
            self.hits.append(self.t)
        sh.update_pet_designer(dt, m, False)
        self.cursor(m)
        self.stamp(_tc("YENİ!", "NEW!"), st - 0.15, (255, 120, 140), y=110)
        self.cap(_tc("KENDİ PETİNİ YAP", "MAKE YOUR OWN PET"),
                 _tc("Göz, kulak, kuyruk, kanat, şapka, efekt... Dünyada TEK!",
                     "Eyes, ears, tail, wings, hat, effects... One of a kind!"),
                 st - 0.3, 6.8, y=612, col=(255, 170, 200))
        if st > 7.5:
            self.cap(_tc("BEĞENDİN Mİ? TAMAM DE!", "LOVE IT? HIT OK!"),
                     _tc("Önce tasarla, beğenince satın al.", "Design first, buy when you love it."),
                     st - 7.6, 1.9, y=612, col=(140, 230, 170))

    def _s_finale(self, st, dt, first):
        if first:
            self._fresh_run(22, {"axe": 9, "pentagram": 9, "tornado": 8, "zemzem": 8}, 60, 64,
                            books={"r_dmg": 8, "r_aspd": 6, "r_crit": 5})
            self._spawn_ring(self.sh.run, 60, 160, 420)
            self.music.append((self.t, "battle"))
        run = self.sh.run
        n_w, n_b, n_s = len(K.BOSS_WEAPONS), len(K.BOOKS), len(K.SKINS)
        texts = ((0.15, _tc(f"{n_w} SİLAH", f"{n_w} WEAPONS"), (255, 214, 120)),
                 (2.0, _tc(f"{n_b} KİTAP", f"{n_b} BOOKS"), (196, 150, 255)),
                 (3.85, _tc("DEV PATRONLAR", "GIANT BOSSES"), (255, 120, 90)),
                 (5.7, _tc("SONSUZ CEHENNEM", "ENDLESS HELL"), (255, 90, 60)))
        for t0, txt, col in texts:
            if self.hit(st, t0):
                self._big_bonk(run)
                self._spawn_ring(run, 14, 200, 400)
            self.pstamp(txt, st - t0, col, life=1.7)
        self._play(dt)

    def _s_outro(self, st, dt, first):
        if first:
            self.hits.append(self.t)
        super()._s_outro(st, dt, first)
        c = self.sh.display.canvas
        if st > 0.8:
            a = int(255 * min(1.0, (st - 0.8) / 0.5))
            K.draw_text(c, _tc("Rekorunu kır. Dünya sıralamasına adını yazdır.",
                               "Break your record. Put your name on the world ranking."),
                        (W / 2, 640), 20, (200, 190, 230), bold=True, center=True, alpha=a)
        if st > self.SCENES[-1][1] - 1.2:
            fade = pygame.Surface((W, H))
            fade.fill((0, 0, 0))
            fade.set_alpha(int(255 * min(1.0, (st - (self.SCENES[-1][1] - 1.2)) / 1.2)))
            c.blit(fade, (0, 0))


# =====================================================================
# MÜZİK — 128 BPM fragman müziği (numpy sentezi)
# =====================================================================
SR = 44100
BPM = 128.0
BEAT = 60.0 / BPM


def _t(n):
    return np.arange(n) / SR


def _bl_saw(freq, dur, cutoff=2400.0, detune=(0.0,)):
    """Bant sınırlı testere (toplamalı sentez): örtüşme yok, filtre yok."""
    n = int(dur * SR)
    t = _t(n)
    out = np.zeros(n)
    for dt_ in detune:
        f = freq * (2 ** (dt_ / 1200.0))
        kmax = max(1, int(cutoff / f))
        for k in range(1, min(kmax, 60) + 1):
            out += np.sin(2 * np.pi * k * f * t) / k
    return out / (len(detune) * 1.6)


def _env(n, a=0.005, r=0.08, hold=None):
    e = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    if hold is None:
        e[-nr:] *= np.linspace(1, 0, nr)
    else:
        nh = int(hold * SR)
        if nh < n:
            tail = n - nh
            e[nh:] *= np.exp(-np.arange(tail) / (r * SR))
    return e


def kick():
    n = int(0.42 * SR)
    t = _t(n)
    f = 44 + 120 * np.exp(-t * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 7.5)
    x[:int(0.004 * SR)] += np.random.uniform(-0.6, 0.6, int(0.004 * SR))
    return np.tanh(x * 1.6) * 0.95


def snare():
    n = int(0.28 * SR)
    t = _t(n)
    nz = np.random.uniform(-1, 1, n)
    nz = np.diff(np.concatenate([[0], nz]))         # parlak gürültü
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 28)
    return (nz * np.exp(-t * 16) * 0.42 + body * 0.5) * 0.8


def clap():
    n = int(0.22 * SR)
    t = _t(n)
    nz = np.diff(np.concatenate([[0], np.random.uniform(-1, 1, n)]))
    env = np.exp(-t * 22) + 0.6 * np.exp(-np.maximum(0, t - 0.012) * 30) * (t > 0.012)
    return nz * env * 0.35


def hat(open_=False):
    n = int((0.22 if open_ else 0.05) * SR)
    t = _t(n)
    nz = np.random.uniform(-1, 1, n)
    nz = np.diff(np.diff(np.concatenate([[0, 0], nz])))
    return nz * np.exp(-t * (14 if open_ else 70)) * (0.10 if open_ else 0.08)


def impact():
    n = int(2.6 * SR)
    t = _t(n)
    f = 32 + 70 * np.exp(-t * 6)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.8)
    nz = np.random.uniform(-1, 1, n)
    nz = np.diff(np.concatenate([[0], nz])) * np.exp(-t * 2.4) * 0.35
    return np.tanh((boom * 1.4 + nz)) * 0.9


def riser(dur):
    n = int(dur * SR)
    t = _t(n)
    k = t / dur
    nz = np.random.uniform(-1, 1, n)
    nz = np.diff(np.concatenate([[0], nz]))
    tone = np.sin(2 * np.pi * np.cumsum(200 + 1400 * k ** 2) / SR)
    return (nz * 0.35 + tone * 0.25) * k ** 2.2


def whoosh():
    n = int(0.5 * SR)
    t = _t(n)
    nz = np.random.uniform(-1, 1, n)
    env = np.sin(np.pi * t / 0.5) ** 2
    return np.diff(np.concatenate([[0], nz])) * env * 0.22


def midi(nn):
    return 440.0 * 2 ** ((nn - 69) / 12.0)


def bass_note(root):
    """Bas notasını duyulur aralığa (A1-G#2, 55-104 Hz) oturtur: C1 gibi
    33 Hz'lik notalar dizüstü hoparlörde hiç duyulmuyor."""
    n = root - 24
    while n < 33:
        n += 12
    while n > 44:
        n -= 12
    return n


# Am - F - C - G (epik minör)
PROG = [(57, (57, 60, 64)), (53, (53, 57, 60)), (48, (55, 60, 64)), (55, (55, 59, 62))]


def compose(total, scenes, cut_times, hits):
    """Sahne zaman çizelgesine oturan fragman müziği."""
    out = np.zeros(int(total * SR) + SR * 3)
    side = np.ones_like(out)           # kick'e göre 'sidechain' sönümü

    def add(x, at, g=1.0, duck=False):
        i = int(at * SR)
        if i >= len(out) or i < 0:
            return
        j = min(len(out), i + len(x))
        if duck:
            out[i:j] += x[:j - i] * g * side[i:j]
        else:
            out[i:j] += x[:j - i] * g

    # bölümler: (başlangıç, bitiş, yoğunluk) — 0 sessiz, 1 hafif, 2 tam, 3 en yoğun
    starts = {}
    acc = 0.0
    for nm, d, _c in scenes:
        starts[nm] = (acc, acc + d)
        acc += d
    sec = [
        (0.0, starts["coldopen"][1], 3),
        (starts["title"][0], starts["title"][0] + 2.0, 0),
        (starts["title"][0] + 2.0, starts["title"][1], 1),
        (starts["wave1"][0], starts["market"][1], 2),
        (starts["bossa"][0], starts["dragon2"][1], 3),
        (starts["codex"][0], starts["worldlb"][1], 1),
        (starts["finale"][0], starts["finale"][1], 3),
        (starts["outro"][0], total, 0),
    ]

    def level_at(t):
        for a, b, lv in sec:
            if a <= t < b:
                return lv
        return 0

    K_, S_, CL, HC, HO = kick(), snare(), clap(), hat(), hat(True)
    nbeats = int(total / BEAT) + 2
    # önce kick'ler (sidechain zarfı için)
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
        # bas: 8'likler (oktav zıplamalı)
        if lv >= 2:
            for e in range(2):
                f = midi(bass_note(root) + (12 if (e == 1 and beat_in_bar % 2) else 0))
                x = _bl_saw(f, BEAT / 2 * 0.92, cutoff=900 if lv == 2 else 1500, detune=(0.0, 7.0))
                x *= _env(len(x), 0.004, 0.06)
                add(x, t + e * BEAT / 2, 0.55, duck=True)
        elif lv == 1 and beat_in_bar == 0:
            f = midi(bass_note(root))
            x = _bl_saw(f, BEAT * 4 * 0.95, cutoff=500) * _env(int(BEAT * 4 * 0.95 * SR), 0.05, 0.6)
            add(x, t, 0.45)
        # akor yastığı (her ölçü başında)
        if beat_in_bar == 0 and lv >= 1:
            for nn in chord:
                x = _bl_saw(midi(nn), BEAT * 4 * 0.98, cutoff=2600 if lv >= 2 else 1600,
                            detune=(-11.0, 0.0, 9.0))
                x *= _env(len(x), 0.04 if lv >= 2 else 0.4, 0.5)
                add(x, t, 0.10 if lv >= 2 else 0.12, duck=lv >= 2)
        # arpej (16'lık)
        if lv >= 1:
            steps = 4 if lv >= 2 else 2
            for s_ in range(steps):
                ai = (bi * steps + s_)
                nn = chord[ai % 3] + 12 + (12 if (ai // 3) % 4 == 3 else 0)
                d = BEAT / steps * 0.8
                n = int(d * SR)
                tt = _t(n)
                x = (np.sign(np.sin(2 * np.pi * midi(nn) * tt)) * 0.5
                     + np.sin(2 * np.pi * midi(nn) * 2 * tt) * 0.3) * np.exp(-tt * 18)
                add(x, t + s_ * BEAT / steps, 0.07 if lv >= 2 else 0.06)
        # en yoğun bölümlerde lead (uzun notalar)
        if lv == 3 and beat_in_bar == 0:
            mel = [chord[2] + 12, chord[1] + 12, chord[2] + 12, chord[0] + 24]
            for q, nn in enumerate(mel):
                x = _bl_saw(midi(nn), BEAT * 0.95, cutoff=3200, detune=(-6.0, 6.0))
                vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * _t(len(x)))
                x = x * vib * _env(len(x), 0.01, 0.12)
                add(x, t + q * BEAT, 0.075, duck=True)

    # kesmeler ve vurgular
    for ct, kind in cut_times:
        if ct > 0.1:
            add(impact() if kind == "flash" else whoosh() * 1.4, ct - (0.0 if kind == "flash" else 0.12),
                0.55 if kind == "flash" else 0.9)
    for ht in hits:
        add(impact(), ht, 0.45)
        add(CL, ht, 0.8)
    # yükselişler: başlık öncesi ve final öncesi
    for at in (starts["title"][0], starts["finale"][0], starts["bossa"][0]):
        r = riser(2.4)
        add(r, at - 2.4, 0.5)
    # final akoru
    o0 = starts["outro"][0]
    for nn in (45, 57, 60, 64, 69):
        x = _bl_saw(midi(nn), 5.5, cutoff=2400, detune=(-9.0, 0.0, 8.0)) * _env(int(5.5 * SR), 0.01, 1.6, hold=0.2)
        add(x, o0, 0.10)
    return out


def mix_sfx(events, total):
    """Oyunun kendi efektlerini (SFX_BUILDERS) kaydedilen anlara yerleştirir."""
    out = np.zeros(int(total * SR) + SR * 3)
    cache = {}
    window = {}
    for t, name, vol in events:
        if t > total:
            continue
        b = window.setdefault(int(t * 10), [0])
        if b[0] >= 5:              # 0.1 sn'de en çok 5 efekt (kakofoni olmasın)
            continue
        b[0] += 1
        if name not in cache:
            fn = K.SFX_BUILDERS.get(name)
            if fn is None:
                cache[name] = None
            else:
                x = np.array(fn(), dtype=np.float64)
                # oyunun örnekleme hızından 44.1 kHz'e
                src = np.arange(len(x)) / float(K._SR)
                dst = np.arange(int(len(x) * SR / K._SR)) / float(SR)
                cache[name] = np.interp(dst, src, x)
        x = cache[name]
        if x is None:
            continue
        i = int(t * SR)
        j = min(len(out), i + len(x))
        out[i:j] += x[:j - i] * vol
    return out


def write_wav(path, x):
    x = np.clip(x, -1.0, 1.0)
    pcm = (x * 32000).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        st = np.empty(len(pcm) * 2, dtype=np.int16)
        st[0::2] = pcm
        st[1::2] = pcm
        w.writeframes(st.tobytes())


# =====================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "trailer", "arena_bonk_tanitim.mp4"))
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--lang", default="tr")
    ap.add_argument("--seconds", type=float, default=0.0, help="deneme için kısa çıktı")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    random.seed(2028)
    np.random.seed(2028)

    K.ONLINE_API_URL = ""
    K.PURCHASE_API_URL = ""
    app = K.App()
    app.splash_t = 99.0
    K.CFG["lang"] = a.lang
    rec = SfxRecorder()
    K.audio = rec
    trailer = GameTrailer(app)
    rec.clock = lambda: trailer.t
    total = trailer.LENGTH if not a.seconds else min(trailer.LENGTH, a.seconds)
    nframes = int(round(total * a.fps))
    ow, oh = (int(v) for v in a.size.lower().split("x"))

    tmp_video = a.out + ".video.mp4"
    tmp_wav = a.out + ".wav"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(a.fps), "-i", "-",
           "-vf", f"scale={ow}:{oh}:flags=lanczos",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", tmp_video]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    dt = 1.0 / a.fps
    for f in range(nframes):
        trailer.update(dt)
        frame = trailer.render()
        ff.stdin.write(pygame.image.tobytes(frame, "RGB"))
        if f % (a.fps * 5) == 0:
            sc = trailer._scene()
            print(f"  {trailer.t:6.1f} / {total:.1f} sn   sahne: {sc[1]:10s}   "
                  f"({time.time() - t0:.0f} sn)", flush=True)
    ff.stdin.close()
    ff.wait()

    print("ses hazırlanıyor...", flush=True)
    music = compose(total, trailer.SCENES, [c for c in trailer.cut_times if c[0] < total],
                    [h for h in trailer.hits if h < total])
    fx = mix_sfx(rec.events, total)
    n = int(total * SR)
    mixd = music[:n] * 0.66 + fx[:n] * 0.30
    peak = np.max(np.abs(mixd)) or 1.0
    mixd = np.tanh(mixd / peak * 1.25) / np.tanh(1.25) * 0.92
    fade = int(1.0 * SR)
    mixd[-fade:] *= np.linspace(1, 0, fade)
    write_wav(tmp_wav, mixd)

    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp_video, "-i", tmp_wav,
                           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", a.out])
    os.remove(tmp_video)
    os.remove(tmp_wav)
    print(f"hazır: {a.out}  ({total:.1f} sn, {time.time() - t0:.0f} sn sürdü)")


if __name__ == "__main__":
    main()
