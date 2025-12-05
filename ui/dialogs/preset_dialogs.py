"""
Klad Macro Tool - Preset Dialogs
Export, Import and Preset management dialogs
"""

import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path

from core.export_import import generate_export_code, parse_import_code


class ExportGroupDialog:
    """Dialog for exporting a group as text"""
    def __init__(self, parent, group, images_folder: Path):
        self.group = group
        self.images_folder = images_folder

        self.top = ctk.CTkToplevel(parent)
        self.top.title(f"Export: {group['name']}")
        self.top.geometry("550x500")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)
        self.top.after(10, self.center_window)

        main = ctk.CTkFrame(self.top, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)

        ctk.CTkLabel(main, text="Export Grup", font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="#00d4ff").pack(pady=(0, 10))

        ctk.CTkLabel(main, text="Bu kodu kopyalayip paylasabilirsiniz:",
                    font=ctk.CTkFont(size=12), text_color="#888888").pack(anchor="w", pady=(0, 10))

        # Export text area
        self.export_text = ctk.CTkTextbox(main, width=500, height=350,
                                          fg_color="#0d0d0d", corner_radius=8,
                                          font=ctk.CTkFont(family="Consolas", size=11))
        self.export_text.pack(fill="both", expand=True, pady=(0, 15))

        # Generate export text
        export_data = self.generate_export()
        self.export_text.insert("1.0", export_data)

        # Buttons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(btn_frame, text="Kopyala", width=100, height=35, fg_color="#00ff88",
                     hover_color="#00cc6e", text_color="#000000",
                     font=ctk.CTkFont(weight="bold"), command=self.copy_to_clipboard).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="Kapat", width=80, height=35, fg_color="#333333",
                     hover_color="#444444", command=self.top.destroy).pack(side="left")

    def center_window(self):
        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        x = (self.top.winfo_screenwidth() // 2) - (w // 2)
        y = (self.top.winfo_screenheight() // 2) - (h // 2)
        self.top.geometry(f'{w}x{h}+{x}+{y}')

    def generate_export(self):
        """Generate export text from group data"""
        return generate_export_code(self.group, self.images_folder)

    def copy_to_clipboard(self):
        """Copy export text to clipboard"""
        text = self.export_text.get("1.0", "end-1c")
        self.top.clipboard_clear()
        self.top.clipboard_append(text)
        messagebox.showinfo("Basarili", "Export kodu panoya kopyalandi!")


class ImportGroupDialog:
    """Dialog for importing a group from text"""
    def __init__(self, parent, manager, images_folder: Path):
        self.manager = manager
        self.images_folder = images_folder

        self.top = ctk.CTkToplevel(parent)
        self.top.title("Import Grup")
        self.top.geometry("550x500")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)
        self.top.after(10, self.center_window)

        main = ctk.CTkFrame(self.top, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)

        ctk.CTkLabel(main, text="Import Grup", font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="#00d4ff").pack(pady=(0, 10))

        ctk.CTkLabel(main, text="Export kodunu buraya yapistirin:",
                    font=ctk.CTkFont(size=12), text_color="#888888").pack(anchor="w", pady=(0, 10))

        # Import text area
        self.import_text = ctk.CTkTextbox(main, width=500, height=350,
                                          fg_color="#0d0d0d", corner_radius=8,
                                          font=ctk.CTkFont(family="Consolas", size=11))
        self.import_text.pack(fill="both", expand=True, pady=(0, 15))

        # Buttons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(btn_frame, text="Import Et", width=100, height=35, fg_color="#00ff88",
                     hover_color="#00cc6e", text_color="#000000",
                     font=ctk.CTkFont(weight="bold"), command=self.do_import).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="Yapistir", width=80, height=35, fg_color="#5a4a27",
                     hover_color="#7a6a47", command=self.paste_from_clipboard).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="Iptal", width=80, height=35, fg_color="#333333",
                     hover_color="#444444", command=self.top.destroy).pack(side="left")

    def center_window(self):
        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        x = (self.top.winfo_screenwidth() // 2) - (w // 2)
        y = (self.top.winfo_screenheight() // 2) - (h // 2)
        self.top.geometry(f'{w}x{h}+{x}+{y}')

    def paste_from_clipboard(self):
        """Paste from clipboard"""
        try:
            text = self.top.clipboard_get()
            self.import_text.delete("1.0", "end")
            self.import_text.insert("1.0", text)
        except:
            messagebox.showwarning("Uyari", "Panoda metin yok!")

    def do_import(self):
        """Import group from text"""
        text = self.import_text.get("1.0", "end-1c").strip()

        group, error = parse_import_code(text, self.images_folder)

        if error:
            messagebox.showerror("Hata", error)
            return

        # Grubu ekle
        self.manager.groups.append(group)
        self.manager.refresh_group_list()
        self.manager.add_log(f"Grup import edildi: {group['name']}", "INFO")

        messagebox.showinfo("Basarili", f"'{group['name']}' grubu basariyla import edildi!")
        self.top.destroy()


class PresetDialog:
    """Dialog for managing and importing presets"""
    def __init__(self, parent, manager, images_folder: Path):
        self.manager = manager
        self.images_folder = images_folder
        self.selected_preset_index = None

        self.top = ctk.CTkToplevel(parent)
        self.top.title("Presets")
        self.top.geometry("700x550")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)
        self.top.after(10, self.center_window)

        main = ctk.CTkFrame(self.top, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=15)

        # Header
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(header, text="Presets", font=ctk.CTkFont(size=20, weight="bold"),
                    text_color="#00d4ff").pack(side="left")

        # Add preset button
        ctk.CTkButton(header, text="+ Yeni Preset", width=120, height=32,
                     fg_color="#4a3a6a", hover_color="#6a5a8a",
                     font=ctk.CTkFont(weight="bold"),
                     command=self.add_preset).pack(side="right")

        # Content area - split view
        content = ctk.CTkFrame(main, fg_color="transparent")
        content.pack(fill="both", expand=True)

        # Left panel - Preset list
        left_panel = ctk.CTkFrame(content, fg_color="#1a1a1a", corner_radius=10, width=220)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        left_panel.pack_propagate(False)

        ctk.CTkLabel(left_panel, text="Preset Listesi", font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="#888888").pack(pady=(15, 10), padx=15, anchor="w")

        # Preset listbox frame
        list_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.preset_listbox = ctk.CTkScrollableFrame(list_frame, fg_color="#0d0d0d", corner_radius=8)
        self.preset_listbox.pack(fill="both", expand=True)

        # Right panel - Preset details
        right_panel = ctk.CTkFrame(content, fg_color="#1a1a1a", corner_radius=10)
        right_panel.pack(side="right", fill="both", expand=True)

        self.details_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        self.details_frame.pack(fill="both", expand=True, padx=20, pady=15)

        # Placeholder
        self.placeholder_label = ctk.CTkLabel(
            self.details_frame,
            text="Bir preset secin veya yeni ekleyin",
            font=ctk.CTkFont(size=14),
            text_color="#666666"
        )
        self.placeholder_label.pack(expand=True)

        # Detail widgets (hidden initially)
        self.detail_widgets_frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")

        # Preset name
        ctk.CTkLabel(self.detail_widgets_frame, text="Preset Adi:", font=ctk.CTkFont(size=12),
                    text_color="#888888").pack(anchor="w")
        self.name_entry = ctk.CTkEntry(self.detail_widgets_frame, height=35, fg_color="#0d0d0d",
                                       font=ctk.CTkFont(size=13))
        self.name_entry.pack(fill="x", pady=(5, 15))

        # Info/description
        ctk.CTkLabel(self.detail_widgets_frame, text="Aciklama:", font=ctk.CTkFont(size=12),
                    text_color="#888888").pack(anchor="w")
        self.info_text = ctk.CTkTextbox(self.detail_widgets_frame, height=60, fg_color="#0d0d0d",
                                        font=ctk.CTkFont(size=12))
        self.info_text.pack(fill="x", pady=(5, 15))

        # Import code
        ctk.CTkLabel(self.detail_widgets_frame, text="Import Kodu:", font=ctk.CTkFont(size=12),
                    text_color="#888888").pack(anchor="w")
        self.code_text = ctk.CTkTextbox(self.detail_widgets_frame, height=180, fg_color="#0d0d0d",
                                        font=ctk.CTkFont(family="Consolas", size=11))
        self.code_text.pack(fill="both", expand=True, pady=(5, 15))

        # Buttons
        btn_frame = ctk.CTkFrame(self.detail_widgets_frame, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(btn_frame, text="Import Et", width=100, height=35,
                     fg_color="#00ff88", hover_color="#00cc6e", text_color="#000000",
                     font=ctk.CTkFont(weight="bold"),
                     command=self.import_preset).pack(side="left", padx=(0, 10))

        ctk.CTkButton(btn_frame, text="Kaydet", width=80, height=35,
                     fg_color="#4a3a6a", hover_color="#6a5a8a",
                     command=self.save_preset).pack(side="left", padx=(0, 10))

        ctk.CTkButton(btn_frame, text="Sil", width=60, height=35,
                     fg_color="#8B0000", hover_color="#a52a2a",
                     command=self.delete_preset).pack(side="left")

        # Bottom close button
        ctk.CTkButton(main, text="Kapat", width=100, height=35,
                     fg_color="#333333", hover_color="#444444",
                     command=self.top.destroy).pack(pady=(15, 0))

        self.refresh_preset_list()

    def center_window(self):
        self.top.update_idletasks()
        w, h = self.top.winfo_width(), self.top.winfo_height()
        x = (self.top.winfo_screenwidth() // 2) - (w // 2)
        y = (self.top.winfo_screenheight() // 2) - (h // 2)
        self.top.geometry(f'{w}x{h}+{x}+{y}')

    def refresh_preset_list(self):
        """Refresh the preset list"""
        for widget in self.preset_listbox.winfo_children():
            widget.destroy()

        for i, preset in enumerate(self.manager.presets):
            btn = ctk.CTkButton(
                self.preset_listbox,
                text=preset.get('name', 'Unnamed'),
                height=36,
                corner_radius=6,
                fg_color="#2a2a2a" if i != self.selected_preset_index else "#4a3a6a",
                hover_color="#3a3a3a",
                anchor="w",
                font=ctk.CTkFont(size=12),
                command=lambda idx=i: self.select_preset(idx)
            )
            btn.pack(fill="x", pady=2)

    def select_preset(self, index):
        """Select a preset and show details"""
        self.selected_preset_index = index
        self.refresh_preset_list()

        # Show detail widgets
        self.placeholder_label.pack_forget()
        self.detail_widgets_frame.pack(fill="both", expand=True)

        # Load preset data
        preset = self.manager.presets[index]
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, preset.get('name', ''))

        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", preset.get('info', ''))

        self.code_text.delete("1.0", "end")
        self.code_text.insert("1.0", preset.get('import_code', ''))

    def add_preset(self):
        """Add a new preset"""
        new_preset = {
            "name": f"Yeni Preset {len(self.manager.presets) + 1}",
            "info": "",
            "import_code": ""
        }
        self.manager.presets.append(new_preset)
        self.manager.save_config(silent=True)
        self.refresh_preset_list()
        self.select_preset(len(self.manager.presets) - 1)

    def save_preset(self):
        """Save current preset"""
        if self.selected_preset_index is None:
            return

        preset = self.manager.presets[self.selected_preset_index]
        preset['name'] = self.name_entry.get().strip() or "Unnamed"
        preset['info'] = self.info_text.get("1.0", "end-1c").strip()
        preset['import_code'] = self.code_text.get("1.0", "end-1c").strip()

        self.manager.save_config(silent=True)
        self.refresh_preset_list()
        messagebox.showinfo("Basarili", "Preset kaydedildi!")

    def delete_preset(self):
        """Delete selected preset"""
        if self.selected_preset_index is None:
            return

        preset = self.manager.presets[self.selected_preset_index]
        if messagebox.askyesno("Onayla", f"'{preset.get('name', 'Preset')}' silinsin mi?"):
            self.manager.presets.pop(self.selected_preset_index)
            self.selected_preset_index = None
            self.manager.save_config(silent=True)
            self.refresh_preset_list()

            # Hide details
            self.detail_widgets_frame.pack_forget()
            self.placeholder_label.pack(expand=True)

    def import_preset(self):
        """Import the preset's group"""
        if self.selected_preset_index is None:
            return

        preset = self.manager.presets[self.selected_preset_index]
        import_code = preset.get('import_code', '').strip()

        if not import_code:
            messagebox.showwarning("Uyari", "Bu preset'in import kodu bos!")
            return

        group, error = parse_import_code(import_code, self.images_folder)

        if error:
            messagebox.showerror("Hata", error)
            return

        # Grubu ekle
        self.manager.groups.append(group)
        self.manager.refresh_group_list()
        self.manager.add_log(f"Preset'ten grup import edildi: {group['name']}", "INFO")

        messagebox.showinfo("Basarili", f"'{group['name']}' grubu preset'ten import edildi!")
