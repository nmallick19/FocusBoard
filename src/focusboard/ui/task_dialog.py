from __future__ import annotations

from datetime import datetime, time, timedelta

from PySide6.QtCore import QDate, QDateTime, QTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from focusboard.models import (
    DIFFICULTY_LABELS,
    PRIORITY_LABELS,
    REPEAT_LABELS,
    TASK_CATEGORY_LABELS,
    Category,
    Difficulty,
    Priority,
    Repeat,
    Task,
)


class TaskDialog(QDialog):
    def __init__(
        self,
        parent=None,
        task: Task | None = None,
        default_due: datetime | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit task" if task else "New task")
        self.setModal(True)
        self.setObjectName("TaskDialog")
        self.resize(520, 460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(16)
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("What needs to be done?")
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        self.notes_edit.setFixedHeight(90)

        self.due_edit = QDateTimeEdit()
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDisplayFormat("yyyy-MM-dd HH:mm")

        self.priority = QComboBox()
        for value, label in PRIORITY_LABELS.items():
            self.priority.addItem(label, value.value)

        self.category = QComboBox()
        for value, label in TASK_CATEGORY_LABELS.items():
            self.category.addItem(label, value.value)

        self.difficulty = QComboBox()
        for value, label in DIFFICULTY_LABELS.items():
            self.difficulty.addItem(label, value.value)

        self.est_hours = QSpinBox()
        self.est_hours.setRange(0, 12)
        self.est_hours.setSuffix(" h")
        self.est_mins = QSpinBox()
        self.est_mins.setRange(0, 59)
        self.est_mins.setSuffix(" min")
        estimate_row = QWidget()
        estimate_layout = QHBoxLayout(estimate_row)
        estimate_layout.setContentsMargins(0, 0, 0, 0)
        estimate_layout.setSpacing(8)
        estimate_layout.addWidget(self.est_hours)
        estimate_layout.addWidget(self.est_mins)
        estimate_layout.addStretch()

        form.addRow("Title", self.title_edit)
        form.addRow("Due", self.due_edit)
        form.addRow("Priority", self.priority)
        form.addRow("Difficulty", self.difficulty)
        form.addRow("Category", self.category)
        form.addRow("Expected time", estimate_row)
        form.addRow("Notes", self.notes_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if task:
            self.title_edit.setText(task.title)
            self.notes_edit.setPlainText(task.notes)
            self._set_due(task.due_at)
            self._set_combo(self.priority, task.priority)
            self._set_combo(self.difficulty, task.difficulty)
            self._set_combo(self.category, task.category)
            self._set_estimate(task.estimated_minutes)
        else:
            due = default_due or datetime.combine(datetime.now().date(), time(17, 0))
            if default_due is None and due < datetime.now():
                due = datetime.now().replace(second=0, microsecond=0)
            self._set_due(due)
            self._set_combo(self.priority, Priority.MEDIUM.value)
            self._set_combo(self.difficulty, Difficulty.MODERATE.value)
            self._set_combo(self.category, Category.WORK.value)
            self._set_estimate(30)

        self.title_edit.setFocus()

    def _set_due(self, due: datetime) -> None:
        qdt = QDateTime(
            QDate(due.year, due.month, due.day),
            QTime(due.hour, due.minute, 0),
        )
        self.due_edit.setDateTime(qdt)

    def _set_estimate(self, minutes: int | None) -> None:
        total = minutes or 0
        hours, mins = divmod(total, 60)
        self.est_hours.setValue(hours)
        self.est_mins.setValue(mins)

    def _set_combo(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _accept(self) -> None:
        if not self.title_edit.text().strip():
            self.title_edit.setFocus()
            return
        self.accept()

    def values(self) -> dict:
        qdt = self.due_edit.dateTime()
        due = datetime(
            qdt.date().year(),
            qdt.date().month(),
            qdt.date().day(),
            qdt.time().hour(),
            qdt.time().minute(),
        )
        estimate = (self.est_hours.value() * 60 + self.est_mins.value()) or None
        return {
            "title": self.title_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
            "due_at": due,
            "priority": self.priority.currentData(),
            "difficulty": self.difficulty.currentData(),
            "category": self.category.currentData(),
            "estimated_minutes": estimate,
        }


class MeetingDialog(QDialog):
    def __init__(
        self,
        parent=None,
        task: Task | None = None,
        default_due: datetime | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit meeting" if task else "New meeting")
        self.setModal(True)
        self.setObjectName("TaskDialog")
        self.resize(500, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(16)
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Meeting name")
        self.due_edit = QDateTimeEdit()
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.repeat = QComboBox()
        for value, label in REPEAT_LABELS.items():
            self.repeat.addItem(label, value.value)
        self.until_edit = QDateEdit()
        self.until_edit.setCalendarPopup(True)
        self.until_edit.setDisplayFormat("yyyy-MM-dd")
        self.place_kind = QComboBox()
        self.place_kind.addItem("Video link", "virtual")
        self.place_kind.addItem("Location", "in_person")
        self.place_edit = QLineEdit()
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        self.notes_edit.setFixedHeight(80)

        form.addRow("Title", self.title_edit)
        form.addRow("Next date", self.due_edit)
        form.addRow("Repeats", self.repeat)
        form.addRow("Until", self.until_edit)
        form.addRow("Where", self.place_kind)
        form.addRow("Details", self.place_edit)
        form.addRow("Notes", self.notes_edit)
        layout.addLayout(form)
        hint = QLabel("Reminder 30 minutes before, only if you're logged in.")
        hint.setObjectName("MetaMuted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.repeat.currentIndexChanged.connect(self._sync_repeat)
        self.place_kind.currentIndexChanged.connect(self._sync_place)
        if task:
            self.title_edit.setText(task.title)
            self.notes_edit.setPlainText(task.notes)
            self._set_due(task.due_at)
            index = self.repeat.findData(task.repeat or Repeat.NONE.value)
            self.repeat.setCurrentIndex(max(0, index))
            until = task.repeat_until or task.due_at
            self.until_edit.setDate(QDate(until.year, until.month, until.day))
            if task.meeting_url:
                self.place_kind.setCurrentIndex(0)
                self.place_edit.setText(task.meeting_url)
            else:
                self.place_kind.setCurrentIndex(1)
                self.place_edit.setText(task.location)
        else:
            due = default_due or datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
            self._set_due(due)
            self.until_edit.setDate(QDate(due.year, due.month, due.day).addMonths(3))
            self.place_kind.setCurrentIndex(0)
        self._sync_repeat()
        self._sync_place()
        self.title_edit.setFocus()

    def _set_due(self, due: datetime) -> None:
        qdt = QDateTime(
            QDate(due.year, due.month, due.day),
            QTime(due.hour, due.minute, 0),
        )
        self.due_edit.setDateTime(qdt)

    def _sync_repeat(self) -> None:
        repeating = self.repeat.currentData() != Repeat.NONE.value
        self.until_edit.setEnabled(repeating)

    def _sync_place(self) -> None:
        virtual = self.place_kind.currentData() == "virtual"
        self.place_edit.setPlaceholderText(
            "https://meet.example.com/…" if virtual else "Building, room, or address"
        )

    def _due(self) -> datetime:
        qdt = self.due_edit.dateTime()
        return datetime(
            qdt.date().year(),
            qdt.date().month(),
            qdt.date().day(),
            qdt.time().hour(),
            qdt.time().minute(),
        )

    def _accept(self) -> None:
        if not self.title_edit.text().strip():
            self.title_edit.setFocus()
            return
        due = self._due()
        if self.repeat.currentData() != Repeat.NONE.value:
            until = self.until_edit.date()
            if QDate(due.year, due.month, due.day) > until:
                self.until_edit.setFocus()
                return
        if not self.place_edit.text().strip():
            self.place_edit.setFocus()
            return
        self.accept()

    def values(self) -> dict:
        due = self._due()
        repeat = self.repeat.currentData()
        until = None
        origin = None
        if repeat != Repeat.NONE.value:
            qdate = self.until_edit.date()
            until = datetime(qdate.year(), qdate.month(), qdate.day(), 23, 59)
            origin = due
        virtual = self.place_kind.currentData() == "virtual"
        place = self.place_edit.text().strip()
        return {
            "title": self.title_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
            "due_at": due,
            "priority": Priority.MEDIUM.value,
            "difficulty": Difficulty.MODERATE.value,
            "category": Category.MEETINGS.value,
            "estimated_minutes": None,
            "repeat": repeat,
            "repeat_until": until,
            "repeat_from": origin,
            "meeting_url": place if virtual else "",
            "location": "" if virtual else place,
        }


def item_dialog(
    parent=None,
    task: Task | None = None,
    *,
    meeting: bool = False,
    default_due: datetime | None = None,
) -> TaskDialog | MeetingDialog:
    if meeting or (task is not None and task.is_meeting()):
        return MeetingDialog(parent, task=task, default_due=default_due)
    return TaskDialog(parent, task=task, default_due=default_due)
