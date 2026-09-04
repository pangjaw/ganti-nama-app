# 📊 Master Data Aset & Identitas Aset — UPT Resor Sintelis 1.21 BOO (2026)

Dokumen ini berisi acuan resmi **Master Data Aset Resor 1.21 Bogor (2026)** beserta daftar whitelist **Nomor Identitas Aset Spesifik per Lokasi** untuk validasi maintenance, OCR, audit kelengkapan, maupun pengujian aplikasi lain.

---

## 📑 1. Ringkasan Agregat & Target Maintenance Bulanan

| No | Kategori Aset | Kode SAP | Target File / Bulan | Frekuensi Perawatan | Wilayah Stasiun / Petak |
|---|---|:---:|:---:|:---:|---|
| 1 | **WESEL (ELEKTRIK & MEKANIK)** | `BPBYE1` | **62** | 2-Mingguan (2 file/bln) | BOO (16), CLT (4), BOP (7), MSG (4) |
| 2 | **DETEKSI KA (AXLE COUNTER)** | `BPBYE7` | **139** | Bulanan | BOO (35), CLT (14), BTT (12), BOP (22), MSG (18), COS (4), CGB (4), BJD-CLT (5), CLT-BOO (25) |
| 3 | **PERAGA SINYAL** | `BPBYE3` | **125** | Bulanan | BOO (20), CLT (9), BTT (12), BOP (14), MSG (13), COS (4), CGB (4), BJD-CLT (9), CLT-BOO (40) |
| 4 | **SERAT OPTIK (OTB)** | `BPBKF4` | **22** | Bulanan | BOO, CLT, BTT, BOP, COS, MSG, CGB, Petak BJD-CLT, CLT-BOO, BOP-BTT |
| 5 | **TELKOM JPL (PTPP)** | `BPBKS17` | **11** | Bulanan | BOO (2), BOP-BTT (2), CLT (1), CLT-BOO (2), CGB (2) |
| 6 | **PINTU PERLINTASAN** | `BPBKS17` | **10** | Bulanan | BOO (2), BOP-BTT (2), CLT (1), CLT-BOO (2), CGB (2) |
| 7 | **CATU DAYA / RECTIFIER** | `BPBYE8` | **9** | Bulanan | BOO (2), CLT (1), BOP (1), BTT (1), COS (2), MSG (1), CGB (1) |
| 8 | **TELEKOMUNIKASI LUAR STASIUN (PTLS)** | `BPBKS16` | **8** | Bulanan | BOO (2), BTT (1), COS (1), MSG (2), CGB (1) |
| 9 | **PERALATAN DALAM (PDSE)** | `BPBYE2` | **7** | Bulanan | CLT (1), BOO (1), BOP (1), BTT (1), COS (1), MSG (1), CGB (1) |
| 10 | **TELEKOMUNIKASI STASIUN (PTDS)** | `BPBKS15` | **7** | Bulanan | CLT (1), BOO (1), BOP (1), BTT (1), COS (1), MSG (1), CGB (1) |
| 11 | **POINT LOCK (W81 BOO)** | `BPBYE12` | **2** | 2-Mingguan (2 file/bln) | BOO (`W81 BOO`) |
| 12 | **CTC / CTS** | `BPBYE4` | **2** | Bulanan | CLT (1), BOO (1) |
| | **TOTAL TARGET** | | **398 File** | | *(372 Unit Aset SAP)* |

---

## 🔀 2. Master Whitelist Identitas Aset Spesifik

### 2.1 Wesel (`BPBYE1`)
* **BOO (Bogor)** [16 Wesel]: `W13`, `W21A`, `W21B1`, `W21B2`, `W23A`, `W23B`, `W31A`, `W31B`, `W31D`, `W31E`, `W41`, `W43`, `W51A1`, `W51A2`, `W61A1`, `W61A2`, `W81`
* **CLT (Cilebut)** [4 Wesel]: `W11`, `W13`, `W21`, `W23`
* **BOP (Bogor Paledang)** [7 Wesel]: `W25`, `W27A`, `W27B`, `W47A`, `W47C`, `W47D`, `W67`
* **MSG (Maseng)** [4 Wesel]: `W11`, `W13`, `W21`, `W23`

---

### 2.2 Pintu Perlintasan (JPL) & PTPP (`BPBKS17`)
* **BOO**: `JPL 01`, `JPL 02`
* **BOP-BTT**: `JPL BNR`, `JPL 07`
* **CLT**: `JPL 26N`
* **CLT-BOO**: `JPL 27`, `JPL 28`
* **CGB**: `JPL 15`, `JPL 16`

---

### 2.3 Point Lock / Pengaman Wesel (`BPBYE12`)
* **BOO**: `W81 BOO` *(Hanya 1 aset, frekuensi 2-mingguan = 2 file/bulan)*

---

### 2.4 Peraga Sinyal (`BPBYE3`)
* **BOO**: `B214`, `J10`, `J20`, `JL12A`, `JL12B`, `JL22A`, `JL22B`, `JL32A`, `JL32B`, `JL42A`, `JL42B`, `JL42C`, `JL52`, `JL62B`, `JL72`, `JL92`, `L20`, `L60`, `L62A`, `L80`
* **CLT**: `J10`, `J12A`, `J12B`, `J14`, `J20`, `J22`, `J24`
* **BTT**: `J10`, `J12A`, `J12B`, `J14`, `J20`, `J22A`, `J22B`, `J24`, `MJ10`, `MJ14`, `MJ20`, `MJ24`
* **BOP**: `J28`, `J48`, `JL26A`, `JL26B`, `JL46A`, `JL46B`, `JL66B`, `L28`, `L47A`, `L47B`, `L68`, `MJ28`, `MJ48`, `UJ26B`
* **CGB**: `B101`, `B201`, `MB101`, `MB201`
* **COS**: `B101`, `B201`, `MB101`, `MB201`
* **MSG**: `J10`, `J12B`, `J14`, `J20`, `J22A`, `J22B`, `J24`, `MJ10`, `MJ14`, `MJ20`, `MJ24`, `UJ12`, `UJ22B`
* **BJD-CLT**: `B101`, `B102`, `B205`, `B206`, `B207`, `MJ20`, `UB101`, `UB102`, `UB205`, `UB206`
* **CLT-BOO**: `B101`–`B112`, `B201`–`B213`, `MJ14`, `MJ20`, `UB102`–`UB106`, `UB110`, `UB202`, `UB206`–`UB212`

---

### 2.5 Deteksi KA / Axle Counter (`BPBYE7`)
* **BOO**: `ZP 10A`, `ZP 10B`, `ZP 12A`, `ZP 12B`, `ZP 13`, `ZP 20A`, `ZP 20B`, `ZP 20C`, `ZP 21A`, `ZP 21B`, `ZP 21C`, `ZP 22A`, `ZP 22B`, `ZP 23A`, `ZP 23B`, `ZP 24A`, `ZP 24B`, `ZP 31A`–`ZP 31E`, `ZP 32A`, `ZP 32B`, `ZP 41`, `ZP 42A`–`ZP 42C`, `ZP 52`, `ZP 60`, `ZP 61`, `ZP 62A`, `ZP 62B`, `ZP 72`, `ZP 92`
* **CLT**: `ZP 10A`, `ZP 10B`, `ZP 11`, `ZP 12A`, `ZP 12B`, `ZP 13`, `ZP 14A`, `ZP 14B`, `ZP 20A`, `ZP 20B`, `ZP 22A`, `ZP 22B`, `ZP 24A`, `ZP 24B`
* **BTT**: `ZP 10A`, `ZP 10B`, `ZP 12A`, `ZP 12B`, `ZP 14A`, `ZP 14B`, `ZP 20A`, `ZP 20B`, `ZP 22A`, `ZP 22B`, `ZP 24A`, `ZP 24B`
* **BOP**: `ZP 25`, `ZP 26A`–`ZP 26C`, `ZP 27A`–`ZP 27C`, `ZP 28A`–`ZP 28C`, `ZP 46A`, `ZP 46B`, `ZP 47A`–`ZP 47D`, `ZP 48A`–`ZP 48C`, `ZP 66A`, `ZP 66B`, `ZP 68`
* **MSG**: `ZP 10A`–`ZP 10C`, `ZP 11`, `ZP 12A`, `ZP 12B`, `ZP 13`, `ZP 14A`–`ZP 14C`, `ZP 20A`–`ZP 20C`, `ZP 22A`, `ZP 22B`, `ZP 24A`–`ZP 24C`
* **CGB & COS**: `ZP 101A`, `ZP 101B`, `ZP 201A`, `ZP 201B`
* **BJD-CLT**: `ZP 101`, `ZP 102`, `ZP 205`, `ZP 206`, `ZP 207`
* **CLT-BOO**: `ZP 101`–`ZP 112`, `ZP 201`–`ZP 213`

---

### 2.6 Serat Optik OTB (`BPBKF4`)
* **Sub-Tipe ER**:
  * **ER RADIO**: HANYA `BOO`
  * **ER SINYAL**: `BTT`, `CLT`, `BOO`, `BOP`, `COS`, `MSG`, `CGB`
  * **ER TELKOM**: `BOO`, `BTT`, `COS`, `MSG`, `CGB`
* **Petak Lintas (Bulanan)**: `BJD-CLT` (2), `CLT-BOO` (2), `BOP-BTT` (2)

---

### 2.7 Peralatan Dalam / PDSE (`BPBYE2`)
* **7 Stasiun**: `PDSE CLT`, `PDSE BOO`, `PDSE BOP`, `PDSE BTT`, `PDSE COS`, `PDSE MSG`, `PDSE CGB`

---

### 2.8 Catu Daya (`BPBYE8`)
* **9 Unit**: `CLT` (1), `BOO` (2), `BOP` (1), `BTT` (1), `COS` (2), `MSG` (1), `CGB` (1)

---

### 2.9 Telekomunikasi Stasiun / PTDS (`BPBKS15`)
* **7 Stasiun**: `PTDS CLT`, `PTDS BOO`, `PTDS BOP`, `PTDS BTT`, `PTDS COS`, `PTDS MSG`, `PTDS CGB`

---

### 2.10 Telekomunikasi Luar Stasiun / PTLS (`BPBKS16`)
* **5 Lokasi**: `PTLS BOO` (2), `PTLS BTT` (1), `PTLS COS` (1), `PTLS MSG` (2), `PTLS CGB` (1)

---

### 2.11 CTC / CTS (`BPBYE4`)
* **2 Unit**: `CTS CLT`, `CTS BOO`

---

## 📍 3. Referensi Kode Stasiun & Wilayah

| Kode | Nama Stasiun / Petak Lintas | Wilayah Operasional |
|:---:|:---|:---:|
| **BJD-CLT** | Bojonggede - Cilebut | BTP JAK |
| **CLT** | Cilebut | BTP JAK |
| **CLT-BOO** | Cilebut - Bogor | BTP JAK |
| **BOO** | Bogor | BTP JAK |
| **BOP** | Bogor Paledang | BOCI |
| **BOP-BTT** | Bogor Paledang - Batutulis | BOCI |
| **BTT** | Batutulis | BOCI |
| **COS** | Ciomas | BOCI |
| **MSG** | Maseng | BOCI |
| **CGB** | Cigombong | BOCI |

---

*Dokumen ini dibuat secara otomatis dan siap dipakai sebagai acuan master di project/aplikasi lain.*
