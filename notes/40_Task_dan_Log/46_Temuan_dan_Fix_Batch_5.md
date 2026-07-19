# 🐛 Temuan & Fix Batch 5

> **Tanggal**: 18-19 Juli 2026  
> **Agent**: Antigravity (Google Deepmind)  
> **Status**: ✅ Semua fixed, EXE dibuild ulang  

---

## 🔴 Bug 1: Blank Screen Setelah Minimize Lama

**Gejala**: App dibuka, proses rename berjalan, minimize lama → restore → tampilan putih kosong.

**Root Cause**: WebView2 GPU rendering context corrupt setelah minimize lama di Windows.

**Fix di** [[../web-app/run_desktop_webview.py|run_desktop_webview.py]]:

```python
# Disable GPU acceleration WebView2 — cegah context hilang
os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--disable-gpu"

def on_restored():
    # location.reload() full render ulang, bukan cuma resize event
    time.sleep(0.1)
    webview.windows[0].evaluate_js('window.location.reload()')
```

2 perubahan:
1. Environment variable `--disable-gpu` sebelum WebView2 init
2. Ganti `dispatchEvent("resize")` jadi `location.reload()` dengan 100ms delay

---

## 🔴 Bug 2: Cancel → Proses Ulang Stuck

**Gejala**: Proses di-cancel, lalu klik proses lagi → stuck di "Mulai proses...", tidak jalan.

**Root Cause**: `cancelledRef.current` tetap `true` setelah cancel, tidak di-reset. For-loop langsung return.

**Fix di** [[../web-app/src/App.jsx|App.jsx]] line 97:

```js
const handleProcess = useCallback(async () => {
    if (!files.length) return;
    cancelledRef.current = false;  // ← tambah 1 baris ini
    setProcessing(true);
    ...
```

---

## 🔴 Bug 3: PTPP JPL ELEKTRIK → Harusnya JPL BNR

**Gejala**: File `PERAWATAN PINTU PERLINTASAN JPL ELEKTRIK BNR BOP ...` → hasilnya `JPL ELEKTRIK`, bukan `JPL BNR`.

**Root Cause**: Regex `JPL\s+([A-Z0-9]+)` menangkap kata pertama setelah JPL = "ELEKTRIK".

**Fix di** [[../web-app/src/utils/detector.js|detector.js]] (2 titik — line 331 & 626):

```js
// Skip "ELEKTRIK" sebagai noise word
const fnMatch = filenameUpper.match(/JPL\s+(?:ELEKTRIK\s+)?([A-Z0-9]+)/);
```

---

## 🔴 Bug 4: PDSE/PTDS/PTLS → "DISETUJUI"

**Gejala**: File `PERAWATAN PDSE DISETUJUI 05-04-2025.pdf` → output menampilkan "DISETUJUI" bukan kategori dokumen.

**Root Cause**:  
- OCR gagal membaca teks → `textFlat` kosong  
- Filename fallback (line 588-627) tidak punya keyword `PDSE`/`PTDS`/`PTLS`  
- `kode=""` dan `kategori=""` → noise keyword "DISETUJUI" leak ke output  

**Fix di** [[../web-app/src/utils/detector.js|detector.js]]:

```js
// 1. Tambah 3 branch fallback filename (setelah PTPP fallback)
} else if (filenameUpper.includes("PDSE")) {
    kode = "BPBYE2"; kategori = "PDSE"; assets = [{ id: "", loc }];
} else if (filenameUpper.includes("PTDS")) {
    kode = "BPBKS15"; kategori = "PTDS"; assets = [{ id: "", loc }];
} else if (filenameUpper.includes("PTLS")) {
    kode = "BPBKS16"; kategori = "PTLS"; assets = [{ id: "", loc }];

// 2. Filter NOISE_WORDS di extractFuncloc (line 89)
// Baris "LOKASI: DISETUJUI" → skip kata "DISETUJUI"
const mapped = subs.map(s => {
    if (NOISE_WORDS.has(s)) return null;  // ← tambah
    ...
}).filter(Boolean);
```

---

## 📦 Build Status

| Step | Status |
|---|---|
| `npm run build` (React/Vite) | ✅ Sukses |
| `pyinstaller build_exe.spec` (EXE) | ✅ Sukses — `dist/SintelisUtility.exe` + `dist/SintelisUtility/` |

---

## 🔗 Terkait

- [[00_Dashboard|Dashboard]]
- [[43_Temuan_dan_Rencana_Perbaikan_v2|Batch 2]]
- [[44_Temuan_dan_Rencana_Perbaikan_v3|Batch 3]]
- [[42_Riwayat_Pembaruan|Riwayat Pembaruan]]

---

## 📋 Rencana Next Update (Batch 6)

### ✅ Drag & Drop di Seluruh Panel Kiri

**Status**: ✅ Done (belum build)

**Deskripsi**: Sebelumnya drag file PDF hanya bisa di kotak dropzone khusus. Sekarang seluruh area kiri (termasuk file list) bisa menerima drop.

**Fix di** [[../web-app/src/App.jsx|App.jsx]] line 327:

```jsx
<div className="left-panel"
  onDragOver={e => { e.preventDefault(); }}
  onDrop={e => { e.preventDefault(); handleDrop(e); }}
>
```

### ⏳ Progress Bar Pindah ke Atas Tombol

**Status**: ⏳ Belum dikerjakan

**Deskripsi**: Saat ini progress bar (`{processing && ...}`) muncul di bawah file list. Harus dipindah ke area di atas tombol "Proses File" agar lebih terlihat saat proses berjalan.

**Rencana**: Pindahkan block progress bar JSX dari line 386-391 ke atas action buttons (sekitar line 398), di dalam card yang sama.
