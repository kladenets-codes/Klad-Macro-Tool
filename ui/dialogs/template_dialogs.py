"""
Klad Macro Tool - Template Dialogs
Dialog classes for template management (Add, Edit, Capture, Key Combo)
"""

import customtkinter as ctk
from tkinter import messagebox, colorchooser
import tkinter as tk
from PIL import Image, ImageTk, ImageGrab
import keyboard
import time
from pathlib import Path

from core.keyboard_utils import get_physical_key_name
from core.constants import DEFAULT_TRIGGER_CONDITION, TRIGGER_CONDITION_FOUND, TRIGGER_CONDITION_NOT_FOUND

# Images folder path
IMAGES_FOLDER = Path(__file__).parent.parent.parent / "images"


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
        # Ana pencereyi ve bu dialog'u gizle
        self.manager.root.withdraw()
        self.top.withdraw()
        self.top.after(300, self.do_capture)

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

        # ESC için hem pencereye hem canvas'a binding ekle
        self.top.bind('<Escape>', lambda e: self.cancel())

        # Focus'u zorla
        self.canvas.focus_set()
        self.top.update()
        self.canvas.focus_force()

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
        # Ana pencereyi ve add dialog'u geri göster
        self.add_dialog.manager.root.deiconify()
        self.add_dialog.top.deiconify()


class TemplateFinalizeDialog:
    """Finalize template with name and key"""
    def __init__(self, parent, add_dialog, template_img):
        self.add_dialog = add_dialog
        self.manager = add_dialog.manager
        self.template_img = template_img
        self.key_combo = None
        self.selected_color = "#00ff88"

        # Ana pencereyi geri göster (capture tamamlandı)
        self.manager.root.deiconify()

        self.top = ctk.CTkToplevel(parent)
        self.top.title("Template Detayları")
        self.top.geometry("450x530")
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
        # Get selected group (folder-safe way)
        selected_group = self.manager.get_selected_group()
        template_count = len(selected_group.get('templates', [])) + 1 if selected_group else 1
        self.name_entry.insert(0, f"template_{template_count}")

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

        # Trigger Condition
        trigger_row = ctk.CTkFrame(main, fg_color="transparent")
        trigger_row.pack(fill="x", pady=8)
        ctk.CTkLabel(trigger_row, text="Tetikleme:", width=70).pack(side="left")
        self.trigger_var = ctk.StringVar(value=DEFAULT_TRIGGER_CONDITION)
        self.trigger_menu = ctk.CTkOptionMenu(
            trigger_row,
            values=["Görsel bulunduğunda", "Görsel bulunmadığında"],
            variable=self.trigger_var,
            width=180,
            height=28,
            fg_color="#333333",
            button_color="#444444",
            button_hover_color="#555555",
            command=self._on_trigger_change
        )
        self.trigger_menu.pack(side="left", padx=10)
        self.trigger_menu.set("Görsel bulunduğunda")

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

    def _on_trigger_change(self, value):
        """Tetikleme koşulu değiştiğinde çağrılır"""
        if value == "Görsel bulunduğunda":
            self.trigger_var.set(TRIGGER_CONDITION_FOUND)
        else:
            self.trigger_var.set(TRIGGER_CONDITION_NOT_FOUND)

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

        # Get trigger condition
        trigger_display = self.trigger_menu.get()
        trigger_condition = TRIGGER_CONDITION_FOUND if trigger_display == "Görsel bulunduğunda" else TRIGGER_CONDITION_NOT_FOUND

        new_template = {
            "name": name,
            "file": filename,
            "enabled": True,
            "threshold": self.threshold_slider.get(),
            "key_combo": self.key_combo,
            "color": self.selected_color,
            "timing": {"pre_delay": pre, "hold_time": hold, "post_delay": post},
            "trigger_condition": trigger_condition,
            "use_macro": False,
            "macro": []
        }

        # Get selected group (folder-safe way)
        selected_group = self.manager.get_selected_group()
        if selected_group is None:
            messagebox.showerror("Hata", "Seçili grup bulunamadı!")
            return

        if 'templates' not in selected_group:
            selected_group['templates'] = []

        selected_group['templates'].append(new_template)
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
        self.top.geometry("380x180")
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
        ctk.CTkButton(btn_frame, text="Sıfırla", width=80, height=32, fg_color="#ff6b6b",
                     text_color="#ffffff", command=self.reset).pack(side="left", padx=(0, 10))
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
        if event.event_type == 'down':
            # Scan code'dan fiziksel tuş adını al (shift ile değişen karakterleri önler)
            key_name = get_physical_key_name(event)
            if key_name and key_name not in self.captured_keys:
                self.captured_keys.append(key_name)
                combo = ' + '.join(self.captured_keys)
                self.key_label.configure(text=combo)
                self.ok_btn.configure(state="normal")

    def reset(self):
        """Yakalanan tuşları sıfırla"""
        self.captured_keys = []
        self.key_label.configure(text="Bekleniyor...")
        self.ok_btn.configure(state="disabled")

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

        # Trigger Condition
        trigger_row = ctk.CTkFrame(main_scroll, fg_color="transparent")
        trigger_row.pack(fill="x", pady=8)
        ctk.CTkLabel(trigger_row, text="Tetikleme:", width=80).pack(side="left")
        current_trigger = template.get('trigger_condition', DEFAULT_TRIGGER_CONDITION)
        current_display = "Görsel bulunduğunda" if current_trigger == TRIGGER_CONDITION_FOUND else "Görsel bulunmadığında"
        self.trigger_var = ctk.StringVar(value=current_trigger)
        self.trigger_menu = ctk.CTkOptionMenu(
            trigger_row,
            values=["Görsel bulunduğunda", "Görsel bulunmadığında"],
            width=180,
            height=28,
            fg_color="#333333",
            button_color="#444444",
            button_hover_color="#555555",
            command=self._on_trigger_change
        )
        self.trigger_menu.pack(side="left", padx=5)
        self.trigger_menu.set(current_display)

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
        # Ana pencereyi ve dialog'u gizle
        self.manager.root.withdraw()
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

    def _on_trigger_change(self, value):
        """Tetikleme koşulu değiştiğinde çağrılır"""
        if value == "Görsel bulunduğunda":
            self.trigger_var.set(TRIGGER_CONDITION_FOUND)
        else:
            self.trigger_var.set(TRIGGER_CONDITION_NOT_FOUND)

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

        # Trigger condition
        trigger_display = self.trigger_menu.get()
        self.template['trigger_condition'] = TRIGGER_CONDITION_FOUND if trigger_display == "Görsel bulunduğunda" else TRIGGER_CONDITION_NOT_FOUND

        # Makro bilgisi
        self.template['use_macro'] = self.use_macro_var.get()
        self.template['macro'] = self.macro_list

        # Get selected group (folder-safe way)
        selected_group = self.manager.get_selected_group()
        if selected_group is None:
            messagebox.showerror("Hata", "Seçili grup bulunamadı!")
            return

        selected_group['templates'][self.index] = self.template
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

        # ESC için hem pencereye hem canvas'a binding ekle
        self.top.bind('<Escape>', lambda e: self.cancel())

        # Focus'u zorla
        self.canvas.focus_set()
        self.top.update()
        self.canvas.focus_force()

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

        # Ana pencereyi ve edit dialog'u geri göster
        self.edit_dialog.manager.root.deiconify()
        # Edit dialog'a yeni görseli gönder
        self.edit_dialog.update_preview(template_img)
        self.edit_dialog.top.deiconify()

    def cancel(self):
        self.top.destroy()
        # Ana pencereyi ve edit dialog'u geri göster
        self.edit_dialog.manager.root.deiconify()
        self.edit_dialog.top.deiconify()
