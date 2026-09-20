from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from focusboard.db import Database
from focusboard.models import Status, Task
from focusboard.ranking import importance, ranked


def _db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


def _task(**kwargs) -> Task:
    now = datetime(2026, 9, 20, 12, 0, 0)
    defaults = dict(
        id=1,
        title="Task",
        notes="",
        category="work",
        due_at=now,
        priority="medium",
        status=Status.TODO.value,
    )
    defaults.update(kwargs)
    return Task(**defaults)


def test_overdue_high_priority_ranks_first():
    now = datetime(2026, 9, 20, 12, 0, 0)
    overdue = _task(id=1, title="Overdue", due_at=now - timedelta(hours=3), priority="high")
    later = _task(id=2, title="Later", due_at=now + timedelta(days=2), priority="low")
    ordered = ranked([later, overdue], now)
    assert ordered[0].title == "Overdue"
    assert importance(overdue, now) > importance(later, now)


def test_ongoing_boosts_score():
    now = datetime(2026, 9, 20, 12, 0, 0)
    todo = _task(id=1, status=Status.TODO.value, due_at=now + timedelta(hours=4))
    ongoing = _task(id=2, title="Doing", status=Status.ONGOING.value, due_at=now + timedelta(hours=4))
    assert importance(ongoing, now) > importance(todo, now)


def test_create_start_finish_duration(tmp_path: Path):
    db = _db(tmp_path)
    due = datetime.now() + timedelta(hours=2)
    task = db.create_task(title="Write notes", due_at=due, priority="high")
    assert task.status == Status.TODO
    started = db.start_task(task.id)
    assert started.status == Status.ONGOING
    assert started.started_at is not None
    done = db.finish_task(task.id)
    assert done.status == Status.DONE
    assert done.duration_seconds is not None
    assert done.duration_seconds >= 0


def test_unstart_returns_to_todo(tmp_path: Path):
    db = _db(tmp_path)
    task = db.create_task(title="Pause me", due_at=datetime.now() + timedelta(hours=2))
    started = db.start_task(task.id)
    assert started.status == Status.ONGOING
    undone = db.unstart_task(task.id)
    assert undone.status == Status.TODO
    assert undone.started_at is None


def test_reopen_finished_and_missed(tmp_path: Path):
    db = _db(tmp_path)
    done = db.create_task(title="Done one", due_at=datetime.now() + timedelta(hours=2))
    db.start_task(done.id)
    db.finish_task(done.id)
    reopened = db.reopen_task(done.id)
    assert reopened.status == Status.TODO
    assert reopened.finished_at is None
    missed = db.create_task(title="Missed one", due_at=datetime.now() - timedelta(hours=1))
    db.miss_task(missed.id, "forgot")
    back = db.reopen_task(missed.id)
    assert back.status == Status.TODO
    assert back.delay_reason is None


def test_late_finish_requires_reason(tmp_path: Path):
    db = _db(tmp_path)
    task = db.create_task(title="Late", due_at=datetime.now() - timedelta(hours=1))
    try:
        db.finish_task(task.id)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    done = db.finish_task(task.id, delay_reason="forgot", delay_note="slipped")
    assert done.status == Status.DONE
    assert done.delay_reason == "forgot"


def test_miss_and_logbook(tmp_path: Path):
    db = _db(tmp_path)
    task = db.create_task(title="Missed call", due_at=datetime.now() - timedelta(hours=1))
    missed = db.miss_task(task.id, "blocked", "waiting on review")
    assert missed.status == Status.MISSED
    from datetime import date

    monday = date.today() - timedelta(days=date.today().weekday())
    rows = db.logbook(monday)
    assert any(row.title == "Missed call" for row in rows)
    stats = db.week_stats(monday)
    assert stats.missed == 1


def test_today_includes_overdue(tmp_path: Path):
    db = _db(tmp_path)
    db.create_task(title="Yesterday", due_at=datetime.now() - timedelta(days=1))
    titles = [t.title for t in db.list_today()]
    assert "Yesterday" in titles


def test_all_tasks_includes_far_future(tmp_path: Path):
    db = _db(tmp_path)
    db.create_task(title="Soon", due_at=datetime.now() + timedelta(hours=2))
    db.create_task(title="Later", due_at=datetime.now() + timedelta(days=30))
    titles = [t.title for t in db.list_all()]
    assert "Soon" in titles
    assert "Later" in titles
    assert "Later" not in [t.title for t in db.list_next_seven_days()]


def test_status_filters_hide_and_show_finished(tmp_path: Path):
    db = _db(tmp_path)
    open_task = db.create_task(title="Open", due_at=datetime.now() + timedelta(hours=1))
    done = db.create_task(title="Done today", due_at=datetime.now() + timedelta(hours=2))
    db.start_task(done.id)
    db.finish_task(done.id)
    db.set_status_filters(next=True, ongoing=True, finished=False)
    titles = [t.title for t in db.list_all()]
    assert "Open" in titles
    assert "Done today" not in titles
    db.set_status_filters(next=True, ongoing=True, finished=True)
    titles = [t.title for t in db.list_all()]
    assert "Open" in titles
    assert "Done today" in titles
    assert open_task.status == "todo"


def test_exclusive_time_windows(tmp_path: Path):
    db = _db(tmp_path)
    today = db.create_task(title="Due today", due_at=datetime.now() + timedelta(hours=1))
    in_three = db.create_task(title="Due in 2 days", due_at=datetime.now() + timedelta(days=2))
    in_seven = db.create_task(title="Due in 5 days", due_at=datetime.now() + timedelta(days=5))
    today_titles = [t.title for t in db.list_today()]
    three_titles = [t.title for t in db.list_next_three_days()]
    seven_titles = [t.title for t in db.list_next_seven_days()]
    assert today.title in today_titles
    assert today.title not in three_titles
    assert today.title not in seven_titles
    assert in_three.title in three_titles
    assert in_three.title not in today_titles
    assert in_three.title not in seven_titles
    assert in_seven.title in seven_titles
    assert in_seven.title not in three_titles
    assert in_seven.title not in today_titles


def test_empty_filters_snap_back_to_open_work(tmp_path: Path):
    db = _db(tmp_path)
    db.set_status_filters(next=False, ongoing=False, finished=False)
    filters = db.status_filters()
    assert filters["next"] is True
    assert filters["ongoing"] is True
    assert filters["finished"] is False


def test_editing_due_time_resets_due_notification(tmp_path: Path):
    db = _db(tmp_path)
    task = db.create_task(title="Ping me", due_at=datetime.now() + timedelta(hours=1))
    db.mark_due_notified(task.id)
    assert db.get_task(task.id).due_notified is True
    later = datetime.now() + timedelta(hours=3)
    updated = db.update_task(
        task.id,
        title=task.title,
        notes=task.notes,
        category=task.category,
        due_at=later,
        priority=task.priority,
        difficulty=task.difficulty,
        estimated_minutes=task.estimated_minutes,
    )
    assert updated.due_notified is False


def test_reminders_split_today_and_coming(tmp_path: Path):
    db = _db(tmp_path)
    db.create_task(title="Now", due_at=datetime.now() + timedelta(hours=1))
    db.create_task(title="Soon", due_at=datetime.now() + timedelta(days=2))
    db.create_task(title="Later week", due_at=datetime.now() + timedelta(days=5))
    buckets = db.list_reminders()
    assert "Now" in [t.title for t in buckets.today]
    assert "Soon" in [t.title for t in buckets.coming]
    assert "Later week" not in [t.title for t in buckets.today]
    assert "Later week" not in [t.title for t in buckets.coming]


def test_seven_days_is_days_four_through_seven(tmp_path: Path):
    db = _db(tmp_path)
    inside = datetime.now() + timedelta(days=6, hours=12)
    outside = datetime.now() + timedelta(days=8)
    db.create_task(title="Inside 7 days", due_at=inside)
    db.create_task(title="Outside 7 days", due_at=outside)
    seven = [t.title for t in db.list_next_seven_days()]
    assert "Inside 7 days" in seven
    assert "Outside 7 days" not in seven


def test_theme_defaults_to_system(tmp_path: Path):
    db = _db(tmp_path)
    assert db.get_theme() == "system"
    db.set_theme("dark")
    assert db.get_theme() == "dark"
    db.set_theme("not-a-theme")
    assert db.get_theme() == "system"


def test_later_excludes_today_and_upcoming(tmp_path: Path):
    db = _db(tmp_path)
    db.create_task(title="Due today", due_at=datetime.now() + timedelta(hours=1))
    db.create_task(title="Due in 2 days", due_at=datetime.now() + timedelta(days=2))
    db.create_task(title="Due in 5 days", due_at=datetime.now() + timedelta(days=5))
    db.create_task(title="Next month", due_at=datetime.now() + timedelta(days=30))
    later = [t.title for t in db.list_later()]
    assert "Due today" not in later
    assert "Due in 2 days" not in later
    assert "Due in 5 days" in later
    assert "Next month" in later


def test_view_from_filters_maps_saved_status_flags():
    from focusboard.ui.sidebar import view_from_filters

    assert view_from_filters({"next": True, "ongoing": True, "finished": False}) == "all"
    assert view_from_filters({"next": True, "ongoing": False, "finished": False}) == "next"
    assert view_from_filters({"next": False, "ongoing": True, "finished": False}) == "ongoing"
    assert view_from_filters({"next": False, "ongoing": False, "finished": True}) == "finished"


def test_format_due_row_uses_relative_days():
    from focusboard.util import format_due_row

    now = datetime(2026, 9, 20, 12, 0, 0)
    assert format_due_row(now, now) == "Today 12:00"
    assert format_due_row(now + timedelta(days=1), now) == "Tomorrow 12:00"
    assert format_due_row(now + timedelta(days=3), now) == "23 Sep 12:00"
    from focusboard.util import due_row_parts

    assert due_row_parts(now, now) == ("Today", "12:00")
    assert due_row_parts(now + timedelta(days=1), now) == ("Tomorrow", "12:00")


def test_progress_ratio_uses_elapsed_against_estimate():
    now = datetime(2026, 9, 20, 12, 0, 0)
    waiting = _task(estimated_minutes=30, status=Status.TODO.value, due_at=now)
    assert waiting.progress_ratio(now) == 0.0
    running = _task(
        estimated_minutes=10,
        status=Status.ONGOING.value,
        due_at=now,
        started_at=now - timedelta(minutes=5),
    )
    assert running.elapsed_seconds(now) == 5 * 60
    assert running.progress_ratio(now) == 0.5
    overtime = _task(
        estimated_minutes=10,
        status=Status.ONGOING.value,
        due_at=now,
        started_at=now - timedelta(minutes=20),
    )
    assert overtime.progress_ratio(now) == 2.0
    none = _task(estimated_minutes=None, status=Status.TODO.value, due_at=now)
    assert none.progress_ratio(now) is None


def test_format_time_progress_shows_expected_then_elapsed():
    from focusboard.util import format_time_progress

    now = datetime(2026, 9, 20, 12, 0, 0)
    waiting = _task(estimated_minutes=30, status=Status.TODO.value, due_at=now)
    assert format_time_progress(waiting, now) == "30m expected"
    running = _task(
        estimated_minutes=10,
        status=Status.ONGOING.value,
        due_at=now,
        started_at=now - timedelta(minutes=5, seconds=12),
    )
    assert format_time_progress(running, now) == "5m 12s / 10m"
    done = _task(
        estimated_minutes=10,
        status=Status.DONE.value,
        due_at=now,
        started_at=now - timedelta(minutes=8),
        finished_at=now - timedelta(minutes=3),
    )
    assert format_time_progress(done, now) == "5m 00s / 10m"


def test_pause_freezes_elapsed_and_keeps_overrun(tmp_path: Path):
    from focusboard.util import format_time_progress, iso

    db = _db(tmp_path)
    due = datetime.now() + timedelta(hours=2)
    task = db.create_task(title="Write notes", due_at=due, estimated_minutes=10)
    db.start_task(task.id)
    started = datetime.now().replace(microsecond=0) - timedelta(minutes=6)
    db._set_fields(task.id, started_at=iso(started), running_since=iso(started), worked_seconds=0)
    running = db.get_task(task.id)
    now = datetime.now()
    before = running.elapsed_seconds(now)
    assert before >= 6 * 60
    paused = db.pause_task(task.id)
    frozen = paused.elapsed_seconds(now)
    assert paused.is_paused()
    assert not paused.is_running()
    assert frozen == paused.worked_seconds
    later = now + timedelta(hours=1)
    assert paused.elapsed_seconds(later) == frozen
    fetched = db.get_task(task.id)
    assert fetched.elapsed_seconds(later) == frozen

    overtime = db.create_task(title="Overrun me", due_at=due, estimated_minutes=10)
    db.start_task(overtime.id)
    long_start = datetime.now().replace(microsecond=0) - timedelta(minutes=22)
    db._set_fields(
        overtime.id,
        started_at=iso(long_start),
        running_since=iso(long_start),
        worked_seconds=0,
    )
    over = db.pause_task(overtime.id)
    assert over.progress_ratio() > 1
    assert over.elapsed_seconds() >= 22 * 60
    assert "paused" in format_time_progress(over)


def test_resume_continues_from_frozen_time(tmp_path: Path):
    from focusboard.util import iso

    db = _db(tmp_path)
    due = datetime.now() + timedelta(hours=2)
    task = db.create_task(title="Keep going", due_at=due, estimated_minutes=30)
    db.start_task(task.id)
    started = datetime.now().replace(microsecond=0) - timedelta(minutes=8)
    db._set_fields(task.id, started_at=iso(started), running_since=iso(started), worked_seconds=0)
    paused = db.pause_task(task.id)
    frozen = paused.worked_seconds or 0
    resumed = db.resume_task(task.id)
    resume_at = datetime.now().replace(microsecond=0) - timedelta(minutes=3)
    db._set_fields(resumed.id, running_since=iso(resume_at))
    live = db.get_task(task.id)
    now = datetime.now()
    elapsed = live.elapsed_seconds(now)
    assert live.is_running()
    assert elapsed >= frozen + 3 * 60
    assert elapsed < frozen + 3 * 60 + 5

    finished = db.finish_task(task.id)
    assert finished.duration_seconds == finished.worked_seconds
    assert finished.duration_seconds is not None
    assert finished.duration_seconds >= frozen + 3 * 60


def test_difficulty_is_stored_and_updated(tmp_path: Path):
    db = _db(tmp_path)
    due = datetime.now() + timedelta(hours=2)
    created = db.create_task(title="Hard one", due_at=due, difficulty="hard")
    assert created.difficulty == "hard"
    updated = db.update_task(
        created.id,
        title=created.title,
        notes=created.notes,
        category=created.category,
        due_at=created.due_at,
        priority=created.priority,
        difficulty="very_hard",
        estimated_minutes=created.estimated_minutes,
    )
    assert updated.difficulty == "very_hard"
    defaulted = db.create_task(title="Plain", due_at=due)
    assert defaulted.difficulty == "moderate"


def test_meetings_category_is_stored(tmp_path: Path):
    db = _db(tmp_path)
    task = db.create_task(
        title="Sprint planning",
        due_at=datetime.now() + timedelta(hours=2),
        category="meetings",
    )
    assert task.category == "meetings"
    from focusboard.models import CATEGORY_LABELS

    assert CATEGORY_LABELS["meetings"] == "Meetings"


def test_starting_or_resuming_pauses_the_running_task(tmp_path: Path):
    db = _db(tmp_path)
    due = datetime.now() + timedelta(hours=2)
    first = db.create_task(title="First", due_at=due, estimated_minutes=20)
    second = db.create_task(title="Second", due_at=due, estimated_minutes=20)
    third = db.create_task(title="Third", due_at=due, estimated_minutes=20)
    db.start_task(first.id)
    assert db.get_task(first.id).is_running()
    db.start_task(second.id)
    first = db.get_task(first.id)
    second = db.get_task(second.id)
    assert first.is_paused()
    assert first.worked_seconds is not None
    assert second.is_running()
    assert len(db.running_tasks()) == 1

    db.pause_task(second.id)
    db.start_task(third.id)
    db.resume_task(first.id)
    first = db.get_task(first.id)
    second = db.get_task(second.id)
    third = db.get_task(third.id)
    assert first.is_running()
    assert second.is_paused()
    assert third.is_paused()
    assert [task.id for task in db.running_tasks()] == [first.id]


def test_checkin_is_due_after_thirty_minutes():
    now = datetime(2026, 9, 20, 12, 0, 0)
    running = _task(
        status=Status.ONGOING.value,
        started_at=now - timedelta(minutes=10),
        running_since=now - timedelta(minutes=10),
        last_ping_at=now - timedelta(minutes=10),
        worked_seconds=0,
    )
    assert running.is_checkin_due(now) is False
    assert running.is_checkin_due(now + timedelta(minutes=30)) is True
    paused = _task(
        status=Status.ONGOING.value,
        started_at=now - timedelta(minutes=40),
        running_since=None,
        worked_seconds=20 * 60,
        last_ping_at=now - timedelta(minutes=40),
    )
    assert paused.is_checkin_due(now) is False


def test_screen_lock_pause_keeps_progress_and_reason(tmp_path: Path):
    from focusboard.models import PAUSE_REASON_SCREEN_LOCK
    from focusboard.util import iso

    db = _db(tmp_path)
    due = datetime.now() + timedelta(hours=2)
    task = db.create_task(title="Deep work", due_at=due, estimated_minutes=60)
    db.start_task(task.id)
    started = datetime.now().replace(microsecond=0) - timedelta(minutes=12)
    db._set_fields(task.id, started_at=iso(started), running_since=iso(started), last_ping_at=iso(started))
    paused = db.pause_task(task.id, PAUSE_REASON_SCREEN_LOCK)
    assert paused.is_paused()
    assert paused.pause_reason == PAUSE_REASON_SCREEN_LOCK
    assert paused.elapsed_seconds() >= 12 * 60
    assert paused.session_pause_explanation() == "the screen was locked"
    assert db.session_paused_tasks()[0].id == paused.id
    kept = db.keep_paused(paused.id)
    assert kept.pause_reason == "user"
    assert kept.session_pause_explanation() is None


def test_meetings_stay_out_of_task_lists(tmp_path: Path):
    db = _db(tmp_path)
    now = datetime.now().replace(microsecond=0)
    db.create_task(title="Write notes", due_at=now + timedelta(hours=1))
    meeting = db.create_task(
        title="Standup",
        due_at=now + timedelta(hours=2),
        category="meetings",
        meeting_url="https://meet.example/standup",
    )
    assert meeting.is_meeting()
    assert [task.title for task in db.list_today()] == ["Write notes"]
    assert [task.title for task in db.list_incomplete()] == ["Write notes"]
    assert [task.title for task in db.list_today(meetings=True)] == ["Standup"]
    try:
        db.start_task(meeting.id)
        raise AssertionError("meetings must not start")
    except ValueError:
        pass


def test_recurring_meeting_maps_calendar_and_rolls_forward(tmp_path: Path):
    db = _db(tmp_path)
    start = datetime(2026, 9, 21, 10, 0, 0)
    until = datetime(2026, 10, 12, 23, 59, 0)
    meeting = db.create_task(
        title="Weekly sync",
        due_at=start,
        category="meetings",
        repeat="weekly",
        repeat_until=until,
        location="Room 4",
    )
    assert meeting.is_recurring()
    assert meeting.repeat_from == start
    assert meeting.meeting_place() == "Room 4"
    assert meeting.next_occurrence(start) == start + timedelta(weeks=1)
    dates = db.dates_with_tasks(2026, 9)
    assert date(2026, 9, 21) in dates
    assert date(2026, 9, 28) in dates
    day = db.tasks_for_date(date(2026, 9, 28))
    assert [task.title for task in day] == ["Weekly sync"]
    assert day[0].when() == datetime(2026, 9, 28, 10, 0, 0)
    assert day[0].due_at == start
    now = datetime(2026, 9, 21, 12, 0, 0)
    assert [task.title for task in db.list_today(now, meetings=True)] == ["Weekly sync"]
    later_titles = [task.title for task in db.list_next_three_days(now, meetings=True)]
    assert later_titles == []
    rolled = db.advance_meeting(meeting.id)
    assert rolled.due_at == datetime(2026, 9, 28, 10, 0, 0)
    assert rolled.due_notified is False
    last = db.advance_meeting(meeting.id)
    last = db.advance_meeting(last.id)
    last = db.advance_meeting(last.id)
    assert last.status == Status.DONE
    assert last.due_at == datetime(2026, 10, 12, 10, 0, 0)


def test_meeting_reminder_window():
    now = datetime(2026, 9, 20, 12, 0, 0)
    meeting = _task(
        category="meetings",
        due_at=now + timedelta(minutes=30),
        meeting_url="https://meet.example/x",
    )
    assert meeting.meeting_reminder_due(now) is True
    assert meeting.meeting_reminder_due(now - timedelta(minutes=1)) is False
    assert meeting.meeting_reminder_due(now + timedelta(minutes=31)) is False
    meeting.due_notified = True
    assert meeting.meeting_reminder_due(now) is False
    one_off = _task(category="meetings", due_at=now + timedelta(hours=2))
    assert one_off.next_occurrence(now) is None
