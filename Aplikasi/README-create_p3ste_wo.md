# README create_p3ste_wo.py

## Ringkas

`create_p3ste_wo.py` adalah script otomasi P3-STE untuk bantu isi form:

`https://p3-ste.kai.id/masterdataprogramrealisasi/form-add`

Script ini dibuat dengan prinsip:

- reuse sistem login dari `download_p3ste_rekap.py`
- browser tampil supaya proses bisa dilihat user
- fokus isi form Work Order / Program Realisasi
- aman dulu: mode akhir saat ini masih `tes`, belum klik `Simpan` atau `Kirim SAP`

## File utama

- `create_p3ste_wo.py`
- `download_p3ste_rekap.py`
- `.p3ste-logins.json`
- `.p3ste-browser`

## Fungsi script

Script akan:

1. Pakai login P3-STE yang sudah tersimpan.
2. Buka halaman `Tambah Program Realisasi`.
3. Isi field atas sesuai jenis asset.
4. Klik `Tambah FuncLoc` berulang sebanyak jumlah asset pada batch.
5. Isi `Short Text`, `Start-Finish Date`, dan jika ada, isi `Operation`.
6. Berhenti sebelum `Simpan` atau `Kirim SAP`.

## Status saat ini

Mode sekarang adalah `test mode`.

Artinya:

- browser tampil dan bisa dilihat langsung
- form diisi otomatis
- script berhenti sebelum submit
- browser tetap terbuka sampai user tekan `Enter` di terminal

Kalau data lebih dari 5 item:

- script saat ini hanya isi batch pertama dulu
- maksimal 5 item pertama
- sisa item hanya diberi info, belum diproses

## Input user

Saat script dijalankan, user diminta isi:

1. `Jenis [wesel/sinyal/axc]`
2. `Lokasi dropdown`
3. `Jumlah orang`
4. `Tanggal dan jam [01072026 0800-2300]`
5. daftar `Short Text` multiline

Contoh:

```text
Jenis [wesel/sinyal/axc]: axc
Lokasi dropdown (contoh: Stasiun Bogor): Stasiun Bogor
Jumlah orang: 1
Tanggal dan jam [01072026 0800-2300]: 01072026 0800-2300
Paste daftar Short Text. Akhiri dengan baris kosong.
AXLE COUNTER ZP 60 BOO
AXLE COUNTER ZP 61 BOO
AXLE COUNTER ZP 62A BOO

```

## Konversi waktu

Input:

```text
01072026 0800-2300
```

Akan diubah menjadi:

- `Tanggal Program` -> `01/07/2026`
- `Start-Finish Date` -> `01/07/2026 08:00 - 01/07/2026 23:00`

`Tanggal Program` selalu diambil dari tanggal awal `Start-Finish Date`.

## Mapping field atas

### Wesel

- `Tipe Checklist` -> `Perawatan`
- `Kategori` -> `Sinyal`
- `Periode` -> `2 Mingguan`
- `Kode Checklist` -> `PERAWATAN WESEL ELEKTRIK 2 MINGGUAN - (WESEL BIASA)`

### Sinyal

- `Tipe Checklist` -> `Perawatan`
- `Kategori` -> `Sinyal`
- `Periode` -> `Bulanan`
- `Kode Checklist` -> `PERAWATAN PERAGA SINYAL ELEKTRIK 1 BULANAN - (-)`

### AXC

- `Tipe Checklist` -> `Perawatan`
- `Kategori` -> `Sinyal`
- `Periode` -> `Bulanan`
- `Kode Checklist` -> `PERAWATAN AXLE COUNTER SIEMENS 1 BULANAN - (SIEMENS)`

## Cara isi FuncLoc

Flow yang dipakai sekarang:

1. Isi field atas dulu.
2. Klik `Tambah FuncLoc` sebanyak jumlah asset pada batch.
3. Setelah semua row muncul, isi setiap row satu per satu.

Ini penting karena row baru memang tidak muncul otomatis 5 sekaligus. Harus klik berulang.

## Matching Short Text

Awalnya script mencoba pilih `Short Text` dengan nama full persis.

Lalu diupdate supaya lebih lentur, karena di lapangan format input user bisa beda sedikit dari dropdown web.

Sekarang script coba cocokkan dengan urutan:

1. teks penuh
2. teks yang sudah dinormalisasi
3. kode asset utama
4. kode asset + lokasi

Contoh:

- `AXLE COUNTER ZP 60 BOO` -> kunci utama: `ZP60`, `BOO`
- `PENGGERAK WESEL W21A BOO` -> kunci utama: `W21A`, `BOO`
- `SINYAL KELUAR DAN LANGSIR JL92 BOO` -> kunci utama: `JL92`, `BOO`

Script juga menunggu dropdown row siap dulu sebelum memilih opsi, karena opsi kadang muncul terlambat walau row sudah kelihatan.

## Cara jalankan

```powershell
python create_p3ste_wo.py
```

Untuk cek fungsi dasar tanpa buka browser:

```powershell
python create_p3ste_wo.py --self-test
```

## Validasi yang sudah ada

Self-test saat ini mengecek:

- parsing waktu
- ekstrak `Tanggal Program`
- pemecahan batch 5 item
- normalisasi text
- ekstrak keyword untuk AXC
- ekstrak keyword untuk sinyal

## Riwayat pembuatan dan update

### Tahap 1 - Pembuatan awal

Versi awal dibuat sebagai script terpisah bernama `create_p3ste_wo.py`.

Tujuan awal:

- pakai login yang sama dengan otomasi download PDF
- isi halaman `Tambah Program Realisasi`
- dukung 3 jenis: `wesel`, `sinyal`, `axc`
- dukung input `Short Text` dari paste multiline

### Tahap 2 - Browser ditampilkan

Awalnya browser masih bisa jalan headless.

Lalu diubah supaya browser tampil default, agar user bisa lihat prosesnya langsung saat otomasi berjalan.

### Tahap 3 - Ubah jadi mode tes

User minta hasil akhir tidak submit dulu.

Maka script diubah menjadi:

- tidak klik `Simpan`
- tidak klik `Kirim SAP`
- hanya isi form
- berhenti untuk review manual

### Tahap 4 - Tambah mapping `Kode Checklist`

Awalnya `Kode Checklist` masih dicari dengan keyword umum.

Lalu diupdate pakai label persis:

- wesel -> `PERAWATAN WESEL ELEKTRIK 2 MINGGUAN - (WESEL BIASA)`
- sinyal -> `PERAWATAN PERAGA SINYAL ELEKTRIK 1 BULANAN - (-)`
- axc -> `PERAWATAN AXLE COUNTER SIEMENS 1 BULANAN - (SIEMENS)`

### Tahap 5 - Samakan `Tanggal Program`

User minta `Tanggal Program` mengikuti tanggal dari `Start-Finish Date`.

Maka logika diubah:

- input waktu hanya satu kali
- script membentuk `Start-Finish Date`
- `Tanggal Program` diambil dari tanggal awal hasil itu

### Tahap 6 - Perbaiki flow `Tambah FuncLoc`

Awalnya row diisi sambil tambah satu per satu.

Lalu disesuaikan dengan perilaku web:

- `Tambah FuncLoc` diklik berulang dulu sesuai jumlah asset
- setelah semua row muncul, barulah row-row itu diisi

### Tahap 7 - Perbaiki matching `Short Text`

Masalah yang muncul:

- script gagal pilih AXC padahal opsi dropdown sebenarnya ada
- error awal sempat dipicu juga oleh input funcloc yang tidak cocok

Perbaikan yang dilakukan:

- matching tidak hanya pakai nama full
- baca kode asset utama seperti `ZP60`, `W21A`, `JL92`, `J10`, `L20`
- tambah retry agar script menunggu opsi dropdown benar-benar siap
- perbaiki pembacaan lokasi agar kata biasa seperti `DAN` tidak dianggap kode lokasi

## Catatan penting

- `Tanggal Realisasi` masih dikosongkan.
- `No WO` dibiarkan kosong.
- `Material` belum diisi.
- Mode live submit belum diaktifkan lagi.
- Saat ini script baru fokus aman di mode tes lebih dulu.

## Arah update berikutnya

Kalau nanti mau lanjut, kandidat update paling natural:

1. mode `live` untuk klik `Simpan` atau `Kirim SAP`
2. proses semua batch, bukan hanya batch pertama
3. validasi input asset sebelum browser mulai isi form
4. log hasil per batch
