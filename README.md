# Sintelis Utility

Aplikasi desktop **OCR PDF + rename otomatis** untuk dokumen maintenance/pengawasan UPT Resor Sintelis 1.21 BOO.

## Arsitektur

- **Frontend**: React SPA (Vite) — `web-app/src/`
- **Backend**: Python WebView + Tesseract OCR — `web-app/run_desktop_webview.py`
- **Build**: PyInstaller → `SintelisUtility.exe` (portable, single-file)

```
web-app/
├── src/
│   ├── App.jsx              # React SPA — UI upload, proses, simpan
│   ├── index.css            # Premium dark theme
│   └── utils/
│       ├── detector.js      # detectDoc() — 15 branch deteksi
│       ├── pdfProcessor.js  # PDF.js render + ekstrak teks
│       └── fsHandler.js     # File System Access API + ZIP
├── run_desktop_webview.py   # Python backend + native window
├── build_exe.spec           # PyInstaller spec
└── package.json
```

## Quick Start

```powershell
# Production: double-click SintelisUtility.exe (no install needed)

# Development:
cd web-app
pip install -r ../requirements.txt
python run_desktop_webview.py    # Terminal 1 — backend + window
npm run dev                      # Terminal 2 — React hot-reload (optional)

# Build EXE:
npm run build
pyinstaller build_exe.spec
```

## Fitur

- Drag & drop PDF dari OS
- OCR Tesseract (ind + eng) + pdf2image
- 15 branch deteksi dokumen (Wesel, Sinyal, AXC, Serat Optik, PDSE, PTDS, PTLS, PTLP, CTC-CTS, Catu Daya, Radio Basestation, Waystation, Pintu Perlintasan, Point Lock)
- Tabel 3-tab: 📎 File Input | ✅ Berhasil | ⚠️ Error
- Export Excel (XLSX) 3 sheet
- Simpan hasil rename ke folder atau download ZIP

## Dokumentasi

Lihat [notes/](notes/) — Obsidian vault dengan panduan penggunaan, arsitektur kode, basis pengetahuan, dan task log.

