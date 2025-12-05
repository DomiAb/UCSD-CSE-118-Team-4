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
        print("Started conversation.")

        while True:
            user_text = input("\nEnter user speech (or 'stop' to end conversation): ").strip()
            if user_text.lower() == "stop":
                await ws.send(json.dumps({"type": "stop_conversation"}))
                try:
                    # Expect highlight then stopped messages.
                    for _ in range(2):
                        msg = await ws.recv()
                        print("Server:", msg)
                except Exception as exc:
                    print(f"Error receiving stop response: {exc}")
                break

            # Send audio_data to get options
            await ws.send(json.dumps({"audio_data": user_text}))
            # Receive until we get options
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

            choice = input("Select option number (default 1, or type 'stop' to end): ").strip() or "1"
            if choice.lower() == "stop":
                await ws.send(json.dumps({"type": "stop_conversation"}))
                try:
                    for _ in range(2):
                        msg = await ws.recv()
                        print("Server:", msg)
                except Exception as exc:
                    print(f"Error receiving stop response: {exc}")
                break

            try:
                choice_num = int(choice)
            except ValueError:
                print("Invalid choice; defaulting to 1")
                choice_num = 1

            await ws.send(json.dumps({"type": "select", "data": choice_num}))

            # Receive until we get selected/error
            while True:
                msg = await ws.recv()
                print("Server:", msg)
                try:
                    parsed = json.loads(msg)
                    if parsed.get("type") in {"selected", "error"}:
                        break
                except Exception:
                    break


if __name__ == "__main__":
    asyncio.run(main())
