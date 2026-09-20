from __future__ import annotations

import subprocess

from PySide6.QtWidgets import QSystemTrayIcon


def notify(title: str, body: str, tray: QSystemTrayIcon | None = None) -> None:
    try:
        subprocess.Popen(
            ["notify-send", "-a", "Focusboard", "-i", "focusboard", title, body],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    except OSError:
        pass
    if tray is not None and tray.isVisible():
        tray.showMessage(title, body, QSystemTrayIcon.MessageIcon.Information, 8000)
