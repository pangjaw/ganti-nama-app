# 📂 Struktur Folder & Komponen Proyek

#arsitektur #struktur

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

Halaman ini mendokumentasikan organisasi berkas serta peran masing-masing komponen dalam proyek **Sintelis Utility**.

---

## 📁 Pohon Direktori Utama

```text
ganti-nama-app/
│
├── .agents/                     # Custom agent rules (Antigravity)
├── .obsidian/                   # Konfigurasi Obsidian Vault
├── notes/                       # Dokumentasi & basis pengetahuan (Markdown)
│   ├── 00_Dashboard.md
│   ├── 10_Panduan_Penggunaan/
│   ├── 20_Arsitektur_Kode/
│   ├── 30_Database_Pengetahuan/
│   └── 40_Task_dan_Log/
│
├── web-app/                     # **PROJECT UTAMA** — React SPA + Python WebView
│   ├── src/                     # Source React
│   │   ├── App.jsx              # Komponen utama UI — Menu 1 (OCR & Rename) + Split View
│   │   ├── components/          # Komponen modular
│   │   │   ├── P3STEDownloader.jsx  # Menu 2: Downloader otomatis website P3-STE
│   │   │   └── AssetAuditPanel.jsx   # Menu 1: Panel Audit & Monitoring Kelengkapan Aset
│   │   ├── index.css            # Premium dark theme CSS
│   │   ├── main.jsx             # Entry point React
│   │   └── utils/               # Library pendukung
│   │       ├── detector.js      # detectDoc() — deteksi tipe dokumen (15 branch)
│   │       ├── pdfProcessor.js  # PDF.js render + ekstrak teks
│   │       ├── fsHandler.js     # File System Access API, folder PDF scan, & ZIP handler
│   │       └── masterAssets.js  # Master data 394+ aset 2026, audit engine, & Excel 3-sheet
│   ├── dist/                    # Vite build output (production)
│   ├── dist_exe/                # PyInstaller standalone EXE output (SintelisUtility.exe)
│   ├── build_exe.spec           # PyInstaller build spec
│   ├── run_desktop_webview.py   # Python WebView + OCR backend + Downloader Playwright
│   ├── index.html               # HTML entry (Vite)
│   ├── vite.config.js
│   └── package.json
│
├── Aplikasi/
│   └── poppler/                 # Poppler binary (PDF → gambar)
│
├── data-aset/                   # File referensi: DATA ASET RESOR 2026.pdf/.xlsx
│
├── compare_pdf_folders.py       # Utility perbandingan folder PDF
├── push_github.bat              # Push ke GitHub
├── requirements.txt             # Dependencies Python
└── README.md
```

---

## 🛠️ Deskripsi Peran Komponen

### 1. `web-app/` (React SPA + Vite)
Adalah **project utama** Sintelis Utility. React single-page application yang berjalan di browser WebView.
- **Peran**:
  - Drag & drop / pilih file PDF (Menu 1)
  - Render PDF via PDF.js di browser & panggil API OCR ke backend Python
  - Deteksi tipe dokumen → rename otomatis
  - **Audit & Monitoring Kelengkapan Aset** (`AssetAuditPanel.jsx` & `masterAssets.js`)
  - **Downloader Otomatis P3-STE** (`P3STEDownloader.jsx`) dengan multi-akun & kontrol proses
  - Simpan hasil ke folder atau download ZIP
  - Export hasil audit / log ke Excel (XLSX)

### 2. `run_desktop_webview.py` (Python Backend + Native Window)
Backend Python yang menjalankan:
- **Tesseract OCR** via `/api/ocr` endpoint (pytesseract + pdf2image)
- **WebView window** — native desktop window yang me-load React build
- **Static file server** — serve `dist/` folder
- **Poppler path** — mengarah ke `Aplikasi/poppler/` untuk konversi PDF→gambar

### 3. `detector.js` (OCR Detection Logic)
Mirror dari logika `detect_doc()` Python, dijalankan di browser:
- 15 branch deteksi: Wesel, Sinyal, AXC, Serat Optik (ER/JPL), PDSE, PTDS, PTLS, PTLP, CTC-CTS, Catu Daya, Radio Basestation, Waystation, Pintu Perlintasan, Point Lock
- Regex matching + keyword detection dari teks hasil OCR

### 4. `compare_pdf_folders.py`
Utility pembanding isi dua folder PDF untuk mencari file yang hilang/tidak lengkap.

---

## 💾 File Data Lokal

- **Aplikasi/poppler/**: Binary Poppler untuk `pdf2image` mengkonversi PDF ke gambar sebelum OCR.
- **data-aset/**: File referensi `DATA ASET RESOR 2026.pdf` dan `.xlsx` — acuan resmi UPT Resor Sintelis 1.21 BOO.

---

## 🔄 Koneksi Antar Note

- [[22_Logika_OCR]] — Detail alur OCR & deteksi dokumen
- [[34_Sintelis_Utility]] — Ringkasan teknis & build
- [[35_Aturan_Serat_Optik_OTB]] — Aturan lengkap SO OTB
- [[11_Menjalankan_Aplikasi]] — Cara menjalankan
- [[00_Dashboard|Kembali ke Dashboard]]
