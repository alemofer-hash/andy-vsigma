from __future__ import annotations

import pandas as pd

from .preprocessing import EPSILON, robust_median


def upstream_delta_at(
    df: pd.DataFrame,
    *,
    se: str,
    upstream_references: tuple[str, ...],
    event_peak: str,
    pre_hours: float,
    post_hours: float,
) -> tuple[float | None, bool, tuple[str, ...]]:
    if not upstream_references:
        return None, False, ("upstream_reference_not_configured",)
    event_ts = pd.Timestamp(event_peak)
    candidates = df[(df["se"] == se) & (df["feeder"].isin(upstream_references)) & (df["variable"] == "IB")]
    if candidates.empty:
        return None, False, ("upstream_reference_not_found_in_data",)
    deltas: list[float] = []
    for _, part in candidates.groupby("feeder"):
        pre = part[(part["timestamp"] >= event_ts - pd.Timedelta(hours=pre_hours)) & (part["timestamp"] < event_ts)]["value"]
        post = part[(part["timestamp"] >= event_ts) & (part["timestamp"] <= event_ts + pd.Timedelta(hours=post_hours))]["value"]
        if len(pre) >= 2 and len(post) >= 2:
            deltas.append(float(robust_median(post) - robust_median(pre)))
    if not deltas:
        return None, False, ("upstream_insufficient_window",)
    delta = float(sum(deltas) / len(deltas))
    stable = abs(delta) <= max(5.0, abs(delta) * 0.05 + EPSILON)
    return delta, stable, ()
