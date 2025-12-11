import asyncio
import json
import logging
import os
from datetime import datetime
import sys
import pathlib
import websockets

from jetson.context.context import Context
from jetson.context.response_creator import create_context, set_response
from jetson.context.llm_interface import query_gemini
from jetson.context.calendar import load_and_summarize_schedule, load_events_from_ics
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
options_map = {}
conversation_state = {}
event_contexts = {}
active_session = None
mic_process = None


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


def _summarize_history(history: list) -> str:
    """Summarize the conversation history using Gemini for concise highlights."""
    if not history:
        return "No conversation history available."
    lines = []
    for turn in history:
        role = turn.get("role", "user")
        text = turn.get("text", "")
        if isinstance(text, list):
            text = "; ".join([str(t) for t in text if t])
        ts = turn.get("timestamp")
        if ts:
            try:
                ts = float(ts)
                ts_str = f"{ts:.0f}s"
            except Exception:
                ts_str = ""
        else:
            ts_str = ""
        prefix = f"[{ts_str}] " if ts_str else ""
        lines.append(f"{prefix}{role}: {text}")

    history_text = "\n".join(lines)
    prompt = (
        "Summarize this conversation between the user and the addressee into 1-3 concise bullet highlights that capture key points, "
        "mentions, and next steps. Keep it concise, clear and meaningful. Directly give the summary without any additional text. Do not mention the word 'assitant'."
        f"{history_text}"
    )
    try:
        return query_gemini(prompt)
    except Exception as exc:
        logger.error(f"Failed to summarize history: {exc}")
        return "Highlight unavailable due to summarization error."


def _load_recent_highlights(max_entries: int = 5) -> list:
    """Load recent highlights from the log file."""
    log_path = pathlib.Path("user_context/conversation_highlights.log")
    if not log_path.exists():
        return []
    highlights = []
    try:
        with log_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()[-max_entries:]
        for line in lines:
            try:
                highlights.append(json.loads(line))
            except Exception:
                continue
    except Exception as exc:
        logger.error(f"Failed to read highlights: {exc}")
    return highlights


def _load_core_context() -> str:
    path = pathlib.Path("user_context/core_context.txt")
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        logger.error(f"Failed to read core context: {exc}")
        return ""


def _load_core_lines() -> list[str]:
    txt = _load_core_context()
    return [ln for ln in txt.splitlines() if ln.strip()]


def _write_core_lines(lines: list[str]):
    path = pathlib.Path("user_context/core_context.txt")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
    except Exception as exc:
        logger.error(f"Failed to write core context: {exc}")


def _read_highlights() -> list[dict]:
    log_path = pathlib.Path("user_context/conversation_highlights.log")
    if not log_path.exists():
        return []
    entries = []
    try:
        with log_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
    except Exception as exc:
        logger.error(f"Failed to read highlights: {exc}")
    return entries


def _write_highlights(entries: list[dict]):
    log_path = pathlib.Path("user_context/conversation_highlights.log")
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.error(f"Failed to write highlights: {exc}")


def _append_conversation_log(record: dict):
    path = pathlib.Path("user_context/conversation_logs.log")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        logger.error(f"Failed to append conversation log: {exc}")


async def _start_mic_sender():
    """Start mic_vad_sender in a separate process if not already running."""
    global mic_process
    if mic_process and mic_process.returncode is None:
        return
    ws_url = os.getenv("WS_URL", "ws://localhost:8765")
    script_path = pathlib.Path(__file__).resolve().parent.parent / "client" / "mic_vad_sender.py"
    if not script_path.exists():
        logger.error(f"mic_vad_sender not found at {script_path}")
        return
    try:
        env = os.environ.copy()
        env["WS_URL"] = ws_url
        # Pass through OPENAI_API_KEY and other env as-is.
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        log_path = pathlib.Path("user_context/mic_vad_sender.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = log_path.open("ab")
        logger.info(f"Launching mic_vad_sender: {sys.executable} {script_path} --ws {ws_url} (cwd={repo_root})")
        mic_process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script_path),
            "--ws",
            ws_url,
            stdout=log_file,
            stderr=log_file,
            cwd=str(repo_root),
            env=env,
        )
        logger.info("Started mic_vad_sender process.")
    except Exception as exc:
        logger.error(f"Failed to start mic_vad_sender: {exc}")


async def _stop_mic_sender():
    """Stop mic_vad_sender process if running."""
    global mic_process
    if mic_process and mic_process.returncode is None:
        try:
            mic_process.terminate()
            await mic_process.wait()
            logger.info("Stopped mic_vad_sender process.")
        except Exception as exc:
            logger.error(f"Failed to stop mic_vad_sender: {exc}")
    mic_process = None


def _load_event_contexts() -> dict:
    path = pathlib.Path("user_context/event_contexts.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error(f"Failed to read event contexts: {exc}")
        return {}


def _save_event_contexts(data: dict):
    path = pathlib.Path("user_context/event_contexts.json")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.error(f"Failed to write event contexts: {exc}")


async def handle_hololens(ws):
    """Receive messages from HoloLens clients."""
    async for message in ws:
        data = json.loads(message)        

        msg_type = data.get("type")

        # Handle conversation control.
        if isinstance(data, str) and data.lower() in {"start conversation", "stop conversation"}:
            msg_type = data.lower().replace(" ", "_")

        if msg_type == "start_conversation":
            logger.info("***** Starting new conversation session. *****")
            try:
                await ws.send(json.dumps({"type": "conversation_started"}))
            except Exception as exc:
                logger.error(f"Failed to send conversation_started: {exc}")
            logger.info("***** Clearing conversation state and speaker. *****")
            await _start_mic_sender()
            recent_highlights = _load_recent_highlights()
            schedule_context = load_and_summarize_schedule("user_context/events.ics")
            core_context = _load_core_context()
            session_id = datetime.now().isoformat()
            # Determine active event context
            events = load_events_from_ics("user_context/events.ics")
            now = datetime.now()
            active_event_ctx = ""
            ctx_map = _load_event_contexts()
            for ev in events:
                if ev.get("start") and ev.get("end") and ev["start"] <= now < ev["end"]:
                    key = f"{ev['summary']}|{ev['start'].isoformat()}|{ev['end'].isoformat()}"
                    if key in ctx_map:
                        active_event_ctx = ctx_map[key]
                    break
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
                "core_context": core_context,
                "session_id": session_id,
                "event_context": active_event_ctx,
                "speaking": False,
            }
            global active_session
            active_session = conversation_state[ws]
            options_map[ws] = []
            continue

        if msg_type == "send_audio":
            logger.info("***** Stopping conversation session. *****")
            try:
                # await ws.send(json.dumps({"type": "conversation_highlight", "data": highlight_text}))
                await ws.send(json.dumps({"type": "conversation_stopped"}))
            except Exception as exc:
                logger.error(f"Failed to send conversation_started: {exc}")
            continue

        if msg_type == "get_context":
            try:
                highlights_entries = _read_highlights()
                core_lines = _load_core_lines()
                schedule_context = load_and_summarize_schedule("user_context/events.ics")
                events = load_events_from_ics("user_context/events.ics")
                ctx_map = _load_event_contexts()
                events_payload = [
                    {
                        "summary": ev.get("summary", ""),
                        "start": ev.get("start").isoformat() if ev.get("start") else "",
                        "end": ev.get("end").isoformat() if ev.get("end") else "",
                        "location": ev.get("location", ""),
                    }
                    for ev in events
                ]
                await ws.send(
                    json.dumps(
                        {
                            "type": "context_snapshot",
                            "core": core_lines,
                            "highlights": highlights_entries,
                            "schedule": schedule_context,
                            "events": events_payload,
                            "event_contexts": ctx_map,
                        }
                    )
                )
            except Exception as exc:
                logger.error(f"Failed to send context snapshot: {exc}")
            continue

        if msg_type == "set_core_context":
            lines = data.get("data") or []
            if isinstance(lines, list):
                _write_core_lines([str(ln).strip() for ln in lines if str(ln).strip()])
                await ws.send(json.dumps({"type": "core_context_updated"}))
            continue

        if msg_type == "add_highlight":
            text = data.get("data") or ""
            if text:
                entries = _read_highlights()
                entries.append(
                    {
                        "start_at": datetime.now().isoformat(),
                        "stop_at": datetime.now().isoformat(),
                        "highlight": str(text),
                    }
                )
                _write_highlights(entries)
                await ws.send(json.dumps({"type": "highlight_added"}))
            continue

        if msg_type == "delete_highlight":
            try:
                idx = int(data.get("data"))
                entries = _read_highlights()
                if 0 <= idx < len(entries):
                    entries.pop(idx)
                    _write_highlights(entries)
                    await ws.send(json.dumps({"type": "highlight_deleted"}))
            except Exception as exc:
                logger.error(f"Failed to delete highlight: {exc}")
            continue

        if msg_type == "set_calendar":
            ics_text = data.get("data") or ""
            try:
                path = pathlib.Path("user_context/events.ics")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(ics_text, encoding="utf-8")
                await ws.send(json.dumps({"type": "calendar_updated"}))
            except Exception as exc:
                logger.error(f"Failed to update calendar: {exc}")
            continue

        if msg_type == "set_event_context":
            # Expect data: { summary, start, end, context }
            payload = data.get("data") or {}
            try:
                summary = payload.get("summary", "")
                start = payload.get("start", "")
                end = payload.get("end", "")
                ctx = payload.get("context", "")
                if summary and start and end:
                    ctx_map = _load_event_contexts()
                    key = f"{summary}|{start}|{end}"
                    ctx_map[key] = ctx
                    _save_event_contexts(ctx_map)
                    await ws.send(json.dumps({"type": "event_context_updated"}))
            except Exception as exc:
                logger.error(f"Failed to set event context: {exc}")
            continue

        if msg_type == "stop_conversation":
            state = conversation_state.get(ws) or active_session or {"history": [], "start_at": datetime.now()}
            history = state.get("history", [])
            start_at = state.get("start_at", datetime.now())
            stop_at = datetime.now()
            session_id = state.get("session_id")
            highlight_text = await asyncio.to_thread(_summarize_history, history)

            try:
                log_path = pathlib.Path("user_context/conversation_highlights.log")
                record = {
                    "start_at": start_at.isoformat(),
                    "stop_at": stop_at.isoformat(),
                    "highlight": highlight_text,
                }
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
            except Exception as exc:
                logger.error(f"Failed to write conversation highlight: {exc}")

            conversation_state[ws] = {
                "active": False,
                "history": [],
                "start_at": None,
                "schedule_context": "",
                "core_context": "",
                "session_id": None,
                "event_context": "",
                "speaking": False,
            }
            active_session = None
            options_map[ws] = []
            try:
                await ws.send(json.dumps({"type": "conversation_highlight", "data": highlight_text}))
                await ws.send(json.dumps({"type": "conversation_stopped"}))
            except Exception as exc:
                logger.error(f"Failed to send conversation summary: {exc}")
            await _stop_mic_sender()
            continue

        # Handle selection messages.
        if msg_type == "select":
            selection_raw = data.get("data") or data.get("selection")
            try:
                idx = int(selection_raw) - 1
                logger.info(f"User selected option index: {idx}")
                opts = options_map.get(ws, [])
                logger.info(f"Available options: {opts}")
                if idx < 0 or idx >= len(opts):
                    raise ValueError("Selection out of bounds")
                selected = opts[idx]
                logger.info(f"User selected option: {selected}")
                if not isinstance(selected, str) or not selected.strip():
                    raise ValueError("Empty selection")
                state = conversation_state.get(ws) or active_session
                if not state:
                    raise ValueError("No active conversation for selection")
                state.setdefault("history", []).append(
                    {"timestamp": asyncio.get_event_loop().time(), "role": "assistant_selection", "text": selected}
                )
                _append_conversation_log(
                    {
                        "session_id": state.get("session_id"),
                        "timestamp": datetime.now().isoformat(),
                        "role": "assistant_selection",
                        "text": selected,
                    }
                )
                state["speaking"] = True
            except Exception:
                try:
                    await ws.send(json.dumps({"type": "error", "message": "Invalid selection"}))
                except Exception as exc:
                    logger.error(f"Failed to send selection error: {exc}")
                continue

            # Send selection back immediately, then perform TTS in the background to avoid blocking/ping timeouts.
            try:
                for client in list(clients):
                    await client.send(json.dumps({"type": "selected", "data": selected}))
            except Exception as exc:
                logger.error(f"Failed to send selected response: {exc}")
                continue

            try:
                # Run TTS without blocking the event loop.
                logger.info(f"Performing TTS for selection: {selected}")
                async def _run_tts():
                    try:
                        await asyncio.to_thread(speak_openai, selected)
                    finally:
                        state["speaking"] = False
                        for client in list(clients):
                            try:
                                await client.send(json.dumps({"type": "tts_done"}))
                                await client.send(json.dumps({"type": "resume_listening"}))
                            except Exception as exc_inner:
                                logger.error(f"Failed to send tts_done: {exc_inner}")
                asyncio.create_task(_run_tts())
            except Exception as exc:
                logger.error(f"TTS failed: {exc}")
                try:
                    await ws.send(json.dumps({"type": "error", "message": "TTS failed"}))
                except Exception as send_exc:
                    logger.error(f"Failed to send TTS error: {send_exc}")
            continue

        # Handle incoming context (audio/image).
        if "audio_data" in data.keys() or "image_data" in data.keys():
            state = conversation_state.get(ws) or active_session
            if not state or not state.get("active"):
                logger.warning("Received audio/image without an active conversation.")
                try:
                    await ws.send(json.dumps({"type": "error", "message": "Conversation not started"}))
                except Exception as exc:
                    logger.error(f"Failed to send conversation not started error: {exc}")
                continue
            if state.get("speaking"):
                logger.info("Dropping audio input while TTS is in progress.")
                try:
                    await ws.send(json.dumps({"type": "error", "message": "TTS in progress"}))
                except Exception as exc:
                    logger.error(f"Failed to send TTS-in-progress error: {exc}")
                continue

            context = create_context(data)
            state.setdefault("history", []).append(
                {
                    "timestamp": asyncio.get_event_loop().time(),
                    "role": "user",
                    "text": context.audio_text,
                }
            )
            _append_conversation_log(
                {
                    "session_id": state.get("session_id"),
                    "timestamp": datetime.now().isoformat(),
                    "role": "user",
                    "text": context.audio_text,
                }
            )
            success = await asyncio.to_thread(
                set_response,
                context,
                state.get("history"),
                state.get("schedule_context", ""),
                state.get("core_context", ""),
                state.get("event_context", ""),
            )

            if success:
                opts = _normalize_options(context.response)
                for client in list(clients):
                    try:
                        options_map[client] = opts
                        if client == ws:
                            state["history"].append(
                                {
                                    "timestamp": asyncio.get_event_loop().time(),
                                    "role": "assistant_options",
                                    "text": opts,
                                }
                            )
                        await client.send(json.dumps({"type": "options", "data": opts}))
                    except Exception as exc:
                        logger.error(f"Failed to send options to client {client}: {exc}")
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


async def main():
    server = await websockets.serve(
        handler,
        "0.0.0.0",
        8765,
        ping_interval=30,
        ping_timeout=180,  # allow longer LLM/TTS cycles before timing out
    )
    logger.info("Server running on ws://0.0.0.0:8765")

    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
