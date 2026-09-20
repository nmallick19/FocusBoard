from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from focusboard.paths import applications_dir, autostart_dir, icons_dir

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#2563EB"/>
  <path d="M18 33 l10 10 18-20" fill="none" stroke="#ffffff" stroke-width="5"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
PACKAGING_DIR = PACKAGE_ROOT / "packaging"


def make_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#2563EB"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)
    painter.setPen(QColor("white"))
    font = painter.font()
    font.setBold(True)
    font.setPointSize(28)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "F")
    painter.end()
    return QIcon(pixmap)


def desktop_entry(exec_cmd: str, icon: str) -> str:
    return f"""[Desktop Entry]
Type=Application
Name=Focusboard
Comment=Reminders, focus list, and task tracking
Exec={exec_cmd}
Icon={icon}
Terminal=false
Categories=Office;Calendar;Utility;
StartupNotify=true
X-GNOME-UsesNotifications=true
X-GNOME-Autostart-enabled=true
"""


def install_icon() -> str:
    dest = icons_dir() / "focusboard.svg"
    source = PACKAGING_DIR / "focusboard.svg"
    if source.exists():
        shutil.copy2(source, dest)
    else:
        dest.write_text(ICON_SVG, encoding="utf-8")
    return str(dest)


def install_menu_entry() -> None:
    icon = install_icon()
    exec_cmd = f"{sys.executable} -m focusboard"
    (applications_dir() / "focusboard.desktop").write_text(
        desktop_entry(exec_cmd, icon), encoding="utf-8"
    )


def set_autostart(enabled: bool) -> None:
    path = autostart_dir() / "focusboard.desktop"
    if not enabled:
        if path.exists():
            path.unlink()
        return
    icon = install_icon()
    exec_cmd = f"{sys.executable} -m focusboard"
    path.write_text(desktop_entry(exec_cmd, icon), encoding="utf-8")


def autostart_enabled() -> bool:
    return (autostart_dir() / "focusboard.desktop").exists()
