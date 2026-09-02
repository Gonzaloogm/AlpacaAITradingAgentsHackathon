import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { Wallet, ShoppingCart, RefreshCw, ArrowUpRight, ArrowDownRight } from 'lucide-react';

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

    if (posRes.success && Array.isArray(posRes.data)) setPositions(posRes.data);
    if (ordRes.success && Array.isArray(ordRes.data)) setOrders(ordRes.data);
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  return (
    <div className="space-y-8 pb-12 font-sans">
      <div className="flex justify-between items-center bg-[#12141C] border border-white/5 rounded-xl p-6 shadow-lg">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
            <Wallet className="text-blue-500" /> Portfolio Holdings
          </h1>
          <p className="text-sm text-slate-400 mt-1">Manage active positions and order history</p>
        </div>
        <button onClick={fetchData} className="flex items-center gap-2 px-4 py-2.5 bg-white/[0.03] hover:bg-white/[0.08] rounded-xl text-sm font-bold text-slate-200 transition-all border border-white/5 shadow-sm">
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      <div className="bg-[#12141C] border border-white/5 rounded-xl p-6 shadow-lg overflow-hidden">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-4 flex justify-between">
          Active Positions <span className="text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">{positions.length}</span>
        </h2>
        {loading && positions.length === 0 ? (
          <div className="h-32 flex items-center justify-center"><LoadingSpinner size="md" /></div>
        ) : positions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-slate-500 border-b border-white/5 text-xs uppercase tracking-wider">
                  <th className="pb-3 font-semibold">Symbol</th>
                  <th className="pb-3 font-semibold">Side</th>
                  <th className="pb-3 font-semibold text-right">Qty</th>
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
                  return (
                    <tr key={idx} className="hover:bg-white/[0.02] transition-colors group">
                      <td className="py-4 font-black text-white">{pos.symbol}</td>
                      <td className="py-4 text-xs font-bold uppercase text-slate-400">{pos.side || 'long'}</td>
                      <td className="py-4 text-right font-mono text-sm text-slate-200">{Number(pos.qty).toLocaleString()}</td>
                      <td className="py-4 text-right font-mono text-sm text-slate-400">${Number(pos.avg_entry_price || 0).toFixed(2)}</td>
                      <td className="py-4 text-right font-mono text-sm text-white">${Number(pos.current_price || 0).toFixed(2)}</td>
                      <td className="py-4 text-right font-mono text-sm font-bold text-white">${Number(pos.market_value || 0).toLocaleString(undefined, {minimumFractionDigits:2})}</td>
                      <td className={`py-4 text-right font-mono text-sm font-bold flex items-center justify-end gap-1 ${isPos ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {isPos ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                        ${Math.abs(pnl).toFixed(2)}
                        <span className="text-xs opacity-75 ml-1">({(Number(pos.unrealized_plpc ?? 0) * 100).toFixed(2)}%)</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-10 text-center text-slate-500 text-sm">No open positions.</div>
        )}
      </div>

      <div className="bg-[#12141C] border border-white/5 rounded-xl p-6 shadow-lg overflow-hidden">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-4 flex justify-between">
          Recent Orders <span className="text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">{orders.length}</span>
        </h2>
        {loading && orders.length === 0 ? (
          <div className="h-32 flex items-center justify-center"><LoadingSpinner size="md" /></div>
        ) : orders.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-slate-500 border-b border-white/5 text-xs uppercase tracking-wider">
                  <th className="pb-3 font-semibold">Symbol</th>
                  <th className="pb-3 font-semibold">Action</th>
                  <th className="pb-3 font-semibold text-right">Qty</th>
                  <th className="pb-3 font-semibold text-center">Type</th>
                  <th className="pb-3 font-semibold text-center">Status</th>
                  <th className="pb-3 font-semibold text-right">Filled Price</th>
                  <th className="pb-3 font-semibold text-right">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {orders.map((ord, idx) => (
                  <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-4 font-black text-white">{ord.symbol}</td>
                    <td className={`py-4 text-xs font-bold uppercase ${ord.side === 'buy' ? 'text-emerald-400' : 'text-rose-400'}`}>{ord.side}</td>
                    <td className="py-4 text-right font-mono text-sm text-slate-200">{Number(ord.qty).toLocaleString()}</td>
                    <td className="py-4 text-center text-xs font-bold uppercase text-slate-500">{ord.type}</td>
                    <td className="py-4 text-center">
                      <span className="px-2.5 py-1 rounded-md bg-white/5 text-slate-300 border border-white/10 text-[10px] uppercase font-bold tracking-wider">
                        {ord.status}
                      </span>
                    </td>
                    <td className="py-4 text-right font-mono text-sm text-slate-300">${Number(ord.filled_avg_price || 0).toFixed(2)}</td>
                    <td className="py-4 text-right font-mono text-xs text-slate-500">
                      {ord.submitted_at ? new Date(ord.submitted_at).toLocaleTimeString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-10 text-center text-slate-500 text-sm">No recent orders.</div>
        )}
      </div>
    </div>
  );
}
