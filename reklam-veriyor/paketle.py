"""public_html'e yüklenecek zip paketini üretir.

    python3 reklam-veriyor/paketle.py [hedef.zip]

Zip'in içeriği doğrudan public_html'e çıkarılır. Testler, bu betik ve
çalışma sırasında oluşan veri dosyaları pakete girmez.
"""
import os
import sys
import zipfile

KOK = os.path.dirname(os.path.abspath(__file__))
HEDEF = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(KOK), "reklam-veriyor-public_html.zip")

DAHIL = ["index.php", "ayarlar.php", ".htaccess", "KURULUM.txt", "lib", "static", "veri/.htaccess", "veri/index.html"]


def dosyalar():
    for yol in DAHIL:
        tam = os.path.join(KOK, yol)
        if os.path.isfile(tam):
            yield yol
            continue
        for kok, dizinler, adlar in os.walk(tam):
            dizinler[:] = sorted(d for d in dizinler if d != "__pycache__")
            for ad in sorted(adlar):
                yield os.path.relpath(os.path.join(kok, ad), KOK)


def main():
    if os.path.exists(HEDEF):
        os.remove(HEDEF)
    n = 0
    with zipfile.ZipFile(HEDEF, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for yol in dosyalar():
            z.write(os.path.join(KOK, yol), yol.replace(os.sep, "/"))
            n += 1
    print("%s  (%d dosya, %.0f KB)" % (HEDEF, n, os.path.getsize(HEDEF) / 1024))


if __name__ == "__main__":
    main()
