export default function ScenarioParamField({ paramKey, spec, value, onChange }) {
  const label = spec.label || paramKey;

  if (spec.type === 'bool') {
    return (
      <div className="field checkbox full">
        <input type="checkbox" id={`p-${paramKey}`} checked={!!value} onChange={(e) => onChange(e.target.checked)} />
        <label htmlFor={`p-${paramKey}`}>{label}</label>
      </div>
    );
  }
  if (spec.type === 'int' || spec.type === 'float') {
    return (
      <div className="field">
        <label>{label}</label>
        <input
          type="number" value={value} step={spec.type === 'int' ? 1 : 'any'}
          min={spec.min ?? undefined} max={spec.max ?? undefined}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    );
  }
  return (
    <div className="field">
      <label>{label}</label>
      <input type="text" value={value ?? ''} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
