from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CadenceStats:
    cadence_seconds: float | None
    gap_count: int
    duplicate_count: int
    coverage_start: str | None
    coverage_end: str | None
    continuous_segments: int
    gap_mask: list[bool]


def infer_cadence(timestamps: pd.Series) -> CadenceStats:
    if timestamps.empty:
        return CadenceStats(None, 0, 0, None, None, 0, [])
    ordered = pd.to_datetime(timestamps).sort_values()
    duplicate_count = int(ordered.duplicated().sum())
    unique = ordered.drop_duplicates()
    if len(unique) < 2:
        start = unique.iloc[0].isoformat() if len(unique) else None
        return CadenceStats(None, 0, duplicate_count, start, start, 1 if len(unique) else 0, [])
    diffs = unique.diff().dt.total_seconds().dropna()
    positive = diffs[diffs > 0]
    cadence = float(positive.median()) if len(positive) else None
    if cadence is None or cadence <= 0:
        gaps = [False] * len(unique)
        gap_count = 0
    else:
        gaps = [False] + [bool(value > cadence * 1.5) for value in positive.tolist()]
        gap_count = int(sum(gaps))
    return CadenceStats(
        cadence_seconds=cadence,
        gap_count=gap_count,
        duplicate_count=duplicate_count,
        coverage_start=unique.iloc[0].isoformat(),
        coverage_end=unique.iloc[-1].isoformat(),
        continuous_segments=gap_count + 1,
        gap_mask=gaps,
    )


def segment_continuous(df: pd.DataFrame, cadence_seconds: float | None) -> list[pd.DataFrame]:
    if df.empty:
        return []
    ordered = df.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    if cadence_seconds is None or cadence_seconds <= 0:
        return [ordered]
    gaps = ordered["timestamp"].diff().dt.total_seconds().fillna(cadence_seconds)
    segment_id = (gaps > cadence_seconds * 1.5).cumsum()
    return [part.reset_index(drop=True) for _, part in ordered.groupby(segment_id) if not part.empty]
