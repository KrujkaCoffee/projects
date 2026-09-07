"""Чистое расчётное ядро модуля шумоглушителя.

Модуль не зависит от Flet и БД: входной словарь преобразуется в результат и
диагностику. Благодаря этому методику можно проверять отдельно от интерфейса.
"""

from __future__ import annotations

import operator
from collections import ChainMap
from typing import Any

from components import (
    calc_acoustic_functions as acoustic_functions,
    calc_acoustic_input_params,
    calc_acoustic_output_params,
    calc_silencer_functions_M5_M400 as silencer_functions,
    calc_silencer_input_params,
    calc_silencer_output_params,
)


CONSTANTS = {**calc_silencer_input_params.constants, **acoustic_functions.CONSTANTS}
INPUT_PARAMS = [
    *calc_silencer_input_params.list_dicts_data_input,
    *calc_acoustic_input_params.list_dicts_data_input,
]
INPUT_PARAM_NAMES = frozenset(meta['name'] for meta in INPUT_PARAMS)
OUTPUT_PARAMS = {
    **calc_silencer_output_params.OUTPUT_PARAMS,
    **calc_acoustic_output_params.OUTPUT_PARAMS_ACOUSTIC,
}
CALC_FUNCTIONS = {
    **silencer_functions.CALC_FUNCTIONS,
    **acoustic_functions.CALC_FUNCTIONS,
}
GROUPS = {
    **calc_silencer_output_params.GROUPS,
    **calc_acoustic_output_params.GROUPS,
}

# В пользовательской таблице спектральные строки содержат уровни, а не
# частоты. Частота уже указана в заголовке строки; единица значения — дБ.
_LEVEL_GROUPS = {
    "Уровень звуковой мощности трубы без ШГ, дБ",
    "Уровень звукового давления на расстоянии 1 м. от трубы без ШГ, дБ",
    "Уровень звуковой мощности шумоглушителя, дБ",
    "Уровень звукового давления на расстоянии 1 м. от ШГ, дБ",
}
for _meta in OUTPUT_PARAMS.values():
    if _meta.get("group_name") in _LEVEL_GROUPS:
        _meta["dimension"] = "дБА" if _meta.get("header") == "Полоса А" else "дБ"

# Группа содержит тысячи промежуточных строк и в ТЗ явно исключена из
# стартового раскрытого набора результатов.
GROUPS["Исходный уровень звуковой мощности на входе в глушитель"] = False

OPERATORS = {
    "<=": operator.le,
    ">=": operator.ge,
    "=": operator.eq,
}

_OPTIONAL_TEXT_INPUTS = {"nazvanie_proekta", "nomer_proekta"}

# Ноль допустим только для полей, которые действительно могут отсутствовать
# в выбранной геометрии. Для расхода, давления, диаметра и прочих обязательных
# физических параметров молчаливая подстановка нуля скрывала бы ошибку ввода и
# приводила к делению на ноль дальше по графу формул.
BLANK_ZERO_INPUT_NAMES = frozenset({
    "pozicii",
    "r1_vnutrennij_radius_1_kassety_mm",
    "t1_tolschina_1_kassety_mm",
    "r3_rasstoyanie_m_u_2_kassetoj_i_oblicovkoj_mm",
    "t3_tolschina_oblicovki_mm",
    "r4_rasstoyanie_m_u_2_kassetoj_i_oblicovkoj_mm",
    "t4_tolschina_oblicovki_mm",
    "r5_rasstoyanie_m_u_2_kassetoj_i_oblicovkoj_mm",
    "t5_tolschina_oblicovki_mm",
    "r6_rasstoyanie_m_u_2_kassetoj_i_oblicovkoj_mm",
    "t6_tolschina_oblicovki_mm",
})


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _data_type(meta: dict[str, Any]) -> type:
    value = meta.get("data_type", str)
    if isinstance(value, type):
        return value
    return {"str": str, "int": int, "float": float, "bool": bool}.get(str(value).lower(), str)


def _empty_policy(meta: dict[str, Any]) -> str:
    explicit = meta.get("empty_policy")
    if explicit in {"error", "zero", "default", "empty"}:
        return explicit

    if meta.get("name") in _OPTIONAL_TEXT_INPUTS:
        return "empty"

    if meta.get("name") in BLANK_ZERO_INPUT_NAMES:
        return "zero"
    return "error"


def _coerce_value(value: Any, data_type: type) -> Any:
    if data_type is str:
        return str(value)
    if data_type is float:
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
        return float(value)
    if data_type is int:
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
        number = float(value)
        if not number.is_integer():
            raise ValueError("ожидается целое число")
        return int(number)
    if data_type is bool:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "yes", "1", "on", "да"}:
                return True
            if normalized in {"false", "no", "0", "off", "нет"}:
                return False
            raise ValueError("ожидается логическое значение")
        return bool(value)
    return data_type(value)


def normalize_input_data(input_data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Применяет типы и явные политики пустых полей до запуска формул."""

    # Берём только объявленные пользовательские параметры. Иначе внешний ключ
    # мог бы незаметно подменить константу методики при слиянии словарей.
    normalized: dict[str, Any] = {}
    errors: list[dict[str, Any]] = []

    for meta in INPUT_PARAMS:
        if meta.get("visible", True) is False:
            continue

        name = meta["name"]
        header = meta.get("header", name)
        raw_value = input_data.get(name)
        data_type = _data_type(meta)

        if _is_blank(raw_value):
            policy = _empty_policy(meta)
            if policy == "zero":
                normalized[name] = data_type(0)
                continue
            if policy == "default":
                normalized[name] = meta.get("default_val", meta.get("val"))
                continue
            if policy == "empty":
                normalized[name] = ""
                continue
            errors.append({
                "header": header,
                "val": raw_value,
                "Exception": "Обязательное поле не заполнено",
            })
            continue

        try:
            value = _coerce_value(raw_value, data_type)
            limits = meta.get("min_max_list")
            if isinstance(limits, tuple) and len(limits) == 2:
                if not limits[0] <= value <= limits[1]:
                    raise ValueError(
                        f"значение вне диапазона {limits[0]}…{limits[1]}"
                    )
            elif isinstance(limits, list) and limits:
                allowed = [_coerce_value(item, data_type) for item in limits]
                if value not in allowed:
                    raise ValueError(
                        "допустимые значения: " + ", ".join(map(str, limits))
                    )
            normalized[name] = value
        except (TypeError, ValueError) as exc:
            errors.append({
                "header": header,
                "val": raw_value,
                "Exception": f"Некорректное значение: {exc}",
            })

    return normalized, errors


def default_input_data() -> dict[str, Any]:
    """Возвращает типизированный набор значений по умолчанию для тестов/нового расчёта."""

    raw = {
        meta["name"]: meta.get("default_val", meta.get("val"))
        for meta in INPUT_PARAMS
        if meta.get("visible", True)
    }
    normalized, errors = normalize_input_data(raw)
    if errors:
        raise ValueError(errors)
    return normalized


def calc_new_data(input_data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
    """Выполняет расчёт и возвращает ``(результат, ошибки, успех)``."""

    normalized_input, validation_errors = normalize_input_data(input_data)
    if validation_errors:
        return {}, validation_errors, False

    invisible_params = {
        meta["name"]: meta.get("val") or 0
        for meta in INPUT_PARAMS
        if meta.get("visible", True) is False
    }
    params: dict[str, Any] = {**CONSTANTS, **invisible_params, **normalized_input}
    calculated: dict[str, Any] = {}
    errors: list[dict[str, Any]] = []

    # ChainMap устраняет создание нового объединённого словаря для каждой из
    # тысяч формул, оставаясь read-only контрактом для функций методики.
    formula_params = ChainMap(calculated, params)

    for key, info in CALC_FUNCTIONS.items():
        fn = info["fnc"]
        try:
            checks = []
            for depend_key, rule in OUTPUT_PARAMS.get(key, {}).get("depends", {}).items():
                op = OPERATORS[rule["operator"]]
                checks.append(op(rule["value"], formula_params[depend_key]))

            if all(checks):
                calculated[key] = fn(formula_params)
            else:
                params[key] = 0
        except Exception as exc:
            calculated[key] = None
            errors.append({
                "header": OUTPUT_PARAMS.get(key, {}).get("header", key),
                "param": key,
                "val": "",
                "Exception": str(exc),
            })

    return calculated, errors, not errors
