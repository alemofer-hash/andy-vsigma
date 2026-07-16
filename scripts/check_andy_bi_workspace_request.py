from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "reports" / "ANDY_BI_WORKSPACE_REQUEST.json"
REPORT_MD = ROOT / "reports" / "ANDY_BI_WORKSPACE_REQUEST.md"

FORBIDDEN_PATTERNS = [
    re.compile(r"\\\\[^\\\s]+\\", re.IGNORECASE),
    re.compile(r"[A-Za-z]:\\Users\\", re.IGNORECASE),
    re.compile(r"client_secret", re.IGNORECASE),
]


def main() -> int:
    docs = [
        ROOT / "docs" / "ANDY_BI_WORKSPACE_REQUEST_CHECKLIST.md",
        ROOT / "docs" / "ANDY_BI_CORPORATE_PUBLICATION_PROCEDURE.md",
        ROOT / "docs" / "ANDY_BI_OWNER_MATRIX.md",
    ]
    failures: list[str] = []
    for path in docs:
        if not path.exists():
            failures.append(f"missing_doc:{path.name}")
            continue
        text = path.read_text(encoding="utf-8-sig")
        if any(pattern.search(text) for pattern in FORBIDDEN_PATTERNS):
            failures.append(f"forbidden_real_value_pattern:{path.name}")
    report = {
        "status": "passed" if not failures else "blocked",
        "failures": failures,
        "docs": [str(path) for path in docs],
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(_markdown(report), encoding="utf-8")
    print(f"status={report['status']}")
    print(f"report={REPORT_MD}")
    return 0 if not failures else 1


def _markdown(report: dict) -> str:
    return (
        "# ANDY BI Workspace Request Gate\n\n"
        f"- Status: {report['status']}\n"
        f"- Failures: {', '.join(report['failures']) if report['failures'] else 'none'}\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
