from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from andy_bi.dataset_builder import build_andy_bi_dataset  # noqa: E402


REPORT_JSON = ROOT / "reports" / "ANDY_BI_DATASET_BUILDER.json"
REPORT_MD = ROOT / "reports" / "ANDY_BI_DATASET_BUILDER.md"


def main() -> int:
    result = build_andy_bi_dataset(out_dir=ROOT / "artifacts" / "andy_bi_dataset_builder_check", fmt="both", synthetic=True)
    report = {
        "status": "passed" if result.validation_status == "valid" else "blocked",
        "validation_status": result.validation_status,
        "synthetic": result.synthetic,
        "row_counts": result.row_counts,
        "manifest": str(result.manifest_path),
        "schema": str(result.schema_path),
        "validation_report": str(result.validation_report_path),
        "file_count": len(result.files),
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(_markdown(report), encoding="utf-8")
    print(f"status={report['status']}")
    print(f"dataset={result.out_dir}")
    print(f"report={REPORT_MD}")
    return 0 if report["status"] == "passed" else 1


def _markdown(report: dict) -> str:
    lines = [
        "# ANDY BI Dataset Builder Gate",
        "",
        f"- Status: {report['status']}",
        f"- Validation status: {report['validation_status']}",
        f"- Synthetic: {report['synthetic']}",
        f"- Files: {report['file_count']}",
        "",
        "## Row Counts",
        "",
    ]
    for table, count in sorted(report["row_counts"].items()):
        lines.append(f"- {table}: {count}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
