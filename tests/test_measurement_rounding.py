from __future__ import annotations

import pandas as pd

from andys_report_runner import aggregate_long
from measurement_value import normalize_measurement_series, round_engineering


def test_round_engineering_half_up_single_decimal() -> None:
    assert round_engineering("1,25", ndigits=1) == 1.3
    assert round_engineering("1,24", ndigits=1) == 1.2
    assert round_engineering("14,320833166440333333333333333", ndigits=1) == 14.3


def test_normalize_measurement_series_handles_decimal_comma() -> None:
    s = pd.Series(["10,55", "10.54", "1.234,56", None, ""])
    out = normalize_measurement_series(s, ndigits=1)
    assert out.iloc[0] == 10.6
    assert out.iloc[1] == 10.5
    assert out.iloc[2] == 1234.6
    assert pd.isna(out.iloc[3])
    assert pd.isna(out.iloc[4])


def test_aggregate_long_uses_standard_rounding() -> None:
    df = pd.DataFrame(
        {
            "timestamp": ["2025-01-01 00:00:00", "2025-01-01 00:00:00"],
            "equip_id": ["TR-1", "TR-1"],
            "var": ["IA", "IA"],
            "classe": ["COR", "COR"],
            "valor": ["10,54", "10,55"],
        }
    )
    out = aggregate_long(df, agg="max", time_floor=None)
    assert len(out) == 1
    assert float(out.iloc[0]["_VAL"]) == 10.6
