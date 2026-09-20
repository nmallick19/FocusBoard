from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from focusboard.models import DELAY_REASON_LABELS, DelayReason


class DelayDialog(QDialog):
    def __init__(self, parent=None, heading: str = "Why is this delayed?") -> None:
        super().__init__(parent)
        self.setWindowTitle("Delay reason")
        self.setModal(True)
        self.setObjectName("DelayDialog")
        self.resize(460, 220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(16)
        heading_label = QLabel(heading)
        heading_label.setWordWrap(True)
        heading_label.setObjectName("SectionTitle")
        layout.addWidget(heading_label)

        form = QFormLayout()
        self.reason = QComboBox()
        for value, label in DELAY_REASON_LABELS.items():
            self.reason.addItem(label, value.value)
        self.note = QLineEdit()
        self.note.setPlaceholderText("Optional note — required if you pick Other")
        form.addRow("Reason", self.reason)
        form.addRow("Note", self.note)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.reason.currentIndexChanged.connect(self._on_reason_changed)

    def _on_reason_changed(self) -> None:
        other = self.reason.currentData() == DelayReason.OTHER.value
        self.note.setPlaceholderText(
            "Describe what happened" if other else "Optional note — required if you pick Other"
        )

    def _accept(self) -> None:
        reason = self.reason.currentData()
        note = self.note.text().strip()
        if reason == DelayReason.OTHER.value and not note:
            self.note.setFocus()
            self.note.setPlaceholderText("Please add a short note")
            return
        self.accept()

    def values(self) -> tuple[str, str]:
        return self.reason.currentData(), self.note.text().strip()
