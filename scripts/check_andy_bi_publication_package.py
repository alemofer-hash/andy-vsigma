from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from andy_bi.export_package import build_corporate_package  # noqa: E402


REPORT_JSON = ROOT / "reports" / "ANDY_BI_PUBLICATION_PACKAGE.json"
REPORT_MD = ROOT / "reports" / "ANDY_BI_PUBLICATION_PACKAGE.md"


def main() -> int:
    package = build_corporate_package(ROOT / "artifacts" / "andy_bi_corporate_package")
    required = [
        "README_FOR_TI_BI.md",
        "ANDY_BI_CORPORATE_PUBLICATION_PROCEDURE.md",
        "ANDY_BI_DATA_CONTRACT.md",
        "ANDY_BI_WORKSPACE_REQUEST_CHECKLIST.md",
        "ANDY_BI_RLS_ABAC_POLICY.md",
        "ANDY_BI_PILOT_REPORT_SPEC.md",
        "ANDY_BI_PARITY_VALIDATION.md",
        "schema/andy_bi_dataset_schema.json",
        "sample_dataset/manifest.json",
        "validation_reports/sample_dataset_validation_report.md",
    ]
    missing = [item for item in required if not (package / item).exists()]
    report = {
        "status": "passed" if not missing else "blocked",
        "package": str(package),
        "missing": missing,
        "required_count": len(required),
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(_markdown(report), encoding="utf-8")
    print(f"status={report['status']}")
    print(f"package={package}")
    print(f"report={REPORT_MD}")
    return 0 if not missing else 1


def _markdown(report: dict) -> str:
    return (
        "# ANDY BI Publication Package Gate\n\n"
        f"- Status: {report['status']}\n"
        f"- Package: {report['package']}\n"
        f"- Required files: {report['required_count']}\n"
        f"- Missing: {', '.join(report['missing']) if report['missing'] else 'none'}\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
