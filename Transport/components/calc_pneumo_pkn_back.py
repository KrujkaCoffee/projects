from __future__ import annotations

import copy
import math
import os
import pathlib
from dataclasses import asdict, dataclass
from typing import Any

import flet as ft

import components.common_funcs as CMF
from components.common_funcs import Table_data
from components import calc_pneumo_pkn_input_params
from components import calc_pneumo_pkn_output_params
from project_cust_38 import Cust_Excel as CEX
from project_cust_38 import Cust_Functions as F
from project_cust_38 import Cust_SQLite as CSQ
from Config import srv_config as SRVCFG
import data_class as DTCLS



INPUT_PARAMS = calc_pneumo_pkn_input_params.list_dicts_data_input
INPUT_PARAMS_BY_NAME = {item["name"]: item for item in INPUT_PARAMS}
OUTPUT_PARAMS = calc_pneumo_pkn_output_params.OUTPUT_PARAMS
GROUPS = calc_pneumo_pkn_output_params.GROUPS

HELPER_INPUT_NAMES = {item["name"] for item in INPUT_PARAMS if not item.get("editable", True)}
PRIMARY_INPUT_NAMES = [item["name"] for item in INPUT_PARAMS if item.get("editable", True)]
DEFAULT_INPUT_VALUES = {item["name"]: copy.deepcopy(item.get("default_val")) for item in INPUT_PARAMS}


class Cust_module_params:
    def __init__(self):
        self.ver_tbls_data = 1
        self.input_tbl_editbl: Table_data | None = None
        self.output_tbl: Table_data | None = None
        self.filtr_seach_history: str = ""


TBL_INPUT = Table_data()
TBL_INPUT.append_column_desc(name="name", header="Имя", hidden=True, editable=False, unique=True)
TBL_INPUT.append_column_desc(name="header", header="Параметр", hidden=False, editable=False, width=330)
TBL_INPUT.append_column_desc(name="dimension", header="Ед.изм", hidden=False, editable=False, width=100)
TBL_INPUT.append_column_desc(name="val", header="Значение", hidden=False, editable=True, width=190)

TBL_OUTPUT_ERR = Table_data()
TBL_OUTPUT_ERR.append_column_desc(name="name", header="№", hidden=False, editable=False, width=50, unique=True)
TBL_OUTPUT_ERR.append_column_desc(name="header", header="Параметр", hidden=False, editable=False, width=330)
TBL_OUTPUT_ERR.append_column_desc(name="val", header="Значение", hidden=False, editable=False, width=150)
TBL_OUTPUT_ERR.append_column_desc(name="err", header="Ошибка", hidden=False, editable=False, width=420)

TBL_OUTPUT = Table_data()
TBL_OUTPUT.append_column_desc(name="name", header="Имя", hidden=True, editable=False, unique=True)
TBL_OUTPUT.append_column_desc(name="header", header="Параметр", hidden=False, editable=False, width=330)
TBL_OUTPUT.append_column_desc(name="val", header="Значение", hidden=False, editable=False, width=160)
TBL_OUTPUT.append_column_desc(name="dimension", header="Ед.изм", hidden=False, editable=False, width=100)
TBL_OUTPUT.append_column_desc(name="comment", header="Примечание", hidden=False, editable=False, width=420)

TBL_HISTORY = Table_data()
TBL_HISTORY.append_column_desc(name='s_num', header='Номер', hidden=True, editable=False, unique=True)
TBL_HISTORY.append_column_desc(name='date', header='Дата', hidden=False, editable=False, width=300)
TBL_HISTORY.append_column_desc(name='name', header='Название', hidden=False, editable=False, width=500)

def is_empty(val: Any) -> bool:
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


def _header_for(name: str) -> str:
    meta = INPUT_PARAMS_BY_NAME.get(name)
    if meta:
        return str(meta.get("header") or name)
    meta = OUTPUT_PARAMS.get(name)
    if meta:
        return str(meta.get("header") or name)
    return name


def _build_error(name: str, val: Any, message: str) -> dict[str, Any]:
    return {"header": _header_for(name), "val": val, "Exception": message}


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, int)):
        return float(value)
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
        if value == "":
            return None
        return float(value)
    return float(value)


def _extract_user_input_values(raw: dict[str, Any]) -> dict[str, Any]:
    return {name: raw.get(name) for name in PRIMARY_INPUT_NAMES}


@dataclass(slots=True)
class PneumoPknInputs:
    pump_volume_m3: float
    purge_time_sec: float
    loading_time_sec: float
    load_time_sec: float
    waiting_time_sec: float
    particle_size_mm: float
    material_density_kg_m3: float
    bulk_density_kg_m3: float
    system_temp_c: float
    horizontal_pipe_length_m: float
    vertical_pipe_length_m: float
    system_ash_flow_kg_h: float
    gravity_m_s2: float
    mass_concentration_kg_kg: float
    outlet_air_velocity_m_s: float
    turns_90_count: int
    turns_60_count: int
    turns_30_count: int
    flow_switches_count: int
    compressor_and_airline_losses_bar: float
    atmospheric_pressure_pa: float
    safety_factor: float
    actual_diameter_m: float

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "PneumoPknInputs":
        return cls(
            pump_volume_m3=float(raw["pump_volume_m3"]),
            purge_time_sec=float(raw["purge_time_sec"]),
            loading_time_sec=float(raw["loading_time_sec"]),
            load_time_sec=float(raw["load_time_sec"]),
            waiting_time_sec=float(raw["waiting_time_sec"]),
            particle_size_mm=float(raw["particle_size_mm"]),
            material_density_kg_m3=float(raw["material_density_kg_m3"]),
            bulk_density_kg_m3=float(raw["bulk_density_kg_m3"]),
            system_temp_c=float(raw["system_temp_c"]),
            horizontal_pipe_length_m=float(raw["horizontal_pipe_length_m"]),
            vertical_pipe_length_m=float(raw["vertical_pipe_length_m"]),
            system_ash_flow_kg_h=float(raw["system_ash_flow_kg_h"]),
            gravity_m_s2=float(raw["gravity_m_s2"]),
            mass_concentration_kg_kg=float(raw["mass_concentration_kg_kg"]),
            outlet_air_velocity_m_s=float(raw["outlet_air_velocity_m_s"]),
            turns_90_count=int(raw["turns_90_count"]),
            turns_60_count=int(raw["turns_60_count"]),
            turns_30_count=int(raw["turns_30_count"]),
            flow_switches_count=int(raw["flow_switches_count"]),
            compressor_and_airline_losses_bar=float(raw["compressor_and_airline_losses_bar"]),
            atmospheric_pressure_pa=float(raw["atmospheric_pressure_pa"]),
            safety_factor=float(raw["safety_factor"]),
            actual_diameter_m=float(raw["actual_diameter_m"]),
        )


@dataclass(slots=True)
class PneumoPknDerivedLeft:
    unloading_time_sec: float
    system_temp_k: float
    gas_constant_j_kg_k: float
    dynamic_viscosity_pa_s: float
    air_density_kg_m3: float
    kinematic_viscosity_m2_s: float


@dataclass(slots=True)
class PneumoPknOutputs:
    productivity_unloading_kg_s: float
    productivity_cycles_per_hour: float
    productivity_by_cycles_kg_h: float
    mass_pump_volume_kg: float
    pump_cycle_count_per_hour: float
    solid_flow_m3_h: float
    reduced_length_m: float
    settling_velocity_m_s: float
    archimedes_number: float
    reynolds_number_for_settling: float
    air_flow_m3_min: float
    calculated_diameter_m: float
    actual_diameter_m: float
    s_for_beta: float
    beta_coefficient: float
    transport_resistance_bar: float
    compressor_pressure_bar: float
    inlet_air_velocity_m_s: float


@dataclass(slots=True)
class PneumoPknResult:
    inputs: PneumoPknInputs
    left: PneumoPknDerivedLeft
    outputs: PneumoPknOutputs

    def as_flat_dict(self) -> dict[str, Any]:
        return {
            **asdict(self.left),
            **asdict(self.outputs),
        }


def _safe_div(numerator: float, denominator: float, *, field_name: str) -> float:
    if denominator == 0:
        raise ZeroDivisionError(f"Поле `{_header_for(field_name)}` привело к делению на ноль")
    return numerator / denominator

def clean_unicode(string):
    if not isinstance(string, str): return ''
    return ''.join(symbol for symbol in string if not (0x2790 <= ord(symbol) <= 0x27BF))

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
    row = [F.now(), name, Data.Data_user.login or "", F.to_binary_pickle(data_save)]
    try:
        return CSQ.custom_request_c(
            Data.Data_user.db_flet,
            f"""INSERT INTO pneumo_pkn_history (date, name, login, data) VALUES ({CSQ.questions_for_mask(row)})""",
            list_of_lists_c=[row],
        )
    except Exception:
        return False

def save_word(list_dict_rez_input: list, list_dict_rez_output: list, name: str, dir_save: str, name_module: str) -> str | bool:
    list_dict_rez_input = [{clean_unicode(k): clean_unicode(v) for k, v in _.items() if k != 'Имя'} for _ in list_dict_rez_input]
    list_dict_rez_output = [{clean_unicode(k): clean_unicode(v) for k, v in _.items() if k != 'Имя'} for _ in list_dict_rez_output]
    name_file = f'{name}.docx'
    pathlib.Path(dir_save).mkdir(parents=True, exist_ok=True)
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
        f"""SELECT data FROM pneumo_pkn_history WHERE s_num == {int(s_num)}""",
        one=True,
        one_column=True,
        hat_c=False,
    )
    if not data:
        return False
    data_obj = F.from_binary_pickle(data)
    return data_obj.get("input_tbl"), data_obj.get("output_tbl")

def make_history_tbl_data(Data: DTCLS.Data_page):
    tbl_history_tmp = copy.deepcopy(TBL_HISTORY)
    filter_value = str(getattr(Data.Data_module.cust_data, "filtr_seach_history", "") or "").strip()
    where = "" if filter_value == "" else f'and name like "%{filter_value}%"'

    try:
        list_calcs = CSQ.custom_request_c(
            Data.Data_user.db_flet,
            f"""SELECT * FROM pneumo_pkn_history WHERE login = '{Data.Data_user.login}' {where} ORDER BY s_num DESC LIMIT 20;""",
            rez_dict=True,
        )
    except Exception:
        list_calcs = []

    for calc in list_calcs:
        row = CMF.Row_data()
        row.append(calc.get('s_num'), CMF.Cell_description())
        row.append(calc.get('date'), CMF.Cell_description())
        row.append(calc.get('name'), CMF.Cell_description())
        tbl_history_tmp.add_row(row)

    return tbl_history_tmp

def validate_inputs(raw: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []

    positive_names = {
        "pump_volume_m3",
        "particle_size_mm",
        "material_density_kg_m3",
        "bulk_density_kg_m3",
        "horizontal_pipe_length_m",
        "system_ash_flow_kg_h",
        "gravity_m_s2",
        "mass_concentration_kg_kg",
        "outlet_air_velocity_m_s",
        "atmospheric_pressure_pa",
        "safety_factor",
        "actual_diameter_m",
    }
    non_negative_names = {
        "purge_time_sec",
        "loading_time_sec",
        "load_time_sec",
        "waiting_time_sec",
        "vertical_pipe_length_m",
        "turns_90_count",
        "turns_60_count",
        "turns_30_count",
        "flow_switches_count",
        "compressor_and_airline_losses_bar",
    }
    integer_like_names = {
        "turns_90_count",
        "turns_60_count",
        "turns_30_count",
        "flow_switches_count",
    }

    for name in PRIMARY_INPUT_NAMES:
        value = raw.get(name)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            errors.append(_build_error(name, value, "Поле обязательно для расчёта"))
            continue

        if name in positive_names:
            try:
                numeric = _as_float(value)
                if numeric is None or numeric <= 0:
                    errors.append(_build_error(name, value, "Значение должно быть больше нуля"))
            except Exception:
                errors.append(_build_error(name, value, "Не удалось распознать число"))
            continue

        if name in non_negative_names:
            try:
                numeric = _as_float(value)
                if numeric is None or numeric < 0:
                    errors.append(_build_error(name, value, "Значение не должно быть отрицательным"))
            except Exception:
                errors.append(_build_error(name, value, "Не удалось распознать число"))
            continue

    for name in integer_like_names:
        value = raw.get(name)
        if value is None:
            continue
        try:
            numeric = float(value)
            if not numeric.is_integer():
                errors.append(_build_error(name, value, "Ожидается целое число"))
        except Exception:
            errors.append(_build_error(name, value, "Ожидается целое число"))

    return errors


def generate_rezult_data_for_save(name: str, input_tbl: ft.DataTable, output_tbl: ft.DataTable) -> dict:
    list_dict_rez_input = CMF.datatable_to_dicts(input_tbl)
    list_dict_rez_output = CMF.datatable_to_dicts(output_tbl)
    return {'name': name, 'input': list_dict_rez_input, 'output': list_dict_rez_output}

def calc_pneumo_pkn(inputs: PneumoPknInputs) -> PneumoPknResult:
    system_temp_k = 273 + inputs.system_temp_c
    gas_constant_j_kg_k = 287.0
    dynamic_viscosity_pa_s = 1.458e-6 * (system_temp_k ** 1.5) / (system_temp_k + 110.4)
    air_density_kg_m3 = inputs.atmospheric_pressure_pa * 28.98 / (8.314 * system_temp_k) / 1000
    kinematic_viscosity_m2_s = _safe_div(
        dynamic_viscosity_pa_s,
        air_density_kg_m3,
        field_name="air_density_kg_m3",
    )

    mass_pump_volume_kg = inputs.pump_volume_m3 * inputs.bulk_density_kg_m3
    air_flow_m3_min = 0.785 * (inputs.actual_diameter_m ** 2) * inputs.outlet_air_velocity_m_s * 60 * 1.05
    unloading_time_sec = 60 * _safe_div(
        (inputs.pump_volume_m3 * inputs.bulk_density_kg_m3),
        (inputs.mass_concentration_kg_kg * air_flow_m3_min),
        field_name="mass_concentration_kg_kg",
    )

    productivity_unloading_kg_s = _safe_div(mass_pump_volume_kg, unloading_time_sec, field_name="unloading_time_sec")
    productivity_cycles_per_hour = _safe_div(
        3600.0,
        (
            unloading_time_sec
            + inputs.loading_time_sec
            + inputs.load_time_sec
            + inputs.purge_time_sec
            + inputs.waiting_time_sec
        ),
        field_name="loading_time_sec",
    )
    productivity_by_cycles_kg_h = mass_pump_volume_kg * productivity_cycles_per_hour
    pump_cycle_count_per_hour = _safe_div(
        inputs.system_ash_flow_kg_h, mass_pump_volume_kg, field_name="bulk_density_kg_m3"
    )
    solid_flow_m3_h = _safe_div(inputs.system_ash_flow_kg_h, inputs.bulk_density_kg_m3, field_name="bulk_density_kg_m3")
    reduced_length_m = (
        inputs.horizontal_pipe_length_m
        + inputs.vertical_pipe_length_m
        + (inputs.turns_90_count * 8 + inputs.turns_60_count * 6 + inputs.turns_30_count * 3)
        + (inputs.flow_switches_count * 8)
    )

    archimedes_number = (
        ((inputs.particle_size_mm / 1000.0) ** 3)
        * inputs.gravity_m_s2
        * (inputs.material_density_kg_m3 - air_density_kg_m3)
    ) / (air_density_kg_m3 * (kinematic_viscosity_m2_s ** 2))

    reynolds_number_for_settling = archimedes_number / (
        18.0 + 0.61 * math.sqrt(archimedes_number)
    )
    settling_velocity_m_s = (
        _safe_div(reynolds_number_for_settling * kinematic_viscosity_m2_s, inputs.particle_size_mm, field_name="particle_size_mm")
        * 1000.0
    )
    calculated_diameter_m = 0.019 * math.sqrt(
        _safe_div(
            inputs.system_ash_flow_kg_h,
            (inputs.outlet_air_velocity_m_s * air_density_kg_m3 * inputs.mass_concentration_kg_kg),
            field_name="mass_concentration_kg_kg",
        )
    )
    s_for_beta = reduced_length_m * ((inputs.mass_concentration_kg_kg * (inputs.outlet_air_velocity_m_s ** 2)) / inputs.actual_diameter_m)
    beta_coefficient = 6.0 / (s_for_beta / 1_000_000.0) + 0.11
    transport_resistance_bar = (
        math.sqrt(1.0 + (beta_coefficient * s_for_beta * 10 ** (-6)))
        + (
            inputs.vertical_pipe_length_m
            * air_density_kg_m3
            * 2.5
            * inputs.mass_concentration_kg_kg
            * ((inputs.outlet_air_velocity_m_s / inputs.outlet_air_velocity_m_s) - settling_velocity_m_s)
            + ((air_density_kg_m3 * inputs.mass_concentration_kg_kg * (10.0 - settling_velocity_m_s)) / inputs.gravity_m_s2)
        )
        * (10 ** (-4))
        - 1.0
    )
    compressor_pressure_bar = transport_resistance_bar * inputs.safety_factor + inputs.compressor_and_airline_losses_bar
    inlet_air_velocity_m_s = _safe_div(
        air_flow_m3_min / 60.0,
        (
            transport_resistance_bar
            * (math.pi * ((inputs.actual_diameter_m / 2.0) ** 2))
        ),
        field_name="transport_resistance_bar",
    )

    left = PneumoPknDerivedLeft(
        unloading_time_sec=unloading_time_sec,
        system_temp_k=system_temp_k,
        gas_constant_j_kg_k=gas_constant_j_kg_k,
        dynamic_viscosity_pa_s=dynamic_viscosity_pa_s,
        air_density_kg_m3=air_density_kg_m3,
        kinematic_viscosity_m2_s=kinematic_viscosity_m2_s,
    )
    outputs = PneumoPknOutputs(
        productivity_unloading_kg_s=productivity_unloading_kg_s,
        productivity_cycles_per_hour=productivity_cycles_per_hour,
        productivity_by_cycles_kg_h=productivity_by_cycles_kg_h,
        mass_pump_volume_kg=mass_pump_volume_kg,
        pump_cycle_count_per_hour=pump_cycle_count_per_hour,
        solid_flow_m3_h=solid_flow_m3_h,
        reduced_length_m=reduced_length_m,
        settling_velocity_m_s=settling_velocity_m_s,
        archimedes_number=archimedes_number,
        reynolds_number_for_settling=reynolds_number_for_settling,
        air_flow_m3_min=air_flow_m3_min,
        calculated_diameter_m=calculated_diameter_m,
        actual_diameter_m=inputs.actual_diameter_m,
        s_for_beta=s_for_beta,
        beta_coefficient=beta_coefficient,
        transport_resistance_bar=transport_resistance_bar,
        compressor_pressure_bar=compressor_pressure_bar,
        inlet_air_velocity_m_s=inlet_air_velocity_m_s,
    )
    return PneumoPknResult(inputs=inputs, left=left, outputs=outputs)


def calc_new_data(input_data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
    errors = validate_inputs(input_data)
    if errors:
        return {}, errors, False

    try:
        user_inputs = _extract_user_input_values(input_data)
        inputs = PneumoPknInputs.from_mapping(user_inputs)
        result = calc_pneumo_pkn(inputs)
        return result.as_flat_dict(), [], True
    except Exception as exc:
        return {}, [_build_error("pump_volume_m3", "", str(exc))], False

def fixed_round(value, max_decimal_part: int = 2):
    value_str = str(value)
    if '.' in value_str:
        decimal_part = value_str.split('.')[1]
        if len(decimal_part) > max_decimal_part:
            return round(value, max_decimal_part)
    return value


def clean_result(raw: dict[str, Any]) -> dict[str, Any]:
    """Постобработка значений результата"""
    new_calced = {}
    for field, value in raw.items():
        if isinstance(value, float):
            value = fixed_round(value, max_decimal_part=2)
        new_calced[field] = value
    return new_calced

def calc_new_tbl_input(default_vals: dict[str, Any] | None = None) -> Table_data:
    tbl = copy.deepcopy(TBL_INPUT)
    tbl.add_table_name("pneumo_pkn_input", "Входные данные")
    prev_group = ""
    merged_values = {**DEFAULT_INPUT_VALUES, **(default_vals or {})}
    values = clean_result(merged_values)
    for item in INPUT_PARAMS:
        group_name = str(item.get("group_name") or "")
        if group_name and group_name != prev_group:
            prev_group = group_name
            tbl.add_group(f"{item['name']}_group", group_name)

        row = CMF.Row_data()
        row.append(item["name"], CMF.Cell_description())
        row.append(item["header"], CMF.Cell_description(data_type=str))
        row.append(item.get("dimension", "") or "", CMF.Cell_description(data_type=str))
        row.append(
            values.get(item["name"], item.get("default_val")),
            CMF.Cell_description(
                min_max_list=item.get("min_max_list"),
                comment=item.get("comment"),
                data_type=item.get("data_type", "str"),
                accuracy=item.get("accuracy", 2),
                default_val=item.get("default_val"),
            ),
        )
        tbl.add_row(row)

    return tbl


def generate_input_data(fnc_onchange, ref, default_vals: dict[str, Any] | None = None) -> tuple[ft.DataTable, Table_data]:
    table_data = calc_new_tbl_input(default_vals)
    table_view = CMF.Table_view(table_data, ref=ref, fnc_onchange=fnc_onchange)
    return table_view, table_data


def apply_calculated_to_input_table(table_data: CMF.Table_data, calculated: dict[str, Any]) -> None:
    for name in HELPER_INPUT_NAMES:
        if name not in calculated:
            continue
        row = table_data.get_row_by_unique_name(name)
        if row is None:
            continue
        row.set_new_val("val", calculated[name])


def prepare_calc_new_data(data: list[dict] | None, Data: DTCLS.Data_page) -> tuple[dict[str, Any] | None, list[dict[str, Any]], bool]:
    if not Data.Data_module.cust_data or not Data.Data_module.cust_data.input_tbl_editbl.sync_ui_to_data("val"):
        return None, [], False

    data_params = Data.Data_module.cust_data.input_tbl_editbl.to_dict_by_unique()
    raw = {k: v["val"] for k, v in data_params.items()}
    return calc_new_data(raw)


def make_res_tbl(data: dict[str, Any], ref_out=None, fnc_cell_click=None) -> CMF.Table_data:
    new_tbl_output: Table_data = copy.deepcopy(TBL_OUTPUT)
    new_tbl_output.add_table_name("pneumo_pkn_output", "Расчетные данные")

    for group_name, is_view in GROUPS.items():
        if not is_view:
            continue

        group_items: list[tuple[str, Any]] = []
        for key, meta in OUTPUT_PARAMS.items():
            if meta.get("group_name") != group_name:
                continue
            if not meta.get("view", True):
                continue
            value = data.get(key)
            if is_empty(value):
                continue
            group_items.append((key, value))

        if not group_items:
            continue

        new_tbl_output.add_group(f"{group_name}_group", group_name)

        for key, value in group_items:
            meta = OUTPUT_PARAMS[key]
            row = CMF.Row_data()
            row.group_name = group_name
            row.append(key, CMF.Cell_description())
            row.append(meta["header"], CMF.Cell_description(data_type=str))
            if isinstance(value, (int, float)):
                row.append(float(value), CMF.Cell_description(accuracy=meta.get("accuracy", 2), data_type=float))
            else:
                row.append(value, CMF.Cell_description(data_type=str))
            row.append(meta.get("dimension", "") or "", CMF.Cell_description(data_type=str))
            row.append(meta.get("comment", "") or "", CMF.Cell_description(data_type=str))
            new_tbl_output.add_row(row)
    CMF.Table_view(new_tbl_output, ref=ref_out, fnc_on_click=fnc_cell_click, lazy_groups=True, single_group_expand=False)
    return new_tbl_output


def make_err_tbl(data: list[dict[str, Any]], ref_out=None) -> CMF.Table_data:
    tbl = copy.deepcopy(TBL_OUTPUT_ERR)
    tbl.add_table_name("pneumo_pkn_errors", "Ошибки расчёта")
    for i, item in enumerate(data, start=1):
        row = CMF.Row_data()
        row.append(str(i), CMF.Cell_description(data_type=str))
        row.append(item.get("header", ""), CMF.Cell_description(data_type=str))
        row.append(item.get("val", ""), CMF.Cell_description(data_type=str))
        row.append(item.get("Exception", ""), CMF.Cell_description(data_type=str))
        tbl.add_row(row)

    CMF.Table_view(tbl, ref=ref_out)
    return tbl

def get_name_new_calc(input_vals: dict | None = None) -> str:
    from project_cust_38 import Cust_Functions as F
    return f"pneumo_pkn_{F.now('%Y-%m-%d(%H%M)')}"