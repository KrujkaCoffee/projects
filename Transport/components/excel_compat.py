"""Минимальный слой совместимости с числовой семантикой Excel.

Встроенный :func:`round` Python использует округление к ближайшему чётному,
тогда как Excel округляет половины от нуля. Для расчётной методики это
наблюдаемое различие, поэтому Excel-функции не должны маскироваться обычным
``round()``.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, ROUND_UP
from typing import SupportsFloat


Number = int | float | Decimal | SupportsFloat


def _as_decimal(value: Number) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _quantum(digits: int) -> Decimal:
    return Decimal("1").scaleb(-int(digits))


def excel_round(value: Number, digits: int = 0) -> float:
    """Эквивалент Excel ``ROUND``: половины округляются от нуля."""

    return float(_as_decimal(value).quantize(_quantum(digits), rounding=ROUND_HALF_UP))


def excel_roundup(value: Number, digits: int = 0) -> float:
    """Эквивалент Excel ``ROUNDUP``: всегда от нуля."""

    return float(_as_decimal(value).quantize(_quantum(digits), rounding=ROUND_UP))


def excel_rounddown(value: Number, digits: int = 0) -> float:
    """Эквивалент Excel ``ROUNDDOWN``: всегда к нулю."""

    return float(_as_decimal(value).quantize(_quantum(digits), rounding=ROUND_DOWN))
