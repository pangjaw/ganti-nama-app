import { useState, useEffect, useMemo } from 'react';

export default function GalleryPanel({ exportDir, onPickFolder }) {
  const [assets, setAssets] = useState([]);
  const [targetFiles, setTargetFiles] = useState([]);
  const [sourceFiles, setSourceFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Filter States
  const [selectedFile, setSelectedFile] = useState('');
  const [selectedStation, setSelectedStation] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedStatus, setSelectedStatus] = useState(''); // '' | 'complete' | 'incomplete'
  const [searchQuery, setSearchQuery] = useState('');

  // Zoom Preview Modal State
  const [zoomPhoto, setZoomPhoto] = useState(null); // { url, title }

  // Action Modals State
  const [activeModal, setActiveModal] = useState(null); // { type: 'time' | 'coord' | 'replace', asset, photo }
  const [editDateText, setEditDateText] = useState('');
  const [applyToSiblings, setApplyToSiblings] = useState(false);
  const [yOverride, setYOverride] = useState(195);
  const [replaceFile, setReplaceFile] = useState(null);
  const [actionBusy, setActionBusy] = useState(false);

  // Fetch photos and metadata from backend
  const fetchPhotos = async () => {
    if (!exportDir) return;
    setLoading(true);
    setFeedback(null);
    try {
      const res = await fetch(`/api/timemark/photos?folder=${encodeURIComponent(exportDir)}`);
      if (res.ok) {
        const data = await res.json();
        setAssets(data.assets || []);
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

  // Combined File List (Target & Source Files)
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
  }, [assets, selectedFile, selectedStation, selectedCategory, selectedStatus, searchQuery]);

  const isFilterActive = Boolean(selectedFile || selectedStation || selectedCategory || selectedStatus || searchQuery);

  const resetAllFilters = () => {
    setSelectedFile('');
    setSelectedStation('');
    setSelectedCategory('');
    setSelectedStatus('');
    setSearchQuery('');
  };

  // Open Edit Time Modal
  const openEditTimeModal = (asset, photoName) => {
    setActiveModal({
      type: 'time',
      asset,
      photo: photoName
    });
    setEditDateText(asset.dateText || '');
    setApplyToSiblings(false);
  };

  // Open Edit Coord Modal
  const openEditCoordModal = (asset, photoName) => {
    setActiveModal({
      type: 'coord',
      asset,
      photo: photoName
    });
    setYOverride(195);
  };

  // Open Replace Photo Modal
  const openReplacePhotoModal = (asset, photoName) => {
    setActiveModal({
      type: 'replace',
      asset,
      photo: photoName
    });
    setReplaceFile(null);
  };

  // Submit Edit Time
  const handleSaveTime = async () => {
    if (!editDateText.trim()) return;
    setActionBusy(true);
    try {
      const res = await fetch('/api/timemark/edit-time', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          baseExportDir: exportDir,
          assetRelPath: activeModal.asset.relPath,
          photoName: applyToSiblings ? 'all' : activeModal.photo,
          newDateText: editDateText.trim(),
          applyToSiblings
        })
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        setFeedback({ type: 'success', text: `✓ Waktu watermark berhasil diperbarui untuk ${activeModal.asset.detail}.` });
        setActiveModal(null);
        fetchPhotos();
      } else {
        alert('Gagal memperbarui waktu: ' + (data.error || 'Terjadi kesalahan'));
      }
    } catch (err) {
      alert('Galat: ' + err.message);
    } finally {
      setActionBusy(false);
    }
  };

  // Submit Edit Coord
  const handleSaveCoord = async () => {
    setActionBusy(true);
    try {
      const res = await fetch('/api/timemark/edit-coord', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          baseExportDir: exportDir,
          assetRelPath: activeModal.asset.relPath,
          photoName: activeModal.photo,
          yOverride: Number(yOverride)
        })
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        setFeedback({ type: 'success', text: `✓ Posisi koordinat berhasil digeser untuk ${activeModal.asset.detail}.` });
        setActiveModal(null);
        fetchPhotos();
      } else {
        alert('Gagal menggeser koordinat: ' + (data.error || 'Terjadi kesalahan'));
      }
    } catch (err) {
      alert('Galat: ' + err.message);
    } finally {
      setActionBusy(false);
    }
  };

  // Submit Replace Photo
  const handleSaveReplace = async () => {
    if (!replaceFile) {
      alert('Silakan pilih berkas foto pengganti dari komputer!');
      return;
    }
    setActionBusy(true);
    try {
      const reader = new FileReader();
      reader.onload = async () => {
        const base64Data = reader.result.split(',')[1];
        const res = await fetch('/api/timemark/replace-photo', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            baseExportDir: exportDir,
            assetRelPath: activeModal.asset.relPath,
            photoName: activeModal.photo,
            imageBase64: base64Data
          })
        });
        const data = await res.json();
        if (res.ok && data.ok) {
          setFeedback({ type: 'success', text: `✓ Foto ${activeModal.photo} untuk ${activeModal.asset.detail} berhasil diganti dan di-watermark ulang.` });
          setActiveModal(null);
          fetchPhotos();
        } else {
          alert('Gagal mengganti foto: ' + (data.error || 'Terjadi kesalahan'));
        }
        setActionBusy(false);
      };
      reader.readAsDataURL(replaceFile);
    } catch (err) {
      alert('Galat baca file: ' + err.message);
      setActionBusy(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', height: '100%', width: '100%', overflowY: 'auto', paddingRight: '0.5rem' }}>
      
      {/* ── Top Bar: Folder & Status Bar ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '10px', padding: '0.85rem 1.25rem', width: '100%', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block' }}>Folder Foto Ekspor:</span>
            <strong style={{ fontSize: '0.875rem', color: 'var(--text-primary)' }}>{exportDir || 'Belum dipilih'}</strong>
          </div>
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
            Menampilkan <strong style={{ color: 'var(--accent)' }}>{filteredAssets.length}</strong> dari <strong>{assets.length}</strong> aset
          </span>
        </div>
      </div>

      {/* ── Filter Toolbar (Diadopsi dari Web App) ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '10px', padding: '1rem 1.25rem', width: '100%' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', width: '100%', alignItems: 'center' }}>
          
          {/* 1. Filter Berkas PDF (Target / Sumber) */}
          <div style={{ position: 'relative' }}>
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
              title="Filter aset berdasarkan berkas PDF target atau sumber"
            >
              <option value="">📄 Semua Berkas File (Target / Sumber)</option>
              {allFileOptions.map((opt, idx) => (
                <option key={idx} value={opt.value} title={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* 2. Filter Stasiun / Wilayah (BTP) */}
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

          {/* 3. Filter Kategori Aset */}
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

          {/* 4. Filter Status Kelengkapan Foto */}
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

          {/* 5. Pencarian Teks Cepat */}
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
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', padding: '0.25rem 0.65rem', borderRadius: '5px', fontWeight: 500 }}>
                    📅 {asset.dateText || 'Belum ada tanggal'}
                  </span>
                </div>
              </div>

              {/* 3 Photos Grid (0% | 50% | 100%) Across 3 Large Columns */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '1rem', width: '100%' }}>
                {['0.jpg', '50.jpg', '100.jpg'].map((photoName) => {
                  const photoObj = (asset.photos || []).find(p => p.name === photoName);
                  const labelPercent = photoName.replace('.jpg', '') + '%';
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
                        boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.1)'
                      }}
                    >
                      {/* Photo Top Badge */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        <strong style={{ color: 'var(--text-primary)', fontSize: '0.85rem' }}>Foto {labelPercent}</strong>
                        {photoObj ? (
                          <span style={{ fontSize: '0.72rem', color: '#4ade80', fontWeight: 600 }}>Tersedia</span>
                        ) : (
                          <span style={{ fontSize: '0.72rem', color: '#f87171', fontWeight: 600 }}>Kosong</span>
                        )}
                      </div>

                      {/* Photo Image Container (Large, ~290px height, Clickable for Zoom Preview) */}
                      <div
                        onClick={() => photoObj && setZoomPhoto({ url: photoObj.url, title: `${asset.detail} - Foto ${labelPercent}` })}
                        style={{
                          width: '100%',
                          height: '290px',
                          background: '#090d16',
                          borderRadius: '6px',
                          overflow: 'hidden',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          cursor: photoObj ? 'zoom-in' : 'default',
                          border: '1px solid rgba(255,255,255,0.06)',
                          position: 'relative'
                        }}
                        title={photoObj ? 'Klik untuk memperbesar foto' : 'Foto belum diekstraksi'}
                      >
                        {photoObj ? (
                          <>
                            <img
                              src={photoObj.url}
                              alt={photoName}
                              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                              loading="lazy"
                            />
                            <div
                              style={{
                                position: 'absolute',
                                bottom: '6px',
                                right: '6px',
                                background: 'rgba(0,0,0,0.65)',
                                color: '#ffffff',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                fontSize: '0.7rem',
                                pointerEvents: 'none'
                              }}
                            >
                              🔍 Perbesar
                            </div>
                          </>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.3rem', color: '#64748b' }}>
                            <span style={{ fontSize: '1.75rem' }}>📷</span>
                            <span style={{ fontSize: '0.8rem', fontWeight: 500 }}>Foto Belum Tersedia</span>
                          </div>
                        )}
                      </div>

                      {/* Button Actions under each Photo */}
                      <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.2rem' }}>
                        <button
                          onClick={() => openEditTimeModal(asset, photoName)}
                          title="Ubah teks tanggal & jam watermark"
                          style={{ flex: 1, padding: '0.45rem 0.25rem', background: 'var(--bg-card-hover)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: '5px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}
                        >
                          🕒 Jam
                        </button>
                        <button
                          onClick={() => openEditCoordModal(asset, photoName)}
                          title="Geser posisi kotak watermark"
                          style={{ flex: 1, padding: '0.45rem 0.25rem', background: 'var(--bg-card-hover)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: '5px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}
                        >
                          📐 Geser
                        </button>
                        <button
                          onClick={() => openReplacePhotoModal(asset, photoName)}
                          title="Ganti berkas foto ini dari komputer"
                          style={{ flex: 1, padding: '0.45rem 0.25rem', background: 'var(--bg-card-hover)', color: 'var(--accent)', border: '1px solid var(--accent)', borderRadius: '5px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 700 }}
                        >
                          📷 Ganti
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>

            </div>
          );
        })}
      </div>

      {/* ── MODAL: PRATINJAU PEMBESARAN FOTO (ZOOM PREVIEW) ── */}
      {zoomPhoto && (
        <div
          onClick={() => setZoomPhoto(null)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.85)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 2000,
            padding: '1.5rem',
            cursor: 'zoom-out'
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              position: 'relative',
              maxWidth: '90vw',
              maxHeight: '90vh',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              background: '#090d16',
              borderRadius: '8px',
              overflow: 'hidden',
              border: '1px solid var(--border-color)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.5)'
            }}
          >
            <div style={{ width: '100%', padding: '0.6rem 1rem', background: 'var(--bg-card)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)' }}>
              <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>{zoomPhoto.title}</strong>
              <button
                onClick={() => setZoomPhoto(null)}
                style={{ background: 'transparent', border: 'none', color: '#ffffff', fontSize: '1.25rem', cursor: 'pointer', padding: '0.2rem 0.5rem' }}
              >
                ✕
              </button>
            </div>
            <img
              src={zoomPhoto.url}
              alt="Preview"
              style={{ maxWidth: '85vw', maxHeight: '80vh', objectFit: 'contain' }}
            />
          </div>
        </div>
      )}

      {/* ── MODAL 1: EDIT TANGGAL & JAM ── */}
      {activeModal?.type === 'time' && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem' }}>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1.25rem', width: '420px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
              ✏️ Ubah Teks Tanggal & Jam Watermark
            </h4>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0 }}>
              Aset: <strong>{activeModal.asset.detail}</strong> ({activeModal.photo})
            </p>

            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>Teks Tanggal & Jam Lengkap</label>
              <input
                type="text"
                value={editDateText}
                onChange={e => setEditDateText(e.target.value)}
                placeholder="Contoh: Senin, Jan 06 2025"
                style={{ width: '100%', padding: '0.5rem 0.75rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              />
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={applyToSiblings}
                onChange={e => setApplyToSiblings(e.target.checked)}
              />
              <span>Terapkan ke seluruh foto aset ini (0%, 50%, 100%)</span>
            </label>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button
                onClick={() => setActiveModal(null)}
                disabled={actionBusy}
                style={{ padding: '0.45rem 0.85rem', background: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', cursor: 'pointer', fontSize: '0.825rem' }}
              >
                Batal
              </button>
              <button
                onClick={handleSaveTime}
                disabled={actionBusy}
                style={{ padding: '0.45rem 1.15rem', background: 'var(--accent)', color: '#ffffff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '0.825rem' }}
              >
                {actionBusy ? 'Menyimpan...' : 'Simpan'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL 2: GESER KOORDINAT ── */}
      {activeModal?.type === 'coord' && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem' }}>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1.25rem', width: '420px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
              📐 Geser Posisi Kotak Watermark (Y-Override)
            </h4>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0 }}>
              Aset: <strong>{activeModal.asset.detail}</strong> ({activeModal.photo})
            </p>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                <span>Posisi Vertikal Y:</span>
                <strong>{yOverride} px</strong>
              </div>
              <input
                type="range"
                min="50"
                max="450"
                value={yOverride}
                onChange={e => setYOverride(Number(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button
                onClick={() => setActiveModal(null)}
                disabled={actionBusy}
                style={{ padding: '0.45rem 0.85rem', background: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', cursor: 'pointer', fontSize: '0.825rem' }}
              >
                Batal
              </button>
              <button
                onClick={handleSaveCoord}
                disabled={actionBusy}
                style={{ padding: '0.45rem 1.15rem', background: 'var(--accent)', color: '#ffffff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '0.825rem' }}
              >
                {actionBusy ? 'Menerapkan...' : 'Terapkan Posisi'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL 3: GANTI FOTO DARI DISK ── */}
      {activeModal?.type === 'replace' && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem' }}>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1.25rem', width: '420px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
              📷 Ganti Foto {activeModal.photo.replace('.jpg', '')}%
            </h4>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0 }}>
              Aset: <strong>{activeModal.asset.detail}</strong>
            </p>

            <div style={{ border: '2px dashed var(--border-color)', borderRadius: '6px', padding: '1.5rem', textAlign: 'center' }}>
              <input
                type="file"
                accept="image/jpeg,image/png,image/jpg"
                onChange={e => setReplaceFile(e.target.files[0] || null)}
                style={{ display: 'block', width: '100%', fontSize: '0.825rem' }}
              />
              {replaceFile && (
                <p style={{ fontSize: '0.75rem', color: 'var(--accent)', margin: '0.5rem 0 0 0' }}>
                  Berkas terpilih: {replaceFile.name} ({(replaceFile.size / 1024).toFixed(1)} KB)
                </p>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button
                onClick={() => setActiveModal(null)}
                disabled={actionBusy}
                style={{ padding: '0.45rem 0.85rem', background: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', cursor: 'pointer', fontSize: '0.825rem' }}
              >
                Batal
              </button>
              <button
                onClick={handleSaveReplace}
                disabled={actionBusy || !replaceFile}
                style={{ padding: '0.45rem 1.15rem', background: 'var(--accent)', color: '#ffffff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '0.825rem' }}
              >
                {actionBusy ? 'Mengunggah & Watermark...' : 'Ganti Foto'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
