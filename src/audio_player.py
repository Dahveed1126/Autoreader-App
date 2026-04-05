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
                try:
                    data, sr = sf.read(io.BytesIO(chunk_bytes), dtype="float32", always_2d=False)
                except Exception:
                    data = np.frombuffer(chunk_bytes, dtype=np.int16).astype(np.float32) / 32767
                    sr = sample_rate

                chunk_size = sr // 10  # 100ms chunks
                for i in range(0, len(data), chunk_size):
                    if self._stop_event.is_set():
                        return
                    self._pause_event.wait()
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
            self._pause_event.set()
            sd.stop()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            self._set_state(PlayerState.IDLE)
