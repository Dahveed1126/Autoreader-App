import asyncio
import io
import numpy as np
import soundfile as sf
import edge_tts
from typing import Generator
from src.tts_engine import TTSEngine, Voice, chunk_text

SAMPLE_RATE = 24000

EDGE_VOICES = [
    Voice("en-US-AriaNeural", "Aria (US Female)", "en-US"),
    Voice("en-US-GuyNeural", "Guy (US Male)", "en-US"),
    Voice("en-US-JennyNeural", "Jenny (US Female)", "en-US"),
    Voice("en-GB-SoniaNeural", "Sonia (GB Female)", "en-GB"),
    Voice("en-GB-RyanNeural", "Ryan (GB Male)", "en-GB"),
    Voice("en-AU-NatashaNeural", "Natasha (AU Female)", "en-AU"),
]


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


class EdgeTTSEngine(TTSEngine):
    engine_name = "edge-tts"

    def synthesize(self, text: str, settings: dict) -> Generator[bytes, None, None]:
        voice = settings.get("voice", "en-US-AriaNeural")
        speed_multiplier = float(settings.get("speed", 1.0))
        rate_pct = int((speed_multiplier - 1.0) * 100)
        rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"
        chunks = chunk_text(text, max_chars=5000)
        for chunk in chunks:
            audio_bytes = _run_async(_synthesize_chunk(chunk, voice, rate_str))
            yield audio_bytes

    def list_voices(self) -> list[Voice]:
        return EDGE_VOICES


async def _synthesize_chunk(text: str, voice: str, rate: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()
