import { useEffect, useRef } from 'react';

// Runs `fn` immediately, then every `ms` milliseconds, until unmount.
// `fn` itself may be async; overlapping ticks are not awaited/cancelled —
// matches the fire-and-forget setInterval pattern of the original vanilla JS.
export function usePolling(fn, ms, deps = []) {
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    fnRef.current();
    const id = setInterval(() => fnRef.current(), ms);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms, ...deps]);
}
