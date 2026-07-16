from __future__ import annotations

from utils.formatting import format_eng_1dp, round_half_up_float


def test_round_half_up_one_decimal() -> None:
    assert round_half_up_float(1.25, ndigits=1) == 1.3
    assert round_half_up_float(1.24, ndigits=1) == 1.2
    assert round_half_up_float(-1.25, ndigits=1) == -1.3


def test_format_eng_1dp_ptbr() -> None:
    assert format_eng_1dp("14,3208", decimal_comma=True) == "14,3"
    assert format_eng_1dp("14,3500", decimal_comma=True) == "14,4"
