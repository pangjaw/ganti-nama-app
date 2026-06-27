# Project Guide and Handover

Tanggal update: 28/06/2026

## Tujuan repo

Repo ini sekarang punya 3 fungsi utama:

1. `app.py`
   - web app Flask untuk OCR dan rename PDF checklist
   - target deploy: Docker -> Google Cloud Run -> Firebase Hosting rewrite

2. `download_p3ste_rekap.py`
   - otomasi download PDF dari `https://p3-ste.kai.id/rekap_checklist`
   - target: intranet kantor P3-STE

3. `desktop_app.py`
   - wrapper desktop Tkinter
   - gabungkan flow downloader P3-STE + proses OCR `app.py`

## Aturan kerja update ke depan

Aturan kerja yang dipakai di project ini:

1. Jangan ubah script utama tanpa persetujuan user.
   - script utama:
     - `app.py`
     - `download_p3ste_rekap.py`
     - `desktop_app.py`

2. Sebelum ubah logic penting:
   - jelaskan bug/perubahan singkat
   - tunggu user setuju

3. Diff harus kecil dan fokus.
   - hindari refactor besar kalau tidak perlu

4. Jangan ubah OCR utama sembarang.
   - flow OCR inti:
     - `pdf2image.convert_from_bytes(..., dpi=150, first_page=1, last_page=1)`
     - crop 30 persen area atas
     - `pytesseract.image_to_string(..., lang='ind+eng').upper()`

5. Mapping lokasi lama jangan dihapus.
   - kalau cocok mapping lama, pakai itu dulu
   - baru fallback ke parsing lokasi generik

6. Jangan sentuh logic aset lain tanpa alasan jelas.
   - terutama sinyal, AXC, wesel, PTPP, pintu perlintasan

7. Setelah perubahan:
   - cek syntax
   - tes seminimal mungkin yang relevan
   - baru deploy kalau memang perlu

## Arsitektur deploy `app.py`

Jalur deploy aktif:

- `app.py` jalan sebagai Flask app
- dibungkus `Dockerfile`
- image dikirim ke Google Artifact Registry
- deploy ke Google Cloud Run
- Firebase Hosting pakai rewrite ke service Cloud Run

File yang terkait deploy dan perlu dipertahankan:

- `app.py`
- `templates/index.html`
- `requirements.txt`
- `Dockerfile`
- `firebase.json`
- `packages.txt`
- `1-klik.bat`
- `push_github.bat`
- `setup_github_actions.sh`

Runtime penting:

- Windows local OCR:
  - `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Linux container:
  - `tesseract-ocr`
  - `tesseract-ocr-ind`
  - `poppler-utils`

## Aturan output file `app.py`

### Format BTP JAK

Dipakai untuk lokasi seperti:

- `BOO`
- `CLT`

Format:

```text
(JENIS KEGIATAN) (IDENTITAS ASET) (DD-MM-YYYY).pdf
```

Contoh:

```text
PERAWATAN WESEL W23B BOO 01-06-2026.pdf
```

### Format BTP BD

Dipakai untuk lokasi seperti:

- `BOP`
- `BTT`
- `COS`
- `MSG`
- `CGB`
- fallback `LOKASI`

Format:

```text
(Tahun-Bulan)_(Resor)_(Kode Ceklis)_(Jenis Kegiatan)_(Identitas Aset)_(DD-MM-YYYY).pdf
```

Contoh:

```text
2026-6_Resor 1.21 Boo_BPBYE1_Perawatan_WESEL W11 MSG_01-06-2026.pdf
```

## Mapping lokasi penting

Prioritas mapping lama:

- `CIOMAS` / `COS` -> `COS`
- `MASENG` / `MSG` -> `MSG`
- `CIGOMBONG` / `CGB` -> `CGB`
- `BOGORPALEDANG` / `PALEDANG` -> `BOP`
- `BATUTULIS` / `BTT` -> `BTT`
- `CILEBUT` -> `CLT`
- `BOGOR` -> `BOO`

Kalau tidak cocok:

- parsing generik setelah keyword:
  - `LOKASI`
  - `STASIUN`
  - `RESOR`

Kalau tetap gagal:

- pakai `LOKASI`

## Keyword aset penting di `app.py`

Deteksi utama saat ini mencakup:

- `WESEL` -> `BPBYE1`
- `PDSE` -> `BPBYE2`
- `SERAT OPTIK` -> `BPBKF4`
- `PTPP` -> `BPBKS17`
- `PINTU PERLINTASAN` -> `BPBKS17`
- `PTDS` -> `BPBKS15`
- `PTLS` -> `BPBKS16`
- `AXLE COUNTER` -> `BPBYE7`
- `PERAGA SINYAL` -> `BPBYE3`
- `CATU DAYA` -> `BPBYE14`

## Riwayat penting `app.py`

### Commit acuan

- `aa9fa02` - `Update OCR parsing rules`
- `4338678` - `update terbaru`

### Perubahan penting yang sudah masuk

1. Fix race condition download ZIP
   - tidak lagi pakai global 1 path
   - sekarang pakai `download_id` unik dan `_downloads`

2. Cleanup ZIP temp setelah download
   - route `/download/<download_id>`
   - file temp dihapus setelah `send_file`

3. Lokasi generik tetap hormati mapping lama dulu

4. Nomor wesel dibuat lebih fleksibel
   - helper `extract_wesel_ids(...)`
   - cegah false positive `WSL...`

5. Support multi-aset lebih luas
   - 1 PDF bisa hasilkan beberapa output dalam ZIP

6. Routing format BTP JAK vs BTP BD dipertahankan

7. Ditambah helper reusable:
   - `process_pdf_entries(...)`
   - dipakai oleh `desktop_app.py`

## Status `app.py` saat ini

Route utama:

- `/`
- `/process`
- `/download/<download_id>`

Fungsi penting:

- `process_pdf_ocr(...)`
- `detect_doc(...)`
- `build_filename(...)`
- `process_pdf_entries(...)`

Catatan penting:

- helper `process_pdf_entries(...)` sudah ada
- tapi route Flask `/process` masih punya flow proses sendiri
- jadi masih ada duplikasi logic

## Status downloader P3-STE

File:

- `download_p3ste_rekap.py`

Fungsi:

- login ke P3-STE bila perlu
- baca captcha teks HTML
- minta jawaban captcha ke user
- filter rekap checklist
- ubah tabel ke 100 data
- download semua link `Cetak`

Filter user:

- tanggal awal
- tanggal akhir
- tipe checklist:
  - `Perawatan`
  - `Pemeriksaan`

Filter tetap:

- `asset=0`
- `category=0`
- `daop=1`
- `resort=170`
- `nipp=0`
- `noasset=0`
- `hasil=baik`
- `status=done`

Perubahan penting:

- tidak pakai tombol `Unduh Semua PDF`
- pakai link `Cetak` per baris
- tunggu tabel 10 data siap dulu
- baru ubah ke 100 data
- tunggu loading lagi sebelum download

Fungsi penting:

- `fetch_summary(...)`
- `run(...)`
- `menu(...)`

Menu CLI:

1. buat data login
2. pilih data login
3. tampilkan total halaman dan data
4. proses download

Penyimpanan lokal:

- `.p3ste-browser`
- `.p3ste-logins.json`

Default output:

- `Downloads\P3STE`

Argumen penting:

- `--awal`
- `--akhir`
- `--tipe`
- `--output`
- `--show`
- `--wait-ms`
- `--table-timeout-ms`
- `--direct`
- `--self-test`

Catatan:

- `--show` = browser terlihat
- tanpa `--show` = headless
- captcha belum otomatis dihitung; user jawab manual

## Status `desktop_app.py`

File:

- `desktop_app.py`

UI sekarang ada 2 tab:

### 1. Download Rekap

- pilih data login
- isi tanggal awal/akhir
- pilih tipe checklist
- pilih folder output
- opsi tampilkan browser
- tombol:
  - `Tampilkan total halaman dan data`
  - `Download`

### 2. Proses PDF

- pilih `Perawatan` / `Pemeriksaan`
- pilih `BTP JAK` / `BTP BD`
- pilih banyak file PDF
- proses OCR
- tampilkan hasil sukses/error
- simpan ZIP

Integrasi:

- downloader tab pakai:
  - `download_p3ste_rekap.fetch_summary`
  - `download_p3ste_rekap.run`
- OCR tab pakai:
  - `app.process_pdf_entries`

## Dependency

`requirements.txt` sekarang:

- `Flask`
- `Werkzeug`
- `pdf2image`
- `pytesseract`
- `Pillow`
- `gunicorn`
- `playwright`

## Cara jalan

Web app:

```powershell
py app.py
```

Downloader CLI:

```powershell
py download_p3ste_rekap.py
```

Downloader langsung:

```powershell
py download_p3ste_rekap.py --awal 01/05/2026 --akhir 31/05/2026 --tipe Perawatan --show
```

Desktop app:

```powershell
py desktop_app.py
```

Kalau Playwright browser belum ada:

```powershell
python -m playwright install chromium
```

## Validasi yang pernah dilakukan

- `python -m py_compile download_p3ste_rekap.py`
- `python -m py_compile desktop_app.py`
- `python -m py_compile app.py`
- `python -c "import desktop_app; print('desktop_app import OK')"`
- `python download_p3ste_rekap.py --self-test`

Status:

- syntax OK
- self-test downloader OK
- belum ada bukti test end-to-end penuh intranet dari dokumen ini

## Known gap

1. Captcha P3-STE belum otomatis dihitung.
   - sekarang user jawab manual

2. `app.py` masih punya duplikasi logic.
   - route `/process` belum dipotong ke `process_pdf_entries(...)`

3. Downloader tergantung:
   - intranet aktif
   - login/session aktif
   - struktur halaman P3-STE tidak berubah besar

4. Dokumen lama tentang workflow `Patur` / curl parser tidak lagi jadi acuan utama project ini.
   - acuan aktif sekarang: Playwright downloader + Flask OCR + desktop app

## Rekomendasi next step

1. Rapikan `app.py`
   - refactor route `/process` agar pakai `process_pdf_entries(...)`

2. Pertahankan `summary.md` ini sebagai dokumen tunggal.

3. Kalau ada update besar berikutnya:
   - update file ini saja
   - jangan buat `.md` baru kecuali memang beda topik total
