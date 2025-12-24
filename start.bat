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

REM Oncelikle PATH'teki python'u kontrol et
set "PYTHON_EXE="
where python >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=python"
    goto :PythonFound
)

REM PATH'te yoksa, bilinen lokasyonlara bak
set "PYTHON_PATHS=%LOCALAPPDATA%\Programs\Python\Python312\python.exe;%LOCALAPPDATA%\Programs\Python\Python311\python.exe;%LOCALAPPDATA%\Programs\Python\Python310\python.exe;C:\Python312\python.exe;C:\Python311\python.exe;C:\Python310\python.exe"

for %%p in (%PYTHON_PATHS%) do (
    if exist "%%p" (
        set "PYTHON_EXE=%%p"
        echo [i] Python bulundu: %%p
        goto :PythonFound
    )
)

REM Python bulunamadi - kurulum yap
echo.
echo [!] Python bulunamadi! Otomatik kurulum baslatiliyor...
echo.
call :InstallPython
if !errorlevel! neq 0 (
    echo.
    echo [X] Python yuklenemedi!
    echo     Manuel olarak yukleyin: https://python.org/downloads
    echo.
    pause
    exit /b 1
)

REM Kurulum sonrasi tekrar kontrol et
for %%p in (%PYTHON_PATHS%) do (
    if exist "%%p" (
        set "PYTHON_EXE=%%p"
        goto :PythonFound
    )
)

REM Hala bulunamadi
echo [X] Python kuruldu ama bulunamadi. Lutfen bilgisayari yeniden baslatin.
pause
exit /b 1

:PythonFound
REM Python versiyonunu kontrol et
for /f "tokens=2" %%a in ('"%PYTHON_EXE%" --version 2^>^&1') do set "PYVER=%%a"
echo [OK] Python !PYVER! bulundu.

REM ===== PIP KONTROLU =====
echo.
echo [2/3] Gerekli paketler kontrol ediliyor...

"%PYTHON_EXE%" -m pip --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [!] pip bulunamadi, yukleniyor...
    "%PYTHON_EXE%" -m ensurepip --upgrade >nul 2>&1
)

REM Requirements kontrolu ve yukleme
if exist "requirements.txt" (
    echo     Paketler kontrol ediliyor...

    REM Tum paketleri kontrol et
    "%PYTHON_EXE%" -c "import cv2, numpy, keyboard, PIL, mss, customtkinter" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [!] Eksik paketler bulundu, yukleniyor...
        echo.
        "%PYTHON_EXE%" -m pip install -r requirements.txt --quiet --disable-pip-version-check
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

REM pythonw.exe yolunu bul
set "PYTHONW_EXE=!PYTHON_EXE:python.exe=pythonw.exe!"

REM Uygulamayi baslat
if exist "start.pyw" (
    start "" "!PYTHONW_EXE!" "start.pyw"
) else (
    if exist "klad_macro_tool.py" (
        start "" "!PYTHONW_EXE!" "klad_macro_tool.py"
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
echo.
echo  Python Kurulum Secenekleri:
echo  ---------------------------

REM Once winget dene (en guvenilir)
winget --version >nul 2>&1
if !errorlevel! equ 0 (
    echo [i] winget ile Python kuruluyor...
    echo.
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    if !errorlevel! equ 0 (
        echo.
        echo [OK] Python basariyla yuklendi!
        exit /b 0
    )
    echo [!] winget ile kurulum basarisiz, manuel indirme deneniyor...
)

REM winget yoksa veya basarisiz olduysa manuel indir
echo [i] Python 3.12 indiriliyor...
echo     (Bu islem internet hiziniza bagli olarak 1-5 dakika surebilir)
echo.

set "PYTHON_URL=https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"

REM PowerShell ile indir
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Write-Host 'Indiriliyor...'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing}" 2>nul

if not exist "%PYTHON_INSTALLER%" (
    echo [X] Python indirilemedi! Internet baglantinizi kontrol edin.
    exit /b 1
)

echo [OK] Indirme tamamlandi.
echo [i] Python kuruluyor...
echo.

REM Kurulum - PrependPath=1 ile PATH'e ekle
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1

set "INSTALL_RESULT=!errorlevel!"

REM Gecici dosyayi sil
del "%PYTHON_INSTALLER%" >nul 2>&1

if !INSTALL_RESULT! neq 0 (
    echo [X] Kurulum basarisiz! Hata kodu: !INSTALL_RESULT!
    echo     Lutfen https://python.org/downloads adresinden manuel yukleyin.
    exit /b 1
)

echo [OK] Python basariyla yuklendi!
echo.

REM PATH'i yenile (mevcut session icin)
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%b"
set "PATH=%USER_PATH%;%PATH%"

exit /b 0
