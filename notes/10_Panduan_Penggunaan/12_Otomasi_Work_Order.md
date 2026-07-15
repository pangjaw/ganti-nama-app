# 🤖 Alur Otomasi Work Order (`create_p3ste_wo.py`)

#panduan #playwright #agent

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

`create_p3ste_wo.py` adalah script otomasi berbasis Playwright untuk membantu pengisian form tambah Program Realisasi di website P3-STE KAI (`https://p3-ste.kai.id/masterdataprogramrealisasi/form-add`).

---

## 📥 Format Input User

Saat script dijalankan, Anda akan diminta memasukkan data secara interaktif di terminal dengan format berikut:

1.  **Jenis Asset**: Pilih salah satu antara `wesel`, `sinyal`, atau `axc`.
2.  **Lokasi Dropdown**: Ketik nama lokasi yang sesuai dengan opsi dropdown pada web (contoh: `Stasiun Bogor`).
3.  **Jumlah Orang**: Jumlah personil pelaksana (contoh: `1`).
4.  **Tanggal dan Jam**: Format `[DDMMYYYY HHMM-HHMM]` (contoh: `01072026 0800-2300`).
5.  **Daftar Short Text**: Tempelkan (paste) daftar nama asset/short text secara multiline. Akhiri dengan menekan **Enter dua kali** (baris kosong).

### Contoh Tampilan Input:
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

---

## ⚙️ Logika Pengolahan & Pengisian Data

### 1. Konversi Waktu
Input tanggal & jam tunggal dikonversi otomatis untuk dua field:
-   **Tanggal Program**: Diambil dari tanggal awal (misal: `01/07/2026`).
-   **Start-Finish Date**: Diformat lengkap dengan jam (misal: `01/07/2026 08:00 - 01/07/2026 23:00`).

### 2. Pengisian Form Web (Flow Playwright)
1.  **Pilih Dropdown Atas**: Menyetel tipe, kategori, periode, dan kode checklist sesuai dengan jenis asset (lihat detail mapping di [[31_Mapping_Checklist|Pemetaan Checklist]]).
2.  **Tambah FuncLoc Baru**: Script akan mengeklik tombol `Tambah FuncLoc` sebanyak jumlah item yang Anda masukkan. Semua baris kosong (row) dimunculkan terlebih dahulu sebelum diisi.
3.  **Pengisian Baris FuncLoc**: Setiap baris diisi satu per satu dengan memilih Short Text yang cocok, lalu mengisi Start-Finish Date, dan Operation (jika tersedia).

### 3. Logika Pencocokan (Matching) Short Text
Agar script tidak mudah error jika input teks dari user berbeda tipis dengan dropdown web, script menerapkan sistem pencarian bertahap (fallback):
1.  **Teks Penuh (Exact Match)**: Mencari kecocokan nama full persis.
2.  **Teks Normalisasi**: Mencari kecocokan setelah spasi ganda atau karakter khusus dibersihkan.
3.  **Kode Asset Utama**: Mengekstrak kode utama asset (misal: `ZP60`, `W21A`, `JL92`) lalu mencocokkannya.
4.  **Kode Asset + Lokasi**: Mencocokkan kode asset dikombinasikan dengan kode stasiun/lokasi (misal: `ZP60` + `BOO`).

> [!NOTE]
> Script menggunakan sistem *retry* agar menunggu opsi dropdown benar-benar ter-load sebelum mengeklik.

---

## 🧪 Aturan Mode Pengujian (Test Mode)

Demi keamanan data sistem P3-STE, script ini default dikonfigurasi dalam **Mode Test**:
*   **Tanpa Submit**: Script **tidak** akan mengeklik tombol `Simpan` atau `Kirim SAP`.
*   **Browser Terbuka**: Setelah selesai mengisi seluruh form, browser Chromium akan tetap terbuka agar Anda dapat melakukan review manual terhadap isian data. Tekan `Enter` di terminal untuk menutup browser.
*   **Batasan Jumlah Item**: Jika Anda memasukkan lebih dari **5 item**, script saat ini hanya akan memproses **5 item pertama** (batch pertama). Item selebihnya akan ditampilkan informasinya saja di terminal untuk diproses secara terpisah.

---

## 🛠️ Perintah Uji Coba (Self-Test)

Anda bisa menguji kevalidan kode regex parsing dan normalisasi text secara instan tanpa perlu meluncurkan browser Chromium dengan perintah:
```powershell
python create_p3ste_wo.py --self-test
```
Perintah ini akan mengetes:
*   Fungsi pembacaan & parser input tanggal program.
*   Logika pembagi batch data (maksimal 5 item).
*   Logika ekstraksi keyword/kode asset untuk Wesel, Sinyal, dan AXC.
*   Pencegahan kata umum (seperti `DAN`, `LENGKAP`) agar tidak dianggap sebagai kode lokasi.

---

## 🔄 Koneksi Antar Note

- [[31_Mapping_Checklist]] — Detail mapping dropdown per jenis asset
- [[23_Otomasi_Browser_Playwright]] — Mekanisme login & session Playwright
- [[51_Alur_Kerja_Agent]] — Scenario 2: Alur kerja WO otomatis
- [[42_Riwayat_Pembaruan]] — Riwayat tahapan pengembangan script ini
- [[00_Dashboard|Kembali ke Dashboard]]
