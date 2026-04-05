# Autoreader App — Design Spec

## Overview

A Windows desktop application that lets users highlight text in any application, right-click (or use a global hotkey), and have the selected text read aloud using high-quality Microsoft neural voices via edge-tts.

## Tech Stack

- **Language:** Python 3.11+
- **UI Framework:** PyQt6 (system tray, floating widget, settings dialog)
- **TTS Engine:** edge-tts (free Microsoft neural voices, streaming)
- **Audio Playback:** pygame.mixer or sounddevice
- **Hotkeys:** keyboard or pynput
- **Packaging:** PyInstaller (single-folder distribution)
- **Installer (optional):** Inno Setup or NSIS

## Architecture

Four main components:

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

### 3. TTS Engine (`tts_engine.py`)

- Uses edge-tts to convert text to speech
- Streams audio chunks for immediate playback (no waiting for full synthesis)
- Configurable voice, speed, pitch, and volume

### 4. Floating Widget (`widget.py`)

- Small always-on-top PyQt6 window
- Play/pause/stop buttons with a progress indicator
- Appears when reading starts, can be dragged around
- Auto-hides when idle

## Data Flow

### Startup
1. App launches → checks single-instance lock (named mutex)
2. Loads settings from `%APPDATA%/AutoreaderApp/settings.json`
3. Registers global hotkey listener
4. Creates system tray icon
5. Starts local socket server for context menu communication

### Reading
1. User highlights text → triggers via context menu or hotkey
2. Context menu path: shell launches CLI script → sends text over local socket → main process
3. Hotkey path: simulates Ctrl+C → reads clipboard → restores previous clipboard
4. Text passed to edge-tts with configured voice/speed/pitch
5. edge-tts streams audio → playback starts immediately
6. Floating widget appears with controls
7. User can pause/resume/stop via widget, tray, or hotkey

## Settings

Stored in `%APPDATA%/AutoreaderApp/settings.json`:

| Setting | Default | Description |
|---------|---------|-------------|
| `voice` | `en-US-AriaNeural` | edge-tts voice name |
| `speed` | `+0%` | Playback rate modifier |
| `pitch` | `+0Hz` | Pitch modifier |
| `volume` | `+0%` | Volume level |
| `hotkey_read` | `ctrl+shift+r` | Trigger hotkey |
| `hotkey_stop` | `ctrl+shift+x` | Stop hotkey |

Settings panel accessible from tray icon → "Settings". PyQt6 dialog with voice dropdown, sliders for speed/pitch/volume, hotkey config, and a "Test" button.

## System Integration

### Context Menu Registration
- Registry key: `HKCU\Software\Classes\*\shell\AutoreaderApp`
- Clean removal on uninstall or via tray menu option

### Auto-Start
- Registry entry: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- Points to the app executable
- Toggleable from settings

### Packaging
- PyInstaller bundles into single-folder distribution with main `.exe`
- Optional Inno Setup/NSIS installer for polished install/uninstall
- Development: `python main.py`

## Project Structure

```
autoreader-app/
├── src/
│   ├── main.py              # Entry point, single-instance check, app init
│   ├── tray.py              # System tray icon and menu
│   ├── widget.py            # Floating playback widget
│   ├── tts_engine.py        # edge-tts wrapper, streaming audio
│   ├── text_capture.py      # Hotkey listener + clipboard handling
│   ├── socket_server.py     # Local socket for context menu communication
│   ├── registry.py          # Context menu + auto-start registry management
│   ├── settings.py          # Settings load/save/defaults
│   └── settings_dialog.py   # PyQt6 settings UI
├── scripts/
│   └── autoreader_send.py   # CLI companion for context menu trigger
├── assets/
│   └── icon.png             # Tray/widget icon
├── requirements.txt
├── setup.py
└── README.md
```

## Error Handling

- **No text selected:** Tray notification "No text selected", no action
- **Already reading:** Stop current playback, start new text
- **No internet:** Tray notification "No internet connection — cannot read aloud"
- **App already running:** Second instance notifies existing instance and exits
- **Long text:** Handled naturally via edge-tts streaming; stop button always available
- **Registry cleanup:** Quit or uninstall removes all registry entries
