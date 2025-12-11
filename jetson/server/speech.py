import os
import shutil
import subprocess
import tempfile
import io
import wave

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
    silence_sec: float = 0.3,
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

    # Prepend a short silence to avoid BT speakers clipping the start.
    with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
        params = wf.getparams()
        frames = wf.readframes(wf.getnframes())
    n_channels, sampwidth, framerate = params.nchannels, params.sampwidth, params.framerate
    silence_frames = int(framerate * silence_sec)
    silence_bytes = b"\x00" * silence_frames * n_channels * sampwidth

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        with wave.open(tmp, "wb") as out:
            out.setnchannels(n_channels)
            out.setsampwidth(sampwidth)
            out.setframerate(framerate)
            out.writeframes(silence_bytes + frames)

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
