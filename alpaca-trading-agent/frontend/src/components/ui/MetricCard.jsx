export default function MetricCard({
  title,
  value,
  subtitle,
  icon,
  isMock,
  error,
  insufficientData,
  badge,
  progress,
}) {
  return (
    <div className="relative bg-[#12141C] border border-white/5 rounded-xl p-6 shadow-lg flex flex-col h-full overflow-hidden group hover:border-blue-500/20 transition-colors">
      {/* Mock data overlay badge or custom badge */}
      <div className="absolute top-4 right-4 flex items-center gap-1.5">
        {isMock && (
          <div className="bg-amber-500/10 border border-amber-500/20 text-amber-500 text-[9px] font-mono font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
            Mock Data
          </div>
        )}
        {badge && !isMock && !insufficientData && (
          <div
            className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded-full uppercase tracking-wider border ${
              badge.color === 'emerald'
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : badge.color === 'blue'
                ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                : 'bg-slate-800 text-slate-400 border-white/10'
            }`}
          >
            {badge.text}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-400 group-hover:bg-blue-500/20 transition-colors">
          {icon}
        </div>
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
          {title}
        </h3>
      </div>

      <div className="mt-auto space-y-2">
        {error ? (
          <div className="text-rose-400 text-sm font-mono">{error}</div>
        ) : insufficientData ? (
          <div className="text-2xl font-mono font-bold text-slate-500/50 tracking-tight">
            N/A
          </div>
        ) : (
          <div className="text-3xl font-mono font-bold text-white tracking-tight">
            {value}
          </div>
        )}

        {typeof progress === 'number' && !insufficientData && (
          <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-blue-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
          </div>
        )}

        <div className="text-xs font-sans text-slate-500">
          {insufficientData ? 'Insufficient trade history' : subtitle}
        </div>
      </div>

      {/* Background decoration */}
      <div className="absolute -bottom-10 -right-10 opacity-[0.03] text-white pointer-events-none">
        {icon && <div className="scale-[4]">{icon}</div>}
      </div>
    </div>
  );
}
