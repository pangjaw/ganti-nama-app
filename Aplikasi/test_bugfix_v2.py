"""Test: jalankan 5 PDF sample lewat app.py, print hasil asset+location."""
import sys, os, re

sys.path.insert(0, r"c:\Users\dikarm\Documents\Server\ganti-nama-app")
from app import process_pdf_ocr, detect_doc, build_filename

DIR = r"C:\Users\dikarm\Documents\Server\ganti-nama-app\FILE BUG"
SAMPLES = [
    "PERAWATAN SINYAL M314 CLT 23-01-2026.pdf",         # Bug 1: M314
    "PERAWATAN AXLE COUNTER ZP BOP 20-01-2026.pdf",     # Bug 2 & 6: ZP regex + lokasi
    "PERAWATAN PDSE CCR 06-01-2026.pdf",                # Bug 3: PDSE location
    "PERAWATAN PINTU PERLINTASAN JPL 27 BOO-CLT 26-01-2026.pdf",  # Bug 4: JPL 27
    "PERAWATAN PINTU PERLINTASAN JPL 28 BOO-CLT 26-01-2026.pdf",  # Bug 4: JPL 28
]

print("=" * 70)
print("TEST HASIL PERBAIKAN app.py — 5 FILE BUG")
print("=" * 70)

for fname in SAMPLES:
    fpath = os.path.join(DIR, fname)
    if not os.path.exists(fpath):
        print(f"\n  SKIP {fname}: file tidak ditemukan")
        continue

    name_only = fname.upper()
    tgl_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', name_only)
    tgl_full = tgl_match.group(0) if tgl_match else "01-01-2026"

    with open(fpath, "rb") as f:
        file_bytes = f.read()

    try:
        text_crop = process_pdf_ocr(file_bytes)
        text_flat = re.sub(r'\s+', ' ', text_crop)
        kode, kategori, assets = detect_doc(text_flat, text_crop, name_only)

        print(f"\n📄 {fname}")
        print(f"   Kode: {kode} | Kategori: {kategori}")
        if not assets:
            print(f"   ❌ TIDAK ADA ASET TERDETEKSI")
        else:
            for a in assets:
                aid = a["id"]
                loc = a["loc"]
                identitas = f"{kategori} {aid} {loc}".strip() if aid else f"{kategori} {loc}".strip()
                identitas = re.sub(r'\s+', ' ', identitas).strip()
                new_name = build_filename("2026-1", kode, "Perawatan", identitas, tgl_full, format_bd=False)
                new_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)
                status = "✅" if loc else "⚠️"
                print(f"   {status} Asset: {aid:<15} Lokasi: {loc:<15} → {new_name}")
    except Exception as e:
        print(f"\n📄 {fname}")
        print(f"   ❌ ERROR: {e}")

print("\n" + "=" * 70)
print("SELESAI")
