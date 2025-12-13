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
        "type": "group",
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


def get_default_folder() -> Dict[str, Any]:
    """
    Get a default folder configuration.

    Returns:
        Dictionary with default folder settings
    """
    return {
        "type": "folder",
        "id": str(uuid.uuid4()),
        "name": "Yeni Klasör",
        "expanded": True,
        "items": []
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

            # Migration: Eski gruplara type ekle
            def migrate_items(items):
                for item in items:
                    if 'type' not in item:
                        # Eğer 'items' anahtarı varsa klasör, yoksa grup
                        if 'items' in item:
                            item['type'] = 'folder'
                            if 'expanded' not in item:
                                item['expanded'] = True
                            migrate_items(item['items'])  # Recursive
                        else:
                            item['type'] = 'group'
                    elif item['type'] == 'folder':
                        migrate_items(item.get('items', []))  # Recursive

                    # Template migration (sadece gruplar için)
                    if item.get('type') == 'group':
                        for template in item.get('templates', []):
                            if 'trigger_condition' not in template:
                                template['trigger_condition'] = DEFAULT_TRIGGER_CONDITION

            migrate_items(groups)

            # Migration: Eski config'lere cpu_cores ekle
            if 'cpu_cores' not in global_settings:
                global_settings['cpu_cores'] = 0  # 0 = sınırsız

            logger.info(f"Config loaded: {len(groups)} items, {len(presets)} presets")
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
        # CRITICAL: Ensure all items have 'type' field before saving
        def ensure_type_field(items):
            """Recursively ensure all items have a type field"""
            for item in items:
                if 'type' not in item:
                    # Eğer 'items' anahtarı varsa klasör, yoksa grup
                    item['type'] = 'folder' if 'items' in item else 'group'

                # If folder, recursively check children
                if item.get('type') == 'folder':
                    ensure_type_field(item.get('items', []))

        ensure_type_field(groups)

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
        groups: List of group configurations (can include folders)

    Returns:
        Set of keys that are used by multiple enabled groups
    """
    key_counts = {}

    def count_keys(items):
        for item in items:
            if item.get('type') == 'folder':
                count_keys(item.get('items', []))
            elif item.get('type') == 'group':
                if item.get('enabled', True):
                    key = item.get('toggle_key', '').lower()
                    if key:
                        key_counts[key] = key_counts.get(key, 0) + 1

    count_keys(groups)
    return {k for k, v in key_counts.items() if v > 1}


def check_missing_template_images(groups: List[Dict], images_folder: Path) -> Dict[str, List[str]]:
    """
    Check for missing template images in enabled groups.

    Args:
        groups: List of group configurations (can include folders)
        images_folder: Path to the images folder

    Returns:
        Dictionary mapping group names to lists of missing template descriptions
    """
    missing = {}

    def check_items(items):
        for item in items:
            if item.get('type') == 'folder':
                check_items(item.get('items', []))
            elif item.get('type') == 'group':
                if not item.get('enabled', True):
                    continue

                group_missing = []
                for template in item.get('templates', []):
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
                    missing[item.get('name', 'Unnamed Group')] = group_missing

    check_items(groups)
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
    def check_items(items):
        for item in items:
            if item.get('type') == 'folder':
                result = check_items(item.get('items', []))
                if result:
                    return result
            elif item.get('type') == 'group':
                if exclude_group_id and item.get('id') == exclude_group_id:
                    continue
                if item.get('toggle_key', '').lower() == key.lower():
                    return item['name']
        return None

    return check_items(groups)


def flatten_groups(items: List[Dict]) -> List[Dict]:
    """
    Flatten nested folder structure to get all groups.

    Args:
        items: List of items (groups and folders)

    Returns:
        Flat list of all groups
    """
    result = []
    for item in items:
        if item.get('type') == 'folder':
            result.extend(flatten_groups(item.get('items', [])))
        elif item.get('type') == 'group':
            result.append(item)
    return result


def find_item_by_id(items: List[Dict], item_id: str) -> Optional[Dict]:
    """
    Find an item (group or folder) by ID in nested structure.

    Args:
        items: List of items to search
        item_id: ID to find

    Returns:
        Item dictionary if found, None otherwise
    """
    for item in items:
        if item.get('id') == item_id:
            return item
        if item.get('type') == 'folder':
            found = find_item_by_id(item.get('items', []), item_id)
            if found:
                return found
    return None


def remove_item_by_id(items: List[Dict], item_id: str) -> bool:
    """
    Remove an item from nested structure by ID.

    Args:
        items: List of items
        item_id: ID to remove

    Returns:
        True if removed, False otherwise
    """
    for i, item in enumerate(items):
        if item.get('id') == item_id:
            items.pop(i)
            return True
        if item.get('type') == 'folder':
            if remove_item_by_id(item.get('items', []), item_id):
                return True
    return False


def find_parent_and_index(items: List[Dict], item_id: str, parent: Optional[List] = None) -> Optional[tuple]:
    """
    Find the parent list and index of an item.

    Args:
        items: List of items to search
        item_id: ID to find
        parent: Parent list (used internally for recursion)

    Returns:
        Tuple of (parent_list, index) if found, None otherwise
    """
    if parent is None:
        parent = items

    for i, item in enumerate(items):
        if item.get('id') == item_id:
            return (items, i)
        if item.get('type') == 'folder':
            result = find_parent_and_index(item.get('items', []), item_id, item.get('items', []))
            if result:
                return result
    return None


def insert_item_at(items: List[Dict], item: Dict, target_parent: List[Dict], target_index: int) -> bool:
    """
    Insert an item at a specific position (after removing it from its current location).

    Args:
        items: Root items list
        item: Item to insert
        target_parent: Target parent list
        target_index: Target index in parent

    Returns:
        True if successful, False otherwise
    """
    # Get item ID
    item_id = item.get('id')
    if not item_id:
        return False

    # CRITICAL FIX: Önce source parent'ı ve index'i bul
    source_info = find_parent_and_index(items, item_id)
    if not source_info:
        return False

    source_parent, source_index = source_info

    # Aynı parent içinde hareket mi?
    if source_parent is target_parent:
        # Aynı parent içinde move - index'i ayarla
        if source_index < target_index:
            # Önce çıkarıldığında target_index 1 azalır
            adjusted_target = target_index - 1
        else:
            adjusted_target = target_index

        # Remove from source
        source_parent.pop(source_index)
        # Insert at target
        target_parent.insert(adjusted_target, item)
    else:
        # Farklı parent'lar arası move
        # Remove from source
        source_parent.pop(source_index)
        # Insert at target
        target_parent.insert(target_index, item)

    return True
