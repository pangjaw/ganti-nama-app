# 🏃 Panduan Menjalankan Aplikasi

#panduan #setup

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

Note ini menjelaskan cara mempersiapkan lingkungan (environment) dan menjalankan berbagai script/aplikasi yang ada di dalam project ini.

---

## 📋 Prasyarat Sistem

Sebelum menjalankan script, pastikan komponen berikut telah terinstall:

1.  **Python 3.10+**
2.  **Tesseract OCR** (untuk modul OCR di `app.py`)
    *   **Windows**: Install ke `C:\Program Files\Tesseract-OCR\tesseract.exe` (atau sesuaikan path-nya di `app.py`). Pastikan menambahkan support bahasa `ind` dan `eng`.
    *   **Linux**: `sudo apt install tesseract-ocr tesseract-ocr-ind`
3.  **Poppler** (prasyarat untuk `pdf2image` dalam konversi PDF)
    *   **Windows**: Unduh poppler binary dan tambahkan path `bin/` ke Environment Variables sistem Anda.

---

## 🛠️ Instalasi Dependencies

Jalankan perintah berikut di terminal/Powershell untuk mengunduh library yang dibutuhkan:

```powershell
# Menggunakan requirements.txt
pip install -r requirements.txt

# Pastikan Playwright browser terinstall (digunakan untuk otomasi web)
playwright install chromium
```

---

## 🚀 Cara Menjalankan Komponen

### 1. Aplikasi Desktop (GUI)
Aplikasi utama untuk mengelola login P3-STE dan mengunduh rekap checklist secara otomatis.
*   **Cara Run**:
    ```powershell
    python desktop_app.py
    ```
*   **Fitur Utama**:
    *   Manajemen akun/login dalam satu UI (Data Login).
    *   Memilih akun aktif, menambah akun baru, mengedit, atau menghapus.
    *   Tombol `Refresh` untuk menyegarkan status data login.
    *   Proses download rekap checklist dengan progress bar.
    *   Shortcut run melalui file `1-klik.bat`.

### 2. Flask OCR Web Server (`app.py`)
Web service backend untuk menerima file PDF, mendeteksi isi halaman dengan OCR, dan menghasilkan penamaan file baru yang konsisten.
*   **Cara Run**:
    ```powershell
    python app.py
    ```
*   *Default port*: `http://127.0.0.1:5000` (atau port Flask standar).
*   **Penggunaan**: Mengirimkan file PDF ke endpoint API atau mengakses UI templates sederhana (jika dikonfigurasi).

### 3. Otomasi Pengisian Work Order (`create_p3ste_wo.py`)
Script CLI untuk memasukkan data Work Order secara massal ke dalam sistem P3-STE.
*   **Cara Run**:
    ```powershell
    python create_p3ste_wo.py
    ```
*   **Uji Coba Mandiri (Self-Test)**:
    Untuk menguji validitas parsing waktu, pembagian batch, normalisasi teks, dan ekstraksi keyword tanpa membuka browser:
    ```powershell
    python create_p3ste_wo.py --self-test
    ```
    *Selengkapnya dapat dibaca di [[12_Otomasi_Work_Order|Panduan Otomasi Work Order]].*

### 4. Pembanding Folder PDF (`compare_pdf_folders.py`)
Script bantu untuk membandingkan isi dua folder PDF guna mencari file yang hilang/tidak lengkap berdasarkan kecocokan nama asset.
*   **Cara Run**:
    ```powershell
    python compare_pdf_folders.py --folder-a "path/ke/folder/A" --folder-b "path/ke/folder/B" --words 3
    ```
    *Parameter `--words 3` menentukan jumlah kata depan nama file yang dijadikan basis pencocokan (mengabaikan format tanggal di awal).*

---

## 🗂️ Shortcut Cepat (.bat)
Di root folder proyek, terdapat file `.bat` untuk mempermudah eksekusi:
- `1-klik.bat` → Menjalankan `desktop_app.py`.
- `download p3ste.bat` → Menjalankan script download rekap secara langsung via command line.
- `push_github.bat` → Melakukan sinkronisasi/push perubahan kode ke repository GitHub. Lihat [[32_Arsitektur_Deploy|Pipeline Deployment]].

---

## 🔄 Koneksi Antar Note

- [[21_Struktur_Proyek]] — Detail peran setiap file
- [[22_Logika_OCR]] — Alur OCR di `app.py`
- [[23_Otomasi_Browser_Playwright]] — Setup Playwright
- [[12_Otomasi_Work_Order]] — Panduan WO
- [[51_Alur_Kerja_Agent]] — Alur kerja ekosistem keseluruhan
- [[00_Dashboard|Kembali ke Dashboard]]
