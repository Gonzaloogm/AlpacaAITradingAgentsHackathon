import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { Terminal, ShieldCheck, ArrowRight, RefreshCw, Cpu, Layers } from 'lucide-react';

export default function ReasoningLogPage() {
  const [logs, setLogs] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    setLoading(true);
    const [logRes, sumRes] = await Promise.all([
      apiClient.getReasoningLog(50, 0),
      apiClient.getReasoningSummary(),
    ]);

    if (logRes.success && Array.isArray(logRes.data)) {
      setLogs(logRes.data);
    }
    if (sumRes.success) {
      setSummary(sumRes.data);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-[#161920] border border-white/5 rounded-2xl p-6">
        <div>
          <div className="flex items-center gap-2">
            <Terminal size={20} className="text-[#00BFA5]" />
            <h1 className="text-xl font-bold text-white tracking-wide">Reasoning Transparency Log</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Full audit trail of AI decision cycles: Market Signal → LLM Reasoning → MCP Tools Called → Order Executed → P&L Impact.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-xl text-xs font-mono font-bold text-slate-300 transition-all border border-white/5"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh Log
        </button>
      </div>

      {/* Summary Stats */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-[#11141D] border border-white/5 p-4 rounded-xl">
            <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Total Cycles</span>
            <div className="text-xl font-bold text-white mt-1 font-mono">{summary.total_entries || logs.length}</div>
          </div>
          <div className="bg-[#11141D] border border-white/5 p-4 rounded-xl">
            <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Total Trades Executed</span>
            <div className="text-xl font-bold text-[#00BFA5] mt-1 font-mono">{summary.total_trades || 0}</div>
          </div>
          <div className="bg-[#11141D] border border-white/5 p-4 rounded-xl">
            <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Win Rate</span>
            <div className="text-xl font-bold text-[#0091EA] mt-1 font-mono">{summary.win_rate ? `${(summary.win_rate * 100).toFixed(1)}%` : '100%'}</div>
          </div>
          <div className="bg-[#11141D] border border-white/5 p-4 rounded-xl">
            <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Total Realized P&L</span>
            <div className="text-xl font-bold text-emerald-400 mt-1 font-mono">${(summary.total_pnl || 0).toFixed(2)}</div>
          </div>
        </div>
      )}

      {/* Reasoning Cycles Table / Cards */}
      {loading && logs.length === 0 ? (
        <div className="h-64 flex flex-col items-center justify-center">
          <LoadingSpinner size="lg" />
          <span className="mt-3 text-xs font-mono text-slate-400">Loading reasoning audit logs...</span>
        </div>
      ) : logs.length > 0 ? (
        <div className="space-y-4">
          {logs.map((entry) => (
            <div key={entry.cycle_id} className="bg-[#11141D] border border-white/5 rounded-2xl p-6 space-y-4 shadow-xl">
              {/* Header line */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-white/5 pb-3">
                <div className="flex items-center gap-3">
                  <span className="px-3 py-1 bg-[#0091EA]/10 border border-[#0091EA]/30 text-[#0091EA] font-mono font-bold text-xs rounded-lg">
                    Cycle #{entry.cycle_id}
                  </span>
                  <span className="text-xs font-mono text-slate-400">
                    {new Date(entry.timestamp).toLocaleString()}
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-mono text-slate-500 uppercase">Provider: {entry.decision?.provider || 'gemini'}</span>
                  <span className={`px-3 py-1 rounded-lg text-xs font-mono font-bold uppercase tracking-wider ${
                    entry.decision?.action === 'buy' ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' :
                    entry.decision?.action === 'sell' ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30' :
                    'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                  }`}>
                    {entry.decision?.action?.toUpperCase() || 'HOLD'} (Confidence: {(entry.decision?.confidence ?? 0.5) * 100}%)
                  </span>
                </div>
              </div>

              {/* Chain of thought & reasoning */}
              <div>
                <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest block mb-1">
                  AI Chain-of-Thought Reasoning
                </span>
                <p className="text-sm text-slate-200 font-sans leading-relaxed bg-[#161920] p-4 rounded-xl border border-white/5">
                  {entry.llm_reasoning || entry.decision?.reasoning || 'No explicit reasoning provided.'}
                </p>
              </div>

              {/* Market Signal & MCP Tools Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                {/* Market Signal */}
                <div className="bg-[#161920] p-4 rounded-xl border border-white/5">
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest block mb-2">
                    Market Signal Input
                  </span>
                  <pre className="text-slate-300 text-[11px] overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(entry.market_data || entry.market_signal, null, 2)}
                  </pre>
                </div>

                {/* MCP Tools Executed */}
                <div className="bg-[#161920] p-4 rounded-xl border border-white/5">
                  <span className="text-[9px] font-bold text-[#00BFA5] uppercase tracking-widest block mb-2">
                    Alpaca MCP Tools Executed
                  </span>
                  {entry.mcp_tools_called && entry.mcp_tools_called.length > 0 ? (
                    <div className="space-y-2">
                      {entry.mcp_tools_called.map((tool, tid) => (
                        <div key={tid} className="bg-white/5 p-2 rounded border border-white/5 text-[11px]">
                          <span className="text-[#00BFA5] font-bold">{tool.name}</span>
                          <span className="text-slate-400 ml-2">args: {JSON.stringify(tool.args || tool.input)}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <span className="text-slate-500 italic text-[11px]">No MCP tools called during this cycle.</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-[#11141D] border border-white/5 rounded-2xl p-12 text-center">
          <Terminal size={32} className="text-slate-600 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider font-mono">No Audit Logs Recorded</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            Start the autonomous trading strategy loop from the Dashboard to generate real-time AI decision cycles.
          </p>
        </div>
      )}
    </div>
  );
}
