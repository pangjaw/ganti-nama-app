# 🔄 Handover PC Kantor — Pending Tasks

> [!important] Context
> Tanggal handover: 17 Juli 2026. User mau kerja, task belum 100%. Lanjut di PC kantor.
> Repo: `pangjaw/ganti-nama-app` | Branch: main | Ignore: `FILE BUG/`

## 1. Status Terakhir

### Task List Original (dari task.md)
- [x] POINT LOCK logic fix (W81)
- [ ] Merge lokasi bolak-balik (BOO-CLT = CLT-BOO) <- PENDING UTAMA
- [ ] Verify full batch 446 file tidak rusak logika lain

### File yang sudah di-edit di laptop ini
- `app.py` L324-338: POINT LOCK prioritas di atas WESEL + extract W81 (via `get_dual_loc`)
- `Aplikasi/core.py`: mirror sama
- `Aplikasi/app.py`: mirror sama (cek L1-80 sudah BJD-CLT mapping baru, tapi belum canonicalize)
- `.gitignore`: sudah ignore FILE BUG/ dll

---

## 2. Pending Utama: Merge BOO-CLT = CLT-BOO

### Masalah User
> "KENAPA SEKARANG ADA BTT & MSG , CCR & MSG? MAKSUDKU ITU DI TABLE SUDAH TERTULIS CLT-BOO, NAH KAMU TIDAK PERLU MENAMBAHKAN BARIS BARU BERNAMA BOO-CLT UNTUK ASET YG LOKASINYA BOO-CLT, CUKUP GABUNG KE CLT-BOO KARENA CLT-BOO DAN BOO-CLT ITU SAMA LOKASINYA, BEGITUPUN BTT-MSG DAN MSG-BTT, MSG-CCR DAN CCR-MSG. KALO MASIH KURANG PAHAM TANYA KEPADAKU"

Contoh di `FILE BUG/Januari 2026/SUDAH RENAME`:
- `PERAWATAN SINYAL B101 BOO-CLT 12-01-2026.pdf` vs `CLT-BOO` -> harus jadi 1 baris `CLT-BOO`
- `ZP 101A BTT-MSG` vs `CCR-MSG` vs `MSG-BTT` -> harus canonical

### Root Cause
- `extract_funcloc()`, `get_dual_loc()`, `get_standard_loc()`, `get_jpl_inline_loc()` preserve urutan OCR kiri-ke-kanan.
- Tidak ada normalisasi arah rel.

### Solusi yang sudah di-plan (lihat implementation_plan.md lama)
Definisikan urutan stasiun jalur Jakarta -> Sukabumi (dari tabel acuan `33_Data_Aset_Referensi.md`):

```
BJD (Bojonggede) 0 -> CLT 1 -> BOO 2 -> BOP 3 -> BTT 4 -> COS 5 -> MSG 6 -> CGB 7 -> CCR 8 -> BNR 9
```

Helper:

```python
STATION_ORDER = {"BJD":0,"CLT":1,"BOO":2,"BOP":3,"BTT":4,"COS":5,"MSG":6,"CGB":7,"CCR":8,"BNR":9}

def canonicalize_loc(loc_str: str) -> str:
    if not loc_str:
        return ""
    # ponytail: split dedup sort by STATION_ORDER, fallback 99 + alpha
    parts = [p.strip() for p in loc_str.split("-") if p.strip()]
    # dedup preserve
    seen=set()
    uniq=[]
    for p in parts:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    # sort
    uniq_sorted = sorted(uniq, key=lambda x: (STATION_ORDER.get(x,99), x))
    return "-".join(uniq_sorted)
```

Apply di semua return:
- `get_standard_loc()` -> return canonicalize_loc(result)
- `extract_funcloc()` -> canonicalize
- `get_dual_loc()` -> canonicalize
- `get_jpl_inline_loc()` internal di `Aplikasi/core.py` + `app.py`
- `extract_jpl_assets()` inline loc -> canonicalize
- PTLS, WS asset loc juga ikut karena call `get_standard_loc`

Sync 3 file WAJIB:
- `app.py` (root)
- `Aplikasi/core.py`
- `Aplikasi/app.py`

### Test yang harus dibuat di kantor
Buat `scratch/test_loc_canonical.py`:

```python
from app import canonicalize_loc
assert canonicalize_loc("BOO-CLT") == "CLT-BOO"
assert canonicalize_loc("CCR-MSG") == "MSG-CCR"
assert canonicalize_loc("MSG-BTT") == "BTT-MSG"
assert canonicalize_loc("BTT-BOP") == "BOP-BTT"
assert canonicalize_loc("CLT-BJD") == "BJD-CLT"
assert canonicalize_loc("BOO") == "BOO"
assert canonicalize_loc("") == ""
assert canonicalize_loc("BOP-BTT-MSG") == "BOP-BTT-MSG" # 3 code support
print("OK")
```

### Verify batch
```bash
python batch_process_app.py
# cek _hasil_app.json di FILE BUG/.../SUDAH RENAME
# unique loc tidak boleh ada pasangan terbalik
python scratch/check_duplicate_loc.py # buat script cek BOO-CLT vs CLT-BOO only one exists
```

> [!warning] Breaking Change
> Setelah fix, output lama BOO-CLT akan jadi CLT-BOO. Itu intended, user sudah approve.

---

## 3. Pending Kedua: POINT LOCK W81

### History
User lapor: output `POINT LOCK PL BOO` harusnya `POINT LOCK W81 BOO`.

### Info User (penting!)
- Q1: TIDAK ADA POINT LOCK DI CGB
- Q2: TIDAK ADA, HANYA ADA W81
- Q3: W81 MASUKNYA POINTLOCK SAJA (bukan WESEL)

### Fix yang sudah done di laptop ini
Di `app.py` L323-338:
```python
# GERBANG A: POINT LOCK prioritas di atas WESEL
if any(x in text_flat for x in ["POINT LOCK", "PENGAMAN WESEL"]):
    kode, kategori = "BPBYE12", "POINT LOCK"
    w_matches = extract_wesel_ids(text_flat, allow_generic=True)
    ...
```

### Yang masih pending di kantor
- [ ] Buat `scratch/test_pl_w81.py` -> verify W81 file ke-detect sebagai POINT LOCK W81 bukan PL
- [ ] Run batch mini test file W81: ada 2 file `PERAWATAN WESEL W81 BOO ...` cek hasil jadi `POINT LOCK`
- [ ] Full batch 446 file verify tidak break: WESEL count 17->16 BOO, SINYAL 118->125, dll
- [ ] Update docs `notes/20_Arsitektur_Kode/22_Logika_OCR.md` tentang prioritas POINT LOCK

Command test:
```bash
python scratch/ocr_w81.py
python batch_process_app.py
```

---

## 4. Pending Ketiga: SERAT OPTIK ER tanpa lokasi

File bermasalah: `FILE BUG/Januari 2026/SUDAH RENAME/PERAWATAN SERAT OPTIK ER 22-01-2026.pdf` (6 duplikat tanpa lokasi)

Analisa sebelumnya:
- Kemungkinan gambar BTT tapi OCR crop 0-40% tidak dapat lokasi karena lokasi di tengah/bawah.
- Solusi: untuk SERAT OPTIK ER, jika `get_standard_loc == ""` coba `extract_funcloc` + `get_dual_loc` full text, atau fallback dev: cek BTT etc.
- Atau memang file SO ER Telkom? Cek lagi.

File referensi ada di `.tempmediaStorage/...` di brain dir.

### PTLS / PTPP quirks
- PTLS sudah fixed `get_ptls_loc`
- PTPP sudah ada filename-based detection, tapi masih perlu cek dedup dual loc.

---

## 5. File Penting & Lokasi

```
Root:
- app.py = logic utama OCR
- Aplikasi/core.py = mirror untuk desktop EXE
- Aplikasi/app.py = mirror untuk Flask paket Aplikasi/
- batch_process_app.py = batch processor via app.py logic (dipakai test)
- notes/30_Database_Pengetahuan/33_Data_Aset_Referensi.md = tabel acuan 372 aset
- FILE BUG/Januari 2026/SUDAH RENAME/ = 446 file sudah rename (ground truth, jangan di-push)
- scratch/ = script test sementara (sudah di .gitignore sekarang)

Handover baru:
- notes/40_Task_dan_Log/45_Handover_PC_Kantor.md (file ini)
- CATATAN_KERJA_BELUM_SELESAI.md (root, quick access)
```

### 3 File Logic Sync
Perubahan apapun di `get_standard_loc` dll HARUS sync manual ke 3 file:
1. `app.py`
2. `Aplikasi/core.py`
3. `Aplikasi/app.py`

---

## 6. Next Step di PC Kantor (step by step)

1. Pull repo: `git pull origin main`
2. Buka `CATATAN_KERJA_BELUM_SELESAI.md` quick summary
3. Implement `canonicalize_loc` di `app.py`:
   - Tambah di atas BTP_JAK_LOCS (sekitar L37)
   - Wrap semua return loc
4. Mirror ke 2 file Aplikasi/
5. Buat `scratch/test_loc_canonical.py` dan run
6. Run `python batch_process_app.py` -> cek `_hasil_app.json`
7. Verify tidak ada `BOO-CLT`, `MSG-BTT`, `CCR-MSG` lagi, hanya canonical `CLT-BOO`, `BTT-MSG`, `MSG-CCR`
8. Run full test POINT LOCK W81 (2 file)
9. Jika oke, push lagi

---

## 7. Push Git Info

- Remote: `https://github.com/pangjaw/ganti-nama-app.git`
- Branch: `main` (cek `git branch --show-current`)
- `.gitignore` sudah include `FILE BUG/` -> aman push
- Commit terakahir di laptop: akan ada `docs: handover pending tasks + ignore FILE BUG`
- Command push: pakai `push_github.bat` atau manual `git push -u origin main`

> [!tip] Jangan lupa di kantor
> `git config --global user.name` & `user.email` kalau belum set

---

## 8. Catatan Tambahan

- File `FILE BUG/` total ~1GB++ (446 PDF). Jangan pernah push, ignore sudah di set.
- `tesseract/` dan exe besar juga di-ignore sekarang.
- Jika mau build exe: `build_portable.bat`
- Jika mau test cepat SERAT OPTIK ER: `scratch/debug_er_loc.py`

Kontak: lanjut via vault Obsidian.

