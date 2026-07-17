"""Show OCR of PTPP files"""
import sys, os, re
sys.path.insert(0, r'c:\Users\dikarm\Documents\Server\ganti-nama-app')
from pdf2image import convert_from_bytes
from PIL import ImageOps
import pytesseract

folders = [
    r"C:\Users\dikarm\Documents\Server\OCR-FOTO-P3STE\IMO\IMO 2025\1. JANUARI\BTP BD",
]

for folder in folders:
    for f in os.listdir(folder):
        if "TELEKOMUNIKASI DI PINTU PERLINTASAN" not in f.upper():
            continue
        filepath = os.path.join(folder, f)
        with open(filepath, 'rb') as fd:
            file_bytes = fd.read()
        images = convert_from_bytes(file_bytes, dpi=150, first_page=1, last_page=1)
        img = images[0].convert('L')
        img = ImageOps.autocontrast(img)
        width, height = img.size
        img_cropped = img.crop((0.0, 0.0, width * 1.0, height * 0.30))
        text = pytesseract.image_to_string(img_cropped, lang='ind+eng').upper()
        print(f"\n=== {f} ===")
        for i, l in enumerate(text.split('\n')):
            if 'JPL' in l.upper() or 'PINTU' in l.upper() or 'PERLINTASAN' in l.upper():
                print(f"  {i}: {l}")
