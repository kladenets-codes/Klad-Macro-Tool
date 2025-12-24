@echo off
cd /d "%~dp0"
title Klad Macro Tool - Launcher

echo.
echo  ========================================
echo       KLAD MACRO TOOL LAUNCHER
echo  ========================================
echo.

REM Step 1: Python Check
echo  [STEP 1/3] Python Check
echo  ----------------------------------------
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo    [X] Python not found!
    echo.
    echo    [i] Installing Python...
    echo        Source: winget / Python 3.12
    echo.
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo.
        echo    [!] Installation failed!
        echo        Manual install: https://python.org/downloads
        pause
        exit /b 1
    )
    echo.
    echo    [OK] Python installed!
    echo    [i] Please run start.bat again.
    echo.
    pause
    exit /b 0
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set pyver=%%v
echo    [OK] Python %pyver% found
echo.

REM Step 2: Package Check
echo  [STEP 2/3] Package Check
echo  ----------------------------------------

echo    [i] Checking packages...
python -c "import cv2, keyboard, mss, customtkinter, numpy, PIL, psutil" >nul 2>&1
if %errorlevel% neq 0 (
    echo    [!] Missing packages found
    echo.
    echo    [i] Installing packages...
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
        echo    [X] Package installation failed!
        pause
        exit /b 1
    )
    echo.
    echo    [OK] All packages installed!
) else (
    echo    [OK] All packages found
)
echo.

REM Step 3: Launch Application
echo  [STEP 3/3] Launching Application
echo  ----------------------------------------
echo    [i] Starting klad_macro_tool.py...
echo.

start "" pythonw klad_macro_tool.py

echo    [OK] Application started!
echo.
echo  ========================================
echo    Window will close in 3 seconds...
echo  ========================================
timeout /t 3 >nul
