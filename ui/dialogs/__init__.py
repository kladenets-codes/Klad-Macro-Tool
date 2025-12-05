# Klad Macro Tool - UI Dialogs Module

from .group_dialogs import (
    AddGroupDialog,
    EditGroupDialog,
    CaptureKeyDialogSimple,
    SelectRegionDialogSimple
)

from .template_dialogs import (
    AddTemplateDialog,
    TemplateCapture,
    TemplateFinalizeDialog,
    CaptureKeyComboDialog,
    EditTemplateDialog,
    EditTemplateCapture
)

from .preset_dialogs import (
    ExportGroupDialog,
    ImportGroupDialog,
    PresetDialog
)

__all__ = [
    # Group dialogs
    'AddGroupDialog',
    'EditGroupDialog',
    'CaptureKeyDialogSimple',
    'SelectRegionDialogSimple',
    # Template dialogs
    'AddTemplateDialog',
    'TemplateCapture',
    'TemplateFinalizeDialog',
    'CaptureKeyComboDialog',
    'EditTemplateDialog',
    'EditTemplateCapture',
    # Preset dialogs
    'ExportGroupDialog',
    'ImportGroupDialog',
    'PresetDialog',
]
