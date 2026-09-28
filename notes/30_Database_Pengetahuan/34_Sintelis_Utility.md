# Sintelis Utility — Ringkasan Proyek

#knowledge #proyek #referensi

## Tentang App
- **Nama**: Sintelis Utility
- **Versi**: 2.0.0
- **Fungsi**: OCR PDF + rename otomatis file menggunakan pola regex untuk dokumen maintenance/pengawasan
- **Tipe**: Desktop EXE (React SPA + Python WebView, PyInstaller bundle)
- **Framework**: React + Vite (frontend), Python WebView + Tesseract + Playwright (backend)

## Fitur Inti
1. **Menu 1: OCR PDF & Rename Otomatis** — drag & drop PDF, 15 branch deteksi tipe dokumen, rename otomatis sesuai pola aset & lokasi.
2. **Audit & Monitoring Kelengkapan Aset (Menu 1)** — integrasi master data 394+ aset SAP Resor 1.21 BOO (398 file bulanan, 3-bulanan, 6-bulanan, 1-tahunan), dual-source (hasil rename vs folder komputer lokal), filter kurang saja, dan ekspor laporan Excel 3 sheet.
3. **Menu 2: Downloader Otomatis P3-STE** — otomasi unduh laporan PDF dari website P3-STE via Playwright/Requests, multi-akun login persisten, auto-retry adaptif saat server HTTP 500, sweep queue coba ulang file gagal, dan penomoran otomatis nama file duplikat ` (2)`, ` (3)`.
4. **Tombol Global Hentikan Proses** — mematikan browser engine, thread download, dan proses OCR serentak.
5. **Real-time Log & Progress Bar** — pembaruan progres dinamis real-time (persentase & jumlah file).
6. **Save on Demand** — simpan langsung ke folder tujuan atau unduh ZIP.
7. **Export Excel Multi-Sheet** — rekapitulasi audit dan log ke file XLSX.

## UI Design
- **Typography**: Segoe UI 13-18pt (judul), Consolas 13pt (log/code)
- **Warna kontras tinggi**: putih, neon hijau `#66ff66`, merah `#ff4444`, biru `#88ccff`
- **Dark theme premium**: glassmorphism + dynamic animations
- **Tata letak**: 2 kolom (kiri: input/file list, kanan: tab hasil + log)
- **Log textbox**: konsolas 13pt, bg hitam, bisa di-scroll

## Struktur File
```
web-app/
├── src/
│   ├── App.jsx              # Komponen utama UI
│   ├── index.css            # Premium dark theme CSS
│   ├── main.jsx             # Entry point React
│   └── utils/
│       ├── detector.js      # detectDoc() — 15 branch deteksi
│       ├── pdfProcessor.js  # PDF.js render + ekstrak teks
│       └── fsHandler.js     # File System Access API + ZIP handler
├── dist/                    # Vite build output (production)
├── build_exe.spec           # PyInstaller spec untuk desktop EXE
├── run_desktop_webview.py   # Python WebView + API OCR backend
├── index.html               # HTML entry (Vite)
├── vite.config.js
└── package.json
```

## Build
```powershell
cd web-app

# 1. Build React
npm run build

# 2. Build EXE (PyInstaller)
pyinstaller build_exe.spec
```

Output: `dist_exe/SintelisUtility.exe`

## Teknikal Info
- **Python**: 3.10+
- **Node.js**: 18+
- **Dependencies**: React, Vite, PDF.js, pytesseract, pdf2image, Pillow
- **PyInstaller**: bundling Python backend + Tesseract + Poppler + React static files

## Common Issues
1. **EXE terkunci saat build ulang** → `taskkill /f /im "Sintelis Utility.exe"` + delete cache
2. **Tesseract error** → pastikan `tesseract.exe` terinstall di `C:\Program Files\Tesseract-OCR\`
3. **Poppler error** → pastikan `Aplikasi/poppler/` ada dan path di `run_desktop_webview.py` benar
4. **React build gagal** → cek `node_modules`, jalankan `npm install` ulang
