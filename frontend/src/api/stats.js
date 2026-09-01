import { apiGet } from './client';

export const getStats = () => apiGet('/api/stats/');
export const getGnrStatus = () => apiGet('/api/gnr/status/');

export function getHistory(metric, interval, rangeParams) {
  return apiGet(`/api/history/?metric=${metric}&interval=${interval}&${rangeParams}`);
}

export function exportCsvUrl(metric, interval, rangeParams) {
  return `/api/export/?metric=${metric}&interval=${interval}&${rangeParams}`;
}
