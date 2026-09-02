import asyncio
import os
from mcp_client.client import AlpacaMCPClient

async def main():
    api_key = os.getenv("ALPACA_API_KEY", "")
    secret_key = os.getenv("ALPACA_SECRET_KEY", "")
    client = AlpacaMCPClient(api_key=api_key, secret_key=secret_key, paper=True)
    await client.start()
    if getattr(client, "is_connected", False):
        try:
            print(await client.get_latest_quote("SPY"))
        finally:
            await client.stop()
asyncio.run(main())
