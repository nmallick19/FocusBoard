from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from focusboard.db import Database
from focusboard.hub import Hub
from focusboard.ui import actions
from focusboard.ui.calendar_page import CalendarPage
from focusboard.ui.chrome import NavButton, PrimaryButton
from focusboard.ui.focus_page import FocusPage
from focusboard.ui.logbook_page import LogbookPage
from focusboard.ui.logger_page import LoggerPage


class MainWindow(QMainWindow):
    def __init__(self, db: Database, hub: Hub, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.hub = hub
        self.setWindowTitle("Focusboard")
        self.resize(1280, 800)
        self.setMinimumSize(880, 560)

        shell = QWidget()
        shell.setObjectName("AppShell")
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("AppHeader")
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(24, 12, 24, 12)
        header_row.setSpacing(8)
        brand = QLabel("Focusboard")
        brand.setObjectName("AppBrand")
        header_row.addWidget(brand)
        header_row.addSpacing(16)

        self.focus_nav = NavButton("Focus")
        self.calendar_nav = NavButton("Calendar")
        self.logbook_nav = NavButton("Logbook")
        self.logger_nav = NavButton("Logger")
        self.focus_nav.setChecked(True)
        for button in (self.focus_nav, self.calendar_nav, self.logbook_nav, self.logger_nav):
            header_row.addWidget(button)
        header_row.addStretch()
        self.header_new = PrimaryButton("+ New task")
        self.header_new.setToolTip("New task (Ctrl+N)")
        header_row.addWidget(self.header_new)
        layout.addWidget(header)

        self.pages = QStackedWidget()
        self.focus_page = FocusPage(db, hub)
        self.calendar_page = CalendarPage(db, hub)
        self.logbook_page = LogbookPage(db, hub)
        self.logger_page = LoggerPage(db, hub)
        self.pages.addWidget(self.focus_page)
        self.pages.addWidget(self.calendar_page)
        self.pages.addWidget(self.logbook_page)
        self.pages.addWidget(self.logger_page)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(shell)

        self.focus_nav.clicked.connect(lambda: self.show_page(0))
        self.calendar_nav.clicked.connect(lambda: self.show_page(1))
        self.logbook_nav.clicked.connect(lambda: self.show_page(2))
        self.logger_nav.clicked.connect(lambda: self.show_page(3))
        self.header_new.clicked.connect(self.add_task)

        self._bind_shortcuts()

        hub.tasks_changed.connect(self.refresh)
        hub.activity_changed.connect(self.logger_page.refresh)
        hub.show_main.connect(self.reveal)
        hub.show_main_task.connect(self.reveal_task)
        self.focus_page.sidebar.project_changed.connect(lambda _name: self._sync_new_button())
        self._sync_new_button()

    @property
    def tabs(self):
        return self.pages

    def show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        buttons = (self.focus_nav, self.calendar_nav, self.logbook_nav, self.logger_nav)
        for i, button in enumerate(buttons):
            button.setChecked(i == index)
        self.header_new.setVisible(index == 0)
        buttons[index].setFocus()
        self._sync_new_button()

    def _sync_new_button(self) -> None:
        meetings = (
            self.pages.currentWidget() is self.focus_page and self.focus_page.showing_meetings()
        )
        if meetings:
            self.header_new.setText("+ New meeting")
            self.header_new.setToolTip("New meeting (Ctrl+N)")
        else:
            self.header_new.setText("+ New task")
            self.header_new.setToolTip("New task (Ctrl+N)")

    def _bind_shortcuts(self) -> None:
        new_action = QAction("New task", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.add_task)
        self.addAction(new_action)

        window_bindings = {
            "Ctrl+1": lambda: self.show_page(0),
            "Ctrl+2": lambda: self.show_page(1),
            "Ctrl+3": lambda: self.show_page(2),
            "Ctrl+4": lambda: self.show_page(3),
            "Ctrl+E": self.edit_task,
            "Ctrl+C": self.copy_task,
            "Ctrl+V": self.paste_task,
            "Delete": self.delete_task,
            "S": self.start_task,
            "P": self.toggle_pause,
            "U": self.unstart_task,
            "R": self.reopen_task,
            "F": self.finish_task,
            "M": self.miss_task,
            "A": lambda: self._set_filter("all"),
            "N": lambda: self._set_filter("next"),
            "O": lambda: self._set_filter("ongoing"),
            "D": lambda: self._set_filter("finished"),
            "Escape": self.clear_selection,
            "Ctrl+B": self._toggle_sidebar,
        }
        for sequence, callback in window_bindings.items():
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
            shortcut.activated.connect(callback)
        for sequence, callback, widget in (
            ("Return", self.edit_task, self.focus_page),
            ("Return", self.edit_task, self.calendar_page),
            ("Down", lambda: self._select_offset(1), self.focus_page),
            ("Up", lambda: self._select_offset(-1), self.focus_page),
        ):
            shortcut = QShortcut(QKeySequence(sequence), widget)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)

    def _current_task_page(self):
        widget = self.pages.currentWidget()
        if widget in (self.focus_page, self.calendar_page):
            return widget
        return None

    def add_task(self) -> None:
        page = self._current_task_page() or self.focus_page
        page.add_task()

    def edit_task(self) -> None:
        page = self._current_task_page()
        if page:
            page.edit_task()

    def selected_task(self):
        page = self._current_task_page()
        return page.selected_task() if page else None

    def start_task(self) -> None:
        if self._current_task_page():
            actions.start_task(self, self.db, self.hub, self.selected_task())

    def toggle_pause(self) -> None:
        if self._current_task_page():
            actions.toggle_pause(self, self.db, self.hub, self.selected_task())

    def unstart_task(self) -> None:
        if self._current_task_page():
            actions.unstart_task(self, self.db, self.hub, self.selected_task())

    def reopen_task(self) -> None:
        if self._current_task_page():
            actions.reopen_task(self, self.db, self.hub, self.selected_task())

    def finish_task(self) -> None:
        if self._current_task_page():
            actions.finish_task(self, self.db, self.hub, self.selected_task())

    def miss_task(self) -> None:
        if self._current_task_page():
            actions.miss_task(self, self.db, self.hub, self.selected_task())

    def delete_task(self) -> None:
        if self._current_task_page():
            actions.delete_task(self, self.db, self.hub, self.selected_task())

    def copy_task(self) -> None:
        if actions._text_field_focused():
            return
        if self._current_task_page():
            actions.copy_item(self, self.db, self.hub, self.selected_task())

    def paste_task(self) -> None:
        if actions._text_field_focused():
            return
        if self._current_task_page() or self.pages.currentWidget() is self.focus_page:
            actions.paste_item(self, self.db, self.hub)

    def clear_selection(self) -> None:
        page = self._current_task_page()
        if page:
            page.clear_task_selection()

    def _select_offset(self, delta: int) -> None:
        if self.pages.currentWidget() is self.focus_page:
            self.focus_page.select_offset(delta)

    def _set_filter(self, key: str) -> None:
        self.focus_page.set_view(key)

    def _toggle_sidebar(self) -> None:
        if self.pages.currentWidget() is self.focus_page:
            self.focus_page.toggle_sidebar()

    def refresh(self) -> None:
        self.focus_page.refresh()
        self.calendar_page.refresh()
        self.logbook_page.refresh()
        self.logger_page.refresh()

    def reveal(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def reveal_task(self, task_id: int) -> None:
        self.show_page(0)
        self.focus_page.select_task_id(task_id)
        self.reveal()

    def closeEvent(self, event) -> None:  # noqa: N802
        app = QApplication.instance()
        if app is not None and app.closingDown():
            event.accept()
            return
        event.ignore()
        self.hide()
