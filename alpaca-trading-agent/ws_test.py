import asyncio
import websockets
import time

async def test():
    async with websockets.connect("ws://localhost:8000/api/stream") as ws:
        print("Connected to WebSocket.")
        for i in range(8):
            msg = await ws.recv()
            print(f"[{time.strftime('%X')}] Received:", msg)

asyncio.run(test())
