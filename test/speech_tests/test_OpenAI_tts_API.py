"""
Minimal OpenAI TTS test.
- Requires OPENAI_API_KEY in the environment.
- Saves a temporary WAV and tries to play it using the system player.
"""

import os
import shutil
import subprocess
import tempfile
from openai import OpenAI

speech_string = "Hey! I appreciate the invite, but I can't today. How's your day going? And Rex is on the mend, just resting up."


def synthesize_speech(
    text: str,
    voice: str = "ash",
    model: str = "gpt-4o-mini-tts",
    instructions: str = f"Speak at the appropriate tone for {speech_string}. Speak at a conversational pace",
):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY before running this test.")

    client = OpenAI(api_key=api_key)
    resp = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format="wav",
        instructions=instructions
    )
    audio_bytes = resp.read()
    return audio_bytes


if __name__ == "__main__":
    audio = synthesize_speech(speech_string)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio)
        tmp_path = tmp.name

    player = None
    if shutil.which("afplay"):
        player = ["afplay", tmp_path]  # macOS
    elif shutil.which("aplay"):
        player = ["aplay", tmp_path]   # Linux ALSA

    if player:
        subprocess.run(player, check=False)
        print(f"Played TTS audio via {' '.join(player)}")
    else:
        print(f"Saved TTS audio to {tmp_path}; play it with your preferred audio player.")
