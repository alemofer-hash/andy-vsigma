from __future__ import annotations

from audit.export_auditor import apply_recommendation


def test_apply_recommendation_updates_timefloor_and_agg_and_max_timestamps() -> None:
    base = {
        "t0": "2025-01-01 00:00:00",
        "t1": "2025-12-31 23:59:59",
        "time_floor": "",
        "agg": "max",
        "max_timestamps": 300000,
    }
    out_floor = apply_recommendation(base, "set_timefloor_1h")
    assert out_floor["time_floor"] == "1H"

    out_agg = apply_recommendation(base, "set_agg_last")
    assert out_agg["agg"] == "last"

    out_max = apply_recommendation(base, "set_max_ts_safe")
    assert int(out_max["max_timestamps"]) > 0


def test_apply_recommendation_updates_date_range() -> None:
    base = {
        "t0": "",
        "t1": "",
        "time_floor": "",
        "agg": "max",
        "max_timestamps": 100000,
    }
    out = apply_recommendation(base, "set_last_90d")
    assert isinstance(out["t0"], str) and len(out["t0"]) >= 19
    assert isinstance(out["t1"], str) and len(out["t1"]) >= 19
