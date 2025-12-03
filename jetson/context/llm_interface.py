import logging
import os
import requests


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
