import asyncio
import websockets

async def main():
    async with websockets.connect("ws://192.168.0.210:8765") as ws:
        await ws.send('{"type":"audio_data","data":"hello"}')
        print("Connected and sent message!")

asyncio.run(main())
