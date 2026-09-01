import { apiPost } from './client';

export const setPathloss = (ueId, value) => apiPost(`/api/ue/${ueId}/pathloss/`, { value });
export const toggleUe = (ueId, active, pathloss) =>
  apiPost(`/api/ue/${ueId}/toggle/`, { active, pathloss });
export const setNoise = (type, level) => apiPost('/api/noise/', { type, level });
