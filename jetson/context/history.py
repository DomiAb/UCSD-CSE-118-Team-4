import json
import logging
import pathlib

from jetson.context.llm_interface import query_gemini


logger = logging.getLogger(__name__)


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
        "Summarize this conversation between me and someone else into 1-3 concise bullet highlights that capture key points, "
        "mentions, and next steps. Keep it concise, clear and meaningful.\n\n"
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
