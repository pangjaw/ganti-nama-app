# 🏃 Panduan Menjalankan Aplikasi

#panduan #setup

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

Note ini menjelaskan cara menjalankan **Sintelis Utility** — aplikasi desktop OCR & rename PDF.

---

## 📋 Prasyarat Sistem

1. **Python 3.10+** (untuk backend OCR)
2. **Tesseract OCR** — install ke `C:\Program Files\Tesseract-OCR\tesseract.exe`
   - Pastikan bahasa `ind` dan `eng` terinstall
3. **Node.js 18+** (untuk development React)
4. **Poppler** (tersedia di `Aplikasi/poppler/`)

---

## 🛠️ Instalasi Dependencies

```powershell
# Python dependencies
pip install -r requirements.txt

# Node dependencies (hanya untuk dev mode)
cd web-app
npm install
```

---

## 🚀 Cara Menjalankan

### 1. Production: EXE Portable (Rekomendasi)

Double-click `SintelisUtility.exe` di folder output build.
- Tidak perlu install Python atau Node.js
- Semua dependencies sudah dibundling oleh PyInstaller
- Window native (WebView) langsung terbuka

### 2. Development: React Dev + Python Backend

```powershell
# Terminal 1 — Python backend (OCR API + WebView)
cd web-app
python run_desktop_webview.py

# Terminal 2 — React dev server (optional, untuk hot-reload)
cd web-app
npm run dev
```

- React dev server: `http://localhost:5173`
- Python API: `http://localhost:8765`
- WebView window akan otomatis terbuka

### 3. Build EXE Baru

```powershell
cd web-app

# 1. Build React (Vite)
npm run build

# 2. Build EXE (PyInstaller)
pyinstaller build_exe.spec
```

Output: `dist_exe/SintelisUtility.exe`

---

## 🔄 Koneksi Antar Note

- [[21_Struktur_Proyek]] — Detail peran setiap komponen
- [[22_Logika_OCR]] — Alur OCR & deteksi dokumen
- [[34_Sintelis_Utility]] — Info teknis & versi
- [[41_Rencana_Perbaikan]] — Backlog pengembangan
- [[00_Dashboard|Kembali ke Dashboard]]
