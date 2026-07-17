# 🐛 Daftar Temuan & Rencana Perbaikan — Batch 2

#task #backlog #bug

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

Halaman ini mencatat temuan bug lokasi aset dari hasil OCR dan rencana perbaikan untuk modul `app.py`.

---

## 📋 Daftar Temuan (Findings)

### A. Masalah Deteksi Aset (Regex)

| # | Bug | Contoh Output Salah | Harusnya | Sebab |
|---|-----|--------------------|---------|-------|
| 1 | `M` sebagai sinyal | `M314` | tidak muncul (OCR artifact) | `SIGNAL_PATTERN` tangkap `M`+digit padahal itu bagian `MJ14` |
| 2 | ZP21C terbaca ZP21 | `ZP21` | `ZP21C` | Regex alternation `[A-Z]{0,3}` prioritaskan empty match |

### B. Masalah Lokasi Per Aset

| # | Bug | Contoh Output Salah | Harusnya | Sebab |
|---|-----|--------------------|---------|-------|
| 3 | PDSE lokasi salah | `CCR` | `MSG` | `extract_funcloc` ambil dari LOKASI line yang beda |
| 4 | JPL 27 & 28 urutan lokasi | `BOO-CLT` | `CLT-BOO` | `get_jpl_inline_loc` pake urutan set (alphabetical) bukan urutan dokumen |
| 5 | MB101 lokasi kelebihan | `CCR-CGB-MSG` | `MSG-CGB` | `get_dual_loc` ambil semua kode dari baris, bukan dari kanan nama aset |
| 6 | ZP101A lokasi salah | `MSG-CCR` | per ZP sesuai baris | Sama — baris ZP201B `CCR-MSG`, ZP101A `MSG-CCR` |
| 7 | AXC 10A kelebihan lokasi | `BOO-BOP-BTT` | `BOO-BTT` | Fallback `extract_funcloc` ambil triple dari LOKASI line |
| 8 | MJ28 kelebihan lokasi | `BOO-BOP-BTT` | `BOP-BTT` | Sama |
| 9 | MJ48 kelebihan lokasi | `BOO-BOP-BTT` | `BOP-BTT` | Sama |
| 10 | MJ10 kelebihan lokasi | `BOO-BOP-BTT` | `BOP-BTT` | Sama |

---

## 🔧 Rencana Perbaikan

### Prioritas Tinggi

#### A. Regex Precision (Bug 1 & 2)

**Bug 1 — Filter M+digit sebagai false positive:**

Di `app.py` bagian `valid_signals` filter, tambah:

```python
# Skip false positive: "M314" (OCR artifact dari "MJ14")
if re.match(r'^M\d+$', s_clean):
    continue
```

**Bug 2 — Fix urutan alternation ZP:**

Ubah regex dari:
```python
r'\bZP\s?(?:(\\d{1,3})([A-Z]{0,3})|([A-Z]))\b'
```
Jadi:
```python
r'\bZP\s?(\\d{1,3})([A-Z]{1,2})?\b'
```
Dengan logika: ZP selalu diikuti angka. Huruf suffix opsional (0-2 karakter). Jika ZP diikuti huruf saja (tanpa angka), skip.

#### B. Per-Asset Location Extraction (Bug 3, 5, 6)

**Root cause**: `get_dual_loc(line)` scan seluruh isi baris untuk kode lokasi. Ini ambil semua kode dari kiri nama aset (termasuk `SIN11754`, dll) dan lokasi yang bukan milik aset tersebut.

**Fix**: Di setiap loop per-aset (WESEL, ZP, SIGNAL), extract location hanya dari **bagian kanan** nama aset dalam baris:

```python
# Setelah ketemu baris aset yang cocok:
asset_pos = line.upper().find(s.upper())
right_snippet = line[asset_pos:]  # ambil dari nama aset ke kanan
loc = get_dual_loc(right_snippet)  # cari lokasi cuma di kanan
```

Juga skip baris yang mengandung "LOKASI" agar tidak salah match ke header.

#### C. Fallback Chain (Bug 7-10)

**Root cause**: Saat `get_dual_loc(right_snippet)` gagal (kosong), kode jatuh ke `extract_funcloc(text_crop)` yang ambil dari baris LOKASI. Baris LOKASI kadang punya 3 kode (BOO-BOP-BTT) padahal aset cuma 2.

**Fix**: Tambah parameter `limit=2` di `get_dual_loc` untuk triple lokasi, atau fallback ke `get_standard_loc` (single loc) saja + skip `extract_funcloc`.

#### D. JPL Location Order (Bug 4)

**Root cause**: `get_jpl_inline_loc` iterate `loc_codes` set → urutan set (alphabetical: `BOO` sebelum `CLT`).

**Fix**: Ganti `get_jpl_inline_loc` pakai position-sorted scan (sama kayak `get_dual_loc`):

```python
def get_jpl_inline_loc(text_snippet):
    matches = []
    for code in loc_codes:
        for m in re.finditer(r'\b' + code + r'\b', text_snippet):
            matches.append((m.start(), code))
    matches.sort(key=lambda x: x[0])
    seen = set()
    found = [code for _, code in matches if not (code in seen or seen.add(code))]
    return "-".join(found)
```

---

## 📊 Status Implementasi

- `[x]` **Bug 1** — Filter M+digit ✅ M314 dari MJ14 tidak muncul
- `[x]` **Bug 2** — Regex ZP ✅ Suffix panjang benar (ZP26A bukan ZP26)
- `[x]` **Bug 3** — PDSE location ✅ Pakai `extract_funcloc` → MSG
- `[x]` **Bug 4** — JPL urutan lokasi ✅ CLT-BOO (urutan dokumen, bukan alphabetical)
- `[x]` **Bug 5** — Signal lokasi per-aset ✅ Scan per-baris text_crop
- `[x]` **Bug 6** — ZP lokasi per-aset ✅ Scan per-baris text_crop
- `[x]` **Bug 7-10** — Fallback chain triple location ✅ Position-sorted + extract_funcloc
- `[x]` **Test & verifikasi** dengan 5 file PDF sample → semua output sesuai harapan

> [!tip] Hasil test: [test_bugfix_v2.py](file:///c:/Users/dikarm/Documents/Server/ganti-nama-app/test_bugfix_v2.py)
> Jalankan `python test_bugfix_v2.py` untuk verifikasi ulang kapan saja.

---

## 🔄 Koneksi Antar Note

- [[42_Riwayat_Pembaruan]] — Riwayat update yang sudah dilakukan
- [[41_Rencana_Perbaikan]] — Rencana perbaikan batch sebelumnya
- [[00_Dashboard|Kembali ke Dashboard]]
