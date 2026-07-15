# 🛠️ Daftar Rencana Perbaikan

#task #backlog

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

Halaman ini digunakan untuk memantau rencana perbaikan, prioritas fitur, dan status implementasi kode pada proyek.

---

## ✅ Tugas yang Sudah Selesai (Completed Tasks)

- `[x]` **Sederhanakan area login di dashboard utama.**
  - *Target*: Tombol depan di dashboard GUI kini disederhanakan hanya menyisakan tombol `Data Login` dan `Refresh`.
  - *Target*: Aksi tambah (create), edit, hapus, dan pilih login dipindahkan ke dalam dialog pop-up `Data Login` agar tidak meramaikan tampilan utama.
- `[x]` **Penyatuan manajemen data login dalam satu wadah.**
  - *Target*: Memungkinkan user melihat akun login aktif.
  - *Target*: Mengintegrasikan proses pilih, buat baru, edit password/NIPP, dan hapus profil data login langsung dari UI.
- `[x]` **Reuse hasil pemindaian halaman dan data rekap.**
  - *Target*: Jika user sudah mengeklik `Tampilkan total halaman dan data`, lalu kemudian mengeklik `Download`, proses download tidak mengulang dari nol lagi.
  - *Target*: Memakai ulang session browser yang aktif serta halaman rekap yang sudah dimuat sebelumnya.
- `[x]` **Meminimalkan lingkup perubahan kode (Keep Changes Small).**
  - *Fokus berkas*: `desktop_app.py` dan `download_p3ste_rekap.py`.

---

## 📝 Agenda Pengembangan Mendatang (Backlog)

Berikut adalah daftar peningkatan fitur berikutnya untuk modul Otomasi Work Order (`create_p3ste_wo.py`):

- `[ ]` **Implementasi Mode Live (Submit Otomatis)**
  - *Target*: Menambahkan opsi/parameter `--live` agar script otomatis mengeklik tombol `Simpan` atau `Kirim SAP` setelah pengisian selesai.
- `[ ]` **Pemrosesan Multi-Batch (Lebih dari 5 Item)**
  - *Target*: Memproses seluruh item input secara berurutan dalam beberapa batch (per 5 item), bukan hanya membatasi pada batch pertama.
- `[ ]` **Validasi Input Awal Sebelum Launch Browser**
  - *Target*: Memvalidasi format input user (tanggal, jam, kecocokan keyword asset) sebelum browser Playwright dibuka untuk menghemat waktu dan meminimalisir error di tengah jalan.
- `[ ]` **Logging Hasil Pengisian Per Batch**
  - *Target*: Menyimpan file log lokal berupa laporan isian yang berhasil dan yang gagal dicocokkan untuk ditinjau ulang oleh user.

---

## 🔄 Koneksi Antar Note

- [[42_Riwayat_Pembaruan]] — Riwayat update yang sudah dilakukan
- [[12_Otomasi_Work_Order]] — Panduan penggunaan script WO
- [[51_Alur_Kerja_Agent]] — Alur kerja ekosistem keseluruhan
- [[00_Dashboard|Kembali ke Dashboard]]
