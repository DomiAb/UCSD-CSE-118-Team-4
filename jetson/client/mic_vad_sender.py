"""
Microphone VAD + STT sender for SpeechLens.

Listens on the Pi/Jetson mic, detects end-of-speech with webrtcvad, runs STT,
then sends the transcript to the websocket server as `{"audio_data": "<text>"}`.

Dependencies:
    pip install sounddevice webrtcvad websockets openai
Environment:
    OPENAI_API_KEY   # for Whisper STT
    WS_URL           # ws://<server>:8765 (defaults below)

Notes:
    - This runs locally on the Pi/Jetson, not on the server.
    - Audio is captured mono, 16 kHz. Adjust DEVICE_INDEX if needed.
"""

import argparse
import asyncio
import collections
import json
import os
import tempfile
import time
import wave

import websockets
import webrtcvad
from openai import OpenAI

WS_URL = os.getenv("WS_URL", "ws://localhost:8765")
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30  # 10, 20, or 30 ms
DEVICE_INDEX = None  # set to an integer device id if needed
VAD_AGGRESSIVENESS = 2  # 0-3
MIN_SPEECH_FRAMES = 5  # minimum voiced frames (~150ms at 30ms frames)
PAUSE_TIMEOUT = 15.0  # seconds to auto-resume if no tts_done arrives


def frame_generator(frame_duration_ms, audio, sample_rate):
    n = int(sample_rate * frame_duration_ms / 1000) * 2  # 16-bit mono
    for i in range(0, len(audio), n):
        yield audio[i : i + n]


def vad_collect(audio_bytes, vad, frame_duration_ms):
    frames = list(frame_generator(frame_duration_ms, audio_bytes, SAMPLE_RATE))
    voiced = []
    for f in frames:
        if len(f) < int(SAMPLE_RATE * frame_duration_ms / 1000) * 2:
            continue
        if vad.is_speech(f, SAMPLE_RATE):
            voiced.append(f)
    return b"".join(frames) if len(voiced) >= MIN_SPEECH_FRAMES else b""


def record_utterance(timeout=5.0, silence_timeout=1.0):
    import sounddevice as sd  # lazy import; not needed if using --file
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    buffer = []
    silent_for = 0.0
    total_time = 0.0
    frame_size = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
    speech_frames = 0

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=frame_size,
        device=DEVICE_INDEX,
        dtype="int16",
        channels=1,
    ) as stream:
        while total_time < timeout:
            chunk, _ = stream.read(frame_size)
            buffer.append(chunk)
            total_time += FRAME_DURATION_MS / 1000
            if not vad.is_speech(chunk, SAMPLE_RATE):
                silent_for += FRAME_DURATION_MS / 1000
            else:
                speech_frames += 1
                silent_for = 0.0
            if silent_for >= silence_timeout and total_time > 0.5:
                break
    if speech_frames < MIN_SPEECH_FRAMES:
        return b""
    return b"".join(buffer)


def transcribe_wav(path: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY for Whisper STT.")
    client = OpenAI(api_key=api_key)
    with open(path, "rb") as f:
        resp = client.audio.transcriptions.create(model="whisper-1", file=f, language="en")
    return resp.text.strip()


async def send_audio_data(text: str, url: str | None = None):
    return {"audio_data": text, "url": url or WS_URL}


async def main():
    parser = argparse.ArgumentParser(description="VAD+STT sender for SpeechLens.")
    parser.add_argument(
        "--file", help="Optional WAV file to transcribe instead of mic capture."
    )
    parser.add_argument(
        "--ws", default=WS_URL, help=f"WebSocket URL (default: {WS_URL})"
    )
    parser.add_argument(
        "--no-send", action="store_true", help="Do not send to WS; just print transcript."
    )
    parser.add_argument(
        "--once", action="store_true", help="Process only one utterance/file then exit."
    )
    args = parser.parse_args()

    ws_url = args.ws or WS_URL

    paused = False
    last_send_ts = 0.0

    async def process_audio(raw_bytes):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(raw_bytes)
        try:
            text = transcribe_wav(wav_path)
            if text and len(text.strip()) >= 3:
                print(f"Transcribed: {text}")
                if not args.no_send:
                    return await send_audio_data(text, url=ws_url)
        except Exception as exc:
            print(f"STT/send failed: {exc}")
        return None

    if args.file:
        with open(args.file, "rb") as f:
            raw = f.read()
        payload = await process_audio(raw)
        if payload:
            async with websockets.connect(ws_url) as ws:
                await ws.send(json.dumps(payload))
        return

    while True:
        paused = False
        last_send_ts = 0.0
        try:
            async with websockets.connect(ws_url) as ws:

                async def recv_loop():
                    nonlocal paused, last_send_ts
                    async for msg in ws:
                        try:
                            data = json.loads(msg)
                            mtype = data.get("type")
                            if mtype in {"options", "selected"}:
                                paused = True
                                if not last_send_ts:
                                    last_send_ts = time.time()
                                print(f"[WS] Received {mtype}, pausing capture.")
                            elif mtype == "tts_done":
                                paused = False
                                last_send_ts = 0.0
                                print("[WS] Received tts_done, resuming capture.")
                            else:
                                print(f"[WS] Received {mtype}")
                        except Exception:
                            continue

                recv_task = asyncio.create_task(recv_loop())

                try:
                    while True:
                        if paused:
                            await asyncio.sleep(0.2)
                            continue
                        print("Listening...")
                        raw = record_utterance()
                        if not raw:
                            continue
                        payload = await process_audio(raw)
                        if payload:
                            await ws.send(json.dumps(payload))
                            paused = True  # wait for selection/tts_done before sending next
                            last_send_ts = time.time()
                        if paused and last_send_ts and (time.time() - last_send_ts) > PAUSE_TIMEOUT:
                            print("[WS] Pause timeout exceeded; resuming capture.")
                            paused = False
                            last_send_ts = 0.0
                        if args.once:
                            break
                finally:
                    recv_task.cancel()
                    try:
                        await recv_task
                    except Exception:
                        pass
            if args.once:
                break
        except Exception as exc:
            print(f"[WS] Connection error: {exc}, retrying in 2s")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
