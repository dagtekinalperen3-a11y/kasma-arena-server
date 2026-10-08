"""
ARENA BONK — OYUN TURU videosu (~90 sn, 1280x720, 30 FPS, sesli).

Oyundaki ödüllü reklamın içeriği olan GameTour filmini (bkz. kasma_arena13.py)
kare kare MP4'e çevirir. Oyun ekransız ve geçici bir kayıtla açılır; sesler
ve müzik oyunun kendi sentezinden gelir (altyapı: tools/make_trailer.py).

Kullanım:
    python tools/make_tour_video.py                    -> arena_bonk_tur.mp4
    python tools/make_tour_video.py --out tur.mp4
    python tools/make_tour_video.py --preview 5,30,60  -> o saniyelerin PNG'leri
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_trailer as mt              # noqa: E402  (oyunu da yükler)

ka, pygame = mt.ka, mt.pygame


class _Timeline:
    def __init__(self, tour):
        self.length = tour.LENGTH
        self.music = list(tour.music)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(mt.ROOT, "arena_bonk_tur.mp4"))
    ap.add_argument("--preview", default="")
    ap.add_argument("--crf", default="21")
    args = ap.parse_args()

    mt.random.seed(2026)
    app = ka.App()
    ka.audio = mt.REC
    tour = ka.GameTour(app)
    n = int(round(tour.LENGTH * mt.FPS))

    if args.preview:
        want = sorted(float(x) for x in args.preview.split(","))
        outdir = os.path.dirname(os.path.abspath(args.out))
        for _i in range(n):
            mt.REC.now = tour.t
            tour.update(mt.DT)
            while want and tour.t >= want[0]:
                p = os.path.join(outdir, "tour_%05.1f.png" % want.pop(0))
                pygame.image.save(tour.render(), p)
            if not want:
                break
        return

    silent = args.out + ".video.mp4"
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", "%dx%d" % (mt.W, mt.H), "-r", str(mt.FPS), "-i", "-",
                             "-c:v", "libx264", "-preset", "slow", "-crf", args.crf,
                             "-pix_fmt", "yuv420p", "-movflags", "+faststart", silent],
                            stdin=subprocess.PIPE)
    for i in range(n):
        mt.REC.now = tour.t
        tour.update(mt.DT)
        frame = tour.render()
        left = tour.LENGTH - tour.t
        if left < 0.5:                      # sonda karar
            f = pygame.Surface((mt.W, mt.H))
            f.set_alpha(int(255 * (0.5 - left) / 0.5))
            frame.blit(f, (0, 0))
        proc.stdin.write(mt.to_bytes(frame))
        if i % 300 == 0:
            print("%d / %d kare" % (i, n), flush=True)
    proc.stdin.close()
    proc.wait()

    wav = args.out + ".wav"
    mt.build_audio(_Timeline(tour), wav)
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
                           "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                           "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                           "-shortest", "-movflags", "+faststart", args.out])
    os.remove(silent)
    os.remove(wav)
    print("Bitti:", args.out, "(%d kare, %.1f sn)" % (n, n / mt.FPS))


if __name__ == "__main__":
    main()
