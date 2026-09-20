from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QWidget

from focusboard.db import Database
from focusboard.hub import Hub
from focusboard.models import (
    PAUSE_REASON_CHECKIN,
    PAUSE_REASON_DISPLAY_OFF,
    PAUSE_REASON_SCREEN_LOCK,
    PAUSE_REASON_SLEEP,
)
from focusboard.notify import notify
from focusboard.session import SessionGuard
from focusboard.sound import play_gonk
from focusboard.ui.prompts import CheckInDialog, SessionPauseDialog
from focusboard.ui.actions import log_action


class FocusWatch(QObject):
    def __init__(self, db: Database, hub: Hub, window: QWidget, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.hub = hub
        self.window = window
        self._busy = False
        self._checkin = QTimer(self)
        self._checkin.setSingleShot(True)
        self._checkin.timeout.connect(self._offer_checkin)
        self._session = SessionGuard(self)
        self._session.unavailable.connect(self._on_session_away)
        self._session.available.connect(self._on_session_back)
        hub.tasks_changed.connect(self._schedule_checkin)
        QTimer.singleShot(800, self._on_startup)
        self._schedule_checkin()

    def stop(self) -> None:
        self._busy = True
        self._checkin.stop()
        self._session.stop()

    def _raise(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _schedule_checkin(self) -> None:
        self._checkin.stop()
        if self._busy or self._session.is_away():
            return
        running = self.db.running_tasks()
        if not running:
            return
        due = running[0].checkin_due_at()
        if due is None:
            return
        remaining = max(0, int((due - datetime.now()).total_seconds() * 1000))
        self._checkin.start(remaining)

    def _offer_checkin(self) -> None:
        if self._busy or self._session.is_away():
            return
        running = self.db.running_tasks()
        if not running:
            return
        task = running[0]
        if not task.is_checkin_due() or task.id is None:
            self._schedule_checkin()
            return
        self._busy = True
        self._raise()
        dialog = CheckInDialog(task.title, self.window)
        accepted = dialog.exec() == CheckInDialog.DialogCode.Accepted
        if accepted:
            self.db.touch_ping(task.id)
            log_action(self.db, self.hub, "check-in acknowledge", task, source="user")
        else:
            self.db.pause_task(task.id, PAUSE_REASON_CHECKIN)
            play_gonk(announce=True)
            notify("Paused", f"“{task.title}” is paused.")
            log_action(self.db, self.hub, "check-in pause", task, source="user")
        self.hub.tasks_changed.emit()
        self._busy = False
        self._schedule_checkin()

    def _on_session_away(self, reason: str) -> None:
        running = self.db.running_tasks()
        if not running or running[0].id is None:
            return
        pause_reason = {
            "sleep": PAUSE_REASON_SLEEP,
            "display_off": PAUSE_REASON_DISPLAY_OFF,
        }.get(reason, PAUSE_REASON_SCREEN_LOCK)
        self.db.pause_task(running[0].id, pause_reason)
        log_action(
            self.db,
            self.hub,
            "auto-pause",
            running[0],
            source="app",
            detail=f"{running[0].title} ({reason})",
        )
        self.hub.tasks_changed.emit()
        self._checkin.stop()

    def _on_session_back(self) -> None:
        self._prompt_session_resume()
        self._schedule_checkin()

    def _on_startup(self) -> None:
        if self._busy:
            return
        if self._session.is_away():
            self._on_session_away("screen_lock")
            return
        self._prompt_session_resume()

    def _prompt_session_resume(self) -> None:
        if self._busy or self._session.is_away():
            return
        paused = self.db.session_paused_tasks()
        if not paused:
            return
        task = paused[0]
        explanation = task.session_pause_explanation()
        if not explanation or task.id is None:
            return
        self._busy = True
        self._raise()
        dialog = SessionPauseDialog(task.title, explanation, self.window)
        accepted = dialog.exec() == SessionPauseDialog.DialogCode.Accepted
        if accepted:
            self.db.resume_task(task.id)
            log_action(self.db, self.hub, "resume after lock", task, source="user")
        else:
            self.db.keep_paused(task.id)
            log_action(self.db, self.hub, "keep paused after lock", task, source="user")
        self.hub.tasks_changed.emit()
        self._busy = False
        self._schedule_checkin()
