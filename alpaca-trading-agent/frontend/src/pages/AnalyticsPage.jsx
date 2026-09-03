import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import MetricCard from '../components/ui/MetricCard';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { BarChart2, TrendingDown, Target, Activity } from 'lucide-react';

export default function AnalyticsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await apiClient.getAnalytics();
        if (res.success) {
          setData(res.data);
        } else {
          setError(res.error || 'Failed to load analytics data.');
        }
      } catch {
        setError('Network error loading analytics.');
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="h-[60vh] flex flex-col items-center justify-center">
        <LoadingSpinner />
        <span className="mt-4 text-slate-500 font-mono text-sm uppercase tracking-widest">Crunching numbers...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-[60vh] flex items-center justify-center">
        <div className="text-rose-400 font-mono">{error}</div>
      </div>
    );
  }

  const { win_rate, sharpe_ratio, max_drawdown, trade_count, is_mock } = data;

  const renderValue = (val, formatter) => {
    if (val === null || val === undefined) return 'N/A';
    return formatter(val);
  };

  return (
    <div className="space-y-8 pb-12 font-sans">
      <div className="flex items-end justify-between border-b border-white/5 pb-6">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-white mb-2">Performance Analytics</h1>
          <p className="text-slate-400 font-mono text-sm">Advanced metrics computed from your portfolio history.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <MetricCard
          title="Sharpe Ratio"
          icon={<BarChart2 size={24} />}
          isMock={is_mock}
          value={renderValue(sharpe_ratio?.value, (v) => v.toFixed(2))}
          insufficientData={sharpe_ratio?.insufficient_data}
          badge={
            sharpe_ratio?.value >= 1.5
              ? { text: 'Optimal (>1.5)', color: 'emerald' }
              : { text: 'Normal (>1.0)', color: 'blue' }
          }
          subtitle="Annualized risk-adjusted excess return (Risk-free: 4%)"
        />

        <MetricCard
          title="Win Rate"
          icon={<Target size={24} />}
          isMock={is_mock}
          value={renderValue(win_rate?.value, (v) => `${v.toFixed(1)}%`)}
          insufficientData={win_rate?.insufficient_data}
          progress={win_rate?.value || 0}
          badge={
            win_rate?.value >= 60
              ? { text: 'High (>60%)', color: 'emerald' }
              : { text: 'Balanced', color: 'blue' }
          }
          subtitle="% of round-trip trades closing with positive realized P&L"
        />

        <MetricCard
          title="Max Drawdown"
          icon={<TrendingDown size={24} />}
          isMock={is_mock}
          value={renderValue(max_drawdown?.value, (v) => `${v.toFixed(2)}%`)}
          insufficientData={max_drawdown?.insufficient_data}
          badge={
            Math.abs(max_drawdown?.value || 0) <= 5
              ? { text: 'Controlled (<5%)', color: 'emerald' }
              : { text: 'Elevated Risk', color: 'rose' }
          }
          subtitle="Largest historical peak-to-trough equity decline"
        />
      </div>

      {/* Strategy Engine & Statistics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#12141C] border border-white/5 rounded-xl p-6 shadow-lg">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200 mb-6 flex items-center gap-2">
            <Activity size={16} className="text-blue-400" />
            Execution & Account Telemetry
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-6">
            <div>
              <div className="text-slate-500 text-[10px] font-mono font-bold uppercase tracking-wider mb-1">
                Completed Trades
              </div>
              <div className="text-2xl font-mono font-bold text-white">{trade_count}</div>
              <div className="text-[11px] text-slate-500 mt-1">Filled on Alpaca</div>
            </div>
            <div>
              <div className="text-slate-500 text-[10px] font-mono font-bold uppercase tracking-wider mb-1">
                Telemetry Mode
              </div>
              <div className="text-sm font-mono font-bold text-slate-200 mt-1">
                {is_mock ? 'Mock Fallback' : 'Live Alpaca MCP'}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                {is_mock ? 'Subprocess offline' : 'Real-time JSON-RPC'}
              </div>
            </div>
            <div>
              <div className="text-slate-500 text-[10px] font-mono font-bold uppercase tracking-wider mb-1">
                Active AI Engine
              </div>
              <div className="text-sm font-mono font-bold text-blue-400 mt-1">
                Gemini 3.6 Flash
              </div>
              <div className="text-[11px] text-slate-500 mt-1">Claude fallback ready</div>
            </div>
          </div>
        </div>

        <div className="bg-[#12141C] border border-white/5 rounded-xl p-6 shadow-lg">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200 mb-6 flex items-center gap-2">
            <Target size={16} className="text-cyan-400" />
            Strategy Parameters (Statistical Arbitrage)
          </h3>
          <div className="space-y-3 font-mono text-xs">
            <div className="flex justify-between items-center py-1.5 border-b border-white/[0.04]">
              <span className="text-slate-400">Equity Pair:</span>
              <span className="text-white font-bold">SPY (S&P 500) / QQQ (Nasdaq 100)</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-white/[0.04]">
              <span className="text-slate-400">Rolling Window Lookback:</span>
              <span className="text-white font-bold">20 daily bars</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-white/[0.04]">
              <span className="text-slate-400">Z-Score Entry Threshold:</span>
              <span className="text-emerald-400 font-bold">±2.0 σ</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-white/[0.04]">
              <span className="text-slate-400">Z-Score Exit Threshold:</span>
              <span className="text-blue-400 font-bold">±0.5 σ</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
