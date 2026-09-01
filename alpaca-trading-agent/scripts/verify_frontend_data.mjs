/**
 * Non-visual verification script.
 * Replicates apiClient.getPositions() and apiClient.getOrders() exactly as
 * the frontend's APIClient class does it, and prints the parsed data.
 *
 * Also verifies PositionsPage's guard logic:
 *   if (posRes.success && Array.isArray(posRes.data)) setPositions(posRes.data)
 *
 * Run: node scripts/verify_frontend_data.mjs
 */

const BASE_URL = 'http://localhost:8000';

async function request(endpoint) {
  const response = await fetch(BASE_URL + endpoint, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });
  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (e) {
      console.warn(`[API] Non-JSON response from ${endpoint}: ${text.slice(0, 100)}`);
      data = { _raw: text };
    }
  }
  if (!response.ok) {
    const msg = data.detail || data.error || `HTTP ${response.status}`;
    throw new Error(msg);
  }
  return { success: true, data };
}

// ---- Mirror PositionsPage.jsx fetchData() logic exactly ----
const posRes = await request('/api/positions');
const ordRes = await request('/api/orders');
const histRes = await request('/api/portfolio-history?period=1M&timeframe=1D');

console.log('\n========== /api/positions ==========');
console.log('posRes.success:', posRes.success);
console.log('Array.isArray(posRes.data):', Array.isArray(posRes.data));
console.log('posRes.data length:', Array.isArray(posRes.data) ? posRes.data.length : 'N/A (not array)');
console.log('Guard passes (success && isArray):', posRes.success && Array.isArray(posRes.data));
if (posRes.success && Array.isArray(posRes.data)) {
  console.log('setPositions() would be called with:');
  posRes.data.forEach((p, i) => {
    console.log(`  [${i}] symbol=${p.symbol}, qty=${p.qty}, avg_entry_price=${p.avg_entry_price}, `
      + `current_price=${p.current_price}, market_value=${p.market_value}, `
      + `unrealized_pl=${p.unrealized_pl}, unrealized_plpc=${p.unrealized_plpc}`);
    // Replicate the NaN-inducing operations from JSX to confirm they work:
    console.log(`       → Number(p.qty).toLocaleString()         = "${Number(p.qty).toLocaleString()}"`);
    console.log(`       → Number(p.avg_entry_price||0).toFixed(2) = "${Number(p.avg_entry_price||0).toFixed(2)}"`);
    console.log(`       → Number(p.current_price||0).toFixed(2)  = "${Number(p.current_price||0).toFixed(2)}"`);
    console.log(`       → Number(p.market_value||0) formatted     = "${Number(p.market_value||0).toLocaleString(undefined,{minimumFractionDigits:2})}"`);
    const pnl = Number(p.unrealized_pl ?? 0);
    console.log(`       → Math.abs(pnl).toFixed(2)               = "${Math.abs(pnl).toFixed(2)}"`);
    console.log(`       → (Number(p.unrealized_plpc??0)*100).toFixed(2) = "${(Number(p.unrealized_plpc??0)*100).toFixed(2)}"`);
  });
} else {
  console.log('  ⚠️  Guard FAILS — setPositions([]) — positions table would be empty');
  console.log('  Raw posRes.data:', JSON.stringify(posRes.data).slice(0, 200));
}

console.log('\n========== /api/orders ==========');
console.log('ordRes.success:', ordRes.success);
console.log('Array.isArray(ordRes.data):', Array.isArray(ordRes.data));
console.log('ordRes.data length:', Array.isArray(ordRes.data) ? ordRes.data.length : 'N/A (not array)');
console.log('Guard passes (success && isArray):', ordRes.success && Array.isArray(ordRes.data));
if (ordRes.success && Array.isArray(ordRes.data)) {
  console.log('setOrders() would be called with:');
  ordRes.data.forEach((o, i) => {
    console.log(`  [${i}] symbol=${o.symbol}, side=${o.side}, qty=${o.qty}, `
      + `type=${o.type}, status=${o.status}, `
      + `filled_avg_price=${o.filled_avg_price}, submitted_at=${o.submitted_at}`);
    console.log(`       → {ord.symbol}          = "${o.symbol}"`);
    console.log(`       → {ord.side}            = "${o.side}"`);
    console.log(`       → Number(ord.qty)       = "${Number(o.qty).toLocaleString()}"`);
    console.log(`       → {ord.type}            = "${o.type}"`);
    console.log(`       → {ord.status}          = "${o.status}"`);
    console.log(`       → Number(ord.filled_avg_price||0).toFixed(2) = "$${Number(o.filled_avg_price||0).toFixed(2)}"`);
    const submittedAt = o.submitted_at ? new Date(o.submitted_at).toLocaleTimeString() : '—';
    console.log(`       → new Date(ord.submitted_at).toLocaleTimeString() = "${submittedAt}"`);
  });
} else {
  console.log('  ⚠️  Guard FAILS — setOrders([]) — orders table would be empty');
  console.log('  Raw ordRes.data:', JSON.stringify(ordRes.data).slice(0, 200));
}

console.log('\n========== /api/portfolio-history (PnLChart input) ==========');
const h = histRes.data;
console.log('keys:', Object.keys(h));
console.log('timestamp count:', h.timestamp?.length);
console.log('equity values:', h.equity);
console.log('profit_loss values:', h.profit_loss);
