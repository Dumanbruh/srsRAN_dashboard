export default function EventLogPanel({ lines, count }) {
  return (
    <div className="log-panel">
      <div className="log-hd">
        <span className="log-title">Журнал событий</span>
        <span className="log-cnt">{count} событий</span>
      </div>
      <div className="log-box">
        {lines.map((l, i) => (
          <div key={i} className={`log-line ${l.type}`}>
            <span className="log-ts">{l.ts}</span>
            <span className="log-msg">{l.msg}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
