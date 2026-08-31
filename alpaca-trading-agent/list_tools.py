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
    res = await client._session.list_tools()
    for t in res.tools:
        if "position" in t.name.lower():
            print(t.name)
    await client.stop()

asyncio.run(main())
