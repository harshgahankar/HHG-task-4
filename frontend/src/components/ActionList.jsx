export default function ActionList({ actions }) {
  if (!actions || actions.length === 0) return <div style={{color:'#8b949e',fontSize:13}}>No actions</div>;

  const routeClass = (r) => r === 'auto' ? 'route-auto' : r === 'L1' ? 'route-L1' : 'route-L2';

  return (
    <div>
      {actions.map((act, i) => (
        <div key={i} className="action-item">
          <span className="action-name">{act.action}</span>
          <span className={`route-badge ${routeClass(act.route)}`}>{act.route}</span>
          <span className="action-reason">{act.reason}</span>
        </div>
      ))}
    </div>
  );
}
