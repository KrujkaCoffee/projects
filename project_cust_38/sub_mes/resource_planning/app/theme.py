from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from string import Template
from typing import Any

from PyQt5.QtCore import QObject, QSettings, pyqtSignal
from PyQt5.QtGui import QColor, QPalette


@dataclass(frozen=True)
class ThemeDefinition:
    key: str
    title: str
    colors: Mapping[str, str]


def _theme(key: str, display_name: str, **colors: str) -> ThemeDefinition:
    return ThemeDefinition(key=key, title=display_name, colors=colors)


THEMES: dict[str, ThemeDefinition] = {
    "dark": _theme(
        "dark",
        "Тёмная",
        window="#0f141c",
        text="#e6edf3",
        bright_text="#ffffff",
        disabled_text="#647084",
        panel="#141b25",
        tab="#171f2b",
        tab_hover="#202b3a",
        button="#202a38",
        button_hover="#29374a",
        button_pressed="#1d4f91",
        button_disabled="#171e28",
        input="#121923",
        view="#111821",
        alternate="#151e29",
        border="#2a3443",
        strong_border="#3a4658",
        focus="#5d9bea",
        selection="#285b99",
        selection_text="#ffffff",
        header="#202a38",
        tooltip="#202a38",
        tooltip_text="#f2f6fb",
        scroll_bg="#101720",
        scroll_handle="#3a4658",
        muted="#9aa9bd",
        title="#c8d2df",
        success="#1f6f50",
        success_hover="#278764",
        warning="#d29922",
        danger="#ff8a8a",
        dirty_bg="#2b2417",
        canvas_bg="#0b1220",
        card_bg="#141f31",
        card_root_bg="#17263b",
        canvas_header="#1f2d43",
        canvas_header_root="#2b3348",
        canvas_text="#e5edf8",
        canvas_grid="#233249",
        canvas_border="#52647c",
        root_border="#f59e0b",
        port="#60a5fa",
        saved="#34d399",
        draft="#f59e0b",
        canvas_disabled="#7c8ba1",
        secondary_text="#aeb9c8",
        accent_text="#7db3ff",
        hover_border="#6099e8",
        pressed_border="#70a9f5",
        disabled_control_text="#596577",
        disabled_control_border="#28313f",
        input_border="#344154",
        popup_bg="#151d28",
        view_text="#dce5ef",
        grid="#283343",
        tooltip_border="#52627a",
        splitter_hover="#456084",
        warning_text="#f2c76e",
        valid_text="#70d6a6",
        success_border="#38a174",
    ),
    "light": _theme(
        "light",
        "Светлая",
        window="#f3f5f8",
        text="#1f2937",
        bright_text="#111827",
        disabled_text="#98a2b3",
        panel="#ffffff",
        tab="#e9edf3",
        tab_hover="#dce5f2",
        button="#eef2f7",
        button_hover="#e0e8f3",
        button_pressed="#c9dcf5",
        button_disabled="#f2f4f7",
        input="#ffffff",
        view="#ffffff",
        alternate="#f7f9fc",
        border="#d0d7e2",
        strong_border="#aeb8c6",
        focus="#3478c9",
        selection="#2f6fb3",
        selection_text="#ffffff",
        header="#e7ecf3",
        tooltip="#253247",
        tooltip_text="#ffffff",
        scroll_bg="#edf1f5",
        scroll_handle="#aeb8c6",
        muted="#667085",
        title="#344054",
        success="#18794e",
        success_hover="#146c43",
        warning="#9a6700",
        danger="#b42318",
        dirty_bg="#fff4ce",
        canvas_bg="#eef3f8",
        card_bg="#ffffff",
        card_root_bg="#edf5ff",
        canvas_header="#dfe8f3",
        canvas_header_root="#d7e7fb",
        canvas_text="#223047",
        canvas_grid="#d8e0ea",
        canvas_border="#8797aa",
        root_border="#b26a00",
        port="#2f6fb3",
        saved="#18794e",
        draft="#b26a00",
        canvas_disabled="#7b8794",
        secondary_text="#667085",
        accent_text="#3478c9",
        hover_border="#3478c9",
        pressed_border="#3478c9",
        disabled_control_text="#98a2b3",
        disabled_control_border="#d0d7e2",
        input_border="#aeb8c6",
        popup_bg="#f7f9fc",
        view_text="#1f2937",
        grid="#d0d7e2",
        tooltip_border="#aeb8c6",
        splitter_hover="#3478c9",
        warning_text="#9a6700",
        valid_text="#18794e",
        success_border="#146c43",
    ),
    "nord": _theme(
        "nord",
        "Северная",
        window="#2e3440",
        text="#eceff4",
        bright_text="#ffffff",
        disabled_text="#697486",
        panel="#3b4252",
        tab="#353c4a",
        tab_hover="#434c5e",
        button="#434c5e",
        button_hover="#4c566a",
        button_pressed="#4c6f8f",
        button_disabled="#343b48",
        input="#2f3541",
        view="#303642",
        alternate="#363d4b",
        border="#4c566a",
        strong_border="#68758a",
        focus="#88c0d0",
        selection="#5e81ac",
        selection_text="#ffffff",
        header="#434c5e",
        tooltip="#242933",
        tooltip_text="#eceff4",
        scroll_bg="#2b303b",
        scroll_handle="#59657a",
        muted="#aab4c4",
        title="#d8dee9",
        success="#4f8f74",
        success_hover="#5c9f82",
        warning="#d09a4a",
        danger="#bf616a",
        dirty_bg="#51452f",
        canvas_bg="#252b35",
        card_bg="#343b49",
        card_root_bg="#3b4657",
        canvas_header="#434c5e",
        canvas_header_root="#4c566a",
        canvas_text="#eceff4",
        canvas_grid="#4c566a",
        canvas_border="#718096",
        root_border="#ebcb8b",
        port="#88c0d0",
        saved="#a3be8c",
        draft="#ebcb8b",
        canvas_disabled="#7d8899",
        secondary_text="#aab4c4",
        accent_text="#88c0d0",
        hover_border="#88c0d0",
        pressed_border="#88c0d0",
        disabled_control_text="#697486",
        disabled_control_border="#4c566a",
        input_border="#68758a",
        popup_bg="#363d4b",
        view_text="#eceff4",
        grid="#4c566a",
        tooltip_border="#68758a",
        splitter_hover="#88c0d0",
        warning_text="#d09a4a",
        valid_text="#a3be8c",
        success_border="#5c9f82",
    ),
    "graphite": _theme(
        "graphite",
        "Графит и красный",
        window="#18191b",
        text="#f0eeee",
        bright_text="#ffffff",
        disabled_text="#6f6f73",
        panel="#202124",
        tab="#26272b",
        tab_hover="#303136",
        button="#2b2c31",
        button_hover="#37383e",
        button_pressed="#6d302f",
        button_disabled="#212226",
        input="#1d1e21",
        view="#1c1d20",
        alternate="#232428",
        border="#36373c",
        strong_border="#52535a",
        focus="#df6b65",
        selection="#9f403d",
        selection_text="#ffffff",
        header="#2b2c31",
        tooltip="#303136",
        tooltip_text="#ffffff",
        scroll_bg="#191a1d",
        scroll_handle="#52535a",
        muted="#a8a5a5",
        title="#ded9d9",
        success="#39745a",
        success_hover="#478a6c",
        warning="#c58b42",
        danger="#f07a73",
        dirty_bg="#3b2e20",
        canvas_bg="#141517",
        card_bg="#232428",
        card_root_bg="#2b292c",
        canvas_header="#303136",
        canvas_header_root="#493033",
        canvas_text="#f0eeee",
        canvas_grid="#3a3b40",
        canvas_border="#686970",
        root_border="#df6b65",
        port="#e28782",
        saved="#5dac83",
        draft="#d49a50",
        canvas_disabled="#77777c",
        secondary_text="#a8a5a5",
        accent_text="#df6b65",
        hover_border="#df6b65",
        pressed_border="#df6b65",
        disabled_control_text="#6f6f73",
        disabled_control_border="#36373c",
        input_border="#52535a",
        popup_bg="#232428",
        view_text="#f0eeee",
        grid="#36373c",
        tooltip_border="#52535a",
        splitter_hover="#df6b65",
        warning_text="#c58b42",
        valid_text="#5dac83",
        success_border="#478a6c",
    ),
    "warm": _theme(
        "warm",
        "Тёплая",
        window="#f2ede4",
        text="#3b3128",
        bright_text="#241d17",
        disabled_text="#a29587",
        panel="#fffaf1",
        tab="#e8dfd2",
        tab_hover="#ded1bf",
        button="#eee3d3",
        button_hover="#e2d2bc",
        button_pressed="#d9b68f",
        button_disabled="#f0ebe4",
        input="#fffdf8",
        view="#fffdf8",
        alternate="#f8f2e9",
        border="#d7c8b5",
        strong_border="#b9a58f",
        focus="#b8652a",
        selection="#a85d2b",
        selection_text="#ffffff",
        header="#e8ddcd",
        tooltip="#4a3c30",
        tooltip_text="#fffaf1",
        scroll_bg="#ece4d8",
        scroll_handle="#b9a58f",
        muted="#7d6f62",
        title="#514237",
        success="#3d7955",
        success_hover="#4b8b64",
        warning="#9b680f",
        danger="#a83d32",
        dirty_bg="#f5e5bd",
        canvas_bg="#ede5da",
        card_bg="#fffaf1",
        card_root_bg="#faead8",
        canvas_header="#e5d6c3",
        canvas_header_root="#e7caa8",
        canvas_text="#3b3128",
        canvas_grid="#d7c8b5",
        canvas_border="#9f8b75",
        root_border="#b8652a",
        port="#b8652a",
        saved="#3d7955",
        draft="#a96b18",
        canvas_disabled="#8d8277",
        secondary_text="#7d6f62",
        accent_text="#b8652a",
        hover_border="#b8652a",
        pressed_border="#b8652a",
        disabled_control_text="#a29587",
        disabled_control_border="#d7c8b5",
        input_border="#b9a58f",
        popup_bg="#f8f2e9",
        view_text="#3b3128",
        grid="#d7c8b5",
        tooltip_border="#b9a58f",
        splitter_hover="#b8652a",
        warning_text="#9b680f",
        valid_text="#3d7955",
        success_border="#4b8b64",
    ),
}

DEFAULT_THEME_KEY = "dark"
_current_theme_key = DEFAULT_THEME_KEY
_theme_listeners: list[Callable[[ThemeDefinition], None]] = []


_QSS_TEMPLATE = Template(
    r"""
QMainWindow, QDialog, QWidget {
    background-color: $window;
    color: $text;
    font-size: 10pt;
}
QMainWindow::separator { background: transparent; width: 0px; height: 0px; border: 0px; }
QWidget:disabled { color: $disabled_text; }
QTabWidget::pane {
    border: 1px solid $border; border-radius: 8px; background: $panel; top: -1px;
}
QTabBar::tab {
    background: $tab; color: $secondary_text; border: 1px solid $border; border-bottom: none;
    padding: 8px 14px; margin-right: 3px; border-top-left-radius: 7px;
    border-top-right-radius: 7px; min-width: 250px;
}
QTabBar::tab:hover { background: $tab_hover; color: $tooltip_text; }
QTabBar::tab:selected { background: $panel; color: $accent_text; font-weight: 600; }
QToolBar { background: $panel; border-bottom: 1px solid $border; spacing: 8px; padding: 6px; }
QStatusBar { background: $panel; border-top: 1px solid $border; color: $secondary_text; }
QPushButton, QToolButton {
    background: $button; color: $text; border: 1px solid $strong_border;
    border-radius: 7px; padding: 6px 10px;
}
QPushButton:hover, QToolButton:hover { background: $button_hover; border-color: $hover_border; }
QPushButton:pressed, QToolButton:pressed { background: $button_pressed; border-color: $pressed_border; }
QPushButton:disabled, QToolButton:disabled {
    background: $button_disabled; color: $disabled_control_text; border-color: $disabled_control_border;
}
QToolButton#column_filter_reset { padding: 0; border-radius: 4px; }
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDateTimeEdit {
    background: $input; color: $text; border: 1px solid $input_border;
    border-radius: 6px; padding: 4px; selection-background-color: $selection;
    selection-color: $selection_text;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDateTimeEdit:focus { border-color: $focus; }
QComboBox QAbstractItemView {
    background: $popup_bg; color: $text; border: 1px solid $strong_border;
    selection-background-color: $selection;
}
QGroupBox {
    background: $panel; border: 1px solid $border; border-radius: 9px;
    margin-top: 12px; padding-top: 10px; font-weight: 600;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: $title; }
QFrame#top_panel, QFrame#tables_filter_panel, QFrame#sql_tools_toolbar,
QFrame#physical_tables_filters_panel {
    background: $panel; border: 1px solid $border; border-radius: 9px;
}
QTableWidget, QTableView, QTreeWidget, QTreeView, QListWidget {
    background: $view; alternate-background-color: $alternate; color: $view_text;
    gridline-color: $grid; border: 1px solid $border; border-radius: 7px;
    selection-background-color: $selection; selection-color: $selection_text;
}
QTableWidget::item, QTreeWidget::item { padding: 3px; }
QTableWidget::item:selected, QTreeWidget::item:selected {
    background: $selection; color: $selection_text;
}
QHeaderView::section {
    background: $header; color: $view_text; padding: 6px; border: 0;
    border-right: 1px solid $input_border; border-bottom: 1px solid $input_border;
    font-weight: 600;
}
QMenu { background: $tab; color: $text; border: 1px solid $strong_border; padding: 4px; }
QMenu::item { padding: 6px 22px 6px 10px; }
QMenu::item:selected { background: $selection; }
QToolTip { background: $tooltip; color: $tooltip_text; border: 1px solid $tooltip_border; padding: 5px; }
QSplitter::handle { background: $border; }
QSplitter::handle:hover { background: $splitter_hover; }
QSplitter::handle:horizontal { width: 5px; }
QSplitter::handle:vertical { height: 5px; }
QScrollBar:vertical { background: $scroll_bg; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: $scroll_handle; min-height: 28px; border-radius: 5px; }
QScrollBar:horizontal { background: $scroll_bg; height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: $scroll_handle; min-width: 28px; border-radius: 5px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QCheckBox::indicator { width: 15px; height: 15px; }
QLabel#pending_changes_label, QLabel#tables_filter_count_label, QLabel#map_status_label,
QLabel#physical_tables_filter_count, QLabel#sql_tools_status { color: $muted; padding: 0 6px; }
QPushButton#apply_draft_btn, QPushButton#sql_run_button {
    background: $success; border-color: $success_border; font-weight: 600;
}
QPushButton#apply_draft_btn:hover, QPushButton#sql_run_button:hover { background: $success_hover; }
QPushButton#sql_cancel_button { color: $danger; }
QLineEdit[editDirty="true"], QComboBox[editDirty="true"],
QTextEdit[editDirty="true"], QPlainTextEdit[editDirty="true"] {
    border: 1px solid $warning; background: $dirty_bg;
}
QCheckBox[editDirty="true"] { color: $warning_text; }
QWidget[filterInvalid="true"] { border: 1px solid $danger; border-radius: 5px; }
QLabel#relation_contract_status_label { color: $muted; padding: 3px 6px; }
QLabel#relation_contract_status_label[state="error"] { color: $danger; }
QLabel#relation_contract_status_label[state="warning"] { color: $warning_text; }
QLabel#relation_contract_status_label[state="valid"] { color: $valid_text; }
QLabel#physical_tables_title { color: $title; font-size: 11pt; font-weight: 600; padding: 4px 2px; }
QLabel#physical_tables_edit_status, QLabel#sql_tools_hint { color: $muted; padding: 3px 6px; }
QLabel#physical_tables_editor_hint { color: $muted; padding: 2px 4px; }
QTreeWidget#physical_tables_list { outline: 0; }
QPushButton#edit_physical_tables_btn { font-weight: 600; }
QTableWidget#physical_tables_filter_grid { border-radius: 5px; }
QPlainTextEdit#sql_editor { font-family: "Cascadia Mono", "Consolas", monospace; font-size: 10.5pt; }
QPlainTextEdit#sql_messages { font-family: "Cascadia Mono", "Consolas", monospace; }
QCheckBox#sql_allow_writes[armed="true"] { color: $danger; font-weight: 600; }
"""
)


def resolve_theme(key: str | None) -> ThemeDefinition:
    return THEMES.get(str(key or ""), THEMES[DEFAULT_THEME_KEY])


def current_theme() -> ThemeDefinition:
    return THEMES[_current_theme_key]


def current_theme_key() -> str:
    return _current_theme_key


def theme_color(token: str, theme: ThemeDefinition | str | None = None) -> QColor:
    definition = (
        resolve_theme(theme) if isinstance(theme, str) else (theme or current_theme())
    )
    return QColor(definition.colors[token])


def build_stylesheet(theme: ThemeDefinition | str | None = None) -> str:
    definition = (
        resolve_theme(theme) if isinstance(theme, str) else (theme or current_theme())
    )
    return _QSS_TEMPLATE.substitute(definition.colors)


def build_palette(theme: ThemeDefinition | str | None = None) -> QPalette:
    definition = (
        resolve_theme(theme) if isinstance(theme, str) else (theme or current_theme())
    )
    colors = definition.colors
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(colors["window"]))
    palette.setColor(QPalette.WindowText, QColor(colors["text"]))
    palette.setColor(QPalette.Base, QColor(colors["view"]))
    palette.setColor(QPalette.AlternateBase, QColor(colors["alternate"]))
    palette.setColor(QPalette.ToolTipBase, QColor(colors["tooltip"]))
    palette.setColor(QPalette.ToolTipText, QColor(colors["tooltip_text"]))
    palette.setColor(QPalette.Text, QColor(colors["text"]))
    palette.setColor(QPalette.Button, QColor(colors["button"]))
    palette.setColor(QPalette.ButtonText, QColor(colors["text"]))
    palette.setColor(QPalette.BrightText, QColor(colors["bright_text"]))
    palette.setColor(QPalette.Highlight, QColor(colors["selection"]))
    palette.setColor(QPalette.HighlightedText, QColor(colors["selection_text"]))
    palette.setColor(QPalette.Link, QColor(colors["focus"]))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(colors["disabled_text"]))
    palette.setColor(
        QPalette.Disabled, QPalette.ButtonText, QColor(colors["disabled_text"])
    )
    palette.setColor(
        QPalette.Disabled, QPalette.WindowText, QColor(colors["disabled_text"])
    )
    return palette


def register_theme_listener(listener: Callable[[ThemeDefinition], None]) -> None:
    if listener not in _theme_listeners:
        _theme_listeners.append(listener)


def unregister_theme_listener(listener: Callable[[ThemeDefinition], None]) -> None:
    if listener in _theme_listeners:
        _theme_listeners.remove(listener)


def apply_theme(app: Any, key: str | None) -> str:
    global _current_theme_key
    definition = resolve_theme(key)
    _current_theme_key = definition.key
    for listener in tuple(_theme_listeners):
        listener(definition)
    app.setPalette(build_palette(definition))
    app.setStyleSheet(build_stylesheet(definition))
    app.setProperty("themeKey", definition.key)
    for widget in app.allWidgets():
        hook = getattr(widget, "apply_application_theme", None)
        if callable(hook):
            hook(definition)
        widget.update()
        viewport = getattr(widget, "viewport", None)
        if callable(viewport):
            viewport().update()
    return definition.key


class ThemeController(QObject):
    themeChanged = pyqtSignal(str)

    SETTINGS_ORGANIZATION = "powerz"
    SETTINGS_APPLICATION = "admin_panel"
    SETTINGS_KEY = "ui/theme"

    def __init__(self, app: Any, settings: QSettings | None = None) -> None:
        super().__init__(app)
        self.app = app
        self.settings = settings or QSettings(
            self.SETTINGS_ORGANIZATION,
            self.SETTINGS_APPLICATION,
        )
        self.current_key = DEFAULT_THEME_KEY

    def apply_saved(self) -> str:
        key = str(self.settings.value(self.SETTINGS_KEY, DEFAULT_THEME_KEY) or "")
        return self.apply(key, persist=False)

    def apply(self, key: str | None, *, persist: bool = True) -> str:
        resolved = apply_theme(self.app, key)
        self.current_key = resolved
        if persist:
            self.settings.setValue(self.SETTINGS_KEY, resolved)
        self.themeChanged.emit(resolved)
        return resolved


# Compatibility names used by the existing entry point and downstream imports.
APP_QSS = build_stylesheet(DEFAULT_THEME_KEY)


def apply_dark_palette(app: Any) -> None:
    app.setPalette(build_palette(DEFAULT_THEME_KEY))
