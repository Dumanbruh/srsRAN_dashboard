import { useEffect, useRef, useState } from 'react';
import { scnStatusLabel } from '../../utils/format';

export default function ScenarioQuickPanel({ catalog, isAdmin, run, logLines, onQuickRun, onStop }) {
  const [slug, setSlug] = useState('');
  const [running, setRunning] = useState(false);
  const logBoxRef = useRef(null);

  useEffect(() => {
    if (catalog.length && !slug) setSlug(catalog[0].slug);
  }, [catalog, slug]);

  useEffect(() => {
    if (logBoxRef.current) logBoxRef.current.scrollTop = logBoxRef.current.scrollHeight;
  }, [logLines]);

  const handleRun = async () => {
    if (!slug) return;
    setRunning(true);
    try { await onQuickRun(slug); } finally { setRunning(false); }
  };

  return (
    <div className="panel" id="scenario-panel" style={{ marginBottom: '1.1rem' }}>
      <div className="panel-hd">
        <span className="panel-title">Сценарий</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {run && <span className={`badge ${run.status}`}>{scnStatusLabel(run.status)}</span>}
          <a href="/scenarios/" className="tr-label" style={{ textDecoration: 'none', color: 'var(--blue)' }}>Все сценарии →</a>
        </div>
      </div>

      {isAdmin && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: '0.6rem' }}>
          <select className="tr-metric-select" style={{ flex: 1, minWidth: 200 }} value={slug} onChange={(e) => setSlug(e.target.value)}>
            {catalog.map((s) => <option key={s.slug} value={s.slug}>{s.name}</option>)}
          </select>
          <button className="tr-btn" disabled={running} onClick={handleRun}>Быстрый запуск (по умолчанию)</button>
        </div>
      )}

      {!run ? (
        <div className="scn-run-meta">Сейчас ничего не выполняется.</div>
      ) : (
        <>
          <div className="scn-run-meta">
            <b>{run.scenario_name}</b> #{run.id} · шаг {run.current_step ?? '—'}
            {run.error && <> · <span style={{ color: 'var(--red)' }}>ошибка: {run.error}</span></>}
            {run.status === 'running' && (
              <> · <a href="javascript:void(0)" onClick={() => onStop(run.id)} style={{ color: 'var(--red)', textDecoration: 'none' }}>[остановить]</a></>
            )}
          </div>
          <div className="scn-log-box" ref={logBoxRef}>
            {logLines.map((l, i) => (
              <div key={i} className={`scn-log-line ${l.level || ''}`}>
                <span className="scn-log-step">{l.step ?? ''}</span>
                <span className="scn-log-msg">{l.message}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
