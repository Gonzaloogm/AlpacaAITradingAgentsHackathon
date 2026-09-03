import { useState, useEffect, useMemo } from 'react';
import { apiClient } from '../api/client';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { Terminal, RefreshCw, Cpu, ChevronDown, ChevronUp, Wrench, CheckCircle, Search, Filter } from 'lucide-react';

export default function ReasoningLogPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterAction, setFilterAction] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedCycles, setExpandedCycles] = useState(new Set());

  const fetchLogs = async () => {
    setLoading(true);
    const res = await apiClient.getReasoningLog(100);
    if (res.success && Array.isArray(res.data)) {
      setLogs(res.data);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const toggleExpand = (cycleId) => {
    setExpandedCycles((prev) => {
      const next = new Set(prev);
      if (next.has(cycleId)) next.delete(cycleId);
      else next.add(cycleId);
      return next;
    });
  };

  // Summary Metrics
  const stats = useMemo(() => {
    let buys = 0;
    let sells = 0;
    let holds = 0;
    let totalTools = 0;

    logs.forEach((log) => {
      const act = (log.decision?.action || 'HOLD').toUpperCase();
      if (act === 'BUY') buys++;
      else if (act === 'SELL') sells++;
      else holds++;

      if (Array.isArray(log.mcp_tools_called)) {
        totalTools += log.mcp_tools_called.length;
      }
    });

    return { total: logs.length, buys, sells, holds, totalTools };
  }, [logs]);

  // Filtered logs
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const action = (log.decision?.action || 'HOLD').toUpperCase();
      if (filterAction !== 'ALL' && action !== filterAction) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const cycleText = String(log.cycle_id || '');
        const reasoning = String(log.llm_reasoning || log.decision?.reasoning || '').toLowerCase();
        const provider = String(log.decision?.provider || '').toLowerCase();
        return cycleText.includes(q) || reasoning.includes(q) || provider.includes(q);
      }
      return true;
    });
  }, [logs, filterAction, searchQuery]);

  return (
    <div className="space-y-6 pb-16 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#12141C] border border-white/5 rounded-xl p-6 shadow-lg">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg border border-blue-500/20">
              <Terminal size={22} />
            </div>
            <div>
              <h1 className="text-2xl font-black text-white tracking-tight">Reasoning Transparency Log</h1>
              <p className="text-xs font-mono text-slate-400 mt-0.5">
                Complete audit trail: Market Signals → LLM Reasoning → MCP Tools Invocations → Executions
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={fetchLogs}
          className="flex items-center gap-2 px-4 py-2 bg-white/[0.04] hover:bg-white/[0.08] rounded-xl text-xs font-mono font-bold text-slate-200 transition-all border border-white/5 shadow-sm"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh Trail
        </button>
      </div>

      {/* KPI Stats Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="bg-[#12141C] border border-white/5 rounded-xl p-4">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-bold">Total Cycles</div>
          <div className="text-2xl font-mono font-black text-white mt-1">{stats.total}</div>
        </div>
        <div className="bg-[#12141C] border border-white/5 rounded-xl p-4">
          <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-bold">Buy Signals</div>
          <div className="text-2xl font-mono font-black text-emerald-400 mt-1">{stats.buys}</div>
        </div>
        <div className="bg-[#12141C] border border-white/5 rounded-xl p-4">
          <div className="text-[10px] font-mono uppercase tracking-wider text-rose-400 font-bold">Sell Signals</div>
          <div className="text-2xl font-mono font-black text-rose-400 mt-1">{stats.sells}</div>
        </div>
        <div className="bg-[#12141C] border border-white/5 rounded-xl p-4">
          <div className="text-[10px] font-mono uppercase tracking-wider text-amber-400 font-bold">Hold Decisions</div>
          <div className="text-2xl font-mono font-black text-amber-400 mt-1">{stats.holds}</div>
        </div>
        <div className="bg-[#12141C] border border-white/5 rounded-xl p-4 col-span-2 sm:col-span-1">
          <div className="text-[10px] font-mono uppercase tracking-wider text-cyan-400 font-bold">MCP Tool Calls</div>
          <div className="text-2xl font-mono font-black text-cyan-400 mt-1">{stats.totalTools}</div>
        </div>
      </div>

      {/* Filters & Search Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-[#12141C] border border-white/5 rounded-xl p-3">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <Filter size={14} className="text-slate-500 ml-2 mr-1" />
          {[
            { label: 'All', value: 'ALL', count: stats.total },
            { label: 'Buy', value: 'BUY', count: stats.buys },
            { label: 'Sell', value: 'SELL', count: stats.sells },
            { label: 'Hold', value: 'HOLD', count: stats.holds },
          ].map((tab) => (
            <button
              key={tab.value}
              onClick={() => setFilterAction(tab.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold uppercase transition-all flex items-center gap-1.5 ${
                filterAction === tab.value
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <span>{tab.label}</span>
              <span className="text-[10px] opacity-70">({tab.count})</span>
            </button>
          ))}
        </div>

        <div className="relative min-w-[220px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by reasoning or cycle..."
            className="w-full bg-[#0D0F14] border border-white/10 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono"
          />
        </div>
      </div>

      {/* Logs List */}
      <div className="bg-[#12141C] border border-white/5 rounded-xl shadow-lg overflow-hidden">
        {loading && logs.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center">
            <LoadingSpinner size="md" />
            <span className="mt-3 font-mono text-xs text-slate-500">Loading audit log entries...</span>
          </div>
        ) : filteredLogs.length > 0 ? (
          <div className="divide-y divide-white/5">
            {filteredLogs.map((log) => {
              const cycleId = log.cycle_id;
              const isExpanded = expandedCycles.has(cycleId);
              const action = (log.decision?.action || 'HOLD').toUpperCase();
              const confidence = log.decision?.confidence ? Math.round(Number(log.decision.confidence) * 100) : null;
              const provider = log.decision?.provider || 'gemini';
              const mcpTools = Array.isArray(log.mcp_tools_called) ? log.mcp_tools_called : [];
              const orders = Array.isArray(log.orders_placed) ? log.orders_placed : [];

              return (
                <div key={cycleId} className="p-6 hover:bg-white/[0.015] transition-colors space-y-4">
                  {/* Card Top Row */}
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg border border-blue-500/20">
                        <Cpu size={16} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                            Cycle #{cycleId}
                          </h3>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-slate-400 border border-white/10">
                            {provider === 'gemini' ? 'Gemini 3.6 Flash' : 'Claude 3.5 Sonnet'}
                          </span>
                        </div>
                        <p className="text-[11px] font-mono text-slate-500 mt-0.5">
                          {log.timestamp ? new Date(log.timestamp).toLocaleString() : 'Timestamp N/A'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {confidence !== null && (
                        <div className="flex items-center gap-2 bg-white/[0.03] px-2.5 py-1 rounded-lg border border-white/5 text-xs font-mono">
                          <span className="text-slate-400">Confidence:</span>
                          <span className="text-blue-400 font-bold">{confidence}%</span>
                          <div className="w-12 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-blue-500 rounded-full"
                              style={{ width: `${Math.min(100, confidence)}%` }}
                            />
                          </div>
                        </div>
                      )}

                      <span
                        className={`px-3 py-1 text-xs font-bold font-mono uppercase rounded-lg border ${
                          action === 'BUY'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : action === 'SELL'
                            ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                            : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        }`}
                      >
                        {action}
                      </span>
                    </div>
                  </div>

                  {/* LLM Reasoning Text Box */}
                  <div className="bg-[#0B0E14] border border-white/5 rounded-xl p-4 text-sm text-slate-200 font-sans leading-relaxed">
                    <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500 font-bold block mb-1">
                      AI Reasoning
                    </span>
                    {log.llm_reasoning || log.decision?.reasoning || 'No qualitative reasoning text provided.'}
                  </div>

                  {/* Orders Placed Banner (if any) */}
                  {orders.length > 0 && (
                    <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-3 py-2 text-xs font-mono text-emerald-400">
                      <CheckCircle size={14} className="flex-shrink-0" />
                      <span>
                        Order executed successfully on Alpaca: {orders.length} order(s) submitted.
                      </span>
                    </div>
                  )}

                  {/* MCP Tool Calls Section */}
                  {mcpTools.length > 0 && (
                    <div className="border border-white/5 rounded-xl overflow-hidden bg-white/[0.01]">
                      <button
                        onClick={() => toggleExpand(cycleId)}
                        className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-mono text-slate-300 hover:bg-white/[0.02] transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Wrench size={13} className="text-cyan-400" />
                          <span className="font-bold text-cyan-400">Alpaca MCP Tools Invoked</span>
                          <span className="px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 text-[10px] border border-cyan-500/20">
                            {mcpTools.length}
                          </span>
                        </div>
                        <div className="flex items-center gap-1 text-slate-500 text-[11px]">
                          <span>{isExpanded ? 'Hide Payload' : 'Inspect MCP Tool Payload'}</span>
                          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="p-4 border-t border-white/5 space-y-3 bg-[#080A0E]">
                          {mcpTools.map((tc, tIdx) => (
                            <div key={tIdx} className="space-y-1.5">
                              <div className="flex items-center gap-2 text-xs font-mono text-white">
                                <span className="text-slate-500">Tool:</span>
                                <span className="font-bold text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded">
                                  {tc.name}
                                </span>
                              </div>
                              {tc.args && Object.keys(tc.args).length > 0 && (
                                <div className="text-[11px] font-mono text-slate-400">
                                  <span className="text-slate-500">Arguments: </span>
                                  <code>{JSON.stringify(tc.args)}</code>
                                </div>
                              )}
                              {tc.result && (
                                <div className="mt-1">
                                  <span className="text-[10px] font-mono text-slate-500 block mb-0.5">MCP Result:</span>
                                  <pre className="bg-black/50 p-2.5 rounded-lg text-[10px] font-mono text-slate-300 overflow-x-auto max-h-32 scrollbar-thin">
                                    {typeof tc.result === 'object'
                                      ? JSON.stringify(tc.result, null, 2)
                                      : String(tc.result)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="py-20 text-center text-slate-500 text-sm">
            {searchQuery ? 'No log entries match your search query.' : 'No decisions logged yet. Start the strategy to generate cycles.'}
          </div>
        )}
      </div>
    </div>
  );
}
