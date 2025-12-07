import asyncio
import websockets
import speech_recognition as sr
import queue
import threading


class VoiceCollector:
    """
    Collects audio data from the microphone in the background using the 
    speech_recognition library's non-blocking listener.
    """
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        self.audio_queue = queue.Queue()
        self.listening = False
        # Holds the function provided by listen_in_background to stop listening.
        self.stop_listening_callback = None 

    def _listen_callback(self, recognizer, audio):
        """
        The function called by the background listener whenever a phrase
        (up to phrase_time_limit) is detected.
        """
        # Only process audio if the start() method hasn't been cancelled by stop()
        if self.listening:
            self.audio_queue.put(audio)

    def start(self):
        """
        Start capturing audio using the non-blocking background listener.
        """
        self.audio_queue = queue.Queue()
        
        # --- FIX: Isolate the noise adjustment in its own, safe context block ---
        print("--- DEBUG: Adjusting for ambient noise... ---")
        try:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
            print("--- DEBUG: Noise adjustment complete. ---")
        except Exception as e:
            # Handle potential failure during stream open/close here
            print(f"--- WARNING: Ambient noise adjustment failed: {e} ---")
            # We continue anyway, as the listener might still work.

        self.listening = True
        
        # --- Start the non-blocking listener (this opens a new stream) ---
        self.stop_listening_callback = self.recognizer.listen_in_background(
            self.mic, 
            self._listen_callback, 
            phrase_time_limit=3
        )

    def stop(self):
        """
        Stop capturing audio, safely terminate the background thread, 
        and return the full combined audio data.
        """
        # Ensure the background thread is stopped gracefully before continuing.
        if self.stop_listening_callback is not None:
            # wait_for_stop=True ensures the audio capture loop is cleanly 
            # shut down, resolving the hang issue.
            print("--- DEBUG: In vc.stop(), attempting to stop listening callback ---")
            self.stop_listening_callback(wait_for_stop=True) 
            self.stop_listening_callback = None
            print("--- DEBUG: stop_listening callback returned successfully ---")

        self.listening = False

        # Retrieve all collected audio chunks from the queue
        items = list(self.audio_queue.queue)
        
        if not items:
            return None

        # Combine all recorded AudioData objects into a single object
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
