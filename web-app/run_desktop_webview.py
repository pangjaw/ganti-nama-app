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
import re
import socketserver
import sys
import tempfile
import threading
import urllib.parse

import webview
from pdf2image import convert_from_path
from PIL import ImageOps, Image
import pytesseract

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
PORT = 18725
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_DIR = os.path.join(BASE_DIR, "..", "Aplikasi", "poppler")

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

_selected_folder = None
_was_minimized = False


def on_minimized():
    """Track bahwa window pernah di-minimize (untuk trigger recovery di restored)."""
    global _was_minimized
    _was_minimized = True
    _log("🟡 EVENT: minimized")


def on_restored():
    """Force WebView2 recreate rendering surface setelah restore dari minimize.
    
    Strategi: navigasi ke about:blank → delay → navigasi balik ke app URL.
    Ini memaksa WebView2 membuat ulang rendering pipeline sepenuhnya,
    tidak seperti location.reload() yang hanya reload JS di halaman sama.
    """
    global _was_minimized
    _log(f"🟢 EVENT: restored (was_minimized={_was_minimized})")
    if not _was_minimized:
        _log("INFO: skip recovery — tidak dari minimize")
        return
    _was_minimized = False
    try:
        if webview.windows:
            _log("RECOVERY: phase 1 — load about:blank")
            time.sleep(0.3)
            webview.windows[0].load_url("about:blank")
            time.sleep(0.5)
            _log(f"RECOVERY: phase 2 — load app URL http://localhost:{PORT}")
            webview.windows[0].load_url(f"http://localhost:{PORT}")
            _log("RECOVERY: done")
    except Exception as e:
        _log(f"RECOVERY: GAGAL — {e}")


class ApiHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler: serve static files + /api/* endpoints"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIST_DIR, **kwargs)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/select-folder":
            self._handle_select_folder()
        elif parsed.path == "/api/save-file":
            self._handle_save_file()
        elif parsed.path == "/api/ocr":
            self._handle_ocr()
        else:
            self.send_error(404)

    def _handle_select_folder(self):
        global _selected_folder
        try:
            result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
            if result and len(result) > 0:
                _selected_folder = result[0]
                self._json({"path": _selected_folder, "name": os.path.basename(_selected_folder)})
            else:
                self._json({"path": None, "name": None})
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _handle_save_file(self):
        global _selected_folder
        if not _selected_folder:
            self._json({"error": "no folder selected"}, 400)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            filename = data.get("filename", "")
            b64data = data.get("data", "")
            raw = base64.b64decode(b64data)
            path = os.path.join(_selected_folder, filename)
            with open(path, "wb") as f:
                f.write(raw)
            self._json({"ok": True})
        except Exception as e:
            self._json({"error": str(e)}, 500)

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
                # Konfigurasi Tesseract
                if os.path.exists(TESSERACT_CMD):
                    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

                # Render halaman pertama
                images = convert_from_path(
                    tmp_path, dpi=200, first_page=1, last_page=1,
                    poppler_path=POPPLER_DIR if os.path.exists(POPPLER_DIR) else None
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
    _log("Server thread starting...")
    with socketserver.TCPServer(("", PORT), ApiHandler) as httpd:
        _log(f"Server listening on port {PORT}")
        httpd.serve_forever()


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

    threading.Thread(target=start_server, daemon=True).start()
    _log(f"Server started at http://localhost:{PORT}")
    print(f"[OK] Server running at http://localhost:{PORT}")
    print("[OK] Opening desktop window...")

    webview.create_window(
        "Sintelis Utility",
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
    try:
        webview.start()
    except Exception as e:
        _log(f"FATAL CRASH: {e}")
        import traceback
        _log(traceback.format_exc())
        print(f"CRASH: {e}")
    _log("=== Sintelis Utility END ===")
    print("[OK] Window closed.")


if __name__ == "__main__":
    main()
