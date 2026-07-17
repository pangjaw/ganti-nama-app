# 📜 Riwayat Pembaruan Script WO

#task #playwright #changelog

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

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

### 🔧 Tahap 8 — Ekspansi Deteksi OCR Multi-Tipe (15 Juli 2026)
*   **Perubahan**: Menambahkan deteksi OCR untuk 5 tipe dokumen baru + perbaikan bug:
    *   **Serat Optik ER/ER TELKOM** — Deteksi identifier `ER` dan `ER TELKOM` dari TRA lines, dengan dedup suffix `(n)` untuk multi-aset
    *   **CTC-CTS** — Branch baru dengan kode `BPBYE4`
    *   **Sistem Waystation** — Branch baru dengan kode `BPBKS5`
    *   **Radio Basestation** — Branch baru dengan 3 sub-tipe: `BPBKF1` (standar), `BPBKF2` (Digital), `BPBKF3` (Tait)
    *   **Bug fix**: `get_standard_loc()` sekarang mendeteksi abbreviation `CLT` untuk Cilebut
*   **Tujuan**: Mencakup semua tipe dokumen P3-STE 2026 yang sebelumnya tidak terdeteksi. Scan 194 file → 193 passed (1 PINTU PERLINTASAN dengan loc kosong — acceptable).
*   **Backup**: Semua script di-backup ke folder `backup_20260715_123116/`

### 🐛 Tahap 9 — Perbaikan Logika PTLS & Encoding Response (15 Juli 2026)
*   **Perubahan**:
    *   `get_ptls_loc()` — logika PTLS diubah: cari `LUAR` di judul, lalu cari `LOKASI` di bawahnya (bukan dari aset TWR/TRA). Special map `DEPOK` → `BOO`.
    *   `X-Files`/`X-Errors` header di-encode ASCII-safe — fix `UnicodeEncodeError: latin-1` saat download multi-file.
*   **Tujuan**: PTLS Depok sebelumnya salah jadi `DPOK` (karena LOKASI field menulis DEPOK, tapi aset BOO). Sekarang ambil dari LOKASI field. Fix encoding agar emoji ⚠️❌ di error message tidak crash Flask.

---

## 🔄 Koneksi Antar Note

- [[41_Rencana_Perbaikan]] — Rencana pengembangan berikutnya
- [[12_Otomasi_Work_Order]] — Panduan penggunaan script ini
- [[23_Otomasi_Browser_Playwright]] — Mekanisme browser yang digunakan
- [[31_Mapping_Checklist]] — Mapping yang diaplikasikan
- [[00_Dashboard|Kembali ke Dashboard]]

---

## 🔄 Koneksi Antar Note

- [[41_Rencana_Perbaikan]] — Rencana pengembangan berikutnya
- [[12_Otomasi_Work_Order]] — Panduan penggunaan script ini
- [[23_Otomasi_Browser_Playwright]] — Mekanisme browser yang digunakan
- [[31_Mapping_Checklist]] — Mapping yang diaplikasikan
- [[00_Dashboard|Kembali ke Dashboard]]

### 🎯 Tahap 10 — Fix PTPP: Table Noise, Regex Alphanumeric, Single-Output (16 Juli 2026)
* **Perubahan** di `app.py`:
  * **Regex `extract_jpl_assets`**: `(\d+)` → `([0-9]+[A-Z]*)` — sekarang bisa tangkap `26N` (alphanumeric), bukan cuma `26`.
  * **Table boundary truncation** untuk PTPP: Semua teks setelah `NO ITEM` / `ITEM PERAWATAN` dipotong sebelum `extract_jpl_assets`. Ini membunuh false positive "JPL 1" dan "JPL 14" yang berasal dari tabel item perawatan.
  * **Single-output enforcement**: PTPP hanya ambil asset pertama, karena 1 foto PTPP = 1 baris = 1 output file.
  * **BJD added to `loc_codes`**: Bojonggede (`BJD`) sekarang dikenali sebagai kode lokasi.
* **Hasil Test** (4 file PTPP sample):
  * `PERAWATAN PTPP JPL 1 17-01-2026.pdf` → ✅ **JPL 26N BJD-CLT** (dulu: JPL 1)
  * `PERAWATAN PTPP JPL 1 27-01-2026.pdf` → ✅ **JPL 07 BOP-BTT** (dulu: JPL 1)
  * `PERAWATAN PTPP JPL 14 26-01-2026.pdf` → ✅ **JPL 27 BOO-CLT** (dulu: JPL 14)
  * `PERAWATAN PTPP JPL 01 BOO 28-01-2026.pdf` → ✅ **JPL 01 BOO** (tetap benar)

### 🎯 Tahap 11 — SO ER OTB Range Naming & JPL Multi-Asset Detection (17 Juli 2026)
* **Perubahan** di `app.py`:
  * **SO ER OTB Range**: Nama file pakai OTB range dari OCR (misal `OTB 1-10`) bukan suffix `(n)`.
    * `detect_doc` ekstrak `otb_min`/`otb_max` dari SEMUA angka OTB di OCR text.
    * Loop `process_files` bangun identitas `SERAT OPTIK OTB {min}-{max} ER LOKASI`.
    * Duplikat handler skip file dgn range sama untuk lokasi & tgl sama.
  * **JPL Multi-Asset**: Scan OCR `TRA` lines untuk extract JPL, bukan hanya filename.
    * File `JPL 15, JPL 16 Cigombong` → jadi 2 file: `JPL 15 CGB` + `JPL 16 CGB`.
    * File `Bogor 07,BNR` → jadi 2 file: `JPL 07 BOO` + `JPL BNR BOO`.
    * JPL standalone tetap 1 file = 1 output.
  * **Duplicate handler aktif**: File dgn OTB range & lokasi sama di-skip + WARNING log.
* **Hasil Tes** (84 PDF SO → 27 file output):
  * 9 JPL files (dari 7 input, 2 input pecah jadi 2 JPL)
  * 16 ER files (OTB range terdeteksi beda2)
  * 2 bulanan files (non-JPL, non-ER)
  * 0 error, semua duplikat di-handle dengan benar
* **JANUARI 2026 (383 file)**: siap test batch full.
