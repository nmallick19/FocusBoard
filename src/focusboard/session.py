from __future__ import annotations

import os
import subprocess

from PySide6.QtCore import QObject, QTimer, Signal, Slot

try:
    from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
except ImportError:  # pragma: no cover - QtDBus missing in some builds
    QDBusConnection = None  # type: ignore[misc, assignment]
    QDBusInterface = None  # type: ignore[misc, assignment]
    QDBusMessage = None  # type: ignore[misc, assignment]


def _loginctl_flag(name: str) -> bool | None:
    try:
        output = subprocess.check_output(
            ["loginctl", "show-session", "self", "-p", name],
            text=True,
            timeout=1,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    line = output.strip().lower()
    if line.endswith("=yes"):
        return True
    if line.endswith("=no"):
        return False
    return None


def _screensaver_active() -> bool | None:
    if QDBusInterface is None or QDBusConnection is None:
        return None
    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        return None
    for service, path, iface in (
        ("org.gnome.ScreenSaver", "/org/gnome/ScreenSaver", "org.gnome.ScreenSaver"),
        ("org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver", "org.freedesktop.ScreenSaver"),
    ):
        proxy = QDBusInterface(service, path, iface, bus)
        if not proxy.isValid():
            continue
        reply = proxy.call("GetActive")
        if reply.type() == QDBusMessage.MessageType.ReplyMessage and reply.arguments():
            return bool(reply.arguments()[0])
    return None


def session_is_locked() -> bool:
    locked = _loginctl_flag("LockedHint")
    if locked:
        return True
    saver = _screensaver_active()
    if saver:
        return True
    return False


def display_is_off() -> bool:
    display = os.environ.get("DISPLAY")
    if not display:
        return False
    try:
        output = subprocess.check_output(
            ["xset", "q"],
            text=True,
            timeout=1,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return "Monitor is Off" in output


def session_unavailable_reason() -> str | None:
    if session_is_locked():
        return "screen_lock"
    if display_is_off():
        return "display_off"
    return None


def session_is_present() -> bool:
    return session_unavailable_reason() is None


class SessionGuard(QObject):
    """Watch lock screen, display idle, and system sleep."""

    unavailable = Signal(str)
    available = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._away = False
        self._sleeping = False
        self._poll = QTimer(self)
        self._poll.setInterval(2000)
        self._poll.timeout.connect(self._tick)
        self._bind_dbus()
        self._poll.start()
        QTimer.singleShot(400, self._tick)

    def is_away(self) -> bool:
        return self._away or self._sleeping or session_unavailable_reason() is not None

    def _bind_dbus(self) -> None:
        if QDBusConnection is None:
            return
        session = QDBusConnection.sessionBus()
        if session.isConnected():
            session.connect(
                "org.gnome.ScreenSaver",
                "/org/gnome/ScreenSaver",
                "org.gnome.ScreenSaver",
                "ActiveChanged",
                self,
                SLOT_ACTIVE,
            )
            session.connect(
                "org.freedesktop.ScreenSaver",
                "/org/freedesktop/ScreenSaver",
                "org.freedesktop.ScreenSaver",
                "ActiveChanged",
                self,
                SLOT_ACTIVE,
            )
        system = QDBusConnection.systemBus()
        if system.isConnected():
            system.connect(
                "org.freedesktop.login1",
                "/org/freedesktop/login1",
                "org.freedesktop.login1.Manager",
                "PrepareForSleep",
                self,
                SLOT_SLEEP,
            )

    @Slot(bool)
    def on_screensaver_active(self, active: bool) -> None:
        self._apply(locked=active, reason="screen_lock")

    @Slot(bool)
    def on_prepare_for_sleep(self, sleeping: bool) -> None:
        self._sleeping = sleeping
        if sleeping:
            self._apply(locked=True, reason="sleep")
        else:
            self._apply(locked=False, reason="sleep")

    def _tick(self) -> None:
        if self._sleeping:
            return
        reason = session_unavailable_reason()
        if reason:
            self._apply(locked=True, reason=reason)
            return
        self._apply(locked=False, reason="screen_lock")

    def _apply(self, *, locked: bool, reason: str) -> None:
        if locked:
            if not self._away:
                self._away = True
                self.unavailable.emit(reason)
            return
        if self._away or self._sleeping:
            self._away = False
            self._sleeping = False
            self.available.emit()


SLOT_ACTIVE = "on_screensaver_active(bool)"
SLOT_SLEEP = "on_prepare_for_sleep(bool)"
