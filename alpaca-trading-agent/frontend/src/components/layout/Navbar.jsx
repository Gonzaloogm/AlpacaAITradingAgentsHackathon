import { NavLink } from 'react-router-dom';
import { useAgentStatus } from '../../hooks/useAgentStatus';
import { Activity, ShieldCheck, Terminal, Wallet, MessageSquare } from 'lucide-react';

const navLinks = [
  { to: '/dashboard', label: 'Dashboard', icon: <Activity size={14} /> },
  { to: '/logs', label: 'Reasoning Log', icon: <Terminal size={14} /> },
  { to: '/positions', label: 'Positions & Orders', icon: <Wallet size={14} /> },
  { to: '/chat', label: 'AI Chat Assistant', icon: <MessageSquare size={14} /> },
];

export default function Navbar() {
  const { account, agentState, health } = useAgentStatus(5000);

  const isOnline = health?.status === 'ok';
  const isRunning = agentState?.is_running ?? false;
  const mcpConnected = health?.mcp_connected ?? false;
  const accountNum = account?.account_number || 'PAPER-SIM';

  return (
    <nav className="sticky top-0 z-50 bg-[#0F111A]/95 backdrop-blur-md border-b border-white/[0.05] flex items-center justify-between px-6 lg:px-8 h-[68px]">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 21L10 12L14 16L21 5" />
            <path d="M16 5h5v5" />
            <circle cx="10" cy="12" r="1.5" fill="currentColor"/>
          </svg>
        </div>
        <div className="flex flex-col justify-center">
          <span className="text-white font-black tracking-widest text-lg uppercase leading-none">Vantage</span>
          <span className="text-[10px] text-blue-400/80 font-mono tracking-widest uppercase font-semibold mt-0.5">Your AI Trader</span>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 h-full">
        {navLinks.map(link => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === '/dashboard'}
            className={({ isActive }) =>
              `flex items-center gap-2 px-4 h-full text-[12px] font-bold uppercase tracking-wider transition-all duration-200 border-b-[3px] ${
                isActive
                  ? 'border-blue-500 text-blue-400 bg-blue-500/5'
                  : 'border-transparent text-slate-500 hover:text-slate-300 hover:bg-white/[0.02]'
              }`
            }
          >
            {link.icon}
            {link.label}
          </NavLink>
        ))}
      </div>

      {/* Status Indicators & Account */}
      <div className="flex items-center gap-5">
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${mcpConnected ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' : 'bg-slate-800/50 border-slate-700 text-slate-500'} transition-colors duration-500`}>
          <ShieldCheck size={12} className={mcpConnected ? 'animate-pulse' : ''} />
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider">
            MCP {mcpConnected ? 'Connected' : 'Offline'}
          </span>
        </div>

        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${!isOnline ? 'bg-red-500/10 border-red-500/20 text-red-400' : isRunning ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-amber-500/10 border-amber-500/20 text-amber-400'} transition-colors duration-500`}>
          <div className={`w-2 h-2 rounded-full ${!isOnline ? 'bg-red-400' : isRunning ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider">
            {!isOnline ? 'Offline' : isRunning ? 'Strategy Running' : 'Standby'}
          </span>
        </div>

        <div className="flex flex-col items-end">
          <span className="text-[9px] text-slate-500 font-sans font-bold uppercase tracking-widest">Alpaca Account</span>
          <span className="text-[12px] font-mono font-bold text-slate-200">{accountNum}</span>
        </div>
      </div>
    </nav>
  );
}
