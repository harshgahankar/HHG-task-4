export default function Header({ caseData, investigating, onReRun, onExportSAR, onEmergencyFreeze }) {
  const c = caseData?.case || {};
  const caseId = caseData?.case_id || 'NO CASE SELECTED';
  const exposure = c.exposure_usd ? `$${c.exposure_usd.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '';

  const verdictBadge = c.verdict === 'fraud'
    ? <span className="badge badge-critical"><span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--error)' }} className="animate-pulse" /> CRITICAL</span>
    : c.verdict === 'uncertain'
    ? <span className="badge badge-medium"><span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--amber)' }} className="animate-pulse" /> REVIEW</span>
    : c.verdict === 'legitimate'
    ? <span className="badge badge-green"><span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--emerald)' }} /> CLEARED</span>
    : null;

  const patternLabel = c.pattern && c.pattern !== 'none'
    ? c.pattern.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    : 'Investigation';

  return (
    <div className="app-header">
      <div className="header-row">
        <div className="header-left">
          {verdictBadge}
          <h1 className="header-title">
            {caseId}: {patternLabel}
          </h1>
          {exposure && (
            <span className="badge badge-surface" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              {exposure}
            </span>
          )}
        </div>
        <div className="header-actions">
          <button className="btn btn-primary" onClick={onReRun} disabled={investigating}>
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>{investigating ? 'refresh' : 'sync_alt'}</span>
            {investigating ? 'Streaming...' : 'Re-Run'}
            <kbd style={{ marginLeft: 4, padding: '1px 5px', borderRadius: 3, background: 'rgba(0,0,0,0.15)', fontSize: '0.6rem', fontFamily: "'JetBrains Mono', monospace" }}>SPACE</kbd>
          </button>
          <button className="btn btn-surface" onClick={onExportSAR}>
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>description</span>
            Export SAR
          </button>
          <button className="btn btn-error" onClick={onEmergencyFreeze}>
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>lock</span>
            Freeze
          </button>
        </div>
      </div>
    </div>
  );
}
