@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Klad Macro Tool - Launcher
color 0A

echo.
echo  ========================================
echo       KLAD MACRO TOOL - LAUNCHER
echo  ========================================
echo.

cd /d "%~dp0"

REM ===== PYTHON KONTROLU =====
echo [1/3] Python kontrol ediliyor...

where python >nul 2>&1
if !errorlevel! neq 0 (
    echo.
    echo [!] Python bulunamadi! Yukleme baslatiliyor...
    echo.
    call :InstallPython
    if !errorlevel! neq 0 (
        echo [X] Python yuklenemedi! Manuel olarak yukleyin: https://python.org
        pause
        exit /b 1
    )
)

REM Python versiyonunu kontrol et
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set "PYVER=%%a"
echo [OK] Python !PYVER! bulundu.

REM ===== PIP KONTROLU =====
echo.
echo [2/3] Gerekli paketler kontrol ediliyor...

python -m pip --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [!] pip bulunamadi, yukleniyor...
    python -m ensurepip --upgrade >nul 2>&1
)

REM Requirements kontrolu ve yukleme
if exist "requirements.txt" (
    echo     Paketler kontrol ediliyor...

    REM Tum paketleri kontrol et
    python -c "import cv2, numpy, keyboard, PIL, mss, customtkinter" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [!] Eksik paketler bulundu, yukleniyor...
        echo.
        python -m pip install -r requirements.txt --quiet --disable-pip-version-check
        if !errorlevel! neq 0 (
            echo [X] Paket yuklemesi basarisiz!
            echo     Manuel olarak calistirin: pip install -r requirements.txt
            pause
            exit /b 1
        )
        echo [OK] Tum paketler yuklendi.
    ) else (
        echo [OK] Tum paketler mevcut.
    )
) else (
    echo [!] requirements.txt bulunamadi!
)

REM ===== UYGULAMAYI BASLAT =====
echo.
echo [3/3] Uygulama baslatiliyor...
echo.
echo  ========================================
echo.

REM Uygulamayi baslat
if exist "start.pyw" (
    start "" pythonw "start.pyw"
) else (
    if exist "klad_macro_tool.py" (
        start "" pythonw "klad_macro_tool.py"
    ) else (
        echo [X] Ana dosya bulunamadi!
        pause
        exit /b 1
    )
)

endlocal
exit /b 0

REM ===== PYTHON YUKLEME FONKSIYONU =====
:InstallPython
echo Python indiriliyor...

set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"

powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe' -OutFile '%PYTHON_INSTALLER%'" 2>nul

if not exist "%PYTHON_INSTALLER%" (
    echo [X] Python indirilemedi!
    exit /b 1
)

echo Python yukleniyor...

"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0

if !errorlevel! neq 0 (
    echo [X] Kurulum basarisiz!
    del "%PYTHON_INSTALLER%" >nul 2>&1
    exit /b 1
)

del "%PYTHON_INSTALLER%" >nul 2>&1

echo [OK] Python basariyla yuklendi!
echo [!] Lutfen bu scripti tekrar calistirin.
pause
exit /b 0
