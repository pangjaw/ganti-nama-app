# P3-STE Rekap Checklist Automation Handoff

Tujuan: lanjutkan pekerjaan otomatisasi download PDF dari `https://p3-ste.kai.id/rekap_checklist` di laptop lain.

## Status

- Script dibuat: `download_p3ste_rekap.py`
- Dependency ditambah: `playwright` di `requirements.txt`
- Output default: `C:\Users\<user>\Downloads\P3STE`
- Browser profile tersimpan lokal di folder `.p3ste-browser`
- Login tetap aman: user ketik NIPP/password di terminal, lalu user jawab captcha.
- Captcha P3-STE terdeteksi sebagai teks HTML math captcha, contoh `3 + 4`, bukan gambar/canvas.

## Cara Pakai

Install dependency:

```powershell
python -m pip install -r requirements.txt
```

Jalankan mode background:

```powershell
python download_p3ste_rekap.py
```

Jalankan mode browser terlihat:

```powershell
python download_p3ste_rekap.py --show
```

Run langsung dengan parameter:

```powershell
python download_p3ste_rekap.py --awal 01/06/2026 --akhir 27/06/2026 --tipe Perawatan --show
```

Kalau Chromium/Edge gagal:

```powershell
python -m playwright install chromium
```

## Flow Script

1. Tanya tanggal awal.
2. Tanya tanggal akhir.
3. Tanya tipe checklist: `Perawatan` atau `Pemeriksaan`.
4. Buka P3-STE.
5. Kalau login muncul:
   - minta NIPP
   - minta password
   - baca captcha teks dari halaman
   - tanya jawaban captcha ke user
   - submit login
6. Buka URL rekap dengan filter tetap:
   - `asset=0`
   - `category=0`
   - `daop=1`
   - `resort=170`
   - `nipp=0`
   - `noasset=0`
   - `hasil=baik`
   - `status=done`
7. Ubah jumlah data tabel ke `100`.
8. Klik semua tombol `Cetak` di halaman.
9. Lanjut halaman berikutnya sampai habis.
10. Simpan semua PDF ke `Downloads\P3STE`.

## Catatan Teknis

- Script tidak memakai tombol `Unduh Semua PDF`, karena tombol itu kadang error.
- Script memakai tombol `Cetak` per baris.
- Setelah mengubah tampilan ke `100`, script menunggu loading tabel.
- Default wait: `3000 ms`; bisa dinaikkan:

```powershell
python download_p3ste_rekap.py --wait-ms 7000
```

## Validasi Yang Sudah Dilakukan

```powershell
python -m py_compile download_p3ste_rekap.py
python download_p3ste_rekap.py --self-test
```

Hasil: OK.

## Belum Diuji End-to-End

Belum diuji sampai download asli selesai, karena butuh login P3-STE aktif dan intranet kantor.

## Lanjut Di Laptop

1. Pull repo dari GitHub.
2. Install dependency.
3. Jalankan `python download_p3ste_rekap.py --show` untuk tes pertama.
4. Login manual via prompt terminal.
5. Pastikan PDF masuk ke `Downloads\P3STE`.
