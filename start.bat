@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Klad Macro Tool - Launcher
color 0A

echo.
echo  ╔════════════════════════════════════════╗
echo  ║     KLAD MACRO TOOL - LAUNCHER         ║
echo  ╚════════════════════════════════════════╝
echo.

cd /d "%~dp0"

REM ===== PYTHON KONTROLU =====
echo [1/3] Python kontrol ediliyor...

REM Oncelikle PATH'teki python'u kontrol et
set "PYTHON_EXE="

REM where python ile kontrol
where python >nul 2>&1
if !errorlevel! equ 0 (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        set "PYTHON_EXE=%%i"
        goto :PythonFound
    )
)

REM PATH'te yoksa, bilinen lokasyonlara bak
echo     PATH'te bulunamadi, bilinen konumlar kontrol ediliyor...

if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    goto :PythonFound
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :PythonFound
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :PythonFound
)
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    goto :PythonFound
)
if exist "C:\Python312\python.exe" (
    set "PYTHON_EXE=C:\Python312\python.exe"
    goto :PythonFound
)
if exist "C:\Python311\python.exe" (
    set "PYTHON_EXE=C:\Python311\python.exe"
    goto :PythonFound
)

REM Python bulunamadi - kurulum yap
echo.
echo  ╔════════════════════════════════════════╗
echo  ║  [!] PYTHON BULUNAMADI                 ║
echo  ║      Otomatik kurulum baslatiliyor...  ║
echo  ╚════════════════════════════════════════╝
echo.

call :InstallPython
if !errorlevel! neq 0 (
    echo.
    echo  [X] Python yuklenemedi!
    echo      Manuel olarak yukleyin: https://python.org/downloads
    echo.
    echo  Cikmak icin bir tusa basin...
    pause >nul
    exit /b 1
)

REM Kurulum sonrasi tekrar kontrol et
echo.
echo [i] Kurulum sonrasi Python kontrol ediliyor...

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :PythonFound
)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    goto :PythonFound
)

REM Hala bulunamadi - kullaniciya sor
echo.
echo  [!] Python kuruldu ama otomarik bulunamadi.
echo      Lutfen bu pencereyi kapatin ve start.bat'i tekrar calistirin.
echo.
pause
exit /b 1

:PythonFound
echo     Python yolu: !PYTHON_EXE!

REM Python versiyonunu kontrol et
for /f "tokens=2" %%a in ('"!PYTHON_EXE!" --version 2^>^&1') do set "PYVER=%%a"
echo [OK] Python !PYVER! bulundu.

REM ===== PIP KONTROLU =====
echo.
echo [2/3] Gerekli paketler kontrol ediliyor...

"!PYTHON_EXE!" -m pip --version >nul 2>&1
if !errorlevel! neq 0 (
    echo     [!] pip bulunamadi, yukleniyor...
    "!PYTHON_EXE!" -m ensurepip --upgrade
    if !errorlevel! neq 0 (
        echo     [X] pip yuklenemedi!
        pause
        exit /b 1
    )
)

REM Requirements kontrolu ve yukleme
if exist "requirements.txt" (
    echo     Paketler kontrol ediliyor...

    REM Tum paketleri kontrol et
    "!PYTHON_EXE!" -c "import cv2, numpy, keyboard, PIL, mss, customtkinter" >nul 2>&1
    if !errorlevel! neq 0 (
        echo.
        echo     [!] Eksik paketler bulundu, yukleniyor...
        echo     (Bu islem birka dakika surebilir)
        echo.
        "!PYTHON_EXE!" -m pip install -r requirements.txt
        if !errorlevel! neq 0 (
            echo.
            echo  [X] Paket yuklemesi basarisiz!
            echo      Manuel olarak calistirin: pip install -r requirements.txt
            echo.
            pause
            exit /b 1
        )
        echo.
        echo [OK] Tum paketler yuklendi.
    ) else (
        echo [OK] Tum paketler mevcut.
    )
) else (
    echo  [!] requirements.txt bulunamadi!
    pause
    exit /b 1
)

REM ===== UYGULAMAYI BASLAT =====
echo.
echo [3/3] Uygulama baslatiliyor...
echo.
echo  ════════════════════════════════════════
echo.

REM pythonw.exe yolunu bul (konsolsuz calistirmak icin)
set "PYTHONW_EXE=!PYTHON_EXE:python.exe=pythonw.exe!"

REM Uygulamayi baslat
if exist "klad_macro_tool.py" (
    echo     Baslatiyor: klad_macro_tool.py
    start "" "!PYTHONW_EXE!" "klad_macro_tool.py"
    echo.
    echo [OK] Uygulama baslatildi!
    timeout /t 2 >nul
) else (
    echo  [X] klad_macro_tool.py bulunamadi!
    pause
    exit /b 1
)

endlocal
exit /b 0


REM ═══════════════════════════════════════════════════════════════
REM                    PYTHON KURULUM FONKSIYONU
REM ═══════════════════════════════════════════════════════════════
:InstallPython

echo  Kurulum Yontemi Seciliyor...
echo.

REM ===== YONTEM 1: WINGET =====
where winget >nul 2>&1
if !errorlevel! equ 0 (
    echo  [1] winget bulundu, Python kuruluyor...
    echo.

    winget install Python.Python.3.12 -h --accept-package-agreements --accept-source-agreements

    if !errorlevel! equ 0 (
        echo.
        echo  [OK] Python winget ile basariyla yuklendi!

        REM PATH'i guncelle
        call :RefreshPath
        exit /b 0
    )
    echo.
    echo  [!] winget basarisiz, manuel indirme deneniyor...
    echo.
)

REM ===== YONTEM 2: MANUEL INDIRME =====
echo  [2] Python 3.12 indiriliyor...
echo      Kaynak: python.org
echo.

set "PYTHON_URL=https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"

echo      Indiriliyor... (30-60 MB)

REM PowerShell ile indir (progress goster)
powershell -Command "& { $ProgressPreference = 'Continue'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing; Write-Host 'Indirme tamamlandi.' } catch { Write-Host 'HATA: ' $_.Exception.Message; exit 1 } }"

if !errorlevel! neq 0 (
    echo.
    echo  [X] Indirme basarisiz! Internet baglantinizi kontrol edin.
    exit /b 1
)

if not exist "%PYTHON_INSTALLER%" (
    echo  [X] Installer dosyasi bulunamadi!
    exit /b 1
)

echo.
echo      [OK] Indirme tamamlandi.
echo.
echo  [3] Python kuruluyor...
echo      (Bu islem 1-2 dakika surebilir, lutfen bekleyin)
echo.

REM Kurulum - GORUNUR modda (passive), PATH'e ekle
"%PYTHON_INSTALLER%" /passive InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1 Include_pip=1

set "INSTALL_RESULT=!errorlevel!"

echo.

REM Gecici dosyayi sil
if exist "%PYTHON_INSTALLER%" del "%PYTHON_INSTALLER%" >nul 2>&1

if !INSTALL_RESULT! neq 0 (
    echo  [X] Kurulum basarisiz! Hata kodu: !INSTALL_RESULT!
    echo.
    echo      Lutfen su adresten manuel olarak indirin:
    echo      https://www.python.org/downloads/
    echo.
    echo      Kurulum sirasinda "Add Python to PATH" secenegini
    echo      isaretlemeyi unutmayin!
    echo.
    exit /b 1
)

echo  [OK] Python basariyla yuklendi!
echo.

REM PATH'i guncelle
call :RefreshPath

exit /b 0


REM ═══════════════════════════════════════════════════════════════
REM                    PATH GUNCELLEME FONKSIYONU
REM ═══════════════════════════════════════════════════════════════
:RefreshPath
echo  [i] PATH guncelleniyor...

REM Kullanici PATH'ini oku ve mevcut PATH'e ekle
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do (
    set "USER_PATH=%%b"
)

if defined USER_PATH (
    set "PATH=!USER_PATH!;!PATH!"
)

REM Sistem PATH'ini de ekle
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do (
    set "SYS_PATH=%%b"
)

if defined SYS_PATH (
    set "PATH=!SYS_PATH!;!PATH!"
)

exit /b 0
