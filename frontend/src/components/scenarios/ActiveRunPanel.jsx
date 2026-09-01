import { useEffect, useRef } from 'react';
import { scnStatusLabel } from '../../utils/format';

export default function ActiveRunPanel({ run, logLines, isAdmin, onStop }) {
  const boxRef = useRef(null);
  useEffect(() => {
    if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight;
  }, [logLines]);

  if (!run) return <div className="run-panel"><div className="no-run">Сейчас ничего не выполняется.</div></div>;

  const canStop = run.status === 'running' && isAdmin;

  return (
    <div className="run-panel">
      <div className="run-panel-hd">
        <div>
          <div className="run-panel-title">#{run.id} {run.scenario_name}</div>
          <div className="run-meta">шаг {run.current_step ?? '—'} · параметры: <span className="params-summary">{JSON.stringify(run.params)}</span></div>
          {run.error && <div className="run-meta" style={{ color: 'var(--red)' }}>ошибка: {run.error}</div>}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className={`badge ${run.status}`}>{scnStatusLabel(run.status)}</span>
          {isAdmin && <button className="btn danger" disabled={!canStop} onClick={() => onStop(run.id)}>Остановить</button>}
        </div>
      </div>
      <div className="run-log-box" ref={boxRef}>
        {logLines.map((l, i) => (
          <div key={i} className={`log-line ${l.level || ''}`}>
            <span className="log-step">{l.step ?? ''}</span>
            <span className="log-msg">{l.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
