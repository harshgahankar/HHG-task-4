import { useState } from 'react';

export default function LeftColumn({ cases, selectedCase, caseData, onSelectCase }) {
  const [mode, setMode] = useState('risk_score');
  const c = caseData?.case || {};
  const flagged = cases.find(cs => cs.case_id === selectedCase);

  const riskScore = flagged?.risk_score || (c.fraud_probability ? (c.fraud_probability * 100).toFixed(0) : '0');
  const riskLevel = riskScore >= 80 ? 'CRITICAL' : riskScore >= 60 ? 'HIGH' : riskScore >= 40 ? 'MED' : 'LOW';
  const riskColor = riskScore >= 80 ? 'var(--error)' : riskScore >= 60 ? 'var(--error)' : riskScore >= 40 ? 'var(--amber)' : 'var(--emerald)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {/* Input Stream */}
      <div className="panel">
        <div className="panel-header">
          <span className="panel-label">Input Stream</span>
          <span className="badge badge-surface" style={{ fontSize: '0.58rem' }}>REAL-TIME</span>
        </div>

        <div className="mode-selector">
          {['risk_score', 'customer_report', 'analyst_request'].map(m => (
            <button key={m} className={`mode-btn ${mode === m ? 'active' : ''}`} onClick={() => setMode(m)}>
              {m === 'risk_score' ? 'Risk' : m === 'customer_report' ? 'Customer' : 'Manual'}
            </button>
          ))}
        </div>

        {flagged && (
          <div style={{ background: 'var(--surface-container)', borderRadius: 'var(--radius-sm)', padding: '0.625rem', border: '1px solid var(--outline-variant)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.82rem', color: 'var(--primary)', fontWeight: 700 }}>
                {flagged.card_id}
              </span>
              <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--secondary)' }}>verified_user</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--on-surface-variant)', marginTop: 4 }}>
              <span>{flagged.flagged_txn_id}</span>
              <span style={{ color: 'var(--error)', fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
                {flagged.trigger_type === 'risk_score' ? `${flagged.risk_score}` : flagged.trigger_type}
              </span>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="panel-label">Risk Velocity</span>
            <span style={{ color: riskColor, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: '0.72rem' }}>
              {riskScore}/100 <span style={{ fontSize: '0.6rem', opacity: 0.7 }}>[{riskLevel}]</span>
            </span>
          </div>

          <div className="sparkline-container">
            <svg width="100%" height="100%" fill="none" viewBox="0 0 200 40" preserveAspectRatio="none">
              <path d="M0 35 L20 32 L40 34 L60 30 L80 28 L100 22 L120 25 L140 12 L160 8 L180 5 L200 2" stroke="var(--secondary)" strokeLinecap="round" strokeWidth="2" />
              <circle cx="160" cy="8" fill="var(--error)" r="3" />
              <circle cx="200" cy="2" fill="var(--primary-container)" r="3.5" className="animate-ping" />
            </svg>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div className="info-row">
              <span className="label">LINKED DEVICES</span>
              <span className="value" style={{ color: 'var(--on-surface)' }}>{c.connected_device_profiles?.length || 0}</span>
            </div>
            <div className="info-row">
              <span className="label">CONNECTED CARDS</span>
              <span className="value" style={{ color: 'var(--secondary)' }}>{c.connected_card_ids?.length || 0}</span>
            </div>
            <div className="info-row">
              <span className="label">TXNs FLAGGED</span>
              <span className="value" style={{ color: 'var(--amber)' }}>{c.affected_txn_ids?.length || 0}</span>
            </div>
          </div>
        </div>

        <button className="btn btn-ghost" style={{ width: '100%', justifyContent: 'center', fontSize: '0.68rem' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--emerald)' }} className="animate-pulse" />
          SSE Agent Loop Active
        </button>
      </div>

      {/* Trigger Queue */}
      <div className="panel" style={{ flex: 1, overflow: 'hidden' }}>
        <div className="panel-header">
          <span className="panel-label">Trigger Queue</span>
          <span className="badge badge-surface" style={{ fontSize: '0.58rem' }}>{cases.length}</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto', flex: 1 }}>
          {cases.map(cs => {
            const isActive = cs.case_id === selectedCase;
            const score = cs.risk_score ? parseFloat(cs.risk_score) * 100 : 50;
            const severity = score >= 80 ? 'CRIT' : score >= 60 ? 'HIGH' : score >= 40 ? 'MED' : 'LOW';
            const sevColor = score >= 80 ? 'var(--error)' : score >= 60 ? 'var(--error)' : score >= 40 ? 'var(--amber)' : 'var(--emerald)';

            return (
              <div key={cs.case_id} className={`trigger-item ${isActive ? 'active' : ''}`} onClick={() => onSelectCase(cs.case_id)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: isActive ? 'var(--primary)' : 'var(--on-surface)', fontSize: '0.72rem' }}>
                    {cs.case_id}
                  </span>
                  <span style={{ padding: '1px 6px', borderRadius: 'var(--radius-xs)', background: `${sevColor}20`, color: sevColor, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: '0.6rem' }}>
                    {score.toFixed(0)} {severity}
                  </span>
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--on-surface-variant)' }}>
                  {cs.trigger_type.replace(/_/g, ' ')}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
