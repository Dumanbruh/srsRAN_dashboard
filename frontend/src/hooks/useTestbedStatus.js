import { useState } from 'react';
import { getTestbedStatus, startTestbed, stopTestbed } from '../api/testbed';
import { usePolling } from './usePolling';

export function useTestbedStatus(onNUesChanged) {
  const [status, setStatus] = useState({ running: false, starting: false, stopping: false, n_ues: 0 });

  usePolling(async () => {
    try {
      const d = await getTestbedStatus();
      setStatus(d);
      if (d.n_ues) onNUesChanged(d.n_ues);
    } catch { /* leave last known status */ }
  }, 3000);

  return {
    status,
    start: (n) => startTestbed(n),
    stop: () => stopTestbed(),
  };
}
