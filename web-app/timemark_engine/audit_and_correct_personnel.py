import sys
import os
import re
import json
import random
from pathlib import Path
from datetime import datetime
import argparse

import fitz

# Ensure scripts folder is on path
sys.path.insert(0, str(Path(__file__).parent))
try:
    from employee_manager import load_pegawai_config, replace_page1_employee_names
except ImportError:
    load_pegawai_config = None
    replace_page1_employee_names = None


def get_roster_sets(pegawai_cfg: dict = None):
    if pegawai_cfg is None:
        if load_pegawai_config:
            pegawai_cfg = load_pegawai_config()
        else:
            pegawai_cfg = {}

    kaur_map = {}  # uppercase name -> dict {nama, nipp, no_sc}
    pnc_map = {}   # uppercase name -> dict {nama, nipp, no_sc}

    for k in pegawai_cfg.get('kaur', []):
        nm = k.get('nama', '').strip().upper()
        if nm:
            kaur_map[nm] = {
                'nama': nm,
                'nipp': k.get('nipp', ''),
                'no_sc': k.get('no_sc', '')
            }

    for p in pegawai_cfg.get('pnc', []):
        nm = p.get('nama', '').strip().upper()
        if nm:
            pnc_map[nm] = {
                'nama': nm,
                'nipp': p.get('nipp', ''),
                'no_sc': p.get('no_sc', '')
            }

    return kaur_map, pnc_map, pegawai_cfg


def extract_page_ocr_text(page: fitz.Page) -> str:
    """Fallback OCR extraction for image-only/scanned PDF pages."""
    try:
        import pytesseract
        from PIL import Image
        import io

        tesseract_bin = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if tesseract_bin.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(tesseract_bin)

        pix = page.get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        raw_ocr = pytesseract.image_to_string(img)

        # Normalize common OCR misreadings for Indonesian railway names:
        # e.g. DED! -> DEDI, pipes/1 inside letters -> I
        t = re.sub(r'(?<=[A-Za-z])!', 'I', raw_ocr)
        t = re.sub(r'!(?=[A-Za-z])', 'I', t)
        t = re.sub(r'(?<=[A-Za-z])[|1](?=[A-Za-z])', 'I', t)
        return t.upper()
    except Exception:
        return ""


def extract_personnel_from_pdf(doc: fitz.Document, kaur_map: dict, pnc_map: dict, return_unauthorized: bool = False):
    if len(doc) == 0:
        return ([], [], [], []) if return_unauthorized else ([], [], [])

    text = doc[0].get_text('text').upper()
    # OCR Fallback if page 1 is scanned or contains no digital text
    if len(text.strip()) < 10:
        ocr_text = extract_page_ocr_text(doc[0])
        if ocr_text:
            text = ocr_text

    lines = [re.sub(r'\s+', ' ', line).strip(' :;,') for line in text.splitlines()]
    start = None
    for i, line in enumerate(lines):
        if re.search(r'^DILAKSANAKAN\s+OLEH', line):
            start = i
            break
        if line == 'DILAKSANAKAN' and i + 1 < len(lines) and re.match(r'^OLEH', lines[i + 1]):
            start = i + 1
            break

    found_kaur, found_pnc, names = [], [], []
    seen = set()
    roster = list(kaur_map.items()) + list(pnc_map.items())
    stop_words = {
        'TIDAK', 'MIRING', 'BERSIH', 'ADA', 'RETAK', 'KOTOR', 'TERTAMBAT',
        'KUAT', 'DAN', 'RATA', 'BAIK', 'KENCANG', 'YA', 'TIDAK ADA',
        'LOKASI', 'CILEBUT', 'BOGOR', 'CIOMAS', 'BOO', 'CLT', 'COS', 'BOP', 'BTT', 'MSG', 'CGB',
        'DISETUJUI', 'DIKETAHUI', 'DISETUJUI OLEH', 'DIKETAHUI OLEH', 'PRP', 'NIPP', 'TANGGAL', 'TGL',
        'HASIL', 'KETERANGAN', 'KEGIATAN', 'REFERENSI', 'STANDAR', 'ITEM',
        'NO', 'SC', 'NO.', 'SC.'
    }
    unauthorized = []
    section_lines = []

    def make_roster_pat(n: str) -> str:
        clean_chars = [re.escape(c) for c in re.sub(r'[^A-Z]', '', n.upper())]
        return r'\b' + r'\s*'.join(clean_chars) + r'\b'

    if start is not None:
        for line in lines[start + 1:]:
            if re.search(r'^(DISETUJUI|DIKETAHUI)\b', line) or re.search(r'\b(DISETUJUI\s+OLEH|DIKETAHUI\s+OLEH)\b', line):
                break
            if re.match(r'^(ITEM\s+PERAWATAN|NOMOR\s+ASET|NOMOR\s+SINYAL)', line.strip(), re.I):
                break
            if re.match(r'^(NO\.?\s*SC|NO\b|SC\b)', line.strip(), re.I):
                continue
            if line and not re.match(r'^(PRP|NIPP)\b', line.strip(), re.I):
                section_lines.append(line)
        section = '\n'.join(section_lines)

        matched_roster = []
        for name, obj in roster:
            pattern = make_roster_pat(name)
            if re.search(pattern, section) and name not in seen:
                seen.add(name)
                matched_roster.append((name, obj))
                target = found_kaur if name in kaur_map else found_pnc
                if obj['nama'] not in {x['nama'] for x in target}:
                    target.append(obj)

        for name, _ in matched_roster:
            names.append(name)

    unauthorized = []
    for raw in section_lines:
        for segment in re.split(r'[,;]', raw):
            candidate = re.sub(r'[^A-Z .-]', ' ', segment).strip()
            candidate = re.sub(r'\s+', ' ', candidate).strip(' .,-')
            words = candidate.split()
            if not (1 <= len(words) <= 4) or any(word in stop_words for word in words):
                continue
            if not re.fullmatch(r'[A-Z][A-Z .-]*', candidate):
                continue
            contained_roster = [name for name, _ in roster
                                if re.search(make_roster_pat(name), candidate)]
            if contained_roster:
                for matched_name in contained_roster:
                    obj = kaur_map.get(matched_name) or pnc_map.get(matched_name)
                    if obj:
                        target = found_kaur if matched_name in kaur_map else found_pnc
                        if obj['nama'] not in {x['nama'] for x in target}:
                            target.append(obj)
                if candidate not in seen:
                    seen.add(candidate)
                    names.append(candidate)
            else:
                if candidate not in unauthorized:
                    unauthorized.append(candidate)

    # Some PDFs place personnel below the checklist, after a second NO. SC.
    # Detect name lines followed by PRP/NIPP identifiers across the full page.
    if not names:
        page_lines = [re.sub(r'\s+', ' ', line).strip(' :;,') for line in text.splitlines()]
        for i, line in enumerate(page_lines[:-1]):
            next_line = page_lines[i + 1]
            candidate = line.strip()
            if not re.fullmatch(r'[A-Z][A-Z .-]*', candidate):
                continue
            words = candidate.split()
            if not (1 <= len(words) <= 4) or any(word in stop_words for word in words):
                continue
            if not re.match(r'^(PRP|NIPP)\.?\s*[.\d-]+$', next_line):
                continue
            if candidate not in seen:
                seen.add(candidate)
                names.append(candidate)
                for r_name, r_obj in roster:
                    if re.search(make_roster_pat(r_name), candidate):
                        target = found_kaur if r_name in kaur_map else found_pnc
                        if r_obj['nama'] not in {x['nama'] for x in target}:
                            target.append(r_obj)

    # If layout separated personnel columns (e.g. CTC-CTS where KAUR/PNC appear in adjacent blocks),
    # search full page 1 text for any roster members not yet captured.
    if len(found_kaur) < 1 or len(found_pnc) < 2:
        found_names = {x['nama'] for x in found_kaur} | {x['nama'] for x in found_pnc}
        for name, obj in roster:
            if name in found_names:
                continue
            pattern = make_roster_pat(name)
            if re.search(pattern, text):
                seen.add(name)
                target = found_kaur if name in kaur_map else found_pnc
                if obj['nama'] not in {x['nama'] for x in target}:
                    target.append(obj)
                names.append(name)

    clean_technicians = [k['nama'] for k in found_kaur] + [p['nama'] for p in found_pnc]
    if not clean_technicians:
        seen_clean = set()
        for candidate in names:
            if candidate not in seen_clean:
                seen_clean.add(candidate)
                clean_technicians.append(candidate)

    if return_unauthorized:
        return found_kaur, found_pnc, clean_technicians, unauthorized
    return found_kaur, found_pnc, clean_technicians



def extract_missing_no_sc(doc: fitz.Document, personnel_names: list[str], kaur_map: dict, pnc_map: dict):
    """Return profile names whose PRP/NIPP cell is blank on the same PDF row."""
    if len(doc) == 0 or not personnel_names:
        return []
    page = doc[0]

    blocks = page.get_text('dict').get('blocks', [])
    lines_with_spans = []
    all_spans = []
    for b in blocks:
        for l in b.get('lines', []):
            line_spans = [s for s in l.get('spans', []) if s.get('text', '').strip()]
            if line_spans:
                all_spans.extend(line_spans)
                line_str = ' '.join(s['text'].strip() for s in line_spans).upper()
                lines_with_spans.append((line_str, l['bbox'], line_spans))

    names = {re.sub(r'\s+', ' ', n).strip().upper() for n in personnel_names}

    # Locate technician rows
    tech_rows = []
    matched_names = set()
    for name in names:
        norm_name = re.sub(r'[^A-Z]', '', name)
        for line_str, bbox, _ in lines_with_spans:
            clean_l = re.sub(r'[^A-Z]', '', line_str)
            if norm_name and (norm_name == clean_l or (len(norm_name) >= 6 and norm_name in clean_l)):
                tech_rows.append((name, bbox))
                matched_names.add(name)
                break

    for name in names - matched_names:
        norm_name = re.sub(r'[^A-Z]', '', name)
        for s in all_spans:
            clean_s = re.sub(r'[^A-Z]', '', s.get('text', '')).upper()
            if norm_name and (norm_name == clean_s or (len(norm_name) >= 6 and norm_name in clean_s)):
                tech_rows.append((name, s['bbox']))
                matched_names.add(name)
                break

    if not tech_rows:
        return []

    sample_y = sum((r[1][1] + r[1][3]) / 2 for r in tech_rows) / len(tech_rows)
    verticals = sorted({
        round(d['rect'].x0, 2) for d in page.get_drawings()
        if d['rect'].width < 2 and d['rect'].height > 5
        and d['rect'].y0 - 1 <= sample_y <= d['rect'].y1 + 1
    })
    name_right = max(r[1][2] for r in tech_rows)
    right_lines = [x for x in verticals if x > name_right + 2]
    separator_index = next(
        (i for i in range(len(right_lines) - 1) if right_lines[i + 1] - right_lines[i] <= 15),
        None
    )
    if separator_index is not None and separator_index + 1 < len(right_lines):
        value_left = right_lines[separator_index + 1]
    else:
        value_left = 450.0

    missing = []
    for name, bbox in tech_rows:
        profile = kaur_map.get(name) or pnc_map.get(name)
        if not profile or not profile.get('no_sc'):
            continue
        y0, y1 = bbox[1], bbox[3]
        row_values = [
            s for s in all_spans
            if s['bbox'][0] >= value_left - 15
            and s['bbox'][1] < y1 + 4
            and s['bbox'][3] > y0 - 4
        ]
        has_sc = any(
            re.match(r'^(PRP|NIPP)\.?\s*[.\d-]+$', s['text'].strip(), re.I)
            for s in row_values
        )
        if not has_sc:
            missing.append(name)
    return list(dict.fromkeys(missing))


def classify_audit_status(found_kaur: list, found_pnc: list, unauthorized: list = None):
    num_k = len(found_kaur)
    num_p = len(found_pnc)
    short_label = f'{num_k} KAUR, {num_p} PNC'

    # Jika ada personil non-teknisi (misal KUPT / pihak luar) yang masuk ke kolom pelaksana -> TEMUAN UTAMA (Perlu Koreksi)
    if unauthorized:
        unauth_str = ', '.join(unauthorized)
        return 'CRITICAL', f'🚨 {short_label} (Temuan: Ada Personil Non-Teknisi ({unauth_str}) di Kolom Pelaksana - Perlu Koreksi)', 'CRITICAL'

    # 1. Tepat 1 KAUR dan 2 PNC (Sesuai Aturan Standar)
    if num_k == 1 and num_p == 2:
        return 'OK', '✅ 1 KAUR, 2 PNC (Sesuai Aturan)', 'OK'

    # 2. Kurang dari 1 KAUR atau kurang dari 2 PNC -> TEMUAN UTAMA (Perlu Koreksi)
    if num_k < 1 or num_p < 2:
        issues = []
        if num_k == 0:
            issues.append('Tanpa KAUR')
        if num_p < 2:
            issues.append(f'Kurang PNC ({num_p}/2)')
        issue_desc = ' & '.join(issues)
        return 'CRITICAL', f'🚨 {short_label} (Temuan Utama: {issue_desc} - Perlu Koreksi)', 'CRITICAL'

    # 3. 2 KAUR 2 PNC, 1 KAUR 3 PNC, dsb (Kelebihan Personil) -> TEMUAN BIASA (Aman / Tidak Perlu Koreksi)
    return 'WARNING', f'ℹ️ {short_label} (Temuan Biasa: Kelebihan Personil - Tidak Perlu Koreksi)', 'WARNING'


def audit_folder(folder_path: Path, pegawai_cfg: dict = None):
    kaur_map, pnc_map, cfg = get_roster_sets(pegawai_cfg)

    pdf_files = sorted(folder_path.rglob('*.pdf'))
    files_result = []
    counts_by_key = {}
    ok_count = 0
    critical_count = 0
    warning_count = 0

    for pdf_p in pdf_files:
        fname = pdf_p.name
        try:
            doc = fitz.open(pdf_p)
            found_k, found_p, raw_personnel, unauth = extract_personnel_from_pdf(doc, kaur_map, pnc_map, return_unauthorized=True)
            if raw_personnel and not found_k and not found_p:
                for raw_name in raw_personnel:
                    normalized = re.sub(r'\s+', ' ', raw_name).strip().upper()
                    if normalized in kaur_map:
                        found_k.append(kaur_map[normalized])
                    elif normalized in pnc_map:
                        found_p.append(pnc_map[normalized])
            missing_no_sc = extract_missing_no_sc(doc, raw_personnel, kaur_map, pnc_map)
            doc.close()
        except Exception as e:
            found_k, found_p, raw_personnel, unauth, missing_no_sc = [], [], [], [], []

        status_code, status_label, severity = classify_audit_status(found_k, found_p, unauth)
        if missing_no_sc:
            status_label += f' | ⚠️ SC belum lengkap: {len(missing_no_sc)}'
        key = f'{len(found_k)} KAUR, {len(found_p)} PNC'
        if unauth:
            key += f' + {len(unauth)} Non-Teknisi'
        counts_by_key[key] = counts_by_key.get(key, 0) + 1

        if severity == 'OK':
            ok_count += 1
        elif severity == 'CRITICAL':
            critical_count += 1
        else: # WARNING
            warning_count += 1

        files_result.append({
            'file': fname,
            'path': str(pdf_p).replace('\\', '/'),
            'status': status_code,
            'status_label': status_label,
            'severity': severity,
            'needs_correction': (severity == 'CRITICAL'),
            'needs_sc_correction': bool(missing_no_sc),
            'missing_no_sc': missing_no_sc,
            'no_sc_missing_count': len(missing_no_sc),
            'unauthorized': unauth,
            'key': key,
            'kaur': [k['nama'] for k in found_k],
            'pnc': [p['nama'] for p in found_p],
            'personnel': raw_personnel or [k['nama'] for k in found_k] + [p['nama'] for p in found_p],
            'personnel_source': 'file' if raw_personnel else 'profile_fallback',
            'num_kaur': len(found_k),
            'num_pnc': len(found_p)
        })

    return {
        'total_files': len(files_result),
        'ok_count': ok_count,
        'critical_count': critical_count,
        'warning_count': warning_count,
        'mismatch_count': critical_count + warning_count,
        'counts_by_key': counts_by_key,
        'files': files_result
    }


def correct_single_file(pdf_path: Path, kaur_obj: dict, pnc1_obj: dict, pnc2_obj: dict, sc_only: bool = False) -> bool:
    if not pdf_path.exists():
        raise FileNotFoundError(f'File tidak ditemukan: {pdf_path}')

    new_employees = [
        {'nama': kaur_obj['nama'], 'no_sc': kaur_obj.get('no_sc', '')},
        {'nama': pnc1_obj['nama'], 'no_sc': pnc1_obj.get('no_sc', '')},
        {'nama': pnc2_obj['nama'], 'no_sc': pnc2_obj.get('no_sc', '')}
    ]

    doc = fitz.open(pdf_path)
    ok = replace_page1_employee_names(doc, new_employees, sc_only=sc_only)
    if ok:
        doc.save(pdf_path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    doc.close()
    return ok


def auto_correct_files(folder_path: Path, target_file_names: list = None, pegawai_cfg: dict = None):
    kaur_map, pnc_map, cfg = get_roster_sets(pegawai_cfg)
    all_kaur = list(kaur_map.values())
    all_pnc = list(pnc_map.values())

    if not all_kaur or len(all_pnc) < 2:
        raise ValueError('Daftar pegawai minimal harus memiliki 1 KAUR dan 2 PNC.')

    audit_res = audit_folder(folder_path, cfg)
    files_to_fix = [f for f in audit_res['files'] if f.get('severity') == 'CRITICAL']

    if target_file_names:
        target_set = set(target_file_names)
        files_to_fix = [f for f in files_to_fix if f['file'] in target_set]

    corrected = []
    failed = []

    for f_info in files_to_fix:
        f_path = Path(f_info['path'])
        if not f_path.exists():
            failed.append({'file': f_info['file'], 'error': 'File not found'})
            continue

        existing_k = [kaur_map[k] for k in f_info['kaur'] if k in kaur_map]
        existing_p = [pnc_map[p] for p in f_info['pnc'] if p in pnc_map]

        # 1. Determine exactly 1 KAUR
        if len(existing_k) >= 1:
            chosen_kaur = existing_k[0]  # retain primary KAUR
        else:
            seed = sum(ord(c) for c in f_info['file'])
            rng = random.Random(seed)
            chosen_kaur = rng.choice(all_kaur)

        # 2. Determine exactly 2 PNC
        chosen_pnc = []
        if len(existing_p) >= 2:
            chosen_pnc = existing_p[:2]
        elif len(existing_p) == 1:
            chosen_pnc.append(existing_p[0])
            rem_pnc = [p for p in all_pnc if p['nama'] != existing_p[0]['nama']]
            if rem_pnc:
                chosen_pnc.append(rem_pnc[0])
        else:
            seed = sum(ord(c) for c in f_info['file'])
            rng = random.Random(seed)
            sample_p = rng.sample(all_pnc, min(2, len(all_pnc)))
            chosen_pnc.extend(sample_p)

        while len(chosen_pnc) < 2:
            for p in all_pnc:
                if p not in chosen_pnc:
                    chosen_pnc.append(p)
                    break

        try:
            success = correct_single_file(f_path, chosen_kaur, chosen_pnc[0], chosen_pnc[1])
            if success:
                corrected.append({
                    'file': f_info['file'],
                    'kaur': chosen_kaur['nama'],
                    'pnc': [p['nama'] for p in chosen_pnc]
                })
            else:
                failed.append({'file': f_info['file'], 'error': 'Gagal menerapkan redaksi'})
        except Exception as e:
            failed.append({'file': f_info['file'], 'error': str(e)})

    return {
        'total_scanned': len(audit_res['files']),
        'total_attempted': len(files_to_fix),
        'total_corrected': len(corrected),
        'total_failed': len(failed),
        'corrected': corrected,
        'failed': failed
    }


def correct_no_sc_file(pdf_path: Path, profiles: list[dict]) -> bool:
    if not pdf_path.exists():
        raise FileNotFoundError(f'File tidak ditemukan: {pdf_path}')
    doc = fitz.open(pdf_path)
    employees = [{'nama': p['nama'], 'no_sc': p.get('no_sc', '')} for p in profiles]
    ok = replace_page1_employee_names(doc, employees, sc_only=True)
    if ok:
        doc.save(pdf_path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    doc.close()
    return ok


def auto_correct_no_sc_files(folder_path: Path, pegawai_cfg: dict = None):
    kaur_map, pnc_map, cfg = get_roster_sets(pegawai_cfg)
    audit_res = audit_folder(folder_path, cfg)
    targets = [f for f in audit_res['files'] if f.get('needs_sc_correction')]
    corrected, failed = [], []
    for info in targets:
        profiles = []
        unresolved = []
        for name in info.get('missing_no_sc', []):
            key = re.sub(r'\s+', ' ', name).strip().upper()
            profile = kaur_map.get(key) or pnc_map.get(key)
            if profile and profile.get('no_sc'):
                profiles.append(profile)
            else:
                unresolved.append(name)
        try:
            ok = correct_no_sc_file(Path(info['path']), profiles) if profiles else False
            if ok:
                corrected.append({'file': info['file'], 'names': [p['nama'] for p in profiles]})
            if unresolved or not ok:
                reasons = []
                if unresolved:
                    reasons.append('Profil/nomor SC tidak tersedia: ' + ', '.join(unresolved))
                if profiles and not ok:
                    reasons.append('Layout PDF tidak dapat dibaca')
                failed.append({'file': info['file'], 'error': '; '.join(reasons)})
        except Exception as exc:
            failed.append({'file': info['file'], 'error': str(exc)})
    return {
        'total_sc_attempted': len(targets),
        'total_sc_corrected': len(corrected),
        'total_sc_failed': len(failed),
        'corrected': corrected,
        'failed': failed
    }


def main():
    parser = argparse.ArgumentParser(description='Audit and correct personnel compliance (1 KAUR, 2 PNC).')
    parser.add_argument('--action', choices=['audit', 'correct-single', 'auto-correct-batch', 'auto-correct-no-sc'], default='audit')
    parser.add_argument('--folder', default='02_pdf_target', help='Target directory containing PDF files')
    parser.add_argument('--file', help='Single PDF file path for correct-single')
    parser.add_argument('--kaur', help='KAUR name for correct-single')
    parser.add_argument('--pnc1', help='PNC 1 name for correct-single')
    parser.add_argument('--pnc2', help='PNC 2 name for correct-single')
    args = parser.parse_args()

    folder_path = Path(args.folder)

    if args.action == 'audit':
        if not folder_path.exists():
            print(json.dumps({'error': f'Folder tidak ditemukan: {folder_path}'}))
            sys.exit(1)
        res = audit_folder(folder_path)
        print(json.dumps(res, indent=2))

    elif args.action == 'correct-single':
        if not args.file:
            print(json.dumps({'error': 'Parameter --file diperlukan untuk correct-single'}))
            sys.exit(1)
        pdf_path = Path(args.file)
        kaur_map, pnc_map, _ = get_roster_sets()
        k_obj = kaur_map.get(args.kaur.strip().upper()) if args.kaur else None
        p1_obj = pnc_map.get(args.pnc1.strip().upper()) if args.pnc1 else None
        p2_obj = pnc_map.get(args.pnc2.strip().upper()) if args.pnc2 else None
        if not k_obj or not p1_obj or not p2_obj:
            print(json.dumps({'error': 'Nama personil tidak valid atau tidak terdaftar di konfigurasi'}))
            sys.exit(1)
        ok = correct_single_file(pdf_path, k_obj, p1_obj, p2_obj)
        print(json.dumps({'success': ok, 'file': str(pdf_path)}))

    elif args.action == 'auto-correct-batch':
        if not folder_path.exists():
            print(json.dumps({'error': f'Folder tidak ditemukan: {folder_path}'}))
            sys.exit(1)
        print(f"[STEP 3.5] Memulai audit dan koreksi personil (1 KAUR, 2 PNC) pada folder: {folder_path}...", file=sys.stderr)
        res = auto_correct_files(folder_path)
        print(f"[STEP 3.5] Selesai! Berkas diperiksa: {res.get('total_scanned', 0)}, Temuan utama perlu koreksi: {res['total_attempted']}, Berhasil dikoreksi: {res['total_corrected']}, Gagal: {res['total_failed']}.", file=sys.stderr)
        
        # Invalidate cache if 02_pdf_target
        cache_path = Path('logs/file_personnel_cache.json')
        if cache_path.exists() and ('02_pdf_target' in str(folder_path) or folder_path.name == '02_pdf_target'):
            try:
                cache_path.unlink()
            except Exception:
                pass

        print(json.dumps(res, indent=2))

    elif args.action == 'auto-correct-no-sc':
        if not folder_path.exists():
            print(json.dumps({'error': f'Folder tidak ditemukan: {folder_path}'}))
            sys.exit(1)
        res = auto_correct_no_sc_files(folder_path)
        cache_path = Path('logs/file_personnel_cache.json')
        if cache_path.exists() and ('02_pdf_target' in str(folder_path) or folder_path.name == '02_pdf_target'):
            try:
                cache_path.unlink()
            except Exception:
                pass
        print(json.dumps(res, indent=2))


if __name__ == '__main__':
    main()
