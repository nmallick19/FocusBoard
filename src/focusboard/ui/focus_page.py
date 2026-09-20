from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from focusboard.db import Database
from focusboard.hub import Hub
from focusboard.models import Task
from focusboard.ui import actions
from focusboard.ui.chrome import IconButton, SectionHeader
from focusboard.ui.inspector import TaskInspector
from focusboard.ui.sidebar import STATUS_VIEWS, FocusSidebar
from focusboard.ui.task_dialog import item_dialog
from focusboard.ui.task_list import TaskList


class FocusPage(QWidget):
    def __init__(self, db: Database, hub: Hub, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.hub = hub
        self._active_list: TaskList | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = FocusSidebar()
        self.sidebar.sync_from_filters(self.db.status_filters())
        self.sidebar.view_changed.connect(self._on_view_changed)
        self.sidebar.project_changed.connect(lambda _name: self.refresh())
        self.sidebar.close_requested.connect(lambda: self.set_sidebar_visible(False))
        root.addWidget(self.sidebar)

        self.sidebar_rail = QFrame()
        self.sidebar_rail.setObjectName("SidebarRail")
        self.sidebar_rail.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.sidebar_rail.setFixedWidth(44)
        rail_layout = QVBoxLayout(self.sidebar_rail)
        rail_layout.setContentsMargins(8, 10, 8, 8)
        rail_layout.setSpacing(0)
        self.open_sidebar_btn = IconButton("☰")
        self.open_sidebar_btn.setToolTip("Show sidebar")
        self.open_sidebar_btn.setAccessibleName("Show sidebar")
        self.open_sidebar_btn.clicked.connect(lambda: self.set_sidebar_visible(True))
        rail_layout.addWidget(self.open_sidebar_btn)
        rail_layout.addStretch()
        root.addWidget(self.sidebar_rail)
        self.set_sidebar_visible(self.db.get_setting("sidebar_open", "1") != "0", persist=False)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName("FocusSplitter")
        self.splitter.setChildrenCollapsible(False)

        scroll = QScrollArea()
        scroll.setObjectName("FocusScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)
        body = QWidget()
        body.setObjectName("FocusBody")
        column = QVBoxLayout(body)
        column.setContentsMargins(28, 8, 16, 24)
        column.setSpacing(0)

        self.today_header = SectionHeader("Today", hero=True)
        self.today = TaskList(
            overdue_group=True,
            empty_text="Nothing needs attention today.",
        )
        column.addWidget(self.today_header)
        column.addWidget(self.today)

        self.upcoming_header = SectionHeader("Upcoming")
        self.upcoming = TaskList(
            group_dates=True,
            empty_text="Nothing due in the next three days.",
        )
        column.addWidget(self.upcoming_header)
        column.addWidget(self.upcoming)

        self.later_header = SectionHeader("Later")
        self.later = TaskList(
            group_dates=True,
            empty_text="No later tasks.",
        )
        column.addWidget(self.later_header)
        column.addWidget(self.later)
        column.addStretch()
        scroll.setWidget(body)
        self.splitter.addWidget(scroll)

        self.inspector = TaskInspector()
        self._bind_inspector(self.inspector)
        self.splitter.addWidget(self.inspector)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([900, 320])
        root.addWidget(self.splitter, 1)

        for widget in self._lists:
            widget.task_selected.connect(lambda task, source=widget: self._on_selected(source, task))
            widget.task_activated.connect(lambda _task: self.edit_task())
            widget.status_clicked.connect(lambda task: actions.toggle_progress(self, self.db, self.hub, task))
            widget.context_action.connect(self._on_context)

        self.refresh()

    @property
    def _lists(self) -> tuple[TaskList, ...]:
        return (self.today, self.upcoming, self.later)

    def _bind_inspector(self, inspector: TaskInspector) -> None:
        inspector.start.connect(lambda: actions.start_task(self, self.db, self.hub, self.selected_task()))
        inspector.unstart.connect(lambda: actions.unstart_task(self, self.db, self.hub, self.selected_task()))
        inspector.pause.connect(lambda: actions.pause_task(self, self.db, self.hub, self.selected_task()))
        inspector.resume.connect(lambda: actions.resume_task(self, self.db, self.hub, self.selected_task()))
        inspector.reopen.connect(lambda: actions.reopen_task(self, self.db, self.hub, self.selected_task()))
        inspector.finish.connect(lambda: actions.finish_task(self, self.db, self.hub, self.selected_task()))
        inspector.missed.connect(lambda: actions.miss_task(self, self.db, self.hub, self.selected_task()))
        inspector.edit.connect(self.edit_task)
        inspector.delete.connect(lambda: actions.delete_task(self, self.db, self.hub, self.selected_task()))
        inspector.close_requested.connect(self.clear_task_selection)

    def set_view(self, name: str) -> None:
        self.sidebar.set_view(name)

    def set_sidebar_visible(self, visible: bool, *, persist: bool = True) -> None:
        self.sidebar.setVisible(visible)
        self.sidebar_rail.setVisible(not visible)
        if persist:
            self.db.set_setting("sidebar_open", "1" if visible else "0")

    def toggle_sidebar(self) -> None:
        self.set_sidebar_visible(not self.sidebar.isVisible())

    def _on_view_changed(self, name: str) -> None:
        flags = STATUS_VIEWS.get(name, STATUS_VIEWS["all"])
        self.db.set_status_filters(**flags)
        self.hub.tasks_changed.emit()

    def _on_selected(self, source: TaskList, task: Task | None) -> None:
        self._active_list = source
        if task is None:
            self.inspector.set_task(None)
            return
        for widget in self._lists:
            if widget is not source:
                widget.clear_selection()
        self.inspector.set_task(task)

    def _on_context(self, name: str, task: Task) -> None:
        if name == "edit":
            self.edit_task()
            return
        actions.apply_named(self, self.db, self.hub, name, task)

    def selected_task(self) -> Task | None:
        if self._active_list:
            task = self._active_list.selected_task()
            if task:
                return task
        for widget in self._lists:
            task = widget.selected_task()
            if task:
                return task
        return None

    def select_task_id(self, task_id: int) -> None:
        for widget in self._lists:
            if widget.select_id(task_id):
                self._active_list = widget
                return

    def clear_task_selection(self) -> None:
        for widget in self._lists:
            widget.clear_selection()
        self._active_list = None
        self.inspector.set_task(None)

    def select_offset(self, delta: int) -> None:
        tasks = [task for widget in self._lists for task in widget.tasks()]
        if not tasks:
            return
        current = self.selected_task()
        ids = [task.id for task in tasks]
        if current and current.id in ids:
            index = max(0, min(len(ids) - 1, ids.index(current.id) + delta))
        else:
            index = 0 if delta >= 0 else len(ids) - 1
        chosen = tasks[index]
        if chosen.id is not None:
            self.select_task_id(chosen.id)

    def showing_meetings(self) -> bool:
        return self.sidebar.current_project() == "meetings"

    def add_task(self) -> None:
        dialog = item_dialog(self, meeting=self.showing_meetings())
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        created = self.db.create_task(**dialog.values())
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
        self.hub.tasks_changed.emit()

    def _filter_project(self, tasks: list[Task]) -> list[Task]:
        project = self.sidebar.current_project()
        if not project or project == "meetings":
            return tasks
        return [task for task in tasks if task.category == project]

    def refresh(self) -> None:
        selected = self.selected_task()
        selected_id = selected.id if selected else None
        meetings = self.showing_meetings()
        today = self._filter_project(self.db.list_today(meetings=meetings))
        upcoming = self._filter_project(self.db.list_next_three_days(meetings=meetings))
        later = self._filter_project(self.db.list_later(meetings=meetings))
        self.today.empty_text = "No meetings today." if meetings else "Nothing needs attention today."
        self.upcoming.empty_text = "No meetings in the next three days." if meetings else "Nothing due in the next three days."
        self.later.empty_text = "No later meetings." if meetings else "No later tasks."
        self.today.set_tasks(today, selected_id)
        self.upcoming.set_tasks(upcoming, selected_id)
        self.later.set_tasks(later, selected_id)
        self.today_header.set_count(len(today))
        self.upcoming_header.set_count(len(upcoming))
        self.later_header.set_count(len(later))
        self.upcoming_header.setVisible(bool(upcoming))
        self.upcoming.setVisible(bool(upcoming))
        self.later_header.setVisible(bool(later))
        self.later.setVisible(bool(later))
        found = False
        if selected_id is not None:
            for widget in self._lists:
                if widget.select_id(selected_id):
                    self._active_list = widget
                    found = True
                    break
        if not found:
            self.inspector.set_task(None)
        self.sidebar.sync_from_filters(self.db.status_filters())
