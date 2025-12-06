"""
Klad Macro Tool - Worker Process
Independent worker process for each group's template matching
"""

# Windows'ta worker process için konsol gizle
import sys
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    hwnd = kernel32.GetConsoleWindow()
    if hwnd:
        user32.ShowWindow(hwnd, 0)

import cv2
import numpy as np
import time
import logging
import mss
from pathlib import Path
from typing import Dict, List, Any
from multiprocessing import Queue, Value

from .keyboard_handler import press_key_with_timing, press_key_combo, execute_macro
from .constants import (
    FPS_REPORT_INTERVAL_SEC,
    FPS_RESET_INTERVAL_SEC,
    IDLE_SLEEP_SEC,
    DEFAULT_TIMING
)

logger = logging.getLogger(__name__)

# Images folder path (will be set from main module)
IMAGES_FOLDER = Path(__file__).parent.parent / "images"


def group_worker(
    group_data: Dict[str, Any],
    command_queue: Queue,
    status_queue: Queue,
    running_flag: Value
) -> None:
    """
    Worker process for each group.
    Runs independently and listens for commands.

    Args:
        group_data: Group configuration dictionary
        command_queue: Queue for receiving commands (toggle, stop)
        status_queue: Queue for sending status updates to main process
        running_flag: Shared flag to signal process termination
    """
    group_id = group_data['id']
    group_name = group_data['name']

    # Load templates (grayscale for faster matching)
    loaded_templates = _load_templates(group_data)

    search_running = False
    last_spam_time = 0

    # Settings
    spam_enabled = group_data.get('spam_enabled', False)
    spam_key = group_data.get('spam_key', None)
    spam_timing = group_data.get('spam_timing', DEFAULT_TIMING)
    spam_interval = group_data.get('spam_key_interval', 0.025)
    search_region = group_data.get('search_region', [0, 0, 100, 100])

    def press_spam_key() -> None:
        """Press spam key if enabled and interval has passed"""
        nonlocal last_spam_time
        if not spam_enabled or not spam_key:
            return

        current_time = time.perf_counter()
        if current_time - last_spam_time >= spam_interval:
            press_key_with_timing(spam_key, spam_timing)
            last_spam_time = current_time

    def process_frame(sct) -> None:
        """Process single frame for template matching"""
        nonlocal last_spam_time

        if not loaded_templates:
            press_spam_key()
            return

        frame_start = time.perf_counter()

        try:
            # Screen capture with mss (~5x faster than PIL)
            monitor = {
                "left": search_region[0],
                "top": search_region[1],
                "width": search_region[2] - search_region[0],
                "height": search_region[3] - search_region[1]
            }
            sct_img = sct.grab(monitor)
            # Convert to grayscale (faster matching)
            screenshot = np.array(sct_img)[:, :, :3]  # BGRA -> BGR
            screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        except Exception as e:
            logger.error(f"[{group_name}] Screen capture error: {e}")
            return

        found_match = None

        for data in loaded_templates:
            try:
                result = cv2.matchTemplate(screenshot_gray, data['image'], cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)

                if max_val >= data['threshold']:
                    found_match = data
                    break
            except Exception as e:
                logger.error(f"[{group_name}] Template match error: {e}")

        frame_time_ms = (time.perf_counter() - frame_start) * 1000

        if found_match:
            # Send match status to main process
            status_queue.put({
                'group_id': group_id,
                'type': 'match',
                'color': found_match['color'],
                'template': found_match['name'],
                'time_ms': round(frame_time_ms, 2)
            })

            # Execute macro or simple key press
            if found_match.get('use_macro') and found_match.get('macro'):
                execute_macro(found_match['macro'])
            else:
                press_key_combo(found_match['key_combo'], found_match.get('timing', {}))

            # Reset indicator to green after execution
            status_queue.put({
                'group_id': group_id,
                'type': 'match',
                'color': '#00FF00'
            })
        else:
            press_spam_key()

    # Main loop
    logger.info(f"[{group_name}] Worker started")
    status_queue.put({'group_id': group_id, 'type': 'status', 'status': 'ready'})

    # FPS tracking
    frame_count = 0
    fps_start_time = time.perf_counter()
    last_fps_report = time.perf_counter()

    # Create mss instance (one per worker)
    with mss.mss() as sct:
        while running_flag.value:
            # Check for commands
            try:
                while not command_queue.empty():
                    cmd = command_queue.get_nowait()
                    if cmd.get('action') == 'toggle':
                        search_running = not search_running
                        status = 'running' if search_running else 'stopped'
                        status_queue.put({
                            'group_id': group_id,
                            'type': 'status',
                            'status': status
                        })
                        logger.info(f"[{group_name}] {'Started' if search_running else 'Stopped'}")
                        # Reset FPS counter
                        frame_count = 0
                        fps_start_time = time.perf_counter()
                    elif cmd.get('action') == 'stop':
                        search_running = False
                        status_queue.put({
                            'group_id': group_id,
                            'type': 'status',
                            'status': 'stopped'
                        })
            except Exception as e:
                logger.error(f"[{group_name}] Command queue error: {e}")

            # Process frame if running
            if search_running:
                try:
                    process_frame(sct)
                    frame_count += 1
                except Exception as e:
                    logger.error(f"[{group_name}] Frame processing error: {e}")

                # Report FPS every 500ms
                current_time = time.perf_counter()
                elapsed = current_time - fps_start_time

                if current_time - last_fps_report >= FPS_REPORT_INTERVAL_SEC:
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    status_queue.put({
                        'group_id': group_id,
                        'type': 'fps',
                        'fps': round(fps, 1),
                        'name': group_name
                    })
                    last_fps_report = current_time

                    # Reset FPS counter every 5 seconds (prevent overflow)
                    if elapsed >= FPS_RESET_INTERVAL_SEC:
                        frame_count = 0
                        fps_start_time = current_time
            else:
                # Sleep when idle (reduce CPU usage)
                time.sleep(IDLE_SLEEP_SEC)

    logger.info(f"[{group_name}] Worker stopped")


def _load_templates(group_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Load and prepare templates for matching.

    Args:
        group_data: Group configuration dictionary

    Returns:
        List of template data dictionaries with loaded images
    """
    loaded_templates = []

    for template in group_data.get('templates', []):
        if not template.get('enabled', True):
            continue

        template_path = IMAGES_FOLDER / template['file']
        if template_path.exists():
            # UTF-8 path desteği için numpy ile oku
            img = cv2.imdecode(np.fromfile(str(template_path), dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                # Convert to grayscale (3x faster matching)
                img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                loaded_templates.append({
                    'name': template['name'],
                    'image': img_gray,
                    'threshold': template['threshold'],
                    'key_combo': template.get('key_combo', ''),
                    'color': template.get('color', '#00ff88'),
                    'timing': template.get('timing', DEFAULT_TIMING),
                    'use_macro': template.get('use_macro', False),
                    'macro': template.get('macro', [])
                })

    return loaded_templates
