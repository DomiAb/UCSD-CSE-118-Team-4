import json
import os
import requests
import logging


def query_gemini(gemini_prompt: str) -> str:
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

    payload = json.dumps({
    "contents": [
        {
        "parts": [
            {
            "text": gemini_prompt
            }
        ]
        }
    ]
    })
    headers = {
    'x-goog-api-key': api_key,
    'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Gemini Error: {e}")
        return "There was an error with gemini processing your request."


def call_llm(context: str) -> str:
    logging.getLogger(__name__).debug(f"Calling LLM with context: {context}")
    try:
        response = query_gemini(f'Give me a possible answer or question I could ask after I heard the following text: {context}. Give me only the answer or question without any additional text.')
        return response
    except Exception as e:
        logging.getLogger(__name__).error(f"LLM Error: {e}")
        return "Default response as long as the api key is not set."


def get_audio_response(audio_data: str) -> str:
    return call_llm(audio_data)
