import io
import numpy as np
import soundfile as sf
from typing import Generator
from src.tts_engine import TTSEngine, Voice, chunk_text

KOKORO_VOICES = [
    Voice("af_bella", "Bella (American Female)", "en-US"),
    Voice("af_nicole", "Nicole (American Female)", "en-US"),
    Voice("af_sarah", "Sarah (American Female)", "en-US"),
    Voice("af_sky", "Sky (American Female)", "en-US"),
    Voice("am_adam", "Adam (American Male)", "en-US"),
    Voice("am_michael", "Michael (American Male)", "en-US"),
    Voice("bf_emma", "Emma (British Female)", "en-GB"),
    Voice("bf_isabella", "Isabella (British Female)", "en-GB"),
    Voice("bm_george", "George (British Male)", "en-GB"),
    Voice("bm_lewis", "Lewis (British Male)", "en-GB"),
]

SAMPLE_RATE = 24000


class KokoroEngine(TTSEngine):
    engine_name = "kokoro"

    def __init__(self):
        self._kokoro = None  # lazy-loaded

    def _load(self):
        if self._kokoro is None:
            from kokoro_onnx import Kokoro
            self._kokoro = Kokoro("kokoro-v0_19.onnx", "voices-v1.0.bin")

    def synthesize(self, text: str, settings: dict) -> Generator[bytes, None, None]:
        self._load()
        chunks = chunk_text(text, max_chars=500)
        voice = settings.get("voice", "af_bella")
        speed = float(settings.get("speed", 1.0))

        for chunk in chunks:
            samples, sr = self._kokoro.create(chunk, voice=voice, speed=speed, lang="en-us")
            # Convert float32 numpy array to 16-bit PCM bytes
            samples_int16 = (samples * 32767).astype(np.int16)
            buf = io.BytesIO()
            sf.write(buf, samples_int16, sr, format="RAW", subtype="PCM_16")
            yield buf.getvalue()

    def list_voices(self) -> list[Voice]:
        return KOKORO_VOICES
