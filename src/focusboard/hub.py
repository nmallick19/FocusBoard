from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class Hub(QObject):
    tasks_changed = Signal()
    show_main = Signal()
    show_main_task = Signal(int)
    theme_changed = Signal(str)
