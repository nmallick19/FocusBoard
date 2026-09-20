from __future__ import annotations

from datetime import datetime, time, timedelta

from PySide6.QtCore import QDate, Qt, QTime, QTimer, Signal
from PySide6.QtWidgets import (
    QCalendarWidget,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
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
    WEEKDAY_LABELS,
    Category,
    Difficulty,
    Priority,
    Repeat,
    Task,
    align_to_weekdays,
    encode_repeat_days,
    parse_repeat_days,
)


def _format_date(qdate: QDate) -> str:
    return qdate.toString("ddd d MMM yyyy")


class CalendarPopup(QFrame):
    picked = Signal(QDate)

    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("CalendarPopup")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.calendar = QCalendarWidget()
        self.calendar.setObjectName("PickerCalendar")
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        self.calendar.setFixedSize(320, 280)
        self.calendar.clicked.connect(self._choose)
        layout.addWidget(self.calendar)

    def popup(self, at: QWidget, current: QDate) -> None:
        self.calendar.setSelectedDate(current)
        self.calendar.setCurrentPage(current.year(), current.month())
        self.move(at.mapToGlobal(at.rect().bottomLeft()))
        self.show()
        self.calendar.setFocus()

    def _choose(self, qdate: QDate) -> None:
        self.picked.emit(qdate)
        self.hide()


class DatePicker(QWidget):
    """One click opens the calendar."""

    picked = Signal(QDate)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.button = QPushButton()
        self.button.setObjectName("DatePicker")
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.clicked.connect(self._open)
        layout.addWidget(self.button)
        self.setFocusProxy(self.button)
        self._date = QDate.currentDate()
        self._popup = CalendarPopup(self)
        self._popup.picked.connect(self._apply)
        self._sync()

    def date(self) -> QDate:
        return QDate(self._date)

    def setDate(self, qdate: QDate) -> None:
        self._date = QDate(qdate)
        self._sync()

    def _sync(self) -> None:
        self.button.setText(f"{_format_date(self._date)}  ▾")

    def _open(self) -> None:
        self._popup.popup(self.button, self._date)

    def _apply(self, qdate: QDate) -> None:
        self._date = QDate(qdate)
        self._sync()
        self.picked.emit(self._date)


class DateTimeRow(QWidget):
    """Date opens a calendar; time opens a clock list. After a date, time is next."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.date_picker = DatePicker()
        self.date_picker.picked.connect(self._focus_time)

        self.time_button = QPushButton()
        self.time_button.setObjectName("TimePicker")
        self.time_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.time_button.setMinimumWidth(96)
        self.time_button.clicked.connect(self._open_time)

        self._time = QTime(17, 0)
        self._popup = TimePopup(self)
        self._popup.closed.connect(self._apply_popup_time)
        self._sync_time_label()

        layout.addWidget(self.date_picker, 1)
        layout.addWidget(self.time_button, 0)

    def _focus_time(self, _date: QDate | None = None) -> None:
        QTimer.singleShot(0, self._open_time)

    def _open_time(self) -> None:
        self.time_button.setFocus()
        self._popup.popup(self.time_button, self._time)

    def _apply_popup_time(self, chosen: QTime) -> None:
        self._time = chosen
        self._sync_time_label()

    def _sync_time_label(self) -> None:
        self.time_button.setText(f"{self._time.toString('HH:mm')}  ▾")

    def set_datetime(self, due: datetime) -> None:
        self.date_picker.setDate(QDate(due.year, due.month, due.day))
        self._time = QTime(due.hour, due.minute)
        self._sync_time_label()

    def datetime_value(self) -> datetime:
        day = self.date_picker.date()
        if self._popup.isVisible():
            self._time = self._popup.current_time()
        return datetime(day.year(), day.month(), day.day(), self._time.hour(), self._time.minute())


class TimePopup(QFrame):
    """Hour and minute lists — pick a time, don't type it."""

    closed = Signal(QTime)

    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("TimePopup")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._armed = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.hours = QListWidget()
        self.hours.setObjectName("TimeList")
        self.minutes = QListWidget()
        self.minutes.setObjectName("TimeList")
        for hour in range(24):
            self.hours.addItem(f"{hour:02d}")
        for minute in (0, 15, 30, 45):
            self.minutes.addItem(f"{minute:02d}")
        for widget in (self.hours, self.minutes):
            widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            widget.setFixedSize(72, 220)
            widget.itemClicked.connect(self._picked)
            layout.addWidget(widget)

    def hideEvent(self, event) -> None:  # noqa: ANN001
        super().hideEvent(event)
        if self._armed:
            self._armed = False
            self.closed.emit(self.current_time())

    def popup(self, at: QWidget, current: QTime) -> None:
        hour_row = current.hour()
        minute_row = min(range(self.minutes.count()), key=lambda i: abs(int(self.minutes.item(i).text()) - current.minute()))
        self.hours.setCurrentRow(hour_row)
        self.minutes.setCurrentRow(minute_row)
        self.hours.scrollToItem(self.hours.item(hour_row), QListWidget.ScrollHint.PositionAtCenter)
        self.minutes.scrollToItem(self.minutes.item(minute_row), QListWidget.ScrollHint.PositionAtCenter)
        origin = at.mapToGlobal(at.rect().bottomLeft())
        self.move(origin)
        self._armed = True
        self.show()
        self.hours.setFocus()

    def current_time(self) -> QTime:
        hour_item = self.hours.currentItem()
        minute_item = self.minutes.currentItem()
        hour = int(hour_item.text()) if hour_item else 17
        minute = int(minute_item.text()) if minute_item else 0
        return QTime(hour, minute)

    def _picked(self, item: QListWidgetItem) -> None:  # noqa: ARG002
        if self.sender() is self.minutes:
            self.hide()


class WeekdayBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.buttons: list[QPushButton] = []
        for label in WEEKDAY_LABELS:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setObjectName("DayChip")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            button.setFixedHeight(32)
            layout.addWidget(button)
            self.buttons.append(button)
        layout.addStretch()

    def set_days(self, days: list[int] | tuple[int, ...]) -> None:
        selected = set(days)
        for index, button in enumerate(self.buttons):
            button.setChecked(index in selected)

    def days(self) -> list[int]:
        return [index for index, button in enumerate(self.buttons) if button.isChecked()]


class TaskDialog(QDialog):
    def __init__(
        self,
        parent=None,
        task: Task | None = None,
        default_due: datetime | None = None,
        *,
        creating: bool = False,
    ) -> None:
        super().__init__(parent)
        editing = task is not None and task.id is not None and not creating
        self.setWindowTitle("Edit task" if editing else "New task")
        self.setModal(True)
        self.setObjectName("TaskDialog")
        self.resize(520, 560)

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

        self.due_edit = DateTimeRow()

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

        self.repeat = QComboBox()
        for value, label in REPEAT_LABELS.items():
            self.repeat.addItem(label, value.value)
        self.until_label = QLabel("Until")
        self.until_edit = DatePicker()
        self.days_label = QLabel("On")
        self.days_bar = WeekdayBar()

        form.addRow("Title", self.title_edit)
        form.addRow("Due", self.due_edit)
        form.addRow("Repeats", self.repeat)
        form.addRow(self.days_label, self.days_bar)
        form.addRow(self.until_label, self.until_edit)
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

        self.repeat.currentIndexChanged.connect(self._sync_repeat)
        if task:
            self.title_edit.setText(task.title)
            self.notes_edit.setPlainText(task.notes)
            self._set_due(task.due_at)
            self._set_combo(self.priority, task.priority)
            self._set_combo(self.difficulty, task.difficulty)
            self._set_combo(self.category, task.category)
            self._set_estimate(task.estimated_minutes)
            index = self.repeat.findData(task.repeat or Repeat.NONE.value)
            self.repeat.setCurrentIndex(max(0, index))
            until = task.repeat_until or task.due_at
            self.until_edit.setDate(QDate(until.year, until.month, until.day))
            self.days_bar.set_days(parse_repeat_days(task.repeat_days))
        else:
            due = default_due or datetime.combine(datetime.now().date(), time(17, 0))
            if default_due is None and due < datetime.now():
                due = datetime.now().replace(second=0, microsecond=0)
            self._set_due(due)
            self._set_combo(self.priority, Priority.MEDIUM.value)
            self._set_combo(self.difficulty, Difficulty.MODERATE.value)
            self._set_combo(self.category, Category.WORK.value)
            self._set_estimate(30)
            self.until_edit.setDate(QDate(due.year, due.month, due.day).addMonths(3))
        self._sync_repeat()
        self.title_edit.setFocus()

    def _set_due(self, due: datetime) -> None:
        self.due_edit.set_datetime(due)

    def _set_estimate(self, minutes: int | None) -> None:
        total = minutes or 0
        hours, mins = divmod(total, 60)
        self.est_hours.setValue(hours)
        self.est_mins.setValue(mins)

    def _set_combo(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _sync_repeat(self) -> None:
        repeating = self.repeat.currentData() != Repeat.NONE.value
        on_days = self.repeat.currentData() == Repeat.ON_DAYS
        self.until_edit.setEnabled(repeating)
        self.until_edit.setVisible(repeating)
        self.until_label.setVisible(repeating)
        self.days_bar.setVisible(on_days)
        self.days_label.setVisible(on_days)
        if on_days and not self.days_bar.days():
            self.days_bar.set_days([self.due_edit.datetime_value().weekday()])

    def _accept(self) -> None:
        if not self.title_edit.text().strip():
            self.title_edit.setFocus()
            return
        if self.repeat.currentData() != Repeat.NONE.value:
            due = self.due_edit.datetime_value()
            due_date = QDate(due.year, due.month, due.day)
            if due_date > self.until_edit.date():
                self.until_edit.setFocus()
                return
            if self.repeat.currentData() == Repeat.ON_DAYS and not self.days_bar.days():
                self.days_bar.setFocus()
                return
        self.accept()

    def values(self) -> dict:
        due = self.due_edit.datetime_value()
        estimate = (self.est_hours.value() * 60 + self.est_mins.value()) or None
        repeat = self.repeat.currentData()
        until = None
        origin = None
        days = ""
        if repeat != Repeat.NONE.value:
            qdate = self.until_edit.date()
            until = datetime(qdate.year(), qdate.month(), qdate.day(), 23, 59)
            origin = due
        if repeat == Repeat.ON_DAYS:
            selected = tuple(self.days_bar.days() or [due.weekday()])
            days = encode_repeat_days(selected)
            due = align_to_weekdays(due, selected)
            origin = due
        return {
            "title": self.title_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
            "due_at": due,
            "priority": self.priority.currentData(),
            "difficulty": self.difficulty.currentData(),
            "category": self.category.currentData(),
            "estimated_minutes": estimate,
            "repeat": repeat,
            "repeat_until": until,
            "repeat_from": origin,
            "repeat_days": days,
        }


class MeetingDialog(QDialog):
    def __init__(
        self,
        parent=None,
        task: Task | None = None,
        default_due: datetime | None = None,
        *,
        creating: bool = False,
    ) -> None:
        super().__init__(parent)
        editing = task is not None and task.id is not None and not creating
        self.setWindowTitle("Edit meeting" if editing else "New meeting")
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
        self.due_edit = DateTimeRow()
        self.repeat = QComboBox()
        for value, label in REPEAT_LABELS.items():
            self.repeat.addItem(label, value.value)
        self.until_label = QLabel("Until")
        self.until_edit = DatePicker()
        self.days_label = QLabel("On")
        self.days_bar = WeekdayBar()
        self.place_kind = QComboBox()
        self.place_kind.addItem("Not set", "none")
        self.place_kind.addItem("Video link", "virtual")
        self.place_kind.addItem("Location", "in_person")
        self.place_edit = QLineEdit()
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes (optional)")
        self.notes_edit.setFixedHeight(80)

        form.addRow("Title", self.title_edit)
        form.addRow("When", self.due_edit)
        form.addRow("Repeats", self.repeat)
        form.addRow(self.days_label, self.days_bar)
        form.addRow(self.until_label, self.until_edit)
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
            self.days_bar.set_days(parse_repeat_days(task.repeat_days))
            if task.meeting_url:
                self.place_kind.setCurrentIndex(1)
                self.place_edit.setText(task.meeting_url)
            elif task.location:
                self.place_kind.setCurrentIndex(2)
                self.place_edit.setText(task.location)
            else:
                self.place_kind.setCurrentIndex(0)
        else:
            due = default_due or datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
            self._set_due(due)
            self.until_edit.setDate(QDate(due.year, due.month, due.day).addMonths(3))
            self.place_kind.setCurrentIndex(0)
        self._sync_repeat()
        self._sync_place()
        self.title_edit.setFocus()

    def _set_due(self, due: datetime) -> None:
        self.due_edit.set_datetime(due)

    def _sync_repeat(self) -> None:
        repeating = self.repeat.currentData() != Repeat.NONE.value
        on_days = self.repeat.currentData() == Repeat.ON_DAYS
        self.until_edit.setEnabled(repeating)
        self.until_edit.setVisible(repeating)
        self.until_label.setVisible(repeating)
        self.days_bar.setVisible(on_days)
        self.days_label.setVisible(on_days)
        if on_days and not self.days_bar.days():
            self.days_bar.set_days([self.due_edit.datetime_value().weekday()])

    def _sync_place(self) -> None:
        kind = self.place_kind.currentData()
        self.place_edit.setEnabled(kind != "none")
        if kind == "virtual":
            self.place_edit.setPlaceholderText("https://meet.example.com/…")
        elif kind == "in_person":
            self.place_edit.setPlaceholderText("Building, room, or address")
        else:
            self.place_edit.setPlaceholderText("Optional")

    def _due(self) -> datetime:
        return self.due_edit.datetime_value()

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
            if self.repeat.currentData() == Repeat.ON_DAYS and not self.days_bar.days():
                self.days_bar.setFocus()
                return
        self.accept()

    def values(self) -> dict:
        due = self._due()
        repeat = self.repeat.currentData()
        until = None
        origin = None
        days = ""
        if repeat != Repeat.NONE.value:
            qdate = self.until_edit.date()
            until = datetime(qdate.year(), qdate.month(), qdate.day(), 23, 59)
            origin = due
        if repeat == Repeat.ON_DAYS:
            selected = tuple(self.days_bar.days() or [due.weekday()])
            days = encode_repeat_days(selected)
            due = align_to_weekdays(due, selected)
            origin = due
        kind = self.place_kind.currentData()
        virtual = kind == "virtual"
        in_person = kind == "in_person"
        place = self.place_edit.text().strip() if kind != "none" else ""
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
            "repeat_days": days,
            "meeting_url": place if virtual else "",
            "location": place if in_person else "",
        }


def item_dialog(
    parent=None,
    task: Task | None = None,
    *,
    meeting: bool = False,
    default_due: datetime | None = None,
    creating: bool = False,
) -> TaskDialog | MeetingDialog:
    if meeting or (task is not None and task.is_meeting()):
        return MeetingDialog(parent, task=task, default_due=default_due, creating=creating)
    return TaskDialog(parent, task=task, default_due=default_due, creating=creating)
