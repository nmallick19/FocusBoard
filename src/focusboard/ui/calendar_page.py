from __future__ import annotations

from datetime import datetime, time

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import (
    QCalendarWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from focusboard.db import Database
from focusboard.hub import Hub
from focusboard.models import Task
from focusboard.ui import actions
from focusboard.ui.chrome import IconButton, PrimaryButton, SectionHeader
from focusboard.ui.inspector import TaskInspector
from focusboard.ui.task_dialog import item_dialog
from focusboard.ui.task_list import TaskList


class CalendarPage(QWidget):
    def __init__(self, db: Database, hub: Hub, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.hub = hub

        root = QHBoxLayout(self)
        root.setContentsMargins(24, 16, 0, 0)
        root.setSpacing(0)

        cal_column = QVBoxLayout()
        cal_column.setContentsMargins(0, 0, 0, 16)
        cal_column.setSpacing(0)
        cal_wrap = QFrame()
        cal_wrap.setObjectName("CalendarCard")
        cal_wrap.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        cal_wrap.setFixedWidth(360)
        cal_wrap.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)
        cal_layout = QVBoxLayout(cal_wrap)
        cal_layout.setContentsMargins(12, 10, 12, 12)
        cal_layout.setSpacing(8)

        nav = QHBoxLayout()
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(4)
        self.prev_month = IconButton("‹")
        self.prev_month.setToolTip("Previous month")
        self.next_month = IconButton("›")
        self.next_month.setToolTip("Next month")
        self.month_label = QLabel()
        self.month_label.setObjectName("CalendarMonth")
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self.prev_month)
        nav.addWidget(self.month_label, 1)
        nav.addWidget(self.next_month)
        cal_layout.addLayout(nav)

        self.calendar = QCalendarWidget()
        self.calendar.setObjectName("MonthCalendar")
        self.calendar.setGridVisible(False)
        self.calendar.setNavigationBarVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        self.calendar.setFixedSize(336, 300)
        self.calendar.selectionChanged.connect(self.refresh)
        self.calendar.currentPageChanged.connect(lambda *_: self._on_page_changed())
        self.prev_month.clicked.connect(self.calendar.showPreviousMonth)
        self.next_month.clicked.connect(self.calendar.showNextMonth)
        cal_layout.addWidget(self.calendar)
        cal_column.addWidget(cal_wrap)
        cal_column.addStretch()
        root.addLayout(cal_column)

        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(24, 0, 8, 0)
        side_layout.setSpacing(0)
        heading_row = QHBoxLayout()
        self.heading = SectionHeader("Tasks")
        heading_row.addWidget(self.heading, 1)
        self.add_btn = PrimaryButton("Add on this day")
        self.add_btn.setToolTip("Create a task due on the selected day (Ctrl+N)")
        heading_row.addWidget(self.add_btn)
        side_layout.addLayout(heading_row)

        self.list = TaskList(empty_text="No tasks on this day.")
        self.list.task_selected.connect(self._on_selected)
        self.list.task_activated.connect(lambda _task: self.edit_task())
        self.list.status_clicked.connect(lambda task: actions.toggle_progress(self, self.db, self.hub, task))
        self.list.context_action.connect(self._on_context)
        side_layout.addWidget(self.list, 1)
        self.add_btn.clicked.connect(self.add_task)
        root.addWidget(side, 1)

        self.inspector = TaskInspector()
        self.inspector.start.connect(lambda: actions.start_task(self, self.db, self.hub, self.selected_task()))
        self.inspector.unstart.connect(lambda: actions.unstart_task(self, self.db, self.hub, self.selected_task()))
        self.inspector.pause.connect(lambda: actions.pause_task(self, self.db, self.hub, self.selected_task()))
        self.inspector.resume.connect(lambda: actions.resume_task(self, self.db, self.hub, self.selected_task()))
        self.inspector.reopen.connect(lambda: actions.reopen_task(self, self.db, self.hub, self.selected_task()))
        self.inspector.finish.connect(lambda: actions.finish_task(self, self.db, self.hub, self.selected_task()))
        self.inspector.missed.connect(lambda: actions.miss_task(self, self.db, self.hub, self.selected_task()))
        self.inspector.edit.connect(self.edit_task)
        self.inspector.delete.connect(lambda: actions.delete_task(self, self.db, self.hub, self.selected_task()))
        self.inspector.close_requested.connect(self.clear_task_selection)
        root.addWidget(self.inspector)
        self.refresh()

    def _selected_date(self):
        qd: QDate = self.calendar.selectedDate()
        return datetime(qd.year(), qd.month(), qd.day()).date()

    def _on_page_changed(self) -> None:
        self._sync_month_label()
        self._mark_dates()

    def _sync_month_label(self) -> None:
        page = QDate(self.calendar.yearShown(), self.calendar.monthShown(), 1)
        self.month_label.setText(page.toString("MMMM yyyy"))

    def _mark_dates(self) -> None:
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())
        year = self.calendar.yearShown()
        month = self.calendar.monthShown()
        marked = QTextCharFormat()
        marked.setFontWeight(700)
        marked.setForeground(QColor("#2563EB"))
        marked.setBackground(QColor(37, 99, 235, 28))
        for day in self.db.dates_with_tasks(year, month):
            self.calendar.setDateTextFormat(QDate(day.year, day.month, day.day), marked)

    def _on_selected(self, task: Task | None) -> None:
        self.inspector.set_task(task)

    def _on_context(self, name: str, task: Task) -> None:
        if name == "edit":
            self.edit_task()
            return
        actions.apply_named(self, self.db, self.hub, name, task)

    def selected_task(self) -> Task | None:
        return self.list.selected_task()

    def select_task_id(self, task_id: int) -> bool:
        return self.list.select_id(task_id)

    def clear_task_selection(self) -> None:
        self.list.clear_selection()
        self.inspector.set_task(None)

    def add_task(self) -> None:
        day = self._selected_date()
        default_due = datetime.combine(day, time(17, 0))
        dialog = item_dialog(self, default_due=default_due)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        created = self.db.create_task(**dialog.values())
        actions.log_action(self.db, self.hub, "create", created)
        self.hub.tasks_changed.emit()
        if created.id is not None:
            self.select_task_id(created.id)

    def edit_task(self) -> None:
        task = self.selected_task()
        if task is None:
            return
        dialog = item_dialog(self, task=task)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self.db.update_task(task.id, **dialog.values())  # type: ignore[arg-type]
        actions.log_action(self.db, self.hub, "edit", task)
        self.hub.tasks_changed.emit()

    def refresh(self) -> None:
        day = self._selected_date()
        self.heading.title.setText(day.strftime("%A %-d %B"))
        selected_id = self.list.selected_id()
        tasks = self.db.tasks_for_date(day)
        self.list.set_tasks(tasks, selected_id)
        self.heading.set_count(len(tasks))
        self.inspector.set_task(self.list.selected_task())
        self._sync_month_label()
        self._mark_dates()
