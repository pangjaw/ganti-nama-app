"""
Bandingkan hasil dedup OCR vs DATA ASET RESOR 2026.
"""
import sys, os, re, json
from collections import Counter, defaultdict

SRC = r"C:\Users\dikarm\Documents\Server\ganti-nama-app\FILE BUG\Januari 2026\SUDAH RENAME"
with open(os.path.join(SRC, "_hasil_dedup.json")) as f:
    data = json.load(f)

processed = data["processed"]

# =====================================================================
# DATA ASET RESOR 2026 — PDF "DATA ASET RESOR 2026.pdf"
# Per-kategori: (total_aset_unik, target_file_per_bulan, dict_stasiun)
# Kolom lokasi: Bjd-Clt, Clt, Clt-Boo, Boo, Bop, Bop-Btt, Btt, Cos, Msg, Cgb
# =====================================================================

KATEGORI = {
    "WESEL": {
        "total": 31, "target": 62,
        "per_stasiun": {"CLT": 4, "BOO": 16, "BOP": 7, "MSG": 4}
    },
    "PDSE": {
        "total": 7, "target": 7,
        "per_stasiun": {"CLT": 1, "BOO": 1, "BOP": 1, "BTT": 1, "COS": 1, "MSG": 1, "CGB": 1}
    },
    "SINYAL": {
        "total": 125, "target": 125,
        "per_stasiun": {"BJD-CLT": 9, "CLT": 9, "CLT-BOO": 40, "BOO": 20, "BOP": 14, "BTT": 12, "COS": 4, "MSG": 13, "CGB": 4}
    },
    "DETEKSI KA": {
        "total": 139, "target": 139,
        "per_stasiun": {"BJD-CLT": 5, "CLT": 14, "CLT-BOO": 25, "BOO": 35, "BOP": 22, "BTT": 12, "COS": 4, "MSG": 18, "CGB": 4}
    },
    "PINTU PERLINTASAN": {
        "total": 10, "target": 10,
        "per_stasiun": {"CLT": 1, "CLT-BOO": 2, "BOO": 1, "BOP": 1, "BOP-BTT": 2, "BTT": 1, "CGB": 2}
    },
    "POINT LOCK": {
        "total": 2, "target": 2,
        "per_stasiun": {"BOO": 1, "CGB": 1}  # Dari PDF: Boo=1, Cgb=1
    },
    "CTS/TSC": {
        "total": 2, "target": 2,
        "per_stasiun": {"CLT": 1, "BOO": 1}
    },
    "CATU DAYA": {
        "total": 9, "target": 9,
        "per_stasiun": {"CLT": 1, "BOO": 2, "BOP": 1, "BTT": 1, "COS": 2, "MSG": 1, "CGB": 1}
    },
    "PTDS": {  # Telkom di Stasiun
        "total": 6, "target": 6,
        "per_stasiun": {"CLT": 1, "BOO": 1, "BOP": 1, "BTT": 1, "MSG": 1, "CGB": 1}
    },
    "PTLS": {  # Telkom di luar Stasiun
        "total": 8, "target": 3,
        "per_stasiun": {"BOO": 2, "BOP": 1, "BTT": 1, "COS": 1, "MSG": 2, "CGB": 1}
    },
    "SERAT OPTIK": {  # Optik (OTB)
        "total": 22, "target": 22,
        "per_stasiun": {"CLT": 2, "CLT-BOO": 2, "BOO": 4, "BOP": 1, "BOP-BTT": 2, "BTT": 3, "COS": 2, "MSG": 2, "CGB": 4}
    },
    "PTPP (JPL)": {  # Telkom Pintu Perlintasan
        "total": 11, "target": 11,
        "per_stasiun": {"BJD-CLT": 1, "CLT": 2, "CLT-BOO": 2, "BOO": 1, "BOP": 2, "BOP-BTT": 1, "BTT": 2}
    },
}

CAT_MAP = {
    "WESEL":          "WESEL",
    "SINYAL":         "SINYAL",
    "PDSE":           "PDSE",
    "AXLE COUNTER":   "DETEKSI KA",
    "CATU DAYA":      "CATU DAYA",
    "CTC-CTS":        "CTS/TSC",
    "PTDS":           "PTDS",
    "PTLS":           "PTLS",
    "SERAT OPTIK":    "SERAT OPTIK",
    "PTPP":           "PTPP (JPL)",
}

# Normalisasi lokasi
LOC_ALIAS = {
    "BOJONGGEDE-CLT": "BJD-CLT",
    "BOO-CLT": "CLT-BOO",
}

# Kumpulin unique aset per kategori + lokasi
cat_loc_aset = defaultdict(lambda: defaultdict(set))
cat_loc_file = defaultdict(lambda: defaultdict(set))

for pf in processed:
    ocr_cat = pf["sap_cat"]
    sap_cat = CAT_MAP.get(ocr_cat, ocr_cat)
    if sap_cat not in KATEGORI:
        continue
    loc = pf["loc"]
    norm_loc = LOC_ALIAS.get(loc, loc)
    aid = pf["asset"]
    cat_loc_aset[sap_cat][norm_loc].add(aid)
    cat_loc_file[sap_cat][norm_loc].add(pf["filename"])

print("=" * 100)
print("PERBANDINGAN OCR (SUDAH RENAME) vs DATA ASET RESOR 2026")
print("Bulan: Januari 2026")
print("=" * 100)
print(f"{'KATEGORI':<25} {'FILE OCR':>8} {'TARGET':>7} {'ASET OCR':>8} {'ASET SAP':>8} {'SELISIH':>8} {'STATUS'}")
print("-" * 100)

total_file_ocr = 0
total_target = 0
total_aset_ocr = 0
total_aset_sap = 0

for sap_cat in sorted(KATEGORI.keys()):
    info = KATEGORI[sap_cat]
    target_n = info["target"]
    aset_sap = info["total"]
    sap_locs = info["per_stasiun"]
    ocr_locs = cat_loc_aset.get(sap_cat, {})
    
    # Count unique files (output filenames) and unique assets
    file_set = set()
    for loc, fnames in cat_loc_file.get(sap_cat, {}).items():
        file_set.update(fnames)
    file_n = len(file_set)
    
    aset_n = sum(len(ocr_locs.get(l, set())) for l in set(list(sap_locs.keys()) + list(ocr_locs.keys())))
    
    diff = file_n - target_n
    
    if file_n == target_n:
        status = "OK"
    elif abs(diff) <= 3:
        status = "~"
    elif diff > 0:
        status = f"EXTRA {diff}"
    else:
        status = f"KURANG {abs(diff)}"
    
    total_file_ocr += file_n
    total_target += target_n
    total_aset_ocr += aset_n
    total_aset_sap += aset_sap
    
    print(f"{sap_cat:<25} {file_n:>8} {target_n:>7} {aset_n:>8} {aset_sap:>8} {diff:>+8} {status}")

print("-" * 100)
print(f"{'TOTAL':<25} {total_file_ocr:>8} {total_target:>7} {total_aset_ocr:>8} {total_aset_sap:>8} {total_file_ocr-total_target:>+8}")

# =====================================================================
# DETAIL PER LOKASI
# =====================================================================
print()
print("=" * 100)
print("DETAIL PER KATEGORI & STASIUN")
print("=" * 100)

grand_missing = 0
grand_extra = 0

for sap_cat in sorted(KATEGORI.keys()):
    info = KATEGORI[sap_cat]
    sap_locs = info["per_stasiun"]
    ocr_locs = cat_loc_aset.get(sap_cat, {})
    file_locs = cat_loc_file.get(sap_cat, {})
    
    target = info["target"]
    file_n = sum(len(v) for v in file_locs.values())
    aset_n = sum(len(ocr_locs.get(l, set())) for l in set(list(sap_locs.keys()) + list(ocr_locs.keys())))
    
    print(f"\n{sap_cat} — FILE: {file_n}/{target} ASET: {aset_n}/{info['total']}")
    
    all_locs = set(list(sap_locs.keys()) + list(ocr_locs.keys()))
    
    for loc in sorted(all_locs):
        sap_aset = sap_locs.get(loc, 0)
        ocr_aset = ocr_locs.get(loc, set())
        ocr_n = len(ocr_aset)
        ocr_file_n = len(file_locs.get(loc, set()))
        
        # Expected files at this location = proportional to asset count
        if sap_aset > 0 and info["total"] > 0:
            expected_files = round(target * sap_aset / info["total"])
        else:
            expected_files = 0
        
        if ocr_n == 0 and sap_aset > 0:
            print(f"  [XX] {loc:15}: aset: OCR 0/SAP {sap_aset} — MISSING SEMUA")
            grand_missing += sap_aset
        elif ocr_n < sap_aset:
            print(f"  [XX] {loc:15}: aset: OCR {ocr_n}/SAP {sap_aset} — KURANG {sap_aset - ocr_n}")
            grand_missing += sap_aset - ocr_n
        elif ocr_n > sap_aset:
            extra = sorted(ocr_aset)
            print(f"  [!]  {loc:15}: aset: OCR {ocr_n}/SAP {sap_aset} — EXTRA {ocr_n - sap_aset}")
            if len(extra) <= 5:
                print(f"       EXTRA: {', '.join(extra)}")
            else:
                print(f"       EXTRA: {', '.join(extra[:5])}... ({len(extra)} total)")
            grand_extra += ocr_n - sap_aset
        else:
            print(f"  [OK] {loc:15}: aset OCR {ocr_n} = SAP {sap_aset}")
    
    # Extra locations not in SAP
    for loc in sorted(ocr_locs.keys()):
        if loc not in sap_locs:
            extra = sorted(ocr_locs[loc])
            print(f"  [!]  {loc:15}: LOKASI TIDAK DI SAP — {len(extra)} aset")
            print(f"       ASET: {', '.join(extra[:5])}{'...' if len(extra) > 5 else ''}")
            grand_extra += len(extra)

print()
print("=" * 100)
print("RINGKASAN FINAL")
print("=" * 100)
print(f"  Total SAP target file: {total_target}")
print(f"  Total OCR file output: {total_file_ocr}")
print(f"  Selisih file:          {total_file_ocr - total_target:+d}")
print(f"  Total SAP aset unik:   {total_aset_sap}")
print(f"  Total OCR aset unik:   {total_aset_ocr}")
print(f"  Selisih aset:          {total_aset_ocr - total_aset_sap:+d}")
print(f"  Total aset MISSING:    {grand_missing}")
print(f"  Total aset EXTRA:      {grand_extra}")
