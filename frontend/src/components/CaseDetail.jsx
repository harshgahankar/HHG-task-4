import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchCase, runInvestigation, fetchSimilarCases } from '../api';
import ConfidenceGauge from './ConfidenceGauge';
import EvidenceCard from './EvidenceCard';
import ActionList from './ActionList';

export default function CaseDetail() {
  const { caseId } = useParams();
  const [data, setData] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [loading, setLoading] = useState(true);
  const [investigating, setInvestigating] = useState(false);
  const [tab, setTab] = useState('evidence');
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const d = await fetchCase(caseId);
      setData(d);
      try {
        const s = await fetchSimilarCases(caseId);
        setSimilar(s.similar_cases || []);
      } catch {}
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, [caseId]);

  const handleInvestigate = async () => {
    setInvestigating(true);
    try {
      const d = await runInvestigation(caseId);
      setData(d);
    } catch (e) { setError(e.message); }
    setInvestigating(false);
  };

  if (loading) return <div className="loading"><span className="spinner" /> Loading case...</div>;
  if (error && !data) return <div className="card" style={{color:'#f85149'}}>Error: {error}<br/><Link to="/" className="btn" style={{marginTop:12,display:'inline-block',textDecoration:'none'}}>Back</Link></div>;

  const c = data?.case || {};
  const nba = data?.next_best_actions || {};
  const sar = data?.sar || {};
  const evidence = data?.evidence_requests || [];

  const verdictClass = (v) => v === 'fraud' ? 'badge-fraud' : v === 'legitimate' ? 'badge-legitimate' : 'badge-uncertain';

  return (
    <div>
      <Link to="/" className="btn" style={{marginBottom:16,display:'inline-block',textDecoration:'none'}}>&larr; All Cases</Link>

      <div className="card">
        <div className="card-header">
          <div>
            <span className="card-title" style={{fontSize:20}}>{caseId}</span>
            <span style={{marginLeft:12}}>
              <span className={`badge ${verdictClass(c.verdict)}`}>{c.verdict}</span>
              <span className="badge" style={{marginLeft:6,background:'#0c2d6b',color:'#58a6ff'}}>{c.pattern}</span>
            </span>
          </div>
          <button className="btn btn-primary" onClick={handleInvestigate} disabled={investigating}>
            {investigating ? <><span className="spinner" /> Investigating...</> : 'Re-Investigate'}
          </button>
        </div>

        <div className="grid-2" style={{marginTop:12}}>
          <div>
            <div style={{fontSize:13,color:'#8b949e'}}>Status</div>
            <div style={{fontSize:14,fontWeight:600}}>{c.status}</div>
          </div>
          <div>
            <div style={{fontSize:13,color:'#8b949e'}}>Exposure</div>
            <div style={{fontSize:14,fontWeight:600}}>${c.exposure_usd?.toFixed(2)}</div>
          </div>
          <div>
            <div style={{fontSize:13,color:'#8b949e'}}>Affected Transactions</div>
            <div style={{fontSize:14,fontWeight:600}}>{c.affected_txn_ids?.length || 0}</div>
          </div>
          <div>
            <div style={{fontSize:13,color:'#8b949e'}}>Connected Cards</div>
            <div style={{fontSize:14,fontWeight:600}}>{c.connected_card_ids?.length || 0}</div>
          </div>
        </div>

        <div style={{marginTop:12,fontSize:13,color:'#8b949e'}}>Summary</div>
        <div style={{fontSize:14,lineHeight:1.6}}>{c.summary}</div>
      </div>

      <div className="grid-2" style={{marginTop:16}}>
        <ConfidenceGauge value={c.fraud_probability} />
        <div className="card">
          <div className="card-title" style={{marginBottom:8}}>Metrics</div>
          <div style={{fontSize:13}}><strong>Tool calls:</strong> {data.tool_calls}</div>
          <div style={{fontSize:13}}><strong>Tokens:</strong> {data.tokens}</div>
          <div style={{fontSize:13}}><strong>Latency:</strong> {data.latency_s}s</div>
          <div style={{fontSize:13,marginTop:8}}><strong>Stop reason:</strong> <span style={{color:'#8b949e'}}>{data.stop_reason}</span></div>
          <div style={{fontSize:13,marginTop:8}}><strong>Graph case ID:</strong> {c.graph_case_id}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs" style={{marginTop:16}}>
        {['evidence','actions','sar','similar','timeline'].map(t => (
          <div key={t} className={`tab ${tab===t?'active':''}`} onClick={()=>setTab(t)}>
            {t.charAt(0).toUpperCase()+t.slice(1)}
            {t==='evidence' && c.evidence?.length ? ` (${c.evidence.length})` : ''}
            {t==='similar' && similar.length ? ` (${similar.length})` : ''}
          </div>
        ))}
      </div>

      {tab === 'evidence' && (
        <div>
          {c.evidence?.map((ev, i) => <EvidenceCard key={i} evidence={ev} index={i} />)}
          {evidence.length > 0 && (
            <div className="card" style={{borderColor:'#d29922'}}>
              <div className="card-title" style={{color:'#d29922',marginBottom:8}}>Additional Evidence Requests</div>
              {evidence.map((er, i) => (
                <div key={i} style={{fontSize:13,marginBottom:4}}>
                  <strong>{er.type}</strong> (step {er.asked_after_step}): {er.assumed_response}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'actions' && (
        <div className="diff-container">
          <div className="card">
            <div className="card-title" style={{marginBottom:8}}>Initial Actions (before evidence)</div>
            <ActionList actions={nba.initial} />
          </div>
          <div className="diff-arrow">&rarr;</div>
          <div className="card">
            <div className="card-title" style={{marginBottom:8}}>Final Actions (after evidence)</div>
            <ActionList actions={nba.final} />
            <div style={{marginTop:12,padding:8,background:'#0c2d6b',borderRadius:6,fontSize:13}}>
              <strong>What changed:</strong> {nba.what_changed}
            </div>
          </div>
        </div>
      )}

      {tab === 'sar' && (
        <div className="card">
          {sar.file ? (
            <>
              <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:12}}>
                <span className="badge badge-fraud">SAR REQUIRED</span>
                <span style={{fontSize:13,color:'#8b949e'}}>{sar.reason}</span>
              </div>
              <div className="card-title" style={{marginBottom:8}}>Narrative</div>
              <div className="sar-narrative">{sar.narrative}</div>
              <div style={{marginTop:12,fontSize:13}}>
                <strong>Subjects:</strong> {sar.subjects?.join(', ')}<br/>
                <strong>Total amount:</strong> ${sar.total_amount_usd?.toFixed(2)}<br/>
                <strong>Activity dates:</strong> {sar.activity_dates?.join(' to ')}
              </div>
            </>
          ) : (
            <div style={{textAlign:'center',padding:24,color:'#8b949e'}}>
              <div style={{fontSize:24,marginBottom:8}}>&#10003;</div>
              SAR not required for this case<br/>
              <span style={{fontSize:12}}>{sar.reason}</span>
            </div>
          )}
        </div>
      )}

      {tab === 'similar' && (
        <div>
          {similar.length === 0 ? (
            <div className="card" style={{textAlign:'center',color:'#8b949e',padding:24}}>No similar cases found</div>
          ) : (
            similar.map((sc, i) => (
              <div key={i} className="card">
                <div className="card-header">
                  <span className="card-title">{sc.case_id}</span>
                  <span className={`badge ${sc.outcome==='confirmed_fraud'?'badge-fraud':'badge-legitimate'}`}>{sc.outcome}</span>
                </div>
                <div style={{fontSize:13}}><strong>Pattern:</strong> {sc.pattern} | <strong>Exposure:</strong> ${parseFloat(sc.exposure_usd||0).toFixed(2)}</div>
                <div style={{fontSize:13,color:'#8b949e',marginTop:4}}>{sc.analyst_notes?.substring(0,200)}</div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === 'timeline' && (
        <div className="card">
          {nba.initial && (
            <div style={{marginBottom:16}}>
              <div className="card-title" style={{marginBottom:8}}>Initial Recommendation</div>
              <ActionList actions={nba.initial} />
            </div>
          )}
          {evidence.length > 0 && (
            <div style={{marginBottom:16,padding:12,background:'#1c2128',borderRadius:6,borderLeft:'3px solid #d29922'}}>
              <div style={{fontSize:13,fontWeight:600,color:'#d29922'}}>Evidence Requested</div>
              {evidence.map((er, i) => (
                <div key={i} style={{fontSize:13,marginTop:4}}>{er.type}: {er.assumed_response}</div>
              ))}
            </div>
          )}
          <div>
            <div className="card-title" style={{marginBottom:8}}>Final Recommendation</div>
            <ActionList actions={nba.final} />
          </div>
        </div>
      )}
    </div>
  );
}
