from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional, NamedTuple

import json
import os
import re
import tempfile

from PyQt5 import QtWidgets

from project_cust_38 import Cust_mes as CMS
from project_cust_38 import Cust_config as CFG
from project_cust_38 import Cust_Qt as CQT
from project_cust_38 import Cust_Functions as F
import classes as CLSS


@dataclass(frozen=True)
class TaskBind:
    idx: int
    dse_id: Optional[int]
    qty_text: str
    dse_nn: str
    dse_name: str
    oper_num: str
    oper_name: str

    @property
    def oper_key(self) -> str:
        return f'{self.oper_num}${self.oper_name}'.strip()

    def dse_key(self) -> str:
        return f'{self.dse_name}${self.dse_nn}'.strip()


@dataclass
class TaskBuildOptions:
    sep: str = '|'
    group_by_dse: bool = True
    show_dse_header: bool = True
    show_oper_header: bool = True
    show_qty_in_oper_header: bool = True
    indent: str = '    '
    bullet_lists: bool = True
    section_for_render_naryad_info: str = 'Операция'
    group_by_sections = ('Материалы', )

class Option(NamedTuple):
    name: str
    alias: str = None
    exclude: bool = False
    section: str = None
    sort_rank: int = 0

KEY_ALIASES = (
    # Системные
    Option(name='dreva_kod', exclude=True),
    Option(name='Код_ERP', exclude=True),
    Option(name='Код_ERP', exclude=True),
    Option(name='Мат_кд', exclude=True),
    Option(name='Параметрика', exclude=True),
    Option(name='ДСЕ', exclude=True, alias='ДСЕ Наименование (По наряду)'),
    Option(name='ДСЕ_ID', exclude=True, alias='ДСЕ ID (По наряду)'),
    Option(name='Опер колво', exclude=True, alias='Количество (По наряду)'),
    Option(name='Способы_получения_материала', exclude=True),
    Option(name='Материалы_Статья_калькуляции', exclude=True),
    Option(name='Опер_вспомогательная', exclude=True),
    # Расшифровки
    Option(name='Номерпп', alias='ID'),
    Option(name='ПКИ', alias='Покупное'),
    Option(name='Количество', alias='Количество (общее)'),
    Option(name='Количество_ед', alias='Количество (На единицу)'),
    Option(name='Прим', alias='Примечание'),
    Option(name='Опер_профессия_наименование', alias='Наименование профессии'),
    Option(name='Опер_оборудование_наименование', alias='Наименование оборудования'),
    Option(name='Опер_оборудование_код', alias='Код оборудования'),
    Option(name='Опер_профессия_код', alias='Код профессии'),
    Option(name='Опер_наименование_подразделения', alias='Наименование подразделения'),
    Option(name='Опер_наименование', alias='Наименование операции'),
    Option(name='Опер_оснастка', alias='Оснастка'),
    Option(name='Опер_номер', alias='Номер операции'),
    Option(name='Опер_код', alias='Код операции'),
    Option(name='Опер_РЦ_код', alias='Код рабочего центра'),
    Option(name='Опер_РЦ_наименование', alias='Наименование рабочего центра'),
    Option(name='Опер_документы', alias='Документы операции'),

    Option(name='Материалы[]', exclude=True),
    Option(name='Список', alias='Материалы', exclude=True),
    Option(name='Мат_параметрика', exclude=True, section='Материалы', sort_rank=3),
    Option(name='Мат_код', alias='Код материала', section='Материалы', sort_rank=2),
    Option(name='Мат_наименование', alias='Наименование', section='Материалы', sort_rank=1),
    Option(name='Мат_ед_изм', alias='Ед. изм.', section='Материалы', sort_rank=6),
    Option(name='Мат_норма', alias='Норма', section='Материалы', sort_rank=4),
    Option(name='Мат_норма_ед', alias='Норма на единицу', section='Материалы', sort_rank=5),
    Option(name='Мат_норма_по_наряду', alias='Норма по наряду', section='Материалы', sort_rank=7, exclude=True),

)


def _humanize_raw_key(key: str) -> str:
    """Преобразование ключа в читабельный (если не задан алиас)"""
    s = str(key).strip()
    s = s.replace('_', ' ').replace('[]', '')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _alias_for_key(key: str) -> str:
    for option in KEY_ALIASES:
        if option.name == key:
            return option.alias or key
    return _humanize_raw_key(key)

def _is_key_excluded(key: str) -> bool:
    return any(option.name == key and option.exclude for option in KEY_ALIASES)


def _strip_list_suffix(token: str) -> tuple[str, bool]:
    token = token.strip()
    if token.endswith('[]'):
        return token[:-2], True
    return token, False


def canonicalize_selector(selector: str) -> str:
    s = (selector or '').strip().strip('.')
    if not s: return s

    first = s.split('.', 1)[0]
    first_clean, _ = _strip_list_suffix(first)

    if first_clean in ('ДСЕ', 'Операция', 'Материалы', 'Наряд'):
        return s

    if first_clean == 'Операции':
        return 'ДСЕ.' + s
    if first_clean.startswith('Опер_') or first_clean in ('Переходы',):
        return 'Операция.' + s
    if first_clean in ('Опер_колво', 'ДСЕ_ID', 'ДСЕ'):
        return 'Наряд.' + s
    if first_clean.startswith('Мат_') or first_clean == 'Материалы':
        return 'Материалы.' + s
    return 'ДСЕ.' + s


def print_label_for_selector(selector: str) -> str:
    sel = canonicalize_selector(selector)
    tokens = [t for t in sel.split('.') if t.strip()]
    if not tokens:
        return selector
    leaf_key, leaf_is_list = _strip_list_suffix(tokens[-1])
    leaf_alias = _alias_for_key(leaf_key)
    return leaf_alias


def _split_pipe(raw: Any, sep: str = '|') -> list[str]:
    if raw is None:
        return ['']
    return [p for p in str(raw).split(sep)]


def parse_naryad_bindings(
    task_instance: CMS.Naryads
) -> list[TaskBind]:
    bindings: list[TaskBind] = []
    for i, param in enumerate(task_instance.params):
        dse_data = param['ДСЕ'].split('$', maxsplit=1)
        nn, name = dse_data, ''
        if len(dse_data) == 2:
            nn, name = dse_data
        bindings.append(
            TaskBind(
                idx=i,
                dse_id=param['ДСЕ_ID'],
                qty_text=str(param['Опер_колво']).strip(),
                dse_name=name,
                dse_nn=nn,
                oper_num=str(param['Операции_номер']),
                oper_name=param['Операции_имя']
            )
        )
    return bindings


def index_route(route: list[dict] | None) -> tuple[dict[int, dict], dict[tuple[int, str], dict]]:
    dse_by_id: dict[int, dict] = {}
    op_by_dse_and_key: dict[tuple[int, str], dict] = {}

    for dse in route or []:
        dse_id = F.valm(dse.get('Номерпп'))
        if dse_id is None:
            continue
        dse_by_id[dse_id] = dse

        for op in dse.get('Операции') or []:
            op_num = str(op.get('Опер_номер') or '').strip()
            op_name = str(op.get('Опер_наименование') or '').strip()
            key = f'{op_num}${op_name}'.strip()
            op_by_dse_and_key[(dse_id, key)] = op

            if re.fullmatch(r'\d+', op_num):
                try:
                    op_by_dse_and_key[(dse_id, f'{int(op_num)}${op_name}'.strip())] = op
                    op_by_dse_and_key[(dse_id, f'{str(int(op_num)).zfill(len(op_num))}${op_name}'.strip())] = op
                except Exception:
                    pass

    return dse_by_id, op_by_dse_and_key


def _binding_context(b: TaskBind) -> dict[str, Any]:
    return {
        'idx': b.idx,
        'ДСЕ_ID': b.dse_id,
        'ДСЕ': b.dse_key(),
        'Операции': b.oper_key,
        'Опер_колво': b.qty_text,
    }


def eval_selector(selector: str, ctx: dict[str, Any]) -> tuple[list[str], bool]:
    sel = canonicalize_selector(selector)
    if not sel:
        return ([], False)

    tokens = [t for t in sel.split('.') if t.strip()]
    cur: list[Any] = [ctx]
    list_mode = False

    for t in tokens:
        key, is_list = _strip_list_suffix(t)
        list_mode = list_mode or is_list
        nxt: list[Any] = []

        for v in cur:
            if v is None:
                continue

            if isinstance(v, dict):
                val = v.get(key)
            else:
                val = getattr(v, key, None)

            if is_list:
                if val is None:
                    continue
                if isinstance(val, (list, tuple)):
                    nxt.extend(list(val))
                else:
                    nxt.append(val)
            else:
                nxt.append(val)

        cur = nxt

    lines: list[str] = []
    for v in cur:
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            s = ', '.join(str(x).strip() for x in v if str(x).strip())
            if s.strip():
                lines.append(s.strip())
        else:
            s = str(v).strip()
            if s:
                lines.append(s)

    if len(lines) == 1 and '\n' in lines[0]:
        lines = [ln.strip() for ln in lines[0].splitlines() if ln.strip()]
        list_mode = True

    return (lines, list_mode)


def render_dse_header(b: TaskBind) -> str:
    name = b.dse_name
    nn = b.dse_nn
    if name and nn:
        return f'ДСЕ: {name} ({nn})'
    if name:
        return f'ДСЕ: {name}'
    return f'ДСЕ ID: {b.dse_id if b.dse_id is not None else "-"}'


def _render_oper_header(b: TaskBind, *, show_qty: bool) -> str:
    op_num = b.oper_num
    op_name = b.oper_name
    base = f'Операция: {op_num} {op_name}'.strip()
    if show_qty and (b.qty_text or '').strip():
        return f'{base} | Количество: {b.qty_text.strip()}'
    return base


def build_materials_context(*, dse: dict | None, op: dict | None, b: TaskBind, selected: list[str]) -> dict[str, Any]:
    mats = []
    if isinstance(op, dict):
        mm = op.get('Материалы')
        if isinstance(mm, (list, tuple)):
            mats = [m for m in mm if isinstance(m, dict)]

    qty_nar = F.valm(b.qty_text)
    dse_qty_route = None
    if isinstance(dse, dict):
        dse_qty_route = F.valm(dse.get('Количество'))

    rows: list[dict[str, Any]] = []
    for m in mats:
        row = dict(m)
        norm_unit = F.valm(m.get('Мат_норма_ед'))
        norm_route = F.valm(m.get('Мат_норма'))

        if norm_unit is None and norm_route is not None and dse_qty_route not in (None, 0):
            try:
                norm_unit = norm_route / float(dse_qty_route)
            except Exception:
                norm_unit = None

        norm_by_naryad = None
        if norm_unit is not None and qty_nar is not None:
            norm_by_naryad = norm_unit * qty_nar

        row['Мат_норма_по_наряду'] = norm_by_naryad
        rows.append(row)

    list_lines = []
    mat_aliases = [
        field_cred
        for field_cred in KEY_ALIASES
        if field_cred.section == 'Материалы' and f'{field_cred.section}.{field_cred.name}' in selected
    ]
    mat_fields = sorted(mat_aliases, key=lambda x: x.sort_rank)
    for r in rows:
        base = []
        for fld in mat_fields:
            value = r.get(fld.name, '')
            if value:
                base.append(str(value).strip())
        line = ' — '.join(base)

        if line:
            list_lines.append(line)

    return {'Список': '\n'.join(list_lines),}

def group_by_selected_fields(selection: list[str], options: TaskBuildOptions) -> list[str]:
    new_struct = []
    lst_sections = set()
    for field in selection:
        section, *_ = field.split('.')
        if section in options.group_by_sections:
            lst_sections.add(f'{section}.Список')
        else:
            new_struct.append(field)
    new_struct.extend(lst_sections)
    return new_struct


def build_task_text_from_route(
    *,
    bindings: list[TaskBind],
    route: list[dict] | None,
    selected_field_ids: Iterable[str] | None = None,
    options: TaskBuildOptions | None = None,
) -> str:
    """Собирает текст задания из связей наряда + маршрута."""
    options = options or TaskBuildOptions()

    ranks = {'ДСЕ': 1, 'Операция': 2, 'Материалы': 3, 'Наряд': 4}

    data = list(selected_field_ids) if selected_field_ids is not None else default_selected_field_ids()
    dse_by_id, op_by_dse_and_key = index_route(route or [])

    out_lines: list[str] = []
    last_dse_id: Optional[int] = None
    grouped_fields = group_by_selected_fields(data, options)
    grouped_fields = sorted(grouped_fields, key=lambda x: ranks.get(x.split('.')[0], 999))

    for b in bindings:
        dse = dse_by_id.get(b.dse_id) if b.dse_id is not None else None
        op = op_by_dse_and_key.get((b.dse_id, b.oper_key)) if b.dse_id is not None else None

        ctx = {
            'ДСЕ': dse or {},
            'Операция': op or {},
            'Материалы': build_materials_context(dse=dse, op=op, b=b, selected=data),
            'Наряд': _binding_context(b),
        }

        if options.group_by_dse:
            if b.dse_id != last_dse_id:
                last_dse_id = b.dse_id
                if options.show_dse_header:
                    if out_lines:
                        out_lines.append('')
                    out_lines.append(render_dse_header(b))

        previous_section = None
        nar_info_rendered = False
        for sel in grouped_fields:
            sel = (sel or '').strip()

            if not sel:
                continue
            split_row = sel.split('.')
            if len(split_row) != 2:
                continue
            section, field = split_row

            lines, is_list = eval_selector(sel, ctx)
            if not lines:
                continue

            rank = ranks.get(section, 0)
            lines, is_list = eval_selector(sel, ctx)

            prev_rank = ranks.get(previous_section, 1)

            if section == options.section_for_render_naryad_info and not nar_info_rendered:
                space = options.indent * prev_rank
                out_lines.append(
                    space + _render_oper_header(b, show_qty=options.show_qty_in_oper_header)
                )
                nar_info_rendered = True

            label = print_label_for_selector(sel)

            if is_list or len(lines) > 1:
                out_lines.append(options.indent * 2 + f'{label}:')
                if options.bullet_lists:
                    for i, ln in enumerate(lines, 1):
                        out_lines.append(options.indent * 3 + f'{i}. {ln}')
                else:
                    for ln in lines:
                        out_lines.append(options.indent * 3 + ln)
            else:
                out_lines.append(options.indent * rank + f'{label}: {lines[0]}')
            previous_section = section

    return '\n'.join(out_lines).strip() + ('\n' if out_lines else '')


def compose_task_for_print(
    nar_info: CLSS.Naryad_info,
    *,
    selected_field_ids: Iterable[str] | None = None,
    options: TaskBuildOptions | None = None,
    fallback_to_saved: bool = True,
) -> str:
    """Генерирует текст задания по номеру наряда."""
    options = options or TaskBuildOptions()

    nom_nar = nar_info.nom_nar

    naryad_instance = CMS.Naryads(db_naryad=CFG.Config.project.db_naryad, p_nom_or_row=int(nom_nar))

    mk = naryad_instance.Номер_мк

    bindings = parse_naryad_bindings(
        task_instance=naryad_instance
    )

    if not bindings:
        return nar_info.zadanie if fallback_to_saved else ''

    route = CMS.load_res(int(mk))

    text = build_task_text_from_route(
        bindings=bindings,
        route=route,
        selected_field_ids=selected_field_ids,
        options=options,
    )

    if text.strip():
        return text

    return nar_info.zadanie if fallback_to_saved else ''


def default_fields_config_path() -> str:
    base = tempfile.gettempdir()
    return os.path.join(base, 'print_task_fields.json')


def load_selected_fields(path: str) -> list[str] | None:
    try:
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data if str(x).strip()]
    except Exception:
        return None
    return None


def save_selected_fields(path: str, selectors: Iterable[str]) -> bool:
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(list(selectors), f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def default_selected_field_ids() -> list[str]:
    return [
        'ДСЕ.Наименование',
        'Операция.Опер_номер',
        'Операция.Опер_наименование',
        'Операция.Опер_оборудование_наименование',
        'Операция.Опер_Тшт',
    ]


def _iter_dict_schema(prefix: str, obj: Any, out: set[str], *, depth: int, max_depth: int) -> None:
    if obj is None or depth > max_depth:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k is None:
                continue
            k = str(k)
            path = out_path = f'{prefix}.{k}' if prefix else k
            if isinstance(v, (list, tuple)):
                out_path = path + '[]'
                if v and isinstance(v[0], dict) and depth < max_depth:
                    _iter_dict_schema(path + '[]', v[0], out, depth=depth + 1, max_depth=max_depth)
            elif isinstance(v, dict) and depth < max_depth:
                _iter_dict_schema(path, v, out, depth=depth + 1, max_depth=max_depth)
            out.add(out_path)




def discover_all_selectors(route: list[dict] | None, *, max_depth: int = 2, sample_limit: int = 50) -> list[str]:
    out: set[str] = set()

    out.update({
        'Наряд.ДСЕ_ID',
        'Наряд.ДСЕ',
        'Наряд.Операции',
        'Наряд.Опер_колво',
    })

    out.update({
        'Материалы.Список',
        'Материалы.Мат_код',
        'Материалы.Мат_наименование',
        'Материалы.Мат_ед_изм',
        'Материалы.Мат_норма',
        'Материалы.Мат_норма_ед',
        'Материалы.Мат_норма_по_наряду',
    })

    if not route:
        out.update({
            'ДСЕ.Наименование',
            'ДСЕ.Номенклатурный_номер',
            'Операция.Опер_номер',
            'Операция.Опер_наименование',
            'Операция.Опер_код',
            'Операция.Переходы[]',
        })
        return sorted(out)

    for dse in (route or [])[:sample_limit]:
        _iter_dict_schema('ДСЕ', dse, out, depth=0, max_depth=max_depth)

        ops = dse.get('Операции') or []
        if isinstance(ops, (list, tuple)) and ops:
            if isinstance(ops[0], dict):
                _iter_dict_schema('Операция', ops[0], out, depth=0, max_depth=max_depth)
                _iter_dict_schema('ДСЕ.Операции[]', ops[0], out, depth=0, max_depth=max_depth)

    return sorted(out)


def decor_settings_table(table: QtWidgets.QTableWidget):
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    table.verticalHeader().hide()
    column_select = CQT.num_col_by_name_c(table, '+')
    column_field = CQT.num_col_by_name_c(table, 'Поле')
    if column_select is None:
        return
    table.setColumnWidth(column_select, 16)

    for row in range(table.rowCount()):
        item = table.item(row, column_select)
        is_checked = item.text() == '+'
        CQT.add_check_box(table, row, column_select,
                          conn_func_checked_row_col=on_select_settings_field,
                          self_obj=table,
                          val=is_checked,
                          )
    table.hideColumn(column_field)

def on_select_settings_field(table: QtWidgets.QTableWidget, is_checked: bool, row: int, column: int):
    value = '+' if is_checked else ''
    item = table.item(row, column)
    if not item: return
    item.setText(value)


def select_fields_dialog(
    parent: Any,
    *,
    all_selectors: list[str],
    preselected: Iterable[str] | None = None,
) -> list[str] | None:

    validate_table_data = lambda data: [item['Поле'] for item in data if item['+'] == '+']
    table_data = []
    for field in all_selectors:
        credentials = field.split('.')
        if len(credentials) != 2:
            continue
        category, field_name = credentials

        if _is_key_excluded(field_name):
            continue
        selected_value = '+' if field in preselected else ''
        alias_name = _alias_for_key(field_name)
        table_data.append({'+': selected_value, 'Поле': field, 'Наименование': alias_name, 'Раздел': category})
    result = CQT.msgboxg_get_table(
        parent,
        'Выбор полей для печати',
        table_data,
        func_oform_tbl=decor_settings_table,
        func_validate=validate_table_data,
        btn0_name='Применить'
    )
    if not isinstance(result, list):
        return
    return result


def configure_print_task_fields(
    parent: Any,
    *,
    mk: int | str | None,
    config_path: str | None = None,
) -> list[str] | None:
    config_path = config_path or default_fields_config_path()
    current = load_selected_fields(config_path) or default_selected_field_ids()

    route = None
    try:
        if mk is not None and str(mk).strip() != '':
            route = CMS.load_res(int(mk))
    except Exception:
        route = None

    all_selectors = discover_all_selectors(route)
    picked = select_fields_dialog(parent, all_selectors=all_selectors, preselected=current)
    if picked is None:
        return None
    save_selected_fields(config_path, picked)
    return picked
