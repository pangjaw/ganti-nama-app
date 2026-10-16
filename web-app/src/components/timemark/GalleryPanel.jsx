import { useState, useEffect, useMemo, useRef } from 'react';

// =============================================================================
// Helper Kalkulasi Tanggal Otomatis (0%, 50%, 100%)
// =============================================================================
function helperCalculateDate(baseDate, photoStem) {
  let cleanDate = (baseDate || '').trim();
  const m = cleanDate.match(/^(.*?\d{4})\s+(\d{2}):(\d{2})$/);
  if (!m) return cleanDate;

  const [_, datePart, hh, mm] = m;
  let totalMin = parseInt(hh, 10) * 60 + parseInt(mm, 10);
  let pct = 0;
  if (photoStem === '50') pct = 50;
  else if (photoStem === '100') pct = 100;
  const duration = 45;
  totalMin += Math.round((pct * duration) / 100);

  const newHH = String(Math.floor(totalMin / 60) % 24).padStart(2, '0');
  const newMM = String(totalMin % 60).padStart(2, '0');
  return `${datePart} ${newHH}:${newMM}`;
}

// =============================================================================
// Modal Editor Timemark Interaktif & Komparasi Berdampingan
// =============================================================================
function TimemarkEditorModal({
  isOpen,
  onClose,
  asset,
  photo,
  exportDir,
  onSaved
}) {
  if (!isOpen || !asset || !photo) return null;

  const rawRelPath = `${asset.relDir}/${photo.name}`;
  const [yPos, setYPos] = useState(photo.meta?.yPos || 220);
  const [xPos, setXPos] = useState(photo.meta?.xPos || 14);
  const [dateText, setDateText] = useState(photo.meta?.dateText || asset.dateText || '');
  const [applyToFolder, setApplyToFolder] = useState(true);
  const [saving, setSaving] = useState(false);
  const [remerging, setRemerging] = useState(false);
  const [msg, setMsg] = useState(null);

  // Quick Time Adjuster Helper
  const adjustMinutes = (deltaMin) => {
    const m = (dateText || '').match(/^(.*?\d{4})\s+(\d{2}):(\d{2})$/);
    if (!m) return;
    const [_, datePart, hh, mm] = m;
    let totalMin = parseInt(hh, 10) * 60 + parseInt(mm, 10) + deltaMin;
    if (totalMin < 0) totalMin += 24 * 60;
    const newHH = String(Math.floor(totalMin / 60) % 24).padStart(2, '0');
    const newMM = String(totalMin % 60).padStart(2, '0');
    setDateText(`${datePart} ${newHH}:${newMM}`);
  };

  const handleSave = async (andRemerge = false) => {
    if (!dateText.trim()) {
      alert('Teks tanggal & waktu tidak boleh kosong!');
      return;
    }
    setSaving(true);
    setMsg(null);
    try {
      const res = await fetch('/api/timemark/manual-edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          baseExportDir: exportDir,
          rawRelPath,
          dateText: dateText.trim(),
          yPos: Number(yPos),
          xPos: Number(xPos),
          applyToFolder,
          timGroup: 'Tim_1'
        })
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        throw new Error(data.error || 'Gagal menyimpan timemark');
      }

      if (andRemerge) {
        setRemerging(true);
        const mergeRes = await fetch('/api/timemark/remerge-single', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            rawRelPath,
            baseExportDir: exportDir,
            pdfName: (asset.targetFiles && asset.targetFiles[0]) || undefined
          })
        });
        const mergeData = await mergeRes.json();
        if (!mergeRes.ok || !mergeData.ok) {
          throw new Error(mergeData.error || 'Gagal re-merge PDF target');
        }
        setMsg({
          type: 'success',
          text: `✓ Timemark disimpan dan PDF ${mergeData.pdfName} berhasil digabung ulang!`
        });
      } else {
        setMsg({
          type: 'success',
          text: '✓ Timemark berhasil diperbarui dan disimpan!'
        });
      }

      if (onSaved) onSaved();
    } catch (err) {
      setMsg({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
      setRemerging(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        background: 'rgba(0, 0, 0, 0.82)',
        backdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.25rem'
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '960px',
          maxHeight: '92vh',
          background: 'var(--bg-card, #131b2e)',
          border: '1px solid var(--border-color, #22304d)',
          borderRadius: '14px',
          boxShadow: '0 25px 60px rgba(0,0,0,0.5)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header Modal */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '1rem 1.5rem',
            borderBottom: '1px solid var(--border-color, #22304d)',
            background: 'rgba(0,0,0,0.2)'
          }}
        >
          <div>
            <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span>⚙️</span> Editor Timemark Manual: {asset.detail} ({photo.name})
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>
              {rawRelPath}
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-secondary)',
              fontSize: '1.25rem',
              cursor: 'pointer',
              padding: '0.25rem 0.5rem',
              borderRadius: '6px'
            }}
          >
            ✕
          </button>
        </div>

        {/* Body Modal */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', padding: '1.25rem 1.5rem', overflowY: 'auto' }}>
          
          {/* Side-by-Side Comparison Box */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            
            {/* Sisi Kiri: Foto Asli */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', background: '#090d16', padding: '0.75rem', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8' }}>📷 Foto Asli / Sebelum Edit</span>
                <span style={{ fontSize: '0.7rem', color: '#64748b' }}>Ekspor Mentah</span>
              </div>
              <div style={{ width: '100%', height: '240px', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', borderRadius: '6px', background: '#000000' }}>
                <img
                  src={photo.rawUrl}
                  alt="Foto Asli"
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                />
              </div>
            </div>

            {/* Sisi Kanan: Foto Hasil Timemark */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', background: '#090d16', padding: '0.75rem', borderRadius: '10px', border: '1px solid #10b981' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 800, color: '#34d399', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <span>✨</span> Foto Hasil Timemark (Aktif)
                </span>
                <span style={{ fontSize: '0.7rem', background: 'rgba(52, 211, 153, 0.15)', color: '#34d399', padding: '1px 6px', borderRadius: '4px', fontWeight: 600 }}>
                  Y-Offset: {yPos}px
                </span>
              </div>
              <div style={{ width: '100%', height: '240px', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', borderRadius: '6px', background: '#000000' }}>
                <img
                  src={photo.editedUrl || photo.rawUrl}
                  alt="Foto Hasil Timemark"
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                />
              </div>
            </div>

          </div>

          {/* Controls: Tanggal, Slider Y-Offset & Options */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', background: 'var(--bg-secondary)', padding: '1rem', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
            
            {/* Input Tanggal & Jam */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              <label style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                📅 Teks Tanggal & Jam Watermark:
              </label>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <input
                  type="text"
                  value={dateText}
                  onChange={e => setDateText(e.target.value)}
                  placeholder="Contoh: Sabtu, 08 Februari 2025 08:30"
                  style={{
                    flex: 1,
                    minWidth: '240px',
                    padding: '0.55rem 0.85rem',
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '6px',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                    fontWeight: 600
                  }}
                />
                <button
                  type="button"
                  onClick={() => adjustMinutes(-15)}
                  style={{ padding: '0.4rem 0.65rem', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}
                  title="Kurangi 15 Menit"
                >
                  -15m
                </button>
                <button
                  type="button"
                  onClick={() => adjustMinutes(15)}
                  style={{ padding: '0.4rem 0.65rem', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}
                  title="Tambah 15 Menit"
                >
                  +15m
                </button>
                <button
                  type="button"
                  onClick={() => adjustMinutes(30)}
                  style={{ padding: '0.4rem 0.65rem', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}
                  title="Tambah 30 Menit"
                >
                  +30m
                </button>
              </div>
            </div>

            {/* Slider Y-Offset Watermark (100 px - 280 px) */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  📏 Posisi Vertikal Watermark (Y-Offset):
                </label>
                <span style={{ fontSize: '0.8rem', fontWeight: 800, color: '#38bdf8', background: 'rgba(56, 189, 248, 0.15)', padding: '2px 8px', borderRadius: '4px' }}>
                  {yPos} px
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>100px (Atas)</span>
                <input
                  type="range"
                  min="100"
                  max="280"
                  step="1"
                  value={yPos}
                  onChange={e => setYPos(Number(e.target.value))}
                  style={{ flex: 1, accentColor: '#38bdf8', cursor: 'pointer' }}
                />
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>280px (Bawah)</span>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.2rem' }}>
                <button
                  type="button"
                  onClick={() => setYPos(220)}
                  style={{ padding: '0.25rem 0.5rem', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '4px', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.7rem' }}
                >
                  Standar (220px)
                </button>
                <button
                  type="button"
                  onClick={() => setYPos(prev => Math.max(100, prev - 10))}
                  style={{ padding: '0.25rem 0.5rem', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '4px', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.7rem' }}
                >
                  Naik (-10px)
                </button>
                <button
                  type="button"
                  onClick={() => setYPos(prev => Math.min(280, prev + 10))}
                  style={{ padding: '0.25rem 0.5rem', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '4px', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.7rem' }}
                >
                  Turun (+10px)
                </button>
              </div>
            </div>

            {/* Checkbox Apply to Siblings */}
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.8rem', color: 'var(--text-primary)', cursor: 'pointer', userSelect: 'none' }}>
              <input
                type="checkbox"
                checked={applyToFolder}
                onChange={e => setApplyToFolder(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: '#10b981', cursor: 'pointer' }}
              />
              <span>
                <strong>Terapkan ke seluruh foto aset ini (0%, 50%, 100%)</strong>
                <span style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                  Otomatis menghitung jeda waktu pelaksanaan: 0% waktu awal, 50% (+23m), 100% (+45m).
                </span>
              </span>
            </label>

          </div>

          {msg && (
            <div style={{
              padding: '0.65rem 0.95rem',
              borderRadius: '6px',
              fontSize: '0.8rem',
              background: msg.type === 'success' ? '#14532d' : '#7f1d1d',
              color: msg.type === 'success' ? '#86efac' : '#fca5a5',
              border: `1px solid ${msg.type === 'success' ? '#22c55e' : '#ef4444'}`
            }}>
              {msg.text}
            </div>
          )}

        </div>

        {/* Footer Modal Buttons */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '1rem 1.5rem',
            borderTop: '1px solid var(--border-color, #22304d)',
            background: 'rgba(0,0,0,0.2)',
            flexWrap: 'wrap',
            gap: '0.75rem'
          }}
        >
          <button
            type="button"
            onClick={onClose}
            disabled={saving || remerging}
            style={{
              padding: '0.55rem 1rem',
              background: 'var(--bg-secondary)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: 600
            }}
          >
            Tutup
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={() => handleSave(false)}
              disabled={saving || remerging}
              style={{
                padding: '0.55rem 1.25rem',
                background: '#10b981',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                boxShadow: '0 2px 10px rgba(16, 185, 129, 0.4)'
              }}
            >
              {saving && !remerging ? '⏳ Menyimpan...' : '💾 Simpan Timemark'}
            </button>

            <button
              type="button"
              onClick={() => handleSave(true)}
              disabled={saving || remerging}
              style={{
                padding: '0.55rem 1.25rem',
                background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: 800,
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                boxShadow: '0 2px 10px rgba(2, 132, 199, 0.4)'
              }}
              title="Simpan perubahan watermark dan langsung perbarui file PDF target terkait"
            >
              {remerging ? '⚡ Sedang Merge PDF...' : '⚡ Simpan & Merge PDF'}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

// =============================================================================
// Komponen Utama GalleryPanel
// =============================================================================
export default function GalleryPanel({ exportDir, onPickFolder }) {
  const [assets, setAssets] = useState([]);
  const [targetFiles, setTargetFiles] = useState([]);
  const [sourceFiles, setSourceFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Mode States (Sama Persis dengan Web App)
  const [pipelineMode, setPipelineMode] = useState('standard'); // 'standard' | 'time' | 'coord'
  const [viewMode, setViewMode] = useState('dual'); // 'dual' | 'edited' | 'raw'
  const [sourceTypeFilter, setSourceTypeFilter] = useState('all'); // 'timemark' | 'export' | 'all'

  // Filter States
  const [selectedFile, setSelectedFile] = useState('');
  const [selectedStation, setSelectedStation] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedStatus, setSelectedStatus] = useState(''); // '' | 'complete' | 'incomplete'
  const [searchQuery, setSearchQuery] = useState('');

  // Drag & Drop State
  const [dragOverRel, setDragOverRel] = useState(null);
  const [actionLoadingRel, setActionLoadingRel] = useState(null);

  // Zoom Preview Modal State
  const [zoomPhoto, setZoomPhoto] = useState(null); // { url, title }

  // Timemark Editor Modal State
  const [editingModal, setEditingModal] = useState(null); // { asset, photo }

  // Single Merge State per Asset Row
  const [mergingRel, setMergingRel] = useState(null);

  // Fetch photos and metadata from backend
  const fetchPhotos = async () => {
    if (!exportDir) return;
    setLoading(true);
    setFeedback(null);
    try {
      const res = await fetch(`/api/timemark/photos?folder=${encodeURIComponent(exportDir)}`);
      if (res.ok) {
        const data = await res.json();
        const loadedAssets = data.assets || [];
        setAssets(loadedAssets);
        setTargetFiles(data.targetFiles || []);
        setSourceFiles(data.sourceFiles || []);
      } else {
        setFeedback({ type: 'error', text: 'Gagal memuat galeri foto dari folder ekspor.' });
      }
    } catch (err) {
      setFeedback({ type: 'error', text: 'Koneksi gagal: ' + err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPhotos();
  }, [exportDir]);

  // Counts
  const editedCount = useMemo(() => assets.filter(a => a.hasEdited).length, [assets]);
  const exportCount = useMemo(() => assets.length, [assets]);

  // Unique lists for dropdowns
  const uniqueStations = useMemo(() => {
    const set = new Set();
    assets.forEach(a => { if (a.station) set.add(a.station); });
    return Array.from(set).sort();
  }, [assets]);

  const uniqueCategories = useMemo(() => {
    const set = new Set();
    assets.forEach(a => {
      const cat = a.category || a.asset_type;
      if (cat) set.add(cat);
    });
    return Array.from(set).sort();
  }, [assets]);

  // Combined File List
  const allFileOptions = useMemo(() => {
    const options = [];
    const seen = new Set();

    targetFiles.forEach(t => {
      if (t.file && !seen.has(t.file)) {
        seen.add(t.file);
        options.push({ value: t.file, label: `📄 ${t.file}`, category: t.category, btp: t.btp });
      }
    });

    sourceFiles.forEach(s => {
      if (s && !seen.has(s)) {
        seen.add(s);
        options.push({ value: s, label: `📥 ${s}` });
      }
    });

    return options.sort((a, b) => a.value.localeCompare(b.value));
  }, [targetFiles, sourceFiles]);

  // Filtered Assets
  const filteredAssets = useMemo(() => {
    return assets.filter(a => {
      // 0. Filter Tipe Sumber Foto (Hasil Timemark vs Ekspor Asli)
      if (sourceTypeFilter === 'timemark' && !a.hasEdited) return false;
      if (sourceTypeFilter === 'export' && a.hasEdited) return false;

      // 1. Filter File (Target PDF atau Source PDF)
      if (selectedFile) {
        const inTargets = (a.targetFiles || []).includes(selectedFile);
        const isSource = a.sourceFile === selectedFile;
        if (!inTargets && !isSource) return false;
      }

      // 2. Filter Stasiun / BTP
      if (selectedStation && a.station !== selectedStation) {
        return false;
      }

      // 3. Filter Kategori Aset
      const cat = a.category || a.asset_type;
      if (selectedCategory && cat !== selectedCategory) {
        return false;
      }

      // 4. Filter Status Kelengkapan Foto
      const photoCount = (a.photos || []).length;
      if (selectedStatus === 'complete' && photoCount < 3) return false;
      if (selectedStatus === 'incomplete' && photoCount >= 3) return false;

      // 5. Search Query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchStation = a.station && a.station.toLowerCase().includes(q);
        const matchCat = cat && cat.toLowerCase().includes(q);
        const matchDetail = a.detail && a.detail.toLowerCase().includes(q);
        if (!matchStation && !matchCat && !matchDetail) return false;
      }

      return true;
    });
  }, [assets, sourceTypeFilter, selectedFile, selectedStation, selectedCategory, selectedStatus, searchQuery]);

  const isFilterActive = Boolean(
    selectedFile || selectedStation || selectedCategory || selectedStatus || searchQuery ||
    sourceTypeFilter !== 'all'
  );

  const resetAllFilters = () => {
    setSelectedFile('');
    setSelectedStation('');
    setSelectedCategory('');
    setSelectedStatus('');
    setSearchQuery('');
    setSourceTypeFilter('all');
  };

  // Direct Drag & Drop Handler
  const handleDirectDrop = async (assetRel, photoName, file) => {
    if (!file.type.startsWith('image/') && !file.name.match(/\.(jpe?g|png|webp|bmp)$/i)) {
      alert('Harap masukkan berkas gambar (JPG, PNG, atau WEBP)!');
      return;
    }

    const targetKey = `${assetRel}/${photoName}`;
    setActionLoadingRel(targetKey);
    try {
      const reader = new FileReader();
      reader.onload = async () => {
        const base64Data = reader.result.split(',')[1];
        const res = await fetch('/api/timemark/replace-photo', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            baseExportDir: exportDir,
            assetRelPath: assetRel,
            photoName,
            imageBase64: base64Data
          })
        });
        const data = await res.json();
        if (res.ok && data.ok) {
          setFeedback({ type: 'success', text: `✓ Foto ${photoName} untuk ${assetRel} berhasil diperbarui.` });
          await fetchPhotos();
        } else {
          alert('Gagal mengganti foto: ' + (data.error || 'Terjadi kesalahan'));
        }
        setActionLoadingRel(null);
      };
      reader.readAsDataURL(file);
    } catch (err) {
      alert('Galat baca berkas: ' + err.message);
      setActionLoadingRel(null);
    }
  };

  // Revert Foto Asli Handler
  const handleRevert = async (assetRel, photoName) => {
    if (!confirm(`Kembalikan foto ${photoName} untuk ${assetRel} ke versi aslinya?`)) return;
    const targetKey = `${assetRel}/${photoName}`;
    setActionLoadingRel(targetKey);
    try {
      const res = await fetch('/api/timemark/revert-photo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          baseExportDir: exportDir,
          assetRelPath: assetRel,
          photoName
        })
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        setFeedback({ type: 'success', text: `✓ Foto ${photoName} berhasil dipulihkan ke versi asli.` });
        await fetchPhotos();
      } else {
        alert('Gagal memulihkan foto: ' + (data.error || 'Terjadi kesalahan'));
      }
    } catch (err) {
      alert('Galat: ' + err.message);
    } finally {
      setActionLoadingRel(null);
    }
  };

  // Instant Merge PDF Per Row Handler
  const handleMergeRow = async (asset) => {
    setMergingRel(asset.relDir);
    try {
      const firstPhotoRel = `${asset.relDir}/0.jpg`;
      const res = await fetch('/api/timemark/remerge-single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rawRelPath: firstPhotoRel,
          baseExportDir: exportDir,
          pdfName: (asset.targetFiles && asset.targetFiles[0]) || undefined
        })
      });
      const data = await res.json();
      if (res.ok && (data.ok || data.success)) {
        if (data.fileUrl) {
          window.open(data.fileUrl, '_blank');
        }
        setFeedback({
          type: 'success',
          text: `✓ Berkas PDF target ${data.pdfName} berhasil digabung dengan foto Timemark!`
        });
      } else {
        alert('Gagal merge PDF: ' + (data.error || 'Terjadi kesalahan'));
      }
    } catch (err) {
      alert('Galat merge PDF: ' + err.message);
    } finally {
      setMergingRel(null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', height: '100%', width: '100%', overflowY: 'auto', paddingRight: '0.5rem' }}>
      
      {/* ── Top Bar: Folder & Status Bar ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '10px', padding: '0.85rem 1.25rem', width: '100%', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block' }}>Folder Foto Ekspor / Timemark:</span>
            <strong style={{ fontSize: '0.875rem', color: 'var(--text-primary)', wordBreak: 'break-all' }}>{exportDir || 'Belum dipilih'}</strong>
          </div>
          {onPickFolder && (
            <button
              onClick={onPickFolder}
              style={{ padding: '0.4rem 0.85rem', background: 'var(--accent)', color: '#ffffff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.35rem' }}
            >
              📁 Ganti Folder...
            </button>
          )}
          <button
            onClick={fetchPhotos}
            disabled={loading}
            style={{ padding: '0.4rem 0.75rem', background: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.35rem' }}
          >
            🔄 Refresh
          </button>
        </div>

        {/* Counter Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', padding: '0.35rem 0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)', fontWeight: 500 }}>
            Menampilkan <strong style={{ color: '#10b981' }}>{filteredAssets.length}</strong> dari <strong>{assets.length}</strong> aset ({editedCount} telah diedit)
          </span>
        </div>
      </div>

      {/* ── Mode Toolbar (Diadopsi Persis dari Web App) ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '10px', padding: '1rem 1.25rem', width: '100%' }}>
        
        {/* Row 1: Pipeline Mode & View Mode Switchers */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
          
          {/* Pipeline Mode Switcher */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: 'var(--bg-secondary)', padding: '0.3rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', paddingLeft: '0.4rem', fontWeight: 600 }}>Mode:</span>
            {[
              { id: 'standard', label: '📅 Edit Tanggal' },
              { id: 'time', label: '⏰ Edit Jam' },
              { id: 'coord', label: '📍 Edit Koordinat' }
            ].map(m => (
              <button
                key={m.id}
                type="button"
                onClick={() => setPipelineMode(m.id)}
                style={{
                  padding: '0.35rem 0.8rem',
                  borderRadius: '6px',
                  border: 'none',
                  background: pipelineMode === m.id ? '#10b981' : 'transparent',
                  color: pipelineMode === m.id ? '#ffffff' : 'var(--text-secondary)',
                  fontWeight: pipelineMode === m.id ? 700 : 500,
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* View Mode Switcher (Dual vs Edited vs Raw) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: 'var(--bg-secondary)', padding: '0.3rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', paddingLeft: '0.4rem', fontWeight: 600 }}>Tampilan:</span>
            {[
              { id: 'dual', label: '⚖️ Komparasi / Dual' },
              { id: 'edited', label: '✨ Edited Saja' },
              { id: 'raw', label: '📷 Mentah Saja' }
            ].map(v => (
              <button
                key={v.id}
                type="button"
                onClick={() => setViewMode(v.id)}
                style={{
                  padding: '0.35rem 0.8rem',
                  borderRadius: '6px',
                  border: 'none',
                  background: viewMode === v.id ? 'var(--accent)' : 'transparent',
                  color: viewMode === v.id ? '#ffffff' : 'var(--text-secondary)',
                  fontWeight: viewMode === v.id ? 700 : 500,
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                {v.label}
              </button>
            ))}
          </div>

        </div>

        {/* Row 2: Search & Dropdown Filters */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', width: '100%', alignItems: 'center' }}>
          
          {/* Filter Berkas PDF Target */}
          <div>
            <select
              value={selectedFile}
              onChange={e => {
                const val = e.target.value;
                setSelectedFile(val);
                const match = targetFiles.find(t => t.file === val);
                if (match) {
                  if (match.category) setSelectedCategory(match.category);
                  if (match.btp) setSelectedStation(match.btp);
                }
              }}
              style={{ width: '100%', padding: '0.55rem 0.75rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.8rem', outline: 'none' }}
              title="Filter aset berdasarkan berkas PDF target"
            >
              <option value="">📄 Semua Berkas Target PDF</option>
              {allFileOptions.map((opt, idx) => (
                <option key={idx} value={opt.value} title={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Filter Stasiun / Wilayah (BTP) */}
          <div>
            <select
              value={selectedStation}
              onChange={e => setSelectedStation(e.target.value)}
              style={{ width: '100%', padding: '0.55rem 0.75rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.8rem', outline: 'none' }}
            >
              <option value="">🏢 Semua Stasiun / Wilayah (BTP)</option>
              {uniqueStations.map(stn => (
                <option key={stn} value={stn}>
                  {stn}
                </option>
              ))}
            </select>
          </div>

          {/* Filter Kategori Aset */}
          <div>
            <select
              value={selectedCategory}
              onChange={e => setSelectedCategory(e.target.value)}
              style={{ width: '100%', padding: '0.55rem 0.75rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.8rem', outline: 'none' }}
            >
              <option value="">⚙️ Semua Kategori Aset</option>
              {uniqueCategories.map(cat => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* Filter Status Kelengkapan Foto */}
          <div>
            <select
              value={selectedStatus}
              onChange={e => setSelectedStatus(e.target.value)}
              style={{ width: '100%', padding: '0.55rem 0.75rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.8rem', outline: 'none' }}
            >
              <option value="">📸 Semua Status Kelengkapan</option>
              <option value="complete">✅ Lengkap (3 Foto: 0, 50, 100%)</option>
              <option value="incomplete">⚠️ Belum Lengkap (&lt; 3 Foto)</option>
            </select>
          </div>

          {/* Pencarian Teks Cepat */}
          <div>
            <input
              type="text"
              placeholder="🔍 Cari nama aset (ZP 101, W11A, J10)..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{ width: '100%', padding: '0.55rem 0.85rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.8rem', outline: 'none' }}
            />
          </div>

        </div>

        {/* Reset Filter Button row */}
        {isFilterActive && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
            <button
              onClick={resetAllFilters}
              style={{ padding: '0.35rem 0.85rem', background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '6px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}
            >
              ✕ Reset Semua Filter
            </button>
          </div>
        )}
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

      {loading && (
        <div style={{ textAlign: 'center', padding: '3.5rem', color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
          ⏳ Memuat daftar foto aset dari disk...
        </div>
      )}

      {!loading && filteredAssets.length === 0 && (
        <div style={{ textAlign: 'center', padding: '3.5rem', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '10px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          {assets.length === 0
            ? 'Belum ada foto yang diekstraksi di folder ini. Jalankan Step 1 pada Tab Pipeline terlebih dahulu.'
            : 'Tidak ada aset yang cocok dengan kriteria filter atau pencarian saat ini.'}
        </div>
      )}

      {/* ── Asset Card List (1 Baris = 1 Kartu Aset Full-Width, 3 Kolom Foto 0%, 50%, 100%) ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%' }}>
        {filteredAssets.map((asset, idx) => {
          const isComplete = (asset.photos || []).length === 3;
          const isRowMerging = mergingRel === asset.relDir;

          return (
            <div
              key={idx}
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-color)',
                borderRadius: '12px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem',
                boxShadow: '0 4px 16px rgba(0,0,0,0.18)',
                width: '100%'
              }}
            >
              
              {/* Asset Card Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '0.2rem 0.55rem', borderRadius: '4px', background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                    {asset.station}
                  </span>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '0.2rem 0.55rem', borderRadius: '4px', background: 'rgba(52, 211, 153, 0.15)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.3)' }}>
                    {asset.category || asset.asset_type}
                  </span>
                  <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                    {asset.detail}
                  </h4>

                  {/* Tombol Instan ⚡ Merge PDF Per Baris Aset */}
                  <button
                    onClick={() => handleMergeRow(asset)}
                    disabled={isRowMerging}
                    style={{
                      padding: '0.25rem 0.75rem',
                      borderRadius: '6px',
                      background: isRowMerging ? 'rgba(2, 132, 199, 0.4)' : '#0284c7',
                      color: '#ffffff',
                      border: 'none',
                      fontSize: '0.75rem',
                      fontWeight: 800,
                      cursor: isRowMerging ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                      boxShadow: '0 2px 6px rgba(2, 132, 199, 0.4)',
                      transition: 'all 0.2s'
                    }}
                    title="Gabungkan 1 baris aset ini langsung ke file PDF target terkait"
                  >
                    {isRowMerging ? (
                      <>
                        <span>⏳</span>
                        <span>Merging...</span>
                      </>
                    ) : (
                      <>
                        <span>⚡</span>
                        <span>Merge PDF</span>
                      </>
                    )}
                  </button>

                  {asset.targetFiles && asset.targetFiles.length > 0 && (
                    <span
                      style={{ fontSize: '0.72rem', color: '#93c5fd', background: 'rgba(59, 130, 246, 0.15)', padding: '0.2rem 0.5rem', borderRadius: '4px', border: '1px solid rgba(59, 130, 246, 0.25)', cursor: 'help' }}
                      title={`Digunakan pada ${asset.targetFiles.length} berkas target:\n${asset.targetFiles.join('\n')}`}
                    >
                      📄 {asset.targetFiles.length} Target PDF
                    </span>
                  )}
                  {asset.sourceFile && (
                    <span
                      style={{ fontSize: '0.72rem', color: '#cbd5e1', background: 'rgba(100, 116, 139, 0.2)', padding: '0.2rem 0.5rem', borderRadius: '4px', border: '1px solid rgba(100, 116, 139, 0.3)' }}
                      title={`Sumber: ${asset.sourceFile}`}
                    >
                      📥 {asset.sourceFile}
                    </span>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '0.25rem 0.6rem', borderRadius: '5px', background: isComplete ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)', color: isComplete ? '#4ade80' : '#f87171', border: `1px solid ${isComplete ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}` }}>
                    {isComplete ? '✅ Lengkap (3 Foto)' : `⚠️ ${(asset.photos || []).length}/3 Foto`}
                  </span>
                  <span style={{ fontSize: '0.8rem', color: asset.hasEdited ? '#4ade80' : 'var(--text-secondary)', background: asset.hasEdited ? 'rgba(34, 197, 94, 0.1)' : 'var(--bg-secondary)', border: asset.hasEdited ? '1px solid rgba(34, 197, 94, 0.25)' : 'none', padding: '0.25rem 0.65rem', borderRadius: '5px', fontWeight: asset.hasEdited ? 700 : 500 }}>
                    📅 {asset.dateText || 'Belum ada tanggal'}
                  </span>
                </div>
              </div>

              {/* 3 Photos Grid (0% | 50% | 100%) Across 3 Large Columns */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', width: '100%' }}>
                {['0.jpg', '50.jpg', '100.jpg'].map((photoName) => {
                  const photoObj = (asset.photos || []).find(p => p.name === photoName);
                  const labelPercent = photoName.replace('.jpg', '') + '%';
                  const targetKey = `${asset.relDir}/${photoName}`;
                  const isDragOver = dragOverRel === targetKey;
                  const isActionLoading = actionLoadingRel === targetKey;

                  // Tentukan URL yang ditampilkan sesuai viewMode
                  let displayUrl = photoObj ? photoObj.rawUrl : '';
                  if (photoObj) {
                    if (viewMode === 'raw') {
                      displayUrl = photoObj.rawUrl;
                    } else if (viewMode === 'edited') {
                      displayUrl = photoObj.editedUrl || photoObj.rawUrl;
                    } else {
                      // dual / komparasi: tampilkan edited jika ada
                      displayUrl = photoObj.editedUrl || photoObj.rawUrl;
                    }
                  }

                  const isManual = photoObj?.meta?.manualEdit;

                  return (
                    <div
                      key={photoName}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.6rem',
                        background: 'var(--bg-secondary)',
                        borderRadius: '8px',
                        padding: '0.75rem',
                        border: '1px solid var(--border-color)',
                        boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.1)',
                        position: 'relative'
                      }}
                    >
                      {/* Photo Top Badge */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        <strong style={{ color: 'var(--text-primary)', fontSize: '0.85rem' }}>Foto {labelPercent}</strong>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          {photoObj ? (
                            <>
                              {isManual ? (
                                <span style={{ fontSize: '0.7rem', padding: '1px 6px', borderRadius: '4px', background: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24', border: '1px solid #f59e0b', fontWeight: 600 }}>
                                  Manual (Y:{photoObj.meta.yPos})
                                </span>
                              ) : photoObj.hasEdited ? (
                                <span style={{ fontSize: '0.7rem', padding: '1px 6px', borderRadius: '4px', background: 'rgba(34, 197, 94, 0.2)', color: '#4ade80', border: '1px solid #22c55e', fontWeight: 600 }}>
                                  ✨ Edited
                                </span>
                              ) : (
                                <span style={{ fontSize: '0.7rem', padding: '1px 6px', borderRadius: '4px', background: 'rgba(148, 163, 184, 0.2)', color: '#94a3b8', border: '1px solid rgba(148, 163, 184, 0.4)' }}>
                                  📷 Mentah
                                </span>
                              )}

                              {photoObj.hasBackup && (
                                <span style={{ fontSize: '0.7rem', padding: '1px 6px', borderRadius: '4px', background: 'rgba(234, 179, 8, 0.2)', color: '#facc15', border: '1px solid #eab308' }} title="Foto ini pernah diganti dan memiliki salinan asli">
                                  ↩️ Diganti
                                </span>
                              )}
                            </>
                          ) : (
                            <span style={{ fontSize: '0.72rem', color: '#f87171', fontWeight: 600 }}>Kosong</span>
                          )}
                        </div>
                      </div>

                      {/* Photo Image Container with Drag & Drop */}
                      <div
                        onDragOver={e => {
                          e.preventDefault();
                          e.stopPropagation();
                          setDragOverRel(targetKey);
                        }}
                        onDragLeave={e => {
                          e.preventDefault();
                          e.stopPropagation();
                          setDragOverRel(null);
                        }}
                        onDrop={e => {
                          e.preventDefault();
                          e.stopPropagation();
                          setDragOverRel(null);
                          const f = e.dataTransfer.files?.[0];
                          if (f) handleDirectDrop(asset.relDir, photoName, f);
                        }}
                        style={{
                          width: '100%',
                          height: '270px',
                          background: '#090d16',
                          borderRadius: '6px',
                          overflow: 'hidden',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          border: isDragOver ? '3px dashed #f59e0b' : '1px solid rgba(255,255,255,0.06)',
                          position: 'relative'
                        }}
                        title="Tarik & lepaskan file gambar ke sini untuk mengganti foto"
                      >
                        {photoObj ? (
                          <img
                            src={displayUrl}
                            alt={`${asset.detail} - ${labelPercent}`}
                            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                            loading="lazy"
                          />
                        ) : (
                          <div style={{ textAlign: 'center', color: '#64748b', fontSize: '0.8rem', padding: '1rem' }}>
                            <div style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>📷</div>
                            Berkas foto belum tersedia
                          </div>
                        )}

                        {/* Drag Over Overlay */}
                        {isDragOver && (
                          <div style={{ position: 'absolute', inset: 0, background: 'rgba(245, 158, 11, 0.9)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#ffffff', zIndex: 10 }}>
                            <span style={{ fontSize: '2rem' }}>📥</span>
                            <strong style={{ fontSize: '0.9rem' }}>Lepaskan untuk ganti foto</strong>
                          </div>
                        )}

                        {/* Action Loading Spinner */}
                        {isActionLoading && (
                          <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#4ade80', zIndex: 10 }}>
                            <span style={{ fontSize: '1.5rem', animation: 'spin 1s linear infinite' }}>⏳</span>
                            <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>Memproses foto...</span>
                          </div>
                        )}
                      </div>

                      {/* Photo Bottom Controls */}
                      {photoObj && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', justifyContent: 'space-between', paddingTop: '0.2rem' }}>
                          <button
                            type="button"
                            onClick={() => setEditingModal({ asset, photo: photoObj })}
                            style={{
                              flex: 1,
                              padding: '0.4rem 0.6rem',
                              background: '#10b981',
                              color: '#ffffff',
                              border: 'none',
                              borderRadius: '6px',
                              cursor: 'pointer',
                              fontSize: '0.75rem',
                              fontWeight: 700,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              gap: '0.35rem',
                              boxShadow: '0 2px 6px rgba(16, 185, 129, 0.3)'
                            }}
                          >
                            <span>⚙️</span>
                            <span>Edit Timemark</span>
                          </button>

                          {photoObj.hasBackup && (
                            <button
                              type="button"
                              onClick={() => handleRevert(asset.relDir, photoName)}
                              style={{
                                padding: '0.4rem 0.6rem',
                                background: 'rgba(234, 179, 8, 0.2)',
                                color: '#facc15',
                                border: '1px solid #eab308',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                fontSize: '0.75rem',
                                fontWeight: 600
                              }}
                              title="Kembalikan foto ini ke versi sebelum diganti"
                            >
                              ↩️ Asli
                            </button>
                          )}

                          <button
                            type="button"
                            onClick={() => setZoomPhoto({ url: displayUrl, title: `${asset.detail} - Foto ${labelPercent}` })}
                            style={{
                              padding: '0.4rem 0.6rem',
                              background: 'var(--bg-card)',
                              color: 'var(--text-secondary)',
                              border: '1px solid var(--border-color)',
                              borderRadius: '6px',
                              cursor: 'pointer',
                              fontSize: '0.75rem',
                              fontWeight: 600
                            }}
                            title="Perbesar Pratinjau Foto"
                          >
                            🔍
                          </button>
                        </div>
                      )}

                    </div>
                  );
                })}
              </div>

            </div>
          );
        })}
      </div>

      {/* ── Zoom Preview Modal ── */}
      {zoomPhoto && (
        <div
          onClick={() => setZoomPhoto(null)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.85)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 99999,
            padding: '2rem'
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              position: 'relative',
              maxWidth: '90vw',
              maxHeight: '90vh',
              background: '#0a0f1d',
              border: '1px solid var(--border-color)',
              borderRadius: '12px',
              padding: '1rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
              boxShadow: '0 20px 50px rgba(0,0,0,0.6)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>{zoomPhoto.title}</strong>
              <button
                onClick={() => setZoomPhoto(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', fontSize: '1.25rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>
            <div style={{ maxWidth: '85vw', maxHeight: '80vh', overflow: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <img
                src={zoomPhoto.url}
                alt={zoomPhoto.title}
                style={{ maxWidth: '100%', maxHeight: '78vh', objectFit: 'contain', borderRadius: '6px' }}
              />
            </div>
          </div>
        </div>
      )}

      {/* ── Timemark Editor Modal Interaktif ── */}
      {editingModal && (
        <TimemarkEditorModal
          isOpen={Boolean(editingModal)}
          onClose={() => setEditingModal(null)}
          asset={editingModal.asset}
          photo={editingModal.photo}
          exportDir={exportDir}
          onSaved={() => {
            fetchPhotos();
          }}
        />
      )}

    </div>
  );
}
