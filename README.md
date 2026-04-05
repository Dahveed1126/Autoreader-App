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

- **Highlight text** in any app, then press `Ctrl+Shift+R` to read, or right-click and select "Read Aloud with Autoreader"
- **Stop:** `Ctrl+Shift+X` or click the stop button in the floating widget
- **Pause/Resume:** Click the pause/play button in the widget or use the tray icon menu
- **Settings:** Right-click tray icon, then select Settings

## Configuration

Settings are stored in `%APPDATA%\AutoreaderApp\settings.json`. Change voice, speed, engine, and API keys via the Settings dialog.

## Running Tests

```bash
python -m pytest tests/ -v
```
