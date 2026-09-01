import { useState } from 'react';

export default function TestbedControlPanel({ status, onStart, onStop }) {
  const [n, setN] = useState(2);
  const statusText = status.starting ? 'Запускается...' : status.stopping ? 'Останавливается...' : (status.running ? 'Запущен' : 'Остановлен');

  return (
    <div className="noise-panel">
      <div className="noise-hd">
        <span>Управление стендом</span>
        <span style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)' }}>{statusText}</span>
      </div>
      <div className="noise-btns" style={{ gridTemplateColumns: 'auto auto auto' }}>
        <select className="tr-metric-select" value={n} onChange={(e) => setN(parseInt(e.target.value, 10))}>
          {[1, 2, 3, 4, 5, 6, 7].map((i) => <option key={i} value={i}>{i} UE</option>)}
        </select>
        <button className="cmd-btn" disabled={status.running || status.starting || status.stopping}
                onClick={() => onStart(n)}>Запустить</button>
        <button className="cmd-btn danger" disabled={(!status.running && !status.starting) || status.stopping}
                onClick={onStop}>Остановить</button>
      </div>
    </div>
  );
}
