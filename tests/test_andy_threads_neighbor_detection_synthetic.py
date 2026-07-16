from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from andy_threads.neighbor_detection.config import NeighborDetectionConfig, SubstationNeighborhood
from andy_threads.neighbor_detection.feeder_graph import PairDefinition, build_pair_definitions
from andy_threads.neighbor_detection.human_review import validate_human_review
from andy_threads.neighbor_detection.neighborhood_fusion import fuse_candidates
from andy_threads.neighbor_detection.occurrence_adapter import episode_to_thread_bundle
from andy_threads.neighbor_detection.pair_state import analyze_pair
from andy_threads.neighbor_detection.synchronization import synchronize_pair


def _frame(
    *,
    al3_delta: float = -40.0,
    al4_delta: float = 38.0,
    tr_delta: float | None = None,
    gradual: bool = False,
    spike: bool = False,
    gap: bool = False,
    duplicate: bool = False,
    third_feeder: bool = False,
) -> pd.DataFrame:
    rows = []
    timestamps = pd.date_range("2026-01-01 00:00:00", periods=32, freq="h")
    if gap:
        timestamps = timestamps.delete([14, 15, 16])
    for feeder, equipment, base, delta in [
        ("AL3", "[52-3]", 100.0, al3_delta),
        ("AL4", "[52-2]", 80.0, al4_delta),
        ("TR-1", "[TR-1]", 180.0, tr_delta if tr_delta is not None else 0.0),
    ]:
        for index, timestamp in enumerate(timestamps):
            active_delta = 0.0
            if spike and index == 12:
                active_delta = delta
            elif spike:
                active_delta = 0.0
            elif gradual and index >= 12:
                active_delta = delta * min(1.0, (index - 11) / 10.0)
            elif index >= 12:
                active_delta = delta
            rows.append(_row(timestamp, feeder, equipment, base + active_delta))
            if duplicate and feeder == "AL3" and index == 12:
                rows.append(_row(timestamp, feeder, equipment, base + active_delta))
    if third_feeder:
        for index, timestamp in enumerate(timestamps):
            delta = 18.0 if index >= 12 else 0.0
            rows.append(_row(timestamp, "AL5", "[52-1]", 55.0 + delta))
    return pd.DataFrame(rows)


def _row(timestamp: pd.Timestamp, feeder: str, equipment: str, value: float) -> dict[str, object]:
    return {
        "source_alias": "synthetic.xlsx",
        "source_hash": "synthetic",
        "timestamp": timestamp,
        "key": f"MOS|{feeder}|{equipment}|Terminal1|IB",
        "se": "MOS",
        "feeder": feeder,
        "equipment": equipment,
        "terminal": "Terminal1",
        "variable": "IB",
        "value": value,
        "is_feeder": feeder.startswith("AL"),
    }


def _config() -> NeighborDetectionConfig:
    return NeighborDetectionConfig(
        substations={"MOS": SubstationNeighborhood(se="MOS", neighbor_pairs=(("AL3", "AL4"),), upstream_references=("TR-1",))},
        pre_windows_hours=(4,),
        post_windows_hours=(4,),
        robust_z_threshold=2.0,
        min_persistence_samples=2,
        max_pair_time_offset_intervals=1,
        min_balance_for_transfer=0.55,
    )


def _analyze(df: pd.DataFrame, pair: tuple[str, str] = ("AL3", "AL4")):
    config = _config()
    synced = synchronize_pair(df, "MOS", pair[0], pair[1], config.min_common_coverage)
    result = analyze_pair(
        df,
        PairDefinition("MOS", pair[0], pair[1], configured_neighbor_pair=True),
        synced,
        config,
        detector_version="test",
        source_alias="synthetic.xlsx",
        source_hash="synthetic",
    )
    return result


def test_balanced_opposite_steps_generate_load_transfer_candidate() -> None:
    result = _analyze(_frame(al3_delta=-40, al4_delta=38, tr_delta=0))
    candidate = result.candidates[0]
    assert candidate.classification.value == "LOAD_TRANSFER_CANDIDATE"
    assert candidate.feeder_from_candidate == "AL3"
    assert candidate.feeder_to_candidate == "AL4"
    assert candidate.balance_score > 0.90
    assert candidate.upstream_stability_hint is True
    assert candidate.training_use is False


def test_same_direction_steps_generate_common_mode_candidate() -> None:
    result = _analyze(_frame(al3_delta=30, al4_delta=28, tr_delta=30))
    assert result.candidates[0].classification.value == "COMMON_MODE_EVENT_CANDIDATE"
    assert "substation_common_mode_change" in result.candidates[0].alternative_hypotheses


def test_single_feeder_step_generates_local_event_candidate() -> None:
    result = _analyze(_frame(al3_delta=-35, al4_delta=0))
    assert result.candidates[0].classification.value == "LOCAL_FEEDER_EVENT_CANDIDATE"


def test_low_balance_opposite_step_is_not_strong_transfer() -> None:
    result = _analyze(_frame(al3_delta=-40, al4_delta=5))
    candidate = result.candidates[0]
    assert candidate.classification.value != "LOAD_TRANSFER_CANDIDATE"
    assert candidate.balance_score < 0.55
    assert "transfer_balance_low" in candidate.alternative_hypotheses


def test_gradual_event_scores_lower_than_step_event() -> None:
    step = _analyze(_frame(al3_delta=-40, al4_delta=38)).candidates[0]
    gradual = _analyze(_frame(al3_delta=-40, al4_delta=38, gradual=True)).candidates
    assert not gradual or gradual[0].transfer_score < step.transfer_score


def test_single_sample_spike_does_not_pass_persistence() -> None:
    result = _analyze(_frame(al3_delta=-40, al4_delta=38, spike=True))
    assert not result.candidates


def test_gap_does_not_create_candidate_across_gap() -> None:
    result = _analyze(_frame(al3_delta=-40, al4_delta=38, gap=True))
    assert not result.candidates or all("source_gaps_present" in item.residues for item in result.candidates)


def test_duplicate_timestamp_is_collapsed_without_duplicate_event() -> None:
    result = _analyze(_frame(al3_delta=-40, al4_delta=38, duplicate=True))
    ids = [item.candidate_id for item in result.candidates]
    assert len(ids) == len(set(ids))


def test_upstream_stability_hint_and_common_residue() -> None:
    stable = _analyze(_frame(al3_delta=-40, al4_delta=38, tr_delta=0)).candidates[0]
    moved = _analyze(_frame(al3_delta=-40, al4_delta=38, tr_delta=50)).candidates[0]
    assert stable.upstream_stability_hint is True
    assert moved.upstream_stability_hint is False
    assert "possible_upstream_or_common_mode_event" in moved.alternative_hypotheses


def test_three_feeder_candidates_fuse_into_one_episode() -> None:
    df = _frame(al3_delta=-40, al4_delta=38, third_feeder=True)
    first = _analyze(df, ("AL3", "AL4")).candidates
    second = _analyze(df, ("AL3", "AL5")).candidates
    episodes = fuse_candidates([*first, *second], cadence_seconds=3600)
    assert len(episodes) == 1
    assert "AL3" in episodes[0].feeders_decreasing
    assert set(episodes[0].pair_candidates)


def test_unconfigured_pair_is_exploratory_only() -> None:
    config = _config()
    pairs, warnings = build_pair_definitions(_frame(third_feeder=True), config, all_pairs_exploratory=True)
    exploratory = [pair for pair in pairs if pair.exploratory_pair and pair.pair != ("AL3", "AL4")]
    assert exploratory
    assert all(not pair.configured_neighbor_pair for pair in exploratory)
    assert not warnings


def test_occurrence_bundle_stays_candidate_only_and_human_review_required() -> None:
    candidate = _analyze(_frame()).candidates[0]
    episode = fuse_candidates([candidate], cadence_seconds=3600)[0]
    bundle = episode_to_thread_bundle(episode, [candidate])
    assert bundle["dispatched"] is False
    assert bundle["notification_intent"]["real_provider_enabled"] is False
    assert bundle["occurrence"]["status"] == "WAITING_HUMAN_FEEDBACK"
    assert bundle["event_candidates"][0]["decision_applied"] is False


def test_human_review_requires_all_required_fields_and_training_off() -> None:
    review = validate_human_review(
        {
            "verdict": "TRANSFERENCIA_CONFIRMADA",
            "reviewer": "engenharia",
            "timestamp": "2026-01-01T12:00:00Z",
            "confidence": 0.8,
            "reason": "SCADA confirma",
            "evidence_type": "SCADA",
            "selected_feeders": ["AL3", "AL4"],
            "notes": "ok",
            "training_use": False,
        }
    )
    assert review.training_use is False
    with pytest.raises(ValueError):
        validate_human_review(
            {
                "verdict": "TRANSFERENCIA_CONFIRMADA",
                "reviewer": "engenharia",
                "timestamp": "2026-01-01T12:00:00Z",
                "confidence": 0.8,
                "reason": "SCADA confirma",
                "evidence_type": "SCADA",
                "selected_feeders": ["AL3", "AL4"],
                "notes": "ok",
                "training_use": True,
            }
        )


def test_runner_script_exists() -> None:
    assert Path("scripts/run_andy_threads_neighbor_detection.py").exists()
