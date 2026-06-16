import streamlit as st
import json
import re
import os
import zipfile
import platform
import pytesseract
import gc
from io import BytesIO
from pdf2image import convert_from_bytes
from streamlit_lottie import st_lottie
from PIL import ImageOps

# --- 1. KONFIGURASI TESSERACT ---
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

def load_lottiefile(filepath: str):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except:
        return None

lottie_train = load_lottiefile("Metro Rail.json")

# --- 2. LOGIKA ADMIN MODE ---
is_admin = st.query_params.get("mode") == "admin"

# --- 3. TAMPILAN UTAMA ---
st.set_page_config(page_title="Sintelis 1.21 BOO Utility", page_icon="📑", layout="wide")
st.title("📑 GANTI NAMA PDFs CEKLIS SINTELIS")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📁 Input & Setting")
    
    jenis_kegiatan = st.radio(
        "Pilih Jenis Kegiatan:",
        ["Perawatan", "Pemeriksaan"],
        index=0,
        horizontal=True
    )
    
    instansi = st.radio(
        "Pilih Instansi/Format Nama:",
        ["BTP JAK (Format Standar)", "BTP BD (Format Khusus Sintel Boo)"],
        index=0
    )
    
    format_eksklusif = True if "BTP BD" in instansi else False
    
    if is_admin:
        with st.expander("🛠️ Admin Debug Tools", expanded=False):
            st.info("Mode Admin: Fitur bantuan teknis.")
            debug_mode = st.checkbox("Aktifkan Layar Intip (Debug Mode)", value=False)
    else:
        debug_mode = False

    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 0

    if st.button("🗑️ Hapus Semua File", use_container_width=True):
        st.session_state["file_uploader_key"] += 1
        st.rerun()

    uploaded_files = st.file_uploader(
        "Upload PDF",
        type="pdf",
        accept_multiple_files=True,
        key=f"uploader_{st.session_state['file_uploader_key']}"
    )

# --- FUNGSI OCR TERPISAH (CACHING AGAR TIDAK LELET) ---
@st.cache_data(show_spinner=False, max_entries=50)
def process_pdf_ocr(file_bytes, debug=False):
    images = convert_from_bytes(file_bytes, dpi=150, first_page=1, last_page=1)
    img = images[0].convert('L')
    img = ImageOps.autocontrast(img)
    width, height = img.size
    
    img_cropped = img.crop((0.0, 0.0, width * 1.0, height * 0.30)) 
    text_crop = pytesseract.image_to_string(img_cropped).upper()
    
    # Clean memory
    del img, images
    gc.collect()
    
    return text_crop, img_cropped

# --- 4. PROSES DATA ---
if uploaded_files:
    zip_buffer = BytesIO()
    processed_files, duplicate_errors, unique_filenames = [], [], set()
    
    with col2:
        head_col, btn_col = st.columns([1.5, 1])
        with head_col:
            st.subheader("📋 Hasil Proses")
        
        status_container = st.empty()
        with status_container.container():
            if lottie_train:
                st_lottie(lottie_train, height=150, key="train_loader")
            progress_text = st.empty()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_f:
            for idx, f in enumerate(uploaded_files):
                progress_text.info(f"Memproses {idx+1}/{len(uploaded_files)}...")
                
                name_only = f.name.upper()
                tgl_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', name_only)
                
                if not tgl_match:
                    duplicate_errors.append(f"❌ {f.name}: Format tanggal tidak ditemukan.")
                    continue
                    
                tgl_full = tgl_match.group(0)
                bln_angka = str(int(tgl_match.group(2)))
                thn_angka = tgl_match.group(3)
                prefix_periode = f"{thn_angka}-{bln_angka}"
                
                assets_found = []
                target_keyword = None
                kode_ceklis = ""
                kategori_nama = ""

                try:
                    file_bytes = f.getvalue()
                    text_crop, img_cropped = process_pdf_ocr(file_bytes, debug_mode)
                    
                    if debug_mode: 
                        st.image(img_cropped, caption=f"Scan: {f.name}")
                        with st.expander(f"👀 Intip Teks OCR: {f.name}"):
                            st.text(text_crop)
                            
                    text_flat = text_crop.replace('\n', ' ')
                    is_special_doc = False

                    # ====================================================
                    # GERBANG A: DOKUMEN SPESIAL
                    # ====================================================
                    
                    if any(x in text_flat for x in ["POINT LOCK", "PENGAMAN WESEL"]):
                        is_special_doc = True
                        target_keyword = "WESEL"
                        kategori_nama = "WESEL"
                        kode_ceklis = "BPBYE1"
                        w_match = re.search(r'(W\d+)', text_flat)
                        aid = w_match.group(1) if w_match else "W_UNKNOWN"
                        loc_id = "BOO" if "BOGOR" in text_flat else "LOKASI"
                        assets_found.append({"id": aid, "loc": loc_id})

                    elif "PERALATAN DALAM PERSINYALAN ELEKTRIK" in text_flat:
                        is_special_doc = True
                        target_keyword = "PDSE"
                        kategori_nama = "PDSE"
                        kode_ceklis = "BPBYE2"
                        if "BOGORPALEDANG" in text_flat: loc_id = "BOP"
                        elif "BOGOR" in text_flat: loc_id = "BOO"
                        elif "CILEBUT" in text_flat: loc_id = "CLT"
                        else: loc_id = "LOKASI"
                        assets_found.append({"id": "", "loc": loc_id})

                    elif "PINTU PERLINTASAN" in text_flat:
                        is_special_doc = True
                        target_keyword = "PINTU PERLINTASAN"
                        kategori_nama = "PINTU PERLINTASAN"
                        kode_ceklis = "BPBKS17"
                        jpl_match = re.search(r'JPL\s+(\d+)', text_flat)
                        aid = f"JPL {jpl_match.group(1)}" if jpl_match else "JPL"
                        loc_id = "BOP" if "BOGORPALEDANG" in text_flat else "LOKASI"
                        assets_found.append({"id": aid, "loc": loc_id})

                    # Fallback Gerbang B
                    if not is_special_doc:
                        if "WESEL" in name_only:
                            target_keyword, kode_ceklis, kategori_nama = "WESEL", "BPBYE1", "WESEL"
                        elif "AXLE" in name_only:
                            target_keyword, kode_ceklis, kategori_nama = "AXLE", "BPBYE7", "AXC"
                        
                        if target_keyword:
                            # Logic extract assets found
                            assets_found.append({"id": "X", "loc": "LOKASI"})

                    # Build Filename
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
                            zip_f.writestr(new_name, f.getvalue())
                            processed_files.append(new_name)
                            unique_filenames.add(new_name)
                        else:
                            duplicate_errors.append(f"⚠️ {f.name}: Duplikat.")

                except Exception as e:
                    duplicate_errors.append(f"❌ {f.name}: Error {e}")

        progress_text.empty()
        status_container.success(f"✅ Selesai! {len(processed_files)} file diproses.")
        
        if processed_files:
            st.download_button(
                label="📥 Download Hasil (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"Ceklis_{prefix_periode}.zip",
                mime="application/zip",
                use_container_width=True
            )
            
            with st.expander("📄 Daftar File Berhasil", expanded=True):
                for name in processed_files:
                    st.write(f"✅ {name}")
        
        if duplicate_errors:
            with st.expander("⚠️ Warning/Error", expanded=False):
                for err in duplicate_errors:
                    st.write(err)
