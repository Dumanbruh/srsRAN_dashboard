import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
} from 'recharts';

function fmtTick(t) {
  return typeof t === 'string' && t.length >= 16 ? t.slice(11, 16) : '';
}

export default function ThroughputChart({ rows, lines, loading, title, legend }) {
  return (
    <div className="panel">
      <div className="panel-hd">
        <span className="panel-title">{title}</span>
        <div className="legend">
          {legend.map((l) => (
            <span key={l.key} className="leg-item">
              <span className="leg-dot" style={{ background: l.color }} />{l.label}
            </span>
          ))}
        </div>
      </div>
      <div className="chart-wrap">
        {loading && <div className="chart-loading">Загрузка...</div>}
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="rgba(0,0,0,0.05)" vertical={false} />
            <XAxis dataKey="t" tickFormatter={fmtTick} tick={{ fill: '#8b98ac', fontSize: 10 }}
                   axisLine={false} tickLine={false} minTickGap={40} />
            <YAxis tick={{ fill: '#8b98ac', fontSize: 10 }} axisLine={false} tickLine={false} width={36} />
            <Tooltip labelFormatter={fmtTick} />
            {lines.map((l) => (
              <Line
                key={l.key} dataKey={l.key} name={l.label} stroke={l.color}
                strokeWidth={l.dashed ? 2 : 1.5} strokeDasharray={l.dashed ? '4 3' : undefined}
                dot={l.dashed ? { r: 2 } : false} isAnimationActive={false}
                connectNulls type="monotone"
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
