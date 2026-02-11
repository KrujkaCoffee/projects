from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import IntEnum
from html import escape
from typing import Any, Dict, List, Tuple, Optional, Iterable
import re

from project_cust_38 import Cust_b24 as CB24

# -----------------------------
# Domain model
# -----------------------------

class Score(IntEnum):
    S0 = 0
    S1 = 1
    S2 = 2
    S3 = 3
    S4 = 4


@dataclass(frozen=True)
class ScoreColor:
    """Цвета подсветки для оценки. Можно использовать только bg, можно bg+text."""
    bg: str
    text: str = "#111827"


@dataclass
class ScoreColorMap:
    """Мапа цветов для оценок 0..4"""
    colors: Dict[int, ScoreColor] = field(default_factory=dict)

    def get(self, score: int) -> Optional[ScoreColor]:
        return self.colors.get(score)


# -----------------------------
# Конфиг
# -----------------------------

@dataclass
class TableStyle:
    background_color: str = "#0A558A"
    border: str = "#212c45"
    text: str = "#111827"
    header_fill: str = "#c5dce9"
    zebra_odd: str = "#77a6c5"
    zebra_even: str = "#c5dce9"
    total_fill_odd: str = "#EEF6FF"
    total_fill_even: str = "#E8F1FF"
    radius_px: int = 12
    min_width_px: int = 900
    font_size: int = 11


@dataclass
class LayoutConfig:
    """Отступы секций"""
    left_margin_px: int = 16
    right_padding_px: int = 12
    section_pt: int = 30
    section_pb: int = 30


@dataclass
class ColumnConfig:
    """конфигурация ширины колонок
    задает текстовые колонки
    """
    default_text_cols: Tuple[str, ...] = ("ФИО", "Должность", "Ответственный")
    skip_cols: Tuple[str, ...] = ("ID_ФизЛица",)

    w_fio: int = 320
    w_position: int = 260
    w_responsible: int = 280
    w_total: int = 120
    w_default: int = 110

    total_key: str = "Итоговыйбалл"


@dataclass
class LegendConfig:
    """Конфиг таблицы "Критерии оценки навыков работников с бальными оценками"""
    enabled: bool = True
    title: str = "Критерии оценки"
    title_color: str = "#HHHHHH"
    header_fill: str = "#c5dce9"
    col_level: str = "Уровень"
    col_desc: str = "Описание"
    w_level: int = 90
    w_desc: int = 900

@dataclass
class CaptionConfig:
    """Конфиг заголовка"""
    ...

@dataclass
class ScoreHighlightConfig:
    """
    Опциональная подсветка оценок 0..4.
    По умолчанию выключена (enabled=False), чтобы HTML совпадал с прошлым результатом.
    """
    enabled: bool = False
    highlight_columns: Optional[Iterable[str]] = None
    colors: ScoreColorMap = field(default_factory=ScoreColorMap)


@dataclass
class GeneratorConfig:
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    table: TableStyle = field(default_factory=TableStyle)
    cols: ColumnConfig = field(default_factory=ColumnConfig)
    legend: LegendConfig = field(default_factory=LegendConfig)
    score_highlight: ScoreHighlightConfig = field(default_factory=ScoreHighlightConfig)


# -----------------------------
# utils
# -----------------------------

def _to_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


def _is_int_score_0_4(v: Any) -> Optional[int]:
    """
    Возвращает int 0..4 если значение похоже на оценку.
    Поддерживает int, строку "0".."4", float 0.0..4.0 без дробной части.
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int) and 0 <= v <= 4:
        return v
    if isinstance(v, float) and v.is_integer() and 0 <= int(v) <= 4:
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        if s.isdigit():
            i = int(s)
            if 0 <= i <= 4:
                return i
    return None


def parse_info_legend(info: str) -> List[Tuple[str, str]]:
    """преобразование данных к форме: [работник, оценки...]"""
    if not info:
        return []
    s = re.sub(r"\s+", " ", info).strip()
    pattern = re.compile(r"(?:(^)|\s)(\d)\s*[-–—]\s*")
    matches = list(pattern.finditer(s))
    if not matches:
        return []
    result: List[Tuple[str, str]] = []
    for i, m in enumerate(matches):
        lvl = m.group(2)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(s)
        text = s[start:end].strip().strip(" ;,")
        result.append((lvl, text))
    return result


# -----------------------------
# Функции отрисовки
# -----------------------------

class BitrixLandingMatrixRenderer:
    """Генерирует HTML основной таблицы метрик"""

    def __init__(self, cfg: GeneratorConfig):
        self.cfg = cfg


    def build_columns(self, tbl: List[Dict[str, Any]]) -> List[str]:
        cc = self.cfg.cols
        skip = set(cc.skip_cols)

        if not tbl:
            return list(cc.default_text_cols) + [cc.total_key]

        seen: List[str] = []

        def add_key(k: str):
            if k not in seen and k not in skip:
                seen.append(k)

        for k in tbl[0].keys():
            add_key(k)
        for r in tbl[1:]:
            for k in r.keys():
                add_key(k)

        cols: List[str] = []
        for k in cc.default_text_cols:
            if k in seen:
                cols.append(k)

        for k in seen:
            if k in cc.default_text_cols or k == cc.total_key:
                continue
            cols.append(k)

        if cc.total_key in seen:
            cols.append(cc.total_key)

        return cols

    def col_width(self, col: str) -> int:
        cc = self.cfg.cols
        if col == "ФИО":
            return cc.w_fio
        if col == "Должность":
            return cc.w_position
        if col == "Ответственный":
            return cc.w_responsible
        if col == cc.total_key:
            return cc.w_total
        return cc.w_default

    def render_table(
        self,
        header: List[str],
        rows: List[List[Any]],
        *,
        header_fill: Optional[str] = None,
        min_width_px: Optional[int] = None,
        is_main: bool = False,
    ) -> str:
        ts = self.cfg.table
        sh = self.cfg.score_highlight

        header_fill = header_fill or ts.header_fill
        min_width_px = min_width_px or ts.min_width_px

        widths = [self.col_width(h) if is_main else None for h in header]
        tech_ths = [
            '<th class="landing-table-th landing-table-th-select-all" style="width: 16px;">'
            '<div class="th-tech-icon"></div></th>'
        ]
        resolved_widths: List[int] = []
        for i, h in enumerate(header):
            w = widths[i] if widths[i] is not None else self.cfg.cols.w_default
            resolved_widths.append(w)
            tech_ths.append(
                f'<th class="landing-table-th landing-table-col-dnd" style="width:{w}px;">'
                '<div class="landing-table-div-col-dnd"></div>'
                '<div class="landing-table-col-resize"></div>'
                '<div class="landing-table-col-add"><div class="landing-table-col-add-line"></div></div>'
                '</th>'
            )
        tech_row = f'<tr class="landing-table-tr">{"".join(tech_ths)}</tr>'

        head_cells = [
            '<th class="landing-table-th landing-table-row-dnd">'
            '<div class="landing-table-row-add"><div class="landing-table-row-add-line"></div></div>'
            '<div class="landing-table-div-row-dnd"></div></th>'
        ]
        for h, w in zip(header, resolved_widths):
            head_cells.append(
                f'<td class="landing-table-th landing-table-td" '
                f'style="width:{w}px; font-weight:700; background:{header_fill}; '
                f'color:{ts.text}; border: none; border-color:{ts.border};">'
                f'{escape(h)}</td>'
            )
        header_row = f'<tr class="landing-table-tr">{"".join(head_cells)}</tr>'

        body_rows: List[str] = []
        for r_i, r in enumerate(rows, start=1):
            cells = [
                '<th class="landing-table-th landing-table-row-dnd">'
                '<div class="landing-table-row-add"><div class="landing-table-row-add-line"></div></div>'
                '<div class="landing-table-div-row-dnd"></div></th>'
            ]

            base_bg = ts.zebra_odd if (r_i % 2 == 1) else ts.zebra_even

            for c_i, (val, col_name, w) in enumerate(zip(r, header, resolved_widths)):
                bg = base_bg

                if is_main and col_name == self.cfg.cols.total_key:
                    bg = ts.total_fill_odd if (r_i % 2 == 1) else ts.total_fill_even

                extra_style = ""
                if sh.enabled:
                    allowed_cols = None if sh.highlight_columns is None else set(sh.highlight_columns)
                    if allowed_cols is None or col_name in allowed_cols:
                        score = _is_int_score_0_4(val)
                        if score is not None:
                            sc = sh.colors.get(score)
                            if sc is not None:
                                bg = sc.bg
                                extra_style = f" color:{sc.text}; font-weight:700;"

                cells.append(
                    f'<td class="landing-table-th landing-table-td" '
                    f'style="width:{w}px; color:{ts.text}; border-color:{ts.border}; border: none; '
                    f'background:{bg};{extra_style}">'
                    f'{escape(_to_str(val))}</td>'
                )

            body_rows.append(f'<tr class="landing-table-tr">{"".join(cells)}</tr>')

        return (
            '<div class="landing-table-container" '
            f'style="max-width:none; width:auto; overflow:auto; '
            f'border-radius:{ts.radius_px}px;">'
            '<table class="landing-table landing-table-style-1" text-color="#111827" '
            f'style=":separate; border-spacing:0; min-width:{min_width_px}px;">'
            f'<tbody>{tech_row}{header_row}{"".join(body_rows)}</tbody>'
            '</table></div>'
        )

    def render_matrix(self, data: Dict[str, Any]) -> str:
        tbl: List[Dict[str, Any]] = data.get("tbl") or []
        cols = self.build_columns(tbl)

        rows = [[r.get(c, "") for c in cols] for r in tbl]
        return self.render_table(cols, rows, is_main=True)

    def render_legend(self, data: Dict[str, Any]) -> str:
        lg = self.cfg.legend
        sh = self.cfg.score_highlight

        if not lg.enabled:
            return ""

        items = parse_info_legend(data.get("info", ""))
        if not items:
            return ""

        header = [lg.col_level, lg.col_desc]
        legend_rows: List[List[Any]] = [[lvl, f"- {txt}"] for (lvl, txt) in items]

        ts = self.cfg.table
        border = ts.border

        tech_ths = [
            '<th class="landing-table-th landing-table-th-select-all" style="width: 16px;">'
            '<div class="th-tech-icon"></div></th>',
            f'<th class="landing-table-th landing-table-col-dnd" style="width:{lg.w_level}px;">'
            '<div class="landing-table-div-col-dnd"></div><div class="landing-table-col-resize"></div>'
            '<div class="landing-table-col-add"><div class="landing-table-col-add-line"></div></div></th>',
            f'<th class="landing-table-th landing-table-col-dnd" style="width:{lg.w_desc}px;">'
            '<div class="landing-table-div-col-dnd"></div><div class="landing-table-col-resize"></div>'
            '<div class="landing-table-col-add"><div class="landing-table-col-add-line"></div></div></th>',
        ]
        tech_row = f'<tr class="landing-table-tr">{"".join(tech_ths)}</tr>'

        head_cells = [
            '<th class="landing-table-th landing-table-row-dnd">'
            '<div class="landing-table-row-add"><div class="landing-table-row-add-line"></div></div>'
            '<div class="landing-table-div-row-dnd"></div></th>',
            f'<td class="landing-table-th landing-table-td" style="width:{lg.w_level}px; font-weight:700; '
            f'background:{lg.header_fill}; color:{ts.text};border: none; border-color:{border};">{escape(lg.col_level)}</td>',
            f'<td class="landing-table-th landing-table-td" style="width:{lg.w_desc}px; font-weight:700; '
            f'background:{lg.header_fill}; color:{ts.text};border: none; border-color:{border};">{escape(lg.col_desc)}</td>',
        ]
        header_row = f'<tr class="landing-table-tr">{"".join(head_cells)}</tr>'

        body_rows: List[str] = []
        for i, (lvl, desc) in enumerate(legend_rows, start=1):
            base_bg = ts.zebra_odd if (i % 2 == 1) else ts.zebra_even

            lvl_bg = base_bg
            lvl_extra = ""
            if sh.enabled:
                score = _is_int_score_0_4(lvl)
                if score is not None:
                    sc = sh.colors.get(score)
                    if sc is not None:
                        lvl_bg = sc.bg
                        lvl_extra = f" color:{sc.text}; font-weight:700;"

            row_cells = [
                '<th class="landing-table-th landing-table-row-dnd">'
                '<div class="landing-table-row-add"><div class="landing-table-row-add-line"></div></div>'
                '<div class="landing-table-div-row-dnd"></div></th>',
                f'<td class="landing-table-th landing-table-td" style="width:{lg.w_level}px; '
                f'color:{ts.text}; border-color:{border}; border: none; background:{lvl_bg}; text-align:center;{lvl_extra}">'
                f'{escape(_to_str(lvl))}</td>',
                f'<td class="landing-table-th landing-table-td" style="width:{lg.w_desc}px; '
                f'color:{ts.text}; border-color:{border}; border: none; background:{base_bg};">'
                f'{escape(_to_str(desc))}</td>',
            ]
            body_rows.append(f'<tr class="landing-table-tr">{"".join(row_cells)}</tr>')

        table_html = (
            '<div class="landing-table-container" '
            f'style="max-width:none; width:auto; overflow:auto; '
            f'border-radius:{ts.radius_px}px;">'
            '<table class="landing-table landing-table-style-1" text-color="#111827" '
            f'style="border-spacing:0; min-width:{max(650, lg.w_level + lg.w_desc)}px;">'
            f'<tbody>{tech_row}{header_row}{"".join(body_rows)}</tbody>'
            '</table></div>'
        )

        return (
            f'<div style="margin-top:14px;">'
            f'<div style="font-weight:700; font-size=22px; text-align: center; color:{lg.title_color}; margin:0 0 8px 2px;">'
            f'{escape(lg.title)}</div>'
            f'{table_html}'
            f'</div>'
        )


    def render(self, data: Dict[str, Any], render_date_end: bool = False) -> str:
        lay = self.cfg.layout

        main = self.render_matrix(data)
        legend = self.render_legend(data)
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        caption = f'<h3 style="color: #dce6fd; padding-left: 40px">Актуален на дату: {now}</h3>' if render_date_end else ''
        return f"""
<section class="landing-block js-animation g-pt-{lay.section_pt} g-pb-{lay.section_pb} u-block-border-none" style="font-size: {self.cfg.table.font_size}px">
    {caption}
  <div class="landing-block-node-text js-animation fadeIn"
       style="animation-duration: 1000ms; animation-play-state: running; animation-name: none;
              max-width:none; margin:0 0 0 {lay.left_margin_px}px; padding-right:{lay.right_padding_px}px;"
       data-selector=".landing-block-node-text@0">
    {main}
    {legend}
  </div>
  <div hidden=""></div>
</section>
""".strip()


def default_score_colors() -> ScoreColorMap:
    """цвета для метрики по оцнка 0...4"""
    return ScoreColorMap(colors={
        int(Score.S0): ScoreColor(bg="#FFF5F5", text="#7F1D1D"),
        int(Score.S1): ScoreColor(bg="#FFF7ED", text="#7C2D12"),
        int(Score.S2): ScoreColor(bg="#FFFBEB", text="#78350F"),
        int(Score.S3): ScoreColor(bg="#ECFDF5", text="#065F46"),
        int(Score.S4): ScoreColor(bg="#EFF6FF", text="#1E3A8A"),
    })
