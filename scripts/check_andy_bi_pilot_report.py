from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from andy_bi.pilot_report import build_pilot_report  # noqa: E402


REPORT_JSON = ROOT / "reports" / "ANDY_BI_PILOT_REPORT.json"
REPORT_MD = ROOT / "reports" / "ANDY_BI_PILOT_REPORT.md"

FORBIDDEN_PATTERNS = [
    re.compile(r"\\\\[^\\\s]+\\", re.IGNORECASE),
    re.compile(r"[A-Za-z]:\\Users\\", re.IGNORECASE),
    re.compile(r"client_secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
]


def main() -> int:
    result = build_pilot_report(
        dataset_dir=ROOT / "artifacts" / "andy_bi_dataset",
        out_dir=ROOT / "artifacts" / "andy_bi_pilot_report",
        require_synthetic=True,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8-sig"))
    html_text = result.html_path.read_text(encoding="utf-8-sig")
    failures = list(result.findings)
    if manifest.get("synthetic") is not True:
        failures.append("pilot_manifest_must_be_synthetic")
    if manifest.get("published_to_corporate_bi") is not False:
        failures.append("pilot_must_not_publish")
    if manifest.get("contains_real_data") is not False:
        failures.append("pilot_must_not_contain_real_data")
    if manifest.get("uses_real_identity_provider") is not False:
        failures.append("pilot_must_not_use_real_identity_provider")
    if any(pattern.search(html_text) for pattern in FORBIDDEN_PATTERNS):
        failures.append("pilot_html_contains_forbidden_private_pattern")
    report = {
        "status": "passed" if not failures else "blocked",
        "failures": failures,
        "pilot_dir": str(result.out_dir),
        "html": str(result.html_path),
        "manifest": str(result.manifest_path),
        "validation_report": str(result.validation_report_path),
        "synthetic": manifest.get("synthetic"),
        "safe_for_publication_review": manifest.get("safe_for_publication_review"),
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(_markdown(report), encoding="utf-8")
    print(f"status={report['status']}")
    print(f"pilot={result.out_dir}")
    print(f"report={REPORT_MD}")
    return 0 if not failures else 1


def _markdown(report: dict) -> str:
    lines = [
        "# ANDY BI Pilot Report Gate",
        "",
        f"- Status: {report['status']}",
        f"- Synthetic: {report['synthetic']}",
        f"- Safe for publication review: {report['safe_for_publication_review']}",
        f"- Pilot dir: {report['pilot_dir']}",
        f"- HTML: {report['html']}",
        f"- Manifest: {report['manifest']}",
        "",
        "## Failures",
        "",
    ]
    lines.append("- none" if not report["failures"] else "\n".join(f"- {item}" for item in report["failures"]))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
