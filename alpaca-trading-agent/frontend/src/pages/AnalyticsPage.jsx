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
      } catch (err) {
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
          value={renderValue(sharpe_ratio?.value, v => v.toFixed(2))}
          insufficientData={sharpe_ratio?.insufficient_data}
          subtitle="Annualized risk-adjusted return (Risk-free rate: 4%)"
        />
        
        <MetricCard
          title="Win Rate"
          icon={<Target size={24} />}
          isMock={is_mock}
          value={renderValue(win_rate?.value, v => `${v.toFixed(1)}%`)}
          insufficientData={win_rate?.insufficient_data}
          subtitle="% of closed trades with positive realized P&L"
        />
        
        <MetricCard
          title="Max Drawdown"
          icon={<TrendingDown size={24} />}
          isMock={is_mock}
          value={renderValue(max_drawdown?.value, v => `${v.toFixed(2)}%`)}
          insufficientData={max_drawdown?.insufficient_data}
          subtitle="Largest peak-to-trough equity decline"
        />
      </div>

      <div className="bg-[#12141C] border border-white/5 rounded-xl p-6 shadow-lg">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-6 flex items-center gap-2">
          <Activity size={16} className="text-slate-500" />
          Trade Statistics
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
          <div>
            <div className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">Total Trades</div>
            <div className="text-2xl font-mono text-slate-200">{trade_count}</div>
          </div>
          <div>
            <div className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">Data Mode</div>
            <div className="text-sm font-mono text-slate-200 mt-2">{is_mock ? 'Mock Fallback' : 'Live Alpaca MCP'}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
