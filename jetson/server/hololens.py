import asyncio
from datetime import datetime
import json
import logging
import pathlib

from jetson.context.calendar import load_and_summarize_schedule
from jetson.context.history import _load_recent_highlights, _summarize_history
from jetson.context.response_creator import create_context, set_response
from jetson.server.speech import speak_openai


logger = logging.getLogger(__name__)


conversation_state = {}
options_map = {}


def start_conversation(ws):
    recent_highlights = _load_recent_highlights()
    schedule_context = load_and_summarize_schedule("user_context/events.ics")
    history_seed = [
        {
            "timestamp": None,
            "role": "recent_highlights",
            "text": h.get("highlight", ""),
        }
        for h in recent_highlights
        if h.get("highlight")
    ]
    conversation_state[ws] = {
        "active": True,
        "history": history_seed,
        "start_at": datetime.now(),
        "schedule_context": schedule_context,
    }
    options_map[ws] = []
    try:
        ws.send(json.dumps({"type": "conversation_started"}))
    except Exception as exc:
        logger.error(f"Failed to send conversation_started: {exc}")


def stop_conversation(ws):
    state = conversation_state.get(ws, {"history": [], "start_at": datetime.now()})
    history = state.get("history", [])
    start_at = state.get("start_at", datetime.now())
    stop_at = datetime.now()

    # Summarize in a thread to avoid blocking the event loop.
    highlight_text = asyncio.to_thread(_summarize_history, history)

    # Persist highlight to a log file.
    try:
        log_path = pathlib.Path("user_context/conversation_highlights.log")
        record = {
            "start_at": start_at.isoformat(),
            "stop_at": stop_at.isoformat(),
            "highlight": highlight_text,
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        logger.error(f"Failed to write conversation highlight: {exc}")

    conversation_state[ws] = {"active": False, "history": [], "start_at": None, "schedule_context": ""}
    options_map[ws] = []
    try:
        ws.send(json.dumps({"type": "conversation_highlight", "data": highlight_text}))
        ws.send(json.dumps({"type": "conversation_stopped"}))
    except Exception as exc:
        logger.error(f"Failed to send conversation summary: {exc}")


async def select(data: dict[str, str], ws):
    try:
        selection_raw = data["data"]
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
            ws.send(json.dumps({"type": "error", "message": "Invalid selection"}))
        except Exception as exc:
            logger.error(f"Failed to send selection error: {exc}")
        return


    try:
        # Run TTS without blocking the event loop.
        asyncio.create_task(asyncio.to_thread(speak_openai, selected))
    except Exception as exc:
        logger.error(f"TTS failed: {exc}")
        try:
            await ws.send(json.dumps({"type": "error", "message": "TTS failed"}))
        except Exception as send_exc:
            logger.error(f"Failed to send TTS error: {send_exc}")


async def image_data(data: dict[str, str], ws):
    state = conversation_state.get(ws, {"active": False, "history": []})
    if not state.get("active"):
        logger.warning("Received audio/image without an active conversation.")
        try:
            await ws.send(json.dumps({"type": "error", "message": "Conversation not started"}))
        except Exception as exc:
            logger.error(f"Failed to send conversation not started error: {exc}")
        return

    context = create_context(data)
    state.setdefault("history", []).append(
        {
            "timestamp": asyncio.get_event_loop().time(),
            "role": "user",
            "text": context.audio_text,
        }
    )
    success = await asyncio.to_thread(
        set_response,
        context,
        state.get("history"),
        state.get("schedule_context", ""),
    )

    if success:
        opts = context._get_normalize_options()
        options_map[ws] = opts
        state["history"].append(
            {"timestamp": asyncio.get_event_loop().time(), "role": "assistant_options", "text": opts}
        )
        try:
            await ws.send(json.dumps({"type": "options", "data": opts}))
        except Exception as exc:
            logger.error(f"Failed to send options to client: {exc}")


async def handle_hololens(ws):
    """Receive messages from HoloLens clients."""
    async for message in ws:
        data = json.loads(message)        

        msg_type = data.get("type")

        match msg_type:
            case "start_conversation":
                start_conversation(ws)
                break
            case "stop_conversation":
                stop_conversation(ws)
                break
            case "select":
                await select(data, ws)
                break
            case "image_data":
                await image_data(data, ws)
                break
            case None:
                logger.error("Received message without type from HoloLens.")
                break
            case _:
                logger.error(f"Unknown message type from HoloLens: {msg_type}")
                break
