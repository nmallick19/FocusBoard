from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QMessageBox, QWidget

from focusboard.db import Database
from focusboard.hub import Hub
from focusboard.models import Status, Task
from focusboard.ui.delay_dialog import DelayDialog


def selected_or_warn(parent: QWidget, task: Task | None) -> Task | None:
    if task is None:
        QMessageBox.information(parent, "Focusboard", "Select a task first.")
        return None
    return task


def _not_a_task(parent: QWidget, task: Task) -> bool:
    if task.is_meeting():
        QMessageBox.information(parent, "Focusboard", "Meetings are reminders only. Edit them instead.")
        return True
    return False


def start_task(parent: QWidget, db: Database, hub: Hub, task: Task | None) -> None:
    task = selected_or_warn(parent, task)
    if task is None:
        return
    if _not_a_task(parent, task):
        return
    if task.status != Status.TODO:
        QMessageBox.information(parent, "Focusboard", "Only to-do tasks can be started.")
        return
    db.start_task(task.id)  # type: ignore[arg-type]
    hub.tasks_changed.emit()


def unstart_task(parent: QWidget, db: Database, hub: Hub, task: Task | None) -> None:
    task = selected_or_warn(parent, task)
    if task is None:
        return
    if _not_a_task(parent, task):
        return
    if task.status != Status.ONGOING:
        QMessageBox.information(parent, "Focusboard", "Only ongoing tasks can be returned to Next.")
        return
    db.unstart_task(task.id)  # type: ignore[arg-type]
    hub.tasks_changed.emit()


def pause_task(parent: QWidget, db: Database, hub: Hub, task: Task | None) -> None:
    task = selected_or_warn(parent, task)
    if task is None:
        return
    if _not_a_task(parent, task):
        return
    if not task.is_running():
        QMessageBox.information(parent, "Focusboard", "Only a running task can be paused.")
        return
    db.pause_task(task.id)  # type: ignore[arg-type]
    hub.tasks_changed.emit()


def resume_task(parent: QWidget, db: Database, hub: Hub, task: Task | None) -> None:
    task = selected_or_warn(parent, task)
    if task is None:
        return
    if _not_a_task(parent, task):
        return
    if not task.is_paused():
        QMessageBox.information(parent, "Focusboard", "Only a paused task can be resumed.")
        return
    db.resume_task(task.id)  # type: ignore[arg-type]
    hub.tasks_changed.emit()


def toggle_pause(parent: QWidget, db: Database, hub: Hub, task: Task | None) -> None:
    task = selected_or_warn(parent, task)
    if task is None:
        return
    if _not_a_task(parent, task):
        return
    if task.is_paused():
        resume_task(parent, db, hub, task)
        return
    if task.is_running():
        pause_task(parent, db, hub, task)
        return
    QMessageBox.information(parent, "Focusboard", "Start a task before pausing the clock.")


def reopen_task(parent: QWidget, db: Database, hub: Hub, task: Task | None) -> None:
    task = selected_or_warn(parent, task)
    if task is None:
        return
    if _not_a_task(parent, task):
        return
    if task.status not in (Status.DONE, Status.MISSED):
        QMessageBox.information(parent, "Focusboard", "Only finished or missed tasks can be reopened.")
        return
    db.reopen_task(task.id)  # type: ignore[arg-type]
    hub.tasks_changed.emit()


def finish_task(parent: QWidget, db: Database, hub: Hub, task: Task | None) -> None:
    task = selected_or_warn(parent, task)
    if task is None:
        return
    if _not_a_task(parent, task):
        return
    if task.status in (Status.DONE, Status.MISSED):
        QMessageBox.information(parent, "Focusboard", "This task is already closed.")
        return
    delay_reason = None
    delay_note = None
    if datetime.now() > task.due_at:
        dialog = DelayDialog(
            parent,
            heading="This task is past its deadline. Why is it delayed?",
        )
        if dialog.exec() != DelayDialog.DialogCode.Accepted:
            return
        delay_reason, delay_note = dialog.values()
    db.finish_task(task.id, delay_reason, delay_note)  # type: ignore[arg-type]
    hub.tasks_changed.emit()


def miss_task(parent: QWidget, db: Database, hub: Hub, task: Task | None) -> None:
    task = selected_or_warn(parent, task)
    if task is None:
        return
    if _not_a_task(parent, task):
        return
    if task.status in (Status.DONE, Status.MISSED):
        QMessageBox.information(parent, "Focusboard", "This task is already closed.")
        return
    dialog = DelayDialog(
        parent,
        heading="Why was this task missed?",
    )
    if dialog.exec() != DelayDialog.DialogCode.Accepted:
        return
    reason, note = dialog.values()
    db.miss_task(task.id, reason, note)  # type: ignore[arg-type]
    hub.tasks_changed.emit()


def apply_named(parent: QWidget, db: Database, hub: Hub, name: str, task: Task | None) -> None:
    handlers = {
        "start": start_task,
        "unstart": unstart_task,
        "pause": pause_task,
        "resume": resume_task,
        "reopen": reopen_task,
        "finish": finish_task,
        "missed": miss_task,
        "delete": delete_task,
    }
    handler = handlers.get(name)
    if handler:
        handler(parent, db, hub, task)


def toggle_progress(parent: QWidget, db: Database, hub: Hub, task: Task | None) -> None:
    task = selected_or_warn(parent, task)
    if task is None:
        return
    if _not_a_task(parent, task):
        return
    if task.status == Status.TODO:
        start_task(parent, db, hub, task)
    elif task.status == Status.ONGOING:
        finish_task(parent, db, hub, task)
    elif task.status in (Status.DONE, Status.MISSED):
        reopen_task(parent, db, hub, task)


def delete_task(parent: QWidget, db: Database, hub: Hub, task: Task | None) -> None:
    task = selected_or_warn(parent, task)
    if task is None:
        return
    kind = "meeting" if task.is_meeting() else "task"
    answer = QMessageBox.question(
        parent,
        f"Delete {kind}",
        f'Delete "{task.title}"? This cannot be undone.',
    )
    if answer != QMessageBox.StandardButton.Yes:
        return
    db.delete_task(task.id)  # type: ignore[arg-type]
    hub.tasks_changed.emit()
