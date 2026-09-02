from PyQt5.QtGui import QColor

from app.theme import ThemeDefinition, register_theme_listener, theme_color

CANVAS_BG = theme_color("canvas_bg")
CARD_BG = theme_color("card_bg")
CARD_ROOT_BG = theme_color("card_root_bg")
HEADER_BG = theme_color("canvas_header")
HEADER_ROOT_BG = theme_color("canvas_header_root")
TEXT = theme_color("canvas_text")
MUTED = theme_color("muted")
GRID = theme_color("canvas_grid")
BORDER = theme_color("canvas_border")
ROOT_BORDER = theme_color("root_border")
PORT = theme_color("port")
SAVED = theme_color("saved")
DRAFT = theme_color("draft")
DISABLED = theme_color("canvas_disabled")


_TOKEN_BY_COLOR = {
    "CANVAS_BG": "canvas_bg",
    "CARD_BG": "card_bg",
    "CARD_ROOT_BG": "card_root_bg",
    "HEADER_BG": "canvas_header",
    "HEADER_ROOT_BG": "canvas_header_root",
    "TEXT": "canvas_text",
    "MUTED": "muted",
    "GRID": "canvas_grid",
    "BORDER": "canvas_border",
    "ROOT_BORDER": "root_border",
    "PORT": "port",
    "SAVED": "saved",
    "DRAFT": "draft",
    "DISABLED": "canvas_disabled",
}


def _apply_theme(theme: ThemeDefinition) -> None:
    # QColor instances are mutated in place because graphics modules import
    # these objects directly. Existing cards and lines therefore see the new
    # palette without rebuilding their domain state.
    for name, token in _TOKEN_BY_COLOR.items():
        color = globals()[name]
        color.setNamedColor(theme.colors[token])


register_theme_listener(_apply_theme)


def as_bool(value, default: int = 0) -> bool:
    try:
        return int(value if value is not None else default) == 1
    except (TypeError, ValueError):
        return bool(value)
