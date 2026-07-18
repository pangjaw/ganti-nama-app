# Sintelis Utility — Ringkasan Proyek

#knowledge #proyek #referensi

## Tentang App
- **Nama**: Sintelis Utility
- **Versi**: 2.0.0
- **Fungsi**: OCR PDF + rename otomatis file menggunakan pola regex untuk dokumen maintenance/pengawasan
- **Tipe**: Desktop EXE (React SPA + Python WebView, PyInstaller bundle)
- **Framework**: React + Vite (frontend), Python WebView + Tesseract (backend)

## Fitur Inti
1. **Drag-drop PDF** — drop file/folder langsung dari OS
2. **OCR** — Python backend: `pdf2image` + `pytesseract` (engine tesseract)
3. **Deteksi Dokumen** — `detector.js`: 15 branch regex + keyword matching
4. **Pola Rename** — regex untuk `JPL`, `PTPP`, `BTP`, `BD`, dll
5. **Real-time Log** — `progress_callback` streaming log ke UI tiap file
6. **Save on Demand** — proses selesai → user klik **💾 Simpan** → baru extract ke folder output
7. **Tabel 3 Tab**: "📎 File Input" | "✅ Berhasil" | "⚠️ Error" — berjejer
8. **Counter** — emoji ✅ / ⚠️ di tiap tab
9. **Export Excel** — export hasil/error ke XLSX dengan 3 sheet

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
