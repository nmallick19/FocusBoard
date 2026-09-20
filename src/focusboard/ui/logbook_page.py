from __future__ import annotations

from datetime import date, timedelta

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
from focusboard.models import CATEGORY_LABELS, DELAY_REASON_LABELS, DIFFICULTY_LABELS, STATUS_LABELS, Status
from focusboard.ui.chrome import GhostButton
from focusboard.util import format_duration, format_estimated


class LogbookPage(QWidget):
    def __init__(self, db: Database, hub: Hub, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.hub = hub
        self.week_start = self._monday(date.today())

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 24)
        root.setSpacing(16)

        nav = QHBoxLayout()
        nav.setSpacing(8)
        self.prev_btn = GhostButton("Previous week")
        self.next_btn = GhostButton("Next week")
        self.this_btn = GhostButton("This week")
        self.week_label = QLabel()
        self.week_label.setObjectName("SectionTitle")
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.this_btn)
        nav.addWidget(self.next_btn)
        nav.addSpacing(16)
        nav.addWidget(self.week_label)
        nav.addStretch()
        root.addLayout(nav)

        self.summary = QLabel()
        self.summary.setObjectName("LogSummary")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

        self.table = QTableWidget(0, 9)
        self.table.setObjectName("LogTable")
        self.table.setHorizontalHeaderLabels(
            [
                "Title",
                "Status",
                "Finished",
                "Duration",
                "Estimated",
                "Difficulty",
                "Delay reason",
                "Note",
                "Category",
            ]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        header = self.table.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(44)
        root.addWidget(self.table, 1)

        self.prev_btn.clicked.connect(self._prev)
        self.next_btn.clicked.connect(self._next)
        self.this_btn.clicked.connect(self._this_week)
        self.refresh()

    def _monday(self, day: date) -> date:
        return day - timedelta(days=day.weekday())

    def _prev(self) -> None:
        self.week_start -= timedelta(days=7)
        self.refresh()

    def _next(self) -> None:
        self.week_start += timedelta(days=7)
        self.refresh()

    def _this_week(self) -> None:
        self.week_start = self._monday(date.today())
        self.refresh()

    def refresh(self) -> None:
        week_end = self.week_start + timedelta(days=6)
        self.week_label.setText(
            f"{self.week_start.strftime('%-d %b %Y')} – {week_end.strftime('%-d %b %Y')}"
        )
        stats = self.db.week_stats(self.week_start)
        self.summary.setText(
            f"Completed {stats.completed}   ·   Missed {stats.missed}   ·   "
            f"Time spent {format_duration(stats.seconds)}   ·   "
            f"Estimated {format_estimated(stats.estimated_minutes)}"
        )
        rows = self.db.logbook(self.week_start)
        self.table.clearSpans()
        self.table.setRowCount(len(rows))
        for index, task in enumerate(rows):
            reason = DELAY_REASON_LABELS.get(task.delay_reason, task.delay_reason or "—")
            finished = task.finished_at.strftime("%a %-d %b %H:%M") if task.finished_at else "—"
            values = [
                task.title,
                STATUS_LABELS.get(task.status, task.status),
                finished,
                format_duration(task.duration_seconds) if task.status == Status.DONE else "—",
                format_estimated(task.estimated_minutes),
                DIFFICULTY_LABELS.get(task.difficulty, task.difficulty),
                reason if task.delay_reason else "—",
                task.delay_note or "",
                CATEGORY_LABELS.get(task.category, task.category.capitalize()),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col != 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(index, col, item)
        if not rows:
            self.table.setRowCount(1)
            empty = QTableWidgetItem("No completed or missed tasks this week")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.table.setItem(0, 0, empty)
            self.table.setSpan(0, 0, 1, 9)
