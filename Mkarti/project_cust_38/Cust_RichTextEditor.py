# -*- coding: utf-8 -*-
"""
Основные методы:
    RichTextEditorWidget() или RichTextEditorWidget(parent)
    html = CSQ.custom_request_c(db_users, 'SELECT html FROM test LIMIT 1', one=True, hat_c=False)

    instance = RichTextEditorWidget(
        initial_view=RichTextViewMode.VIEW_ONLY,    Режим просмотра (без возможности редактирования)
        html=html                                   Базовый html
    )
    instance.set_html(html)                         Загрузить html разметку в виджет
    html = instance.to_html()                       Выгрузить html разметку из редактора
    instance.set_read_only(True)                    Переключить в режим просмотра
    instance.is_modified()                          Изменился ли текст с момента загрузки
    instance.clear()                                Отчистить текст с редактора
    instance.mark_clean()                           Стереть отметку о том что объект был редактирован

    instance.plain_text_to_html()                   Конвертировать обычный текст в html
    instance.set_text_auto(text)                    Если текст html заполнит его как html если нет попытается конвертировать в html

Побочные (отладочные) методы:
    instance.view()                                 Получить текущий режим отображения RichTextViewMode
    instance.set_view(RichTextViewMode.EDIT)        Переключится в режим редактирования
    instance.set_view(RichTextViewMode.PREVIEW)     Переключится в режим просмотра
    instance.set_view(RichTextViewMode.VIEW_ONLY)   Переключится в режим отображения (без возможности переключаться в редактор)


"""
from __future__ import annotations

import enum
import html as _html
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, Union

from functools import lru_cache

from PyQt5 import QtGui
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QByteArray, QSize, Qt
from PyQt5.QtGui import QIcon, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer


class RichTextViewMode(enum.Enum):
    """Статусы режима отображения виджета."""

    EDIT = "edit"              # прямое редактирование, toolbar виден
    PREVIEW = "preview"        # предпросмотр, можно вернуться в EDIT
    VIEW_ONLY = "view_only"    # только отображение, редактирование отключено

    @classmethod
    def coerce(cls, value: Union["RichTextViewMode", str, None]) -> "RichTextViewMode":
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.EDIT
        raw = str(value).strip().lower()
        for item in cls:
            if raw in (item.value, item.name.lower()):
                return item
        raise ValueError(f"Неизвестный режим RichTextViewMode: {value!r}")


@dataclass
class RichTextEditorConfig:
    """Базовые конфигурации виджета"""

    initial_view: RichTextViewMode = RichTextViewMode.EDIT  # Базовое состояние при пустом конструкторе

    show_mode_switcher: bool = True                         # показывать переключение на edit/preview
    show_toolbar: bool = True                               # Показывать тулбар редактора (жирность цвет и т д)
    allow_mode_switch: bool = True                          # разрешить менять preview/edit

    # Настройки для разгрузки тулбара (при False секция не видна)
    allow_font_family: bool = True                          # разрешить менять шрифт
    allow_font_size: bool = True                            # разрешить менять размер букв
    allow_text_color: bool = True                           # разрешить менять размер цвет
    allow_background_color: bool = True                     # разрешить менять размер фон
    allow_alignment: bool = True
    allow_lists: bool = True
    allow_links: bool = True
    allow_paste_plain_text: bool = True

    live_preview: bool = False
    preview_update_delay_ms: int = 250          # Раз в сколько обновлять preview представление
    preview_open_external_links: bool = False

    default_font_family: str = "Times New Roman"# Базовый шрифт
    default_font_point_size: int = 14           # базовый размер шрифта
    minimum_height: int = 90
    placeholder_text: str = ""


SVG_ICONS = {
    "bold": """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M8 5H13.2C15.1 5 16.4 6.1 16.4 7.8C16.4 9.1 15.7 10 14.5 10.4C16.1 10.8 17.1 12 17.1 13.7C17.1 15.8 15.5 17 13.2 17H8V5Z"
        fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>
  <path d="M10.5 10.3H13.1M10.5 14.8H13.3"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
</svg>
""",

    "italic": """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M10 5H18M6 19H14M14 5L10 19"
        fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
</svg>
""",

    "underline": """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M7 5V11C7 14.3 9 16 12 16C15 16 17 14.3 17 11V5"
        fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
  <path d="M6 20H18"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
</svg>
""",

    "bullet_list": """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <circle cx="6" cy="7" r="1.4" fill="{color}"/>
  <circle cx="6" cy="12" r="1.4" fill="{color}"/>
  <circle cx="6" cy="17" r="1.4" fill="{color}"/>
  <path d="M10 7H19M10 12H19M10 17H19"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
</svg>
""",

    "numbered_list": """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <text x="4" y="8" font-size="5" font-family="Arial" fill="{color}">1</text>
  <text x="4" y="13" font-size="5" font-family="Arial" fill="{color}">2</text>
  <text x="4" y="18" font-size="5" font-family="Arial" fill="{color}">3</text>
  <path d="M11 7H20M11 12H20M11 17H20"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
</svg>
""",

    "indent_dec": """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M12 6H20M12 11H20M12 16H20"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
  <path d="M9 8L5 12L9 16"
        fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
""",

    "indent_inc": """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M12 6H20M12 11H20M12 16H20"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
  <path d="M5 8L9 12L5 16"
        fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
""",

    "align_left": """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M5 6H19M5 10H15M5 14H19M5 18H13"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
</svg>
""",

    "align_center": """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M5 6H19M8 10H16M5 14H19M9 18H15"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
</svg>
""",

    "align_right": """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M5 6H19M9 10H19M5 14H19M11 18H19"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
</svg>
""",

    "align_justify": """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M5 6H19M5 10H19M5 14H19M5 18H19"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
</svg>
""",

    "text_color": """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M7 17L11 6H13L17 17"
        fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M9 13H15"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
  <path d="M6 20H18"
        stroke="{accent}" stroke-width="3" stroke-linecap="round"/>
</svg>
""",

    "background_color": """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M5 13L13 5L20 12L12 20L5 13Z"
        fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>
  <path d="M8 10L14 16"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
  <path d="M18 15C18 15 20 17.2 20 18.5C20 19.3 19.3 20 18.5 20C17.7 20 17 19.3 17 18.5C17 17.2 18 15 18 15Z"
        fill="{accent}"/>
</svg>
""",

    "clear_format": """
<svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M6 7H14"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
  <path d="M10 7L7 17"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
  <path d="M14 7L17 17"
        stroke="{color}" stroke-width="2" stroke-linecap="round"/>
  <path d="M13 15L19 9"
        stroke="{accent}" stroke-width="2" stroke-linecap="round"/>
  <path d="M16 9H19V12"
        fill="none" stroke="{accent}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
""",
}

@lru_cache(maxsize=256)
def get_svg_icon(
    name: str,
    size: int = 24,
    color: str = "#333333",
    accent: str = "#2F80ED",
) -> QIcon:
    svg = SVG_ICONS[name].format(
        color=color,
        accent=accent,
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))

    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return QIcon(pixmap)


@contextmanager
def _blocked_signals(*objects):
    """Локальный аналог QSignalBlocker, совместимый со старыми сборками PyQt5."""
    previous_states = []
    try:
        for obj in objects:
            if obj is None:
                continue
            previous_states.append((obj, obj.blockSignals(True)))
        yield
    finally:
        for obj, old_state in reversed(previous_states):
            try:
                obj.blockSignals(old_state)
            except RuntimeError:
                pass


class LinkInputDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, selected_text="", title = "Ссылка"):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setModal(True)

        self.url_edit = QtWidgets.QLineEdit(self)
        self.url_edit.setPlaceholderText("https://powerz.ru")

        self.text_edit = QtWidgets.QLineEdit(self)
        self.text_edit.setPlaceholderText("Текст ссылки")

        if selected_text:
            self.text_edit.setText(selected_text)

        form = QtWidgets.QFormLayout()
        form.addRow("URL:", self.url_edit)
        form.addRow("Текст:", self.text_edit)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            parent=self
        )

        self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setText("ОК")
        self.buttons.button(QtWidgets.QDialogButtonBox.Cancel).setText("Отмена")

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.buttons)

        self.url_edit.textChanged.connect(self._sync_ok_state)
        self.text_edit.textChanged.connect(self._sync_ok_state)
        self._sync_ok_state()

    def _sync_ok_state(self):
        url = self.url_edit.text().strip()
        text = self.text_edit.text().strip()

        ok_button = self.buttons.button(QtWidgets.QDialogButtonBox.Ok)
        ok_button.setEnabled(bool(url and text))

    def get_values(self):
        return (
            self.url_edit.text().strip(),
            self.text_edit.text().strip()
        )

class RichTextEditorWidget(QtWidgets.QWidget):
    htmlChanged = QtCore.pyqtSignal(str)
    plainTextChanged = QtCore.pyqtSignal(str)
    modeChanged = QtCore.pyqtSignal(str)
    modificationChanged = QtCore.pyqtSignal(bool)

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        *,
        initial_view: Union[RichTextViewMode, str, None] = None,
        html: str = "",
        plain_text: str = "",
        config: Optional[RichTextEditorConfig] = None,
        # UI настройки
        expanding: bool = False,
        minimum_size_width: int = None,
        minimum_size_height: int = None,
        button_edit_css: str = None,
        button_preview_css: str = None
    ):
        """
            @config         Базовые настройки (цвет/шрифт/размер/фон)
            @html           Базовая разметка для заполнения
            @plain_text     Попытаться конвертировать обычный текст в html (наприме \n в <br/>)

            UI:
            @button_edit_css задать css для кнопки редактировать (toggle)
            @button_preview_css css для кнопки предпросмотра (toggle)
            @expanding       Растянутся по родителю
            @minimum_size_width/minimum_size_height Задать базовую ширину/высоту
        """
        super().__init__(parent)
        self.setObjectName(self.objectName() or "RichTextEditorWidget")
        self.btn_edit_css = button_edit_css
        self.btn_preview_css = button_preview_css
        if expanding:
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding
            )
        if minimum_size_width is not None and minimum_size_height is not None:
            self.setMinimumSize(minimum_size_width, minimum_size_height)
        if config is None:
            view = RichTextViewMode.coerce(initial_view) if initial_view is not None else RichTextViewMode.EDIT
            config = RichTextEditorConfig(initial_view=view)
        elif initial_view is not None:
            config.initial_view = RichTextViewMode.coerce(initial_view)
        else:
            config.initial_view = RichTextViewMode.coerce(config.initial_view)

        self.config = config
        self._view: RichTextViewMode = RichTextViewMode.EDIT
        self._toolbar_sync_locked = False
        self._last_text_color = QtGui.QColor(QtCore.Qt.black)
        self._last_background_color = QtGui.QColor(QtCore.Qt.transparent)

        self._build_widgets()
        self._build_actions()
        self._build_layout()
        self._connect_signals()
        self._apply_initial_style()

        if html:
            self.set_html(html, mark_clean=True, emit_signal=False)
        elif plain_text:
            self.set_plain_text(plain_text, mark_clean=True, emit_signal=False)
        else:
            self.editor.document().setModified(False)
            self._refresh_preview()

        self.set_view(config.initial_view)
        self._sync_toolbar_state()

    def _build_widgets(self) -> None:
        self.mode_bar = QtWidgets.QWidget(self)
        self.mode_bar.setObjectName("RichTextEditorModeBar")
        self.btn_edit = QtWidgets.QToolButton(self.mode_bar)
        self.btn_edit.setObjectName("btn_rich_text_edit_mode")
        self.btn_edit.setText("Редактирование")
        self.btn_edit.setCheckable(True)
        self.btn_edit.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)

        self.btn_preview = QtWidgets.QToolButton(self.mode_bar)
        self.btn_preview.setObjectName("btn_rich_text_preview_mode")
        self.btn_preview.setText("Предпросмотр")
        self.btn_preview.setCheckable(True)
        self.btn_preview.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)

        self.mode_button_group = QtWidgets.QButtonGroup(self)
        self.mode_button_group.setExclusive(True)
        self.mode_button_group.addButton(self.btn_edit)
        self.mode_button_group.addButton(self.btn_preview)

        self.toolbar = QtWidgets.QToolBar(self)
        self.toolbar.setObjectName("RichTextEditorToolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QtCore.QSize(18, 18))

        self.editor = QtWidgets.QTextEdit(self)
        self.editor.setObjectName("rich_text_editor_text_edit")
        self.editor.setAcceptRichText(True)
        self.editor.setMinimumHeight(self.config.minimum_height)
        self.editor.setPlaceholderText(self.config.placeholder_text)

        self.preview = QtWidgets.QTextBrowser(self)
        self.preview.setObjectName("rich_text_editor_preview")
        self.preview.setOpenExternalLinks(self.config.preview_open_external_links)
        self.preview.setMinimumHeight(self.config.minimum_height)
        self.preview.setOpenLinks(False)

        self.preview.anchorClicked.connect(
            lambda url: QtGui.QDesktopServices.openUrl(url)
        )

        self.stack = QtWidgets.QStackedWidget(self)
        self.stack.setObjectName("RichTextEditorStack")
        self.stack.addWidget(self.editor)
        self.stack.addWidget(self.preview)

        self.font_family = QtWidgets.QFontComboBox(self.toolbar)
        self.font_family.setObjectName("cmb_rich_text_font_family")
        self.font_family.setMaximumWidth(210)

        self.font_size = QtWidgets.QComboBox(self.toolbar)
        self.font_size.setObjectName("cmb_rich_text_font_size")
        self.font_size.setEditable(True)
        self.font_size.setMaximumWidth(72)
        for size in (8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72):
            self.font_size.addItem(str(size), size)

        self._preview_timer = QtCore.QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(max(0, int(self.config.preview_update_delay_ms)))
        self._preview_timer.timeout.connect(self._refresh_preview)

    def _build_actions(self) -> None:
        style = self.style()

        self.action_undo = QtWidgets.QAction("↶", self)
        self.action_undo.setObjectName("act_rich_text_undo")
        self.action_undo.setToolTip("Отменить (Ctrl+Z)")
        self.action_undo.setShortcut(QtGui.QKeySequence("Ctrl+Z"))

        self.action_redo = QtWidgets.QAction("↷", self)
        self.action_redo.setObjectName("act_rich_text_redo")
        self.action_redo.setToolTip("Повторить (Ctrl+Y / Ctrl+Shift+Z)")
        self.action_redo.setShortcuts([QtGui.QKeySequence("Ctrl+Y"), QtGui.QKeySequence("Ctrl+Shift+Z")])

        self.action_bold = QtWidgets.QAction("B", self)
        self.action_bold.setObjectName("act_rich_text_bold")
        self.action_bold.setToolTip("Жирный (Ctrl+B)")
        self.action_bold.setCheckable(True)
        self.action_bold.setShortcut(QtGui.QKeySequence("Ctrl+B"))
        bold_font = QtGui.QFont()
        bold_font.setBold(True)
        self.action_bold.setFont(bold_font)

        self.action_italic = QtWidgets.QAction("I", self)
        self.action_italic.setObjectName("act_rich_text_italic")
        self.action_italic.setToolTip("Курсив (Ctrl+I)")
        self.action_italic.setCheckable(True)
        self.action_italic.setShortcut(QtGui.QKeySequence("Ctrl+I"))
        italic_font = QtGui.QFont()
        italic_font.setItalic(True)
        self.action_italic.setFont(italic_font)

        self.action_underline = QtWidgets.QAction("U", self)
        self.action_underline.setObjectName("act_rich_text_underline")
        self.action_underline.setToolTip("Подчёркивание (Ctrl+U)")
        self.action_underline.setCheckable(True)
        self.action_underline.setShortcut(QtGui.QKeySequence("Ctrl+U"))
        underline_font = QtGui.QFont()
        underline_font.setUnderline(True)
        self.action_underline.setFont(underline_font)

        self.action_text_color = QtWidgets.QAction("A", self)
        # self.action_text_color.setIcon(get_svg_icon('text_color', size=24))
        self.action_text_color.setObjectName("act_rich_text_text_color")
        self.action_text_color.setToolTip("Цвет текста")

        self.action_background_color = QtWidgets.QAction("🎨", self)
        # self.action_background_color.setIcon(get_svg_icon('background_color', size=26))
        self.action_background_color.setObjectName("act_rich_text_background_color")
        self.action_background_color.setToolTip("Цвет фона / выделение")

        self.action_clear_format = QtWidgets.QAction("Tx", self)
        self.action_clear_format.setObjectName("act_rich_text_clear_format")
        self.action_clear_format.setToolTip("Очистить форматирование выделения")

        self.action_align_left = QtWidgets.QAction("≡", self)
        self.action_align_left.setIcon(get_svg_icon('align_left', size=26))
        self.action_align_left.setObjectName("act_rich_text_align_left")
        self.action_align_left.setToolTip("Выровнять по левому краю")
        self.action_align_left.setCheckable(True)

        self.action_align_center = QtWidgets.QAction("≡", self)
        self.action_align_center.setIcon(get_svg_icon('align_center', size=26))
        self.action_align_center.setObjectName("act_rich_text_align_center")
        self.action_align_center.setToolTip("Выровнять по центру")
        self.action_align_center.setCheckable(True)

        self.action_align_right = QtWidgets.QAction("≡", self)
        self.action_align_right.setIcon(get_svg_icon('align_right', size=26))
        self.action_align_right.setObjectName("act_rich_text_align_right")
        self.action_align_right.setToolTip("Выровнять по правому краю")
        self.action_align_right.setCheckable(True)

        self.action_align_justify = QtWidgets.QAction("☰", self)
        self.action_align_justify.setIcon(get_svg_icon('align_justify', size=26))
        self.action_align_justify.setObjectName("act_rich_text_align_justify")
        self.action_align_justify.setToolTip("Выровнять по ширине")
        self.action_align_justify.setCheckable(True)

        self.align_group = QtWidgets.QActionGroup(self)
        self.align_group.setExclusive(True)
        for action in (
            self.action_align_left,
            self.action_align_center,
            self.action_align_right,
            self.action_align_justify,
        ):
            self.align_group.addAction(action)

        self.action_bullet_list = QtWidgets.QAction("•", self)
        self.action_bullet_list.setIcon(get_svg_icon('bullet_list', size=26))
        self.action_bullet_list.setObjectName("act_rich_text_bullet_list")
        self.action_bullet_list.setToolTip("Маркированный список")

        self.action_numbered_list = QtWidgets.QAction("1.", self)
        self.action_numbered_list.setIcon(get_svg_icon('numbered_list', size=42))
        self.action_numbered_list.setObjectName("act_rich_text_numbered_list")
        self.action_numbered_list.setToolTip("Нумерованный список")

        self.action_insert_link = QtWidgets.QAction("🔗", self)
        self.action_insert_link.setObjectName("act_rich_text_insert_link")
        self.action_insert_link.setToolTip("Вставить ссылку")
        self.action_insert_link.setShortcut(QtGui.QKeySequence("Ctrl+K"))

        self.action_paste_plain = QtWidgets.QAction("T", self)
        self.action_paste_plain.setObjectName("act_rich_text_paste_plain")
        self.action_paste_plain.setToolTip("Вставить как простой текст (Ctrl+Shift+V)")
        self.action_paste_plain.setShortcut(QtGui.QKeySequence("Ctrl+Shift+V"))

        self.action_copy_html = QtWidgets.QAction("HTML", self)
        self.action_copy_html.setObjectName("act_rich_text_copy_html")
        self.action_copy_html.setToolTip("Скопировать HTML в буфер")
        self.action_copy_html.setVisible(False) # для дебага

        self.action_undo.setIcon(style.standardIcon(QtWidgets.QStyle.SP_ArrowBack))
        self.action_redo.setIcon(style.standardIcon(QtWidgets.QStyle.SP_ArrowForward))

    def _build_layout(self) -> None:
        mode_layout = QtWidgets.QHBoxLayout(self.mode_bar)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(3)
        mode_layout.addWidget(self.btn_edit)
        mode_layout.addWidget(self.btn_preview)
        mode_layout.addStretch(1)

        self.toolbar.addAction(self.action_undo)
        self.toolbar.addAction(self.action_redo)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_bold)
        self.toolbar.addAction(self.action_italic)
        self.toolbar.addAction(self.action_underline)
        self.toolbar.addSeparator()

        if self.config.allow_font_family:
            self.toolbar.addWidget(self.font_family)
        else:
            self.font_family.hide()

        if self.config.allow_font_size:
            self.toolbar.addWidget(self.font_size)
        else:
            self.font_size.hide()

        if self.config.allow_text_color or self.config.allow_background_color:
            self.toolbar.addSeparator()
        if self.config.allow_text_color:
            self.toolbar.addAction(self.action_text_color)
        if self.config.allow_background_color:
            self.toolbar.addAction(self.action_background_color)

        self.toolbar.addAction(self.action_clear_format)

        if self.config.allow_alignment:
            self.toolbar.addSeparator()
            self.toolbar.addAction(self.action_align_left)
            self.toolbar.addAction(self.action_align_center)
            self.toolbar.addAction(self.action_align_right)
            self.toolbar.addAction(self.action_align_justify)

        if self.config.allow_lists:
            self.toolbar.addSeparator()
            self.toolbar.addAction(self.action_bullet_list)
            self.toolbar.addAction(self.action_numbered_list)

        if self.config.allow_links or self.config.allow_paste_plain_text:
            self.toolbar.addSeparator()
        if self.config.allow_links:
            self.toolbar.addAction(self.action_insert_link)
        if self.config.allow_paste_plain_text:
            self.toolbar.addAction(self.action_paste_plain)

        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_copy_html)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(3)
        main_layout.addWidget(self.mode_bar)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.stack, 1)

    def _connect_signals(self) -> None:
        self.btn_edit.clicked.connect(lambda: self.set_view(RichTextViewMode.EDIT))
        self.btn_preview.clicked.connect(lambda: self.set_view(RichTextViewMode.PREVIEW))

        self.action_undo.triggered.connect(self.editor.undo)
        self.action_redo.triggered.connect(self.editor.redo)
        self.editor.undoAvailable.connect(self.action_undo.setEnabled)
        self.editor.redoAvailable.connect(self.action_redo.setEnabled)
        self.action_undo.setEnabled(False)
        self.action_redo.setEnabled(False)

        self.action_bold.toggled.connect(self._set_bold)
        self.action_italic.toggled.connect(self._set_italic)
        self.action_underline.toggled.connect(self._set_underline)
        self.font_family.currentFontChanged.connect(self._set_font_family)
        self.font_size.activated[str].connect(self._set_font_size_from_text)
        self.font_size.lineEdit().editingFinished.connect(self._set_font_size_from_combo_text)

        self.action_text_color.triggered.connect(self._choose_text_color)
        self.action_background_color.triggered.connect(self._choose_background_color)
        self.action_clear_format.triggered.connect(self.clear_selection_format)

        self.action_align_left.triggered.connect(lambda: self._set_alignment(QtCore.Qt.AlignLeft))
        self.action_align_center.triggered.connect(lambda: self._set_alignment(QtCore.Qt.AlignHCenter))
        self.action_align_right.triggered.connect(lambda: self._set_alignment(QtCore.Qt.AlignRight))
        self.action_align_justify.triggered.connect(lambda: self._set_alignment(QtCore.Qt.AlignJustify))

        self.action_bullet_list.triggered.connect(lambda: self._make_list(QtGui.QTextListFormat.ListDisc))
        self.action_numbered_list.triggered.connect(lambda: self._make_list(QtGui.QTextListFormat.ListDecimal))
        self.action_insert_link.triggered.connect(self._insert_link)
        self.action_paste_plain.triggered.connect(self.paste_plain_text)
        self.action_copy_html.triggered.connect(self.copy_html_to_clipboard)

        self.editor.currentCharFormatChanged.connect(self._sync_char_format)
        self.editor.cursorPositionChanged.connect(self._sync_toolbar_state)
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.document().modificationChanged.connect(self.modificationChanged.emit)

    def _apply_initial_style(self) -> None:
        font = QtGui.QFont(self.config.default_font_family, self.config.default_font_point_size)
        self.editor.setFont(font)
        self.preview.setFont(font)
        self.font_family.setCurrentFont(font)
        self._set_combo_size_text(self.config.default_font_point_size)

        self.mode_bar.setVisible(bool(self.config.show_mode_switcher and self.config.allow_mode_switch))
        self.toolbar.setVisible(bool(self.config.show_toolbar))

        btn_edit_css = self.btn_edit_css if self.btn_edit_css else self._mode_button_css()
        btn_preview_css = self.btn_edit_css if self.btn_preview_css else self._mode_button_css()
        self.btn_edit.setStyleSheet(btn_edit_css)
        self.btn_preview.setStyleSheet(btn_preview_css)
        self._set_color_action_css(self.action_text_color, QtGui.QColor(QtCore.Qt.black))
        self._set_color_action_css(self.action_background_color, QtGui.QColor(QtCore.Qt.white))

        self.setStyleSheet(self.styleSheet() + """
        QToolBar#RichTextEditorToolbar {
            spacing: 2px;
            padding: 2px;
            border: 1px solid rgb(220, 220, 220);
            background: rgb(248, 248, 248);
        }
        QTextEdit#rich_text_editor_text_edit,
        QTextBrowser#rich_text_editor_preview {
            border: 1px solid rgb(210, 210, 210);
            background: rgb(255, 255, 255);
            padding: 4px;
        }
        """)

    def set_html(self, html: str, *, mark_clean: bool = True, emit_signal: bool = False) -> None:
        """Загрузить HTML в редактор."""
        html = html or ""
        with _blocked_signals(self.editor):
            self.editor.setHtml(html)
        if mark_clean:
            self.editor.document().setModified(False)
        self._refresh_preview()
        self._sync_toolbar_state()
        if emit_signal:
            self._emit_content_changed()

    def to_html(self) -> str:
        """Вернуть HTML-представление документа."""
        return self.editor.toHtml()

    def set_plain_text(self, text: str, *, mark_clean: bool = True, emit_signal: bool = False) -> None:
        """Загрузить plain text без интерпретации HTML."""
        text = text or ""
        with _blocked_signals(self.editor):
            self.editor.setPlainText(text)
        if mark_clean:
            self.editor.document().setModified(False)
        self._refresh_preview()
        self._sync_toolbar_state()
        if emit_signal:
            self._emit_content_changed()

    def to_plain_text(self) -> str:
        """Вернуть текст без форматирования."""
        return self.editor.toPlainText()

    def set_text_auto(self, text: str, *, mark_clean: bool = True, emit_signal: bool = False) -> None:
        """
        Установить текст с простой авто-логикой:
        если строка похожа на HTML — set_html(), иначе set_plain_text().
        """
        raw = text or ""
        if self._looks_like_html(raw):
            self.set_html(raw, mark_clean=mark_clean, emit_signal=emit_signal)
        else:
            self.set_plain_text(raw, mark_clean=mark_clean, emit_signal=emit_signal)

    def set_view(self, view: Union[RichTextViewMode, str]) -> None:
        """Переключить визуальный режим."""
        view = RichTextViewMode.coerce(view)

        if view == RichTextViewMode.EDIT and self._view == RichTextViewMode.VIEW_ONLY:
            return

        self._view = view

        if view == RichTextViewMode.EDIT:
            self.editor.setReadOnly(False)
            self.stack.setCurrentWidget(self.editor)
            self.toolbar.setVisible(bool(self.config.show_toolbar))
            self.mode_bar.setVisible(bool(self.config.show_mode_switcher and self.config.allow_mode_switch))
            self._set_mode_buttons(edit=True)
            self.editor.setFocus(QtCore.Qt.OtherFocusReason)
        elif view == RichTextViewMode.PREVIEW:
            self._refresh_preview()
            self.editor.setReadOnly(False)
            self.stack.setCurrentWidget(self.preview)
            self.toolbar.setVisible(False)
            self.mode_bar.setVisible(bool(self.config.show_mode_switcher and self.config.allow_mode_switch))
            self._set_mode_buttons(edit=False)
        elif view == RichTextViewMode.VIEW_ONLY:
            self._refresh_preview()
            self.editor.setReadOnly(True)
            self.stack.setCurrentWidget(self.preview)
            self.toolbar.setVisible(False)
            self.mode_bar.setVisible(False)
            self._set_mode_buttons(edit=False)

        self.modeChanged.emit(view.value)

    def view(self) -> RichTextViewMode:
        return self._view

    def mode(self) -> str:
        return self._view.value

    def set_read_only(self, value: bool) -> None:
        if value:
            self.set_view(RichTextViewMode.VIEW_ONLY)
        else:
            self._view = RichTextViewMode.PREVIEW
            self.set_view(RichTextViewMode.EDIT)

    def set_editable(self, value: bool) -> None:
        self.set_read_only(not value)

    def is_read_only(self) -> bool:
        return self._view == RichTextViewMode.VIEW_ONLY or self.editor.isReadOnly()

    def is_modified(self) -> bool:
        return self.editor.document().isModified()

    def set_modified(self, value: bool) -> None:
        self.editor.document().setModified(bool(value))

    def mark_clean(self) -> None:
        self.set_modified(False)

    def clear(self) -> None:
        self.editor.clear()
        self._refresh_preview()
        self._emit_content_changed()

    def focus_editor(self) -> None:
        self.set_view(RichTextViewMode.EDIT)
        self.editor.setFocus(QtCore.Qt.OtherFocusReason)

    def set_placeholder_text(self, text: str) -> None:
        self.editor.setPlaceholderText(text or "")

    def copy_html_to_clipboard(self) -> None:
        mime = QtCore.QMimeData()
        html = self.to_html()
        mime.setHtml(html)
        mime.setText(self.to_plain_text())
        QtWidgets.QApplication.clipboard().setMimeData(mime)

    def paste_plain_text(self) -> None:
        if self.is_read_only():
            return
        text = QtWidgets.QApplication.clipboard().text()
        if text:
            self.editor.insertPlainText(text)

    def clear_selection_format(self) -> None:
        """Очистить символьное форматирование у выделения или у будущего ввода."""
        if self.is_read_only():
            return
        cursor = self.editor.textCursor()
        default_format = QtGui.QTextCharFormat()
        if cursor.hasSelection():
            cursor.setCharFormat(default_format)
            self.editor.setTextCursor(cursor)
        self.editor.setCurrentCharFormat(default_format)
        self._sync_toolbar_state()

    def _merge_char_format(self, fmt: QtGui.QTextCharFormat) -> None:
        if self.is_read_only() or self._toolbar_sync_locked:
            return
        self.editor.mergeCurrentCharFormat(fmt)
        self._sync_toolbar_state()

    def _set_bold(self, checked: bool) -> None:
        if self._toolbar_sync_locked:
            return
        fmt = QtGui.QTextCharFormat()
        fmt.setFontWeight(QtGui.QFont.Bold if checked else QtGui.QFont.Normal)
        self._merge_char_format(fmt)

    def _set_italic(self, checked: bool) -> None:
        if self._toolbar_sync_locked:
            return
        fmt = QtGui.QTextCharFormat()
        fmt.setFontItalic(bool(checked))
        self._merge_char_format(fmt)

    def _set_underline(self, checked: bool) -> None:
        if self._toolbar_sync_locked:
            return
        fmt = QtGui.QTextCharFormat()
        fmt.setFontUnderline(bool(checked))
        self._merge_char_format(fmt)

    def _set_font_family(self, font: QtGui.QFont) -> None:
        if self._toolbar_sync_locked:
            return
        fmt = QtGui.QTextCharFormat()
        fmt.setFontFamily(font.family())
        self._merge_char_format(fmt)

    def _set_font_size_from_combo_text(self) -> None:
        self._set_font_size_from_text(self.font_size.currentText())

    def _set_font_size_from_text(self, text: str) -> None:
        if self._toolbar_sync_locked:
            return
        try:
            value = int(float(str(text).replace(",", ".").strip()))
        except Exception:
            return
        if value <= 0:
            return
        fmt = QtGui.QTextCharFormat()
        fmt.setFontPointSize(value)
        self._merge_char_format(fmt)
        self._set_combo_size_text(value)

    def _choose_text_color(self) -> None:
        if self.is_read_only():
            return
        start_color = self._last_text_color if self._last_text_color.isValid() else QtGui.QColor(QtCore.Qt.black)
        color = QtWidgets.QColorDialog.getColor(start_color, self, "Выберите цвет текста")
        if not color.isValid():
            return
        self._last_text_color = color
        self._set_color_action_css(self.action_text_color, color)
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(color)
        self._merge_char_format(fmt)

    def _choose_background_color(self) -> None:
        if self.is_read_only():
            return
        start_color = self._last_background_color
        if not start_color.isValid() or start_color.alpha() == 0:
            start_color = QtGui.QColor(QtCore.Qt.yellow)
        color = QtWidgets.QColorDialog.getColor(start_color, self, "Выберите цвет фона")
        if not color.isValid():
            return
        self._last_background_color = color
        self._set_color_action_css(self.action_background_color, color)
        fmt = QtGui.QTextCharFormat()
        fmt.setBackground(color)
        self._merge_char_format(fmt)

    def _set_alignment(self, alignment: QtCore.Qt.AlignmentFlag) -> None:
        if self.is_read_only():
            return
        self.editor.setAlignment(alignment)
        self._sync_alignment_state()

    def _make_list(self, style: QtGui.QTextListFormat.Style) -> None:
        if self.is_read_only():
            return
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        list_format = QtGui.QTextListFormat()
        list_format.setStyle(style)
        cursor.createList(list_format)
        cursor.endEditBlock()
        self.editor.setTextCursor(cursor)

    def _insert_link(self) -> None:
        if self.is_read_only():
            return

        cursor = self.editor.textCursor()
        selected_text = cursor.selectedText().strip()

        dlg = LinkInputDialog(self, selected_text=selected_text, title="Добавить ссылку")

        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        url, link_text = dlg.get_values()

        if not url or not link_text:
            return

        fmt = QtGui.QTextCharFormat()
        fmt.setAnchor(True)
        fmt.setAnchorHref(url)
        fmt.setFontUnderline(True)
        fmt.setForeground(QtGui.QColor("#0563C1"))

        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        else:
            cursor.insertText(link_text, fmt)
        self.editor.setTextCursor(cursor)

    def _on_text_changed(self) -> None:
        self._emit_content_changed()
        if self.config.live_preview:
            self._preview_timer.start()

    def _emit_content_changed(self) -> None:
        self.htmlChanged.emit(self.to_html())
        self.plainTextChanged.emit(self.to_plain_text())

    def _refresh_preview(self) -> None:
        self.preview.setHtml(self.editor.toHtml())

    def _sync_toolbar_state(self) -> None:
        self._sync_char_format(self.editor.currentCharFormat())
        self._sync_alignment_state()

    def _sync_char_format(self, fmt: QtGui.QTextCharFormat) -> None:
        if self._toolbar_sync_locked:
            return
        self._toolbar_sync_locked = True
        try:
            self.action_bold.setChecked(fmt.fontWeight() >= QtGui.QFont.Bold)
            self.action_italic.setChecked(fmt.fontItalic())
            self.action_underline.setChecked(fmt.fontUnderline())

            font = fmt.font()
            if font.family():
                self.font_family.setCurrentFont(font)

            point_size = fmt.fontPointSize()
            if point_size <= 0:
                point_size = self.editor.fontPointSize()
            if point_size and point_size > 0:
                self._set_combo_size_text(int(round(point_size)))

            foreground = fmt.foreground()
            if foreground.style() != QtCore.Qt.NoBrush:
                color = foreground.color()
                if color.isValid():
                    self._last_text_color = color
                    self._set_color_action_css(self.action_text_color, color)

            background = fmt.background()
            if background.style() != QtCore.Qt.NoBrush:
                color = background.color()
                if color.isValid():
                    self._last_background_color = color
                    self._set_color_action_css(self.action_background_color, color)
        finally:
            self._toolbar_sync_locked = False

    def _sync_alignment_state(self) -> None:
        if self._toolbar_sync_locked:
            return
        self._toolbar_sync_locked = True
        try:
            alignment = self.editor.alignment()
            self.action_align_left.setChecked(bool(alignment & QtCore.Qt.AlignLeft))
            self.action_align_center.setChecked(bool(alignment & QtCore.Qt.AlignHCenter))
            self.action_align_right.setChecked(bool(alignment & QtCore.Qt.AlignRight))
            self.action_align_justify.setChecked(bool(alignment & QtCore.Qt.AlignJustify))
        finally:
            self._toolbar_sync_locked = False

    def _set_mode_buttons(self, *, edit: bool) -> None:
        with _blocked_signals(self.btn_edit, self.btn_preview):
            self.btn_edit.setChecked(edit)
            self.btn_preview.setChecked(not edit)

    def _set_combo_size_text(self, size: int) -> None:
        text = str(int(size))
        with _blocked_signals(self.font_size):
            idx = self.font_size.findText(text)
            if idx == -1:
                self.font_size.addItem(text, int(size))
                idx = self.font_size.findText(text)
            self.font_size.setCurrentIndex(idx)
            if self.font_size.lineEdit() is not None:
                self.font_size.lineEdit().setText(text)

    def _set_color_action_css(self, action: QtWidgets.QAction, color: QtGui.QColor) -> None:
        button = self.toolbar.widgetForAction(action)
        if button is None:
            return
        name = color.name(QtGui.QColor.HexRgb) if color.isValid() else "#ffffff"
        text_color = "#000000"
        if color.isValid() and color.lightness() < 100:
            text_color = "#ffffff"
        button.setStyleSheet(
            "QToolButton {"
            "border: 1px solid rgb(180, 180, 180);"
            "padding: 2px 5px;"
            f"background-color: {name};"
            f"color: {text_color};"
            "}"
        )

    @staticmethod
    def _mode_button_css() -> str:
        return """
        QToolButton {
            border: 1px solid rgb(190, 190, 190);
            border-radius: 3px;
            padding: 4px 10px;
            background: rgb(245, 245, 245);
        }
        QToolButton:checked {
            background: rgb(225, 240, 220);
            border: 1px solid rgb(150, 190, 145);
        }
        """

    @staticmethod
    def _looks_like_html(text: str) -> bool:
        raw = str(text or "").strip().lower()
        if not raw:
            return False
        return any(tag in raw for tag in ("<html", "<body", "<p", "<span", "<div", "<b", "<i", "<table", "<br"))

    @staticmethod
    def plain_text_to_html(text: str) -> str:
        """Конвертировать обычный текст в html."""
        escaped = _html.escape(text or "").replace("\n", "<br />\n")
        return f"<p>{escaped}</p>"


if __name__ == "__main__":
    import sys
    from project_cust_38 import Cust_Qt as CQT

    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QWidget()
    window.ui = window
    window.setWindowTitle("RichTextEditorWidget demo")
    layout = QtWidgets.QVBoxLayout(window)

    editor = RichTextEditorWidget(
        initial_view=RichTextViewMode.EDIT,
        html="<p>Тест: <b>жирный</b>, <i>курсив</i>, <span style='color:#b00000;'>цвет</span>.</p>",
    )
    layout.addWidget(editor)

    buttons = QtWidgets.QHBoxLayout()
    btn_print_html = QtWidgets.QPushButton("Печать HTML")
    btn_print_html.clicked.connect(lambda: print(editor.to_html()))
    buttons.addWidget(btn_print_html)
    buttons.addStretch(1)
    layout.addLayout(buttons)

    window.resize(900, 520)
    CQT.load_css(window)
    window.show()
    sys.exit(app.exec_())
