import asyncio
import json
import websockets


async def main():
    uri = "ws://192.168.0.210:8765"
    async with websockets.connect(uri) as ws:
        # Step 1: send audio data to receive options on the same connection.
        await ws.send(json.dumps({"audio_data": "Can you join us for lunch?"}))
        options_msg = await ws.recv()
        print("Options from server:", options_msg)

        try:
            options = json.loads(options_msg).get("data", [])
        except Exception:
            options = []

        for idx, opt in enumerate(options, start=1):
            print(f"{idx}. {opt}")

        choice = input("Select option number (default 1): ").strip() or "1"
        await ws.send(json.dumps({"type": "select", "data": int(choice)}))
        selected_msg = await ws.recv()
        print("Selected response:", selected_msg)


if __name__ == "__main__":
    asyncio.run(main())
