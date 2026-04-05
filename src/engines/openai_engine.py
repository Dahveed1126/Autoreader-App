from typing import Generator
from src.tts_engine import TTSEngine, Voice, chunk_text

OPENAI_VOICES = [
    Voice("alloy", "Alloy", "en"),
    Voice("echo", "Echo", "en"),
    Voice("fable", "Fable", "en"),
    Voice("onyx", "Onyx", "en"),
    Voice("nova", "Nova", "en"),
    Voice("shimmer", "Shimmer", "en"),
]


class OpenAIEngine(TTSEngine):
    engine_name = "openai"

    def __init__(self, api_key: str):
        self._api_key = api_key

    def synthesize(self, text: str, settings: dict) -> Generator[bytes, None, None]:
        from openai import OpenAI
        client = OpenAI(api_key=self._api_key)
        voice = settings.get("voice", "onyx")
        chunks = chunk_text(text, max_chars=4096)
        for chunk in chunks:
            response = client.audio.speech.create(
                model="tts-1-hd",
                voice=voice,
                input=chunk,
                response_format="mp3",
            )
            yield response.content

    def list_voices(self) -> list[Voice]:
        return OPENAI_VOICES
