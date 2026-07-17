"""
Sintelis Utility — Portable Desktop App
Import langsung dari app.py (single source of truth).
PyInstaller bundle Tesseract + poppler.
"""
import os
import sys
import threading
import zipfile
from io import BytesIO
from tkinter import filedialog, messagebox
from pathlib import Path

# Pastikan bisa import app.py (baik running langsung maupun dari PyInstaller bundle)
if getattr(sys, 'frozen', False):
    BASE = sys._MEIPASS
else:
    BASE = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE)

import customtkinter as ctk
from app import process_pdf_ocr, detect_doc, build_filename, process_pdf_entries, read_input_file

# ── Constants ──────────────────────────────────────────
APP_VERSION = "1.0.0"
APP_NAME = "Sintelis Utility"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class PortableApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("920x620")
        self.minsize(800, 500)

        # ── State ──
        self.pdf_files: list[tuple[str, bytes]] = []  # (name, bytes)
        self.zip_data: bytes | None = None
        self.processed_files: list[str] = []
        self.errors: list[str] = []

        # ── UI ──
        self._build_ui()

        # ── Cek update (async) ──
        self.after(2000, self._check_update_async)

    def _build_ui(self):
        # ── Main grid ──
        self.grid_columnconfigure(0, weight=0, minsize=280)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Kiri: Upload ──
        left = ctk.CTkFrame(self, corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(left, text="📁 Upload PDF", font=("Segoe UI", 16, "bold")).pack(pady=(12, 4))

        self.drop_frame = ctk.CTkFrame(left, fg_color="transparent", border_width=2,
                                        border_color="#3a7ebf", corner_radius=10)
        self.drop_frame.pack(fill="x", padx=12, pady=4)
        self.drop_label = ctk.CTkLabel(self.drop_frame, text="Drop PDF di sini\natau", font=("Segoe UI", 12))
        self.drop_label.pack(pady=(14, 2))
        ctk.CTkButton(self.drop_frame, text="Pilih File", command=self._pick_files,
                       font=("Segoe UI", 12)).pack(pady=(0, 14))

        # Bind drag-drop
        self.drop_frame.bind("<Button-1>", lambda e: self._pick_files())
        self.drop_label.bind("<Button-1>", lambda e: self._pick_files())

        # File list
        self.file_listbox = ctk.CTkTextbox(left, height=140, font=("Consolas", 11))
        self.file_listbox.pack(fill="both", expand=True, padx=12, pady=6)
        self.file_listbox.configure(state="disabled")

        # Tombol bawah
        btn_frame = ctk.CTkFrame(left, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(4, 10))

        self.btn_clear = ctk.CTkButton(btn_frame, text="🗑 Hapus", command=self._clear_files,
                                        fg_color="#d35b5b", hover_color="#b04444", font=("Segoe UI", 12))
        self.btn_clear.pack(side="left", padx=(0, 4))

        self.btn_process = ctk.CTkButton(btn_frame, text="🔄 Proses", command=self._process_thread,
                                          font=("Segoe UI", 13, "bold"))
        self.btn_process.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # ── Kanan: Hasil ──
        right = ctk.CTkFrame(self, corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # Notif update
        self.update_banner = ctk.CTkLabel(right, text="", fg_color="#2d7a2d", corner_radius=6,
                                           font=("Segoe UI", 11))
        self.update_banner.grid(row=0, column=0, sticky="ew", pady=(0, 6), padx=2)
        self.update_banner.grid_remove()

        # Tab view
        self.tab_view = ctk.CTkTabview(right, corner_radius=8)
        self.tab_view.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        self.tab_view._segmented_button.configure(font=("Segoe UI", 11))

        tab_success = self.tab_view.add("✅ Berhasil")
        tab_error = self.tab_view.add("⚠️ Warning/Error")
        tab_log = self.tab_view.add("📋 Log")

        # Tab Success
        self.success_text = ctk.CTkTextbox(tab_success, font=("Consolas", 12))
        self.success_text.pack(fill="both", expand=True, padx=4, pady=4)
        self.success_text.configure(state="disabled")

        # Tab Error
        self.error_text = ctk.CTkTextbox(tab_error, font=("Consolas", 12))
        self.error_text.pack(fill="both", expand=True, padx=4, pady=4)
        self.error_text.configure(state="disabled")

        # Export CSV button in error tab
        ctk.CTkButton(tab_error, text="📊 Export CSV", command=self._export_csv,
                       font=("Segoe UI", 11)).pack(pady=4)

        # Tab Log
        self.log_text = ctk.CTkTextbox(tab_log, font=("Consolas", 11))
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)
        self.log_text.configure(state="disabled")

        # ── Bottom bar ──
        bottom = ctk.CTkFrame(self, corner_radius=8, height=44)
        bottom.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        bottom.grid_columnconfigure(1, weight=1)

        self.progress = ctk.CTkProgressBar(bottom, height=14, corner_radius=4)
        self.progress.grid(row=0, column=0, columnspan=3, sticky="ew", padx=8, pady=(6, 0))
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(bottom, text="Siap", font=("Segoe UI", 11))
        self.status_label.grid(row=1, column=0, sticky="w", padx=8, pady=(2, 4))

        self.btn_download = ctk.CTkButton(bottom, text="📥 Download ZIP", command=self._save_zip,
                                           font=("Segoe UI", 12, "bold"))
        self.btn_download.grid(row=1, column=1, padx=4, pady=(2, 4))
        self.btn_download.configure(state="disabled")

        self.btn_open = ctk.CTkButton(bottom, text="📂 Buka Folder", command=self._open_output,
                                       font=("Segoe UI", 11))
        self.btn_open.grid(row=1, column=2, padx=(4, 8), pady=(2, 4))
        self.btn_open.configure(state="disabled")

    # ── Drag & Drop ──
    # CustomTkinter doesn't support native drag-drop easily.
    # We'll use the button + file dialog.

    def _pick_files(self):
        files = filedialog.askopenfilenames(
            title="Pilih file PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not files:
            return
        for fp in files:
            p = Path(fp)
            if p.suffix.lower() == ".pdf":
                data = p.read_bytes()
                self.pdf_files.append((p.name, data))
        self._refresh_file_list()

    def _clear_files(self):
        self.pdf_files.clear()
        self._refresh_file_list()
        self.zip_data = None
        self.processed_files = []
        self.errors = []
        self.btn_download.configure(state="disabled")
        self.btn_open.configure(state="disabled")
        self._set_success_text("")
        self._set_error_text("")
        self.progress.set(0)
        self.status_label.configure(text="Siap")

    def _refresh_file_list(self):
        self.file_listbox.configure(state="normal")
        self.file_listbox.delete("1.0", "end")
        for name, _ in self.pdf_files:
            self.file_listbox.insert("end", f"📄 {name}\n")
        self.file_listbox.configure(state="disabled")

    # ── Processing ──
    def _process_thread(self):
        if not self.pdf_files:
            messagebox.showwarning(APP_NAME, "Pilih file PDF dulu.")
            return
        self.btn_process.configure(state="disabled", text="⏳ Memproses...")
        self.progress.set(0)
        self.status_label.configure(text="Memproses...")
        self._set_success_text("")
        self._set_error_text("")
        self._append_log("Memulai proses...\n")
        threading.Thread(target=self._process_worker, daemon=True).start()

    def _process_worker(self):
        try:
            result = process_pdf_entries(self.pdf_files)
            self.after(0, self._process_done, result)
        except Exception as e:
            self.after(0, self._process_error, str(e))

    def _process_done(self, result):
        self.zip_data = result["zip_bytes"]
        self.processed_files = result["files"]
        self.errors = result["errors"]

        # Berhasil
        success_text = ""
        for f in self.processed_files:
            success_text += f"✅ {f}\n"
        self._set_success_text(success_text)

        # Error
        error_text = ""
        for err in self.errors:
            parts = err.split("|")
            badge = "❌ ERROR" if parts[0] == "ERROR" else "⚠️ WARNING"
            file_part = parts[1] if len(parts) > 1 else ""
            msg_part = "|".join(parts[2:]) if len(parts) > 2 else err
            error_text += f"{badge} | {file_part} | {msg_part}\n"
        self._set_error_text(error_text)

        self._append_log(f"Selesai. {len(self.processed_files)} berhasil, {len(self.errors)} error/warning.\n")

        self.btn_download.configure(state="normal" if self.zip_data else "disabled")
        self.btn_open.configure(state="normal")
        self.progress.set(1)
        self.status_label.configure(text=f"Selesai — {len(self.processed_files)} file berhasil")
        self.btn_process.configure(state="normal", text="🔄 Proses")

        if self.zip_data:
            self.tab_view.set("✅ Berhasil")

    def _process_error(self, err_msg):
        self._append_log(f"ERROR: {err_msg}\n")
        self.status_label.configure(text="Error — lihat log")
        self.btn_process.configure(state="normal", text="🔄 Proses")
        messagebox.showerror(APP_NAME, f"Proses gagal:\n{err_msg}")

    def _save_zip(self):
        if not self.zip_data:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip")],
            initialfile="Hasil_Rename.zip"
        )
        if not path:
            return
        Path(path).write_bytes(self.zip_data)
        self._append_log(f"ZIP disimpan: {path}\n")
        messagebox.showinfo(APP_NAME, f"ZIP disimpan:\n{path}")

    def _open_output(self):
        # Buka folder Documents
        docs = os.path.join(os.path.expanduser("~"), "Documents")
        os.startfile(docs)

    def _export_csv(self):
        if not self.errors:
            messagebox.showinfo(APP_NAME, "Tidak ada error untuk di-export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="Warning_Error_List.csv"
        )
        if not path:
            return
        csv = "Tipe,File,Keterangan\n"
        for err in self.errors:
            parts = err.split("|")
            tipe = parts[0] if len(parts) > 0 else ""
            file_ = (parts[1] if len(parts) > 1 else "").replace('"', '""')
            msg = ("|".join(parts[2:]) if len(parts) > 2 else err).replace('"', '""')
            csv += f'"{tipe}","{file_}","{msg}"\n'
        Path(path).write_text(csv, encoding="utf-8-sig")
        self._append_log(f"CSV disimpan: {path}\n")
        messagebox.showinfo(APP_NAME, f"CSV disimpan:\n{path}")

    def _set_success_text(self, text):
        self.success_text.configure(state="normal")
        self.success_text.delete("1.0", "end")
        if text:
            self.success_text.insert("1.0", text)
        self.success_text.configure(state="disabled")

    def _set_error_text(self, text):
        self.error_text.configure(state="normal")
        self.error_text.delete("1.0", "end")
        if text:
            self.error_text.insert("1.0", text)
        self.error_text.configure(state="disabled")

    def _append_log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ── Update ──
    def _check_update_async(self):
        threading.Thread(target=self._check_update_worker, daemon=True).start()

    def _check_update_worker(self):
        try:
            import urllib.request
            url = "https://storage.googleapis.com/ganti-nama-file-update/version.txt"
            resp = urllib.request.urlopen(url, timeout=5)
            data = resp.read().decode().strip()
            ver = ""
            for line in data.split("\n"):
                if line.startswith("APP_VERSION="):
                    ver = line.split("=", 1)[1].strip()
                    break
            if ver and ver != APP_VERSION:
                self.after(0, self._show_update_banner, ver)
        except Exception:
            pass  # offline atau blom ada update

    def _show_update_banner(self, new_ver):
        self.update_banner.configure(
            text=f"⬇ Update v{new_ver} tersedia — Klik untuk download",
            cursor="hand2"
        )
        self.update_banner.grid()
        self.update_banner.bind("<Button-1>", lambda e: self._do_update(new_ver))

    def _do_update(self, new_ver):
        import urllib.request
        import subprocess
        temp_exe = os.path.join(os.environ.get("TEMP", "."), "Sintelis_Utility_new.exe")
        dl_url = f"https://storage.googleapis.com/ganti-nama-file-update/Sintelis_Utility_v{new_ver}.exe"
        self._append_log(f"Mendownload update v{new_ver}...\n")
        try:
            urllib.request.urlretrieve(dl_url, temp_exe)
            self._append_log("Download selesai. Menukar file...\n")
            # Buat batch updater
            me = sys.executable if getattr(sys, 'frozen', False) else __file__
            batch = f"""@echo off
:wait
timeout /t 2 /nobreak >nul
del "{me}" 2>nul
if exist "{me}" goto wait
copy "{temp_exe}" "{me}" >nul
start "" "{me}"
del "%~f0"
"""
            batch_path = os.path.join(os.environ.get("TEMP", "."), "updater.bat")
            with open(batch_path, "w") as f:
                f.write(batch)
            subprocess.Popen([batch_path], shell=True, close_fds=True)
            self.quit()
        except Exception as e:
            self._append_log(f"Update gagal: {e}\n")
            messagebox.showerror(APP_NAME, f"Update gagal:\n{e}")


if __name__ == "__main__":
    # Set Tesseract path — bundle path if frozen, else fallback
    if getattr(sys, 'frozen', False):
        tess_dir = os.path.join(BASE, "tesseract")
        tess_exe = os.path.join(tess_dir, "tesseract.exe")
        if os.path.exists(tess_exe):
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tess_exe

        poppler_dir = os.path.join(BASE, "poppler")
        if os.path.exists(poppler_dir):
            from pdf2image import pdf2image
            pdf2image.pdf2image.poppler_path = poppler_dir

    app = PortableApp()
    app.mainloop()
