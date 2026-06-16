import os
import re
import zipfile
import platform
import pytesseract
import gc
from io import BytesIO
from flask import Flask, request, jsonify, render_template, send_file
from pdf2image import convert_from_bytes
from PIL import ImageOps

app = Flask(__name__)

# Config Tesseract
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

BTP_JAK_LOCS = ["BOO", "CLT"]  # Bogor, Cilebut
BTP_BD_LOCS  = ["BOP", "BTT", "COS", "MSG", "CGB"]  # Bogorpaledang, Batutulis, dll

def process_pdf_ocr(file_bytes):
    images = convert_from_bytes(file_bytes, dpi=150, first_page=1, last_page=1)
    img = images[0].convert('L')
    img = ImageOps.autocontrast(img)
    width, height = img.size
    img_cropped = img.crop((0.0, 0.0, width * 1.0, height * 0.30)) 
    text_crop = pytesseract.image_to_string(img_cropped, lang='ind+eng').upper()
    del img, images
    gc.collect()
    return text_crop

def detect_doc(text_flat, text_crop, filename_upper):
    kode = ""
    kategori = ""
    assets = []

    # GERBANG A: OCR-based detection
    if any(x in text_flat for x in ["POINT LOCK", "PENGAMAN WESEL"]):
        kode, kategori = "BPBYE1", "WESEL"
        w_match = re.search(r'(W\d+[A-Z]*)', text_flat)
        aid = w_match.group(1) if w_match else "W_UNKNOWN"
        loc = "CLT" if "CILEBUT" in text_flat else ("BOO" if "BOGOR" in text_flat else "LOKASI")
        assets.append({"id": aid, "loc": loc})

    elif "PERAWATAN WESEL" in text_flat or "PENGGERAK WESEL" in text_flat:
        kode, kategori = "BPBYE1", "WESEL"
        w_matches = re.findall(r'PENGGERAK\s+WESEL\s+(W\d+[A-Z]*)', text_flat)
        if w_matches:
            aid = w_matches[0]
        else:
            w_match = re.search(r'(W\d+[A-Z]*)', text_flat)
            aid = w_match.group(1) if w_match else "W_UNKNOWN"
        loc = "CLT" if "CILEBUT" in text_flat else ("BOO" if "BOGOR" in text_flat else "LOKASI")
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
        text_clean = re.sub(r'\bJPL\d+\b', '', text_flat)
        jpl_match = re.search(r'JPL\s+(?:ELEKTRIK\s+)?(?:NO[.\s]*)?(\d+)', text_clean)
        if jpl_match:
            aid = f"JPL {jpl_match.group(1).strip()}"
            after_jpl = text_clean[jpl_match.end():].strip()
            for noise in ["DISETUJUL", "DIKETAHUI", "OLEH", "TANGGAL", "LOKASI", "PERIODE", "DILAKSANAKAN"]:
                if noise in after_jpl: after_jpl = after_jpl.split(noise)[0].strip()
            loc = re.sub(r'\s+', ' ', after_jpl).strip()
        else:
            jpl_word_match = re.search(r'\bJPL\s+([A-Z]+)\b', text_clean)
            if jpl_word_match:
                aid = f"JPL {jpl_word_match.group(1).strip()}"
                after_jpl = text_clean[jpl_word_match.end():].strip()
                for noise in ["DISETUJUL", "DIKETAHUI", "OLEH", "TANGGAL", "LOKASI", "PERIODE", "DILAKSANAKAN"]:
                    if noise in after_jpl: after_jpl = after_jpl.split(noise)[0].strip()
                loc = re.sub(r'\s+', ' ', after_jpl).strip()
            else:
                aid, loc = "JPL", ""
        assets.append({"id": aid, "loc": loc})

    elif "PINTU PERLINTASAN" in text_flat and "TELEKOMUNIKASI" not in text_flat:
        kode, kategori = "BPBKS17", "PINTU PERLINTASAN"
        jpl_match = re.search(r'JPL\s+(?:ELEKTRIK\s+)?(?:NO[.\s]*)?(\d+)', text_flat)
        if jpl_match:
            aid = f"JPL {jpl_match.group(1).strip()}"
            after_jpl = text_flat[jpl_match.end():].strip()
            for noise in ["DISETUJUL", "DIKETAHUI", "OLEH", "TANGGAL", "LOKASI", "PERIODE", "DILAKSANAKAN"]:
                if noise in after_jpl: after_jpl = after_jpl.split(noise)[0].strip()
            loc = re.sub(r'\s+', ' ', after_jpl).strip()
        else:
            jpl_fallback = re.search(r'JPL\s+([A-Z]+(?:\s+[A-Z\-]+)*)', text_flat)
            if jpl_fallback:
                aid = "JPL"
                after_jpl = text_flat[jpl_fallback.end():].strip()
                for noise in ["DISETUJUL", "DIKETAHUI", "OLEH", "TANGGAL", "LOKASI", "PERIODE", "DILAKSANAKAN"]:
                    if noise in after_jpl: after_jpl = after_jpl.split(noise)[0].strip()
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
            loc = "BOP" if "BOGORPALEDANG" in filename_upper else ("CLT" if "CILEBUT" in filename_upper else ("BOO" if "BOGOR" in filename_upper else "LOKASI"))
            assets.append({"id": aid, "loc": loc})
        elif "POINT LOCK" in filename_upper:
            kode, kategori = "BPBYE7", "WESEL"
            loc = "BOP" if "BOGORPALEDANG" in filename_upper else ("CLT" if "CILEBUT" in filename_upper else ("BOO" if "BOGOR" in filename_upper else "LOKASI"))
            assets.append({"id": "PL", "loc": loc})
        elif "AXLE COUNTER" in filename_upper:
            kode, kategori = "BPBYE7", "AXLE COUNTER"
            loc = "BOP" if "BOGORPALEDANG" in filename_upper else ("CLT" if "CILEBUT" in filename_upper else ("BOO" if "BOGOR" in filename_upper else "LOKASI"))
            assets.append({"id": "ZP", "loc": loc})
        elif "PERAGA SINYAL" in filename_upper:
            kode, kategori = "BPBYE3", "PERAGA SINYAL"
            loc = "BOP" if "BOGORPALEDANG" in filename_upper else ("CLT" if "CILEBUT" in filename_upper else ("BOO" if "BOGOR" in filename_upper else "LOKASI"))
            assets.append({"id": "", "loc": loc})
        elif "SERAT OPTIK" in filename_upper:
            kode, kategori = "BPBKF4", "SERAT OPTIK"
            loc = "BOP" if "BOGORPALEDANG" in filename_upper else ("CLT" if "CILEBUT" in filename_upper else ("BOO" if "BOGOR" in filename_upper else "LOKASI"))
            assets.append({"id": "", "loc": loc})

    return kode, kategori, assets

def get_btp(loc):
    if loc in BTP_JAK_LOCS:
        return "BTP JAK"
    return "BTP BD"

def build_filename(prefix_periode, kode, jenis, identitas, tgl_full, format_bd):
    if format_bd:
        resor = "Resor 1.21 Boo"
        return f"{prefix_periode}_{resor}_{kode}_{jenis}_{identitas}_{tgl_full}.pdf"
    else:
        return f"{jenis.upper()} {identitas} {tgl_full}.pdf"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_files():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
        
    uploaded_files = request.files.getlist('files[]')
    jenis_kegiatan = request.form.get('jenis_kegiatan', 'Perawatan')
    instansi = request.form.get('instansi', 'BTP JAK')
    user_format_bd = (instansi == 'BTP BD')

    zip_buffer = BytesIO()
    processed_files = []
    duplicate_errors = []
    unique_filenames = set()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_f:
        for f in uploaded_files:
            if not f.filename.endswith('.pdf'):
                continue
                
            name_only = f.filename.upper()
            tgl_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', name_only)
            
            if not tgl_match:
                duplicate_errors.append(f"❌ {f.filename}: Format tanggal tidak ditemukan.")
                continue
                
            tgl_full = tgl_match.group(0)
            bln_angka = str(int(tgl_match.group(2)))
            thn_angka = tgl_match.group(3)
            prefix_periode = f"{thn_angka}-{bln_angka}"

            try:
                file_bytes = f.read()
                text_crop = process_pdf_ocr(file_bytes)
                text_flat = text_crop.replace('\n', ' ')

                kode, kategori, assets = detect_doc(text_flat, text_crop, name_only)

                if not assets:
                    duplicate_errors.append(f"❌ {f.filename}: Jenis dokumen tidak terdeteksi.")
                    continue

                for asset in assets:
                    aid = asset["id"]
                    loc = asset["loc"]
                    
                    # Routing BTP: Gunakan default dari deteksi lokasi asset
                    btp = get_btp(loc)
                    
                    # Namun user input manual radio button bisa memaksa format (BD vs JAK)
                    format_bd = user_format_bd if instansi != 'BTP JAK' else (btp == "BTP BD")
                    
                    identitas = f"{kategori} {aid} {loc}".strip() if aid else f"{kategori} {loc}".strip()
                    identitas = re.sub(r'\s+', ' ', identitas).strip()
                    
                    new_name = build_filename(prefix_periode, kode, jenis_kegiatan, identitas, tgl_full, format_bd)
                    new_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)
                    
                    if new_name not in unique_filenames:
                        zip_f.writestr(new_name, file_bytes)
                        processed_files.append(new_name)
                        unique_filenames.add(new_name)
                    else:
                        duplicate_errors.append(f"⚠️ {f.filename}: Duplikat ({new_name})")

            except Exception as e:
                duplicate_errors.append(f"❌ {f.filename}: Error {e}")

    if not processed_files:
        return jsonify({'error': 'Tidak ada file yang berhasil diproses', 'details': duplicate_errors}), 400

    zip_buffer.seek(0)
    temp_zip_path = os.path.join('/tmp' if platform.system() != 'Windows' else os.environ.get('TEMP', '.'), 'temp_output.zip')
    with open(temp_zip_path, 'wb') as f_out:
        f_out.write(zip_buffer.getvalue())

    return jsonify({
        'success': True,
        'processed_count': len(processed_files),
        'files': processed_files,
        'errors': duplicate_errors,
        'download_url': '/download'
    })

@app.route('/download')
def download():
    temp_zip_path = os.path.join('/tmp' if platform.system() != 'Windows' else os.environ.get('TEMP', '.'), 'temp_output.zip')
    if os.path.exists(temp_zip_path):
        return send_file(temp_zip_path, as_attachment=True, download_name='Ceklis_Hasil_OCR.zip', mimetype='application/zip')
    return "File tidak ditemukan", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8501))
    app.run(host='0.0.0.0', port=port, debug=True)
