import { scnStatusLabel, fmtDuration } from '../../utils/format';

export default function RunHistoryTable({ runs, onAttach }) {
  if (!runs.length) return <div className="empty-hint">Прогонов ещё не было.</div>;

  return (
    <table className="history-table">
      <thead>
        <tr><th>Сценарий</th><th>Параметры</th><th>Статус</th><th>Начало</th><th>Длительность</th><th></th></tr>
      </thead>
      <tbody>
        {runs.map((r) => (
          <tr key={r.id}>
            <td>{r.scenario_name}</td>
            <td className="params-summary">{JSON.stringify(r.params)}</td>
            <td><span className={`badge ${r.status}`}>{scnStatusLabel(r.status)}</span></td>
            <td>{r.started_at ? new Date(r.started_at).toLocaleString('ru-RU') : '—'}</td>
            <td>{fmtDuration(r.started_at, r.finished_at)}</td>
            <td>
              {r.started_at && (
                <a className="hist-link"
                   href={`/?start=${encodeURIComponent(r.started_at)}&end=${encodeURIComponent(r.finished_at || new Date().toISOString())}`}>
                  данные →
                </a>
              )}
              <a className="hist-link" href="javascript:void(0)" onClick={() => onAttach(r.id)}>лог →</a>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
