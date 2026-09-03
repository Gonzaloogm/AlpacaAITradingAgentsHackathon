import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAgentStatus } from '../hooks/useAgentStatus';
import { apiClient } from '../api/client';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import PnLChart from '../components/agent/PnLChart';
import CandlestickChart from '../components/charts/CandlestickChart';
import { Activity, Terminal as TerminalIcon, Play, Square, Layers, TrendingUp, TrendingDown, DollarSign } from 'lucide-react';
import { toast } from 'sonner';

export default function DashboardPage() {
  const { account, agentState, loading: statusLoading, refetch } = useAgentStatus(4000);
  const [strategyRunning, setStrategyRunning] = useState(false);
  const [controlLoading, setControlLoading] = useState(false);
  const [pnlData, setPnlData] = useState([]);
  const [reasoningLogs, setReasoningLogs] = useState([]);
  const [chartSymbol, setChartSymbol] = useState('SPY');
  const [chartTimeframe, setChartTimeframe] = useState('1Day');
  const terminalRef = useRef(null);

  useEffect(() => {
    if (agentState) setStrategyRunning(agentState.is_running);
  }, [agentState]);

  useEffect(() => {
    const loadInitialData = async () => {
      const histRes = await apiClient.getPortfolioHistory('1M', '1D');
      if (histRes.success && histRes.data?.equity?.length > 0) {
        const points = histRes.data.equity.map((val, idx) => ({
          time: histRes.data.timestamp?.[idx] ? new Date(histRes.data.timestamp[idx] * 1000).toLocaleDateString() : `Day ${idx + 1}`,
          value: val
        }));
        setPnlData(points);
      } else if (account?.portfolio_value) {
        setPnlData([{ time: new Date().toLocaleDateString(), value: Number(account.portfolio_value) }]);
      }

      const logRes = await apiClient.getReasoningLog(20);
      if (logRes.success && Array.isArray(logRes.data)) setReasoningLogs(logRes.data);
    };
    loadInitialData();
  }, [account]);

  useEffect(() => {
    let ws = null;
    const connect = () => {
      try {
        const isDev = window.location.hostname === 'localhost';
        const host = isDev ? 'localhost:8000' : window.location.host;
        const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${host}/api/stream`;
        ws = new WebSocket(wsUrl);
        ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data);
            if (msg.type === 'reasoning_log_entry' && msg.data) {
              setReasoningLogs(prev => [msg.data, ...prev].slice(0, 30));
            }
            if (msg.type === 'agent_state_update' && msg.data) {
              setStrategyRunning(msg.data.is_running);
            }
          } catch {
            // Ignore parse errors on malformed messages
          }
        };
        ws.onclose = () => setTimeout(connect, 5000);
      } catch {
        setTimeout(connect, 5000);
      }
    };
    connect();
    return () => ws && ws.close();
  }, []);

  useEffect(() => {
    if (terminalRef.current) terminalRef.current.scrollTop = 0;
  }, [reasoningLogs]);

  const handleToggleStrategy = async () => {
    setControlLoading(true);
    if (strategyRunning) {
      const res = await apiClient.stopStrategy();
      if (res.success) {
        setStrategyRunning(false);
        toast.info('Autonomous strategy stopped');
      } else toast.error(`Failed to stop: ${res.error}`);
    } else {
      const res = await apiClient.startStrategy();
      if (res.success) {
        setStrategyRunning(true);
        toast.success('Autonomous strategy started');
      } else toast.error(`Failed to start: ${res.error}`);
    }
    setControlLoading(false);
    refetch();
  };

  if (statusLoading && !account) {
    return (
      <div className="h-[80vh] flex flex-col items-center justify-center bg-[#0D0F14]">
        <LoadingSpinner size="lg" />
        <span className="mt-4 font-mono text-xs text-slate-400">Loading market data & portfolio state...</span>
      </div>
    );
  }

  const pVal = Number(account?.portfolio_value || 0);
  const eq = Number(account?.equity || 0);
  const lastEq = Number(account?.last_equity || eq);
  const dayPnl = eq - lastEq;
  const dayPnlPct = lastEq > 0 ? (dayPnl / lastEq) * 100 : 0;
  const isPos = dayPnl >= 0;

  return (
    <div className="space-y-6 pb-12 font-sans">
      {/* 1. TOP STATS (High Density) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="bg-[#12141C] border border-white/5 rounded-xl p-6 flex flex-col justify-between shadow-lg">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Portfolio Value</span>
          <div className="text-4xl font-mono font-black text-white tracking-tight flex items-baseline gap-1">
            <span className="text-2xl text-slate-500">$</span>
            {pVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="mt-4 flex items-center gap-2">
            <div className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-bold font-mono ${isPos ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
              {isPos ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              {isPos ? '+' : ''}${Math.abs(dayPnl).toFixed(2)} ({isPos ? '+' : ''}{dayPnlPct.toFixed(2)}%)
            </div>
            <span className="text-xs text-slate-500 font-medium uppercase tracking-wide">Today</span>
          </div>
        </div>

        <div className="bg-[#12141C] border border-white/5 rounded-xl p-6 flex flex-col justify-between shadow-lg">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Buying Power</span>
          <div className="text-3xl font-mono font-black text-slate-200 tracking-tight flex items-baseline gap-1">
            <span className="text-xl text-slate-600">$</span>
            {Number(account?.buying_power || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
          <div className="mt-4 flex items-center gap-2 text-xs font-medium text-slate-500">
            Cash: <span className="font-mono text-slate-300">${Number(account?.cash || 0).toLocaleString()}</span>
          </div>
        </div>

        <div className="bg-[#12141C] border border-white/5 rounded-xl p-6 flex flex-col justify-between shadow-lg relative overflow-hidden group">
          <div className="absolute -right-6 -bottom-6 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl group-hover:bg-blue-500/20 transition-all pointer-events-none" />
          <div className="flex justify-between items-start">
            <div>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1 block">Strategy Control</span>
              <div className="flex items-center gap-1.5 text-[10px] font-mono text-blue-400">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping" />
                Gemini 3.6 Flash · AI Engine
              </div>
            </div>
            <div className={`p-2 rounded-lg ${strategyRunning ? 'bg-emerald-500/10 text-emerald-400' : 'bg-white/5 text-slate-500'}`}>
              <Activity size={20} className={strategyRunning ? 'animate-pulse' : ''} />
            </div>
          </div>
          <div className="text-lg font-bold text-white leading-tight mt-2 mb-3">
            Pairs Trading <span className="text-blue-400 font-mono text-sm">(SPY/QQQ)</span>
          </div>
          <button
            onClick={handleToggleStrategy}
            disabled={controlLoading}
            className={`w-full flex justify-center items-center gap-2 px-4 py-3 rounded-xl font-sans text-sm font-bold tracking-wide transition-all shadow-md ${
              strategyRunning
                ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20'
                : 'bg-blue-600 hover:bg-blue-500 text-white shadow-[0_4px_14px_0_rgba(37,99,235,0.39)]'
            }`}
          >
            {controlLoading ? <LoadingSpinner size="sm" /> : strategyRunning ? <><Square size={16} /> Stop Loop</> : <><Play size={16} /> Start Loop</>}
          </button>
        </div>
      </div>

      {/* 2. CANDLESTICK CHART */}
      <div className="bg-[#12141C] border border-white/5 rounded-xl flex flex-col h-[480px] shadow-lg overflow-hidden">
        <div className="p-4 border-b border-white/5 flex justify-between items-center bg-white/[0.01]">
          <div className="flex items-center gap-4">
            <span className="text-sm font-bold uppercase tracking-wider text-slate-200">Price Action</span>
            <div className="flex items-center gap-1">
              {['SPY', 'QQQ'].map((sym) => (
                <button
                  key={sym}
                  onClick={() => setChartSymbol(sym)}
                  className={`px-3 py-1.5 rounded-lg text-[11px] font-mono font-bold uppercase tracking-wider transition-all ${
                    chartSymbol === sym
                      ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
                      : 'text-slate-500 hover:text-slate-300 border border-transparent hover:bg-white/[0.03]'
                  }`}
                >
                  {sym}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-1">
            {[
              { label: '15m', value: '15Min' },
              { label: '1H', value: '1Hour' },
              { label: '1D', value: '1Day' },
            ].map((tf) => (
              <button
                key={tf.value}
                onClick={() => setChartTimeframe(tf.value)}
                className={`px-2.5 py-1 rounded text-[10px] font-mono font-bold uppercase tracking-wider transition-all ${
                  chartTimeframe === tf.value
                    ? 'bg-white/10 text-slate-200'
                    : 'text-slate-600 hover:text-slate-400'
                }`}
              >
                {tf.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 p-1">
          <CandlestickChart
            symbol={chartSymbol}
            timeframe={chartTimeframe}
            limit={chartTimeframe === '1Day' ? 60 : chartTimeframe === '1Hour' ? 48 : 60}
          />
        </div>
      </div>

      {/* 3. EQUITY CURVE & LOGS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-[#12141C] border border-white/5 rounded-xl flex flex-col h-[460px] shadow-lg overflow-hidden">
          <div className="p-5 border-b border-white/5 flex justify-between items-center bg-white/[0.01]">
            <span className="text-sm font-bold uppercase tracking-wider text-slate-200">Portfolio Equity Curve</span>
          </div>
          <div className="flex-1 p-5">
            <PnLChart data={pnlData} />
          </div>
        </div>

        <div className="bg-[#12141C] border border-white/5 rounded-xl p-5 shadow-lg flex flex-col h-[460px]">
          <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-4">
            <div className="flex items-center gap-2 text-slate-200">
              <TerminalIcon size={18} className="text-blue-400" />
              <h3 className="text-sm font-bold uppercase tracking-wider">Reasoning Audit</h3>
            </div>
            <Link to="/logs" className="text-xs font-mono text-blue-400 hover:text-blue-300 transition-colors">
              View All Logs →
            </Link>
          </div>
          <div ref={terminalRef} className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-thin scrollbar-thumb-slate-800">
            {reasoningLogs.length > 0 ? (
              reasoningLogs.map((log, idx) => (
                <div key={idx} className="bg-white/[0.02] p-4 rounded-xl border border-white/5 space-y-2 hover:bg-white/[0.03] transition-colors">
                  <div className="flex justify-between items-center text-xs font-mono">
                    <span className="text-slate-400">Cycle #{log.cycle_id}</span>
                    <div className="flex items-center gap-2">
                      {log.decision?.confidence && (
                        <span className="text-slate-500 font-mono text-[10px]">
                          {Math.round(log.decision.confidence * 100)}% conf
                        </span>
                      )}
                      <span className={`px-2 py-0.5 rounded font-bold uppercase ${
                        log.decision?.action === 'buy' ? 'bg-emerald-500/10 text-emerald-400' :
                        log.decision?.action === 'sell' ? 'bg-rose-500/10 text-rose-400' : 'bg-amber-500/10 text-amber-400'
                      }`}>
                        {log.decision?.action || 'HOLD'}
                      </span>
                    </div>
                  </div>
                  <div className="text-slate-300 text-sm leading-relaxed font-sans">
                    {log.llm_reasoning || log.decision?.reasoning}
                  </div>
                  {log.mcp_tools_called && log.mcp_tools_called.length > 0 && (
                    <div className="pt-1 flex flex-wrap gap-1">
                      {log.mcp_tools_called.map((tc, tIdx) => (
                        <span key={tIdx} className="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded border border-cyan-500/20">
                          ⚡ MCP: {tc.name}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 text-sm">
                No decisions recorded yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
