from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from focusboard.db import Database
from focusboard.hub import Hub
from focusboard.ui.chrome import GhostButton


class LoggerPage(QWidget):
    def __init__(self, db: Database, hub: Hub, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.hub = hub

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 24)
        root.setSpacing(16)

        heading = QHBoxLayout()
        self.title = QLabel("Activity")
        self.title.setObjectName("SectionTitle")
        heading.addWidget(self.title)
        heading.addStretch()
        self.refresh_btn = GhostButton("Refresh")
        heading.addWidget(self.refresh_btn)
        root.addLayout(heading)

        self.summary = QLabel()
        self.summary.setObjectName("LogSummary")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        self.table = QTableWidget(0, 4)
        self.table.setObjectName("LogTable")
        self.table.setHorizontalHeaderLabels(["When", "Source", "Action", "Detail"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        header = self.table.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(40)
        root.addWidget(self.table, 1)

        self.refresh_btn.clicked.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        rows = self.db.list_activity()
        self.summary.setText(
            f"{len(rows)} events in the last 7 days. Older entries are dropped automatically."
        )
        self.table.clearSpans()
        self.table.setRowCount(len(rows))
        for index, event in enumerate(rows):
            values = [
                event.created_at.strftime("%a %-d %b %H:%M:%S"),
                "You" if event.source == "user" else "App",
                event.action,
                event.detail,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(index, col, item)
        if not rows:
            self.table.setRowCount(1)
            empty = QTableWidgetItem("Nothing logged yet.")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.table.setItem(0, 0, empty)
            self.table.setSpan(0, 0, 1, 4)
