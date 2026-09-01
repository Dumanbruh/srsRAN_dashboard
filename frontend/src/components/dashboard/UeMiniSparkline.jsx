import { useEffect, useState } from 'react';
import Sparkline from '../shared/Sparkline';

export default function UeMiniSparkline({ dl, ul }) {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    setHistory((prev) => {
      const next = [...prev, { dl, ul }];
      return next.length > 20 ? next.slice(next.length - 20) : next;
    });
  }, [dl, ul]);

  return (
    <Sparkline series={[
      { key: 'dl', color: '#347cbe', data: history.map((h) => h.dl) },
      { key: 'ul', color: '#178a63', data: history.map((h) => h.ul) },
    ]} />
  );
}
