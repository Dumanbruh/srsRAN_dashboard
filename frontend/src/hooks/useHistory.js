import { useEffect, useRef, useState } from 'react';
import { getHistory } from '../api/stats';
import { downsampleRows } from './useChartDownsample';

function intervalToMs(iv) {
  const n = parseInt(iv, 10) || 30;
  return iv.endsWith('m') ? n * 60000 : n * 1000;
}

// Pivots {series:{rnti:[{t,v}]}} (what /api/history/ returns) into Recharts'
// row-based shape: [{t, [rnti]: v, [rnti]: v, ...}], one row per unique
// timestamp across all series — mirrors what loadHistory() did in the old
// vanilla JS before handing labels/datasets to Chart.js.
function pivot(series) {
  const rntis = Object.keys(series);
  const byTime = new Map();
  for (const rnti of rntis) {
    for (const p of series[rnti]) {
      if (!byTime.has(p.t)) byTime.set(p.t, { t: p.t });
      byTime.get(p.t)[rnti] = p.v;
    }
  }
  const rows = [...byTime.values()].sort((a, b) => (a.t < b.t ? -1 : 1));
  return { rows: downsampleRows(rows), rntis };
}

// suppressed: while true (a demo-traffic overlay is active on this chart),
// refreshes are skipped so a real-data poll doesn't wipe the overlay.
// isFixedRange: a custom start/end window is a frozen snapshot — poll once
// and stop, matching the original "точный период" behavior.
export function useHistory(metric, interval, rangeParams, { suppressed = false, isFixedRange = false } = {}) {
  const [rows, setRows] = useState([]);
  const [rntis, setRntis] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);
  const suppressedRef = useRef(suppressed);
  suppressedRef.current = suppressed;

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (suppressedRef.current) return;
      setLoading(true);
      try {
        const d = await getHistory(metric, interval, rangeParams);
        if (cancelled) return;
        if (!d.ok) { setRows([]); setRntis([]); return; }
        const { rows, rntis } = pivot(d.series || {});
        setRows(rows);
        setRntis(rntis);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    if (isFixedRange) return () => { cancelled = true; };
    const ms = Math.max(intervalToMs(interval), 3000);
    const id = setInterval(load, ms);
    return () => { cancelled = true; clearInterval(id); };
  }, [metric, interval, rangeParams, isFixedRange, refreshTick]);

  const refresh = () => setRefreshTick((t) => t + 1);
  return { rows, rntis, loading, refresh };
}
