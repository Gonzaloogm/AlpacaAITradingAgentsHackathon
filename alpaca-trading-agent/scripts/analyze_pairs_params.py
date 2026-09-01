"""
Step 2: Analyze pairs trading parameters on REAL historical SPY/QQQ data.

Pulls bars via the live AlpacaMCPClient, runs PairsTradingStrategy._calculate_spread
and _calculate_zscore over the full history, and reports:
  - Current z-score
  - Rolling z-score series over the lookback window
  - How often entry/exit thresholds would have been crossed
  - Recommendation on whether thresholds are calibrated well

Run: python3 scripts/analyze_pairs_params.py
"""

import asyncio
import os
import sys
import json
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from mcp_client.client import AlpacaMCPClient

# ---- Strategy parameters (from code defaults + .env overrides) ----
LOOKBACK = int(os.getenv("STRATEGY_LOOKBACK_PERIOD", "20"))
ENTRY_Z  = float(os.getenv("STRATEGY_ENTRY_ZSCORE", "2.0"))
EXIT_Z   = float(os.getenv("STRATEGY_EXIT_ZSCORE", "0.5"))
SYMBOL_A = "SPY"
SYMBOL_B = "QQQ"
BARS_TO_FETCH = 60  # Fetch more than lookback so we can do rolling analysis


async def main():
    api_key = os.getenv("ALPACA_API_KEY", "")
    secret_key = os.getenv("ALPACA_SECRET_KEY", "")

    print(f"=== Pairs Trading Parameter Analysis ===")
    print(f"Pair:            {SYMBOL_A} / {SYMBOL_B}")
    print(f"Lookback period: {LOOKBACK} bars (daily)")
    print(f"Entry z-score:   ±{ENTRY_Z}")
    print(f"Exit z-score:    ±{EXIT_Z}")
    print(f"Bars to fetch:   {BARS_TO_FETCH} (for rolling analysis)")
    print()

    async with AlpacaMCPClient(api_key=api_key, secret_key=secret_key, paper=True) as client:
        print(f"[MCP] Connected. Fetching {BARS_TO_FETCH} daily bars for {SYMBOL_A} and {SYMBOL_B}...")

        # Fetch bars for both symbols
        result_spy = await client.call_tool("get_stock_bars", {
            "symbols": SYMBOL_A,
            "timeframe": "1Day",
            "limit": BARS_TO_FETCH,
            "days": 120
        })
        result_qqq = await client.call_tool("get_stock_bars", {
            "symbols": SYMBOL_B,
            "timeframe": "1Day",
            "limit": BARS_TO_FETCH,
            "days": 120
        })

    # ---- Extract closing prices ----
    def extract_closes(result, symbol):
        """Navigate the various response shapes from MCP bars."""
        # result may be: {"bars": {"SPY": [...]}} or just a list or dict
        if isinstance(result, dict):
            bars_dict = result.get("bars", result)
            if isinstance(bars_dict, dict):
                bars = bars_dict.get(symbol, bars_dict.get("bars", {}).get(symbol, []))
            else:
                bars = bars_dict
        elif isinstance(result, list):
            bars = result
        else:
            bars = []

        closes = []
        for bar in bars:
            if isinstance(bar, dict):
                c = bar.get("c") or bar.get("close")
                t = bar.get("t") or bar.get("timestamp", "")
                if c is not None:
                    closes.append((t, float(c)))
        return closes

    spy_bars = extract_closes(result_spy, SYMBOL_A)
    qqq_bars = extract_closes(result_qqq, SYMBOL_B)

    print(f"[Data] {SYMBOL_A}: {len(spy_bars)} bars fetched")
    print(f"[Data] {SYMBOL_B}: {len(qqq_bars)} bars fetched")

    if len(spy_bars) < 2 or len(qqq_bars) < 2:
        print("ERROR: insufficient bars returned. Cannot analyze.")
        return

    # Align to common length
    n = min(len(spy_bars), len(qqq_bars))
    spy_bars = spy_bars[-n:]
    qqq_bars = qqq_bars[-n:]

    spy_closes = np.array([b[1] for b in spy_bars])
    qqq_closes = np.array([b[1] for b in qqq_bars])
    dates       = [b[0][:10] for b in spy_bars]  # date portion

    print(f"\n=== Last 5 bars (aligned) ===")
    print(f"{'Date':<12} {'SPY':>8} {'QQQ':>8} {'Spread':>10}")
    for i in range(-5, 0):
        print(f"{dates[i]:<12} {spy_closes[i]:>8.2f} {qqq_closes[i]:>8.2f} {spy_closes[i]-qqq_closes[i]:>10.2f}")

    # ---- Rolling z-score over full history ----
    print(f"\n=== Rolling z-score (window={LOOKBACK}) over {n} bars ===")
    spread_series = spy_closes - qqq_closes

    z_scores = []
    for i in range(LOOKBACK - 1, n):
        window = spread_series[i - LOOKBACK + 1: i + 1]
        mean = np.mean(window)
        std  = np.std(window, ddof=1) if len(window) > 1 else 0.0
        z    = float((window[-1] - mean) / std) if std > 0 else 0.0
        z_scores.append((dates[i], float(window[-1]), mean, std, z))

    print(f"\nLast 10 rolling z-scores:")
    print(f"{'Date':<12} {'Spread':>10} {'Mean':>10} {'Std':>8} {'Z-score':>9} {'Signal':<14}")
    for date, spread, mean, std, z in z_scores[-10:]:
        if z >= ENTRY_Z:
            sig = "SHORT_A_LONG_B"
        elif z <= -ENTRY_Z:
            sig = "LONG_A_SHORT_B"
        elif abs(z) <= EXIT_Z:
            sig = "EXIT"
        else:
            sig = "NEUTRAL"
        print(f"{date:<12} {spread:>10.4f} {mean:>10.4f} {std:>8.4f} {z:>9.4f} {sig:<14}")

    # ---- Threshold crossing frequency ----
    total_bars = len(z_scores)
    entry_crosses = sum(1 for *_, z in z_scores if abs(z) >= ENTRY_Z)
    exit_crosses  = sum(1 for *_, z in z_scores if abs(z) <= EXIT_Z)
    neutral_bars  = sum(1 for *_, z in z_scores if EXIT_Z < abs(z) < ENTRY_Z)

    current_z = z_scores[-1][4] if z_scores else 0.0

    print(f"\n=== Threshold Analysis (over {total_bars} rolling bars) ===")
    print(f"Current z-score:            {current_z:+.4f}")
    print(f"Entry threshold (±{ENTRY_Z}):    {entry_crosses}/{total_bars} bars ({100*entry_crosses/total_bars:.1f}%) would trigger ENTRY")
    print(f"Exit threshold  (±{EXIT_Z}):   {exit_crosses}/{total_bars} bars ({100*exit_crosses/total_bars:.1f}%) would trigger EXIT")
    print(f"Neutral (no signal):        {neutral_bars}/{total_bars} bars ({100*neutral_bars/total_bars:.1f}%)")

    print(f"\n=== Z-score distribution ===")
    z_vals = [z for *_, z in z_scores]
    print(f"  Min:    {min(z_vals):+.4f}")
    print(f"  Max:    {max(z_vals):+.4f}")
    print(f"  Mean:   {np.mean(z_vals):+.4f}")
    print(f"  Std:    {np.std(z_vals):.4f}")
    print(f"  |Z|>1:  {sum(1 for z in z_vals if abs(z)>1)}/{total_bars} bars ({100*sum(1 for z in z_vals if abs(z)>1)/total_bars:.1f}%)")
    print(f"  |Z|>2:  {sum(1 for z in z_vals if abs(z)>2)}/{total_bars} bars ({100*sum(1 for z in z_vals if abs(z)>2)/total_bars:.1f}%)")
    print(f"  |Z|>3:  {sum(1 for z in z_vals if abs(z)>3)}/{total_bars} bars ({100*sum(1 for z in z_vals if abs(z)>3)/total_bars:.1f}%)")

    print(f"\n=== RECOMMENDATION ===")
    if entry_crosses == 0:
        print("⚠️  ENTRY threshold NEVER triggered over full history — thresholds too tight or pair too stable.")
        print(f"   Consider lowering entry_zscore from {ENTRY_Z} to ~1.5.")
    elif entry_crosses / total_bars > 0.3:
        print("⚠️  ENTRY threshold triggered >30% of bars — thresholds too loose, will overtrade.")
        print(f"   Consider raising entry_zscore from {ENTRY_Z} to ~2.5.")
    else:
        print(f"✓  Entry z-score ±{ENTRY_Z} appears calibrated ({entry_crosses}/{total_bars} bars = {100*entry_crosses/total_bars:.1f}% trigger rate).")

    if current_z >= ENTRY_Z:
        print(f"🔴 RIGHT NOW: z={current_z:+.4f} → would trigger SHORT_A_LONG_B (short SPY, long QQQ)")
    elif current_z <= -ENTRY_Z:
        print(f"🟢 RIGHT NOW: z={current_z:+.4f} → would trigger LONG_A_SHORT_B (long SPY, short QQQ)")
    elif abs(current_z) <= EXIT_Z:
        print(f"⚪ RIGHT NOW: z={current_z:+.4f} → EXIT signal (spread mean-reverted)")
    else:
        print(f"🟡 RIGHT NOW: z={current_z:+.4f} → NEUTRAL (between EXIT and ENTRY thresholds)")


if __name__ == "__main__":
    asyncio.run(main())
