from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


CURRENT_VARIABLES = frozenset({"IA", "IB", "IC"})


class NeighborClassification(str, Enum):
    LOAD_TRANSFER_CANDIDATE = "LOAD_TRANSFER_CANDIDATE"
    COMMON_MODE_EVENT_CANDIDATE = "COMMON_MODE_EVENT_CANDIDATE"
    LOCAL_FEEDER_EVENT_CANDIDATE = "LOCAL_FEEDER_EVENT_CANDIDATE"
    DATA_QUALITY_CANDIDATE = "DATA_QUALITY_CANDIDATE"
    EXPLORATORY_PAIR_CANDIDATE = "EXPLORATORY_PAIR_CANDIDATE"


class ReviewStatus(str, Enum):
    PENDING_HUMAN_REVIEW = "PENDING_HUMAN_REVIEW"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    SCADA_CONFIRMED = "SCADA_CONFIRMED"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class FeederKey:
    se: str
    feeder: str
    equipment: str
    terminal: str
    variable: str = "IB"

    @property
    def canonical(self) -> str:
        return "|".join((self.se, self.feeder, self.equipment, self.terminal, self.variable))


@dataclass(frozen=True)
class FeederProfile:
    source_alias: str
    source_hash: str
    key: str
    se: str
    feeder: str
    equipment: str
    terminal: str
    variable: str
    rows: int
    period_start: str | None
    period_end: str | None
    cadence_seconds: float | None
    gap_count: int
    duplicate_count: int
    missing_count: int
    constant_series: bool


@dataclass(frozen=True)
class CadenceReport:
    cadence_seconds: float | None
    gap_count: int
    duplicate_count: int
    coverage_start: str | None
    coverage_end: str | None
    continuous_segments: int


@dataclass(frozen=True)
class LocalChangeCandidate:
    candidate_id: str
    se: str
    feeder: str
    equipment: str
    terminal: str
    timestamp: str
    pre_window_hours: float
    post_window_hours: float
    delta_i: float
    delta_relative: float
    robust_z: float
    pre_median: float
    post_median: float
    pre_stability: float
    post_stability: float
    persistence_score: float
    quality_score: float
    gap_proximity: bool
    residues: tuple[str, ...] = ()


@dataclass(frozen=True)
class CentroidEvidence:
    centroid_before: dict[str, float]
    centroid_after: dict[str, float]
    centroid_delta_vector: dict[str, float]
    centroid_delta_magnitude: float
    centroid_threshold: float
    interpretation: str


@dataclass(frozen=True)
class NeighborManeuverCandidate:
    candidate_id: str
    detector_version: str
    config_hash: str
    source_alias: str
    source_hash: str
    SE: str
    feeder_from_candidate: str | None
    feeder_to_candidate: str | None
    feeder_pair: tuple[str, str]
    equipment_by_feeder: dict[str, str]
    terminal: str
    variable: str
    event_start: str
    event_peak: str
    event_end: str
    cadence_seconds: float | None
    pre_window: float
    post_window: float
    delta_I_by_feeder: dict[str, float]
    robust_z_by_feeder: dict[str, float]
    centroid_before: dict[str, float]
    centroid_after: dict[str, float]
    centroid_delta_vector: dict[str, float]
    centroid_delta_magnitude: float
    threshold: float
    opposite_direction: bool
    balance_score: float
    synchrony_score: float
    persistence_score: float
    upstream_stability_hint: bool
    quality_score: float
    transfer_score: float
    classification: NeighborClassification | str
    alternative_hypotheses: tuple[str, ...] = ()
    residues: tuple[str, ...] = ()
    human_validation_required: bool = True
    review_status: ReviewStatus | str = ReviewStatus.PENDING_HUMAN_REVIEW
    training_use: bool = False
    configured_neighbor_pair: bool = False
    exploratory_pair: bool = False
    upstream_delta: float | None = None
    score_components: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "classification", NeighborClassification(self.classification))
        object.__setattr__(self, "review_status", ReviewStatus(self.review_status))
        variable = str(self.variable or "").strip().upper()
        if variable not in CURRENT_VARIABLES:
            raise ValueError("neighbor_detector_uses_only_current_variables")
        object.__setattr__(self, "variable", variable)
        if not self.human_validation_required:
            raise ValueError("neighbor_candidate_requires_human_validation")
        if self.training_use:
            raise ValueError("neighbor_candidate_training_use_must_default_false")
        if len(self.feeder_pair) != 2 or self.feeder_pair[0] == self.feeder_pair[1]:
            raise ValueError("neighbor_candidate_requires_two_distinct_feeders")
        if not 0.0 <= float(self.transfer_score) <= 1.0:
            raise ValueError("transfer_score_out_of_range")


@dataclass(frozen=True)
class NeighborhoodEventEpisode:
    episode_id: str
    SE: str
    event_start: str
    event_peak: str
    event_end: str
    feeders_increasing: tuple[str, ...]
    feeders_decreasing: tuple[str, ...]
    feeder_deltas: dict[str, float]
    pair_candidates: tuple[str, ...]
    upstream_delta: float | None
    net_neighborhood_delta: float
    transfer_balance: float
    centroid_evidence: dict[str, Any]
    quality: float
    alternative_hypotheses: tuple[str, ...]
    review_status: ReviewStatus | str = ReviewStatus.PENDING_HUMAN_REVIEW

    def __post_init__(self) -> None:
        object.__setattr__(self, "review_status", ReviewStatus(self.review_status))
        if self.review_status != ReviewStatus.PENDING_HUMAN_REVIEW:
            raise ValueError("episode_must_start_pending_human_review")


@dataclass(frozen=True)
class HumanNeighborReview:
    reviewer: str
    timestamp: str
    confidence: float
    reason: str
    evidence_type: str
    selected_feeders: tuple[str, ...]
    notes: str
    verdict: str
    training_use: bool = False

    def __post_init__(self) -> None:
        if not self.reviewer.strip():
            raise ValueError("reviewer_required")
        if not self.timestamp.strip():
            raise ValueError("review_timestamp_required")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("review_confidence_out_of_range")
        if not self.selected_feeders:
            raise ValueError("review_selected_feeders_required")
        if self.training_use:
            raise ValueError("training_use_disabled_in_lab")


def to_plain_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_plain_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_plain_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_plain_dict(item) for item in value]
    return value


def stable_hash(payload: Any, length: int = 16) -> str:
    encoded = json.dumps(to_plain_dict(payload), sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:length]
