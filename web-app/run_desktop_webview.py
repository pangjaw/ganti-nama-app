"""
Sintelis Utility — Desktop WebView App
Menjalankan web-app hasil build Vite dalam native window.
API folder dialog & save file via HTTP endpoint (tidak pakai pywebview js_api).
"""
import base64
import http.server
import io
import json
import os
import time
from datetime import datetime
import re
import socketserver
import sys
import tempfile
import threading
import urllib.parse
import shutil
import subprocess

import webview
from pdf2image import convert_from_path
from PIL import ImageOps, Image
import pytesseract
import updater_engine
from timemark_engine import pipeline_runner

if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BUNDLE_DIR, "dist")
PORT = 18725

ENGINE_DIR = os.path.join(BUNDLE_DIR, "timemark_engine")
if not os.path.isdir(ENGINE_DIR):
    ENGINE_DIR = os.path.join(BASE_DIR, "timemark_engine")

def get_tesseract_cmd():
    candidates = [
        os.path.join(BUNDLE_DIR, "tesseract", "tesseract.exe"),
        os.path.join(BUNDLE_DIR, "Tesseract-OCR", "tesseract.exe"),
        os.path.join(BASE_DIR, "tesseract", "tesseract.exe"),
        os.path.join(BASE_DIR, "Tesseract-OCR", "tesseract.exe"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    import shutil
    which = shutil.which("tesseract")
    if which:
        return which
    return r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def get_poppler_dir():
    candidates = [
        os.path.join(BUNDLE_DIR, "poppler"),
        os.path.join(BUNDLE_DIR, "Aplikasi", "poppler"),
        os.path.join(BASE_DIR, "poppler"),
        os.path.join(BASE_DIR, "..", "Aplikasi", "poppler"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return os.path.join(BASE_DIR, "..", "Aplikasi", "poppler")

TESSERACT_CMD = get_tesseract_cmd()
POPPLER_DIR = get_poppler_dir()

# Set TESSDATA_PREFIX otomatis jika ada tessdata
_tessdata_candidate = os.path.join(os.path.dirname(TESSERACT_CMD), "tessdata")
if os.path.isdir(_tessdata_candidate):
    os.environ["TESSDATA_PREFIX"] = _tessdata_candidate
if os.path.isfile(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# ---- Logging ke file ----
LOG_FILE = os.path.join(tempfile.gettempdir(), "sintelis_utility.log")

def _log(msg):
    """Append log entry ke file log dengan timestamp."""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as lf:
            lf.write(f"[{ts}] {msg}\n")
            lf.flush()
    except Exception:
        pass  # silent fail — jangan ganggu app utama

# Fix blank screen setelah minimize lama — disable GPU acceleration WebView2
# CalculateNativeWinOcclusion: cegah Windows suspend rendering pipeline saat window minimized
os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
    "--disable-gpu "
    "--disable-features=CalculateNativeWinOcclusion"
)

APP_DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SintelisUtility")
os.makedirs(APP_DATA_DIR, exist_ok=True)
ACCOUNTS_FILE = os.path.join(APP_DATA_DIR, "p3ste_accounts.json")

_selected_folder = None
_was_minimized = False


def on_minimized():
    """Track bahwa window pernah di-minimize (untuk trigger recovery di restored)."""
    global _was_minimized
    _was_minimized = True
    _log("🟡 EVENT: minimized")


_was_minimized = False

# ---- P3-STE Downloader Engine State ----
_p3ste_state = {
    "running": False,
    "cancelled": False,
    "current": 0,
    "total": 0,
    "logs": [],
    "downloaded_files": [],
    "error": None
}

def _add_p3ste_log(log_type, msg):
    ts = time.strftime("%H:%M:%S")
    _p3ste_state["logs"].append({"type": log_type, "msg": msg, "ts": ts})
    _log(f"P3STE [{log_type.upper()}] {msg}")
_current_playwright_context = None

def _cancel_all_processes():
    global _current_playwright_context, _p3ste_state
    _p3ste_state["cancelled"] = True
    _p3ste_state["running"] = False
    _add_p3ste_log("warn", "🛑 Menghentikan semua proses yang sedang berjalan...")
    if _current_playwright_context:
        try:
            _current_playwright_context.close()
            _add_p3ste_log("info", "✓ Browser engine berhasil ditutup.")
        except Exception as e:
            _log(f"Notice closing browser context: {e}")
        _current_playwright_context = None

def _get_unique_p3ste_filename(target_folder, filename, existing_names=None):
    """
    Menghasilkan nama file unik dengan menambahkan (2), (3), dst. jika nama file sudah ada
    di target_folder atau sudah digunakan dalam sesi pengunduhan saat ini.
    Contoh:
    checklist.pdf -> checklist.pdf (jika belum ada)
    checklist.pdf -> checklist (2).pdf (jika sudah ada)
    checklist.pdf -> checklist (3).pdf (jika checklist (2).pdf sudah ada)
    """
    clean_fn = re.sub(r'[<>:"/\\|?*]', '_', filename).strip()
    base, ext = os.path.splitext(clean_fn)
    if not ext:
        ext = ".pdf"

    m = re.search(r'^(.*?)\s*\((\d+)\)$', base)
    if m:
        base_clean = m.group(1).strip()
        counter = int(m.group(2))
    else:
        base_clean = base
        counter = 1

    candidate_fn = f"{base}{ext}"
    candidate_path = os.path.join(target_folder, candidate_fn)

    while os.path.exists(candidate_path) or (existing_names and candidate_fn in existing_names):
        counter += 1
        candidate_fn = f"{base_clean} ({counter}){ext}"
        candidate_path = os.path.join(target_folder, candidate_fn)

    return candidate_fn, candidate_path

def _correct_filename_date(filename, table_date):
    """
    Jika tanggal di nama file dari server berbeda dengan tanggal resmi di kolom tabel web P3-STE,
    ganti prefix tanggal nama file dengan tanggal dari tabel web.
    Contoh: '02-08-2026_PERAWATAN...pdf' -> '02-07-2026_PERAWATAN...pdf'
    """
    if not table_date or not re.match(r'^\d{2}-\d{2}-\d{4}$', table_date):
        return filename, None
    
    # Cek apakah nama file diawali format DD-MM-YYYY
    m = re.match(r'^(\d{2}-\d{2}-\d{4})(_.*\.pdf)$', filename, re.IGNORECASE)
    if m:
        server_date = m.group(1)
        suffix = m.group(2)
        if server_date != table_date:
            corrected_fn = f"{table_date}{suffix}"
            return corrected_fn, server_date
    elif filename.lower().startswith("checklist_"):
        # Jika server tidak mengembalikan tanggal sama sekali
        return f"{table_date}_{filename}", None
        
    return filename, None

def _parse_curl_header_cookies(curl_cmd):
    """Parse headers and cookies from cURL string (mendukung bash, cmd, powershell, case-insensitive)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    cookies = {}
    
    if not curl_cmd:
        return headers, cookies

    # Clean CMD carets and newlines
    clean_cmd = curl_cmd.replace("^\r\n", " ").replace("^\n", " ").replace("^\"", "\"").replace("^", "")
    
    # 1. Extract headers (-H '...' or --header '...' or -H "...")
    header_matches = re.findall(r'(?:-H|--header)\s+[\'"]([^\'"]+)[\'"]', clean_cmd, re.IGNORECASE)
    for h in header_matches:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()
            
    # 2. Case-insensitive search for Cookie header
    cookie_str = ""
    for k, v in list(headers.items()):
        if k.lower() == "cookie":
            cookie_str = v
            break
            
    # 3. Extract -b '...' or --cookie '...'
    cookie_flag_matches = re.findall(r'(?:-b|--cookie)\s+[\'"]([^\'"]+)[\'"]', clean_cmd, re.IGNORECASE)
    if cookie_flag_matches:
        cookie_str += ("; " if cookie_str else "") + cookie_flag_matches[0]
        
    if cookie_str:
        for c in cookie_str.split(";"):
            if "=" in c:
                ck, cv = c.strip().split("=", 1)
                ck = ck.strip()
                cv = cv.strip()
                if ck:
                    cookies[ck] = cv
                    
    return headers, cookies

def _safe_evaluate(page, js_func, arg=None, max_retries=6, delay=1.5):
    """Jalankan page.evaluate dengan retry otomatis jika context hancur saat navigasi."""
    last_err = None
    for attempt in range(max_retries):
        try:
            if arg is not None:
                return page.evaluate(js_func, arg)
            return page.evaluate(js_func)
        except Exception as e:
            last_err = e
            err_msg = str(e)
            if "destroyed" in err_msg or "navigating" in err_msg or "Target closed" not in err_msg:
                time.sleep(delay)
                continue
            raise e
    _log(f"safe_evaluate notice (retried {max_retries}x): {last_err}")
    return None

def _run_p3ste_download_task(nipp, password, awal, akhir, type_val, target_folder, start_id=None, end_id=None, show_browser=False, curl_cmd=""):
    global _p3ste_state
    _p3ste_state["running"] = True
    _p3ste_state["cancelled"] = False
    _p3ste_state["current"] = 0
    _p3ste_state["total"] = 0
    _p3ste_state["logs"] = []
    _p3ste_state["downloaded_files"] = []
    _p3ste_state["error"] = None

    try:
        headers, cookies = {}, {}
        if curl_cmd:
            _add_p3ste_log("info", "Memparsing Header & Cookie dari string cURL...")
            headers, cookies = _parse_curl_header_cookies(curl_cmd)
        else:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://p3-ste.kai.id/"
            }
        
        import requests
        requests.packages.urllib3.disable_warnings()
        
        session = requests.Session()
        session.verify = False
        session.headers.update(headers)
        session.cookies.update(cookies)

        type_name = "pemeriksaan" if str(type_val) == "1" else "perawatan"

        # Check for Direct ID Range Download Mode
        if start_id and end_id:
            try:
                s_id = int(str(start_id).strip())
                e_id = int(str(end_id).strip())
                if s_id > 0 and e_id >= s_id:
                    total_ids = e_id - s_id + 1
                    _add_p3ste_log("info", f"Mode Unduh Langsung ID: {s_id} s.d. {e_id} (Total {total_ids} target)...")
                    _p3ste_state["total"] = total_ids
                    os.makedirs(target_folder, exist_ok=True)
                    session_filenames = set()
                    
                    for current_id in range(s_id, e_id + 1):
                        if _p3ste_state["cancelled"]:
                            _add_p3ste_log("warn", "Pengunduhan dibatalkan pengguna.")
                            break
                            
                        total_downloaded = len(_p3ste_state["downloaded_files"]) + 1
                        _p3ste_state["current"] = total_downloaded
                        pdf_url = f"https://p3-ste.kai.id/cetak_checklist/report/{type_name}/exports/pdf/{current_id}?false"
                        fn = f"checklist_{current_id}.pdf"
                        
                        _add_p3ste_log("info", f"[{current_id}] Mencoba unduh checklist ID {current_id}...")
                        
                        download_success = False
                        last_err = ""
                        max_attempts = 3
                        for attempt in range(max_attempts):
                            if _p3ste_state["cancelled"]: break
                            try:
                                fresp = session.get(pdf_url, timeout=30)
                                if fresp.status_code == 200 and fresp.content[:4] == b"%PDF":
                                    cd = fresp.headers.get("Content-Disposition", "")
                                    if "filename=" in cd:
                                        cd_fn = re.search(r'filename=["\']?([^"\';]+)["\']?', cd)
                                        if cd_fn:
                                            fn = cd_fn.group(1).strip().strip('"').strip("'")

                                    fn, out_path = _get_unique_p3ste_filename(target_folder, fn, session_filenames)

                                    with open(out_path, "wb") as pf:
                                        pf.write(fresp.content)

                                    file_size = len(fresp.content)
                                    session_filenames.add(fn)
                                    _p3ste_state["downloaded_files"].append({
                                        "name": fn,
                                        "path": out_path,
                                        "size": file_size
                                    })
                                    retry_tag = f" (coba ulang ke-{attempt})" if attempt > 0 else ""
                                    _add_p3ste_log("success", f"✓ Tersimpan: {fn} ({file_size // 1024} KB){retry_tag}")
                                    download_success = True
                                    break
                                elif fresp.status_code in (500, 502, 503, 504, 429):
                                    last_err = f"HTTP {fresp.status_code}"
                                    if attempt < max_attempts - 1:
                                        time.sleep(1.5 * (attempt + 1))
                                        continue
                                else:
                                    last_err = f"HTTP {fresp.status_code}"
                                    break
                            except Exception as fe:
                                last_err = str(fe)
                                if attempt < max_attempts - 1:
                                    time.sleep(1.5 * (attempt + 1))
                                    continue

                        if not download_success and not _p3ste_state["cancelled"]:
                            _add_p3ste_log("error", f"✗ ID {current_id} Gagal: {last_err}")

                        time.sleep(0.15)

                    _add_p3ste_log("success", f"Selesai! Berhasil mengunduh total {len(_p3ste_state['downloaded_files'])} file PDF.")
                    return
            except Exception as id_err:
                _add_p3ste_log("warn", f"Pengecekan ID Range: {id_err}. Melanjutkan ke mode Scraper Halaman...")

        mode_desc = "Visual / Jendela Tampil" if show_browser else "Headless"
        _add_p3ste_log("info", f"Memulai Browser Engine ({type_name.upper()} - {mode_desc})...")

        if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright")

        user_data_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SintelisUtility", "p3ste_browser_profile")
        os.makedirs(user_data_dir, exist_ok=True)

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            context = None
            last_err = None
            for ch in ["msedge", "chrome", None]:
                try:
                    ch_label = f"Channel: {ch}" if ch else "Default Chromium"
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir,
                        channel=ch,
                        headless=not show_browser,
                        viewport=None,
                        user_agent=headers.get("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--no-sandbox",
                            "--disable-infobars"
                        ],
                        ignore_default_args=["--enable-automation"]
                    )
                    _add_p3ste_log("info", f"✓ Browser engine aktif ({ch_label}, Profile: Persistent).")
                    global _current_playwright_context
                    _current_playwright_context = context
                    break
                except Exception as b_err:
                    last_err = b_err
                    continue

            if not context:
                raise Exception(
                    f"Gagal menjalankan browser engine: {last_err}. "
                    "Pastikan Microsoft Edge atau Google Chrome terpasang di Windows."
                )

            # Injeksi cookie dari cURL jika ada
            if cookies:
                pw_cookies = []
                for ck, cv in cookies.items():
                    pw_cookies.append({
                        "name": ck,
                        "value": cv,
                        "url": "https://p3-ste.kai.id"
                    })
                try:
                    context.add_cookies(pw_cookies)
                except Exception as ce:
                    pass

            page = context.pages[0] if len(context.pages) > 0 else context.new_page()

            # 1. Buka halaman rekap_checklist dengan query filter langsung
            query_url = f"https://p3-ste.kai.id/rekap_checklist?awal={awal.replace('/', '%2F')}&akhir={akhir.replace('/', '%2F')}&type={type_val}&asset=0&category=0&daop=1&resort=170&nipp=0&noasset=0&hasil=baik&status=done"
            _add_p3ste_log("info", f"Membuka portal P3-STE ({type_name.upper()})...")
            
            page.goto(query_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)

            cur_url = page.url
            page_title = page.title()
            _add_p3ste_log("info", f"Halaman termuat: '{page_title}'")

            # Cek apakah berada di halaman Login
            is_login_page = _safe_evaluate(page, """() => {
                const hasLoginForm = document.querySelector('input#nipp, input[name="nipp"], input#kata_sandi, input[name="kata_sandi"], form[action*="auth"]');
                const hasDashboard = document.querySelector('#submited, #table, a[href*="logout"], a[href*="rekap_checklist"], .navbar-nav, .sidebar');
                if (hasDashboard) return false;
                return !!hasLoginForm || window.location.pathname === '/' || document.title.toLowerCase().includes('login');
            }""")

            if is_login_page:
                if not nipp or not password:
                    _add_p3ste_log("error", "⚠️ Sesi login habis dan data NIPP / Kata Sandi belum diatur.")
                    raise Exception("Sesi login kedaluwarsa. Silakan lengkapi NIPP dan Kata Sandi pada menu pengaturan akun.")

                _add_p3ste_log("info", f"🔐 Sesi belum aktif. Melakukan login otomatis untuk NIPP: {nipp}...")
                
                # Pastikan berada di URL login jika sempat terlempar
                if "rekap_checklist" not in page.url and "/auth" not in page.url and page.url.rstrip("/") != "https://p3-ste.kai.id":
                    page.goto("https://p3-ste.kai.id/", wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(1500)

                # Isi formulir login dan selesaikan captcha matematika secara otomatis
                fill_res = _safe_evaluate(page, f"""() => {{
                    const nippInp = document.querySelector('input#nipp, input[name="nipp"]');
                    const passInp = document.querySelector('input#kata_sandi, input[name="kata_sandi"]');
                    const cptInp = document.querySelector('input#captcha, input[name="captcha"]');
                    const cptRes = document.querySelector('input#cptres, input[name="cptres"]');
                    const spanMath = document.querySelector('span[style*="font-size"]');

                    if (!nippInp || !passInp || !cptInp) {{
                        return {{ ok: false, error: 'Elemen input form login tidak ditemukan di halaman website P3-STE.' }};
                    }}

                    nippInp.value = {json.dumps(nipp)};
                    nippInp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    nippInp.dispatchEvent(new Event('change', {{ bubbles: true }}));

                    passInp.value = {json.dumps(password)};
                    passInp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    passInp.dispatchEvent(new Event('change', {{ bubbles: true }}));

                    let captchaVal = "";
                    if (cptRes && cptRes.value) {{
                        captchaVal = cptRes.value.trim();
                    }} else if (spanMath) {{
                        try {{
                            const expr = spanMath.innerText.trim();
                            const parts = expr.split('+');
                            if (parts.length === 2) {{
                                captchaVal = String(parseInt(parts[0].trim()) + parseInt(parts[1].trim()));
                            }}
                        }} catch (e) {{}}
                    }}

                    cptInp.value = captchaVal;
                    cptInp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    cptInp.dispatchEvent(new Event('change', {{ bubbles: true }}));

                    return {{ ok: true, captcha: captchaVal }};
                }}""")

                if not fill_res or not fill_res.get("ok"):
                    err = fill_res.get("error") if fill_res else "Gagal mengisi input formulir login"
                    raise Exception(err)

                _add_p3ste_log("info", f"Form terisi (Captcha: {fill_res.get('captcha', '-')}). Mengirim autentikasi...")
                
                # Klik tombol submit Masuk
                try:
                    page.click('button[type="submit"], #form-login button')
                except Exception:
                    _safe_evaluate(page, "() => { document.querySelector('form#form-login')?.submit(); }")
                
                page.wait_for_timeout(3000)

                # Periksa apakah berhasil login atau muncul alert pesan error dari web
                login_check = _safe_evaluate(page, """() => {
                    const alertEl = document.querySelector('.alert-danger, .alert, .invalid-feedback, .text-danger, .error-message, .swal2-html-container');
                    let errText = alertEl ? alertEl.innerText.trim() : "";
                    const hasDashboard = document.querySelector('#submited, #table, a[href*="logout"], a[href*="rekap_checklist"], .navbar-nav, .sidebar');
                    const isLogged = !!hasDashboard || (!window.location.pathname.includes('auth') && window.location.pathname !== '/' && !document.title.toLowerCase().includes('login'));
                    return {
                        isLogged: isLogged,
                        errText: errText
                    };
                }""")

                if login_check and not login_check.get("isLogged"):
                    page.wait_for_timeout(2000)
                    login_check2 = _safe_evaluate(page, """() => {
                        const alertEl = document.querySelector('.alert-danger, .alert, .invalid-feedback, .text-danger, .error-message, .swal2-html-container');
                        let errText = alertEl ? alertEl.innerText.trim() : "";
                        const hasDashboard = document.querySelector('#submited, #table, a[href*="logout"], a[href*="rekap_checklist"], .navbar-nav, .sidebar');
                        return {
                            isLogged: !!hasDashboard,
                            errText: errText
                        };
                    }""")
                    if login_check2:
                        if login_check2.get("isLogged"):
                            login_check["isLogged"] = True
                        elif login_check2.get("errText"):
                            login_check["errText"] = login_check2.get("errText")

                if not login_check.get("isLogged"):
                    err_msg = login_check.get("errText")
                    if err_msg:
                        _add_p3ste_log("error", f"❌ Gagal Login dari Website P3-STE: {err_msg}")
                        raise Exception(f"P3-STE Menolak Login: {err_msg}")
                    else:
                        _add_p3ste_log("error", "❌ Gagal Login P3-STE: NIPP atau Kata Sandi salah / Sesi ditolak.")
                        raise Exception("Gagal Login P3-STE: NIPP atau Kata Sandi salah / Sesi ditolak.")

                _add_p3ste_log("success", f"✓ Login Berhasil untuk NIPP: {nipp}! Membuka halaman rekap...")
                page.goto(query_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2500)
            else:
                _add_p3ste_log("success", "✓ Sesi login profil browser masih aktif. Melanjutkan pengunduhan...")

            # Sinkronisasi cookie terbaru dari browser ke Requests session
            try:
                live_cookies = context.cookies(["https://p3-ste.kai.id"])
                for lc in live_cookies:
                    session.cookies.set(lc["name"], lc["value"], domain="p3-ste.kai.id")
            except Exception as se_err:
                _add_p3ste_log("warn", f"Sinkronisasi cookie session notice: {se_err}")

            # 1. Terapkan nilai filter pada form dan klik tombol filter
            _add_p3ste_log("info", "Memasukkan filter tanggal & jenis laporan...")
            _safe_evaluate(page, """(args) => {
                const { awal, akhir, typeVal } = args;
                const awalInp = document.querySelector('input[name="awal"], #awal, input[placeholder*="Awal"]');
                if (awalInp) {
                    awalInp.value = awal;
                    awalInp.dispatchEvent(new Event('input', { bubbles: true }));
                    awalInp.dispatchEvent(new Event('change', { bubbles: true }));
                }
                
                const akhirInp = document.querySelector('input[name="akhir"], #akhir, input[placeholder*="Akhir"]');
                if (akhirInp) {
                    akhirInp.value = akhir;
                    akhirInp.dispatchEvent(new Event('input', { bubbles: true }));
                    akhirInp.dispatchEvent(new Event('change', { bubbles: true }));
                }
                
                const typeSel = document.querySelector('select[name="type"], #type');
                if (typeSel) {
                    typeSel.value = typeVal;
                    typeSel.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }""", {"awal": awal, "akhir": akhir, "typeVal": type_val})

            clicked_filter = _safe_evaluate(page, """() => {
                const btn = document.querySelector('#submited, button[type="submit"], input[type="submit"], button.btn-primary');
                if (btn) {
                    btn.click();
                    return true;
                }
                return false;
            }""")
            if clicked_filter:
                _add_p3ste_log("info", "Tombol Filter diklik. Menunggu 10 data awal & tombol Cetak muncul di layar...")
            else:
                _add_p3ste_log("info", "Menunggu data tabel awal termuat...")

            # 2. Tunggu 10 data awal & tombol Cetak muncul di layar (seperti Gambar 3)
            initial_ready = False
            for _ in range(45):
                if _p3ste_state["cancelled"]: break
                page.wait_for_timeout(1000)
                row_status = _safe_evaluate(page, """() => {
                    // Cek kemunculan tombol Cetak pada tabel
                    const cetakBtns = Array.from(document.querySelectorAll('table tbody tr a, table tbody tr button, table tbody tr .btn-danger'))
                        .filter(b => b.innerText.trim().toLowerCase().includes('cetak') || (b.getAttribute('href') || '').includes('pdf') || (b.getAttribute('onclick') || '').includes('cetak'));
                    const trs = document.querySelectorAll('table tbody tr');
                    const empty = document.querySelector('.dataTables_empty');
                    const emptyText = empty ? empty.innerText.trim() : '';
                    if (empty && (emptyText.includes('Loading') || emptyText.includes('memuat') || emptyText.includes('...'))) {
                        return { ready: false, count: 0 };
                    }
                    if (cetakBtns.length > 0) {
                        return { ready: true, count: cetakBtns.length };
                    }
                    if (trs.length > 0 && !empty) {
                        return { ready: true, count: trs.length };
                    }
                    return { ready: false, count: 0 };
                }""") or {}
                
                if row_status.get("ready"):
                    _add_p3ste_log("success", f"✓ {row_status.get('count')} data awal & tombol Cetak berhasil tampil di layar.")
                    initial_ready = True
                    break

            if not initial_ready:
                _add_p3ste_log("warn", "Data awal belum terdeteksi. Mencoba melanjutkan...")

            page.wait_for_timeout(2000)

            # Sinkronisasi cookie live dari browser ke Requests session sebelum unduhan
            try:
                live_cookies = context.cookies(["https://p3-ste.kai.id"])
                for lc in live_cookies:
                    session.cookies.set(lc["name"], lc["value"], domain="p3-ste.kai.id")
                _add_p3ste_log("info", f"✓ Sesi browser terverifikasi ({len(live_cookies)} cookies).")
            except Exception as se_err:
                _add_p3ste_log("warn", f"Notice sinkronisasi cookie: {se_err}")

            # Diagnostik status tabel & Deteksi Total Data Target
            page_diag = _safe_evaluate(page, r"""() => {
                let total = 0;
                try {
                    if (typeof $ !== 'undefined' && $.fn && $.fn.DataTable) {
                        const tbls = Array.from(document.querySelectorAll('table'));
                        for (const t of tbls) {
                            if ($.fn.DataTable.isDataTable(t)) {
                                const info = $(t).DataTable().page.info();
                                if (info && info.recordsDisplay > 0) total = info.recordsDisplay;
                                else if (info && info.recordsTotal > 0) total = info.recordsTotal;
                                if (total > 0) break;
                            }
                        }
                    }
                } catch (e) {}

                const infoEl = document.querySelector('.dataTables_info, #table_info, [id*="_info"]');
                const infoText = infoEl ? infoEl.innerText : null;
                if (!total && infoText) {
                    const m = infoText.match(/(?:dari|of)\s+([\d.,]+)/i);
                    if (m) {
                        total = parseInt(m[1].replace(/[.,]/g, ''), 10) || 0;
                    }
                }

                const rows = document.querySelectorAll('#table tbody tr, table tbody tr');
                const emptyEl = document.querySelector('.dataTables_empty');
                return {
                    info: infoText,
                    total: total,
                    rowCount: (!emptyEl && rows.length > 0) ? rows.length : 0
                };
            }""") or {}
            
            if page_diag.get("info"):
                _add_p3ste_log("info", f"Status Tabel: {page_diag['info']}")

            detected_total = page_diag.get("total", 0)
            if detected_total > 0:
                _p3ste_state["total"] = detected_total
                _add_p3ste_log("info", f"📊 Terdeteksi target total: {detected_total} file checklist.")

            os.makedirs(target_folder, exist_ok=True)
            checkpoint_file = os.path.join(target_folder, ".p3ste_checkpoint.json")
            checkpoint_data = {}
            if os.path.isfile(checkpoint_file):
                try:
                    with open(checkpoint_file, "r", encoding="utf-8") as cf:
                        checkpoint_data = json.load(cf)
                except Exception:
                    checkpoint_data = {}

            if checkpoint_data:
                _add_p3ste_log("info", f"📌 Ditemukan checkpoint {len(checkpoint_data)} file. Fitur Resume otomatis aktif.")

            page_index = 1
            total_downloaded = 0
            downloaded_ids = set()
            session_filenames = set()
            failed_queue = []

            while True:
                if _p3ste_state["cancelled"]:
                    _add_p3ste_log("warn", "Pengunduhan dibatalkan pengguna.")
                    break

                _add_p3ste_log("info", f"--- Memproses Halaman {page_index} ---")
                
                # Tunggu agar baris data di halaman aktif siap
                for _ in range(20):
                    rows_ready = _safe_evaluate(page, """() => {
                        const trs = document.querySelectorAll('#table tbody tr, table tbody tr');
                        if (trs.length === 0 || document.querySelector('.dataTables_empty')) return 0;
                        return trs.length;
                    }""") or 0
                    if rows_ready > 0:
                        break
                    page.wait_for_timeout(1000)

                # Pastikan cookie Requests session selalu up-to-date
                try:
                    cur_cookies = context.cookies(["https://p3-ste.kai.id"])
                    for cc in cur_cookies:
                        session.cookies.set(cc["name"], cc["value"], domain="p3-ste.kai.id")
                except Exception:
                    pass

                # Ekstrak ID/Link PDF valid (6-8 digit ID checklist)
                pdf_items = _safe_evaluate(page, r"""(typeName) => {
                    const items = [];
                    const seen = new Set();

                    function extractRowDate(tr) {
                        if (!tr) return '';
                        const tds = tr.querySelectorAll('td');
                        for (let i = 0; i < Math.min(tds.length, 4); i++) {
                            const txt = (tds[i].innerText || '').trim();
                            const dm = txt.match(/(\d{2})[/-](\d{2})[/-](\d{4})/);
                            if (dm) {
                                return `${dm[1]}-${dm[2]}-${dm[3]}`;
                            }
                        }
                        return '';
                    }
                    
                    // 1. Ekstrak dari link atau button cetak
                    const els = document.querySelectorAll('#table tbody tr a, #table tbody tr button, #table tbody tr [onclick], table tbody tr a, table tbody tr button');
                    els.forEach(el => {
                        const href = el.getAttribute('href') || '';
                        const onclick = el.getAttribute('onclick') || '';
                        const dataUrl = el.getAttribute('data-url') || el.getAttribute('data-href') || '';
                        const dataId = el.getAttribute('data-id') || '';
                        const combined = `${href} ${onclick} ${dataUrl} ${dataId}`;
                        
                        const m = combined.match(/exports\/pdf\/(\d{4,8})/i) || combined.match(/checklist.*?(\d{5,8})/i) || onclick.match(/['"](\d{5,8})['"]/);
                        let fid = null;
                        if (m) {
                            fid = m[1];
                        } else if (/^\d{5,8}$/.test(dataId)) {
                            fid = dataId;
                        }

                        if (fid && !seen.has(fid)) {
                            seen.add(fid);
                            const rowDate = extractRowDate(el.closest('tr'));
                            items.push({
                                id: fid,
                                url: `https://p3-ste.kai.id/cetak_checklist/report/${typeName}/exports/pdf/${fid}?false`,
                                date: rowDate
                            });
                        }
                    });
                    
                    // 2. Fallback: Ekstrak dari teks ID 6 digit di dalam baris tabel
                    if (items.length === 0) {
                        document.querySelectorAll('#table tbody tr, table tbody tr').forEach(tr => {
                            if (tr.querySelector('.dataTables_empty')) return;
                            const txt = tr.innerText || '';
                            const m = txt.match(/\b(\d{6,8})\b/);
                            if (m && !seen.has(m[1])) {
                                seen.add(m[1]);
                                const rowDate = extractRowDate(tr);
                                items.push({
                                    id: m[1],
                                    url: `https://p3-ste.kai.id/cetak_checklist/report/${typeName}/exports/pdf/${m[1]}?false`,
                                    date: rowDate
                                });
                            }
                        });
                    }
                    
                    return items;
                }""", type_name) or []

                # Filter item baru yang belum diunduh
                new_page_pdfs = [item for item in pdf_items if item["id"] not in downloaded_ids]
                _add_p3ste_log("info", f"Halaman {page_index}: Ditemukan {len(new_page_pdfs)} file PDF.")

                if len(new_page_pdfs) == 0:
                    # Beri kesempatan sekali lagi jika target data belum tercapai
                    if _p3ste_state["total"] > 0 and total_downloaded < _p3ste_state["total"]:
                        page.wait_for_timeout(2500)
                        pdf_items_retry = _safe_evaluate(page, r"""(typeName) => {
                            const items = [];
                            const seen = new Set();

                            function extractRowDate(tr) {
                                if (!tr) return '';
                                const tds = tr.querySelectorAll('td');
                                for (let i = 0; i < Math.min(tds.length, 4); i++) {
                                    const txt = (tds[i].innerText || '').trim();
                                    const dm = txt.match(/(\d{2})[/-](\d{2})[/-](\d{4})/);
                                    if (dm) {
                                        return `${dm[1]}-${dm[2]}-${dm[3]}`;
                                    }
                                }
                                return '';
                            }

                            const els = document.querySelectorAll('#table tbody tr a, #table tbody tr button, #table tbody tr [onclick], table tbody tr a, table tbody tr button');
                            els.forEach(el => {
                                const href = el.getAttribute('href') || '';
                                const onclick = el.getAttribute('onclick') || '';
                                const dataUrl = el.getAttribute('data-url') || el.getAttribute('data-href') || '';
                                const dataId = el.getAttribute('data-id') || '';
                                const combined = `${href} ${onclick} ${dataUrl} ${dataId}`;
                                
                                const m = combined.match(/exports\/pdf\/(\d{4,8})/i) || combined.match(/checklist.*?(\d{5,8})/i) || onclick.match(/['"](\d{5,8})['"]/);
                                let fid = null;
                                if (m) {
                                    fid = m[1];
                                } else if (/^\d{5,8}$/.test(dataId)) {
                                    fid = dataId;
                                }

                                if (fid && !seen.has(fid)) {
                                    seen.add(fid);
                                    const rowDate = extractRowDate(el.closest('tr'));
                                    items.push({
                                        id: fid,
                                        url: `https://p3-ste.kai.id/cetak_checklist/report/${typeName}/exports/pdf/${fid}?false`,
                                        date: rowDate
                                    });
                                }
                            });
                            if (items.length === 0) {
                                document.querySelectorAll('#table tbody tr, table tbody tr').forEach(tr => {
                                    if (tr.querySelector('.dataTables_empty')) return;
                                    const txt = tr.innerText || '';
                                    const m = txt.match(/\b(\d{6,8})\b/);
                                    if (m && !seen.has(m[1])) {
                                        seen.add(m[1]);
                                        const rowDate = extractRowDate(tr);
                                        items.push({
                                            id: m[1],
                                            url: `https://p3-ste.kai.id/cetak_checklist/report/${typeName}/exports/pdf/${m[1]}?false`,
                                            date: rowDate
                                        });
                                    }
                                });
                            }
                            return items;
                        }""", type_name) or []
                        new_page_pdfs = [item for item in pdf_items_retry if item["id"] not in downloaded_ids]
                        if len(new_page_pdfs) > 0:
                            _add_p3ste_log("info", f"Halaman {page_index} (Retry): Ditemukan {len(new_page_pdfs)} file PDF.")

                    if len(new_page_pdfs) == 0:
                        _add_p3ste_log("info", "Tidak ada file PDF baru pada halaman ini. Selesai.")
                        break

                for item in new_page_pdfs:
                    if _p3ste_state["cancelled"]: break
                    fid = item["id"]
                    pdf_url = item["url"]
                    downloaded_ids.add(fid)
                    
                    total_downloaded += 1
                    _p3ste_state["current"] = total_downloaded

                    # 1. Cek dari file checkpoint
                    cached_entry = checkpoint_data.get(str(fid))
                    if cached_entry:
                        c_name = cached_entry.get("name", f"checklist_{fid}.pdf")
                        c_path = os.path.join(target_folder, c_name)
                        if c_name not in session_filenames and os.path.isfile(c_path) and os.path.getsize(c_path) > 1000:
                            fsize = os.path.getsize(c_path)
                            _p3ste_state["downloaded_files"].append({
                                "name": c_name,
                                "path": c_path,
                                "size": fsize
                            })
                            session_filenames.add(c_name)
                            _add_p3ste_log("info", f"⏭️ [{total_downloaded}] {c_name} (Sudah ada, dilewati)")
                            continue

                    # 2. Cek apakah file fisik checklist_{fid}.pdf sudah ada di folder
                    default_fn = f"checklist_{fid}.pdf"
                    default_path = os.path.join(target_folder, default_fn)
                    if default_fn not in session_filenames and os.path.isfile(default_path) and os.path.getsize(default_path) > 1000:
                        fsize = os.path.getsize(default_path)
                        checkpoint_data[str(fid)] = {"name": default_fn, "size": fsize}
                        _p3ste_state["downloaded_files"].append({
                            "name": default_fn,
                            "path": default_path,
                            "size": fsize
                        })
                        session_filenames.add(default_fn)
                        _add_p3ste_log("info", f"⏭️ [{total_downloaded}] {default_fn} (Sudah ada di folder, dilewati)")
                        continue

                    # Unduh via context.request dengan Retry Otomatis
                    fn = default_fn
                    download_success = False
                    last_err = ""
                    max_attempts = 4

                    for attempt in range(max_attempts):
                        if _p3ste_state["cancelled"]: break
                        try:
                            fresp = context.request.get(pdf_url, timeout=35000)
                            if fresp.status == 200:
                                body = fresp.body()
                                if body[:4] == b"%PDF":
                                    cd = fresp.headers.get("content-disposition", "")
                                    if "filename=" in cd:
                                        cd_fn = re.search(r'filename=["\']?([^"\';]+)["\']?', cd)
                                        if cd_fn:
                                            fn = cd_fn.group(1).strip().strip('"').strip("'")

                                    # Koreksi tanggal filename jika berbeda dari kolom Tanggal tabel web
                                    table_date = item.get("date")
                                    corrected_fn, orig_date = _correct_filename_date(fn, table_date)
                                    if orig_date:
                                        _add_p3ste_log("warn", f"⚠️ Koreksi Tanggal [{orig_date} → {table_date}]: Nama file server '{fn}' disesuaikan dengan tanggal tabel web.")
                                        fn = corrected_fn

                                    fn, out_path = _get_unique_p3ste_filename(target_folder, fn, session_filenames)

                                    with open(out_path, "wb") as pf:
                                        pf.write(body)

                                    file_size = len(body)
                                    session_filenames.add(fn)
                                    checkpoint_data[str(fid)] = {"name": fn, "size": file_size}
                                    try:
                                        with open(checkpoint_file, "w", encoding="utf-8") as cf:
                                            json.dump(checkpoint_data, cf, indent=2)
                                    except Exception:
                                        pass

                                    _p3ste_state["downloaded_files"].append({
                                        "name": fn,
                                        "path": out_path,
                                        "size": file_size
                                    })
                                    retry_tag = f" (setelah coba ulang ke-{attempt})" if attempt > 0 else ""
                                    _add_p3ste_log("success", f"✓ [{total_downloaded}] Tersimpan: {fn} ({file_size // 1024} KB){retry_tag}")
                                    download_success = True
                                    break
                                else:
                                    last_err = "Bukan file PDF valid"
                            elif fresp.status in (500, 502, 503, 504, 429, 408):
                                last_err = f"HTTP {fresp.status}"
                                if attempt < max_attempts - 1:
                                    sleep_sec = 2.0 * (attempt + 1)
                                    _add_p3ste_log("warn", f"⚠️ [{total_downloaded}] {fn}: {last_err} - Server sibuk, mencoba ulang ({attempt + 1}/{max_attempts}) dalam {sleep_sec:.0f} detik...")
                                    time.sleep(sleep_sec)
                                    continue
                            else:
                                last_err = f"HTTP {fresp.status}"
                                break
                        except Exception as fe:
                            last_err = str(fe)
                            if attempt < max_attempts - 1:
                                sleep_sec = 2.0 * (attempt + 1)
                                _add_p3ste_log("warn", f"⚠️ [{total_downloaded}] {fn}: Error koneksi ({last_err}) - Mencoba ulang ({attempt + 1}/{max_attempts}) dalam {sleep_sec:.0f} detik...")
                                time.sleep(sleep_sec)
                                continue

                    if not download_success and not _p3ste_state["cancelled"]:
                        _add_p3ste_log("error", f"✗ [{total_downloaded}] {fn}: {last_err} (Gagal pada putaran pertama, akan dicoba ulang di akhir)")
                        failed_queue.append({
                            "id": fid,
                            "url": pdf_url,
                            "default_fn": default_fn,
                            "last_err": last_err,
                            "date": item.get("date")
                        })

                    if total_downloaded > _p3ste_state["total"]:
                        _p3ste_state["total"] = total_downloaded

                old_first_id = new_page_pdfs[0]["id"] if new_page_pdfs else None

                # Pengecekan halaman selanjutnya (Next Page) dengan retry cerdas
                max_next_retries = 3 if (_p3ste_state["total"] > 0 and total_downloaded < _p3ste_state["total"]) else 1
                page_changed = False

                for next_attempt in range(max_next_retries):
                    if _p3ste_state["cancelled"]:
                        break

                    can_go_next = _safe_evaluate(page, """() => {
                        // 1. Cek DOM Tombol Next
                        const nextLi = document.querySelector('li#table_next, #table_next, li.paginate_button.next, li.next, #tblData_next');
                        if (nextLi && !nextLi.classList.contains('disabled') && nextLi.getAttribute('aria-disabled') !== 'true') {
                            const a = nextLi.querySelector('a') || nextLi;
                            a.click();
                            return { hasNext: true, method: 'dom' };
                        }
                        // 2. Cek DataTables API
                        if (typeof $ !== 'undefined' && $.fn.DataTable) {
                            const tables = Array.from(document.querySelectorAll('table'));
                            for (const tbl of tables) {
                                if ($.fn.DataTable.isDataTable(tbl)) {
                                    const info = $(tbl).DataTable().page.info();
                                    if (info && info.page < info.pages - 1) {
                                        $(tbl).DataTable().page('next').draw('page');
                                        return { hasNext: true, page: info.page + 2, totalPages: info.pages, method: 'api' };
                                    }
                                }
                            }
                        }
                        return { hasNext: false };
                    }""") or {}

                    if not can_go_next.get("hasNext"):
                        # Jika menurut indikator halaman habis tapi target belum terpenuhi, tunggu 2.5s lalu periksa ulang
                        if _p3ste_state["total"] > 0 and total_downloaded < _p3ste_state["total"] and next_attempt < max_next_retries - 1:
                            _add_p3ste_log("warn", f"⏳ Memverifikasi status pagination ({total_downloaded}/{_p3ste_state['total']} data)...")
                            page.wait_for_timeout(2500)
                            continue
                        _add_p3ste_log("info", "Mencapai halaman terakhir.")
                        break

                    if next_attempt == 0:
                        _add_p3ste_log("info", f"Mengeklik 'Selanjutnya' ke Halaman {page_index + 1}...")
                    else:
                        _add_p3ste_log("warn", f"Mencoba ulang klik 'Selanjutnya' ke Halaman {page_index + 1} (Percobaan {next_attempt + 1}/{max_next_retries})...")

                    # Tunggu proses AJAX DataTables selesai memuat halaman berikutnya (hingga 60 detik)
                    for wait_sec in range(60):
                        if _p3ste_state["cancelled"]: break
                        page.wait_for_timeout(1000)

                        # Re-click jika setelah 25 detik server belum merespons
                        if wait_sec == 25:
                            _safe_evaluate(page, """() => {
                                const nextLi = document.querySelector('li#table_next, #table_next, li.paginate_button.next, li.next, #tblData_next');
                                if (nextLi && !nextLi.classList.contains('disabled')) {
                                    const a = nextLi.querySelector('a') || nextLi;
                                    a.click();
                                }
                            }""")

                        cur_first_id = _safe_evaluate(page, r"""() => {
                            const tr = document.querySelector('#table tbody tr, table tbody tr');
                            if (!tr || tr.querySelector('.dataTables_empty')) return null;
                            const m = (tr.innerHTML || '').match(/exports\/pdf\/(\d{4,8})|['"](\d{5,8})['"]/i);
                            if (m) return m[1] || m[2];
                            const txtMatch = (tr.innerText || '').match(/\b(\d{6,8})\b/);
                            return txtMatch ? txtMatch[1] : null;
                        }""")

                        if cur_first_id and cur_first_id != old_first_id:
                            page_changed = True
                            break

                    if page_changed:
                        break

                if not page_changed:
                    if _p3ste_state["total"] > 0 and total_downloaded < _p3ste_state["total"]:
                        _add_p3ste_log("warn", f"⚠️ Halaman berikutnya tidak merespons setelah beberapa percobaan. Pengunduhan diselesaikan pada {total_downloaded} dari target {_p3ste_state['total']} data.")
                    else:
                        _add_p3ste_log("info", "Halaman berikutnya tidak memuat data baru. Selesai.")
                    break

                page_index += 1
                page.wait_for_timeout(1500)

            # Putaran Kedua: Coba ulang file yang sempat gagal pada putaran pertama
            if failed_queue and not _p3ste_state["cancelled"]:
                _add_p3ste_log("warn", f"🔄 Ditemukan {len(failed_queue)} file yang sempat gagal. Memulai putaran coba ulang otomatis...")
                time.sleep(2.5)
                still_failed = []
                for idx, failed_item in enumerate(failed_queue, 1):
                    if _p3ste_state["cancelled"]: break
                    ffid = failed_item["id"]
                    furl = failed_item["url"]
                    ffn = failed_item["default_fn"]
                    _add_p3ste_log("info", f"🔄 [Coba Ulang {idx}/{len(failed_queue)}] ID {ffid}...")

                    retry_ok = False
                    for r_att in range(3):
                        if _p3ste_state["cancelled"]: break
                        try:
                            fresp = context.request.get(furl, timeout=35000)
                            if fresp.status == 200:
                                body = fresp.body()
                                if body[:4] == b"%PDF":
                                    cd = fresp.headers.get("content-disposition", "")
                                    if "filename=" in cd:
                                        cd_fn = re.search(r'filename=["\']?([^"\';]+)["\']?', cd)
                                        if cd_fn:
                                            ffn = cd_fn.group(1).strip().strip('"').strip("'")

                                    # Koreksi tanggal filename jika berbeda dari kolom Tanggal tabel web
                                    table_date = failed_item.get("date")
                                    corrected_ffn, orig_date = _correct_filename_date(ffn, table_date)
                                    if orig_date:
                                        _add_p3ste_log("warn", f"⚠️ Koreksi Tanggal [{orig_date} → {table_date}]: Nama file server '{ffn}' disesuaikan dengan tanggal tabel web.")
                                        ffn = corrected_ffn

                                    ffn, out_path = _get_unique_p3ste_filename(target_folder, ffn, session_filenames)

                                    with open(out_path, "wb") as pf:
                                        pf.write(body)

                                    file_size = len(body)
                                    session_filenames.add(ffn)
                                    checkpoint_data[str(ffid)] = {"name": ffn, "size": file_size}
                                    try:
                                        with open(checkpoint_file, "w", encoding="utf-8") as cf:
                                            json.dump(checkpoint_data, cf, indent=2)
                                    except Exception:
                                        pass

                                    _p3ste_state["downloaded_files"].append({
                                        "name": ffn,
                                        "path": out_path,
                                        "size": file_size
                                    })
                                    _add_p3ste_log("success", f"✓ Berhasil diunduh pada putaran ulang: {ffn} ({file_size // 1024} KB)")
                                    retry_ok = True
                                    break
                                else:
                                    time.sleep(2.0)
                            else:
                                time.sleep(2.0)
                        except Exception:
                            time.sleep(2.0)

                    if not retry_ok:
                        still_failed.append(failed_item)

                if still_failed:
                    _add_p3ste_log("error", f"❌ {len(still_failed)} file tetap gagal diunduh setelah coba ulang: {', '.join(str(x['id']) for x in still_failed[:5])}")
                else:
                    _add_p3ste_log("success", "🎉 Semua file yang sempat gagal berhasil diunduh 100% pada putaran ulang!")

            if _p3ste_state["cancelled"]:
                _add_p3ste_log("warn", "🛑 Pengunduhan dihentikan oleh pengguna.")
            else:
                success_count = len(_p3ste_state['downloaded_files'])
                target_tot = _p3ste_state['total']
                if target_tot > 0 and success_count >= target_tot:
                    _add_p3ste_log("success", f"🎉 Selesai! Semua {success_count} dari {target_tot} file PDF berhasil diunduh 100%.")
                else:
                    _add_p3ste_log("success", f"Selesai! Berhasil mengunduh total {success_count} file PDF dari semua halaman.")

            try:
                context.close()
            except Exception:
                pass
            _current_playwright_context = None

    except Exception as e:
        if _p3ste_state["cancelled"]:
            _add_p3ste_log("warn", "🛑 Semua proses berhasil dihentikan oleh pengguna.")
        else:
            _p3ste_state["error"] = str(e)
            _add_p3ste_log("error", f"FATAL ERROR: {e}")
    finally:
        _current_playwright_context = None
        _p3ste_state["running"] = False


def on_restored():
    """Keep state intact. No page reload — env flags already prevent blank screen."""
    global _was_minimized
    _log(f"🟢 EVENT: restored (was_minimized={_was_minimized})")
    _was_minimized = False


def _pick_folder_native():
    """Buka dialog pemilihan folder di Windows:
    1. Tkinter askdirectory (Topmost, native OS dialog, paling stabil & cepat)
    2. pywebview create_file_dialog (jika native window aktif)
    3. PowerShell WinForms fallback
    """
    # 1. Tkinter (Topmost dialog)
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(title="Pilih Folder Penyimpanan PDF Rekap")
        root.destroy()
        if folder and os.path.isdir(folder):
            return os.path.normpath(folder)
    except Exception as e:
        _log(f"Tkinter folder picker notice: {e}")

    # 2. Coba via pywebview jika window aktif
    try:
        if getattr(webview, 'windows', None) and len(webview.windows) > 0:
            dialog_type = getattr(webview.FileDialog, 'FOLDER', getattr(webview, 'FOLDER_DIALOG', 2))
            result = webview.windows[0].create_file_dialog(dialog_type)
            if result and len(result) > 0 and result[0]:
                return os.path.normpath(result[0])
    except Exception as e:
        _log(f"WebView file dialog notice: {e}")

    # 3. Fallback via PowerShell WinForms
    try:
        import subprocess
        ps_cmd = [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "Add-Type -AssemblyName System.Windows.Forms; $f = New-Object System.Windows.Forms.FolderBrowserDialog; $f.Description = 'Pilih Folder Penyimpanan'; $f.ShowNewFolderButton = $true; if($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK){ [Console]::Out.Write($f.SelectedPath) }"
        ]
        res = subprocess.run(
            ps_cmd,
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        )
        path = res.stdout.strip()
        if path and os.path.isdir(path):
            return os.path.normpath(path)
    except Exception as e:
        _log(f"PowerShell folder dialog fallback error: {e}")

    return None


def _pick_file_native():
    """Buka dialog pemilihan file di Windows:
    1. Tkinter askopenfilename (Topmost)
    2. pywebview create_file_dialog OPEN
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        fpath = filedialog.askopenfilename(
            title="Pilih Berkas PDF atau schedule.json",
            filetypes=[("PDF atau JSON", "*.pdf;*.json"), ("Semua Berkas", "*.*")]
        )
        root.destroy()
        if fpath and os.path.isfile(fpath):
            return os.path.normpath(fpath)
    except Exception as e:
        _log(f"Tkinter file picker notice: {e}")

    try:
        if getattr(webview, 'windows', None) and len(webview.windows) > 0:
            dialog_type = getattr(webview.FileDialog, 'OPEN', getattr(webview, 'OPEN_DIALOG', 10))
            result = webview.windows[0].create_file_dialog(
                dialog_type,
                file_types=("PDF & JSON (*.pdf;*.json)", "Semua Berkas (*.*)")
            )
            if result and len(result) > 0 and result[0]:
                return os.path.normpath(result[0])
    except Exception as e:
        _log(f"WebView file dialog notice: {e}")

    return None


def _save_file_dialog_native(default_name):
    """Opens a native Windows Save As file dialog."""
    # 1. Coba via pywebview jika window aktif (Native Windows FileDialog)
    try:
        if getattr(webview, 'windows', None) and len(webview.windows) > 0:
            dialog_type = getattr(webview.FileDialog, 'SAVE', getattr(webview, 'SAVE_DIALOG', 30))
            ext = os.path.splitext(default_name)[1]
            file_types = ('Excel Files (*.xlsx)', 'All files (*.*)') if ext == '.xlsx' else ('All files (*.*)',)
            result = webview.windows[0].create_file_dialog(
                dialog_type,
                save_filename=default_name,
                file_types=file_types
            )
            if result:
                if isinstance(result, (list, tuple)) and len(result) > 0:
                    return os.path.normpath(result[0])
                elif isinstance(result, str):
                    return os.path.normpath(result)
            return None
    except Exception as e:
        _log(f"WebView save dialog notice: {e}")

    # 2. Coba via Tkinter (Dev mode jika tkinter tersedia)
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        ext = os.path.splitext(default_name)[1]
        filetypes = [("Excel Files", "*.xlsx"), ("All Files", "*.*")] if ext == ".xlsx" else [("All Files", "*.*")]
        path = filedialog.asksaveasfilename(
            initialfile=default_name,
            filetypes=filetypes,
            defaultextension=ext
        )
        root.destroy()
        if path:
            return os.path.normpath(path)
    except Exception as e:
        _log(f"Tkinter save dialog notice: {e}")

    # 3. Fallback via PowerShell WinForms
    try:
        ext = os.path.splitext(default_name)[1]
        ps_cmd = [
            "powershell.exe",
            "-NoProfile",
            "-Sta",
            "-Command",
            f"Add-Type -AssemblyName System.Windows.Forms; $f = New-Object System.Windows.Forms.SaveFileDialog; $f.FileName = '{default_name}'; $f.Filter = 'Files (*{ext})|*{ext}|All files (*.*)|*.*'; if($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK){{ [Console]::Out.Write($f.FileName) }}"
        ]
        res = subprocess.run(
            ps_cmd,
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        )
        path = res.stdout.strip()
        if path:
            return os.path.normpath(path)
    except Exception as ps_err:
        _log(f"PowerShell save dialog notice: {ps_err}")

    return None


class ApiHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler: serve static files + /api/* endpoints"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIST_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/p3ste/status":
            self._json(_p3ste_state)
        elif parsed.path == "/api/accounts":
            self._handle_get_accounts()
        elif parsed.path == "/api/get-file":
            self._handle_get_file(parsed)
        elif parsed.path == "/api/list-folder-pdfs":
            self._handle_list_folder_pdfs(parsed)
        elif parsed.path == "/api/timemark/status":
            self._json(pipeline_runner.get_state())
        elif parsed.path == "/api/timemark/photos":
            self._handle_timemark_photos(parsed)
        elif parsed.path == "/api/timemark/photo-file":
            self._handle_timemark_photo_file(parsed)
        elif parsed.path == "/api/timemark/pegawai":
            self._handle_timemark_pegawai_get()
        elif parsed.path == "/api/update/check":
            qs = urllib.parse.parse_qs(parsed.query)
            custom_url = qs.get("url", [None])[0]
            self._json(updater_engine.check_update(custom_url))
        elif parsed.path == "/api/update/progress":
            self._json(updater_engine.get_update_state())
        else:
            super().do_GET()

    def _handle_get_accounts(self):
        try:
            if os.path.isfile(ACCOUNTS_FILE):
                with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._json(data)
            else:
                self._json({"accounts": [], "selected_id": "acc_default"})
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _handle_save_accounts(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._json({"ok": True})
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _handle_get_file(self, parsed):
        try:
            qs = urllib.parse.parse_qs(parsed.query)
            file_path = qs.get("path", [""])[0]
            if not file_path or not os.path.isfile(file_path):
                self.send_error(404, "File tidak ditemukan")
                return
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _handle_list_folder_pdfs(self, parsed):
        try:
            qs = urllib.parse.parse_qs(parsed.query)
            folder = qs.get("folder", [""])[0]
            if not folder or not os.path.isdir(folder):
                self._json({"files": []})
                return
            files = []
            for fn in sorted(os.listdir(folder)):
                if fn.lower().endswith(".pdf"):
                    fp = os.path.join(folder, fn)
                    if os.path.isfile(fp):
                        files.append({
                            "name": fn,
                            "path": fp,
                            "size": os.path.getsize(fp)
                        })
            self._json({"files": files})
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/select-folder":
            self._handle_select_folder()
        elif parsed.path == "/api/select-file":
            self._handle_select_file()
        elif parsed.path == "/api/accounts":
            self._handle_save_accounts()
        elif parsed.path == "/api/save-file":
            self._handle_save_file()
        elif parsed.path == "/api/save-dialog-file":
            self._handle_save_dialog_file()
        elif parsed.path == "/api/ocr":
            self._handle_ocr()
        elif parsed.path == "/api/p3ste/download":
            self._handle_p3ste_download()
        elif parsed.path == "/api/p3ste/status":
            self._json(_p3ste_state)
        elif parsed.path == "/api/p3ste/cancel":
            _cancel_all_processes()
            self._json({"ok": True})
        elif parsed.path == "/api/timemark/start":
            self._handle_timemark_start()
        elif parsed.path == "/api/timemark/cancel":
            pipeline_runner.cancel_pipeline()
            self._json({"ok": True})
        elif parsed.path == "/api/timemark/edit-time":
            self._handle_timemark_edit_time()
        elif parsed.path == "/api/timemark/edit-coord":
            self._handle_timemark_edit_coord()
        elif parsed.path == "/api/timemark/replace-photo":
            self._handle_timemark_replace_photo()
        elif parsed.path == "/api/timemark/pegawai":
            self._handle_timemark_pegawai_post()
        elif parsed.path == "/api/timemark/koreksi-serat-optik":
            self._handle_timemark_koreksi_serat_optik()
        elif parsed.path == "/api/timemark/audit-personil":
            self._handle_timemark_audit_personil()
        elif parsed.path == "/api/timemark/export-tablo":
            self._handle_timemark_export_tablo()
        elif parsed.path == "/api/timemark/export-dinasan":
            self._handle_timemark_export_dinasan()
        elif parsed.path == "/api/timemark/open-file":
            self._handle_timemark_open_file()
        elif parsed.path == "/api/update/download":
            self._handle_update_download()
        elif parsed.path == "/api/update/apply":
            self._json(updater_engine.apply_update_and_restart())
        else:
            self.send_error(404)

    def _handle_timemark_start(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body) if body else {}
            res = pipeline_runner.start_pipeline(
                data.get("sourceDir"),
                data.get("targetDir"),
                data.get("exportDir"),
                data.get("mergedDir"),
                data.get("steps"),
                data.get("mode", "dual"),
                data.get("overwriteOriginal", False)
            )
            self._json(res)
        except Exception as e:
            _log(f"Timemark start error: {e}")
            self._json({"error": str(e)}, 500)

    def _handle_timemark_photos(self, parsed):
        try:
            qs = urllib.parse.parse_qs(parsed.query)
            folder = qs.get("folder", [""])[0]
            if not folder or not os.path.isdir(folder):
                self._json({"ok": True, "assets": []})
                return

            assets = []
            for root, dirs, files in os.walk(folder):
                photo_files = [f for f in files if f.lower() in ("0.jpg", "50.jpg", "100.jpg")]
                if not photo_files:
                    continue

                rel_path = os.path.relpath(root, folder).replace("\\", "/")
                parts = [p for p in rel_path.split("/") if p]
                if not parts:
                    continue

                detail = parts[-1]
                category = parts[-2] if len(parts) >= 2 else "ASET"
                station = parts[-3] if len(parts) >= 3 else (parts[0] if len(parts) >= 1 else "STN")
                if station.lower().startswith("tim_") and len(parts) >= 4:
                    station = parts[-3]
                    category = parts[-2]

                date_text = ""
                date_file = os.path.join(root, "date.txt")
                if os.path.isfile(date_file):
                    try:
                        with open(date_file, "r", encoding="utf-8", errors="ignore") as df:
                            date_text = df.read().strip()
                    except Exception:
                        pass

                photos = []
                for p_name in ["0.jpg", "50.jpg", "100.jpg"]:
                    p_file = os.path.join(root, p_name)
                    if os.path.isfile(p_file):
                        photos.append({
                            "name": p_name,
                            "url": f"/api/timemark/photo-file?path={urllib.parse.quote(os.path.abspath(p_file))}"
                        })

                assets.append({
                    "station": station,
                    "category": category,
                    "detail": detail,
                    "relPath": rel_path,
                    "dateText": date_text,
                    "photos": photos
                })

            assets.sort(key=lambda a: (a["station"], a["category"], a["detail"]))
            self._json({"ok": True, "assets": assets})
        except Exception as e:
            _log(f"Error scanning photos: {e}")
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_timemark_photo_file(self, parsed):
        try:
            qs = urllib.parse.parse_qs(parsed.query)
            file_path = qs.get("path", [""])[0]
            if not file_path or not os.path.isfile(file_path):
                self.send_error(404, "Berkas foto tidak ditemukan")
                return
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, str(e))

    def _handle_timemark_pegawai_get(self):
        try:
            pegawai_file = os.path.join(ENGINE_DIR, "daftar_pegawai.json")
            presets_file = os.path.join(ENGINE_DIR, "employee_presets.json")

            daftar_pegawai = {}
            if os.path.isfile(pegawai_file):
                with open(pegawai_file, "r", encoding="utf-8") as f:
                    daftar_pegawai = json.load(f)

            presets_data = {}
            if os.path.isfile(presets_file):
                with open(presets_file, "r", encoding="utf-8") as f:
                    presets_data = json.load(f)

            self._json({
                "ok": True,
                "daftar_pegawai": daftar_pegawai,
                "presets": presets_data.get("presets", []),
                "active_preset_id": presets_data.get("active_preset_id", "")
            })
        except Exception as e:
            _log(f"Get pegawai error: {e}")
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_timemark_pegawai_post(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body) if body else {}

            pegawai_file = os.path.join(ENGINE_DIR, "daftar_pegawai.json")
            presets_file = os.path.join(ENGINE_DIR, "employee_presets.json")

            if "daftar_pegawai" in data:
                with open(pegawai_file, "w", encoding="utf-8") as f:
                    json.dump(data["daftar_pegawai"], f, indent=2, ensure_ascii=False)

            if "presets" in data or "active_preset_id" in data:
                existing_presets = {}
                if os.path.isfile(presets_file):
                    try:
                        with open(presets_file, "r", encoding="utf-8") as f:
                            existing_presets = json.load(f)
                    except Exception:
                        pass
                if "presets" in data:
                    existing_presets["presets"] = data["presets"]
                if "active_preset_id" in data:
                    existing_presets["active_preset_id"] = data["active_preset_id"]
                with open(presets_file, "w", encoding="utf-8") as f:
                    json.dump(existing_presets, f, indent=2, ensure_ascii=False)

            self._json({"ok": True, "message": "Profil pegawai berhasil disimpan."})
        except Exception as e:
            _log(f"Save pegawai error: {e}")
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_timemark_edit_time(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body) if body else {}
            base_dir = data.get("baseExportDir", "")
            rel_path = data.get("assetRelPath", "")
            new_date = data.get("newDateText", "").strip()
            if not base_dir or not rel_path or not new_date:
                self._json({"ok": False, "error": "Parameter tidak lengkap."}, 400)
                return

            target_folder = os.path.normpath(os.path.join(base_dir, rel_path))
            if not os.path.isdir(target_folder):
                self._json({"ok": False, "error": "Folder aset tidak ditemukan."}, 404)
                return

            date_file = os.path.join(target_folder, "date.txt")
            with open(date_file, "w", encoding="utf-8") as df:
                df.write(new_date + "\n")

            cmd = [
                sys.executable,
                os.path.join(ENGINE_DIR, "edit_timemark_ide1.py"),
                "--input", target_folder,
                "--date", new_date,
                "--detector", "guide"
            ]
            subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
            self._json({"ok": True, "message": "Waktu timemark berhasil diperbarui."})
        except Exception as e:
            _log(f"Edit time error: {e}")
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_timemark_edit_coord(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body) if body else {}
            base_dir = data.get("baseExportDir", "")
            rel_path = data.get("assetRelPath", "")
            photo_name = data.get("photoName", "0.jpg")
            y_override = int(data.get("yOverride", 195))

            target_photo = os.path.normpath(os.path.join(base_dir, rel_path, photo_name))
            if not os.path.isfile(target_photo):
                self._json({"ok": False, "error": "Berkas foto tidak ditemukan."}, 404)
                return

            cmd = [
                sys.executable,
                os.path.join(ENGINE_DIR, "edit_timemark_ide1.py"),
                "--input", target_photo,
                "--y-override", str(y_override),
                "--detector", "guide"
            ]
            subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
            self._json({"ok": True, "message": f"Koordinat y={y_override} berhasil diterapkan."})
        except Exception as e:
            _log(f"Edit coord error: {e}")
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_timemark_replace_photo(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body) if body else {}
            base_dir = data.get("baseExportDir", "")
            rel_path = data.get("assetRelPath", "")
            photo_name = data.get("photoName", "0.jpg")
            img_b64 = data.get("imageBase64", "")

            if not img_b64:
                self._json({"ok": False, "error": "Data gambar kosong."}, 400)
                return

            target_photo = os.path.normpath(os.path.join(base_dir, rel_path, photo_name))
            if not os.path.isfile(target_photo):
                self._json({"ok": False, "error": "Berkas foto tujuan tidak ditemukan."}, 404)
                return

            backup_file = target_photo + ".original_backup.jpg"
            if not os.path.isfile(backup_file):
                shutil.copy2(target_photo, backup_file)

            raw_bytes = base64.b64decode(img_b64)
            with open(target_photo, "wb") as pf:
                pf.write(raw_bytes)

            cmd = [
                sys.executable,
                os.path.join(ENGINE_DIR, "edit_timemark_ide1.py"),
                "--input", target_photo,
                "--detector", "guide"
            ]
            subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
            self._json({"ok": True, "message": "Foto berhasil diganti dan di-watermark ulang."})
        except Exception as e:
            _log(f"Replace photo error: {e}")
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_timemark_koreksi_serat_optik(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body) if body else {}
            folder = data.get("folder", "")
            apply_corr = bool(data.get("apply", False))

            if not folder or not os.path.isdir(folder):
                self._json({"ok": False, "error": "Folder PDF tidak valid."}, 400)
                return

            cmd = [
                sys.executable,
                os.path.join(ENGINE_DIR, "correct_serat_optik_cores.py"),
                "--folders", folder,
                "--json"
            ]
            if apply_corr:
                cmd.append("--apply")

            res = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
            items = []
            if res.stdout:
                try:
                    items = json.loads(res.stdout)
                except Exception:
                    match = re.search(r'\[\s*\{.*\}\s*\]', res.stdout, re.DOTALL)
                    if match:
                        items = json.loads(match.group(0))

            self._json({"ok": True, "items": items})
        except Exception as e:
            _log(f"Koreksi serat optik error: {e}")
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_timemark_audit_personil(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body) if body else {}
            folder = data.get("folder", "")
            action = data.get("action", "audit")

            if not folder or not os.path.isdir(folder):
                self._json({"ok": False, "error": "Folder PDF tidak valid."}, 400)
                return

            cmd = [
                sys.executable,
                os.path.join(ENGINE_DIR, "audit_and_correct_personnel.py"),
                "--folder", folder,
                "--action", action
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
            report = {}
            if res.stdout:
                try:
                    report = json.loads(res.stdout)
                except Exception:
                    match = re.search(r'\{.*\}', res.stdout, re.DOTALL)
                    if match:
                        report = json.loads(match.group(0))

            self._json({"ok": True, "result": report})
        except Exception as e:
            _log(f"Audit personil error: {e}")
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_timemark_export_tablo(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body) if body else {}
            folder = data.get("folder")
            export_dir = data.get("exportDir")
            year = data.get("year")
            month = data.get("month")

            out_dir = os.path.join(BASE_DIR, "logs")
            os.makedirs(out_dir, exist_ok=True)

            cmd = [
                sys.executable,
                os.path.join(ENGINE_DIR, "export_tablo_excel.py"),
                "--output-dir", out_dir
            ]
            if year:
                cmd.extend(["--year", str(year)])
            if month:
                cmd.extend(["--month", str(month)])

            if folder:
                if os.path.isfile(folder):
                    if folder.lower().endswith(".json"):
                        cmd.extend(["--mode", "pipeline", "--schedule", folder])
                    else:
                        cmd.extend(["--mode", "custom", "--folder", os.path.dirname(folder)])
                elif os.path.isdir(folder):
                    if os.path.isfile(os.path.join(folder, "schedule.json")):
                        cmd.extend(["--mode", "pipeline", "--schedule", os.path.join(folder, "schedule.json")])
                    else:
                        cmd.extend(["--mode", "custom", "--folder", folder])
            elif export_dir and os.path.isfile(os.path.join(export_dir, "schedule.json")):
                cmd.extend(["--mode", "pipeline", "--schedule", os.path.join(export_dir, "schedule.json")])

            res = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
            file_path = None
            if res.stdout:
                for line in res.stdout.splitlines():
                    if "[OUTPUT_FILE]" in line:
                        file_path = line.replace("[OUTPUT_FILE]", "").strip()
                        break

            if not file_path:
                cand = [os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.startswith("TABLO") and f.endswith(".xlsx")]
                if cand:
                    cand.sort(key=os.path.getmtime, reverse=True)
                    file_path = cand[0]

            if file_path and os.path.isfile(file_path):
                self._json({"ok": True, "filePath": file_path})
            else:
                self._json({"ok": False, "error": res.stderr or "Gagal membuat berkas Tablo Excel."})
        except Exception as e:
            _log(f"Export tablo error: {e}")
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_timemark_export_dinasan(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body) if body else {}
            folder = data.get("folder")
            export_dir = data.get("exportDir")
            year = data.get("year", datetime.now().year)
            month = data.get("month", datetime.now().month)
            with_personnel = data.get("withPersonnel", True)

            out_dir = os.path.join(BASE_DIR, "logs")
            os.makedirs(out_dir, exist_ok=True)
            month_str = f"{year}-{int(month):02d}"

            sch_path = None
            if folder:
                if os.path.isfile(folder) and folder.lower().endswith(".json"):
                    sch_path = folder
                elif os.path.isfile(folder):
                    folder_dir = os.path.dirname(folder)
                    temp_sch = os.path.join(out_dir, "temp_dinasan_schedule.json")
                    subprocess.run([
                        sys.executable, os.path.join(ENGINE_DIR, "scheduler.py"),
                        "--pdf-dir", folder_dir,
                        "--output", temp_sch
                    ], capture_output=True, text=True, cwd=BASE_DIR)
                    if os.path.isfile(temp_sch):
                        sch_path = temp_sch
                elif os.path.isdir(folder):
                    if os.path.isfile(os.path.join(folder, "schedule.json")):
                        sch_path = os.path.join(folder, "schedule.json")
                    else:
                        temp_sch = os.path.join(out_dir, "temp_dinasan_schedule.json")
                        subprocess.run([
                            sys.executable, os.path.join(ENGINE_DIR, "scheduler.py"),
                            "--pdf-dir", folder,
                            "--output", temp_sch
                        ], capture_output=True, text=True, cwd=BASE_DIR)
                        if os.path.isfile(temp_sch):
                            sch_path = temp_sch
            elif export_dir and os.path.isfile(os.path.join(export_dir, "schedule.json")):
                sch_path = os.path.join(export_dir, "schedule.json")

            if not sch_path:
                sch_path = os.path.join(out_dir, "temp_dinasan_schedule.json")

            cmd = [
                sys.executable,
                os.path.join(ENGINE_DIR, "export_dinasan_excel.py"),
                "--month", month_str,
                "--schedule", sch_path,
                "--config", os.path.join(ENGINE_DIR, "daftar_pegawai.json")
            ]
            if with_personnel:
                cmd.append("--with-personnel")

            res = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
            file_path = None
            if res.stdout:
                for line in res.stdout.splitlines():
                    if "->" in line:
                        file_path = line.split("->")[-1].strip()
                        break

            if not file_path:
                cand = [os.path.join(out_dir, f) for f in os.listdir(out_dir) if "DAFTAR_DINASAN_PEGAWAI" in f and f.endswith(".xlsx")]
                if cand:
                    cand.sort(key=os.path.getmtime, reverse=True)
                    file_path = cand[0]

            if file_path and os.path.isfile(file_path):
                self._json({"ok": True, "filePath": file_path})
            else:
                self._json({"ok": False, "error": res.stderr or "Gagal membuat berkas Jadwal Dinasan Excel."})
        except Exception as e:
            _log(f"Export dinasan error: {e}")
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_timemark_open_file(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body) if body else {}
            file_path = data.get("filePath", "")
            if not file_path or not os.path.exists(file_path):
                self._json({"ok": False, "error": "Berkas tidak ditemukan."}, 404)
                return

            norm = os.path.normpath(file_path)
            os.startfile(norm)
            self._json({"ok": True})
        except Exception as e:
            _log(f"Open file error: {e}")
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_update_download(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body) if body else {}
            url = data.get("downloadUrl")
            res = updater_engine.start_download(url)
            self._json(res)
        except Exception as e:
            _log(f"Update download error: {e}")
            self._json({"error": str(e)}, 500)

    def _handle_save_dialog_file(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            filename = data.get("filename", "Export.xlsx")
            b64data = data.get("data", "")
            
            save_path = _save_file_dialog_native(filename)
            if save_path:
                parent_dir = os.path.dirname(save_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                raw = base64.b64decode(b64data)
                with open(save_path, "wb") as f:
                    f.write(raw)
                self._json({"ok": True, "path": save_path})
            else:
                self._json({"ok": False, "cancelled": True})
        except Exception as e:
            _log(f"Save dialog file error: {e}")
            self._json({"error": str(e)}, 500)

    def _handle_select_folder(self):
        global _selected_folder
        try:
            folder = _pick_folder_native()
            if folder:
                _selected_folder = folder
                self._json({"path": _selected_folder, "name": os.path.basename(_selected_folder)})
            else:
                self._json({"path": None, "name": None})
        except Exception as e:
            _log(f"Folder selection error: {e}")
            self._json({"error": str(e)}, 500)

    def _handle_select_file(self):
        try:
            fpath = _pick_file_native()
            if fpath:
                self._json({"path": fpath, "name": os.path.basename(fpath)})
            else:
                self._json({"path": None, "name": None})
        except Exception as e:
            _log(f"File selection error: {e}")
            self._json({"error": str(e)}, 500)

    def _handle_save_file(self):
        global _selected_folder
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length))
            filename = str(data.get("filename", ""))
            relative = str(data.get("relativePath") or filename).replace("\\\\", "/")
            conflict = str(data.get("conflictMode") or "rename").lower()
            folder = data.get("folder") or _selected_folder
            if not folder:
                self._json({"error": "Folder tujuan penyimpanan belum ditentukan."}, 400)
                return
            if conflict not in {"rename", "skip", "overwrite"}:
                self._json({"error": "Mode konflik tidak valid."}, 400)
                return
            parts = [part for part in relative.split("/") if part]
            if not parts or any(part in {".", ".."} or ":" in part for part in parts):
                self._json({"error": "Path tujuan tidak aman."}, 400)
                return
            root = os.path.abspath(folder)
            path = os.path.abspath(os.path.join(root, *parts))
            if os.path.commonpath([root, path]) != root:
                self._json({"error": "Path tujuan berada di luar folder root."}, 400)
                return
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if os.path.exists(path):
                if conflict == "skip":
                    return self._json({"ok": True, "status": "skipped", "path": path})
                if conflict == "rename":
                    stem, ext = os.path.splitext(path)
                    counter = 2
                    candidate = path
                    while os.path.exists(candidate):
                        candidate = f"{stem} ({counter}){ext}"
                        counter += 1
                    path = candidate
            raw = base64.b64decode(data.get("data", ""))
            with open(path, "wb") as f:
                f.write(raw)
            _log(f"Saved: {path}")
            self._json({"ok": True, "status": "saved", "path": path})
        except Exception as e:
            _log(f"Save file error ({filename}): {e}")
            self._json({"error": f"{filename}: {str(e)}"}, 500)

    def _handle_ocr(self):
        """Endpoint /api/ocr — OCR PDF pakai Tesseract desktop (fallback dari Tesseract.js).
        Menerima JSON: {"data": "<base64 PDF>"} → return {"text": "hasil OCR"}"""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            b64data = data.get("data", "")
            if not b64data:
                self._json({"error": "missing data field"}, 400)
                return

            # Simpan PDF sementara
            pdf_bytes = base64.b64decode(b64data)
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = tmp.name

            try:
                # Konfigurasi Tesseract & Poppler
                tess_cmd = get_tesseract_cmd()
                if os.path.exists(tess_cmd):
                    pytesseract.pytesseract.tesseract_cmd = tess_cmd
                    tessdata_dir = os.path.join(os.path.dirname(tess_cmd), "tessdata")
                    if os.path.isdir(tessdata_dir):
                        os.environ["TESSDATA_PREFIX"] = tessdata_dir

                poppler_dir = get_poppler_dir()
                # Render halaman pertama
                images = convert_from_path(
                    tmp_path, dpi=200, first_page=1, last_page=1,
                    poppler_path=poppler_dir if (poppler_dir and os.path.exists(poppler_dir)) else None
                )
                if not images:
                    self._json({"text": ""})
                    return

                img = images[0].convert("L")
                img = ImageOps.autocontrast(img)
                ww, hh = img.size
                img_crop = img.crop((0, 0, ww, int(hh * 0.40)))

                text = pytesseract.image_to_string(img_crop, lang="ind+eng").upper()
                self._json({"text": text})
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _handle_p3ste_download(self):
        if _p3ste_state["running"]:
            self._json({"error": "Pengunduhan sedang berjalan"}, 400)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)

            nipp = str(data.get("nipp", "")).strip()
            password = str(data.get("password", "")).strip()
            curl_cmd = data.get("curl", "")
            awal = data.get("awal", "")
            akhir = data.get("akhir", "")
            type_val = data.get("type", "2")
            target_folder = data.get("folder", "")
            start_id = data.get("start_id")
            end_id = data.get("end_id")
            show_browser = data.get("show_browser", False)

            if not target_folder:
                self._json({"error": "Folder Penyimpanan wajib dipilih"}, 400)
                return

            if not nipp or not password:
                if not curl_cmd:
                    self._json({"error": "NIPP dan Kata Sandi akun login wajib diisi"}, 400)
                    return

            threading.Thread(
                target=_run_p3ste_download_task,
                args=(nipp, password, awal, akhir, type_val, target_folder, start_id, end_id, show_browser, curl_cmd),
                daemon=True
            ).start()

            self._json({"ok": True})
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _json(self, obj, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())
        if status >= 400:
            _log(f"API ERROR {status}: {obj.get('error', 'unknown')}")

    def log_message(self, fmt, *args):
        _log(f"HTTP: {fmt % args if args else fmt}")


def start_server():
    _log("Server thread starting (ThreadingHTTPServer)...")
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    http.server.ThreadingHTTPServer.request_queue_size = 64
    try:
        with http.server.ThreadingHTTPServer(("", PORT), ApiHandler) as httpd:
            _log(f"Server listening on port {PORT}")
            httpd.serve_forever()
    except OSError as e:
        _log(f"Server notice: Port {PORT} sudah aktif atau sedang digunakan ({e}). Menggunakan server yang ada.")


_storage_lock_fd = None


def _get_safe_webview_storage():
    """Mendapatkan direktori penyimpanan WebView2 yang aman dan bebas benturan multi-instance."""
    global _storage_lock_fd
    base_storage = os.path.join(APP_DATA_DIR, "webview_storage")
    os.makedirs(base_storage, exist_ok=True)
    
    # Pembersihan direktori storage lama dari proses yang sudah mati
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        for item in os.listdir(APP_DATA_DIR):
            if item.startswith("webview_storage_") and item != "webview_storage":
                pid_str = item.replace("webview_storage_", "")
                if pid_str.isdigit():
                    handle = kernel32.OpenProcess(0x1000, False, int(pid_str))
                    if handle:
                        kernel32.CloseHandle(handle)
                    else:
                        shutil.rmtree(os.path.join(APP_DATA_DIR, item), ignore_errors=True)
    except Exception:
        pass

    # Cek apakah base_storage dapat dikunci oleh proses ini
    try:
        import msvcrt
        lock_marker = os.path.join(base_storage, ".instance_lock")
        fd = os.open(lock_marker, os.O_CREAT | os.O_RDWR)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        _storage_lock_fd = fd
        _log(f"Using primary webview_storage: {base_storage}")
        return base_storage
    except (IOError, OSError, PermissionError) as e:
        # Jika instance lain sedang berjalan, gunakan storage terisolasi per-PID agar tidak crash 0x800700AA
        fallback_storage = os.path.join(APP_DATA_DIR, f"webview_storage_{os.getpid()}")
        os.makedirs(fallback_storage, exist_ok=True)
        _log(f"Primary webview_storage in use ({e}). Using isolated fallback: {fallback_storage}")
        return fallback_storage


def main():
    _log("=== Sintelis Utility START ===")
    _log(f"Python: {sys.version}")
    _log(f"Tesseract: {TESSERACT_CMD} exists={os.path.exists(TESSERACT_CMD)}")
    _log(f"Poppler: {POPPLER_DIR} exists={os.path.exists(POPPLER_DIR)}")
    
    if not os.path.isdir(DIST_DIR):
        msg = f"Build not found at {DIST_DIR}"
        _log(f"FATAL: {msg}")
        print(f"ERROR: {msg}")
        print("Run 'npm run build' in web-app/ first.")
        sys.exit(1)

    if "--server-only" in sys.argv or os.environ.get("SERVER_ONLY") == "1":
        _log("Running in SERVER-ONLY mode (serving at http://localhost:18725)...")
        print(f"[OK] Server running in background at http://localhost:{PORT}")
        start_server()
        return

    threading.Thread(target=start_server, daemon=True).start()
    _log(f"Server started at http://localhost:{PORT}")
    print(f"[OK] Server running at http://localhost:{PORT}")
    print("[OK] Opening desktop window...")

    webview.create_window(
        "Sintelis Utility 2.0 (v1.5.1)",
        f"http://localhost:{PORT}",
        width=1400,
        height=900,
        resizable=True,
        min_size=(1000, 600),
    )
    _log("Window created, binding events...")
    webview.windows[0].events.minimized += on_minimized
    webview.windows[0].events.restored += on_restored
    _log("Events bound. Starting webview...")
    webview_storage = _get_safe_webview_storage()
    try:
        webview.start(private_mode=False, storage_path=webview_storage)
    except Exception as e:
        _log(f"FATAL CRASH: {e}")
        import traceback
        _log(traceback.format_exc())
        print(f"CRASH: {e}")
    finally:
        global _storage_lock_fd
        if _storage_lock_fd is not None:
            try:
                import msvcrt
                msvcrt.locking(_storage_lock_fd, msvcrt.LK_UNLCK, 1)
                os.close(_storage_lock_fd)
            except Exception:
                pass
            _storage_lock_fd = None
    _log("=== Sintelis Utility END ===")
    print("[OK] Window closed.")


if __name__ == "__main__":
    main()
