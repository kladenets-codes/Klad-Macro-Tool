"""
Klad Macro Tool - Config Manager
Functions for loading and saving configuration
"""

import json
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

from .constants import (
    DEFAULT_TIMING,
    DEFAULT_SEARCH_REGION,
    DEFAULT_SPAM_INTERVAL,
    DEFAULT_CYCLE_DELAY,
    DEFAULT_TRIGGER_CONDITION
)

logger = logging.getLogger(__name__)


def get_default_group() -> Dict[str, Any]:
    """
    Get a default group configuration.

    Returns:
        Dictionary with default group settings
    """
    return {
        "id": str(uuid.uuid4()),
        "name": "Default Group",
        "enabled": True,
        "toggle_key": "num lock",
        "spam_key": '"',
        "spam_enabled": True,
        "spam_timing": DEFAULT_TIMING.copy(),
        "spam_key_interval": DEFAULT_SPAM_INTERVAL,
        "search_region": DEFAULT_SEARCH_REGION.copy(),
        "cycle_delay": DEFAULT_CYCLE_DELAY,
        "notes": "",
        "templates": []
    }


def load_config(config_file: Path) -> Tuple[List[Dict], Dict[str, Any], List[Dict]]:
    """
    Load configuration from JSON file.

    Args:
        config_file: Path to the config.json file

    Returns:
        Tuple of (groups, global_settings, presets)
    """
    if not config_file.exists():
        logger.info("Config file not found, using defaults")
        return [get_default_group()], {"debug_enabled": False, "fps_overlay_enabled": True, "cpu_cores": 0}, []

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            groups = data.get("groups", [])
            global_settings = data.get("global_settings", {})
            presets = data.get("presets", [])

            # Migration: Eski template'lere trigger_condition ekle
            for group in groups:
                for template in group.get('templates', []):
                    if 'trigger_condition' not in template:
                        template['trigger_condition'] = DEFAULT_TRIGGER_CONDITION

            # Migration: Eski config'lere cpu_cores ekle
            if 'cpu_cores' not in global_settings:
                global_settings['cpu_cores'] = 0  # 0 = sınırsız

            logger.info(f"Config loaded: {len(groups)} groups, {len(presets)} presets")
            return groups, global_settings, presets
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return [get_default_group()], {"debug_enabled": False, "fps_overlay_enabled": True, "cpu_cores": 0}, []


def save_config(
    config_file: Path,
    groups: List[Dict],
    global_settings: Dict[str, Any],
    presets: List[Dict]
) -> bool:
    """
    Save configuration to JSON file.

    Args:
        config_file: Path to the config.json file
        groups: List of group configurations
        global_settings: Global settings dictionary
        presets: List of preset configurations

    Returns:
        True if successful, False otherwise
    """
    try:
        data = {
            "groups": groups,
            "global_settings": global_settings,
            "presets": presets
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("Config saved successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        return False


def get_conflicting_keys(groups: List[Dict]) -> set:
    """
    Find conflicting toggle keys among enabled groups.

    Args:
        groups: List of group configurations

    Returns:
        Set of keys that are used by multiple enabled groups
    """
    key_counts = {}
    for group in groups:
        if group.get('enabled', True):
            key = group.get('toggle_key', '').lower()
            if key:
                key_counts[key] = key_counts.get(key, 0) + 1
    return {k for k, v in key_counts.items() if v > 1}


def check_missing_template_images(groups: List[Dict], images_folder: Path) -> Dict[str, List[str]]:
    """
    Check for missing template images in enabled groups.

    Args:
        groups: List of group configurations
        images_folder: Path to the images folder

    Returns:
        Dictionary mapping group names to lists of missing template descriptions
    """
    missing = {}
    for group in groups:
        if not group.get('enabled', True):
            continue

        group_missing = []
        for template in group.get('templates', []):
            if not template.get('enabled', True):
                continue

            img_file = template.get('file', '')
            if not img_file:
                group_missing.append(f"{template.get('name', 'Unnamed')} (dosya yok)")
            else:
                img_path = images_folder / img_file
                if not img_path.exists():
                    group_missing.append(f"{template.get('name', 'Unnamed')} ({img_file})")

        if group_missing:
            missing[group.get('name', 'Unnamed Group')] = group_missing

    return missing


def is_hotkey_used(groups: List[Dict], key: str, exclude_group_id: Optional[str] = None) -> Optional[str]:
    """
    Check if a hotkey is already used by another group.

    Args:
        groups: List of group configurations
        key: The key to check
        exclude_group_id: Group ID to exclude from check (for editing)

    Returns:
        Name of the group using the key, or None if not used
    """
    for group in groups:
        if exclude_group_id and group.get('id') == exclude_group_id:
            continue
        if group.get('toggle_key', '').lower() == key.lower():
            return group['name']
    return None
