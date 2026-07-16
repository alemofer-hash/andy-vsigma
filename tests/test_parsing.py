from __future__ import annotations

import warnings

import pandas as pd

from utils.parsing import parse_number_ptbr, parse_timestamp_br


def test_parse_timestamp_br_dayfirst_without_warning() -> None:
    s = pd.Series(["31/12/2023 23:59:59", "01/01/2024", "15/02/2024 08:30"])
    with warnings.catch_warnings(record=True) as got:
        warnings.simplefilter("always")
        out = parse_timestamp_br(s, field_name="E3TIMESTAMP")
    assert str(out.iloc[0]) == "2023-12-31 23:59:59"
    assert out.iloc[1].day == 1 and out.iloc[1].month == 1
    assert out.iloc[2].day == 15 and out.iloc[2].month == 2
    assert not any("dayfirst=False" in str(w.message) for w in got)


def test_parse_number_ptbr_variants() -> None:
    assert parse_number_ptbr("14,3208") == 14.3208
    assert parse_number_ptbr("1.234,56") == 1234.56
    assert parse_number_ptbr("") is None
    assert parse_number_ptbr("NA") is None
