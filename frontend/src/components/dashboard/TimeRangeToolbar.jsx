import { useState } from 'react';

const PRESETS = ['5m', '15m', '30m', '1h', '6h', '24h'];
const PRESET_LABELS = { '5m': '5м', '15m': '15м', '30m': '30м', '1h': '1ч', '6h': '6ч', '24h': '24ч' };
const METRICS = [
  ['dl', 'DL Throughput'], ['ul', 'UL Throughput'], ['mcs', 'DL MCS'], ['ul_mcs', 'UL MCS'],
  ['bler_dl', 'DL BLER'], ['bler_ul', 'UL BLER'], ['loss_dl', 'DL Packet Loss %'], ['loss_ul', 'UL Packet Loss %'],
];
const INTERVALS = [['5s', '5с'], ['10s', '10с'], ['30s', '30с'], ['1m', '1м'], ['5m', '5м']];

export default function TimeRangeToolbar({
  range, onRangeChange, metric1, onMetric1Change, metric2, onMetric2Change,
  interval, onIntervalChange, isFixedRange, onApplyCustomRange, onExport,
}) {
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');

  return (
    <>
      <div className="toolbar">
        <span className="tr-label">Период</span>
        {PRESETS.map((p) => (
          <button key={p} className={`tr-btn ${!isFixedRange && range === p ? 'active' : ''}`}
                  onClick={() => onRangeChange(p)}>{PRESET_LABELS[p]}</button>
        ))}
        <div className="tr-sep" />
        <span className="tr-label">Метрика 1</span>
        <select className="tr-metric-select" value={metric1} onChange={(e) => onMetric1Change(e.target.value)}>
          {METRICS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <div className="tr-sep" />
        <span className="tr-label">Метрика 2</span>
        <select className="tr-metric-select" value={metric2} onChange={(e) => onMetric2Change(e.target.value)}>
          {METRICS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <div className="tr-sep" />
        <select className="tr-interval-select" value={interval} onChange={(e) => onIntervalChange(e.target.value)}>
          {INTERVALS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <button className="btn-export" onClick={onExport}>↓ CSV</button>
      </div>

      <div className="toolbar" style={{ marginTop: -6 }}>
        <span className="tr-label">Точный период</span>
        <input type="datetime-local" className="tr-interval-select" style={{ cursor: 'text' }}
               value={start} onChange={(e) => setStart(e.target.value)} />
        <span className="tr-label">—</span>
        <input type="datetime-local" className="tr-interval-select" style={{ cursor: 'text' }}
               value={end} onChange={(e) => setEnd(e.target.value)} />
        <button className="tr-btn" onClick={() => start && end && onApplyCustomRange(start, end)}>Применить</button>
        {isFixedRange && (
          <span className="tr-label" style={{ color: 'var(--blue)' }}>
            точный период активен — график зафиксирован, не обновляется
          </span>
        )}
      </div>
    </>
  );
}
