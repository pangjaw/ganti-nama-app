import os
import re
import zipfile
import platform
import pytesseract
import gc
from io import BytesIO
from flask import Flask, request, jsonify, render_template, send_file
from pdf2image import convert_from_bytes
from PIL import ImageOps, Image

app = Flask(__name__)

# Config Tesseract
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

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
    format_eksklusif = (instansi == 'BTP BD')

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
            
            assets_found = []
            is_special_doc = False
            kode_ceklis = ""
            kategori_nama = ""

            try:
                file_bytes = f.read()
                text_crop = process_pdf_ocr(file_bytes)
                text_flat = text_crop.replace('\n', ' ')

                # GERBANG A: DOKUMEN SPESIAL
                if any(x in text_flat for x in ["POINT LOCK", "PENGAMAN WESEL"]):
                    is_special_doc = True
                    kategori_nama = "WESEL"
                    kode_ceklis = "BPBYE1"
                    w_match = re.search(r'(W\d+)', text_flat)
                    aid = w_match.group(1) if w_match else "W_UNKNOWN"
                    loc_id = "BOO" if "BOGOR" in text_flat else "LOKASI"
                    assets_found.append({"id": aid, "loc": loc_id})

                elif "PERALATAN DALAM PERSINYALAN ELEKTRIK" in text_flat:
                    is_special_doc = True
                    kategori_nama = "PDSE"
                    kode_ceklis = "BPBYE2"
                    if "BOGORPALEDANG" in text_flat: loc_id = "BOP"
                    elif "BOGOR" in text_flat: loc_id = "BOO"
                    elif "CILEBUT" in text_flat: loc_id = "CLT"
                    else: loc_id = "LOKASI"
                    assets_found.append({"id": "", "loc": loc_id})

                elif "PINTU PERLINTASAN" in text_flat:
                    is_special_doc = True
                    kategori_nama = "PINTU PERLINTASAN"
                    kode_ceklis = "BPBKS17"
                    jpl_match = re.search(r'JPL\s+(\d+)', text_flat)
                    aid = f"JPL {jpl_match.group(1)}" if jpl_match else "JPL"
                    loc_id = "BOP" if "BOGORPALEDANG" in text_flat else "LOKASI"
                    assets_found.append({"id": aid, "loc": loc_id})

                # GERBANG B: DOKUMEN MULTI-ASET (Fallback)
                if not is_special_doc:
                    if "WESEL" in name_only:
                        kode_ceklis, kategori_nama = "BPBYE1", "WESEL"
                        assets_found.append({"id": "X", "loc": "LOKASI"})
                    elif "AXLE" in name_only:
                        kode_ceklis, kategori_nama = "BPBYE7", "AXC"
                        assets_found.append({"id": "X", "loc": "LOKASI"})

                if not assets_found:
                    duplicate_errors.append(f"❌ {f.filename}: Gagal mendeteksi aset.")
                    continue

                for asset in assets_found:
                    aid = asset["id"]
                    loc = asset["loc"]
                    identitas = f"{kategori_nama} {aid} {loc}".strip()
                    
                    if format_eksklusif:
                        resor = "Resor 1.21 Boo"
                        new_name = f"{prefix_periode}_{resor}_{kode_ceklis}_{jenis_kegiatan}_{identitas}_{tgl_full}.pdf"
                    else:
                        new_name = f"{jenis_kegiatan.upper()} {identitas} {tgl_full}.pdf"
                    
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

    # Simpan zip ke cache temporary di memori agar bisa didownload
    zip_buffer.seek(0)
    
    # Simpan temporary ke disk agar Flask session bisa ambil nanti
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
