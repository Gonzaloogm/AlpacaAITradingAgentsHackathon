import asyncio
import os
import json
import math
from dotenv import load_dotenv
load_dotenv()
from mcp_client.client import AlpacaMCPClient

async def main():
    api_key = os.getenv("ALPACA_API_KEY", "")
    secret_key = os.getenv("ALPACA_SECRET_KEY", "")
    client = AlpacaMCPClient(api_key=api_key, secret_key=secret_key, paper=True)
    await client.start()
    
    try:
        if getattr(client, "is_connected", False):
            hist = await client.get_portfolio_history(period="1A", timeframe="1D")
            equity_curve = hist.get("equity", [])
            print("RAW EQUITY PTS:", len(equity_curve))
            equity_curve = [e for e in equity_curve if e is not None and e > 0]
            print("FILTERED EQUITY PTS:", len(equity_curve))
    finally:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
