from __future__ import annotations

from datetime import date, datetime, timedelta

from focusboard.models import Task
from focusboard.ranking import ordered_for_lists


def date_heading(day: date, now: datetime | None = None) -> str:
    now = now or datetime.now()
    today = now.date()
    if day == today:
        return "Today"
    if day == today + timedelta(days=1):
        return "Tomorrow"
    if day == today - timedelta(days=1):
        return "Yesterday"
    return day.strftime("%A %-d %b")


def split_overdue(tasks: list[Task], now: datetime | None = None) -> tuple[list[Task], list[Task]]:
    now = now or datetime.now()
    overdue: list[Task] = []
    rest: list[Task] = []
    for task in tasks:
        if task.is_incomplete() and task.due_at.date() < now.date():
            overdue.append(task)
        else:
            rest.append(task)
    return overdue, rest


def group_by_due_date(tasks: list[Task]) -> list[tuple[date, list[Task]]]:
    grouped: dict[date, list[Task]] = {}
    for task in tasks:
        grouped.setdefault(task.due_at.date(), []).append(task)
    rows: list[tuple[date, list[Task]]] = []
    for day in sorted(grouped):
        rows.append((day, ordered_for_lists(grouped[day])))
    return rows
