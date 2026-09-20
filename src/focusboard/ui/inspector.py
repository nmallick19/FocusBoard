from __future__ import annotations

import html
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from focusboard.models import (
    CATEGORY_LABELS,
    DELAY_REASON_LABELS,
    DIFFICULTY_LABELS,
    PAUSE_REASON_LABELS,
    PRIORITY_LABELS,
    STATUS_LABELS,
    Status,
    Task,
)
from focusboard.ui.chrome import DangerButton, GhostButton, IconButton, PrimaryButton
from focusboard.ui.task_list import DueStamp, TimeBar
from focusboard.util import format_due, format_duration, format_estimated, format_time_progress


class _Field(QWidget):
    def __init__(self, label: str, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(2)
        caption = QLabel(label)
        caption.setObjectName("InspectorCaption")
        self.caption = caption
        self.value = QLabel("—")
        self.value.setObjectName("InspectorValue")
        self.value.setWordWrap(True)
        layout.addWidget(caption)
        layout.addWidget(self.value)

    def set_text(self, text: str) -> None:
        self.value.setText(text or "—")


class TaskInspector(QFrame):
    start = Signal()
    unstart = Signal()
    pause = Signal()
    resume = Signal()
    reopen = Signal()
    finish = Signal()
    missed = Signal()
    edit = Signal()
    delete = Signal()
    close_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Inspector")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(280)
        self.setMaximumWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 12, 16)
        root.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 0, 8)
        header.addStretch()
        self.close_btn = IconButton("×")
        self.close_btn.setToolTip("Close details")
        self.close_btn.setAccessibleName("Close details")
        self.close_btn.clicked.connect(self.close_requested.emit)
        header.addWidget(self.close_btn)
        root.addLayout(header)

        self.empty = QLabel("Select a task to see details and actions.")
        self.empty.setObjectName("EmptyHint")
        self.empty.setWordWrap(True)
        root.addWidget(self.empty)

        self.body = QWidget()
        body = QVBoxLayout(self.body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.title = QLabel()
        self.title.setObjectName("InspectorTitle")
        self.title.setWordWrap(True)
        font = QFont()
        font.setPointSize(18)
        font.setWeight(QFont.Weight.DemiBold)
        self.title.setFont(font)
        body.addWidget(self.title)

        self.notes = QLabel()
        self.notes.setObjectName("InspectorNotes")
        self.notes.setWordWrap(True)
        body.addWidget(self.notes)

        self.due = QWidget()
        due_col = QVBoxLayout(self.due)
        due_col.setContentsMargins(0, 0, 0, 10)
        due_col.setSpacing(4)
        self.due_caption = QLabel("Due")
        self.due_caption.setObjectName("InspectorCaption")
        self.due_stamp = DueStamp(align_right=False)
        self.due_stamp.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        due_col.addWidget(self.due_caption)
        due_col.addWidget(self.due_stamp, 0, Qt.AlignmentFlag.AlignLeft)
        self.repeats = _Field("Repeats")
        self.until = _Field("Until")
        self.place = _Field("Where")
        self.priority = _Field("Priority")
        self.difficulty = _Field("Difficulty")
        self.status = _Field("Status")
        self.project = _Field("Project")
        self.estimate = _Field("Expected time")
        self.progress = _Field("Progress")
        self.timing = _Field("Time")
        self.delay = _Field("Delay")
        for field in (
            self.due,
            self.repeats,
            self.until,
            self.place,
            self.priority,
            self.difficulty,
            self.status,
            self.project,
            self.estimate,
            self.progress,
        ):
            body.addWidget(field)
        self.time_bar = TimeBar()
        body.addWidget(self.time_bar)
        body.addWidget(self.timing)
        body.addWidget(self.delay)

        body.addSpacing(12)
        self.start_btn = PrimaryButton("Start")
        self.start_btn.setToolTip("Start (S)")
        self.finish_btn = GhostButton("Finish")
        self.finish_btn.setToolTip("Finish (F)")
        self.finish_primary = PrimaryButton("Finish")
        self.finish_primary.setToolTip("Finish (F)")
        self.pause_btn = GhostButton("Pause")
        self.pause_btn.setToolTip("Pause the clock (P)")
        self.resume_btn = PrimaryButton("Resume")
        self.resume_btn.setToolTip("Resume the clock (P)")
        self.reopen_btn = PrimaryButton("Reopen")
        self.reopen_btn.setToolTip("Reopen (R)")
        self.unstart_btn = GhostButton("Undo Start")
        self.unstart_btn.setToolTip("Undo Start (U)")
        self.miss_btn = GhostButton("Missed")
        self.miss_btn.setToolTip("Missed (M)")
        self.edit_btn = GhostButton("Edit")
        self.edit_btn.setToolTip("Edit (Enter or Ctrl+E)")
        self.delete_btn = DangerButton("Delete")
        self.delete_btn.setToolTip("Delete (Del)")
        for btn in (
            self.start_btn,
            self.pause_btn,
            self.resume_btn,
            self.finish_primary,
            self.finish_btn,
            self.reopen_btn,
            self.unstart_btn,
            self.miss_btn,
            self.edit_btn,
            self.delete_btn,
        ):
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            body.addWidget(btn)
            body.addSpacing(4)

        body.addStretch()
        root.addWidget(self.body, 1)

        self.start_btn.clicked.connect(self.start.emit)
        self.pause_btn.clicked.connect(self.pause.emit)
        self.resume_btn.clicked.connect(self.resume.emit)
        self.finish_primary.clicked.connect(self.finish.emit)
        self.unstart_btn.clicked.connect(self.unstart.emit)
        self.reopen_btn.clicked.connect(self.reopen.emit)
        self.finish_btn.clicked.connect(self.finish.emit)
        self.miss_btn.clicked.connect(self.missed.emit)
        self.edit_btn.clicked.connect(self.edit.emit)
        self.delete_btn.clicked.connect(self.delete.emit)
        self._task: Task | None = None
        self._clock = QTimer(self)
        self._clock.setInterval(1000)
        self._clock.timeout.connect(self._tick)
        self.set_task(None)

    def set_task(self, task: Task | None) -> None:
        self._task = task
        if task is None:
            self._clock.stop()
            self.time_bar.set_progress(None)
            self.empty.setVisible(True)
            self.body.setVisible(False)
            self.setVisible(False)
            return
        self.setVisible(True)
        self.empty.setVisible(False)
        self.body.setVisible(True)
        self.title.setText(task.title)
        if task.notes:
            self.notes.setText(task.notes)
            self.notes.setVisible(True)
        else:
            self.notes.setVisible(False)
        meeting = task.is_meeting()
        self.due_caption.setText("Next" if meeting else "Due")
        overdue = task.is_incomplete() and task.when() < datetime.now()
        self.due_stamp.set_due(task.when(), overdue=overdue, show_remain=task.is_incomplete())
        self.repeats.set_text(task.repeat_label())
        self.repeats.setVisible(bool(task.is_recurring() or meeting))
        if task.is_recurring() and task.repeat_until:
            self.until.set_text(task.repeat_until.strftime("%-d %b %Y"))
            self.until.setVisible(True)
        else:
            self.until.setVisible(False)
        if meeting:
            url = task.meeting_url.strip()
            if url:
                safe = html.escape(url, quote=True)
                self.place.value.setText(f'<a href="{safe}">{html.escape(url)}</a>')
                self.place.value.setOpenExternalLinks(True)
                self.place.value.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
                self.place.setVisible(True)
            elif task.location.strip():
                self.place.value.setOpenExternalLinks(False)
                self.place.value.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
                self.place.set_text(task.location.strip())
                self.place.setVisible(True)
            else:
                self.place.setVisible(False)
            self.priority.setVisible(False)
            self.difficulty.setVisible(False)
            self.status.setVisible(False)
            self.project.setVisible(False)
            self.estimate.setVisible(False)
            self.progress.setVisible(False)
            self.time_bar.set_progress(None)
            self.timing.setVisible(False)
            self.delay.setVisible(False)
            self.start_btn.setVisible(False)
            self.pause_btn.setVisible(False)
            self.resume_btn.setVisible(False)
            self.finish_primary.setVisible(False)
            self.finish_btn.setVisible(False)
            self.unstart_btn.setVisible(False)
            self.miss_btn.setVisible(False)
            self.reopen_btn.setVisible(False)
            self._clock.stop()
            return
        self.place.setVisible(False)
        self.place.value.setOpenExternalLinks(False)
        self.priority.setVisible(True)
        self.difficulty.setVisible(True)
        self.status.setVisible(True)
        self.project.setVisible(True)
        self.priority.set_text(PRIORITY_LABELS.get(task.priority, task.priority))
        self.difficulty.set_text(DIFFICULTY_LABELS.get(task.difficulty, task.difficulty))
        if task.is_paused():
            extra = PAUSE_REASON_LABELS.get(task.pause_reason or "", "")
            if extra and extra != "Paused":
                self.status.set_text(f"Paused because {extra}")
            else:
                self.status.set_text("Paused")
        else:
            self.status.set_text(STATUS_LABELS.get(task.status, task.status))
        self.project.set_text(CATEGORY_LABELS.get(task.category, task.category))
        self.estimate.set_text(format_estimated(task.estimated_minutes))
        self.estimate.setVisible(True)
        self._tick()
        timing = []
        if task.started_at:
            timing.append(f"Started {format_due(task.started_at)}")
        if task.finished_at:
            timing.append(f"Closed {format_due(task.finished_at)}")
        if task.duration_seconds is not None:
            timing.append(f"Spent {format_duration(task.duration_seconds)}")
        self.timing.set_text("\n".join(timing))
        self.timing.setVisible(bool(timing))
        if task.delay_reason:
            reason = DELAY_REASON_LABELS.get(task.delay_reason, task.delay_reason)
            note = f" — {task.delay_note}" if task.delay_note else ""
            self.delay.set_text(f"{reason}{note}")
            self.delay.setVisible(True)
        else:
            self.delay.setVisible(False)

        todo = task.status == Status.TODO
        ongoing = task.status == Status.ONGOING
        running = task.is_running()
        paused = task.is_paused()
        closed = task.status in (Status.DONE, Status.MISSED)
        self.start_btn.setVisible(todo)
        self.pause_btn.setVisible(running)
        self.resume_btn.setVisible(paused)
        self.finish_primary.setVisible(running)
        self.finish_btn.setVisible(todo or paused)
        self.unstart_btn.setVisible(ongoing)
        self.miss_btn.setVisible(todo or ongoing)
        self.reopen_btn.setVisible(closed)
        if running:
            self._clock.start()
        else:
            self._clock.stop()

    def _tick(self) -> None:
        task = self._task
        if task is None:
            return
        caption = format_time_progress(task)
        elapsed = task.elapsed_seconds()
        ratio = task.progress_ratio()
        if elapsed is None:
            self.progress.setVisible(False)
            self.time_bar.set_progress(None)
            return
        self.progress.set_text(caption)
        self.progress.setVisible(bool(caption))
        if ratio is None:
            self.time_bar.set_progress(None)
        else:
            self.time_bar.set_progress(ratio, overrun=ratio > 1)
