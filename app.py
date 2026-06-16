#!/usr/bin/env python3
"""
DIKO Batch Processor - Jalankan OCR processing langsung tanpa Streamlit UI
Menggunakan logic yang sama dengan app.py
"""

import os, re, zipfile, gc, shutil, platform
from pathlib import Path
from io import BytesIO

# Setup tesseract
import pytesseract
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

from pdf2image import convert_from_bytes
from PIL import ImageOps

# =============================================
# CONFIG
# =============================================
SOURCE_FOLDER = r"C:\Users\SINTEL 1.21 BOO\Downloads\6. JUNI"
OUTPUT_BASE   = r"C:\Users\SINTEL 1.21 BOO\Downloads\6. JUNI\hasil download"

# Lokasi → BTP routing
BTP_JAK_LOCS = ["BOO", "CLT"]  # Bogor, Cilebut
BTP_BD_LOCS  = ["BOP", "BTT", "COS", "MSG", "CGB"]  # Bogorpaledang, Batutulis, dll

# Asset type → folder name
ASSET_FOLDERS = {
    "WESEL": "Wesel",
    "PDSE": "PDSE",
    "SERAT OPTIK": "Serat Optik",
    "PTPP": "PTPP",
    "PINTU PERLINTASAN": "Pintu Perlintasan",
    "PTDS": "PTDS",
    "PTLS": "PTLS",
    "CATU DAYA": "Catu Daya",
    "AXLE COUNTER": "Axle Counter",
    "PERAGA SINYAL": "Peraga Sinyal Elektrik",
}

def process_pdf_ocr(file_bytes):
    images = convert_from_bytes(file_bytes, dpi=150, first_page=1, last_page=1)
    img = images[0].convert('L')
    img = ImageOps.autocontrast(img)
    width, height = img.size
    img_cropped = img.crop((0.0, 0.0, width * 1.0, height * 0.30))
    text_crop = pytesseract.image_to_string(img_cropped).upper()
    del img, images
    gc.collect()
    return text_crop

def detect_doc(text_crop, filename_upper):
    text_flat = text_crop.replace('\n', ' ')
    kode = ""
    kategori = ""
    assets = []

    # GERBANG A: OCR-based detection (same order as app.py)
    if any(x in text_flat for x in ["POINT LOCK", "PENGAMAN WESEL"]):
        kode, kategori = "BPBYE1", "WESEL"
        # Improved regex: allow letters after W code (W23A, W61A1)
        w_match = re.search(r'(W\d+[A-Z]*)', text_flat)
        aid = w_match.group(1) if w_match else "W_UNKNOWN"
        if "CILEBUT" in text_flat:
            loc = "CLT"
        elif "BOGOR" in text_flat:
            loc = "BOO"
        else:
            loc = "LOKASI"
        assets.append({"id": aid, "loc": loc})

    elif "PERAWATAN WESEL" in text_flat or "PENGGERAK WESEL" in text_flat:
        # Fallback: detect wesel from "PENGGERAK WESEL W##" pattern
        kode, kategori = "BPBYE1", "WESEL"
        w_matches = re.findall(r'PENGGERAK\s+WESEL\s+(W\d+[A-Z]*)', text_flat)
        if w_matches:
            aid = w_matches[0]
        else:
            w_match = re.search(r'(W\d+[A-Z]*)', text_flat)
            aid = w_match.group(1) if w_match else "W_UNKNOWN"
        # Determine BTP based on location keyword in OCR text
        if "CILEBUT" in text_flat:
            loc = "CLT"
        elif "BOGOR" in text_flat:
            loc = "BOO"
        else:
            loc = "LOKASI"
        assets.append({"id": aid, "loc": loc})

    elif "PERALATAN DALAM PERSINYALAN ELEKTRIK" in text_flat:
        kode, kategori = "BPBYE2", "PDSE"
        if "BOGORPALEDANG" in text_flat or "PALEDANG" in text_flat: loc = "BOP"
        elif "CILEBUT" in text_flat: loc = "CLT"
        elif "BATUTULIS" in text_flat: loc = "BTT"
        elif "BOGOR" in text_flat: loc = "BOO"
        else: loc = "LOKASI"
        assets.append({"id": "", "loc": loc})

    elif "SERAT OPTIK" in text_flat and "JPL" in text_flat:
        kode, kategori = "BPBKF4", "SERAT OPTIK"
        lines = [l.strip() for l in text_crop.split('\n') if l.strip()]
        noise = ["PERAWATAN","PEMERIKSAAN","MINGGUAN","BULANAN","TAHUNAN","SERAT","OPTIK"]
        for line in lines:
            if "JPL" in line and ("OTB" in line or "FO" in line):
                clean = line.split(":")[-1].strip() if ":" in line else line.strip()
                words = clean.replace(".", " ").split()
                final = [w for w in words if w not in noise]
                if final and "JPL" in final:
                    jpl_idx = final.index("JPL")
                    if jpl_idx + 1 < len(final):
                        aid = f"JPL {final[jpl_idx+1]}"
                        loc = " ".join(final[jpl_idx+2:]) if jpl_idx+2 < len(final) else "LOKASI"
                        assets.append({"id": aid, "loc": loc})

    elif "TELEKOMUNIKASI DI PINTU PERLINTASAN" in text_flat:
        kode, kategori = "BPBKS17", "PTPP"
        # Remove system codes (JPL10506, JPL10498, etc.) to avoid false matches
        text_clean = re.sub(r'\bJPL\d+\b', '', text_flat)
        
        # Try to match JPL with number first (e.g., "JPL ELEKTRIK NO 04 BOP")
        jpl_match = re.search(r'JPL\s+(?:ELEKTRIK\s+)?(?:NO[.\s]*)?(\d+)', text_clean)
        if jpl_match:
            aid = f"JPL {jpl_match.group(1).strip()}"
            after_jpl = text_clean[jpl_match.end():].strip()
            for noise in ["DISETUJUL", "DIKETAHUI", "OLEH", "TANGGAL", "LOKASI", "PERIODE", "DILAKSANAKAN"]:
                if noise in after_jpl:
                    after_jpl = after_jpl.split(noise)[0].strip()
            loc = re.sub(r'\s+', ' ', after_jpl).strip()
        else:
            # Fallback: JPL without number (e.g., "JPL BNR BOP-BTT")
            jpl_word_match = re.search(r'\bJPL\s+([A-Z]+)\b', text_clean)
            if jpl_word_match:
                word = jpl_word_match.group(1).strip()
                aid = f"JPL {word}"
                after_jpl = text_clean[jpl_word_match.end():].strip()
                for noise in ["DISETUJUL", "DIKETAHUI", "OLEH", "TANGGAL", "LOKASI", "PERIODE", "DILAKSANAKAN"]:
                    if noise in after_jpl:
                        after_jpl = after_jpl.split(noise)[0].strip()
                loc = re.sub(r'\s+', ' ', after_jpl).strip()
            else:
                aid, loc = "JPL", ""
        assets.append({"id": aid, "loc": loc})

    elif "PINTU PERLINTASAN" in text_flat and "TELEKOMUNIKASI" not in text_flat:
        kode, kategori = "BPBKS17", "PINTU PERLINTASAN"
        # Try to match JPL with number first
        jpl_match = re.search(r'JPL\s+(?:ELEKTRIK\s+)?(?:NO[.\s]*)?(\d+)', text_flat)
        if jpl_match:
            aid = f"JPL {jpl_match.group(1).strip()}"
            # Extract location: text after JPL number, stop at noise keywords
            after_jpl = text_flat[jpl_match.end():].strip()
            for noise in ["DISETUJUL", "DIKETAHUI", "OLEH", "TANGGAL", "LOKASI", "PERIODE", "DILAKSANAKAN"]:
                if noise in after_jpl:
                    after_jpl = after_jpl.split(noise)[0].strip()
            loc = re.sub(r'\s+', ' ', after_jpl).strip()
        else:
            # Fallback: JPL without number (e.g., "JPL BNR BOP-BTT")
            jpl_fallback = re.search(r'JPL\s+([A-Z]+(?:\s+[A-Z\-]+)*)', text_flat)
            if jpl_fallback:
                aid = "JPL"
                after_jpl = text_flat[jpl_fallback.end():].strip()
                for noise in ["DISETUJUL", "DIKETAHUI", "OLEH", "TANGGAL", "LOKASI", "PERIODE", "DILAKSANAKAN"]:
                    if noise in after_jpl:
                        after_jpl = after_jpl.split(noise)[0].strip()
                loc = re.sub(r'\s+', ' ', after_jpl).strip()
            else:
                aid, loc = "JPL", ""
        assets.append({"id": aid, "loc": loc})

    elif "TELEKOMUNIKASI DI STASIUN" in text_flat:
        kode, kategori = "BPBKS15", "PTDS"
        if "BOGORPALEDANG" in text_flat or "PALEDANG" in text_flat: loc = "BOP"
        elif "CILEBUT" in text_flat: loc = "CLT"
        elif "BATUTULIS" in text_flat: loc = "BTT"
        elif "BOGOR" in text_flat: loc = "BOO"
        else: loc = "LOKASI"
        assets.append({"id": "", "loc": loc})

    elif "TELEKOMUNIKASI DI LUAR STASIUN" in text_flat:
        kode, kategori = "BPBKS16", "PTLS"
        if "BOGORPALEDANG" in text_flat or "PALEDANG" in text_flat: loc = "BOP"
        elif "CILEBUT" in text_flat: loc = "CLT"
        elif "BATUTULIS" in text_flat: loc = "BTT"
        elif "BOGOR" in text_flat: loc = "BOO"
        else: loc = "LOKASI"
        assets.append({"id": "", "loc": loc})

    elif "CATU DAYA" in text_flat:
        kode, kategori = "BPBYE14", "CATU DAYA"
        if "BOGORPALEDANG" in text_flat or "PALEDANG" in text_flat: loc = "BOP"
        elif "CILEBUT" in text_flat: loc = "CLT"
        elif "BATUTULIS" in text_flat: loc = "BTT"
        elif "BOGOR" in text_flat: loc = "BOO"
        else: loc = "LOKASI"
        assets.append({"id": "", "loc": loc})

    # GERBANG B: filename-based detection
    if not assets:
        if "WESEL ELEKTRIK" in filename_upper:
            kode, kategori = "BPBYE1", "WESEL"
            w_match = re.search(r'(W\d+[A-Z]*)', filename_upper)
            aid = w_match.group(1) if w_match else "W_UNKNOWN"
            if "BOGORPALEDANG" in filename_upper: loc = "BOP"
            elif "CILEBUT" in filename_upper: loc = "CLT"
            elif "BOGOR" in filename_upper: loc = "BOO"
            else: loc = "LOKASI"
            assets.append({"id": aid, "loc": loc})

        elif "POINT LOCK" in filename_upper:
            kode, kategori = "BPBYE7", "WESEL"
            if "BOGORPALEDANG" in filename_upper: loc = "BOP"
            elif "CILEBUT" in filename_upper: loc = "CLT"
            elif "BOGOR" in filename_upper: loc = "BOO"
            else: loc = "LOKASI"
            assets.append({"id": "PL", "loc": loc})

        elif "AXLE COUNTER" in filename_upper:
            kode, kategori = "BPBYE7", "AXLE COUNTER"
            if "BOGORPALEDANG" in filename_upper: loc = "BOP"
            elif "CILEBUT" in filename_upper: loc = "CLT"
            elif "BOGOR" in filename_upper: loc = "BOO"
            else: loc = "LOKASI"
            assets.append({"id": "ZP", "loc": loc})

        elif "PERAGA SINYAL" in filename_upper:
            kode, kategori = "BPBYE3", "PERAGA SINYAL"
            if "BOGORPALEDANG" in filename_upper: loc = "BOP"
            elif "CILEBUT" in filename_upper: loc = "CLT"
            elif "BOGOR" in filename_upper: loc = "BOO"
            else: loc = "LOKASI"
            assets.append({"id": "", "loc": loc})

        elif "SERAT OPTIK" in filename_upper:
            kode, kategori = "BPBKF4", "SERAT OPTIK"
            if "BOGORPALEDANG" in filename_upper: loc = "BOP"
            elif "CILEBUT" in filename_upper: loc = "CLT"
            elif "BOGOR" in filename_upper: loc = "BOO"
            else: loc = "LOKASI"
            assets.append({"id": "", "loc": loc})

    return kode, kategori, assets


def get_btp(loc):
    if loc in BTP_JAK_LOCS:
        return "BTP JAK"
    return "BTP BD"


def build_filename(prefix_periode, kode, jenis, identitas, tgl_full, format_bd):
    if format_bd:
        # BTP BD: 2026-6_Resor 1.21 Boo_BPBKS17_Perawatan_PTPP JPL 04 BOP_12-06-2026.pdf
        resor = "Resor 1.21 Boo"
        return f"{prefix_periode}_{resor}_{kode}_{jenis}_{identitas}_{tgl_full}.pdf"
    else:
        # BTP JAK: PERAWATAN WESEL W23B BOO 01-06-2026.pdf (no kode, no prefix_periode)
        return f"{jenis.upper()} {identitas} {tgl_full}.pdf"


def main():
    print("🤖 DIKO Batch Processor v1.0")
    print("="*60)

    # Get all PDF files from source folder
    pdf_files = [f for f in Path(SOURCE_FOLDER).glob("*.pdf")]
    print(f"📂 Found {len(pdf_files)} PDF files to process\n")

    results = {"BTP JAK": [], "BTP BD": []}
    errors = []
    unique_filenames = set()

    for idx, pdf_path in enumerate(sorted(pdf_files)):
        fname = pdf_path.name
        fname_upper = fname.upper()
        print(f"📄 [{idx+1}/{len(pdf_files)}] {fname}")

        # Extract date from filename
        tgl_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', fname)
        if not tgl_match:
            print(f"   ❌ Tanggal tidak ditemukan, skip\n")
            errors.append(f"❌ {fname}: format tanggal tidak ditemukan")
            continue

        tgl_full = tgl_match.group(0)
        bln_angka = str(int(tgl_match.group(2)))
        thn_angka = tgl_match.group(3)
        prefix_periode = f"{thn_angka}-{bln_angka}"

        # OCR
        try:
            file_bytes = pdf_path.read_bytes()
            text_crop = process_pdf_ocr(file_bytes)
        except Exception as e:
            print(f"   ❌ OCR error: {e}\n")
            errors.append(f"❌ {fname}: OCR error - {e}")
            continue

        # Detect doc type
        kode, kategori, assets = detect_doc(text_crop, fname_upper)

        if not assets:
            print(f"   ❌ Tidak terdeteksi, skip\n")
            errors.append(f"❌ {fname}: jenis dokumen tidak terdeteksi")
            continue

        # Process each asset
        for asset in assets:
            aid = asset["id"]
            loc = asset["loc"]
            btp = get_btp(loc)
            format_bd = (btp == "BTP BD")

            # Build identitas
            identitas = f"{kategori} {aid} {loc}".strip() if aid else f"{kategori} {loc}".strip()
            identitas = re.sub(r'\s+', ' ', identitas).strip()

            # Build new filename
            new_name = build_filename(prefix_periode, kode, "Perawatan", identitas, tgl_full, format_bd)
            new_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)

            if new_name in unique_filenames:
                print(f"   ⚠️  Duplikat: {new_name}, skip")
                continue

            unique_filenames.add(new_name)

            # Get asset folder name
            asset_folder = ASSET_FOLDERS.get(kategori, kategori)

            results[btp].append({
                "src": pdf_path,
                "new_name": new_name,
                "asset_folder": asset_folder,
                "btp": btp,
                "kode": kode,
                "kategori": kategori,
                "loc": loc
            })

            print(f"   ✅ {btp} | {kategori} | {new_name}")

        print()

    # Save results to output folders
    print("="*60)
    print("📁 Saving files to output folders...")
    print("="*60)

    total_saved = 0
    for btp, files in results.items():
        for item in files:
            dest_dir = Path(OUTPUT_BASE) / btp / item["asset_folder"]
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / item["new_name"]

            if dest_path.exists():
                print(f"   ⚠️  Already exists: {item['new_name']}")
                continue

            shutil.copy2(item["src"], dest_path)
            print(f"   ✅ {item['btp']}/{item['asset_folder']}/{item['new_name']}")
            total_saved += 1

    print()
    print("="*60)
    print(f"✅ Done! {total_saved} files processed and saved")
    print(f"📁 Output: {OUTPUT_BASE}")

    if errors:
        print(f"\n⚠️  {len(errors)} errors:")
        for e in errors:
            print(f"   {e}")

    print("="*60)


if __name__ == "__main__":
    main()
