"""
ARENA BONK — "REKLAM İZLE" filminin video hâli (30 sn, 1280x720, 30 FPS, sesli).

Oyundaki ödüllü reklam penceresinde oynayan tanıtım filmini (HouseAd)
kare kare MP4'e çevirir. Altyapı tools/make_trailer.py ile ortak: oyun
ekransız ve geçici bir kayıtla açılır, sesler oyunun kendi sentezinden gelir.

Kullanım:
    python tools/make_ad_video.py                 -> arena_bonk_reklam.mp4
    python tools/make_ad_video.py --out reklam.mp4
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_trailer as mt              # noqa: E402  (oyunu da yükler)

ka, pygame = mt.ka, mt.pygame


class _Timeline:
    """build_audio'nun beklediği iki alan: müzik değişimleri ve süre."""

    def __init__(self, length):
        self.length = length
        # Giriş ve kapanışta menü müziği, savaş sahnelerinde savaş müziği.
        self.music = [(0.0, "menu"), (3.5, "battle"), (17.5, "menu")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(mt.ROOT, "arena_bonk_reklam.mp4"))
    ap.add_argument("--crf", default="19")
    args = ap.parse_args()

    mt.random.seed(2026)
    app = ka.App()
    ka.audio = mt.REC
    sv = app.save
    sv.unlock_everything()
    sv.data["tainted"] = False
    sv.data["equipped_skin"] = "prism"
    ad = ka.HouseAd(sv)
    length = ad.LENGTH

    silent = args.out + ".video.mp4"
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", "%dx%d" % (mt.W, mt.H), "-r", str(mt.FPS), "-i", "-",
                             "-c:v", "libx264", "-preset", "slow", "-crf", args.crf,
                             "-pix_fmt", "yuv420p", "-movflags", "+faststart", silent],
                            stdin=subprocess.PIPE)
    n = int(round(length * mt.FPS))
    for i in range(n):
        mt.REC.now = i * mt.DT
        app.t += mt.DT
        ad.update(mt.DT)
        frame = ad.render()
        # son yarım saniyede karar
        if mt.REC.now > length - 0.5:
            f = pygame.Surface((mt.W, mt.H))
            f.set_alpha(int(255 * (mt.REC.now - (length - 0.5)) / 0.5))
            frame.blit(f, (0, 0))
        proc.stdin.write(mt.to_bytes(frame))
    proc.stdin.close()
    proc.wait()

    wav = args.out + ".wav"
    mt.build_audio(_Timeline(length), wav)
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav,
                           "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                           "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                           "-shortest", "-movflags", "+faststart", args.out])
    os.remove(silent)
    os.remove(wav)
    print("Bitti:", args.out, "(%d kare, %.1f sn)" % (n, n / mt.FPS))


if __name__ == "__main__":
    main()
