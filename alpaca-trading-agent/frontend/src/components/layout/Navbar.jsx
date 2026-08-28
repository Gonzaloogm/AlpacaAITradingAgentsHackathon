import { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { useAgentStatus } from '../../hooks/useAgentStatus';
import { Activity, Wallet, Terminal, Video } from 'lucide-react';

const navLinks = [
  { to: '/dashboard', label: 'Dashboard', icon: <Activity size={14} /> },
  { to: '/stream', label: 'Live Stream', icon: <Video size={14} /> },
  { to: '/positions', label: 'Positions', icon: <Wallet size={14} /> },
  { to: '/logs', label: 'AI Logs', icon: <Terminal size={14} /> },
];

export default function Navbar() {
  const { account } = useAgentStatus(20000);
  const [isOperational, setIsOperational] = useState(localStorage.getItem('DEMO_OPERATIONAL') === 'true');

  const isOnline = !!account;
  const shortId = account?.id ? account.id.substring(0, 8) : '—';

  useEffect(() => {
    const checkState = () => {
      setIsOperational(localStorage.getItem('DEMO_OPERATIONAL') === 'true');
    };
    window.addEventListener('storage', checkState);
    const interval = setInterval(checkState, 1000);
    return () => {
      window.removeEventListener('storage', checkState);
      clearInterval(interval);
    };
  }, []);

  return (
    <nav className="sticky-header flex items-center justify-between px-10 mb-8 shadow-sm">
      {/* Brand – STRIKER Logo */}
      <div className="flex items-center gap-3">
        <img
          src="/img/striker-logo.png"
          alt="STRIKER"
          className="h-9 w-auto object-contain rounded"
        />
        <span className="text-white font-bold tracking-tight text-base uppercase">Striker</span>
      </div>

      {/* Corporate Tabs */}
      <div className="flex items-center gap-1">
        {navLinks.map(link => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === '/dashboard'}
            className={({ isActive }) =>
              `flex items-center gap-2 px-6 h-[60px] text-[10px] font-semibold uppercase tracking-wider transition-all duration-300 transform ${isActive
                ? 'text-[#00BFA5] active-tab-indicator'
                : 'text-gray-500 hover:text-white'
              }`
            }
          >
            {link.icon}
            {link.label}
          </NavLink>
        ))}
      </div>

      {/* Status & ID - Corporate Right */}
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2 py-1 px-3 bg-white/5 rounded-full border border-white/5">
          <div className={`w-1.5 h-1.5 rounded-full transition-all duration-500 ${!isOnline ? 'bg-red-500' :
            isOperational ? 'bg-[#00BFA5] animate-pulse shadow-[0_0_8px_#00BFA5]' :
              'bg-amber-400'
            }`} />
          <span className={`text-[9px] font-bold uppercase tracking-widest leading-none ${!isOnline ? 'text-gray-500' :
            isOperational ? 'text-[#00BFA5]' :
              'text-amber-400'
            }`}>
            {!isOnline ? 'System Offline' : isOperational ? 'Operational' : 'Validated Ready'}
          </span>
        </div>

        <div className="flex flex-col items-end">
          <span className="text-[7px] text-gray-600 font-bold uppercase tracking-tighter mb-0.5">Account ID</span>
          <span className="text-[10px] font-mono text-white/80 leading-none">{shortId}</span>
        </div>
      </div>
    </nav>
  );
}
