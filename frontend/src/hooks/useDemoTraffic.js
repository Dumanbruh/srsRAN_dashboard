import { useCallback, useRef, useState } from 'react';

// Pure client-side synthetic traffic animation — no hardware dependency, used
// as the safe "make it work at least visually" fallback when the real
// GNU Radio / gNB stack is flaky. Ports runTraffic() from the old vanilla JS.
//
// `demoPoints[ueId]` accumulates {t, dl, ul} samples for the duration of one
// run (plus a short grace period after it ends) so the two throughput charts
// can overlay whichever of dl/ul they're currently showing; `demoActiveUes`
// is the set of UE ids a real-data chart refresh must not currently touch.
export function useDemoTraffic(setUes) {
  const [demoActiveUes, setDemoActiveUes] = useState(() => new Set());
  const [demoPoints, setDemoPoints] = useState({});
  const timers = useRef({});

  const runTraffic = useCallback((ueId) => {
    if (timers.current[ueId]) return; // already running

    setDemoActiveUes((prev) => new Set(prev).add(ueId));
    setDemoPoints((prev) => ({ ...prev, [ueId]: [] }));
    setUes((prev) => prev.map((u) => (u.id === ueId ? { ...u, trafficRunning: true } : u)));

    const totalTicks = 8;
    const peakDl = 8 + Math.random() * 8; // 8-16 Mbps
    const peakUl = 3 + Math.random() * 5; // 3-8 Mbps
    let tick = 0;

    const timer = setInterval(() => {
      tick++;
      const phase = tick <= totalTicks / 2 ? tick / (totalTicks / 2) : (totalTicks - tick) / (totalTicks / 2);
      const jitter = () => 0.85 + Math.random() * 0.3;
      const dl = +(peakDl * phase * jitter()).toFixed(2);
      const ul = +(peakUl * phase * jitter()).toFixed(2);
      const t = new Date().toISOString();

      setUes((prev) => prev.map((u) => (u.id === ueId ? { ...u, dl, ul } : u)));
      setDemoPoints((prev) => ({ ...prev, [ueId]: [...(prev[ueId] || []), { t, dl, ul }] }));

      if (tick >= totalTicks) {
        clearInterval(timer);
        delete timers.current[ueId];
        setUes((prev) => prev.map((u) => (u.id === ueId ? { ...u, dl: 0, ul: 0, trafficRunning: false } : u)));
        setTimeout(() => {
          setDemoActiveUes((prev) => { const next = new Set(prev); next.delete(ueId); return next; });
          setDemoPoints((prev) => { const next = { ...prev }; delete next[ueId]; return next; });
        }, 1500);
      }
    }, 1000);
    timers.current[ueId] = timer;
  }, [setUes]);

  return { demoActiveUes, demoPoints, runTraffic };
}
