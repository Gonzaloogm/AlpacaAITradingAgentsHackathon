import Navbar from './Navbar';
import TickerTape from './TickerTape';

export default function Layout({ children }) {
  return (
    <div className="min-h-screen relative bg-[#0B0E14] overflow-hidden flex flex-col">
      {/* Clean trading platform background */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#0B0E14] to-[#07090C] pointer-events-none" />
      
      <div className="relative z-10 flex flex-col flex-1 min-h-0 w-full">
        <Navbar />
        <TickerTape />
        
        <div className="flex-1 flex flex-col min-h-0 mt-6 w-full max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8">
          <main className="flex-1 min-w-0 overflow-y-auto pr-2 scrollbar-hide pb-12">
            {children}
          </main>
        </div>

        <footer className="mt-auto pb-4 pt-8 text-center text-[10px] font-sans font-bold text-slate-600 uppercase tracking-widest opacity-60">
          Vantage · Powered by Alpaca · Paper Trading
        </footer>
      </div>
    </div>
  );
}
