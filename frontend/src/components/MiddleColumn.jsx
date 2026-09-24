const STEPS = [
  { key: 'trigger', label: 'TRIGGER CAPTURED' },
  { key: 'traversal', label: 'GRAPH TRAVERSAL' },
  { key: 'assessment', label: 'UNCERTAINTY ASSESSMENT' },
  { key: 'evidence', label: 'EVIDENCE REQUEST' },
  { key: 'reassess', label: 'RE-ASSESSMENT' },
  { key: 'action', label: 'ACTION & ROUTING' },
];

export default function MiddleColumn({ caseData, investigating, simResponse, onSimulate }) {
  const c = caseData?.case || {};
  const evidence = caseData?.evidence_requests || [];
  const hasEvidence = evidence.length > 0;
  const prob = c.fraud_probability || 0.5;
  const prevProb = hasEvidence ? Math.max(0.1, prob - 0.2) : prob;

  const getStepState = (idx) => {
    if (!caseData) return 'pending';
    if (idx <= 2) return 'done';
    if (idx === 3) return hasEvidence ? 'done' : 'pending';
    if (idx === 4) return hasEvidence ? 'done' : 'pending';
    if (idx === 5) return 'done';
    return 'pending';
  };

  return (
    <div className="panel" style={{ gap: '0.75rem' }}>
      {/* Header */}
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span className="material-symbols-outlined" style={{ fontSize: 20, color: 'var(--primary)' }}>account_tree</span>
          <div>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--on-surface)' }}>Agent Execution Trace</span>
            <span className="panel-label" style={{ display: 'block', marginTop: 2 }}>STATE MACHINE · {STEPS.length} STEPS</span>
          </div>
        </div>
        <div className="badge badge-ok" style={{ fontSize: '0.58rem' }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--emerald)' }} className="animate-pulse" />
          TG-MCP CONNECTED
        </div>
      </div>

      {/* Stepper */}
      <div className="stepper">
        {STEPS.map((step, idx) => {
          const state = getStepState(idx);
          const isDone = state === 'done';

          return (
            <div key={step.key} className="step">
              <div className="step-indicator">
                <div className={`step-num ${isDone ? 'done' : ''}`}>{idx + 1}</div>
                {idx < STEPS.length - 1 && <div className={`step-line ${isDone ? 'done' : ''}`} />}
              </div>
              <div className="step-content" style={!isDone ? { opacity: 0.5 } : {}}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: '0.72rem', fontWeight: 700, color: isDone ? 'var(--primary)' : 'var(--on-surface-variant)', letterSpacing: '0.03em' }}>
                    {step.label}
                  </span>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.6rem', color: 'var(--outline)' }}>
                    {isDone ? '✓' : 'PENDING'}
                  </span>
                </div>

                {/* Step 0: Trigger */}
                {idx === 0 && caseData && (
                  <p style={{ fontSize: '0.75rem', color: 'var(--on-surface-variant)', lineHeight: 1.5 }}>
                    Flagged transaction on card <strong style={{ color: 'var(--primary)' }}>{c.card_id || 'N/A'}</strong>.
                    {c.exposure_usd ? ` Exposure: $${c.exposure_usd.toFixed(2)}.` : ''}
                  </p>
                )}

                {/* Step 1: Graph Traversal */}
                {idx === 1 && caseData && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div className="code-block">
                      <div><span className="code-keyword">RUN QUERY</span> <span className="code-type">findFraudRing</span>(</div>
                      <div style={{ paddingLeft: 16 }}>target=<span className="code-string">"{c.card_id || 'N/A'}"</span>, hops=<span className="code-number">2</span></div>
                      <div>);</div>
                    </div>
                    <div style={{ display: 'flex', gap: 8, fontSize: '0.68rem', color: 'var(--on-surface-variant)' }}>
                      <span>↔ {c.connected_card_ids?.length || 0} cards</span>
                      <span>·</span>
                      <span>📱 {c.connected_device_profiles?.length || 0} devices</span>
                    </div>
                  </div>
                )}

                {/* Step 2: Assessment */}
                {idx === 2 && caseData && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--on-surface-variant)', lineHeight: 1.5 }}>
                    {c.verdict === 'uncertain'
                      ? <>Probability <strong style={{ color: 'var(--amber)' }}>AMBIGUOUS</strong> at {prob.toFixed(2)}. Insufficient evidence.</>
                      : c.verdict === 'fraud'
                      ? <>Fraud at <strong style={{ color: 'var(--error)' }}>{prob.toFixed(2)}</strong> · {c.evidence?.length || 0} evidence items.</>
                      : <>Appears legitimate · prob: <strong style={{ color: 'var(--emerald)' }}>{prob.toFixed(2)}</strong>.</>
                    }
                  </div>
                )}

                {/* Step 3: Evidence */}
                {idx === 3 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {hasEvidence ? (
                      evidence.map((er, i) => (
                        <div key={i} style={{ fontSize: '0.72rem', color: 'var(--on-surface-variant)', padding: '0.375rem 0.5rem', background: 'var(--surface-lowest)', borderRadius: 'var(--radius-xs)', border: '1px solid var(--outline-variant)' }}>
                          Triggered <strong>{er.type?.replace(/_/g, ' ') || 'evidence'}</strong> for card <span style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--secondary)' }}>{c.card_id}</span>
                        </div>
                      ))
                    ) : (
                      <p style={{ fontSize: '0.72rem', color: 'var(--outline)' }}>No additional evidence needed.</p>
                    )}

                    {hasEvidence && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '0.5rem', background: 'var(--surface-lowest)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--outline-variant)' }}>
                        <span className="panel-label">Simulate Response</span>
                        <div className="sim-buttons">
                          <button className="btn btn-error btn-sm" onClick={() => onSimulate('denied')}>
                            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>cancel</span>
                            Denied
                          </button>
                          <button className="btn btn-ghost btn-sm" onClick={() => onSimulate('approved')}>
                            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>check_circle</span>
                            Approved
                          </button>
                          <button className="btn btn-ghost btn-sm" onClick={() => onSimulate('timeout')}>
                            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>timer_off</span>
                            Timeout
                          </button>
                        </div>
                      </div>
                    )}

                    {simResponse && (
                      <div className={`sim-banner ${simResponse}`}>
                        <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
                          {simResponse === 'denied' ? 'gpp_bad' : simResponse === 'approved' ? 'verified' : 'hourglass_empty'}
                        </span>
                        <span>
                          {simResponse === 'denied' && 'Denial → CONFIRMED FRAUD'}
                          {simResponse === 'approved' && 'Confirmed → LOW RISK'}
                          {simResponse === 'timeout' && 'Timeout → FALLBACK ESCALATION'}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Step 4: Reassess */}
                {idx === 4 && hasEvidence && (
                  <div style={{ fontSize: '0.72rem', color: 'var(--on-surface-variant)' }}>
                    Confidence: <span style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--amber)' }}>{prevProb.toFixed(2)}</span>
                    {' → '}
                    <strong style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--emerald)' }}>{prob.toFixed(2)}</strong>
                  </div>
                )}

                {/* Step 5: Action */}
                {idx === 5 && caseData && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {c.evidence?.map((ev, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.68rem', padding: '0.25rem 0.5rem', background: 'var(--surface-lowest)', borderRadius: 'var(--radius-xs)' }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--emerald)' }}>check</span>
                        <span style={{ flex: 1, color: 'var(--on-surface-variant)' }}>{ev.claim?.substring(0, 60)}{ev.claim?.length > 60 ? '...' : ''}</span>
                        <span style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--outline)', fontSize: '0.58rem' }}>{ev.source}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
