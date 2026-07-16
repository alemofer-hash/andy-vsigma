from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from andy_bi.identity import MockIdentityResolver
from andy_bi.policy import AccessRequest, TenantPolicyResolver


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
JSON_REPORT = REPORT_DIR / "ANDY_BI_IDENTITY_MOCK.json"
MD_REPORT = REPORT_DIR / "ANDY_BI_IDENTITY_MOCK.md"

MOCK_CLAIMS_EXAMPLE = ROOT / "config" / "andy_bi_mock_claims.example.json"
TENANT_POLICY_EXAMPLE = ROOT / "config" / "andy_bi_tenant_policy.example.json"

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"\\\\[^\\\s]+\\", re.IGNORECASE),
    re.compile(r"[A-Za-z]:\\Users\\", re.IGNORECASE),
    re.compile(r"\.local\b", re.IGNORECASE),
    re.compile(r"password\s*[:=]\s*[^,\s}]+", re.IGNORECASE),
    re.compile(r"secret\s*[:=]\s*[^,\s}]+", re.IGNORECASE),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be object")
    return data


def _flatten_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        out: list[str] = []
        for nested in value.values():
            out.extend(_flatten_values(nested))
        return out
    if isinstance(value, list):
        out = []
        for nested in value:
            out.extend(_flatten_values(nested))
        return out
    if value is None:
        return []
    return [str(value)]


def _forbidden_hit_count(path: Path) -> int:
    data = _load_json(path)
    count = 0
    for item in _flatten_values(data):
        for pattern in FORBIDDEN_VALUE_PATTERNS:
            if pattern.search(item):
                count += 1
    return count


def _make_enabled_mock_file() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="andy_bi_identity_mock_"))
    temp_path = temp_dir / "andy_bi_mock_claims.private.json"
    data = _load_json(MOCK_CLAIMS_EXAMPLE)
    data["mock_enabled"] = True
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return temp_path


def build_report() -> dict[str, Any]:
    mock_data = _load_json(MOCK_CLAIMS_EXAMPLE)
    tenant_policy = TenantPolicyResolver.from_file(TENANT_POLICY_EXAMPLE)
    disabled_resolution = MockIdentityResolver(enabled=False, config_path=MOCK_CLAIMS_EXAMPLE).resolve()

    enabled_path = _make_enabled_mock_file()
    try:
        engineer_resolution = MockIdentityResolver(enabled=True, config_path=enabled_path).resolve("mock_engineer_rs")
        viewer_resolution = MockIdentityResolver(enabled=True, config_path=enabled_path).resolve("mock_viewer_pa")
    finally:
        shutil.rmtree(enabled_path.parent, ignore_errors=True)

    engineer_claims = engineer_resolution.claims
    viewer_claims = viewer_resolution.claims
    allow_query = tenant_policy.evaluate(
        engineer_claims,
        AccessRequest(action="query", tenant_id="DISTRIBUTOR_RS_PLACEHOLDER", state="RS", source_root="${ANDY_BI_RS_SOURCE_ROOT}"),
    )
    allow_export = tenant_policy.evaluate(
        engineer_claims,
        AccessRequest(action="export", tenant_id="DISTRIBUTOR_RS_PLACEHOLDER", state="RS", source_root="${ANDY_BI_RS_SOURCE_ROOT}"),
    )
    deny_wrong_tenant = tenant_policy.evaluate(
        engineer_claims,
        AccessRequest(action="query", tenant_id="DISTRIBUTOR_PA_PLACEHOLDER", state="PA", source_root="${ANDY_BI_PA_SOURCE_ROOT}"),
    )
    deny_viewer_export = tenant_policy.evaluate(
        viewer_claims,
        AccessRequest(action="export", tenant_id="DISTRIBUTOR_PA_PLACEHOLDER", state="PA", source_root="${ANDY_BI_PA_SOURCE_ROOT}"),
    )

    checks = {
        "mock_claims_example_exists": MOCK_CLAIMS_EXAMPLE.exists(),
        "mock_claims_example_valid_json": isinstance(mock_data, dict),
        "mock_claims_disabled_by_default": mock_data.get("mock_enabled") is False and disabled_resolution.status == "disabled",
        "mock_claims_have_no_forbidden_real_values": _forbidden_hit_count(MOCK_CLAIMS_EXAMPLE) == 0,
        "enabled_mock_resolves_engineer": engineer_resolution.status == "resolved",
        "enabled_mock_resolves_viewer": viewer_resolution.status == "resolved",
        "engineer_query_allowed_in_scope": allow_query.allowed is True,
        "engineer_export_allowed_in_scope": allow_export.allowed is True,
        "engineer_query_denied_outside_scope": deny_wrong_tenant.allowed is False,
        "viewer_export_denied_by_role": deny_viewer_export.allowed is False,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "status": "identity_contract_mock_ready" if not failures else "blocked",
        "generated_utc": now_utc(),
        "checks": checks,
        "failures": failures,
        "disabled_resolution": disabled_resolution.public_summary(),
        "engineer_resolution": engineer_resolution.public_summary(),
        "viewer_resolution": viewer_resolution.public_summary(),
        "decisions": {
            "engineer_query_in_scope": allow_query.as_dict(),
            "engineer_export_in_scope": allow_export.as_dict(),
            "engineer_query_outside_scope": deny_wrong_tenant.as_dict(),
            "viewer_export": deny_viewer_export.as_dict(),
        },
        "safety_boundary": {
            "connects_to_corporate_network": False,
            "stores_passwords": False,
            "uses_real_employee_claims": False,
            "enables_runtime_login": False,
            "changes_analytical_engine": False,
        },
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ANDY BI Identity Contract Mock Gate",
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
        lines.append(f"- {name}: allowed={decision['allowed']} reason={decision['reason']}")
    lines.extend(["", "## Safety Boundary", ""])
    for name, value in report["safety_boundary"].items():
        lines.append(f"- {name}: {value}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ANDY BI-1 identity contract mock without real corporate identity data.")
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
    return 0 if report["status"] == "identity_contract_mock_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
