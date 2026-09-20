from __future__ import annotations

import sys
from datetime import date, datetime

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from focusboard.db import Database
from focusboard.desktop import autostart_enabled, install_menu_entry, make_icon, set_autostart
from focusboard.hub import Hub
from focusboard.notify import notify
from focusboard.session import session_is_present
from focusboard.theme import apply_theme, build_theme_menu
from focusboard.single_instance import acquire_instance_lock
from focusboard.ui.main_window import MainWindow
from focusboard.ui.tray import TrayIcon
from focusboard.util import format_due
from focusboard.watch import FocusWatch


class DueNotifier(QObject):
    def __init__(self, db: Database, hub: Hub, tray: QSystemTrayIcon | None, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.hub = hub
        self.tray = tray
        self.timer = QTimer(self)
        self.timer.setInterval(60_000)
        self.timer.timeout.connect(self.check)
        self.timer.start()
        QTimer.singleShot(3000, self.check)

    def check(self) -> None:
        self._planning_digest()
        now = datetime.now()
        rolled = False
        for task in self.db.list_incomplete():
            if task.id is None:
                continue
            if task.due_at <= now and not task.due_notified:
                notify("Task due", f"{task.title} — {format_due(task.due_at, now)}", self.tray)
                self.db.mark_due_notified(task.id)
        for meeting in self.db.list_open_meetings():
            if meeting.id is None:
                continue
            if meeting.due_at <= now:
                self.db.advance_meeting(meeting.id)
                rolled = True
                continue
            if meeting.meeting_reminder_due(now) and session_is_present():
                place = meeting.meeting_place()
                extra = f" — {place}" if place else ""
                notify(
                    "Meeting in 30 minutes",
                    f"{meeting.title}{extra} — {format_due(meeting.due_at, now)}",
                    self.tray,
                )
                self.db.mark_due_notified(meeting.id)
        if rolled:
            self.hub.tasks_changed.emit()

    def _planning_digest(self) -> None:
        today = date.today().isoformat()
        if self.db.get_setting("planning_notified_on") == today:
            return
        buckets = self.db.list_reminders()
        self.db.set_setting("planning_notified_on", today)
        if not buckets.today and not buckets.coming:
            return
        parts: list[str] = []
        if buckets.today:
            titles = ", ".join(task.title for task in buckets.today[:4])
            extra = "…" if len(buckets.today) > 4 else ""
            parts.append(f"Today ({len(buckets.today)}): {titles}{extra}")
        if buckets.coming:
            titles = ", ".join(task.title for task in buckets.coming[:4])
            extra = "…" if len(buckets.coming) > 4 else ""
            parts.append(f"Next 3 days ({len(buckets.coming)}): {titles}{extra}")
        notify("What needs doing", "\n".join(parts), self.tray)


def _build_menu(window: MainWindow, db: Database, hub: Hub) -> None:
    bar = window.menuBar()
    file_menu = bar.addMenu("&File")
    new_action = QAction("New task", window)
    new_action.setShortcut(QKeySequence.StandardKey.New)
    new_action.triggered.connect(lambda: window.focus_page.add_task())
    autostart_action = QAction("Start at login", window)
    autostart_action.setCheckable(True)
    autostart_action.setChecked(autostart_enabled())
    autostart_action.toggled.connect(set_autostart)
    quit_action = QAction("Quit", window)
    quit_action.setShortcut(QKeySequence.StandardKey.Quit)
    quit_action.triggered.connect(lambda: QApplication.quit())
    file_menu.addAction(new_action)
    file_menu.addSeparator()
    file_menu.addMenu(build_theme_menu(window, db, hub))
    file_menu.addSeparator()
    file_menu.addAction(autostart_action)
    file_menu.addSeparator()
    file_menu.addAction(quit_action)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    instance_lock = acquire_instance_lock()
    app = QApplication(argv)
    app.setApplicationName("Focusboard")
    app.setOrganizationName("Focusboard")
    app.setDesktopFileName("focusboard")
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    icon = make_icon()
    app.setWindowIcon(icon)

    db = Database()
    hub = Hub()
    apply_theme(app, db.get_theme())
    install_menu_entry()

    window = MainWindow(db, hub)
    _build_menu(window, db, hub)
    window.show()

    def follow_system(_scheme) -> None:
        if db.get_theme() == "system":
            apply_theme(app, "system")

    app.styleHints().colorSchemeChanged.connect(follow_system)

    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = TrayIcon(db, hub, window)
        tray.setIcon(icon)
        tray.show()
    app._tray = tray  # noqa: SLF001 — keep the tray alive
    app._notifier = DueNotifier(db, hub, tray, app)  # noqa: SLF001
    app._watch = FocusWatch(db, hub, window, app)  # noqa: SLF001
    app._instance_lock = instance_lock  # noqa: SLF001 — release on exit
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
