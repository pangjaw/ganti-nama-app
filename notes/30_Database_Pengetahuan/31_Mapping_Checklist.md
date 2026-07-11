# 📋 Pemetaan Kode & Kategori Checklist

Halaman ini berisi tabel referensi pemetaan field input untuk masing-masing tipe asset saat membuat Program Realisasi (Work Order) baru di portal P3-STE. Pemetaan ini diterapkan secara otomatis di dalam script `create_p3ste_wo.py`.

---

## 🗺️ Tabel Pemetaan (Mapping Table)

| Jenis Asset | Tipe Checklist | Kategori | Periode | Kode Checklist (Persis pada Web Dropdown) |
| :--- | :--- | :--- | :--- | :--- |
| **Wesel** | Perawatan | Sinyal | 2 Mingguan | `PERAWATAN WESEL ELEKTRIK 2 MINGGUAN - (WESEL BIASA)` |
| **Sinyal** | Perawatan | Sinyal | Bulanan | `PERAWATAN PERAGA SINYAL ELEKTRIK 1 BULANAN - (-)` |
| **AXC** | Perawatan | Sinyal | Bulanan | `PERAWATAN AXLE COUNTER SIEMENS 1 BULANAN - (SIEMENS)` |

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
