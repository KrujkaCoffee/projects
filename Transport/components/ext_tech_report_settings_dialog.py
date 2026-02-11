from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

import re
import asyncio
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
_DEFAULT_GZ_FORM = "Среднегеометрическая частота, Гц"


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
    """Сканирует OUTPUT_PARAMS и находит серии по suffix_regex. """
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
        infos = list(tmp[g].values())
        infos.sort(key=lambda x: (x.header.lower(), x.base.lower()))
        series_by_group[g] = infos

    return group_names, series_by_group


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

    _item_lc = {it.key: (it.header.lower(), it.key.lower(), it.group.lower()) for it in items}
    _group_lc = {g: g.lower() for g in group_names}

    field_state: Dict[str, bool] = {}
    for it in items:
        field_state[it.key] = bool(cfg_fields.get(it.key, it.default_visible))

    group_state: Dict[str, bool] = {}
    for g in group_names:
        group_state[g] = bool(cfg_groups.get(g, True))

    series_group_names, series_by_group = _scan_series(output_params, suffix_regex_init)
    all_bases: List[str] = []
    for g in series_group_names:
        for info in series_by_group.get(g, []):
            all_bases.append(info.base)
    all_bases_set = set(all_bases)

    transpose_group_state: Dict[str, bool] = {}
    for g in series_group_names:
        transpose_group_state[g] = bool(cfg_t_groups.get(g, True))

    transpose_base_state: Dict[str, bool] = {}
    if cfg_t_bases is None:
        for b in all_bases_set:
            transpose_base_state[b] = True
    else:
        allowed = set(cfg_t_bases)
        for b in all_bases_set:
            transpose_base_state[b] = b in allowed

    search_tf = ft.TextField(
        label="Поиск",
        hint_text="по имени / ключу параметра",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        dense=True,
    )

    search_scope_dd = ft.Dropdown(
        value="params",
        dense=True,
        width=220,
        options=[
            ft.dropdown.Option("params", "По параметрам"),
            ft.dropdown.Option("groups", "По группам"),
            ft.dropdown.Option("both", "Параметры + группы"),
        ],
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
    )

    fields_body_ref = ft.Ref[ft.Column]()
    transpose_body_ref = ft.Ref[ft.Column]()

    # action controls (to disable during save)
    progress_ring = ft.ProgressRing(width=18, height=18, visible=False)
    btn_cancel = ft.TextButton("Отмена")
    btn_save = ft.FilledButton("Сохранить")

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
        # ---- search/render control ----
    _search_ctl = {"seq": 0, "limit": 200}

    def _schedule_fields_render(*, reset_limit: bool = False):
        """Debounce для тяжёлого рендера при вводе в поиск/переключении режима."""
        if reset_limit:
            _search_ctl["limit"] = 200
        _search_ctl["seq"] += 1
        seq = _search_ctl["seq"]

        async def _debounced():
            await asyncio.sleep(0.35)
            if seq != _search_ctl["seq"]:
                return
            _render_fields()

        try:
            if hasattr(page, "run_task"):
                page.run_task(_debounced)
            else:
                asyncio.create_task(_debounced())
        except Exception:
            try:
                asyncio.create_task(_debounced())
            except Exception:
                _render_fields()

    def _render_fields():
        q_raw = (search_tf.value or "").strip()
        q = q_raw.lower()
        mode = str(search_scope_dd.value or "params")
        limit = int(_search_ctl.get("limit", 200) or 200)

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

        tiles.append(ft.Row([search_tf, search_scope_dd, buttons], spacing=12))
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

        def _field_tile(it: _Item) -> ft.Control:
            cb = ft.Checkbox(value=bool(field_state.get(it.key, True)), data=it.key, on_change=_on_field_toggle)
            subtitle = f"{it.group} · {it.key}"
            if it.dim:
                subtitle = f"{subtitle} · {it.dim}"
            return ft.ListTile(
                leading=cb,
                title=ft.Text(it.header),
                subtitle=ft.Text(subtitle, size=11, opacity=0.75),
                dense=True,
            )

        # ---- режим: поиск по параметрам (плоский список + лимит) ----
        if mode == "params" and q and len(q) >= 2:
            matched: List[_Item] = []
            for it in items:
                h_lc, k_lc, _g_lc = _item_lc[it.key]
                if q in h_lc or q in k_lc:
                    matched.append(it)

            total = len(matched)
            shown = matched[:limit]

            tiles.append(ft.Text(f"Найдено: {total}. Показано: {len(shown)}.", size=12, opacity=0.8))

            if not shown:
                tiles.append(ft.Text("Ничего не найдено.", size=12, opacity=0.75))
            else:
                tiles.extend(_field_tile(it) for it in shown)

            if total > limit:
                def _more(_e):
                    _search_ctl["limit"] = min(total, limit + 200)
                    _render_fields()

                tiles.append(ft.OutlinedButton(f"Показать ещё (+200)", on_click=_more))

            fields_body_ref.current.controls = tiles
            fields_body_ref.current.update()
            return

        # ---- иначе: показываем группы (поиск по группам / смешанный / без поиска) ----
        match_by_group: Dict[str, List[_Item]] = {}
        if q and len(q) >= 2 and mode in ("both",):
            for it in items:
                h_lc, k_lc, _g_lc = _item_lc[it.key]
                if q in h_lc or q in k_lc:
                    match_by_group.setdefault(it.group, []).append(it)

        # в "groups" мы ищем только по имени группы
        # в "both" — группа проходит, если совпала по имени ИЛИ есть совпадения по параметрам
        groups_to_show: List[Tuple[str, List[_Item], bool]] = []  # (group, items_for_group, is_match_items_only)
        for g in group_names:
            g_lc = _group_lc.get(g, g.lower())
            group_name_match = bool(q) and (q in g_lc)

            if mode == "groups":
                if q and not group_name_match:
                    continue
                groups_to_show.append((g, group_to_items.get(g, []), False))
                continue

            if mode == "both" and q and len(q) >= 2:
                if group_name_match:
                    groups_to_show.append((g, group_to_items.get(g, []), False))
                elif g in match_by_group:
                    groups_to_show.append((g, match_by_group.get(g, []), True))
                else:
                    continue
            else:
                # без поиска или q слишком короткий — обычный список групп
                groups_to_show.append((g, group_to_items.get(g, []), False))

        if q and len(q) == 1 and mode in ("params", "both"):
            tiles.append(ft.Text("Для поиска по параметрам введите минимум 2 символа.", size=12, opacity=0.75))

        for g, group_items, match_only in groups_to_show:
            grp_cb = ft.Checkbox(value=bool(group_state.get(g, True)), data=g, on_change=_on_group_toggle)

            cnt_txt = f"({len(group_items)})"
            if match_only and q:
                cnt_txt = f"({len(group_items)} совп.)"

            title_row = ft.Row(
                controls=[
                    grp_cb,
                    ft.Text(g, weight=ft.FontWeight.W_600),
                    ft.Text(cnt_txt, size=12, opacity=0.7),
                ],
                spacing=8,
            )

            tile = ft.ExpansionTile(
                title=title_row,
                maintain_state=True,
                expanded=False,
                controls=[],  # lazy
            )

            def _mk_on_tile_change(items_for_group: List[_Item]):
                def _on_tile_change(e):
                    if str(getattr(e, "data", "")) != "true":
                        return
                    # build only once for this tile instance
                    if getattr(e.control, "controls", None):
                        return
                    e.control.controls = [_field_tile(it) for it in items_for_group]
                    e.control.update()
                return _on_tile_change

            tile.on_change = _mk_on_tile_change(group_items)
            tiles.append(tile)

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

    # ---- dialog close ----
    def _close(save: bool):
        if _closing["busy"]:
            return
        _closing["busy"] = True

        # instant UI feedback
        progress_ring.visible = True
        btn_save.disabled = True
        btn_cancel.disabled = True
        try:
            dlg.update()
        except Exception:
            pass

        try:
            if save:
                on_save(_build_cfg())
        finally:
            try:
                # prefer close dialog without global page.update()
                if hasattr(page, "close"):
                    page.close(dlg)
                else:
                    dlg.open = False
                    dlg.update()
            except Exception:
                pass

    btn_cancel.on_click = lambda _e: _close(False)
    btn_save.on_click = lambda _e: _close(True)

    # ---- tabs layout (Flet 0.80+) ----
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

    # open
    try:
        page.show_dialog(dlg)
        # if hasattr(page, "open"):
        #     page.open(dlg)
        # else:
        #     page.dialog = dlg
        #     dlg.open = True
        #     page.update()
    except Exception:
        page.dialog = dlg
        dlg.open = True
        page.update()
    # initial render
    def _on_search_change(_e):
        _schedule_fields_render(reset_limit=True)

    search_tf.on_change = _on_search_change
    search_scope_dd.on_change = _on_search_change

    _render_fields()
    _render_transpose()
