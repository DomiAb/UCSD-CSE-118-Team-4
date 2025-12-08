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
        self.listening = False  # The state flag
        # Holds the function provided by listen_in_background to stop listening.
        self.stop_listening_callback = None 

    def _listen_callback(self, recognizer, audio):
        """
        The function called by the background listener whenever a phrase
        (up to phrase_time_limit) is detected.
        """
        # Only process audio if the start() method hasn't been cancelled by stop()
        # This check is good practice but less critical than the one in start()
        if self.listening:
            self.audio_queue.put(audio)

    def start(self):
        """
        Start capturing audio using the non-blocking background listener.
        
        FIX: Added a check to prevent multiple concurrent listeners.
        """
        # --- FIX: Check if we are already listening ---
        if self.listening:
            print("--- WARNING: VoiceCollector is already listening. Ignoring start() call. ---")
            return
            
        self.audio_queue = queue.Queue()
        self.listening = True # Set the state immediately before starting the listener

        # --- Refinement: Ambient noise adjustment only needs to be done once,
        #     but it's safe to do it before every session to ensure accuracy.
        #     The fix is ensuring we only launch one listener. ---
        print("--- DEBUG: Adjusting for ambient noise... ---")
        try:
            # It's better to isolate the adjustment logic completely.
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
            print("--- DEBUG: Noise adjustment complete. ---")
        except Exception as e:
            print(f"--- WARNING: Ambient noise adjustment failed: {e} ---")
            # We continue anyway.

        # --- Start the non-blocking listener (this opens a new stream) ---
        print("--- DEBUG: Starting new background listener thread ---")
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
        # --- FIX: Check if we are listening before attempting to stop ---
        if not self.listening:
            print("--- WARNING: VoiceCollector is not listening. Ignoring stop() call. ---")
            return None # Or return the previous data if that's desired, but None is safer.

        # Ensure the background thread is stopped gracefully before continuing.
        if self.stop_listening_callback is not None:
            # wait_for_stop=True ensures the audio capture loop is cleanly 
            # shut down.
            print("--- DEBUG: In vc.stop(), attempting to stop listening callback ---")
            # Call the stored stop function
            self.stop_listening_callback(wait_for_stop=True) 
            self.stop_listening_callback = None
            print("--- DEBUG: stop_listening callback returned successfully ---")

        self.listening = False # Reset the state
        
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
