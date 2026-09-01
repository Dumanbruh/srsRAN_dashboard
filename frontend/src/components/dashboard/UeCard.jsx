import UeMiniSparkline from './UeMiniSparkline';

function statColor(kind, value) {
  if (kind === 'nok') return value > 20 ? 'var(--red)' : value > 5 ? 'var(--amber)' : 'var(--green)';
  return value < 0 ? 'var(--red)' : value < 5 ? 'var(--amber)' : 'var(--green)'; // snr
}

export default function UeCard({ ue, color, isAdmin, onToggle, onPathloss, onRunTraffic }) {
  const dlPct = Math.min(100, (ue.dl / 15) * 100).toFixed(0);
  const ulPct = Math.min(100, (ue.ul / 15) * 100).toFixed(0);

  return (
    <div className={`ue-card ${ue.active ? 'active' : 'inactive'}`}>
      <div className="ue-hd">
        <span className="ue-name" style={{ color }}>UE{ue.id}</span>
        {isAdmin ? (
          <button className={`toggle ${ue.active ? 'on' : ''}`} onClick={() => onToggle(ue.id)}>
            {ue.active ? 'ON' : 'OFF'}
          </button>
        ) : <span className="viewer-badge">viewer</span>}
      </div>

      <div className="ue-stats">
        <div className="ue-stat">
          <div className="ue-stat-l">DL</div>
          <div className="ue-stat-v">{(ue.dl * 1000).toFixed(0)}<span className="ue-stat-u"> kb/s</span></div>
        </div>
        <div className="ue-stat">
          <div className="ue-stat-l">UL</div>
          <div className="ue-stat-v">{(ue.ul * 1000).toFixed(0)}<span className="ue-stat-u"> kb/s</span></div>
        </div>
        <div className="ue-stat">
          <div className="ue-stat-l">PUSCH SNR</div>
          <div className="ue-stat-v" style={{ color: statColor('snr', ue.snr) }}>{ue.snr.toFixed(1)}<span className="ue-stat-u"> dB</span></div>
        </div>
        <div className="ue-stat">
          <div className="ue-stat-l">NOK%</div>
          <div className="ue-stat-v" style={{ color: statColor('nok', ue.nok) }}>{ue.nok}%</div>
        </div>
      </div>

      <div className="bar-row">
        <div className="bar-lbl"><span>DL</span><span>{dlPct}%</span></div>
        <div className="bar-track"><div className="bar-fill" style={{ background: color, width: `${dlPct}%` }} /></div>
      </div>
      <div className="bar-row">
        <div className="bar-lbl"><span>UL</span><span>{ulPct}%</span></div>
        <div className="bar-track"><div className="bar-fill" style={{ background: color, width: `${ulPct}%` }} /></div>
      </div>

      <div className="slider-row">
        <span className="sl-label">Pathloss</span>
        <input
          type="range" min="0" max="100" step="1" value={ue.pathloss} disabled={!isAdmin}
          onChange={(e) => onPathloss(ue.id, e.target.value)}
        />
        <span className="sl-val">{ue.pathloss}dB</span>
      </div>

      <div style={{ marginTop: 8 }}><UeMiniSparkline dl={ue.dl} ul={ue.ul} /></div>

      <button className="cmd-btn" style={{ marginTop: 8, width: '100%' }}
              disabled={ue.trafficRunning} onClick={() => onRunTraffic(ue.id)}>
        {ue.trafficRunning ? 'Идёт трафик...' : '▶ Трафик (демо)'}
      </button>
    </div>
  );
}
