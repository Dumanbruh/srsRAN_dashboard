import { apiGet, apiPost } from './client';

export const getScenarios = () => apiGet('/api/scenarios/');
export const getScenario = (slug) => apiGet(`/api/scenarios/${slug}/`);
export const runScenario = (slug, params) => apiPost(`/api/scenarios/${slug}/run/`, params);
export const getRuns = (limit) => apiGet(`/api/runs/?limit=${limit}`);
export const getRun = (id) => apiGet(`/api/runs/${id}/`);
export const stopRun = (id) => apiPost(`/api/runs/${id}/stop/`, {});
export const runLogStreamUrl = (id) => `/api/runs/${id}/logs/stream/`;
