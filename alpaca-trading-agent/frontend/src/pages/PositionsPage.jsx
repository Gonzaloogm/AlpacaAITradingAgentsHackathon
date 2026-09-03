import { useState, useEffect, useMemo } from 'react';
import { apiClient } from '../api/client';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { Wallet, ShoppingCart, RefreshCw, ArrowUpRight, ArrowDownRight, Layers, CheckCircle2, Clock } from 'lucide-react';

export default function PositionsPage() {
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [orderFilter, setOrderFilter] = useState('ALL');

  const fetchData = async () => {
    setLoading(true);
    const [posRes, ordRes] = await Promise.all([
      apiClient.getPositions(),
      apiClient.getOrders(),
    ]);

    if (posRes.success && Array.isArray(posRes.data)) setPositions(posRes.data);
    if (ordRes.success && Array.isArray(ordRes.data)) setOrders(ordRes.data);
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Compute portfolio aggregate metrics
  const summary = useMemo(() => {
    let totalMktVal = 0;
    let totalCostBasis = 0;
    let totalUnrealizedPl = 0;

    positions.forEach((pos) => {
      totalMktVal += Number(pos.market_value || 0);
      totalCostBasis += Number(pos.cost_basis || 0);
      totalUnrealizedPl += Number(pos.unrealized_pl || 0);
    });

    const totalPlPct = totalCostBasis > 0 ? (totalUnrealizedPl / totalCostBasis) * 100 : 0;
    const filledCount = orders.filter((o) => (o.status || '').toLowerCase() === 'filled').length;
    const openCount = orders.filter((o) => ['new', 'partially_filled', 'accepted', 'pending_new'].includes((o.status || '').toLowerCase())).length;

    return {
      totalMktVal,
      totalUnrealizedPl,
      totalPlPct,
      openCount,
      filledCount,
    };
  }, [positions, orders]);

  // Filtered orders
  const filteredOrders = useMemo(() => {
    if (orderFilter === 'FILLED') {
      return orders.filter((o) => (o.status || '').toLowerCase() === 'filled');
    }
    if (orderFilter === 'OPEN') {
      return orders.filter((o) => ['new', 'partially_filled', 'accepted', 'pending_new'].includes((o.status || '').toLowerCase()));
    }
    return orders;
  }, [orders, orderFilter]);

  const isPositivePl = summary.totalUnrealizedPl >= 0;

  return (
    <div className="space-y-8 pb-16 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[#12141C] border border-white/5 rounded-xl p-6 shadow-lg">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
            <Wallet className="text-blue-500" /> Portfolio Holdings & Orders
          </h1>
          <p className="text-xs font-mono text-slate-400 mt-1">
            Real-time equity exposure and order management synced with Alpaca Paper Trading
          </p>
        </div>
        <button
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 bg-white/[0.04] hover:bg-white/[0.08] rounded-xl text-xs font-mono font-bold text-slate-200 transition-all border border-white/5 shadow-sm"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh Data
        </button>
      </div>

      {/* Aggregate KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-[#12141C] border border-white/5 rounded-xl p-5 shadow-lg">
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 block mb-1">
            Total Position Value
          </span>
          <div className="text-2xl font-mono font-black text-white">
            ${summary.totalMktVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="mt-2 text-xs font-mono text-slate-500">
            Across {positions.length} active position{positions.length === 1 ? '' : 's'}
          </div>
        </div>

        <div className="bg-[#12141C] border border-white/5 rounded-xl p-5 shadow-lg">
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 block mb-1">
            Unrealized P&L
          </span>
          <div className={`text-2xl font-mono font-black flex items-baseline gap-1.5 ${isPositivePl ? 'text-emerald-400' : 'text-rose-400'}`}>
            <span>{isPositivePl ? '+' : ''}${summary.totalUnrealizedPl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            <span className="text-xs font-bold font-mono opacity-80">
              ({isPositivePl ? '+' : ''}{summary.totalPlPct.toFixed(2)}%)
            </span>
          </div>
          <div className="mt-2 text-xs font-mono text-slate-500">
            Floating paper trading return
          </div>
        </div>

        <div className="bg-[#12141C] border border-white/5 rounded-xl p-5 shadow-lg">
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 block mb-1">
            Active Holdings
          </span>
          <div className="text-2xl font-mono font-black text-blue-400">
            {positions.length}
          </div>
          <div className="mt-2 text-xs font-mono text-slate-500">
            Equities currently long/short
          </div>
        </div>

        <div className="bg-[#12141C] border border-white/5 rounded-xl p-5 shadow-lg">
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 block mb-1">
            Total Orders
          </span>
          <div className="text-2xl font-mono font-black text-white">
            {orders.length}
          </div>
          <div className="mt-2 text-xs font-mono text-slate-500 flex items-center gap-2">
            <span className="text-emerald-400">{summary.filledCount} filled</span> · <span className="text-slate-400">{summary.openCount} open</span>
          </div>
        </div>
      </div>

      {/* Active Positions Table */}
      <div className="bg-[#12141C] border border-white/5 rounded-xl p-6 shadow-lg overflow-hidden">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-2">
            <Layers size={16} className="text-blue-400" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              Active Positions
            </h2>
          </div>
          <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
            {positions.length} Assets
          </span>
        </div>

        {loading && positions.length === 0 ? (
          <div className="h-36 flex flex-col items-center justify-center">
            <LoadingSpinner size="md" />
            <span className="mt-2 text-xs font-mono text-slate-500">Loading open positions...</span>
          </div>
        ) : positions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-slate-500 border-b border-white/5 text-[11px] font-mono uppercase tracking-wider">
                  <th className="pb-3 font-semibold">Symbol</th>
                  <th className="pb-3 font-semibold">Side</th>
                  <th className="pb-3 font-semibold text-right">Shares</th>
                  <th className="pb-3 font-semibold text-right">Avg Entry</th>
                  <th className="pb-3 font-semibold text-right">Current Price</th>
                  <th className="pb-3 font-semibold text-right">Market Value</th>
                  <th className="pb-3 font-semibold text-right">Unrealized P&L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {positions.map((pos, idx) => {
                  const pnl = Number(pos.unrealized_pl ?? 0);
                  const isPos = pnl >= 0;
                  const plpc = Number(pos.unrealized_plpc ?? 0) * 100;
                  return (
                    <tr key={idx} className="hover:bg-white/[0.02] transition-colors group">
                      <td className="py-4">
                        <div className="font-mono font-black text-white text-base">{pos.symbol}</div>
                        <div className="text-[10px] font-mono text-slate-500">{pos.exchange || 'US_EQUITY'}</div>
                      </td>
                      <td className="py-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                          (pos.side || 'long').toLowerCase() === 'long'
                            ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                            : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        }`}>
                          {pos.side || 'long'}
                        </span>
                      </td>
                      <td className="py-4 text-right font-mono text-sm text-slate-200">
                        {Number(pos.qty).toLocaleString()}
                      </td>
                      <td className="py-4 text-right font-mono text-sm text-slate-400">
                        ${Number(pos.avg_entry_price || 0).toFixed(2)}
                      </td>
                      <td className="py-4 text-right font-mono text-sm text-white font-bold">
                        ${Number(pos.current_price || 0).toFixed(2)}
                      </td>
                      <td className="py-4 text-right font-mono text-sm font-bold text-white">
                        ${Number(pos.market_value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="py-4 text-right">
                        <div className={`flex items-center justify-end gap-1 font-mono text-sm font-bold ${isPos ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {isPos ? <ArrowUpRight size={15} /> : <ArrowDownRight size={15} />}
                          <span>${Math.abs(pnl).toFixed(2)}</span>
                          <span className="text-xs opacity-75 font-normal ml-0.5">({isPos ? '+' : ''}{plpc.toFixed(2)}%)</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-12 text-center text-slate-500 text-sm font-mono">
            No active positions in paper trading account. Start the strategy to open positions.
          </div>
        )}
      </div>

      {/* Recent Orders Section */}
      <div className="bg-[#12141C] border border-white/5 rounded-xl p-6 shadow-lg overflow-hidden">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-4">
          <div className="flex items-center gap-2">
            <ShoppingCart size={16} className="text-blue-400" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              Orders History
            </h2>
          </div>

          <div className="flex items-center gap-1.5 bg-[#0D0F14] p-1 rounded-lg border border-white/5">
            {[
              { label: 'All', value: 'ALL', count: orders.length },
              { label: 'Filled', value: 'FILLED', count: summary.filledCount },
              { label: 'Open', value: 'OPEN', count: summary.openCount },
            ].map((tab) => (
              <button
                key={tab.value}
                onClick={() => setOrderFilter(tab.value)}
                className={`px-3 py-1 rounded text-xs font-mono font-bold uppercase transition-all ${
                  orderFilter === tab.value
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {tab.label} ({tab.count})
              </button>
            ))}
          </div>
        </div>

        {loading && orders.length === 0 ? (
          <div className="h-36 flex flex-col items-center justify-center">
            <LoadingSpinner size="md" />
            <span className="mt-2 text-xs font-mono text-slate-500">Loading orders...</span>
          </div>
        ) : filteredOrders.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-slate-500 border-b border-white/5 text-[11px] font-mono uppercase tracking-wider">
                  <th className="pb-3 font-semibold">Symbol</th>
                  <th className="pb-3 font-semibold">Action</th>
                  <th className="pb-3 font-semibold text-right">Shares</th>
                  <th className="pb-3 font-semibold text-center">Type</th>
                  <th className="pb-3 font-semibold text-center">Status</th>
                  <th className="pb-3 font-semibold text-right">Filled Price</th>
                  <th className="pb-3 font-semibold text-right">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredOrders.map((ord, idx) => (
                  <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-4 font-mono font-black text-white">{ord.symbol}</td>
                    <td className="py-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                        (ord.side || '').toLowerCase() === 'buy'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>
                        {ord.side}
                      </span>
                    </td>
                    <td className="py-4 text-right font-mono text-sm text-slate-200">
                      {Number(ord.qty || 0).toLocaleString()}
                    </td>
                    <td className="py-4 text-center text-xs font-mono uppercase text-slate-400">{ord.type}</td>
                    <td className="py-4 text-center">
                      <span className={`px-2.5 py-1 rounded-md text-[10px] uppercase font-bold tracking-wider font-mono border ${
                        (ord.status || '').toLowerCase() === 'filled'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : 'bg-white/5 text-slate-300 border-white/10'
                      }`}>
                        {ord.status}
                      </span>
                    </td>
                    <td className="py-4 text-right font-mono text-sm text-slate-300">
                      ${Number(ord.filled_avg_price || 0).toFixed(2)}
                    </td>
                    <td className="py-4 text-right font-mono text-xs text-slate-500">
                      {ord.submitted_at ? new Date(ord.submitted_at).toLocaleTimeString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-12 text-center text-slate-500 text-sm font-mono">
            No orders found matching the selected filter.
          </div>
        )}
      </div>
    </div>
  );
}
