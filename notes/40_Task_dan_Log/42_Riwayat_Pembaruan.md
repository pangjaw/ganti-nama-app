# 📜 Riwayat Pembaruan Script WO

Berikut adalah riwayat tahapan pembuatan dan penyempurnaan script otomasi pengisian Work Order (`create_p3ste_wo.py`).

---

## 📅 Kronologi Tahapan Update

### 🚀 Tahap 1 — Pembuatan Awal (Initial Release)
*   **Perubahan**: Script dibuat mandiri terpisah dari script rekap.
*   **Tujuan**: Menggunakan data login yang sama dengan otomasi rekap, mengisi form Tambah Program Realisasi, mendukung 3 jenis asset (`wesel`, `sinyal`, `axc`), serta mendukung input copy-paste list nama asset multiline.

### 👁️ Tahap 2 — Browser Diaktifkan Visual (Headful Mode)
*   **Perubahan**: Mengubah mode browser Playwright dari *headless* menjadi default tampil (*headful*).
*   **Tujuan**: Memungkinkan user melihat proses pengisian form secara langsung di layar monitor untuk verifikasi awal.

### 🧪 Tahap 3 — Mode Pengujian Mandiri (Test Mode Only)
*   **Perubahan**: Membatasi eksekusi sebelum proses penyimpanan.
*   **Tujuan**: Menghindari pengisian data fiktif ke database live. Script berhenti tepat sebelum mengeklik `Simpan` atau `Kirim SAP` agar user bisa mengoreksi secara manual terlebih dahulu.

### 📋 Tahap 4 — Pemetaan Kode Checklist Spesifik
*   **Perubahan**: Pencarian kode checklist diperbarui memakai label string persis.
*   **Tujuan**: Menghindari kesalahan sistem dalam memilih checklist. Opsi dropdown yang dipilih dipetakan langsung berdasarkan jenis asset:
    *   Wesel: `PERAWATAN WESEL ELEKTRIK 2 MINGGUAN - (WESEL BIASA)`
    *   Sinyal: `PERAWATAN PERAGA SINYAL ELEKTRIK 1 BULANAN - (-)`
    *   AXC: `PERAWATAN AXLE COUNTER SIEMENS 1 BULANAN - (SIEMENS)`

### 📅 Tahap 5 — Penyelarasan Tanggal Program & Realisasi
*   **Perubahan**: Logika parser input tanggal dirombak.
*   **Tujuan**: Cukup satu kali input tanggal & rentang jam. Script otomatis mengekstrak tanggal awal untuk mengisi field **Tanggal Program** dan merangkainya bersama jam untuk mengisi field **Start-Finish Date**.

### ⚡ Tahap 6 — Optimalisasi Flow Penambahan FuncLoc
*   **Perubahan**: Urutan interaksi web disesuaikan dengan behavior asli form.
*   **Tujuan**: Melakukan klik tombol `Tambah FuncLoc` berulang-ulang sampai jumlah baris sesuai jumlah asset pada batch terpenuhi, kemudian baru mengisi data di masing-masing baris secara berurutan. Ini memperbaiki masalah delay kemunculan row baru di web.

### 🔍 Tahap 7 — Peningkatan Akurasi Pencocokan Asset (Matching Logic)
*   **Perubahan**: Menambahkan fungsi pembersih teks, pencarian regex kode asset utama (`ZP60`, `W21A`, `JL92`), serta mekanisme retry menunggu dropdown siap.
*   **Tujuan**: Menghilangkan error gagal pilih opsi asset AXC/Sinyal yang sering terjadi akibat perbedaan spasi atau penulisan antara data input user dengan opsi dropdown di web. Menghindari kata penghubung seperti `DAN` dianggap sebagai kode stasiun.
