"""
Klad Macro Tool - Update Dialog
Güncelleme bildirimi ve indirme popup'ı
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading


class UpdateDialog(ctk.CTkToplevel):
    """Güncelleme mevcut olduğunda gösterilen popup"""

    def __init__(self, parent, commit_info, updater_module):
        super().__init__(parent)

        self.commit_info = commit_info
        self.updater = updater_module
        self.download_in_progress = False

        # Pencere ayarları
        self.title("Güncelleme Mevcut")
        self.geometry("450x320")
        self.resizable(False, False)

        # Modal yap
        self.transient(parent)
        self.grab_set()

        # Ortala
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 450) // 2
        y = (self.winfo_screenheight() - 320) // 2
        self.geometry(f"+{x}+{y}")

        # Renkler
        self.colors = {
            "bg": "#1a1a1a",
            "card": "#242424",
            "accent": "#00d4ff",
            "success": "#00ff88",
            "text": "#ffffff",
            "text_secondary": "#888888"
        }

        self.configure(fg_color=self.colors["bg"])

        self.build_ui()

    def build_ui(self):
        """UI oluştur"""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color=self.colors["card"], corner_radius=0)
        header_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            header_frame,
            text="🔄 Yeni Güncelleme Mevcut!",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.colors["accent"]
        ).pack(pady=15)

        # Content
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20)

        # Commit bilgileri
        info_frame = ctk.CTkFrame(content_frame, fg_color=self.colors["card"], corner_radius=10)
        info_frame.pack(fill="x", pady=(0, 15))

        # Mevcut commit
        current_commit = self.updater.get_current_commit()
        ctk.CTkLabel(
            info_frame,
            text=f"Mevcut: {current_commit}",
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text_secondary"]
        ).pack(anchor="w", padx=15, pady=(10, 2))

        # Yeni commit
        new_commit = self.commit_info.get("sha", "")[:7]
        ctk.CTkLabel(
            info_frame,
            text=f"Yeni: {new_commit}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.colors["success"]
        ).pack(anchor="w", padx=15, pady=(0, 5))

        # Commit mesajı
        commit_msg = self.commit_info.get("message", "").split("\n")[0][:60]
        if len(self.commit_info.get("message", "")) > 60:
            commit_msg += "..."

        ctk.CTkLabel(
            info_frame,
            text=f"📝 {commit_msg}",
            font=ctk.CTkFont(size=11),
            text_color=self.colors["text"],
            wraplength=380
        ).pack(anchor="w", padx=15, pady=(5, 10))

        # Progress bar (başta gizli)
        self.progress_frame = ctk.CTkFrame(content_frame, fg_color="transparent")

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            width=380,
            height=15,
            corner_radius=5,
            fg_color=self.colors["card"],
            progress_color=self.colors["accent"]
        )
        self.progress_bar.pack(pady=(0, 5))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="İndiriliyor...",
            font=ctk.CTkFont(size=11),
            text_color=self.colors["text_secondary"]
        )
        self.progress_label.pack()

        # Butonlar
        btn_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))

        self.update_btn = ctk.CTkButton(
            btn_frame,
            text="Güncelle",
            width=130,
            height=40,
            corner_radius=8,
            fg_color=self.colors["success"],
            hover_color="#00cc6e",
            text_color="#000000",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.start_update
        )
        self.update_btn.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="GitHub'da Gör",
            width=130,
            height=40,
            corner_radius=8,
            fg_color=self.colors["card"],
            hover_color="#333333",
            font=ctk.CTkFont(size=13),
            command=self.open_github
        ).pack(side="left", padx=(0, 10))

        self.skip_btn = ctk.CTkButton(
            btn_frame,
            text="Atla",
            width=80,
            height=40,
            corner_radius=8,
            fg_color="transparent",
            hover_color="#333333",
            text_color=self.colors["text_secondary"],
            font=ctk.CTkFont(size=12),
            command=self.destroy
        )
        self.skip_btn.pack(side="right")

    def start_update(self):
        """Güncelleme işlemini başlat"""
        if self.download_in_progress:
            return

        self.download_in_progress = True
        self.update_btn.configure(state="disabled", text="İndiriliyor...")
        self.skip_btn.configure(state="disabled")

        # Progress bar'ı göster
        self.progress_frame.pack(fill="x", pady=(0, 10))

        # Arka planda indir
        thread = threading.Thread(target=self.download_thread)
        thread.daemon = True
        thread.start()

    def download_thread(self):
        """İndirme işlemini arka planda yap"""
        try:
            def progress_callback(downloaded, total):
                if total > 0:
                    progress = downloaded / total
                    self.after(0, lambda: self.update_progress(progress, downloaded, total))

            zip_path = self.updater.download_update(self.commit_info, progress_callback)

            if zip_path:
                self.after(0, lambda: self.progress_label.configure(text="Kurulum yapılıyor..."))

                success = self.updater.extract_and_install(zip_path)

                if success:
                    # version.txt'yi yeni commit hash ile güncelle
                    new_commit = self.commit_info.get("sha", "")
                    self.updater.update_version_file(new_commit)

                    self.after(0, self.show_restart_dialog)
                else:
                    self.after(0, lambda: self.show_error("Kurulum başarısız oldu!"))
            else:
                self.after(0, lambda: self.show_error("İndirme başarısız oldu!"))

        except Exception as e:
            self.after(0, lambda: self.show_error(f"Hata: {str(e)}"))

    def update_progress(self, progress, downloaded, total):
        """Progress bar'ı güncelle"""
        self.progress_bar.set(progress)
        if total > 0:
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self.progress_label.configure(text=f"İndiriliyor... {mb_downloaded:.1f} / {mb_total:.1f} MB")

    def show_restart_dialog(self):
        """Başarılı güncelleme sonrası otomatik yeniden başlat"""
        self.progress_label.configure(text="Yeniden başlatılıyor...")
        self.update()

        # 1 saniye bekle ve yeniden başlat
        self.after(1000, self.do_restart)

    def do_restart(self):
        """Uygulamayı yeniden başlat"""
        self.updater.restart_application()

    def show_error(self, message):
        """Hata mesajı göster"""
        self.download_in_progress = False
        self.update_btn.configure(state="normal", text="Tekrar Dene")
        self.skip_btn.configure(state="normal")
        self.progress_frame.pack_forget()
        messagebox.showerror("Hata", message)

    def open_github(self):
        """GitHub sayfasını aç"""
        self.updater.open_github_page()


def show_update_dialog_if_available(parent, check_async=True):
    """
    Güncelleme kontrolü yap ve varsa dialog göster.
    check_async: True ise arka planda kontrol et
    """
    from core import updater

    def check_and_show():
        has_update, commit_info = updater.check_for_updates()
        if has_update and commit_info:
            parent.after(0, lambda: UpdateDialog(parent, commit_info, updater))

    if check_async:
        thread = threading.Thread(target=check_and_show)
        thread.daemon = True
        thread.start()
    else:
        check_and_show()
