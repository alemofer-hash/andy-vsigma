from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


DEFAULT_CHRONOS_PROFILE = Path("work/andy_chronos_elipse_lab/profiles/elipse_final_cadence_refined.json")


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[1]


def default_chronos_profile_path(*, repo_root: Path | None = None) -> Path:
    root = repo_root or repo_root_from_here()
    return (root / DEFAULT_CHRONOS_PROFILE).resolve()


def load_chronos_profile(profile_path: str | Path | None = None, *, repo_root: Path | None = None) -> dict[str, Any]:
    path = Path(profile_path).expanduser() if profile_path else default_chronos_profile_path(repo_root=repo_root)
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Chronos profile not found: {path}")
    if not path.is_file():
        raise ValueError(f"Chronos profile path is not a file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Chronos profile must be a JSON object.")
    return data


def chronos_profile_review_payload(
    profile: Mapping[str, Any],
    *,
    profile_path: str | Path,
) -> dict[str, Any]:
    schema = _mapping(profile.get("schema"))
    metadata = _mapping(profile.get("metadata"))
    scan_stats = _mapping(metadata.get("scan_stats"))
    label_distribution = _mapping(profile.get("label_distribution"))
    reading_cadences = _list_of_mappings(profile.get("reading_cadences"))
    alternative_templates = _list_of_mappings(schema.get("alternative_templates"))
    warnings = [str(item) for item in _list(profile.get("warnings") or schema.get("warnings"))]
    unknown_count = int(label_distribution.get("UNKNOWN", 0) or 0)
    model_name = str(profile.get("model_name", "") or "")

    return {
        "status": "experimental_review_required",
        "experimental": True,
        "approved_for_operational_use": False,
        "can_drive_filters_export": False,
        "profile_path": str(Path(profile_path).resolve()),
        "source": {
            "root": str(profile.get("root", "") or ""),
            "measurement_files_scanned": int(metadata.get("measurement_files_scanned", 0) or 0),
            "paths_visited": int(scan_stats.get("paths_visited", 0) or 0),
            "stopped_reason": str(scan_stats.get("stopped_reason", "") or ""),
        },
        "model": {
            "name": model_name,
            "recommended": model_name == "rules",
            "confidence": float(profile.get("confidence", 0.0) or 0.0),
            "schema_confidence": float(schema.get("confidence", 0.0) or 0.0),
        },
        "schema": {
            "name": str(schema.get("name", "") or ""),
            "path_template": str(schema.get("path_template", "") or ""),
            "expanded_template": str(schema.get("expanded_template", "") or ""),
            "date_granularity": str(schema.get("date_granularity", "") or ""),
            "terminal_file_label": str(schema.get("terminal_file_label", "") or ""),
            "date_segments": dict(_mapping(schema.get("date_segments"))),
            "entity_segments": dict(_mapping(schema.get("entity_segments"))),
            "cadence_segments": dict(_mapping(schema.get("cadence_segments"))),
            "temporal_compositions": dict(_mapping(schema.get("temporal_compositions"))),
        },
        "reading_cadences": [_safe_cadence(item) for item in reading_cadences],
        "label_distribution": dict(label_distribution),
        "template_review": [
            {
                "template": str(item.get("template", "") or ""),
                "expanded_template": str(item.get("expanded_template", "") or ""),
                "count": int(item.get("count", 0) or 0),
                "confidence": float(item.get("confidence", 0.0) or 0.0),
            }
            for item in alternative_templates
        ],
        "review": {
            "requires_human_acceptance": True,
            "unknown_segments": unknown_count,
            "residuals": _residuals(unknown_count, alternative_templates, warnings),
            "next_action": "Revisar o schema Chronos antes de usar em filtros ou exportacao.",
        },
        "safety": {
            "opens_measurement_files": False,
            "copies_measurement_files": False,
            "modifies_source_tree": False,
            "integrates_into_operational_filters": False,
            "integrates_into_export": False,
        },
        "warnings": warnings,
    }


def load_chronos_profile_review(
    profile_path: str | Path | None = None,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    resolved = Path(profile_path).expanduser().resolve() if profile_path else default_chronos_profile_path(repo_root=repo_root)
    profile = load_chronos_profile(resolved)
    return chronos_profile_review_payload(profile, profile_path=resolved)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _list_of_mappings(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in _list(value) if isinstance(item, Mapping)]


def _safe_cadence(item: Mapping[str, Any]) -> dict[str, Any]:
    cadence_type = str(item.get("type", "") or "")
    out: dict[str, Any] = {
        "type": cadence_type,
        "count": int(item.get("count", 0) or 0),
        "confidence": float(item.get("confidence", 0.0) or 0.0),
        "source_segment_examples": [str(value) for value in _list(item.get("source_segment_examples"))[:5]],
    }
    if cadence_type == "INTERVAL_MINUTES":
        out["minutes"] = int(item.get("minutes", 0) or 0)
    if cadence_type == "INTERVAL_HOURLY":
        out["hours"] = int(item.get("hours", 0) or 0)
    return out


def _residuals(
    unknown_count: int,
    alternative_templates: list[Mapping[str, Any]],
    warnings: list[str],
) -> list[str]:
    residuals: list[str] = []
    if unknown_count:
        residuals.append(f"{unknown_count} segmentos UNKNOWN ainda precisam de revisao humana.")
    if len(alternative_templates) > 1:
        residuals.append(f"{len(alternative_templates)} templates alternativos detectados.")
    for warning in warnings:
        if warning and warning not in residuals:
            residuals.append(warning)
    return residuals
