from __future__ import annotations

import json
import os
import re
import threading
import datetime as _dt
import random
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List

from PyQt5 import QtCore, QtGui, QtWidgets


# -------------------- defaults --------------------
CARD_ID_DEFAULT = "women_day_2026"
temp = tempfile.gettempdir()
folder = Path(temp) / 'MES'
folder.mkdir(parents=True, exist_ok=True)
FLAG_FILE = folder / "once_flags.json"
print(FLAG_FILE)


# -------------------- storage --------------------
def _safe_read_json(path: Path) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(e)
    return {}


def _safe_write_json(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(e)


def reset_shown_flag(card_id: str = CARD_ID_DEFAULT) -> None:
    """Testing helper: removes stored "shown" flag for card_id."""
    try:
        app_name = QtWidgets.QApplication.applicationName() or "MES"
        flag_key = f"{app_name}:{card_id}"
        flags = _safe_read_json(FLAG_FILE)
        if flag_key in flags:
            del flags[flag_key]
            _safe_write_json(FLAG_FILE, flags)
    except Exception as e:
        print(e)


# -------------------- name --------------------
_SURNAME_SUFFIXES = (
    "ов", "ова", "ев", "ева", "ин", "ина", "ский", "цкий", "ко", "ук", "юк",
    "ov", "ova", "ev", "eva", "in", "ina", "sky", "skiy",
)
_PATRONYMIC_SUFFIXES = ("вич", "вна", "ич", "на")


def _cleanup_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _format_name_for_card(full_name: Optional[str]) -> Optional[str]:
    if not full_name:
        return None
    s = _cleanup_spaces(str(full_name))
    if not s:
        return None
    s = s.replace(",", " ")
    s = _cleanup_spaces(s)
    parts = s.split(" ")
    if not parts:
        return None

    def looks_like_surname(word: str) -> bool:
        w = word.lower()
        return any(w.endswith(suf) for suf in _SURNAME_SUFFIXES)

    def looks_like_patronymic(word: str) -> bool:
        w = word.lower()
        return any(w.endswith(suf) for suf in _PATRONYMIC_SUFFIXES)

    if len(parts) >= 2 and looks_like_surname(parts[0]) and len(parts[1]) >= 2:
        first_name = parts[1]
        patronymic = parts[2] if len(parts) >= 3 and looks_like_patronymic(parts[2]) else ""
    else:
        first_name = parts[0]
        patronymic = parts[1] if len(parts) >= 2 and looks_like_patronymic(parts[1]) else ""

    nice = (first_name + (" " + patronymic if patronymic else "")).strip()
    if len(nice) < 2:
        nice = " ".join(parts[:2]).strip()
    if len(nice) > 28:
        nice = nice[:27] + "…"
    return nice


def _get_user_display_name_fast(timeout_sec: float = 0.8) -> Optional[str]:
    result = {"name": None}

    def worker():
        try:
            from project_cust_38.Cust_Functions import user_full_namre  # type: ignore
            result["name"] = user_full_namre()
        except Exception as e:
            print(e)
            result["name"] = None

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout=timeout_sec)

    full = result["name"]
    if full:
        return _cleanup_spaces(str(full))

    try:
        return _cleanup_spaces(os.getlogin())
    except Exception as e:
        print(e)
        return _cleanup_spaces(os.environ.get("USERNAME") or os.environ.get("USER") or "") or None


# -------------------- text helpers --------------------
def _draw_text_shadow(
    p: QtGui.QPainter,
    rect: QtCore.QRectF,
    text: str,
    font: QtGui.QFont,
    color: QtGui.QColor,
    flags: int,
    shadow_offset: QtCore.QPointF = QtCore.QPointF(2, 2),
    shadow_color: QtGui.QColor = QtGui.QColor(0, 0, 0, 140),
) -> None:
    p.setFont(font)
    p.setPen(shadow_color)
    p.drawText(rect.translated(shadow_offset), flags, text)
    p.setPen(color)
    p.drawText(rect, flags, text)


def _measure_text_height(font: QtGui.QFont, width: float, text: str, flags: int) -> float:
    fm = QtGui.QFontMetricsF(font)
    r = fm.boundingRect(QtCore.QRectF(0, 0, width, 10_000), flags, text)
    return max(0.0, r.height())


def _draw_text_block(
    p: QtGui.QPainter,
    x: float,
    y: float,
    width: float,
    text: str,
    font: QtGui.QFont,
    color: QtGui.QColor,
    flags: int,
    *,
    shadow: bool = True,
    gap_after: float = 10.0,
) -> float:
    text = (text or "").strip()
    if not text:
        return 0.0
    h = _measure_text_height(font, width, text, flags)
    rect = QtCore.QRectF(x, y, width, h)
    if shadow:
        _draw_text_shadow(p, rect, text, font, color, flags)
    else:
        p.setFont(font)
        p.setPen(color)
        p.drawText(rect, flags, text)
    return h + gap_after


def _fit_font_to_height(
    text: str,
    font: QtGui.QFont,
    width: float,
    max_height: float,
    flags: int,
    *,
    min_pt: int = 14,
    step: int = 2,
) -> QtGui.QFont:
    f = QtGui.QFont(font)
    pt = f.pointSize() if f.pointSize() > 0 else 22
    while pt > min_pt:
        f.setPointSize(pt)
        if _measure_text_height(f, width, text, flags) <= max_height:
            return f
        pt -= step
    f.setPointSize(min_pt)
    return f


# -------------------- assets (background images) --------------------
_BG_CACHE: dict[str, Optional[QtGui.QPixmap]] = {}


def _assets_dir() -> Path:
    try:
        return Path(__file__).resolve().parent / "assets"
    except Exception:
        return Path("assets")


def _load_pixmap(path: Path) -> Optional[QtGui.QPixmap]:
    key = str(path)
    if key in _BG_CACHE:
        return _BG_CACHE[key]
    try:
        if path.exists() and path.is_file() and path.stat().st_size > 0:
            pm = QtGui.QPixmap(str(path))
            if not pm.isNull():
                _BG_CACHE[key] = pm
                return pm
    except Exception:
        pass
    _BG_CACHE[key] = None
    return None


def _pick_bg(kind: str, rnd: random.Random) -> Optional[QtGui.QPixmap]:
    """
    Deterministic pick based on rnd (seeded by card_id).
    kind: "art" or "basic"
    """
    if kind == "art":
        names = ["bg_art_1.png", "bg_art_2.png", "bg_art_3.png"]
    else:
        names = ["bg_basic_1.png", "bg_basic_2.png"]

    start = rnd.randrange(len(names))
    ad = _assets_dir()
    for i in range(len(names)):
        name = names[(start + i) % len(names)]
        pm = _load_pixmap(ad / name)
        if pm:
            return pm
    return None


def _draw_bg_image(p: QtGui.QPainter, rect: QtCore.QRectF, pm: QtGui.QPixmap, *, darken: bool) -> None:
    p.save()
    p.setClipRect(rect)
    p.drawPixmap(rect.toRect(), pm)

    if darken:
        g = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        g.setColorAt(0.0, QtGui.QColor(0, 0, 0, 25))
        g.setColorAt(1.0, QtGui.QColor(0, 0, 0, 75))
        p.fillRect(rect, g)
    else:
        g = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        g.setColorAt(0.0, QtGui.QColor(255, 255, 255, 10))
        g.setColorAt(1.0, QtGui.QColor(0, 0, 0, 20))
        p.fillRect(rect, g)

    p.restore()


# -------------------- art helpers (bouquet) --------------------
def _ellipse_rotated(p: QtGui.QPainter, cx: float, cy: float, rx: float, ry: float, ang: float) -> None:
    p.save()
    p.translate(cx, cy)
    p.rotate(ang)
    p.drawEllipse(QtCore.QRectF(-rx, -ry, rx * 2, ry * 2))
    p.restore()


def _draw_tulip(p: QtGui.QPainter, x: float, y: float, s: float, col: QtGui.QColor) -> None:
    p.setBrush(QtGui.QBrush(col))
    p.setPen(QtCore.Qt.NoPen)
    _ellipse_rotated(p, x, y, 18 * s, 28 * s, -18)
    _ellipse_rotated(p, x, y, 18 * s, 28 * s, 0)
    _ellipse_rotated(p, x, y, 18 * s, 28 * s, 18)

    p.setBrush(QtGui.QBrush(QtGui.QColor(255, 240, 200, 170)))
    _ellipse_rotated(p, x, y + 6 * s, 7 * s, 10 * s, 0)

    p.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 70)))
    _ellipse_rotated(p, x - 7 * s, y - 6 * s, 5 * s, 9 * s, -10)


def _draw_bouquet(p: QtGui.QPainter, rect: QtCore.QRectF, rnd: random.Random, *, bg_pm: Optional[QtGui.QPixmap] = None) -> None:
    if bg_pm:
        _draw_bg_image(p, rect, bg_pm, darken=False)
    else:
        bg = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        bg.setColorAt(0.0, QtGui.QColor(255, 120, 190, 60))
        bg.setColorAt(1.0, QtGui.QColor(255, 220, 245, 15))
        p.fillRect(rect, bg)

    stem_pen = QtGui.QPen(QtGui.QColor(120, 205, 150, 200))
    stem_pen.setWidth(4)
    stem_pen.setCapStyle(QtCore.Qt.RoundCap)
    p.setPen(stem_pen)
    p.setBrush(QtCore.Qt.NoBrush)

    base_x = rect.left() + rect.width() * 0.35
    base_y = rect.bottom() - rect.height() * 0.10

    flower_colors = [
        QtGui.QColor(255, 90, 160, 240),
        QtGui.QColor(255, 130, 200, 240),
        QtGui.QColor(220, 80, 255, 230),
        QtGui.QColor(255, 170, 120, 240),
        QtGui.QColor(255, 70, 120, 245),
    ]

    tops = []
    for _ in range(11):
        x1 = base_x + rnd.uniform(-80, 140)
        y1 = base_y - rnd.uniform(200, 360)
        cx = rect.left() + rect.width() * (0.20 + 0.65 * rnd.random())
        cy = rect.top() + rect.height() * (0.20 + 0.30 * rnd.random())

        path = QtGui.QPainterPath(QtCore.QPointF(base_x, base_y))
        path.cubicTo(
            QtCore.QPointF(base_x + (cx - base_x) * 0.35, base_y - 80),
            QtCore.QPointF(cx, cy + 60),
            QtCore.QPointF(x1, y1),
        )
        p.drawPath(path)
        tops.append((x1, y1))

    # leaves
    p.setPen(QtCore.Qt.NoPen)
    p.setBrush(QtGui.QBrush(QtGui.QColor(110, 210, 150, 100)))
    for _ in range(9):
        lx = rect.left() + rect.width() * (0.20 + 0.70 * rnd.random())
        ly = rect.top() + rect.height() * (0.52 + 0.40 * rnd.random())
        _ellipse_rotated(p, lx, ly, 18, 60, rnd.uniform(-35, 35))

    # flowers
    for (fx, fy) in tops:
        s = rnd.uniform(1.0, 1.8)
        col = rnd.choice(flower_colors)
        _draw_tulip(p, fx, fy, s, col)

    # sparkles
    for _ in range(70):
        x = rect.left() + rect.width() * rnd.random()
        y = rect.top() + rect.height() * rnd.random()
        r = rnd.uniform(2, 7)
        p.setBrush(QtGui.QBrush(QtGui.QColor(255, 235, 170, rnd.randint(18, 70))))
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(QtCore.QPointF(x, y), r, r)


# -------------------- theme detection --------------------
def _is_women_day(text: str) -> bool:
    t = (text or "").lower()
    return ("8" in t and "мар" in t) or ("марта" in t) or ("8 марта" in t) or ("women" in t)


def _theme8(card_id: str, title: str, headline: str) -> bool:
    return _is_women_day(card_id) or _is_women_day(title) or _is_women_day(headline)


# -------------------- pixmap generation --------------------
def generate_greeting_pixmap(
    *,
    style: str,
    card_id: str,
    name: Optional[str],
    title: str,
    headline: str,
    body_lines: List[str],
    footer: Optional[str] = None,
    size: Tuple[int, int] = (1920, 1080),
) -> QtGui.QPixmap:
    w, h = size
    pm = QtGui.QPixmap(w, h)
    pm.fill(QtCore.Qt.transparent)

    p = QtGui.QPainter(pm)
    p.setRenderHints(
        QtGui.QPainter.Antialiasing
        | QtGui.QPainter.TextAntialiasing
        | QtGui.QPainter.SmoothPixmapTransform
    )

    bg = QtCore.QRectF(0, 0, w, h)
    grad = QtGui.QLinearGradient(0, 0, w, h)
    grad.setColorAt(0.0, QtGui.QColor(12, 12, 16))
    grad.setColorAt(1.0, QtGui.QColor(30, 30, 38))
    p.fillRect(bg, grad)

    rnd = random.Random(abs(hash(card_id)) % (2**32))

    for _ in range(80):
        x = rnd.randint(0, w)
        y = rnd.randint(0, h)
        r = rnd.randint(8, 34)
        col = QtGui.QColor(255, 210, 60, rnd.randint(12, 55))
        p.setBrush(QtGui.QBrush(col))
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(QtCore.QPointF(x, y), r, r)

    card_margin = 90
    card_rect = QtCore.QRectF(card_margin, card_margin, w - 2 * card_margin, h - 2 * card_margin)
    card_round = 28.0

    theme8 = _theme8(card_id, title, headline)
    card_grad = QtGui.QLinearGradient(card_rect.topLeft(), card_rect.bottomRight())
    if theme8:
        card_grad.setColorAt(0.0, QtGui.QColor(38, 18, 32, 235))
        card_grad.setColorAt(1.0, QtGui.QColor(14, 10, 18, 235))
    else:
        card_grad.setColorAt(0.0, QtGui.QColor(24, 26, 31, 235))
        card_grad.setColorAt(1.0, QtGui.QColor(10, 10, 12, 235))

    p.setBrush(QtGui.QBrush(card_grad))
    p.setPen(QtCore.Qt.NoPen)
    p.drawRoundedRect(card_rect, card_round, card_round)

    pen = QtGui.QPen(QtGui.QColor(255, 210, 60, 210))
    pen.setWidth(3)
    p.setPen(pen)
    p.setBrush(QtCore.Qt.NoBrush)
    p.drawRoundedRect(card_rect.adjusted(2, 2, -2, -2), card_round, card_round)

    tag_font = QtGui.QFont("Segoe UI", 16, QtGui.QFont.Bold)
    tag_rect = QtCore.QRectF(card_rect.left() + 28, card_rect.top() + 22, 240, 40)
    _draw_text_shadow(
        p, tag_rect, "",
        tag_font,
        QtGui.QColor(255, 210, 60),
        int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter),
        shadow_offset=QtCore.QPointF(1.5, 1.5),
    )

    nice_name = _format_name_for_card(name)
    name_line = f"{nice_name}!" if nice_name else "Коллега!"

    f_left = int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
    f_left_wrap = int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop | QtCore.Qt.TextWordWrap)

    if theme8 and style.lower() == "art":
        bg_pm = _pick_bg("art", rnd)
        ill_rect = QtCore.QRectF(
            card_rect.left() + 30,
            card_rect.top() + 70,
            card_rect.width() - 60,
            card_rect.height() - 140,
        )
        if bg_pm:
            _draw_bg_image(p, ill_rect, bg_pm, darken=False)
        _draw_bouquet(p, ill_rect, rnd, bg_pm=None)  # bouquet paints its own fill if bg_pm None; here we already filled

        panel_w = min(760.0, card_rect.width() * 0.46)
        panel_rect = QtCore.QRectF(
            card_rect.right() - panel_w - 60,
            card_rect.top() + 140,
            panel_w,
            card_rect.height() - 280,
        )

        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QBrush(QtGui.QColor(10, 10, 12, 175)))
        p.drawRoundedRect(panel_rect, 22, 22)

        pen2 = QtGui.QPen(QtGui.QColor(255, 210, 60, 170))
        pen2.setWidth(2)
        p.setPen(pen2)
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(panel_rect.adjusted(1, 1, -1, -1), 22, 22)

        pad = 34.0
        x = panel_rect.left() + pad
        y = panel_rect.top() + pad
        wtxt = panel_rect.width() - 2 * pad

        name_font = QtGui.QFont("Segoe UI", 30, QtGui.QFont.DemiBold)
        y += _draw_text_block(p, x, y, wtxt, name_line, name_font, QtGui.QColor(255, 210, 60), f_left, gap_after=10)

        head_font = QtGui.QFont("Segoe UI", 44, QtGui.QFont.Bold)
        y += _draw_text_block(p, x, y, wtxt, headline, head_font, QtGui.QColor(245, 245, 245), f_left_wrap, gap_after=14)

        body_text = "\n".join(body_lines).strip() if body_lines else ""
        footer_h = 34.0
        available = max(80.0, panel_rect.bottom() - (y + pad) - footer_h)
        body_font_base = QtGui.QFont("Segoe UI", 22, QtGui.QFont.Normal)
        body_font = _fit_font_to_height(body_text, body_font_base, wtxt, available, f_left_wrap, min_pt=16)

        y += _draw_text_block(p, x, y, wtxt, body_text, body_font, QtGui.QColor(235, 235, 235), f_left_wrap, gap_after=10)

        if footer is None:
            footer = "Команда MES"
        footer_font = QtGui.QFont("Segoe UI", 14, QtGui.QFont.Normal)
        footer_rect = QtCore.QRectF(x, panel_rect.bottom() - pad - 26, wtxt, 24)
        _draw_text_shadow(
            p, footer_rect, footer,
            footer_font,
            QtGui.QColor(185, 185, 185),
            int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter),
            shadow_offset=QtCore.QPointF(1.2, 1.2),
        )

    elif theme8 and style.lower() == "basic":
        # bg_pm = _pick_bg("basic", rnd)

        ill_w = 560.0
        ill_rect = QtCore.QRectF(
            card_rect.right() - ill_w - 40,
            card_rect.top() + 90,
            ill_w,
            card_rect.height() - 180,
        )
        # _draw_bouquet(p, ill_rect, rnd, bg_pm=bg_pm)
        _draw_bouquet(p, ill_rect, rnd)

        # text block area with contrast
        text_rect = QtCore.QRectF(
            card_rect.left() + 40,
            card_rect.top() + 90,
            card_rect.width() - ill_w - 120,
            card_rect.height() - 180,
        )
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QBrush(QtGui.QColor(10, 10, 12, 125)))
        p.drawRoundedRect(text_rect, 18, 18)

        x = text_rect.left() + 70
        y = text_rect.top() + 40
        wtxt = text_rect.width() - 140

        name_font = QtGui.QFont("Segoe UI", 34, QtGui.QFont.DemiBold)
        y += _draw_text_block(p, x, y, wtxt, name_line, name_font, QtGui.QColor(255, 210, 60), f_left, gap_after=10)

        head_font = QtGui.QFont("Segoe UI", 52, QtGui.QFont.Bold)
        y += _draw_text_block(p, x, y, wtxt, headline, head_font, QtGui.QColor(245, 245, 245), f_left_wrap, gap_after=18)

        body_text = "\n".join(body_lines).strip() if body_lines else ""
        footer_space = 60.0
        available = max(120.0, text_rect.bottom() - (y + 20) - footer_space)
        body_font_base = QtGui.QFont("Segoe UI", 24, QtGui.QFont.Normal)
        body_font = _fit_font_to_height(body_text, body_font_base, wtxt, available, f_left_wrap, min_pt=16)

        y += _draw_text_block(p, x, y, wtxt, body_text, body_font, QtGui.QColor(235, 235, 235), f_left_wrap, gap_after=10)

        if footer is None:
            footer = "Команда MES"
        footer_font = QtGui.QFont("Segoe UI", 14, QtGui.QFont.Normal)
        footer_rect = QtCore.QRectF(x, text_rect.bottom() - 40, wtxt, 24)
        _draw_text_shadow(
            p, footer_rect, footer, footer_font, QtGui.QColor(185, 185, 185),
            int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter),
            shadow_offset=QtCore.QPointF(1.2, 1.2),
        )

    else:
        # Generic (non-8march)
        x = card_rect.left() + 90
        y = card_rect.top() + 160
        wtxt = card_rect.width() - 180

        name_font = QtGui.QFont("Segoe UI", 34, QtGui.QFont.DemiBold)
        y += _draw_text_block(p, x, y, wtxt, name_line, name_font, QtGui.QColor(255, 210, 60), f_left, gap_after=10)

        head_font = QtGui.QFont("Segoe UI", 60, QtGui.QFont.Bold)
        y += _draw_text_block(p, x, y, wtxt, headline, head_font, QtGui.QColor(245, 245, 245), f_left_wrap, gap_after=18)

        body_text = "\n".join(body_lines).strip() if body_lines else ""
        available = max(120.0, card_rect.bottom() - y - 120)
        body_font_base = QtGui.QFont("Segoe UI", 26, QtGui.QFont.Normal)
        body_font = _fit_font_to_height(body_text, body_font_base, wtxt, available, f_left_wrap, min_pt=16)

        y += _draw_text_block(p, x, y, wtxt, body_text, body_font, QtGui.QColor(235, 235, 235), f_left_wrap, gap_after=10)

        if footer is None:
            footer = _dt.datetime.now().strftime("%d.%m.%Y")
        footer_font = QtGui.QFont("Segoe UI", 14, QtGui.QFont.Normal)
        footer_rect = QtCore.QRectF(x, card_rect.bottom() - 80, wtxt, 24)
        _draw_text_shadow(
            p, footer_rect, footer, footer_font, QtGui.QColor(185, 185, 185),
            int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter),
            shadow_offset=QtCore.QPointF(1.2, 1.2),
        )

    p.end()
    return pm


# -------------------- dialog --------------------
class GreetingCardDialog(QtWidgets.QDialog):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, title: str = "Поздравление"):
        super().__init__(parent)

        from project_cust_38.dialog import Ui_Dialog  # type: ignore

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.setWindowTitle(title)
        self.setWindowModality(QtCore.Qt.ApplicationModal)

        self._pixmap_src: Optional[QtGui.QPixmap] = None
        self._prepare_layout_for_card()

        self.resize(920, 524)

        if hasattr(self.ui, "btn_ok"):
            self.ui.btn_ok.setText("Закрыть")
            self.ui.btn_ok.clicked.connect(self.accept)

        if hasattr(self.ui, "lbl_img"):
            self.ui.lbl_img.setAlignment(QtCore.Qt.AlignCenter)
            sp = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            self.ui.lbl_img.setSizePolicy(sp)
            self.ui.lbl_img.setMinimumSize(480, 360)
            self.ui.lbl_img.setText("")

        if hasattr(self.ui, "fr_figures"):
            sp = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            self.ui.fr_figures.setSizePolicy(sp)

    def _prepare_layout_for_card(self) -> None:
        if hasattr(self.ui, "cmb_action"):
            self.ui.cmb_action.setVisible(False)

        if hasattr(self.ui, "layoutWidget"):
            self.ui.layoutWidget.setVisible(False)

        if hasattr(self.ui, "fr_groups"):
            self.ui.fr_groups.setVisible(False)

        for name in (
            "splitter_2",
            "tbl_fields",
            "tbl_add_gr_field",
            "tbl_add_res_field",
            "groupBox",
            "groupBox_2",
            "btn_add_gr_field",
            "btn_del_gr_field",
            "btn_add_res_field",
            "btn_del_res_field",
            "btn_reset",
        ):
            w = getattr(self.ui, name, None)
            if isinstance(w, QtWidgets.QWidget):
                w.setVisible(False)

    def showEvent(self, e: QtGui.QShowEvent) -> None:
        super().showEvent(e)
        self._fix_splitters()
        QtCore.QTimer.singleShot(0, self._apply_scaled_pixmap)

    def _fix_splitters(self) -> None:
        try:
            if hasattr(self.ui, "splitter_4"):
                self.ui.splitter_4.setSizes([10_000, 0])
            if hasattr(self.ui, "splitter_3"):
                self.ui.splitter_3.setSizes([10_000, 0])
        except Exception:
            pass

    def set_pixmap(self, pm: QtGui.QPixmap) -> None:
        self._pixmap_src = pm
        self._apply_scaled_pixmap()

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        super().resizeEvent(e)
        self._apply_scaled_pixmap()

    def _apply_scaled_pixmap(self) -> None:
        if not self._pixmap_src or self._pixmap_src.isNull():
            return
        if not hasattr(self.ui, "lbl_img"):
            return
        label: QtWidgets.QLabel = self.ui.lbl_img
        target = label.size()
        if target.width() < 10 or target.height() < 10:
            return
        scaled = self._pixmap_src.scaled(target, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        label.setPixmap(scaled)


def try_show_once(
    parent: Optional[QtWidgets.QWidget] = None,
    *,
    style: str = "art",
    card_id: str = CARD_ID_DEFAULT,
    title: str = "С 8 Марта!",
    headline: Optional[str] = None,
    body_lines: Optional[List[str]] = None,
    footer: Optional[str] = None,
    force: bool = False,
    name_timeout_sec: float = 0.8,
        fio: str = None
) -> bool:
    """Returns True if shown, False if skipped."""
    if os.environ.get("MES_DISABLE_GREETING") == "1":
        return False

    try:
        display_name = fio

        flag_key = f"{fio}:{card_id}"
        flags = _safe_read_json(FLAG_FILE)
        if (not force) and bool(flags.get(flag_key)):
            return False

        # display_name = _get_user_display_name_fast(timeout_sec=name_timeout_sec)


        if headline is None:
            headline = "С 8 Марта!" if _theme8(card_id, title, title) else "Поздравляем!"

        if body_lines is None:
            if _theme8(card_id, title, headline):
                body_lines = [
                    "Пусть весна принесёт тепло, радость и вдохновение.",
                    "Желаем здоровья, гармонии и лёгких рабочих дней.",
                    "С праздником! 🌷",
                ]
                if footer is None:
                    footer = "Команда MES"
            else:
                body_lines = ["Пусть всё складывается легко,", "а техкарты — без ошибок 😊"]

        pm = generate_greeting_pixmap(
            style=style,
            card_id=card_id,
            name=display_name,
            title=title,
            headline=headline,
            body_lines=body_lines,
            footer=footer,
            size=(1920, 1080),
        )

        dlg = GreetingCardDialog(parent=parent, title=title)
        dlg.set_pixmap(pm)
        dlg.exec_()

        if not force:
            flags[flag_key] = True
            _safe_write_json(FLAG_FILE, flags)

        return True

    except Exception as e:
        print(e)
        return False
