from __future__ import annotations

from datetime import datetime, timedelta


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    total_minutes = max(0, int(seconds // 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def format_estimated(minutes: int | None) -> str:
    if not minutes:
        return "—"
    return format_duration(minutes * 60)


def format_elapsed(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def format_time_progress(task, now: datetime | None = None) -> str:
    elapsed = task.elapsed_seconds(now)
    estimate = format_estimated(task.estimated_minutes)
    paused = bool(getattr(task, "is_paused", lambda: False)())
    suffix = " · paused" if paused else ""
    if task.estimated_minutes and elapsed is None:
        return f"{estimate} expected"
    if task.estimated_minutes and elapsed is not None:
        return f"{format_elapsed(elapsed)} / {estimate}{suffix}"
    if elapsed is not None:
        return f"{format_elapsed(elapsed)} elapsed{suffix}"
    return ""


def format_due(due_at: datetime, now: datetime | None = None) -> str:
    now = now or datetime.now()
    due_day = due_at.date()
    today = now.date()
    time_part = due_at.strftime("%H:%M")
    if due_day == today:
        prefix = "Today"
    elif due_day == today + timedelta(days=1):
        prefix = "Tomorrow"
    elif due_day == today - timedelta(days=1):
        prefix = "Yesterday"
    else:
        prefix = due_at.strftime("%a %d %b")
    return f"{prefix} {time_part}"


def due_row_parts(due_at: datetime, now: datetime | None = None) -> tuple[str, str]:
    now = now or datetime.now()
    due_day = due_at.date()
    today = now.date()
    time_part = due_at.strftime("%H:%M")
    if due_day == today:
        return "Today", time_part
    if due_day == today + timedelta(days=1):
        return "Tomorrow", time_part
    if due_day == today - timedelta(days=1):
        return "Yesterday", time_part
    return due_at.strftime("%-d %b"), time_part


def format_due_row(due_at: datetime, now: datetime | None = None) -> str:
    day, time_part = due_row_parts(due_at, now)
    return f"{day} {time_part}"


def format_countdown(seconds: float) -> str:
    total_minutes = max(0, int(abs(seconds) // 60))
    days, rem = divmod(total_minutes, 60 * 24)
    hours, minutes = divmod(rem, 60)
    if days and hours:
        return f"{days}d {hours}h"
    if days:
        return f"{days}d"
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def format_when(due_at: datetime, now: datetime | None = None) -> str:
    """Human when-label for reminders: overdue, today with time left, or coming days."""
    now = now or datetime.now()
    time_part = due_at.strftime("%H:%M")
    remaining = (due_at - now).total_seconds()
    if remaining < 0:
        late = format_countdown(-remaining)
        if due_at.date() == now.date():
            return f"Overdue {late} · {time_part}"
        return f"Overdue {late} · {format_due(due_at, now)}"
    if due_at.date() == now.date():
        return f"Today {time_part} · in {format_countdown(remaining)}"
    if due_at.date() == now.date() + timedelta(days=1):
        return f"Tomorrow {time_part}"
    days = (due_at.date() - now.date()).days
    return f"{due_at.strftime('%a %d %b')} {time_part} · in {days}d"


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat(sep=" ")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)
