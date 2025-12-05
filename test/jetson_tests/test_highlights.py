import asyncio
import json
import websockets


async def main():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as ws:
        # Start conversation
        await ws.send(json.dumps({"type": "start_conversation"}))
        try:
            msg = await ws.recv()
            print("Server:", msg)
        except Exception as exc:
            print(f"Failed to receive start ack: {exc}")
            return

        # Single turn for brevity
        await ws.send(json.dumps({"audio_data": "Quick check-in. How are you feeling today?"}))
        options = None
        while options is None:
            msg = await ws.recv()
            print("Server:", msg)
            try:
                parsed = json.loads(msg)
                if parsed.get("type") == "options":
                    options = parsed.get("data", [])
            except Exception:
                pass

        for idx, opt in enumerate(options, start=1):
            print(f"{idx}. {opt}")

        await ws.send(json.dumps({"type": "select", "data": 1}))
        while True:
            msg = await ws.recv()
            print("Server:", msg)
            try:
                parsed = json.loads(msg)
                if parsed.get("type") in {"selected", "error"}:
                    break
            except Exception:
                break

        # Stop conversation and read highlight
        await ws.send(json.dumps({"type": "stop_conversation"}))
        try:
            msg = await ws.recv()
            print("Highlight:", msg)
            msg2 = await ws.recv()
            print("Stopped:", msg2)
        except Exception as exc:
            print(f"Error receiving stop response: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
