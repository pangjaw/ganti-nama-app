import React from 'react';

export default function BentoHeader({
  activePreset = 'Standar (Resor 1.21 Bogor)',
  currentVersion = 'v1.5.7',
  updateAvailable = false,
  onOpenUpdateModal = null,
  mainTab = 'ocr',
  title = '',
  subtitle = ''
}) {
  const getTabMeta = () => {
    switch (mainTab) {
      case 'ocr':
        return {
          title: 'OCR & Penamaan Ceklis PDF',
          sub: 'Standardisasi nama dokumen otomatis sesuai format BTP JAK & BTP BD'
        };
      case 'downloader':
        return {
          title: 'Downloader Dokumen Rekap P3-STE',
          sub: 'Otomatisasi pengunduhan checklist PDF bulanan dari portal P3-STE'
        };
      case 'timemark':
        return {
          title: 'Timemark & Manajemen Berkas Lapangan',
          sub: 'Otomasi watermark koordinat, jadwal dinasan, tablo checklist, dan penggabungan PDF'
        };
      default:
        return {
          title: 'Sintelis Utility 2.0',
          sub: 'Platform otomasi cerdas persinyalan dan telekomunikasi'
        };
    }
  };

  const meta = getTabMeta();
  const displayTitle = title || meta.title;
  const displaySubtitle = subtitle || meta.sub;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', marginBottom: '0.85rem' }}>
      {/* ── Title Banner ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#FFFFFF', margin: 0 }}>
            {displayTitle}
          </h2>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
            {displaySubtitle}
          </p>
        </div>
      </div>

      {/* ── 2 Bento Cards: Versi Aplikasi (Glow Orange jika ada update) & Profil Preset ── */}
      <div
        className="bento-header-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '0.75rem'
        }}
      >
        {/* Card 1: Versi Aplikasi */}
        <div
          className="bento-card"
          onClick={() => {
            if (updateAvailable && onOpenUpdateModal) {
              onOpenUpdateModal();
            }
          }}
          style={{
            cursor: updateAvailable ? 'pointer' : 'default',
            borderColor: updateAvailable ? '#FF7300' : 'var(--border-color)',
            boxShadow: updateAvailable
              ? '0 0 16px rgba(255, 115, 0, 0.4), inset 0 0 12px rgba(255, 115, 0, 0.15)'
              : 'none',
            background: updateAvailable
              ? 'linear-gradient(135deg, rgba(255, 115, 0, 0.12) 0%, var(--bg-card) 75%)'
              : 'var(--bg-card)',
            transition: 'all 0.3s ease'
          }}
          title={updateAvailable ? 'Versi baru tersedia! Klik untuk memperbarui.' : 'Versi aplikasi saat ini.'}
        >
          <div className="bento-card-top">
            <span className="bento-card-label" style={{ color: updateAvailable ? '#FF9433' : 'var(--text-secondary)' }}>
              VERSI APLIKASI
            </span>
            {updateAvailable ? (
              <span
                style={{
                  fontSize: '0.7rem',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  background: '#FF7300',
                  color: '#FFFFFF',
                  fontWeight: 700,
                  boxShadow: '0 0 8px #FF7300',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <span style={{ fontSize: '0.6rem' }}>●</span> UPDATE TERSEDIA
              </span>
            ) : (
              <span
                style={{
                  fontSize: '0.7rem',
                  padding: '1px 6px',
                  borderRadius: '4px',
                  background: 'rgba(16, 185, 129, 0.15)',
                  color: '#10B981',
                  fontWeight: 600
                }}
              >
                TERBARU
              </span>
            )}
          </div>
          <div
            className="bento-card-value"
            style={{
              color: updateAvailable ? '#FF9433' : '#FFFFFF',
              textShadow: updateAvailable ? '0 0 10px rgba(255, 115, 0, 0.5)' : 'none'
            }}
          >
            {currentVersion}
          </div>
          <div className="bento-card-sub" style={{ color: updateAvailable ? '#FFAA5B' : 'var(--text-secondary)' }}>
            {updateAvailable ? '⚡ Klik di sini untuk mengunduh update baru' : 'Sintelis Desktop Suite (Stable)'}
          </div>
        </div>

        {/* Card 2: Profil Preset Pegawai Aktif */}
        <div className="bento-card">
          <div className="bento-card-top">
            <span className="bento-card-label">PROFIL PRESET AKTIF</span>
            <span
              style={{
                fontSize: '0.7rem',
                padding: '1px 6px',
                borderRadius: '4px',
                background: 'rgba(59, 130, 246, 0.15)',
                color: '#60A5FA',
                fontWeight: 600
              }}
            >
              TERPILIH
            </span>
          </div>
          <div
            className="bento-card-value"
            style={{
              color: '#FFFFFF',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}
            title={activePreset}
          >
            {activePreset}
          </div>
          <div className="bento-card-sub">
            KUPT & Roster Personil Lapangan
          </div>
        </div>
      </div>
    </div>
  );
}
