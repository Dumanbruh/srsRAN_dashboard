import { ResponsiveContainer, LineChart, Line } from 'recharts';

function computeHealth(ues, avgNok, avgCqi) {
  if (!ues.length) return { level: 'neutral', text: 'нет подключений' };
  if (avgNok > 20 || avgCqi < 3) return { level: 'err', text: 'проблема со связью' };
  if (avgNok > 5 || avgCqi < 7) return { level: 'warn', text: 'деградация связи' };
  return { level: 'ok', text: 'сеть стабильна' };
}

export default function SummaryBar({ ues, ok, dlHistory }) {
  const active = ues.filter((u) => (u.dl || 0) > 0 || (u.ul || 0) > 0 || (u.cqi || 0) > 0);
  const totalDl = ues.reduce((s, u) => s + (u.dl || 0) * 1000, 0);
  const totalUl = ues.reduce((s, u) => s + (u.ul || 0) * 1000, 0);
  const avgCqi = ues.length ? ues.reduce((s, u) => s + (u.cqi || 0), 0) / ues.length : 0;
  const avgNok = ues.length ? ues.reduce((s, u) => {
    const okN = u.dl_ok || 0, nok = u.dl_nok || 0;
    return s + ((okN + nok) > 0 ? (nok / (okN + nok)) * 100 : 0);
  }, 0) / ues.length : 0;
  const health = ok ? computeHealth(ues, avgNok, avgCqi) : { level: 'neutral', text: 'нет данных' };

  const sparkData = dlHistory.map((v, i) => ({ i, v }));

  return (
    <div className="summary-bar">
      <div className={`health-pill ${health.level}`}>
        <div className="ctx-dot" />
        <span>{health.text}</span>
      </div>
      <div className="mcard-row">
        <div className="mcard blue"><div className="mc-label">Total DL</div><div className="mc-val">{totalDl.toFixed(0)}<span className="mc-unit">kb/s</span></div></div>
        <div className="mcard blue"><div className="mc-label">Total UL</div><div className="mc-val">{totalUl.toFixed(0)}<span className="mc-unit">kb/s</span></div></div>
        <div className="mcard green"><div className="mc-label">Активных UE</div><div className="mc-val">{active.length}/{ues.length}</div></div>
        <div className="mcard amber"><div className="mc-label">Avg CQI</div><div className="mc-val">{ues.length ? avgCqi.toFixed(1) : '—'}</div></div>
        <div className="mcard pink"><div className="mc-label">Avg NOK%</div><div className="mc-val">{avgNok.toFixed(0)}<span className="mc-unit">%</span></div></div>
      </div>
      <div className="summary-spark">
        <div className="summary-spark-label">DL, Mbps</div>
        <ResponsiveContainer width="100%" height={34}>
          <LineChart data={sparkData}>
            <Line dataKey="v" stroke="#347cbe" strokeWidth={1.5} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
