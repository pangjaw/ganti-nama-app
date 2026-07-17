"""Diagnostic: OCR JPL 02, 15, 16 files to verify location."""
import sys, os, re
sys.path.insert(0, r"c:\Users\dikarm\Documents\Server\ganti-nama-app")
from app import process_pdf_ocr, detect_doc

TARGET_DIR = r"C:\Users\dikarm\Documents\Server\OCR-FOTO-P3STE\IMO\IMO 2025\1. JANUARI\BTP BD"

files = [
    "25-01-2025_PERAWATAN PERALATAN TELEKOMUNIKASI DI PINTU PERLINTASAN 1 BULANAN_Bogor-Batutulis.pdf",
    "30-01-2025_PERAWATAN PERALATAN TELEKOMUNIKASI DI PINTU PERLINTASAN 1 BULANAN_Cigombong-Cicurug.pdf",
    "30-01-2025_PERAWATAN PERALATAN TELEKOMUNIKASI DI PINTU PERLINTASAN 1 BULANAN_Cigombong-Cicurug (2).pdf",
]

for fname in files:
    fpath = os.path.join(TARGET_DIR, fname)
    print("=" * 80)
    print(f"FILE: {fname}")
    print("=" * 80)
    with open(fpath, "rb") as f:
        file_bytes = f.read()
    text_crop = process_pdf_ocr(file_bytes)
    text_flat = re.sub(r'\s+', ' ', text_crop)
    
    print("--- OCR TEXT (top 30%) ---")
    print(text_crop)
    print("\n--- DETECT_DOC RESULT ---")
    kode, kategori, assets = detect_doc(text_flat, text_crop, fname.upper())
    for a in assets:
        print(f"  id={a['id']}, loc={a['loc']}")
    print()
