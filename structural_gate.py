from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from k_supervisor import DEFAULT_HBIT_NAMES, KSupervisor, KSupervisorOutput
from source_guardian import (
    FileFingerprint,
    classify_layout,
    collect_generated_months,
    compute_drift_metrics,
    fingerprint_file,
    get_default_profile,
    reconcile_generated_months,
)

GUARDIAN_AUDIT_FILENAME = "source_guardian_audit.jsonl"
GUARDIAN_METADATA_KEY = "source_guardian"


def evaluate_source_candidate(
    file_path: str | Path,
    *,
    supervisor: KSupervisor | None = None,
) -> dict[str, Any]:
    file_path = Path(file_path).resolve()
    fingerprint = fingerprint_file(file_path)
    profile = get_default_profile()
    metrics = compute_drift_metrics(fingerprint, profile)
    hbits = build_hbits(fingerprint, metrics)
    supervisor_engine = supervisor or KSupervisor()
    supervisor_output = supervisor_engine.forward(hbits, m=metrics.total)
    classification = classify_layout(metrics)
    decision = _decide_pre_promotion(fingerprint, metrics, classification, supervisor_output)
    return {
        "fingerprint": fingerprint,
        "metrics": metrics,
        "classification": classification,
        "hbits": dict(hbits),
        "supervisor": supervisor_output,
        "decision": decision,
    }


def build_hbits(fingerprint: FileFingerprint, metrics: Any) -> dict[str, float]:
    column_delta = abs(len(fingerprint.normalized_columns) - len(get_default_profile().required_fields))
    file_size_mb = fingerprint.file_size_bytes / (1024 * 1024) if fingerprint.file_size_bytes else 0.0
    month_gap = 1.0 if not fingerprint.discovered_months else 0.0
    values = {
        "header_variance": float(metrics.m_header),
        "null_ratio": float(fingerprint.null_ratio_estimate),
        "file_size_delta": float(_clamp01(file_size_mb / 25.0)),
        "timestamp_delta_rate": float(metrics.m_date),
        "column_count_delta": float(_clamp01(column_delta / 10.0)),
        "sheet_count_delta": float(_clamp01(max(len(fingerprint.candidate_sheet_names) - 1, 0) / 3.0)),
        "semantic_mismatch": float(metrics.m_semantic),
        "month_coverage_gap": float(month_gap),
    }
    return {name: float(values.get(name, 0.0)) for name in DEFAULT_HBIT_NAMES}


def finalize_source_promotion(
    assessment: Mapping[str, Any],
    *,
    canon_df: pd.DataFrame,
    long_df: pd.DataFrame,
) -> dict[str, Any]:
    fingerprint = assessment["fingerprint"]
    pre_decision = dict(assessment["decision"])
    reconciliation = reconcile_generated_months(fingerprint, canon_df, long_df)
    final_decision = dict(pre_decision)

    if reconciliation.missing_in_canon or reconciliation.missing_in_long:
        final_decision["verdict"] = "restructure"
        final_decision["severity"] = "high"
        final_decision["reasons"] = list(final_decision.get("reasons", [])) + list(reconciliation.reasons)
        final_decision["action"] = "block_promotion_missing_generated_months"
    elif final_decision["verdict"] == "review":
        final_decision["reasons"] = list(final_decision.get("reasons", [])) + list(reconciliation.reasons)

    canon_months, long_months = collect_generated_months(canon_df, long_df)
    return {
        "reconciliation": reconciliation,
        "decision": final_decision,
        "canon_months": canon_months,
        "long_months": long_months,
    }


def collect_source_months(results: Mapping[str, Mapping[str, Any]]) -> list[str]:
    months: set[str] = set()
    for payload in results.values():
        fingerprint = payload.get("fingerprint")
        if isinstance(fingerprint, FileFingerprint):
            months.update(fingerprint.discovered_months)
        elif isinstance(fingerprint, dict):
            months.update(str(v) for v in fingerprint.get("discovered_months", []))
    return sorted(months)


def build_run_summary(
    *,
    file_results: Mapping[str, Mapping[str, Any]],
    indexed_months_after: list[str],
) -> dict[str, Any]:
    source_months = collect_source_months(file_results)
    indexed_set = set(indexed_months_after)
    source_set = set(source_months)
    missing_after_run = sorted(source_set - indexed_set)
    verdict_counts: dict[str, int] = {}
    for payload in file_results.values():
        verdict = str((payload.get("decision") or {}).get("verdict", "")).strip() or "unknown"
        verdict_counts[verdict] = int(verdict_counts.get(verdict, 0)) + 1
    return {
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_months": source_months,
        "indexed_months_after": list(indexed_months_after),
        "missing_after_run": missing_after_run,
        "verdict_counts": verdict_counts,
        "status": "mismatch" if missing_after_run else "ok",
    }


def append_guardian_audit_event(
    work_root: str | Path,
    payload: Mapping[str, Any],
) -> Path:
    lake_root = (Path(work_root).resolve() / "ANDYS_LAKE").resolve()
    lake_root.mkdir(parents=True, exist_ok=True)
    audit_path = (lake_root / GUARDIAN_AUDIT_FILENAME).resolve()
    event = dict(payload)
    event.setdefault("ts", dt.datetime.now(dt.timezone.utc).isoformat())
    line = json.dumps(_json_safe(event), ensure_ascii=False, sort_keys=True)
    with open(audit_path, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return audit_path


def summarize_for_manifest(
    *,
    assessment: Mapping[str, Any],
    finalization: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    fingerprint = assessment["fingerprint"]
    metrics = assessment["metrics"]
    supervisor_output: KSupervisorOutput = assessment["supervisor"]
    out = {
        "fingerprint": fingerprint.to_dict(),
        "hbits": dict(assessment["hbits"]),
        "metrics": metrics.to_dict(),
        "classification": str(assessment["classification"]),
        "mutation_score": float(supervisor_output.mutation_score),
        "phase": float(supervisor_output.phase),
        "weights": [float(v) for v in supervisor_output.weights.tolist()],
        "cost": float(supervisor_output.thermostat.cost),
        "volume": float(supervisor_output.thermostat.volume),
        "dominant_degree": int(supervisor_output.thermostat.dominant_degree),
        "action": str(supervisor_output.thermostat.action),
        "severity": str(supervisor_output.thermostat.severity),
        "decision": dict(assessment["decision"]),
    }
    if finalization:
        reconciliation = finalization.get("reconciliation")
        if reconciliation is not None:
            out["generated_month_reconciliation"] = reconciliation.to_dict()
        out["decision"] = dict(finalization.get("decision") or out["decision"])
    return out


def _decide_pre_promotion(
    fingerprint: FileFingerprint,
    metrics: Any,
    classification: str,
    supervisor_output: KSupervisorOutput,
) -> dict[str, Any]:
    action = supervisor_output.thermostat.action
    if action == "quarantine_source":
        verdict = "quarantine"
    elif action == "restructure_source":
        verdict = "restructure"
    elif action == "review_filter_before_plot":
        verdict = "review"
    else:
        verdict = "allow"

    reasons: list[str] = [
        f"classification={classification}",
        f"volume={supervisor_output.thermostat.volume:.4f}",
        f"dominant_degree={supervisor_output.thermostat.dominant_degree}",
    ]
    reasons.extend(str(issue) for issue in fingerprint.issues)

    if metrics.m_required >= 0.80 or metrics.m_date >= 0.98:
        verdict = "quarantine"
        reasons.append("drift estrutural critico nas colunas obrigatorias ou parse temporal.")
    elif metrics.m_required >= 0.55 or metrics.m_date >= 0.75:
        verdict = "restructure" if verdict != "quarantine" else verdict
        reasons.append("drift severo, exigindo reestruturacao antes da promocao.")
    elif verdict == "allow" and classification != "compatible":
        verdict = "review"
        reasons.append("layout recuperavel, mas exige validacao adaptativa.")

    if not fingerprint.discovered_months:
        verdict = "review" if verdict == "allow" else verdict
        reasons.append("arquivo sem mes/ano detectavel; reconciliação ficará obrigatória.")

    severity = {
        "allow": "low",
        "review": "moderate",
        "restructure": "high",
        "quarantine": "critical",
    }[verdict]
    return {
        "verdict": verdict,
        "severity": severity,
        "action": action,
        "reasons": reasons,
    }


def _clamp01(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return float(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, FileFingerprint):
        return value.to_dict()
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value
