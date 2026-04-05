import json
import os
from typing import Generator
from src.tts_engine import TTSEngine, Voice, chunk_text

CACHE_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "AutoreaderApp", "elevenlabs_voices.json"
)


class ElevenLabsEngine(TTSEngine):
    engine_name = "elevenlabs"

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._voices: list[Voice] | None = None

    def synthesize(self, text: str, settings: dict) -> Generator[bytes, None, None]:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=self._api_key)
        voice_id = settings.get("voice", "JBFqnCBsd6RMkjVDRZzb")
        chunks = chunk_text(text, max_chars=40000)
        for chunk in chunks:
            audio = client.text_to_speech.convert(
                text=chunk,
                voice_id=voice_id,
                model_id="eleven_flash_v2_5",
                output_format="mp3_44100_128",
            )
            if isinstance(audio, bytes):
                yield audio
            else:
                buf = b"".join(audio)
                yield buf

    def list_voices(self) -> list[Voice]:
        if self._voices is not None:
            return self._voices
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    data = json.load(f)
                self._voices = [Voice(**v) for v in data]
                return self._voices
            except Exception:
                pass
        try:
            from elevenlabs.client import ElevenLabs
            client = ElevenLabs(api_key=self._api_key)
            # get_all returns GetVoicesResponse with a .voices list;
            # each item has .voice_id and .name attributes.
            response = client.voices.get_all(show_legacy=False)
            voices = [
                Voice(id=v.voice_id, name=v.name, language="en")
                for v in response.voices
            ]
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump(
                    [{"id": v.id, "name": v.name, "language": v.language} for v in voices],
                    f,
                )
            self._voices = voices
            return voices
        except Exception:
            return [Voice("JBFqnCBsd6RMkjVDRZzb", "George (default)", "en")]
