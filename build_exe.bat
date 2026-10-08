@echo off
REM ============================================================
REM  ARENA BONK - tek dosya .exe uretir (Windows)
REM  Gerekenler:  pip install pygame pyinstaller
REM  Cikti:       dist\ArenaBonk.exe  (ikonu assets\arena_bonk.ico)
REM  Logo/ikon zaten oyunun icine gomulu; yanina dosya koymak gerekmez.
REM ============================================================
pyinstaller --noconfirm --onefile --windowed ^
  --name ArenaBonk ^
  --icon assets\arena_bonk.ico ^
  kasma_arena13.py
echo.
echo Bitti: dist\ArenaBonk.exe
pause
