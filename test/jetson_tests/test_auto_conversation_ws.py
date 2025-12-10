import asyncio
import json
import websockets


async def recv_expect(ws, expected_types, timeout=30):
    while True:
        msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
        print("Server:", msg)
        try:
            data = json.loads(msg)
            if data.get("type") in expected_types:
                return data
        except Exception:
            continue


async def main():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as ws:
        # Start conversation
        await ws.send(json.dumps({"type": "start_conversation"}))
        await recv_expect(ws, {"conversation_started"})

        print("Waiting for options from mic_vad_sender. Type 'stop' to end the conversation.")
        while True:
            options_msg = await recv_expect(ws, {"options"})
            options = options_msg.get("data", [])
            print("Options:")
            for idx, opt in enumerate(options, start=1):
                print(f"{idx}. {opt}")

            choice = input("Select option number (default 1, or 'stop' to end): ").strip()
            if choice.lower() == "stop":
                await ws.send(json.dumps({"type": "stop_conversation"}))
                await recv_expect(ws, {"conversation_highlight"})
                await recv_expect(ws, {"conversation_stopped"})
                break
            choice = choice or "1"
            await ws.send(json.dumps({"type": "select", "data": int(choice)}))
            await recv_expect(ws, {"selected", "error"})
            # TTS runs server-side; when done, server sends tts_done
            await recv_expect(ws, {"tts_done"})


if __name__ == "__main__":
    asyncio.run(main())
