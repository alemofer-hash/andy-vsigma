from __future__ import annotations

from typing import Any


TIMESTAMP_SPLIT_DATE_COLUMN = "DATA"
TIMESTAMP_SPLIT_TIME_COLUMN = "HORA"
TIMESTAMP_SPLIT_EXCEL_DATE_NUMBER_FORMAT = "dd/mm/yyyy"
TIMESTAMP_SPLIT_EXCEL_TIME_NUMBER_FORMAT = "hh:mm:ss"

_FORMULA_PREFIXES = ("=", "+", "-", "@")


def neutralize_formula_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if not value:
        return value
    return "'" + value if value.startswith(_FORMULA_PREFIXES) else value
