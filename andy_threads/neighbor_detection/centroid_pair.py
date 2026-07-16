from __future__ import annotations

import math

import pandas as pd

from .models import CentroidEvidence
from .preprocessing import EPSILON, robust_mad, robust_median


def compute_centroid_evidence(
    data: pd.DataFrame,
    *,
    first: str,
    second: str,
    event_peak: str,
    pre_hours: float,
    post_hours: float,
) -> CentroidEvidence:
    timestamp = pd.Timestamp(event_peak)
    pre = data[(data["timestamp"] >= timestamp - pd.Timedelta(hours=pre_hours)) & (data["timestamp"] < timestamp)]
    post = data[(data["timestamp"] >= timestamp) & (data["timestamp"] <= timestamp + pd.Timedelta(hours=post_hours))]
    left_col = f"IB_{first}_z"
    right_col = f"IB_{second}_z"
    before = {first: _mean_or_zero(pre[left_col]), second: _mean_or_zero(pre[right_col])}
    after = {first: _mean_or_zero(post[left_col]), second: _mean_or_zero(post[right_col])}
    vector = {first: after[first] - before[first], second: after[second] - before[second]}
    magnitude = math.sqrt(vector[first] ** 2 + vector[second] ** 2)
    threshold = _centroid_threshold(data, first=first, second=second)
    return CentroidEvidence(
        centroid_before=before,
        centroid_after=after,
        centroid_delta_vector=vector,
        centroid_delta_magnitude=float(magnitude),
        centroid_threshold=float(threshold),
        interpretation=_interpret_vector(vector[first], vector[second]),
    )


def _mean_or_zero(values: pd.Series) -> float:
    clean = values.dropna().astype(float)
    return float(clean.mean()) if not clean.empty else 0.0


def _centroid_threshold(data: pd.DataFrame, *, first: str, second: str) -> float:
    left = data[f"IB_{first}_z"].astype(float)
    right = data[f"IB_{second}_z"].astype(float)
    displacement = ((left.diff().fillna(0.0) ** 2) + (right.diff().fillna(0.0) ** 2)) ** 0.5
    return float(robust_median(displacement) + 2.5 * max(robust_mad(displacement), EPSILON))


def _interpret_vector(first_delta: float, second_delta: float) -> str:
    if first_delta >= 0 and second_delta >= 0:
        return "(+,+): common increase"
    if first_delta < 0 and second_delta < 0:
        return "(-,-): common decrease"
    if first_delta >= 0 and second_delta < 0:
        return "(+,-): transfer second_to_first"
    return "(-,+): transfer first_to_second"
