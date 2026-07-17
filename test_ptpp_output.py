"""Test script: feed 8 PTPP PDFs through app.py pipeline, print output filenames."""
import sys, os, re

# Add project root
sys.path.insert(0, r"c:\Users\dikarm\Documents\Server\ganti-nama-app")
from app import process_pdf_ocr, detect_doc, build_filename, get_btp

TARGET_DIR = r"C:\Users\dikarm\Documents\Server\OCR-FOTO-P3STE\IMO\IMO 2025\1. JANUARI\BTP BD"
INSTANSI = "BTP JAK"
JENIS_KEGIATAN = "Perawatan"

# Filter: only TELEKOMUNIKASI DI PINTU PERLINTASAN files
files = sorted([
    f for f in os.listdir(TARGET_DIR)
    if f.endswith(".pdf") and "TELEKOMUNIKASI DI PINTU PERLINTASAN" in f.upper()
])

print(f"File PTPP ditemukan: {len(files)}\n")

for fname in files:
    fpath = os.path.join(TARGET_DIR, fname)
    name_only = fname.upper()

    tgl_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', name_only)
    if not tgl_match:
        print(f"  SKIP {fname}: no date")
        continue

    tgl_full = tgl_match.group(0)
    bln = str(int(tgl_match.group(2)))
    thn = tgl_match.group(3)
    prefix = f"{thn}-{bln}"

    with open(fpath, "rb") as f:
        file_bytes = f.read()

    try:
        text_crop = process_pdf_ocr(file_bytes)
        text_flat = re.sub(r'\s+', ' ', text_crop)
        kode, kategori, assets = detect_doc(text_flat, text_crop, name_only)

        if not assets:
            print(f"  {fname}")
            print(f"    -> GAGAL: tidak terdeteksi\n")
            continue

        for asset in assets:
            aid = asset["id"]
            loc = asset["loc"]
            identitas = f"{kategori} {aid} {loc}".strip() if aid else f"{kategori} {loc}".strip()
            identitas = re.sub(r'\s+', ' ', identitas).strip()
            new_name = build_filename(prefix, kode, JENIS_KEGIATAN, identitas, tgl_full, format_bd=False)
            new_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)
            print(f"  {fname}")
            print(f"    -> Kode     : {kode}")
            print(f"    -> Kategori : {kategori}")
            print(f"    -> Asset    : {aid}")
            print(f"    -> Lokasi   : {loc}")
            print(f"    -> OUTPUT   : {new_name}")
            print()

    except Exception as e:
        print(f"  {fname}")
        print(f"    -> ERROR: {e}\n")
