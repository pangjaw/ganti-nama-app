import { useState, useEffect, useRef, useCallback } from 'react';

export default function TimemarkModule() {
  const [sourceDir, setSourceDir] = useState('');
  const [targetDir, setTargetDir] = useState('');
  const [exportDir, setExportDir] = useState('');
  const [mergedDir, setMergedDir] = useState('');

  const [selectedSteps, setSelectedSteps] = useState(['1', '2', '3', '4', '5']);
  const [pipelineState, setPipelineState] = useState({
    running: false,
    cancelled: false,
    current_step: 0,
    step_name: '',
    progress: 0,
    logs: [],
    step_statuses: {
      step1: 'pending',
      step2: 'pending',
      step3: 'pending',
      step4: 'pending',
      step5: 'pending'
    },
    error: null
  });

  const [pdfCounts, setPdfCounts] = useState({ source: null, target: null });
  const logEndRef = useRef(null);

  // Poll status when running
  useEffect(() => {
    let interval = null;
    const checkStatus = async () => {
      try {
        const res = await fetch('/api/timemark/status');
        if (res.ok) {
          const data = await res.json();
          setPipelineState(data);
        }
      } catch (err) {
        console.error('Error polling timemark status:', err);
      }
    };

    if (pipelineState.running) {
      interval = setInterval(checkStatus, 1000);
    } else {
      checkStatus();
    }
    return () => { if (interval) clearInterval(interval); };
  }, [pipelineState.running]);

  // Auto-scroll log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [pipelineState.logs]);

  // Folder picking helper
  const handlePickFolder = async (setter, type) => {
    try {
      const res = await fetch('/api/select-folder', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.path) {
          setter(data.path);
          // Check pdf count if source or target
          if (type === 'source' || type === 'target') {
            const listRes = await fetch(`/api/list-folder-pdfs?folder=${encodeURIComponent(data.path)}`);
            if (listRes.ok) {
              const listData = await listRes.json();
              setPdfCounts(prev => ({
                ...prev,
                [type]: listData.files ? listData.files.length : 0
              }));
            }
          }
        }
      }
    } catch (err) {
      alert('Gagal membuka dialog folder: ' + err.message);
    }
  };

  const handleToggleStep = (stepId) => {
    setSelectedSteps(prev =>
      prev.includes(stepId) ? prev.filter(s => s !== stepId) : [...prev, stepId].sort()
    );
  };

  const handleStartPipeline = async () => {
    if (!sourceDir) {
      alert('Silakan pilih Folder Sumber PDF 2026 terlebih dahulu!');
      return;
    }
    if (!targetDir) {
      alert('Silakan pilih Folder Target PDF 2025 terlebih dahulu!');
      return;
    }
    if (selectedSteps.length === 0) {
      alert('Pilih minimal satu tahap untuk dijalankan!');
      return;
    }

    try {
      const res = await fetch('/api/timemark/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sourceDir,
          targetDir,
          exportDir: exportDir || undefined,
          mergedDir: mergedDir || undefined,
          steps: selectedSteps
        })
      });
      const data = await res.json();
      if (!data.ok) {
        alert('Gagal memulai pipeline: ' + (data.error || 'Terjadi kesalahan'));
      } else {
        setPipelineState(prev => ({ ...prev, running: true, error: null, logs: [] }));
      }
    } catch (err) {
      alert('Gagal menghubungi server: ' + err.message);
    }
  };

  const handleCancelPipeline = async () => {
    if (!confirm('Apakah Anda yakin ingin membatalkan proses pipeline?')) return;
    try {
      await fetch('/api/timemark/cancel', { method: 'POST' });
    } catch (err) {
      console.error('Cancel error:', err);
    }
  };

  const stepLabels = [
    { id: '1', key: 'step1', name: 'Step 1: Ekstraksi Foto PDF 2026' },
    { id: '2', key: 'step2', name: 'Step 2: Ekstraksi Tanggal PDF Target 2025' },
    { id: '3', key: 'step3', name: 'Step 3: Penjadwalan Tim & Alokasi Waktu' },
    { id: '4', key: 'step4', name: 'Step 4: Edit Watermark Timemark Foto' },
    { id: '5', key: 'step5', name: 'Step 5: Penggabungan PDF Final A4' }
  ];

  return (
    <div style={{ display: 'flex', gap: '1.25rem', height: '100%', overflow: 'hidden' }}>
      {/* Kolom Kiri: Form Konfigurasi Folder & Step */}
      <div style={{ flex: '0 0 480px', display: 'flex', flexDirection: 'column', gap: '1rem', overflowY: 'auto', paddingRight: '0.5rem' }}>
        
        {/* Card Pemilihan Folder */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '10px', padding: '1.25rem' }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>📁</span> Pemilihan Folder Fleksibel
          </h3>

          {/* 1. Sumber PDF 2026 */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
              <span>Folder PDF Sumber 2026 (Mentah)*</span>
              {pdfCounts.source !== null && (
                <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{pdfCounts.source} PDF terdeteksi</span>
              )}
            </label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                placeholder="Pilih folder sumber PDF 2026..."
                value={sourceDir}
                onChange={e => setSourceDir(e.target.value)}
                style={{ flex: 1, padding: '0.5rem 0.75rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              />
              <button
                onClick={() => handlePickFolder(setSourceDir, 'source')}
                style={{ padding: '0.5rem 0.85rem', background: 'var(--accent-dim)', color: 'var(--accent)', border: '1px solid var(--accent)', borderRadius: '6px', cursor: 'pointer', fontWeight: 500, whiteSpace: 'nowrap' }}
              >
                Pilih...
              </button>
            </div>
          </div>

          {/* 2. Target PDF 2025 */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
              <span>Folder PDF Target 2025 (Acuan)*</span>
              {pdfCounts.target !== null && (
                <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{pdfCounts.target} PDF terdeteksi</span>
              )}
            </label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                placeholder="Pilih folder target PDF 2025..."
                value={targetDir}
                onChange={e => setTargetDir(e.target.value)}
                style={{ flex: 1, padding: '0.5rem 0.75rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              />
              <button
                onClick={() => handlePickFolder(setTargetDir, 'target')}
                style={{ padding: '0.5rem 0.85rem', background: 'var(--accent-dim)', color: 'var(--accent)', border: '1px solid var(--accent)', borderRadius: '6px', cursor: 'pointer', fontWeight: 500, whiteSpace: 'nowrap' }}
              >
                Pilih...
              </button>
            </div>
          </div>

          {/* 3. Output Export Foto (Opsional) */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
              Folder Foto Ekstraksi (Opsional / Default Dokumen)
            </label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                placeholder="Default: Dokumen/Sintelis/03_photos_export"
                value={exportDir}
                onChange={e => setExportDir(e.target.value)}
                style={{ flex: 1, padding: '0.5rem 0.75rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              />
              <button
                onClick={() => handlePickFolder(setExportDir, 'export')}
                style={{ padding: '0.5rem 0.85rem', background: 'var(--bg-card-hover)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', cursor: 'pointer', whiteSpace: 'nowrap' }}
              >
                Pilih...
              </button>
            </div>
          </div>

          {/* 4. Output Merged PDF (Opsional) */}
          <div style={{ marginBottom: '0.25rem' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
              Folder PDF Gabungan Akhir (Opsional / Default Dokumen)
            </label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                placeholder="Default: Dokumen/Sintelis/05_pdf_merged"
                value={mergedDir}
                onChange={e => setMergedDir(e.target.value)}
                style={{ flex: 1, padding: '0.5rem 0.75rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              />
              <button
                onClick={() => handlePickFolder(setMergedDir, 'merged')}
                style={{ padding: '0.5rem 0.85rem', background: 'var(--bg-card-hover)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', cursor: 'pointer', whiteSpace: 'nowrap' }}
              >
                Pilih...
              </button>
            </div>
          </div>
        </div>

        {/* Card Pilihan Tahap Pipeline */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '10px', padding: '1.25rem' }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
            ⚙️ Tahapan Pemrosesan
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {stepLabels.map(s => (
              <label key={s.id} style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', fontSize: '0.88rem', color: 'var(--text-primary)', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={selectedSteps.includes(s.id)}
                  onChange={() => handleToggleStep(s.id)}
                  disabled={pipelineState.running}
                  style={{ width: '16px', height: '16px', accentColor: 'var(--accent)' }}
                />
                <span>{s.name}</span>
              </label>
            ))}
          </div>

          {/* Tombol Aksi */}
          <div style={{ marginTop: '1.25rem', display: 'flex', gap: '0.75rem' }}>
            {!pipelineState.running ? (
              <button
                onClick={handleStartPipeline}
                style={{ flex: 1, padding: '0.75rem', background: 'var(--accent)', color: '#0b0d15', border: 'none', borderRadius: '8px', fontWeight: 700, fontSize: '0.95rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
              >
                <span>🚀</span> Mulai Pemrosesan
              </button>
            ) : (
              <button
                onClick={handleCancelPipeline}
                style={{ flex: 1, padding: '0.75rem', background: 'var(--danger)', color: '#ffffff', border: 'none', borderRadius: '8px', fontWeight: 700, fontSize: '0.95rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
              >
                <span>🛑</span> Batalkan Proses
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Kolom Kanan: Status, Progress Bar, & Live Terminal Log */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem', minWidth: 0, height: '100%' }}>
        
        {/* Status & Progress Bar Card */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '10px', padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <span style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-primary)' }}>
              Status: {pipelineState.running ? pipelineState.step_name || 'Memproses...' : (pipelineState.progress === 100 ? 'Selesai' : 'Siap')}
            </span>
            <span style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--accent)' }}>
              {pipelineState.progress}%
            </span>
          </div>

          {/* Progress Bar Container */}
          <div style={{ width: '100%', height: '8px', background: 'var(--bg-secondary)', borderRadius: '4px', overflow: 'hidden', marginBottom: '1rem' }}>
            <div style={{ width: `${pipelineState.progress}%`, height: '100%', background: 'linear-gradient(90deg, var(--accent), #38ef7d)', transition: 'width 0.3s ease' }} />
          </div>

          {/* Badges per Step */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {stepLabels.map(s => {
              const st = pipelineState.step_statuses[s.key] || 'pending';
              let badgeColor = '#6c757d';
              let badgeText = 'Menunggu';
              if (st === 'running') { badgeColor = '#00bcd4'; badgeText = 'Berjalan...'; }
              if (st === 'success') { badgeColor = '#28a745'; badgeText = 'Sukses'; }
              if (st === 'error') { badgeColor = '#dc3545'; badgeText = 'Gagal'; }
              if (st === 'cancelled') { badgeColor = '#ffc107'; badgeText = 'Dibatalkan'; }

              return (
                <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.25rem 0.65rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', fontSize: '0.78rem' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: badgeColor }} />
                  <span style={{ color: 'var(--text-primary)' }}>Step {s.id}</span>
                  <span style={{ color: badgeColor, fontWeight: 600 }}>({badgeText})</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Live Terminal Log */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#080a0f', border: '1px solid var(--border-color)', borderRadius: '10px', overflow: 'hidden' }}>
          <div style={{ padding: '0.65rem 1rem', background: 'var(--bg-card)', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              🖥️ Terminal Log Real-time ({pipelineState.logs.length} baris)
            </span>
          </div>

          <div style={{ flex: 1, padding: '0.85rem', overflowY: 'auto', fontFamily: 'Consolas, Monaco, monospace', fontSize: '0.82rem', lineHeight: 1.5 }}>
            {pipelineState.logs.length === 0 ? (
              <div style={{ color: '#4a5568', fontStyle: 'italic' }}>
                Log aktivitas pipeline akan muncul di sini secara real-time saat pemrosesan dimulai...
              </div>
            ) : (
              pipelineState.logs.map((item, idx) => {
                let color = '#a0aec0';
                if (item.type === 'success') color = '#48bb78';
                if (item.type === 'error') color = '#f56565';
                if (item.type === 'warn') color = '#ecc94b';

                return (
                  <div key={idx} style={{ color, wordBreak: 'break-all' }}>
                    <span style={{ color: '#4a5568', marginRight: '0.5rem' }}>[{item.ts}]</span>
                    {item.msg}
                  </div>
                );
              })
            )}
            <div ref={logEndRef} />
          </div>
        </div>

      </div>
    </div>
  );
}
