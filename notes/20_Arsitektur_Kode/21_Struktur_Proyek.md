# 📂 Struktur Folder & Komponen Proyek

#arsitektur #struktur

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

Halaman ini mendokumentasikan organisasi berkas (file structure) serta peran masing-masing modul/script dalam proyek **Ganti Nama App & Otomasi P3-STE**.

---

## 📁 Pohon Direktori Utama

Berikut adalah berkas-berkas penting yang membentuk proyek ini:

```text
ganti-nama-app/
│
├── .obsidian/                  # Folder konfigurasi Obsidian Vault (Workspace ini)
├── notes/                      # Dokumentasi & basis pengetahuan proyek (Markdown)
│   ├── 00_Dashboard.md
│   ├── 10_Panduan_Penggunaan/
│   ├── 20_Arsitektur_Kode/
│   └── 30_Database_Pengetahuan/
│
├── templates/                  # Template HTML untuk web service Flask
│
├── 1-klik.bat                  # Shortcut menjalankan desktop GUI
├── download p3ste.bat          # Shortcut menjalankan download rekap via CLI
├── push_github.bat             # Shortcut push perubahan ke GitHub
│
├── app.py                      # Backend server Flask untuk OCR & Rename PDF
├── desktop_app.py              # Aplikasi desktop GUI (Tkinter) manajemen login & download
├── download_p3ste_rekap.py     # Modul inti otomasi download rekap (Playwright)
├── create_p3ste_wo.py          # Modul otomasi pengisian form Work Order (Playwright)
├── compare_pdf_folders.py      # Modul pembantu untuk membandingkan jumlah PDF di dua folder
│
├── requirements.txt            # Daftar package dependencies Python
├── packages.txt                # Kebutuhan package Linux (untuk setup docker/server)
├── Dockerfile                  # Konfigurasi containerization Flask app
│
├── .p3ste-logins.json          # [Auto-Generated] Menyimpan profil & password lokal
└── .p3ste-browser/             # [Auto-Generated] State/cookie browser Chromium Playwright
```

---

## 🛠️ Deskripsi Peran Komponen

### 1. `desktop_app.py`
Merupakan antarmuka pengguna (GUI) berbasis Tkinter yang bertindak sebagai control center.
*   **Peran**:
    *   Menampilkan status login aktif saat ini.
    *   Membuka modal `LoginDialog` (`LoginDialog` di `desktop_app.py`) untuk menambah/mengedit/menghapus konfigurasi NIPP dan password.
    *   Mengalihkan output console (`stdout`) dari library `download_p3ste_rekap.py` ke box log GUI secara real-time.
    *   Menampilkan progress bar saat proses download berjalan.

### 2. `download_p3ste_rekap.py`
Merupakan engine otomasi web untuk mengunduh berkas rekap checklist P3-STE.
*   **Peran**:
    *   Membuka browser Playwright secara asynchronous.
    *   Membaca kredensial dari `.p3ste-logins.json` untuk login ke `https://p3-ste.kai.id`.
    *   Membuka halaman Rekap Checklist, mem-filter rentang tanggal, dan memicu download PDF untuk tiap checklist.
    *   Menyimpan file PDF ke folder Downloads lokal (default: `~/Downloads/P3STE`).

### 3. `create_p3ste_wo.py`
Engine otomasi untuk mengisi form tambah program realisasi (Work Order) baru.
*   **Peran**:
    *   Membagi data input yang besar menjadi batch-batch berukuran 5 item (sesuai performa web).
    *   Mendeteksi kode stasiun/lokasi dan kode asset secara dinamis dari short text yang di-input user.
    *   Mengotomasi pembuatan form di browser Chromium Playwright agar siap direview sebelum disimpan.

### 4. `app.py`
Aplikasi web backend berbasis Flask untuk memproses penggantian nama file PDF secara otomatis menggunakan kecerdasan buatan OCR.
*   **Peran**:
    *   Menerima upload file PDF.
    *   Mengonversi halaman pertama PDF menjadi gambar menggunakan `pdf2image`.
    *   Melakukan cropping 30% area atas (lokasi header dokumen) lalu melakukan OCR text extraction dengan `pytesseract`.
    *   Menggunakan regex untuk mendeteksi tipe dokumen, kode asset, stasiun, dll.
    *   Menghasilkan file ZIP baru berisi PDF yang sudah di-rename dengan pola nama yang konsisten.

### 5. `compare_pdf_folders.py`
Utility sederhana untuk mencocokkan kelengkapan file hasil download di dua lokasi folder berbeda.
*   **Peran**:
    *   Menghitung jumlah file PDF per asset dengan cara men-strip format tanggal pada nama file.
    *   Menampilkan laporan perbandingan folder A dan B di terminal, memberi tahu folder mana yang kekurangan file untuk asset tertentu.

---

## 💾 File Data Lokal (Abaikan dari Version Control)

*   **.p3ste-logins.json**: File ini menyimpan profil NIPP, nama, dan hash password lokal yang di-input lewat GUI. **Penting:** File ini tidak boleh di-commit ke Git karena berisi informasi kredensial sensitif.
*   **.p3ste-browser/**: Direktori profil user data browser Chromium. Menyimpan cookie dan session login agar pengguna tidak perlu mengisi captcha/login berulang kali setiap kali menjalankan otomasi.
*   **templates/**: Folder template Flask (index.html) jika server diakses lewat browser. Lihat [[11_Menjalankan_Aplikasi|Panduan Menjalankan]].

---

## 🔄 Koneksi Antar Note

- [[22_Logika_OCR]] — Detail alur OCR di `app.py`
- [[23_Otomasi_Browser_Playwright]] — Detail Playwright di `download_p3ste_rekap.py`
- [[51_Alur_Kerja_Agent]] — Diagram dependency antar script
- [[32_Arsitektur_Deploy]] — File Dockerfile & firebase.json
- [[00_Dashboard|Kembali ke Dashboard]]
