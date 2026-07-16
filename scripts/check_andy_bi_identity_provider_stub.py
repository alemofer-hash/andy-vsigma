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
from andy_bi.providers import CORPORATE_PROVIDER_TYPES, load_provider_template, resolve_identity_for_policy


REPORT_DIR = ROOT / "reports"
JSON_REPORT = REPORT_DIR / "ANDY_BI_IDENTITY_PROVIDER_STUB.json"
MD_REPORT = REPORT_DIR / "ANDY_BI_IDENTITY_PROVIDER_STUB.md"

MOCK_CLAIMS_EXAMPLE = ROOT / "config" / "andy_bi_mock_claims.example.json"
PROVIDER_TEMPLATE = ROOT / "config" / "andy_bi_identity_provider.example.json"
TENANT_POLICY_EXAMPLE = ROOT / "config" / "andy_bi_tenant_policy.example.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be object")
    return data


def _enabled_mock_file() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="andy_bi_provider_mock_"))
    temp_path = temp_dir / "andy_bi_mock_claims.private.json"
    data = _load_json(MOCK_CLAIMS_EXAMPLE)
    data["mock_enabled"] = True
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return temp_path


def build_report() -> dict[str, Any]:
    template = load_provider_template(PROVIDER_TEMPLATE)
    mock_path = _enabled_mock_file()
    try:
        mock_result = resolve_identity_for_policy(
            {
                "identity_provider": "mock_claims",
                "identity_key": "mock_engineer_rs",
                "mock_claims_file": str(mock_path),
            }
        )
        oidc_stub = resolve_identity_for_policy(
            {
                "identity_provider": "oidc",
                "identity_key": "mock_engineer_rs",
                "identity_provider_config": str(PROVIDER_TEMPLATE),
                "provider_enabled": True,
            }
        )
        enforcement_with_oidc = evaluate_boundary_policy(
            "query.page",
            {
                "db_path": "not_used_by_policy_gate.duckdb",
                "bi_policy": {
                    "enabled": True,
                    "identity_provider": "oidc",
                    "identity_key": "mock_engineer_rs",
                    "identity_provider_config": str(PROVIDER_TEMPLATE),
                    "provider_enabled": True,
                    "tenant_policy_file": str(TENANT_POLICY_EXAMPLE),
                },
                "bi_scope": {
                    "tenant_id": "DISTRIBUTOR_RS_PLACEHOLDER",
                    "state": "RS",
                    "source_root": "${ANDY_BI_RS_SOURCE_ROOT}",
                },
            },
        )
    finally:
        shutil.rmtree(mock_path.parent, ignore_errors=True)

    provider_entries = template.get("providers", {}) if isinstance(template, dict) else {}
    corporate_stubs = {
        name: isinstance(provider_entries.get(name), dict) and provider_entries[name].get("stub_only") is True
        for name in sorted(CORPORATE_PROVIDER_TYPES)
    }
    security_rules = template.get("security_rules", {}) if isinstance(template, dict) else {}
    checks = {
        "provider_template_exists": PROVIDER_TEMPLATE.exists(),
        "provider_template_valid_json": bool(template),
        "default_provider_is_mock_claims": template.get("default_provider") == "mock_claims",
        "corporate_providers_are_stub_only": all(corporate_stubs.values()),
        "template_disables_password_and_secret_storage": security_rules.get("store_user_password") is False
        and security_rules.get("store_client_secret") is False,
        "template_disallows_stub_network_calls": security_rules.get("network_calls_allowed_in_stub") is False,
        "mock_provider_still_resolves": mock_result.status == "resolved",
        "oidc_stub_blocks_when_enabled": oidc_stub.status == "blocked",
        "oidc_stub_does_not_use_network": oidc_stub.safety.get("connects_to_corporate_network") is False,
        "enforcement_blocks_corporate_stub": enforcement_with_oidc.status == "blocked",
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "status": "corporate_identity_adapter_stub_ready" if not failures else "blocked",
        "generated_utc": now_utc(),
        "checks": checks,
        "failures": failures,
        "corporate_stubs": corporate_stubs,
        "mock_result": mock_result.public_summary(),
        "oidc_stub": oidc_stub.public_summary(),
        "enforcement_with_oidc_stub": enforcement_with_oidc.as_dict(),
        "safety_boundary": {
            "connects_to_corporate_network": False,
            "stores_passwords": False,
            "uses_real_identity_provider": False,
            "changes_analytical_engine": False,
        },
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ANDY BI Corporate Identity Adapter Stub Gate",
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
    lines.extend(["", "## Corporate Stubs", ""])
    for name, value in report["corporate_stubs"].items():
        lines.append(f"- {name}: stub_only={value}")
    lines.extend(["", "## Safety Boundary", ""])
    for name, value in report["safety_boundary"].items():
        lines.append(f"- {name}: {value}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ANDY BI-3 corporate identity provider stubs without network calls.")
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
    return 0 if report["status"] == "corporate_identity_adapter_stub_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
