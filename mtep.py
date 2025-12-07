from time import sleep
import speech_recognition as sr

from jetson.context.speech import VoiceCollector, offline_stt


def main():
    vc = VoiceCollector()

    for i, name in enumerate(sr.Microphone.list_microphone_names()):
        print(i, name)



    # add enter key so start/stop is manual for testing
    inp = input("Enter mic number to use: ")

    mic_index = int(inp)
    vc.mic = sr.Microphone(device_index=mic_index)

    print(f"Using microphone index {mic_index}")
    input("Press Enter to start listening for 3 seconds...")

    print("Listening for 5 seconds...")
    vc.start()
    
    # 🛑 Add Print 1: Before Sleep
    print("--- DEBUG: Starting 3 second sleep ---") 
    sleep(3)
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
