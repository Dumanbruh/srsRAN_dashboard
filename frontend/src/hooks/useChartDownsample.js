// A chart never needs more rendered points than this, regardless of how much
// the API returns — re-rendering thousands of points on every auto-refresh is
// what made the old vanilla-JS charts bog down over a long session.
export const MAX_CHART_POINTS = 300;

export function downsampleRows(rows) {
  if (rows.length <= MAX_CHART_POINTS) return rows;
  const step = Math.ceil(rows.length / MAX_CHART_POINTS);
  const out = [];
  for (let i = 0; i < rows.length; i += step) out.push(rows[i]);
  const last = rows[rows.length - 1];
  if (out[out.length - 1] !== last) out.push(last);
  return out;
}
