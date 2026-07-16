from __future__ import annotations

from .models import LocalChangeCandidate, NeighborClassification
from .preprocessing import EPSILON, clamp01


def balance_score(delta_first: float, delta_second: float) -> float:
    return clamp01(1.0 - abs(delta_first + delta_second) / (abs(delta_first) + abs(delta_second) + EPSILON))


def synchrony_score(seconds_apart: float, cadence_seconds: float | None, max_offset_intervals: int) -> float:
    cadence = max(float(cadence_seconds or 3600.0), 1.0)
    max_allowed = max(float(max_offset_intervals), 1.0) * cadence
    return clamp01(1.0 - abs(seconds_apart) / (max_allowed + EPSILON))


def classify_pair(
    first: LocalChangeCandidate | None,
    second: LocalChangeCandidate | None,
    *,
    quality_score: float,
    min_balance_for_transfer: float,
) -> NeighborClassification:
    if quality_score < 0.35:
        return NeighborClassification.DATA_QUALITY_CANDIDATE
    if first is not None and second is not None:
        same_direction = first.delta_i * second.delta_i > 0
        opposite = first.delta_i * second.delta_i < 0
        if opposite and balance_score(first.delta_i, second.delta_i) >= min_balance_for_transfer:
            return NeighborClassification.LOAD_TRANSFER_CANDIDATE
        if same_direction:
            return NeighborClassification.COMMON_MODE_EVENT_CANDIDATE
    return NeighborClassification.LOCAL_FEEDER_EVENT_CANDIDATE


def score_pair(
    first: LocalChangeCandidate | None,
    second: LocalChangeCandidate | None,
    *,
    seconds_apart: float,
    cadence_seconds: float | None,
    max_offset_intervals: int,
    quality_score: float,
    min_balance_for_transfer: float,
) -> tuple[float, dict[str, float], NeighborClassification]:
    if first is None and second is None:
        return 0.0, {}, NeighborClassification.DATA_QUALITY_CANDIDATE
    z_first = clamp01((first.robust_z if first else 0.0) / 8.0)
    z_second = clamp01((second.robust_z if second else 0.0) / 8.0)
    delta_first = first.delta_i if first else 0.0
    delta_second = second.delta_i if second else 0.0
    opposite = 1.0 if first and second and delta_first * delta_second < 0 else 0.0
    balance = balance_score(delta_first, delta_second) if first and second else 0.0
    sync = synchrony_score(seconds_apart, cadence_seconds, max_offset_intervals) if first and second else 0.0
    persistence = clamp01(((first.persistence_score if first else 0.0) + (second.persistence_score if second else 0.0)) / (2.0 if first and second else 1.0))
    quality = clamp01(quality_score)
    classification = classify_pair(first, second, quality_score=quality, min_balance_for_transfer=min_balance_for_transfer)
    score = (
        0.20 * min(z_first, z_second if second else z_first)
        + 0.20 * opposite
        + 0.20 * balance
        + 0.15 * sync
        + 0.15 * persistence
        + 0.10 * quality
    )
    if classification == NeighborClassification.COMMON_MODE_EVENT_CANDIDATE:
        score = 0.45 * max(z_first, z_second) + 0.25 * sync + 0.20 * persistence + 0.10 * quality
    if classification == NeighborClassification.LOCAL_FEEDER_EVENT_CANDIDATE:
        score = 0.60 * max(z_first, z_second) + 0.25 * persistence + 0.15 * quality
    components = {
        "robust_z_first": z_first,
        "robust_z_second": z_second,
        "opposite_direction": opposite,
        "balance_score": balance,
        "synchrony_score": sync,
        "persistence_score": persistence,
        "quality_score": quality,
    }
    return clamp01(score), components, classification
