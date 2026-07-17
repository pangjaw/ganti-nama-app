# README

## Plan perbaikan desktop app

- [x] Sederhanakan area login di dashboard.
  - target: tombol depan tinggal `Data Login` dan `Refresh`
  - create/edit/hapus/pilih dipindah ke dalam dialog `Data Login`

- [x] Satukan manajemen data login dalam satu tempat.
  - target: lihat data login aktif
  - target: pilih login
  - target: buat login
  - target: edit login
  - target: hapus login

- [x] Reuse hasil `Tampilkan total halaman dan data`.
  - target: kalau user sudah klik `Tampilkan...`, lalu klik `Download`, proses tidak mulai dari nol lagi
  - target: session browser dan halaman rekap yang sudah siap dipakai ulang

- [x] Jaga perubahan tetap kecil.
  - fokus file:
    - `desktop_app.py`
    - `download_p3ste_rekap.py`

## Catatan

- Akar bug lama: `normalize_args()` terpanggil dobel.
- Akar bug login lama: password tersimpan bisa salah, jadi perlu edit/hapus login dari UI.
