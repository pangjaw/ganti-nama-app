# Optimasi Ukuran EXE (193 MB → target <100 MB)

## Problem
`app.py` adalah dual-purpose file: Flask web server + core OCR logic. Saat `portable_ui.py` import fungsi dari `app.py`, PyInstaller trace seluruh module termasuk Flask + Jinja2 + Werkzeug ke bundle.

```
app.py (856 lines)
├── Flask imports (Flask, request, jsonify, render_template, send_file)
├── Flask app = Flask(__name__)
├── Fungsi core (process_pdf_ocr, detect_doc, build_filename, dll)
├── Flask route handlers (@app.route)
└── if __name__ == '__main__': app.run()
```

**Hasil**: EXE 193 MB, mayoritas Flask + Jinja2 + Werkzeug + MarkupSafe.

## Solution
Split `app.py` jadi 2 file:
1. **`core.py`** [NEW] — fungsi murni tanpa Flask, tanpa decorators, tanpa import Flask
2. **`app.py`** [MODIFY] — import dari `core.py`, hanya Flask routes
3. **`portable_ui.py`** [MODIFY] — import dari `core.py` bukan `app.py`
4. **`build_portable.ps1`** [MODIFY] — update `--add-data` ke `core.py`

## Additional Optimizations (Bonus)
- **Build**: tambah `--exclude-module` untuk Flask/Jinja2/Werkzeug/MarkupSafe di portable build
- **OCR DPI**: turunin dari 200 → 150 (40% faster OCR, negligible quality drop for single-page crop)
- **`del` cleanup**: tambah explicit GC collect setelah batch (free memory tiap N file)

## Verification
- `process_pdf_entries` harus return sama persis
- Build dengan PyInstaller → cek EXE size
- Test jalan OCR dengan file real → hasil rename sama
