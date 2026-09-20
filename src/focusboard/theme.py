from __future__ import annotations

import subprocess

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication, QMenu

THEMES = ("system", "light", "dark")

THEME_LABELS = {
    "system": "System (default)",
    "light": "Light",
    "dark": "Dark",
}

# Light and dark each own a full, contrasting set. System picks one of these.
_LIGHT = {
    "window": QColor(247, 247, 248),
    "base": QColor(255, 255, 255),
    "alt": QColor(240, 240, 242),
    "button": QColor(244, 244, 245),
    "text": QColor(24, 24, 27),
    "mid": QColor(113, 113, 122),
    "placeholder": QColor(113, 113, 122),
    "highlight": QColor(37, 99, 235),
    "bright": QColor(225, 29, 72),
}

_DARK = {
    "window": QColor(24, 24, 27),
    "base": QColor(32, 32, 36),
    "alt": QColor(39, 39, 45),
    "button": QColor(39, 39, 45),
    "text": QColor(244, 244, 245),
    "mid": QColor(161, 161, 170),
    "placeholder": QColor(161, 161, 170),
    "highlight": QColor(59, 130, 246),
    "bright": QColor(251, 113, 133),
}

_APP_QSS = """
QWidget { color: palette(window-text); }
QMainWindow, QWidget#AppShell, QWidget#FocusBody {
    background: palette(window);
}
QCheckBox, QRadioButton, QLabel, QGroupBox, QTabBar::tab {
    color: palette(window-text);
}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox, QDateTimeEdit, QDateEdit, QTimeEdit,
QListWidget, QTableWidget, QTreeWidget {
    color: palette(text);
    background: palette(base);
    selection-color: palette(highlighted-text);
    selection-background-color: palette(highlight);
    border: 1px solid palette(mid);
    border-radius: 8px;
    padding: 6px 8px;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
QComboBox:focus, QDateTimeEdit:focus, QDateEdit:focus, QTimeEdit:focus {
    border: 1px solid palette(highlight);
}
QMenu {
    color: palette(window-text);
    background: palette(window);
    border: 1px solid palette(mid);
    padding: 6px;
}
QMenu::item {
    padding: 6px 16px;
    border-radius: 6px;
}
QMenu::item:selected {
    background: palette(highlight);
    color: palette(highlighted-text);
}
QMenuBar, QMenuBar::item {
    color: palette(window-text);
    background: palette(window);
}
QMenuBar::item:selected {
    background: palette(alternate-base);
    border-radius: 6px;
}
QHeaderView::section {
    color: palette(mid);
    background: palette(window);
    border: none;
    border-bottom: 1px solid palette(mid);
    padding: 8px;
    font-weight: 600;
}
QPushButton {
    color: palette(button-text);
    background: palette(button);
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 6px 12px;
}
QPushButton:hover {
    background: palette(alternate-base);
}
QPushButton:focus {
    border: 1px solid palette(highlight);
}
QScrollArea#FocusScroll, QScrollArea#FocusScroll > QWidget > QWidget {
    background: transparent;
    border: none;
}
QFrame#AppHeader {
    background: palette(base);
    border: none;
    border-bottom: 1px solid palette(mid);
}
QLabel#AppBrand {
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.2px;
}
QPushButton#NavButton {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton#NavButton:hover {
    background: palette(alternate-base);
}
QPushButton#NavButton:checked {
    background: palette(alternate-base);
    color: palette(highlight);
}
QPushButton#NavButton:focus {
    border: 1px solid transparent;
}
QPushButton#NavButton:checked:focus {
    border: 1px solid palette(highlight);
}
QPushButton#PrimaryButton {
    background: #2563EB;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton#PrimaryButton:hover {
    background: #1D4ED8;
}
QPushButton#PrimaryButton:focus {
    border: 1px solid palette(highlighted-text);
}
QPushButton#GhostButton {
    background: transparent;
    border: 1px solid transparent;
    padding: 6px 10px;
    color: palette(window-text);
    text-align: left;
}
QPushButton#GhostButton:hover {
    background: palette(alternate-base);
}
QPushButton#DangerButton {
    background: transparent;
    color: #E11D48;
    border: 1px solid transparent;
    padding: 6px 10px;
    text-align: left;
}
QPushButton#DangerButton:hover {
    background: rgba(225, 29, 72, 0.12);
}
QPushButton#FilterChip {
    background: transparent;
    border: 1px solid palette(mid);
    border-radius: 14px;
    padding: 5px 12px;
    font-weight: 600;
}
QPushButton#FilterChip:hover {
    background: palette(alternate-base);
}
QPushButton#FilterChip:checked {
    background: palette(highlight);
    color: palette(highlighted-text);
    border-color: palette(highlight);
}
QPushButton#DayChip {
    background: transparent;
    border: 1px solid palette(mid);
    border-radius: 8px;
    padding: 6px 0;
    min-width: 40px;
    font-weight: 600;
}
QPushButton#DayChip:hover {
    background: palette(alternate-base);
}
QPushButton#DayChip:checked {
    background: palette(highlight);
    color: palette(highlighted-text);
    border-color: palette(highlight);
}
QFrame#FocusSidebar {
    background: palette(base);
    border: none;
    border-right: 1px solid palette(mid);
}
QLabel#SidebarLabel {
    color: palette(mid);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.6px;
    padding: 8px 10px 6px 10px;
}
QPushButton#SideNav {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 8px 10px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
}
QPushButton#SideNav:hover {
    background: palette(alternate-base);
}
QPushButton#SideNav:checked {
    background: palette(alternate-base);
    color: palette(highlight);
    font-weight: 600;
}
QPushButton#IconButton {
    background: transparent;
    border: none;
    border-radius: 6px;
    font-size: 18px;
    font-weight: 600;
    padding: 0;
    color: palette(window-text);
}
QPushButton#IconButton:hover {
    background: palette(alternate-base);
}
QPushButton#IconButton:focus {
    border: 1px solid palette(highlight);
}
QFrame#SidebarRail {
    background: palette(base);
    border: none;
    border-right: 1px solid palette(mid);
}
QFrame#Inspector {
    background: palette(base);
    border: none;
    border-left: 1px solid palette(mid);
}
QLabel#InspectorTitle {
    font-size: 18px;
    font-weight: 700;
    padding-bottom: 10px;
}
QLabel#InspectorCaption {
    color: palette(mid);
    font-size: 12px;
    font-weight: 600;
}
QLabel#InspectorValue {
    font-size: 15px;
}
QFrame#Inspector QPushButton#GhostButton,
QFrame#Inspector QPushButton#DangerButton,
QFrame#Inspector QPushButton#PrimaryButton {
    text-align: left;
    padding: 8px 12px;
}
QSplitter#FocusSplitter::handle {
    background: transparent;
    width: 8px;
}
QLabel#HeroSection {
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.4px;
}
QLabel#SectionTitle {
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.2px;
}
QLabel#CountBadge {
    color: palette(mid);
    background: palette(alternate-base);
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: 600;
}
QLabel#DateHeader {
    color: palette(window-text);
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.3px;
    padding: 10px 8px 6px 8px;
}
QLabel#EmptyHint, QLabel#MetaMuted, QLabel#ActionCaption, QLabel#LogSummary {
    color: palette(mid);
    font-size: 13px;
}
QLabel#TimeCaption {
    color: palette(mid);
    font-size: 13px;
    font-weight: 600;
}
QPushButton#DatePicker, QPushButton#TimePicker {
    color: palette(text);
    background: palette(base);
    border: 1px solid palette(mid);
    border-radius: 8px;
    padding: 6px 12px;
    font-weight: 600;
    text-align: left;
}
QPushButton#TimePicker {
    min-width: 96px;
    text-align: center;
}
QPushButton#DatePicker:hover, QPushButton#TimePicker:hover,
QPushButton#DatePicker:focus, QPushButton#TimePicker:focus {
    border: 1px solid palette(highlight);
}
QFrame#TimePopup, QFrame#CalendarPopup {
    background: palette(base);
    border: 1px solid palette(mid);
    border-radius: 10px;
}
QListWidget#TimeList {
    border: none;
    font-size: 16px;
    font-weight: 600;
    outline: none;
    background: palette(base);
}
QListWidget#TimeList::item {
    padding: 6px;
    border-radius: 6px;
}
QListWidget#TimeList::item:selected {
    background: palette(highlight);
    color: palette(highlighted-text);
}
QWidget#DueBlock {
    border-radius: 12px;
    min-width: 112px;
}
QLabel#TaskDueDate {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.2px;
}
QLabel#TaskDueTime {
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.6px;
    padding: 1px 0 2px 0;
}
QLabel#TaskDueRemain {
    font-size: 13px;
    font-weight: 700;
}
QLabel#StatusPill {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 8px;
    background: palette(alternate-base);
    color: palette(mid);
}
QLabel#StatusPill[status="todo"] {
    background: rgba(100, 116, 139, 0.16);
    color: #64748B;
}
QLabel#StatusPill[status="ongoing"] {
    background: rgba(37, 99, 235, 0.14);
    color: #2563EB;
}
QLabel#StatusPill[status="done"] {
    background: rgba(22, 163, 74, 0.14);
    color: #16A34A;
}
QLabel#StatusPill[status="missed"] {
    background: rgba(234, 88, 12, 0.14);
    color: #EA580C;
}
QFrame#TaskRow {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
}
QFrame#TaskRow:hover {
    background: palette(alternate-base);
}
QFrame#TaskRow[selected="true"] {
    background: palette(alternate-base);
}
QFrame#TaskRow[closed="true"] QLabel#TaskTitle,
QFrame#TaskRow[closed="true"] QLabel#MetaMuted {
    color: palette(mid);
}
QFrame#TodayPanel {
    background: palette(base);
    border: 1px solid palette(mid);
    border-radius: 12px;
}
QFrame#ActionBar {
    background: palette(base);
    border: none;
    border-top: 1px solid palette(mid);
}
QFrame#CalendarCard {
    background: palette(base);
    border: 1px solid palette(mid);
    border-radius: 12px;
}
QLabel#CalendarMonth {
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.3px;
    color: palette(window-text);
}
QCalendarWidget#MonthCalendar {
    background: palette(base);
    border: none;
    font-size: 15px;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background: palette(base);
    border: none;
}
QCalendarWidget QAbstractItemView {
    selection-background-color: palette(highlight);
    selection-color: palette(highlighted-text);
    outline: none;
    font-size: 15px;
}
QCalendarWidget QTableView {
    background: palette(base);
    alternate-background-color: palette(base);
    outline: none;
}
QCalendarWidget QHeaderView,
QCalendarWidget QHeaderView::section {
    background: palette(base);
    color: palette(mid);
    border: none;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 0;
}
QTableWidget#LogTable {
    border: 1px solid palette(mid);
    border-radius: 12px;
    gridline-color: transparent;
    padding: 4px;
}
QTableWidget#LogTable::item {
    padding: 6px 8px;
}
QTableWidget#LogTable::item:selected {
    background: palette(highlight);
    color: palette(highlighted-text);
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px 2px;
}
QScrollBar::handle:vertical {
    background: palette(mid);
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""

_WHEN_LIGHT = """
QWidget#DueBlock[due="today"] {
    background: #DBEAFE;
    border: 1px solid #93C5FD;
    border-left: 4px solid #2563EB;
}
QLabel#TaskDueDate[due="today"], QLabel#TaskDueRemain[due="today"] { color: #1D4ED8; }
QLabel#TaskDueTime[due="today"] { color: #1E40AF; }
QWidget#DueBlock[due="tomorrow"] {
    background: #FEF3C7;
    border: 1px solid #FCD34D;
    border-left: 4px solid #D97706;
}
QLabel#TaskDueDate[due="tomorrow"], QLabel#TaskDueRemain[due="tomorrow"] { color: #B45309; }
QLabel#TaskDueTime[due="tomorrow"] { color: #C2410C; }
QWidget#DueBlock[due="later"] {
    background: #EDE9FE;
    border: 1px solid #C4B5FD;
    border-left: 4px solid #7C3AED;
}
QLabel#TaskDueDate[due="later"], QLabel#TaskDueRemain[due="later"] { color: #6D28D9; }
QLabel#TaskDueTime[due="later"] { color: #5B21B6; }
QWidget#DueBlock[due="overdue"] {
    background: #FFE4E6;
    border: 1px solid #FECDD3;
    border-left: 4px solid #E11D48;
}
QLabel#TaskDueDate[due="overdue"],
QLabel#TaskDueRemain[due="overdue"],
QLabel#TaskDueTime[due="overdue"] { color: #BE123C; }
QLabel#TaskDueTime[due="overdue"] { color: #E11D48; }
"""

_WHEN_DARK = """
QWidget#DueBlock[due="today"] {
    background: #1E3A5F;
    border: 1px solid #3B82F6;
    border-left: 4px solid #60A5FA;
}
QLabel#TaskDueDate[due="today"], QLabel#TaskDueRemain[due="today"] { color: #93C5FD; }
QLabel#TaskDueTime[due="today"] { color: #BFDBFE; }
QWidget#DueBlock[due="tomorrow"] {
    background: #422006;
    border: 1px solid #F59E0B;
    border-left: 4px solid #FBBF24;
}
QLabel#TaskDueDate[due="tomorrow"], QLabel#TaskDueRemain[due="tomorrow"] { color: #FCD34D; }
QLabel#TaskDueTime[due="tomorrow"] { color: #FDE68A; }
QWidget#DueBlock[due="later"] {
    background: #2E1065;
    border: 1px solid #8B5CF6;
    border-left: 4px solid #A78BFA;
}
QLabel#TaskDueDate[due="later"], QLabel#TaskDueRemain[due="later"] { color: #C4B5FD; }
QLabel#TaskDueTime[due="later"] { color: #DDD6FE; }
QWidget#DueBlock[due="overdue"] {
    background: #4C0519;
    border: 1px solid #FB7185;
    border-left: 4px solid #FB7185;
}
QLabel#TaskDueDate[due="overdue"], QLabel#TaskDueRemain[due="overdue"] { color: #FDA4AF; }
QLabel#TaskDueTime[due="overdue"] { color: #FECDD3; }
"""


def normalize_theme(value: str | None) -> str:
    if value in THEMES:
        return value
    return "system"


def _gsettings(key: str) -> str:
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", key],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
    except OSError:
        return ""
    return result.stdout.strip().strip("'\"")


def system_prefers_dark() -> bool:
    color_scheme = _gsettings("color-scheme")
    if "prefer-dark" in color_scheme:
        return True
    if "prefer-light" in color_scheme:
        return False

    gtk_theme = _gsettings("gtk-theme").lower()
    if gtk_theme.endswith("-dark") or "-dark-" in gtk_theme or gtk_theme.endswith("dark"):
        return True

    scheme = QGuiApplication.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Dark:
        return True
    if scheme == Qt.ColorScheme.Light:
        return False

    return QGuiApplication.palette().color(QPalette.ColorRole.Window).lightness() < 128


def resolved_dark(theme: str) -> bool:
    theme = normalize_theme(theme)
    if theme == "dark":
        return True
    if theme == "light":
        return False
    return system_prefers_dark()


def _build_palette(colors: dict[str, QColor]) -> QPalette:
    palette = QPalette()
    window = colors["window"]
    text = colors["text"]
    base = colors["base"]
    alt = colors["alt"]
    button = colors["button"]
    mid = colors["mid"]
    highlight = colors["highlight"]
    mapping = {
        QPalette.ColorRole.Window: window,
        QPalette.ColorRole.WindowText: text,
        QPalette.ColorRole.Base: base,
        QPalette.ColorRole.AlternateBase: alt,
        QPalette.ColorRole.ToolTipBase: base,
        QPalette.ColorRole.ToolTipText: text,
        QPalette.ColorRole.Text: text,
        QPalette.ColorRole.Button: button,
        QPalette.ColorRole.ButtonText: text,
        QPalette.ColorRole.BrightText: colors["bright"],
        QPalette.ColorRole.Link: highlight,
        QPalette.ColorRole.Highlight: highlight,
        QPalette.ColorRole.HighlightedText: QColor(255, 255, 255),
        QPalette.ColorRole.PlaceholderText: colors["placeholder"],
        QPalette.ColorRole.Light: window.lighter(115),
        QPalette.ColorRole.Midlight: window.darker(108),
        QPalette.ColorRole.Mid: mid,
        QPalette.ColorRole.Dark: window.darker(150),
        QPalette.ColorRole.Shadow: QColor(0, 0, 0),
    }
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        for role, color in mapping.items():
            palette.setColor(group, role, color)
    disabled = QColor(mid)
    disabled_bg = QColor(window)
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
        QPalette.ColorRole.PlaceholderText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, disabled)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Window, disabled_bg)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, alt)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, button)
    return palette


def light_palette() -> QPalette:
    return _build_palette(_LIGHT)


def dark_palette() -> QPalette:
    return _build_palette(_DARK)


def apply_theme(app: QApplication, theme: str) -> None:
    dark = resolved_dark(theme)
    app.setStyle("Fusion")
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark if dark else Qt.ColorScheme.Light)
    palette = dark_palette() if dark else light_palette()
    font = app.font()
    font.setPointSize(max(font.pointSize(), 11))
    app.setFont(font)
    app.setStyleSheet(_APP_QSS + (_WHEN_DARK if dark else _WHEN_LIGHT))
    app.setPalette(palette)
    style = app.style()
    for widget in app.allWidgets():
        widget.setPalette(QPalette())
        style.unpolish(widget)
        style.polish(widget)
        widget.update()
    app.setPalette(palette)


def build_theme_menu(parent, db, hub) -> QMenu:
    menu = QMenu("Theme", parent)
    group = QActionGroup(menu)
    group.setExclusive(True)
    current = db.get_theme()
    actions: dict[str, QAction] = {}
    for key in THEMES:
        action = QAction(THEME_LABELS[key], menu)
        action.setCheckable(True)
        action.setData(key)
        action.setChecked(key == current)
        group.addAction(action)
        menu.addAction(action)
        actions[key] = action

    def on_triggered(action: QAction) -> None:
        name = action.data()
        if name == db.get_theme():
            return
        db.set_theme(name)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, name)
        hub.theme_changed.emit(name)

    group.triggered.connect(on_triggered)

    def sync(name: str) -> None:
        action = actions.get(name)
        if action and not action.isChecked():
            action.setChecked(True)

    hub.theme_changed.connect(sync)
    return menu
