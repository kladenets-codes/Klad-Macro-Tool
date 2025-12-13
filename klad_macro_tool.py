"""
Klad Macro Tool
Groups System with Multiprocessing
"""

# Windows'ta konsol penceresini gizle
import sys
import os
if sys.platform == "win32":
    import ctypes
    # Konsol penceresini gizle (GUI uygulaması olarak çalış)
    kernel32 = ctypes.WinDLL('kernel32')
    user32 = ctypes.WinDLL('user32')
    hwnd = kernel32.GetConsoleWindow()
    if hwnd:
        user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0

import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk
import cv2
import numpy as np
from pathlib import Path
import keyboard
import time
import multiprocessing
from multiprocessing import Process, Queue, Value
import logging
import copy

# Core module imports
from core import (
    # Version
    VERSION,
    COMMIT_HASH,
    # Constants
    COLORS,
    LOG_COLORS,
    MACRO_ACTION_COLORS,
    MACRO_ACTION_LABELS,
    STATUS_CHECK_INTERVAL_MS,
    TEST_CYCLE_INTERVAL_MS,
    DEFAULT_TIMING,
    DEFAULT_SEARCH_REGION,
    EXPORT_START_MARKER,
    EXPORT_END_MARKER,
    MIN_REGION_SIZE,

    # Functions
    group_worker,
    load_config as core_load_config,
    save_config as core_save_config,
    get_conflicting_keys,
    check_missing_template_images,
    is_hotkey_used,
    generate_export_code,
    parse_import_code,
    get_default_group,
    get_default_folder,
    flatten_groups,
    find_item_by_id,
    remove_item_by_id,
    find_parent_and_index,
    insert_item_at,
)

# UI module imports - lazy loaded for faster startup
# Dialog classes are imported when first needed

# CustomTkinter ayarları
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Paths
CONFIG_FILE = Path(__file__).parent / "config.json"
IMAGES_FOLDER = Path(__file__).parent / "images"

# Ensure folders exist
IMAGES_FOLDER.mkdir(exist_ok=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ==================== MAIN APPLICATION ====================
# Note: group_worker is now imported from core.worker

class ConfigManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Klad Macro Tool")
        self.root.geometry("1100x800")
        self.root.minsize(950, 700)

        # Renk paleti (core/constants.py'den)
        self.colors = COLORS

        # Groups data
        self.groups = []
        self.global_settings = {
            "debug_enabled": False,
            "fps_overlay_enabled": True,
            "cpu_cores": 0  # 0 = sınırsız
        }
        self.presets = []

        # Process management
        self.processes = {}  # group_id -> Process
        self.command_queues = {}  # group_id -> Queue
        self.status_queue = None
        self.running_flags = {}  # group_id -> Value
        self.bot_active = False

        # UI state
        self.selected_group_index = None
        self.selected_template_index = None
        self.selected_folder_id = None  # Seçili klasörün ID'si (grup eklerken klasör içine eklemek için)

        # Widget pools for reuse
        self.group_card_pool = []  # Reusable group cards
        self.template_card_pool = []  # Reusable template cards

        # Drag & drop state for groups/folders
        self.item_drag_data = {
            'active': False,
            'item': None,  # Item being dragged (group or folder dict)
            'source_parent': None,  # Parent list where item came from
            'source_index': None  # Index in source parent
        }
        self.item_drop_indicator = None
        self.drag_preview_window = None  # Floating preview window during drag

        # Indicator windows
        self.indicator_windows = {}  # group_id -> (window, label)

        # FPS tracking
        self.fps_data = {}  # group_id -> {'fps': 0, 'name': ''}
        self.fps_overlay = None
        self.fps_labels = {}
        self.fps_label_frame = None

        # Test mode
        self.test_mode_active = False
        self.test_overlay = None
        self.test_labels = {}  # group_id -> {template_name -> label}
        self.test_update_job = None

        # Load existing config
        self.load_config()

        # Build UI
        self.build_ui()

        # Start status monitor
        self.root.after(100, self.check_status_queue)

        # Güncelleme kontrolü (arka planda)
        self.root.after(1000, self.check_for_updates)

    def build_ui(self):
        """Build the modern UI with groups tab system"""
        self.root.configure(fg_color=self.colors["bg_dark"])

        # Header
        header_frame = ctk.CTkFrame(self.root, fg_color=self.colors["bg_secondary"], height=60, corner_radius=0)
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)

        title_label = ctk.CTkLabel(
            header_frame,
            text="⚡ TEMPLATE CONFIG MANAGER",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=self.colors["accent"]
        )
        title_label.pack(side="left", padx=20, pady=15)

        ctk.CTkLabel(
            header_frame,
            text=f"v{VERSION} ({COMMIT_HASH[:7]})",
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text_secondary"]
        ).pack(side="left", padx=5, pady=15)

        # ==================== TAB SYSTEM ====================
        self.tabview = ctk.CTkTabview(
            self.root,
            fg_color=self.colors["bg_card"],
            segmented_button_fg_color=self.colors["bg_secondary"],
            segmented_button_selected_color=self.colors["accent"],
            segmented_button_selected_hover_color=self.colors["accent_hover"],
            segmented_button_unselected_color=self.colors["bg_secondary"],
            segmented_button_unselected_hover_color=self.colors["border"],
            text_color="#000000",
            text_color_disabled=self.colors["text_secondary"],
            corner_radius=15
        )
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(15, 10))

        self.tabview.add("📁 Groups")
        self.tabview.add("⚙️ Genel Ayarlar")

        # Tab text colors: unselected=white, selected=black
        self.tabview._segmented_button.configure(
            text_color=("#ffffff", "#ffffff"),
            selected_color=self.colors["accent"],
            selected_hover_color=self.colors["accent_hover"],
            unselected_color=self.colors["bg_secondary"],
            unselected_hover_color=self.colors["border"]
        )
        self.tabview.configure(command=self.on_tab_change)
        self.update_tab_text_colors()

        # ==================== GROUPS TAB ====================
        self.build_groups_tab()

        # ==================== SETTINGS TAB ====================
        self.build_settings_tab()

        # ==================== BOTTOM BAR ====================
        self.build_bottom_bar()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_tab_change(self):
        """Called when tab is changed"""
        self.update_tab_text_colors()

    def update_tab_text_colors(self):
        """Update tab text colors: selected=black, unselected=white"""
        current_tab = self.tabview.get()
        for name, button in self.tabview._segmented_button._buttons_dict.items():
            if name == current_tab:
                button._text_label.configure(fg="#000000")
            else:
                button._text_label.configure(fg="#ffffff")

    def build_groups_tab(self):
        """Build the groups tab"""
        groups_tab = self.tabview.tab("📁 Groups")

        # Main container
        main_container = ctk.CTkFrame(groups_tab, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Left panel - Group list (wider for better visibility)
        left_panel = ctk.CTkFrame(main_container, fg_color=self.colors["bg_secondary"], corner_radius=12, width=360)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        left_panel.pack_propagate(False)

        # Sol panel içinde 2 sütun oluştur
        left_panel_content = ctk.CTkFrame(left_panel, fg_color="transparent")
        left_panel_content.pack(fill="both", expand=True, padx=8, pady=8)

        # 1. Sütun (Sol): Butonlar - %15 genişlik (54px = 360 * 0.15)
        button_column = ctk.CTkFrame(left_panel_content, fg_color="transparent", width=54)
        button_column.pack(side="left", fill="y", padx=(0, 6))
        button_column.pack_propagate(False)

        # 2. Sütun (Sağ): Gruplar - %85 genişlik
        groups_column = ctk.CTkFrame(left_panel_content, fg_color="transparent")
        groups_column.pack(side="left", fill="both", expand=True)

        # Group list header (sağ sütunda)
        ctk.CTkLabel(
            groups_column,
            text="📁 Gruplar",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", padx=8, pady=(8, 10))

        # Group list (sağ sütunda)
        self.group_scroll = ctk.CTkScrollableFrame(
            groups_column,
            fg_color="transparent",
            scrollbar_button_color=self.colors["accent"],
            scrollbar_button_hover_color=self.colors["accent_hover"]
        )
        self.group_scroll.pack(fill="both", expand=True, padx=0, pady=5)


        # --- GRUPLAR Section (Sol sütunda - button_column) ---
        # GRUPLAR title
        ctk.CTkLabel(
            button_column,
            text="GRUPLAR",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=self.colors["text_secondary"]
        ).pack(pady=(0, 6))

        # Ekle button
        ctk.CTkButton(
            button_column,
            text="➕",
            width=48,
            height=36,
            corner_radius=6,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            text_color="#000000",
            font=ctk.CTkFont(size=20),
            anchor="center",
            command=self.add_group
        ).pack(pady=(0, 4))

        # Düzenle button
        ctk.CTkButton(
            button_column,
            text="✏️",
            width=48,
            height=36,
            corner_radius=6,
            fg_color="#3a3a4e",
            hover_color="#4a4a5e",
            text_color="#ffffff",
            font=ctk.CTkFont(size=20),
            anchor="center",
            command=self.edit_group
        ).pack(pady=(0, 4))

        # Sil button
        ctk.CTkButton(
            button_column,
            text="🗑",
            width=48,
            height=36,
            corner_radius=6,
            fg_color=self.colors["danger"],
            hover_color="#d93a47",
            text_color="#ffffff",
            font=ctk.CTkFont(size=22),
            anchor="center",
            command=self.delete_group
        ).pack(pady=(0, 4))

        # Klasör Ekle button
        ctk.CTkButton(
            button_column,
            text="📁",
            width=48,
            height=36,
            corner_radius=6,
            fg_color="#6b5b3d",
            hover_color="#8b7b5d",
            text_color="#ffffff",
            font=ctk.CTkFont(size=20),
            anchor="center",
            command=self.add_folder
        ).pack(pady=(0, 8))

        # Separator
        ctk.CTkFrame(
            button_column,
            fg_color=self.colors["border"],
            height=2
        ).pack(fill="x", pady=(0, 8))

        # --- IMPORT Section ---
        # IMPORT title
        ctk.CTkLabel(
            button_column,
            text="IMPORT",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=self.colors["text_secondary"]
        ).pack(pady=(0, 6))

        # Import button
        ctk.CTkButton(
            button_column,
            text="📥",
            width=48,
            height=36,
            corner_radius=6,
            fg_color="#6b5b3d",
            hover_color="#8b7b5d",
            text_color="#ffffff",
            font=ctk.CTkFont(size=20),
            anchor="center",
            command=self.import_group
        ).pack(pady=(0, 4))

        # Export button
        ctk.CTkButton(
            button_column,
            text="📤",
            width=48,
            height=36,
            corner_radius=6,
            fg_color="#2d6a2d",
            hover_color="#3d8a3d",
            text_color="#ffffff",
            font=ctk.CTkFont(size=20),
            anchor="center",
            command=self.export_group
        ).pack(pady=(0, 4))

        # Presets button
        ctk.CTkButton(
            button_column,
            text="⚙️",
            width=48,
            height=36,
            corner_radius=6,
            fg_color="#5a4a7a",
            hover_color="#7a6a9a",
            text_color="#ffffff",
            font=ctk.CTkFont(size=20),
            anchor="center",
            command=self.open_presets
        ).pack(pady=(0, 4))

        # Right panel - Group details
        right_panel = ctk.CTkFrame(main_container, fg_color="transparent")
        right_panel.pack(side="right", fill="both", expand=True)

        # Group details card
        self.group_details_frame = ctk.CTkFrame(right_panel, fg_color=self.colors["bg_secondary"], corner_radius=12)
        self.group_details_frame.pack(fill="x", pady=(0, 10))

        self.group_details_content = ctk.CTkFrame(self.group_details_frame, fg_color="transparent")
        self.group_details_content.pack(fill="x", padx=20, pady=15)

        # Selected group indicator with background
        self.group_name_container = ctk.CTkFrame(
            self.group_details_content,
            fg_color=self.colors["bg_dark"],
            corner_radius=8
        )
        self.group_name_container.pack(fill="x", pady=(0, 10))

        self.group_name_label = ctk.CTkLabel(
            self.group_name_container,
            text="Bir grup seçin...",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors["text"]
        )
        self.group_name_label.pack(anchor="w", padx=12, pady=8)

        self.group_info_label = ctk.CTkLabel(
            self.group_details_content,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text_secondary"]
        )
        self.group_info_label.pack(anchor="w", pady=(5, 0))

        self.group_notes_label = ctk.CTkLabel(
            self.group_details_content,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=self.colors["text_secondary"],
            wraplength=500,
            justify="left"
        )
        self.group_notes_label.pack(anchor="w", pady=(5, 0))

        # Templates section for selected group
        templates_frame = ctk.CTkFrame(right_panel, fg_color=self.colors["bg_secondary"], corner_radius=12)
        templates_frame.pack(fill="both", expand=True)

        templates_header = ctk.CTkFrame(templates_frame, fg_color="transparent")
        templates_header.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            templates_header,
            text="📋 Bu Grubun Template'leri",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["text"]
        ).pack(side="left")

        # Template buttons
        template_btn_frame = ctk.CTkFrame(templates_header, fg_color="transparent")
        template_btn_frame.pack(side="right")

        self.add_template_btn = ctk.CTkButton(
            template_btn_frame,
            text="+ Ekle",
            width=70,
            height=28,
            corner_radius=6,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            font=ctk.CTkFont(size=11),
            anchor="center",
            command=self.add_template
        )
        self.add_template_btn.pack(side="left", padx=(0, 5))

        self.edit_template_btn = ctk.CTkButton(
            template_btn_frame,
            text=" ✏️",
            width=40,
            height=32,
            corner_radius=8,
            fg_color=self.colors["bg_dark"],
            hover_color=self.colors["border"],
            font=ctk.CTkFont(size=13),
            command=self.edit_template
        )
        self.edit_template_btn.pack(side="left", padx=(0, 6))

        self.delete_template_btn = ctk.CTkButton(
            template_btn_frame,
            text=" 🗑",
            width=40,
            height=32,
            corner_radius=8,
            fg_color=self.colors["danger"],
            hover_color="#cc3a47",
            font=ctk.CTkFont(size=13),
            command=self.delete_template
        )
        self.delete_template_btn.pack(side="left", padx=(0, 6))

        self.duplicate_template_btn = ctk.CTkButton(
            template_btn_frame,
            text=" 📋",
            width=40,
            height=32,
            corner_radius=8,
            fg_color="#5a4a27",
            hover_color="#7a6a47",
            font=ctk.CTkFont(size=13),
            command=self.duplicate_template
        )
        self.duplicate_template_btn.pack(side="left")

        # Template list
        self.template_scroll = ctk.CTkScrollableFrame(
            templates_frame,
            fg_color="transparent",
            scrollbar_button_color=self.colors["accent"],
            scrollbar_button_hover_color=self.colors["accent_hover"]
        )
        self.template_scroll.pack(fill="both", expand=True, padx=8, pady=5)

        # Populate lists
        self.refresh_group_list()

    def build_settings_tab(self):
        """Build the general settings tab"""
        settings_tab = self.tabview.tab("⚙️ Genel Ayarlar")

        settings_scroll = ctk.CTkScrollableFrame(
            settings_tab,
            fg_color="transparent",
            scrollbar_button_color=self.colors["accent"],
            scrollbar_button_hover_color=self.colors["accent_hover"]
        )
        settings_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Debug card
        debug_card = ctk.CTkFrame(settings_scroll, fg_color=self.colors["bg_secondary"], corner_radius=12)
        debug_card.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            debug_card,
            text="🔧 Debug Ayarları",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["accent"]
        ).pack(anchor="w", padx=20, pady=(15, 10))

        debug_content = ctk.CTkFrame(debug_card, fg_color="transparent")
        debug_content.pack(fill="x", padx=20, pady=(0, 15))

        self.debug_var = ctk.BooleanVar(value=self.global_settings.get("debug_enabled", False))
        ctk.CTkCheckBox(
            debug_content,
            text="Debug Modu (Detaylı log)",
            variable=self.debug_var,
            font=ctk.CTkFont(size=13),
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            command=self.toggle_debug_mode
        ).pack(anchor="w")

        self.fps_overlay_var = ctk.BooleanVar(value=self.global_settings.get("fps_overlay_enabled", True))
        ctk.CTkCheckBox(
            debug_content,
            text="FPS Overlay (Ekranda göster)",
            variable=self.fps_overlay_var,
            font=ctk.CTkFont(size=13),
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            command=self.toggle_fps_overlay
        ).pack(anchor="w", pady=(8, 0))

        # CPU Çekirdek Slider
        cpu_limit_frame = ctk.CTkFrame(debug_content, fg_color="transparent")
        cpu_limit_frame.pack(anchor="w", pady=(12, 0), fill="x")

        ctk.CTkLabel(
            cpu_limit_frame,
            text="CPU Çekirdek:",
            font=ctk.CTkFont(size=13)
        ).pack(side="left")

        # Toplam çekirdek sayısını al
        import psutil
        self.total_cpu_cores = psutil.cpu_count(logical=True) or 4
        current_cores = self.global_settings.get("cpu_cores", 0)  # 0 = sınırsız
        if current_cores == 0 or current_cores > self.total_cpu_cores:
            current_cores = self.total_cpu_cores

        self.cpu_cores_slider = ctk.CTkSlider(
            cpu_limit_frame,
            from_=1,
            to=self.total_cpu_cores,
            number_of_steps=self.total_cpu_cores - 1,
            width=150,
            height=16,
            fg_color=self.colors["bg_dark"],
            progress_color=self.colors["accent"],
            button_color=self.colors["accent"],
            button_hover_color=self.colors["accent_hover"],
            command=self.on_cpu_cores_change
        )
        self.cpu_cores_slider.pack(side="left", padx=(10, 5))
        self.cpu_cores_slider.set(current_cores)

        # Değer etiketi
        display_text = "Sınırsız" if current_cores == self.total_cpu_cores else f"{current_cores}/{self.total_cpu_cores}"
        self.cpu_cores_label = ctk.CTkLabel(
            cpu_limit_frame,
            text=display_text,
            font=ctk.CTkFont(size=12),
            width=70,
            text_color=self.colors["accent"]
        )
        self.cpu_cores_label.pack(side="left")

        # Log Console card
        log_card = ctk.CTkFrame(settings_scroll, fg_color=self.colors["bg_secondary"], corner_radius=12)
        log_card.pack(fill="both", expand=True, pady=(0, 15))

        log_header = ctk.CTkFrame(log_card, fg_color="transparent")
        log_header.pack(fill="x", padx=20, pady=(15, 10))

        ctk.CTkLabel(
            log_header,
            text="📋 Log Konsolu",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["accent"]
        ).pack(side="left")

        ctk.CTkButton(
            log_header,
            text="Temizle",
            width=70,
            height=26,
            corner_radius=6,
            fg_color=self.colors["bg_dark"],
            hover_color=self.colors["border"],
            font=ctk.CTkFont(size=11),
            command=self.clear_log
        ).pack(side="right")

        # Log text area
        self.log_text = ctk.CTkTextbox(
            log_card,
            fg_color=self.colors["bg_dark"],
            text_color="#00ff88",
            font=ctk.CTkFont(family="Consolas", size=11),
            height=200,
            corner_radius=8
        )
        self.log_text.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        self.log_text.configure(state="disabled")

        # İlk log mesajı
        self.add_log("Log konsolu hazır.")

        # Info card
        info_card = ctk.CTkFrame(settings_scroll, fg_color=self.colors["bg_secondary"], corner_radius=12)
        info_card.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            info_card,
            text="ℹ️ Bilgi",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["accent"]
        ).pack(anchor="w", padx=20, pady=(15, 10))

        info_text = """Her grup bağımsız olarak çalışır.
• Her grubun kendi start/stop tuşu vardır
• Her grubun kendi arama bölgesi vardır
• Her grubun opsiyonel spam tuşu vardır
• Gruplar aynı anda aktif olabilir

Kullanım:
1. 'BAŞLAT' butonuna tıklayın
2. Her grubun kendi tuşuyla başlatın/durdurun
3. Sol üst köşedeki indicator'lar durumu gösterir"""

        ctk.CTkLabel(
            info_card,
            text=info_text,
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text_secondary"],
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 15))

    def build_bottom_bar(self):
        """Build the bottom control bar"""
        bottom_bar = ctk.CTkFrame(self.root, fg_color=self.colors["bg_secondary"], height=70, corner_radius=0)
        bottom_bar.pack(fill="x", side="bottom", padx=0, pady=0)
        bottom_bar.pack_propagate(False)

        bottom_content = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        bottom_content.pack(fill="both", expand=True, padx=20, pady=12)

        # Left - Start/Stop All and Save
        left_controls = ctk.CTkFrame(bottom_content, fg_color="transparent")
        left_controls.pack(side="left")

        self.start_stop_btn = ctk.CTkButton(
            left_controls,
            text="▶  BAŞLAT",
            width=140,
            height=45,
            corner_radius=10,
            fg_color=self.colors["success"],
            hover_color="#00cc6e",
            text_color="#000000",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.toggle_all_bots
        )
        self.start_stop_btn.pack(side="left", padx=(0, 10))

        self.test_mode_btn = ctk.CTkButton(
            left_controls,
            text="🧪  Test",
            width=100,
            height=45,
            corner_radius=10,
            fg_color=self.colors["warning"],
            hover_color="#e6a800",
            text_color="#000000",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.toggle_test_mode
        )
        self.test_mode_btn.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            left_controls,
            text="💾  Kaydet",
            width=100,
            height=45,
            corner_radius=10,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            text_color="#000000",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.save_config
        ).pack(side="left", padx=(0, 10))

        # Right - Status
        right_controls = ctk.CTkFrame(bottom_content, fg_color="transparent")
        right_controls.pack(side="right")

        self.status_label = ctk.CTkLabel(
            right_controls,
            text="Durdu",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["danger"]
        )
        self.status_label.pack(side="right")

        self.status_indicator = ctk.CTkFrame(
            right_controls,
            width=12,
            height=12,
            corner_radius=6,
            fg_color=self.colors["danger"]
        )
        self.status_indicator.pack(side="right", padx=(0, 8))

    # ==================== GROUP MANAGEMENT ====================

    def refresh_group_list(self):
        """Refresh the group list (supports nested folders)"""
        # Clear existing widgets
        for widget in self.group_scroll.winfo_children():
            widget.pack_forget()

        # Çakışan key'leri bir kez hesapla
        conflicting_keys = self.get_conflicting_keys()

        # Render items recursively
        self._render_items(self.groups, level=0, conflicting_keys=conflicting_keys, parent_widget=self.group_scroll, parent_folder=None)

    def _render_items(self, items, level, conflicting_keys, parent_widget=None, parent_list=None, parent_folder=None):
        """Recursively render items (groups and folders)"""
        if parent_list is None:
            parent_list = items
        if parent_widget is None:
            parent_widget = self.group_scroll

        for i, item in enumerate(items):
            item_type = item.get('type', 'group')

            if item_type == 'folder':
                self._render_folder(item, level, i, parent_list, conflicting_keys, parent_folder, parent_widget)
            else:  # group
                self._render_group(item, level, i, conflicting_keys, parent_list, parent_folder, parent_widget)

    def _render_folder(self, folder, level, index, parent_list, conflicting_keys, parent_folder, parent_widget):
        """Render a folder card with border container"""
        is_selected = folder.get('id') == self.selected_folder_id
        is_expanded = folder.get('expanded', True)

        # Get folder colors (default to gold theme if not set)
        folder_bg = folder.get('color_bg', '#3a3a4e')
        folder_fg = folder.get('color_fg', '#ffcc00')

        # Create container frame with border (klasör renginde çerçeve)
        container = ctk.CTkFrame(
            parent_widget,
            fg_color="transparent",
            border_width=2,
            border_color=folder_fg,  # Klasör rengi border
            corner_radius=10
        )
        container.pack(fill="x", pady=4, padx=(4 + level * 20, 4))

        # Create folder header card inside container
        card = ctk.CTkFrame(
            container,
            fg_color=self.colors["accent"] if is_selected else folder_bg,
            corner_radius=8,
            height=55
        )
        card.pack(fill="x", pady=5, padx=5)
        card.pack_propagate(False)

        # Store metadata for drag & drop
        card._item_data = {
            'item': folder,
            'parent_list': parent_list,
            'index': index,
            'level': level
        }

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=8)

        # Drag handle
        drag_handle = ctk.CTkLabel(
            content,
            text="≡",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["text_secondary"],
            width=20,
            cursor="hand2"
        )
        drag_handle.pack(side="left", padx=(0, 8))

        # Expand/collapse button - daha belirgin
        expand_icon = "▼" if is_expanded else "▶"
        expand_btn = ctk.CTkButton(
            content,
            text=expand_icon,
            width=28,
            height=28,
            fg_color="#444444",
            hover_color="#555555",
            text_color="#ffffff",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=4
        )
        expand_btn.pack(side="left", padx=(0, 8))

        # Get folder ID first (needed for buttons)
        folder_id = folder.get('id')

        # Folder icon + name - daha güzel
        folder_label = ctk.CTkLabel(
            content,
            text=f"📁  {folder.get('name', 'Unnamed Folder')}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff" if is_selected else folder_fg,  # Use saved color
            anchor="w"
        )
        folder_label.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Item count badge - küçük
        item_count = len(folder.get('items', []))
        count_label = ctk.CTkLabel(
            content,
            text=f"{item_count}",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#aaaaaa",
            fg_color="#3a3a4e",
            corner_radius=10,
            width=24,
            height=20
        )
        count_label.pack(side="right", padx=(6, 0))

        # Edit button for folder
        edit_btn = ctk.CTkButton(
            content,
            text="✏️",
            width=28,
            height=28,
            corner_radius=6,
            fg_color="#444444",
            hover_color="#555555",
            text_color="#ffffff",
            font=ctk.CTkFont(size=12),
            command=lambda fid=folder_id: self._edit_folder(fid)
        )
        edit_btn.pack(side="right", padx=(0, 0))

        # Bind events
        expand_btn.configure(command=lambda fid=folder_id: self._toggle_folder(fid))

        # Selection events - klasöre tıklandığında seç
        for widget in [card, content, folder_label, count_label]:
            widget.bind('<Button-1>', lambda _, fid=folder_id: self.select_folder(fid))

        # Drag & drop events
        drag_handle.bind('<Button-1>', lambda e, item=folder, plist=parent_list: self._item_drag_start(e, item, plist))
        drag_handle.bind('<B1-Motion>', self._item_drag_motion)
        drag_handle.bind('<ButtonRelease-1>', self._item_drag_end)

        # Render children if expanded
        if is_expanded:
            children = folder.get('items', [])
            if children:
                conflicting_keys = self.get_conflicting_keys()
                # Render children inside the container (klasör border'ı içinde)
                self._render_items(children, level + 1, conflicting_keys, parent_widget=container, parent_list=children, parent_folder=folder)

    def _toggle_folder(self, folder_id):
        """Toggle folder expanded state"""
        folder = find_item_by_id(self.groups, folder_id)
        if folder:
            folder['expanded'] = not folder.get('expanded', True)
            self.refresh_group_list()

    def _edit_folder(self, folder_id):
        """Edit folder name and color"""
        folder = find_item_by_id(self.groups, folder_id)
        if not folder:
            return

        # Create edit dialog
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Klasörü Düzenle")
        dialog.geometry("450x340")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        # Center window
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (340 // 2)
        dialog.geometry(f"450x340+{x}+{y}")

        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=30, pady=20)

        ctk.CTkLabel(
            main,
            text="📁 Klasörü Düzenle",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors["accent"]
        ).pack(pady=(0, 15))

        # Name input
        name_frame = ctk.CTkFrame(main, fg_color="transparent")
        name_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            name_frame,
            text="Klasör Adı:",
            width=90,
            anchor="w"
        ).pack(side="left")

        name_entry = ctk.CTkEntry(
            name_frame,
            width=290,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        name_entry.pack(side="left", padx=10)
        name_entry.insert(0, folder.get('name', ''))
        name_entry.select_range(0, 'end')
        name_entry.focus_set()

        # Color selection
        color_frame = ctk.CTkFrame(main, fg_color="#2a2a3e", corner_radius=10)
        color_frame.pack(fill="x", pady=(0, 15), ipady=8)

        ctk.CTkLabel(
            color_frame,
            text="Klasör Rengi:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#aaaaaa"
        ).pack(pady=(5, 8))

        # Predefined color options
        colors_container = ctk.CTkFrame(color_frame, fg_color="transparent")
        colors_container.pack(pady=(0, 5))

        color_options = [
            {"name": "Altın", "bg": "#6b5b3d", "fg": "#ffcc00"},
            {"name": "Mavi", "bg": "#2d4a6a", "fg": "#5a9eff"},
            {"name": "Yeşil", "bg": "#2d5a2d", "fg": "#5aff5a"},
            {"name": "Mor", "bg": "#4a3a6a", "fg": "#aa7aff"},
            {"name": "Kırmızı", "bg": "#5a2d2d", "fg": "#ff6a6a"},
            {"name": "Turuncu", "bg": "#5a4a2d", "fg": "#ffaa4a"},
            {"name": "Pembe", "bg": "#5a2d4a", "fg": "#ff7aaa"},
            {"name": "Cyan", "bg": "#2d5a5a", "fg": "#5affff"},
        ]

        selected_color = tk.StringVar(value=folder.get('color_bg', "#6b5b3d"))
        selected_color_fg = tk.StringVar(value=folder.get('color_fg', "#ffcc00"))
        color_buttons = []

        # Create color buttons in 2 rows
        for i, color_opt in enumerate(color_options):
            if i % 4 == 0:
                row_frame = ctk.CTkFrame(colors_container, fg_color="transparent")
                row_frame.pack(pady=2)

            def make_color_select(bg, fg):
                def select():
                    selected_color.set(bg)
                    selected_color_fg.set(fg)
                    # Update all buttons
                    for btn_data in color_buttons:
                        if btn_data["bg"] == bg:
                            btn_data["btn"].configure(border_width=3, border_color=self.colors["accent"])
                        else:
                            btn_data["btn"].configure(border_width=1, border_color="#555555")
                return select

            is_selected = color_opt["bg"] == folder.get('color_bg', "#6b5b3d")

            btn = ctk.CTkButton(
                row_frame,
                text=color_opt["name"],
                width=98,
                height=30,
                corner_radius=8,
                fg_color=color_opt["bg"],
                hover_color=color_opt["bg"],
                text_color=color_opt["fg"],
                font=ctk.CTkFont(size=10, weight="bold"),
                border_width=3 if is_selected else 1,
                border_color=self.colors["accent"] if is_selected else "#555555",
                command=make_color_select(color_opt["bg"], color_opt["fg"])
            )
            btn.pack(side="left", padx=2)
            color_buttons.append({"btn": btn, "bg": color_opt["bg"]})

        # Buttons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(pady=(10, 0))

        def save():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showwarning("Uyarı", "Klasör adı boş olamaz!")
                return

            folder['name'] = new_name
            folder['color_bg'] = selected_color.get()
            folder['color_fg'] = selected_color_fg.get()
            self.refresh_group_list()
            self.save_config(silent=True)
            dialog.destroy()

        def cancel():
            dialog.destroy()

        ctk.CTkButton(
            btn_frame,
            text="✓ Kaydet",
            width=120,
            height=35,
            corner_radius=8,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            text_color="#000000",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=save
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="✗ İptal",
            width=120,
            height=35,
            corner_radius=8,
            fg_color=self.colors["bg_dark"],
            hover_color=self.colors["border"],
            font=ctk.CTkFont(size=12),
            command=cancel
        ).pack(side="left")

        # Enter to save
        name_entry.bind('<Return>', lambda e: save())
        name_entry.bind('<Escape>', lambda e: cancel())

    # ==================== DRAG & DROP ====================

    def _item_drag_start(self, event, item, parent_list):
        """Start dragging an item"""
        # Find the card widget
        widget = event.widget
        while widget and not hasattr(widget, '_item_data'):
            widget = widget.master
            if widget is None or widget == self.root:
                # Couldn't find card widget - silently return
                return

        if widget and hasattr(widget, '_item_data'):
            data = widget._item_data
            self.item_drag_data = {
                'active': True,
                'item': data['item'],
                'parent_list': data['parent_list'],
                'index': data['index'],
                'widget': widget,
                'start_y': event.y_root
            }

            # Create drag preview window
            self._create_drag_preview(event, data['item'])

    def _create_drag_preview(self, event, item):
        """Create a floating preview window that follows the cursor"""
        if self.drag_preview_window:
            self.drag_preview_window.destroy()

        # Create a toplevel window without decorations
        preview = ctk.CTkToplevel(self.root)
        preview.withdraw()  # Hide initially
        preview.overrideredirect(True)  # No window decorations
        preview.attributes('-topmost', True)  # Always on top
        preview.attributes('-alpha', 0.8)  # Semi-transparent

        # Create preview content based on item type
        if item.get('type') == 'folder':
            # Folder preview
            frame = ctk.CTkFrame(
                preview,
                fg_color="#3a3a4e",
                corner_radius=10,
                border_width=2,
                border_color=self.colors["accent"]
            )
            frame.pack(padx=0, pady=0)

            content = ctk.CTkFrame(frame, fg_color="transparent")
            content.pack(padx=10, pady=8)

            label = ctk.CTkLabel(
                content,
                text=f"📁  {item.get('name', 'Folder')}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#ffcc00"
            )
            label.pack(side="left")
        else:
            # Group preview
            frame = ctk.CTkFrame(
                preview,
                fg_color=self.colors["bg_dark"],
                corner_radius=10,
                border_width=2,
                border_color=self.colors["accent"]
            )
            frame.pack(padx=0, pady=0)

            content = ctk.CTkFrame(frame, fg_color="transparent")
            content.pack(padx=12, pady=10)

            label = ctk.CTkLabel(
                content,
                text=item.get('name', 'Group'),
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=self.colors["text"]
            )
            label.pack(side="left")

            key_badge = ctk.CTkLabel(
                content,
                text=item.get('toggle_key', '?').upper(),
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#ffffff",
                fg_color=self.colors["border"],
                corner_radius=4,
                padx=8,
                pady=4
            )
            key_badge.pack(side="right", padx=(10, 0))

        # Position at cursor
        preview.update_idletasks()
        preview.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        preview.deiconify()

        self.drag_preview_window = preview

    def _update_drag_preview_position(self, event):
        """Update preview window position to follow cursor"""
        if self.drag_preview_window and self.drag_preview_window.winfo_exists():
            self.drag_preview_window.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

    def _destroy_drag_preview(self):
        """Destroy the drag preview window"""
        if self.drag_preview_window:
            try:
                self.drag_preview_window.destroy()
            except:
                pass
            self.drag_preview_window = None

    def _item_drag_motion(self, event):
        """Handle drag motion - show drop indicator and update preview position"""
        if not self.item_drag_data['active']:
            return

        # Update preview position
        self._update_drag_preview_position(event)

        # Calculate target position based on mouse Y
        y_pos = event.y_root
        self._update_drop_indicator(y_pos)

    def _item_drag_end(self, event):
        """End dragging - perform the move"""
        if not self.item_drag_data['active']:
            return

        # Destroy drag preview
        self._destroy_drag_preview()

        # Hide drop indicator
        self._hide_drop_indicator()

        # Calculate drop position
        y_pos = event.y_root
        target_info = self._calculate_drop_position(y_pos)

        if target_info:
            dragged_item = self.item_drag_data['item']
            target_parent = target_info['parent_list']
            target_index = target_info['index']

            # Debug logging
            if self.global_settings.get("debug_enabled", False):
                self.add_log(f"DRAG: Moving '{dragged_item.get('name')}' to index {target_index} (parent has {len(target_parent)} items)", "DEBUG")

            # Remember which group is currently selected (by ID)
            selected_group_id = None
            if self.selected_group_index is not None:
                flat_groups = flatten_groups(self.groups)
                if self.selected_group_index < len(flat_groups):
                    selected_group_id = flat_groups[self.selected_group_index].get('id')

            # Perform the move using helper function
            insert_item_at(self.groups, dragged_item, target_parent, target_index)

            # Update selected_group_index to match the selected group's new position
            if selected_group_id is not None:
                flat_groups = flatten_groups(self.groups)
                for i, group in enumerate(flat_groups):
                    if group.get('id') == selected_group_id:
                        self.selected_group_index = i
                        break

            # If dropped into a folder, expand it
            if target_info.get('is_folder_drop'):
                folder = target_info.get('folder')
                if folder:
                    folder['expanded'] = True

            # Refresh and save (async save için)
            self.refresh_group_list()
            self.root.update_idletasks()  # UI'ı hemen güncelle
            self.root.after(100, lambda: self.save_config(silent=True))  # Save'i geciktirilmiş yap

        # Reset drag state
        self.item_drag_data = {
            'active': False,
            'item': None,
            'parent_list': None,
            'index': None,
            'widget': None,
            'start_y': 0
        }

    def _calculate_drop_position(self, y_pos):
        """Calculate where to drop the item based on mouse Y position"""
        # Get all card widgets recursively (klasör container'ları içindekiler dahil)
        def get_all_cards(widget):
            cards = []
            for child in widget.winfo_children():
                if hasattr(child, '_item_data'):
                    cards.append(child)
                # Recursive: container içindeki card'ları da al
                cards.extend(get_all_cards(child))
            return cards

        all_cards = get_all_cards(self.group_scroll)

        if not all_cards:
            return {'parent_list': self.groups, 'index': 0}

        # Find the card at mouse position
        for i, card in enumerate(all_cards):
            try:
                card_y = card.winfo_rooty()
                card_h = card.winfo_height()
                card_bottom = card_y + card_h

                # Check if mouse is over this card
                if card_y <= y_pos <= card_bottom:
                    data = card._item_data
                    item = data['item']

                    # If it's a folder, check if we should drop INSIDE it
                    if item.get('type') == 'folder':
                        # Calculate thirds: top third = before, middle third = inside, bottom third = after
                        third = card_h / 3

                        # CRITICAL: Gerçek index'i parent_list'ten al (render index değil!)
                        try:
                            real_index = data['parent_list'].index(item)
                        except (ValueError, AttributeError):
                            real_index = data['index']  # Fallback

                        if y_pos < card_y + third:
                            # Top third - drop BEFORE folder
                            return {
                                'parent_list': data['parent_list'],
                                'index': real_index
                            }
                        elif y_pos > card_y + 2 * third:
                            # Bottom third - drop AFTER folder
                            return {
                                'parent_list': data['parent_list'],
                                'index': real_index + 1
                            }
                        else:
                            # Middle third - drop INSIDE folder
                            folder_items = item.get('items', [])
                            return {
                                'parent_list': folder_items,
                                'index': len(folder_items),  # Add at end of folder
                                'is_folder_drop': True,
                                'folder': item
                            }
                    else:
                        # Regular group - check top/bottom half
                        # CRITICAL: Gerçek index'i parent_list'ten al
                        try:
                            real_index = data['parent_list'].index(item)
                        except (ValueError, AttributeError):
                            real_index = data['index']  # Fallback

                        card_mid = card_y + card_h / 2
                        if y_pos < card_mid:
                            # Drop before
                            return {
                                'parent_list': data['parent_list'],
                                'index': real_index
                            }
                        else:
                            # Drop after
                            return {
                                'parent_list': data['parent_list'],
                                'index': real_index + 1
                            }
            except:
                pass

        # Drop at end
        last_card = all_cards[-1]
        data = last_card._item_data
        item = data['item']
        # CRITICAL: Gerçek index'i parent_list'ten al
        try:
            real_index = data['parent_list'].index(item)
        except (ValueError, AttributeError):
            real_index = data['index']  # Fallback

        return {
            'parent_list': data['parent_list'],
            'index': real_index + 1
        }

    def _update_drop_indicator(self, y_pos):
        """Show visual drop indicator"""
        # Get target position
        target_info = self._calculate_drop_position(y_pos)

        # Check if target has changed (optimization: only update if target changed)
        target_folder_id = target_info.get('folder', {}).get('id') if target_info and target_info.get('is_folder_drop') else None
        last_target_folder_id = getattr(self, '_last_drop_target_folder_id', None)

        # If target hasn't changed, skip update (performance optimization)
        if target_folder_id == last_target_folder_id:
            return

        self._last_drop_target_folder_id = target_folder_id

        # Get all cards recursively (need to use same method as _calculate_drop_position)
        def get_all_cards(widget):
            cards = []
            for child in widget.winfo_children():
                if hasattr(child, '_item_data'):
                    cards.append(child)
                cards.extend(get_all_cards(child))
            return cards

        all_cards = get_all_cards(self.group_scroll)

        # Reset all folder cards to normal state
        for card in all_cards:
            try:
                data = card._item_data
                item = data['item']

                # Reset folder highlight
                if item.get('type') == 'folder':
                    # Use folder's custom color or default
                    folder_bg = item.get('color_bg', '#3a3a4e')
                    card.configure(fg_color=folder_bg)
            except:
                pass

        # Highlight target folder if dropping into one
        if target_folder_id:
            # Find the card for this folder and highlight it
            for card in all_cards:
                try:
                    data = card._item_data
                    if data['item'].get('id') == target_folder_id:
                        # Highlight the folder
                        card.configure(fg_color="#3a5a3e")  # Green-ish highlight
                        break
                except:
                    pass

    def _hide_drop_indicator(self):
        """Hide drop indicator"""
        if self.item_drop_indicator:
            try:
                self.item_drop_indicator.destroy()
            except:
                pass
            self.item_drop_indicator = None

        # Reset cached target folder ID
        self._last_drop_target_folder_id = None

    def _render_group(self, group, level, index, conflicting_keys, parent_list, parent_folder=None, parent_widget=None):
        """Render a group card"""
        if parent_widget is None:
            parent_widget = self.group_scroll

        # Find the actual index in the flat groups list for compatibility
        flat_groups = flatten_groups(self.groups)
        try:
            group_index = next(i for i, g in enumerate(flat_groups) if g.get('id') == group.get('id'))
        except StopIteration:
            group_index = index

        is_selected = group_index == self.selected_group_index
        is_enabled = group.get('enabled', True)
        has_conflict = is_enabled and group.get('toggle_key', '').lower() in conflicting_keys

        # Determine card color - öncelik sırası: conflict > selected > enabled > disabled
        if has_conflict:
            card_color = "#4a2020"  # KIRMIZI - en yüksek öncelik (conflict)
        elif is_selected:
            card_color = self.colors["accent"]  # CYAN - yüksek öncelik
        elif is_enabled:
            card_color = "#1a1a1a"  # KOYU SİYAH - orta öncelik
        else:
            card_color = self.colors["bg_secondary"]  # GRİ - disabled

        # Create group card
        card = ctk.CTkFrame(
            parent_widget,
            fg_color=card_color,
            corner_radius=10,
            height=60
        )
        # Eğer klasör içindeyse (parent_folder varsa), padding'i container'a göre ayarla
        if parent_folder is not None:
            card.pack(fill="x", pady=5, padx=5)  # Container içinde 5px padding (klasör header ile aynı)
        else:
            card.pack(fill="x", pady=4, padx=(4 + level * 20, 4))
        card.pack_propagate(False)

        # Store group index for selection
        card._group_index = group_index

        # Store metadata for drag & drop
        card._item_data = {
            'item': group,
            'parent_list': parent_list,
            'parent_folder': parent_folder,
            'index': index,
            'level': level
        }

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=10)

        # Drag handle
        drag_handle = ctk.CTkLabel(
            content,
            text="≡",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["text_secondary"],
            width=20,
            cursor="hand2"
        )
        drag_handle.pack(side="left", padx=(0, 8))

        # Toggle switch
        toggle_switch = ctk.CTkSwitch(
            content,
            text="",
            width=36,
            height=18,
            switch_width=36,
            switch_height=18,
            fg_color=self.colors["border"],
            progress_color=self.colors["success"],
            button_color="#ffffff",
            button_hover_color="#eeeeee"
        )
        toggle_switch.pack(side="left", padx=(0, 10))

        if is_enabled:
            toggle_switch.select()
        else:
            toggle_switch.deselect()

        toggle_switch.configure(command=lambda idx=group_index: self.toggle_group_enabled(idx))

        # Info frame
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)

        name_color = "#ffffff" if is_selected else (self.colors["text"] if is_enabled else self.colors["text_secondary"])
        name_label = ctk.CTkLabel(
            info_frame,
            text=group['name'],
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=name_color,
            anchor="w"
        )
        name_label.pack(anchor="w")

        spam_text = f"Spam: {group.get('spam_key', '-')}" if group.get('spam_enabled') else "Spam: Kapalı"
        spam_color = "#cccccc" if is_selected else self.colors["text_secondary"]
        spam_label = ctk.CTkLabel(
            info_frame,
            text=spam_text,
            font=ctk.CTkFont(size=11),
            text_color=spam_color,
            anchor="w"
        )
        spam_label.pack(anchor="w")

        # Key badge
        badge_bg = "#1a5f7a" if is_selected else self.colors["border"]
        badge_text_color = "#ffffff" if is_selected else self.colors["text_secondary"]
        key_badge = ctk.CTkLabel(
            content,
            text=group.get('toggle_key', '?').upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=badge_text_color,
            fg_color=badge_bg,
            corner_radius=4,
            padx=8,
            pady=4
        )
        key_badge.pack(side="right")

        # Store widget references for efficient updates
        card._name_label = name_label
        card._spam_label = spam_label
        card._key_badge = key_badge

        # Click handlers
        for widget in [card, content, info_frame, name_label, spam_label, key_badge]:
            widget.bind('<Button-1>', lambda e, idx=group_index: self.select_group(idx))

        # Drag & drop events
        drag_handle.bind('<Button-1>', lambda e, item=group, plist=parent_list: self._item_drag_start(e, item, plist))
        drag_handle.bind('<B1-Motion>', self._item_drag_motion)
        drag_handle.bind('<ButtonRelease-1>', self._item_drag_end)

    def _create_empty_group_card(self):
        """Create an empty group card template"""
        card = ctk.CTkFrame(
            self.group_scroll,
            fg_color=self.colors["bg_dark"],
            corner_radius=10,
            height=60
        )
        card.pack_propagate(False)
        card._group_index = None

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=10)
        card._content = content

        # Toggle switch
        toggle_switch = ctk.CTkSwitch(
            content,
            text="",
            width=36,
            height=18,
            switch_width=36,
            switch_height=18,
            fg_color=self.colors["border"],
            progress_color=self.colors["success"],
            button_color="#ffffff",
            button_hover_color="#eeeeee"
        )
        toggle_switch.pack(side="left", padx=(0, 10))
        card._toggle_switch = toggle_switch

        # Info frame
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)
        card._info_frame = info_frame

        name_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.colors["text"],
            anchor="w"
        )
        name_label.pack(anchor="w")
        card._name_label = name_label

        spam_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=self.colors["text_secondary"],
            anchor="w"
        )
        spam_label.pack(anchor="w")
        card._spam_label = spam_label

        # Key badge
        key_badge = ctk.CTkLabel(
            content,
            text="",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.colors["text_secondary"],
            fg_color=self.colors["border"],
            corner_radius=4,
            padx=8,
            pady=4
        )
        key_badge.pack(side="right")
        card._key_badge = key_badge

        return card

    def _update_group_card(self, card, index, group, conflicting_keys):
        """Update an existing group card with new data"""
        is_selected = index == self.selected_group_index
        is_enabled = group.get('enabled', True)
        has_conflict = is_enabled and group.get('toggle_key', '').lower() in conflicting_keys

        # Renk belirleme
        if is_selected:
            card_color = self.colors["accent"]
        elif has_conflict:
            card_color = "#4a2020"
        elif is_enabled:
            card_color = self.colors["bg_dark"]
        else:
            card_color = self.colors["bg_secondary"]

        card.configure(fg_color=card_color)
        card._group_index = index

        # Toggle switch güncelle
        card._toggle_switch.configure(command=lambda idx=index: self.toggle_group_enabled(idx))
        if is_enabled:
            card._toggle_switch.select()
        else:
            card._toggle_switch.deselect()

        # Name label güncelle
        name_color = "#ffffff" if is_selected else (self.colors["text"] if is_enabled else self.colors["text_secondary"])
        card._name_label.configure(text=group['name'], text_color=name_color)

        # Spam label güncelle
        spam_text = f"Spam: {group.get('spam_key', '-')}" if group.get('spam_enabled') else "Spam: Kapalı"
        spam_color = "#cccccc" if is_selected else self.colors["text_secondary"]
        card._spam_label.configure(text=spam_text, text_color=spam_color)

        # Key badge güncelle
        badge_bg = "#1a5f7a" if is_selected else self.colors["border"]
        badge_text_color = "#ffffff" if is_selected else self.colors["text_secondary"]
        card._key_badge.configure(
            text=group.get('toggle_key', '?').upper(),
            fg_color=badge_bg,
            text_color=badge_text_color
        )

        # Click handlers - tüm widget'lara bağla
        for widget in [card, card._content, card._info_frame, card._name_label, card._spam_label, card._key_badge]:
            widget.bind("<Button-1>", lambda e, idx=index: self.select_group(idx))

    def get_conflicting_keys(self):
        """Çakışan toggle key'leri bul (sadece aktif gruplar arasında)"""
        return get_conflicting_keys(self.groups)

    def check_missing_template_images(self):
        """Aktif gruplardaki eksik template görsellerini kontrol et"""
        return check_missing_template_images(self.groups, IMAGES_FOLDER)

    def get_selected_group(self):
        """Get the currently selected group from flat groups list"""
        if self.selected_group_index is None:
            return None
        flat_groups = flatten_groups(self.groups)
        if self.selected_group_index >= len(flat_groups):
            return None
        return flat_groups[self.selected_group_index]

    def get_selected_item(self):
        """Get the currently selected item (group or folder)"""
        # If a folder is selected, return it
        if self.selected_folder_id:
            folder = find_item_by_id(self.groups, self.selected_folder_id)
            if folder and folder.get('type') == 'folder':
                return folder

        # If a group is selected, return it
        group = self.get_selected_group()
        if group:
            return group

        return None

    def select_group(self, index):
        """Select a group - update selection state without full refresh"""
        if self.selected_group_index == index:
            return  # Zaten seçili, işlem yapma

        old_index = self.selected_group_index
        old_folder_id = self.selected_folder_id

        self.selected_group_index = index
        self.selected_template_index = None
        self.selected_folder_id = None  # Klasör seçimini clear et

        # Hızlı update: Sadece seçim renklerini güncelle, tam render yapma
        self._update_selection_colors(old_index, old_folder_id, index, None)
        self.update_group_details()
        self.refresh_template_list()

    def select_folder(self, folder_id):
        """Select a folder - update selection state without full refresh"""
        if self.selected_folder_id == folder_id:
            return  # Zaten seçili

        old_index = self.selected_group_index
        old_folder_id = self.selected_folder_id

        self.selected_folder_id = folder_id
        self.selected_group_index = None  # Grup seçimini clear et
        self.selected_template_index = None

        # Hızlı update: Sadece seçim renklerini güncelle
        self._update_selection_colors(old_index, old_folder_id, None, folder_id)
        self.update_group_details()
        self.refresh_template_list()

    def _update_selection_colors(self, old_group_index, old_folder_id, new_group_index, new_folder_id):
        """Hızlı seçim renk güncellemesi - sadece eski ve yeni seçili kartların renklerini değiştir"""
        # Eski grup seçimini kaldır
        if old_group_index is not None:
            self._update_group_card_selection(old_group_index, False)

        # Eski klasör seçimini kaldır
        if old_folder_id is not None:
            self._update_folder_card_selection(old_folder_id, False)

        # Yeni grup seçimini ekle
        if new_group_index is not None:
            self._update_group_card_selection(new_group_index, True)

        # Yeni klasör seçimini ekle
        if new_folder_id is not None:
            self._update_folder_card_selection(new_folder_id, True)

    def _update_folder_card_selection(self, folder_id, is_selected):
        """Sadece bir klasör kartının seçim durumunu güncelle"""
        if folder_id is None:
            return False

        # Tüm widget'ları recursive olarak tara
        def find_folder_card(widget):
            for child in widget.winfo_children():
                if hasattr(child, '_item_data'):
                    item_data = child._item_data
                    if item_data['item'].get('id') == folder_id and item_data['item'].get('type') == 'folder':
                        # Klasör kartını bulduk, rengini güncelle
                        folder = item_data['item']
                        folder_bg = folder.get('color_bg', '#3a3a4e')
                        card_color = self.colors["accent"] if is_selected else folder_bg
                        child.configure(fg_color=card_color)

                        # Label rengini güncelle
                        for label_child in child.winfo_children():
                            if hasattr(label_child, 'winfo_children'):
                                for inner in label_child.winfo_children():
                                    if isinstance(inner, ctk.CTkLabel) and '📁' in str(inner.cget('text')):
                                        folder_fg = folder.get('color_fg', '#ffcc00')
                                        text_color = "#ffffff" if is_selected else folder_fg
                                        inner.configure(text_color=text_color)
                        return True
                # Recursive search
                if find_folder_card(child):
                    return True
            return False

        return find_folder_card(self.group_scroll)

    def _update_group_card_selection(self, index, is_selected):
        """Update only the selection state of a specific group card. Returns True if card was found and updated."""
        flat_groups = flatten_groups(self.groups)
        if index is None or index >= len(flat_groups):
            return False

        # Kartı bul
        for card in self.group_scroll.winfo_children():
            if hasattr(card, '_group_index') and card._group_index == index:
                group = flat_groups[index]
                is_enabled = group.get('enabled', True)

                # Renk güncelle - 3 basit durum
                if is_selected:
                    card_color = self.colors["accent"]  # CYAN - en yüksek öncelik
                elif is_enabled:
                    card_color = "#1a1a1a"  # KOYU SİYAH - orta öncelik
                else:
                    card_color = self.colors["bg_secondary"]  # GRİ - disabled

                card.configure(fg_color=card_color)

                # Text renkleri güncelle
                name_color = "#ffffff" if is_selected else (self.colors["text"] if is_enabled else self.colors["text_secondary"])
                card._name_label.configure(text_color=name_color)

                spam_color = "#cccccc" if is_selected else self.colors["text_secondary"]
                card._spam_label.configure(text_color=spam_color)

                badge_bg = "#1a5f7a" if is_selected else self.colors["border"]
                badge_text_color = "#ffffff" if is_selected else self.colors["text_secondary"]
                card._key_badge.configure(fg_color=badge_bg, text_color=badge_text_color)
                return True

        return False  # Card not found

    def toggle_group_enabled(self, index):
        """Toggle group enabled/disabled - optimized to only update that card"""
        flat_groups = flatten_groups(self.groups)
        if index < len(flat_groups):
            group = flat_groups[index]
            current = group.get('enabled', True)
            group['enabled'] = not current
            status = "aktif" if not current else "pasif"
            self.add_log(f"Grup '{group['name']}' {status} yapıldı.", "INFO")

            # Sadece o grubun kartını güncelle (tam refresh yerine)
            is_selected = (self.selected_group_index == index)
            self._update_group_card_selection(index, is_selected)

            # Config'i async kaydet
            self.root.after(100, lambda: self.save_config(silent=True))

    def update_group_details(self):
        """Update the group details panel"""
        group = self.get_selected_group()
        if group is None:
            self.group_name_label.configure(text="Bir grup seçin...", text_color=self.colors["text_secondary"])
            self.group_name_container.configure(fg_color=self.colors["bg_dark"])
            self.group_info_label.configure(text="")
            self.group_notes_label.configure(text="")
            return

        # Highlight selected group with accent color
        self.group_name_container.configure(fg_color=self.colors["accent"])
        self.group_name_label.configure(text=f"📁 {group['name']}", text_color="#000000")

        spam_info = f"Spam: {group.get('spam_key', 'Yok')}" if group.get('spam_enabled') else "Spam: Kapalı"
        region = group.get('search_region', [0, 0, 100, 100])

        info = f"Toggle: {group.get('toggle_key', '?').upper()}  |  {spam_info}  |  Bölge: {region[0]},{region[1]}-{region[2]},{region[3]}"
        self.group_info_label.configure(text=info)

        # Notları göster
        notes = group.get('notes', '')
        if notes:
            self.group_notes_label.configure(text=f"Not: {notes}")
        else:
            self.group_notes_label.configure(text="")

    def refresh_template_list(self):
        """Refresh template list for selected group with widget reuse"""
        existing_cards = [w for w in self.template_scroll.winfo_children()
                         if isinstance(w, ctk.CTkFrame) and hasattr(w, '_template_index')]

        group = self.get_selected_group()
        if group is None:
            # Tüm kartları gizle ve pool'a taşı
            for card in existing_cards:
                card.pack_forget()
                self.template_card_pool.append(card)
            return
        templates = group.get('templates', [])
        needed = len(templates)

        # Drop indicator for templates (lazy create)
        if not hasattr(self, 'template_drop_indicator') or self.template_drop_indicator is None:
            self.template_drop_indicator = ctk.CTkFrame(
                self.template_scroll,
                fg_color=self.colors["accent"],
                height=3
            )

        # Fazla kartları pool'a taşı
        while len(existing_cards) > needed:
            card = existing_cards.pop()
            card.pack_forget()
            self.template_card_pool.append(card)

        # Eksik kartları oluştur veya pool'dan al
        while len(existing_cards) < needed:
            if self.template_card_pool:
                card = self.template_card_pool.pop()
            else:
                card = self._create_empty_template_card()
            existing_cards.append(card)

        # Tüm kartları güncelle
        for i, template in enumerate(templates):
            card = existing_cards[i]
            self._update_template_card(card, i, template)
            card.pack(fill="x", pady=4, padx=4)

    def _create_empty_template_card(self):
        """Create an empty template card template"""
        card = ctk.CTkFrame(
            self.template_scroll,
            fg_color=self.colors["bg_dark"],
            corner_radius=10,
            height=60
        )
        card.pack_propagate(False)
        card._template_index = None
        card.template_index = None  # For drag & drop compatibility

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=10)
        card._content = content

        # Drag handle
        drag_handle = ctk.CTkLabel(
            content,
            text="≡",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors["text_secondary"],
            width=20,
            cursor="fleur"
        )
        drag_handle.pack(side="left", padx=(0, 8))
        card._drag_handle = drag_handle

        # Color indicator
        color_indicator = ctk.CTkFrame(
            content,
            width=5,
            height=40,
            corner_radius=2,
            fg_color="#00ff88"
        )
        color_indicator.pack(side="left", padx=(0, 12))
        color_indicator.pack_propagate(False)
        card._color_indicator = color_indicator

        # Info frame
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)
        card._info_frame = info_frame

        name_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.colors["text"],
            anchor="w"
        )
        name_label.pack(anchor="w", pady=(0, 2))
        card._name_label = name_label

        key_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=self.colors["text_secondary"],
            anchor="w"
        )
        key_label.pack(anchor="w")
        card._key_label = key_label

        # Enable switch
        switch_frame = ctk.CTkFrame(content, fg_color="transparent", width=50)
        switch_frame.pack(side="right")
        switch_frame.pack_propagate(False)
        card._switch_frame = switch_frame

        switch = ctk.CTkSwitch(
            switch_frame,
            text="",
            width=42,
            height=22,
            switch_width=38,
            switch_height=18,
            fg_color=self.colors["border"],
            progress_color=self.colors["success"],
            button_color="#ffffff",
            button_hover_color="#e0e0e0"
        )
        switch.pack(expand=True)
        card._switch = switch

        return card

    def _update_template_card(self, card, index, template):
        """Update an existing template card with new data"""
        is_selected = index == self.selected_template_index
        is_enabled = template.get("enabled", True)

        # Card rengi
        if is_selected:
            card_color = self.colors["accent"]
        elif is_enabled:
            card_color = self.colors["bg_dark"]
        else:
            card_color = self.colors["bg_secondary"]

        card.configure(fg_color=card_color)
        card._template_index = index
        card.template_index = index  # For drag & drop

        # Drag handle bindings güncelle
        card._drag_handle.bind("<Button-1>", lambda e, c=card, idx=index: self.template_drag_start(e, c, idx))
        card._drag_handle.bind("<B1-Motion>", lambda e, c=card: self.template_drag_motion(e, c))
        card._drag_handle.bind("<ButtonRelease-1>", lambda e, c=card: self.template_drag_end(e, c))

        # Color indicator güncelle
        card._color_indicator.configure(fg_color=template.get("color", "#00ff88"))

        # Name label güncelle
        name_color = "#000000" if is_selected else (self.colors["text"] if is_enabled else self.colors["text_secondary"])
        card._name_label.configure(text=template['name'], text_color=name_color)

        # Key label güncelle
        key_color = "#000000" if is_selected else self.colors["text_secondary"]
        card._key_label.configure(text=template.get('key_combo', '?'), text_color=key_color)

        # Switch güncelle
        card._switch.configure(command=lambda idx=index: self._on_template_switch_toggle(idx, card._switch))
        if is_enabled:
            card._switch.select()
        else:
            card._switch.deselect()

        # Click handlers
        for widget in [card, card._content, card._info_frame, card._name_label, card._key_label]:
            widget.bind("<Button-1>", lambda e, idx=index: self.select_template(idx))

    def _on_template_switch_toggle(self, index, switch):
        """Handle template switch toggle - update only affected card"""
        group = self.get_selected_group()
        if group is not None:
            is_enabled = switch.get()
            group['templates'][index]['enabled'] = is_enabled
            # Sadece bu kartın rengini güncelle
            self._update_template_card_color(index, is_enabled)

    def _update_template_card_color(self, index, is_enabled):
        """Update only the color of a specific template card"""
        for card in self.template_scroll.winfo_children():
            if hasattr(card, '_template_index') and card._template_index == index:
                is_selected = index == self.selected_template_index
                if is_selected:
                    card_color = self.colors["accent"]
                elif is_enabled:
                    card_color = self.colors["bg_dark"]
                else:
                    card_color = self.colors["bg_secondary"]
                card.configure(fg_color=card_color)

                # Text renklerini de güncelle
                name_color = "#000000" if is_selected else (self.colors["text"] if is_enabled else self.colors["text_secondary"])
                card._name_label.configure(text_color=name_color)
                break

    def select_template(self, index):
        """Select a template - only update changed cards"""
        if self.selected_template_index == index:
            return  # Zaten seçili

        old_index = self.selected_template_index
        self.selected_template_index = index

        # Sadece eski ve yeni seçili kartları güncelle
        self._update_template_card_selection(old_index, False)
        self._update_template_card_selection(index, True)

    def _update_template_card_selection(self, index, is_selected):
        """Update only the selection state of a specific template card"""
        if index is None:
            return

        group = self.get_selected_group()
        if group is None:
            return

        templates = group.get('templates', [])
        if index >= len(templates):
            return

        template = templates[index]
        is_enabled = template.get("enabled", True)

        for card in self.template_scroll.winfo_children():
            if hasattr(card, '_template_index') and card._template_index == index:
                # Renk güncelle
                if is_selected:
                    card_color = self.colors["accent"]
                elif is_enabled:
                    card_color = self.colors["bg_dark"]
                else:
                    card_color = self.colors["bg_secondary"]

                card.configure(fg_color=card_color)

                # Text renkleri güncelle
                name_color = "#000000" if is_selected else (self.colors["text"] if is_enabled else self.colors["text_secondary"])
                card._name_label.configure(text_color=name_color)

                key_color = "#000000" if is_selected else self.colors["text_secondary"]
                card._key_label.configure(text_color=key_color)
                break

    # ==================== TEMPLATE DRAG & DROP ====================

    def template_drag_start(self, event, card, index):
        """Start dragging a template"""
        self.template_dragging = True
        self.template_drag_index = index
        self.template_drag_card = card
        self.template_drag_start_y = event.y_root

    def template_drag_motion(self, event, card):
        """Handle template drag motion"""
        if not getattr(self, 'template_dragging', False):
            return

        # Find drop position
        cards = [w for w in self.template_scroll.winfo_children()
                 if isinstance(w, ctk.CTkFrame) and hasattr(w, 'template_index')]

        drop_index = len(cards)
        for i, c in enumerate(cards):
            try:
                card_y = c.winfo_rooty()
                card_height = c.winfo_height()
                if event.y_root < card_y + card_height // 2:
                    drop_index = i
                    break
            except:
                pass

        self.template_drop_index = drop_index
        self.show_template_drop_indicator(drop_index, cards)

    def template_drag_end(self, event, card):
        """End template drag"""
        if not getattr(self, 'template_dragging', False):
            return

        self.template_dragging = False
        self.hide_template_drop_indicator()

        group = self.get_selected_group()
        if group is None:
            return

        from_index = self.template_drag_index
        to_index = getattr(self, 'template_drop_index', from_index)

        # Adjust index
        if to_index > from_index:
            to_index -= 1

        if from_index != to_index:
            templates = group['templates']
            template = templates.pop(from_index)
            templates.insert(to_index, template)
            self.add_log(f"Template sırası değişti: {from_index + 1} -> {to_index + 1}", "INFO")
            self.refresh_template_list()

    def show_template_drop_indicator(self, index, cards):
        """Show drop indicator at position"""
        try:
            if not hasattr(self, 'template_drop_indicator') or not self.template_drop_indicator.winfo_exists():
                return

            self.template_drop_indicator.pack_forget()

            if index < len(cards) and cards[index].winfo_exists():
                self.template_drop_indicator.pack(before=cards[index], fill="x", pady=2, padx=4)
            else:
                self.template_drop_indicator.pack(fill="x", pady=2, padx=4)
        except:
            pass

    def hide_template_drop_indicator(self):
        """Hide drop indicator"""
        try:
            if hasattr(self, 'template_drop_indicator') and self.template_drop_indicator.winfo_exists():
                self.template_drop_indicator.pack_forget()
        except:
            pass

    # ==================== CRUD OPERATIONS ====================

    def add_group(self):
        """Add a new group"""
        from ui.dialogs.group_dialogs import AddGroupDialog
        AddGroupDialog(self.root, self)

    def add_folder(self):
        """Add a new folder"""
        # Simple dialog for folder name
        dialog = ctk.CTkInputDialog(
            text="Klasör adı:",
            title="Yeni Klasör"
        )
        folder_name = dialog.get_input()

        if folder_name:
            new_folder = get_default_folder()
            new_folder['name'] = folder_name
            self.groups.append(new_folder)
            self.refresh_group_list()
            self.save_config(silent=True)

    def edit_group(self):
        """Edit selected group"""
        group = self.get_selected_group()
        if group is None:
            messagebox.showwarning("Uyarı", "Önce bir grup seçin!")
            return

        # For EditGroupDialog compatibility, we need to create a temporary wrapper
        # that makes the group accessible as if it were in a flat list
        from ui.dialogs.group_dialogs import EditGroupDialog

        # Create a temporary flat manager proxy
        class ManagerProxy:
            def __init__(self, real_manager, target_group):
                self.root = real_manager.root
                self.groups = [target_group]  # Single-item list for dialog compatibility
                self.colors = real_manager.colors
                self._real_manager = real_manager

            def refresh_group_list(self):
                self._real_manager.refresh_group_list()

            def update_group_details(self):
                self._real_manager.update_group_details()

        proxy = ManagerProxy(self, group)
        EditGroupDialog(self.root, proxy, 0)  # Always use index 0 for the proxy

    def delete_group(self):
        """Delete selected group"""
        group = self.get_selected_group()
        if group is None:
            messagebox.showwarning("Uyarı", "Önce bir grup seçin!")
            return

        if messagebox.askyesno("Onayla", f"'{group['name']}' grubu silinsin mi?\nTüm template'ler de silinecek!"):
            # Remove from nested structure using ID
            group_id = group.get('id')
            if group_id:
                remove_item_by_id(self.groups, group_id)
            self.selected_group_index = None
            self.refresh_group_list()
            self.update_group_details()
            self.refresh_template_list()

    def export_group(self):
        """Export selected group as text"""
        group = self.get_selected_group()
        if group is None:
            messagebox.showwarning("Uyarı", "Önce bir grup seçin!")
            return

        from ui.dialogs.preset_dialogs import ExportGroupDialog
        ExportGroupDialog(self.root, group, IMAGES_FOLDER)

    def import_group(self):
        """Import group from text"""
        from ui.dialogs.preset_dialogs import ImportGroupDialog
        ImportGroupDialog(self.root, self, IMAGES_FOLDER)

    def open_presets(self):
        """Open presets dialog"""
        from ui.dialogs.preset_dialogs import PresetDialog
        PresetDialog(self.root, self, IMAGES_FOLDER)

    def add_template(self):
        """Add template to selected group"""
        if self.selected_group_index is None:
            messagebox.showwarning("Uyarı", "Önce bir grup seçin!")
            return
        from ui.dialogs.template_dialogs import AddTemplateDialog
        AddTemplateDialog(self.root, self)

    def edit_template(self):
        """Edit selected template"""
        group = self.get_selected_group()
        if group is None or self.selected_template_index is None:
            messagebox.showwarning("Uyarı", "Önce bir template seçin!")
            return
        from ui.dialogs.template_dialogs import EditTemplateDialog
        template = group['templates'][self.selected_template_index]
        EditTemplateDialog(self.root, self, template, self.selected_template_index)

    def delete_template(self):
        """Delete selected template"""
        group = self.get_selected_group()
        if group is None or self.selected_template_index is None:
            messagebox.showwarning("Uyarı", "Önce bir template seçin!")
            return

        template = group['templates'][self.selected_template_index]
        if messagebox.askyesno("Onayla", f"'{template['name']}' silinsin mi?"):
            group['templates'].pop(self.selected_template_index)
            self.selected_template_index = None
            self.refresh_template_list()

    def duplicate_template(self):
        """Duplicate selected template"""
        group = self.get_selected_group()
        if group is None or self.selected_template_index is None:
            messagebox.showwarning("Uyarı", "Önce bir template seçin!")
            return

        original = group['templates'][self.selected_template_index]

        # Deep copy the template
        new_template = copy.deepcopy(original)

        # Generate new name
        base_name = original['name']
        counter = 1
        new_name = f"{base_name} (kopya)"

        # Check if name already exists
        existing_names = [t['name'] for t in group['templates']]
        while new_name in existing_names:
            counter += 1
            new_name = f"{base_name} (kopya {counter})"

        new_template['name'] = new_name

        # Generate new filename for the image
        if 'file' in new_template:
            original_file = original['file']
            base, ext = original_file.rsplit('.', 1) if '.' in original_file else (original_file, 'png')
            new_file = f"{base}_copy_{counter}.{ext}"

            # Copy the actual image file
            try:
                original_path = IMAGES_FOLDER / original_file
                new_path = IMAGES_FOLDER / new_file
                if original_path.exists():
                    import shutil
                    shutil.copy2(original_path, new_path)
                    new_template['file'] = new_file
            except Exception as e:
                print(f"Image copy error: {e}")

        # Insert after the original
        insert_index = self.selected_template_index + 1
        group['templates'].insert(insert_index, new_template)

        # Select the new template
        self.selected_template_index = insert_index
        self.refresh_template_list()

    # ==================== HOTKEY VALIDATION ====================

    def is_hotkey_used(self, key, exclude_group_id=None):
        """Check if a hotkey is already used by another group"""
        return is_hotkey_used(self.groups, key, exclude_group_id)

    # ==================== TEST MODE ====================

    def toggle_test_mode(self):
        """Toggle test mode on/off"""
        if self.test_mode_active:
            self.stop_test_mode()
        else:
            self.start_test_mode()

    def start_test_mode(self):
        """Start test mode - shows template matching status in overlay"""
        # Aktif grup kontrolü
        enabled_groups = [g for g in self.groups if g.get('enabled', True)]
        if not enabled_groups:
            messagebox.showwarning("Uyarı", "Test için en az bir aktif grup olmalı!")
            return

        # Template'i olan grup kontrolü
        groups_with_templates = [g for g in enabled_groups if g.get('templates')]
        if not groups_with_templates:
            messagebox.showwarning("Uyarı", "Test için en az bir template olmalı!")
            return

        self.test_mode_active = True
        self.test_mode_btn.configure(text="⏹  Durdur", fg_color=self.colors["danger"], hover_color="#cc3344")

        # Overlay penceresi oluştur
        self.create_test_overlay()

        # Test döngüsünü başlat
        self.run_test_cycle()

    def stop_test_mode(self):
        """Stop test mode"""
        self.test_mode_active = False
        self.test_mode_btn.configure(text="🧪  Test", fg_color=self.colors["warning"], hover_color="#e6a800")

        # Scheduled job'u iptal et
        if self.test_update_job:
            self.root.after_cancel(self.test_update_job)
            self.test_update_job = None

        # Overlay'i kapat
        if self.test_overlay:
            try:
                self.test_overlay.destroy()
            except:
                pass
            self.test_overlay = None

        self.test_labels.clear()

    def create_test_overlay(self):
        """Create test mode overlay window - FPS overlay style, click-through"""
        self.test_overlay = tk.Toplevel(self.root)
        self.test_overlay.title("")
        self.test_overlay.overrideredirect(True)  # Çerçevesiz
        self.test_overlay.attributes('-topmost', True)  # Her zaman üstte
        self.test_overlay.attributes('-alpha', 0.85)  # Hafif şeffaf
        self.test_overlay.configure(bg='#1a1a1a')

        # Ekranın sağ üstüne konumlandır (FPS overlay'ın altına)
        screen_width = self.root.winfo_screenwidth()
        self.test_overlay.geometry(f"+{screen_width - 280}+50")

        # Windows'ta click-through yapmak için
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.test_overlay.winfo_id())
            # WS_EX_LAYERED | WS_EX_TRANSPARENT
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20)  # WS_EX_LAYERED | WS_EX_TRANSPARENT
        except:
            pass

        # Ana container
        main_frame = tk.Frame(self.test_overlay, bg='#1a1a1a')
        main_frame.pack(padx=10, pady=8)

        # Header
        header_frame = tk.Frame(main_frame, bg='#1a1a1a')
        header_frame.pack(fill="x", pady=(0, 8))

        tk.Label(
            header_frame,
            text="🧪 TEST MODE",
            font=("Segoe UI", 11, "bold"),
            fg="#ffa502",
            bg='#1a1a1a'
        ).pack(side="left")

        # Aktif grupları ve template'lerini listele
        enabled_groups = [g for g in self.groups if g.get('enabled', True)]

        for group in enabled_groups:
            if not group.get('templates'):
                continue

            group_id = group['id']
            self.test_labels[group_id] = {}

            # Grup başlığı
            group_frame = tk.Frame(main_frame, bg='#242424', padx=8, pady=6)
            group_frame.pack(fill="x", pady=(0, 6))

            tk.Label(
                group_frame,
                text=f"📁 {group['name']}",
                font=("Segoe UI", 10, "bold"),
                fg="#00d4ff",
                bg='#242424'
            ).pack(anchor="w")

            # Template'leri listele
            for template in group.get('templates', []):
                if not template.get('enabled', True):
                    continue

                template_name = template['name']
                template_color = template.get('color', '#888888')
                threshold = template.get('threshold', 0.9)

                # Template satırı
                row = tk.Frame(group_frame, bg='#242424')
                row.pack(fill="x", pady=2)

                # Status indicator (canvas ile yuvarlak)
                canvas = tk.Canvas(row, width=12, height=12, bg='#242424', highlightthickness=0)
                canvas.pack(side="left", padx=(0, 6))
                indicator = canvas.create_oval(1, 1, 11, 11, fill="#ff4757", outline="")

                # Template adı
                tk.Label(
                    row,
                    text=template_name,
                    font=("Segoe UI", 9),
                    fg=template_color,
                    bg='#242424'
                ).pack(side="left")

                # Threshold
                tk.Label(
                    row,
                    text=f"({int(threshold * 100)}%)",
                    font=("Segoe UI", 8),
                    fg="#666666",
                    bg='#242424'
                ).pack(side="right", padx=(4, 0))

                # Match değeri
                match_label = tk.Label(
                    row,
                    text="0%",
                    font=("Segoe UI", 9),
                    fg="#888888",
                    bg='#242424',
                    width=4,
                    anchor="e"
                )
                match_label.pack(side="right")

                self.test_labels[group_id][template_name] = {
                    'canvas': canvas,
                    'indicator': indicator,
                    'match': match_label,
                    'threshold': threshold
                }

    def run_test_cycle(self):
        """Run one test cycle and schedule next"""
        if not self.test_mode_active:
            return

        try:
            import mss
            with mss.mss() as sct:
                enabled_groups = [g for g in self.groups if g.get('enabled', True)]

                for group in enabled_groups:
                    if not group.get('templates'):
                        continue

                    group_id = group['id']
                    if group_id not in self.test_labels:
                        continue

                    search_region = group.get('search_region', [0, 0, 100, 100])

                    # Ekran görüntüsü al
                    try:
                        monitor = {
                            "left": search_region[0],
                            "top": search_region[1],
                            "width": search_region[2] - search_region[0],
                            "height": search_region[3] - search_region[1]
                        }
                        sct_img = sct.grab(monitor)
                        screenshot = np.array(sct_img)[:, :, :3]
                        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
                    except Exception as e:
                        continue

                    # Her template için eşleşme kontrolü
                    for template in group.get('templates', []):
                        if not template.get('enabled', True):
                            continue

                        template_name = template['name']
                        if template_name not in self.test_labels[group_id]:
                            continue

                        threshold = template.get('threshold', 0.9)
                        template_file = template.get('file', '')

                        # Template yolunu bul (bot worker ile AYNI mantık: IMAGES_FOLDER / file)
                        template_path = IMAGES_FOLDER / template_file

                        match_val = 0.0
                        matched = False

                        if template_path.exists():
                            try:
                                # UTF-8 path desteği için numpy ile oku
                                template_img = cv2.imdecode(np.fromfile(str(template_path), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
                                if template_img is not None:
                                    # Template screenshot'tan büyükse atla
                                    if template_img.shape[0] > screenshot_gray.shape[0] or template_img.shape[1] > screenshot_gray.shape[1]:
                                        logger.warning(f"Template '{template_name}' arama bölgesinden büyük!")
                                        continue

                                    result = cv2.matchTemplate(screenshot_gray, template_img, cv2.TM_CCOEFF_NORMED)
                                    _, max_val, _, _ = cv2.minMaxLoc(result)
                                    match_val = max_val
                                    matched = max_val >= threshold
                            except Exception as e:
                                logger.error(f"Template match error for '{template_name}': {e}")
                        else:
                            logger.warning(f"Template dosyası bulunamadı: {template_path}")

                        # UI güncelle
                        labels = self.test_labels[group_id][template_name]
                        match_percent = int(match_val * 100)

                        if matched:
                            labels['canvas'].itemconfig(labels['indicator'], fill="#00ff88")
                            labels['match'].configure(text=f"{match_percent}%", fg="#00ff88")
                        else:
                            labels['canvas'].itemconfig(labels['indicator'], fill="#ff4757")
                            labels['match'].configure(text=f"{match_percent}%", fg="#888888")

        except Exception as e:
            logger.error(f"Test cycle error: {e}")

        # Sonraki cycle'ı zamanla (100ms = 10 FPS test)
        if self.test_mode_active:
            self.test_update_job = self.root.after(100, self.run_test_cycle)

    # ==================== BOT CONTROL ====================

    def toggle_all_bots(self):
        """Toggle all bot processes"""
        if not self.bot_active:
            self.start_all_bots()
        else:
            self.stop_all_bots()

    def start_all_bots(self):
        """Start all group processes"""
        # Flatten nested structure to get all groups
        all_groups = flatten_groups(self.groups)

        if not all_groups:
            messagebox.showwarning("Uyarı", "Hiç grup yok!")
            return

        # Aktif grup var mı kontrol et
        enabled_groups = [g for g in all_groups if g.get('enabled', True)]
        if not enabled_groups:
            messagebox.showwarning("Uyarı", "Hiç aktif grup yok! En az bir grubu aktif yapın.")
            return

        # Çakışan key kontrolü
        conflicting_keys = self.get_conflicting_keys()
        if conflicting_keys:
            keys_str = ", ".join(k.upper() for k in conflicting_keys)
            messagebox.showerror("Hata", f"Çakışan toggle key'ler var: {keys_str}\n\nAynı tuşu kullanan gruplardan birini pasif yapın veya tuşlarını değiştirin.")
            return

        # Eksik görsel kontrolü
        missing_images = self.check_missing_template_images()
        if missing_images:
            error_msg = "Eksik template görselleri var:\n\n"
            for group_name, templates in missing_images.items():
                error_msg += f"• {group_name}:\n"
                for t in templates:
                    error_msg += f"   - {t}\n"
            error_msg += "\nLütfen eksik görselleri düzeltin veya template'leri silin."
            messagebox.showerror("Hata", error_msg)
            return

        self.save_config(silent=True)

        # Create status queue
        self.status_queue = multiprocessing.Queue()

        # Start process for each enabled group
        for group in enabled_groups:

            group_id = group['id']

            # Create command queue and running flag
            cmd_queue = multiprocessing.Queue()
            running_flag = multiprocessing.Value('b', True)

            self.command_queues[group_id] = cmd_queue
            self.running_flags[group_id] = running_flag

            # Start process
            p = Process(target=group_worker, args=(group, cmd_queue, self.status_queue, running_flag))
            p.daemon = True
            p.start()
            self.processes[group_id] = p

            # CPU affinity ayarla
            self.apply_cpu_affinity(p.pid)

            # Create indicator
            self.create_indicator(group_id, len(self.indicator_windows))

        # Setup hotkeys - use enabled_groups (already filtered)
        keyboard.unhook_all()
        for group in enabled_groups:
            toggle_key = group.get('toggle_key')
            if toggle_key:
                group_id = group['id']
                keyboard.on_press_key(toggle_key, lambda e, gid=group_id: self.toggle_group(gid))

        self.bot_active = True
        self.update_ui_state()
        logger.info("All bots started")

    def stop_all_bots(self):
        """Stop all group processes"""
        # Stop all processes
        for group_id, flag in self.running_flags.items():
            flag.value = False

        # Wait and terminate
        for group_id, process in self.processes.items():
            process.join(timeout=1)
            if process.is_alive():
                process.terminate()

        # Cleanup
        self.processes.clear()
        self.command_queues.clear()
        self.running_flags.clear()

        # Remove indicators
        for group_id, (window, _) in self.indicator_windows.items():
            try:
                window.destroy()
            except:
                pass
        self.indicator_windows.clear()

        # FPS overlay'i kapat
        self.destroy_fps_overlay()

        # Unhook keyboard
        keyboard.unhook_all()

        self.bot_active = False
        self.update_ui_state()
        logger.info("All bots stopped")

    def toggle_group(self, group_id):
        """Toggle a specific group"""
        if group_id in self.command_queues:
            self.command_queues[group_id].put({'action': 'toggle'})

    def update_ui_state(self):
        """Update UI based on bot state"""
        if self.bot_active:
            self.start_stop_btn.configure(
                text="⏹  DURDUR",
                fg_color=self.colors["danger"],
                hover_color="#cc3a47",
                text_color="#ffffff"
            )
            self.status_indicator.configure(fg_color=self.colors["warning"])
            self.status_label.configure(text="Hazır", text_color=self.colors["warning"])

            # Bot aktifken düzenleme butonlarını devre dışı bırak
            self.add_group_btn.configure(state="disabled")
            self.edit_group_btn.configure(state="disabled")
            self.delete_group_btn.configure(state="disabled")
            self.add_template_btn.configure(state="disabled")
            self.edit_template_btn.configure(state="disabled")
            self.delete_template_btn.configure(state="disabled")
            self.duplicate_template_btn.configure(state="disabled")
        else:
            self.start_stop_btn.configure(
                text="▶  BAŞLAT",
                fg_color=self.colors["success"],
                hover_color="#00cc6e",
                text_color="#000000"
            )
            self.status_indicator.configure(fg_color=self.colors["danger"])
            self.status_label.configure(text="Durdu", text_color=self.colors["danger"])

            # Bot durduğunda düzenleme butonlarını aktif et
            self.add_group_btn.configure(state="normal")
            self.edit_group_btn.configure(state="normal")
            self.delete_group_btn.configure(state="normal")
            self.add_template_btn.configure(state="normal")
            self.edit_template_btn.configure(state="normal")
            self.delete_template_btn.configure(state="normal")
            self.duplicate_template_btn.configure(state="normal")

    # ==================== INDICATORS ====================

    def create_indicator(self, group_id, index):
        """Create indicator window for a group"""
        # Grup adını bul
        group_name = ""
        for g in self.groups:
            if g.get('id') == group_id:
                group_name = g.get('name', '')[:12]  # Max 12 karakter
                break

        window = tk.Toplevel(self.root)
        window.title("")

        # Daha büyük ve düzgün boyut
        width = 100
        height = 24
        spacing = 4
        y_pos = index * (height + spacing)

        window.geometry(f"{width}x{height}+4+{y_pos + 4}")
        window.overrideredirect(True)
        window.attributes('-topmost', True)
        window.resizable(False, False)

        # Frame ve label
        frame = tk.Frame(window, bg="#1a1a2e", highlightthickness=1, highlightbackground="#333")
        frame.place(x=0, y=0, width=width, height=height)

        # Status dot (sol taraf)
        dot = tk.Frame(frame, bg="#FF0000", width=10, height=10)
        dot.place(x=6, y=7)

        # Grup adı (sağ taraf)
        name_label = tk.Label(
            frame,
            text=group_name,
            bg="#1a1a2e",
            fg="#aaaaaa",
            font=("Segoe UI", 8)
        )
        name_label.place(x=22, y=2)

        self.indicator_windows[group_id] = (window, dot)

    def update_indicator(self, group_id, color):
        """Update indicator color"""
        if group_id in self.indicator_windows:
            _, dot = self.indicator_windows[group_id]
            try:
                dot.config(bg=color)
            except:
                pass

    def create_fps_overlay(self):
        """FPS overlay penceresini oluştur"""
        if self.fps_overlay is not None:
            return

        self.fps_overlay = tk.Toplevel(self.root)
        self.fps_overlay.title("")
        self.fps_overlay.overrideredirect(True)  # Çerçevesiz
        self.fps_overlay.attributes('-topmost', True)  # Her zaman üstte
        self.fps_overlay.attributes('-alpha', 0.85)  # Hafif şeffaf
        self.fps_overlay.configure(bg='#1a1a1a')

        # Ekranın sağ üstüne konumlandır
        screen_width = self.root.winfo_screenwidth()
        self.fps_overlay.geometry(f"+{screen_width - 220}+10")

        # FPS label container
        self.fps_label_frame = tk.Frame(self.fps_overlay, bg='#1a1a1a')
        self.fps_label_frame.pack(padx=8, pady=5)

        # Başlık
        tk.Label(
            self.fps_label_frame,
            text="⚡ FPS Monitor",
            font=('Consolas', 10, 'bold'),
            fg='#00d4ff',
            bg='#1a1a1a'
        ).pack(anchor='w')

        self.fps_labels = {}

    def update_fps_overlay(self):
        """FPS overlay'i güncelle"""
        if not self.fps_data:
            return

        # FPS overlay kapalıysa gösterme
        if not self.fps_overlay_var.get():
            return

        # Overlay yoksa oluştur
        if self.fps_overlay is None:
            self.create_fps_overlay()

        # Her grup için label güncelle
        for group_id, data in self.fps_data.items():
            fps = data['fps']
            name = data['name']

            # Renk belirle (FPS'e göre)
            if fps >= 60:
                color = '#00ff88'  # Yeşil
            elif fps >= 30:
                color = '#ffaa00'  # Turuncu
            else:
                color = '#ff4757'  # Kırmızı

            if group_id not in self.fps_labels:
                # Yeni label oluştur
                label = tk.Label(
                    self.fps_label_frame,
                    text=f"{fps:5.1f} FPS | {name}",
                    font=('Consolas', 11, 'bold'),
                    fg=color,
                    bg='#1a1a1a'
                )
                label.pack(anchor='w', pady=1)
                self.fps_labels[group_id] = label
            else:
                # Mevcut label'ı güncelle
                self.fps_labels[group_id].configure(
                    text=f"{fps:5.1f} FPS | {name}",
                    fg=color
                )

    def destroy_fps_overlay(self):
        """FPS overlay'i kapat"""
        if self.fps_overlay:
            try:
                self.fps_overlay.destroy()
            except:
                pass
            self.fps_overlay = None
            self.fps_labels = {}
            self.fps_data = {}

    def check_status_queue(self):
        """Check status queue for updates from worker processes"""
        if self.status_queue:
            try:
                while not self.status_queue.empty():
                    msg = self.status_queue.get_nowait()
                    group_id = msg.get('group_id')
                    msg_type = msg.get('type')

                    # Grup adını bul
                    group_name = "Unknown"
                    for g in self.groups:
                        if g.get('id') == group_id:
                            group_name = g.get('name', 'Unknown')
                            break

                    if msg_type == 'status':
                        status = msg.get('status')
                        if status == 'running':
                            self.update_indicator(group_id, '#00FF00')
                            if self.debug_var.get():
                                self.add_log(f"[{group_name}] Çalışıyor", "DEBUG")
                        elif status == 'stopped':
                            self.update_indicator(group_id, '#FF0000')
                            if self.debug_var.get():
                                self.add_log(f"[{group_name}] Durduruldu", "DEBUG")
                        elif status == 'ready':
                            self.update_indicator(group_id, '#FF0000')
                            self.add_log(f"[{group_name}] Hazır", "INFO")
                    elif msg_type == 'match':
                        color = msg.get('color', '#00FF00')
                        self.update_indicator(group_id, color)
                        if self.debug_var.get():
                            template_name = msg.get('template', '')
                            time_ms = msg.get('time_ms', 0)
                            self.add_log(f"[{group_name}] Eşleşme: {template_name} ({time_ms}ms)", "MATCH")
                    elif msg_type == 'fps':
                        fps = msg.get('fps', 0)
                        name = msg.get('name', 'Unknown')
                        self.fps_data[group_id] = {'fps': fps, 'name': name}
                        self.update_fps_overlay()
            except:
                pass

        self.root.after(50, self.check_status_queue)

    # ==================== CONFIG ====================

    def load_config(self):
        """Load config from JSON"""
        try:
            self.groups, self.global_settings, self.presets = core_load_config(CONFIG_FILE)
        except Exception as e:
            messagebox.showerror("Hata", f"Config yüklenemedi: {e}")
            self.groups = [get_default_group()]
            self.global_settings = {"debug_enabled": False, "fps_overlay_enabled": True, "cpu_cores": 0}
            self.presets = []

    def add_log(self, message, level="INFO"):
        """Log konsoluna mesaj ekle"""
        if not hasattr(self, 'log_text'):
            return

        timestamp = time.strftime("%H:%M:%S")

        # Renk kodları
        colors = {
            "INFO": "#00ff88",
            "DEBUG": "#00d4ff",
            "WARN": "#ffaa00",
            "ERROR": "#ff4757",
            "MATCH": "#ff00ff"
        }

        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] [{level}] {message}\n")
        self.log_text.see("end")  # Otomatik scroll
        self.log_text.configure(state="disabled")

    def clear_log(self):
        """Log konsolunu temizle"""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.add_log("Log temizlendi.")

    def toggle_debug_mode(self):
        """Debug modunu aç/kapa"""
        if self.debug_var.get():
            self.add_log("Debug modu açıldı.", "DEBUG")
        else:
            self.add_log("Debug modu kapatıldı.", "INFO")

    def toggle_fps_overlay(self):
        """FPS overlay'i aç/kapa"""
        if self.fps_overlay_var.get():
            self.add_log("FPS overlay açıldı.", "INFO")
            if self.bot_active:
                self.create_fps_overlay()
        else:
            self.add_log("FPS overlay kapatıldı.", "INFO")
            self.destroy_fps_overlay()

    def apply_cpu_affinity(self, pid):
        """Process'e CPU affinity uygula"""
        try:
            import psutil

            # Toplam çekirdek sayısı
            total_cores = psutil.cpu_count(logical=True)
            if total_cores is None or total_cores < 1:
                return

            # Kullanılacak çekirdek sayısını al
            cpu_cores = self.global_settings.get("cpu_cores", 0)

            # 0 veya max = sınırsız
            if cpu_cores == 0 or cpu_cores >= total_cores:
                return  # Sınırsız, bir şey yapma

            # İlk N çekirdeği kullan
            affinity_mask = list(range(cpu_cores))

            # Process'e affinity uygula
            proc = psutil.Process(pid)
            proc.cpu_affinity(affinity_mask)

            logger.info(f"CPU affinity set for PID {pid}: {cpu_cores}/{total_cores} cores")
        except ImportError:
            logger.warning("psutil not installed, CPU affinity not applied")
        except Exception as e:
            logger.error(f"Failed to set CPU affinity: {e}")

    def on_cpu_cores_change(self, value):
        """CPU çekirdek sayısı değiştiğinde çağrılır"""
        cores = int(value)
        self.global_settings["cpu_cores"] = cores

        # Etiketi güncelle
        if cores == self.total_cpu_cores:
            self.cpu_cores_label.configure(text="Sınırsız")
        else:
            self.cpu_cores_label.configure(text=f"{cores}/{self.total_cpu_cores}")

    def save_config(self, silent=False):
        """Save config to JSON"""
        try:
            self.global_settings["debug_enabled"] = self.debug_var.get()
            self.global_settings["fps_overlay_enabled"] = self.fps_overlay_var.get()
            # CPU çekirdek sayısını kaydet
            if hasattr(self, 'cpu_cores_slider'):
                self.global_settings["cpu_cores"] = int(self.cpu_cores_slider.get())

            success = core_save_config(
                CONFIG_FILE,
                self.groups,
                self.global_settings,
                getattr(self, 'presets', [])
            )

            if success and not silent:
                messagebox.showinfo("Başarılı", "Config kaydedildi!")
            elif not success:
                messagebox.showerror("Hata", "Config kaydedilemedi!")
        except Exception as e:
            messagebox.showerror("Hata", f"Config kaydedilemedi: {e}")

    def check_for_updates(self):
        """Arka planda güncelleme kontrolü yap"""
        from ui.dialogs.update_dialog import show_update_dialog_if_available
        show_update_dialog_if_available(self.root, check_async=True)

    def on_close(self):
        """Handle window close"""
        if self.bot_active:
            self.stop_all_bots()
        self.save_config(silent=True)  # Auto-save on close
        self.root.quit()

def main():
    # Required for Windows multiprocessing
    multiprocessing.freeze_support()

    root = ctk.CTk()
    app = ConfigManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
