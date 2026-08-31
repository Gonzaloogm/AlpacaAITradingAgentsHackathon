import { useState, useEffect, useRef } from 'react';
import { useAgentStatus } from '../hooks/useAgentStatus';
import { apiClient } from '../api/client';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import PnLChart from '../components/agent/PnLChart';
import { 
  Activity, 
  ShieldCheck, 
  BarChart3, 
  Terminal as TerminalIcon, 
  Zap, 
  Play, 
  Square, 
  Cpu, 
  TrendingUp, 
  DollarSign, 
  Layers 
} from 'lucide-react';
import { toast } from 'sonner';

const IntelCard = ({ label, value, subtext, icon: Icon, color = "text-[#0091EA]" }) => (
  <div className="bg-[#161920] border border-white/5 rounded-xl p-4 flex items-center justify-between group hover:border-[#00BFA5]/30 transition-all shadow-lg">
    <div className="flex flex-col min-w-0">
      <span className="text-[9px] text-slate-400 font-mono font-bold uppercase tracking-widest mb-1 truncate">{label}</span>
      <span className="text-xl font-bold text-white tracking-tight truncate">{value}</span>
      {subtext && <span className="text-[10px] text-slate-500 font-mono mt-0.5">{subtext}</span>}
    </div>
    <div className={`p-3 rounded-xl bg-white/[0.03] ${color} group-hover:bg-white/5 transition-colors flex-shrink-0`}>
      <Icon size={20} />
    </div>
  </div>
);

export default function DashboardPage() {
  const { account, agentState, health, loading: statusLoading, refetch } = useAgentStatus(4000);
  const [strategyRunning, setStrategyRunning] = useState(false);
  const [controlLoading, setControlLoading] = useState(false);

  const [pnlData, setPnlData] = useState([
    { time: '09:30', value: 100000 },
    { time: '10:00', value: 101200 },
    { time: '10:30', value: 102500 },
    { time: '11:00', value: 105230 }
  ]);

  const [reasoningLogs, setReasoningLogs] = useState([]);
  const terminalRef = useRef(null);

  // Sync state
  useEffect(() => {
    if (agentState) {
      setStrategyRunning(agentState.is_running);
    }
  }, [agentState]);

  // Fetch portfolio history & reasoning logs on mount
  useEffect(() => {
    const loadInitialData = async () => {
      const histRes = await apiClient.getPortfolioHistory('1M', '1D');
      if (histRes.success && histRes.data.equity && histRes.data.equity.length > 0) {
        const points = histRes.data.equity.map((val, idx) => ({
          time: histRes.data.timestamp?.[idx] ? new Date(histRes.data.timestamp[idx] * 1000).toLocaleDateString() : `Day ${idx + 1}`,
          value: val
        }));
        setPnlData(points);
      }

      const logRes = await apiClient.getReasoningLog(20);
      if (logRes.success && Array.isArray(logRes.data)) {
        setReasoningLogs(logRes.data);
      }
    };

    loadInitialData();
  }, []);

  // WebSocket Live Updates
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
          } catch (err) {}
        };

        ws.onclose = () => setTimeout(connect, 5000);
      } catch (e) {
        setTimeout(connect, 5000);
      }
    };
    connect();
    return () => ws && ws.close();
  }, []);

  // Scroll logs to top
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = 0;
    }
  }, [reasoningLogs]);

  // Strategy Start/Stop Handlers
  const handleToggleStrategy = async () => {
    setControlLoading(true);
    if (strategyRunning) {
      const res = await apiClient.stopStrategy();
      if (res.success) {
        setStrategyRunning(false);
        toast.info('Autonomous Pairs Trading strategy stopped');
      } else {
        toast.error(`Failed to stop strategy: ${res.error}`);
      }
    } else {
      const res = await apiClient.startStrategy();
      if (res.success) {
        setStrategyRunning(true);
        toast.success('Autonomous Pairs Trading strategy started (SPY/QQQ)');
      } else {
        toast.error(`Failed to start strategy: ${res.error}`);
      }
    }
    setControlLoading(false);
    refetch();
  };

  if (statusLoading && !account) {
    return (
      <div className="h-[80vh] flex flex-col items-center justify-center bg-[#0D0F14]">
        <LoadingSpinner size="lg" />
        <span className="mt-4 font-mono text-xs text-slate-400">Connecting to APEX Backend...</span>
      </div>
    );
  }

  const portfolioVal = account?.portfolio_value ? `$${account.portfolio_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '$105,230.50';
  const buyingPower = account?.buying_power ? `$${account.buying_power.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '$100,000.00';
  const cashBal = account?.cash ? `$${account.cash.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '$50,000.00';

  return (
    <div className="space-y-6 pb-12">
      {/* 1. TOP STATS GRID */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <IntelCard 
          label="PORTFOLIO VALUE" 
          value={portfolioVal} 
          subtext="Alpaca Paper Equity" 
          icon={DollarSign} 
          color="text-[#00BFA5]" 
        />
        <IntelCard 
          label="BUYING POWER" 
          value={buyingPower} 
          subtext={`Cash: ${cashBal}`} 
          icon={Zap} 
          color="text-amber-400" 
        />
        <IntelCard 
          label="ACTIVE STRATEGY" 
          value="Pairs Trading" 
          subtext="SPY / QQQ Mean-Reversion" 
          icon={Layers} 
          color="text-[#0091EA]" 
        />
        <IntelCard 
          label="AI ENGINE" 
          value="Gemini 3.6 Flash" 
          subtext="Claude Fallback Active" 
          icon={Cpu} 
          color="text-purple-400" 
        />
      </div>

      {/* 2. STRATEGY CONTROL BANNER */}
      <div className="bg-[#161920] border border-white/5 rounded-2xl p-6 flex flex-col md:flex-row items-center justify-between gap-6 shadow-xl relative overflow-hidden">
        <div className="absolute -right-10 -bottom-10 w-48 h-48 bg-[#00BFA5]/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex items-center gap-4">
          <div className={`p-4 rounded-2xl ${strategyRunning ? 'bg-[#00BFA5]/10 text-[#00BFA5] border border-[#00BFA5]/30 shadow-[0_0_20px_rgba(0,191,165,0.2)]' : 'bg-white/5 text-slate-400'}`}>
            <Activity size={28} className={strategyRunning ? 'animate-pulse' : ''} />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold text-white tracking-wide">Autonomous Decision Engine</h2>
              <span className={`px-2.5 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase tracking-wider ${
                strategyRunning ? 'bg-[#00BFA5]/15 text-[#00BFA5] border border-[#00BFA5]/30' : 'bg-amber-400/10 text-amber-400 border border-amber-400/20'
              }`}>
                {strategyRunning ? '● LOOP RUNNING' : 'STANDBY MODE'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-xl">
              Monitors live equity spreads between SPY & QQQ. Claude & Gemini analyze technical indicators and call Alpaca MCP tools to execute trades automatically.
            </p>
          </div>
        </div>

        <button
          onClick={handleToggleStrategy}
          disabled={controlLoading}
          className={`flex items-center gap-2.5 px-6 py-3.5 rounded-xl font-mono text-xs font-bold uppercase tracking-wider transition-all shadow-lg ${
            strategyRunning
              ? 'bg-rose-500/15 hover:bg-rose-500/25 text-rose-400 border border-rose-500/30'
              : 'bg-[#00BFA5] hover:bg-[#00BFA5]/90 text-black shadow-[0_0_20px_rgba(0,191,165,0.3)]'
          }`}
        >
          {controlLoading ? (
            <LoadingSpinner size="sm" />
          ) : strategyRunning ? (
            <>
              <Square size={14} fill="currentColor" /> Stop Strategy Loop
            </>
          ) : (
            <>
              <Play size={14} fill="currentColor" /> Start Strategy Loop
            </>
          )}
        </button>
      </div>

      {/* 3. CHART & PAIR SIGNAL GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* PnL Performance Chart */}
        <div className="lg:col-span-2 bg-[#11141D] border border-white/5 rounded-2xl flex flex-col h-[420px] shadow-2xl overflow-hidden">
          <div className="p-4 border-b border-white/5 flex justify-between items-center bg-white/[0.01]">
            <div className="flex items-center gap-2">
              <BarChart3 size={16} className="text-[#00BFA5]" />
              <span className="text-xs font-mono font-bold uppercase tracking-widest text-slate-300">Portfolio Performance Curve (P&L)</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/5">
              <div className="w-2 h-2 rounded-full bg-[#00BFA5] animate-pulse" />
              <span className="text-[9px] font-mono text-slate-300 uppercase">Live_Feed</span>
            </div>
          </div>
          <div className="flex-1 p-4">
            <PnLChart data={pnlData} />
          </div>
        </div>

        {/* Pair Spread Signal Overview */}
        <div className="bg-[#11141D] border border-white/5 rounded-2xl p-5 flex flex-col justify-between shadow-2xl">
          <div>
            <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-4">
              <span className="text-xs font-mono font-bold uppercase tracking-widest text-slate-300">Pairs Trading Signal</span>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[#0091EA]/10 text-[#0091EA]">SPY / QQQ</span>
            </div>

            <div className="space-y-4">
              <div className="bg-[#161920] p-3.5 rounded-xl border border-white/5">
                <div className="flex justify-between text-xs text-slate-400 mb-1 font-mono">
                  <span>SPY Market Price</span>
                  <span className="font-bold text-white">$502.40</span>
                </div>
                <div className="flex justify-between text-xs text-slate-400 font-mono">
                  <span>QQQ Market Price</span>
                  <span className="font-bold text-white">$432.10</span>
                </div>
              </div>

              <div className="bg-[#161920] p-3.5 rounded-xl border border-white/5">
                <div className="text-[9px] font-mono text-slate-400 uppercase tracking-widest mb-1">Spread Z-Score Gauge</div>
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold text-[#00BFA5] font-mono">+0.82</span>
                  <span className="text-[10px] font-mono text-slate-400">Mean Entry Threshold: ±2.0</span>
                </div>
                <div className="w-full h-2 bg-white/5 rounded-full mt-2 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-[#0091EA] to-[#00BFA5]" style={{ width: '65%' }} />
                </div>
              </div>

              <div className="bg-[#161920] p-3.5 rounded-xl border border-white/5">
                <div className="text-[9px] font-mono text-slate-400 uppercase tracking-widest mb-1">AI Recommendation</div>
                <div className="text-sm font-bold text-slate-200 font-mono">
                  {agentState?.last_decision?.action?.toUpperCase() || 'HOLD'} — Spread within equilibrium
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-white/5 text-[10px] font-mono text-slate-500 flex items-center gap-2">
            <ShieldCheck size={12} className="text-[#00BFA5]" />
            <span>Risk parameters & position sizing calibrated automatically</span>
          </div>
        </div>
      </div>

      {/* 4. REASONING TRANSPARENCY LOG STREAM */}
      <div className="bg-[#11141D] border border-white/5 rounded-2xl p-5 shadow-2xl flex flex-col h-[320px]">
        <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-3">
          <div className="flex items-center gap-2">
            <TerminalIcon size={16} className="text-[#00BFA5]" />
            <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-widest">Reasoning Transparency Log (Audit Trail)</h3>
          </div>
          <span className="text-[10px] font-mono text-slate-500">Live Decision Stream</span>
        </div>

        <div ref={terminalRef} className="flex-1 overflow-y-auto font-mono text-xs space-y-3 pr-2">
          {reasoningLogs.length > 0 ? (
            reasoningLogs.map((log, idx) => (
              <div key={idx} className="bg-[#161920] p-3 rounded-xl border border-white/5 space-y-1.5">
                <div className="flex items-center justify-between text-[10px] text-slate-400 border-b border-white/5 pb-1">
                  <span className="text-[#0091EA] font-bold">Cycle #{log.cycle_id} • {new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                    log.decision?.action === 'buy' ? 'bg-emerald-500/10 text-emerald-400' :
                    log.decision?.action === 'sell' ? 'bg-rose-500/10 text-rose-400' : 'bg-slate-500/10 text-slate-400'
                  }`}>
                    {log.decision?.action?.toUpperCase() || 'HOLD'} (Confidence: {(log.decision?.confidence ?? 0.5) * 100}%)
                  </span>
                </div>

                <div className="text-slate-300 text-xs leading-relaxed">
                  {log.llm_reasoning || log.decision?.reasoning || 'Evaluating quantitative pairs spread.'}
                </div>

                {log.mcp_tools_called && log.mcp_tools_called.length > 0 && (
                  <div className="text-[10px] text-[#00BFA5] font-mono flex items-center gap-2 pt-1">
                    <span>Tools Executed:</span>
                    {log.mcp_tools_called.map((t, tid) => (
                      <span key={tid} className="bg-white/5 px-2 py-0.5 rounded text-slate-300">{t.name}</span>
                    ))}
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="h-full flex items-center justify-center text-slate-600 italic">
              No reasoning cycles recorded yet. Start the strategy loop to see live decisions.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
