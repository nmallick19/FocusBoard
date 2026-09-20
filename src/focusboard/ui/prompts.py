from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout

from focusboard.ui.chrome import GhostButton, PrimaryButton


class PromptDialog(QDialog):
    def __init__(self, title: str, body: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setObjectName("PromptDialog")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(460, 200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(16)
        heading = QLabel(body)
        heading.setWordWrap(True)
        heading.setObjectName("SectionTitle")
        layout.addWidget(heading)
        layout.addStretch()
        self.buttons = QHBoxLayout()
        self.buttons.setSpacing(8)
        self.buttons.addStretch()
        layout.addLayout(self.buttons)

    def _add_buttons(self, *buttons) -> None:
        for button in buttons:
            self.buttons.addWidget(button)


class CheckInDialog(PromptDialog):
    def __init__(self, task_title: str, parent=None) -> None:
        super().__init__(
            "Still working?",
            f'Are you still working on “{task_title}”?',
            parent,
        )
        self.acknowledge_btn = PrimaryButton("Acknowledge")
        self.pause_btn = GhostButton("Pause")
        self.acknowledge_btn.clicked.connect(self.accept)
        self.pause_btn.clicked.connect(self.reject)
        self._add_buttons(self.pause_btn, self.acknowledge_btn)
        self.acknowledge_btn.setDefault(True)


class SessionPauseDialog(PromptDialog):
    def __init__(self, task_title: str, explanation: str, parent=None) -> None:
        super().__init__(
            "Task paused",
            f"“{task_title}” was paused because {explanation}. Would you like to resume it?",
            parent,
        )
        self.resume_btn = PrimaryButton("Resume")
        self.close_btn = GhostButton("Close")
        self.resume_btn.clicked.connect(self.accept)
        self.close_btn.clicked.connect(self.reject)
        self._add_buttons(self.close_btn, self.resume_btn)
        self.resume_btn.setDefault(True)
