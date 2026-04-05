from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QSlider, QPushButton, QLineEdit,
    QCheckBox, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from src.tts_engine import get_engine
from src.settings import encrypt_key, decrypt_key

ENGINE_LABELS = {
    "kokoro": "Kokoro (Local, Free — best quality offline)",
    "edge-tts": "edge-tts (Free, requires internet)",
    "openai": "OpenAI TTS (API key required — $30/1M chars)",
    "elevenlabs": "ElevenLabs (API key required — best expressiveness)",
}


class SettingsDialog(QDialog):
    settings_saved = pyqtSignal(dict)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = dict(settings)
        self.setWindowTitle("Autoreader Settings")
        self.setMinimumWidth(480)
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._tabs.addTab(self._build_voice_tab(), "Voice")
        self._tabs.addTab(self._build_keys_tab(), "API Keys")
        self._tabs.addTab(self._build_hotkeys_tab(), "Hotkeys")
        self._tabs.addTab(self._build_system_tab(), "System")

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self._on_save)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _build_voice_tab(self):
        w = QWidget()
        form = QFormLayout(w)

        self._engine_combo = QComboBox()
        for key, label in ENGINE_LABELS.items():
            self._engine_combo.addItem(label, key)
        self._engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        form.addRow("Engine:", self._engine_combo)

        self._voice_combo = QComboBox()
        form.addRow("Voice:", self._voice_combo)

        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(50, 300)
        self._speed_label = QLabel("1.0x")
        self._speed_slider.valueChanged.connect(
            lambda v: self._speed_label.setText(f"{v/100:.1f}x")
        )
        speed_row = QHBoxLayout()
        speed_row.addWidget(self._speed_slider)
        speed_row.addWidget(self._speed_label)
        speed_widget = QWidget()
        speed_widget.setLayout(speed_row)
        form.addRow("Speed:", speed_widget)

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_label = QLabel("100%")
        self._volume_slider.valueChanged.connect(
            lambda v: self._volume_label.setText(f"{v}%")
        )
        vol_row = QHBoxLayout()
        vol_row.addWidget(self._volume_slider)
        vol_row.addWidget(self._volume_label)
        vol_widget = QWidget()
        vol_widget.setLayout(vol_row)
        form.addRow("Volume:", vol_widget)

        test_btn = QPushButton("Test Voice")
        test_btn.clicked.connect(self._on_test)
        form.addRow("", test_btn)
        return w

    def _build_keys_tab(self):
        w = QWidget()
        form = QFormLayout(w)

        self._openai_key_edit = QLineEdit()
        self._openai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._openai_key_edit.setPlaceholderText("sk-...")
        openai_verify = QPushButton("Verify")
        openai_verify.clicked.connect(lambda: self._verify_key("openai"))
        openai_row = QHBoxLayout()
        openai_row.addWidget(self._openai_key_edit)
        openai_row.addWidget(openai_verify)
        openai_widget = QWidget()
        openai_widget.setLayout(openai_row)
        form.addRow("OpenAI API Key:", openai_widget)

        self._elevenlabs_key_edit = QLineEdit()
        self._elevenlabs_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._elevenlabs_key_edit.setPlaceholderText("Your ElevenLabs API key")
        el_verify = QPushButton("Verify")
        el_verify.clicked.connect(lambda: self._verify_key("elevenlabs"))
        el_row = QHBoxLayout()
        el_row.addWidget(self._elevenlabs_key_edit)
        el_row.addWidget(el_verify)
        el_widget = QWidget()
        el_widget.setLayout(el_row)
        form.addRow("ElevenLabs API Key:", el_widget)

        cost_note = QLabel(
            "Kokoro & edge-tts are free.\n"
            "OpenAI tts-1-hd: $30/1M chars.\n"
            "ElevenLabs Flash: ~$165/1M chars."
        )
        cost_note.setStyleSheet("color: gray; font-size: 11px;")
        form.addRow("", cost_note)
        return w

    def _build_hotkeys_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        self._read_hotkey_edit = QLineEdit()
        self._read_hotkey_edit.setPlaceholderText("e.g. ctrl+shift+r")
        form.addRow("Read Hotkey:", self._read_hotkey_edit)
        self._stop_hotkey_edit = QLineEdit()
        self._stop_hotkey_edit.setPlaceholderText("e.g. ctrl+shift+x")
        form.addRow("Stop Hotkey:", self._stop_hotkey_edit)
        return w

    def _build_system_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self._autostart_check = QCheckBox("Start Autoreader when Windows starts")
        layout.addWidget(self._autostart_check)
        from src.registry import is_context_menu_installed
        self._context_menu_btn = QPushButton(
            "Remove Context Menu Entry" if is_context_menu_installed()
            else "Install Context Menu Entry"
        )
        self._context_menu_btn.clicked.connect(self._toggle_context_menu)
        layout.addWidget(self._context_menu_btn)
        layout.addStretch()
        return w

    def _populate(self):
        s = self._settings
        engine = s.get("engine", "kokoro")
        idx = list(ENGINE_LABELS.keys()).index(engine) if engine in ENGINE_LABELS else 0
        self._engine_combo.setCurrentIndex(idx)
        self._refresh_voices()
        self._speed_slider.setValue(int(float(s.get("speed", 1.0)) * 100))
        self._volume_slider.setValue(int(float(s.get("volume", 1.0)) * 100))
        self._openai_key_edit.setText(decrypt_key(s.get("openai_api_key", "")))
        self._elevenlabs_key_edit.setText(decrypt_key(s.get("elevenlabs_api_key", "")))
        self._read_hotkey_edit.setText(s.get("hotkey_read", "ctrl+shift+r"))
        self._stop_hotkey_edit.setText(s.get("hotkey_stop", "ctrl+shift+x"))
        from src.registry import is_autostart_installed
        self._autostart_check.setChecked(is_autostart_installed())

    def _on_engine_changed(self, _):
        self._refresh_voices()

    def _refresh_voices(self):
        self._voice_combo.clear()
        engine_key = self._engine_combo.currentData()
        try:
            engine = get_engine(engine_key, self._settings)
            for voice in engine.list_voices():
                self._voice_combo.addItem(voice.name, voice.id)
            current = self._settings.get("voice", "")
            for i in range(self._voice_combo.count()):
                if self._voice_combo.itemData(i) == current:
                    self._voice_combo.setCurrentIndex(i)
                    break
        except Exception:
            pass

    def _verify_key(self, provider: str):
        if provider == "openai":
            key = self._openai_key_edit.text().strip()
            if not key:
                QMessageBox.warning(self, "No Key", "Enter an OpenAI API key first.")
                return
            try:
                from openai import OpenAI
                client = OpenAI(api_key=key)
                client.models.list()
                QMessageBox.information(self, "Valid", "OpenAI API key is valid.")
            except Exception as e:
                QMessageBox.critical(self, "Invalid", f"Key verification failed:\n{e}")
        elif provider == "elevenlabs":
            key = self._elevenlabs_key_edit.text().strip()
            if not key:
                QMessageBox.warning(self, "No Key", "Enter an ElevenLabs API key first.")
                return
            try:
                from elevenlabs.client import ElevenLabs
                client = ElevenLabs(api_key=key)
                client.voices.get_all(show_legacy=False)
                QMessageBox.information(self, "Valid", "ElevenLabs API key is valid.")
            except Exception as e:
                QMessageBox.critical(self, "Invalid", f"Key verification failed:\n{e}")

    def _on_test(self):
        engine_key = self._engine_combo.currentData()
        voice_id = self._voice_combo.currentData()
        test_settings = dict(self._settings)
        test_settings["voice"] = voice_id
        test_settings["speed"] = self._speed_slider.value() / 100
        test_settings["volume"] = self._volume_slider.value() / 100
        try:
            from src.audio_player import AudioPlayer
            engine = get_engine(engine_key, test_settings)
            player = AudioPlayer()
            gen = engine.synthesize("This is a test of the selected voice.", test_settings)
            player.play(gen)
        except Exception as e:
            QMessageBox.critical(self, "Test Failed", str(e))

    def _toggle_context_menu(self):
        import sys
        from src.registry import (
            install_context_menu, uninstall_context_menu, is_context_menu_installed
        )
        exe = sys.executable
        if is_context_menu_installed():
            uninstall_context_menu()
            self._context_menu_btn.setText("Install Context Menu Entry")
        else:
            install_context_menu(exe)
            self._context_menu_btn.setText("Remove Context Menu Entry")

    def _on_save(self):
        s = self._settings
        s["engine"] = self._engine_combo.currentData()
        s["voice"] = self._voice_combo.currentData() or s.get("voice", "af_bella")
        s["speed"] = self._speed_slider.value() / 100
        s["volume"] = self._volume_slider.value() / 100
        s["hotkey_read"] = self._read_hotkey_edit.text().strip() or "ctrl+shift+r"
        s["hotkey_stop"] = self._stop_hotkey_edit.text().strip() or "ctrl+shift+x"
        oai = self._openai_key_edit.text().strip()
        el = self._elevenlabs_key_edit.text().strip()
        s["openai_api_key"] = encrypt_key(oai) if oai else ""
        s["elevenlabs_api_key"] = encrypt_key(el) if el else ""
        from src.registry import install_autostart, uninstall_autostart
        import sys
        if self._autostart_check.isChecked():
            install_autostart(sys.executable)
        else:
            uninstall_autostart()
        from src.settings import save_settings
        save_settings(s)
        self.settings_saved.emit(s)
        self.accept()
