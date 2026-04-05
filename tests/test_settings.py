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
            with patch("src.settings.KEY_FILE", str(tmp_path / "key.bin")):
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
