from __future__ import annotations

import os
from pathlib import Path


APP_ID = "focusboard"


def data_dir() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / APP_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    path = base / APP_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "focusboard.db"


def autostart_dir() -> Path:
    path = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart"
    path.mkdir(parents=True, exist_ok=True)
    return path


def applications_dir() -> Path:
    path = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "applications"
    path.mkdir(parents=True, exist_ok=True)
    return path


def icons_dir() -> Path:
    path = (
        Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        / "icons"
        / "hicolor"
        / "scalable"
        / "apps"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path
