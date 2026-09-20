from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QPoint, QRect, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QStyle,
    QStyleOption,
    QVBoxLayout,
    QWidget,
)

from focusboard.models import (
    CATEGORY_LABELS,
    DIFFICULTY_LABELS,
    PRIORITY_LABELS,
    STATUS_LABELS,
    Status,
    Task,
)
from focusboard.ui.chrome import DateHeader, EmptyHint
from focusboard.ui.grouping import date_heading, group_by_due_date, split_overdue
from focusboard.util import due_band, due_row_parts, format_time_progress

PRIORITY_COLORS = {
    "high": "#E11D48",
    "medium": "#D97706",
    "low": "#0D9488",
}

STATUS_COLORS = {
    Status.TODO.value: "#64748B",
    Status.ONGOING.value: "#2563EB",
    Status.DONE.value: "#16A34A",
    Status.MISSED.value: "#EA580C",
}


def _refresh_style(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class DueStamp(QWidget):
    def __init__(self, parent=None, *, align_right: bool = True) -> None:
        super().__init__(parent)
        self.setObjectName("DueBlock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(0)
        align = Qt.AlignmentFlag.AlignRight if align_right else Qt.AlignmentFlag.AlignLeft
        align |= Qt.AlignmentFlag.AlignVCenter
        self.day = QLabel("—")
        self.day.setObjectName("TaskDueDate")
        self.time = QLabel("—")
        self.time.setObjectName("TaskDueTime")
        self.remain = QLabel("")
        self.remain.setObjectName("TaskDueRemain")
        for label in (self.day, self.time, self.remain):
            label.setAlignment(align)
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(label)

    def set_due(self, due_at: datetime, *, overdue: bool = False, show_remain: bool = True) -> None:
        day_text, time_text, remain_text = due_row_parts(due_at)
        self.day.setText(day_text)
        self.time.setText(time_text)
        self.remain.setText(remain_text)
        self.remain.setVisible(show_remain and bool(remain_text))
        band = due_band(due_at, overdue=overdue)
        self.setProperty("due", band)
        for label in (self.day, self.time, self.remain):
            label.setProperty("due", band)
            _refresh_style(label)
        _refresh_style(self)


class StatusMark(QWidget):
    clicked = Signal()

    def __init__(self, task: Task, parent=None) -> None:
        super().__init__(parent)
        self.task = task
        self.setFixedSize(24, 24)
        if task.is_meeting():
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setToolTip("Meeting")
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip("Paused" if task.is_paused() else STATUS_LABELS.get(task.status, task.status))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self.task.is_meeting():
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(STATUS_COLORS.get(self.task.status, "#64748B"))
        rect = self.rect().adjusted(3, 3, -3, -3)
        if self.task.status == Status.DONE:
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect)
            painter.setPen(QColor("white"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "✓")
        elif self.task.is_paused():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(color)
            painter.drawEllipse(rect)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            cx = self.rect().center().x()
            cy = self.rect().center().y()
            painter.drawRoundedRect(QRect(cx - 4, cy - 4, 3, 8), 1, 1)
            painter.drawRoundedRect(QRect(cx + 1, cy - 4, 3, 8), 1, 1)
        elif self.task.status == Status.ONGOING:
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect)
        elif self.task.status == Status.MISSED:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(color)
            painter.drawEllipse(rect)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "!")
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(color)
            painter.drawEllipse(rect)


class TimeBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TimeBar")
        self.setFixedHeight(7)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._ratio = 0.0
        self._overrun = False
        self.setVisible(False)

    def set_progress(self, ratio: float | None, *, overrun: bool = False) -> None:
        if ratio is None:
            self.setVisible(False)
            return
        self.setVisible(True)
        self._ratio = max(0.0, min(1.0, ratio))
        self._overrun = overrun
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        track = QColor(self.palette().mid().color())
        track.setAlpha(70)
        rect = self.rect()
        painter.setBrush(track)
        painter.drawRoundedRect(rect, 3, 3)
        width = int(rect.width() * self._ratio)
        if width <= 0:
            return
        fill = QColor("#E11D48" if self._overrun else "#2563EB")
        painter.setBrush(fill)
        painter.drawRoundedRect(QRect(rect.x(), rect.y(), max(width, 6), rect.height()), 3, 3)


class PriorityDot(QWidget):
    def __init__(self, priority: str, parent=None) -> None:
        super().__init__(parent)
        self.priority = priority
        self.setFixedSize(8, 8)
        self.setToolTip(PRIORITY_LABELS.get(priority, priority))

    def paintEvent(self, event) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(PRIORITY_COLORS.get(self.priority, "#64748B")))
        painter.drawEllipse(self.rect())


class TaskRow(QFrame):
    selected = Signal(object)
    activated = Signal(object)
    status_clicked = Signal(object)
    context_action = Signal(str, object)

    def __init__(self, task: Task, parent=None) -> None:
        super().__init__(parent)
        self.task = task
        self.setObjectName("TaskRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("overdue", self._is_overdue())
        self.setProperty("closed", task.status in (Status.DONE, Status.MISSED))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)

        shell = QVBoxLayout(self)
        shell.setContentsMargins(10, 10, 12, 8)
        shell.setSpacing(6)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.mark = StatusMark(task)
        self.mark.clicked.connect(lambda: self.status_clicked.emit(self.task))
        layout.addWidget(self.mark, 0, Qt.AlignmentFlag.AlignVCenter)

        text = QVBoxLayout()
        text.setSpacing(2)
        title = QLabel(task.title)
        title.setObjectName("TaskTitle")
        font = QFont()
        font.setPointSize(13)
        font.setWeight(QFont.Weight.DemiBold)
        if task.status == Status.DONE:
            font.setStrikeOut(True)
        title.setFont(font)
        title.setWordWrap(False)
        text.addWidget(title)

        meta = QHBoxLayout()
        meta.setSpacing(6)
        if not task.is_meeting():
            meta.addWidget(PriorityDot(task.priority), 0, Qt.AlignmentFlag.AlignVCenter)
        if task.is_meeting():
            bits = []
            place = task.meeting_place()
            if place:
                bits.append(place)
            if task.is_recurring():
                bits.append(task.repeat_label())
            else:
                bits.append("Meeting")
        else:
            bits = [
                PRIORITY_LABELS.get(task.priority, task.priority),
                DIFFICULTY_LABELS.get(task.difficulty, task.difficulty),
                CATEGORY_LABELS.get(task.category, task.category),
            ]
            if task.is_recurring():
                bits.append(task.repeat_label())
            if task.is_paused():
                bits.append("Paused")
            elif task.status == Status.ONGOING:
                bits.append("Ongoing")
            elif task.status == Status.MISSED:
                bits.append("Missed")
        meta_label = QLabel(" · ".join(bits))
        meta_label.setObjectName("MetaMuted")
        meta.addWidget(meta_label)
        self.time_caption = QLabel()
        self.time_caption.setObjectName("TimeCaption")
        meta.addWidget(self.time_caption)
        meta.addStretch()
        text.addLayout(meta)
        layout.addLayout(text, 1)

        due_stamp = DueStamp()
        due_stamp.set_due(task.when(), overdue=self._is_overdue(), show_remain=task.is_incomplete())
        layout.addWidget(due_stamp, 0, Qt.AlignmentFlag.AlignVCenter)
        shell.addLayout(layout)

        self.time_bar = TimeBar()
        shell.addWidget(self.time_bar)
        self.tick()

        for label in (title, meta_label, self.time_caption):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def tick(self) -> None:
        if self.task.is_meeting():
            self.time_caption.setVisible(False)
            self.time_bar.set_progress(None)
            return
        caption = format_time_progress(self.task)
        self.time_caption.setText(f" · {caption}" if caption else "")
        self.time_caption.setVisible(bool(caption))
        elapsed = self.task.elapsed_seconds()
        ratio = self.task.progress_ratio()
        if elapsed is None or ratio is None:
            self.time_bar.set_progress(None)
        else:
            self.time_bar.set_progress(ratio, overrun=ratio > 1)

    def _is_overdue(self) -> bool:
        return self.task.is_incomplete() and self.task.due_at < datetime.now()

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        _refresh_style(self)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.task)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self.task)
        super().mouseDoubleClickEvent(event)

    def _menu(self, pos: QPoint) -> None:
        self.selected.emit(self.task)
        menu = QMenu(self)
        if self.task.is_meeting():
            menu.addAction("Copy", lambda: self.context_action.emit("copy", self.task))
            menu.addAction("Edit", lambda: self.context_action.emit("edit", self.task))
            menu.addAction("Delete", lambda: self.context_action.emit("delete", self.task))
            menu.exec(self.mapToGlobal(pos))
            return
        todo = self.task.status == Status.TODO
        ongoing = self.task.status == Status.ONGOING
        closed = self.task.status in (Status.DONE, Status.MISSED)
        if todo:
            menu.addAction("Start", lambda: self.context_action.emit("start", self.task))
        if ongoing:
            if self.task.is_paused():
                menu.addAction("Resume", lambda: self.context_action.emit("resume", self.task))
            else:
                menu.addAction("Pause", lambda: self.context_action.emit("pause", self.task))
            menu.addAction("Undo Start", lambda: self.context_action.emit("unstart", self.task))
        if todo or ongoing:
            menu.addAction("Finish", lambda: self.context_action.emit("finish", self.task))
            menu.addAction("Missed", lambda: self.context_action.emit("missed", self.task))
        if closed:
            menu.addAction("Reopen", lambda: self.context_action.emit("reopen", self.task))
        menu.addSeparator()
        menu.addAction("Copy", lambda: self.context_action.emit("copy", self.task))
        menu.addAction("Edit", lambda: self.context_action.emit("edit", self.task))
        menu.addAction("Delete", lambda: self.context_action.emit("delete", self.task))
        menu.exec(self.mapToGlobal(pos))

    def paintEvent(self, event) -> None:
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)
        super().paintEvent(event)


class TaskList(QWidget):
    task_selected = Signal(object)
    task_activated = Signal(object)
    status_clicked = Signal(object)
    context_action = Signal(str, object)

    def __init__(
        self,
        parent=None,
        *,
        group_dates: bool = False,
        overdue_group: bool = False,
        empty_text: str = "No tasks",
    ) -> None:
        super().__init__(parent)
        self.group_dates = group_dates
        self.overdue_group = overdue_group
        self.empty_text = empty_text
        self._tasks: list[Task] = []
        self._rows: dict[int, TaskRow] = {}
        self._selected_id: int | None = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._clock = QTimer(self)
        self._clock.setInterval(1000)
        self._clock.timeout.connect(self._tick_progress)

    def tasks(self) -> list[Task]:
        return list(self._tasks)

    def selected_task(self) -> Task | None:
        if self._selected_id is None:
            return None
        for task in self._tasks:
            if task.id == self._selected_id:
                return task
        return None

    def selected_id(self) -> int | None:
        return self._selected_id

    def clear_selection(self) -> None:
        self._selected_id = None
        for row in self._rows.values():
            row.set_selected(False)

    def select_id(self, task_id: int | None) -> bool:
        if task_id is None:
            self.clear_selection()
            return False
        row = self._rows.get(task_id)
        if row is None:
            return False
        self._selected_id = task_id
        for other_id, other in self._rows.items():
            other.set_selected(other_id == task_id)
        self.task_selected.emit(row.task)
        return True

    def set_tasks(self, tasks: list[Task], selected_id: int | None = None) -> None:
        self._tasks = list(tasks)
        keep = selected_id if selected_id is not None else self._selected_id
        self._rebuild()
        if keep is not None and keep in self._rows:
            self._selected_id = keep
            self._rows[keep].set_selected(True)
        else:
            self._selected_id = None
        if any(task.is_running() for task in self._tasks):
            self._clock.start()
        else:
            self._clock.stop()

    def _tick_progress(self) -> None:
        for row in self._rows.values():
            row.tick()

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self._rows = {}

    def _rebuild(self) -> None:
        self._clear()
        if not self._tasks:
            self._layout.addWidget(EmptyHint(self.empty_text))
            return

        overdue: list[Task] = []
        rest = self._tasks
        if self.overdue_group:
            overdue, rest = split_overdue(self._tasks)
        if overdue:
            self._layout.addWidget(DateHeader("Overdue"))
            for task in overdue:
                self._add_row(task)
        if self.group_dates:
            for day, group in group_by_due_date(rest):
                self._layout.addWidget(DateHeader(date_heading(day)))
                for task in group:
                    self._add_row(task)
        else:
            for task in rest:
                self._add_row(task)

    def _add_row(self, task: Task) -> None:
        row = TaskRow(task)
        row.selected.connect(self._on_selected)
        row.activated.connect(self.task_activated.emit)
        row.status_clicked.connect(self._on_status)
        row.context_action.connect(self.context_action.emit)
        self._layout.addWidget(row)
        if task.id is not None:
            self._rows[task.id] = row

    def _on_selected(self, task: Task) -> None:
        self.select_id(task.id)

    def _on_status(self, task: Task) -> None:
        self.select_id(task.id)
        self.status_clicked.emit(task)


TaskListWidget = TaskList
