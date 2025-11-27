"""
Template Configuration Manager v3
Groups System with Multiprocessing
"""

import customtkinter as ctk
from tkinter import messagebox, colorchooser
import tkinter as tk
import json
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageTk, ImageGrab
import keyboard
import time
import multiprocessing
from multiprocessing import Process, Queue, Value
import logging
import uuid
import mss

# CustomTkinter ayarları
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Paths
CONFIG_FILE = Path(__file__).parent / "config_v3.json"
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


# ==================== WORKER PROCESS FUNCTION ====================

def group_worker(group_data, command_queue, status_queue, running_flag):
    """
    Worker process for each group.
    Runs independently and listens for commands.
    """
    group_id = group_data['id']
    group_name = group_data['name']

    # Load templates (grayscale for faster matching)
    loaded_templates = []
    for template in group_data.get('templates', []):
        if not template.get('enabled', True):
            continue
        template_path = IMAGES_FOLDER / template['file']
        if template_path.exists():
            img = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
            if img is not None:
                # Grayscale'e çevir (3x daha hızlı matching)
                img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                loaded_templates.append({
                    'name': template['name'],
                    'image': img_gray,
                    'threshold': template['threshold'],
                    'key_combo': template.get('key_combo', ''),
                    'color': template.get('color', '#00ff88'),
                    'timing': template.get('timing', {"pre_delay": 1, "hold_time": 1, "post_delay": 1}),
                    'use_macro': template.get('use_macro', False),
                    'macro': template.get('macro', [])
                })

    search_running = False
    last_spam_time = 0

    # Settings
    spam_enabled = group_data.get('spam_enabled', False)
    spam_key = group_data.get('spam_key', None)
    spam_timing = group_data.get('spam_timing', {"pre_delay": 1, "hold_time": 1, "post_delay": 1})
    spam_interval = group_data.get('spam_key_interval', 0.025)
    search_region = group_data.get('search_region', [0, 0, 100, 100])

    def press_key_with_timing(key, timing):
        """Press a key with timing"""
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

    def press_key_combo(key_combo, timing):
        """Press key combination with timing"""
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

        for mod in modifiers:
            keyboard.press(mod)

        for key in regular_keys:
            keyboard.press(key)
            if hold_time > 0:
                time.sleep(hold_time)
            keyboard.release(key)

        for mod in reversed(modifiers):
            keyboard.release(mod)

        if post_delay > 0:
            time.sleep(post_delay)

    def execute_macro(macro_list):
        """Execute a macro sequence (Logitech G Hub style)"""
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

    def press_spam_key():
        """Press spam key"""
        nonlocal last_spam_time
        if not spam_enabled or not spam_key:
            return

        current_time = time.perf_counter()
        if current_time - last_spam_time >= spam_interval:
            press_key_with_timing(spam_key, spam_timing)
            last_spam_time = current_time

    def process_frame(sct):
        """Process single frame"""
        nonlocal last_spam_time

        if not loaded_templates:
            press_spam_key()
            return

        # Frame süresini ölç
        frame_start = time.perf_counter()

        try:
            # mss ile ekran yakalama (PIL'den ~5x daha hızlı)
            monitor = {
                "left": search_region[0],
                "top": search_region[1],
                "width": search_region[2] - search_region[0],
                "height": search_region[3] - search_region[1]
            }
            sct_img = sct.grab(monitor)
            # Direkt grayscale'e çevir (daha hızlı)
            screenshot = np.array(sct_img)[:, :, :3]  # BGRA -> BGR (alpha kaldır)
            screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        except Exception as e:
            return

        found_match = None

        for data in loaded_templates:
            try:
                result = cv2.matchTemplate(screenshot_gray, data['image'], cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)

                if max_val >= data['threshold']:
                    found_match = data
                    break
            except:
                pass

        # Frame süresini hesapla
        frame_time_ms = (time.perf_counter() - frame_start) * 1000

        if found_match:
            # Send color update to main process
            status_queue.put({
                'group_id': group_id,
                'type': 'match',
                'color': found_match['color'],
                'template': found_match['name'],
                'time_ms': round(frame_time_ms, 2)
            })

            # Makro modu veya basit mod
            if found_match.get('use_macro') and found_match.get('macro'):
                execute_macro(found_match['macro'])
            else:
                press_key_combo(found_match['key_combo'], found_match.get('timing', {}))

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

    # mss instance oluştur (worker başına bir tane)
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
                        # FPS reset
                        frame_count = 0
                        fps_start_time = time.perf_counter()
                    elif cmd.get('action') == 'stop':
                        search_running = False
                        status_queue.put({
                            'group_id': group_id,
                            'type': 'status',
                            'status': 'stopped'
                        })
            except:
                pass

            # Process frame if running
            if search_running:
                try:
                    process_frame(sct)
                    frame_count += 1
                except Exception as e:
                    logger.error(f"[{group_name}] Error: {e}")

                # Her 500ms'de bir FPS raporu gönder
                current_time = time.perf_counter()
                elapsed = current_time - fps_start_time

                if current_time - last_fps_report >= 0.5:
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    status_queue.put({
                        'group_id': group_id,
                        'type': 'fps',
                        'fps': round(fps, 1),
                        'name': group_name
                    })
                    last_fps_report = current_time

                    # Her 5 saniyede FPS sayacını resetle (overflow önlemek için)
                    if elapsed >= 5.0:
                        frame_count = 0
                        fps_start_time = current_time
            else:
                # Sadece beklerken sleep yap (CPU kullanımını düşürmek için)
                time.sleep(0.01)

    logger.info(f"[{group_name}] Worker stopped")


# ==================== MAIN APPLICATION ====================

class ConfigManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Template Configuration Manager v3 - Groups")
        self.root.geometry("1100x800")
        self.root.minsize(950, 700)

        # Renk paleti
        self.colors = {
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

        # Groups data
        self.groups = []
        self.global_settings = {
            "debug_enabled": False
        }

        # Process management
        self.processes = {}  # group_id -> Process
        self.command_queues = {}  # group_id -> Queue
        self.status_queue = None
        self.running_flags = {}  # group_id -> Value
        self.bot_active = False

        # UI state
        self.selected_group_index = None
        self.selected_template_index = None

        # Indicator windows
        self.indicator_windows = {}  # group_id -> (window, label)

        # FPS tracking
        self.fps_data = {}  # group_id -> {'fps': 0, 'name': ''}
        self.fps_overlay = None
        self.fps_labels = {}
        self.fps_label_frame = None

        # Load existing config
        self.load_config()

        # Build UI
        self.build_ui()

        # Start status monitor
        self.root.after(100, self.check_status_queue)

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
            text="v3.0 Groups",
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
            corner_radius=15
        )
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(15, 10))

        self.tabview.add("📁 Groups")
        self.tabview.add("⚙️ Genel Ayarlar")

        # ==================== GROUPS TAB ====================
        self.build_groups_tab()

        # ==================== SETTINGS TAB ====================
        self.build_settings_tab()

        # ==================== BOTTOM BAR ====================
        self.build_bottom_bar()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_groups_tab(self):
        """Build the groups tab"""
        groups_tab = self.tabview.tab("📁 Groups")

        # Main container
        main_container = ctk.CTkFrame(groups_tab, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Left panel - Group list
        left_panel = ctk.CTkFrame(main_container, fg_color=self.colors["bg_secondary"], corner_radius=12, width=280)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        left_panel.pack_propagate(False)

        # Group list header
        ctk.CTkLabel(
            left_panel,
            text="📁 Gruplar",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", padx=15, pady=(15, 10))

        # Group list
        self.group_scroll = ctk.CTkScrollableFrame(
            left_panel,
            fg_color="transparent",
            scrollbar_button_color=self.colors["accent"],
            scrollbar_button_hover_color=self.colors["accent_hover"]
        )
        self.group_scroll.pack(fill="both", expand=True, padx=8, pady=5)

        # Group buttons
        group_btn_frame = ctk.CTkFrame(left_panel, fg_color="transparent", height=50)
        group_btn_frame.pack(fill="x", padx=15, pady=12)

        ctk.CTkButton(
            group_btn_frame,
            text="+ Yeni",
            width=75,
            height=32,
            corner_radius=8,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="center",
            command=self.add_group
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            group_btn_frame,
            text="✏️",
            width=40,
            height=32,
            corner_radius=8,
            fg_color=self.colors["bg_dark"],
            hover_color=self.colors["border"],
            font=ctk.CTkFont(size=14),
            anchor="center",
            command=self.edit_group
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            group_btn_frame,
            text="🗑️",
            width=40,
            height=32,
            corner_radius=8,
            fg_color=self.colors["danger"],
            hover_color="#cc3a47",
            font=ctk.CTkFont(size=14),
            anchor="center",
            command=self.delete_group
        ).pack(side="left")

        # Right panel - Group details
        right_panel = ctk.CTkFrame(main_container, fg_color="transparent")
        right_panel.pack(side="right", fill="both", expand=True)

        # Group details card
        self.group_details_frame = ctk.CTkFrame(right_panel, fg_color=self.colors["bg_secondary"], corner_radius=12)
        self.group_details_frame.pack(fill="x", pady=(0, 10))

        self.group_details_content = ctk.CTkFrame(self.group_details_frame, fg_color="transparent")
        self.group_details_content.pack(fill="x", padx=20, pady=15)

        self.group_name_label = ctk.CTkLabel(
            self.group_details_content,
            text="Bir grup seçin...",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors["text"]
        )
        self.group_name_label.pack(anchor="w")

        self.group_info_label = ctk.CTkLabel(
            self.group_details_content,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text_secondary"]
        )
        self.group_info_label.pack(anchor="w", pady=(5, 0))

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

        ctk.CTkButton(
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
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            template_btn_frame,
            text="✏️",
            width=35,
            height=28,
            corner_radius=6,
            fg_color=self.colors["bg_dark"],
            hover_color=self.colors["border"],
            font=ctk.CTkFont(size=14),
            anchor="center",
            command=self.edit_template
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            template_btn_frame,
            text="🗑️",
            width=35,
            height=28,
            corner_radius=6,
            fg_color=self.colors["danger"],
            hover_color="#cc3a47",
            font=ctk.CTkFont(size=14),
            anchor="center",
            command=self.delete_template
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            template_btn_frame,
            text="📋",
            width=35,
            height=28,
            corner_radius=6,
            fg_color="#5a4a27",
            hover_color="#7a6a47",
            font=ctk.CTkFont(size=14),
            anchor="center",
            command=self.duplicate_template
        ).pack(side="left")

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
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.toggle_all_bots
        )
        self.start_stop_btn.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            left_controls,
            text="💾 Kaydet",
            width=100,
            height=45,
            corner_radius=10,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
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
        """Refresh the group list"""
        for widget in self.group_scroll.winfo_children():
            widget.destroy()

        for i, group in enumerate(self.groups):
            self.create_group_card(i, group)

    def create_group_card(self, index, group):
        """Create a group card"""
        is_selected = index == self.selected_group_index
        is_enabled = group.get('enabled', True)

        card = ctk.CTkFrame(
            self.group_scroll,
            fg_color=self.colors["accent"] if is_selected else (
                self.colors["bg_dark"] if is_enabled else self.colors["bg_secondary"]
            ),
            corner_radius=10,
            height=60
        )
        card.pack(fill="x", pady=4, padx=4)
        card.pack_propagate(False)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=10)

        # Status indicator (yeşil/kırmızı nokta)
        status_color = "#00ff88" if is_enabled else "#ff4444"
        status_indicator = ctk.CTkFrame(
            content,
            width=8,
            height=8,
            corner_radius=4,
            fg_color=status_color
        )
        status_indicator.pack(side="left", padx=(0, 10))
        status_indicator.pack_propagate(False)

        # Info frame
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)

        # Group name - seçili durumda beyaz, değilse normal
        name_color = "#ffffff" if is_selected else (self.colors["text"] if is_enabled else self.colors["text_secondary"])
        name_label = ctk.CTkLabel(
            info_frame,
            text=group['name'],
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=name_color,
            anchor="w"
        )
        name_label.pack(anchor="w")

        # Spam info - küçük yazı
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

        # Toggle key badge - sağda, kontrastlı
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

        # Click handlers
        for widget in [card, content, info_frame, name_label, spam_label, key_badge, status_indicator]:
            widget.bind("<Button-1>", lambda e, idx=index: self.select_group(idx))

    def select_group(self, index):
        """Select a group"""
        self.selected_group_index = index
        self.selected_template_index = None
        self.refresh_group_list()
        self.update_group_details()
        self.refresh_template_list()

    def update_group_details(self):
        """Update the group details panel"""
        if self.selected_group_index is None or self.selected_group_index >= len(self.groups):
            self.group_name_label.configure(text="Bir grup seçin...")
            self.group_info_label.configure(text="")
            return

        group = self.groups[self.selected_group_index]
        self.group_name_label.configure(text=f"📁 {group['name']}")

        spam_info = f"Spam: {group.get('spam_key', 'Yok')}" if group.get('spam_enabled') else "Spam: Kapalı"
        region = group.get('search_region', [0, 0, 100, 100])

        info = f"Toggle: {group.get('toggle_key', '?').upper()}  |  {spam_info}  |  Bölge: {region[0]},{region[1]}-{region[2]},{region[3]}"
        self.group_info_label.configure(text=info)

    def refresh_template_list(self):
        """Refresh template list for selected group"""
        for widget in self.template_scroll.winfo_children():
            widget.destroy()

        if self.selected_group_index is None or self.selected_group_index >= len(self.groups):
            return

        group = self.groups[self.selected_group_index]
        templates = group.get('templates', [])

        for i, template in enumerate(templates):
            self.create_template_card(i, template)

    def create_template_card(self, index, template):
        """Create a template card"""
        is_selected = index == self.selected_template_index
        is_enabled = template.get("enabled", True)

        card = ctk.CTkFrame(
            self.template_scroll,
            fg_color=self.colors["accent"] if is_selected else (
                self.colors["bg_dark"] if is_enabled else self.colors["bg_secondary"]
            ),
            corner_radius=10,
            height=60
        )
        card.pack(fill="x", pady=4, padx=4)
        card.pack_propagate(False)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=10)

        # Color indicator - daha belirgin
        color_indicator = ctk.CTkFrame(
            content,
            width=5,
            height=40,
            corner_radius=2,
            fg_color=template.get("color", "#00ff88")
        )
        color_indicator.pack(side="left", padx=(0, 12))
        color_indicator.pack_propagate(False)

        # Info - ortalı düzen
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)

        name_color = "#000000" if is_selected else (self.colors["text"] if is_enabled else self.colors["text_secondary"])

        # Template adı
        name_label = ctk.CTkLabel(
            info_frame,
            text=template['name'],
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=name_color,
            anchor="w"
        )
        name_label.pack(anchor="w", pady=(0, 2))

        # Tuş bilgisi - daha düzgün
        key_text = template.get('key_combo', '?')
        key_label = ctk.CTkLabel(
            info_frame,
            text=key_text,
            font=ctk.CTkFont(size=11),
            text_color="#000000" if is_selected else self.colors["text_secondary"],
            anchor="w"
        )
        key_label.pack(anchor="w")

        # Enable switch - sağda sabit
        switch_frame = ctk.CTkFrame(content, fg_color="transparent", width=50)
        switch_frame.pack(side="right")
        switch_frame.pack_propagate(False)

        enable_var = ctk.BooleanVar(value=is_enabled)
        switch = ctk.CTkSwitch(
            switch_frame,
            text="",
            variable=enable_var,
            width=42,
            height=22,
            switch_width=38,
            switch_height=18,
            fg_color=self.colors["border"],
            progress_color=self.colors["success"],
            button_color="#ffffff",
            button_hover_color="#e0e0e0",
            command=lambda idx=index, var=enable_var: self.toggle_template_enabled(idx, var)
        )
        switch.pack(expand=True)

        # Click handler
        for widget in [card, content, info_frame, name_label, key_label]:
            widget.bind("<Button-1>", lambda e, idx=index: self.select_template(idx))

    def select_template(self, index):
        """Select a template"""
        self.selected_template_index = index
        self.refresh_template_list()

    def toggle_template_enabled(self, index, var):
        """Toggle template enabled state"""
        if self.selected_group_index is not None:
            self.groups[self.selected_group_index]['templates'][index]['enabled'] = var.get()
            self.refresh_template_list()

    # ==================== CRUD OPERATIONS ====================

    def add_group(self):
        """Add a new group"""
        AddGroupDialog(self.root, self)

    def edit_group(self):
        """Edit selected group"""
        if self.selected_group_index is None:
            messagebox.showwarning("Uyarı", "Önce bir grup seçin!")
            return
        EditGroupDialog(self.root, self, self.selected_group_index)

    def delete_group(self):
        """Delete selected group"""
        if self.selected_group_index is None:
            messagebox.showwarning("Uyarı", "Önce bir grup seçin!")
            return

        group = self.groups[self.selected_group_index]
        if messagebox.askyesno("Onayla", f"'{group['name']}' grubu silinsin mi?\nTüm template'ler de silinecek!"):
            self.groups.pop(self.selected_group_index)
            self.selected_group_index = None
            self.refresh_group_list()
            self.update_group_details()
            self.refresh_template_list()

    def add_template(self):
        """Add template to selected group"""
        if self.selected_group_index is None:
            messagebox.showwarning("Uyarı", "Önce bir grup seçin!")
            return
        AddTemplateDialog(self.root, self)

    def edit_template(self):
        """Edit selected template"""
        if self.selected_group_index is None or self.selected_template_index is None:
            messagebox.showwarning("Uyarı", "Önce bir template seçin!")
            return
        template = self.groups[self.selected_group_index]['templates'][self.selected_template_index]
        EditTemplateDialog(self.root, self, template, self.selected_template_index)

    def delete_template(self):
        """Delete selected template"""
        if self.selected_group_index is None or self.selected_template_index is None:
            messagebox.showwarning("Uyarı", "Önce bir template seçin!")
            return

        template = self.groups[self.selected_group_index]['templates'][self.selected_template_index]
        if messagebox.askyesno("Onayla", f"'{template['name']}' silinsin mi?"):
            self.groups[self.selected_group_index]['templates'].pop(self.selected_template_index)
            self.selected_template_index = None
            self.refresh_template_list()

    def duplicate_template(self):
        """Duplicate selected template"""
        if self.selected_group_index is None or self.selected_template_index is None:
            messagebox.showwarning("Uyarı", "Önce bir template seçin!")
            return

        original = self.groups[self.selected_group_index]['templates'][self.selected_template_index]

        # Deep copy the template
        import copy
        new_template = copy.deepcopy(original)

        # Generate new name
        base_name = original['name']
        counter = 1
        new_name = f"{base_name} (kopya)"

        # Check if name already exists
        existing_names = [t['name'] for t in self.groups[self.selected_group_index]['templates']]
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
        self.groups[self.selected_group_index]['templates'].insert(insert_index, new_template)

        # Select the new template
        self.selected_template_index = insert_index
        self.refresh_template_list()

    # ==================== HOTKEY VALIDATION ====================

    def is_hotkey_used(self, key, exclude_group_id=None):
        """Check if a hotkey is already used by another group"""
        for group in self.groups:
            if exclude_group_id and group.get('id') == exclude_group_id:
                continue
            if group.get('toggle_key', '').lower() == key.lower():
                return group['name']
        return None

    # ==================== BOT CONTROL ====================

    def toggle_all_bots(self):
        """Toggle all bot processes"""
        if not self.bot_active:
            self.start_all_bots()
        else:
            self.stop_all_bots()

    def start_all_bots(self):
        """Start all group processes"""
        if not self.groups:
            messagebox.showwarning("Uyarı", "Hiç grup yok!")
            return

        self.save_config()

        # Create status queue
        self.status_queue = multiprocessing.Queue()

        # Start process for each group
        for group in self.groups:
            if not group.get('enabled', True):
                continue

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

            # Create indicator
            self.create_indicator(group_id, len(self.indicator_windows))

        # Setup hotkeys
        keyboard.unhook_all()
        for group in self.groups:
            if group.get('enabled', True):
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
                hover_color="#cc3a47"
            )
            self.status_indicator.configure(fg_color=self.colors["warning"])
            self.status_label.configure(text="Hazır", text_color=self.colors["warning"])
        else:
            self.start_stop_btn.configure(
                text="▶  BAŞLAT",
                fg_color=self.colors["success"],
                hover_color="#00cc6e"
            )
            self.status_indicator.configure(fg_color=self.colors["danger"])
            self.status_label.configure(text="Durdu", text_color=self.colors["danger"])

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
        if not CONFIG_FILE.exists():
            # Default config with one group
            self.groups = [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Default Group",
                    "enabled": True,
                    "toggle_key": "num lock",
                    "spam_key": '"',
                    "spam_enabled": True,
                    "spam_timing": {"pre_delay": 1, "hold_time": 1, "post_delay": 1},
                    "spam_key_interval": 0.025,
                    "search_region": [430, 275, 750, 460],
                    "cycle_delay": 0.01,
                    "templates": []
                }
            ]
            return

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.groups = data.get("groups", [])
                self.global_settings = data.get("global_settings", {})
        except Exception as e:
            messagebox.showerror("Hata", f"Config yüklenemedi: {e}")

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

    def save_config(self):
        """Save config to JSON"""
        try:
            self.global_settings["debug_enabled"] = self.debug_var.get()

            data = {
                "groups": self.groups,
                "global_settings": self.global_settings
            }

            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("Başarılı", "Config kaydedildi!")
        except Exception as e:
            messagebox.showerror("Hata", f"Config kaydedilemedi: {e}")

    def on_close(self):
        """Handle window close"""
        if self.bot_active:
            self.stop_all_bots()
        self.root.quit()


# ==================== DIALOG CLASSES ====================

class AddGroupDialog:
    """Dialog for adding new group"""
    def __init__(self, parent, manager):
        self.manager = manager
        self.selected_key = None
        self.spam_key = None

        self.top = ctk.CTkToplevel(parent)
        self.top.title("Yeni Grup Ekle")
        self.top.geometry("500x550")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)
        self.top.after(10, self.center_window)

        main = ctk.CTkFrame(self.top, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=30, pady=25)

        ctk.CTkLabel(main, text="📁 Yeni Grup", font=ctk.CTkFont(size=20, weight="bold"),
                    text_color="#00d4ff").pack(pady=(0, 20))

        # Name
        name_frame = ctk.CTkFrame(main, fg_color="transparent")
        name_frame.pack(fill="x", pady=8)
        ctk.CTkLabel(name_frame, text="Grup Adı:", width=100).pack(side="left")
        self.name_entry = ctk.CTkEntry(name_frame, width=250, height=35)
        self.name_entry.pack(side="left", padx=10)
        self.name_entry.insert(0, f"Group {len(manager.groups) + 1}")

        # Toggle key
        key_frame = ctk.CTkFrame(main, fg_color="transparent")
        key_frame.pack(fill="x", pady=8)
        ctk.CTkLabel(key_frame, text="Start/Stop Tuşu:", width=100).pack(side="left")
        self.key_btn = ctk.CTkButton(key_frame, text="Tuş Seç", width=150, height=35,
                                      fg_color="#333333", hover_color="#444444",
                                      command=self.capture_toggle_key)
        self.key_btn.pack(side="left", padx=10)

        # Spam settings
        spam_frame = ctk.CTkFrame(main, fg_color="#1a1a1a", corner_radius=10)
        spam_frame.pack(fill="x", pady=15)

        spam_header = ctk.CTkFrame(spam_frame, fg_color="transparent")
        spam_header.pack(fill="x", padx=15, pady=(15, 10))

        self.spam_enabled_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(spam_header, text="Spam Tuşu Aktif", variable=self.spam_enabled_var,
                       fg_color="#00d4ff", command=self.toggle_spam_options).pack(side="left")

        self.spam_options = ctk.CTkFrame(spam_frame, fg_color="transparent")
        self.spam_options.pack(fill="x", padx=15, pady=(0, 15))

        spam_key_row = ctk.CTkFrame(self.spam_options, fg_color="transparent")
        spam_key_row.pack(fill="x", pady=5)
        ctk.CTkLabel(spam_key_row, text="Spam Tuşu:", width=80).pack(side="left")
        self.spam_key_btn = ctk.CTkButton(spam_key_row, text="Tuş Seç", width=100, height=30,
                                          fg_color="#333333", hover_color="#444444",
                                          command=self.capture_spam_key, state="disabled")
        self.spam_key_btn.pack(side="left", padx=10)

        timing_row = ctk.CTkFrame(self.spam_options, fg_color="transparent")
        timing_row.pack(fill="x", pady=5)
        ctk.CTkLabel(timing_row, text="Önce:", width=40).pack(side="left")
        self.pre_entry = ctk.CTkEntry(timing_row, width=50, height=28, state="disabled")
        self.pre_entry.pack(side="left", padx=3)
        ctk.CTkLabel(timing_row, text="Basılı:", width=40).pack(side="left", padx=(10, 0))
        self.hold_entry = ctk.CTkEntry(timing_row, width=50, height=28, state="disabled")
        self.hold_entry.pack(side="left", padx=3)
        ctk.CTkLabel(timing_row, text="Sonra:", width=40).pack(side="left", padx=(10, 0))
        self.post_entry = ctk.CTkEntry(timing_row, width=50, height=28, state="disabled")
        self.post_entry.pack(side="left", padx=3)

        # Search region
        region_frame = ctk.CTkFrame(main, fg_color="transparent")
        region_frame.pack(fill="x", pady=8)
        ctk.CTkLabel(region_frame, text="Arama Bölgesi:", width=100).pack(side="left")
        self.region_label = ctk.CTkLabel(region_frame, text="430,275 - 750,460")
        self.region_label.pack(side="left", padx=10)
        self.search_region = [430, 275, 750, 460]
        ctk.CTkButton(region_frame, text="Seç", width=60, height=30,
                     fg_color="#333333", hover_color="#444444",
                     command=self.select_region).pack(side="left")

        # Buttons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(20, 0))

        ctk.CTkButton(btn_frame, text="✓ Ekle", width=120, height=40, fg_color="#00ff88",
                     hover_color="#00cc6e", text_color="#000000",
                     font=ctk.CTkFont(weight="bold"), command=self.save).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="İptal", width=100, height=40, fg_color="#333333",
                     hover_color="#444444", command=self.top.destroy).pack(side="left")

    def center_window(self):
        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        x = (self.top.winfo_screenwidth() // 2) - (w // 2)
        y = (self.top.winfo_screenheight() // 2) - (h // 2)
        self.top.geometry(f'{w}x{h}+{x}+{y}')

    def toggle_spam_options(self):
        state = "normal" if self.spam_enabled_var.get() else "disabled"
        self.spam_key_btn.configure(state=state)
        self.pre_entry.configure(state=state)
        self.hold_entry.configure(state=state)
        self.post_entry.configure(state=state)
        if state == "normal" and not self.pre_entry.get():
            self.pre_entry.insert(0, "1")
            self.hold_entry.insert(0, "1")
            self.post_entry.insert(0, "1")

    def capture_toggle_key(self):
        CaptureKeyDialogSimple(self.top, self, "toggle")

    def capture_spam_key(self):
        CaptureKeyDialogSimple(self.top, self, "spam")

    def select_region(self):
        self.top.withdraw()
        self.top.after(200, lambda: SelectRegionDialogSimple(self.top.master, self))

    def save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Uyarı", "Grup adı boş olamaz!")
            return

        if not self.selected_key:
            messagebox.showwarning("Uyarı", "Start/Stop tuşu seçmelisiniz!")
            return

        # Check for duplicate hotkey
        used_by = self.manager.is_hotkey_used(self.selected_key)
        if used_by:
            messagebox.showwarning("Uyarı", f"Bu tuş zaten '{used_by}' grubu tarafından kullanılıyor!")
            return

        # Get spam timing
        try:
            pre = int(self.pre_entry.get()) if self.pre_entry.get() else 1
            hold = int(self.hold_entry.get()) if self.hold_entry.get() else 1
            post = int(self.post_entry.get()) if self.post_entry.get() else 1
        except:
            pre = hold = post = 1

        new_group = {
            "id": str(uuid.uuid4()),
            "name": name,
            "enabled": True,
            "toggle_key": self.selected_key,
            "spam_key": self.spam_key,
            "spam_enabled": self.spam_enabled_var.get(),
            "spam_timing": {"pre_delay": pre, "hold_time": hold, "post_delay": post},
            "spam_key_interval": 0.025,
            "search_region": self.search_region,
            "cycle_delay": 0.01,
            "templates": []
        }

        self.manager.groups.append(new_group)
        self.manager.refresh_group_list()
        self.top.destroy()


class EditGroupDialog:
    """Dialog for editing group"""
    def __init__(self, parent, manager, index):
        self.manager = manager
        self.index = index
        self.group = manager.groups[index]
        self.selected_key = self.group.get('toggle_key')
        self.spam_key = self.group.get('spam_key')
        self.search_region = self.group.get('search_region', [430, 275, 750, 460])

        self.top = ctk.CTkToplevel(parent)
        self.top.title(f"Grubu Düzenle: {self.group['name']}")
        self.top.geometry("500x550")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)
        self.top.after(10, self.center_window)

        main = ctk.CTkFrame(self.top, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=30, pady=25)

        ctk.CTkLabel(main, text="✏️ Grubu Düzenle", font=ctk.CTkFont(size=20, weight="bold"),
                    text_color="#00d4ff").pack(pady=(0, 20))

        # Name
        name_frame = ctk.CTkFrame(main, fg_color="transparent")
        name_frame.pack(fill="x", pady=8)
        ctk.CTkLabel(name_frame, text="Grup Adı:", width=100).pack(side="left")
        self.name_entry = ctk.CTkEntry(name_frame, width=250, height=35)
        self.name_entry.pack(side="left", padx=10)
        self.name_entry.insert(0, self.group['name'])

        # Toggle key
        key_frame = ctk.CTkFrame(main, fg_color="transparent")
        key_frame.pack(fill="x", pady=8)
        ctk.CTkLabel(key_frame, text="Start/Stop Tuşu:", width=100).pack(side="left")
        self.key_btn = ctk.CTkButton(key_frame, text=self.selected_key or "Tuş Seç", width=150, height=35,
                                      fg_color="#333333", hover_color="#444444",
                                      command=self.capture_toggle_key)
        self.key_btn.pack(side="left", padx=10)

        # Spam settings
        spam_frame = ctk.CTkFrame(main, fg_color="#1a1a1a", corner_radius=10)
        spam_frame.pack(fill="x", pady=15)

        spam_header = ctk.CTkFrame(spam_frame, fg_color="transparent")
        spam_header.pack(fill="x", padx=15, pady=(15, 10))

        self.spam_enabled_var = ctk.BooleanVar(value=self.group.get('spam_enabled', False))
        ctk.CTkCheckBox(spam_header, text="Spam Tuşu Aktif", variable=self.spam_enabled_var,
                       fg_color="#00d4ff", command=self.toggle_spam_options).pack(side="left")

        self.spam_options = ctk.CTkFrame(spam_frame, fg_color="transparent")
        self.spam_options.pack(fill="x", padx=15, pady=(0, 15))

        spam_key_row = ctk.CTkFrame(self.spam_options, fg_color="transparent")
        spam_key_row.pack(fill="x", pady=5)
        ctk.CTkLabel(spam_key_row, text="Spam Tuşu:", width=80).pack(side="left")
        self.spam_key_btn = ctk.CTkButton(spam_key_row, text=self.spam_key or "Tuş Seç", width=100, height=30,
                                          fg_color="#333333", hover_color="#444444",
                                          command=self.capture_spam_key)
        self.spam_key_btn.pack(side="left", padx=10)

        timing = self.group.get('spam_timing', {"pre_delay": 1, "hold_time": 1, "post_delay": 1})
        timing_row = ctk.CTkFrame(self.spam_options, fg_color="transparent")
        timing_row.pack(fill="x", pady=5)
        ctk.CTkLabel(timing_row, text="Önce:", width=40).pack(side="left")
        self.pre_entry = ctk.CTkEntry(timing_row, width=50, height=28)
        self.pre_entry.pack(side="left", padx=3)
        self.pre_entry.insert(0, str(timing.get('pre_delay', 1)))
        ctk.CTkLabel(timing_row, text="Basılı:", width=40).pack(side="left", padx=(10, 0))
        self.hold_entry = ctk.CTkEntry(timing_row, width=50, height=28)
        self.hold_entry.pack(side="left", padx=3)
        self.hold_entry.insert(0, str(timing.get('hold_time', 1)))
        ctk.CTkLabel(timing_row, text="Sonra:", width=40).pack(side="left", padx=(10, 0))
        self.post_entry = ctk.CTkEntry(timing_row, width=50, height=28)
        self.post_entry.pack(side="left", padx=3)
        self.post_entry.insert(0, str(timing.get('post_delay', 1)))

        # Update spam options state
        self.toggle_spam_options()

        # Search region
        region_frame = ctk.CTkFrame(main, fg_color="transparent")
        region_frame.pack(fill="x", pady=8)
        ctk.CTkLabel(region_frame, text="Arama Bölgesi:", width=100).pack(side="left")
        self.region_label = ctk.CTkLabel(region_frame,
            text=f"{self.search_region[0]},{self.search_region[1]} - {self.search_region[2]},{self.search_region[3]}")
        self.region_label.pack(side="left", padx=10)
        ctk.CTkButton(region_frame, text="Seç", width=60, height=30,
                     fg_color="#333333", hover_color="#444444",
                     command=self.select_region).pack(side="left")

        # Buttons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(20, 0))

        ctk.CTkButton(btn_frame, text="✓ Kaydet", width=120, height=40, fg_color="#00ff88",
                     hover_color="#00cc6e", text_color="#000000",
                     font=ctk.CTkFont(weight="bold"), command=self.save).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="İptal", width=100, height=40, fg_color="#333333",
                     hover_color="#444444", command=self.top.destroy).pack(side="left")

    def center_window(self):
        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        x = (self.top.winfo_screenwidth() // 2) - (w // 2)
        y = (self.top.winfo_screenheight() // 2) - (h // 2)
        self.top.geometry(f'{w}x{h}+{x}+{y}')

    def toggle_spam_options(self):
        state = "normal" if self.spam_enabled_var.get() else "disabled"
        self.spam_key_btn.configure(state=state)
        self.pre_entry.configure(state=state)
        self.hold_entry.configure(state=state)
        self.post_entry.configure(state=state)

    def capture_toggle_key(self):
        CaptureKeyDialogSimple(self.top, self, "toggle")

    def capture_spam_key(self):
        CaptureKeyDialogSimple(self.top, self, "spam")

    def select_region(self):
        self.top.withdraw()
        self.top.after(200, lambda: SelectRegionDialogSimple(self.top.master, self))

    def save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Uyarı", "Grup adı boş olamaz!")
            return

        if not self.selected_key:
            messagebox.showwarning("Uyarı", "Start/Stop tuşu seçmelisiniz!")
            return

        # Check for duplicate hotkey
        used_by = self.manager.is_hotkey_used(self.selected_key, self.group.get('id'))
        if used_by:
            messagebox.showwarning("Uyarı", f"Bu tuş zaten '{used_by}' grubu tarafından kullanılıyor!")
            return

        # Get spam timing
        try:
            pre = int(self.pre_entry.get()) if self.pre_entry.get() else 1
            hold = int(self.hold_entry.get()) if self.hold_entry.get() else 1
            post = int(self.post_entry.get()) if self.post_entry.get() else 1
        except:
            pre = hold = post = 1

        self.group['name'] = name
        self.group['toggle_key'] = self.selected_key
        self.group['spam_key'] = self.spam_key
        self.group['spam_enabled'] = self.spam_enabled_var.get()
        self.group['spam_timing'] = {"pre_delay": pre, "hold_time": hold, "post_delay": post}
        self.group['search_region'] = self.search_region

        self.manager.groups[self.index] = self.group
        self.manager.refresh_group_list()
        self.manager.update_group_details()
        self.top.destroy()


class CaptureKeyDialogSimple:
    """Simple key capture dialog"""
    def __init__(self, parent, caller, key_type):
        self.caller = caller
        self.key_type = key_type

        self.top = ctk.CTkToplevel(parent)
        self.top.title("Tuş Seç")
        self.top.geometry("300x150")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)
        self.top.after(10, self.center_window)

        main = ctk.CTkFrame(self.top, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(main, text="Bir tuşa basın...", font=ctk.CTkFont(size=14)).pack(pady=(0, 15))

        self.key_label = ctk.CTkLabel(main, text="Bekleniyor...", font=ctk.CTkFont(size=18, weight="bold"),
                                       text_color="#00d4ff")
        self.key_label.pack(pady=(0, 15))

        ctk.CTkButton(main, text="İptal", width=80, height=32, fg_color="#333333",
                     command=self.cancel).pack()

        keyboard.hook(self.on_key)

    def center_window(self):
        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        x = (self.top.winfo_screenwidth() // 2) - (w // 2)
        y = (self.top.winfo_screenheight() // 2) - (h // 2)
        self.top.geometry(f'{w}x{h}+{x}+{y}')

    def on_key(self, event):
        if event.event_type == 'down':
            key = event.name
            keyboard.unhook_all()

            if self.key_type == "toggle":
                self.caller.selected_key = key
                self.caller.key_btn.configure(text=key)
            else:
                self.caller.spam_key = key
                self.caller.spam_key_btn.configure(text=key)

            self.top.destroy()

    def cancel(self):
        keyboard.unhook_all()
        self.top.destroy()


class SelectRegionDialogSimple:
    """Simple region selection dialog"""
    def __init__(self, parent, caller):
        self.caller = caller
        self.screenshot = ImageGrab.grab()
        self.width, self.height = self.screenshot.size

        self.top = tk.Toplevel(parent)
        self.top.title("Bölge Seç")
        self.top.attributes('-fullscreen', True)
        self.top.attributes('-topmost', True)
        self.top.configure(cursor="crosshair")
        self.top.focus_force()
        self.top.grab_set()

        self.canvas = tk.Canvas(self.top, highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.photo = ImageTk.PhotoImage(self.screenshot)
        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

        self.rect = None
        self.start_x = None
        self.start_y = None

        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<Escape>', lambda e: self.cancel())
        self.canvas.focus_set()

        self.canvas.create_rectangle(self.width//2 - 150, 30, self.width//2 + 150, 60,
                                     fill='black', stipple='gray50')
        self.canvas.create_text(self.width//2, 45, text="Tıkla ve sürükle | ESC: İptal",
                               font=('Arial', 12, 'bold'), fill='white')

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y,
                                                  outline='#00d4ff', width=3, dash=(5, 5))

    def on_drag(self, event):
        if self.rect:
            self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)

        if x2 - x1 < 10 or y2 - y1 < 10:
            return

        self.caller.search_region = [x1, y1, x2, y2]
        self.caller.region_label.configure(text=f"{x1},{y1} - {x2},{y2}")
        self.top.destroy()
        self.caller.top.deiconify()

    def cancel(self):
        self.top.destroy()
        self.caller.top.deiconify()


class AddTemplateDialog:
    """Dialog for adding template to group"""
    def __init__(self, parent, manager):
        self.manager = manager
        self.template_img = None
        self.key_combo = None
        self.selected_color = "#00ff88"

        self.top = ctk.CTkToplevel(parent)
        self.top.title("Template Ekle")
        self.top.geometry("450x300")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)
        self.top.after(10, self.center_window)

        main = ctk.CTkFrame(self.top, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=30, pady=25)

        ctk.CTkLabel(main, text="🎯 Template Ekle", font=ctk.CTkFont(size=20, weight="bold"),
                    text_color="#00d4ff").pack(pady=(0, 20))

        info = ctk.CTkFrame(main, fg_color="#1a1a1a", corner_radius=10)
        info.pack(fill="x", pady=(0, 20))

        for step in ["1️⃣  Ekran görüntüsü al", "2️⃣  Bölge seç", "3️⃣  Tuş ata"]:
            ctk.CTkLabel(info, text=step, font=ctk.CTkFont(size=12)).pack(anchor="w", padx=15, pady=4)

        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(btn_frame, text="▶ Başla", width=120, height=40, fg_color="#00ff88",
                     hover_color="#00cc6e", text_color="#000000",
                     font=ctk.CTkFont(weight="bold"), command=self.start_capture).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="İptal", width=100, height=40, fg_color="#333333",
                     command=self.top.destroy).pack(side="left")

    def center_window(self):
        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        x = (self.top.winfo_screenwidth() // 2) - (w // 2)
        y = (self.top.winfo_screenheight() // 2) - (h // 2)
        self.top.geometry(f'{w}x{h}+{x}+{y}')

    def start_capture(self):
        self.top.withdraw()
        self.top.after(200, self.do_capture)

    def do_capture(self):
        TemplateCapture(self.top.master, self)


class TemplateCapture:
    """Capture template from screen"""
    def __init__(self, parent, add_dialog):
        self.add_dialog = add_dialog
        self.screenshot = ImageGrab.grab()
        self.width, self.height = self.screenshot.size

        self.top = tk.Toplevel(parent)
        self.top.title("Bölge Seç")
        self.top.attributes('-fullscreen', True)
        self.top.attributes('-topmost', True)
        self.top.configure(cursor="crosshair")
        self.top.focus_force()
        self.top.grab_set()

        self.canvas = tk.Canvas(self.top, highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.photo = ImageTk.PhotoImage(self.screenshot)
        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

        self.rect = None
        self.start_x = None
        self.start_y = None
        self.is_selecting = False
        self.overlay = None
        self.coord_text = None

        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<Escape>', lambda e: self.cancel())
        self.canvas.bind('<Motion>', self.on_motion)
        self.canvas.focus_set()

        # Talimatlar
        self.canvas.create_rectangle(
            self.width//2 - 180, 30, self.width//2 + 180, 70,
            fill='black', stipple='gray50'
        )
        self.canvas.create_text(
            self.width//2, 50,
            text="Tıkla ve sürükle | ESC: İptal",
            font=('Arial', 12, 'bold'), fill='white'
        )

    def on_motion(self, event):
        if not self.is_selecting:
            if self.coord_text:
                self.canvas.delete(self.coord_text)
            self.coord_text = self.canvas.create_text(
                event.x + 15, event.y - 15,
                text=f"X: {event.x}, Y: {event.y}",
                fill='cyan', font=('Arial', 10, 'bold'), anchor=tk.NW
            )

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.is_selecting = True

        if self.rect:
            self.canvas.delete(self.rect)
        if self.overlay:
            self.canvas.delete(self.overlay)
        if self.coord_text:
            self.canvas.delete(self.coord_text)

        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='#00d4ff', width=3, dash=(5, 5)
        )
        self.overlay = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            fill='#00d4ff', stipple='gray25', outline=''
        )

    def on_drag(self, event):
        if self.rect and self.is_selecting:
            self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)
            if self.overlay:
                self.canvas.coords(self.overlay, self.start_x, self.start_y, event.x, event.y)

            width = abs(event.x - self.start_x)
            height = abs(event.y - self.start_y)

            if self.coord_text:
                self.canvas.delete(self.coord_text)
            self.coord_text = self.canvas.create_text(
                event.x + 15, event.y - 15,
                text=f"{width}x{height} px",
                fill='cyan', font=('Arial', 12, 'bold'), anchor=tk.NW
            )

    def on_release(self, event):
        self.is_selecting = False
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)

        if x2 - x1 < 10 or y2 - y1 < 10:
            if self.rect:
                self.canvas.delete(self.rect)
            if self.overlay:
                self.canvas.delete(self.overlay)
            return

        template_img = self.screenshot.crop((x1, y1, x2, y2))
        self.top.destroy()
        TemplateFinalizeDialog(self.top.master, self.add_dialog, template_img)

    def cancel(self):
        self.top.destroy()
        self.add_dialog.top.deiconify()


class TemplateFinalizeDialog:
    """Finalize template with name and key"""
    def __init__(self, parent, add_dialog, template_img):
        self.add_dialog = add_dialog
        self.manager = add_dialog.manager
        self.template_img = template_img
        self.key_combo = None
        self.selected_color = "#00ff88"

        self.top = ctk.CTkToplevel(parent)
        self.top.title("Template Detayları")
        self.top.geometry("450x480")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)
        self.top.after(10, self.center_window)

        main = ctk.CTkFrame(self.top, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=30, pady=20)

        ctk.CTkLabel(main, text="✨ Template Detayları", font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="#00d4ff").pack(pady=(0, 15))

        # Preview
        preview_frame = ctk.CTkFrame(main, fg_color="#1a1a1a", corner_radius=10)
        preview_frame.pack(pady=(0, 15))
        try:
            preview = template_img.copy()
            preview.thumbnail((80, 80))
            self.preview_photo = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)
            ctk.CTkLabel(preview_frame, image=self.preview_photo, text="").pack(padx=15, pady=15)
        except:
            pass

        # Name
        name_row = ctk.CTkFrame(main, fg_color="transparent")
        name_row.pack(fill="x", pady=5)
        ctk.CTkLabel(name_row, text="İsim:", width=70).pack(side="left")
        self.name_entry = ctk.CTkEntry(name_row, width=200, height=32)
        self.name_entry.pack(side="left", padx=10)
        self.name_entry.insert(0, f"template_{len(self.manager.groups[self.manager.selected_group_index].get('templates', [])) + 1}")

        # Key combo
        key_row = ctk.CTkFrame(main, fg_color="transparent")
        key_row.pack(fill="x", pady=5)
        ctk.CTkLabel(key_row, text="Tuş:", width=70).pack(side="left")
        self.key_btn = ctk.CTkButton(key_row, text="Tuş Seç", width=120, height=32,
                                      fg_color="#333333", command=self.capture_key)
        self.key_btn.pack(side="left", padx=10)

        # Threshold
        thresh_row = ctk.CTkFrame(main, fg_color="transparent")
        thresh_row.pack(fill="x", pady=5)
        ctk.CTkLabel(thresh_row, text="Threshold:", width=70).pack(side="left")
        self.threshold_slider = ctk.CTkSlider(thresh_row, from_=0.5, to=1.0, width=150)
        self.threshold_slider.pack(side="left", padx=10)
        self.threshold_slider.set(0.9)
        self.thresh_label = ctk.CTkLabel(thresh_row, text="0.90", width=40)
        self.thresh_label.pack(side="left")
        self.threshold_slider.configure(command=lambda v: self.thresh_label.configure(text=f"{v:.2f}"))

        # Color
        color_row = ctk.CTkFrame(main, fg_color="transparent")
        color_row.pack(fill="x", pady=5)
        ctk.CTkLabel(color_row, text="Renk:", width=70).pack(side="left")
        self.color_preview = ctk.CTkFrame(color_row, width=30, height=25, corner_radius=4, fg_color=self.selected_color)
        self.color_preview.pack(side="left", padx=10)
        ctk.CTkButton(color_row, text="Seç", width=50, height=25, fg_color="#333333",
                     command=self.pick_color).pack(side="left")

        # Timing
        timing_row = ctk.CTkFrame(main, fg_color="transparent")
        timing_row.pack(fill="x", pady=8)
        ctk.CTkLabel(timing_row, text="Timing (ms):", width=70).pack(side="left")
        self.pre_entry = ctk.CTkEntry(timing_row, width=45, height=28)
        self.pre_entry.pack(side="left", padx=3)
        self.pre_entry.insert(0, "1")
        self.hold_entry = ctk.CTkEntry(timing_row, width=45, height=28)
        self.hold_entry.pack(side="left", padx=3)
        self.hold_entry.insert(0, "1")
        self.post_entry = ctk.CTkEntry(timing_row, width=45, height=28)
        self.post_entry.pack(side="left", padx=3)
        self.post_entry.insert(0, "1")

        # Buttons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(15, 0))

        ctk.CTkButton(btn_frame, text="✓ Kaydet", width=120, height=40, fg_color="#00ff88",
                     hover_color="#00cc6e", text_color="#000000",
                     font=ctk.CTkFont(weight="bold"), command=self.save).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="İptal", width=100, height=40, fg_color="#333333",
                     command=self.cancel).pack(side="left")

    def center_window(self):
        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        x = (self.top.winfo_screenwidth() // 2) - (w // 2)
        y = (self.top.winfo_screenheight() // 2) - (h // 2)
        self.top.geometry(f'{w}x{h}+{x}+{y}')

    def capture_key(self):
        CaptureKeyComboDialog(self.top, self)

    def pick_color(self):
        color = colorchooser.askcolor(initialcolor=self.selected_color)
        if color[1]:
            self.selected_color = color[1]
            self.color_preview.configure(fg_color=self.selected_color)

    def save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Uyarı", "İsim boş olamaz!")
            return

        if not self.key_combo:
            messagebox.showwarning("Uyarı", "Tuş atamalısınız!")
            return

        # Save image
        filename = f"{name}.png"
        filepath = IMAGES_FOLDER / filename
        try:
            self.template_img.save(filepath, 'PNG')
        except Exception as e:
            messagebox.showerror("Hata", f"Görsel kaydedilemedi: {e}")
            return

        # Get timing
        try:
            pre = int(self.pre_entry.get())
            hold = int(self.hold_entry.get())
            post = int(self.post_entry.get())
        except:
            pre = hold = post = 1

        new_template = {
            "name": name,
            "file": filename,
            "enabled": True,
            "threshold": self.threshold_slider.get(),
            "key_combo": self.key_combo,
            "color": self.selected_color,
            "timing": {"pre_delay": pre, "hold_time": hold, "post_delay": post},
            "use_macro": False,
            "macro": []
        }

        if 'templates' not in self.manager.groups[self.manager.selected_group_index]:
            self.manager.groups[self.manager.selected_group_index]['templates'] = []

        self.manager.groups[self.manager.selected_group_index]['templates'].append(new_template)
        self.manager.refresh_template_list()

        self.top.destroy()
        self.add_dialog.top.destroy()

    def cancel(self):
        self.top.destroy()
        self.add_dialog.top.deiconify()


class CaptureKeyComboDialog:
    """Capture key combination"""
    def __init__(self, parent, caller):
        self.caller = caller
        self.captured_keys = []

        self.top = ctk.CTkToplevel(parent)
        self.top.title("Tuş Kombinasyonu")
        self.top.geometry("350x180")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)
        self.top.after(10, self.center_window)

        main = ctk.CTkFrame(self.top, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=25, pady=20)

        ctk.CTkLabel(main, text="Tuş kombinasyonunu basın:", font=ctk.CTkFont(size=13)).pack(pady=(0, 10))

        self.key_label = ctk.CTkLabel(main, text="Bekleniyor...", font=ctk.CTkFont(size=18, weight="bold"),
                                       text_color="#00d4ff")
        self.key_label.pack(pady=(0, 15))

        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack()

        self.ok_btn = ctk.CTkButton(btn_frame, text="Tamam", width=80, height=32, fg_color="#00ff88",
                                    text_color="#000000", state="disabled", command=self.confirm)
        self.ok_btn.pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="İptal", width=80, height=32, fg_color="#333333",
                     command=self.cancel).pack(side="left")

        keyboard.hook(self.on_key)

    def center_window(self):
        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        x = (self.top.winfo_screenwidth() // 2) - (w // 2)
        y = (self.top.winfo_screenheight() // 2) - (h // 2)
        self.top.geometry(f'{w}x{h}+{x}+{y}')

    def on_key(self, event):
        if event.event_type == 'down' and event.name not in self.captured_keys:
            self.captured_keys.append(event.name)
            combo = ' + '.join(self.captured_keys)
            self.key_label.configure(text=combo)
            self.ok_btn.configure(state="normal")

    def confirm(self):
        keyboard.unhook_all()
        self.caller.key_combo = '+'.join(self.captured_keys)
        self.caller.key_btn.configure(text=self.caller.key_combo)
        self.top.destroy()

    def cancel(self):
        keyboard.unhook_all()
        self.top.destroy()


class EditTemplateDialog:
    """Dialog for editing template"""
    def __init__(self, parent, manager, template, index):
        self.manager = manager
        self.template = template
        self.index = index
        self.selected_color = template.get('color', '#00ff88')
        self.key_combo = template.get('key_combo', '')
        self.new_image = None
        self.macro_list = template.get('macro', [])[:]  # Kopyala

        self.top = ctk.CTkToplevel(parent)
        self.top.title(f"Template Düzenle: {template['name']}")
        self.top.geometry("500x700")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)
        self.top.after(10, self.center_window)

        # Scrollable main
        main_scroll = ctk.CTkScrollableFrame(self.top, fg_color="transparent")
        main_scroll.pack(fill="both", expand=True, padx=20, pady=15)

        ctk.CTkLabel(main_scroll, text="✏️ Template Düzenle", font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="#00d4ff").pack(pady=(0, 15))

        # Preview frame
        preview_container = ctk.CTkFrame(main_scroll, fg_color="#1a1a1a", corner_radius=10)
        preview_container.pack(fill="x", pady=(0, 10))
        preview_content = ctk.CTkFrame(preview_container, fg_color="transparent")
        preview_content.pack(fill="x", padx=15, pady=12)

        self.preview_frame = ctk.CTkFrame(preview_content, fg_color="#0d0d0d", width=70, height=70, corner_radius=8)
        self.preview_frame.pack(side="left")
        self.preview_frame.pack_propagate(False)
        self.preview_label = ctk.CTkLabel(self.preview_frame, text="")
        self.preview_label.pack(expand=True)
        self.load_preview()

        ctk.CTkButton(preview_content, text="Yeni Görsel", width=100, height=30, fg_color="#333333",
                     command=self.capture_new_image).pack(side="left", padx=15)

        # Name
        name_row = ctk.CTkFrame(main_scroll, fg_color="transparent")
        name_row.pack(fill="x", pady=4)
        ctk.CTkLabel(name_row, text="İsim:", width=80).pack(side="left")
        self.name_entry = ctk.CTkEntry(name_row, width=180, height=30)
        self.name_entry.pack(side="left", padx=5)
        self.name_entry.insert(0, template['name'])

        # Threshold & Color row
        tc_row = ctk.CTkFrame(main_scroll, fg_color="transparent")
        tc_row.pack(fill="x", pady=4)
        ctk.CTkLabel(tc_row, text="Threshold:", width=80).pack(side="left")
        self.threshold_slider = ctk.CTkSlider(tc_row, from_=0.5, to=1.0, width=120)
        self.threshold_slider.pack(side="left", padx=5)
        self.threshold_slider.set(template.get('threshold', 0.9))
        self.thresh_label = ctk.CTkLabel(tc_row, text=f"{template.get('threshold', 0.9):.2f}", width=35)
        self.thresh_label.pack(side="left")
        self.threshold_slider.configure(command=lambda v: self.thresh_label.configure(text=f"{v:.2f}"))

        self.color_preview = ctk.CTkFrame(tc_row, width=25, height=25, corner_radius=4, fg_color=self.selected_color)
        self.color_preview.pack(side="left", padx=(15, 5))
        ctk.CTkButton(tc_row, text="Renk", width=45, height=25, fg_color="#333333",
                     command=self.pick_color).pack(side="left")

        # ==================== MAKRO MODU ====================
        macro_frame = ctk.CTkFrame(main_scroll, fg_color="#1a1a1a", corner_radius=10)
        macro_frame.pack(fill="x", pady=10)

        macro_header = ctk.CTkFrame(macro_frame, fg_color="transparent")
        macro_header.pack(fill="x", padx=15, pady=(10, 5))

        self.use_macro_var = ctk.BooleanVar(value=template.get('use_macro', False))
        ctk.CTkCheckBox(macro_header, text="Gelişmiş Makro Kullan", variable=self.use_macro_var,
                       fg_color="#00d4ff", command=self.toggle_macro_mode).pack(side="left")

        # Basit mod frame
        self.simple_frame = ctk.CTkFrame(macro_frame, fg_color="transparent")
        self.simple_frame.pack(fill="x", padx=15, pady=10)

        simple_row1 = ctk.CTkFrame(self.simple_frame, fg_color="transparent")
        simple_row1.pack(fill="x", pady=3)
        ctk.CTkLabel(simple_row1, text="Tuş:", width=60).pack(side="left")
        self.key_btn = ctk.CTkButton(simple_row1, text=self.key_combo or "Tuş Seç", width=120, height=28,
                                      fg_color="#333333", command=self.capture_key)
        self.key_btn.pack(side="left", padx=5)

        simple_row2 = ctk.CTkFrame(self.simple_frame, fg_color="transparent")
        simple_row2.pack(fill="x", pady=3)
        timing = template.get('timing', {"pre_delay": 1, "hold_time": 1, "post_delay": 1})
        ctk.CTkLabel(simple_row2, text="Timing:", width=60).pack(side="left")
        self.pre_entry = ctk.CTkEntry(simple_row2, width=45, height=26, placeholder_text="Önce")
        self.pre_entry.pack(side="left", padx=2)
        self.pre_entry.insert(0, str(timing.get('pre_delay', 1)))
        self.hold_entry = ctk.CTkEntry(simple_row2, width=45, height=26, placeholder_text="Basılı")
        self.hold_entry.pack(side="left", padx=2)
        self.hold_entry.insert(0, str(timing.get('hold_time', 1)))
        self.post_entry = ctk.CTkEntry(simple_row2, width=45, height=26, placeholder_text="Sonra")
        self.post_entry.pack(side="left", padx=2)
        self.post_entry.insert(0, str(timing.get('post_delay', 1)))
        ctk.CTkLabel(simple_row2, text="ms", text_color="#666666").pack(side="left", padx=3)

        # Makro mod frame
        self.macro_frame = ctk.CTkFrame(macro_frame, fg_color="transparent")

        # Record kontrolü
        self.is_recording = False
        self.record_start_time = 0
        self.last_key_time = 0

        # Record satırı
        record_row = ctk.CTkFrame(self.macro_frame, fg_color="transparent")
        record_row.pack(fill="x", pady=(0, 8))

        self.record_btn = ctk.CTkButton(record_row, text="⏺ Kayıt Başlat", width=110, height=28,
                                        fg_color="#aa2222", hover_color="#cc3333",
                                        command=self.toggle_recording)
        self.record_btn.pack(side="left", padx=2)

        self.record_status = ctk.CTkLabel(record_row, text="", text_color="#ff6666",
                                          font=ctk.CTkFont(size=11))
        self.record_status.pack(side="left", padx=10)

        ctk.CTkButton(record_row, text="Temizle", width=60, height=28, fg_color="#444444",
                     command=self.clear_macro).pack(side="right", padx=2)

        # Drag & drop state
        self.drag_data = {"type": None, "index": None, "widget": None}
        self.drop_indicator = None

        # Manuel ekleme butonları (sürüklenebilir)
        macro_btn_row = ctk.CTkFrame(self.macro_frame, fg_color="transparent")
        macro_btn_row.pack(fill="x", pady=(0, 5))

        # Draggable butonlar
        btn_configs = [
            ("+ Down", "key_down", "#2d5a27", 60),
            ("+ Up", "key_up", "#5a2727", 50),
            ("+ Press", "key_press", "#27455a", 55),
            ("+ Sleep", "sleep", "#5a4a27", 55)
        ]

        for text, action_type, color, width in btn_configs:
            btn = ctk.CTkButton(macro_btn_row, text=text, width=width, height=24, fg_color=color,
                               font=ctk.CTkFont(size=10),
                               command=lambda at=action_type: self.add_macro_action(at))
            btn.pack(side="left", padx=2)
            # Drag binding
            btn.bind('<Button-1>', lambda e, at=action_type: self.start_drag_from_button(e, at))
            btn.bind('<B1-Motion>', self.on_drag_motion)
            btn.bind('<ButtonRelease-1>', self.on_drag_release)

        # Makro listesi
        self.macro_scroll = ctk.CTkScrollableFrame(self.macro_frame, fg_color="#0d0d0d", height=150)
        self.macro_scroll.pack(fill="x", pady=5)

        self.refresh_macro_list()

        # Toggle başlangıç durumu
        self.toggle_macro_mode()

        # Enabled
        self.enabled_var = ctk.BooleanVar(value=template.get('enabled', True))
        ctk.CTkCheckBox(main_scroll, text="Aktif", variable=self.enabled_var,
                       fg_color="#00d4ff").pack(anchor="w", pady=8)

        # Buttons
        btn_frame = ctk.CTkFrame(main_scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))
        ctk.CTkButton(btn_frame, text="✓ Kaydet", width=120, height=38, fg_color="#00ff88",
                     hover_color="#00cc6e", text_color="#000000",
                     font=ctk.CTkFont(weight="bold"), command=self.save).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="İptal", width=90, height=38, fg_color="#333333",
                     command=self.top.destroy).pack(side="left")

    def toggle_macro_mode(self):
        """Basit/Makro mod arasında geçiş"""
        if self.use_macro_var.get():
            self.simple_frame.pack_forget()
            self.macro_frame.pack(fill="x", padx=15, pady=10)
        else:
            self.macro_frame.pack_forget()
            self.simple_frame.pack(fill="x", padx=15, pady=10)

    def add_macro_action(self, action_type):
        """Makroya yeni aksiyon ekle"""
        if action_type == "sleep":
            self.macro_list.append({"action": "sleep", "ms": 50})
        else:
            self.macro_list.append({"action": action_type, "key": ""})
        self.refresh_macro_list()

    def refresh_macro_list(self):
        """Makro listesini yenile"""
        for widget in self.macro_scroll.winfo_children():
            widget.destroy()

        for i, action in enumerate(self.macro_list):
            row = ctk.CTkFrame(self.macro_scroll, fg_color="#1a1a1a", corner_radius=6, height=32)
            row.pack(fill="x", pady=2, padx=2)
            row.pack_propagate(False)
            row.macro_index = i  # Index'i sakla

            # Drag handle (sürükleme tutamacı)
            handle = ctk.CTkLabel(row, text="≡", width=20, text_color="#666666",
                                  font=ctk.CTkFont(size=14), cursor="hand2")
            handle.pack(side="left", padx=(3, 0))
            handle.bind('<Button-1>', lambda e, idx=i: self.start_drag_from_list(e, idx))
            handle.bind('<B1-Motion>', self.on_drag_motion)
            handle.bind('<ButtonRelease-1>', self.on_drag_release)

            # Sıra numarası
            ctk.CTkLabel(row, text=f"{i+1}.", width=20, text_color="#666666").pack(side="left", padx=2)

            action_type = action.get('action', '')

            # Aksiyon tipi badge
            colors = {"key_down": "#2d5a27", "key_up": "#5a2727", "key_press": "#27455a", "sleep": "#5a4a27"}
            labels = {"key_down": "↓ DOWN", "key_up": "↑ UP", "key_press": "⏎ PRESS", "sleep": "⏱ SLEEP"}

            ctk.CTkLabel(row, text=labels.get(action_type, "?"), width=70,
                        fg_color=colors.get(action_type, "#333"), corner_radius=4,
                        font=ctk.CTkFont(size=10)).pack(side="left", padx=3)

            if action_type == "sleep":
                entry = ctk.CTkEntry(row, width=50, height=24)
                entry.pack(side="left", padx=3)
                entry.insert(0, str(action.get('ms', 50)))
                entry.bind('<FocusOut>', lambda e, idx=i, ent=entry: self.update_macro_value(idx, 'ms', ent.get()))
                ctk.CTkLabel(row, text="ms", text_color="#666666", width=25).pack(side="left")
            else:
                entry = ctk.CTkEntry(row, width=80, height=24, placeholder_text="tuş")
                entry.pack(side="left", padx=3)
                entry.insert(0, action.get('key', ''))
                entry.bind('<FocusOut>', lambda e, idx=i, ent=entry: self.update_macro_value(idx, 'key', ent.get()))

            # Sil butonu
            ctk.CTkButton(row, text="×", width=24, height=24, fg_color="#ff4757",
                         command=lambda idx=i: self.delete_macro_action(idx)).pack(side="right", padx=5)

    def update_macro_value(self, idx, key, value):
        """Makro değerini güncelle"""
        if idx < len(self.macro_list):
            if key == 'ms':
                try:
                    self.macro_list[idx][key] = int(value)
                except:
                    pass
            else:
                self.macro_list[idx][key] = value

    def delete_macro_action(self, idx):
        """Makro aksiyonunu sil"""
        if idx < len(self.macro_list):
            del self.macro_list[idx]
            self.refresh_macro_list()

    def toggle_recording(self):
        """Kayıt başlat/durdur"""
        if not self.is_recording:
            # Kayıt başlat
            self.is_recording = True
            self.record_start_time = time.perf_counter()
            self.last_key_time = self.record_start_time
            self.record_btn.configure(text="⏹ Bitti", fg_color="#cc3333")
            self.record_status.configure(text="⏺ Kayıt yapılıyor...")
            # Keyboard hook'u ekle
            self.keyboard_hook = keyboard.hook(self.on_record_key)
        else:
            # Kayıt durdur
            self.is_recording = False
            self.record_btn.configure(text="⏺ Kayıt Başlat", fg_color="#aa2222")
            self.record_status.configure(text="")
            # Keyboard hook'u kaldır
            if hasattr(self, 'keyboard_hook') and self.keyboard_hook:
                keyboard.unhook(self.keyboard_hook)
                self.keyboard_hook = None
            self.refresh_macro_list()

    def on_record_key(self, event):
        """Klavye olaylarını kaydet"""
        if not self.is_recording:
            return

        current_time = time.perf_counter()

        # Son olaydan bu yana geçen süreyi hesapla
        elapsed_ms = int((current_time - self.last_key_time) * 1000)

        # Eğer anlamlı bir bekleme süresi varsa (>5ms), sleep ekle
        if elapsed_ms > 5:
            self.macro_list.append({"action": "sleep", "ms": elapsed_ms})

        # Tuş olayını ekle
        key_name = event.name
        if event.event_type == keyboard.KEY_DOWN:
            self.macro_list.append({"action": "key_down", "key": key_name})
        elif event.event_type == keyboard.KEY_UP:
            self.macro_list.append({"action": "key_up", "key": key_name})

        self.last_key_time = current_time

        # UI'ı güncelle (thread-safe)
        self.top.after(10, self.refresh_macro_list)

    def clear_macro(self):
        """Tüm makro aksiyonlarını temizle"""
        self.macro_list = []
        self.refresh_macro_list()

    def start_drag_from_button(self, event, action_type):
        """Butondan sürüklemeye başla"""
        self.drag_data = {"type": "new", "action_type": action_type, "index": None}

    def start_drag_from_list(self, event, index):
        """Listeden sürüklemeye başla"""
        self.drag_data = {"type": "reorder", "action_type": None, "index": index}

    def on_drag_motion(self, event):
        """Sürükleme hareketi"""
        if not self.drag_data["type"]:
            return

        # Mouse pozisyonunu al (pencere koordinatlarında)
        try:
            x_root = event.widget.winfo_rootx() + event.x
            y_root = event.widget.winfo_rooty() + event.y

            # Scroll frame'in pozisyonunu al
            scroll_x = self.macro_scroll.winfo_rootx()
            scroll_y = self.macro_scroll.winfo_rooty()
            scroll_height = self.macro_scroll.winfo_height()
            scroll_width = self.macro_scroll.winfo_width()

            # Mouse scroll frame içinde mi kontrol et
            if (scroll_x <= x_root <= scroll_x + scroll_width and
                scroll_y <= y_root <= scroll_y + scroll_height):

                # Drop indicator göster
                self.show_drop_indicator(y_root - scroll_y)
            else:
                self.hide_drop_indicator()
        except:
            pass

    def on_drag_release(self, event):
        """Sürükleme bırakıldı"""
        if not self.drag_data["type"]:
            return

        try:
            x_root = event.widget.winfo_rootx() + event.x
            y_root = event.widget.winfo_rooty() + event.y

            # Scroll frame'in pozisyonunu al
            scroll_x = self.macro_scroll.winfo_rootx()
            scroll_y = self.macro_scroll.winfo_rooty()
            scroll_height = self.macro_scroll.winfo_height()
            scroll_width = self.macro_scroll.winfo_width()

            # Mouse scroll frame içinde mi kontrol et
            if (scroll_x <= x_root <= scroll_x + scroll_width and
                scroll_y <= y_root <= scroll_y + scroll_height):

                # Hedef index'i hesapla
                relative_y = y_root - scroll_y
                target_idx = self.calculate_drop_index(relative_y)

                if self.drag_data["type"] == "new":
                    # Yeni aksiyon ekle
                    action_type = self.drag_data["action_type"]
                    if action_type == "sleep":
                        new_action = {"action": "sleep", "ms": 50}
                    else:
                        new_action = {"action": action_type, "key": ""}
                    self.macro_list.insert(target_idx, new_action)

                elif self.drag_data["type"] == "reorder":
                    # Mevcut aksiyonu taşı
                    src_idx = self.drag_data["index"]
                    if src_idx is not None and src_idx != target_idx:
                        item = self.macro_list.pop(src_idx)
                        # Eğer src < target ise, target'ı 1 azalt
                        if src_idx < target_idx:
                            target_idx -= 1
                        self.macro_list.insert(target_idx, item)

                self.refresh_macro_list()
        except Exception as e:
            print(f"Drag release error: {e}")

        self.hide_drop_indicator()
        self.drag_data = {"type": None, "action_type": None, "index": None}

    def calculate_drop_index(self, relative_y):
        """Mouse pozisyonuna göre drop index'i hesapla"""
        children = self.macro_scroll.winfo_children()
        if not children:
            return 0

        row_height = 36  # Yaklaşık satır yüksekliği (32 + padding)
        idx = int(relative_y / row_height)
        return min(max(0, idx), len(self.macro_list))

    def show_drop_indicator(self, relative_y):
        """Drop indicator çizgisini göster"""
        try:
            target_idx = self.calculate_drop_index(relative_y)
            row_height = 36
            indicator_y = target_idx * row_height

            # Eğer indicator yoksa veya parent'ı yok olduysa yeniden oluştur
            if self.drop_indicator is None or not self.drop_indicator.winfo_exists():
                self.drop_indicator = ctk.CTkFrame(self.macro_scroll, fg_color="#00d4ff", height=2)

            self.drop_indicator.place(x=0, y=indicator_y, relwidth=1)
        except:
            pass

    def hide_drop_indicator(self):
        """Drop indicator'ı gizle"""
        if self.drop_indicator:
            try:
                if self.drop_indicator.winfo_exists():
                    self.drop_indicator.place_forget()
            except:
                pass
            self.drop_indicator = None

    def load_preview(self):
        """Mevcut template görselini yükle"""
        try:
            filepath = IMAGES_FOLDER / self.template['file']
            if filepath.exists():
                img = Image.open(filepath)
                img.thumbnail((70, 70))
                self.preview_photo = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self.preview_label.configure(image=self.preview_photo)
            else:
                self.preview_label.configure(text="Görsel\nYok", text_color="#666666")
        except Exception as e:
            self.preview_label.configure(text="Hata", text_color="#ff4757")

    def capture_new_image(self):
        """Yeni görsel yakalamak için ekran yakalama başlat"""
        self.top.withdraw()
        self.top.after(200, self._do_capture)

    def _do_capture(self):
        """Ekran yakalama işlemini başlat"""
        EditTemplateCapture(self.top.master, self)

    def center_window(self):
        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        x = (self.top.winfo_screenwidth() // 2) - (w // 2)
        y = (self.top.winfo_screenheight() // 2) - (h // 2)
        self.top.geometry(f'{w}x{h}+{x}+{y}')

    def capture_key(self):
        CaptureKeyComboDialog(self.top, self)

    def pick_color(self):
        color = colorchooser.askcolor(initialcolor=self.selected_color)
        if color[1]:
            self.selected_color = color[1]
            self.color_preview.configure(fg_color=self.selected_color)

    def save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Uyarı", "İsim boş olamaz!")
            return

        try:
            pre = int(self.pre_entry.get())
            hold = int(self.hold_entry.get())
            post = int(self.post_entry.get())
        except:
            pre = hold = post = 1

        # Yeni görsel varsa kaydet
        if self.new_image is not None:
            filename = f"{name}.png"
            filepath = IMAGES_FOLDER / filename
            try:
                self.new_image.save(filepath, 'PNG')
                self.template['file'] = filename
            except Exception as e:
                messagebox.showerror("Hata", f"Görsel kaydedilemedi: {e}")
                return

        self.template['name'] = name
        self.template['key_combo'] = self.key_combo
        self.template['threshold'] = self.threshold_slider.get()
        self.template['color'] = self.selected_color
        self.template['enabled'] = self.enabled_var.get()
        self.template['timing'] = {"pre_delay": pre, "hold_time": hold, "post_delay": post}

        # Makro bilgisi
        self.template['use_macro'] = self.use_macro_var.get()
        self.template['macro'] = self.macro_list

        self.manager.groups[self.manager.selected_group_index]['templates'][self.index] = self.template
        self.manager.refresh_template_list()
        self.top.destroy()

    def update_preview(self, new_img):
        """Yeni yakalanan görseli önizlemeye yükle"""
        self.new_image = new_img
        try:
            preview = new_img.copy()
            preview.thumbnail((70, 70))
            self.preview_photo = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)
            self.preview_label.configure(image=self.preview_photo)
        except:
            pass


class EditTemplateCapture:
    """Capture new template image for editing"""
    def __init__(self, parent, edit_dialog):
        self.edit_dialog = edit_dialog
        self.screenshot = ImageGrab.grab()
        self.width, self.height = self.screenshot.size

        self.top = tk.Toplevel(parent)
        self.top.title("Bölge Seç")
        self.top.attributes('-fullscreen', True)
        self.top.attributes('-topmost', True)
        self.top.configure(cursor="crosshair")
        self.top.focus_force()
        self.top.grab_set()

        self.canvas = tk.Canvas(self.top, highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.photo = ImageTk.PhotoImage(self.screenshot)
        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

        self.rect = None
        self.start_x = None
        self.start_y = None
        self.is_selecting = False
        self.overlay = None
        self.coord_text = None

        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<Escape>', lambda e: self.cancel())
        self.canvas.bind('<Motion>', self.on_motion)
        self.canvas.focus_set()

        # Talimatlar
        self.canvas.create_rectangle(
            self.width//2 - 200, 30, self.width//2 + 200, 70,
            fill='black', stipple='gray50'
        )
        self.canvas.create_text(
            self.width//2, 50,
            text="Yeni görsel için bölge seç | ESC: İptal",
            font=('Arial', 12, 'bold'), fill='white'
        )

    def on_motion(self, event):
        if not self.is_selecting:
            if self.coord_text:
                self.canvas.delete(self.coord_text)
            self.coord_text = self.canvas.create_text(
                event.x + 15, event.y - 15,
                text=f"X: {event.x}, Y: {event.y}",
                fill='cyan', font=('Arial', 10, 'bold'), anchor=tk.NW
            )

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.is_selecting = True

        if self.rect:
            self.canvas.delete(self.rect)
        if self.overlay:
            self.canvas.delete(self.overlay)
        if self.coord_text:
            self.canvas.delete(self.coord_text)

        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='#00d4ff', width=3, dash=(5, 5)
        )
        self.overlay = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            fill='#00d4ff', stipple='gray25', outline=''
        )

    def on_drag(self, event):
        if self.rect and self.is_selecting:
            self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)
            if self.overlay:
                self.canvas.coords(self.overlay, self.start_x, self.start_y, event.x, event.y)

            width = abs(event.x - self.start_x)
            height = abs(event.y - self.start_y)

            if self.coord_text:
                self.canvas.delete(self.coord_text)
            self.coord_text = self.canvas.create_text(
                event.x + 15, event.y - 15,
                text=f"{width}x{height} px",
                fill='cyan', font=('Arial', 12, 'bold'), anchor=tk.NW
            )

    def on_release(self, event):
        self.is_selecting = False
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)

        if x2 - x1 < 10 or y2 - y1 < 10:
            if self.rect:
                self.canvas.delete(self.rect)
            if self.overlay:
                self.canvas.delete(self.overlay)
            return

        template_img = self.screenshot.crop((x1, y1, x2, y2))
        self.top.destroy()

        # Edit dialog'a yeni görseli gönder
        self.edit_dialog.update_preview(template_img)
        self.edit_dialog.top.deiconify()

    def cancel(self):
        self.top.destroy()
        self.edit_dialog.top.deiconify()


# ==================== MAIN ====================

def main():
    # Required for Windows multiprocessing
    multiprocessing.freeze_support()

    root = ctk.CTk()
    app = ConfigManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
