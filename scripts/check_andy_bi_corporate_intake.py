from __future__ import annotations

import argparse
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
JSON_REPORT = REPORT_DIR / "ANDY_BI_CORPORATE_INTAKE.json"
MD_REPORT = REPORT_DIR / "ANDY_BI_CORPORATE_INTAKE.md"
DEFAULT_CONFIG = ROOT / "config" / "andy_bi_corporate_intake.example.json"
PRIVATE_CONFIGS = [
    "config/andy_bi_corporate_intake.json",
    "config/andy_bi_corporate_intake.private.json",
]


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


def build_report(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    path = Path(config_path).resolve()
    data = load_json_config(path)
    security = validate_https_security_config(data)
    gitignore = _gitignore_text()
    tracked_private = sorted({tracked for item in PRIVATE_CONFIGS for tracked in git_ls_files(item)})
    private_ignored = {
        item: item in gitignore.replace("\\", "/") or item.replace("/", "\\") in gitignore
        for item in PRIVATE_CONFIGS
    }
    checks = {
        "config_exists": path.exists(),
        "config_valid_json": isinstance(data, dict),
        "https_security_ready": security.status == "https_security_ready",
        "private_intake_configs_not_tracked": not tracked_private,
        "private_intake_configs_ignored": all(private_ignored.values()),
        "report_redacts_urls": all(endpoint.get("host_redacted") is True for endpoint in security.endpoints if endpoint.get("host_hash")),
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "status": "corporate_intake_https_ready" if not failures else "blocked",
        "generated_utc": now_utc(),
        "config_path_redacted": path.name,
        "checks": checks,
        "failures": failures,
        "https_security": security.as_dict(),
        "private_tracking": {
            "tracked_private_configs": tracked_private,
            "private_ignored": private_ignored,
            "paths_redacted": True,
        },
        "safety_boundary": {
            "connects_to_network": False,
            "prints_raw_urls": False,
            "prints_secrets": False,
            "changes_analytical_engine": False,
        },
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ANDY BI Corporate Config Intake HTTPS Gate",
        "",
        f"- Generated UTC: {report['generated_utc']}",
        f"- Status: {report['status']}",
        f"- Config: {report['config_path_redacted']}",
        f"- Failures: {', '.join(report['failures']) if report['failures'] else 'none'}",
        "",
        "## Checks",
        "",
    ]
    for name, passed in report["checks"].items():
        lines.append(f"- {name}: {passed}")
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
    parser = argparse.ArgumentParser(description="Validate ANDY BI corporate private config intake HTTPS/TLS contract without network calls.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--json-out", default=str(JSON_REPORT))
    parser.add_argument("--md-out", default=str(MD_REPORT))
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
    return 0 if report["status"] == "corporate_intake_https_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
