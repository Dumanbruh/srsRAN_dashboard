// Hand-rolled inline SVG sparkline instead of a full chart-library instance —
// cheap enough to run one per UE card (updating every ~1s) without paying for
// several concurrent ResizeObserver-backed chart instances.
export default function Sparkline({ series, height = 50, maxPoints = 20 }) {
  const allValues = series.flatMap((s) => s.data);
  const max = Math.max(1, ...allValues);
  const w = 100, h = 100;

  const toPoints = (data) => {
    const trimmed = data.slice(-maxPoints);
    const n = Math.max(trimmed.length - 1, 1);
    return trimmed.map((v, i) => `${(i / n) * w},${h - (v / max) * h}`).join(' ');
  };

  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ width: '100%', height }}>
      {series.map((s) => (
        <polyline
          key={s.key}
          points={toPoints(s.data)}
          fill="none"
          stroke={s.color}
          strokeWidth="2"
          vectorEffect="non-scaling-stroke"
        />
      ))}
    </svg>
  );
}
