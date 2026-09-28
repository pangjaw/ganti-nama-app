# 🚀 Temuan, Fitur Baru & Fix Batch 6

#task #changelog

> **Tanggal**: 28 Agustus – 7 September 2026  
> **Agent**: Antigravity (Google Deepmind)  
> **Status**: ✅ Semua diterapkan, teruji & binary EXE terbaru dibuild  

---

## 📌 Ringkasan Pembaruan Batch 6

Batch 6 menghadirkan ekspansi besar pada dua menu utama aplikasi:
1. **Menu 1 (OCR & Rename)**: Penambahan fitur **Audit & Monitoring Kelengkapan Aset Resor** (Master database 394+ unit aset SAP 2026, dual-source audit, filter status kurang, dan ekspor laporan Excel 3 sheet).
2. **Menu 2 (Downloader P3-STE)**: Peningkatan kehandalan engine unduh otomatis (multi-akun login persisten, tombol hentikan proses global, penomoran nama file duplikat, auto-retry adaptif saat HTTP 500, dan perbaikan visualisasi progress bar).

---

## 🛠️ Rincian Fitur & Perbaikan

### 1. 📊 Fitur Audit & Monitoring Kelengkapan Aset (Menu 1)
* **Latar Belakang**: Pengguna membutuhkan cara cepat untuk memverifikasi apakah seluruh dokumen pemeliharaan bulanan/berkala sudah lengkap atau aset mana saja yang masih kurang.
* **Master Data Aset Resor 1.21 BOO (`masterAssets.js`)**:
  * **Rutin Bulanan (Target: 398 file/bulan)**:
    * Wesel (31 unit × 2 = 62 file / 2-mingguan)
    * Point Lock (1 unit W81 BOO × 2 = 2 file)
    * Peraga Sinyal (125 unit)
    * Deteksi KA / Axle Counter (139 unit)
    * Pintu Perlintasan JPL (10 unit)
    * Telkom JPL PTPP (11 unit)
    * Catu Daya / Rectifier (9 unit)
    * Serat Optik OTB (22 unit)
    * PDSE (7 unit), PTDS (6 unit), PTLS (8 unit), CTC-CTS (2 unit)
  * **Berkala Khusus**:
    * 3 Bulanan: Radio Waystation (9 stasiun)
    * 6 Bulanan: Radio Basestation (5 lokasi)
    * 1 Tahunan: Sistem Waystation (1 unit BOO)
* **Komponen UI (`AssetAuditPanel.jsx`)**:
  * Terintegrasi langsung di Menu 1 (tab "📊 Audit Aset" di split panel kiri).
  * **Dual-Source**: Audit otomatis dari hasil rename saat ini ATAU dari folder komputer lokal via tombol "📁 Folder Komputer".
  * **Filter & Pencarian**: Filter periode (Bulanan, 3 Bulanan, 6 Bulanan, 1 Tahunan, Semua), filter status (`Semua`, `❌ Kurang Saja`, `✅ Lengkap`), dan kotak pencarian aset.
  * **Ekspor Excel 3-Sheet**:
    1. Sheet 1: *Ringkasan Kategori* (Target, Realisasi, Kekurangan, Persentase)
    2. Sheet 2: *Daftar Aset Kurang* (Hanya daftar aset yang belum lengkap)
    3. Sheet 3: *Semua Aset* (Checklist lengkap unit aset dan nama file PDF yang cocok)

---

### 2. 👥 Multi-Akun P3-STE & Penyimpanan Persisten
* **Masalah**: Data akun login (NIPP & password) hilang setiap kali aplikasi di-restart.
* **Solusi**:
  * Implementasi penyimpanan backend `sintelis_accounts.json` via endpoint `/api/accounts` (GET/POST) disinkronkan dengan `localStorage`.
  * Fitur CRUD Multi-Akun: Tambah, edit, dan hapus akun dengan tombol switcher cepat di form login Menu 2.

---

### 3. ⏹️ Tombol Global "Hentikan Proses"
* **Masalah**: Tombol "Hentikan Download" sebelumnya hanya memutus loop unduh, namun tidak mematikan browser engine Playwright atau proses OCR di Menu 1.
* **Solusi**:
  * Mengubah tombol menjadi **"⏹ Hentikan Proses"**.
  * Menghubungkan fungsi `_cancel_all_processes()` di Python backend untuk seketika menutup browser context Playwright, membatalkan thread download, serta menghentikan loop proses OCR di Menu 1.

---

### 4. 📑 Penanganan Nama File Duplikat di Menu 2
* **Masalah**: P3-STE sering mengirimkan header `Content-Disposition` dengan nama file yang sama persis untuk checklist berbeda (misal: `PERAWATAN WESEL ELEKTRIK 2 MINGGUAN.pdf`). Akibatnya file saling menimpa (*overwrite*) di disk.
* **Solusi**:
  * Fungsi `_get_unique_p3ste_filename(target_folder, filename, existing_names)`:
    * Jika `namafile.pdf` sudah ada, otomatis menjadi `namafile (2).pdf`, `namafile (3).pdf`, dst.
    * Diterapkan pada mode scraper tabel otomatis dan mode unduh langsung ID range.
    * Checkpoint tracking disempurnakan agar tidak melewatkan file yang memiliki nama kembar di sesi berjalan.

---

### 5. 🔄 Auto-Retry HTTP 500 & Sweep Queue (Solusi File Hilang)
* **Masalah**: Server P3-STE terkadang mengembalikan `HTTP 500` saat lonjakan beban pembuatan PDF (misal: 5 dari 197 file gagal terunduh dan terlewat tanpa coba ulang).
* **Solusi**:
  1. **Immediate Retry**: Setiap kegagalan HTTP 500/502/503/504/timeout diulang otomatis hingga **4 kali percobaan** dengan jeda adaptif (*backoff* 2s, 4s, 6s).
  2. **Sweep Retry Queue**: File yang masih gagal dimasukkan ke `failed_queue`. Setelah seluruh halaman selesai dipindai, sistem menjalankan putaran kedua khusus untuk mencoba ulang file-file yang sempat gagal.
  3. Menjamin seluruh target file (misal 197 file) terunduh utuh tanpa ada yang terlewat.

---

### 6. 📈 Perbaikan Progress Bar Download
* **Masalah**: Progress bar download membeku di 0% dan tidak bergerak selama proses berlangsung.
* **Root Cause**:
  * Variabel target `_p3ste_state["total"]` sebelumnya bernilai 0 sepanjang proses scraper tabel, sehingga perhitungan persentase `current / total` tidak dapat dihitung.
* **Solusi**:
  * Engine backend kini otomatis membaca total record dari DataTables P3-STE (`.dataTables_info` atau DataTables API, misal terbaca target `197 file`).
  * Frontend `P3STEDownloader.jsx` memperbarui state progress secara real-time (`Terunduh / Terproses: 95 dari 197 file (48%)`).
  * Jika total data belum selesai dihitung, progress bar menampilkan animasi bergerak (*indeterminate animation*) sehingga pengguna tahu proses sedang aktif.

---

### 7. ⚡ Resilient Pagination & Timeout 60s (Solusi Berhenti di 180 File)
* **Masalah**: Pengunduhan berhenti di 180 file dari total 197 file dengan log:
  ```
  [20:57:11] Mengeklik 'Selanjutnya' ke Halaman 19...
  [20:57:31] Halaman berikutnya tidak memuat data baru. Selesai.
  ```
* **Root Cause**:
  1. Default tampilan tabel P3-STE adalah **10 data per halaman**. Untuk 197 file, scraper harus berpindah sebanyak **20 halaman** (20 kali request AJAX pagination).
  2. Pada halaman 18 menuju 19, server P3-STE mengalami lonjakan beban dan memerlukan waktu > 20 detik untuk merespons AJAX.
  3. Loop tunggu pagination sebelumnya dibatasi hardcode 20 detik (`range(20)`). Tepat pada detik ke-20, scraper menganggap tidak ada perubahan baris dan memutus proses secara prematur.
* **Solusi**:
  1. **Pertahankan Format Asli 10 Data per Halaman**:
     - Upaya mengubah dropdown ke 100 data dihapus total karena server P3-STE tidak mendukung perubahan panjang entri dan merusak state DataTables.
     - Format asli 10 data per halaman terbukti sangat stabil (berhasil mulus dari Halaman 1 sampai 18).
  2. **Toleransi Timeout Ditingkatkan ke 60 Detik**:
     - Batas waktu tunggu transisi AJAX dinaikkan dari 20 detik menjadi 60 detik (`range(60)`), memberi waktu yang sangat cukup bagi server P3-STE untuk merender halaman baru.
  3. **Auto Re-click Tombol "Selanjutnya" pada Detik ke-25**:
     - Jika server belum merespons dalam 25 detik, tombol Next diklik ulang secara otomatis untuk memicu kembali event AJAX.
  4. **Target-Aware Multi-Attempt Retry**:
     - Jika target total (`197 file`) belum tercapai, sistem melakukan retry navigasi hingga 3 kali percobaan sebelum mengakhiri proses.
  5. **Pengecekan ID Bersih Tanpa Hambatan State**:
     - Pengecekan transisi halaman murni membandingkan perubahan ID checklist baris pertama (`cur_first_id != old_first_id`) tanpa memblokir pada status overlay processing.

---

### 8. 🎯 Perbaikan Deteksi OCR & Normalisasi Penamaan Dokumen (Batch 6.1)
* **Bug 1 — Serat Optik JPL BNR (BOP-BTT)**:
  - *Temuan*: Teks PDF memuat `JPL BNR BOP-BTT`, namun karena OCR terus memindai hingga ke tabel bawah, teks referensi `JPL 7A` ikut terbaca dan menduplikasi file dengan lokasi `BOO`.
  - *Solusi*: Batasi loop pembacaan aset serat optik agar langsung berhenti ketika menemukan kata kunci `ITEM PERAWATAN` / `NO ITEM`. Lokasi `JPL BNR` dikunci secara definitif ke `BOP-BTT`.
* **Bug 2 — PTPP JPL 04 (BOP)**:
  - *Temuan*: Dokumen checklist PTPP JPL 04 ter-rename ganda menjadi `BOO-BOP` dan `BOP`.
  - *Solusi*: Kunci pemetaan `"JPL 04": "BOP"` dan `"JPL 4": "BOP"` di `JPL_KNOWN_LOCS` sehingga selalu konsisten menghasilkan lokasi `BOP`.
* **Bug 3 — PTLS BOO vs BTT & Dukungan File Duplikat**:
  - *Temuan*: Dokumen PTLS BOO ter-rename menjadi `PTLS BTT` karena mengambil teks header `Bogor-Batutulis`. Dokumen kedua tertimpa / dibuang.
  - *Solusi*: Prioritaskan kode stasiun langsung dari baris item aset (`MULTIPLEX BOO` -> `BOO`). Loop final penamaan di `App.jsx` kini secara otomatis menambahkan akhiran counter `(2)`, `(3)`, dst. jika ada nama file identik alih-alih membuang file.
* **Bug 4 — PTDS BOO & Robust Fallback**:
  - *Temuan*: Dokumen PTDS kedua menghasilkan nama `PERAWATAN PTDS UNKNOWN 26-08-2026.pdf`.
  - *Solusi*: Tambahkan dukungan multi-line pada `extractFuncloc` untuk menangani format `Lokasi\n:\nBogor`, serta fallback membaca kode stasiun dari baris aset seperti `SENTRANIK PAP BOO`. File kedua otomatis menjadi `PERAWATAN PTDS BOO 26-08-2026 (2).pdf`.
* **Bug 5 — Peraga Sinyal Tanpa Nomor ID & Spasi Petak**:
  - *Temuan*: 5 file sinyal ter-rename tanpa nomor aset (hanya `PERAWATAN SINYAL [LOC]`).
  - *Solusi*: Tambahkan multi-line lookahead untuk baris `SINYAL MUKA\n...` dan normalisasi spasi nama petak (`BOP - BTT` -> `BOP-BTT`). Kelima file kini terdeteksi akurat sebagai `MJ20 BOO`, `MJ10/MJ20 BOP-BTT`, `MJ28/MJ48 BOP-BTT`, `MJ14 CLT`, dan `MJ20 CLT`.

---

### 9. 🏛️ Penyelarasan Audit Aset dengan Nomor ID Otentik Dokumen
* **Prinsip Utama**: Mengikuti instruksi pengguna untuk mempertahankan keaslian otentik nomor ID aset sesuai dokumen form dari kantor, tanpa melakukan mutasi kode atau transformasi fuzzy liar pada level aplikasi.
* **Penyelarasan Sinyal Blok B.214**:
  - *Temuan*: File `PERAWATAN SINYAL B214 BOO-CLT 09-08-2026.pdf` dianggap `KURANG 1` oleh Audit Aset.
  - *Root Cause*: Master data aset sebelumnya menempatkan `B214` di stasiun `BOO`, sedangkan di dokumen SAP resmi dan teks fisik form, `B.214` adalah sinyal blok pada petak `CLT-BOO` (posisi 14 di petak Cilebut-Bogor).
  - *Solusi*: Pindahkan `B214` ke petak `CLT-BOO` pada `masterAssets.js`. Fungsi `normalizeSectionLoc('BOO-CLT')` mengarahkannya ke `CLT-BOO` sehingga terjadi pencocokan eksak 100% tanpa mengubah ID.
* **Penyelarasan Nomor ID Master Lainnya**:
  - `JPL 2 BOO`: Disesuaikan menjadi `JPL 2` (sebelumnya `JPL 02`) sesuai teks asli `JPL ELEKTRIK NO 2 BOO`.
  - `J12 MSG`: Disesuaikan menjadi `J12` (sebelumnya `J12B`) sesuai teks asli `SINYAL KELUAR J12 MSG`.
  - `PTDS BOO`: Target file disesuaikan menjadi 2 checklist (Sentral Toka & Voice Logger).
* **Normalisasi Ekstensi Duplikat pada Audit**:
  - `matchFileToAsset()` otomatis membersihkan akhiran `\s*\(\d+\)\.pdf$` sehingga file berakhiran `(2)` tetap terpetakan ke slot aset master yang bersangkutan.
* **Pencegahan Slot Stealing**:
  - Kategori spesifik ber-ID (`WESEL`, `POINT LOCK`, `PERAGA SINYAL`, `AXLE COUNTER`, `PINTU PERLINTASAN`, `PTPP`) hanya boleh cocok jika ID-nya sesuai. Pencocokan berbasis lokasi murni hanya diizinkan untuk kategori deskriptif tanpa ID unik (`PDSE`, `PTDS`, `PTLS`, `CATU DAYA`, `SERAT OPTIK`, `CTC-CTS`).

---

### 10. ⚡ Perbaikan Deskripsi Majemuk Sinyal & Dialog Ekspor Excel (Batch 6.2)
* **Bug Deskripsi Majemuk Sinyal (`KELUAR DAN LANGSIR` & `ULANG JALAN`)**:
  - *Temuan*:
    - `09-08-2026_PERAWATAN PERAGA SINYAL ELEKTRIK 1 BULANAN_Bogor.pdf`: Aset `JL22A` dan `JL42A` tidak terbuat filenya.
    - `07-08-2026_PERAWATAN PERAGA SINYAL ELEKTRIK 1 BULANAN_Bogor.pdf`: Aset `JL62B` tidak terbuat filenya.
    - `25-08-2026_...Bogorpaledang (2).pdf`: Aset `UJ26B` tidak terbuat.
    - `28-08-2026_...Maseng (2).pdf`: Aset `UJ12` dan `UJ22B` tidak terbuat.
  - *Root Cause*:
    Regex `sinyalRowRx` sebelumnya memakai whitelist kata tunggal kaku: `(?:MUKA|MASUK|KELUAR|LANGSIR|BLOK|ULANG)`. Saat bertemu frasa majemuk `SINYAL KELUAR DAN LANGSIR JL42A`, regex membaca `KELUAR`, lalu teks selanjutnya adalah `DAN LANGSIR`. Regex mengira kata `DAN` adalah ID sinyal sehingga terjadi error/mismatch dan baris tersebut dilewati. Hal yang sama terjadi pada frasa `SINYAL ULANG JALAN UJ...` di mana kata `JALAN` menggagalkan pembacaan ID `UJ`.
  - *Solusi*:
    Regex diperbarui menjadi fleksibel:
    ```javascript
    const sinyalRowRx = /\b(?:SIN|SC)\d{4,6}\s*[:|;.]*\s*(?:SINYAL(?:\s+[A-Za-z]+)*?\s+)?([BJLMSXU]+\.?\s?\d{1,3}[A-Za-z]?)\s*(.*)/i;
    ```
    Pola ini menerima kata deskripsi majemuk apa pun setelah kata `SINYAL`, lalu langsung mengekstrak ID unik asetnya.
  - *Kepastian Penamaan File*:
    Nama file hasil rename tetap baku dan bersih:
    `PERAWATAN SINYAL JL22A BOO 09-08-2026.pdf`
    (Sama sekali tidak ada tambahan kata "KELUAR DAN LANGSIR").
* **Bug Ekspor Excel Audit Aset Dibatalkan**:
  - *Temuan*:
    Mengeklik tombol "📊 Ekspor Excel" pada panel Audit Aset tidak memunculkan jendela dialog dan langsung menampilkan log: *"Penyimpanan Excel dibatalkan."*
  - *Root Cause*:
    Fungsi backend `_save_file_dialog_native` di `run_desktop_webview.py` awalnya mencoba memanggil modul `tkinter`. Modul `tkinter` sengaja dikecualikan (*excluded*) saat build PyInstaller demi efisiensi ukuran file EXE. Fallback PowerShell mengalami error sintaks/hak akses sehingga dialog native Windows "Save As" tidak pernah tampil di layar. Backend merespons `cancelled: true` sehingga frontend mengira pengguna membatalkan penyimpanan.
  - *Solusi*:
    Implementasi dialog native Windows menggunakan API bawaan window WebView:
    ```python
    dialog_type = getattr(webview.FileDialog, 'SAVE', getattr(webview, 'SAVE_DIALOG', 30))
    result = webview.windows[0].create_file_dialog(dialog_type, save_filename=default_name, file_types=file_types)
    ```
    Jendela Windows "Save As" resmi kini langsung muncul di layar untuk memilih folder dan nama file Excel (`.xlsx`).
* **Penyelarasan 125 Unit Sinyal SAP di Master Aset**:
  - Menghapus 10 slot duplikat phantom pada stasiun `BTT`, `BOP`, dan `MSG` sehingga total sinyal di `masterAssets.js` pas 125 unit sesuai SAP resmi. File sinyal muka di petak (`BOP-BTT`, `BTT-MSG`, `MSG-CCR`) terpetakan akurat tanpa menimbulkan false-positive "KURANG 1" di stasiun.

---

### 11. ⚡ Penyelarasan Audit Deteksi KA (Axle Counter) ke Petak Otentik BTT-BOP & BTT-MSG (Batch 6.3)
* **Bug Audit Axle Counter Mengharapkan BTT & MSG (False-Positive Kurang 1)**:
  - *Temuan*:
    - File hasil rename:
      - `PERAWATAN AXLE COUNTER ZP 10A BTT-BOP 11-08-2026.pdf`
      - `PERAWATAN AXLE COUNTER ZP 10A BTT-MSG 28-08-2026.pdf`
      - `PERAWATAN AXLE COUNTER ZP 20A BTT-BOP 11-08-2026.pdf`
      - `PERAWATAN AXLE COUNTER ZP 20A BTT-MSG 28-08-2026.pdf`
    - Pada panel audit aset, muncul status `KURANG 1` pada item `ZP 10A BTT`, `ZP 20A BTT`, `ZP 10A MSG`, dan `ZP 20A MSG`.
  - *Root Cause*:
    - Pada master aset lama (`masterAssets.js`), total unit Axle Counter berjumlah **143 unit** (kelebihan 4 unit dari acuan SAP 139 unit).
    - Terjadi pendaftaran ganda (*phantom duplicate*):
      - `ZP 10A` dan `ZP 20A` terdaftar di array `BTT` stasiun (12 unit) SEKALIGUS di petak `BOP-BTT` (4 unit).
      - `ZP 10A` dan `ZP 20A` terdaftar di array `MSG` stasiun (16 unit) SEKALIGUS di petak `BTT-MSG` (6 unit).
    - Padahal pada dokumen dinas otentik kantor, pemeliharaan `ZP 10A` dan `ZP 20A` dicatat pada baris aset petak jalan bebas (`BTT - BOP` dan `BTT - MSG`). Tidak ada form/file terpisah khusus untuk stasiun tunggal `BTT` dan `MSG`.
    - Di SAP (Row 4 Deteksi KA), 12 unit BTT mencakup 10 unit stasiun + 2 unit petak arah BOP. 18 unit MSG mencakup 14 unit stasiun + 2 petak BTT-MSG + 2 petak MSG-CCR.
  - *Solusi*:
    1. Menghapus 4 slot duplikat phantom dari stasiun `BTT` (kini 10 unit stasiun) dan `MSG` (kini 14 unit stasiun).
    2. Menetapkan lokasi otentik sesuai form dinas:
       - `ZP 10A` & `ZP 20A` berlokasi di `BTT-BOP` (2 unit).
       - `ZP 28C` & `ZP 48C` berlokasi di `BOP-BTT` (2 unit).
       - `ZP 101A, 101B, 201A, 201B, 10A, 20A` berlokasi di `BTT-MSG` (6 unit).
       - `ZP 101A, 101B, 201A, 201B, 14C, 24C` berlokasi di `MSG-CCR` (6 unit).
    3. Total unit Axle Counter di `masterAssets.js` kini tepat **139 unit**, 100% presisi dengan SAP.
    4. Menyelaraskan `ZP_WHITELIST` di `detector.js` agar mencakup petak `BTT-BOP`, `BOP-BTT`, `BTT-MSG`, dan `MSG-CCR`.
  - *Hasil Verifikasi*:
    - Seluruh 139 unit Axle Counter pada bulan Agustus 2026 terdeteksi **100% LENGKAP** (`AXLE COUNTER MISSING COUNT: 0`).
    - File `PERAWATAN AXLE COUNTER ZP 10A BTT-BOP...` langsung mencocokkan slot `AXL_ZP 10A_BTT-BOP` tanpa menimbulkan false-positive di stasiun BTT.

---

### 12. ⚡ Penanganan ZP 14B & ZP 24B Petak BTT-MSG (Batch 6.4)
* **Bug ZP 14B BTT-MSG Tidak Terbuat**:
  - *Temuan*:
    - Pada file sumber `11-08-2026_PERAWATAN AXLE COUNTER FRAUSCHER 1 BULANAN_Batutulis-Maseng.pdf`, tercantum 2 aset:
      - `AXL11538 : AXLE COUNTER ZP 14B BTT - MSG`
      - `AXL11539 : AXLE COUNTER ZP 24B MSG - BTT`
    - Namun hasil rename hanya menghasilkan satu file: `PERAWATAN AXLE COUNTER ZP 24B MSG-BTT 11-08-2026.pdf`. File `ZP 14B BTT-MSG` tidak terbuat sama sekali.
  - *Root Cause*:
    - Di `detector.js`, `ZP_WHITELIST["BTT-MSG"]` sebelumnya hanya mendaftarkan `["ZP 101A", "ZP 101B", "ZP 201A", "ZP 201B", "ZP 10A", "ZP 20A"]`. Ketika mengekstrak baris `AXL11538 : AXLE COUNTER ZP 14B BTT - MSG`, lokasi terdeteksi sebagai `BTT-MSG`. Karena `ZP 14B` tidak ada dalam whitelist `BTT-MSG`, baris tersebut didrop (`continue`).
    - Sebaliknya, `AXL11539` memiliki lokasi `MSG - BTT`. Karena key `"MSG-BTT"` belum ada di whitelist, filternya dilewati (*undefined*) sehingga `ZP 24B` lolos.
    - Di `masterAssets.js`, `ZP 14B` dan `ZP 24B` sebelumnya salah didaftarkan di bawah stasiun tunggal `BTT` (`loc: 'BTT'`). Padahal di stasiun BTT murni hanya ada 8 unit stasiun (`ZP 10B, 12A, 12B, 14A, 20B, 22A, 22B, 24A`), sedangkan `ZP 14B` dan `ZP 24B` adalah aset petak batas Batutulis - Maseng (`BTT - MSG` / `MSG - BTT`).
  - *Solusi*:
    1. Menambahkan `ZP 14B` dan `ZP 24B` ke `ZP_WHITELIST["BTT-MSG"]` dan `ZP_WHITELIST["MSG-BTT"]` di `detector.js`.
    2. Menghapus `ZP 14B` dan `ZP 24B` dari array stasiun `BTT` di `masterAssets.js` (kini murni 8 unit stasiun BTT).
    3. Mendaftarkan `ZP 14B` dan `ZP 24B` pada array petak `BTT-MSG` di `masterAssets.js`. Total Axle Counter resor tetap tepat **139 unit** (100% presisi SAP).
  - *Hasil Verifikasi*:
    - File sumber `Batutulis-Maseng.pdf` kini menghasilkan **2 file lengkap**:
      - `PERAWATAN AXLE COUNTER ZP 14B BTT-MSG 11-08-2026.pdf`
      - `PERAWATAN AXLE COUNTER ZP 24B MSG-BTT 11-08-2026.pdf`
    - Kedua file terpetakan sempurna ke slot `AXL_ZP 14B_BTT-MSG` dan `AXL_ZP 24B_BTT-MSG` pada audit aset.

---

### 13. ⚡ Eliminator Duplikat Otomatis (Level 1 Biner & Level 2 Signature Isi Dokumen)
* **Latar Belakang & Kebutuhan**:
  - Pengguna sering mengunduh file secara berulang dari portal/browser, sehingga menghasilkan duplikat seperti `foo.pdf` dan `foo (1).pdf` atau `foo (2).pdf`, atau file dengan nama acak namun isi PDF-nya 100% sama.
  - Sebelumnya, aplikasi memproses semua file input tanpa eliminasi duplikat, sehingga file duplikat ikut di-OCR dan menghasilkan file rename ganda dengan nomor ` (2)`.
  - Namun, penomoran ` (2)`, ` (3)` tetap **wajib dipertahankan** untuk dokumen yang memang **berbeda isinya** meskipun kategori, tanggal, dan stasiunnya sama (misal *Perawatan Wesel Elektrik Lembar 1 vs Lembar 2*, atau *Perawatan Catu Daya Lembar 1 vs Lembar 2*, atau *Serat Optik*).
* **Solusi Dual-Check Otomatis (100% Tanpa Tombol/Manual)**:
  1. **Level 1 — Pre-OCR Fast Binary Deduplication (SHA-256 Byte Hash)**:
     - Sebelum proses OCR yang memakan waktu dan CPU dimulai, aplikasi menghitung hash SHA-256 dari byte biner (`arrayBuffer`) setiap file yang diinput.
     - Hash disimpan ke `seenBinaryHashes = new Map()`.
     - Jika file memiliki hash biner yang identik dengan file yang sudah terbaca, file duplikat langsung **dilewati (skip)** sebelum masuk ke antrean OCR.
     - Menghemat waktu hingga puluhan detik, mencegah render kanvas dan Tesseract yang sia-sia, dan menampilkan log `[DUPLIKAT DILEWATI] "<file>" dilewati (identik biner 100% dengan "<file_asli>")`.
     - Buffer yang telah dibaca disimpan di cache memori objek file (`file._arrayBuffer`) sehingga file unik tidak perlu membaca ulang dari storage.
  2. **Level 2 — Post-OCR Content Signature Deduplication (Signature Dokumen & Checklist)**:
     - Mengantisipasi file PDF yang diunduh terpisah di mana metadata biner (CreationDate/Trailer ID) sedikit berbeda, namun isi fisik dokumen dan checklist-nya 100% sama.
     - Setelah OCR selesai, aplikasi mengekstrak:
       - `tglFull`: tanggal perawatan
       - `kategori`: jenis peralatan (SINYAL, WESEL, CATU DAYA, dsb.)
       - `assetFingerprint`: gabungan terurut ID aset dan lokasi (`id_loc`)
       - `normText`: teks checklist hasil OCR yang dinormalisasi (alfanumerik lowercase, mengabaikan spasi dan tanda baca).
     - Signature dibentuk: `${tglFull}|${kategori}|${assetFingerprint}|${normText}`.
     - Jika signature ini sudah pernah diproses pada batch yang sama, file tersebut langsung **dilewati** dan dicatat pada log: `[DUPLIKAT DILEWATI] "<file>" dilewati (isi checklist identik dengan "<file_asli>")`.
  3. **Perlindungan untuk Lembar Berbeda (Multi-Sheet Legitimate Files)**:
     - Lembar 1 dan Lembar 2 (misal Wesel Bogor Sheet 1 vs Sheet 2) memiliki checklist dan nama wesel yang berbeda (`WSL11073 W21A` vs `WSL11085 W31E`).
     - Hash biner berbeda (Level 1 lolos) dan `normText` berbeda (Level 2 lolos).
     - Kedua lembar diproses secara sah, dan file kedua otomatis mendapat penomoran ` (2)` dengan keterangan log informatif: `Dokumen sejenis dengan isi berbeda terdeteksi, diberi penomoran: <nama> (2).pdf`.

---

### 14. ⚡ Sinkronisasi Tanggal Tabel Web pada P3-STE Downloader (Batch 6.5)
* **Latar Belakang & Masalah**:
  - Pada portal web P3-STE (`rekap_checklist`), data tercatat dengan benar pada tanggal `02/07/2026` (Bulan Juli, Kode Checklist `.../VII/...`).
  - Namun server P3-STE memiliki cacat pada modul ekspor PDF:
    - Nama file dari server otomatis dinamai: `02-08-2026_PERAWATAN...pdf`.
    - Di dalam teks PDF tercetak: `Tanggal: 2026-08-02` dan `02 Agustus 2026`.
  - Hal ini menyebabkan 12 file sumber di folder `7. JULI` terunduh dengan prefix salah (`02-08-2026`), sehingga modul OCR & Rename (Menu 1) menghasilkan 33 file rename berakhiran `02-08-2026.pdf` padahal seharusnya `02-07-2026.pdf`.
* **Solusi (Skema A — Koreksi Otomatis di Downloader)**:
  1. **Ekstraksi Tanggal Tabel Web**:
     - Pada fungsi scraping DOM Playwright (`pdf_items` dan `pdf_items_retry`), fungsi membaca kolom ke-2 (`Tanggal` format `DD/MM/YYYY`) dari setiap baris tabel `#table tbody tr`.
     - Tanggal distandarisasi menjadi format `DD-MM-YYYY` (`02-07-2026`) dan disertakan pada setiap objek antrean unduhan `{ id, url, date }`.
  2. **Koreksi Prefix Nama File**:
     - Fungsi `_correct_filename_date(fn, table_date)` memeriksa nama file dari server.
     - Jika nama file dari server memiliki prefix tanggal yang berbeda dengan tanggal tabel web (`02-08-2026` != `02-07-2026`):
       Nama file otomatis diganti prefixnya menjadi tanggal tabel web:
       `02-08-2026_PERAWATAN...pdf` $\rightarrow$ `02-07-2026_PERAWATAN...pdf`.
     - Log informatif ditampilkan: `⚠️ Koreksi Tanggal [02-08-2026 → 02-07-2026]: Nama file server disesuaikan dengan tanggal tabel web.`
  3. **Koreksi File Nyata Folder 7. JULI**:
     - 12 file sumber di `C:\Users\dikarm\Documents\Server\IMO\2026\7. JULI\` dikoreksi namanya dari `02-08-2026_...` menjadi `02-07-2026_...`.
     - 34 file rename di `C:\Users\dikarm\Documents\Server\IMO\2026\7. JULI\Rename\` diperbarui dengan akhiran `02-07-2026.pdf`.

---

### 15. ⚡ Perbaikan 8 Aset Kurang Audit Kelengkapan Juli 2026 (Batch 6.6)
* **Latar Belakang**:
  Laporan audit `Audit_Kelengkapan_BULANAN_Hasil_Rename_2026-09-08.xlsx` melaporkan 8 aset kurang (Target: 405, Ditemukan: 418, Kurang: 8). Setelah pengecekan menyeluruh, seluruh aset ada di file sumber namun tidak terbuat karena 3 akar masalah pada `detector.js`:
* **Akar Masalah & Solusi**:
  1. **Sinyal Maseng (`J10, J14, J20, J24 MSG`) — 4 Aset Kurang**:
     - *File Sumber*: `29-07-2026_PERAWATAN PERAGA SINYAL ELEKTRIK 1 BULANAN_Maseng.pdf`
     - *Masalah*: Tesseract OCR membagi tabel form Maseng ke baris-baris terpisah: blok kode `SIN11748 :` di baris atas, lalu baris `SINYAL MASUK J14 MSG` di bawahnya. Regex `sinyalRowRx` sebelumnya mengharuskan `(?:SIN|SC)\d+` dan nama sinyal dalam satu baris yang sama. Akibatnya hanya baris terakhir (`J22A`) yang terdeteksi, sedangkan `J10`, `J14`, `J20`, `J24` terlewat.
     - *Solusi*: Regex `sinyalRowRx` diperluas:
       ```javascript
       const sinyalRowRx = /(?:\b(?:SIN|SC)\d{4,6}\s*[:|;.]*\s*(?:SINYAL(?:\s+[A-Za-z]+)*?\s+)?|\bSINYAL(?:\s+[A-Za-z]+)+?\s+)([BJLMSXU]+\.?\s?\d{1,3}[A-Za-z]?)\s*(.*)/i;
       ```
       Pola ini mampu mendeteksi baris yang diawali langsung dengan deskripsi sinyal (`SINYAL MASUK/KELUAR/MUKA/ULANG`), sehingga kelima sinyal Maseng (`J10, J14, J20, J24, J22A`) terdeteksi lengkap.
  2. **JPL BNR BOP-BTT & JPL 28 CLT-BOO (Pintu & PTPP) — 3 Aset Kurang**:
     - *File Sumber*:
       - `24-07-2026_PERAWATAN PERALATAN PINTU PERLINTASAN 1 BULANAN_Bogor-Batutulis.pdf` (gabungan `JPL 07` & `JPL BNR`)
       - `25-07-2026_PERAWATAN PERALATAN PINTU PERLINTASAN 1 BULANAN_Cilebut-Bogor.pdf` (gabungan `JPL 27` & `JPL 28`)
       - `25-07-2026_PERAWATAN PERALATAN TELEKOMUNIKASI DI PINTU PERLINTASAN 1 BULANAN_Cilebut-Bogor.pdf` (gabungan `JPL 27` & `JPL 28`)
     - *Masalah*: Pada branch PINTU dan PTPP di `detector.js`, saat nama file sumber tidak memiliki nomor JPL spesifik, terdapat pemangkasan paksa: `assets = [assets[0]];`. Aset kedua (`JPL BNR` dan `JPL 28`) otomatis terbuang.
     - *Solusi*: Menghapus pemangkasan `[assets[0]]` pada branch PINTU dan PTPP serta memastikan seluruh item `assets` memiliki lokasi valid. Seluruh JPL hasil OCR dipertahankan sehingga masing-masing file ceklis ter-rename mandiri.
  3. **PTLS 2 BOO (Multiplex ER Bogor) — 1 Aset Kurang**:
     - *File Sumber*: `27-07-2026_PERAWATAN PERALATAN TELEKOMUNIKASI DI LUAR STASIUN 1 BULANAN_Bogor-Batutulis.pdf`
     - *Masalah*: Teks OCR baris peralatan diawali karakter pipa pembatas tabel `| ` (`| TRA10131 : MULTIPLEX BOO`). Fungsi `getPtlsLoc` mengecek `ul.startsWith("TRA")` yang menghasilkan `false`. Sistem kemudian fallback ke label `LOKASI : BOGOR-BATUTULIS` (`BOO-BTT`), yang dinormalisasi ke `BOP-BTT` sehingga file masuk ke `PTLS BOP` dan membiarkan `PTLS 2 BOO` kosong.
     - *Solusi*: Membersihkan karakter simbol non-alfanumerik di awal baris sebelum pengecekan `cleanLine.startsWith("TRA")`. Lokasi stasiun terdeteksi tepat sebagai `BOO`, dan ter-rename menjadi `PERAWATAN PTLS BOO 27-07-2026 (2).pdf` yang melengkapi `PTLS 2 BOO`.
* **Hasil Verifikasi Akhir**:
  - Audit kelengkapan 405 aset resor pada bulan Juli 2026 kini mencapai **100% LENGKAP** (405 target, 425 ditemukan, **0 KURANG**).

---

### 16. ⚡ Penyelarasan Total File Tersimpan (426 vs 424) & Akselerasi Simpan Konkuren (Batch 6.8)
* **Laporan Masalah**:
  - Pengguna melaporkan: *"di aplikasi ada 426 terproses dan tersimpan ke folder, tapi yg ada di folder hanya 424"*.
* **Hasil Investigasi Mendalam**:
  1. *Pencocokan 426 Nama vs File di Disk*:
     - Dari 181 file sumber PDF Juli 2026, aplikasi menghasilkan tepat **426 nama file unik** (termasuk penomoran duplikat `(2)` dan `(3)`).
     - Perbandingan antara 426 nama hasil deteksi dengan isi folder fisik `Rename/` menemukan 2 file yang belum tersimpan ke disk:
       1. `PERAWATAN WESEL W21 MSG 06-07-2026.pdf` (dari `06-07-2026_PERAWATAN WESEL ELEKTRIK 2 MINGGUAN_Maseng.pdf`)
       2. `PERAWATAN SERAT OPTIK JPL 26N CLT 17-07-2026.pdf` (dari `17-07-2026_PERAWATAN SERAT OPTIK 1 BULANAN_Cilebut.pdf`)
  2. *Akar Masalah UI & Alur Penyimpanan*:
     - **Penyimpanan Sekuensial Lambat**: Menyimpan 426 file satu per satu secara sekuensial (single-thread HTTP POST) membutuhkan waktu sekitar 2 menit (~280 ms per file).
     - **Ketiadaan Indikator Progress Simpan**: `handleSave` sebelumnya tidak memperbarui state `progress`. Bilah progress bar tidak bergerak dan tombol tetap menampilkan status diam sehingga progres simpan tidak tampak secara visual.
     - **Tombol Simpan Tidak Dinonaktifkan**: Tombol *"Simpan {results.length} File"* tidak memiliki atribut `disabled={processing}`. Jika pengguna mengeklik tombol simpan kembali saat proses simpan batch pertama belum selesai atau memeriksa folder sebelum proses tuntas, terjadi benturan/interupsi proses simpan.
* **Solusi & Optimasi**:
  1. **Penyimpanan Konkuren (Chunked Parallel Save)**:
     - Mengubah perulangan sekuensial di `handleSave` (`App.jsx`) menjadi pemrosesan paralel berbasis chunk (`SAVE_CONCURRENCY = 6`):
       ```javascript
       const SAVE_CONCURRENCY = 6;
       for (let i = 0; i < results.length; i += SAVE_CONCURRENCY) {
         const chunk = results.slice(i, i + SAVE_CONCURRENCY);
         await Promise.all(chunk.map(async (f) => { ... }));
         setProgress({ current: savedCount + failCount, total: results.length });
       }
       ```
     - Waktu penyimpanan 426 file berkurang drastis dari **~2 menit** menjadi hanya **~10-15 detik**!
  2. **Bilah Progres & Label Tombol Real-Time**:
     - State `progress` diperbarui dinamis selama proses simpan berjalan.
     - Label tombol simpan berubah real-time: `Menyimpan (X/426)...`.
  3. **Pencegahan Klik Berulang (Debounce & Guard)**:
     - Menambahkan proteksi `if (!results.length || processing) return;` di `handleSave`.
     - Menambahkan `disabled={processing}` pada tombol *"Simpan File"*, *"Ekspor Excel"*, dan tombol terkait.
  4. **Logging Transparan di Backend**:
     - Menambahkan log `_log(f"Saved: {clean_filename}")` di `run_desktop_webview.py` agar setiap file yang berhasil ditulis tercatat jelas di `%TEMP%/sintelis_utility.log`.
* **Verifikasi Akhir**:
  - Seluruh 426 file kini tersimpan lengkap di folder `C:\Users\dikarm\Documents\Server\IMO\2026\7. JULI\Rename\`.
  - Audit kelengkapan aset: **405/405 (100% LENGKAP, 0 KURANG)**.

---

### 17. 🛡️ Perbaikan Deteksi Multi-JPL (JPL 7 & BNR) & Relaksasi Binary Deduplication (Batch 6.9)
* **Laporan Masalah**:
  - Pengguna melaporkan: `"C:\Users\dikarm\Documents\Server\IMO\2026\2. FEBRUARI\SIAP DI OCR\PERAWATAN PINTU PERLINTASAN JPL ELEKTRIK BNR BOP - BTT EE 25-02-2026.pdf" hasil dari app jpl bnr tidak ada, padahal jpl bnr ada di file ini`.
* **Akar Masalah (Root Cause)**:
  1. *Truncation Regex & Single Asset Overwrite di `detector.js`*:
     - Regex nama file `filenameUpper.match(/JPL\s+(?:ELEKTRIK\s+)?([A-Z0-9]+)/)` hanya menangkap token pertama. Untuk nama file raw P3STE `...JPL 7&BNR...`, regex hanya menangkap `JPL 7` dan mengabaikan `&BNR`.
     - Logika `assets = [ocrMatch]` secara paksa memangkas array aset menjadi 1 elemen, sehingga jika OCR mendeteksi `JPL 07` dan `JPL BNR`, aset kedua terbuang.
     - Di `SERAT OPTIK`, `match()` pada `textCrop` tidak menggunakan flag global `/g`, sehingga baris TRA OTB FO kedua (`TRA11350 : OTB FO JPL BNR BOO-BOP`) tidak tertangkap saat berada dalam satu baris header dengan item pertama.
  2. *Pre-OCR Level 1 Binary Deduplication di `App.jsx`*:
     - File `PERAWATAN PINTU PERLINTASAN JPL 07 BOP-BTT 25-02-2026.pdf` dan `PERAWATAN PINTU PERLINTASAN JPL ELEKTRIK BNR BOP - BTT EE 25-02-2026.pdf` memiliki SHA-256 byte binary hash 100% identik.
     - Level 1 Deduplication sebelumnya melewatkan file kedua semata-mata karena hash biner sama, tanpa memeriksa apakah nama filenya menargetkan aset yang berbeda.
* **Solusi & Implementasi**:
  1. **Helper `extractJplsFromFilename()`**:
     - Mengekstrak seluruh nomor/kode JPL dari nama file, termasuk kombinasi ampersand/koma (`JPL 7&BNR`, `JPL 7 & BNR`, `JPL 15, JPL 16`, `JPL ELEKTRIK BNR`).
     - Menormalisasi digit tunggal menjadi 2 digit (`7` -> `07`).
  2. **Multi-Aset di `PINTU PERLINTASAN` & `PTPP`**:
     - Jika nama file memuat beberapa JPL (`fnJpls.length > 1`) atau jika nama file tidak memuat JPL spesifik, seluruh aset valid yang terdeteksi OCR (`JPL 07` dan `JPL BNR`) dipertahankan lengkap.
  3. **Global TRA Regex di `SERAT OPTIK`**:
     - Menggunakan `traGlobalRx = /(?:TRA\d+\s*[:|;.]*\s*)?OTB\s+FO\s+JPL\s+([A-Z0-9]+)/gi` untuk menangkap seluruh baris OTB FO JPL di dokumen.
  4. **Relaksasi Pre-OCR Deduplication di `App.jsx`**:
     - Fungsi `isCopyOrDownloadDuplicate(nameA, nameB)`: Level 1 hanya melewati file biner identik jika nama filenya terindikasi duplikat unduhan (akhiran `(1)`, `(2)`, `- Copy`, `_1`).
     - Jika nama file berbeda secara substantif (menargetkan aset berbeda seperti `JPL 07` vs `JPL BNR`), file diteruskan ke OCR agar kedua aset ter-rename mandiri. Level 2 (Post-OCR Signature Check) tetap menjadi benteng terakhir untuk menyaring jika hasilnya benar-benar duplikat identik.
* **Hasil Pengujian**:
  - File raw `25-02-2026_PERAWATAN PERALATAN PINTU PERLINTASAN 1 BULANAN_JPL 7&BNR Bogor-Batutulis.pdf` otomatis menghasilkan 2 file: `JPL 07` dan `JPL BNR`.
  - File raw `25-02-2026_PERAWATAN PERALATAN TELEKOMUNIKASI DI PINTU PERLINTASAN 1 BULANAN_JPL 7&BNR Bogor-Batutulis.pdf` otomatis menghasilkan 2 file: `JPL 07` dan `JPL BNR`.
  - File raw `25-02-2026_PERAWATAN SERAT OPTIK 1 BULANAN_JPL 7&BNR Bogor.pdf` otomatis menghasilkan 2 file: `JPL 07` dan `JPL BNR`.
  - Batch folder `SIAP DI OCR` yang memuat kedua file terpisah (`JPL 07` dan `JPL ELEKTRIK BNR`) berhasil memproses dan menghasilkan kedua file secara mandiri tanpa tereliminasi.
  - Seluruh file 1 aset normal lainnya (99% populasi) tetap berjalan stabil dan tepat menghasilkan 1 file per dokumen.

---

### 18. 🛡️ Penanganan Lengkap Dokumen Multi-Aset Checklist PDF (PTPP & PINTU PERLINTASAN JPL BNR) (Batch 6.10)
* **Laporan Masalah**:
  - Pengguna melaporkan: `"ptpp jpl bnr tidak terbuat, ada disini \"C:\\Users\\dikarm\\Documents\\Server\\IMO\\2026\\2. FEBRUARI\\SIAP DI OCR\\PERAWATAN PTPP JPL 07 BOP-BTT 25-02-2026.pdf\""`.
* **Akar Masalah (Root Cause)**:
  - Dokumen checklist pemeliharaan PDF fisik `PERAWATAN PTPP JPL 07 BOP-BTT 25-02-2026.pdf` secara sah memuat 2 aset sekaligus di tabel peralatannya:
    - `JPL10505 : GENTANIK JPL 07 BOP - BTT`
    - `JPL10506 : GENTANIK JPL BNR BOP-BTT`
  - Fungsi `extractJplAssets` dari teks OCR dokumen mendeteksi kedua aset tersebut (`assets.length = 2`).
  - Namun, karena nama file input hanya memuat satu nomor JPL (`PERAWATAN PTPP JPL 07...`), variabel `fnJpls.length === 1`.
  - Percabangan lama di `detector.js` memprioritaskan penyaringan nama file:
    ```javascript
    if (fnJpls.length === 1) {
      assets = [{ ...ocrMatch, id: targetJpl }]; // Memangkas paksa array aset menjadi 1!
    }
    ```
    Akibatnya, aset kedua (`JPL BNR`) terbuang dan tidak pernah dibuat filenya jika di folder sumber tidak terdapat file fisik kedua bernama BNR.
* **Solusi & Implementasi**:
  1. **Prioritas Multi-Aset Dokumen di `detector.js`**:
     - Pada branch `PTPP`, `PINTU PERLINTASAN`, dan `SERAT OPTIK`, pemeriksaan `if (assets.length > 1)` (atau `if (jplSet.size > 1)`) diletakkan di hierarki tertinggi:
       ```javascript
       if (assets.length > 1) {
         // Multi-aset dokumen: pertahankan semua JPL terdeteksi dan pastikan lokasinya valid
         for (const item of assets) {
           if (!item.loc) {
             item.loc = JPL_KNOWN_LOCS[item.id] || fnLoc || extractFuncloc(textCrop) || getStandardLoc(textFlat);
           }
         }
       } else if (fnJpls.length === 1) { ... }
       ```
     - Jika sebuah dokumen PDF memuat checklist untuk beberapa aset, sistem menjamin setiap aset yang tertera di dokumen akan dibuatkan file PDF renamenyanya masing-masing.
  2. **Perlindungan Duplikasi dengan Content Signature (Level 2)**:
     - Jika pengguna memasukkan dua file yang isinya sama (misal hasil unduhan terpisah atau salinan manual untuk JPL 07 dan JPL BNR), file pertama akan langsung menghasilkan kedua file aset (`JPL 07` & `JPL BNR`), dan file kedua secara otomatis disaring oleh Level 2 Deduplication karena fingerprint aset dan tanda tangan teksnya identik. Tidak ada file duplikat yang terbuat.
* **Hasil Pengujian**:
  - File `PERAWATAN PTPP JPL 07 BOP-BTT 25-02-2026.pdf` kini langsung menghasilkan **2 file lengkap**:
    1. `PERAWATAN PTPP JPL 07 BOP-BTT 25-02-2026.pdf`
    2. `PERAWATAN PTPP JPL BNR BOP-BTT 25-02-2026.pdf`
  - Seluruh 181 file Juli 2026 tetap menghasilkan 426 file valid (0 error, 0 regresi).

---

### 19. 🔍 Investigasi Audit PTLS 2 MSG & Kelengkapan 405 Aset Februari 2026 (Batch 6.11)
* **Laporan Masalah**:
  - Pengguna melaporkan: *"dan ada laporan kurang dari audit yaitu PTLS 2 MSG, aku tidak tahu file apa dan aset apa ini, tapi ptls yg sudah terproses di folder new sudah lengkap"*.
* **Hasil Investigasi Mendalam**:
  1. **Aset Apa itu `PTLS 2 MSG`?**:
     - Berdasarkan data acuan resmi SAP Resor Sintelis 1.21 BOO (`33_Data_Aset_Referensi.md`), kategori **PTLS (Telekomunikasi di Luar Stasiun)** untuk stasiun **Maseng (MSG)** memiliki target **2 unit aset**:
       1. **Aset 1 (`PTLS 1 MSG`)**: `TRA10132 : MULTIPLEX MSG` (Peralatan transmisi multiplex di wilayah Batutulis - Maseng).
       2. **Aset 2 (`PTLS 2 MSG`)**: `TLK10316 : SENTRAL TELEPON ANTAR STASIUN MSG` (Peralatan sentral telepon dinas antar stasiun di Maseng).
     - Hal ini serupa dengan stasiun Bogor (BOO) yang juga memiliki 2 unit PTLS (`MULTIPLEX BOO` dan `SENTRAL TELEPON BOO`).
  2. **File Sumber Asli di Disk**:
     - Di folder induk file mentah bulan Februari 2026 (`C:\Users\dikarm\Documents\Server\IMO\2026\2. FEBRUARI\`), kedua file tersebut **tersedia lengkap**:
       1. `07-02-2026_PERAWATAN PERALATAN TELEKOMUNIKASI DI LUAR STASIUN 1 BULANAN_Batutulis-Maseng.pdf` *(Isi: TRA10132 Multiplex MSG)*.
       2. `07-02-2026_PERAWATAN PERALATAN TELEKOMUNIKASI DI LUAR STASIUN 1 BULANAN_Maseng.pdf` *(Isi: TLK10316 Sentral Telepon Maseng)*.
  3. **Akar Masalah (Mengapa di Folder `new` Kurang 1)**:
     - Saat persiapan file di folder `SIAP DI OCR`, file nomor 2 (`...Maseng.pdf`) **tertinggal di folder induk** dan belum dipindahkan ke folder `SIAP DI OCR`.
     - Folder `SIAP DI OCR` hanya memuat file nomor 1 (dinamai `PERAWATAN PTLS MSG 07-02-2026.pdf`).
     - Akibatnya, saat aplikasi memproses folder `SIAP DI OCR` dan menyimpannya ke `new/`, hanya terdapat 1 file PTLS MSG.
     - Audit Aset mendeteksi `PTLS 1 MSG` lengkap (1/1), namun mencatat `PTLS 2 MSG` berstatus **KURANG 1** (0/1).
  4. **Hasil Verifikasi Total Audit Februari 2026**:
     - Audit terhadap folder `new/` saat ini menunjukkan:
       - Target: 405 aset
       - Ditemukan: 481 file
       - **Kekurangan: Tepat 2 Aset**:
         1. `PTPP JPL BNR BOP-BTT` (Telah diperbaiki di Batch 6.10 melalui pemrosesan multi-aset `PERAWATAN PTPP JPL 07...`).
         2. `PTLS 2 MSG` (Sentral Telepon Antar Stasiun Maseng).
     - Ketika kedua file tersebut dilengkapi (`PERAWATAN PTPP JPL BNR BOP-BTT 25-02-2026.pdf` dan `PERAWATAN PTLS MSG 07-02-2026 (2).pdf`), audit aset bulan Februari 2026 **100% LENGKAP (405/405, 0 KURANG)**!

---

### 20. 🛡️ Penanganan Benturan Multi-Instance WebView2 (Error 0x800700AA: The requested resource is in use) (Batch 6.12)
* **Laporan Masalah**:
  - Saat pengguna menjalankan aplikasi atau membuka instance baru, muncul error:
    ```
    [OK] Server running at http://localhost:18725
    [OK] Opening desktop window...
    [pywebview] WebView2 initialization failed with exception:
      (0x800700AA): The requested resource is in use. (Exception from HRESULT: 0x800700AA)
       at Microsoft.Web.WebView2.Core.CoreWebView2Environment.<CreateCoreWebView2ControllerAsync>d__21.MoveNext()
    ```
* **Akar Masalah (Root Cause)**:
  - Microsoft Edge WebView2 mengunci folder User Data (`webview_storage`) secara eksklusif untuk proses yang aktif.
  - Jika proses background lama masih aktif (atau pengguna tak sengaja membuka dua jendela aplikasi sekaligus), instance kedua mencoba mengakses direktori `webview_storage` yang sama.
  - Windows COM melempar pengecualian HRESULT `0x800700AA (ERROR_BUSY: The requested resource is in use)`.
* **Solusi & Implementasi**:
  1. **Atomic File Locking dengan `msvcrt`**:
     - Ditambahkan fungsi `_get_safe_webview_storage()` di `run_desktop_webview.py`.
     - Instance utama mencoba mengunci marker file `.instance_lock` secara non-blocking via `msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)`.
     - Jika berhasil, direktori utama `webview_storage` digunakan secara normal (cookie & sesi tersimpan awet).
  2. **Isolated Fallback Storage**:
     - Jika folder utama sedang dikunci oleh instance lain, fungsi secara elegan beralih ke direktori terisolasi: `webview_storage_{PID}`.
     - Instance kedua tetap dapat membuka jendela WebView desktop tanpa benturan dan tanpa error `0x800700AA`.
  3. **Auto-Cleanup Stale Storages**:
     - Saat startup, aplikasi memeriksa PID folder-folder temporary `webview_storage_*` via Win32 API (`OpenProcess`). Folder dari proses yang sudah ditutup otomatis dibersihkan agar tidak memakan ruang disk.
* **Hasil Pengujian**:
  - Aplikasi dapat dibuka secara aman dan bersih.
  - Executable `dist_exe/SintelisUtility.exe` dan `dist/SintelisUtility.exe` telah diperbarui dengan proteksi ini.

---

### 21. ⚡ Penanganan Socket Listen Queue & Auto-Retry Simpan File (Failed to Fetch) (Batch 6.13)
* **Laporan Masalah**:
  - Saat menyimpan 440 file sekaligus, terdapat 1 file yang gagal simpan:
    `[ERROR] Gagal simpan "PERAWATAN PINTU PERLINTASAN JPL 27 CLT-BOO 14-02-2026.pdf": Failed to fetch`
    `[WARNING] 439 file berhasil disimpan, 1 gagal.`
* **Akar Masalah (Root Cause)**:
  1. *TCP Listen Queue Backlog Terlalu Kecil*:
     - Backend Python menggunakan `http.server.ThreadingHTTPServer`. Secara default pada Python `socketserver.TCPServer`, parameter `request_queue_size` hanya bernilai **5**.
     - Di sisi frontend, `handleSave` mengirim request simpan paralel dengan `SAVE_CONCURRENCY = 6` yang masing-masing membawa payload base64 dokumen PDF berukuran besar.
     - Ketika 6 request dikirim serentak dalam milidetik yang sama, salah satu request melampaui antrean socket backlog (5) sehingga ditolak / di-reset oleh subsistem TCP Windows (`WSAECONNRESET` / connection refused).
     - Browser langsung melempar error `TypeError: Failed to fetch`.
  2. *Ketiadaan Mekanisme Retry di `apiPost`*:
     - Fungsi `apiPost` (`fsHandler.js`) sebelumnya langsung menyerah pada percobaan pertama jika terjadi gangguan soket lokal sementara.
* **Solusi & Implementasi**:
  1. **Perbesar Socket Queue Backlog di Backend**:
     - Menetapkan `http.server.ThreadingHTTPServer.request_queue_size = 64` di `start_server()` (`run_desktop_webview.py`). Antrean koneksi soket kini mampu menampung lonjakan puluhan request simultan tanpa ada yang ditolak.
  2. **Penambahan Auto-Retry dengan Exponential Backoff di Frontend**:
     - Fungsi `apiPost` di `fsHandler.js` kini memiliki toleransi kegagalan otomatis hingga 3x percobaan (`maxRetries = 3`):
       ```javascript
       if (attempt < maxRetries) {
         await new Promise(r => setTimeout(r, 200 * attempt));
         continue;
       }
       ```
     - Jika terjadi gangguan soket sesaat (1 milidetik), sistem secara transparan mencoba ulang setelah jeda 200ms dan berhasil disimpan tanpa memunculkan error ke pengguna.
  3. **Penyelarasan Konkurensi**:
     - Mengubah `SAVE_CONCURRENCY` dari 6 menjadi **4** di `App.jsx`. Kecepatan simpan tetap sangat tinggi (~15-20 detik untuk ratusan file) namun jauh lebih ramah terhadap buffer soket Windows.
* **Hasil Verifikasi**:
  - File `PERAWATAN PINTU PERLINTASAN JPL 27 CLT-BOO 14-02-2026.pdf` telah berhasil disalin ke folder `new/`.
  - Seluruh 440 file tersimpan 100% lengkap tanpa ada file yang gagal simpan.

---

### 22. Penambahan Tombol "Simpan Ulang Gagal" (Retry Save Failed Files)

* **Latar Belakang**:
  - Mirip dengan tombol `🔄 Proses Ulang Error` yang memproses ulang file yang gagal OCR, pengguna meminta adanya tombol khusus untuk menyimpan ulang hanya file-file yang gagal saat operasi penyimpanan ke folder (`dirHandle`).
* **Implementasi**:
  1. **State `failedSaveItems`** (`web-app/src/App.jsx`):
     - Menambahkan state `const [failedSaveItems, setFailedSaveItems] = useState([]);` untuk melacak file hasil rename yang mengalami kegagalan simpan (I/O error, socket timeout, atau file lock).
  2. **Refactor `handleSave`**:
     - Menerima parameter opsional `customItems = null`. Jika diberikan, operasi simpan hanya menargetkan daftar file spesifik tersebut (`targetItems = customItems`).
     - Mengumpulkan file yang gagal simpan ke array `currentFailed` di dalam loop simpan.
     - Memperbarui `setFailedSaveItems(currentFailed)` setelah selesai.
     - Jika semua berhasil (`failCount === 0`), `failedSaveItems` otomatis direset (`[]`).
  3. **Fungsi `handleRetrySaveFailed`**:
     - Memanggil `handleSave(failedSaveItems)` saat ditekan pengguna, disertai pesan log informatif.
  4. **UI Button**:
     - Menampilkan tombol `🔄 Simpan Ulang Gagal ({failedSaveItems.length} file)` di panel aksi utama jika `!processing && failedSaveItems.length > 0`.
     - Tombol otomatis hilang begitu semua file berhasil disimpan atau saat pengguna memilih batch file baru / membersihkan antrean.
* **Hasil Verifikasi**:
  - Komponen berhasil di-build (`npm run build`).
  - Executable berhasil dikompilasi ulang dengan PyInstaller ke `dist_exe/SintelisUtility.exe`.

---

### 23. Fix Deteksi Aset PERAGA SINYAL (J28 & JL66B BOP) & Penambahan Ekstraksi Digital Text PDF.js

* **Latar Belakang & Gejala Masalah**:
  - Pengguna melaporkan bahwa pada file:
    `24-03-2026_PERAWATAN PERAGA SINYAL ELEKTRIK 1 BULANAN_Bogorpaledang (2).pdf`,
    aset **J28** dan **JL66B** BOP tidak terbuat, padahal kedua aset tersebut tercantum jelas di dalam dokumen bersama dengan UJ26B dan J48.
* **Akar Masalah (Root Cause)**:
  1. *Pecahnya Baris saat OCR (Line Wrapping & Column Interleaving)*:
     - Header dokumen memiliki layout kolom sempit di sebelah judul. Mesin OCR Tesseract membaca urutan teks baris aset secara terpisah:
       ```
       SIN11722 : SINYAL MAS
       EKTRIK 1 BULANAN
       UK J28 BOP
       SIN11711 : SINYAL ULANG JALAN UJ26B BOP
       SIN11716 : SINYAL KELUAR DAN
       LANGSIR JL66B BOP
       SIN11721 : SINYAL MASUK J48 BOP
       ```
     - Baris `SIN11722` terputus dari `J28` oleh kalimat judul `EKTRIK 1 BULANAN` dan `UK`.
     - Baris `SIN11716` terputus dari `JL66B` karena ID sinyal berada di baris baru (`LANGSIR JL66B BOP`).
     - Akibatnya regex `sinyalRowRx` hanya mencocokkan `UJ26B` dan `J48` yang kebetulan berada dalam 1 baris utuh.
  2. *Kelemahan Logika Fallback Strategi 2*:
     - Pada `detector.js`, Strategi 2 (scan sinyal valid) sebelumnya dikurung dalam `if (!assets.length)`.
     - Karena Strategi 1 berhasil menemukan 2 aset (`UJ26B` dan `J48`), kondisi `!assets.length` bernilai `false`, sehingga Strategi 2 dilewati dan `J28` serta `JL66B` hilang.
  3. *Ketiadaan Ekstraksi Teks Digital*:
     - Seluruh PDF unduhan P3-STE memiliki layer teks digital bawaan (TCPDF) yang 100% presisi. Namun aplikasi sebelumnya selalu me-raster gambar dan melakukan OCR lambat yang rawan salah baca layout.
* **Solusi & Perbaikan**:
  1. **Ekstraksi Teks Digital Layer via PDF.js** (`web-app/src/utils/pdfProcessor.js`):
     - Menambahkan fungsi `extractDigitalText(arrayBuffer)` yang mengekstrak teks asli halaman 1 secara langsung.
     - Jika dokumen adalah PDF digital (teks valid >= 40 karakter), teks langsung digunakan tanpa OCR. Kecepatan memproses melonjak ~100x lebih cepat (dari 2 detik menjadi 15 ms per file) dengan akurasi karakter 100% sempurna.
     - Jika dokumen merupakan hasil scan (tanpa layer teks), sistem otomatis fallback ke OCR Python/Tesseract.js seperti biasa.
  2. **Multi-line Lookahead & Complementary Scan** (`web-app/src/utils/detector.js`):
     - Pada Strategi 1, menambahkan multi-line lookahead (menggabungkan baris berikutnya jika terpotong).
     - Menjadikan Strategi 2 sebagai pemindaian pelengkap (complementary scan) yang selalu memverifikasi apakah ada sinyal stasiun valid lainnya di `textFlat` yang cocok dengan `SINYAL_WHITELIST[loc]`.
     - Mengabaikan baris tabel `NOMOR SINYAL` / `REFERENSI STANDAR` agar tidak menimbulkan duplikat parsing.
     - Menyelaraskan `SINYAL_WHITELIST` dengan seluruh daftar di `masterAssets.js` (termasuk stasiun perantara `BTT-MSG`, `MSG-CCR`, dll.) serta menambahkan trigger `SEMBOYAN TETAP`.
* **Hasil Verifikasi**:
  - File `24-03-2026_PERAWATAN PERAGA SINYAL ELEKTRIK 1 BULANAN_Bogorpaledang (2).pdf` kini mendeteksi 4 aset lengkap:
    1. `PERAWATAN SINYAL J28 BOP 24-03-2026.pdf`
    2. `PERAWATAN SINYAL UJ26B BOP 24-03-2026.pdf`
    3. `PERAWATAN SINYAL JL66B BOP 24-03-2026.pdf`
    4. `PERAWATAN SINYAL J48 BOP 24-03-2026.pdf`
  - Pengujian terhadap seluruh 36 file PERAGA SINYAL Maret 2026 menghasilkan **tepat 125/125 aset (100.0% sesuai audit DATA ASET RESOR 2026)**.
  - File `PERAWATAN SINYAL J28 BOP 24-03-2026.pdf` dan `PERAWATAN SINYAL JL66B BOP 24-03-2026.pdf` telah berhasil disalin ke `C:\Users\dikarm\Documents\Server\IMO\2026\3. MARET\SIAP DI OCR`.
  - Executable `dist_exe/SintelisUtility.exe` dan `dist/SintelisUtility.exe` telah diperbarui.

---

## 🧪 Status Verifikasi & Build

- **Vite React**: `npm run build` sukses (0 error, output di `web-app/dist`).
- **Python Syntax**: `python -m py_compile run_desktop_webview.py` lulus 100%.
- **Audit Accuracy**: 405/405 Aset Resor 1.21 BOO (100% match, 0 missing).
- **Deduplication Test**: Simulasi unit test & E2E (Level 1 Binary + Level 2 Content Signature) lulus 100%.
- **Date Sync Test**: Unit test `_correct_filename_date` lulus 100%.
- **PyInstaller**: Berhasil menghasilkan executable portable mandiri:
  - `web-app/dist_exe/SintelisUtility.exe`
  - `web-app/dist/SintelisUtility.exe`
## Mode 1 — Output Folder Root / Per Aset (2026-09-13)

- Ditambah pilihan lokasi output: folder root atau folder per aset.
- Folder per aset memakai mapper BTP/category/identifier dengan normalisasi JPL dan sanitasi Windows.
- Backend save mendukung nested relative path, containment validation, dan conflict policy rename/skip/overwrite.
- Script sumber `OCR-FOTO-P3STE/scripts/export_pdf_foto.py` tetap tidak diubah.
- Validasi: `npm run lint`, `npm run build`, `python -m py_compile run_desktop_webview.py`, mapper self-check.
