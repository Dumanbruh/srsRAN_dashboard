import { useEffect, useState } from 'react';
import { probeOllamaStatus } from '../api/ai';

export function useOllamaStatus() {
  const [ok, setOk] = useState(null); // null = checking

  useEffect(() => {
    probeOllamaStatus()
      .then((status) => setOk(status !== 502))
      .catch(() => setOk(false));
  }, []);

  return ok;
}
