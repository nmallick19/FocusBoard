from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from pathlib import Path

from focusboard.models import (
    LOG_KEEP,
    PAUSE_REASON_USER,
    ActivityEvent,
    ReminderBuckets,
    Status,
    Task,
    WeekStats,
    statuses_for_filters,
)
from focusboard.paths import db_path
from focusboard.ranking import ordered_for_lists, ranked
from focusboard.util import iso, parse_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'work',
    due_at TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    difficulty TEXT NOT NULL DEFAULT 'moderate',
    status TEXT NOT NULL DEFAULT 'todo',
    started_at TEXT,
    finished_at TEXT,
    estimated_minutes INTEGER,
    delay_reason TEXT,
    delay_note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    due_notified INTEGER NOT NULL DEFAULT 0,
    last_ping_at TEXT,
    worked_seconds INTEGER,
    running_since TEXT,
    pause_reason TEXT,
    repeat TEXT NOT NULL DEFAULT 'none',
    repeat_until TEXT,
    repeat_from TEXT,
    repeat_days TEXT NOT NULL DEFAULT '',
    meeting_url TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_at);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    task_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log(created_at);
"""


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            self._migrate(conn)
        self._pause_other_running()

    def running_tasks(self) -> list[Task]:
        return [task for task in self._query("WHERE status = 'ongoing'") if task.is_running()]

    def session_paused_tasks(self) -> list[Task]:
        return [
            task
            for task in self._query("WHERE status = 'ongoing'")
            if task.session_pause_explanation()
        ]

    def _pause_other_running(self, keep_id: int | None = None) -> None:
        running = self.running_tasks()
        if keep_id is None:
            running.sort(key=lambda task: task.updated_at or datetime.min, reverse=True)
            extra = running[1:]
        else:
            extra = [task for task in running if task.id != keep_id]
        for task in extra:
            if task.id is not None:
                self.pause_task(task.id)

    def _migrate(self, conn: sqlite3.Connection) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
        added_running = False
        if "worked_seconds" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN worked_seconds INTEGER")
        if "running_since" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN running_since TEXT")
            added_running = True
        if added_running:
            conn.execute(
                """
                UPDATE tasks
                SET running_since = started_at
                WHERE status = 'ongoing' AND started_at IS NOT NULL
                """
            )
        if "difficulty" not in cols:
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN difficulty TEXT NOT NULL DEFAULT 'moderate'"
            )
        if "pause_reason" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN pause_reason TEXT")
        if "repeat" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN repeat TEXT NOT NULL DEFAULT 'none'")
        if "repeat_until" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN repeat_until TEXT")
        if "repeat_from" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN repeat_from TEXT")
        if "repeat_days" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN repeat_days TEXT NOT NULL DEFAULT ''")
        if "meeting_url" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN meeting_url TEXT NOT NULL DEFAULT ''")
        if "location" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN location TEXT NOT NULL DEFAULT ''")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                source TEXT NOT NULL,
                action TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                task_id INTEGER
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log(created_at)"
        )

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            notes=row["notes"] or "",
            category=row["category"],
            due_at=parse_iso(row["due_at"]),  # type: ignore[arg-type]
            priority=row["priority"],
            difficulty=row["difficulty"] if "difficulty" in row.keys() else "moderate",
            status=row["status"],
            started_at=parse_iso(row["started_at"]),
            finished_at=parse_iso(row["finished_at"]),
            estimated_minutes=row["estimated_minutes"],
            delay_reason=row["delay_reason"],
            delay_note=row["delay_note"],
            created_at=parse_iso(row["created_at"]),
            updated_at=parse_iso(row["updated_at"]),
            due_notified=bool(row["due_notified"]),
            last_ping_at=parse_iso(row["last_ping_at"]),
            worked_seconds=row["worked_seconds"] if "worked_seconds" in row.keys() else None,
            running_since=parse_iso(row["running_since"]) if "running_since" in row.keys() else None,
            pause_reason=row["pause_reason"] if "pause_reason" in row.keys() else None,
            repeat=row["repeat"] if "repeat" in row.keys() and row["repeat"] else "none",
            repeat_until=parse_iso(row["repeat_until"]) if "repeat_until" in row.keys() else None,
            repeat_from=parse_iso(row["repeat_from"]) if "repeat_from" in row.keys() else None,
            repeat_days=row["repeat_days"] if "repeat_days" in row.keys() else "",
            meeting_url=row["meeting_url"] if "meeting_url" in row.keys() else "",
            location=row["location"] if "location" in row.keys() else "",
        )

    def _query(self, where: str = "", params: tuple = ()) -> list[Task]:
        sql = "SELECT * FROM tasks"
        if where:
            sql += f" {where}"
        sql += " ORDER BY due_at ASC"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_task(self, task_id: int) -> Task:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(f"No task with id {task_id}")
        return self._row_to_task(row)

    def create_task(
        self,
        *,
        title: str,
        notes: str = "",
        category: str = "work",
        due_at: datetime,
        priority: str = "medium",
        difficulty: str = "moderate",
        estimated_minutes: int | None = None,
        repeat: str = "none",
        repeat_until: datetime | None = None,
        repeat_from: datetime | None = None,
        repeat_days: str = "",
        meeting_url: str = "",
        location: str = "",
    ) -> Task:
        now = datetime.now().replace(microsecond=0)
        if repeat not in ("", "none"):
            repeat_from = repeat_from or due_at
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO tasks (
                    title, notes, category, due_at, priority, difficulty, status,
                    estimated_minutes, created_at, updated_at,
                    repeat, repeat_until, repeat_from, repeat_days, meeting_url, location
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title.strip(),
                    notes.strip(),
                    category,
                    iso(due_at),
                    priority,
                    difficulty,
                    Status.TODO.value,
                    estimated_minutes,
                    iso(now),
                    iso(now),
                    repeat or "none",
                    iso(repeat_until),
                    iso(repeat_from),
                    (repeat_days or "").strip(),
                    (meeting_url or "").strip(),
                    (location or "").strip(),
                ),
            )
            task_id = int(cur.lastrowid)
        return self.get_task(task_id)

    def update_task(
        self,
        task_id: int,
        *,
        title: str,
        notes: str,
        category: str,
        due_at: datetime,
        priority: str,
        difficulty: str,
        estimated_minutes: int | None,
        repeat: str = "none",
        repeat_until: datetime | None = None,
        repeat_from: datetime | None = None,
        repeat_days: str = "",
        meeting_url: str = "",
        location: str = "",
    ) -> Task:
        now = datetime.now().replace(microsecond=0)
        previous = self.get_task(task_id)
        due_changed = previous.due_at.replace(microsecond=0) != due_at.replace(microsecond=0)
        if repeat not in ("", "none"):
            repeat_from = repeat_from or previous.repeat_from or due_at
            if previous.repeat_from and due_at < previous.repeat_from:
                repeat_from = due_at
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE tasks SET
                    title = ?, notes = ?, category = ?, due_at = ?,
                    priority = ?, difficulty = ?, estimated_minutes = ?, updated_at = ?,
                    due_notified = CASE WHEN ? THEN 0 ELSE due_notified END,
                    repeat = ?, repeat_until = ?, repeat_from = ?, repeat_days = ?,
                    meeting_url = ?, location = ?
                WHERE id = ?
                """,
                (
                    title.strip(),
                    notes.strip(),
                    category,
                    iso(due_at),
                    priority,
                    difficulty,
                    estimated_minutes,
                    iso(now),
                    1 if due_changed else 0,
                    repeat or "none",
                    iso(repeat_until),
                    iso(repeat_from),
                    (repeat_days or "").strip(),
                    (meeting_url or "").strip(),
                    (location or "").strip(),
                    task_id,
                ),
            )
        return self.get_task(task_id)

    def delete_task(self, task_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def _set_fields(self, task_id: int, **fields: object) -> Task:
        fields["updated_at"] = iso(datetime.now().replace(microsecond=0))
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = tuple(fields.values()) + (task_id,)
        with self.connect() as conn:
            conn.execute(f"UPDATE tasks SET {assignments} WHERE id = ?", values)
        return self.get_task(task_id)

    def start_task(self, task_id: int) -> Task:
        task = self.get_task(task_id)
        if task.status == Status.ONGOING:
            return task
        if task.is_meeting():
            raise ValueError("Meetings cannot be started")
        if task.status not in (Status.TODO,):
            raise ValueError("Only to-do tasks can be started")
        self._pause_other_running(task_id)
        now = datetime.now().replace(microsecond=0)
        return self._set_fields(
            task_id,
            status=Status.ONGOING.value,
            started_at=iso(task.started_at or now),
            running_since=iso(now),
            worked_seconds=0,
            last_ping_at=iso(now),
            pause_reason=None,
        )

    def unstart_task(self, task_id: int) -> Task:
        task = self.get_task(task_id)
        if task.status != Status.ONGOING:
            raise ValueError("Only ongoing tasks can be returned to Next")
        return self._set_fields(
            task_id,
            status=Status.TODO.value,
            started_at=None,
            running_since=None,
            worked_seconds=None,
            last_ping_at=None,
            pause_reason=None,
        )

    def pause_task(self, task_id: int, reason: str | None = PAUSE_REASON_USER) -> Task:
        task = self.get_task(task_id)
        if task.status != Status.ONGOING:
            raise ValueError("Only ongoing tasks can be paused")
        if task.is_paused():
            return task
        now = datetime.now().replace(microsecond=0)
        elapsed = task.elapsed_seconds(now) or 0
        return self._set_fields(
            task_id,
            worked_seconds=elapsed,
            running_since=None,
            pause_reason=reason,
        )

    def resume_task(self, task_id: int) -> Task:
        task = self.get_task(task_id)
        if task.status != Status.ONGOING:
            raise ValueError("Only ongoing tasks can be resumed")
        if task.is_running():
            return task
        self._pause_other_running(task_id)
        now = datetime.now().replace(microsecond=0)
        return self._set_fields(
            task_id,
            running_since=iso(now),
            last_ping_at=iso(now),
            pause_reason=None,
            worked_seconds=task.worked_seconds if task.worked_seconds is not None else (task.elapsed_seconds(now) or 0),
        )

    def finish_task(
        self,
        task_id: int,
        delay_reason: str | None = None,
        delay_note: str | None = None,
    ) -> Task:
        task = self.get_task(task_id)
        if task.status in (Status.DONE, Status.MISSED):
            raise ValueError("Task is already closed")
        now = datetime.now().replace(microsecond=0)
        if now > task.due_at and not delay_reason:
            raise ValueError("A delay reason is required when finishing late")
        started = task.started_at or now
        elapsed = task.elapsed_seconds(now) or 0
        closed = self._set_fields(
            task_id,
            status=Status.DONE.value,
            started_at=iso(started),
            finished_at=iso(now),
            worked_seconds=elapsed,
            running_since=None,
            pause_reason=None,
            delay_reason=delay_reason,
            delay_note=(delay_note or "").strip() or None,
        )
        return self._roll_if_recurring(closed)

    def miss_task(
        self,
        task_id: int,
        delay_reason: str,
        delay_note: str | None = None,
    ) -> Task:
        task = self.get_task(task_id)
        if task.status in (Status.DONE, Status.MISSED):
            raise ValueError("Task is already closed")
        if not delay_reason:
            raise ValueError("A reason is required when marking a task missed")
        now = datetime.now().replace(microsecond=0)
        elapsed = task.elapsed_seconds(now)
        missed = self._set_fields(
            task_id,
            status=Status.MISSED.value,
            finished_at=iso(now),
            worked_seconds=elapsed,
            running_since=None,
            pause_reason=None,
            delay_reason=delay_reason,
            delay_note=(delay_note or "").strip() or None,
        )
        return self._roll_if_recurring(missed)

    def reopen_task(self, task_id: int) -> Task:
        task = self.get_task(task_id)
        if task.status not in (Status.DONE, Status.MISSED):
            raise ValueError("Only finished or missed tasks can be reopened")
        return self._set_fields(
            task_id,
            status=Status.TODO.value,
            started_at=None,
            finished_at=None,
            running_since=None,
            worked_seconds=None,
            delay_reason=None,
            delay_note=None,
            due_notified=0,
            last_ping_at=None,
            pause_reason=None,
        )

    def mark_due_notified(self, task_id: int) -> None:
        self._set_fields(task_id, due_notified=1)

    def touch_ping(self, task_id: int) -> None:
        self._set_fields(task_id, last_ping_at=iso(datetime.now().replace(microsecond=0)))

    def keep_paused(self, task_id: int) -> Task:
        return self._set_fields(task_id, pause_reason=PAUSE_REASON_USER)

    def advance_meeting(self, task_id: int) -> Task:
        task = self.get_task(task_id)
        if not task.is_meeting():
            return task
        nxt = task.next_occurrence(task.due_at)
        now = datetime.now().replace(microsecond=0)
        if nxt is None:
            return self._set_fields(
                task_id,
                status=Status.DONE.value,
                finished_at=iso(now),
                due_notified=1,
            )
        return self._set_fields(
            task_id,
            due_at=iso(nxt),
            due_notified=0,
        )

    def _roll_if_recurring(self, task: Task) -> Task:
        if not task.is_recurring() or task.id is None:
            return task
        now = datetime.now().replace(microsecond=0)
        after = task.due_at if task.due_at >= now else now
        nxt = task.next_occurrence(after)
        if nxt is None:
            return task
        return self._set_fields(
            task.id,
            status=Status.TODO.value,
            due_at=iso(nxt),
            started_at=None,
            finished_at=None,
            running_since=None,
            worked_seconds=None,
            last_ping_at=None,
            pause_reason=None,
            delay_reason=None,
            delay_note=None,
            due_notified=0,
        )

    def log_event(
        self,
        action: str,
        detail: str = "",
        *,
        source: str = "app",
        task_id: int | None = None,
    ) -> None:
        now = datetime.now().replace(microsecond=0)
        cutoff = now - LOG_KEEP
        with self.connect() as conn:
            conn.execute("DELETE FROM activity_log WHERE created_at < ?", (iso(cutoff),))
            conn.execute(
                """
                INSERT INTO activity_log (created_at, source, action, detail, task_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (iso(now), source, action, detail, task_id),
            )

    def list_activity(self, limit: int = 400) -> list[ActivityEvent]:
        cutoff = datetime.now().replace(microsecond=0) - LOG_KEEP
        with self.connect() as conn:
            conn.execute("DELETE FROM activity_log WHERE created_at < ?", (iso(cutoff),))
            rows = conn.execute(
                """
                SELECT * FROM activity_log
                WHERE created_at >= ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (iso(cutoff), limit),
            ).fetchall()
        return [
            ActivityEvent(
                id=row["id"],
                created_at=parse_iso(row["created_at"]),  # type: ignore[arg-type]
                source=row["source"],
                action=row["action"],
                detail=row["detail"] or "",
                task_id=row["task_id"],
            )
            for row in rows
        ]

    def status_filters(self) -> dict[str, bool]:
        return {
            "next": self.get_setting("filter_next", "1") != "0",
            "ongoing": self.get_setting("filter_ongoing", "1") != "0",
            "finished": self.get_setting("filter_finished", "0") != "0",
        }

    def set_status_filters(self, *, next: bool, ongoing: bool, finished: bool) -> None:
        if not next and not ongoing and not finished:
            next = True
            ongoing = True
        self.set_setting("filter_next", "1" if next else "0")
        self.set_setting("filter_ongoing", "1" if ongoing else "0")
        self.set_setting("filter_finished", "1" if finished else "0")

    def selected_statuses(self) -> tuple[str, ...]:
        filters = self.status_filters()
        return statuses_for_filters(
            next=filters["next"],
            ongoing=filters["ongoing"],
            finished=filters["finished"],
        )

    def _filter_kind(self, tasks: list[Task], *, meetings: bool = False) -> list[Task]:
        if meetings:
            return [task for task in tasks if task.is_meeting()]
        return [task for task in tasks if not task.is_meeting()]

    def list_incomplete(self) -> list[Task]:
        return self._filter_kind(self._query("WHERE status IN ('todo', 'ongoing')"))

    def list_open_meetings(self) -> list[Task]:
        return self._query("WHERE category = 'meetings' AND status IN ('todo', 'ongoing')")

    def _by_statuses(self, statuses: tuple[str, ...]) -> list[Task]:
        if not statuses:
            return []
        placeholders = ", ".join("?" * len(statuses))
        return self._query(f"WHERE status IN ({placeholders})", statuses)

    def _in_window(
        self,
        task: Task,
        start: datetime,
        end: datetime,
        *,
        include_overdue_open: bool,
    ) -> bool:
        if task.is_incomplete():
            if include_overdue_open:
                return task.due_at <= end
            return start <= task.due_at <= end
        if start <= task.due_at <= end:
            return True
        return bool(task.finished_at and start <= task.finished_at <= end)

    def list_all(
        self,
        now: datetime | None = None,
        statuses: tuple[str, ...] | None = None,
        *,
        meetings: bool = False,
    ) -> list[Task]:
        now = now or datetime.now()
        if meetings:
            pool = self.list_open_meetings()
        else:
            chosen = statuses if statuses is not None else self.selected_statuses()
            pool = self._filter_kind(self._by_statuses(chosen))
        return ordered_for_lists(pool, now)

    def list_today(
        self,
        now: datetime | None = None,
        statuses: tuple[str, ...] | None = None,
        *,
        meetings: bool = False,
    ) -> list[Task]:
        now = now or datetime.now()
        start = datetime.combine(now.date(), time.min)
        end = datetime.combine(now.date(), time.max)
        if meetings:
            pool = self.list_open_meetings()
        else:
            chosen = statuses if statuses is not None else self.selected_statuses()
            pool = self._filter_kind(self._by_statuses(chosen))
        tasks = [
            task
            for task in pool
            if self._in_window(task, start, end, include_overdue_open=True)
        ]
        return ordered_for_lists(tasks, now)

    def list_next_three_days(
        self,
        now: datetime | None = None,
        statuses: tuple[str, ...] | None = None,
        *,
        meetings: bool = False,
    ) -> list[Task]:
        now = now or datetime.now()
        start = datetime.combine(now.date() + timedelta(days=1), time.min)
        end = datetime.combine(now.date() + timedelta(days=3), time.max)
        if meetings:
            pool = self.list_open_meetings()
        else:
            chosen = statuses if statuses is not None else self.selected_statuses()
            pool = self._filter_kind(self._by_statuses(chosen))
        tasks = [
            task
            for task in pool
            if self._in_window(task, start, end, include_overdue_open=False)
        ]
        return ordered_for_lists(tasks, now)

    def list_next_seven_days(
        self,
        now: datetime | None = None,
        statuses: tuple[str, ...] | None = None,
    ) -> list[Task]:
        now = now or datetime.now()
        chosen = statuses if statuses is not None else self.selected_statuses()
        start = datetime.combine(now.date() + timedelta(days=4), time.min)
        end = datetime.combine(now.date() + timedelta(days=7), time.max)
        tasks = [
            task
            for task in self._filter_kind(self._by_statuses(chosen))
            if self._in_window(task, start, end, include_overdue_open=False)
        ]
        return ordered_for_lists(tasks, now)

    def list_later(
        self,
        now: datetime | None = None,
        statuses: tuple[str, ...] | None = None,
        *,
        meetings: bool = False,
    ) -> list[Task]:
        now = now or datetime.now()
        today_ids = {task.id for task in self.list_today(now, statuses, meetings=meetings)}
        upcoming_ids = {task.id for task in self.list_next_three_days(now, statuses, meetings=meetings)}
        skip = today_ids | upcoming_ids
        return [task for task in self.list_all(now, statuses, meetings=meetings) if task.id not in skip]

    def _reminder_open(self) -> list[Task]:
        return self.list_incomplete()

    def list_reminder_today(self, now: datetime | None = None) -> list[Task]:
        """Open work that is overdue or due today, soonest first."""
        now = now or datetime.now()
        end = datetime.combine(now.date(), time.max)
        tasks = [task for task in self._reminder_open() if task.due_at <= end]
        return sorted(tasks, key=lambda task: (task.due_at, task.title.lower()))

    def list_reminder_coming(self, now: datetime | None = None) -> list[Task]:
        """Open work due tomorrow through three days from now, soonest first."""
        now = now or datetime.now()
        start = datetime.combine(now.date() + timedelta(days=1), time.min)
        end = datetime.combine(now.date() + timedelta(days=3), time.max)
        tasks = [task for task in self._reminder_open() if start <= task.due_at <= end]
        return sorted(tasks, key=lambda task: (task.due_at, task.title.lower()))

    def list_reminders(self, now: datetime | None = None) -> ReminderBuckets:
        now = now or datetime.now()
        return ReminderBuckets(
            today=self.list_reminder_today(now),
            coming=self.list_reminder_coming(now),
        )

    def tasks_for_date(self, day: date) -> list[Task]:
        start = datetime.combine(day, time.min)
        end = datetime.combine(day, time.max)
        tasks: list[Task] = []
        seen: set[int] = set()
        for task in self._query(""):
            if task.id is not None and task.id in seen:
                continue
            if task.is_recurring():
                hits = task.occurrences_between(start, end)
                if hits:
                    tasks.append(replace(task, shown_at=hits[0]))
                    if task.id is not None:
                        seen.add(task.id)
                continue
            if start <= task.due_at <= end:
                tasks.append(task)
                if task.id is not None:
                    seen.add(task.id)
        return ranked(tasks)

    def dates_with_tasks(self, year: int, month: int) -> set[date]:
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        last = end - timedelta(seconds=1)
        dates: set[date] = set()
        for task in self._query(""):
            if task.is_recurring():
                for occ in task.occurrences_between(start, last):
                    dates.add(occ.date())
            elif start <= task.due_at <= last:
                dates.add(task.due_at.date())
        return dates

    def logbook(self, week_start: date) -> list[Task]:
        start = datetime.combine(week_start, time.min)
        end = datetime.combine(week_start + timedelta(days=7), time.min)
        tasks = self._query(
            "WHERE status IN ('done', 'missed') AND finished_at >= ? AND finished_at < ?",
            (iso(start), iso(end)),
        )
        return sorted(tasks, key=lambda t: t.finished_at or t.due_at, reverse=True)

    def week_stats(self, week_start: date) -> WeekStats:
        tasks = self.logbook(week_start)
        completed = sum(1 for task in tasks if task.status == Status.DONE)
        missed = sum(1 for task in tasks if task.status == Status.MISSED)
        seconds = sum(task.duration_seconds or 0 for task in tasks if task.status == Status.DONE)
        estimated = sum(task.estimated_minutes or 0 for task in tasks)
        return WeekStats(
            completed=completed,
            missed=missed,
            seconds=seconds,
            estimated_minutes=estimated,
        )

    def get_theme(self) -> str:
        value = self.get_setting("theme", "system")
        if value in ("system", "light", "dark"):
            return value
        return "system"

    def set_theme(self, theme: str) -> None:
        if theme not in ("system", "light", "dark"):
            theme = "system"
        self.set_setting("theme", theme)

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return str(row["value"])

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
