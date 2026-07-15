# 🗂️ Dashboard Project: Ganti Nama App & Otomasi P3-STE

Selamat datang di Obsidian Vault untuk **Ganti Nama App & Otomasi P3-STE**. Vault ini dirancang untuk mendokumentasikan alur kerja, arsitektur kode, aturan bisnis, serta melacak perkembangan pengerjaan proyek.

#dashboard #index #MOC

---

## 🗺️ Peta Navigasi (Map of Content)

### 🚀 1. Panduan Penggunaan
*   [[11_Menjalankan_Aplikasi|🏃 Panduan Menjalankan Aplikasi]] — Langkah-langkah menjalankan script utama, Flask OCR, serta aplikasi desktop (GUI).
*   [[12_Otomasi_Work_Order|🤖 Alur Otomasi Work Order]] — Panduan detail penggunaan `create_p3ste_wo.py`, format input, pencocokan text (matching logic), dan mode pengujian.

### 📐 2. Arsitektur Kode & Sistem
*   [[21_Struktur_Proyek|📂 Struktur Folder & Komponen]] — Penjelasan peran setiap file utama (`app.py`, `desktop_app.py`, dll.) dalam proyek.
*   [[22_Logika_OCR|🔍 Cara Kerja OCR & Ekstraksi PDF]] — Logika pemotongan area (cropping), pemanfaatan Tesseract OCR, dan pencocokan pola regex.
*   [[23_Otomasi_Browser_Playwright|🌐 Otomasi Browser & Login Session]] — Detail implementasi Playwright, manajemen profil `.p3ste-browser`, dan penyimpanan data login.

### 📚 3. Basis Pengetahuan (Knowledge Base)
*   [[31_Mapping_Checklist|📋 Pemetaan Kode & Kategori Checklist]] — Referensi mapping tipe checklist, kategori, periode, dan kode checklist (Wesel, Sinyal, AXC).
*   [[32_Arsitektur_Deploy|🚀 Pipeline Deployment]] — Dokumentasi Docker, Cloud Run, Firebase Hosting, dan alur deploy 1-klik.

### 📋 4. Rencana Kerja & Riwayat
*   [[41_Rencana_Perbaikan|🛠️ Daftar Rencana Perbaikan]] — Todo list perbaikan aplikasi, prioritas fitur, dan area perbaikan saat ini.
*   [[42_Riwayat_Pembaruan|📜 Riwayat Pembaruan Script WO]] — Catatan tahapan perkembangan implementasi script pembuatan Work Order.

### 🤖 5. Alur Kerja Agent & Otomasi
*   [[51_Alur_Kerja_Agent|🧠 Alur Kerja Agent]] — Penjelasan bagaimana script-agent mengorkestrasi seluruh pipeline otomatisasi P3-STE.

---

## 🔄 Alur Kerja Ekosistem (End-to-End)

```mermaid
graph TD
    classDef ui fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef engine fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#bf360c;
    classDef data fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef infra fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#4a148c;

    subgraph "INTERFACE LAYER"
        A["🖥️ desktop_app.py<br/>(Tkinter GUI)"]:::ui
        B["🌐 templates/index.html<br/>(Web Upload UI)"]:::ui
    end

    subgraph "ENGINE LAYER"
        C["📥 download_p3ste_rekap.py<br/>(Download Rekap PDF)"]:::engine
        D["📝 create_p3ste_wo.py<br/>(Buat Work Order)"]:::engine
        E["🔍 app.py<br/>(Flask OCR Server)"]:::engine
        F["📊 compare_pdf_folders.py<br/>(Perbandingan Folder)"]:::engine
    end

    subgraph "DATA LAYER"
        G[".p3ste-logins.json<br/>(Kredensial)"]:::data
        H[".p3ste-cookies.json<br/>(Session Cookie)"]:::data
        I["~/Downloads/P3STE/<br/>(PDF Hasil Download)"]:::data
    end

    subgraph "INFRA LAYER"
        J["🐳 Dockerfile"]:::infra
        K["☁️ Google Cloud Run"]:::infra
        L["🔥 Firebase Hosting"]:::infra
    end

    %% Interface → Engine
    A -->|"Panggil modul"| C
    A -->|"Kelola login"| G
    B -->|"Upload PDF → POST /process"| E

    %% Engine → Data
    C -->|"Login & download"| G
    C -->|"Simpan cookie"| H
    C -->|"Download PDF"| I
    D -->|"Gunakan login"| G
    D -->|"Gunakan cookie"| H
    E -->|"OCR & rename"| I
    F -->|"Bandingkan folder"| I

    %% Engine → Infra
    E -.->|"Containerized"| J
    J -.->|"Deploy"| K
    B -.->|"Static files"| L

    %% Cross-link
    D -.->|"Mapping dropdown"| M["[[31_Mapping_Checklist]]"]
    C -.->|"Login session"| N["[[23_Otomasi_Browser_Playwright]]"]
    E -.->|"OCR logic"| O["[[22_Logika_OCR]]"]
```

---

## 📊 Keterkaitan Antar Note

```mermaid
graph LR
    classDef guide fill:#bbdefb,stroke:#1976d2;
    classDef arch fill:#c8e6c9,stroke:#388e3c;
    classDef kb fill:#ffe0b2,stroke:#f57c00;
    classDef task fill:#f8bbd0,stroke:#c2185b;
    classDef agent fill:#d1c4e9,stroke:#512da8;

    D[["00_Dashboard"]]:::guide

    D --> G1["11_Menjalankan_Aplikasi"]:::guide
    D --> G2["12_Otomasi_Work_Order"]:::guide
    D --> A1["21_Struktur_Proyek"]:::arch
    D --> A2["22_Logika_OCR"]:::arch
    D --> A3["23_Otomasi_Browser_Playwright"]:::arch
    D --> K1["31_Mapping_Checklist"]:::kb
    D --> K2["32_Arsitektur_Deploy"]:::kb
    D --> T1["41_Rencana_Perbaikan"]:::task
    D --> T2["42_Riwayat_Pembaruan"]:::task
    D --> AG["51_Alur_Kerja_Agent"]:::agent

    G1 --> A1
    G1 --> A2
    G1 --> G2
    G2 --> K1
    G2 --> A3
    A1 --> A2
    A1 --> A3
    A2 --> E["app.py"]
    A3 --> C["download_p3ste_rekap.py"]
    K1 --> D2["create_p3ste_wo.py"]
    T2 --> D2
    AG --> C
    AG --> D2
    AG --> E
```

---

## 🏷️ Tag Index

| Tag | Keterangan |
|-----|------------|
| `#dashboard` | Halaman index utama |
| `#panduan` | Panduan penggunaan |
| `#arsitektur` | Dokumentasi arsitektur kode |
| `#knowledge` | Basis pengetahuan & referensi |
| `#task` | Rencana & riwayat pekerjaan |
| `#agent` | Alur kerja agent & otomasi |
| `#ocr` | Terkait OCR & ekstraksi PDF |
| `#playwright` | Terkait Playwright & browser automation |
| `#deploy` | Terkait deployment & infrastruktur |

---

💡 **Tips Obsidian:**
- Gunakan shortcut `Ctrl + Click` (Windows) pada tautan wikilink untuk langsung membuka note.
- Tekan `Ctrl + P` untuk membuka Command Palette dan cari note dengan cepat.
- Buka **Graph View** (`Ctrl + G`) untuk melihat peta keterkaitan seluruh note secara visual.
- Gunakan **Tag Pane** untuk navigasi berdasarkan kategori.
