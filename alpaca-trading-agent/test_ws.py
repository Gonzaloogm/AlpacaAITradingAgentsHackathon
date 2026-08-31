import asyncio
import websockets

async def test():
    try:
        async with websockets.connect("ws://localhost:8000/api/stream") as ws:
            print("Connected")
            msg = await asyncio.wait_for(ws.recv(), timeout=40.0)
            print("WS received:", msg[:200])
    except Exception as e:
        print("Error:", repr(e))

asyncio.run(test())
