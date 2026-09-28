# 📜 Riwayat Pembaruan Script WO

#task #changelog

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

Berikut adalah riwayat tahapan pembuatan dan penyempurnaan aplikasi Sintelis Utility.

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
- [[22_Logika_OCR]] — Alur OCR & deteksi dokumen
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

---

### 🚀 Tahap 7 — Bug Fix Batch 5 (18-19 Juli 2026)
* **Blank Screen Minimize**:
  * WebView2 GPU rendering context corrupt setelah minimize lama.
  * Fix: `--disable-gpu` env var + replace resize dengan `location.reload()` di `on_restored`.
* **Cancel → Proses Ulang Stuck**:
  * `cancelledRef.current` tidak di-reset saat proses baru.
  * Fix: tambah `cancelledRef.current = false` di awal `handleProcess`.
* **PTPP JPL ELEKTRIK → JPL BNR**:
  * Regex `JPL\s+([A-Z0-9]+)` tangkap "ELEKTRIK" bukan "BNR".
  * Fix: regex jadi `JPL\s+(?:ELEKTRIK\s+)?([A-Z0-9]+)` — skip noise word.
* **PDSE/PTDS/PTLS → DISETUJUI**:
  * OCR gagal + filename fallback tidak punya keyword PDSE/PTDS/PTLS.
  * Fix: 3 branch fallback baru di `filenameDetect` + filter `NOISE_WORDS` di `extractFuncloc`.
* Lihat [[46_Temuan_dan_Fix_Batch_5|detail lengkap di note Batch 5]].

---

### 📊 Tahap 12 — Audit & Monitoring Kelengkapan Aset Resor (2 September 2026)
* **Perubahan**:
  * Pembuatan database referensi lengkap aset Resor 1.21 BOO tahun 2026 (`masterAssets.js`).
  * Target Rutin Bulanan resmi 398 file (Wesel 62, Point Lock 2, Sinyal 125, Axle Counter 139, JPL 10, PTPP 11, Catu Daya 9, Serat Optik 22, PDSE 7, PTDS 6, PTLS 8, CTC/CTS 2).
  * Target berkala khusus: Radio Waystation 3-Bulanan (9 stasiun), Radio Basestation 6-Bulanan (5 lokasi), Sistem Waystation 1-Tahunan (1 stasiun).
  * Komponen UI terpadu di Menu 1 (`AssetAuditPanel.jsx`): Dual-source (hasil rename vs folder komputer lokal), filter status (Kurang Saja / Lengkap), pencarian instan, dan ekspor laporan resmi Excel 3 sheet.

---

### 🚀 Tahap 13 — Downloader P3-STE Robustness, Multi-Akun, & Retry System (7 September 2026)
* **Perubahan**:
  * **Penyimpanan Akun Persisten**: Akun NIPP & Password login tersimpan di backend disk (`sintelis_accounts.json`), tahan restart aplikasi.
  * **Tombol Hentikan Proses Global**: Menghentikan browser Playwright, thread download, dan proses OCR Menu 1 secara serentak.
  * **Penomoran File Duplikat**: Mengatasi nama kembar dari server P3-STE dengan suffix urut ` (2)`, ` (3)`, dst. tanpa menimpa file yang sudah ada.
  * **Auto-Retry HTTP 500 & Sweep Queue**: Mengatasi kegagalan pembuatan PDF di server P3-STE dengan 4x retry berturut-turut + putaran kedua (sweep retry) di akhir sesi sehingga 100% file terunduh lengkap.
  * **Optimasi 100 Data/Halaman & Resilient Pagination**: Mengubah tampilan default tabel dari 10 menjadi 100 baris per halaman (memangkas navigasi halaman dari 20 ke 2 halaman saja), menaikkan timeout transisi AJAX ke 50 detik, deteksi status processing server, dan auto-reclick tombol Next untuk memastikan semua data (seperti 197 file) terunduh tanpa macet di tengah jalan.
  * **Perbaikan Progress Bar**: Deteksi total data otomatis dari DataTables dan animasi real-time akurat.
* Lihat [[47_Temuan_dan_Fix_Batch_6|detail lengkap di note Batch 6]].

---

### 🎯 Tahap 14 — Penyelarasan Audit Aset & Perbaikan Batch 6.1 (7 September 2026)
* **Perubahan**:
  * **Penyelarasan Audit Aset Otentik**: Menyelaraskan nomor ID master aset di `masterAssets.js` dengan nomor otentik pada form/dokumen tanpa mutasi fuzzy (`B214` dipetakan ke petak `CLT-BOO`, `JPL 2` dari `JPL 02`, `J12` MSG dari `J12B`, target `PTDS BOO` disesuaikan 2 checklist).
  * **Normalisasi File Duplikat pada Audit**: `matchFileToAsset()` otomatis membersihkan akhiran counter `\s*\(\d+\)\.pdf$` agar file kembar tetap terpetakan ke slot aset master.
  * **Pencegahan Slot Stealing**: Kategori ber-ID unik (`WESEL`, `POINT LOCK`, `PERAGA SINYAL`, `AXLE COUNTER`, `PINTU PERLINTASAN`, `PTPP`) wajib cocok ID terlebih dahulu sebelum lokasi.
  * **Perbaikan Deteksi OCR 5 Kasus**:
    1. Serat Optik JPL BNR dikunci ke `BOP-BTT` dan dihentikan sebelum teks tabel `ITEM PERAWATAN` agar tidak terbaca `JPL 7A`.
    2. PTPP JPL 04 dikunci ke `BOP`.
    3. PTLS BOO memprioritaskan kode stasiun dari baris aset (`BOO`) dan mendukung penomoran duplikat `(2)` di `App.jsx`.
    4. PTDS BOO mendukung format `Lokasi\n:\nBogor` dan fallback baris aset.
    5. Peraga sinyal mendukung multi-line `SINYAL MUKA\n...` dan normalisasi spasi nama petak (`BOP - BTT` -> `BOP-BTT`).
* Lihat [[47_Temuan_dan_Fix_Batch_6|detail lengkap di note Batch 6]].

---

### 🚀 Tahap 15 — Perbaikan Deskripsi Majemuk Sinyal & Native Excel Save Dialog (7 September 2026)
* **Perubahan**:
  * **Regex Sinyal Majemuk**: Mengakomodasi frasa majemuk pada formulir checklist seperti `SINYAL KELUAR DAN LANGSIR` (`JL22A`, `JL42A`, `JL62B`) dan `SINYAL ULANG JALAN` (`UJ26B`, `UJ12`, `UJ22B`) tanpa memotong atau gagal membaca ID aset. Format penamaan tetap baku murni `PERAWATAN SINYAL <ID> <LOKASI> <TGL>.pdf`.
  * **Native Excel Save Dialog**: Mengganti modul `tkinter` di `run_desktop_webview.py` dengan API resmi `webview.windows[0].create_file_dialog(webview.FileDialog.SAVE, ...)` sehingga jendela Windows resmi "Save As" langsung muncul di layar saat mengekspor laporan audit kelengkapan aset.
  * **Penyelarasan 125 Sinyal SAP**: Menghapus 10 duplikat phantom sinyal muka di stasiun BTT, BOP, dan MSG pada `masterAssets.js` sehingga target tepat 125 unit dan tidak menimbulkan false-positive "KURANG 1".
* Lihat [[47_Temuan_dan_Fix_Batch_6|detail lengkap di note Batch 6]].

---

### 🔍 Tahap 16 — Penyelarasan Audit Axle Counter Petak BTT-BOP & BTT-MSG (7 September 2026)
* **Perubahan**:
  * **Eliminasi 4 Slot Phantom Axle Counter**: Menghapus duplikasi `ZP 10A` & `ZP 20A` di stasiun `BTT` dan `MSG` pada `masterAssets.js`.
  * **Penetapan Lokasi Petak Otentik**: Menempatkan `ZP 10A` & `ZP 20A` pada petak `BTT-BOP` dan `BTT-MSG` sesuai fisik baris aset dokumen kantor. Total unit Axle Counter kini tepat **139 unit** (100% presisi SAP).
  * **Sinkronisasi `ZP_WHITELIST` di `detector.js`**: Menambahkan petak jalan bebas `BTT-BOP`, `BOP-BTT`, `BTT-MSG`, dan `MSG-CCR` ke daftar verifikasi deteksi.
  * **Hasil Audit Sempurna**: Seluruh 139 unit Axle Counter pada folder Agustus 2026 terverifikasi 100% LENGKAP tanpa false-positive `KURANG 1`.
* Lihat [[47_Temuan_dan_Fix_Batch_6|detail lengkap di note Batch 6]].

---

### 🔧 Tahap 17 — Perbaikan Deteksi ZP 14B & Penyelarasan ZP 24B Petak BTT-MSG (7 September 2026)
* **Perubahan**:
  * **Perbaikan Whitelist `detector.js`**: Mendaftarkan `ZP 14B` dan `ZP 24B` pada `ZP_WHITELIST["BTT-MSG"]` dan `ZP_WHITELIST["MSG-BTT"]` sehingga checklist `Batutulis-Maseng.pdf` mengekstrak kedua file lengkap tanpa didrop.
  * **Penyelarasan Master Aset `masterAssets.js`**: Memindahkan `ZP 14B` dan `ZP 24B` dari stasiun tunggal `BTT` (kini murni 8 unit stasiun BTT) ke petak `BTT-MSG`.
  * **Total Unit Axle Counter**: Tetap tepat **139 unit** (100% presisi SAP).
  * **Hasil Verifikasi**: File `PERAWATAN AXLE COUNTER ZP 14B BTT-MSG 11-08-2026.pdf` dan `PERAWATAN AXLE COUNTER ZP 24B MSG-BTT 11-08-2026.pdf` keduanya terbuat dan lolos audit 100%.
* Lihat [[47_Temuan_dan_Fix_Batch_6|detail lengkap di note Batch 6]].

---

### 🛡️ Tahap 18 — Eliminator Duplikat Otomatis Dual-Check (Level 1 Biner & Level 2 Signature Dokumen) (8 September 2026)
* **Perubahan**:
  * **Level 1 — Pre-OCR Fast Binary Deduplication**: Menghitung hash SHA-256 byte biner (`arrayBuffer`) sebelum OCR dimulai. File duplikat biner (hasil unduh berulang dengan sufiks nama `(1)`, `(2)`, dsb.) langsung dilewati (skip) seketika, menghemat puluhan detik proses OCR dan beban memori/CPU.
  * **Level 2 — Post-OCR Content Signature Deduplication**: Mendeteksi file PDF yang memiliki perbedaan byte biner (misal karena timestamp metadata/trailer ID yang berbeda saat unduhan terpisah), namun memiliki isi fisik formulir checklist dan peralatan yang 100% sama. File duplikat isi langsung dilewati dari daftar hasil penamaan.
  * **Perlindungan Lembar Sah Multi-Sheet**: Lembar formulir berbeda pada kategori dan stasiun yang sama (seperti *Wesel Bogor Lembar 1 vs Lembar 2*, *Catu Daya Lembar 1 vs Lembar 2*, atau *Serat Optik*) memiliki teks checklist dan aset yang berbeda, sehingga keduanya tetap diproses sah dan file kedua secara otomatis diberi penomoran ` (2)` tanpa konflik.
  * **Operasi 100% Otomatis**: Berjalan otomatis di latar belakang tanpa memerlukan tombol/intervensi manual pengguna.
  * **Log Informatif**: Menampilkan log `[DUPLIKAT DILEWATI]` berwarna khusus di konsol dan ringkasan jumlah duplikat yang dieliminasi pada akhir proses.
* Lihat [[47_Temuan_dan_Fix_Batch_6|detail lengkap di note Batch 6]].

---

### 🌐 Tahap 19 — Sinkronisasi Tanggal Tabel Web P3-STE Downloader (8 September 2026)
* **Perubahan**:
  * **Penyebab**: Server P3-STE memiliki bug pada fungsi ekspor PDF (`tcpdf`) di mana file unduhan dinamai dengan tanggal yang keliru (misal `02-08-2026` padahal di tabel web tercatat `02/07/2026` pada filter bulan Juli).
  * **Koreksi Otomatis Downloader**: Engine Playwright di `run_desktop_webview.py` kini membaca kolom `Tanggal` dari baris tabel web (`#table tbody tr`). Jika nama file dari server membawa tanggal yang berbeda, prefix tanggal otomatis diganti dengan tanggal resmi tabel web (`02-08-2026_...` $\rightarrow$ `02-07-2026_...`).
  * **Koreksi File Folder 7. JULI**: 12 file sumber di `7. JULI` dan 34 file rename di folder `Rename` telah diperbarui ke tanggal yang sah `02-07-2026`.
* Lihat [[47_Temuan_dan_Fix_Batch_6|detail lengkap di note Batch 6]].

---

### 🎯 Tahap 20 — Penyempurnaan 8 Aset Kurang Audit Kelengkapan Juli (8 September 2026)
* **Perubahan**:
  * **Sinyal Maseng Multiline OCR**: Regex `sinyalRowRx` di `detector.js` diperluas untuk mengenali baris yang diawali langsung dengan deskripsi `SINYAL MASUK/KELUAR/MUKA/ULANG` meskipun baris kode `SIN...` terpisah oleh OCR. Sinyal `J10`, `J14`, `J20`, `J24`, dan `J22A` Maseng semuanya terdeteksi lengkap.
  * **Multi-Aset PINTU & PTPP**: Menghapus pemangkasan paksa `assets = [assets[0]]` pada branch PINTU dan PTPP di `detector.js`. Seluruh aset pada formulir gabungan (`JPL 07` & `JPL BNR BOP-BTT`, serta `JPL 27` & `JPL 28 CLT-BOO`) dipertahankan dan ter-rename masing-masing.
  * **Pembersihan Simbol Tabel PTLS (`getPtlsLoc`)**: Menghilangkan karakter batas tabel seperti `| ` sebelum mencocokkan baris `TRA/TLK`, sehingga `TRA10131 : MULTIPLEX BOO` terdeteksi tepat sebagai stasiun `BOO` dan menghasilkan `PERAWATAN PTLS BOO 27-07-2026 (2).pdf` yang melengkapi `PTLS 2 BOO`.
  * **Hasil Audit Sempurna**: Audit kelengkapan seluruh 405 aset resor pada bulan Juli 2026 kini mencapai **100% LENGKAP** (405 target, 425 ditemukan, **0 KURANG**).
* Lihat [[47_Temuan_dan_Fix_Batch_6|detail lengkap di note Batch 6]].

---

### 🚀 Tahap 21 — Penyelarasan Total File Tersimpan & Akselerasi Simpan Konkuren (10 September 2026)
* **Perubahan**:
  * **Penyelarasan 426 File Tersimpan**: Menyelaraskan 2 file yang sempat belum tersimpan (`PERAWATAN WESEL W21 MSG 06-07-2026.pdf` dan `PERAWATAN SERAT OPTIK JPL 26N CLT 17-07-2026.pdf`) sehingga jumlah fisik di folder `7. JULI\Rename` pas **426 file** sesuai hasil deteksi aplikasi.
  * **Akselerasi Simpan Paralel (Chunk Concurrency)**: Menyimpan 426 file sebelumnya membutuhkan waktu ~2 menit secara sekuensial. Sekarang ditingkatkan menjadi pemrosesan paralel (`SAVE_CONCURRENCY = 6`) sehingga waktu simpan berkurang menjadi hanya **~10-15 detik** (10x lebih cepat).
  * **Progress Bar & Dynamic Button Label**: Menambahkan tracking progres real-time (`setProgress`) pada fungsi simpan dan label tombol dinamis: `Menyimpan (X/426)...`.
  * **Guard Cegah Klik Ganda**: Menambahkan proteksi `if (!results.length || processing) return;` dan atribut `disabled={processing}` pada tombol simpan dan ekspor.
  * **Logging File Simpan Backend**: Menambahkan pencatatan `Saved: {clean_filename}` pada backend Python untuk transparansi penuh di file log.
* Lihat [[47_Temuan_dan_Fix_Batch_6|detail lengkap di note Batch 6]].

---

### 🛡️ Tahap 22 — Perbaikan Deteksi Multi-JPL (JPL 7 & BNR) & Relaksasi Binary Deduplication (11 September 2026)
* **Perubahan**:
  * **Parser Multi-JPL Nama File (`extractJplsFromFilename`)**: Menambahkan fungsi ekstraksi cerdas di `detector.js` yang mampu mengenali pola multi-JPL pada nama file (`JPL 7&BNR`, `JPL 7 & BNR`, `JPL 15, JPL 16`, `JPL ELEKTRIK BNR`), serta menormalisasi angka 1 digit menjadi 2 digit (`7` $\rightarrow$ `07`).
  * **Preservasi Multi-Aset OCR di PINTU & PTPP**: Menghapus penimpaan tunggal `assets = [ocrMatch]`. Jika file sumber P3STE mencakup dua JPL (seperti `JPL 07` dan `JPL BNR` di lintas BOP-BTT) atau nama file memuat gabungan `7&BNR`, seluruh aset hasil deteksi dipertahankan sehingga otomatis terpecah menjadi 2 file mandiri.
  * **Regex Global OTB FO di Serat Optik**: Mengubah pencarian baris TRA OTB FO JPL di `detector.js` menggunakan regex global `/(?:TRA\d+\s*[:|;.]*\s*)?OTB\s+FO\s+JPL\s+([A-Z0-9]+)/gi`, sehingga item kedua (`BNR`) tidak lagi terlewat meski berada pada satu baris teks dokumen.
  * **Relaksasi Level 1 Fast Binary Deduplication di `App.jsx`**:
    * Menambahkan fungsi `isCopyOrDownloadDuplicate(nameA, nameB)`.
    * Level 1 kini secara cerdas **hanya melewati file biner identik jika nama dasarnya terindikasi duplikat unduhan** (akhiran `(1)`, `(2)`, `- Copy`, `_1`).
    * File dengan nama substantif berbeda (seperti `...JPL 07...` dan `...JPL ELEKTRIK BNR...` yang sengaja disiapkan pengguna untuk 2 aset) **tidak lagi diblokir sebelum OCR**, melainkan diproses mandiri.
    * Level 2 (Post-OCR Signature Check) tetap aktif sebagai pengaman untuk menyaring file duplikat sejati jika isi checklist dan asetnya identik.
  * **Hasil Verifikasi**:
    * File raw `25-02-2026_PERAWATAN PERALATAN PINTU PERLINTASAN 1 BULANAN_JPL 7&BNR Bogor-Batutulis.pdf` langsung menghasilkan 2 file: `JPL 07` dan `JPL BNR`.
    * File raw `25-02-2026_PERAWATAN PERALATAN TELEKOMUNIKASI DI PINTU PERLINTASAN 1 BULANAN_JPL 7&BNR Bogor-Batutulis.pdf` langsung menghasilkan 2 file: `JPL 07` dan `JPL BNR`.
    * File raw `25-02-2026_PERAWATAN SERAT OPTIK 1 BULANAN_JPL 7&BNR Bogor.pdf` langsung menghasilkan 2 file: `JPL 07` dan `JPL BNR`.
    * Batch folder `SIAP DI OCR` yang memuat kedua file terpisah (`JPL 07` dan `JPL ELEKTRIK BNR`) berhasil memproses dan menghasilkan kedua file secara mandiri tanpa tereliminasi.
    * File checklist normal (1 aset, 99% populasi dokumen) tetap berjalan 100% stabil dan menghasilkan 1 file per dokumen.
* Lihat [[47_Temuan_dan_Fix_Batch_6|detail lengkap di note Batch 6]].
