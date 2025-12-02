
class Context:
    def __init__(self, audio_text: str | None = None, image = None):
        self.audio_text = audio_text
        self.image = image
        self.response: str | None = None
