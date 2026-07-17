"""Test PTPP detection for BNR with dual locations"""
import sys, os, re
sys.path.insert(0, r'c:\Users\dikarm\Documents\Server\ganti-nama-app')
from app import detect_doc

folders = [
    r"C:\Users\dikarm\Documents\Server\OCR-FOTO-P3STE\IMO\IMO 2025\1. JANUARI\BTP BD",
    r"C:\Users\dikarm\Documents\Server\OCR-FOTO-P3STE\IMO\IMO 2025\1. JANUARI\BTP JAK",
]

print("=== Test PTPP files ===\n")
for folder in folders:
    if not os.path.exists(folder):
        continue
    print(f"Folder: {os.path.basename(folder)}")
    for f in os.listdir(folder):
        if "TELEKOMUNIKASI DI PINTU PERLINTASAN" not in f.upper():
            continue
        filepath = os.path.join(folder, f)
        try:
            from pdf2image import convert_from_bytes
            from PIL import ImageOps
            import pytesseract
            
            with open(filepath, 'rb') as fd:
                file_bytes = fd.read()
            
            images = convert_from_bytes(file_bytes, dpi=150, first_page=1, last_page=1)
            img = images[0].convert('L')
            img = ImageOps.autocontrast(img)
            width, height = img.size
            img_cropped = img.crop((0.0, 0.0, width * 1.0, height * 0.30))
            text_crop = pytesseract.image_to_string(img_cropped, lang='ind+eng').upper()
            text_flat = re.sub(r'\s+', ' ', text_crop)
            
            kode, kategori, assets = detect_doc(text_flat, text_crop, f.upper())
            
            if kategori == "PTPP" and assets:
                for asset in assets:
                    print(f"  {f} -> {asset}")
        except Exception as e:
            print(f"  {f}: Error {e}")
