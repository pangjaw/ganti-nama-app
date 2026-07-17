# 🐛 Temuan & Rencana Perbaikan — Batch 3 (DATA ASET RESOR 2026)

#task #backlog #bug

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

Halaman ini mencatat temuan dari validasi menggunakan acuan resmi **`DATA ASET RESOR 2026.pdf`** (menggantikan `data aset.xlsx` lama yang tidak akurat).

> [!warning] Data referensi baru: [[33_Data_Aset_Referensi]]
> Total aset SAP benar = **372** (bukan 556). Total target file/bulan = **398**.

---

## 📋 Ringkasan Hasil Validasi

### Yang Match Sempurna ✅

| Kategori | File OCR | File Target | Aset OCR | Aset SAP |
|:---|---:|---:|---:|---:|
| DETEKSI KA | 139 | 139 | 139 | 139 |
| PDSE | 8 | 7 | 7 | 7 |
| CTS/TSC | 2 | 2 | 2 | 2 |
| SERAT OPTIK | 71 | 22 | 22 | 22 |

> [!note] SERAT OPTIK file count 71 vs target 22 → masalah dedup per funcloc. Fix: hanya pakai 1 funcloc pertama.

### Yang Kurang/Lebih ⚠️

| Kategori | File OCR | Target File | Aset OCR | Aset SAP | Selisih |
|:---|---:|---:|---:|---:|---:|
| WESEL | 64 | 62 | 32 | 31 | +1 aset |
| SINYAL | 120 | 125 | 118 | 125 | -7 aset |
| PINTU PERLINTASAN | 26 | 10 | 16 | 10 | +6 aset (campur PTPP) |
| CATU DAYA | 9 | 9 | 7 | 9 | -2 aset |
| POINT LOCK | 0 | 2 | 0 | 2 | HILANG SEMUA |
| PTLS | 0 | 8 | 0 | 8 | HILANG SEMUA |
| PTPP (JPL) | 0 | 11 | 0 | 11 | HILANG SEMUA |
| **TOTAL** | **446** | **398** | **350** | **372** | **-22 aset** |

---

## 🔴 Temuan Kritis

### A1. POINT LOCK dipaksa jadi WESEL (BPBYE1 → harus BPBYE12)

**Lokasi**: [app.py L337-L351](file:///c:/Users/dikarm/Documents/Server/ganti-nama-app/app.py#L337-L351)

**Masalah**: Deteksi `POINT LOCK` atau `PENGAMAN WESEL` memakai kode `BPBYE1` + kategori `WESEL`.

**Fix**:
- Kode baru: **BPBYE12**
- Kategori baru: `POINT LOCK`
- SAP: BOO=1, CGB=1 → total 2 aset
- Output: `PERAWATAN POINT LOCK PL ... BOO dd-mm-yyyy.pdf`

### A2. BOJONGGEDE tidak di-map

**Lokasi**: [app.py detect_doc](file:///c:/Users/dikarm/Documents/Server/ganti-nama-app/app.py#L63)

**Masalah**: `get_standard_loc`/`extract_funcloc` tidak punya `BOJONGGEDE` → `BJD-CLT`.
**Akibat**: DETEKSI KA di BJD-CLT kehilangan lokasi, jadi 0 vs target 5.

**Fix**: Tambah `"BOJONGGEDE" | "BOJONG GEDE"` → `"BJD-CLT"` di LOC_ALIAS.

### A3. SERAT OPTIK: file duplikat per funcloc

**Masalah**: 1 PDF SERAT OPTIK berisi banyak OTB (contoh: ER MSG ada OTB 1-6). OCR detect tiap OTB → hasilkan 6 file. Padahal harusnya **1 file per PDF** (hanya pakai funcloc pertama).

**Fix**: Di app.py, untuk kategori SERAT OPTIK, hanya ambil **satu funcloc pertama** → no duplicate file.

### A4. PTPP (JPL) tercampur dengan PINTU PERLINTASAN

**Masalah**: Script banding memetakan PTPP → PINTU PERLINTASAN. Di DATA ASET RESOR 2026, ini **dua kategori terpisah**:
- PINTU PERLINTASAN = 10 aset
- PTPP (Telkom JPL) = 11 aset

**Fix**: Pisah di CAT_MAP dan SAP data.

### A5. PTLS salah mapping (BPBKS16 → WAYSTATION)

**Lokasi**: [test_batch_sap.py L33](file:///c:/Users/dikarm/Documents/Server/ganti-nama-app/test_batch_sap.py#L33)

**Masalah**: `BPBKS16 = "WAYSTATION"` — harusnya `BPBKS16 = "PTLS"`.
**Akibat**: 8 file PTLS masuk WAYSTATION, PTLS = 0 di output.

**Fix**: Ganti mapping. PTLS = single lokasi. Format: `PERAWATAN PTLS RADIO BOO 29-01-2026.pdf`.

---

## 🟡 Temuan Signifikan

### B1. Dual-loc legitimate

Dual-loc (BOP-BTT, BTT-MSG, CCR-MSG, MSG-BTT, MSG-CCR) adalah aset legitimate di DETEKSI KA & SINYAL. Bukan false positive.

### B2. SINYAL kurang 7 aset

Missing: CGB=0 vs 4, COS=0 vs 4, MSG=4 vs 13. Perlu cari file fisik.

### B3. CATU DAYA kurang 2 aset

BOO=1 vs 2, COS=1 vs 2. Perlu cari.

### B4. WESEL ada +1 aset

BOO=17 vs 16. Lihat file mana yang ekstra.

---

## 🔧 Rencana Perbaikan

### Phase 1: Fix Data Referensi
- `[ ]` Update `test_banding_sap.py` — pisah PTPP, POINT LOCK data, SAP ref dari PDF
- `[ ]` Update `test_batch_sap.py` — BPBKS16 → PTLS, data referensi dari PDF

### Phase 2: Fix `app.py`
- `[ ]` POINT LOCK: BPBYE12, kategori baru, jangan merge WESEL
- `[x]` BOJONGGEDE → BJD-CLT mapping ✅ (Tahap 10)
- `[ ]` SERAT OPTIK: hanya 1 funcloc pertama
- `[x]` PTPP: fix table noise, regex alphanumeric, single-output ✅ (Tahap 10)
- `[ ]` Dual-loc normalization: BTT-BOP→BOP-BTT, CCR-MSG→MSG-CCR, BTT-MSG→MSG-BTT

### Phase 3: Cari File Hilang
- `[ ]` SINYAL: CGB, COS — cek folder BELUM RENAME
- `[ ]` CATU DAYA: BOO, COS
- `[ ]` DETEKSI KA: BJD-CLT=0 (terkait BOJONGGEDE fix)

### Phase 4: Rename Ulang
- `[ ]` Proses ulang file Januari 2026 dengan app.py yang sudah fix

---

## 🔄 Koneksi Antar Note

- [[33_Data_Aset_Referensi]] — Data aset resmi dari PDF
- [[41_Rencana_Perbaikan]] — Backlog perbaikan umum
- [[42_Riwayat_Pembaruan]] — Riwayat update
- [[00_Dashboard|Kembali ke Dashboard]]
