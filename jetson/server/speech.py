import os
import shutil
import subprocess
import tempfile

import pyttsx3
from openai import OpenAI


tts = pyttsx3.init()


def speak(text: str):
    """Local TTS using pyttsx3 (system default voice)."""
    tts.say(text)
    tts.runAndWait()


def speak_openai(
    text: str,
    voice: str = "ash",
    model: str = "gpt-4o-mini-tts",
):
    """
    Generate speech via OpenAI TTS and play it immediately.

    Requires OPENAI_API_KEY in the environment.
    Uses a temporary WAV and plays with afplay (macOS) or aplay (Linux);
    if no player is available, the file path is printed.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY before calling speak_openai.")

    client = OpenAI(api_key=api_key)
    resp = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        instructions=f"Speak at the appropriate tone for {text}. Speak at a conversational pace",
        response_format="wav",
    )
    audio_bytes = resp.read()

    # Use delete=False so the player can read it; clean up after playback.
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    player = None
    if shutil.which("afplay"):
        player = ["afplay", tmp_path]
    elif shutil.which("aplay"):
        player = ["aplay", tmp_path]

    try:
        if player:
            subprocess.run(player, check=False)
        else:
            print(f"Saved TTS audio to {tmp_path}; play it manually.")
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
