from time import sleep
import speech_recognition as sr

from jetson.context.speech import VoiceCollector, offline_stt


def main():
    vc = VoiceCollector()

    print("Available microphones:")
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        print(f"{index}: {name}")

    mic_index = 2  # Change this to the appropriate mic index
    print(f"Using microphone {sr.Microphone.list_microphone_names()[mic_index]}")

    vc.mic = sr.Microphone(device_index=mic_index)
    input("Press Enter to start listening for 5 seconds...")

    print("Listening for 5 seconds...")
    vc.start()
    
    # 🛑 Add Print 1: Before Sleep
    print("--- DEBUG: Starting 5 second sleep ---") 
    sleep(5)
    # 🛑 Add Print 2: After Sleep, before stop()
    print("--- DEBUG: Sleep finished, calling vc.stop() ---")
    
    audio = vc.stop()
    
    # 🛑 Add Print 3: After stop()
    print("--- DEBUG: vc.stop() returned. Audio object acquired. ---")

    if audio is None:
        result = ""
    else:
        # 🛑 Add Print 4: Before STT
        print("--- DEBUG: Starting offline_stt (This can take a while) ---")
        result = offline_stt(audio)
        # 🛑 Add Print 5: After STT
        print("--- DEBUG: offline_stt finished. ---")


    print("Recognized text:", result)


if __name__ == "__main__":
    main()
