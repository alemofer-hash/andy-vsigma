from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .cadence import infer_cadence, segment_continuous
from .preprocessing import robust_z_series


@dataclass(frozen=True)
class SynchronizedPair:
    se: str
    first: str
    second: str
    data: pd.DataFrame
    cadence_seconds: float | None
    coverage_common: float
    residues: tuple[str, ...]


def synchronize_pair(df: pd.DataFrame, se: str, first: str, second: str, min_common_coverage: float) -> SynchronizedPair:
    left = _series_for(df, se, first)
    right = _series_for(df, se, second)
    if left.empty or right.empty:
        return SynchronizedPair(se, first, second, pd.DataFrame(), None, 0.0, ("missing_feeder_series",))
    left = left.groupby("timestamp", as_index=False)["value"].median().rename(columns={"value": f"IB_{first}_raw"})
    right = right.groupby("timestamp", as_index=False)["value"].median().rename(columns={"value": f"IB_{second}_raw"})
    merged = pd.merge(left, right, on="timestamp", how="inner").sort_values("timestamp").reset_index(drop=True)
    cadence_left = infer_cadence(left["timestamp"])
    cadence_right = infer_cadence(right["timestamp"])
    cadence = cadence_left.cadence_seconds or cadence_right.cadence_seconds
    denom = max(len(left), len(right), 1)
    coverage = len(merged) / denom
    residues: list[str] = []
    if coverage < min_common_coverage:
        residues.append("insufficient_common_coverage")
    if cadence_left.gap_count or cadence_right.gap_count:
        residues.append("source_gaps_present")
    if not merged.empty:
        merged[f"IB_{first}_z"] = robust_z_series(merged[f"IB_{first}_raw"])
        merged[f"IB_{second}_z"] = robust_z_series(merged[f"IB_{second}_raw"])
        segment_ids = []
        segments = segment_continuous(merged[["timestamp"]].copy(), cadence)
        if segments:
            lookup = {}
            for segment_index, segment in enumerate(segments):
                for ts in segment["timestamp"]:
                    lookup[ts] = segment_index
            segment_ids = [lookup.get(ts, 0) for ts in merged["timestamp"]]
        merged["segment_id"] = segment_ids or 0
    return SynchronizedPair(se, first, second, merged, cadence, coverage, tuple(residues))


def _series_for(df: pd.DataFrame, se: str, feeder: str) -> pd.DataFrame:
    part = df[(df["se"] == se) & (df["feeder"] == feeder) & (df["variable"] == "IB")][["timestamp", "value"]].copy()
    return part.dropna(subset=["timestamp", "value"]).sort_values("timestamp")
