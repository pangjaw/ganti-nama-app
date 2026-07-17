"""
Batch process semua PDF di SUDAH RENAME lewat process_pdf_entries
(langsung pake dedup logic app.py), bandingin dengan SAP 2026.
"""
import sys, os, re, json
from collections import Counter, defaultdict

sys.path.insert(0, r"c:\Users\dikarm\Documents\Server\ganti-nama-app")
from app import process_pdf_ocr, detect_doc, process_pdf_entries, read_input_file, build_filename

SRC = r"C:\Users\dikarm\Documents\Server\ganti-nama-app\FILE BUG\Januari 2026\SUDAH RENAME"

# SAP 2026 reference — DATA ASET RESOR 2026.pdf
SAP_2026 = {
    "WESEL":            {"total": 31, "BTP JAK": 20, "BOCI": 11},
    "PDSE":             {"total": 7, "BTP JAK": 2, "BOCI": 5},
    "SINYAL":           {"total": 125, "BTP JAK": 78, "BOCI": 47},
    "DETEKSI KA":       {"total": 139, "BTP JAK": 79, "BOCI": 60},
    "PINTU PERLINTASAN": {"total": 10, "BTP JAK": 4, "BOCI": 6},
    "POINT LOCK":       {"total": 2, "BTP JAK": 1, "BOCI": 1},
    "CATU DAYA":        {"total": 9, "BTP JAK": 4, "BOCI": 5},
    "SERAT OPTIK":      {"total": 22, "BTP JAK": 8, "BOCI": 14},
    "PTDS":             {"total": 6, "BTP JAK": 2, "BOCI": 4},
    "PTLS":             {"total": 8, "BTP JAK": 2, "BOCI": 6},
    "PTPP (JPL)":       {"total": 11, "BTP JAK": 6, "BOCI": 5},
    "CTC-CTS":          {"total": 2, "BTP JAK": 2, "BOCI": 0},
    "WAYSTATION":       {"total": 0, "BTP JAK": 0, "BOCI": 0},  # tidak ada di DATA ASET RESOR 2026
}

# Kode ke kategori (sama kayak app.py mapping)
CAT_FROM_KODE = {
    "BPBYE1": "WESEL", "BPBYE3": "SINYAL", "BPBYE2": "PDSE",
    "BPBYE7": "AXLE COUNTER", "BPBKS17": "PTPP",
    "BPBKF4": "SERAT OPTIK", "BPBYE14": "CATU DAYA",
    "BPBKS12": "PTDS", "BPBKS13": "PTLS", "BPBYE4": "CTC-CTS",
    "BPBYE12": "POINT LOCK", "BPBKS16": "PTLS",
    "BPBKS5": "WAYSTATION", "BPBKF3": "WAYSTATION",
}

# Cari wilayah dari lokasi
WILAYAH_MAP = {
    "CLT": "BTP JAK", "CLT-BOO": "BTP JAK", "BOO": "BTP JAK",
    "BJD-CLT": "BTP JAK", "BOO-CLT": "BTP JAK",
    "BOO-BOP": "BOCI", "BOO-BOP-BTT": "BOCI", "BOP": "BOCI",
    "BOP-BTT": "BOCI", "BTT": "BOCI", "BTT-MSG": "BOCI",
    "BTT-BOP": "BOCI", "COS": "BOCI", "MSG": "BOCI",
    "MSG-CCR": "BOCI", "MSG-BTT": "BOCI", "CGB": "BOCI",
    "CCR": "BOCI", "CCR-MSG": "BOCI", "CCR-CGB-MSG": "BOCI",
}

def get_wilayah(loc):
    if not loc:
        return "?"
    for k, w in WILAYAH_MAP.items():
        if loc.startswith(k) or loc == k:
            return w
    # Fallback: cek BOCI dulu
    for boci in ["BOP", "BTT", "COS", "MSG", "CGB", "CCR"]:
        if boci in loc:
            return "BOCI"
    if "BOO" in loc or "CLT" in loc or "BJD" in loc:
        return "BTP JAK"
    return "?"

# Kumpulin semua file
files = sorted([f for f in os.listdir(SRC) if f.endswith('.pdf') and not f.startswith('~')])

# Process pake process_pdf_entries logic (tapi tanpa zip, kita trace)
from io import BytesIO
import zipfile

format_bd = False
zip_buffer = BytesIO()
processed_files = []  # list of (filename, kategori, lokasi, asset_id)
duplicate_errors = []
unique_filenames = set()

total_count = len(files)

print(f"Total file: {total_count}")
print()

for idx, fname in enumerate(files, 1):
    fpath = os.path.join(SRC, fname)
    name_only = fname.upper()

    tgl_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', name_only)
    if not tgl_match:
        duplicate_errors.append(f"{fname}: no date")
        continue

    tgl_full = tgl_match.group(0)
    bln_angka = str(int(tgl_match.group(2)))
    thn_angka = tgl_match.group(3)
    prefix_periode = f"{thn_angka}-{bln_angka}"

    try:
        with open(fpath, "rb") as f:
            file_bytes = f.read()

        text_crop = process_pdf_ocr(file_bytes)
        text_flat = re.sub(r'\s+', ' ', text_crop)
        kode, kategori, assets = detect_doc(text_flat, text_crop, name_only)

        if not assets:
            duplicate_errors.append(f"{fname}: no assets detected")
            continue

        for asset in assets:
            aid = asset["id"]
            loc = asset["loc"]
            identitas = f"{kategori} {aid} {loc}".strip() if aid else f"{kategori} {loc}".strip()
            identitas = re.sub(r'\s+', ' ', identitas).strip()
            new_name = build_filename(prefix_periode, kode, "Perawatan", identitas, tgl_full, format_bd)
            new_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)

            # Serat Optik: duplikat dapat suffix (2), dst
            if kategori == "SERAT OPTIK" and new_name in unique_filenames:
                counter = 2
                while True:
                    name_no_ext, ext = os.path.splitext(new_name)
                    candidate = f"{name_no_ext} ({counter}){ext}"
                    if candidate not in unique_filenames:
                        new_name = candidate
                        break
                    counter += 1

            if new_name not in unique_filenames:
                sap_cat = CAT_FROM_KODE.get(kode, kategori)
                processed_files.append({
                    "filename": new_name,
                    "kategori": kategori,
                    "sap_cat": sap_cat,
                    "loc": loc,
                    "asset": aid,
                })
                unique_filenames.add(new_name)
            else:
                duplicate_errors.append(f"{fname}: Dup ({new_name})")

    except Exception as e:
        duplicate_errors.append(f"{fname}: Error {e}")

    if idx % 50 == 0 or idx == total_count:
        print(f"  Progress: {idx}/{total_count} ({idx*100//total_count}%)")

print()
print("=" * 70)
print("HASIL PROCESSING — DEDUP SAMA KAYAK APP.PY")
print("=" * 70)

# Hitung unique file per kategori
cat_file_count = Counter()
cat_unique_aset = defaultdict(set)  # sap_cat -> set of (asset_id, loc)
cat_locs = defaultdict(set)

for pf in processed_files:
    cat = pf["sap_cat"]
    cat_file_count[cat] += 1
    cat_unique_aset[cat].add((pf["asset"], pf["loc"]))
    if pf["loc"]:
        cat_locs[cat].add(pf["loc"])

# Tabel utama
print(f"\n{'Kategori':<22} {'File':>6} {'Unik':>6} {'SAP':>6} {'BTP':>6} {'BOCI':>6} {'Match':>6}")
print("-" * 64)

total_ocr = 0
total_sap = 0

for cat in sorted(cat_file_count.keys()):
    if cat == "AXLE COUNTER":
        continue
    files_c = cat_file_count[cat]
    unik = len(cat_unique_aset[cat])
    sap = SAP_2026.get(cat, {})
    sap_total = sap.get("total", "?")
    
    # Wilayah dari unique assets
    wil_count = Counter()
    for (aid, loc) in cat_unique_aset[cat]:
        w = get_wilayah(loc)
        if w in ("BTP JAK", "BOCI"):
            wil_count[w] += 1
    btp = wil_count.get("BTP JAK", 0)
    boci = wil_count.get("BOCI", 0)

    if isinstance(sap_total, int) and sap_total > 0:
        diff = abs(unik - sap_total)
        if diff <= 3:
            match = "[OK]"
        elif diff <= 10:
            match = "[~]"
        else:
            match = "[XX]"
    else:
        match = "?"

    total_ocr += unik
    if isinstance(sap_total, int):
        total_sap += sap_total

    print(f"{cat:<22} {files_c:>6} {unik:>6} {str(sap_total):>6} {str(btp):>6} {str(boci):>6} {match:>6}")

# Axle counter
axc_count = cat_file_count.get("AXLE COUNTER", 0)
axc_unik = len(cat_unique_aset.get("AXLE COUNTER", set()))
print(f"{'AXLE COUNTER':<22} {axc_count:>6} {axc_unik:>6} {'N/A':>6} {'?':>6} {'?':>6} {'?':>6}")
print(f"\nTotal: {len(processed_files)} file output | {total_ocr} unique asset | SAP total matching: {total_sap}")

# Detail per kategori
print()
print("=" * 70)
print("DETAIL PER KATEGORI")
print("=" * 70)

for cat in sorted(cat_file_count.keys()):
    if cat == "AXLE COUNTER":
        continue
    sap = SAP_2026.get(cat, {})
    unik = len(cat_unique_aset[cat])
    print(f"\n[{cat}]")
    print(f"  File output: {cat_file_count[cat]} | Unique: {unik} | SAP: {sap.get('total','?')}")
    locs = sorted(cat_locs[cat])
    print(f"  Lokasi: {', '.join(locs) if locs else '-'}")
    wil_count = Counter()
    for (aid, loc) in cat_unique_aset[cat]:
        w = get_wilayah(loc)
        if w in ("BTP JAK", "BOCI"):
            wil_count[w] += 1
    for w in ["BTP JAK", "BOCI"]:
        ocr_w = wil_count.get(w, 0)
        sap_w = sap.get(w, "?")
        status = "[OK]" if ocr_w == sap_w else "[~]"
        print(f"    {w}: OCR {ocr_w} vs SAP {sap_w} {status}")

# Errors
if duplicate_errors:
    print()
    print("=" * 70)
    print(f"ERROR/DUPLICATE ({len(duplicate_errors)})")
    print("=" * 70)
    for e in duplicate_errors[:20]:
        print(f"  {e}")
    if len(duplicate_errors) > 20:
        print(f"  ... dan {len(duplicate_errors)-20} lainnya")

# Save
outpath = os.path.join(SRC, "_hasil_dedup.json")
with open(outpath, "w") as f:
    json.dump({
        "processed": processed_files,
        "errors": duplicate_errors,
        "cat_count": dict(cat_file_count),
        "total_files": len(processed_files),
        "total_unique": total_ocr,
    }, f, indent=2)
print(f"\nDetail: {outpath}")
print("SELESAI")
