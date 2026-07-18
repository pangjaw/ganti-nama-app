# Sintelis Utility — Agent Boot

## Project Ini

**Sintelis Utility** — Desktop app OCR PDF + rename otomatis untuk dokumen maintenance UPT Resor Sintelis 1.21 BOO.

- **Arsitektur**: React SPA (Vite) + Python WebView backend
- **Build**: PyInstaller → `SintelisUtility.exe` (portable)

## Folder Utama

```
web-app/                  # PROJECT UTAMA
├── src/
│   ├── App.jsx           # React SPA komponen utama
│   ├── index.css         # Dark theme premium CSS
│   ├── main.jsx          # React entry point
│   └── utils/
│       ├── detector.js   # detectDoc() — 15 branch deteksi dokumen
│       ├── pdfProcessor.js  # PDF.js render + ekstrak teks
│       └── fsHandler.js  # File System API + ZIP handler
├── run_desktop_webview.py  # Python backend (Tesseract OCR + native window)
├── build_exe.spec         # PyInstaller build spec
└── package.json

notes/                   # Obsidian Vault — BACA 00_Dashboard.md DULU
Aplikasi/poppler/        # Poppler binary (PDF → gambar)
data-aset/               # Referensi DATA ASET RESOR 2026
```

## Build

```powershell
cd web-app
npm run build                    # Build React (Vite → dist/)
pyinstaller build_exe.spec       # Build EXE → dist_exe/SintelisUtility.exe
```

## Dev Mode

```powershell
cd web-app
python run_desktop_webview.py    # Terminal 1: backend + window (serve dist/)
npm run dev                      # Terminal 2: React hot-reload (optional)
```

## Dependencies

- **Python**: pytesseract, pdf2image, Pillow (see requirements.txt)
- **Node**: React, Vite, PDF.js (see package.json)
- **System**: Tesseract-OCR, Poppler

## Observability

- Log: `%TEMP%/sintelis_utility.log`
- Debug mode: `python run_desktop_webview.py --debug`

## Dokumentasi Lengkap

Buka [notes/00_Dashboard.md](notes/00_Dashboard.md) — peta navigasi ke semua dokumentasi:
- Arsitektur kode & alur OCR
- Mapping kategori dokumen
- Aturan regex SO OTB
- Rencana perbaikan & riwayat perubahan
