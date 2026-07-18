import os
import re
import sys
import uuid
import zipfile
import platform
import pytesseract
from io import BytesIO
from flask import Flask, request, jsonify, render_template, send_file, after_this_request
from pdf2image import convert_from_bytes
from PIL import ImageOps

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log')

# Force UTF-8 so emoji in logs doesn't crash
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def log(msg):
    print(f"[LOG] {msg}", flush=True)

def logerr(msg):
    print(f"[ERR] {msg}", file=sys.stderr, flush=True)

# Allow uploads up to 500MB
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

# Config Tesseract
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

BTP_JAK_LOCS = ["BOO", "CLT"]  # Bogor, Cilebut
BTP_BD_LOCS  = ["BOP", "BTT", "COS", "MSG", "CGB", "CCR"]  # Bogorpaledang, Batutulis, dll

# Pola regex untuk pendeteksian sinyal (digunakan di beberapa tempat)
SIGNAL_PATTERN = re.compile(r'\b([BJLMSXU]+\.?\s?\d{1,3}[A-Z]?)\b')



# Path temp ZIP per request, diambil lewat download_id agar download tidak tertukar antar user
_downloads = {}

def get_temp_zip_path():
    """Menghasilkan path temp ZIP yang unik per request untuk menghindari konflik."""
    temp_dir = '/tmp' if platform.system() != 'Windows' else os.environ.get('TEMP', '.')
    return os.path.join(temp_dir, f'output_{uuid.uuid4().hex}.zip')

def process_pdf_ocr(file_bytes):
    images = convert_from_bytes(file_bytes, dpi=200, first_page=1, last_page=1)
    img = images[0].convert('L')
    img = ImageOps.autocontrast(img)
    width, height = img.size
    img_cropped = img.crop((0.0, 0.0, width * 1.0, height * 0.40)) 
    text_crop = pytesseract.image_to_string(img_cropped, lang='ind+eng').upper()
    del img, images
    return text_crop

def detect_doc(text_flat, text_crop, filename_upper):
    kode = ""
    kategori = ""
    assets = []

    # Fungsi helper untuk menentukan lokasi standar
    def get_standard_loc(text):
        text = text.upper()
        if "BOJONGGEDE" in text or "BOJONG GEDE" in text: return "BJD-CLT"
        if "CIOMAS" in text or "COS" in text: return "COS"
        if "CICURUG" in text or "CCR" in text: return "CCR"
        if "CIGOMBONG" in text or "CGB" in text: return "CGB"
        if "MASENG" in text or "MSG" in text: return "MSG"
        if "BOGORPALEDANG" in text or "PALEDANG" in text: return "BOP"
        if "BATUTULIS" in text or "BTT" in text: return "BTT"
        if "CILEBUT" in text or "CLT" in text: return "CLT"
        if "BOGOR" in text: return "BOO"

        noise_words = {
            "DISETUJUI", "DISETUJUL", "PISETUJUI", "DIKETAHUI", "DILAKSANAKAN", "OLEH",
            "TANGGAL", "PERIODE", "PERAWATAN", "NO", "SC", "NOMOR", "ASET",
            "PENGGERAK", "WESEL", "ELEKTRIK", "MINGGUAN", "BULANAN", "TAHUNAN",
            "HERU"
        }
        trailing_loc_noise = {"AN", "EEN", "SIE", "SIEH", "SIH", "SETE", "S"}
        for keyword in ("LOKASI", "STASIUN", "RESOR"):
            match = re.search(rf'\b{keyword}\b', text)
            if not match:
                continue
            tail = re.sub(r'^[\s:.\-]+', '', text[match.end():])
            loc_parts = []
            for part in re.findall(r'[A-Z0-9]+(?:-[A-Z0-9]+)*', tail):
                if part in noise_words or part.isdigit():
                    break
                loc_parts.append(part)
                if len(loc_parts) == 3:
                    break
            while loc_parts and loc_parts[-1] in trailing_loc_noise:
                loc_parts.pop()
            if loc_parts:
                return " ".join(loc_parts)

        if ".PDF" in text and "_" in text:
            tail = text.rsplit("_", 1)[-1]
            loc_parts = [p for p in re.findall(r'[A-Z0-9]+', tail) if not p.isdigit() and p != "PDF"]
            if loc_parts:
                return " ".join(loc_parts[:3])

        return ""

    def extract_funcloc(text_crop):
        """Ambil lokasi dari baris LOKASI di header crop.
        FUNCLOC bisa singkatan (MSG-CCR) atau full (MASENG-CICURUG).
        Preserve urutan asli."""
        loc_map = {
            "MASENG": "MSG", "CICURUG": "CCR",
            "CILEBUT": "CLT", "BOGOR": "BOO",
            "BATUTULIS": "BTT", "BOGORPALEDANG": "BOP", "PALEDANG": "BOP",
            "CIOMAS": "COS", "CIGOMBONG": "CGB", "BOJONGGEDE": "BJD",
        }
        for line in text_crop.split('\n'):
            m = re.search(r'\bLOKASI\b', line.upper())
            if not m:
                continue
            tail = line[m.end():].strip()
            tail = re.sub(r'^[\s:.]+', '', tail)
            parts = re.findall(r'[A-Z]+(?:-[A-Z]+)*', tail.upper())
            if not parts:
                continue
            first = parts[0]
            subs = first.split('-')
            mapped = []
            for s in subs:
                s = s.strip()
                # langsung 3-letter code
                if s in loc_map.values():
                    mapped.append(s)
                elif s in loc_map:
                    mapped.append(loc_map[s])
                else:
                    mapped.append(s)
            if mapped:
                return '-'.join(mapped)
        return None  # fallback ke method lama
    
    def get_ptls_loc(text_flat, text_crop):
        """PTLS: cari "LUAR" di judul, lalu cari "LOKASI" di bawahnya."""
        loc_map = {
            "BOGOR": "BOO", "CILEBUT": "CLT",
            "BATUTULIS": "BTT", "BOGORPALEDANG": "BOP", "PALEDANG": "BOP",
            "CIOMAS": "COS", "MASENG": "MSG", "CIGOMBONG": "CGB", "CICURUG": "CCR",
            "DEPOK": "BOO",
        }
        lines = text_crop.split('\n')
        luar_idx = None
        for i, l in enumerate(lines):
            if 'LUAR' in l.upper():
                luar_idx = i
                break
        if luar_idx is None:
            return get_standard_loc(text_flat)
        for l in lines[luar_idx + 1:]:
            l_strip = l.strip().upper()
            if l_strip.startswith('LOKASI'):
                parts = re.split(r'[:|]+', l_strip, maxsplit=1)
                if len(parts) > 1:
                    val = parts[-1].strip()
                else:
                    val = parts[0][6:].strip()
                words = re.findall(r'[A-Z0-9]+(?:-[A-Z0-9]+)*', val)
                if not words:
                    continue
                first = words[0]
                if '-' in first:
                    subs = first.split('-')
                    for s in subs:
                        if s == 'CIGOMBONG':
                            return 'CGB'
                    for s in subs:
                        m = loc_map.get(s)
                        if m:
                            return m
                    return first
                return loc_map.get(first, first)
        return get_standard_loc(text_flat)

    # Fungsi helper untuk memfilter duplikat array (O(n), urutan terjaga)
    def get_unique_list(items):
        return list(dict.fromkeys(items))

    def extract_wesel_ids(text, allow_generic=False):
        result = []
        patterns = [
            r'PENGGERAK\s+WESEL(?:\s+ELEKTRIK)?\s+(?:W\s*\.?\s*)?(\d{1,3})\s*([A-Z]?\d?)\b',
            r'\bW(?!SL)\s*\.?\s*(\d{1,3})\s*([A-Z]?\d?)\b'
        ]
        if allow_generic:
            patterns.append(r'\b(?:W\s*\.?\s*)?(\d{1,3})\s*([A-Z]\d?)\b')
        for pattern in patterns:
            for num, suffix in re.findall(pattern, text):
                result.append(f"W{num}{suffix}".replace(" ", ""))
        return get_unique_list(result)

    # Fungsi helper untuk ekstraksi aset JPL (menghilangkan duplikasi kode)
    def extract_jpl_assets(text_clean, text_flat_ref, multi_word=False):
        """Ekstrak aset JPL dari text_clean. multi_word=True untuk pola multi-kata."""
        result = []
        noise_words = ["DISETUJUL", "DIKETAHUI", "OLEH", "TANGGAL", "ELEKTRIK", "NO"]
        loc_codes = {"BOP", "BTT", "CLT", "CGB", "MSG", "COS", "BOO", "CCR", "BJD"}
        
        def get_jpl_inline_loc(text_snippet):
            """Cari 3-letter location codes di sekitar text JPL sesuai urutan dokumen."""
            matches = []
            for code in loc_codes:
                for m in re.finditer(r'\b' + code + r'\b', text_snippet):
                    matches.append((m.start(), code))
            matches.sort(key=lambda x: x[0])
            seen = set()
            found = [code for _, code in matches if not (code in seen or seen.add(code))]
            return "-".join(found)
        
        # Ekstrak JPL Angka (support alphanumeric: 26N, 01, dll)
        for match in re.finditer(r'JPL\s+(?:ELEKTRIK\s+)?(?:NO[.\s]*)?([0-9]+[A-Z]*)', text_clean):
            aid = f"JPL {match.group(1).strip()}"
            # Coba inline location dulu (max 80 karakter setelah match)
            snippet = text_clean[match.end():match.end()+25]
            loc = get_jpl_inline_loc(snippet)
            if not loc:
                loc = get_standard_loc(text_clean[match.end():])
            if loc == "LOKASI":
                loc = get_standard_loc(text_flat_ref)
            if not any(a["id"] == aid for a in result):
                result.append({"id": aid, "loc": loc})
        # Ekstrak JPL Huruf
        word_rx = r'JPL\s+([A-Z]+(?:\s+[A-Z\-]+)*)' if multi_word else r'\bJPL\s+([A-Z]+)\b'
        for match in re.finditer(word_rx, text_clean):
            aid = f"JPL {match.group(1).strip()}"
            aid = re.split(r'\s+\b(?:LOKASI|DISETUJUI|DISETUJUL|PISETUJUI|DIKETAHUI|TANGGAL|OLEH)\b', aid, 1)[0].strip()
            word_parts = aid.replace("JPL ", "").split()
            if all(part.strip(".-,;") in noise_words for part in word_parts):
                continue
            # Coba inline location dulu (max 80 karakter setelah match)
            snippet = text_clean[match.end():match.end()+25]
            loc = get_jpl_inline_loc(snippet)
            if not loc:
                loc = get_standard_loc(text_clean[match.end():])
            if loc == "LOKASI":
                loc = get_standard_loc(text_flat_ref)
            if re.search(r'\b[A-Z]{3}\s*-\s*[A-Z]{3}\b', aid):
                loc = ""
            if not any(a["id"] == aid for a in result):
                result.append({"id": aid, "loc": loc})
        if not result:
            result.append({"id": "JPL", "loc": get_standard_loc(text_flat_ref)})
        return result

    def get_dual_loc(text):
        """Scan text left-to-right, kumpulin kode lokasi sesuai urutan dokumen. Max 2 kode."""
        loc_map = {
            "BOGOR": "BOO", "CILEBUT": "CLT",
            "BATUTULIS": "BTT", "BOGORPALEDANG": "BOP", "PALEDANG": "BOP",
            "CIOMAS": "COS", "MASENG": "MSG", "CIGOMBONG": "CGB",
            "CICURUG": "CCR", "BOJONGGEDE": "BJD",
        }
        short_codes = {"BOO", "CLT", "BTT", "BOP", "COS", "MSG", "CGB", "CCR", "BJD"}

        matches = []
        # Short code 3 huruf
        for code in short_codes:
            for m in re.finditer(r'\b' + re.escape(code) + r'\b', text):
                matches.append((m.start(), code))
        # Nama panjang
        for full, code in loc_map.items():
            for m in re.finditer(r'\b' + re.escape(full) + r'\b', text):
                matches.append((m.start(), code))

        if not matches:
            return get_standard_loc(text)

        matches.sort(key=lambda x: x[0])
        seen = set()
        found = []
        for pos, code in matches:
            if code not in seen:
                seen.add(code)
                found.append(code)
            if len(found) >= 2:
                break
        return "-".join(found)

    def extract_radio_waystation_assets(text):
        result = []
        loc_codes = set(BTP_JAK_LOCS + BTP_BD_LOCS)
        stop_words = {
            "LOKASI", "DISETUJUI", "DISETUJUL", "PISETUJUI", "DIKETAHUI", "TANGGAL",
            "PERIODE", "PERAWATAN", "DILAKSANAKAN", "OLEH", "NO", "SC"
        }
        for match in re.finditer(r'\bTLK\d+\s*:\s*(WS\b[^:]+)', text):
            tokens = re.findall(r'[A-Z0-9]+', match.group(1))
            aid_parts = []
            loc = ""
            for token in tokens:
                if token in stop_words:
                    break
                if token in loc_codes or token in {"BOGOR", "CILEBUT", "BATUTULIS", "BOGORPALEDANG", "PALEDANG", "CIOMAS", "MASENG", "CIGOMBONG"}:
                    loc = get_standard_loc(token)
                    break
                aid_parts.append(token)
            if aid_parts and aid_parts[0] == "WS":
                if not loc:
                    loc = get_standard_loc(text[match.end():])
                if loc == "LOKASI":
                    loc = get_standard_loc(text)
                aid = " ".join(aid_parts)
                if not any(a["id"] == aid and a["loc"] == loc for a in result):
                    result.append({"id": aid, "loc": loc})
        if not result:
            result.append({"id": "WS", "loc": get_standard_loc(text)})
        return result

    # GERBANG A: OCR-based detection — POINT LOCK prioritas di atas WESEL (keyword WESEL ada di POINT LOCK)
    if any(x in text_flat for x in ["POINT LOCK", "PENGAMAN WESEL"]):
        kode, kategori = "BPBYE12", "POINT LOCK"
        w_matches = extract_wesel_ids(text_flat, allow_generic=True)
        if w_matches:
            for w in w_matches:
                w_loc = None
                for line in text_crop.split('\n'):
                    if w in line and 'PERAWATAN' not in line.upper():
                        w_loc = get_dual_loc(line)
                        break
                loc = w_loc or extract_funcloc(text_crop) or get_standard_loc(text_flat)
                assets.append({"id": w, "loc": loc})
        else:
            loc = extract_funcloc(text_crop) or get_standard_loc(text_flat)
            assets.append({"id": "PL", "loc": loc})

    elif "PERAWATAN WESEL" in text_flat or "PENGGERAK WESEL" in text_flat:
        kode, kategori = "BPBYE1", "WESEL"
        w_matches = extract_wesel_ids(text_flat, allow_generic=True)
        
        if w_matches:
            for w in w_matches:
                w_loc = None
                for line in text_crop.split('\n'):
                    if w in line and 'PERAWATAN' not in line.upper():
                        w_loc = get_dual_loc(line)
                        break
                loc = w_loc or extract_funcloc(text_crop) or get_standard_loc(text_flat)
                assets.append({"id": w, "loc": loc})
        else:
            loc = extract_funcloc(text_crop) or get_standard_loc(text_flat)
            assets.append({"id": "W_UNKNOWN", "loc": loc})

    elif "PERALATAN DALAM PERSINYALAN ELEKTRIK" in text_flat:
        kode, kategori = "BPBYE2", "PDSE"
        loc = extract_funcloc(text_crop) or get_standard_loc(text_flat)
        assets.append({"id": "", "loc": loc})
    elif "TELEKOMUNIKASI DI PINTU PERLINTASAN" in text_flat:
        kode, kategori = "BPBKS17", "PTPP"
        text_clean = re.sub(r'\bJPL\d+\b', '', text_flat)  # filter system code JPL10506
        # Truncate di table boundary (NO ITEM / ITEM PERAWATAN) hindari false positive JPL dari tabel
        for marker in ('NO ITEM', 'ITEM PERAWATAN'):
            idx = text_clean.upper().find(marker)
            if idx >= 0:
                text_clean = text_clean[:idx]
                break
        assets = extract_jpl_assets(text_clean, text_flat, multi_word=False)
        # Dedup JPL dengan ID sama — gabungkan lokasi berbeda jadi satu
        dedup = {}
        for a in assets:
            aid = a["id"]
            loc = a["loc"]
            if aid not in dedup:
                dedup[aid] = {"id": aid, "loc": loc}
            else:
                existing = dedup[aid]["loc"]
                if existing != loc:
                    # merge lokasi
                    all_locs = list(dict.fromkeys(existing.split("-") + loc.split("-")))
                    dedup[aid]["loc"] = "-".join(all_locs)
        assets = list(dedup.values())
        # PTPP: 1 foto = 1 output file. Prefer JPL dari filename (atasi false positive OCR)
        fn_match = re.search(r'JPL\s+([A-Z0-9]+)', filename_upper)
        if fn_match:
            fn_jpl = f"JPL {fn_match.group(1)}"
            fn_loc = get_standard_loc(filename_upper)
            ocr_match = [a for a in assets if a["id"] == fn_jpl]
            if ocr_match:
                assets = [ocr_match[0]]
            else:
                assets = [{"id": fn_jpl, "loc": fn_loc or ""}]
        elif assets:
            assets = [assets[0]]

    elif "PINTU PERLINTASAN" in text_flat and "TELEKOMUNIKASI" not in text_flat:
        kode, kategori = "BPBKS17", "PINTU PERLINTASAN"
        text_clean = re.sub(r'\bJPL\d+\b', '', text_flat)
        assets = extract_jpl_assets(text_clean, text_flat, multi_word=True)
        if not assets:
            # Fallback: ambil JPL dari filename
            fn_match = re.search(r'JPL\s+([A-Z0-9]+)', filename_upper)
            if fn_match:
                fn_jpl = f"JPL {fn_match.group(1)}"
                fn_loc = get_standard_loc(filename_upper)
                assets = [{"id": fn_jpl, "loc": fn_loc or ""}]
            else:
                loc = extract_funcloc(text_crop) or get_standard_loc(text_flat)
                assets = [{"id": "", "loc": loc}]

    elif "TELEKOMUNIKASI DI STASIUN" in text_flat:
        kode, kategori = "BPBKS15", "PTDS"
        loc = extract_funcloc(text_crop) or get_standard_loc(text_flat)
        assets.append({"id": "", "loc": loc})

    elif "TELEKOMUNIKASI DI LUAR STASIUN" in text_flat:
        kode, kategori = "BPBKS16", "PTLS"
        loc = get_ptls_loc(text_flat, text_crop)
        assets.append({"id": "", "loc": loc})

    elif "RADIO BASESTATION" in text_flat:
        loc = extract_funcloc(text_crop) or get_standard_loc(text_flat)
        if "TAIT" in text_flat:
            kode, kategori = "BPBKF3", "RADIO BASESTATION TAIT"
        elif "DIGITAL" in text_flat:
            kode, kategori = "BPBKF2", "RADIO BASESTATION DIGITAL"
        else:
            kode, kategori = "BPBKF1", "RADIO BASESTATION"
        assets.append({"id": "", "loc": loc})

    elif "SISTEM WAYSTATION" in text_flat or "RADIO WAYSTATION" in text_flat or "RADIO WAY STATION" in text_flat:
        if "SISTEM WAYSTATION" in text_flat:
            kode, kategori = "BPBKS5", "SISTEM WAYSTATION"
            loc = extract_funcloc(text_crop) or get_standard_loc(text_flat)
            assets.append({"id": "", "loc": loc})
        else:
            kode, kategori = "BPBKS16", "RADIO WAYSTATION"
            assets = extract_radio_waystation_assets(text_flat)

    elif "CTC" in text_flat and "CTS" in text_flat:
        kode, kategori = "BPBYE4", "CTC-CTS"
        loc = extract_funcloc(text_crop) or get_standard_loc(text_flat)
        assets.append({"id": "", "loc": loc})

    elif "PERAWATAN AXLE COUNTER" in text_flat:
        kode, kategori = "BPBYE7", "AXLE COUNTER"
        
        # Cari format ZP dengan angka/huruf aset, atau kode lokasi menempel (ZP41SRP, ZPA SDM).
        zp_matches = []
        for match in re.finditer(r'\bZP\s?(\d{1,3})([A-Z]{1,2})?\b', text_flat):
            num, suffix = match.groups()
            suffix = suffix or ""
            # Hapus false positive "ZP 43" (yang biasanya ZP43 atau ZP 43) karena itu tipe alat.
            if num == "43" and not suffix:
                continue
            zp_matches.append((f"ZP {num}{suffix}", match.start()))

        if zp_matches:
            seen_zp = set()
            for z_clean, pos in zp_matches:
                if z_clean in seen_zp:
                    continue
                seen_zp.add(z_clean)
                # Cari baris di text_crop yang beneran baris aset
                zp_loc = None
                for line in text_crop.split('\n'):
                    if z_clean in line and 'PERAWATAN' not in line.upper():
                        zp_loc = get_dual_loc(line)
                        break
                loc = zp_loc or extract_funcloc(text_crop) or get_dual_loc(text_flat)
                assets.append({"id": z_clean, "loc": loc})
        else:
            loc = extract_funcloc(text_crop) or get_dual_loc(text_flat)
            assets.append({"id": "ZP", "loc": loc})

    elif "PERAGA SINYAL" in text_flat or "PERAWATAN SINYAL" in text_flat:
        
        kode, kategori = "BPBYE3", "PERAGA SINYAL"
        # Cari Sinyal: B.210, UB.210, B210, JL62B, B201, L22, S11A, dll
        # Variasi di KAI: SINYAL BLOK B.210, SINYAL ULANG BLOK UB.210, JL62B, B201
        signal_matches = SIGNAL_PATTERN.findall(text_flat)
        
        valid_signals = []
        for s in signal_matches:
            s_clean = s.replace(" ", "").replace(".", "")
            # Skip false positive: "M314" (OCR artifact dari "MJ14")
            if re.match(r'^M\d+$', s_clean):
                continue
            # Sinyal harus punya huruf awal B/L/J/M/S/X/U dan setelah itu ada angkanya (termasuk MJ, MJ20, dll)
            if re.match(r'^[BJLMSXU]+\d+', s_clean):
                valid_signals.append(s_clean)
                
        if valid_signals:
            unique_sig = get_unique_list(valid_signals)
            for s in unique_sig:
                # Cari baris di text_crop yang beneran baris aset
                sig_loc = None
                for line in text_crop.split('\n'):
                    line_flat = line.replace(".", "").replace(" ", "")
                    if (s in line or s in line_flat) and 'PERAWATAN' not in line.upper():
                        sig_loc = get_dual_loc(line)
                        break
                loc = sig_loc or get_dual_loc(text_flat)
                assets.append({"id": s, "loc": loc})
        else:
            loc = get_dual_loc(text_flat)
            assets.append({"id": "", "loc": loc})

    elif "CATU DAYA" in text_flat:
        # Deteksi subtype dari baris CDA: GENSET/UPS/BATTERE ER SINYAL atau ER RADIO
        cda_lines = [l for l in text_crop.split('\n') if 'CDA' in l.upper()]
        combined_cda = ' '.join(cda_lines).upper()
        if 'ER RADIO' in combined_cda:
            kode, kategori = "BPBYE14", "CATU DAYA ER RADIO"
        elif 'ER SINYAL' in combined_cda:
            kode, kategori = "BPBYE14", "CATU DAYA ER SINYAL"
        else:
            kode, kategori = "BPBYE14", "CATU DAYA"
        loc = extract_funcloc(text_crop) or get_dual_loc(text_flat)
        assets.append({"id": "", "loc": loc})

    elif "SERAT OPTIK" in text_flat and re.search(r'\bER\b', text_flat):
        # ER/ER TELKOM: parse first OTB from filename, location from OCR
        kode, kategori = "BPBKF4", "SERAT OPTIK"
        
        # Extract ER type from filename + OCR
        er_type = "ER"
        filename_upper = filename_upper  # already upper
        # Check OCR for TELKOM keyword
        has_telkom_ocr = "TELKOM" in text_flat
        # Check filename for Telkom variants
        has_telkom_fn = "TELKOM" in filename_upper or "RADIO" in filename_upper
        if has_telkom_ocr or has_telkom_fn:
            er_type = "ER TELKOM"
        
        # Extract OTB number from filename
        otb_match = re.search(r'OTB\s+(\d+)', filename_upper)
        first_otb = int(otb_match.group(1)) if otb_match else 1
        
        # Extract ALL OTB numbers from OCR to compute range
        all_otb_nums = [int(m.group(1)) for m in re.finditer(r'OTB\s+(\d+)', text_flat)]
        if all_otb_nums:
            otb_min = min(all_otb_nums)
            otb_max = max(all_otb_nums)
        else:
            # Fallback: use first_otb from filename
            otb_min = first_otb
            otb_max = first_otb
        
        # Extract location from OCR (first OTB line)
        loc = None
        for line in text_crop.split('\n'):
            ul = line.upper()
            if 'OTB' in ul and 'ER' in ul:
                parts = ul.split(':')
                if len(parts) >= 2:
                    after = parts[-1].strip()
                    after = re.sub(r'OTB\s+FO\s+\d+\s*', '', after)
                    after = re.sub(r'OTB\s+\d+\s*', '', after)
                    after = re.sub(r'TRA\d+\s*:\s*', '', after)
                    # Strip ER TELKOM or ER prefix
                    after = re.sub(r'^ER\s+TELKOM\s+', '', after)
                    after = re.sub(r'^ER\s+', '', after)
                    loc = after.strip()
                    if loc:
                        break
        
        if not loc:
            fn_loc = get_standard_loc(filename_upper)
            loc = fn_loc or extract_funcloc(text_crop) or get_standard_loc(text_flat)
        
        # Return metadata for grouping in processing loop
        assets = [{
            "id": er_type,
            "loc": loc,
            "first_otb": first_otb,
            "er_type": er_type,
            "otb_min": otb_min,
            "otb_max": otb_max
        }]

    elif "SERAT OPTIK" in text_flat:
        # SERAT OPTIK JPL: scan OCR TRA lines for multiple JPLs
        # SERAT OPTIK BULANAN non-JPL: group by location, sequence from filename _01, _02
        kode, kategori = "BPBKF4", "SERAT OPTIK"
        fn_loc = get_standard_loc(filename_upper)
        loc = fn_loc or extract_funcloc(text_crop) or get_standard_loc(text_flat)
        
        # Scan OCR for TRA lines with JPL numbers (handles 2 JPL in 1 file e.g. JPL 15 + JPL 16, or BNR + 07)
        jpl_set = set()
        for ocr_line in text_crop.split('\n'):
            ul = ocr_line.upper().strip()
            # Match TRAxxxxx : OTB FO JPL XXX
            m = re.search(r'TRA\d+\s*:\s*OTB\s+FO\s+JPL\s+(\S+)', ul)
            if m:
                jpl_id = m.group(1)
                # Strip trailing location like CGB, BOO-BOP
                jpl_id = re.sub(r'\s+[A-Z][A-Z].*', '', jpl_id)
                jpl_set.add(jpl_id)
        
        if jpl_set:
            # Multiple JPLs from OCR → multiple assets
            assets = []
            for jpl_id in sorted(jpl_set):
                assets.append({"id": f"JPL {jpl_id}", "loc": loc})
        else:
            # Fallback: filename-based
            fn_match = re.search(r'JPL\s+(\d+[A-Z]*)', filename_upper)
            if fn_match:
                assets = [{"id": f"JPL {fn_match.group(1)}", "loc": loc or ""}]
            else:
                # Non-JPL SERAT OPTIK (bulanan): extract sequence from filename _01, _02
                seq_match = re.search(r'_0*(\d+)\s', filename_upper)
                seq_num = int(seq_match.group(1)) if seq_match else 1
                assets = [{
                    "id": "", 
                    "loc": loc,
                    "seq_num": seq_num,
                    "is_bulanan": True
                }]

    # GERBANG B: filename-based detection
    if not assets:
        loc = get_standard_loc(filename_upper)
        if "WESEL ELEKTRIK" in filename_upper:
            kode, kategori = "BPBYE1", "WESEL"
            w_matches = extract_wesel_ids(filename_upper)
            if w_matches:
                for w in w_matches: assets.append({"id": w, "loc": loc})
            else: assets.append({"id": "W_UNKNOWN", "loc": loc})
        elif "POINT LOCK" in filename_upper:
            kode, kategori = "BPBYE12", "POINT LOCK"
            w_matches = extract_wesel_ids(filename_upper)
            if w_matches:
                for w in w_matches: assets.append({"id": w, "loc": loc})
            else:
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
        elif "SINYAL" in filename_upper:
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
            if "ER TELKOM" in filename_upper:
                assets.append({"id": "ER TELKOM", "loc": loc})
            elif " ER " in filename_upper or filename_upper.endswith(" ER"):
                assets.append({"id": "ER", "loc": loc})
            else:
                assets.append({"id": "", "loc": loc})
        elif "CTC" in filename_upper and "CTS" in filename_upper:
            kode, kategori = "BPBYE4", "CTC-CTS"
            assets.append({"id": "", "loc": loc})
        elif "RADIO BASESTATION" in filename_upper:
            if "TAIT" in filename_upper:
                kode, kategori = "BPBKF3", "RADIO BASESTATION TAIT"
            elif "DIGITAL" in filename_upper:
                kode, kategori = "BPBKF2", "RADIO BASESTATION DIGITAL"
            else:
                kode, kategori = "BPBKF1", "RADIO BASESTATION"
            assets.append({"id": "", "loc": loc})
        elif "SISTEM WAYSTATION" in filename_upper:
            kode, kategori = "BPBKS5", "SISTEM WAYSTATION"
            assets.append({"id": "", "loc": loc})
        elif "RADIO WAYSTATION" in filename_upper or "RADIO WAY STATION" in filename_upper:
            kode, kategori = "BPBKS16", "RADIO WAYSTATION"
            assets.append({"id": "WS", "loc": loc})
        elif "PTPP" in filename_upper or "PINTU PERLINTASAN" in filename_upper:
            kode, kategori = "BPBKS17", "PTPP"
            fn_match = re.search(r'JPL\s+([A-Z0-9]+)', filename_upper)
            if fn_match:
                assets = [{"id": f"JPL {fn_match.group(1)}", "loc": loc or ""}]
            else:
                assets = [{"id": "", "loc": loc or ""}]

    return kode, kategori, assets

def get_btp(loc):
    if loc in BTP_JAK_LOCS:
        return "BTP JAK"
    return "BTP BD"

def build_filename(prefix_periode, kode, jenis, identitas, tgl_full, format_bd):
    # Ganti label SINYAL di output agar sesuai format
    identitas = identitas.replace("PERAGA SINYAL", "SINYAL").replace("PERAWATAN SINYAL", "SINYAL")
        
    if format_bd:
        resor = "Resor 1.21 Boo"
        return f"{prefix_periode}_{resor}_{kode}_{jenis}_{identitas}_{tgl_full}.pdf"
    else:
        return f"{jenis.upper()} {identitas} {tgl_full}.pdf"


def read_input_file(entry):
    if isinstance(entry, tuple):
        return entry[0], entry[1]

    if hasattr(entry, "filename") and hasattr(entry, "read"):
        return entry.filename, entry.read()

    path = os.fspath(entry)
    with open(path, "rb") as f_in:
        return os.path.basename(path), f_in.read()


def process_pdf_entries(entries, jenis_kegiatan="Perawatan", instansi="BTP JAK"):
    format_bd = (instansi == "BTP BD")
    zip_buffer = BytesIO()
    processed_files = []
    duplicate_errors = []
    unique_filenames = set()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_f:
        for entry in entries:
            filename, file_bytes = read_input_file(entry)
            if not filename.lower().endswith(".pdf"):
                continue

            name_only = filename.upper()
            tgl_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', name_only)
            if not tgl_match:
                duplicate_errors.append(f"ERROR|{filename}|Format tanggal tidak ditemukan.")
                continue

            tgl_full = tgl_match.group(0)
            bln_angka = str(int(tgl_match.group(2)))
            thn_angka = tgl_match.group(3)
            prefix_periode = f"{thn_angka}-{bln_angka}"

            try:
                text_crop = process_pdf_ocr(file_bytes)
                text_flat = re.sub(r'\s+', ' ', text_crop)
                kode, kategori, assets = detect_doc(text_flat, text_crop, name_only)

                if not assets:
                    duplicate_errors.append(f"ERROR|{filename}|Jenis dokumen tidak terdeteksi.")
                    continue

                for asset in assets:
                    aid = asset["id"]
                    loc = asset["loc"]
                    identitas = f"{kategori} {aid} {loc}".strip() if aid else f"{kategori} {loc}".strip()
                    identitas = re.sub(r'\s+', ' ', identitas).strip()
                    new_name = build_filename(prefix_periode, kode, jenis_kegiatan, identitas, tgl_full, format_bd)
                    new_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)

                    # Serat Optik: duplikat langsung skip (1 file per aset)
                    if new_name not in unique_filenames:
                        zip_f.writestr(new_name, file_bytes)
                        processed_files.append(new_name)
                        unique_filenames.add(new_name)
                    else:
                        duplicate_errors.append(f"WARNING|{filename}|Duplikat: {new_name}")
            except Exception as e:
                duplicate_errors.append(f"ERROR|{filename}|Error: {e}")

    zip_bytes = b""
    if processed_files:
        zip_buffer.seek(0)
        zip_bytes = zip_buffer.getvalue()

    return {
        "success": bool(processed_files),
        "processed_count": len(processed_files),
        "files": processed_files,
        "errors": duplicate_errors,
        "zip_bytes": zip_bytes,
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_files():
    log(f"Request files keys: {list(request.files.keys())}")
    log(f"Form keys: {list(request.form.keys())}")

    if 'files[]' not in request.files:
        return jsonify({'error': 'No files uploaded - field name files[] not found'}), 400
        
    uploaded_files = request.files.getlist('files[]')
    jenis_kegiatan = request.form.get('jenis_kegiatan', 'Perawatan')
    instansi = request.form.get('instansi', 'BTP JAK')
    format_bd = (instansi == 'BTP BD')  # Dihitung sekali, dipakai di semua iterasi

    zip_buffer = BytesIO()
    processed_files = []
    duplicate_errors = []
    unique_filenames = set()

    # ===== FIRST PASS: Collect all SO ER assets for grouping =====
    so_er_assets = []  # List of (file_bytes, fname, first_otb, er_type, loc, kode, kategori, tgl_full, prefix_periode, jenis_kegiatan, format_bd)
    so_bulanan_assets = []  # List of (file_bytes, fname, seq_num, loc, kode, kategori, tgl_full, prefix_periode, jenis_kegiatan, format_bd)
    other_assets = []  # List of (file_bytes, fname, identitas, kode, kategori, tgl_full, prefix_periode, jenis_kegiatan, format_bd)

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_f:
        for f in uploaded_files:
            fname = f.filename or ''
            if not fname.lower().endswith('.pdf'):
                log(f"  SKIP (not PDF): {fname}")
                continue
                
            name_only = f.filename.upper()
            # Format 1: DD-MM-YYYY
            tgl_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', name_only)
            # Format 2: Indonesia "TGL 12 JANUARI 2025"
            if not tgl_match:
                bulan_map = {
                    'JANUARI':'1','FEBRUARI':'2','MARET':'3','APRIL':'4',
                    'MEI':'5','JUNI':'6','JULI':'7','AGUSTUS':'8',
                    'SEPTEMBER':'9','OKTOBER':'10','NOVEMBER':'11','DESEMBER':'12'
                }
                tgl_match = re.search(r'(?:^|\D)(\d{1,2})\s+(JANUARI|FEBRUARI|MARET|APRIL|MEI|JUNI|JULI|AGUSTUS|SEPTEMBER|OKTOBER|NOVEMBER|DESEMBER)\s+(\d{4})\b', name_only)

            if not tgl_match:
                duplicate_errors.append(f"ERROR|{f.filename}|Format tanggal tidak ditemukan.")
                continue

            # Parsing: cek format berdasarkan isi group(2)
            if tgl_match.group(2).isdigit():
                # Format DD-MM-YYYY
                tgl_full = tgl_match.group(0)
                bln_angka = str(int(tgl_match.group(2)))
                thn_angka = tgl_match.group(3)
            else:
                # Format Indonesia
                day = tgl_match.group(1)
                bln_angka = bulan_map.get(tgl_match.group(2).strip().upper(), '1')
                thn_angka = tgl_match.group(3)
                tgl_full = f"{int(day):02d}-{int(bln_angka):02d}-{thn_angka}"

            prefix_periode = f"{thn_angka}-{bln_angka}"

            try:
                log(f"  Processing: {f.filename}")
                file_bytes = f.read()
                log(f"  OCR...")
                text_crop = process_pdf_ocr(file_bytes)
                log(f"  OCR done ({len(text_crop)} chars)")
                text_flat = re.sub(r'\s+', ' ', text_crop)

                kode, kategori, assets = detect_doc(text_flat, text_crop, name_only)
                log(f"  detect_doc: kode={kode} kategori={kategori} assets={len(assets)}")

                if not assets:
                    duplicate_errors.append(f"ERROR|{f.filename}|Jenis dokumen tidak terdeteksi.")
                    continue

                # Proses setiap aset yang ditemukan di dokumen (multi-aset support)
                for asset in assets:
                    aid = asset["id"]
                    loc = asset["loc"]
                    
                    identitas = f"{kategori} {aid} {loc}".strip() if aid else f"{kategori} {loc}".strip()
                    identitas = re.sub(r'\s+', ' ', identitas).strip()

                    # Check if this is SERAT OPTIK ER (has first_otb and er_type metadata)
                    if "first_otb" in asset and "er_type" in asset:
                        # SO ER - defer writing, collect for grouping
                        so_er_assets.append((
                            file_bytes, fname, asset["first_otb"], asset["er_type"], loc,
                            kode, kategori, tgl_full, prefix_periode, jenis_kegiatan, format_bd,
                            asset.get("otb_min", asset["first_otb"]), asset.get("otb_max", asset["first_otb"])
                        ))
                    # Check if this is SERAT OPTIK BULANAN non-JPL (has is_bulanan)
                    elif asset.get("is_bulanan"):
                        # Bulanan - defer writing, collect for grouping by loc+seq_num
                        so_bulanan_assets.append((
                            file_bytes, fname, asset["seq_num"], loc,
                            kode, kategori, tgl_full, prefix_periode, jenis_kegiatan, format_bd
                        ))
                    else:
                        # Other types - process normally
                        other_assets.append((
                            file_bytes, fname, identitas,
                            kode, kategori, tgl_full, prefix_periode, jenis_kegiatan, format_bd
                        ))

            except Exception as e:
                duplicate_errors.append(f"ERROR|{f.filename}|Error: {e}")

        # ===== PROCESS OTHER ASSETS (normal flow) =====
        for (file_bytes, fname, identitas, kode, kategori, tgl_full, prefix_periode, jenis_kegiatan, format_bd) in other_assets:
            new_name = build_filename(prefix_periode, kode, jenis_kegiatan, identitas, tgl_full, format_bd)
            new_name = re.sub(r'[<>:\"/\\|?*]', '_', new_name)
            
            if new_name not in unique_filenames:
                zip_f.writestr(new_name, file_bytes)
                processed_files.append(new_name)
                unique_filenames.add(new_name)
            else:
                duplicate_errors.append(f"WARNING|{fname}|Duplikat: {new_name}")

        # ===== PROCESS SO ER ASSETS (grouped by er_type|location, sorted by first_otb) =====
        # Group by er_type|location
        so_er_groups = {}
        for item in so_er_assets:
            (file_bytes, fname, first_otb, er_type, loc,
             kode, kategori, tgl_full, prefix_periode, jenis_kegiatan, format_bd,
             otb_min, otb_max) = item
            key = f"{er_type}|{loc}"
            if key not in so_er_groups:
                so_er_groups[key] = []
            so_er_groups[key].append(item)

        # Write each file with OTB range in name, duplicate handler catches same range
        for key, items in so_er_groups.items():
            items.sort(key=lambda x: x[2])  # sort by first_otb
            for idx, item in enumerate(items):
                (file_bytes, fname, first_otb, er_type, loc,
                 kode, kategori, tgl_full, prefix_periode, jenis_kegiatan, format_bd,
                 otb_min, otb_max) = item
                
                # Build identitas with OTB range: "SERAT OPTIK OTB {min}-{max} ER|ER TELKOM {lokasi}"
                range_str = f"{otb_min}-{otb_max}" if otb_min != otb_max else str(otb_min)
                identitas = f"{kategori} OTB {range_str} {er_type} {loc}".strip()
                identitas = re.sub(r'\s+', ' ', identitas)
                
                new_name = build_filename(prefix_periode, kode, jenis_kegiatan, identitas, tgl_full, format_bd)
                new_name = re.sub(r'[<>:\"/\\|?*]', '_', new_name)
                
                if new_name not in unique_filenames:
                    zip_f.writestr(new_name, file_bytes)
                    processed_files.append(new_name)
                    unique_filenames.add(new_name)
                else:
                    duplicate_errors.append(f"WARNING|{fname}|Duplikat: {new_name}")

        # ===== PROCESS SO BULANAN ASSETS (grouped by location, sorted by seq_num) =====
        bulanan_groups = {}
        for item in so_bulanan_assets:
            (file_bytes, fname, seq_num, loc,
             kode, kategori, tgl_full, prefix_periode, jenis_kegiatan, format_bd) = item
            key = loc
            if key not in bulanan_groups:
                bulanan_groups[key] = []
            bulanan_groups[key].append(item)

        for key, items in bulanan_groups.items():
            items.sort(key=lambda x: x[2])  # sort by seq_num
            for idx, item in enumerate(items):
                (file_bytes, fname, seq_num, loc,
                 kode, kategori, tgl_full, prefix_periode, jenis_kegiatan, format_bd) = item
                
                suffix = f" ({idx + 1})" if idx > 0 else ""
                identitas = f"{kategori} {loc}".strip()
                identitas = re.sub(r'\s+', ' ', identitas) + suffix
                
                new_name = build_filename(prefix_periode, kode, jenis_kegiatan, identitas, tgl_full, format_bd)
                new_name = re.sub(r'[<>:\"/\\|?*]', '_', new_name)
                
                if new_name not in unique_filenames:
                    zip_f.writestr(new_name, file_bytes)
                    processed_files.append(new_name)
                    unique_filenames.add(new_name)
                else:
                    duplicate_errors.append(f"WARNING|{fname}|Duplikat: {new_name}")

    if not processed_files:
        logerr(f"FAILED - all {len(uploaded_files)} files failed: {duplicate_errors}")
        return jsonify({'error': 'Tidak ada file yang berhasil diproses', 'details': duplicate_errors}), 400

    zip_buffer.seek(0)

    # Kirim ZIP langsung, embed metadata di response headers
    resp = send_file(zip_buffer, as_attachment=True, download_name='Hasil_Rename.zip', mimetype='application/zip')
    resp.headers['X-Processed-Count'] = str(len(processed_files))
    # Encode custom headers to ASCII-safe to prevent latin-1 errors
    x_files = '||'.join(processed_files)
    x_errors = '||'.join(duplicate_errors)
    resp.headers['X-Files'] = x_files
    resp.headers['X-Errors'] = x_errors
    return resp

@app.route('/download/<download_id>')
def download(download_id):
    zip_path = _downloads.pop(download_id, None)
    if zip_path and os.path.exists(zip_path):
        @after_this_request
        def cleanup(response):
            try:
                os.remove(zip_path)
            except OSError:
                pass
            return response

        return send_file(zip_path, as_attachment=True, download_name='Hasil_Rename.zip', mimetype='application/zip')
    return "File tidak ditemukan", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8501))
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
