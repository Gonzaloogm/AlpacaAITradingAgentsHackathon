import asyncio
from mcp_client.client import AlpacaMCPClient
from dotenv import load_dotenv
import os

async def main():
    load_dotenv()
    client = AlpacaMCPClient(
        api_key=os.getenv("ALPACA_API_KEY", ""),
        secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
        paper=True
    )
    await client.start()
    
    names = ["get_all_open_positions", "get_open_positions", "get_positions", "list_positions"]
    for n in names:
        try:
            res = await client.call_tool(n, {})
            if not isinstance(res, str) or "Unknown tool" not in res:
                print(f"SUCCESS FOR: {n}")
                break
        except Exception:
            pass

    order_names = ["get_orders", "get_all_orders", "list_orders"]
    for n in order_names:
        try:
            res = await client.call_tool(n, {})
            if not isinstance(res, str) or "Unknown tool" not in res:
                print(f"SUCCESS FOR: {n}")
                break
        except Exception:
            pass

    hist_names = ["get_portfolio_history", "get_account_portfolio_history", "portfolio_history"]
    for n in hist_names:
        try:
            res = await client.call_tool(n, {"period": "1M", "timeframe": "1D"})
            if not isinstance(res, str) or "Unknown tool" not in res:
                print(f"SUCCESS FOR: {n}")
                break
        except Exception:
            pass

    await client.stop()

asyncio.run(main())
