from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path

from PySide6.QtCore import QLockFile

from focusboard.paths import data_dir


def _cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ")
        return raw.decode("utf-8", errors="ignore").lower()
    except OSError:
        return ""


def _is_focusboard(pid: int) -> bool:
    return "focusboard" in _cmdline(pid)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _stop_pid(pid: int, wait_seconds: float = 6.0) -> None:
    if pid <= 0 or pid == os.getpid():
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        return
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        return
    time.sleep(0.2)


def acquire_instance_lock() -> QLockFile:
    """Close any running Focusboard, then take the lock for this process."""
    lock_path = str(data_dir() / "focusboard.lock")
    lock = QLockFile(lock_path)
    lock.setStaleLockTime(2000)
    if lock.tryLock(50):
        return lock

    pid, _host, _app = lock.getLockInfo()
    if pid and pid != os.getpid() and _pid_alive(pid):
        if _is_focusboard(pid):
            _stop_pid(pid)
        else:
            lock.removeStaleLockFile()
    else:
        lock.removeStaleLockFile()

    if lock.tryLock(4000):
        return lock

    lock.removeStaleLockFile()
    if lock.tryLock(1000):
        return lock

    print("Focusboard is already running and could not be replaced.", file=sys.stderr)
    raise SystemExit(1)
