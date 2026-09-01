import { useState } from 'react';
import { getStats } from '../api/stats';
import { usePolling } from './usePolling';

export function useAiSummary() {
  const [ues, setUes] = useState([]);
  const [ok, setOk] = useState(false);
  const [dlHistory, setDlHistory] = useState([]);

  usePolling(async () => {
    try {
      const d = await getStats();
      setOk(!!d.ok);
      if (!d.ok) return;
      const list = d.ues || [];
      setUes(list);
      const totalDl = list.reduce((s, u) => s + (u.dl || 0) * 1000, 0);
      setDlHistory((prev) => {
        const next = [...prev, totalDl / 1000];
        return next.length > 20 ? next.slice(next.length - 20) : next;
      });
    } catch { setOk(false); }
  }, 5000);

  return { ues, ok, dlHistory };
}
