export default function ConfidenceGauge({ value }) {
  const pct = (value || 0) * 100;
  const color = pct >= 70 ? '#f85149' : pct >= 30 ? '#d29922' : '#3fb950';

  return (
    <div className="card">
      <div className="gauge-container">
        <div className="gauge-value" style={{color}}>{pct.toFixed(0)}%</div>
        <div className="gauge-label">FRAUD PROBABILITY</div>
        <div className="gauge-bar">
          <div className="gauge-fill" style={{width:`${pct}%`,background:color}} />
        </div>
        <div style={{display:'flex',justifyContent:'space-between',fontSize:11,color:'#8b949e',marginTop:4}}>
          <span>0%</span>
          <span style={{color:'#d29922'}}>30% threshold</span>
          <span style={{color:'#f85149'}}>85% threshold</span>
          <span>100%</span>
        </div>
      </div>
    </div>
  );
}
