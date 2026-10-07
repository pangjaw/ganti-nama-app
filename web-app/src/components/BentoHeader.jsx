import React from 'react';

export default function BentoHeader({
  engineStatus = 'Siap',
  activePreset = 'Resor 1.21 Bogor',
  filesCount = 0,
  currentVersion = 'v1.5.5',
  mainTab = 'ocr',
  title = '',
  subtitle = ''
}) {
  const getTabMeta = () => {
    switch (mainTab) {
      case 'ocr':
        return {
          title: 'OCR & Penamaan Ceklis PDF',
          sub: 'Standardisasi nama dokumen otomatis sesuai format BTP JAK & BTP BD',
          statLabel: 'Berkas Dimuat',
          statUnit: 'PDF'
        };
      case 'downloader':
        return {
          title: 'Downloader Dokumen Rekap P3-STE',
          sub: 'Otomatisasi pengunduhan checklist PDF bulanan dari portal P3-STE',
          statLabel: 'Antrean Download',
          statUnit: 'Laporan'
        };
      case 'timemark':
        return {
          title: 'Timemark & Manajemen Berkas Lapangan',
          sub: 'Otomasi watermark koordinat, jadwal dinasan, tablo checklist, dan penggabungan PDF',
          statLabel: 'Total Berkas Terkait',
          statUnit: 'Aset'
        };
      default:
        return {
          title: 'Sintelis Utility 2.0',
          sub: 'Platform otomasi cerdas persinyalan dan telekomunikasi',
          statLabel: 'Total Berkas',
          statUnit: 'Item'
        };
    }
  };

  const meta = getTabMeta();
  const displayTitle = title || meta.title;
  const displaySubtitle = subtitle || meta.sub;

  const isWorking = engineStatus.toLowerCase().includes('proses') || engineStatus.toLowerCase().includes('jalan');

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

      {/* ── 4 Bento Metric Cards ── */}
      <div
        className="bento-header-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '0.75rem'
        }}
      >
        {/* Card 1: Status Engine */}
        <div className="bento-card">
          <div className="bento-card-top">
            <span className="bento-card-label">STATUS ENGINE</span>
            <span
              className={`bento-pulse-dot ${isWorking ? 'working' : 'ready'}`}
              title={isWorking ? 'Sedang Memproses' : 'Engine Siap'}
            />
          </div>
          <div className="bento-card-value" style={{ color: isWorking ? 'var(--accent-orange)' : '#10B981' }}>
            {engineStatus}
          </div>
          <div className="bento-card-sub">
            {isWorking ? 'Aktivitas latar belakang aktif' : 'Semua komponen standby'}
          </div>
        </div>

        {/* Card 2: Wilayah Operasi */}
        <div className="bento-card">
          <div className="bento-card-top">
            <span className="bento-card-label">WILAYAH OPERASI</span>
            <span style={{ fontSize: '0.9rem' }}>📍</span>
          </div>
          <div className="bento-card-value" style={{ color: '#FFFFFF' }}>
            {activePreset}
          </div>
          <div className="bento-card-sub">
            Daop 1 Jakarta (Sintel)
          </div>
        </div>

        {/* Card 3: Berkas Dimuat */}
        <div className="bento-card">
          <div className="bento-card-top">
            <span className="bento-card-label">{meta.statLabel.toUpperCase()}</span>
            <span style={{ fontSize: '0.9rem' }}>📂</span>
          </div>
          <div className="bento-card-value" style={{ color: 'var(--accent-orange)' }}>
            {filesCount} <span style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-secondary)' }}>{meta.statUnit}</span>
          </div>
          <div className="bento-card-sub">
            {filesCount > 0 ? 'Siap dieksekusi / diproses' : 'Belum ada berkas dipilih'}
          </div>
        </div>

        {/* Card 4: Versi Rilis */}
        <div className="bento-card">
          <div className="bento-card-top">
            <span className="bento-card-label">VERSI BINER</span>
            <span style={{ fontSize: '0.7rem', padding: '1px 5px', borderRadius: '4px', background: 'rgba(255, 115, 0, 0.15)', color: 'var(--accent-orange)', fontWeight: 600 }}>STABLE</span>
          </div>
          <div className="bento-card-value" style={{ color: '#FFFFFF' }}>
            {currentVersion}
          </div>
          <div className="bento-card-sub">
            Sintelis Desktop Suite
          </div>
        </div>
      </div>
    </div>
  );
}
