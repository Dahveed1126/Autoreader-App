import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal
from src.audio_player import PlayerState


class TrayIcon(QObject):
    read_requested = pyqtSignal(str)

    def __init__(self, icon_path: str, app: QApplication):
        super().__init__()
        self._app = app
        self._icon = QSystemTrayIcon(QIcon(icon_path), app)
        self._icon.setToolTip("Autoreader — idle")
        self._menu = QMenu()
        self._build_menu()
        self._icon.setContextMenu(self._menu)
        self._icon.show()

        self._pause_action: QAction | None = None
        self._resume_action: QAction | None = None
        self._stop_action: QAction | None = None

    def _build_menu(self):
        self._pause_action = self._menu.addAction("Pause")
        self._pause_action.setEnabled(False)
        self._resume_action = self._menu.addAction("Resume")
        self._resume_action.setEnabled(False)
        self._stop_action = self._menu.addAction("Stop")
        self._stop_action.setEnabled(False)
        self._menu.addSeparator()
        settings_action = self._menu.addAction("Settings…")
        settings_action.triggered.connect(self._open_settings)
        self._menu.addSeparator()
        quit_action = self._menu.addAction("Quit")
        quit_action.triggered.connect(self._quit)

    def set_player_callbacks(self, on_pause, on_resume, on_stop):
        self._pause_action.triggered.connect(on_pause)
        self._resume_action.triggered.connect(on_resume)
        self._stop_action.triggered.connect(on_stop)

    def set_settings_callback(self, on_settings):
        self._settings_callback = on_settings

    def _open_settings(self):
        if hasattr(self, "_settings_callback"):
            self._settings_callback()

    def update_state(self, state: PlayerState):
        if state == PlayerState.PLAYING:
            self._icon.setToolTip("Autoreader — reading…")
            self._pause_action.setEnabled(True)
            self._resume_action.setEnabled(False)
            self._stop_action.setEnabled(True)
        elif state == PlayerState.PAUSED:
            self._icon.setToolTip("Autoreader — paused")
            self._pause_action.setEnabled(False)
            self._resume_action.setEnabled(True)
            self._stop_action.setEnabled(True)
        elif state == PlayerState.IDLE:
            self._icon.setToolTip("Autoreader — idle")
            self._pause_action.setEnabled(False)
            self._resume_action.setEnabled(False)
            self._stop_action.setEnabled(False)

    def show_message(self, title: str, message: str):
        self._icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)

    def _quit(self):
        self._app.quit()
