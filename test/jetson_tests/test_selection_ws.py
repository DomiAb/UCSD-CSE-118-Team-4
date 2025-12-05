import asyncio
import json
import websockets


# Sends a request with heard speech
# Displays options to users enabling user to select
# Sends back selection to server (This also leads to it being spoken through default speaker)


async def main():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as ws:
        # Step 1: send audio data to receive options on the same connection.
        await ws.send(json.dumps({"audio_data": "Hey what's up Jeremy! Can you join us for lunch? And how's that dog of yours, I heard he was a little ill."}))
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
