from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Status(StrEnum):
    TODO = "todo"
    ONGOING = "ongoing"
    DONE = "done"
    MISSED = "missed"


class Category(StrEnum):
    WORK = "work"
    PERSONAL = "personal"
    MEETINGS = "meetings"
    OTHER = "other"


class Difficulty(StrEnum):
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"
    VERY_HARD = "very_hard"


class Repeat(StrEnum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class DelayReason(StrEnum):
    UNDERESTIMATED = "underestimated"
    BLOCKED = "blocked"
    MEETING_OVERRAN = "meeting_overran"
    FORGOT = "forgot"
    TOO_TIRED = "too_tired"
    SCOPE_GREW = "scope_grew"
    OTHER = "other"


PRIORITY_LABELS = {
    Priority.HIGH: "High",
    Priority.MEDIUM: "Medium",
    Priority.LOW: "Low",
}

STATUS_LABELS = {
    Status.TODO: "To do",
    Status.ONGOING: "Ongoing",
    Status.DONE: "Done",
    Status.MISSED: "Missed",
}

CATEGORY_LABELS = {
    Category.WORK: "Work",
    Category.PERSONAL: "Personal",
    Category.MEETINGS: "Meetings",
    Category.OTHER: "Other",
}

TASK_CATEGORY_LABELS = {
    key: label for key, label in CATEGORY_LABELS.items() if key != Category.MEETINGS
}

DIFFICULTY_LABELS = {
    Difficulty.EASY: "Easy",
    Difficulty.MODERATE: "Moderate",
    Difficulty.HARD: "Hard",
    Difficulty.VERY_HARD: "Very hard",
}

REPEAT_LABELS = {
    Repeat.NONE: "Does not repeat",
    Repeat.DAILY: "Daily",
    Repeat.WEEKLY: "Weekly",
    Repeat.BIWEEKLY: "Every 2 weeks",
    Repeat.MONTHLY: "Monthly",
}

PAUSE_REASON_USER = "user"
PAUSE_REASON_CHECKIN = "checkin"
PAUSE_REASON_SCREEN_LOCK = "screen_lock"
PAUSE_REASON_DISPLAY_OFF = "display_off"
PAUSE_REASON_SLEEP = "sleep"

SESSION_PAUSE_REASONS = (
    PAUSE_REASON_SCREEN_LOCK,
    PAUSE_REASON_DISPLAY_OFF,
    PAUSE_REASON_SLEEP,
)

PAUSE_REASON_LABELS = {
    PAUSE_REASON_USER: "Paused",
    PAUSE_REASON_CHECKIN: "the 30-minute check-in",
    PAUSE_REASON_SCREEN_LOCK: "the screen was locked",
    PAUSE_REASON_DISPLAY_OFF: "the display turned off",
    PAUSE_REASON_SLEEP: "the computer went to sleep",
}

DELAY_REASON_LABELS = {
    DelayReason.UNDERESTIMATED: "Underestimated time",
    DelayReason.BLOCKED: "Blocked by someone/something",
    DelayReason.MEETING_OVERRAN: "Meeting overran",
    DelayReason.FORGOT: "Forgot",
    DelayReason.TOO_TIRED: "Too tired / low energy",
    DelayReason.SCOPE_GREW: "Scope grew",
    DelayReason.OTHER: "Other",
}

INCOMPLETE_STATUSES = (Status.TODO, Status.ONGOING)
CLOSED_STATUSES = (Status.DONE, Status.MISSED)
CHECKIN_INTERVAL = timedelta(minutes=30)
MEETING_REMIND_BEFORE = timedelta(minutes=30)

FILTER_STATUS_MAP = {
    "next": (Status.TODO.value,),
    "ongoing": (Status.ONGOING.value,),
    "finished": (Status.DONE.value, Status.MISSED.value),
}


def statuses_for_filters(*, next: bool = True, ongoing: bool = True, finished: bool = False) -> tuple[str, ...]:
    selected: list[str] = []
    if next:
        selected.extend(FILTER_STATUS_MAP["next"])
    if ongoing:
        selected.extend(FILTER_STATUS_MAP["ongoing"])
    if finished:
        selected.extend(FILTER_STATUS_MAP["finished"])
    return tuple(selected)


def _step_repeat(dt: datetime, repeat: str) -> datetime:
    if repeat == Repeat.DAILY:
        return dt + timedelta(days=1)
    if repeat == Repeat.WEEKLY:
        return dt + timedelta(weeks=1)
    if repeat == Repeat.BIWEEKLY:
        return dt + timedelta(weeks=2)
    month = dt.month - 1 + 1
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


@dataclass
class Task:
    id: int | None
    title: str
    notes: str
    category: str
    due_at: datetime
    priority: str
    status: str
    difficulty: str = "moderate"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    estimated_minutes: int | None = None
    delay_reason: str | None = None
    delay_note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    due_notified: bool = False
    last_ping_at: datetime | None = None
    worked_seconds: int | None = None
    running_since: datetime | None = None
    pause_reason: str | None = None
    repeat: str = "none"
    repeat_until: datetime | None = None
    repeat_from: datetime | None = None
    meeting_url: str = ""
    location: str = ""
    shown_at: datetime | None = None

    def is_paused(self) -> bool:
        return (
            self.status == Status.ONGOING
            and self.started_at is not None
            and self.running_since is None
            and self.worked_seconds is not None
        )

    def is_running(self) -> bool:
        return self.status == Status.ONGOING and self.started_at is not None and not self.is_paused()

    def is_meeting(self) -> bool:
        return self.category == Category.MEETINGS

    def meeting_reminder_due(self, now: datetime | None = None) -> bool:
        if not self.is_meeting() or self.due_notified:
            return False
        now = now or datetime.now()
        return self.due_at - MEETING_REMIND_BEFORE <= now < self.due_at

    def is_recurring(self) -> bool:
        return self.is_meeting() and self.repeat not in ("", Repeat.NONE)

    def meeting_place(self) -> str:
        if self.meeting_url.strip():
            return self.meeting_url.strip()
        return self.location.strip()

    def when(self) -> datetime:
        return self.shown_at or self.due_at

    def next_occurrence(self, after: datetime | None = None) -> datetime | None:
        after = after or datetime.now()
        if not self.is_recurring() or self.repeat_until is None:
            return None
        current = self.due_at
        if current > after and current.date() <= self.repeat_until.date():
            return current
        current = _step_repeat(current, self.repeat)
        guard = 0
        while current <= after and guard < 800:
            current = _step_repeat(current, self.repeat)
            guard += 1
            if current.date() > self.repeat_until.date():
                return None
        if current.date() > self.repeat_until.date():
            return None
        return current

    def occurrences_between(self, start: datetime, end: datetime) -> list[datetime]:
        if not self.is_meeting():
            return [self.due_at] if start <= self.due_at <= end else []
        if not self.is_recurring() or self.repeat_until is None:
            return [self.due_at] if start <= self.due_at <= end else []
        origin = self.repeat_from or self.due_at
        current = origin
        found: list[datetime] = []
        guard = 0
        while current < start and guard < 800:
            current = _step_repeat(current, self.repeat)
            guard += 1
            if current.date() > self.repeat_until.date():
                return []
        while current <= end and current.date() <= self.repeat_until.date() and len(found) < 400:
            if current >= start:
                found.append(current)
            current = _step_repeat(current, self.repeat)
        return found

    def checkin_due_at(self) -> datetime | None:
        if not self.is_running():
            return None
        anchor = self.last_ping_at or self.running_since or self.started_at
        if anchor is None:
            return None
        return anchor + CHECKIN_INTERVAL

    def is_checkin_due(self, now: datetime | None = None) -> bool:
        due = self.checkin_due_at()
        return bool(due and (now or datetime.now()) >= due)

    def session_pause_explanation(self) -> str | None:
        if not self.is_paused():
            return None
        if self.pause_reason in SESSION_PAUSE_REASONS:
            return PAUSE_REASON_LABELS.get(self.pause_reason)
        return None

    @property
    def duration_seconds(self) -> int | None:
        if self.worked_seconds is not None and self.status in CLOSED_STATUSES:
            return max(0, int(self.worked_seconds))
        if self.started_at and self.finished_at:
            return max(0, int((self.finished_at - self.started_at).total_seconds()))
        return None

    def is_late(self, now: datetime | None = None) -> bool:
        end = self.finished_at or now or datetime.now()
        return end > self.due_at

    def is_incomplete(self) -> bool:
        return self.status in INCOMPLETE_STATUSES

    def elapsed_seconds(self, now: datetime | None = None) -> int | None:
        now = now or datetime.now()
        if self.status == Status.ONGOING and self.started_at:
            worked = self.worked_seconds or 0
            if self.running_since is not None:
                extra = max(0, int((now - self.running_since).total_seconds()))
                return worked + extra
            if self.worked_seconds is not None:
                return max(0, worked)
            return max(0, int((now - self.started_at).total_seconds()))
        return self.duration_seconds

    def progress_ratio(self, now: datetime | None = None) -> float | None:
        if not self.estimated_minutes:
            return None
        total = self.estimated_minutes * 60
        if total <= 0:
            return None
        elapsed = self.elapsed_seconds(now)
        if elapsed is None:
            return 0.0
        return elapsed / total


@dataclass
class ReminderBuckets:
    today: list[Task]
    coming: list[Task]


@dataclass
class WeekStats:
    completed: int
    missed: int
    seconds: int
    estimated_minutes: int
