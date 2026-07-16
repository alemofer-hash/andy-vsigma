from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .semantic_dataset import load_dataset_frames


@dataclass(frozen=True)
class ParityFinding:
    code: str
    severity: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "severity": self.severity, "message": self.message}


def summarize_dataset(dataset_dir: str | Path) -> dict[str, Any]:
    frames = load_dataset_frames(dataset_dir)
    summary: dict[str, Any] = {"tables": {}, "critical_metrics": {}}
    for name, frame in sorted(frames.items()):
        table_summary: dict[str, Any] = {"rows": int(len(frame)), "columns": list(map(str, frame.columns))}
        if "timestamp" in frame.columns:
            ts = pd.to_datetime(frame["timestamp"], errors="coerce").dropna()
            table_summary["timestamp_min"] = ts.min().isoformat() if not ts.empty else ""
            table_summary["timestamp_max"] = ts.max().isoformat() if not ts.empty else ""
        summary["tables"][name] = table_summary
    flow = frames.get("fact_power_flow")
    if flow is not None:
        summary["critical_metrics"] = {
            "mva_sum": _safe_float_sum(flow, "mva"),
            "mw_sum": _safe_float_sum(flow, "mw"),
            "inversao_count": int(flow["inversao_flag"].fillna(False).astype(bool).sum()) if "inversao_flag" in flow else 0,
        }
    return summary


def compare_summaries(left: Mapping[str, Any], right: Mapping[str, Any], *, float_tolerance: float = 1e-6) -> list[ParityFinding]:
    findings: list[ParityFinding] = []
    left_tables = left.get("tables", {})
    right_tables = right.get("tables", {})
    for table in sorted(set(left_tables) | set(right_tables)):
        if table not in left_tables:
            findings.append(ParityFinding("missing_left_table", "ERROR", f"Left summary missing {table}."))
            continue
        if table not in right_tables:
            findings.append(ParityFinding("missing_right_table", "ERROR", f"Right summary missing {table}."))
            continue
        if left_tables[table].get("rows") != right_tables[table].get("rows"):
            findings.append(ParityFinding("row_count_mismatch", "ERROR", f"{table}: row counts differ."))
    for metric, value in (left.get("critical_metrics") or {}).items():
        other = (right.get("critical_metrics") or {}).get(metric)
        if other is None or abs(float(value) - float(other)) > float_tolerance:
            findings.append(ParityFinding("critical_metric_mismatch", "ERROR", f"{metric}: values differ."))
    return findings


def write_parity_report(path: str | Path, findings: list[ParityFinding], left_label: str, right_label: str) -> Path:
    lines = [
        "# ANDY BI Parity Validation",
        "",
        f"- Left: {left_label}",
        f"- Right: {right_label}",
        f"- Status: {'blocked' if findings else 'passed'}",
        "- Critical math source: ANDY Python engine",
        "",
        "## Findings",
        "",
    ]
    if findings:
        for finding in findings:
            lines.append(f"- {finding.severity} {finding.code}: {finding.message}")
    else:
        lines.append("- none")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def _safe_float_sum(frame: pd.DataFrame, column: str) -> float:
    if column not in frame.columns:
        return 0.0
    return float(pd.to_numeric(frame[column], errors="coerce").fillna(0.0).sum())
