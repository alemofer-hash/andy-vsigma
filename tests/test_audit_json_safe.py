from __future__ import annotations

import datetime as dt
import json

from security.audit import _json_safe


def test_json_safe_serializes_datetime_in_nested_structures() -> None:
    payload = {
        "metrics": {"min_ts": dt.datetime(2026, 3, 9, 10, 0, 0), "max_ts": dt.date(2026, 3, 9)},
        "items": [dt.datetime(2026, 1, 1, 12, 30, 0)],
    }
    out = _json_safe(payload)
    txt = json.dumps(out, ensure_ascii=True)
    assert "2026-03-09T10:00:00" in txt
    assert "2026-03-09" in txt
    assert "2026-01-01T12:30:00" in txt
