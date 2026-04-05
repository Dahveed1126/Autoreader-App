# Autoreader App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows desktop app that reads highlighted text aloud from any application via right-click context menu or global hotkey, using a swappable multi-engine TTS backend.

**Architecture:** A Python system tray app (PyQt6) with a local socket server for context menu IPC. TTS engines share an abstract base class so the active engine can be swapped in settings. Audio streams in chunks via sounddevice so playback starts immediately.

**Tech Stack:** Python 3.11+, PyQt6, kokoro-onnx, edge-tts, openai, elevenlabs, sounddevice, soundfile, keyboard, pywin32 (registry/mutex), PyInstaller

---

## File Map

| File | Responsibility |
|------|---------------|
| `src/main.py` | Entry point: single-instance mutex, arg parsing, QApplication lifecycle |
| `src/settings.py` | Load/save `settings.json`; defaults; encrypted key storage via `cryptography` |
| `src/tts_engine.py` | Abstract `TTSEngine` base class + `Voice` dataclass + `get_engine()` factory |
| `src/engines/kokoro_engine.py` | Kokoro ONNX local engine; sentence chunking; model download prompt |
| `src/engines/edge_tts_engine.py` | edge-tts async wrapper; network error handling |
| `src/engines/openai_engine.py` | OpenAI TTS engine; 4096-char chunking |
| `src/engines/elevenlabs_engine.py` | ElevenLabs engine; voice list caching; Flash model |
| `src/audio_player.py` | sounddevice stream; pause/resume/stop thread-safe controls |
| `src/text_capture.py` | Global hotkey registration; clipboard grab/restore |
| `src/socket_server.py` | Local TCP server on 127.0.0.1:47832; receives text from CLI companion |
| `src/registry.py` | Context menu registry CRUD; auto-start registry CRUD |
| `src/tray.py` | System tray icon, menu, signals to start/pause/stop reading |
| `src/widget.py` | Floating always-on-top PyQt6 widget; play/pause/stop; auto-hide |
| `src/settings_dialog.py` | 4-tab settings dialog: Voice, Keys, Hotkeys, System |
| `scripts/autoreader_send.py` | Standalone CLI: grabs selected text, sends to socket, exits |
| `assets/icon.png` | 64x64 tray/widget icon (generated programmatically in Task 1) |
| `requirements.txt` | All pip dependencies pinned |
| `tests/test_settings.py` | Unit tests for settings load/save/defaults/encryption |
| `tests/test_text_chunker.py` | Unit tests for sentence-boundary chunking logic |
| `tests/test_audio_player.py` | Unit tests for player state machine |
| `tests/test_registry.py` | Unit tests for registry read/write (mocked winreg) |

---

## Task 1: Project Scaffold & Requirements

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/engines/__init__.py`
- Create: `tests/__init__.py`
- Create: `assets/` (directory)

- [ ] **Step 1: Create directory structure**

```bash
cd "C:/Users/David/Desktop/Auto reader"
mkdir -p src/engines tests assets scripts
touch src/__init__.py src/engines/__init__.py tests/__init__.py
```

- [ ] **Step 2: Create `requirements.txt`**

```
PyQt6>=6.6.0
kokoro-onnx>=0.4.0
edge-tts>=6.1.9
openai>=1.30.0
elevenlabs>=1.2.0
sounddevice>=0.4.6
soundfile>=0.12.1
keyboard>=0.13.5
pywin32>=306
cryptography>=42.0.0
numpy>=1.26.0
requests>=2.31.0
```

- [ ] **Step 3: Install dependencies**

```bash
cd "C:/Users/David/Desktop/Auto reader"
pip install -r requirements.txt
```

Expected: All packages install without error. Note: `kokoro-onnx` also requires `espeak-ng` on Windows — download the installer from https://github.com/espeak-ng/espeak-ng/releases and add it to PATH.

- [ ] **Step 4: Generate a simple icon programmatically**

Create `assets/generate_icon.py`:

```python
"""Run once to generate assets/icon.png"""
from PIL import Image, ImageDraw
import os

img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.ellipse([4, 4, 60, 60], fill=(52, 120, 246))
# Speaker symbol: triangle body
draw.polygon([(18, 24), (18, 40), (28, 40), (38, 50), (38, 14), (28, 24)], fill="white")
# Sound waves
draw.arc([38, 20, 52, 44], start=-60, end=60, fill="white", width=3)
draw.arc([42, 16, 58, 48], start=-60, end=60, fill="white", width=3)
os.makedirs("assets", exist_ok=True)
img.save("assets/icon.png")
print("Icon saved to assets/icon.png")
```

```bash
pip install Pillow
python assets/generate_icon.py
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt src/ tests/ assets/ scripts/
git commit -m "feat: project scaffold, dependencies, icon"
```

---

## Task 2: Settings Module

**Files:**
- Create: `src/settings.py`
- Create: `tests/test_settings.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_settings.py`:

```python
import json
import os
import tempfile
import pytest
from unittest.mock import patch

# We patch APPDATA so tests don't touch real user data
@pytest.fixture
def tmp_settings(tmp_path):
    with patch("src.settings.SETTINGS_DIR", str(tmp_path)):
        with patch("src.settings.SETTINGS_FILE", str(tmp_path / "settings.json")):
            yield tmp_path

def test_defaults_returned_when_no_file(tmp_settings):
    from src.settings import load_settings
    s = load_settings()
    assert s["engine"] == "kokoro"
    assert s["voice"] == "af_bella"
    assert s["speed"] == 1.0
    assert s["volume"] == 1.0
    assert s["hotkey_read"] == "ctrl+shift+r"
    assert s["hotkey_stop"] == "ctrl+shift+x"

def test_save_and_reload(tmp_settings):
    from src.settings import load_settings, save_settings
    s = load_settings()
    s["engine"] = "openai"
    s["speed"] = 1.5
    save_settings(s)
    s2 = load_settings()
    assert s2["engine"] == "openai"
    assert s2["speed"] == 1.5

def test_partial_file_fills_defaults(tmp_settings):
    settings_file = tmp_settings / "settings.json"
    settings_file.write_text(json.dumps({"engine": "edge-tts"}))
    from src.settings import load_settings
    s = load_settings()
    assert s["engine"] == "edge-tts"
    assert s["voice"] == "af_bella"  # default filled in

def test_encrypt_decrypt_api_key(tmp_settings):
    from src.settings import encrypt_key, decrypt_key
    key = "sk-test-1234567890abcdef"
    encrypted = encrypt_key(key)
    assert encrypted != key
    assert decrypt_key(encrypted) == key
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd "C:/Users/David/Desktop/Auto reader"
python -m pytest tests/test_settings.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.settings'`

- [ ] **Step 3: Implement `src/settings.py`**

```python
import json
import os
from pathlib import Path
from cryptography.fernet import Fernet

SETTINGS_DIR = os.path.join(os.environ.get("APPDATA", str(Path.home())), "AutoreaderApp")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")
KEY_FILE = os.path.join(SETTINGS_DIR, "key.bin")

DEFAULTS = {
    "engine": "kokoro",
    "voice": "af_bella",
    "speed": 1.0,
    "pitch": 0,
    "volume": 1.0,
    "hotkey_read": "ctrl+shift+r",
    "hotkey_stop": "ctrl+shift+x",
    "openai_api_key": "",
    "elevenlabs_api_key": "",
}


def _get_fernet() -> Fernet:
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    with open(KEY_FILE, "rb") as f:
        return Fernet(f.read())


def encrypt_key(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except Exception:
        return ""


def load_settings() -> dict:
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    result = dict(DEFAULTS)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                stored = json.load(f)
            result.update(stored)
        except (json.JSONDecodeError, OSError):
            pass
    return result


def save_settings(settings: dict) -> None:
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_settings.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/settings.py tests/test_settings.py
git commit -m "feat: settings load/save with encrypted API key storage"
```

---

## Task 3: TTS Engine Abstract Base + Text Chunker

**Files:**
- Create: `src/tts_engine.py`
- Create: `tests/test_text_chunker.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_text_chunker.py`:

```python
from src.tts_engine import chunk_text

def test_short_text_not_chunked():
    text = "Hello world."
    chunks = chunk_text(text, max_chars=500)
    assert chunks == ["Hello world."]

def test_long_text_split_at_sentence_boundary():
    text = "First sentence. Second sentence. Third sentence."
    chunks = chunk_text(text, max_chars=30)
    # Each chunk must be <= 30 chars
    for chunk in chunks:
        assert len(chunk) <= 30
    # Reassembled text must equal original (stripped)
    assert " ".join(chunks).strip() == text.strip()

def test_no_sentence_boundary_splits_at_max():
    text = "A" * 200
    chunks = chunk_text(text, max_chars=50)
    for chunk in chunks:
        assert len(chunk) <= 50

def test_empty_text_returns_empty_list():
    assert chunk_text("", max_chars=500) == []

def test_whitespace_only_returns_empty_list():
    assert chunk_text("   \n  ", max_chars=500) == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_text_chunker.py -v
```

Expected: `ImportError: cannot import name 'chunk_text' from 'src.tts_engine'`

- [ ] **Step 3: Implement `src/tts_engine.py`**

```python
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

    # Split on sentence-ending punctuation followed by whitespace
    sentence_pattern = re.compile(r'(?<=[.!?])\s+')
    sentences = sentence_pattern.split(text)

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        if len(sentence) > max_chars:
            # No sentence boundary available — hard split
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_text_chunker.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tts_engine.py tests/test_text_chunker.py
git commit -m "feat: TTSEngine abstract base, Voice dataclass, chunk_text utility"
```

---

## Task 4: Kokoro Engine

**Files:**
- Create: `src/engines/kokoro_engine.py`

- [ ] **Step 1: Verify kokoro-onnx is importable**

```bash
python -c "from kokoro_onnx import Kokoro; print('kokoro-onnx OK')"
```

Expected: `kokoro-onnx OK`. If it fails, ensure `espeak-ng` is installed and in PATH.

- [ ] **Step 2: Implement `src/engines/kokoro_engine.py`**

```python
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
```

- [ ] **Step 3: Smoke-test the engine manually**

```python
# Run interactively: python -c "..."
from src.engines.kokoro_engine import KokoroEngine
import sounddevice as sd
import numpy as np

engine = KokoroEngine()
settings = {"voice": "af_bella", "speed": 1.0}
for chunk in engine.synthesize("Hello, this is a test of the Kokoro engine.", settings):
    samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32767
    sd.play(samples, samplerate=24000)
    sd.wait()
print("Kokoro smoke test passed")
```

Expected: You hear "Hello, this is a test of the Kokoro engine." spoken aloud.

- [ ] **Step 4: Commit**

```bash
git add src/engines/kokoro_engine.py
git commit -m "feat: Kokoro ONNX local TTS engine"
```

---

## Task 5: edge-tts Engine

**Files:**
- Create: `src/engines/edge_tts_engine.py`

- [ ] **Step 1: Implement `src/engines/edge_tts_engine.py`**

```python
import asyncio
import io
import numpy as np
import soundfile as sf
import edge_tts
from typing import Generator
from src.tts_engine import TTSEngine, Voice, chunk_text

SAMPLE_RATE = 24000

# Common high-quality edge-tts voices
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
        # edge-tts rate is expressed as a percentage change string
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
```

- [ ] **Step 2: Smoke-test**

```python
from src.engines.edge_tts_engine import EdgeTTSEngine
import sounddevice as sd
import numpy as np
import io, soundfile as sf

engine = EdgeTTSEngine()
settings = {"voice": "en-US-AriaNeural", "speed": 1.0}
for chunk in engine.synthesize("Hello from edge TTS.", settings):
    data, sr = sf.read(io.BytesIO(chunk), dtype="float32")
    sd.play(data, samplerate=sr)
    sd.wait()
print("edge-tts smoke test passed")
```

Expected: Audio plays via system speakers.

- [ ] **Step 3: Commit**

```bash
git add src/engines/edge_tts_engine.py
git commit -m "feat: edge-tts engine with async streaming"
```

---

## Task 6: OpenAI & ElevenLabs Engines

**Files:**
- Create: `src/engines/openai_engine.py`
- Create: `src/engines/elevenlabs_engine.py`

- [ ] **Step 1: Implement `src/engines/openai_engine.py`**

```python
import io
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
```

- [ ] **Step 2: Implement `src/engines/elevenlabs_engine.py`**

```python
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
        # Try cache first
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    data = json.load(f)
                self._voices = [Voice(**v) for v in data]
                return self._voices
            except Exception:
                pass
        # Fetch from API
        try:
            from elevenlabs.client import ElevenLabs
            client = ElevenLabs(api_key=self._api_key)
            response = client.voices.search(show_legacy=False)
            voices = [
                Voice(id=v.voice_id, name=v.name, language="en")
                for v in response.voices
            ]
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump([{"id": v.id, "name": v.name, "language": v.language} for v in voices], f)
            self._voices = voices
            return voices
        except Exception:
            return [Voice("JBFqnCBsd6RMkjVDRZzb", "George (default)", "en")]
```

- [ ] **Step 3: Commit**

```bash
git add src/engines/openai_engine.py src/engines/elevenlabs_engine.py
git commit -m "feat: OpenAI and ElevenLabs TTS engine implementations"
```

---

## Task 7: Audio Player

**Files:**
- Create: `src/audio_player.py`
- Create: `tests/test_audio_player.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_audio_player.py`:

```python
import time
import numpy as np
from unittest.mock import patch, MagicMock
from src.audio_player import AudioPlayer, PlayerState

def test_initial_state_is_idle():
    player = AudioPlayer()
    assert player.state == PlayerState.IDLE

def test_stop_when_idle_does_nothing():
    player = AudioPlayer()
    player.stop()  # Should not raise
    assert player.state == PlayerState.IDLE

def test_state_transitions():
    player = AudioPlayer()
    assert player.state == PlayerState.IDLE
    # Simulate what play() sets internally
    player._state = PlayerState.PLAYING
    assert player.state == PlayerState.PLAYING
    player._state = PlayerState.PAUSED
    assert player.state == PlayerState.PAUSED
    player._state = PlayerState.IDLE
    assert player.state == PlayerState.IDLE
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_audio_player.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/audio_player.py`**

```python
import io
import threading
from enum import Enum, auto
from typing import Generator, Callable
import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 24000


class PlayerState(Enum):
    IDLE = auto()
    PLAYING = auto()
    PAUSED = auto()


class AudioPlayer:
    def __init__(self, on_state_change: Callable[[PlayerState], None] | None = None):
        self._state = PlayerState.IDLE
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused by default
        self._thread: threading.Thread | None = None
        self._on_state_change = on_state_change

    @property
    def state(self) -> PlayerState:
        return self._state

    def _set_state(self, state: PlayerState):
        self._state = state
        if self._on_state_change:
            self._on_state_change(state)

    def play(self, audio_gen: Generator[bytes, None, None], sample_rate: int = SAMPLE_RATE):
        """Start playing audio from a bytes generator. Stops any current playback."""
        self.stop()
        self._stop_event.clear()
        self._pause_event.set()
        self._thread = threading.Thread(
            target=self._play_loop,
            args=(audio_gen, sample_rate),
            daemon=True,
        )
        self._set_state(PlayerState.PLAYING)
        self._thread.start()

    def _play_loop(self, audio_gen: Generator[bytes, None, None], sample_rate: int):
        try:
            for chunk_bytes in audio_gen:
                if self._stop_event.is_set():
                    break
                # Decode audio chunk (handles MP3 and raw PCM)
                try:
                    data, sr = sf.read(io.BytesIO(chunk_bytes), dtype="float32", always_2d=False)
                except Exception:
                    # Raw PCM int16
                    data = np.frombuffer(chunk_bytes, dtype=np.int16).astype(np.float32) / 32767
                    sr = sample_rate

                # Play in small sub-chunks to allow pause/stop responsiveness
                chunk_size = sr // 10  # 100ms chunks
                for i in range(0, len(data), chunk_size):
                    if self._stop_event.is_set():
                        return
                    self._pause_event.wait()  # blocks if paused
                    if self._stop_event.is_set():
                        return
                    sub = data[i:i + chunk_size]
                    sd.play(sub, samplerate=sr)
                    sd.wait()
        finally:
            self._set_state(PlayerState.IDLE)

    def pause(self):
        if self._state == PlayerState.PLAYING:
            self._pause_event.clear()
            self._set_state(PlayerState.PAUSED)

    def resume(self):
        if self._state == PlayerState.PAUSED:
            self._pause_event.set()
            self._set_state(PlayerState.PLAYING)

    def stop(self):
        if self._state != PlayerState.IDLE:
            self._stop_event.set()
            self._pause_event.set()  # unblock if paused
            sd.stop()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            self._set_state(PlayerState.IDLE)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_audio_player.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/audio_player.py tests/test_audio_player.py
git commit -m "feat: threaded AudioPlayer with pause/resume/stop"
```

---

## Task 8: Socket Server + CLI Companion

**Files:**
- Create: `src/socket_server.py`
- Create: `scripts/autoreader_send.py`

- [ ] **Step 1: Implement `src/socket_server.py`**

```python
import socket
import threading
from typing import Callable

HOST = "127.0.0.1"
PORT = 47832
BUFFER_SIZE = 65536


class SocketServer:
    def __init__(self, on_text_received: Callable[[str], None]):
        self._on_text = on_text_received
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((HOST, PORT))
        self._server.listen(5)
        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def _accept_loop(self):
        while self._running:
            try:
                self._server.settimeout(1.0)
                conn, _ = self._server.accept()
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle(self, conn: socket.socket):
        with conn:
            data = b""
            while chunk := conn.recv(BUFFER_SIZE):
                data += chunk
            text = data.decode("utf-8", errors="replace").strip()
            if text:
                self._on_text(text)

    def stop(self):
        self._running = False
        if self._server:
            self._server.close()


def send_text(text: str) -> bool:
    """Send text to a running Autoreader instance. Returns True on success."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((HOST, PORT))
            s.sendall(text.encode("utf-8"))
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False
```

- [ ] **Step 2: Create `scripts/autoreader_send.py`**

```python
#!/usr/bin/env python3
"""
CLI companion script for the Windows Shell context menu.
Reads selected text from clipboard and sends it to the running Autoreader app.
Usage: autoreader_send.py
"""
import sys
import os

# Allow running from the scripts/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import ctypes
import win32clipboard

from src.socket_server import send_text


def get_clipboard_text() -> str:
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
    except Exception:
        pass
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
    return ""


def main():
    # The context menu entry runs this script after the user right-clicks on selected text.
    # Windows will have already placed the selection on the clipboard via the shell.
    # Give the clipboard a moment to settle.
    time.sleep(0.05)
    text = get_clipboard_text().strip()
    if not text:
        ctypes.windll.user32.MessageBoxW(
            0, "No text found on clipboard.", "Autoreader", 0x30
        )
        return
    if not send_text(text):
        ctypes.windll.user32.MessageBoxW(
            0,
            "Autoreader is not running.\nStart it from the system tray.",
            "Autoreader",
            0x30,
        )


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add src/socket_server.py scripts/autoreader_send.py
git commit -m "feat: local socket server and CLI companion for context menu IPC"
```

---

## Task 9: Text Capture (Hotkey + Clipboard)

**Files:**
- Create: `src/text_capture.py`

- [ ] **Step 1: Implement `src/text_capture.py`**

```python
import time
import threading
from typing import Callable
import keyboard
import win32clipboard
import win32con


def _get_clipboard() -> str:
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        return ""
    except Exception:
        return ""
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass


def _set_clipboard(text: str):
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
    except Exception:
        pass
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass


def grab_selected_text() -> str:
    """
    Grab currently selected text by simulating Ctrl+C, reading clipboard,
    then restoring the previous clipboard content.
    """
    previous = _get_clipboard()
    _set_clipboard("")  # clear so we can detect if copy worked
    time.sleep(0.05)
    keyboard.send("ctrl+c")
    time.sleep(0.15)  # wait for copy
    selected = _get_clipboard()
    # Restore previous clipboard
    if previous:
        _set_clipboard(previous)
    return selected.strip()


class HotkeyListener:
    def __init__(
        self,
        read_hotkey: str,
        stop_hotkey: str,
        on_read: Callable[[str], None],
        on_stop: Callable[[], None],
    ):
        self._read_hotkey = read_hotkey
        self._stop_hotkey = stop_hotkey
        self._on_read = on_read
        self._on_stop = on_stop
        self._registered = False

    def start(self):
        keyboard.add_hotkey(self._read_hotkey, self._handle_read, suppress=True)
        keyboard.add_hotkey(self._stop_hotkey, self._on_stop, suppress=True)
        self._registered = True

    def _handle_read(self):
        def _worker():
            text = grab_selected_text()
            if text:
                self._on_read(text)
        threading.Thread(target=_worker, daemon=True).start()

    def update_hotkeys(self, read_hotkey: str, stop_hotkey: str):
        self.stop()
        self._read_hotkey = read_hotkey
        self._stop_hotkey = stop_hotkey
        self.start()

    def stop(self):
        if self._registered:
            try:
                keyboard.remove_hotkey(self._read_hotkey)
                keyboard.remove_hotkey(self._stop_hotkey)
            except KeyError:
                pass
            self._registered = False
```

- [ ] **Step 2: Commit**

```bash
git add src/text_capture.py
git commit -m "feat: hotkey listener and clipboard-based text capture"
```

---

## Task 10: Registry Integration

**Files:**
- Create: `src/registry.py`
- Create: `tests/test_registry.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_registry.py`:

```python
from unittest.mock import patch, MagicMock, call
import winreg

def test_install_context_menu_creates_registry_keys():
    with patch("winreg.CreateKey") as mock_create, \
         patch("winreg.SetValueEx") as mock_set, \
         patch("winreg.CloseKey"):
        mock_create.return_value = MagicMock()
        from src.registry import install_context_menu
        install_context_menu("C:/path/to/autoreader_send.exe")
        assert mock_create.called
        assert mock_set.called

def test_uninstall_context_menu_deletes_key():
    with patch("winreg.DeleteKey") as mock_del, \
         patch("winreg.OpenKey") as mock_open:
        mock_open.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        from src.registry import uninstall_context_menu
        uninstall_context_menu()
        # Just verify it runs without raising
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_registry.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/registry.py`**

```python
import winreg
import os
import sys

CONTEXT_MENU_KEY = r"Software\Classes\*\shell\AutoreaderApp"
CONTEXT_MENU_COMMAND_KEY = CONTEXT_MENU_KEY + r"\command"
AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "AutoreaderApp"


def install_context_menu(companion_exe_path: str):
    """Register 'Read Aloud with Autoreader' in the Windows shell context menu."""
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_KEY) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Read Aloud with Autoreader")
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, companion_exe_path)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_COMMAND_KEY) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{companion_exe_path}"')


def uninstall_context_menu():
    """Remove the context menu registry entries."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_KEY):
            pass
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_COMMAND_KEY)
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_KEY)
    except FileNotFoundError:
        pass


def is_context_menu_installed() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_KEY):
            return True
    except FileNotFoundError:
        return False


def install_autostart(exe_path: str):
    """Add app to Windows startup registry."""
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')


def uninstall_autostart():
    """Remove app from Windows startup registry."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, AUTOSTART_NAME)
    except FileNotFoundError:
        pass


def is_autostart_installed() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY) as key:
            winreg.QueryValueEx(key, AUTOSTART_NAME)
            return True
    except FileNotFoundError:
        return False
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_registry.py -v
```

Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/registry.py tests/test_registry.py
git commit -m "feat: Windows registry helpers for context menu and auto-start"
```

---

## Task 11: Floating Widget

**Files:**
- Create: `src/widget.py`

- [ ] **Step 1: Implement `src/widget.py`**

```python
from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QIcon
from src.audio_player import PlayerState


class FloatingWidget(QWidget):
    pause_clicked = pyqtSignal()
    resume_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()

    def __init__(self, icon_path: str):
        super().__init__()
        self._drag_pos = QPoint()
        self._setup_ui(icon_path)

    def _setup_ui(self, icon_path: str):
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(180, 48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._status_label = QLabel("▶ Reading…")
        self._status_label.setStyleSheet("color: white; font-size: 11px;")

        self._pause_btn = QPushButton("⏸")
        self._play_btn = QPushButton("▶")
        self._stop_btn = QPushButton("⏹")

        for btn in (self._pause_btn, self._play_btn, self._stop_btn):
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.2); border-radius: 14px;"
                " color: white; font-size: 14px; border: none; }"
                "QPushButton:hover { background: rgba(255,255,255,0.4); }"
            )

        self._play_btn.hide()
        self._pause_btn.clicked.connect(self.pause_clicked)
        self._play_btn.clicked.connect(self.resume_clicked)
        self._stop_btn.clicked.connect(self.stop_clicked)

        layout.addWidget(self._status_label)
        layout.addWidget(self._pause_btn)
        layout.addWidget(self._play_btn)
        layout.addWidget(self._stop_btn)

        self.setStyleSheet(
            "FloatingWidget { background: rgba(30,30,30,0.85); border-radius: 24px; }"
        )

    def update_state(self, state: PlayerState):
        if state == PlayerState.PLAYING:
            self._status_label.setText("▶ Reading…")
            self._pause_btn.show()
            self._play_btn.hide()
            self.show()
        elif state == PlayerState.PAUSED:
            self._status_label.setText("⏸ Paused")
            self._pause_btn.hide()
            self._play_btn.show()
        elif state == PlayerState.IDLE:
            self.hide()

    # Allow dragging
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
```

- [ ] **Step 2: Commit**

```bash
git add src/widget.py
git commit -m "feat: floating always-on-top playback widget"
```

---

## Task 12: Settings Dialog

**Files:**
- Create: `src/settings_dialog.py`

- [ ] **Step 1: Implement `src/settings_dialog.py`**

```python
from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QSlider, QPushButton, QLineEdit,
    QCheckBox, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from src.tts_engine import get_engine
from src.settings import encrypt_key, decrypt_key

ENGINE_LABELS = {
    "kokoro": "Kokoro (Local, Free — best quality offline)",
    "edge-tts": "edge-tts (Free, requires internet)",
    "openai": "OpenAI TTS (API key required — $30/1M chars)",
    "elevenlabs": "ElevenLabs (API key required — best expressiveness)",
}


class SettingsDialog(QDialog):
    settings_saved = pyqtSignal(dict)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = dict(settings)
        self.setWindowTitle("Autoreader Settings")
        self.setMinimumWidth(480)
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._tabs.addTab(self._build_voice_tab(), "Voice")
        self._tabs.addTab(self._build_keys_tab(), "API Keys")
        self._tabs.addTab(self._build_hotkeys_tab(), "Hotkeys")
        self._tabs.addTab(self._build_system_tab(), "System")

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self._on_save)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _build_voice_tab(self):
        w = QWidget()
        form = QFormLayout(w)

        self._engine_combo = QComboBox()
        for key, label in ENGINE_LABELS.items():
            self._engine_combo.addItem(label, key)
        self._engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        form.addRow("Engine:", self._engine_combo)

        self._voice_combo = QComboBox()
        form.addRow("Voice:", self._voice_combo)

        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(50, 300)  # 0.5x to 3.0x
        self._speed_label = QLabel("1.0x")
        self._speed_slider.valueChanged.connect(
            lambda v: self._speed_label.setText(f"{v/100:.1f}x")
        )
        speed_row = QHBoxLayout()
        speed_row.addWidget(self._speed_slider)
        speed_row.addWidget(self._speed_label)
        speed_widget = QWidget()
        speed_widget.setLayout(speed_row)
        form.addRow("Speed:", speed_widget)

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_label = QLabel("100%")
        self._volume_slider.valueChanged.connect(
            lambda v: self._volume_label.setText(f"{v}%")
        )
        vol_row = QHBoxLayout()
        vol_row.addWidget(self._volume_slider)
        vol_row.addWidget(self._volume_label)
        vol_widget = QWidget()
        vol_widget.setLayout(vol_row)
        form.addRow("Volume:", vol_widget)

        test_btn = QPushButton("Test Voice")
        test_btn.clicked.connect(self._on_test)
        form.addRow("", test_btn)
        return w

    def _build_keys_tab(self):
        w = QWidget()
        form = QFormLayout(w)

        self._openai_key_edit = QLineEdit()
        self._openai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._openai_key_edit.setPlaceholderText("sk-...")
        openai_verify = QPushButton("Verify")
        openai_verify.clicked.connect(lambda: self._verify_key("openai"))
        openai_row = QHBoxLayout()
        openai_row.addWidget(self._openai_key_edit)
        openai_row.addWidget(openai_verify)
        openai_widget = QWidget()
        openai_widget.setLayout(openai_row)
        form.addRow("OpenAI API Key:", openai_widget)

        self._elevenlabs_key_edit = QLineEdit()
        self._elevenlabs_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._elevenlabs_key_edit.setPlaceholderText("Your ElevenLabs API key")
        el_verify = QPushButton("Verify")
        el_verify.clicked.connect(lambda: self._verify_key("elevenlabs"))
        el_row = QHBoxLayout()
        el_row.addWidget(self._elevenlabs_key_edit)
        el_row.addWidget(el_verify)
        el_widget = QWidget()
        el_widget.setLayout(el_row)
        form.addRow("ElevenLabs API Key:", el_widget)

        cost_note = QLabel(
            "Kokoro & edge-tts are free.\n"
            "OpenAI tts-1-hd: $30/1M chars.\n"
            "ElevenLabs Flash: ~$165/1M chars."
        )
        cost_note.setStyleSheet("color: gray; font-size: 11px;")
        form.addRow("", cost_note)
        return w

    def _build_hotkeys_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        self._read_hotkey_edit = QLineEdit()
        self._read_hotkey_edit.setPlaceholderText("e.g. ctrl+shift+r")
        form.addRow("Read Hotkey:", self._read_hotkey_edit)
        self._stop_hotkey_edit = QLineEdit()
        self._stop_hotkey_edit.setPlaceholderText("e.g. ctrl+shift+x")
        form.addRow("Stop Hotkey:", self._stop_hotkey_edit)
        return w

    def _build_system_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self._autostart_check = QCheckBox("Start Autoreader when Windows starts")
        layout.addWidget(self._autostart_check)
        from src.registry import is_context_menu_installed
        self._context_menu_btn = QPushButton(
            "Remove Context Menu Entry" if is_context_menu_installed()
            else "Install Context Menu Entry"
        )
        self._context_menu_btn.clicked.connect(self._toggle_context_menu)
        layout.addWidget(self._context_menu_btn)
        layout.addStretch()
        return w

    def _populate(self):
        s = self._settings
        # Engine
        engine = s.get("engine", "kokoro")
        idx = list(ENGINE_LABELS.keys()).index(engine) if engine in ENGINE_LABELS else 0
        self._engine_combo.setCurrentIndex(idx)
        self._refresh_voices()
        # Speed
        self._speed_slider.setValue(int(float(s.get("speed", 1.0)) * 100))
        # Volume
        self._volume_slider.setValue(int(float(s.get("volume", 1.0)) * 100))
        # API keys (decrypted for display)
        self._openai_key_edit.setText(decrypt_key(s.get("openai_api_key", "")))
        self._elevenlabs_key_edit.setText(decrypt_key(s.get("elevenlabs_api_key", "")))
        # Hotkeys
        self._read_hotkey_edit.setText(s.get("hotkey_read", "ctrl+shift+r"))
        self._stop_hotkey_edit.setText(s.get("hotkey_stop", "ctrl+shift+x"))
        # Auto-start
        from src.registry import is_autostart_installed
        self._autostart_check.setChecked(is_autostart_installed())

    def _on_engine_changed(self, _):
        self._refresh_voices()

    def _refresh_voices(self):
        self._voice_combo.clear()
        engine_key = self._engine_combo.currentData()
        try:
            engine = get_engine(engine_key, self._settings)
            for voice in engine.list_voices():
                self._voice_combo.addItem(voice.name, voice.id)
            # Select current voice if present
            current = self._settings.get("voice", "")
            for i in range(self._voice_combo.count()):
                if self._voice_combo.itemData(i) == current:
                    self._voice_combo.setCurrentIndex(i)
                    break
        except Exception:
            pass

    def _verify_key(self, provider: str):
        if provider == "openai":
            key = self._openai_key_edit.text().strip()
            if not key:
                QMessageBox.warning(self, "No Key", "Enter an OpenAI API key first.")
                return
            try:
                from openai import OpenAI
                client = OpenAI(api_key=key)
                client.models.list()
                QMessageBox.information(self, "Valid", "OpenAI API key is valid.")
            except Exception as e:
                QMessageBox.critical(self, "Invalid", f"Key verification failed:\n{e}")
        elif provider == "elevenlabs":
            key = self._elevenlabs_key_edit.text().strip()
            if not key:
                QMessageBox.warning(self, "No Key", "Enter an ElevenLabs API key first.")
                return
            try:
                from elevenlabs.client import ElevenLabs
                client = ElevenLabs(api_key=key)
                client.voices.search(show_legacy=False)
                QMessageBox.information(self, "Valid", "ElevenLabs API key is valid.")
            except Exception as e:
                QMessageBox.critical(self, "Invalid", f"Key verification failed:\n{e}")

    def _on_test(self):
        engine_key = self._engine_combo.currentData()
        voice_id = self._voice_combo.currentData()
        test_settings = dict(self._settings)
        test_settings["voice"] = voice_id
        test_settings["speed"] = self._speed_slider.value() / 100
        test_settings["volume"] = self._volume_slider.value() / 100
        try:
            from src.audio_player import AudioPlayer
            engine = get_engine(engine_key, test_settings)
            player = AudioPlayer()
            gen = engine.synthesize("This is a test of the selected voice.", test_settings)
            player.play(gen)
        except Exception as e:
            QMessageBox.critical(self, "Test Failed", str(e))

    def _toggle_context_menu(self):
        import sys
        from src.registry import (
            install_context_menu, uninstall_context_menu, is_context_menu_installed
        )
        exe = sys.executable  # In packaged build this will be the companion exe path
        if is_context_menu_installed():
            uninstall_context_menu()
            self._context_menu_btn.setText("Install Context Menu Entry")
        else:
            install_context_menu(exe)
            self._context_menu_btn.setText("Remove Context Menu Entry")

    def _on_save(self):
        s = self._settings
        s["engine"] = self._engine_combo.currentData()
        s["voice"] = self._voice_combo.currentData() or s.get("voice", "af_bella")
        s["speed"] = self._speed_slider.value() / 100
        s["volume"] = self._volume_slider.value() / 100
        s["hotkey_read"] = self._read_hotkey_edit.text().strip() or "ctrl+shift+r"
        s["hotkey_stop"] = self._stop_hotkey_edit.text().strip() or "ctrl+shift+x"
        # Encrypt API keys before saving
        oai = self._openai_key_edit.text().strip()
        el = self._elevenlabs_key_edit.text().strip()
        s["openai_api_key"] = encrypt_key(oai) if oai else ""
        s["elevenlabs_api_key"] = encrypt_key(el) if el else ""
        # Auto-start
        from src.registry import install_autostart, uninstall_autostart
        import sys
        if self._autostart_check.isChecked():
            install_autostart(sys.executable)
        else:
            uninstall_autostart()
        from src.settings import save_settings
        save_settings(s)
        self.settings_saved.emit(s)
        self.accept()
```

- [ ] **Step 2: Commit**

```bash
git add src/settings_dialog.py
git commit -m "feat: 4-tab settings dialog with voice, API keys, hotkeys, system"
```

---

## Task 13: System Tray

**Files:**
- Create: `src/tray.py`

- [ ] **Step 1: Implement `src/tray.py`**

```python
import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal
from src.audio_player import PlayerState


class TrayIcon(QObject):
    read_requested = pyqtSignal(str)

    def __init__(self, icon_path: str, app: QApplication):
        super().__init__()
        self._app = app
        self._icon = QSystemTrayIcon(QIcon(icon_path), app)
        self._icon.setToolTip("Autoreader — idle")
        self._menu = QMenu()
        self._build_menu()
        self._icon.setContextMenu(self._menu)
        self._icon.show()

        self._pause_action: QAction | None = None
        self._resume_action: QAction | None = None
        self._stop_action: QAction | None = None

    def _build_menu(self):
        self._pause_action = self._menu.addAction("Pause")
        self._pause_action.setEnabled(False)
        self._resume_action = self._menu.addAction("Resume")
        self._resume_action.setEnabled(False)
        self._stop_action = self._menu.addAction("Stop")
        self._stop_action.setEnabled(False)
        self._menu.addSeparator()
        settings_action = self._menu.addAction("Settings…")
        settings_action.triggered.connect(self._open_settings)
        self._menu.addSeparator()
        quit_action = self._menu.addAction("Quit")
        quit_action.triggered.connect(self._quit)

    def set_player_callbacks(self, on_pause, on_resume, on_stop):
        self._pause_action.triggered.connect(on_pause)
        self._resume_action.triggered.connect(on_resume)
        self._stop_action.triggered.connect(on_stop)

    def set_settings_callback(self, on_settings):
        self._settings_callback = on_settings

    def _open_settings(self):
        if hasattr(self, "_settings_callback"):
            self._settings_callback()

    def update_state(self, state: PlayerState):
        if state == PlayerState.PLAYING:
            self._icon.setToolTip("Autoreader — reading…")
            self._pause_action.setEnabled(True)
            self._resume_action.setEnabled(False)
            self._stop_action.setEnabled(True)
        elif state == PlayerState.PAUSED:
            self._icon.setToolTip("Autoreader — paused")
            self._pause_action.setEnabled(False)
            self._resume_action.setEnabled(True)
            self._stop_action.setEnabled(True)
        elif state == PlayerState.IDLE:
            self._icon.setToolTip("Autoreader — idle")
            self._pause_action.setEnabled(False)
            self._resume_action.setEnabled(False)
            self._stop_action.setEnabled(False)

    def show_message(self, title: str, message: str):
        self._icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)

    def _quit(self):
        self._app.quit()
```

- [ ] **Step 2: Commit**

```bash
git add src/tray.py
git commit -m "feat: system tray icon with pause/resume/stop/settings/quit menu"
```

---

## Task 14: Main Entry Point

**Files:**
- Create: `src/main.py`

- [ ] **Step 1: Implement `src/main.py`**

```python
import sys
import os
import ctypes
import threading

# Single-instance mutex
MUTEX_NAME = "AutoreaderAppMutex_v1"

def _check_single_instance() -> bool:
    """Returns True if this is the first instance, False if another is running."""
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = ctypes.windll.kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    return last_error != ERROR_ALREADY_EXISTS


def main():
    if not _check_single_instance():
        # Notify via socket if another instance is running
        from src.socket_server import send_text
        send_text("__FOCUS__")
        sys.exit(0)

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    from src.settings import load_settings, save_settings
    from src.tts_engine import get_engine
    from src.audio_player import AudioPlayer, PlayerState
    from src.text_capture import HotkeyListener
    from src.socket_server import SocketServer
    from src.registry import install_context_menu, install_autostart, is_autostart_installed
    from src.tray import TrayIcon
    from src.widget import FloatingWidget

    ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
    ICON_PATH = os.path.join(ASSETS_DIR, "icon.png")
    SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
    COMPANION_PATH = os.path.join(SCRIPTS_DIR, "autoreader_send.py")

    settings = load_settings()

    # Install auto-start and context menu on first run
    if not is_autostart_installed():
        install_autostart(sys.executable)
    from src.registry import is_context_menu_installed
    if not is_context_menu_installed():
        install_context_menu(COMPANION_PATH)

    engine_instance = get_engine(settings["engine"], settings)

    player = AudioPlayer()
    tray = TrayIcon(ICON_PATH, app)
    widget = FloatingWidget(ICON_PATH)

    def _on_state_change(state: PlayerState):
        tray.update_state(state)
        widget.update_state(state)

    player._on_state_change = _on_state_change

    def _read_text(text: str):
        if not text.strip():
            tray.show_message("Autoreader", "No text selected.")
            return
        nonlocal engine_instance
        try:
            engine_instance = get_engine(settings["engine"], settings)
            gen = engine_instance.synthesize(text, settings)
            player.play(gen)
        except Exception as e:
            tray.show_message("Autoreader Error", str(e))

    hotkeys = HotkeyListener(
        read_hotkey=settings["hotkey_read"],
        stop_hotkey=settings["hotkey_stop"],
        on_read=_read_text,
        on_stop=player.stop,
    )
    hotkeys.start()

    socket_server = SocketServer(on_text_received=_read_text)
    socket_server.start()

    tray.set_player_callbacks(
        on_pause=player.pause,
        on_resume=player.resume,
        on_stop=player.stop,
    )

    def _open_settings():
        from src.settings_dialog import SettingsDialog
        dialog = SettingsDialog(settings)
        def _on_saved(new_settings):
            settings.update(new_settings)
            hotkeys.update_hotkeys(
                settings["hotkey_read"],
                settings["hotkey_stop"],
            )
        dialog.settings_saved.connect(_on_saved)
        dialog.exec()

    tray.set_settings_callback(_open_settings)

    widget.pause_clicked.connect(player.pause)
    widget.resume_clicked.connect(player.resume)
    widget.stop_clicked.connect(player.stop)

    # Position widget bottom-right
    screen = app.primaryScreen().geometry()
    widget.move(screen.width() - widget.width() - 20, screen.height() - widget.height() - 60)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the app**

```bash
cd "C:/Users/David/Desktop/Auto reader"
python src/main.py
```

Expected: Tray icon appears in the system tray. No errors in console.

- [ ] **Step 3: Commit**

```bash
git add src/main.py
git commit -m "feat: main entry point with single-instance lock and full app wiring"
```

---

## Task 15: Run Full Test Suite & Fix Issues

- [ ] **Step 1: Run all tests**

```bash
cd "C:/Users/David/Desktop/Auto reader"
python -m pytest tests/ -v
```

Expected: All tests PASS (settings, text_chunker, audio_player, registry).

- [ ] **Step 2: End-to-end smoke test — hotkey**

1. Start the app: `python src/main.py`
2. Open Notepad, type some text, select it
3. Press `Ctrl+Shift+R`
4. Expected: Floating widget appears, text is read aloud

- [ ] **Step 3: End-to-end smoke test — context menu**

1. With app running, open any application with text
2. Select some text, right-click
3. Expected: "Read Aloud with Autoreader" appears in context menu
4. Click it — text should be read aloud

- [ ] **Step 4: End-to-end smoke test — settings**

1. Right-click tray icon → Settings
2. Change engine to edge-tts, click Test Voice
3. Expected: Audio plays through speakers

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve issues found during end-to-end testing"
```

---

## Task 16: README + Push

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

```markdown
# Autoreader App

Read any highlighted text aloud from any Windows application. Right-click selected text and choose **"Read Aloud with Autoreader"**, or press `Ctrl+Shift+R`.

## Features

- System-wide text-to-speech from any app
- Right-click context menu + global hotkey triggers
- Multiple TTS engines:
  - **Kokoro** (default) — local, offline, high quality, free
  - **edge-tts** — free Microsoft neural voices (requires internet)
  - **OpenAI TTS** — best value cloud ($30/1M chars)
  - **ElevenLabs** — most expressive cloud voices
- Floating playback widget with pause/resume/stop
- System tray with full controls
- Configurable voices, speed, volume, hotkeys
- Starts automatically with Windows

## Requirements

- Windows 10/11
- Python 3.11+
- [espeak-ng](https://github.com/espeak-ng/espeak-ng/releases) (required for Kokoro engine — add to PATH after installing)

## Installation

```bash
git clone https://github.com/Dahveed1126/Autoreader-App.git
cd Autoreader-App
pip install -r requirements.txt
python src/main.py
```

## Usage

- **Highlight text** in any app → `Ctrl+Shift+R` to read, or right-click → "Read Aloud with Autoreader"
- **Stop:** `Ctrl+Shift+X` or click ⏹ in the floating widget
- **Pause/Resume:** Click ⏸/▶ in the widget or use the tray icon menu
- **Settings:** Right-click tray icon → Settings

## Configuration

Settings are stored in `%APPDATA%\AutoreaderApp\settings.json`. Change voice, speed, engine, and API keys via the Settings dialog.
```

- [ ] **Step 2: Commit and push**

```bash
git add README.md
git commit -m "docs: add README with setup and usage instructions"
git push
```

---

## Task 17: (Optional) PyInstaller Packaging

- [ ] **Step 1: Install PyInstaller**

```bash
pip install pyinstaller
```

- [ ] **Step 2: Create `autoreader.spec`**

```python
# autoreader.spec
block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('assets/', 'assets/')],
    hiddenimports=['kokoro_onnx', 'edge_tts', 'sounddevice', 'soundfile'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='Autoreader',
    icon='assets/icon.png',
    console=False,
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name='Autoreader')
```

- [ ] **Step 3: Build**

```bash
pyinstaller autoreader.spec
```

Expected: `dist/Autoreader/Autoreader.exe` created. Test by running it directly.

- [ ] **Step 4: Commit**

```bash
git add autoreader.spec
git commit -m "build: add PyInstaller spec for Windows packaging"
git push
```
