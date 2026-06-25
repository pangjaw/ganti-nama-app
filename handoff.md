# Handoff Codex - ganti-nama-app

Tanggal ringkasan: 2026-06-25

## Project

File utama:

```text
C:\Users\dikarm\Documents\Server\ganti-nama-app\app.py
```

Aplikasi Flask untuk upload PDF ceklis, OCR halaman 1 bagian atas 30 persen, deteksi jenis dokumen/aset/lokasi, rename file, lalu output ZIP.

OCR utama saat ini:

```python
pdf2image.convert_from_bytes(..., dpi=150, first_page=1, last_page=1)
img.crop((0.0, 0.0, width * 1.0, height * 0.30))
pytesseract.image_to_string(..., lang='ind+eng').upper()
```

## Aturan kerja dari user

1. Jangan langsung update script tanpa perintah user.
2. Sebelum update, jelaskan bug dan fix secara singkat.
3. User menentukan lanjut atau tidak.
4. Diff harus kecil dan fokus.
5. Jangan refactor besar tanpa alasan kuat.
6. Jangan mengubah OCR utama kecuali user benar-benar minta.
7. Mapping lokasi lama tidak boleh dihapus.
8. Untuk lokasi, script harus cek mapping lama lebih dulu. Kalau tidak cocok, baru pakai fallback generik.
9. Jangan menyentuh logic aset lain seperti sinyal/AXC tanpa persetujuan user.

## Perubahan yang sudah ada sebelumnya

1. Fix race condition download ZIP:
   - Sebelumnya memakai global `_last_zip_path`.
   - Sekarang memakai `_downloads = {}` dan `download_id` unik.
   - Response `/process` mengirim `download_url: f'/download/{download_id}'`.
   - Route download menjadi `/download/<download_id>`.

2. Fix cleanup ZIP temp:
   - Import `after_this_request` dari Flask.
   - Setelah `send_file`, ZIP temp dihapus dengan `os.remove(zip_path)`.
   - Kalau `os.remove` gagal, `OSError` diabaikan.

## Perubahan yang diterapkan pada sesi ini

### 1. Lokasi generik, mapping lama tetap prioritas

Fungsi `get_standard_loc(text)` sekarang urutannya:

1. Cek mapping lama dulu:
   - `CIOMAS` atau `COS` -> `COS`
   - `MASENG` atau `MSG` -> `MSG`
   - `CIGOMBONG` atau `CGB` -> `CGB`
   - `BOGORPALEDANG` atau `PALEDANG` -> `BOP`
   - `BATUTULIS` atau `BTT` -> `BTT`
   - `CILEBUT` -> `CLT`
   - `BOGOR` -> `BOO`

2. Kalau mapping lama tidak cocok, cari lokasi generik setelah keyword:
   - `LOKASI`
   - `STASIUN`
   - `RESOR`

3. Lokasi generik berhenti saat bertemu kata pemutus, misalnya:
   - `DISETUJUI`
   - `DISETUJUL`
   - `PISETUJUI`
   - `DIKETAHUI`
   - `DILAKSANAKAN`
   - `OLEH`
   - `TANGGAL`
   - `PERIODE`
   - `NO`
   - `SC`

Contoh hasil:

```text
LOKASI SERPONG PISETUJUI HERU -> SERPONG
LOKASI SERPONG DISETUJUI HERU -> SERPONG
LOKASI TANAH ABANG DISETUJUI HERU -> TANAH ABANG
LOKASI BOGOR PISETUJUI HERU -> BOO
```

Catatan: lokasi generik ini ikut dipakai oleh cabang lain yang memakai `get_standard_loc`, termasuk sinyal, AXC, catu daya, telekomunikasi, pintu perlintasan, dan serat optik. Tetapi logic nomor aset masing-masing cabang belum semuanya diubah.

### 2. Nomor aset WESEL dibuat fleksibel

Ditambahkan helper:

```python
def extract_wesel_ids(text, allow_generic=False):
```

Tujuannya agar WESEL bisa membaca variasi:

```text
W21A -> W21A
21A -> W21A
21 A -> W21A
PENGGERAK WESEL ELEKTRIK 21A SRP -> W21A
```

Helper ini dipakai di:

1. Cabang OCR `PERAWATAN WESEL` atau `PENGGERAK WESEL`.
2. Cabang OCR `POINT LOCK` atau `PENGAMAN WESEL`.
3. Cabang filename fallback `WESEL ELEKTRIK`.

Regex memakai `W(?!SL)` agar ID seperti `WSL10032` tidak dianggap sebagai nomor wesel `W10032`.

## Contoh PDF Serpong

File contoh:

```text
C:\Users\dikarm\Documents\Server\ganti-nama-app\17-06-2026_PERAWATAN WESEL ELEKTRIK 2 MINGGUAN_Serpong(1).pdf
```

Yang terlihat di OCR crop halaman 1:

```text
PERAWATAN WESEL ELEKTRIK 2 MINGGUAN
WSL10032 : PENGGERAK WESEL ELEKTRIK 21A SRP
WSL10132 : PENGGERAK WESEL ELEKTRIK 11A SRP
WSL10133 : PENGGERAK WESEL ELEKTRIK 11B SRP
WSL10033 : PENGGERAK WESEL ELEKTRIK 21B SRP
WSL10034 : PENGGERAK WESEL ELEKTRIK 23A SRP
Lokasi Serpong
Tanggal 2026-06-17
```

Sebelum patch, output bisa salah:

```text
PERAWATAN WESEL W_UNKNOWN LOKASI 17-06-2026.pdf
PERAWATAN WESEL W21A SERPONG PISETUJUI HERU 17-06-2026.pdf
```

Setelah patch parser, target output non-BTP BD:

```text
PERAWATAN WESEL W21A SERPONG 17-06-2026.pdf
PERAWATAN WESEL W11A SERPONG 17-06-2026.pdf
PERAWATAN WESEL W11B SERPONG 17-06-2026.pdf
PERAWATAN WESEL W21B SERPONG 17-06-2026.pdf
PERAWATAN WESEL W23A SERPONG 17-06-2026.pdf
```

## Verifikasi yang sudah dilakukan

Tes parser `detect_doc` langsung:

```text
bad_ocr    -> [{'id': 'W21A', 'loc': 'SERPONG'}]
normal_ocr -> [{'id': 'W21A', 'loc': 'SERPONG'}]
multiword  -> [{'id': 'W21A', 'loc': 'TANAH ABANG'}]
old_map    -> [{'id': 'W21A', 'loc': 'BOO'}]
```

Tes sintaks:

```text
ast.parse(app.py) -> syntax ok
```

Belum dilakukan full upload test via Flask server dari Codex.

## Yang belum diubah

1. Validasi PDF masih case-sensitive:

```python
if not f.filename.endswith('.pdf'):
```

2. Format tanggal masih hanya `DD-MM-YYYY` dari filename.

3. PERAGA SINYAL:
   - Lokasi generik ikut kena patch karena memakai `get_standard_loc`.
   - Tetapi logic nomor aset sinyal masih lama.
   - Ada catatan bug lama: `valid_signals` dibersihkan menjadi `B210`, lalu `text_flat.find(s)` bisa gagal kalau OCR asli `B.210`.
   - Jangan patch tanpa izin user.

4. AXLE COUNTER / AXC:
   - Lokasi generik ikut kena patch karena memakai `get_standard_loc`.
   - Logic nomor aset AXC masih lama, regex `ZP...`.
   - Jangan patch tanpa izin user.

5. POINT LOCK filename branch masih:

```python
elif "POINT LOCK" in filename_upper:
    kode, kategori = "BPBYE7", "WESEL"
```

Padahal user pernah konfirmasi POINT LOCK harus sama dengan WESEL yaitu `BPBYE1`. OCR branch sudah `BPBYE1`, filename branch belum diubah. Jangan ubah tanpa izin user.

6. Jangan refactor besar `detect_doc`.

## Catatan Git dan GitHub

Saat dicek dari Codex, `git status` sempat gagal karena user sandbox berbeda:

```text
fatal: detected dubious ownership in repository
```

Di VS Code normal milik user, ini biasanya tidak muncul. Kalau muncul, perintah yang disarankan Git:

```powershell
git config --global --add safe.directory C:/Users/dikarm/Documents/Server/ganti-nama-app
```

Cara push manual dari VS Code:

```powershell
git status
git add app.py
git commit -m "Fix generic location and wesel asset parsing"
git push
```

Cara pull paksa di PC server setelah perubahan sudah di-push:

```powershell
git fetch origin
git reset --hard @{u}
```

Kalau branch upstream tidak diset, pakai salah satu:

```powershell
git reset --hard origin/main
git reset --hard origin/master
```

Hati-hati: `git reset --hard` membuang perubahan lokal yang belum di-commit.

## Instruksi untuk Codex berikutnya

Mulai dari membaca `app.py` terbaru dulu.

Jangan langsung update. Kalau user menemukan output salah:

1. Jelaskan penyebab bug.
2. Jelaskan fix kecil yang diusulkan.
3. Tunggu user bilang lanjut.
4. Jangan ubah OCR utama kecuali user minta.
5. Jangan ubah cabang sinyal/AXC/POINT LOCK besar-besaran tanpa izin.

