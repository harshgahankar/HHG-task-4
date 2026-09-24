import { useRef, useEffect, useState } from 'react';

const TABS = [
  { key: 'graph', label: 'Graph', icon: 'hub' },
  { key: 'evidence', label: 'Evidence', icon: 'folder_open' },
  { key: 'timeline', label: 'Timeline', icon: 'history' },
  { key: 'similar', label: 'Similar', icon: 'hub' },
  { key: 'sar', label: 'SAR', icon: 'contract_edit' },
];

const NODE_COLORS = {
  Transaction: '#60a5fa',
  Card: '#00f2fe',
  Customer: '#f59e0b',
  DeviceProfile: '#34d399',
  ClosedCase: '#849495',
  Case: '#a78bfa',
  EmailDomain: '#fb923c',
  BillingRegion: '#818cf8',
};

export default function BottomWorkspace({ activeTab, setActiveTab, subgraph, caseData, evidenceList, similarCases, sar, nba }) {
  const canvasRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [hopDepth, setHopDepth] = useState(2);

  useEffect(() => {
    if (activeTab !== 'graph' || !canvasRef.current || !subgraph) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const W = canvas.width = canvas.parentElement.offsetWidth - 32;
    const H = canvas.height = 360;
    ctx.clearRect(0, 0, W, H);

    const nodes = subgraph.nodes || [];
    const edges = subgraph.edges || [];
    if (nodes.length === 0) {
      ctx.fillStyle = '#6b7a7b';
      ctx.font = '14px Plus Jakarta Sans';
      ctx.textAlign = 'center';
      ctx.fillText('No subgraph data', W / 2, H / 2);
      return;
    }

    const pos = {};
    const cx = W / 2, cy = H / 2;
    nodes.forEach((n, i) => {
      const angle = (2 * Math.PI * i) / nodes.length;
      const r = Math.min(150, 70 + nodes.length * 4);
      pos[n.id] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
    });

    edges.forEach(e => {
      const s = pos[e.source], t = pos[e.target];
      if (!s || !t) return;
      const gradient = ctx.createLinearGradient(s.x, s.y, t.x, t.y);
      gradient.addColorStop(0, 'rgba(0,242,254,0.35)');
      gradient.addColorStop(1, 'rgba(255,180,171,0.4)');
      ctx.strokeStyle = gradient;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(t.x, t.y);
      ctx.stroke();
    });

    nodes.forEach(n => {
      const p = pos[n.id];
      if (!p) return;
      const color = NODE_COLORS[n.type] || '#6b7a7b';
      const r = n.type === 'Transaction' ? 4 : n.type === 'Case' ? 7 : 5;

      ctx.shadowColor = color;
      ctx.shadowBlur = 10;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, 2 * Math.PI);
      ctx.fill();
      ctx.shadowBlur = 0;

      ctx.fillStyle = '#e1e2ec';
      ctx.font = '9px JetBrains Mono';
      ctx.textAlign = 'center';
      const label = n.label || n.id;
      ctx.fillText(label.length > 20 ? label.substring(0, 18) + '..' : label, p.x, p.y + r + 12);
    });
  }, [subgraph, activeTab]);

  const evidenceCount = evidenceList?.length || 0;
  const similarCount = similarCases?.length || 0;

  return (
    <div className="col-full">
      <div className="tabs-bar">
        {TABS.map(tab => {
          const count = tab.key === 'evidence' ? evidenceCount : tab.key === 'similar' ? similarCount : null;
          return (
            <button key={tab.key} className={`tab-btn ${activeTab === tab.key ? 'active' : ''}`} onClick={() => setActiveTab(tab.key)}>
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>{tab.icon}</span>
              {tab.label}
              {count != null && count > 0 && <span className="tab-badge">{count}</span>}
            </button>
          );
        })}

        {activeTab === 'graph' && (
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: '0.6rem', color: 'var(--outline)' }}>DEPTH:</span>
            {[1, 2, 3, 4].map(d => (
              <button key={d} onClick={() => setHopDepth(d)} style={{
                width: 22, height: 22, borderRadius: 'var(--radius-xs)', border: '1px solid var(--outline-variant)',
                background: hopDepth === d ? 'var(--primary-container)' : 'transparent',
                color: hopDepth === d ? 'var(--on-primary-fixed)' : 'var(--outline)',
                fontSize: '0.62rem', fontWeight: 700, cursor: 'pointer', fontFamily: "'JetBrains Mono', monospace",
              }}>
                {d}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="graph-canvas" style={{ marginTop: '0.625rem' }}>
        {activeTab === 'graph' && (
          <>
            <div className="legend-overlay">
              <span style={{ fontSize: '0.58rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--outline)', fontWeight: 600 }}>Entities</span>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2px 12px' }}>
                {Object.entries(NODE_COLORS).slice(0, 6).map(([type, color]) => (
                  <div key={type} className="legend-item">
                    <span className="legend-dot" style={{ background: color }} />
                    <span>{type}</span>
                  </div>
                ))}
              </div>
            </div>

            <canvas ref={canvasRef} style={{ width: '100%', height: 360, cursor: 'crosshair' }} onClick={(e) => {
              if (!subgraph?.nodes) return;
              const rect = e.target.getBoundingClientRect();
              const mx = e.clientX - rect.left;
              const nodes = subgraph.nodes;
              const cx = rect.width / 2, cy = 180;
              let closest = null, minDist = 25;
              nodes.forEach((n, i) => {
                const angle = (2 * Math.PI * i) / nodes.length;
                const r = Math.min(150, 70 + nodes.length * 4);
                const d = Math.hypot(mx - (cx + r * Math.cos(angle)), (e.clientY - rect.top) - (cy + r * Math.sin(angle)));
                if (d < minDist) { minDist = d; closest = n; }
              });
              setSelectedNode(closest);
            }} />

            {selectedNode && (
              <div className="node-inspector">
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 8 }}>
                    <span className="panel-label">Node Inspector</span>
                    <button className="btn btn-ghost btn-sm" style={{ padding: '2px 4px', minWidth: 'auto' }} onClick={() => setSelectedNode(null)}>
                      <span className="material-symbols-outlined" style={{ fontSize: 14 }}>close</span>
                    </button>
                  </div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--primary)', fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", marginBottom: 4 }}>{selectedNode.label}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--on-surface-variant)' }}>Type: {selectedNode.type}</div>
                  <div className="inspector-row" style={{ marginTop: 8 }}>
                    <span style={{ color: 'var(--outline)', fontSize: '0.6rem' }}>ID</span>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--primary)', fontSize: '0.62rem' }}>{selectedNode.id}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 4, paddingTop: 8 }}>
                  <button className="btn btn-primary btn-sm" style={{ flex: 1, justifyContent: 'center' }}>Isolate</button>
                  <button className="btn btn-ghost btn-sm" style={{ flex: 1, justifyContent: 'center' }} onClick={() => alert(`GSQL:\nRUN QUERY findFraudRing(\n  target="${selectedNode.id}",\n  hops=${hopDepth}\n);`)}>GSQL</button>
                </div>
              </div>
            )}
          </>
        )}

        {activeTab === 'evidence' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 360, overflowY: 'auto' }}>
            {evidenceList?.length === 0 && (
              <div className="empty-state">
                <span className="material-symbols-outlined">folder_open</span>
                <span className="empty-state-title">No Evidence</span>
                <span className="empty-state-desc">Evidence will appear here during investigation</span>
              </div>
            )}
            {evidenceList?.map((ev, i) => (
              <div key={i} style={{ background: 'var(--surface-container)', borderRadius: 'var(--radius-sm)', padding: '0.75rem', borderLeft: `3px solid ${ev.source === 'graph' ? 'var(--secondary)' : ev.source === 'customer' ? 'var(--amber)' : 'var(--emerald)'}`, border: '1px solid var(--outline-variant)', borderLeftWidth: 3, borderLeftColor: ev.source === 'graph' ? 'var(--secondary)' : ev.source === 'customer' ? 'var(--amber)' : 'var(--emerald)' }}>
                <div style={{ display: 'flex', gap: 8 }}>
                  <span style={{ color: 'var(--outline)', fontSize: '0.65rem', fontFamily: "'JetBrains Mono', monospace" }}>#{i + 1}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.78rem', color: 'var(--on-surface)', lineHeight: 1.5 }}>{ev.claim}</div>
                    <div style={{ display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap' }}>
                      <span className={`badge ${ev.source === 'graph' ? 'badge-ok' : ev.source === 'customer' ? 'badge-medium' : 'badge-green'}`} style={{ fontSize: '0.55rem' }}>{ev.source}</span>
                      {ev.entity_ids?.length > 0 && (
                        <span style={{ fontSize: '0.6rem', color: 'var(--outline)' }}>{ev.entity_ids.slice(0, 2).join(', ')}</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'timeline' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 360, overflowY: 'auto' }}>
            {nba?.initial?.map((act, i) => (
              <div key={`i-${i}`} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0.5rem 0.625rem', background: 'var(--surface-container)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--outline-variant)', borderLeft: '3px solid var(--amber)' }}>
                <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--amber)' }}>pending</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--on-surface)' }}>{act.action}</div>
                  <div style={{ fontSize: '0.62rem', color: 'var(--on-surface-variant)' }}>{act.reason}</div>
                </div>
                <span className="badge badge-surface" style={{ fontSize: '0.55rem' }}>{act.route}</span>
                <span style={{ fontSize: '0.58rem', color: 'var(--outline)' }}>PRE</span>
              </div>
            ))}
            {caseData?.evidence_requests?.map((er, i) => (
              <div key={`e-${i}`} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0.5rem 0.625rem', background: 'var(--surface-high)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--outline-variant)', borderLeft: '3px solid var(--secondary)' }}>
                <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--secondary)' }}>send</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--on-surface)' }}>Evidence: {er.type}</div>
                  <div style={{ fontSize: '0.62rem', color: 'var(--on-surface-variant)' }}>{er.assumed_response}</div>
                </div>
              </div>
            ))}
            {nba?.final?.map((act, i) => (
              <div key={`f-${i}`} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0.5rem 0.625rem', background: 'var(--surface-container)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--outline-variant)', borderLeft: '3px solid var(--emerald)' }}>
                <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--emerald)' }}>check_circle</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--on-surface)' }}>{act.action}</div>
                  <div style={{ fontSize: '0.62rem', color: 'var(--on-surface-variant)' }}>{act.reason}</div>
                </div>
                <span className={`badge ${act.route === 'L2' ? 'badge-high' : act.route === 'L1' ? 'badge-medium' : 'badge-green'}`} style={{ fontSize: '0.55rem' }}>{act.route}</span>
                <span style={{ fontSize: '0.58rem', color: 'var(--outline)' }}>POST</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'similar' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 360, overflowY: 'auto' }}>
            {similarCases?.length === 0 && (
              <div className="empty-state">
                <span className="material-symbols-outlined">hub</span>
                <span className="empty-state-title">No Similar Cases</span>
              </div>
            )}
            {similarCases?.map((sc, i) => (
              <div key={i} style={{ background: 'var(--surface-container)', borderRadius: 'var(--radius-sm)', padding: '0.75rem', border: '1px solid var(--outline-variant)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: 'var(--primary)', fontSize: '0.78rem' }}>{sc.case_id}</span>
                  <span className={`badge ${sc.outcome === 'confirmed_fraud' ? 'badge-high' : 'badge-green'}`} style={{ fontSize: '0.55rem' }}>{sc.outcome}</span>
                </div>
                <div style={{ fontSize: '0.68rem', color: 'var(--on-surface-variant)' }}>
                  {sc.pattern} · ${parseFloat(sc.exposure_usd || 0).toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'sar' && (
          <div style={{ maxHeight: 360, overflowY: 'auto' }}>
            {sar?.file ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <span className="badge badge-critical">SAR REQUIRED</span>
                <div style={{ background: 'var(--surface-container)', borderRadius: 'var(--radius-sm)', padding: '1rem', fontSize: '0.82rem', lineHeight: 1.6, color: 'var(--on-surface)', border: '1px solid var(--outline-variant)' }}>
                  {sar.narrative}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--on-surface-variant)' }}>
                  <strong>Subjects:</strong> {sar.subjects?.join(', ')} · <strong>${sar.total_amount_usd?.toFixed(2)}</strong>
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <span className="material-symbols-outlined" style={{ color: 'var(--emerald)' }}>verified</span>
                <span className="empty-state-title">SAR Not Required</span>
                <span className="empty-state-desc">{sar?.reason || 'No SAR filing needed'}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
