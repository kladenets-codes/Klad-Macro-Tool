"""
Klad Macro Tool - Core Module

This module contains the core functionality:
- constants: All configuration values and magic numbers
- keyboard_handler: Key press simulation and macro execution
- worker: Worker process for template matching
- config: Configuration loading and saving
- export_import: Group export/import functionality
- keyboard_utils: Keyboard key name utilities
"""

from .constants import (
    # Version
    VERSION,
    COMMIT_HASH,
    GITHUB_REPO,

    # Timing (used by worker)
    STATUS_CHECK_INTERVAL_MS,
    TEST_CYCLE_INTERVAL_MS,
    FPS_REPORT_INTERVAL_SEC,
    FPS_RESET_INTERVAL_SEC,
    IDLE_SLEEP_SEC,

    # UI
    MIN_REGION_SIZE,
    DEFAULT_THRESHOLD,
    DEFAULT_SPAM_INTERVAL,
    DEFAULT_CYCLE_DELAY,
    DEFAULT_TIMING,
    DEFAULT_SEARCH_REGION,

    # Colors
    COLORS,
    LOG_COLORS,
    MACRO_ACTION_COLORS,
    MACRO_ACTION_LABELS,

    # Export
    EXPORT_START_MARKER,
    EXPORT_END_MARKER,
)

from .keyboard_handler import (
    press_key_with_timing,
    press_key_combo,
    execute_macro,
)

from .worker import group_worker

from .config import (
    get_default_group,
    load_config,
    save_config,
    get_conflicting_keys,
    check_missing_template_images,
    is_hotkey_used,
)

from .export_import import (
    generate_export_code,
    parse_import_code,
)

from .keyboard_utils import get_physical_key_name

__all__ = [
    # Version
    'VERSION',
    'COMMIT_HASH',
    'GITHUB_REPO',
    # Constants
    'STATUS_CHECK_INTERVAL_MS',
    'TEST_CYCLE_INTERVAL_MS',
    'FPS_REPORT_INTERVAL_SEC',
    'FPS_RESET_INTERVAL_SEC',
    'IDLE_SLEEP_SEC',
    'MIN_REGION_SIZE',
    'DEFAULT_THRESHOLD',
    'DEFAULT_SPAM_INTERVAL',
    'DEFAULT_CYCLE_DELAY',
    'DEFAULT_TIMING',
    'DEFAULT_SEARCH_REGION',
    'COLORS',
    'LOG_COLORS',
    'MACRO_ACTION_COLORS',
    'MACRO_ACTION_LABELS',
    'EXPORT_START_MARKER',
    'EXPORT_END_MARKER',

    # Keyboard
    'press_key_with_timing',
    'press_key_combo',
    'execute_macro',
    'get_physical_key_name',

    # Worker
    'group_worker',

    # Config
    'get_default_group',
    'load_config',
    'save_config',
    'get_conflicting_keys',
    'check_missing_template_images',
    'is_hotkey_used',

    # Export/Import
    'generate_export_code',
    'parse_import_code',
]
