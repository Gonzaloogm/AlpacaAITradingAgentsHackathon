import { useState, useRef } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

/**
 * PnLChart — Interactive Institutional Portfolio Performance Chart
 * Features:
 * - Linear polyline representing equity curve without spline distortion
 * - Interactive hover with crosshair line, focus dot, and date/equity tooltip
 * - Period metrics header (Net change, Return %, High, Low)
 * - Grid lines with currency scale indicators
 */
export default function PnLChart({ data }) {
  const [hoverIndex, setHoverIndex] = useState(null);
  const containerRef = useRef(null);

  if (!data || data.length < 2) {
    return (
      <div className="h-full w-full flex items-center justify-center text-slate-600 font-mono text-xs uppercase tracking-widest animate-pulse">
        Collecting Portfolio History Data...
      </div>
    );
  }

  const width = 800;
  const height = 240;
  const paddingX = 35;
  const paddingY = 25;

  const values = data.map((d) => Number(d.value || 0));
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal || 1;

  // Compute (x, y) coordinates for all points
  const points = data.map((d, i) => ({
    x: (i / (data.length - 1)) * (width - 2 * paddingX) + paddingX,
    y: height - ((Number(d.value || 0) - minVal) / range) * (height - 2 * paddingY) - paddingY,
    raw: d,
  }));

  const createLinearPath = (pts) => {
    if (pts.length < 2) return '';
    return pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  };

  const linePath = createLinearPath(points);
  const lastPt = points[points.length - 1];
  const areaPath = `${linePath} L ${lastPt.x.toFixed(1)},${height} L ${paddingX},${height} Z`;

  // Period stats
  const firstVal = values[0];
  const activeIndex = hoverIndex !== null ? hoverIndex : data.length - 1;
  const activePoint = points[activeIndex];
  const activeVal = Number(activePoint?.raw?.value || 0);
  const deltaFromStart = activeVal - firstVal;
  const pctFromStart = firstVal > 0 ? (deltaFromStart / firstVal) * 100 : 0;
  const isGain = deltaFromStart >= 0;

  // Grid lines
  const midVal = (minVal + maxVal) / 2;
  const gridLines = [
    { val: maxVal, y: paddingY },
    { val: midVal, y: height / 2 },
    { val: minVal, y: height - paddingY },
  ];

  const handleMouseMove = (e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const chartWidth = rect.width;
    const relativeX = Math.max(0, Math.min(1, (mouseX - (paddingX / width) * chartWidth) / (chartWidth * ((width - 2 * paddingX) / width))));
    const closestIdx = Math.round(relativeX * (data.length - 1));
    setHoverIndex(Math.max(0, Math.min(data.length - 1, closestIdx)));
  };

  const handleMouseLeave = () => {
    setHoverIndex(null);
  };

  return (
    <div className="w-full h-full flex flex-col justify-between select-none">
      {/* Metrics Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-3 pb-2 border-b border-white/[0.04]">
        <div className="flex items-baseline gap-3">
          <span className="text-2xl font-mono font-black text-white tracking-tight">
            ${activeVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          <div className={`flex items-center gap-1 text-xs font-mono font-bold px-2 py-0.5 rounded ${isGain ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
            {isGain ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
            <span>{isGain ? '+' : ''}${Math.abs(deltaFromStart).toFixed(2)}</span>
            <span className="opacity-80">({isGain ? '+' : ''}{pctFromStart.toFixed(2)}%)</span>
          </div>
          {hoverIndex !== null && (
            <span className="text-[11px] font-mono text-blue-400/90 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
              {activePoint?.raw?.time}
            </span>
          )}
        </div>

        <div className="flex items-center gap-4 text-[11px] font-mono text-slate-500">
          <div>Low: <span className="text-slate-300 font-semibold">${minVal.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span></div>
          <div>High: <span className="text-slate-300 font-semibold">${maxVal.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span></div>
        </div>
      </div>

      {/* Interactive SVG Surface */}
      <div
        ref={containerRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className="relative flex-1 w-full min-h-[180px] cursor-crosshair"
      >
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full overflow-visible"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="pnlAreaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.22" />
              <stop offset="60%" stopColor="#00BFA5" stopOpacity="0.06" />
              <stop offset="100%" stopColor="#00BFA5" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="pnlLineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#3B82F6" />
              <stop offset="50%" stopColor="#60A5FA" />
              <stop offset="100%" stopColor="#00BFA5" />
            </linearGradient>
          </defs>

          {/* Grid lines & Values */}
          {gridLines.map((line, i) => (
            <g key={i}>
              <line
                x1={paddingX}
                y1={line.y}
                x2={width - paddingX}
                y2={line.y}
                stroke="rgba(255, 255, 255, 0.04)"
                strokeDasharray="4 4"
                strokeWidth="1"
              />
              <text
                x={width - paddingX + 6}
                y={line.y + 3}
                fill="#64748B"
                fontSize="9"
                fontFamily="'JetBrains Mono', monospace"
              >
                ${line.val >= 1000 ? `${(line.val / 1000).toFixed(1)}k` : line.val.toFixed(0)}
              </text>
            </g>
          ))}

          {/* Area Fill */}
          <path d={areaPath} fill="url(#pnlAreaGradient)" />

          {/* Line Stroke */}
          <path
            d={linePath}
            fill="none"
            stroke="url(#pnlLineGradient)"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Active Hover Crosshair and Dot */}
          {hoverIndex !== null && activePoint && (
            <g>
              {/* Vertical Crosshair */}
              <line
                x1={activePoint.x}
                y1={paddingY}
                x2={activePoint.x}
                y2={height - paddingY}
                stroke="rgba(59, 130, 246, 0.5)"
                strokeDasharray="3 3"
                strokeWidth="1.5"
              />
              {/* Focus Dot Glow */}
              <circle
                cx={activePoint.x}
                cy={activePoint.y}
                r="7"
                fill="#3B82F6"
                fillOpacity="0.25"
              />
              {/* Focus Dot Center */}
              <circle
                cx={activePoint.x}
                cy={activePoint.y}
                r="3.5"
                fill="#FFFFFF"
                stroke="#2563EB"
                strokeWidth="2"
              />
            </g>
          )}
        </svg>
      </div>

      {/* Date Range Footer */}
      <div className="flex justify-between items-center text-[10px] font-mono text-slate-500 pt-2 border-t border-white/[0.03]">
        <span>{data[0]?.time || 'Start'}</span>
        <span className="text-slate-600 uppercase tracking-widest text-[9px]">Continuous Paper Stream</span>
        <span>{data[data.length - 1]?.time || 'Latest'}</span>
      </div>
    </div>
  );
}
