# IMPROVEMENT SUMMARY: Implementasi Multi-Aset Global, Handling Duplikat & BTP Routing

**Tanggal:** 2026-06-21
**Target File:** `app.py`

## 1. Masalah Saat Ini
- Logika ekstraksi multi-aset hanya diimplementasikan pada kategori **"PERAWATAN/PENGGERAK WESEL"**.
- Kategori lain seperti **POINT LOCK**, **PTPP**, dan **PINTU PERLINTASAN** masih menggunakan `re.search()` (hanya mengambil 1 ID pertama).
- Ada instruksi tambahan: **Semua aset harus mendukung format BTP JAK dan BTP BD.** Meskipun saat ini routing `get_btp(loc)` sudah berjalan untuk menentukan BTP mana berdasarkan lokasi, kita harus memastikan `build_filename` dieksekusi dengan benar untuk *semua jenis aset*.

## 2. Perbaikan yang Akan Dilakukan (app.py)

**A. Mengubah `re.search` menjadi `re.findall` untuk semua deteksi ID Aset:**
1. **POINT LOCK (BPBYE1):**
   - Akan mengekstrak semua kode `W\d+[A-Z]*` menggunakan `re.findall`.
2. **PTPP (BPBKS17):**
   - Akan mengekstrak semua angka JPL (`JPL\s+(?:ELEKTRIK\s+)?(?:NO[.\s]*)?(\d+)`).
   - Serta fallback untuk semua JPL huruf (`JPL\s+([A-Z]+(?:\s+[A-Z\-]+)*)`).
3. **PINTU PERLINTASAN (BPBKS17):**
   - Sama seperti PTPP, akan mengekstrak semua angka JPL dan JPL huruf yang muncul menggunakan `re.findall`.
4. *(Note: SERAT OPTIK sudah menggunakan looping per-baris sehingga sifatnya sudah multi-aset, PDSE/PTDS/PTLS/CATU DAYA memang tidak memiliki ID spesifik selain lokasi).*

**B. Filter Duplikat Internal (Mencegah Spam Warning):**
Jika di dalam 1 file PDF tertulis "JPL 04" sebanyak 5 kali, `re.findall` akan menangkap 5 ID "JPL 04". Kita akan mem-filter menggunakan set unik:
```python
unique_ids = []
for m in matches:
    if m not in unique_ids: unique_ids.append(m)
```
Sehingga tidak ada ekstrak ID yang berulang dari satu halaman PDF.

**C. Handling Output Duplikat Eksternal:**
Sistem sudah memiliki logika (line 278-283):
```python
if new_name not in unique_filenames:
    zip_f.writestr(new_name, file_bytes)
    # ...
else:
    duplicate_errors.append(f"⚠️ {f.filename}: Duplikat ({new_name})")
```
Kita pertahankan ini. File output pertama yang masuk akan diproses, sisanya akan dilewati dan menghasilkan notifikasi ke UI web.

**D. Routing BTP JAK & BTP BD untuk SEMUA Aset:**
Fungsi `build_filename` akan diterapkan secara universal untuk semua hasil deteksi, diatur oleh variabel boolean `format_bd` yang nilainya diambil dari `get_btp(loc)`.
- Jika lokasi adalah **BOO** atau **CLT** -> `BTP JAK` -> Format: `JENIS IDENTITAS TANGGAL.pdf`
- Jika lokasi adalah **BOP, BTT, COS, MSG, CGB**, atau **LOKASI** -> `BTP BD` -> Format: `PERIODE_Resor 1.21 Boo_KODE_Jenis_Identitas_Tanggal.pdf`

## 3. Hasil Akhir (Expected Output)
Jika user mengupload `15-06-2026_Ceklis_Pintu_Perlintasan.pdf` yang berisi teks untuk "JPL 10" dan "JPL 11" di lokasi CLT:
- Output 1 (BTP JAK): `PERAWATAN PINTU PERLINTASAN JPL 10 CLT 15-06-2026.pdf`
- Output 2 (BTP JAK): `PERAWATAN PINTU PERLINTASAN JPL 11 CLT 15-06-2026.pdf`

Jika dokumen yang sama lokasinya terdeteksi sebagai BOP (Paledang):
- Output 1 (BTP BD): `2026-6_Resor 1.21 Boo_BPBKS17_Perawatan_PINTU PERLINTASAN JPL 10 BOP_15-06-2026.pdf`
- Output 2 (BTP BD): `2026-6_Resor 1.21 Boo_BPBKS17_Perawatan_PINTU PERLINTASAN JPL 11 BOP_15-06-2026.pdf`
