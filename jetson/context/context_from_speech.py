import json
import os
import requests
import logging


def query_gemini(gemini_prompt: str) -> str:
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": gemini_prompt
                    }
                ]
            }
        ]
    }
    headers = {
        'x-goog-api-key': api_key,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Gemini Error: {e}")
        return "There was an error with gemini processing your request."


def call_llm(context: str) -> list[str]:
    logging.getLogger(__name__).debug(f"Calling LLM with context: {context}")
    try:
        response = query_gemini(f'You hear the following text: {context}. Give me a three possible answer or question I could ask after I heard that text. Give me only the answer or question without any additional text. The three options should be concise and to the point. Separate the three options with a semicolon ";"')
        options = [option.strip() for option in response.split(';')]
        return options
    except Exception as e:
        logging.getLogger(__name__).error(f"LLM Error: {e}")
        return ["Default response as long as the api key is not set."]


def get_audio_response(audio_data: str) -> list[str]:
    return call_llm(audio_data)
