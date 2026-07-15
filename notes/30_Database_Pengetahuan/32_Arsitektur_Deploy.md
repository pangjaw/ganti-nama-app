# 🚀 Pipeline Deployment

Note ini mendokumentasikan alur deployment proyek **Ganti Nama App** ke Google Cloud Run dan Firebase Hosting.

#deploy #arsitektur

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

---

## 🐳 Dockerfile

File `Dockerfile` di root proyek digunakan untuk meng-containerize Flask OCR server (`app.py`).

**Komponen penting:**
- Base image `python:3.10-slim` untuk ukuran container kecil
- Install `tesseract-ocr` + bahasa Indonesia (`tesseract-ocr-ind`)
- Install `poppler-utils` untuk `pdf2image` (konversi PDF → gambar)
- Menggunakan `gunicorn` sebagai production WSGI server

---

## ☁️ Google Cloud Run

Flask server di-deploy ke **Google Cloud Run** (region `asia-southeast2`).

### Konfigurasi Deploy
- **Service name**: `sintelis-utility`
- **Region**: `asia-southeast2` (Jakarta)
- **Authentication**: `--allow-unauthenticated` (publik)
- **Image registry**: `asia-southeast2-docker.pkg.dev/ganti-nama-file/sintelis-repo/sintelis-utility:latest`

---

## 🔥 Firebase Hosting

File statis (`templates/index.html`) di-hosting via **Firebase Hosting** pada project `ganti-nama-file`.

---

## ⚡ Shortcut 1-Klik (`1-klik.bat`)

Seluruh pipeline bisa dijalankan sekali klik melalui file batch:

**Urutan eksekusi:**
1. `docker build` → Rakit image dari Dockerfile
2. `docker push` → Upload ke Artifact Registry
3. `gcloud run deploy` → Deploy container ke Cloud Run
4. `firebase deploy` → Upload static files ke Firebase

> [!warning] Prasyarat
> Pastikan `gcloud` CLI dan `firebase` CLI sudah terinstall dan ter-autentikasi.

---

## 🔄 Keterkaitan Note

- [[21_Struktur_Proyek]] — Struktur file Dockerfile & firebase.json
- [[11_Menjalankan_Aplikasi]] — Cara menjalankan lokal sebelum deploy
- [[23_Otomasi_Browser_Playwright]] — Cloud Run hanya serve Flask OCR, bukan Playwright
- [[00_Dashboard|Kembali ke Dashboard]]
