"""
Klad Macro Tool - Auto Updater
GitHub'dan commit hash kontrolü ve güncelleme indirme
"""

import urllib.request
import json
import os
import sys
import zipfile
import shutil
import tempfile
import threading
from pathlib import Path

from .constants import VERSION, COMMIT_HASH, GITHUB_REPO


def get_latest_commit():
    """GitHub'dan main branch'in son commit bilgisini al"""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/commits/main"
        req = urllib.request.Request(url, headers={"User-Agent": "Klad-Macro-Tool"})

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

            return {
                "sha": data.get("sha", ""),
                "message": data.get("commit", {}).get("message", ""),
                "author": data.get("commit", {}).get("author", {}).get("name", ""),
                "date": data.get("commit", {}).get("author", {}).get("date", ""),
                "html_url": data.get("html_url", ""),
            }
    except Exception as e:
        print(f"Update check error: {e}")
        return None


def check_for_updates():
    """
    Güncelleme kontrolü yap (commit hash'e göre).
    Returns: (has_update, commit_info) veya (False, None)
    """
    commit = get_latest_commit()
    if commit is None:
        return False, None

    latest_sha = commit["sha"]
    # Sadece ilk 7 karakter karşılaştır (short hash)
    has_update = latest_sha[:40] != COMMIT_HASH[:40]

    return has_update, commit


def download_update(commit_info, progress_callback=None):
    """
    Güncellemeyi indir (main branch ZIP olarak).
    progress_callback: (downloaded_bytes, total_bytes) -> None
    Returns: İndirilen dosyanın yolu veya None
    """
    try:
        # Main branch'ı ZIP olarak indir
        zipball_url = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip"

        # Geçici dosya oluştur
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, "klad_macro_update.zip")

        req = urllib.request.Request(zipball_url, headers={"User-Agent": "Klad-Macro-Tool"})

        with urllib.request.urlopen(req, timeout=60) as response:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            block_size = 8192

            with open(zip_path, 'wb') as f:
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    f.write(buffer)
                    downloaded += len(buffer)
                    if progress_callback:
                        progress_callback(downloaded, total_size)

        return zip_path
    except Exception as e:
        print(f"Download error: {e}")
        return None


def extract_and_install(zip_path, target_dir=None):
    """
    ZIP'i çıkar ve dosyaları güncelle.
    Returns: True eğer başarılı
    """
    try:
        if target_dir is None:
            target_dir = Path(__file__).parent.parent

        temp_extract = tempfile.mkdtemp()

        # ZIP'i çıkar
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract)

        # GitHub ZIP'leri içinde bir klasör oluşturur (örn: Klad-Macro-Tool-main)
        extracted_dirs = [d for d in os.listdir(temp_extract)
                         if os.path.isdir(os.path.join(temp_extract, d))]

        if not extracted_dirs:
            return False

        source_dir = os.path.join(temp_extract, extracted_dirs[0])

        # Dosyaları kopyala (images ve config.json hariç - kullanıcı verilerini koru)
        for item in os.listdir(source_dir):
            if item in ['images', 'config.json', '.git', '__pycache__', '.gitignore']:
                continue

            src = os.path.join(source_dir, item)
            dst = os.path.join(target_dir, item)

            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        # Temizlik
        shutil.rmtree(temp_extract)
        os.remove(zip_path)

        return True
    except Exception as e:
        print(f"Install error: {e}")
        return False


def open_github_page():
    """GitHub repo sayfasını tarayıcıda aç"""
    import webbrowser
    webbrowser.open(f"https://github.com/{GITHUB_REPO}")


def get_current_version():
    """Mevcut versiyonu döndür"""
    return VERSION


def get_current_commit():
    """Mevcut commit hash'i döndür (kısa)"""
    return COMMIT_HASH[:7]
