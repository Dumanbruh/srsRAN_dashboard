import { useState } from 'react';
import ScenarioParamField from './ScenarioParamField';

export default function ScenarioCard({ scenario, isAdmin, onRun }) {
  const params = scenario.parameters || {};
  const [values, setValues] = useState(() =>
    Object.fromEntries(Object.entries(params).map(([k, spec]) => [k, spec.default])));
  const [running, setRunning] = useState(false);

  const setField = (key, val) => setValues((prev) => ({ ...prev, [key]: val }));

  const handleRun = async () => {
    setRunning(true);
    try { await onRun(scenario.slug, values); } finally { setRunning(false); }
  };

  return (
    <div className="scard">
      <div className="scard-name">{scenario.name}</div>
      <div className="scard-desc">{scenario.description || ''}</div>
      <div className="scard-form">
        {Object.entries(params).map(([key, spec]) => (
          <ScenarioParamField key={key} paramKey={key} spec={spec} value={values[key]} onChange={(v) => setField(key, v)} />
        ))}
      </div>
      {isAdmin && (
        <div className="scard-actions">
          <button className="btn primary" disabled={running} onClick={handleRun}>Запустить</button>
        </div>
      )}
    </div>
  );
}
