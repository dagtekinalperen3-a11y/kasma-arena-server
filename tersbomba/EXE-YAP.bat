@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Ters Bomba - EXE yapiliyor
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js gerekli. https://nodejs.org adresinden LTS surumunu kur, sonra bu dosyayi tekrar calistir.
  pause
  exit /b 1
)
echo Paketler indiriliyor...
call npm install
echo EXE yapiliyor...
call npm run exe:win
echo.
echo HAZIR! exe klasorunde: Ters-Bomba.exe
start "" "%~dp0exe"
pause
