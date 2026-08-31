import { useNavigate } from 'react-router-dom';
import { ArrowRight, Activity, Cpu, ShieldCheck } from 'lucide-react';

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 font-sans bg-[#0D0F14]">
      <div className="max-w-3xl text-center space-y-8">
        <div className="inline-flex items-center justify-center p-4 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 mb-4 shadow-lg shadow-blue-500/10">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 21L10 12L14 16L21 5" />
            <path d="M16 5h5v5" />
            <circle cx="10" cy="12" r="1.5" fill="currentColor"/>
          </svg>
        </div>
        
        <h1 className="text-6xl md:text-7xl font-black text-white tracking-tighter">
          Vantage
        </h1>
        <p className="text-xl md:text-2xl text-slate-400 font-medium tracking-wide">
          Your AI Trader
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-8 pb-12 text-left">
          <div className="p-6 rounded-2xl bg-[#12141C] border border-white/5">
            <Cpu className="text-blue-500 mb-4" size={24} />
            <h3 className="text-white font-bold mb-2">AI Decision Engine</h3>
            <p className="text-sm text-slate-500">Powered by Google Gemini and Anthropic Claude for intelligent market analysis.</p>
          </div>
          <div className="p-6 rounded-2xl bg-[#12141C] border border-white/5">
            <Activity className="text-emerald-500 mb-4" size={24} />
            <h3 className="text-white font-bold mb-2">Pairs Trading Strategy</h3>
            <p className="text-sm text-slate-500">An AI-driven pairs trading agent executing live on Alpaca.</p>
          </div>
          <div className="p-6 rounded-2xl bg-[#12141C] border border-white/5">
            <ShieldCheck className="text-amber-500 mb-4" size={24} />
            <h3 className="text-white font-bold mb-2">MCP Integration</h3>
            <p className="text-sm text-slate-500">Using the Model Context Protocol (MCP) to seamlessly interact with Alpaca trading APIs.</p>
          </div>
        </div>

        <button
          onClick={() => navigate('/dashboard')}
          className="group inline-flex items-center gap-3 px-8 py-4 bg-blue-600 hover:bg-blue-500 text-white rounded-full font-bold text-lg transition-all shadow-[0_8px_30px_rgb(37,99,235,0.4)] hover:shadow-[0_8px_40px_rgb(37,99,235,0.6)]"
        >
          Enter Dashboard
          <ArrowRight className="group-hover:translate-x-1 transition-transform" />
        </button>

        <div className="pt-12 text-xs font-mono font-bold text-slate-600 uppercase tracking-widest">
          Hackathon Demo · Alpaca AI Trading
        </div>
      </div>
    </div>
  );
}
