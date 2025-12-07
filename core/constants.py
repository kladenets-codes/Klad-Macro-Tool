"""
Klad Macro Tool - Constants
All magic numbers and configuration values in one place
"""

from pathlib import Path

# Version info - version.txt'den oku
def _load_version():
    """version.txt dosyasından versiyon bilgisini oku"""
    version_file = Path(__file__).parent.parent / "version.txt"
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            lines = f.read().strip().split('\n')
            version = lines[0].strip() if len(lines) > 0 else "0.0.0"
            commit = lines[1].strip() if len(lines) > 1 else "unknown"
            return version, commit
    except:
        return "0.0.0", "unknown"

VERSION, COMMIT_HASH = _load_version()
GITHUB_REPO = "kladenets-codes/Klad-Macro-Tool"

# Timing constants (milliseconds)
STATUS_CHECK_INTERVAL_MS = 50
TEST_CYCLE_INTERVAL_MS = 100
FPS_REPORT_INTERVAL_SEC = 0.5
FPS_RESET_INTERVAL_SEC = 5.0
IDLE_SLEEP_SEC = 0.01

# UI constants
MIN_REGION_SIZE = 10
DEFAULT_THRESHOLD = 0.9
DEFAULT_SPAM_INTERVAL = 0.025
DEFAULT_CYCLE_DELAY = 0.01

# Default timing for key presses (milliseconds)
DEFAULT_TIMING = {
    "pre_delay": 1,
    "hold_time": 1,
    "post_delay": 1
}

# Default search region [x1, y1, x2, y2]
DEFAULT_SEARCH_REGION = [430, 275, 750, 460]

# Color palette for UI
COLORS = {
    "bg_dark": "#0d0d0d",
    "bg_secondary": "#1a1a1a",
    "bg_card": "#242424",
    "accent": "#00d4ff",
    "accent_hover": "#00a8cc",
    "success": "#00ff88",
    "danger": "#ff4757",
    "warning": "#ffa502",
    "text": "#ffffff",
    "text_secondary": "#888888",
    "border": "#333333"
}

# Log colors
LOG_COLORS = {
    "INFO": "#00ff88",
    "DEBUG": "#00d4ff",
    "WARN": "#ffaa00",
    "ERROR": "#ff4757",
    "MATCH": "#ff00ff"
}

# Macro action colors
MACRO_ACTION_COLORS = {
    "key_down": "#2d5a27",
    "key_up": "#5a2727",
    "key_press": "#27455a",
    "sleep": "#5a4a27"
}

# Macro action labels
MACRO_ACTION_LABELS = {
    "key_down": "↓ DOWN",
    "key_up": "↑ UP",
    "key_press": "⏎ PRESS",
    "sleep": "⏱ SLEEP"
}

# Template trigger conditions
TRIGGER_CONDITION_FOUND = "found"      # Görsel bulunduğunda tetikle
TRIGGER_CONDITION_NOT_FOUND = "not_found"  # Görsel bulunmadığında tetikle
DEFAULT_TRIGGER_CONDITION = TRIGGER_CONDITION_FOUND

# Export markers
EXPORT_START_MARKER = "===KLAD_MACRO_EXPORT_START==="
EXPORT_END_MARKER = "===KLAD_MACRO_EXPORT_END==="
