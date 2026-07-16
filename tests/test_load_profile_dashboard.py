"""Semantic consistency tests for load_profile_service."""
from __future__ import annotations

import pandas as pd
import pytest

from desktop_app.load_profile_service import LoadProfileService, classify_shift, SHIFT_DEFS, SHIFT_ORDER, MIDNIGHT_HOUR


def test_shift_boundaries():
    cases = {
        1: "madrugada", 5: "madrugada",
        6: "manha", 11: "manha",
        12: "tarde", 16: "tarde",
        17: "noite", 23: "noite",
    }
    for hour, expected in cases.items():
        ts = pd.Timestamp(f"2025-01-01 {hour:02d}:30:00")
        assert classify_shift(ts) == expected


def test_midnight_excluded():
    assert MIDNIGHT_HOUR == 0
    assert classify_shift(pd.Timestamp("2025-01-01 00:00:00")) is None
    assert classify_shift(pd.Timestamp("2025-01-01 00:30:00")) is None


def test_shift_defs_have_no_overlap():
    covered = set()
    for _name, start, end in SHIFT_DEFS:
        hours = set(range(start, end + 1))
        assert not (covered & hours)
        covered |= hours


def test_build_profile_drops_midnight_and_summarizes():
    df = pd.DataFrame({
        "_TS": pd.to_datetime([
            "2025-01-01 00:00:00",
            "2025-01-01 01:00:00",
            "2025-01-01 06:00:00",
            "2025-01-01 12:00:00",
            "2025-01-01 17:00:00",
        ]),
        "_KEY": ["k"] * 5,
        "_VAL": [99.0, 1.0, 2.0, 3.0, 4.0],
        "_EQUIP": ["TR-001"] * 5,
        "_VAR": ["IA"] * 5,
        "_CLASSE": ["COR"] * 5,
    })
    svc = LoadProfileService()
    profile = svc.build_profile(df, equips=["TR-001"], var="IA")
    assert "TR-001" in profile
    shifts = profile["TR-001"]
    assert set(shifts.keys()) == set(SHIFT_ORDER)
    summary = svc.shift_summary(profile)
    assert len(summary) == 4
    assert summary[summary["shift"] == "madrugada"].iloc[0]["min"] == 1.0
