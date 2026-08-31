import { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { useAgentStatus } from '../../hooks/useAgentStatus';
import { Activity, ShieldCheck, Terminal, Wallet, MessageSquare, Zap } from 'lucide-react';

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
  const accountNum = account?.account_number || account?.id?.substring(0, 10) || 'PA31415926';

  return (
    <nav className="sticky top-0 z-50 bg-[#0D0F14]/90 backdrop-blur-md border-b border-white/5 flex items-center justify-between px-6 lg:px-10 h-[64px]">
      {/* Brand — APEX */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#00BFA5] to-[#0091EA] flex items-center justify-center font-black text-black text-sm shadow-[0_0_15px_rgba(0,191,165,0.4)]">
          ⚡
        </div>
        <div className="flex flex-col">
          <span className="text-white font-black tracking-wider text-base uppercase leading-none">APEX</span>
          <span className="text-[9px] text-[#00BFA5] font-mono tracking-widest uppercase font-semibold">Alpaca AI Trading Agent</span>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 h-full">
        {navLinks.map(link => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === '/dashboard'}
            className={({ isActive }) =>
              `flex items-center gap-2 px-5 h-full text-[11px] font-bold uppercase tracking-wider transition-all duration-200 border-b-2 ${
                isActive
                  ? 'border-[#00BFA5] text-[#00BFA5] bg-white/[0.02]'
                  : 'border-transparent text-slate-400 hover:text-white hover:bg-white/[0.01]'
              }`
            }
          >
            {link.icon}
            {link.label}
          </NavLink>
        ))}
      </div>

      {/* Status Indicators & Account */}
      <div className="flex items-center gap-6">
        {/* MCP Status */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-white/5 rounded-full border border-white/5">
          <ShieldCheck size={12} className={mcpConnected ? 'text-[#00BFA5]' : 'text-slate-500'} />
          <span className="text-[10px] font-mono text-slate-300 font-medium">
            MCP Server: <span className={mcpConnected ? 'text-[#00BFA5] font-bold' : 'text-slate-400'}>{mcpConnected ? 'CONNECTED' : 'DISCONNECTED'}</span>
          </span>
        </div>

        {/* Strategy Loop Status */}
        <div className="flex items-center gap-2 px-3 py-1 bg-white/5 rounded-full border border-white/5">
          <div className={`w-2 h-2 rounded-full ${!isOnline ? 'bg-red-500' : isRunning ? 'bg-[#00BFA5] animate-pulse shadow-[0_0_8px_#00BFA5]' : 'bg-amber-400'}`} />
          <span className={`text-[10px] font-mono font-bold uppercase tracking-wider ${!isOnline ? 'text-red-400' : isRunning ? 'text-[#00BFA5]' : 'text-amber-400'}`}>
            {!isOnline ? 'OFFLINE' : isRunning ? 'STRATEGY RUNNING' : 'STANDBY'}
          </span>
        </div>

        {/* Account Info */}
        <div className="flex flex-col items-end hidden sm:flex">
          <span className="text-[8px] text-slate-500 font-mono font-bold uppercase tracking-widest">Alpaca Paper Account</span>
          <span className="text-[11px] font-mono font-bold text-white/90">{accountNum}</span>
        </div>
      </div>
    </nav>
  );
}
