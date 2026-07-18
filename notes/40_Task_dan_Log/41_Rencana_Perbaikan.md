# 🛠️ Daftar Rencana Perbaikan

#task #backlog

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

Halaman ini digunakan untuk memantau rencana perbaikan dan backlog pengembangan **Sintelis Utility**.

---

## ✅ Tugas yang Sudah Selesai

- `[x]` **Split-view hasil/error + log** — Panel kanan sekarang tab hasil/error di samping log.
- `[x]` **Export Excel (XLSX)** — 3 sheet: Input Files, Hasil, Error.
- `[x]` **Rapihkan vault** — Hapus 60+ file usang, ~130 MB tesseract, desktop app lama.
- `[x]` **Dashboard Obsidian diperbarui** — Mencerminkan arsitektur web-app + Python WebView.
- `[x]` **Client-side PDF processing** — PDF.js + Tesseract.js di browser, tanpa upload ke server.

---

## 📝 Agenda Pengembangan Mendatang (Backlog)

- `[ ]` **Perbaikan akurasi OCR untuk Serat Optik OTB**
  - *Target*: Perbaiki regex negative lookbehind di detector.js untuk exclude `ODF/OTB` core count.
- `[ ]` **Progress bar per file**
  - *Target*: Tampilkan progress granular per file, bukan hanya counter.
- `[ ]` **Dark/light mode toggle**
  - *Target*: Opsi switch tema untuk aksesibilitas.
- `[ ]` **Batch rename preview**
  - *Target*: Preview nama file hasil rename sebelum simpan, dengan opsi edit manual.

---

## 🔄 Koneksi Antar Note

- [[42_Riwayat_Pembaruan]] — Riwayat update yang sudah dilakukan
- [[44_Temuan_dan_Rencana_Perbaikan_v3]] — Temuan & rencana terkini
- [[00_Dashboard|Kembali ke Dashboard]]
