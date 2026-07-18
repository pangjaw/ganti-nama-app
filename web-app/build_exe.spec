# -*- mode: python ; coding: utf-8 -*-
import sys, os
from pathlib import Path

sys.setrecursionlimit(5000)

_cwd = os.getcwd()
dist_dir = Path(_cwd) / 'dist'
if not dist_dir.is_dir():
    raise SystemExit(f'ERROR: Build not found at {dist_dir}. Run npm run build first.')

block_cipher = None

a = Analysis(
    ['run_desktop_webview.py'],
    pathex=[],
    binaries=[],
    datas=[(str(dist_dir), 'dist')],
    hiddenimports=[
        'webview',
        'webview.platforms.edgechromium',
        'http.server', 'socketserver',
        'json', 'base64', 'urllib.parse', 'threading',
        'pytesseract', 'pdf2image', 'PIL', 'PIL.ImageOps', 'PIL.Image',
        'tempfile', 'io', 're',
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pdb', 'test'],
    cipher=block_cipher, noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    name='SintelisUtility', debug=False, strip=False, upx=True,
    upx_exclude=[], runtime_tmpdir=None, console=True,
    disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)

coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[], name='SintelisUtility',
)
