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

APP_VERSION = "1.6.0"
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
        exe_path = os.path.abspath(sys.executable)
        exe_dir = os.path.dirname(exe_path)
        target_exe = os.path.join(exe_dir, "SintelisUtility.exe")
        old_exe_to_clean = exe_path if exe_path.lower() != target_exe.lower() else ""
    else:
        target_exe = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "SintelisUtility.exe"))
        old_exe_to_clean = ""

    current_pid = os.getpid()

    # Script restart PowerShell yang tangguh & anti-gagal di Windows:
    # 1. Pastikan proses lama berhenti (Stop-Process target PID)
    # 2. Matikan semua proses terkait target maupun old_exe (pohon proses PyInstaller & WebView)
    # 3. Loop copy dengan jeda nyata hingga sistem operasi melepas file lock
    # 4. Bersihkan file lama berakhiran versi jika ada
    # 5. Jalankan aplikasi baru via Start-Process
    ps_content = f"""
$target = "{target_exe}"
$temp = "{temp_exe}"
$old_to_clean = "{old_exe_to_clean}"
$pid_to_kill = {current_pid}

# 1. Matikan proses utama saat ini
try {{ Stop-Process -Id $pid_to_kill -Force -ErrorAction SilentlyContinue }} catch {{}}

# 2. Matikan SEMUA proses Windows yang menjalankan target maupun berkas lama
$targetName = [System.IO.Path]::GetFileName($target)
if ($targetName) {{
    try {{ taskkill.exe /F /IM "$targetName" /T 2>$null }} catch {{}}
}}
if ($old_to_clean) {{
    $oldName = [System.IO.Path]::GetFileName($old_to_clean)
    if ($oldName) {{
        try {{ taskkill.exe /F /IM "$oldName" /T 2>$null }} catch {{}}
    }}
}}
try {{
    Get-Process | Where-Object {{
        try {{
            $p = $_.Path.ToLower()
            $p -eq $target.ToLower() -or ($old_to_clean -and $p -eq $old_to_clean.ToLower())
        }} catch {{ $false }}
    }} | Stop-Process -Force -ErrorAction SilentlyContinue
}} catch {{}}

Start-Sleep -Seconds 2

# 3. Loop Copy-Item dengan jeda hingga Windows melepas kunci berkas (file lock)
$copied = $false
for ($i = 0; $i -lt 30; $i++) {{
    try {{
        Copy-Item -LiteralPath $temp -Destination $target -Force -ErrorAction Stop
        $copied = $true
        break
    }} catch {{
        Start-Sleep -Seconds 1
    }}
}}

if ($copied) {{
    try {{ Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }} catch {{}}
    if ($old_to_clean -and (Test-Path -LiteralPath $old_to_clean)) {{
        try {{ Remove-Item -LiteralPath $old_to_clean -Force -ErrorAction SilentlyContinue }} catch {{}}
    }}
    Start-Process -FilePath $target
}}
"""
    ps_file = os.path.join(tempfile.gettempdir(), "sintelis_updater.ps1")
    with open(ps_file, "w", encoding="utf-8") as f:
        f.write(ps_content)

    DETACHED_PROCESS = 0x00000008
    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        ["powershell.exe", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", ps_file],
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True
    )

    threading.Thread(target=lambda: (time.sleep(1.0), os._exit(0)), daemon=True).start()
    return {"ok": True, "message": "Restarting application to apply update..."}
