# 🔍 Cara Kerja OCR & Ekstraksi PDF (`app.py`)

#arsitektur #ocr

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

Aplikasi `app.py` menggunakan teknologi OCR (Optical Character Recognition) untuk mendeteksi data teks di dalam PDF hasil scan, guna mengenali jenis dokumen dan menamainya kembali secara terstruktur.

---

## 🛠️ Alur Pemrosesan Dokumen

Proses pengolahan PDF di dalam `app.py` mengikuti alur pipeline berikut:

```mermaid
graph TD
    A[PDF Uploaded] --> B[Convert Page 1 to Image]
    B --> C[Convert to Grayscale & Autocontrast]
    C --> D[Crop Top 30% Area]
    D --> E[Run PyTesseract OCR]
    E --> F[Extract Text string]
    F --> G[Run Pattern Matching / Regex]
    G --> H[Rename PDF File]
```

---

## 💻 Detail Implementasi Langkah-Langkah

### 1. Konversi Halaman PDF ke Gambar
Pemeriksaan P3-STE biasanya hanya memerlukan data pada lembar pertama dokumen.
*   **Modul**: `pdf2image.convert_from_bytes()`
*   **Resolusi**: `dpi=150` (keseimbangan optimal antara kecepatan proses dan keakuratan OCR).
*   **Rentang Halaman**: `first_page=1, last_page=1` (hanya mengambil halaman pertama).

```python
# Potongan kode implementasi
images = convert_from_bytes(file_bytes, dpi=150, first_page=1, last_page=1)
img = images[0].convert('L') # Ubah ke grayscale (L) untuk meningkatkan kontras OCR
```

### 2. Autocontrast & Cropping Area
Kualitas scan dokumen di lapangan bisa sangat bervariasi.
*   **Autocontrast**: `ImageOps.autocontrast(img)` digunakan untuk menyeimbangkan histogram warna abu-abu agar text hitam terlihat tajam dan background putih bersih.
*   **Cropping**: Kunci penting kecepatan dan keakuratan OCR proyek ini adalah pemotongan area (cropping). Bagian header dokumen (yang memuat stasiun, kode asset, dan tipe checklist) hanya berada di bagian atas halaman.
    *   Lebar dipotong penuh: `width * 1.0`
    *   Tinggi dipotong hanya bagian atas: `height * 0.30` (30% teratas)

```python
img_cropped = img.crop((0.0, 0.0, width * 1.0, height * 0.30))
text_crop = pytesseract.image_to_string(img_cropped, lang='ind+eng').upper()
```

### 3. Deteksi Dokumen & Ekstraksi Metadata (`detect_doc()`)
Hasil teks dari OCR (`text_crop`) kemudian dicocokkan menggunakan regex dan pencarian kata kunci:

*   **Pola Deteksi Sinyal**:
    ```python
    SIGNAL_PATTERN = re.compile(r'\b([BJLMSXU]+\.?\s?\d{1,3}[A-Z]?)\b')
    ```
    Pola ini mendeteksi kode sinyal khas kereta api seperti `J.10`, `JL92`, `S14`, dll.

*   **Pengelompokan Lokasi**:
    *   **BTP Jakarta** (`BTP_JAK_LOCS`): `"BOO"`, `"CLT"` (Bogor, Cilebut).
    *   **BTP Bandung** (`BTP_BD_LOCS`): `"BOP"`, `"BTT"`, `"COS"`, `"MSG"`, `"CGB"`.

*   **Daftar Branch `detect_doc()` (Gerbang A — OCR-based)**:
    Urutan branch menentukan prioritas deteksi. Branch pertama yang match akan dieksekusi.

    | # | Keyword Match | Kode | Kategori | Ekstraksi Aset |
    |---|--------------|------|----------|----------------|
    | 1 | `PERAWATAN WESEL` / `PENGGERAK WESEL` | `BPBYE1` | WESEL | Regex `W{n}{suffix}` per baris |
    | 2 | `POINT LOCK` / `PENGAMAN WESEL` | `BPBYE1` | WESEL | Sama dengan #1 |
    | 3 | `PERALATAN DALAM PERSINYALAN ELEKTRIK` | `BPBYE2` | PDSE | Single asset, loc dari OCR |
    | 4 | `SERAT OPTIK` + `JPL` | `BPBKF4` | SERAT OPTIK | Ekstrak JPL per baris |
    | 5 | `SERAT OPTIK` + `ER` | `BPBKF4` | SERAT OPTIK | Parse TRA lines → ER/ER TELKOM |
    | 6 | `TELEKOMUNIKASI DI PINTU PERLINTASAN` | — | PTLP | `extract_jpl_assets()` |
    | 7 | `PINTU PERLINTASAN` | `BPBKS17` | PINTU PERLINTASAN | `extract_jpl_assets(multi_word=True)` |
    | 8 | `TELEKOMUNIKASI DI STASIUN` | `BPBKS15` | PTDS | Single asset |
    | 9 | `TELEKOMUNIKASI DI LUAR STASIUN` | `BPBKS16` | PTLS | `get_ptls_loc()` — cari `LUAR` di judul, lalu cari baris `LOKASI` di bawahnya. Parsing nama lokasi dari LOKASI field. Special map: `DEPOK` → `BOO` |
    | 10 | `RADIO BASESTATION` | `BPBKF1/2/3` | RADIO BASESTATION | Sub-tipe: Tait/Digital/standar |
    | 11 | `SISTEM WAYSTATION` / `RADIO WAYSTATION` | `BPBKS5/BPBKS16` | WAYSTATION | Multi-asset TLK parsing |
    | 12 | `CTC` + `CTS` | `BPBYE4` | CTC-CTS | Single asset |
    | 13 | `CATU DAYA` | `BPBYE14` | CATU DAYA | Single asset |
    | 14 | `PERAWATAN AXLE COUNTER` | `BPBYE7` | AXLE COUNTER | Regex `ZP{n}{suffix}` per baris |
    | 15 | `PERAGA SINYAL` | `BPBYE3` | PERAGA SINYAL | Regex signal code per baris |

*   **Gerbang B (Fallback Filename-based)**:
    Jika Gerbang A tidak menghasilkan asset, deteksi fallback dari nama file upload menggunakan keyword yang sama.

*   **Renaming Logic**:
    Setelah kode asset, stasiun, dan kategori teridentifikasi, file PDF akan dinamai ulang dengan format standar yang mudah dibaca oleh sistem rekap dan manusia.

*   **Format BTP JAK**: `{JENIS} {KATEGORI} {ID} {LOKASI} {TANGGAL}.pdf`
*   **Format BTP BD**: `{PERIODE}_{RESOR}_{KODE}_{JENIS}_{IDENTITAS}_{TANGGAL}.pdf`

---

## 🔄 Koneksi Antar Note

- [[21_Struktur_Proyek]] — Peran `app.py` dalam keseluruhan proyek
- [[51_Alur_Kerja_Agent]] — Scenario 3: Alur upload PDF via web
- [[32_Arsitektur_Deploy]] — OCR server di-deploy ke Cloud Run
- [[11_Menjalankan_Aplikasi]] — Cara menjalankan `app.py` lokal
- [[00_Dashboard|Kembali ke Dashboard]]
