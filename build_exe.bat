@echo off
chcp 65001 >nul
REM ============================================================
REM  EvolveArena - TEK EXE (Nuitka)
REM
REM  Neden PyInstaller degil: PyInstaller'in hazir baslaticisi (bootloader)
REM  virus yazanlarin da kullandigi ayni dosya oldugu icin Windows Defender
REM  "Trojan:Win32/Sabsik / Wacatac !ml" diye yanlis alarm veriyor.
REM  Nuitka oyunu gercek C koduna cevirip derler: yanlis alarm cok daha az.
REM
REM  Kullanim: bu dosyayi arenaee.py ile AYNI klasore koy, cift tikla.
REM  Ilk calistirmada Nuitka C derleyicisini (MinGW) kendisi indirir.
REM  Derleme uzun surer (10-30 dk), bilgisayar yavas gibi gorunebilir: normal.
REM  Cikti: EvolveArena.exe (bu klasorde)
REM ============================================================

cd /d "%~dp0"

REM oyun dosyasini bul (arenaee.py yoksa klasordeki ilk arena*.py)
set "GAME=arenaee.py"
if not exist "%GAME%" (
  for %%F in (arena*.py) do (
    set "GAME=%%F"
    goto :found
  )
  echo HATA: Bu klasorde arenaee.py bulunamadi. Dosyayi bu .bat ile ayni klasore koy.
  pause
  exit /b 1
)
:found
echo Oyun dosyasi: %GAME%

python -m pip install --upgrade pip
python -m pip install --upgrade nuitka ordered-set zstandard pygame-ce

python -m nuitka ^
  --onefile ^
  --lto=no ^
  --windows-console-mode=disable ^
  --assume-yes-for-downloads ^
  --include-package-data=pygame ^
  --nofollow-import-to=tkinter,unittest,pydoc_data ^
  --onefile-tempdir-spec="{CACHE_DIR}/EvolveArena/3.49" ^
  --company-name=EvolveArena ^
  --product-name=EvolveArena ^
  --file-description="EvolveArena" ^
  --file-version=3.49.0.0 ^
  --product-version=3.49.0.0 ^
  --copyright="EvolveArena" ^
  --output-filename=EvolveArena.exe ^
  --output-dir=build_exe ^
  --remove-output ^
  "%GAME%"

if errorlevel 1 (
  echo.
  echo Derleme BASARISIZ. Yukaridaki hatayi kontrol et.
  pause
  exit /b 1
)

move /y build_exe\EvolveArena.exe EvolveArena.exe >nul
echo.
echo Hazir: EvolveArena.exe
echo Gondermeden once virustotal.com'a yukleyip kontrol et.
pause
