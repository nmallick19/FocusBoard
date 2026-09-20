from __future__ import annotations

from PySide6.QtGui import QAction, QCursor, QFont
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from focusboard.db import Database
from focusboard.desktop import autostart_enabled, make_icon, set_autostart
from focusboard.hub import Hub
from focusboard.models import STATUS_LABELS, Status, Task
from focusboard.theme import build_theme_menu
from focusboard.util import format_due, format_when

TRAY_LIMIT = 20
REMINDER_LIMIT = 8


def _task_label(task: Task) -> str:
    status = STATUS_LABELS.get(task.status, task.status)
    return f"{task.title}  ·  {format_due(task.due_at)}  ·  {status}"


def _reminder_label(task: Task) -> str:
    if task.is_paused():
        mark = "❚❚ "
    elif task.status == Status.ONGOING:
        mark = "▶ "
    else:
        mark = ""
    return f"{mark}{task.title}    {format_when(task.due_at)}"


class TrayIcon(QSystemTrayIcon):
    def __init__(self, db: Database, hub: Hub, window: QWidget, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.hub = hub
        self.window = window
        self.setIcon(window.windowIcon() if window.windowIcon() else make_icon())
        self.setToolTip("Focusboard")
        self.menu = QMenu()
        self.setContextMenu(self.menu)
        self._theme_menu = build_theme_menu(None, db, hub)
        self.menu.aboutToShow.connect(self.rebuild)
        self.activated.connect(self._activated)
        hub.tasks_changed.connect(self.rebuild)
        self.rebuild()

    def rebuild(self) -> None:
        self.menu.clear()
        open_action = QAction("Open Focusboard", self.menu)
        open_action.triggered.connect(lambda: self.hub.show_main.emit())
        new_action = QAction("New task", self.menu)
        new_action.triggered.connect(self._new_task)
        self.menu.addAction(open_action)
        self.menu.addAction(new_action)
        self.menu.addSeparator()
        self._add_reminders()
        self.menu.addSeparator()

        self._add_submenu("All tasks", self.db.list_all())
        self._add_submenu("Today", self.db.list_today())
        self._add_submenu("Tomorrow to +3 days", self.db.list_next_three_days())
        self._add_submenu("Days 4–7", self.db.list_next_seven_days())

        self.menu.addSeparator()
        self.menu.addMenu(self._theme_menu)
        autostart_action = QAction("Start at login", self.menu)
        autostart_action.setCheckable(True)
        autostart_action.setChecked(autostart_enabled())
        autostart_action.toggled.connect(set_autostart)
        quit_action = QAction("Quit", self.menu)
        quit_action.triggered.connect(lambda: QApplication.quit())
        self.menu.addAction(autostart_action)
        self.menu.addAction(quit_action)

        buckets = self.db.list_reminders()
        today_n = len(buckets.today)
        coming_n = len(buckets.coming)
        self.setToolTip(f"Focusboard — {today_n} today, {coming_n} in 3 days")

    def _add_reminders(self) -> None:
        buckets = self.db.list_reminders()
        header = QAction("Reminders", self.menu)
        header.setEnabled(False)
        font = QFont(header.font())
        font.setBold(True)
        header.setFont(font)
        self.menu.addAction(header)
        if not buckets.today and not buckets.coming:
            empty = QAction("Nothing due today or in the next 3 days", self.menu)
            empty.setEnabled(False)
            self.menu.addAction(empty)
            return
        if buckets.today:
            self.menu.addSection("Due today")
            for task in buckets.today[:REMINDER_LIMIT]:
                self._add_reminder_item(task)
        if buckets.coming:
            self.menu.addSection("Due in 3 days")
            for task in buckets.coming[:REMINDER_LIMIT]:
                self._add_reminder_item(task)

    def _add_reminder_item(self, task: Task) -> None:
        action = QAction(_reminder_label(task), self.menu)
        task_id = task.id
        action.triggered.connect(lambda _=False, tid=task_id: self._open_task(tid))
        self.menu.addAction(action)

    def _add_submenu(self, title: str, tasks: list[Task]) -> None:
        submenu = self.menu.addMenu(f"{title} ({len(tasks)})")
        if not tasks:
            empty = QAction("No tasks", submenu)
            empty.setEnabled(False)
            submenu.addAction(empty)
            return
        for task in tasks[:TRAY_LIMIT]:
            action = QAction(_task_label(task), submenu)
            task_id = task.id
            action.triggered.connect(lambda _=False, tid=task_id: self._open_task(tid))
            submenu.addAction(action)
        if len(tasks) > TRAY_LIMIT:
            more = QAction(f"Open remaining {len(tasks) - TRAY_LIMIT} in Focusboard…", submenu)
            more.triggered.connect(lambda: self.hub.show_main.emit())
            submenu.addAction(more)

    def _open_task(self, task_id: int | None) -> None:
        if task_id is None:
            self.hub.show_main.emit()
            return
        self.hub.show_main_task.emit(task_id)

    def _new_task(self) -> None:
        self.hub.show_main.emit()
        add_task = getattr(self.window, "focus_page", None)
        if add_task is not None:
            self.window.focus_page.add_task()

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.rebuild()
            self.menu.popup(QCursor.pos())
