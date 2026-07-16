from __future__ import annotations

from typing import Any, Optional

import pandas as pd
from utils.formatting import round_half_up_float
from utils.parsing import parse_number_ptbr


def parse_measurement_float(value: Any) -> Optional[float]:
    return parse_number_ptbr(value)


def round_engineering(value: Any, ndigits: int = 1) -> Optional[float]:
    return round_half_up_float(value, ndigits=ndigits)


def normalize_measurement_series(series: pd.Series, ndigits: int = 1) -> pd.Series:
    values = [round_engineering(v, ndigits=ndigits) for v in series]
    return pd.Series(values, index=series.index, dtype="float64")
