from __future__ import annotations

from typing import Any, Callable, Iterable

import flet as ft


_FREQ_LABELS: list[str] = ["31,5", "63", "125", "250", "500", "1000", "2000", "4000", "8000", "LАЭкв"]

_PRESSURE_BEFORE_KEYS: list[str] = [
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

_PRESSURE_AFTER_KEYS: list[str] = [
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

_POWER_TUBE_KEYS: list[str] = [
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

_POWER_SILENCER_KEYS: list[str] = [
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


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", ".")
        if not text:
            return None
        try:
            return float(text)
        except Exception:
            return None
    return None


def _fmt(value: Any, accuracy: int = 1, empty: str = "—") -> str:
    num = _as_float(value)
    if num is None:
        return empty
    if abs(num - int(num)) < 10 ** (-(accuracy + 1)):
        return str(int(round(num)))
    return f"{num:.{accuracy}f}".replace(".", ",")


def _fmt_cell(value: Any, accuracy: int = 1, empty: str = "—") -> str:
    num = _as_float(value)
    if num is not None:
        return _fmt(num, accuracy=accuracy, empty=empty)
    if value is None:
        return empty
    text = str(value).strip()
    return text if text else empty


def _value(source: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in source and source.get(key) not in (None, ""):
            return source.get(key)
    return default


def _series(calculated: dict[str, Any], keys: Iterable[str]) -> list[float | None]:
    return [_as_float(calculated.get(key)) for key in keys]


def _card(title: str, rows: list[tuple[str, Any, str]], *, width: int | None = None) -> ft.Container:
    body: list[ft.Control] = [ft.Text(title, weight=ft.FontWeight.W_600, size=15)]
    for name, val, dim in rows:
        body.append(
            ft.Row(
                controls=[
                    ft.Text(name, size=12, opacity=0.78, expand=True),
                    ft.Text(_fmt_cell(val), size=12, weight=ft.FontWeight.W_600),
                    ft.Text(dim, size=12, opacity=0.7, width=48),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    return ft.Container(
        content=ft.Column(body, spacing=6),
        padding=14,
        width=width,
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=12,
        bgcolor=ft.Colors.SURFACE,
    )


def _small_table(title: str, before_title: str, after_title: str, before: list[float | None], after: list[float | None]) -> ft.Container:
    header = ft.Row(
        controls=[
            ft.Text("Показатель", width=92, size=11, weight=ft.FontWeight.W_600),
            *[ft.Text(label, width=58, size=11, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER) for label in _FREQ_LABELS],
        ],
        spacing=2,
    )

    def _row(label: str, vals: list[float | None]) -> ft.Row:
        return ft.Row(
            controls=[
                ft.Text(label, width=92, size=11),
                *[
                    ft.Text(_fmt(v), width=58, size=11, text_align=ft.TextAlign.CENTER)
                    for v in vals
                ],
            ],
            spacing=2,
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(title, weight=ft.FontWeight.W_600, size=15),
                ft.Container(content=header, padding=ft.padding.only(top=4, bottom=2)),
                _row(before_title, before),
                _row(after_title, after),
            ],
            spacing=4,
        ),
        padding=14,
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=12,
        bgcolor=ft.Colors.SURFACE,
    )


def _twin_tower_chart(before: list[float | None], after: list[float | None]) -> ft.Container:
    numeric_values = [v for v in [*before, *after] if isinstance(v, (int, float))]
    max_value = max(numeric_values) if numeric_values else 1.0
    min_value = min(numeric_values) if numeric_values else 0.0
    spread = max(max_value - min_value, 1.0)

    def _bar(value: float | None, color: str) -> ft.Container:
        if value is None:
            h = 2
        else:
            h = 18 + int(((value - min_value) / spread) * 142)
        return ft.Container(
            width=16,
            height=max(2, h),
            bgcolor=color,
            border_radius=ft.border_radius.only(top_left=5, top_right=5),
            tooltip=_fmt(value),
        )

    tower_controls: list[ft.Control] = []
    for label, before_val, after_val in zip(_FREQ_LABELS, before, after):
        delta = None
        if before_val is not None and after_val is not None:
            delta = before_val - after_val
        tower_controls.append(
            ft.Column(
                controls=[
                    ft.Text(_fmt(before_val), size=10, text_align=ft.TextAlign.CENTER, width=70),
                    ft.Container(
                        height=170,
                        content=ft.Row(
                            controls=[
                                _bar(before_val, ft.Colors.PRIMARY),
                                _bar(after_val, ft.Colors.TERTIARY),
                            ],
                            spacing=5,
                            vertical_alignment=ft.CrossAxisAlignment.END,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                    ),
                    ft.Text(_fmt(after_val), size=10, text_align=ft.TextAlign.CENTER, width=70),
                    ft.Text(label, size=11, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER, width=70),
                    ft.Text(f"Δ {_fmt(delta)}", size=10, opacity=0.72, text_align=ft.TextAlign.CENTER, width=70),
                ],
                spacing=3,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Акустическая эффективность шумоглушителя", weight=ft.FontWeight.W_600, size=16),
                        ft.Container(expand=True),
                        ft.Row(
                            controls=[
                                ft.Container(width=12, height=12, bgcolor=ft.Colors.PRIMARY, border_radius=3),
                                ft.Text("до установки", size=12),
                                ft.Container(width=12, height=12, bgcolor=ft.Colors.TERTIARY, border_radius=3),
                                ft.Text("после установки", size=12),
                            ],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(
                    "УЗД до и после установки ШГ.",
                    size=12,
                    opacity=0.75,
                ),
                ft.Row(tower_controls, spacing=12, scroll=ft.ScrollMode.ALWAYS),
            ],
            spacing=10,
        ),
        padding=16,
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=14,
        bgcolor=ft.Colors.SURFACE,
    )


def _subtitle_by_distance(input_values: dict[str, Any]) -> tuple[str, str]:
    distance = _fmt(
        _value(input_values, "ak_proekciya_rasstoyaniya_ot_istochnika_shuma_do_priemnika_na_ploskost_zemli_m", default=1),
        accuracy=2,
    )
    before = f"УЗД* в {distance} м. от трубы до установки ШГ, дБ"
    after = f"УЗД* в {distance} м. после установки ШГ, дБ"
    return before, after


def build_silencer_report(
    *,
    calculated: dict[str, Any],
    input_values: dict[str, Any],
    on_back: Callable[[ft.ControlEvent], None],
) -> ft.Control:
    """Собирает экран отчёта"""

    before_pressure = _series(calculated, _PRESSURE_BEFORE_KEYS)
    after_pressure = _series(calculated, _PRESSURE_AFTER_KEYS)
    tube_power = _series(calculated, _POWER_TUBE_KEYS)
    silencer_power = _series(calculated, _POWER_SILENCER_KEYS)
    before_title, after_title = _subtitle_by_distance(input_values)

    project_name = str(_value(input_values, "nazvanie_proekta", default="") or "").strip()
    project_num = str(_value(input_values, "nomer_proekta", default="") or "").strip()
    title_suffix = " · ".join([x for x in (project_name, project_num) if x])

    top_cards = ft.Row(
        controls=[
            _card(
                "Номинальные параметры среды",
                [
                    ("Среда", _value(input_values, "sreda", default="—"), ""),
                    (f"Расход, {_value(input_values, 'edinica_rashoda', default='')}", _value(input_values, "rashod"), ""),
                    ("Давление до клапана", _value(input_values, "ak_produvka_davlenie_v_nachale_truby_mpa_davlenie_do_klapana_mpa", "davlenie_na_vhode_v_shg_ri_abs_mpa"), "МПа"),
                    ("Температура", _value(input_values, "temperatura_sredy_s"), "°C"),
                ],
                width=360,
            ),
            _card(
                "Результаты аэродинамического расчёта",
                [
                    ("Давление на входе", _value(input_values, "davlenie_na_vhode_v_shg_ri_abs_mpa"), "МПа"),
                    ("Давление на выходе", _value(calculated, "davlenie_na_vyhode_iz_shg_pe_mpa"), "МПа"),
                    ("Реактивные силы", _value(calculated, "r_reaktivnye_sily_n"), "Н"),
                    ("Скорость на выходе ШГ", _value(calculated, "skorost_na_vyhode_shg_m_s"), "м/с"),
                ],
                width=400,
            ),
            _card(
                "Элементы шумоглушителя",
                [
                    ("Тип дроссельного блока", "Ступенчатый", ""),
                    ("Ступеней дросселирования", _value(input_values, "kolichestvo_stupenej_drosselirovaniya_sht"), "шт"),
                    ("Наличие кассет", _value(input_values, "nalichie_kasset", default="—"), ""),
                    ("Внутренний диаметр корпуса", _value(input_values, "vnutrennij_diametr_shumoglushitelya_korpus_m"), "м"),
                ],
                width=390,
            ),
        ],
        spacing=12,
        wrap=True,
    )

    content = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.TextButton("← Назад к расчету", on_click=on_back),
                    ft.Container(expand=True),
                    # ft.Text("📊 Отчёт-график", size=24, weight=ft.FontWeight.W_700),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text(
                f"Акустический и аэродинамический расчет шумоглушителя{(' — ' + title_suffix) if title_suffix else ''}",
                size=14,
                opacity=0.78,
            ),
            top_cards,
            _small_table(
                "Уровни звуковой мощности, дБ",
                "Труба без ШГ",
                "Шумоглушитель",
                tube_power,
                silencer_power,
            ),
            _small_table(
                "Уровни звукового давления, дБ",
                before_title,
                after_title,
                before_pressure,
                after_pressure,
            ),
            _twin_tower_chart(before_pressure, after_pressure),
            ft.Text("*УЗД — уровень звукового давления. LАЭкв — эквивалентный уровень звука.", size=12, opacity=0.72),
        ],
        spacing=14,
        scroll=ft.ScrollMode.ALWAYS,
        expand=True,
    )

    return ft.Container(
        content=content,
        expand=True,
        padding=ft.padding.only(left=18, right=18, top=14, bottom=14),
        bgcolor=ft.Colors.SURFACE,
    )
