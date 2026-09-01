import { getRuns } from '../api/scenarios';
import { usePolling } from './usePolling';

// Reload-recovery: if a scenario is already running when this page mounts
// (e.g. the browser was refreshed mid-run), find it and reattach the SSE log
// stream, instead of leaving the panel showing "nothing running".
export function useActiveRunPoll(isAttached, attach) {
  usePolling(async () => {
    if (isAttached()) return;
    try {
      const d = await getRuns(5);
      if (!d.ok) return;
      const running = d.runs.find((r) => r.status === 'running');
      if (running) attach(running.id);
    } catch { /* ignore, retried on next tick */ }
  }, 5000);
}
