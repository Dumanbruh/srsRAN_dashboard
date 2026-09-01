import { useCallback, useState } from 'react';

const MAX_LINES = 150;

export function useEventLog() {
  const [lines, setLines] = useState([]);
  const [count, setCount] = useState(0);

  const log = useCallback((msg, type = '') => {
    setCount((c) => c + 1);
    const ts = new Date().toTimeString().slice(0, 8);
    setLines((prev) => [{ ts, msg, type }, ...prev].slice(0, MAX_LINES));
  }, []);

  return { lines, count, log };
}
