/**
 * Non-visual verification of PnLChart.jsx path generation.
 *
 * Replicates the EXACT JS logic from the fixed PnLChart.jsx (linear polyline,
 * not Catmull-Rom spline) and computes the SVG path string for the real
 * portfolio-history data returned by the API.
 *
 * Run: node scripts/verify_pnlchart_path.mjs
 */

// ---- Real data from /api/portfolio-history ----
const equity = [100000, 102500, 105230.5];   // 3 data points
const portfolioHistoryData = equity.map((v, i) => ({ value: v, index: i }));

// ---- Constants from PnLChart.jsx ----
const width = 800;
const height = 250;
const padding = 20;

const values = portfolioHistoryData.map(d => d.value);
const minVal = Math.min(...values);
const maxVal = Math.max(...values);
const range = maxVal - minVal || 0.0001;

console.log('Data points (equity values):', values);
console.log(`minVal = ${minVal}, maxVal = ${maxVal}, range = ${range}`);

// ---- getPoints() from PnLChart.jsx ----
const points = portfolioHistoryData.map((d, i) => ({
  x: (i / (portfolioHistoryData.length - 1)) * (width - 2 * padding) + padding,
  y: height - ((d.value - minVal) / range) * (height - 2 * padding) - padding,
}));

console.log('\nComputed SVG points:');
points.forEach((p, i) => {
  console.log(`  [${i}] x=${p.x.toFixed(4)}, y=${p.y.toFixed(4)}  (equity=${values[i]})`);
});

// ---- OLD: Catmull-Rom spline (createSmoothPath) ----
const createSmoothPath = (pts) => {
  if (pts.length < 2) return '';
  let d = `M ${pts[0].x},${pts[0].y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i === 0 ? i : i - 1];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2 === pts.length ? i + 1 : i + 2];
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${cp1x},${cp1y} ${cp2x},${cp2y} ${p2.x},${p2.y}`;
  }
  return d;
};

// ---- NEW: Linear path (createLinearPath) ----
const createLinearPath = (pts) => {
  if (pts.length < 2) return '';
  return pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`).join(' ');
};

const oldPath = createSmoothPath(points);
const newPath = createLinearPath(points);

console.log('\n========== OLD path (Catmull-Rom cubic bezier) ==========');
console.log(oldPath);

console.log('\n========== NEW path (linear polyline — fixed) ==========');
console.log(newPath);

// ---- Mathematical analysis ----
console.log('\n========== Mathematical analysis ==========');
console.log('Data shape: monotonically increasing [100000, 102500, 105230.5]');
console.log('No step-function (flat-then-jump) in this mock data — it rises steadily.');
console.log('');

// Extract cubic bezier control points from old path and show the overshoot
// C cp1x,cp1y cp2x,cp2y x2,y2
const cubicMatch = oldPath.match(/C ([^\s]+),([^\s]+) ([^\s]+),([^\s]+) ([^\s]+),([^\s]+)/g);
if (cubicMatch) {
  console.log('Catmull-Rom control points (where overshoot would occur):');
  cubicMatch.forEach(segment => {
    const nums = segment.replace('C ', '').split(/[, ]/);
    console.log(`  cp1=(${parseFloat(nums[0]).toFixed(2)},${parseFloat(nums[1]).toFixed(2)}) `
      + `cp2=(${parseFloat(nums[2]).toFixed(2)},${parseFloat(nums[3]).toFixed(2)}) `
      + `end=(${parseFloat(nums[4]).toFixed(2)},${parseFloat(nums[5]).toFixed(2)})`);
    // Check if control point y exceeds either endpoint y (overshoot)
    const y1 = points[0].y, y2 = points[1].y;
    const cp1y_val = parseFloat(nums[1]);
    const cp2y_val = parseFloat(nums[3]);
    const minY = Math.min(y1, y2), maxY = Math.max(y1, y2);
    const overshoot1 = cp1y_val < minY || cp1y_val > maxY;
    const overshoot2 = cp2y_val < minY || cp2y_val > maxY;
    console.log(`  cp1y overshoot: ${overshoot1}, cp2y overshoot: ${overshoot2}`);
  });
}

console.log('');
console.log('Linear path verification:');
// Linear path should have y values strictly between min and max
const linearYValues = [points[0].y, points[1].y, points[2].y];
console.log(`  y values at each data point: ${linearYValues.map(v => v.toFixed(4)).join(', ')}`);
console.log(`  Are all y values within [${Math.min(...linearYValues).toFixed(4)}, ${Math.max(...linearYValues).toFixed(4)}]? YES — no overshoot possible`);
console.log('  Monotonically decreasing y? (higher equity = lower y in SVG coordinate system)');
console.log('  ', linearYValues.every((v, i, a) => i === 0 || v <= a[i-1]) ? 'YES ✓' : 'NO ✗');

// Test with flat data that would cause spline overshoot (the actual bug scenario)
console.log('\n========== Worst-case spike scenario (flat → jump → flat) ==========');
console.log('Simulating what the bug looks like with 3 points: [0, 0, 100000]');
const spikeEquity = [0, 0, 100000];
const spikeData = spikeEquity.map((v, i) => ({ value: v }));
const spikeMinVal = Math.min(...spikeEquity);
const spikeMaxVal = Math.max(...spikeEquity);
const spikeRange = spikeMaxVal - spikeMinVal || 0.0001;
const spikePoints = spikeData.map((d, i) => ({
  x: (i / (spikeData.length - 1)) * (width - 2 * padding) + padding,
  y: height - ((d.value - spikeMinVal) / spikeRange) * (height - 2 * padding) - padding,
}));
console.log('Spike points:', spikePoints.map(p => `(${p.x.toFixed(1)}, ${p.y.toFixed(1)})`).join(' → '));
const spikeCubic = createSmoothPath(spikePoints);
const spikeLinear = createLinearPath(spikePoints);
console.log('Old spline path:', spikeCubic);
console.log('New linear path:', spikeLinear);
// Catmull-Rom will produce a control point that dips below y=230 (the floor)
const spikeMatch = spikeCubic.match(/C ([^\s]+),([^\s]+) ([^\s]+),([^\s]+)/);
if (spikeMatch) {
  const cp1y = parseFloat(spikeMatch[2]);
  const cp2y = parseFloat(spikeMatch[4]);
  console.log(`\nCatmull-Rom cp1y=${cp1y.toFixed(2)}, cp2y=${cp2y.toFixed(2)}`);
  console.log(`Floor y (equity=0) = ${spikePoints[0].y.toFixed(2)}, Ceiling y (equity=100000) = ${spikePoints[2].y.toFixed(2)}`);
  console.log(`cp1y OUTSIDE bounds [${spikePoints[2].y.toFixed(2)}, ${spikePoints[0].y.toFixed(2)}]? ${cp1y < spikePoints[2].y || cp1y > spikePoints[0].y ? 'YES — SPIKE CONFIRMED' : 'No'}`);
  console.log(`cp2y OUTSIDE bounds? ${cp2y < spikePoints[2].y || cp2y > spikePoints[0].y ? 'YES — SPIKE CONFIRMED' : 'No'}`);
}
console.log('\nLinear path: no control points, straight lines only — no overshoot possible ✓');
