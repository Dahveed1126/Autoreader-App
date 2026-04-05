import time
import numpy as np
from unittest.mock import patch, MagicMock
from src.audio_player import AudioPlayer, PlayerState

def test_initial_state_is_idle():
    player = AudioPlayer()
    assert player.state == PlayerState.IDLE

def test_stop_when_idle_does_nothing():
    player = AudioPlayer()
    player.stop()
    assert player.state == PlayerState.IDLE

def test_state_transitions():
    player = AudioPlayer()
    assert player.state == PlayerState.IDLE
    player._state = PlayerState.PLAYING
    assert player.state == PlayerState.PLAYING
    player._state = PlayerState.PAUSED
    assert player.state == PlayerState.PAUSED
    player._state = PlayerState.IDLE
    assert player.state == PlayerState.IDLE
