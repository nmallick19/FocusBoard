from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox, QPlainTextEdit, QTextEdit, QWidget

from focusboard.db import Database
from focusboard.hub import Hub
from focusboard.models import Status, Task
from focusboard.ui.delay_dialog import DelayDialog
from focusboard.ui.task_dialog import item_dialog


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


def confirm(parent: QWidget, title: str, message: str) -> bool:
    answer = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return answer == QMessageBox.StandardButton.Yes


def log_action(
    db: Database,
    hub: Hub,
    action: str,
    task: Task | None = None,
    *,
    source: str = "user",
    detail: str | None = None,
) -> None:
    text = detail if detail is not None else (task.title if task else "")
    db.log_event(action, text, source=source, task_id=task.id if task else None)
    hub.activity_changed.emit()


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
    log_action(db, hub, "start", task)
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
    if not confirm(
        parent,
        "Undo start",
        f'Undo start on "{task.title}"? Elapsed time on this run will be cleared.',
    ):
        return
    db.unstart_task(task.id)  # type: ignore[arg-type]
    log_action(db, hub, "undo start", task)
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
    if not confirm(parent, "Pause", f'Stop the clock on "{task.title}"?'):
        return
    db.pause_task(task.id)  # type: ignore[arg-type]
    log_action(db, hub, "pause", task)
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
    log_action(db, hub, "resume", task)
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
    if not confirm(parent, "Reopen", f'Reopen "{task.title}" and put it back on Next?'):
        return
    db.reopen_task(task.id)  # type: ignore[arg-type]
    log_action(db, hub, "reopen", task)
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
    extra = " The next occurrence will be scheduled." if task.is_recurring() else ""
    if not confirm(parent, "Finish", f'Mark "{task.title}" as finished?{extra}'):
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
    log_action(db, hub, "finish", task)
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
    extra = " The next occurrence will be scheduled." if task.is_recurring() else ""
    if not confirm(parent, "Missed", f'Mark "{task.title}" as missed?{extra}'):
        return
    dialog = DelayDialog(
        parent,
        heading="Why was this task missed?",
    )
    if dialog.exec() != DelayDialog.DialogCode.Accepted:
        return
    reason, note = dialog.values()
    db.miss_task(task.id, reason, note)  # type: ignore[arg-type]
    log_action(db, hub, "missed", task)
    hub.tasks_changed.emit()


def copy_item(parent: QWidget, db: Database, hub: Hub, task: Task | None) -> None:
    task = selected_or_warn(parent, task)
    if task is None:
        return
    hub.copied_task = task.as_draft()
    log_action(db, hub, "copy", task)


def paste_item(parent: QWidget, db: Database, hub: Hub) -> None:
    if _text_field_focused():
        return
    draft = hub.copied_task
    if draft is None:
        QMessageBox.information(parent, "Focusboard", "Copy a task or meeting first (Ctrl+C).")
        return
    dialog = item_dialog(parent, task=draft, creating=True)
    if dialog.exec() != dialog.DialogCode.Accepted:
        return
    created = db.create_task(**dialog.values())
    log_action(db, hub, "paste", created)
    hub.tasks_changed.emit()


def _text_field_focused() -> bool:
    widget = QApplication.focusWidget()
    return isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit))


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
        "copy": copy_item,
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
    if not confirm(parent, f"Delete {kind}", f'Delete "{task.title}"? This cannot be undone.'):
        return
    db.delete_task(task.id)  # type: ignore[arg-type]
    log_action(db, hub, "delete", task)
    hub.tasks_changed.emit()
