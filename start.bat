@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title Klad Macro Tool - Launcher

echo.
echo  ╔═══════════════════════════════════════╗
echo  ║      KLAD MACRO TOOL LAUNCHER         ║
echo  ╚═══════════════════════════════════════╝
echo.

REM ══════════════════════════════════════════
echo  [ADIM 1/3] Python Kontrolu
echo  ─────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo    [X] Python bulunamadi!
    echo.
    echo    [i] Python yukleniyor...
    echo        Kaynak: winget / Python 3.12
    echo.
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo.
        echo    [!] Kurulum basarisiz!
        echo        Manuel yukleyin: https://python.org/downloads
        pause
        exit /b 1
    )
    echo.
    echo    [OK] Python yuklendi!
    echo    [i] Lutfen start.bat'i tekrar calistirin.
    echo.
    pause
    exit /b 0
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set pyver=%%v
echo    [OK] Python %pyver% mevcut
echo.

REM ══════════════════════════════════════════
echo  [ADIM 2/3] Paket Kontrolu
echo  ─────────────────────────────────────────

echo    [i] Paketler kontrol ediliyor...
python -c "import cv2, keyboard, mss, customtkinter, numpy, PIL, psutil" >nul 2>&1
if %errorlevel% neq 0 (
    echo    [!] Eksik paketler bulundu
    echo.
    echo    [i] Paketler yukleniyor...
    echo        - opencv-python
    echo        - keyboard
    echo        - mss
    echo        - customtkinter
    echo        - numpy
    echo        - Pillow
    echo        - psutil
    echo.
    python -m pip install -r requirements.txt --disable-pip-version-check
    if %errorlevel% neq 0 (
        echo.
        echo    [X] Paket yuklemesi basarisiz!
        pause
        exit /b 1
    )
    echo.
    echo    [OK] Tum paketler yuklendi!
) else (
    echo    [OK] Tum paketler mevcut
)
echo.

REM ══════════════════════════════════════════
echo  [ADIM 3/3] Uygulama Baslatiliyor
echo  ─────────────────────────────────────────
echo    [i] klad_macro_tool.py baslatiliyor...
echo.

start "" pythonw klad_macro_tool.py

echo    [OK] Uygulama baslatildi!
echo.
echo  ═══════════════════════════════════════════
echo    Pencere 3 saniye icinde kapanacak...
echo  ═══════════════════════════════════════════
timeout /t 3 >nul
