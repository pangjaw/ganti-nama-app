"""
updater_engine.py — Cloudflare Auto-Updater Engine for Sintelis Utility
Checks version.json via Cloudflare domain, downloads new exe with progress tracking,
and performs atomic swap on Windows.
"""
import os
import sys
import time
import json
import urllib.request
import threading
import subprocess
import tempfile

APP_VERSION = "1.5.1"
DEFAULT_UPDATE_URL = "https://update.sintelboo.my.id/version.json"

_update_state = {
    "status": "idle",       # idle, checking, available, downloading, ready, error
    "server_version": None,
    "download_url": None,
    "changelog": [],
    "file_size": 0,
    "downloaded_bytes": 0,
    "percent": 0,
    "error": None,
    "target_temp_exe": None
}

_update_lock = threading.Lock()

def parse_semver(ver_str):
    try:
        clean = ver_str.lower().replace("v", "").strip()
        parts = [int(p) for p in clean.split(".")]
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])
    except Exception:
        return (0, 0, 0)

def check_update(custom_url=None):
    url = custom_url or DEFAULT_UPDATE_URL
    with _update_lock:
        _update_state["status"] = "checking"
        _update_state["error"] = None

    last_err = None
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "SintelisUtility-Client/1.5.1"}
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            server_ver = data.get("version", "0.0.0")
            is_newer = parse_semver(server_ver) > parse_semver(APP_VERSION)

            with _update_lock:
                _update_state["server_version"] = server_ver
                _update_state["download_url"] = data.get("downloadUrl")
                _update_state["changelog"] = data.get("changelog", [])
                _update_state["file_size"] = data.get("fileSize", 0)
                if is_newer:
                    _update_state["status"] = "available"
                else:
                    _update_state["status"] = "idle"

            return {
                "updateAvailable": is_newer,
                "currentVersion": APP_VERSION,
                "serverVersion": server_ver,
                "changelog": data.get("changelog", []),
                "downloadUrl": data.get("downloadUrl"),
                "fileSize": data.get("fileSize", 0),
                "releaseDate": data.get("releaseDate", "")
            }
        except Exception as e:
            last_err = e
            time.sleep(0.5)

    with _update_lock:
        _update_state["status"] = "error"
        _update_state["error"] = str(last_err)
    return {
        "updateAvailable": False,
        "currentVersion": APP_VERSION,
        "error": str(last_err),
        "offline": True
    }

def _download_task(download_url):
    temp_dir = tempfile.gettempdir()
    temp_exe = os.path.join(temp_dir, "SintelisUtility_update.exe")

    with _update_lock:
        _update_state["status"] = "downloading"
        _update_state["downloaded_bytes"] = 0
        _update_state["percent"] = 0
        _update_state["target_temp_exe"] = temp_exe

    try:
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "SintelisUtility-Client/1.5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp, open(temp_exe, "wb") as out_f:
            total_len = int(resp.headers.get("Content-Length", 0)) or _update_state["file_size"] or 1
            downloaded = 0
            chunk_size = 1024 * 128

            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out_f.write(chunk)
                downloaded += len(chunk)
                percent = min(100.0, round(downloaded / total_len * 100, 1))
                with _update_lock:
                    _update_state["downloaded_bytes"] = downloaded
                    _update_state["percent"] = percent

        with _update_lock:
            _update_state["status"] = "ready"
            _update_state["percent"] = 100.0
    except Exception as e:
        with _update_lock:
            _update_state["status"] = "error"
            _update_state["error"] = str(e)

def start_download(download_url=None):
    url = download_url or _update_state.get("download_url")
    if not url:
        return {"ok": False, "error": "Download URL tidak ditemukan"}
    t = threading.Thread(target=_download_task, args=(url,), daemon=True)
    t.start()
    return {"ok": True, "message": "Download started"}

def get_update_state():
    with _update_lock:
        return dict(_update_state)

def apply_update_and_restart():
    with _update_lock:
        temp_exe = _update_state.get("target_temp_exe")
        if not temp_exe or not os.path.isfile(temp_exe):
            return {"ok": False, "error": "File pembaruan belum siap diunduh"}

    if getattr(sys, "frozen", False):
        target_exe = os.path.abspath(sys.executable)
    else:
        target_exe = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "SintelisUtility.exe"))

    current_pid = os.getpid()

    # Script restart batch yang handal di Windows:
    # 1. Pastikan proses lama berhenti (taskkill target PID)
    # 2. Copy timpa file exe
    # 3. Jalankan aplikasi baru via explorer.exe (memunculkan window GUI interaktif di desktop pengguna)
    # 4. Bersihkan file sementara
    bat_content = f"""@echo off
set "TARGET={target_exe}"
set "TEMP_EXE={temp_exe}"

:: Tunggu sejenak lalu pastikan proses lama benar-benar mati
timeout /t 1 /nobreak > nul
taskkill /F /PID {current_pid} > nul 2>&1
timeout /t 1 /nobreak > nul

:retry_copy
copy /y "%TEMP_EXE%" "%TARGET%" > nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak > nul
    goto retry_copy
)

:: Jalankan aplikasi baru menggunakan explorer.exe (memastikan window GUI muncul di desktop pengguna)
start "" explorer.exe "%TARGET%"

:: Bersihkan file sementara
del "%TEMP_EXE%" > nul 2>&1
(goto) 2>nul & del "%~f0"
exit
"""
    bat_file = os.path.join(tempfile.gettempdir(), "sintelis_updater.bat")
    with open(bat_file, "w", encoding="utf-8") as f:
        f.write(bat_content)

    DETACHED_PROCESS = 0x00000008
    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        ["cmd.exe", "/c", bat_file],
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True
    )

    threading.Thread(target=lambda: (time.sleep(1.0), os._exit(0)), daemon=True).start()
    return {"ok": True, "message": "Restarting application to apply update..."}
