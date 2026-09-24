import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { fetchCases, runAllInvestigations } from '../api';

export default function CaseList() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [investigating, setInvestigating] = useState(false);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchCases();
      setCases(data.cases);
    } catch (e) { setError(e.message); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleInvestigateAll = async () => {
    setInvestigating(true);
    try {
      await runAllInvestigations();
      await load();
    } catch (e) { setError(e.message); }
    setInvestigating(false);
  };

  if (loading) return <div className="loading"><span className="spinner" /> Loading cases...</div>;
  if (error) return <div className="card" style={{color:'#f85149'}}>Error: {error}</div>;

  const verdictColor = (v) => {
    if (v === 'fraud') return 'badge-fraud';
    if (v === 'legitimate') return 'badge-legitimate';
    return 'badge-uncertain';
  };

  return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
        <h2 style={{fontSize:18}}>Case Pack ({cases.length} cases)</h2>
        <button className="btn btn-primary" onClick={handleInvestigateAll} disabled={investigating}>
          {investigating ? <><span className="spinner" /> Investigating...</> : 'Run All Investigations'}
        </button>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Case</th>
            <th>Trigger</th>
            <th>Card</th>
            <th>Customer</th>
            <th>Score</th>
            <th>Verdict</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {cases.map(c => (
            <tr key={c.case_id}>
              <td style={{fontWeight:600}}>{c.case_id}</td>
              <td><span className={`badge ${c.trigger_type==='risk_score'?'badge-uncertain':c.trigger_type==='customer_report'?'badge-fraud':'badge-open'}`}>{c.trigger_type}</span></td>
              <td style={{fontFamily:'monospace',fontSize:12}}>{c.card_id}</td>
              <td style={{fontFamily:'monospace',fontSize:12}}>{c.customer_id}</td>
              <td>{c.risk_score || '-'}</td>
              <td>{c.verdict ? <span className={`badge ${verdictColor(c.verdict)}`}>{c.verdict}</span> : <span className="badge" style={{background:'#21262d',color:'#8b949e'}}>pending</span>}</td>
              <td><Link to={`/case/${c.case_id}`} className="btn" style={{textDecoration:'none'}}>{c.has_answer ? 'View' : 'Investigate'}</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
