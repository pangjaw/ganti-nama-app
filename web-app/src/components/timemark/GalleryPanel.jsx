import { useState, useEffect } from 'react';

export default function GalleryPanel({ exportDir, onPickFolder }) {
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [feedback, setFeedback] = useState(null);

  // Modal State
  const [activeModal, setActiveModal] = useState(null); // { type: 'time' | 'coord' | 'replace', asset, photo }
  const [editDateText, setEditDateText] = useState('');
  const [applyToSiblings, setApplyToSiblings] = useState(false);
  const [yOverride, setYOverride] = useState(195);
  const [replaceFile, setReplaceFile] = useState(null);
  const [actionBusy, setActionBusy] = useState(false);

  // Fetch photos
  const fetchPhotos = async () => {
    if (!exportDir) return;
    setLoading(true);
    setFeedback(null);
    try {
      const res = await fetch(`/api/timemark/photos?folder=${encodeURIComponent(exportDir)}`);
      if (res.ok) {
        const data = await res.json();
        setAssets(data.assets || []);
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
      // Read file as base64
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

  // Filter assets
  const filteredAssets = assets.filter(a => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (a.station && a.station.toLowerCase().includes(q)) ||
      (a.asset_type && a.asset_type.toLowerCase().includes(q)) ||
      (a.detail && a.detail.toLowerCase().includes(q))
    );
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%', overflowY: 'auto', paddingRight: '0.5rem' }}>
      
      {/* Top Bar: Folder & Search */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '0.85rem 1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block' }}>Folder Foto Ekspor:</span>
            <strong style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>{exportDir || 'Belum dipilih'}</strong>
          </div>
          <button
            onClick={fetchPhotos}
            disabled={loading}
            style={{ padding: '0.35rem 0.65rem', background: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', borderRadius: '5px', cursor: 'pointer', fontSize: '0.75rem' }}
          >
            🔄 Refresh
          </button>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', width: '320px' }}>
          <input
            type="text"
            placeholder="Cari stasiun atau aset (cth: CLT, W11A, ZP)..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ width: '100%', padding: '0.45rem 0.75rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.825rem' }}
          />
        </div>
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
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Memuat daftar foto aset dari disk...
        </div>
      )}

      {!loading && filteredAssets.length === 0 && (
        <div style={{ textAlign: 'center', padding: '3rem', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          {assets.length === 0
            ? 'Belum ada foto yang diekstraksi di folder ini. Jalankan Step 1 pada Tab Pipeline terlebih dahulu.'
            : 'Tidak ada aset yang cocok dengan kata kunci pencarian.'}
        </div>
      )}

      {/* Grid Kartu Aset */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(460px, 1fr))', gap: '1rem' }}>
        {filteredAssets.map((asset, idx) => (
          <div key={idx} style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            
            {/* Card Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--accent)', fontWeight: 600, textTransform: 'uppercase' }}>
                  {asset.station} • {asset.asset_type}
                </span>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', margin: '0.15rem 0 0 0' }}>
                  {asset.detail}
                </h4>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>
                {asset.dateText || 'Belum ada tanggal'}
              </span>
            </div>

            {/* 3 Photos Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
              {['0.jpg', '50.jpg', '100.jpg'].map((photoName) => {
                const photoObj = (asset.photos || []).find(p => p.name === photoName);
                return (
                  <div key={photoName} style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', background: 'var(--bg-secondary)', borderRadius: '6px', padding: '0.4rem', border: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                      <strong>Foto {photoName.replace('.jpg', '')}%</strong>
                    </div>
                    
                    <div style={{ width: '100%', height: '110px', background: '#000000', borderRadius: '4px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      {photoObj ? (
                        <img
                          src={photoObj.url}
                          alt={photoName}
                          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                          loading="lazy"
                        />
                      ) : (
                        <span style={{ fontSize: '0.7rem', color: '#64748b' }}>Kosong</span>
                      )}
                    </div>

                    {/* Button Actions per Photo */}
                    <div style={{ display: 'flex', gap: '0.25rem', marginTop: '0.15rem' }}>
                      <button
                        onClick={() => openEditTimeModal(asset, photoName)}
                        title="Ubah teks tanggal & jam"
                        style={{ flex: 1, padding: '0.25rem 0', background: 'var(--bg-card-hover)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: '4px', cursor: 'pointer', fontSize: '0.7rem' }}
                      >
                        🕒 Jam
                      </button>
                      <button
                        onClick={() => openEditCoordModal(asset, photoName)}
                        title="Geser posisi kotak watermark"
                        style={{ flex: 1, padding: '0.25rem 0', background: 'var(--bg-card-hover)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', borderRadius: '4px', cursor: 'pointer', fontSize: '0.7rem' }}
                      >
                        📐 Geser
                      </button>
                      <button
                        onClick={() => openReplacePhotoModal(asset, photoName)}
                        title="Ganti berkas foto ini"
                        style={{ flex: 1, padding: '0.25rem 0', background: 'var(--bg-card-hover)', color: 'var(--accent)', border: '1px solid var(--accent)', borderRadius: '4px', cursor: 'pointer', fontSize: '0.7rem' }}
                      >
                        📷 Ganti
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

          </div>
        ))}
      </div>

      {/* MODAL 1: EDIT TANGGAL & JAM */}
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

      {/* MODAL 2: GESER KOORDINAT */}
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

      {/* MODAL 3: GANTI FOTO DARI DISK */}
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
