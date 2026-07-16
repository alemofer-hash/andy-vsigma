from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .config import DETECTOR_VERSION, NeighborDetectionConfig
from .feeder_graph import build_pair_definitions
from .models import NeighborManeuverCandidate, to_plain_dict
from .neighborhood_fusion import fuse_candidates
from .occurrence_adapter import episode_to_thread_bundle
from .pair_state import analyze_pair
from .reporting import write_blind_run_report, write_human_review_queue, write_json, write_table
from .synchronization import synchronize_pair


@dataclass(frozen=True)
class RunnerResult:
    run_dir: Path
    manifests: list[dict[str, Any]]
    candidates: list[NeighborManeuverCandidate]
    episode_count: int
    warnings: list[str]


def run_neighbor_detection(
    *,
    inputs: list[Path],
    config: NeighborDetectionConfig,
    output_root: Path,
    all_pairs_exploratory: bool = False,
    blind_run: bool = False,
    generate_thread_occurrences: bool = False,
    generate_ui_runtime: bool = False,
    profile_only: bool = False,
) -> RunnerResult:
    from .workbook_intake import read_workbook_ib

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    frames: list[pd.DataFrame] = []
    manifests: list[dict[str, Any]] = []
    profiles = []
    for input_path in inputs:
        frame, manifest, feeder_profiles = read_workbook_ib(input_path)
        frames.append(frame)
        manifests.append(manifest)
        profiles.extend(feeder_profiles)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    write_json(run_dir / "input_manifest.json", manifests)
    write_json(run_dir / "feeder_profiles.json", [to_plain_dict(item) for item in profiles])
    if profile_only:
        return RunnerResult(run_dir, manifests, [], 0, [])
    pair_defs, warnings = build_pair_definitions(df, config, all_pairs_exploratory=all_pairs_exploratory)
    graph = {
        "config_hash": config.config_hash,
        "all_pairs_exploratory": all_pairs_exploratory,
        "pairs": [to_plain_dict(item) for item in pair_defs],
        "warnings": warnings,
    }
    write_json(run_dir / "neighbor_graph.json", graph)
    all_local_changes = []
    candidates: list[NeighborManeuverCandidate] = []
    cadence_rows = []
    gap_rows = []
    pair_score_rows = []
    centroid_rows = []
    for pair_def in pair_defs:
        synced = synchronize_pair(df, pair_def.se, pair_def.first, pair_def.second, config.min_common_coverage)
        cadence_rows.append(
            {
                "se": pair_def.se,
                "first": pair_def.first,
                "second": pair_def.second,
                "cadence_seconds": synced.cadence_seconds,
                "coverage_common": synced.coverage_common,
                "residues": ";".join(synced.residues),
            }
        )
        gap_rows.append({"se": pair_def.se, "pair": f"{pair_def.first}-{pair_def.second}", "residues": ";".join(synced.residues)})
        result = analyze_pair(
            df,
            pair_def,
            synced,
            config,
            detector_version=DETECTOR_VERSION,
            source_alias=";".join(sorted(set(df["source_alias"].dropna().astype(str)))) if not df.empty else "unknown",
            source_hash=config.config_hash,
        )
        all_local_changes.extend(result.local_changes)
        candidates.extend(result.candidates)
    candidates = sorted(candidates, key=lambda item: item.transfer_score, reverse=True)
    for candidate in candidates:
        pair_score_rows.append(_candidate_row(candidate))
        centroid_rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "se": candidate.SE,
                "pair": "-".join(candidate.feeder_pair),
                "event_peak": candidate.event_peak,
                "centroid_delta_magnitude": candidate.centroid_delta_magnitude,
                "centroid_threshold": candidate.threshold,
                "centroid_delta_vector": candidate.centroid_delta_vector,
            }
        )
    representative_cadence = _representative_cadence(candidates)
    episodes = fuse_candidates(candidates, cadence_seconds=representative_cadence)
    write_table(run_dir / "local_changes.parquet", [to_plain_dict(item) for item in all_local_changes])
    write_table(run_dir / "pair_scores.parquet", pair_score_rows)
    write_table(run_dir / "centroid_displacements.parquet", centroid_rows)
    write_table(run_dir / "candidate_windows.csv", pair_score_rows)
    write_table(run_dir / "event_episodes.csv", [to_plain_dict(item) for item in episodes])
    write_json(run_dir / "cadence_report.json", cadence_rows)
    write_json(run_dir / "gap_report.json", gap_rows)
    if generate_thread_occurrences:
        bundles = []
        for episode in episodes:
            linked = [candidate for candidate in candidates if candidate.candidate_id in episode.pair_candidates]
            bundles.append(episode_to_thread_bundle(episode, linked))
        write_json(run_dir / "threads_occurrences.json", bundles)
    else:
        write_json(run_dir / "threads_occurrences.json", [])
    write_human_review_queue(run_dir / "human_review_queue.md", episodes, candidates)
    if blind_run:
        write_blind_run_report(
            run_dir / "blind_run_report.md",
            manifests=manifests,
            graph=graph,
            candidates=candidates,
            episodes=episodes,
            warnings=warnings,
        )
    write_json(run_dir / "manual_event_comparison.json", {"manual_event_provided": False, "status": "AWAITING_REVEAL"})
    if generate_ui_runtime:
        _write_ui_runtime(run_dir, candidates, episodes)
    return RunnerResult(run_dir, manifests, candidates, len(episodes), warnings)


def _representative_cadence(candidates: list[NeighborManeuverCandidate]) -> float | None:
    values = [item.cadence_seconds for item in candidates if item.cadence_seconds]
    if not values:
        return None
    return float(sorted(values)[len(values) // 2])


def _candidate_row(candidate: NeighborManeuverCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "SE": candidate.SE,
        "feeder_pair": "-".join(candidate.feeder_pair),
        "feeder_from_candidate": candidate.feeder_from_candidate,
        "feeder_to_candidate": candidate.feeder_to_candidate,
        "event_peak": candidate.event_peak,
        "event_start": candidate.event_start,
        "event_end": candidate.event_end,
        "classification": candidate.classification.value,
        "delta_I_by_feeder": candidate.delta_I_by_feeder,
        "robust_z_by_feeder": candidate.robust_z_by_feeder,
        "balance_score": candidate.balance_score,
        "synchrony_score": candidate.synchrony_score,
        "persistence_score": candidate.persistence_score,
        "quality_score": candidate.quality_score,
        "transfer_score": candidate.transfer_score,
        "centroid_delta_magnitude": candidate.centroid_delta_magnitude,
        "upstream_delta": candidate.upstream_delta,
        "upstream_stability_hint": candidate.upstream_stability_hint,
        "configured_neighbor_pair": candidate.configured_neighbor_pair,
        "exploratory_pair": candidate.exploratory_pair,
        "review_status": candidate.review_status.value,
        "training_use": candidate.training_use,
    }


def _write_ui_runtime(run_dir: Path, candidates: list[NeighborManeuverCandidate], episodes: list[Any]) -> None:
    payload = {
        "data_class": "REAL_INPUT_LOCAL",
        "candidate_only": True,
        "human_validation_required": True,
        "training_use": False,
        "top_candidates": [_candidate_row(item) for item in candidates[:20]],
        "episodes": [to_plain_dict(item) for item in episodes],
    }
    write_json(run_dir / "ui_runtime.json", payload)
