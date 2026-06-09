from __future__ import annotations

import math
import os
import re
from datetime import date
from typing import Any, Iterable

from project_cust_38 import Cust_Functions as F # noqa

FREQ_LABELS: list[str] = ["31,5", "63", "125", "250", "500", "1000", "2000", "4000", "8000", "LАЭкв"]

PRESSURE_BEFORE_KEYS: list[str] = [
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_31_5_2",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_63_2",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_125_2",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_250_2",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_500_2",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_1000_2",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_2000_2",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_4000_2",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_8000_2",
    "ak_polosa_a_2",
]

PRESSURE_AFTER_KEYS: list[str] = [
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_31_5_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_63_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_125_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_250_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_500_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_1000_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_2000_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_4000_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_8000_5",
    "ak_polosa_a_5",
]

POWER_TUBE_KEYS: list[str] = [
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_31_5",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_63",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_125",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_250",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_500",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_1000",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_2000",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_4000",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_8000",
    "ak_polosa_a",
]

POWER_SILENCER_KEYS: list[str] = [
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_31_5_4",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_63_4",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_125_4",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_250_4",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_500_4",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_1000_4",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_2000_4",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_4000_4",
    "ak_srednegeometricheskaya_chastota_oktavnyh_polos_gc_8000_4",
    "ak_polosa_a_4",
]

BAD_FILE_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def convert_html_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", ".")
        if not text:
            return None
        try:
            num = float(text)
        except Exception:
            return None
        if math.isnan(num) or math.isinf(num):
            return None
        return num
    return None


def format_num(value: Any, accuracy: int = 1, empty: str = "-") -> str:
    num = convert_html_float(value)
    if num is None:
        if value is None:
            return empty
        text = str(value).strip()
        return text if text else empty
    if abs(num - round(num)) < 10 ** (-(accuracy + 1)):
        return str(int(round(num)))
    return f"{num:.{accuracy}f}".replace(".", ",")


def unpack_value_by_key(source: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in source and source.get(key) not in (None, ""):
            return source.get(key)
    return default


def get_num_series(calculated: dict[str, Any], keys: Iterable[str]) -> list[float | None]:
    return [convert_html_float(calculated.get(key)) for key in keys]

def build_nomen_name(input_values: dict[str, Any]) -> str:
    sreda = str(unpack_value_by_key(input_values, "sreda", default="") or "")
    prefix = "ШСГ"
    if sreda == "Пар":
        prefix = "ШПС"
    elif sreda == "Воздух":
        prefix = "ШСВ"

    project_no = str(unpack_value_by_key(input_values, "nomer_proekta", default="") or "").strip()
    pos = unpack_value_by_key(input_values, "pozicii", default="")
    try:
        pos_text = f"{int(float(str(pos).replace(',', '.'))):02d}"
    except Exception:
        pos_text = str(pos or "").strip() or "01"
    if project_no:
        return f"{prefix}.{project_no}.{pos_text}"
    return f"{prefix}.{pos_text}"


def register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        # (
        #     r"Z:\Data\fonts\DejaVuSans.ttf",
        #     r"Z:\Data\fonts\DejaVuSans-Bold.ttf",
        #     "DejaVuSans",
        #     "DejaVuSans-Bold",
        # ),
        (
            r"Z:\Data\fonts\LiberationSans-Regular.ttf",
            r"Z:\Data\fonts\LiberationSans-Bold.ttf",
            "LiberationSans",
            "LiberationSans-Bold",
        ),
        # (
        #     r"Z:\Data\fonts\TFlex.ttf",
        #     r"Z:\Data\fonts\TFlex-Bold.ttf",
        #     "TFlex",
        #     "TFlex-Bold",
        # ),
    ]
    for regular, bold, regular_name, bold_name in candidates:
        if os.path.exists(regular) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont(regular_name, regular))
            pdfmetrics.registerFont(TTFont(bold_name, bold))
            return regular_name, bold_name
    return "Helvetica", "Helvetica-Bold"


def draw_text(c, text: Any, x: float, y: float, *, font: str, size: float = 8, bold_font: str | None = None,
              bold: bool = False, align: str = "left", max_width: float | None = None, leading: float | None = None):
    from reportlab.pdfbase import pdfmetrics

    text = format_num(text, empty="") if not isinstance(text, str) else text
    text = text or ""
    font_name = bold_font if bold and bold_font else font
    c.setFont(font_name, size)
    if max_width is None or pdfmetrics.stringWidth(text, font_name, size) <= max_width:
        if align == "center" and max_width is not None:
            c.drawCentredString(x + max_width / 2, y, text)
        elif align == "right" and max_width is not None:
            c.drawRightString(x + max_width, y, text)
        else:
            c.drawString(x, y, text)
        return

    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        probe = word if not cur else f"{cur} {word}"
        if pdfmetrics.stringWidth(probe, font_name, size) <= max_width:
            cur = probe
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)

    line_h = leading or size * 1.18
    for i, line in enumerate(lines[:4]):
        yy = y - i * line_h
        if align == "center":
            c.drawCentredString(x + max_width / 2, yy, line)
        elif align == "right":
            c.drawRightString(x + max_width, yy, line)
        else:
            c.drawString(x, yy, line)


def draw_cell(c, x: float, y: float, w: float, h: float, text: Any = "", *, font: str, bold_font: str,
              size: float = 7.2, bold: bool = False, align: str = "left", valign: str = "middle", fill=None,
              stroke=1, pad: float = 3.0, max_lines: int = 3):
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics

    if fill is not None:
        c.setFillColor(fill)
        c.rect(x, y, w, h, fill=1, stroke=0)
    if stroke:
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.45)
        c.rect(x, y, w, h, fill=0, stroke=1)

    text = format_num(text, empty="") if not isinstance(text, str) else text
    text = text or ""
    font_name = bold_font if bold else font
    c.setFont(font_name, size)

    max_width = max(1, w - 2 * pad)
    words = text.split()
    lines: list[str] = []
    cur = ""
    if words:
        for word in words:
            probe = word if not cur else f"{cur} {word}"
            if pdfmetrics.stringWidth(probe, font_name, size) <= max_width:
                cur = probe
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    else:
        lines = [text]
    lines = lines[:max_lines]

    line_h = size * 1.15
    total_h = len(lines) * line_h
    if valign == "top":
        yy = y + h - pad - size
    elif valign == "bottom":
        yy = y + pad + total_h - line_h
    else:
        yy = y + (h + total_h) / 2 - line_h

    c.setFillColor(colors.black)
    for line in lines:
        if align == "center":
            c.drawCentredString(x + w / 2, yy, line)
        elif align == "right":
            c.drawRightString(x + w - pad, yy, line)
        else:
            c.drawString(x + pad, yy, line)
        yy -= line_h


def draw_section_header(c, x: float, y: float, w: float, h: float, title: str, *, font: str, bold_font: str):
    from reportlab.lib import colors

    draw_cell(c, x, y, w, h, title, font=font, bold_font=bold_font, size=8.5, bold=True, align="center", fill=colors.HexColor("#EDEDED"))


def draw_column_table(c, x: float, y: float, w: float, rows: list[tuple[str, Any, str]], *, font: str, bold_font: str,
                      title: str, row_h: float = 15.5) -> float:
    draw_section_header(c, x, y + len(rows) * row_h, w, 17, title, font=font, bold_font=bold_font)
    label_w = w * 0.66
    val_w = w * 0.22
    dim_w = w - label_w - val_w
    for i, (label, val, dim) in enumerate(rows):
        yy = y + (len(rows) - 1 - i) * row_h
        size_value = 5
        if F.valm(val):
            size_value = 7
        draw_cell(c, x, yy, label_w, row_h, label, font=font, bold_font=bold_font, size=6.8)
        draw_cell(c, x + label_w, yy, val_w, row_h, format_num(val), font=font, bold_font=bold_font, size=size_value, bold=True, align="center")
        draw_cell(c, x + label_w + val_w, yy, dim_w, row_h, dim, font=font, bold_font=bold_font, size=6.8, align="center")
    return 17 + len(rows) * row_h


def draw_series_table(c, x: float, y: float, w: float, *, title: str, row1_label: str, row2_label: str,
                      row1: list[float | None], row2: list[float | None], font: str, bold_font: str) -> float:
    from reportlab.lib import colors

    header_h = 16
    row_h = 16
    title_h = 17
    label_w = 98
    col_w = (w - label_w) / len(FREQ_LABELS)
    total_h = title_h + header_h + 2 * row_h

    draw_section_header(c, x, y + total_h - title_h, w, title_h, title, font=font, bold_font=bold_font)
    yy = y + 2 * row_h
    draw_cell(c, x, yy, label_w, header_h, "Показатель", font=font, bold_font=bold_font, size=6.3, bold=True, align="center", fill=colors.HexColor("#F7F7F7"))
    for i, label in enumerate(FREQ_LABELS):
        draw_cell(c, x + label_w + i * col_w, yy, col_w, header_h, label, font=font, bold_font=bold_font, size=5.8, bold=True, align="center", fill=colors.HexColor("#F7F7F7"))

    for r, (label, values) in enumerate(((row1_label, row1), (row2_label, row2))):
        yy = y + (1 - r) * row_h
        draw_cell(c, x, yy, label_w, row_h, label, font=font, bold_font=bold_font, size=5.9, max_lines=2)
        for i, value in enumerate(values):
            draw_cell(c, x + label_w + i * col_w, yy, col_w, row_h, format_num(value), font=font, bold_font=bold_font, size=6.4, align="center")
    return total_h


def draw_twin_chart(c, x: float, y: float, w: float, h: float, before: list[float | None], after: list[float | None], *, font: str, bold_font: str):
    from reportlab.lib import colors

    draw_section_header(c, x, y + h - 18, w, 18, "До / после установки ШГ", font=font, bold_font=bold_font)
    plot_y = y + 30
    plot_h = h - 58
    label_w = w / len(FREQ_LABELS)
    numeric = [v for v in [*before, *after] if isinstance(v, (int, float))]
    max_v = max(numeric) if numeric else 1
    min_v = min(numeric) if numeric else 0
    spread = max(max_v - min_v, 1.0)

    c.setStrokeColor(colors.HexColor("#BFBFBF"))
    c.setLineWidth(0.3)
    for i in range(5):
        gy = plot_y + i * plot_h / 4
        c.line(x + 12, gy, x + w - 8, gy)

    before_color = colors.HexColor("#4F81BD")
    after_color = colors.HexColor("#9BBB59")
    c.setFont(font, 6)
    draw_cell(c, x + w - 122, y + h - 16, 8, 8, "", font=font, bold_font=bold_font, fill=before_color, stroke=0)
    c.drawString(x + w - 110, y + h - 14, "до установки")
    draw_cell(c, x + w - 62, y + h - 16, 8, 8, "", font=font, bold_font=bold_font, fill=after_color, stroke=0)
    c.drawString(x + w - 50, y + h - 14, "после")

    for i, label in enumerate(FREQ_LABELS):
        cx = x + i * label_w + label_w / 2
        vals = (before[i] if i < len(before) else None, after[i] if i < len(after) else None)
        bar_w = min(12, label_w * 0.24)
        gap = 3
        for j, value in enumerate(vals):
            if value is None:
                bh = 1
            else:
                bh = 6 + ((value - min_v) / spread) * (plot_h - 8)
            bx = cx - bar_w - gap / 2 if j == 0 else cx + gap / 2
            c.setFillColor(before_color if j == 0 else after_color)
            c.rect(bx, plot_y, bar_w, bh, fill=1, stroke=0)
            c.setFillColor(colors.black)
            c.setFont(font, 5.4)
            c.drawCentredString(bx + bar_w / 2, plot_y + bh + 2, format_num(value))

        c.setFont(bold_font, 5.8)
        c.drawCentredString(cx, y + 16, label)
        delta = None
        if vals[0] is not None and vals[1] is not None:
            delta = vals[0] - vals[1]
        c.setFont(font, 5.3)
        c.drawCentredString(cx, y + 6, f"Δ {format_num(delta)}")

    c.setStrokeColor(colors.black)
    c.setLineWidth(0.45)
    c.rect(x, y, w, h, fill=0, stroke=1)


def draw_sidebar(c, x: float, y: float, w: float, h: float, *, font: str):
    from reportlab.lib import colors

    c.setStrokeColor(colors.black)
    c.setLineWidth(0.45)
    c.rect(x, y, w, h, fill=0, stroke=1)
    c.line(x + w / 2, y, x + w / 2, y + h)

    labels = [
        ("Взам. инв. №", 0.20),
        ("Подп. и дата", 0.16),
        ("Инв. № дубл.", 0.17),
        ("Подп. и дата", 0.20),
        ("Инв. № подл.", 0.27),
    ]
    cur_y = y + h
    for text, frac in labels:
        seg_h = h * frac
        cur_y -= seg_h
        c.line(x, cur_y, x + w, cur_y)
        c.saveState()
        c.translate(x + w * 0.25, cur_y + seg_h / 2)
        c.rotate(90)
        c.setFillColor(colors.black)
        c.setFont(font, 5.3)
        c.drawCentredString(0, -2, text)
        c.restoreState()


def draw_footer(c, x: float, y: float, w: float, h: float, *, font: str, bold_font: str, input_values: dict[str, Any]):
    from reportlab.lib import colors

    c.setStrokeColor(colors.black)
    c.setLineWidth(0.55)
    c.rect(x, y, w, h, fill=0, stroke=1)

    code_h = 28
    bottom_h = h - code_h
    code = build_nomen_name(input_values)
    draw_cell(c, x + 190, y + bottom_h, w - 190, code_h, code, font=font, bold_font=bold_font, size=12, bold=True, align="center")

    left_w = 190
    center_w = w - left_w - 150
    right_w = 150
    c.line(x + left_w, y, x + left_w, y + bottom_h)
    c.line(x + left_w + center_w, y, x + left_w + center_w, y + bottom_h)
    c.line(x + left_w, y + bottom_h, x + w, y + bottom_h)

    hdr_h = 16
    row_h = (bottom_h - hdr_h) / 4
    col_ws = [31, 32, 60, 36, 31]
    labels = ["Изм.", "Лист", "№ докум.", "Подп.", "Дата"]
    xx = x
    for cw, label in zip(col_ws, labels):
        draw_cell(c, xx, y + bottom_h - hdr_h, cw, hdr_h, label, font=font, bold_font=bold_font, size=5.7, bold=True, align="center")
        xx += cw
    roles = ["Разраб.", "Пров.", "Н. контр.", "Утв."]
    today = date.today().strftime("%d.%m.%Y")
    for i, role in enumerate(roles):
        yy = y + bottom_h - hdr_h - (i + 1) * row_h
        xx = x
        values = [role, "", "", "", today if i in (0, 3) else ""]
        for cw, value in zip(col_ws, values):
            draw_cell(c, xx, yy, cw, row_h, value, font=font, bold_font=bold_font, size=5.3, align="center")
            xx += cw

    project_name = str(unpack_value_by_key(input_values, "nazvanie_proekta", default="") or "").strip()
    title = "Акустический и аэродинамический расчет шумоглушителя"
    if project_name:
        title = f"{title}\n{project_name}"
    draw_cell(c, x + left_w, y, center_w, bottom_h, title, font=font, bold_font=bold_font, size=7.2, bold=True, align="center", max_lines=4)

    rx = x + left_w + center_w
    lit_w = 54
    page_w = 48
    sheets_w = right_w - lit_w - page_w
    draw_cell(c, rx, y + bottom_h - 18, lit_w, 18, "Лит.", font=font, bold_font=bold_font, size=6, bold=True, align="center")
    draw_cell(c, rx + lit_w, y + bottom_h - 18, page_w, 18, "Лист", font=font, bold_font=bold_font, size=6, bold=True, align="center")
    draw_cell(c, rx + lit_w + page_w, y + bottom_h - 18, sheets_w, 18, "Листов", font=font, bold_font=bold_font, size=6, bold=True, align="center")
    draw_cell(c, rx, y + bottom_h - 36, lit_w, 18, "", font=font, bold_font=bold_font, size=6, align="center")
    draw_cell(c, rx + lit_w, y + bottom_h - 36, page_w, 18, "1", font=font, bold_font=bold_font, size=6, align="center")
    draw_cell(c, rx + lit_w + page_w, y + bottom_h - 36, sheets_w, 18, "1", font=font, bold_font=bold_font, size=6, align="center")
    draw_cell(c, rx, y, right_w, bottom_h - 36, "ООО \"Пауэрз\"", font=font, bold_font=bold_font, size=8, bold=True, align="center")

    c.setFillColor(colors.black)


def build_silencer_report_pdf(
    *,
    report_name: str,
    calculated: dict[str, Any],
    input_values: dict[str, Any],
    save_dir: str,

) -> str | bool:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception as exc:
        raise RuntimeError("не установлен пакет reportlab") from exc

    os.makedirs(save_dir, exist_ok=True)
    safe = F.clear_row_for_file_name_c(report_name or str(unpack_value_by_key(input_values, "nazvanie_proekta", default="") or "silencer_report"))
    datetime_str = F.now('%Y%m%d%H%M%S')
    path = os.path.join(save_dir, f"{datetime_str}_{safe}_report.pdf")

    font, bold_font = register_fonts()
    c = canvas.Canvas(path, pagesize=A4)
    page_w, page_h = A4

    margin_l = 18
    margin_r = 16
    margin_t = 18
    footer_y = 20
    footer_h = 98
    sidebar_w = 36
    gap = 0
    main_x = margin_l + sidebar_w + gap
    main_w = page_w - main_x - margin_r
    top_y = page_h - margin_t

    c.setTitle(safe)
    c.setAuthor("MES silencer module")
    c.setSubject("Акустический и аэродинамический расчет шумоглушителя")

    c.setStrokeColor(colors.black)
    c.setLineWidth(0.7)
    c.rect(margin_l, footer_y, page_w - margin_l - margin_r, page_h - footer_y - margin_t, fill=0, stroke=1)
    draw_sidebar(c, margin_l, footer_y, sidebar_w, 218, font=font)
    draw_footer(c, main_x, footer_y, main_w, footer_h, font=font, bold_font=bold_font, input_values=input_values)

    project_name = str(unpack_value_by_key(input_values, "nazvanie_proekta", default="") or "").strip()
    project_num = str(unpack_value_by_key(input_values, "nomer_proekta", default="") or "").strip()
    y = top_y - 15
    c.setFont(bold_font, 11)
    c.drawString(main_x, y, "Отчет по расчету шумоглушителя")
    c.setFont(font, 7)
    subtitle = " · ".join([x for x in (project_name, project_num) if x])
    if subtitle:
        c.drawRightString(main_x + main_w, y, subtitle)
    y -= 10

    col_gap = 7
    card_w = (main_w - 2 * col_gap) / 3
    rows_nominal = [
        ("Среда", unpack_value_by_key(input_values, "sreda", default="-"), ""),
        (f"Расход, {unpack_value_by_key(input_values, 'edinica_rashoda', default='')}", unpack_value_by_key(input_values, "rashod"), ""),
        ("Давление до клапана", unpack_value_by_key(input_values, "ak_produvka_davlenie_v_nachale_truby_mpa_davlenie_do_klapana_mpa", "davlenie_na_vhode_v_shg_ri_abs_mpa"), "МПа"),
        ("Температура", unpack_value_by_key(input_values, "temperatura_sredy_s"), "°C"),
    ]
    rows_aero = [
        ("Давление на входе", unpack_value_by_key(input_values, "davlenie_na_vhode_v_shg_ri_abs_mpa"), "МПа"),
        ("Давление на выходе", unpack_value_by_key(calculated, "davlenie_na_vyhode_iz_shg_pe_mpa"), "МПа"),
        ("Реактивные силы", unpack_value_by_key(calculated, "r_reaktivnye_sily_n"), "Н"),
        ("Скорость на выходе ШГ", unpack_value_by_key(calculated, "skorost_na_vyhode_shg_m_s"), "м/с"),
    ]
    rows_elements = [
        ("Тип дроссельного блока", "Ступенчатый", ""),
        ("Ступеней дросселирования", unpack_value_by_key(input_values, "kolichestvo_stupenej_drosselirovaniya_sht"), "шт"),
        ("Наличие кассет", unpack_value_by_key(input_values, "nalichie_kasset", default="-"), ""),
        ("Внутренний диаметр корпуса", unpack_value_by_key(input_values, "vnutrennij_diametr_shumoglushitelya_korpus_m"), "м"),
    ]
    h_cards = 17 + 4 * 15.5
    y -= h_cards
    draw_column_table(c, main_x, y, card_w, rows_nominal, font=font, bold_font=bold_font, title="Номинальные параметры среды")
    draw_column_table(c, main_x + card_w + col_gap, y, card_w, rows_aero, font=font, bold_font=bold_font, title="Аэродинамический расчет")
    draw_column_table(c, main_x + 2 * (card_w + col_gap), y, card_w, rows_elements, font=font, bold_font=bold_font, title="Элементы шумоглушителя")
    y -= 12

    tube_power = get_num_series(calculated, POWER_TUBE_KEYS)
    silencer_power = get_num_series(calculated, POWER_SILENCER_KEYS)
    before_pressure = get_num_series(calculated, PRESSURE_BEFORE_KEYS)
    after_pressure = get_num_series(calculated, PRESSURE_AFTER_KEYS)
    distance = format_num(unpack_value_by_key(input_values, "ak_proekciya_rasstoyaniya_ot_istochnika_shuma_do_priemnika_na_ploskost_zemli_m", default=1), accuracy=2)

    series_h = 17 + 16 + 2 * 16
    y -= series_h
    draw_series_table(
        c,
        main_x,
        y,
        main_w,
        title="Уровни звуковой мощности, дБ",
        row1_label="Труба без ШГ",
        row2_label="Шумоглушитель",
        row1=tube_power,
        row2=silencer_power,
        font=font,
        bold_font=bold_font,
    )
    y -= 8 + series_h
    draw_series_table(
        c,
        main_x,
        y,
        main_w,
        title="Уровни звукового давления, дБ",
        row1_label=f"УЗД* в {distance} м до ШГ",
        row2_label=f"УЗД* в {distance} м после ШГ",
        row1=before_pressure,
        row2=after_pressure,
        font=font,
        bold_font=bold_font,
    )
    y -= 10

    chart_h = min(230, max(170, y - (footer_y + footer_h + 12)))
    y -= chart_h
    draw_twin_chart(c, main_x, y, main_w, chart_h, before_pressure, after_pressure, font=font, bold_font=bold_font)

    c.setFont(font, 5.8)
    c.drawString(main_x, footer_y + footer_h + 4, "* УЗД - уровень звукового давления. LАЭкв - эквивалентный уровень звука.")

    c.showPage()
    c.save()
    return path
