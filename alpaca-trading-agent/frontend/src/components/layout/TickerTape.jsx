import { useState, useEffect, useRef } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export default function TickerTape() {
  const [ticks, setTicks] = useState({});
  const [prevTicks, setPrevTicks] = useState({});
  const wsRef = useRef(null);
  
  // Track continuous scrolling
  const scrollRef = useRef(null);

  useEffect(() => {
    let wsUrl = '';
    // Handle development vs production ports
    if (window.location.hostname === 'localhost' && window.location.port === '5173') {
      wsUrl = 'ws://localhost:8000/api/stream';
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//${window.location.host}/api/stream`;
    }

    const connect = () => {
      const ws = new WebSocket(wsUrl);
      
      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === 'price_tick' && Array.isArray(payload.data)) {
            setTicks(current => {
              setPrevTicks(current);
              const next = { ...current };
              payload.data.forEach(tick => {
                next[tick.symbol] = tick.price;
              });
              return next;
            });
          }
        } catch (err) {
          // Ignore parse errors
        }
      };

      ws.onclose = () => {
        setTimeout(connect, 3000); // Reconnect
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Continuous smooth scrolling effect
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    
    let animationFrameId;
    let pos = 0;
    
    const animate = () => {
      pos -= 0.5; // Scroll speed
      if (Math.abs(pos) >= el.scrollWidth / 2) {
        pos = 0;
      }
      el.style.transform = `translateX(${pos}px)`;
      animationFrameId = requestAnimationFrame(animate);
    };
    
    animate();
    
    return () => cancelAnimationFrame(animationFrameId);
  }, [ticks]);

  const symbols = Object.keys(ticks).sort();
  
  if (symbols.length === 0) return null;

  // Duplicate items for seamless scrolling
  const displayItems = [...symbols, ...symbols, ...symbols];

  return (
    <div className="w-full h-9 bg-[#0B0C10] border-b border-white/[0.05] flex items-center overflow-hidden">
      <div className="flex items-center gap-8 px-4 whitespace-nowrap will-change-transform" ref={scrollRef}>
        {displayItems.map((sym, i) => {
          const currentPrice = ticks[sym];
          const prevPrice = prevTicks[sym] || currentPrice;
          
          let colorClass = 'text-slate-400';
          let Icon = Minus;
          
          if (currentPrice > prevPrice) {
            colorClass = 'text-emerald-400';
            Icon = TrendingUp;
          } else if (currentPrice < prevPrice) {
            colorClass = 'text-rose-400';
            Icon = TrendingDown;
          }
          
          return (
            <div key={`${sym}-${i}`} className="flex items-center gap-2 font-mono text-[11px] uppercase font-bold tracking-widest">
              <span className="text-slate-500">{sym}</span>
              <span className={colorClass}>${currentPrice.toFixed(2)}</span>
              <Icon size={12} className={colorClass} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
