# 📋 Pemetaan Kode & Kategori Checklist

#knowledge #ocr #referensi

> [!tip] Kembali ke [[00_Dashboard|Dashboard Utama]]

Halaman ini berisi tabel referensi pemetaan field input untuk masing-masing tipe asset. Pemetaan ini diterapkan di `detector.js` (branch Gate B — fallback filename-based) dan digunakan sebagai acuan format rename output.

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

## 🔄 Koneksi Antar Note

- [[22_Logika_OCR]] — Tabel branch `detectDoc()` & kode checklist
- [[33_Data_Aset_Referensi]] — Data aset resmi validasi
- [[35_Aturan_Serat_Optik_OTB]] — Deteksi SO OTB
- [[00_Dashboard|Kembali ke Dashboard]]
