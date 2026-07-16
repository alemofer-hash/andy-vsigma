from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from andy_bi.https_security import load_json_config, validate_https_security_config


REPORT_DIR = ROOT / "reports"
JSON_REPORT = REPORT_DIR / "ANDY_BI_PRIVATE_CONFIG_DRY_RUN.json"
MD_REPORT = REPORT_DIR / "ANDY_BI_PRIVATE_CONFIG_DRY_RUN.md"
DEFAULT_PRIVATE_CONFIG = ROOT / "config" / "andy_bi_corporate_intake.private.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_ls_files(pathspec: str) -> list[str]:
    completed = subprocess.run(["git", "ls-files", pathspec], cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return []
    return [line.strip().replace("\\", "/") for line in completed.stdout.splitlines() if line.strip()]


def _gitignore_text() -> str:
    path = ROOT / ".gitignore"
    return path.read_text(encoding="utf-8-sig") if path.exists() else ""


def _relative_or_name(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _top_level_keys(data: dict[str, Any]) -> list[str]:
    return sorted(str(key) for key in data.keys())


def _section_present(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    return isinstance(value, dict) and bool(value)


def _is_ignored(path: Path) -> bool:
    rel = _relative_or_name(path)
    gitignore = _gitignore_text()
    return rel in gitignore.replace("\\", "/") or rel.replace("/", "\\") in gitignore


def _is_tracked(path: Path) -> bool:
    rel = _relative_or_name(path)
    return bool(git_ls_files(rel))


def build_report(config_path: str | Path = DEFAULT_PRIVATE_CONFIG) -> dict[str, Any]:
    path = Path(config_path).resolve()
    if not path.exists():
        return {
            "status": "waiting_for_private_config",
            "generated_utc": now_utc(),
            "config_path_redacted": path.name,
            "checks": {
                "private_config_exists": False,
                "connects_to_network": False,
                "prints_raw_urls": False,
                "prints_secrets": False,
            },
            "failures": [],
            "guidance": [
                "Copy config/andy_bi_corporate_intake.example.json to config/andy_bi_corporate_intake.private.json.",
                "Fill only values approved by corporate IT/security.",
                "Run this dry-run gate before enabling any real identity provider.",
            ],
            "safety_boundary": {
                "connects_to_network": False,
                "prints_raw_urls": False,
                "prints_secrets": False,
                "changes_analytical_engine": False,
            },
        }

    data = load_json_config(path)
    security = validate_https_security_config(data)
    checks = {
        "private_config_exists": True,
        "private_config_valid_json": isinstance(data, dict),
        "private_config_not_tracked": not _is_tracked(path),
        "private_config_ignored_if_inside_repo": (not path.is_relative_to(ROOT)) or _is_ignored(path),
        "https_security_ready": security.status == "https_security_ready",
        "identity_provider_section_present": _section_present(data, "identity_provider"),
        "https_security_section_present": _section_present(data, "https_security"),
        "report_redacts_endpoints": all(endpoint.get("host_redacted") is True for endpoint in security.endpoints if endpoint.get("host_hash")),
        "connects_to_network": False,
        "prints_raw_urls": False,
        "prints_secrets": False,
    }
    safety_false_is_expected = {"connects_to_network", "prints_raw_urls", "prints_secrets"}
    failures = [name for name, passed in checks.items() if not passed and name not in safety_false_is_expected]
    return {
        "status": "private_config_dry_run_ready" if not failures else "blocked",
        "generated_utc": now_utc(),
        "config_path_redacted": path.name,
        "config_location": "inside_repo" if path.is_relative_to(ROOT) else "outside_repo",
        "config_fingerprint_sha256": _fingerprint(path),
        "config_size_bytes": path.stat().st_size,
        "top_level_keys": _top_level_keys(data),
        "checks": checks,
        "failures": failures,
        "https_security": security.as_dict(),
        "safety_boundary": {
            "connects_to_network": False,
            "prints_raw_urls": False,
            "prints_secrets": False,
            "changes_analytical_engine": False,
            "uses_private_config_for_authentication": False,
        },
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ANDY BI Private Config Dry Run",
        "",
        f"- Generated UTC: {report['generated_utc']}",
        f"- Status: {report['status']}",
        f"- Config: {report['config_path_redacted']}",
        f"- Failures: {', '.join(report.get('failures', [])) if report.get('failures') else 'none'}",
        "",
        "## Checks",
        "",
    ]
    for name, passed in report["checks"].items():
        lines.append(f"- {name}: {passed}")
    if report["status"] == "waiting_for_private_config":
        lines.extend(["", "## Guidance", ""])
        for item in report.get("guidance", []):
            lines.append(f"- {item}")
    else:
        lines.extend(["", "## Config Summary", ""])
        lines.append(f"- config_location: {report['config_location']}")
        lines.append(f"- config_size_bytes: {report['config_size_bytes']}")
        lines.append(f"- config_fingerprint_sha256: {report['config_fingerprint_sha256']}")
        lines.append(f"- top_level_keys: {', '.join(report['top_level_keys'])}")
        lines.extend(["", "## HTTPS Findings", ""])
        findings = report["https_security"]["findings"]
        if findings:
            for item in findings:
                lines.append(f"- {item['severity']} {item['code']} at {item['field_path']}")
        else:
            lines.append("- none")
        lines.extend(["", "## Endpoint Summaries", ""])
        for endpoint in report["https_security"]["endpoints"]:
            lines.append(
                f"- {endpoint['field_path']}: scheme={endpoint['scheme']} host_hash={endpoint['host_hash']} path_depth={endpoint['path_depth']}"
            )
    lines.extend(["", "## Safety Boundary", ""])
    for name, value in report["safety_boundary"].items():
        lines.append(f"- {name}: {value}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run validate a private ANDY BI corporate config with redacted reporting and no network calls.")
    parser.add_argument("--config", default=str(DEFAULT_PRIVATE_CONFIG))
    parser.add_argument("--json-out", default=str(JSON_REPORT))
    parser.add_argument("--md-out", default=str(MD_REPORT))
    parser.add_argument("--strict", action="store_true", help="Return non-zero if the private config is not present.")
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
    if report["status"] == "private_config_dry_run_ready":
        return 0
    if report["status"] == "waiting_for_private_config" and not args.strict:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
