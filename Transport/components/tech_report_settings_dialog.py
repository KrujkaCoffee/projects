from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple, Optional

import re
import asyncio
import flet as ft


@dataclass(frozen=True)
class GroupItem:
    key: str
    group: str
    header: str
    dim: str
    default_visible: bool


@dataclass
class SeriesInfo:
    base: str
    header: str
    tags: set[str]
    idxs: set[float]


DEFAULT_SUFFIX_REGEX = r"^(?P<base>.+)_(?P<tag>[A-Za-z]+)_?(?P<idx>\d+)(?P<rest>(?:_\d+)*)$"

FREQ_RE = re.compile(r"(?i)(?:гц|hz)\s*(?P<a>\d+(?:[.,]\d+)?)|(?P<b>\d+(?:[.,]\d+)?)\s*(?:гц|hz)")


def default_visible(meta: dict) -> bool:
    view = meta.get("view", True)
    if isinstance(view, bool):
        return view
    if isinstance(view, dict):
        return bool(view.get("visible", True))
    return True


def normalize_tags(raw: Any) -> List[str]:
    if raw is None:
        return ["n"]
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.split(",")]
        return [p for p in parts if p]
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return ["n"]


def _slug_base(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^0-9a-zа-я]+", "_", s, flags=re.IGNORECASE)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "series"


def _extract_freq(header: str, comment: str) -> Optional[float]:
    for s in (header or "", comment or ""):
        m = FREQ_RE.search(str(s))
        if not m:
            continue
        raw = m.group("a") or m.group("b")
        if not raw:
            continue
        try:
            return float(raw.replace(",", "."))
        except Exception:
            return None
    return None


def _strip_freq_suffix(header: str) -> str:
    s = (header or "").strip()
    if not s:
        return s
    s2 = re.sub(r"(?:,\s*)?(?:гц|hz)\s*\d+(?:[.,]\d+)?\s*$", "", s, flags=re.IGNORECASE).strip()
    if s2 != s:
        return s2.strip(" ,")
    s2 = re.sub(r"\d+(?:[.,]\d+)?\s*(?:гц|hz)\s*$", "", s, flags=re.IGNORECASE).strip()
    return s2.strip(" ,")


def _fmt_num(x: float) -> str:
    if abs(x - int(x)) < 1e-9:
        return str(int(x))
    return str(x).replace(".", ",")


def _scan_series(
    output_params: Dict[str, dict],
    suffix_regex: str,
    transpose_mode: str,
) -> Tuple[List[str], Dict[str, List[SeriesInfo]]]:
    """Парсинг OUTPUT_PARAMS для вкладки «Транспонирование»."""
    mode = (transpose_mode or "auto").strip().lower()
    if mode not in ("auto", "suffix", "freq"):
        mode = "auto"

    suffix_re = re.compile((suffix_regex or DEFAULT_SUFFIX_REGEX).strip())

    tmp: Dict[str, Dict[str, SeriesInfo]] = {}

    def _add(*, group: str, base: str, header: str, tag: str, idx: float):
        gmap = tmp.setdefault(group, {})
        info = gmap.get(base)
        if info is None:
            info = SeriesInfo(base=base, header=header, tags=set(), idxs=set())
            gmap[base] = info
        info.tags.add(tag)
        info.idxs.add(float(idx))

    for key, meta in (output_params or {}).items():
        if not isinstance(meta, dict):
            meta = {}

        group = str(meta.get("group_name") or "").strip() or "Без группы"
        header = str(meta.get("header") or key)
        comment = str(meta.get("comment") or "")

        if mode in ("auto", "suffix"):
            m = suffix_re.match(str(key))
            if m:
                base = str(m.group("base"))
                tag = str(m.group("tag"))
                try:
                    idx = float(int(m.group("idx")))
                except Exception:
                    idx = None
                if idx is not None:
                    _add(group=group, base=base, header=str(meta.get("header") or base), tag=tag, idx=idx)

        if mode in ("auto", "freq"):
            f = _extract_freq(header, comment)
            if f is not None:
                base_header = _strip_freq_suffix(header) or header
                base = f"F__{_slug_base(base_header)}"
                _add(group=group, base=base, header=base_header, tag="freq", idx=f)

    group_names = sorted(tmp.keys(), key=lambda s: s.lower())
    series_by_group: Dict[str, List[SeriesInfo]] = {}
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
    transpose_tags_init = normalize_tags(cfg.get("transpose_tags"))
    suffix_regex_init = str(cfg.get("suffix_regex") or DEFAULT_SUFFIX_REGEX).strip()

    transpose_mode_init = str(cfg.get("transpose_mode") or "auto").strip().lower()
    if transpose_mode_init == "header_n":
        transpose_mode_init = "freq"
    if transpose_mode_init not in ("auto", "suffix", "freq"):
        transpose_mode_init = "auto"

    debug_sheet_init = bool(cfg.get("debug_sheet", False))
    persist_init = bool(cfg.get("persist", True))

    cfg_t_groups: Dict[str, Any] = cfg.get("transpose_groups") if isinstance(cfg.get("transpose_groups"), dict) else {}
    cfg_t_bases_raw = cfg.get("transpose_bases")
    cfg_t_bases: List[str] | None
    if isinstance(cfg_t_bases_raw, list):
        cfg_t_bases = [str(x) for x in cfg_t_bases_raw if str(x).strip()]
    elif isinstance(cfg_t_bases_raw, str):
        cfg_t_bases = [x.strip() for x in cfg_t_bases_raw.split(",") if x.strip()]
    else:
        cfg_t_bases = None

    items: list[GroupItem] = []
    for key, meta in (output_params or {}).items():
        if not isinstance(meta, dict):
            meta = {}
        group = str(meta.get("group_name") or "").strip() or "Без группы"
        header = str(meta.get("header") or key)
        dim = str(meta.get("dimension") or "")
        items.append(
            GroupItem(
                key=str(key),
                group=group,
                header=header,
                dim=dim,
                default_visible=default_visible(meta),
            )
        )

    items.sort(key=lambda it: (it.group.lower(), it.header.lower()))
    group_names = sorted({it.group for it in items}, key=lambda s: s.lower())
    group_to_items: Dict[str, List[GroupItem]] = {g: [] for g in group_names}
    for it in items:
        group_to_items[it.group].append(it)

    field_state: Dict[str, bool] = {}
    for it in items:
        field_state[it.key] = bool(cfg_fields.get(it.key, it.default_visible))

    group_state: Dict[str, bool] = {}
    for g in group_names:
        group_state[g] = bool(cfg_groups.get(g, True))

    series_group_names, series_by_group = _scan_series(output_params, suffix_regex_init, transpose_mode_init)

    def _calc_all_bases() -> List[str]:
        out: List[str] = []
        for g in series_group_names:
            for info in series_by_group.get(g, []):
                out.append(info.base)
        return out

    all_bases = _calc_all_bases()
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

    transpose_enabled_sw = ft.Switch(label="Включить транспонирование серий", value=transpose_enabled_init)

    transpose_mode_rg = ft.RadioGroup(
        value=transpose_mode_init,
        content=ft.Row(
            controls=[
                ft.Radio(value="auto", label="Авто (суффикс + частота)"),
                ft.Radio(value="suffix", label="По суффиксу ключа"),
                ft.Radio(value="freq", label="По частоте (Гц/Hz)"),
            ],
            wrap=True,
            spacing=12,
        ),
    )

    debug_sheet_sw = ft.Switch(label="Создать дополнительный лист результатов (Ссылки на все результаты одной колонкой)", value=debug_sheet_init)
    persist_sw = ft.Switch(label="Сохранять настройки на этом устройстве", value=persist_init)

    transpose_tags_tf = ft.TextField(
        label="Теги серий (через запятую) — только для суффиксного режима",
        value=", ".join(transpose_tags_init),
        hint_text="например: n, out",
        dense=True,
    )
    suffix_regex_tf = ft.TextField(
        label="Regex суффикса — только для суффиксного режима",
        value=suffix_regex_init,
        dense=True,
    )

    fields_body_ref = ft.Ref[ft.Column]()
    transpose_body_ref = ft.Ref[ft.Column]()

    progress_ring = ft.ProgressRing(width=18, height=18, visible=False)
    btn_cancel = ft.TextButton("Отмена")
    btn_save = ft.FilledButton("Сохранить")

    _closing = {"busy": False}

    def _build_cfg() -> Dict[str, Any]:
        out: Dict[str, Any] = dict(cfg)

        fields_overrides: Dict[str, bool] = {}
        for it in items:
            cur = bool(field_state.get(it.key, True))
            if cur != bool(it.default_visible):
                fields_overrides[it.key] = cur

        groups_overrides: Dict[str, bool] = {}
        for g in group_names:
            cur = bool(group_state.get(g, True))
            if cur is not True:
                groups_overrides[g] = cur

        t_groups_overrides: Dict[str, bool] = {}
        for g in series_group_names:
            cur = bool(transpose_group_state.get(g, True))
            if cur is not True:
                t_groups_overrides[g] = cur

        enabled_bases = sorted([b for b, v in transpose_base_state.items() if bool(v)], key=lambda s: s.lower())
        if not all_bases_set:
            transpose_bases_out = None
        else:
            if set(enabled_bases) == set(all_bases_set):
                transpose_bases_out = None
            else:
                transpose_bases_out = enabled_bases

        out["fields"] = fields_overrides
        out["groups"] = groups_overrides
        out["transpose_enabled"] = bool(transpose_enabled_sw.value)
        out["transpose_mode"] = str(transpose_mode_rg.value or "auto")
        out["transpose_tags"] = normalize_tags(transpose_tags_tf.value)
        out["suffix_regex"] = (suffix_regex_tf.value or DEFAULT_SUFFIX_REGEX).strip()
        out["debug_sheet"] = bool(debug_sheet_sw.value)
        out["persist"] = bool(persist_sw.value)

        if t_groups_overrides:
            out["transpose_groups"] = t_groups_overrides
        else:
            out.pop("transpose_groups", None)

        if transpose_bases_out is not None:
            out["transpose_bases"] = transpose_bases_out
        else:
            out.pop("transpose_bases", None)

        return out

    fields_dynamic_ref = ft.Ref[ft.Column]()

    group_cb_by_name: Dict[str, ft.Checkbox] = {}
    group_cnt_by_name: Dict[str, ft.Text] = {}
    group_children_by_name: Dict[str, ft.Column] = {}
    group_block_by_name: Dict[str, ft.Column] = {}
    group_expand_btn_by_name: Dict[str, ft.IconButton] = {}

    field_cb_by_key: Dict[str, ft.Checkbox] = {}

    _group_built: Dict[str, bool] = {g: False for g in group_names}
    _group_building: set[str] = set()

    _search_seq = {"n": 0}

    def _set_field_value(key: str, val: bool, *, source_cb: ft.Checkbox | None = None):
        field_state[key] = bool(val)
        cb = field_cb_by_key.get(key)
        if cb is not None and cb is not source_cb:
            cb.value = bool(val)
            try:
                cb.update()
            except Exception:
                pass

    def _on_group_toggle(e: ft.ControlEvent):
        gg = str(e.control.data)
        group_state[gg] = bool(e.control.value)

    def _on_field_toggle(e: ft.ControlEvent):
        kk = str(e.control.data)
        _set_field_value(kk, bool(e.control.value), source_cb=e.control)

    def _bulk_apply_all(val: bool):
        for it in items:
            field_state[it.key] = bool(val)
        for g in group_names:
            group_state[g] = True

        for cb in group_cb_by_name.values():
            cb.value = True
        for cb in field_cb_by_key.values():
            cb.value = bool(val)

        _apply_search_now()

    def _bulk_apply_none():
        for it in items:
            field_state[it.key] = False
        for g in group_names:
            group_state[g] = False

        for cb in group_cb_by_name.values():
            cb.value = False
        for cb in field_cb_by_key.values():
            cb.value = False

        _apply_search_now()

    def _bulk_apply_reset():
        for it in items:
            field_state[it.key] = bool(it.default_visible)
        for g in group_names:
            group_state[g] = True

        for cb in group_cb_by_name.values():
            cb.value = True
        for it_key, cb in field_cb_by_key.items():
            cb.value = bool(field_state.get(it_key, True))

        _apply_search_now()

    bulk_buttons = ft.Row(
        controls=[
            ft.FilledButton("Все", on_click=lambda _e: _bulk_apply_all(True)),
            ft.OutlinedButton("Снять все галки", on_click=lambda _e: _bulk_apply_none()),
            ft.TextButton("Сброс", on_click=lambda _e: _bulk_apply_reset()),
        ],
        spacing=10,
    )

    fields_hint = ft.Text(
        "Галочка группы выключает группу целиком в Технологическом отчёте.",
        size=12,
        opacity=0.8,
    )

    def _build_group_children_sync(g: str) -> List[ft.Control]:
        out: List[ft.Control] = []
        for it in group_to_items.get(g, []):
            cb = ft.Checkbox(value=bool(field_state.get(it.key, True)), data=it.key, on_change=_on_field_toggle)
            field_cb_by_key[it.key] = cb
            subtitle = it.key
            if it.dim:
                subtitle = f"{subtitle} · {it.dim}"
            out.append(
                ft.ListTile(
                    leading=cb,
                    title=ft.Text(it.header),
                    subtitle=ft.Text(subtitle, size=11, opacity=0.75),
                    dense=True,
                )
            )
        return out

    async def _build_group_children_async(g: str):
        out: List[ft.Control] = []
        group_items = group_to_items.get(g, [])
        for i, it in enumerate(group_items):
            cb = ft.Checkbox(value=bool(field_state.get(it.key, True)), data=it.key, on_change=_on_field_toggle)
            field_cb_by_key[it.key] = cb
            subtitle = it.key
            if it.dim:
                subtitle = f"{subtitle} · {it.dim}"
            out.append(
                ft.ListTile(
                    leading=cb,
                    title=ft.Text(it.header),
                    subtitle=ft.Text(subtitle, size=11, opacity=0.75),
                    dense=True,
                )
            )
            if i and (i % 60 == 0):
                await asyncio.sleep(0)
        return out

    def _toggle_group_expand(e: ft.ControlEvent):
        g = str(e.control.data)
        col = group_children_by_name.get(g)
        if col is None:
            return

        if _group_built.get(g, False):
            col.visible = not bool(col.visible)
            btn = group_expand_btn_by_name.get(g)
            if btn is not None:
                btn.icon = ft.Icons.EXPAND_MORE if col.visible else ft.Icons.CHEVRON_RIGHT
            try:
                group_block_by_name[g].update()
            except Exception:
                pass
            return

        if g in _group_building:
            col.visible = not bool(col.visible)
            btn = group_expand_btn_by_name.get(g)
            if btn is not None:
                btn.icon = ft.Icons.EXPAND_MORE if col.visible else ft.Icons.CHEVRON_RIGHT
            try:
                group_block_by_name[g].update()
            except Exception:
                pass
            return

        _group_building.add(g)
        col.controls = [ft.Row(controls=[ft.ProgressRing(width=16, height=16), ft.Text("Загрузка...")], spacing=8)]
        col.visible = True
        btn = group_expand_btn_by_name.get(g)
        if btn is not None:
            btn.icon = ft.Icons.EXPAND_MORE
        try:
            group_block_by_name[g].update()
        except Exception:
            pass

        async def _task():
            await asyncio.sleep(0)
            if _closing["busy"]:
                return
            try:
                children = await _build_group_children_async(g)
            except Exception:
                children = _build_group_children_sync(g)

            col.controls = children
            _group_built[g] = True
            _group_building.discard(g)
            try:
                col.update()
            except Exception:
                pass

        page.run_task(_task)

    def _build_group_blocks() -> list[ft.Control]:
        blocks: list[ft.Control] = []
        for g in group_names:
            g_items_cnt = len(group_to_items.get(g, []))

            exp_btn = ft.IconButton(
                icon=ft.Icons.CHEVRON_RIGHT,
                tooltip="Развернуть/свернуть",
                data=g,
                on_click=_toggle_group_expand,
            )
            group_expand_btn_by_name[g] = exp_btn

            grp_cb = ft.Checkbox(value=bool(group_state.get(g, True)), data=g, on_change=_on_group_toggle)
            group_cb_by_name[g] = grp_cb

            cnt_txt = ft.Text(f"({g_items_cnt})", size=12, opacity=0.7)
            group_cnt_by_name[g] = cnt_txt

            children_col = ft.Column(controls=[], visible=False, spacing=0)
            group_children_by_name[g] = children_col

            header_row = ft.Row(
                controls=[exp_btn, grp_cb, ft.Text(g, weight=ft.FontWeight.W_600), cnt_txt],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

            block = ft.Column(
                controls=[header_row, ft.Container(content=children_col, padding=ft.padding.only(left=28))],
                spacing=0,
            )
            group_block_by_name[g] = block
            blocks.append(block)
        return blocks

    _group_blocks: List[ft.Control] = _build_group_blocks()

    def _build_search_results(q: str) -> List[ft.Control]:
        q = (q or "").strip().lower()
        if not q:
            return []

        matched = [it for it in items if (q in it.header.lower()) or (q in it.key.lower())]

        limit = 400
        sliced = matched[:limit]

        out: List[ft.Control] = [
            ft.Text(
                f"Найдено: {len(matched)}" + (f" (показано первые {limit})" if len(matched) > limit else ""),
                size=12,
                opacity=0.75,
            )
        ]

        for it in sliced:
            cb = ft.Checkbox(value=bool(field_state.get(it.key, True)), data=it.key, on_change=_on_field_toggle)
            subtitle = it.key
            if it.dim:
                subtitle = f"{subtitle} · {it.dim}"
            title = ft.Text(f"[{it.group}] {it.header}")
            out.append(
                ft.ListTile(
                    leading=cb,
                    title=title,
                    subtitle=ft.Text(subtitle, size=11, opacity=0.75),
                    dense=True,
                )
            )
        return out

    def _apply_search_now():
        if fields_dynamic_ref.current is None:
            return

        q = (search_tf.value or "").strip().lower()
        if q:
            fields_dynamic_ref.current.controls = _build_search_results(q)
        else:
            fields_dynamic_ref.current.controls = _group_blocks

        try:
            fields_dynamic_ref.current.update()
        except Exception:
            pass

    async def _debounced_search(seq: int):
        await asyncio.sleep(0.35)
        if _closing["busy"]:
            return
        if seq != _search_seq["n"]:
            return
        _apply_search_now()

    def _on_search_change(_e: ft.ControlEvent):
        _search_seq["n"] += 1
        seq = _search_seq["n"]
        page.run_task(_debounced_search, seq)
        _apply_search_now()

    _transpose_rendered = {"done": False}

    def _render_transpose():
        if transpose_body_ref.current is None:
            return

        tiles: List[ft.Control] = []

        tiles.append(
            ft.Text(
                "Транспонирование серий",
                size=12,
                opacity=0.85,
            )
        )

        tiles.append(transpose_enabled_sw)
        # tiles.append(ft.Text("Метод транспонирования:", size=12, opacity=0.85))
        # tiles.append(transpose_mode_rg)
        tiles.append(ft.Row([debug_sheet_sw, persist_sw], wrap=True, spacing=12))

        if not series_group_names:
            tiles.append(ft.Text("Серийные поля не найдены (для текущего режима).", size=12, opacity=0.75))
        else:
            t_base_cb_by_base: Dict[str, ft.Checkbox] = {}
            t_group_children_by_name: Dict[str, ft.Column] = {}
            t_group_btn_by_name: Dict[str, ft.IconButton] = {}
            t_group_built: Dict[str, bool] = {g: False for g in series_group_names}
            t_group_building: set[str] = set()

            def _on_t_group_toggle(e: ft.ControlEvent):
                gg = str(e.control.data)
                transpose_group_state[gg] = bool(e.control.value)

            def _on_t_base_toggle(e: ft.ControlEvent):
                bb = str(e.control.data)
                transpose_base_state[bb] = bool(e.control.value)

            def _bases_all(val: bool):
                for b in all_bases_set:
                    transpose_base_state[b] = bool(val)
                for cb in t_base_cb_by_base.values():
                    cb.value = bool(val)
                try:
                    transpose_body_ref.current.update()
                except Exception:
                    pass

            tiles.append(
                ft.Row(
                    controls=[
                        ft.FilledButton("Все серии", on_click=lambda _e: _bases_all(True)),
                        ft.OutlinedButton("Ни одной", on_click=lambda _e: _bases_all(False)),
                    ],
                    spacing=10,
                )
            )

            async def _build_group_rows_async(g: str) -> List[ft.Control]:
                out: List[ft.Control] = []
                infos = series_by_group.get(g, [])
                for i, info in enumerate(infos):
                    tags_txt = ", ".join(sorted(info.tags, key=lambda s: s.lower()))
                    idx_txt = "?"
                    if info.idxs:
                        mn, mx = min(info.idxs), max(info.idxs)
                        if abs(mn - mx) < 1e-9:
                            idx_txt = _fmt_num(mn)
                        else:
                            idx_txt = f"{_fmt_num(mn)}..{_fmt_num(mx)}"
                        idx_txt = f"{idx_txt} (n={len(info.idxs)})"

                    cb = ft.Checkbox(
                        value=bool(transpose_base_state.get(info.base, True)),
                        data=info.base,
                        on_change=_on_t_base_toggle,
                    )
                    t_base_cb_by_base[info.base] = cb

                    out.append(
                        ft.ListTile(
                            leading=cb,
                            title=ft.Text(info.header),
                            subtitle=ft.Text(
                                f"base: {info.base} · тип: {tags_txt} · индексы/частоты: {idx_txt}",
                                size=11,
                                opacity=0.75,
                            ),
                            dense=True,
                        )
                    )

                    if i and (i % 60 == 0):
                        await asyncio.sleep(0)
                return out

            def _toggle_t_group_expand(e: ft.ControlEvent):
                g = str(e.control.data)
                col = t_group_children_by_name.get(g)
                if col is None:
                    return

                if t_group_built.get(g, False):
                    col.visible = not bool(col.visible)
                    btn = t_group_btn_by_name.get(g)
                    if btn is not None:
                        btn.icon = ft.Icons.EXPAND_MORE if col.visible else ft.Icons.CHEVRON_RIGHT
                    try:
                        transpose_body_ref.current.update()
                    except Exception:
                        pass
                    return

                if g in t_group_building:
                    col.visible = not bool(col.visible)
                    btn = t_group_btn_by_name.get(g)
                    if btn is not None:
                        btn.icon = ft.Icons.EXPAND_MORE if col.visible else ft.Icons.CHEVRON_RIGHT
                    try:
                        transpose_body_ref.current.update()
                    except Exception:
                        pass
                    return

                t_group_building.add(g)
                col.controls = [ft.Row(controls=[ft.ProgressRing(width=16, height=16), ft.Text("Загрузка...")], spacing=8)]
                col.visible = True
                btn = t_group_btn_by_name.get(g)
                if btn is not None:
                    btn.icon = ft.Icons.EXPAND_MORE
                try:
                    transpose_body_ref.current.update()
                except Exception:
                    pass

                async def _task():
                    await asyncio.sleep(0)
                    if _closing["busy"]:
                        return
                    try:
                        rows = await _build_group_rows_async(g)
                    except Exception:
                        rows = []
                    col.controls = rows
                    t_group_built[g] = True
                    t_group_building.discard(g)
                    try:
                        col.update()
                    except Exception:
                        pass

                page.run_task(_task)

                rows_sync: List[ft.Control] = []
                for info in series_by_group.get(g, []):
                    cb = ft.Checkbox(
                        value=bool(transpose_base_state.get(info.base, True)),
                        data=info.base,
                        on_change=_on_t_base_toggle,
                    )
                    t_base_cb_by_base[info.base] = cb
                    tags_txt = ", ".join(sorted(info.tags, key=lambda s: s.lower()))
                    idx_txt = f"n={len(info.idxs)}"
                    rows_sync.append(
                        ft.ListTile(
                            leading=cb,
                            title=ft.Text(info.header),
                            subtitle=ft.Text(f"base: {info.base} · тип: {tags_txt} · {idx_txt}", size=11, opacity=0.75),
                            dense=True,
                        )
                    )
                col.controls = rows_sync
                t_group_built[g] = True
                t_group_building.discard(g)
                try:
                    col.update()
                except Exception:
                    pass

            for g in series_group_names:
                infos = series_by_group.get(g, [])
                if not infos:
                    continue

                exp_btn = ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    tooltip="Развернуть/свернуть",
                    data=g,
                    on_click=_toggle_t_group_expand,
                )
                t_group_btn_by_name[g] = exp_btn

                g_sw = ft.Switch(
                    value=bool(transpose_group_state.get(g, True)),
                    label="Трансп.",
                    data=g,
                    on_change=_on_t_group_toggle,
                )

                children_col = ft.Column(controls=[], visible=False, spacing=0)
                t_group_children_by_name[g] = children_col

                header_row = ft.Row(
                    controls=[
                        exp_btn,
                        ft.Text(g, weight=ft.FontWeight.W_600),
                        ft.Text(f"({len(infos)})", size=12, opacity=0.7),
                        ft.Container(expand=True),
                        g_sw,
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )

                tiles.append(
                    ft.Column(
                        controls=[header_row, ft.Container(content=children_col, padding=ft.padding.only(left=28))],
                        spacing=0,
                    )
                )

        transpose_body_ref.current.controls = tiles
        transpose_body_ref.current.update()

    def _ensure_transpose_rendered():
        if _transpose_rendered["done"]:
            return
        _transpose_rendered["done"] = True

        if transpose_body_ref.current is None:
            return

        transpose_body_ref.current.controls = [
            ft.Row(controls=[ft.ProgressRing(width=18, height=18), ft.Text("Загрузка вкладки...")], spacing=10)
        ]
        try:
            transpose_body_ref.current.update()
        except Exception:
            pass

        async def _task():
            await asyncio.sleep(0)
            if _closing["busy"]:
                return
            _render_transpose()

        page.run_task(_task)
        _render_transpose()

    def _rescan_and_rerender():
        nonlocal series_group_names, series_by_group, all_bases, all_bases_set
        series_group_names, series_by_group = _scan_series(output_params, suffix_regex_tf.value or DEFAULT_SUFFIX_REGEX, transpose_mode_rg.value)
        all_bases = _calc_all_bases()
        all_bases_set = set(all_bases)

        for g in series_group_names:
            transpose_group_state.setdefault(g, True)
        for b in all_bases_set:
            transpose_base_state.setdefault(b, True)

        for g in list(transpose_group_state.keys()):
            if g not in series_group_names:
                transpose_group_state.pop(g, None)
        for b in list(transpose_base_state.keys()):
            if b not in all_bases_set:
                transpose_base_state.pop(b, None)

        if _transpose_rendered["done"]:
            _render_transpose()

    def _on_mode_change(_e: ft.ControlEvent):
        _rescan_and_rerender()

    transpose_mode_rg.on_change = _on_mode_change

    def _close(save: bool):
        if _closing["busy"]:
            return
        _closing["busy"] = True

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
        tabs=[ft.Tab(label="Поля"), ft.Tab(label="Транспонирование")]
    )

    tab_view = ft.TabBarView(
        controls=[fields_tab, transpose_tab],
        expand=True,
    )

    tabs = ft.Tabs(
        length=2,
        selected_index=0,
        expand=True,
        content=ft.Column(
            controls=[tab_bar, ft.Container(height=8), tab_view],
            expand=True,
        ),
    )

    def _on_tab_click(e: ft.ControlEvent):
        try:
            tabs.selected_index = int(e.data)
            tabs.update()
        except Exception:
            pass
        if str(e.data) == "1":
            _ensure_transpose_rendered()

    tab_bar.on_click = _on_tab_click

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Container(width=980, height=650, content=tabs),
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[progress_ring, btn_cancel, btn_save],
    )
    page.show_dialog(dlg)

    search_tf.on_change = _on_search_change

    def _mount_fields_tab():
        if fields_body_ref.current is None:
            return
        fields_body_ref.current.controls = [
            ft.Row([search_tf, bulk_buttons], spacing=12),
            fields_hint,
            ft.Container(height=6),
            ft.Column(ref=fields_dynamic_ref, controls=_group_blocks, spacing=4),
        ]
        try:
            fields_body_ref.current.update()
        except Exception:
            pass
        _apply_search_now()

    def _mount_transpose_placeholder():
        if transpose_body_ref.current is None:
            return
        transpose_body_ref.current.controls = [
            ft.Text(
                "Откройте вкладку «Транспонирование», чтобы загрузить список серий.",
                size=12,
                opacity=0.75,
            )
        ]
        try:
            transpose_body_ref.current.update()
        except Exception:
            pass

    async def _post_open_init():
        await asyncio.sleep(0)
        _mount_fields_tab()
        _mount_transpose_placeholder()

    page.run_task(_post_open_init)
