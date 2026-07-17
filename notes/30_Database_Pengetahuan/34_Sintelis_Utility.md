# Sintelis Utility — Ringkasan Proyek

## Tentang App
- **Nama**: Sintelis Utility
- **Versi**: 1.1.0
- **Fungsi**: OCR PDF + rename otomatis file menggunakan pola regex untuk dokumen maintenance/pengawasan
- **Tipe**: Portable EXE (tkinter + PyInstaller), no install needed
- **Framework**: CustomTkinter + tkinterdnd2 (drag-drop PDF)

## Fitur Inti
1. **Drag-drop PDF** — drop file/folder langsung
2. **OCR** — pake `pdf2image` + `pytesseract` (engine tesseract)
3. **Pola Rename** — regex untuk `JPL`, `PTPP`, `BTP`, `BD`, dll
4. **Real-time Log** — `progress_callback` streaming log ke UI tiap file
5. **Save on Demand** — proses selesai → user klik **💾 Simpan** → baru extract ke folder output
6. **Tabel 3 Tab**: "📎 File Input" | "✅ Berhasil" | "⚠️ Error" — berjejer
7. **Counter** — emoji ✅ / ⚠️ di tiap tab
8. **Auto-updater** — Firebase Storage (versi 1.2.0 ke atas)

## UI Perbaikan (v9)
- **Typography**: Segoe UI 13-18pt (judul), Consolas 13pt (log/code)
- **Warna kontras tinggi**: putih, neon hijau `#66ff66`, merah `#ff4444`, biru `#88ccff`
- **Tata letak**: 2 kolom (kiri: input/file list, kanan: tab hasil + log)
- **Log textbox**: konsolas 13pt, bg hitam, bisa di-scroll
- **MonitorBuild** — label status realtime di pojok kanan

## Struktur File
```
Aplikasi/
├── portable_ui.py    # UI aplikasi (portable, tkinter)
├── app.py            # Core logic: OCR, rename, ZIP
├── build_portable.ps1 # Build PyInstaller
└── dist/
    └── Sintelis Utility.exe
```

## Build
```powershell
# 1. Hapus cache dulu
Remove-Item -Recurse -Force "dist", "build", "*.spec" -ErrorAction SilentlyContinue

# 2. Build
PowerShell -ExecutionPolicy Bypass -File .\build_portable.ps1
```

## Kritikal: Subprocess Silent Patch
monkey-patch `subprocess.Popen.__init__` di `portable_ui.py` biar CMD nggak flashing.
```python
import subprocess
_original_popen_init = subprocess.Popen.__init__
def _silent_popen_init(self, *args, **kwargs):
    kwargs.setdefault("startupinfo", si = subprocess.STARTUPINFO())
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    kwargs["startupinfo"] = si
    return _original_popen_init(self, *args, **kwargs)
subprocess.Popen.__init__ = _silent_popen_init
```

## Teknikal Info
- **Python**: 3.14
- **Dependencies**: customtkinter, tkinterdnd2, pytesseract, pdf2image, pillow, pandas, openpyxl
- **PyInstaller hooks**: butuh `--collect-data pillow` dan hook `tkinterdnd2`
- **Firebase**: `ganti-nama-file-update` bucket GCS

## Common Issues
1. **EXE terkunci saat build ulang** → `taskkill /f /im "Sintelis Utility.exe"` + delete cache
2. **Tesseract error** → pastikan `tesseract/` di folder yang sama dgn EXE, path `TESSDATA_PREFIX`
3. **MonitorBuild tidak berjalan** → cek tab name di [tab_view.py], UI pake `"📎 File Input"`
