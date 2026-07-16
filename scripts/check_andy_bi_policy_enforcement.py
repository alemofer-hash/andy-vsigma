from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from andy_bi.enforcement import evaluate_boundary_policy


REPORT_DIR = ROOT / "reports"
JSON_REPORT = REPORT_DIR / "ANDY_BI_POLICY_ENFORCEMENT.json"
MD_REPORT = REPORT_DIR / "ANDY_BI_POLICY_ENFORCEMENT.md"

MOCK_CLAIMS_EXAMPLE = ROOT / "config" / "andy_bi_mock_claims.example.json"
TENANT_POLICY_EXAMPLE = ROOT / "config" / "andy_bi_tenant_policy.example.json"
ENFORCEMENT_EXAMPLE = ROOT / "config" / "andy_bi_policy_enforcement.example.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be object")
    return data


def _enabled_mock_file() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="andy_bi_policy_mock_"))
    temp_path = temp_dir / "andy_bi_mock_claims.private.json"
    data = _load_json(MOCK_CLAIMS_EXAMPLE)
    data["mock_enabled"] = True
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return temp_path


def _payload(*, identity_key: str, tenant_id: str, state: str, source_root: str, enabled_mock_path: Path) -> dict[str, Any]:
    return {
        "db_path": "not_used_by_policy_gate.duckdb",
        "bi_policy": {
            "enabled": True,
            "identity_key": identity_key,
            "mock_claims_file": str(enabled_mock_path),
            "tenant_policy_file": str(TENANT_POLICY_EXAMPLE),
        },
        "bi_scope": {
            "tenant_id": tenant_id,
            "state": state,
            "source_root": source_root,
        },
    }


def build_report() -> dict[str, Any]:
    enforcement = _load_json(ENFORCEMENT_EXAMPLE)
    disabled_result = evaluate_boundary_policy("query.page", {"db_path": "ignored.duckdb"})
    mock_path = _enabled_mock_file()
    try:
        allow_query = evaluate_boundary_policy(
            "query.page",
            _payload(
                identity_key="mock_engineer_rs",
                tenant_id="DISTRIBUTOR_RS_PLACEHOLDER",
                state="RS",
                source_root="${ANDY_BI_RS_SOURCE_ROOT}",
                enabled_mock_path=mock_path,
            ),
        )
        allow_export = evaluate_boundary_policy(
            "export.xlsx_dashboard",
            _payload(
                identity_key="mock_engineer_rs",
                tenant_id="DISTRIBUTOR_RS_PLACEHOLDER",
                state="RS",
                source_root="${ANDY_BI_RS_SOURCE_ROOT}",
                enabled_mock_path=mock_path,
            ),
        )
        deny_scope = evaluate_boundary_policy(
            "query.page",
            _payload(
                identity_key="mock_engineer_rs",
                tenant_id="DISTRIBUTOR_PA_PLACEHOLDER",
                state="PA",
                source_root="${ANDY_BI_PA_SOURCE_ROOT}",
                enabled_mock_path=mock_path,
            ),
        )
        deny_role = evaluate_boundary_policy(
            "export.csv_long",
            _payload(
                identity_key="mock_viewer_pa",
                tenant_id="DISTRIBUTOR_PA_PLACEHOLDER",
                state="PA",
                source_root="${ANDY_BI_PA_SOURCE_ROOT}",
                enabled_mock_path=mock_path,
            ),
        )
        deny_missing_scope = evaluate_boundary_policy(
            "query.page",
            {
                "db_path": "ignored.duckdb",
                "bi_policy": {
                    "enabled": True,
                    "identity_key": "mock_engineer_rs",
                    "mock_claims_file": str(mock_path),
                    "tenant_policy_file": str(TENANT_POLICY_EXAMPLE),
                },
            },
        )
    finally:
        shutil.rmtree(mock_path.parent, ignore_errors=True)

    checks = {
        "enforcement_template_disabled_by_default": enforcement.get("enabled") is False,
        "default_boundary_policy_result_is_disabled": disabled_result.status == "disabled",
        "engineer_query_allowed_in_scope": allow_query.status == "allowed",
        "engineer_export_allowed_in_scope": allow_export.status == "allowed",
        "engineer_query_denied_outside_scope": deny_scope.status == "denied",
        "viewer_export_denied_by_role": deny_role.status == "denied",
        "enabled_policy_requires_bi_scope": deny_missing_scope.status == "blocked",
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "status": "policy_enforcement_adapter_ready" if not failures else "blocked",
        "generated_utc": now_utc(),
        "checks": checks,
        "failures": failures,
        "decisions": {
            "default_disabled": disabled_result.as_dict(),
            "engineer_query_allowed": allow_query.as_dict(),
            "engineer_export_allowed": allow_export.as_dict(),
            "engineer_query_outside_scope": deny_scope.as_dict(),
            "viewer_export_denied": deny_role.as_dict(),
            "missing_scope_blocked": deny_missing_scope.as_dict(),
        },
        "safety_boundary": {
            "connects_to_corporate_network": False,
            "stores_passwords": False,
            "uses_real_identity_provider": False,
            "changes_analytical_engine": False,
            "enforcement_default_enabled": False,
        },
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ANDY BI Policy Enforcement Adapter Gate",
        "",
        f"- Generated UTC: {report['generated_utc']}",
        f"- Status: {report['status']}",
        f"- Failures: {', '.join(report['failures']) if report['failures'] else 'none'}",
        "",
        "## Checks",
        "",
    ]
    for name, passed in report["checks"].items():
        lines.append(f"- {name}: {passed}")
    lines.extend(["", "## Decisions", ""])
    for name, decision in report["decisions"].items():
        lines.append(f"- {name}: status={decision['status']} reason={decision['reason']}")
    lines.extend(["", "## Safety Boundary", ""])
    for name, value in report["safety_boundary"].items():
        lines.append(f"- {name}: {value}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ANDY BI-2 policy enforcement adapter without corporate network data.")
    parser.add_argument("--json-out", default=str(JSON_REPORT))
    parser.add_argument("--md-out", default=str(MD_REPORT))
    args = parser.parse_args()
    report = build_report()
    json_path = Path(args.json_out).resolve()
    md_path = Path(args.md_out).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0 if report["status"] == "policy_enforcement_adapter_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
