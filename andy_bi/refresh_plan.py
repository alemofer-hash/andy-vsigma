from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .schema_version import ANDY_BI_REFRESH_PLAN_VERSION


def default_refresh_plan() -> dict[str, Any]:
    return {
        "schema": ANDY_BI_REFRESH_PLAN_VERSION,
        "real_gateway_configured": False,
        "publish_automatically": False,
        "refresh_modes": ["manual", "scheduled", "incremental"],
        "default_mode": "manual",
        "incremental_keys": ["lote_id", "source_id", "source_period_start", "source_period_end"],
        "retention": {
            "dataset_lotes": "policy_defined_by_data_owner",
            "logs_days": 90,
            "rollback_lotes": 2,
        },
        "stale_catalog_policy": {
            "detect_before_build": True,
            "block_publish_when_stale": True,
        },
    }


def write_default_refresh_plan(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(default_refresh_plan(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def load_refresh_plan(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("refresh_plan_root_must_be_object")
    return payload


def validate_refresh_plan(plan: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if plan.get("schema") != ANDY_BI_REFRESH_PLAN_VERSION:
        failures.append("schema_version_mismatch")
    if plan.get("real_gateway_configured") is not False:
        failures.append("example_must_not_enable_real_gateway")
    if plan.get("publish_automatically") is not False:
        failures.append("automatic_publish_must_be_false")
    if plan.get("default_mode") not in {"manual", "scheduled", "incremental"}:
        failures.append("invalid_default_refresh_mode")
    if not isinstance(plan.get("incremental_keys"), list) or not plan.get("incremental_keys"):
        failures.append("incremental_keys_required")
    return failures
