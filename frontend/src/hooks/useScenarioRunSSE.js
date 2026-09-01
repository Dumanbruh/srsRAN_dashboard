import { useCallback, useRef, useState } from 'react';
import { getRun, runLogStreamUrl } from '../api/scenarios';

// Attaches to one scenario run's live log stream (SSE) and tracks its detail,
// shared between the dashboard's embedded scenario panel and the full
// Scenarios page. Only one EventSource is kept open at a time — attaching to
// a new run closes the previous stream first.
export function useScenarioRunSSE() {
  const [run, setRun] = useState(null);
  const [logLines, setLogLines] = useState([]);
  const esRef = useRef(null);
  const activeRunId = useRef(null);

  const refreshRun = useCallback(async (runId) => {
    const d = await getRun(runId);
    if (d.ok) setRun(d.run);
  }, []);

  const attach = useCallback((runId) => {
    if (esRef.current) { esRef.current.close(); esRef.current = null; }
    activeRunId.current = runId;
    setLogLines([]);
    refreshRun(runId);

    const es = new EventSource(runLogStreamUrl(runId));
    esRef.current = es;
    es.onmessage = (ev) => {
      const payload = JSON.parse(ev.data);
      setLogLines((prev) => [...prev, payload]);
    };
    es.addEventListener('done', () => {
      es.close();
      if (esRef.current === es) esRef.current = null;
      refreshRun(runId);
    });
    es.onerror = () => { /* EventSource retries on its own */ };
  }, [refreshRun]);

  const isAttached = useCallback(() => activeRunId.current !== null, []);

  return { run, logLines, attach, isAttached };
}
