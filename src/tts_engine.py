import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generator


@dataclass
class Voice:
    id: str
    name: str
    language: str = "en"


class TTSEngine(ABC):
    engine_name: str = "base"

    @abstractmethod
    def synthesize(
        self, text: str, settings: dict
    ) -> Generator[bytes, None, None]:
        """Yield raw PCM audio chunks (16-bit, 24000 Hz, mono) as bytes."""

    @abstractmethod
    def list_voices(self) -> list[Voice]:
        """Return available voices for this engine."""


def chunk_text(text: str, max_chars: int = 4000) -> list[str]:
    """Split text at sentence boundaries so each chunk is <= max_chars."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    sentence_pattern = re.compile(r'(?<=[.!?])\s+')
    sentences = sentence_pattern.split(text)

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        if len(sentence) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            for i in range(0, len(sentence), max_chars):
                chunks.append(sentence[i:i + max_chars])
            continue
        if current and len(current) + 1 + len(sentence) > max_chars:
            chunks.append(current.strip())
            current = sentence
        else:
            current = (current + " " + sentence).strip() if current else sentence

    if current:
        chunks.append(current.strip())
    return chunks


def get_engine(engine_name: str, settings: dict) -> TTSEngine:
    """Factory: return the appropriate TTSEngine instance."""
    if engine_name == "kokoro":
        from src.engines.kokoro_engine import KokoroEngine
        return KokoroEngine()
    elif engine_name == "edge-tts":
        from src.engines.edge_tts_engine import EdgeTTSEngine
        return EdgeTTSEngine()
    elif engine_name == "openai":
        from src.engines.openai_engine import OpenAIEngine
        from src.settings import decrypt_key
        return OpenAIEngine(api_key=decrypt_key(settings.get("openai_api_key", "")))
    elif engine_name == "elevenlabs":
        from src.engines.elevenlabs_engine import ElevenLabsEngine
        from src.settings import decrypt_key
        return ElevenLabsEngine(api_key=decrypt_key(settings.get("elevenlabs_api_key", "")))
    else:
        raise ValueError(f"Unknown engine: {engine_name}")
