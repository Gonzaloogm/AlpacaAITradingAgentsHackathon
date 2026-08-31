import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { Wallet, ShoppingCart, RefreshCw, ArrowUpRight, ArrowDownRight, Layers } from 'lucide-react';

export default function PositionsPage() {
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    const [posRes, ordRes] = await Promise.all([
      apiClient.getPositions(),
      apiClient.getOrders(),
    ]);

    if (posRes.success && Array.isArray(posRes.data)) {
      setPositions(posRes.data);
    }
    if (ordRes.success && Array.isArray(ordRes.data)) {
      setOrders(ordRes.data);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-[#161920] border border-white/5 rounded-2xl p-6">
        <div>
          <div className="flex items-center gap-2">
            <Wallet size={20} className="text-[#00BFA5]" />
            <h1 className="text-xl font-bold text-white tracking-wide">Positions & Orders Management</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Live portfolio holdings and trade execution order history via Alpaca API & MCP.
          </p>
        </div>

        <button
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-xl text-xs font-mono font-bold text-slate-300 transition-all border border-white/5"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh Data
        </button>
      </div>

      {/* Open Positions Table */}
      <div className="bg-[#11141D] border border-white/5 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-white/5 pb-3">
          <div className="flex items-center gap-2">
            <Layers size={16} className="text-[#00BFA5]" />
            <h2 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-widest">Active Open Positions</h2>
          </div>
          <span className="text-[10px] font-mono text-slate-500 font-bold">{positions.length} Active Position(s)</span>
        </div>

        {loading && positions.length === 0 ? (
          <div className="h-40 flex items-center justify-center">
            <LoadingSpinner size="md" />
          </div>
        ) : positions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="text-slate-500 border-b border-white/5 text-[10px] uppercase">
                  <th className="pb-3">Symbol</th>
                  <th className="pb-3">Side</th>
                  <th className="pb-3">Qty</th>
                  <th className="pb-3">Avg Entry</th>
                  <th className="pb-3">Current Price</th>
                  <th className="pb-3">Market Value</th>
                  <th className="pb-3 text-right">Unrealized P&L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {positions.map((pos, idx) => {
                  const pnl = pos.unrealized_pl ?? 0;
                  const isPos = pnl >= 0;
                  return (
                    <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                      <td className="py-4 font-bold text-white flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-[#00BFA5]" />
                        {pos.symbol}
                      </td>
                      <td className="py-4 uppercase text-slate-400">{pos.side || 'long'}</td>
                      <td className="py-4 font-bold text-slate-200">{pos.qty}</td>
                      <td className="py-4 text-slate-400">${Number(pos.avg_entry_price || 0).toFixed(2)}</td>
                      <td className="py-4 text-slate-200">${Number(pos.current_price || pos.avg_entry_price || 0).toFixed(2)}</td>
                      <td className="py-4 font-bold text-white">${Number(pos.market_value || 0).toFixed(2)}</td>
                      <td className={`py-4 text-right font-bold flex items-center justify-end gap-1 ${isPos ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {isPos ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                        ${pnl.toFixed(2)} ({((pos.unrealized_plpc ?? 0) * 100).toFixed(2)}%)
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-slate-500 italic text-xs font-mono">
            No open positions currently in your Alpaca paper account.
          </div>
        )}
      </div>

      {/* Orders History Table */}
      <div className="bg-[#11141D] border border-white/5 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-white/5 pb-3">
          <div className="flex items-center gap-2">
            <ShoppingCart size={16} className="text-[#0091EA]" />
            <h2 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-widest">Recent Orders History</h2>
          </div>
          <span className="text-[10px] font-mono text-slate-500 font-bold">{orders.length} Order(s)</span>
        </div>

        {loading && orders.length === 0 ? (
          <div className="h-40 flex items-center justify-center">
            <LoadingSpinner size="md" />
          </div>
        ) : orders.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="text-slate-500 border-b border-white/5 text-[10px] uppercase">
                  <th className="pb-3">Order ID</th>
                  <th className="pb-3">Symbol</th>
                  <th className="pb-3">Side</th>
                  <th className="pb-3">Qty</th>
                  <th className="pb-3">Type</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3">Filled Price</th>
                  <th className="pb-3 text-right">Submitted At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {orders.map((ord, idx) => (
                  <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-4 text-slate-400 font-mono text-[11px]">{ord.client_order_id || ord.id || '—'}</td>
                    <td className="py-4 font-bold text-white">{ord.symbol}</td>
                    <td className={`py-4 font-bold uppercase ${ord.side === 'buy' ? 'text-emerald-400' : 'text-rose-400'}`}>{ord.side}</td>
                    <td className="py-4 text-slate-200">{ord.qty}</td>
                    <td className="py-4 text-slate-400 uppercase">{ord.type}</td>
                    <td className="py-4">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] uppercase font-bold">
                        {ord.status}
                      </span>
                    </td>
                    <td className="py-4 text-slate-200">${Number(ord.filled_avg_price || 0).toFixed(2)}</td>
                    <td className="py-4 text-right text-slate-400 text-[11px]">
                      {ord.submitted_at ? new Date(ord.submitted_at).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-slate-500 italic text-xs font-mono">
            No recent orders recorded.
          </div>
        )}
      </div>
    </div>
  );
}
