"""
Sintelis Utility — Portable Desktop App v2
Drag-drop PDF, output langsung ke folder (no ZIP).
Import langsung dari app.py (single source of truth).
"""
import os
import sys

# ⚡ PATCH subprocess SEBELUM import apapun — tesseract/pdf2image dll semua pake subprocess
if getattr(sys, 'frozen', False):
    import subprocess
    _orig_popen_init = subprocess.Popen.__init__
    def _silent_popen_init(self, *args, **kwargs):
        kwargs.setdefault('creationflags', 0x08000000)  # CREATE_NO_WINDOW
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE
        kwargs.setdefault('startupinfo', si)
        _orig_popen_init(self, *args, **kwargs)
    subprocess.Popen.__init__ = _silent_popen_init

import re
import threading
import zipfile
from io import BytesIO
from tkinter import filedialog, messagebox
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE = sys._MEIPASS
else:
    BASE = os.path.dirname(os.path.abspath(__file__))

# ── Early bundled env setup (before core import) ──
def _early_setup_bundled():
    # Resolve tesseract
    cands = [
        os.path.join(BASE, "tesseract"),
        os.path.join(BASE, "..", "tesseract"),
        os.path.join(BASE, "Aplikasi", "tesseract"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesseract"),
    ]
    for d in cands:
        ad = os.path.abspath(d)
        exe = os.path.join(ad, "tesseract.exe")
        tessdata = os.path.join(ad, "tessdata")
        if os.path.isfile(exe) and os.path.isdir(tessdata):
            os.environ["TESSDATA_PREFIX"] = ad
            break

_early_setup_bundled()

sys.path.insert(0, BASE)

import customtkinter as ctk
from core import process_pdf_ocr, detect_doc, build_filename, process_pdf_entries, read_input_file

# tkinterdnd2 untuk drag-drop
import tkinterdnd2

APP_VERSION = "1.1.0"
APP_NAME = "Sintelis Utility"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class PortableApp(tkinterdnd2.Tk):
    """Pakai TkinterDnD.Tk sebagai root biar drag-drop jalan."""
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("920x620")
        self.minsize(800, 500)

        # State
        self.pdf_files: list[tuple[str, bytes]] = []
        self.processed_files: list[str] = []
        self.errors: list[str] = []
        self.result_zip: bytes | None = None
        self.output_dir: str | None = None
        self.jenis_var = ctk.StringVar(value="Perawatan")
        self.instansi_var = ctk.StringVar(value="BTP JAK")

        # Konfigurasi CTk di atas TkinterDnD.Tk
        ctk.set_appearance_mode("dark")
        ctk.deactivate_automatic_dpi_awareness()

        self._build_ui()
        self.after(2000, self._check_update_async)

    def _build_ui(self):
        # Main grid
        self.grid_columnconfigure(0, weight=0, minsize=280)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Kiri: Upload ──
        left = ctk.CTkFrame(self, corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(left, text="📁 Upload PDF", font=("Segoe UI", 18, "bold"), text_color="#f39c12").pack(pady=(14, 6))

        # Drop zone — pakai frame biasa + tkinterdnd2 binding
        self.drop_frame = ctk.CTkFrame(left, fg_color="transparent", border_width=2,
                                        border_color="#f39c12", corner_radius=10)
        self.drop_frame.pack(fill="x", padx=12, pady=4)
        self.drop_label = ctk.CTkLabel(self.drop_frame, text="📄 Drop PDF di sini\natau", font=("Segoe UI", 14), text_color="#cccccc")
        self.drop_label.pack(pady=(16, 4))
        ctk.CTkButton(self.drop_frame, text="Pilih File", command=self._pick_files,
                       font=("Segoe UI", 13, "bold"), height=34, fg_color="#2980b9", hover_color="#3498db").pack(pady=(0, 16))

        # Drag-drop — register langsung ke canvas CTkFrame (bukan root)
        self.after(200, self._register_dnd)

        # ── Dropdown Jenis Kegiatan ──
        jenis_frame = ctk.CTkFrame(left, fg_color="transparent")
        jenis_frame.pack(fill="x", padx=12, pady=(4, 0))
        ctk.CTkLabel(jenis_frame, text="📋 Jenis:", font=("Segoe UI", 13), text_color="#ffffff").pack(side="left", padx=(0, 6))
        self.jenis_menu = ctk.CTkOptionMenu(jenis_frame, variable=self.jenis_var,
            values=["Perawatan", "Perbaikan"],
            font=("Segoe UI", 12), width=130, height=28)
        self.jenis_menu.pack(side="left")

        # ── Dropdown Instansi ──
        ctk.CTkLabel(jenis_frame, text="  Instansi:", font=("Segoe UI", 13), text_color="#ffffff").pack(side="left", padx=(6, 0))
        self.instansi_menu = ctk.CTkOptionMenu(jenis_frame, variable=self.instansi_var,
            values=["BTP JAK", "BTP BD"],
            font=("Segoe UI", 12), width=120, height=28)
        self.instansi_menu.pack(side="left")

        # Tombol pilih output folder
        out_frame = ctk.CTkFrame(left, fg_color="transparent")
        out_frame.pack(fill="x", padx=12, pady=(2, 2))
        ctk.CTkLabel(out_frame, text="📂 Output:", font=("Segoe UI", 13), text_color="#ffffff").pack(side="left", padx=(0, 6))
        self.btn_outdir = ctk.CTkButton(out_frame, text="Pilih Folder", command=self._pick_output_dir,
                                         font=("Segoe UI", 12), width=110, height=30, fg_color="#34495e", hover_color="#4a6a8a")
        self.btn_outdir.pack(side="left")
        self.outdir_label = ctk.CTkLabel(out_frame, text="(default: ./Hasil_Rename)", font=("Segoe UI", 11),
                                          text_color="#aaaaaa")
        self.outdir_label.pack(side="left", padx=(6, 0))

        # File list + counter
        self.file_listbox = ctk.CTkTextbox(left, height=120, font=("Consolas", 13), text_color="#e0e0e0")
        self.file_listbox.pack(fill="both", expand=True, padx=12, pady=(6, 0))
        self.file_listbox.configure(state="disabled")
        self.file_counter_label = ctk.CTkLabel(left, text="📎 0 file", font=("Segoe UI", 12), text_color="#bbbbbb")
        self.file_counter_label.pack(padx=12, pady=(2, 4), anchor="w")

        # Buttons
        btn_frame = ctk.CTkFrame(left, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(4, 10))

        self.btn_clear = ctk.CTkButton(btn_frame, text="🗑 Hapus", command=self._clear_files,
                                        fg_color="#c0392b", hover_color="#e74c3c", font=("Segoe UI", 13, "bold"), height=34)
        self.btn_clear.pack(side="left", padx=(0, 4))

        self.btn_process = ctk.CTkButton(btn_frame, text="🔄 Proses", command=self._process_thread,
                                          font=("Segoe UI", 14, "bold"), height=34, fg_color="#e67e22", hover_color="#f39c12")
        self.btn_process.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # ── Kanan: Hasil — 3 kolom sejajar (berhasil | error | log) ──
        right = ctk.CTkFrame(self, corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right.grid_columnconfigure(0, weight=1)
        right.grid_columnconfigure(1, weight=1)
        right.grid_columnconfigure(2, weight=1)

        # Banner update
        self.update_banner = ctk.CTkLabel(right, text="", fg_color="#2d7a2d", corner_radius=6,
                                          font=("Segoe UI", 11))
        self.update_banner.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 6), padx=2)
        self.update_banner.grid_remove()

        ctk.CTkLabel(right, text="✅ Berhasil", font=("Segoe UI", 15, "bold"), text_color="#f39c12").grid(row=1, column=0, pady=(0, 2))
        self.success_count_label = ctk.CTkLabel(right, text="0", font=("Segoe UI", 13, "bold"), text_color="#f39c12")
        self.success_count_label.grid(row=2, column=0, pady=(0, 2))
        self.success_text = ctk.CTkTextbox(right, font=("Consolas", 13), wrap="word", text_color="#e0e0e0")
        self.success_text.grid(row=3, column=0, sticky="nsew", padx=(0, 3), pady=(0, 2))
        self.success_text.configure(state="disabled")

        ctk.CTkLabel(right, text="⚠️ Error", font=("Segoe UI", 15, "bold"), text_color="#ff6644").grid(row=1, column=1, pady=(0, 2))
        self.error_count_label = ctk.CTkLabel(right, text="0", font=("Segoe UI", 13, "bold"), text_color="#ff4444")
        self.error_count_label.grid(row=2, column=1, pady=(0, 2))
        self.error_text = ctk.CTkTextbox(right, font=("Consolas", 13), wrap="word", text_color="#e0e0e0")
        self.error_text.grid(row=3, column=1, sticky="nsew", padx=3, pady=(0, 2))
        self.error_text.configure(state="disabled")
        ctk.CTkButton(right, text="📊 Export CSV", command=self._export_csv,
                       font=("Segoe UI", 10), text_color="#aaaaaa", fg_color="#34495e", hover_color="#4a6a8a", height=24).grid(row=4, column=1, pady=(0, 4))

        ctk.CTkLabel(right, text="📋 Log", font=("Segoe UI", 15, "bold"), text_color="#3498db").grid(row=1, column=2, pady=(0, 2))
        self.log_text = ctk.CTkTextbox(right, font=("Consolas", 12), wrap="word", text_color="#cccccc")
        self.log_text.grid(row=3, column=2, sticky="nsew", padx=(3, 0), pady=(0, 2))
        self.log_text.configure(state="disabled")

        # Row 3 weight biar textbox full-height
        right.grid_rowconfigure(3, weight=1)

        # ── Bottom bar ──
        bottom = ctk.CTkFrame(self, corner_radius=8, height=44)
        bottom.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        bottom.grid_columnconfigure(0, weight=0)
        bottom.grid_columnconfigure(3, weight=1)

        self.progress = ctk.CTkProgressBar(bottom, height=14, corner_radius=4)
        self.progress.grid(row=0, column=0, columnspan=4, sticky="ew", padx=8, pady=(6, 0))
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(bottom, text="Siap", font=("Segoe UI", 12), text_color="#bbbbbb")
        self.status_label.grid(row=1, column=0, sticky="w", padx=8, pady=(2, 4))

        self.btn_save = ctk.CTkButton(bottom, text="💾 Simpan", command=self._save_result,
                                       font=("Segoe UI", 13, "bold"), height=30, fg_color="#e67e22", hover_color="#f39c12")
        self.btn_save.grid(row=1, column=1, padx=(0, 4), pady=(2, 4))
        self.btn_save.configure(state="disabled")

        self.btn_open = ctk.CTkButton(bottom, text="📂 Buka Folder Hasil", command=self._open_output,
                                       font=("Segoe UI", 13, "bold"), height=30, fg_color="#2980b9", hover_color="#3498db")
        self.btn_open.grid(row=1, column=2, padx=4, pady=(2, 4))
        self.btn_open.configure(state="disabled")

        # Label lokasi output
        self.output_label = ctk.CTkLabel(bottom, text="", font=("Segoe UI", 11), text_color="#aaaaaa")
        self.output_label.grid(row=1, column=3, sticky="e", padx=8, pady=(2, 4))

    # ── Drag-Drop ──
    def _register_dnd(self):
        """Daftarkan drop ke canvas drop_frame (CTk punya _canvas internal)."""
        canvas = self.drop_frame._canvas
        canvas.drop_target_register(tkinterdnd2.DND_FILES)
        canvas.dnd_bind('<<Drop>>', self._on_drop)
        # Juga register root sbg fallback
        self.drop_target_register(tkinterdnd2.DND_FILES)
        self.dnd_bind('<<Drop>>', self._on_drop)

    def _on_drop(self, event):
        """Handler drag-drop file — parse path Windows dgn {kurung}."""
        raw = event.data
        files = []
        # Parse: paths dgn spasi dibungkus {}, tanpa spasi langsung
        for m in re.finditer(r'\{([^}]+)\}|(\S+)', raw):
            path = m.group(1) or m.group(2)
            path = path.strip('"')
            if path:
                p = Path(path)
                if p.suffix.lower() == ".pdf" and p.exists():
                    files.append(p)
        if not files:
            self._append_log(f"[DND] Gagal parse path: {raw}\n")
            return
        for p in files:
            data = p.read_bytes()
            self.pdf_files.append((p.name, data))
        self._append_log(f"[DND] {len(files)} file ditambahkan\n")
        self._refresh_file_list()

    def _pick_output_dir(self):
        """Pilih folder output kustom."""
        path = filedialog.askdirectory(title="Pilih folder output")
        if path:
            self.output_dir = path
            self.outdir_label.configure(text=path, text_color="#ffffff")
            self._append_log(f"[OUT] Folder output: {path}\n")

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
        self.processed_files = []
        self.errors = []
        self.result_zip = None
        self.btn_open.configure(state="disabled")
        self.btn_save.configure(state="disabled", text="💾 Simpan")
        self.output_label.configure(text="")
        self._set_success_text("")
        self._set_error_text("")
        self.success_count_label.configure(text="✅ 0")
        self.error_count_label.configure(text="⚠️ 0")
        self.progress.set(0)
        self.status_label.configure(text="Siap")
        # Jangan reset output_dir — user mungkin mau folder tetap

    def _refresh_file_list(self):
        self.file_listbox.configure(state="normal")
        self.file_listbox.delete("1.0", "end")
        for i, (name, _) in enumerate(self.pdf_files, 1):
            self.file_listbox.insert("end", f"{i:2d}. {name}\n")
        self.file_listbox.configure(state="disabled")
        self.file_counter_label.configure(text=f"{len(self.pdf_files)} file")

    # ── Core Process ──
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
            jenis = self.jenis_var.get()
            instansi = self.instansi_var.get()
            def log_cb(msg):
                self.after(0, lambda: self._append_log(f"{msg}\n"))
            result = process_pdf_entries(self.pdf_files, jenis_kegiatan=jenis, instansi=instansi, progress_callback=log_cb)
            self.after(0, self._process_done, result)
        except Exception as e:
            self.after(0, self._process_error, str(e))

    def _process_done(self, result):
        # Pakai folder pilihan user atau default
        if self.output_dir:
            out = self.output_dir
        else:
            out = os.path.join(BASE, "Hasil_Rename")
        os.makedirs(out, exist_ok=True)
        self.output_dir = out  # simpan biar konsisten

        self.processed_files = result["files"]
        self.errors = result["errors"]
        self.result_zip = result["zip_bytes"]  # simpan dulu, jangan extract

        # Text hasil (nama file saja, tanpa ukuran karena belum di-save)
        success_text = ""
        for i, f in enumerate(self.processed_files, 1):
            success_text += f"{i:2d}. {f}\n"
        self._set_success_text(success_text)
        self.success_count_label.configure(text=f"✅ {len(self.processed_files)}")

        error_text = ""
        for i, err in enumerate(self.errors, 1):
            parts = err.split("|")
            badge = "❌" if parts[0] == "ERROR" else "⚠️"
            file_part = parts[1] if len(parts) > 1 else ""
            msg_part = "|".join(parts[2:]) if len(parts) > 2 else err
            error_text += f"{badge} {file_part} | {msg_part}\n"
        self._set_error_text(error_text)
        self.error_count_label.configure(text=f"⚠️ {len(self.errors)}")

        self._append_log(f"Selesai. {len(self.processed_files)} berhasil, {len(self.errors)} error.\n")
        self._append_log(f"Klik 💾 Simpan untuk menyimpan file ke folder output.\n")

        self.btn_open.configure(state="disabled")
        self.btn_save.configure(state="normal", text=f"💾 Simpan ({len(self.processed_files)} file)")
        self.progress.set(1)
        self.status_label.configure(text=f"Selesai — {len(self.processed_files)} file — klik Simpan")
        self.btn_process.configure(state="normal", text="🔄 Proses")

        if self.processed_files:
            messagebox.showinfo(APP_NAME, f"Proses selesai!\n{len(self.processed_files)} file siap disimpan.\nKlik tombol 💾 Simpan.")

    def _process_error(self, err_msg):
        self._append_log(f"ERROR: {err_msg}\n")
        self.status_label.configure(text="Error — lihat log")
        self.btn_process.configure(state="normal", text="🔄 Proses")
        messagebox.showerror(APP_NAME, f"Proses gagal:\n{err_msg}")

    def _save_result(self):
        """Simpan hasil extract ZIP ke folder output."""
        if not self.result_zip or not self.processed_files:
            messagebox.showwarning(APP_NAME, "Tidak ada hasil untuk disimpan.")
            return
        # Pakai folder pilihan user atau default
        if self.output_dir:
            out = self.output_dir
        else:
            out = os.path.join(BASE, "Hasil_Rename")
        os.makedirs(out, exist_ok=True)
        self.output_dir = out

        with zipfile.ZipFile(BytesIO(self.result_zip)) as zf:
            zf.extractall(self.output_dir)

        # Update success text with sizes
        success_text = ""
        for i, f in enumerate(self.processed_files, 1):
            fp = os.path.join(self.output_dir, f)
            size = os.path.getsize(fp) if os.path.exists(fp) else 0
            success_text += f"{i:2d}. {f} — {size/1024:.1f} KB\n"
        self._set_success_text(success_text)

        self.btn_save.configure(state="disabled", text="✅ Tersimpan")
        self.btn_open.configure(state="normal")
        self.output_label.configure(text=f"📁 {os.path.basename(self.output_dir)}")
        self.status_label.configure(text=f"Tersimpan — {len(self.processed_files)} file")
        self._append_log(f"File tersimpan di: {self.output_dir}\n")
        self.result_zip = None  # free memory
        messagebox.showinfo(APP_NAME, f"{len(self.processed_files)} file disimpan!\nFolder: {self.output_dir}")

    # ── Actions ──
    def _open_output(self):
        if self.output_dir and os.path.isdir(self.output_dir):
            os.startfile(self.output_dir)
        else:
            # Buka Documents
            os.startfile(os.path.join(os.path.expanduser("~"), "Documents"))

    def _export_csv(self):
        if not self.errors:
            messagebox.showinfo(APP_NAME, "Tidak ada error.")
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

    # ── Helpers ──
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
            pass

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
    # Bundle path untuk Tesseract
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
