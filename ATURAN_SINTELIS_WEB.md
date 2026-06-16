# PANDUAN PENGEMBANGAN SINTELIS WEB APP & OCR RENAMER

Dokumen ini berisi aturan baku, konvensi, dan logika inti (Business Logic) dari aplikasi **Sintelis 1.21 BOO Utility**. Gunakan dokumen ini sebagai panduan utama setiap kali melakukan perbaikan (bugfix) atau penambahan fitur baru pada aplikasi web Flask / backend OCR.

## 1. Arsitektur Infrastruktur Saat Ini
* **Aplikasi Utama (Web App):** Menggunakan **Flask** murni (Python) + HTML/CSS Tailwind, ditaruh di dalam Docker container. (Peralihan dari Streamlit untuk menghindari pemblokiran WebSocket oleh FortiGuard).
* **Backend OCR:** Tesseract OCR Linux (`tesseract-ocr`, `tesseract-ocr-ind`) dan Poppler-utils (`pdf2image`). Tesseract harus dikonfigurasi untuk membaca bahasa Indonesia & Inggris (`lang='ind+eng'`).
* **Deploy Target:** Docker Image dikirim ke Google Artifact Registry -> Di-deploy ke **Google Cloud Run** -> Diakses melalui **Firebase Hosting Rewrites** (`app-sintelboo.web.app`) untuk membypass filter *Unrated Domain* kantor.

## 2. Aturan Penamaan File Output (Renaming Rules)
Aplikasi membedakan penamaan PDF berdasarkan wilayah atau instansi.

### A. BTP JAK (Format Default)
Format ini digunakan untuk stasiun wilayah BTP Jakarta (misal: BOO, CLT).
**Format Wajib:** `(JENIS KEGIATAN) (NAMA/KATEGORI ASET) (KODE/NOMOR ASET) (LOKASI STASIUN) (DD-MM-YYYY).pdf`
* ❌ **TIDAK BOLEH** ada prefix periode bulan/tahun (seperti `2026-6_`).
* ❌ **TIDAK BOLEH** ada kode ceklis (seperti `BPBYE1`).
* *Contoh yang Benar:* `PERAWATAN WESEL W23B BOO 01-06-2026.pdf`

### B. BTP BD (Format Khusus)
Format ini digunakan untuk stasiun wilayah BTP Bandung (misal: BOP, BTT, COS, MSG, CGB).
**Format Wajib:** `(Tahun-Bulan)_(Resor)_(Kode Ceklis)_(Jenis Kegiatan)_(Identitas Aset)_(DD-MM-YYYY).pdf`
* ✅ **WAJIB** ada prefix periode (misal `2026-6_`).
* ✅ **WAJIB** ada nama resor `Resor 1.21 Boo`.
* ✅ **WAJIB** ada kode ceklis.
* *Contoh yang Benar:* `2026-6_Resor 1.21 Boo_BPBYE1_Perawatan_WESEL W11 MSG_01-06-2026.pdf`

## 3. Logika Deteksi Aset (Gerbang A - OCR)
Pendeteksian dilakukan dengan mengambil 30% area atas PDF halaman pertama (`img.crop((0.0, 0.0, width, height * 0.30))`), lalu di-OCR untuk mendapatkan `text_flat` (teks tanpa newline).

### A. Penanganan Multi-Aset (Split) [Opsi B]
Jika satu dokumen fisik PDF terdeteksi memiliki banyak ID Aset (Contoh: Terdapat Wesel `W11`, `W21`, `W23`, `W13` sekaligus dalam satu lembar PDF), maka program **WAJIB** memisahkan atau menduplikasi file tersebut ke dalam ZIP menjadi banyak file terpisah (1 output file PDF per ID Aset yang terdeteksi).
* *Contoh Output Multi-Aset dalam ZIP:* 
  1. `..._WESEL W11 MSG...pdf`
  2. `..._WESEL W21 MSG...pdf`
  3. `..._WESEL W23 MSG...pdf`

### B. Daftar Keyword dan Kode Ceklis
1. **WESEL (BPBYE1)**
   * *Regex:* `r'(W\d+[A-Z]*)'` atau dari kata kunci `PENGGERAK WESEL` / `POINT LOCK` / `PENGAMAN WESEL`.
2. **PDSE (BPBYE2)** -> Peralatan Dalam Persinyalan Elektrik.
3. **SERAT OPTIK (BPBKF4)** -> Cek kata kunci `SERAT OPTIK` + `JPL` + `FO` / `OTB`. *Wajib filter noise kata.*
4. **PTPP (BPBKS17)** -> Telekomunikasi Di Pintu Perlintasan (JPL Number).
5. **PINTU PERLINTASAN (BPBKS17)** -> Cek `PINTU PERLINTASAN` (tanpa kata Telekomunikasi).
6. **PTDS (BPBKS15)** -> Telekomunikasi Di Stasiun.
7. **PTLS (BPBKS16)** -> Telekomunikasi Di Luar Stasiun.
8. **CATU DAYA (BPBYE14)** -> Catu Daya.

### C. Pemetaan Lokasi Singkatan
Setiap teks OCR yang mengandung nama daerah stasiun atau singkatannya **WAJIB** dipetakan ke kode 3 huruf resmi:
* CILEBUT -> `CLT`
* BOGOR -> `BOO`
* CIOMAS / COS -> `COS`
* MASENG / MSG -> `MSG`
* CIGOMBONG / CGB -> `CGB`
* BOGORPALEDANG / PALEDANG -> `BOP`
* BATUTULIS / BTT -> `BTT`
* Jika tidak terdeteksi sama sekali -> `"LOKASI"`

## 4. Standar Penanganan Error & Duplikasi
* **Duplikat Aset:** Jika 1 file input menghasilkan multiple aset output yang sah (e.g. W11, W21), *jangan lempar error duplikat*.
* **Duplikat File Fisik:** Jika nama file keluaran (new_name) sudah pernah tertulis ke dalam zip dari file input lain, tolak file tersebut, jangan dimasukkan ke zip, dan munculkan pesan `"⚠️ Duplikat"` di UI.
* **Tanggal:** Jika regex ekstrak tanggal `(\d{2})-(\d{2})-(\d{4})` gagal di nama file input, tolak file tersebut (Tampilkan `"❌ Format tanggal tidak ditemukan"`).
