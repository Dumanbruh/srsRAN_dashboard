const LABELS = {
  ok: 'OK', err: 'ошибка', warn: 'предупреждение', running: 'выполняется',
  idle: 'простой', completed: 'завершено', failed: 'ошибка', stopped: 'остановлено',
};

export default function StatusBadge({ status, label }) {
  return <span className={'badge ' + status}>{label ?? LABELS[status] ?? status}</span>;
}
