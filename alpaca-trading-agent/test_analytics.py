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
            # Orders
            orders = await client.get_orders(status="all", limit=500)
            print("ORDERS COUNT:", len(orders) if isinstance(orders, list) else len(orders.get("orders", [])))
            
            # Activities
            try:
                acts = await client.call_tool("get_account_activities", {"activity_types": "FILL"})
                print("ACTIVITIES:", json.dumps(acts[:2] if isinstance(acts, list) else acts, indent=2))
            except Exception as e:
                print("Activities error:", e)

            # Portfolio History
            hist = await client.get_portfolio_history(period="1A", timeframe="1D")
            equity = hist.get("equity", [])
            print("EQUITY PTS:", len(equity))
    finally:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
