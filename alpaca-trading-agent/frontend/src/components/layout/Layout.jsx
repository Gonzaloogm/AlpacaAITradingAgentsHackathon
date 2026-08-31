import Navbar from './Navbar';

export default function Layout({ children }) {
  return (
    <div className="min-h-screen relative bg-[#0D0F14] overflow-hidden flex flex-col">
      <div className="absolute inset-0 opacity-20 pointer-events-none" style={{ backgroundImage: 'radial-gradient(#ffffff 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
      
      <div className="relative z-10 flex flex-col flex-1 min-h-0 w-full max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Navbar />
        
        <div className="flex-1 flex flex-col min-h-0 mt-6">
          <main className="flex-1 min-w-0 overflow-y-auto pr-2 scrollbar-hide">
            {children}
          </main>
        </div>

        <footer className="mt-8 pb-4 text-center text-[10px] font-sans font-bold text-slate-600 uppercase tracking-widest opacity-60">
          Vantage · Powered by Alpaca · Paper Trading
        </footer>
      </div>
    </div>
  );
}
