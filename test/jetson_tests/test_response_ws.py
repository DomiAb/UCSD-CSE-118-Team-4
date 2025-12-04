import asyncio, json, websockets


# Tests only the response functionality of the server

async def main():
    uri = "ws://192.168.0.210:8765"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"audio_data": "How's college going?"}))
        msg = await ws.recv()
        print("Got from server:", msg)
asyncio.run(main())
