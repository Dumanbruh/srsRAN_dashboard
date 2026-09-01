import { useRef, useState } from 'react';
import { getStats } from '../api/stats';
import { usePolling } from './usePolling';

// Polls /api/stats/ every second and merges live dl/ul/snr/nok into `ues`
// (skipping any UE whose demo-traffic animation is currently driving its
// numbers) — mirrors fetchStats() from the old vanilla JS.
export function useStats(ues, setUes) {
  const [influxOk, setInfluxOk] = useState(false);
  const [gnbOk, setGnbOk] = useState(false);
  const uesRef = useRef(ues);
  uesRef.current = ues;

  usePolling(async () => {
    try {
      const d = await getStats();
      setInfluxOk(d.ok);
      if (!d.ok) { setGnbOk(false); return; }
      setGnbOk(true);
      const incoming = d.ues || [];
      setUes((prev) => prev.map((ue, i) => {
        const u = incoming[i];
        if (!u || ue.trafficRunning) return ue;
        const ok = u.dl_ok || 0;
        const nok = u.dl_nok || 0;
        return {
          ...ue,
          dl: u.dl || 0,
          ul: u.ul || 0,
          snr: u.pusch_snr !== undefined ? u.pusch_snr : (u.snr || 0),
          nok: (ok + nok) > 0 ? Math.round((nok / (ok + nok)) * 100) : 0,
        };
      }));
    } catch {
      setInfluxOk(false);
      setGnbOk(false);
    }
  }, 1000);

  return { influxOk, gnbOk };
}
