# CATATAN KERJA BELUM SELESAI - Lanjut di PC Kantor

> Tanggal: 17 Juli 2026 | Status: PENDING | Repo: pangjaw/ganti-nama-app

## Pending 1: Merge Lokasi Bolak-Balik (UTAMA)
**Masalah:** Ada 2 versi lokasi: `BOO-CLT` vs `CLT-BOO`, `BTT-MSG` vs `MSG-BTT`, `CCR-MSG` vs `MSG-CCR`
**Minta:** Gabung ke canonical, jangan bikin baris baru. Contoh `BOO-CLT` -> `CLT-BOO`.

**Fix:**
Tambah di `app.py` atas (sekitar L37):
```python
STATION_ORDER = {"BJD":0,"CLT":1,"BOO":2,"BOP":3,"BTT":4,"COS":5,"MSG":6,"CGB":7,"CCR":8,"BNR":9}
def canonicalize_loc(loc):
    if not loc: return ""
    parts = [p.strip() for p in loc.split("-") if p.strip()]
    seen=set(); uniq=[]
    for p in parts:
        if p not in seen:
            seen.add(p); uniq.append(p)
    return "-".join(sorted(uniq, key=lambda x: (STATION_ORDER.get(x,99), x)))
```
Wrap semua return di:
- `get_standard_loc()` 
- `extract_funcloc()`
- `get_dual_loc()`
- `get_jpl_inline_loc()`
-> `return canonicalize_loc(...)`

Sync 3 file: `app.py`, `Aplikasi/core.py`, `Aplikasi/app.py`

**Test:**
```
python scratch/test_loc_canonical.py  # assert BOO-CLT == CLT-BOO
python batch_process_app.py
# cek tidak ada lagi BOO-CLT, MSG-BTT, CCR-MSG
```

## Pending 2: POINT LOCK W81
- `POINT LOCK PL BOO` harusnya `POINT LOCK W81 BOO`
- Sudah fix prioritas POINT LOCK > WESEL di app.py L324
- Info: TIDAK ADA POINT LOCK DI CGB, hanya W81, W81 masuk POINT LOCK
- Pending: test 2 file W81 + full batch 446 file verify WESEL/SINYAL gak rusak

## Pending 3: SERAT OPTIK ER tanpa lokasi
File `PERAWATAN SERAT OPTIK ER 22-01-2026.pdf` (6 duplikat) tanpa lokasi -> perlu fallback loc logic.

## File Penting
- Acuan aset: `notes/30_Database_Pengetahuan/33_Data_Aset_Referensi.md` (372 aset)
- Detail handover lengkap: `notes/40_Task_dan_Log/45_Handover_PC_Kantor.md`
- Test folder: `FILE BUG/Januari 2026/SUDAH RENAME/` (446 file, JANGAN PUSH - sudah di .gitignore)

## Cara Lanjut di Kantor
1. `git pull origin main`
2. Edit `app.py` -> canonicalize
3. Mirror ke `Aplikasi/core.py` & `Aplikasi/app.py`
4. `python batch_process_app.py` test
5. Push lagi

## Git Push Info
- `.gitignore` sudah ignore `FILE BUG/`, `backup_*/`, `*.bak`, `tesseract/`, exe besar, dll
- Remote: https://github.com/pangjaw/ganti-nama-app.git
- Branch: main

## Status Akhir Laptop Rumah
- [x] POINT LOCK logic partial done
- [ ] Canonical loc BELUM
- [x] .gitignore updated
- [x] Handover docs created
- [ ] Push GitHub (next step)
