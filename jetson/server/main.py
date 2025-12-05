import asyncio
import json
import logging
import sys
import websockets

from jetson.context.context import Context
from jetson.context.response_creator import create_context, set_response
from jetson.server.speech import speak_openai


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("jetson_server.log", mode="w")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.addHandler(file_handler)


clients = set()
mic_running = False
options_map = {}
conversation_state = {}


async def notify_hololens(event_type: str):
    """Send an event to all connected HoloLens clients."""
    if clients:
        message = json.dumps({"type": event_type})
        await asyncio.gather(*(client.send(message) for client in clients))


def _normalize_options(raw_response):
    """
    Turn a raw response into a list of options.
    - Gemini returns comma-separated options; parse and enforce exactly 3.
    """
    if isinstance(raw_response, list):
        opts = [o.strip() for o in raw_response if isinstance(o, str) and o.strip()]
    elif isinstance(raw_response, str):
        opts = [p.strip() for p in raw_response.split("|") if p.strip()]
    else:
        opts = []

    if len(opts) < 3:
        # pad with empty placeholders to keep length consistent
        opts.extend([""] * (3 - len(opts)))
    if len(opts) > 3:
        opts = opts[:3]
    return opts


async def handle_hololens(ws):
    """Receive messages from HoloLens clients."""
    async for message in ws:
        data = json.loads(message)        

        msg_type = data.get("type")

        # Handle conversation control.
        if isinstance(data, str) and data.lower() in {"start conversation", "stop conversation"}:
            msg_type = data.lower().replace(" ", "_")

        if msg_type == "start_conversation":
            conversation_state[ws] = {"active": True, "history": []}
            options_map[ws] = []
            try:
                await ws.send(json.dumps({"type": "conversation_started"}))
            except Exception as exc:
                logger.error(f"Failed to send conversation_started: {exc}")
            continue

        if msg_type == "stop_conversation":
            state = conversation_state.get(ws, {"history": []})
            highlight = state.get("history", [])
            conversation_state[ws] = {"active": False, "history": []}
            options_map[ws] = []
            try:
                await ws.send(json.dumps({"type": "conversation_highlight", "data": highlight}))
                await ws.send(json.dumps({"type": "conversation_stopped"}))
            except Exception as exc:
                logger.error(f"Failed to send conversation summary: {exc}")
            continue

        # Handle selection messages.
        if msg_type == "select":
            selection_raw = data.get("data") or data.get("selection")
            try:
                idx = int(selection_raw) - 1
                opts = options_map.get(ws, [])
                if idx < 0 or idx >= len(opts):
                    raise ValueError("Selection out of bounds")
                selected = opts[idx]
                if not isinstance(selected, str) or not selected.strip():
                    raise ValueError("Empty selection")
                state = conversation_state.get(ws, {"history": []})
                state.setdefault("history", []).append(
                    {"timestamp": asyncio.get_event_loop().time(), "role": "assistant_selection", "text": selected}
                )
            except Exception:
                try:
                    await ws.send(json.dumps({"type": "error", "message": "Invalid selection"}))
                except Exception as exc:
                    logger.error(f"Failed to send selection error: {exc}")
                continue

            # Send selection back immediately, then perform TTS in the background to avoid blocking/ping timeouts.
            try:
                await ws.send(json.dumps({"type": "selected", "data": selected}))
            except Exception as exc:
                logger.error(f"Failed to send selected response: {exc}")
                continue

            try:
                # Run TTS without blocking the event loop.
                asyncio.create_task(asyncio.to_thread(speak_openai, selected))
            except Exception as exc:
                logger.error(f"TTS failed: {exc}")
                try:
                    await ws.send(json.dumps({"type": "error", "message": "TTS failed"}))
                except Exception as send_exc:
                    logger.error(f"Failed to send TTS error: {send_exc}")
            continue

        # Handle incoming context (audio/image).
        if "audio_data" in data.keys() or "image_data" in data.keys():
            state = conversation_state.get(ws, {"active": False, "history": []})
            if not state.get("active"):
                logger.warning("Received audio/image without an active conversation.")
                try:
                    await ws.send(json.dumps({"type": "error", "message": "Conversation not started"}))
                except Exception as exc:
                    logger.error(f"Failed to send conversation not started error: {exc}")
                continue

            context = create_context(data)
            state.setdefault("history", []).append(
                {
                    "timestamp": asyncio.get_event_loop().time(),
                    "role": "user",
                    "text": context.audio_text,
                }
            )
            success = await asyncio.to_thread(set_response, context, state.get("history"))

            if success:
                opts = _normalize_options(context.response)
                options_map[ws] = opts
                state["history"].append(
                    {"timestamp": asyncio.get_event_loop().time(), "role": "assistant_options", "text": opts}
                )
                try:
                    await ws.send(json.dumps({"type": "options", "data": opts}))
                except Exception as exc:
                    logger.error(f"Failed to send options to client: {exc}")
            else:
                logger.error("Failed to get response from LLM.")
            continue

        logger.warning(f"Received a message with unknown type from HoloLens: {data}")


async def handler(ws):
    """Register HoloLens clients and listen to their messages."""
    logger.info(f"New HoloLens connection from {ws.remote_address}")
    clients.add(ws)

    try:
        await handle_hololens(ws)
    finally:
        clients.remove(ws)
        options_map.pop(ws, None)
        conversation_state.pop(ws, None)
        logger.info(f"HoloLens disconnected: {ws.remote_address}")


async def trigger_button_simulation():
    """Simulate button press without blocking the event loop."""
    global mic_running

    while True:
        prompt = "Press Enter to start microphone..." if not mic_running else "Press Enter to end microphone..."
        await asyncio.to_thread(input, prompt)

        mic_running = not mic_running
        event = "start_microphone" if mic_running else "stop_microphone"
        logger.info(f"Sending event: {event}")
        await notify_hololens(event)


async def main():
    server = await websockets.serve(
        handler,
        "0.0.0.0",
        8765,
        ping_interval=30,
        ping_timeout=60,
    )
    logger.info("Server running on ws://0.0.0.0:8765")

    await trigger_button_simulation()

    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
