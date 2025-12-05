"""
Klad Macro Tool - Keyboard Handler
Functions for key press simulation and macro execution
"""

import keyboard
import time
from typing import Dict, List, Optional

from .constants import DEFAULT_TIMING


def press_key_with_timing(key: str, timing: Optional[Dict[str, int]] = None) -> None:
    """
    Press a key with pre-delay, hold time, and post-delay.

    Args:
        key: The key to press
        timing: Dict with pre_delay, hold_time, post_delay in milliseconds
    """
    if timing is None:
        timing = DEFAULT_TIMING

    pre_delay = timing.get("pre_delay", 1) / 1000.0
    hold_time = timing.get("hold_time", 1) / 1000.0
    post_delay = timing.get("post_delay", 1) / 1000.0

    if pre_delay > 0:
        time.sleep(pre_delay)

    keyboard.press(key)
    if hold_time > 0:
        time.sleep(hold_time)
    keyboard.release(key)

    if post_delay > 0:
        time.sleep(post_delay)


def press_key_combo(key_combo: str, timing: Optional[Dict[str, int]] = None) -> None:
    """
    Press a key combination (e.g., "shift+ctrl+a") with timing.

    Args:
        key_combo: Key combination string separated by '+'
        timing: Dict with pre_delay, hold_time, post_delay in milliseconds
    """
    if timing is None:
        timing = DEFAULT_TIMING

    pre_delay = timing.get("pre_delay", 1) / 1000.0
    hold_time = timing.get("hold_time", 1) / 1000.0
    post_delay = timing.get("post_delay", 1) / 1000.0

    keys = [k.strip().lower() for k in key_combo.split('+')]
    modifiers = []
    regular_keys = []

    for key in keys:
        if key in ['shift', 'alt', 'ctrl', 'control']:
            modifiers.append(key)
        else:
            regular_keys.append(key)

    if pre_delay > 0:
        time.sleep(pre_delay)

    # Press modifiers first
    for mod in modifiers:
        keyboard.press(mod)

    # Press and release regular keys
    for key in regular_keys:
        keyboard.press(key)
        if hold_time > 0:
            time.sleep(hold_time)
        keyboard.release(key)

    # Release modifiers in reverse order
    for mod in reversed(modifiers):
        keyboard.release(mod)

    if post_delay > 0:
        time.sleep(post_delay)


def execute_macro(macro_list: List[Dict]) -> None:
    """
    Execute a macro sequence (Logitech G Hub style).

    Supported actions:
        - key_down: Press and hold a key
        - key_up: Release a pressed key
        - key_press: Single key press and release
        - sleep: Delay in milliseconds

    Args:
        macro_list: List of action dictionaries
    """
    for action in macro_list:
        action_type = action.get('action', '')

        if action_type == 'key_down':
            key = action.get('key', '')
            if key:
                keyboard.press(key)

        elif action_type == 'key_up':
            key = action.get('key', '')
            if key:
                keyboard.release(key)

        elif action_type == 'key_press':
            key = action.get('key', '')
            if key:
                keyboard.press(key)
                keyboard.release(key)

        elif action_type == 'sleep':
            ms = action.get('ms', 0)
            if ms > 0:
                time.sleep(ms / 1000.0)
