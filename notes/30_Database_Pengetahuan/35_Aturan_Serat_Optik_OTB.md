# 35 — Aturan Lengkap SERAT OPTIK OTB (ER SINYAL / ER RADIO / ER TELKOM)

#knowledge #ocr #serat-optik

> **Tujuan:** Dokumen ini adalah **aturan penuh** untuk `detect_doc()` dan grouping logic khusus SERAT OPTIK OTB.
> Agent masa depan WAJIB baca ini sebelum menyentuh kode terkait SO OTB.

---

## 1. Struktur OCR File SO OTB

Setiap file SO OTB punya header seperti ini di OCR:
```
CZ | TRA11236 : OTB FO ER SINYAL BTT
```
atau tanpa FO:
```
CZ | TRA11257 : OTB ER SINYAL CLT
```

Dan di bagian tabel ada:
```
1 Nama ODF/OTB
Jumlah Core Sesuai dengan Serat Optik yang ada di ODF/OTB 144
```

### PENTING: Jumlah Core TIDAK SAMA dengan Nomor OTB

| Apa | Di mana | Contoh |
|---|---|---|
| **Header aset** | `CZ | TRAxxxxx : OTB FO ER SINYAL BTT` | Ini baris identitas |
| **Jumlah Core** | `Jumlah Core ... ODF/OTB 144` | Ini **BUKAN** nomor OTB! |

144, 72, 96, 120 adalah **jumlah core fiber optik**, bukan nomor OTB.

---

## 2. Deteksi Sub-Type ER

### Priority (OCR > filename)

```python
# Deteksi dari OCR header
if has_er and has_otb:
    if "SINYAL" in text_flat:
        er_type = "ER SINYAL"
    elif "RADIO" in text_flat:
        er_type = "ER RADIO"
    elif "TELKOM" in text_flat:
        er_type = "ER TELKOM"
    else:
        er_type = "ER"  # generic fallback

# Fallback dari filename (jika OCR tidak detect)
if er_type is None:
    if "SINYAL" in filename_upper:
        er_type = "ER SINYAL"
    elif "RADIO" in filename_upper:
        er_type = "ER RADIO"
    elif "TELKOM" in filename_upper:
        er_type = "ER TELKOM"

if er_type is None:
    er_type = "ER"
```

### Bug Sejarah: "RADIO" dikira ER TELKOM

Dulu ada logika: `has_telkom_fn = "TELKOM" or "RADIO"` yg selalu true karena `"RADIO"` string truthy.

**Fix:** Deteksi terpisah — SINYAL, RADIO, TELKOM masing-masing.

---

## 3. Scan Nomor OTB (Baris Aset)

### Regex yang BENAR

```python
# PAKAI NEGATIVE LOOKBEHIND — exclude ODF/OTB (core count)
all_otb_nums_raw = re.findall(r'(?<!ODF/)\bOTB\s+(\d+)\b', text_flat)
all_otb_nums = sorted(set(int(n) for n in all_otb_nums_raw))
```

### Kenapa perlu `(?<!ODF/)`?

Tanpa lookbehind, `\bOTB\s+(\d+)\b` akan menangkap:
- `ODF/OTB 144` -> 144 (jumlah core, **bukan** nomor OTB!)
- `ODF/OTB 72` -> 72 (jumlah core)

Dengan `(?<!ODF/)`, hanya `OTB 1`, `OTB 2`, `OTB 3` (standalone) yang ditangkap.

### Hasil scanning menentukan `has_otb_numbers`

```python
if all_otb_nums:
    otb_min = all_otb_nums[0]   # terkecil
    otb_max = all_otb_nums[-1]  # terbesar
    first_otb = otb_min
    has_otb_numbers = True
else:
    # fallback dari filename
    otb_range_match = re.search(r'OTB\s+(\d+)-(\d+)', filename_upper)
    otb_single_match = re.search(r'OTB\s+(\d+)(?!\s*-)', filename_upper)
    if otb_range_match:
        otb_min = int(otb_range_match.group(1))
        otb_max = int(otb_range_match.group(2))
        has_otb_numbers = True
    elif otb_single_match:
        otb_min = int(otb_single_match.group(1))
        otb_max = otb_min
        has_otb_numbers = True
    else:
        # OTB tanpa nomor
        has_otb_numbers = False
```

---

## 4. Ekstrak Lokasi

### Strip OTB FO (dua varian!)

```python
after = re.sub(r'OTB\s+FO\s+\d+\s*', '', after)   # OTB FO 123
after = re.sub(r'OTB\s+FO\s+', '', after)           # OTB FO ER SINYAL BTT
after = re.sub(r'OTB\s+\d+\s*', '', after)          # OTB 1, OTB 5
after = re.sub(r'TRA\d+\s*:\s*', '', after)         # TRA11236 :
```

### Kenapa dua regex untuk OTB FO?

- `OTB FO 123` -> regex pertama (FO + digit) OK
- `OTB FO ER SINYAL BTT` -> regex kedua (FO + apapun) OK

Tanpa regex kedua, `OTB FO` tanpa angka lolos dan mencemari lokasi.

### Strip prefix ER

```python
after = re.sub(r'^ER\s+SINYAL\s+', '', after)
after = re.sub(r'^ER\s+RADIO\s+', '', after)
after = re.sub(r'^ER\s+TELKOM\s+', '', after)
after = re.sub(r'^ER\s+', '', after)
```

---

## 5. Filename Output

### OTB bernomor -> ada range/angka

| Input | Output |
|---|---|
| OTB 1 s/d OTB 10, ER SINYAL, BOO | `SERAT OPTIK OTB 1-10 ER SINYAL BOO.pdf` |
| OTB 5, ER TELKOM, COS | `SERAT OPTIK OTB 5 ER TELKOM COS.pdf` |
| OTB 6-12, ER, CIGOMBONG | `SERAT OPTIK OTB 6-12 ER CIGOMBONG.pdf` |

```python
if has_otb_numbers:
    if otb_min == otb_max:
        range_str = str(otb_min)
    else:
        range_str = f"{otb_min}-{otb_max}"
    identitas = f"SERAT OPTIK OTB {range_str} {er_type} {loc}"
else:
    identitas = f"SERAT OPTIK OTB {er_type} {loc}"
```

### OTB TANPA nomor -> tanpa range

| Input | Output |
|---|---|
| OTB ER SINYAL, BOO | `SERAT OPTIK OTB ER SINYAL BOO.pdf` |
| OTB ER SINYAL, BTT | `SERAT OPTIK OTB ER SINYAL BTT.pdf` |
| OTB ER TELKOM, MSG | `SERAT OPTIK OTB ER TELKOM MSG.pdf` |

---

## 6. Contoh Nyata (dari OCR debug)

### OTB ER SINYAL BTT — tanpa nomor
```
CZ | TRA11236 : OTB FO ER SINYAL BTT
...
Jumlah Core ... ODF/OTB 144    <- INI JUMLAH CORE, BUKAN NOMOR OTB!
```
Output: `SERAT OPTIK OTB ER SINYAL BTT.pdf`

### OTB ER TELKOM BTT — tanpa nomor
```
CZ | TRA10927 : OTB FO ER TELKOM BTT
...
Jumlah Core ... ODF/OTB 72     <- INI JUMLAH CORE!
```
Output: `SERAT OPTIK OTB ER TELKOM BTT.pdf`

### OTB 1-3 ER TELKOM CIGOMBONG — bernomor
```
CZ | TRAxxxxx : OTB 1 ER TELKOM CIGOMBONG
CZ | TRAxxxxx : OTB 2 ER TELKOM CIGOMBONG
CZ | TRAxxxxx : OTB 3 ER TELKOM CIGOMBONG
```
Output: `SERAT OPTIK OTB 1-3 ER TELKOM CIGOMBONG.pdf`

---

## 7. Gate B (filename-based fallback)

Saat `detect_doc()` tidak detect via OCR, Gate B (processing loop) membaca dari filename:

```python
if "ER SINYAL" in filename_upper:
    assets.append({"id": "ER SINYAL", "loc": loc})
elif "ER RADIO" in filename_upper:
    assets.append({"id": "ER RADIO", "loc": loc})
elif "ER TELKOM" in filename_upper:
    assets.append({"id": "ER TELKOM", "loc": loc})
elif "ER" in filename_upper and "SERAT OPTIK" in kategori:
    assets.append({"id": "ER", "loc": loc})
```

---

## 8. Koleksi & Grouping

### Tuple collection
```python
so_er_assets.append((
    kategori,          # "SERAT OPTIK"
    asset["id"],       # "ER SINYAL" / "ER RADIO" / "ER TELKOM" / "ER"
    asset["loc"],      # "BOO" / "BTT" / dll
    otb_min,           # minimum OTB number
    otb_max,           # maximum OTB number
    first_otb,         # untuk sort order
    has_otb_numbers,   # True/False flag
))
```

### Grouping unpack
```python
kategori, er_type, loc, otb_min, otb_max, first_otb, has_otb_numbers = first
```

### Sort by first_otb
```python
so_er_assets.sort(key=lambda x: x[5])  # sort by first_otb
```

---

## 9. Checkpoint: Hal yang PERNAH SALAH

| # | Bug | Root Cause | Fix |
|---|---|---|---|
| 1 | `OTB FO ER SINYAL BTT` -> lokasi double | Regex `OTB\s+FO\s+\d+` hanya match FO+digit | Tambah `OTB\s+FO\s+` (tanpa digit) |
| 2 | `RADIO` di filename -> `ER TELKOM` | `"TELKOM" or "RADIO"` selalu true | Deteksi terpisah per keyword |
| 3 | `OTB 1-144 ER SINYAL BTT` padahal tanpa nomor | `\bOTB\s+(\d+)\b` menangkap `ODF/OTB 144` | `(?<!ODF/)` negative lookbehind |
| 4 | `OTB 72 ER TELKOM BTT` padahal tanpa nomor | Sama seperti atas | Sama |

---

## 10. File yang Harus Selalu Disinkron

Setiap perubahan logic di SERAT OPTIK OTB HARUS disinkron ke **2 file**:

| File | Path |
|---|---|
| Detector (JS) | [detector.js](file:///c:/Users/dikarm/Documents/Server/ganti-nama-app/web-app/src/utils/detector.js) |
| Backend OCR (Python) | [run_desktop_webview.py](file:///c:/Users/dikarm/Documents/Server/ganti-nama-app/web-app/run_desktop_webview.py) |
