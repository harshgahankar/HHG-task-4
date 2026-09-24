import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchSubgraph } from '../api';

export default function GraphView() {
  const { txnId } = useParams();
  const [graph, setGraph] = useState(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    fetchSubgraph(txnId, 2).then(setGraph).catch(console.error);
  }, [txnId]);

  useEffect(() => {
    if (!graph || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const W = canvas.width = canvas.parentElement.offsetWidth;
    const H = canvas.height = 500;

    ctx.fillStyle = '#0f1117';
    ctx.fillRect(0, 0, W, H);

    const nodes = graph.nodes || [];
    const edges = graph.edges || [];
    if (nodes.length === 0) return;

    // Simple force layout
    const pos = {};
    nodes.forEach((n, i) => {
      const angle = (2 * Math.PI * i) / nodes.length;
      pos[n.id] = { x: W/2 + 150 * Math.cos(angle), y: H/2 + 150 * Math.sin(angle), node: n };
    });

    // Draw edges
    ctx.strokeStyle = '#2d333b';
    ctx.lineWidth = 1;
    edges.forEach(e => {
      const s = pos[e.source], t = pos[e.target];
      if (s && t) {
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(t.x, t.y);
        ctx.stroke();
      }
    });

    // Draw nodes
    const colors = { Transaction: '#58a6ff', Card: '#3fb950', Customer: '#d29922', DeviceProfile: '#f85149', ClosedCase: '#8b949e', Case: '#f0883e' };
    nodes.forEach(n => {
      const p = pos[n.id];
      if (!p) return;
      ctx.fillStyle = colors[n.type] || '#8b949e';
      ctx.beginPath();
      ctx.arc(p.x, p.y, 6, 0, 2 * Math.PI);
      ctx.fill();
      ctx.fillStyle = '#e1e4e8';
      ctx.font = '10px sans-serif';
      ctx.fillText(n.label || n.id, p.x + 10, p.y + 4);
    });
  }, [graph]);

  return (
    <div>
      <Link to="/" className="btn" style={{marginBottom:16,display:'inline-block',textDecoration:'none'}}>&larr; Back</Link>
      <div className="card">
        <div className="card-title" style={{marginBottom:8}}>Subgraph around transaction {txnId}</div>
        <canvas ref={canvasRef} style={{width:'100%',borderRadius:6,background:'#0f1117'}} />
        {graph && (
          <div style={{fontSize:12,color:'#8b949e',marginTop:8}}>
            {graph.nodes?.length || 0} nodes, {graph.edges?.length || 0} edges
          </div>
        )}
      </div>
    </div>
  );
}
