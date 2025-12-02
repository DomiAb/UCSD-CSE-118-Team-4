import json
import os
import requests
import logging

from jetson.context.context import Context
from jetson.context.llm_interface import query_gemini


def set_response(context: Context) -> bool:
    logging.getLogger(__name__).debug(f"Calling LLM with context: {context}")
    try:
        if context.image is not None:
            response = query_gemini(f'Give me a possible answer or question I could ask after I heard the following text: {context.audio_text} and having seen this image at this time: {context.image}. Give me only the answer or question without any additional text.')
            context.response = response
            return True
        else:
            response = query_gemini(f'Give me a possible answer or question I could ask after I heard the following text: {context.audio_text}. Give me only the answer or question without any additional text.')
            context.response = response
            return True
    except Exception as e:
        logging.getLogger(__name__).error(f"LLM Error: {e}")
        context.response = "Default response as long as the api key is not set."
        return False
