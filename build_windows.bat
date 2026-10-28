@echo off
chcp 65001 >nul
REM ============================================================
REM  EvolveArena - Windows paketleme
REM  Antivirus (Windows Defender) yanlis alarmini en aza indirmek icin:
REM    * tek dosya (--onefile) DEGIL, klasor (--onedir) paketlenir
REM    * UPX sikistirmasi KAPALI (--noupx)
REM    * exe'ye surum / yayinci bilgisi eklenir (version_info.txt)
REM  Cikti: dist\EvolveArena\EvolveArena.exe  (klasoru zipleyip paylas)
REM ============================================================

cd /d "%~dp0"

python -m pip install --upgrade pip
python -m pip install --upgrade pygame-ce pyinstaller

REM eski derleme artiklarini temizle
if exist build rmdir /s /q build
if exist dist\EvolveArena rmdir /s /q dist\EvolveArena

python -m PyInstaller --noconfirm --clean --onedir --windowed --noupx ^
  --name EvolveArena ^
  --version-file version_info.txt ^
  arenaee.py

if errorlevel 1 (
  echo.
  echo Paketleme BASARISIZ. Yukaridaki hatayi kontrol et.
  pause
  exit /b 1
)

REM paylasim icin zip
powershell -NoProfile -Command "Compress-Archive -Path 'dist\EvolveArena\*' -DestinationPath 'dist\EvolveArena.zip' -Force"

echo.
echo Hazir: dist\EvolveArena.zip
echo Arkadaslarin zipi acip EvolveArena.exe'yi calistirsin.
echo Gondermeden once dist\EvolveArena.zip'i virustotal.com'a yukleyip kontrol et.
pause
