# Autoreader App — Design Spec

## Overview

A Windows desktop application that lets users highlight text in any application, right-click (or use a global hotkey), and have the selected text read aloud. Supports multiple TTS engines: Kokoro (local, free, high-quality default), edge-tts (internet-based fallback), and optional cloud engines (OpenAI, ElevenLabs) via user-supplied API keys.

## Tech Stack

- **Language:** Python 3.11+
- **UI Framework:** PyQt6 (system tray, floating widget, settings dialog)
- **TTS Engines:**
  - Kokoro 82M (default — local, offline, Apache 2.0)
  - edge-tts (internet fallback — free Microsoft neural voices)
  - OpenAI TTS (optional — user supplies API key, $30/1M chars)
  - ElevenLabs (optional — user supplies API key, best expressiveness)
- **Audio Playback:** sounddevice + soundfile
- **Hotkeys:** keyboard or pynput
- **Packaging:** PyInstaller (single-folder distribution)
- **Installer (optional):** Inno Setup or NSIS

## Architecture

Five main components:

### 1. System Tray Service (`tray.py`)

The main process. Always running in the background. Hosts the tray icon with a right-click menu:
- Pause / Resume
- Stop
- Settings
- Remove Context Menu
- Quit

### 2. Text Capture Layer (`text_capture.py`, `socket_server.py`)

Two triggers to grab selected text:

**Windows Shell Context Menu:**
- Registers `HKCU\Software\Classes\*\shell\AutoreaderApp` on first launch
- Adds "Read Aloud with Autoreader" to the native right-click menu
- Context menu invokes a lightweight CLI companion script (`autoreader_send.py`) that sends selected text to the main process via a localhost socket

**Global Hotkey:**
- Default: `Ctrl+Shift+R` to read, `Ctrl+Shift+X` to stop
- Simulates `Ctrl+C` to grab selected text from clipboard
- Restores previous clipboard contents after capture

### 3. TTS Engine Interface (`tts_engine.py`, `engines/`)

A swappable engine interface. All engines implement the same abstract base class:

```
TTSEngine (abstract)
  ├── synthesize(text, settings) -> audio_chunks (generator)
  ├── list_voices() -> list[Voice]
  └── engine_name: str

KokoroEngine(TTSEngine)     # local, default
EdgeTTSEngine(TTSEngine)    # internet-based fallback
OpenAIEngine(TTSEngine)     # cloud, requires API key
ElevenLabsEngine(TTSEngine) # cloud, requires API key
```

The active engine is selected in settings. API keys are stored encrypted in `settings.json`. If Kokoro is selected but its model weights aren't downloaded yet, the app prompts to download on first use (~350MB, one-time).

**Engine-specific notes:**
- **Kokoro:** Uses `kokoro-onnx` for CPU inference; chunks text at sentence boundaries; 50 voices; no internet needed
- **edge-tts:** Async streaming; falls back gracefully if no internet
- **OpenAI:** 4,096 char limit per request — engine auto-chunks; 6 voices
- **ElevenLabs:** 40,000 char limit (Flash model); voice list fetched from API and cached locally

### 4. Floating Widget (`widget.py`)

- Small always-on-top PyQt6 window
- Play/pause/stop buttons with a progress indicator
- Appears when reading starts, can be dragged around
- Auto-hides when idle

### 5. Settings Dialog (`settings_dialog.py`)

Accessible from tray icon → "Settings". Tabs:

- **Voice tab:** Engine selector dropdown, voice dropdown (populated per engine), speed/pitch/volume sliders, "Test" button
- **Keys tab:** API key fields for OpenAI and ElevenLabs (masked input), "Verify Key" button, usage display for cloud engines
- **Hotkeys tab:** Configurable read/stop hotkeys
- **System tab:** Auto-start toggle, context menu install/remove button

## Data Flow

### Startup
1. App launches → checks single-instance lock (named mutex)
2. Loads settings from `%APPDATA%/AutoreaderApp/settings.json`
3. Initializes selected TTS engine (loads Kokoro model weights if local)
4. Registers global hotkey listener
5. Creates system tray icon
6. Starts local socket server for context menu communication

### Reading
1. User highlights text → triggers via context menu or hotkey
2. Context menu path: shell launches CLI script → sends text over local socket → main process
3. Hotkey path: simulates Ctrl+C → reads clipboard → restores previous clipboard
4. Text passed to active TTS engine; long text auto-chunked at sentence boundaries
5. Engine streams audio chunks → playback starts immediately via sounddevice
6. Floating widget appears with controls
7. User can pause/resume/stop via widget, tray, or hotkey

## Settings

Stored in `%APPDATA%/AutoreaderApp/settings.json`:

| Setting | Default | Description |
|---------|---------|-------------|
| `engine` | `kokoro` | Active TTS engine: `kokoro`, `edge-tts`, `openai`, `elevenlabs` |
| `voice` | `af_bella` | Voice ID (per-engine) |
| `speed` | `1.0` | Playback rate multiplier |
| `pitch` | `0` | Pitch offset (Hz, for supported engines) |
| `volume` | `1.0` | Volume multiplier |
| `hotkey_read` | `ctrl+shift+r` | Trigger hotkey |
| `hotkey_stop` | `ctrl+shift+x` | Stop hotkey |
| `openai_api_key` | `""` | Encrypted OpenAI key |
| `elevenlabs_api_key` | `""` | Encrypted ElevenLabs key |

## System Integration

### Context Menu Registration
- Registry key: `HKCU\Software\Classes\*\shell\AutoreaderApp`
- Clean removal on uninstall or via settings panel

### Auto-Start
- Registry entry: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- Points to the app executable
- Enabled by default; toggleable from settings

### Packaging
- PyInstaller bundles into single-folder distribution with main `.exe`
- Kokoro ONNX model weights bundled or downloaded on first run
- Optional Inno Setup/NSIS installer for polished install/uninstall
- Development: `python main.py`

## Project Structure

```
autoreader-app/
├── src/
│   ├── main.py                  # Entry point, single-instance check, app init
│   ├── tray.py                  # System tray icon and menu
│   ├── widget.py                # Floating playback widget
│   ├── tts_engine.py            # Abstract TTSEngine base class
│   ├── engines/
│   │   ├── kokoro_engine.py     # Kokoro local engine
│   │   ├── edge_tts_engine.py   # edge-tts engine
│   │   ├── openai_engine.py     # OpenAI TTS engine
│   │   └── elevenlabs_engine.py # ElevenLabs engine
│   ├── text_capture.py          # Hotkey listener + clipboard handling
│   ├── socket_server.py         # Local socket for context menu communication
│   ├── registry.py              # Context menu + auto-start registry management
│   ├── settings.py              # Settings load/save/defaults
│   └── settings_dialog.py       # PyQt6 settings UI
├── scripts/
│   └── autoreader_send.py       # CLI companion for context menu trigger
├── assets/
│   └── icon.png                 # Tray/widget icon
├── requirements.txt
├── setup.py
└── README.md
```

## Error Handling

- **No text selected:** Tray notification "No text selected", no action
- **Already reading:** Stop current playback, start new text immediately
- **No internet (cloud engine selected):** Tray notification with option to switch to Kokoro
- **Invalid/missing API key:** Settings dialog highlights the key field with an error; tray notification on read attempt
- **Kokoro model not downloaded:** Prompt to download on first use; fall back to edge-tts in the meantime
- **App already running:** Second instance notifies existing instance and exits
- **Long text:** Auto-chunked at sentence boundaries; stop button always available
- **Registry cleanup:** Quit or uninstall removes all registry entries

## Engine Cost Reference (for settings UI tooltip)

| Engine | Cost | Notes |
|--------|------|-------|
| Kokoro | Free | Local, offline, ~90% of ElevenLabs quality |
| edge-tts | Free | Requires internet, Microsoft neural voices |
| OpenAI tts-1-hd | $30/1M chars | Best value cloud, 6 voices |
| ElevenLabs Flash | ~$165/1M chars | Most expressive, voice cloning available |
