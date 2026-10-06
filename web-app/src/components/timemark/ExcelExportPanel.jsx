import { useState } from 'react';

export default function ExcelExportPanel({ targetDir, exportDir }) {
  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth() + 1;

  const [tabloYear, setTabloYear] = useState(currentYear);
  const [tabloMonth, setTabloMonth] = useState(currentMonth);
  const [tabloGenerating, setTabloGenerating] = useState(false);

  const [dinasanYear, setDinasanYear] = useState(currentYear);
  const [dinasanMonth, setDinasanMonth] = useState(currentMonth);
  const [withPersonnel, setWithPersonnel] = useState(true);
  const [dinasanGenerating, setDinasanGenerating] = useState(false);

  const [historyFiles, setHistoryFiles] = useState([]);
  const [feedback, setFeedback] = useState(null);

  const months = [
    { num: 1, name: 'Januari' }, { num: 2, name: 'Februari' }, { num: 3, name: 'Maret' },
    { num: 4, name: 'April' }, { num: 5, name: 'Mei' }, { num: 6, name: 'Juni' },
    { num: 7, name: 'Juli' }, { num: 8, name: 'Agustus' }, { num: 9, name: 'September' },
    { num: 10, name: 'Oktober' }, { num: 11, name: 'November' }, { num: 12, name: 'Desember' }
  ];

  // 1. Ekspor Tablo Checklist
  const handleExportTablo = async () => {
    if (!targetDir && !exportDir) {
      alert('Silakan tentukan Folder Target PDF atau Folder Ekspor terlebih dahulu!');
      return;
    }
    setTabloGenerating(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/timemark/export-tablo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          folder: targetDir,
          exportDir,
          year: tabloYear,
          month: tabloMonth
        })
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        setFeedback({ type: 'success', text: `✓ Berkas Tablo Checklist berhasil dibuat: ${data.filePath}` });
        if (data.filePath) {
          setHistoryFiles(prev => [data.filePath, ...prev.filter(f => f !== data.filePath)]);
        }
      } else {
        setFeedback({ type: 'error', text: 'Gagal membuat Tablo: ' + (data.error || 'Terjadi kesalahan') });
      }
    } catch (err) {
      setFeedback({ type: 'error', text: 'Galat: ' + err.message });
    } finally {
      setTabloGenerating(false);
    }
  };

  // 2. Ekspor Jadwal Dinasan
  const handleExportDinasan = async () => {
    setDinasanGenerating(true);
    setFeedback(null);
    try {
      const res = await fetch('/api/timemark/export-dinasan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          folder: targetDir,
          exportDir,
          year: dinasanYear,
          month: dinasanMonth,
          withPersonnel
        })
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        setFeedback({ type: 'success', text: `✓ Berkas Jadwal Dinasan berhasil dibuat: ${data.filePath}` });
        if (data.filePath) {
          setHistoryFiles(prev => [data.filePath, ...prev.filter(f => f !== data.filePath)]);
        }
      } else {
        setFeedback({ type: 'error', text: 'Gagal membuat Jadwal Dinasan: ' + (data.error || 'Terjadi kesalahan') });
      }
    } catch (err) {
      setFeedback({ type: 'error', text: 'Galat: ' + err.message });
    } finally {
      setDinasanGenerating(false);
    }
  };

  // Open file in Windows Explorer
  const handleOpenFile = async (filePath) => {
    try {
      await fetch('/api/timemark/open-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filePath })
      });
    } catch (err) {
      alert('Gagal membuka berkas: ' + err.message);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', height: '100%', overflowY: 'auto', paddingRight: '0.5rem' }}>
      
      {/* Header Info */}
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1rem 1.25rem' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>📊</span> Ekspor Dokumen Resmi Excel
        </h3>
        <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>
          Mencetak formulir KAI resmi Tablo Checklist (Form STE-RECORD-13.4.01) dan Jadwal Dinasan yang otomatis sinkron dengan profil pegawai aktif.
        </p>
      </div>

      {feedback && (
        <div style={{
          padding: '0.75rem 1rem',
          borderRadius: '6px',
          fontSize: '0.85rem',
          background: feedback.type === 'success' ? '#14532d' : '#7f1d1d',
          color: feedback.type === 'success' ? '#86efac' : '#fca5a5',
          border: `1px solid ${feedback.type === 'success' ? '#22c55e' : '#ef4444'}`
        }}>
          {feedback.text}
        </div>
      )}

      {/* Grid: 2 Export Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
        
        {/* Card 1: Tablo Checklist */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '1.25rem' }}>📑</span>
              <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                Tablo Checklist & Perawatan Berkala
              </h4>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem', lineHeight: 1.4 }}>
              Formulir resmi No. STE-RECORD-13.4.01 A4 Landscape tepat 1 halaman, lengkap dengan tanda tangan KUPT Resor dan KAUR Preventif.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>Bulan</label>
                <select
                  value={tabloMonth}
                  onChange={e => setTabloMonth(Number(e.target.value))}
                  style={{ width: '100%', padding: '0.5rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.85rem' }}
                >
                  {months.map(m => (
                    <option key={m.num} value={m.num}>{m.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>Tahun</label>
                <input
                  type="number"
                  value={tabloYear}
                  onChange={e => setTabloYear(Number(e.target.value))}
                  style={{ width: '100%', padding: '0.5rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.85rem' }}
                />
              </div>
            </div>
          </div>

          <button
            onClick={handleExportTablo}
            disabled={tabloGenerating}
            style={{ width: '100%', padding: '0.65rem', background: 'var(--accent)', color: '#ffffff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '0.875rem' }}
          >
            {tabloGenerating ? 'Membuat Tablo Excel...' : '⚡ Buat Tablo Excel'}
          </button>
        </div>

        {/* Card 2: Jadwal Dinasan Pegawai */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '1.25rem' }}>📅</span>
              <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                Jadwal Dinasan Pegawai
              </h4>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem', lineHeight: 1.4 }}>
              Matriks dinasan harian pegawai UPT Resor Sintel 1.21 Bogor format Portrait 1 halaman lebar dengan rekap dinas (S, M, L, P, CT).
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.85rem' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>Bulan</label>
                <select
                  value={dinasanMonth}
                  onChange={e => setDinasanMonth(Number(e.target.value))}
                  style={{ width: '100%', padding: '0.5rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.85rem' }}
                >
                  {months.map(m => (
                    <option key={m.num} value={m.num}>{m.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>Tahun</label>
                <input
                  type="number"
                  value={dinasanYear}
                  onChange={e => setDinasanYear(Number(e.target.value))}
                  style={{ width: '100%', padding: '0.5rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.85rem' }}
                />
              </div>
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)', cursor: 'pointer', marginBottom: '1rem' }}>
              <input
                type="checkbox"
                checked={withPersonnel}
                onChange={e => setWithPersonnel(e.target.checked)}
              />
              <span>Sertakan Kolom Personil Tim Dinasan Lengkap</span>
            </label>
          </div>

          <button
            onClick={handleExportDinasan}
            disabled={dinasanGenerating}
            style={{ width: '100%', padding: '0.65rem', background: 'var(--accent)', color: '#ffffff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '0.875rem' }}
          >
            {dinasanGenerating ? 'Membuat Jadwal Dinasan...' : '⚡ Buat Jadwal Dinasan Excel'}
          </button>
        </div>

      </div>

      {/* Riwayat Berkas yang Baru Dibuat */}
      {historyFiles.length > 0 && (
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1.25rem' }}>
          <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
            📁 Berkas Excel yang Baru Dihasilkan:
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {historyFiles.map((file, idx) => (
              <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '0.6rem 0.85rem' }}>
                <span style={{ fontSize: '0.825rem', color: 'var(--text-primary)', fontFamily: 'monospace' }}>{file}</span>
                <button
                  onClick={() => handleOpenFile(file)}
                  style={{ padding: '0.35rem 0.75rem', background: 'var(--accent-dim)', color: 'var(--accent)', border: '1px solid var(--accent)', borderRadius: '5px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}
                >
                  Buka Berkas
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
