import sys
import os
import ctypes
import threading

MUTEX_NAME = "AutoreaderAppMutex_v1"

def _check_single_instance() -> bool:
    """Returns True if this is the first instance, False if another is running."""
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = ctypes.windll.kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    return last_error != ERROR_ALREADY_EXISTS


def main():
    if not _check_single_instance():
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
