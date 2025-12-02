@echo off
setlocal

REM Python kontrol etme ve kurulum
python --version >nul 2>&1
if %errorlevel% NEQ 0 (
    echo Python yüklü değil, kuruluyor...
    REM Python'u indirin ve sessizce kurun (Python 3.10 örnek URL, güncel URL'yi kontrol edin)
    curl -o python-installer.exe https://www.python.org/ftp/python/3.10.0/python-3.10.0-amd64.exe
    start /wait python-installer.exe /quiet InstallAllUsers=1 PrependPath=1
    del python-installer.exe
)

REM Paketleri kur
echo Gereksinimler yükleniyor...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

REM config_manager.py dosyasını çalıştır
echo config_manager.py çalıştırılıyor...
python config_manager.py

endlocal
