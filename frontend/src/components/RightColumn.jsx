export default function RightColumn({ caseData, nba, onApprove, frozen }) {
  const c = caseData?.case || {};
  const prob = c.fraud_probability || 0;
  const riskScore = prob >= 0.85 ? 96 : prob >= 0.70 ? 78 : prob >= 0.40 ? 55 : 30;
  const riskLevel = riskScore >= 80 ? 'CRITICAL' : riskScore >= 60 ? 'HIGH' : riskScore >= 40 ? 'MED' : 'LOW';
  const riskColor = riskScore >= 80 ? 'var(--error)' : riskScore >= 60 ? 'var(--error)' : riskScore >= 40 ? 'var(--amber)' : 'var(--emerald)';
  const uncertainty = ((1 - prob) * 100).toFixed(1);
  const confPct = (prob * 100).toFixed(1);
  const confLevel = prob >= 0.85 ? 'CALIBRATED' : prob >= 0.50 ? 'MODERATE' : 'UNCERTAIN';
  const confColor = prob >= 0.85 ? 'var(--secondary)' : prob >= 0.50 ? 'var(--amber)' : 'var(--emerald)';
  const entropy = prob >= 0.85 ? 'LOW' : prob >= 0.50 ? 'MED' : 'HIGH';

  const stoppingGain = prob >= 0.85 ? 0.94 : prob >= 0.50 ? 0.72 : 0.45;
  const stopped = stoppingGain >= 0.85;
  const toolBudgetUsed = caseData?.tool_calls || 0;
  const confGain = Math.max(0, ((prob * 100) - (prob * 0.6 * 100))).toFixed(1);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {/* Gauges */}
      <div className="panel">
        <div className="panel-header">
          <span className="panel-label">Confidence</span>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.6rem', color: 'var(--outline)' }}>ENTROPY: {entropy}</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
          <div className="gauge-card">
            <span className="gauge-label">RISK</span>
            <div className="gauge-value" style={{ color: riskColor }}>{riskScore}</div>
            <span className="gauge-tag" style={{ background: `${riskColor}20`, color: riskColor }}>{riskLevel}</span>
          </div>
          <div className="gauge-card">
            <span className="gauge-label">CONF</span>
            <div className="gauge-value" style={{ color: 'var(--primary-container)' }}>{confPct}%</div>
            <span className="gauge-tag" style={{ background: 'rgba(0,242,254,0.12)', color: confColor }}>{confLevel}</span>
          </div>
          <div className="gauge-card">
            <span className="gauge-label">UNCERT</span>
            <div className="gauge-value" style={{ color: 'var(--emerald)' }}>{uncertainty}%</div>
            <span className="gauge-tag" style={{ background: 'rgba(52,211,153,0.1)', color: 'var(--emerald)' }}>
              {parseFloat(uncertainty) < 15 ? 'DONE' : 'OPEN'}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem' }}>
            <span style={{ color: 'var(--on-surface-variant)' }}>Stopping Rule</span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--primary)', fontSize: '0.62rem' }}>
              {stoppingGain.toFixed(2)}/0.85 {stopped ? '✓' : ''}
            </span>
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${(stoppingGain / 0.85) * 100}%`, background: stopped ? 'var(--emerald)' : 'var(--primary-container)' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: 'var(--outline)' }}>
            <span>Tools: {toolBudgetUsed}/15</span>
            <span>{stopped ? 'Plateau' : 'Gathering'}</span>
          </div>
        </div>
      </div>

      {/* Recommendation Diff */}
      <div className="panel" style={{ flex: 1 }}>
        <div className="panel-header">
          <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--on-surface)' }}>Recommendation Diff</span>
          <span className="badge badge-ok" style={{ fontSize: '0.55rem' }}>DELTA</span>
        </div>

        {/* Stage 1 */}
        <div className="diff-stage" style={{ opacity: 0.6 }}>
          <span style={{ fontSize: '0.58rem', fontFamily: "'JetBrains Mono', monospace", color: 'var(--outline)', textTransform: 'uppercase' }}>STAGE 1: PRE-EVIDENCE</span>
          <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--on-surface)', textDecoration: 'line-through', textDecorationColor: 'var(--error)', marginTop: 4 }}>
            {nba.initial?.map(a => a.action).join(', ') || 'Pending'}
          </div>
          <div style={{ fontSize: '0.62rem', color: 'var(--outline)', marginTop: 4 }}>
            Conf: {(prob * 0.6 * 100).toFixed(0)}% · Risk: {riskScore - 20}
          </div>
        </div>

        {/* Arrow */}
        <div className="diff-arrow">
          <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--secondary)' }}>south</span>
          <span className="label">+{confGain}% CONFIDENCE</span>
          <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--secondary)' }}>south</span>
        </div>

        {/* Stage 2 */}
        <div className="diff-stage" style={{ background: 'var(--surface-high)', borderColor: 'var(--primary-container)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ fontSize: '0.58rem', fontFamily: "'JetBrains Mono', monospace", color: 'var(--primary)', textTransform: 'uppercase', fontWeight: 700 }}>STAGE 2: POST-EVIDENCE</span>
            <span style={{ fontSize: '0.58rem', fontFamily: "'JetBrains Mono', monospace", color: 'var(--emerald)', fontWeight: 600 }}>COMPLETE</span>
          </div>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className="material-symbols-outlined" style={{ color: c.verdict === 'fraud' ? 'var(--error)' : 'var(--emerald)', fontSize: 18 }}>
              {c.verdict === 'fraud' ? 'dangerous' : 'verified'}
            </span>
            {nba.final?.map(a => a.action).join(' + ') || 'Pending'}
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
            <span className="badge badge-green" style={{ fontSize: '0.55rem', fontFamily: "'JetBrains Mono', monospace" }}>CONF: {confPct}%</span>
            <span className="badge badge-high" style={{ fontSize: '0.55rem', fontFamily: "'JetBrains Mono', monospace" }}>RISK: {riskScore}</span>
            <span className="badge badge-ok" style={{ fontSize: '0.55rem', fontFamily: "'JetBrains Mono', monospace" }}>{nba.final?.[0]?.route || 'AUTO'}</span>
          </div>
          {nba.what_changed && (
            <div style={{ fontSize: '0.7rem', color: 'var(--on-surface-variant)', marginTop: 6, padding: '0.5rem', background: 'var(--surface-lowest)', borderRadius: 'var(--radius-xs)', border: '1px solid var(--outline-variant)' }}>
              {nba.what_changed}
            </div>
          )}
        </div>

        {/* Approve */}
        <div style={{ display: 'flex', gap: 6, marginTop: 'auto', paddingTop: 8 }}>
          <button className="btn btn-primary btn-lg" style={{ flex: 1, justifyContent: 'center' }} onClick={onApprove}>
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
              {frozen ? 'lock_open' : 'how_to_reg'}
            </span>
            {frozen ? 'Frozen' : 'Approve'}
          </button>
          <button className="btn btn-ghost btn-icon" title="More">
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>more_vert</span>
          </button>
        </div>
      </div>
    </div>
  );
}
