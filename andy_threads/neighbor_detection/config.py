from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import stable_hash

DETECTOR_VERSION = "andy_threads_neighbor_ib_pair_v0.1"
FEATURE_FLAG = "ANDY_THREADS_NEIGHBOR_DETECTION_ENABLED"


@dataclass(frozen=True)
class SubstationNeighborhood:
    se: str
    neighbor_pairs: tuple[tuple[str, str], ...] = ()
    upstream_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class NeighborDetectionConfig:
    substations: dict[str, SubstationNeighborhood] = field(default_factory=dict)
    pre_windows_hours: tuple[float, ...] = (2.0, 4.0, 8.0)
    post_windows_hours: tuple[float, ...] = (2.0, 4.0, 8.0)
    min_persistence_samples: int = 2
    max_pair_time_offset_intervals: int = 1
    robust_z_threshold: float = 3.0
    min_balance_for_transfer: float = 0.55
    min_quality_score: float = 0.35
    min_common_coverage: float = 0.60
    paper_reproduction_mode: bool = False
    paper_window_samples: int = 200
    paper_overlap: float = 0.5

    @property
    def config_hash(self) -> str:
        payload = {
            "substations": {
                key: {
                    "neighbor_pairs": value.neighbor_pairs,
                    "upstream_references": value.upstream_references,
                }
                for key, value in sorted(self.substations.items())
            },
            "pre_windows_hours": self.pre_windows_hours,
            "post_windows_hours": self.post_windows_hours,
            "min_persistence_samples": self.min_persistence_samples,
            "max_pair_time_offset_intervals": self.max_pair_time_offset_intervals,
            "robust_z_threshold": self.robust_z_threshold,
            "min_balance_for_transfer": self.min_balance_for_transfer,
            "min_quality_score": self.min_quality_score,
            "min_common_coverage": self.min_common_coverage,
            "paper_reproduction_mode": self.paper_reproduction_mode,
        }
        return stable_hash(payload)


def is_neighbor_detection_enabled() -> bool:
    return str(os.environ.get(FEATURE_FLAG, "0")).strip().lower() in {"1", "true", "yes", "on"}


def load_neighborhood_config(path: str | Path | None) -> NeighborDetectionConfig:
    if path is None:
        return NeighborDetectionConfig()
    config_path = Path(path)
    if not config_path.exists():
        return NeighborDetectionConfig()
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    return config_from_payload(payload)


def config_from_payload(payload: dict[str, Any]) -> NeighborDetectionConfig:
    substations: dict[str, SubstationNeighborhood] = {}
    for raw_se, raw_config in dict(payload.get("substations") or {}).items():
        se = str(raw_se).strip().upper()
        pairs = tuple(
            tuple(str(item).strip().upper() for item in pair[:2])
            for pair in raw_config.get("neighbor_pairs", [])
            if len(pair) >= 2 and str(pair[0]).strip() and str(pair[1]).strip()
        )
        upstream = tuple(str(item).strip().upper() for item in raw_config.get("upstream_references", []) if str(item).strip())
        substations[se] = SubstationNeighborhood(se=se, neighbor_pairs=pairs, upstream_references=upstream)
    return NeighborDetectionConfig(
        substations=substations,
        pre_windows_hours=tuple(float(v) for v in payload.get("pre_windows_hours", (2, 4, 8))),
        post_windows_hours=tuple(float(v) for v in payload.get("post_windows_hours", (2, 4, 8))),
        min_persistence_samples=int(payload.get("min_persistence_samples", 2)),
        max_pair_time_offset_intervals=int(payload.get("max_pair_time_offset_intervals", 1)),
        robust_z_threshold=float(payload.get("robust_z_threshold", 3.0)),
        min_balance_for_transfer=float(payload.get("min_balance_for_transfer", 0.55)),
        min_quality_score=float(payload.get("min_quality_score", 0.35)),
        min_common_coverage=float(payload.get("min_common_coverage", 0.60)),
        paper_reproduction_mode=bool(payload.get("paper_reproduction_mode", False)),
        paper_window_samples=int(payload.get("paper_window_samples", 200)),
        paper_overlap=float(payload.get("paper_overlap", 0.5)),
    )


def with_cli_pair(config: NeighborDetectionConfig, pair_texts: list[str]) -> NeighborDetectionConfig:
    substations = dict(config.substations)
    for text in pair_texts:
        parts = [part.strip().upper() for part in text.split(":") if part.strip()]
        if len(parts) != 3:
            raise ValueError("pair_must_use_SE:FEEDER_A:FEEDER_B")
        se, first, second = parts
        current = substations.get(se, SubstationNeighborhood(se=se))
        pairs = tuple(dict.fromkeys((*current.neighbor_pairs, (first, second))))
        substations[se] = SubstationNeighborhood(se=se, neighbor_pairs=pairs, upstream_references=current.upstream_references)
    return NeighborDetectionConfig(
        substations=substations,
        pre_windows_hours=config.pre_windows_hours,
        post_windows_hours=config.post_windows_hours,
        min_persistence_samples=config.min_persistence_samples,
        max_pair_time_offset_intervals=config.max_pair_time_offset_intervals,
        robust_z_threshold=config.robust_z_threshold,
        min_balance_for_transfer=config.min_balance_for_transfer,
        min_quality_score=config.min_quality_score,
        min_common_coverage=config.min_common_coverage,
        paper_reproduction_mode=config.paper_reproduction_mode,
        paper_window_samples=config.paper_window_samples,
        paper_overlap=config.paper_overlap,
    )
