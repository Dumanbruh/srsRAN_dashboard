const NOISE_TYPES = [
  { key: 'none', label: 'Чистый' },
  { key: 'awgn', label: 'AWGN' },
  { key: 'fading', label: 'Fading' },
  { key: 'shadow', label: 'Shadow' },
  { key: 'doppler', label: 'Doppler' },
  { key: 'interf', label: 'Interf.' },
];
const NOISE_LABELS = {
  none: 'Чистый канал', awgn: 'AWGN', fading: 'Rayleigh Fading',
  shadow: 'Shadowing', doppler: 'Doppler', interf: 'Интерференция',
};

export default function NoisePanel({ noise, noiseLevel, onSetNoise, onSetLevel }) {
  return (
    <div className="noise-panel">
      <div className="noise-hd">
        <span>Имитация помех канала</span>
        <span style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)' }}>
          {NOISE_LABELS[noise] || noise}
        </span>
      </div>
      <div className="noise-btns">
        {NOISE_TYPES.map((n) => (
          <button key={n.key} className={`nbtn ${noise === n.key ? 'active' : ''}`}
                  onClick={() => onSetNoise(n.key)}>{n.label}</button>
        ))}
      </div>
      <div className="noise-intensity">
        <span className="ni-label">Интенсивность</span>
        <input type="range" min="0" max="30" step="1" value={noiseLevel}
               onChange={(e) => onSetLevel(e.target.value)} />
        <span className="sl-val" style={{ minWidth: 45 }}>{noiseLevel} dB</span>
      </div>
    </div>
  );
}
