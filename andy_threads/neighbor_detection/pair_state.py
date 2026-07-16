from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .centroid_pair import compute_centroid_evidence
from .common_mode import alternative_hypotheses_for
from .config import NeighborDetectionConfig
from .feeder_graph import PairDefinition, upstream_references_for
from .models import LocalChangeCandidate, NeighborManeuverCandidate, stable_hash
from .robust_step import StepDetectionConfig, detect_local_changes
from .synchronization import SynchronizedPair
from .transfer_score import balance_score, score_pair
from .upstream_reference import upstream_delta_at


@dataclass(frozen=True)
class PairAnalysisResult:
    local_changes: list[LocalChangeCandidate]
    candidates: list[NeighborManeuverCandidate]


def analyze_pair(
    all_df: pd.DataFrame,
    pair_def: PairDefinition,
    synced: SynchronizedPair,
    config: NeighborDetectionConfig,
    *,
    detector_version: str,
    source_alias: str,
    source_hash: str,
) -> PairAnalysisResult:
    if synced.data.empty:
        return PairAnalysisResult([], [])
    first, second = pair_def.first, pair_def.second
    equipment = _equipment_by_feeder(all_df, pair_def.se, (first, second))
    terminal = _terminal_for(all_df, pair_def.se, (first, second))
    step_config = StepDetectionConfig(
        pre_windows_hours=config.pre_windows_hours,
        post_windows_hours=config.post_windows_hours,
        min_persistence_samples=config.min_persistence_samples,
        robust_z_threshold=config.robust_z_threshold,
    )
    first_changes = detect_local_changes(
        synced.data,
        se=pair_def.se,
        feeder=first,
        equipment=equipment.get(first, ""),
        terminal=terminal,
        value_column=f"IB_{first}_raw",
        cadence_seconds=synced.cadence_seconds,
        config=step_config,
    )
    second_changes = detect_local_changes(
        synced.data,
        se=pair_def.se,
        feeder=second,
        equipment=equipment.get(second, ""),
        terminal=terminal,
        value_column=f"IB_{second}_raw",
        cadence_seconds=synced.cadence_seconds,
        config=step_config,
    )
    candidates: list[NeighborManeuverCandidate] = []
    local_changes = [*first_changes, *second_changes]
    pairs = _match_changes(first_changes, second_changes, synced.cadence_seconds, config.max_pair_time_offset_intervals)
    for first_change, second_change in pairs:
        event_peak = _event_peak(first_change, second_change)
        seconds_apart = _seconds_apart(first_change, second_change)
        quality = min(
            first_change.quality_score if first_change else 0.40,
            second_change.quality_score if second_change else 0.40,
            synced.coverage_common,
        )
        transfer_score, components, classification = score_pair(
            first_change,
            second_change,
            seconds_apart=seconds_apart,
            cadence_seconds=synced.cadence_seconds,
            max_offset_intervals=config.max_pair_time_offset_intervals,
            quality_score=quality,
            min_balance_for_transfer=config.min_balance_for_transfer,
        )
        centroid = compute_centroid_evidence(
            synced.data,
            first=first,
            second=second,
            event_peak=event_peak,
            pre_hours=(first_change or second_change).pre_window_hours,
            post_hours=(first_change or second_change).post_window_hours,
        )
        upstream_delta, upstream_stable, upstream_residues = upstream_delta_at(
            all_df,
            se=pair_def.se,
            upstream_references=upstream_references_for(config, pair_def.se),
            event_peak=event_peak,
            pre_hours=(first_change or second_change).pre_window_hours,
            post_hours=(first_change or second_change).post_window_hours,
        )
        deltas = {first: float(first_change.delta_i if first_change else 0.0), second: float(second_change.delta_i if second_change else 0.0)}
        zscores = {first: float(first_change.robust_z if first_change else 0.0), second: float(second_change.robust_z if second_change else 0.0)}
        feeder_from, feeder_to = _direction(first, second, deltas)
        balance = balance_score(deltas[first], deltas[second]) if first_change and second_change else 0.0
        residues = tuple(dict.fromkeys((*synced.residues, *upstream_residues)))
        hypotheses = alternative_hypotheses_for(classification, upstream_delta is not None and not upstream_stable, balance < config.min_balance_for_transfer)
        candidate_id = "nmc-" + stable_hash((source_hash, pair_def.se, first, second, event_peak, round(transfer_score, 6)))
        candidates.append(
            NeighborManeuverCandidate(
                candidate_id=candidate_id,
                detector_version=detector_version,
                config_hash=config.config_hash,
                source_alias=source_alias,
                source_hash=source_hash,
                SE=pair_def.se,
                feeder_from_candidate=feeder_from,
                feeder_to_candidate=feeder_to,
                feeder_pair=(first, second),
                equipment_by_feeder=equipment,
                terminal=terminal,
                variable="IB",
                event_start=(pd.Timestamp(event_peak) - pd.Timedelta(hours=(first_change or second_change).pre_window_hours)).isoformat(),
                event_peak=event_peak,
                event_end=(pd.Timestamp(event_peak) + pd.Timedelta(hours=(first_change or second_change).post_window_hours)).isoformat(),
                cadence_seconds=synced.cadence_seconds,
                pre_window=(first_change or second_change).pre_window_hours,
                post_window=(first_change or second_change).post_window_hours,
                delta_I_by_feeder=deltas,
                robust_z_by_feeder=zscores,
                centroid_before=centroid.centroid_before,
                centroid_after=centroid.centroid_after,
                centroid_delta_vector=centroid.centroid_delta_vector,
                centroid_delta_magnitude=centroid.centroid_delta_magnitude,
                threshold=centroid.centroid_threshold,
                opposite_direction=bool(deltas[first] * deltas[second] < 0),
                balance_score=balance,
                synchrony_score=components.get("synchrony_score", 0.0),
                persistence_score=components.get("persistence_score", 0.0),
                upstream_stability_hint=upstream_stable,
                quality_score=quality,
                transfer_score=transfer_score,
                classification=classification,
                alternative_hypotheses=hypotheses,
                residues=residues,
                configured_neighbor_pair=pair_def.configured_neighbor_pair,
                exploratory_pair=pair_def.exploratory_pair,
                upstream_delta=upstream_delta,
                score_components=components,
            )
        )
    return PairAnalysisResult(local_changes=local_changes, candidates=sorted(candidates, key=lambda item: item.transfer_score, reverse=True))


def _match_changes(
    first_changes: list[LocalChangeCandidate],
    second_changes: list[LocalChangeCandidate],
    cadence_seconds: float | None,
    max_offset_intervals: int,
) -> list[tuple[LocalChangeCandidate | None, LocalChangeCandidate | None]]:
    max_seconds = max(float(cadence_seconds or 3600.0), 1.0) * max(1, max_offset_intervals)
    used_second: set[str] = set()
    matched: list[tuple[LocalChangeCandidate | None, LocalChangeCandidate | None]] = []
    for first in first_changes:
        first_ts = pd.Timestamp(first.timestamp)
        options = [
            second
            for second in second_changes
            if second.candidate_id not in used_second and abs((first_ts - pd.Timestamp(second.timestamp)).total_seconds()) <= max_seconds
        ]
        if options:
            chosen = max(options, key=lambda item: item.robust_z)
            used_second.add(chosen.candidate_id)
            matched.append((first, chosen))
        else:
            matched.append((first, None))
    for second in second_changes:
        if second.candidate_id not in used_second:
            matched.append((None, second))
    return matched


def _event_peak(first: LocalChangeCandidate | None, second: LocalChangeCandidate | None) -> str:
    if first is not None and second is not None:
        return min((first, second), key=lambda item: item.timestamp).timestamp
    return (first or second).timestamp


def _seconds_apart(first: LocalChangeCandidate | None, second: LocalChangeCandidate | None) -> float:
    if first is None or second is None:
        return 0.0
    return float((pd.Timestamp(first.timestamp) - pd.Timestamp(second.timestamp)).total_seconds())


def _direction(first: str, second: str, deltas: dict[str, float]) -> tuple[str | None, str | None]:
    if deltas[first] < 0 < deltas[second]:
        return first, second
    if deltas[second] < 0 < deltas[first]:
        return second, first
    return None, None


def _equipment_by_feeder(df: pd.DataFrame, se: str, feeders: tuple[str, str]) -> dict[str, str]:
    output: dict[str, str] = {}
    for feeder in feeders:
        part = df[(df["se"] == se) & (df["feeder"] == feeder)]
        output[feeder] = str(part["equipment"].dropna().iloc[0]) if not part.empty else ""
    return output


def _terminal_for(df: pd.DataFrame, se: str, feeders: tuple[str, str]) -> str:
    part = df[(df["se"] == se) & (df["feeder"].isin(feeders))]
    return str(part["terminal"].dropna().iloc[0]) if not part.empty else ""
