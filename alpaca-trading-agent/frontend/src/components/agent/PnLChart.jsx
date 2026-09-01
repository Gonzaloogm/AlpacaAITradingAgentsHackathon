import React from 'react';

/**
 * PnLChart - Institutional Corporate Style
 * Uses a linear polyline so step-function data (flat → jump → flat) renders
 * accurately without the spline-overshoot spikes that Catmull-Rom produces.
 */
export default function PnLChart({ data }) {
  if (!data || data.length < 2) {
    return (
      <div className="h-full w-full flex items-center justify-center text-slate-700 font-mono text-[10px] uppercase tracking-widest animate-pulse">
        Loading Chart Data...
      </div>
    );
  }

  const width = 800;
  const height = 250;
  const padding = 20;

  const values = data.map(d => d.value);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal || 0.0001;

  const getPoints = () => {
    return data.map((d, i) => ({
      x: (i / (data.length - 1)) * (width - 2 * padding) + padding,
      y: height - ((d.value - minVal) / range) * (height - 2 * padding) - padding
    }));
  };

  const points = getPoints();

  // Linear path — no spline overshoot on step-function data
  const createLinearPath = (pts) => {
    if (pts.length < 2) return '';
    return pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`).join(' ');
  };

  const linePath = createLinearPath(points);
  const areaPath = `${linePath} L ${points[points.length - 1].x},${height} L ${padding},${height} Z`;

  return (
    <div className="w-full h-full">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible" preserveAspectRatio="none">
        <defs>
          <linearGradient id="pnlCorporateGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#0091EA" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#00BFA5" stopOpacity="0.01" />
          </linearGradient>
          <linearGradient id="lineStrokeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00BFA5" />
            <stop offset="100%" stopColor="#0091EA" />
          </linearGradient>
        </defs>
        
        {/* Area fill */}
        <path d={areaPath} fill="url(#pnlCorporateGradient)" />
        
        {/* Linear line — faithful step representation */}
        <path
          d={linePath}
          fill="none"
          stroke="url(#lineStrokeGradient)"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}
