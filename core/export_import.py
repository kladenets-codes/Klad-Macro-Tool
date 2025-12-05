"""
Klad Macro Tool - Export/Import Functions
Functions for exporting and importing groups with embedded images
"""

import json
import uuid
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from .constants import EXPORT_START_MARKER, EXPORT_END_MARKER

logger = logging.getLogger(__name__)


def generate_export_code(group: Dict[str, Any], images_folder: Path) -> str:
    """
    Generate export code for a group including embedded images.

    Args:
        group: Group configuration dictionary
        images_folder: Path to the images folder

    Returns:
        Export string with markers and base64 encoded data
    """
    # Create a copy with new ID
    group_copy = group.copy()
    group_copy['id'] = str(uuid.uuid4())

    # Embed template images as base64
    templates_with_images = []
    for template in group_copy.get('templates', []):
        t_copy = template.copy()
        img_path = images_folder / template.get('file', '')
        if img_path.exists():
            try:
                with open(img_path, 'rb') as f:
                    img_data = base64.b64encode(f.read()).decode('utf-8')
                t_copy['image_data'] = img_data
            except Exception as e:
                logger.error(f"Failed to encode image {img_path}: {e}")
                t_copy['image_data'] = ''
        templates_with_images.append(t_copy)

    group_copy['templates'] = templates_with_images

    # Convert to JSON and encode
    json_str = json.dumps(group_copy, ensure_ascii=False)
    encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

    return f"{EXPORT_START_MARKER}\n{encoded}\n{EXPORT_END_MARKER}"


def parse_import_code(import_code: str, images_folder: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Parse import code and extract group with images.

    Args:
        import_code: The import string with markers
        images_folder: Path to save extracted images

    Returns:
        Tuple of (group_dict, error_message)
        If successful, error_message is None
        If failed, group_dict is None and error_message contains the error
    """
    # Validate markers
    if EXPORT_START_MARKER not in import_code or EXPORT_END_MARKER not in import_code:
        return None, "Geçersiz import kodu! Export kodunun tamamını yapıştırdığınızdan emin olun."

    try:
        # Extract base64 data
        start = import_code.find(EXPORT_START_MARKER) + len(EXPORT_START_MARKER)
        end = import_code.find(EXPORT_END_MARKER)
        encoded = import_code[start:end].strip()

        # Decode
        json_str = base64.b64decode(encoded.encode('utf-8')).decode('utf-8')
        group = json.loads(json_str)

        # Assign new ID
        group['id'] = str(uuid.uuid4())

        # Extract and save template images
        for template in group.get('templates', []):
            if 'image_data' in template and template['image_data']:
                try:
                    img_data = base64.b64decode(template['image_data'])
                    new_filename = f"imported_{uuid.uuid4().hex[:8]}.png"
                    img_path = images_folder / new_filename
                    with open(img_path, 'wb') as f:
                        f.write(img_data)
                    template['file'] = new_filename
                    logger.info(f"Imported image: {new_filename}")
                except Exception as e:
                    logger.error(f"Failed to import image: {e}")

                # Remove image_data (no longer needed)
                del template['image_data']

        return group, None

    except json.JSONDecodeError as e:
        return None, f"JSON parse hatası: {str(e)}"
    except Exception as e:
        return None, f"Import başarısız: {str(e)}"
