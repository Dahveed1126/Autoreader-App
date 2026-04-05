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
    previous = _get_clipboard()
    _set_clipboard("")
    time.sleep(0.05)
    keyboard.send("ctrl+c")
    time.sleep(0.15)
    selected = _get_clipboard()
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
        # Store handler objects returned by add_hotkey for reliable removal
        self._read_handler = None
        self._stop_handler = None

    def start(self):
        self._read_handler = keyboard.add_hotkey(
            self._read_hotkey, self._handle_read, suppress=True
        )
        self._stop_handler = keyboard.add_hotkey(
            self._stop_hotkey, self._on_stop, suppress=True
        )
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
                keyboard.remove_hotkey(self._read_handler)
            except (KeyError, Exception):
                pass
            try:
                keyboard.remove_hotkey(self._stop_handler)
            except (KeyError, Exception):
                pass
            self._read_handler = None
            self._stop_handler = None
            self._registered = False
