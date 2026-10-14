/** Task progress as slices of pizza. New slices pop in with an animation. */
export const PIZZA_SLICES = 8;

function wedge(i: number, r: number, c: number) {
  const a0 = ((i * 360) / PIZZA_SLICES - 90) * (Math.PI / 180);
  const a1 = (((i + 1) * 360) / PIZZA_SLICES - 90) * (Math.PI / 180);
  const x0 = c + r * Math.cos(a0), y0 = c + r * Math.sin(a0);
  const x1 = c + r * Math.cos(a1), y1 = c + r * Math.sin(a1);
  return `M${c} ${c} L${x0.toFixed(2)} ${y0.toFixed(2)} A${r} ${r} 0 0 1 ${x1.toFixed(2)} ${y1.toFixed(2)} Z`;
}

function pepperoni(i: number, r: number, c: number) {
  const mid = ((i + 0.5) * 360 / PIZZA_SLICES - 90) * (Math.PI / 180);
  return { cx: c + r * 0.58 * Math.cos(mid), cy: c + r * 0.58 * Math.sin(mid) };
}

export function Pizza({ slices, burnt = false, size = 54 }: { slices: number; burnt?: boolean; size?: number }) {
  const c = 30, r = 26;
  const filled = Math.max(0, Math.min(PIZZA_SLICES, slices));
  return (
    <div className={`pizza ${filled === PIZZA_SLICES ? "pizza-whole" : ""} ${burnt ? "pizza-burnt" : ""}`}>
      <svg viewBox="0 0 60 60" width={size} height={size} aria-label={`${filled} of ${PIZZA_SLICES} slices`}>
        <circle cx={c} cy={c} r={r + 2} fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.35)" strokeDasharray="3 3" />
        {Array.from({ length: filled }, (_, i) => {
          const p = pepperoni(i, r, c);
          return (
            <g key={i} className="slice" style={{ transformOrigin: `${c}px ${c}px` }}>
              <path d={wedge(i, r, c)} fill={burnt ? "#6b3b2a" : "#ffd36e"} stroke="#d98c2b" strokeWidth="2.2" />
              <circle cx={p.cx} cy={p.cy} r="3.2" fill={burnt ? "#2a1a14" : "#d9433a"} />
            </g>
          );
        })}
      </svg>
      <span className="pizza-label">{filled}/{PIZZA_SLICES}</span>
    </div>
  );
}
