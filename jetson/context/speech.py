import asyncio
import websockets
import speech_recognition as sr
import queue
import threading


class VoiceCollector:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        self.audio_queue = queue.Queue()
        self.listening = False
        self.listener_thread = None

    def _listen_loop(self):
        """Background thread collecting small audio chunks."""
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.8)

            while self.listening:
                try:
                    audio = self.recognizer.listen(
                        source,
                        timeout=None,
                        phrase_time_limit=3   # small chunks
                    )
                    self.audio_queue.put(audio)
                except Exception:
                    pass  # ignore timeouts

    def start(self):
        """Start capturing audio."""
        self.audio_queue = queue.Queue()
        self.listening = True
        self.listener_thread = threading.Thread(target=self._listen_loop)
        self.listener_thread.start()

    def stop(self):
        """Stop capturing audio and return full combined audio."""
        self.listening = False
        if self.listener_thread:
            self.listener_thread.join()

        items = list(self.audio_queue.queue)
        if not items:
            return None

        combined = items[0]
        for frame in items[1:]:
            combined = sr.AudioData(
                combined.frame_data + frame.frame_data,
                combined.sample_rate,
                combined.sample_width
            )
        return combined


def offline_stt(audio_data):
    """Convert audio to text using offline PocketSphinx."""
    recognizer = sr.Recognizer()
    try:
        text = recognizer.recognize_sphinx(audio_data)
        return text
    except Exception as e:
        print("Speech recognition error:", e)
        return ""


async def handle_websocket():
    vc = VoiceCollector()

    async with websockets.connect(WEBSOCKET_URI) as ws:
        print("Connected to WebSocket server at", WEBSOCKET_URI)

        while True:
            msg = await ws.recv()

            if msg == START_MSG:
                print("Start signal received.")
                vc.start()

            elif msg == STOP_MSG:
                print("Stop signal received.")
                audio = vc.stop()
                if audio is None:
                    result = ""
                else:
                    result = offline_stt(audio)

                print("Recognized text:", result)

                # send result back to PIC (optional)
                await ws.send(result)
