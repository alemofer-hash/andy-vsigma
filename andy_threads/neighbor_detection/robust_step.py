from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .models import LocalChangeCandidate, stable_hash
from .preprocessing import EPSILON, clamp01, robust_mad, robust_median


@dataclass(frozen=True)
class StepDetectionConfig:
    pre_windows_hours: tuple[float, ...]
    post_windows_hours: tuple[float, ...]
    min_persistence_samples: int
    robust_z_threshold: float


def detect_local_changes(
    data: pd.DataFrame,
    *,
    se: str,
    feeder: str,
    equipment: str,
    terminal: str,
    value_column: str,
    cadence_seconds: float | None,
    config: StepDetectionConfig,
) -> list[LocalChangeCandidate]:
    if data.empty or value_column not in data:
        return []
    ordered = data.sort_values("timestamp").reset_index(drop=True)
    if len(ordered) < config.min_persistence_samples * 2 + 1:
        return []
    values = ordered[value_column].astype(float)
    diff = values.diff().abs().fillna(0.0)
    diff_threshold = float(diff.median() + 3.0 * max(robust_mad(diff), EPSILON))
    seed_indexes = sorted(set(int(idx) for idx in diff[diff >= diff_threshold].index if 0 < idx < len(ordered) - 1))
    candidates: list[LocalChangeCandidate] = []
    seen: set[tuple[str, float, float]] = set()
    for idx in seed_indexes:
        timestamp = ordered.loc[idx, "timestamp"]
        for pre_hours in config.pre_windows_hours:
            for post_hours in config.post_windows_hours:
                candidate = _evaluate_timestamp(
                    ordered,
                    idx,
                    timestamp,
                    se=se,
                    feeder=feeder,
                    equipment=equipment,
                    terminal=terminal,
                    value_column=value_column,
                    pre_hours=pre_hours,
                    post_hours=post_hours,
                    cadence_seconds=cadence_seconds,
                    min_persistence_samples=config.min_persistence_samples,
                    robust_z_threshold=config.robust_z_threshold,
                )
                if candidate is None:
                    continue
                key = (candidate.timestamp, pre_hours, post_hours)
                if key not in seen:
                    seen.add(key)
                    candidates.append(candidate)
    return _dedupe_nearby(candidates, cadence_seconds)


def _evaluate_timestamp(
    ordered: pd.DataFrame,
    idx: int,
    timestamp: pd.Timestamp,
    *,
    se: str,
    feeder: str,
    equipment: str,
    terminal: str,
    value_column: str,
    pre_hours: float,
    post_hours: float,
    cadence_seconds: float | None,
    min_persistence_samples: int,
    robust_z_threshold: float,
) -> LocalChangeCandidate | None:
    pre_start = timestamp - pd.Timedelta(hours=pre_hours)
    post_end = timestamp + pd.Timedelta(hours=post_hours)
    pre = ordered[(ordered["timestamp"] >= pre_start) & (ordered["timestamp"] < timestamp)]
    post = ordered[(ordered["timestamp"] >= timestamp) & (ordered["timestamp"] <= post_end)]
    if len(pre) < min_persistence_samples or len(post) < min_persistence_samples:
        return None
    if _crosses_gap(pre, cadence_seconds) or _crosses_gap(post, cadence_seconds):
        return None
    pre_values = pre[value_column].astype(float)
    post_values = post[value_column].astype(float)
    pre_median = robust_median(pre_values)
    post_median = robust_median(post_values)
    delta = post_median - pre_median
    local_mad = max(robust_mad(pd.concat([pre_values, post_values])), EPSILON)
    robust_z = abs(delta) / local_mad
    if robust_z < robust_z_threshold:
        return None
    persistence = _persistence_score(post_values, pre_median, delta, min_persistence_samples)
    if persistence <= 0.0:
        return None
    pre_stability = 1.0 / (1.0 + robust_mad(pre_values))
    post_stability = 1.0 / (1.0 + robust_mad(post_values))
    quality = clamp01((pre_stability + post_stability) / 2.0) * persistence
    delta_relative = delta / (abs(pre_median) + EPSILON)
    return LocalChangeCandidate(
        candidate_id="lc-" + stable_hash((se, feeder, timestamp.isoformat(), round(delta, 6), pre_hours, post_hours)),
        se=se,
        feeder=feeder,
        equipment=equipment,
        terminal=terminal,
        timestamp=timestamp.isoformat(),
        pre_window_hours=pre_hours,
        post_window_hours=post_hours,
        delta_i=float(delta),
        delta_relative=float(delta_relative),
        robust_z=float(robust_z),
        pre_median=float(pre_median),
        post_median=float(post_median),
        pre_stability=float(pre_stability),
        post_stability=float(post_stability),
        persistence_score=float(persistence),
        quality_score=float(quality),
        gap_proximity=False,
    )


def _persistence_score(post_values: pd.Series, pre_median: float, delta: float, min_persistence_samples: int) -> float:
    if len(post_values) < min_persistence_samples or abs(delta) <= EPSILON:
        return 0.0
    direction = math.copysign(1.0, delta)
    moved = ((post_values.astype(float) - pre_median) * direction) > (abs(delta) * 0.35)
    required = moved.iloc[:min_persistence_samples].all()
    if not bool(required):
        return 0.0
    return clamp01(float(moved.mean()))


def _crosses_gap(part: pd.DataFrame, cadence_seconds: float | None) -> bool:
    if cadence_seconds is None or cadence_seconds <= 0 or len(part) < 2:
        return False
    diffs = part["timestamp"].diff().dt.total_seconds().dropna()
    return bool((diffs > cadence_seconds * 1.5).any())


def _dedupe_nearby(candidates: list[LocalChangeCandidate], cadence_seconds: float | None) -> list[LocalChangeCandidate]:
    if not candidates:
        return []
    window_seconds = max(float(cadence_seconds or 3600.0), 1.0)
    ordered = sorted(candidates, key=lambda item: (item.timestamp, -item.robust_z))
    kept: list[LocalChangeCandidate] = []
    for candidate in ordered:
        ts = pd.Timestamp(candidate.timestamp)
        near = False
        for existing in kept:
            if abs((ts - pd.Timestamp(existing.timestamp)).total_seconds()) <= window_seconds:
                near = True
                if candidate.robust_z > existing.robust_z:
                    kept.remove(existing)
                    kept.append(candidate)
                break
        if not near:
            kept.append(candidate)
    return sorted(kept, key=lambda item: item.timestamp)
