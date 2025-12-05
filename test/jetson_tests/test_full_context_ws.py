"""
End-to-end websocket test for conversation context, highlights, and schedule seeding.

Assumes the websocket server is running on ws://localhost:8765 with:
- GEMINI_API_KEY set (for options/highlights)
- OPENAI_API_KEY set (for TTS, though we only assert responses here)
- user_context/events.ics and user_context/conversation_highlights.log accessible

This script:
1. Starts a conversation.
2. Sends one user utterance to fetch options.
3. Selects the first option.
4. Stops the conversation and prints the highlight.
It will raise on timeouts or missing expected message types.
"""

import asyncio
import json

import websockets
from jetson.context.calendar import load_and_summarize_schedule
from pathlib import Path


async def recv_expect(ws, expected_types, timeout=30):
    """Receive until a message with type in expected_types is found."""
    while True:
        msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
        print("Server:", msg)
        try:
            parsed = json.loads(msg)
            mtype = parsed.get("type")
            if mtype in expected_types:
                return parsed
        except Exception:
            continue


async def main():
    uri = "ws://localhost:8765"

    # Print seeded context once.
    log_path = Path("user_context/conversation_highlights.log")
    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8").splitlines()[-3:]
            print("Recent highlights to be seeded:")
            for ln in lines:
                try:
                    rec = json.loads(ln)
                    print(f"- {rec.get('highlight')}")
                except Exception:
                    print(f"- {ln}")
        except Exception as exc:
            print(f"Could not read highlights: {exc}")
    else:
        print("No highlights log found; none will be seeded.")

    try:
        schedule_summary = load_and_summarize_schedule("user_context/events.ics")
        print(f"Schedule summary: {schedule_summary}")
    except Exception as exc:
        print(f"Could not load schedule summary: {exc}")
        schedule_summary = ""

    async with websockets.connect(uri) as ws:
        # 1) Start conversation
        await ws.send(json.dumps({"type": "start_conversation"}))
        start_ack = await recv_expect(ws, {"conversation_started"})
        print("Start ack OK:", start_ack)

        # Print seeded highlights and schedule summary once (server seeds them internally).
        if schedule_summary:
            print(f"Schedule context sent to server: {schedule_summary}")

        # 2) Send user speech to get options
        await ws.send(json.dumps({"audio_data": "Quick check-in before lunch. How are you doing?"}))
        options_msg = await recv_expect(ws, {"options"})
        options = options_msg.get("data", [])
        print("Options:", options)
        if not options:
            raise RuntimeError("No options received from server")

        # 3) Select first option
        await ws.send(json.dumps({"type": "select", "data": 1}))
        await recv_expect(ws, {"selected", "error"})

        # 4) Stop conversation and read highlight
        await ws.send(json.dumps({"type": "stop_conversation"}))
        highlight_msg = await recv_expect(ws, {"conversation_highlight"})
        stopped_msg = await recv_expect(ws, {"conversation_stopped"})
        print("Highlight:", highlight_msg)
        print("Stopped:", stopped_msg)


if __name__ == "__main__":
    asyncio.run(main())
