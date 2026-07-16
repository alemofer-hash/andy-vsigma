from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
JSON_REPORT = REPORT_DIR / "ANDY_BI_READINESS.json"
MD_REPORT = REPORT_DIR / "ANDY_BI_READINESS.md"

REQUIRED_CONFIGS = [
    ROOT / "config" / "andy_bi_identity.example.json",
    ROOT / "config" / "andy_bi_tenant_policy.example.json",
    ROOT / "config" / "andy_bi_environment.example.json",
]

REQUIRED_DOCS = [
    ROOT / "docs" / "ANDY_BI_EQUATORIAL_ROADMAP.md",
    ROOT / "docs" / "ANDY_BI_PRODUCT_CHARTER.md",
    ROOT / "docs" / "ANDY_BI_IDENTITY_OPTIONS.md",
    ROOT / "docs" / "ANDY_BI_SECURITY_MODEL.md",
    ROOT / "docs" / "ANDY_BI_TENANT_POLICY_MODEL.md",
    ROOT / "docs" / "ANDY_BI_PREIMPLEMENTATION_READINESS.md",
]

PRIVATE_CONFIGS = [
    "config/andy_bi_identity.json",
    "config/andy_bi_identity.private.json",
    "config/andy_bi_environment.local.json",
    "config/andy_bi_environment.private.json",
    "config/andy_bi_tenant_policy.json",
    "config/andy_bi_tenant_policy.private.json",
]

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"\\\\[^\\\s]+\\", re.IGNORECASE),
    re.compile(r"[A-Za-z]:\\Users\\", re.IGNORECASE),
    re.compile(r"\.local\b", re.IGNORECASE),
    re.compile(r"client_secret\s*[:=]\s*[^,\s}]+", re.IGNORECASE),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig") if path.exists() else ""


def git_ls_files(pathspec: str) -> list[str]:
    completed = subprocess.run(["git", "ls-files", pathspec], cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return []
    return [line.strip().replace("\\", "/") for line in completed.stdout.splitlines() if line.strip()]


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # pragma: no cover - message is for reports.
        return None, f"invalid_json: {exc}"
    if not isinstance(data, dict):
        return None, "json_root_not_object"
    return data, None


def flatten_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        out: list[str] = []
        for nested in value.values():
            out.extend(flatten_values(nested))
        return out
    if isinstance(value, list):
        out = []
        for nested in value:
            out.extend(flatten_values(nested))
        return out
    if value is None:
        return []
    return [str(value)]


def config_summary(path: Path) -> dict[str, Any]:
    data, error = load_json(path)
    values = flatten_values(data or {})
    forbidden_hits = []
    for item in values:
        for pattern in FORBIDDEN_VALUE_PATTERNS:
            if pattern.search(item):
                forbidden_hits.append({"pattern": pattern.pattern, "value_redacted": True})
    return {
        "path": rel(path),
        "exists": path.exists(),
        "json_valid": error is None,
        "error": error,
        "schema": (data or {}).get("schema") if data else None,
        "schema_version": (data or {}).get("schema_version") if data else None,
        "forbidden_value_hit_count": len(forbidden_hits),
        "forbidden_values_redacted": forbidden_hits,
    }


def build_report() -> dict[str, Any]:
    gitignore = read_text(ROOT / ".gitignore")
    config_reports = [config_summary(path) for path in REQUIRED_CONFIGS]
    doc_reports = [{"path": rel(path), "exists": path.exists()} for path in REQUIRED_DOCS]
    private_tracked = sorted({tracked for pattern in PRIVATE_CONFIGS for tracked in git_ls_files(pattern)})
    required_ignore_entries = {
        private_path: private_path in gitignore.replace("\\", "/") or private_path.replace("/", "\\") in gitignore
        for private_path in PRIVATE_CONFIGS
    }
    checks = {
        "required_configs_exist": all(item["exists"] for item in config_reports),
        "required_configs_valid_json": all(item["json_valid"] for item in config_reports),
        "required_docs_exist": all(item["exists"] for item in doc_reports),
        "examples_have_no_forbidden_real_values": all(item["forbidden_value_hit_count"] == 0 for item in config_reports),
        "private_bi_configs_not_tracked": not private_tracked,
        "private_bi_configs_ignored": all(required_ignore_entries.values()),
        "identity_template_disables_password_storage": _identity_template_disables_password_storage(),
        "tenant_policy_defaults_to_deny": _tenant_policy_defaults_to_deny(),
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "status": "ready_for_private_corporate_inputs" if not failures else "blocked",
        "generated_utc": now_utc(),
        "checks": checks,
        "failures": failures,
        "configs": config_reports,
        "docs": doc_reports,
        "private_config_tracking": {
            "tracked_private_configs": private_tracked,
            "paths_redacted": True,
        },
        "required_ignore_entries": required_ignore_entries,
        "safety_boundary": {
            "connects_to_corporate_network": False,
            "stores_passwords": False,
            "requires_real_identity_provider": False,
            "changes_analytical_engine": False,
        },
    }


def _identity_template_disables_password_storage() -> bool:
    data, error = load_json(ROOT / "config" / "andy_bi_identity.example.json")
    if error or data is None:
        return False
    rules = data.get("security_rules", {})
    return (
        isinstance(rules, dict)
        and rules.get("store_user_password") is False
        and rules.get("store_client_secret") is False
        and rules.get("interactive_password_login_allowed") is False
    )


def _tenant_policy_defaults_to_deny() -> bool:
    data, error = load_json(ROOT / "config" / "andy_bi_tenant_policy.example.json")
    if error or data is None:
        return False
    return data.get("default_decision") == "deny"


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ANDY BI Readiness Gate",
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
    lines.extend(["", "## Config Templates", ""])
    for item in report["configs"]:
        lines.append(f"- {item['path']}: exists={item['exists']} json_valid={item['json_valid']} forbidden_value_hits={item['forbidden_value_hit_count']}")
    lines.extend(["", "## Docs", ""])
    for item in report["docs"]:
        lines.append(f"- {item['path']}: exists={item['exists']}")
    lines.extend(["", "## Safety Boundary", ""])
    for name, value in report["safety_boundary"].items():
        lines.append(f"- {name}: {value}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ANDY BI preimplementation readiness without printing corporate secrets.")
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
    return 0 if report["status"] == "ready_for_private_corporate_inputs" else 2


if __name__ == "__main__":
    raise SystemExit(main())
