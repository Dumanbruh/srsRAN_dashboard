const SCN_STATUS_LABELS = {
  idle: 'ожидание', running: 'выполняется', completed: 'завершён',
  failed: 'ошибка', stopped: 'остановлен',
};

export function scnStatusLabel(status) {
  return SCN_STATUS_LABELS[status] || status;
}

export function fmtDuration(startIso, endIso) {
  if (!startIso) return '—';
  const start = new Date(startIso).getTime();
  const end = endIso ? new Date(endIso).getTime() : Date.now();
  const s = Math.max(0, Math.round((end - start) / 1000));
  if (s < 60) return `${s}с`;
  const m = Math.floor(s / 60), rs = s % 60;
  if (m < 60) return `${m}м ${rs}с`;
  const h = Math.floor(m / 60), rm = m % 60;
  return `${h}ч ${rm}м`;
}

export function toDatetimeLocalValue(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
