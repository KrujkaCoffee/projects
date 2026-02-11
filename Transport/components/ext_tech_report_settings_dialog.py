from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

import re
import flet as ft


@dataclass(frozen=True)
class _Item:
    key: str
    group: str
    header: str
    dim: str
    default_visible: bool


@dataclass
class _SeriesInfo:
    base: str
    header: str
    tags: set[str]
    idxs: set[int]


_DEFAULT_SUFFIX_REGEX = r"^(?P<base>.+)_(?P<tag>[A-Za-z]+)(?P<idx>\d+)$"


def _default_visible(meta: dict) -> bool:
    """Определяем дефолтную видимость параметра.

    Поддерживаем форматы:
    - view: bool
    - view: {"visible": bool, ...}
    - отсутствует -> True
    """
    view = meta.get("view", True)
    if isinstance(view, bool):
        return view
    if isinstance(view, dict):
        return bool(view.get("visible", True))
    return True


def _normalize_tags(raw: Any) -> List[str]:
    if raw is None:
        return ["n"]
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.split(",")]
        return [p for p in parts if p]
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return ["n"]


def _scan_series(output_params: Dict[str, dict], suffix_regex: str) -> Tuple[List[str], Dict[str, List[_SeriesInfo]]]:
    """Сканирует OUTPUT_PARAMS и находит серии по suffix_regex.

    Returns:
        group_names: list[str]
        series_by_group: group_name -> list[_SeriesInfo]
    """
    try:
        suffix_re = re.compile(suffix_regex)
    except Exception:
        suffix_re = re.compile(_DEFAULT_SUFFIX_REGEX)

    tmp: Dict[str, Dict[str, _SeriesInfo]] = {}  # group -> base -> info

    for key, meta in (output_params or {}).items():
        if not isinstance(meta, dict):
            meta = {}

        m = suffix_re.match(str(key))
        if not m:
            continue

        base = str(m.group("base"))
        tag = str(m.group("tag"))
        try:
            idx = int(m.group("idx"))
        except Exception:
            continue

        group = str(meta.get("group_name") or "").strip() or "Без группы"
        header = str(meta.get("header") or base)

        gmap = tmp.setdefault(group, {})
        info = gmap.get(base)
        if info is None:
            info = _SeriesInfo(base=base, header=header, tags=set(), idxs=set())
            gmap[base] = info

        info.tags.add(tag)
        info.idxs.add(idx)

    group_names = sorted(tmp.keys(), key=lambda s: s.lower())
    series_by_group: Dict[str, List[_SeriesInfo]] = {}
    for g in group_names:
        # stable sort: by header/base
        infos = list(tmp[g].values())
        infos.sort(key=lambda x: (x.header.lower(), x.base.lower()))
        series_by_group[g] = infos

    return group_names, series_by_group

def _set_btn_busy(btn, text):
    try:
        btn.disabled = True
        # на 0.80.x у кнопок обычно есть content
        btn.content = ft.Row(
            [ft.ProgressRing(width=16, height=16, stroke_width=2), ft.Text(text)],
            tight=True,
            spacing=8,
        )
    except Exception:
        # fallback
        try:
            btn.disabled = True
            btn.text = text
        except Exception:
            pass

def open_tech_report_settings_dialog(
    page: ft.Page,
    *,
    output_params: Dict[str, dict],
    cfg: Dict[str, Any] | None,
    on_save: Callable[[Dict[str, Any]], None],
    title: str = "Настройки технологического отчёта",
):
    """Открыть модальный диалог настроек тех. отчёта."""

    cfg = cfg if isinstance(cfg, dict) else {}
    cfg_fields: Dict[str, Any] = cfg.get("fields") if isinstance(cfg.get("fields"), dict) else {}
    cfg_groups: Dict[str, Any] = cfg.get("groups") if isinstance(cfg.get("groups"), dict) else {}

    transpose_enabled_init = bool(cfg.get("transpose_enabled", True))
    transpose_tags_init = _normalize_tags(cfg.get("transpose_tags"))
    suffix_regex_init = str(cfg.get("suffix_regex") or _DEFAULT_SUFFIX_REGEX)

    # transpose filters (optional)
    cfg_t_groups: Dict[str, Any] = cfg.get("transpose_groups") if isinstance(cfg.get("transpose_groups"), dict) else {}
    cfg_t_bases_raw = cfg.get("transpose_bases")
    cfg_t_bases: List[str] | None
    if isinstance(cfg_t_bases_raw, list):
        cfg_t_bases = [str(x) for x in cfg_t_bases_raw if str(x).strip()]
    elif isinstance(cfg_t_bases_raw, str):
        cfg_t_bases = [x.strip() for x in cfg_t_bases_raw.split(",") if x.strip()]
    else:
        cfg_t_bases = None

    # ---- build output items ----
    items: List[_Item] = []
    for key, meta in (output_params or {}).items():
        if not isinstance(meta, dict):
            meta = {}
        group = str(meta.get("group_name") or "").strip() or "Без группы"
        header = str(meta.get("header") or key)
        dim = str(meta.get("dimension") or "")
        items.append(
            _Item(
                key=str(key),
                group=group,
                header=header,
                dim=dim,
                default_visible=_default_visible(meta),
            )
        )

    items.sort(key=lambda it: (it.group.lower(), it.header.lower()))
    group_names = sorted({it.group for it in items}, key=lambda s: s.lower())
    group_to_items: Dict[str, List[_Item]] = {g: [] for g in group_names}
    for it in items:
        group_to_items[it.group].append(it)

    # ---- effective state ----
    field_state: Dict[str, bool] = {}
    for it in items:
        field_state[it.key] = bool(cfg_fields.get(it.key, it.default_visible))

    group_state: Dict[str, bool] = {}
    for g in group_names:
        group_state[g] = bool(cfg_groups.get(g, True))

    # ---- transpose scan + state ----
    series_group_names, series_by_group = _scan_series(output_params, suffix_regex_init)
    all_bases: List[str] = []
    for g in series_group_names:
        for info in series_by_group.get(g, []):
            all_bases.append(info.base)
    all_bases_set = set(all_bases)

    transpose_group_state: Dict[str, bool] = {}
    for g in series_group_names:
        # cfg stores only выключенные группы; default True
        transpose_group_state[g] = bool(cfg_t_groups.get(g, True))

    transpose_base_state: Dict[str, bool] = {}
    if cfg_t_bases is None:
        # None => все базы включены
        for b in all_bases_set:
            transpose_base_state[b] = True
    else:
        allowed = set(cfg_t_bases)
        for b in all_bases_set:
            transpose_base_state[b] = b in allowed

    # ---- controls ----
    search_tf = ft.TextField(
        label="Поиск",
        hint_text="по имени / ключу параметра",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        dense=True,
    )

    transpose_enabled_sw = ft.Switch(label="Включить транспонирование серий", value=transpose_enabled_init)
    transpose_tags_tf = ft.TextField(
        label="Теги серий (через запятую)",
        value=", ".join(transpose_tags_init),
        hint_text="например: n, out",
        dense=True,
    )
    suffix_regex_tf = ft.TextField(
        label="Regex суффикса",
        value=suffix_regex_init,
        dense=True,
        helper="Дефолт: <base>_<tag><idx>  (пример: pressure_n1)",
    )

    fields_body_ref = ft.Ref[ft.Column]()
    transpose_body_ref = ft.Ref[ft.Column]()

    # action controls (to disable during save)
    progress_ring = ft.ProgressRing(width=18, height=18, visible=False)
    btn_cancel = ft.TextButton("Отмена")
    btn_save = ft.FilledButton("Сохранить")

    def _close(save: bool):
        if _closing["busy"]:
            return
        _closing["busy"] = True

        # instant feedback
        _set_btn_busy(btn_save, "Сохранение…" if save else "Закрытие…")
        _set_btn_busy(btn_cancel, "…")
        try:
            dlg.update()  # важно: обновляем только диалог
        except Exception:
            pass

        # закрываем сразу (без page.update/close)
        try:
            dlg.open = False
            dlg.update()
        except Exception:
            pass

        # потом сохраняем (если нужно)
        if save:
            try:
                on_save(_build_cfg())
            except Exception as ex:
                try:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка сохранения настроек: {ex}"))
                    page.snack_bar.open = True
                    page.update()
                except Exception:
                    pass

    _closing = {"busy": False}

    # ---- cfg builder ----
    def _build_cfg() -> Dict[str, Any]:
        # fields overrides: пишем только отличия от дефолта
        fields_overrides: Dict[str, bool] = {}
        for it in items:
            cur = bool(field_state.get(it.key, True))
            if cur != bool(it.default_visible):
                fields_overrides[it.key] = cur

        # groups overrides: дефолт True
        groups_overrides: Dict[str, bool] = {}
        for g in group_names:
            cur = bool(group_state.get(g, True))
            if cur is not True:
                groups_overrides[g] = cur

        # transpose: groups overrides (по умолчанию True)
        t_groups_overrides: Dict[str, bool] = {}
        for g in series_group_names:
            cur = bool(transpose_group_state.get(g, True))
            if cur is not True:
                t_groups_overrides[g] = cur

        # transpose: bases allow-list
        enabled_bases = sorted([b for b, v in transpose_base_state.items() if bool(v)], key=lambda s: s.lower())
        if not all_bases_set:
            transpose_bases_out = None
        else:
            # если включены все - не пишем allow-list (значит "все")
            if set(enabled_bases) == set(all_bases_set):
                transpose_bases_out = None
            else:
                transpose_bases_out = enabled_bases  # может быть [] => "ничего"

        out: Dict[str, Any] = {
            "fields": fields_overrides,
            "groups": groups_overrides,
            "transpose_enabled": bool(transpose_enabled_sw.value),
            "transpose_tags": _normalize_tags(transpose_tags_tf.value),
            "suffix_regex": (suffix_regex_tf.value or _DEFAULT_SUFFIX_REGEX).strip(),
        }

        if t_groups_overrides:
            out["transpose_groups"] = t_groups_overrides
        if transpose_bases_out is not None:
            out["transpose_bases"] = transpose_bases_out

        return out

    # ---- fields rendering ----
    def _render_fields():
        q = (search_tf.value or "").strip().lower()

        tiles: List[ft.Control] = []

        # bulk actions
        def _apply_all(val: bool):
            for it in items:
                field_state[it.key] = val
            for g in group_names:
                group_state[g] = True
            _render_fields()

        def _apply_none():
            for it in items:
                field_state[it.key] = False
            for g in group_names:
                group_state[g] = False
            _render_fields()

        def _apply_reset():
            for it in items:
                field_state[it.key] = it.default_visible
            for g in group_names:
                group_state[g] = True
            _render_fields()

        buttons = ft.Row(
            controls=[
                ft.FilledButton("Все", on_click=lambda _e: _apply_all(True)),
                ft.OutlinedButton("Ничего", on_click=lambda _e: _apply_none()),
                ft.TextButton("Сброс", on_click=lambda _e: _apply_reset()),
            ],
            spacing=10,
        )

        tiles.append(ft.Row([search_tf, buttons], spacing=12))
        tiles.append(
            ft.Text(
                "Подсказка: дефолтная видимость берётся из OUTPUT_PARAMS[key]['view'] (если задано).\n"
                "Галочка группы выключает группу целиком в отчёте.",
                size=12,
                opacity=0.8,
            )
        )

        def _on_group_toggle(e: ft.ControlEvent):
            gg = str(e.control.data)
            group_state[gg] = bool(e.control.value)
            # группа — маска, поле не трогаем

        def _on_field_toggle(e: ft.ControlEvent):
            kk = str(e.control.data)
            field_state[kk] = bool(e.control.value)

        for g in group_names:
            group_items = group_to_items.get(g, [])

            if q:
                group_items = [it for it in group_items if (q in it.header.lower()) or (q in it.key.lower())]
                if not group_items:
                    continue

            grp_cb = ft.Checkbox(value=bool(group_state.get(g, True)), data=g, on_change=_on_group_toggle)
            title_row = ft.Row(
                controls=[
                    grp_cb,
                    ft.Text(g, weight=ft.FontWeight.W_600),
                    ft.Text(f"({len(group_items)})", size=12, opacity=0.7),
                ],
                spacing=8,
            )

            field_tiles: List[ft.Control] = []
            for it in group_items:
                cb = ft.Checkbox(value=bool(field_state.get(it.key, True)), data=it.key, on_change=_on_field_toggle)
                subtitle = it.key
                if it.dim:
                    subtitle = f"{subtitle} · {it.dim}"
                field_tiles.append(
                    ft.ListTile(
                        leading=cb,
                        title=ft.Text(it.header),
                        subtitle=ft.Text(subtitle, size=11, opacity=0.75),
                        dense=True,
                    )
                )

            tiles.append(
                ft.ExpansionTile(
                    title=title_row,
                    maintain_state=True,
                    expanded=False,
                    controls=field_tiles,
                )
            )

        fields_body_ref.current.controls = tiles
        fields_body_ref.current.update()

    # ---- transpose rendering ----
    def _render_transpose():
        tiles: List[ft.Control] = []

        tiles.append(
            ft.Text(
                "Транспонирование серий: собираем параметры вида <base>_<tag><idx> в одну строку\n"
                "и раскладываем значения по колонкам (tag+idx).",
                size=12,
                opacity=0.85,
            )
        )
        tiles.append(transpose_enabled_sw)

        if not series_group_names:
            tiles.append(
                ft.Text(
                    "Серийные поля не найдены (по regex суффикса).",
                    size=12,
                    opacity=0.75,
                )
            )
        else:
            # bulk base actions
            def _bases_all(val: bool):
                for b in all_bases_set:
                    transpose_base_state[b] = val
                _render_transpose()

            tiles.append(
                ft.Row(
                    controls=[
                        ft.FilledButton("Все серии", on_click=lambda _e: _bases_all(True)),
                        ft.OutlinedButton("Ни одной", on_click=lambda _e: _bases_all(False)),
                    ],
                    spacing=10,
                )
            )

            def _on_t_group_toggle(e: ft.ControlEvent):
                gg = str(e.control.data)
                transpose_group_state[gg] = bool(e.control.value)

            def _on_t_base_toggle(e: ft.ControlEvent):
                bb = str(e.control.data)
                transpose_base_state[bb] = bool(e.control.value)

            for g in series_group_names:
                infos = series_by_group.get(g, [])
                if not infos:
                    continue

                g_sw = ft.Switch(
                    value=bool(transpose_group_state.get(g, True)),
                    label="Транспонировать в группе",
                    data=g,
                    on_change=_on_t_group_toggle,
                )

                rows: List[ft.Control] = []
                for info in infos:
                    tags_txt = ", ".join(sorted(info.tags, key=lambda s: s.lower()))
                    if info.idxs:
                        mn, mx = min(info.idxs), max(info.idxs)
                        idx_txt = f"{mn}..{mx}" if mn != mx else f"{mn}"
                    else:
                        idx_txt = "?"

                    rows.append(
                        ft.ListTile(
                            leading=ft.Checkbox(
                                value=bool(transpose_base_state.get(info.base, True)),
                                data=info.base,
                                on_change=_on_t_base_toggle,
                            ),
                            title=ft.Text(info.header),
                            subtitle=ft.Text(f"base: {info.base} · теги: {tags_txt} · индексы: {idx_txt}", size=11, opacity=0.75),
                            dense=True,
                        )
                    )

                tiles.append(
                    ft.ExpansionTile(
                        title=ft.Row(
                            controls=[ft.Text(g, weight=ft.FontWeight.W_600), ft.Text(f"({len(infos)})", size=12, opacity=0.7)],
                            spacing=8,
                        ),
                        maintain_state=True,
                        expanded=False,
                        controls=[g_sw] + rows,
                    )
                )

        # advanced settings
        tiles.append(
            ft.ExpansionTile(
                title=ft.Text("Служебные настройки (не обязательно)", weight=ft.FontWeight.W_600),
                maintain_state=True,
                expanded=False,
                controls=[
                    ft.Text(
                        "Если нужно — можно расширить список тегов или поменять regex распознавания серий.",
                        size=12,
                        opacity=0.75,
                    ),
                    transpose_tags_tf,
                    suffix_regex_tf,
                ],
            )
        )

        transpose_body_ref.current.controls = tiles
        transpose_body_ref.current.update()

    def _close_prev(save: bool):
        if _closing["busy"]:
            return
        _closing["busy"] = True
        progress_ring.visible = True
        btn_save.disabled = True
        btn_cancel.disabled = True
        dlg.update()

        if save:
            on_save(_build_cfg())
        page.pop_dialog()



    btn_cancel.on_click = lambda _e: _close(False)
    btn_save.on_click = lambda _e: _close(True)

    fields_tab = ft.Container(
        content=ft.Column(ref=fields_body_ref, controls=[], scroll=ft.ScrollMode.AUTO, expand=True),
        expand=True,
    )

    transpose_tab = ft.Container(
        content=ft.Column(ref=transpose_body_ref, controls=[], scroll=ft.ScrollMode.AUTO, expand=True),
        expand=True,
        padding=ft.padding.only(top=8),
    )

    tab_bar = ft.TabBar(
        tabs=[
            ft.Tab(label="Поля"),
            ft.Tab(label="Транспонирование"),
        ]
    )

    tab_view = ft.TabBarView(
        controls=[
            fields_tab,
            transpose_tab,
        ],
        expand=True,
    )

    tabs = ft.Tabs(
        length=2,
        selected_index=0,
        expand=True,
        content=ft.Column(
            controls=[
                tab_bar,
                ft.Container(height=8),
                tab_view,
            ],
            expand=True,
        ),
    )

    def _on_tab_click(e: ft.ControlEvent):
        try:
            tabs.selected_index = int(e.data)
            tabs.update()
        except Exception:
            pass

    tab_bar.on_click = _on_tab_click

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Container(width=980, height=650, content=tabs),
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[progress_ring, btn_cancel, btn_save],
    )

    page.show_dialog(dlg)

    def _on_search_change(_e):
        _render_fields()

    search_tf.on_change = _on_search_change
    _render_fields()
    _render_transpose()
