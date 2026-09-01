import asyncio
import json
import logging
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path("/Users/alumnoad/AI-TradingAgents2/AlpacaAITradingAgentsHackathon/alpaca-trading-agent")))

from mcp_client.client import AlpacaMCPClient
from strategy.pairs_trading import PairsTradingStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_single_cycle():
    mcp_client = AlpacaMCPClient(
        api_key=os.environ.get("ALPACA_API_KEY"),
        secret_key=os.environ.get("ALPACA_SECRET_KEY")
    )
    strategy = PairsTradingStrategy(symbol_a="SPY", symbol_b="QQQ")
    
    await mcp_client.start()
    await asyncio.sleep(4)
    
    data_spy = await mcp_client.get_market_data("SPY")
    data_qqq = await mcp_client.get_market_data("QQQ")

    market_data = {"SPY": data_spy, "QQQ": data_qqq}
    signal = await strategy.analyze(market_data)
    
    print("\n=== FINAL TEST RESULTS ===")
    print(json.dumps(signal, indent=2))
    
    await mcp_client.stop()

if __name__ == "__main__":
    asyncio.run(run_single_cycle())
