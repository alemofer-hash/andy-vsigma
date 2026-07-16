from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_andy_bi_private_config_dry_run import (  # noqa: E402
    DEFAULT_PRIVATE_CONFIG,
    build_report as build_private_config_dry_run,
)
from scripts.check_andy_bi_readiness import build_report as build_readiness_report  # noqa: E402


REPORT_DIR = ROOT / "reports"
JSON_REPORT = REPORT_DIR / "ANDY_BI_CORPORATE_CONFIG_REVIEW.json"
MD_REPORT = REPORT_DIR / "ANDY_BI_CORPORATE_CONFIG_REVIEW.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _review_status(readiness: dict[str, Any], dry_run: dict[str, Any]) -> str:
    if readiness.get("status") != "ready_for_private_corporate_inputs":
        return "blocked"
    if dry_run.get("status") == "private_config_dry_run_ready":
        return "ready_for_human_security_review"
    if dry_run.get("status") == "waiting_for_private_config":
        return "waiting_for_private_config"
    return "blocked"


def _review_decision(status: str) -> str:
    if status == "ready_for_human_security_review":
        return "ALLOW_REDACTED_HUMAN_REVIEW_BEFORE_PROVIDER_IMPLEMENTATION"
    if status == "waiting_for_private_config":
        return "HOLD_WAITING_FOR_CORPORATE_IT_INPUT"
    return "BLOCK_PROVIDER_IMPLEMENTATION"


def build_report(config_path: str | Path = DEFAULT_PRIVATE_CONFIG) -> dict[str, Any]:
    readiness = build_readiness_report()
    dry_run = build_private_config_dry_run(config_path)
    status = _review_status(readiness, dry_run)
    checks = {
        "readiness_gate_ready": readiness.get("status") == "ready_for_private_corporate_inputs",
        "private_config_present": dry_run.get("checks", {}).get("private_config_exists") is True,
        "private_config_dry_run_ready": dry_run.get("status") == "private_config_dry_run_ready",
        "dry_run_waiting_is_safe": dry_run.get("status") == "waiting_for_private_config",
        "no_network_calls": dry_run.get("safety_boundary", {}).get("connects_to_network") is False,
        "no_raw_url_printing": dry_run.get("safety_boundary", {}).get("prints_raw_urls") is False,
        "no_secret_printing": dry_run.get("safety_boundary", {}).get("prints_secrets") is False,
        "provider_not_activated": dry_run.get("safety_boundary", {}).get("uses_private_config_for_authentication", False) is False,
        "analytical_engine_unchanged": dry_run.get("safety_boundary", {}).get("changes_analytical_engine") is False,
    }
    hard_failures = [
        name
        for name in (
            "readiness_gate_ready",
            "no_network_calls",
            "no_raw_url_printing",
            "no_secret_printing",
            "provider_not_activated",
            "analytical_engine_unchanged",
        )
        if not checks.get(name)
    ]
    if status == "blocked":
        hard_failures.extend(dry_run.get("failures", []))
    return {
        "status": status,
        "review_decision": _review_decision(status),
        "generated_utc": now_utc(),
        "config_path_redacted": Path(config_path).name,
        "checks": checks,
        "failures": sorted(set(hard_failures)),
        "readiness_status": readiness.get("status"),
        "private_config_dry_run_status": dry_run.get("status"),
        "private_config_dry_run": dry_run,
        "review_scope": {
            "connects_to_network": False,
            "activates_real_identity_provider": False,
            "stores_employee_passwords": False,
            "prints_raw_urls": False,
            "prints_secrets": False,
            "changes_analytical_engine": False,
            "changes_export_pipeline": False,
        },
        "next_action": _next_action(status),
    }


def _next_action(status: str) -> str:
    if status == "ready_for_human_security_review":
        return "Human reviewer should inspect the redacted report and approve or block provider implementation."
    if status == "waiting_for_private_config":
        return "Obtain the private corporate config from IT/security and run this review again."
    return "Fix blocked readiness or private config findings before any provider work."


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ANDY BI Corporate Config Review",
        "",
        f"- Generated UTC: {report['generated_utc']}",
        f"- Status: {report['status']}",
        f"- Review decision: {report['review_decision']}",
        f"- Config: {report['config_path_redacted']}",
        f"- Readiness: {report['readiness_status']}",
        f"- Private config dry-run: {report['private_config_dry_run_status']}",
        f"- Failures: {', '.join(report['failures']) if report['failures'] else 'none'}",
        "",
        "## Checks",
        "",
    ]
    for name, value in report["checks"].items():
        lines.append(f"- {name}: {value}")
    lines.extend(["", "## Review Scope", ""])
    for name, value in report["review_scope"].items():
        lines.append(f"- {name}: {value}")
    lines.extend(["", "## Redacted Dry Run Summary", ""])
    dry_run = report["private_config_dry_run"]
    lines.append(f"- status: {dry_run.get('status')}")
    lines.append(f"- config: {dry_run.get('config_path_redacted')}")
    lines.append(f"- failures: {', '.join(dry_run.get('failures', [])) if dry_run.get('failures') else 'none'}")
    if dry_run.get("status") == "waiting_for_private_config":
        lines.extend(["", "## Guidance", ""])
        for item in dry_run.get("guidance", []):
            lines.append(f"- {item}")
    elif dry_run.get("status") == "private_config_dry_run_ready":
        lines.append(f"- config_location: {dry_run.get('config_location')}")
        lines.append(f"- config_size_bytes: {dry_run.get('config_size_bytes')}")
        lines.append(f"- config_fingerprint_sha256: {dry_run.get('config_fingerprint_sha256')}")
        lines.append(f"- top_level_keys: {', '.join(dry_run.get('top_level_keys', []))}")
        lines.extend(["", "## Endpoint Summaries", ""])
        for endpoint in dry_run.get("https_security", {}).get("endpoints", []):
            lines.append(
                f"- {endpoint['field_path']}: scheme={endpoint['scheme']} host_hash={endpoint['host_hash']} path_depth={endpoint['path_depth']}"
            )
    lines.extend(["", "## Next Action", "", report["next_action"], ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Review ANDY BI private corporate config readiness with redacted offline reporting.")
    parser.add_argument("--config", default=str(DEFAULT_PRIVATE_CONFIG))
    parser.add_argument("--json-out", default=str(JSON_REPORT))
    parser.add_argument("--md-out", default=str(MD_REPORT))
    parser.add_argument("--strict", action="store_true", help="Return non-zero if the private config is missing.")
    args = parser.parse_args()
    report = build_report(args.config)
    json_path = Path(args.json_out).resolve()
    md_path = Path(args.md_out).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    if report["status"] == "blocked":
        return 2
    if report["status"] == "waiting_for_private_config" and args.strict:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
