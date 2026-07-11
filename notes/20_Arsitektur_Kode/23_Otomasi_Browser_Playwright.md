# 🌐 Otomasi Browser & Login Session

Proyek ini menggunakan **Playwright (Python Async API)** untuk mengotomasi interaksi dengan portal P3-STE (`https://p3-ste.kai.id`). Note ini mendokumentasikan bagaimana session browser, bypass login, serta penanganan captcha diimplementasikan.

---

## 🔒 Manajemen Session Persistent (Bypass Login)

Untuk menghindari keharusan login dan memasukkan Captcha setiap kali otomasi dijalankan, script menggunakan fitur **Persistent Browser Context** dari Playwright.

*   **Direktori Profil**: `.p3ste-browser/` (lokal di root proyek).
*   **Cara Kerja**: 
    1. Saat script dijalankan, Playwright membuka browser Chromium menggunakan profile dari direktori `.p3ste-browser/`.
    2. Semua data session seperti cookie, localStorage, cache, dan state login akan otomatis tersimpan ke folder tersebut.
    3. Jika session di web P3-STE belum kedaluwarsa, browser akan langsung masuk ke halaman utama/dashboard tanpa menampilkan halaman login.

```python
# Modul launch persistent context
return await pw.chromium.launch_persistent_context(
    user_data_dir=PROFILE_DIR, # .p3ste-browser
    headless=False,            # Dibuat visual agar user dapat memantau
    viewport={"width": 1280, "height": 720}
)
```

---

## 🤖 Mekanisme Login & Pemecahan Captcha

Jika session kedaluwarsa atau belum ada cookie tersimpan, browser akan diarahkan ke halaman login. Proses login diotomasi melalui beberapa tahap:

### 1. Membaca Kredensial
Kredensial dibaca berdasarkan prioritas berikut:
1. Environment variables (`P3STE_NIPP` & `P3STE_PASSWORD`).
2. Akun terpilih dari berkas konfigurasi lokal `.p3ste-logins.json`.
3. Input manual di terminal jika kedua sumber di atas kosong.

### 2. Deteksi Captcha Matematika Sederhana
Web P3-STE menggunakan captcha berbasis operasi aritmatika teks (seperti `5 + 3`, `12 - 4`, dll.).
Script menggunakan fungsi Javascript Evaluator (`read_captcha_text`) untuk mengekstrak string tersebut dari DOM halaman login:

```javascript
// Mengambil text captcha matematika dari form login
for (const el of document.querySelectorAll('form#form-login span, form#form-login .text-center')) {
    const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (/^\d+\s*[+\-xX*/]\s*\d+$/.test(text)) return text;
}
```

*   **Bila terdeteksi**: Script akan menampilkan operasi matematika tersebut di terminal dan meminta user mengetikkan jawabannya:
    `Captcha 5 + 3 = [User menginput jawaban]`
*   **Bila tidak terdeteksi**: User diminta melihat browser Chromium yang terbuka dan mengetikkan jawaban captcha secara manual ke terminal.

### 3. Deteksi Feedback Kegagalan Login
Jika kombinasi NIPP, sandi, atau captcha salah, script mengevaluasi elemen alert di halaman login untuk mengambil pesan kesalahan dari web dan menampilkannya kembali ke user/GUI log.

---

## ⏳ Sinkronisasi Loading Halaman (State Polling)

Salah satu kendala terbesar otomasi web adalah ketidaksinkronan waktu rendering elemen web dengan jalannya script. Proyek ini menangani masalah tersebut dengan melakukan polling state tabel (`table_state`):

1.  **Mendeteksi Loading Spinner**: Memeriksa keberadaan CSS selector loading umum seperti `.dataTables_processing`, `.loader-box`, `.spinner-border`.
2.  **Menghitung Baris**: Memastikan jumlah baris (`tr`) di `<tbody>` lebih dari 0 dan bukan bertuliskan "tidak ada data".
3.  **Kestabilan Data**: Data harus stabil (tidak berubah dan spinner tidak muncul) selama minimal 2.5 detik (`stable_ms >= 2500`) sebelum proses download atau interaksi berikutnya dimulai.
