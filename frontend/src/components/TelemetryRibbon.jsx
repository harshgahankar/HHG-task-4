export default function TelemetryRibbon({ caseData }) {
  const c = caseData?.case || {};
  const pattern = c.pattern && c.pattern !== 'none' ? c.pattern.replace(/_/g, ' ') : 'Awaiting';
  const status = c.status ? c.status.replace(/_/g, ' ').toUpperCase() : 'IDLE';

  return (
    <div className="telemetry-ribbon">
      <div className="ribbon-chip">
        <span>TRIGGER:</span>
        <strong>{caseData?.case_id ? 'Benchmark Investigation' : 'Waiting...'}</strong>
      </div>
      <div className="ribbon-chip">
        <span>PATTERN:</span>
        <strong style={{ color: 'var(--primary)' }}>{pattern}</strong>
      </div>
      <div className="ribbon-chip">
        <span>AGENT:</span>
        <strong style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--primary)' }}>smart_toy</span>
          Sentinel-7
        </strong>
      </div>
      <div className="ribbon-chip">
        <span>STATUS:</span>
        <strong style={{ color: 'var(--amber)', display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--amber)' }} className="animate-pulse" />
          {status}
        </strong>
      </div>
      <div className="ribbon-spacer" />
      <div className="ribbon-meta">
        <span>SESSION: #{caseData?.case_id?.replace('HHG-', '') || '----'}</span>
        <span>·</span>
        <span style={{ color: 'var(--primary-container)' }}>MCP: ACTIVE</span>
      </div>
    </div>
  );
}
