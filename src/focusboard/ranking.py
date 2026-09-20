from __future__ import annotations

from datetime import datetime

from focusboard.models import Status, Task

PRIORITY_WEIGHT = {
    "high": 50,
    "medium": 20,
    "low": 5,
}


def importance(task: Task, now: datetime | None = None) -> float:
    """Higher is more important.

    score = priority_weight + overdue_boost + due_soon_boost + ongoing_boost
    """
    now = now or datetime.now()
    score = float(PRIORITY_WEIGHT.get(task.priority, 20))
    if task.status == Status.ONGOING:
        score += 35

    hours = (task.due_at - now).total_seconds() / 3600
    if hours < 0:
        score += 45 + min(30.0, -hours / 2)
    elif hours <= 6:
        score += 30
    elif hours <= 24:
        score += 20
    elif hours <= 72:
        score += 12
    elif hours <= 168:
        score += 5
    return score


def ranked(tasks: list[Task], now: datetime | None = None) -> list[Task]:
    now = now or datetime.now()
    return sorted(tasks, key=lambda t: (-importance(t, now), t.due_at, t.title.lower()))


def ordered_for_lists(tasks: list[Task], now: datetime | None = None) -> list[Task]:
    """Open tasks by importance, then finished/missed by when they closed."""
    now = now or datetime.now()
    open_tasks = [task for task in tasks if task.is_incomplete()]
    closed = [task for task in tasks if not task.is_incomplete()]
    closed.sort(key=lambda task: task.finished_at or task.due_at, reverse=True)
    return ranked(open_tasks, now) + closed
