# 📋 Pemetaan Kode & Kategori Checklist

#knowledge #playwright #agent

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

Halaman ini berisi tabel referensi pemetaan field input untuk masing-masing tipe asset saat membuat Program Realisasi (Work Order) baru di portal P3-STE. Pemetaan ini diterapkan secara otomatis di dalam script `create_p3ste_wo.py`.

---

## 🗺️ Tabel Pemetaan (Mapping Table)

| Jenis Asset | Tipe Checklist | Kategori | Periode | Kode Checklist (Persis pada Web Dropdown) |
| :--- | :--- | :--- | :--- | :--- |
| **Wesel** | Perawatan | Sinyal | 2 Mingguan | `PERAWATAN WESEL ELEKTRIK 2 MINGGUAN - (WESEL BIASA)` |
| **Sinyal** | Perawatan | Sinyal | Bulanan | `PERAWATAN PERAGA SINYAL ELEKTRIK 1 BULANAN - (-)` |
| **AXC** | Perawatan | Sinyal | Bulanan | `PERAWATAN AXLE COUNTER SIEMENS 1 BULANAN - (SIEMENS)` |
| **AXC Frauscher** | Perawatan | Sinyal | Bulanan | `PERAWATAN AXLE COUNTER FRAUSCHER 1 BULANAN - (FRAUSCHER)` |
| **PDSE** | Perawatan | Sinyal | Bulanan | `PERAWATAN PERALATAN DALAM PERSINYALAN ELEKTRIK 1 BULANAN` |
| **Serat Optik (ER)** | Perawatan | Telekomunikasi | Bulanan | `PERAWATAN SERAT OPTIK 1 BULANAN` |
| **Serat Optik (ER TELKOM)** | Perawatan | Telekomunikasi | Bulanan | `PERAWATAN SERAT OPTIK 1 BULANAN` |
| **Serat Optik (JPL)** | Perawatan | Telekomunikasi | Bulanan | `PERAWATAN SERAT OPTIK 1 BULANAN` |
| **PTDS** | Perawatan | Telekomunikasi | Bulanan | `PERAWATAN PERALATAN TELEKOMUNIKASI DI STASIUN 1 BULANAN` |
| **PTLS** | Perawatan | Telekomunikasi | Bulanan | `PERAWATAN PERALATAN TELEKOMUNIKASI DI LUAR STASIUN 1 BULANAN` |
| **PTLP** | Perawatan | Telekomunikasi | Bulanan | `PERAWATAN PERALATAN TELEKOMUNIKASI DI PINTU PERLINTASAN 1 BULANAN` |
| **Pintu Perlintasan** | Perawatan | Sinyal | Bulanan | `PERAWATAN PERALATAN PINTU PERLINTASAN 1 BULANAN` |
| **CTC-CTS** | Perawatan | Sinyal | Bulanan | `PERAWATAN PERALATAN CTC-CTS 1 BULANAN` |
| **Catu Daya** | Perawatan | Sinyal | Bulanan | `PERAWATAN CATU DAYA 1 BULANAN` |
| **Radio Waystation** | Perawatan | Telekomunikasi | 3 Bulanan | `PERAWATAN PERALATAN RADIO WAYSTATION` |
| **Sistem Waystation** | Perawatan | Telekomunikasi | 1 Tahunan | `PERAWATAN PERALATAN SISTEM WAYSTATION 1 TAHUNAN` |
| **Radio Basestation** | Perawatan | Telekomunikasi | 6 Bulanan | `PERAWATAN PERALATAN RADIO BASESTATION 6 BULANAN` |
| **Radio Basestation Digital** | Perawatan | Telekomunikasi | 6 Bulanan | `PERAWATAN PERALATAN RADIO BASESTATION DIGITAL 6 BULANAN` |
| **Radio Basestation Tait** | Perawatan | Telekomunikasi | 6 Bulanan | `PERAWATAN PERALATAN RADIO BASESTATION TAIT 6 BULANAN` |

---

## 🛠️ Implementasi Kode pada Script

Di dalam berkas `create_p3ste_wo.py`, data mapping di atas direpresentasikan menggunakan struktur data berikut untuk mempermudah pemilihan opsi pada elemen select HTML:

```python
# Ilustrasi logika mapping di create_p3ste_wo.py
MAPPING = {
    "wesel": {
        "tipe": "Perawatan",
        "kategori": "Sinyal",
        "periode": "2 Mingguan",
        "kode_checklist": "PERAWATAN WESEL ELEKTRIK 2 MINGGUAN - (WESEL BIASA)"
    },
    "sinyal": {
        "tipe": "Perawatan",
        "kategori": "Sinyal",
        "periode": "Bulanan",
        "kode_checklist": "PERAWATAN PERAGA SINYAL ELEKTRIK 1 BULANAN - (-)"
    },
    "axc": {
        "tipe": "Perawatan",
        "kategori": "Sinyal",
        "periode": "Bulanan",
        "kode_checklist": "PERAWATAN AXLE COUNTER SIEMENS 1 BULANAN - (SIEMENS)"
    }
}
```

---

## 📌 Alur Pengisian Dropdown di Web

Ketika script mengotomasi browser, Playwright akan mengeksekusi langkah-langkah berikut secara berurutan sesuai pemetaan di atas:
1.  Mengeklik dropdown **Tipe Checklist** dan memilih opsi sesuai mapping (contoh: `Perawatan`).
2.  Menunggu dropdown **Kategori** aktif, lalu memilih `Sinyal`.
3.  Menunggu dropdown **Periode** aktif, lalu memilih sesuai periode asset (contoh: `2 Mingguan` atau `Bulanan`).
4.  Menunggu dropdown **Kode Checklist** aktif, lalu memilih string kode checklist yang tepat (contoh: `PERAWATAN WESEL ELEKTRIK 2 MINGGUAN - (WESEL BIASA)`).
5.  Setelah isian header di atas selesai, barulah script memicu pemanggilan baris-baris FuncLoc asset di bawahnya.

---

## 🔄 Koneksi Antar Note

- [[12_Otomasi_Work_Order]] — Panduan penggunaan `create_p3ste_wo.py`
- [[23_Otomasi_Browser_Playwright]] — Mekanisme dropdown selection
- [[51_Alur_Kerja_Agent]] — Scenario 2: Alur kerja WO
- [[00_Dashboard|Kembali ke Dashboard]]
