from time import sleep

from jetson.context.speech import VoiceCollector, offline_stt


def main():
    vc = VoiceCollector()


    # add enter key so start/stop is manual for testing
    input("Press Enter to start listening...")

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
