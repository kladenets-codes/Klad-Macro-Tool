"""
Klad Macro Tool - Group Dialogs
Dialog classes for group management (Add, Edit, Key Capture, Region Select)
"""

import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk
from PIL import ImageTk, ImageGrab
import keyboard
import uuid

from core.keyboard_utils import get_physical_key_name


class AddGroupDialog:
    """Dialog for adding new group"""
    def __init__(self, parent, manager):
        self.manager = manager
        self.selected_key = None
        self.spam_key = None

        self.top = ctk.CTkToplevel(parent)
        self.top.title("Yeni Grup Ekle")
        self.top.geometry("500x650")
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

        # Notes
        notes_frame = ctk.CTkFrame(main, fg_color="#1a1a1a", corner_radius=10)
        notes_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(notes_frame, text="Notlar:", font=ctk.CTkFont(size=12),
                    text_color="#888888").pack(anchor="w", padx=15, pady=(10, 5))
        self.notes_entry = ctk.CTkTextbox(notes_frame, width=420, height=60,
                                          fg_color="#0d0d0d", corner_radius=6)
        self.notes_entry.pack(padx=15, pady=(0, 10))

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
        # Ana pencereyi ve dialog'u gizle
        self.manager.root.withdraw()
        self.top.withdraw()
        self.top.after(300, lambda: SelectRegionDialogSimple(self.top.master, self))

    def save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Uyarı", "Grup adı boş olamaz!")
            return

        if not self.selected_key:
            messagebox.showwarning("Uyarı", "Start/Stop tuşu seçmelisiniz!")
            return

        # Get spam timing
        try:
            pre = int(self.pre_entry.get()) if self.pre_entry.get() else 1
            hold = int(self.hold_entry.get()) if self.hold_entry.get() else 1
            post = int(self.post_entry.get()) if self.post_entry.get() else 1
        except:
            pre = hold = post = 1

        new_group = {
            "type": "group",
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
            "notes": self.notes_entry.get("1.0", "end-1c").strip(),
            "templates": []
        }

        # Seçili item'ı kontrol et - eğer klasör ise içine ekle
        selected_item = self.manager.get_selected_item()
        if selected_item and selected_item.get('type') == 'folder':
            # Klasörün içine ekle
            if 'items' not in selected_item:
                selected_item['items'] = []
            selected_item['items'].append(new_group)
            # Klasörü expand et
            selected_item['expanded'] = True
        else:
            # Root seviyesine ekle
            self.manager.groups.append(new_group)

        self.manager.refresh_group_list()
        self.manager.save_config(silent=True)
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
        self.top.geometry("500x650")
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

        # Notes
        notes_frame = ctk.CTkFrame(main, fg_color="#1a1a1a", corner_radius=10)
        notes_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(notes_frame, text="Notlar:", font=ctk.CTkFont(size=12),
                    text_color="#888888").pack(anchor="w", padx=15, pady=(10, 5))
        self.notes_entry = ctk.CTkTextbox(notes_frame, width=420, height=60,
                                          fg_color="#0d0d0d", corner_radius=6)
        self.notes_entry.pack(padx=15, pady=(0, 10))
        # Mevcut notları yükle
        if self.group.get('notes'):
            self.notes_entry.insert("1.0", self.group.get('notes', ''))

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
        # Ana pencereyi ve dialog'u gizle
        self.manager.root.withdraw()
        self.top.withdraw()
        self.top.after(300, lambda: SelectRegionDialogSimple(self.top.master, self))

    def save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Uyarı", "Grup adı boş olamaz!")
            return

        if not self.selected_key:
            messagebox.showwarning("Uyarı", "Start/Stop tuşu seçmelisiniz!")
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
        self.group['notes'] = self.notes_entry.get("1.0", "end-1c").strip()

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
        self.top.geometry("350x160")
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

        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack()

        self.ok_btn = ctk.CTkButton(btn_frame, text="Tamam", width=80, height=32, fg_color="#00ff88",
                                    text_color="#000000", state="disabled", command=self.confirm)
        self.ok_btn.pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="Sıfırla", width=80, height=32, fg_color="#ff6b6b",
                     text_color="#ffffff", command=self.reset).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="İptal", width=80, height=32, fg_color="#333333",
                     command=self.cancel).pack(side="left")

        self.selected_key = None
        keyboard.hook(self.on_key)

    def center_window(self):
        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        x = (self.top.winfo_screenwidth() // 2) - (w // 2)
        y = (self.top.winfo_screenheight() // 2) - (h // 2)
        self.top.geometry(f'{w}x{h}+{x}+{y}')

    def on_key(self, event):
        if event.event_type == 'down':
            key = get_physical_key_name(event)
            self.selected_key = key
            self.key_label.configure(text=key)
            self.ok_btn.configure(state="normal")

    def reset(self):
        """Yakalanan tuşu sıfırla"""
        self.selected_key = None
        self.key_label.configure(text="Bekleniyor...")
        self.ok_btn.configure(state="disabled")

    def confirm(self):
        keyboard.unhook_all()
        if self.selected_key:
            if self.key_type == "toggle":
                self.caller.selected_key = self.selected_key
                self.caller.key_btn.configure(text=self.selected_key)
            else:
                self.caller.spam_key = self.selected_key
                self.caller.spam_key_btn.configure(text=self.selected_key)
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
        # Ana pencereyi ve dialog'u geri göster
        self.caller.manager.root.deiconify()
        self.caller.top.deiconify()

    def cancel(self):
        self.top.destroy()
        # Ana pencereyi ve dialog'u geri göster
        self.caller.manager.root.deiconify()
        self.caller.top.deiconify()
