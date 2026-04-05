from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QIcon
from src.audio_player import PlayerState


class FloatingWidget(QWidget):
    pause_clicked = pyqtSignal()
    resume_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()

    def __init__(self, icon_path: str):
        super().__init__()
        self._drag_pos = QPoint()
        self._setup_ui(icon_path)

    def _setup_ui(self, icon_path: str):
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(180, 48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._status_label = QLabel("▶ Reading…")
        self._status_label.setStyleSheet("color: white; font-size: 11px;")

        self._pause_btn = QPushButton("⏸")
        self._play_btn = QPushButton("▶")
        self._stop_btn = QPushButton("⏹")

        for btn in (self._pause_btn, self._play_btn, self._stop_btn):
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.2); border-radius: 14px;"
                " color: white; font-size: 14px; border: none; }"
                "QPushButton:hover { background: rgba(255,255,255,0.4); }"
            )

        self._play_btn.hide()
        self._pause_btn.clicked.connect(self.pause_clicked)
        self._play_btn.clicked.connect(self.resume_clicked)
        self._stop_btn.clicked.connect(self.stop_clicked)

        layout.addWidget(self._status_label)
        layout.addWidget(self._pause_btn)
        layout.addWidget(self._play_btn)
        layout.addWidget(self._stop_btn)

        self.setStyleSheet(
            "FloatingWidget { background: rgba(30,30,30,0.85); border-radius: 24px; }"
        )

    def update_state(self, state: PlayerState):
        if state == PlayerState.PLAYING:
            self._status_label.setText("▶ Reading…")
            self._pause_btn.show()
            self._play_btn.hide()
            self.show()
        elif state == PlayerState.PAUSED:
            self._status_label.setText("⏸ Paused")
            self._pause_btn.hide()
            self._play_btn.show()
        elif state == PlayerState.IDLE:
            self.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
