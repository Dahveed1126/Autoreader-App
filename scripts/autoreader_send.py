#!/usr/bin/env python3
"""
CLI companion script for the Windows Shell context menu.
Reads selected text from clipboard and sends it to the running Autoreader app.
Usage: autoreader_send.py
"""
import sys
import os

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
