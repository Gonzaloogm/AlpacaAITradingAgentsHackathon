import React, { useEffect, useRef, useState, useCallback, Component } from 'react';
import { createChart, ColorType, CrosshairMode, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import { apiClient } from '../../api/client';

class ChartErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, errorMessage: error.message };
  }

  componentDidCatch(error, errorInfo) {
    console.error("CandlestickChart Error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="w-full h-full flex flex-col items-center justify-center text-center p-4">
          <div className="bg-rose-500/10 text-rose-400 border border-rose-500/20 px-4 py-3 rounded-xl max-w-sm">
            <h3 className="font-bold text-sm uppercase tracking-wider mb-1">Chart failed to load</h3>
            <p className="text-xs font-mono opacity-80 break-words">{this.state.errorMessage}</p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

/**
 * CandlestickChartInner — TradingView Lightweight Charts wrapper
 *
 * Renders real OHLC candlestick data with volume histogram overlay.
 * Dark theme matching Vantage design system.
 */
function CandlestickChartInner({ symbol = 'SPY', timeframe = '1Day', limit = 60 }) {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastBar, setLastBar] = useState(null);
  const [isMock, setIsMock] = useState(false);

  // Parse ISO timestamp to lightweight-charts time value
  const parseTime = useCallback((t) => {
    if (!t) return 0;
    // lightweight-charts expects UTC timestamps as YYYY-MM-DD string or unix seconds
    const d = new Date(t);
    if (isNaN(d.getTime())) return 0;
    // For daily bars, use YYYY-MM-DD string format
    if (timeframe.includes('Day') || timeframe.includes('Week') || timeframe.includes('Month')) {
      return d.toISOString().slice(0, 10);
    }
    // For intraday, use unix timestamp in seconds
    return Math.floor(d.getTime() / 1000);
  }, [timeframe]);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#64748B',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.03)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.03)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: 'rgba(59, 130, 246, 0.4)',
          labelBackgroundColor: '#1e293b',
        },
        horzLine: {
          color: 'rgba(59, 130, 246, 0.4)',
          labelBackgroundColor: '#1e293b',
        },
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.05)',
        scaleMargins: { top: 0.05, bottom: 0.2 },
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.05)',
        timeVisible: !timeframe.includes('Day'),
        secondsVisible: false,
      },
      handleScroll: { vertTouchDrag: false },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10B981',
      downColor: '#EF4444',
      borderUpColor: '#10B981',
      borderDownColor: '#EF4444',
      wickUpColor: '#10B981',
      wickDownColor: '#EF4444',
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    // Subscribe to crosshair move for legend
    chart.subscribeCrosshairMove((param) => {
      if (!param || !param.time) {
        setLastBar(null);
        return;
      }
      const data = param.seriesData?.get(candleSeries);
      if (data) {
        setLastBar(data);
      }
    });

    // Resize handler
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        chart.applyOptions({ width, height });
      }
    });
    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
    };
  }, []); // Chart instance created once

  // Fetch and render data when symbol/timeframe changes
  useEffect(() => {
    let cancelled = false;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      setIsMock(false);

      const res = await apiClient.getOHLC(symbol, timeframe, limit);

      if (cancelled) return;

      if (!res.success) {
        setError(res.error || 'Failed to load chart data');
        setLoading(false);
        return;
      }

      setIsMock(!!res.data?.is_mock);

      const bars = res.data?.bars || [];
      if (bars.length === 0) {
        setError('No bar data available');
        setLoading(false);
        return;
      }

      // Transform to lightweight-charts format
      const candleData = bars
        .map((bar) => ({
          time: parseTime(bar.t),
          open: bar.o,
          high: bar.h,
          low: bar.l,
          close: bar.c,
        }))
        .filter((d) => d.time);

      const volumeData = bars
        .map((bar) => ({
          time: parseTime(bar.t),
          value: bar.v,
          color: bar.c >= bar.o ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)',
        }))
        .filter((d) => d.time);

      if (candleSeriesRef.current) {
        candleSeriesRef.current.setData(candleData);
      }
      if (volumeSeriesRef.current) {
        volumeSeriesRef.current.setData(volumeData);
      }

      // Set last bar for legend
      if (candleData.length > 0) {
        const last = bars[bars.length - 1];
        setLastBar({ open: last.o, high: last.h, low: last.l, close: last.c });
      }

      // Fit content
      if (chartRef.current) {
        chartRef.current.timeScale().fitContent();
      }

      setLoading(false);
    };

    fetchData();

    return () => {
      cancelled = true;
    };
  }, [symbol, timeframe, limit, parseTime]);

  const change = lastBar ? lastBar.close - lastBar.open : 0;
  const isUp = change >= 0;

  return (
    <div className="relative w-full h-full">
      {/* OHLC Legend overlay */}
      <div className="absolute top-2 left-3 z-10 flex items-center gap-4 text-[11px] font-mono">
        <span className="text-slate-400 font-bold">{symbol}</span>
        {lastBar && (
          <>
            <span className="text-slate-500">
              O <span className="text-slate-300">{lastBar.open?.toFixed(2)}</span>
            </span>
            <span className="text-slate-500">
              H <span className="text-slate-300">{lastBar.high?.toFixed(2)}</span>
            </span>
            <span className="text-slate-500">
              L <span className="text-slate-300">{lastBar.low?.toFixed(2)}</span>
            </span>
            <span className="text-slate-500">
              C{' '}
              <span className={isUp ? 'text-emerald-400' : 'text-rose-400'}>
                {lastBar.close?.toFixed(2)}
              </span>
            </span>
            <span className={`font-bold ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
              {isUp ? '+' : ''}{change.toFixed(2)}
            </span>
          </>
        )}
      </div>

      {/* Mock data warning overlay */}
      {isMock && !loading && !error && (
        <div className="absolute top-8 left-1/2 -translate-x-1/2 z-10 pointer-events-none">
          <div className="bg-amber-500/10 border border-amber-500/20 text-amber-500/90 px-3 py-1.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-widest backdrop-blur-md flex items-center gap-2 shadow-lg">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
            Demo data — MCP disconnected
          </div>
        </div>
      )}

      {/* Loading/Error states */}
      {loading && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-[#12141C]/80">
          <div className="flex items-center gap-2 text-slate-500 text-xs font-mono uppercase tracking-widest">
            <div className="w-4 h-4 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
            Loading {symbol}...
          </div>
        </div>
      )}
      {error && !loading && (
        <div className="absolute inset-0 z-20 flex items-center justify-center">
          <span className="text-rose-400 text-xs font-mono">{error}</span>
        </div>
      )}

      {/* Chart container */}
      <div ref={chartContainerRef} className="w-full h-full" />
    </div>
  );
}

export default function CandlestickChart(props) {
  return (
    <ChartErrorBoundary>
      <CandlestickChartInner {...props} />
    </ChartErrorBoundary>
  );
}
