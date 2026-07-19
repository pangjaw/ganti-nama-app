// =============================================================================
// App.jsx — Main React Component for Sintelis Utility Client-Side App
// =============================================================================

import { useState, useRef, useCallback, useEffect } from 'react';
import { detectDoc, buildFilename } from './utils/detector';
import { processSingleFile } from './utils/pdfProcessor';
import { pickDirectory, writeFileToDir, createZipBlob, triggerDownload } from './utils/fsHandler';
import * as XLSX from 'xlsx';

export default function App() {
  const [files, setFiles] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [message, setMessage] = useState(null);
  const [jenisKegiatan, setJenisKegiatan] = useState('Perawatan');
  const [instansi, setInstansi] = useState('BTP JAK');
  const [dirHandle, setDirHandle] = useState(null);
  const [results, setResults] = useState([]);
  const [errors, setErrors] = useState([]);
  const [logs, setLogs] = useState([]);
  const [activeTab, setActiveTab] = useState('hasil');
  const [paused, setPaused] = useState(false);
  const [errorFileNames, setErrorFileNames] = useState([]);
  const logEndRef = useRef();
  const inputRef = useRef();
  const cancelledRef = useRef(false);
  const pausedRef = useRef(false);
  const resumeRef = useRef(null);
  const processRef = useRef(null); // ref ke handleProcess agar handleRetryErrors tidak stale

  // Force re-render key — digunakan saat window jadi visible lagi setelah minimize
  // Bug WebView2: React state changes saat window hidden tidak di-paint.
  // Increment key ini memaksa React mount ulang komponen hasil/error.
  const [visibilityKey, setVisibilityKey] = useState(0);

  const formatBd = instansi === 'BTP BD';

  // Visibility listener: force re-render saat window restore dari minimize
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        // Force re-render dengan increment key
        // Delay sedikit agar compositor WebView2 siap
        setTimeout(() => {
          setVisibilityKey(k => k + 1);
        }, 150);
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);

  // Auto-scroll log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const addLog = useCallback((type, msg) => {
    setLogs(prev => [...prev, { type, msg, ts: Date.now() }]);
  }, []);

  const handleFileSelect = useCallback((e) => {
    const selected = Array.from(e.target.files || []);
    setFiles(prev => {
      const existingNames = new Set(prev.map(f => f.name));
      const newFiles = selected.filter(f => !existingNames.has(f.name));
      return [...prev, ...newFiles];
    });
    setMessage(null); setResults([]); setErrors([]); setLogs([]);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.pdf'));
    setFiles(prev => {
      const existingNames = new Set(prev.map(f => f.name));
      const newFiles = dropped.filter(f => !existingNames.has(f.name));
      return [...prev, ...newFiles];
    });
    setMessage(null); setResults([]); setErrors([]); setLogs([]);
  }, []);

  const removeFile = useCallback((name) => {
    setFiles(prev => prev.filter(f => f.name !== name));
  }, []);

  const handlePickDir = useCallback(async () => {
    const handle = await pickDirectory();
    setDirHandle(handle);
    if (handle) addLog('success', `Folder dipilih: ${handle.name}`);
    else addLog('info', 'Mode ZIP (folder tidak dipilih).');
  }, [addLog]);

  const handleCancel = useCallback(() => {
    cancelledRef.current = true;
    // Jika sedang pause, resume dulu agar loop bisa keluar
    pausedRef.current = false;
    if (resumeRef.current) { resumeRef.current(); resumeRef.current = null; }
    setPaused(false);
    addLog('error', 'Proses dibatalkan pengguna.');
  }, [addLog]);

  const handlePause = useCallback(() => {
    pausedRef.current = true;
    setPaused(true);
    addLog('info', 'Proses dijeda. Klik Lanjutkan untuk melanjutkan.');
  }, [addLog]);

  const handleResume = useCallback(() => {
    pausedRef.current = false;
    setPaused(false);
    if (resumeRef.current) { resumeRef.current(); resumeRef.current = null; }
    addLog('info', 'Proses dilanjutkan.');
  }, [addLog]);

  // handleProcess: opsional terima fileList untuk retry-error-only
  const handleProcess = useCallback(async (fileList) => {
    const targetFiles = Array.isArray(fileList) ? fileList : files;
    if (!targetFiles.length) return;

    cancelledRef.current = false;
    pausedRef.current = false;
    setPaused(false);
    setErrorFileNames([]);
    setProcessing(true);
    setLogs([]);
    setProgress({ current: 0, total: targetFiles.length });
    setMessage(null); setResults([]); setErrors([]);

    const TIMEOUT_MS = 30000; // 30 detik per file
    addLog('info', `Mulai proses ${targetFiles.length} file...`);
    const allResultItems = [];
    const soErAssets = [];
    const soBulananAssets = [];
    const errorList = [];
    const erroredFiles = []; // track File objects yang error untuk retry

    // Parallel processing: 4 file sekaligus
    const CONCURRENCY = 4;
    let globalIdx = 0;

    for (let ci = 0; ci < targetFiles.length; ci += CONCURRENCY) {
      // --- Cek cancel ---
      if (cancelledRef.current) {
        setProcessing(false);
        setProgress({ current: 0, total: 0 });
        return;
      }

      // --- Cek pause: tunggu sampai resume dipanggil ---
      while (pausedRef.current && !cancelledRef.current) {
        await new Promise(resolve => { resumeRef.current = resolve; });
      }
      if (cancelledRef.current) {
        setProcessing(false);
        setProgress({ current: 0, total: 0 });
        return;
      }

      const chunk = targetFiles.slice(ci, ci + CONCURRENCY);
      const chunkStartIdx = ci;

      // Log semua file di chunk ini
      for (let j = 0; j < chunk.length; j++) {
        addLog('processing', `[${chunkStartIdx + j + 1}/${targetFiles.length}] OCR ${chunk[j].name}`);
      }

      // Wrap setiap file dengan timeout
      const batchResults = await Promise.allSettled(
        chunk.map(f => Promise.race([
          processSingleFile(f, detectDoc),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error(`TIMEOUT: proses file >30 detik`)), TIMEOUT_MS)
          )
        ]))
      );

      // Proses hasil batch berurutan (agar log & progress urut)
      for (let j = 0; j < batchResults.length; j++) {
        if (cancelledRef.current) {
          setProcessing(false);
          setProgress({ current: 0, total: 0 });
          return;
        }

        const counter = chunkStartIdx + j + 1;
        const file = chunk[j];
        const settled = batchResults[j];

        if (settled.status === 'rejected') {
          const errMsg = settled.reason?.message || 'Unknown error';
          errorList.push(`ERROR|${file.name}|${errMsg}`);
          erroredFiles.push(file);
          addLog('error', `[${counter}/${targetFiles.length}] ${file.name}: ${errMsg}`);
          globalIdx++;
          setProgress({ current: globalIdx, total: targetFiles.length });
          continue;
        }

        const res = settled.value;
        globalIdx++;
        setProgress({ current: globalIdx, total: targetFiles.length });

        if (res.status === 'skip') { continue; }
        if (res.status === 'error' || res.status === 'exception') {
          errorList.push(`ERROR|${res.filename}|${res.error}`);
          erroredFiles.push(file);
          addLog('error', `[${counter}/${targetFiles.length}] ${res.filename}: ${res.error}`);
          continue;
        }

        const { filename, fileBytes, kode, kategori, assets, tglFull, prefixPeriode, textFlat } = res;
        addLog('info', `[OCR TEXT] ${filename}: "${textFlat ? textFlat.substring(0, 120) : '(KOSONG)'}"`);
        if (assets && assets.length > 0) {
          addLog('info', `[ASSETS] ${filename}: ${assets.map(a => `${a.id || '(TANPA ID)'} (${a.loc || '(TANPA LOKASI)'})`).join(', ')}`);
        }
        if (!assets || !assets.length) {
          errorList.push(`ERROR|${filename}|Jenis dokumen tidak terdeteksi.`);
          erroredFiles.push(file);
          addLog('error', `[${counter}/${targetFiles.length}] ${filename}: tidak terdeteksi`);
          continue;
        }

        addLog('success', `[${counter}/${targetFiles.length}] ${filename} → ${kategori} (${assets.length} aset)`);

        for (const asset of assets) {
          const aid = asset.id || '';
          const loc = asset.loc || '';
          let identitas = aid ? `${kategori} ${aid} ${loc}` : `${kategori} ${loc}`;
          identitas = identitas.replace(/\s+/g, ' ').trim();

          if (asset.firstOtb !== undefined && asset.erType !== undefined) {
            soErAssets.push({ fileBytes, fname: filename, firstOtb: asset.firstOtb, erType: asset.erType, loc, kode, kategori, tglFull, prefixPeriode, jenisKegiatan, formatBd, otbMin: asset.otbMin ?? asset.firstOtb, otbMax: asset.otbMax ?? asset.firstOtb, hasOtbNumbers: asset.hasOtbNumbers });
          } else if (asset.isBulanan) {
            soBulananAssets.push({ fileBytes, fname: filename, seqNum: asset.seqNum ?? 1, loc, kode, kategori, tglFull, prefixPeriode, jenisKegiatan, formatBd });
          } else {
            allResultItems.push({ fileBytes, identitas, kode, jenisKegiatan, tglFull, prefixPeriode, formatBd });
          }
        }
      }
    }

    if (cancelledRef.current) {
      setProcessing(false);
      setProgress({ current: 0, total: 0 });
      return;
    }

    // Simpan daftar file error untuk fitur retry
    setErrorFileNames(erroredFiles);

    // SO ER grouping
    const erGroups = {};
    for (const item of soErAssets) {
      const key = `${item.erType}|${item.loc}`;
      if (!erGroups[key]) erGroups[key] = [];
      erGroups[key].push(item);
    }
    for (const items of Object.values(erGroups)) {
      items.sort((a, b) => a.firstOtb - b.firstOtb);
      for (const item of items) {
        let identitas;
        if (item.hasOtbNumbers) {
          const rangeStr = item.otbMin !== item.otbMax ? `${item.otbMin}-${item.otbMax}` : String(item.otbMin);
          identitas = `${item.kategori} OTB ${rangeStr} ${item.erType} ${item.loc}`.replace(/\s+/g, ' ').trim();
        } else {
          identitas = `${item.kategori} OTB ${item.erType} ${item.loc}`.replace(/\s+/g, ' ').trim();
        }
        allResultItems.push({ fileBytes: item.fileBytes, identitas, kode: item.kode, jenisKegiatan: item.jenisKegiatan, tglFull: item.tglFull, prefixPeriode: item.prefixPeriode, formatBd: item.formatBd });
      }
    }

    // SO Bulanan grouping
    const bulananGroups = {};
    for (const item of soBulananAssets) {
      if (!bulananGroups[item.loc]) bulananGroups[item.loc] = [];
      bulananGroups[item.loc].push(item);
    }
    for (const items of Object.values(bulananGroups)) {
      items.sort((a, b) => a.seqNum - b.seqNum);
      items.forEach((item, idx) => {
        const suffix = idx > 0 ? ` (${idx + 1})` : '';
        const identitas = `${item.kategori} ${item.loc}${suffix}`.replace(/\s+/g, ' ').trim();
        allResultItems.push({ fileBytes: item.fileBytes, identitas, kode: item.kode, jenisKegiatan: item.jenisKegiatan, tglFull: item.tglFull, prefixPeriode: item.prefixPeriode, formatBd: item.formatBd });
      });
    }

    // Build filenames + dedup
    const uniqueNames = new Set();
    const finalNames = [];
    for (const item of allResultItems) {
      let newName = buildFilename(item.prefixPeriode, item.kode, item.jenisKegiatan, item.identitas, item.tglFull, item.formatBd);
      newName = newName.replace(/[<>:"\/\\|?*]/g, '_');
      if (!uniqueNames.has(newName)) {
        uniqueNames.add(newName);
        finalNames.push({ data: item.fileBytes, name: newName });
      } else {
        errorList.push(`WARNING|?|Duplikat: ${newName}`);
      }
    }

    setProgress({ current: targetFiles.length, total: targetFiles.length });
    setResults(finalNames);
    setErrors(errorList);
    if (erroredFiles.length > 0) {
      addLog('info', `Selesai: ${finalNames.length} berhasil, ${erroredFiles.length} error (bisa di-retry).`);
    } else {
      addLog('info', `Selesai deteksi: ${finalNames.length} file siap disimpan.`);
    }
    setProcessing(false);
    setPaused(false);
    pausedRef.current = false;
  }, [files, jenisKegiatan, instansi, addLog]);

  // Simpan versi terbaru handleProcess ke ref setiap render
  // Ini menghindari stale closure di handleRetryErrors
  useEffect(() => { processRef.current = handleProcess; });

  // Retry hanya file yang error — pakai processRef agar tidak stale
  const handleRetryErrors = useCallback(() => {
    if (!errorFileNames.length) return;
    addLog('info', `Retry ${errorFileNames.length} file error...`);
    processRef.current(errorFileNames);
  }, [errorFileNames, addLog]);

  const handleCopyLogs = useCallback(() => {
    if (!logs.length) return;
    const text = logs.map(l => {
      const time = new Date(l.ts).toLocaleTimeString();
      return `[${time}] [${l.type.toUpperCase()}] ${l.msg}`;
    }).join('\n');
    navigator.clipboard.writeText(text);
    setMessage({ type: 'success', text: 'Log berhasil disalin ke clipboard.' });
  }, [logs]);

  const handleExportLogs = useCallback(() => {
    if (!logs.length) return;
    const text = logs.map(l => {
      const time = new Date(l.ts).toLocaleTimeString();
      return `[${time}] [${l.type.toUpperCase()}] ${l.msg}`;
    }).join('\n');
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `SintelisUtility_Log_${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [logs]);

  const handleSave = useCallback(async () => {
    if (!results.length) return;
    setProcessing(true);
    if (dirHandle) {
      let savedCount = 0;
      try {
        for (const f of results) {
          await writeFileToDir(dirHandle, f.name, f.data);
          savedCount++;
        }
        addLog('success', `${savedCount} file tersimpan ke "${dirHandle.name}"`);
        setMessage({ type: 'success', text: `${savedCount} file tersimpan ke "${dirHandle.name}"` });
      } catch (err) {
        addLog('error', `Gagal tulis folder: ${err.message}`);
        setMessage({ type: 'error', text: `Gagal tulis folder: ${err.message}` });
      }
    } else {
      const blob = await createZipBlob(results);
      triggerDownload(blob, 'Hasil_Rename.zip');
      addLog('success', `ZIP diunduh (${results.length} file)`);
      setMessage({ type: 'success', text: `${results.length} file dalam ZIP diunduh.` });
    }
    setProcessing(false);
  }, [results, dirHandle, addLog]);

  const handleExportExcel = useCallback(() => {
    if (!results.length) return;
    const wsData = [['No', 'Nama File Baru']];
    results.forEach((r, i) => wsData.push([i + 1, r.name]));
    const ws = XLSX.utils.aoa_to_sheet(wsData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Hasil Rename');
    XLSX.writeFile(wb, `Hasil_Rename_${new Date().toISOString().slice(0, 10)}.xlsx`);
    addLog('success', `Excel diekspor (${results.length} file)`);
    setMessage({ type: 'success', text: 'Excel berhasil diekspor.' });
  }, [results, addLog]);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Sintelis Utility</h1>
        <p>Renamer file — diproses langsung di browser Anda</p>
      </header>

      <div className="main-content">
        {/* --------- LEFT PANEL --------- */}
        <div className="left-panel"
          onDragOver={e => { e.preventDefault(); }}
          onDrop={e => { e.preventDefault(); handleDrop(e); }}
        >
          <div className="card">
            <div className="card-title">Upload & Konfigurasi</div>

            <div className="select-group">
              <label>
                <span>Jenis Kegiatan</span>
                <select value={jenisKegiatan} onChange={e => setJenisKegiatan(e.target.value)}>
                  <option>Perawatan</option>
                  <option>Pemeriksaan</option>
                </select>
              </label>
              <label>
                <span>Instansi</span>
                <select value={instansi} onChange={e => setInstansi(e.target.value)}>
                  <option value="BTP JAK">BTP JAK</option>
                  <option value="BTP BD">BTP BD {formatBd ? '— KHUSUS SINTEL BOO' : ''}</option>
                </select>
              </label>
            </div>

            {formatBd && (
              <div className="message info">BTP BD KHUSUS SINTEL BOO</div>
            )}

            <div
              className="dropzone"
              onClick={() => inputRef.current?.click()}
              onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add('active'); }}
              onDragLeave={e => e.currentTarget.classList.remove('active')}
              onDrop={e => { e.currentTarget.classList.remove('active'); handleDrop(e); }}
            >
              <div className="dropzone-icon">📄</div>
              <div className="dropzone-text">
                <strong>Klik untuk pilih file</strong> atau drag & drop file PDF di sini
              </div>
              <input ref={inputRef} type="file" multiple accept=".pdf" style={{ display: 'none' }} onChange={handleFileSelect} />
            </div>

            {files.length > 0 && (
              <div className="file-list">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{files.length} file dipilih</span>
                  <button className="btn btn-secondary" style={{ padding: '0.3rem 0.7rem', fontSize: '0.78rem' }}
                    onClick={() => { setFiles([]); setResults([]); setErrors([]); setMessage(null); setLogs([]); }}>
                    Hapus semua
                  </button>
                </div>
                {files.map(f => (
                  <div key={f.name} className="file-item">
                    <span className="file-status pending" />
                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</span>
                    <button className="btn btn-secondary" style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem', border: 'none' }}
                      onClick={() => removeFile(f.name)}>✕</button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {message && !processing && <div className={`message ${message.type}`}>{message.text}</div>}
        </div>

        {/* --------- RIGHT PANEL: ACTIONS + SPLIT (Hasil/Error | Log) --------- */}
        <div className="right-panel">
          <div className="card actions-card">
            {processing && (
              <div className="progress-bar-wrapper" style={{ marginBottom: '0.6rem' }}>
                <div className="progress-bar-fill" style={{ width: `${(progress.current / progress.total) * 100}%` }} />
              </div>
            )}
            <div className="actions-row">
              <button className="btn btn-primary" disabled={!files.length || processing} onClick={() => handleProcess()}>
                {processing ? 'Memproses...' : 'Proses File'}
              </button>
              {processing && !paused && (
                <button className="btn btn-secondary" onClick={handlePause}>
                  ⏸ Pause
                </button>
              )}
              {processing && paused && (
                <button className="btn btn-primary" onClick={handleResume}>
                  ▶ Lanjutkan
                </button>
              )}
              {processing && (
                <button className="btn btn-danger" onClick={handleCancel}>
                  ✕ Batal
                </button>
              )}
              <button className="btn btn-secondary" onClick={handlePickDir}>
                Pilih Folder Tujuan
              </button>
              {dirHandle && (
                <span style={{ fontSize: '0.78rem', color: 'var(--accent)', alignSelf: 'center' }}>
                  {dirHandle.name}
                </span>
              )}
            </div>
            {results.length > 0 && (
              <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <button className="btn btn-primary" onClick={handleSave}>
                  Simpan {results.length} File
                </button>
                <button className="btn btn-secondary" onClick={handleExportExcel}>
                  📊 Ekspor Excel
                </button>
                {!processing && errorFileNames.length > 0 && (
                  <button className="btn btn-danger" onClick={handleRetryErrors}>
                    🔄 Proses Ulang Error ({errorFileNames.length} file)
                  </button>
                )}
              </div>
            )}
          </div>

          {/* --------- Split View: Hasil/Error | Log --------- */}
          <div className="split-view">
            {/* Split Left: Hasil / Error (tabbed) */}
            <div className="split-left">
              <div className="tab-bar">
                <button
                  className={`tab-btn${activeTab === 'hasil' ? ' active' : ''}`}
                  onClick={() => setActiveTab('hasil')}
                >
                  Hasil{results.length > 0 && <span className="tab-badge">{results.length}</span>}
                </button>
                <button
                  className={`tab-btn${activeTab === 'error' ? ' active' : ''}`}
                  onClick={() => setActiveTab('error')}
                >
                  Error{errors.length > 0 && <span className="tab-badge" style={{ background: 'rgba(255,94,125,0.15)', color: 'var(--danger)' }}>{errors.length}</span>}
                </button>
              </div>
              <div className="split-lists" key={visibilityKey}>
                {activeTab === 'hasil' && (
                  <>
                    {results.length === 0 && (
                      <div className="file-item" style={{ justifyContent: 'center' }}>Belum ada hasil</div>
                    )}
                    {results.map((r, i) => (
                      <div key={i} className="file-item success">
                        <span className="file-status done" />
                        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.name}</span>
                      </div>
                    ))}
                  </>
                )}
                {activeTab === 'error' && (
                  <>
                    {errors.length === 0 && (
                      <div className="file-item" style={{ justifyContent: 'center' }}>Tidak ada error</div>
                    )}
                    {errors.map((e, i) => {
                      const parts = e.split('|');
                      const srcFile = parts[1] || '';
                      const msg = parts[2] || e;
                      return (
                        <div key={i} className="file-item error">
                          <span className="file-status fail" />
                          <span style={{ flex: 1, fontSize: '0.72rem', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            <strong>{srcFile}</strong>: {msg}
                          </span>
                        </div>
                      );
                    })}
                  </>
                )}
              </div>
            </div>

            {/* Split Right: Log */}
            <div className="split-right">
              <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span>Log {logs.length > 0 && <span style={{ fontWeight: 400, textTransform: 'none' }}>({logs.length})</span>}</span>
                {logs.length > 0 && (
                  <div style={{ display: 'flex', gap: '0.4rem' }}>
                    <button className="btn btn-secondary" style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem' }} onClick={handleCopyLogs}>Salin</button>
                    <button className="btn btn-secondary" style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem' }} onClick={handleExportLogs}>Ekspor TXT</button>
                  </div>
                )}
              </div>
              <div className="log-panel" style={{ border: '1px solid var(--border-color)', borderRadius: '6px', padding: '0.4rem', background: 'var(--bg-secondary)' }}>
                {logs.length === 0 && (
                  <div className="log-item" style={{ justifyContent: 'center', color: 'var(--text-secondary)', background: 'none' }}>
                    Log akan muncul saat proses berjalan
                  </div>
                )}
                {logs.map((l, i) => (
                  <div key={i} className={`log-item ${l.type === 'success' ? 'success' : l.type === 'error' ? 'error' : ''}`}>
                    <span className={`file-status ${l.type === 'success' ? 'done' : l.type === 'error' ? 'fail' : 'processing'}`} />
                    <span style={{ flex: 1 }}>{l.msg}</span>
                  </div>
                ))}
                <div ref={logEndRef} />
              </div>
            </div>
          </div>
        </div>
      </div>

      <footer className="app-footer">
        Sintelis Utility — Client-Side (PDF.js + Tesseract.js)
      </footer>
    </div>
  );
}
