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

    vc.start()
    print("Listening for 5 seconds...")
    sleep(5)
    audio = vc.stop()
    if audio is None:
        result = ""
    else:
        result = offline_stt(audio)

    print("Recognized text:", result)


if __name__ == "__main__":
    main()
