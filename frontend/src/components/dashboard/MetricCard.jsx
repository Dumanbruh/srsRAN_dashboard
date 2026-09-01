export default function MetricCard({ color, label, value, unit }) {
  return (
    <div className={`mcard ${color}`}>
      <div className="mc-label">{label}</div>
      <div className="mc-val">{value}<span className="mc-unit">{unit}</span></div>
    </div>
  );
}
