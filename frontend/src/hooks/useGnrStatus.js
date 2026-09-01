import { useState } from 'react';
import { getGnrStatus } from '../api/stats';
import { usePolling } from './usePolling';

export function useGnrStatus() {
  const [ok, setOk] = useState(false);

  usePolling(async () => {
    try {
      const d = await getGnrStatus();
      setOk(!!d.ok);
    } catch { setOk(false); }
  }, 3000);

  return ok;
}
