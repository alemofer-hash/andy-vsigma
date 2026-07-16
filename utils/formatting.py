from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Optional

import pandas as pd

from utils.parsing import parse_number_ptbr


def round_half_up_float(value: Any, ndigits: int = 1) -> Optional[float]:
    parsed = parse_number_ptbr(value)
    if parsed is None:
        return None
    q = Decimal("1").scaleb(-ndigits)
    try:
        rounded = Decimal(str(parsed)).quantize(q, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None
    return float(rounded)


def format_eng_1dp(value: Any, *, decimal_comma: bool = True) -> str:
    rounded = round_half_up_float(value, ndigits=1)
    if rounded is None or pd.isna(rounded):
        return ""
    txt = f"{Decimal(str(rounded)).quantize(Decimal('0.0'), rounding=ROUND_HALF_UP)}"
    return txt.replace(".", ",") if decimal_comma else txt
