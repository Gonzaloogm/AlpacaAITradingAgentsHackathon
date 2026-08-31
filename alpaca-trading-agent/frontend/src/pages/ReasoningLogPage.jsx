import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { Terminal, RefreshCw, Cpu } from 'lucide-react';

export default function ReasoningLogPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    setLoading(true);
    const res = await apiClient.getReasoningLog(50);
    if (res.success && Array.isArray(res.data)) {
      setLogs(res.data);
    }
    setLoading(false);
  };

  useEffect(() => { fetchLogs(); }, []);

  return (
    <div className="space-y-6 pb-12 font-sans">
      <div className="flex justify-between items-center bg-[#12141C] border border-white/5 rounded-2xl p-6 shadow-lg">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
            <Terminal className="text-blue-500" /> Reasoning Log
          </h1>
          <p className="text-sm text-slate-400 mt-1">Real-time audit trail of AI trading decisions</p>
        </div>
        <button onClick={fetchLogs} className="flex items-center gap-2 px-4 py-2.5 bg-white/[0.03] hover:bg-white/[0.08] rounded-xl text-sm font-bold text-slate-200 transition-all border border-white/5 shadow-sm">
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      <div className="bg-[#12141C] border border-white/5 rounded-2xl shadow-lg overflow-hidden">
        {loading && logs.length === 0 ? (
          <div className="h-64 flex items-center justify-center"><LoadingSpinner size="md" /></div>
        ) : logs.length > 0 ? (
          <div className="divide-y divide-white/5">
            {logs.map((log, idx) => (
              <div key={idx} className="p-6 hover:bg-white/[0.02] transition-colors">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg"><Cpu size={18} /></div>
                    <div>
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider">Cycle #{log.cycle_id}</h3>
                      <p className="text-xs font-mono text-slate-500 mt-0.5">{new Date(log.timestamp).toLocaleString()}</p>
                    </div>
                  </div>
                  <span className={`px-3 py-1 text-xs font-bold font-mono uppercase rounded border ${
                    log.decision?.action === 'buy' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                    log.decision?.action === 'sell' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  }`}>
                    {log.decision?.action || 'HOLD'}
                  </span>
                </div>
                <div className="bg-black/30 border border-white/5 rounded-xl p-4 text-sm text-slate-300 font-sans leading-relaxed">
                  {log.llm_reasoning || log.decision?.reasoning}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-20 text-center text-slate-500 text-sm">No decisions logged yet.</div>
        )}
      </div>
    </div>
  );
}
