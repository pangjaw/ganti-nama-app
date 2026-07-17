"""
Batch process via app.py logic (same duplicate handler as Flask endpoint).
"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import process_pdf_ocr, detect_doc, build_filename

SRC = r"C:\Users\dikarm\Documents\Server\ganti-nama-app\FILE BUG\Januari 2026\SUDAH RENAME"

files = sorted([f for f in os.listdir(SRC) if f.endswith('.pdf') and not f.startswith('~')])
total = len(files)
print(f"Total files: {total}")

processed_files = []
duplicate_errors = []
unique_filenames = set()

for idx, fname in enumerate(files, 1):
    fpath = os.path.join(SRC, fname)
    name_only = fname.upper()

    tgl_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', name_only)
    if not tgl_match:
        duplicate_errors.append(f"ERROR|{fname}|No date")
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
            duplicate_errors.append(f"ERROR|{fname}|No assets detected")
            continue

        for asset in assets:
            aid = asset["id"]
            loc = asset["loc"]
            identitas = f"{kategori} {aid} {loc}".strip() if aid else f"{kategori} {loc}".strip()
            identitas = re.sub(r'\s+', ' ', identitas).strip()
            new_name = build_filename(prefix_periode, kode, "Perawatan", identitas, tgl_full, False)
            new_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)

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
                processed_files.append({
                    "filename": new_name,
                    "kategori": kategori,
                    "sap_cat": kategori,
                    "loc": loc,
                    "asset": aid,
                    "kode": kode,
                })
                unique_filenames.add(new_name)
            else:
                duplicate_errors.append(f"WARNING|{fname}|Duplicate: {new_name}")

    except Exception as e:
        duplicate_errors.append(f"ERROR|{fname}|{e}")

    if idx % 50 == 0 or idx == total:
        print(f"  Progress: {idx}/{total} ({idx*100//total}%)")

out = {
    "processed": processed_files,
    "errors": duplicate_errors,
    "total_files": len(processed_files),
}
outpath = os.path.join(SRC, "_hasil_app.json")
with open(outpath, "w") as f:
    json.dump(out, f, indent=2)

print(f"\nDone. {len(processed_files)} files processed, {len(duplicate_errors)} errors")
print(f"Saved: {outpath}")
