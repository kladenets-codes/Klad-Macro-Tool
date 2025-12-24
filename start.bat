@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo.
echo  KLAD MACRO TOOL
echo  ================
echo.

REM Python var mi?
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python bulunamadi, yukleniyor...
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    echo [i] Python yuklendi. Lutfen start.bat'i tekrar calistirin.
    pause
    exit /b
)

echo [OK] Python mevcut

REM Paketleri kontrol et ve yukle
python -c "import cv2, keyboard, mss, customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Paketler yukleniyor...
    python -m pip install -r requirements.txt -q
)

echo [OK] Paketler hazir
echo.

REM Baslat
start "" pythonw klad_macro_tool.py
