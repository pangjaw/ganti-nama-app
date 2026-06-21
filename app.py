import os
import re
import uuid
import zipfile
import platform
import pytesseract
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

# Pola regex untuk pendeteksian sinyal (digunakan di beberapa tempat)
SIGNAL_PATTERN = re.compile(r'\b([BJLSXU]+\.?\s?\d{1,3}[A-Z]?)\b')

# Path temp ZIP terakhir yang dihasilkan (diperbarui setiap request /process)
_last_zip_path = None

def get_temp_zip_path():
    """Menghasilkan path temp ZIP yang unik per request untuk menghindari konflik."""
    temp_dir = '/tmp' if platform.system() != 'Windows' else os.environ.get('TEMP', '.')
    return os.path.join(temp_dir, f'output_{uuid.uuid4().hex}.zip')

def process_pdf_ocr(file_bytes):
    images = convert_from_bytes(file_bytes, dpi=150, first_page=1, last_page=1)
    img = images[0].convert('L')
    img = ImageOps.autocontrast(img)
    width, height = img.size
    img_cropped = img.crop((0.0, 0.0, width * 1.0, height * 0.30)) 
    text_crop = pytesseract.image_to_string(img_cropped, lang='ind+eng').upper()
    del img, images
    return text_crop

def detect_doc(text_flat, text_crop, filename_upper):
    kode = ""
    kategori = ""
    assets = []

    # Fungsi helper untuk menentukan lokasi standar
    def get_standard_loc(text):
        if "CIOMAS" in text or "COS" in text: return "COS"
        if "MASENG" in text or "MSG" in text: return "MSG"
        if "CIGOMBONG" in text or "CGB" in text: return "CGB"
        if "BOGORPALEDANG" in text or "PALEDANG" in text: return "BOP"
        if "BATUTULIS" in text or "BTT" in text: return "BTT"
        if "CILEBUT" in text: return "CLT"
        if "BOGOR" in text: return "BOO"
        return "LOKASI"

    # Fungsi helper untuk memfilter duplikat array (O(n), urutan terjaga)
    def get_unique_list(items):
        return list(dict.fromkeys(items))

    # Fungsi helper untuk ekstraksi aset JPL (menghilangkan duplikasi kode)
    def extract_jpl_assets(text_clean, text_flat_ref, multi_word=False):
        """Ekstrak aset JPL dari text_clean. multi_word=True untuk pola multi-kata."""
        result = []
        noise_words = ["DISETUJUL", "DIKETAHUI", "OLEH", "TANGGAL", "ELEKTRIK", "NO"]
        # Ekstrak JPL Angka
        for match in re.finditer(r'JPL\s+(?:ELEKTRIK\s+)?(?:NO[.\s]*)?(\d+)', text_clean):
            aid = f"JPL {match.group(1).strip()}"
            loc = get_standard_loc(text_clean[match.end():])
            if loc == "LOKASI":
                loc = get_standard_loc(text_flat_ref)
            if not any(a["id"] == aid for a in result):
                result.append({"id": aid, "loc": loc})
        # Ekstrak JPL Huruf
        word_rx = r'JPL\s+([A-Z]+(?:\s+[A-Z\-]+)*)' if multi_word else r'\bJPL\s+([A-Z]+)\b'
        for match in re.finditer(word_rx, text_clean):
            aid = f"JPL {match.group(1).strip()}"
            word_parts = aid.replace("JPL ", "").split()
            if all(part.strip(".-,;") in noise_words for part in word_parts):
                continue
            loc = get_standard_loc(text_clean[match.end():])
            if loc == "LOKASI":
                loc = get_standard_loc(text_flat_ref)
            if not any(a["id"] == aid for a in result):
                result.append({"id": aid, "loc": loc})
        if not result:
            result.append({"id": "JPL", "loc": get_standard_loc(text_flat_ref)})
        return result

    # GERBANG A: OCR-based detection
    if "PERAWATAN WESEL" in text_flat or "PENGGERAK WESEL" in text_flat:
        kode, kategori = "BPBYE1", "WESEL"
        loc = get_standard_loc(text_flat)
        w_matches = re.findall(r'PENGGERAK\s+WESEL\s+(W\d+[A-Z]*)', text_flat)
        
        if w_matches:
            unique_w = get_unique_list(w_matches)
            for w in unique_w:
                assets.append({"id": w, "loc": loc})
        else:
            # Fallback jika tidak menemukan teks persis 'PENGGERAK WESEL (Wxx)'
            fallback_matches = re.findall(r'(W\d+[A-Z]*)', text_flat)
            if fallback_matches:
                unique_w = get_unique_list(fallback_matches)
                for w in unique_w:
                    assets.append({"id": w, "loc": loc})
            else:
                assets.append({"id": "W_UNKNOWN", "loc": loc})

    elif any(x in text_flat for x in ["POINT LOCK", "PENGAMAN WESEL"]):
        kode, kategori = "BPBYE1", "WESEL"  # Biarkan WESEL sesuai aslinya kecuali ada instruksi lain
        loc = get_standard_loc(text_flat)
        w_matches = re.findall(r'(W\d+[A-Z]*)', text_flat)
        
        if w_matches:
            unique_w = get_unique_list(w_matches)
            for w in unique_w:
                assets.append({"id": w, "loc": loc})
        else:
            assets.append({"id": "W_UNKNOWN", "loc": loc})

    elif "PERALATAN DALAM PERSINYALAN ELEKTRIK" in text_flat:
        kode, kategori = "BPBYE2", "PDSE"
        loc = get_standard_loc(text_flat)
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
                        loc = get_standard_loc(line)
                        if loc == "LOKASI": # Jika perbaris gagal mendeteksi, fallback ke keseluruhan
                            loc = get_standard_loc(text_flat)
                        # Cek duplikasi di array object
                        if not any(a["id"] == aid and a["loc"] == loc for a in assets):
                            assets.append({"id": aid, "loc": loc})

    elif "TELEKOMUNIKASI DI PINTU PERLINTASAN" in text_flat:
        kode, kategori = "BPBKS17", "PTPP"
        text_clean = re.sub(r'\bJPL\d+\b', '', text_flat)  # filter system code JPL10506
        assets = extract_jpl_assets(text_clean, text_flat, multi_word=False)

    elif "PINTU PERLINTASAN" in text_flat and "TELEKOMUNIKASI" not in text_flat:
        kode, kategori = "BPBKS17", "PINTU PERLINTASAN"
        text_clean = re.sub(r'\bJPL\d+\b', '', text_flat)
        assets = extract_jpl_assets(text_clean, text_flat, multi_word=True)

    elif "TELEKOMUNIKASI DI STASIUN" in text_flat:
        kode, kategori = "BPBKS15", "PTDS"
        loc = get_standard_loc(text_flat)
        assets.append({"id": "", "loc": loc})

    elif "TELEKOMUNIKASI DI LUAR STASIUN" in text_flat:
        kode, kategori = "BPBKS16", "PTLS"
        loc = get_standard_loc(text_flat)
        assets.append({"id": "", "loc": loc})

    elif "PERAWATAN AXLE COUNTER" in text_flat:
        kode, kategori = "BPBYE7", "AXLE COUNTER"
        
        # Cari format ZP dengan 1-3 angka dan opsional huruf (ZP 10A, ZP10B, ZP 1, ZP 114)
        # Kami mengizinkan \d{1,3} agar ZP 1 dan ZP 114 terdeteksi.
        # Hindari tipe perangkat seperti ZP43 dengan memastikan tidak ada teks yang terkait dengannya.
        zp_matches = re.findall(r'\b(ZP\s?\d{1,3}[A-Z]?)\b', text_flat)
        # Hapus false positive "ZP 43" (yang biasanya ZP43 atau ZP 43) karena itu tipe alat
        zp_matches = [z for z in zp_matches if z.replace(" ", "") != "ZP43"]

        if zp_matches:
            unique_zp = get_unique_list(zp_matches)
            for z in unique_zp:
                pos = text_flat.find(z)
                loc = get_standard_loc(text_flat[pos:] if pos != -1 else text_flat)
                if loc == "LOKASI": loc = get_standard_loc(text_flat)
                z_clean = re.sub(r'ZP\s?(\d)', r'ZP \1', z)
                assets.append({"id": z_clean, "loc": loc})
        else:
            loc = get_standard_loc(text_flat)
            assets.append({"id": "ZP", "loc": loc})

    elif "PERAGA SINYAL" in text_flat:
        kode, kategori = "BPBYE3", "PERAGA SINYAL"
        # Cari Sinyal: B.210, UB.210, B210, JL62B, B201, L22, S11A, dll
        # Variasi di KAI: SINYAL BLOK B.210, SINYAL ULANG BLOK UB.210, JL62B, B201
        signal_matches = SIGNAL_PATTERN.findall(text_flat)
        
        valid_signals = []
        for s in signal_matches:
            s_clean = s.replace(" ", "").replace(".", "")
            # Sinyal harus punya huruf awal B/L/J/S/X/U dan setelah itu ada angkanya
            if re.match(r'^[BJLSXU]+\d+', s_clean):
                valid_signals.append(s_clean)
                
        if valid_signals:
            unique_sig = get_unique_list(valid_signals)
            for s in unique_sig:
                pos = text_flat.find(s)
                loc = get_standard_loc(text_flat[pos:] if pos != -1 else text_flat)
                if loc == "LOKASI": loc = get_standard_loc(text_flat)
                assets.append({"id": s, "loc": loc})
        else:
            loc = get_standard_loc(text_flat)
            assets.append({"id": "", "loc": loc})

    elif "CATU DAYA" in text_flat:
        kode, kategori = "BPBYE14", "CATU DAYA"
        loc = get_standard_loc(text_flat)
        assets.append({"id": "", "loc": loc})

    # GERBANG B: filename-based detection
    if not assets:
        loc = get_standard_loc(filename_upper)
        if "WESEL ELEKTRIK" in filename_upper:
            kode, kategori = "BPBYE1", "WESEL"
            w_matches = re.findall(r'(W\d+[A-Z]*)', filename_upper)
            if w_matches:
                unique_w = get_unique_list(w_matches)
                for w in unique_w: assets.append({"id": w, "loc": loc})
            else: assets.append({"id": "W_UNKNOWN", "loc": loc})
        elif "POINT LOCK" in filename_upper:
            kode, kategori = "BPBYE7", "WESEL"
            assets.append({"id": "PL", "loc": loc})
        elif "AXLE COUNTER" in filename_upper:
            kode, kategori = "BPBYE7", "AXLE COUNTER"
            zp_matches = re.findall(r'(ZP\s?\d+[A-Z]*)', filename_upper)
            if zp_matches:
                unique_zp = get_unique_list(zp_matches)
                for z in unique_zp:
                    z_clean = re.sub(r'ZP(\d)', r'ZP \1', z)
                    assets.append({"id": z_clean, "loc": loc})
            else:
                assets.append({"id": "ZP", "loc": loc})
        elif "PERAGA SINYAL" in filename_upper:
            kode, kategori = "BPBYE3", "PERAGA SINYAL"
            signal_matches = SIGNAL_PATTERN.findall(filename_upper)
            if signal_matches:
                unique_sig = get_unique_list(signal_matches)
                for s in unique_sig:
                    s_clean = s.replace(" ", "").replace(".", "")
                    assets.append({"id": s_clean, "loc": loc})
            else:
                assets.append({"id": "", "loc": loc})
        elif "SERAT OPTIK" in filename_upper:
            kode, kategori = "BPBKF4", "SERAT OPTIK"
            assets.append({"id": "", "loc": loc})

    return kode, kategori, assets

def get_btp(loc):
    if loc in BTP_JAK_LOCS:
        return "BTP JAK"
    return "BTP BD"

def build_filename(prefix_periode, kode, jenis, identitas, tgl_full, format_bd):
    # Untuk PERAGA SINYAL, gunakan label 'SINYAL' di output agar sesuai format
    identitas = identitas.replace("PERAGA SINYAL", "SINYAL").replace("PERAWATAN SINYAL", "SINYAL")
        
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
    global _last_zip_path

    if 'files[]' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
        
    uploaded_files = request.files.getlist('files[]')
    jenis_kegiatan = request.form.get('jenis_kegiatan', 'Perawatan')
    instansi = request.form.get('instansi', 'BTP JAK')
    format_bd = (instansi == 'BTP BD')  # Dihitung sekali, dipakai di semua iterasi

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
                text_flat = re.sub(r'\s+', ' ', text_crop)

                kode, kategori, assets = detect_doc(text_flat, text_crop, name_only)

                if not assets:
                    duplicate_errors.append(f"❌ {f.filename}: Jenis dokumen tidak terdeteksi.")
                    continue

                # Proses setiap aset yang ditemukan di dokumen (multi-aset support)
                for asset in assets:
                    aid = asset["id"]
                    loc = asset["loc"]
                    
                    identitas = f"{kategori} {aid} {loc}".strip() if aid else f"{kategori} {loc}".strip()
                    identitas = re.sub(r'\s+', ' ', identitas).strip()
                    
                    # Eksekusi build_filename yang sudah mendukung 2 format sesuai aturan routing
                    new_name = build_filename(prefix_periode, kode, jenis_kegiatan, identitas, tgl_full, format_bd)
                    new_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)
                    
                    # Filter output akhir duplikat di level arsip zip
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
    _last_zip_path = get_temp_zip_path()
    with open(_last_zip_path, 'wb') as f_out:
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
    if _last_zip_path and os.path.exists(_last_zip_path):
        return send_file(_last_zip_path, as_attachment=True, download_name='Ceklis_Hasil_OCR.zip', mimetype='application/zip')
    return "File tidak ditemukan", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8501))
    app.run(host='0.0.0.0', port=port, debug=True)
