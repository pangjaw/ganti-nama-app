# 🧠 Alur Kerja Agent

Note ini mendokumentasikan bagaimana **seluruh script** dalam proyek ini saling terhubung dan bekerja sebagai satu ekosistem otomatisasi yang utuh. Setiap script memiliki peran spesifik dan dapat dipanggil secara independen maupun berurutan.

#agent #arsitektur

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

---

## 🏗️ Tiga Lapisan Ekosistem

```mermaid
graph TB
    classDef ui fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1
    classDef engine fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#bf360c
    classDef data fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20

    subgraph L1["🖥️ LAYER 1: INTERFACE"]
        GUI["desktop_app.py<br/>(Tkinter Desktop GUI)"]:::ui
        WEB["templates/index.html<br/>(Web Upload UI)"]:::ui
        CLI["Command Line<br/>(Terminal langsung)"]:::ui
    end

    subgraph L2["⚙️ LAYER 2: ENGINE"]
        REKAP["download_p3ste_rekap.py<br/>📥 Download Rekap PDF"]:::engine
        WO["create_p3ste_wo.py<br/>📝 Buat Work Order"]:::engine
        OCR["app.py<br/>🔍 Flask OCR Server"]:::engine
        COMPARE["compare_pdf_folders.py<br/>📊 Perbandingan Folder"]:::engine
    end

    subgraph L3["💾 LAYER 3: DATA & SESSION"]
        LOGIN[".p3ste-logins.json"]:::data
        COOKIE[".p3ste-cookies.json"]:::data
        PDF["~/Downloads/P3STE/"]:::data
    end

    GUI --> REKAP
    GUI --> OCR
    WEB --> OCR
    CLI --> REKAP
    CLI --> WO
    CLI --> COMPARE

    REKAP --> LOGIN
    REKAP --> COOKIE
    REKAP --> PDF
    WO --> LOGIN
    WO --> COOKIE
    OCR --> PDF
    COMPARE --> PDF
```

---

## 📋 Alur Kerja Per Scenario

### Scenario 1: Download & Rename PDF Ceklis

Alur paling umum dipakai sehari-hari — download rekap dari P3-STE lalu rename hasilnya.

```mermaid
sequenceDiagram
    actor User
    participant GUI as desktop_app.py
    participant REKAP as download_p3ste_rekap.py
    participant BROWSER as Playwright Chromium
    participant P3STE as p3-ste.kai.id
    participant OCR as app.py (Flask)

    User->>GUI: Jalankan desktop_app.py
    User->>GUI: Pilih login, set tanggal, tipe
    GUI->>REKAP: start_summary()
    REKAP->>BROWSER: Launch persistent context
    BROWSER->>P3STE: Buka /rekap_checklist
    P3STE-->>BROWSER: Halaman login (jika session expired)
    REKAP->>BROWSER: Auto-fill NIPP + captcha solve
    BROWSER->>P3STE: Submit login
    P3STE-->>BROWSER: Dashboard rekap
    REKAP->>BROWSER: Set filter tanggal & tipe
    BROWSER-->>REKAP: Total data & halaman
    REKAP-->>GUI: Tampilkan ringkasan
    User->>GUI: Klik "Download"
    GUI->>REKAP: start_download()
    REKAP->>BROWSER: Crawl semua halaman, kumpulkan target PDF
    REKAP->>BROWSER: Download paralel (5 concurrent)
    BROWSER-->>REKAP: PDF files saved to ~/Downloads/P3STE/
    REKAP-->>GUI: Progress selesai
    User->>GUI: Pindah ke tab "Proses PDF"
    User->>GUI: Pilih file PDF hasil download
    GUI->>OCR: POST /process (upload PDF files)
    OCR->>OCR: OCR halaman 1, deteksi kode & aset
    OCR-->>GUI: ZIP berisi PDF yang sudah di-rename
    GUI->>User: Simpan ZIP hasil rename
```

### Scenario 2: Buat Work Order Otomatis

Alur untuk mengisi form Program Realisasi di P3-STE secara massal.

```mermaid
sequenceDiagram
    actor User
    participant CLI as create_p3ste_wo.py
    participant BROWSER as Playwright Chromium
    participant P3STE as p3-ste.kai.id

    User->>CLI: python create_p3ste_wo.py
    CLI->>User: Tanya jenis (wesel/sinyal/axc)
    User->>CLI: axc
    CLI->>User: Tanya lokasi, jumlah orang, tanggal
    User->>CLI: Stasiun Bogor, 1, 01072026 0800-2300
    CLI->>User: Paste daftar Short Text (multiline)
    User->>CLI: AXLE COUNTER ZP 60 BOO<br/>AXLE COUNTER ZP 61 BOO<br/>(Enter kosong)
    CLI->>BROWSER: Launch browser (headful)
    BROWSER->>P3STE: Buka /masterdataprogramrealisasi/form-add
    CLI->>BROWSER: Isi dropdown: Perawatan → Sinyal → Bulanan → Kode
    CLI->>BROWSER: Tambah FuncLoc (2 baris)
    CLI->>BROWSER: Isi baris 1: Short Text + Start-Finish
    CLI->>BROWSER: Isi baris 2: Short Text + Start-Finish
    CLI->>User: Mode test selesai. Browser tetap terbuka untuk review.
```

### Scenario 3: Upload PDF ke Web (Rename via Browser)

Alur ketika user mengakses web UI untuk upload PDF dan download hasil rename.

```mermaid
sequenceDiagram
    actor User
    participant WEB as Browser (index.html)
    participant FLASK as app.py (Cloud Run)
    participant TESSERACT as PyTesseract OCR

    User->>WEB: Buka URL Cloud Run / Firebase
    User->>WEB: Drag & drop PDF files
    User->>WEB: Pilih jenis kegiatan & instansi
    User->>WEB: Klik "Proses PDF"
    WEB->>FLASK: POST /process (FormData)
    FLASK->>TESSERACT: Convert PDF → Image → OCR
    TESSERACT-->>FLASK: Teks hasil OCR
    FLASK->>FLASK: detect_doc() — regex matching
    FLASK->>FLASK: build_filename() — generate nama baru
    FLASK-->>WEB: JSON {files, errors, download_url}
    WEB->>User: Tampilkan hasil & tombol download ZIP
    User->>WEB: Klik download
    WEB->>FLASK: GET /download/{id}
    FLASK-->>WEB: ZIP file
```

---

## 🔗 Dependency Antar Script

| Script | Depends On | Shared Data |
|--------|-----------|-------------|
| `desktop_app.py` | `download_p3ste_rekap.py` (import modul) | `.p3ste-logins.json` |
| `create_p3ste_wo.py` | `download_p3ste_rekap.py` (reuse login, browser, base URL) | `.p3ste-logins.json`, `.p3ste-cookies.json` |
| `app.py` | `pytesseract`, `pdf2image` (independen) | File PDF upload |
| `compare_pdf_folders.py` | Tidak ada (independen) | Folder PDF lokal |
| `download_p3ste_rekap.py` | `playwright` (independen) | `.p3ste-logins.json`, `.p3ste-cookies.json` |

> [!note] Modul Inti
> `download_p3ste_rekap.py` adalah **modul inti** yang di-reuse oleh `desktop_app.py` dan `create_p3ste_wo.py`. Fungsi login, cookie management, dan browser context didefinisikan di sini dan di-import oleh modul lain.

---

## 🔄 Koneksi Antar Note

- [[21_Struktur_Proyek]] — Detail peran setiap file
- [[22_Logika_OCR]] — Alur OCR di `app.py`
- [[23_Otomasi_Browser_Playwright]] — Detail Playwright session
- [[12_Otomasi_Work_Order]] — Panduan input WO
- [[31_Mapping_Checklist]] — Mapping dropdown WO
- [[32_Arsitektur_Deploy]] — Pipeline deployment
- [[00_Dashboard|Kembali ke Dashboard]]
