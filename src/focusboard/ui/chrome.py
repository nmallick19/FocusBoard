from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from focusboard.models import Status, Task


class SideNavButton(QPushButton):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("SideNav")
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setFlat(True)


class SidebarLabel(QLabel):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text.upper(), parent)
        self.setObjectName("SidebarLabel")


class NavButton(QPushButton):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("NavButton")
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)


class PrimaryButton(QPushButton):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("PrimaryButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class GhostButton(QPushButton):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("GhostButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)


class DangerButton(GhostButton):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("DangerButton")


class IconButton(QPushButton):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("IconButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self.setFixedSize(28, 28)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)


class EmptyHint(QLabel):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("EmptyHint")
        self.setWordWrap(True)


class SectionHeader(QWidget):
    def __init__(self, title: str, count: int = 0, hero: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SectionHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 20 if hero else 16, 0, 8)
        layout.setSpacing(8)
        self.title = QLabel(title)
        self.title.setObjectName("HeroSection" if hero else "SectionTitle")
        self.count = QLabel(str(count))
        self.count.setObjectName("CountBadge")
        layout.addWidget(self.title)
        layout.addWidget(self.count)
        layout.addStretch()

    def set_count(self, count: int) -> None:
        self.count.setText(str(count))
        self.count.setVisible(count > 0)


class DateHeader(QLabel):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("DateHeader")


class ActionBar(QFrame):
    start = Signal()
    unstart = Signal()
    reopen = Signal()
    finish = Signal()
    missed = Signal()
    edit = Signal()
    delete = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ActionBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setVisible(False)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(8)
        self.caption = QLabel("No task selected")
        self.caption.setObjectName("ActionCaption")
        self.caption.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.caption, 1)
        self.start_btn = GhostButton("Start")
        self.start_btn.setToolTip("Start (S)")
        self.unstart_btn = GhostButton("Undo Start")
        self.unstart_btn.setToolTip("Undo Start (U)")
        self.reopen_btn = GhostButton("Reopen")
        self.reopen_btn.setToolTip("Reopen (R)")
        self.finish_btn = GhostButton("Finish")
        self.finish_btn.setToolTip("Finish (F)")
        self.miss_btn = GhostButton("Missed")
        self.miss_btn.setToolTip("Missed (M)")
        self.edit_btn = GhostButton("Edit")
        self.edit_btn.setToolTip("Edit (Enter or Ctrl+E)")
        self.delete_btn = DangerButton("Delete")
        self.delete_btn.setToolTip("Delete (Del)")
        for btn in (
            self.start_btn,
            self.unstart_btn,
            self.reopen_btn,
            self.finish_btn,
            self.miss_btn,
            self.edit_btn,
            self.delete_btn,
        ):
            layout.addWidget(btn)
        self.start_btn.clicked.connect(self.start.emit)
        self.unstart_btn.clicked.connect(self.unstart.emit)
        self.reopen_btn.clicked.connect(self.reopen.emit)
        self.finish_btn.clicked.connect(self.finish.emit)
        self.miss_btn.clicked.connect(self.missed.emit)
        self.edit_btn.clicked.connect(self.edit.emit)
        self.delete_btn.clicked.connect(self.delete.emit)

    def set_task(self, task: Task | None) -> None:
        if task is None:
            self.setVisible(False)
            return
        self.setVisible(True)
        self.caption.setText(task.title)
        todo = task.status == Status.TODO
        ongoing = task.status == Status.ONGOING
        closed = task.status in (Status.DONE, Status.MISSED)
        self.start_btn.setVisible(todo)
        self.unstart_btn.setVisible(ongoing)
        self.finish_btn.setVisible(todo or ongoing)
        self.miss_btn.setVisible(todo or ongoing)
        self.reopen_btn.setVisible(closed)
        self.edit_btn.setVisible(True)
        self.delete_btn.setVisible(True)
