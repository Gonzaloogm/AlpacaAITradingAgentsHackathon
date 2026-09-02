import asyncio
import os
import json
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
            clock = await client.get_clock()
            print("CLOCK:", json.dumps(clock, indent=2))
    finally:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
