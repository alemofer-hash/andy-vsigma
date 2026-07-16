from __future__ import annotations

from collections import defaultdict

import pandas as pd

from .models import NeighborManeuverCandidate, NeighborhoodEventEpisode, stable_hash


def fuse_candidates(
    candidates: list[NeighborManeuverCandidate],
    *,
    cadence_seconds: float | None,
) -> list[NeighborhoodEventEpisode]:
    if not candidates:
        return []
    max_gap = max(float(cadence_seconds or 3600.0) * 2.0, 3600.0)
    ordered = sorted(candidates, key=lambda item: (item.SE, item.event_peak))
    groups: list[list[NeighborManeuverCandidate]] = []
    for candidate in ordered:
        if not groups:
            groups.append([candidate])
            continue
        last = groups[-1][-1]
        close = candidate.SE == last.SE and abs((pd.Timestamp(candidate.event_peak) - pd.Timestamp(last.event_peak)).total_seconds()) <= max_gap
        if close:
            groups[-1].append(candidate)
        else:
            groups.append([candidate])
    return [_episode_from_group(group) for group in groups]


def _episode_from_group(group: list[NeighborManeuverCandidate]) -> NeighborhoodEventEpisode:
    first = group[0]
    feeder_deltas: dict[str, float] = defaultdict(float)
    for candidate in group:
        for feeder, delta in candidate.delta_I_by_feeder.items():
            feeder_deltas[feeder] += float(delta)
    increasing = tuple(sorted(feeder for feeder, delta in feeder_deltas.items() if delta > 0))
    decreasing = tuple(sorted(feeder for feeder, delta in feeder_deltas.items() if delta < 0))
    peaks = [pd.Timestamp(item.event_peak) for item in group]
    starts = [pd.Timestamp(item.event_start) for item in group]
    ends = [pd.Timestamp(item.event_end) for item in group]
    quality = min(item.quality_score for item in group)
    balance = max(item.balance_score for item in group)
    centroid = {
        item.candidate_id: {
            "delta_vector": item.centroid_delta_vector,
            "magnitude": item.centroid_delta_magnitude,
            "threshold": item.threshold,
        }
        for item in group
    }
    upstream_values = [item.upstream_delta for item in group if item.upstream_delta is not None]
    upstream_delta = float(sum(upstream_values) / len(upstream_values)) if upstream_values else None
    alternatives = tuple(dict.fromkeys(h for item in group for h in item.alternative_hypotheses))
    episode_id = "episode-" + stable_hash((first.SE, [item.candidate_id for item in group]))
    return NeighborhoodEventEpisode(
        episode_id=episode_id,
        SE=first.SE,
        event_start=min(starts).isoformat(),
        event_peak=min(peaks).isoformat(),
        event_end=max(ends).isoformat(),
        feeders_increasing=increasing,
        feeders_decreasing=decreasing,
        feeder_deltas=dict(feeder_deltas),
        pair_candidates=tuple(item.candidate_id for item in group),
        upstream_delta=upstream_delta,
        net_neighborhood_delta=float(sum(feeder_deltas.values())),
        transfer_balance=float(balance),
        centroid_evidence=centroid,
        quality=float(quality),
        alternative_hypotheses=alternatives,
    )
