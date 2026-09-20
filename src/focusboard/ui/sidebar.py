from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
)

from focusboard.models import CATEGORY_LABELS
from focusboard.ui.chrome import IconButton, SideNavButton, SidebarLabel

STATUS_VIEWS = {
    "all": {"next": True, "ongoing": True, "finished": False},
    "next": {"next": True, "ongoing": False, "finished": False},
    "ongoing": {"next": False, "ongoing": True, "finished": False},
    "finished": {"next": False, "ongoing": False, "finished": True},
}


def view_from_filters(filters: dict[str, bool]) -> str:
    if filters.get("finished") and not filters.get("next") and not filters.get("ongoing"):
        return "finished"
    if filters.get("next") and not filters.get("ongoing") and not filters.get("finished"):
        return "next"
    if filters.get("ongoing") and not filters.get("next") and not filters.get("finished"):
        return "ongoing"
    return "all"


class FocusSidebar(QFrame):
    view_changed = Signal(str)
    project_changed = Signal(object)
    close_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("FocusSidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 8, 16)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 0, 4)
        header.addStretch()
        self.close_btn = IconButton("×")
        self.close_btn.setToolTip("Close sidebar")
        self.close_btn.setAccessibleName("Close sidebar")
        self.close_btn.clicked.connect(self.close_requested.emit)
        header.addWidget(self.close_btn)
        layout.addLayout(header)

        layout.addWidget(SidebarLabel("Filters"))
        self._view_group = QButtonGroup(self)
        self._view_group.setExclusive(True)
        self.view_buttons: dict[str, SideNavButton] = {}
        for key, label, tip in (
            ("all", "All", "Open work that still needs attention (A)"),
            ("next", "Next", "To-do tasks that have not been started (N)"),
            ("ongoing", "Ongoing", "Tasks you have started (O)"),
            ("finished", "Finished", "Done and missed tasks (D)"),
        ):
            button = SideNavButton(label)
            button.setToolTip(tip)
            self._view_group.addButton(button)
            self.view_buttons[key] = button
            layout.addWidget(button)
            button.clicked.connect(lambda checked, name=key: self._on_view(name, checked))

        layout.addSpacing(16)
        layout.addWidget(SidebarLabel("Projects"))
        self._project_group = QButtonGroup(self)
        self._project_group.setExclusive(True)
        self.project_buttons: dict[str | None, SideNavButton] = {}
        all_projects = SideNavButton("All projects")
        all_projects.setToolTip("Show every project")
        self._project_group.addButton(all_projects)
        self.project_buttons[None] = all_projects
        layout.addWidget(all_projects)
        all_projects.clicked.connect(lambda checked: self._on_project(None, checked))
        for value, label in CATEGORY_LABELS.items():
            button = SideNavButton(label)
            self._project_group.addButton(button)
            self.project_buttons[value.value] = button
            layout.addWidget(button)
            button.clicked.connect(lambda checked, name=value.value: self._on_project(name, checked))

        layout.addStretch()
        self.view_buttons["all"].setChecked(True)
        all_projects.setChecked(True)
        self._project: str | None = None

    def current_view(self) -> str:
        for key, button in self.view_buttons.items():
            if button.isChecked():
                return key
        return "all"

    def current_project(self) -> str | None:
        return self._project

    def set_view(self, name: str) -> None:
        button = self.view_buttons.get(name)
        if button is None or button.isChecked():
            return
        button.setChecked(True)
        self.view_changed.emit(name)

    def sync_from_filters(self, filters: dict[str, bool]) -> None:
        name = view_from_filters(filters)
        button = self.view_buttons[name]
        button.blockSignals(True)
        button.setChecked(True)
        button.blockSignals(False)

    def _on_view(self, name: str, checked: bool) -> None:
        if checked:
            self.view_changed.emit(name)

    def _on_project(self, name: str | None, checked: bool) -> None:
        if not checked:
            return
        self._project = name
        self.project_changed.emit(name)
