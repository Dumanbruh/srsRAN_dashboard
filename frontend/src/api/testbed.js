import { apiGet, apiPost } from './client';

export const getTestbedStatus = () => apiGet('/api/testbed/status/');
export const startTestbed = (n) => apiPost('/api/testbed/start/', { n });
export const stopTestbed = () => apiPost('/api/testbed/stop/', {});
