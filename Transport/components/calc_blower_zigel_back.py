import copy
import dataclasses
import math
import operator
import os
import re
import typing

import flet as ft

import project_cust_38.Cust_Functions as F
import project_cust_38.Cust_SQLite as CSQ
import project_cust_38.Cust_emoji as Cust_emoji
import project_cust_38.Cust_Excel as CEX

import Config.srv_config as SRVCFG
import components.common_funcs as CMF
from components.common_funcs import Table_data
import components.blower_zigel_materials as BZM
import data_class as DTCLS


CONSTANTS = {
    "g": 9.81,
    "R": 8.31446261815324,
    "M_air": 0.02898,  # кг/моль
}


GOST_D_LIST_M = [
    0.050,
    0.065,
    0.080,
    0.100,
    0.125,
    0.150,
    0.200,
    0.250,
    0.300,
    0.350,
    0.400,
]

@dataclasses.dataclass
class Validator:
    condition: typing.Union[operator.ge, operator.le, operator.gt, operator.lt, operator.eq, operator.ne]
    second_operand: typing.Any
    if_true_message: str = None
    if_false_message: str = None

    def validate(self, value: typing.Any):
        return self.if_true_message if self.condition(value, self.second_operand) else self.if_false_message



MATERIAL_OPTIONS = [""] + sorted(BZM.MATERIALS.keys())


MANUAL_DU_GROUP_NAME = "Выбор Ду (для ручного подбора)"
MANUAL_DU_TOGGLE_FIELD = "manual_du_enabled"

def generate_rezult_data_for_save(name: str, input_tbl: ft.DataTable, output_tbl: ft.DataTable) -> dict:
    list_dict_rez_input = CMF.datatable_to_dicts(input_tbl)
    list_dict_rez_output = CMF.datatable_to_dicts(output_tbl)
    return {'name': name, 'input': list_dict_rez_input, 'output': list_dict_rez_output}

def gost_next_geq(x: float) -> float:
    """Ближайший размер из ряда ГОСТ, который >= x."""
    try:
        x = float(x)
    except Exception:
        return GOST_D_LIST_M[0]
    for d in GOST_D_LIST_M:
        if d >= x:
            return d
    return GOST_D_LIST_M[-1]

DS_TOKEN_SPLIT_RE = re.compile(r"[xXхХ×*\u00D7]")


def parse_particle_size_mm(raw) -> tuple[float, str]:
    if raw is None:
        return 0.0, 'Ds не задан'

    if isinstance(raw, (int, float)):
        try:
            v = float(raw)
            return v, 'Ds задан числом'
        except Exception:
            return 0.0, 'Ds не удалось привести к числу'

    s = str(raw).strip()
    if s == '':
        return 0.0, 'Ds пустой'

    s_norm = s.replace(',', '.')

    try:
        v = float(s_norm)
        return v, 'Ds задан числом (строка)'
    except Exception:
        pass

    parts = [p.strip() for p in DS_TOKEN_SPLIT_RE.split(s_norm) if p.strip()]
    nums = []
    for p in parts:
        try:
            nums.append(float(p))
        except Exception:
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)", p)
            if m:
                nums.append(float(m.group(1)))

    if not nums:
        return 0.0, f'Ds не распознан: {s}'

    if len(nums) == 1:
        return nums[0], f'Ds из записи {s} → {nums[0]:.3g} мм'

    if len(nums) == 2:
        ds = (nums[0] * nums[1]) ** 0.5
        return ds, f'Ds экв.: sqrt({nums[0]:g}×{nums[1]:g}) = {ds:.3g} мм'

    prod = 1.0
    for n in nums:
        prod *= max(n, 0.0)
    ds = prod ** (1.0 / len(nums)) if prod > 0 else 0.0
    return ds, f'Ds экв.: геом.среднее({"×".join(str(n) for n in nums)}) = {ds:.3g} мм'


def apply_material_defaults(input_vals: dict, overwrite: bool = True) -> tuple[dict, str, bool]:
    """Подставить значения из справочника материалов."""
    if not isinstance(input_vals, dict):
        return input_vals, 'Нет входных данных', False

    raw_name = str(input_vals.get('material_name', '') or '').strip()
    if not raw_name:
        return input_vals, 'Материал не указан', False

    canon, rec = BZM.find_material(raw_name)
    if not rec:
        example = ', '.join(BZM.list_materials(limit=10))
        return input_vals, f'Материал не найден в справочнике. Пример: {example}', False

    out = dict(input_vals)
    out['material_name'] = canon

    def _set(k: str, v):
        if v is None:
            return
        if overwrite:
            out[k] = v
            return
        cur = out.get(k)
        if cur is None:
            out[k] = v
            return
        if isinstance(cur, (int, float)) and float(cur) == 0.0:
            out[k] = v
            return
        if isinstance(cur, str) and cur.strip() == '':
            out[k] = v
            return

    _set('ds_mm', rec.get('ds'))
    _set('qs_kg_m3', rec.get('qs_kg_m3'))
    _set('qss_kg_m3', rec.get('qss_kg_m3'))
    _set('u0_m_s', rec.get('u0_m_s'))
    _set('lambda_s_dl_over_d', rec.get('lambda_s_dl_over_d'))

    if rec.get('u0_range'):
        try:
            a, b = rec['u0_range']
            a = float(a); b = float(b)
            _set('u2_min_m_s', max(5.0, min(a, b)))
            _set('u2_max_m_s', min(60.0, max(a, b)))
        except Exception:
            pass


    note_parts = [f'Материал: {canon}']
    if rec.get('u0_range'):
        a, b = rec['u0_range']
        note_parts.append(f'u0 диапазон: {a:g}–{b:g} м/с')
    if rec.get('qss_range'):
        a, b = rec['qss_range']
        note_parts.append(f'qss диапазон: {a:g}–{b:g} кг/м³')
    note = '; '.join(note_parts)
    return out, note, True


def auto_pick_yellow_inputs(input_vals: dict, overwrite: bool = True) -> tuple[dict, str, bool]:
    """Автоматический подбор параметров (Ду1, Ду2, u2, Ду3)."""
    if not isinstance(input_vals, dict):
        return input_vals, "Нет входных данных", False

    base = dict(input_vals)

    u0 = _safe_float(base.get("u0_m_s"), 0.0)
    u0_note = ""
    if u0 <= 0:
        u0 = 20.0
        base["u0_m_s"] = u0
        u0_note = "u0 не задано/0 → принято 20 м/с"

    try:
        pblower = float(base.get("pblower_bar") or 0.0)
        gs = float(base.get("qs_kg_h") or 0.0)
    except Exception:
        pblower = 0.0
        gs = 0.0
    if pblower <= 0:
        return base, "Для автоподбора нужно задать давление воздуходувки Pвд > 0", False
    if gs <= 0:
        return base, "Для автоподбора нужно задать массовый расход материала Gs (кг/ч) > 0", False

    tmp = dict(base)
    tmp.setdefault("d1_sel_m", GOST_D_LIST_M[0])
    tmp.setdefault("d2_sel_m", GOST_D_LIST_M[0])
    tmp.setdefault("d3_sel_m", GOST_D_LIST_M[0])
    tmp.setdefault("u2_m_s", float(tmp.get("u0_m_s")))

    calc0, _, _ = calc_new_data(tmp)
    d_calc0 = float(calc0.get("d_calc_0_m") or 0.0)
    d1 = gost_next_geq(d_calc0) if d_calc0 > 0 else float(tmp.get("d1_sel_m") or GOST_D_LIST_M[0])

    tmp["d1_sel_m"] = d1
    tmp["d2_sel_m"] = d1
    tmp["d3_sel_m"] = max(d1, float(tmp.get("d3_sel_m") or d1))
    calc1, _, _ = calc_new_data(tmp)
    d_calc1 = float(calc1.get("d_calc_1_m") or 0.0)
    d2 = gost_next_geq(d_calc1) if d_calc1 > 0 else float(tmp.get("d2_sel_m") or d1)
    d2 = max(d2, d1)

    u2_min_in = _safe_float(base.get("u2_min_m_s"), 0.0)
    u2_max_in = _safe_float(base.get("u2_max_m_s"), 0.0)

    if u2_min_in > 0 and u2_max_in > u2_min_in:
        u2_min = u2_min_in
        u2_max = u2_max_in
    else:
        u2_min = max(5.0, 0.6 * u0)
        u2_max = min(60.0, 1.6 * u0)

    mat_name = str(base.get("material_name") or "").strip()
    if mat_name:
        canon, rec = BZM.find_material(mat_name)
        if rec and rec.get("u0_range") and not (u2_min_in > 0 and u2_max_in > u2_min_in):
            a, b = rec["u0_range"]
            try:
                a = float(a); b = float(b)
                u2_min = max(5.0, min(a, b) - 2.0)
                u2_max = min(60.0, max(a, b) + 2.0)
            except Exception:
                pass
    if u2_max <= u2_min:
        u2_max = u2_min + 5.0

    step_coarse = 0.5
    step2 = 0.1


    base["u2_min_m_s"] = u2_min
    base["u2_max_m_s"] = u2_max

    tol = 0.005

    def eval_u2(u2_val: float):
        t = dict(base)
        t["d1_sel_m"] = d1
        t["d2_sel_m"] = d2
        t["u2_m_s"] = float(u2_val)
        t["d3_sel_m"] = d2
        c, _, _ = calc_new_data(t)
        d_calc2 = float(c.get("d_calc_2_m") or 0.0)
        d3 = gost_next_geq(d_calc2) if d_calc2 > 0 else d2
        d3 = max(d3, d2)
        t["d3_sel_m"] = d3
        c2, _, _ = calc_new_data(t)
        dp = float(c2.get("dp_2_bar") or 0.0)
        margin = float(c2.get("margin_bar") or (pblower - dp))
        if 0 <= margin <= tol:
            rank = 0
            score = margin
        elif margin > tol:
            rank = 1
            score = margin
        else:
            rank = 2
            score = abs(margin)

        return (rank, score), margin, dp, d3, c2

    best = None
    u = u2_min
    while u <= u2_max + 1e-9:
        res = eval_u2(u)
        if best is None or res[0] < best[0]:
            best = res + (u,)
        u += step_coarse

    best_u = best[-1]
    u2_min2 = max(u2_min, best_u - 1.0)
    u2_max2 = min(u2_max, best_u + 1.0)
    u = u2_min2
    while u <= u2_max2 + 1e-9:
        res = eval_u2(u)
        if res[0] < best[0]:
            best = res + (u,)
        u += step2

    _, margin, dp, d3, _calc_final, u_best = best

    picked = dict(base)

    if overwrite or float(picked.get("d1_sel_m") or 0.0) <= 0:
        picked["d1_sel_m"] = d1
    if overwrite or float(picked.get("d2_sel_m") or 0.0) <= 0:
        picked["d2_sel_m"] = d2
    if overwrite or float(picked.get("u2_m_s") or 0.0) <= 0:
        picked["u2_m_s"] = float(u_best)
    if overwrite or float(picked.get("d3_sel_m") or 0.0) <= 0:
        picked["d3_sel_m"] = d3

    if margin < 0:
        note = f"Автоподбор выполнен, но условие Δp≤Pвд не достигнуто: Δp={dp:.3f} bar, Pвд={pblower:.3f} bar. Попробуйте увеличить Ду3 или уменьшить расход."
        ok = False
    else:
        note = (
            f"Автоподбор: Ду1={d1:.3f} м; Ду2={d2:.3f} м; u2={float(u_best):.1f} м/с; Ду3={d3:.3f} м; "
            f"Δp={dp:.3f} bar; запас={margin:.3f} bar; tol={tol:.3f} bar; "
            f"u2∈[{u2_min:.1f}; {u2_max:.1f}] шаги {step_coarse:g}/{step2:g}."
            + (f" ({u0_note})" if u0_note else "")
        )
        ok = True
    accuracy = {item['name']: item.get('accuracy') or 2 for item in INPUT_PARAMS}
    picked = {
        k: round(v, accuracy.get(k, 2)) if isinstance(v, float)  else v
        for k, v in picked.items()
    }

    return picked, note, ok


INPUT_PARAMS: list[dict] = [
    {
        "name": "material_name",
        "header": "Материал",
        "dimension": "",
        "default_val": "",
        "data_type": str,
        "accuracy": 0,
        "min_max_list": MATERIAL_OPTIONS,
        "group_name": "Исходные данные",
        "comment": "",
    },
        {
        "name": "ds_mm",
        "header": "Диаметр частиц Ds",
        "dimension": "мм",
        "default_val": 5,
        "data_type": str,
        "accuracy": 0,
        "min_max_list": None,
        "group_name": "Исходные данные",
        "comment": "Принимает число (мм) или строку форматом ‘100x50x4’ (мм). ",
    },
    {
        "name": "qs_kg_m3",
        "header": "Плотность вещества qs",
        "dimension": "кг/м³",
        "default_val": 1000.0,
        "data_type": float,
        "accuracy": 1,
        "min_max_list": (10.0, 10000.0),
        "group_name": "Исходные данные",
    },
    {
        "name": "qss_kg_m3",
        "header": "Плотность насыпная qss",
        "dimension": "кг/м³",
        "default_val": 550.0,
        "data_type": float,
        "accuracy": 1,
        "min_max_list": (1.0, 10000.0),
        "group_name": "Исходные данные",
    },
    {
        "name": "cw",
        "header": "Коэффицент сопротивления Cw",
        "dimension": "-",
        "default_val": 0.6,
        "data_type": float,
        "accuracy": 3,
        "min_max_list": (0.01, 50.0),
        "group_name": "Исходные данные",
    },
    {
        "name": "patm_bar",
        "header": "Атмосферное давление",
        "dimension": "bar",
        "default_val": 1.0,
        "data_type": float,
        "accuracy": 3,
        "min_max_list": (0.5, 2.0),
        "group_name": "Исходные данные",
    },
    {
        "name": "t_c",
        "header": "Температура системы",
        "dimension": "°C",
        "default_val": 30.0,
        "data_type": float,
        "accuracy": 1,
        "min_max_list": (-50.0, 200.0),
        "group_name": "Исходные данные",
    },
    {
        "name": "u0_m_s",
        "header": "Скорость воздуха (начальная) u0",
        "dimension": "м/с",
        "default_val": 23.0,
        "data_type": float,
        "accuracy": 2,
        "min_max_list": (1.0, 80.0),
        "group_name": "Исходные данные",
        "comment": "Начальная скорость по справочной таблице (примерный диапазон).",
    },
    {
        "name": "qs_kg_h",
        "header": "Производительность Qs",
        "dimension": "кг/ч",
        "default_val": 10000.0,
        "data_type": float,
        "accuracy": 1,
        "min_max_list": (1.0, 1e9),
        "group_name": "Исходные данные",
    },
    {
        "name": "lh_m",
        "header": "Горизонтальная длина трассы",
        "dimension": "м",
        "default_val": 215.0,
        "data_type": float,
        "accuracy": 1,
        "min_max_list": (0.0, 1e6),
        "group_name": "Исходные данные",
    },
    {
        "name": "h_m",
        "header": "Высота подъёма",
        "dimension": "м",
        "default_val": 12.0,
        "data_type": float,
        "accuracy": 1,
        "min_max_list": (0.0, 1e6),
        "group_name": "Исходные данные",
    },
    {
        "name": "lambda_s_dl_over_d",
        "header": "Коэфф. потери давления λs*∆l/d",
        "dimension": "-",
        "default_val": 0.04,
        "data_type": float,
        "accuracy": 4,
        "min_max_list": (0.0, 10.0),
        "group_name": "Исходные данные",
    },
    {
        "name": "pblower_bar",
        "header": "Давление воздуходувки",
        "dimension": "bar",
        "default_val": 0.47,
        "data_type": float,
        "accuracy": 3,
        "min_max_list": (0.0, 5.0),
        "group_name": "Исходные данные",
    },
    {
        "name": "lambda_l",
        "header": "Коэфф. сопротивления воздух/труба λL",
        "dimension": "-",
        "default_val": 0.02,
        "data_type": float,
        "accuracy": 4,
        "min_max_list": (0.0, 10.0),
        "group_name": "Исходные данные",
    },
    {
        "name": "n_elbows",
        "header": "Кол-во отводов",
        "dimension": "шт",
        "default_val": 4,
        "data_type": int,
        "accuracy": 0,
        "min_max_list": (0, 1000),
        "group_name": "Исходные данные",
    },

    {
        "name": "d1_sel_m", # H7
        "header": "Ду1 — принятый внутренний диаметр (ГОСТ)",
        "dimension": "м",
        "default_val": 0.125,
        "data_type": float,
        "accuracy": 3,
        "min_max_list": GOST_D_LIST_M,
        "group_name": MANUAL_DU_GROUP_NAME,
        "comment": "Выберите ближайший Ду (м) ≥ расчётного d.",
    },

    {
        "name": "d2_sel_m", #  H18
        "header": "Ду2 — принятый внутренний диаметр (ГОСТ)",
        "dimension": "м",
        "default_val": 0.125,
        "data_type": float,
        "accuracy": 3,
        "min_max_list": GOST_D_LIST_M,
        "group_name": MANUAL_DU_GROUP_NAME,
        "comment": "Выберите ближайший Ду (м) ≥ расчётного d.",
    },

    {
        "name": "u2_m_s", # H36
        "header": "u2 — рабочая скорость воздуха (Корректирующая скорость 2)",
        "dimension": "м/с",
        "default_val": 29.0,
        "data_type": float,
        "accuracy": 2,
        "min_max_list": (1.0, 80.0),
        "group_name": MANUAL_DU_GROUP_NAME,
        "comment": "Подбирается совместно с Ду3 так, чтобы Δp было чуть меньше Pвд.",
    },
    {
        "name": "d3_sel_m", # H29
        "header": "Ду3 — принятый внутренний диаметр (ГОСТ)",
        "dimension": "м",
        "default_val": 0.125,
        "data_type": float,
        "accuracy": 3,
        "min_max_list": GOST_D_LIST_M,
        "group_name": MANUAL_DU_GROUP_NAME,
        "comment": "Выберите ближайший Ду (м) ≥ расчётного d и совместно с u2 добейтесь Δp≈Pвд.",
    },
    {
        "name": "u2_min_m_s",
        "header": "Минимальный предел u2 для рабочей скорости воздуха",
        "dimension": "м/с",
        "default_val": 0.0,
        "data_type": float,
        "accuracy": 2,
        "min_max_list": (0.0, 200.0),
        "group_name": "Параметры автоподбора",
        "comment": "минимальное значение параметра u0 m/s",
    },
    {
        "name": "u2_max_m_s",
        "header": "Макисмальный предел u2 для рабочая скорость воздуха",
        "dimension": "м/с",
        "default_val": 0.0,
        "data_type": float,
        "accuracy": 2,
        "min_max_list": (0.0, 200.0),
        "group_name": "Параметры автоподбора",
        "comment": "максимальное значение параметра u0 m/s",
    },


]


GROUP_0 = "Шаг 1 — Расчётные данные предварительные"
GROUP_1 = "Шаг 2 — Итерация с корр. Скоростью"
GROUP_2 = "Шаг 3 — Итерация с корр. Скоростью 2, подбирать скорость и диаметр трубы до выполнения условия примерного равенства давления воздуходувки и потери давления на транспортировку"


GROUPS = {
    GROUP_0: True,
    GROUP_1: True,
    GROUP_2: True,
}


OUTPUT_PARAMS: dict[str, dict] = {
    "rho_air_kg_m3": {
        "view": True,
        "header": "Плотность воздуха ρ",
        "dimension": "кг/м³",
        "comment": "Идеальный газ",
        "accuracy": 5,
        "group_name": GROUP_0,
    },
    "porosity": {
        "view": True,
        "header": "Порозность",
        "dimension": "-",
        "comment": "1 - qss/qs",
        "accuracy": 5,
        "group_name": GROUP_0,
    },

    "material_name_out": {
        "view": True,
        "header": "Материал (по справочнику)",
        "dimension": "",
        "comment": "",
        "accuracy": 0,
        "group_name": GROUP_0,
    },
    "ds_input_str": {
        "view": True,
        "header": "Ds (ввод пользователя)",
        "dimension": "мм",
        "comment": "Число или формат AxBxC",
        "accuracy": 0,
        "group_name": GROUP_0,
    },
    "ds_equiv_mm": {
        "view": True,
        "header": "Ds эквивалентный (использовано в расчёте)",
        "dimension": "мм",
        "comment": "Парсинг AxBxC → эквивалентный Ds",
        "accuracy": 3,
        "group_name": GROUP_0,
    },
    "ds_equiv_note": {
        "view": True,
        "header": "Как получен Ds эквивалентный",
        "dimension": "",
        "comment": "Эвристика эквивалентирования",
        "accuracy": 0,
        "group_name": GROUP_0,
    },

    "ws_m_s": {
        "view": True,
        "header": "Скорость витания частицы",
        "dimension": "м/с",
        "comment": "",
        "accuracy": 5,
        "group_name": GROUP_0,
    },
    "c_m_s": {
        "view": True,
        "header": "Скорость частиц верт. участка c",
        "dimension": "м/с",
        "comment": "",
        "accuracy": 5,
        "group_name": GROUP_0,
    },
    "fr": {
        "view": True,
        "header": "Число Фруда Fr",
        "dimension": "-",
        "comment": "",
        "accuracy": 5,
        "group_name": GROUP_0,
    },
    "ks_0": {
        "view": True,
        "header": "Коэффициент Ks",
        "dimension": "-",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_0,
    },
    "d_calc_0_m": {
        "view": True,
        "header": "Диаметр расчётный d",
        "dimension": "м",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_0,
    },
    "d_sel_0_m": {
        "view": True,
        "header": "Принято по ГОСТ (Ду)",
        "dimension": "м",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_0,
    },
    "mu_0": {
        "view": True,
        "header": "Концентрация эффективная µ",
        "dimension": "-",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_0,
    },
    "k_start": {
        "view": True,
        "header": "Коэфф. уменьшения скорости воздуха в начале трубы",
        "dimension": "-",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_0,
    },
    "u_start_0_m_s": {
        "view": True,
        "header": "Скорость воздуха в начале трансп. трубы",
        "dimension": "м/с",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_0,
    },
    "kl_0": {
        "view": True,
        "header": "Коэффициент KL",
        "dimension": "-",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_0,
    },
    "k_0": {
        "view": True,
        "header": "Коэффициент K",
        "dimension": "-",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_0,
    },
    "dp_0_pa": {
        "view": True,
        "header": "Потери давления на транспортировку",
        "dimension": "Па",
        "comment": "",
        "accuracy": 3,
        "group_name": GROUP_0,
    },
    "dp_0_bar": {
        "view": True,
        "header": "Потери давления на транспортировку",
        "dimension": "bar",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_0,
    },
    "u_corr_1_m_s": {
        "view": True,
        "header": "Скорость воздуха корректир.",
        "dimension": "м/с",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_0,
    },

    "ks_1": {
        "view": True,
        "header": "Коэффициент Ks",
        "dimension": "-",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_1,
    },
    "d_calc_1_m": {
        "view": True,
        "header": "Диаметр расчётный d",
        "dimension": "м",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_1,
    },
    "d_sel_1_m": {
        "view": True,
        "header": "Принято по ГОСТ (Ду)",
        "dimension": "м",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_1,
    },
    "mu_1": {
        "view": True,
        "header": "Концентрация эффективная µ",
        "dimension": "-",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_1,
    },
    "u_start_1_m_s": {
        "view": True,
        "header": "Скорость воздуха в начале трансп. трубы",
        "dimension": "м/с",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_1,
    },
    "kl_1": {
        "view": True,
        "header": "Коэффициент KL",
        "dimension": "-",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_1,
    },
    "k_1": {
        "view": True,
        "header": "Коэффициент K",
        "dimension": "-",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_1,
    },
    "dp_1_pa": {
        "view": True,
        "header": "Потери давления на транспортировку",
        "dimension": "Па",
        "comment": "",
        "accuracy": 3,
        "group_name": GROUP_1,
    },
    "dp_1_bar": {
        "view": True,
        "header": "Потери давления на транспортировку",
        "dimension": "bar",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_1,
    },

    "u2_m_s_out": {
        "view": True,
        "header": "Корректирующая скорость 2",
        "dimension": "м/с",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_2,
    },
    "ks_2": {
        "view": True,
        "header": "Коэффициент Ks",
        "dimension": "-",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_2,
    },
    "d_calc_2_m": {
        "view": True,
        "header": "Диаметр расчётный d",
        "dimension": "м",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_2,
    },
    "d_sel_2_m": {
        "view": True,
        "header": "Принято по ГОСТ (Ду)",
        "dimension": "м",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_2,
    },
    "mu_2": {
        "view": True,
        "header": "Концентрация эффективная µ",
        "dimension": "-",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_2,
    },
    "u_start_2_m_s": {
        "view": True,
        "header": "Скорость воздуха в начале трансп. трубы",
        "dimension": "м/с",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_2,
    },
    "kl_2": {
        "view": True,
        "header": "Коэффициент KL",
        "dimension": "-",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_2,
    },
    "k_2": {
        "view": True,
        "header": "Коэффициент K",
        "dimension": "-",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_2,
    },
    "dp_2_pa": {
        "view": True,
        "header": "Потери давления на транспортировку",
        "dimension": "Па",
        "comment": "",
        "accuracy": 3,
        "group_name": GROUP_2,
    },
    "dp_2_bar": {
        "view": True,
        "header": "Потери давления на транспортировку",
        "dimension": "bar",
        "comment": "",
        "accuracy": 6,
        "group_name": GROUP_2,
    },
    "air_volume_m3_min": {
        "view": True,
        "header": "Объём воздуха V",
        "dimension": "м³/мин",
        "comment": "",
        "accuracy": 4,
        "group_name": GROUP_2,
    },
    "margin_bar": {
        "view": True,
        "header": "Запас по давлению (Pblower - Δp)",
        "dimension": "bar",
        "comment": "Разница Давление воздуходувки и Потери давления на пневматическую транспортировку",
        "accuracy": 6,
        "group_name": GROUP_2,
        "validators": [
            Validator(
                condition=operator.lt,
                second_operand=0,
                if_true_message=f"{Cust_emoji.СтатусыПроизводства.error} Запас по давлению (Pblower - Δp) ниже нуля транспортировка невозможна!"
            )
        ]
    },
    "log": {
        "view": False,
        "header": "Лог расчета",
        "dimension": "",
        "comment": "",
        "accuracy": 0,
        "group_name": GROUP_2,
    },
}


class Cust_module_params:
    def __init__(self):
        self.ver_tbls_data = 1
        self.input_tbl_editbl: Table_data | None = None
        self.input_tbl_not_editbl: Table_data | None = None
        self.output_tbl: Table_data | None = None
        self.filtr_seach_history: str = ""
        self.manual_du_enabled: bool = False


TBL_INPUT = Table_data()
TBL_INPUT.append_column_desc(name="name", header="Имя", hidden=True, editable=False, unique=True)
TBL_INPUT.append_column_desc(name="header", header="Параметр", hidden=False, editable=False, width=300)
TBL_INPUT.append_column_desc(name="dimension", header="Ед.изм", hidden=False, editable=False, width=80)
TBL_INPUT.append_column_desc(name="val", header="Значение", hidden=False, editable=True, width=180)
TBL_INPUT.append_column_desc(name=MANUAL_DU_TOGGLE_FIELD, header="Ручн.", hidden=False, editable=False, width=70)

TBL_OUTPUT_ERR = Table_data()
TBL_OUTPUT_ERR.append_column_desc(name="name", header="№", hidden=False, editable=False, width=50, unique=True)
TBL_OUTPUT_ERR.append_column_desc(name="header", header="Параметр", hidden=False, editable=False, width=300)
TBL_OUTPUT_ERR.append_column_desc(name="val", header="Значение", hidden=False, editable=False, width=130)
TBL_OUTPUT_ERR.append_column_desc(name="err", header="Ошибка", hidden=False, editable=False, width=300)

TBL_OUTPUT = Table_data()
TBL_OUTPUT.append_column_desc(name="name", header="Имя", hidden=True, editable=False, unique=True)
TBL_OUTPUT.append_column_desc(name="header", header="Параметр", hidden=False, editable=False, width=300)
TBL_OUTPUT.append_column_desc(name="val", header="Значение", hidden=False, editable=False, width=130)
TBL_OUTPUT.append_column_desc(name="dimension", header="Ед.изм", hidden=False, editable=False, width=100)
TBL_OUTPUT.append_column_desc(name="comment", header="Примечание", hidden=False, editable=False, width=500)

TBL_HISTORY = Table_data()
TBL_HISTORY.append_column_desc(name="s_num", header="Номер", hidden=True, editable=False, unique=True)
TBL_HISTORY.append_column_desc(name="date", header="Дата", hidden=False, editable=False, width=300)
TBL_HISTORY.append_column_desc(name="name", header="Название", hidden=False, editable=False, width=500)


def is_empty(val) -> bool:
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    if isinstance(val, float):
        try:
            if math.isnan(val) or math.isinf(val):
                return True
        except Exception:
            pass
    return False


def calc_new_tbl_input() -> Table_data:
    new_tbl_input_copy = copy.deepcopy(TBL_INPUT)
    new_tbl_input_copy.add_table_name(F.get_time_shtamp_c(), "Ввод параметров:")
    prev_gr = ""
    for item in INPUT_PARAMS:
        name = item["name"]
        header = item["header"]
        dimension = item.get("dimension", "")

        data_type = item.get("data_type", None)
        default_val = item.get("default_val", 0)
        val = copy.deepcopy(default_val)
        min_max_list = item.get("min_max_list", None)
        comment = item.get("comment", None)
        accuracy = item.get("accuracy", 5)
        group_name = item.get("group_name", "")
        if group_name and prev_gr != group_name:
            prev_gr = group_name
            new_tbl_input_copy.add_group(name, prev_gr)

        row = CMF.Row_data()
        row.group_name = group_name
        row.append(name, CMF.Cell_description())
        row.append(header, CMF.Cell_description())
        row.append(dimension, CMF.Cell_description())
        row.append(
            val,
            CMF.Cell_description(
                min_max_list,
                comment=comment,
                data_type=data_type,
                accuracy=accuracy,
                default_val=default_val,
            ),
        )
        row.append("", CMF.Cell_description(data_type=str, accuracy=0))
        new_tbl_input_copy.add_row(row)
    return new_tbl_input_copy


new_tbl_input = calc_new_tbl_input()


def generate_input_data(
    fnc_onchange,
    ref,
    default_vals: dict | None = None,
    *,
    group_header_controls: dict | None = None,
) -> (ft.DataTable, Table_data):
    if default_vals:
        new_tbl_input.set_vals_into_field(default_vals, "val")
    table_view = CMF.Table_view(
        new_tbl_input,
        ref=ref,
        fnc_onchange=fnc_onchange,
        group_header_controls=group_header_controls,
    )
    return table_view, new_tbl_input


def prepare_calc_new_data(data: list[dict], Data: DTCLS.Data_page) -> tuple[dict | None, list[dict], bool]:
    if not Data.Data_module.cust_data.input_tbl_editbl.sync_ui_to_data("val"):
        return None, [], False
    data_params = Data.Data_module.cust_data.input_tbl_editbl.to_dict_by_unique()
    calculated, errors, success = calc_new_data({k: v["val"] for k, v in data_params.items()})
    return calculated, errors, success


def set_manual_du_inputs_enabled(tbl_data: Table_data | None, enabled: bool) -> None:
    """Включить/выключить блок ввода группы MANUAL_DU_GROUP_NAME.

    enabled=True  -> поля доступны (ручной подбор)
    enabled=False -> поля заблокированы (автоподбор)
    """
    if tbl_data is None:
        return
    disabled = not bool(enabled)
    for row in getattr(tbl_data, "rows", []):
        if getattr(row, "merge", False) or getattr(row, "table_header", False):
            continue
        if getattr(row, "group_name", None) != MANUAL_DU_GROUP_NAME:
            continue
        try:
            row.set_cell_disabled("val", disabled)
            if disabled:
                row.set_cell_text_color("val", ft.Colors.SECONDARY)
            else:
                row.set_cell_text_color("val", ft.Colors.ON_SURFACE)
        except Exception:
            pass


def _safe_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def calc_new_data(input_data: dict) -> tuple[dict, list[dict], bool]:
    """Чистый расчёт без Excel. Формулы соответствуют листу «Зигель без изм.диаметра трубы»."""
    errs: list[dict] = []
    out: dict = {}

    material_name = str(input_data.get("material_name", "") or "").strip()
    ds_raw = input_data.get("ds_mm", 0.0)
    ds_mm, ds_note = parse_particle_size_mm(ds_raw)
    qs = _safe_float(input_data.get("qs_kg_m3", 0.0))
    qss = _safe_float(input_data.get("qss_kg_m3", 0.0))
    cw = _safe_float(input_data.get("cw", 0.0))
    patm_bar = _safe_float(input_data.get("patm_bar", 1.0))
    t_c = _safe_float(input_data.get("t_c", 20.0))
    u0 = _safe_float(input_data.get("u0_m_s", 0.0))
    qs_kg_h = _safe_float(input_data.get("qs_kg_h", 0.0))
    lh = _safe_float(input_data.get("lh_m", 0.0))
    h = _safe_float(input_data.get("h_m", 0.0))
    lambda_s_dl_over_d = _safe_float(input_data.get("lambda_s_dl_over_d", 0.0))
    pblower_bar = _safe_float(input_data.get("pblower_bar", 0.0))
    lambda_l = _safe_float(input_data.get("lambda_l", 0.0))
    n_elbows = int(_safe_float(input_data.get("n_elbows", 0), 0))

    d1_sel = _safe_float(input_data.get("d1_sel_m", 0.0))
    d2_sel = _safe_float(input_data.get("d2_sel_m", 0.0))
    u2 = _safe_float(input_data.get("u2_m_s", 0.0))
    d3_sel = _safe_float(input_data.get("d3_sel_m", 0.0))
    tol_bar = 0.005

    d1_eff, d2_eff, d3_eff = d1_sel, d2_sel, d3_sel


    def err(header: str, val, exc: str):
        errs.append({"header": header, "val": val, "Exception": exc})

    if cw <= 0:
        err("Коэффициент сопротивления Cw", cw, "Cw должно быть > 0")
    if u0 <= 0:
        err("Скорость u0", u0, "u0 должно быть > 0")
    if patm_bar <= 0:
        err("Атмосферное давление", patm_bar, "Patm должно быть > 0")
    if pblower_bar <= 0:
        err("Давление воздуходувки", pblower_bar, "Pblower должно быть > 0")
    if qs <= 0:
        err("Плотность вещества qs", qs, "qs должно быть > 0")
    if qs_kg_h <= 0:
        err("Массовый расход материала Gs (Qs)", qs_kg_h, "Qs должно быть > 0")
    if ds_mm <= 0:
        err("Размер частиц Ds", ds_raw, "Ds должно быть > 0 (мм или AxBxC)")

    g = CONSTANTS["g"]
    R = CONSTANTS["R"]
    M_air = CONSTANTS["M_air"]

    rho_air = (M_air * (patm_bar * 100000.0)) / (R * (t_c + 273.0))
    out["rho_air_kg_m3"] = rho_air

    porosity = 1.0 - (qss / qs) if qs else 0.0
    out["porosity"] = porosity

    out["material_name_out"] = material_name
    out["ds_input_str"] = str(ds_raw)
    out["ds_equiv_mm"] = ds_mm
    out["ds_equiv_note"] = ds_note

    m_dot = qs_kg_h / 3600.0

    ws = math.sqrt((4.0 / 3.0) * (g * (ds_mm / 1000.0) * qs) / (cw * rho_air)) if cw and rho_air else 0.0 # H3
    out["ws_m_s"] = ws # H4
    c = u0 - ws
    out["c_m_s"] = c # C17 = c/v
    c_over_v = (c / u0) if u0 else 0.0

    ks0 = (lambda_s_dl_over_d * lh) + ((2.0 * h * g) / (c_over_v * (u0**2))) + 2.0 * c_over_v * (1.0 + n_elbows / 2.0) if (c_over_v and u0) else 0.0# H6
    out["ks_0"] = ks0

    d_calc0 = math.sqrt((2.0 * ks0 * m_dot * u0) / (math.pi * pblower_bar * 100000.0)) if pblower_bar else 0.0 # H7 (расчётный d)
    out["d_calc_0_m"] = d_calc0

    fr = u0 / math.sqrt(d_calc0 * g) if d_calc0 > 0 else 0.0 # Fr (H5)
    out["fr"] = fr

    out["d_sel_0_m"] = d1_sel
    out["d_used_0_m"] = d1_eff

    mu0 = (4.0 * m_dot) / (math.pi * (d1_eff**2) * u0 * rho_air) if (d1_eff and u0 and rho_air) else 0.0 # H8
    out["mu_0"] = mu0

    k_start = math.sqrt(1.0 + pblower_bar) # H9
    out["k_start"] = k_start

    out["u_start_0_m_s"] = (u0 / k_start) if k_start else 0.0 # H10

    kl0 = (lambda_l * (lh / d1_eff)) if d1_eff else 0.0 # H11
    out["kl_0"] = kl0

    k0 = kl0 + mu0 * ks0 # H12
    out["k_0"] = k0

    patm_pa = patm_bar * 100000.0 # H13, H14
    dp0_pa = patm_pa * (math.sqrt(1.0 + (k0 * (rho_air * u0 * u0) / patm_pa)) - 1.0) if patm_pa else 0.0
    out["dp_0_pa"] = dp0_pa
    out["dp_0_bar"] = dp0_pa / 100000.0

    dp0_bar = out["dp_0_bar"]
    u_corr1 = u0 * math.sqrt(1.0 + (dp0_bar / patm_bar)) if patm_bar else 0.0 # H15
    out["u_corr_1_m_s"] = u_corr1

    #==== Итерация с корр. Скоростью G16
    ks1 = (lambda_s_dl_over_d * lh) + ((2.0 * h * g) / (c_over_v * (u_corr1**2))) + 2.0 * c_over_v * (1.0 + n_elbows / 2.0) if (c_over_v and u_corr1) else 0.0
    out["ks_1"] = ks1

    d_calc1 = math.sqrt((2.0 * ks0 * m_dot * u_corr1) / (math.pi * pblower_bar * 100000.0)) if pblower_bar else 0.0 # H18
    out["d_calc_1_m"] = d_calc1
    out["d_sel_1_m"] = d2_sel
    out["d_used_1_m"] = d2_eff

    mu1 = (4.0 * m_dot) / (math.pi * (d2_eff**2) * u_corr1 * rho_air) if (d2_eff and u_corr1 and rho_air) else 0.0
    out["mu_1"] = mu1
    out["u_start_1_m_s"] = (u_corr1 / k_start) if k_start else 0.0
    kl1 = (lambda_l * (lh / d2_eff)) if d2_eff else 0.0
    out["kl_1"] = kl1
    k1 = kl1 + mu1 * ks1
    out["k_1"] = k1

    dp1_pa = patm_pa * (math.sqrt(1.0 + (k1 * (rho_air * u_corr1 * u_corr1) / patm_pa)) - 1.0) if patm_pa else 0.0
    out["dp_1_pa"] = dp1_pa
    out["dp_1_bar"] = dp1_pa / 100000.0

    #G27
    # == Итерация с корр. Скоростью 2, подбирать скорость и диаметр трубы до выполнения условия примерного равенства давления воздуходувки и потери давления на транспортировку
    out["u2_m_s_out"] = u2 # H28
    out["ks_2"] = ks1
    d_calc2 = math.sqrt((2.0 * ks1 * m_dot * u2) / (math.pi * pblower_bar * 100000.0)) if pblower_bar else 0.0
    out["d_calc_2_m"] = d_calc2
    out["d_sel_2_m"] = d3_sel
    out["d_used_2_m"] = d3_eff

    mu2 = (4.0 * m_dot) / (math.pi * (d3_eff**2) * u2 * rho_air) if (d3_eff and u2 and rho_air) else 0.0
    out["mu_2"] = mu2
    out["u_start_2_m_s"] = (u2 / k_start) if k_start else 0.0
    kl2 = (lambda_l * (lh / d3_eff)) if d3_eff else 0.0
    out["kl_2"] = kl2
    k2 = kl2 + mu2 * ks1
    out["k_2"] = k2

    dp2_pa = patm_pa * (math.sqrt(1.0 + (k2 * (rho_air * u2 * u2) / patm_pa)) - 1.0) if patm_pa else 0.0
    out["dp_2_pa"] = dp2_pa
    dp2_bar = dp2_pa / 100000.0
    out["dp_2_bar"] = dp2_bar

    out["air_volume_m3_min"] = (math.pi / 4.0) * (d3_eff**2) * u2 * 60.0

    margin = pblower_bar - dp2_bar
    out["margin_bar"] = margin

    rec_parts: list[str] = []
    d1_rec = gost_next_geq(d_calc0)
    d2_rec = gost_next_geq(d_calc1)
    d3_rec = gost_next_geq(d_calc2)
    if d1_eff + 1e-12 < d_calc0:
        rec_parts.append(f"Ду (ит.0, J7) увеличить до ≥ {d1_rec:.3f} м")
    if d2_eff + 1e-12 < d_calc1:
        rec_parts.append(f"Ду (ит.1, J18) увеличить до ≥ {d2_rec:.3f} м")
    if d3_eff + 1e-12 < d_calc2:
        rec_parts.append(f"Ду (ит.2, J29) увеличить до ≥ {d3_rec:.3f} м")

    if dp2_bar > pblower_bar:
        rec_parts.append(
            f"Δp={dp2_bar:.3f} bar > Pblower={pblower_bar:.3f} bar: увеличьте Ду (ит.2, J29) (вверх по ряду) "
            f"или уменьшите скорость H26"
        )
    else:
        if margin > tol_bar:
            rec_parts.append(
                f"Есть запас {margin:.3f} bar. Для приближения к Pblower можно увеличить H26 (скорость) "
                f"или уменьшить Ду (но не ниже расчётного)."
            )
        else:
            rec_parts.append(f"Условие выполнено: Δp≈Pblower в допуске {tol_bar:.3f} bar")



    out["log"] = "; ".join(rec_parts)

    if errs:
        return out, errs, False
    return out, [], True

def validate_output_result(calculated: dict[str, typing.Any]) -> list[str]:
    messages = []
    for param, value in calculated.items():
        if param not in OUTPUT_PARAMS or not isinstance(OUTPUT_PARAMS[param], dict):
            continue
        validators = OUTPUT_PARAMS[param].get('validators', [])
        for validator in validators:
            if message := validator.validate(value):
                messages.append(message)
    return messages

def generate_rez_tbl(e: ft.ControlEvent, tbl: ft.DataTable, ref_out, fnc_cell_click=None) -> bool | None:
    """Генерация таблицы результатов."""

    def _has_any_data_rows(tbl_data: CMF.Table_data) -> bool:
        if tbl_data is None:
            return False
        for row in getattr(tbl_data, "rows", []):
            if not getattr(row, "merge", False) and not getattr(row, "table_header", False):
                return True
        return False

    Data: DTCLS.Data_page = e.page.data
    data = CMF.datatable_to_dicts(tbl)
    DTCLS.Data_page.Data_module.cust_data.output_tbl = None

    calculated, errors, success = prepare_calc_new_data(data, Data)
    if calculated is None:
        return

    tbl_output = make_res_tbl(calculated, ref_out, fnc_cell_click)
    warning_symbol = Cust_emoji.СтатусыПроизводства.warning.symbol
    success_symbol = Cust_emoji.СтатусыПроизводства.success.symbol

    if errors and not _has_any_data_rows(tbl_output):
        tbl_output = make_err_tbl(errors, ref_out)
        DTCLS.Data_page.Data_module.cust_data.output_tbl = tbl_output
        Data.Data_module.status_bar.set_text(f"{warning_symbol} Ошибка расчёта: рассчитанных параметров нет")
        return False


    DTCLS.Data_page.Data_module.cust_data.output_tbl = tbl_output
    try:
        mat = str(
            Data.Data_module.cust_data.input_tbl_editbl
                .to_dict_by_unique()
                .get("material_name", {})
                .get("val", "") or ""
        ).strip()
    except Exception:
        mat = ""


    suffix = ""
    if not mat:
        suffix = f"{Cust_emoji.СтатусыПроизводства.info} материал не выбран — использованы ручные параметры материала"
    if errors:
        headers = "\n ".join(f"{msg.get('header')}" for msg in errors if msg.get("header"))
        Data.Data_module.status_bar.set_text(
            f"{warning_symbol} Произошли ошибки при расчете {len(errors)} параметров ({headers})"
        )
    elif validate_messages := validate_output_result(calculated):
        if suffix:
            validate_messages.append(suffix)
        Data.Data_module.status_bar.set_text('\n'.join(validate_messages))
    else:
        Data.Data_module.status_bar.set_text(f"{success_symbol} Успешно рассчитано\n{suffix}")
    return True


def make_res_tbl(data: dict, ref_out=None, fnc_cell_click=None) -> CMF.Table_data:
    new_tbl_output: Table_data = copy.deepcopy(TBL_OUTPUT)
    new_tbl_output.add_table_name(F.get_time_shtamp_c(), "Расчетные данные:")

    list_groups = [group for group, is_view in GROUPS.items() if is_view]

    for group in list_groups:
        group_items: list[tuple[str, object]] = []
        for name, val in data.items():
            if name not in OUTPUT_PARAMS:
                continue
            if not OUTPUT_PARAMS[name].get("view", True):
                continue
            current_group = OUTPUT_PARAMS[name].get("group_name", "")
            if current_group != group:
                continue
            if is_empty(val):
                continue
            group_items.append((name, val))

        if not group_items:
            continue

        new_tbl_output.add_group(F.get_time_shtamp_c(), group)

        for key, meta in OUTPUT_PARAMS.items():
            if meta.get("group_name") != group:
                continue
            if not meta.get("view", True):
                continue
            if key not in data:
                continue
            val = data[key]
            if is_empty(val):
                continue

            row = CMF.Row_data()
            row.group_name = group
            row.append(key, CMF.Cell_description())
            row.append(meta.get("header", key), CMF.Cell_description())
            if F.is_numeric(val):
                row.append(val, CMF.Cell_description(accuracy=meta.get("accuracy", 5), data_type=float))
            else:
                row.append(val, CMF.Cell_description(data_type=str))
            row.append(meta.get("dimension", ""), CMF.Cell_description())
            row.append(meta.get("comment", "") or "", CMF.Cell_description())
            new_tbl_output.add_row(row)

    CMF.Table_view(
        new_tbl_output,
        ref=ref_out,
        fnc_on_click=fnc_cell_click,
        lazy_groups=True,
        single_group_expand=False,
    )
    return new_tbl_output


def make_err_tbl(data, ref_out=None) -> CMF.Table_data:
    new_tbl_output_err = copy.deepcopy(TBL_OUTPUT_ERR)
    for i, item in enumerate(data):
        row = CMF.Row_data()
        row.append(str(i + 1), CMF.Cell_description())
        row.append(item["header"], CMF.Cell_description())
        row.append(item.get("val", ""), CMF.Cell_description())
        row.append(item.get("Exception", ""), CMF.Cell_description())
        new_tbl_output_err.add_row(row)

    CMF.Table_view(new_tbl_output_err, ref=ref_out)
    return new_tbl_output_err


def make_history_tbl_data(Data: DTCLS.Data_page):
    tbl = copy.deepcopy(TBL_HISTORY)
    filter_value = str(getattr(Data.Data_module.cust_data, "filtr_seach_history", "") or "").strip()
    where = "" if filter_value == "" else f'and name like "%{filter_value}%"'
    try:
        list_calcs = CSQ.custom_request_c(
            Data.Data_user.db_flet,
            f"""SELECT * FROM blower_zigel_history WHERE ip = '{Data.Data_user.ip}' {where} ORDER BY s_num DESC LIMIT 20;""",
            rez_dict=True,
        )
    except Exception:
        list_calcs = []

    for calc in list_calcs:
        row = CMF.Row_data()
        row.append(calc.get("s_num"), CMF.Cell_description())
        row.append(calc.get("date"), CMF.Cell_description())
        row.append(calc.get("name"), CMF.Cell_description())
        tbl.add_row(row)
    return tbl


def save_in_db(e: ft.ControlEvent, name: str):
    Data: DTCLS.Data_page = e.page.data
    module_data: Cust_module_params = Data.Data_module.cust_data

    input_tbl = _clone_table_for_history(getattr(module_data, "input_tbl_editbl", None))
    output_tbl = _clone_table_for_history(getattr(module_data, "output_tbl", None))
    if input_tbl is None or output_tbl is None:
        return False

    data_save = {
        "ver": module_data.ver_tbls_data,
        "input_tbl": input_tbl,
        "output_tbl": output_tbl,
    }
    row = [F.now(), name, Data.Data_user.ip or "", F.to_binary_pickle(data_save)]
    try:
        return CSQ.custom_request_c(
            Data.Data_user.db_flet,
            """INSERT INTO blower_zigel_history (date, name, ip, data) VALUES ({})""".format(
                CSQ.questions_for_mask(row)
            ),
            list_of_lists_c=[row],
        )
    except Exception:
        return False



def _clone_table_for_history(table_data: CMF.Table_data | None) -> CMF.Table_data | None:
    if table_data is None:
        return None

    cloned = CMF.Table_data()
    for field in table_data.list_fields:
        cloned.append_column_desc(
            name=field.name,
            header=field.header,
            hidden=field.hidden,
            editable=field.editable,
            width=field.width,
            unique=field.unique,
        )

    cloned.name = table_data.name

    for src_row in table_data.rows:
        row = CMF.Row_data(merge=getattr(src_row, "merge", False))
        row.group_name = getattr(src_row, "group_name", None)
        row.table_header = getattr(src_row, "table_header", False)

        for src_cell in src_row.cells:
            desc = CMF.Cell_description(
                min_max_list=copy.deepcopy(src_cell.description.min_max_list),
                accuracy=src_cell.description.accuracy,
                comment=copy.deepcopy(src_cell.description.comment),
                data_type=src_cell.description.data_type,
                default_val=copy.deepcopy(src_cell.description.default_val),
            )
            row.append(copy.deepcopy(src_cell.val), desc)

        cloned.add_row(row)
        cloned.rows[-1].group_name = getattr(src_row, "group_name", None)
        cloned.rows[-1].table_header = getattr(src_row, "table_header", False)

    return cloned


def clean_unicode(string):
    if not isinstance(string, str): return ''
    return ''.join(symbol for symbol in string if not (0x2790 <= ord(symbol) <= 0x27BF))

def save_word(list_dict_rez_input: list, list_dict_rez_output: list, name: str, dir_save: str, name_module: str) -> str | bool:
    list_dict_rez_input = [{clean_unicode(k): clean_unicode(v) for k, v in _.items() if k != 'Имя'} for _ in list_dict_rez_input]
    list_dict_rez_output = [{clean_unicode(k): clean_unicode(v) for k, v in _.items() if k != 'Имя'} for _ in list_dict_rez_output]
    name_file = f'{name}.docx'
    template_path = os.path.join(SRVCFG.DOCX_TEMPLATES_PATH, 'report.docx')
    path = os.path.join(dir_save, name_file)
    rez = CEX.make_docx_report(name_module, list_dict_rez_input, list_dict_rez_output, output_docx_path=path,
                           template_name=template_path)
    if not rez:
        return False
    return rez

def load_from_db_history_calc(Data: DTCLS.Data_page, s_num: int) -> (CMF.Table_data, CMF.Table_data):
    data = CSQ.custom_request_c(
        Data.Data_user.db_flet,
        f"""SELECT data FROM blower_zigel_history WHERE s_num == {int(s_num)}""",
        one=True,
        one_column=True,
        hat_c=False,
    )
    if not data:
        return False
    data_obj = F.from_binary_pickle(data)
    return data_obj.get("input_tbl"), data_obj.get("output_tbl")


def get_vals_from_input_data_tbl(tbl: ft.DataTable):
    """Считать значения из UI-таблицы ввода."""
    tbl_pre = CMF.datatable_to_dicts(tbl)
    out: dict = {}
    for row in tbl_pre:
        k = row.get("Имя")
        v = row.get("Значение")
        if k in ("ds_mm", "material_name"):
            out[k] = "" if v is None else str(v)
        else:
            try:
                out[k] = F.valm(v)
            except Exception:
                out[k] = v
    return out


def get_name_new_calc(input_vals: dict | None = None) -> str:
    return f"blower_{F.now('%Y-%m-%d(%H%M)')}"
