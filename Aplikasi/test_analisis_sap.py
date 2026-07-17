"""
Analisis perbandingan hasil OCR vs SAP 2026.
Fokus: jumlah file (bukan aset) per kategori vs SAP.
Item duplikat (mingguan) di-flatten jadi 1 per aset.
"""
import sys, os, re, json

OUTDIR = r"C:\Users\dikarm\Documents\Server\ganti-nama-app\FILE BUG\Januari 2026\SUDAH RENAME"
with open(os.path.join(OUTDIR, "_hasil_ocr_v2.json")) as f:
    data = json.load(f)

results = data["results"]

# SAP 2026 reference
SAP_2026 = {
    "WESEL":       {"total": 31, "BTP JAK": 20, "BOCI": 11},
    "PDSE":        {"total": 36, "BTP JAK": 16, "BOCI": 20},
    "SINYAL":      {"total": 125, "BTP JAK": 78, "BOCI": 47},
    "DETEKSI KA":  {"total": 139, "BTP JAK": 79, "BOCI": 60},
    "PINTU PERLINTASAN": {"total": 37, "BTP JAK": 17, "BOCI": 20},
    "CATU DAYA":   {"total": 27, "BTP JAK": 9, "BOCI": 18},
    "SERAT OPTIK": {"total": 86, "BTP JAK": 30, "BOCI": 56},
    "PTDS":        {"total": 31, "BTP JAK": 11, "BOCI": 20},
    "PTLS":        {"total": 10, "BTP JAK": 3, "BOCI": 7},
    "CTC-CTS":     {"total": 2, "BTP JAK": 2, "BOCI": 0},
    "WAYSTATION":  {"total": 9, "BTP JAK": 6, "BOCI": 3},
}

WILAYAH = {
    "BJD-CLT": "BTP JAK", "CLT": "BTP JAK", "CLT-BOO": "BTP JAK", "BOO": "BTP JAK",
    "BOO-CLT": "BTP JAK",
    "BOP": "BOCI", "BOP-BTT": "BOCI", "BTT": "BOCI", "COS": "BOCI",
    "MSG": "BOCI", "CGB": "BOCI", "CCR": "BOCI", "BTT-MSG": "BOCI",
    "CCR-MSG": "BOCI", "CCR-CGB-MSG": "BOCI", "MSG-CCR": "BOCI",
    "MSG-BTT": "BOCI", "BTT-BOP": "BOCI", "BOO-BOP": "BOCI",
    "BOO-BOP-BTT": "BOCI",
    "BJD": "BTP JAK", "BOJONGGEDE-CLT": "BTP JAK",
    "BOJONGGEDE": "BTP JAK",
}

# Hitung file UNIK per kategori per lokasi
from collections import Counter, defaultdict

# Kategori dari kode
CAT_FROM_KODE = {
    "BPBYE1": "WESEL", "BPBYE3": "SINYAL", "BPBYE2": "PDSE",
    "BPBYE7": "AXLE COUNTER", "BPBKS17": "PTPP",
    "BPBKF4": "SERAT OPTIK", "BPBYE14": "CATU DAYA",
    "BPBKS12": "PTDS", "BPBKS13": "PTLS", "BPBYE4": "CTC-CTS",
    "BPBKS5": "WAYSTATION", "BPBKS16": "WAYSTATION",
}

# File unik per kategori = berapa file berbeda yg diproses
file_cats = set()
for r in results:
    file_cats.add((r["file"], r["sap_cat"]))

cat_file_count = Counter()
for f, c in file_cats:
    cat_file_count[c] += 1

# Per lokasi: unique (kategori, lokasi) dari hasil
cat_loc = defaultdict(set)
cat_loc_wilayah = defaultdict(lambda: Counter())

for r in results:
    cat = r["sap_cat"]
    loc = r["loc"]
    cat_loc[cat].add(loc)
    if loc and loc in WILAYAH:
        w = WILAYAH[loc]
        cat_loc_wilayah[cat][w] += 1
    elif loc and loc.startswith("B"):
        # Fallback: cek apakah BOO atau BOP dll
        pass

# Flatten: unique (kategori, asset_id) per file
# Ini perkiraan jumlah aset UNIK (bukan per-file)
unique_assets_by_cat = defaultdict(set)
for r in results:
    key = (r["sap_cat"], r["asset"], r["loc"])
    unique_assets_by_cat[r["sap_cat"]].add((r["asset"], r["loc"]))

print("=" * 70)
print("PERBANDINGAN HASIL OCR v2 vs SAP 2026")
print("=" * 70)
print(f"\n442 file diproses, {len(results)} total aset terdeteksi")
print()

# Tabel utama
print(f"{'Kategori':<22} {'File':>5} {'Unik Aset':>10} {'SAP':>6} {'BTP JAK':>9} {'BOCI':>7} {'Match?':>8}")
print("-" * 75)
for cat in sorted(CAT_FROM_KODE.values()):
    if cat == "AXLE COUNTER":
        continue  # skip karena di file SUDAH RENAME bukan AXLE COUNTER murni (ZP)
    files_c = cat_file_count.get(cat, 0)
    sap = SAP_2026.get(cat, {})
    sap_total = sap.get("total", "?")
    btp = cat_loc_wilayah[cat].get("BTP JAK", 0)
    boci = cat_loc_wilayah[cat].get("BOCI", 0)
    unik = len(unique_assets_by_cat[cat])

    # Kira match: unik aset dekat dengan SAP
    if isinstance(sap_total, int) and sap_total > 0:
        diff = abs(unik - sap_total)
        if diff <= 5:
            match = "[OK]"
        elif diff <= 10:
            match = "[~]"
        else:
            match = "[XX]"
    else:
        match = "?"

    print(f"{cat:<22} {files_c:>5} {unik:>10} {str(sap_total):>6} {str(btp):>9} {str(boci):>7} {match:>8}")

# Axle counter separate
axc_count = cat_file_count.get("AXLE COUNTER", 0)
axc_unik = len(unique_assets_by_cat.get("AXLE COUNTER", set()))
print(f"\n{'AXLE COUNTER':<22} {axc_count:>5} {axc_unik:>10} {'N/A':>6} {'?':>9} {'?':>7} {'?':>8}")

print()
print("=" * 70)
print("ANALISIS")
print("=" * 70)

# Temuan
print("""
[NOTE]: Perbandingan ini <file per kategori> vs <SAP aset>.
   Karena 1 file bisa cover 1 aset (misal: Wesel W11), maka file count ~ aset count.
   Tapi untuk SINYAL dan AXC, 1 file bisa berisi banyak aset (B101, B102...).

[OK] SESUAI:
  - CTC-CTS: 2 -- cocok sempurna
  - CATU DAYA: 9 file, SAP 27 -- [XX] MISSING 18. Mungkin karena file CATU DAYA hanya yg di folder?
  - PDSE: 10 file, SAP 36 -- [XX] MISSING 26. Banyak yg belum terproses?

[~] PERLU CEK LOKASI:
  - SINYAL: lokasi "BOJONGGEDE-CLT" (41x) -- ini seharusnya BJD-CLT atau BOO-CLT
  - AXLE: "MSG-BTT" dan "BTT-BOP" -- format dual lokasi urutan terbalik?

[XX] DETEKSI HILANG:
  - PTPP: 1 file gagal (JPL 04 BOP)
  - PTDS/PTLS: cuma 7 file dari SAP 31/10 -- mungkin karena banyak file belum di-folder ini?
""")

# Detail per kategori
print("=" * 70)
print("DETAIL KATEGORI")
print("=" * 70)

for cat in sorted(cat_loc.keys()):
    if cat == "AXLE COUNTER":
        continue
    sap = SAP_2026.get(cat, {})
    print(f"\n  [{cat}]")
    print(f"     File: {cat_file_count.get(cat,0)} | Unik aset: {len(unique_assets_by_cat[cat])} | SAP: {sap.get('total','?')}")
    locs_here = sorted(cat_loc[cat])
    print(f"     Lokasi: {', '.join(locs_here)}")
    # Hitung unique asset per wilayah
    unik_wil = Counter()
    for (aid, loc) in unique_assets_by_cat[cat]:
        if loc in WILAYAH:
            unik_wil[WILAYAH[loc]] += 1
    for w in ["BTP JAK", "BOCI"]:
        ocr_w = unik_wil.get(w, 0)
        sap_w = sap.get(w, "?")
        status = "[OK]" if ocr_w == sap_w else "[~]"
        print(f"       {w}: OCR {ocr_w} vs SAP {sap_w} {status}")

print()
print("=" * 70)
print("FILE GAGAL: PERAWATAN PTPP JPL 04 BOP 11-01-2026.pdf")
print("=" * 70)
