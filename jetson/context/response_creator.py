import logging

from jetson.context.context import Context
from jetson.context.llm_interface import query_gemini


def set_response(context: Context) -> bool:
    logging.getLogger(__name__).debug(f"Calling LLM with context: {context}")
    try:
        if context.image is not None and context.audio_text is not None:
            response = query_gemini(f'Give me three possible answers or questions in response to the following text: {context.audio_text} and having seen this image at this time: {context.image}. Give me only the answers or questions separated by commas.')
            context.response = response
            return True
        
        elif context.image is not None and context.audio_text is None:
            response = query_gemini(f'Give me three possible answers or questions in response to having seen the following image at this time: {context.image}. Give me only the answers or questions separated by commas.')
            context.response = response
            return True
        
        elif context.image is None and context.audio_text is not None:
            response = query_gemini(f'Give me three possible answers or questions in response to having heard the following text: {context.audio_text}. Give me only the answers or questions separated by commas.')
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
