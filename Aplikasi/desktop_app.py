from __future__ import annotations

import argparse
import asyncio
import builtins
import contextlib
import queue
import re
import threading
import traceback
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

import download_p3ste_rekap as core


def today_str() -> str:
    return datetime.now().strftime("%d/%m/%Y")


class TextWriter:
    def __init__(self, enqueue_log, enqueue_progress):
        self._enqueue_log = enqueue_log
        self._enqueue_progress = enqueue_progress
        self._buffer = ""

    def write(self, text: str) -> None:
        if not text:
            return

        for percent, message in re.findall(r"(\d{1,3})%\s+([^\r\n]+)", text):
            self._enqueue_progress(int(percent), message.strip())

        if "\r" in text and "%" in text:
            return

        self._buffer += text.replace("\r", "")
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if line and not re.match(r"^\[.*\]\s*\d{1,3}%\s+", line):
                self._enqueue_log(line)

    def flush(self) -> None:
        return


class LoginDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, title: str = "Data Login", initial: dict | None = None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result: dict | None = None
        initial = initial or {}

        self.var_name = tk.StringVar(value=initial.get("name", ""))
        self.var_nipp = tk.StringVar(value=initial.get("nipp", ""))
        self.var_password = tk.StringVar(value=initial.get("password", ""))
        self.var_save = tk.BooleanVar(value=bool(initial.get("password")))

        body = ttk.Frame(self, padding=12)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Nama").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(body, textvariable=self.var_name, width=30).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(body, text="NIPP").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(body, textvariable=self.var_nipp, width=30).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(body, text="Password").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(body, textvariable=self.var_password, width=30, show="*").grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Checkbutton(body, text="Simpan password lokal", variable=self.var_save).grid(
            row=3, column=1, sticky="w", pady=(4, 8)
        )

        buttons = ttk.Frame(body)
        buttons.grid(row=4, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Batal", command=self._cancel).grid(row=0, column=0, padx=4)
        ttk.Button(buttons, text="Simpan", command=self._save).grid(row=0, column=1, padx=4)

        self.bind("<Escape>", lambda _event: self._cancel())
        self.bind("<Return>", lambda _event: self._save())
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.wait_visibility()
        self.focus_force()

    def _save(self) -> None:
        name = self.var_name.get().strip()
        nipp = self.var_nipp.get().strip()
        password = self.var_password.get() if self.var_save.get() else ""

        if not name or not nipp:
            messagebox.showerror("Data login", "Nama dan NIPP wajib diisi.", parent=self)
            return

        self.result = {"name": name, "nipp": nipp, "password": password}
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class SelectLoginDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, logins: dict[str, dict], selected: str = ""):
        super().__init__(parent)
        self.title("Pilih Data Login")
        self.resizable(False, False)
        self.result: str | None = None

        body = ttk.Frame(self, padding=12)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(body, height=8, width=40)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.listbox.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scroll.set)

        self.names = sorted(logins)
        for name in self.names:
            item = f"{name} ({logins[name].get('nipp', '-')})"
            self.listbox.insert("end", item)
        if selected in self.names:
            self.listbox.selection_set(self.names.index(selected))

        buttons = ttk.Frame(body)
        buttons.grid(row=1, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(buttons, text="Batal", command=self._cancel).grid(row=0, column=0, padx=4)
        ttk.Button(buttons, text="Pilih", command=self._choose).grid(row=0, column=1, padx=4)

        self.listbox.bind("<Double-Button-1>", lambda _event: self._choose())
        self.bind("<Escape>", lambda _event: self._cancel())
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.wait_visibility()
        self.focus_force()

    def _choose(self) -> None:
        if not self.names:
            self.result = None
            self.destroy()
            return
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showinfo("Pilih data login", "Pilih satu item dulu.", parent=self)
            return
        self.result = self.names[selection[0]]
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class LoginManagerDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, logins: dict[str, dict], selected: str = ""):
        super().__init__(parent)
        self.title("Data Login")
        self.resizable(False, False)
        self.result: str | None = None
        self.logins = {name: dict(value) for name, value in logins.items()}
        self.selected_name = selected

        body = ttk.Frame(self, padding=12)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        ttk.Label(body, text="Daftar login").grid(row=0, column=0, sticky="w")
        self.listbox = tk.Listbox(body, height=8, width=42)
        self.listbox.grid(row=1, column=0, sticky="nsew", pady=(6, 8))
        self.listbox.bind("<<ListboxSelect>>", lambda _event: self._refresh_info())

        self.info_var = tk.StringVar(value="Belum ada data login.")
        ttk.Label(body, textvariable=self.info_var, wraplength=360).grid(row=2, column=0, sticky="w")

        actions = ttk.Frame(body)
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(actions, text="Buat", command=self._create).grid(row=0, column=0, padx=2)
        ttk.Button(actions, text="Edit", command=self._edit).grid(row=0, column=1, padx=2)
        ttk.Button(actions, text="Hapus", command=self._delete).grid(row=0, column=2, padx=2)
        ttk.Button(actions, text="Pakai", command=self._choose).grid(row=0, column=3, padx=2)
        ttk.Button(actions, text="Tutup", command=self._cancel).grid(row=0, column=4, padx=2)

        self._refresh_list()
        self.bind("<Escape>", lambda _event: self._cancel())
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.wait_visibility()
        self.focus_force()

    def _refresh_list(self) -> None:
        self.listbox.delete(0, "end")
        names = sorted(self.logins)
        for name in names:
            item = f"{name} ({self.logins[name].get('nipp', '-')})"
            self.listbox.insert("end", item)
        if names:
            index = names.index(self.selected_name) if self.selected_name in names else 0
            self.listbox.selection_set(index)
            self.selected_name = names[index]
        else:
            self.selected_name = ""
        self._refresh_info()

    def _current_name(self) -> str:
        names = sorted(self.logins)
        selection = self.listbox.curselection()
        if selection and selection[0] < len(names):
            return names[selection[0]]
        return self.selected_name

    def _refresh_info(self) -> None:
        name = self._current_name()
        self.selected_name = name
        current = self.logins.get(name)
        if not current:
            self.info_var.set("Belum ada data login.")
            return
        has_password = "ya" if current.get("password") else "tidak"
        self.info_var.set(f"Nama: {name} | NIPP: {current.get('nipp', '-')} | password tersimpan: {has_password}")

    def _create(self) -> None:
        dialog = LoginDialog(self, title="Buat Data Login")
        self.wait_window(dialog)
        if not dialog.result:
            return
        name = dialog.result["name"]
        self.logins[name] = {"nipp": dialog.result["nipp"], "password": dialog.result["password"]}
        self.selected_name = name
        self._refresh_list()

    def _edit(self) -> None:
        name = self._current_name()
        current = self.logins.get(name)
        if not current:
            messagebox.showinfo("Data Login", "Pilih data login dulu.", parent=self)
            return
        dialog = LoginDialog(
            self,
            title="Edit Data Login",
            initial={"name": name, "nipp": current.get("nipp", ""), "password": current.get("password", "")},
        )
        self.wait_window(dialog)
        if not dialog.result:
            return
        new_name = dialog.result["name"]
        if new_name != name:
            self.logins.pop(name, None)
        self.logins[new_name] = {"nipp": dialog.result["nipp"], "password": dialog.result["password"]}
        self.selected_name = new_name
        self._refresh_list()

    def _delete(self) -> None:
        name = self._current_name()
        if not name:
            messagebox.showinfo("Data Login", "Pilih data login dulu.", parent=self)
            return
        if not messagebox.askyesno("Data Login", f"Hapus data login '{name}'?", parent=self):
            return
        self.logins.pop(name, None)
        self.selected_name = sorted(self.logins)[0] if self.logins else ""
        self._refresh_list()

    def _choose(self) -> None:
        self.result = self._current_name()
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class DesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("P3-STE Utility")
        self.geometry("1120x820")
        self.minsize(980, 720)

        self.event_queue: queue.Queue = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.running = False
        self.running_mode = ""
        self.session_loop: asyncio.AbstractEventLoop | None = None
        self.session_thread: threading.Thread | None = None
        self.prepared_session: core.PreparedSession | None = None
        self.prepared_key: tuple | None = None
        self.login_store = core.load_login_store()
        self.pdf_files: list[str] = []
        self.pdf_zip_bytes = b""

        self.login_var = tk.StringVar()
        self.login_name_var = tk.StringVar(value="-")
        self.start_var = tk.StringVar(value=today_str())
        self.end_var = tk.StringVar(value=today_str())
        self.type_var = tk.StringVar(value="Perawatan")
        self.output_var = tk.StringVar(value=str(Path.home() / "Downloads" / "P3STE"))
        self.show_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Siap")
        self.progress_var = tk.IntVar(value=0)
        self.login_info_var = tk.StringVar(value="-")
        self.summary_data_var = tk.StringVar(value="-")
        self.summary_pages_var = tk.StringVar(value="-")
        self.summary_info_var = tk.StringVar(value="-")

        self.pdf_type_var = tk.StringVar(value="Perawatan")
        self.pdf_instansi_var = tk.StringVar(value="BTP JAK")
        self.pdf_file_count_var = tk.StringVar(value="0 file")
        self.pdf_success_var = tk.StringVar(value="Berhasil: 0")
        self.pdf_error_var = tk.StringVar(value="Error: 0")

        self._build_ui()
        self.refresh_logins()
        self.after(100, self._poll_events)

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)
        container.rowconfigure(3, weight=1)

        notebook = ttk.Notebook(container)
        notebook.grid(row=0, column=0, sticky="nsew")

        self.download_tab = ttk.Frame(notebook, padding=12)
        self.pdf_tab = ttk.Frame(notebook, padding=12)
        notebook.add(self.download_tab, text="Download Rekap")
        notebook.add(self.pdf_tab, text="Proses PDF")

        self._build_download_tab(self.download_tab)
        self._build_pdf_tab(self.pdf_tab)

        progress_box = ttk.Frame(container)
        progress_box.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        progress_box.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(progress_box, maximum=100, variable=self.progress_var)
        self.progress.grid(row=0, column=0, sticky="ew")
        ttk.Label(progress_box, textvariable=self.status_var).grid(row=1, column=0, sticky="w", pady=(6, 0))

        log_box = ttk.LabelFrame(container, text="Log", padding=12)
        log_box.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        log_box.columnconfigure(0, weight=1)
        log_box.rowconfigure(0, weight=1)

        self.log = scrolledtext.ScrolledText(log_box, height=14, wrap="word", state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_download_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)

        login_box = ttk.LabelFrame(parent, text="Data Login", padding=12)
        login_box.grid(row=0, column=0, sticky="ew")
        login_box.columnconfigure(1, weight=1)

        ttk.Label(login_box, text="Login aktif").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Label(login_box, textvariable=self.login_name_var).grid(row=0, column=1, sticky="w")

        login_buttons = ttk.Frame(login_box)
        login_buttons.grid(row=0, column=2, padx=(8, 0))
        self.manage_login_button = ttk.Button(login_buttons, text="Data Login", command=self.manage_logins)
        self.manage_login_button.grid(row=0, column=0, padx=2)
        self.refresh_login_button = ttk.Button(login_buttons, text="Refresh", command=self.refresh_logins)
        self.refresh_login_button.grid(row=0, column=1, padx=2)

        ttk.Label(login_box, textvariable=self.login_info_var).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )

        job_box = ttk.LabelFrame(parent, text="Filter Rekap", padding=12)
        job_box.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        for idx in range(4):
            job_box.columnconfigure(idx, weight=1 if idx in (1, 3) else 0)

        ttk.Label(job_box, text="Tanggal awal").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(job_box, textvariable=self.start_var, width=16).grid(row=0, column=1, sticky="w", pady=4)
        ttk.Label(job_box, text="Tanggal akhir").grid(row=0, column=2, sticky="w", padx=(20, 8), pady=4)
        ttk.Entry(job_box, textvariable=self.end_var, width=16).grid(row=0, column=3, sticky="w", pady=4)

        ttk.Label(job_box, text="Tipe checklist").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Combobox(
            job_box,
            textvariable=self.type_var,
            state="readonly",
            values=["Perawatan", "Pemeriksaan"],
            width=16,
        ).grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(job_box, text="Folder output").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(job_box, textvariable=self.output_var).grid(row=2, column=1, columnspan=2, sticky="ew", pady=4)
        self.output_button = ttk.Button(job_box, text="Pilih", command=self.choose_output)
        self.output_button.grid(row=2, column=3, sticky="w", pady=4)

        ttk.Checkbutton(job_box, text="Tampilkan browser", variable=self.show_var).grid(
            row=3, column=1, sticky="w", pady=(8, 0)
        )

        summary_box = ttk.LabelFrame(parent, text="Ringkasan", padding=12)
        summary_box.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        summary_box.columnconfigure(1, weight=1)

        ttk.Label(summary_box, text="Total data").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(summary_box, textvariable=self.summary_data_var).grid(row=0, column=1, sticky="w", pady=2)
        ttk.Label(summary_box, text="Total halaman").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Label(summary_box, textvariable=self.summary_pages_var).grid(row=1, column=1, sticky="w", pady=2)
        ttk.Label(summary_box, text="Info tabel").grid(row=2, column=0, sticky="nw", pady=2)
        ttk.Label(summary_box, textvariable=self.summary_info_var, wraplength=760).grid(
            row=2, column=1, sticky="w", pady=2
        )

        action_box = ttk.Frame(parent)
        action_box.grid(row=3, column=0, sticky="w", pady=(12, 0))
        self.summary_button = ttk.Button(
            action_box,
            text="Tampilkan total halaman dan data",
            command=self.start_summary,
        )
        self.summary_button.grid(row=0, column=0, padx=(0, 8))
        self.download_button = ttk.Button(action_box, text="Download", command=self.start_download)
        self.download_button.grid(row=0, column=1)

    def _build_pdf_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(2, weight=1)

        option_box = ttk.LabelFrame(parent, text="Setting", padding=12)
        option_box.grid(row=0, column=0, columnspan=2, sticky="ew")
        option_box.columnconfigure(0, weight=1)
        option_box.columnconfigure(1, weight=1)

        jenis_box = ttk.LabelFrame(option_box, text="Jenis Kegiatan", padding=10)
        jenis_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Radiobutton(jenis_box, text="Perawatan", value="Perawatan", variable=self.pdf_type_var).grid(
            row=0, column=0, sticky="w", pady=2
        )
        ttk.Radiobutton(jenis_box, text="Pemeriksaan", value="Pemeriksaan", variable=self.pdf_type_var).grid(
            row=1, column=0, sticky="w", pady=2
        )

        instansi_box = ttk.LabelFrame(option_box, text="Instansi / Format Nama", padding=10)
        instansi_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ttk.Radiobutton(
            instansi_box,
            text="BTP JAK (Format Standar)",
            value="BTP JAK",
            variable=self.pdf_instansi_var,
        ).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Radiobutton(
            instansi_box,
            text="BTP BD (Format Khusus Sintel Boo)",
            value="BTP BD",
            variable=self.pdf_instansi_var,
        ).grid(row=1, column=0, sticky="w", pady=2)

        file_box = ttk.LabelFrame(parent, text="File PDF", padding=12)
        file_box.grid(row=1, column=0, sticky="nsew", pady=(12, 0), padx=(0, 6))
        file_box.columnconfigure(0, weight=1)
        file_box.rowconfigure(1, weight=1)

        file_actions = ttk.Frame(file_box)
        file_actions.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.pick_pdf_button = ttk.Button(file_actions, text="Pilih file PDF", command=self.choose_pdf_files)
        self.pick_pdf_button.grid(row=0, column=0, padx=(0, 8))
        self.clear_pdf_button = ttk.Button(file_actions, text="Bersihkan", command=self.clear_pdf_files)
        self.clear_pdf_button.grid(row=0, column=1, padx=(0, 8))
        self.process_pdf_button = ttk.Button(file_actions, text="Proses app.py", command=self.start_pdf_process)
        self.process_pdf_button.grid(row=0, column=2)
        ttk.Label(file_actions, textvariable=self.pdf_file_count_var).grid(row=0, column=3, padx=(12, 0), sticky="w")

        self.pdf_file_list = tk.Listbox(file_box, height=12)
        self.pdf_file_list.grid(row=1, column=0, sticky="nsew")

        result_box = ttk.LabelFrame(parent, text="Hasil", padding=12)
        result_box.grid(row=1, column=1, rowspan=2, sticky="nsew", pady=(12, 0), padx=(6, 0))
        result_box.columnconfigure(0, weight=1)
        result_box.rowconfigure(2, weight=1)
        result_box.rowconfigure(4, weight=1)

        result_actions = ttk.Frame(result_box)
        result_actions.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.save_zip_button = ttk.Button(result_actions, text="Simpan ZIP", command=self.save_pdf_zip, state="disabled")
        self.save_zip_button.grid(row=0, column=0, sticky="w")

        ttk.Label(result_box, textvariable=self.pdf_success_var).grid(row=1, column=0, sticky="nw")
        self.pdf_success_list = tk.Listbox(result_box, height=10)
        self.pdf_success_list.grid(row=2, column=0, sticky="nsew", pady=(4, 12))

        ttk.Label(result_box, textvariable=self.pdf_error_var).grid(row=3, column=0, sticky="nw")
        self.pdf_error_list = tk.Listbox(result_box, height=8)
        self.pdf_error_list.grid(row=4, column=0, sticky="nsew", pady=(4, 0))

    def append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_status(self, percent: int, message: str) -> None:
        self.progress_var.set(max(0, min(100, percent)))
        self.status_var.set(message)

    def refresh_logins(self) -> None:
        self.login_store = core.load_login_store()
        names = sorted(self.login_store.get("logins", {}))
        selected = self.login_store.get("selected", "")
        if selected in names:
            self.login_var.set(selected)
        elif names:
            self.login_var.set(names[0])
        else:
            self.login_var.set("")
        self.login_name_var.set(self.login_var.get() or "-")
        self._update_login_info()
        self.append_log("Daftar login dimuat.")

    def _update_login_info(self) -> None:
        data = self.login_store.get("logins", {})
        selected = self.login_var.get().strip()
        record = data.get(selected)
        if not record:
            self.login_name_var.set("-")
            self.login_info_var.set("Belum ada login dipilih.")
            return
        self.login_name_var.set(selected)
        has_password = "ya" if record.get("password") else "tidak"
        self.login_info_var.set(f"NIPP: {record.get('nipp', '-')}, password tersimpan: {has_password}")

    def manage_logins(self) -> None:
        data = core.load_login_store()
        dialog = LoginManagerDialog(self, data.get("logins", {}), data.get("selected", ""))
        self.wait_window(dialog)
        if not dialog.result:
            return

        updated = {"selected": dialog.result, "logins": dialog.logins}
        core.save_login_store(updated)
        self._invalidate_prepared_session()
        self.append_log(f"Data login aktif: {dialog.result}")
        self.refresh_logins()

    def choose_output(self) -> None:
        selected = filedialog.askdirectory(title="Pilih folder output")
        if selected:
            self.output_var.set(selected)

    def choose_pdf_files(self) -> None:
        selected = filedialog.askopenfilenames(
            title="Pilih file PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not selected:
            return

        known = set(self.pdf_files)
        for path in selected:
            if path not in known:
                self.pdf_files.append(path)
                known.add(path)
        self._refresh_pdf_files()

    def clear_pdf_files(self) -> None:
        self.pdf_files.clear()
        self.pdf_zip_bytes = b""
        self._refresh_pdf_files()
        self._show_pdf_result({"files": [], "errors": [], "zip_bytes": b"", "success": False, "processed_count": 0})

    def _refresh_pdf_files(self) -> None:
        self.pdf_file_list.delete(0, "end")
        for path in self.pdf_files:
            self.pdf_file_list.insert("end", Path(path).name)
        self.pdf_file_count_var.set(f"{len(self.pdf_files)} file")

    def _show_summary(self, summary: dict) -> None:
        self.summary_data_var.set(str(summary.get("total_data", "-")))
        self.summary_pages_var.set(str(summary.get("total_pages", "-")))
        self.summary_info_var.set(summary.get("info_text", "-") or "-")

    def _show_pdf_result(self, result: dict) -> None:
        self.pdf_success_list.delete(0, "end")
        self.pdf_error_list.delete(0, "end")

        files = result.get("files", [])
        errors = result.get("errors", [])
        for item in files:
            self.pdf_success_list.insert("end", item)
        for item in errors:
            self.pdf_error_list.insert("end", item)

        self.pdf_zip_bytes = result.get("zip_bytes", b"") or b""
        self.save_zip_button.configure(state="normal" if self.pdf_zip_bytes else "disabled")
        self.pdf_success_var.set(f"Berhasil: {len(files)}")
        self.pdf_error_var.set(f"Error: {len(errors)}")

    def save_pdf_zip(self) -> None:
        if not self.pdf_zip_bytes:
            messagebox.showinfo("P3-STE", "Belum ada ZIP hasil proses.", parent=self)
            return

        target = filedialog.asksaveasfilename(
            title="Simpan ZIP hasil",
            defaultextension=".zip",
            initialfile="Ceklis_Hasil_OCR.zip",
            filetypes=[("ZIP files", "*.zip")],
        )
        if not target:
            return

        Path(target).write_bytes(self.pdf_zip_bytes)
        self.append_log(f"ZIP disimpan: {target}")
        messagebox.showinfo("P3-STE", "ZIP berhasil disimpan.", parent=self)

    def _selected_login_data(self) -> dict | None:
        data = core.load_login_store()
        selected = self.login_var.get().strip()
        if selected and selected in data.get("logins", {}):
            data["selected"] = selected
            core.save_login_store(data)
        return core.selected_login(core.load_login_store())

    def _login_key(self, login_data: dict | None) -> tuple:
        login_data = login_data or {}
        return (login_data.get("nipp", ""), login_data.get("password", ""))

    def _read_download_args(self) -> argparse.Namespace | None:
        start = self.start_var.get().strip()
        end = self.end_var.get().strip()
        tipe = self.type_var.get().strip()
        output = self.output_var.get().strip()

        if not start or not end or not tipe:
            messagebox.showerror("P3-STE", "Tanggal dan tipe wajib diisi.", parent=self)
            return None

        try:
            start = core.parse_date(start)
            end = core.parse_date(end)
        except SystemExit as exc:
            messagebox.showerror("P3-STE", str(exc), parent=self)
            return None

        return argparse.Namespace(
            awal=start,
            akhir=end,
            tipe=tipe,
            output=output or str(Path.home() / "Downloads" / "P3STE"),
            show=bool(self.show_var.get()),
            wait_ms=5_000,
            table_timeout_ms=120_000,
            direct=True,
        )

    def _download_key(self, args: argparse.Namespace, login_data: dict | None) -> tuple:
        return (
            args.awal,
            args.akhir,
            args.tipe,
            args.output,
            bool(args.show),
            self._login_key(login_data),
        )

    def _ensure_session_loop(self) -> asyncio.AbstractEventLoop:
        if self.session_loop and self.session_thread and self.session_thread.is_alive():
            return self.session_loop

        loop = asyncio.new_event_loop()

        def runner() -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        self.session_loop = loop
        self.session_thread = thread
        return loop

    def _close_prepared_session_sync(self) -> None:
        if not self.prepared_session:
            return
        loop = self._ensure_session_loop()
        asyncio.run_coroutine_threadsafe(core.close_prepared_session(self.prepared_session), loop).result()
        self.prepared_session = None
        self.prepared_key = None

    def _invalidate_prepared_session(self) -> None:
        try:
            self._close_prepared_session_sync()
        except Exception:
            self.event_queue.put(("log", "Session ringkasan lama gagal ditutup, tapi proses lanjut."))

    def _set_running(self, running: bool, mode: str = "") -> None:
        self.running = running
        self.running_mode = mode if running else ""
        state = "disabled" if running else "normal"
        for widget in (
            self.manage_login_button,
            self.refresh_login_button,
            self.output_button,
            self.summary_button,
            self.download_button,
            self.pick_pdf_button,
            self.clear_pdf_button,
            self.process_pdf_button,
        ):
            widget.configure(state=state)

    def start_summary(self) -> None:
        if self.running:
            return

        args = self._read_download_args()
        if not args:
            return

        login_data = self._selected_login_data()
        key = self._download_key(args, login_data)
        if self.prepared_session and self.prepared_key == key:
            self._show_summary(self.prepared_session.summary)
            self.append_log("Pakai ringkasan yang sudah disiapkan.")
            return

        self._set_running(True, "summary")
        self.set_status(0, "Mulai ringkasan")
        self.append_log("Mulai baca total halaman dan data.")
        self.worker_thread = threading.Thread(
            target=self._worker_download,
            args=("summary", args, login_data),
            daemon=True,
        )
        self.worker_thread.start()

    def start_download(self) -> None:
        if self.running:
            return

        args = self._read_download_args()
        if not args:
            return

        login_data = self._selected_login_data()
        self._set_running(True, "download")
        self.set_status(0, "Mulai download")
        if self.prepared_session and self.prepared_key == self._download_key(args, login_data):
            self.append_log("Mulai download dari session ringkasan yang sudah siap.")
        else:
            self.append_log("Mulai proses download.")
        self.worker_thread = threading.Thread(
            target=self._worker_download,
            args=("download", args, login_data),
            daemon=True,
        )
        self.worker_thread.start()

    def start_pdf_process(self) -> None:
        if self.running:
            return
        if not self.pdf_files:
            messagebox.showerror("P3-STE", "Pilih minimal 1 file PDF.", parent=self)
            return

        self._set_running(True, "pdf")
        self.set_status(0, "Mulai proses PDF")
        self.append_log("Mulai proses app.py.")
        self.worker_thread = threading.Thread(
            target=self._worker_pdf,
            args=(list(self.pdf_files), self.pdf_type_var.get(), self.pdf_instansi_var.get()),
            daemon=True,
        )
        self.worker_thread.start()

    def _worker_download(self, mode: str, args: argparse.Namespace, login_data: dict | None) -> None:
        def enqueue_log(text: str) -> None:
            self.event_queue.put(("log", text))

        def enqueue_progress(percent: int, message: str) -> None:
            self.event_queue.put(("progress", percent, message))

        def gui_prompt(prompt: str, password: bool = False) -> str:
            response_q: queue.Queue[str] = queue.Queue(maxsize=1)
            self.event_queue.put(("prompt", prompt, password, response_q))
            return response_q.get()

        writer = TextWriter(enqueue_log, enqueue_progress)
        orig_input = builtins.input
        orig_getpass = core.getpass.getpass

        def patched_input(prompt: str = "") -> str:
            return gui_prompt(prompt, password=False)

        def patched_getpass(prompt: str = "Password: ", stream=None) -> str:
            return gui_prompt(prompt, password=True)

        class GuiProgress:
            def set(self, percent: int, message: str) -> None:
                enqueue_progress(percent, message)

            def line(self, message: str) -> None:
                enqueue_log(message)

            def done(self, message: str) -> None:
                enqueue_progress(100, "Selesai")
                enqueue_log(message)

        try:
            builtins.input = patched_input
            core.getpass.getpass = patched_getpass
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                progress = GuiProgress()
                loop = self._ensure_session_loop()
                key = self._download_key(args, login_data)

                if mode == "summary":
                    if self.prepared_session and self.prepared_key != key:
                        self._close_prepared_session_sync()
                    if self.prepared_session and self.prepared_key == key:
                        summary = self.prepared_session.summary
                    else:
                        session = asyncio.run_coroutine_threadsafe(
                            core.open_prepared_session(args, login_data, progress),
                            loop,
                        ).result()
                        self.prepared_session = session
                        self.prepared_key = key
                        summary = session.summary
                    self.event_queue.put(("summary", summary))
                else:
                    if self.prepared_session and self.prepared_key == key:
                        asyncio.run_coroutine_threadsafe(
                            core.download_prepared_session(self.prepared_session, args, progress),
                            loop,
                        ).result()
                        self._close_prepared_session_sync()
                    else:
                        asyncio.run(core.run(args, login_data))
                    self.event_queue.put(("download_done", "Download selesai."))
        except Exception:
            self.event_queue.put(("error", traceback.format_exc()))
        finally:
            builtins.input = orig_input
            core.getpass.getpass = orig_getpass

    def _worker_pdf(self, paths: list[str], jenis: str, instansi: str) -> None:
        try:
            self.event_queue.put(("progress", 10, "Muat modul OCR"))
            import app as pdf_core

            self.event_queue.put(("progress", 25, f"Siapkan {len(paths)} file"))
            entries = [(Path(path).name, Path(path).read_bytes()) for path in paths]
            self.event_queue.put(("progress", 60, "Proses OCR dan rename"))
            result = pdf_core.process_pdf_entries(entries, jenis, instansi)
            self.event_queue.put(("pdf_result", result))
        except Exception:
            self.event_queue.put(("error", traceback.format_exc()))

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.event_queue.get_nowait()
                kind = event[0]

                if kind == "log":
                    self.append_log(event[1])
                elif kind == "progress":
                    self.set_status(event[1], event[2])
                elif kind == "prompt":
                    _, prompt, password, response_q = event
                    answer = simpledialog.askstring(
                        "P3-STE",
                        prompt or "Input:",
                        parent=self,
                        show="*" if password else None,
                    )
                    response_q.put(answer or "")
                elif kind == "summary":
                    self._set_running(False)
                    self.set_status(100, "Ringkasan selesai")
                    self._show_summary(event[1])
                    self.append_log(
                        f"Total data: {event[1].get('total_data', 0)}. Total halaman: {event[1].get('total_pages', 0)}."
                    )
                elif kind == "download_done":
                    self._set_running(False)
                    self.set_status(100, event[1])
                    self.append_log(event[1])
                    messagebox.showinfo("P3-STE", event[1], parent=self)
                elif kind == "pdf_result":
                    self._set_running(False)
                    self.set_status(100, "Proses PDF selesai")
                    self._show_pdf_result(event[1])
                    self.append_log(
                        f"Proses PDF selesai. Berhasil: {event[1].get('processed_count', 0)}. Error: {len(event[1].get('errors', []))}."
                    )
                    if event[1].get("success"):
                        messagebox.showinfo("P3-STE", "Proses PDF selesai.", parent=self)
                    else:
                        messagebox.showwarning("P3-STE", "Tidak ada file berhasil diproses. Lihat hasil.", parent=self)
                elif kind == "error":
                    self._invalidate_prepared_session()
                    self._set_running(False)
                    self.append_log(event[1])
                    self.set_status(0, "Proses gagal")
                    messagebox.showerror("P3-STE", "Proses gagal. Lihat log.", parent=self)
        except queue.Empty:
            pass
        finally:
            self.after(100, self._poll_events)

    def _on_close(self) -> None:
        if self.running:
            if not messagebox.askokcancel("P3-STE", "Proses masih jalan. Tutup tetap?", parent=self):
                return
        self._invalidate_prepared_session()
        if self.session_loop and self.session_thread and self.session_thread.is_alive():
            self.session_loop.call_soon_threadsafe(self.session_loop.stop)
        self.destroy()


def main() -> None:
    app = DesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
