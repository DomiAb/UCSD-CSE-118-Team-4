
class Context:
    def __init__(self, audio_text: str | None = None, image = None):
        self.audio_text = audio_text
        self.image = image
        self.response: str | None = None

    def _get_normalize_options(self) -> list[str]:
        """
        Turn a raw response into a list of options.
        - Gemini returns comma-separated options; parse and enforce exactly 3.
        """
        if isinstance(self.response, list):
            opts = [o.strip() for o in self.response if isinstance(o, str) and o.strip()]
        elif isinstance(self.response, str):
            opts = [p.strip() for p in self.response.split("|") if p.strip()]
        else:
            opts = []

        if len(opts) < 3:
            # pad with empty placeholders to keep length consistent
            opts.extend([""] * (3 - len(opts)))
        if len(opts) > 3:
            opts = opts[:3]
        return opts
