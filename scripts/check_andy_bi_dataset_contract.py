from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from andy_bi.data_contract import default_data_contract, required_table_names, validate_contract_payload, write_default_contract  # noqa: E402


REPORT_JSON = ROOT / "reports" / "ANDY_BI_DATASET_CONTRACT.json"
REPORT_MD = ROOT / "reports" / "ANDY_BI_DATASET_CONTRACT.md"


def main() -> int:
    payload = default_data_contract()
    failures = validate_contract_payload(payload)
    generated_schema = ROOT / "artifacts" / "andy_bi_contract_check" / "schema.json"
    write_default_contract(generated_schema)
    report = {
        "status": "passed" if not failures else "blocked",
        "failures": failures,
        "required_table_count": len(required_table_names()),
        "required_tables": list(required_table_names()),
        "generated_schema": str(generated_schema),
        "critical_math_source": payload["critical_math_policy"]["critical_measure_source"],
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(_markdown(report), encoding="utf-8")
    print(f"status={report['status']}")
    print(f"report={REPORT_MD}")
    return 0 if not failures else 1


def _markdown(report: dict) -> str:
    lines = [
        "# ANDY BI Dataset Contract Gate",
        "",
        f"- Status: {report['status']}",
        f"- Required tables: {report['required_table_count']}",
        f"- Critical math source: {report['critical_math_source']}",
        f"- Generated schema: {report['generated_schema']}",
        "",
        "## Failures",
        "",
    ]
    lines.append("- none" if not report["failures"] else "\n".join(f"- {item}" for item in report["failures"]))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
