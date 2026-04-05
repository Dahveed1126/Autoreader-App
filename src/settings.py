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
    import src.settings as _self
    key_file = _self.KEY_FILE
    settings_dir = _self.SETTINGS_DIR
    os.makedirs(settings_dir, exist_ok=True)
    if not os.path.exists(key_file):
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
    with open(key_file, "rb") as f:
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
    import src.settings as _self
    settings_dir = _self.SETTINGS_DIR
    settings_file = _self.SETTINGS_FILE
    os.makedirs(settings_dir, exist_ok=True)
    result = dict(DEFAULTS)
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                stored = json.load(f)
            result.update(stored)
        except (json.JSONDecodeError, OSError):
            pass
    return result


def save_settings(settings: dict) -> None:
    import src.settings as _self
    settings_dir = _self.SETTINGS_DIR
    settings_file = _self.SETTINGS_FILE
    os.makedirs(settings_dir, exist_ok=True)
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
