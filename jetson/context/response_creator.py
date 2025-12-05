import logging

from jetson.context.context import Context
from jetson.context.llm_interface import query_gemini


def _history_prefix(history: list) -> str:
    """Format conversation history into a short prefix."""
    if not history:
        return ""
    parts = []
    for turn in history:
        role = turn.get("role", "user")
        text = turn.get("text", "")
        if isinstance(text, list):
            text = "; ".join([str(t) for t in text if t])
        parts.append(f"{role}: {text}")
    return "Conversation so far:\n" + "\n".join(parts) + "\n"


def set_response(context: Context, history: list | None = None) -> bool:
    logging.getLogger(__name__).debug(f"Calling LLM with context: {context}")
    prefix = _history_prefix(history or [])
    try:
        if context.image is not None and context.audio_text is not None:
            response = query_gemini(
                f'{prefix}Give three concise answers/questions after hearing: "{context.audio_text}" and seeing this image: {context.image}. '
                "Return only the three options, separated by '|'."
            )
            context.response = response
            return True
        
        elif context.image is not None and context.audio_text is None:
            response = query_gemini(
                f'{prefix}Give three concise answers/questions after seeing this image: {context.image}. '
                "Return only the three options, separated by '|'."
            )
            context.response = response
            return True
        
        elif context.image is None and context.audio_text is not None:
            response = query_gemini(
                f'{prefix}Give three concise answers/questions after hearing: "{context.audio_text}". '
                "Return only the three options, separated by '|'."
            )
            context.response = response
            return True

        else:
            logging.getLogger(__name__).error("No input data received in context.")
            return False

    except Exception as e:
        logging.getLogger(__name__).error(f"LLM Error: {e}")
        context.response = "Default response as long as the api key is not set."
        return False


def create_context(data: dict) -> Context:
    context = Context()

    if "audio_data" in data.keys():
        audio_text = data.get("audio_data")
        logging.getLogger(__name__).info(f"Received text from HoloLens: {audio_text}")
        context.audio_text = audio_text

    if "image_data" in data.keys():
        image_data = data.get("image_data")
        logging.getLogger(__name__).info(f"Received image data from HoloLens")
        context.image = image_data

    return context
