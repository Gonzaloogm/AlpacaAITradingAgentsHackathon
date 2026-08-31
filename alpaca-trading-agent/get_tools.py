import asyncio
from mcp_client.client import AlpacaMCPClient
import os

async def main():
    client = AlpacaMCPClient(
        api_key=os.getenv("ALPACA_API_KEY", ""),
        secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
        paper=True
    )
    await client.start()
    tools = await client.list_tools()
    for t in tools:
        print(f"Tool: {t.name}")
    await client.stop()

asyncio.run(main())
