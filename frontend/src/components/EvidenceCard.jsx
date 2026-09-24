export default function EvidenceCard({ evidence, index }) {
  const sourceClass = evidence.source || 'graph';
  return (
    <div className="evidence-item">
      <div style={{display:'flex',alignItems:'start',gap:8}}>
        <span style={{color:'#8b949e',fontSize:12,minWidth:20}}>#{index + 1}</span>
        <div style={{flex:1}}>
          <div className="evidence-claim">{evidence.claim}</div>
          <div style={{display:'flex',alignItems:'center',gap:8,marginTop:6}}>
            <span className={`evidence-source ${sourceClass}`}>{evidence.source}</span>
            {evidence.entity_ids?.length > 0 && (
              <span style={{fontSize:11,color:'#8b949e'}}>
                Entities: {evidence.entity_ids.slice(0,3).join(', ')}
                {evidence.entity_ids.length > 3 && ` +${evidence.entity_ids.length - 3} more`}
              </span>
            )}
          </div>
          <div className="evidence-ref">Ref: {evidence.ref}</div>
        </div>
      </div>
    </div>
  );
}
